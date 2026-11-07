//! Actual-core producer controls, known truth and two separate timestamp targets.
#![allow(dead_code)]
#[path = "noise-bee-repeat-binding.rs"]
mod binding;
#[path = "real-noise-consumer-warped.rs"]
mod context;
#[path = "noise-bee-repeat-gate.rs"]
mod model;
#[path = "real-noise-consumer-structure-operator.rs"]
mod operator;
#[path = "noise-bee-repeat-producer.rs"]
mod producer;
#[path = "noise-bee-repeat-model.rs"]
mod temporal;
use anyhow::{Context, Result, ensure};
use serde_json::{Value, json};
use sha2::{Digest, Sha256};
use std::{fs, io::Write, path::Path};
use strehl_cli::{
    session_input::{ResolvedSession, SourceIdentity},
    session_sampling::SamplingDomain,
};
fn sha(bytes: &[u8]) -> String {
    Sha256::digest(bytes)
        .iter()
        .map(|x| format!("{x:02x}"))
        .collect()
}
fn read(p: &Path) -> Result<Value> {
    Ok(serde_json::from_slice(&fs::read(p)?)?)
}
fn write(p: &Path, v: &Value) -> Result<()> {
    let mut f = fs::OpenOptions::new()
        .create_new(true)
        .write(true)
        .open(p)?;
    serde_json::to_writer_pretty(&mut f, v)?;
    f.write_all(b"\n")?;
    f.sync_all()?;
    Ok(())
}
fn main() -> Result<()> {
    let args: Vec<_> = std::env::args().collect();
    ensure!(args.len() == 5, "RENDER PROTOCOL NEW_OUT flat|all|roles");
    let render = Path::new(&args[1]);
    let input = Path::new(&args[2]);
    let out = Path::new(&args[3]);
    fs::create_dir(out)?;
    let bytes = fs::read(input)?;
    ensure!(
        sha(&bytes) == "f2fc47d451314ef0bf4a188cdf52d147d17de4fd72b947f58069017f631fcae4",
        "frozen bee roles"
    );
    let protocol: Value = serde_json::from_slice(&bytes)?;
    let originals_path = input
        .parent()
        .context("input parent")?
        .join("source-identities32.json");
    let original_bytes = fs::read(originals_path)?;
    ensure!(
        protocol["input_receipts"][r"inputs\source-identities32.json"] == sha(&original_bytes),
        "original identity receipt changed"
    );
    let originals: Vec<Value> = serde_json::from_slice(&original_bytes)?;
    let original_records: Vec<_> = originals
        .iter()
        .map(|v| {
            Ok(binding::Record {
                filename: Path::new(v["path"].as_str().context("original path")?)
                    .file_name()
                    .context("name")?
                    .to_str()
                    .context("UTF8")?
                    .into(),
                bytes: v["bytes"].as_u64().context("bytes")?,
                sha256: v["sha256"].as_str().context("hash")?.into(),
            })
        })
        .collect::<Result<_>>()?;
    let identities: Vec<SourceIdentity> =
        serde_json::from_value(read(&render.join("source-identities.json"))?)?;
    let copies: Vec<_> = identities
        .iter()
        .map(|v| {
            Ok(binding::Record {
                filename: Path::new(&v.path)
                    .file_name()
                    .context("name")?
                    .to_str()
                    .context("UTF8")?
                    .into(),
                bytes: v.bytes,
                sha256: v.sha256.clone(),
            })
        })
        .collect::<Result<_>>()?;
    let indices = binding::bind32(&original_records, &copies).map_err(anyhow::Error::msg)?;
    let c = context::context(render)?;
    let report = read(&render.join("render-report.json"))?;
    let session: ResolvedSession = serde_json::from_value(read(&render.join("session.json"))?)?;
    ensure!(session.frames.len() == 32, "session count");
    let full = c.map.geometry();
    let witness = protocol["witnesses"]
        .as_array()
        .unwrap()
        .iter()
        .find(|v| v["id"] == "eye-facets")
        .unwrap();
    let f = witness["active_fraction_center"].as_array().unwrap();
    let d = SamplingDomain {
        full,
        x: (f[0].as_f64().unwrap() * full.width as f64).floor() as usize - 64,
        y: (f[1].as_f64().unwrap() * full.height as f64).floor() as usize - 64,
        width: 128,
        height: 128,
    };
    let pool = rayon::ThreadPoolBuilder::new().num_threads(4).build()?;
    let times = protocol["timestamps_unix"].as_array().unwrap();
    let case_args = |base: usize| {
        let t0 = times[base].as_f64().unwrap();
        (
            std::array::from_fn(|j| indices[base + j]),
            std::array::from_fn(|j| times[base + j].as_f64().unwrap() - t0),
        )
    };
    write(
        &out.join("protocol-frozen.json"),
        &json!({"schema":"strehl.bee-actual-core-risk-controls.v1","command":args,"input_protocol_sha256":sha(&bytes),"original_identity_receipt_sha256":sha(&original_bytes),"bindings":c.bindings,"domain_quad":[d.x,d.y,128,128],"bases":[0,24],"seeds":[144,145,146,147],"levels":[0,20,200,1200,2500],"cutoff":1.10,"consumer":"exact existing four-arm production core; original-u16 synthetic source only","mask":"Q/V complete frozen mask; no R/M pruning","source_sha256":sha(include_bytes!("noise-bee-repeat-risk-controls.rs")),"producer_sha256":sha(include_bytes!("noise-bee-repeat-producer.rs")),"core_consumer_sha256":sha(include_bytes!("real-noise-consumer-structure-consumer.rs")),"gate_sha256":sha(include_bytes!("noise-bee-repeat-gate.rs")),"workers":4,"raw_decodes":0,"cache_reads":0}),
    )?;
    if args[4] == "roles" {
        let (ii, tt) = case_args(0);
        let a = pool.install(|| {
            producer::produce(&c, &report, d, ii, tt, "flat", 200., 144, None, false)
        })?;
        let b = pool.install(|| {
            producer::produce(&c, &report, d, ii, tt, "flat", 200., 144, Some(999), false)
        })?;
        ensure!(
            a.masks == b.masks && a.qualification == b.qualification,
            "R changed mask"
        );
        for (x, y) in a.outcomes.iter().zip(&b.outcomes) {
            ensure!(
                x.valid == y.valid
                    && x.diagnostics == y.diagnostics
                    && x.planes
                        .iter()
                        .flatten()
                        .zip(y.planes.iter().flatten())
                        .all(|(a, b)| a.to_bits() == b.to_bits()),
                "R changed actual consumer"
            );
        }
        ensure!(
            a.references
                .iter()
                .flatten()
                .flatten()
                .zip(b.references.iter().flatten().flatten())
                .any(|(a, b)| a.to_bits() != b.to_bits()),
            "R seed foil inactive"
        );
        let missing = pool
            .install(|| producer::produce(&c, &report, d, ii, tt, "flat", 200., 144, None, true))?;
        ensure!(
            missing.outcomes[2]
                .planes
                .iter()
                .flatten()
                .zip(missing.outcomes[3].planes.iter().flatten())
                .all(|(a, b)| a.to_bits() == b.to_bits()),
            "missing Qguide not exact equal fallback"
        );
        let guide: producer::Planes = std::array::from_fn(|_| vec![1200.; 144 * 144]);
        let mut valid = vec![true; 144 * 144];
        let (g, v) = producer::finish_guide(&guide, &valid)?;
        ensure!(
            g.iter().flatten().all(|x| *x == 1200.) && v.iter().all(|x| *x),
            "flatguide changed"
        );
        valid[0] = false;
        let (_, v) = producer::finish_guide(&guide, &valid)?;
        ensure!(!v[0] && v[32 * 128 + 32], "halo-only poison not propagated");
        let union: std::collections::BTreeSet<_> = a
            .qv_reads
            .iter()
            .chain(&a.r_reads)
            .chain(&a.m_reads)
            .copied()
            .collect();
        ensure!(
            union.len() == 8
                && a.qv_reads.len() == 4
                && a.r_reads.len() == 2
                && a.m_reads.len() == 2,
            "role census"
        );
        write(
            &out.join("report.json"),
            &json!({"passed":true,"checks":["original hash receipt/copy identity","R-only perturbation leaves actual candidates/masks/diagnostics bit-identical","missing Qguide actual equal fallback bit-identical","flatguide exact","guide halo poison","8distinct original roles"],"qv_reads":a.qv_reads,"r_reads":a.r_reads,"m_reads":a.m_reads}),
        )?;
        return Ok(());
    }
    ensure!(args[4] == "flat" || args[4] == "all", "mode");
    let modes = if args[4] == "flat" {
        vec!["flat"]
    } else {
        vec!["flat", "linear", "quadratic", "focus", "shift", "step"]
    };
    let mut summaries = Vec::new();
    for mode in modes {
        let mut rows = Vec::new();
        let mut diagnostic_rows = Vec::new();
        for base in [0, 24] {
            let (ii, tt) = case_args(base);
            for seed in 144..148 {
                for level in [0., 20., 200., 1200., 2500.] {
                    let case = pool.install(|| {
                        producer::produce(&c, &report, d, ii, tt, mode, level, seed, None, false)
                    })?;
                    let blurred = producer::smooth(&case.outcomes[3].planes, 1);
                    for state in 0..2 {
                        for color in 0..4 {
                            for arm in 0..8 {
                                let mut n = 0;
                                let mut risk = 0.;
                                let mut true_delta = 0.;
                                let mut mse = 0.;
                                let mut single_mse = 0.;
                                let mut reference_bias = 0.;
                                let mut mean_error = 0.;
                                let mut transfer = 0.;
                                let mut transfer_den = 0.;
                                for pixel in 0..128 * 128 {
                                    if !case.masks[color][pixel] {
                                        continue;
                                    }
                                    ensure!(
                                        case.outcomes.iter().all(|x| x.valid[pixel]),
                                        "invalid delivered pixel cannot be pruned"
                                    );
                                    let value = match arm {
                                        0..=3 => case.outcomes[arm].planes[color][pixel],
                                        4 => level as f32,
                                        5 => blurred[color][pixel],
                                        6 => case.outcomes[3].planes[color][pixel + 1],
                                        _ => {
                                            if color == 2 {
                                                blurred[color][pixel]
                                            } else {
                                                case.outcomes[3].planes[color][pixel]
                                            }
                                        }
                                    };
                                    let a = f64::from(value);
                                    let b = f64::from(case.outcomes[state].planes[color][pixel]);
                                    let r = f64::from(case.references[state][color][pixel]);
                                    let t = f64::from(case.truths[state][color][pixel]);
                                    risk += (a - r).powi(2) - (b - r).powi(2);
                                    true_delta += (a - t).powi(2) - (b - t).powi(2);
                                    mse += (a - t).powi(2);
                                    single_mse += (b - t).powi(2);
                                    reference_bias += r - t;
                                    mean_error += a - t;
                                    transfer += (a - level) * (t - level);
                                    transfer_den += (t - level).powi(2);
                                    n += 1;
                                }
                                let scale = n.max(1) as f64;
                                rows.push(json!({"mode":mode,"base":base,"seed":seed,"original_level_dn":level,"state":state,"color":color,"arm":(["singleM3","singleM4","equal","precision","constant","blur","shift","B-only-blur"][arm]),"fixed_pixels":n,"reference_risk_delta_vs_own_single":risk/scale,"known_truth_risk_delta_vs_own_single":true_delta/scale,"truth_mse":mse/scale,"own_single_truth_mse":single_mse/scale,"reference_mean_bias_dn":reference_bias/scale,"output_mean_error_dn":mean_error/scale,"known_signal_projection":if transfer_den>0.{json!(transfer/transfer_den)}else{Value::Null}}));
                            }
                        }
                    }
                    diagnostic_rows.push(json!({"base":base,"seed":seed,"level":level,"qualification":case.qualification,"outcomes":case.outcomes.iter().enumerate().map(|(i,v)|json!({"arm":i,"diagnostics":v.diagnostics})).collect::<Vec<_>>()}));
                }
            }
        }
        let mut required_pass = true;
        if mode == "flat" {
            for level in [0., 20., 200., 1200., 2500.] {
                for color in 0..4 {
                    let selected: Vec<_> = rows
                        .iter()
                        .filter(|r| {
                            r["original_level_dn"] == level
                                && r["color"] == color
                                && r["arm"] == "equal"
                                && r["fixed_pixels"].as_u64().unwrap() > 0
                        })
                        .collect();
                    ensure!(!selected.is_empty(), "flat producer has no qualification");
                    let a: f64 = selected
                        .iter()
                        .map(|r| r["truth_mse"].as_f64().unwrap())
                        .sum();
                    let b: f64 = selected
                        .iter()
                        .map(|r| r["own_single_truth_mse"].as_f64().unwrap())
                        .sum();
                    required_pass &= a / b <= 0.80;
                    summaries.push(json!({"mode":mode,"level":level,"color":color,"equal_to_single_truth_mse_ratio":a/b,"bar":0.80,"scope":"Finite planted acquisition noise, actual nonlinear core and Q/V masks; not camera calibration."}));
                }
            }
        }
        write(
            &out.join(format!("{mode}.json")),
            &json!({"rows":rows,"diagnostics":diagnostic_rows,"required_pass":required_pass}),
        )?;
        println!(
            "{mode}: {}component-state-arm rows, requiredflatcontrol {required_pass}",
            rows.len()
        );
        ensure!(
            required_pass,
            "actualcore flat variance control failed; retain outputs"
        );
    }
    write(
        &out.join("report.json"),
        &json!({"protocol_sha256":sha(&fs::read(out.join("protocol-frozen.json"))?),"passed":true,"summaries":summaries,"scope":"Synthetic actual-core producer control. All component/state/seed rows retained, reference-model bias reported against knowntruth. No actual R/M photons/cache reads; no fullphoto noise claim."}),
    )?;
    Ok(())
}
