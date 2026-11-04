//! Pre-measurement insect qualification, streamed over all frozen witnesses.
#![allow(dead_code)]
#[path = "real-noise-consumer-gate.rs"]
mod gate;
#[path = "../sr/historical-cache.rs"]
mod historical_cache;
#[path = "real-noise-consumer-warped.rs"]
mod warped;
use anyhow::{Context, Result, ensure};
use serde_json::{Value, json};
use sha2::{Digest, Sha256};
use std::{fs, io::Write, path::Path};
use strehl_cli::{
    session_input::{ResolvedSession, SourceIdentity},
    session_reconstruction_sampling::RegionSampler,
    session_sampling::SamplingDomain,
};
use strehl_core::CfaPlane;
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
fn selected(window: &Value, pass: usize) -> Vec<usize> {
    window["guides_local"]
        .as_array()
        .unwrap()
        .iter()
        .chain(window["validation_local"].as_array().unwrap())
        .map(|v| v.as_u64().unwrap() as usize + 299 * pass)
        .collect()
}
fn commission(
    c: &warped::Contexts,
    protocol: &Value,
    domains: &[SamplingDomain],
    out: &Path,
    pool: &rayon::ThreadPool,
) -> Result<()> {
    let mut rows = Vec::new();
    for mode in [
        "flat",
        "stationary-texture",
        "drift",
        "translated-texture",
        "defocus",
        "clipped",
    ] {
        let mut accepted = 0;
        let mut total = 0;
        for wi in [0, 5] {
            let window = &protocol["windows"][wi];
            for (roi, &domain) in domains.iter().enumerate() {
                for pass in 0..2 {
                    for level_divisor in [1., 6.] {
                        let mut q = gate::Gate::new();
                        let mut sampler = RegionSampler::new(domain, 8 << 20)?;
                        pool.install(|| -> Result<()> {
                            for (j, index) in selected(window, pass).iter().enumerate() {
                                let t =
                                    c.map.warps()[*index].placed().context("unplaced control")?;
                                let temporal = if j < 5 {
                                    (j as f32 - 2.) / 2.
                                } else if j == 5 {
                                    1.
                                } else {
                                    -1.
                                };
                                let raw = warped::plant(
                                    domain,
                                    t,
                                    c.profiles[pass],
                                    &c.noise[pass],
                                    c.gains[pass] * level_divisor,
                                    mode,
                                    temporal,
                                    1 + *index as u64 * 7919 + roi as u64 * 53139,
                                )?;
                                let sample = sampler.gather(
                                    &raw,
                                    c.noise[pass].plane(CfaPlane::R).levels,
                                    t,
                                    c.profiles[pass],
                                    c.map.resampler(),
                                )?;
                                q.observe(&sample.planes, &sample.support, j >= 5);
                            }
                            Ok(())
                        })?;
                        let tiles = q.result(&c.noise[pass])?;
                        let count = tiles.iter().filter(|v| v["accepted"] == true).count();
                        accepted += count;
                        total += 9;
                        rows.push(json!({"mode":mode,"window_index":wi,"roi_index":roi,"pass":pass,"planted_original_signal_dn":1200./(c.gains[pass]*level_divisor),"accepted":count,"tiles":tiles}));
                    }
                }
            }
        }
        println!("insect warped {mode}: {accepted}/{total}");
        write(
            &out.join(format!("control-{mode}.json")),
            &json!({"rows":rows.iter().filter(|v|v["mode"]==mode).collect::<Vec<_>>()}),
        )?;
        ensure!(
            if mode == "flat" || mode == "stationary-texture" {
                accepted * 4 >= total * 3
            } else {
                accepted == 0
            },
            "insect warped qualification control failed: {mode}"
        );
    }
    write(
        &out.join("controls-complete-before-cache.json"),
        &json!({"modes":6,"actual_u16_region_sampler_and_frozen_gate":true,"signal_levels_dn":[200,1200],"no_camera_calibration_claim":true}),
    )?;
    Ok(())
}
fn main() -> Result<()> {
    let args: Vec<_> = std::env::args().collect();
    ensure!(args.len() == 3, "FROZEN_PROTOCOL NEW_OUT");
    let input = Path::new(&args[1]);
    let out = Path::new(&args[2]);
    fs::create_dir(out)?;
    let protocol = read(input)?;
    ensure!(
        protocol["schema"] == "strehl.real-noise-insect-qualification-protocol.v1",
        "wrong protocol"
    );
    let render = Path::new(protocol["render"].as_str().unwrap());
    let c = warped::context(render)?;
    ensure!(
        protocol["alignment_sha256"] == c.bindings["alignment_sha256"],
        "frozen alignment changed"
    );
    ensure!(
        protocol["source_identities_sha256"].as_str()
            == Some(sha(&fs::read(render.join("source-identities.json"))?).as_str()),
        "frozen source identities changed"
    );
    let session: ResolvedSession = serde_json::from_value(read(&render.join("session.json"))?)?;
    let ids: Vec<SourceIdentity> =
        serde_json::from_value(read(&render.join("source-identities.json"))?)?;
    ensure!(
        ids.len() == 598 && session.passes.len() == 2,
        "insect census differs"
    );
    let domains: Vec<_> = protocol["rois"]
        .as_array()
        .unwrap()
        .iter()
        .map(|r| {
            let d = &r["domain_quad"];
            SamplingDomain {
                full: c.map.geometry(),
                x: d[0].as_u64().unwrap() as usize,
                y: d[1].as_u64().unwrap() as usize,
                width: 128,
                height: 128,
            }
        })
        .collect();
    write(
        &out.join("protocol-frozen.json"),
        &json!({"input":protocol,"input_sha256":sha(&fs::read(input)?),"source_sha256":sha(include_bytes!("real-noise-consumer-insect-qualification.rs")),"helper_sha256":sha(include_bytes!("real-noise-consumer-warped.rs")),"gate_sha256":sha(include_bytes!("real-noise-consumer-gate.rs")),"historical_reader_sha256":sha(include_bytes!("../sr/historical-cache.rs")),"bindings":c.bindings,"historical_binding":historical_cache::binding()?,"command":args,"workers":4,"memory_limit_bytes":2usize<<30,"measurement_loaded":false}),
    )?;
    let pool = rayon::ThreadPoolBuilder::new().num_threads(4).build()?;
    commission(&c, &protocol, &domains, out, &pool)?;
    let mut cache = historical_cache::HistoricalCache::new(
        Path::new(protocol["cache"].as_str().unwrap()),
        &ids,
        128 << 20,
        c.map.geometry(),
    )?;
    let mut results = Vec::new();
    let mut sources = Vec::new();
    for window in protocol["windows"].as_array().unwrap() {
        let mut passes = Vec::new();
        for pass in 0..2 {
            let mut qs: Vec<_> = (0..domains.len()).map(|_| gate::Gate::new()).collect();
            let mut samplers: Vec<_> = domains
                .iter()
                .map(|&d| RegionSampler::new(d, 8 << 20))
                .collect::<Result<_>>()?;
            pool.install(||->Result<()> {for(j,index) in selected(window,pass).iter().enumerate() {ensure!(session.frames[*index].pass_index==pass,"source pass mismatch");let original=cache.load(&ids[*index])?.context("missing historical original")?;
    for ri in 0..domains.len() {let s=samplers[ri].gather(original.as_ref(),original.levels(),c.map.warps()[*index].placed().context("unplaced guide")?,c.profiles[pass],c.map.resampler())?;qs[ri].observe(&s.planes,&s.support,j>=5);}
    sources.push(json!({"base":window["base"],"pass":pass,"global_index":index,"source":ids[*index],"cache_path":cache.path(&ids[*index])?}));
   }Ok(())})?;
            passes.push(
                qs.iter()
                    .map(|q| q.result(&c.noise[pass]))
                    .collect::<Result<Vec<_>>>()?,
            );
        }
        let mut rois = Vec::new();
        for ri in 0..domains.len() {
            let mut tiles = Vec::new();
            for tile in 0..9 {
                let mut accepted = passes[0][ri][tile]["accepted"] == true
                    && passes[1][ri][tile]["accepted"] == true;
                let mut colors = Vec::new();
                let mut gaps = Vec::new();
                for color in 0..4 {
                    let a = &passes[0][ri][tile]["colors"][color];
                    let b = &passes[1][ri][tile]["colors"][color];
                    let value = |v: &Value, p: usize, k: &str| {
                        v[k].as_f64().unwrap() * f64::from(c.gains[p])
                    };
                    let gap = (value(a, 0, "mean_dn") - value(b, 1, "mean_dn")).abs()
                        / value(a, 0, "mean_sample_sigma").hypot(value(b, 1, "mean_sample_sigma"));
                    gaps.push(gap);
                    accepted &= gap <= 0.5;
                    colors.push(
                        passes[0][ri][tile]["complete_support"] == true
                            && passes[1][ri][tile]["complete_support"] == true
                            && a["accepted"] == true
                            && b["accepted"] == true
                            && gap <= 0.5,
                    );
                }
                tiles.push(json!({"tile":tile,"passes":[passes[0][ri][tile],passes[1][ri][tile]],"mean_gap_combined_sigma":gaps,"accepted_components_before_measurement":colors,"accepted_before_measurement":accepted}));
            }
            rois.push(json!({"name":protocol["rois"][ri]["name"],"domain_quad":[domains[ri].x,domains[ri].y,128,128],"tiles":tiles}));
        }
        let counts: Vec<_> = (0..4)
            .map(|color| {
                rois.iter()
                    .flat_map(|r| r["tiles"].as_array().unwrap())
                    .filter(|t| t["accepted_components_before_measurement"][color] == true)
                    .count()
            })
            .collect();
        println!("base {} accepted CFA {counts:?}", window["base"]);
        results.push(json!({"window":window,"rois":rois,"accepted_components":counts}));
    }
    for id in &ids {
        id.check_unchanged()?;
    }
    write(
        &out.join("qualification.json"),
        &json!({"schema":"strehl.real-noise-insect-qualification.v1","protocol_sha256":sha(&fs::read(out.join("protocol-frozen.json"))?),"windows":results,"sources":sources,"cache_disk_hits":cache.stats().disk_hits,"raw_decodes":0,"measurement_loaded":false,"gate_unchanged":true}),
    )?;
    Ok(())
}
