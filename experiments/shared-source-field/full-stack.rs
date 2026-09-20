// Complete fixed70-source pair. Root alone executes this ignored test after admission.
use super::*;
use phase_packed_rgb::full_stack::{absorb_chunk, chunk_plan, write_planes};
use serde::Deserialize;
use serde_json::json;
use sha2::{Digest, Sha256};
use std::{fs::File, io::{Read, Write}, path::{Path, PathBuf}, time::{Instant, SystemTime}};
use strehl_core::pyramid::{AdmissionMode, BaseBand, Fallback, Hull, SelectMode};

const BASELINE_FILE: &str = "c0d8faca8a23f31a73b843fbc9aa9f55fda96b5fcce9d3540ebf6a2b4319bb21";
const BASELINE_PIXELS: &str = "2a19cd9b7236a13bf90e81b87e85b1058e071aa19f4a5af82b97f453687d0dda";
const MAP_HASH: &str = "84275850a032dc8beb88945b00514a58ebca433e267c8e10342ac55986cf830f";
const WB_BITS: [u32;3] = [1070374912,1065353216,1076715520];
const MATRIX: [[f32;3];3] = [[0.746,-0.2365,-0.0588],[-0.5687,1.3442,0.2474],[-0.0624,0.1156,0.6584]];

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct Config {
    schema:u32, source_dir:PathBuf, warp_map:PathBuf, warp_map_sha256:String,
    out_dir:PathBuf, expected_crop:[usize;4], max_extra_inset_quads:usize,
    expected_xyz_to_cam:[[f32;3];3], tone:[f32;3],
}
fn hex(h:Sha256)->String {h.finalize().iter().map(|v|format!("{v:02x}")).collect()}
fn file_hash(path:&Path)->Result<String> {
    let mut file=File::open(path)?;let mut h=Sha256::new();let mut buf=vec![0u8;1<<20];
    loop {let n=file.read(&mut buf)?;if n==0 {break;}h.update(&buf[..n]);}Ok(hex(h))
}
fn field_hash(values:&[f32])->String {
    let mut h=Sha256::new();let mut buf=vec![0u8;65536];
    for chunk in values.chunks(buf.len()/4) {
        for (dst,v) in buf.chunks_exact_mut(4).zip(chunk) {dst.copy_from_slice(&v.to_bits().to_le_bytes());}
        h.update(&buf[..4*chunk.len()]);
    }hex(h)
}
fn source_hash(frame:&Frame)->String {
    let mut h=Sha256::new();let mut row=vec![0u8;2*frame.active.width];
    for y in 0..frame.active.height {
        for (dst,v) in row.chunks_exact_mut(2).zip(frame.active_row(y)) {dst.copy_from_slice(&v.to_le_bytes());}
        h.update(&row);
    }hex(h)
}
fn stamp(path:&Path)->Result<(u64,SystemTime)> {let m=std::fs::metadata(path)?;Ok((m.len(),m.modified()?))}
fn write_json(path:&Path,value:&serde_json::Value)->Result<()> {
    let mut f=std::fs::OpenOptions::new().write(true).create_new(true).open(path)?;
    serde_json::to_writer_pretty(&mut f,value)?;writeln!(f)?;Ok(())
}
fn write_field(path:&Path,values:&[f32])->Result<()> {
    let mut f=std::fs::OpenOptions::new().write(true).create_new(true).open(path)?;
    let mut bytes=vec![0u8;65536];
    for chunk in values.chunks(bytes.len()/4) {
        for (dst,v) in bytes.chunks_exact_mut(4).zip(chunk) {dst.copy_from_slice(&v.to_bits().to_le_bytes());}
        f.write_all(&bytes[..4*chunk.len()])?;
    }Ok(())
}
fn wb_gains(wb:[f32;4])->Result<[f32;3]> {
    ensure!(wb[..3].iter().all(|v|v.is_finite() && *v>0.0),"invalid held WB");
    Ok([wb[0]/wb[1],1.0,wb[2]/wb[1]])
}
fn check_written_baseline(path:&Path)->Result<(String,String)> {
    let mut decoder=tiff::decoder::Decoder::new(std::io::BufReader::new(File::open(path)?))?;
    ensure!(decoder.dimensions()?==(6920,4612) && decoder.colortype()?==tiff::ColorType::RGB(16),
        "held baseline TIFF shape/type differs");
    let software=decoder.get_tag_ascii_string(tiff::tags::Tag::Software)?;
    let pixels=match decoder.read_image()? {
        tiff::decoder::DecodingResult::U16(v)=>v,
        _=>anyhow::bail!("baseline TIFF did not decode as RGB16"),
    };
    ensure!(pixels.len()==95_745_120 && !decoder.more_images(),"baseline sample/page count differs");
    let mut h=Sha256::new();let mut bytes=vec![0u8;65536];
    for chunk in pixels.chunks(bytes.len()/2) {
        for (dst,v) in bytes.chunks_exact_mut(2).zip(chunk) {dst.copy_from_slice(&v.to_le_bytes());}
        h.update(&bytes[..2*chunk.len()]);
    }
    let hash=hex(h);ensure!(hash==BASELINE_PIXELS,"held baseline RGB16 differs: {hash}");
    Ok((hash,software))
}
struct OneFrame<'a> {frame:&'a Frame,index:usize}
impl PyramidFrameSource for OneFrame<'_> {
    fn len(&self)->usize {70}
    fn decode(&self,index:usize)->Result<Frame> {
        ensure!(index==self.index,"one-frame source index changed");Ok(self.frame.clone())
    }
}

