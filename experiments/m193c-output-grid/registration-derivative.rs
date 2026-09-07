// M193c source preparation only. No hook or execution release.
// Future parent: merge_cmd::production_truth::m193c_registration_derivative.
use super::*;
use serde::{Deserialize, Serialize};
use serde_json::{Value, json};
use sha2::{Digest, Sha256};
use std::collections::BTreeMap;
use std::io::{Read, Write};
use strehl_core::demosaic::{Mosaic, demosaic_malvar_row};

const PREFIX: &str = "STREHL_M193C_DERIVATIVE_";
const CORPUS: &str = "D:/personal/macro/coffee-bean";
const JSON_LIMIT: usize = 1024 * 1024;
const RAW_LIMIT: u64 = 64 * 1024 * 1024;
const TIFF_LIMIT: u64 = 6 * 36_000_000 + 1024 * 1024;
const ORIGINALS: [usize; 9] = [0, 13, 26, 39, 52, 65, 78, 91, 104];
const NAMES: [&str; 9] = [
    "DSC00016.ARW",
    "DSC00029.ARW",
    "DSC00042.ARW",
    "DSC00055.ARW",
    "DSC00068.ARW",
    "DSC00081.ARW",
    "DSC00094.ARW",
    "DSC00107.ARW",
    "DSC00120.ARW",
];
const LENGTHS: [u64; 9] = [
    39_030_784, 39_878_656, 40_873_984, 40_669_184, 39_497_728, 39_235_584, 39_096_320, 39_018_496,
    38_969_344,
];
const OWNED_NAMES: [&str; 4] = [
    "experiments/m193c-output-grid/registration-derivative.rs",
    "experiments/m193c-output-grid/derivative-controls-preregister.md",
    "experiments/m193c-output-grid/registration-derivative-design.md",
    "experiments/m193c-output-grid/independent-derivative-design-review.md",
];

fn digest(raw: &[u8]) -> String {
    Sha256::digest(raw)
        .iter()
        .map(|v| format!("{v:02x}"))
        .collect()
}
fn finish_hash(h: Sha256) -> String {
    h.finalize().iter().map(|v| format!("{v:02x}")).collect()
}
fn hash_form(value: &str) -> bool {
    value.len() == 64
        && value
            .bytes()
            .all(|b| b.is_ascii_digit() || (b'a'..=b'f').contains(&b))
}
#[derive(Clone, Debug, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
struct FileRef {
    path: PathBuf,
    sha256: String,
    bytes: u64,
}
fn file_ref(path: &Path, cap: u64) -> Result<FileRef> {
    let mut f = fs::File::open(path)?;
    let bytes = f.metadata()?.len();
    ensure!(bytes > 0 && bytes <= cap, "derivative file extent");
    let mut h = Sha256::new();
    let mut chunk = [0u8; 65536];
    let mut total = 0u64;
    loop {
        let n = f.read(&mut chunk)?;
        if n == 0 {
            break;
        }
        total = total
            .checked_add(n as u64)
            .context("derivative hash length overflow")?;
        ensure!(total <= cap, "derivative changed file extent");
        h.update(&chunk[..n]);
    }
    ensure!(total == bytes, "derivative file changed while hashing");
    Ok(FileRef {
        path: path.to_path_buf(),
        sha256: finish_hash(h),
        bytes,
    })
}
fn verify_file(r: &FileRef, cap: u64) -> Result<()> {
    ensure!(
        r.path.is_absolute() && hash_form(&r.sha256),
        "derivative file reference"
    );
    let actual = file_ref(&r.path, cap)?;
    ensure!(
        actual.bytes == r.bytes && actual.sha256 == r.sha256,
        "derivative bound file changed"
    );
    Ok(())
}
fn read_json_bytes(path: &Path) -> Result<Vec<u8>> {
    let mut f = fs::File::open(path)?;
    let n = f.metadata()?.len();
    ensure!(n > 0 && n <= JSON_LIMIT as u64, "derivative JSON extent");
    let mut raw = Vec::with_capacity(n as usize);
    Read::by_ref(&mut f)
        .take(JSON_LIMIT as u64 + 1)
        .read_to_end(&mut raw)?;
    ensure!(
        raw.len() as u64 == n,
        "derivative JSON changed while reading"
    );
    Ok(raw)
}
fn write_json_new(path: &Path, value: &Value) -> Result<()> {
    let mut raw = serde_json::to_vec_pretty(value)?;
    raw.push(b'\n');
    ensure!(raw.len() <= JSON_LIMIT, "derivative JSON output extent");
    let mut f = fs::OpenOptions::new()
        .write(true)
        .create_new(true)
        .open(path)?;
    f.write_all(&raw)?;
    f.sync_all()?;
    ensure!(
        read_json_bytes(path)? == raw,
        "derivative persisted JSON changed"
    );
    Ok(())
}
fn publish(path: &Path, value: &Value, recheck: impl FnOnce() -> Result<()>) -> Result<()> {
    write_json_new(path, value)?;
    if let Err(primary) = recheck() {
        let mut refused = value.clone();
        refused["status"] = json!("REFUSED");
        if refused["error"].is_null() {
            refused["error"] = json!(format!("{primary:#}"));
        }
        let errors = refused["finalization_errors"]
            .as_array_mut()
            .context("derivative finalization error-array contract")?;
        errors.push(json!(format!("{primary:#}")));
        let first = path.with_extension("first.json");
        let saved = (|| -> Result<()> {
            ensure!(
                !first.exists(),
                "derivative retained receipt already exists"
            );
            fs::rename(path, &first)?;
            write_json_new(path, &refused)
        })();
        if let Err(secondary) = saved {
            eprintln!(
                "derivative original finalization error: {primary:#}; persistence error: {secondary:#}"
            );
            return Err(primary.context(format!("failed-status persistence: {secondary:#}")));
        }
        return Err(primary);
    }
    Ok(())
}
fn repo() -> Result<PathBuf> {
    Ok(Path::new(env!("CARGO_MANIFEST_DIR"))
        .join("../..")
        .canonicalize()?)
}
fn workspace_file(path: &Path) -> Result<()> {
    ensure!(
        path.is_absolute() && path.is_file(),
        "derivative workspace input path"
    );
    ensure!(
        path.canonicalize()?.starts_with(repo()?),
        "derivative input outside workspace"
    );
    Ok(())
}
fn output_dir() -> Result<PathBuf> {
    let p = PathBuf::from(std::env::var(format!("{PREFIX}OUTPUT_DIR"))?);
    ensure!(
        p.is_absolute() && !p.exists(),
        "derivative needs a fresh absolute output directory"
    );
    let parent = p.parent().context("derivative output parent")?;
    ensure!(
        parent.is_dir() && parent.canonicalize()?.starts_with(repo()?),
        "derivative output containment"
    );
    fs::create_dir(&p)?;
    Ok(p)
}
fn environment(native: bool) -> Result<BTreeMap<String, String>> {
    ensure!(
        std::env::var("RAYON_NUM_THREADS").as_deref() == Ok("2"),
        "derivative requires two Rayon threads"
    );
    let allowed: &[&str] = if native {
        &[
            "OUTPUT_DIR",
            "INPUT_PLAN",
            "INPUT_PLAN_SHA256",
            "ORIGINAL_INDEX",
            "SNAPSHOT",
        ]
    } else {
        &["OUTPUT_DIR"]
    };
    let mut result = BTreeMap::new();
    result.insert("RAYON_NUM_THREADS".into(), "2".into());
    for (key, value) in std::env::vars() {
        if let Some(suffix) = key.strip_prefix(PREFIX) {
            ensure!(
                allowed.contains(&suffix),
                "derivative unexpected argument {key}"
            );
            result.insert(key, value);
        } else {
            ensure!(
                !key.starts_with("STREHL_"),
                "derivative uncleared override {key}"
            );
        }
    }
    Ok(result)
}

