// One complete, held vitamin-C pair. Test-only, explicitly invoked by the
// resource-bounded parent runner. Originals are opened only for reading.
use super::*;
use phase_packed_rgb::full_stack::{absorb_chunk, chunk_plan, full_source_supported,
    gather_full_source, write_planes};
use serde::Deserialize;
use serde_json::json;
use std::{fs::File, io::{Read, Write}, time::SystemTime};
use strehl_core::pyramid::{AdmissionMode, BaseBand, Fallback, Hull, SelectMode};

const EXPECTED_BASELINE: &str = "c0d8faca8a23f31a73b843fbc9aa9f55fda96b5fcce9d3540ebf6a2b4319bb21";
const EXPECTED_MAP: &str = "84275850a032dc8beb88945b00514a58ebca433e267c8e10342ac55986cf830f";
const EXPECTED_WB_BITS: [u32; 3] = [1070374912, 1065353216, 1076715520];
const EXPECTED_MATRIX: [[f32; 3]; 3] = [
    [0.746, -0.2365, -0.0588], [-0.5687, 1.3442, 0.2474], [-0.0624, 0.1156, 0.6584],
];

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct Config {
    schema: u32,
    source_dir: PathBuf,
    warp_map: PathBuf,
    warp_map_sha256: String,
    out_dir: PathBuf,
    expected_crop: [usize; 4],
    expected_xyz_to_cam: [[f32; 3]; 3],
    tone: [f32; 3],
    max_extra_inset_quads: usize,
}

fn wb_gains(wb: [f32; 4]) -> Result<[f32; 3]> {
    ensure!(wb[..3].iter().all(|v| v.is_finite() && *v > 0.0), "invalid full-pair WB");
    Ok([wb[0] / wb[1], 1.0, wb[2] / wb[1]])
}
fn file_hash(path: &Path) -> Result<String> {
    let mut f = File::open(path)?;
    let mut h = Sha256::new();
    let mut buf = vec![0u8; 1 << 20];
    loop { let n = f.read(&mut buf)?; if n == 0 { break; } h.update(&buf[..n]); }
    Ok(digest(h))
}
fn write_json(path: &Path, value: &serde_json::Value) -> Result<()> {
    let mut f = std::fs::OpenOptions::new().write(true).create_new(true).open(path)?;
    serde_json::to_writer_pretty(&mut f, value)?;
    writeln!(f)?;
    Ok(())
}
// Chunked byte packing avoids millions of tiny digest updates. Byte order is
// identical to the generated hash helpers; no floating-point math is involved.
fn field_hash(values: &[f32]) -> String {
    let mut h = Sha256::new();
    let mut buf = vec![0u8; 65536];
    for chunk in values.chunks(buf.len() / 4) {
        for (dst, v) in buf.chunks_exact_mut(4).zip(chunk) {
            dst.copy_from_slice(&v.to_bits().to_le_bytes());
        }
        h.update(&buf[..4 * chunk.len()]);
    }
    digest(h)
}
fn source_hash(frame: &Frame) -> String {
    let mut h = Sha256::new();
    let mut row = vec![0u8; frame.active.width * 2];
    for y in 0..frame.active.height {
        for (dst, v) in row.chunks_exact_mut(2).zip(frame.active_row(y)) {
            dst.copy_from_slice(&v.to_le_bytes());
        }
        h.update(&row);
    }
    digest(h)
}
fn stamp(path: &Path) -> Result<(u64, SystemTime)> {
    let m = std::fs::metadata(path)?;
    Ok((m.len(), m.modified()?))
}
struct OneFrame<'a> { frame: &'a Frame, index: usize }
impl PyramidFrameSource for OneFrame<'_> {
    fn len(&self) -> usize { 70 }
    fn decode(&self, index: usize) -> Result<Frame> {
        ensure!(index == self.index, "full-pair one-frame source index");
        Ok(self.frame.clone())
    }
}

