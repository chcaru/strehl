// Complete70 vitamin-C streaming learned guide; no production default.
use super::*;
use serde::{Deserialize,Serialize};
use serde_json::json;
use sha2::{Digest,Sha256};
use std::{fs::File,io::{Read,Write},time::SystemTime};
use phase_packed_rgb::full_stack::{absorb_chunk,chunk_plan,full_source_supported};
use strehl_core::pyramid::{Pyramid,LevelSize,real_source_contributions as native};
use full_stack_source_prior::CacheMetadata;
use crate::image_out::highlight_rendering::{self as rendering,Arm};
use strehl_core::pyramid::{rb_own_guide_diagnostic as core,Hull,Fallback};

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
    exposure_stops:f32,tone_policy:String,historical_tone:[f32;3],
    python:PathBuf,score_server:PathBuf,score_server_sha256:String,weights:PathBuf,weights_sha256:String,generic_consumer_sha256:String,
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

#[derive(Clone,Deserialize,Serialize)]
pub(crate) struct BridgeConfig {
    pub python:PathBuf,pub score_server:PathBuf,pub score_server_sha256:String,
    pub weights:PathBuf,pub weights_sha256:String,pub generic_consumer_sha256:String,
    pub out_dir:PathBuf,
}
pub(crate) struct Bridge {
    child:std::process::Child,input:std::io::BufWriter<std::process::ChildStdin>,
    output:std::io::BufReader<std::process::ChildStdout>,sizes:Vec<LevelSize>,
    count:usize,seen:usize,indices:Vec<usize>,scored:usize,ready:bool,closed:bool,
}
impl Drop for Bridge {fn drop(&mut self){if !self.closed{let _=self.child.kill();let _=self.child.wait();}}}
impl Bridge {
    pub(crate) fn new(c:&BridgeConfig,sizes:&[LevelSize],count:usize,range:f32,indices:&[usize])->Result<Self>{
        ensure!(count>0&&count<=70&&[4,8].contains(&sizes.len())&&range.is_finite()&&range>0.0,"bridge scope");
        ensure!(!indices.is_empty()&&indices.iter().all(|&i|i<count)&&indices.windows(2).all(|p|p[0]<p[1]),"score order");
        ensure!(c.generic_consumer_sha256=="587e373f6d6afb81e120ca74c4c0094a86b1abd4a020724de38e1b4397ba8003"
            &&file_hash(&c.score_server)?==c.score_server_sha256&&file_hash(&c.weights)?==c.weights_sha256,"frozen bridge/model changed");
        let stderr=std::fs::OpenOptions::new().create_new(true).write(true).open(c.out_dir.join("server.log"))?;
        let mut child=std::process::Command::new(&c.python).args(["-I","-B","-X","faulthandler"])
            .arg(&c.score_server).arg("--weights").arg(&c.weights).arg("--weights-sha256").arg(&c.weights_sha256)
            .arg("--receipt").arg(c.out_dir.join("server-receipt.json"))
            .env("CUBLAS_WORKSPACE_CONFIG",":4096:8").stdin(std::process::Stdio::piped())
            .stdout(std::process::Stdio::piped()).stderr(stderr).spawn()?;
        let input=std::io::BufWriter::with_capacity(1<<20,child.stdin.take().context("child stdin")?);
        let output=std::io::BufReader::with_capacity(1<<20,child.stdout.take().context("child stdout")?);
        let mut this=Self{child,input,output,sizes:sizes.to_vec(),count,seen:0,indices:indices.to_vec(),scored:0,ready:false,closed:false};
        this.header(&json!({"op":"start","schema":1,"sizes":sizes.iter().map(|s|[s.width,s.height]).collect::<Vec<_>>(),
            "source_count":count,"range":range,"score_indices":indices}))?;
        let response=this.response("start")?;ensure!(response["model_sha256"]==c.weights_sha256
            &&response["generic_consumer_sha256"]==c.generic_consumer_sha256
            &&response["scorer_sha256"]=="03ddcab38c492557244638d93694b66473a749aaac6f7785fb129be98dfce96f"
            &&response["consumer_sha256"]=="b5455f488a92ed75c2a8ae8d9dcfb31b054237805b7ded22893459ef4ea9b987","server frozen identity");Ok(this)
    }
    fn pixels(&self)->usize{self.sizes[..self.sizes.len()-1].iter().map(|s|s.pixels()).sum()}
    fn header(&mut self,v:&serde_json::Value)->Result<()>{let bytes=serde_json::to_vec(v)?;ensure!(bytes.len()<=65536,"header bound");
        self.input.write_all(&(bytes.len()as u32).to_le_bytes())?;self.input.write_all(&bytes)?;self.input.flush()?;Ok(())}
    fn response(&mut self,op:&str)->Result<serde_json::Value>{let mut n=[0;4];self.output.read_exact(&mut n)?;let n=u32::from_le_bytes(n)as usize;
        ensure!(n>0&&n<=65536,"response header bound");let mut bytes=vec![0;n];self.output.read_exact(&mut bytes)?;
        let v:serde_json::Value=serde_json::from_slice(&bytes)?;ensure!(v["ok"]==true,"server refused: {v}");ensure!(v["op"]==op,"response operation differs");Ok(v)}
    fn send_fields(&mut self,v:&[Vec<f32>],channels:usize)->Result<()>{ensure!(v.len()+1==self.sizes.len(),"payload levels");
        let mut bytes=vec![0u8;65536];for(k,values)in v.iter().enumerate(){ensure!(values.len()==channels*self.sizes[k].pixels()
            &&values.iter().all(|v|v.is_finite()),"payload shape/finite");for row in values.chunks(bytes.len()/4){
                for(dst,value)in bytes.chunks_exact_mut(4).zip(row){dst.copy_from_slice(&value.to_le_bytes());}self.input.write_all(&bytes[..row.len()*4])?;}}
        self.input.flush()?;Ok(())}
    pub(crate) fn stats(&mut self,index:usize,coeff:&[Vec<f32>])->Result<()>{ensure!(!self.ready&&index==self.seen&&index<self.count,"statistics order");
        self.header(&json!({"op":"stats","index":index,"floats":4*self.pixels()}))?;self.send_fields(coeff,4)?;
        ensure!(self.response("stats")?["index"]==index,"statistics identity");self.seen+=1;Ok(())}
    pub(crate) fn finish_stats(&mut self)->Result<()>{ensure!(!self.ready&&self.seen==self.count,"complete statistics required");
        self.header(&json!({"op":"finish-stats"}))?;ensure!(self.response("finish-stats")?["source_count"]==self.count,"statistics source count");self.ready=true;Ok(())}
    pub(crate) fn score(&mut self,index:usize,coeff:&[Vec<f32>],features:&[Vec<f32>])->Result<Vec<Vec<f32>>>{
        ensure!(self.ready&&self.scored<self.indices.len()&&self.indices[self.scored]==index,"score order");
        self.header(&json!({"op":"score","index":index,"floats":9*self.pixels()}))?;self.send_fields(coeff,4)?;self.send_fields(features,5)?;
        let response=self.response("score")?;ensure!(response["index"]==index&&response["floats"]==self.pixels(),"score response layout");
        let mut values=Vec::new();for s in &self.sizes[..self.sizes.len()-1]{let mut bytes=vec![0u8;4*s.pixels()];self.output.read_exact(&mut bytes)?;
            let v=bytes.chunks_exact(4).map(|v|f32::from_le_bytes(v.try_into().unwrap())).collect::<Vec<_>>();
            ensure!(v.iter().all(|v|v.is_finite()&&*v>0.0&&*v<=2.0),"invalid returned weights");values.push(v);}
        self.scored+=1;Ok(values)
    }
    pub(crate) fn finish(&mut self)->Result<serde_json::Value>{ensure!(self.ready&&self.scored==self.indices.len(),"incomplete scoring");
        self.header(&json!({"op":"finish"}))?;let v=self.response("finish")?;ensure!(self.child.wait()?.success(),"server failed");self.closed=true;Ok(v)}
}

