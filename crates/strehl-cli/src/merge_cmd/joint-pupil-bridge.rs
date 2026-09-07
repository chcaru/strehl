// M194f private admitted-input bridge. The production fold/writer is unchanged.
use super::*;

const F_PREFIX: &str = "STREHL_M194F_";
const JSON_LIMIT: usize = 1_048_576;
const CFA_BYTES: usize = 64 * 48 * 2;
const MANIFEST_HASH: &str = "f47c2b8720560fe9dbd777eeed3281ce2531f1f2287f5c88ef7b51a083d03299";
const GATE_HASH: &str = "706462ad18a5a3846cadd99e1ef24d6b92b77e064df2e34cbe72e45907fc06a6";
const FLOAT_HASH: &str = "4bd57b896be0b68c42fb1384a468a4f29cc54139a18a046a678dd97bad408217";
const SCOPE: &str = "Exact noiseless CFA conversion and recorded provenance of the admitted geometric model; no camera calibration, diffraction, production merge, quality or SOTA claim";
const PRODUCER_NAMES: &[&str] = &[
    "author-controls.py",
    "commission.py",
    "emit-cfa.py",
    "model.py",
    "render.py",
    "schema.py",
];
const DESIGN_NAMES: &[&str] = &[
    "emission-contract.md",
    "implementation-plan.md",
    "implementation-preregister.md",
    "independent-design.md",
    "numerical-amendment-1.md",
    "numerical-amendment-2.md",
    "numerical-amendment-3.md",
    "numerical-amendment-4.md",
];
const VERIFIER_NAMES: &[&str] = &[
    "author-controls.py",
    "commission.py",
    "emission-contract.md",
    "emit-cfa.py",
    "implementation-plan.md",
    "implementation-preregister.md",
    "independent-amendment3-metadata-design.md",
    "independent-amendment4-emission-design.md",
    "independent-cfa-oracle.py",
    "independent-design.md",
    "independent-emission-api-controls.py",
    "independent-emission-design.md",
    "independent-verify-cfa.py",
    "model.py",
    "numerical-amendment-1.md",
    "numerical-amendment-2.md",
    "numerical-amendment-3.md",
    "numerical-amendment-4.md",
    "render.py",
    "schema.py",
];
fn valid_hash(value: &str) -> bool {
    super::valid_hash(value).is_ok()
}
fn names_match<'a>(actual: impl Iterator<Item = &'a String>, expected: &[&str]) -> bool {
    actual.map(String::as_str).collect::<BTreeSet<_>>()
        == expected.iter().copied().collect::<BTreeSet<_>>()
}

#[derive(Clone, Debug, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
struct FileDigest {
    bytes: u64,
    sha256: String,
}
#[derive(Clone, Debug, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
struct FileRef {
    path: String,
    bytes: u64,
    sha256: String,
}
#[derive(Clone, Debug, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
struct HashRef {
    path: String,
    sha256: String,
}
#[derive(Clone, Debug, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
struct ArrayRef {
    path: String,
    bytes: u64,
    sha256: String,
    dtype: String,
    shape: [usize; 2],
}
#[derive(Clone, Debug, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
struct Forward {
    centre: [f64; 2],
    rotation: f64,
    scale: f64,
    translation: [f64; 2],
}
#[derive(Clone, Debug, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
struct BridgeFrame {
    #[serde(rename = "K")]
    k: f64,
    index: usize,
    inverse_focus: f64,
    forward_similarity: Forward,
    cfa: ArrayRef,
    expected_cfa: ArrayRef,
    expected_scalar: ArrayRef,
    numerical_receipt: FileRef,
}
#[derive(Clone, Debug, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
struct BridgeSensor {
    width: usize,
    height: usize,
    active_origin: [usize; 2],
    black: usize,
    white: usize,
    cell: String,
    cfa: String,
    channel_factors: [f64; 3],
    gain_dn_per_e: f64,
    noise: bool,
    rounding: String,
}
#[derive(Clone, Debug, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
struct BridgeProducer {
    source_base: String,
    sources: BTreeMap<String, FileDigest>,
    designs: BTreeMap<String, FileDigest>,
    command: Vec<String>,
    author_controls: FileRef,
    emission_receipt: FileRef,
}
#[derive(Clone, Debug, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
struct BridgeManifest {
    schema: String,
    status: String,
    sensor: BridgeSensor,
    frames: Vec<BridgeFrame>,
    producer: BridgeProducer,
    ray_model: Value,
    scene: Value,
    numerical_contract: Value,
}
#[derive(Clone, Debug, Deserialize)]
#[serde(deny_unknown_fields)]
struct CfaGate {
    schema: String,
    status: String,
    scope: String,
    sample_count: usize,
    manifest: HashRef,
    float_commission: HashRef,
    independent_verification: HashRef,
}
#[derive(Clone, Debug, Deserialize)]
#[serde(deny_unknown_fields)]
struct ExactConversion {
    cfa_sha256: String,
    expected_cfa_sha256: String,
    scalar_sha256: String,
    sample_count: usize,
    maximum_quantization_error_dn_rgb: [f64; 3],
    minimum_half_integer_margin_dn_rgb: [f64; 3],
    rail_endpoint_admission: String,
    within_optical_discrepancy_allowance_rgb: [usize; 3],
}
#[derive(Clone, Debug, Deserialize)]
#[serde(deny_unknown_fields)]
struct ChannelDiscrepancy {
    channel: String,
    code_differences_outside_allowance: usize,
    maximum_unquantized_reference_difference_dn: f64,
    minimum_half_integer_margin_dn: f64,
    registered_float_allowance_dn: f64,
    rounded_reference_code_differences: usize,
    sites_within_rounding_allowance: usize,
}
#[derive(Clone, Debug, Deserialize)]
#[serde(deny_unknown_fields)]
struct ReferenceDiscrepancy {
    channels: Vec<ChannelDiscrepancy>,
    interpretation: String,
    maximum_scalar_discrepancy_e: f64,
    rms_scalar_discrepancy_e: f64,
    rounded_reference_code_differences: usize,
}
#[derive(Clone, Debug, Deserialize)]
#[serde(deny_unknown_fields)]
struct VerificationFrame {
    index: usize,
    exact_conversion: ExactConversion,
    reference_discrepancy: ReferenceDiscrepancy,
}
#[derive(Clone, Debug, Deserialize)]
#[serde(deny_unknown_fields)]
struct CfaVerification {
    schema: String,
    status: String,
    scope: String,
    fixture_only: bool,
    sample_count: usize,
    externally_trusted_manifest_sha256: String,
    externally_trusted_float_commission_sha256: String,
    source_before: BTreeMap<String, String>,
    source_after: BTreeMap<String, String>,
    source_unchanged: bool,
    input_bindings: BTreeMap<String, FileDigest>,
    frames: Vec<VerificationFrame>,
    units: Value,
    command: Vec<String>,
    interpreter_argv: Vec<String>,
    completed_utc: String,
    cwd: String,
    executable: String,
    numpy: String,
    python: String,
    reader_controls: HashRef,
    xoptions: BTreeMap<String, Value>,
}

