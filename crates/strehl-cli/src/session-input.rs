//! Explicit multi-pass input, independent of geometry and merge policy.
//!
//! A pass may contain ordered directory segments. Frames are sorted only within
//! each segment; neither filenames nor directory names imply focus coincidence.
use anyhow::{Context, Result, bail, ensure};
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use std::collections::{HashMap, HashSet};
use std::fs::{self, File};
use std::io::{Read, Take};
use std::ops::Range;
use std::path::{Component, Path, PathBuf};
use std::time::UNIX_EPOCH;

pub const SESSION_VERSION: u32 = 1;
/// The current merge reserves the terminal u16 index; keep total frames below it.
pub const MAX_SESSION_FRAMES: usize = u16::MAX as usize - 1;
const MAX_MANIFEST_BYTES: u64 = 1024 * 1024;

fn version_one() -> u32 {
    SESSION_VERSION
}

#[derive(Debug, Clone, Copy, Default, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum SessionMode {
    #[default]
    Combine,
    Repeat,
    Layers,
    Hdr,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct PassSpec {
    pub name: String,
    /// Ordered directory segments belonging to this pass.
    pub directories: Vec<PathBuf>,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct SessionSpec {
    #[serde(default = "version_one")]
    pub version: u32,
    #[serde(default)]
    pub mode: SessionMode,
    pub passes: Vec<PassSpec>,
    /// User-selected primary pass; absence stays distinct from pass zero.
    #[serde(default)]
    pub primary_pass: Option<usize>,
}

impl Default for SessionSpec {
    fn default() -> Self {
        Self {
            version: SESSION_VERSION,
            mode: SessionMode::Combine,
            passes: Vec::new(),
            primary_pass: None,
        }
    }
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct SourceFrame {
    pub global_index: usize,
    pub pass_index: usize,
    pub segment_index: usize,
    pub pass_frame_index: usize,
    pub segment_frame_index: usize,
    pub path: PathBuf,
    pub bytes: u64,
    pub modified_unix_nanos: Option<u64>,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct ResolvedPass {
    pub name: String,
    pub directories: Vec<PathBuf>,
    pub global_range: Range<usize>,
    /// Ranges in global frame coordinates, in the declared segment order.
    pub segment_ranges: Vec<Range<usize>>,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct ResolvedSession {
    /// Canonical absolute directories, retaining the declared mode and primary.
    pub spec: SessionSpec,
    pub manifest_path: Option<PathBuf>,
    pub passes: Vec<ResolvedPass>,
    pub frames: Vec<SourceFrame>,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct SourceIdentity {
    pub path: PathBuf,
    pub bytes: u64,
    pub modified_unix_nanos: Option<u64>,
    /// Whole original input bytes, lowercase hexadecimal SHA256.
    pub sha256: String,
}

/// Header facts, not decode geometry, a focus key or a noise calibration.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct SourceMetadata {
    pub global_index: usize,
    pub path: PathBuf,
    pub camera_make: Option<String>,
    pub camera_model: Option<String>,
    pub lens_model: Option<String>,
    pub lens_type3: Option<u16>,
    /// Existing owned readers do not expose a body serial: None is unknown.
    pub body_serial: Option<String>,
    pub iso: Option<u32>,
    pub exposure_time: Option<[u32; 2]>,
    pub aperture: Option<[u32; 2]>,
    pub focal_length: Option<[u32; 2]>,
    pub capture_date: Option<String>,
    /// Not supplied by the header readers. Decode validates actual WB later.
    pub white_balance: Option<[f32; 4]>,
    pub stored_dimensions: Option<[u32; 2]>,
    pub header_cfa_pattern: Option<[u8; 4]>,
    pub header_black: Option<[u32; 4]>,
    pub header_white: Option<u32>,
    pub optical_header_present: bool,
}

impl SessionSpec {
    pub fn load(path: &Path) -> Result<Self> {
        let file = File::open(path)
            .with_context(|| format!("opening session manifest {}", path.display()))?;
        ensure!(
            file.metadata()?.len() <= MAX_MANIFEST_BYTES,
            "session manifest exceeds {} bytes",
            MAX_MANIFEST_BYTES
        );
        let mut bytes = Vec::new();
        let mut bounded: Take<File> = file.take(MAX_MANIFEST_BYTES + 1);
        bounded.read_to_end(&mut bytes)?;
        ensure!(
            bytes.len() as u64 <= MAX_MANIFEST_BYTES,
            "session manifest grew beyond its size limit"
        );
        let spec: Self = serde_json::from_slice(&bytes)
            .with_context(|| format!("reading session manifest {}", path.display()))?;
        spec.validate()?;
        Ok(spec)
    }

    pub fn validate(&self) -> Result<()> {
        ensure!(
            self.version == SESSION_VERSION,
            "unsupported session version {}, expected {}",
            self.version,
            SESSION_VERSION
        );
        ensure!(!self.passes.is_empty(), "a session needs at least one pass");
        if let Some(primary) = self.primary_pass {
            ensure!(
                primary < self.passes.len(),
                "primary pass {} is outside {} passes",
                primary,
                self.passes.len()
            );
        }
        for (index, pass) in self.passes.iter().enumerate() {
            ensure!(!pass.name.trim().is_empty(), "pass {} needs a name", index);
            ensure!(
                !pass.directories.is_empty(),
                "pass {} has no source directory segments",
                index
            );
            for directory in &pass.directories {
                ensure!(
                    !directory.as_os_str().is_empty(),
                    "pass {} has an empty source directory path",
                    index
                );
            }
        }
        Ok(())
    }

    /// Resolve a saved manifest; relative directories use its parent's path.
    pub fn resolve(&self, manifest_path: &Path) -> Result<ResolvedSession> {
        let manifest_path = fs::canonicalize(manifest_path)
            .with_context(|| format!("resolving manifest {}", manifest_path.display()))?;
        ensure!(manifest_path.is_file(), "session manifest is not a file");
        let parent = manifest_path.parent().context("manifest has no parent")?;
        let mut resolved = self.resolve_from(parent)?;
        resolved.manifest_path = Some(manifest_path);
        Ok(resolved)
    }

    /// Resolve an in-memory spec, such as an unsaved UI draft, from a directory.
    pub fn resolve_from(&self, base_directory: &Path) -> Result<ResolvedSession> {
        self.validate()?;
        let base = fs::canonicalize(base_directory).with_context(|| {
            format!(
                "resolving session base directory {}",
                base_directory.display()
            )
        })?;
        ensure!(base.is_dir(), "session base is not a directory");
        let mut spec = self.clone();
        let mut frames = Vec::new();
        let mut passes = Vec::new();
        let mut seen_directories = HashSet::new();
        let mut seen_files = HashSet::new();
        for (pass_index, pass) in self.passes.iter().enumerate() {
            let start = frames.len();
            let mut directories = Vec::new();
            let mut segment_ranges = Vec::new();
            for (segment_index, source) in pass.directories.iter().enumerate() {
                let path = if source.is_absolute() {
                    source.clone()
                } else {
                    base.join(source)
                };
                let directory = fs::canonicalize(&path)
                    .with_context(|| format!("resolving source directory {}", path.display()))?;
                ensure!(
                    directory.is_dir(),
                    "{} is not a source directory",
                    directory.display()
                );
                ensure!(
                    seen_directories.insert(directory.clone()),
                    "source directory appears more than once: {}",
                    directory.display()
                );
                let mut paths = Vec::new();
                for entry in fs::read_dir(&directory)? {
                    let entry =
                        entry.with_context(|| format!("listing {}", directory.display()))?;
                    let path = entry.path();
                    let is_arw = path
                        .extension()
                        .and_then(|e| e.to_str())
                        .is_some_and(|e| e.eq_ignore_ascii_case("arw"));
                    if !is_arw {
                        continue;
                    }
                    ensure!(
                        path.is_file(),
                        "RAW source is not a file: {}",
                        path.display()
                    );
                    // Refuse while enumerating, before an unbounded candidate
                    // list can grow beyond the merge's representable census.
                    validate_frame_count(frames.len() + paths.len() + 1)?;
                    paths.push(path);
                }
                // Same lexical path order as ordinary raw_paths, within this segment.
                paths.sort();
                ensure!(
                    !paths.is_empty(),
                    "no direct ARW files in {}",
                    directory.display()
                );
                let segment_start = frames.len();
                for (segment_frame_index, path) in paths.into_iter().enumerate() {
                    let path = fs::canonicalize(&path)?;
                    ensure!(
                        seen_files.insert(path.clone()),
                        "RAW source appears more than once: {}",
                        path.display()
                    );
                    validate_frame_count(frames.len() + 1)?;
                    let (bytes, modified_unix_nanos) = file_stamp(&path)?;
                    ensure!(bytes > 0, "RAW source is empty: {}", path.display());
                    frames.push(SourceFrame {
                        global_index: frames.len(),
                        pass_index,
                        segment_index,
                        pass_frame_index: frames.len() - start,
                        segment_frame_index,
                        path,
                        bytes,
                        modified_unix_nanos,
                    });
                }
                segment_ranges.push(segment_start..frames.len());
                directories.push(directory);
            }
            spec.passes[pass_index].directories.clone_from(&directories);
            passes.push(ResolvedPass {
                name: pass.name.clone(),
                directories,
                global_range: start..frames.len(),
                segment_ranges,
            });
        }
        Ok(ResolvedSession {
            spec,
            manifest_path: None,
            passes,
            frames,
        })
    }
}

impl ResolvedSession {
    pub fn load(manifest_path: &Path) -> Result<Self> {
        SessionSpec::load(manifest_path)?.resolve(manifest_path)
    }

    pub fn len(&self) -> usize {
        self.frames.len()
    }

    pub fn is_empty(&self) -> bool {
        self.frames.is_empty()
    }

    pub fn primary_pass_index(&self) -> Option<usize> {
        self.spec.primary_pass
    }

    pub fn frames_for_pass(&self, pass_index: usize) -> Option<&[SourceFrame]> {
        let pass = self.passes.get(pass_index)?;
        self.frames.get(pass.global_range.clone())
    }

    pub fn paths(&self) -> Vec<PathBuf> {
        self.frames.iter().map(|frame| frame.path.clone()).collect()
    }

    /// Check existing paths and nonexistent descendants through their closest
    /// existing ancestor. Directory symlinks/junctions cannot bypass this check.
    /// Call before creating each output, not just when loading the manifest.
    pub fn ensure_output_outside_sources(&self, path: &Path) -> Result<PathBuf> {
        let path = canonical_destination(path)?;
        for pass in &self.passes {
            for directory in &pass.directories {
                ensure!(
                    !path.starts_with(directory),
                    "output/cache {} is inside source directory {}",
                    path.display(),
                    directory.display()
                );
            }
        }
        // Also protect a directly linked source whose target is outside its
        // containing capture directory.
        for frame in &self.frames {
            ensure!(
                path != frame.path,
                "output would overwrite RAW {}",
                path.display()
            );
        }
        Ok(path)
    }

    /// Check a final product destination, refusing any pre-existing object.
    /// This also refuses hardlink aliases and dangling symlinks without needing
    /// platform file identifiers. Publication must still use create-new or an
    /// atomic no-replace operation to close the check/write race.
    pub fn ensure_fresh_output(&self, path: &Path) -> Result<PathBuf> {
        let path = self.ensure_output_outside_sources(path)?;
        match fs::symlink_metadata(&path) {
            Ok(_) => bail!("output already exists: {}", path.display()),
            Err(error) if error.kind() == std::io::ErrorKind::NotFound => Ok(path),
            Err(error) => Err(error).with_context(|| format!("checking output {}", path.display())),
        }
    }

    /// Hash every original file, serially and with bounded scratch. Repeat/HDR
    /// consumers must set reject_duplicate_content before claiming extra data.
    pub fn hash_sources(&self, reject_duplicate_content: bool) -> Result<Vec<SourceIdentity>> {
        let mut seen = HashMap::<String, PathBuf>::new();
        let mut identities = Vec::with_capacity(self.frames.len());
        for frame in &self.frames {
            let identity = frame.hash()?;
            if reject_duplicate_content {
                if let Some(previous) = seen.get(&identity.sha256) {
                    bail!(
                        "duplicate original RAW content: {} and {}; copied inputs are not independent observations",
                        previous.display(),
                        identity.path.display()
                    );
                }
                seen.insert(identity.sha256.clone(), identity.path.clone());
            }
            identities.push(identity);
        }
        Ok(identities)
    }

    pub fn read_metadata(&self) -> Result<Vec<SourceMetadata>> {
        self.frames.iter().map(SourceFrame::read_metadata).collect()
    }
}

impl SourceFrame {
    pub fn check_unchanged(&self) -> Result<()> {
        ensure!(
            file_stamp(&self.path)? == (self.bytes, self.modified_unix_nanos),
            "RAW source changed since session resolution: {}",
            self.path.display()
        );
        Ok(())
    }

    pub fn hash(&self) -> Result<SourceIdentity> {
        self.check_unchanged()?;
        let sha256 = hash_file(&self.path)?;
        self.check_unchanged()?;
        Ok(SourceIdentity {
            path: self.path.clone(),
            bytes: self.bytes,
            modified_unix_nanos: self.modified_unix_nanos,
            sha256,
        })
    }

    pub fn read_metadata(&self) -> Result<SourceMetadata> {
        self.check_unchanged()?;
        let gear = strehl_raw::identity(&self.path);
        // Unlike the best-effort identity reader, malformed optical metadata is
        // an explicit error, never converted into missing calibration.
        let optical = strehl_raw::sony_optical::read(&self.path)
            .with_context(|| format!("reading session metadata {}", self.path.display()))?;
        let result = SourceMetadata {
            global_index: self.global_index,
            path: self.path.clone(),
            camera_make: optical.as_ref().map(|m| m.make.value.clone()).or(gear.make),
            camera_model: optical
                .as_ref()
                .map(|m| m.model.value.clone())
                .or(gear.model),
            lens_model: optical
                .as_ref()
                .and_then(|m| m.lens_model.as_ref().map(|v| v.value.clone()))
                .or(gear.lens_model),
            lens_type3: optical
                .as_ref()
                .and_then(|m| m.lens_type3.as_ref().map(|v| v.value))
                .or(gear.lens_type3),
            body_serial: None,
            iso: optical
                .as_ref()
                .and_then(|m| m.iso.as_ref().map(|v| v.value)),
            exposure_time: optical
                .as_ref()
                .and_then(|m| m.exposure_time.as_ref().map(|v| v.value)),
            aperture: optical
                .as_ref()
                .and_then(|m| m.aperture.as_ref().map(|v| v.value)),
            focal_length: optical
                .as_ref()
                .and_then(|m| m.focal_length.as_ref().map(|v| v.value)),
            capture_date: optical
                .as_ref()
                .and_then(|m| m.capture_date.as_ref().map(|v| v.value.clone())),
            white_balance: None,
            stored_dimensions: optical.as_ref().and_then(|m| {
                Some([
                    m.geometry.stored_width.as_ref()?.value,
                    m.geometry.stored_height.as_ref()?.value,
                ])
            }),
            header_cfa_pattern: optical
                .as_ref()
                .and_then(|m| m.geometry.cfa_pattern.as_ref().map(|v| v.value)),
            header_black: optical
                .as_ref()
                .and_then(|m| m.header_black.as_ref().map(|v| v.value)),
            header_white: optical
                .as_ref()
                .and_then(|m| m.header_white.as_ref().map(|v| v.value)),
            optical_header_present: optical.is_some(),
        };
        self.check_unchanged()?;
        Ok(result)
    }
}

impl SourceIdentity {
    pub fn validate(&self) -> Result<()> {
        ensure!(
            self.path.is_absolute(),
            "source identity path must be absolute"
        );
        ensure!(self.bytes > 0, "source identity has no bytes");
        ensure!(
            self.sha256.len() == 64
                && self
                    .sha256
                    .bytes()
                    .all(|b| b.is_ascii_digit() || (b'a'..=b'f').contains(&b)),
            "source identity needs a lowercase whole-file SHA256"
        );
        Ok(())
    }

    pub fn check_unchanged(&self) -> Result<()> {
        self.validate()?;
        ensure!(
            file_stamp(&self.path)? == (self.bytes, self.modified_unix_nanos),
            "original source changed after hashing: {}",
            self.path.display()
        );
        Ok(())
    }

    /// Full byte check for cache creation; cheap stamps suffice only after the
    /// session has already hashed and frozen its original inputs.
    pub fn verify_content(&self) -> Result<()> {
        self.check_unchanged()?;
        ensure!(
            hash_file(&self.path)? == self.sha256,
            "original RAW digest changed: {}",
            self.path.display()
        );
        self.check_unchanged()
    }
}

fn validate_frame_count(count: usize) -> Result<()> {
    ensure!(
        count <= MAX_SESSION_FRAMES,
        "session has too many frames: {} exceeds the merge limit {}",
        count,
        MAX_SESSION_FRAMES
    );
    Ok(())
}

pub(crate) fn hex(bytes: &[u8]) -> String {
    bytes.iter().map(|byte| format!("{byte:02x}")).collect()
}

fn hash_file(path: &Path) -> Result<String> {
    let mut file = File::open(path)?;
    let mut hasher = Sha256::new();
    let mut block = [0_u8; 64 * 1024];
    loop {
        let count = file.read(&mut block)?;
        if count == 0 {
            break;
        }
        hasher.update(&block[..count]);
    }
    Ok(hex(&hasher.finalize()))
}

fn file_stamp(path: &Path) -> Result<(u64, Option<u64>)> {
    let metadata = fs::metadata(path)
        .with_context(|| format!("reading source identity {}", path.display()))?;
    ensure!(
        metadata.is_file(),
        "{} is not a regular source file",
        path.display()
    );
    let modified = metadata
        .modified()
        .ok()
        .and_then(|t| t.duration_since(UNIX_EPOCH).ok())
        .and_then(|d| u64::try_from(d.as_nanos()).ok());
    Ok((metadata.len(), modified))
}

/// Canonicalize a prospective output without creating it. Resolve links before
/// appending missing descendants; reject parent traversal after a missing part.
pub(crate) fn canonical_destination(path: &Path) -> Result<PathBuf> {
    ensure!(!path.as_os_str().is_empty(), "output path is empty");
    let absolute = if path.is_absolute() {
        path.to_path_buf()
    } else {
        std::env::current_dir()?.join(path)
    };
    let mut existing = absolute.as_path();
    let mut missing = Vec::new();
    while !existing.try_exists()? {
        let component = existing
            .file_name()
            .context("output has an unresolved parent or non-normal component")?;
        missing.push(component.to_os_string());
        existing = existing
            .parent()
            .context("output has no existing ancestor")?;
    }
    let mut resolved = fs::canonicalize(existing)?;
    if !missing.is_empty() {
        ensure!(resolved.is_dir(), "output ancestor is not a directory");
    }
    for component in missing.into_iter().rev() {
        let part = Path::new(&component);
        ensure!(
            part.components().all(|c| matches!(c, Component::Normal(_))),
            "output contains non-normal missing components"
        );
        resolved.push(part);
    }
    Ok(resolved)
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::sync::atomic::{AtomicU64, Ordering};

    static NEXT: AtomicU64 = AtomicU64::new(0);
    struct Fixture(PathBuf);
    impl Fixture {
        fn new() -> Self {
            let path = std::env::temp_dir().join(format!(
                "strehl-session-input-{}-{}",
                std::process::id(),
                NEXT.fetch_add(1, Ordering::Relaxed)
            ));
            fs::create_dir(&path).unwrap();
            Self(path)
        }
        fn directory(&self, name: &str, files: &[(&str, &[u8])]) -> PathBuf {
            let path = self.0.join(name);
            fs::create_dir_all(&path).unwrap();
            for (name, data) in files {
                fs::write(path.join(name), data).unwrap();
            }
            path
        }
    }
    impl Drop for Fixture {
        fn drop(&mut self) {
            let _ = fs::remove_dir_all(&self.0);
        }
    }
    fn pass(name: &str, directories: &[&str]) -> PassSpec {
        PassSpec {
            name: name.into(),
            directories: directories.iter().map(PathBuf::from).collect(),
        }
    }

    #[test]
    fn session_input_defaults_are_explicit_and_unknown_fields_fail() {
        let spec: SessionSpec =
            serde_json::from_str(r#"{"passes":[{"name":"A","directories":["a"]}]}"#).unwrap();
        assert_eq!(spec.version, 1);
        assert_eq!(spec.mode, SessionMode::Combine);
        assert_eq!(spec.primary_pass, None);
        assert!(serde_json::from_str::<SessionSpec>(r#"{"passes":[],"primay_pass":0}"#).is_err());
        assert!(
            serde_json::from_str::<SessionSpec>(
                r#"{"passes":[{"name":"A","directories":[],"repeat":true}]}"#
            )
            .is_err()
        );
        assert!(
            SessionSpec {
                version: 2,
                ..spec.clone()
            }
            .validate()
            .is_err()
        );
        assert!(
            SessionSpec {
                primary_pass: Some(1),
                ..spec
            }
            .validate()
            .is_err()
        );
        assert!(SessionSpec::default().validate().is_err());
    }

    #[test]
    fn session_input_preserves_pass_segment_order_and_reused_filenames() {
        let f = Fixture::new();
        f.directory("a", &[("DSC02.ARW", b"2"), ("DSC01.arw", b"1")]);
        f.directory("b", &[("DSC01.ARW", b"3")]);
        f.directory("c", &[("DSC01.ARW", b"4")]);
        f.directory("a/nested", &[("ignored.ARW", b"nested")]);
        let spec = SessionSpec {
            passes: vec![pass("A", &["b", "a"]), pass("B", &["c"])],
            primary_pass: Some(1),
            ..Default::default()
        };
        let resolved = spec.resolve_from(&f.0).unwrap();
        assert_eq!(resolved.len(), 4);
        assert_eq!(resolved.primary_pass_index(), Some(1));
        assert_eq!(resolved.passes[0].segment_ranges, vec![0..1, 1..3]);
        assert_eq!(resolved.passes[1].global_range, 3..4);
        assert_eq!(resolved.frames[1].path.file_name().unwrap(), "DSC01.arw");
        assert_eq!(resolved.frames[2].pass_frame_index, 2);
        assert_eq!(resolved.frames[2].segment_frame_index, 1);
        assert_eq!(resolved.frames[3].pass_frame_index, 0);
        assert_eq!(resolved.frames_for_pass(1).unwrap().len(), 1);
        assert!(resolved.frames_for_pass(2).is_none());
        assert_eq!(resolved.hash_sources(true).unwrap().len(), 4);
    }

    #[test]
    fn session_input_rejects_canonical_and_copied_duplicates() {
        let f = Fixture::new();
        f.directory("a", &[("one.ARW", b"same")]);
        f.directory("b", &[("different.ARW", b"same")]);
        let mut spec = SessionSpec {
            passes: vec![pass("A", &["a", "./a"])],
            ..Default::default()
        };
        assert!(spec.resolve_from(&f.0).is_err());
        spec.passes = vec![pass("A", &["a"]), pass("B", &["b"])];
        let session = spec.resolve_from(&f.0).unwrap();
        assert_eq!(session.hash_sources(false).unwrap().len(), 2);
        assert!(
            session
                .hash_sources(true)
                .unwrap_err()
                .to_string()
                .contains("duplicate original RAW")
        );
        fs::write(f.0.join("b/different.ARW"), b"changed length").unwrap();
        assert!(session.hash_sources(false).is_err());
    }

    #[test]
    fn session_input_output_guards_cover_missing_descendants_and_manifest_base() {
        let f = Fixture::new();
        let a = f.directory("a", &[("one.ARW", b"one")]);
        let spec = SessionSpec {
            passes: vec![pass("A", &["a"])],
            ..Default::default()
        };
        let manifest = f.0.join("session.json");
        fs::write(&manifest, serde_json::to_vec(&spec).unwrap()).unwrap();
        let session = ResolvedSession::load(&manifest).unwrap();
        assert_eq!(
            session.spec.passes[0].directories,
            vec![fs::canonicalize(&a).unwrap()]
        );
        assert!(
            session
                .ensure_output_outside_sources(&a.join("new/deep/out.tif"))
                .is_err()
        );
        assert!(
            session
                .ensure_output_outside_sources(&f.0.join("output/result.tif"))
                .is_ok()
        );
        assert!(
            session
                .ensure_output_outside_sources(&a.join("one.ARW"))
                .is_err()
        );
    }

    #[test]
    fn session_input_fresh_output_refuses_preexisting_hardlink_aliases() {
        let f = Fixture::new();
        let a = f.directory("a", &[("one.ARW", b"original")]);
        let spec = SessionSpec {
            passes: vec![pass("A", &["a"])],
            ..Default::default()
        };
        let session = spec.resolve_from(&f.0).unwrap();
        let alias = f.0.join("output.tif");
        fs::hard_link(a.join("one.ARW"), &alias).unwrap();
        assert!(session.ensure_fresh_output(&alias).is_err());
        assert_eq!(fs::read(a.join("one.ARW")).unwrap(), b"original");
        assert!(
            session
                .ensure_fresh_output(&f.0.join("new/result.tif"))
                .is_ok()
        );
        assert!(session.ensure_fresh_output(&f.0).is_err());
        // Existing directories remain valid cache roots via the separate guard.
        assert!(session.ensure_output_outside_sources(&f.0).is_ok());
    }

    #[test]
    fn session_input_frame_limit_matches_the_merge_reserved_index() {
        assert!(validate_frame_count(MAX_SESSION_FRAMES).is_ok());
        assert!(validate_frame_count(u16::MAX as usize).is_err());
        assert!(validate_frame_count(usize::MAX).is_err());
    }

    #[test]
    fn session_input_refuses_empty_segments_and_directories_named_arw() {
        let f = Fixture::new();
        f.directory("empty", &[]);
        let mut spec = SessionSpec {
            passes: vec![pass("A", &["empty"])],
            ..Default::default()
        };
        assert!(spec.resolve_from(&f.0).is_err());
        f.directory("bad/file.ARW", &[]);
        spec.passes[0].directories = vec![PathBuf::from("bad")];
        assert!(spec.resolve_from(&f.0).is_err());
    }
}
