//! Small persistent navigation derivatives. File evidence and all disk access
//! stay on a worker; a UI paint is always a memory-only lookup.
use super::PreviewImage;
use crate::workspace_history::{PhotoVersion, photographs};
use anyhow::{Context, Result, ensure};
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use std::{
    fs::{self, File, OpenOptions},
    io::{Read, Seek, SeekFrom, Write},
    path::{Path, PathBuf},
    sync::atomic::{AtomicBool, Ordering},
    time::{SystemTime, UNIX_EPOCH},
};
use strehl_edit::{DevelopmentRecipe, LinearImage};

pub(crate) const SIDE: u32 = 384;
const MAX_HEADER: usize = 4096;
const MAX_PIXELS: usize = SIDE as usize * SIDE as usize * 4;
const DISK_BUDGET: u64 = 128 * 1024 * 1024;
const DISK_ENTRIES: usize = 512;
const FORMAT: u32 = 2;

#[derive(Serialize, Deserialize)]
struct Header {
    format: u32,
    identity: String,
    source_size: [u32; 2],
    size: [usize; 2],
}

fn digest(bytes: &[u8]) -> String {
    Sha256::digest(bytes)
        .iter()
        .map(|b| format!("{b:02x}"))
        .collect()
}

fn file_identity(path: &Path, source: bool) -> Result<String> {
    let mut file = File::open(path)?;
    let metadata = file.metadata()?;
    ensure!(metadata.is_file(), "Preview source is not a file");
    let nanos = |time: std::io::Result<SystemTime>| {
        time.ok()
            .and_then(|t| t.duration_since(UNIX_EPOCH).ok())
            .map(|d| d.as_nanos())
    };
    let mut identity = serde_json::to_vec(&(
        FORMAT,
        path,
        source,
        metadata.len(),
        nanos(metadata.modified()),
        nanos(metadata.created()),
    ))?;
    // The small bookends include TIFF directory/ICC changes and protect common
    // same-size/coarse-timestamp replacements without hashing a 400 MB master.
    let count = metadata.len().min(4096) as usize;
    let mut bytes = vec![0; count];
    file.read_exact(&mut bytes)?;
    identity.extend_from_slice(&bytes);
    file.seek(SeekFrom::End(-(count as i64)))?;
    file.read_exact(&mut bytes)?;
    identity.extend_from_slice(&bytes);
    Ok(digest(&identity))
}

pub(crate) fn default_root() -> Option<PathBuf> {
    crate::workspace_history::default_path()
        .and_then(|p| p.parent().map(|p| p.join("explorer-previews")))
}

pub(crate) fn load_file(
    path: &Path,
    source: bool,
    root: Option<&Path>,
    cancelled: &AtomicBool,
) -> Result<PreviewImage> {
    ensure!(!cancelled.load(Ordering::Relaxed), "Preview cancelled");
    let identity = file_identity(path, source)?;
    let cached = root.map(|root| root.join(format!("{identity}.preview")));
    if let Some(cache) = &cached
        && let Ok(image) = read(cache, path, &identity)
    {
        return Ok(image);
    }
    let image = if source {
        crate::source_preview::load_draft_source(path, SIDE, cancelled)?
    } else if path
        .extension()
        .is_some_and(|e| e.eq_ignore_ascii_case("tif") || e.eq_ignore_ascii_case("tiff"))
    {
        let (image, source_size) = strehl_edit::load_tiff_thumbnail(path, SIDE, cancelled)?;
        render(path, &image, &DevelopmentRecipe::default(), source_size)?
    } else {
        super::load_preview_image(path.into(), SIDE, cancelled)?
    };
    ensure!(!cancelled.load(Ordering::Relaxed), "Preview cancelled");
    // Do not publish a derivative when its source changed during the read.
    ensure!(
        identity == file_identity(path, source)?,
        "Preview source changed while reading it"
    );
    if let Some(cache) = &cached {
        let _ = write(cache, &identity, &image);
        if let Some(root) = root {
            prune(root);
        }
    }
    Ok(image)
}

pub(crate) fn render(
    path: &Path,
    image: &LinearImage,
    recipe: &DevelopmentRecipe,
    source_size: [u32; 2],
) -> Result<PreviewImage> {
    let (width, height, rgb) = image.render_region_sdr8(recipe, [0.0, 0.0], [1.0, 1.0], SIDE)?;
    Ok(PreviewImage {
        path: path.into(),
        source_size,
        size: [width as usize, height as usize],
        rgba: rgb
            .as_chunks::<3>()
            .0
            .iter()
            .flat_map(|p| [p[0], p[1], p[2], 255])
            .collect(),
        is_overview: true,
    })
}

