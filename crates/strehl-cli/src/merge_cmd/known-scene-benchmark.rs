//! M194b test-local known-scene adapter. Shares production arithmetic unchanged.
use super::*;
use serde::{Deserialize, Serialize};
use serde_json::{Value, json};
use sha2::{Digest, Sha256};
use std::collections::{BTreeMap, BTreeSet};
use std::fs;
use std::io::Read;
use std::path::Component;
use std::sync::atomic::AtomicUsize;
use strehl_core::align::{Similarity, SimilarityParams};
use strehl_core::noise::{PlaneNoise, Provenance as NoiseProvenance};
use strehl_core::warpmap::Provenance as WarpProvenance;
use strehl_raw::Region;

const SCHEMA: &str = "m194b-known-scene-v1";
const PREFIX: &str = "STREHL_M194B_";
const ROI: [usize; 4] = [64, 64, 256, 176];

#[derive(Clone, Debug, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
struct Manifest {
    schema: String,
    scene: String,
    noise_enabled: bool,
    repeat: Option<u64>,
    sensor: Sensor,
    geometry: Geometry,
    frames: Vec<InputFile>,
    producer: Producer,
}

#[derive(Clone, Debug, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
struct Sensor {
    width: usize,
    height: usize,
    active_origin: [usize; 2],
    stride: usize,
    buffer_height: usize,
    black: f64,
    white: f64,
    iso: f64,
    wb: [f64; 3],
    noise_gain_dn_per_e: f64,
    read_noise_e: f64,
    cfa: String,
}

#[derive(Clone, Debug, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
struct Geometry {
    reference_index: usize,
    scale_centre_native: [f64; 2],
    frames: Vec<Placement>,
}

#[derive(Clone, Debug, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
struct Placement {
    index: usize,
    focus: f64,
    scale: f64,
}

#[derive(Clone, Debug, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
struct InputFile {
    index: usize,
    path: String,
    bytes: u64,
    sha256: String,
}

#[derive(Clone, Debug, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
struct Producer {
    preregistration_sha256: String,
    source_sha256: BTreeMap<String, String>,
    expected_electrons_sha256: String,
    command: Vec<String>,
}

/// Reject duplicate keys at every nesting level, including source digest maps,
/// before typed deserialization can discard any evidence of the duplicate.
struct UniqueValue(Value);
impl<'de> Deserialize<'de> for UniqueValue {
    fn deserialize<D: serde::Deserializer<'de>>(d: D) -> std::result::Result<Self, D::Error> {
        struct Visitor;
        impl<'de> serde::de::Visitor<'de> for Visitor {
            type Value = UniqueValue;
            fn expecting(&self, f: &mut std::fmt::Formatter) -> std::fmt::Result {
                f.write_str("JSON with unique object keys")
            }
            fn visit_map<A: serde::de::MapAccess<'de>>(
                self,
                mut a: A,
            ) -> std::result::Result<Self::Value, A::Error> {
                let mut map = serde_json::Map::new();
                while let Some((k, v)) = a.next_entry::<String, UniqueValue>()? {
                    if map.insert(k.clone(), v.0).is_some() {
                        return Err(serde::de::Error::custom(format!(
                            "duplicate JSON key {k:?}"
                        )));
                    }
                }
                Ok(UniqueValue(Value::Object(map)))
            }
            fn visit_seq<A: serde::de::SeqAccess<'de>>(
                self,
                mut a: A,
            ) -> std::result::Result<Self::Value, A::Error> {
                let mut values = Vec::new();
                while let Some(v) = a.next_element::<UniqueValue>()? {
                    values.push(v.0);
                }
                Ok(UniqueValue(Value::Array(values)))
            }
            fn visit_bool<E: serde::de::Error>(
                self,
                v: bool,
            ) -> std::result::Result<Self::Value, E> {
                Ok(UniqueValue(json!(v)))
            }
            fn visit_i64<E: serde::de::Error>(self, v: i64) -> std::result::Result<Self::Value, E> {
                Ok(UniqueValue(json!(v)))
            }
            fn visit_u64<E: serde::de::Error>(self, v: u64) -> std::result::Result<Self::Value, E> {
                Ok(UniqueValue(json!(v)))
            }
            fn visit_f64<E: serde::de::Error>(self, v: f64) -> std::result::Result<Self::Value, E> {
                let n = serde_json::Number::from_f64(v)
                    .ok_or_else(|| E::custom("nonfinite JSON number"))?;
                Ok(UniqueValue(Value::Number(n)))
            }
            fn visit_str<E: serde::de::Error>(
                self,
                v: &str,
            ) -> std::result::Result<Self::Value, E> {
                Ok(UniqueValue(json!(v)))
            }
            fn visit_string<E: serde::de::Error>(
                self,
                v: String,
            ) -> std::result::Result<Self::Value, E> {
                Ok(UniqueValue(json!(v)))
            }
            fn visit_unit<E: serde::de::Error>(self) -> std::result::Result<Self::Value, E> {
                Ok(UniqueValue(Value::Null))
            }
        }
        d.deserialize_any(Visitor)
    }
}

