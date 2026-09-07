// M193c source-only prototype. NO INCLUDE HOOK / BUILD / EXECUTION RELEASE.
// Intended parent: merge_cmd::production_truth::m193c_output_grid.
// This supplies generated CFA to the shared production body; it is not a merge.
use super::*;
use serde_json::{Value, json};
use sha2::{Digest, Sha256};
use std::collections::BTreeMap;
use std::io::{Read, Write};
use std::sync::Mutex;
use strehl_core::align::Cx;
use strehl_core::noise::{NoiseProvenance, PlaneNoise};
use strehl_core::pyramid::{Fallback, Hull};

const WIDTH: usize = 320;
const HEIGHT: usize = 240;
const RAW_BYTES: usize = WIDTH * HEIGHT * 2;
const JSON_LIMIT: usize = 1024 * 1024;
const TIFF_LIMIT: usize = 4 * 1024 * 1024;
const ENV_PREFIX: &str = "STREHL_M193C_GRID_";
const RUNGS: [usize; 9] = [0, 40, 80, 112, 144, 184, 224, 264, 298];
const SCALES: [f64; 9] = [
    0.9999999999999998, 0.9856299999999998, 0.9726649999999999,
    0.9642499999999998, 0.9468599999999999, 0.9285849999999999,
    0.9090699999999999, 0.8795899999999999, 0.85714,
];
const IMAGINARY: [f64; 9] = [
    0.0, 1.0 / 128.0, 0.0, -1.0 / 256.0, 0.0,
    1.0 / 256.0, 0.0, -1.0 / 128.0, 0.0,
];
const TRANSLATIONS: [[f64; 2]; 9] = [
    [-2.0, 1.0], [-1.5, 1.0], [-1.0, 0.5], [-0.5, 0.25], [0.0, 0.0],
    [0.5, -0.25], [1.0, -0.5], [1.5, -1.0], [2.0, -1.5],
];
const CASE_NAMES: [&str; 10] = [
    "identity-nine", "curved-nine-off", "curved-nine-count",
    "curved-nine-placebo", "curved-nine-scale", "original-one-correct",
    "original-one-swapped", "original-one-restored", "original-one-inverse",
    "constant-nine-null",
];

#[derive(Clone, Copy)]
struct Case {
    ordinal: usize,
}
impl Case {
    fn parse(name: &str) -> Result<Self> {
        let ordinal = CASE_NAMES.iter().position(|v| *v == name)
            .context("M193c unregistered private case")?;
        Ok(Self { ordinal })
    }
    fn name(self) -> &'static str { CASE_NAMES[self.ordinal] }
    fn original(self) -> Vec<usize> {
        if (5..=8).contains(&self.ordinal) { vec![1] } else { (0..9).collect() }
    }
    fn cover(self) -> align_cmd::CoverMode {
        if self.ordinal == 4 { align_cmd::CoverMode::Scale }
        else { align_cmd::CoverMode::Crop }
    }
    fn observer(self) -> &'static str {
        match self.ordinal { 2 => "count", 3 => "placebo", _ => "off" }
    }
    fn fault(self) -> &'static str {
        match self.ordinal {
            6 => "swap-original-1-7",
            8 => "invert-selected-pull",
            _ => "none",
        }
    }
    fn source_track(self) -> [Similarity; 9] {
        std::array::from_fn(|i| {
            if self.ordinal == 0 { Similarity::IDENTITY }
            else {
                // Direct coefficients avoid confusing a_im with rotation angle.
                Similarity {
                    a: Cx::new(SCALES[i] / SCALES[4], IMAGINARY[i]),
                    b: Cx::new(TRANSLATIONS[i][0], TRANSLATIONS[i][1]),
                }
            }
        })
    }
}

