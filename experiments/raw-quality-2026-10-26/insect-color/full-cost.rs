// COST ONLY. Exactly one pinned original149; no full-stack entry or quality admission.
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
use strehl_core::pyramid::{
    LevelSize, correction_variance_diagnostic as kernels, rb_own_guide_diagnostic as consumer,
};

mod fixed_guide {
    include!(concat!(
        env!("CARGO_MANIFEST_DIR"),
        "/../../experiments/raw-quality-2026-10-26/insect-color/guide-fields.rs"
    ));
}
const SOURCE_SHA: &str = "e85572179c8a98f5a2de2be5c81cd0b1bdeae67999aa00e585c6dde35f531154";
const ORDER_SHA: &str = "0235564cf5131e7eb5e4ea251c16ea9272f6a55a9d8cc6efc717970615a30d6f";
const MAP_SHA: &str = "4a76cd0c56c3a525e70f5bf72b965adb706131618c5bf49d0ae853fbf341c225";
const BASE_EXE_SHA: &str = "89a0d92aad1628cfdfe75f39d2627ed3679990c5b3381d8839f6cce61b7f2388";
const BASE_MASTER_SHA: &str = "ecfae13e937f44445f3fe2a83a2e72861c4cd6cd9f56f02139f3f5e3dc0f9665";
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
    baseline_linear_sha256: String,
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
fn same(a: &[Vec<f32>], b: &[Vec<f32>]) -> bool {
    a.len() == b.len()
        && a.iter().zip(b).all(|(a, b)| {
            a.len() == b.len() && a.iter().zip(b).all(|(a, b)| a.to_bits() == b.to_bits())
        })
}