pub(crate) fn coefficients(worker:&BandWorker,sizes:&[LevelSize])->Vec<Vec<f32>>{
    (0..sizes.len()-1).map(|k|native::coefficients(&worker.fws,k).iter().flat_map(|p|p.iter().copied()).collect()).collect()
}
pub(crate) fn features(worker:&BandWorker,sizes:&[LevelSize],fields:&core::Fields,range:f32)->Vec<Vec<f32>>{
    let guides=[worker.luma.clone(),worker.planes[0].iter().zip(&worker.luma).map(|(r,g)|r-g).collect(),
        worker.planes[3].iter().zip(&worker.luma).map(|(b,g)|b-g).collect()];
    let gaussian=guides.iter().map(|g|{let mut p=Pyramid::zeros(sizes);p.build_gaussian(g,&mut Workspace::new(sizes));p}).collect::<Vec<_>>();
    (0..sizes.len()-1).map(|k|{let px=sizes[k].pixels();let mut v=vec![0.;5*px];for j in 0..px{
        v[j]=(fields.energy[k][j]/fields.floor[k][j].max(1.0)).ln_1p();v[px+j]=fields.floor[k][j].ln_1p();
        for c in 0..3{v[(c+2)*px+j]=gaussian[c].level(k)[j]/range;}}v}).collect()
}
fn held_mean_hull(a:&BandMerge,b:&BandMerge,sizes:&[LevelSize])->bool{
    let aa=core::terminal_means(a);let bb=core::terminal_means(b);
    aa.len()==bb.len()&&aa.iter().zip(&bb).all(|(a,b)|same(a,b))
        &&(0..sizes[0].pixels()).all(|j|native::hull(a,j).iter().flatten().zip(native::hull(b,j).iter().flatten()).all(|(a,b)|a.to_bits()==b.to_bits()))
}

