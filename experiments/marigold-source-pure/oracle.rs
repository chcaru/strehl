// Bounded source-purity counterfactual, not an automatic merge algorithm.
// Included only in merge_cmd's explicitly enabled test build.
use super::*;
use crate::image_out::highlight_rendering::{self as rendering, Arm};
use full_stack_source_prior::CacheMetadata;
use serde::{Deserialize, Serialize};
use serde_json::{json, Value};
use sha2::{Digest, Sha256};
use std::{fs::File, io::{Read, Write}};

const CORE: [usize; 4] = [3230, 3000, 384, 384];
const OUTER: [usize; 4] = [3198, 2968, 448, 448];
const RGB_SUPPORT: [usize; 4] = [3196, 2966, 452, 452]; // MHC radius two native pixels.
const INDICES: [usize; 3] = [112, 152, 320];
const SOURCE_SHA: [&str; 3] = [
    "d61479b87463522b43dea20cddd94c7af15b4080545b993794e799f15da028c7",
    "fc268680728e15ee76c2fb117046a5a3282e1f4fc12b3c928a8c7456ef012d38",
    "ff52e26157c3ed95d7a2a14ffd1e215538f5b030e915c82fd198523e55b5485f",
];
#[derive(Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
struct Input { index: usize, path: PathBuf, identity_name: String, bytes: u64, sha256: String }
#[derive(Deserialize)]
struct Recipe { stack_name: String, inputs: Vec<Input>, warp_map: PathBuf, warp_map_sha256: String,
    expected_camera: String, expected_iso: f32 }
#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct Config { schema: u32, recipe: PathBuf, recipe_sha256: String, cache: PathBuf,
    cache_sha256: String, full_receipt: PathBuf, full_receipt_sha256: String,
    expected_current_tiff: PathBuf, expected_current_file_sha256: String, out_dir: PathBuf }

fn hex(h: Sha256) -> String { h.finalize().iter().map(|x| format!("{x:02x}")).collect() }
fn bytes_hash(v: &[u8]) -> String { let mut h=Sha256::new();h.update(v);hex(h) }
fn file_hash(path: &Path) -> Result<String> {
    let mut f=File::open(path)?; let mut h=Sha256::new();let mut b=[0u8;65536];
    loop {let n=f.read(&mut b)?;if n==0{break;}h.update(&b[..n]);} Ok(hex(h))
}
fn field_hash(v: &[f32]) -> String {
    let mut h=Sha256::new();let mut b=[0u8;65536];
    for row in v.chunks(b.len()/4) {for(dst,x) in b.chunks_exact_mut(4).zip(row){dst.copy_from_slice(&x.to_bits().to_le_bytes());}h.update(&b[..row.len()*4]);}hex(h)
}
fn plane_hashes(v: &[Vec<f32>]) -> Vec<String> {v.iter().map(|p|field_hash(p)).collect()}
fn raw_hash(f: &Frame) -> String {
    let mut h=Sha256::new();let mut row=vec![0u8;2*f.active.width];
    for y in 0..f.active.height {for(dst,x) in row.chunks_exact_mut(2).zip(f.active_row(y)){dst.copy_from_slice(&x.to_le_bytes());}h.update(&row);}hex(h)
}
fn save(path: &Path, value: &Value) -> Result<()> {
    let mut f=std::fs::OpenOptions::new().write(true).create_new(true).open(path)?;
    serde_json::to_writer_pretty(&mut f,value)?;writeln!(f)?;Ok(())
}
struct Rgb { w: usize, h: usize, pixels: Vec<u16>, icc: Vec<u8> }
fn image(path: &Path) -> Result<Rgb> {
    let mut d=tiff::decoder::Decoder::new(std::io::BufReader::new(File::open(path)?))?;
    let(w,h)=d.dimensions()?;ensure!(d.colortype()?==tiff::ColorType::RGB(16),"RGB16 required");
    let icc=d.get_tag_u8_vec(tiff::tags::Tag::IccProfile)?;ensure!(!icc.is_empty(),"ICC required");
    let pixels=match d.read_image()?{tiff::decoder::DecodingResult::U16(v)=>v,_=>bail!("RGB16 required")};
    ensure!(pixels.len()==w as usize*h as usize*3&&!d.more_images(),"TIFF shape/pages changed");
    Ok(Rgb{w:w as usize,h:h as usize,pixels,icc})
}
fn rgb_hash(v: &[u16]) -> String {let mut h=Sha256::new();let mut b=[0u8;65536];
    for row in v.chunks(b.len()/2){for(dst,x)in b.chunks_exact_mut(2).zip(row){dst.copy_from_slice(&x.to_le_bytes());}h.update(&b[..row.len()*2]);}hex(h)}
