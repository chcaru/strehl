// M194g test-local noisy-CFA bridge. No alternate production arithmetic.
use super::*;

const GP: &str = "STREHL_M194G_BRIDGE_";
const JSON_CAP: usize = 16 * 1024 * 1024;
const WIDTH: usize = 320;
const HEIGHT: usize = 240;
const RAW_BYTES: usize = WIDTH * HEIGHT * 2;
const SEEDS: [u64; 8] = [701, 709, 719, 727, 733, 739, 743, 751];
const WB: [f32; 3] = [4.0 / 3.0, 1.0, 5.0 / 3.0];
const INTERFACE_SHA: &str = "98048ba64d9f984e6dbba17607b40d6c5899057aa88708b9354e98a40fa131c2";

#[derive(Clone, Debug, PartialEq, Eq, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
struct Ref {
    path: String,
    sha256: String,
    bytes: u64,
}
#[derive(Clone, Debug, PartialEq, Eq, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
struct Array {
    path: String,
    sha256: String,
    bytes: u64,
    dtype: String,
    shape: [usize; 2],
}
impl Array {
    fn file(&self) -> Ref {
        Ref {
            path: self.path.clone(),
            sha256: self.sha256.clone(),
            bytes: self.bytes,
        }
    }
}
#[derive(Clone, Debug, PartialEq, Eq, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
struct Binding {
    sha256: String,
    bytes: u64,
}
#[derive(Clone, Debug, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
struct Admission {
    schema: String,
    status: String,
    ref_root: String,
    manifest: Ref,
    generation_result: Ref,
    independent_read: Ref,
    float_commission: Ref,
    noise_commission: Ref,
}
#[derive(Clone, Debug, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
struct Geometry {
    width: usize,
    height: usize,
    cfa_origin: [usize; 2],
    reference_index: usize,
    frame_indices: [usize; 5],
    inverse_foci: [f64; 5],
    forward_similarity: Forward,
}
#[derive(Clone, Debug, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
struct Forward {
    scale: f64,
    rotation: f64,
    centre: [f64; 2],
    translation: [f64; 2],
}
#[derive(Clone, Debug, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
struct Sensor {
    cfa: String,
    factors_f64: [f64; 4],
    gain_dn_per_e: [f64; 4],
    read_noise_e: [f64; 4],
    black: [u16; 4],
    white: [u16; 4],
    quantization: String,
    wb_rgb_f32: [f64; 3],
}
#[derive(Clone, Debug, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
struct InputFrame {
    index: usize,
    inverse_focus: f64,
    cfa: Array,
    audit: Ref,
}
#[derive(Clone, Debug, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
struct Bundle {
    scene: String,
    noise_enabled: bool,
    seed: Option<u64>,
    frames: Vec<InputFrame>,
}
#[derive(Clone, Debug, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
struct NoiseManifest {
    schema: String,
    status: String,
    ref_root: String,
    upstream_ref_root: String,
    contract: Ref,
    float_commission: Ref,
    noise_commission: Ref,
    runtime: Ref,
    source_bindings: BTreeMap<String, Binding>,
    geometry: Geometry,
    sensor: Sensor,
    bundles: Vec<Bundle>,
}

fn bounded(path: &Path, cap: usize) -> Result<Vec<u8>> {
    let mut bytes = Vec::new();
    fs::File::open(path)?
        .take(cap as u64 + 1)
        .read_to_end(&mut bytes)?;
    ensure!(bytes.len() <= cap, "bridge bounded input exceeds limit");
    Ok(bytes)
}
fn unique(raw: &[u8]) -> Result<Value> {
    Ok(serde_json::from_slice::<UniqueValue>(raw)?.0)
}
fn closed(v: &Value, names: &[&str]) -> Result<()> {
    let m = v.as_object().context("bridge object required")?;
    ensure!(
        m.len() == names.len() && names.iter().all(|k| m.contains_key(*k)),
        "bridge unknown/missing fields"
    );
    Ok(())
}
fn repo() -> Result<PathBuf> {
    Ok(Path::new(env!("CARGO_MANIFEST_DIR"))
        .join("../..")
        .canonicalize()?)
}
fn relative(base: &Path, name: &str) -> Result<PathBuf> {
    ensure!(
        !name.is_empty()
            && !name.contains(['\\', ':'])
            && name
                .split('/')
                .all(|p| !p.is_empty() && p != "." && p != ".."),
        "bridge noncanonical relative path"
    );
    ensure!(
        Path::new(name)
            .components()
            .all(|p| matches!(p, Component::Normal(_))),
        "bridge relative path escapes"
    );
    let base = base.canonicalize()?;
    let path = base.join(name).canonicalize()?;
    ensure!(
        path.starts_with(&base) && path.is_file(),
        "bridge resolved path escapes or is not file"
    );
    Ok(path)
}

// Actual backing identities, not content hashes: distinct flat files may be equal.
#[cfg(windows)]
fn file_identity(path: &Path) -> Result<(u64, u64)> {
    use std::os::windows::io::AsRawHandle;
    #[repr(C)]
    #[derive(Default)]
    struct Info {
        attributes: u32,
        creation: [u32; 2],
        access: [u32; 2],
        write: [u32; 2],
        volume: u32,
        size_high: u32,
        size_low: u32,
        links: u32,
        index_high: u32,
        index_low: u32,
    }
    #[link(name = "kernel32")]
    unsafe extern "system" {
        fn GetFileInformationByHandle(handle: *mut std::ffi::c_void, info: *mut Info) -> i32;
    }
    let file = fs::File::open(path)?;
    let mut info = Info::default();
    // Owned live file handle and correctly sized Win32 output record.
    ensure!(
        unsafe { GetFileInformationByHandle(file.as_raw_handle(), &mut info) } != 0,
        "bridge file identity unavailable"
    );
    Ok((
        u64::from(info.volume),
        (u64::from(info.index_high) << 32) | u64::from(info.index_low),
    ))
}
#[cfg(unix)]
fn file_identity(path: &Path) -> Result<(u64, u64)> {
    use std::os::unix::fs::MetadataExt;
    let m = fs::metadata(path)?;
    Ok((m.dev(), m.ino()))
}

