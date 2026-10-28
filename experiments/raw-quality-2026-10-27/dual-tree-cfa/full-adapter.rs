// Fixed six-orientation candidate; root alone schedules this ignored diagnostic.
// Root owns build, execution bounds and the decision whether to run this source.
use super::*;
use serde::Deserialize;
use serde_json::{Value, json};
use sha2::{Digest, Sha256};
use std::{
    fs::{File, OpenOptions},
    io::{BufReader, BufWriter, Read, Write},
    time::SystemTime,
};
use strehl_core::align::Similarity;
use strehl_core::pyramid::{Fallback, Hull};

const SOURCE_SHA: &str = "e85572179c8a98f5a2de2be5c81cd0b1bdeae67999aa00e585c6dde35f531154";
const ORDER_SHA: &str = "0235564cf5131e7eb5e4ea251c16ea9272f6a55a9d8cc6efc717970615a30d6f";
const MAP_SHA: &str = "4a76cd0c56c3a525e70f5bf72b965adb706131618c5bf49d0ae853fbf341c225";
const BASE_EXE_SHA: &str = "89a0d92aad1628cfdfe75f39d2627ed3679990c5b3381d8839f6cce61b7f2388";
const BASE_MASTER_SHA: &str = "5dc571cce0d9e310f1f06b6e7f3c78faae8fb4ee4f12c94ff76d1d0c0e3fb655";
const CROP: [usize; 4] = [34, 23, 3448, 2298];
const MATRIX: [[f32; 3]; 3] = [
    [0.746, -0.2365, -0.0588],
    [-0.5687, 1.3442, 0.2474],
    [-0.0624, 0.1156, 0.6584],
];

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct Config {
    schema: u32,
    out_dir: PathBuf,
    mode: String,
    expected_test_executable_sha256: String,
}
fn digest(h: Sha256) -> String {
    h.finalize().iter().map(|v| format!("{v:02x}")).collect()
}
fn sha(path: &Path) -> Result<String> {
    let mut file = File::open(path)?;
    let mut h = Sha256::new();
    let mut buf = vec![0u8; 1 << 20];
    loop {
        let n = file.read(&mut buf)?;
        if n == 0 {
            break;
        }
        h.update(&buf[..n]);
    }
    Ok(digest(h))
}
fn f32_hash(values: &[f32]) -> String {
    let mut h = Sha256::new();
    let mut bytes = vec![0u8; 65536];
    for chunk in values.chunks(bytes.len() / 4) {
        for (dst, v) in bytes.chunks_exact_mut(4).zip(chunk) {
            dst.copy_from_slice(&v.to_bits().to_le_bytes());
        }
        h.update(&bytes[..4 * chunk.len()]);
    }
    digest(h)
}
fn write_json(path: &Path, value: &Value) -> Result<()> {
    let mut out = OpenOptions::new().write(true).create_new(true).open(path)?;
    serde_json::to_writer_pretty(&mut out, value)?;
    writeln!(out)?;
    Ok(())
}
fn stamp(path: &Path) -> Result<(u64, SystemTime)> {
    let m = std::fs::metadata(path)?;
    Ok((m.len(), m.modified()?))
}
fn file_record(path: &Path) -> Result<Value> {
    Ok(json!({"path":path,"sha256":sha(path)?,"bytes":std::fs::metadata(path)?.len()}))
}
fn same_planes(a: &[Vec<f32>], b: &[Vec<f32>]) -> bool {
    a.len() == b.len()
        && a.iter().zip(b).all(|(a, b)| {
            a.len() == b.len() && a.iter().zip(b).all(|(a, b)| a.to_bits() == b.to_bits())
        })
}

