//! Opt-in observer of the final, compact R/G1/G2/B collapse planes.
//! This is a signed FP32 CFA interchange file, not a camera RAW or a DNG.
use std::{
    collections::BTreeMap,
    fs::{self, File, OpenOptions},
    io::{BufWriter, Read, Write},
    path::{Component, Path, PathBuf},
    sync::atomic::{AtomicU64, Ordering},
};

use anyhow::{Context, Result, bail, ensure};
use serde::Serialize;
use serde_json::{Value, json};
use sha2::{Digest, Sha256};

use super::{MergeBackend, MergeOptions};

fn hex(bytes: &[u8]) -> String {
    bytes.iter().map(|b| format!("{b:02x}")).collect()
}

const CONTRACT: &str = "strehl-merged-cfa-f32-v1";

#[derive(Default)]
pub(crate) enum Request {
    #[default]
    Disabled,
    File(PathBuf),
    Placebo,
}

impl Request {
    pub(crate) fn enabled(&self) -> bool {
        !matches!(self, Self::Disabled)
    }
}

fn sidecar(path: &Path) -> PathBuf {
    let mut name = path.as_os_str().to_os_string();
    name.push(".json");
    PathBuf::from(name)
}

// Resolve existing ancestors, including directory symlinks, then normalize the
// non-existent tail. Case folding matches the supported Windows filesystem.
fn normalized(path: &Path) -> Result<String> {
    let absolute = if path.is_absolute() {
        path.to_path_buf()
    } else {
        std::env::current_dir()?.join(path)
    };
    let mut resolved = PathBuf::new();
    for component in absolute.components() {
        match component {
            Component::CurDir => {}
            Component::ParentDir => {
                ensure!(resolved.pop(), "path escapes its root");
            }
            c => resolved.push(c.as_os_str()),
        }
        if resolved.exists() {
            resolved = fs::canonicalize(&resolved)?;
        }
    }
    let text = resolved
        .to_str()
        .context("sensor master paths must be valid Unicode")?
        .to_owned();
    #[cfg(windows)]
    let text = text.to_lowercase();
    Ok(text)
}

fn require_absent(path: &Path) -> Result<()> {
    match fs::symlink_metadata(path) {
        Ok(_) => bail!(
            "sensor master destination already exists: {}",
            path.display()
        ),
        Err(e) if e.kind() == std::io::ErrorKind::NotFound => Ok(()),
        Err(e) => Err(e).with_context(|| format!("checking {}", path.display())),
    }
}

pub(crate) fn preflight(opts: &MergeOptions, sources: &[PathBuf]) -> Result<()> {
    if !opts.sensor_master.enabled() {
        return Ok(());
    }
    ensure!(
        opts.backend == MergeBackend::Pyramid,
        "sensor master requires --merge pyramid"
    );
    ensure!(opts.out.is_some(), "sensor master requires --out");
    ensure!(
        strehl_core::restore::gain_cap_from_env().is_none(),
        "sensor master v1 requires restoration disabled (STREHL_RESTORE); its contract is pre-restoration"
    );
    if let Request::File(path) = &opts.sensor_master {
        let metadata = sidecar(path);
        let confidence = super::confidence_map_path(opts);
        let protected = opts
            .out
            .iter()
            .chain(opts.linear_master.iter())
            .chain(opts.region_recipe.iter())
            .chain(confidence.iter())
            .chain(opts.index_map.iter())
            .chain(opts.n_eff_map.iter())
            .chain(sources.iter());
        let keys: Vec<_> = protected.map(|p| normalized(p)).collect::<Result<_>>()?;
        for destination in [path, &metadata] {
            require_absent(destination)?;
            let parent = destination
                .parent()
                .filter(|p| !p.as_os_str().is_empty())
                .unwrap_or(Path::new("."));
            ensure!(
                parent.is_dir(),
                "sensor master parent directory must already exist: {}",
                parent.display()
            );
            let key = normalized(destination)?;
            ensure!(
                !keys.contains(&key),
                "sensor master destination aliases a source or another output: {}",
                destination.display()
            );
        }
        ensure!(
            normalized(path)? != normalized(&metadata)?,
            "sensor master TIFF and sidecar alias"
        );
    }
    Ok(())
}

#[derive(Serialize)]
struct FileBinding {
    path: PathBuf,
    bytes: u64,
    sha256: String,
}