fn read_bounded(path: &Path, limit: usize) -> Result<Vec<u8>> {
    let file = fs::File::open(path).with_context(|| format!("open {}", path.display()))?;
    let mut bytes = Vec::new();
    file.take((limit as u64) + 1).read_to_end(&mut bytes)?;
    ensure!(bytes.len() <= limit, "bounded input exceeds {limit} bytes");
    Ok(bytes)
}
fn parse_unique(bytes: &[u8]) -> Result<Value> {
    Ok(serde_json::from_slice::<UniqueValue>(bytes)?.0)
}
fn read_json_bound(path: &Path, expected: &str) -> Result<Value> {
    ensure!(valid_hash(expected), "invalid external SHA-256");
    let bytes = read_bounded(path, JSON_LIMIT)?;
    ensure!(digest(&bytes) == expected, "JSON SHA-256 mismatch");
    parse_unique(&bytes)
}
fn keys(v: &Value, expected: &[&str]) -> Result<()> {
    let object = v.as_object().context("object required")?;
    ensure!(
        object.len() == expected.len() && expected.iter().all(|k| object.contains_key(*k)),
        "unknown or missing object fields"
    );
    Ok(())
}
fn relative_path(root: &Path, name: &str) -> Result<PathBuf> {
    valid_relative(name)?;
    let relative = Path::new(name);
    ensure!(
        relative
            .components()
            .all(|c| matches!(c, Component::Normal(_))),
        "relative reference escapes root"
    );
    let base = root.canonicalize()?;
    let path = base.join(relative).canonicalize()?;
    ensure!(path.starts_with(&base), "resolved reference escapes root");
    Ok(path)
}
fn valid_relative(name: &str) -> Result<()> {
    ensure!(
        !name.is_empty()
            && !name.contains('\\')
            && !name.contains(':')
            && name
                .split('/')
                .all(|c| !c.is_empty() && c != "." && c != ".."),
        "invalid relative reference"
    );
    Ok(())
}
fn repository() -> Result<PathBuf> {
    Ok(Path::new(env!("CARGO_MANIFEST_DIR"))
        .join("../..")
        .canonicalize()?)
}
fn registered_absolute(path: &str) -> Result<PathBuf> {
    let p = Path::new(path);
    ensure!(p.is_absolute(), "absolute recorded binding required");
    let resolved = p.canonicalize()?;
    ensure!(
        resolved.starts_with(repository()?.join("experiments/m194e-joint-pupil")),
        "recorded binding outside M194e"
    );
    Ok(resolved)
}
fn expected_scene() -> Value {
    json!({"depths":[1.0,2.0],"mask":{"normal":[1.0,-0.15],"offset":28.4,"side":"ge"},
        "foreground":{"constant":15000.0,"affine":[0.0,0.0],"waves":[{"amplitude":1400.0,"frequency":[0.045,0.095],"phase":0.7},{"amplitude":700.0,"frequency":[0.17,0.01],"phase":0.3}]},
        "background":{"constant":12000.0,"affine":[0.0,0.0],"waves":[{"amplitude":3200.0,"frequency":[0.08,0.015],"phase":0.2},{"amplitude":1800.0,"frequency":[-0.035,0.12],"phase":1.1}]}})
}
fn expected_ray_model() -> Value {
    json!({"coordinates":"native-displacement-before-inverse-similarity","defocus":"K*(inverse_focus-1/depth)","diffraction":false,"exposure":"radiance-normalized","name":"shared-pupil-two-opaque-planes-v1","pupil":"uniform-unit-disc-area","spectral_optics":false,"visibility":"foreground-first-same-ray"})
}
fn expected_numerics() -> Value {
    let mut arms = serde_json::Map::new();
    for arm in ["primary", "angle-refined", "cell-refined"] {
        let angle = arm == "angle-refined";
        let cell = arm == "cell-refined";
        arms.insert(arm.into(),json!({"arm":arm,"angle_depth":10,"angle_high":if angle{64}else{32},"angle_low":if angle{32}else{16},
            "angular_limit":600000000,"array_limit":33554432,"cell_depth":6,"cell_high":if cell{16}else{8},"cell_low":if cell{8}else{4},
            "cell_point_tolerance":if angle{0.00001171875}else{0.000046875},"cell_tolerance":if cell{0.0001875}else{0.00075},
            "cpu_limit":600,"node_pair_limit":32768,"point_limit":4000000,"pupil_tolerance":if angle{0.0000625}else{0.00025},"wall_limit":1200}));
    }
    json!({"arms":arms,"arrays":"all-five-complete-float64-frames","author_refinement_max_e":0.001,"cell_allocation":"global-absolute-leaf-priority-v1",
        "cell_map":"predicate-square-distance-duffy-v1","cell_point_policy":"family-min-cell-budget-quarter-v1","edge_distance_native":8,
        "independent_refinement_max_e":0.0005,"indicators":"weighted-low-and-high-pupil-plus-cell-delta","max_discrepancy_e":0.004,
        "method":"polar-radial-ladder32-tangent-cell-global-inner-v5","radial_crossing_levels":32,"rms_discrepancy_e":0.0008})
}
fn validate_manifest(v: &Value) -> Result<BridgeManifest> {
    let m: BridgeManifest = serde_json::from_value(v.clone())?;
    ensure!(
        m.schema == "m194e-joint-pupil-v1" && m.status == "float-commissioned-cfa-unverified",
        "wrong manifest schema/status"
    );
    let s = &m.sensor;
    ensure!(
        s.width == 64
            && s.height == 48
            && s.active_origin == [0, 0]
            && s.black == 512
            && s.white == 15360
            && s.cfa == "RGGB"
            && s.cell == "integer-centre-unit-square"
            && s.channel_factors == [0.75, 1.0, 0.6]
            && s.gain_dn_per_e == 0.25
            && !s.noise
            && s.rounding == "ties-to-even",
        "unsupported sensor contract"
    );
    ensure!(
        m.scene == expected_scene()
            && m.ray_model == expected_ray_model()
            && m.numerical_contract == expected_numerics(),
        "unsupported admitted model/numerical contract"
    );
    ensure!(m.frames.len() == 5, "exactly five frames required");
    for (i, f) in m.frames.iter().enumerate() {
        let t = &f.forward_similarity;
        ensure!(
            f.index == i
                && f.k == 12.0
                && f.inverse_focus == [0.5, 0.625, 0.75, 0.875, 1.0][i]
                && t.centre == [0.0; 2]
                && t.translation == [0.0; 2]
                && t.scale == 1.0
                && t.rotation == 0.0,
            "frame geometry/index mismatch"
        );
        for (a, dtype, bytes) in [
            (&f.cfa, "<u2", 6144),
            (&f.expected_cfa, "<f8", 24704),
            (&f.expected_scalar, "<f8", 24704),
        ] {
            ensure!(
                a.shape == [48, 64]
                    && a.dtype == dtype
                    && a.bytes == bytes
                    && valid_hash(&a.sha256),
                "array reference type/shape/length mismatch"
            );
            valid_relative(&a.path)?;
        }
        ensure!(
            valid_hash(&f.numerical_receipt.sha256)
                && f.numerical_receipt.bytes > 0
                && f.numerical_receipt.bytes <= JSON_LIMIT as u64,
            "invalid numerical reference"
        );
        valid_relative(&f.numerical_receipt.path)?;
    }
    ensure!(
        m.producer.source_base == "repository"
            && m.producer.sources.len() == 6
            && m.producer.designs.len() == 8
            && !m.producer.command.is_empty(),
        "producer closure mismatch"
    );
    let expected: Vec<_> = PRODUCER_NAMES
        .iter()
        .map(|name| format!("experiments/m194e-joint-pupil/{name}"))
        .collect();
    ensure!(
        names_match(
            m.producer.sources.keys(),
            &expected.iter().map(String::as_str).collect::<Vec<_>>()
        ) && names_match(m.producer.designs.keys(), DESIGN_NAMES),
        "registered producer source/design names mismatch"
    );
    ensure!(
        m.producer
            .sources
            .values()
            .chain(m.producer.designs.values())
            .all(|b| valid_hash(&b.sha256) && b.bytes > 0 && b.bytes <= JSON_LIMIT as u64),
        "invalid producer bindings"
    );
    valid_relative(&m.producer.author_controls.path)?;
    valid_relative(&m.producer.emission_receipt.path)?;
    Ok(m)
}
fn validate_gate(v: &Value, manifest_sha: &str, float_sha: &str) -> Result<()> {
    let g: CfaGate = serde_json::from_value(v.clone())?;
    ensure!(
        g.schema == "m194e-cfa-commission-v1"
            && g.status == "PASS"
            && g.scope == SCOPE
            && g.sample_count == 15360,
        "CFA authority schema/status/scope/count"
    );
    ensure!(
        g.manifest.sha256 == manifest_sha
            && g.float_commission.sha256 == float_sha
            && valid_hash(&g.independent_verification.sha256),
        "CFA authority association mismatch"
    );
    Ok(())
}
fn validate_verification(
    v: &Value,
    gate: &Value,
    manifest_sha: &str,
    float_sha: &str,
) -> Result<()> {
    validate_gate(gate, manifest_sha, float_sha)?;
    let r: CfaVerification = serde_json::from_value(v.clone())?;
    ensure!(
        r.schema == "m194e-independent-cfa-verification-v1"
            && r.status == "PASS_CFA_CONVERSION_AND_PROVENANCE"
            && r.scope == SCOPE
            && !r.fixture_only
            && r.sample_count == 15360,
        "independent CFA result status/scope/count"
    );
    ensure!(
        r.externally_trusted_manifest_sha256 == manifest_sha
            && r.externally_trusted_float_commission_sha256 == float_sha,
        "independent CFA result authority association"
    );
    ensure!(
        r.source_unchanged
            && r.source_before == r.source_after
            && !r.source_before.is_empty()
            && !r.input_bindings.is_empty(),
        "independent source closure incomplete/changed"
    );
    ensure!(
        names_match(r.source_before.keys(), VERIFIER_NAMES)
            && r.source_before.values().all(|h| valid_hash(h)),
        "registered verifier source names/hash mismatch"
    );
    ensure!(
        r.units
            == json!({"black_dn":512,"cfa":"little-endian u16 DN","expected_cfa":"electrons with site channel factor","gain_dn_per_e":0.25,
        "noise":false,"scalar":"electrons","wb_applied":false,"white_exclusive_dn":15360}),
        "independent units mismatch"
    );
    ensure!(r.frames.len() == 5, "independent frame count mismatch");
    for (i, f) in r.frames.iter().enumerate() {
        let e = &f.exact_conversion;
        let d = &f.reference_discrepancy;
        ensure!(
            f.index == i
                && e.sample_count == 3072
                && valid_hash(&e.cfa_sha256)
                && valid_hash(&e.scalar_sha256)
                && valid_hash(&e.expected_cfa_sha256),
            "independent frame association"
        );
        ensure!(
            e.maximum_quantization_error_dn_rgb
                .iter()
                .all(|x| x.is_finite() && *x >= 0.0 && *x <= 0.5)
                && e.minimum_half_integer_margin_dn_rgb
                    .iter()
                    .all(|x| x.is_finite() && *x >= 0.0 && *x <= 0.5)
                && e.within_optical_discrepancy_allowance_rgb
                    .iter()
                    .all(|&x| x <= 3072)
                && e.rail_endpoint_admission
                    == "black512 valid; DN<15360 and rounded code<15360; no clipping",
            "invalid exact conversion record"
        );
        ensure!(
            d.channels.len() == 3
                && d.maximum_scalar_discrepancy_e.is_finite()
                && d.maximum_scalar_discrepancy_e >= 0.0
                && d.rms_scalar_discrepancy_e.is_finite()
                && d.rms_scalar_discrepancy_e >= 0.0
                && d.rounded_reference_code_differences <= 3072
                && !d.interpretation.is_empty(),
            "invalid reference discrepancy record"
        );
        for (j, c) in d.channels.iter().enumerate() {
            ensure!(
                c.channel == ["R", "G", "B"][j]
                    && c.code_differences_outside_allowance == 0
                    && c.rounded_reference_code_differences <= 3072
                    && c.sites_within_rounding_allowance <= 3072
                    && c.maximum_unquantized_reference_difference_dn.is_finite()
                    && c.maximum_unquantized_reference_difference_dn >= 0.0
                    && c.minimum_half_integer_margin_dn.is_finite()
                    && c.minimum_half_integer_margin_dn >= 0.0
                    && c.registered_float_allowance_dn == [0.00075, 0.001, 0.0006][j],
                "invalid channel discrepancy record"
            );
        }
    }
    ensure!(
        !r.command.is_empty()
            && !r.interpreter_argv.is_empty()
            && !r.completed_utc.is_empty()
            && !r.cwd.is_empty()
            && !r.executable.is_empty()
            && !r.numpy.is_empty()
            && !r.python.is_empty()
            && valid_hash(&r.reader_controls.sha256),
        "incomplete verifier provenance"
    );
    ensure!(
        r.xoptions
            .keys()
            .all(|k| ["faulthandler", "pycache_prefix"].contains(&k.as_str())),
        "unknown verifier interpreter option"
    );
    Ok(())
}

