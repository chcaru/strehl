// Separate observational full-chip adapter. The failed generated rule is unchanged.
use super::*;
use serde::{Deserialize,Serialize};
use serde_json::json;
use sha2::{Digest,Sha256};
use std::{fs::File,io::{Read,Write},time::SystemTime};
use phase_packed_rgb::full_stack::{absorb_chunk,chunk_plan,full_source_supported,write_planes};
use cross_scale_source_prior::{FinestSum,Mode,WeightChanges};
use strehl_core::pyramid::{rb_own_guide_diagnostic as core,cross_scale_source_prior_diagnostic as invariant};
const MAP_HASH:&str="ce8534c9e65c5c761373bad87df5352c1c46319b7eaf7f7c91477ea61b4f4922";
const BASE_PIXELS:&str="7df99f8f54339711c189380cca45cd63fd8106a2a196162bf562ecc60fbfd7db";
const CROP:[usize;4]=[141,97,3234,2150];
const WB:[u32;3]=[1070374912,1065353216,1076715520];
const MATRIX:[[f32;3];3]=[[0.746,-0.2365,-0.0588],[-0.5687,1.3442,0.2474],[-0.0624,0.1156,0.6584]];
#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct Config{schema:u32,phase:String,source_dir:PathBuf,warp_map:PathBuf,out_dir:PathBuf,expected_crop:[usize;4],tone:[f32;3]}
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
fn rgb_hash(path:&Path)->Result<String>{let mut d=tiff::decoder::Decoder::new(std::io::BufReader::new(File::open(path)?))?;
    ensure!(d.dimensions()?==(6468,4300)&&d.colortype()?==tiff::ColorType::RGB(16),"delivered dimensions/type differ");
    let v=match d.read_image()?{tiff::decoder::DecodingResult::U16(v)=>v,_=>bail!("delivered storage is not u16")};
    ensure!(v.len()==6468*4300*3&&!d.more_images(),"delivered shape/pages differ");
    let mut h=Sha256::new();let mut b=vec![0u8;65536];for row in v.chunks(b.len()/2){for(dst,v)in b.chunks_exact_mut(2).zip(row){dst.copy_from_slice(&v.to_le_bytes());}h.update(&b[..2*row.len()]);}Ok(digest(h))}
struct OneFrame<'a>{frame:&'a Frame,index:usize}
impl PyramidFrameSource for OneFrame<'_>{fn len(&self)->usize{299}fn decode(&self,i:usize)->Result<Frame>{ensure!(i==self.index,"source index changed");Ok(self.frame.clone())}}
#[derive(Serialize)]
struct Evidence{index:usize,active_u16_sha256:String,known4_sha256:Vec<String>,guide_sha256:String,variance_sha256:String,beta:Vec<f32>,
    energy_sha256:Vec<String>,floor_sha256:Vec<String>,canonical_weight_sha256:Vec<String>,candidate_weight_sha256:Vec<String>,
    prior_sha256:Vec<String>,changes:Option<WeightChanges>,replay_exact:bool,held_state_bit_exact:bool,source_unchanged:bool,
    pass1_seconds:f64,pass2_seconds:f64}