fn read_json(path: &Path, expected: &str) -> Result<Value> {
    valid_hash(expected)?;
    ensure!(
        fs::metadata(path)?.len() <= 1_048_576,
        "JSON receipt exceeds bounded size"
    );
    let bytes = fs::read(path)?;
    ensure!(
        digest(&bytes) == expected,
        "trusted JSON SHA-256 mismatch: {}",
        path.display()
    );
    Ok(serde_json::from_slice::<UniqueValue>(&bytes)?.0)
}

fn digest(bytes: &[u8]) -> String {
    hex(&Sha256::digest(bytes))
}
fn hex(bytes: &[u8]) -> String {
    bytes.iter().map(|b| format!("{b:02x}")).collect()
}
fn hash_file(path: &Path) -> Result<String> {
    let mut file = fs::File::open(path)?;
    let mut hash = Sha256::new();
    let mut buffer = [0u8; 65536];
    loop {
        let n = file.read(&mut buffer)?;
        if n == 0 {
            break;
        }
        hash.update(&buffer[..n]);
    }
    Ok(hex(&hash.finalize()))
}
fn valid_hash(s: &str) -> Result<()> {
    ensure!(
        s.len() == 64
            && s.bytes()
                .all(|b| b.is_ascii_digit() || (b'a'..=b'f').contains(&b)),
        "invalid lowercase SHA-256"
    );
    Ok(())
}

fn controlled_environment() -> Result<BTreeMap<String, String>> {
    controlled_environment_for(false)
}

fn controlled_environment_for(m194d: bool) -> Result<BTreeMap<String, String>> {
    controlled_environment_configured(m194d, false)
}
fn controlled_environment_configured(m194d: bool, direct: bool) -> Result<BTreeMap<String, String>> {
    let diagnostic = std::env::var(format!("{PREFIX}DIAGNOSTIC")).ok();
    ensure!(
        diagnostic
            .as_deref()
            .is_none_or(|value| value == "white-floor-isolation"),
        "unsupported diagnostic control"
    );
    let white_floor_diagnostic = diagnostic.is_some();
    ensure!(
        if white_floor_diagnostic {
            std::env::var(gatefloor::GATE_FLOOR_ENV).as_deref() == Ok("white")
        } else {
            std::env::var(gatefloor::GATE_FLOOR_ENV).is_err()
        },
        "white-floor isolation requires both diagnostic marker and white floor; baseline requires neither"
    );
    let required = [
        ("STREHL_DEFECT", "off"),
        ("STREHL_FIX_CA", "off"),
        ("STREHL_FULLRES_GATHER", "1"),
        ("STREHL_PYRAMID_WORKERS", "2"),
    ];
    for (key, value) in required {
        ensure!(
            std::env::var(key).as_deref() == Ok(value),
            "required environment {key}={value}"
        );
    }
    ensure!(
        std::env::var("RAYON_NUM_THREADS").as_deref() == Ok("2"),
        "require two Rayon threads"
    );
    let mut out = BTreeMap::new();
    for (key, value) in std::env::vars() {
        if key.to_ascii_uppercase().starts_with("STREHL_") {
            ensure!(
                key.starts_with(PREFIX)
                    || (m194d && key == "STREHL_M194D_ADMISSION")
                    || (direct && cfg!(feature = "native-direct-planes") && key == "STREHL_DIRECT_PLANES")
                    || key == "STREHL_BUILD_ID"
                    || (white_floor_diagnostic && key == gatefloor::GATE_FLOOR_ENV)
                    || required.iter().any(|(k, _)| key == *k),
                "unexpected render override {key}"
            );
            if !key.starts_with(PREFIX) {
                out.insert(key, value);
            }
        }
    }
    out.insert("RAYON_NUM_THREADS".into(), "2".into());
    Ok(out)
}

