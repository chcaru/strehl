//! Released descriptive real two-state assay. Complete frozen Q/V mask first;
//! never select, fit, normalize or remove pixels using R/M values.
#![allow(dead_code)]
#[path = "noise-bee-repeat-binding.rs"]
mod binding;
#[path = "real-noise-consumer-structure-consumer.rs"]
mod consumer;
#[path = "real-noise-consumer-warped.rs"]
mod context;
#[path = "noise-bee-repeat-producer.rs"]
mod guide_helper;
#[path = "noise-bee-repeat-gate.rs"]
mod model;
#[path = "real-noise-consumer-structure-operator.rs"]
mod operator;
#[path = "noise-bee-repeat-model.rs"]
mod temporal;
use anyhow::{Context, Result, ensure};
use serde_json::{Value, json};
use sha2::{Digest, Sha256};
use std::{
    fs,
    io::{BufWriter, Write},
    path::Path,
};
use strehl_cli::{
    session_cache::SourceCache,
    session_input::{ResolvedSession, SourceIdentity},
    session_reconstruction_sampling::RegionSampler,
    session_sampling::{SampledCfa, SamplingDomain},
};
type Planes = [Vec<f32>; 4];
const N: usize = 128 * 128;
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
    let mut w = BufWriter::new(
        fs::OpenOptions::new()
            .create_new(true)
            .write(true)
            .open(p)?,
    );
    serde_json::to_writer_pretty(&mut w, v)?;
    w.write_all(b"\n")?;
    w.flush()?;
    w.get_ref().sync_all()?;
    Ok(())
}
fn clone_sample(s: &SampledCfa) -> SampledCfa {
    SampledCfa {
        planes: s.planes.clone(),
        coverage: s.coverage.clone(),
        support: s.support.clone(),
        clipped: s.clipped.clone(),
    }
}
fn zeros() -> Planes {
    std::array::from_fn(|_| vec![0.; N])
}
struct Prepared {
    guide: Planes,
    guide_support: Vec<bool>,
    tiles: Vec<Value>,
}
fn main() -> Result<()> {
    let args: Vec<_> = std::env::args().collect();
    ensure!(args.len() == 6, "RENDER CACHE PROTOCOL SAVED_QV NEW_OUT");
    let render = Path::new(&args[1]);
    let protocol_path = Path::new(&args[3]);
    let qv_path = Path::new(&args[4]);
    let out = Path::new(&args[5]);
    fs::create_dir(out)?;
    let pb = fs::read(protocol_path)?;
    ensure!(
        sha(&pb) == "f2fc47d451314ef0bf4a188cdf52d147d17de4fd72b947f58069017f631fcae4",
        "frozen protocol"
    );
    let protocol: Value = serde_json::from_slice(&pb)?;
    let qb = fs::read(qv_path)?;
    ensure!(
        sha(&qb) == "d0bf1f7bb48d309fee0d1e2f19857d0877dccf02f0fe8446edd126a20ae3875b",
        "frozen Q/V mask"
    );
    let qv: Value = serde_json::from_slice(&qb)?;
    let qpb = fs::read(qv_path.parent().unwrap().join("protocol-frozen.json"))?;
    ensure!(
        sha(&qpb) == "7e7c658be1d729b4e9e829fee0eabb70b0fab40431db92c8e01cf3ff14f05ede"
            && qv["protocol_sha256"] == sha(&qpb),
        "Q/V provenance"
    );
    let qp: Value = serde_json::from_slice(&qpb)?;
    let c = context::context(render)?;
    ensure!(
        qp["bindings"] == c.bindings
            && qp["gate_sha256"] == sha(include_bytes!("noise-bee-repeat-gate.rs")),
        "geometry/noise/optics/gate changed"
    );
    ensure!(
        c.gains == [1., 1.] && format!("{:?}", c.noise[0]) == format!("{:?}", c.noise[1]),
        "same-exposure camera/noise contract"
    );
    let report = read(&render.join("render-report.json"))?;
    let session: ResolvedSession = serde_json::from_value(read(&render.join("session.json"))?)?;
    let identities: Vec<SourceIdentity> =
        serde_json::from_value(read(&render.join("source-identities.json"))?)?;
    ensure!(
        identities.len() == 32 && session.frames.len() == 32,
        "exact32"
    );
    let ob = fs::read(
        protocol_path
            .parent()
            .unwrap()
            .join("source-identities32.json"),
    )?;
    ensure!(
        protocol["input_receipts"][r"inputs\source-identities32.json"] == sha(&ob),
        "original hash receipt"
    );
    let originals: Vec<Value> = serde_json::from_slice(&ob)?;
    let originals: Vec<_> = originals
        .iter()
        .map(|v| {
            Ok(binding::Record {
                filename: Path::new(v["path"].as_str().context("path")?)
                    .file_name()
                    .unwrap()
                    .to_str()
                    .unwrap()
                    .into(),
                bytes: v["bytes"].as_u64().context("bytes")?,
                sha256: v["sha256"].as_str().context("sha")?.into(),
            })
        })
        .collect::<Result<_>>()?;
    let copies: Vec<_> = identities
        .iter()
        .map(|v| binding::Record {
            filename: Path::new(&v.path)
                .file_name()
                .unwrap()
                .to_str()
                .unwrap()
                .into(),
            bytes: v.bytes,
            sha256: v.sha256.clone(),
        })
        .collect();
    let indices = binding::bind32(&originals, &copies).map_err(anyhow::Error::msg)?;
    for (i, f) in session.frames.iter().enumerate() {
        ensure!(
            f.global_index == i && f.path == identities[i].path,
            "session/identity order"
        );
        identities[i].check_unchanged()?;
    }
    let witnesses = protocol["witnesses"].as_array().context("witnesses")?;
    ensure!(witnesses.len() == 9, "all witnesses");
    let full = c.map.geometry();
    let domains: Vec<_> = witnesses
        .iter()
        .map(|w| {
            let f = w["active_fraction_center"].as_array().unwrap();
            SamplingDomain {
                full,
                x: (f[0].as_f64().unwrap() * full.width as f64).floor() as usize - 64,
                y: (f[1].as_f64().unwrap() * full.height as f64).floor() as usize - 64,
                width: 128,
                height: 128,
            }
        })
        .collect();
    let times = protocol["timestamps_unix"].as_array().unwrap();
    let get_times = |base: usize| {
        let t0 = times[base].as_f64().unwrap();
        let t = |o: usize| times[base + o].as_f64().unwrap() - t0;
        temporal::Times {
            q: [t(0), t(7)],
            v: [t(1), t(6)],
            r: [t(2), t(5)],
            m: [t(3), t(4)],
        }
    };
    write(
        &out.join("protocol-frozen.json"),
        &json!({"schema":"strehl.bee-conditional-two-state-assay.v1","command":args,"input_protocol_sha256":sha(&pb),"original_identity_sha256":sha(&ob),"saved_qv_sha256":sha(&qb),"bindings":c.bindings,"source_sha256":sha(include_bytes!("noise-bee-repeat-risk-real.rs")),"gate_sha256":sha(include_bytes!("noise-bee-repeat-gate.rs")),"guide_sha256":sha(include_bytes!("noise-bee-repeat-producer.rs")),"consumer_sha256":sha(include_bytes!("real-noise-consumer-structure-consumer.rs")),"workers":4,"cache_budget_bytes":256<<20,"maximum_memory_bytes":4usize<<30,"scopes":36,"witnesses":witnesses,"estimand":"Conditional empirical two-state reference agreement on the COMPLETE saved Q/V masks; global map already depended on all32sources.","not_claimed":["unbiased physical risk","pure noise/RGBSNR","stationarity","texture certification"],"support_policy":"Every qualified tile stays in all arms; any missing R/M/output support makes the whole affected component/state/arm row unavailable and retains failure counts."}),
    )?;
    let pool = rayon::ThreadPoolBuilder::new().num_threads(4).build()?;
    let mut cache = SourceCache::new(Path::new(&args[2]), &session, 256 << 20)?;
    let mut loaded = Vec::new();
    let mut prepared = Vec::new();
    // Recompute ALL Q/V before any R/M load. Same128 operator/rounding as saved.
    for window in 0..4 {
        let base = 8 * window;
        let t = get_times(base);
        let mut gates: Vec<_> = (0..9).map(|_| model::Gate::new(t)).collect::<Result<_>>()?;
        let mut guides: Vec<Planes> = (0..9)
            .map(|_| std::array::from_fn(|_| vec![0.; 144 * 144]))
            .collect();
        let mut valid = vec![vec![true; 144 * 144]; 9];
        for (role, offsets) in [("Q", [0usize, 7]), ("V", [1usize, 6])] {
            for (j, offset) in offsets.into_iter().enumerate() {
                let index = indices[base + offset];
                let source = cache
                    .load(&identities[index])?
                    .context("cache miss; RAW forbidden")?;
                let pass = session.frames[index].pass_index;
                let placement = c.map.warps()[index].placed().context("unplaced")?;
                pool.install(|| -> Result<()> {
                    for (di, d) in domains.iter().enumerate() {
                        let mut sampler = RegionSampler::new(*d, 8 << 20)?;
                        let sample = sampler.gather(
                            source.as_ref(),
                            source.levels(),
                            placement,
                            c.profiles[pass],
                            c.map.resampler(),
                        )?;
                        let beta = operator::beta(*d, placement, c.profiles[pass]);
                        if role == "Q" {
                            gates[di].q(j, &sample.planes, &sample.support, &beta)?;
                            let expanded = SamplingDomain {
                                x: d.x - 8,
                                y: d.y - 8,
                                width: 144,
                                height: 144,
                                ..*d
                            };
                            let mut gs = RegionSampler::new(expanded, 8 << 20)?;
                            let g = gs.gather(
                                source.as_ref(),
                                source.levels(),
                                placement,
                                c.profiles[pass],
                                c.map.resampler(),
                            )?;
                            let weight = temporal::weights(t.q, (t.m[0] + t.m[1]) * 0.5)
                                .map_err(anyhow::Error::msg)?[j]
                                as f32;
                            for color in 0..4 {
                                for i in 0..144 * 144 {
                                    guides[di][color][i] += weight * g.planes[color][i];
                                    valid[di][i] &= g.support[i];
                                }
                            }
                        } else {
                            gates[di].v(j, &sample.planes, &sample.support, &beta)?;
                        }
                    }
                    Ok(())
                })?;
                loaded.push(json!({"stage":"Q/V","window":window,"role":role,"ordinal":base+offset,"global_index":index}));
            }
        }
        for (di, gate) in gates.iter().enumerate() {
            let tiles = gate.finish(&c.noise[0], 1.10)?;
            let saved = qv["rows"]
                .as_array()
                .unwrap()
                .iter()
                .find(|r| r["window"] == window && r["witness"] == witnesses[di]["id"])
                .context("saved scope")?;
            let mut saved_tiles = saved["tiles"].as_array().context("saved tiles")?.clone();
            for tile in &mut saved_tiles {
                tile.as_object_mut()
                    .unwrap()
                    .remove("q_predicted_measurement_dn");
            }
            ensure!(
                tiles == saved_tiles,
                "EXACT Q/V numerical/mask equality failed before any R/M"
            );
            let (g, s) = guide_helper::finish_guide(&guides[di], &valid[di])?;
            prepared.push(Prepared {
                guide: g,
                guide_support: s,
                tiles,
            });
        }
    }
    ensure!(
        loaded.len() == 16 && prepared.len() == 36,
        "complete allQV first"
    );
    write(
        &out.join("qv-replay-proof.json"),
        &json!({"exact_all_tile_values_and_masks":true,"scopes":36,"loaded":loaded,"r_m_read":false}),
    )?;
    let mut rows = Vec::new();
    let mut diagnostic_rows = Vec::new();
    for window in 0..4 {
        let base = 8 * window;
        let t = get_times(base);
        let mi = [indices[base + 3], indices[base + 4]];
        let m0 = cache.load(&identities[mi[0]])?.context("missing M0")?;
        let m1 = cache.load(&identities[mi[1]])?.context("missing M1")?;
        let ms = [m0, m1];
        let mut outcomes = Vec::new();
        let mut measurement_valid = vec![vec![true; N]; 9];
        let mut measurement_clipped = vec![vec![false; N]; 9];
        for (di, d) in domains.iter().enumerate() {
            let p = &prepared[window * 9 + di];
            let o = pool.install(|| {
                consumer::produce(
                    &c,
                    &report,
                    mi,
                    &p.guide,
                    &p.guide_support,
                    indices[base],
                    |index| {
                        let j = if index == mi[0] {
                            0
                        } else if index == mi[1] {
                            1
                        } else {
                            anyhow::bail!("non-M consumer read")
                        };
                        let pass = session.frames[index].pass_index;
                        let mut sampler = RegionSampler::new(*d, 8 << 20)?;
                        let sample = sampler.gather(
                            ms[j].as_ref(),
                            ms[j].levels(),
                            c.map.warps()[index].placed().unwrap(),
                            c.profiles[pass],
                            c.map.resampler(),
                        )?;
                        for i in 0..N {
                            measurement_valid[di][i] &= sample.support[i];
                            measurement_clipped[di][i] |= sample.clipped[i];
                        }
                        Ok(clone_sample(sample))
                    },
                )
            })?;
            diagnostic_rows.push(json!({"window":window,"witness":witnesses[di]["id"],"guide_supported_pixels":p.guide_support.iter().filter(|v|**v).count(),"outcomes":o.iter().enumerate().map(|(a,v)|json!({"arm":a,"diagnostics":v.diagnostics})).collect::<Vec<_>>()}));
            outcomes.push(o);
        }
        drop(ms);
        for (j, &index) in mi.iter().enumerate() {
            loaded.push(json!({"stage":"M beforeR","window":window,"role":"M","ordinal":base+3+j,"global_index":index}));
        }
        let mut refs: Vec<[Planes; 2]> = (0..9).map(|_| [zeros(), zeros()]).collect();
        let mut refvalid = vec![vec![true; N]; 9];
        let mut refclipped = vec![vec![false; N]; 9];
        for (j, offset) in [2usize, 5].into_iter().enumerate() {
            let index = indices[base + offset];
            let source = cache.load(&identities[index])?.context("missing R")?;
            let pass = session.frames[index].pass_index;
            let placement = c.map.warps()[index].placed().unwrap();
            pool.install(|| -> Result<()> {
                for (di, d) in domains.iter().enumerate() {
                    let mut sampler = RegionSampler::new(*d, 8 << 20)?;
                    let s = sampler.gather(
                        source.as_ref(),
                        source.levels(),
                        placement,
                        c.profiles[pass],
                        c.map.resampler(),
                    )?;
                    for i in 0..N {
                        refvalid[di][i] &= s.support[i];
                        refclipped[di][i] |= s.clipped[i];
                    }
                    for state in 0..2 {
                        let w = temporal::weights(t.r, t.m[state]).map_err(anyhow::Error::msg)?[j]
                            as f32;
                        for color in 0..4 {
                            for i in 0..N {
                                refs[di][state][color][i] += w * s.planes[color][i];
                            }
                        }
                    }
                }
                Ok(())
            })?;
            loaded.push(json!({"stage":"R aftercandidates","window":window,"role":"R","ordinal":base+offset,"global_index":index}));
        }
        for di in 0..9 {
            for tile in &prepared[window * 9 + di].tiles {
                let color = tile["color"].as_u64().unwrap() as usize;
                let x = tile["tile_quad"][0].as_u64().unwrap() as usize;
                let y = tile["tile_quad"][1].as_u64().unwrap() as usize;
                let accepted = tile["accepted"] == true;
                for state in 0..2 {
                    for arm in 0..4 {
                        let mut missing_r = 0;
                        let mut missing_m = 0;
                        let mut clipped_m = 0;
                        let mut missing_output = 0;
                        let mut clipped_r = 0;
                        let mut ar = 0.;
                        let mut br = 0.;
                        let mut am = 0.;
                        let mut bm = 0.;
                        let mut rm = 0.;
                        let mut diff = 0.;
                        for yy in y..y + 32 {
                            for xx in x..x + 32 {
                                let i = yy * 128 + xx;
                                missing_r += usize::from(!refvalid[di][i]);
                                missing_m += usize::from(!measurement_valid[di][i]);
                                clipped_m += usize::from(measurement_clipped[di][i]);
                                clipped_r += usize::from(refclipped[di][i]);
                                missing_output += usize::from(
                                    !outcomes[di][arm].valid[i] || !outcomes[di][state].valid[i],
                                );
                                let a = f64::from(outcomes[di][arm].planes[color][i]);
                                let b = f64::from(outcomes[di][state].planes[color][i]);
                                let r = f64::from(refs[di][state][color][i]);
                                ar += (a - r).powi(2);
                                br += (b - r).powi(2);
                                am += a;
                                bm += b;
                                rm += r;
                                diff += a - b;
                            }
                        }
                        let status = if !accepted {
                            "not-qualified"
                        } else if missing_r > 0 || missing_output > 0 || missing_m > 0 {
                            "unavailable-support"
                        } else {
                            "available"
                        };
                        let metric = if status == "available" {
                            json!({"candidate_reference_mse":ar/1024.,"own_single_reference_mse":br/1024.,"difference_vs_own_single":(ar-br)/1024.,"candidate_minus_reference_mean_dn":(am-rm)/1024.,"own_single_minus_reference_mean_dn":(bm-rm)/1024.,"candidate_centered_reference_mse":ar/1024.-((am-rm)/1024.).powi(2),"own_single_centered_reference_mse":br/1024.-((bm-rm)/1024.).powi(2),"candidate_minus_own_single_mean_dn":diff/1024.})
                        } else {
                            Value::Null
                        };
                        rows.push(json!({"window":window,"base":base,"witness":witnesses[di]["id"],"domain_quad":[domains[di].x,domains[di].y,128,128],"tile_quad":[x,y,32,32],"color":color,"state":state,"arm":(["singleM3","singleM4","equal","precision"][arm]),"qv_qualified":accepted,"fixed_pixels":if accepted{1024}else{0},"status":status,"missing_measurement_pixels":missing_m,"clipped_measurement_pixels":clipped_m,"missing_reference_pixels":missing_r,"clipped_reference_pixels":clipped_r,"missing_output_pixels":missing_output,"reference_weights":temporal::weights(t.r,t.m[state]).unwrap(),"metric":metric}));
                    }
                }
            }
        }
    }
    ensure!(
        loaded.len() == 32 && cache.stats().decodes == 0,
        "all32cachedonly"
    );
    for identity in &identities {
        identity.check_unchanged()?;
    }
    write(
        &out.join("result.json"),
        &json!({"schema":"strehl.bee-conditional-two-state-assay.v1","protocol_sha256":sha(&fs::read(out.join("protocol-frozen.json"))?),"qv_exact_replay":true,"rows":rows,"diagnostics":diagnostic_rows,"loaded_sources":loaded,"source_identities":identities,"cache_disk_hits":cache.stats().disk_hits,"raw_decodes":0,"limitations":["Conditional joint-map empirical reference agreement, not unbiased risk or pure noise/RGBSNR.","All complete frozen component masks retained; support-unavailable rows retained without survivor pruning.","Nearblack commissioning has a retained failed stratum and known calibration uncertainty.","Low-signal temporal/texture mismatch can pass Q/V; lower predictive error can reward blur.","Four acquisition windows; spatial blocks and two reference states are dependent. No pixel-count uncertainty.","Assay pairs are two acquisitions, not proof of runtime cross-pass matching or fullphoto benefit."]}),
    )?;
    println!(
        "all36scopes {}rows; exact Q/V;32cache-only reads,0decode",
        rows.len()
    );
    Ok(())
}
