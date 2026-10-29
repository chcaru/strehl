//! Synthetic independent-R risk through the actual four-arm CFA consumer.
//! No real originals or cache entries are read. Complete Q/V masks stay fixed.
#![allow(dead_code)]
#[path = "real-noise-consumer-structure-consumer.rs"]
mod consumer;
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
    session_reconstruction_sampling::RegionSampler,
    session_sampling::{SampledCfa, SamplingDomain},
};
use strehl_core::{CfaPlane, align::Resampler, boxfilter::box_mean};
type Planes = [Vec<f32>; 4];
const N: usize = 128 * 128;
fn sha(b: &[u8]) -> String {
    Sha256::digest(b)
        .iter()
        .map(|v| format!("{v:02x}"))
        .collect()
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
fn zero() -> Planes {
    std::array::from_fn(|_| vec![0.; N])
}
fn r_weights(t: f64) -> [f64; 4] {
    let z = (t - 4.) / 4.;
    [-1.5, -0.5, 0.5, 1.5].map(|x| 0.25 + z * x / 5. + (z * z - 1.25) * (x * x - 1.25) / 4.)
}
fn gather(
    c: &context::Contexts,
    d: SamplingDomain,
    mode: &str,
    base: usize,
    index: usize,
    seed: u64,
    sampler: &mut RegionSampler,
) -> Result<SampledCfa> {
    gather_at(
        c,
        d,
        [d.x as f64, d.y as f64],
        mode,
        base,
        index,
        seed,
        sampler,
    )
}
fn gather_at(
    c: &context::Contexts,
    d: SamplingDomain,
    signal_origin: [f64; 2],
    mode: &str,
    base: usize,
    index: usize,
    seed: u64,
    sampler: &mut RegionSampler,
) -> Result<SampledCfa> {
    let pass = usize::from(index >= 299);
    let ordinal = index - 299 * pass;
    let temporal = ordinal as f32 - base as f32;
    let t = c.map.warps()[index].placed().context("unplaced original")?;
    let raw = operator::plant_at(
        d,
        signal_origin,
        t,
        c.profiles[pass],
        &c.noise[pass],
        c.gains[pass],
        mode,
        temporal,
        seed * 53139 + index as u64 * 7919,
    )?;
    let s = sampler.gather(
        &raw,
        c.noise[pass].plane(CfaPlane::R).levels,
        t,
        c.profiles[pass],
        c.map.resampler(),
    )?;
    Ok(SampledCfa {
        planes: s.planes.clone(),
        support: s.support.clone(),
        coverage: s.coverage.clone(),
        clipped: s.clipped.clone(),
    })
}
fn eligible(
    c: &context::Contexts,
    d: SamplingDomain,
    mode: &str,
    base: usize,
    seed: u64,
    sampler: &mut RegionSampler,
) -> Result<([Vec<bool>; 4], Value)> {
    let mut both: Option<Vec<Value>> = None;
    let mut passes = Vec::new();
    for pass in 0..2 {
        let mut gate = model::Gate::new();
        for (role, ordinals) in [("Q", [0, 4, 8]), ("V", [1, 5, 9])] {
            for (j, o) in ordinals.into_iter().enumerate() {
                let i = base + o + 299 * pass;
                let s = gather(c, d, mode, base, i, seed, sampler)?;
                let b = operator::beta(d, c.map.warps()[i].placed().unwrap(), c.profiles[pass]);
                if role == "Q" {
                    gate.q(j, &s.planes, &s.support, &b, c.gains[pass])?;
                } else {
                    gate.v(j, &s.planes, &s.support, &b, c.gains[pass])?;
                }
            }
        }
        let rows = gate.finish(&c.noise[pass], c.gains[pass])?;
        if let Some(joint) = &mut both {
            for (a, b) in joint.iter_mut().zip(&rows) {
                a["accepted"] = json!(a["accepted"] == true && b["accepted"] == true);
            }
        } else {
            both = Some(rows.clone());
        }
        passes.push(rows);
    }
    let joint = both.unwrap();
    let mut masks = std::array::from_fn(|_| vec![false; N]);
    for row in &joint {
        if row["accepted"] == true {
            let c = row["color"].as_u64().unwrap() as usize;
            let tx = row["tile_quad"][0].as_u64().unwrap() as usize;
            let ty = row["tile_quad"][1].as_u64().unwrap() as usize;
            for y in ty..ty + 32 {
                for x in tx..tx + 32 {
                    masks[c][y * 128 + x] = true;
                }
            }
        }
    }
    Ok((masks, json!({"passes":passes,"joint":joint})))
}
fn truth(mode: &str, t: f64) -> Planes {
    std::array::from_fn(|c| {
        let (dx, dy) = CfaPlane::ALL[c].rggb_offset();
        (0..N)
            .map(|i| {
                operator::truth(
                    mode,
                    t,
                    c,
                    (i % 128) as f64 + dx as f64 * 0.5 - 0.25,
                    (i / 128) as f64 + dy as f64 * 0.5 - 0.25,
                ) as f32
            })
            .collect()
    })
}
fn smooth(p: &Planes, r: usize) -> Planes {
    let mut scratch = vec![0.; N];
    std::array::from_fn(|c| {
        let mut out = vec![0.; N];
        box_mean(
            &p[c],
            strehl_core::plane::PlaneGeometry {
                width: 128,
                height: 128,
            },
            r,
            &mut scratch,
            &mut out,
        );
        out
    })
}

fn finish_weight_guide(sum: &Planes, valid: &[bool], width: usize) -> Result<(Planes, Vec<bool>)> {
    ensure!(
        width == 144
            && valid.len() == width * width
            && sum.iter().all(|p| p.len() == width * width),
        "expanded guide shape"
    );
    let g = strehl_core::plane::PlaneGeometry {
        width,
        height: width,
    };
    let mut scratch = vec![0.; g.pixels()];
    let mut blurred = vec![0.; g.pixels()];
    let mut support_scratch = vec![0u32; g.pixels()];
    let mut support = vec![false; g.pixels()];
    strehl_cli::session_focus::complete_support(valid, g, 8, &mut support_scratch, &mut support)?;
    let mut out = zero();
    let mut cropped = vec![false; N];
    for c in 0..4 {
        box_mean(&sum[c], g, 8, &mut scratch, &mut blurred);
        for y in 0..128 {
            for x in 0..128 {
                let p = y * 128 + x;
                let q = (y + 8) * width + x + 8;
                out[c][p] = blurred[q];
                cropped[p] = support[q];
            }
        }
    }
    Ok((out, cropped))
}
fn weight_guide(
    c: &context::Contexts,
    d: SamplingDomain,
    mode: &str,
    base: usize,
    seed: u64,
) -> Result<(Planes, Vec<bool>)> {
    ensure!(d.x >= 8 && d.y >= 8, "guide halo before source");
    let expanded = SamplingDomain {
        full: d.full,
        x: d.x - 8,
        y: d.y - 8,
        width: 144,
        height: 144,
    };
    expanded.validate()?;
    let mut sampler = RegionSampler::new(expanded, 8 << 20)?;
    let mut sum: Planes = std::array::from_fn(|_| vec![0.; 144 * 144]);
    let mut valid = vec![true; 144 * 144];
    for pass in 0..2 {
        for offset in [-1isize, 11] {
            let i = (base as isize + offset) as usize + 299 * pass;
            let s = gather_at(
                c,
                expanded,
                [d.x as f64, d.y as f64],
                mode,
                base,
                i,
                seed,
                &mut sampler,
            )?;
            for color in 0..4 {
                for p in 0..144 * 144 {
                    sum[color][p] += s.planes[color][p] * c.gains[pass] * 0.25;
                    valid[p] &= s.support[p];
                }
            }
        }
    }
    finish_weight_guide(&sum, &valid, 144)
}
fn main() -> Result<()> {
    let args: Vec<_> = std::env::args().collect();
    ensure!(args.len() == 4, "RENDER NEW_OUT flat|all");
    let out = Path::new(&args[2]);
    fs::create_dir(out)?;
    let mut c = context::context(Path::new(&args[1]))?;
    ensure!(
        c.map.resampler() == Resampler::CatmullRom,
        "linear CatmullRom required"
    );
    let report: Value =
        serde_json::from_slice(&fs::read(Path::new(&args[1]).join("render-report.json"))?)?;
    let full = c.map.geometry();
    let d = SamplingDomain {
        full,
        x: full.width / 2 - 64,
        y: full.height / 2 - 64,
        width: 128,
        height: 128,
    };
    let modes = if args[3] == "flat" {
        vec!["flat"]
    } else {
        vec!["flat", "quadratic", "cubic", "focus", "shift"]
    };
    let protocol = json!({"schema":"strehl.structure-observer-independent-risk-control.v1","command":args,"bindings":c.bindings,"roles":{"Q":[0,4,8],"V":[1,5,9],"R":[-2,2,6,10],"W":[-1,11],"M":[3,7]},"bases":[36,236],"seeds":[80,81],"exposure_arms":["repeat-gain1-1","synthetic-HDR-gain2.5335414-1"],"signal_divisors":[1,6],"energy_cutoff":model::LIMIT,"domain_quad":[d.x,d.y,128,128],"scope":"Synthetic exact original-u16 measured-trajectory and four production-core arms, disjoint current Q/V/R/W/M photons. No real measurement or cache read. Reference quadratic bias does not cancel; known truth reported alongside independent-R risk.","sources":{"driver":sha(include_bytes!("real-noise-consumer-structure-risk.rs")),"model":sha(include_bytes!("real-noise-consumer-structure-model.rs")),"operator":sha(include_bytes!("real-noise-consumer-structure-operator.rs")),"consumer":sha(include_bytes!("real-noise-consumer-structure-consumer.rs"))}});
    write(&out.join("protocol-frozen.json"), &protocol)?;
    let pool = rayon::ThreadPoolBuilder::new().num_threads(4).build()?;
    let mut summary = Vec::new();
    for mode in modes {
        let mut rows = Vec::new();
        for base in [36usize, 236] {
            for seed in [80u64, 81] {
                for hdr in [false, true] {
                    for divisor in [1f32, 6.] {
                        c.gains = [if hdr { 2.5335414 * divisor } else { divisor }, divisor];
                        let mut sampler = RegionSampler::new(d, 8 << 20)?;
                        let (mask, qualification) =
                            pool.install(|| eligible(&c, d, mode, base, seed, &mut sampler))?;
                        // Mask is frozen before generating any W, R or M photons. Every
                        // selected pixel remains in every arm, including core fallback.
                        let (guide, valid) = weight_guide(&c, d, mode, base, seed)?;
                        let mut references: [Planes; 2] = std::array::from_fn(|_| zero());
                        for pass in 0..2 {
                            for (j, offset) in [-2isize, 2, 6, 10].into_iter().enumerate() {
                                let i = (base as isize + offset) as usize + 299 * pass;
                                let s = gather(&c, d, mode, base, i, seed, &mut sampler)?;
                                for state in 0..2 {
                                    let h = r_weights([3., 7.][state])[j] as f32 * 0.5;
                                    for color in 0..4 {
                                        for p in 0..N {
                                            ensure!(
                                                s.support[p] || !mask[color][p],
                                                "invalid fixed-mask reference"
                                            );
                                            references[state][color][p] +=
                                                h * s.planes[color][p] * c.gains[pass];
                                        }
                                    }
                                }
                            }
                        }
                        let mut outcomes = Vec::new();
                        for offset in [3, 7] {
                            let indices = [base + offset, base + offset + 299];
                            outcomes.push(pool.install(|| {
                                consumer::produce(
                                    &c,
                                    &report,
                                    indices,
                                    &guide,
                                    &valid,
                                    base - 1,
                                    |i| gather(&c, d, mode, base, i, seed, &mut sampler),
                                )
                            })?);
                        }
                        for state in 0..2 {
                            let common_truth = truth(mode, [3., 7.][state]);
                            let baseline = &outcomes[state][2].planes;
                            let precise = &outcomes[state][3].planes;
                            let blur = smooth(precise, 1);
                            for (name, arm) in [
                                "pass0",
                                "pass1",
                                "equal",
                                "precision",
                                "constant",
                                "blur",
                                "mild-blur",
                                "shift",
                            ]
                            .into_iter()
                            .enumerate()
                            {
                                for color in 0..4 {
                                    let mut n = 0usize;
                                    let mut risk = 0.;
                                    let mut true_risk = 0.;
                                    let mut ref_bias = 0.;
                                    let mut transfer = 0.;
                                    let mut den = 0.;
                                    let mut bias = 0.;
                                    let mut mse = 0.;
                                    let mut ref_mse = 0.;
                                    for p in 0..N {
                                        if !mask[color][p] {
                                            continue;
                                        }
                                        ensure!(
                                            outcomes[state].iter().all(|o| o.valid[p]),
                                            "invalid delivered fixed-mask pixel"
                                        );
                                        let v = match name {
                                            0..=3 => outcomes[state][name].planes[color][p],
                                            4 => 1200.,
                                            5 => blur[color][p],
                                            6 => 0.85 * precise[color][p] + 0.15 * blur[color][p],
                                            _ => precise[color][p + 1],
                                        };
                                        let a = f64::from(v);
                                        let b = f64::from(baseline[color][p]);
                                        let r = f64::from(references[state][color][p]);
                                        let t = f64::from(common_truth[color][p]);
                                        risk += (a - r).powi(2) - (b - r).powi(2);
                                        true_risk += (a - t).powi(2) - (b - t).powi(2);
                                        ref_bias += r - t;
                                        bias += a - t;
                                        mse += (a - t).powi(2);
                                        ref_mse += (r - t).powi(2);
                                        transfer += (a - 1200.) * (t - 1200.);
                                        den += (t - 1200.).powi(2);
                                        n += 1;
                                    }
                                    let scale = n.max(1) as f64;
                                    rows.push(json!({"mode":mode,"base":base,"seed":seed,"hdr":hdr,"divisor":divisor,"state":state,"arm":arm,"color":color,"fixed_pixels":n,"independent_reference_risk_delta_vs_equal":risk/scale,"known_truth_risk_delta_vs_equal":true_risk/scale,"output_truth_mse":mse/scale,"reference_truth_mse":ref_mse/scale,"mean_reference_bias_dn":ref_bias/scale,"mean_output_bias_dn":bias/scale,"known_signal_projection":if den>0.{json!(transfer/den)}else{Value::Null}}));
                                }
                            }
                        }
                        write(
                            &out.join(format!("mask-{mode}-{base}-{seed}-{hdr}-{divisor}.json")),
                            &qualification,
                        )?;
                    }
                }
            }
        }
        write(&out.join(format!("{mode}.json")), &json!({"rows":rows}))?;
        let active = rows
            .iter()
            .filter(|r| r["fixed_pixels"].as_u64().unwrap() > 0)
            .count();
        println!(
            "{mode}: {active}/{} output component observations with frozen Q/V support",
            rows.len()
        );
        summary.push(json!({"mode":mode,"active_rows":active,"rows":rows.len()}));
    }
    write(
        &out.join("report.json"),
        &json!({"protocol_sha256":sha(&fs::read(out.join("protocol-frozen.json"))?),"summary":summary,"workers":4,"raw_decodes":0,"cache_reads":0,"note":"Risk deltas are reported for every fixed-mask arm. Analyze by independent synthetic acquisition seed/window, not pixel count. Two temporal outputs per case are correlated through guides/reference. No real SNR claim."}),
    )?;
    Ok(())
}
#[test]
fn independent_r_weights_reproduce_known_quadratic() {
    for t in [1., 3., 5., 7., 9.] {
        let v = [-2f64, 2., 6., 10.].map(|x| 12. + 3. * x - 0.7 * x * x);
        let y = r_weights(t).iter().zip(v).map(|(h, v)| h * v).sum::<f64>();
        assert!((y - (12. + 3. * t - 0.7 * t * t)).abs() < 1e-10);
    }
}

#[test]
fn a00_real_smoothing_wrapper_preserves_flat_and_two_dimensional_impulse() {
    let flat = std::array::from_fn(|c| vec![1200. + c as f32; N]);
    for radius in [1, 8] {
        let result = smooth(&flat, radius);
        assert_eq!(result, flat);
        let mut p = zero();
        for plane in &mut p {
            plane[64 * 128 + 64] = ((2 * radius + 1) * (2 * radius + 1)) as f32;
        }
        let result = smooth(&p, radius);
        for plane in result {
            for y in 16..112 {
                for x in 16..112 {
                    assert_eq!(
                        plane[y * 128 + x],
                        if x.abs_diff(64) <= radius && y.abs_diff(64) <= radius {
                            1.
                        } else {
                            0.
                        }
                    );
                }
            }
        }
    }
}

#[test]
fn guide_halo_only_poison_is_not_marked_supported() {
    let mut p: Planes = std::array::from_fn(|_| vec![1200.; 144 * 144]);
    let mut valid = vec![true; 144 * 144];
    let poison = 72 * 144 + 79;
    valid[poison] = false;
    for c in 0..4 {
        p[c][poison] = 50000.;
    }
    assert!(valid[72 * 144 + 72]);
    let (out, support) = finish_weight_guide(&p, &valid, 144).unwrap();
    assert!(out[0][64 * 128 + 64] > 1200.);
    assert!(!support[64 * 128 + 64]);
    assert!(support[64 * 128 + 90]);
    assert_eq!(out[0][64 * 128 + 90], 1200.);
}
#[test]
fn missing_weight_guide_uses_actual_equal_fallback_bits() {
    let c = context::context(Path::new("outputs/multi-stack/insect-repeat-7")).unwrap();
    let report: Value = serde_json::from_slice(
        &fs::read("outputs/multi-stack/insect-repeat-7/render-report.json").unwrap(),
    )
    .unwrap();
    let full = c.map.geometry();
    let d = SamplingDomain {
        full,
        x: full.width / 2 - 64,
        y: full.height / 2 - 64,
        width: 128,
        height: 128,
    };
    let guide = std::array::from_fn(|_| vec![50000.; N]);
    let valid = vec![false; N];
    let mut sampler = RegionSampler::new(d, 8 << 20).unwrap();
    let produced = consumer::produce(&c, &report, [39, 338], &guide, &valid, 35, |i| {
        gather(&c, d, "quadratic", 36, i, 73, &mut sampler)
    })
    .unwrap();
    for color in 0..4 {
        assert!(
            produced[2].planes[color]
                .iter()
                .zip(&produced[3].planes[color])
                .all(|(a, b)| a.to_bits() == b.to_bits())
        );
    }
    assert_eq!(produced[2].valid, produced[3].valid);
}