#[derive(Clone, Debug, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
struct Entry {
    original_index: usize,
    name: String,
    path: PathBuf,
    bytes: u64,
    sha256: String,
    mtime_utc: String,
    attributes: u32,
}
#[derive(Clone, Debug, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
struct Settings {
    purpose: String,
    colour: String,
    transfer: String,
    matrix: Value,
    orientation_applied: bool,
    spatial_transform: String,
}
fn unique_hashes<'de, D: serde::Deserializer<'de>>(
    d: D,
) -> std::result::Result<BTreeMap<String, String>, D::Error> {
    struct Visitor;
    impl<'de> serde::de::Visitor<'de> for Visitor {
        type Value = BTreeMap<String, String>;
        fn expecting(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
            f.write_str("unique source-hash map")
        }
        fn visit_map<M: serde::de::MapAccess<'de>>(
            self,
            mut m: M,
        ) -> std::result::Result<Self::Value, M::Error> {
            let mut out = BTreeMap::new();
            while let Some((k, v)) = m.next_entry::<String, String>()? {
                if out.insert(k, v).is_some() {
                    return Err(serde::de::Error::custom("duplicate source key"));
                }
            }
            Ok(out)
        }
    }
    d.deserialize_map(Visitor)
}
#[derive(Clone, Debug, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
struct InputPlan {
    schema: String,
    status: String,
    entries: Vec<Entry>,
    build: FileRef,
    #[serde(deserialize_with = "unique_hashes")]
    source_bindings: BTreeMap<String, String>,
    settings: Settings,
}
impl InputPlan {
    fn validate(&self) -> Result<()> {
        ensure!(
            self.schema == "m193c-registration-input-plan-v1" && self.status == "PLAN_ONLY",
            "derivative input plan schema/status"
        );
        ensure!(self.entries.len() == 9, "nine input plan");
        for (i, e) in self.entries.iter().enumerate() {
            ensure!(
                e.original_index == ORIGINALS[i]
                    && e.name == NAMES[i]
                    && e.bytes == LENGTHS[i]
                    && e.path == Path::new(CORPUS).join(NAMES[i])
                    && hash_form(&e.sha256)
                    && !e.mtime_utc.is_empty()
                    && e.mtime_utc.len() <= 128,
                "nine input plan"
            );
        }
        let s = &self.settings;
        ensure!(
            s.purpose == "registration-development-only"
                && s.colour == "linear-camera-native"
                && s.transfer == "identity"
                && s.matrix.is_null()
                && !s.orientation_applied
                && s.spatial_transform == "identity",
            "derivative input settings"
        );
        ensure!(
            self.build.path.is_absolute() && self.build.bytes > 0 && hash_form(&self.build.sha256),
            "derivative build reference"
        );
        for name in OWNED_NAMES {
            ensure!(
                self.source_bindings.get(name).is_some_and(|s| hash_form(s)),
                "derivative missing owned source binding"
            );
        }
        for (name, sha) in &self.source_bindings {
            ensure!(
                !Path::new(name).is_absolute()
                    && !name.contains('\\')
                    && name
                        .split('/')
                        .all(|p| !p.is_empty() && p != "." && p != "..")
                    && hash_form(sha),
                "derivative source path/hash"
            );
        }
        Ok(())
    }
    fn selected(&self, original: usize) -> Result<&Entry> {
        self.entries
            .iter()
            .find(|e| e.original_index == original)
            .context("derivative unregistered original")
    }
    fn verify_sources(&self) -> Result<()> {
        let root = repo()?;
        for (name, sha) in &self.source_bindings {
            let p = root.join(name);
            ensure!(
                p.canonicalize()?.starts_with(&root),
                "derivative escaped source binding"
            );
            ensure!(
                file_ref(&p, 32 * 1024 * 1024)?.sha256 == *sha,
                "derivative source changed: {name}"
            );
        }
        let own = compiled_sources();
        for (name, sha) in own {
            ensure!(
                self.source_bindings.get(name) == Some(&sha),
                "derivative source/executable mismatch: {name}"
            );
        }
        ensure!(
            std::env::current_exe()?.canonicalize()? == self.build.path.canonicalize()?,
            "derivative wrong executable path"
        );
        verify_file(&self.build, 256 * 1024 * 1024)
    }
}
fn compiled_sources() -> BTreeMap<&'static str, String> {
    BTreeMap::from([
        (
            OWNED_NAMES[0],
            digest(include_bytes!(concat!(
                env!("CARGO_MANIFEST_DIR"),
                "/../../experiments/m193c-output-grid/registration-derivative.rs"
            ))),
        ),
        (
            OWNED_NAMES[1],
            digest(include_bytes!(concat!(
                env!("CARGO_MANIFEST_DIR"),
                "/../../experiments/m193c-output-grid/derivative-controls-preregister.md"
            ))),
        ),
        (
            OWNED_NAMES[2],
            digest(include_bytes!(concat!(
                env!("CARGO_MANIFEST_DIR"),
                "/../../experiments/m193c-output-grid/registration-derivative-design.md"
            ))),
        ),
        (
            OWNED_NAMES[3],
            digest(include_bytes!(concat!(
                env!("CARGO_MANIFEST_DIR"),
                "/../../experiments/m193c-output-grid/independent-derivative-design-review.md"
            ))),
        ),
    ])
}
fn verify_compiled_sources() -> Result<()> {
    let root = repo()?;
    for (name, sha) in compiled_sources() {
        let path = root.join(name);
        ensure!(
            path.canonicalize()?.starts_with(&root),
            "derivative compiled-source containment"
        );
        ensure!(
            file_ref(&path, 32 * 1024 * 1024)?.sha256 == sha,
            "derivative compiled source changed: {name}"
        );
    }
    Ok(())
}