#[derive(Default)]
struct Ledger {
    files: BTreeMap<PathBuf, Binding>,
    identities: BTreeMap<PathBuf, (u64, u64)>,
}
impl Ledger {
    fn raw(&mut self, path: &Path, hash: &str, length: Option<u64>, cap: usize) -> Result<Vec<u8>> {
        valid_hash(hash)?;
        let path = path.canonicalize()?;
        let bytes = bounded(&path, cap)?;
        ensure!(
            digest(&bytes) == hash && length.is_none_or(|n| n == bytes.len() as u64),
            "bridge input hash/length mismatch"
        );
        let b = Binding {
            sha256: hash.into(),
            bytes: bytes.len() as u64,
        };
        let identity = file_identity(&path)?;
        if let Some(old) = self.identities.insert(path.clone(), identity) {
            ensure!(old == identity, "bridge input file identity changed");
        }
        if let Some(old) = self.files.insert(path, b.clone()) {
            ensure!(old == b, "bridge input changed between reads");
        }
        Ok(bytes)
    }
    fn file(&mut self, base: &Path, r: &Ref, cap: usize) -> Result<(PathBuf, Vec<u8>)> {
        ensure!(
            r.bytes > 0 && r.bytes <= cap as u64,
            "bridge reference byte extent"
        );
        let path = relative(base, &r.path)?;
        let raw = self.raw(&path, &r.sha256, Some(r.bytes), cap)?;
        Ok((path, raw))
    }
    fn json(&mut self, base: &Path, r: &Ref) -> Result<(PathBuf, Value)> {
        let (p, b) = self.file(base, r, JSON_CAP)?;
        Ok((p, unique(&b)?))
    }
    fn check(&self) -> Result<()> {
        for (p, b) in &self.files {
            ensure!(
                fs::metadata(p)?.len() == b.bytes && hash_file(p)? == b.sha256,
                "bridge input/source changed before completion"
            );
            ensure!(
                self.identities.get(p) == Some(&file_identity(p)?),
                "bridge input file identity changed before completion"
            );
        }
        Ok(())
    }
    fn sources(&mut self, root: &Path, map: &BTreeMap<String, Binding>) -> Result<()> {
        ensure!(!map.is_empty(), "bridge empty source map");
        for (path, b) in map {
            self.file(
                root,
                &Ref {
                    path: path.clone(),
                    sha256: b.sha256.clone(),
                    bytes: b.bytes,
                },
                JSON_CAP,
            )?;
        }
        Ok(())
    }
}
fn validate_manifest(v: Value) -> Result<NoiseManifest> {
    let m: NoiseManifest = serde_json::from_value(v)?;
    ensure!(
        m.schema == "m194g-software-noise-manifest-v1"
            && m.status == "COMPLETE_NOISE_FILES_UNCOMMISSIONED"
            && m.ref_root == "manifest-parent"
            && m.upstream_ref_root == "repository",
        "bridge manifest schema/status/root"
    );
    let g = &m.geometry;
    ensure!(
        g.width == WIDTH
            && g.height == HEIGHT
            && g.cfa_origin == [0, 0]
            && g.reference_index == 2
            && g.frame_indices == [0, 1, 2, 3, 4]
            && g.inverse_foci == [0.5, 0.625, 0.75, 0.875, 1.0],
        "bridge geometry mismatch"
    );
    let t = &g.forward_similarity;
    ensure!(
        t.scale == 1.0
            && t.rotation == 0.0
            && t.centre == [0.0, 0.0]
            && t.translation == [0.0, 0.0],
        "bridge nonidentity placement"
    );
    let s = &m.sensor;
    ensure!(
        s.cfa == "RGGB"
            && s.factors_f64 == [0.75, 1.0, 1.0, 0.6]
            && s.gain_dn_per_e == [0.25; 4]
            && s.read_noise_e == [4.0; 4]
            && s.black == [512; 4]
            && s.white == [15360; 4]
            && s.quantization == "ties-even-then-clip-[0,15360]"
            && s.wb_rgb_f32 == WB.map(f64::from),
        "bridge sensor/noise/normalization mismatch"
    );
    ensure!(m.bundles.len() == 18, "bridge requires18 bundles");
    for (bi, b) in m.bundles.iter().enumerate() {
        let seed = if bi % 9 == 0 {
            None
        } else {
            Some(SEEDS[bi % 9 - 1])
        };
        ensure!(
            b.scene == if bi < 9 { "textured" } else { "flat" }
                && b.seed == seed
                && b.noise_enabled == seed.is_some()
                && b.frames.len() == 5,
            "bridge bundle identity/order/count mismatch"
        );
        for (i, f) in b.frames.iter().enumerate() {
            ensure!(
                f.index == i
                    && f.inverse_focus == g.inverse_foci[i]
                    && f.cfa.dtype == "<u2"
                    && f.cfa.shape == [HEIGHT, WIDTH]
                    && f.cfa.bytes == RAW_BYTES as u64,
                "bridge frame identity/shape mismatch"
            );
            valid_hash(&f.cfa.sha256)?;
        }
    }
    Ok(m)
}
fn run_record(v: &Value, mode: &str, status: &str) -> Result<()> {
    closed(
        v,
        &[
            "schema",
            "mode",
            "status",
            "invocation",
            "execution_release",
            "runtime",
            "sources_before",
            "sources_after",
            "inputs_before",
            "inputs_after",
            "index",
            "manifest",
            "independent_reader",
            "work",
            "error",
            "finalization_errors",
        ],
    )?;
    ensure!(
        v["schema"] == "m194g-software-noise-run-v1"
            && v["mode"] == mode
            && v["status"] == status
            && v["error"].is_null()
            && v["finalization_errors"] == json!([]),
        "bridge failed generation/commission"
    );
    ensure!(
        v["sources_before"].is_object()
            && v["sources_before"] == v["sources_after"]
            && v["inputs_before"].is_object()
            && v["inputs_before"] == v["inputs_after"],
        "bridge run source/input closure"
    );
    Ok(())
}
fn bind_run_maps(v: &Value, ledger: &mut Ledger, root: &Path) -> Result<()> {
    for k in ["sources_before", "inputs_before"] {
        let m: BTreeMap<String, Binding> = serde_json::from_value(v[k].clone())?;
        ledger.sources(root, &m)?;
    }
    Ok(())
}

#[derive(Clone, Debug, Deserialize)]
#[serde(deny_unknown_fields)]
struct ReadRow {
    scene: String,
    seed: Option<u64>,
    index: usize,
    cfa: Ref,
    audit: Ref,
    minimum: u16,
    maximum: u16,
    noise_off_exact: Option<bool>,
}

// Accepted concrete intended90 reader child; private1186 PASS cannot stand in.
fn validate_intended_read(v: &Value, authority: &Admission) -> Result<Vec<ReadRow>> {
    closed(
        v,
        &[
            "schema",
            "status",
            "ref_root",
            "method",
            "manifest",
            "generation_result",
            "float_commission",
            "noise_commission",
            "execution_release",
            "invocation",
            "sources_before",
            "sources_after",
            "inputs_before",
            "inputs_after",
            "file_count",
            "noise_off_count",
            "noisy_count",
            "files",
            "controls",
            "work",
            "error",
            "finalization_errors",
        ],
    )?;
    ensure!(
        v["schema"] == "m194g-independent-noise-files-read-v1"
            && v["status"] == "PASS_SOFTWARE_NOISE_FILES_ONLY"
            && v["ref_root"] == "repository"
            && v["method"] == "actual-native-cfa-files-v1"
            && v["error"].is_null()
            && v["finalization_errors"] == json!([]),
        "bridge intended-reader schema/status"
    );
    for (key, wanted) in [
        ("manifest", &authority.manifest),
        ("generation_result", &authority.generation_result),
        ("float_commission", &authority.float_commission),
        ("noise_commission", &authority.noise_commission),
    ] {
        let r: Ref = serde_json::from_value(v[key].clone())?;
        ensure!(&r == wanted, "bridge intended-reader authority association");
    }
    for (key, count) in [
        ("file_count", 90),
        ("noise_off_count", 10),
        ("noisy_count", 80),
    ] {
        ensure!(
            v[key].as_u64() == Some(count),
            "bridge intended-reader population count/type"
        );
    }
    ensure!(
        v["sources_before"].is_object()
            && v["sources_before"] == v["sources_after"]
            && v["inputs_before"].is_object()
            && v["inputs_before"] == v["inputs_after"],
        "bridge intended-reader changed source/input"
    );
    closed(&v["controls"], &["check_count", "checks"])?;
    let checks = v["controls"]["checks"]
        .as_array()
        .context("bridge intended checks list")?;
    ensure!(
        !checks.is_empty() && v["controls"]["check_count"].as_u64() == Some(checks.len() as u64),
        "bridge intended controls count/type"
    );
    let mut names = BTreeSet::new();
    for c in checks {
        closed(c, &["name", "pass", "evidence"])?;
        let name = c["name"].as_str().context("bridge intended control name")?;
        ensure!(
            !name.is_empty() && names.insert(name) && c["pass"].as_bool() == Some(true),
            "bridge intended controls failed/duplicate"
        );
    }
    let rows: Vec<ReadRow> = serde_json::from_value(v["files"].clone())?;
    ensure!(rows.len() == 90, "bridge intended rows incomplete");
    for (n, row) in rows.iter().enumerate() {
        let bundle = n / 5;
        let seed = if bundle % 9 == 0 {
            None
        } else {
            Some(SEEDS[bundle % 9 - 1])
        };
        ensure!(
            row.scene == if bundle < 9 { "textured" } else { "flat" }
                && row.seed == seed
                && row.index == n % 5
                && row.minimum <= row.maximum
                && row.maximum <= 15360
                && row.noise_off_exact == if seed.is_none() { Some(true) } else { None },
            "bridge intended row order/range/exactness"
        );
    }
    Ok(rows)
}

fn associate_read_row(
    row: &ReadRow,
    b: &Bundle,
    f: &InputFrame,
    cfa: &Path,
    audit: &Path,
    raw: &[u8],
    root: &Path,
) -> Result<()> {
    ensure!(
        row.scene == b.scene && row.seed == b.seed && row.index == f.index,
        "bridge reader/manifest tuple"
    );
    ensure!(
        relative(root, &row.cfa.path)? == cfa
            && row.cfa.sha256 == f.cfa.sha256
            && row.cfa.bytes == f.cfa.bytes
            && relative(root, &row.audit.path)? == audit
            && row.audit.sha256 == f.audit.sha256
            && row.audit.bytes == f.audit.bytes,
        "bridge reader/manifest payload association"
    );
    ensure!(raw.len() == RAW_BYTES, "bridge reader payload extent");
    let values = raw
        .as_chunks::<2>()
        .0
        .iter()
        .map(|p| u16::from_le_bytes(*p));
    ensure!(
        values.clone().min() == Some(row.minimum) && values.max() == Some(row.maximum),
        "bridge reader extrema differ from actual CFA"
    );
    Ok(())
}

