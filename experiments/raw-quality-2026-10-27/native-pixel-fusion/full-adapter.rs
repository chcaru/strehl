// Root-owned flat60 observation. No original/source directory writes.
use super::*;
use phase_packed_rgb::full_stack::{absorb_chunk, chunk_plan, full_source_supported};
use serde::Deserialize;
use sha2::{Digest, Sha256};
use std::{
    fs::{File, OpenOptions},
    io::{BufReader, BufWriter, Read, Write},
    time::SystemTime,
};
const ORDER_SHA: &str = "7a7f6474eca174c5dd9c9d4cabc6eb1ae15e8385c7395472a793175c59a107fe";
const MAP_SHA: &str = "658501d70e5623b168bdee327219382952ca0887f5eafec4d02650343f0dd36b";
const MASTER_SHA: &str = "01e576315fdf8242b9d008c06a0ad9b52f837f84d8d28e05d59d13b97379dbdc";
const LINEAR_SHA: &str = "51fd1f3e281c10def359af38a2064055de11b8788ff5ce7c0428d9e5a9e417ab";
const EXPORT_SHA: &str = "c18a216ebebfb37a09a6d4b6e252b2abfe73a2a9d20d9e28480607b8212bc759";
const CROP: [usize; 4] = [25, 17, 3466, 2310];
const WB_BITS: [u32; 3] = [1076994048, 1065353216, 1069719552];
const TONE_BITS: [u32; 3] = [1007739294, 1052551964, 1057803469];
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
    expected_test_executable_sha256: String,
}
fn digest(h: Sha256) -> String {
    h.finalize().iter().map(|v| format!("{v:02x}")).collect()
}
fn sha(path: &Path) -> Result<String> {
    let mut f = File::open(path)?;
    let mut h = Sha256::new();
    let mut b = vec![0u8; 1 << 20];
    loop {
        let n = f.read(&mut b)?;
        if n == 0 {
            break;
        }
        h.update(&b[..n]);
    }
    Ok(digest(h))
}
fn save(path: &Path, v: &Value) -> Result<()> {
    let mut f = OpenOptions::new().write(true).create_new(true).open(path)?;
    serde_json::to_writer_pretty(&mut f, v)?;
    writeln!(f)?;
    Ok(())
}
fn stamp(path: &Path) -> Result<(u64, SystemTime)> {
    let m = std::fs::metadata(path)?;
    Ok((m.len(), m.modified()?))
}
fn record(path: &Path) -> Result<Value> {
    Ok(json!({"path":path,"bytes":std::fs::metadata(path)?.len(),"sha256":sha(path)?}))
}
fn same(a: &[Vec<f32>], b: &[Vec<f32>]) -> bool {
    a.len() == b.len()
        && a.iter().zip(b).all(|(a, b)| {
            a.len() == b.len() && a.iter().zip(b).all(|(a, b)| a.to_bits() == b.to_bits())
        })
}
fn pixel_hash(path: &Path, float: bool) -> Result<String> {
    let mut limits = tiff::decoder::Limits::default();
    limits.decoding_buffer_size = 6932 * 4620 * 3 * 4;
    let mut d = tiff::decoder::Decoder::new(BufReader::new(File::open(path)?))?.with_limits(limits);
    ensure!(
        d.dimensions()? == (6932, 4620)
            && d.colortype()? == tiff::ColorType::RGB(if float { 32 } else { 16 }),
        "full output geometry/type"
    );
    let mut h = Sha256::new();
    let mut bytes = vec![0u8; 65536];
    match d.read_image()? {
        tiff::decoder::DecodingResult::F32(v) if float => {
            ensure!(v.len() == 6932 * 4620 * 3, "complete float payload");
            for chunk in v.chunks(bytes.len() / 4) {
                for (dst, x) in bytes.chunks_exact_mut(4).zip(chunk) {
                    dst.copy_from_slice(&x.to_bits().to_le_bytes());
                }
                h.update(&bytes[..chunk.len() * 4]);
            }
        }
        tiff::decoder::DecodingResult::U16(v) if !float => {
            ensure!(v.len() == 6932 * 4620 * 3, "complete u16 payload");
            for chunk in v.chunks(bytes.len() / 2) {
                for (dst, x) in bytes.chunks_exact_mut(2).zip(chunk) {
                    dst.copy_from_slice(&x.to_le_bytes());
                }
                h.update(&bytes[..chunk.len() * 2]);
            }
        }
        _ => bail!("wrong TIFF sample storage"),
    }
    ensure!(!d.more_images(), "one image required");
    Ok(digest(h))
}
fn display(path: &Path) -> Result<strehl_edit::DisplayBaseline> {
    let mut d = tiff::decoder::Decoder::new(BufReader::new(File::open(path)?))?;
    let description = d.get_tag_ascii_string(tiff::tags::Tag::ImageDescription)?;
    let line = description
        .lines()
        .find_map(|l| l.strip_prefix("DisplayBaseline: "))
        .context("display baseline absent")?;
    let v: strehl_edit::DisplayBaseline = serde_json::from_str(line)?;
    ensure!(
        [v.black, v.white, v.contrast].map(f32::to_bits) == TONE_BITS
            && v.exposure_gain.to_bits() == 1f32.to_bits(),
        "held exact tone changed"
    );
    Ok(v)
}
fn write_result(
    out: &Path,
    name: &str,
    planes: &[Vec<f32>],
    levels: Levels,
    gain: [f32; 3],
    dev: &image_out::Develop,
) -> Result<Value> {
    let (w, h) = (2 * CROP[2], 2 * CROP[3]);
    let sensor = out.join(format!("{name}-sensor.f32le"));
    let mut f = BufWriter::new(
        OpenOptions::new()
            .write(true)
            .create_new(true)
            .open(&sensor)?,
    );
    let mut row = vec![0u8; w * 4];
    let mut mosaic = vec![0.; w * h];
    let gains = [gain[0], gain[1], gain[1], gain[2]];
    for y in 0..h {
        for x in 0..w {
            let p = 2 * (y % 2) + x % 2;
            let v = planes[p][(y / 2) * CROP[2] + x / 2];
            row[4 * x..4 * x + 4].copy_from_slice(&v.to_bits().to_le_bytes());
            mosaic[y * w + x] = v.max(0.) * gains[p] * 1.0 / levels.range();
        }
        f.write_all(&row)?;
    }
    f.flush()?;
    drop(f);
    save(
        &out.join(format!("{name}-sensor.json")),
        &json!({"format":"row-major RGGB signed f32 little-endian black-subtracted DN",
        "width":w,"height":h,"active_native_origin":[2*CROP[0],2*CROP[1]],"before":["WB","MHC","development"],"payload":record(&sensor)?}),
    )?;
    let master = out.join(format!("{name}-master.tiff"));
    let linear = out.join(format!("{name}-linear.tiff"));
    image_out::write_demosaiced_with_master(&master, w, h, &mosaic, dev, Some(&linear), None)?;
    drop(mosaic);
    Ok(
        json!({"sensor":record(&sensor)?,"rgb16":record(&master)?,"linear":record(&linear)?,
        "rgb16_pixels_sha256":pixel_hash(&master,false)?,"linear_pixels_sha256":pixel_hash(&linear,true)?,"entire_output":true}),
    )
}
struct Source<'a> {
    frame: &'a Frame,
    index: usize,
}
impl PyramidFrameSource for Source<'_> {
    fn len(&self) -> usize {
        60
    }
    fn decode(&self, index: usize) -> Result<Frame> {
        ensure!(index == self.index, "one original decode");
        Ok(self.frame.clone())
    }
}

