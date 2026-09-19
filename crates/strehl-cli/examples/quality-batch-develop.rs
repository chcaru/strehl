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

const SOFTWARE: &str = "strehl quality-batch-develop diagnostic; unaligned product MHC";

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
fn make_dev(xyz: [[f32; 3]; 3], levels: Levels, wb: [f32; 3], tone: [f32; 3]) -> Result<image_out::Develop> {
    ensure!(xyz.iter().flatten().chain(wb.iter()).chain(tone.iter()).all(|v| v.is_finite()), "nonfinite development metadata");
    let matrix = color::camera_to_srgb(xyz).context("singular camera matrix")?
        .with_saturation(levels, wb, 1.0);
    let mut dev = image_out::OutputSpace::Srgb.develop(Some(matrix));
    dev.tone = Some(image_out::Tone {black: tone[0], white: tone[1], contrast: tone[2]});
    dev.exposure_gain = 1.0;
    Ok(dev)
}

fn normalize_row(source: &[u16], y: usize, out: &mut [f32], levels: Levels, wb: [f32; 3]) {
    for (x,v) in out.iter_mut().enumerate() {
        let channel = match (y&1,x&1) { (0,0) => 0, (1,1) => 2, _ => 1 };
        *v = (source[x] as f32-levels.black).max(0.0) * wb[channel] / (levels.white-levels.black);
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
    let dev = make_dev(xyz, levels, bits("wb_bits")?, bits("tone_bits")?)?;
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
        normalize_row(&samples[offset..offset+336],y,&mut normalized[y*336..(y+1)*336],levels,bits("wb_bits")?);
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

fn main() -> Result<()> {
    let config_path = PathBuf::from(std::env::args_os().nth(1).context("configuration JSON required")?);
    let cfg = load(&config_path)?;
    let out = PathBuf::from(cfg["out"].as_str().context("out")?);
    let root = PathBuf::from(env!("CARGO_MANIFEST_DIR")).parent().unwrap().parent().unwrap().canonicalize()?;
    ensure!(out.parent().context("output parent")?.canonicalize()?.starts_with(&root), "output outside workspace");
    std::fs::create_dir(&out)?;
    let witness = golden(&cfg, &out)?;
    save(&out.join("golden.json"), &witness)?;
    let paths: Vec<PathBuf> = serde_json::from_value(cfg["inputs"].clone())?;
    ensure!(paths.len() == 70, "exactly 70 frozen frames required");
    let input_dir = PathBuf::from(cfg["input_dir"].as_str().context("input_dir")?).canonicalize()?;
    for (i, path) in paths.iter().enumerate() {
        ensure!(path.canonicalize()?.parent() == Some(input_dir.as_path()), "input escaped frozen directory");
        ensure!(path.file_name().unwrap().to_str().unwrap() == format!("DSC{:05}.ARW",94+i), "input order");
    }
    let frame0 = strehl_raw::decode(&paths[0])?;
    ensure!(frame0.camera == "ILCE-7CM2", "camera changed");
    ensure!(frame0.iso == Some(100.0), "baseline ISO changed");
    let wb = frame0.wb_gains().context("first frame WB absent")?;
    let (xyz, matrix_source) = frame0.xyz_to_cam_rgb_with_source().context("camera matrix absent")?;
    let expected_xyz: [[f32; 3]; 3] = serde_json::from_value(cfg["expected_xyz_to_cam"].clone())?;
    ensure!(xyz == expected_xyz, "baseline camera matrix mismatch");
    ensure!((wb[0]-1.5986).abs() < 0.00006 && wb[1] == 1.0 && (wb[2]-2.7090).abs() < 0.00006,
        "WB inconsistent with baseline log");
    let levels = frame0.levels;
    ensure!(levels.black == 512.0 && levels.white == 15360.0, "baseline levels mismatch");
    let (w,h) = (frame0.active.width, frame0.active.height);
    ensure!((w,h) == (7032,4688), "active area changed");
    let tone: [f32; 3] = serde_json::from_value(cfg["tone"].clone())?;
    ensure!(tone == [0.090420,0.914606,0.550], "frozen baseline tone changed");
    let dev = make_dev(xyz, levels, wb, tone)?;
    let mut first = Some(frame0);
    let mut records = Vec::with_capacity(70);
    for (i,path) in paths.iter().enumerate() {
        let before = std::fs::metadata(path)?;
        let raw_hash = hash(path)?;
        let frame = if i == 0 { first.take().unwrap() } else { strehl_raw::decode(path)? };
        ensure!((frame.active.width,frame.active.height) == (w,h), "mixed geometry");
        ensure!(frame.camera == "ILCE-7CM2" && frame.iso == Some(100.0), "mixed camera/ISO");
        ensure!(frame.levels.black == levels.black && frame.levels.white == levels.white, "mixed levels");
        ensure!(frame.xyz_to_cam_rgb() == Some(xyz), "mixed camera matrix");
        let frame_wb = frame.wb_gains().context("frame WB absent")?;
        ensure!(frame_wb.map(f32::to_bits)==wb.map(f32::to_bits), "manual WB changed");
        let mut mosaic = vec![0.0f32; w*h];
        // Match write_merged: subtract black, clamp negatives, multiply WB, divide range.
        mosaic.par_chunks_mut(w).enumerate().for_each(|(y,row)| {
            normalize_row(frame.active_row(y),y,row,levels,wb);
        });
        ensure!(mosaic.par_iter().all(|v|v.is_finite()),"nonfinite normalized CFA");
        let tiff = out.join(format!("DSC{:05}.tiff",94+i));
        image_out::write_demosaiced(&tiff,w,h,&mosaic,&dev)?;
        let after = std::fs::metadata(path)?;
        ensure!(before.len()==after.len() && before.modified()?==after.modified()?, "original metadata changed");
        let record = json!({"ordinal":i,"input":path,"input_sha256":raw_hash,"input_bytes":before.len(),
            "input_wb_bits":frame_wb.map(f32::to_bits),"held_wb_differs":frame_wb!=wb,
            "raw_buffer_wh":[frame.stride,frame.buffer_height],
            "raw_active_xywh":[frame.active.x,frame.active.y,w,h],"output":tiff,
            "output_sha256":hash(&tiff)?,"output_bytes":std::fs::metadata(&tiff)?.len(),
            "output_wh":[w,h],"original_metadata_unchanged":true});
        save(&out.join(format!("frame-{i:03}.json")),&record)?;
        records.push(record);
        println!("developed {}/70 {}",i+1,path.file_name().unwrap().to_string_lossy());
    }
    save(&out.join("receipt.json"),&json!({"status":"70_UNALIGNED_NATIVE_RGB16_DEVELOPED", "configuration":cfg,
        "golden":witness,"wb_bits":wb.map(f32::to_bits),"tone_bits":tone.map(f32::to_bits),
        "xyz_to_cam_bits":xyz.map(|r|r.map(f32::to_bits)),"matrix_source":matrix_source,
        "levels":[levels.black,levels.white],"frames":records,
        "scope":"Same product decoder, MHC and colour developer; no CA warp or alignment; tone before external merge, six-digit rounded baseline tone; not a pure merge comparison"}))?;
    Ok(())
}