fn version_identity(version: &PhotoVersion, recipe: &DevelopmentRecipe) -> Result<String> {
    Ok(digest(&serde_json::to_vec(&(
        FORMAT,
        &version.id,
        &version.owner,
        &version.photo,
        &version.decoded_source,
        &version.loaded_sha256,
        recipe,
    ))?))
}
pub(crate) fn save_version(
    root: &Path,
    version: &PhotoVersion,
    image: &LinearImage,
    recipe: &DevelopmentRecipe,
) -> Result<PreviewImage> {
    ensure!(
        photographs::valid_id(&version.id),
        "Invalid version thumbnail identity"
    );
    let preview = render(
        &version.owner.output,
        image,
        recipe,
        version.photo.dimensions,
    )?;
    write(
        &root.join(format!("{}.preview", version.id)),
        &version_identity(version, recipe)?,
        &preview,
    )?;
    Ok(preview)
}
pub(crate) fn load_version(root: &Path, version: &PhotoVersion) -> Result<PreviewImage> {
    let recipe = photographs::read_preview_recipe(root, version)?;
    read(
        &root.join(format!("{}.preview", version.id)),
        &version.owner.output,
        &version_identity(version, &recipe)?,
    )
}

fn read(cache: &Path, source: &Path, identity: &str) -> Result<PreviewImage> {
    let mut file = File::open(cache)?;
    let bytes = file.metadata()?.len();
    ensure!(
        bytes <= (MAX_HEADER + MAX_PIXELS + 4) as u64,
        "Thumbnail cache entry is oversized"
    );
    let mut prefix = [0; 4];
    file.read_exact(&mut prefix)?;
    let header_bytes = u32::from_le_bytes(prefix) as usize;
    ensure!(header_bytes <= MAX_HEADER, "Thumbnail header is oversized");
    let mut body = vec![0; header_bytes];
    file.read_exact(&mut body)?;
    let header: Header = serde_json::from_slice(&body)?;
    ensure!(
        header.format == FORMAT
            && header.identity == identity
            && header.size.iter().all(|&n| n > 0 && n <= SIDE as usize)
            && header.source_size.iter().all(|&n| n > 0),
        "Thumbnail evidence does not match"
    );
    let count = header.size[0] * header.size[1] * 4;
    ensure!(
        bytes == (4 + header_bytes + count) as u64,
        "Thumbnail pixels are incomplete"
    );
    let mut rgba = vec![0; count];
    file.read_exact(&mut rgba)?;
    Ok(PreviewImage {
        path: source.into(),
        source_size: header.source_size,
        size: header.size,
        rgba,
        is_overview: true,
    })
}
fn write(cache: &Path, identity: &str, image: &PreviewImage) -> Result<()> {
    ensure!(
        image.size.iter().all(|&n| n > 0 && n <= SIDE as usize)
            && image.rgba.len() == image.size[0] * image.size[1] * 4,
        "Thumbnail dimensions are invalid"
    );
    let parent = cache.parent().context("Thumbnail has no cache directory")?;
    fs::create_dir_all(parent)?;
    let header = serde_json::to_vec(&Header {
        format: FORMAT,
        identity: identity.into(),
        source_size: image.source_size,
        size: image.size,
    })?;
    let mut random = [0; 8];
    getrandom::fill(&mut random).map_err(|e| anyhow::anyhow!("Creating thumbnail: {e}"))?;
    let temporary = parent.join(format!("{}.pending", digest(&random)));
    let result = (|| {
        let mut file = OpenOptions::new()
            .write(true)
            .create_new(true)
            .open(&temporary)?;
        file.write_all(&(header.len() as u32).to_le_bytes())?;
        file.write_all(&header)?;
        file.write_all(&image.rgba)?;
        drop(file);
        fs::rename(&temporary, cache)?;
        Ok(())
    })();
    let _ = fs::remove_file(&temporary);
    result
}
fn prune(root: &Path) {
    let Ok(files) = fs::read_dir(root) else {
        return;
    };
    let mut entries: Vec<_> = files
        .flatten()
        .filter_map(|entry| {
            let path = entry.path();
            if path.extension().is_none_or(|e| e != "preview") {
                return None;
            }
            let metadata = entry.metadata().ok()?;
            metadata.is_file().then_some((
                metadata.modified().unwrap_or(UNIX_EPOCH),
                metadata.len(),
                path,
            ))
        })
        .collect();
    entries.sort_unstable_by_key(|e| e.0);
    let mut bytes: u64 = entries.iter().map(|e| e.1).sum();
    let mut count = entries.len();
    for (_, size, path) in entries {
        if bytes <= DISK_BUDGET && count <= DISK_ENTRIES {
            break;
        }
        if fs::remove_file(path).is_ok() {
            bytes = bytes.saturating_sub(size);
            count -= 1;
        }
    }
}

#[cfg(test)]
#[path = "explorer-preview-cache-tests.rs"]
mod tests;