struct Inputs {
    manifest: NoiseManifest,
    authority: Admission,
    ledger: Ledger,
    bundle_root: PathBuf,
    authority_sha: String,
}
impl Inputs {
    fn load(path: &Path, sha: &str) -> Result<Self> {
        ensure!(
            path.is_absolute(),
            "bridge external admission path must be absolute"
        );
        let root = repo()?;
        let mut ledger = Ledger::default();
        ledger.raw(
            &root.join("experiments/m194g-larger-pupil/software-noise-interface.md"),
            INTERFACE_SHA,
            None,
            JSON_CAP,
        )?;
        let authority: Admission =
            serde_json::from_value(unique(&ledger.raw(path, sha, None, JSON_CAP)?)?)?;
        ensure!(
            authority.schema == "m194g-software-noise-admission-v1"
                && authority.status == "PASS_SOFTWARE_NOISE_FILES_ONLY"
                && authority.ref_root == "repository",
            "bridge requires genuine noise-file admission"
        );
        let (mp, mv) = ledger.json(&root, &authority.manifest)?;
        let manifest = validate_manifest(mv)?;
        ensure!(
            manifest.float_commission == authority.float_commission
                && manifest.noise_commission == authority.noise_commission,
            "bridge upstream authority association"
        );
        let (gp, generation) = ledger.json(&root, &authority.generation_result)?;
        run_record(
            &generation,
            "intended",
            "COMPLETE_NOISE_FILES_UNCOMMISSIONED",
        )?;
        let gr: Ref = serde_json::from_value(generation["manifest"].clone())?;
        ensure!(
            ledger
                .file(gp.parent().context("generation parent")?, &gr, JSON_CAP)?
                .0
                == mp,
            "bridge generation manifest association"
        );
        let recorded: BTreeMap<String, Binding> =
            serde_json::from_value(generation["sources_before"].clone())?;
        ensure!(
            recorded == manifest.source_bindings,
            "bridge generation source association"
        );
        bind_run_maps(&generation, &mut ledger, &root)?;
        let (_, reader) = ledger.json(&root, &authority.independent_read)?;
        let read_rows = validate_intended_read(&reader, &authority)?;
        bind_run_maps(&reader, &mut ledger, &root)?;
        let (_, floats) = ledger.json(&root, &authority.float_commission)?;
        ensure!(
            floats["schema"] == "m194g-float-commission-v1"
                && floats["status"] == "PASS_COMPLETE_FLOAT_MODEL",
            "bridge full-float prerequisite failed"
        );
        let (np, noise) = ledger.json(&root, &authority.noise_commission)?;
        run_record(&noise, "commission", "PASS_SOFTWARE_NOISE_COMMISSION")?;
        bind_run_maps(&noise, &mut ledger, &root)?;
        let wrapper: Ref = serde_json::from_value(noise["independent_reader"].clone())?;
        let (wp, w) = ledger.json(np.parent().context("noise parent")?, &wrapper)?;
        closed(&w, &["schema", "status", "read", "controls"])?;
        ensure!(
            w["schema"] == "m194g-software-noise-reader-command-v1"
                && w["status"] == "PASS_SOFTWARE_NOISE_PRIVATE_TRACES",
            "bridge noise component wrapper failed"
        );
        for (key, schema, status) in [
            (
                "read",
                "m194g-independent-software-noise-reader-v1",
                "PASS_SOFTWARE_NOISE_PRIVATE_TRACES",
            ),
            (
                "controls",
                "m194g-independent-noise-reader-controls-v1",
                "PASS_INDEPENDENT_NOISE_READER_CONTROLS",
            ),
        ] {
            let r: Ref = serde_json::from_value(w[key].clone())?;
            let (_, child) = ledger.json(wp.parent().context("noise wrapper parent")?, &r)?;
            ensure!(
                child["schema"] == schema && child["status"] == status,
                "bridge failed noise component child"
            );
        }
        let base = mp.parent().context("manifest parent")?.to_path_buf();
        ledger.file(&base, &manifest.contract, JSON_CAP)?;
        ledger.file(&base, &manifest.runtime, JSON_CAP)?;
        ledger.sources(&root, &manifest.source_bindings)?;
        let mut paths = BTreeSet::new();
        let mut ids = BTreeSet::new();
        for (bi, b) in manifest.bundles.iter().enumerate() {
            for (fi, f) in b.frames.iter().enumerate() {
                let (p, raw) = ledger.file(&base, &f.cfa.file(), RAW_BYTES)?;
                ensure!(
                    paths.insert(p.to_string_lossy().to_lowercase())
                        && ids.insert(file_identity(&p)?),
                    "bridge duplicate actual CFA identity"
                );
                ensure!(
                    raw.as_chunks::<2>()
                        .0
                        .iter()
                        .all(|p| u16::from_le_bytes(*p) <= 15360),
                    "bridge CFA outside rails"
                );
                let (audit_path, audit) = ledger.json(&base, &f.audit)?;
                associate_read_row(&read_rows[bi * 5 + fi], b, f, &p, &audit_path, &raw, &root)?;
                closed(
                    &audit,
                    &[
                        "input",
                        "phase",
                        "fault_id",
                        "observer_mode",
                        "streams",
                        "derived_hashes",
                        "rail_counts",
                        "witness",
                        "q_sha256",
                    ],
                )?;
                ensure!(
                    audit["q_sha256"] == f.cfa.sha256
                        && audit["phase"] == "baseline"
                        && audit["fault_id"].is_null()
                        && audit["observer_mode"] == "off",
                    "bridge CFA/audit association"
                );
                closed(
                    &audit["input"],
                    &[
                        "scene",
                        "seed",
                        "frame_index",
                        "width",
                        "height",
                        "scalar_level",
                        "expected_scalar_sha256",
                    ],
                )?;
                let input = &audit["input"];
                ensure!(
                    input["scene"] == b.scene
                        && input["seed"] == json!(b.seed)
                        && input["frame_index"].as_u64() == Some(f.index as u64)
                        && input["width"].as_u64() == Some(WIDTH as u64)
                        && input["height"].as_u64() == Some(HEIGHT as u64)
                        && input["scalar_level"]
                            == if b.scene == "flat" {
                                json!(12000)
                            } else {
                                Value::Null
                            },
                    "bridge audit input tuple"
                );
            }
        }
        ledger.check()?;
        Ok(Self {
            manifest,
            authority,
            ledger,
            bundle_root: base,
            authority_sha: sha.into(),
        })
    }
    fn selected(&self, s: &Settings) -> Result<Vec<InputFrame>> {
        let b = self
            .manifest
            .bundles
            .iter()
            .find(|b| b.scene == s.scene && b.seed == s.seed)
            .context("bridge unknown selected tuple")?;
        Ok(s.indices().iter().map(|&i| b.frames[i].clone()).collect())
    }
}