fn same_image(a:&Rgb,b:&Rgb)->bool {a.w==b.w&&a.h==b.h&&a.icc==b.icc&&a.pixels==b.pixels}
fn inside(x:usize,y:usize,r:[usize;4])->bool{x>=r[0]&&y>=r[1]&&x<r[0]+r[2]&&y<r[1]+r[3]}
fn outside_changes(a:&Rgb,b:&Rgb,r:[usize;4])->Result<usize>{
    ensure!(a.w==b.w&&a.h==b.h&&a.icc==b.icc,"RGB comparison metadata changed");
    Ok(a.pixels.chunks_exact(3).zip(b.pixels.chunks_exact(3)).enumerate()
        .filter(|(i,(x,y))|!inside(i%a.w,i/a.w,r)&&x!=y).count())
}

// Shared across all CFA planes; 1 in the full 384-square core, a fixed
// Chebyshev-distance smoothstep ring, 0 beyond the 448-square support.
fn mask(qx:usize,qy:usize,enabled:bool)->f32 {
    if !enabled{return 0.0;}
    let(x,y)=(2.0*qx as f32+0.5,2.0*qy as f32+0.5);
    let dx=(CORE[0] as f32-x).max(x-(CORE[0]+CORE[2]) as f32).max(0.0);
    let dy=(CORE[1] as f32-y).max(y-(CORE[1]+CORE[3]) as f32).max(0.0);
    let t=((32.0-dx.max(dy))/32.0).clamp(0.0,1.0);t*t*(3.0-2.0*t)
}
// A patch is the four gathered source planes restricted to OUTER. No image
// analysis, selected pixel argmax, AC decomposition, or new range clamp.
fn patch(planes:&[Vec<f32>],width:usize)->Vec<Vec<f32>> {
    planes.iter().map(|p|{let mut v=Vec::with_capacity(224*224);
        for y in OUTER[1]/2..(OUTER[1]+OUTER[3])/2 {v.extend_from_slice(&p[y*width+OUTER[0]/2..y*width+(OUTER[0]+OUTER[2])/2]);}v}).collect()
}
fn replace(planes:&mut[Vec<f32>],width:usize,donor:&[Vec<f32>],enabled:bool)->Result<()> {
    ensure!(planes.len()==4&&donor.len()==4&&donor.iter().all(|p|p.len()==224*224&&p.iter().all(|v|v.is_finite())),"donor patch invalid");
    for ly in 0..224 {for lx in 0..224 {let(x,y)=(OUTER[0]/2+lx,OUTER[1]/2+ly);let a=mask(x,y,enabled);
        if a==0.0{continue;}for c in 0..4 {let i=y*width+x;let d=donor[c][ly*224+lx];
            planes[c][i]=if a==1.0{d}else{(1.0-a)*planes[c][i]+a*d};}
    }}Ok(())
}

// The only duplicated writer operations are explicit restore=None RGGB
// interleave and norm(v,g)=v*g*eg/range from actual write_merged. The actual
// image_out writer performs MHC/colour/tone/TIFF. The exact complete baseline
// gate below is mandatory; this helper is not a general rendering API.
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
struct One<'a>{frame:&'a Frame,index:usize,count:usize}
impl PyramidFrameSource for One<'_>{fn len(&self)->usize{self.count}
    fn decode(&self,index:usize)->Result<Frame>{ensure!(index==self.index,"unexpected source decode request");Ok(self.frame.clone())}}

