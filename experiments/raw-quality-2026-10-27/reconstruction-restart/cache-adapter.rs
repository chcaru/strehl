// Read-only cached numerical pair. No RAW decoder, gather, hull or image writer.
use super::operator;
use super::super::consistent_reconstruction::operator as historical;
use anyhow::{ensure, Context, Result};
use serde::Deserialize;
use serde_json::{json, Value};
use sha2::{Digest, Sha256};
use std::{
    fs::{File, OpenOptions},
    io::{BufReader, Read, Write},
    path::{Path, PathBuf},
    time::{Instant, SystemTime},
};
use strehl_core::pyramid::LevelSize;

const ORIGINAL: &str = "C:/dev/blog/death-of-software/projects/strehl/experiments/consistent-reconstruction";
const CACHE: &str = "full-1/output/canonical-coefficients.f32";
const CACHE_BYTES: u64 = 150_194_784;
const CACHE_SHA: &str = "fd441cdb71515f423292b38a3ba055d677a835803b7d0bc19edb29a288ada9e2";
const OLD_SOURCE_SHA: &str = "b0b83797af39f7f234e84ce2aa48ebaedbd70c21c57e57722eeed99c58d6548b";
const PINS: &[(&str, &str)] = &[
    (CACHE, CACHE_SHA),
    ("operator.rs", "fe8b1b978e8895a55e0cf3ea3e21a72bdf5a9afa189207397a5288234ca92258"),
    ("full-1/output/canonical-coefficients.json", "728f0c323cc298753b7238faf5e5d9861c583d712314a2331c8f6eff93b740f8"),
    ("full-1/output/solver-results.json", "02a1180b8ac802bdc804f66dd4526a56b2a224a3d8ee302d22f012e633633a7f"),
    ("full-1/output/receipt.json", "bddc33398cdcb945f1f5201d60cf7bd43983c4151f6d09034ce59edec40d443a"),
    ("full-1/completion.json", "7f3313aed4457168ee1f93046e57dd4b037183bf3df7a28117488fa868765bd2"),
    ("full-1/input-order.json", "ca1d16d0ffab95372c3401c48e9da79b330d4d2c6a4dd76077e06aa74a39c364"),
    ("full-1/output/observer-placebo.json", "a61d02cae35d4cdb3dafbd585d658fa212b38cb5bf8e6857dc96f03992b98f1a"),
    ("full-1/bindings.json", "840be355edcff16ebbccd06b0f2f911e0d51fd9f293a6369fd517855eb86fc4b"),
];

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct Config {
    schema: u32,
    out_dir: PathBuf,
    expected_test_executable_sha256: String,
}

fn digest(h: Sha256) -> String {
    h.finalize().iter().map(|v| format!("{v:02x}")).collect()
}
fn file_hash(path: &Path) -> Result<String> {
    let mut f = File::open(path)?;
    let mut h = Sha256::new();
    let mut buffer = vec![0; 1 << 20];
    loop {
        let n = f.read(&mut buffer)?;
        if n == 0 { break; }
        h.update(&buffer[..n]);
    }
    Ok(digest(h))
}
fn field_hash(values: &[f32]) -> String {
    let mut h = Sha256::new();
    for value in values { h.update(value.to_bits().to_le_bytes()); }
    digest(h)
}
fn save(path: &Path, value: &Value) -> Result<()> {
    let mut f = OpenOptions::new().write(true).create_new(true).open(path)?;
    serde_json::to_writer_pretty(&mut f, value)?;
    writeln!(f)?;
    Ok(())
}
fn read_json(relative: &str) -> Result<Value> {
    Ok(serde_json::from_reader(BufReader::new(File::open(Path::new(ORIGINAL).join(relative))?))?)
}
fn binding(path: &Path) -> Result<Value> {
    let m = std::fs::metadata(path)?;
    let stamp = m.modified()?.duration_since(SystemTime::UNIX_EPOCH)?.as_nanos();
    Ok(json!({"path":path,"bytes":m.len(),"mtime_ns":stamp,"sha256":file_hash(path)?}))
}
fn bindings(executable: &Path, old_source: &Path, expected_exe: &str) -> Result<Vec<Value>> {
    let mut result = Vec::new();
    for &(relative, expected) in PINS {
        let row = binding(&Path::new(ORIGINAL).join(relative))?;
        ensure!(row["sha256"] == expected, "retained binding changed: {relative}");
        if relative == CACHE { ensure!(row["bytes"] == CACHE_BYTES, "cache bytes changed"); }
        result.push(row);
    }
    let row = binding(old_source)?;
    ensure!(row["sha256"] == OLD_SOURCE_SHA, "compiled historical source file changed");
    result.push(row);
    let row = binding(executable)?;
    ensure!(row["sha256"] == expected_exe, "test executable changed");
    result.push(row);
    Ok(result)
}

