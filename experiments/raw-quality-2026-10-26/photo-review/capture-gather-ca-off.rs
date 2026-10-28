//! Manual ignored CA-off capture of the same frozen actual full-resolution gather.
//! No fit, source write, renderer, candidate, or photographic quality assertion.

use std::fs::{self, File, OpenOptions};
use std::io::{BufReader, BufWriter, Read, Write};
use std::path::{Path, PathBuf};
use std::time::Instant;

use anyhow::{Context, Result, ensure};
use serde_json::{Value, json};
use sha2::{Digest, Sha256};
use strehl_core::align::Resampler;
use strehl_core::warpmap::{StackIdentity, WarpMap};

const SOURCE_SHA: &str = "e85572179c8a98f5a2de2be5c81cd0b1bdeae67999aa00e585c6dde35f531154";
const MAP_SHA: &str = "4a76cd0c56c3a525e70f5bf72b965adb706131618c5bf49d0ae853fbf341c225";
const ORDER_SHA: &str = "0235564cf5131e7eb5e4ea251c16ea9272f6a55a9d8cc6efc717970615a30d6f";
const CROP: [usize; 4] = [68, 46, 6896, 4596];

fn sha(path: &Path) -> Result<String> {
    let mut input = BufReader::new(File::open(path)?);
    let mut digest = Sha256::new();
    let mut buffer = [0u8; 65_536];
    loop {
        let count = input.read(&mut buffer)?;
        if count == 0 {
            break;
        }
        digest.update(&buffer[..count]);
    }
    Ok(digest
        .finalize()
        .iter()
        .map(|b| format!("{b:02x}"))
        .collect())
}

fn dump_crop(frame: &strehl_raw::Frame, path: &Path) -> Result<Value> {
    let [x, y, width, height] = CROP;
    ensure!(x + width <= frame.active.width && y + height <= frame.active.height);
    let mut output = BufWriter::new(OpenOptions::new().write(true).create_new(true).open(path)?);
    let mut row = vec![0u8; width * 2];
    for py in y..y + height {
        for px in 0..width {
            row[2 * px..2 * px + 2].copy_from_slice(&frame.sample(x + px, py).to_le_bytes());
        }
        output.write_all(&row)?;
    }
    output.flush()?;
    drop(output);
    ensure!(fs::metadata(path)?.len() == (2 * width * height) as u64);
    Ok(json!({
        "path": path, "sha256": sha(path)?, "bytes": 2 * width * height,
        "format": "headerless u16 little-endian CFA, row-major, no padding",
        "width": width, "height": height, "row_stride_samples": width,
        "reference_native_crop_xywh": CROP, "cfa_at_crop_origin": "RGGB"
    }))
}

// Stream two saved CFA crops; no second decoded frame or RGB volume is retained.
fn compare_crops(original: &Path, gathered: &Path) -> Result<Value> {
    let [_, _, width, height] = CROP;
    let mut a = BufReader::new(File::open(original)?);
    let mut b = BufReader::new(File::open(gathered)?);
    let mut aa = vec![0u8; width * 2];
    let mut bb = vec![0u8; width * 2];
    let mut count = [0u64; 4];
    let mut changed = [0u64; 4];
    let mut absolute = [0u64; 4];
    let mut signed = [0i64; 4];
    let mut squared = [0f64; 4];
    let mut maximum = [0u32; 4];
    for y in 0..height {
        a.read_exact(&mut aa)?;
        b.read_exact(&mut bb)?;
        for x in 0..width {
            let phase = 2 * (y % 2) + x % 2;
            let before = u16::from_le_bytes([aa[2 * x], aa[2 * x + 1]]) as i32;
            let after = u16::from_le_bytes([bb[2 * x], bb[2 * x + 1]]) as i32;
            let delta = after - before;
            count[phase] += 1;
            changed[phase] += u64::from(delta != 0);
            absolute[phase] += delta.unsigned_abs() as u64;
            signed[phase] += delta as i64;
            squared[phase] += f64::from(delta) * f64::from(delta);
            maximum[phase] = maximum[phase].max(delta.unsigned_abs());
        }
    }
    let mut result = serde_json::Map::new();
    for (phase, name) in ["R", "G1", "G2", "B"].into_iter().enumerate() {
        result.insert(
            name.into(),
            json!({"total":count[phase], "changed":changed[phase],
            "mean_abs_DN":absolute[phase] as f64/count[phase] as f64,
            "mean_signed_gather_minus_original_DN":signed[phase] as f64/count[phase] as f64,
            "rms_DN":(squared[phase]/count[phase] as f64).sqrt(), "max_abs_DN":maximum[phase]}),
        );
    }
    Ok(Value::Object(result))
}

