//! Manual ignored source143 CA-off production-gather capture under the frozen map.
//! No fit, source write, renderer, candidate, or photographic quality assertion.

use std::fs::{self, File, OpenOptions};
use std::io::{BufReader, BufWriter, Read, Write};
use std::path::{Path, PathBuf};
use std::time::{Instant, UNIX_EPOCH};

use anyhow::{Context, Result, ensure};
use serde_json::{Value, json};
use sha2::{Digest, Sha256};
use strehl_core::align::Resampler;
use strehl_core::warpmap::{StackIdentity, WarpMap};

const SOURCE_SHA: &str = "9101ce7866343d2fb4d4d4468f7fdeae8eab83d5ed4d61faabc8e7cb874e4abf";
const SOURCE_BYTES: u64 = 35_233_792;
const SOURCE_MTIME_NS: u128 = 1_792_989_186_660_000_000;
const SOURCE_INDEX: usize = 143;
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

fn dump_crop(frame: &strehl_raw::Frame, path: &Path, gauge: &str) -> Result<Value> {
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
        "native_crop_xywh": CROP, "coordinate_gauge": gauge,
        "cfa_at_crop_origin": "RGGB"
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
#[ignore = "manual source143 CA-off production-gather capture; requires STREHL_WEEVIL_CAPTURE_OUT"]
fn capture_weevil_source143_actual_ca_off_gather() -> Result<()> {
    let started = Instant::now();
    ensure!(
        !cfg!(feature = "direct-cfa-gather"),
        "use a baseline build without direct-cfa-gather"
    );
    ensure!(
        !cfg!(feature = "native-gpu-gather"),
        "use the baseline CPU gather build"
    );
    ensure!(
        !cfg!(feature = "native-direct-planes"),
        "use the baseline u16 writeback build"
    );
    ensure!(
        super::align_enabled(),
        "baseline registration must be enabled"
    );
    ensure!(
        super::fullres_gather_enabled(),
        "baseline fullres gather must be enabled"
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
    ensure!(
        parent.join(out.file_name().context("output directory name")?)
            == repo.join("outputs/raw-quality-2026-10-26/weevil-source143-gather-ca-off"),
        "use the allocated source143 output directory"
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
    ensure!(order.len() == 299 && order[SOURCE_INDEX]["index"] == SOURCE_INDEX);
    let source = PathBuf::from(
        order[SOURCE_INDEX]["path"]
            .as_str()
            .context("source143 path")?,
    );
    ensure!(source.file_name().and_then(|v| v.to_str()) == Some("DSC00144.ARW"));
    ensure!(order[SOURCE_INDEX]["sha256"].as_str() == Some(SOURCE_SHA));
    ensure!(order[SOURCE_INDEX]["bytes"].as_u64() == Some(SOURCE_BYTES));
    ensure!(order[SOURCE_INDEX]["mtime_ns"].as_u64().map(u128::from) == Some(SOURCE_MTIME_NS));
    ensure!(sha(&source)? == SOURCE_SHA, "original RAW hash changed");
    let source_metadata = fs::metadata(&source)?;
    ensure!(source_metadata.len() == SOURCE_BYTES);
    ensure!(
        source_metadata
            .modified()?
            .duration_since(UNIX_EPOCH)?
            .as_nanos()
            == SOURCE_MTIME_NS
    );
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
    let transform = map.warps()[SOURCE_INDEX]
        .placed()
        .context("source143 is unplaced")?;
    // This is a nonidentity source143 pull in the reference149 gauge.
    // Preserve exact stored bits; do not refit or substitute an identity pull.
    ensure!(
        [
            transform.a.re.to_bits(),
            transform.a.im.to_bits(),
            transform.b.re.to_bits(),
            transform.b.im.to_bits(),
        ] == [
            0x3ff0_028c_d977_1a5d,
            0x3efc_5b23_fccf_dd20,
            0x3faf_74d1_6be8_bc80,
            0xbfbb_4527_b01f_b520,
        ],
        "frozen source143 transform bits changed"
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
        "mtime_unix_ns": SOURCE_MTIME_NS.to_string(),
        "index_zero_based": SOURCE_INDEX, "camera": frame.camera,
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
    let original = dump_crop(
        &frame,
        &out.join("original-crop.u16le"),
        "source143 original active sensor; not registered to reference149",
    )?;
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
    let gathered = dump_crop(
        &frame,
        &out.join("gathered-crop.u16le"),
        "reference149 active sensor after the actual source143 production pull",
    )?;
    let phase_comparison = compare_crops(
        &out.join("original-crop.u16le"),
        &out.join("gathered-crop.u16le"),
    )?;
    // These arrays have different physical gauges. Their same-index difference
    // records a checksum-like observation, not placement or interpolation error.
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
        "schema": 1, "status": "SOURCE143_ACTUAL_CA_OFF_GATHER_CAPTURED_NO_QUALITY_CLAIM",
        "source": source_info, "frame_count": 299,
        "map": {"path": map_path, "sha256": MAP_SHA, "reference": 149, "resampler": "catmull-rom", "quad_dimensions": [geom.width, geom.height]},
        "transform": {"a": [transform.a.re, transform.a.im], "b": [transform.b.re, transform.b.im], "bits": [transform.a.re.to_bits(), transform.a.im.to_bits(), transform.b.re.to_bits(), transform.b.im.to_bits()]},
        "transform_units": "stored quad-plane reference-to-source similarity; production fullres gather performs its native conversion",
        "input_order_sha256": ORDER_SHA, "original": original, "gathered": gathered,
        "phase_comparison_original_vs_gathered_full_crop": phase_comparison,
        "phase_comparison_limit": "different physical gauges; same-index differences are not interpolation or placement error and not a sharpness metric",
        "ca_disabled_explicitly": true, "resolved_ca_profile_none": true,
        "any_channel_identity_asserted": false,
        "independent_decode": {
            "status": "PENDING_SEPARATELY_SCHEDULED_INDEPENDENT_COMPARISON",
            "bound_original": "original-crop.u16le",
            "source_sha256": SOURCE_SHA,
            "original_active_crop_xywh": CROP,
            "comparison_contract": "copy RawPy raw_image_visible inside its context; compare this exact interior original crop and all four CFA phases, not the resampled gathered crop; retain decoder/version, source SHA/mtime and differing-sensel counts"
        },
        "whole_active_coverage": coverage, "rayon_workers": rayon::current_num_threads(),
        "environment": environment, "test_executable": {"path": exe, "sha256": sha(&exe)?},
        "harness_sha256": sha(&repo.join("experiments/raw-quality-2026-10-26/insect-consumer-spread/capture-gather143.rs"))?,
        "gather_seconds_operational_only": gather_seconds, "elapsed_seconds": started.elapsed().as_secs_f64(),
        "original_map_order_unchanged": true,
        "scope": "exactly source143 decoded through production fullres CPU gather with lateral CA explicitly disabled; frozen full299 map/reference149 and original source143 pull; no alignment fit, stack or renderer; complete delivered crop extent with original and reference gauges explicitly distinct"
    });
    let mut receipt_file = OpenOptions::new()
        .write(true)
        .create_new(true)
        .open(out.join("capture.json"))?;
    serde_json::to_writer_pretty(&mut receipt_file, &receipt)?;
    receipt_file.write_all(b"\n")?;
    receipt_file.flush()?;
    eprintln!("source143 CA-off gather captured to {}", out.display());
    Ok(())
}