#[derive(Clone, Debug, Serialize)]
struct BoundFile {
    path: PathBuf,
    bytes: u64,
    sha256: String,
    limit: usize,
}
#[derive(Default)]
struct Bindings {
    files: BTreeMap<String, BoundFile>,
}
impl Bindings {
    fn read(
        &mut self,
        path: &Path,
        expected: &str,
        bytes: Option<u64>,
        limit: usize,
    ) -> Result<Vec<u8>> {
        ensure!(valid_hash(expected), "invalid bound hash");
        let path = path.canonicalize()?;
        let data = read_bounded(&path, limit)?;
        ensure!(
            bytes.is_none_or(|n| n == data.len() as u64) && digest(&data) == expected,
            "bound file size/hash mismatch: {}",
            path.display()
        );
        let item = BoundFile {
            path: path.clone(),
            bytes: data.len() as u64,
            sha256: expected.into(),
            limit,
        };
        let key = path.to_string_lossy().to_lowercase();
        if let Some(old) = self.files.get(&key) {
            ensure!(
                old.bytes == item.bytes && old.sha256 == item.sha256,
                "conflicting file aliases"
            );
        }
        self.files.insert(key, item);
        Ok(data)
    }
    fn json(&mut self, path: &Path, expected: &str) -> Result<Value> {
        parse_unique(&self.read(path, expected, None, JSON_LIMIT)?)
    }
    fn check(&self) -> Result<()> {
        for file in self.files.values() {
            let data = read_bounded(&file.path, file.limit)?;
            ensure!(
                data.len() as u64 == file.bytes && digest(&data) == file.sha256,
                "input/source changed since planning"
            );
        }
        Ok(())
    }
}
struct BridgeInputs {
    manifest: BridgeManifest,
    paths: Vec<PathBuf>,
    bindings: Bindings,
}
impl BridgeInputs {
    fn load(manifest: &Path, manifest_sha: &str, gate: &Path, gate_sha: &str) -> Result<Self> {
        ensure!(
            manifest_sha == MANIFEST_HASH && gate_sha == GATE_HASH,
            "unregistered external authority"
        );
        let mut bindings = Bindings::default();
        let manifest_value = bindings.json(manifest, manifest_sha)?;
        let m = validate_manifest(&manifest_value)?;
        let gate_value = bindings.json(gate, gate_sha)?;
        validate_gate(&gate_value, manifest_sha, FLOAT_HASH)?;
        let g: CfaGate = serde_json::from_value(gate_value.clone())?;
        // Absolute locations in the old gate are provenance, not a relocation
        // override. Their exact authority bytes stay pinned above.
        registered_absolute(&g.manifest.path)?;
        let float_path = registered_absolute(&g.float_commission.path)?;
        let float_value = bindings.json(&float_path, FLOAT_HASH)?;
        keys(
            &float_value,
            &[
                "schema",
                "status",
                "author_root",
                "author_bundle",
                "producer_sources",
                "scene",
                "ray_model",
                "numerical_contract",
                "expected_scalars",
                "numerical_receipts",
                "author_controls",
                "independent_evidence",
            ],
        )?;
        ensure!(
            float_value["schema"] == "m194e-float-commission-v1"
                && float_value["status"] == "PASS"
                && float_value["scene"] == m.scene
                && float_value["ray_model"] == m.ray_model
                && float_value["numerical_contract"] == m.numerical_contract,
            "float authority contract mismatch"
        );
        let root = manifest
            .canonicalize()?
            .parent()
            .context("manifest parent")?
            .to_path_buf();
        let gate_root = gate
            .canonicalize()?
            .parent()
            .context("gate parent")?
            .to_path_buf();
        let child = relative_path(&gate_root, &g.independent_verification.path)?;
        let rv = bindings.json(&child, &g.independent_verification.sha256)?;
        validate_verification(&rv, &gate_value, manifest_sha, FLOAT_HASH)?;
        let r: CfaVerification = serde_json::from_value(rv)?;
        let repo = repository()?;
        let e_root = repo.join("experiments/m194e-joint-pupil");
        for (name, h) in &r.source_before {
            let path = relative_path(&e_root, name)?;
            bindings.read(&path, h, None, JSON_LIMIT)?;
        }
        for (name, b) in &r.input_bindings {
            let path = registered_absolute(name)?;
            bindings.read(&path, &b.sha256, Some(b.bytes), JSON_LIMIT)?;
        }
        for (name, b) in &m.producer.sources {
            let path = relative_path(&repo, name)?;
            bindings.read(&path, &b.sha256, Some(b.bytes), JSON_LIMIT)?;
        }
        for (name, b) in &m.producer.designs {
            let path = relative_path(&e_root, name)?;
            bindings.read(&path, &b.sha256, Some(b.bytes), JSON_LIMIT)?;
        }
        let controls = relative_path(&repo, &m.producer.author_controls.path)?;
        bindings.read(
            &controls,
            &m.producer.author_controls.sha256,
            Some(m.producer.author_controls.bytes),
            JSON_LIMIT,
        )?;
        let emission = relative_path(&root, &m.producer.emission_receipt.path)?;
        bindings.read(
            &emission,
            &m.producer.emission_receipt.sha256,
            Some(m.producer.emission_receipt.bytes),
            JSON_LIMIT,
        )?;
        let mut paths = Vec::new();
        let mut seen = BTreeSet::new();
        for (i, f) in m.frames.iter().enumerate() {
            let proof = &r.frames[i].exact_conversion;
            ensure!(
                proof.cfa_sha256 == f.cfa.sha256
                    && proof.expected_cfa_sha256 == f.expected_cfa.sha256
                    && proof.scalar_sha256 == f.expected_scalar.sha256,
                "frame conversion proof mismatch"
            );
            for a in [&f.cfa, &f.expected_cfa, &f.expected_scalar] {
                let path = relative_path(&root, &a.path)?;
                bindings.read(
                    &path,
                    &a.sha256,
                    Some(a.bytes),
                    if a.dtype == "<u2" {
                        CFA_BYTES
                    } else {
                        JSON_LIMIT
                    },
                )?;
            }
            let path = relative_path(&root, &f.cfa.path)?;
            ensure!(
                seen.insert(path.to_string_lossy().to_lowercase()),
                "duplicate CFA path"
            );
            paths.push(path);
            let receipt = relative_path(&root, &f.numerical_receipt.path)?;
            bindings.read(
                &receipt,
                &f.numerical_receipt.sha256,
                Some(f.numerical_receipt.bytes),
                JSON_LIMIT,
            )?;
        }
        Ok(Self {
            manifest: m,
            paths,
            bindings,
        })
    }
}

