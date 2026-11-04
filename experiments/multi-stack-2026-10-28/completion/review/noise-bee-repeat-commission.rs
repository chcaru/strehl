//! Synthetic original-u16 commissioning at current bee placements; no CFA cache reads.
#![allow(dead_code)]
#[path = "real-noise-consumer-warped.rs"]
mod context;
#[path = "noise-bee-repeat-gate.rs"]
mod model;
#[path = "real-noise-consumer-structure-operator.rs"]
mod operator;
#[path = "noise-bee-repeat-model.rs"]
mod temporal;
use anyhow::{Context, Result, ensure};
use rayon::prelude::*;
use serde_json::{Value, json};
use sha2::{Digest, Sha256};
use std::{collections::BTreeMap, fs, io::Write, path::Path};
use strehl_cli::{
    session_reconstruction_sampling::RegionSampler, session_sampling::SamplingDomain,
};
use strehl_core::{CfaPlane, align::Resampler};
fn sha(bytes: &[u8]) -> String {
    Sha256::digest(bytes)
        .iter()
        .map(|x| format!("{x:02x}"))
        .collect()
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
fn percentile(values: &[f64], fraction: f64) -> f64 {
    let mut x = values.to_vec();
    x.sort_by(f64::total_cmp);
    x[((fraction * x.len() as f64).ceil() as usize)
        .saturating_sub(1)
        .min(x.len() - 1)]
}
fn stats(values: &[f64]) -> Value {
    json!({"count":values.len(),"mean":values.iter().sum::<f64>()/values.len() as f64,"median":percentile(values,0.5),"p95":percentile(values,0.95),"p99":percentile(values,0.99),"maximum":percentile(values,1.)})
}
fn main() -> Result<()> {
    let args: Vec<_> = std::env::args().collect();
    ensure!(
        args.len() == 5 || args.len() == 6,
        "RENDER FROZEN_PROTOCOL NEW_OUT train|held [TRAIN_REPORT]"
    );
    let training = args[4] == "train";
    ensure!(training || args[4] == "held", "mode");
    let protocol_bytes = fs::read(&args[2])?;
    ensure!(
        sha(&protocol_bytes) == "f2fc47d451314ef0bf4a188cdf52d147d17de4fd72b947f58069017f631fcae4",
        "frozen bee protocol"
    );
    let protocol: Value = serde_json::from_slice(&protocol_bytes)?;
    let out = Path::new(&args[3]);
    fs::create_dir(out)?;
    let c = context::context(Path::new(&args[1]))?;
    ensure!(
        c.map.resampler() == Resampler::CatmullRom,
        "linear Catmull required"
    );
    let session: Value =
        serde_json::from_slice(&fs::read(Path::new(&args[1]).join("session.json"))?)?;
    let mut indices = [usize::MAX; 32];
    for frame in session["frames"].as_array().context("frames")? {
        let path = Path::new(frame["path"].as_str().context("path")?);
        let ordinal = path
            .file_stem()
            .context("stem")?
            .to_str()
            .context("UTF8")?
            .trim_start_matches("DSC")
            .parse::<usize>()?
            .checked_sub(328)
            .context("ordinal")?;
        ensure!(
            ordinal < 32 && indices[ordinal] == usize::MAX,
            "unique frozen ordinal"
        );
        indices[ordinal] = frame["global_index"].as_u64().context("global index")? as usize;
    }
    ensure!(indices.iter().all(|x| *x != usize::MAX), "all32originals");
    let cutoff = if training {
        1e9
    } else {
        let p = Path::new(args.get(5).context("training report")?);
        let r: Value = serde_json::from_slice(&fs::read(p)?)?;
        let frozen_path = p
            .parent()
            .context("training report parent")?
            .join("protocol-frozen.json");
        let frozen_bytes = fs::read(frozen_path)?;
        let trained: Value = serde_json::from_slice(&frozen_bytes)?;
        ensure!(
            r["phase"] == "train"
                && r["commission_passed"] == true
                && r["input_protocol_sha256"] == sha(&protocol_bytes),
            "training gate binding"
        );
        ensure!(
            r["protocol_sha256"] == sha(&frozen_bytes)
                && trained["bindings"] == c.bindings
                && trained["source_sha256"]
                    == sha(include_bytes!("noise-bee-repeat-commission.rs"))
                && trained["gate_sha256"] == sha(include_bytes!("noise-bee-repeat-gate.rs"))
                && trained["temporal_sha256"] == sha(include_bytes!("noise-bee-repeat-model.rs"))
                && trained["operator_sha256"]
                    == sha(include_bytes!("real-noise-consumer-structure-operator.rs")),
            "training code/geometry/noise binding changed"
        );
        r["cutoff"].as_f64().context("cutoff")?
    };
    let seeds = if training { 96u64..112 } else { 112u64..128 };
    let modes: Vec<_> = if training {
        vec!["flat"]
    } else {
        vec![
            "flat",
            "linear",
            "quadratic",
            "focus",
            "shift",
            "step",
            "clipped",
        ]
    };
    let full = c.map.geometry();
    let witnesses: Vec<_> = protocol["witnesses"]
        .as_array()
        .unwrap()
        .iter()
        .filter(|v| v["id"] == "eye-facets" || v["id"] == "dark-background")
        .collect();
    ensure!(witnesses.len() == 2, "two commissioned domains");
    let pool = rayon::ThreadPoolBuilder::new().num_threads(4).build()?;
    let frozen = json!({"schema":"strehl.bee-two-state-commission.v1","command":args,"input_protocol_sha256":sha(&protocol_bytes),"phase":if training{"train"}else{"held"},"seeds":[seeds.start,seeds.end-1],"bindings":c.bindings,"cutoff_rule":"max(1.10, nearest-rank empirical99thpercentile); maximum1.50; no retry","mean_energy_range":[0.90,1.10],"stratum_null_acceptance_minimum":0.95,"source_sha256":sha(include_bytes!("noise-bee-repeat-commission.rs")),"gate_sha256":sha(include_bytes!("noise-bee-repeat-gate.rs")),"temporal_sha256":sha(include_bytes!("noise-bee-repeat-model.rs")),"operator_sha256":sha(include_bytes!("real-noise-consumer-structure-operator.rs")),"raw_decodes":0,"cache_reads":0,"workers":4});
    write(&out.join("protocol-frozen.json"), &frozen)?;
    let mut all_rows = Vec::new();
    let mut summaries = Vec::new();
    let mut success = true;
    for mode in modes {
        let mut jobs = Vec::new();
        for window in 0..4 {
            for domain in 0..2 {
                for level in [1200., 200.] {
                    for seed in seeds.clone() {
                        jobs.push((window, domain, level, seed));
                    }
                }
            }
        }
        let rows:Vec<Value>=pool.install(||jobs.par_iter().map(|&(window,di,level,seed)|->Result<Value> {
            let w=&protocol["windows"][window];let base=w["base"].as_u64().unwrap() as usize;
            let times=&protocol["timestamps_unix"].as_array().unwrap();let first=times[base].as_f64().unwrap();
            let t=|o:usize|times[base+o].as_f64().unwrap()-first;
            let timestamps=temporal::Times{q:[t(0),t(7)],v:[t(1),t(6)],r:[t(2),t(5)],m:[t(3),t(4)]};
            let f=witnesses[di]["active_fraction_center"].as_array().unwrap();
            let domain=SamplingDomain{full,x:(f[0].as_f64().unwrap()*full.width as f64).floor() as usize-64,y:(f[1].as_f64().unwrap()*full.height as f64).floor() as usize-64,width:128,height:128};
            let mut gate=model::Gate::new(timestamps)?;let mut sampler=RegionSampler::new(domain,8<<20)?;
            for (is_q,offsets) in [(true,[0usize,7]),(false,[1usize,6])] {for (j,offset) in offsets.into_iter().enumerate() {
                let index=indices[base+offset];let pass=if index<16{0}else{1};
                let placement=c.map.warps()[index].placed().context("placed")?;
                let normalized=t(offset)/t(7);
                let brightness=match mode {"linear"=>1.+0.12*normalized,"quadratic"=>1.+0.40*normalized*normalized,_=>1.};
                let plant_mode=match mode {"linear"|"quadratic"=>"stationary",_=>mode};
                let raw=operator::plant(domain,placement,c.profiles[pass],&c.noise[pass],(1200./level/brightness) as f32,plant_mode,(normalized*8.) as f32,seed*53139+(base+offset) as u64*7919)?;
                let sample=sampler.gather(&raw,c.noise[pass].plane(CfaPlane::R).levels,placement,c.profiles[pass],c.map.resampler())?;
                let beta=operator::beta(domain,placement,c.profiles[pass]);
                if is_q {gate.q(j,&sample.planes,&sample.support,&beta)?;} else {gate.v(j,&sample.planes,&sample.support,&beta)?;}
            }}
            ensure!(format!("{:?}",c.noise[0])==format!("{:?}",c.noise[1]),"equal camera noise for frozen burst");
            Ok(json!({"mode":mode,"window":window,"domain":witnesses[di]["id"],"original_level_dn":level,"seed":seed,"tiles":gate.finish(&c.noise[0],cutoff)?}))
        }).collect::<Result<Vec<_>>>())?;
        let mut strata: BTreeMap<String, Vec<(f64, bool)>> = BTreeMap::new();
        for row in &rows {
            for tile in row["tiles"].as_array().unwrap() {
                let key = format!(
                    "w{}-{}-level{}-c{}",
                    row["window"],
                    row["domain"].as_str().unwrap(),
                    row["original_level_dn"],
                    tile["color"]
                );
                strata.entry(key).or_default().push((
                    tile["energy"].as_f64().unwrap(),
                    tile["accepted"].as_bool().unwrap(),
                ));
            }
        }
        let mut summary = Vec::new();
        for (key, values) in strata {
            let energy: Vec<_> = values.iter().map(|v| v.0).collect();
            let accepted = values.iter().filter(|v| v.1).count();
            let mean = energy.iter().sum::<f64>() / energy.len() as f64;
            if mode == "flat" {
                success &= (0.90..=1.10).contains(&mean);
            }
            if !training && (mode == "flat" || mode == "linear") {
                success &= accepted * 100 >= 95 * values.len();
            }
            summary.push(json!({"stratum":key,"energy":stats(&energy),"accepted":accepted,"total":values.len()}));
        }
        write(&out.join(format!("{mode}.json")), &json!({"rows":rows}))?;
        println!(
            "{mode}: {} cases; current required controls {success}",
            rows.len()
        );
        summaries.push(json!({"mode":mode,"strata":summary}));
        all_rows.extend(rows);
    }
    let learned = if training {
        let energies: Vec<_> = all_rows
            .iter()
            .flat_map(|r| r["tiles"].as_array().unwrap())
            .map(|t| t["energy"].as_f64().unwrap())
            .collect();
        let value = percentile(&energies, 0.99).max(1.10);
        success &= value <= 1.50;
        value
    } else {
        cutoff
    };
    let report = json!({"schema":"strehl.bee-two-state-commission.v1","phase":if training{"train"}else{"held"},"input_protocol_sha256":sha(&protocol_bytes),"protocol_sha256":sha(&fs::read(out.join("protocol-frozen.json"))?),"cutoff":learned,"commission_passed":success,"summaries":summaries,"scope":"Empirical controlled operating point, not calibrated real false-positive probability. Original-u16 synthetic photons only; no actual assay Q/V/R/M cache read."});
    write(&out.join("report.json"), &report)?;
    ensure!(
        success,
        "frozen commission failed; retain report, diagnose, no threshold retry"
    );
    Ok(())
}
