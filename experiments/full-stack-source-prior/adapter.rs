// Full photographs under an unchanged, known-risk prior; no production default.
use super::*;
use serde::{Deserialize,Serialize};
use serde_json::json;
use sha2::{Digest,Sha256};
use std::{fs::File,io::{Read,Write},time::SystemTime};
use phase_packed_rgb::full_stack::{absorb_chunk,chunk_plan,full_source_supported};
use cross_scale_source_prior::{SourcePrior,Mode,WeightChanges};
use strehl_core::pyramid::{LevelSize,reduce,rb_own_guide_diagnostic as core,cross_scale_source_prior_diagnostic as invariant};

#[derive(Deserialize,Serialize)]
#[serde(deny_unknown_fields)]
struct Input {index:usize,path:PathBuf,identity_name:String,bytes:u64,sha256:String}
#[derive(Deserialize,Serialize)]
#[serde(deny_unknown_fields)]
struct Historical {receipt:PathBuf,sha256:String}
#[derive(Deserialize,Serialize)]
#[serde(deny_unknown_fields)]
struct Config {
    schema:u32,phase:String,mode:String,stack_name:String,inputs:Vec<Input>,warp_map:PathBuf,
    warp_map_sha256:String,out_dir:PathBuf,expected_reference:usize,expected_full_geometry:[usize;2],
    expected_crop:[usize;4],expected_baseline:PathBuf,expected_baseline_sha256:String,
    expected_baseline_pixels_sha256:String,expected_camera:String,expected_iso:f32,
    exposure_stops:f32,tone_policy:String,
    historical:Option<Historical>,
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

/// Only the scope constructor is new. The denominator arithmetic is literally
/// the retained serial-f32 loop; SourcePrior::source/apply remain shared.
struct FullFinestSum {sizes:Vec<LevelSize>,source_count:usize,seen:usize,denominator:Vec<f32>}
impl FullFinestSum {
    fn new(sizes:&[LevelSize],source_count:usize)->Result<Self>{
        ensure!((1..=1024).contains(&source_count)&&!sizes.is_empty(),"bounded source count required");
        let first=sizes[0];let pixels=first.width.checked_mul(first.height).context("extent overflow")?;
        ensure!(first.width>0&&first.width<=3516&&first.height>0&&first.height<=2344
            &&pixels<=3516*2344&&sizes==level_sizes(first.width,first.height,7).as_slice()&&sizes.len()>=2,"bounded exact seven-band geometry required");
        Ok(Self{sizes:sizes.to_vec(),source_count,seen:0,denominator:vec![0.0;pixels]})
    }
    fn add(&mut self,w:&[f32])->Result<()>{ensure!(self.seen<self.source_count&&w.len()==self.denominator.len()
        &&w.iter().all(|v|v.is_finite()&&*v>=0.0),"invalid finest field/count");
        for(d,&v)in self.denominator.iter_mut().zip(w){*d+=v;ensure!(d.is_finite(),"finest denominator overflow");}
        self.seen+=1;Ok(())}
    fn finish(self)->Result<SourcePrior>{ensure!(self.seen==self.source_count,"incomplete finest denominator");
        let z=self.denominator.iter().map(|&d|if d>0.0{1.0}else{0.0}).collect::<Vec<_>>();let mut supported=vec![z];
        for k in 1..self.sizes.len(){let mut next=vec![0.0;self.sizes[k].pixels()];
            reduce(&supported[k-1],self.sizes[k-1],&mut next,&mut vec![0.0;self.sizes[k].width*self.sizes[k-1].height]);supported.push(next);}
        Ok(SourcePrior{sizes:self.sizes,source_count:self.source_count,denominator:self.denominator,supported})}
}

#[derive(Clone,Serialize,Deserialize)]
#[serde(deny_unknown_fields)]
pub(crate) struct CacheMetadata {
    pub schema:u32,pub full_geometry:[usize;2],pub crop:[usize;4],pub levels_bits:[u32;2],
    pub wb_gains_bits:Option<[u32;3]>,pub xyz_to_cam_bits:Option<[[u32;3];3]>,pub xyz_source:Option<String>,
    pub exposure_stops_bits:Option<u32>,pub tone_policy:String,pub frames:usize,pub reference:usize,
    pub map_sha256:String,pub input_order_sha256:String,pub plane_order:[String;4],pub binary:String,
    pub binary_bytes:u64,pub binary_sha256:String,pub plane_sha256:Vec<String>,pub arm:String,pub phase:String,
}
impl CacheMetadata {
    pub(crate) fn domain(&self)->Result<PyramidDomain>{PyramidDomain::cropped(
        PlaneGeometry{width:self.full_geometry[0],height:self.full_geometry[1]},
        align_cmd::CropRect{x:self.crop[0],y:self.crop[1],width:self.crop[2],height:self.crop[3]})}
    pub(crate) fn levels(&self)->Levels{Levels{black:f32::from_bits(self.levels_bits[0]),white:f32::from_bits(self.levels_bits[1])}}
    pub(crate) fn wb(&self)->Option<[f32;3]>{self.wb_gains_bits.map(|v|v.map(f32::from_bits))}
    pub(crate) fn xyz(&self)->Option<([[f32;3];3],String)>{self.xyz_to_cam_bits.map(|v|(v.map(|r|r.map(f32::from_bits)),self.xyz_source.clone().unwrap_or_default()))}
    pub(crate) fn exposure(&self)->Result<Exposure>{Ok(Exposure::resolve(true,self.exposure_stops_bits.map(f32::from_bits).unwrap_or(0.0),false)?)}
}
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
pub(crate) fn read_cache(path:&Path)->Result<(CacheMetadata,Vec<Vec<f32>>)> {
    let m:CacheMetadata=serde_json::from_slice(&std::fs::read(path)?)?;let d=m.domain()?;
    ensure!(m.schema==1&&m.full_geometry==[3516,2344]&&m.frames>0&&m.frames<=1024&&m.reference<m.frames
        &&["cost","full"].contains(&m.phase.as_str())
        &&m.plane_order==["R","G1","G2","B"].map(String::from)&&m.plane_sha256.len()==4
        &&m.tone_policy=="automatic-per-arm-current-writer","invalid cache contract");
    let len=d.analysis().pixels();let bytes=len.checked_mul(16).context("cache size overflow")?;
    ensure!(m.binary_bytes==bytes as u64&&Path::new(&m.binary).components().count()==1
        &&Path::new(&m.binary).file_name().is_some(),"invalid cache file/length");
    let file=path.parent().context("cache parent")?.join(&m.binary);ensure!(std::fs::metadata(&file)?.len()==m.binary_bytes&&file_hash(&file)?==m.binary_sha256,"cache binary binding changed");
    let mut input=std::io::BufReader::new(File::open(file)?);let mut output=Vec::with_capacity(4);let mut buf=vec![0u8;65536];
    for k in 0..4{let mut plane=vec![0.0;len];for row in plane.chunks_mut(buf.len()/4){input.read_exact(&mut buf[..row.len()*4])?;for(v,b)in row.iter_mut().zip(buf.chunks_exact(4)){*v=f32::from_bits(u32::from_le_bytes(b.try_into().unwrap()));}}
        ensure!(plane.iter().all(|v|v.is_finite())&&field_hash(&plane)==m.plane_sha256[k],"cache plane is invalid");output.push(plane);}
    ensure!(m.levels().black.is_finite()&&m.levels().white.is_finite()&&m.levels().range().is_finite()&&m.levels().range()>0.0
        &&m.wb().is_some_and(|v|v.iter().all(|x|x.is_finite()&&*x>0.0))
        &&m.xyz().is_some_and(|(v,_)|v.iter().flatten().all(|x|x.is_finite())),"cache camera metadata invalid");m.exposure()?;
    Ok((m,output))
}
pub(crate) fn write_current(path:&Path,planes:&[Vec<f32>],m:&CacheMetadata)->Result<()>{
    write_merged(Merged::Bands{domain:m.domain()?,planes},m.levels(),m.wb(),m.xyz().as_ref(),
        image_out::OutputSpace::Srgb,true,m.exposure()?,None,path)
}
struct OneFrame<'a>{frame:&'a Frame,index:usize,count:usize}
impl PyramidFrameSource for OneFrame<'_>{fn len(&self)->usize{self.count}fn decode(&self,i:usize)->Result<Frame>{ensure!(i==self.index,"source index changed");Ok(self.frame.clone())}}
#[derive(Serialize)]
struct Evidence{index:usize,active_u16_sha256:String,known4_sha256:Vec<String>,guide_sha256:String,variance_sha256:String,beta:Vec<f32>,
    energy_sha256:Vec<String>,floor_sha256:Vec<String>,canonical_weight_sha256:Vec<String>,candidate_weight_sha256:Vec<String>,
    prior_sha256:Vec<String>,changes:Option<WeightChanges>,replay_exact:bool,held_state_bit_exact:bool,source_unchanged:bool,
    pass1_seconds:f64,pass2_seconds:f64}