fn full_gather(
    frame: &Frame,
    warp: Similarity,
    crop: align_cmd::CropRect,
) -> Result<Vec<Vec<f32>>> {
    ensure!(
        frame.geometry()
            == PlaneGeometry {
                width: 3516,
                height: 2344
            }
            && [crop.x, crop.y, crop.width, crop.height] == CROP,
        "fixed full domain"
    );
    let id = strehl_raw::identity(&frame.path);
    ensure!(
        strehl_core::optics::profile_for_capture_env(id.model.as_deref(), id.lens_type3)?.is_none()
            && phase_packed_rgb::full_stack::full_source_supported(
                warp,
                frame.geometry(),
                crop,
                None
            ),
        "CA-off covered pull required"
    );
    let mut current = frame.clone();
    let mut planes = vec![vec![0.0; crop.width * crop.height]; 4];
    // Exactly the canonical full-resolution CPU remosaic followed by its
    // actual extraction helper. The canonical green-only noise probe setting
    // cannot shorten this explicitly four-phase candidate gather.
    align_cmd::warp_frame_in_place(
        &mut current,
        warp,
        frame.geometry(),
        Resampler::CatmullRom,
        &mut WarpScratch::new(frame.geometry()),
    )?;
    extract_planes(
        &current.data,
        current.stride,
        current.active.x,
        current.active.y,
        current.levels.black,
        PyramidDomain::cropped(frame.geometry(), crop)?,
        &BAND_PLANE_OFFSETS,
        &mut planes,
    )?;
    ensure!(
        planes.iter().flatten().all(|v| v.is_finite()),
        "nonfinite gather"
    );
    Ok(planes)
}
struct OneSource<'a> {
    frame: &'a Frame,
    index: usize,
}
impl PyramidFrameSource for OneSource<'_> {
    fn len(&self) -> usize {
        299
    }
    fn decode(&self, index: usize) -> Result<Frame> {
        ensure!(index == self.index, "one decoded source");
        Ok(self.frame.clone())
    }
}
fn exact_baseline(path: &Path) -> Result<strehl_edit::DisplayBaseline> {
    let mut d = tiff::decoder::Decoder::new(BufReader::new(File::open(path)?))?;
    ensure!(
        d.dimensions()? == (6896, 4596) && d.colortype()? == tiff::ColorType::RGB(32),
        "held linear master dimensions/type"
    );
    let description = d.get_tag_ascii_string(tiff::tags::Tag::ImageDescription)?;
    let line = description
        .lines()
        .find_map(|line| line.strip_prefix("DisplayBaseline: "))
        .context("exact DisplayBaseline metadata absent")?;
    let baseline: strehl_edit::DisplayBaseline = serde_json::from_str(line)?;
    ensure!(
        [
            baseline.black,
            baseline.white,
            baseline.contrast,
            baseline.exposure_gain
        ]
        .iter()
        .all(|v| v.is_finite())
            && baseline.white > baseline.black
            && baseline.contrast == 0.55
            && baseline.exposure_gain == 1.0,
        "held display baseline values differ"
    );
    Ok(baseline)
}
fn write_result(
    out: &Path,
    name: &str,
    planes: &[Vec<f32>],
    levels: Levels,
    wb: [f32; 4],
    dev: &image_out::Develop,
) -> Result<Value> {
    let width = 2 * CROP[2];
    let height = 2 * CROP[3];
    let cfa_path = out.join(format!("{name}-cfa-dn.f32le"));
    let mut raw = BufWriter::new(
        OpenOptions::new()
            .write(true)
            .create_new(true)
            .open(&cfa_path)?,
    );
    let mut row = vec![0u8; 4 * width];
    for y in 0..height {
        for x in 0..width {
            let c = 2 * (y % 2) + x % 2;
            let v = planes[c][(y / 2) * CROP[2] + x / 2];
            row[4 * x..4 * x + 4].copy_from_slice(&v.to_le_bytes());
        }
        raw.write_all(&row)?;
    }
    raw.flush()?;
    drop(raw);
    let gains = [wb[0] / wb[1], 1.0, 1.0, wb[2] / wb[1]];
    let mut mosaic = vec![0.0f32; width * height];
    mosaic
        .par_chunks_mut(width)
        .enumerate()
        .for_each(|(y, row)| {
            for (x, v) in row.iter_mut().enumerate() {
                let c = 2 * (y % 2) + x % 2;
                *v =
                    planes[c][(y / 2) * CROP[2] + x / 2].max(0.0) * gains[c] * 1.0 / levels.range();
            }
        });
    let master = out.join(format!("{name}-master.tiff"));
    let linear = out.join(format!("{name}-linear.tiff"));
    image_out::write_demosaiced_with_master(
        &master,
        width,
        height,
        &mosaic,
        dev,
        Some(&linear),
        None,
    )?;
    drop(mosaic);
    Ok(
        json!({"cfa":file_record(&cfa_path)?,"cfa_format":"headerless row-major RGGB float32 LE, black-subtracted DN, 6896x4596",
        "rgb16":file_record(&master)?,"linear_rgb32":file_record(&linear)?,"entire_output":true}),
    )
}
fn rgb16_hash(path: &Path) -> Result<String> {
    let mut d = tiff::decoder::Decoder::new(BufReader::new(File::open(path)?))?;
    ensure!(
        d.dimensions()? == (6896, 4596) && d.colortype()? == tiff::ColorType::RGB(16),
        "delivered output dimensions/type"
    );
    let pixels = match d.read_image()? {
        tiff::decoder::DecodingResult::U16(p) => p,
        _ => anyhow::bail!("RGB16 pixels required"),
    };
    ensure!(
        !d.more_images() && pixels.len() == 6896 * 4596 * 3,
        "single complete RGB16 image required"
    );
    let mut h = Sha256::new();
    let mut bytes = vec![0u8; 65536];
    for chunk in pixels.chunks(bytes.len() / 2) {
        for (dst, v) in bytes.chunks_exact_mut(2).zip(chunk) {
            dst.copy_from_slice(&v.to_le_bytes());
        }
        h.update(&bytes[..2 * chunk.len()]);
    }
    Ok(digest(h))
}

