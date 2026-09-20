// Bounded read-only source measurements; no source election or image output.
use super::*;
use serde::Serialize;
use serde_json::{json, Value};
use sha2::{Digest, Sha256};
use std::{fs::File, io::{Read, Write}};
use strehl_core::pyramid::{LevelSize, Pyramid, Workspace};
use phase_packed_rgb::full_stack::full_source_supported;

const MAP_HASH: &str = "84275850a032dc8beb88945b00514a58ebca433e267c8e10342ac55986cf830f";
const OLD_WIDE_HASH: &str = "cbf028ae17deb80c79fb388e1b515c614e1290ec6406ab7445c75b4c44d0ee15";
const CONFIG_HASH: &str = "03d677617f4307516877cd34c5b2e155a3d3976b5ba135501e768e40fa98375f";
const WB_BITS: [u32; 3] = [1070374912, 1065353216, 1076715520];
const MATRIX: [[f32; 3]; 3] = [[0.746,-0.2365,-0.0588],[-0.5687,1.3442,0.2474],[-0.0624,0.1156,0.6584]];
const WINDOWS: [(&str, [usize; 4]); 2] = [
    ("facet-edges", [1056,1196,512,512]),
    ("dark-inclusion", [1284,818,512,512]),
];

#[derive(Clone, Debug, Serialize)]
pub struct PlaneSummary {
    pub count: usize,
    pub mean_dn: f32,
    pub mean_l0: f32,
    pub mean_energy: f32,
    pub checker_count: [usize; 2],
    pub checker_mean_dn: [f32; 2],
    pub checker_mean_l0: [f32; 2],
    pub mean_guide: f32,
    pub mean_guide_variance: f32,
}

/// Fixed row-major f32 accumulation. Coordinates are cropped output quads;
/// parity_origin converts them to active-reference global quad checkerboards.
/// Only addressed samples are read. Subsets are sensitivity checks, not repeats.
pub fn summarize_roi(known: &[f32], l0: &[f32], energy: &[f32], guide: &[f32],
    variance: &[f32], size: LevelSize, roi: [usize;4], parity_origin: [usize;2])
    -> Result<PlaneSummary> {
    let n = size.width.checked_mul(size.height).context("field dimensions overflow")?;
    ensure!(n > 0 && [known,l0,energy,guide,variance].iter().all(|a|a.len()==n), "field shape");
    let [x,y,w,h] = roi;
    ensure!(w > 0 && h > 0 && x.checked_add(w).is_some_and(|v|v<=size.width)
        && y.checked_add(h).is_some_and(|v|v<=size.height), "ROI bounds");
    let mut sums = [0.0f32;5]; let mut counts = [0usize;2];
    let mut half_dn = [0.0f32;2]; let mut half_l0 = [0.0f32;2];
    for yy in y..y+h { for xx in x..x+w {
        let j=yy*size.width+xx;
        let values=[known[j],l0[j],energy[j],guide[j],variance[j]];
        ensure!(values.iter().all(|v|v.is_finite()) && energy[j]>=0.0 && variance[j]>=0.0,
            "nonfinite field or negative energy/guide variance");
        for k in 0..5 { sums[k]+=values[k]; }
        let parity=((xx&1) ^ (yy&1) ^ (parity_origin[0]&1) ^ (parity_origin[1]&1)) & 1;
        counts[parity]+=1; half_dn[parity]+=known[j]; half_l0[parity]+=l0[j];
    }}
    ensure!(counts.iter().all(|&v|v>0) && sums.iter().chain(&half_dn).chain(&half_l0).all(|v|v.is_finite()),
        "empty checkerboard subset or overflowing sum");
    let count=w*h; let inv=1.0/count as f32;
    Ok(PlaneSummary {count,mean_dn:sums[0]*inv,mean_l0:sums[1]*inv,
        mean_energy:sums[2]*inv,checker_count:counts,
        checker_mean_dn:[half_dn[0]/counts[0] as f32,half_dn[1]/counts[1] as f32],
        checker_mean_l0:[half_l0[0]/counts[0] as f32,half_l0[1]/counts[1] as f32],
        mean_guide:sums[3]*inv,mean_guide_variance:sums[4]*inv})
}

