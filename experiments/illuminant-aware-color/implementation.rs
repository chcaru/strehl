// Experiment-only final color replacement; no production/default hook.
use super::*;
use serde::{Deserialize,Serialize};
use serde_json::{json,Value};
use sha2::{Digest,Sha256};
use std::{fs::File,io::{Read,Write},time::SystemTime};
use full_stack_source_prior::CacheMetadata;
use crate::image_out::highlight_rendering::{self as rendering,Arm};
pub(crate) mod operator {
    include!(concat!(env!("CARGO_MANIFEST_DIR"),"/../../experiments/illuminant-aware-color/operator.rs"));
}

#[derive(Clone,Serialize,Deserialize)]
#[serde(deny_unknown_fields)]
struct Capture {
    name:String,source:PathBuf,source_bytes:u64,source_sha256:String,
    cache:PathBuf,cache_sha256:String,baseline:PathBuf,baseline_sha256:String,baseline_pixels_sha256:String,
}
#[derive(Serialize,Deserialize)]
#[serde(deny_unknown_fields)]
struct Config {
    schema:u32,phase:String,shot_kelvin:f64,out_dir:PathBuf,captures:Vec<Capture>,
    metadata_receipt:Option<PathBuf>,metadata_receipt_sha256:Option<String>,
}
fn digest(h:Sha256)->String {h.finalize().iter().map(|v|format!("{v:02x}")).collect()}
fn file_hash(path:&Path)->Result<String> {
    let mut f=File::open(path)?;let mut h=Sha256::new();let mut b=vec![0u8;65536];
    loop{let n=f.read(&mut b)?;if n==0{break;}h.update(&b[..n]);}Ok(digest(h))
}
fn save(path:&Path,v:&Value)->Result<()> {
    let mut f=std::fs::OpenOptions::new().write(true).create_new(true).open(path)?;
    serde_json::to_writer_pretty(&mut f,v)?;writeln!(f)?;Ok(())
}
fn stamp(path:&Path)->Result<(u64,SystemTime)> {let m=std::fs::metadata(path)?;Ok((m.len(),m.modified()?))}
fn source_hash(frame:&Frame)->String {
    let mut h=Sha256::new();let mut b=vec![0u8;frame.active.width*2];
    for y in 0..frame.active.height{for(dst,v)in b.chunks_exact_mut(2).zip(frame.active_row(y)){dst.copy_from_slice(&v.to_le_bytes());}h.update(&b);}
    digest(h)
}
fn config(phase:&str)->Result<Config> {
    let path=PathBuf::from(std::env::var_os("STREHL_ILLUMINANT_AWARE_COLOR_CONFIG").context("explicit config required")?);
    let c:Config=serde_json::from_slice(&std::fs::read(path)?)?;
    ensure!(c.schema==1&&c.phase==phase&&c.shot_kelvin.to_bits()==3000.0f64.to_bits(),"fixed phase/3000K contract differs");
    ensure!(c.captures.len()==2&&c.captures[0].name=="opal103"&&c.captures[1].name=="marigold4","exact two captures required");
    ensure!(c.captures.iter().all(|v|v.source.is_absolute()&&v.cache.is_absolute()&&v.baseline.is_absolute()
        &&v.source_bytes>0&&[&v.source_sha256,&v.cache_sha256,&v.baseline_sha256,&v.baseline_pixels_sha256]
        .iter().all(|s|s.len()==64)),"invalid source/cache bindings");
    let root=PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../../experiments/illuminant-aware-color").canonicalize()?;
    ensure!(c.out_dir.is_absolute()&&!c.out_dir.exists()
        &&c.out_dir.parent().context("output parent")?.canonicalize()?.starts_with(root),"fresh owned output required");
    ensure!(std::env::var_os(strehl_core::highlight::KNEE_ENV).is_none()
        &&!std::env::var(strehl_core::demosaic::DEMOSAIC_ENV).is_ok_and(|v|v.eq_ignore_ascii_case("directional"))
        &&std::env::var("STREHL_CA_BEFORE_MHC").ok().as_deref()==Some("off"),"held MHC/highlight/CA stage required");
    Ok(c)
}
fn cache_metadata(c:&Capture)->Result<CacheMetadata> {
    ensure!(file_hash(&c.cache)?==c.cache_sha256,"cache metadata binding differs");
    let m:CacheMetadata=serde_json::from_slice(&std::fs::read(&c.cache)?)?;
    let(count,reference,crop,exposure,arm)=if c.name=="opal103"{(155,77,[60,40,3396,2264],-0.3f32,"baseline")}
        else{(488,244,[191,128,3134,2088],-0.5f32,"candidate")};
    ensure!(m.schema==1&&m.phase=="full"&&m.frames==count&&m.reference==reference&&m.crop==crop
        &&m.full_geometry==[3516,2344]&&m.arm==arm&&m.exposure_stops_bits==Some(exposure.to_bits())
        &&m.xyz_source.as_deref()==Some("decoder color_matrix[D65]")
        &&m.tone_policy=="automatic-per-arm-current-writer","held complete baseline cache differs");
    m.domain()?;Ok(m)
}
pub(crate) fn camera_metadata(frame:&Frame)->Result<operator::CameraMetadata> {
    let(selected,selected_source)=frame.xyz_to_cam_rgb_with_source().context("selected calibration absent")?;
    let mut matrices=frame.color_matrices.iter().map(|(name,m)|operator::NamedMatrix{
        name:name.clone(),bits:m.map(|r|r.map(f32::to_bits))}).collect::<Vec<_>>();
    matrices.sort_by(|a,b|a.name.cmp(&b.name));
    Ok(operator::CameraMetadata{camera:frame.camera.clone(),wb_gains_bits:frame.wb_gains().context("invalid WB")?.map(f32::to_bits),
        matrices,selected_source,selected_matrix_bits:selected.map(|r|r.map(f32::to_bits)),
        direct_matrix_bits:frame.xyz_to_cam_rgbe.map(|r|r.map(f32::to_bits))})
}
#[test]
#[ignore="root-owned exactly two first-frame metadata decodes"]
fn metadata_pair()->Result<()> {
    let c=config("metadata")?;ensure!(c.metadata_receipt.is_none()&&c.metadata_receipt_sha256.is_none(),"metadata route cannot import its own outcome");
    std::fs::create_dir(&c.out_dir)?;let mut captures=Vec::new();
    for capture in &c.captures {
        let started=Instant::now();let m=cache_metadata(capture)?;let before=stamp(&capture.source)?;
        ensure!(before.0==capture.source_bytes&&file_hash(&capture.source)?==capture.source_sha256,"original identity differs");
        let frame=strehl_raw::decode(&capture.source)?;
        ensure!(frame.camera=="ILCE-7CM2"&&frame.iso==Some(100.0)&&frame.geometry()==PlaneGeometry{width:3516,height:2344}
            &&frame.active.width==7032&&frame.active.height==4688
            &&[frame.levels.black.to_bits(),frame.levels.white.to_bits()]==m.levels_bits,"original camera/geometry/levels differ from cache");
        let data=camera_metadata(&frame)?;
        ensure!(Some(data.wb_gains_bits)==m.wb_gains_bits&&Some(data.selected_matrix_bits)==m.xyz_to_cam_bits
            &&Some(data.selected_source.as_str())==m.xyz_source.as_deref(),"original consumed WB/D65 differs from cache");
        let active_u16_sha256=source_hash(&frame);let(selection,refusal)=match operator::select(&data,c.shot_kelvin){
            Ok(v)=>(Some(v),None),Err(e)=>(None,Some(format!("{e:#}")))};
        ensure!(stamp(&capture.source)?==before&&file_hash(&capture.source)?==capture.source_sha256
            &&file_hash(&capture.cache)?==capture.cache_sha256,"original/cache changed during metadata extraction");
        let row=json!({"input":capture,"camera_metadata":data,"selection":selection,"refusal":refusal,
            "admitted":selection.is_some(),"raw_wb_coeffs_bits":frame.wb_coeffs.map(f32::to_bits),
            "active_u16_sha256":active_u16_sha256,"levels_bits":m.levels_bits,"iso":frame.iso,
            "cache_wb_d65_exact":true,"source_unchanged":true,"seconds":started.elapsed().as_secs_f64()});
        save(&c.out_dir.join(format!("{}-metadata.json",capture.name)),&row)?;captures.push(row);
    }
    let admitted=captures.iter().all(|v|v["admitted"]==true);
    save(&c.out_dir.join("receipt.json"),&json!({"schema":1,"phase":"metadata",
        "status":if admitted{"METADATA_AVAILABLE"}else{"METADATA_REFUSED"},"admitted":admitted,"captures":captures,
        "source_count":2,"shot_kelvin":c.shot_kelvin,"temperature_is_declared_assumption":true,
        "physical_color_calibration_established":false,"original_metadata_unchanged":true}))?;Ok(())
}
fn rgb(path:&Path,native:[usize;2])->Result<(String,Vec<u8>)> {
    let mut d=tiff::decoder::Decoder::new(std::io::BufReader::new(File::open(path)?))?;
    ensure!(d.dimensions()?==(native[0]as u32,native[1]as u32)&&d.colortype()?==tiff::ColorType::RGB(16),"RGB16 dimensions differ");
    let icc=d.get_tag_u8_vec(tiff::tags::Tag::IccProfile)?;ensure!(!icc.is_empty(),"ICC absent");
    let data=match d.read_image()?{tiff::decoder::DecodingResult::U16(v)=>v,_=>bail!("RGB16 storage absent")};
    ensure!(data.len()==native[0]*native[1]*3&&!d.more_images(),"RGB storage/pages differ");
    let mut h=Sha256::new();let mut b=vec![0u8;65536];
    for row in data.chunks(b.len()/2){for(dst,v)in b.chunks_exact_mut(2).zip(row){dst.copy_from_slice(&v.to_le_bytes());}h.update(&b[..row.len()*2]);}
    Ok((digest(h),icc))
}
// Same WB, MHC and developer as the existing pinned writer; only matrix varies.
pub(crate) fn pinned_write(path:&Path,planes:&[Vec<f32>],m:&CacheMetadata,resolved:&rendering::Resolved,
    replacement:Option<&operator::Transform>)->Result<rendering::Resolved> {
    let domain=m.domain()?;let(w,h)=(domain.rect.width,domain.rect.height);let levels=m.levels();
    ensure!(planes.len()==4&&planes.iter().all(|v|v.len()==w*h&&v.iter().all(|x|x.is_finite())),"invalid CFA cache");
    let gains=m.wb().context("WB absent")?;let xyz=m.xyz().context("matrix absent")?;
    let applied=match m.exposure()?{Exposure::None=>AppliedExposure::IDENTITY,
        Exposure::Stops(stops)=>AppliedExposure{stops,automatic:false},Exposure::Auto=>bail!("automatic exposure refused")};
    let eg=applied.gain();ensure!(eg.to_bits()==resolved.exposure_gain_bits,"exposure differs");
    let matrix=match replacement{Some(v)=>color::Render::new(v.matrix),None=>color::camera_to_srgb(xyz.0).context("baseline matrix invalid")?};
    let mut dev=image_out::OutputSpace::Srgb.develop(Some(matrix.with_saturation(levels,gains,eg))).with_exposure_gain(eg);
    let t=resolved.tone_bits.context("resolved tone absent")?;
    dev.tone=Some(image_out::Tone{black:f32::from_bits(t[0]),white:f32::from_bits(t[1]),contrast:f32::from_bits(t[2])});
    let mut mosaic=vec![0.0f32;w*h*4];
    for p in 0..4{let gain=gains[if p==0{0}else if p==3{2}else{1}];
        for y in 0..h{for x in 0..w{let v=planes[p][y*w+x].max(0.0);
            mosaic[(2*y+p/2)*(2*w)+2*x+p%2]=v*gain*eg/levels.range();}}}
    let(_,observed)=rendering::with_arm(Arm::Current,||image_out::write_demosaiced(path,2*w,2*h,&mosaic,&dev))?;
    let mut expected=resolved.clone();if let Some(t)=replacement{expected.matrix_bits=Some(t.matrix.map(|r|r.map(f32::to_bits)));}
    ensure!(observed==expected,"development changed beyond the one intended matrix");Ok(observed)
}
#[test]
#[ignore="root-owned complete cached opal and marigold matrix comparison; no RAW reads"]
fn cached_pair()->Result<()> {
    let c=config("cached")?;
    let path=c.metadata_receipt.as_ref().context("metadata receipt required")?;
    let expected=c.metadata_receipt_sha256.as_ref().context("metadata receipt hash required")?;
    ensure!(path.is_absolute()&&file_hash(path)?==*expected,"metadata receipt binding differs");
    let metadata:Value=serde_json::from_slice(&std::fs::read(path)?)?;
    ensure!(metadata["schema"]==1&&metadata["phase"]=="metadata"&&metadata["status"]=="METADATA_AVAILABLE"
        &&metadata["admitted"]==true&&metadata["source_count"]==2&&metadata["shot_kelvin"]==json!(c.shot_kelvin),"metadata route not admitted");
    let rows=metadata["captures"].as_array().context("metadata captures absent")?;ensure!(rows.len()==2,"metadata count differs");
    std::fs::create_dir(&c.out_dir)?;let mut captures=Vec::new();
    for(capture,row)in c.captures.iter().zip(rows){let started=Instant::now();
        ensure!(row["input"]==serde_json::to_value(capture)?&&row["admitted"]==true&&row["cache_wb_d65_exact"]==true,
            "metadata capture identity/admission differs");
        let bound=cache_metadata(capture)?;
        let data:operator::CameraMetadata=serde_json::from_value(row["camera_metadata"].clone())?;
        ensure!(Some(data.wb_gains_bits)==bound.wb_gains_bits&&Some(data.selected_matrix_bits)==bound.xyz_to_cam_bits,
            "saved original metadata differs from cache");
        let selection=operator::select(&data,c.shot_kelvin)?;
        ensure!(serde_json::to_value(&selection)?==row["selection"],"recomputed transform differs from metadata route");
        let(m,planes)=full_stack_source_prior::read_cache(&capture.cache)?;
        ensure!(serde_json::to_value(&m)?==serde_json::to_value(&bound)?,"cache metadata changed during read");
        let native=[2*m.crop[2],2*m.crop[3]];let current=c.out_dir.join(format!("{}-current.tiff",capture.name));
        ensure!(file_hash(&capture.baseline)?==capture.baseline_sha256,"baseline file binding differs");
        let expected_rgb=rgb(&capture.baseline,native)?;ensure!(expected_rgb.0==capture.baseline_pixels_sha256,"baseline RGB binding differs");
        let(_,resolved)=rendering::with_arm(Arm::Current,||full_stack_source_prior::write_current(&current,&planes,&m))?;
        ensure!(rgb(&current,native)?==expected_rgb,"complete current baseline RGB16/ICC differs");
        let pinned=c.out_dir.join(format!("{}-pinned.tiff",capture.name));pinned_write(&pinned,&planes,&m,&resolved,None)?;
        ensure!(rgb(&pinned,native)?==expected_rgb,"pinned rewrite changes current RGB16/ICC");
        let candidate=c.out_dir.join(format!("{}-candidate.tiff",capture.name));
        let observed=pinned_write(&candidate,&planes,&m,&resolved,Some(&selection.transform))?;
        let(candidate_rgb,candidate_icc)=rgb(&candidate,native)?;ensure!(candidate_icc==expected_rgb.1,"candidate ICC changed");
        let binary=capture.cache.parent().context("cache parent")?.join(&m.binary);
        ensure!(file_hash(&capture.cache)?==capture.cache_sha256&&file_hash(&binary)?==m.binary_sha256
            &&file_hash(&capture.baseline)?==capture.baseline_sha256,"cache or baseline changed during writer comparison");
        let result=json!({"name":capture.name,"input":capture,"native_dimensions":native,"selection":selection,
            "baseline_resolved":resolved,"candidate_resolved":observed,"matrix_only_changed":true,
            "baseline_current_rgb16_icc_exact":true,"baseline_pinned_rewrite_exact":true,"cache_unchanged":true,
            "current_path":current,"current_sha256":file_hash(&current)?,"current_rgb16_le_sha256":expected_rgb.0,
            "pinned_path":pinned,"pinned_sha256":file_hash(&pinned)?,
            "candidate_path":candidate,"candidate_sha256":file_hash(&candidate)?,"candidate_rgb16_le_sha256":candidate_rgb,
            "cache_plane_sha256":m.plane_sha256,"cache_binary_sha256":m.binary_sha256,"seconds":started.elapsed().as_secs_f64()});
        save(&c.out_dir.join(format!("{}-receipt.json",capture.name)),&result)?;captures.push(result);
    }
    ensure!(file_hash(path)?==*expected,"metadata receipt changed");
    save(&c.out_dir.join("receipt.json"),&json!({"schema":1,"phase":"cached","status":"COMPARISON_COMPLETE",
        "captures":captures,"source_reads":0,"shot_kelvin":c.shot_kelvin,"temperature_is_declared_assumption":true,
        "actual_tone_pinned":true,"matrix_only_changed":true,"cache_unchanged":true,
        "physical_color_calibration_established":false,"photographic_quality_verdict":null}))?;Ok(())
}
mod independent_controls {
    include!(concat!(env!("CARGO_MANIFEST_DIR"),"/../../experiments/illuminant-aware-color/independent-controls.rs"));
}
