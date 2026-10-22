// A test-only observer around the actual RAW Pyramid consumer and writer.
use super::*;
use serde_json::{json, Value};
use std::io::Write;
use std::sync::{Mutex, OnceLock};
use strehl_core::demosaic::{Mosaic, demosaic_row};

#[derive(Clone)]
struct Region { name: String, frame: usize, x: usize, y: usize, width: usize, height: usize }
struct Capture {
    out: PathBuf, domain: PyramidDomain, map: WarpMap, regions: Vec<Region>,
    observe: bool,
    levels: Levels, gains: [f32; 3], dev: image_out::Develop,
    records: Vec<Value>, raw_count: usize, gathered_count: usize, merged_count: usize,
}
static CAPTURE: OnceLock<Mutex<Option<Capture>>> = OnceLock::new();
const PAD: usize = 4;

pub(crate) fn pinned_tone() -> Option<image_out::Tone> {
    CAPTURE.get()?.lock().ok()?.as_ref()?.dev.tone
}

fn f32_file(path: &Path, values: &[f32]) -> Result<()> {
    let mut file = std::fs::OpenOptions::new().write(true).create_new(true).open(path)?;
    for v in values { file.write_all(&v.to_bits().to_le_bytes())?; }
    Ok(())
}

fn save_patch(state: &mut Capture, region: &Region, stage: &str, values: Vec<f32>, xy: [usize;2]) -> Result<()> {
    let w = region.width + 2*PAD;
    let h = region.height + 2*PAD;
    ensure!(values.len()==w*h && w<=400 && h<=400, "patch extent mismatch");
    ensure!(values.iter().all(|v|v.is_finite()), "nonfinite CFA patch");
    let stem = format!("{}-frame{}-{stage}", region.name, region.frame);
    f32_file(&state.out.join(format!("{stem}-cfa.f32")), &values)?;
    let mosaic = Mosaic {data:&values,width:w,height:h};
    let mut rgb = vec![0.0f32;w*h*3];
    for y in 0..h { demosaic_row(&mosaic,y,&mut rgb[y*w*3..(y+1)*w*3]); }
    f32_file(&state.out.join(format!("{stem}-mhc-camera-rgb.f32")), &rgb)?;
    image_out::write_demosaiced(&state.out.join(format!("{stem}.tiff")),w,h,&values,&state.dev)?;
    state.records.push(json!({"name":region.name,"frame":region.frame,"stage":stage,
        "stem":stem,"width":w,"height":h,"trim":PAD,"reference_output_xywh":[region.x,region.y,region.width,region.height],
        "padded_origin_xy":xy,"coordinates":if stage=="raw" {"active native sensor; mapped centre rounded to even origin, no warp or CA correction"} else {"cropped reference output native grid"},
        "cfa_encoding":"row-major RGGB f32 little endian; black subtracted, first-frame WB and 1/(white-black), no upper clamp",
        "rgb_encoding":"row-major interleaved linear camera RGB f32; actual current demosaic_row before colour matrix/tone",
        "meaningful_interior_xywh":[PAD,PAD,region.width,region.height]}));
    Ok(())
}

pub(crate) fn observe_raw(index:usize, frame:&Frame) -> Result<()> {
    let Some(lock)=CAPTURE.get() else {return Ok(())};
    let mut guard=lock.lock().map_err(|_|anyhow::anyhow!("matched observer poisoned"))?;
    let Some(state)=guard.as_mut() else {return Ok(())};
    if !state.observe {return Ok(())}
    let regions:Vec<_>=state.regions.iter().filter(|r|r.frame==index).cloned().collect();
    for region in regions {
        let w=region.width+2*PAD;let h=region.height+2*PAD;
        let rx=(region.x+region.width/2) as f64/2.0+state.domain.rect.x as f64;
        let ry=(region.y+region.height/2) as f64/2.0+state.domain.rect.y as f64;
        let full=state.domain.full;
        let (sx,sy)=state.map.placement(index)?.apply_at(rx,ry,full.width as f64/2.0,full.height as f64/2.0);
        let x=((2.0*sx-region.width as f64/2.0).round() as usize)&!1;
        let y=((2.0*sy-region.height as f64/2.0).round() as usize)&!1;
        ensure!(x>=PAD && y>=PAD && x+region.width+PAD<frame.active.width && y+region.height+PAD<frame.active.height,"raw patch unsupported");
        let (x,y)=(x-PAD,y-PAD);
        let mut values=Vec::with_capacity(w*h);
        for py in 0..h {for px in 0..w {
            let p=CfaPlane::rggb_at(px,py);
            let gain=state.gains[match p {CfaPlane::R=>0,CfaPlane::G1|CfaPlane::G2=>1,CfaPlane::B=>2}];
            let value=(frame.sample(x+px,y+py) as f32-state.levels.black).max(0.0);
            values.push(value*gain*1.0/state.levels.range());
        }}
        save_patch(state,&region,"raw",values,[x,y])?;
        state.raw_count+=1;
    }
    Ok(())
}

