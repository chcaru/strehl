// Test-only observer inside image_out. No renderer treatment or RAW access.
// Integration and execution belong to root after the running source freeze.
use super::*;
use anyhow::{bail, ensure};
use serde::Deserialize;
use serde_json::json;
use sha2::{Digest, Sha256};
use std::{io::{Read, Write}, path::PathBuf, sync::Mutex};

const ROI: [usize; 4] = [4668, 1858, 384, 384]; // complete output-native gauge
const NATIVE: [usize; 2] = [6524, 4348];

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct Config {
    schema: u32,
    cache: PathBuf,
    cache_sha256: String,
    expected_current_tiff: PathBuf,
    expected_current_file_sha256: String,
    out_dir: PathBuf,
}

struct Trace {
    mosaic: Vec<f32>,
    linear: Vec<f32>,
    pin_channels: Vec<u8>,
    pinned: Vec<u16>,
    clip_changed: Vec<u16>,
    clipped: Vec<f32>,
    developed: Vec<f32>,
    toned: Vec<f32>,
    gamut: Vec<f32>,
    final_rgb: Vec<u16>,
}
static RUN: Mutex<()> = Mutex::new(());
static STATE: Mutex<Option<Option<Trace>>> = Mutex::new(None);
struct Reset;
impl Drop for Reset {
    fn drop(&mut self) {
        if let Ok(mut slot) = STATE.lock() { *slot = None; }
    }
}

fn capture<T>(write: impl FnOnce() -> Result<T>) -> Result<(T, Trace)> {
    let _run = RUN.try_lock().map_err(|_| anyhow::anyhow!("stage probe already active/poisoned"))?;
    {
        let mut slot = STATE.lock().map_err(|_| anyhow::anyhow!("stage probe state poisoned"))?;
        ensure!(slot.is_none(), "nested stage probe");
        *slot = Some(None);
    }
    let _reset = Reset;
    let result = write()?;
    let trace = STATE.lock().map_err(|_| anyhow::anyhow!("stage probe state poisoned"))?
        .take().flatten().context("actual writer did not reach the stage observer")?;
    Ok((result, trace))
}

/// Call once in actual write_demosaiced, immediately after resolve_tone.
/// This receives the actual full normalized mosaic; it does not recreate WB,
/// exposure, black subtraction, crop or normalization from logged constants.
pub(crate) fn observe_mosaic(m: &Mosaic<'_>, dev: &Develop) -> Result<()> {
    let mut slot = STATE.lock().map_err(|_| anyhow::anyhow!("stage probe state poisoned"))?;
    let Some(trace_slot) = slot.as_mut() else { return Ok(()); };
    ensure!(trace_slot.is_none(), "stage observer called more than once");
    ensure!([m.width, m.height] == NATIVE && dev.srgb && dev.wants_tone,
        "stage probe requires the frozen full garnet photographic writer");
    let render = dev.matrix.as_ref().context("missing camera matrix")?;
    let tone = dev.tone.as_ref().context("tone not resolved")?;
    ensure!(std::env::var_os(strehl_core::demosaic::DEMOSAIC_ENV).is_none(), "current MHC required");
    ensure!(std::env::var_os(strehl_core::highlight::KNEE_ENV).is_none(), "default sensor rolloff required");
    let [x0, y0, width, height] = ROI;
    let n = width * height;
    let mut trace = Trace {
        mosaic: Vec::with_capacity(n), linear: Vec::with_capacity(3*n),
        pin_channels: Vec::with_capacity(n), pinned: Vec::with_capacity(n),
        clip_changed: Vec::with_capacity(n), clipped: Vec::with_capacity(3*n),
        developed: Vec::with_capacity(3*n), toned: Vec::with_capacity(3*n),
        gamut: Vec::with_capacity(3*n), final_rgb: Vec::with_capacity(3*n),
    };
    let mut row = vec![0.0f32; 3*m.width];
    let ceiling = render.ceiling();
    for y in y0..y0+height {
        // Full source row/full mosaic context: never demosaic an isolated crop.
        demosaic_row(m, y, &mut row);
        trace.mosaic.extend_from_slice(&m.data[y*m.width+x0..y*m.width+x0+width]);
        for x in x0..x0+width {
            let lin = [row[3*x], row[3*x+1], row[3*x+2]];
            let mask = u8::from(lin[0] >= ceiling[0])
                | (u8::from(lin[1] >= ceiling[1]) << 1)
                | (u8::from(lin[2] >= ceiling[2]) << 2);
            let clipped = render.clip_highlights(lin);
            let developed = render.develop(lin);
            let gain = tone.gain(luma709(developed)) * dev.exposure_gain;
            let toned = [developed[0]*gain, developed[1]*gain, developed[2]*gain];
            let gamut = gamut_map(toned);
            // Actual current pixel function, guarded against a live factorial
            // override. This is checked against the written ROI, not itself.
            let final_rgb = highlight_rendering::pixel(lin, dev, highlight_rendering::Arm::Current);
            ensure!(lin.into_iter().chain(clipped).chain(developed).chain(toned).chain(gamut)
                .all(f32::is_finite), "nonfinite observed RGB stage");
            trace.linear.extend_from_slice(&lin);
            trace.pin_channels.push(mask);
            trace.pinned.push(if mask != 0 { 65535 } else { 0 });
            trace.clip_changed.push(if lin.map(f32::to_bits) != clipped.map(f32::to_bits) { 65535 } else { 0 });
            trace.clipped.extend_from_slice(&clipped);
            trace.developed.extend_from_slice(&developed);
            trace.toned.extend_from_slice(&toned);
            trace.gamut.extend_from_slice(&gamut);
            trace.final_rgb.extend_from_slice(&final_rgb);
        }
    }
    *trace_slot = Some(trace);
    Ok(())
}

