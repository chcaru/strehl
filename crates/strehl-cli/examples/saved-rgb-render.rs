//! Develop saved camera-RGB patches through the actual product writer.
//! Requires bit-identical baseline pixels before emitting candidate images.
#[allow(dead_code)]
#[path = "../src/image_out.rs"]
mod image_out;

use anyhow::{Context, Result, ensure};
use serde_json::{Value, json};
use std::{fs::File, path::{Path, PathBuf}};
use strehl_core::{color, noise::Levels};

const SOFTWARE: &str = "strehl saved-rgb-render diagnostic (actual product development)";

fn read_json(path: &Path) -> Result<Value> {
    Ok(serde_json::from_slice(&std::fs::read(path)?)?)
}

fn read_rgb(path: &Path, pixels: usize) -> Result<Vec<f32>> {
    let bytes = std::fs::read(path)?;
    ensure!(bytes.len() == pixels * 3 * 4, "wrong RGB file extent: {}", path.display());
    let values: Vec<f32> = bytes.chunks_exact(4)
        .map(|b| f32::from_le_bytes(b.try_into().unwrap())).collect();
    ensure!(values.iter().all(|v| v.is_finite()), "nonfinite RGB input");
    Ok(values)
}

fn develop(rgb: &[f32], dev: &image_out::Develop) -> Vec<u16> {
    rgb.chunks_exact(3).flat_map(|v| image_out::develop_pixel([v[0], v[1], v[2]], dev)).collect()
}

fn main() -> Result<()> {
    let config_path = PathBuf::from(std::env::args_os().nth(1).context("configuration JSON required")?);
    let cfg = read_json(&config_path)?;
    let text = |k: &str| cfg[k].as_str().with_context(|| format!("missing {k}"));
    let receipt = read_json(Path::new(text("receipt")?))?;
    let w = cfg["width"].as_u64().context("width")? as usize;
    let h = cfg["height"].as_u64().context("height")? as usize;
    ensure!(w > 0 && h > 0 && w <= 400 && h <= 400, "bounded patch required");
    let bits = |k: &str| -> Result<[f32; 3]> {
        let values = receipt[k].as_array().with_context(|| format!("missing {k}"))?;
        ensure!(values.len() == 3, "wrong {k} length");
        let mut out = [0.0f32; 3];
        for (v, encoded) in out.iter_mut().zip(values) {
            let b = encoded.as_u64().context("f32 bits")?;
            ensure!(b <= u32::MAX as u64, "invalid f32 bits");
            *v = f32::from_bits(b as u32);
        }
        ensure!(out.iter().all(|v| v.is_finite()), "nonfinite {k}");
        Ok(out)
    };
    let wb = bits("wb_bits")?;
    let tone = bits("tone_bits")?;
    let levels = Levels {black: receipt["levels"][0].as_f64().context("black")? as f32,
        white: receipt["levels"][1].as_f64().context("white")? as f32};
    let xyz: [[f32; 3]; 3] = serde_json::from_value(cfg["xyz_to_cam"].clone())?;
    ensure!(xyz.iter().flatten().all(|v| v.is_finite()), "invalid camera matrix");
    let matrix = color::camera_to_srgb(xyz).context("singular camera matrix")?
        .with_saturation(levels, wb, 1.0);
    let mut dev = image_out::OutputSpace::Srgb.develop(Some(matrix));
    dev.tone = Some(image_out::Tone {black: tone[0], white: tone[1], contrast: tone[2]});
    dev.exposure_gain = 1.0;
    let baseline = develop(&read_rgb(Path::new(text("baseline_rgb")?), w*h)?, &dev);
    let mut decoder = tiff::decoder::Decoder::new(File::open(text("baseline_tiff")?)?)?;
    ensure!(decoder.dimensions()? == (w as u32, h as u32), "baseline TIFF shape differs");
    let tiff::decoder::DecodingResult::U16(expected) = decoder.read_image()? else {
        anyhow::bail!("baseline must be RGB16");
    };
    ensure!(expected.len() == baseline.len(), "baseline sample count differs");
    let differing = expected.iter().zip(&baseline).filter(|(a,b)| a != b).count();
    ensure!(differing == 0, "baseline development differs in {differing} u16 samples; no candidates written");
    let out = PathBuf::from(text("out")?);
    let root = PathBuf::from(env!("CARGO_MANIFEST_DIR")).parent().unwrap().parent().unwrap().canonicalize()?;
    ensure!(out.parent().context("output parent")?.canonicalize()?.starts_with(root), "output outside repository");
    std::fs::create_dir(&out)?;
    image_out::write_rgb16_described(&out.join("mhc.tiff"), w as u32, h as u32, &baseline, &dev)?;
    let mut names = vec!["mhc".to_owned()];
    for candidate in cfg["candidates"].as_array().context("candidates")? {
        let name = candidate["name"].as_str().context("candidate name")?;
        ensure!(!name.is_empty() && name.bytes().all(|v| v.is_ascii_alphanumeric() || v == b'-')
            && !names.iter().any(|n| n == name), "invalid or repeated candidate name");
        let rgb = read_rgb(Path::new(candidate["rgb"].as_str().context("candidate RGB")?), w*h)?;
        image_out::write_rgb16_described(&out.join(format!("{name}.tiff")), w as u32, h as u32,
            &develop(&rgb, &dev), &dev)?;
        names.push(name.to_owned());
    }
    let report = json!({"status":"BASELINE_PIXELS_EXACT", "baseline_differing_u16_samples":differing,
        "configuration":cfg, "tone_bits":tone.map(f32::to_bits), "wb_bits":wb.map(f32::to_bits),
        "xyz_to_cam_bits":xyz.map(|row| row.map(f32::to_bits)), "outputs":names,
        "scope":"saved camera RGB through actual develop_pixel; no RAW decode, gather, merge or tone remeasurement"});
    let file = std::fs::OpenOptions::new().write(true).create_new(true).open(out.join("receipt.json"))?;
    serde_json::to_writer_pretty(file, &report)?;
    println!("{}", json!({"status":"BASELINE_PIXELS_EXACT", "baseline_differing_u16_samples":0, "outputs":names}));
    Ok(())
}
