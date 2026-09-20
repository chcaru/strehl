// One complete, held vitamin-C prescribed-donor triplet. Test-only, explicitly invoked by the
// resource-bounded parent runner. Originals are opened only for reading.
use super::*;
use phase_packed_rgb::full_stack::{absorb_chunk, chunk_plan, full_source_supported, write_planes};
use serde::Deserialize;
use serde_json::json;
use std::{fs::File, io::{Read, Write}, time::SystemTime};
use strehl_core::pyramid::{AdmissionMode, BaseBand, Fallback, Hull, SelectMode};
use strehl_core::pyramid::donor_consistency_diagnostic::SpatialDonor;

const EXPECTED_BASELINE: &str = "c0d8faca8a23f31a73b843fbc9aa9f55fda96b5fcce9d3540ebf6a2b4319bb21";
// Independently decoded from the held baseline. Full-1 proved its pixel bytes
// unchanged while TIFF Software truthfully changed with the build revision.
const EXPECTED_BASELINE_RGB16: &str = "2a19cd9b7236a13bf90e81b87e85b1058e071aa19f4a5af82b97f453687d0dda";
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
fn check_written_baseline(path: &Path) -> Result<(String, String)> {
    let mut decoder = tiff::decoder::Decoder::new(std::io::BufReader::new(File::open(path)?))?;
    ensure!(decoder.dimensions()? == (6920, 4612)
        && decoder.colortype()? == tiff::ColorType::RGB(16), "baseline TIFF shape/type differs");
    let software = decoder.get_tag_ascii_string(tiff::tags::Tag::Software)?;
    let pixels = match decoder.read_image()? {
        tiff::decoder::DecodingResult::U16(pixels) => pixels,
        _ => anyhow::bail!("baseline TIFF decoder did not return u16 samples"),
    };
    ensure!(pixels.len() == 95_745_120 && !decoder.more_images(), "baseline TIFF sample/page count differs");
    let mut h = Sha256::new();
    let mut bytes = vec![0u8; 65536];
    for chunk in pixels.chunks(bytes.len() / 2) {
        for (dst, value) in bytes.chunks_exact_mut(2).zip(chunk) {
            dst.copy_from_slice(&value.to_le_bytes());
        }
        h.update(&bytes[..chunk.len() * 2]);
    }
    let hash = digest(h);
    ensure!(hash == EXPECTED_BASELINE_RGB16, "held full baseline RGB16 pixels differ: {hash}");
    Ok((hash, software))
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

// Dispatch only; each fixed experiment keeps its existing arithmetic separate.
enum FullDonor { Bands(DonorBlend), Spatial(SpatialDonor) }
impl FullDonor {
    fn new(spatial: bool, sizes: &[strehl_core::pyramid::LevelSize], masks: &[Vec<f32>]) -> Self {
        if spatial { Self::Spatial(SpatialDonor::new(sizes,4,masks)) }
        else { Self::Bands(DonorBlend::new(sizes,4,masks)) }
    }
    fn add_source(&mut self, regions: &[usize], planes: &[Vec<f32>]) {
        match self { Self::Bands(d) => d.add_source(regions,planes), Self::Spatial(d) => d.add_source(regions,planes) }
    }
    fn finish(&self, merge: &BandMerge, ws: &mut Workspace) -> Vec<Vec<f32>> {
        match self { Self::Bands(d) => d.finish(merge,ws), Self::Spatial(d) => d.finish(merge,ws) }
    }
    fn bands(&self) -> &DonorBlend {
        match self { Self::Bands(d) => d, Self::Spatial(_) => panic!("coefficient observer excludes spatial mode") }
    }
    fn spatial(&self) -> &SpatialDonor {
        match self { Self::Spatial(d) => d, Self::Bands(_) => panic!("spatial witness requires spatial mode") }
    }
}

mod attribution {
    include!(concat!(env!("CARGO_MANIFEST_DIR"), "/../../experiments/donor-consistency/attribution.rs"));
}
mod spatial_witness {
    include!(concat!(env!("CARGO_MANIFEST_DIR"), "/../../experiments/donor-consistency/spatial-witness.rs"));
}
impl PyramidFrameSource for OneFrame<'_> {
    fn len(&self) -> usize { 70 }
    fn decode(&self, index: usize) -> Result<Frame> {
        ensure!(index == self.index, "full-pair one-frame source index");
        Ok(self.frame.clone())
    }
}