fn hex(bytes: impl AsRef<[u8]>) -> String {
    bytes.as_ref().iter().map(|v| format!("{v:02x}")).collect()
}
fn file_hash(path: &Path) -> Result<String> {
    let mut input = std::io::BufReader::new(File::open(path)?);
    let mut hash = Sha256::new(); let mut buf = [0u8; 65536];
    loop { let n = input.read(&mut buf)?; if n == 0 { break; } hash.update(&buf[..n]); }
    Ok(hex(hash.finalize()))
}
fn f32_hash(values: &[f32]) -> String {
    let mut hash = Sha256::new();
    for chunk in values.chunks(16384) {
        let bytes: Vec<u8> = chunk.iter().flat_map(|v| v.to_bits().to_le_bytes()).collect();
        hash.update(bytes);
    }
    hex(hash.finalize())
}
fn create(path: &Path) -> Result<File> {
    Ok(std::fs::OpenOptions::new().write(true).create_new(true).open(path)?)
}
fn save_json(path: &Path, value: &serde_json::Value) -> Result<()> {
    let mut file = create(path)?; serde_json::to_writer_pretty(&mut file, value)?;
    writeln!(file)?; Ok(())
}
fn save_f32(path: &Path, values: &[f32]) -> Result<()> {
    let mut file = std::io::BufWriter::new(create(path)?);
    for chunk in values.chunks(16384) {
        let bytes: Vec<u8> = chunk.iter().flat_map(|v| v.to_bits().to_le_bytes()).collect();
        file.write_all(&bytes)?;
    }
    file.flush()?; Ok(())
}
fn read_rgb(path: &Path) -> Result<([usize; 2], Vec<u16>, Vec<u8>)> {
    let mut decoder = tiff::decoder::Decoder::new(std::io::BufReader::new(File::open(path)?))?;
    let (w,h) = decoder.dimensions()?;
    ensure!(decoder.colortype()? == tiff::ColorType::RGB(16), "expected RGB16 master");
    let icc = decoder.get_tag_u8_vec(tiff::tags::Tag::IccProfile)?;
    ensure!(!icc.is_empty(), "ICC absent");
    let pixels = match decoder.read_image()? {
        tiff::decoder::DecodingResult::U16(v) => v,
        _ => bail!("expected u16 samples"),
    };
    ensure!(pixels.len() == w as usize*h as usize*3 && !decoder.more_images(), "invalid image shape/pages");
    Ok(([w as usize,h as usize],pixels,icc))
}
fn roi_rgb(pixels: &[u16]) -> Vec<u16> {
    let [x,y,w,h] = ROI;
    let mut result = Vec::with_capacity(w*h*3);
    for row in y..y+h {
        result.extend_from_slice(&pixels[3*(row*NATIVE[0]+x)..3*(row*NATIVE[0]+x+w)]);
    }
    result
}

