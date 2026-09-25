// Test-only full-output replay from one frozen collapsed merge, no RAW reads.
use super::*;
use crate::image_out::highlight_rendering::{self as render, Arm};
use serde::Deserialize;
use serde_json::json;
use sha2::{Digest, Sha256};
use std::{fs::File, io::{Read, Write}};

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct Config {
    schema: u32, cache: PathBuf, expected_current_tiff: PathBuf,
    expected_current_file_sha256: String, out_dir: PathBuf,
}
fn sha_bytes(bytes: &[u8]) -> String { Sha256::digest(bytes).iter().map(|b| format!("{b:02x}")).collect() }
fn sha_file(path: &Path) -> Result<String> {
    let mut reader = std::io::BufReader::new(File::open(path)?);
    let mut digest = Sha256::new(); let mut block = [0u8; 65536];
    loop { let n = reader.read(&mut block)?; if n == 0 { break; } digest.update(&block[..n]); }
    Ok(digest.finalize().iter().map(|b| format!("{b:02x}")).collect())
}
fn plane_hash(v: &[f32]) -> String {
    let mut digest = Sha256::new(); let mut block = [0u8; 65536];
    for chunk in v.chunks(block.len() / 4) {
        for (dst, src) in block.chunks_exact_mut(4).zip(chunk) { dst.copy_from_slice(&src.to_bits().to_le_bytes()); }
        digest.update(&block[..chunk.len()*4]);
    } digest.finalize().iter().map(|b| format!("{b:02x}")).collect()
}
fn image(path: &Path) -> Result<(u32, u32, Vec<u16>, Vec<u8>)> {
    let mut decoder = tiff::decoder::Decoder::new(std::io::BufReader::new(File::open(path)?))?;
    let (w, h) = decoder.dimensions()?;
    ensure!(decoder.colortype()? == tiff::ColorType::RGB(16), "non-RGB16 image");
    let icc = decoder.get_tag_u8_vec(tiff::tags::Tag::IccProfile)?;
    ensure!(!icc.is_empty(), "ICC absent");
    let pixels = match decoder.read_image()? { tiff::decoder::DecodingResult::U16(v) => v,
        _ => bail!("non-u16 pixels") };
    ensure!(pixels.len() == w as usize * h as usize * 3 && !decoder.more_images(), "invalid image shape/pages");
    Ok((w, h, pixels, icc))
}
fn pixels_hash(v: &[u16]) -> String {
    let mut digest = Sha256::new(); let mut block = [0u8; 65536];
    for chunk in v.chunks(block.len()/2) {
        for (dst, src) in block.chunks_exact_mut(2).zip(chunk) { dst.copy_from_slice(&src.to_le_bytes()); }
        digest.update(&block[..chunk.len()*2]);
    } digest.finalize().iter().map(|b| format!("{b:02x}")).collect()
}
fn save(path: &Path, value: &serde_json::Value) -> Result<()> {
    let mut file = std::fs::OpenOptions::new().write(true).create_new(true).open(path)?;
    serde_json::to_writer_pretty(&mut file, value)?; writeln!(file)?; Ok(())
}