fn digest_file(path: &Path) -> Result<FileBinding> {
    let mut file = File::open(path)
        .with_context(|| format!("binding sensor master input {}", path.display()))?;
    let before = file.metadata()?;
    ensure!(
        before.is_file(),
        "sensor master input is not a regular file"
    );
    let mut hash = Sha256::new();
    let mut bytes = 0;
    let mut buffer = [0u8; 262144];
    loop {
        let n = file.read(&mut buffer)?;
        if n == 0 {
            break;
        }
        hash.update(&buffer[..n]);
        bytes += n as u64;
    }
    let after = file.metadata()?;
    ensure!(
        bytes == before.len()
            && before.len() == after.len()
            && before.modified()? == after.modified()?,
        "sensor master input changed while hashing: {}",
        path.display()
    );
    Ok(FileBinding {
        path: fs::canonicalize(path)?,
        bytes,
        sha256: hex(&hash.finalize()),
    })
}

pub(crate) struct Provenance {
    sources: Vec<FileBinding>,
    auxiliary_files: Vec<FileBinding>,
    binary: FileBinding,
    environment: BTreeMap<String, String>,
    first_source: Value,
}

impl Provenance {
    pub(crate) fn capture(opts: &MergeOptions, paths: &[PathBuf]) -> Result<Self> {
        preflight(opts, paths)?;
        let environment: BTreeMap<_, _> = std::env::vars()
            .filter(|(k, _)| k.starts_with("STREHL_") || k == "RAYON_NUM_THREADS")
            .collect();
        let mut auxiliary_paths: Vec<PathBuf> = opts.region_recipe.iter().cloned().collect();
        // Only file inputs: output/diagnostic environment paths may be rewritten
        // normally during the stack and must not be mistaken for source inputs.
        for key in [
            "STREHL_WARPMAP",
            "STREHL_DEFECT_MAP",
            "STREHL_LOCAL_PLACEMENT_FILE",
        ] {
            let Some(value) = environment.get(key) else {
                continue;
            };
            let p = PathBuf::from(value);
            if p.is_file() && !auxiliary_paths.contains(&p) {
                auxiliary_paths.push(p);
            }
        }
        Ok(Self {
            sources: paths
                .iter()
                .map(|p| digest_file(p))
                .collect::<Result<_>>()?,
            auxiliary_files: auxiliary_paths
                .iter()
                .map(|p| digest_file(p))
                .collect::<Result<_>>()?,
            binary: digest_file(&std::env::current_exe()?)?,
            environment,
            first_source: Value::Null,
        })
    }

    pub(crate) fn bind_first(&mut self, frame: &strehl_raw::Frame) {
        self.first_source = json!({
            "ordered_source_index": 0, "path": frame.path,
            "camera": frame.camera, "iso_bits": frame.iso.map(f32::to_bits),
            "decoded_buffer": [frame.stride, frame.buffer_height],
            "decoded_active_area": [frame.active.x, frame.active.y, frame.active.width, frame.active.height],
            "black_level_bits": frame.levels.black.to_bits(), "white_level_bits": frame.levels.white.to_bits(),
            "wb_coefficients_bits": frame.wb_coeffs.map(f32::to_bits),
            "xyz_to_camera_rgbe_bits": frame.xyz_to_cam_rgbe.map(|row| row.map(f32::to_bits)),
            "color_matrices_bits": frame.color_matrices.iter().map(|(name,m)| (name,m.map(|r| r.map(f32::to_bits)))).collect::<Vec<_>>(),
            "native_orientation": null, "native_default_crop": null,
            "native_calibration_tags": null,
            "metadata_scope": "Strehl decoded source wrapper; not a copy of native camera tags"
        });
    }

    fn verify(&self) -> Result<()> {
        for expected in self.sources.iter().chain(self.auxiliary_files.iter()) {
            let actual = digest_file(&expected.path)?;
            ensure!(
                actual.bytes == expected.bytes && actual.sha256 == expected.sha256,
                "sensor master input changed during stack: {}",
                expected.path.display()
            );
        }
        ensure!(
            !self.first_source.is_null(),
            "sensor master needs actual first-source metadata"
        );
        Ok(())
    }
}

#[derive(Clone, Copy, Serialize)]
pub(crate) struct Geometry {
    pub full_quad_width: usize,
    pub full_quad_height: usize,
    pub crop_quad: [usize; 4],
}

