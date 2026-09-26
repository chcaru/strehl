//! Experiment-only sequential, unaligned native RAW development for an external comparator.
//! Uses the product decoder, MHC and writer. No alignment, merge, RAW writes or CA warp.
#[allow(dead_code)]
#[path = "../src/image_out.rs"]
mod image_out;

use anyhow::{Context, Result, ensure};
use rayon::prelude::*;
use serde_json::{Value, json};
use sha2::{Digest, Sha256};
use std::{fs::{File, OpenOptions}, io::{Read, Write}, path::{Path, PathBuf}};
use strehl_core::{color, noise::Levels};

const SOFTWARE: &str = "strehl marigold-batch-develop diagnostic; unaligned product MHC";

fn load(path: &Path) -> Result<Value> { Ok(serde_json::from_slice(&std::fs::read(path)?)?) }
fn save(path: &Path, value: &Value) -> Result<()> {
    let mut file = OpenOptions::new().write(true).create_new(true).open(path)?;
    serde_json::to_writer_pretty(&mut file, value)?;
    writeln!(file)?;
    Ok(())
}
fn hash(path: &Path) -> Result<String> {
    let mut file = File::open(path)?;
    let mut h = Sha256::new();
    let mut buf = vec![0u8; 1 << 20];
    loop { let n = file.read(&mut buf)?; if n == 0 { break; } h.update(&buf[..n]); }
    Ok(h.finalize().iter().map(|b| format!("{b:02x}")).collect())
}
fn make_dev(xyz: [[f32; 3]; 3], levels: Levels, wb: [f32; 3], tone: [f32; 3], exposure: f32) -> Result<image_out::Develop> {
    ensure!(xyz.iter().flatten().chain(wb.iter()).chain(tone.iter()).all(|v| v.is_finite()), "nonfinite development metadata");
    let matrix = color::camera_to_srgb(xyz).context("singular camera matrix")?
        .with_saturation(levels, wb, exposure);
    let mut dev = image_out::OutputSpace::Srgb.develop(Some(matrix));
    dev.tone = Some(image_out::Tone {black: tone[0], white: tone[1], contrast: tone[2]});
    dev.exposure_gain = exposure;
    Ok(dev)
}

fn normalize_row(source: &[u16], y: usize, out: &mut [f32], levels: Levels, wb: [f32; 3], exposure: f32) {
    for (x,v) in out.iter_mut().enumerate() {
        let channel = match (y&1,x&1) { (0,0) => 0, (1,1) => 2, _ => 1 };
        *v = (source[x] as f32-levels.black).max(0.0) * wb[channel] * exposure / (levels.white-levels.black);
    }
}

