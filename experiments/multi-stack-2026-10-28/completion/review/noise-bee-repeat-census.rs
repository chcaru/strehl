//! Read ONLY the frozen16 Q/V originals from the verified product cache.
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
use serde_json::{Value, json};
use sha2::{Digest, Sha256};
use std::{collections::BTreeSet, fs, io::Write, path::Path};
use strehl_cli::{
    session_cache::SourceCache,
    session_input::{ResolvedSession, SourceIdentity},
    session_reconstruction_sampling::RegionSampler,
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
    ensure!(
        args.len() == 7,
        "RENDER CACHE FROZEN_PROTOCOL TRAIN_REPORT HELD_REPORT NEW_OUT"
    );
    let render = Path::new(&args[1]);
    let out = Path::new(&args[6]);
    fs::create_dir(out)?;
    let c = context::context(render)?;
    let bytes = fs::read(&args[3])?;
    ensure!(
        sha(&bytes) == "f2fc47d451314ef0bf4a188cdf52d147d17de4fd72b947f58069017f631fcae4",
        "frozen roles"
    );
    let protocol: Value = serde_json::from_slice(&bytes)?;
    let train = read(Path::new(&args[4]))?;
    let held = read(Path::new(&args[5]))?;
    for (path, r, phase) in [(&args[4], &train, "train"), (&args[5], &held, "held")] {
        let pb = fs::read(
            Path::new(path)
                .parent()
                .context("reportparent")?
                .join("protocol-frozen.json"),
        )?;
        let p: Value = serde_json::from_slice(&pb)?;
        ensure!(
            r["phase"] == phase
                && r["commission_passed"] == true
                && r["protocol_sha256"] == sha(&pb)
                && r["input_protocol_sha256"] == sha(&bytes)
                && p["bindings"] == c.bindings
                && p["gate_sha256"] == sha(include_bytes!("noise-bee-repeat-gate.rs"))
                && p["temporal_sha256"] == sha(include_bytes!("noise-bee-repeat-model.rs"))
                && p["operator_sha256"]
                    == sha(include_bytes!("real-noise-consumer-structure-operator.rs")),
            "commission binding"
        );
    }
    let cutoff = train["cutoff"].as_f64().context("cutoff")?;
    // The frozen producer pooled every training tile. Its actual flat corpus
    // had full support; explicitly refuse reuse if that premise is not true.
    let training_flat = read(
        &Path::new(&args[4])
            .parent()
            .context("training parent")?
            .join("flat.json"),
    )?;
    ensure!(
        training_flat["rows"]
            .as_array()
            .context("training rows")?
            .iter()
            .flat_map(|r| r["tiles"].as_array().unwrap())
            .all(|t| t["supported"] == 1024),
        "training cutoff included unsupported tiles"
    );
    ensure!(
        held["cutoff"] == cutoff && cutoff == 1.10,
        "released cutoff"
    );
    let session: ResolvedSession = serde_json::from_value(read(&render.join("session.json"))?)?;
    let identities: Vec<SourceIdentity> =
        serde_json::from_value(read(&render.join("source-identities.json"))?)?;
    let mut indices = [usize::MAX; 32];
    for f in &session.frames {
        let ordinal = f
            .path
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
            "unique ordinal"
        );
        indices[ordinal] = f.global_index;
    }
    ensure!(
        indices.iter().all(|x| *x != usize::MAX),
        "complete32sources"
    );
    let mut allowed = BTreeSet::new();
    let mut withheld = BTreeSet::new();
    for base in [0, 8, 16, 24] {
        for offset in [0, 7, 1, 6] {
            allowed.insert(indices[base + offset]);
        }
        for offset in [2, 5, 3, 4] {
            withheld.insert(indices[base + offset]);
        }
    }
    ensure!(
        allowed.len() == 16 && withheld.len() == 16 && allowed.is_disjoint(&withheld),
        "Q/V-only role split"
    );
    let full = c.map.geometry();
    let witnesses = protocol["witnesses"].as_array().context("witnesses")?;
    ensure!(witnesses.len() == 9, "all9witnesses");
    let domains: Vec<_> = witnesses
        .iter()
        .map(|v| {
            let f = v["active_fraction_center"].as_array().unwrap();
            SamplingDomain {
                full,
                x: (f[0].as_f64().unwrap() * full.width as f64).floor() as usize - 64,
                y: (f[1].as_f64().unwrap() * full.height as f64).floor() as usize - 64,
                width: 128,
                height: 128,
            }
        })
        .collect();
    write(
        &out.join("protocol-frozen.json"),
        &json!({"schema":"strehl.bee-qv-census.v1","command":args,"input_protocol_sha256":sha(&bytes),"bindings":c.bindings,"training_report_sha256":sha(&fs::read(&args[4])?),"heldout_report_sha256":sha(&fs::read(&args[5])?),"cutoff":cutoff,"allowed_global_indices":allowed,"withheld_global_indices":withheld,"witnesses":witnesses,"domain_quad":domains.iter().map(|d|[d.x,d.y,d.width,d.height]).collect::<Vec<_>>(),"source_sha256":sha(include_bytes!("noise-bee-repeat-census.rs")),"gate_sha256":sha(include_bytes!("noise-bee-repeat-gate.rs")),"workers":4,"memory_limit_bytes":4usize<<30,"scope":"Q/V-only assay reads. All32sources already read by fullphoto preparation; conditional joint geometry is not independent-R geometry."}),
    )?;
    let pool = rayon::ThreadPoolBuilder::new().num_threads(4).build()?;
    let mut cache = SourceCache::new(Path::new(&args[2]), &session, 256 << 20)?;
    let mut rows = Vec::new();
    let mut loaded = Vec::new();
    for window in 0..4 {
        let base = 8 * window;
        let times = protocol["timestamps_unix"].as_array().unwrap();
        let first = times[base].as_f64().unwrap();
        let t = |o: usize| times[base + o].as_f64().unwrap() - first;
        let timestamps = temporal::Times {
            q: [t(0), t(7)],
            v: [t(1), t(6)],
            r: [t(2), t(5)],
            m: [t(3), t(4)],
        };
        let mut gates: Vec<_> = (0..9)
            .map(|_| model::Gate::new(timestamps))
            .collect::<Result<_>>()?;
        let mut predictions: Vec<[[Vec<f64>; 4]; 2]> = (0..9)
            .map(|_| std::array::from_fn(|_| std::array::from_fn(|_| vec![0.; 128 * 128])))
            .collect();
        for (role, offsets) in [("Q", [0usize, 7]), ("V", [1usize, 6])] {
            for (j, offset) in offsets.into_iter().enumerate() {
                let ordinal = base + offset;
                let index = indices[ordinal];
                ensure!(
                    allowed.contains(&index) && !withheld.contains(&index),
                    "attempted nonQ/Vread"
                );
                let source = cache
                    .load(&identities[index])?
                    .context("missing cache; RAW decoding forbidden")?;
                let pass = session.frames[index].pass_index;
                let placement = c.map.warps()[index].placed().context("unplaced")?;
                pool.install(|| -> Result<()> {
                    for (di, domain) in domains.iter().enumerate() {
                        let mut sampler = RegionSampler::new(*domain, 8 << 20)?;
                        let sample = sampler.gather(
                            source.as_ref(),
                            source.levels(),
                            placement,
                            c.profiles[pass],
                            c.map.resampler(),
                        )?;
                        let beta = operator::beta(*domain, placement, c.profiles[pass]);
                        if role == "Q" {
                            gates[di].q(j, &sample.planes, &sample.support, &beta)?;
                            for state in 0..2 {
                                let w = temporal::weights(timestamps.q, timestamps.m[state])
                                    .map_err(anyhow::Error::msg)?[j];
                                for color in 0..4 {
                                    for pixel in 0..128 * 128 {
                                        predictions[di][state][color][pixel] +=
                                            w * f64::from(sample.planes[color][pixel]);
                                    }
                                }
                            }
                        } else {
                            gates[di].v(j, &sample.planes, &sample.support, &beta)?;
                        }
                    }
                    Ok(())
                })?;
                loaded.push(json!({"window":window,"role":role,"ordinal":ordinal,"global_index":index,"source":identities[index],"cache_path":cache.cache_path(&identities[index])?}));
            }
        }
        for (di, gate) in gates.iter().enumerate() {
            let mut tiles = gate.finish(&c.noise[0], cutoff)?;
            for tile in &mut tiles {
                let color = tile["color"].as_u64().unwrap() as usize;
                let x = tile["tile_quad"][0].as_u64().unwrap() as usize;
                let y = tile["tile_quad"][1].as_u64().unwrap() as usize;
                let mut levels = Vec::new();
                for state in 0..2 {
                    let mut sum = 0.;
                    let mut minimum = f64::INFINITY;
                    let mut maximum = f64::NEG_INFINITY;
                    for yy in y..y + 32 {
                        for xx in x..x + 32 {
                            let value = predictions[di][state][color][yy * 128 + xx];
                            sum += value;
                            minimum = minimum.min(value);
                            maximum = maximum.max(value);
                        }
                    }
                    levels.push(json!({"measurement_state":state,"mean":sum/1024.,"minimum":minimum,"maximum":maximum}));
                }
                tile["q_predicted_measurement_dn"] = json!(levels);
            }
            let counts: [usize; 4] = std::array::from_fn(|color| {
                tiles
                    .iter()
                    .filter(|v| v["color"] == color && v["accepted"] == true)
                    .count()
            });
            let coherent = (0..9)
                .filter(|tile| (0..4).all(|color| tiles[tile * 4 + color]["accepted"] == true))
                .count();
            rows.push(json!({"window":window,"base":base,"witness":witnesses[di]["id"],"domain_quad":[domains[di].x,domains[di].y,128,128],"accepted_components":counts,"all_cfa_blocks":coherent,"tiles":tiles}));
        }
    }
    for &i in &allowed {
        identities[i].check_unchanged()?;
    }
    ensure!(
        loaded.len() == 16 && cache.stats().decodes == 0,
        "only16cachedQ/Voriginals"
    );
    let counts: [u64; 4] = std::array::from_fn(|c| {
        rows.iter()
            .map(|r| r["accepted_components"][c].as_u64().unwrap())
            .sum()
    });
    let coherent: u64 = rows
        .iter()
        .map(|r| r["all_cfa_blocks"].as_u64().unwrap())
        .sum();
    println!("Q/V components {counts:?}, allCFA {coherent}/324");
    write(
        &out.join("qualification.json"),
        &json!({"schema":"strehl.bee-qv-census.v1","protocol_sha256":sha(&fs::read(out.join("protocol-frozen.json"))?),"rows":rows,"accepted_components":counts,"all_cfa_blocks":coherent,"component_block_total":324,"loaded_sources":loaded,"cache_disk_hits":cache.stats().disk_hits,"raw_decodes":0,"r_m_loaded_by_assay":false,"limitations":["Joint wholephoto geometry includes all32acquisitions; not the independent-R assay geometry.","Temporal consistency under commissioned linear model, not stationarity or physical focus identity.","LowDN shift/step/focus plants have accepted cases; cutoff does not exclude all temporalmodel error.","All9witnesses and all component/window outcomes retained; noR/Mselection."]}),
    )?;
    Ok(())
}
