// Root-only one-source cost and complete299 observation. No default/product mutation.
// Root owns build, execution bounds and the decision whether to run this source.
use super::*;
use strehl_core::pyramid::{Fallback, Hull};
use serde::Deserialize;
use serde_json::{Value, json};
use sha2::{Digest, Sha256};
use std::{
    fs::{File, OpenOptions},
    io::{BufReader, BufWriter, Read, Write},
    time::SystemTime,
};
use strehl_core::align::Similarity;
use strehl_core::pyramid::rb_own_guide_diagnostic as consumer;

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

fn float_pixels_hash(path: &Path, channels: usize) -> Result<String> {
    let mut limits = tiff::decoder::Limits::default();
    // The pinned complete RGB32 image is 380,328,192 bytes. Admit that exact
    // geometry's buffer, without disabling TIFF resource limits generally.
    limits.decoding_buffer_size = 6896 * 4596 * channels * std::mem::size_of::<f32>();
    let mut d = tiff::decoder::Decoder::new(BufReader::new(File::open(path)?))?
        .with_limits(limits);
    ensure!(d.dimensions()? == (6896, 4596), "held float geometry");
    let p = match d.read_image()? {
        tiff::decoder::DecodingResult::F32(v) => v,
        _ => anyhow::bail!("float32 required"),
    };
    ensure!(
        !d.more_images() && p.len() == 6896 * 4596 * channels,
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
fn run(full_run: bool) -> Result<()> {
    let total = Instant::now();
    ensure!(
        std::env::var("STREHL_FIX_CA").as_deref() == Ok("off"),
        "explicit CA-off required"
    );
    ensure!(
        align_cmd::fullres_gather_enabled()
            && gatefloor::enabled()
            && align_cmd::direct_plane_mode()? == align_cmd::DirectPlaneMode::Rounded
            && align_cmd::native_gpu_integration::gpu_gather_enabled()?,
        "actual rounded GPU/probe route required"
    );
    ensure!(
        std::env::var_os("STREHL_LOCAL_PLACEMENT_FILE").is_none()
            && matches!(
                std::env::var("STREHL_DEMOSAIC").as_deref(),
                Err(std::env::VarError::NotPresent) | Ok("malvar")
            )
            && strehl_core::pyramid::fine_support_candidate::environment_mode()
                == strehl_core::pyramid::fine_support_candidate::Mode::Off,
        "fixed MHC/no competing treatment"
    );
    let config_path = PathBuf::from(
        std::env::var_os("STREHL_GREEN_PHASE_GUIDE_CONFIG").context("config required")?,
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
    let map_path = campaign.join("weevil-107-sensor-ca-off-alignment.txt");
    let order_path = campaign.join("weevil-107-baseline/input-order.json");
    let linear_path = base.join("linear-master.tiff");
    ensure!(
        sha(&map_path)? == MAP_SHA && sha(&order_path)? == ORDER_SHA,
        "held map/order changed"
    );
    ensure!(
        sha(&campaign.join("baseline-strehl.exe"))? == BASE_EXE_SHA
            && sha(&base.join("stack-master.tiff"))? == BASE_MASTER_SHA
            && sha(&linear_path)? == config.baseline_linear_sha256,
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
    write_json(
        &config.out_dir.join("started.json"),
        &json!({"phase":if full_run {"complete299"}else{"source149-cost"},
        "source_count":if full_run {299}else{1},"held_stack_count":299,"map_sha256":MAP_SHA,"order_sha256":ORDER_SHA,
        "baseline_exe_sha256":BASE_EXE_SHA,"baseline_master_sha256":BASE_MASTER_SHA,"baseline_linear_sha256":config.baseline_linear_sha256,
        "test_exe":file_record(&exe)?,"config":file_record(&config_path)?,"config_resolved":format!("{cfg:?}"),"noise":format!("{noise:?}"),
        "exact_baseline_display":display,"crop_quad":CROP,"native_dimensions":[6896,4596],"threads":threads,"operator_workers":1,
        "plan":plan,"exponents":(0..7).map(|k|cfg.exponent_at(k,7)).collect::<Vec<_>>(),"fine_changed":[0,1],
        "arms":["baseline","matched-mean","phase-energy"],"environment":std::env::vars().filter(|(k,_)|k.starts_with("STREHL_")||k=="RAYON_NUM_THREADS").collect::<std::collections::BTreeMap<_,_>>(),
        "quality_claim":false,"full299_authorization":"root selected this ignored test; no automatic promotion"}),
    )?;
    let original = if full_run {
        Value::Null
    } else {
        write_original(&first, &config.out_dir.join("original149-crop.u16le"))?
    };
    let mut first = Some(first);
    let mut baseline = BandWorker::new(PyramidDomain::cropped(full, crop)?, cfg);
    let mut changed: [BandMerge; 2] =
        std::array::from_fn(|_| BandMerge::new(crop.width, crop.height, 4, cfg));
    let mut work: [FrameWorkspace; 2] = std::array::from_fn(|_| FrameWorkspace::new(&sizes, 4));
    let mut totals: [Option<BandMerge>; 3] = std::array::from_fn(|_| None);
    let indices = if full_run {
        (0..299).collect::<Vec<_>>()
    } else {
        vec![149]
    };
    let mut receipts = Vec::new();
    let processing_start = Instant::now();
    pool.install(||->Result<()> {
        let mut chunks=indices.chunks(plan.per_chunk).peekable();
        while let Some(chunk)=chunks.next() {
            for &index in chunk {
                let start=Instant::now();
                let frame=match first.take(){Some(v)=>v,None=>strehl_raw::decode(&paths[index])?};
                validate_frame(&frame,full)?;
                let source_hash=rb_own_guide::active_hash(&frame);
                let source=OneSource{frame:&frame,index};
                let b=Instant::now();
                ensure!(baseline.fold(&source,index,levels,&noise,Some(&map),None)?,"canonical refused source");
                let baseline_seconds=b.elapsed().as_secs_f64();
                let canonical=consumer::canonical_fields(&baseline.merge,&baseline.fws,(!baseline.beta.is_empty()).then_some(baseline.beta.as_slice()));
                let g=Instant::now();
                let (fields,probe)=fields_with_gather(&frame,&noise,&sizes,cfg,&baseline.planes,&canonical,false,
                    |f|full_gather(f,map.placement(index)?,crop),true)?;
                let refs=baseline.planes.iter().map(Vec::as_slice).collect::<Vec<_>>();
                for arm in 0..2 {consumer::add_fields(&mut changed[arm],&refs,&fields[arm],&mut work[arm]);}
                let field_hashes=fields.iter().map(|f|json!({"energy":f.energy.iter().map(|v|f32_hash(v)).collect::<Vec<_>>(),
                    "floor":f.floor.iter().map(|v|f32_hash(v)).collect::<Vec<_>>(),"weights":f.weights.iter().map(|v|f32_hash(v)).collect::<Vec<_>>()})).collect::<Vec<_>>();
                ensure!(rb_own_guide::active_hash(&frame)==source_hash,"decoded source changed");
                if !full_run {for arm in 0..2 {
                    let collapsed=changed[arm].finish(&mut Workspace::new(&sizes));
                    ensure!(same_planes(&collapsed,&baseline.planes),"one-source hull identity failed");}}
                receipts.push(json!({"index":index,"active_sha256":source_hash,"probe":probe,"field_hashes":field_hashes,
                    "coarse_fields_exact":true,"reconstruction_planes_per_shared_field":4,"baseline_seconds":baseline_seconds,
                    "guide_and_fold_seconds":g.elapsed().as_secs_f64(),"total_source_seconds":start.elapsed().as_secs_f64()}));
                eprintln!("GREEN_PHASE {}/{} index {} {:.3}s elapsed {:.3}s",receipts.len(),indices.len(),index,start.elapsed().as_secs_f64(),total.elapsed().as_secs_f64());
            }
            phase_packed_rgb::full_stack::absorb_chunk(&mut totals[0],&mut baseline.merge,crop.width,crop.height,4,cfg);
            for arm in 0..2 {phase_packed_rgb::full_stack::absorb_chunk(&mut totals[arm+1],&mut changed[arm],crop.width,crop.height,4,cfg);}
            if chunks.peek().is_some() {baseline.reset_chunk();for m in &mut changed {m.reset_for_reuse();}}
        } Ok(())
    })?;
    let processing_seconds = processing_start.elapsed().as_secs_f64();
    drop(work);
    drop(changed);
    drop(baseline);
    let terminal = consumer::terminal_means(totals[0].as_ref().context("baseline total")?);
    for arm in 1..3 {
        ensure!(
            same_planes(
                &terminal,
                &consumer::terminal_means(totals[arm].as_ref().context("changed total")?)
            ),
            "terminal mean changed"
        );
    }
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
    let finish_start = Instant::now();
    for (arm, name) in ["baseline", "matched-mean", "phase-energy"]
        .into_iter()
        .enumerate()
    {
        let merge = totals[arm].take().context("arm absent")?;
        let averaged = merge.averaged_fraction();
        let output = pool.install(|| merge.finish(&mut Workspace::new(&sizes)));
        drop(merge);
        ensure!(
            output.iter().flatten().all(|v| v.is_finite()),
            "nonfinite full output"
        );
        let mut f =
            pool.install(|| write_result(&config.out_dir, name, &output, levels, wb, &dev))?;
        drop(output);
        f["averaged_fractions"] = json!(averaged);
        pixel_hashes.push(json!({"rgb16":rgb16_hash(&config.out_dir.join(format!("{name}-master.tiff")))?,
            "linear_rgb32":float_pixels_hash(&config.out_dir.join(format!("{name}-linear.tiff")),3)?}));
        files.push(f);
    }
    let identity = if full_run {
        let held = json!({"rgb16":rgb16_hash(&base.join("stack-master.tiff"))?,"linear_rgb32":float_pixels_hash(&linear_path,3)?,
            "cfa":"1a442c1638eb8f1b68d31dd502acc670eedf0f35463e864dd5f21ee26d4112b0"});
        let equal = pixel_hashes[0]["rgb16"] == held["rgb16"]
            && pixel_hashes[0]["linear_rgb32"] == held["linear_rgb32"]
            && files[0]["cfa"]["sha256"] == held["cfa"];
        json!({"scope":"complete old CPU CA-off vs new canonical route","held":held,"canonical":pixel_hashes[0],"exact":equal})
    } else {
        let equal = (1..3).all(|a| {
            pixel_hashes[a] == pixel_hashes[0]
                && files[a]["cfa"]["sha256"] == files[0]["cfa"]["sha256"]
        });
        json!({"scope":"one-source actual-gather hull","exact":equal})
    };
    write_json(&config.out_dir.join("baseline-identity.json"), &identity)?;
    ensure!(
        identity["exact"] == true,
        "baseline identity failed; complete files retained, no admission"
    );
    for (i, p) in paths.iter().enumerate() {
        ensure!(stamp(p)? == before[i], "source metadata changed");
        if full_run || i == 149 {
            ensure!(
                Some(sha(p)?.as_str()) == order[i]["sha256"].as_str(),
                "source contents changed"
            );
        }
    }
    ensure!(
        sha(&map_path)? == MAP_SHA
            && sha(&order_path)? == ORDER_SHA
            && sha(&exe)? == config.expected_test_executable_sha256
            && sha(&linear_path)? == config.baseline_linear_sha256,
        "bound input changed"
    );
    let finish_seconds = finish_start.elapsed().as_secs_f64();
    write_json(
        &config.out_dir.join(if full_run {
            "completion.json"
        } else {
            "cost.json"
        }),
        &json!({
        "status":if full_run {"COMPLETE299_OBSERVATION_READY"}else{"SOURCE149_COST_COMPLETE"},"quality_claim":false,
        "frames":indices.len(),"baseline_identity":identity,"terminal_mean_exact":true,"original_cfa":original,
        "arms":files,"pixel_hashes":pixel_hashes,"frame_receipts":receipts,"plan":plan,
        "first_decode_seconds":first_decode_seconds,"processing_seconds":processing_seconds,"finish_seconds":finish_seconds,
        "projected299_seconds_without_margin":if full_run {Value::Null}else{json!(299.0*(first_decode_seconds+processing_seconds)+finish_seconds)},
        "total_seconds":total.elapsed().as_secs_f64(),"all299_source_metadata_unchanged":true,"processed_source_contents_unchanged":true,
        "all299_contents_reread":full_run,"peak_memory":"root process measurement required","native_dimensions":[6896,4596]}),
    )?;
    Ok(())
}
#[test]
#[ignore = "root scheduled full-size one-source feasibility only"]
fn weevil_source149_full_cost() -> Result<()> {
    run(false)
}
#[test]
#[ignore = "root scheduled complete299 observational photograph only"]
fn weevil299_complete_observation() -> Result<()> {
    run(true)
}