// This existing actual-consumer fixture has a known RGB16 result. A changed tap,
// normalization, colour or tone route can fail; no capture is decoded for this guard.
fn golden(cfg: &Value, out: &Path) -> Result<Value> {
    let dir = Path::new(cfg["fixture_dir"].as_str().context("fixture_dir")?);
    let receipt = load(&dir.join("receipt.json"))?;
    let bits = |key: &str| -> Result<[f32; 3]> {
        let a: [u32; 3] = serde_json::from_value(receipt[key].clone())?;
        Ok(a.map(f32::from_bits))
    };
    let levels = Levels {black: receipt["levels"][0].as_f64().context("black")? as f32,
        white: receipt["levels"][1].as_f64().context("white")? as f32};
    let xyz = serde_json::from_value(cfg["expected_xyz_to_cam"].clone())?;
    let dev = make_dev(xyz, levels, bits("wb_bits")?, bits("tone_bits")?, 1.0)?;
    let stem = "porous-source-129-frame129-raw";
    let cfa_path = dir.join(format!("{stem}-cfa.f32"));
    let expected_path = dir.join(format!("{stem}.tiff"));
    let cfa_bytes = std::fs::read(&cfa_path)?;
    ensure!(cfa_bytes.len() == 336*336*4, "fixture CFA extent");
    let cfa: Vec<f32> = cfa_bytes.chunks_exact(4).map(|b| f32::from_le_bytes(b.try_into().unwrap())).collect();
    // Independently decoded original u16 support overlaps this actual-consumer raw patch.
    // Exercise the same normalization function used below, not just saved f32 input.
    let original_path = Path::new(cfg["fixture_original_u16"].as_str().context("fixture_original_u16")?);
    let original = std::fs::read(original_path)?;
    ensure!(original.len() >= 16, "original CFA header absent");
    let header: Vec<usize> = original[..16].chunks_exact(4).map(|b| u32::from_le_bytes(b.try_into().unwrap()) as usize).collect();
    let (oy,ox,oh,ow) = (header[0],header[1],header[2],header[3]);
    ensure!(original.len()==16+oh*ow*2, "original CFA extent");
    let samples: Vec<u16> = original[16..].chunks_exact(2).map(|b|u16::from_le_bytes(b.try_into().unwrap())).collect();
    let patch = receipt["patches"].as_array().context("fixture patches")?.iter()
        .find(|p|p["stem"]==stem).context("fixture patch")?;
    let px = patch["padded_origin_xy"][0].as_u64().context("fixture x")? as usize;
    let py = patch["padded_origin_xy"][1].as_u64().context("fixture y")? as usize;
    ensure!(px%2==0 && py%2==0 && px>=ox && py>=oy && px+336<=ox+ow && py+336<=oy+oh, "fixture overlap/phase");
    let mut normalized = vec![0.0f32;336*336];
    for y in 0..336 {
        let offset = (py-oy+y)*ow + px-ox;
        normalize_row(&samples[offset..offset+336],y,&mut normalized[y*336..(y+1)*336],levels,bits("wb_bits")?,1.0);
    }
    let normalized_differences = normalized.iter().zip(&cfa).filter(|(a,b)|a.to_bits()!=b.to_bits()).count();
    ensure!(normalized_differences==0,"u16 normalization differs in {normalized_differences} f32 samples");
    let actual_path = out.join("golden.tiff");
    image_out::write_demosaiced(&actual_path, 336, 336, &cfa, &dev)?;
    let decode = |p: &Path| -> Result<Vec<u16>> {
        let mut d = tiff::decoder::Decoder::new(File::open(p)?)?;
        ensure!(d.dimensions()? == (336,336), "fixture dimensions");
        let tiff::decoder::DecodingResult::U16(v) = d.read_image()? else { anyhow::bail!("fixture type"); };
        Ok(v)
    };
    let a = decode(&actual_path)?; let b = decode(&expected_path)?;
    ensure!(a.len() == b.len() && a.len() == 336*336*3, "fixture sample count");
    let differing = a.iter().zip(&b).filter(|(x,y)| x != y).count();
    ensure!(differing == 0, "actual developer fixture differs in {differing} samples");
    Ok(json!({"status":"EXACT", "rgb16_samples":a.len(), "differing":differing,
        "normalized_f32_samples":normalized.len(),"normalized_f32_differences":normalized_differences,
        "original_u16_sha256":hash(original_path)?,
        "fixture_cfa_sha256":hash(&cfa_path)?, "fixture_tiff_sha256":hash(&expected_path)?}))
}