struct Inputs {
    manifest: Manifest,
    manifest_sha256: String,
    paths: Vec<PathBuf>,
}
impl Inputs {
    fn load(path: &Path, expected: &str) -> Result<Self> {
        let manifest: Manifest = serde_json::from_value(read_json(path, expected)?)?;
        ensure!(manifest.schema == SCHEMA, "unsupported known-scene schema");
        ensure!(
            ["flat", "plane", "color", "color-null"].contains(&manifest.scene.as_str()),
            "unknown scene"
        );
        ensure!(
            manifest.noise_enabled == manifest.repeat.is_some(),
            "noise/repeat mismatch"
        );
        if manifest.noise_enabled {
            ensure!(
                ["flat", "plane"].contains(&manifest.scene.as_str()),
                "color noise not commissioned"
            );
            ensure!(
                [701, 709, 719, 727, 733, 739, 743, 751].contains(&manifest.repeat.unwrap()),
                "unregistered noise seed"
            );
        }
        let s = &manifest.sensor;
        ensure!(
            (s.width, s.height) == (320, 240) && s.cfa == "RGGB",
            "unsupported dimensions/CFA"
        );
        ensure!(
            s.black == 512.0
                && s.white == 15360.0
                && s.iso == 160.0
                && s.noise_gain_dn_per_e == 0.25
                && s.read_noise_e == 4.0,
            "synthetic noise/level configuration mismatch"
        );
        ensure!(
            s.wb.iter()
                .zip([4.0 / 3.0, 1.0, 5.0 / 3.0])
                .all(|(a, b)| a.is_finite() && (*a - b).abs() < 1e-12),
            "synthetic WB mismatch"
        );
        ensure!(
            s.active_origin.iter().all(|&v| v <= 64),
            "active origin exceeds bound"
        );
        ensure!(
            (s.active_origin[0] + s.width..=s.active_origin[0] + s.width + 64).contains(&s.stride),
            "invalid stride"
        );
        ensure!(
            (s.active_origin[1] + s.height..=s.active_origin[1] + s.height + 64)
                .contains(&s.buffer_height),
            "invalid buffer height"
        );
        ensure!(
            manifest.frames.len() == 9
                && manifest.geometry.frames.len() == 9
                && manifest.geometry.reference_index == 4,
            "nine-frame/reference contract mismatch"
        );
        ensure!(
            manifest
                .geometry
                .scale_centre_native
                .iter()
                .zip([s.width, s.height])
                .all(|(&v, n)| v.is_finite() && v >= 0.0 && v < n as f64),
            "invalid native scale centre"
        );
        for (i, p) in manifest.geometry.frames.iter().enumerate() {
            ensure!(
                p.index == i
                    && p.focus == i as f64
                    && p.scale.is_finite()
                    && (0.5..2.0).contains(&p.scale),
                "invalid indexed placement"
            );
        }
        ensure!(
            manifest.geometry.frames[4].scale == 1.0,
            "reference placement must be identity"
        );
        valid_hash(&manifest.producer.preregistration_sha256)?;
        valid_hash(&manifest.producer.expected_electrons_sha256)?;
        ensure!(
            !manifest.producer.source_sha256.is_empty() && !manifest.producer.command.is_empty(),
            "missing producer binding"
        );
        for h in manifest.producer.source_sha256.values() {
            valid_hash(h)?;
        }
        let root = path
            .canonicalize()?
            .parent()
            .context("manifest has no parent")?
            .to_path_buf();
        let mut paths = Vec::new();
        let mut seen = BTreeSet::new();
        for (i, f) in manifest.frames.iter().enumerate() {
            ensure!(
                f.index == i && f.bytes == (s.width * s.height * 2) as u64,
                "frame index/length mismatch"
            );
            valid_hash(&f.sha256)?;
            let rel = Path::new(&f.path);
            ensure!(
                !rel.as_os_str().is_empty()
                    && rel.components().all(|c| matches!(c, Component::Normal(_))),
                "unsafe input path"
            );
            ensure!(
                rel.extension().and_then(|e| e.to_str()) == Some("cfa"),
                "input is not a CFA file"
            );
            let file = root.join(rel).canonicalize()?;
            ensure!(
                file.starts_with(&root),
                "input path escapes manifest directory"
            );
            ensure!(
                seen.insert(file.to_string_lossy().to_lowercase()),
                "duplicate input path"
            );
            ensure!(
                fs::metadata(&file)?.len() == f.bytes && hash_file(&file)? == f.sha256,
                "input file length/SHA-256 mismatch at {i}"
            );
            paths.push(file);
        }
        Ok(Self {
            manifest,
            manifest_sha256: expected.into(),
            paths,
        })
    }