#[test]
fn mask_and_support_controls()->Result<()> {
    let(w,h)=(1840,1730);let baseline=(0..4).map(|p|vec![p as f32-7.0;w*h]).collect::<Vec<_>>();
    let donor=(0..4).map(|p|(0..224*224).map(|i|20.0+p as f32*65536.0+i as f32).collect::<Vec<_>>()).collect::<Vec<_>>();
    let mut zero=baseline.clone();replace(&mut zero,w,&donor,false)?;
    ensure!(plane_hashes(&zero)==plane_hashes(&baseline),"zero placebo changes bits");drop(zero);
    let mut changed=baseline.clone();replace(&mut changed,w,&donor,true)?;
    let(mut core,mut ring,mut outside)=(0,0,0);
    for y in 0..h {for x in 0..w {let a=mask(x,y,true);
        if inside(2*x,2*y,CORE){ensure!(a==1.0,"incomplete core");core+=1;}
        else if inside(2*x,2*y,OUTER){ensure!(a>0.0&&a<1.0,"ring invalid");ring+=1;}
        else{ensure!(a==0.0,"mask escaped support");outside+=1;}
        for p in 0..4{let i=y*w+x;if a==1.0{let j=(y-OUTER[1]/2)*224+x-OUTER[0]/2;ensure!(changed[p][i].to_bits()==donor[p][j].to_bits(),"core not source-pure at matching donor location");}
            if a==0.0{ensure!(changed[p][i].to_bits()==baseline[p][i].to_bits(),"outside CFA changed");}}
    }}ensure!(core==192*192&&ring==224*224-core&&outside>0,"fixture lacks core/ring/outside");
    // The outside-RGB detector must reject a changed pixel, not merely return
    // zero on two identical images. An inside change remains allowed.
    let a=Rgb{w:8,h:8,pixels:vec![1;8*8*3],icc:vec![42]};
    let mut b=Rgb{w:a.w,h:a.h,pixels:a.pixels.clone(),icc:a.icc.clone()};
    b.pixels[(3*8+3)*3]=2;ensure!(outside_changes(&a,&b,[2,2,4,4])?==0,"inside mutation rejected");
    b.pixels[0]=2;ensure!(outside_changes(&a,&b,[2,2,4,4])?==1,"outside destroyer undetected");Ok(())
}