#[test]
#[ignore="root-owned full70 pair; requires independent screen admission and resource-bounded runner"]
fn vitamin_c_complete_pair()->Result<()> {
    let started=Instant::now();
    let config_path=PathBuf::from(std::env::var_os("STREHL_SHARED_SOURCE_FIELD_FULL_CONFIG")
        .context("STREHL_SHARED_SOURCE_FIELD_FULL_CONFIG required")?);
    let config:Config=serde_json::from_slice(&std::fs::read(&config_path)?)?;
    ensure!(config.schema==1 && config.expected_crop==[28,19,3460,2306]
        && config.max_extra_inset_quads==0 && config.warp_map_sha256==MAP_HASH,
        "held full configuration differs");
    ensure!(config.expected_xyz_to_cam==MATRIX
        && config.tone.map(f32::to_bits)==[0.090420f32,0.914606,0.55].map(f32::to_bits),
        "held matrix/tone differs");
    ensure!(config.source_dir.is_absolute()
        && config.source_dir.file_name().and_then(|v|v.to_str())==Some("crystalized-vitamin-c-cpl"),
        "held source scope differs");
    ensure!(align_cmd::fullres_gather_enabled() && gatefloor::enabled()
        && align_cmd::direct_plane_mode()?==align_cmd::DirectPlaneMode::Rounded,
        "actual fullres rounded gather and injected probe required");
    ensure!(std::env::var_os("STREHL_LOCAL_PLACEMENT_FILE").is_none(),"local placement excluded");
    ensure!(!std::env::var(strehl_core::demosaic::DEMOSAIC_ENV)
        .is_ok_and(|v|v.eq_ignore_ascii_case("directional")),"held MHC required");
    ensure!(strehl_core::pyramid::fine_support_candidate::environment_mode()
        ==strehl_core::pyramid::fine_support_candidate::Mode::Off,"fine support must be off");
    ensure!(file_hash(&config.warp_map)?==MAP_HASH,"held map changed");
    let paths=crate::raw_paths(&config.source_dir,None)?;
    ensure!(paths.len()==70 && paths.iter().enumerate().all(|(i,p)|
        p.file_name().and_then(|v|v.to_str())==Some(format!("DSC{:05}.ARW",i+94).as_str())),
        "complete held seventy-source sequence required");
    let before=paths.iter().map(|p|stamp(p)).collect::<Result<Vec<_>>>()?;
    let original=WarpMap::load(&config.warp_map)?;
    original.check_stack(&StackIdentity::from_paths("crystalized-vitamin-c-cpl",&paths)?)?;
    ensure!(original.resampler()==Resampler::CatmullRom && original.len()==70 && original.placed_count()==70,
        "held map coverage/resampler differs");
    let (map,fit)=align_cmd::cover_or_explain(original,align_cmd::CoverMode::Crop);
    let crop=fit.rect().context("held map lacks common crop")?;
    ensure!([crop.x,crop.y,crop.width,crop.height]==config.expected_crop,"common crop changed");
    let full=map.geometry();
    ensure!(full==PlaneGeometry{width:3516,height:2344},"held geometry differs");
    let identities=paths.iter().map(|p|strehl_raw::identity(p)).collect::<Vec<_>>();
    let profiles=identities.iter().map(|i|strehl_core::optics::profile_for_capture_env(i.model.as_deref(),i.lens_type3))
        .collect::<std::result::Result<Vec<_>,_>>()?;
    ensure!(profiles.iter().all(|p|p.is_some_and(|p|p.key=="a7c2-fe100gm-2xtc-x4cpl")),
        "held source CA profile differs");
    let workspace=PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../..").canonicalize()?;
    ensure!(!config.out_dir.exists(),"output directory already exists");
    let parent=config.out_dir.parent().context("output parent")?.canonicalize()?;
    ensure!(parent.starts_with(workspace.join("experiments").canonicalize()?),"output must be below workspace experiments");
    let first=strehl_raw::decode(&paths[0])?;
    let levels=first.levels;let wb=first.wb_coeffs;
    ensure!(first.camera=="ILCE-7CM2" && first.iso==Some(100.0)
        && levels==Levels{black:512.0,white:15360.0} && first.geometry()==full
        && first.active.width==7032 && first.active.height==4688
        && wb_gains(wb)?.map(f32::to_bits)==WB_BITS && first.xyz_to_cam_rgb()==Some(MATRIX),
        "held first-source metadata differs");
    let active=first.active;let stride=first.stride;let buffer_height=first.buffer_height;
    let check_frame=|frame:&Frame|->Result<()> {
        ensure!(frame.camera=="ILCE-7CM2" && frame.iso==Some(100.0) && frame.levels==levels
            && frame.active==active && frame.stride==stride && frame.buffer_height==buffer_height
            && frame.geometry()==full && wb_gains(frame.wb_coeffs)?.map(f32::to_bits)==WB_BITS
            && frame.xyz_to_cam_rgb()==Some(MATRIX),"held per-source metadata drift");Ok(())
    };
    let cfg=MergeConfig::default();
    ensure!(cfg.bands==7 && cfg.gate==2.0 && cfg.exponent==2.0 && cfg.sharpen_per_octave==1.4
        && cfg.select==SelectMode::SoftPower && cfg.admission==AdmissionMode::HardFloor
        && cfg.base==BaseBand::Mean && cfg.mean_coarse==0 && cfg.hull==Hull::InputRange
        && cfg.fallback==Fallback::Mean && cfg.significance_scale==0.0,"held merge settings differ");
    let plan=chunk_plan(full,first.allocated_bytes(),70,cfg);
    ensure!(plan.canonical_chunks==4 && plan.per_chunk==18,"canonical18,18,18,16 grouping differs");
    let workers=band_workers(plan.planning_bytes,70)?;
    ensure!(workers==8,"parent must bind eight execution threads");
    let pool=ThreadPoolBuilder::new().num_threads(workers).build()?;
    let domain=PyramidDomain::cropped(full,crop)?;
    let sizes=level_sizes(crop.width,crop.height,cfg.bands);
    ensure!(sizes.len()==8,"held seven-band depth differs");
    let n=crop.width.checked_mul(crop.height).context("quad extent overflow")?;
    let volume_bytes=n.checked_mul(70).and_then(|v|v.checked_mul(4)).context("cost volume overflow")?;
    let two_volume_bytes=volume_bytes.checked_mul(2).context("paired volume overflow")?;
    ensure!(n==7_978_760 && two_volume_bytes==4_468_105_600usize,"fixed volume budget differs");
    let noise=profile::noise_model_for(&first.camera,first.iso,levels);
    let matrix=color::camera_to_srgb(MATRIX).context("held matrix singular")?
        .with_saturation(levels,wb_gains(wb)?,1.0);
    let mut dev=image_out::OutputSpace::Srgb.develop(Some(matrix));
    dev.tone=Some(image_out::Tone{black:config.tone[0],white:config.tone[1],contrast:config.tone[2]});
    dev.exposure_gain=1.0;
    std::fs::create_dir(&config.out_dir)?;
    write_json(&config.out_dir.join("started.json"),&json!({"schema":1,"mode":"shared-source-field",
        "source_dir":config.source_dir,"config_sha256":file_hash(&config_path)?,"map_sha256":MAP_HASH,
        "original_crop":config.expected_crop,"effective_crop":config.expected_crop,"plan":plan,
        "canonical_source_chunks":[18,18,18,16],"execution_threads":workers,"wb_bits":WB_BITS,
        "tone_bits":config.tone.map(f32::to_bits),"matrix":MATRIX,"ca_profile":"a7c2-fe100gm-2xtc-x4cpl",
        "merge_config":format!("{cfg:?}"),"native_dimensions":[6920,4612],
        "source_active":[active.x,active.y,active.width,active.height],"source_stride":stride,
        "source_buffer_height":buffer_height,"level_sizes":sizes.iter().map(|s|[s.width,s.height]).collect::<Vec<_>>(),
        "scalar_volume":{"layout":"pixel-major [quad,source], f32","each_bytes":volume_bytes,"pair_bytes":two_volume_bytes},
        "process_limit":"parent runner16GiB /600s","passes":2,"source_image_volume":false,
        "original_metadata_check":"all70 length/modified before and after both passes"}))?;

    let mut costs=CostVolume::new(crop.width,crop.height,70)?;
    let mut base=BandWorker::new(domain,cfg);let mut first=Some(first);let mut total=None;
    let mut evidence=Vec::with_capacity(70);let mut known4=Vec::with_capacity(70);
    let pass1_start=Instant::now();
    pool.install(||->Result<()> {
        let mut chunks=paths.chunks(plan.per_chunk).enumerate().peekable();
        while let Some((chunk_index,chunk))=chunks.next() {
            for (offset,path) in chunk.iter().enumerate() {
                let index=chunk_index*plan.per_chunk+offset;let frame_start=Instant::now();
                let frame=match first.take(){Some(f)=>f,None=>strehl_raw::decode(path)?};
                check_frame(&frame)?;let src_hash=source_hash(&frame);
                ensure!(base.fold(&OneFrame{frame:&frame,index},index,levels,&noise,Some(&map),None)?,"baseline source refused");
                let beta=(!base.beta.is_empty()).then_some(base.beta.as_slice());
                let fields=checked_core(core::finest_evidence(&base.merge,&base.fws,beta))?;
                costs.set_source(index,&fields.energy,&fields.floor)?;
                let hashes=base.planes.iter().map(|p|field_hash(p)).collect::<Vec<_>>();
                known4.push(hashes.clone());
                ensure!(source_hash(&frame)==src_hash,"decoded original changed during pass1");
                ensure!(before[index]==stamp(path)?,"original metadata changed during pass1");
                evidence.push(json!({"index":index,"file":path.file_name().map(|v|v.to_string_lossy()),
                    "source_active_u16_sha256":src_hash,"actual_known4_sha256":hashes,
                    "guide_sha256":field_hash(&base.luma),"variance_sha256":field_hash(&base.var),"beta":base.beta,
                    "finest_energy_sha256":field_hash(&fields.energy),"finest_floor_sha256":field_hash(&fields.floor),
                    "source_bytes":before[index].0,"source_modified_ns":before[index].1.duration_since(SystemTime::UNIX_EPOCH)?.as_nanos().to_string(),
                    "pass1_seconds":frame_start.elapsed().as_secs_f64()}));
                eprintln!("shared-source-field pass1 {}/70, total {:.1}s",index+1,started.elapsed().as_secs_f64());
            }
            absorb_chunk(&mut total,&mut base.merge,crop.width,crop.height,4,cfg);
            if chunks.peek().is_some(){base.reset_chunk();}
        }Ok(())
    })?;
    let pass1_seconds=pass1_start.elapsed().as_secs_f64();
    drop(base);let total=total.context("empty complete baseline")?;
    eprintln!("shared-source-field baseline finish/write, total {:.1}s",started.elapsed().as_secs_f64());
    let baseline_write_start=Instant::now();
    let baseline_averaged_fraction=total.averaged_fraction();
    let baseline=pool.install(||total.finish(&mut Workspace::new(&sizes)));
    let baseline_plane_hashes=baseline.iter().map(|p|field_hash(p)).collect::<Vec<_>>();
    let guide=baseline[1].iter().zip(&baseline[2]).map(|(g1,g2)|0.5*(g1+g2)).collect::<Vec<_>>();
    let guide_hash=field_hash(&guide);let baseline_path=config.out_dir.join("baseline.tiff");
    pool.install(||write_planes(&baseline_path,&baseline,crop,levels,wb,&dev))?;
    drop(baseline);
    let baseline_sha256=file_hash(&baseline_path)?;
    let (baseline_rgb16_sha256,baseline_software)=check_written_baseline(&baseline_path)?;
    let baseline_write_seconds=baseline_write_start.elapsed().as_secs_f64();
    write_json(&config.out_dir.join("baseline-ready.json"),&json!({"baseline_sha256":baseline_sha256,
        "baseline_rgb16_le_sha256":baseline_rgb16_sha256,"baseline_software":baseline_software,
        "reference_baseline_file_sha256":BASELINE_FILE,"baseline_planes_sha256":baseline_plane_hashes,
        "common_guide_sha256":guide_hash,"baseline_averaged_fraction":baseline_averaged_fraction,
        "frame_evidence":evidence,"pass1_seconds":pass1_seconds,"baseline_finish_write_seconds":baseline_write_seconds,
        "seconds":started.elapsed().as_secs_f64()}))?;

    // Exact baseline guard passes before spatial source aggregation or candidate replay.
    eprintln!("shared-source-field forming fixed categorical field, total {:.1}s",started.elapsed().as_secs_f64());
    let field_start=Instant::now();let raw=costs.normalize()?;
    let raw_hash=field_hash(&raw.costs);let rmax_hash=field_hash(&raw.rmax);let spread_hash=field_hash(&raw.spread);
    let normalize_hash_seconds=field_start.elapsed().as_secs_f64();
    eprintln!("shared-source-field four-path aggregation starts, total {:.1}s",started.elapsed().as_secs_f64());
    let aggregate_start=Instant::now();
    let aggregate=pool.install(||aggregate_costs(&raw,&guide))?;
    let aggregate_hash=field_hash(&aggregate);drop(guide);
    let aggregate_hash_seconds=aggregate_start.elapsed().as_secs_f64();
    eprintln!("shared-source-field four-path aggregation complete in {:.1}s; memberships next",aggregate_hash_seconds);
    let membership_start=Instant::now();
    let member=memberships(aggregate,&raw)?;drop(raw);
    let member_hash=field_hash(&member.pixel_major_q);let alpha_hash=field_hash(&member.alpha);
    let member_evidence=member.evidence();let field_seconds=field_start.elapsed().as_secs_f64();
    let membership_hash_seconds=membership_start.elapsed().as_secs_f64();
    let alpha_path=config.out_dir.join("activation.f32");write_field(&alpha_path,&member.alpha)?;
    write_json(&config.out_dir.join("field-ready.json"),&json!({
        "raw_costs_sha256":raw_hash,"rmax_sha256":rmax_hash,"raw_spread_sha256":spread_hash,
        "aggregate_costs_sha256":aggregate_hash,"membership_sha256":member_hash,"alpha_sha256":alpha_hash,
        "field_evidence":member_evidence,"seconds":field_seconds,
        "activation_map":{"path":alpha_path,"sha256":file_hash(&alpha_path)?,"dtype":"f32le",
            "shape_yx":[crop.height,crop.width],"interpretation":"evidence activation, not depth confidence"}}))?;
    let mut replay=checked_core(core::Replay::new(&sizes,&member.alpha))?;
    let pass2_start=Instant::now();
    pool.install(||->Result<()> {
        for (index,path) in paths.iter().enumerate() {
            let frame_start=Instant::now();let frame=strehl_raw::decode(path)?;check_frame(&frame)?;
            let src_hash=source_hash(&frame);
            ensure!(Some(src_hash.as_str())==evidence[index]["source_active_u16_sha256"].as_str(),
                "independent second decode differs at source {index}");
            let planes=gather_direct(&frame,map.placement(index)?,crop)?;
            let hashes=planes.iter().map(|p|field_hash(p)).collect::<Vec<_>>();
            ensure!(hashes==known4[index],"actual pass2 gather differs from pass1 at source {index}");
            let q=member.source(index);let q_hash=field_hash(&q);
            checked_core(replay.add_source(&q,&planes))?;
            ensure!(planes.iter().map(|p|field_hash(p)).collect::<Vec<_>>()==hashes,
                "replay mutated actual gathered source {index}");
            ensure!(source_hash(&frame)==src_hash,"replay mutated decoded source {index}");
            ensure!(before[index]==stamp(path)?,"original metadata changed during pass2");
            evidence[index]["replay"]=json!({"source_active_u16":"BIT_EXACT_SECOND_DECODE",
                "actual_known4":"BIT_EXACT_PASS1","known4_sha256":hashes,"membership_sha256":q_hash,
                "positive_quads":q.iter().filter(|&&v|v>0.0).count(),"seconds":frame_start.elapsed().as_secs_f64()});
            eprintln!("shared-source-field pass2 {}/70, total {:.1}s",index+1,started.elapsed().as_secs_f64());
        }Ok(())
    })?;
    let pass2_seconds=pass2_start.elapsed().as_secs_f64();
    let coverage_hash=field_hash(replay.coverage());
    let coverage_error=replay.coverage().iter().zip(&member.alpha).map(|(a,b)|(a-b).abs()).fold(0.0f32,f32::max);
    drop(member);
    eprintln!("shared-source-field final candidate reconstruction/write, total {:.1}s",started.elapsed().as_secs_f64());
    let final_write_start=Instant::now();
    let candidate=pool.install(||checked_core(replay.finish(&total,&mut Workspace::new(&sizes))))?;
    let candidate_plane_hashes=candidate.iter().map(|p|field_hash(p)).collect::<Vec<_>>();
    let candidate_path=config.out_dir.join("candidate.tiff");
    pool.install(||write_planes(&candidate_path,&candidate,crop,levels,wb,&dev))?;
    drop(candidate);drop(replay);drop(total);
    let candidate_sha256=file_hash(&candidate_path)?;
    let final_write_seconds=final_write_start.elapsed().as_secs_f64();
    eprintln!("shared-source-field candidate written in {:.1}s, total {:.1}s",final_write_seconds,started.elapsed().as_secs_f64());
    for (index,path) in paths.iter().enumerate(){ensure!(before[index]==stamp(path)?,"original metadata changed after pair");}
    ensure!(file_hash(&config.warp_map)?==MAP_HASH,"held map changed after pair");
    write_json(&config.out_dir.join("receipt.json"),&json!({"schema":1,"mode":"shared-source-field","frames":70,
        "baseline_sha256":baseline_sha256,"candidate_sha256":candidate_sha256,
        "baseline_rgb16_le_sha256":baseline_rgb16_sha256,"baseline_software":baseline_software,
        "reference_baseline_file_sha256":BASELINE_FILE,"baseline_planes_sha256":baseline_plane_hashes,
        "candidate_planes_sha256":candidate_plane_hashes,"baseline_averaged_fraction":baseline_averaged_fraction,
        "common_guide_sha256":guide_hash,"raw_costs_sha256":raw_hash,"aggregate_costs_sha256":aggregate_hash,
        "membership_sha256":member_hash,"alpha_sha256":alpha_hash,"coverage_sha256":coverage_hash,
        "coverage_max_abs_error":coverage_error,"field_evidence":member_evidence,
        "field_receipt_sha256":file_hash(&config.out_dir.join("field-ready.json"))?,
        "terminal_base":"unchanged baseline mean","input_range":"unchanged baseline hull",
        "known4_replay":"all70 sources bit-exact actual pass1/pass2",
        "plan":plan,"frame_evidence":evidence,"native_dimensions":[6920,4612],"effective_crop":config.expected_crop,
        "original_metadata_unchanged":true,"source_image_volume":false,"scalar_volume_bytes":volume_bytes,
        "phase_seconds":{"baseline_and_evidence":pass1_seconds,"baseline_finish_write":baseline_write_seconds,
            "field":field_seconds,"normalize_and_hash":normalize_hash_seconds,"aggregate_and_hash":aggregate_hash_seconds,
            "memberships_evidence_and_hash":membership_hash_seconds,"replay":pass2_seconds,
            "candidate_finish_write_hash":final_write_seconds},
        "seconds":started.elapsed().as_secs_f64(),"photographic_promotion":false}))?;
    Ok(())
}