// This scoped adapter is deliberately separate from the generated-only probe.
// It retains original source-space variance, identical seed mapping, 8 independent
// pairs, round-to-u16 samples, actual MHC/CA/GPU pull, and existing NoiseEnergy.
fn full_gather(
    frame: &Frame,
    warp: Similarity,
    crop: align_cmd::CropRect,
) -> Result<Vec<Vec<f32>>> {
    ensure!(
        frame.path.file_name().and_then(|v| v.to_str()) == Some("DSC00150.ARW")
            && frame.geometry()
                == PlaneGeometry {
                    width: 3516,
                    height: 2344
                }
            && [crop.x, crop.y, crop.width, crop.height] == CROP,
        "fixed one-source gather scope"
    );
    let mut current = frame.clone();
    let mut planes = vec![vec![0.0; crop.width * crop.height]; 4];
    align_cmd::warp_frame_fullres_into_planes::<false>(
        &mut current,
        warp,
        frame.geometry(),
        Resampler::CatmullRom,
        &mut WarpScratch::new(frame.geometry()),
        crop,
        &[(0, 0), (1, 0), (0, 1), (1, 1)],
        &mut planes,
        align_cmd::DirectPlaneMode::Rounded,
    )?;
    ensure!(
        planes.iter().flatten().all(|v| v.is_finite()),
        "nonfinite full probe gather"
    );
    Ok(planes)
}
fn probe(
    frame: &Frame,
    warp: Similarity,
    crop: align_cmd::CropRect,
    noise: &NoiseModel,
    sizes: &[LevelSize],
) -> Result<(rb_own_guide::GuideBands, Value)> {
    let active_sha = rb_own_guide::active_hash(frame);
    let seeds = rb_own_guide::source_seeds(&active_sha)?;
    let variance = boundary_cfa_wavelet::original_variances(frame, noise)?;
    let variance_sha = f32_hash(&variance);
    let mut energy = rb_own_guide::NoiseEnergy::new(sizes);
    let started = Instant::now();
    let mut pairs = Vec::new();
    for pair in 0..8 {
        let pair_start = Instant::now();
        let member = |draw: usize| -> Result<rb_own_guide::GuideBands> {
            let noisy = boundary_cfa_wavelet::noisy_source(frame, &variance, seeds[draw])?;
            let known = full_gather(&noisy, warp, crop)?;
            rb_own_guide::guide_laplacians(&known, sizes)
        };
        let a = member(2 * pair)?;
        let b = member(2 * pair + 1)?;
        energy.add_pair(&a, &b)?;
        pairs.push(pair_start.elapsed().as_secs_f64());
        eprintln!(
            "INSECT_COLOR_COST probe pair {}/8 complete {:.3}s",
            pair + 1,
            started.elapsed().as_secs_f64()
        );
    }
    let energy = energy.finish()?;
    let hashes = energy
        .iter()
        .map(|bands| bands.iter().map(|v| f32_hash(v)).collect::<Vec<_>>())
        .collect::<Vec<_>>();
    Ok((
        energy,
        json!({"pairs":8,"draws":16,"seeds":seeds,"source_active_sha256":active_sha,
        "original_variance_sha256":variance_sha,"energy_variance_sha256":hashes,"pair_seconds":pairs,
        "probe_seconds":started.elapsed().as_secs_f64(),"same_estimator_as_generated_screen":true}),
    ))
}
struct OneSource<'a>(&'a Frame);
impl PyramidFrameSource for OneSource<'_> {
    fn len(&self) -> usize {
        299
    }
    fn decode(&self, index: usize) -> Result<Frame> {
        ensure!(index == 149, "cost only source149");
        Ok(self.0.clone())
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
fn write_original(frame: &Frame, path: &Path) -> Result<Value> {
    let mut out = BufWriter::new(OpenOptions::new().write(true).create_new(true).open(path)?);
    let mut row = vec![0u8; 4 * CROP[2]];
    for y in 2 * CROP[1]..2 * (CROP[1] + CROP[3]) {
        for x in 0..2 * CROP[2] {
            row[2 * x..2 * x + 2].copy_from_slice(&frame.sample(2 * CROP[0] + x, y).to_le_bytes());
        }
        out.write_all(&row)?;
    }
    out.flush()?;
    drop(out);
    file_record(path)
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

#[test]
#[ignore = "manual COST ONLY pinned source149; root bounds resources and approves execution"]
fn weevil_source149_full_cost() -> Result<()> {
    let total = Instant::now();
    ensure!(
        std::env::var("STREHL_INSECT_COLOR_PHASE").as_deref() == Ok("cost"),
        "only cost phase is implemented"
    );
    ensure!(
        std::env::var_os("STREHL_FIX_CA").is_none(),
        "held default capture CA required"
    );
    ensure!(
        align_cmd::fullres_gather_enabled()
            && gatefloor::enabled()
            && align_cmd::direct_plane_mode()? == align_cmd::DirectPlaneMode::Rounded
            && align_cmd::native_gpu_integration::gpu_gather_enabled()?,
        "actual rounded GPU/probe gather required"
    );
    ensure!(
        std::env::var_os("STREHL_LOCAL_PLACEMENT_FILE").is_none()
            && matches!(
                std::env::var("STREHL_DEMOSAIC").as_deref(),
                Err(std::env::VarError::NotPresent) | Ok("malvar")
            )
            && strehl_core::pyramid::fine_support_candidate::environment_mode()
                == strehl_core::pyramid::fine_support_candidate::Mode::Off,
        "fixed MHC/no placement/no fine-support route required"
    );
    let config_path = PathBuf::from(
        std::env::var_os("STREHL_INSECT_COLOR_COST_CONFIG").context("cost config required")?,
    );
    let config: Config = serde_json::from_slice(&std::fs::read(&config_path)?)?;
    ensure!(
        config.schema == 1
            && config.baseline_linear_sha256.len() == 64
            && config.expected_test_executable_sha256.len() == 64,
        "schema/hash contract"
    );
    let repo = Path::new(env!("CARGO_MANIFEST_DIR"))
        .join("../..")
        .canonicalize()?;
    let campaign = repo.join("outputs/raw-quality-2026-10-26");
    let base = campaign.join("weevil-107-baseline");
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
    let map_path = base.join("alignment.txt");
    let order_path = base.join("input-order.json");
    let linear_path = base.join("linear-master.tiff");
    ensure!(
        sha(&map_path)? == MAP_SHA && sha(&order_path)? == ORDER_SHA,
        "held map/order changed"
    );
    ensure!(
        sha(&campaign.join("baseline-strehl.exe"))? == BASE_EXE_SHA
            && sha(&base.join("stack-master.tiff"))? == BASE_MASTER_SHA,
        "held baseline executable/master changed"
    );
    ensure!(
        sha(&linear_path)? == config.baseline_linear_sha256,
        "held linear master changed"
    );
    let display = exact_baseline(&linear_path)?;
    let order: Vec<Value> = serde_json::from_slice(&std::fs::read(&order_path)?)?;
    ensure!(
        order.len() == 299
            && order[149]["index"] == 149
            && order[149]["sha256"].as_str() == Some(SOURCE_SHA),
        "held299 order/source149 identity"
    );
    let paths = order
        .iter()
        .map(|v| v["path"].as_str().map(PathBuf::from).context("source path"))
        .collect::<Result<Vec<_>>>()?;
    let before = paths.iter().map(|p| stamp(p)).collect::<Result<Vec<_>>>()?;
    for (index, item) in order.iter().enumerate() {
        ensure!(
            item["index"].as_u64() == Some(index as u64)
                && item["bytes"].as_u64() == Some(before[index].0)
                && item["mtime_ns"].as_u64()
                    == Some(
                        before[index]
                            .1
                            .duration_since(SystemTime::UNIX_EPOCH)?
                            .as_nanos() as u64
                    ),
            "held source metadata differs"
        );
    }
    ensure!(sha(&paths[149])? == SOURCE_SHA, "original149 bytes changed");
    let mut entries = Vec::new();
    for (index, p) in paths.iter().enumerate() {
        entries.push((
            p.file_name()
                .and_then(|v| v.to_str())
                .context("filename")?
                .to_owned(),
            before[index].0,
        ));
    }
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
        "held complete map contract"
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
    let warp = map.placement(149).context("source149 unplaced")?;
    ensure!(
        [
            warp.a.re.to_bits(),
            warp.a.im.to_bits(),
            warp.b.re.to_bits(),
            warp.b.im.to_bits()
        ] == [
            0x3ff0000000000000,
            0xbc00000000000000,
            0x3ca0000000000000,
            0
        ],
        "frozen actual transform bits changed"
    );
    let id = strehl_raw::identity(&paths[149]);
    let ca = strehl_core::optics::profile_for_capture_env(id.model.as_deref(), id.lens_type3)?;
    ensure!(
        ca.is_some_and(|p| p.key == "a7c2-fe100gm-2xtc-x4cpl")
            && phase_packed_rgb::full_stack::full_source_supported(warp, full, crop, ca),
        "held default CA/covered pull required"
    );
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
    ensure!((1..=8).contains(&threads), "bounded1..8 threads required");
    let pool = ThreadPoolBuilder::new().num_threads(threads).build()?;
    std::fs::create_dir(&config.out_dir)?;
    write_json(
        &config.out_dir.join("started.json"),
        &json!({"phase":"cost-only","source_index":149,"source_count":1,"held_stack_count":299,
        "source_sha256":SOURCE_SHA,"map_sha256":MAP_SHA,"order_sha256":ORDER_SHA,"baseline_exe_sha256":BASE_EXE_SHA,
        "baseline_master_sha256":BASE_MASTER_SHA,"baseline_linear_sha256":config.baseline_linear_sha256,
        "test_exe":file_record(&exe)?,"config":file_record(&config_path)?,"config_resolved":format!("{cfg:?}"),
        "exact_baseline_display":display,"crop_quad":CROP,"native_dimensions":[6896,4596],"threads":threads,"operator_workers":1,
        "environment":std::env::vars().filter(|(k,_)|k.starts_with("STREHL_") || k=="RAYON_NUM_THREADS").collect::<std::collections::BTreeMap<_,_>>(),
        "quality_admitted":false,"full299_execution_implemented":false}),
    )?;
    let decode_start = Instant::now();
    let frame = strehl_raw::decode(&paths[149])?;
    let decode_seconds = decode_start.elapsed().as_secs_f64();
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
        "source149 metadata changed"
    );
    let active_sha = rb_own_guide::active_hash(&frame);
    let original = write_original(&frame, &config.out_dir.join("original149-crop.u16le"))?;
    let levels = frame.levels;
    let wb = frame.wb_coeffs;
    let noise = profile::noise_model_for(&frame.camera, frame.iso, levels);
    ensure!(
        noise.is_trustworthy() && noise.prnu().is_none(),
        "one trusted injected temporal noise model required"
    );
    let sizes = level_sizes(crop.width, crop.height, cfg.bands);
    ensure!(sizes.len() == 8, "seven AC bands required");
    let processing_start = Instant::now();
    let mut baseline = BandWorker::new(PyramidDomain::cropped(full, crop)?, cfg);
    let mut joint = BandMerge::new(crop.width, crop.height, 4, cfg);
    let mut fws = FrameWorkspace::new(&sizes, 4);
    let (probe_receipt,fields_receipt,baseline_seconds,guide_seconds)=pool.install(||->Result<_>{
        let b=Instant::now();ensure!(baseline.fold(&OneSource(&frame),149,levels,&noise,Some(&map),None)?,"baseline refused149");let baseline_seconds=b.elapsed().as_secs_f64();
        let (variance,probe_receipt)=probe(&frame,warp,crop,&noise,&sizes)?;
        let g=Instant::now();let signal=rb_own_guide::guide_laplacians(&baseline.planes,&sizes)?;
        let fields:[consumer::Fields;3]=std::array::from_fn(|c|consumer::fields_from_energy(&sizes,cfg,
            signal[c].iter().enumerate().map(|(k,v)|kernels::energy(v,sizes[k])).collect(),
            variance[c].iter().map(|v|v.iter().map(|v|cfg.gate*v).collect()).collect()));
        let common=fixed_guide::shared_snr_fields(&sizes,cfg,[&fields[0],&fields[1],&fields[2]]).map_err(anyhow::Error::msg)?;
        consumer::add_fields(&mut joint,&baseline.planes.iter().map(Vec::as_slice).collect::<Vec<_>>(),&common,&mut fws);
        let receipt=json!({"energy_sha256":common.energy.iter().map(|v|f32_hash(v)).collect::<Vec<_>>(),
            "floor_sha256":common.floor.iter().map(|v|f32_hash(v)).collect::<Vec<_>>(),"weight_sha256":common.weights.iter().map(|v|f32_hash(v)).collect::<Vec<_>>(),
            "positive_weight_counts":common.weights.iter().map(|v|v.iter().filter(|&&v|v>0.0).count()).collect::<Vec<_>>(),"shared_planes":4});
        Ok((probe_receipt,receipt,baseline_seconds,g.elapsed().as_secs_f64()))
    })?;
    let processing_seconds = processing_start.elapsed().as_secs_f64();
    ensure!(
        rb_own_guide::active_hash(&frame) == active_sha,
        "original source buffer changed"
    );
    let base_terminal = consumer::terminal_means(&baseline.merge);
    let joint_terminal = consumer::terminal_means(&joint);
    ensure!(
        same(&base_terminal, &joint_terminal),
        "terminal plain mean changed"
    );
    let known_hashes = baseline
        .planes
        .iter()
        .map(|v| f32_hash(v))
        .collect::<Vec<_>>();
    let finish_start = Instant::now();
    drop(fws);
    let base_result = pool.install(|| baseline.merge.finish(&mut Workspace::new(&sizes)));
    let joint_result = pool.install(|| joint.finish(&mut Workspace::new(&sizes)));
    ensure!(
        same(&base_result, &baseline.planes) && same(&joint_result, &baseline.planes),
        "one-source hull failed exact actual gathered input identity"
    );
    let averaged = [
        baseline.merge.averaged_fraction(),
        joint.averaged_fraction(),
    ];
    drop(baseline);
    drop(joint);
    let reconstruction_seconds = finish_start.elapsed().as_secs_f64();
    let gains = [wb[0] / wb[1], 1.0, wb[2] / wb[1]];
    let matrix = color::camera_to_srgb(MATRIX)
        .context("matrix singular")?
        .with_saturation(levels, gains, 1.0);
    let mut dev = image_out::OutputSpace::Srgb.develop(Some(matrix));
    dev.tone = Some(image_out::Tone {
        black: display.black,
        white: display.white,
        contrast: display.contrast,
    });
    dev.exposure_gain = display.exposure_gain;
    let write_start = Instant::now();
    let base_files =
        pool.install(|| write_result(&config.out_dir, "baseline", &base_result, levels, wb, &dev))?;
    drop(base_result);
    let joint_files =
        pool.install(|| write_result(&config.out_dir, "joint", &joint_result, levels, wb, &dev))?;
    drop(joint_result);
    let write_seconds = write_start.elapsed().as_secs_f64();
    let base_pixels = rgb16_hash(&config.out_dir.join("baseline-master.tiff"))?;
    let joint_pixels = rgb16_hash(&config.out_dir.join("joint-master.tiff"))?;
    ensure!(
        base_pixels == joint_pixels
            && base_files["cfa"]["sha256"] == joint_files["cfa"]["sha256"]
            && base_files["linear_rgb32"]["sha256"] == joint_files["linear_rgb32"]["sha256"],
        "one-source delivered CFA/linear/RGB identity failed"
    );
    for (index, p) in paths.iter().enumerate() {
        ensure!(stamp(p)? == before[index], "source metadata changed");
    }
    ensure!(
        sha(&paths[149])? == SOURCE_SHA
            && sha(&map_path)? == MAP_SHA
            && sha(&order_path)? == ORDER_SHA
            && sha(&exe)? == config.expected_test_executable_sha256
            && sha(&linear_path)? == config.baseline_linear_sha256,
        "bound input changed during cost"
    );
    let finish_seconds = finish_start.elapsed().as_secs_f64();
    let source_phase_seconds = decode_seconds + processing_seconds;
    write_json(
        &config.out_dir.join("cost.json"),
        &json!({"status":"COST_ONLY_COMPLETE","quality_admitted":false,"full299_authorized":false,
        "source_index":149,"source_count":1,"held_stack_count":299,"source_active_sha256":active_sha,"actual_known4_sha256":known_hashes,
        "original_cfa":original,"baseline":base_files,"joint":joint_files,"rgb16_pixels_sha256":base_pixels,
        "single_source_hull_cfa_exact":true,"terminal_mean_exact":true,"single_source_linear_and_rgb16_exact":true,
        "probe":probe_receipt,"shared_guide":fields_receipt,"averaged_fractions":averaged,
        "levels":sizes.iter().map(|s|[s.width,s.height]).collect::<Vec<_>>(),"exponents":(0..7).map(|k|cfg.exponent_at(k,7)).collect::<Vec<_>>(),
        "decode_seconds":decode_seconds,"baseline_fold_seconds":baseline_seconds,"guide_and_fold_seconds":guide_seconds,
        "processing_seconds":processing_seconds,"source_phase_seconds":source_phase_seconds,"reconstruction_seconds":reconstruction_seconds,
        "write_seconds":write_seconds,"finish_seconds":finish_seconds,"projected299_seconds_without_margin":299.0*source_phase_seconds+finish_seconds,
        "total_seconds":total.elapsed().as_secs_f64(),"original_metadata_unchanged":true,"processed_original_content_unchanged":true,
        "unprocessed_original_contents_not_reread":true,"peak_memory":"root process measurement required",
        "scope":"one-source feasibility and identity only; no multi-source quality inference or full-stack admission"}),
    )?;
    Ok(())
}
