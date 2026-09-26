// Complete held-current chip observation; root execution, no production default.
use super::*;
use serde::{Deserialize,Serialize};
use serde_json::json;
use sha2::{Digest,Sha256};
use std::{fs::File,io::{Read,Write},time::SystemTime};
use phase_packed_rgb::full_stack::{absorb_chunk,chunk_plan,full_source_supported};
use shared_source_field::{checked_core,gather_direct};
use full_stack_source_prior::CacheMetadata;
use crate::image_out::highlight_rendering::{self as rendering,Arm};
use strehl_core::pyramid::{chip_shared_source_observation_diagnostic as core,Hull,Fallback};

#[derive(Deserialize,Serialize)]
#[serde(deny_unknown_fields)]
struct Input {index:usize,path:PathBuf,identity_name:String,bytes:u64,sha256:String}
#[derive(Deserialize,Serialize)]
#[serde(deny_unknown_fields)]
struct Config {
    schema:u32,phase:String,mode:String,stack_name:String,inputs:Vec<Input>,warp_map:PathBuf,
    warp_map_sha256:String,out_dir:PathBuf,expected_reference:usize,expected_full_geometry:[usize;2],
    expected_crop:[usize;4],expected_baseline:PathBuf,expected_baseline_sha256:String,
    expected_baseline_pixels_sha256:String,expected_camera:String,expected_iso:f32,
    exposure_stops:f32,tone_policy:String,
}
fn digest(h:Sha256)->String{h.finalize().iter().map(|v|format!("{v:02x}")).collect()}
fn file_hash(path:&Path)->Result<String>{let mut f=File::open(path)?;let mut h=Sha256::new();let mut b=vec![0u8;1<<20];
    loop{let n=f.read(&mut b)?;if n==0{break;}h.update(&b[..n]);}Ok(digest(h))}
fn save(path:&Path,v:&serde_json::Value)->Result<()>{let mut f=std::fs::OpenOptions::new().write(true).create_new(true).open(path)?;
    serde_json::to_writer_pretty(&mut f,v)?;writeln!(f)?;Ok(())}
fn stamp(path:&Path)->Result<(u64,SystemTime)>{let m=std::fs::metadata(path)?;Ok((m.len(),m.modified()?))}
fn source_hash(f:&Frame)->String{let mut h=Sha256::new();let mut row=vec![0u8;2*f.active.width];
    for y in 0..f.active.height{for(dst,v)in row.chunks_exact_mut(2).zip(f.active_row(y)){dst.copy_from_slice(&v.to_le_bytes());}h.update(&row);}digest(h)}
fn field_hash(v:&[f32])->String{let mut h=Sha256::new();let mut b=vec![0u8;65536];for row in v.chunks(b.len()/4){
    for(dst,v)in b.chunks_exact_mut(4).zip(row){dst.copy_from_slice(&v.to_bits().to_le_bytes());}h.update(&b[..row.len()*4]);}digest(h)}
fn hashes(v:&[Vec<f32>])->Vec<String>{v.iter().map(|p|field_hash(p)).collect()}
fn same(a:&[f32],b:&[f32])->bool{a.len()==b.len()&&a.iter().zip(b).all(|(a,b)|a.to_bits()==b.to_bits())}
fn rgb_hash(path:&Path,native:[usize;2])->Result<String>{let mut d=tiff::decoder::Decoder::new(std::io::BufReader::new(File::open(path)?))?;
    ensure!(d.dimensions()?==(native[0] as u32,native[1] as u32)&&d.colortype()?==tiff::ColorType::RGB(16),"delivered dimensions/type differ");
    let v=match d.read_image()?{tiff::decoder::DecodingResult::U16(v)=>v,_=>bail!("delivered storage is not u16")};
    ensure!(v.len()==native[0]*native[1]*3&&!d.more_images(),"delivered shape/pages differ");
    let mut h=Sha256::new();let mut b=vec![0u8;65536];for row in v.chunks(b.len()/2){for(dst,v)in b.chunks_exact_mut(2).zip(row){dst.copy_from_slice(&v.to_le_bytes());}h.update(&b[..2*row.len()]);}Ok(digest(h))}