#[test]
#[ignore="root-owned complete observational pair/cost; explicit config required"]
fn complete_pair()->Result<()> {
    run_complete(false)
}
#[test]
#[ignore="root-owned corrected current observation; immutable historical bundle required"]
fn corrected_current()->Result<()> {run_complete(true)}

fn historical_replay(config:&Config,template:&CacheMetadata,native:[usize;2])->Result<serde_json::Value>{
    let binding=config.historical.as_ref().context("historical bundle required")?;
    ensure!(binding.receipt.is_absolute()&&file_hash(&binding.receipt)?==binding.sha256,"historical receipt binding changed");
    let old:serde_json::Value=serde_json::from_slice(&std::fs::read(&binding.receipt)?)?;
    ensure!(old["phase"]=="full"&&(old["mode"]=="current"||old["mode"]=="prior")&&old["source_count"]==json!(template.frames)
        &&old["baseline_rgb16_le_sha256"]==json!(config.expected_baseline_pixels_sha256)
        &&old["original_metadata_unchanged"]==true,"historical receipt is not a complete exact current baseline");
    let cache=PathBuf::from(old["baseline_cache"]["path"].as_str().context("historical cache path")?);
    ensure!(cache.is_absolute()&&json!(file_hash(&cache)?)==old["baseline_cache"]["sha256"],"historical cache metadata changed");
    let (m,planes)=read_cache(&cache)?;
    ensure!(m.arm=="baseline"&&m.phase=="full"&&json!(m.binary_sha256)==old["baseline_cache"]["binary_sha256"]
        &&json!(m.plane_sha256)==old["baseline_planes_sha256"],"historical cache/receipt disagree");
    let (a,b)=(serde_json::to_value(&m)?,serde_json::to_value(template)?);
    for key in ["schema","full_geometry","crop","levels_bits","wb_gains_bits","xyz_to_cam_bits","xyz_source",
        "exposure_stops_bits","tone_policy","frames","reference","map_sha256","input_order_sha256","plane_order","phase"] {
        ensure!(a[key]==b[key],"historical acquisition metadata differs: {key}");
    }
    let replay=config.out_dir.join("historical-baseline-replay.tiff");write_current(&replay,&planes,&m)?;
    ensure!(rgb_hash(&replay,native)?==config.expected_baseline_pixels_sha256,"historical cache replay pixels changed");
    let icc=|p:&Path|->Result<Vec<u8>>{let mut d=tiff::decoder::Decoder::new(std::io::BufReader::new(File::open(p)?))?;
        let v=d.get_tag_u8_vec(tiff::tags::Tag::IccProfile)?;ensure!(!v.is_empty(),"ICC absent");Ok(v)};
    ensure!(icc(&replay)?==icc(&config.expected_baseline)?,"historical replay ICC changed");
    let frames=old["frames"].as_array().context("historical source evidence absent")?;
    ensure!(frames.len()==template.frames&&frames.iter().enumerate().all(|(i,v)|v["index"]==json!(i)),"historical evidence order differs");
    Ok(old)
}