impl Geometry {
    fn mosaic_origin(self) -> Result<[usize; 2]> {
        // A tiny crop can still have an unrepresentable reference coordinate.
        // Check the reference domain, not just the allocated crop dimensions.
        for dimension in [self.full_quad_width, self.full_quad_height] {
            dimension
                .checked_mul(2)
                .context("sensor master reference pixel extent overflow")?;
        }
        Ok([
            self.crop_quad[0]
                .checked_mul(2)
                .context("sensor master horizontal origin overflow")?,
            self.crop_quad[1]
                .checked_mul(2)
                .context("sensor master vertical origin overflow")?,
        ])
    }

    fn dimensions(self) -> Result<(u32, u32, usize)> {
        self.mosaic_origin()?;
        let [x, y, w, h] = self.crop_quad;
        ensure!(
            w > 0
                && h > 0
                && x.checked_add(w).is_some_and(|r| r <= self.full_quad_width)
                && y.checked_add(h).is_some_and(|b| b <= self.full_quad_height),
            "invalid sensor master compact domain"
        );
        let width = u32::try_from(w.checked_mul(2).context("sensor width overflow")?)?;
        let height = u32::try_from(h.checked_mul(2).context("sensor height overflow")?)?;
        let pixels = w.checked_mul(h).context("sensor pixel count overflow")?;
        Ok((width, height, pixels))
    }
}

#[derive(Debug, Serialize)]
struct PlaneStats {
    name: &'static str,
    minimum: f32,
    maximum: f32,
    negative_samples: u64,
    above_usable_white_samples: u64,
    sha256: String,
}

#[derive(Debug, Serialize)]
struct Encoded {
    width: u32,
    height: u32,
    payload_offset: u32,
    payload_bytes: u64,
    tiff_bytes: u64,
    payload_sha256: String,
    tiff_sha256: String,
    planes: Vec<PlaneStats>,
}

fn payload_size(width: u32, height: u32) -> Result<u64> {
    ensure!(
        width > 0 && height > 0,
        "sensor master dimensions must be positive"
    );
    u64::from(width)
        .checked_mul(u64::from(height))
        .and_then(|pixels| pixels.checked_mul(4))
        .context("sensor master payload byte count overflow")
}

// TIFF 6.0/TIFF-EP numeric fields. Offsets are known before writing, so the
// exact serializer also runs against io::sink() for the observer placebo.
// No seek, full mosaic allocation, compression, floating conversion or clamp.
fn header(width: u32, height: u32) -> Result<Vec<u8>> {
    const DESCRIPTION: &[u8] =
        b"strehl-merged-cfa-f32-v1; signed black-subtracted DN; see .json sidecar\0";
    const SOFTWARE: &[u8] = b"Strehl sensor master v1\0";
    const ENTRIES: u16 = 15;
    let description_offset = 8 + 2 + u32::from(ENTRIES) * 12 + 4;
    let software_offset = description_offset + DESCRIPTION.len() as u32;
    let payload_offset = (software_offset + SOFTWARE.len() as u32 + 3) & !3;
    let payload_bytes = payload_size(width, height)?;
    let tiff_bytes = payload_bytes
        .checked_add(u64::from(payload_offset))
        .context("sensor master TIFF byte count overflow")?;
    ensure!(
        tiff_bytes <= u64::from(u32::MAX),
        "sensor master v1 exceeds classic TIFF size limit; BigTIFF is not implemented"
    );
    let mut out = Vec::with_capacity(payload_offset as usize);
    out.extend_from_slice(b"II\x2a\x00\x08\x00\x00\x00");
    out.extend_from_slice(&ENTRIES.to_le_bytes());
    let entries = [
        (256u16, 4u16, 1u32, width),
        (257, 4, 1, height),
        (258, 3, 1, 32),
        (259, 3, 1, 1),
        (262, 3, 1, 32803),
        (270, 2, DESCRIPTION.len() as u32, description_offset),
        (273, 4, 1, payload_offset),
        (277, 3, 1, 1),
        (278, 4, 1, height),
        (279, 4, 1, payload_bytes as u32),
        (284, 3, 1, 1),
        (305, 2, SOFTWARE.len() as u32, software_offset),
        (339, 3, 1, 3),
        (33421, 3, 2, 0x0002_0002),
        (33422, 1, 4, 0x0201_0100),
    ];
    for (tag, kind, count, value) in entries {
        out.extend_from_slice(&tag.to_le_bytes());
        out.extend_from_slice(&kind.to_le_bytes());
        out.extend_from_slice(&count.to_le_bytes());
        out.extend_from_slice(&value.to_le_bytes());
    }
    out.extend_from_slice(&0u32.to_le_bytes());
    out.extend_from_slice(DESCRIPTION);
    out.extend_from_slice(SOFTWARE);
    out.resize(payload_offset as usize, 0);
    Ok(out)
}