fn digest(h: Sha256)->String { h.finalize().iter().map(|b|format!("{b:02x}")).collect() }
fn file_hash(path:&Path)->Result<String> {
    let mut f=File::open(path)?; let mut h=Sha256::new(); let mut b=vec![0u8;65536];
    loop {let n=f.read(&mut b)?;if n==0 {break}h.update(&b[..n]);} Ok(digest(h))
}
fn field_hash(values:&[f32])->String {
    let mut h=Sha256::new();let mut b=vec![0u8;65536];
    for chunk in values.chunks(b.len()/4) {
        for (dst,v) in b.chunks_exact_mut(4).zip(chunk) {dst.copy_from_slice(&v.to_bits().to_le_bytes());}
        h.update(&b[..4*chunk.len()]);
    } digest(h)
}
fn source_hash(frame:&Frame)->String {
    let mut h=Sha256::new();let mut row=vec![0u8;2*frame.active.width];
    for y in 0..frame.active.height {
        for (dst,v) in row.chunks_exact_mut(2).zip(frame.active_row(y)) {dst.copy_from_slice(&v.to_le_bytes());}
        h.update(&row);
    } digest(h)
}
fn stamp(path:&Path)->Result<(u64,std::time::SystemTime)> {let m=std::fs::metadata(path)?;Ok((m.len(),m.modified()?))}
fn checked_json(path:&Path, hash:&str)->Result<Value> {
    ensure!(file_hash(path)?==hash,"held JSON changed: {}",path.display());
    Ok(serde_json::from_slice(&std::fs::read(path)?)?)
}
fn patch(values:&[f32],width:usize,r:[usize;4])->Vec<f32> {
    (r[1]..r[1]+r[3]).flat_map(|y|values[y*width+r[0]..y*width+r[0]+r[2]].iter().copied()).collect()
}
struct OneFrame<'a> {frame:&'a Frame,index:usize}
impl PyramidFrameSource for OneFrame<'_> {
    fn len(&self)->usize {70}
    fn decode(&self,index:usize)->Result<Frame> {ensure!(index==self.index,"unrequested source");Ok(self.frame.clone())}
}

#[derive(Clone, Debug, Serialize)]
pub struct RoiSpec {
    pub name: &'static str,
    pub window: &'static str,
    pub local_quad_xywh: [usize;4],
    pub output_quad_xywh: [usize;4],
    pub role: &'static str,
}
pub fn roi_specs()->Vec<RoiSpec> {
    let inputs=[
        ("facet-core",0,[248,252,16,10],"core"),
        ("facet-extension",0,[240,272,12,12],"extension"),
        ("facet-adjacent",0,[268,272,20,20],"adjacent structure"),
        ("dark-core",1,[248,252,16,10],"core"),
        ("dark-column",1,[250,283,12,12],"extension"),
        ("dark-fan",1,[261,278,12,12],"extension"),
        ("dark-structure",1,[328,210,16,16],"competing structure"),
        ("nearby-core",1,[328,212,16,10],"separate core"),
        ("dark-continuation",1,[328,224,16,16],"separate continuation"),
        ("facet-extension-minus64",0,[176,272,12,12],"spatial null; not certified flat"),
        ("facet-extension-plus64",0,[304,272,12,12],"spatial null; not certified flat"),
        ("dark-column-minus64",1,[186,283,12,12],"spatial null; not certified flat"),
        ("dark-column-plus64",1,[314,283,12,12],"spatial null; not certified flat"),
        ("dark-fan-minus64",1,[197,278,12,12],"spatial null; not certified flat"),
        ("dark-fan-plus64",1,[325,278,12,12],"spatial null; not certified flat"),
        ("dark-continuation-minus64",1,[264,224,16,16],"spatial null; not certified flat"),
        ("dark-continuation-plus64",1,[392,224,16,16],"spatial null; not certified flat"),
    ];
    let mut result=inputs.into_iter().map(|(name,w,r,role)| {
        let origin=WINDOWS[w].1;
        RoiSpec{name,window:WINDOWS[w].0,local_quad_xywh:r,
            output_quad_xywh:[origin[0]+r[0],origin[1]+r[1],r[2],r[3]],role}
    }).collect::<Vec<_>>();
    result.push(RoiSpec{name:"pale-background",window:"output",
        local_quad_xywh:[288,663,16,16],output_quad_xywh:[288,663,16,16],
        role:"inherited pale-background negative; not calibrated flat"});
    result
}