fn bits3(value: &Value) -> Result<[f32;3]> {
    Ok(serde_json::from_value::<[u32;3]>(value.clone())?.map(f32::from_bits))
}
fn exact_development(cfg: &Value) -> Result<(Levels,[f32;3],[[f32;3];3],image_out::Develop)> {
    let m = &cfg["cache_metadata"];
    let lb: [u32;2] = serde_json::from_value(m["levels_bits"].clone())?;
    let levels = Levels {black:f32::from_bits(lb[0]),white:f32::from_bits(lb[1])};
    let wb = bits3(&m["wb_gains_bits"])?;
    let xyz = serde_json::from_value::<[[u32;3];3]>(m["xyz_to_cam_bits"].clone())?.map(|r|r.map(f32::from_bits));
    let resolved = &cfg["resolved"];
    let exposure = f32::from_bits(resolved["exposure_gain_bits"].as_u64().context("exposure bits")? as u32);
    ensure!(exposure.to_bits()==2.0f32.powf(-0.5).to_bits(),"expected fixed -0.5EV");
    let dev = make_dev(xyz,levels,wb,bits3(&resolved["tone_bits"])?,exposure)?;
    let matrix = dev.matrix.context("render matrix absent")?;
    ensure!(json!(matrix.matrix().map(|r|r.map(f32::to_bits)))==resolved["matrix_bits"],"matrix differs from current");
    ensure!(json!(matrix.ceiling().map(f32::to_bits))==resolved["ceiling_bits"],"ceiling differs from current");
    ensure!(json!(matrix.top().to_bits())==resolved["sensor_top_bits"],"rolloff differs from current");
    ensure!(json!(dev.srgb)==resolved["srgb"]&&json!(dev.wants_tone)==resolved["wants_tone"],"output space differs");
    ensure!(levels.black==512.0&&levels.white==15360.0,"unexpected marigold levels");
    Ok((levels,wb,xyz,dev))
}
fn rgb(path: &Path) -> Result<((u32,u32),Vec<u16>,Vec<u8>)> {
    let mut d=tiff::decoder::Decoder::new(std::io::BufReader::new(File::open(path)?))?;
    let dims=d.dimensions()?;
    ensure!(d.colortype()?==tiff::ColorType::RGB(16),"RGB16 required");
    let icc=d.get_tag_u8_vec(tiff::tags::Tag::IccProfile)?;
    let tiff::decoder::DecodingResult::U16(p)=d.read_image()? else {anyhow::bail!("u16 pixels absent")};
    ensure!(!d.more_images()&&!icc.is_empty(),"unexpected TIFF pages/ICC");
    Ok((dims,p,icc))
}
fn current_golden(cfg:&Value,out:&Path,levels:Levels,wb:[f32;3],dev:&image_out::Develop)->Result<Value> {
    let m=&cfg["cache_metadata"];
    let path=Path::new(cfg["cache_binary"].as_str().context("cache binary")?);
    ensure!(hash(path)?==m["binary_sha256"].as_str().context("cache hash")?,"current cache bytes changed");
    let bytes=std::fs::read(path)?;
    let(w,h)=(3134usize,2088usize);let n=w*h;
    ensure!(bytes.len()==4*n*4,"current cache extent");
    let mut mosaic=vec![0.0f32;4*n];
    for p in 0..4 {let gain=wb[if p==0{0}else if p==3{2}else{1}];
        for y in 0..h {for x in 0..w {let i=4*(p*n+y*w+x);
            let v=f32::from_le_bytes(bytes[i..i+4].try_into().unwrap());
            ensure!(v.is_finite(),"nonfinite current CFA");
            mosaic[(2*y+p/2)*(2*w)+2*x+p%2]=v.max(0.0)*gain*dev.exposure_gain/levels.range();
        }}
    }
    drop(bytes);
    let actual=out.join("current-pinned-golden.tiff");
    image_out::write_demosaiced(&actual,2*w,2*h,&mosaic,dev)?;drop(mosaic);
    let baseline=Path::new(cfg["baseline"].as_str().context("baseline")?);
    ensure!(hash(baseline)?==cfg["baseline_sha256"].as_str().context("baseline hash")?,"current master changed");
    let a=rgb(&actual)?;let b=rgb(baseline)?;
    ensure!(a.0==(6268,4176)&&a==b,"pinned current pixels/ICC differ");
    Ok(json!({"rgb16_and_icc_exact":true,"native_wh":[6268,4176],"output_sha256":hash(&actual)?,
        "baseline_sha256":hash(baseline)?,"cache_binary_sha256":hash(path)?,"resolved":cfg["resolved"]}))
}
fn main() -> Result<()> {
    let config_path=PathBuf::from(std::env::args_os().nth(1).context("configuration JSON required")?);
    let cfg=load(&config_path)?;
    let out=PathBuf::from(cfg["out"].as_str().context("out")?);
    let root=PathBuf::from(env!("CARGO_MANIFEST_DIR")).parent().unwrap().parent().unwrap().canonicalize()?;
    let allowed=root.join("experiments/marigold-comparator").canonicalize()?;
    ensure!(out.parent().context("output parent")?.canonicalize()?.starts_with(&allowed),"output outside new experiment");
    std::fs::create_dir(&out)?;
    let witness=golden(&cfg,&out)?;save(&out.join("golden.json"),&witness)?;
    let(levels,wb,xyz,dev)=exact_development(&cfg)?;
    let current=current_golden(&cfg,&out,levels,wb,&dev)?;save(&out.join("current-golden.json"),&current)?;
    let rows=cfg["inputs"].as_array().context("input records")?;
    ensure!(rows.len()==488,"exactly488 ordered sources required");
    let mut records=Vec::with_capacity(488);
    for(i,row)in rows.iter().enumerate(){
        let path=Path::new(row["path"].as_str().context("input path")?);
        let(parent,number)=if i<279{("stack4.1-offcenter-sw5-cpl",i+21)}else{("stack4.2-offcenter-sw5-cpl",i-278)};
        ensure!(row["index"]==json!(i)&&path.parent().and_then(Path::file_name).and_then(|s|s.to_str())==Some(parent)
            &&path.file_name().and_then(|s|s.to_str())==Some(format!("DSC{number:05}.ARW").as_str()),"input chronology differs");
        let before=std::fs::metadata(path)?;let raw_hash=hash(path)?;
        ensure!(row["bytes"]==json!(before.len())&&row["sha256"].as_str()==Some(raw_hash.as_str()),"original identity differs");
        let frame=strehl_raw::decode(path)?;
        ensure!(frame.camera=="ILCE-7CM2"&&frame.iso==Some(100.0),"mixed camera/ISO");
        ensure!((frame.active.x,frame.active.y,frame.active.width,frame.active.height)==(0,0,7032,4688),"active geometry differs");
        ensure!(frame.levels==levels&&frame.wb_gains().map(|v|v.map(f32::to_bits))==Some(wb.map(f32::to_bits))
            &&frame.xyz_to_cam_rgb().map(|v|v.map(|r|r.map(f32::to_bits)))==Some(xyz.map(|r|r.map(f32::to_bits))),"capture metadata differs");
        let(w,h)=(frame.active.width,frame.active.height);let mut mosaic=vec![0.0f32;w*h];
        mosaic.par_chunks_mut(w).enumerate().for_each(|(y,dst)|normalize_row(frame.active_row(y),y,dst,levels,wb,dev.exposure_gain));
        ensure!(mosaic.par_iter().all(|v|v.is_finite()),"nonfinite CFA");
        let tiff=out.join(format!("frame-{i:05}.tiff"));image_out::write_demosaiced(&tiff,w,h,&mosaic,&dev)?;
        let after=std::fs::metadata(path)?;
        ensure!(before.len()==after.len()&&before.modified()?==after.modified()?,"original metadata changed");
        let record=json!({"ordinal":i,"input":path,"input_sha256":raw_hash,"input_bytes":before.len(),
            "input_wb_bits":wb.map(f32::to_bits),"raw_buffer_wh":[frame.stride,frame.buffer_height],
            "raw_active_xywh":[frame.active.x,frame.active.y,w,h],"output":tiff,
            "output_sha256":hash(&tiff)?,"output_bytes":std::fs::metadata(&tiff)?.len(),"output_wh":[w,h],"original_metadata_unchanged":true});
        save(&out.join(format!("frame-{i:05}.json")),&record)?;records.push(record);
        println!("developed {}/488 {}",i+1,path.display());
    }
    save(&out.join("receipt.json"),&json!({"status":"488_UNALIGNED_NATIVE_RGB16_DEVELOPED","configuration":cfg,
        "golden":witness,"current_golden":current,"wb_bits":wb.map(f32::to_bits),"resolved":cfg["resolved"],
        "xyz_to_cam_bits":xyz.map(|r|r.map(f32::to_bits)),"levels":[levels.black,levels.white],"frames":records,
        "scope":"Same product decoder/MHC and exact current fixed development; no CA or alignment; development precedes external fusion; workflow reference only"}))?;
    Ok(())
}
