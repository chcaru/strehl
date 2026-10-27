//! Read-only original-CFA ROI export. Root alone schedules compilation and RAW access.
use anyhow::{Context, Result, ensure};
use serde_json::{Value, json};
use sha2::{Digest, Sha256};
use std::collections::HashSet;
use std::env;
use std::fs::{self, File, OpenOptions};
use std::io::{Read, Write};
use std::path::{Path, PathBuf};
use std::time::UNIX_EPOCH;
use strehl_core::CfaPlane;
use strehl_core::noise::Provenance;
use strehl_core::profile::noise_model_for;
use strehl_raw::Region;

const PLAN_SCHEMA: &str = "rea-a7c2-i-ca-diagnostic-plan-v1";
const PHASES: [CfaPlane; 4] = [CfaPlane::R, CfaPlane::G1, CfaPlane::G2, CfaPlane::B];
const NAMES: [&str; 4] = ["R", "G1", "G2", "B"];

fn hex(bytes: &[u8]) -> String {
    bytes.iter().map(|b| format!("{b:02x}")).collect()
}

fn digest(bytes: &[u8]) -> String {
    hex(&Sha256::digest(bytes))
}

fn file_digest(path: &Path) -> Result<String> {
    let mut file = File::open(path)?;
    let mut hash = Sha256::new();
    let mut block = [0u8; 65536];
    loop {
        let n = file.read(&mut block)?;
        if n == 0 {
            break;
        }
        hash.update(&block[..n]);
    }
    Ok(hex(&hash.finalize()))
}

fn stamp(path: &Path) -> Result<(u64, u64)> {
    let m = fs::metadata(path)?;
    ensure!(m.is_file(), "input is not a regular file");
    Ok((
        m.len(),
        u64::try_from(m.modified()?.duration_since(UNIX_EPOCH)?.as_nanos())?,
    ))
}

fn stamp_json(s: (u64, u64)) -> Value {
    json!({"bytes": s.0, "modified_unix_ns": s.1})
}

fn path_key(path: &Path) -> String {
    path.to_string_lossy()
        .replace('/', "\\")
        .to_ascii_lowercase()
}

fn within(path: &Path, root: &Path) -> bool {
    let p = path_key(path);
    let r = path_key(root).trim_end_matches('\\').to_string();
    p == r || p.starts_with(&(r + "\\"))
}

fn fresh_output(path: &Path, sources: &[PathBuf]) -> Result<PathBuf> {
    ensure!(
        path.is_absolute() && !path.exists(),
        "output must be a fresh absolute directory"
    );
    let parent = path
        .parent()
        .context("output parent absent")?
        .canonicalize()?;
    let out = parent.join(path.file_name().context("output leaf absent")?);
    // Refuse the common capture ancestor, not only the four immediate source folders.
    let mut capture_root = sources[0].parent().context("source parent absent")?;
    while !sources.iter().all(|p| within(p, capture_root)) {
        capture_root = capture_root
            .parent()
            .context("sources have no common capture root")?;
    }
    ensure!(
        !within(&out, capture_root),
        "output inside capture corpus refused"
    );
    fs::create_dir(&out)?;
    Ok(out)
}

fn write_new(path: &Path, bytes: &[u8]) -> Result<()> {
    let mut f = OpenOptions::new().create_new(true).write(true).open(path)?;
    f.write_all(bytes)?;
    f.sync_all()?;
    Ok(())
}

fn write_json(path: &Path, value: &Value) -> Result<()> {
    let mut bytes = serde_json::to_vec_pretty(value)?;
    bytes.push(b'\n');
    write_new(path, &bytes)
}

fn region(value: &Value) -> Result<Region> {
    let a = value.as_array().context("ROI must be [x,y,width,height]")?;
    ensure!(a.len() == 4, "ROI needs four integers");
    let mut n = [0usize; 4];
    for (i, v) in a.iter().enumerate() {
        n[i] = usize::try_from(
            v.as_u64()
                .context("ROI coordinate is not unsigned integer")?,
        )?;
    }
    Ok(Region {
        x: n[0],
        y: n[1],
        width: n[2],
        height: n[3],
    })
}

fn inside(r: Region, width: usize, height: usize) -> bool {
    r.width > 0
        && r.height > 0
        && r.x.checked_add(r.width).is_some_and(|x| x <= width)
        && r.y.checked_add(r.height).is_some_and(|y| y <= height)
}

