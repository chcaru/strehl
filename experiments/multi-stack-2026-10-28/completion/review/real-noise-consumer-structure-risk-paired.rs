//! Asymmetric bases and separate per-pass independent target controls.
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
use strehl_core::{CfaPlane, boxfilter::box_mean};
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

fn sample(
    c: &context::Contexts,
    d: SamplingDomain,
    origin: [f64; 2],
    bases: [usize; 2],
    modes: [&str; 2],
    index: usize,
    seed: u64,
    sampler: &mut RegionSampler,
) -> Result<SampledCfa> {
    let pass = usize::from(index >= 299);
    let ordinal = index - 299 * pass;
    let t = c.map.warps()[index].placed().context("unplaced")?;
    let raw = operator::plant_at(
        d,
        origin,
        t,
        c.profiles[pass],
        &c.noise[pass],
        c.gains[pass],
        modes[pass],
        (ordinal as isize - bases[pass] as isize) as f32,
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
        coverage: s.coverage.clone(),
        clipped: s.clipped.clone(),
        support: s.support.clone(),
    })
}
fn common_truth(mode: &str, t: f64) -> Planes {
    std::array::from_fn(|color| {
        let (dx, dy) = CfaPlane::ALL[color].rggb_offset();
        (0..N)
            .map(|i| {
                operator::truth(
                    mode,
                    t,
                    color,
                    (i % 128) as f64 + dx as f64 * 0.5 - 0.25,
                    (i / 128) as f64 + dy as f64 * 0.5 - 0.25,
                ) as f32
            })
            .collect()
    })
}
fn main() -> Result<()> {
    let args: Vec<_> = std::env::args().collect();
    ensure!(args.len() == 4, "RENDER NEW_OUT flat|all");
    let out = Path::new(&args[2]);
    fs::create_dir(out)?;
    let render = Path::new(&args[1]);
    let mut c = context::context(render)?;
    let report: Value = serde_json::from_slice(&fs::read(render.join("render-report.json"))?)?;
    let d = SamplingDomain {
        full: c.map.geometry(),
        x: 969,
        y: 1029,
        width: 128,
        height: 128,
    };
    let origin = [d.x as f64, d.y as f64];
    let bases = [106usize, 97];
    let cases = if args[3] == "flat" {
        vec![("flat", ["flat", "flat"])]
    } else {
        vec![
            ("flat", ["flat", "flat"]),
            ("common", ["quadratic", "quadratic"]),
            ("unequal", ["quadratic", "quadratic-unequal"]),
            ("opposite", ["quadratic", "quadratic-opposite"]),
            ("slope", ["quadratic", "quadratic-slope"]),
        ]
    };
    write(
        &out.join("protocol-frozen.json"),
        &json!({"schema":"strehl.structure-risk-asymmetric.v1","command":args,"bases":bases,"centers":[110,101],"domain_quad":[969,1029,128,128],"roles":{"Q":[0,4,8],"V":[1,5,9],"R":[-2,2,6,10],"W":[-1,11],"M":[3,7]},"seeds":[90,91],"exposure_arms":[[1,1],[2.5335414,1]],"signal_divisor":6,"bindings":c.bindings,"driver_sha256":sha(include_bytes!("real-noise-consumer-structure-risk-paired.rs")),"operator_sha256":sha(include_bytes!("real-noise-consumer-structure-operator.rs")),"scope":"Synthetic unequal physical signals, exact measured asymmetric geometry and four core arms; reference trajectories remain separate. Single-pass outputs define observer reference targets. Actual optional-primary behavior is not exercised. No real R/M reads."}),
    )?;
    let pool = rayon::ThreadPoolBuilder::new().num_threads(4).build()?;
    let mut totals = Vec::new();
    for (name, modes) in cases {
        let mut rows = Vec::new();
        let mut producer_diagnostics = Vec::new();
        let mut swap_max = 0f64;
        for seed in [90u64, 91] {
            for hdr in [false, true] {
                c.gains = [if hdr { 2.5335414 * 6. } else { 6. }, 6.];
                let mut sampler = RegionSampler::new(d, 8 << 20)?;
                let mut quals = Vec::new();
                for pass in 0..2 {
                    let mut gate = model::Gate::new();
                    for (role, offsets) in [("Q", [0, 4, 8]), ("V", [1, 5, 9])] {
                        for (j, o) in offsets.into_iter().enumerate() {
                            let index = bases[pass] + o + 299 * pass;
                            let s = sample(&c, d, origin, bases, modes, index, seed, &mut sampler)?;
                            let beta = operator::beta(
                                d,
                                c.map.warps()[index].placed().unwrap(),
                                c.profiles[pass],
                            );
                            if role == "Q" {
                                gate.q(j, &s.planes, &s.support, &beta, c.gains[pass])?;
                            } else {
                                gate.v(j, &s.planes, &s.support, &beta, c.gains[pass])?;
                            }
                        }
                    }
                    quals.push(gate.finish(&c.noise[pass], c.gains[pass])?);
                }
                let mut mask: [Vec<bool>; 4] = std::array::from_fn(|_| vec![false; N]);
                for row in 0..36 {
                    if quals[0][row]["accepted"] == true && quals[1][row]["accepted"] == true {
                        let color = row % 4;
                        let x = quals[0][row]["tile_quad"][0].as_u64().unwrap() as usize;
                        let y = quals[0][row]["tile_quad"][1].as_u64().unwrap() as usize;
                        for yy in y..y + 32 {
                            for xx in x..x + 32 {
                                mask[color][yy * 128 + xx] = true;
                            }
                        }
                    }
                }
                // Q/V mask frozen before independent R/W/M photons.
                let expanded = SamplingDomain {
                    full: d.full,
                    x: d.x - 8,
                    y: d.y - 8,
                    width: 144,
                    height: 144,
                };
                let mut es = RegionSampler::new(expanded, 8 << 20)?;
                let mut sum: Planes = std::array::from_fn(|_| vec![0.; 144 * 144]);
                let mut support = vec![true; 144 * 144];
                for pass in 0..2 {
                    for o in [-1isize, 11] {
                        let index = (bases[pass] as isize + o) as usize + 299 * pass;
                        let s = sample(&c, expanded, origin, bases, modes, index, seed, &mut es)?;
                        for color in 0..4 {
                            for p in 0..144 * 144 {
                                sum[color][p] += s.planes[color][p] * c.gains[pass] * 0.25;
                                support[p] &= s.support[p];
                            }
                        }
                    }
                }
                let (guide, guide_support) = finish_weight_guide(&sum, &support, 144)?;
                let mut refs: [[Planes; 2]; 2] =
                    std::array::from_fn(|_| std::array::from_fn(|_| zero()));
                for pass in 0..2 {
                    for (j, o) in [-2isize, 2, 6, 10].into_iter().enumerate() {
                        let index = (bases[pass] as isize + o) as usize + 299 * pass;
                        let s = sample(&c, d, origin, bases, modes, index, seed, &mut sampler)?;
                        for state in 0..2 {
                            let h = r_weights([3., 7.][state])[j] as f32;
                            for color in 0..4 {
                                for p in 0..N {
                                    ensure!(
                                        s.support[p] || !mask[color][p],
                                        "invalid fixed-mask R"
                                    );
                                    refs[pass][state][color][p] +=
                                        h * s.planes[color][p] * c.gains[pass];
                                }
                            }
                        }
                    }
                }
                let mut swapped = context::context(render)?;
                swapped.noise.swap(0, 1);
                swapped.gains = [c.gains[1], c.gains[0]];
                for (state, o) in [3usize, 7].into_iter().enumerate() {
                    let indices = [bases[0] + o, bases[1] + o + 299];
                    let produced = pool.install(|| {
                        consumer::produce(
                            &c,
                            &report,
                            indices,
                            &guide,
                            &guide_support,
                            bases[0] - 1,
                            |i| sample(&c, d, origin, bases, modes, i, seed, &mut sampler),
                        )
                    })?;
                    producer_diagnostics.push(json!({"seed":seed,"hdr":hdr,"state":state,"source_indices":indices,"arms":produced.iter().enumerate().map(|(i,o)|json!({"arm":(["pass0","pass1","equal","precision"][i]),"diagnostics":o.diagnostics,"valid_output_count":o.valid.iter().filter(|v|**v).count()})).collect::<Vec<_>>()}));
                    let permuted = pool.install(|| {
                        consumer::produce(
                            &swapped,
                            &report,
                            [indices[1], indices[0]],
                            &guide,
                            &guide_support,
                            bases[0] - 1,
                            |i| sample(&c, d, origin, bases, modes, i, seed, &mut sampler),
                        )
                    })?;
                    for color in 0..4 {
                        for p in 0..N {
                            swap_max = swap_max.max(f64::from(
                                (produced[3].planes[color][p] - permuted[3].planes[color][p]).abs(),
                            ));
                        }
                    }
                    let blur = smooth(&produced[3].planes, 1);
                    let truth = [
                        common_truth(modes[0], [3., 7.][state]),
                        common_truth(modes[1], [3., 7.][state]),
                    ];
                    for (arm_index, arm) in [
                        "pass0",
                        "pass1",
                        "equal",
                        "precision",
                        "constant",
                        "blue-only-blur",
                    ]
                    .into_iter()
                    .enumerate()
                    {
                        for target in 0..2 {
                            for color in 0..4 {
                                let mut n = 0;
                                let mut risk = 0.;
                                let mut known = 0.;
                                let mut mse = 0.;
                                let mut projection = 0.;
                                let mut den = 0.;
                                let mut average_risk = 0.;
                                for p in 0..N {
                                    if !mask[color][p] {
                                        continue;
                                    }
                                    ensure!(
                                        produced.iter().all(|v| v.valid[p]),
                                        "invalid delivered mask"
                                    );
                                    let a = f64::from(match arm_index {
                                        0..=3 => produced[arm_index].planes[color][p],
                                        4 => 1200.,
                                        _ => {
                                            if color == 2 {
                                                blur[color][p]
                                            } else {
                                                produced[3].planes[color][p]
                                            }
                                        }
                                    });
                                    let baseline = f64::from(produced[target].planes[color][p]);
                                    let r = f64::from(refs[target][state][color][p]);
                                    let t = f64::from(truth[target][color][p]);
                                    let averaged = f64::from(
                                        (refs[0][state][color][p] + refs[1][state][color][p]) * 0.5,
                                    );
                                    risk += (a - r).powi(2) - (baseline - r).powi(2);
                                    known += (a - t).powi(2) - (baseline - t).powi(2);
                                    mse += (a - t).powi(2);
                                    projection += (a - 1200.) * (t - 1200.);
                                    den += (t - 1200.).powi(2);
                                    average_risk += (a - averaged).powi(2);
                                    n += 1;
                                }
                                let scale = n.max(1) as f64;
                                rows.push(json!({"case":name,"seed":seed,"hdr":hdr,"state":state,"arm":arm,"target_pass":target,"color":color,"fixed_pixels":n,"independent_risk_delta_vs_target_single_pass":risk/scale,"known_risk_delta_vs_target_single_pass":known/scale,"known_mse":mse/scale,"projection":if den>0.{json!(projection/den)}else{Value::Null},"invalid_averaged_reference_mse_for_foil_only":average_risk/scale}));
                            }
                        }
                    }
                }
                write(
                    &out.join(format!("qualification-{name}-{seed}-{hdr}.json")),
                    &json!({"passes":quals}),
                )?;
            }
        }
        ensure!(
            swap_max <= 0.005,
            "pass label permutation changes consuming result more than0.005DN: {swap_max}"
        );
        println!("{name}: {} rows, pass-swap maximum{swap_max}DN", rows.len());
        write(
            &out.join(format!("{name}.json")),
            &json!({"rows":rows,"pass_swap_max_abs_dn":swap_max,"producer_diagnostics":producer_diagnostics}),
        )?;
        totals.push(json!({"case":name,"rows":rows.len(),"pass_swap_max_abs_dn":swap_max}));
    }
    write(
        &out.join("report.json"),
        &json!({"totals":totals,"workers":4,"cache_reads":0,"raw_decodes":0,"real_signal_reads":0}),
    )?;
    Ok(())
}
