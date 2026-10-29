//! Execute the actual proposal generator on frozen metadata, before image arms.
pub use strehl_cli::session_align;
#[path="../../../../crates/strehl-cli/src/session-repeat-proposals.rs"]
mod proposals;
use anyhow::{Context,Result,ensure};
use serde_json::{Value,json};
use sha2::{Digest,Sha256};
use std::{collections::BTreeMap,path::Path};
fn sha(p:&Path)->Result<String> {Ok(Sha256::digest(std::fs::read(p)?).iter().map(|b|format!("{b:02x}")).collect())}
fn read(p:&Path)->Result<Value>{Ok(serde_json::from_slice(&std::fs::read(p)?)?)}
fn main()->Result<()> {
    let args:Vec<_>=std::env::args().collect();ensure!(args.len()==5,"alignment render-directory python-proxy output");
    let alignment=Path::new(&args[1]);let render=Path::new(&args[2]);let python=Path::new(&args[3]);let out=Path::new(&args[4]);
    ensure!(!out.exists(),"output exists");
    let a=read(alignment)?;let ids=read(&render.join("source-identities.json"))?;
    let session=read(&render.join("session.json"))?;let reference=read(python)?;
    ensure!(reference["alignment_sha256"]==sha(alignment)?,"proxy alignment differs");
    let report:session_align::SessionAlignmentReport=serde_json::from_value(a["report"].clone())?;
    let mut scales=BTreeMap::new();
    for line in a["warpmap"].as_str().context("map")?.lines() {
        let p:Vec<_>=line.split_whitespace().collect();
        if p.len()>=6 && p[1]=="placed" && p[0].parse::<usize>().is_ok() {
            let r=f64::from_bits(u64::from_str_radix(p[2],16)?);
            let i=f64::from_bits(u64::from_str_radix(p[3],16)?);
            scales.insert(p[0].parse::<usize>()?,r.hypot(i).ln());
        }
    }
    let frames=session["frames"].as_array().context("frames")?;
    let mut sources=Vec::new();
    for (&index,&log_scale) in &scales {
        sources.push(proposals::Source{index,pass:frames[index]["pass_index"].as_u64().context("pass")? as usize,
            sha256:ids[index]["sha256"].as_str().context("identity")?.to_owned(),log_scale});
    }
    let old=report.focus_candidates.iter().filter_map(|p|p.allowed_log_scale_gap).fold(0_f64,f64::max);
    let plan=proposals::plan(&sources,&report.edges,old,proposals::RESERVATION_BYTES)?;
    let mut comparison=Vec::new();
    for r in &plan.sources {
        let expected=reference["sources"].as_array().context("reference sources")?.iter()
            .find(|v|v["global_index"].as_u64()==Some(r.source.index as u64)).context("reference source")?;
        let observed=r.uncertainty_proxy.context("missing actual proxy")?;
        let oracle=expected["proxy"].as_f64().context("missing independent proxy")?;
        // Independent libm hypot/log and decimal readers need not be bit-identical.
        // Bound absolute arithmetic error at128 double epsilons; every discrete
        // nomination and integer cost below must still agree EXACTLY.
        ensure!((observed-oracle).abs()<=128.*f64::EPSILON,
            "independent proxy mismatch at {}: {observed:.18e} versus {oracle:.18e}",r.source.index);
        comparison.push(json!({"index":r.source.index,"actual":observed,"independent":oracle,
            "difference":observed-oracle}));
    }
    for p in &plan.proposals {
        let expected=reference["nominations"].as_array().context("reference proposals")?.iter()
            .find(|r|r["i"].as_u64()==Some(p.sources[0] as u64) && r["j"].as_u64()==Some(p.sources[1] as u64)).context("reference pair")?;
        ensure!(expected["nomination_only"].as_bool()==Some(p.nominated)
            && expected["cost_fixedpoint"].as_u64()==p.cost.map(u64::from),"discrete nomination/cost mismatch");
    }
    let result=json!({"schema":"strehl.repeat-proposal-metadata-check.v1","plan":plan,
        "inputs":{"alignment":sha(alignment)?,"identities":sha(&render.join("source-identities.json"))?,
            "session":sha(&render.join("session.json"))?,"independent_python_proxy":sha(python)?},
        "independent_proxy_comparison":comparison,"independent_discrete_nomination_cost_exact":true,
        "original_reads":0,"raw_decodes":0,"command":args});
    std::fs::write(out,format!("{}\n",serde_json::to_string_pretty(&result)?))?;
    println!("{}",json!({"matched_pairs":result["plan"]["matched_pairs"],"groups":result["plan"]["groups"],"total_cost":result["plan"]["total_cost"]}));
    Ok(())
}