fn export_bytes(
    data: &[u16],
    stride: usize,
    height: usize,
    active: Region,
    roi: Region,
) -> Result<Vec<u8>> {
    ensure!(
        stride.checked_mul(height) == Some(data.len()),
        "buffer dimensions disagree"
    );
    ensure!(
        inside(active, stride, height),
        "active area outside decoded storage"
    );
    ensure!(
        inside(roi, active.width, active.height),
        "ROI outside decoded active area"
    );
    let bytes = roi
        .width
        .checked_mul(roi.height)
        .and_then(|n| n.checked_mul(2))
        .context("ROI size overflow")?;
    let mut out = Vec::with_capacity(bytes);
    for y in roi.y..roi.y + roi.height {
        let first = (active.y + y) * stride + active.x + roi.x;
        for code in &data[first..first + roi.width] {
            out.extend_from_slice(&code.to_le_bytes());
        }
    }
    ensure!(out.len() == bytes, "incomplete ROI extraction");
    Ok(out)
}

fn phase_tile(x: usize, y: usize) -> [[&'static str; 2]; 2] {
    std::array::from_fn(|dy| std::array::from_fn(|dx| NAMES[((y + dy) & 1) * 2 + ((x + dx) & 1)]))
}

fn commission() -> Result<()> {
    let active = Region {
        x: 2,
        y: 0,
        width: 4,
        height: 4,
    };
    let mut data = vec![65535u16; 6 * 5];
    for y in 0..4 {
        for x in 0..4 {
            data[y * 6 + 2 + x] = (1000 + y * 10 + x) as u16;
        }
    }
    let r = Region {
        x: 1,
        y: 1,
        width: 2,
        height: 2,
    };
    ensure!(
        export_bytes(&data, 6, 5, active, r)? == [0xf3, 3, 0xf4, 3, 0xfd, 3, 0xfe, 3],
        "exact stride/origin/u16le control failed"
    );
    let bad = Region {
        x: 3,
        y: 3,
        width: 2,
        height: 2,
    };
    ensure!(
        export_bytes(&data, 6, 5, active, bad).is_err(),
        "outside-active control did not fail"
    );
    ensure!(
        export_bytes(&data, 5, 5, active, r).is_err(),
        "wrong-stride control did not fail"
    );
    ensure!(
        phase_tile(1, 1) == [["B", "G2"], ["G1", "R"]],
        "odd-origin CFA control failed"
    );
    ensure!(
        digest(b"abc") == "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad",
        "SHA256 control failed"
    );
    Ok(())
}

fn main() -> Result<()> {
    let args: Vec<_> = env::args_os().collect();
    commission()?;
    if args.len() == 2 && args[1].to_str() == Some("--commission-only") {
        println!("REA_NATIVE_ROI_COMMISSION_PASS (no files decoded)");
        return Ok(());
    }
    ensure!(
        args.len() == 7 && args[1] == "--plan" && args[3] == "--plan-sha256" && args[5] == "--out",
        "usage: rea-native-roi --plan <json> --plan-sha256 <frozen-sha256> --out <fresh-absolute-dir> | --commission-only"
    );
    let plan_path = Path::new(&args[2]).canonicalize()?;
    let plan_bytes = fs::read(&plan_path)?;
    let plan_hash = digest(&plan_bytes);
    ensure!(
        Some(plan_hash.as_str()) == args[4].to_str(),
        "plan SHA256 differs from root-frozen plan"
    );
    let plan: Value = serde_json::from_slice(&plan_bytes)?;
    ensure!(
        plan["schema"] == PLAN_SCHEMA && plan["workers"] == 1 && plan["new_raw_files"] == 4,
        "wrong plan schema, source count or worker scope"
    );
    ensure!(
        plan["decodes_per_file"]["native"] == 1,
        "plan must authorize one native decode per source"
    );
    let specs = plan["sources"].as_array().context("sources absent")?;
    ensure!(specs.len() == 4, "exactly four sources required");
    let mut sources = Vec::new();
    let mut seen = HashSet::new();
    let mut windows = Vec::new();
    let mut initial = Vec::new();
    for s in specs {
        let p = Path::new(s["path"].as_str().context("source path absent")?);
        ensure!(p.is_absolute(), "source path must be absolute");
        let p = p.canonicalize()?;
        ensure!(seen.insert(path_key(&p)), "duplicate source refused");
        let before = stamp(&p)?;
        ensure!(
            Some(before.0) == s["historical_bytes"].as_u64()
                && Some(before.1) == s["historical_mtime_ns"].as_u64(),
            "source size/mtime differs from frozen identity: {}",
            p.display()
        );
        let expected_hash = s["historical_full_file_sha256"]
            .as_str()
            .context("historical full-file SHA256 absent")?;
        ensure!(
            expected_hash.len() == 64 && expected_hash.bytes().all(|b| b.is_ascii_hexdigit()),
            "bad historical SHA256"
        );
        let scene = s["scene"].as_str().context("scene absent")?;
        let rois = plan["witness_windows_active_xywh"][scene]
            .as_array()
            .context("scene windows absent")?
            .iter()
            .map(region)
            .collect::<Result<Vec<_>>>()?;
        ensure!(
            rois.iter()
                .all(|r| r.width == 384 && r.height == 384 && r.x % 2 == 0 && r.y % 2 == 0),
            "this frozen diagnostic requires even-origin 384x384 windows"
        );
        sources.push(p);
        windows.push(rois);
        initial.push(before);
    }
    ensure!(
        windows.iter().map(Vec::len).sum::<usize>() == 48,
        "frozen 48-window population changed"
    );
    rayon::ThreadPoolBuilder::new()
        .num_threads(1)
        .build_global()?;
    ensure!(
        rayon::current_num_threads() == 1,
        "one native worker required"
    );
    let out = fresh_output(Path::new(&args[6]), &sources)?;
    write_new(&out.join("run-status.txt"), b"STARTED_NOT_COMPLETE\n")?;
    write_new(&out.join("frozen-plan.json"), &plan_bytes)?;
    let mut frames = Vec::new();
    let mut records = Vec::new();
    for (i, path) in sources.iter().enumerate() {
        let before = stamp(path)?;
        ensure!(before == initial[i], "source changed before its decode");
        let frame =
            strehl_raw::decode(path).with_context(|| format!("decode {}", path.display()))?;
        let after_decode = stamp(path)?;
        ensure!(after_decode == before, "source changed while decoding");
        let a = frame.active;
        ensure!(frame.camera == "ILCE-7CM2", "unexpected camera model");
        let storage = (frame.stride, frame.buffer_height);
        let geometry_case = match ((a.x, a.y, a.width, a.height), storage) {
            ((0, 0, 7032, 4688), (7032, 4688)) => "tight_7032x4688",
            ((0, 0, 7032, 4688), (7168, 5120)) => "padded_7168x5120_active7032x4688",
            ((0, 0, 7040, 4688), (7040, 4688)) => "uncompressed_tight_7040x4688",
            _ => anyhow::bail!(
                "unreviewed native geometry: active={:?}, buffer={:?}",
                a,
                storage
            ),
        };
        ensure!(
            frame.levels.black.is_finite()
                && frame.levels.white.is_finite()
                && frame.levels.white > frame.levels.black,
            "invalid decoder levels"
        );
        let iso = frame.iso.context("ISO absent; do not guess noise model")?;
        ensure!(iso.is_finite() && iso > 0.0, "invalid ISO");
        let model = noise_model_for(&frame.camera, frame.iso, frame.levels);
        ensure!(
            model.provenance == Provenance::Profile,
            "profile unavailable; fallback refused for this diagnostic"
        );
        let mut noise = Vec::new();
        for (p, name) in PHASES.into_iter().zip(NAMES) {
            let n = model.plane(p);
            ensure!(
                n.gain_dn_per_e.is_finite()
                    && n.gain_dn_per_e > 0.0
                    && n.read_noise_e.is_finite()
                    && n.read_noise_e > 0.0,
                "invalid noise coefficients"
            );
            ensure!(
                n.variance(0.0).is_finite()
                    && n.variance(0.0) > 0.0
                    && n.variance(1000.0).is_finite()
                    && n.variance(1000.0) > 0.0,
                "invalid noise variance evaluations"
            );
            noise.push(json!({"phase":name,"gain_dn_per_e":n.gain_dn_per_e,"gain_f32_bits":n.gain_dn_per_e.to_bits(),
                "read_noise_e":n.read_noise_e,"read_noise_f32_bits":n.read_noise_e.to_bits(),
                "black_dn":n.levels.black,"white_dn":n.levels.white,"read_floor_dn":n.read_floor_dn(),
                "variance_zero_dn2":n.variance(0.0),"variance_1000_dn2":n.variance(1000.0)}));
        }
        for (j, r) in windows[i].iter().copied().enumerate() {
            let bytes = export_bytes(&frame.data, frame.stride, frame.buffer_height, a, r)?;
            let name = format!("source-{i}-roi-{j}.u16le");
            write_new(&out.join(&name), &bytes)?;
            records.push(json!({"source_index":i,"roi_index":j,"scene":specs[i]["scene"],"path":specs[i]["path"],
                "active_xywh":[r.x,r.y,r.width,r.height],"buffer_xywh":[a.x+r.x,a.y+r.y,r.width,r.height],
                "cfa_tile_at_roi_origin":phase_tile(a.x+r.x,a.y+r.y),"file":name,"bytes":bytes.len(),
                "sha256":digest(&bytes),"dtype":"uint16-little-endian","row_order":"C"}));
        }
        let after_export = stamp(path)?;
        ensure!(after_export == before, "source changed during extraction");
        let header = json!({"source_index":i,"scene":specs[i]["scene"],"path":specs[i]["path"],"canonical_path":path,
            "expected_full_file_sha256":specs[i]["historical_full_file_sha256"],
            "input_before":stamp_json(before),"input_after_decode":stamp_json(after_decode),"input_after_export":stamp_json(after_export),
            "camera":frame.camera,"iso":iso,"black_dn":frame.levels.black,"white_dn":frame.levels.white,
            "level_provenance":"public Frame scalar levels; decoder first black/white entry, not a per-channel table",
            "wb_coeffs_rgbe":frame.wb_coeffs.map(|v| v.is_finite().then_some(v)),"wb_coeffs_f32_bits":frame.wb_coeffs.map(f32::to_bits),
            "buffer_stride_samples":frame.stride,"buffer_height_rows":frame.buffer_height,"buffer_samples":frame.data.len(),
            "active_in_buffer_xywh":[a.x,a.y,a.width,a.height],"native_geometry_case":geometry_case,"cfa_pattern":"RGGB",
            "cfa_provenance":"strehl_raw::decode RGGB-only guard; no independent CFA field exists on Frame",
            "cfa_tile_at_active_origin":phase_tile(a.x,a.y),"orientation_applied":false,
            "noise_model":{"source":"noise_model_for(camera, ISO, decoder levels)","provenance":"Profile","iso":model.iso,
                "planes_raster_order":noise,"signal_units":"signed black-subtracted DN",
                "variance_formula":"f32 gain * max(signal_dn,0) + (read_noise_e * gain)^2; no fitted ROI term or PRNU"}});
        write_json(&out.join(format!("source-{i}.json")), &header)?;
        frames.push(header);
        eprintln!("REA_NATIVE_ROI_FRAME {}/4 {}", i + 1, path.display());
        // Drop this full u16 CFA frame before decoding the next source.
    }
    for (i, path) in sources.iter().enumerate() {
        let after_run = stamp(path)?;
        ensure!(
            after_run == initial[i],
            "input changed by end of native run"
        );
        frames[i]["input_after_run"] = stamp_json(after_run);
    }
    ensure!(
        frames.len() == 4 && records.len() == 48,
        "incomplete export population"
    );
    write_json(
        &out.join("manifest.json"),
        &json!({"schema":"rea-native-roi-export-v1","status":"COMPLETE","commission":"PASS",
        "plan_path":plan_path,"plan_sha256":plan_hash,"source_sha256":digest(include_bytes!("raw-roi-export.rs")),
        "executable_sha256":file_digest(&env::current_exe()?)?,"workers":1,"decodes_per_source":1,
        "source_pixel_gauge":plan["source_pixel_gauge"],"operation":"exact original CFA ROI extraction only; no black subtraction, interpolation, demosaic or correction",
        "input_hash_note":"historical expected hashes are copied from the frozen plan, not recomputed here; join root before/after full-file hash receipt",
        "frames":frames,"records":records}),
    )?;
    fs::write(out.join("run-status.txt"), b"COMPLETE\n")?;
    println!("REA_NATIVE_ROI_COMPLETE {}", out.display());
    Ok(())
}