fn validate_frame(frame: &Frame) -> Result<[f32; 3]> {
    let r = frame.active;
    ensure!(r.width > 0 && r.height > 0, "active extent");
    ensure!(r.width <= 8192 && r.height <= 8192, "axis bound");
    let pixels = r
        .width
        .checked_mul(r.height)
        .context("active product overflow")?;
    ensure!(pixels <= 36_000_000, "pixel bound");
    let samples = frame
        .stride
        .checked_mul(frame.buffer_height)
        .context("storage overflow")?;
    ensure!(samples <= 40_000_000, "buffer bound");
    ensure!(
        r.x.is_multiple_of(2)
            && r.y.is_multiple_of(2)
            && r.width.is_multiple_of(2)
            && r.height.is_multiple_of(2),
        "active parity"
    );
    let x1 =
        r.x.checked_add(r.width)
            .context("active endpoint overflow")?;
    let y1 =
        r.y.checked_add(r.height)
            .context("active endpoint overflow")?;
    ensure!(
        x1 <= frame.stride && y1 <= frame.buffer_height,
        "active containment"
    );
    ensure!(frame.data.len() == samples, "storage length");
    let b = frame.levels.black;
    let w = frame.levels.white;
    ensure!(
        b.is_finite() && w.is_finite() && b >= 0.0 && w > b && w <= 65535.0 && (w - b).is_finite(),
        "levels"
    );
    let gains = frame.wb_gains().context("WB coefficients")?;
    ensure!(gains.iter().all(|v| v.is_finite() && *v > 0.0), "WB gains");
    Ok(gains)
}
fn normalized_active_mosaic(frame: &Frame) -> Result<(Vec<f32>, Value)> {
    let gains = validate_frame(frame)?;
    let r = frame.active;
    let b = frame.levels.black;
    let w = frame.levels.white;
    let inv = 1.0f32 / (w - b);
    ensure!(inv.is_finite() && inv > 0.0, "inverse range");
    let mut mosaic = Vec::with_capacity(r.width * r.height);
    let mut payload = Sha256::new();
    let mut rows = Vec::with_capacity(r.height);
    let mut minimum = f32::INFINITY;
    let mut maximum = f32::NEG_INFINITY;
    for y in 0..r.height {
        let mut row_hash = Sha256::new();
        for (x, &sample) in frame.active_row(y).iter().enumerate() {
            let channel = match ((y & 1), (x & 1)) {
                (0, 0) => 0,
                (1, 1) => 2,
                _ => 1,
            };
            let value = ((sample as f32 - b) * inv) * gains[channel];
            ensure!(value.is_finite(), "normalized finiteness");
            minimum = minimum.min(value);
            maximum = maximum.max(value);
            mosaic.push(value);
            payload.update(sample.to_le_bytes());
            row_hash.update(sample.to_le_bytes());
        }
        rows.push(finish_hash(row_hash));
    }
    let mut metadata = json!({
        "stride": frame.stride, "buffer_height": frame.buffer_height,
        "allocated_samples": frame.data.len(), "allocated_bytes": frame.allocated_bytes(),
        "active": {"x": r.x, "y": r.y, "width": r.width, "height": r.height},
        "active_samples": r.width * r.height, "active_sha256_u16_le": finish_hash(payload),
        "active_row_sha256_u16_le": rows,
    });
    let radiometry = json!({"black": b, "white": w,
        "black_f32_bits": b.to_bits(), "white_f32_bits": w.to_bits(),
        "inverse_range_f32_bits": inv.to_bits(), "wb_rgb": gains,
        "wb_rgb_f32_bits": gains.map(f32::to_bits),
        "raw_wb_f32_bits": frame.wb_coeffs.map(f32::to_bits),
        "normalized_min": minimum, "normalized_max": maximum,
        "mosaic_bytes": mosaic.len() * 4,
    });
    let conventions = json!({
        "cfa_validation": "owned decoder requires camera RGGB; even active origin preserves local RGGB",
        "level_selection": "existing wrapper resolved scalar; absent black/white can become0/65535; metadata presence unproved",
        "operation": "((sample-black)*(1.0f32/(white-black)))*green-normalized-as-shot-gain",
        "compiled_sources": compiled_sources(),
    });
    for fields in [radiometry, conventions] {
        let Value::Object(fields) = fields else {
            bail!("derivative metadata assembly");
        };
        metadata
            .as_object_mut()
            .context("derivative metadata object")?
            .extend(fields);
    }
    Ok((mosaic, metadata))
}
struct Lease<'a> {
    frame: Frame,
    live: &'a AtomicUsize,
}
impl Drop for Lease<'_> {
    fn drop(&mut self) {
        self.live.fetch_sub(1, Ordering::SeqCst);
    }
}
struct PreparedDerivative {
    mosaic: Vec<f32>,
    source: Value,
    width: usize,
    height: usize,
}
fn prepare_from_source(
    plan: &InputPlan,
    original: usize,
    decode: impl FnOnce() -> Result<Frame>,
    live: &AtomicUsize,
) -> Result<PreparedDerivative> {
    plan.validate()?;
    plan.selected(original)?;
    ensure!(
        live.load(Ordering::SeqCst) == 0,
        "derivative prior frame still leased"
    );
    let frame = decode()?;
    live.fetch_add(1, Ordering::SeqCst);
    let lease = Lease { frame, live };
    let (mosaic, source) = normalized_active_mosaic(&lease.frame)?;
    let width = lease.frame.active.width;
    let height = lease.frame.active.height;
    drop(lease);
    ensure!(
        live.load(Ordering::SeqCst) == 0,
        "derivative frame lease not dropped"
    );
    Ok(PreparedDerivative {
        mosaic,
        source,
        width,
        height,
    })
}
fn with_released_frame<T>(
    p: &PreparedDerivative,
    live: &AtomicUsize,
    write: impl FnOnce(&PreparedDerivative) -> Result<T>,
) -> Result<T> {
    ensure!(
        live.load(Ordering::SeqCst) == 0,
        "derivative writer reached with a live frame lease"
    );
    write(p)
}
fn write_registration_derivative(
    path: &Path,
    p: &PreparedDerivative,
    live: &AtomicUsize,
) -> Result<FileRef> {
    with_released_frame(p, live, |p| {
        ensure!(!path.exists(), "derivative output already exists");
        image_out::write_demosaiced(
            path,
            p.width,
            p.height,
            &p.mosaic,
            &image_out::Develop::measurement(false),
        )?;
        fs::OpenOptions::new().write(true).open(path)?.sync_all()?;
        file_ref(path, TIFF_LIMIT)
    })
}

