//! Develop one final reference-cell camera-RGB field; no CFA interpolation.
#[allow(dead_code)]
#[path = "../src/image_out.rs"]
mod image_out;

use anyhow::{Context, Result, ensure};
use rayon::prelude::*;
use serde::{Deserialize, Serialize};
use serde_json::{Value, json};
use sha2::{Digest, Sha256};
use std::{
    fs::{File, OpenOptions},
    io::{Read, Write},
    path::{Path, PathBuf},
};
use strehl_core::{color, noise::Levels};

const SOFTWARE: &str = "strehl direct-rgb-develop diagnostic; final RGB, no demosaic";

#[derive(Clone, Debug, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
struct FileBinding {
    path: PathBuf,
    sha256: String,
    bytes: u64,
}

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct Config {
    schema: u32,
    camera_rgb: FileBinding,
    delivery_receipt: FileBinding,
    development_receipt: FileBinding,
    out_dir: PathBuf,
    expected_executable_sha256: String,
}

#[derive(Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
struct Development {
    schema: u32,
    levels_bits: [u32; 2],
    wb_bits: [u32; 3],
    xyz_to_cam_bits: [[u32; 3]; 3],
    tone_bits: [u32; 3],
    exposure_bits: u32,
    source_bindings: Vec<FileBinding>,
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

fn bind(value: &FileBinding) -> Result<()> {
    ensure!(
        std::fs::metadata(&value.path)?.len() == value.bytes,
        "bound file size differs"
    );
    ensure!(
        hash(&value.path)? == value.sha256,
        "bound file content differs: {}",
        value.path.display()
    );
    Ok(())
}

fn record(path: &Path) -> Result<FileBinding> {
    Ok(FileBinding {
        path: path.canonicalize()?,
        bytes: std::fs::metadata(path)?.len(),
        sha256: hash(path)?,
    })
}

fn save(path: &Path, value: &Value) -> Result<()> {
    let mut f = OpenOptions::new().write(true).create_new(true).open(path)?;
    serde_json::to_writer_pretty(&mut f, value)?;
    writeln!(f)?;
    Ok(())
}

fn pixel_hash(values: &[u16]) -> String {
    let mut h = Sha256::new();
    let mut bytes = vec![0u8; 65536];
    for chunk in values.chunks(bytes.len() / 2) {
        for (v, out) in chunk.iter().zip(bytes.as_chunks_mut::<2>().0.iter_mut()) {
            out.copy_from_slice(&v.to_le_bytes());
        }
        h.update(&bytes[..chunk.len() * 2]);
    }
    h.finalize().iter().map(|b| format!("{b:02x}")).collect()
}

fn make_dev(meta: &Development) -> Result<(image_out::Develop, Levels, [f32; 3])> {
    ensure!(meta.schema == 1, "unsupported development schema");
    let [black, white] = meta.levels_bits.map(f32::from_bits);
    let levels = Levels { black, white };
    let wb = meta.wb_bits.map(f32::from_bits);
    let xyz = meta.xyz_to_cam_bits.map(|row| row.map(f32::from_bits));
    let tone = meta.tone_bits.map(f32::from_bits);
    ensure!(
        meta.exposure_bits == 1.0f32.to_bits(),
        "fixed exposure must be exactly one"
    );
    ensure!(
        black.is_finite() && white.is_finite() && black >= 0.0 && white > black,
        "invalid level bits"
    );
    ensure!(
        wb.iter().all(|v| v.is_finite() && *v > 0.0) && wb[1].to_bits() == 1.0f32.to_bits(),
        "finite green-normalized as-shot WB required"
    );
    ensure!(
        xyz.iter()
            .flatten()
            .chain(tone.iter())
            .all(|v| v.is_finite()),
        "nonfinite matrix/tone"
    );
    ensure!(
        tone[1] > tone[0] && (0.0..=1.0).contains(&tone[2]),
        "invalid pinned tone"
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
    Ok((dev, levels, wb))
}

fn main() -> Result<()> {
    let started = std::time::Instant::now();
    rayon::ThreadPoolBuilder::new()
        .num_threads(4)
        .build_global()?;
    let mut args = std::env::args_os().skip(1);
    let config_path = PathBuf::from(args.next().context("configuration JSON required")?);
    ensure!(
        args.next().is_none(),
        "exactly one configuration argument required"
    );
    let config_hash = hash(&config_path)?;
    let cfg: Config = serde_json::from_slice(&std::fs::read(&config_path)?)?;
    ensure!(cfg.schema == 1, "unsupported renderer configuration");
    let executable = std::env::current_exe()?;
    ensure!(
        hash(&executable)? == cfg.expected_executable_sha256,
        "executable differs"
    );
    for binding in [
        &cfg.camera_rgb,
        &cfg.delivery_receipt,
        &cfg.development_receipt,
    ] {
        bind(binding)?;
    }
    let delivery: Value = serde_json::from_slice(&std::fs::read(&cfg.delivery_receipt.path)?)?;
    ensure!(
        delivery["schema"] == 1
            && delivery["status"] == "COMPLETE_REFERENCE_CELL_CAMERA_RGB"
            && delivery["complete"] == true
            && delivery["dtype"] == "<f4"
            && delivery["units"] == "black-subtracted-camera-DN"
            && delivery["channels"] == json!(["R", "G", "B"])
            && delivery["demosaic_calls"] == 0
            && delivery["remosaic_calls"] == 0,
        "input is not declared final reference-cell RGB"
    );
    let delivered: FileBinding = serde_json::from_value(delivery["camera_rgb"].clone())?;
    ensure!(
        delivered.sha256 == cfg.camera_rgb.sha256
            && delivered.bytes == cfg.camera_rgb.bytes
            && delivered.path.canonicalize()? == cfg.camera_rgb.path.canonicalize()?,
        "delivery/input binding differs"
    );
    let [height, width, channels]: [usize; 3] = serde_json::from_value(delivery["shape"].clone())?;
    ensure!(
        channels == 3 && (1..=8192).contains(&width) && (1..=8192).contains(&height),
        "unsupported delivered extent"
    );
    let sample_count = width
        .checked_mul(height)
        .and_then(|v| v.checked_mul(3))
        .context("sample overflow")?;
    ensure!(
        cfg.camera_rgb.bytes == (sample_count * 4) as u64,
        "exact f32 input size differs"
    );
    let development: Development =
        serde_json::from_slice(&std::fs::read(&cfg.development_receipt.path)?)?;
    ensure!(
        !development.source_bindings.is_empty(),
        "development needs pinned provenance"
    );
    let mut preserved = vec![
        cfg.camera_rgb.clone(),
        cfg.delivery_receipt.clone(),
        cfg.development_receipt.clone(),
    ];
    preserved.extend(development.source_bindings.iter().cloned());
    for value in &preserved {
        bind(value)?;
    }
    let stats: Vec<_> = preserved
        .iter()
        .map(|value| -> Result<_> {
            let m = std::fs::metadata(&value.path)?;
            Ok((m.len(), m.modified()?))
        })
        .collect::<Result<_>>()?;
    let (dev, levels, wb) = make_dev(&development)?;
    ensure!(!cfg.out_dir.exists(), "fresh output directory required");
    std::fs::create_dir_all(&cfg.out_dir)?;
    let bytes = std::fs::read(&cfg.camera_rgb.path)?;
    ensure!(bytes.len() == sample_count * 4, "read f32 extent differs");
    let camera: Vec<f32> = bytes
        .as_chunks::<4>()
        .0
        .iter()
        .map(|v| f32::from_le_bytes(*v))
        .collect();
    drop(bytes);
    ensure!(
        camera.iter().all(|v| v.is_finite()),
        "nonfinite camera RGB input"
    );
    let negative_samples = camera.iter().filter(|v| **v < 0.0).count();
    let mut rgb = vec![0u16; sample_count];
    let range = levels.range();
    rgb.par_chunks_exact_mut(3)
        .zip(camera.par_chunks_exact(3))
        .try_for_each(|(out, input)| -> Result<()> {
            // The reconstruction is already black-subtracted. Preserve its signed
            // values through WB/range; the existing developer owns later handling.
            let normalized = [
                input[0] * wb[0] / range,
                input[1] * wb[1] / range,
                input[2] * wb[2] / range,
            ];
            ensure!(
                normalized.iter().all(|v| v.is_finite()),
                "nonfinite normalized camera RGB"
            );
            out.copy_from_slice(&image_out::develop_pixel(normalized, &dev));
            Ok(())
        })?;
    let master = cfg.out_dir.join("rgb16-master.tiff");
    image_out::write_rgb16_described(&master, width as u32, height as u32, &rgb, &dev)?;
    let mut limits = tiff::decoder::Limits::default();
    // Tag decoding shares this limit; tiny commissioning images still carry
    // the complete ICC profile. Keep a bounded allowance for those metadata.
    limits.decoding_buffer_size = (sample_count * 2).max(1 << 20);
    let mut decoder = tiff::decoder::Decoder::new(File::open(&master)?)?.with_limits(limits);
    ensure!(
        decoder.dimensions()? == (width as u32, height as u32)
            && decoder.colortype()? == tiff::ColorType::RGB(16),
        "written RGB16 extent/type differs"
    );
    let icc = decoder.get_tag_u8_vec(tiff::tags::Tag::IccProfile)?;
    ensure!(!icc.is_empty(), "native writer omitted ICC");
    let description = decoder.get_tag_ascii_string(tiff::tags::Tag::ImageDescription)?;
    let tiff::decoder::DecodingResult::U16(decoded) = decoder.read_image()? else {
        anyhow::bail!("written RGB16 sample type differs");
    };
    ensure!(decoded == rgb, "TIFF pixel readback differs");
    drop(decoded);
    for (binding, expected) in preserved.iter().zip(&stats) {
        bind(binding)?;
        let now = std::fs::metadata(&binding.path)?;
        ensure!(
            (now.len(), now.modified()?) == *expected,
            "retained input metadata changed"
        );
    }
    ensure!(
        hash(&config_path)? == config_hash && hash(&executable)? == cfg.expected_executable_sha256,
        "configuration/executable changed"
    );
    let receipt = json!({
        "schema":1,"status":"COMPLETE_DIRECT_RGB_NATIVE_DEVELOPMENT","complete":true,"software":SOFTWARE,
        "configuration":record(&config_path)?,"executable":record(&executable)?,
        "package_version":env!("CARGO_PKG_VERSION"),"worker_count":rayon::current_num_threads(),
        "signed_camera_rgb_master":cfg.camera_rgb,"delivery_receipt":cfg.delivery_receipt,
        "development_receipt":cfg.development_receipt,"development":development,
        "native_dimensions":[width,height],"rgb16":record(&master)?,
        "rgb16_pixels_sha256":pixel_hash(&rgb),"pixel_readback_exact":true,
        "icc_sha256":Sha256::digest(&icc).iter().map(|b| format!("{b:02x}")).collect::<String>(),"image_description":description,
        "negative_camera_samples_preserved_until_developer":negative_samples,
        "normalization":"signed black-subtracted DN * as-shot WB / (white-black); exposure1; no added clamp",
        "native_consumer":"image_out::develop_pixel + write_rgb16_described",
        "demosaic_calls":0,"remosaic_calls":0,"tone_measured_from_output":false,
        "retained_input_bytes_and_metadata_unchanged":true,"RAW_reads":0,
        "entire_output":true,"quality_claim":false,"photographic_admission":false,
        "seconds":started.elapsed().as_secs_f64()
    });
    save(&cfg.out_dir.join("receipt.json"), &receipt)?;
    println!("complete direct RGB development: {width}x{height}, signed research master retained");
    Ok(())
}
