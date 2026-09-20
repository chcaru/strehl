// Explicit measurement export. No merge result, image development, or quality score.
use super::*;
use sha2::{Digest,Sha256};
use serde_json::{json,Value};
use std::{fs::File,io::{Read,Write}};
use phase_packed_rgb::full_stack::full_source_supported;

const SOURCE_INDICES:[usize;4]=[25,28,33,69];
const MAP_HASH:&str="84275850a032dc8beb88945b00514a58ebca433e267c8e10342ac55986cf830f";
const WITNESS_HASH:&str="45dee5d6ca1498337dbc88eef009406e964733b673f78c509791b9c17e5047ac";
const RECEIPT_HASH:&str="8489d681d94d6aa56bca54b8cfacc3cb302c964109cb9fe97d939cc4ec05cd26";
const CONFIG_HASH:&str="03d677617f4307516877cd34c5b2e155a3d3976b5ba135501e768e40fa98375f";
const WB_BITS:[u32;3]=[1070374912,1065353216,1076715520];
const MATRIX:[[f32;3];3]=[[0.746,-0.2365,-0.0588],[-0.5687,1.3442,0.2474],[-0.0624,0.1156,0.6584]];
// Output-quad coordinates, fixed before execution. Both original 192-square
// witness windows are wholly inside these wider, even-origin fields.
const WINDOWS:[(&str,[usize;4],[usize;4]);2]=[
    ("facet-edges",[1056,1196,512,512],[1250,1350,192,192]),
    ("dark-inclusion",[1284,818,512,512],[1525,925,192,192]),
];

fn digest(h:Sha256)->String{h.finalize().iter().map(|b|format!("{b:02x}")).collect()}
fn file_hash(path:&Path)->Result<String>{
    let mut f=File::open(path)?;let mut h=Sha256::new();let mut buf=vec![0u8;65536];
    loop{let n=f.read(&mut buf)?;if n==0{break}h.update(&buf[..n]);}Ok(digest(h))
}
fn field_hash(values:&[f32])->String{
    let mut h=Sha256::new();let mut buf=vec![0u8;65536];
    for chunk in values.chunks(buf.len()/4){
        for (dst,v) in buf.chunks_exact_mut(4).zip(chunk){dst.copy_from_slice(&v.to_bits().to_le_bytes());}
        h.update(&buf[..4*chunk.len()]);
    }digest(h)
}
fn source_hash(frame:&Frame)->String{
    let mut h=Sha256::new();let mut row=vec![0u8;2*frame.active.width];
    for y in 0..frame.active.height{
        for (dst,v) in row.chunks_exact_mut(2).zip(frame.active_row(y)){dst.copy_from_slice(&v.to_le_bytes());}
        h.update(&row);
    }digest(h)
}
fn stamp(path:&Path)->Result<(u64,std::time::SystemTime)>{let m=std::fs::metadata(path)?;Ok((m.len(),m.modified()?))}
fn patch(values:&[f32],width:usize,r:[usize;4])->Vec<f32>{
    (r[1]..r[1]+r[3]).flat_map(|y|values[y*width+r[0]..y*width+r[0]+r[2]].iter().copied()).collect()
}
fn save_field(directory:&Path,name:&str,planes:&[Vec<f32>])->Result<Value>{
    ensure!(!planes.is_empty() && planes.iter().all(|p|p.len()==512*512 && p.iter().all(|v|v.is_finite())),"export field shape/values");
    let path=directory.join(name);let mut f=std::fs::OpenOptions::new().write(true).create_new(true).open(&path)?;
    let mut bytes=vec![0u8;65536];
    for plane in planes{for chunk in plane.chunks(bytes.len()/4){
        for (dst,v) in bytes.chunks_exact_mut(4).zip(chunk){dst.copy_from_slice(&v.to_bits().to_le_bytes());}
        f.write_all(&bytes[..4*chunk.len()])?;
    }}drop(f);
    Ok(json!({"path":name,"shape":[planes.len(),512,512],"sha256":file_hash(&path)?,
        "plane_sha256":planes.iter().map(|p|field_hash(p)).collect::<Vec<_>>()}))
}
fn checked_json(path:&Path,hash:&str)->Result<Value>{
    ensure!(file_hash(path)?==hash,"held JSON changed: {}",path.display());
    Ok(serde_json::from_slice(&std::fs::read(path)?)?)
}
struct OneFrame<'a>{frame:&'a Frame,index:usize}
impl PyramidFrameSource for OneFrame<'_>{
    fn len(&self)->usize{70}
    fn decode(&self,index:usize)->Result<Frame>{ensure!(index==self.index,"unrequested source");Ok(self.frame.clone())}
}