fn levels() -> Levels { Levels { black: 512.0, white: 15360.0 } }
fn noise() -> NoiseModel {
    NoiseModel::new(
        [PlaneNoise { gain_dn_per_e: 0.25, read_noise_e: 4.0, levels: levels() }; 4],
        160.0, NoiseProvenance::Fallback,
    )
}
fn sentinel(original: usize) -> PathBuf {
    PathBuf::from(format!("M193C-NO-SUCH-RAW-{original}.ARW"))
}
fn digest(raw: &[u8]) -> String {
    Sha256::digest(raw).iter().map(|v| format!("{v:02x}")).collect()
}
fn bounded(path: &Path, maximum: usize) -> Result<Vec<u8>> {
    let mut f = fs::File::open(path)?;
    let n = f.metadata()?.len();
    ensure!(n > 0 && n <= maximum as u64, "M193c bounded file extent");
    let mut raw = Vec::with_capacity(n as usize);
    Read::by_ref(&mut f).take(maximum as u64 + 1).read_to_end(&mut raw)?;
    ensure!(raw.len() as u64 == n, "M193c file changed while reading");
    Ok(raw)
}
fn file_ref(path: &Path, maximum: usize) -> Result<Value> {
    let raw = bounded(path, maximum)?;
    Ok(json!({"path": path, "sha256": digest(&raw), "bytes": raw.len()}))
}
fn json_bytes(value: &Value) -> Result<Vec<u8>> {
    let mut raw = serde_json::to_vec_pretty(value)?;
    raw.push(b'\n');
    ensure!(raw.len() <= JSON_LIMIT, "M193c JSON output extent");
    Ok(raw)
}
fn write_new_json(path: &Path, value: &Value) -> Result<()> {
    let raw = json_bytes(value)?;
    let mut f = fs::OpenOptions::new().create_new(true).write(true).open(path)?;
    f.write_all(&raw)?;
    f.sync_all()?;
    ensure!(bounded(path, JSON_LIMIT)? == raw, "M193c persisted JSON mismatch");
    Ok(())
}
fn named_path(key: &str, exists: bool) -> Result<PathBuf> {
    let p = PathBuf::from(std::env::var(format!("{ENV_PREFIX}{key}"))?);
    ensure!(p.is_absolute(), "M193c {key} path must be absolute");
    ensure!(p.parent().is_some_and(Path::is_dir), "M193c {key} parent missing");
    ensure!(if exists { p.is_file() } else { !p.exists() }, "M193c {key} freshness/type");
    Ok(p)
}
fn environment(mode: &str) -> Result<BTreeMap<String, String>> {
    let required = [
        ("STREHL_DEFECT", "off"), ("STREHL_FIX_CA", "off"),
        ("STREHL_FULLRES_GATHER", "1"), ("STREHL_PYRAMID_WORKERS", "2"),
        ("RAYON_NUM_THREADS", "2"),
    ];
    let mut result = BTreeMap::new();
    for (key, value) in required {
        ensure!(std::env::var(key).as_deref() == Ok(value), "M193c required {key}={value}");
        result.insert(key.to_string(), value.to_string());
    }
    let suffixes: &[&str] = if mode == "plan" { &["MODE", "CASE", "PLAN"] }
    else { &["MODE", "CASE", "PLAN", "PLAN_SHA256", "OUTPUT", "RECEIPT"] };
    for (key, _) in std::env::vars() {
        if let Some(suffix) = key.strip_prefix(ENV_PREFIX) {
            ensure!(suffixes.contains(&suffix), "M193c unexpected mode variable {key}");
        } else if key.starts_with("STREHL_") {
            ensure!(result.contains_key(&key), "M193c uncleared environment {key}");
        }
    }
    Ok(result)
}
fn options(output: PathBuf, case: Case) -> Result<MergeOptions> {
    let mut o = fixture_options(output);
    // These are prototype prerequisites, not claims about a future default.
    ensure!(o.pyramid.admission == AdmissionMode::HardFloor, "M193c default admission changed");
    ensure!(o.pyramid.hull == Hull::InputRange, "M193c needs final InputRange hull");
    ensure!(o.pyramid.select == SelectMode::SoftPower, "M193c select mode");
    ensure!(o.pyramid.base == BaseBand::Mean && o.pyramid.fallback == Fallback::Mean,
        "M193c mean base/fallback required");
    ensure!(o.pyramid.mean_coarse == 0 && o.pyramid.significance_scale == 0.0,
        "M193c coarse/significance defaults");
    ensure!(o.pyramid.gate == 2.0 && o.pyramid.exponent == 2.0
        && o.pyramid.sharpen_per_octave == 1.4, "M193c power schedule");
    ensure!(gatefloor::enabled(), "M193c measured gate floor required");
    o.dir = PathBuf::from("M193C-NO-SUCH-RAW-DIRECTORY");
    o.cover = case.cover();
    o.pyramid.bands = 3;
    Ok(o)
}
fn similarity_record(t: Similarity) -> Value {
    json!({"a_re": t.a.re, "a_im": t.a.im, "b_re": t.b.re, "b_im": t.b.im})
}
fn map(original: &[usize], pulls: &[Similarity], note: &str) -> WarpMap {
    let names: Vec<_> = original.iter().map(|&i| sentinel(i).to_string_lossy().into_owned()).collect();
    let entries: Vec<_> = names.iter().map(|p| (p.as_str(), RAW_BYTES as u64)).collect();
    WarpMap::new(
        WarpProvenance {
            stack: StackIdentity::from_entries("M193c generated private CFA", &entries),
            strategy: "supplied private coordinate plant; no alignment solve".into(),
            heldout_px: None, cycle_floor_px: None,
            reference: if original.len() == 1 { 0 } else { 4 },
            note: note.into(),
        },
        PlaneGeometry::from_active(WIDTH, HEIGHT), Resampler::CatmullRom,
        pulls.iter().copied().map(FrameWarp::Placed).collect(),
    )
}