#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize)]
#[serde(rename_all = "kebab-case")]
enum Observer {
    Off,
    Count,
    Placebo,
}
#[derive(Clone, Debug)]
struct Settings {
    scene: String,
    seed: Option<u64>,
    subset: String,
    admission: AdmissionMode,
    observer: Observer,
}
impl Settings {
    fn validate(&self) -> Result<()> {
        ensure!(
            matches!(self.scene.as_str(), "flat" | "textured")
                && self.seed.is_none_or(|s| SEEDS.contains(&s)),
            "bridge unregistered scene/seed"
        );
        ensure!(
            matches!(self.subset.as_str(), "all" | "first" | "last"),
            "bridge unknown subset"
        );
        ensure!(
            self.subset == "all"
                || (self.scene == "textured"
                    && self.seed.is_none()
                    && self.admission == AdmissionMode::HardFloor),
            "bridge endpoints require noiseless textured HardFloor"
        );
        Ok(())
    }
    fn indices(&self) -> Vec<usize> {
        match self.subset.as_str() {
            "first" => vec![0],
            "last" => vec![4],
            _ => vec![0, 1, 2, 3, 4],
        }
    }
}
fn levels() -> Levels {
    Levels {
        black: 512.0,
        white: 15360.0,
    }
}
fn noise() -> NoiseModel {
    NoiseModel::new(
        [PlaneNoise {
            gain_dn_per_e: 0.25,
            read_noise_e: 4.0,
            levels: levels(),
        }; 4],
        160.0,
        NoiseProvenance::Fallback,
    )
}
fn sentinel(i: usize) -> PathBuf {
    PathBuf::from(format!("M194G-NO-SUCH-RAW-{i}.ARW"))
}
fn frame(data: Vec<u16>, original: usize) -> Frame {
    Frame {
        data,
        stride: WIDTH,
        buffer_height: HEIGHT,
        active: Region {
            x: 0,
            y: 0,
            width: WIDTH,
            height: HEIGHT,
        },
        levels: levels(),
        iso: Some(160.0),
        wb_coeffs: [WB[0], WB[1], WB[2], f32::NAN],
        xyz_to_cam_rgbe: [[0.0; 3]; 4],
        color_matrices: Vec::new(),
        camera: "M194g synthetic software-noise input".into(),
        path: sentinel(original),
    }
}
struct Source {
    paths: Vec<PathBuf>,
    hashes: Vec<String>,
    original: Vec<usize>,
    observer: Observer,
    calls: Vec<AtomicUsize>,
    hooks: AtomicUsize,
    attempts: Vec<AtomicUsize>,
    fail: Option<(usize, usize)>,
}
impl Source {
    fn new(
        paths: Vec<PathBuf>,
        hashes: Vec<String>,
        original: Vec<usize>,
        observer: Observer,
    ) -> Result<Self> {
        ensure!(
            !paths.is_empty() && paths.len() == hashes.len() && paths.len() == original.len(),
            "bridge source lengths"
        );
        let mut ids = BTreeSet::new();
        let mut originals = BTreeSet::new();
        for ((p, h), &i) in paths.iter().zip(&hashes).zip(&original) {
            valid_hash(h)?;
            ensure!(
                ids.insert(file_identity(p)?) && i < 5 && originals.insert(i),
                "bridge source duplicate/outside identity"
            );
        }
        let n = paths.len();
        Ok(Self {
            paths,
            hashes,
            original,
            observer,
            calls: (0..n).map(|_| AtomicUsize::new(0)).collect(),
            hooks: AtomicUsize::new(0),
            attempts: (0..n).map(|_| AtomicUsize::new(0)).collect(),
            fail: None,
        })
    }
    fn counts(&self) -> Vec<usize> {
        self.calls
            .iter()
            .map(|c| c.load(Ordering::SeqCst))
            .collect()
    }
}
impl PyramidFrameSource for Source {
    fn len(&self) -> usize {
        self.paths.len()
    }
    fn decode(&self, index: usize) -> Result<Frame> {
        let p = self.paths.get(index).context("bridge decode index")?;
        if let Some(fail) = self.fail {
            let attempt = self.attempts[index].fetch_add(1, Ordering::SeqCst) + 1;
            ensure!(
                fail != (index, attempt),
                "M194g injected decode failure index{index} attempt{attempt}"
            );
        }
        let raw = bounded(p, RAW_BYTES)?;
        ensure!(
            raw.len() == RAW_BYTES && digest(&raw) == self.hashes[index],
            "bridge decode CFA hash/length"
        );
        let data: Vec<u16> = raw
            .as_chunks::<2>()
            .0
            .iter()
            .map(|p| u16::from_le_bytes(*p))
            .collect();
        ensure!(
            data.iter().all(|&v| v <= 15360),
            "bridge decode rail violation"
        );
        let value = frame(data, self.original[index]);
        if self.observer != Observer::Off {
            self.hooks.fetch_add(1, Ordering::SeqCst);
            if self.observer == Observer::Count {
                self.calls[index].fetch_add(1, Ordering::SeqCst);
            }
        }
        Ok(value)
    }
}
fn map(full: PlaneGeometry, original: &[usize]) -> WarpMap {
    let names: Vec<_> = original
        .iter()
        .map(|&i| sentinel(i).to_string_lossy().into_owned())
        .collect();
    let entries: Vec<_> = names
        .iter()
        .map(|s| (s.as_str(), RAW_BYTES as u64))
        .collect();
    WarpMap::new(
        WarpProvenance {
            stack: StackIdentity::from_entries("M194g admitted selected CFA", &entries),
            strategy: "supplied identity; no alignment solve".into(),
            heldout_px: None,
            cycle_floor_px: None,
            reference: if original.len() == 1 { 0 } else { 2 },
            note: "reference2 coordinate gauge; selected local indices seed probe".into(),
        },
        full,
        Resampler::CatmullRom,
        original
            .iter()
            .map(|_| FrameWarp::Placed(Similarity::IDENTITY))
            .collect(),
    )
}
fn prepared(s: &Settings) -> Result<(PyramidDomain, align_cmd::CoverFit, Value)> {
    s.validate()?;
    ensure!(
        MergeConfig::default().admission == AdmissionMode::HardFloor,
        "bridge default admission changed"
    );
    let full = PlaneGeometry::from_active(WIDTH, HEIGHT);
    let original = s.indices();
    let (_, fit) = align_cmd::cover_or_explain(map(full, &original), align_cmd::CoverMode::Crop);
    let domain = pyramid_domain(full, align_cmd::CoverMode::Crop, Some(&fit))?;
    let (_, all_fit) =
        align_cmd::cover_or_explain(map(full, &[0, 1, 2, 3, 4]), align_cmd::CoverMode::Crop);
    let all = pyramid_domain(full, align_cmd::CoverMode::Crop, Some(&all_fit))?;
    ensure!(domain == all, "bridge endpoint/five-frame crop mismatch");
    let sizes = level_sizes(domain.rect.width, domain.rect.height, 3);
    ensure!(
        sizes.len() == 4,
        "bridge needs three Laplacian bands plus base"
    );
    let rect = domain.rect;
    let geometric = json!({"full_native":[WIDTH,HEIGHT],"full_quad":[full.width,full.height],"crop_quad":{"x":rect.x,"y":rect.y,"width":rect.width,"height":rect.height},"canonical_native_offset":[2*rect.x,2*rect.y],"output_native":[2*rect.width,2*rect.height],"reference_coordinate_gauge":2,"reference_local_index":if original.len()==1{0}else{2},"level_sizes":sizes.iter().map(|s|[s.width,s.height]).collect::<Vec<_>>(),"placements":original.iter().enumerate().map(|(local,&index)|json!({"original_index":index,"local_index":local,"probe_seed_index":local,"quad_similarity":{"a_re":1.0,"a_im":0.0,"b_re":0.0,"b_im":0.0}})).collect::<Vec<_>>()});
    Ok((domain, fit, geometric))
}
fn opts(path: PathBuf, s: &Settings) -> Result<MergeOptions> {
    s.validate()?;
    let mut o = options(path);
    o.dir = PathBuf::from("M194G-NO-RAW-DIRECTORY");
    o.pyramid.admission = s.admission;
    Ok(o)
}
fn plan(
    input: &Inputs,
    s: &Settings,
    env: &BTreeMap<String, String>,
) -> Result<(PyramidDomain, align_cmd::CoverFit, Value)> {
    let (domain, fit, geometry) = prepared(s)?;
    let cfg = opts(PathBuf::new(), s)?.pyramid;
    let config = json!({"merge":"Pyramid","bands":cfg.bands,"gate":cfg.gate,"exponent":cfg.exponent,"sharpen_per_octave":cfg.sharpen_per_octave,"admission":format!("{:?}",cfg.admission),"select":format!("{:?}",cfg.select),"base":format!("{:?}",cfg.base),"mean_coarse":cfg.mean_coarse,"hull":format!("{:?}",cfg.hull),"hull_lambda":cfg.hull_lambda,"hull_low_only":cfg.hull_low_only,"hull_from_level":cfg.hull_from_level,"fallback":format!("{:?}",cfg.fallback),"fallback_k":cfg.fallback_k,"fallback_power":cfg.fallback_power,"significance_scale":cfg.significance_scale,"resampler":"CatmullRom","demosaic":"MHC","space":"CameraLinear","fullres_gather":true,"exposure_stops":0,"auto_exposure":false,"confidence":false,"photometric":"Off","gate_floor_enabled":gatefloor::enabled(),"floor_scale":"unset","ca":"off","defect":"off","restoration":"unset"});
    let exe = std::env::current_exe()?;
    let injected = json!({"iso":160.0,"gain_dn_per_e":vec![0.25;4],"read_noise_e":vec![4.0;4],"provenance":"Fallback: injected synthetic algorithm coefficients; not physical calibration","prnu":false});
    let normalization = json!({"tiff_u16_to_dn":14848.0/65535.0,"second_black_subtraction":false,"input_rounding":"ties-even-then-clip-[0,15360]","output_rounding":"half-up after clipping"});
    let result = json!({"schema":"m194g-noise-consumer-plan-v1","noise_admission_sha256":input.authority_sha,"authority":input.authority,"input_bindings":input.ledger.files,"selected":{"scene":s.scene,"noise_enabled":s.seed.is_some(),"seed":s.seed,"subset":s.subset,"frames":input.selected(s)?},"geometry":geometry,"sensor":input.manifest.sensor,"config":config,"injected_noise":injected,"wb_f32":WB,"frame_wb_f32":WB,"normalization":normalization,"observer":{"mode":s.observer,"excludes_planning_reads":true,"excludes_raw_prologue":true},"floor_witness":{"source":"actual terminal stderr","eligible_prefix_maximum":2,"required":"finite nonempty prefix and count equal selected frames","unmeasured":"existing white-floor fallback"},"environment":env,"build":{"sha256":hash_file(&exe)?,"bytes":fs::metadata(&exe)?.len(),"software":crate::SOFTWARE}});
    Ok((domain, fit, result))
}
fn run_source(output: PathBuf, s: &Settings, source: &impl PyramidFrameSource) -> Result<()> {
    let (domain, fit, _) = prepared(s)?;
    let indices = s.indices();
    ensure!(
        source.len() == indices.len(),
        "bridge selected source count mismatch"
    );
    let paths: Vec<_> = indices.iter().map(|&i| sentinel(i)).collect();
    ensure!(
        paths.iter().all(|p| !p.exists()),
        "bridge RAW sentinel exists"
    );
    let o = opts(output, s)?;
    run_pyramid_prepared(
        &o,
        PreparedPyramid {
            paths: &paths,
            geom: domain.full,
            levels: levels(),
            noise: noise(),
            wb: Some(WB),
            xyz_to_cam: None,
            frame_bytes: RAW_BYTES,
            alignment: Some((map(domain.full, &indices), "M194g supplied identity", fit)),
            domain,
            sizes: level_sizes(domain.rect.width, domain.rect.height, 3),
            defect_plan: None,
            prologue_secs: 0.0,
            align_secs: 0.0,
            t_start: Instant::now(),
            exposure: Exposure::resolve(false, 0.0, false)?,
        },
        source,
    )
}
fn environment() -> Result<BTreeMap<String, String>> {
    let required = [
        ("STREHL_DEFECT", "off"),
        ("STREHL_FIX_CA", "off"),
        ("STREHL_FULLRES_GATHER", "1"),
        ("STREHL_PYRAMID_WORKERS", "2"),
        ("RAYON_NUM_THREADS", "2"),
    ];
    for (k, v) in required {
        ensure!(
            std::env::var(k).as_deref() == Ok(v),
            "bridge required {k}={v}"
        );
    }
    let allowed = [
        "MODE",
        "NOISE_ADMISSION",
        "NOISE_ADMISSION_SHA256",
        "SCENE",
        "SEED",
        "SUBSET",
        "ADMISSION",
        "OBSERVER",
        "PLAN",
        "PLAN_SHA256",
        "OUTPUT",
        "RECEIPT",
        "PRIVATE_OUTPUT",
    ];
    for (k, _) in std::env::vars() {
        if k.to_ascii_uppercase().starts_with("STREHL_") {
            if let Some(s) = k.strip_prefix(GP) {
                ensure!(
                    allowed.contains(&s),
                    "bridge unknown namespaced environment"
                );
            } else {
                ensure!(
                    required.iter().any(|(r, _)| k == *r),
                    "bridge forbidden render override {k}"
                );
            }
        }
    }
    ensure!(gatefloor::enabled(), "bridge requires measured floor");
    Ok(required
        .into_iter()
        .map(|(k, v)| (k.into(), v.into()))
        .collect())
}
fn env(k: &str) -> Result<String> {
    std::env::var(format!("{GP}{k}")).with_context(|| format!("missing {GP}{k}"))
}
fn settings() -> Result<Settings> {
    let seed = match env("SEED")?.as_str() {
        "noise-off" => None,
        s => Some(s.parse::<u64>().context("bridge seed integer")?),
    };
    let admission = match env("ADMISSION")?.as_str() {
        "hard-floor" => AdmissionMode::HardFloor,
        "floor-pedestal-v1" => AdmissionMode::FloorPedestalV1,
        _ => bail!("bridge unregistered admission"),
    };
    let observer = match env("OBSERVER")?.as_str() {
        "off" => Observer::Off,
        "count" => Observer::Count,
        "placebo" => Observer::Placebo,
        _ => bail!("bridge unknown observer"),
    };
    let s = Settings {
        scene: env("SCENE")?,
        seed,
        subset: env("SUBSET")?,
        admission,
        observer,
    };
    s.validate()?;
    Ok(s)
}
fn tiff(path: &Path) -> Result<Value> {
    let raw = bounded(path, 1024 * 1024)?;
    let mut d = tiff::decoder::Decoder::new(std::io::Cursor::new(raw))?;
    let (w, h) = d.dimensions()?;
    output_dimensions(w, h)?;
    ensure!(
        d.colortype()? == tiff::ColorType::RGB(16),
        "bridge output is not RGB16"
    );
    let software = d.get_tag_ascii_string(tiff::tags::Tag::Software)?;
    let tiff::decoder::DecodingResult::U16(p) = d.read_image()? else {
        bail!("bridge TIFF not u16")
    };
    ensure!(p.len() == w as usize * h as usize * 3, "bridge TIFF extent");
    let mut hasher = Sha256::new();
    for v in p {
        hasher.update(v.to_le_bytes());
    }
    Ok(
        json!({"path":path.canonicalize()?,"sha256":hash_file(path)?,"bytes":fs::metadata(path)?.len(),"width":w,"height":h,"channels":3,"sample_type":"u16","pixel_sha256_le":hex(&hasher.finalize()),"software":software}),
    )
}
fn output_dimensions(w: u32, h: u32) -> Result<()> {
    ensure!(
        (1..=WIDTH as u32).contains(&w) && (1..=HEIGHT as u32).contains(&h),
        "bridge TIFF dimensions exceed bounded output"
    );
    Ok(())
}
fn new_paths(paths: &[PathBuf]) -> Result<()> {
    let mut unique = BTreeSet::new();
    for path in paths {
        ensure!(
            path.is_absolute() && !path.exists(),
            "bridge output path must be absolute and new"
        );
        let name = path.file_name().context("bridge output filename")?;
        let parent = path
            .parent()
            .context("bridge output parent")?
            .canonicalize()?;
        ensure!(
            parent.is_dir() && unique.insert(parent.join(name).to_string_lossy().to_lowercase()),
            "bridge output paths alias"
        );
    }
    Ok(())
}
fn check_output(path: &Path, image: &Value) -> Result<()> {
    ensure!(
        fs::metadata(path)?.len()
            == image["bytes"]
                .as_u64()
                .context("bridge output bytes type")?
            && hash_file(path)?
                == image["sha256"]
                    .as_str()
                    .context("bridge output hash type")?,
        "bridge output changed before completion"
    );
    Ok(())
}
fn publish_receipt(path: &Path, result: &Value, check: impl Fn() -> Result<()>) -> Result<()> {
    check()?;
    write_json_new(path, result)?;
    if let Err(primary) = check() {
        let mut secondary = Vec::new();
        let rejected = path.with_extension("rejected.json");
        if rejected.exists() {
            secondary.push("rejected receipt path already exists".into());
        } else if let Err(e) = fs::rename(path, &rejected) {
            secondary.push(format!("retain receipt: {e}"));
        }
        let failed = json!({"schema":"m194g-noise-consumer-receipt-v1","status":"UNCOMMISSIONED_BRIDGE","error":format!("{primary:#}"),"secondary_errors":secondary});
        // This path was created by this call. If rename failed, replace its
        // rejected success in place; failure to revoke cannot hide the error.
        match serde_json::to_vec_pretty(&failed) {
            Ok(bytes) => {
                if let Err(e) = fs::write(path, bytes) {
                    secondary.push(format!("revoke receipt: {e}"));
                }
            }
            Err(e) => secondary.push(format!("serialize refusal: {e}")),
        }
        return Err(if secondary.is_empty() {
            primary
        } else {
            primary.context(format!(
                "secondary receipt finalization errors: {}",
                secondary.join("; ")
            ))
        });
    }
    Ok(())
}
fn execute() -> Result<()> {
    let environment = environment()?;
    let s = settings()?;
    let inputs = Inputs::load(
        Path::new(&env("NOISE_ADMISSION")?),
        &env("NOISE_ADMISSION_SHA256")?,
    )?;
    let (_, _, p) = plan(&inputs, &s, &environment)?;
    let pp = PathBuf::from(env("PLAN")?);
    ensure!(pp.is_absolute(), "bridge plan path must be absolute");
    let mode = env("MODE")?;
    if mode == "plan" {
        new_paths(std::slice::from_ref(&pp))?;
        inputs.ledger.check()?;
        write_json_new(&pp, &p)?;
        inputs.ledger.check()?;
        return Ok(());
    }
    ensure!(mode == "render", "bridge mode must be plan/render");
    let mut extra = Ledger::default();
    let ph = env("PLAN_SHA256")?;
    validate_plan(&unique(&extra.raw(&pp, &ph, None, JSON_CAP)?)?, &p)?;
    let output = PathBuf::from(env("OUTPUT")?);
    let receipt = PathBuf::from(env("RECEIPT")?);
    new_paths(&[output.clone(), receipt.clone()])?;
    let selected = inputs.selected(&s)?;
    let source = Source::new(
        selected
            .iter()
            .map(|f| relative(&inputs.bundle_root, &f.cfa.path))
            .collect::<Result<_>>()?,
        selected.iter().map(|f| f.cfa.sha256.clone()).collect(),
        s.indices(),
        s.observer,
    )?;
    run_source(output.clone(), &s, &source)?;
    let n = source.len();
    let hooks = source.hooks.load(Ordering::SeqCst);
    ensure!(
        source.counts() == vec![usize::from(s.observer == Observer::Count); n]
            && hooks == if s.observer == Observer::Off { 0 } else { n },
        "bridge actual decode observer mismatch"
    );
    let image = tiff(&output)?;
    ensure!(
        image["width"] == p["geometry"]["output_native"][0]
            && image["height"] == p["geometry"]["output_native"][1],
        "bridge output/plan dimensions"
    );
    let result = json!({"schema":"m194g-noise-consumer-receipt-v1","status":"COMPLETE_RGB_UNVERIFIED","plan_sha256":ph,"plan":p,"successful_decode_counts":source.counts(),"hook_calls":hooks,"output":image,"inputs_unchanged":true,"floor_witness":"bound terminal stderr requires independent read; no exact beta authority"});
    publish_receipt(&receipt, &result, || {
        inputs.ledger.check()?;
        extra.check()?;
        check_output(&output, &image)
    })
}
fn validate_plan(saved: &Value, recomputed: &Value) -> Result<()> {
    ensure!(
        saved == recomputed,
        "bridge trusted plan differs from recomputed config"
    );
    Ok(())
}
#[test]
#[ignore = "M194g requires externally admitted90 CFA files and frozen command"]
fn m194g_noise_production_bridge() -> Result<()> {
    execute()
}