fn check_old_wide(old:&Value, old_dir:&Path, index:usize, worker:&BandWorker,
    full_hashes:&[String], guide_hash:&str, variance_hash:&str, active_hash:&str,
    width:usize)->Result<bool> {
    if ![25,28,33,69].contains(&index) {return Ok(false)}
    let group=old["groups"].as_array().context("old wide groups")?.iter()
        .find(|g|g["source_index0"].as_u64()==Some(index as u64)).context("old source missing")?;
    ensure!(group["source_active_u16_sha256"]==active_hash
        && group["full_known4_sha256"]==json!(full_hashes)
        && group["full_guide_sha256"]==guide_hash && group["full_variance_sha256"]==variance_hash,
        "old full actual source/known4/guide/variance mismatch");
    let old_beta=group["beta"].as_array().context("old beta")?;
    ensure!(old_beta.len()==worker.beta.len() && old_beta.iter().zip(&worker.beta)
        .all(|(a,b)|a.as_f64().is_some_and(|v|(v as f32).to_bits()==b.to_bits())),"old beta differs");
    for (name,r) in WINDOWS {
        let artifact=group["artifacts"].as_array().context("old artifacts")?.iter()
            .find(|a|a["region"]==name).context("old region absent")?;
        ensure!(artifact["output_quad_xywh"]==json!(r),"old wide coordinates differ");
        for (field,planes) in [("known4",worker.planes.iter().map(Vec::as_slice).collect::<Vec<_>>()),
            ("guide",vec![worker.luma.as_slice()]),("variance",vec![worker.var.as_slice()])] {
            let a=&artifact[field];
            ensure!(a["shape"]==json!([planes.len(),512,512]),"old wide shape differs");
            let path=old_dir.join(a["path"].as_str().context("old field path")?);
            ensure!(file_hash(&path)?==a["sha256"].as_str().context("old field hash")?,"old field file changed");
            let retained=std::fs::read(&path)?;
            let actual=planes.iter().flat_map(|p|patch(p,width,r))
                .flat_map(|v|v.to_bits().to_le_bytes()).collect::<Vec<_>>();
            ensure!(retained==actual,"old512 field differs: source {index} {name} {field}");
        }
    }
    Ok(true)
}