struct PreparedCase {
    alignment: WarpMap,
    fit: align_cmd::CoverFit,
    domain: PyramidDomain,
    source_pulls: [Similarity; 9],
    post_cover: Vec<Similarity>,
    post_fault: Vec<Similarity>,
    k: f64,
}
fn prepare(case: Case) -> Result<PreparedCase> {
    let source_pulls = case.source_track();
    let full = PlaneGeometry::from_active(WIDTH, HEIGHT);
    let all: Vec<_> = (0..9).collect();
    let initial = map(&all, &source_pulls, "canonical private4; full track cover before subset");
    let (fitted, fit) = align_cmd::cover_or_explain(initial, case.cover());
    let k = match fit {
        align_cmd::CoverFit::Cropped { k, .. } | align_cmd::CoverFit::Scaled(k) => k,
        align_cmd::CoverFit::Uncovered => bail!("M193c supplied track uncovered"),
    };
    ensure!(k.is_finite() && k > 0.0 && k < 1.0, "M193c nontrivial cover fit");
    let domain = pyramid_domain(full, case.cover(), Some(&fit))?;
    let expected = if case.ordinal == 0 { [5, 4, 150, 113] }
        else if case.ordinal == 4 { [0, 0, 160, 120] }
        else { [10, 8, 140, 105] };
    let r = domain.rect;
    ensure!([r.x, r.y, r.width, r.height] == expected,
        "M193c derived crop disagreement: actual {:?}, expected {:?}",
        [r.x, r.y, r.width, r.height], expected);
    let post_cover: Vec<_> = fitted.warps().iter()
        .map(|f| f.placed().context("M193c refused fitted placement"))
        .collect::<Result<_>>()?;
    let mut post_fault = post_cover.clone();
    if case.ordinal == 6 { post_fault.swap(1, 7); }
    if case.ordinal == 8 {
        post_fault[1] = post_fault[1].invert().context("M193c invert fault singular")?;
    }
    ensure!(post_fault[0] == post_cover[0] && post_fault[4] == post_cover[4]
        && post_fault[8] == post_cover[8], "M193c intervention changed endpoint/anchor");
    let original = case.original();
    let selected: Vec<_> = original.iter().map(|&i| post_fault[i]).collect();
    let alignment = map(&original, &selected,
        "external canonical private4; selected local identity/probe seed recorded separately");
    ensure!(level_sizes(r.width, r.height, 3).len() == 4, "M193c small pyramid depth");
    Ok(PreparedCase { alignment, fit, domain, source_pulls, post_cover, post_fault, k })
}
fn make_plan(case: Case, prepared: &PreparedCase, env: &BTreeMap<String, String>) -> Result<Value> {
    let cfg = options(PathBuf::new(), case)?.pyramid;
    let r = prepared.domain.rect;
    let track: Vec<_> = (0..9).map(|i| json!({
        "original_index": i, "retained_rung": RUNGS[i], "retained_scale": SCALES[i],
        "source_generation_pull": similarity_record(prepared.source_pulls[i]),
        "correct_post_cover_pull": similarity_record(prepared.post_cover[i]),
        "actual_post_fault_pull": similarity_record(prepared.post_fault[i]),
    })).collect();
    let selected: Vec<_> = case.original().iter().enumerate().map(|(local, &i)| json!({
        "local_index": local, "original_index": i, "probe_seed_index": local,
        "path": sentinel(i), "actual_quad_pull": similarity_record(prepared.post_fault[i]),
    })).collect();
    let geometry = json!({
        "full_native": [WIDTH, HEIGHT], "full_quad": [WIDTH / 2, HEIGHT / 2],
        "native_centre": [160.0, 120.0], "canonical_private_index": 4,
        "local_reference": if selected.len() == 1 { 0 } else { 4 },
        "crop_quad": {"x": r.x, "y": r.y, "width": r.width, "height": r.height},
        "output_native": [2 * r.width, 2 * r.height], "cover_k": prepared.k,
        "cover_mode": format!("{:?}", case.cover()),
        "output_to_canonical": if case.ordinal == 4 { "C+k*(z-C)" } else { "z+2*crop_origin" },
        "level_sizes": level_sizes(r.width, r.height, 3).iter()
            .map(|s| [s.width, s.height]).collect::<Vec<_>>(),
    });
    let config = json!({
        "backend": "Pyramid", "bands": cfg.bands, "gate": cfg.gate,
        "exponent": cfg.exponent, "sharpen_per_octave": cfg.sharpen_per_octave,
        "select": format!("{:?}", cfg.select), "admission": format!("{:?}", cfg.admission),
        "base": format!("{:?}", cfg.base), "fallback": format!("{:?}", cfg.fallback),
        "hull": format!("{:?}", cfg.hull), "mean_coarse": cfg.mean_coarse,
        "significance_scale": cfg.significance_scale, "resampler": "CatmullRom",
        "fullres_gather": true, "demosaic": "MHC", "space": "CameraLinear",
        "exposure": 0, "photometric": "Off", "confidence": false,
        "defect": false, "ca": false, "restoration": false, "gate_floor": true,
    });
    let sensor = json!({
        "black": 512, "white": 15360, "range_dn": 14848,
        "cfa": "RGGB", "stride": WIDTH, "buffer_height": HEIGHT,
        "active": {"x": 0, "y": 0, "width": WIDTH, "height": HEIGHT},
        "frame_wb_f32": [1.0, 1.0, 1.0], "writer_wb_f32": [1.0, 1.0, 1.0],
        "gain_dn_per_e": [0.25, 0.25, 0.25, 0.25],
        "read_noise_e": [4.0, 4.0, 4.0, 4.0], "iso": 160,
        "provenance": "Fallback: injected synthetic coefficients; no calibration claim",
        "source_rounding": "positive half-up, no clipping permitted",
        "tiff_u16_to_dn": 14848.0 / 65535.0,
    });
    let exe = std::env::current_exe()?;
    let exe_len = fs::metadata(&exe)?.len();
    let mut executable = fs::File::open(&exe)?;
    let mut hasher = Sha256::new();
    let mut chunk = [0u8; 65536];
    loop {
        let n = executable.read(&mut chunk)?;
        if n == 0 { break; }
        hasher.update(&chunk[..n]);
    }
    let sha: String = hasher.finalize().iter().map(|v| format!("{v:02x}")).collect();
    let build = json!({"path": exe, "sha256": sha, "bytes": exe_len, "software": crate::SOFTWARE});
    let compiled_inputs = json!({
        "private_protocol_sha256": digest(include_bytes!(concat!(env!("CARGO_MANIFEST_DIR"),
            "/../../experiments/m193c-output-grid/private-protocol.md"))),
        "private_adapter_sha256": digest(include_bytes!(concat!(env!("CARGO_MANIFEST_DIR"),
            "/../../experiments/m193c-output-grid/private-adapter.rs"))),
    });
    let fields = if case.ordinal == 9 {
        json!({"kind": "constant", "rgb_affine": [[1800, 0, 0], [2300, 0, 0], [2900, 0, 0]]})
    } else {
        json!({"kind": "affine", "rgb_affine": [[1100, 40, 0], [1700, 0, 40], [2100, 12, 8]]})
    };
    Ok(json!({
        "schema": "m193c-private-grid-plan-v1", "status": "PLAN_ONLY",
        "case": {"ordinal": case.ordinal, "id": case.name(), "fault": case.fault(),
            "observer": case.observer(), "restored_from": if case.ordinal == 7 { Some(6) } else { None }},
        "track": track, "selected": selected, "geometry": geometry, "fields": fields,
        "sensor": sensor, "config": config, "environment": env,
        "build": build, "compiled_inputs": compiled_inputs,
    }))
}