    fn noise(&self) -> NoiseModel {
        let s = &self.manifest.sensor;
        NoiseModel::new(
            [PlaneNoise {
                gain_dn_per_e: s.noise_gain_dn_per_e as f32,
                read_noise_e: s.read_noise_e as f32,
                levels: self.levels(),
            }; 4],
            s.iso as f32,
            NoiseProvenance::Fallback,
        )
    }
    fn levels(&self) -> Levels {
        Levels {
            black: self.manifest.sensor.black as f32,
            white: self.manifest.sensor.white as f32,
        }
    }
    fn full(&self) -> PlaneGeometry {
        PlaneGeometry::from_active(self.manifest.sensor.width, self.manifest.sensor.height)
    }
    fn wb(&self) -> [f32; 3] {
        self.manifest.sensor.wb.map(|v| v as f32)
    }
    fn transforms(&self) -> Vec<FrameWarp> {
        let full = self.full();
        let cp = [full.width as f64 / 2.0, full.height as f64 / 2.0];
        let cq = self.manifest.geometry.scale_centre_native.map(|v| v / 2.0);
        self.manifest
            .geometry
            .frames
            .iter()
            .map(|p| {
                FrameWarp::Placed(Similarity::from_params(SimilarityParams {
                    ax: (1.0 - p.scale) * (cq[0] - cp[0]),
                    ay: (1.0 - p.scale) * (cq[1] - cp[1]),
                    g: p.scale - 1.0,
                    rot: 0.0,
                }))
            })
            .collect()
    }
    fn map(&self, indices: &[usize], reference: usize) -> WarpMap {
        let transforms = self.transforms();
        let entries: Vec<_> = indices
            .iter()
            .map(|&i| {
                (
                    self.manifest.frames[i].path.as_str(),
                    self.manifest.frames[i].bytes,
                )
            })
            .collect();
        WarpMap::new(
            WarpProvenance {
                stack: StackIdentity::from_entries("M194b trusted synthetic inputs", &entries),
                strategy: "M194b supplied forward map, no alignment solve".into(),
                heldout_px: None,
                cycle_floor_px: None,
                reference,
                note: "original reference4; local reindexing is recorded in receipt".into(),
            },
            self.full(),
            Resampler::CatmullRom,
            indices.iter().map(|&i| transforms[i].clone()).collect(),
        )
    }
}

fn options(out: PathBuf) -> MergeOptions {
    MergeOptions {
        linear_master: None,
        sensor_master: Default::default(),
        region_recipe: None,
        dir: PathBuf::from("M194B-NO-RAW-DIRECTORY"),
        out: Some(out),
        limit: None,
        srgb: false,
        space: image_out::OutputSpace::CameraLinear,
        demosaic: true,
        exposure: 0.0,
        auto_exposure: false,
        gates: vec![2.0],
        focus: None,
        flat_roi: None,
        detail_roi: None,
        index_map: None,
        n_eff_map: None,
        confidence_map: None,
        photometric: PhotometricMode::Off,
        photometric_source: SettingSource::Default,
        target_n_eff: None,
        stats: false,
        stats_placebo: false,
        confidence_tail: 0.05,
        resampler: Resampler::CatmullRom,
        backend: MergeBackend::Pyramid,
        cover: align_cmd::CoverMode::Crop,
        cover_source: SettingSource::Flag,
        pyramid: MergeConfig {
            bands: 3,
            gate: 2.0,
            ..MergeConfig::default()
        },
    }
}

fn options_with_admission(out: PathBuf, admission: Option<AdmissionMode>) -> MergeOptions {
    let mut opts = options(out);
    if let Some(mode) = admission {
        opts.pyramid.admission = mode;
    }
    opts
}

fn prepare(
    inputs: &Inputs,
    environment: &BTreeMap<String, String>,
) -> Result<(PyramidDomain, align_cmd::CoverFit, Value)> {
    prepare_with_admission(inputs, environment, None)
}