#[test]
#[ignore = "root-owned stage trace of frozen full garnet cache; no RAW reads"]
fn garnet_cached_stage_trace() -> Result<()> {
    use crate::merge_cmd::full_stack_source_prior as cache;
    let config_path = PathBuf::from(std::env::var_os("STREHL_HIGHLIGHT_STAGE_CONFIG").context("config required")?);
    let config_bytes = std::fs::read(&config_path)?;
    let cfg: Config = serde_json::from_slice(&config_bytes)?;
    ensure!(cfg.schema == 1 && cfg.cache.is_absolute() && cfg.expected_current_tiff.is_absolute()
        && cfg.out_dir.is_absolute(), "invalid stage probe configuration");
    ensure!(file_hash(&cfg.cache)? == cfg.cache_sha256, "cache metadata binding changed");
    ensure!(file_hash(&cfg.expected_current_tiff)? == cfg.expected_current_file_sha256, "retained image binding changed");
    ensure!(std::env::var_os(strehl_core::highlight::KNEE_ENV).is_none()
        && std::env::var_os(strehl_core::demosaic::DEMOSAIC_ENV).is_none(), "default MHC/highlight settings required");
    ensure!(crate::merge_cmd::matched_source_tests::pinned_tone().is_none(), "unrelated pinned tone active");
    let (metadata, planes) = cache::read_cache(&cfg.cache)?;
    ensure!(metadata.phase == "full" && metadata.arm == "baseline" && metadata.frames == 183
        && metadata.reference == 91 && metadata.crop == [127,85,3262,2174], "expected frozen full garnet current cache");
    let binary_path = cfg.cache.parent().context("cache parent")?.join(&metadata.binary);
    let before: Vec<_> = planes.iter().map(|p| f32_hash(p)).collect();
    ensure!(before == metadata.plane_sha256, "in-memory cache binding mismatch");
    let root = PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../..").canonicalize()?;
    ensure!(!cfg.out_dir.exists() && cfg.out_dir.parent().context("output parent required")?.canonicalize()?
        .starts_with(root.join("experiments").canonicalize()?), "fresh workspace output required");
    std::fs::create_dir(&cfg.out_dir)?;

    // Actual write_merged helper owns every preprocessing expression.
    let off = cfg.out_dir.join("observer-off.tiff");
    let (_, off_development) = highlight_rendering::with_arm(highlight_rendering::Arm::Current,
        || cache::write_current(&off, &planes, &metadata))?;
    let (dims, baseline, icc) = read_rgb(&off)?;
    let (old_dims, retained, old_icc) = read_rgb(&cfg.expected_current_tiff)?;
    ensure!(dims == NATIVE && dims == old_dims && baseline == retained && icc == old_icc,
        "actual cache writer differs from retained full current image");
    drop(retained);
    let expected_roi = roi_rgb(&baseline); drop(baseline);

    let on = cfg.out_dir.join("observer-on.tiff");
    let ((_, on_development), trace) = capture(|| highlight_rendering::with_arm(highlight_rendering::Arm::Current,
        || cache::write_current(&on, &planes, &metadata)))?;
    ensure!(off_development == on_development, "observer changed resolved development");
    let output_hash = file_hash(&off)?;
    ensure!(output_hash == file_hash(&on)?, "stage observer changed complete TIFF bytes");
    ensure!(trace.final_rgb == expected_roi, "stage trace final RGB differs from actual baseline ROI");

    let mut artifacts = Vec::new();
    for (name, data, channels, space) in [
        ("normalized-mosaic.f32",trace.mosaic.as_slice(),1,"camera RGGB, exact writer-normalized mosaic"),
        ("linear-camera-rgb.f32",trace.linear.as_slice(),3,"camera RGB, actual full-context MHC"),
        ("post-clip-camera-rgb.f32",trace.clipped.as_slice(),3,"camera RGB, actual Render::clip_highlights"),
        ("post-develop-linear-srgb.f32",trace.developed.as_slice(),3,"linear sRGB, actual Render::develop"),
        ("post-tone-linear-srgb.f32",trace.toned.as_slice(),3,"linear sRGB, actual Tone::gain and exposure gain"),
        ("post-gamut-linear-srgb.f32",trace.gamut.as_slice(),3,"linear sRGB, actual gamut_map"),
    ] {
        let path = cfg.out_dir.join(name); save_f32(&path,data)?;
        artifacts.push(json!({"file":name,"sha256":file_hash(&path)?,"shape":[ROI[3],ROI[2],channels],
            "dtype":"f32-le","layout":"row-major interleaved","space":space}));
    }
    let pin_path = cfg.out_dir.join("pin-channels.u8"); create(&pin_path)?.write_all(&trace.pin_channels)?;
    artifacts.push(json!({"file":"pin-channels.u8","sha256":file_hash(&pin_path)?,"shape":[ROI[3],ROI[2]],
        "dtype":"u8","meaning":"bit0 R>=ceiling_R; bit1 G>=ceiling_G; bit2 B>=ceiling_B"}));
    for (name, data) in [("pin-mask.tiff", &trace.pinned), ("clip-changed-mask.tiff", &trace.clip_changed)] {
        let path = cfg.out_dir.join(name); write_gray16(&path,ROI[2] as u32,ROI[3] as u32,data)?;
        artifacts.push(json!({"file":name,"sha256":file_hash(&path)?,"shape":[ROI[3],ROI[2]],
            "dtype":"u16 TIFF","meaning":"0 false,65535 true; diagnostic mask, no display normalization"}));
    }
    let roi_path = cfg.out_dir.join("final-rgb16.tiff");
    // Direct RGB16 values with the retained ICC; no second development.
    let mut encoder = TiffEncoder::new(std::io::BufWriter::new(create(&roi_path)?))?;
    let mut output = encoder.new_image::<colortype::RGB16>(ROI[2] as u32, ROI[3] as u32)?;
    output.encoder().write_tag(tiff::tags::Tag::IccProfile, icc.as_slice())?;
    output.write_data(&trace.final_rgb)?; drop(encoder);
    let (roi_dims, saved_roi, saved_icc) = read_rgb(&roi_path)?;
    ensure!(roi_dims == [ROI[2],ROI[3]] && saved_roi == expected_roi && saved_icc == icc,
        "saved stage ROI pixels/ICC changed");
    artifacts.push(json!({"file":"final-rgb16.tiff","sha256":file_hash(&roi_path)?,"shape":[ROI[3],ROI[2],3],
        "dtype":"u16 RGB TIFF","icc_sha256":hex(Sha256::digest(&icc))}));

    ensure!(planes.iter().map(|p|f32_hash(p)).collect::<Vec<_>>() == before, "observer changed cache planes");
    ensure!(file_hash(&cfg.cache)? == cfg.cache_sha256 && file_hash(&binary_path)? == metadata.binary_sha256
        && file_hash(&cfg.expected_current_tiff)? == cfg.expected_current_file_sha256
        && std::fs::read(&config_path)? == config_bytes, "probe inputs changed");
    save_json(&cfg.out_dir.join("receipt.json"), &json!({"schema":1,"status":"GARNET_STAGE_TRACE_COMPLETE",
        "cache":cfg.cache,"cache_metadata_sha256":cfg.cache_sha256,"cache_binary_sha256":metadata.binary_sha256,
        "planes_sha256":before,"retained_image_sha256":cfg.expected_current_file_sha256,
        "native_dimensions":NATIVE,"roi_output_native":ROI,"roi_full_active_native":[ROI[0]+254,ROI[1]+170,ROI[2],ROI[3]],
        "resolved_development":off_development,"observer_on_off_file_sha256":output_hash,
        "observer_on_off_file_exact":true,"retained_current_pixels_and_icc_exact":true,
        "trace_final_rgb_matches_actual_roi":true,"merged_planes_unchanged":true,"raw_reads":0,
        "pin_pixels":trace.pinned.iter().filter(|&&v|v!=0).count(),
        "clip_changed_pixels":trace.clip_changed.iter().filter(|&&v|v!=0).count(),
        "artifacts":artifacts,"causal_verdict":null,
        "scope":"stage trace only; pin-mask agreement alone does not prove causation or genuine sensor clipping"}))?;
    eprintln!("GARNET_STAGE_TRACE_COMPLETE {}",cfg.out_dir.display()); Ok(())
}