#[test]
#[ignore = "root-owned complete cached render factorial; no RAW reads"]
fn complete_cached_factorial() -> Result<()> {
    let started = Instant::now();
    let config_path = PathBuf::from(std::env::var_os("STREHL_HIGHLIGHT_RENDERING_CONFIG").context("config required")?);
    let cfg: Config = serde_json::from_slice(&std::fs::read(&config_path)?)?;
    ensure!(cfg.schema == 1 && cfg.cache.is_absolute() && cfg.expected_current_tiff.is_absolute(), "invalid replay config");
    ensure!(sha_file(&cfg.expected_current_tiff)? == cfg.expected_current_file_sha256, "retained user image binding changed");
    ensure!(std::env::var_os(strehl_core::highlight::KNEE_ENV).is_none(), "current default sensor knee required");
    ensure!(!std::env::var(strehl_core::demosaic::DEMOSAIC_ENV).is_ok_and(|v| v.eq_ignore_ascii_case("directional")), "current MHC required");
    ensure!(matched_source_tests::pinned_tone().is_none(), "unrelated tone override active");
    let cache_metadata_bytes = std::fs::read(&cfg.cache)?;
    let (metadata, planes) = full_stack_source_prior::read_cache(&cfg.cache)?;
    ensure!(metadata.phase == "full", "cost/subset cache cannot enter photographic factorial");
    let domain = metadata.domain()?; let levels = metadata.levels(); let wb = metadata.wb();
    let xyz = metadata.xyz(); let exposure = metadata.exposure()?;
    ensure!(wb.is_some() && xyz.is_some(), "full photographic metadata required");
    let before: Vec<_> = planes.iter().map(|p| plane_hash(p)).collect();
    let root = PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../..").canonicalize()?;
    ensure!(!cfg.out_dir.exists() && cfg.out_dir.parent().context("output parent required")?.canonicalize()?
        .starts_with(root.join("experiments").canonicalize()?), "fresh workspace output required");
    std::fs::create_dir(&cfg.out_dir)?;
    let write = |path: &Path| write_merged(Merged::Bands { domain, planes: &planes }, levels, wb,
        xyz.as_ref(), image_out::OutputSpace::Srgb, true, exposure, None, path);

    // Literal hook-off baseline and Current observer arm prove the observer
    // is inert on the actual complete writer, not merely on a pixel helper.
    let off = cfg.out_dir.join("observer-off.tiff"); write(&off)?;
    let current = cfg.out_dir.join("current.tiff");
    let (_, reference_development) = render::with_arm(Arm::Current, || write(&current))?;
    ensure!(sha_file(&off)? == sha_file(&current)?, "observer changed complete output bytes");
    let (w, h, baseline, icc) = image(&current)?;
    ensure!((w as usize, h as usize) == (2*domain.analysis().width, 2*domain.analysis().height), "cache output dimensions changed");
    let (rw, rh, retained, retained_icc) = image(&cfg.expected_current_tiff)?;
    ensure!((w,h) == (rw,rh) && baseline == retained && icc == retained_icc,
        "cached actual writer differs from complete retained user image; do not run candidate arms");
    drop(retained);
    let pixel_sha = pixels_hash(&baseline); drop(baseline);
    save(&cfg.out_dir.join("baseline-verified.json"), &json!({
        "cache_metadata_sha256": sha_bytes(&cache_metadata_bytes), "width":w,"height":h,
        "retained_image_sha256":cfg.expected_current_file_sha256,"rgb16_le_sha256":pixel_sha,
        "icc_sha256":sha_bytes(&icc),"observer_on_off_file_exact":true,
        "resolved_development":reference_development,"planes_sha256":before}))?;
    let mut arms = vec![json!({"arm":Arm::Current,"file":"current.tiff","file_sha256":sha_file(&current)?,
        "rgb16_le_sha256":pixel_sha,"resolved_development":reference_development})];
    for arm in [Arm::SensorRolloffOff, Arm::Shoulder, Arm::Both] {
        let start = Instant::now(); let path = cfg.out_dir.join(format!("{}.tiff", arm.name()));
        let (_, development) = render::with_arm(arm, || write(&path))?;
        ensure!(development == reference_development, "factorial changed actual tone/exposure/matrix metadata");
        let (cw, ch, rgb, ci) = image(&path)?;
        ensure!((cw,ch)==(w,h) && ci==icc, "candidate dimensions/ICC changed");
        arms.push(json!({"arm":arm,"file":format!("{}.tiff",arm.name()),"file_sha256":sha_file(&path)?,
            "rgb16_le_sha256":pixels_hash(&rgb),"resolved_development":development,"seconds":start.elapsed().as_secs_f64()}));
    }
    ensure!(planes.iter().map(|p|plane_hash(p)).collect::<Vec<_>>()==before, "renderer changed merged planes");
    ensure!(std::fs::read(&cfg.cache)?==cache_metadata_bytes, "cache metadata changed");
    ensure!(sha_file(&cfg.expected_current_tiff)?==cfg.expected_current_file_sha256, "retained user output changed");
    save(&cfg.out_dir.join("receipt.json"), &json!({"schema":1,"status":"COMPLETE_CACHED_FACTORIAL",
        "cache":cfg.cache,"cache_metadata_sha256":sha_bytes(&cache_metadata_bytes),"planes_sha256":before,
        "width":w,"height":h,"icc_sha256":sha_bytes(&icc),"arms":arms,
        "observer_on_off_file_exact":true,"retained_current_pixels_and_icc_exact":true,
        "merged_planes_unchanged":true,"raw_reads":0,"total_seconds":started.elapsed().as_secs_f64(),
        "visual_verdict":null,"scope":"display-only factorial; no spatial ghosting repair claim"}))?;
    eprintln!("HIGHLIGHT_RENDERING_COMPLETE {}", cfg.out_dir.display()); Ok(())
}