fn fixture(signed: bool) -> Frame {
    let (stride, height, ax, ay, w, h) = (40, 32, 2, 4, 30, 22);
    let mut data = vec![65000; stride * height];
    for y in 0..h {
        for x in 0..w {
            let value = if signed {
                192
            } else {
                match ((y & 1), (x & 1)) {
                    (0, 0) => 320 + 4 * x + 8 * y,
                    (1, 1) => 448 - 2 * x + 2 * y,
                    _ => 1088 + 16 * x - 8 * y,
                }
            };
            data[(ay + y) * stride + ax + x] = value as u16;
        }
    }
    if signed {
        for (x, y, value) in [
            (10, 8, 48),
            (0, 0, 2368),
            (29, 0, 576),
            (0, 21, 1088),
            (29, 21, 1472),
        ] {
            data[(ay + y) * stride + ax + x] = value;
        }
    }
    Frame {
        data,
        stride,
        buffer_height: height,
        active: Region {
            x: ax,
            y: ay,
            width: w,
            height: h,
        },
        levels: Levels {
            black: 64.0,
            white: 4160.0,
        },
        iso: Some(160.0),
        wb_coeffs: [2.0, 1.0, 4.0, f32::from_bits(0x7fc00001)],
        xyz_to_cam_rgbe: [[0.0; 3]; 4],
        color_matrices: Vec::new(),
        camera: "M193c synthetic derivative fixture".into(),
        path: PathBuf::from("M193C-NO-SUCH-DERIVATIVE-RAW.ARW"),
    }
}
fn fake_plan() -> InputPlan {
    InputPlan {
        schema: "m193c-registration-input-plan-v1".into(),
        status: "PLAN_ONLY".into(),
        entries: (0..9)
            .map(|i| Entry {
                original_index: ORIGINALS[i],
                name: NAMES[i].into(),
                path: Path::new(CORPUS).join(NAMES[i]),
                bytes: LENGTHS[i],
                sha256: "0".repeat(64),
                mtime_utc: "private metadata-only plan; no RAW authority".into(),
                attributes: 32,
            })
            .collect(),
        build: FileRef {
            path: PathBuf::from("C:/M193C-PRIVATE-NONEXISTENT-EXE"),
            sha256: "0".repeat(64),
            bytes: 1,
        },
        source_bindings: OWNED_NAMES
            .iter()
            .map(|v| (v.to_string(), "0".repeat(64)))
            .collect(),
        settings: Settings {
            purpose: "registration-development-only".into(),
            colour: "linear-camera-native".into(),
            transfer: "identity".into(),
            matrix: Value::Null,
            orientation_applied: false,
            spatial_transform: "identity".into(),
        },
    }
}
fn same_bits(a: &[f32], b: &[f32]) -> bool {
    a.len() == b.len() && a.iter().zip(b).all(|(a, b)| a.to_bits() == b.to_bits())
}
fn malvar_row(mosaic: &[f32], y: usize) -> Vec<f32> {
    let m = Mosaic {
        data: mosaic,
        width: 30,
        height: 22,
    };
    let mut out = vec![0.0; 90];
    demosaic_malvar_row(&m, y, &mut out);
    out
}
fn record(checks: &mut Vec<Value>, id: &str, pass: bool, evidence: Value) {
    checks.push(json!({"id": id, "pass": pass, "evidence": evidence}));
}
fn private_controls(dir: &Path, checks: &mut Vec<Value>) -> Result<()> {
    let base = fixture(false);
    let (baseline, baseline_meta) = normalized_active_mosaic(&base)?;
    record(
        checks,
        "valid-affine",
        validate_frame(&base).is_ok(),
        baseline_meta.clone(),
    );
    let faults: [(&str, &str, fn(&mut Frame)); 21] = [
        ("empty-active", "active extent", |f| f.active.width = 0),
        ("odd-origin-x", "active parity", |f| f.active.x = 3),
        ("odd-origin-y", "active parity", |f| f.active.y = 5),
        ("odd-width", "active parity", |f| f.active.width = 29),
        ("odd-height", "active parity", |f| f.active.height = 21),
        ("stride-storage", "storage length", |f| f.stride = 41),
        ("active-outside", "active containment", |f| f.active.x = 12),
        ("stride-overflow", "storage overflow", |f| {
            f.stride = usize::MAX;
            f.buffer_height = 2;
        }),
        ("axis-bound", "axis bound", |f| f.active.width = 8194),
        ("pixel-bound", "pixel bound", |f| {
            f.active.width = 8000;
            f.active.height = 5000;
        }),
        ("buffer-bound", "buffer bound", |f| {
            f.stride = 10000;
            f.buffer_height = 4001;
        }),
        ("black-nan", "levels", |f| f.levels.black = f32::NAN),
        ("black-negative", "levels", |f| f.levels.black = -1.0),
        ("white-infinity", "levels", |f| {
            f.levels.white = f32::INFINITY
        }),
        ("white-container", "levels", |f| f.levels.white = 65536.0),
        ("zero-range", "levels", |f| f.levels.white = 64.0),
        ("negative-range", "levels", |f| f.levels.white = 63.0),
        ("red-gain-zero", "WB coefficients", |f| f.wb_coeffs[0] = 0.0),
        ("green-gain-zero", "WB coefficients", |f| {
            f.wb_coeffs[1] = 0.0
        }),
        ("blue-gain-nan", "WB coefficients", |f| {
            f.wb_coeffs[2] = f32::NAN
        }),
        ("gain-ratio-overflow", "WB gains", |f| {
            f.wb_coeffs[0] = f32::MAX;
            f.wb_coeffs[1] = f32::MIN_POSITIVE;
        }),
    ];
    for (id, wanted, mutate) in faults {
        let mut f = base.clone();
        mutate(&mut f);
        let error = validate_frame(&f).err().map(|e| format!("{e:#}"));
        let restored = validate_frame(&base).is_ok();
        record(
            checks,
            id,
            error.as_ref().is_some_and(|e| e == wanted) && restored,
            json!({"expected": wanted, "actual": error, "restored": restored}),
        );
    }
    let mut fourth = base.clone();
    fourth.wb_coeffs[3] = f32::from_bits(0xffc00002);
    let (values, metadata) = normalized_active_mosaic(&fourth)?;
    record(
        checks,
        "fourth-wb-null",
        same_bits(&baseline, &values),
        json!({"raw_wb_f32_bits": metadata["raw_wb_f32_bits"]}),
    );
    let mut padding = base.clone();
    for y in 0..padding.buffer_height {
        for x in 0..padding.stride {
            if !(2..32).contains(&x) || !(4..26).contains(&y) {
                padding.data[y * padding.stride + x] = 17;
            }
        }
    }
    let (values, metadata) = normalized_active_mosaic(&padding)?;
    record(
        checks,
        "padding-null",
        same_bits(&baseline, &values)
            && metadata["active_sha256_u16_le"] == baseline_meta["active_sha256_u16_le"],
        json!({"active_sha256_u16_le": metadata["active_sha256_u16_le"]}),
    );
    let mut gain = base.clone();
    gain.wb_coeffs[0] = 3.0;
    let (values, _) = normalized_active_mosaic(&gain)?;
    let r = 8 * 30 + 10;
    let g = r + 1;
    record(
        checks,
        "red-gain-live",
        values[r] != baseline[r] && values[g] == baseline[g],
        json!({"red_before": baseline[r], "red_after": values[r], "green_before": baseline[g], "green_after": values[g]}),
    );
    let signed = fixture(true);
    let (mosaic, _) = normalized_active_mosaic(&signed)?;
    let row = malvar_row(&mosaic, 8);
    let clamped: Vec<_> = mosaic.iter().map(|v| v.max(0.0)).collect();
    let bad = malvar_row(&clamped, 8);
    let restored = malvar_row(&mosaic, 8);
    let delta = bad[11 * 3] - row[11 * 3];
    record(
        checks,
        "black-clamp-live",
        (delta - 1.0 / 256.0).abs() < 1e-7
            && row[11 * 3] > 0.0
            && bad[11 * 3] < 1.0
            && same_bits(&row, &restored),
        json!({"before": row[11 * 3], "early_clamp": bad[11 * 3], "delta": delta, "restored_exact": same_bits(&row, &restored)}),
    );
    let mut unity = signed.clone();
    unity.wb_coeffs = [1.0, 1.0, 1.0, f32::NAN];
    let (unbalanced, _) = normalized_active_mosaic(&unity)?;
    let mut late = malvar_row(&unbalanced, 8);
    for (i, value) in late.iter_mut().enumerate() {
        *value *= [2.0, 1.0, 4.0][i % 3];
    }
    let before = row[10 * 3 + 1].clamp(0.0, 1.0);
    let after = late[10 * 3 + 1].clamp(0.0, 1.0);
    record(
        checks,
        "wb-order-live",
        (before - after).abs() > 1.0 / 512.0 && same_bits(&row, &restored),
        json!({"pre_wb_green": before, "post_wb_green": after, "restored_exact": same_bits(&row, &restored)}),
    );
    let valid = fake_plan();
    let mut wrong = valid.clone();
    wrong.entries[8].original_index = 91;
    let calls = AtomicUsize::new(0);
    let live = AtomicUsize::new(0);
    let denied = prepare_from_source(
        &wrong,
        0,
        || {
            calls.fetch_add(1, Ordering::SeqCst);
            Ok(fixture(false))
        },
        &live,
    )
    .err()
    .map(|e| format!("{e:#}"));
    record(
        checks,
        "nine-plan-before-decode",
        denied.as_deref() == Some("nine input plan") && calls.load(Ordering::SeqCst) == 0,
        json!({"actual": denied, "decode_calls": calls.load(Ordering::SeqCst)}),
    );
    let prepared = prepare_from_source(
        &valid,
        0,
        || {
            calls.fetch_add(1, Ordering::SeqCst);
            Ok(fixture(false))
        },
        &live,
    )?;
    // Exercise the actual consuming writer guard without an extra TIFF call.
    let writer_observed_live =
        with_released_frame(&prepared, &live, |_| Ok(live.load(Ordering::SeqCst)))?;
    live.store(1, Ordering::SeqCst);
    let blocked_writer = with_released_frame(&prepared, &live, |_| -> Result<()> {
        bail!("private writer callback must not be reached with a live lease")
    })
    .err()
    .map(|e| format!("{e:#}"));
    live.store(0, Ordering::SeqCst);
    let restored_writer = with_released_frame(&prepared, &live, |_| Ok(())).is_ok();
    record(
        checks,
        "decode-once-drop-before-write",
        calls.load(Ordering::SeqCst) == 1
            && writer_observed_live == 0
            && same_bits(&baseline, &prepared.mosaic)
            && blocked_writer.as_deref()
                == Some("derivative writer reached with a live frame lease")
            && restored_writer,
        json!({"decode_calls": calls.load(Ordering::SeqCst), "writer_observed_live_leases": writer_observed_live,
            "injected_live_lease_refusal": blocked_writer, "restored_writer": restored_writer}),
    );
    let guard = dir.join("guard.bin");
    fs::write(&guard, b"m193c-before\n")?;
    let bound = file_ref(&guard, 64)?;
    verify_file(&bound, 64)?;
    fs::write(&guard, b"m193c-after!\n")?;
    fs::write(dir.join("guard-mutated.bin"), b"m193c-after!\n")?;
    let rejected = verify_file(&bound, 64).err().map(|e| format!("{e:#}"));
    fs::write(&guard, b"m193c-before\n")?;
    record(
        checks,
        "snapshot-changed",
        rejected.as_deref() == Some("derivative bound file changed")
            && verify_file(&bound, 64).is_ok(),
        json!({"actual": rejected, "restored": file_ref(&guard, 64)?}),
    );
    let publication = dir.join("publication.json");
    let first = json!({"status": "PRIVATE_PROVISIONAL", "error": null, "finalization_errors": []});
    let mut expected_first = serde_json::to_vec_pretty(&first)?;
    expected_first.push(b'\n');
    let mut observed_first = None;
    let refused = publish(&publication, &first, || {
        let initial = read_json_bytes(&publication)?;
        ensure!(
            initial == expected_first,
            "private initial provisional byte mismatch"
        );
        observed_first = Some(initial);
        bail!("private late-finalization source fault")
    });
    let returned_error = refused.as_ref().err().map(|e| format!("{e:#}"));
    let persisted: Value = serde_json::from_slice(&read_json_bytes(&publication)?)?;
    let retained_path = publication.with_extension("first.json");
    let retained_first = read_json_bytes(&retained_path)?;
    record(
        checks,
        "late-publication-revokes",
        returned_error.as_deref() == Some("private late-finalization source fault")
            && persisted["status"] == "REFUSED"
            && persisted["error"] == "private late-finalization source fault"
            && persisted["finalization_errors"]
                == json!(["private late-finalization source fault"])
            && observed_first.as_ref() == Some(&expected_first)
            && retained_first == expected_first,
        json!({"persisted": persisted, "returned_error": returned_error,
            "expected_provisional_sha256": digest(&expected_first),
            "observed_provisional_sha256": observed_first.as_deref().map(digest),
            "retained_first": file_ref(&retained_path, JSON_LIMIT as u64)?,
            "retained_first_matches_initial_bytes": observed_first.as_ref() == Some(&retained_first)}),
    );
    let (again, again_meta) = normalized_active_mosaic(&fixture(false))?;
    record(
        checks,
        "restored-affine",
        same_bits(&baseline, &again) && baseline_meta == again_meta,
        json!({"active_sha256_u16_le": again_meta["active_sha256_u16_le"]}),
    );
    ensure!(checks.len() == 32, "derivative private control cardinality");
    Ok(())
}