fn run_complete(numerical_candidate:bool)->Result<()> {
    let started=Instant::now();let path=PathBuf::from(std::env::var_os("STREHL_FULL_STACK_SOURCE_PRIOR_CONFIG").context("full-stack config required")?);
    let config:Config=serde_json::from_slice(&std::fs::read(&path)?)?;
    ensure!(numerical_candidate==config.historical.is_some()
        &&(!numerical_candidate||(config.phase=="full"&&config.mode=="current")),"historical/corrected purpose mismatch");
    ensure!(config.schema==1&&["cost","full"].contains(&config.phase.as_str())&&["current","prior"].contains(&config.mode.as_str())
        &&config.tone_policy=="automatic-per-arm-current-writer"&&config.expected_full_geometry==[3516,2344],"held full-stack contract differs");
    let count=config.inputs.len();ensure!((3..=1024).contains(&count)&&config.expected_reference>0&&config.expected_reference+1<count,"bounded complete stack/ref required");
    ensure!(config.inputs.iter().enumerate().all(|(i,v)|v.index==i&&v.path.is_absolute()&&v.bytes>0&&v.sha256.len()==64
        &&Path::new(&v.identity_name).components().count()==1&&Path::new(&v.identity_name).file_name().is_some()),"ordered source identity invalid");
    ensure!(std::env::var("STREHL_CA_BEFORE_MHC").ok().as_deref()==Some("off")
        &&strehl_core::pyramid::fine_support_candidate::environment_mode()==strehl_core::pyramid::fine_support_candidate::Mode::Off,
        "competing experiments must be off; original optical CA remains on");
    ensure!(align_cmd::fullres_gather_enabled()&&gatefloor::enabled()&&align_cmd::direct_plane_mode()?==align_cmd::DirectPlaneMode::Rounded
        &&align_cmd::native_gpu_integration::gpu_gather_enabled()?,"actual rounded GPU/probe path required");
    ensure!(std::env::var_os("STREHL_LOCAL_PLACEMENT_FILE").is_none()&&std::env::var_os("STREHL_ONLY_FRAME").is_none()
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
    let cost=config.phase=="cost";let indices=if cost{vec![config.expected_reference-1,config.expected_reference,config.expected_reference+1]}else{(0..count).collect::<Vec<_>>()};
    let decode_clock=Instant::now();let first=strehl_raw::decode(&paths[indices[0]])?;let first_decode_seconds=decode_clock.elapsed().as_secs_f64();
    ensure!(first.camera==config.expected_camera&&first.iso==Some(config.expected_iso)&&first.geometry()==full
        &&first.active.width==7032&&first.active.height==4688,"held first metadata differs");
    let levels=first.levels;let wb=first.wb_gains().context("WB")?;let xyz=first.xyz_to_cam_rgb_with_source().context("camera matrix")?;
    ensure!(levels.range()>0.0&&wb.iter().all(|v|v.is_finite()&&*v>0.0)&&xyz.0.iter().flatten().all(|v|v.is_finite()),"invalid first calibration metadata");
    let(active,stride,height)=(first.active,first.stride,first.buffer_height);
    let cfg=MergeConfig::default();ensure!(cfg.bands==7,"held bands changed");
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
    std::fs::create_dir(&config.out_dir)?;
    let mut real_trace = real_source_contributions::Session::start(
        &config.out_dir, &sizes, count, plan.per_chunk)?;
    let historical=if numerical_candidate{Some(historical_replay(&config,&cache_template,native)?)}else{None};
    if let Some(old)=&historical{ensure!(old["plan"]==json!(plan)&&old["threads"]==json!(threads),"historical canonical chunk plan/threads changed");}
    save(&config.out_dir.join("started.json"),&json!({"schema":1,"phase":config.phase,"mode":config.mode,"map_sha256":config.warp_map_sha256,
        "crop":config.expected_crop,"plan":plan,"threads":threads,"indices":indices,"source_count":indices.len(),"probe_source_count":count,
        "all_colour_site_support_checks":support,"generated_photographic_replay_admitted":false,
        "scope":"separate observational complete-stack counterfactual; previous general qualification remains rejected",
        "cache_metadata":cache_template,"ca_stage":"off","optical_ca":"a7c2-fe100gm-2xtc-x4cpl","observer":false}))?;
    let metadata=|f:&Frame|->Result<()>{ensure!(f.camera==config.expected_camera&&f.iso==Some(config.expected_iso)&&f.levels==levels
        &&f.active==active&&f.stride==stride&&f.buffer_height==height&&f.wb_gains().context("WB")?.map(f32::to_bits)==wb.map(f32::to_bits)
        &&f.xyz_to_cam_rgb()==Some(xyz.0),"source metadata drift");Ok(())};
    let source_clock=Instant::now();
    let mut sum=FullFinestSum::new(&sizes,indices.len())?;let mut base=BandWorker::new(domain,cfg);let mut base_total=None;
    let mut evidence=Vec::new();let mut initial=Some(first);
    pool.install(||->Result<()>{for(position,&i)in indices.iter().enumerate(){let timer=Instant::now();
        let frame=match initial.take(){Some(f)=>f,None=>strehl_raw::decode(&paths[i])?};metadata(&frame)?;
        let active_u16_sha256=source_hash(&frame);let source=OneFrame{frame:&frame,index:i,count:paths.len()};
        ensure!(base.fold(&source,i,levels,&noise,Some(&map),None)?,"first-pass source{i} refused");
        let fields=core::canonical_fields(&base.merge,&base.fws,(!base.beta.is_empty()).then_some(base.beta.as_slice()));sum.add(&fields.weights[0])?;
        if let Some(trace) = real_trace.as_mut() {
            trace.source(i, &base.merge, &base.fws, &fields, &base.planes)?;
        }
        ensure!(source_hash(&frame)==active_u16_sha256,"original active CFA changed");
        evidence.push(Evidence{index:i,active_u16_sha256,known4_sha256:hashes(&base.planes),guide_sha256:field_hash(&base.luma),
            variance_sha256:field_hash(&base.var),beta:base.beta.clone(),energy_sha256:hashes(&fields.energy),floor_sha256:hashes(&fields.floor),
            canonical_weight_sha256:hashes(&fields.weights),candidate_weight_sha256:vec![],prior_sha256:vec![],changes:None,
            replay_exact:false,held_state_bit_exact:false,source_unchanged:true,pass1_seconds:timer.elapsed().as_secs_f64(),pass2_seconds:0.});
        if let Some(old)=&historical {let now=serde_json::to_value(evidence.last().context("missing current evidence")?)?;
            for key in ["index","active_u16_sha256","known4_sha256","guide_sha256","variance_sha256","beta",
                "energy_sha256","floor_sha256","canonical_weight_sha256","source_unchanged"] {
                ensure!(now[key]==old["frames"][i][key],"corrected run changed held source{i} field {key}");
            }
        }
        let last=position+1==indices.len();if last||(i+1)%plan.per_chunk==0{absorb_chunk(&mut base_total,&mut base.merge,crop.width,crop.height,4,cfg);if !last{base.reset_chunk();}}
        eprintln!("full-stack prior pass1 {}/{} source{} {:.3}s",position+1,indices.len(),i,timer.elapsed().as_secs_f64());
    }Ok(())})?;
    let pass1_seconds=source_clock.elapsed().as_secs_f64();drop(base);let prior=pool.install(||sum.finish())?;
    let base_total=base_total.context("no baseline")?;let baseline_averaged_fraction=base_total.averaged_fraction();
    let finish_clock=Instant::now();let baseline=pool.install(||base_total.finish(&mut Workspace::new(&sizes)));
    if let Some(trace) = real_trace.take() { trace.finish(&base_total, &baseline)?; }
    let arm=if numerical_candidate{"candidate"}else{"baseline"};
    let baseline_planes_sha256=hashes(&baseline);let base_path=config.out_dir.join(format!("{arm}.tiff"));
    let baseline_cache=write_cache(&config.out_dir,arm,&baseline,&cache_template)?;
    pool.install(||write_current(&base_path,&baseline,&cache_template))?;drop(baseline);
    let base_rgb=rgb_hash(&base_path,native)?;
    if numerical_candidate {
        ensure!(paths.iter().map(|p|stamp(p)).collect::<Result<Vec<_>>>()?==before&&file_hash(&config.warp_map)?==config.warp_map_sha256,"input bindings changed");
        let h=config.historical.as_ref().context("historical bundle")?;ensure!(file_hash(&h.receipt)?==h.sha256,"historical receipt changed during corrected run");
        save(&config.out_dir.join("receipt.json"),&json!({"schema":1,"phase":"full","mode":"numerical-candidate","frames":evidence,
            "source_count":indices.len(),"probe_source_count":count,"crop":config.expected_crop,"native_dimensions":native,
            "map_sha256":config.warp_map_sha256,"plan":plan,"threads":threads,"tone_policy":config.tone_policy,
            "source_phase_seconds":pass1_seconds,"finish_seconds":finish_clock.elapsed().as_secs_f64(),"total_seconds":started.elapsed().as_secs_f64(),
            "candidate_planes_sha256":baseline_planes_sha256,"candidate_rgb16_le_sha256":base_rgb,"candidate_sha256":file_hash(&base_path)?,
            "candidate_cache":baseline_cache,"historical":config.historical,"historical_cache_replay_exact":true,"held_source_evidence_exact":true,
            "expected_historical_pixels_sha256":config.expected_baseline_pixels_sha256,"corrected_output_changed":base_rgb!=config.expected_baseline_pixels_sha256,
            "all_colour_site_support_checks":support,"original_metadata_unchanged":true,"photographic_replay_admitted":false}))?;
        return Ok(());
    }
    if !cost{ensure!(base_rgb==config.expected_baseline_pixels_sha256,"historical complete baseline pixels changed");}
    let baseline_sha256=file_hash(&base_path)?;save(&config.out_dir.join("baseline-ready.json"),&json!({"image_sha256":baseline_sha256,
        "rgb16_le_sha256":base_rgb,"historical_pixels_required":!cost}))?;let baseline_finish_seconds=finish_clock.elapsed().as_secs_f64();
    if config.mode=="current" {
        ensure!(paths.iter().map(|p|stamp(p)).collect::<Result<Vec<_>>>()?==before&&file_hash(&config.warp_map)?==config.warp_map_sha256,"input bindings changed");
        save(&config.out_dir.join("receipt.json"),&json!({"schema":1,"phase":config.phase,"mode":config.mode,"frames":evidence,
            "source_count":indices.len(),"probe_source_count":count,"crop":config.expected_crop,"native_dimensions":native,
            "map_sha256":config.warp_map_sha256,"plan":plan,"threads":threads,"tone_policy":config.tone_policy,
            "source_phase_seconds":pass1_seconds,"variable_source_seconds":first_decode_seconds+evidence.iter().map(|e|e.pass1_seconds).sum::<f64>(),
            "first_decode_seconds":first_decode_seconds,"finish_seconds":baseline_finish_seconds,"total_seconds":started.elapsed().as_secs_f64(),
            "baseline_averaged_fraction":baseline_averaged_fraction,"baseline_planes_sha256":baseline_planes_sha256,
            "baseline_rgb16_le_sha256":base_rgb,"baseline_sha256":baseline_sha256,"baseline_cache":baseline_cache,
            "all_colour_site_support_checks":support,"original_metadata_unchanged":true,
            "generated_photographic_replay_admitted":false,"candidate_executed":false}))?;
        return Ok(());
    }
    let second_clock=Instant::now();let mut replay=BandWorker::new(domain,cfg);let mut candidate=BandMerge::new(crop.width,crop.height,4,cfg);
    let mut candidate_ws=FrameWorkspace::new(&sizes,4);let(mut replay_total,mut candidate_total)=(None,None);
    pool.install(||->Result<()>{for(position,&i)in indices.iter().enumerate(){let timer=Instant::now();let frame=strehl_raw::decode(&paths[i])?;metadata(&frame)?;
        let ev=&mut evidence[position];ensure!(ev.index==i&&source_hash(&frame)==ev.active_u16_sha256,"original active CFA differs between passes");
        let source=OneFrame{frame:&frame,index:i,count:paths.len()};ensure!(replay.fold(&source,i,levels,&noise,Some(&map),None)?,"second-pass source{i} refused");
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
        ev.pass2_seconds=timer.elapsed().as_secs_f64();eprintln!("full-stack prior pass2 {}/{} source{} {:.3}s",position+1,indices.len(),i,ev.pass2_seconds);
    }Ok(())})?;
    let pass2_seconds=second_clock.elapsed().as_secs_f64();drop(replay);drop(candidate);drop(candidate_ws);
    let finish_clock=Instant::now();let replay_total=replay_total.context("no repeated current")?;let candidate_total=candidate_total.context("no candidate")?;
    ensure!(invariant::held_state_bit_exact(&base_total,&replay_total)&&invariant::held_state_bit_exact(&base_total,&candidate_total),"complete held accumulator state differs");
    let repeated=pool.install(||replay_total.finish(&mut Workspace::new(&sizes)));
    ensure!(hashes(&repeated)==baseline_planes_sha256,"complete canonical replay differs");drop(repeated);drop(replay_total);drop(base_total);
    let candidate_averaged_fraction=candidate_total.averaged_fraction();let output=pool.install(||candidate_total.finish(&mut Workspace::new(&sizes)));drop(candidate_total);
    let candidate_planes_sha256=hashes(&output);
    let candidate_cache=write_cache(&config.out_dir,"candidate",&output,&cache_template)?;
    let candidate_path=config.out_dir.join("candidate.tiff");pool.install(||write_current(&candidate_path,&output,&cache_template))?;drop(output);
    let candidate_rgb=rgb_hash(&candidate_path,native)?;
    let candidate_sha256=file_hash(&candidate_path)?;let finish_seconds=baseline_finish_seconds+finish_clock.elapsed().as_secs_f64();
    ensure!(paths.iter().map(|p|stamp(p)).collect::<Result<Vec<_>>>()?==before&&file_hash(&config.warp_map)?==config.warp_map_sha256,"input bindings changed");
    save(&config.out_dir.join("receipt.json"),&json!({"schema":1,"phase":config.phase,"mode":config.mode,"frames":evidence,"source_count":indices.len(),
        "prior_source_count":indices.len(),"probe_source_count":paths.len(),"map_sha256":config.warp_map_sha256,"crop":config.expected_crop,"native_dimensions":native,
        "plan":plan,"threads":threads,"observer":false,"tone_policy":config.tone_policy,"cache_metadata":cache_template,
        "source_phase_seconds":pass1_seconds+pass2_seconds,"variable_source_seconds":first_decode_seconds+evidence.iter().map(|e|e.pass1_seconds+e.pass2_seconds).sum::<f64>(),"first_decode_seconds":first_decode_seconds,"pass1_seconds":pass1_seconds,"pass2_seconds":pass2_seconds,
        "finish_seconds":finish_seconds,"total_seconds":started.elapsed().as_secs_f64(),"baseline_averaged_fraction":baseline_averaged_fraction,
        "candidate_averaged_fraction":candidate_averaged_fraction,"held_state_bit_exact":true,"replay_exact":true,
        "cost_output_exact":false,"generated_photographic_replay_admitted":false,
        "finest_denominator_sha256":field_hash(&prior.denominator),"supported_sha256":hashes(&prior.supported),
        "wholly_unsupported_counts":prior.supported.iter().map(|v|v.iter().filter(|&&x|x==0.).count()).collect::<Vec<_>>(),
        "baseline_planes_sha256":baseline_planes_sha256,"candidate_planes_sha256":candidate_planes_sha256,
        "baseline_rgb16_le_sha256":base_rgb,"candidate_rgb16_le_sha256":candidate_rgb,"baseline_sha256":baseline_sha256,
        "candidate_sha256":candidate_sha256,"baseline_cache":baseline_cache,"candidate_cache":candidate_cache,"all_colour_site_support_checks":support,"original_metadata_unchanged":true}))?;
    Ok(())
}

#[test]
fn bounded_constructor_preserves_retained_arithmetic()->Result<()> {
    let sizes=level_sizes(33,27,7);let mut old=cross_scale_source_prior::FinestSum::new(&sizes,3)?;
    let mut new=FullFinestSum::new(&sizes,3)?;
    for i in 0..3 {let w=(0..sizes[0].pixels()).map(|p|if p%5==0{0.0}else{((p*13+i*7)%29)as f32*0.125}).collect::<Vec<_>>();old.add(&w)?;new.add(&w)?;}
    let(a,b)=(old.finish()?,new.finish()?);
    ensure!(same(&a.denominator,&b.denominator)&&hashes(&a.supported)==hashes(&b.supported),"constructor changed denominator/support arithmetic");
    ensure!(a.denominator.iter().any(|&v|v==0.0)&&a.denominator.iter().any(|&v|v>0.0),"fixture must contain mixed support");
    ensure!(FullFinestSum::new(&sizes,0).is_err()&&FullFinestSum::new(&sizes,1025).is_err()
        &&FullFinestSum::new(&[LevelSize{width:usize::MAX,height:2}],3).is_err(),"invalid extents/counts admitted");
    let mut incomplete=FullFinestSum::new(&sizes,2)?;incomplete.add(&vec![0.0;sizes[0].pixels()])?;
    ensure!(incomplete.finish().is_err(),"incomplete sum admitted");Ok(())
}