mod private_controls {
    use super::*;
    fn dir(name: &str) -> Result<PathBuf> {
        let root = PathBuf::from(env("PRIVATE_OUTPUT")?);
        fs::create_dir_all(&root)?;
        let p = root.join(name);
        fs::create_dir(&p)?;
        Ok(p)
    }
    fn source_at(root: &Path, data: &[u16], mode: Observer) -> Result<Source> {
        let raw: Vec<u8> = data.iter().flat_map(|v| v.to_le_bytes()).collect();
        let mut paths = Vec::new();
        for i in 0..5 {
            let p = root.join(format!("{i}.cfa"));
            fs::write(&p, &raw)?;
            paths.push(p);
        }
        Source::new(paths, vec![digest(&raw); 5], vec![0, 1, 2, 3, 4], mode)
    }
    fn baseline() -> Settings {
        Settings {
            scene: "textured".into(),
            seed: None,
            subset: "all".into(),
            admission: AdmissionMode::HardFloor,
            observer: Observer::Off,
        }
    }
    fn refuses<T>(r: Result<T>, text: &str) {
        let e = r.err().expect("required actual refusal");
        assert!(format!("{e:#}").contains(text), "wrong refusal: {e:#}");
    }
    #[test]
    fn m194g_private_source_rails_and_fault() -> Result<()> {
        let root = dir("rails")?;
        let mut data = vec![1000; WIDTH * HEIGHT];
        for (i, v) in [0, 511, 512, 15360].into_iter().enumerate() {
            data[71 + i] = v;
        }
        let mut source = source_at(&root, &data, Observer::Count)?;
        let decoded = source.decode(3)?;
        assert_eq!(decoded.data, data);
        assert_eq!(source.counts(), [0, 0, 0, 1, 0]);
        source.fail = Some((3, 2));
        source.decode(3)?;
        refuses(source.decode(3), "injected decode failure index3 attempt2");
        assert_eq!(source.counts(), [0, 0, 0, 2, 0]);
        let mut bad = data.clone();
        bad[3911] = 15361;
        let raw: Vec<_> = bad.iter().flat_map(|v| v.to_le_bytes()).collect();
        fs::write(&source.paths[1], &raw)?;
        refuses(source.decode(1), "decode CFA hash/length");
        source.hashes[1] = digest(&raw);
        refuses(source.decode(1), "decode rail violation");
        assert_eq!(source.counts(), [0, 0, 0, 2, 0]);
        Ok(())
    }
    #[test]
    fn m194g_private_bounded_json_paths_aliases() -> Result<()> {
        let root = dir("json-paths")?;
        let file = root.join("large");
        fs::write(&file, [0u8; 18])?;
        assert_eq!(bounded(&file, 18)?.len(), 18);
        refuses(bounded(&file, 17), "bounded input");
        refuses(unique(br#"{"x":1,"x":2}"#), "duplicate JSON key");
        for s in ["../large", "/large", "x/../large", "x\\large", "C:large"] {
            assert!(relative(&root, s).is_err());
        }
        let first = root.join("a.cfa");
        let other = root.join("b.cfa");
        let alias = root.join("alias.cfa");
        fs::write(&first, [0, 0])?;
        fs::write(&other, [0, 0])?;
        fs::hard_link(&first, &alias)?;
        assert_ne!(file_identity(&first)?, file_identity(&other)?);
        assert_eq!(file_identity(&first)?, file_identity(&alias)?);
        refuses(
            Source::new(
                vec![first, alias],
                vec![digest(&[0, 0]); 2],
                vec![0, 1],
                Observer::Off,
            ),
            "duplicate/outside identity",
        );
        output_dimensions(320, 240)?;
        for (w, h) in [(0, 240), (320, 0), (321, 240), (320, 241), (u32::MAX, 1)] {
            refuses(
                output_dimensions(w, h),
                "TIFF dimensions exceed bounded output",
            );
        }
        output_dimensions(320, 240)?;
        Ok(())
    }
    #[test]
    fn m194g_private_settings_geometry() -> Result<()> {
        environment()?;
        let s = baseline();
        let (d, _, g) = prepared(&s)?;
        assert_eq!(g["level_sizes"].as_array().unwrap().len(), 4);
        for name in ["first", "last"] {
            let mut e = s.clone();
            e.subset = name.into();
            let (ed, _, eg) = prepared(&e)?;
            assert_eq!(ed, d);
            assert_eq!(eg["placements"][0]["probe_seed_index"], 0);
            assert_eq!(
                eg["placements"][0]["original_index"],
                if name == "first" { 0 } else { 4 }
            );
        }
        let mut bad = s.clone();
        bad.seed = Some(702);
        refuses(bad.validate(), "unregistered scene/seed");
        bad = s.clone();
        bad.subset = "last".into();
        bad.seed = Some(701);
        refuses(bad.validate(), "endpoints require");
        let mut candidate = s.clone();
        candidate.admission = AdmissionMode::FloorPedestalV1;
        assert_eq!(
            opts(PathBuf::new(), &s)?.pyramid.admission,
            AdmissionMode::HardFloor
        );
        assert_eq!(
            opts(PathBuf::new(), &candidate)?.pyramid.admission,
            AdmissionMode::FloorPedestalV1
        );
        assert!(Exposure::resolve(false, 1.0, false).is_err());
        Ok(())
    }

    fn manifest_fixture() -> Value {
        let r = json!({"path":"private-only.json","sha256":"0".repeat(64),"bytes":1});
        let frames:Vec<_>=(0..5).map(|i|json!({"index":i,"inverse_focus":0.5+i as f64/8.0,
            "cfa":{"path":format!("private-{i}.cfa"),"sha256":"0".repeat(64),"bytes":RAW_BYTES,"dtype":"<u2","shape":[HEIGHT,WIDTH]},"audit":r})).collect();
        let bundles: Vec<_> = (0..18)
            .map(|i| {
                json!({"scene":if i<9{"textured"}else{"flat"},"noise_enabled":i%9!=0,
            "seed":if i%9==0{None}else{Some(SEEDS[i%9-1])},"frames":frames})
            })
            .collect();
        let geometry = json!({"width":WIDTH,"height":HEIGHT,"cfa_origin":[0,0],"reference_index":2,"frame_indices":[0,1,2,3,4],"inverse_foci":[0.5,0.625,0.75,0.875,1.0],"forward_similarity":{"scale":1.0,"rotation":0.0,"centre":[0.0,0.0],"translation":[0.0,0.0]}});
        let sensor = json!({"cfa":"RGGB","factors_f64":[0.75,1.0,1.0,0.6],"gain_dn_per_e":vec![0.25;4],"read_noise_e":vec![4.0;4],"black":vec![512;4],"white":vec![15360;4],"quantization":"ties-even-then-clip-[0,15360]","wb_rgb_f32":WB.map(f64::from)});
        json!({"schema":"m194g-software-noise-manifest-v1","status":"COMPLETE_NOISE_FILES_UNCOMMISSIONED","ref_root":"manifest-parent","upstream_ref_root":"repository","contract":r,"float_commission":r,"noise_commission":r,"runtime":r,"source_bindings":{},"geometry":geometry,"sensor":sensor,"bundles":bundles})
    }
    #[test]
    fn m194g_private_manifest_schema_tuple_controls() -> Result<()> {
        let valid = manifest_fixture();
        validate_manifest(valid.clone())?;
        let replacements = [
            ("/schema", json!("m194e-joint-pupil-v1")),
            ("/extra", json!(1)),
            ("/geometry/width", json!(64)),
            ("/geometry/width", json!(320.0)),
            ("/geometry/reference_index", json!(false)),
            ("/geometry/reference_index", json!(4)),
            ("/geometry/cfa_origin/0", json!(1)),
            ("/geometry/forward_similarity/scale", json!(1.001)),
            ("/sensor/gain_dn_per_e/0", json!(0.5)),
            ("/sensor/read_noise_e/3", json!(0.0)),
            ("/sensor/factors_f64/0", json!(1.0)),
            ("/sensor/wb_rgb_f32/0", json!(1.0)),
            ("/sensor/black/0", json!(0)),
            ("/sensor/white/2", json!(16383)),
            ("/bundles/0/seed", json!(701)),
            ("/bundles/1/seed", json!(709)),
            ("/bundles/1/noise_enabled", json!(false)),
            ("/bundles/2/scene", json!("flat")),
            ("/bundles/0/frames/1/index", json!(0)),
            ("/bundles/0/frames/1/index", json!(1.0)),
            ("/bundles/0/frames/2/cfa/bytes", json!(6144)),
            ("/bundles/0/frames/2/cfa/shape/1", json!(64)),
            ("/bundles/0/frames/3/cfa/dtype", json!(">u2")),
            ("/bundles/0/frames/4/inverse_focus", json!(0.5)),
        ];
        let mut checked = Vec::new();
        for (pointer, value) in replacements {
            let mut bad = valid.clone();
            if pointer == "/extra" {
                bad["extra"] = value;
            } else {
                *bad.pointer_mut(pointer).unwrap() = value;
            }
            // Persist/reopen each descriptor: checksum consistency is not the predicate.
            let bytes = serde_json::to_vec(&bad)?;
            assert!(
                validate_manifest(unique(&bytes)?).is_err(),
                "accepted {pointer}"
            );
            checked.push(pointer);
        }
        let mut missing = valid.clone();
        missing["bundles"].as_array_mut().unwrap().pop();
        refuses(validate_manifest(missing), "requires18 bundles");
        validate_manifest(unique(&serde_json::to_vec(&valid)?)?)?;
        let root = dir("manifest-controls")?;
        let r = Ref {
            path: "private-only.json".into(),
            sha256: "0".repeat(64),
            bytes: 1,
        };
        let a = Admission {
            schema: "m194g-software-noise-admission-v1".into(),
            status: "PASS_SOFTWARE_NOISE_FILES_ONLY".into(),
            ref_root: "repository".into(),
            manifest: r.clone(),
            generation_result: r.clone(),
            independent_read: r.clone(),
            float_commission: r.clone(),
            noise_commission: r.clone(),
        };
        let rows:Vec<_>=(0..90).map(|i|{let b=i/5;let seed=if b%9==0{None}else{Some(SEEDS[b%9-1])};json!({"scene":if b<9{"textured"}else{"flat"},"seed":seed,"index":i%5,"cfa":r,"audit":r,"minimum":0,"maximum":15360,"noise_off_exact":if seed.is_none(){Some(true)}else{None}})}).collect();
        let reader = json!({"schema":"m194g-independent-noise-files-read-v1","status":"PASS_SOFTWARE_NOISE_FILES_ONLY","ref_root":"repository","method":"actual-native-cfa-files-v1","manifest":r,"generation_result":r,"float_commission":r,"noise_commission":r,"execution_release":r,"invocation":[],"sources_before":{},"sources_after":{},"inputs_before":{},"inputs_after":{},"file_count":90,"noise_off_count":10,"noisy_count":80,"files":rows,"controls":{"check_count":1,"checks":[{"name":"private-schema-companion","pass":true,"evidence":{}}]},"work":{},"error":null,"finalization_errors":[]});
        assert_eq!(validate_intended_read(&reader, &a)?.len(), 90);
        for (pointer, value) in [
            ("/status", json!("PASS_SOFTWARE_NOISE_PRIVATE_TRACES")),
            ("/file_count", json!(90.0)),
            ("/noise_off_count", json!(true)),
            ("/manifest/sha256", json!("1".repeat(64))),
            ("/files/47/index", json!(0)),
            ("/files/0/noise_off_exact", json!(false)),
            ("/files/8/seed", json!(709)),
            ("/controls/checks/0/pass", json!(1)),
            ("/sources_after", json!({"extra":{}})),
            ("/error", json!({"type":"ValueError"})),
        ] {
            let mut bad = reader.clone();
            *bad.pointer_mut(pointer).unwrap() = value;
            assert!(
                validate_intended_read(&unique(&serde_json::to_vec(&bad)?)?, &a).is_err(),
                "accepted reader fault {pointer}"
            );
        }
        validate_intended_read(&reader, &a)?;
        let cfa = root.join("actual.cfa");
        let audit = root.join("audit.json");
        let raw = vec![0u8; RAW_BYTES];
        fs::write(&cfa, &raw)?;
        fs::write(&audit, b"{}")?;
        let f = InputFrame {
            index: 0,
            inverse_focus: 0.5,
            cfa: Array {
                path: "actual.cfa".into(),
                sha256: digest(&raw),
                bytes: RAW_BYTES as u64,
                dtype: "<u2".into(),
                shape: [HEIGHT, WIDTH],
            },
            audit: Ref {
                path: "audit.json".into(),
                sha256: digest(b"{}"),
                bytes: 2,
            },
        };
        let b = Bundle {
            scene: "textured".into(),
            noise_enabled: false,
            seed: None,
            frames: vec![f.clone()],
        };
        let mut row = ReadRow {
            scene: "textured".into(),
            seed: None,
            index: 0,
            cfa: f.cfa.file(),
            audit: f.audit.clone(),
            minimum: 0,
            maximum: 0,
            noise_off_exact: Some(true),
        };
        let cfa = cfa.canonicalize()?;
        let audit = audit.canonicalize()?;
        associate_read_row(&row, &b, &f, &cfa, &audit, &raw, &root)?;
        row.maximum = 1;
        refuses(
            associate_read_row(&row, &b, &f, &cfa, &audit, &raw, &root),
            "extrema differ",
        );
        row.maximum = 0;
        row.cfa.sha256 = "1".repeat(64);
        refuses(
            associate_read_row(&row, &b, &f, &cfa, &audit, &raw, &root),
            "payload association",
        );
        row.cfa = f.cfa.file();
        associate_read_row(&row, &b, &f, &cfa, &audit, &raw, &root)?;
        write_json_new(
            &root.join("result.json"),
            &json!({"schema":"m194g-bridge-private-manifest-v1","fixture_only":true,"status":"PASS_PRIVATE_SCHEMA_ONLY","rejected_pointers":checked,"missing_bundle_refused":true,"restored":true}),
        )?;
        Ok(())
    }
    #[test]
    fn m194g_private_ledger_changed_input() -> Result<()> {
        let root = dir("ledger")?;
        let file = root.join("input.json");
        let original = br#"{"n":1}"#;
        fs::write(&file, original)?;
        let mut ledger = Ledger::default();
        assert_eq!(
            unique(&ledger.raw(
                &file,
                &digest(original),
                Some(original.len() as u64),
                JSON_CAP
            )?)?,
            json!({"n":1})
        );
        ledger.check()?;
        fs::write(&file, br#"{"n":2}"#)?;
        refuses(ledger.check(), "input/source changed before completion");
        refuses(
            ledger.raw(&file, &digest(br#"{"n":2}"#), None, JSON_CAP),
            "input changed between reads",
        );
        // The failed second read deliberately does not restore ledger authority.
        fs::write(&file, original)?;
        let mut restored = Ledger::default();
        restored.raw(&file, &digest(original), None, JSON_CAP)?;
        restored.check()?;
        refuses(
            new_paths(&[PathBuf::from("relative.tiff")]),
            "absolute and new",
        );
        refuses(
            new_paths(&[root.join("A.tiff"), root.join("a.tiff")]),
            "output paths alias",
        );
        let output = root.join("pixels-private.bin");
        let original = b"abcdef";
        fs::write(&output, original)?;
        let image = json!({"bytes":original.len(),"sha256":digest(original)});
        check_output(&output, &image)?;
        let receipt = root.join("publication.json");
        // Exercise a secondary retention failure as well as the original output
        // corruption through the same finalization used by actual execute().
        fs::write(
            receipt.with_extension("rejected.json"),
            b"preexisting private sentinel",
        )?;
        let calls = std::cell::Cell::new(0);
        let result = json!({"schema":"m194g-noise-consumer-receipt-v1","status":"COMPLETE_RGB_UNVERIFIED","fixture_only":true});
        let error = publish_receipt(&receipt, &result, || {
            let n = calls.get() + 1;
            calls.set(n);
            if n == 2 {
                fs::write(&output, b"abcdeg")?;
            }
            check_output(&output, &image)
        })
        .unwrap_err();
        let message = format!("{error:#}");
        assert!(
            message.contains("output changed before completion")
                && message.contains("already exists")
        );
        let rejected = unique(&bounded(&receipt, JSON_CAP)?)?;
        assert_eq!(rejected["status"], "UNCOMMISSIONED_BRIDGE");
        assert!(
            rejected["error"]
                .as_str()
                .unwrap()
                .contains("output changed before completion")
        );
        fs::write(&output, original)?;
        check_output(&output, &image)?;
        let restored_receipt = root.join("publication-restored.json");
        publish_receipt(&restored_receipt, &result, || check_output(&output, &image))?;
        Ok(())
    }
    #[test]
    fn m194g_private_actual_plan_controls() -> Result<()> {
        environment()?;
        let root = dir("plans")?;
        let manifest = validate_manifest(manifest_fixture())?;
        let r = Ref {
            path: "private-only.json".into(),
            sha256: "0".repeat(64),
            bytes: 1,
        };
        let authority = Admission {
            schema: "m194g-software-noise-admission-v1".into(),
            status: "PASS_SOFTWARE_NOISE_FILES_ONLY".into(),
            ref_root: "repository".into(),
            manifest: r.clone(),
            generation_result: r.clone(),
            independent_read: r.clone(),
            float_commission: r.clone(),
            noise_commission: r,
        };
        let inputs = Inputs {
            manifest,
            authority,
            ledger: Ledger::default(),
            bundle_root: root.clone(),
            authority_sha: "0".repeat(64),
        };
        let s = baseline();
        let (_, _, wanted) = plan(&inputs, &s, &environment()?)?;
        let p = root.join("private-plan.json");
        write_json_new(&p, &wanted)?;
        validate_plan(&unique(&bounded(&p, JSON_CAP)?)?, &wanted)?;
        for (pointer, value) in [
            ("/geometry/canonical_native_offset/0", json!(99)),
            ("/geometry/placements/4/original_index", json!(0)),
            ("/geometry/placements/4/probe_seed_index", json!(0)),
            ("/config/admission", json!("FloorPedestalV1")),
            ("/config/exposure_stops", json!(1)),
            ("/wb_f32/0", json!(1.0)),
            ("/frame_wb_f32/2", json!(1.0)),
            ("/injected_noise/gain_dn_per_e/0", json!(0.5)),
            ("/normalization/second_black_subtraction", json!(true)),
        ] {
            let mut bad = wanted.clone();
            *bad.pointer_mut(pointer).unwrap() = value;
            let raw = serde_json::to_vec(&bad)?;
            // Actual full Value comparison also rejects coherently rehashed changes.
            refuses(
                validate_plan(&unique(&raw)?, &wanted),
                "trusted plan differs",
            );
        }
        let mut last = s.clone();
        last.subset = "last".into();
        let (_, _, lp) = plan(&inputs, &last, &environment()?)?;
        assert_eq!(lp["geometry"]["placements"][0]["original_index"], 4);
        assert_eq!(lp["geometry"]["placements"][0]["probe_seed_index"], 0);
        validate_plan(&unique(&serde_json::to_vec(&lp)?)?, &lp)?;
        Ok(())
    }

    #[test]
    #[ignore = "private six RGB outputs; root freezes exact command before execution"]
    fn m194g_private_production_outputs() -> Result<()> {
        let environment = environment()?;
        let root = dir("private-outputs")?;
        let s = baseline();
        let mut records = Vec::new();
        let mut null = None;
        let fields = [
            "constant-off",
            "constant-count",
            "constant-placebo",
            "affine-off",
            "green-change-off",
            "constant-pedestal",
        ];
        for field in fields {
            let case = root.join(field);
            fs::create_dir(&case)?;
            let mut data = vec![0u16; WIDTH * HEIGHT];
            for y in 0..HEIGHT {
                for x in 0..WIDTH {
                    let c = match (y % 2, x % 2) {
                        (0, 0) => 0,
                        (1, 1) => 2,
                        _ => 1,
                    };
                    let affine = matches!(field, "affine-off" | "green-change-off");
                    let v = if affine {
                        match c {
                            0 => 1500 + 2 * x + y,
                            1 => 1800 + x + 3 * y,
                            _ => 2300 + 3 * x + 2 * y,
                        }
                    } else {
                        [1800, 2000, 2400][c]
                    };
                    data[y * WIDTH + x] = 512
                        + v as u16
                        + if field == "green-change-off" && c == 1 {
                            64
                        } else {
                            0
                        };
                }
            }
            let mut setting = s.clone();
            setting.observer = match field {
                "constant-count" => Observer::Count,
                "constant-placebo" => Observer::Placebo,
                _ => Observer::Off,
            };
            if field == "constant-pedestal" {
                setting.admission = AdmissionMode::FloorPedestalV1;
            }
            let source = source_at(&case, &data, setting.observer)?;
            let out = case.join("output.tiff");
            run_source(out.clone(), &setting, &source)?;
            let image = tiff(&out)?;
            assert_eq!(
                source.counts(),
                vec![usize::from(setting.observer == Observer::Count); 5]
            );
            assert_eq!(
                source.hooks.load(Ordering::SeqCst),
                if setting.observer == Observer::Off {
                    0
                } else {
                    5
                }
            );
            if field == "constant-off" {
                null = Some(image["sha256"].clone());
            }
            if matches!(field, "constant-count" | "constant-placebo") {
                assert_eq!(Some(image["sha256"].clone()), null);
            }
            records.push(json!({"name":field,"configuration":{"admission":format!("{:?}",setting.admission),"observer":setting.observer},"geometry":prepared(&setting)?.2,"output":image,"successful_decode_counts":source.counts(),"hook_calls":source.hooks.load(Ordering::SeqCst)}));
        }
        assert_ne!(
            records[3]["output"]["pixel_sha256_le"], records[4]["output"]["pixel_sha256_le"],
            "actual changed green input must move writer output"
        );
        let fault_dir = root.join("decode-fault");
        fs::create_dir(&fault_dir)?;
        let mut fault = source_at(&fault_dir, &vec![2512; WIDTH * HEIGHT], Observer::Count)?;
        fault.fail = Some((3, 1));
        let failed = fault_dir.join("output.tiff");
        refuses(
            run_source(failed.clone(), &s, &fault),
            "injected decode failure index3 attempt1",
        );
        assert!(!failed.exists());
        assert_eq!(fault.counts(), [1, 1, 1, 0, 0]);
        write_json_new(
            &root.join("result.json"),
            &json!({"schema":"m194g-private-bridge-output-v1","status":"COMPLETE_PRIVATE_RGB_UNVERIFIED","fixture_only":true,"environment":environment,"outputs":records,"decode_fault":{"index":3,"attempt":1,"successful_decode_counts":fault.counts(),"output_absent":true},"scope":"private source and shared production path only; independent TIFF/config/log read required"}),
        )?;
        Ok(())
    }
}

#[cfg(feature = "m194h-pedestal-causality")]
mod pedestal_causality {
    include!(concat!(
        env!("CARGO_MANIFEST_DIR"),
        "/../../experiments/m194h-pedestal-causality/production-bridge.rs"
    ));
}

#[cfg(feature = "native-boundary-radiance")]
mod boundary_radiance_bridge {
    include!(concat!(env!("CARGO_MANIFEST_DIR"), "/../../experiments/native-boundary-radiance/bridge.rs"));
}