fn private_child() -> Result<()> {
    let start = Instant::now();
    let env = environment(false)?;
    let dir = output_dir()?;
    let mut checks = Vec::new();
    let mut outputs = serde_json::Map::new();
    let attempt = (|| -> Result<()> {
        verify_compiled_sources()?;
        private_controls(&dir, &mut checks)?;
        ensure!(
            checks.iter().all(|v| v["pass"] == true),
            "derivative private helper control failed"
        );
        let plan = fake_plan();
        let live = AtomicUsize::new(0);
        for (name, signed) in [("affine", false), ("signed_border", true)] {
            let p = prepare_from_source(&plan, 0, || Ok(fixture(signed)), &live)?;
            let filename = if signed {
                "signed-border.tiff"
            } else {
                "affine.tiff"
            };
            outputs.insert(
                name.into(),
                serde_json::to_value(write_registration_derivative(
                    &dir.join(filename),
                    &p,
                    &live,
                )?)?,
            );
        }
        Ok(())
    })();
    let result = json!({"schema": "m193c-derivative-private-v1",
        "status": if attempt.is_ok() { "COMPLETE_PRIVATE_DERIVATIVE_PRODUCTS_UNVERIFIED" } else { "REFUSED" },
        "checks": checks, "outputs": outputs, "command": std::env::args().collect::<Vec<_>>(),
        "environment": env, "elapsed_seconds": start.elapsed().as_secs_f64(),
        "error": attempt.as_ref().err().map(|e| format!("{e:#}")), "finalization_errors": []});
    let persisted = publish(&dir.join("result.json"), &result, || {
        ensure!(environment(false)? == env, "derivative environment changed");
        verify_compiled_sources()?;
        for value in outputs.values() {
            verify_file(
                &serde_json::from_value::<FileRef>(value.clone())?,
                TIFF_LIMIT,
            )?;
        }
        Ok(())
    });
    if let Err(primary) = attempt {
        if let Err(secondary) = persisted {
            return Err(primary.context(format!("publication: {secondary:#}")));
        }
        return Err(primary);
    }
    persisted
}

