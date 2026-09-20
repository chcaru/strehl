// Parallel fixed-boundary observational adapter; no generated-quality admission.
// Parent owns resource bounds, compilation, execution, and photographic review.
use super::*;
use phase_packed_rgb::full_stack::{absorb_chunk,chunk_plan,full_source_supported,write_planes};
use serde::Deserialize;
use serde_json::json;
use std::{fs::File,io::{Read,Write},time::SystemTime};
fn finish_digest(h:Sha256)->String {h.finalize().iter().map(|b|format!("{b:02x}")).collect()}
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
pub(crate) struct Config {
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
    Ok(finish_digest(h))
}
fn check_written_baseline(path: &Path) -> Result<(String, String)> {
    let result=read_written_rgb16(path)?;
    ensure!(result.0==EXPECTED_BASELINE_RGB16,"held full baseline RGB16 pixels differ: {}",result.0);
    Ok(result)
}
fn read_written_rgb16(path: &Path) -> Result<(String, String)> {
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
    let hash = finish_digest(h);
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
    finish_digest(h)
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
    finish_digest(h)
}
fn stamp(path: &Path) -> Result<(u64, SystemTime)> {
    let m = std::fs::metadata(path)?;
    Ok((m.len(), m.modified()?))
}
struct OneFrame<'a> { frame: &'a Frame, index: usize }