fn prepare_with_admission(
    inputs: &Inputs,
    environment: &BTreeMap<String, String>,
    admission: Option<AdmissionMode>,
) -> Result<(PyramidDomain, align_cmd::CoverFit, Value)> {
    let full = inputs.full();
    let indices: Vec<_> = (0..9).collect();
    let (map, fit) =
        align_cmd::cover_or_explain(inputs.map(&indices, 4), align_cmd::CoverMode::Crop);
    let domain = pyramid_domain(full, align_cmd::CoverMode::Crop, Some(&fit))?;
    let align_cmd::CoverFit::Cropped { k, .. } = fit else {
        bail!("actual cover did not return Crop")
    };
    ensure!(
        domain.rect.x * 2 <= ROI[0]
            && domain.rect.y * 2 <= ROI[1]
            && (domain.rect.x + domain.rect.width) * 2 >= ROI[2]
            && (domain.rect.y + domain.rect.height) * 2 >= ROI[3],
        "registered ROI does not survive actual Crop"
    );
    let placements:Vec<_>=map.warps().iter().enumerate().map(|(i,w)| {
        let FrameWarp::Placed(t)=w else { unreachable!("known placements must all be placed") };
        let p=t.to_params();
        json!({"original_index":i,"scale":inputs.manifest.geometry.frames[i].scale,"quad_similarity":{"a_re":t.a.re,"a_im":t.a.im,"b_re":t.b.re,"b_im":t.b.im},"params":{"ax":p.ax,"ay":p.ay,"g":p.g,"rot":p.rot}})
    }).collect();
    let cfg = options_with_admission(PathBuf::new(), admission).pyramid;
    let noise = inputs.noise();
    let plane = noise.plane(CfaPlane::R);
    let rect = domain.rect;
    let config_receipt = json!({"merge":"Pyramid","bands":cfg.bands,"gate":cfg.gate,"exponent":cfg.exponent,"sharpen_per_octave":cfg.sharpen_per_octave,"select":format!("{:?}",cfg.select),"base":format!("{:?}",cfg.base),"mean_coarse":cfg.mean_coarse,"hull":format!("{:?}",cfg.hull),"hull_lambda":cfg.hull_lambda,"hull_low_only":cfg.hull_low_only,"hull_from_level":cfg.hull_from_level,"fallback":format!("{:?}",cfg.fallback),"fallback_k":cfg.fallback_k,"fallback_power":cfg.fallback_power,"significance_scale":cfg.significance_scale,"resampler":"CatmullRom","demosaic":true,"space":"CameraLinear","exposure_stops":0,"auto_exposure":false,"photometric":"Off","gate_floor_enabled":gatefloor::enabled(),"ca":"off","defect":"off","restoration":"unset"});
    let mut plan = json!({
        "schema":"m194b-consumer-plan-v1","manifest_sha256":inputs.manifest_sha256,
        "scene":inputs.manifest.scene,"noise_enabled":inputs.manifest.noise_enabled,"repeat":inputs.manifest.repeat,
        "sensor":inputs.manifest.sensor,"producer":inputs.manifest.producer,"inputs":inputs.manifest.frames,
        "full_native":[inputs.manifest.sensor.width,inputs.manifest.sensor.height],"full_quad":[full.width,full.height],
        "crop_quad":{"x":rect.x,"y":rect.y,"width":rect.width,"height":rect.height},
        "cover_fit":{"kind":"Crop","k":k},
        "output_native":[rect.width*2,rect.height*2],"output_channels":3,
        "canonical_native_offset":[rect.x*2,rect.y*2],"roi_native":ROI,
        "reference_original_index":4,"scale_centre_native":inputs.manifest.geometry.scale_centre_native,"placements":placements,
        "noise":{"gain_dn_per_e":plane.gain_dn_per_e,"read_noise_e":plane.read_noise_e,"black":plane.levels.black,"white":plane.levels.white,"iso":noise.iso,"provenance":"Fallback: explicitly synthetic-known coefficients; no calibration claim","prnu":false,"variance_at_3000_dn":plane.variance(3000.0)},
        "wb_f32":inputs.wb(),"normalization":{"tiff_u16_to_dn":(15360.0-512.0)/65535.0,"second_black_subtraction":false},
        "config":config_receipt,
        "diagnostic":std::env::var(format!("{PREFIX}DIAGNOSTIC")).ok(),
        "level_sizes":level_sizes(rect.width,rect.height,cfg.bands).iter().map(|s|[s.width,s.height]).collect::<Vec<_>>(),
        "environment":environment,"software":crate::SOFTWARE,
    });
    if let Some(mode) = admission {
        plan["schema"] = json!("m194d-consumer-plan-v1");
        plan["config"]["admission"] = json!(format!("{:?}", cfg.admission));
        plan["config"]["admission_formula"] = json!(match mode {
            AdmissionMode::HardFloor => "hard-floor-v1",
            AdmissionMode::FloorPedestalV1 => {
                "floor-pedestal-v1: q=max(E-F,0); w=(hypot(q/max(F,1),1)/64)^p"
            }
        });
    }
    Ok((domain, fit, plan))
}

