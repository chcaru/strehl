//! Develop one final physical RGGB CFA field with one actual core MHC stage.
#[allow(dead_code)]
#[path = "../../../../crates/strehl-cli/src/image_out.rs"]
mod image_out;

use anyhow::{Context, Result, ensure};
use rayon::prelude::*;
use serde::{Deserialize, Serialize};
use serde_json::{Value, json};
use sha2::{Digest, Sha256};
use std::{
    fs::{File, OpenOptions},
    io::{BufReader, BufWriter, Read, Write},
    path::{Path, PathBuf},
};
use strehl_core::{
    color,
    demosaic::{Mosaic, demosaic_malvar_row},
    noise::Levels,
};

const SOFTWARE: &str = "strehl native-cfa-develop diagnostic; physical final CFA, one MHC stage";

#[derive(Clone, Debug, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
struct FileBinding {
    path: PathBuf,
    sha256: String,
    bytes: u64,
}

#[derive(Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
struct Config {
    schema: u32,
    cfa: FileBinding,
    width: usize,
    height: usize,
    active_origin_xy: [usize; 2],
    physical_pattern: String,
    units: String,
    development_receipt: FileBinding,
    out_dir: PathBuf,
    expected_executable_sha256: String,
    parity_reference: Option<ParityReference>,
}
#[derive(Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
struct ParityReference {
    rgb16: FileBinding,
    linear_rgb32: FileBinding,
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
    let bytes = serde_json::to_vec_pretty(value)?;
    ensure!(bytes.len() <= 4 << 20, "JSON output exceeds4MiB");
    let mut f = OpenOptions::new().write(true).create_new(true).open(path)?;
    f.write_all(&bytes)?;
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

fn read_json<T: serde::de::DeserializeOwned>(path: &Path) -> Result<T> {
    ensure!(
        std::fs::metadata(path)?.len() <= 4 << 20,
        "JSON input exceeds4MiB"
    );
    Ok(serde_json::from_slice(&std::fs::read(path)?)?)
}
fn f32_hash(values: &[f32]) -> String {
    let mut h = Sha256::new();
    let mut bytes = vec![0u8; 65536];
    for chunk in values.chunks(bytes.len() / 4) {
        for (value, dst) in chunk.iter().zip(bytes.as_chunks_mut::<4>().0.iter_mut()) {
            dst.copy_from_slice(&value.to_le_bytes());
        }
        h.update(&bytes[..chunk.len() * 4]);
    }
    h.finalize().iter().map(|v| format!("{v:02x}")).collect()
}
fn write_f32(path: &Path, values: &[f32]) -> Result<()> {
    let mut f = BufWriter::new(OpenOptions::new().write(true).create_new(true).open(path)?);
    let mut bytes = vec![0u8; 65536];
    for chunk in values.chunks(bytes.len() / 4) {
        for (value, dst) in chunk.iter().zip(bytes.as_chunks_mut::<4>().0.iter_mut()) {
            dst.copy_from_slice(&value.to_le_bytes());
        }
        f.write_all(&bytes[..chunk.len() * 4])?;
    }
    f.flush()?;
    ensure!(
        hash(path)? == f32_hash(values),
        "f32 write/read byte hash differs"
    );
    Ok(())
}
fn tiff_pixels(path: &Path, w: usize, h: usize, float: bool) -> Result<String> {
    let mut limits = tiff::decoder::Limits::default();
    limits.decoding_buffer_size = (w * h * 3 * 4).max(1 << 20);
    let mut d = tiff::decoder::Decoder::new(BufReader::new(File::open(path)?))?.with_limits(limits);
    ensure!(
        d.dimensions()? == (w as u32, h as u32)
            && d.colortype()? == tiff::ColorType::RGB(if float { 32 } else { 16 }),
        "TIFF geometry/sample type differs"
    );
    let result = match d.read_image()? {
        tiff::decoder::DecodingResult::F32(v) if float => {
            ensure!(
                v.len() == w * h * 3 && v.iter().all(|x| x.is_finite()),
                "finite complete RGB32 required"
            );
            f32_hash(&v)
        }
        tiff::decoder::DecodingResult::U16(v) if !float => {
            ensure!(v.len() == w * h * 3, "complete RGB16 required");
            pixel_hash(&v)
        }
        _ => anyhow::bail!("TIFF decoded sample storage differs"),
    };
    ensure!(!d.more_images(), "single TIFF page required");
    Ok(result)
}
fn material(path: &Path) -> Result<Value> {
    use tiff::tags::Tag;
    let mut limits = tiff::decoder::Limits::default();
    limits.decoding_buffer_size = 1 << 20;
    let mut d = tiff::decoder::Decoder::new(BufReader::new(File::open(path)?))?.with_limits(limits);
    let description = d.get_tag_ascii_string(Tag::ImageDescription)?;
    let icc = d.get_tag_u8_vec(Tag::IccProfile)?;
    ensure!(!icc.is_empty(), "ICC absent");
    let mut tags = std::collections::BTreeMap::new();
    for tag in [
        Tag::BitsPerSample,
        Tag::PhotometricInterpretation,
        Tag::SamplesPerPixel,
        Tag::SampleFormat,
        Tag::Orientation,
        Tag::XResolution,
        Tag::YResolution,
        Tag::ResolutionUnit,
    ] {
        tags.insert(format!("{tag:?}"), format!("{:?}", d.get_tag(tag).ok()));
    }
    Ok(
        json!({"description":description,"icc_sha256":Sha256::digest(&icc).iter().map(|v|format!("{v:02x}")).collect::<String>(),"material_tags":tags}),
    )
}
fn run(config_path: &Path) -> Result<()> {
    let started = std::time::Instant::now();
    rayon::ThreadPoolBuilder::new()
        .num_threads(4)
        .build_global()?;
    let config_binding = record(config_path)?;
    let cfg: Config = read_json(config_path)?;
    ensure!(cfg.schema == 1, "unsupported renderer configuration");
    ensure!(
        cfg.physical_pattern == "RGGB" && cfg.units == "black-subtracted-DN",
        "physical RGGB black-subtracted CFA required"
    );
    ensure!(
        cfg.active_origin_xy
            .iter()
            .all(|v| *v <= 8192 && v % 2 == 0),
        "even/even active-native origin required; no silent phase relabeling"
    );
    ensure!(
        (8..=8192).contains(&cfg.width) && (8..=8192).contains(&cfg.height),
        "unsupported delivered extent"
    );
    let (w, h) = (cfg.width, cfg.height);
    let n = w.checked_mul(h).context("extent overflow")?;
    ensure!(
        n <= 40_000_000 && cfg.cfa.bytes == (4 * n) as u64,
        "bounded exact native f32 CFA extent required"
    );
    let executable = std::env::current_exe()?;
    ensure!(
        hash(&executable)? == cfg.expected_executable_sha256,
        "executable differs"
    );
    bind(&cfg.cfa)?;
    bind(&cfg.development_receipt)?;
    let development: Development = read_json(&cfg.development_receipt.path)?;
    ensure!(
        !development.source_bindings.is_empty(),
        "held development provenance required"
    );
    let (dev, levels, wb) = make_dev(&development)?;
    let mut preserved = vec![cfg.cfa.clone(), cfg.development_receipt.clone()];
    preserved.extend(development.source_bindings.iter().cloned());
    if let Some(golden) = &cfg.parity_reference {
        preserved.push(golden.rgb16.clone());
        preserved.push(golden.linear_rgb32.clone());
    }
    for value in &preserved {
        bind(value)?;
    }
    let stamps = preserved
        .iter()
        .map(|v| -> Result<_> {
            let m = std::fs::metadata(&v.path)?;
            Ok((m.len(), m.modified()?))
        })
        .collect::<Result<Vec<_>>>()?;
    ensure!(!cfg.out_dir.exists(), "fresh output directory required");
    std::fs::create_dir_all(&cfg.out_dir)?;
    let result = (|| -> Result<()> {
        let bytes = std::fs::read(&cfg.cfa.path)?;
        ensure!(bytes.len() == 4 * n, "read CFA size differs");
        let mut mosaic = bytes
            .as_chunks::<4>()
            .0
            .iter()
            .map(|v| f32::from_le_bytes(*v))
            .collect::<Vec<_>>();
        drop(bytes);
        ensure!(
            mosaic.iter().all(|v| v.is_finite()),
            "nonfinite final CFA refused before development"
        );
        let negatives = mosaic.iter().filter(|v| **v < 0.).count();
        let cfa_path = cfg.out_dir.join("final-cfa-dn.f32le");
        write_f32(&cfa_path, &mosaic)?;
        ensure!(
            hash(&cfa_path)? == cfg.cfa.sha256,
            "signed CFA copy differs"
        );
        let gains = [wb[0] / wb[1], 1.0, 1.0, wb[2] / wb[1]];
        mosaic.par_chunks_mut(w).enumerate().for_each(|(y, row)| {
            for (x, v) in row.iter_mut().enumerate() {
                // Literal held writer order. This final display boundary clamps
                // negative CFA; the separate signed CFA master preserves it.
                *v = v.max(0.0) * gains[2 * (y % 2) + x % 2] * 1.0 / levels.range();
            }
        });
        ensure!(
            mosaic.iter().all(|v| v.is_finite()),
            "nonfinite normalized CFA"
        );
        let m = Mosaic {
            data: &mosaic,
            width: w,
            height: h,
        };
        let mut camera = vec![0f32; n * 3];
        camera
            .par_chunks_mut(w * 3)
            .enumerate()
            .for_each(|(y, row)| demosaic_malvar_row(&m, y, row));
        ensure!(
            camera.iter().all(|v| v.is_finite()),
            "nonfinite actual final MHC camera RGB"
        );
        drop(mosaic);
        let camera_path = cfg.out_dir.join("camera-rgb-normalized.f32le");
        write_f32(&camera_path, &camera)?;
        let camera_negative = camera.iter().filter(|v| **v < 0.).count();
        let matrix = dev.matrix.context("scene-linear matrix required")?;
        let mut linear = vec![0f32; n * 3];
        linear
            .par_chunks_exact_mut(3)
            .zip(camera.par_chunks_exact(3))
            .for_each(|(dst, src)| {
                dst.copy_from_slice(&matrix.develop([src[0], src[1], src[2]]));
            });
        ensure!(
            linear.iter().all(|v| v.is_finite()),
            "nonfinite developed linear RGB"
        );
        let linear_sha = f32_hash(&linear);
        let linear_path = cfg.out_dir.join("linear-master.tiff");
        let tone = dev
            .tone
            .context("held tone required; no output tone fitting")?;
        let image = strehl_edit::LinearImage {
            width: w as u32,
            height: h as u32,
            pixels: linear,
            origin: strehl_edit::ImageOrigin::SceneLinear,
            baseline: Some(strehl_edit::DisplayBaseline {
                black: tone.black,
                white: tone.white,
                contrast: tone.contrast,
                exposure_gain: dev.exposure_gain,
            }),
            baked_recipe: None,
        };
        strehl_edit::save_linear_tiff(&linear_path, &image)?;
        drop(image);
        let mut rgb = vec![0u16; n * 3];
        rgb.par_chunks_exact_mut(3)
            .zip(camera.par_chunks_exact(3))
            .for_each(|(dst, src)| {
                dst.copy_from_slice(&image_out::develop_pixel([src[0], src[1], src[2]], &dev));
            });
        drop(camera);
        let rgb_sha = pixel_hash(&rgb);
        let master = cfg.out_dir.join("rgb16-master.tiff");
        image_out::write_rgb16_described(&master, w as u32, h as u32, &rgb, &dev)?;
        drop(rgb);
        ensure!(
            tiff_pixels(&master, w, h, false)? == rgb_sha
                && tiff_pixels(&linear_path, w, h, true)? == linear_sha,
            "full writer pixel readback differs"
        );
        let rgb_material = material(&master)?;
        let linear_material = material(&linear_path)?;
        let parity = if let Some(golden) = &cfg.parity_reference {
            let rgb_exact = tiff_pixels(&golden.rgb16.path, w, h, false)? == rgb_sha;
            let linear_exact = tiff_pixels(&golden.linear_rgb32.path, w, h, true)? == linear_sha;
            let rgb_metadata = material(&golden.rgb16.path)? == rgb_material;
            let linear_metadata = material(&golden.linear_rgb32.path)? == linear_material;
            let value = json!({"requested":true,"rgb16_pixel_exact":rgb_exact,"linear_pixel_exact":linear_exact,
                "rgb16_material_exact":rgb_metadata,"linear_material_exact":linear_metadata,"references":golden});
            save(&cfg.out_dir.join("parity.json"), &value)?;
            ensure!(
                rgb_exact && linear_exact && rgb_metadata && linear_metadata,
                "requested held CFA development parity failed"
            );
            value
        } else {
            json!({"requested":false,"not_a_parity_claim":true})
        };
        for (binding, stamp) in preserved.iter().zip(&stamps) {
            bind(binding)?;
            let m = std::fs::metadata(&binding.path)?;
            ensure!(
                (m.len(), m.modified()?) == *stamp,
                "retained input metadata changed"
            );
        }
        ensure!(
            hash(config_path)? == config_binding.sha256
                && hash(&executable)? == cfg.expected_executable_sha256,
            "configuration/executable changed"
        );
        let mut receipt = json!({"schema":1,"status":"COMPLETE_NATIVE_CFA_DEVELOPMENT","complete":true,
            "software":SOFTWARE,"configuration":config_binding,"executable":record(&executable)?,
            "package_version":env!("CARGO_PKG_VERSION"),"worker_count":rayon::current_num_threads(),
            "input_cfa":cfg.cfa,"cfa":record(&cfa_path)?,"camera_rgb":record(&camera_path)?,
            "rgb16":record(&master)?,"linear_rgb32":record(&linear_path)?,
            "native_dimensions":[w,h],"active_origin_xy":cfg.active_origin_xy,"physical_pattern":"RGGB"});
        let detail = json!({"development_receipt":cfg.development_receipt,"development":development,
            "pixel_hashes":{"rgb16":rgb_sha,"linear_rgb32":linear_sha},"material_metadata":rgb_material,
            "linear_material_metadata":linear_material,"parity":parity,"pixel_readback_exact":true,
            "signed_cfa_copy_bit_exact":true,"negative_cfa_samples_retained_in_master":negatives,
            "negative_final_camera_samples_retained":camera_negative,"camera_rgb_semantics":"actual final MHC of max0 black-subtracted CFA times WB/range; HWC normalized camera RGB before matrix/highlight/tone; signed MHC values retained",
            "linear_semantics":"actual matrix/highlight output before tone; BT.709/D65, not inverse-developed camera RGB"});
        receipt
            .as_object_mut()
            .unwrap()
            .extend(detail.as_object().unwrap().clone());
        let scope = json!({"demosaic_stages":1,"demosaic_row_calls":h,"demosaic_implementation":"strehl_core::demosaic::demosaic_malvar_row",
            "source_demosaic_calls":0,"remosaic_calls":0,"RAW_reads":0,"tone_measured_from_output":false,
            "retained_input_bytes_and_metadata_unchanged":true,"entire_output":true,"quality_claim":false,
            "photographic_admission":false,"seconds":started.elapsed().as_secs_f64(),
            "limits":"delivery-only; root owns source-population, upstream CFA validity, process bounds and photographic assessment"});
        receipt
            .as_object_mut()
            .unwrap()
            .extend(scope.as_object().unwrap().clone());
        save(&cfg.out_dir.join("receipt.json"), &receipt)?;
        println!(
            "complete native CFA development: {w}x{h}, one final MHC stage, signed CFA and actual camera field saved"
        );
        Ok(())
    })();
    if let Err(error) = &result {
        save(
            &cfg.out_dir.join("failure.json"),
            &json!({"status":"NATIVE_CFA_DEVELOPMENT_FAILED","error":format!("{error:#}"),"partial_outputs_preserved":true,"quality_claim":false,"photographic_admission":false}),
        )?;
    }
    result
}
fn main() -> Result<()> {
    let mut args = std::env::args_os().skip(1);
    let config_path = PathBuf::from(args.next().context("configuration JSON required")?);
    ensure!(
        args.next().is_none(),
        "exactly one configuration argument required"
    );
    run(&config_path)
}