fn float_pixels_hash(path: &Path, channels: usize) -> Result<String> {
    let mut limits = tiff::decoder::Limits::default();
    // The pinned complete RGB32 image is 380,328,192 bytes. Admit that exact
    // geometry's buffer, without disabling TIFF resource limits generally.
    limits.decoding_buffer_size = 6896 * 4596 * channels * std::mem::size_of::<f32>();
    let mut d = tiff::decoder::Decoder::new(BufReader::new(File::open(path)?))?.with_limits(limits);
    ensure!(d.dimensions()? == (6896, 4596), "held float geometry");
    let p = match d.read_image()? {
        tiff::decoder::DecodingResult::F32(v) => v,
        _ => anyhow::bail!("float32 required"),
    };
    ensure!(
        !d.more_images() && p.len() == 6896 * 4596 * channels && p.iter().all(|v| v.is_finite()),
        "complete single float image"
    );
    Ok(f32_hash(&p))
}
fn validate_frame(frame: &Frame, full: PlaneGeometry) -> Result<()> {
    ensure!(
        frame.camera == "ILCE-7CM2"
            && frame.iso == Some(100.0)
            && frame.levels
                == Levels {
                    black: 512.0,
                    white: 15360.0
                }
            && frame.geometry() == full
            && frame.active.width == 7032
            && frame.active.height == 4688
            && frame.wb_coeffs[..3] == [1637.0 / 1024.0, 1.0, 2774.0 / 1024.0]
            && frame.xyz_to_cam_rgb() == Some(MATRIX),
        "held source metadata changed"
    );
    Ok(())
}

fn material(path: &Path) -> Result<Value> {
    use tiff::tags::Tag;
    let mut d = tiff::decoder::Decoder::new(BufReader::new(File::open(path)?))?;
    let description = d.get_tag_ascii_string(Tag::ImageDescription)?;
    let icc = d.get_tag_u8_vec(Tag::IccProfile)?;
    ensure!(!icc.is_empty(), "ICC required");
    let mut hash = Sha256::new();
    hash.update(&icc);
    let mut tags = std::collections::BTreeMap::new();
    for tag in [
        Tag::BitsPerSample,
        Tag::PhotometricInterpretation,
        Tag::SamplesPerPixel,
        Tag::SampleFormat,
        Tag::Orientation,
        Tag::XResolution,
        Tag::YResolution,
        Tag::ResolutionUnit,
    ] {
        tags.insert(format!("{tag:?}"), format!("{:?}", d.get_tag(tag).ok()));
    }
    Ok(json!({"description":description,"icc_sha256":digest(hash),"material_tags":tags}))
}

const BASE_LINEAR_SHA: &str = "8f3d9ec977f06d8fd44e070f27ab97e398611436cef17271fa6b889067ea1960";
const BASE_SENSOR_PAYLOAD_SHA: &str =
    "1a442c1638eb8f1b68d31dd502acc670eedf0f35463e864dd5f21ee26d4112b0";
const BASE_RGB_PIXELS_SHA: &str =
    "f98cb4d9bc281eb9f28f4e618878607d7e7317eeb7ac20b349f35dfee81c280c";
const BASE_LINEAR_PIXELS_SHA: &str =
    "ee2b711bc36e48b9913531e1c615bd265ad06fd395a74f6224ca94392e32be09";