struct Source {
    case: Case,
    original: Vec<usize>,
    pulls: [Similarity; 9],
    attempts: Vec<AtomicUsize>,
    optional_counts: Vec<AtomicUsize>,
    hooks: AtomicUsize,
    records: Mutex<Vec<Option<Value>>>,
}
impl Source {
    fn new(case: Case, pulls: [Similarity; 9]) -> Self {
        let original = case.original();
        let n = original.len();
        Self { case, original, pulls,
            attempts: (0..n).map(|_| AtomicUsize::new(0)).collect(),
            optional_counts: (0..n).map(|_| AtomicUsize::new(0)).collect(),
            hooks: AtomicUsize::new(0), records: Mutex::new(vec![None; n]),
        }
    }
    fn evidence(&self) -> Result<Value> {
        let attempts: Vec<_> = self.attempts.iter().map(|a| a.load(Ordering::SeqCst)).collect();
        let counts: Vec<_> = self.optional_counts.iter().map(|a| a.load(Ordering::SeqCst)).collect();
        let records = self.records.lock().map_err(|_| anyhow::anyhow!("M193c source ledger poisoned"))?;
        Ok(json!({"attempts": attempts, "optional_counts": counts,
            "optional_hooks": self.hooks.load(Ordering::SeqCst), "records": *records}))
    }
    fn complete(&self) -> Result<()> {
        ensure!(self.attempts.iter().all(|a| a.load(Ordering::SeqCst) == 1), "M193c decode count");
        let expected_hooks = if self.case.observer() == "off" { 0 } else { self.original.len() };
        ensure!(self.hooks.load(Ordering::SeqCst) == expected_hooks, "M193c observer hooks");
        let expected_count = usize::from(self.case.observer() == "count");
        ensure!(self.optional_counts.iter().all(|a| a.load(Ordering::SeqCst) == expected_count),
            "M193c observer counts");
        ensure!(self.records.lock().map_err(|_| anyhow::anyhow!("M193c source ledger poisoned"))?
            .iter().all(Option::is_some), "M193c incomplete source ledger");
        Ok(())
    }
}
impl PyramidFrameSource for Source {
    fn len(&self) -> usize { self.original.len() }
    fn decode(&self, local: usize) -> Result<Frame> {
        let &original = self.original.get(local).context("M193c source local index")?;
        ensure!(self.attempts[local].fetch_add(1, Ordering::SeqCst) == 0,
            "M193c unexpected second source decode");
        let t = self.pulls[original];
        let det = t.a.re * t.a.re + t.a.im * t.a.im;
        ensure!(det.is_finite() && det > 0.0, "M193c singular source inverse");
        let mut data = Vec::with_capacity(WIDTH * HEIGHT);
        let mut minimum = f64::INFINITY;
        let mut maximum = f64::NEG_INFINITY;
        let mut hasher = Sha256::new();
        for y in 0..HEIGHT {
            for x in 0..WIDTH {
                // Explicit source -> canonical inverse. Never production apply/invert.
                let vx = x as f64 - 160.0 - 2.0 * t.b.re;
                let vy = y as f64 - 120.0 - 2.0 * t.b.im;
                let cx = 160.0 + (t.a.re * vx + t.a.im * vy) / det;
                let cy = 120.0 + (-t.a.im * vx + t.a.re * vy) / det;
                let site = (y % 2) * 2 + x % 2;
                let value = if self.case.ordinal == 9 { [1800.0, 2300.0, 2300.0, 2900.0][site] }
                else { match site {
                    0 => 1100.0 + 40.0 * cx,
                    1 | 2 => 1700.0 + 40.0 * cy,
                    _ => 2100.0 + 12.0 * cx + 8.0 * cy,
                }};
                ensure!(value.is_finite() && value > 0.0 && value < 14848.0,
                    "M193c invalid source value original{original} x{x} y{y}: {value}");
                let raw = (512.0 + value).round();
                ensure!(raw > 512.0 && raw < 15360.0, "M193c source rounded rail");
                minimum = minimum.min(value);
                maximum = maximum.max(value);
                let v = raw as u16;
                data.push(v);
                hasher.update(v.to_le_bytes());
            }
        }
        let hash: String = hasher.finalize().iter().map(|v| format!("{v:02x}")).collect();
        self.records.lock().map_err(|_| anyhow::anyhow!("M193c source ledger poisoned"))?[local] =
            Some(json!({"local_index": local, "original_index": original, "probe_seed_index": local,
                "sha256_u16_le": hash, "bytes": RAW_BYTES, "samples": data.len(),
                "minimum_unrounded_dn": minimum, "maximum_unrounded_dn": maximum,
                "source_generation_pull": similarity_record(t)}));
        if self.case.observer() != "off" {
            self.hooks.fetch_add(1, Ordering::SeqCst);
            if self.case.observer() == "count" { self.optional_counts[local].fetch_add(1, Ordering::SeqCst); }
        }
        Ok(Frame {
            data, stride: WIDTH, buffer_height: HEIGHT,
            active: Region { x: 0, y: 0, width: WIDTH, height: HEIGHT }, levels: levels(),
            iso: Some(160.0), wb_coeffs: [1.0, 1.0, 1.0, f32::NAN],
            xyz_to_cam_rgbe: [[0.0; 3]; 4], color_matrices: Vec::new(),
            camera: "M193c synthetic private coordinate field".into(), path: sentinel(original),
        })
    }
}