#[derive(Clone, Copy, Debug, Deserialize, Serialize, PartialEq, Eq)]
#[serde(rename_all = "lowercase")]
enum ObserverMode {
    Off,
    Count,
    Placebo,
}
struct BridgeSource {
    paths: Vec<PathBuf>,
    hashes: Vec<String>,
    observer: ObserverMode,
    successes: Vec<AtomicUsize>,
    hooks: AtomicUsize,
    attempts: Vec<AtomicUsize>,
    fail_on_attempt: Option<(usize, usize)>,
}
impl BridgeSource {
    fn new(paths: Vec<PathBuf>, hashes: Vec<String>, observer: ObserverMode) -> Result<Self> {
        ensure!(
            paths.len() == 5 && hashes.len() == 5 && hashes.iter().all(|h| valid_hash(h)),
            "five source paths/hashes required"
        );
        Ok(Self {
            paths,
            hashes,
            observer,
            successes: (0..5).map(|_| AtomicUsize::new(0)).collect(),
            hooks: AtomicUsize::new(0),
            attempts: (0..5).map(|_| AtomicUsize::new(0)).collect(),
            fail_on_attempt: None,
        })
    }
    fn success_counts(&self) -> Vec<usize> {
        self.successes
            .iter()
            .map(|n| n.load(Ordering::SeqCst))
            .collect()
    }
    fn hook_calls(&self) -> usize {
        self.hooks.load(Ordering::SeqCst)
    }
    fn attempt_counts(&self) -> Vec<usize> {
        self.attempts
            .iter()
            .map(|n| n.load(Ordering::SeqCst))
            .collect()
    }
}
fn bridge_levels() -> Levels {
    Levels {
        black: 512.0,
        white: 15360.0,
    }
}
fn bridge_noise() -> NoiseModel {
    NoiseModel::new(
        [PlaneNoise {
            gain_dn_per_e: 0.25,
            read_noise_e: 4.0,
            levels: bridge_levels(),
        }; 4],
        160.0,
        NoiseProvenance::Fallback,
    )
}
fn bridge_frame(data: Vec<u16>, width: usize, height: usize, index: usize) -> Frame {
    Frame {
        data,
        stride: width,
        buffer_height: height,
        active: Region {
            x: 0,
            y: 0,
            width,
            height,
        },
        levels: bridge_levels(),
        iso: Some(160.0),
        wb_coeffs: [4.0 / 3.0, 1.0, 5.0 / 3.0, f32::NAN],
        xyz_to_cam_rgbe: [[0.0; 3]; 4],
        color_matrices: Vec::new(),
        camera: "M194f private synthetic bridge".into(),
        path: PathBuf::from(format!("M194F-NO-SUCH-RAW-{index}.ARW")),
    }
}
impl PyramidFrameSource for BridgeSource {
    fn len(&self) -> usize {
        self.paths.len()
    }
    fn decode(&self, index: usize) -> Result<Frame> {
        let path = self
            .paths
            .get(index)
            .context("bridge source index outside input")?;
        // Attempts are private fault-injection state, absent from healthy
        // execution and distinct from successful optional observer statistics.
        if let Some(failure) = self.fail_on_attempt {
            let attempt = self.attempts[index].fetch_add(1, Ordering::SeqCst) + 1;
            ensure!(
                failure != (index, attempt),
                "M194f injected decode failure at index {index}, attempt {attempt}"
            );
        }
        let bytes = read_bounded(path, CFA_BYTES)?;
        ensure!(
            bytes.len() == CFA_BYTES && digest(&bytes) == self.hashes[index],
            "source CFA length/hash changed"
        );
        let data: Vec<u16> = bytes
            .as_chunks::<2>()
            .0
            .iter()
            .map(|p| u16::from_le_bytes([p[0], p[1]]))
            .collect();
        ensure!(
            data.iter().all(|&n| (512..15360).contains(&n)),
            "source CFA outside admitted rails"
        );
        let frame = bridge_frame(data, 64, 48, index);
        if self.observer != ObserverMode::Off {
            self.hooks.fetch_add(1, Ordering::SeqCst);
            if self.observer == ObserverMode::Count {
                self.successes[index].fetch_add(1, Ordering::SeqCst);
            }
        }
        Ok(frame)
    }
}
#[derive(Clone, Copy, Debug)]
struct BridgeSettings {
    observer: ObserverMode,
    confidence: bool,
    exposure: u8,
}
impl BridgeSettings {
    fn validate(self) -> Result<()> {
        ensure!(self.exposure <= 1, "unregistered exposure");
        Ok(())
    }
}
fn identity_map(full: PlaneGeometry) -> WarpMap {
    let names: Vec<_> = (0..5)
        .map(|i| format!("M194F-NO-SUCH-RAW-{i}.ARW"))
        .collect();
    let entries: Vec<_> = names
        .iter()
        .map(|p| (p.as_str(), CFA_BYTES as u64))
        .collect();
    WarpMap::new(
        WarpProvenance {
            stack: StackIdentity::from_entries("M194f admitted five-frame CFA", &entries),
            strategy: "supplied identity map; no alignment solve".into(),
            heldout_px: None,
            cycle_floor_px: None,
            reference: 2,
            note: "identity reference2 is a coordinate gauge only".into(),
        },
        full,
        Resampler::CatmullRom,
        (0..5)
            .map(|_| FrameWarp::Placed(Similarity::IDENTITY))
            .collect(),
    )
}
fn bridge_options(
    output: PathBuf,
    settings: BridgeSettings,
    confidence: Option<PathBuf>,
) -> Result<MergeOptions> {
    settings.validate()?;
    let mut opts = options(output);
    ensure!(
        MergeConfig::default().admission == AdmissionMode::HardFloor
            && opts.pyramid.admission == AdmissionMode::HardFloor,
        "default admission changed"
    );
    opts.dir = PathBuf::from("M194F-NO-RAW-DIRECTORY");
    opts.exposure = f32::from(settings.exposure);
    opts.confidence_map = confidence;
    Ok(opts)
}
fn prepare_bridge(
    inputs: &BridgeInputs,
    settings: &BridgeSettings,
    environment: &BTreeMap<String, String>,
) -> Result<(PyramidDomain, align_cmd::CoverFit, Value)> {
    settings.validate()?;
    let full = PlaneGeometry::from_active(64, 48);
    let (map, fit) = align_cmd::cover_or_explain(identity_map(full), align_cmd::CoverMode::Crop);
    let domain = pyramid_domain(full, align_cmd::CoverMode::Crop, Some(&fit))?;
    let align_cmd::CoverFit::Cropped { k, .. } = fit else {
        bail!("actual cover did not return Crop")
    };
    let rect = domain.rect;
    let cfg = bridge_options(PathBuf::new(), *settings, None)?.pyramid;
    let sizes = level_sizes(rect.width, rect.height, cfg.bands);
    ensure!(sizes.len() == 2, "expected one Laplacian band plus base");
    let placements:Vec<_>=map.warps().iter().enumerate().map(|(i,w)| {
        let FrameWarp::Placed(t)=w else {unreachable!("known identity placements")};
        json!({"original_index":i,"local_index":i,"quad_similarity":{"a_re":t.a.re,"a_im":t.a.im,"b_re":t.b.re,"b_im":t.b.im}})
    }).collect();
    let exe = std::env::current_exe()?;
    let config = json!({"merge":"Pyramid","bands":cfg.bands,"gate":cfg.gate,"exponent":cfg.exponent,"sharpen_per_octave":cfg.sharpen_per_octave,
        "admission":format!("{:?}",cfg.admission),"select":format!("{:?}",cfg.select),"base":format!("{:?}",cfg.base),"mean_coarse":cfg.mean_coarse,
        "hull":format!("{:?}",cfg.hull),"hull_lambda":cfg.hull_lambda,"hull_low_only":cfg.hull_low_only,"hull_from_level":cfg.hull_from_level,
        "fallback":format!("{:?}",cfg.fallback),"fallback_k":cfg.fallback_k,"fallback_power":cfg.fallback_power,"significance_scale":cfg.significance_scale,
        "resampler":"CatmullRom","demosaic":"MHC","space":"CameraLinear","fullres_gather":true,"exposure_stops":settings.exposure,"auto_exposure":false,
        "confidence":settings.confidence,"photometric":"Off","gate_floor_enabled":gatefloor::enabled(),"measured_floor_bands":0,
        "floor_fallback":"empty measured beta; existing per-band fixed beta","ca":"off","defect":"off","restoration":"unset"});
    let noise = json!({"gain_dn_per_e":0.25,"read_noise_e":4.0,"black":512.0,"white":15360.0,"iso":160.0,
        "provenance":"Fallback: injected synthetic algorithm coefficients; noise draws off","prnu":false});
    let normalization = json!({"tiff_u16_to_dn":14848.0/65535.0,"second_black_subtraction":false,
        "input_rounding":"ties-to-even","output_rounding":"half-up after clipping"});
    let build = json!({"test_executable_sha256":hash_file(&exe)?,"bytes":fs::metadata(&exe)?.len(),"software":crate::SOFTWARE});
    let plan = json!({"schema":"m194f-consumer-plan-v1","authority":{"manifest_sha256":MANIFEST_HASH,"cfa_commission_sha256":GATE_HASH,"float_commission_sha256":FLOAT_HASH},
        "input_bindings":inputs.bindings.files,"sensor":inputs.manifest.sensor,"inputs":inputs.manifest.frames,"producer":inputs.manifest.producer,
        "full_native":[64,48],"full_quad":[full.width,full.height],"crop_quad":{"x":rect.x,"y":rect.y,"width":rect.width,"height":rect.height},
        "canonical_native_offset":[rect.x*2,rect.y*2],"output_native":[rect.width*2,rect.height*2],"output_channels":3,
        "reference_original_index":2,"reference_local_index":2,"placements":placements,"cover_fit":{"kind":"Crop","k":k},
        "level_sizes":sizes.iter().map(|s|[s.width,s.height]).collect::<Vec<_>>(),
        "noise":noise,"wb_f32":[4.0f32/3.0,1.0f32,5.0f32/3.0],"normalization":normalization,"config":config,
        "observer":{"mode":settings.observer,"excludes_planning_reads":true,"excludes_raw_prologue":true},"environment":environment,
        "build":build});
    Ok((domain, fit, plan))
}
fn validate_plan(saved: &Value, recomputed: &Value) -> Result<()> {
    ensure!(saved == recomputed, "trusted plan/config/geometry mismatch");
    Ok(())
}
fn run_bridge_source(
    opts: &MergeOptions,
    source: &impl PyramidFrameSource,
    domain: PyramidDomain,
    fit: align_cmd::CoverFit,
) -> Result<()> {
    ensure!(source.len() == 5, "prepared bridge requires five sources");
    let paths: Vec<_> = (0..5)
        .map(|i| PathBuf::from(format!("M194F-NO-SUCH-RAW-{i}.ARW")))
        .collect();
    ensure!(
        paths.iter().all(|p| !p.exists()),
        "RAW sentinel unexpectedly exists"
    );
    let local = domain.analysis();
    run_pyramid_prepared(
        opts,
        PreparedPyramid {
            paths: &paths,
            geom: domain.full,
            levels: bridge_levels(),
            noise: bridge_noise(),
            wb: Some([4.0 / 3.0, 1.0, 5.0 / 3.0]),
            xyz_to_cam: None,
            frame_bytes: CFA_BYTES,
            alignment: Some((identity_map(domain.full), "M194f supplied identity", fit)),
            domain,
            sizes: level_sizes(local.width, local.height, opts.pyramid.bands),
            defect_plan: None,
            prologue_secs: 0.0,
            align_secs: 0.0,
            t_start: Instant::now(),
            exposure: Exposure::resolve(false, opts.exposure, false)?,
        },
        source,
    )
}
fn tiff_receipt(path: &Path, channels: usize) -> Result<Value> {
    let mut decoder = tiff::decoder::Decoder::new(fs::File::open(path)?)?;
    let (width, height) = decoder.dimensions()?;
    let software = if channels == 3 {
        Some(decoder.get_tag_ascii_string(tiff::tags::Tag::Software)?)
    } else {
        ensure!(
            decoder.find_tag(tiff::tags::Tag::Software)?.is_none(),
            "unexpected Gray Software tag"
        );
        None
    };
    let tiff::decoder::DecodingResult::U16(pixels) = decoder.read_image()? else {
        bail!("expected u16 TIFF")
    };
    ensure!(
        pixels.len() == width as usize * height as usize * channels,
        "TIFF channel/payload extent"
    );
    let mut h = Sha256::new();
    for v in pixels {
        h.update(v.to_le_bytes());
    }
    Ok(
        json!({"path":path.canonicalize()?,"sha256":hash_file(path)?,"bytes":fs::metadata(path)?.len(),"width":width,"height":height,
        "channels":channels,"sample_type":"u16","pixel_sha256_le":hex(&h.finalize()),"software":software}),
    )
}
fn f_env(name: &str) -> Result<String> {
    std::env::var(format!("{F_PREFIX}{name}")).with_context(|| format!("missing {F_PREFIX}{name}"))
}
fn controlled_bridge_environment() -> Result<BTreeMap<String, String>> {
    let required = [
        ("STREHL_DEFECT", "off"),
        ("STREHL_FIX_CA", "off"),
        ("STREHL_FULLRES_GATHER", "1"),
        ("STREHL_PYRAMID_WORKERS", "2"),
    ];
    for (key, value) in required {
        ensure!(
            std::env::var(key).as_deref() == Ok(value),
            "required {key}={value}"
        );
    }
    ensure!(
        std::env::var("RAYON_NUM_THREADS").as_deref() == Ok("2"),
        "require two Rayon threads"
    );
    let keys = [
        "MANIFEST",
        "MANIFEST_SHA256",
        "CFA_COMMISSION",
        "CFA_COMMISSION_SHA256",
        "MODE",
        "PLAN",
        "OBSERVER",
        "CONFIDENCE",
        "EXPOSURE",
        "PLAN_SHA256",
        "OUTPUT",
        "RECEIPT",
        "CONFIDENCE_OUTPUT",
    ];
    let mut out = BTreeMap::new();
    for (key, value) in std::env::vars() {
        if key.to_ascii_uppercase().starts_with("STREHL_") {
            if let Some(suffix) = key.strip_prefix(F_PREFIX) {
                ensure!(keys.contains(&suffix), "unknown bridge environment {key}");
            } else {
                ensure!(
                    required.iter().any(|(k, _)| key == *k),
                    "unexpected render override {key}"
                );
                out.insert(key, value);
            }
        }
    }
    out.insert("RAYON_NUM_THREADS".into(), "2".into());
    Ok(out)
}
fn execute_bridge() -> Result<()> {
    let environment = controlled_bridge_environment()?;
    let settings = BridgeSettings {
        observer: match f_env("OBSERVER")?.as_str() {
            "off" => ObserverMode::Off,
            "count" => ObserverMode::Count,
            "placebo" => ObserverMode::Placebo,
            _ => bail!("unknown observer"),
        },
        confidence: match f_env("CONFIDENCE")?.as_str() {
            "0" => false,
            "1" => true,
            _ => bail!("unknown confidence flag"),
        },
        exposure: match f_env("EXPOSURE")?.as_str() {
            "0" => 0,
            "1" => 1,
            _ => bail!("unknown exposure"),
        },
    };
    let inputs = BridgeInputs::load(
        &PathBuf::from(f_env("MANIFEST")?),
        &f_env("MANIFEST_SHA256")?,
        &PathBuf::from(f_env("CFA_COMMISSION")?),
        &f_env("CFA_COMMISSION_SHA256")?,
    )?;
    let (domain, fit, plan) = prepare_bridge(&inputs, &settings, &environment)?;
    let plan_path = PathBuf::from(f_env("PLAN")?);
    let mode = f_env("MODE")?;
    if mode == "plan" {
        inputs.bindings.check()?;
        write_json_new(&plan_path, &plan)?;
        return Ok(());
    }
    ensure!(mode == "render", "unknown bridge mode");
    let plan_sha = f_env("PLAN_SHA256")?;
    validate_plan(&read_json_bound(&plan_path, &plan_sha)?, &plan)?;
    let output = PathBuf::from(f_env("OUTPUT")?);
    let receipt = PathBuf::from(f_env("RECEIPT")?);
    ensure!(
        !output.exists() && !receipt.exists(),
        "output/receipt already exists"
    );
    let confidence = if settings.confidence {
        Some(PathBuf::from(f_env("CONFIDENCE_OUTPUT")?))
    } else {
        ensure!(
            std::env::var(format!("{F_PREFIX}CONFIDENCE_OUTPUT")).is_err(),
            "confidence path without confidence"
        );
        None
    };
    if let Some(path) = &confidence {
        ensure!(
            !path.exists() && path != &output && path != &receipt && path != &plan_path,
            "confidence output exists or aliases protected path"
        );
    }
    let opts = bridge_options(output.clone(), settings, confidence.clone())?;
    let source = BridgeSource::new(
        inputs.paths.clone(),
        inputs
            .manifest
            .frames
            .iter()
            .map(|f| f.cfa.sha256.clone())
            .collect(),
        settings.observer,
    )?;
    run_bridge_source(&opts, &source, domain, fit)?;
    let calls = if settings.confidence { 2 } else { 1 };
    ensure!(
        source.success_counts()
            == vec![
                if settings.observer == ObserverMode::Count {
                    calls
                } else {
                    0
                };
                5
            ]
            && source.hook_calls()
                == if settings.observer == ObserverMode::Off {
                    0
                } else {
                    5 * calls
                },
        "decode observer counts mismatch"
    );
    let tiff = tiff_receipt(&output, 3)?;
    ensure!(
        tiff["width"] == domain.rect.width * 2 && tiff["height"] == domain.rect.height * 2,
        "actual output geometry mismatch"
    );
    let confidence = confidence
        .as_ref()
        .map(|p| tiff_receipt(p, 1))
        .transpose()?;
    if let Some(tiff) = &confidence {
        ensure!(
            tiff["width"] == domain.rect.width && tiff["height"] == domain.rect.height,
            "confidence grid mismatch"
        );
    }
    inputs.bindings.check()?;
    validate_plan(&read_json_bound(&plan_path, &plan_sha)?, &plan)?;
    write_json_new(
        &receipt,
        &json!({"schema":"m194f-consumer-receipt-v1","status":"complete","plan_sha256":plan_sha,"plan":plan,
        "successful_decode_counts":source.success_counts(),"hook_calls":source.hook_calls(),"output":tiff,"confidence":confidence,"inputs_unchanged":true}),
    )?;
    Ok(())
}
#[test]
#[ignore = "M194f explicit admitted manifest, plan and output only"]
fn m194f_production_bridge() -> Result<()> {
    execute_bridge()
}

mod m194f_author_tests {
    include!(concat!(
        env!("CARGO_MANIFEST_DIR"),
        "/../../experiments/m194f-production-bridge/author-controls.rs"
    ));
}

mod m194f_independent_tests {
    include!(concat!(
        env!("CARGO_MANIFEST_DIR"),
        "/../../experiments/m194f-production-bridge/independent-reader-controls.rs"
    ));
}