struct FileSource<'a> {
    inputs: &'a Inputs,
    indices: Vec<usize>,
    calls: Vec<AtomicUsize>,
    #[cfg(feature = "native-direct-planes")]
    direct_trace: direct_planes_bridge::Trace,
}
impl PyramidFrameSource for FileSource<'_> {
    #[cfg(feature = "native-direct-planes")]
    fn observe_direct_inputs(&self, index: usize, planes: &[Vec<f32>], luma: &[f32], beta: Option<&[f32]>) -> Result<()> {
        self.direct_trace.inputs(self.indices[index], planes, luma, beta)
    }
    #[cfg(feature = "native-direct-planes")]
    fn observe_direct_collapsed(&self, planes: &[Vec<f32>]) -> Result<()> {
        self.direct_trace.collapsed(planes)
    }
    fn len(&self) -> usize {
        self.indices.len()
    }
    fn decode(&self, index: usize) -> Result<Frame> {
        let &original = self
            .indices
            .get(index)
            .context("source index outside subset")?;
        let f = &self.inputs.manifest.frames[original];
        let path = &self.inputs.paths[original];
        ensure!(
            fs::metadata(path)?.len() == f.bytes,
            "source length changed after planning"
        );
        let bytes = fs::read(path)?;
        ensure!(
            bytes.len() as u64 == f.bytes && digest(&bytes) == f.sha256,
            "source hash changed after planning"
        );
        let s = &self.inputs.manifest.sensor;
        let mut data = vec![65000; s.stride * s.buffer_height];
        for y in 0..s.height {
            for x in 0..s.width {
                let i = 2 * (y * s.width + x);
                data[(s.active_origin[1] + y) * s.stride + s.active_origin[0] + x] =
                    u16::from_le_bytes([bytes[i], bytes[i + 1]]);
            }
        }
        self.calls[index].fetch_add(1, Ordering::SeqCst);
        let wb = self.inputs.wb();
        Ok(Frame {
            data,
            stride: s.stride,
            buffer_height: s.buffer_height,
            active: Region {
                x: s.active_origin[0],
                y: s.active_origin[1],
                width: s.width,
                height: s.height,
            },
            levels: self.inputs.levels(),
            iso: Some(s.iso as f32),
            wb_coeffs: [wb[0], wb[1], wb[2], f32::NAN],
            xyz_to_cam_rgbe: [[0.0; 3]; 4],
            color_matrices: Vec::new(),
            camera: "M194b explicit synthetic known scene".into(),
            path: PathBuf::from(format!("M194B-NO-SUCH-RAW-{original}.ARW")),
        })
    }
}

fn write_json_new(path: &Path, value: &Value) -> Result<()> {
    use std::io::Write;
    let mut file = fs::OpenOptions::new()
        .write(true)
        .create_new(true)
        .open(path)?;
    let mut bytes = serde_json::to_vec_pretty(value)?;
    bytes.push(b'\n');
    file.write_all(&bytes)?;
    file.sync_all()?;
    Ok(())
}
fn env(name: &str) -> Result<String> {
    std::env::var(format!("{PREFIX}{name}")).with_context(|| format!("missing {PREFIX}{name}"))
}

#[test]
#[ignore = "explicit generated fixture manifest and external hash bindings required"]
fn m194b_known_scene_consumer() -> Result<()> {
    run_known_scene_consumer(None)
}

fn run_known_scene_consumer(admission: Option<AdmissionMode>) -> Result<()> {
    run_known_scene_consumer_configured(admission, false)
}

#[cfg(feature = "native-boundary-radiance")]
#[test]
#[ignore = "Requires existing colour manifest and boundary no-treatment plan/output paths"]
fn m194b_boundary_radiance_no_treatment_consumer() -> Result<()> {
    run_known_scene_consumer_configured(None, true)
}