fn execute(case: Case, prepared: PreparedCase, output: &Path, source: &Source) -> Result<()> {
    let paths: Vec<_> = case.original().iter().map(|&i| sentinel(i)).collect();
    ensure!(paths.iter().all(|p| !p.exists()), "M193c source sentinel exists");
    let o = options(output.to_path_buf(), case)?;
    let r = prepared.domain.rect;
    run_pyramid_prepared(&o, PreparedPyramid {
        paths: &paths, geom: prepared.domain.full, levels: levels(), noise: noise(),
        wb: Some([1.0; 3]), xyz_to_cam: None, frame_bytes: RAW_BYTES,
        alignment: Some((prepared.alignment, "M193c supplied private pull", prepared.fit)),
        domain: prepared.domain, sizes: level_sizes(r.width, r.height, 3), defect_plan: None,
        prologue_secs: 0.0, align_secs: 0.0, t_start: Instant::now(),
        exposure: Exposure::resolve(false, 0.0, false)?,
    }, source)?;
    source.complete()?;
    Ok(())
}

fn child() -> Result<()> {
    let started = Instant::now();
    let mode = std::env::var(format!("{ENV_PREFIX}MODE"))?;
    ensure!(mode == "plan" || mode == "render", "M193c mode must be plan/render");
    let case = Case::parse(&std::env::var(format!("{ENV_PREFIX}CASE"))?)?;
    let env = environment(&mode)?;
    let plan_path = named_path("PLAN", mode == "render")?;
    let prepared = prepare(case)?;
    let plan = make_plan(case, &prepared, &env)?;
    if mode == "plan" { return write_new_json(&plan_path, &plan); }
    let raw = bounded(&plan_path, JSON_LIMIT)?;
    let plan_sha = std::env::var(format!("{ENV_PREFIX}PLAN_SHA256"))?;
    ensure!(digest(&raw) == plan_sha, "M193c external plan hash");
    // The exact bounded bytes must equal the producer's canonical serialization.
    // No duplicate-key or numeric-token normalization can disappear in parsing.
    ensure!(raw == json_bytes(&plan)?, "M193c actual prepared plan mismatch");
    let output = named_path("OUTPUT", false)?;
    let receipt_path = named_path("RECEIPT", false)?;
    ensure!(output != receipt_path && output != plan_path && receipt_path != plan_path,
        "M193c output paths must differ");
    let source = Source::new(case, prepared.source_pulls);
    let attempt = execute(case, prepared, &output, &source).and_then(|()| {
        ensure!(bounded(&plan_path, JSON_LIMIT)? == raw, "M193c plan changed during render");
        ensure!(environment(&mode)? == env, "M193c environment changed during render");
        file_ref(&output, TIFF_LIMIT)
    });
    let mut secondary_errors = Vec::<String>::new();
    let evidence = match source.evidence() {
        Ok(v) => v,
        Err(e) => { secondary_errors.push(format!("source evidence: {e:#}")); Value::Null }
    };
    let error = attempt.as_ref().err().map(|e| format!("{e:#}"));
    let result = json!({
        "schema": "m193c-private-grid-receipt-v1",
        "status": if attempt.is_ok() && secondary_errors.is_empty() {
            "COMPLETE_RGB_UNVERIFIED" } else { "REFUSED_PRIVATE_OUTPUT" },
        "plan": plan, "plan_sha256": plan_sha, "plan_bytes": raw.len(),
        "source": evidence, "output": attempt.as_ref().ok(),
        "command": std::env::args().collect::<Vec<_>>(),
        "elapsed_seconds_before_receipt": started.elapsed().as_secs_f64(),
        "error": error, "secondary_errors": secondary_errors,
        "validation_scope": "actual shared production output; independent pixel read still required",
    });
    let persistence = write_new_json(&receipt_path, &result);
    if let Err(e) = persistence {
        eprintln!("M193c primary outcome: {error:?}; receipt persistence error: {e:#}");
        if let Err(primary) = attempt { return Err(primary.context(format!("receipt persistence: {e:#}"))); }
        return Err(e);
    }
    attempt?;
    ensure!(secondary_errors.is_empty(), "M193c evidence finalization failure: {secondary_errors:?}");
    Ok(())
}

#[test]
#[ignore = "M193c requires future frozen source, exact parent commands, fresh output paths and independent reader"]
fn m193c_private_output_case() -> Result<()> {
    child()
}