fn write_cache(dir:&Path,arm:&str,planes:&[Vec<f32>],template:&CacheMetadata)->Result<serde_json::Value>{
    ensure!(planes.len()==4&&planes.iter().all(|p|p.len()==template.crop[2]*template.crop[3]
        &&p.iter().all(|v|v.is_finite())),"invalid cache planes");
    let path=dir.join(format!("{arm}-planes.f32"));let mut f=std::io::BufWriter::new(std::fs::OpenOptions::new().write(true).create_new(true).open(&path)?);
    let mut buf=vec![0u8;65536];for plane in planes{for row in plane.chunks(buf.len()/4){for(dst,v)in buf.chunks_exact_mut(4).zip(row){dst.copy_from_slice(&v.to_bits().to_le_bytes());}f.write_all(&buf[..row.len()*4])?;}}f.flush()?;drop(f);
    let mut metadata=template.clone();metadata.arm=arm.into();metadata.binary=path.file_name().unwrap().to_string_lossy().into_owned();
    metadata.binary_bytes=std::fs::metadata(&path)?.len();metadata.binary_sha256=file_hash(&path)?;metadata.plane_sha256=hashes(planes);
    let json_path=dir.join(format!("{arm}-cache.json"));save(&json_path,&serde_json::to_value(&metadata)?)?;
    Ok(json!({"path":json_path,"sha256":file_hash(&json_path)?,"binary_sha256":metadata.binary_sha256}))
}
pub(crate) fn write_current(path:&Path,planes:&[Vec<f32>],m:&CacheMetadata)->Result<()>{
    write_merged(Merged::Bands{domain:m.domain()?,planes},m.levels(),m.wb(),m.xyz().as_ref(),
        image_out::OutputSpace::Srgb,true,m.exposure()?,None,path)
}
struct OneFrame<'a>{frame:&'a Frame,index:usize,count:usize}
impl PyramidFrameSource for OneFrame<'_>{fn len(&self)->usize{self.count}fn decode(&self,i:usize)->Result<Frame>{ensure!(i==self.index,"source index changed");Ok(self.frame.clone())}}
#[derive(Serialize)]
struct Evidence {
    index:usize,active_u16_sha256:String,known4_sha256:Vec<String>,guide_sha256:String,
    variance_sha256:String,beta:Vec<f32>,finest_energy_sha256:String,finest_floor_sha256:String,
    membership_sha256:Option<String>,replay_exact:bool,source_unchanged:bool,
    pass1_seconds:f64,pass2_seconds:f64,
}