fn errors(a: &[Vec<f32>], b: &[Vec<f32>]) -> Result<Value> {
    ensure!(a.len() == 4 && b.len() == 4, "four physical CFA phases");
    let mut rows = Vec::new();
    for phase in 0..4 {
        ensure!(
            a[phase].len() == CROP[2] * CROP[3] && a[phase].len() == b[phase].len(),
            "complete phase geometry"
        );
        let mut max = 0.0f32;
        let mut sum = 0.0f64;
        for (&x, &y) in a[phase].iter().zip(&b[phase]) {
            ensure!(x.is_finite() && y.is_finite(), "finite comparison");
            let d = x - y;
            max = max.max(d.abs());
            sum += f64::from(d) * f64::from(d);
        }
        let rms = (sum / a[phase].len() as f64).sqrt();
        rows.push(json!({"phase":phase,"maximum_dn":max,"rms_dn":rms,"pass":max<=0.05&&rms<=0.01}));
    }
    let pass = rows.iter().all(|v| v["pass"] == true);
    Ok(
        json!({"phases":rows,"pass":pass,"maximum_bound_dn":0.05,"rms_bound_dn":0.01,"before_hull":true}),
    )
}
fn finite_four(p: &[Vec<f32>]) -> bool {
    p.len() == 4
        && p.iter()
            .all(|v| v.len() == CROP[2] * CROP[3] && v.iter().all(|x| x.is_finite()))
}
fn run(full_run: bool) -> Result<()> {
    let total = Instant::now();
    for (key, value) in [
        ("STREHL_ALIGN", "1"),
        ("STREHL_FULLRES_GATHER", "1"),
        ("STREHL_DIRECT_PLANES", "off"),
        ("STREHL_PROBE_GATHER", "green"),
        ("STREHL_WARP_WRITEBACK", "parallel"),
        ("STREHL_GPU_GATHER", "off"),
        ("STREHL_FIX_CA", "off"),
        ("STREHL_DEFECT", "off"),
        ("STREHL_TEMPORAL_ENERGY", "off"),
        ("STREHL_SPATIAL_NOISE_FLOOR", "off"),
        ("STREHL_DEMOSAIC", "malvar"),
    ] {
        ensure!(
            std::env::var(key).as_deref() == Ok(value),
            "held environment {key}"
        );
    }
    ensure!(
        align_cmd::fullres_gather_enabled()
            && gatefloor::enabled()
            && align_cmd::direct_plane_mode()? == align_cmd::DirectPlaneMode::Off
            && !align_cmd::native_gpu_integration::gpu_gather_enabled()?,
        "held CPU canonical route"
    );
    ensure!(
        std::env::var_os("STREHL_LOCAL_PLACEMENT_FILE").is_none()
            && strehl_core::pyramid::fine_support_candidate::environment_mode()
                == strehl_core::pyramid::fine_support_candidate::Mode::Off,
        "no competing intervention"
    );
    let config_path = PathBuf::from(
        std::env::var_os("STREHL_DUAL_TREE_CFA_CONFIG").context("explicit config required")?,
    );
    let config_sha = sha(&config_path)?;
    let config: Config = serde_json::from_slice(&std::fs::read(&config_path)?)?;
    ensure!(
        config.schema == 1
            && config.mode == if full_run { "full" } else { "cost" }
            && config.expected_test_executable_sha256.len() == 64,
        "config mode/schema"
    );
    let repo = Path::new(env!("CARGO_MANIFEST_DIR"))
        .join("../..")
        .canonicalize()?;
    let campaign = repo.join("outputs/raw-quality-2026-10-26");
    let base = campaign.join("weevil-107-sensor-ca-off");
    ensure!(
        config.out_dir.is_absolute()
            && !config.out_dir.exists()
            && config
                .out_dir
                .parent()
                .context("output parent")?
                .canonicalize()?
                .starts_with(repo.join("outputs").canonicalize()?),
        "fresh workspace output required"
    );
    let exe = std::env::current_exe()?;
    ensure!(
        sha(&exe)? == config.expected_test_executable_sha256,
        "test executable changed"
    );
    let map_path = campaign.join("weevil-107-ca-off-alignment.txt");
    let order_path = campaign.join("weevil-107-baseline/input-order.json");
    let linear_path = base.join("linear-master.tiff");
    ensure!(
        sha(&map_path)? == MAP_SHA && sha(&order_path)? == ORDER_SHA,
        "held map/order changed"
    );
    ensure!(
        sha(&campaign.join("baseline-strehl.exe"))? == BASE_EXE_SHA
            && sha(&base.join("stack-master.tiff"))? == BASE_MASTER_SHA
            && sha(&linear_path)? == BASE_LINEAR_SHA,
        "held baseline changed"
    );
    ensure!(
        sha(&base.join("sensor-master.tiff"))?
            == "fa5825b834121b28547fc6e2154623740a24acc4e1616915c1c197bc90be2b02",
        "held sensor master changed"
    );
    ensure!(
        sha(&base.join("sensor-master.tiff.json"))?
            == "e22ad2fad5ac7307a4560ccee4b0ad232edf1dc9449fdce7057022bff9341f21",
        "held sensor sidecar changed"
    );
    // This payload hash is the exact encoded.payload_sha256 in that pinned sidecar.
    // The complete TIFF hash above binds its bytes; avoid treating CFA photometric
    // data as an RGB/gray TIFF in the general image decoder.
    let display = exact_baseline(&linear_path)?;
    let order: Vec<Value> = serde_json::from_slice(&std::fs::read(&order_path)?)?;
    ensure!(
        order.len() == 299
            && order[149]["index"] == 149
            && order[149]["sha256"].as_str() == Some(SOURCE_SHA),
        "held299 order"
    );
    let paths = order
        .iter()
        .map(|v| v["path"].as_str().map(PathBuf::from).context("source path"))
        .collect::<Result<Vec<_>>>()?;
    let before = paths.iter().map(|p| stamp(p)).collect::<Result<Vec<_>>>()?;
    for (i, item) in order.iter().enumerate() {
        ensure!(
            item["index"].as_u64() == Some(i as u64)
                && item["bytes"].as_u64() == Some(before[i].0)
                && item["mtime_ns"].as_u64()
                    == Some(
                        before[i]
                            .1
                            .duration_since(SystemTime::UNIX_EPOCH)?
                            .as_nanos() as u64
                    ),
            "source metadata differs"
        );
        if full_run || i == 149 {
            ensure!(
                Some(sha(&paths[i])?.as_str()) == item["sha256"].as_str(),
                "source content differs"
            );
        }
    }
    let entries = paths
        .iter()
        .enumerate()
        .map(|(i, p)| {
            Ok((
                p.file_name()
                    .and_then(|v| v.to_str())
                    .context("filename")?
                    .to_owned(),
                before[i].0,
            ))
        })
        .collect::<Result<Vec<_>>>()?;
    let original_map = WarpMap::load(&map_path)?;
    original_map
        .provenance()
        .stack
        .check(&StackIdentity::from_entries("107MSDCF", &entries))?;
    ensure!(
        original_map.len() == 299
            && original_map.placed_count() == 299
            && original_map.provenance().reference == 149
            && original_map.resampler() == Resampler::CatmullRom,
        "complete held map contract"
    );
    let (map, fit) = align_cmd::cover_or_explain(original_map, align_cmd::CoverMode::Crop);
    let crop = fit.rect().context("crop")?;
    ensure!(
        [crop.x, crop.y, crop.width, crop.height] == CROP,
        "held crop changed"
    );
    let full = map.geometry();
    ensure!(
        full == PlaneGeometry {
            width: 3516,
            height: 2344
        },
        "held geometry"
    );
    for i in 0..299 {
        let id = strehl_raw::identity(&paths[i]);
        ensure!(
            strehl_core::optics::profile_for_capture_env(id.model.as_deref(), id.lens_type3)?
                .is_none()
                && phase_packed_rgb::full_stack::full_source_supported(
                    map.placement(i)?,
                    full,
                    crop,
                    None
                ),
            "CA-off/source support differs"
        );
    }
    let cfg = MergeConfig::default();
    ensure!(
        cfg.bands == 7
            && cfg.gate == 2.0
            && cfg.exponent == 2.0
            && cfg.sharpen_per_octave == 1.4
            && cfg.select == SelectMode::SoftPower
            && cfg.admission == AdmissionMode::HardFloor
            && cfg.base == BaseBand::Mean
            && cfg.mean_coarse == 0
            && cfg.hull == Hull::InputRange
            && cfg.fallback == Fallback::Mean
            && cfg.significance_scale == 0.0,
        "held production7 defaults required"
    );
    let threads: usize = std::env::var("RAYON_NUM_THREADS")?.parse()?;
    ensure!(
        threads == 4 && std::env::var("STREHL_PYRAMID_WORKERS").as_deref() == Ok("4"),
        "fixed4 execution threads"
    );
    let pool = ThreadPoolBuilder::new().num_threads(threads).build()?;
    let decode_start = Instant::now();
    let first_index = if full_run { 0 } else { 149 };
    let first = strehl_raw::decode(&paths[first_index])?;
    let first_decode_seconds = decode_start.elapsed().as_secs_f64();
    validate_frame(&first, full)?;
    let levels = first.levels;
    let wb = first.wb_coeffs;
    let plan = phase_packed_rgb::full_stack::chunk_plan(full, first.allocated_bytes(), 299, cfg);
    ensure!(
        plan.canonical_chunks == 4 && plan.per_chunk == 75,
        "held4 arithmetic chunks changed"
    );
    let noise = profile::noise_model_for(&first.camera, first.iso, levels);
    ensure!(
        noise.is_trustworthy() && noise.prnu().is_none(),
        "one injected temporal model"
    );
    let sizes = level_sizes(crop.width, crop.height, cfg.bands);
    std::fs::create_dir(&config.out_dir)?;

    for p in [CfaPlane::R, CfaPlane::G1, CfaPlane::G2, CfaPlane::B] {
        let n = noise.plane(p);
        ensure!(
            n.gain_dn_per_e.to_bits() == 0.22893773f32.to_bits()
                && n.read_noise_e.to_bits() == 4.2f32.to_bits()
                && n.levels == levels,
            "held injected phase noise"
        );
    }
    let candidate_plan = Plan::new(crop.width, crop.height)?;
    ensure!(
        (
            candidate_plan.padded_width,
            candidate_plan.padded_height,
            candidate_plan.levels
        ) == (6912, 4608, 7),
        "fixed mirrored seven-level plan"
    );
    write_json(
        &config.out_dir.join("started.json"),
        &json!({
            "mode":config.mode,"held_stack_count":299,"map":file_record(&map_path)?,"order":file_record(&order_path)?,
            "test_executable":file_record(&exe)?,"config":file_record(&config_path)?,"baseline_linear":file_record(&linear_path)?,
            "crop_quad":CROP,"native_dimensions":[6896,4596],"reference":149,
            "canonical_chunk_lengths":[75,75,75,74],"candidate_source_order":"ascending original ordinal; no chunk reduction",
            "canonical_config":format!("{cfg:?}"),"noise":format!("{noise:?}"),"wb_coefficients":wb,
            "display_baseline":display,"candidate_plan":format!("{candidate_plan:?}"),"threads":threads,
            "environment":std::env::vars().filter(|(k,_)|k.starts_with("STREHL_")||k=="RAYON_NUM_THREADS").collect::<std::collections::BTreeMap<_,_>>(),
            "admission":false,"quality_claim":false
        }),
    )?;
    let mut first = Some(first);
    let mut canonical = BandWorker::new(PyramidDomain::cropped(full, crop)?, cfg);
    let mut baseline_total: Option<BandMerge> = None;
    let mut candidate = Accumulator::new(candidate_plan, cfg, wb)?;
    let indices = if full_run {
        (0..299).collect::<Vec<_>>()
    } else {
        vec![149]
    };
    let mut frame_receipts = Vec::new();
    let mut singleton_gather = None;
    let processing_start = Instant::now();
    pool.install(||->Result<()> {
        let mut chunks=indices.chunks(plan.per_chunk).peekable();
        while let Some(chunk)=chunks.next() {
            for &index in chunk {
                let start=Instant::now();
                let frame=match first.take() {Some(f)=>f,None=>strehl_raw::decode(&paths[index])?};
                validate_frame(&frame,full)?;
                let original_hash=rb_own_guide::active_hash(&frame);
                let source=OneSource{frame:&frame,index};
                let baseline_start=Instant::now();
                ensure!(canonical.fold(&source,index,levels,&noise,Some(&map),None)?,"canonical source refused");
                let canonical_seconds=baseline_start.elapsed().as_secs_f64();
                let known_hashes=canonical.planes.iter().map(|p|f32_hash(p)).collect::<Vec<_>>();
                // A cost-only equality check commissions this adapter's explicit
                // four-phase callback against the actual canonical gathered input.
                let callback_exact=if !full_run {
                    let check=full_gather(&frame,map.placement(index)?,crop)?;
                    ensure!(same_planes(&check,&canonical.planes),"candidate gather differs from canonical");
                    singleton_gather=Some(canonical.planes.clone()); true
                } else {false};
                let candidate_start=Instant::now();
                let draw_count=std::cell::Cell::new(0usize);
                let probe=candidate.add_source(&frame,index,&canonical.planes,&noise, |f| {
                    draw_count.set(draw_count.get()+1);
                    full_gather(f,map.placement(index)?,crop)
                })?;
                ensure!(draw_count.get()==16 && probe["probe_draws"]==16 && probe["probe_pairs"]==8
                    && probe["source_index"]==index, "actual sixteen-draw/ordinal contract");
                let candidate_seconds=candidate_start.elapsed().as_secs_f64();
                ensure!(rb_own_guide::active_hash(&frame)==original_hash,"original decoded CFA mutated");
                ensure!(known_hashes==canonical.planes.iter().map(|p|f32_hash(p)).collect::<Vec<_>>(), "canonical gathered input mutated");
                let row=json!({"index":index,"input":order[index],"active_sha256":original_hash,
                    "gathered_phase_sha256":known_hashes,"callback_matches_canonical":if full_run {Value::Null}else{json!(callback_exact)},
                    "canonical_seconds":canonical_seconds,"candidate_seconds":candidate_seconds,"probe":probe,
                    "total_source_seconds":start.elapsed().as_secs_f64()});
                write_json(&config.out_dir.join(format!("source-{index:03}.json")),&row)?;
                frame_receipts.push(row);
                eprintln!("DUAL_TREE {}/{} index={} source={:.3}s elapsed={:.3}s",frame_receipts.len(),indices.len(),index,start.elapsed().as_secs_f64(),total.elapsed().as_secs_f64());
            }
            phase_packed_rgb::full_stack::absorb_chunk(&mut baseline_total,&mut canonical.merge,crop.width,crop.height,4,cfg);
            if chunks.peek().is_some() {canonical.reset_chunk();}
        }
        Ok(())
    })?;
    let source_phase_seconds = processing_start.elapsed().as_secs_f64() + first_decode_seconds;
    drop(canonical);
    let finish_start = Instant::now();
    let finished = pool.install(|| candidate.finish())?;
    ensure!(
        finite_four(&finished.planes4)
            && finite_four(&finished.pre_hull_planes4)
            && finite_four(&finished.uniform_planes4)
            && finite_four(&finished.mean_planes4),
        "all complete finite candidate arms"
    );
    ensure!(
        finished.evidence["source_count"] == indices.len()
            && finished.evidence["source_ids"] == json!(indices),
        "complete candidate source-order census"
    );
    let uniform_null = errors(&finished.uniform_planes4, &finished.mean_planes4)?;
    write_json(
        &config.out_dir.join("uniform-transform-null.json"),
        &uniform_null,
    )?;
    ensure!(
        uniform_null["pass"] == true,
        "actual uniform transform/mean null failed"
    );
    let singleton_null = if let Some(known) = singleton_gather.as_ref() {
        ensure!(
            same_planes(&finished.planes4, known),
            "actual singleton hull differs from gather"
        );
        ensure!(
            same_planes(&finished.mean_planes4, known),
            "actual singleton mean differs from gather"
        );
        let pre = errors(&finished.pre_hull_planes4, known)?;
        write_json(
            &config.out_dir.join("single-source-transform-null.json"),
            &pre,
        )?;
        ensure!(
            pre["pass"] == true,
            "actual single-source pre-hull transform null failed"
        );
        pre
    } else {
        Value::Null
    };
    let baseline = pool.install(|| {
        baseline_total
            .take()
            .context("canonical total")
            .map(|m| m.finish(&mut Workspace::new(&sizes)))
    })?;
    ensure!(finite_four(&baseline), "complete finite canonical output");
    if let Some(known) = singleton_gather.as_ref() {
        ensure!(
            same_planes(&baseline, known),
            "canonical singleton hull differs from gather"
        );
    }
    drop(singleton_gather);
    let gains = [wb[0] / wb[1], 1.0, wb[2] / wb[1]];
    let matrix = color::camera_to_srgb(MATRIX)
        .context("matrix")?
        .with_saturation(levels, gains, 1.0);
    let mut dev = image_out::OutputSpace::Srgb.develop(Some(matrix));
    dev.tone = Some(image_out::Tone {
        black: display.black,
        white: display.white,
        contrast: display.contrast,
    });
    dev.exposure_gain = display.exposure_gain;
    let mut files = Vec::new();
    let mut pixel_hashes = Vec::new();
    let mut materials = Vec::new();
    for (name, planes) in [
        ("baseline", &baseline),
        ("candidate", &finished.planes4),
        ("uniform", &finished.uniform_planes4),
    ] {
        let mut row =
            pool.install(|| write_result(&config.out_dir, name, planes, levels, wb, &dev))?;
        row["name"] = json!(name);
        pixel_hashes.push(json!({"rgb16":rgb16_hash(&config.out_dir.join(format!("{name}-master.tiff")))?,
            "linear_rgb32":float_pixels_hash(&config.out_dir.join(format!("{name}-linear.tiff")),3)?}));
        materials.push(
            json!({"rgb16":material(&config.out_dir.join(format!("{name}-master.tiff")))?,
            "linear_rgb32":material(&config.out_dir.join(format!("{name}-linear.tiff")))?}),
        );
        files.push(row);
    }
    ensure!(
        materials[0] == materials[1] && materials[0] == materials[2],
        "paired color/tone/ICC metadata differs"
    );
    let identity = if full_run {
        let held = json!({"rgb16":BASE_RGB_PIXELS_SHA,"linear_rgb32":BASE_LINEAR_PIXELS_SHA});
        let held_material = json!({"rgb16":material(&base.join("stack-master.tiff"))?,"linear_rgb32":material(&linear_path)?});
        json!({"scope":"complete old CPU CA-off vs canonical held-source replay","exact":pixel_hashes[0]==held&&files[0]["cfa"]["sha256"]==BASE_SENSOR_PAYLOAD_SHA,
            "held":held,"canonical":pixel_hashes[0],"material_metadata_exact":materials[0]==held_material})
    } else {
        json!({"scope":"one-source actual gather/hull","exact":pixel_hashes[0]==pixel_hashes[1]&&files[0]["cfa"]["sha256"]==files[1]["cfa"]["sha256"],
            "material_metadata_exact":materials[0]==materials[1]})
    };
    write_json(&config.out_dir.join("baseline-identity.json"), &identity)?;
    ensure!(
        identity["exact"] == true && identity["material_metadata_exact"] == true,
        "baseline pixel/material identity failed; complete outputs retained"
    );
    for (i, path) in paths.iter().enumerate() {
        ensure!(
            stamp(path)? == before[i],
            "original source metadata changed"
        );
        if full_run || i == 149 {
            ensure!(
                Some(sha(path)?.as_str()) == order[i]["sha256"].as_str(),
                "original contents changed"
            );
        }
    }
    ensure!(
        sha(&map_path)? == MAP_SHA
            && sha(&order_path)? == ORDER_SHA
            && sha(&exe)? == config.expected_test_executable_sha256
            && sha(&linear_path)? == BASE_LINEAR_SHA
            && sha(&config_path)? == config_sha
            && sha(&base.join("stack-master.tiff"))? == BASE_MASTER_SHA
            && sha(&base.join("sensor-master.tiff"))?
                == "fa5825b834121b28547fc6e2154623740a24acc4e1616915c1c197bc90be2b02"
            && sha(&base.join("sensor-master.tiff.json"))?
                == "e22ad2fad5ac7307a4560ccee4b0ad232edf1dc9449fdce7057022bff9341f21"
            && sha(&campaign.join("baseline-strehl.exe"))? == BASE_EXE_SHA,
        "bound input changed"
    );
    let finish_seconds = finish_start.elapsed().as_secs_f64();
    let mut receipt = json!({"status":if full_run {"COMPLETE299_DUAL_TREE_DIAGNOSTIC"}else{"SOURCE149_DUAL_TREE_COST_COMPLETE"},
        "mechanical_pass":true,"admission":false,"quality_claim":false,"photographic_admission":false,
        "source_count":indices.len(),"source_index":if full_run {Value::Null}else{json!(149)},"noise_probe_draws":16,
        "source_phase_seconds":source_phase_seconds,"finish_seconds":finish_seconds,"first_decode_seconds":first_decode_seconds,
        "total_seconds":total.elapsed().as_secs_f64(),"input_preservation":true,
        "all299_metadata_unchanged":true,"processed_original_contents_unchanged":true,"all299_contents_reread":full_run,
        "baseline_pixel_golden_exact":if full_run {json!(true)}else{Value::Null},"baseline_identity":identity,
        "uniform_transform_null":uniform_null,"single_source_pre_hull_null":singleton_null,
        "singleton_hull_exact":if full_run {Value::Null}else{json!(true)},"noise_probe_scope":"original u16 noise; 8 independent pairs through actual all-four CPU gather"});
    let extra = json!({"arms":files,"pixel_hashes":pixel_hashes,"material_metadata":materials,"candidate_evidence":finished.evidence,
        "pre_hull_phase_sha256":finished.pre_hull_planes4.iter().map(|v|f32_hash(v)).collect::<Vec<_>>(),
        "source_mean_phase_sha256":finished.mean_planes4.iter().map(|v|f32_hash(v)).collect::<Vec<_>>(),
        "frame_receipts":frame_receipts,"canonical_plan":plan,"canonical_chunk_lengths":if full_run {vec![75,75,75,74]}else{vec![1]},
        "native_dimensions":[6896,4596],"crop_quad":CROP,"reference":149,"storage":"original u16 CFA; f32 arithmetic; no aligned-frame volume",
        "projected299_seconds_with_fixed_margin":if full_run {Value::Null}else{json!(299.0*source_phase_seconds+finish_seconds+120.0)},
        "peak_memory":"root bounded-job observation; CPU full gate 14 GiB","software_provenance":"TIFF Software may differ; pixels and material metadata are held"});
    receipt
        .as_object_mut()
        .context("receipt map")?
        .extend(extra.as_object().context("extra map")?.clone());
    write_json(&config.out_dir.join("receipt.json"), &receipt)?;
    Ok(())
}
#[test]
#[ignore = "root scheduled full-size source149 and sixteen actual probes"]
fn weevil_source149_cost() -> Result<()> {
    run(false)
}
#[test]
#[ignore = "root scheduled complete299 diagnostic after exact cost/mechanical guards"]
fn weevil299_complete() -> Result<()> {
    run(true)
}
