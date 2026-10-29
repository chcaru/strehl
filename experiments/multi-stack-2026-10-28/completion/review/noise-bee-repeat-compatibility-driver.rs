//! Exact original-CFA band primitive -> fixed compatibility decision controls.
//! No real cache/source reads. Oracle per-original-site mean is explicitly scoped.
#![allow(dead_code)]
pub use strehl_core::{CfaPlane, align, noise, plane};
#[path = "real-noise-consumer-warped.rs"]
mod context;
#[path = "noise-bee-repeat-compatibility.rs"]
mod decision;
#[path = "real-noise-consumer-structure-operator.rs"]
mod operator;
#[path = "../../../../crates/strehl-core/src/repeat-evidence.rs"]
mod tap;
use anyhow::{Result, ensure};
use serde_json::{Value, json};
use sha2::{Digest, Sha256};
use std::{collections::BTreeSet, fs, io::Write, path::Path};
use strehl_cli::session_sampling::SamplingDomain;
use strehl_core::optics::{OpticalProfile, cfa_site_channel};
fn sha(b: &[u8]) -> String {
    Sha256::digest(b)
        .iter()
        .map(|v| format!("{v:02x}"))
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
fn iv(i: Option<decision::Interval>) -> Value {
    i.map_or(Value::Null, |v| json!([v.lower, v.upper]))
}
fn evidence(e: &decision::Evidence) -> Value {
    json!({"decision":format!("{:?}",e.decision),"points":e.points,"identity_difference_to_noise":iv(e.identity_difference_to_noise),"joint_difference_to_noise":iv(e.joint_difference_to_noise),"bands":e.bands.iter().map(|b|json!({"band":b.band,"decision":format!("{:?}",b.decision),"signal_x":iv(b.signal_x),"signal_y":iv(b.signal_y),"signal_difference":iv(b.signal_difference),"signed_cross":iv(b.signed_cross),"y_from_x_amplitude":iv(b.y_from_x_amplitude),"x_from_y_amplitude":iv(b.x_from_y_amplitude),"disagreement_cost_to_equal_noise_benefit":iv(b.difference_cost_to_equal_noise_benefit)})).collect::<Vec<_>>()})
}
fn main() -> Result<()> {
    let args: Vec<_> = std::env::args().collect();
    ensure!(args.len() == 5, "RENDER PROTOCOL NEW_OUT flat|all");
    let out = Path::new(&args[3]);
    fs::create_dir(out)?;
    let c = context::context(Path::new(&args[1]))?;
    let bytes = fs::read(&args[2])?;
    ensure!(
        sha(&bytes) == "f2fc47d451314ef0bf4a188cdf52d147d17de4fd72b947f58069017f631fcae4",
        "frozen protocol"
    );
    let p: Value = serde_json::from_slice(&bytes)?;
    let patches = p["geometry_patches"].as_array().unwrap();
    let bands = tap::binomial_bands();
    let filters: Vec<_> = bands.iter().map(Vec::as_slice).collect();
    let full = c.map.geometry();
    let indices = [1usize, 17usize];
    let pulls = indices.map(|i| c.map.warps()[i].placed().unwrap());
    let modes = if args[4] == "flat" {
        vec!["flat"]
    } else {
        ensure!(args[4] == "all", "mode");
        vec![
            "stationary",
            "focus",
            "shift",
            "step",
            "opposite",
            "clipped",
            "low-signal",
        ]
    };
    write(
        &out.join("protocol-frozen.json"),
        &json!({"schema":"strehl.bee-native-mean-compatibility-controls.v1","command":args,"input_protocol_sha256":sha(&bytes),"bindings":c.bindings,"indices":indices,"seeds":[160,161,162,163],"patches":&patches[1..3],"point_grid_quad":"8..248 step16 (32sensor), exact originaltaps checked disjoint","bands":"root binomial high/mid/low, sensor2/4support","guide":"ORACLE known per-original-site signal, not actualQ0/7; no real image admission","policy":{"minimum_points":64,"envelope_t":4.605170185988092,"equal_loss_budget":0.5,"amplitude_margin":0.05},"source_sha256":sha(include_bytes!("noise-bee-repeat-compatibility-driver.rs")),"decision_sha256":sha(include_bytes!("noise-bee-repeat-compatibility.rs")),"tap_sha256":sha(include_bytes!("../../../../crates/strehl-core/src/repeat-evidence.rs")),"workers":1,"raw_decodes":0,"cache_reads":0}),
    )?;
    let mut rows = Vec::new();
    for mode in modes {
        for seed in 160..164 {
            for patch in &patches[1..3] {
                let f = patch["active_fraction_center"].as_array().unwrap();
                let d = SamplingDomain {
                    full,
                    x: (f[0].as_f64().unwrap() * full.width as f64).floor() as usize - 128,
                    y: (f[1].as_f64().unwrap() * full.height as f64).floor() as usize - 128,
                    width: 256,
                    height: 256,
                };
                let kind0 = if mode == "flat" { "flat" } else { "stationary" };
                let kind1 = match mode {
                    "opposite" => "quadratic-opposite",
                    "low-signal" => "stationary",
                    "flat" => "flat",
                    x => x,
                };
                let divisor = if mode == "low-signal" { 60. } else { 1. };
                let ts = [
                    4f32,
                    if mode == "focus" {
                        7.
                    } else if mode == "shift" || mode == "step" {
                        6.
                    } else {
                        4.
                    },
                ];
                let sources = [
                    operator::plant(
                        d,
                        pulls[0],
                        c.profiles[0],
                        &c.noise[0],
                        divisor,
                        kind0,
                        ts[0],
                        seed * 7919 + indices[0] as u64,
                    )?,
                    operator::plant(
                        d,
                        pulls[1],
                        c.profiles[1],
                        &c.noise[1],
                        divisor,
                        kind1,
                        ts[1],
                        seed * 7919 + indices[1] as u64,
                    )?,
                ];
                for color in 0..4 {
                    let plane = CfaPlane::ALL[color];
                    let (dx, dy) = plane.rggb_offset();
                    let site = [dx as f64 * 0.5 - 0.25, dy as f64 * 0.5 - 0.25];
                    let color_pulls: [align::Similarity; 2] = std::array::from_fn(|source| {
                        OpticalProfile::compose(
                            c.profiles[source],
                            cfa_site_channel(dx, dy),
                            pulls[source],
                        )
                    });
                    let mut used: [BTreeSet<(usize, usize)>; 2] =
                        std::array::from_fn(|_| BTreeSet::new());
                    let mut points = Vec::new();
                    let mut refusals = Vec::new();
                    for yy in (8..256).step_by(16) {
                        for xx in (8..256).step_by(16) {
                            let center_sensor =
                                [2. * (d.x + xx) as f64 + 0.5, 2. * (d.y + yy) as f64 + 0.5];
                            let mut observed = Vec::new();
                            for source in 0..2 {
                                let inverse = color_pulls[source].invert().unwrap();
                                let kind = if source == 0 { kind0 } else { kind1 };
                                let view = tap::OriginalView {
                                    acquisition_id: [(indices[source] + 1) as u8; 32],
                                    source: &sources[source],
                                    plane,
                                    color_pull: color_pulls[source],
                                    noise: *c.noise[source].plane(plane),
                                    gain: 1.,
                                };
                                let r = tap::observe(
                                    &view,
                                    full,
                                    center_sensor,
                                    &filters,
                                    tap::Kernel::CatmullRom,
                                    2 << 20,
                                    |s| {
                                        let q = inverse.apply_at(
                                            s.quad[0] as f64 + site[0],
                                            s.quad[1] as f64 + site[1],
                                            full.width as f64 * 0.5,
                                            full.height as f64 * 0.5,
                                        );
                                        Some(
                                            (operator::truth(
                                                kind,
                                                ts[source] as f64,
                                                color,
                                                (q.0 - d.x as f64) as f32 as f64,
                                                (q.1 - d.y as f64) as f32 as f64,
                                            ) / divisor as f64)
                                                as f32,
                                        )
                                    },
                                );
                                match r {
                                    Ok(o) => {
                                        for t in &o.taps {
                                            ensure!(
                                                used[source]
                                                    .insert((t.site.quad[0], t.site.quad[1])),
                                                "overlapping original point evidence"
                                            );
                                        }
                                        observed.push(o);
                                    }
                                    Err(e) => {
                                        refusals.push(json!({"grid":[xx,yy],"source":source,"reason":format!("{e:?}")}));
                                    }
                                }
                            }
                            if observed.len() == 2 {
                                points.push(decision::PairSample {
                                    x: std::array::from_fn(|i| f64::from(observed[0].values[i])),
                                    y: std::array::from_fn(|i| f64::from(observed[1].values[i])),
                                    covariance_x: std::array::from_fn(|i| {
                                        std::array::from_fn(|j| {
                                            f64::from(observed[0].covariance[i][j])
                                        })
                                    }),
                                    covariance_y: std::array::from_fn(|i| {
                                        std::array::from_fn(|j| {
                                            f64::from(observed[1].covariance[i][j])
                                        })
                                    }),
                                });
                            }
                        }
                    }
                    // No survivor subset can become admitted after support/clip refusal.
                    let evaluated = if refusals.is_empty() {
                        Some(
                            decision::evaluate(&points, decision::Policy::default())
                                .map_err(anyhow::Error::msg)?,
                        )
                    } else {
                        None
                    };
                    if mode == "flat" {
                        ensure!(
                            evaluated
                                .as_ref()
                                .is_none_or(|e| e.decision != decision::Decision::Compatible),
                            "flat certified PSF/transfer"
                        );
                    }
                    rows.push(json!({"mode":mode,"seed":seed,"patch":patch["id"],"color":color,"points":points.len(),"exact_disjoint_original_sites":[used[0].len(),used[1].len()],"refusals":refusals,"evidence":evaluated.as_ref().map(evidence),"state_if_support_failed":"Unknown"}));
                }
            }
        }
    }
    write(
        &out.join("result.json"),
        &json!({"schema":"strehl.bee-native-mean-compatibility-controls.v1","protocol_sha256":sha(&fs::read(out.join("protocol-frozen.json"))?),"rows":rows,"scope":"Author-run synthetic exact-CFA primitive + decision. No actualpairadmission, no matching/core/fullphoto claim. Same-PSF nearNyquist alias control and actual disjointQguide remain required."}),
    )?;
    println!("{} allscope component rows, no realreads", rows.len());
    Ok(())
}