#[test]
#[ignore="root-owned full299 chip observation; explicit bound config required"]
fn complete_pair()->Result<()> {
    let started=Instant::now();let path=PathBuf::from(std::env::var_os("STREHL_CHIP_SHARED_SOURCE_CONFIG").context("full-stack config required")?);
    let config:Config=serde_json::from_slice(&std::fs::read(&path)?)?;
    ensure!(config.schema==1&&config.phase=="full"&&config.mode=="shared-source-field"
        &&config.tone_policy=="automatic-baseline-then-exact-pinned-candidate"&&config.expected_full_geometry==[3516,2344],"held full-stack contract differs");
    let count=config.inputs.len();ensure!(count==299&&config.expected_reference==149
        &&config.stack_name=="uncapped-IC-chip-cpl"&&config.expected_crop==[133,89,3250,2166]
        &&config.exposure_stops.to_bits()==0.0f32.to_bits(),"fixed complete current chip contract differs");
    ensure!(config.inputs.iter().enumerate().all(|(i,v)|v.index==i&&v.path.is_absolute()&&v.bytes>0&&v.sha256.len()==64
        &&Path::new(&v.identity_name).components().count()==1&&Path::new(&v.identity_name).file_name().is_some()),"ordered source identity invalid");
    ensure!(std::env::var("STREHL_CA_BEFORE_MHC").ok().as_deref()==Some("off")
        &&strehl_core::pyramid::fine_support_candidate::environment_mode()==strehl_core::pyramid::fine_support_candidate::Mode::Off,
        "competing experiments must be off; original optical CA remains on");
    ensure!(align_cmd::fullres_gather_enabled()&&gatefloor::enabled()&&align_cmd::direct_plane_mode()?==align_cmd::DirectPlaneMode::Rounded
        &&align_cmd::native_gpu_integration::gpu_gather_enabled()?,"actual rounded GPU/probe path required");
    ensure!(std::env::var_os("STREHL_LOCAL_PLACEMENT_FILE").is_none()&&std::env::var_os("STREHL_ONLY_FRAME").is_none()
        &&std::env::var_os(strehl_core::highlight::KNEE_ENV).is_none()&&matched_source_tests::pinned_tone().is_none()
        &&!std::env::var(strehl_core::demosaic::DEMOSAIC_ENV).is_ok_and(|v|v.eq_ignore_ascii_case("directional")),"held geometry/Malvar required");
    let root=PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../..").canonicalize()?;
    ensure!(config.out_dir.is_absolute()&&!config.out_dir.exists()
        &&config.out_dir.parent().context("output parent")?.canonicalize()?.starts_with(root.join("experiments").canonicalize()?),"fresh workspace output required");
    let paths=config.inputs.iter().map(|v|v.path.clone()).collect::<Vec<_>>();
    let mut unique=std::collections::BTreeSet::new();ensure!(paths.iter().all(|p|unique.insert(p.clone())),"duplicate original paths");
    let before=paths.iter().map(|p|stamp(p)).collect::<Result<Vec<_>>>()?;
    for(i,input)in config.inputs.iter().enumerate(){ensure!(before[i].0==input.bytes&&file_hash(&input.path)?==input.sha256,"original hash/length differs at {i}");}
    ensure!(file_hash(&config.warp_map)?==config.warp_map_sha256,"map hash differs");
    let original=WarpMap::load(&config.warp_map)?;
    let entries=config.inputs.iter().map(|v|(v.identity_name.as_str(),v.bytes)).collect::<Vec<_>>();
    original.check_stack(&StackIdentity::from_entries(&config.stack_name,&entries))?;
    ensure!(original.resampler()==Resampler::CatmullRom&&original.len()==count&&original.placed_count()==count
        &&original.provenance().reference==config.expected_reference,"held placements differ");
    let(map,fit)=align_cmd::cover_or_explain(original,align_cmd::CoverMode::Crop);let crop=fit.rect().context("map crop")?;
    ensure!([crop.x,crop.y,crop.width,crop.height]==config.expected_crop,"actual product crop differs");
    let full=map.geometry();ensure!(full==PlaneGeometry{width:3516,height:2344},"full geometry changed");
    let native=[crop.width*2,crop.height*2];
    ensure!(file_hash(&config.expected_baseline)?==config.expected_baseline_sha256
        &&rgb_hash(&config.expected_baseline,native)?==config.expected_baseline_pixels_sha256,"expected user baseline binding differs");
    let identities=paths.iter().map(|p|strehl_raw::identity(p)).collect::<Vec<_>>();
    let profiles=identities.iter().map(|id|strehl_core::optics::profile_for_capture_env(id.model.as_deref(),id.lens_type3)).collect::<std::result::Result<Vec<_>,_>>()?;
    let mut support=Vec::with_capacity(count);for(i,ca)in profiles.iter().enumerate(){
        ensure!(ca.is_some_and(|p|p.key=="a7c2-fe100gm-2xtc-x4cpl"),"held optical CA absent at {i}");
        support.push(full_source_supported(map.placement(i)?,full,crop,*ca));}
    // This diagnostic checks all twelve colour/site combinations. It must not
    // silently shrink the product's actual four-plane crop or boundary policy.
    ensure!(support.iter().all(|v|*v),"held crop has an unsupported colour/site pull");
    let indices=(0..count).collect::<Vec<_>>();
    let decode_clock=Instant::now();let first=strehl_raw::decode(&paths[indices[0]])?;let first_decode_seconds=decode_clock.elapsed().as_secs_f64();
    ensure!(first.camera==config.expected_camera&&first.iso==Some(config.expected_iso)&&first.geometry()==full
        &&first.active.width==7032&&first.active.height==4688,"held first metadata differs");
    let levels=first.levels;let wb=first.wb_gains().context("WB")?;let xyz=first.xyz_to_cam_rgb_with_source().context("camera matrix")?;
    ensure!(levels.range()>0.0&&wb.iter().all(|v|v.is_finite()&&*v>0.0)&&xyz.0.iter().flatten().all(|v|v.is_finite()),"invalid first calibration metadata");
    let(active,stride,height)=(first.active,first.stride,first.buffer_height);
    let cfg=MergeConfig::default();ensure!(cfg.bands==7&&cfg.gate==2.0&&cfg.exponent==2.0
        &&cfg.sharpen_per_octave==1.4&&cfg.select==SelectMode::SoftPower
        &&cfg.admission==AdmissionMode::HardFloor&&cfg.base==BaseBand::Mean
        &&cfg.fallback==Fallback::Mean&&cfg.hull==Hull::InputRange
        &&cfg.mean_coarse==0&&cfg.significance_scale==0.0,"held production merge changed");
    let plan=chunk_plan(full,first.allocated_bytes(),count,cfg);
    let threads=band_workers(plan.planning_bytes,count)?;ensure!(threads==8,"eight execution threads required");
    let pool=ThreadPoolBuilder::new().num_threads(threads).build()?;
    let sizes=level_sizes(crop.width,crop.height,cfg.bands);let domain=PyramidDomain::cropped(full,crop)?;
    let noise=profile::noise_model_for(&first.camera,first.iso,levels);ensure!(noise.is_trustworthy(),"injected profile untrusted");
    let input_order_bytes=serde_json::to_vec(&config.inputs)?;let mut input_hash=Sha256::new();input_hash.update(&input_order_bytes);
    let cache_template=CacheMetadata{schema:1,full_geometry:[full.width,full.height],crop:config.expected_crop,
        levels_bits:[levels.black.to_bits(),levels.white.to_bits()],wb_gains_bits:Some(wb.map(f32::to_bits)),
        xyz_to_cam_bits:Some(xyz.0.map(|r|r.map(f32::to_bits))),xyz_source:Some(xyz.1.clone()),
        exposure_stops_bits:Some(config.exposure_stops.to_bits()),tone_policy:config.tone_policy.clone(),
        frames:count,reference:config.expected_reference,map_sha256:config.warp_map_sha256.clone(),input_order_sha256:digest(input_hash),
        plane_order:["R","G1","G2","B"].map(String::from),binary:String::new(),binary_bytes:0,binary_sha256:String::new(),
        plane_sha256:vec![],arm:String::new(),phase:config.phase.clone()};cache_template.exposure()?;
    let scalar_pair_bytes=scalar_volume_pair_bytes(crop.width,crop.height,count)?;
    ensure!(scalar_pair_bytes==16_838_484_000usize,"fixed scalar pair byte count differs");
    std::fs::create_dir(&config.out_dir)?;
    save(&config.out_dir.join("started.json"),&json!({"schema":1,"phase":config.phase,"mode":config.mode,"map_sha256":config.warp_map_sha256,
        "crop":config.expected_crop,"plan":plan,"threads":threads,"indices":indices,"source_count":indices.len(),"probe_source_count":count,
        "all_colour_site_support_checks":support,"generated_photographic_replay_admitted":false,
        "scope":"unchanged shared-source field; old generated rejection retained; separate full-chip observation",
        "scalar_pair_bytes":scalar_pair_bytes,"process_limit":"32GiB/1800wall seconds","source_image_volume":false,"cache_metadata":cache_template,"ca_stage":"off","optical_ca":"a7c2-fe100gm-2xtc-x4cpl","observer":false}))?;
    let metadata=|f:&Frame|->Result<()>{ensure!(f.camera==config.expected_camera&&f.iso==Some(config.expected_iso)&&f.levels==levels
        &&f.active==active&&f.stride==stride&&f.buffer_height==height&&f.wb_gains().context("WB")?.map(f32::to_bits)==wb.map(f32::to_bits)
        &&f.xyz_to_cam_rgb()==Some(xyz.0),"source metadata drift");Ok(())};
    let source_clock=Instant::now();
    let mut costs=CostVolume::new(crop.width,crop.height,count)?;
    let mut base=BandWorker::new(domain,cfg);let mut base_total=None;
    let mut evidence=Vec::with_capacity(count);let mut initial=Some(first);
    pool.install(||->Result<()> {for(position,&i)in indices.iter().enumerate(){
        let timer=Instant::now();let frame=match initial.take(){Some(f)=>f,None=>strehl_raw::decode(&paths[i])?};metadata(&frame)?;
        let active_u16_sha256=source_hash(&frame);let source=OneFrame{frame:&frame,index:i,count};
        ensure!(base.fold(&source,i,levels,&noise,Some(&map),None)?,"baseline source{i} refused");
        let fields=checked_core(core::finest_evidence(&base.merge,&base.fws,(!base.beta.is_empty()).then_some(base.beta.as_slice())))?;
        costs.set_source(i,&fields.energy,&fields.floor)?;
        ensure!(source_hash(&frame)==active_u16_sha256&&stamp(&paths[i])?==before[i],"original changed in pass1");
        evidence.push(Evidence{index:i,active_u16_sha256,known4_sha256:hashes(&base.planes),
            guide_sha256:field_hash(&base.luma),variance_sha256:field_hash(&base.var),beta:base.beta.clone(),
            finest_energy_sha256:field_hash(&fields.energy),finest_floor_sha256:field_hash(&fields.floor),
            membership_sha256:None,replay_exact:false,source_unchanged:true,
            pass1_seconds:timer.elapsed().as_secs_f64(),pass2_seconds:0.});
        let last=position+1==indices.len();if last||(i+1)%plan.per_chunk==0{
            absorb_chunk(&mut base_total,&mut base.merge,crop.width,crop.height,4,cfg);if !last{base.reset_chunk();}}
        eprintln!("chip shared-source pass1 {}/{} source{} {:.3}s",position+1,count,i,timer.elapsed().as_secs_f64());
    }Ok(())})?;
    let pass1_seconds=source_clock.elapsed().as_secs_f64();drop(base);
    let base_total=base_total.context("no baseline")?;let baseline_averaged_fraction=base_total.averaged_fraction();
    let finish_clock=Instant::now();let baseline=pool.install(||base_total.finish(&mut Workspace::new(&sizes)));
    let guide=baseline[1].iter().zip(&baseline[2]).map(|(a,b)|0.5*(a+b)).collect::<Vec<_>>();
    let common_guide_sha256=field_hash(&guide);let baseline_planes_sha256=hashes(&baseline);
    let base_path=config.out_dir.join("baseline.tiff");let baseline_cache=write_cache(&config.out_dir,"baseline",&baseline,&cache_template)?;
    let (_,resolved)=pool.install(||rendering::with_arm(Arm::Current,||write_current(&base_path,&baseline,&cache_template)))?;
    let locked_path=config.out_dir.join("baseline-pinned-rewrite.tiff");
    pool.install(||pinned_write(&locked_path,&baseline,&cache_template,&resolved))?;
    ensure!(rgb_hash(&locked_path,native)?==rgb_hash(&base_path,native)?&&icc(&locked_path)?==icc(&base_path)?,"pinned baseline rewrite differs");
    drop(baseline);let base_rgb=rgb_hash(&base_path,native)?;
    ensure!(base_rgb==config.expected_baseline_pixels_sha256&&icc(&base_path)?==icc(&config.expected_baseline)?,"complete current baseline RGB16/ICC differs");
    let baseline_sha256=file_hash(&base_path)?;
    save(&config.out_dir.join("baseline-ready.json"),&json!({"image_sha256":baseline_sha256,
        "rgb16_le_sha256":base_rgb,"current_pixels_required":true,"frames":evidence}))?;
    let baseline_finish_seconds=finish_clock.elapsed().as_secs_f64();
    eprintln!("chip shared-source normalization and four-path aggregation begins; {} scalar bytes",scalar_pair_bytes);
    let field_clock=Instant::now();let raw=costs.normalize()?;
    let raw_costs_sha256=field_hash(&raw.costs);let rmax_sha256=field_hash(&raw.rmax);let spread_sha256=field_hash(&raw.spread);
    let normalize_seconds=field_clock.elapsed().as_secs_f64();let aggregate_clock=Instant::now();
    let aggregate=pool.install(||aggregate_costs(&raw,&guide))?;drop(guide);
    let aggregate_sha256=field_hash(&aggregate);let aggregate_seconds=aggregate_clock.elapsed().as_secs_f64();
    eprintln!("chip shared-source four paths complete {:.3}s; memberships next",aggregate_seconds);
    let member_clock=Instant::now();let member=memberships(aggregate,&raw)?;drop(raw);
    let membership_sha256=field_hash(&member.pixel_major_q);let alpha_sha256=field_hash(&member.alpha);
    let field_evidence=member.evidence();let membership_seconds=member_clock.elapsed().as_secs_f64();
    let alpha_path=config.out_dir.join("activation.f32");write_field(&alpha_path,&member.alpha)?;
    save(&config.out_dir.join("field-ready.json"),&json!({"raw_costs_sha256":raw_costs_sha256,"rmax_sha256":rmax_sha256,
        "spread_sha256":spread_sha256,"aggregate_sha256":aggregate_sha256,"membership_sha256":membership_sha256,
        "alpha_sha256":alpha_sha256,"field_evidence":field_evidence,"scalar_pair_bytes":scalar_pair_bytes,
        "activation":{"path":alpha_path,"sha256":file_hash(&alpha_path)?,"shape_yx":[crop.height,crop.width],"dtype":"f32le"},
        "normalize_seconds":normalize_seconds,"aggregate_seconds":aggregate_seconds,"membership_seconds":membership_seconds}))?;
    let mut replay=checked_core(core::Replay::new(&sizes,&member.alpha))?;let second_clock=Instant::now();
    pool.install(||->Result<()> {for(i,path)in paths.iter().enumerate(){
        let timer=Instant::now();let frame=strehl_raw::decode(path)?;metadata(&frame)?;
        let ev=&mut evidence[i];ensure!(ev.index==i&&source_hash(&frame)==ev.active_u16_sha256,"independent second decode differs");
        let planes=gather_direct(&frame,map.placement(i)?,crop)?;
        ensure!(hashes(&planes)==ev.known4_sha256,"actual gathered source differs between passes");
        let q=member.source(i);ev.membership_sha256=Some(field_hash(&q));checked_core(replay.add_source(&q,&planes))?;
        ensure!(hashes(&planes)==ev.known4_sha256&&source_hash(&frame)==ev.active_u16_sha256&&stamp(path)?==before[i],"replay changed gathered/original source");
        ev.replay_exact=true;ev.pass2_seconds=timer.elapsed().as_secs_f64();
        eprintln!("chip shared-source pass2 {}/{} {:.3}s",i+1,count,ev.pass2_seconds);
    }Ok(())})?;
    let pass2_seconds=second_clock.elapsed().as_secs_f64();
    let coverage_sha256=field_hash(replay.coverage());
    let coverage_max_abs_error=replay.coverage().iter().zip(&member.alpha).map(|(q,a)|(q-a).abs()).fold(0.0f32,f32::max);
    ensure!(coverage_max_abs_error<=8e-6,"coverage changed from the original replay bar");drop(member);
    let finish_clock=Instant::now();let output=pool.install(||checked_core(replay.finish(&base_total,&mut Workspace::new(&sizes))))?;
    let candidate_planes_sha256=hashes(&output);let candidate_cache=write_cache(&config.out_dir,"candidate",&output,&cache_template)?;
    let candidate_path=config.out_dir.join("candidate.tiff");pool.install(||pinned_write(&candidate_path,&output,&cache_template,&resolved))?;
    drop(output);drop(replay);drop(base_total);
    let candidate_rgb=rgb_hash(&candidate_path,native)?;ensure!(icc(&candidate_path)?==icc(&base_path)?,"candidate ICC changed");
    let candidate_sha256=file_hash(&candidate_path)?;let finish_seconds=baseline_finish_seconds+finish_clock.elapsed().as_secs_f64();
    ensure!(paths.iter().map(|p|stamp(p)).collect::<Result<Vec<_>>>()?==before&&file_hash(&config.warp_map)?==config.warp_map_sha256,"input bindings changed");
    let mut receipt=json!({"schema":1,"phase":config.phase,"mode":config.mode,"frames":evidence,"source_count":count,
        "probe_source_count":count,"map_sha256":config.warp_map_sha256,"crop":config.expected_crop,"native_dimensions":native,
        "plan":plan,"threads":threads,"tone_policy":config.tone_policy,"cache_metadata":cache_template,
        "pass1_seconds":pass1_seconds,"pass2_seconds":pass2_seconds,"normalize_seconds":normalize_seconds,
        "aggregate_seconds":aggregate_seconds,"membership_seconds":membership_seconds,"finish_seconds":finish_seconds,
        "total_seconds":started.elapsed().as_secs_f64(),"first_decode_seconds":first_decode_seconds,
        "baseline_averaged_fraction":baseline_averaged_fraction,"replay_exact":true,"source_image_volume":false,
        "terminal_base":"unchanged baseline mean","input_hull":"unchanged baseline hull","scalar_pair_bytes":scalar_pair_bytes});
    let output_receipt=json!({"common_guide_sha256":common_guide_sha256,"raw_costs_sha256":raw_costs_sha256,
        "aggregate_sha256":aggregate_sha256,"membership_sha256":membership_sha256,"alpha_sha256":alpha_sha256,
        "coverage_sha256":coverage_sha256,"coverage_max_abs_error":coverage_max_abs_error,"field_evidence":field_evidence,
        "generated_photographic_replay_admitted":false,"resolved_development":resolved,"actual_tone_pinned":true,
        "baseline_pinned_rewrite_exact":true,"baseline_planes_sha256":baseline_planes_sha256,"candidate_planes_sha256":candidate_planes_sha256,
        "baseline_rgb16_le_sha256":base_rgb,"candidate_rgb16_le_sha256":candidate_rgb,"baseline_sha256":baseline_sha256,
        "candidate_sha256":candidate_sha256,"baseline_cache":baseline_cache,"candidate_cache":candidate_cache,
        "all_colour_site_support_checks":support,"original_metadata_unchanged":true});
    receipt.as_object_mut().context("receipt not object")?.extend(output_receipt.as_object().context("output receipt not object")?.clone());
    save(&config.out_dir.join("receipt.json"),&receipt)?;Ok(())
}