#[test]
#[ignore = "explicit complete photo pair; parent bounds resources and freezes configuration"]
fn vitamin_c_complete_triplet() -> Result<()> {
    let started = Instant::now();
    let spatial = match std::env::var("STREHL_DONOR_SPATIAL") {
        Err(std::env::VarError::NotPresent) => false,
        Ok(value) if value == "1" => true,
        _ => anyhow::bail!("STREHL_DONOR_SPATIAL must be absent or exactly1"),
    };
    let target_setting=match std::env::var("STREHL_DONOR_TARGET") {
        Ok(value)=>Some(value),
        Err(std::env::VarError::NotPresent)=>None,
        Err(error)=>return Err(error.into()),
    };
    let corrected_dark_tail=target_from_setting(target_setting.as_deref(),spatial)?;
    let target=if corrected_dark_tail {"corrected-dark-tail"} else {"original"};
    let segments=target_segments(corrected_dark_tail);
    ensure!(!spatial || std::env::var_os("STREHL_DONOR_ATTRIBUTION_DIR").is_none(),
        "old coefficient attribution is incompatible with spatial donor mode");
    ensure!(spatial || std::env::var_os("STREHL_DONOR_SPATIAL_WITNESS_DIR").is_none(),
        "spatial witness requires spatial donor mode");
    let mode = if corrected_dark_tail { "fixed-native-spatial-donor-corrected-dark-tail-oracle" }
        else if spatial { "fixed-native-spatial-donor-oracle" } else { MODE };
    let counterfactual = if spatial { "baseline_pre + (sum(mask0*full_donor_ac) - coverage0*baseline_ac); unchanged terminal mean" }
        else { "prescribed shared donor AC coefficients; baseline terminal mean retained" };
    let config_path = PathBuf::from(std::env::var_os("STREHL_DONOR_CONSISTENCY_FULL_CONFIG")
        .context("STREHL_DONOR_CONSISTENCY_FULL_CONFIG required")?);
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
    let mut attribution = attribution::Observer::from_env(&workspace, &config.out_dir)?;
    let mut spatial_witness = spatial_witness::Witness::from_env(&workspace,&config.out_dir)?;
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
    write_json(&config.out_dir.join("started.json"), &json!({"schema":1,"mode":mode,"target":target,
        "source_dir":config.source_dir,"map_sha256":EXPECTED_MAP,"config_sha256":file_hash(&config_path)?,
        "original_crop":config.expected_crop,"effective_crop":config.expected_crop,"plan":plan,
        "execution_threads":workers,"wb_bits":EXPECTED_WB_BITS,"tone_bits":config.tone.map(f32::to_bits),
        "matrix":EXPECTED_MATRIX,"ca_profile":"a7c2-fe100gm-2xtc-x4cpl",
        "merge_config":format!("{merge_cfg:?}"),"native_dimensions":[2*crop.width,2*crop.height],
        "source_active":[active.x,active.y,active.width,active.height],"source_stride":stride,
        "source_buffer_height":buffer_height,"original_metadata_check":"length and modified time; all70 before/after both passes",
        "counterfactual":counterfactual,
        "donors":DONORS,"late_donor":69,"segments":segments,"radii_native":[16,24],
        "mask_native_origin":[0,0],"mask_sample_offset_native":[0.5,0.5]}))?;
    let masks0=fixed_masks_for_target(crop.width,crop.height,[0,0],corrected_dark_tail);
    let mut oracle=FullDonor::new(spatial,&sizes,&masks0);
    let mut late=FullDonor::new(spatial,&sizes,&masks0);
    let mut mask_record=match &oracle {
        FullDonor::Bands(donor) => {
            let mask_receipt=donor.masks().iter().enumerate().map(|(region,p)|json!({
        "region":region,"prescribed_donor":DONORS[region],"segment":segments[region],
        "levels":(0..p.levels()).map(|k|json!({"level":k,
            "dimensions":[p.sizes()[k].width,p.sizes()[k].height],
            "sha256":field_hash(p.level(k)),
            "positive_coefficients":p.level(k).iter().filter(|&&v|v>0.0).count(),
            "terminal_ignored":k+1==p.levels()})).collect::<Vec<_>>()
    })).collect::<Vec<_>>();
            json!({
        "native_origin":[0,0],"native_quad_centre":[0.5,0.5],"radii":[16,24],
                "raw_overlap_counts":donor.raw_overlap_counts(),"normalized_counts":donor.normalized_counts(),
                "masks":mask_receipt})
        },
        FullDonor::Spatial(donor) => json!({
            "native_origin":[0,0],"native_quad_centre":[0.5,0.5],"radii":[16,24],
            "mask_domain":"finest output quads after full-domain AC reconstruction; no reduced masks",
            "normalized_count":donor.normalized_count(),"coverage_sha256":field_hash(donor.coverage()),
            "masks":donor.masks().iter().enumerate().map(|(region,m)|json!({
                "region":region,"prescribed_donor":DONORS[region],"segment":segments[region],
                "dimensions":[crop.width,crop.height],"sha256":field_hash(m),
                "positive_quads":m.iter().filter(|&&v|v>0.0).count()})).collect::<Vec<_>>()
        }),
    };
    mask_record["target"]=json!(target);
    mask_record["segments"]=json!(segments);
    write_json(&config.out_dir.join("masks.json"),&mask_record)?;
    drop(masks0);
    let mut base=BandWorker::new(domain,merge_cfg);
    let mut first=Some(first);let mut total=None;let mut evidence=Vec::new();
    pool.install(||->Result<()> {
        let mut chunks=paths.chunks(plan.per_chunk).enumerate().peekable();
        while let Some((chunk_index,chunk))=chunks.next() {
            for (offset,path) in chunk.iter().enumerate() {
                let index=chunk_index*plan.per_chunk+offset;
                let frame_start=Instant::now();
                let frame=match first.take(){Some(f)=>f,None=>strehl_raw::decode(path)?};
                check_frame(&frame)?;let src_hash=source_hash(&frame);
                ensure!(base.fold(&OneFrame{frame:&frame,index},index,levels,&noise,Some(&map),None)?,
                    "baseline source refused");
                let prescribed=DONORS.iter().position(|&d|d==index);
                let is_late=index==69;
                let donor_hashes=if prescribed.is_some() || is_late {
                    Some(base.planes.iter().map(|p|field_hash(p)).collect::<Vec<_>>())
                } else {None};
                if let (Some(witness),Some(hashes))=(spatial_witness.as_mut(),donor_hashes.as_ref()) {
                    witness.source(index,&base.planes,&sizes,hashes,levels,wb,&dev)?;
                }
                if let Some(region)=prescribed {oracle.add_source(&[region],&base.planes);}
                if is_late {late.add_source(&[0,1,2],&base.planes);}
                if let Some(ref hashes)=donor_hashes {
                    ensure!(*hashes==base.planes.iter().map(|p|field_hash(p)).collect::<Vec<_>>(),
                        "donor accumulation mutated the actual gathered source");
                }
                ensure!(source_hash(&frame)==src_hash,"original decoded source changed");
                ensure!(before[index]==stamp(path)?,"original metadata changed during baseline");
                evidence.push(json!({"index":index,"file":path.file_name().map(|v|v.to_string_lossy()),
                    "source_active_u16_sha256":src_hash,"guide_sha256":field_hash(&base.luma),
                    "variance_sha256":field_hash(&base.var),"beta":base.beta,
                    "source_bytes":before[index].0,"source_modified_ns":before[index].1.duration_since(SystemTime::UNIX_EPOCH)?.as_nanos().to_string(),
                    "prescribed_region":prescribed,"late_control":is_late,"actual_known4_sha256":donor_hashes,
                    "baseline_seconds":frame_start.elapsed().as_secs_f64()}));
                eprintln!("donor-consistency source {}/70, total {:.1}s",index+1,started.elapsed().as_secs_f64());
            }
            absorb_chunk(&mut total,&mut base.merge,crop.width,crop.height,4,merge_cfg);
            if chunks.peek().is_some(){base.reset_chunk();}
        }
        Ok(())
    })?;
    drop(base);
    let total=total.context("empty full baseline")?;
    let baseline_averaged_fraction=total.averaged_fraction();
    let baseline=pool.install(||total.finish(&mut Workspace::new(&sizes)));
    let baseline_plane_hashes=baseline.iter().map(|p|field_hash(p)).collect::<Vec<_>>();
    let baseline_path=config.out_dir.join("baseline.tiff");
    pool.install(||write_planes(&baseline_path,&baseline,crop,levels,wb,&dev))?;
    drop(baseline);
    let baseline_sha256=file_hash(&baseline_path)?;
    let (baseline_rgb16_sha256,baseline_software)=check_written_baseline(&baseline_path)?;
    write_json(&config.out_dir.join("baseline-ready.json"),&json!({
        "baseline_sha256":baseline_sha256,"baseline_rgb16_le_sha256":baseline_rgb16_sha256,
        "baseline_software":baseline_software,"baseline_planes_sha256":baseline_plane_hashes,
        "reference_baseline_file_sha256":EXPECTED_BASELINE,"baseline_averaged_fraction":baseline_averaged_fraction,
        "frame_evidence":evidence,"seconds":started.elapsed().as_secs_f64()}))?;
    // Guard above passes BEFORE either donor image is developed or written.
    let candidate=pool.install(||oracle.finish(&total,&mut Workspace::new(&sizes)));
    let candidate_plane_hashes=candidate.iter().map(|p|field_hash(p)).collect::<Vec<_>>();
    let candidate_path=config.out_dir.join("candidate.tiff");
    pool.install(||write_planes(&candidate_path,&candidate,crop,levels,wb,&dev))?;
    if let Some(observer) = attribution.as_mut() {
        pool.install(||observer.record("candidate",&total,oracle.bands(),&sizes,&candidate))?;
    }
    if let Some(witness)=spatial_witness.as_mut() {
        pool.install(||witness.finish_arm("candidate",&total,oracle.spatial(),&sizes,&candidate))?;
    }
    drop(candidate);drop(oracle);
    let late_image=pool.install(||late.finish(&total,&mut Workspace::new(&sizes)));
    let late_plane_hashes=late_image.iter().map(|p|field_hash(p)).collect::<Vec<_>>();
    let late_path=config.out_dir.join("late.tiff");
    pool.install(||write_planes(&late_path,&late_image,crop,levels,wb,&dev))?;
    if let Some(observer) = attribution.as_mut() {
        pool.install(||observer.record("late",&total,late.bands(),&sizes,&late_image))?;
    }
    if let Some(witness)=spatial_witness.as_mut() {
        pool.install(||witness.finish_arm("late",&total,late.spatial(),&sizes,&late_image))?;
    }
    drop(late_image);drop(late);drop(total);
    if let Some(observer) = attribution { observer.finish(&sizes)?; }
    if let Some(witness)=spatial_witness { witness.finish(&sizes,levels,wb,config.tone)?; }
    for (i,path) in paths.iter().enumerate(){ensure!(before[i]==stamp(path)?,"original metadata changed after triplet");}
    ensure!(file_hash(&config.warp_map)?==EXPECTED_MAP,"held warp map changed");
    write_json(&config.out_dir.join("receipt.json"),&json!({"schema":1,"mode":mode,"frames":70,
        "target":target,"segments":segments,"radii_native":[16,24],
        "counterfactual":counterfactual,
        "baseline_sha256":baseline_sha256,"candidate_sha256":file_hash(&candidate_path)?,"late_sha256":file_hash(&late_path)?,
        "baseline_rgb16_le_sha256":baseline_rgb16_sha256,"baseline_software":baseline_software,
        "reference_baseline_file_sha256":EXPECTED_BASELINE,
        "baseline_planes_sha256":baseline_plane_hashes,"candidate_planes_sha256":candidate_plane_hashes,
        "late_planes_sha256":late_plane_hashes,"baseline_averaged_fraction":baseline_averaged_fraction,
        "donors":DONORS,"late_donor":69,"mask_receipt_sha256":file_hash(&config.out_dir.join("masks.json"))?,
        "terminal_base":"unchanged baseline mean","input_range":"same baseline hull after actual collapse",
        "plan":plan,"frame_evidence":evidence,"native_dimensions":[2*crop.width,2*crop.height],
        "effective_crop":config.expected_crop,"original_metadata_unchanged":true,
        "seconds":started.elapsed().as_secs_f64()}))?;
    Ok(())
}
