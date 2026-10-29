//! Complete Q/V image qualification controls. No real R/M reads.
#![allow(dead_code)]
#[path = "real-noise-consumer-warped.rs"]
mod context;
#[path = "real-noise-consumer-structure-model.rs"]
mod model;
#[path = "real-noise-consumer-structure-operator.rs"]
mod operator;
use anyhow::{Context, Result, ensure};
use serde_json::{Value, json};
use sha2::{Digest, Sha256};
use std::{fs, io::Write, path::Path};
use strehl_cli::{
    session_reconstruction_sampling::RegionSampler, session_sampling::SamplingDomain,
};
use strehl_core::{CfaPlane, align::Resampler};
fn sha(b: &[u8]) -> String {
    Sha256::digest(b)
        .iter()
        .map(|v| format!("{v:02x}"))
        .collect()
}
fn write(path: &Path, value: &Value) -> Result<()> {
    let mut f = fs::OpenOptions::new()
        .create_new(true)
        .write(true)
        .open(path)?;
    serde_json::to_writer_pretty(&mut f, value)?;
    f.write_all(b"\n")?;
    f.sync_all()?;
    Ok(())
}
fn main() -> Result<()> {
    let args: Vec<_> = std::env::args().collect();
    ensure!(args.len() == 4, "RENDER NEW_OUT flat|all");
    let out = Path::new(&args[2]);
    fs::create_dir(out)?;
    let c = context::context(Path::new(&args[1]))?;
    ensure!(
        c.map.resampler() == Resampler::CatmullRom,
        "observer exact beta requires linear Catmull-Rom"
    );
    let full = c.map.geometry();
    let domain = SamplingDomain {
        full,
        x: full.width / 2 - 64,
        y: full.height / 2 - 64,
        width: 128,
        height: 128,
    };
    let modes: Vec<_> = if args[3] == "flat" {
        vec!["flat"]
    } else {
        vec![
            "flat",
            "quadratic",
            "cubic",
            "focus",
            "step",
            "shift",
            "clipped",
        ]
    };
    let protocol = json!({"schema":"strehl.structure-observer-commission.v1","command":args,"bindings":c.bindings,"q":[0,4,8],"v":[1,5,9],"bases":[36,236],"seeds":[64,65,66,67],"passes":[0,1],"original_signal_dn":[1200,200],"domain_quad":[domain.x,domain.y,128,128],"component_block":32,"energy_cutoff":model::LIMIT,"source_sha256":sha(include_bytes!("real-noise-consumer-structure-warped.rs")),"model_sha256":sha(include_bytes!("real-noise-consumer-structure-model.rs")),"operator_sha256":sha(include_bytes!("real-noise-consumer-structure-operator.rs")),"scope":"Synthetic original u16 through actual RegionSampler at measured curved insect placements. Q-only local-constant signal-dependent variance plug-in, exact tap norm, full temporal covariance; no statistical absolute bound or real quality claim. Four-worker ceiling, no real original loads."});
    write(&out.join("protocol-frozen.json"), &protocol)?;
    let pool = rayon::ThreadPoolBuilder::new().num_threads(4).build()?;
    let mut summaries = Vec::new();
    for mode in modes {
        let mut rows = Vec::new();
        for base in [36usize, 236] {
            for pass in 0..2 {
                for seed in [64u64, 65, 66, 67] {
                    for divisor in [1f32, 6.] {
                        let gain = c.gains[pass] * divisor;
                        let mut gate = model::Gate::new();
                        let mut sampler = RegionSampler::new(domain, 8 << 20)?;
                        pool.install(|| -> Result<()> {
                            for (role, ordinals) in [("Q", [0usize, 4, 8]), ("V", [1usize, 5, 9])] {
                                for (j, offset) in ordinals.into_iter().enumerate() {
                                    let index = base + offset + 299 * pass;
                                    let t = c.map.warps()[index]
                                        .placed()
                                        .context("unplaced original")?;
                                    let raw = operator::plant(
                                        domain,
                                        t,
                                        c.profiles[pass],
                                        &c.noise[pass],
                                        gain,
                                        mode,
                                        offset as f32,
                                        seed * 53139 + index as u64 * 7919,
                                    )?;
                                    let sample = sampler.gather(
                                        &raw,
                                        c.noise[pass].plane(CfaPlane::R).levels,
                                        t,
                                        c.profiles[pass],
                                        c.map.resampler(),
                                    )?;
                                    let beta = operator::beta(domain, t, c.profiles[pass]);
                                    if role == "Q" {
                                        gate.q(j, &sample.planes, &sample.support, &beta, gain)?;
                                    } else {
                                        gate.v(j, &sample.planes, &sample.support, &beta, gain)?;
                                    }
                                }
                            }
                            Ok(())
                        })?;
                        let tiles = gate.finish(&c.noise[pass], gain)?;
                        let accepted = tiles.iter().filter(|v| v["accepted"] == true).count();
                        rows.push(json!({"mode":mode,"base":base,"pass":pass,"seed":seed,"mean_original_dn":1200./gain,"divisor":divisor,"accepted":accepted,"total":tiles.len(),"tiles":tiles,"sampler_peak_bytes":sampler.peak_reserved_bytes()}));
                    }
                }
            }
        }
        let accepted: usize = rows
            .iter()
            .map(|v| v["accepted"].as_u64().unwrap() as usize)
            .sum();
        let total = rows.len() * 36;
        let mut by_level = Vec::new();
        for level in [1., 6.] {
            let selected: Vec<_> = rows.iter().filter(|r| r["divisor"] == level).collect();
            let n = selected.len() * 36;
            let a: usize = selected
                .iter()
                .map(|r| r["accepted"].as_u64().unwrap() as usize)
                .sum();
            let mean_energy = selected
                .iter()
                .flat_map(|r| r["tiles"].as_array().unwrap())
                .map(|t| t["energy"].as_f64().unwrap())
                .sum::<f64>()
                / n as f64;
            by_level.push(
                json!({"divisor":level,"accepted":a,"total":n,"mean_whitened_energy":mean_energy}),
            );
        }
        println!("{mode}: {accepted}/{total} {by_level:?}");
        write(&out.join(format!("{mode}.json")), &json!({"rows":rows}))?;
        summaries.push(json!({"mode":mode,"accepted":accepted,"total":total,"by_level":by_level}));
        // Null/in-model failure is fatal. Adverse acceptance is preserved and
        // reported as measured instrument power, never fixed by changing LIMIT.
        if mode == "flat" || mode == "quadratic" {
            ensure!(
                accepted * 100 >= 95 * total,
                "known in-model commission refused: {mode}"
            );
        }
    }
    write(
        &out.join("report.json"),
        &json!({"protocol_sha256":sha(&fs::read(out.join("protocol-frozen.json"))?),"summaries":summaries,"raw_decodes":0,"cache_reads":0,"workers":4,"limitations":["Conditional local-constant variance plug-in; spatial block energy has no iid-pixel confidence interval.","Adverse accepted cases remain visible. Passing known signals is not validation of real temporal focus law.","No measurement or independent R risk-reference acquisition read."]}),
    )?;
    Ok(())
}
