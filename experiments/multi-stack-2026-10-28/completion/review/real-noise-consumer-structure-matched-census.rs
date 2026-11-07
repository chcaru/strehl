//! Matched-focus nomination Q/V only, separate from the earlier same-ordinal census.
#![allow(dead_code)]
#[path = "real-noise-consumer-warped.rs"]
mod context;
#[path = "../sr/historical-cache.rs"]
mod historical_cache;
#[path = "real-noise-consumer-structure-model.rs"]
mod model;
#[path = "real-noise-consumer-structure-operator.rs"]
mod operator;
use anyhow::{Context, Result, ensure};
use serde_json::{Value, json};
use sha2::{Digest, Sha256};
use std::{collections::BTreeSet, fs, io::Write, path::Path};
use strehl_cli::{
    session_input::SourceIdentity, session_reconstruction_sampling::RegionSampler,
    session_sampling::SamplingDomain,
};
const N: usize = 128 * 128;
type Planes = [Vec<f64>; 4];
fn sha(b: &[u8]) -> String {
    Sha256::digest(b)
        .iter()
        .map(|v| format!("{v:02x}"))
        .collect()
}
fn read(p: &Path) -> Result<Value> {
    Ok(serde_json::from_slice(&fs::read(p)?)?)
}
fn write(p: &Path, v: &Value) -> Result<()> {
    let mut f = fs::OpenOptions::new()
        .write(true)
        .create_new(true)
        .open(p)?;
    serde_json::to_writer_pretty(&mut f, v)?;
    f.write_all(b"\n")?;
    f.sync_all()?;
    Ok(())
}
fn fields() -> [Planes; 2] {
    std::array::from_fn(|_| std::array::from_fn(|_| vec![0.; N]))
}
fn main() -> Result<()> {
    let args: Vec<_> = std::env::args().collect();
    ensure!(args.len() == 3, "FROZEN_MATCHED_PROTOCOL NEW_OUT");
    let input = Path::new(&args[1]);
    let out = Path::new(&args[2]);
    fs::create_dir(out)?;
    let protocol = read(input)?;
    ensure!(
        protocol["schema"] == "strehl.structure-observer-focus-matched-protocol.v1",
        "wrong protocol"
    );
    let render = Path::new(protocol["source_render"].as_str().context("render")?);
    ensure!(
        protocol["sources_sha256"].as_str()
            == Some(sha(&fs::read(render.join("source-identities.json"))?).as_str()),
        "source binding"
    );
    ensure!(
        protocol["alignment_sha256"].as_str()
            == Some(sha(&fs::read(render.join("alignment.json"))?).as_str()),
        "geometry binding"
    );
    let c = context::context(render)?;
    let ids: Vec<SourceIdentity> =
        serde_json::from_value(read(&render.join("source-identities.json"))?)?;
    let q = &protocol["domain_quad"];
    let d = SamplingDomain {
        full: c.map.geometry(),
        x: q[0].as_u64().unwrap() as usize,
        y: q[1].as_u64().unwrap() as usize,
        width: q[2].as_u64().unwrap() as usize,
        height: q[3].as_u64().unwrap() as usize,
    };
    ensure!(d.width == 128 && d.height == 128, "frozen observer size");
    d.validate()?;
    let mut allowed = BTreeSet::new();
    let mut all = BTreeSet::new();
    for role in protocol["roles"].as_array().context("roles")? {
        let i = role["global_index"].as_u64().unwrap() as usize;
        ensure!(all.insert(i), "overlapping roles");
        ensure!(
            serde_json::to_value(&ids[i])? == role["source"],
            "role source identity differs"
        );
        if role["role"] == "Q" || role["role"] == "V" {
            allowed.insert(i);
        }
    }
    ensure!(
        allowed.len() == 12 && all.len() == 28,
        "role census differs"
    );
    let seal =
        Path::new("experiments/multi-stack-2026-10-28/completion/sr/focus-census-01-seal.json");
    ensure!(
        protocol["focus_seal_sha256"].as_str() == Some(sha(&fs::read(seal)?).as_str()),
        "focus nomination seal changed"
    );
    write(
        &out.join("protocol-frozen.json"),
        &json!({"nomination":protocol,"nomination_sha256":sha(&fs::read(input)?),"command":args,"bindings":c.bindings,"historical_binding":historical_cache::binding()?,"loaded_roles":["Q","V"],"r_w_m_loaded":false,"workers":4,"memory_limit_bytes":2usize<<30,"source_hashes":{"driver":sha(include_bytes!("real-noise-consumer-structure-matched-census.rs")),"model":sha(include_bytes!("real-noise-consumer-structure-model.rs")),"operator":sha(include_bytes!("real-noise-consumer-structure-operator.rs")),"historical":sha(include_bytes!("../sr/historical-cache.rs"))}}),
    )?;
    let pool = rayon::ThreadPoolBuilder::new().num_threads(4).build()?;
    let mut cache = historical_cache::HistoricalCache::new(
        Path::new(protocol["cache"].as_str().context("cache")?),
        &ids,
        128 << 20,
        c.map.geometry(),
    )?;
    let mut passes = Vec::new();
    let mut prediction = Vec::new();
    let mut loaded = Vec::new();
    for pass in 0..2 {
        let mut gate = model::Gate::new();
        let mut predicted = fields();
        let mut sampler = RegionSampler::new(d, 8 << 20)?;
        pool.install(||->Result<()>{for role in ["Q","V"]{let sources:Vec<_>=protocol["roles"].as_array().unwrap().iter().filter(|r|r["role"]==role&&r["pass"]==pass).collect();ensure!(sources.len()==3,"role count");for(j,r)in sources.iter().enumerate(){let i=r["global_index"].as_u64().unwrap()as usize;ensure!(allowed.contains(&i),"attempt outside Q/V");let original=cache.load(&ids[i])?.context("cache missing; decoding forbidden")?;let t=c.map.warps()[i].placed().context("unplaced")?;let sample=sampler.gather(original.as_ref(),original.levels(),t,c.profiles[pass],c.map.resampler())?;let beta=operator::beta(d,t,c.profiles[pass]);if role=="Q"{gate.q(j,&sample.planes,&sample.support,&beta,c.gains[pass])?;for state in 0..2{let weight=model::q_weights([3.,7.][state])[j];for color in 0..4{for p in 0..N{predicted[state][color][p]+=weight*f64::from(sample.planes[color][p])*f64::from(c.gains[pass]);}}}}else{gate.v(j,&sample.planes,&sample.support,&beta,c.gains[pass])?;}loaded.push(json!({"pass":pass,"role":role,"source":ids[i],"global_index":i,"cache_path":cache.path(&ids[i])?}));}}Ok(())})?;
        passes.push(gate.finish(&c.noise[pass], c.gains[pass])?);
        prediction.push(predicted);
    }
    let mut rows = Vec::new();
    let mut accepted = [0usize; 4];
    let mut all_cfa = 0;
    for tile in 0..9 {
        let mut whole = true;
        for color in 0..4 {
            let a = &passes[0][tile * 4 + color];
            let b = &passes[1][tile * 4 + color];
            let qualified = a["accepted"] == true && b["accepted"] == true;
            whole &= qualified;
            accepted[color] += usize::from(qualified);
            let x = a["tile_quad"][0].as_u64().unwrap() as usize;
            let y = a["tile_quad"][1].as_u64().unwrap() as usize;
            let mut diagnostics = Vec::new();
            for state in 0..2 {
                let mut delta = 0.;
                let mut square = 0.;
                let mut means = [0.; 2];
                for yy in y..y + 32 {
                    for xx in x..x + 32 {
                        let p = yy * 128 + xx;
                        let d = prediction[0][state][color][p] - prediction[1][state][color][p];
                        delta += d;
                        square += d * d;
                        for pass in 0..2 {
                            means[pass] += prediction[pass][state][color][p];
                        }
                    }
                }
                diagnostics.push(json!({"state_offset":([3,7][state]),"predicted_means_dn":means.map(|v|v/1024.),"predicted_signed_difference_dn":delta/1024.,"predicted_per_site_difference_rms_dn":(square/1024.).sqrt(),"compatibility_certified":false}));
            }
            rows.push(json!({"tile":tile,"color":color,"passes":[a,b],"accepted_qv_both_passes":qualified,"q_only_crosspass":diagnostics}));
        }
        all_cfa += usize::from(whole);
    }
    for i in &allowed {
        ids[*i].check_unchanged()?;
    }
    ensure!(loaded.len() == 12, "wrong read count");
    println!("matched Q/V components{accepted:?}; allCFA{all_cfa}/9");
    write(
        &out.join("qualification.json"),
        &json!({"schema":"strehl.structure-observer-matched-qv.v1","protocol_sha256":sha(&fs::read(out.join("protocol-frozen.json"))?),"rows":rows,"accepted_components":accepted,"all_cfa_blocks":all_cfa,"loaded_sources":loaded,"cache_disk_hits":cache.stats().disk_hits,"raw_decodes":0,"r_w_m_loaded":false,"scope":"Q/V temporal consistency only. Per-site Q-prediction difference is a diagnostic, with Q noise/temporal-model error; no uncommissioned compatibility mask is applied. R targets stay separate if later authorized."}),
    )?;
    Ok(())
}