#[test]
#[ignore = "manual source149 CA-off production-gather capture; requires STREHL_WEEVIL_CAPTURE_OUT"]
fn capture_weevil_anchor149_actual_ca_off_gather() -> Result<()> {
    let started = Instant::now();
    ensure!(
        !cfg!(feature = "direct-cfa-gather"),
        "use a baseline build without direct-cfa-gather"
    );
    ensure!(
        !cfg!(feature = "native-gpu-gather"),
        "use the baseline CPU gather build"
    );
    for key in [
        "STREHL_DIRECT_CFA",
        "STREHL_GPU_GATHER",
        "STREHL_DIRECT_PLANES",
    ] {
        ensure!(
            matches!(
                std::env::var(key).as_deref(),
                Err(std::env::VarError::NotPresent) | Ok("off")
            ),
            "{key} must be absent/off"
        );
    }
    ensure!(
        std::env::var_os("STREHL_LOCAL_PLACEMENT_FILE").is_none(),
        "no local placement intervention in baseline capture"
    );
    ensure!(
        std::env::var("STREHL_FIX_CA").as_deref() == Ok("off"),
        "CA ablation requires explicit STREHL_FIX_CA=off"
    );
    ensure!(
        matches!(
            std::env::var("STREHL_DEMOSAIC").as_deref(),
            Err(std::env::VarError::NotPresent) | Ok("malvar")
        ),
        "baseline MHC required"
    );
    let repo = Path::new(env!("CARGO_MANIFEST_DIR"))
        .join("../..")
        .canonicalize()?;
    let out = PathBuf::from(
        std::env::var_os("STREHL_WEEVIL_CAPTURE_OUT")
            .context("STREHL_WEEVIL_CAPTURE_OUT must name a fresh absolute output directory")?,
    );
    ensure!(
        out.is_absolute() && !out.exists(),
        "output directory must be absolute and fresh"
    );
    let parent = out.parent().context("output parent")?.canonicalize()?;
    ensure!(
        parent.starts_with(repo.join("outputs").canonicalize()?),
        "capture outputs belong below this worktree's outputs directory"
    );
    let base = repo.join("outputs/raw-quality-2026-10-26/weevil-107-baseline");
    let order_path = base.join("input-order.json");
    let map_path = base.join("alignment.txt");
    ensure!(
        sha(&order_path)? == ORDER_SHA,
        "frozen source order changed"
    );
    ensure!(sha(&map_path)? == MAP_SHA, "frozen map changed");
    let order: Vec<Value> = serde_json::from_slice(&fs::read(&order_path)?)?;
    ensure!(order.len() == 299 && order[149]["index"] == 149);
    let source = PathBuf::from(order[149]["path"].as_str().context("source149 path")?);
    ensure!(order[149]["sha256"].as_str() == Some(SOURCE_SHA));
    ensure!(sha(&source)? == SOURCE_SHA, "original RAW hash changed");
    let source_metadata = fs::metadata(&source)?;
    ensure!(source_metadata.len() == 35_184_640);
    let mut entries = Vec::with_capacity(299);
    for (index, item) in order.iter().enumerate() {
        ensure!(item["index"].as_u64() == Some(index as u64));
        let p = Path::new(item["path"].as_str().context("source path")?);
        let name = p
            .file_name()
            .and_then(|v| v.to_str())
            .context("source filename")?;
        entries.push((
            name.to_owned(),
            item["bytes"].as_u64().context("source size")?,
        ));
    }
    let map = WarpMap::load(&map_path)?;
    map.provenance()
        .stack
        .check(&StackIdentity::from_entries("107MSDCF", &entries))?;
    ensure!(map.warps().len() == 299 && map.provenance().reference == 149);
    ensure!(map.resampler() == Resampler::CatmullRom);
    let transform = map.warps()[149].placed().context("anchor149 is unplaced")?;
    // The globally solved anchor is numerically identity, but retains tiny
    // gauge roundoff. Bind its stored bits and preserve the actual pull.
    ensure!(
        [
            transform.a.re.to_bits(),
            transform.a.im.to_bits(),
            transform.b.re.to_bits(),
            transform.b.im.to_bits(),
        ] == [
            0x3ff0_0000_0000_0000,
            0xbc00_0000_0000_0000,
            0x3ca0_0000_0000_0000,
            0x0000_0000_0000_0000,
        ],
        "frozen reference149 transform bits changed"
    );
    let geom = map.geometry();
    ensure!(geom.width == 3516 && geom.height == 2344);

    let mut frame = strehl_raw::decode(&source)?;
    ensure!(frame.active.width == 2 * geom.width && frame.active.height == 2 * geom.height);
    let identity = strehl_raw::identity(&source);
    let ca = strehl_core::optics::profile_for_capture_env(
        identity.model.as_deref(),
        identity.lens_type3,
    )?;
    ensure!(ca.is_none(), "CA-off capture resolved an optical profile");
    let source_info = json!({
        "path": source, "sha256": SOURCE_SHA, "bytes": source_metadata.len(),
        "index_zero_based": 149, "camera": frame.camera,
        "active_xywh": [frame.active.x, frame.active.y, frame.active.width, frame.active.height],
        "buffer_stride_samples": frame.stride, "buffer_height": frame.buffer_height,
        "black": frame.levels.black, "white": frame.levels.white, "iso": frame.iso,
        "wb_coeffs": frame.wb_coeffs.map(|v| v.is_finite().then_some(v)),
        "resolved_wb_gains": super::wb_gains(&frame.wb_coeffs),
        "xyz_to_cam_rgbe": frame.xyz_to_cam_rgbe,
        "color_matrices": frame.color_matrices,
        "resolved_xyz_to_cam": frame.xyz_to_cam_rgb_with_source(),
        "identity_body": identity.model, "identity_lens_type3": identity.lens_type3,
        "resolved_ca_profile": ca.map(|p| json!({"key": p.key, "eps_r": p.eps_r, "eps_b": p.eps_b, "translation": p.translation}))
    });
    fs::create_dir(&out)?;
    let original = dump_crop(&frame, &out.join("original-crop.u16le"))?;
    let mut scratch = super::WarpScratch::new(geom);
    let gather_start = Instant::now();
    let coverage = super::warp_frame_in_place_fullres(
        &mut frame,
        transform,
        geom,
        map.resampler(),
        &mut scratch,
    )?;
    let gather_seconds = gather_start.elapsed().as_secs_f64();
    ensure!(coverage.is_finite() && coverage > 0.9);
    let gathered = dump_crop(&frame, &out.join("gathered-crop.u16le"))?;
    let phase_comparison = compare_crops(
        &out.join("original-crop.u16le"),
        &out.join("gathered-crop.u16le"),
    )?;
    // The unchanged green pull is the same tiny-gauge anchor pull as baseline.
    // Record R/B rather than asserting identity from nominal near-zero geometry.
    ensure!(
        phase_comparison["G1"]["changed"].as_u64() == Some(0)
            && phase_comparison["G2"]["changed"].as_u64() == Some(0),
        "original measured green samples changed under frozen anchor pull"
    );
    ensure!(
        sha(&source)? == SOURCE_SHA && sha(&map_path)? == MAP_SHA && sha(&order_path)? == ORDER_SHA,
        "bound input changed during capture"
    );
    ensure!(
        fs::metadata(&source)?.modified()? == source_metadata.modified()?,
        "original modification time changed"
    );
    let environment: std::collections::BTreeMap<String, String> = std::env::vars()
        .filter(|(key, _)| key.starts_with("STREHL_") || key == "RAYON_NUM_THREADS")
        .collect();
    let exe = std::env::current_exe()?;
    let receipt = json!({
        "schema": 1, "status": "ACTUAL_CA_OFF_GATHER_CAPTURED_NO_QUALITY_CLAIM",
        "source": source_info, "frame_count": 299,
        "map": {"path": map_path, "sha256": MAP_SHA, "reference": 149, "resampler": "catmull-rom", "quad_dimensions": [geom.width, geom.height]},
        "transform": {"a": [transform.a.re, transform.a.im], "b": [transform.b.re, transform.b.im], "bits": [transform.a.re.to_bits(), transform.a.im.to_bits(), transform.b.re.to_bits(), transform.b.im.to_bits()]},
        "input_order_sha256": ORDER_SHA, "original": original, "gathered": gathered,
        "phase_comparison_original_vs_gathered_full_crop": phase_comparison,
        "ca_disabled_explicitly": true, "resolved_ca_profile_none": true,
        "all_original_greens_unchanged": true,
        "red_blue_identity_asserted": false,
        "whole_active_coverage": coverage, "rayon_workers": rayon::current_num_threads(),
        "environment": environment, "test_executable": {"path": exe, "sha256": sha(&exe)?},
        "harness_sha256": sha(&repo.join("experiments/raw-quality-2026-10-26/photo-review/capture-gather-ca-off.rs"))?,
        "gather_seconds_operational_only": gather_seconds, "elapsed_seconds": started.elapsed().as_secs_f64(),
        "original_map_order_unchanged": true,
        "scope": "one actual decoded source through production fullres CPU gather with lateral CA explicitly disabled; same frozen map and pull as baseline; no alignment fit, stack or renderer; matched complete delivered crop"
    });
    let mut receipt_file = OpenOptions::new()
        .write(true)
        .create_new(true)
        .open(out.join("capture.json"))?;
    serde_json::to_writer_pretty(&mut receipt_file, &receipt)?;
    receipt_file.write_all(b"\n")?;
    receipt_file.flush()?;
    eprintln!("source149 CA-off gather captured to {}", out.display());
    Ok(())
}
