//! Real Q/V-only census. No R, W or M original signal is loaded.
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
    session_input::{ResolvedSession, SourceIdentity},
    session_reconstruction_sampling::RegionSampler,
    session_sampling::SamplingDomain,
};
use strehl_core::align::Resampler;
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
fn main() -> Result<()> {
    let args: Vec<_> = std::env::args().collect();
    ensure!(args.len() == 3, "FROZEN_INSECT_PROTOCOL NEW_OUT");
    let input = Path::new(&args[1]);
    let out = Path::new(&args[2]);
    fs::create_dir(out)?;
    let prior = read(input)?;
    ensure!(
        prior["schema"] == "strehl.real-noise-insect-qualification-protocol.v1",
        "wrong prior protocol"
    );
    let render = Path::new(prior["render"].as_str().context("render")?);
    let c = context::context(render)?;
    ensure!(
        c.map.resampler() == Resampler::CatmullRom,
        "exact tap norm requires linear CatmullRom"
    );
    ensure!(
        prior["alignment_sha256"] == c.bindings["alignment_sha256"],
        "frozen geometry differs"
    );
    ensure!(
        prior["source_identities_sha256"].as_str()
            == Some(sha(&fs::read(render.join("source-identities.json"))?).as_str()),
        "frozen source census differs"
    );
    let session: ResolvedSession = serde_json::from_value(read(&render.join("session.json"))?)?;
    let ids: Vec<SourceIdentity> =
        serde_json::from_value(read(&render.join("source-identities.json"))?)?;
    ensure!(
        ids.len() == 598 && session.passes.len() == 2,
        "wrong source count"
    );
    let domains: Vec<_> = prior["rois"]
        .as_array()
        .context("rois")?
        .iter()
        .map(|r| SamplingDomain {
            full: c.map.geometry(),
            x: r["domain_quad"][0].as_u64().unwrap() as usize,
            y: r["domain_quad"][1].as_u64().unwrap() as usize,
            width: 128,
            height: 128,
        })
        .collect();
    ensure!(domains.len() == 9, "frozen nine witnesses required");
    let roles = [
        ("Q", vec![0isize, 4, 8]),
        ("V", vec![1, 5, 9]),
        ("R", vec![-2, 2, 6, 10]),
        ("W", vec![-1, 11]),
        ("M", vec![3, 7]),
    ];
    let mut census = Vec::new();
    let mut all = BTreeSet::new();
    let mut allowed = BTreeSet::new();
    for base in [36usize, 76, 116, 156, 196, 236] {
        for pass in 0..2 {
            for (role, offsets) in &roles {
                for offset in offsets {
                    let index = (base as isize + offset) as usize + 299 * pass;
                    ensure!(all.insert(index), "roles overlap");
                    ensure!(
                        session.frames[index].pass_index == pass,
                        "source/pass mismatch"
                    );
                    if *role == "Q" || *role == "V" {
                        allowed.insert(index);
                    }
                    census.push(json!({"base":base,"pass":pass,"role":role,"offset":offset,"index":index,"source":ids[index]}));
                }
            }
        }
    }
    write(
        &out.join("protocol-frozen.json"),
        &json!({"schema":"strehl.structure-observer-real-census-protocol.v1","command":args,"prior_nomination":prior,"prior_nomination_sha256":sha(&fs::read(input)?),"roles":census,"read_roles":["Q","V"],"r_w_m_loaded":false,"bindings":c.bindings,"historical_binding":historical_cache::binding()?,"cutoff":model::LIMIT,"variance_policy":"Q-only local-constant signal-dependent plug-in, exact CatmullRom tap norm, full3x3 temporal covariance; same-photon denominator approximation commissioned synthetically. Not a chi-square confidence or absolute model-error bound.","crosspass_policy":"Per-pass Q/V consistency intersection only. Does not certify identical cross-pass focus/appearance or authorize using their mean as true target.","source_hashes":{"driver":sha(include_bytes!("real-noise-consumer-structure-census.rs")),"model":sha(include_bytes!("real-noise-consumer-structure-model.rs")),"operator":sha(include_bytes!("real-noise-consumer-structure-operator.rs")),"context":sha(include_bytes!("real-noise-consumer-warped.rs")),"historical_reader":sha(include_bytes!("../sr/historical-cache.rs"))},"workers":4,"memory_limit_bytes":2usize<<30}),
    )?;
    let pool = rayon::ThreadPoolBuilder::new().num_threads(4).build()?;
    let mut cache = historical_cache::HistoricalCache::new(
        Path::new(prior["cache"].as_str().context("cache")?),
        &ids,
        128 << 20,
        c.map.geometry(),
    )?;
    let mut results = Vec::new();
    let mut loaded = Vec::new();
    for base in [36usize, 76, 116, 156, 196, 236] {
        let mut passes = Vec::new();
        let mut q_mean_passes = Vec::new();
        for pass in 0..2 {
            let mut gates: Vec<_> = (0..9).map(|_| model::Gate::new()).collect();
            let mut samplers: Vec<_> = domains
                .iter()
                .map(|&d| RegionSampler::new(d, 8 << 20))
                .collect::<Result<_>>()?;
            let mut means = vec![vec![[[0f64; 3]; 4]; 9]; 9];
            pool.install(||->Result<()>{for(role,offsets)in [("Q",[0,4,8]),("V",[1,5,9])]{for(j,offset)in offsets.into_iter().enumerate(){let index=base+offset+299*pass;ensure!(allowed.contains(&index),"attempted read outside Q/V");let original=cache.load(&ids[index])?.context("historical source absent; no decoder fallback")?;let t=c.map.warps()[index].placed().context("unplaced Q/V source")?;
                for(ri,&d)in domains.iter().enumerate(){let s=samplers[ri].gather(original.as_ref(),original.levels(),t,c.profiles[pass],c.map.resampler())?;let beta=operator::beta(d,t,c.profiles[pass]);if role=="Q"{gates[ri].q(j,&s.planes,&s.support,&beta,c.gains[pass])?;for(ty,y0)in[16,48,80].into_iter().enumerate(){for(tx,x0)in[16,48,80].into_iter().enumerate(){for color in 0..4{let mut sum=0.;for y in y0..y0+32{for x in x0..x0+32{sum+=f64::from(s.planes[color][y*128+x])*f64::from(c.gains[pass]);}}means[ri][ty*3+tx][color][j]=sum/1024.;}}}}else{gates[ri].v(j,&s.planes,&s.support,&beta,c.gains[pass])?;}}
                loaded.push(json!({"base":base,"pass":pass,"role":role,"index":index,"source":ids[index],"cache_path":cache.path(&ids[index])?}));
            }}Ok(())})?;
            passes.push(
                gates
                    .iter()
                    .map(|q| q.finish(&c.noise[pass], c.gains[pass]))
                    .collect::<Result<Vec<_>>>()?,
            );
            q_mean_passes.push(means);
        }
        let mut regions = Vec::new();
        let mut counts = [0usize; 4];
        let mut all_cfa = 0;
        for ri in 0..9 {
            let mut tiles = Vec::new();
            for tile in 0..9 {
                let mut colors = Vec::new();
                let mut all = true;
                for color in 0..4 {
                    let a = &passes[0][ri][tile * 4 + color];
                    let b = &passes[1][ri][tile * 4 + color];
                    let accepted = a["accepted"] == true && b["accepted"] == true;
                    counts[color] += usize::from(accepted);
                    all &= accepted;
                    let predicted: Vec<_> = (0..2)
                        .map(|p| {
                            [3., 7.].map(|t| {
                                model::q_weights(t)
                                    .iter()
                                    .zip(q_mean_passes[p][ri][tile][color])
                                    .map(|(w, v)| w * v)
                                    .sum::<f64>()
                            })
                        })
                        .collect();
                    colors.push(json!({"color":color,"passes":[a,b],"accepted_qv_both_passes":accepted,"q_only_predicted_block_mean_dn_at_m_states_by_pass":predicted,"crosspass_not_qualified":true}));
                }
                all_cfa += usize::from(all);
                tiles.push(json!({"tile":tile,"colors":colors,"all_cfa_qv":all}));
            }
            regions.push(json!({"name":prior["rois"][ri]["name"],"domain_quad":prior["rois"][ri]["domain_quad"],"tiles":tiles}));
        }
        println!("base {base}: Q/V CFA {counts:?}, allCFA {all_cfa}/81");
        results
            .push(json!({"base":base,"regions":regions,"counts":counts,"all_cfa_blocks":all_cfa}));
    }
    for index in &allowed {
        ids[*index].check_unchanged()?;
    }
    ensure!(loaded.len() == 72, "Q/V loaded census differs");
    write(
        &out.join("qualification.json"),
        &json!({"schema":"strehl.structure-observer-real-qv.v1","protocol_sha256":sha(&fs::read(out.join("protocol-frozen.json"))?),"windows":results,"loaded_sources":loaded,"cache_disk_hits":cache.stats().disk_hits,"raw_decodes":0,"r_w_m_loaded":false,"warning":"This is temporal-model consistency, not stationarity, unbiased true-image risk or noise gain. Low-DN cubic/focus misses remain a known instrument limit."}),
    )?;
    Ok(())
}