#[test]
#[ignore="root-run fixed three-RAW source-purity counterfactual; explicit corrected cache"]
fn three_source_oracle()->Result<()> {
    let started=Instant::now();let config_path=PathBuf::from(std::env::var_os("STREHL_MARIGOLD_SOURCE_PURE_CONFIG").context("config required")?);
    let cfg:Config=serde_json::from_slice(&std::fs::read(&config_path)?)?;
    ensure!(cfg.schema==1,"schema mismatch");
    for(p,expected)in [(&cfg.recipe,&cfg.recipe_sha256),(&cfg.cache,&cfg.cache_sha256),
        (&cfg.full_receipt,&cfg.full_receipt_sha256),(&cfg.expected_current_tiff,&cfg.expected_current_file_sha256)]{
        ensure!(p.is_absolute()&&file_hash(p)?==*expected,"binding changed: {}",p.display());}
    let recipe:Recipe=serde_json::from_slice(&std::fs::read(&cfg.recipe)?)?;
    let receipt:Value=serde_json::from_slice(&std::fs::read(&cfg.full_receipt)?)?;
    let(m,planes)=full_stack_source_prior::read_cache(&cfg.cache)?;
    ensure!(m.phase=="full"&&m.frames==488&&m.reference==244&&m.crop==[191,128,3134,2088]
        &&["baseline","candidate"].contains(&m.arm.as_str()),"wrong full marigold cache/domain");
    let prefix=&m.arm;let evidence=receipt["frames"].as_array().context("source evidence absent")?;
    ensure!(receipt["phase"]=="full"&&receipt["source_count"]==488&&receipt["probe_source_count"]==488
        &&receipt["original_metadata_unchanged"]==true&&evidence.len()==488
        &&evidence.iter().enumerate().all(|(i,r)|r["index"]==json!(i)),"not complete ordered source evidence");
    let bound=&receipt[format!("{prefix}_cache")];
    ensure!(bound["sha256"]==json!(cfg.cache_sha256)&&bound["binary_sha256"]==json!(m.binary_sha256)
        &&PathBuf::from(bound["path"].as_str().context("cache path absent")?).canonicalize()?==cfg.cache.canonicalize()?
        &&receipt[format!("{prefix}_planes_sha256")]==json!(m.plane_sha256),"cache not bound by complete receipt");
    ensure!(recipe.inputs.len()==488&&recipe.inputs.iter().enumerate().all(|(i,r)|r.index==i)
        &&bytes_hash(&serde_json::to_vec(&recipe.inputs)?)==m.input_order_sha256
        &&recipe.warp_map_sha256==m.map_sha256&&file_hash(&recipe.warp_map)?==m.map_sha256
        &&receipt["map_sha256"]==json!(m.map_sha256),"source order/map differs");
    ensure!(std::env::var("STREHL_CA_BEFORE_MHC").ok().as_deref()==Some("off")
        &&strehl_core::pyramid::fine_support_candidate::environment_mode()==strehl_core::pyramid::fine_support_candidate::Mode::Off
        &&align_cmd::fullres_gather_enabled()&&gatefloor::enabled()
        &&align_cmd::direct_plane_mode()?==align_cmd::DirectPlaneMode::Rounded
        &&align_cmd::native_gpu_integration::gpu_gather_enabled()?,"held current gather required");
    ensure!(std::env::var_os("STREHL_LOCAL_PLACEMENT_FILE").is_none()&&std::env::var_os("STREHL_ONLY_FRAME").is_none()
        &&std::env::var_os(strehl_core::highlight::KNEE_ENV).is_none()
        &&!std::env::var(strehl_core::demosaic::DEMOSAIC_ENV).is_ok_and(|v|v.eq_ignore_ascii_case("directional"))
        &&matched_source_tests::pinned_tone().is_none(),"competing overrides forbidden");
    let original=WarpMap::load(&recipe.warp_map)?;
    let entries=recipe.inputs.iter().map(|r|(r.identity_name.as_str(),r.bytes)).collect::<Vec<_>>();
    original.check_stack(&StackIdentity::from_entries(&recipe.stack_name,&entries))?;
    ensure!(original.len()==488&&original.placed_count()==488&&original.resampler()==Resampler::CatmullRom
        &&original.provenance().reference==m.reference,"placement contract differs");
    let(map,fit)=align_cmd::cover_or_explain(original,align_cmd::CoverMode::Crop);
    let crop=fit.rect().context("crop absent")?;ensure!([crop.x,crop.y,crop.width,crop.height]==m.crop&&map.geometry()==m.domain()?.full,"map/cache domain differs");
    let here=PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../../experiments/marigold-source-pure").canonicalize()?;
    ensure!(!cfg.out_dir.exists()&&cfg.out_dir.parent().context("output parent")?.canonicalize()?.starts_with(&here),"fresh owned output required");
    std::fs::create_dir(&cfg.out_dir)?;
    let pool=ThreadPoolBuilder::new().num_threads(8).build()?;
    let baseline_path=cfg.out_dir.join("baseline.tiff");
    let(_,resolved)=pool.install(||rendering::with_arm(Arm::Current,||write_merged(Merged::Bands{domain:m.domain()?,planes:&planes},
        m.levels(),m.wb(),m.xyz().as_ref(),image_out::OutputSpace::Srgb,true,m.exposure()?,None,&baseline_path)))?;
    let baseline=image(&baseline_path)?;let expected=image(&cfg.expected_current_tiff)?;
    ensure!(same_image(&baseline,&expected)&&rgb_hash(&baseline.pixels)==receipt[format!("{prefix}_rgb16_le_sha256")].as_str().context("full pixels hash absent")?,"actual cache replay differs from selected full baseline");drop(expected);
    let mut zero=planes.clone();let placebo=(0..4).map(|p|vec![-111.0+p as f32;224*224]).collect::<Vec<_>>();
    replace(&mut zero,m.crop[2],&placebo,false)?;
    ensure!(plane_hashes(&zero)==m.plane_sha256,"zero mask changed CFA bits");
    let zero_path=cfg.out_dir.join("zero-placebo.tiff");pool.install(||pinned_write(&zero_path,&zero,&m,&resolved))?;drop(zero);
    ensure!(same_image(&baseline,&image(&zero_path)?),"pinned writer/zero placebo failed full RGB16+ICC identity");
    save(&cfg.out_dir.join("baseline-verified.json"),&json!({"resolved_development":resolved,"cache":cfg.cache,"cache_sha256":cfg.cache_sha256,
        "actual_writer_pixels_and_icc_exact":true,"zero_mask_cfa_exact":true,"zero_mask_rgb16_and_icc_exact":true,
        "baseline_sha256":file_hash(&baseline_path)?,"zero_placebo_sha256":file_hash(&zero_path)?,"raw_reads":0}))?;
    let noise=profile::noise_model_for(&recipe.expected_camera,Some(recipe.expected_iso),m.levels());ensure!(noise.is_trustworthy(),"noise profile untrusted");
    let mut worker=BandWorker::new(m.domain()?,MergeConfig::default());let mut donors=Vec::new();let mut source_records=Vec::new();
    for(slot,index)in INDICES.into_iter().enumerate(){
        let input=&recipe.inputs[index];let before=std::fs::metadata(&input.path)?;
        ensure!(input.path.is_absolute()&&input.sha256==SOURCE_SHA[slot]&&before.len()==input.bytes&&file_hash(&input.path)?==input.sha256,"frozen donor file differs");
        let frame=strehl_raw::decode(&input.path)?; // Exactly three actual RAW decode calls, no other decode route.
        ensure!(frame.camera==recipe.expected_camera&&frame.iso==Some(recipe.expected_iso)&&frame.geometry()==m.domain()?.full
            &&frame.active.width==7032&&frame.active.height==4688&&frame.levels==m.levels()
            &&frame.wb_gains().map(|v|v.map(f32::to_bits))==m.wb_gains_bits
            &&frame.xyz_to_cam_rgb_with_source().map(|v|v.0.map(|r|r.map(f32::to_bits)))==m.xyz_to_cam_bits,"donor capture metadata differs");
        let active=raw_hash(&frame);ensure!(evidence[index]["active_u16_sha256"]==json!(active),"actual decoder differs from full receipt");
        let source=One{frame:&frame,index,count:488};
        ensure!(pool.install(||worker.fold(&source,index,m.levels(),&noise,Some(&map),None))?,"donor gather refused");
        let known=plane_hashes(&worker.planes);
        ensure!(evidence[index]["known4_sha256"]==json!(known)&&worker.planes.iter().flatten().all(|v|v.is_finite()),"actual four-plane gather differs from full receipt");
        donors.push(patch(&worker.planes,m.crop[2]));
        ensure!(raw_hash(&frame)==active,"gather mutated retained RAW");worker.reset_chunk();
        let after=std::fs::metadata(&input.path)?;ensure!(before.len()==after.len()&&before.modified()?==after.modified()?
            &&file_hash(&input.path)?==input.sha256,"original file changed");
        source_records.push(json!({"index":index,"path":input.path,"file_sha256":input.sha256,"active_u16_sha256":active,
            "known4_sha256":known,"full_receipt_match":true,"original_unchanged":true}));
    }drop(worker);
    let mut arms=Vec::new();
    for(slot,index)in INDICES.into_iter().enumerate(){let mut candidate=planes.clone();replace(&mut candidate,m.crop[2],&donors[slot],true)?;
        // Check every CFA location outside the actual support, before MHC.
        for p in 0..4 {ensure!(candidate[p].iter().zip(&planes[p]).enumerate().all(|(i,(a,b))|
            inside(2*(i%m.crop[2]),2*(i/m.crop[2]),OUTER)||a.to_bits()==b.to_bits()),"CFA escaped mask");}
        let name=format!("donor-{index}");let path=cfg.out_dir.join(format!("{name}.tiff"));
        pool.install(||pinned_write(&path,&candidate,&m,&resolved))?;let output=image(&path)?;
        ensure!(outside_changes(&baseline,&output,RGB_SUPPORT)?==0,"RGB escaped fixed MHC support");
        arms.push(json!({"name":name,"index":index,"file":path,"sha256":file_hash(&path)?,"rgb16_le_sha256":rgb_hash(&output.pixels),
            "outside_cfa_exact":true,"outside_rgb_support_exact":true,"negative_control":index==320}));
    }
    ensure!(plane_hashes(&planes)==m.plane_sha256&&file_hash(&cfg.cache)?==cfg.cache_sha256
        &&file_hash(&cfg.full_receipt)?==cfg.full_receipt_sha256&&file_hash(&recipe.warp_map)?==m.map_sha256,"retained bindings changed");
    save(&cfg.out_dir.join("receipt.json"),&json!({"schema":1,"status":"COMPLETE_FIXED_THREE_DONOR_ORACLE",
        "cache":cfg.cache,"cache_sha256":cfg.cache_sha256,"full_receipt":cfg.full_receipt,"full_receipt_sha256":cfg.full_receipt_sha256,
        "source_count":488,"raw_decode_count":3,"indices":INDICES,"sources":source_records,"arms":arms,
        "core_native_xywh":CORE,"outer_native_xywh":OUTER,"rgb_support_native_xywh":RGB_SUPPORT,
        "baseline_file":"baseline.tiff","baseline_sha256":file_hash(&baseline_path)?,"baseline_rgb16_le_sha256":rgb_hash(&baseline.pixels),
        "icc_sha256":bytes_hash(&baseline.icc),"native_dimensions":[baseline.w,baseline.h],"resolved_development":resolved,
        "zero_mask_rgb16_and_icc_exact":true,"baseline_cache_unchanged":true,"total_seconds":started.elapsed().as_secs_f64(),
        "visual_verdict":null,"scope":"Manual complete-CFA source-purity counterfactual, not an automatic method, quality claim, or SOTA qualification."}))?;
    Ok(())
}