pub(crate) fn observe_planes(index:Option<usize>, planes:&[Vec<f32>]) -> Result<()> {
    let Some(lock)=CAPTURE.get() else {return Ok(())};
    let mut guard=lock.lock().map_err(|_|anyhow::anyhow!("matched observer poisoned"))?;
    let Some(state)=guard.as_mut() else {return Ok(())};
    if !state.observe {return Ok(())}
    let regions:Vec<_>=state.regions.iter().filter(|r|index.is_none()||index==Some(r.frame)).cloned().collect();
    ensure!(planes.len()==4 && planes.iter().all(|p|p.len()==state.domain.analysis().pixels()),"wrong consumed plane extent");
    for region in regions {
        let w=region.width+2*PAD;let h=region.height+2*PAD;
        let (x,y)=(region.x-PAD,region.y-PAD);
        let mut values=Vec::with_capacity(w*h);
        for py in 0..h {for px in 0..w {
            let ox=x+px;let oy=y+py;
            let p=(oy%2)*2+ox%2;
            let gain=state.gains[if p==0 {0}else if p==3 {2}else{1}];
            // Exact write_merged -> Merged::Bands::value -> norm arithmetic.
            values.push(planes[p][(oy/2)*state.domain.rect.width+ox/2].max(0.0)*gain*1.0/state.levels.range());
        }}
        save_patch(state,&region,if index.is_some(){"gathered"}else{"merged"},values,[x,y])?;
        if index.is_some(){state.gathered_count+=1}else{state.merged_count+=1}
    }
    Ok(())
}

fn options(dir:PathBuf,out:PathBuf)->MergeOptions {
    MergeOptions {dir,out:Some(out),linear_master:None,region_recipe:None,sensor_master:Default::default(),limit:None,srgb:true,space:image_out::OutputSpace::Srgb,demosaic:true,
        exposure:0.0,auto_exposure:false,gates:vec![2.0],focus:None,flat_roi:None,detail_roi:None,
        index_map:None,n_eff_map:None,confidence_map:None,photometric:PhotometricMode::Off,
        photometric_source:SettingSource::Default,target_n_eff:None,stats:false,stats_placebo:false,
        confidence_tail:0.05,resampler:Resampler::CatmullRom,backend:MergeBackend::Pyramid,
        cover:align_cmd::CoverMode::Crop,cover_source:SettingSource::Flag,pyramid:MergeConfig::default()}
}

#[test]
#[ignore="root-owned matched RAW source diagnostic; explicit JSON configuration required"]
fn matched_source_actual_consumer() {
    run().unwrap();
}