#[test]
#[ignore="root-owned observational chip pair/cost; fixed config required"]
fn chip_complete_pair()->Result<()>{
    let started=Instant::now();let path=PathBuf::from(std::env::var_os("STREHL_CROSS_SCALE_SOURCE_PRIOR_CHIP_CONFIG").context("chip config required")?);
    let config:Config=serde_json::from_slice(&std::fs::read(&path)?)?;
    ensure!(config.schema==1&&["cost","full"].contains(&config.phase.as_str())&&config.expected_crop==CROP
        &&config.tone.map(f32::to_bits)==[0.004293f32,0.946441,0.55].map(f32::to_bits),"held chip contract differs");
    ensure!(std::env::var("STREHL_CA_BEFORE_MHC").ok().as_deref()==Some("off")
        &&strehl_core::pyramid::fine_support_candidate::environment_mode()==strehl_core::pyramid::fine_support_candidate::Mode::Off,
        "competing experiments must be off; original optical CA remains on");
    ensure!(align_cmd::fullres_gather_enabled()&&gatefloor::enabled()&&align_cmd::direct_plane_mode()?==align_cmd::DirectPlaneMode::Rounded
        &&align_cmd::native_gpu_integration::gpu_gather_enabled()?,"actual rounded GPU/probe path required");
    ensure!(std::env::var_os("STREHL_LOCAL_PLACEMENT_FILE").is_none()&&std::env::var_os("STREHL_ONLY_FRAME").is_none(),"placement/truncation excluded");
    ensure!(!std::env::var(strehl_core::demosaic::DEMOSAIC_ENV).is_ok_and(|v|v.eq_ignore_ascii_case("directional")),"Malvar required");
    ensure!(config.source_dir.is_absolute()&&config.source_dir.file_name().and_then(|s|s.to_str())==Some("uncapped-IC-chip-cpl"),"wrong chip source");
    ensure!(file_hash(&config.warp_map)?==MAP_HASH,"map hash differs");let paths=crate::raw_paths(&config.source_dir,None)?;
    ensure!(paths.len()==299&&paths.iter().enumerate().all(|(i,p)|p.file_name().and_then(|s|s.to_str())==Some(format!("DSC{:05}.ARW",i+1).as_str())),"all299 sources required");
    let before=paths.iter().map(|p|stamp(p)).collect::<Result<Vec<_>>>()?;
    let original=WarpMap::load(&config.warp_map)?;original.check_stack(&StackIdentity::from_paths("uncapped-IC-chip-cpl",&paths)?)?;
    ensure!(original.resampler()==Resampler::CatmullRom&&original.len()==299&&original.placed_count()==299&&original.provenance().reference==149,"held placements differ");
    let(map,fit)=align_cmd::cover_or_explain(original,align_cmd::CoverMode::Crop);let old=fit.rect().context("map crop")?;
    ensure!([old.x,old.y,old.width,old.height]==[133,89,3250,2166],"original crop changed");
    let full=map.geometry();ensure!(full==PlaneGeometry{width:3516,height:2344},"full geometry changed");
    let crop=align_cmd::CropRect{x:CROP[0],y:CROP[1],width:CROP[2],height:CROP[3]};
    let identities=paths.iter().map(|p|strehl_raw::identity(p)).collect::<Vec<_>>();
    let profiles=identities.iter().map(|id|strehl_core::optics::profile_for_capture_env(id.model.as_deref(),id.lens_type3)).collect::<std::result::Result<Vec<_>,_>>()?;
    for(i,ca)in profiles.iter().enumerate(){ensure!(ca.is_some_and(|p|p.key=="a7c2-fe100gm-2xtc-x4cpl"),"held optical CA absent");
        ensure!(full_source_supported(map.placement(i)?,full,crop,*ca),"held source support refused at {i}");}
    let cost=config.phase=="cost";let indices=if cost{vec![149]}else{(0..299).collect::<Vec<_>>()};
    let source_clock=Instant::now();let first=strehl_raw::decode(&paths[indices[0]])?;
    let levels=first.levels;let wb=first.wb_coeffs;let gain=first.wb_gains().context("WB")?;
    ensure!(first.camera=="ILCE-7CM2"&&first.iso==Some(100.)&&levels==Levels{black:512.,white:15360.}
        &&first.geometry()==full&&first.active.width==7032&&first.active.height==4688&&gain.map(f32::to_bits)==WB
        &&first.xyz_to_cam_rgb()==Some(MATRIX),"held first metadata differs");
    let(active,stride,height)=(first.active,first.stride,first.buffer_height);
    let cfg=MergeConfig::default();ensure!(cfg.bands==7,"held bands changed");
    let plan=chunk_plan(full,first.allocated_bytes(),299,cfg);ensure!(plan.canonical_chunks==4&&plan.per_chunk==75,"canonical grouping changed");
    let threads=band_workers(plan.planning_bytes,299)?;ensure!(threads==8,"eight execution threads required");let pool=ThreadPoolBuilder::new().num_threads(threads).build()?;
    let sizes=level_sizes(crop.width,crop.height,cfg.bands);let domain=PyramidDomain::cropped(full,crop)?;
    let noise=profile::noise_model_for(&first.camera,first.iso,levels);ensure!(noise.is_trustworthy(),"injected profile untrusted");
    let matrix=color::camera_to_srgb(MATRIX).context("matrix singular")?.with_saturation(levels,gain,1.);
    let mut dev=image_out::OutputSpace::Srgb.develop(Some(matrix));dev.tone=Some(image_out::Tone{black:config.tone[0],white:config.tone[1],contrast:config.tone[2]});dev.exposure_gain=1.;
    let root=PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../..").canonicalize()?;
    ensure!(!config.out_dir.exists()&&config.out_dir.parent().context("output parent")?.canonicalize()?.starts_with(root.join("experiments").canonicalize()?),"fresh workspace output required");
    std::fs::create_dir(&config.out_dir)?;
    save(&config.out_dir.join("started.json"),&json!({"schema":1,"phase":config.phase,"map_sha256":MAP_HASH,"crop":CROP,
        "tone_bits":config.tone.map(f32::to_bits),"wb_bits":WB,"matrix":MATRIX,"plan":plan,"threads":threads,
        "source_count":indices.len(),"prior_source_count":indices.len(),"probe_source_count":299,"probe_source_index":"original index",
        "all299_support_preflight":true,"generated_photographic_replay_admitted":false,"scope":"separate observational chip counterfactual",
        "level_sizes":sizes.iter().map(|s|[s.width,s.height]).collect::<Vec<_>>(),"ca_stage":"off","optical_ca":"a7c2-fe100gm-2xtc-x4cpl","observer":false}))?;
    let metadata=|f:&Frame|->Result<()>{ensure!(f.camera=="ILCE-7CM2"&&f.iso==Some(100.)&&f.levels==levels&&f.active==active
        &&f.stride==stride&&f.buffer_height==height&&f.wb_gains().context("WB")?.map(f32::to_bits)==WB
        &&f.xyz_to_cam_rgb()==Some(MATRIX),"source metadata drift");Ok(())};
    let mut sum=FinestSum::full_chip(&sizes,indices.len())?;let mut base=BandWorker::new(domain,cfg);let mut base_total=None;
    let mut evidence=Vec::new();let mut initial=Some(first);
    pool.install(||->Result<()>{for(position,&i)in indices.iter().enumerate(){let timer=Instant::now();
        let frame=match initial.take(){Some(f)=>f,None=>strehl_raw::decode(&paths[i])?};metadata(&frame)?;
        let active_u16_sha256=source_hash(&frame);let source=OneFrame{frame:&frame,index:i};
        ensure!(base.fold(&source,i,levels,&noise,Some(&map),None)?,"first-pass source{i} refused");
        let fields=core::canonical_fields(&base.merge,&base.fws,(!base.beta.is_empty()).then_some(base.beta.as_slice()));sum.add(&fields.weights[0])?;
        ensure!(source_hash(&frame)==active_u16_sha256,"original active CFA changed");
        evidence.push(Evidence{index:i,active_u16_sha256,known4_sha256:hashes(&base.planes),guide_sha256:field_hash(&base.luma),
            variance_sha256:field_hash(&base.var),beta:base.beta.clone(),energy_sha256:hashes(&fields.energy),floor_sha256:hashes(&fields.floor),
            canonical_weight_sha256:hashes(&fields.weights),candidate_weight_sha256:vec![],prior_sha256:vec![],changes:None,
            replay_exact:false,held_state_bit_exact:false,source_unchanged:true,pass1_seconds:timer.elapsed().as_secs_f64(),pass2_seconds:0.});
        let last=position+1==indices.len();if last||(i+1)%plan.per_chunk==0{absorb_chunk(&mut base_total,&mut base.merge,crop.width,crop.height,4,cfg);if !last{base.reset_chunk();}}
        eprintln!("cross-scale chip pass1 {}/{} source{} {:.3}s",position+1,indices.len(),i,timer.elapsed().as_secs_f64());
    }Ok(())})?;
    let pass1_seconds=source_clock.elapsed().as_secs_f64();drop(base);let prior=pool.install(||sum.finish())?;
    let base_total=base_total.context("no baseline")?;let baseline_averaged_fraction=base_total.averaged_fraction();
    let finish_clock=Instant::now();let baseline=pool.install(||base_total.finish(&mut Workspace::new(&sizes)));
    let baseline_planes_sha256=hashes(&baseline);let base_path=config.out_dir.join("baseline.tiff");
    pool.install(||write_planes(&base_path,&baseline,crop,levels,wb,&dev))?;drop(baseline);
    let base_rgb=rgb_hash(&base_path)?;if !cost{ensure!(base_rgb==BASE_PIXELS,"historical complete baseline pixels changed");}
    let baseline_sha256=file_hash(&base_path)?;save(&config.out_dir.join("baseline-ready.json"),&json!({"image_sha256":baseline_sha256,
        "rgb16_le_sha256":base_rgb,"historical_pixels_required":!cost}))?;let baseline_finish_seconds=finish_clock.elapsed().as_secs_f64();
    let second_clock=Instant::now();let mut replay=BandWorker::new(domain,cfg);let mut candidate=BandMerge::new(crop.width,crop.height,4,cfg);
    let mut candidate_ws=FrameWorkspace::new(&sizes,4);let(mut replay_total,mut candidate_total)=(None,None);
    pool.install(||->Result<()>{for(position,&i)in indices.iter().enumerate(){let timer=Instant::now();let frame=strehl_raw::decode(&paths[i])?;metadata(&frame)?;
        let ev=&mut evidence[position];ensure!(ev.index==i&&source_hash(&frame)==ev.active_u16_sha256,"original active CFA differs between passes");
        let source=OneFrame{frame:&frame,index:i};ensure!(replay.fold(&source,i,levels,&noise,Some(&map),None)?,"second-pass source{i} refused");
        ensure!(hashes(&replay.planes)==ev.known4_sha256&&field_hash(&replay.luma)==ev.guide_sha256
            &&field_hash(&replay.var)==ev.variance_sha256&&same(&replay.beta,&ev.beta),"gather/guide/variance/beta replay differs");
        let mut fields=core::canonical_fields(&replay.merge,&replay.fws,(!replay.beta.is_empty()).then_some(replay.beta.as_slice()));
        ensure!(hashes(&fields.energy)==ev.energy_sha256&&hashes(&fields.floor)==ev.floor_sha256
            &&hashes(&fields.weights)==ev.canonical_weight_sha256,"canonical E/F/weights replay differs");
        ev.prior_sha256=hashes(&prior.source(&fields.weights[0])?);ev.changes=Some(prior.apply(&mut fields,Mode::Prior)?);
        ev.candidate_weight_sha256=hashes(&fields.weights);ensure!(ev.candidate_weight_sha256[0]==ev.canonical_weight_sha256[0],"finest weights changed");
        core::add_fields(&mut candidate,&replay.planes.iter().map(Vec::as_slice).collect::<Vec<_>>(),&fields,&mut candidate_ws);
        ensure!(invariant::held_state_bit_exact(&replay.merge,&candidate),"chunk b0/base/mean/hull changed");
        ensure!(source_hash(&frame)==ev.active_u16_sha256,"second pass mutated original active CFA");ev.replay_exact=true;ev.held_state_bit_exact=true;
        let last=position+1==indices.len();if last||(i+1)%plan.per_chunk==0{
            absorb_chunk(&mut replay_total,&mut replay.merge,crop.width,crop.height,4,cfg);absorb_chunk(&mut candidate_total,&mut candidate,crop.width,crop.height,4,cfg);
            if !last{replay.reset_chunk();candidate.reset_for_reuse();}}
        ev.pass2_seconds=timer.elapsed().as_secs_f64();eprintln!("cross-scale chip pass2 {}/{} source{} {:.3}s",position+1,indices.len(),i,ev.pass2_seconds);
    }Ok(())})?;
    let pass2_seconds=second_clock.elapsed().as_secs_f64();drop(replay);drop(candidate);drop(candidate_ws);
    let finish_clock=Instant::now();let replay_total=replay_total.context("no repeated current")?;let candidate_total=candidate_total.context("no candidate")?;
    ensure!(invariant::held_state_bit_exact(&base_total,&replay_total)&&invariant::held_state_bit_exact(&base_total,&candidate_total),"complete held accumulator state differs");
    let repeated=pool.install(||replay_total.finish(&mut Workspace::new(&sizes)));
    ensure!(hashes(&repeated)==baseline_planes_sha256,"complete canonical replay differs");drop(repeated);drop(replay_total);drop(base_total);
    let candidate_averaged_fraction=candidate_total.averaged_fraction();let output=pool.install(||candidate_total.finish(&mut Workspace::new(&sizes)));drop(candidate_total);
    let candidate_planes_sha256=hashes(&output);if cost{ensure!(candidate_planes_sha256==baseline_planes_sha256,"one-source prior changed CFA");}
    let candidate_path=config.out_dir.join("candidate.tiff");pool.install(||write_planes(&candidate_path,&output,crop,levels,wb,&dev))?;drop(output);
    let candidate_rgb=rgb_hash(&candidate_path)?;if cost{ensure!(candidate_rgb==base_rgb,"one-source prior changed delivered RGB16");}
    let candidate_sha256=file_hash(&candidate_path)?;let finish_seconds=baseline_finish_seconds+finish_clock.elapsed().as_secs_f64();
    ensure!(paths.iter().map(|p|stamp(p)).collect::<Result<Vec<_>>>()?==before&&file_hash(&config.warp_map)?==MAP_HASH,"input bindings changed");
    save(&config.out_dir.join("receipt.json"),&json!({"schema":1,"phase":config.phase,"frames":evidence,"source_count":indices.len(),
        "prior_source_count":indices.len(),"probe_source_count":299,"map_sha256":MAP_HASH,"crop":CROP,"native_dimensions":[6468,4300],
        "plan":plan,"threads":threads,"observer":false,"tone_bits":config.tone.map(f32::to_bits),"wb_bits":WB,"matrix":MATRIX,
        "source_phase_seconds":pass1_seconds+pass2_seconds,"pass1_seconds":pass1_seconds,"pass2_seconds":pass2_seconds,
        "finish_seconds":finish_seconds,"total_seconds":started.elapsed().as_secs_f64(),"baseline_averaged_fraction":baseline_averaged_fraction,
        "candidate_averaged_fraction":candidate_averaged_fraction,"held_state_bit_exact":true,"replay_exact":true,
        "cost_output_exact":if cost{Some(true)}else{None},"generated_photographic_replay_admitted":false,
        "finest_denominator_sha256":field_hash(&prior.denominator),"supported_sha256":hashes(&prior.supported),
        "wholly_unsupported_counts":prior.supported.iter().map(|v|v.iter().filter(|&&x|x==0.).count()).collect::<Vec<_>>(),
        "baseline_planes_sha256":baseline_planes_sha256,"candidate_planes_sha256":candidate_planes_sha256,
        "baseline_rgb16_le_sha256":base_rgb,"candidate_rgb16_le_sha256":candidate_rgb,"baseline_sha256":baseline_sha256,
        "candidate_sha256":candidate_sha256,"unsupported_samples":0,"all299_support_preflight":true,"original_metadata_unchanged":true}))?;
    Ok(())
}