fn encode(
    writer: &mut impl Write,
    geometry: Geometry,
    planes: &[Vec<f32>],
    usable_white: f32,
) -> Result<Encoded> {
    let (width, height, pixels) = geometry.dimensions()?;
    ensure!(
        planes.len() == 4 && planes.iter().all(|p| p.len() == pixels),
        "sensor master requires four compact R/G1/G2/B planes"
    );
    ensure!(
        usable_white.is_finite() && usable_white > 0.0,
        "sensor master usable white must be finite and positive"
    );
    let prefix = header(width, height)?;
    let mut full_hash = Sha256::new();
    full_hash.update(&prefix);
    writer.write_all(&prefix)?;
    let mut payload_hash = Sha256::new();
    let mut plane_hashes = [Sha256::new(), Sha256::new(), Sha256::new(), Sha256::new()];
    let mut stats: Vec<_> = ["R", "G1", "G2", "B"]
        .into_iter()
        .map(|name| PlaneStats {
            name,
            minimum: f32::INFINITY,
            maximum: f32::NEG_INFINITY,
            negative_samples: 0,
            above_usable_white_samples: 0,
            sha256: String::new(),
        })
        .collect();
    let qw = geometry.crop_quad[2];
    let mut row = vec![0u8; width as usize * 4];
    for y in 0..height as usize {
        for x in 0..width as usize {
            let slot = (y % 2) * 2 + x % 2; // R G1 / G2 B -- NOT CfaPlane::ALL order.
            let index = (y / 2) * qw + x / 2;
            let value = planes[slot][index];
            ensure!(
                value.is_finite(),
                "nonfinite sensor master value in {} plane at compact index {}",
                stats[slot].name,
                index
            );
            let bits = value.to_bits().to_le_bytes();
            row[x * 4..x * 4 + 4].copy_from_slice(&bits);
            plane_hashes[slot].update(bits);
            let stat = &mut stats[slot];
            stat.minimum = stat.minimum.min(value);
            stat.maximum = stat.maximum.max(value);
            stat.negative_samples += u64::from(value < 0.0);
            stat.above_usable_white_samples += u64::from(value > usable_white);
        }
        payload_hash.update(&row);
        full_hash.update(&row);
        writer.write_all(&row)?;
    }
    for (stat, hash) in stats.iter_mut().zip(plane_hashes) {
        stat.sha256 = hex(&hash.finalize());
    }
    let payload_bytes = payload_size(width, height)?;
    Ok(Encoded {
        width,
        height,
        payload_offset: prefix.len() as u32,
        payload_bytes,
        tiff_bytes: prefix.len() as u64 + payload_bytes,
        payload_sha256: hex(&payload_hash.finalize()),
        tiff_sha256: hex(&full_hash.finalize()),
        planes: stats,
    })
}

#[cfg(not(windows))]
fn publish_without_replace(from: &Path, to: &Path) -> std::io::Result<()> {
    fs::hard_link(from, to)
}
#[cfg(windows)]
fn publish_without_replace(from: &Path, to: &Path) -> std::io::Result<()> {
    use std::os::windows::ffi::OsStrExt;
    use windows_sys::Win32::Storage::FileSystem::{MOVEFILE_WRITE_THROUGH, MoveFileExW};
    let from: Vec<u16> = from.as_os_str().encode_wide().chain(Some(0)).collect();
    let to: Vec<u16> = to.as_os_str().encode_wide().chain(Some(0)).collect();
    // SAFETY: Owned UTF-16 buffers remain live and terminated for this call.
    // REPLACE_EXISTING is deliberately omitted.
    if unsafe { MoveFileExW(from.as_ptr(), to.as_ptr(), MOVEFILE_WRITE_THROUGH) } == 0 {
        Err(std::io::Error::last_os_error())
    } else {
        Ok(())
    }
}