#[test]
#[ignore="explicit four-source measurement export; parent freezes inputs and bounds resources"]
fn vitamin_c_wide_source_witness()->Result<()>{
    let started=Instant::now();
    let workspace=PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../..").canonicalize()?;
    let prior=workspace.join("experiments/donor-consistency/spatial-on-2");
    let config=checked_json(&prior.join("config.json"),CONFIG_HASH)?;
    let witness=checked_json(&prior.join("witness/receipt.json"),WITNESS_HASH)?;
    let receipt=checked_json(&prior.join("output/receipt.json"),RECEIPT_HASH)?;
    ensure!(witness["layout"]=="planar-y-x-f32le" && witness["plane_order"]==json!(["R","G1","G2","B"])
        && witness["native_dimensions"]==json!([6920,4612]),"held witness layout differs");
    let source_dir=PathBuf::from(config["source_dir"].as_str().context("held source directory")?);
    let map_path=PathBuf::from(config["warp_map"].as_str().context("held map path")?);
    ensure!(source_dir.is_absolute() && source_dir.file_name().and_then(|v|v.to_str())==Some("crystalized-vitamin-c-cpl")
        && file_hash(&map_path)?==MAP_HASH,"source/map scope differs");
    let out=PathBuf::from(std::env::var_os("STREHL_RELATIVE_BLUR_SOURCE_OUT").context("STREHL_RELATIVE_BLUR_SOURCE_OUT required")?);
    ensure!(out.is_absolute() && !out.exists(),"new absolute output directory required");
    ensure!(out.parent().context("output parent")?.canonicalize()?
        .starts_with(workspace.join("experiments/relative-blur-evidence").canonicalize()?),"output outside measurement directory");
    ensure!(align_cmd::fullres_gather_enabled() && gatefloor::enabled()
        && align_cmd::direct_plane_mode()?==align_cmd::DirectPlaneMode::Rounded
        && align_cmd::native_gpu_integration::gpu_gather_enabled()?,"actual rounded GPU/probe route required");
    ensure!(std::env::var_os("STREHL_LOCAL_PLACEMENT_FILE").is_none()
        && !std::env::var(strehl_core::demosaic::DEMOSAIC_ENV).is_ok_and(|v|v.eq_ignore_ascii_case("directional")),"held MHC/no-local-placement required");
    ensure!(strehl_core::pyramid::fine_support_candidate::environment_mode()==strehl_core::pyramid::fine_support_candidate::Mode::Off,
        "fine support candidate excluded");
    let paths=crate::raw_paths(&source_dir,None)?;
    ensure!(paths.len()==70 && paths.iter().enumerate().all(|(i,p)|p.file_name().and_then(|v|v.to_str())
        ==Some(format!("DSC{:05}.ARW",94+i).as_str())),"held seventy-source sequence differs");
    let before=paths.iter().map(|p|stamp(p)).collect::<Result<Vec<_>>>()?;
    let original=WarpMap::load(&map_path)?;
    original.check_stack(&StackIdentity::from_paths("crystalized-vitamin-c-cpl",&paths)?)?;
    ensure!(original.resampler()==Resampler::CatmullRom && original.len()==70 && original.placed_count()==70,"held complete map differs");
    let (map,fit)=align_cmd::cover_or_explain(original,align_cmd::CoverMode::Crop);
    let crop=fit.rect().context("held crop absent")?;let full=map.geometry();
    ensure!([crop.x,crop.y,crop.width,crop.height]==[28,19,3460,2306]
        && full==PlaneGeometry{width:3516,height:2344},"held full-domain gauge differs");
    for (name,r,old) in WINDOWS{
        ensure!(r[0]%2==0 && r[1]%2==0 && r[0]+r[2]<=crop.width && r[1]+r[3]<=crop.height
            && old[0]>=r[0] && old[1]>=r[1] && old[0]+old[2]<=r[0]+r[2] && old[1]+old[3]<=r[1]+r[3],"window/support mismatch");
        let retained=witness["windows"].as_array().context("held windows")?.iter().find(|w|w["name"]==name).context("held region")?;
        ensure!(retained["quad_xywh"]==json!(old),"held old window moved");
    }
    let cfg=MergeConfig::default();let pool=ThreadPoolBuilder::new().num_threads(8).build()?;
    std::fs::create_dir(&out)?;let mut groups=Vec::new();
    for index in SOURCE_INDICES{
        let source_start=Instant::now();let frame=strehl_raw::decode(&paths[index])?;
        validate_pyramid_frame(&frame,full,index)?;
        let gains=[frame.wb_coeffs[0]/frame.wb_coeffs[1],1.0,frame.wb_coeffs[2]/frame.wb_coeffs[1]];
        ensure!(frame.camera=="ILCE-7CM2" && frame.iso==Some(100.0) && frame.levels==Levels{black:512.0,white:15360.0}
            && frame.active.x==0 && frame.active.y==0 && frame.active.width==7032 && frame.active.height==4688
            && gains.map(f32::to_bits)==WB_BITS && frame.xyz_to_cam_rgb()==Some(MATRIX),"source metadata differs");
        let identity=strehl_raw::identity(&paths[index]);
        let ca=strehl_core::optics::profile_for_capture_env(identity.model.as_deref(),identity.lens_type3)?;
        ensure!(ca.is_some_and(|p|p.key=="a7c2-fe100gm-2xtc-x4cpl")
            && full_source_supported(map.placement(index)?,full,crop,ca),"held CA pull differs");
        let old_group=witness["groups"].as_array().context("held source groups")?.iter()
            .find(|g|g["index0"].as_u64()==Some(index as u64)).context("held source witness absent")?;
        let old_row=receipt["frame_evidence"].as_array().context("held frame evidence")?.iter()
            .find(|r|r["index"].as_u64()==Some(index as u64)).context("held frame row absent")?;
        let active_hash=source_hash(&frame);
        ensure!(old_row["source_active_u16_sha256"]==active_hash,"original active source differs");
        let noise=profile::noise_model_for(&frame.camera,frame.iso,frame.levels);
        let mut worker=BandWorker::new(PyramidDomain::cropped(full,crop)?,cfg);
        ensure!(pool.install(||worker.fold(&OneFrame{frame:&frame,index},index,frame.levels,&noise,Some(&map),None))?,"actual consumer refused source");
        let full_hashes=worker.planes.iter().map(|p|field_hash(p)).collect::<Vec<_>>();
        ensure!(old_group["actual_known4_sha256"]==json!(full_hashes) && old_row["actual_known4_sha256"]==json!(full_hashes),"full actual known4 differs from retained consumer");
        let guide_hash=field_hash(&worker.luma);let variance_hash=field_hash(&worker.var);
        ensure!(old_row["guide_sha256"]==guide_hash && old_row["variance_sha256"]==variance_hash,"actual guide/variance differs from retained consumer");
        let old_beta=old_row["beta"].as_array().context("held beta")?;
        ensure!(old_beta.len()==worker.beta.len() && old_beta.iter().zip(&worker.beta)
            .all(|(a,b)|a.as_f64().is_some_and(|v|(v as f32).to_bits()==b.to_bits())),"actual injected beta differs");
        let mut artifacts=Vec::new();
        for (name,r,old) in WINDOWS{
            let known=worker.planes.iter().map(|p|patch(p,crop.width,r)).collect::<Vec<_>>();
            let old_artifact=old_group["artifacts"].as_array().context("held artifacts")?.iter()
                .find(|a|a["field"]=="source-known4" && a["region"]==name).context("held known4 artifact")?;
            ensure!(old_artifact["shape"]==json!([4,192,192]),"held known4 shape differs");
            let old_path=prior.join("witness").join(old_artifact["path"].as_str().context("held artifact path")?);
            ensure!(file_hash(&old_path)?==old_artifact["sha256"].as_str().context("held artifact hash")?,"held known4 file changed");
            let inner=[old[0]-r[0],old[1]-r[1],old[2],old[3]];
            let overlap=known.iter().flat_map(|p|patch(p,r[2],inner)).flat_map(|v|v.to_bits().to_le_bytes()).collect::<Vec<_>>();
            ensure!(overlap==std::fs::read(&old_path)?,"wide export overlap is not bit-exact with old actual witness");
            let stem=format!("source-{index:02}-{name}");
            let known_ref=save_field(&out,&format!("{stem}-known4.f32"),&known)?;
            let guide_ref=save_field(&out,&format!("{stem}-guide.f32"),&[patch(&worker.luma,crop.width,r)])?;
            let variance_ref=save_field(&out,&format!("{stem}-variance.f32"),&[patch(&worker.var,crop.width,r)])?;
            artifacts.push(json!({"region":name,"output_quad_xywh":r,
                "output_native_xywh":[2*r[0],2*r[1],2*r[2],2*r[3]],
                "reference_active_native_xywh":[2*(crop.x+r[0]),2*(crop.y+r[1]),2*r[2],2*r[3]],
                "known4":known_ref,"guide":guide_ref,"variance":variance_ref,
                "old_overlap_quad_xywh":old,"old_overlap_sha256":old_artifact["sha256"],"old_overlap_bit_exact":true}));
        }
        ensure!(source_hash(&frame)==active_hash && full_hashes==worker.planes.iter().map(|p|field_hash(p)).collect::<Vec<_>>(),"export mutated source or gather");
        let t=map.placement(index)?;
        groups.push(json!({"source_index0":index,"source_path":paths[index],"source_active_u16_sha256":active_hash,
            "full_known4_sha256":full_hashes,"full_guide_sha256":guide_hash,"full_variance_sha256":variance_hash,"beta":worker.beta,
            "transform_bits":([t.a.re,t.a.im,t.b.re,t.b.im].map(|v|format!("{:016x}",v.to_bits()))),
            "active":[frame.active.x,frame.active.y,frame.active.width,frame.active.height],"stride":frame.stride,
            "buffer_height":frame.buffer_height,"raw_wb_bits":frame.wb_coeffs.map(f32::to_bits),
            "artifacts":artifacts,"seconds":source_start.elapsed().as_secs_f64()}));
        eprintln!("relative blur source witness {index}: {:.2}s",source_start.elapsed().as_secs_f64());
    }
    ensure!(paths.iter().zip(&before).all(|(p,b)|stamp(p).is_ok_and(|a|a==*b)) && file_hash(&map_path)?==MAP_HASH,"original metadata/map changed");
    let record=json!({"schema":1,"scope":"actual full-domain gathered measurements only; no blur model, image, or quality claim",
        "source_indices":SOURCE_INDICES,"source_dir":source_dir,"map":map_path,"map_sha256":MAP_HASH,
        "prior_witness_sha256":WITNESS_HASH,"prior_full_receipt_sha256":RECEIPT_HASH,"prior_config_sha256":CONFIG_HASH,
        "full_source_quad_dimensions":[full.width,full.height],"crop_quad_xywh":[crop.x,crop.y,crop.width,crop.height],
        "native_dimensions":[6920,4612],"plane_order":["R","G1","G2","B"],"layout":"planar-y-x-f32le",
        "known4_units":"black-subtracted source DN; actual rounded MHC/Catmull/CA consumer",
        "guide_units":"same actual green guide DN","variance_units":"actual injected guide variance DN squared; not independently calibrated patch noise",
        "levels":[512,15360],"wb_bits":WB_BITS,"matrix":MATRIX,"development_applied":false,
        "merge_config":format!("{cfg:?}"),"execution_threads":8,"original_metadata_unchanged":true,
        "groups":groups,"seconds":started.elapsed().as_secs_f64()});
    let mut f=std::fs::OpenOptions::new().write(true).create_new(true).open(out.join("receipt.json"))?;
    serde_json::to_writer_pretty(&mut f,&record)?;writeln!(f)?;Ok(())
}
