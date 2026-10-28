//! Experiment-only sequential, unaligned native RAW development for an external comparator.
//! Uses the product decoder, MHC and writer. No alignment, merge, RAW writes or CA warp.
#[allow(dead_code)]
#[path = "../src/image_out.rs"]
mod image_out;

use anyhow::{Context, Result, ensure};
use rayon::prelude::*;
use serde_json::{Value, json};
use sha2::{Digest, Sha256};
use std::{
    fs::{File, OpenOptions},
    io::{Read, Write},
    path::{Path, PathBuf},
};
use strehl_core::{color, noise::Levels};

const SOFTWARE: &str = "strehl weevil-batch-develop diagnostic; unaligned product MHC";

fn load(path: &Path) -> Result<Value> {
    Ok(serde_json::from_slice(&std::fs::read(path)?)?)
}
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
    loop {
        let n = file.read(&mut buf)?;
        if n == 0 {
            break;
        }
        h.update(&buf[..n]);
    }
    Ok(h.finalize().iter().map(|b| format!("{b:02x}")).collect())
}
fn make_dev(
    xyz: [[f32; 3]; 3],
    levels: Levels,
    wb: [f32; 3],
    tone: [f32; 3],
) -> Result<image_out::Develop> {
    ensure!(
        xyz.iter()
            .flatten()
            .chain(wb.iter())
            .chain(tone.iter())
            .all(|v| v.is_finite()),
        "nonfinite development metadata"
    );
    let matrix = color::camera_to_srgb(xyz)
        .context("singular camera matrix")?
        .with_saturation(levels, wb, 1.0);
    let mut dev = image_out::OutputSpace::Srgb.develop(Some(matrix));
    dev.tone = Some(image_out::Tone {
        black: tone[0],
        white: tone[1],
        contrast: tone[2],
    });
    dev.exposure_gain = 1.0;
    Ok(dev)
}