#[test]
#[ignore="explicit all70 measurement export; root freezes inputs and bounds resources"]
fn vitamin_c_complete_source_traces()->Result<()> {
    let started=Instant::now();
    let workspace=PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../..").canonicalize()?;
    let old_dir=workspace.join("experiments/relative-blur-evidence/witness-1/output");
    let old=checked_json(&old_dir.join("receipt.json"),OLD_WIDE_HASH)?;
    let config=checked_json(&workspace.join("experiments/donor-consistency/spatial-on-2/config.json"),CONFIG_HASH)?;
    let headroom_path=workspace.join("experiments/relative-blur-evidence/original-headroom-1/result.json");
    const HEADROOM_HASH:&str="ca82a3569fad41686a6cd12cf85160aec315c854d72fd5d068610286f5e7e2d9";
    let _headroom=checked_json(&headroom_path,HEADROOM_HASH)?;
    let source_dir=PathBuf::from(config["source_dir"].as_str().context("held source directory")?);
    let map_path=PathBuf::from(config["warp_map"].as_str().context("held map")?);
    ensure!(source_dir.is_absolute() && source_dir.file_name().and_then(|v|v.to_str())==Some("crystalized-vitamin-c-cpl")
        && file_hash(&map_path)?==MAP_HASH,"held source/map scope differs");
    let out=PathBuf::from(std::env::var_os("STREHL_THROUGH_FOCUS_EVENTS_OUT").context("STREHL_THROUGH_FOCUS_EVENTS_OUT required")?);
    ensure!(out.is_absolute() && !out.exists(),"new absolute output directory required");
    ensure!(out.parent().context("output parent")?.canonicalize()?
        .starts_with(workspace.join("experiments/through-focus-events").canonicalize()?),"output outside experiment");
    ensure!(align_cmd::fullres_gather_enabled() && gatefloor::enabled()
        && align_cmd::direct_plane_mode()?==align_cmd::DirectPlaneMode::Rounded
        && align_cmd::native_gpu_integration::gpu_gather_enabled()?,"actual rounded GPU/probe route required");
    ensure!(std::env::var_os("STREHL_LOCAL_PLACEMENT_FILE").is_none()
        && !std::env::var(strehl_core::demosaic::DEMOSAIC_ENV).is_ok_and(|v|v.eq_ignore_ascii_case("directional")),
        "held MHC/no local placement required");
    ensure!(strehl_core::pyramid::fine_support_candidate::environment_mode()==strehl_core::pyramid::fine_support_candidate::Mode::Off,
        "fine support candidate excluded");
    let paths=crate::raw_paths(&source_dir,None)?;
    ensure!(paths.len()==70 && paths.iter().enumerate().all(|(i,p)|p.file_name().and_then(|v|v.to_str())
        ==Some(format!("DSC{:05}.ARW",94+i).as_str())),"held70 sequence differs");
    let before=paths.iter().map(|p|stamp(p)).collect::<Result<Vec<_>>>()?;
    let original=WarpMap::load(&map_path)?;
    original.check_stack(&StackIdentity::from_paths("crystalized-vitamin-c-cpl",&paths)?)?;
    ensure!(original.resampler()==Resampler::CatmullRom && original.len()==70 && original.placed_count()==70,"held complete map differs");
    let (map,fit)=align_cmd::cover_or_explain(original,align_cmd::CoverMode::Crop);
    let crop=fit.rect().context("held crop absent")?;let full=map.geometry();
    ensure!([crop.x,crop.y,crop.width,crop.height]==[28,19,3460,2306]
        && full==PlaneGeometry{width:3516,height:2344},"held domain gauge differs");
    let size=LevelSize{width:crop.width,height:crop.height};
    // L0 depends only on G0/G1. Deeper pyramid levels do not enter its build.
    // Full spatial domain and exact production phase remain unchanged.
    let sizes=[size,size.reduced()];
    let specs=roi_specs();let shifts=[[0usize,0usize],[1,0]];
    let rows=specs.iter().flat_map(|s|shifts.map(|shift| {
        let [x,y,w,h]=s.output_quad_xywh;
        (s,shift,[x+shift[0],y+shift[1],w,h])
    })).collect::<Vec<_>>();
    ensure!(rows.len()==36 && rows.iter().all(|(_,_,r)|r[0]+r[2]<=crop.width && r[1]+r[3]<=crop.height),"frozen ROI extent");
    let cfg=MergeConfig::default();let pool=ThreadPoolBuilder::new().num_threads(8).build()?;
    let mut pyramid=Pyramid::zeros(&sizes);let mut scratch=Workspace::new(&sizes);
    std::fs::create_dir(&out)?;let mut sources=Vec::new();
    for index in 0..70 {
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
        let active_hash=source_hash(&frame);
        let noise=profile::noise_model_for(&frame.camera,frame.iso,frame.levels);
        let mut worker=BandWorker::new(PyramidDomain::cropped(full,crop)?,cfg);
        ensure!(pool.install(||worker.fold(&OneFrame{frame:&frame,index},index,frame.levels,&noise,Some(&map),None))?,
            "actual consumer refused source");
        let full_hashes=worker.planes.iter().map(|p|field_hash(p)).collect::<Vec<_>>();
        let guide_hash=field_hash(&worker.luma);let variance_hash=field_hash(&worker.var);
        let old_exact=check_old_wide(&old,&old_dir,index,&worker,&full_hashes,&guide_hash,&variance_hash,&active_hash,crop.width)?;
        let mut measurements=(0..rows.len()).map(|_|Vec::<PlaneSummary>::new()).collect::<Vec<_>>();
        for plane in &worker.planes {
            pool.install(||pyramid.build(plane,&mut scratch));
            let energy=pool.install(||strehl_core::pyramid::correction_variance_diagnostic::energy(pyramid.level(0),size));
            for (j,(_,_,r)) in rows.iter().enumerate() {
                measurements[j].push(summarize_roi(plane,pyramid.level(0),&energy,&worker.luma,&worker.var,size,*r,[crop.x,crop.y])?);
            }
        }
        ensure!(source_hash(&frame)==active_hash
            && full_hashes==worker.planes.iter().map(|p|field_hash(p)).collect::<Vec<_>>()
            && guide_hash==field_hash(&worker.luma) && variance_hash==field_hash(&worker.var),"measurement changed input/gather/guide/variance");
        let record_rows=rows.iter().zip(measurements).map(|((spec,shift,r),planes)|json!({
            "roi_name":spec.name,"role":spec.role,"shift_quad_xy":shift,"output_quad_xywh":r,
            "reference_active_quad_xywh":[crop.x+r[0],crop.y+r[1],r[2],r[3]],"planes":planes})).collect::<Vec<_>>();
        let t=map.placement(index)?;
        sources.push(json!({"source_index0":index,"source_path":paths[index],"source_active_u16_sha256":active_hash,
            "full_known4_sha256":full_hashes,"full_guide_sha256":guide_hash,"full_variance_sha256":variance_hash,
            "beta":worker.beta,"old_wide_bit_exact":old_exact,"measurement_fields_unchanged":true,
            "transform_bits":([t.a.re,t.a.im,t.b.re,t.b.im].map(|v|format!("{:016x}",v.to_bits()))),
            "rows":record_rows,"seconds":source_start.elapsed().as_secs_f64()}));
        eprintln!("through-focus events source {index}/69: {:.2}s",source_start.elapsed().as_secs_f64());
    }
    ensure!(paths.iter().zip(&before).all(|(p,b)|stamp(p).is_ok_and(|a|a==*b))
        && file_hash(&map_path)?==MAP_HASH,"original metadata/map changed");
    let record=json!({"schema":1,"scope":"fixed descriptive all-source traces; no source selection, image output or quality admission",
        "source_indices":(0..70).collect::<Vec<_>>(),"source_dir":source_dir,"warp_map":map_path,"warp_map_sha256":MAP_HASH,
        "prior_wide_receipt_sha256":OLD_WIDE_HASH,"prior_config_sha256":CONFIG_HASH,
        "original_headroom":{"path":headroom_path,"sha256":HEADROOM_HASH,
            "scope":"original clipping established in broad core boxes at sources25/28/33/69; remaining frames unknown; no exact branch/stencil eligibility",
            "metadata_white_code":15360,"comparison_original_top_code":16383},
        "source_quad_dimensions":[full.width,full.height],"crop_quad_xywh":[crop.x,crop.y,crop.width,crop.height],
        "plane_order":["R","G1","G2","B"],"roi_specs":specs,"shifts_quad_xy":shifts,
        "parity_origin_quad_xy":[crop.x,crop.y],"checkerboards":"active-reference global quad parity; sensitivity subsets, not independent noise realizations",
        "mean_dn_units":"signed black-subtracted actual gathered source DN",
        "mean_l0_units":"signed actual full-domain finest Laplacian coefficient DN",
        "mean_energy_units":"mean production smooth5(L0 squared), DN squared; no noise subtraction",
        "guide_variance_scope":"mean actual injected green-guide variance DN squared; not per-plane variance/covariance or correlation calibration",
        "development_applied":false,"levels":[512,15360],"wb_bits":WB_BITS,"matrix":MATRIX,
        "merge_config":format!("{cfg:?}"),"execution_threads":8,"original_metadata_unchanged":true,
        "sources":sources,"seconds":started.elapsed().as_secs_f64()});
    let mut f=std::fs::OpenOptions::new().write(true).create_new(true).open(out.join("receipt.json"))?;
    serde_json::to_writer_pretty(&mut f,&record)?;writeln!(f)?;Ok(())
}

mod independent_controls {
    include!(concat!(env!("CARGO_MANIFEST_DIR"),"/../../experiments/through-focus-events/independent-controls.rs"));
}