fn run()->Result<()> {
    let config_path=PathBuf::from(std::env::var_os("STREHL_MATCHED_SOURCE_CONFIG").context("explicit config required")?);
    let cfg:Value=serde_json::from_slice(&std::fs::read(&config_path)?)?;
    let text=|k:&str|cfg[k].as_str().with_context(||format!("missing {k}"));
    let dir=PathBuf::from(text("dir")?);let out=PathBuf::from(text("out")?);
    ensure!(std::env::var_os(ONLY_FRAME_ENV).is_none(),"do not truncate source paths");
    let map_path=PathBuf::from(std::env::var_os(WARPMAP_ENV).context("explicit STREHL_WARPMAP required")?);
    ensure!(map_path.canonicalize()?==PathBuf::from(text("map")?).canonicalize()?,"configured map differs from consumed map");
    ensure!(align_cmd::align_enabled(),"alignment must be on");
    let root=PathBuf::from(env!("CARGO_MANIFEST_DIR")).parent().unwrap().parent().unwrap().canonicalize()?;
    ensure!(out.parent().context("output parent")?.canonicalize()?.starts_with(&root),"output outside repository");
    std::fs::create_dir(&out)?;
    let replay=out.join("replay.tiff");
    ensure!(!replay.exists(),"replay exists");
    let paths=crate::raw_paths(&dir,None)?;
    ensure!(paths.len()==cfg["frames"].as_u64().context("frames")? as usize,"wrong source count");
    let first=strehl_raw::decode(&paths[0])?;
    let levels=first.levels;let gains=first.wb_gains().context("first-frame WB")?;
    let full=first.geometry();let xyz=first.xyz_to_cam_rgb_with_source().context("camera matrix")?;
    let matrix=color::camera_to_srgb(xyz.0).context("matrix conversion")?.with_saturation(levels,gains,1.0);
    let tone=image_out::Tone {black:cfg["tone"]["black"].as_f64().context("tone black")? as f32,
        white:cfg["tone"]["white"].as_f64().context("tone white")? as f32,
        contrast:cfg["tone"]["contrast"].as_f64().context("tone contrast")? as f32};
    ensure!(tone.black.is_finite()&&tone.white.is_finite()&&tone.white>tone.black&&tone.contrast.is_finite(),"invalid tone");
    let mut dev=image_out::OutputSpace::Srgb.develop(Some(matrix));dev.tone=Some(tone);dev.exposure_gain=1.0;
    let (map,_)=alignment_for(&dir,&paths,Resampler::CatmullRom)?.context("explicit map required")?;
    let (map,fit)=align_cmd::cover_or_explain(map,align_cmd::CoverMode::Crop);
    let domain=pyramid_domain(full,align_cmd::CoverMode::Crop,Some(&fit))?;
    let mut regions=Vec::new();
    for r in cfg["regions"].as_array().context("regions")? {
        let v=|k:&str|r[k].as_u64().with_context(||format!("region {k}"));
        let region=Region{name:r["name"].as_str().context("region name")?.into(),frame:v("frame")? as usize,
            x:v("x")? as usize,y:v("y")? as usize,width:v("width")? as usize,height:v("height")? as usize};
        ensure!(region.name.bytes().all(|c|c.is_ascii_alphanumeric()||c==b'-'),"invalid region name");
        ensure!(region.frame<paths.len()&&region.x>=PAD&&region.y>=PAD&&region.x%2==0&&region.y%2==0
            &&region.width>0&&region.height>0&&region.width%2==0&&region.height%2==0
            &&region.width+2*PAD<=400&&region.height+2*PAD<=400
            &&region.x+region.width+PAD<2*domain.rect.width&&region.y+region.height+PAD<2*domain.rect.height,"invalid region");
        regions.push(region);
    }
    ensure!(!regions.is_empty()&&regions.len()<=8,"region count");
    let count=regions.len();
    let observe=match cfg.get("observe") {None=>true,Some(v)=>v.as_bool().context("observe must be boolean")?};
    drop(first);
    let lock=CAPTURE.get_or_init(||Mutex::new(None));
    ensure!(lock.lock().unwrap().is_none(),"observer already installed");
    *lock.lock().unwrap()=Some(Capture {out:out.clone(),domain,map,regions,observe,levels,gains,dev,
        records:Vec::new(),raw_count:0,gathered_count:0,merged_count:0});
    run_pyramid(&options(dir,replay.clone()))?;
    let state=lock.lock().unwrap().take().context("missing observer")?;
    let expected=if observe {count}else{0};
    ensure!(state.raw_count==expected&&state.gathered_count==expected&&state.merged_count==expected,"observer counts mismatch");
    let receipt=json!({"status":"MATCHED_SOURCE_CAPTURED","configuration":cfg,"patches":state.records,
        "raw_count":state.raw_count,"gathered_count":state.gathered_count,"merged_count":state.merged_count,
        "tone_bits":[tone.black.to_bits(),tone.white.to_bits(),tone.contrast.to_bits()],"wb_bits":gains.map(f32::to_bits),
        "levels":[levels.black,levels.white],"crop_quad_xywh":[domain.rect.x,domain.rect.y,domain.rect.width,domain.rect.height],
        "replay_tiff":replay,"source_frame_count":paths.len(),"native_map_reference":state.map.provenance().reference,
        "limits":"raw panels have no CA correction or geometric resampling; gathered and merged share the exact reference grid and production correction path; shared pinned tone differs slightly from prior automatic baseline; retain replay until independent pixel comparison"});
    let mut file=std::fs::OpenOptions::new().write(true).create_new(true).open(out.join("receipt.json"))?;
    serde_json::to_writer_pretty(&mut file,&receipt)?;file.write_all(b"\n")?;
    Ok(())
}