#[test]
#[ignore="root-owned complete70 vitamin-C observation; explicit bound config required"]
fn complete_pair()->Result<()> {
    let started=Instant::now();let path=PathBuf::from(std::env::var_os("STREHL_CROSS_SCALE_BAND_FULL_CONFIG").context("full-stack config required")?);
    let config:Config=serde_json::from_slice(&std::fs::read(&path)?)?;
    ensure!(config.schema==1&&["cost","full"].contains(&config.phase.as_str())&&config.mode=="learned-guide"
        &&config.tone_policy=="automatic-baseline-then-exact-pinned-candidate"&&config.expected_full_geometry==[3516,2344],"held full-stack contract differs");
    let count=config.inputs.len();ensure!(count==70&&config.expected_reference==35
        &&config.stack_name=="crystalized-vitamin-c-cpl"&&config.expected_crop==[28,19,3460,2306]
        &&config.exposure_stops.to_bits()==0.0f32.to_bits(),"fixed complete vitamin-C contract differs");
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
    std::fs::create_dir(&config.out_dir)?;
    save(&config.out_dir.join("started.json"),&json!({"schema":1,"phase":config.phase,"mode":config.mode,"map_sha256":config.warp_map_sha256,
        "crop":config.expected_crop,"plan":plan,"threads":threads,"indices":indices,"source_count":indices.len(),"probe_source_count":count,
        "all_colour_site_support_checks":support,"generated_photographic_replay_admitted":false,
        "scope":"one frozen learned guide complete70 observation; no general qualification or default change",
        "cache_metadata":cache_template,"ca_stage":"off","optical_ca":"a7c2-fe100gm-2xtc-x4cpl","observer":false}))?;
    let metadata=|f:&Frame|->Result<()>{ensure!(f.camera==config.expected_camera&&f.iso==Some(config.expected_iso)&&f.levels==levels
        &&f.active==active&&f.stride==stride&&f.buffer_height==height&&f.wb_gains().context("WB")?.map(f32::to_bits)==wb.map(f32::to_bits)
        &&f.xyz_to_cam_rgb()==Some(xyz.0),"source metadata drift");Ok(())};

    ensure!(config.historical_tone.map(f32::to_bits)==[0.090420f32,0.914606f32,0.55f32].map(f32::to_bits),"historical fixed tone differs");
    let scored_indices=if config.phase=="cost"{vec![35]}else{indices.clone()};
    let bridge_config=BridgeConfig{python:config.python.clone(),score_server:config.score_server.clone(),
        score_server_sha256:config.score_server_sha256.clone(),weights:config.weights.clone(),weights_sha256:config.weights_sha256.clone(),
        generic_consumer_sha256:config.generic_consumer_sha256.clone(),out_dir:config.out_dir.clone()};
    let mut bridge=Bridge::new(&bridge_config,&sizes,count,levels.range(),&scored_indices)?;
    let first_clock=Instant::now();let mut base=BandWorker::new(domain,cfg);let mut base_total=None;
    let mut evidence=Vec::new();let mut initial=Some(first);
    pool.install(||->Result<()>{for &i in &indices {let timer=Instant::now();
        let frame=match initial.take(){Some(f)=>f,None=>strehl_raw::decode(&paths[i])?};metadata(&frame)?;
        let active_hash=source_hash(&frame);let source=OneFrame{frame:&frame,index:i,count};
        ensure!(base.fold(&source,i,levels,&noise,Some(&map),None)?,"context source{i} refused");
        let coeff=coefficients(&base,&sizes);bridge.stats(i,&coeff)?;
        let fields=core::canonical_fields(&base.merge,&base.fws,(!base.beta.is_empty()).then_some(base.beta.as_slice()));
        ensure!(source_hash(&frame)==active_hash,"source changed during context");
        evidence.push(json!({"index":i,"active_u16_sha256":active_hash,"known4_sha256":hashes(&base.planes),
            "guide_sha256":field_hash(&base.luma),"variance_sha256":field_hash(&base.var),"beta":base.beta,
            "coefficients_sha256":hashes(&coeff),"energy_sha256":hashes(&fields.energy),"floor_sha256":hashes(&fields.floor),
            "canonical_weight_sha256":hashes(&fields.weights),"pass1_seconds":timer.elapsed().as_secs_f64()}));
        let last=i+1==count;if last||(i+1)%plan.per_chunk==0{absorb_chunk(&mut base_total,&mut base.merge,crop.width,crop.height,4,cfg);if !last{base.reset_chunk();}}
        eprintln!("learned guide context {}/{} {:.3}s",i+1,count,timer.elapsed().as_secs_f64());
    }Ok(())})?;
    bridge.finish_stats()?;drop(base);let pass1_seconds=first_clock.elapsed().as_secs_f64();
    let base_total=base_total.context("no canonical baseline")?;let baseline_averaged_fraction=base_total.averaged_fraction();
    let baseline=pool.install(||base_total.finish(&mut Workspace::new(&sizes)));
    let baseline_planes_sha256=hashes(&baseline);let baseline_cache=write_cache(&config.out_dir,"baseline",&baseline,&cache_template)?;
    let base_path=config.out_dir.join("baseline.tiff");
    let(_,resolved)=pool.install(||rendering::with_arm(Arm::Current,||write_current(&base_path,&baseline,&cache_template)))?;
    let pinned_path=config.out_dir.join("baseline-pinned-rewrite.tiff");pool.install(||pinned_write(&pinned_path,&baseline,&cache_template,&resolved))?;
    ensure!(file_hash(&base_path)?==file_hash(&pinned_path)?,"fresh baseline pinned whole TIFF differs");
    let baseline_sha256=file_hash(&base_path)?;let baseline_rgb=rgb_hash(&base_path,native)?;
    let historical_auto_match=baseline_rgb==config.expected_baseline_pixels_sha256;
    let mut old_resolved=resolved.clone();old_resolved.tone_bits=Some(config.historical_tone.map(f32::to_bits));
    let old_path=config.out_dir.join("baseline-historical-tone.tiff");pool.install(||pinned_write(&old_path,&baseline,&cache_template,&old_resolved))?;
    let historical_match=rgb_hash(&old_path,native)?==config.expected_baseline_pixels_sha256&&icc(&old_path)?==icc(&config.expected_baseline)?;
    save(&config.out_dir.join("baseline-ready.json"),&json!({"automatic_historical_rgb_match":historical_auto_match,
        "historical_tone_rgb_icc_exact":historical_match,"actual_tone":resolved,"historical_tone":old_resolved,
        "baseline_sha256":baseline_sha256,"baseline_rgb16_le_sha256":baseline_rgb,"baseline_planes_sha256":baseline_planes_sha256}))?;
    ensure!(historical_match,"current baseline differs even at historical tone; diagnose before scoring");drop(baseline);

    let second_clock=Instant::now();let mut replay=BandWorker::new(domain,cfg);let mut candidate=BandMerge::new(crop.width,crop.height,4,cfg);
    let mut candidate_ws=FrameWorkspace::new(&sizes,4);let(mut replay_total,mut candidate_total)=(None,None);let mut scored=Vec::new();
    pool.install(||->Result<()>{for &i in &scored_indices{let timer=Instant::now();let frame=strehl_raw::decode(&paths[i])?;metadata(&frame)?;
        let ev=&evidence[i];ensure!(ev["active_u16_sha256"]==source_hash(&frame),"source bytes differ between passes");
        let source=OneFrame{frame:&frame,index:i,count};ensure!(replay.fold(&source,i,levels,&noise,Some(&map),None)?,"scoring source refused");
        let coeff=coefficients(&replay,&sizes);let mut fields=core::canonical_fields(&replay.merge,&replay.fws,(!replay.beta.is_empty()).then_some(replay.beta.as_slice()));
        ensure!(ev["known4_sha256"]==json!(hashes(&replay.planes))&&ev["guide_sha256"]==field_hash(&replay.luma)
            &&ev["variance_sha256"]==field_hash(&replay.var)&&ev["beta"]==json!(replay.beta)
            &&ev["coefficients_sha256"]==json!(hashes(&coeff))&&ev["energy_sha256"]==json!(hashes(&fields.energy))
            &&ev["floor_sha256"]==json!(hashes(&fields.floor))&&ev["canonical_weight_sha256"]==json!(hashes(&fields.weights)),"actual source/probe/coefficient replay differs");
        let feature_clock=Instant::now();let feature=features(&replay,&sizes,&fields,levels.range());let feature_seconds=feature_clock.elapsed().as_secs_f64();
        let score_clock=Instant::now();fields.weights=bridge.score(i,&coeff,&feature)?;let score_seconds=score_clock.elapsed().as_secs_f64();
        drop(coeff);drop(feature);let add_clock=Instant::now();core::add_fields(&mut candidate,&replay.planes.iter().map(Vec::as_slice).collect::<Vec<_>>(),&fields,&mut candidate_ws);
        let add_seconds=add_clock.elapsed().as_secs_f64();ensure!(held_mean_hull(&replay.merge,&candidate,&sizes),"terminal mean/input hull changed");
        scored.push(json!({"index":i,"weight_sha256":hashes(&fields.weights),"feature_seconds":feature_seconds,
            "score_transaction_seconds":score_seconds,"native_add_seconds":add_seconds,"total_seconds":timer.elapsed().as_secs_f64(),"replay_exact":true}));
        let last=i==*scored_indices.last().unwrap();if last||(i+1)%plan.per_chunk==0{
            absorb_chunk(&mut replay_total,&mut replay.merge,crop.width,crop.height,4,cfg);absorb_chunk(&mut candidate_total,&mut candidate,crop.width,crop.height,4,cfg);
            if !last{replay.reset_chunk();candidate.reset_for_reuse();}}
        eprintln!("learned guide scored source{} {:.3}s",i,timer.elapsed().as_secs_f64());
    }Ok(())})?;
    let pass2_seconds=second_clock.elapsed().as_secs_f64();let server_finish=bridge.finish()?;drop(bridge);
    drop(replay);drop(candidate);drop(candidate_ws);
    ensure!(paths.iter().map(|p|stamp(p)).collect::<Result<Vec<_>>>()?==before&&file_hash(&config.warp_map)?==config.warp_map_sha256
        &&file_hash(&config.weights)?==config.weights_sha256&&file_hash(&config.score_server)?==config.score_server_sha256,"bound inputs changed");
    let mut receipt=json!({"schema":1,"phase":config.phase,"mode":config.mode,"status":if config.phase=="cost"{"COST_ONLY"}else{"COMPLETE"},
        "source_count":count,"probe_source_count":count,"frames":evidence,"scored":scored,"scored_indices":scored_indices,
        "map_sha256":config.warp_map_sha256,"crop":config.expected_crop,"native_dimensions":native,"plan":plan,"threads":threads,
        "pass1_seconds":pass1_seconds,"pass2_seconds":pass2_seconds,"first_decode_seconds":first_decode_seconds,
        "total_seconds":started.elapsed().as_secs_f64(),"weights_sha256":config.weights_sha256,"server_finish":server_finish});
    let common=json!({"baseline_sha256":baseline_sha256,"baseline_rgb16_le_sha256":baseline_rgb,
        "baseline_planes_sha256":baseline_planes_sha256,"baseline_cache":baseline_cache,"baseline_averaged_fraction":baseline_averaged_fraction,
        "resolved_development":resolved,"actual_tone_pinned":true,"baseline_pinned_rewrite_exact":true,
        "historical_tone_rgb_icc_exact":historical_match,"automatic_historical_rgb_match":historical_auto_match,
        "original_metadata_unchanged":true,"all_colour_site_support_checks":support,"generated_photographic_replay_admitted":false,
        "generic_consumer_sha256":config.generic_consumer_sha256,"score_server_sha256":config.score_server_sha256,
        "partial_candidate_emitted":false,"aligned_stack_materialized":false});
    receipt.as_object_mut().unwrap().extend(common.as_object().unwrap().clone());
    if config.phase=="full"{
        let repeated=replay_total.context("no canonical replay")?;let candidate=candidate_total.context("no candidate")?;
        ensure!(held_mean_hull(&base_total,&candidate,&sizes),"complete mean/hull changed");
        let repeated=pool.install(||repeated.finish(&mut Workspace::new(&sizes)));
        ensure!(hashes(&repeated)==baseline_planes_sha256,"full canonical CFA replay differs");
        let replay_path=config.out_dir.join("canonical-replay.tiff");pool.install(||pinned_write(&replay_path,&repeated,&cache_template,&resolved))?;
        ensure!(file_hash(&replay_path)?==file_hash(&pinned_path)?,"statistics/scoring observer changed full canonical TIFF");drop(repeated);
        let output=pool.install(||candidate.finish(&mut Workspace::new(&sizes)));let candidate_planes_sha256=hashes(&output);
        let candidate_cache=write_cache(&config.out_dir,"candidate",&output,&cache_template)?;let candidate_path=config.out_dir.join("candidate.tiff");
        pool.install(||pinned_write(&candidate_path,&output,&cache_template,&resolved))?;drop(output);
        ensure!(icc(&candidate_path)?==icc(&base_path)?,"candidate ICC differs");
        let result=json!({"candidate_sha256":file_hash(&candidate_path)?,"candidate_rgb16_le_sha256":rgb_hash(&candidate_path,native)?,
            "candidate_planes_sha256":candidate_planes_sha256,"candidate_cache":candidate_cache,
            "observer_canonical_tiff_exact":true,"terminal_mean_input_hull_exact":true});
        receipt.as_object_mut().unwrap().extend(result.as_object().unwrap().clone());
    }
    receipt["total_seconds"]=json!(started.elapsed().as_secs_f64());
    save(&config.out_dir.join("receipt.json"),&receipt)?;Ok(())
}

#[cfg(test)]
mod independent_controls {
    include!(concat!(env!("CARGO_MANIFEST_DIR"), "/../../experiments/cross-scale-band-guide/independent-bridge-controls.rs"));
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