fn run(complete: bool) -> Result<()> {
    let start = Instant::now();
    route()?;
    let config_path =
        PathBuf::from(std::env::var_os("STREHL_NATIVE_PIXEL_CONFIG").context("config required")?);
    let config: Config = serde_json::from_slice(&std::fs::read(&config_path)?)?;
    ensure!(
        config.schema == 1
            && sha(&std::env::current_exe()?)? == config.expected_test_executable_sha256,
        "schema/test executable binding"
    );
    let repo = Path::new(env!("CARGO_MANIFEST_DIR"))
        .join("../..")
        .canonicalize()?;
    let campaign = repo.join("outputs/raw-quality-2026-10-26");
    let base = campaign.join("flat-1s-baseline");
    let order_path = base.join("input-order.json");
    let map_path = base.join("alignment.txt");
    let held_master = base.join("stack-master.tiff");
    let held_linear = base.join("linear-master.tiff");
    let export_receipt = campaign.join("flat-1s-tiff-export/receipt.json");
    ensure!(
        sha(&order_path)? == ORDER_SHA
            && sha(&map_path)? == MAP_SHA
            && sha(&held_master)? == MASTER_SHA
            && sha(&held_linear)? == LINEAR_SHA
            && sha(&export_receipt)? == EXPORT_SHA,
        "held file binding changed"
    );
    let view = display(&held_linear)?;
    let exported: Value = serde_json::from_slice(&std::fs::read(&export_receipt)?)?;
    ensure!(
        exported["wb_bits"] == json!(WB_BITS) && exported["input_order_sha256"] == ORDER_SHA,
        "held first-source WB binding"
    );
    let order: Vec<Value> = serde_json::from_slice(&std::fs::read(&order_path)?)?;
    ensure!(order.len() == 60, "complete60 order");
    let paths = order
        .iter()
        .map(|v| v["path"].as_str().map(PathBuf::from).context("source path"))
        .collect::<Result<Vec<_>>>()?;
    let before = paths.iter().map(|p| stamp(p)).collect::<Result<Vec<_>>>()?;
    for (i, p) in paths.iter().enumerate() {
        ensure!(
            order[i]["index"].as_u64() == Some(i as u64)
                && p.file_name().and_then(|v| v.to_str())
                    == Some(format!("DSC{:05}.ARW", i + 16).as_str())
                && order[i]["bytes"].as_u64() == Some(before[i].0)
                && order[i]["mtime_ns"].as_u64()
                    == Some(
                        before[i]
                            .1
                            .duration_since(SystemTime::UNIX_EPOCH)?
                            .as_nanos() as u64
                    )
                && order[i]["sha256"].as_str() == Some(sha(p)?.as_str()),
            "source manifest differs at {i}"
        );
    }
    let original = WarpMap::load(&map_path)?;
    original.check_stack(&StackIdentity::from_paths("flat-et1s-sw4-cpl", &paths)?)?;
    ensure!(
        original.len() == 60
            && original.placed_count() == 60
            && original.provenance().reference == 30
            && original.resampler() == Resampler::CatmullRom,
        "held map gauge"
    );
    let (map, fit) = align_cmd::cover_or_explain(original, align_cmd::CoverMode::Crop);
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
        "held full extent"
    );
    for (i, p) in paths.iter().enumerate() {
        let id = strehl_raw::identity(p);
        let ca = strehl_core::optics::profile_for_capture_env(id.model.as_deref(), id.lens_type3)?;
        ensure!(
            ca.is_some_and(|p| p.key == "a7c2-fe100gm-2xtc-x4cpl")
                && full_source_supported(map.placement(i)?, full, crop, ca),
            "held CA-on/support differs at {i}"
        );
    }
    let cfg = MergeConfig::default();
    config_guard(cfg)?;
    ensure!(
        cfg.bands == 7 && cfg.gate == 2. && cfg.exponent == 2. && cfg.sharpen_per_octave == 1.4,
        "held7-band defaults"
    );
    ensure!(
        std::env::var("RAYON_NUM_THREADS").as_deref() == Ok("4")
            && std::env::var("STREHL_PYRAMID_WORKERS").as_deref() == Ok("4"),
        "four workers required"
    );
    let pool = ThreadPoolBuilder::new().num_threads(4).build()?;
    let indices = if complete {
        (0..60).collect::<Vec<_>>()
    } else {
        vec![30]
    };
    let first = strehl_raw::decode(&paths[indices[0]])?;
    let levels = first.levels;
    ensure!(
        first.camera == "ILCE-7CM2"
            && first.iso == Some(100.)
            && levels
                == Levels {
                    black: 512.,
                    white: 15360.
                }
            && first.geometry() == full
            && first.active.width == 7032
            && first.active.height == 4688
            && first.xyz_to_cam_rgb() == Some(MATRIX),
        "fixed camera metadata"
    );
    if complete {
        ensure!(
            first.wb_gains().context("first WB")?.map(f32::to_bits) == WB_BITS,
            "first-source WB differs"
        );
    }
    let gain = WB_BITS.map(f32::from_bits);
    let active = first.active;
    let stride = first.stride;
    let buffer_height = first.buffer_height;
    let noise = profile::noise_model_for(&first.camera, first.iso, levels);
    ensure!(
        noise.is_trustworthy() && noise.prnu().is_none(),
        "one injected temporal profile"
    );
    let plan = chunk_plan(full, first.allocated_bytes(), 60, cfg);
    ensure!(
        plan.canonical_chunks == 4 && plan.per_chunk == 15,
        "held canonical4 chunks"
    );
    let domain = PyramidDomain::cropped(full, crop)?;
    let sizes = level_sizes(crop.width, crop.height, cfg.bands);
    let mut dev = image_out::OutputSpace::Srgb.develop(Some(
        color::camera_to_srgb(MATRIX)
            .context("matrix")?
            .with_saturation(levels, gain, 1.),
    ));
    dev.tone = Some(image_out::Tone {
        black: view.black,
        white: view.white,
        contrast: view.contrast,
    });
    dev.exposure_gain = view.exposure_gain;
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
    std::fs::create_dir(&config.out_dir)?;
    save(
        &config.out_dir.join("started.json"),
        &json!({"schema":1,"phase":if complete{"complete60"}else{"source30-checkpoint"},
        "expected_sources":indices.len(),"probe_source_count":60,"probe_source_index":"original stack index",
        "map_sha256":MAP_SHA,"order_sha256":ORDER_SHA,"baseline_master_sha256":MASTER_SHA,"baseline_linear_sha256":LINEAR_SHA,
        "test_executable_sha256":config.expected_test_executable_sha256,"config":record(&config_path)?,
        "crop_quad_xywh":CROP,"native_dimensions":[6932,4620],"reference":30,"plan":plan,"threads":4,"operator_workers":1,
        "noise_model":format!("{noise:?}"),"resolved_config":format!("{cfg:?}"),
        "level_sizes":sizes.iter().map(|s|[s.width,s.height]).collect::<Vec<_>>(),
        "exponents":(0..sizes.len()-1).map(|k|cfg.exponent_at(k,sizes.len()-1)).collect::<Vec<_>>(),
        "fixed_first_source_wb_bits":WB_BITS,"display_baseline":view,"tone_bits":TONE_BITS,"optical_ca":"a7c2-fe100gm-2xtc-x4cpl",
        "environment":std::env::vars().filter(|(k,_)|k.starts_with("STREHL_")||k=="RAYON_NUM_THREADS").collect::<std::collections::BTreeMap<_,_>>(),
        "quality_claim":false}),
    )?;
    let mut baseline = BandWorker::new(domain, cfg);
    let mut total = None;
    let mut candidate = Accumulator::new(crop.width * crop.height);
    let mut first = Some(first);
    let mut receipts = Vec::new();
    let mut witness = None;
    let processing = Instant::now();
    pool.install(||->Result<()>{for(position,&index)in indices.iter().enumerate(){let tick=Instant::now();
        let frame=match first.take(){Some(f)=>f,None=>strehl_raw::decode(&paths[index])?};
        ensure!(frame.camera=="ILCE-7CM2" && frame.iso==Some(100.) && frame.levels==levels && frame.active==active
            && frame.stride==stride && frame.buffer_height==buffer_height && frame.xyz_to_cam_rgb()==Some(MATRIX),"source metadata drift");
        let source_hash=rb_own_guide::active_hash(&frame);let source=Source{frame:&frame,index};
        ensure!(baseline.fold(&source,index,levels,&noise,Some(&map),None)?,"canonical source refused");
        let fields=core::canonical_fields(&baseline.merge,&baseline.fws,(!baseline.beta.is_empty()).then_some(baseline.beta.as_slice()));
        candidate.add(&baseline.planes,&fields.weights[0])?;
        if !complete{witness=Some(baseline.planes.clone());}
        ensure!(rb_own_guide::active_hash(&frame)==source_hash,"decoded source changed");
        receipts.push(json!({"index":index,"source_sha256":source_hash,"known4_sha256":baseline.planes.iter().map(|v|hash32(v)).collect::<Vec<_>>(),
            "canonical_weight_sha256":fields.weights.iter().map(|v|hash32(v)).collect::<Vec<_>>(),"guide_sha256":hash32(&baseline.luma),
            "variance_sha256":hash32(&baseline.var),"beta":baseline.beta,"reported_wb_bits":frame.wb_gains().context("reported WB")?.map(f32::to_bits),
            "source_unchanged":true,"seconds":tick.elapsed().as_secs_f64()}));
        let last=position+1==indices.len();if last || (index+1)%plan.per_chunk==0{absorb_chunk(&mut total,&mut baseline.merge,crop.width,crop.height,4,cfg);if !last{baseline.reset_chunk();}}
        eprintln!("NATIVE_PIXEL {}/{} index{} {:.3}s",position+1,indices.len(),index,tick.elapsed().as_secs_f64());
    }Ok(())})?;
    let processing_seconds = processing.elapsed().as_secs_f64();
    drop(baseline);
    let accumulator = candidate.evidence();
    let candidate = candidate.finish()?;
    let baseline = pool.install(|| {
        total
            .context("baseline absent")
            .map(|m| m.finish(&mut Workspace::new(&sizes)))
    })?;
    let checkpoint = if let Some(w) = witness.as_ref() {
        ensure!(
            same(&candidate, w),
            "single-source candidate not exact gathered tuple"
        );
        ensure!(
            same(&baseline, w),
            "single-source canonical hull not exact gathered tuple"
        );
        let matrix = (MATRIX, "D65".to_owned());
        for (name, planes) in [("source30-writer", w), ("candidate-writer", &candidate)] {
            pool.install(|| {
                write_merged_observed(
                    Merged::Bands { domain, planes },
                    levels,
                    Some(gain),
                    Some(&matrix),
                    image_out::OutputSpace::Srgb,
                    true,
                    Exposure::None,
                    None,
                    &config.out_dir.join(format!("{name}.tiff")),
                    None,
                    Some(&config.out_dir.join(format!("{name}-linear.tiff"))),
                    None,
                )
            })?;
        }
        ensure!(
            pixel_hash(&config.out_dir.join("source30-writer.tiff"), false)?
                == pixel_hash(&config.out_dir.join("candidate-writer.tiff"), false)?,
            "ordinary writer parity failed"
        );
        true
    } else {
        false
    };
    let baseline_files =
        pool.install(|| write_result(&config.out_dir, "baseline", &baseline, levels, gain, &dev))?;
    drop(baseline);
    if complete {
        ensure!(
            baseline_files["rgb16_pixels_sha256"].as_str()
                == Some(pixel_hash(&held_master, false)?.as_str())
                && baseline_files["linear_pixels_sha256"].as_str()
                    == Some(pixel_hash(&held_linear, true)?.as_str()),
            "complete canonical baseline pixel golden failed"
        );
    }
    let candidate_files = pool
        .install(|| write_result(&config.out_dir, "candidate", &candidate, levels, gain, &dev))?;
    if !complete {
        ensure!(
            baseline_files["rgb16_pixels_sha256"] == candidate_files["rgb16_pixels_sha256"]
                && baseline_files["linear_pixels_sha256"]
                    == candidate_files["linear_pixels_sha256"]
                && baseline_files["sensor"]["sha256"] == candidate_files["sensor"]["sha256"],
            "single-source fixed-tone/sensor parity failed"
        );
        ensure!(
            candidate_files["linear_pixels_sha256"].as_str()
                == Some(
                    pixel_hash(&config.out_dir.join("source30-writer-linear.tiff"), true)?.as_str()
                ),
            "fixed-tone normalization differs from ordinary writer pre-tone payload"
        );
    }
    for (i, p) in paths.iter().enumerate() {
        ensure!(
            stamp(p)? == before[i] && order[i]["sha256"].as_str() == Some(sha(p)?.as_str()),
            "original changed after run"
        );
    }
    ensure!(
        sha(&order_path)? == ORDER_SHA
            && sha(&map_path)? == MAP_SHA
            && sha(&held_master)? == MASTER_SHA
            && sha(&held_linear)? == LINEAR_SHA
            && sha(&export_receipt)? == EXPORT_SHA
            && sha(&std::env::current_exe()?)? == config.expected_test_executable_sha256,
        "held inputs changed"
    );
    save(
        &config.out_dir.join("receipt.json"),
        &json!({"schema":1,"status":if complete{"COMPLETE60_OBSERVATION_READY"}else{"SOURCE30_CHECKPOINT_EXACT"},
        "source_count":indices.len(),"frames":receipts,"one_actual_gather_per_source":true,"canonical_and_candidate_share_known4":true,
        "accumulator":accumulator,"candidate_association":"sequential original source order, canonical baseline retains4 chunks",
        "baseline_pixel_golden_required":complete,"baseline_pixel_golden_exact":complete,
        "single_source_gathered_cfa_exact":checkpoint,"single_source_canonical_hull_exact":checkpoint,
        "single_source_fixed_tone_rgb_linear_sensor_exact":checkpoint,"single_source_ordinary_writer_parity":checkpoint,
        "single_source_ordinary_vs_fixed_writer_linear_exact":checkpoint,
        "ordinary_writer_parity_display":"ordinary automatic tone on identical input; delivered pair independently uses fixed held tone",
        "baseline":baseline_files,"candidate":candidate_files,"original_bytes_and_metadata_unchanged":true,
        "held_map_order_baseline_unchanged":true,"processing_seconds":processing_seconds,"seconds":start.elapsed().as_secs_f64(),
        "input_count":60,"native_dimensions":[6932,4620],"crop_quad_xywh":CROP,"fixed_first_source_wb_bits":WB_BITS,
        "reported_per_source_wb_does_not_change_development":true,"quality_claim":false}),
    )?;
    Ok(())
}
#[test]
#[ignore = "root-owned source30 checkpoint, strict config"]
fn flat_source30_checkpoint() -> Result<()> {
    run(false)
}
#[test]
#[ignore = "root-owned complete flat60 observation, strict config"]
fn flat60_complete_observation() -> Result<()> {
    run(true)
}
