//! Explicit research-only reader for one independently audited historical cache.
//! Never modifies/relabels caches and never invokes a RAW decoder.
use anyhow::{Context, Result, ensure};
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use std::{
    collections::HashMap,
    fs::{self, File},
    io::Read,
    path::{Path, PathBuf},
    sync::Arc,
};
use strehl_cli::{
    session_cache::{CacheStats, CachedFrameMetadata, CachedGeometry, CachedSource},
    session_input::SourceIdentity,
};
use strehl_core::plane::PlaneGeometry;
const KEY: &str = "c6fa0bc876fd2934faedea72a6e545c8bc2e2d3a812650c4726716216f0ce5bd";
const LOCK: &str = "d2a0612ac7af7eb0157a587043cc89915d92fee6776e351b6ad6504201a581a3";
const RAW: &str = "34e779aaffdd215bdee3e9a0128289bae551cbb49dc75c1d3aa96b646f4c1455";
fn hex(bytes: &[u8]) -> String {
    bytes.iter().map(|v| format!("{v:02x}")).collect()
}
fn materialize(text: &str) -> Vec<u8> {
    text.replace("\r\n", "\n")
        .replace('\n', "\r\n")
        .into_bytes()
}
fn verify_binding(lock: &str, raw: &str) -> Result<String> {
    let lock = lock.replace("\r\n", "\n");
    let start = lock
        .find("[[package]]\nname = \"strehl-core\"\n")
        .context("core package missing")?;
    let end = lock[start + 1..]
        .find("[[package]]")
        .map_or(lock.len(), |i| start + 1 + i);
    let core = &lock[start..end];
    let line = " \"sha2\",\n";
    ensure!(
        core.matches(line).count() == 1,
        "expected exactly one added core sha2 dependency"
    );
    let old = format!(
        "{}{}{}",
        &lock[..start],
        core.replacen(line, "", 1),
        &lock[end..]
    );
    let old = materialize(&old);
    let raw = materialize(raw);
    ensure!(
        hex(&Sha256::digest(&old)) == LOCK,
        "historical lock differs beyond audited core sha2 linkage"
    );
    ensure!(
        hex(&Sha256::digest(&raw)) == RAW,
        "historical raw source differs"
    );
    let mut h = Sha256::new();
    h.update(b"strehl-original-active-cfa-v1");
    h.update(&old);
    h.update(&raw);
    let key = hex(&h.finalize());
    ensure!(key == KEY, "historical decoder key mismatch");
    Ok(key)
}
pub fn binding() -> Result<serde_json::Value> {
    let lock = include_str!(concat!(env!("CARGO_MANIFEST_DIR"), "/../../Cargo.lock"));
    let raw = include_str!(concat!(
        env!("CARGO_MANIFEST_DIR"),
        "/../strehl-raw/src/lib.rs"
    ));
    let key = verify_binding(lock, raw)?;
    Ok(
        serde_json::json!({"revision":"ef65505013585abcc86b1410e4bf902bf34ed479","decoder_key":key,"raw_crlf_sha256":RAW,"old_lock_crlf_sha256":LOCK,"current_compiled_lock_sha256":hex(&Sha256::digest(lock.as_bytes())),"current_compiled_raw_sha256":hex(&Sha256::digest(raw.as_bytes())),"proof":"exact current lock bytes minus only core sha2 line equal historical lock after CRLF normalization; exact own RAW source equal","policy":"explicit historical research read only; no production cache acceptance, rewrite, relabel or decode"}),
    )
}
#[derive(Clone, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
struct Header {
    version: u32,
    decoder_key: String,
    source: SourceIdentity,
    cfa: String,
    geometry: CachedGeometry,
    metadata: CachedFrameMetadata,
}
fn read_header(path: &Path) -> Result<(File, Header, Vec<u8>)> {
    let mut file = File::open(path)?;
    let mut prefix = [0u8; 12];
    file.read_exact(&mut prefix)?;
    ensure!(&prefix[..8] == b"STRHCFA1", "wrong historical cache magic");
    let n = u32::from_le_bytes(prefix[8..].try_into().unwrap()) as usize;
    ensure!(n > 0 && n <= 256 * 1024, "historical header limit");
    let mut bytes = vec![0u8; n];
    file.read_exact(&mut bytes)?;
    let header = serde_json::from_slice(&bytes)?;
    Ok((file, header, bytes))
}
fn validate(
    header: &Header,
    identity: &SourceIdentity,
    full: PlaneGeometry,
    length: u64,
    header_len: usize,
) -> Result<usize> {
    ensure!(
        header.version == 1
            && header.decoder_key == KEY
            && header.cfa == "RGGB"
            && header.source == *identity,
        "historical version/decoder/CFA/source mismatch"
    );
    let g = header.geometry;
    ensure!(
        g.width == full.width.checked_mul(2).context("geometry overflow")?
            && g.height == full.height.checked_mul(2).context("geometry overflow")?,
        "historical active geometry differs"
    );
    ensure!(
        g.active_x
            .checked_add(g.width)
            .is_some_and(|v| v <= g.stride)
            && g.active_y
                .checked_add(g.height)
                .is_some_and(|v| v <= g.buffer_height)
            && g.full_frame_bytes().is_some(),
        "historical original buffer geometry invalid"
    );
    let black = f32::from_bits(header.metadata.black_bits);
    let white = f32::from_bits(header.metadata.white_bits);
    ensure!(
        black.is_finite() && black >= 0. && white.is_finite() && white > black && white <= 65535.,
        "historical levels invalid"
    );
    ensure!(
        header
            .metadata
            .iso_bits
            .is_none_or(|v| f32::from_bits(v).is_finite() && f32::from_bits(v) > 0.)
            && header.metadata.camera.len() <= 4096
            && header.metadata.color_matrices_bits.len() <= 64
            && header
                .metadata
                .color_matrices_bits
                .iter()
                .all(|(name, _)| name.len() <= 4096),
        "historical metadata invalid"
    );
    let bytes = g
        .width
        .checked_mul(g.height)
        .and_then(|n| n.checked_mul(2))
        .filter(|n| *n <= isize::MAX as usize)
        .context("historical payload overflow")?;
    let expected = 12u64
        .checked_add(header_len as u64)
        .and_then(|n| n.checked_add(bytes as u64))
        .and_then(|n| n.checked_add(32))
        .context("envelope overflow")?;
    ensure!(
        length == expected,
        "historical payload truncated or trailing bytes"
    );
    Ok(bytes)
}
pub struct HistoricalCache {
    paths: HashMap<String, (SourceIdentity, PathBuf)>,
    entries: HashMap<String, (Arc<CachedSource>, u64)>,
    budget: usize,
    full: PlaneGeometry,
    clock: u64,
    stats: CacheStats,
}
impl HistoricalCache {
    pub fn new(
        root: &Path,
        ids: &[SourceIdentity],
        budget: usize,
        full: PlaneGeometry,
    ) -> Result<Self> {
        binding()?;
        ensure!(
            budget > 0 && root.is_dir() && full.width > 0 && full.height > 0,
            "historical cache budget/root invalid"
        );
        let wanted: HashMap<_, _> = ids.iter().map(|id| (id.sha256.clone(), id)).collect();
        ensure!(wanted.len() == ids.len(), "duplicate original digest");
        for id in ids {
            id.validate()?;
            id.check_unchanged()?;
        }
        let mut paths = HashMap::new();
        for entry in fs::read_dir(root)? {
            let path = entry?.path();
            if path.extension().is_none_or(|v| v != "cfa") {
                continue;
            }
            let (file, h, bytes) = read_header(&path)?;
            let Some(&identity) = wanted.get(&h.source.sha256) else {
                continue;
            };
            validate(&h, identity, full, file.metadata()?.len(), bytes.len())?;
            ensure!(
                paths
                    .insert(identity.sha256.clone(), (identity.clone(), path))
                    .is_none(),
                "duplicate historical entries for one source"
            );
        }
        ensure!(
            paths.len() == ids.len(),
            "historical cache has {} of {} required sources",
            paths.len(),
            ids.len()
        );
        Ok(Self {
            paths,
            entries: HashMap::new(),
            budget,
            full,
            clock: 0,
            stats: CacheStats::default(),
        })
    }
    pub fn stats(&self) -> CacheStats {
        self.stats
    }
    pub fn path(&self, id: &SourceIdentity) -> Result<PathBuf> {
        let (bound, path) = self
            .paths
            .get(&id.sha256)
            .context("source not in historical session")?;
        ensure!(*bound == *id, "historical source identity changed");
        Ok(path.clone())
    }
    pub fn load(&mut self, id: &SourceIdentity) -> Result<Option<Arc<CachedSource>>> {
        id.check_unchanged()?;
        let path = self.path(id)?;
        self.clock = self.clock.wrapping_add(1);
        if let Some((source, clock)) = self.entries.get_mut(&id.sha256) {
            *clock = self.clock;
            self.stats.memory_hits += 1;
            return Ok(Some(Arc::clone(source)));
        }
        let (mut file, h, header) = read_header(&path)?;
        let bytes = validate(&h, id, self.full, file.metadata()?.len(), header.len())?;
        while bytes > self.budget.saturating_sub(self.stats.resident_cfa_bytes) {
            let key = self
                .entries
                .iter()
                .filter(|(_, v)| Arc::strong_count(&v.0) == 1)
                .min_by_key(|(_, v)| v.1)
                .map(|(k, _)| k.clone())
                .context("historical cache pinned beyond budget")?;
            let old = self.entries.remove(&key).unwrap();
            self.stats.resident_cfa_bytes -= old.0.cfa_bytes();
        }
        let mut data = Vec::new();
        data.try_reserve_exact(bytes / 2)?;
        let mut digest = Sha256::new();
        digest.update(&header);
        let mut block = [0u8; 64 * 1024];
        let mut remaining = bytes;
        while remaining > 0 {
            let n = remaining.min(block.len());
            file.read_exact(&mut block[..n])?;
            digest.update(&block[..n]);
            data.extend(
                block[..n]
                    .as_chunks::<2>()
                    .0
                    .iter()
                    .map(|v| u16::from_le_bytes(*v)),
            );
            remaining -= n;
        }
        let mut expected = [0u8; 32];
        file.read_exact(&mut expected)?;
        let actual: [u8; 32] = digest.finalize().into();
        ensure!(
            actual == expected,
            "historical full header/payload digest mismatch"
        );
        id.check_unchanged()?;
        let source = Arc::new(CachedSource {
            identity: id.clone(),
            geometry: h.geometry,
            metadata: h.metadata,
            data,
        });
        self.stats.resident_cfa_bytes += source.cfa_bytes();
        self.stats.peak_resident_cfa_bytes = self
            .stats
            .peak_resident_cfa_bytes
            .max(self.stats.resident_cfa_bytes);
        self.stats.disk_hits += 1;
        self.entries
            .insert(id.sha256.clone(), (Arc::clone(&source), self.clock));
        Ok(Some(source))
    }
}
#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn historical_binding_is_exact_and_refuses_other_source_or_dependency_changes() {
        let lock = include_str!(concat!(env!("CARGO_MANIFEST_DIR"), "/../../Cargo.lock"));
        let raw = include_str!(concat!(
            env!("CARGO_MANIFEST_DIR"),
            "/../strehl-raw/src/lib.rs"
        ));
        assert_eq!(verify_binding(lock, raw).unwrap(), KEY);
        assert!(verify_binding(&format!("{lock}\n# unrelated change"), raw).is_err());
        assert!(verify_binding(lock, &format!("{raw}\n// modified decoder")).is_err());
        assert!(verify_binding(&lock.replacen(" \"sha2\",", " \"sha3\",", 1), raw).is_err());
    }
    struct Fixture {
        root: PathBuf,
        id: SourceIdentity,
        path: PathBuf,
        full: PlaneGeometry,
    }
    impl Fixture {
        fn new() -> Self {
            let base = std::env::var_os("STREHL_TEST_TMP")
                .map(PathBuf::from)
                .unwrap_or_else(std::env::temp_dir);
            let stamp = std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .unwrap()
                .as_nanos();
            let root = base.join(format!("sr-historical-{}-{stamp}", std::process::id()));
            fs::create_dir_all(&root).unwrap();
            let source = root.join("original.fixture");
            fs::write(&source, [37u8]).unwrap();
            let source = fs::canonicalize(source).unwrap();
            let meta = fs::metadata(&source).unwrap();
            let id = SourceIdentity {
                path: source,
                bytes: 1,
                modified_unix_nanos: Some(
                    meta.modified()
                        .unwrap()
                        .duration_since(std::time::UNIX_EPOCH)
                        .unwrap()
                        .as_nanos()
                        .try_into()
                        .unwrap(),
                ),
                sha256: hex(&Sha256::digest([37u8])),
            };
            let h = Header {
                version: 1,
                decoder_key: KEY.into(),
                source: id.clone(),
                cfa: "RGGB".into(),
                geometry: CachedGeometry {
                    stride: 20,
                    buffer_height: 16,
                    active_x: 1,
                    active_y: 2,
                    width: 16,
                    height: 12,
                },
                metadata: CachedFrameMetadata {
                    black_bits: 512f32.to_bits(),
                    white_bits: 16000f32.to_bits(),
                    iso_bits: Some(100f32.to_bits()),
                    wb_bits: [1f32.to_bits(); 4],
                    xyz_to_cam_bits: [[0; 3]; 4],
                    color_matrices_bits: vec![],
                    camera: "fixture".into(),
                },
            };
            let header = serde_json::to_vec(&h).unwrap();
            let payload: Vec<u8> = (0..192u16).flat_map(|i| (1024 + i).to_le_bytes()).collect();
            let mut digest = Sha256::new();
            digest.update(&header);
            digest.update(&payload);
            let mut file = Vec::new();
            file.extend_from_slice(b"STRHCFA1");
            file.extend_from_slice(&(header.len() as u32).to_le_bytes());
            file.extend_from_slice(&header);
            file.extend_from_slice(&payload);
            file.extend_from_slice(&digest.finalize());
            let path = root.join("fixture.cfa");
            fs::write(&path, file).unwrap();
            Self {
                root,
                id,
                path,
                full: PlaneGeometry {
                    width: 8,
                    height: 6,
                },
            }
        }
        fn open(&self, budget: usize) -> HistoricalCache {
            HistoricalCache::new(
                &self.root,
                std::slice::from_ref(&self.id),
                budget,
                self.full,
            )
            .unwrap()
        }
    }
    impl Drop for Fixture {
        fn drop(&mut self) {
            let _ = fs::remove_dir_all(&self.root);
        }
    }
    #[test]
    fn historical_payload_memory_hits_budget_and_stale_source_are_checked() {
        let f = Fixture::new();
        let mut cache = f.open(1024);
        let source = cache.load(&f.id).unwrap().unwrap();
        assert_eq!(source.data.len(), 192);
        assert_eq!(source.data[0], 1024);
        assert_eq!(source.geometry.active_x, 1);
        assert!(Arc::ptr_eq(&source, &cache.load(&f.id).unwrap().unwrap()));
        assert_eq!(cache.stats().memory_hits, 1);
        assert_eq!(cache.stats().decodes, 0);
        let mut small = f.open(383);
        assert!(small.load(&f.id).is_err());
        fs::write(&f.id.path, [37u8, 38]).unwrap();
        assert!(cache.load(&f.id).is_err());
    }
    #[test]
    fn historical_corrupt_payload_identity_and_envelope_refuse() {
        let f = Fixture::new();
        let original = fs::read(&f.path).unwrap();
        let mut changed = original.clone();
        let n = changed.len();
        changed[n - 33] ^= 1;
        fs::write(&f.path, changed).unwrap();
        let mut cache = f.open(1024);
        assert!(cache.load(&f.id).is_err());
        fs::write(&f.path, &original).unwrap();
        let mut cache = f.open(1024);
        let mut wrong = f.id.clone();
        wrong.bytes += 1;
        assert!(cache.load(&wrong).is_err());
        let mut trailing = original.clone();
        trailing.push(0);
        fs::write(&f.path, trailing).unwrap();
        assert!(HistoricalCache::new(&f.root, std::slice::from_ref(&f.id), 1024, f.full).is_err());
        fs::write(&f.path, &original[..original.len() - 1]).unwrap();
        assert!(HistoricalCache::new(&f.root, std::slice::from_ref(&f.id), 1024, f.full).is_err());
    }
}
