//! Immutable photograph versions and delivery evidence. Recipes belong to one
//! exact TIFF; portable looks remain a separate feature.
use anyhow::{Context, Result, ensure};
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use std::{
    fs::{self, File, OpenOptions},
    io::{Read, Write},
    path::{Path, PathBuf},
    sync::{
        Arc,
        atomic::{AtomicBool, Ordering},
    },
};
use strehl_edit::{DevelopmentRecipe, ExportSettings, LinearImage};

const MAX_VERSION_BYTES: usize = 2 * 1024 * 1024 + 64 * 1024;

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub(crate) struct PhotoOwner {
    pub stack: Option<u64>,
    pub run: Option<PathBuf>,
    pub output: PathBuf,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub(crate) struct PhotoIdentity {
    pub canonical_path: PathBuf,
    pub bytes: u64,
    pub dimensions: [u32; 2],
    pub sha256: String,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub(crate) struct PhotoVersion {
    pub id: String,
    pub owner: PhotoOwner,
    pub name: String,
    pub created: u64,
    pub photo: PhotoIdentity,
    pub decoded_source: PhotoIdentity,
    /// Exact loaded pixels, origin, baseline and baked repair identity.
    pub loaded_sha256: String,
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub(crate) struct PhotoExport {
    pub id: String,
    pub version: String,
    pub path: PathBuf,
    pub created: u64,
    pub settings: ExportSettings,
    pub bytes: u64,
    pub sha256: String,
}

#[derive(Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
struct SavedVersion {
    format: u32,
    version: PhotoVersion,
    recipe: DevelopmentRecipe,
}

pub(crate) fn checked_name(name: &str) -> Result<String> {
    let name = name.trim();
    ensure!(
        !name.is_empty()
            && name.chars().count() <= 120
            && name.len() <= 384
            && !name.chars().any(char::is_control),
        "Use a name of 1–120 characters without control characters"
    );
    Ok(name.to_owned())
}

pub(crate) fn valid_id(id: &str) -> bool {
    id.len() == 32
        && id
            .bytes()
            .all(|b| b.is_ascii_digit() || (b'a'..=b'f').contains(&b))
}
fn new_id() -> Result<String> {
    let mut bytes = [0u8; 16];
    getrandom::fill(&mut bytes).map_err(|e| anyhow::anyhow!("Creating version identity: {e}"))?;
    Ok(bytes.iter().map(|b| format!("{b:02x}")).collect())
}
fn payload_path(root: &Path, id: &str) -> Result<PathBuf> {
    ensure!(valid_id(id), "Invalid photograph version identity");
    Ok(root.join(format!("{id}.json")))
}

fn hash_file(path: &Path, cancelled: &AtomicBool) -> Result<(u64, String)> {
    let mut file = File::open(path).with_context(|| format!("Opening {}", path.display()))?;
    let before = file.metadata()?;
    ensure!(
        before.is_file(),
        "Photograph evidence must be a regular file"
    );
    let mut hash = Sha256::new();
    let mut buffer = vec![0u8; 256 * 1024];
    let mut bytes = 0u64;
    loop {
        ensure!(
            !cancelled.load(Ordering::Relaxed),
            "Photograph history cancelled"
        );
        let read = file.read(&mut buffer)?;
        if read == 0 {
            break;
        }
        bytes += read as u64;
        ensure!(bytes <= before.len(), "Photograph changed while reading it");
        hash.update(&buffer[..read]);
    }
    let after = file.metadata()?;
    ensure!(
        bytes == before.len()
            && before.len() == after.len()
            && before.modified().ok() == after.modified().ok(),
        "Photograph changed while reading it"
    );
    Ok((
        bytes,
        hash.finalize().iter().map(|b| format!("{b:02x}")).collect(),
    ))
}

pub(crate) fn identify(
    path: &Path,
    dimensions: [u32; 2],
    cancelled: &AtomicBool,
) -> Result<PhotoIdentity> {
    ensure!(
        dimensions.iter().all(|n| *n > 0),
        "Photograph dimensions are unavailable"
    );
    let canonical_path = fs::canonicalize(path)?;
    let (bytes, sha256) = hash_file(&canonical_path, cancelled)?;
    Ok(PhotoIdentity {
        canonical_path,
        bytes,
        dimensions,
        sha256,
    })
}

pub(crate) fn loaded_hash(image: &LinearImage, cancelled: &AtomicBool) -> Result<String> {
    let mut hash = Sha256::new();
    hash.update(serde_json::to_vec(&(
        image.width,
        image.height,
        image.origin,
        &image.baseline,
        &image.baked_recipe,
    ))?);
    let mut bytes = Vec::with_capacity(256 * 1024);
    for chunk in image.pixels.chunks(64 * 1024) {
        ensure!(
            !cancelled.load(Ordering::Relaxed),
            "Photograph history cancelled"
        );
        bytes.clear();
        for value in chunk {
            bytes.extend_from_slice(&value.to_le_bytes());
        }
        hash.update(&bytes);
    }
    Ok(hash.finalize().iter().map(|b| format!("{b:02x}")).collect())
}

pub(crate) fn save_version(
    root: &Path,
    owner: PhotoOwner,
    name: &str,
    recipe: DevelopmentRecipe,
    image: &Arc<LinearImage>,
    source: &Path,
    cancelled: &AtomicBool,
) -> Result<PhotoVersion> {
    let dimensions = [image.width, image.height];
    recipe.validate()?;
    ensure!(
        serde_json::to_vec_pretty(&recipe)?.len() <= 2 * 1024 * 1024,
        "Photo edits exceed the document limit"
    );
    let version = PhotoVersion {
        id: new_id()?,
        photo: identify(&owner.output, dimensions, cancelled)?,
        decoded_source: identify(source, dimensions, cancelled)?,
        loaded_sha256: loaded_hash(image, cancelled)?,
        owner,
        name: checked_name(name)?,
        created: super::timestamp(),
    };
    let body = serde_json::to_vec(&SavedVersion {
        format: 1,
        version: version.clone(),
        recipe: recipe.clone(),
    })?;
    ensure!(
        body.len() <= MAX_VERSION_BYTES,
        "Photograph version exceeds its size limit"
    );
    fs::create_dir_all(root)?;
    let destination = payload_path(root, &version.id)?;
    let temporary = root.join(format!("{}.pending", version.id));
    let result = (|| {
        let mut file = OpenOptions::new()
            .write(true)
            .create_new(true)
            .open(&temporary)?;
        file.write_all(&body)?;
        file.sync_all()?;
        drop(file);
        ensure!(
            !cancelled.load(Ordering::Relaxed),
            "Photograph history cancelled"
        );
        // A random immutable filename and no-replacement hard link make a
        // competing publisher unable to overwrite an existing version.
        fs::hard_link(&temporary, &destination)?;
        Ok(())
    })();
    let _ = fs::remove_file(&temporary);
    result?;
    // The immutable recipe is already safe. A small navigation derivative is
    // best-effort and must never turn a successful version save into failure.
    let job = crate::development_job::DevelopmentJob::native(image.clone(), recipe);
    let _ = crate::preview::explorer::save_version(root, &version, &job);
    Ok(version)
}

pub(crate) fn read_version(
    root: &Path,
    record: &PhotoVersion,
    current: &PhotoOwner,
    image: &LinearImage,
    source: &Path,
    cancelled: &AtomicBool,
) -> Result<DevelopmentRecipe> {
    let dimensions = [image.width, image.height];
    ensure!(
        &record.owner == current,
        "This version belongs to a different photograph or stack"
    );
    let recipe = read_preview_recipe(root, record)?;
    ensure!(
        identify(&current.output, dimensions, cancelled)? == record.photo,
        "The TIFF has changed since this version was saved; its edits cannot be restored onto different pixels"
    );
    ensure!(
        identify(source, dimensions, cancelled)? == record.decoded_source
            && loaded_hash(image, cancelled)? == record.loaded_sha256,
        "The loaded photograph or RAW-derived master differs from the pixels edited in this version"
    );
    Ok(recipe)
}

/// Preview-only recipe read. Callers must match the recorded loaded-pixel identity.
pub(crate) fn read_preview_recipe(root: &Path, record: &PhotoVersion) -> Result<DevelopmentRecipe> {
    let file = File::open(payload_path(root, &record.id)?)?;
    ensure!(
        file.metadata()?.len() <= MAX_VERSION_BYTES as u64,
        "Photograph version exceeds its size limit"
    );
    let mut bytes = Vec::new();
    file.take((MAX_VERSION_BYTES + 1) as u64)
        .read_to_end(&mut bytes)?;
    ensure!(
        bytes.len() <= MAX_VERSION_BYTES,
        "Photograph version exceeds its size limit"
    );
    let saved: SavedVersion = serde_json::from_slice(&bytes)?;
    ensure!(
        saved.format == 1
            && saved.version.id == record.id
            && saved.version.owner == record.owner
            && saved.version.photo == record.photo
            && saved.version.decoded_source == record.decoded_source
            && saved.version.loaded_sha256 == record.loaded_sha256,
        "Photograph version provenance does not match the library"
    );
    saved.recipe.validate()?;
    Ok(saved.recipe)
}

pub(crate) fn record_export(
    version: &PhotoVersion,
    path: PathBuf,
    settings: ExportSettings,
    cancelled: &AtomicBool,
) -> Result<PhotoExport> {
    settings.validate()?;
    ensure!(
        fs::canonicalize(&path)? != version.photo.canonical_path,
        "An export cannot replace its source photograph"
    );
    let (bytes, sha256) = hash_file(&path, cancelled)?;
    Ok(PhotoExport {
        id: new_id()?,
        version: version.id.clone(),
        path,
        created: super::timestamp(),
        settings,
        bytes,
        sha256,
    })
}

pub(crate) fn verify_export(record: &PhotoExport, cancelled: &AtomicBool) -> Result<()> {
    ensure!(
        hash_file(&record.path, cancelled)? == (record.bytes, record.sha256.clone()),
        "This exported file has changed since it was recorded"
    );
    Ok(())
}

#[cfg(test)]
#[path = "photo-history-tests.rs"]
mod tests;