impl PyramidFrameSource for OneFrame<'_> {
    fn len(&self)->usize{70}
    fn decode(&self,index:usize)->Result<Frame>{ensure!(index==self.index,"one-frame source index");Ok(self.frame.clone())}
}
struct Accumulator {
    boundary:BoundaryPlan,bands:Vec<Subband>,gains:[f32;4],cfg:MergeConfig,
    // sums and den share each coefficient's running maximum weight scale.
    // Their quotient is unchanged; no raw weight*coefficient product is stored.
    sums:Vec<Vec<Complex>>,means:Vec<Vec<Complex>>,den:Vec<f32>,counts:Vec<u16>,scales:Vec<f32>,
    low:Vec<Vec<f32>>,high:Vec<Vec<f32>>,summary:Vec<DirectionWeightSummary>,frames:usize,
}
impl Accumulator {
    fn new(wb:[f32;4],cfg:MergeConfig)->Result<Self> {
        let boundary=BoundaryPlan::full_vitamin_c();let n=boundary.padded_width*boundary.padded_height;
        let native_n=boundary.input_width*boundary.input_height;
        let bands=subbands_scoped(boundary.padded_width,boundary.padded_height,true)?;
        let summary=bands.iter().map(|b|DirectionWeightSummary{min_weight:f32::INFINITY,max_weight:0.0,
            positive_source_coefficients:0,multi_source_coefficients:0,total_coefficients:b.positions.len(),
            own_plane_positive_source_coefficients:[0;4],own_plane_positive_aggregate_zero:[0;4]}).collect();
        let gains=[wb[0]/wb[1],1.0,1.0,wb[2]/wb[1]].map(|v|v*v);
        ensure!(gains.iter().all(|v|v.is_finite()),"WB squared overflow");
        Ok(Self{boundary,bands,gains,cfg,sums:vec![vec![Complex::default();n];4],means:vec![vec![Complex::default();n];4],
            den:vec![0.0;n],counts:vec![0;n],scales:vec![0.0;n],low:vec![vec![f32::INFINITY;native_n];4],
            high:vec![vec![f32::NEG_INFINITY;native_n];4],summary,frames:0})
    }
    fn fold(&mut self,frame:&Frame,index:usize,warp:Similarity,crop:align_cmd::CropRect,
        noise:&NoiseModel,known:&[Vec<f32>])->Result<serde_json::Value> {
        let signal_start=Instant::now();let p=&self.boundary;
        let wave=extend_four(known,p)?.iter().map(|v|forward_real_scoped(v,p.padded_width,p.padded_height,true))
            .collect::<Result<Vec<_>>>()?;
        let signal_seconds=signal_start.elapsed().as_secs_f64();let probe_start=Instant::now();
        let probe=probe_from_wave_scoped(frame,warp,crop,noise,p,index,false,&wave,true)?;
        let probe_seconds=probe_start.elapsed().as_secs_f64();let weight_start=Instant::now();
        fold_coefficients(known,&wave,&probe.variance4,self.cfg,self.gains,p.depth(),&self.bands,
            &mut self.sums,&mut self.means,&mut self.den,&mut self.counts,&mut self.low,&mut self.high,&mut self.summary,false,&mut self.scales)?;
        self.frames+=1;
        let weight_seconds=weight_start.elapsed().as_secs_f64();
        // Hashes are bounded scalar receipts; no per-frame coefficient volume retained.
        Ok(json!({"source_index":index,"signal_transform_seconds":signal_seconds,"probe_seconds":probe_seconds,
            "weights_seconds":weight_seconds,"probe_seeds":probe.seeds,"probe_pairs":PROBE_PAIRS,
            "original_variance_sha256":field_hash(&probe.original_variance),
            "coefficient_variance_sha256":probe.variance4.iter().map(|v|field_hash(v)).collect::<Vec<_>>(),
            "coefficient_variance_min_max":probe.variance4.iter().map(|v|[
                v.iter().copied().fold(f32::INFINITY,f32::min),v.iter().copied().fold(0.0,f32::max)]).collect::<Vec<_>>() }))
    }
    fn finish(mut self)->Result<(Vec<Vec<f32>>,serde_json::Value)> {
        ensure!(self.frames>0 && self.frames<=70,"bounded positive observational source count");
        let fallback=self.bands.iter().map(|b|b.positions.iter().filter(|&&i|self.den[i]==0.0).count() as f64/b.positions.len() as f64).collect::<Vec<_>>();
        for (b,s) in self.bands.iter().zip(&mut self.summary){s.multi_source_coefficients=b.positions.iter().filter(|&&i|self.counts[i]>1).count();}
        for c in 0..4 {for i in 0..self.den.len() {
            if self.den[i]>0.0 {self.sums[c][i].re/=self.den[i];self.sums[c][i].im/=self.den[i];}
            else{self.sums[c][i].re=self.means[c][i].re/self.frames as f32;self.sums[c][i].im=self.means[c][i].im/self.frames as f32;}
        }}drop(self.means);
        let p=&self.boundary;
        let reconstructed=self.sums.iter().map(|v|Ok(transform_all(v,p.padded_width,p.padded_height,true,true)?.iter()
            .map(|v|v.re).collect::<Vec<_>>())).collect::<Result<Vec<_>>>()?;
        let mut output=crop_four(&reconstructed,p)?;
        for c in 0..4 {for i in 0..output[c].len(){output[c][i]=output[c][i].clamp(self.low[c][i],self.high[c][i]);}}
        ensure!(output.iter().flatten().all(|v|v.is_finite()),"nonfinite full candidate output");
        let summary=json!({"candidate_fallback_fraction":fallback,"bands":self.bands.iter().zip(&self.summary).map(|(b,s)|json!({
            "level":b.level,"direction":b.direction,"dimensions":[b.width,b.height],"min_weight":s.min_weight,
            "max_weight":s.max_weight,"positive_source_coefficients":s.positive_source_coefficients,
            "multi_source_coefficients":s.multi_source_coefficients,"total_coefficients":s.total_coefficients})).collect::<Vec<_>>()});
        Ok((output,summary))
    }
}
#[test]
#[ignore="explicit observational image/cost run; parent bounds resources"]
fn vitamin_c_observational_pair()->Result<()> {
    let started=Instant::now();
    let phase=std::env::var("STREHL_PARALLEL_CFA_PHASE").context("cost/full phase required")?;
    ensure!(phase=="cost" || phase=="full","phase must be cost or full");let cost=phase=="cost";
    let config_path = PathBuf::from(std::env::var_os("STREHL_PARALLEL_CFA_FULL_CONFIG")
        .context("STREHL_PARALLEL_CFA_FULL_CONFIG required")?);
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
        && align_cmd::direct_plane_mode()? == align_cmd::DirectPlaneMode::Rounded
        && align_cmd::native_gpu_integration::gpu_gather_enabled()?,
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
    let first_index=if cost {35}else{0};
    let decode_start=Instant::now();
    let first = strehl_raw::decode(&paths[first_index])?;
    let first_decode_seconds=decode_start.elapsed().as_secs_f64();
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
    write_json(&config.out_dir.join("started.json"),&json!({"schema":1,"mode":"observational-parallel-cfa-wavelet",
        "phase":phase,"generated_quality_admitted":false,"source_count":if cost{1}else{70},"cost_source_index":35,
        "source_dir":config.source_dir,"map_sha256":EXPECTED_MAP,"config_sha256":file_hash(&config_path)?,
        "original_crop":config.expected_crop,"effective_crop":config.expected_crop,"plan":plan,
        "execution_threads":workers,"operator_workers":1,"wb_bits":EXPECTED_WB_BITS,"tone_bits":config.tone.map(f32::to_bits),
        "matrix":EXPECTED_MATRIX,"ca_profile":"a7c2-fe100gm-2xtc-x4cpl","merge_config":format!("{merge_cfg:?}"),
        "baseline_level_sizes":sizes.iter().map(|s|[s.width,s.height]).collect::<Vec<_>>(),
        "candidate_extent":[4096,4096],"candidate_levels":12,"candidate_terminal":[1,1],"padding_left_top":[318,895],
        "native_dimensions":[2*crop.width,2*crop.height],"source_active":[active.x,active.y,active.width,active.height],
        "source_stride":stride,"source_buffer_height":buffer_height,"probe_pairs":PROBE_PAIRS,
        "diagnostics":false,"variance":"eight independent original-source pairs through actual rounded GPU MHC/Catmull/CA gather",
        "admission":"observation only; prior generated quality rejection retained"}))?;
    let mut base=BandWorker::new(domain,merge_cfg);let mut accumulator=Accumulator::new(wb,merge_cfg)?;
    let mut first=Some(first);let mut total=None;let mut evidence=Vec::new();
    let indices=if cost{vec![35]}else{(0..70).collect::<Vec<_>>()};
    let processing_start=Instant::now();
    pool.install(||->Result<()> {
        let mut chunks=indices.chunks(plan.per_chunk).peekable();
        while let Some(chunk)=chunks.next(){
            for &index in chunk {
                let frame_start=Instant::now();let decode_start=Instant::now();
                let (frame,decode_seconds)=match first.take(){Some(frame)=>(frame,first_decode_seconds),
                    None=>(strehl_raw::decode(&paths[index])?,decode_start.elapsed().as_secs_f64())};
                check_frame(&frame)?;let src_hash=source_hash(&frame);let baseline_start=Instant::now();
                ensure!(base.fold(&OneFrame{frame:&frame,index},index,levels,&noise,Some(&map),None)?,"actual baseline refused source");
                let baseline_seconds=baseline_start.elapsed().as_secs_f64();
                let known_hashes=base.planes.iter().map(|p|field_hash(p)).collect::<Vec<_>>();
                let mut row=accumulator.fold(&frame,index,map.placement(index).context("source unplaced")?,crop,&noise,&base.planes)?;
                ensure!(known_hashes==base.planes.iter().map(|p|field_hash(p)).collect::<Vec<_>>(),"candidate mutated actual known4");
                ensure!(source_hash(&frame)==src_hash && before[index]==stamp(&paths[index])?,"original source changed");
                row["source_active_u16_sha256"]=json!(src_hash);row["actual_known4_sha256"]=json!(known_hashes);
                row["actual_guide_sha256"]=json!(field_hash(&base.luma));row["actual_variance_sha256"]=json!(field_hash(&base.var));
                row["decode_seconds"]=json!(decode_seconds);row["baseline_fold_seconds"]=json!(baseline_seconds);
                row["frame_seconds"]=json!(frame_start.elapsed().as_secs_f64());
                write_json(&config.out_dir.join(format!("source-{index:02}.json")),&row)?;evidence.push(row);
                eprintln!("parallel wavelet source {index}/69, {:.1}s",started.elapsed().as_secs_f64());
            }
            absorb_chunk(&mut total,&mut base.merge,crop.width,crop.height,4,merge_cfg);
            if chunks.peek().is_some(){base.reset_chunk();}
        }Ok(())
    })?;
    let processing_seconds=processing_start.elapsed().as_secs_f64();
    let source_phase_seconds=processing_seconds+first_decode_seconds;
    eprintln!("parallel wavelet sources complete; finishing baseline, {:.1}s",started.elapsed().as_secs_f64());
    let finish_start=Instant::now();drop(base);
    let total=total.context("empty baseline")?;let baseline_averaged_fraction=total.averaged_fraction();
    let baseline_start=Instant::now();let baseline=pool.install(||total.finish(&mut Workspace::new(&sizes)));
    drop(total);let baseline_plane_hashes=baseline.iter().map(|p|field_hash(p)).collect::<Vec<_>>();
    let baseline_path=config.out_dir.join("baseline.tiff");
    pool.install(||write_planes(&baseline_path,&baseline,crop,levels,wb,&dev))?;drop(baseline);
    let baseline_finish_write_seconds=baseline_start.elapsed().as_secs_f64();
    let baseline_sha256=file_hash(&baseline_path)?;
    let baseline_check=if cost{None}else{Some(check_written_baseline(&baseline_path)?)};
    // Full baseline pixel guard must pass before candidate reconstruction/write.
    eprintln!("parallel wavelet baseline written; reconstructing candidate, {:.1}s",started.elapsed().as_secs_f64());
    let candidate_start=Instant::now();let (candidate,summary)=pool.install(||accumulator.finish())?;
    let candidate_finish_seconds=candidate_start.elapsed().as_secs_f64();
    let candidate_plane_hashes=candidate.iter().map(|p|field_hash(p)).collect::<Vec<_>>();
    if cost{ensure!(candidate_plane_hashes==evidence[0]["actual_known4_sha256"].as_array().unwrap().iter()
        .map(|v|v.as_str().unwrap().to_owned()).collect::<Vec<_>>(),"one-source hull output differs from actual gathered source");}
    let candidate_path=config.out_dir.join("candidate.tiff");let write_start=Instant::now();
    eprintln!("parallel wavelet candidate reconstructed; writing, {:.1}s",started.elapsed().as_secs_f64());
    pool.install(||write_planes(&candidate_path,&candidate,crop,levels,wb,&dev))?;drop(candidate);
    let candidate_write_seconds=write_start.elapsed().as_secs_f64();
    for (i,path) in paths.iter().enumerate(){ensure!(before[i]==stamp(path)?,"original metadata changed");}
    ensure!(file_hash(&config.warp_map)?==EXPECTED_MAP,"held map changed");
    let candidate_sha256=file_hash(&candidate_path)?;
    let cost_rgb16_check=if cost{
        let b=read_written_rgb16(&baseline_path)?;let c=read_written_rgb16(&candidate_path)?;
        ensure!(b.0==c.0 && baseline_plane_hashes==candidate_plane_hashes,
            "one-source baseline/candidate delivered output differs");Some(c)
    }else{None};
    let finish_seconds=finish_start.elapsed().as_secs_f64();
    let receipt=json!({"schema":1,"mode":"observational-parallel-cfa-wavelet","phase":phase,"generated_quality_admitted":false,
        "frames":indices.len(),"source_indices":indices,"operator_workers":1,"execution_threads":workers,
        "effective_crop":config.expected_crop,"native_dimensions":[6920,4612],"candidate_extent":[4096,4096],"candidate_levels":12,
        "plan":plan,"baseline_sha256":baseline_sha256,"candidate_sha256":candidate_sha256,
        "baseline_rgb16_check":baseline_check,"reference_baseline_rgb16_sha256":EXPECTED_BASELINE_RGB16,
        "cost_rgb16_check":cost_rgb16_check,
        "reference_baseline_file_sha256":EXPECTED_BASELINE,"baseline_planes_sha256":baseline_plane_hashes,
        "candidate_planes_sha256":candidate_plane_hashes,"baseline_averaged_fraction":baseline_averaged_fraction,
        "candidate":summary,"frame_evidence":evidence,"original_metadata_unchanged":true,
        "source_phase_seconds":source_phase_seconds,"finish_seconds":finish_seconds,
        "processing_seconds":processing_seconds,"baseline_finish_write_seconds":baseline_finish_write_seconds,
        "candidate_finish_seconds":candidate_finish_seconds,"candidate_write_seconds":candidate_write_seconds,
        "seconds":started.elapsed().as_secs_f64(),"quality_claim":false,"diagnostics":false});
    write_json(&config.out_dir.join(if cost{"cost.json"}else{"receipt.json"}),&receipt)?;
    Ok(())
}