fn native_child() -> Result<()> {
    let start = Instant::now();
    let env = environment(true)?;
    let dir = output_dir()?;
    let mut plan_ref = Value::Null;
    let mut snapshot_ref = Value::Null;
    let mut source = Value::Null;
    let mut output = Value::Null;
    let mut actual_plan: Option<InputPlan> = None;
    let mut selected_identity = Value::Null;
    let attempt = (|| -> Result<()> {
        let original_text = std::env::var(format!("{PREFIX}ORIGINAL_INDEX"))?;
        let original: usize = original_text.parse()?;
        ensure!(
            original.to_string() == original_text,
            "derivative original index representation"
        );
        selected_identity = json!(original);
        let plan_path = PathBuf::from(std::env::var(format!("{PREFIX}INPUT_PLAN"))?);
        workspace_file(&plan_path)?;
        let raw = read_json_bytes(&plan_path)?;
        let sha = std::env::var(format!("{PREFIX}INPUT_PLAN_SHA256"))?;
        ensure!(
            hash_form(&sha) && digest(&raw) == sha,
            "derivative input plan external hash"
        );
        let plan: InputPlan = serde_json::from_slice(&raw)?;
        plan.validate()?;
        plan.verify_sources()?;
        plan_ref = json!(FileRef {
            path: plan_path,
            sha256: sha,
            bytes: raw.len() as u64
        });
        let selected = plan.selected(original)?;
        let snapshot = PathBuf::from(std::env::var(format!("{PREFIX}SNAPSHOT"))?);
        workspace_file(&snapshot)?;
        ensure!(
            snapshot.file_name().and_then(|s| s.to_str()) == Some(selected.name.as_str()),
            "derivative snapshot basename"
        );
        let bound = FileRef {
            path: snapshot.clone(),
            sha256: selected.sha256.clone(),
            bytes: selected.bytes,
        };
        verify_file(&bound, RAW_LIMIT)?;
        snapshot_ref = json!(bound);
        let live = AtomicUsize::new(0);
        let calls = AtomicUsize::new(0);
        let p = prepare_from_source(
            &plan,
            original,
            || {
                calls.fetch_add(1, Ordering::SeqCst);
                Ok(strehl_raw::decode(&snapshot)?)
            },
            &live,
        )?;
        ensure!(
            calls.load(Ordering::SeqCst) == 1,
            "derivative actual decode count"
        );
        verify_file(&bound, RAW_LIMIT)?;
        source = p.source.clone();
        source["decode_calls"] = json!(calls.load(Ordering::SeqCst));
        source["live_frame_leases_after_prepare"] = json!(live.load(Ordering::SeqCst));
        let stem = Path::new(&selected.name)
            .file_stem()
            .context("derivative original stem")?
            .to_string_lossy();
        let out_path = dir.join(format!("{stem}-registration.tiff"));
        output = serde_json::to_value(write_registration_derivative(&out_path, &p, &live)?)?;
        plan.verify_sources()?;
        actual_plan = Some(plan);
        Ok(())
    })();
    let result = json!({"schema": "m193c-registration-derivative-v1",
        "status": if attempt.is_ok() { "COMPLETE_REGISTRATION_DERIVATIVE_UNVERIFIED" } else { "REFUSED" },
        "input_plan": plan_ref, "selected": selected_identity, "snapshot": snapshot_ref,
        "source": source, "output": output, "command": std::env::args().collect::<Vec<_>>(),
        "environment": env, "elapsed_seconds": start.elapsed().as_secs_f64(),
        "error": attempt.as_ref().err().map(|e| format!("{e:#}")), "finalization_errors": []});
    let persisted = publish(&dir.join("result.json"), &result, || {
        ensure!(environment(true)? == env, "derivative environment changed");
        if let Some(plan) = &actual_plan {
            plan.verify_sources()?;
        }
        for (value, cap) in [
            (&plan_ref, JSON_LIMIT as u64),
            (&snapshot_ref, RAW_LIMIT),
            (&output, TIFF_LIMIT),
        ] {
            if !value.is_null() {
                verify_file(&serde_json::from_value::<FileRef>(value.clone())?, cap)?;
            }
        }
        Ok(())
    });
    if let Err(primary) = attempt {
        if let Err(secondary) = persisted {
            return Err(primary.context(format!("publication: {secondary:#}")));
        }
        return Err(primary);
    }
    persisted
}

#[test]
#[ignore = "M193c needs frozen source, exact parent command, independent reader and fresh workspace"]
fn m193c_derivative_private() -> Result<()> {
    private_child()
}

#[test]
#[ignore = "M193c needs admitted private controls, fixed nine-input plan, both decoders and explicit native release"]
fn m193c_derivative_native() -> Result<()> {
    native_child()
}