#[test]
#[ignore = "explicit complete photo pair; parent bounds resources and freezes configuration"]
fn vitamin_c_complete_pair() -> Result<()> {
    let started = Instant::now();
    let config_path = PathBuf::from(std::env::var_os("STREHL_GREEN_MATCH_FULL_CONFIG")
        .context("STREHL_GREEN_MATCH_FULL_CONFIG required")?);
    let config: Config = serde_json::from_slice(&std::fs::read(&config_path)?)?;
    ensure!(config.schema == 1 && config.expected_crop == [28, 19, 3460, 2306]
        && config.warp_map_sha256 == EXPECTED_MAP
        && config.max_extra_inset_quads == 0,
        "full-pair held binding differs");
    ensure!(config.expected_xyz_to_cam == EXPECTED_MATRIX
        && config.tone.map(f32::to_bits) == [0.090420f32, 0.914606, 0.55].map(f32::to_bits),
        "full-pair held matrix/tone differs");
    ensure!(config.source_dir.is_absolute() && config.source_dir.file_name().and_then(|v| v.to_str())
        == Some("crystalized-vitamin-c-cpl"), "full-pair source scope differs");
    ensure!(align_cmd::fullres_gather_enabled() && gatefloor::enabled()
        && align_cmd::direct_plane_mode()? == align_cmd::DirectPlaneMode::Rounded,
        "actual rounded fullres/probe route required");
    ensure!(std::env::var_os("STREHL_LOCAL_PLACEMENT_FILE").is_none(), "local placement excluded");
    ensure!(!std::env::var(strehl_core::demosaic::DEMOSAIC_ENV)
        .is_ok_and(|v| v.eq_ignore_ascii_case("directional")), "Malvar required");
    #[cfg(feature = "native-correction-variance")]
    ensure!(strehl_core::pyramid::fine_support_candidate::environment_mode()
        == strehl_core::pyramid::fine_support_candidate::Mode::Off, "fine support must be off");
    ensure!(file_hash(&config.warp_map)? == EXPECTED_MAP, "held warp map changed");
    let paths = crate::raw_paths(&config.source_dir, None)?;
    ensure!(paths.len() == 70 && paths.iter().enumerate().all(|(i, p)|
        p.file_name().and_then(|s| s.to_str()) == Some(format!("DSC{:05}.ARW", i + 94).as_str())),
        "complete held seventy-frame sequence required");
    let before = paths.iter().map(|p| stamp(p)).collect::<Result<Vec<_>>>()?;
    let original_map = WarpMap::load(&config.warp_map)?;
    original_map.check_stack(&StackIdentity::from_paths("crystalized-vitamin-c-cpl", &paths)?)?;
    ensure!(original_map.resampler() == Resampler::CatmullRom && original_map.len() == 70
        && original_map.placed_count() == 70, "held map does not place all sources");
    let (map, fit) = align_cmd::cover_or_explain(original_map, align_cmd::CoverMode::Crop);
    let crop = fit.rect().context("held map has no crop")?;
    ensure!([crop.x, crop.y, crop.width, crop.height] == config.expected_crop,
        "held crop changed; this experiment does not inset");
    let full = map.geometry();
    ensure!(full == PlaneGeometry { width: 3516, height: 2344 }, "held source geometry differs");
    let identities = paths.iter().map(|p| strehl_raw::identity(p)).collect::<Vec<_>>();
    let profiles = identities.iter().map(|i|
        strehl_core::optics::profile_for_capture_env(i.model.as_deref(), i.lens_type3))
        .collect::<std::result::Result<Vec<_>, _>>()?;
    ensure!(profiles.iter().all(|p| p.is_some_and(|p| p.key == "a7c2-fe100gm-2xtc-x4cpl")),
        "held CA profile differs");
    ensure!((0..70).all(|i| full_source_supported(map.placement(i).unwrap(), full, crop, profiles[i])),
        "held crop does not support every twelve-site pull");
    let workspace = PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../..").canonicalize()?;
    ensure!(!config.out_dir.exists(), "output directory already exists");
    let parent = config.out_dir.parent().context("output parent")?.canonicalize()?;
    ensure!(parent.starts_with(workspace.join("experiments").canonicalize()?),
        "outputs must be below workspace experiments");
    let first = strehl_raw::decode(&paths[0])?;
    let levels = first.levels;
    let wb = first.wb_coeffs;
    ensure!(first.camera == "ILCE-7CM2" && first.iso == Some(100.0)
        && levels == Levels { black: 512.0, white: 15360.0 }
        && first.geometry() == full && first.active.width == 7032 && first.active.height == 4688
        && wb_gains(wb)?.map(f32::to_bits) == EXPECTED_WB_BITS
        && first.xyz_to_cam_rgb() == Some(EXPECTED_MATRIX), "held first-frame metadata differs");
    let active = first.active;
    let stride = first.stride;
    let buffer_height = first.buffer_height;
    let check_frame = |frame: &Frame| -> Result<()> {
        ensure!(frame.camera == "ILCE-7CM2" && frame.iso == Some(100.0) && frame.levels == levels
            && frame.active == active && frame.stride == stride && frame.buffer_height == buffer_height
            && frame.geometry() == full && wb_gains(frame.wb_coeffs)?.map(f32::to_bits) == EXPECTED_WB_BITS
            && frame.xyz_to_cam_rgb() == Some(EXPECTED_MATRIX), "full-pair source metadata drift");
        Ok(())
    };
    let merge_cfg = MergeConfig::default();
    ensure!(merge_cfg.bands == 7 && merge_cfg.gate == 2.0 && merge_cfg.exponent == 2.0
        && merge_cfg.sharpen_per_octave == 1.4 && merge_cfg.select == SelectMode::SoftPower
        && merge_cfg.admission == AdmissionMode::HardFloor && merge_cfg.base == BaseBand::Mean
        && merge_cfg.mean_coarse == 0 && merge_cfg.hull == Hull::InputRange
        && merge_cfg.fallback == Fallback::Mean && merge_cfg.significance_scale == 0.0,
        "held default merge configuration differs");
    let plan = chunk_plan(full, first.allocated_bytes(), 70, merge_cfg);
    ensure!(plan.canonical_chunks == 4 && plan.per_chunk == 18, "held canonical grouping differs");
    let workers = band_workers(plan.planning_bytes, 70)?;
    ensure!(workers == 8, "full-pair parent must bind eight execution threads");
    let pool = ThreadPoolBuilder::new().num_threads(workers).build()?;
    let domain = PyramidDomain::cropped(full, crop)?;
    let sizes = level_sizes(crop.width, crop.height, merge_cfg.bands);
    let noise = profile::noise_model_for(&first.camera, first.iso, levels);
    let matrix = color::camera_to_srgb(EXPECTED_MATRIX).context("held matrix singular")?
        .with_saturation(levels, wb_gains(wb)?, 1.0);
    let mut dev = image_out::OutputSpace::Srgb.develop(Some(matrix));
    dev.tone = Some(image_out::Tone { black: config.tone[0], white: config.tone[1], contrast: config.tone[2] });
    dev.exposure_gain = 1.0;
    std::fs::create_dir(&config.out_dir)?;
    write_json(&config.out_dir.join("started.json"), &json!({"schema":1,"mode":MODE,
        "source_dir":config.source_dir,"map_sha256":EXPECTED_MAP,"config_sha256":file_hash(&config_path)?,
        "original_crop":config.expected_crop,"effective_crop":config.expected_crop,"plan":plan,
        "execution_threads":workers,"wb_bits":EXPECTED_WB_BITS,"tone_bits":config.tone.map(f32::to_bits),
        "matrix":EXPECTED_MATRIX,"ca_profile":"a7c2-fe100gm-2xtc-x4cpl",
        "merge_config":format!("{merge_cfg:?}"),"native_dimensions":[2*crop.width,2*crop.height],
        "source_active":[active.x,active.y,active.width,active.height],"source_stride":stride,
        "source_buffer_height":buffer_height,"original_metadata_check":"length and modified time; all70 before/after both passes",
        "acceptance":"(source green - baseline reconstructed green)^2 <= 4*injected guide variance; heuristic, not calibrated probability"}))?;
    let mut base = BandWorker::new(domain, merge_cfg);
    let mut first = Some(first);
    let mut total = None;
    let mut evidence = Vec::new();
    pool.install(|| -> Result<()> {
        let mut chunks = paths.chunks(plan.per_chunk).enumerate().peekable();
        while let Some((chunk_index, chunk)) = chunks.next() {
            for (offset, path) in chunk.iter().enumerate() {
                let index = chunk_index * plan.per_chunk + offset;
                let frame_start = Instant::now();
                let frame = match first.take() { Some(f) => f, None => strehl_raw::decode(path)? };
                check_frame(&frame)?;
                let src_hash = source_hash(&frame);
                ensure!(base.fold(&OneFrame { frame: &frame, index }, index, levels, &noise, Some(&map), None)?,
                    "baseline source refused");
                ensure!(before[index] == stamp(path)?, "original metadata changed during baseline");
                evidence.push(json!({"index":index,"file":path.file_name().map(|v|v.to_string_lossy()),
                    "source_active_u16_sha256":src_hash,"guide_sha256":field_hash(&base.luma),
                    "variance_sha256":field_hash(&base.var),"beta":base.beta,
                    "source_bytes":before[index].0,"source_modified_ns":before[index].1.duration_since(SystemTime::UNIX_EPOCH)?.as_nanos().to_string(),
                    "baseline_seconds":frame_start.elapsed().as_secs_f64()}));
                eprintln!("green-match baseline {}/70, total {:.1}s", index + 1, started.elapsed().as_secs_f64());
            }
            absorb_chunk(&mut total, &mut base.merge, crop.width, crop.height, 4, merge_cfg);
            if chunks.peek().is_some() { base.reset_chunk(); }
        }
        Ok(())
    })?;
    drop(base);
    let total = total.context("empty full baseline")?;
    let baseline_averaged_fraction = total.averaged_fraction();
    let baseline = pool.install(|| total.finish(&mut Workspace::new(&sizes)));
    drop(total);
    let baseline_path = config.out_dir.join("baseline.tiff");
    pool.install(|| write_planes(&baseline_path, &baseline, crop, levels, wb, &dev))?;
    let baseline_sha256 = file_hash(&baseline_path)?;
    ensure!(baseline_sha256 == EXPECTED_BASELINE, "held full baseline differs: {baseline_sha256}");
    let target = baseline[1].iter().zip(&baseline[2]).map(|(a,b)| 0.5 * (a+b)).collect::<Vec<_>>();
    let target_sha256 = field_hash(&target);
    let baseline_rgb = pool.install(|| camera_rgb(&baseline, crop.width, crop.height, levels, wb))?;
    drop(baseline);
    write_json(&config.out_dir.join("baseline-ready.json"), &json!({"baseline_sha256":baseline_sha256,
        "target_green_sha256":target_sha256,"baseline_averaged_fraction":baseline_averaged_fraction,
        "frame_evidence":evidence,"seconds":started.elapsed().as_secs_f64()}))?;
    let n = crop.width * crop.height;
    let mut sums = vec![vec![0.0f32; n]; 12];
    let mut counts = vec![0u32; n];
    let mut planes = vec![vec![0.0f32; n]; 4];
    let mut luma = vec![0.0f32; n];
    let mut variance = vec![0.0f32; n];
    let mut warp = WarpScratch::new(full);
    pool.install(|| -> Result<()> {
        for (index, path) in paths.iter().enumerate() {
            let frame_start = Instant::now();
            let frame = strehl_raw::decode(path)?;
            check_frame(&frame)?;
            ensure!(source_hash(&frame) == evidence[index]["source_active_u16_sha256"].as_str().unwrap(),
                "independent second decode differs at frame {index}");
            ensure!(load_frame(&OneFrame { frame: &frame, index }, index, domain, levels, Some(&map), None,
                &mut warp, None, &mut planes, &mut luma)?, "replay source refused");
            luma_variance(&luma, &noise, &mut variance);
            ensure!(field_hash(&luma) == evidence[index]["guide_sha256"].as_str().unwrap()
                && field_hash(&variance) == evidence[index]["variance_sha256"].as_str().unwrap(),
                "full replay guide/variance differs from baseline at frame {index}");
            let mut extra = gather_full_source(&frame, map.placement(index)?, full, crop, profiles[index], 4)?;
            // Move the actual consumer's known four planes, without copying or
            // reinterpreting them; only the eight missing colours are gathered.
            let mut packed = std::mem::take(&mut planes);
            let known4_hashes = packed.iter().map(|p| field_hash(p)).collect::<Vec<_>>();
            packed.append(&mut extra);
            let accepted = apply_acceptance(&packed, &luma, &variance, &target, &mut sums, &mut counts)?;
            drop(packed.split_off(4));
            planes = packed;
            ensure!(before[index] == stamp(path)?, "original metadata changed during replay");
            evidence[index]["replay"] = json!({"source_active_u16":"BIT_EXACT_SECOND_DECODE",
                "guide_variance":"BIT_EXACT_BASELINE","known4":"MOVED_ACTUAL_CONSUMER_PLANES",
                "known4_sha256":known4_hashes,"accepted_quads":accepted.accepted_quads,
                "acceptance_mask_sha256":accepted.mask_sha256,"unsupported_samples":0,
                "seconds":frame_start.elapsed().as_secs_f64()});
            eprintln!("green-match colour replay {}/70, total {:.1}s", index + 1, started.elapsed().as_secs_f64());
        }
        Ok(())
    })?;
    drop(planes); drop(luma); drop(variance); drop(warp);
    let candidate_rgb = pool.install(|| finish_projection(&sums, &counts, &baseline_rgb,
        crop.width, crop.height, levels, wb))?;
    drop(sums); drop(baseline_rgb);
    let mut developed = vec![0u16; candidate_rgb.len()];
    pool.install(|| developed.par_chunks_mut(3).zip(candidate_rgb.par_chunks(3)).for_each(|(out, input)|
        out.copy_from_slice(&image_out::develop_pixel([input[0],input[1],input[2]], &dev))));
    drop(candidate_rgb);
    let candidate_path = config.out_dir.join("candidate.tiff");
    image_out::write_rgb16_described(&candidate_path, (2*crop.width) as u32, (2*crop.height) as u32, &developed, &dev)?;
    drop(developed);
    let mut histogram = vec![0usize; 71];
    for &count in &counts { ensure!(count <= 70, "invalid acceptance count"); histogram[count as usize] += 1; }
    let mut count_hash = Sha256::new();
    for &count in &counts { count_hash.update(count.to_le_bytes()); }
    ensure!(histogram.iter().sum::<usize>() == n, "acceptance accounting differs");
    // Native quad map: one byte per quad, 0 means the four native output
    // sites retained the baseline; 1 means projection from a single source.
    let count_path = config.out_dir.join("acceptance-counts.u8");
    let mut count_file = std::fs::OpenOptions::new().write(true).create_new(true).open(&count_path)?;
    let mut count_bytes = vec![0u8; 65536];
    for chunk in counts.chunks(count_bytes.len()) {
        for (dst, &v) in count_bytes.iter_mut().zip(chunk) { *dst = v as u8; }
        count_file.write_all(&count_bytes[..chunk.len()])?;
    }
    drop(count_file);
    for (i,path) in paths.iter().enumerate() { ensure!(before[i] == stamp(path)?, "original metadata changed after pair"); }
    ensure!(file_hash(&config.warp_map)? == EXPECTED_MAP, "original warp map changed");
    write_json(&config.out_dir.join("receipt.json"), &json!({"schema":1,"mode":MODE,"frames":70,
        "baseline_sha256":baseline_sha256,"candidate_sha256":file_hash(&candidate_path)?,
        "target_green_sha256":target_sha256,"acceptance_counts_sha256":digest(count_hash),
        "acceptance_count_histogram":histogram,"fallback_quads":histogram[0],
        "acceptance_count_map":{"path":count_path,"sha256":file_hash(&count_path)?,
            "dtype":"u8","shape_yx":[crop.height,crop.width],"order":"row-major quad grid"},
        "accepted_samples":counts.iter().map(|&v|v as usize).sum::<usize>(),
        "baseline_averaged_fraction":baseline_averaged_fraction,"unsupported_samples":0,
        "plan":plan,"frame_evidence":evidence,"native_dimensions":[2*crop.width,2*crop.height],
        "effective_crop":config.expected_crop,"original_metadata_unchanged":true,
        "seconds":started.elapsed().as_secs_f64()}))?;
    Ok(())
}