fn load_targets(meta: &Value) -> Result<(Vec<LevelSize>, Vec<Vec<Vec<f32>>>)> {
    let expected_sizes = [[3250,2166],[1625,1083],[813,542],[407,271],
        [204,136],[102,68],[51,34],[26,17]];
    ensure!(meta["schema"] == 1 && meta["binary"] == "canonical-coefficients.f32"
        && meta["binary_bytes"] == CACHE_BYTES && meta["binary_sha256"] == CACHE_SHA
        && meta["encoding"] == "little-endian-f32"
        && meta["plane_order"] == json!(["R","G1","G2","B"]), "coefficient metadata");
    let layout = meta["layout"].as_array().context("missing cache layout")?;
    ensure!(layout.len() == 32, "complete four-plane/eight-level layout required");
    let sizes = expected_sizes.iter().map(|s| LevelSize { width:s[0], height:s[1] }).collect::<Vec<_>>();
    let mut f = BufReader::new(File::open(Path::new(ORIGINAL).join(CACHE))?);
    let mut offset = 0u64;
    let mut targets = Vec::new();
    for plane in 0..4 {
        let mut bands = Vec::new();
        for (level, size) in sizes.iter().enumerate() {
            let bytes = (size.pixels() * 4) as u64;
            let item = &layout[plane * 8 + level];
            ensure!(item["plane"] == plane && item["level"] == level
                && item["size"] == json!([size.width,size.height])
                && item["offset_bytes"] == offset && item["bytes"] == bytes, "cache layout mismatch");
            let mut raw = vec![0u8; bytes as usize];
            f.read_exact(&mut raw)?;
            let mut h = Sha256::new(); h.update(&raw);
            let hash = digest(h);
            ensure!(item["sha256"] == hash && meta["target_sha256"][plane][level] == hash,
                "coefficient payload differs at {plane}/{level}");
            let values = raw.chunks_exact(4).map(|b| f32::from_le_bytes(b.try_into().unwrap())).collect::<Vec<_>>();
            ensure!(values.iter().all(|v| v.is_finite()), "nonfinite cached target");
            bands.push(values);
            offset += bytes;
        }
        targets.push(bands);
    }
    ensure!(offset == CACHE_BYTES && f.read(&mut [0u8;1])? == 0, "cache trailing/absent data");
    Ok((sizes, targets))
}

fn old_record(plane: usize, s: &historical::Solve) -> Value {
    json!({"plane":plane,"admitted":s.converged,"converged":s.converged,"iterations":s.iterations,
        "relative_residual":s.relative_residual,"error_bound_rms":s.error_bound_rms,
        "correction_rhs_norm":s.correction_rhs_norm,"correction_residual_norm":s.correction_residual_norm,
        "correction_objective":s.correction_objective,"final_rounding_bound":s.final_rounding_bound,
        "initial_objective":s.initial_objective,"objective":s.objective,"refusal":s.refusal,
        "last_iterate_sha256":field_hash(&s.image)})
}
fn new_record(plane: usize, s: &operator::Solve) -> Value {
    json!({"plane":plane,"admitted":s.converged,"converged":s.converged,"iterations":s.iterations,
        "relative_residual":s.relative_residual,"error_bound_rms":s.error_bound_rms,
        "correction_rhs_norm":s.correction_rhs_norm,"correction_residual_norm":s.correction_residual_norm,
        "correction_objective":s.correction_objective,"final_rounding_bound":s.final_rounding_bound,
        "initial_objective":s.initial_objective,"objective":s.objective,"refusal":s.refusal,
        "last_iterate_sha256":field_hash(&s.image),"restart_applied":s.restart_applied,
        "residual_trace":s.residual_trace})
}