fn normalize_row(source: &[u16], y: usize, out: &mut [f32], levels: Levels, wb: [f32; 3]) {
    for (x, v) in out.iter_mut().enumerate() {
        let channel = match (y & 1, x & 1) {
            (0, 0) => 0,
            (1, 1) => 2,
            _ => 1,
        };
        *v = (source[x] as f32 - levels.black).max(0.0) * wb[channel]
            / (levels.white - levels.black);
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
    let levels = Levels {
        black: receipt["levels"][0].as_f64().context("black")? as f32,
        white: receipt["levels"][1].as_f64().context("white")? as f32,
    };
    let xyz = serde_json::from_value(cfg["expected_xyz_to_cam"].clone())?;
    let dev = make_dev(xyz, levels, bits("wb_bits")?, bits("tone_bits")?)?;
    let stem = "porous-source-129-frame129-raw";
    let cfa_path = dir.join(format!("{stem}-cfa.f32"));
    let expected_path = dir.join(format!("{stem}.tiff"));
    let cfa_bytes = std::fs::read(&cfa_path)?;
    ensure!(cfa_bytes.len() == 336 * 336 * 4, "fixture CFA extent");
    let cfa: Vec<f32> = cfa_bytes
        .chunks_exact(4)
        .map(|b| f32::from_le_bytes(b.try_into().unwrap()))
        .collect();
    // Independently decoded original u16 support overlaps this actual-consumer raw patch.
    // Exercise the same normalization function used below, not just saved f32 input.
    let original_path = Path::new(
        cfg["fixture_original_u16"]
            .as_str()
            .context("fixture_original_u16")?,
    );
    let original = std::fs::read(original_path)?;
    ensure!(original.len() >= 16, "original CFA header absent");
    let header: Vec<usize> = original[..16]
        .chunks_exact(4)
        .map(|b| u32::from_le_bytes(b.try_into().unwrap()) as usize)
        .collect();
    let (oy, ox, oh, ow) = (header[0], header[1], header[2], header[3]);
    ensure!(original.len() == 16 + oh * ow * 2, "original CFA extent");
    let samples: Vec<u16> = original[16..]
        .chunks_exact(2)
        .map(|b| u16::from_le_bytes(b.try_into().unwrap()))
        .collect();
    let patch = receipt["patches"]
        .as_array()
        .context("fixture patches")?
        .iter()
        .find(|p| p["stem"] == stem)
        .context("fixture patch")?;
    let px = patch["padded_origin_xy"][0].as_u64().context("fixture x")? as usize;
    let py = patch["padded_origin_xy"][1].as_u64().context("fixture y")? as usize;
    ensure!(
        px % 2 == 0
            && py % 2 == 0
            && px >= ox
            && py >= oy
            && px + 336 <= ox + ow
            && py + 336 <= oy + oh,
        "fixture overlap/phase"
    );
    let mut normalized = vec![0.0f32; 336 * 336];
    for y in 0..336 {
        let offset = (py - oy + y) * ow + px - ox;
        normalize_row(
            &samples[offset..offset + 336],
            y,
            &mut normalized[y * 336..(y + 1) * 336],
            levels,
            bits("wb_bits")?,
        );
    }
    let normalized_differences = normalized
        .iter()
        .zip(&cfa)
        .filter(|(a, b)| a.to_bits() != b.to_bits())
        .count();
    ensure!(
        normalized_differences == 0,
        "u16 normalization differs in {normalized_differences} f32 samples"
    );
    let actual_path = out.join("golden.tiff");
    image_out::write_demosaiced(&actual_path, 336, 336, &cfa, &dev)?;
    let decode = |p: &Path| -> Result<Vec<u16>> {
        let mut d = tiff::decoder::Decoder::new(File::open(p)?)?;
        ensure!(d.dimensions()? == (336, 336), "fixture dimensions");
        let tiff::decoder::DecodingResult::U16(v) = d.read_image()? else {
            anyhow::bail!("fixture type");
        };
        Ok(v)
    };
    let a = decode(&actual_path)?;
    let b = decode(&expected_path)?;
    ensure!(
        a.len() == b.len() && a.len() == 336 * 336 * 3,
        "fixture sample count"
    );
    let differing = a.iter().zip(&b).filter(|(x, y)| x != y).count();
    ensure!(
        differing == 0,
        "actual developer fixture differs in {differing} samples"
    );
    Ok(
        json!({"status":"EXACT", "rgb16_samples":a.len(), "differing":differing,
        "normalized_f32_samples":normalized.len(),"normalized_f32_differences":normalized_differences,
        "original_u16_sha256":hash(original_path)?,
        "fixture_cfa_sha256":hash(&cfa_path)?, "fixture_tiff_sha256":hash(&expected_path)?}),
    )
}

fn main() -> Result<()> {
    let started = std::time::Instant::now();
    rayon::ThreadPoolBuilder::new()
        .num_threads(4)
        .build_global()?;
    let config_path = PathBuf::from(
        std::env::args_os()
            .nth(1)
            .context("configuration JSON required")?,
    );
    let config_hash = hash(&config_path)?;
    let cfg = load(&config_path)?;
    let manifest_path = PathBuf::from(cfg["input_order"].as_str().context("input_order")?);
    let manifest_hash = hash(&manifest_path)?;
    ensure!(
        Some(manifest_hash.as_str()) == cfg["input_order_sha256"].as_str(),
        "baseline input order content changed"
    );
    let manifest = load(&manifest_path)?;
    let inputs = manifest.as_array().context("baseline input-order array")?;
    ensure!(inputs.len() == 299, "all 299 originals are required");
    let input_dir =
        PathBuf::from(cfg["input_dir"].as_str().context("input_dir")?).canonicalize()?;
    let mut paths = Vec::with_capacity(299);
    let mut input_metadata = Vec::with_capacity(299);
    // Full content preflight precedes the first original decode; no subset mode.
    for (i, row) in inputs.iter().enumerate() {
        ensure!(
            row["index"].as_u64() == Some(i as u64),
            "baseline ordinal changed"
        );
        let path = PathBuf::from(row["path"].as_str().context("input path")?);
        ensure!(
            path.canonicalize()?.parent() == Some(input_dir.as_path()),
            "input escaped frozen directory"
        );
        ensure!(
            path.file_name().unwrap().to_str() == Some(format!("DSC{:05}.ARW", i + 1).as_str()),
            "baseline filename/order changed"
        );
        let metadata = std::fs::metadata(&path)?;
        ensure!(
            Some(metadata.len()) == row["bytes"].as_u64(),
            "input byte count changed"
        );
        ensure!(
            Some(hash(&path)?.as_str()) == row["sha256"].as_str(),
            "input content changed: {}",
            path.display()
        );
        input_metadata.push((metadata.len(), metadata.modified()?));
        paths.push(path);
    }
    let fixture_bindings = cfg["fixture_bindings"]
        .as_array()
        .context("fixture bindings")?;
    for row in fixture_bindings {
        let path = Path::new(row["path"].as_str().context("fixture path")?);
        ensure!(
            Some(hash(path)?.as_str()) == row["sha256"].as_str(),
            "frozen golden input changed"
        );
        ensure!(
            Some(std::fs::metadata(path)?.len()) == row["bytes"].as_u64(),
            "frozen golden extent changed"
        );
    }
    let out = PathBuf::from(cfg["out"].as_str().context("out")?);
    let root = PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .parent()
        .unwrap()
        .parent()
        .unwrap()
        .canonicalize()?;
    ensure!(
        out.parent()
            .context("output parent")?
            .canonicalize()?
            .starts_with(&root),
        "output outside workspace"
    );
    std::fs::create_dir(&out)?;
    let witness = golden(&cfg, &out)?;
    save(&out.join("golden.json"), &witness)?;
    let frames_dir = out.join("frames");
    std::fs::create_dir(&frames_dir)?;
    let expected_xyz: [[f32; 3]; 3] = serde_json::from_value(cfg["expected_xyz_to_cam"].clone())?;
    let wb: [f32; 3] = [1637.0 / 1024.0, 1.0, 2774.0 / 1024.0];
    let tone: [f32; 3] = serde_json::from_value(cfg["tone"].clone())?;
    ensure!(
        tone == [-0.00026, 0.27030, 0.55],
        "frozen rounded weevil baseline tone changed"
    );
    let frame0 = strehl_raw::decode(&paths[0])?;
    ensure!(
        frame0.camera == "ILCE-7CM2" && frame0.iso == Some(100.0),
        "baseline camera/ISO changed"
    );
    let levels = frame0.levels;
    ensure!(
        levels.black == 512.0 && levels.white == 15360.0,
        "baseline development levels changed"
    );
    let (xyz, matrix_source) = frame0
        .xyz_to_cam_rgb_with_source()
        .context("camera matrix absent")?;
    ensure!(xyz == expected_xyz, "baseline D65 camera matrix changed");
    let (w, h) = (frame0.active.width, frame0.active.height);
    // Export the decoder's whole active area. The prior Helicon application
    // witness was vitamin-C, not proof of this corpus's native active width.
    ensure!(
        w >= 6896 && h >= 4596 && w % 2 == 0 && h % 2 == 0,
        "invalid full active dimensions"
    );
    let dev = make_dev(xyz, levels, wb, tone)?;
    let mut first = Some(frame0);
    let mut records = Vec::with_capacity(299);
    let mut output_paths = Vec::with_capacity(299);
    let mut expected_icc: Option<Vec<u8>> = None;
    for (i, path) in paths.iter().enumerate() {
        let frame_started = std::time::Instant::now();
        let frame = if i == 0 {
            first.take().unwrap()
        } else {
            strehl_raw::decode(path)?
        };
        ensure!(
            (frame.active.width, frame.active.height) == (w, h),
            "mixed active geometry"
        );
        ensure!(
            frame.active.x % 2 == 0 && frame.active.y % 2 == 0,
            "active origin changes Bayer phase"
        );
        ensure!(
            frame.camera == "ILCE-7CM2" && frame.iso == Some(100.0),
            "mixed camera/ISO"
        );
        ensure!(
            frame.levels.black == levels.black && frame.levels.white == levels.white,
            "mixed levels"
        );
        ensure!(frame.xyz_to_cam_rgb() == Some(xyz), "mixed camera matrix");
        let frame_wb = frame.wb_gains().context("frame WB absent")?;
        ensure!(
            frame_wb.map(f32::to_bits) == wb.map(f32::to_bits),
            "manual WB changed"
        );
        let mut mosaic = vec![0.0f32; w * h];
        mosaic.par_chunks_mut(w).enumerate().for_each(|(y, row)| {
            normalize_row(frame.active_row(y), y, row, levels, wb);
        });
        ensure!(
            mosaic.par_iter().all(|v| v.is_finite()),
            "nonfinite normalized CFA"
        );
        let tiff_path = frames_dir.join(format!("DSC{:05}.tiff", i + 1));
        image_out::write_demosaiced(&tiff_path, w, h, &mosaic, &dev)?;
        drop(mosaic);
        let mut decoder = tiff::decoder::Decoder::new(File::open(&tiff_path)?)?;
        ensure!(
            decoder.dimensions()? == (w as u32, h as u32),
            "written TIFF dimensions changed"
        );
        ensure!(
            decoder.colortype()? == tiff::ColorType::RGB(16),
            "written TIFF is not RGB16"
        );
        let icc = decoder.get_tag_u8_vec(tiff::tags::Tag::IccProfile)?;
        ensure!(!icc.is_empty(), "written TIFF has no ICC profile");
        if let Some(expected) = &expected_icc {
            ensure!(*expected == icc, "mixed output ICC profiles");
        } else {
            expected_icc = Some(icc);
        }
        drop(decoder);
        let after = std::fs::metadata(path)?;
        ensure!(
            (after.len(), after.modified()?) == input_metadata[i],
            "original metadata changed during development"
        );
        let record = json!({"ordinal":i, "input":inputs[i], "input_wb_bits":frame_wb.map(f32::to_bits),
            "raw_buffer_wh":[frame.stride, frame.buffer_height],
            "raw_active_xywh":[frame.active.x, frame.active.y, w, h], "output":tiff_path,
            "output_sha256":hash(&tiff_path)?, "output_bytes":std::fs::metadata(&tiff_path)?.len(),
            "output_wh":[w,h], "output_type":"RGB16+ICC", "seconds":frame_started.elapsed().as_secs_f64()});
        save(&out.join(format!("frame-{i:03}.json")), &record)?;
        records.push(record);
        output_paths.push(tiff_path);
        println!(
            "developed {}/299 {}",
            i + 1,
            path.file_name().unwrap().to_string_lossy()
        );
    }
    // Whole corpus postflight, including originals decoded early in the run.
    for (i, path) in paths.iter().enumerate() {
        let metadata = std::fs::metadata(path)?;
        ensure!(
            (metadata.len(), metadata.modified()?) == input_metadata[i],
            "original metadata changed after export"
        );
        ensure!(
            Some(hash(path)?.as_str()) == inputs[i]["sha256"].as_str(),
            "original content changed after export"
        );
    }
    for row in fixture_bindings {
        let path = Path::new(row["path"].as_str().context("fixture path")?);
        ensure!(
            Some(hash(path)?.as_str()) == row["sha256"].as_str(),
            "golden input changed after export"
        );
    }
    ensure!(
        hash(&manifest_path)? == manifest_hash && hash(&config_path)? == config_hash,
        "configuration/manifest changed"
    );
    let mut list = OpenOptions::new()
        .write(true)
        .create_new(true)
        .open(out.join("inputs.txt"))?;
    for path in &output_paths {
        writeln!(list, "{}", path.display())?;
    }
    let executable = std::env::current_exe()?;
    save(
        &out.join("receipt.json"),
        &json!({"status":"299_UNALIGNED_NATIVE_RGB16_DEVELOPED",
        "configuration":cfg, "configuration_sha256":config_hash, "input_order_sha256":manifest_hash,
        "executable":executable, "executable_sha256":hash(&executable)?,
        "package_version":env!("CARGO_PKG_VERSION"), "worker_count":rayon::current_num_threads(),
        "golden":witness, "wb_bits":wb.map(f32::to_bits), "tone_bits":tone.map(f32::to_bits),
        "xyz_to_cam_bits":xyz.map(|r| r.map(f32::to_bits)), "matrix_source":matrix_source,
        "levels":[levels.black,levels.white], "active_wh":[w,h], "frames":records,
        "input_content_and_metadata_unchanged":true, "seconds":started.elapsed().as_secs_f64(),
        "scope":"Full-workflow comparator preparation: product RAW decode/MHC/developer; no CA warp, alignment or merge. Fixed as-shot WB; rounded logged baseline tone applied before external merge. This differs from native RAW merge and is not a pure merger comparison."}),
    )?;
    println!(
        "complete: 299 original hashes revalidated; {}x{} RGB16+ICC, 4 workers",
        w, h
    );
    Ok(())
}