static TEMP_ID: AtomicU64 = AtomicU64::new(0);
struct Temporary {
    path: PathBuf,
    file: Option<File>,
}
impl Temporary {
    fn new(destination: &Path) -> Result<Self> {
        let parent = destination
            .parent()
            .filter(|p| !p.as_os_str().is_empty())
            .unwrap_or(Path::new("."));
        for _ in 0..64 {
            let path = parent.join(format!(
                ".strehl-sensor-{}-{}.tmp",
                std::process::id(),
                TEMP_ID.fetch_add(1, Ordering::Relaxed)
            ));
            match OpenOptions::new().write(true).create_new(true).open(&path) {
                Ok(file) => {
                    return Ok(Self {
                        path,
                        file: Some(file),
                    });
                }
                Err(e) if e.kind() == std::io::ErrorKind::AlreadyExists => {}
                Err(e) => return Err(e.into()),
            }
        }
        bail!("could not reserve a sensor master temporary file")
    }
    fn sync_close(&mut self) -> Result<()> {
        if let Some(file) = self.file.take() {
            file.sync_all()?;
        }
        Ok(())
    }
    fn publish(&self, destination: &Path) -> Result<()> {
        // Publish only a new directory entry, never replace a file or symlink.
        // Unix uses hard_link; Windows uses MoveFileEx without replacement.
        publish_without_replace(&self.path, destination).with_context(|| {
            format!(
                "publishing sensor master without replacement: {}",
                destination.display()
            )
        })
    }
}
impl Drop for Temporary {
    fn drop(&mut self) {
        self.file.take();
        let _ = fs::remove_file(&self.path);
    }
}

pub(crate) fn finish(
    opts: &MergeOptions,
    provenance: Provenance,
    geometry: Geometry,
    planes: &[Vec<f32>],
    usable_white: f32,
    process: Value,
) -> Result<()> {
    ensure!(
        opts.sensor_master.enabled(),
        "disabled sensor master must not enter serializer"
    );
    geometry.dimensions()?;
    let mosaic_origin = geometry.mosaic_origin()?;
    provenance.verify()?;
    // Recheck after the long stack: never overwrite a file created meanwhile.
    let sources: Vec<_> = provenance.sources.iter().map(|s| s.path.clone()).collect();
    preflight(opts, &sources)?;
    let mut temporary = match &opts.sensor_master {
        Request::File(path) => Some(Temporary::new(path)?),
        _ => None,
    };
    let encoded = if let Some(tmp) = temporary.as_mut() {
        let mut writer = BufWriter::new(
            tmp.file
                .as_mut()
                .context("sensor master temporary is closed")?,
        );
        let result = encode(&mut writer, geometry, planes, usable_white)?;
        writer.flush()?;
        result
    } else {
        encode(&mut std::io::sink(), geometry, planes, usable_white)?
    };
    let receipt = json!({"contract":CONTRACT,"mode":if temporary.is_some(){"file"}else{"placebo"},"encoded":encoded});
    let metadata = json!({
        "contract":CONTRACT,"schema_version":1,"encoded":encoded,"geometry":geometry,
        "sample_domain":"signed black-subtracted camera DN; final pyramid collapse after region repairs",
        "plane_order":["R","G1","G2","B"],"cfa_pattern":[["R","G1"],["G2","B"]],
        "mosaic_origin_in_reference_active_pixels":mosaic_origin,
        "before":["white balance","exposure","normalization","demosaic","color conversion","restoration"],
        "sources":provenance.sources,"auxiliary_files":provenance.auxiliary_files,
        "first_source_metadata":provenance.first_source,"binary":provenance.binary,
        "version":env!("CARGO_PKG_VERSION"),"environment":provenance.environment,"process":process,
        "native_raw_metadata_complete":false,"dng_compatibility_claimed":false
    });
    if let (Request::File(path), Some(tmp)) = (&opts.sensor_master, temporary.as_mut()) {
        let mut metadata_tmp = Temporary::new(&sidecar(path))?;
        serde_json::to_writer_pretty(
            metadata_tmp
                .file
                .as_mut()
                .context("metadata temporary is closed")?,
            &metadata,
        )?;
        metadata_tmp.file.as_mut().unwrap().write_all(b"\n")?;
        metadata_tmp.sync_close()?;
        tmp.sync_close()?;
        tmp.publish(path)?;
        metadata_tmp.publish(&sidecar(path)).context(
            "sensor TIFF is complete but sidecar publication failed; pair is not committed",
        )?;
    }
    eprintln!("sensor-master-receipt {}", serde_json::to_string(&receipt)?);
    Ok(())
}

#[cfg(test)]
#[path = "sensor-master-tests.rs"]
mod tests;