#[test]
#[ignore = "root-scheduled bound cached pair; requires explicit output config"]
fn cached_chip_pair() -> Result<()> {
    let config_path = PathBuf::from(std::env::var_os("STREHL_RECONSTRUCTION_RESTART_CONFIG")
        .context("root config required")?);
    let config_bytes = std::fs::read(&config_path)?;
    let cfg: Config = serde_json::from_slice(&config_bytes)?;
    ensure!(cfg.schema == 1 && cfg.out_dir.is_absolute(), "config schema/absolute output");
    let root = Path::new(env!("CARGO_MANIFEST_DIR")).join("../..").canonicalize()?;
    let output_parent = cfg.out_dir.parent().context("output parent")?.canonicalize()?;
    ensure!(output_parent.starts_with(root.join("outputs").canonicalize()?), "fresh workspace output required");
    std::fs::create_dir(&cfg.out_dir)?;
    let executable = std::env::current_exe()?;
    let old_source = root.join("experiments/consistent-reconstruction/operator.rs");
    let before = bindings(&executable, &old_source, &cfg.expected_test_executable_sha256)?;
    save(&cfg.out_dir.join("bindings-before.json"), &json!(before))?;
    save(&cfg.out_dir.join("started.json"), &json!({"schema":1,"config":config_path,
        "executable":executable,"max_iterations":operator::MAX_ITERATIONS,
        "restart_iteration":operator::RESTART_ITERATION,"error_rms_limit_dn":operator::ERROR_RMS_LIMIT,
        "RAW_reads":0,"image_output":false,"cache_only":true}))?;
    let started = Instant::now();
    let outcome = (|| -> Result<Value> {
        ensure!(historical::MAX_ITERATIONS == operator::MAX_ITERATIONS
            && historical::ERROR_RMS_LIMIT.to_bits() == operator::ERROR_RMS_LIMIT.to_bits(), "solver limits changed");
        let original_text = std::fs::read_to_string(Path::new(ORIGINAL).join("operator.rs"))?;
        ensure!(std::fs::read_to_string(&old_source)?.replace("\r\n", "\n")
            == original_text.replace("\r\n", "\n"), "old compiled source differs beyond line endings");
        let meta = read_json("full-1/output/canonical-coefficients.json")?;
        let receipt = read_json("full-1/output/receipt.json")?;
        let completion = read_json("full-1/completion.json")?;
        let observer = read_json("full-1/output/observer-placebo.json")?;
        let historic = read_json("full-1/output/solver-results.json")?;
        let order = read_json("full-1/input-order.json")?;
        ensure!(completion["status"] == "NUMERICAL_REFUSAL" && completion["sources_unchanged"] == true
            && completion["baseline_current_production_pixels_and_icc_exact"] == true
            && completion["receipt"]["sha256"] == PINS[4].1, "historical completion mismatch");
        ensure!(receipt["status"] == "NUMERICAL_REFUSAL" && receipt["candidate_valid"] == false
            && receipt["source_count"] == 299 && receipt["held_state_bit_exact"] == true
            && receipt["canonical_coefficients_sha256"] == meta["target_sha256"]
            && receipt["coefficients_after_sha256"] == meta["target_sha256"]
            && receipt["coefficient_cache"]["binary_sha256"] == CACHE_SHA
            && observer["whole_tiff_byte_exact"] == true, "historical coefficient lineage mismatch");
        let m = &meta["metadata"];
        ensure!(m["frames"] == 299 && m["reference"] == 149 && m["crop"] == json!([133,89,3250,2166])
            && m["full_geometry"] == json!([3516,2344])
            && m["map_sha256"] == "ce8534c9e65c5c761373bad87df5352c1c46319b7eaf7f7c91477ea61b4f4922"
            && receipt["map_sha256"] == m["map_sha256"], "held source gauge mismatch");
        let sources = order.as_array().context("source order array")?;
        ensure!(sources.len() == 299 && sources.iter().enumerate().all(|(i,s)| s["index"] == i), "historical source order/count");
        let (sizes, targets) = load_targets(&meta)?;
        let mut old_rows = Vec::new();
        let mut old_exact = true;
        for (plane, bands) in targets.iter().enumerate() {
            let initial = historical::synthesis(&sizes, bands);
            ensure!(receipt["baseline_pre_hull_sha256"][plane] == field_hash(&initial), "canonical initial changed");
            let old = historical::reconstruct(&sizes, bands, &initial)?;
            let row = old_record(plane, &old);
            let expected = &historic["solves"][plane];
            let exact = row.as_object().unwrap().iter().all(|(k,v)| &expected[k] == v);
            old_exact &= exact;
            save(&cfg.out_dir.join(format!("historical-plane-{plane}.json")),
                &json!({"record":row,"matches_historical_exactly":exact}))?;
            old_rows.push(row);
        }
        ensure!(old_exact, "same-binary old arm failed historical numerical/hash reproduction");
        let mut new_rows = Vec::new();
        let mut all_admit = true;
        for (plane, bands) in targets.iter().enumerate() {
            let initial = operator::synthesis(&sizes, bands);
            ensure!(receipt["baseline_pre_hull_sha256"][plane] == field_hash(&initial), "candidate initial changed");
            let solved = operator::reconstruct(&sizes, bands, &initial)?;
            all_admit &= solved.converged;
            let row = new_record(plane, &solved);
            save(&cfg.out_dir.join(format!("restart-plane-{plane}.json")), &row)?;
            new_rows.push(row);
        }
        Ok(json!({"schema":1,"status":if all_admit {"CACHED_NUMERICAL_PASS"} else {"CACHED_NUMERICAL_REFUSAL"},
            "old_historical_exact":old_exact,"all_restart_planes_admitted":all_admit,
            "historical":old_rows,"restart":new_rows,"source_count":299,"reference":149,
            "crop":m["crop"],"cache_sha256":CACHE_SHA,"max_iterations":operator::MAX_ITERATIONS,
            "restart_iteration":operator::RESTART_ITERATION,"error_rms_limit_dn":operator::ERROR_RMS_LIMIT,
            "image_output":false,"RAW_reads":0,"quality_claim":false,"full_photo_released":false,
            "scope":"Cached coefficient solver only. Prior glint/far-detail harms remain; no hull or image was reconstructed for delivery."}))
    })();
    // Check retained files even after a numerical/lineage error. A process kill
    // cannot reach this receipt and must remain incomplete in the root wrapper.
    let after = bindings(&executable, &old_source, &cfg.expected_test_executable_sha256);
    let unchanged = after.as_ref().map(|a| a == &before).unwrap_or(false)
        && std::fs::read(&config_path).map(|v| v == config_bytes).unwrap_or(false);
    save(&cfg.out_dir.join("bindings-after.json"), &json!({"unchanged":unchanged,
        "bindings":after.as_ref().ok(),"error":after.as_ref().err().map(|e| e.to_string())}))?;
    match outcome {
        Ok(mut result) => {
            result["inputs_unchanged"] = json!(unchanged);
            result["wall_seconds"] = json!(started.elapsed().as_secs_f64());
            save(&cfg.out_dir.join("cache-result.json"), &result)?;
            ensure!(unchanged, "cache/source/executable/config changed");
            Ok(())
        }
        Err(error) => {
            save(&cfg.out_dir.join("cache-result.json"), &json!({"status":"FAILED",
                "error":error.to_string(),"inputs_unchanged":unchanged,
                "wall_seconds":started.elapsed().as_secs_f64(),"quality_claim":false}))?;
            Err(error)
        }
    }
}