fn write_field(path:&Path,values:&[f32])->Result<()> {
    let mut file=std::io::BufWriter::new(std::fs::OpenOptions::new().write(true).create_new(true).open(path)?);
    let mut bytes=vec![0u8;65536];for chunk in values.chunks(bytes.len()/4){
        for(dst,v)in bytes.chunks_exact_mut(4).zip(chunk){dst.copy_from_slice(&v.to_bits().to_le_bytes());}
        file.write_all(&bytes[..chunk.len()*4])?;
    }file.flush()?;Ok(())
}

// Held formula copied from marigold-source-pure::pinned_write.
fn pinned_write(path:&Path,planes:&[Vec<f32>],m:&CacheMetadata,
    resolved:&rendering::Resolved)->Result<()> {
    let domain=m.domain()?;let(w,h)=(domain.rect.width,domain.rect.height);let levels=m.levels();
    let gains=m.wb().context("WB absent")?;let xyz=m.xyz().context("matrix absent")?;
    let applied=match m.exposure()? {Exposure::None=>AppliedExposure::IDENTITY,
        Exposure::Stops(stops)=>AppliedExposure{stops,automatic:false},Exposure::Auto=>bail!("automatic exposure not admitted")};
    let eg=applied.gain();ensure!(eg.to_bits()==resolved.exposure_gain_bits,"exposure changed");
    let matrix=color::camera_to_srgb(xyz.0).context("invalid camera matrix")?;
    let mut dev=image_out::OutputSpace::Srgb.develop(Some(matrix.with_saturation(levels,gains,eg))).with_exposure_gain(eg);
    let t=resolved.tone_bits.context("actual tone absent")?;
    dev.tone=Some(image_out::Tone{black:f32::from_bits(t[0]),white:f32::from_bits(t[1]),contrast:f32::from_bits(t[2])});
    let mut mosaic=vec![0.0f32;w*h*4];
    for p in 0..4 {let gain=gains[if p==0{0}else if p==3{2}else{1}];
        for y in 0..h {for x in 0..w {let v=planes[p][y*w+x].max(0.0);
            mosaic[(2*y+p/2)*(2*w)+2*x+p%2]=v*gain*eg/levels.range();}}}
    let(_,observed)=rendering::with_arm(Arm::Current,||image_out::write_demosaiced(path,2*w,2*h,&mosaic,&dev))?;
    ensure!(&observed==resolved,"pinned development metadata changed");Ok(())
}
fn icc(path:&Path)->Result<Vec<u8>> {
    let mut d=tiff::decoder::Decoder::new(std::io::BufReader::new(File::open(path)?))?;
    let v=d.get_tag_u8_vec(tiff::tags::Tag::IccProfile)?;
    ensure!(!v.is_empty(),"ICC absent");Ok(v)
}