#[cfg(feature = "native-direct-planes")]
mod direct_planes_bridge {
    include!(concat!(env!("CARGO_MANIFEST_DIR"), "/../../experiments/native-direct-planes/bridge.rs"));
}
#[cfg(feature = "native-direct-planes")]
#[test]
#[ignore = "Requires fixed M194b source, explicit direct mode and bound plan/output paths"]
fn m194b_direct_planes_consumer() -> Result<()> {
    run_known_scene_consumer_modes(None, false, true)
}
fn run_known_scene_consumer_configured(admission: Option<AdmissionMode>, boundary_no_treatment: bool) -> Result<()> {
    run_known_scene_consumer_modes(admission, boundary_no_treatment, false)
}
fn run_known_scene_consumer_modes(admission: Option<AdmissionMode>, boundary_no_treatment: bool, direct_experiment: bool) -> Result<()> {
    #[cfg(not(feature = "native-direct-planes"))]
    ensure!(!direct_experiment, "direct-plane feature is disabled");
    #[cfg(feature = "native-direct-planes")]
    let direct = if direct_experiment {
        ensure!(admission.is_none() && !boundary_no_treatment, "direct bridge cannot combine other candidates");
        Some(direct_planes_bridge::Configuration::load()?)
    } else { None };
    #[cfg(not(feature = "native-boundary-radiance"))]
    ensure!(!boundary_no_treatment, "boundary radiance feature is disabled");
    if let Some(mode) = admission {
        let expected = match mode {
            AdmissionMode::HardFloor => "hard-floor",
            AdmissionMode::FloorPedestalV1 => "floor-pedestal-v1",
        };
        ensure!(
            std::env::var("STREHL_M194D_ADMISSION").as_deref() == Ok(expected),
            "M194d supplied mode disagrees with actual configuration"
        );
    }
    let environment = if direct_experiment {
        controlled_environment_configured(false, true)?
    } else if admission.is_some() {
        controlled_environment_for(true)?
    } else {
        controlled_environment()?
    };
    let manifest_path = PathBuf::from(env("MANIFEST")?);
    let inputs = Inputs::load(&manifest_path, &env("MANIFEST_SHA256")?)?;
    let (domain, fit, mut plan) = if admission.is_some() {
        prepare_with_admission(&inputs, &environment, admission)?
    } else {
        prepare(&inputs, &environment)?
    };
    if boundary_no_treatment {
        ensure!(inputs.manifest.scene == "color" && !inputs.manifest.noise_enabled,
            "boundary no-treatment control requires the existing genuine colour fixture");
        plan["schema"] = json!("native-boundary-radiance-colour-no-treatment-plan-v1");
        plan["boundary_radiance"] = json!("explicit no-treatment; M194g geometry unsupported");
    }
    #[cfg(feature = "native-direct-planes")]
    if let Some(config) = &direct { config.bind(&inputs, &mut plan)?; }
    let plan_path = PathBuf::from(env("PLAN")?);
    let mode = env("MODE")?;
    if mode == "plan" {
        write_json_new(&plan_path, &plan)?;
        return Ok(());
    }
    ensure!(mode == "render", "unknown consumer mode");
    let plan_hash = env("PLAN_SHA256")?;
    ensure!(
        read_json(&plan_path, &plan_hash)? == plan,
        "trusted plan/config/geometry mismatch"
    );
    let subset = env("SUBSET")?;
    let indices: Vec<_> = match subset.as_str() {
        "all" => (0..9).collect(),
        "best" => vec![4],
        _ => bail!("unknown frame subset"),
    };
    let output = PathBuf::from(env("OUTPUT")?);
    let receipt = PathBuf::from(env("RECEIPT")?);
    ensure!(
        !output.exists() && !receipt.exists(),
        "output/receipt already exists"
    );
    let mut opts = options_with_admission(output.clone(), admission);
    let confidence = std::env::var(format!("{PREFIX}CONFIDENCE"))
        .ok()
        .map(PathBuf::from);
    if let Some(path) = &confidence {
        ensure!(!path.exists(), "confidence output already exists");
    }
    opts.confidence_map = confidence.clone();
    let paths: Vec<_> = indices
        .iter()
        .map(|&i| PathBuf::from(format!("M194B-NO-SUCH-RAW-{i}.ARW")))
        .collect();
    ensure!(
        paths.iter().all(|p| !p.exists()),
        "synthetic RAW sentinel exists"
    );
    let local_reference = if subset == "all" { 4 } else { 0 };
    let source = FileSource {
        inputs: &inputs,
        calls: indices.iter().map(|_| AtomicUsize::new(0)).collect(),
        indices: indices.clone(),
        #[cfg(feature = "native-direct-planes")]
        direct_trace: direct_planes_bridge::Trace::new(direct.as_ref().is_some_and(|c|c.observer)),
    };
    #[cfg(feature = "native-boundary-radiance")]
    let configured_source = native_boundary_radiance::ConfiguredSource::optional(&source,
        boundary_no_treatment.then_some(native_boundary_radiance::Configuration::NoTreatment));
    #[cfg(feature = "native-boundary-radiance")]
    let consumer_source = &configured_source;
    #[cfg(not(feature = "native-boundary-radiance"))]
    let consumer_source = &source;
    let local = domain.analysis();
    #[cfg(feature = "native-direct-planes")]
    let direct_before = {
        align_cmd::direct_plane_observer(direct.as_ref().is_some_and(|c|c.observer));
        align_cmd::direct_plane_hits()
    };
    run_pyramid_prepared(
        &opts,
        PreparedPyramid {
            paths: &paths,
            geom: inputs.full(),
            levels: inputs.levels(),
            noise: inputs.noise(),
            wb: Some(inputs.wb()),
            xyz_to_cam: None,
            frame_bytes: inputs.manifest.sensor.stride * inputs.manifest.sensor.buffer_height * 2,
            alignment: Some((
                inputs.map(&indices, local_reference),
                "M194b known forward geometry",
                fit,
            )),
            domain,
            sizes: level_sizes(local.width, local.height, opts.pyramid.bands),
            defect_plan: None,
            prologue_secs: 0.0,
            align_secs: 0.0,
            t_start: Instant::now(),
            exposure: Exposure::resolve(false, 0.0, false)?,
        },
        consumer_source,
    )?;
    let calls: Vec<_> = source
        .calls
        .iter()
        .map(|v| v.load(Ordering::SeqCst))
        .collect();
    ensure!(
        calls
            .iter()
            .all(|&n| n == if confidence.is_some() { 2 } else { 1 }),
        "source decode count mismatch"
    );
    let mut tiff = tiff::decoder::Decoder::new(fs::File::open(&output)?)?;
    let (width, height) = tiff.dimensions()?;
    let software = tiff.get_tag_ascii_string(tiff::tags::Tag::Software)?;
    let tiff::decoder::DecodingResult::U16(pixels) = tiff.read_image()? else {
        bail!("output is not u16")
    };
    ensure!(
        (width as usize, height as usize) == (domain.rect.width * 2, domain.rect.height * 2)
            && pixels.len() == width as usize * height as usize * 3,
        "output dimensions/channels mismatch"
    );
    let mut pixel_hash = Sha256::new();
    for v in &pixels {
        pixel_hash.update(v.to_le_bytes());
    }
    let confidence_receipt = match confidence {
        Some(p) => Some(json!({"path":p.to_string_lossy(),"sha256":hash_file(&p)?})),
        None => None,
    };
    let receipt_schema = if direct_experiment {
        "native-direct-planes-consumer-receipt-v1"
    } else if boundary_no_treatment {
        "native-boundary-radiance-colour-no-treatment-receipt-v1"
    } else if admission.is_some() {
        "m194d-consumer-receipt-v1"
    } else {
        "m194b-consumer-receipt-v1"
    };
    let mut result = json!({"schema":receipt_schema,"manifest_sha256":inputs.manifest_sha256,"plan_sha256":plan_hash,"plan":plan,
        "frame_subset_original":indices,"reference_original_index":4,"reference_local_index":local_reference,"decode_counts":calls,
        "output":{"path":output.canonicalize()?.to_string_lossy(),"sha256":hash_file(&output)?,"bytes":fs::metadata(&output)?.len(),"width":width,"height":height,"channels":3,"sample_type":"u16","pixel_sha256_le":hex(&pixel_hash.finalize()),"software":software},
        "confidence":confidence_receipt,
    });
    #[cfg(feature = "native-direct-planes")]
    if let Some(config) = &direct {
        result["direct_planes_mode"] = json!(config.label);
        result["direct_planes_evidence"] = source.direct_trace.receipt(config, direct_before, domain)?;
    }
    write_json_new(&receipt, &result)?;
    Ok(())
}

mod band_admission_benchmark {
    include!(concat!(
        env!("CARGO_MANIFEST_DIR"),
        "/src/merge_cmd/band-admission-benchmark.rs"
    ));
}

mod joint_pupil_bridge {
    include!(concat!(
        env!("CARGO_MANIFEST_DIR"),
        "/src/merge_cmd/joint-pupil-bridge.rs"
    ));
}

mod noise_pupil_bridge {
    include!(concat!(
        env!("CARGO_MANIFEST_DIR"),
        "/src/merge_cmd/noise-pupil-bridge.rs"
    ));
}
