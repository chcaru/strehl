//! Synthetic same-acquisition Q/guide preparation and exact four-arm core call.
//! Parent supplies frozen content-bound source indices; no real source I/O here.
use super::{context, model, operator, temporal};
#[path = "real-noise-consumer-structure-consumer.rs"]
mod consumer;
use anyhow::{Context, Result, ensure};
use serde_json::{Value, json};
use strehl_cli::{
    session_reconstruction_sampling::RegionSampler,
    session_sampling::{SampledCfa, SamplingDomain},
};
use strehl_core::{CfaPlane, boxfilter::box_mean, plane::PlaneGeometry};
pub type Planes = [Vec<f32>; 4];
const N: usize = 128 * 128;
pub struct Case {
    pub masks: [Vec<bool>; 4],
    pub qualification: Value,
    pub outcomes: Vec<consumer::Outcome>,
    pub references: [Planes; 2],
    pub truths: [Planes; 2],
    pub qv_reads: Vec<usize>,
    pub r_reads: Vec<usize>,
    pub m_reads: Vec<usize>,
}
fn zero() -> Planes {
    std::array::from_fn(|_| vec![0.; N])
}
fn owned(s: &SampledCfa) -> SampledCfa {
    SampledCfa {
        planes: s.planes.clone(),
        coverage: s.coverage.clone(),
        support: s.support.clone(),
        clipped: s.clipped.clone(),
    }
}
fn crop(s: &SampledCfa, width: usize) -> SampledCfa {
    let positions: Vec<_> = (0..N)
        .map(|i| (i / 128 + 8) * width + i % 128 + 8)
        .collect();
    SampledCfa {
        planes: std::array::from_fn(|c| positions.iter().map(|&i| s.planes[c][i]).collect()),
        coverage: positions.iter().map(|&i| s.coverage[i]).collect(),
        support: positions.iter().map(|&i| s.support[i]).collect(),
        clipped: positions.iter().map(|&i| s.clipped[i]).collect(),
    }
}
pub fn smooth(p: &Planes, radius: usize) -> Planes {
    let g = PlaneGeometry {
        width: 128,
        height: 128,
    };
    let mut scratch = vec![0.; N];
    std::array::from_fn(|c| {
        let mut out = vec![0.; N];
        box_mean(&p[c], g, radius, &mut scratch, &mut out);
        out
    })
}
pub fn finish_guide(sum: &Planes, support: &[bool]) -> Result<(Planes, Vec<bool>)> {
    let g = PlaneGeometry {
        width: 144,
        height: 144,
    };
    ensure!(
        sum.iter().all(|p| p.len() == g.pixels()) && support.len() == g.pixels(),
        "guide full halo"
    );
    let mut s = vec![0.; g.pixels()];
    let mut blurred = vec![0.; g.pixels()];
    let mut temp = vec![0u32; g.pixels()];
    let mut all = vec![false; g.pixels()];
    strehl_cli::session_focus::complete_support(support, g, 8, &mut temp, &mut all)?;
    let mut output = zero();
    let mut valid = vec![false; N];
    for c in 0..4 {
        box_mean(&sum[c], g, 8, &mut s, &mut blurred);
        for i in 0..N {
            let j = (i / 128 + 8) * 144 + i % 128 + 8;
            output[c][i] = blurred[j];
            valid[i] = all[j];
        }
    }
    Ok((output, valid))
}
fn signal(mode: &str, normalized: f64, level: f64) -> (&str, f64, f64) {
    let brightness = match mode {
        "linear" => 1. + 0.12 * normalized,
        "quadratic" => 1. + 0.40 * normalized * normalized,
        _ => 1.,
    };
    let kind = match mode {
        "linear" | "quadratic" => "stationary",
        _ => mode,
    };
    (kind, 1200. / level / brightness, normalized * 8.)
}
fn gather(
    c: &context::Contexts,
    d: SamplingDomain,
    origin: [f64; 2],
    mode: &str,
    time: f64,
    level: f64,
    index: usize,
    seed: u64,
) -> Result<SampledCfa> {
    let pass = usize::from(index >= 16);
    let t = c.map.warps()[index].placed().context("placed source")?;
    let (kind, divisor, temporal) = signal(mode, time, level);
    let raw = operator::plant_at(
        d,
        origin,
        t,
        c.profiles[pass],
        &c.noise[pass],
        divisor as f32,
        kind,
        temporal as f32,
        if seed == 0 {
            0
        } else {
            seed * 53139 + index as u64 * 7919
        },
    )?;
    let mut sampler = RegionSampler::new(d, 8 << 20)?;
    Ok(owned(sampler.gather(
        &raw,
        c.noise[pass].plane(CfaPlane::R).levels,
        t,
        c.profiles[pass],
        c.map.resampler(),
    )?))
}
fn truth(mode: &str, time: f64, level: f64) -> Planes {
    let (kind, divisor, temporal) = signal(mode, time, level);
    std::array::from_fn(|c| {
        let (dx, dy) = CfaPlane::ALL[c].rggb_offset();
        (0..N)
            .map(|i| {
                (operator::truth(
                    kind,
                    temporal,
                    c,
                    (i % 128) as f64 + dx as f64 * 0.5 - 0.25,
                    (i / 128) as f64 + dy as f64 * 0.5 - 0.25,
                ) / divisor) as f32
            })
            .collect()
    })
}
/// All eight original roles are read exactly once. Q is gathered with full
/// guide halo ONCE; its central128 is the exact same photons used by Gate.
pub fn produce(
    c: &context::Contexts,
    report: &Value,
    d: SamplingDomain,
    indices: [usize; 8],
    times: [f64; 8],
    mode: &str,
    level: f64,
    seed: u64,
    reference_seed: Option<u64>,
    missing_guide: bool,
) -> Result<Case> {
    ensure!(
        indices
            .iter()
            .copied()
            .collect::<std::collections::BTreeSet<_>>()
            .len()
            == 8,
        "role acquisitions overlap"
    );
    ensure!(c.gains == [1., 1.], "same-exposure repeat plant");
    let temporal = temporal::Times {
        q: [times[0], times[7]],
        v: [times[1], times[6]],
        r: [times[2], times[5]],
        m: [times[3], times[4]],
    };
    temporal.validate().map_err(anyhow::Error::msg)?;
    let norm = |i: usize| (times[i] - times[0]) / (times[7] - times[0]);
    let expanded = SamplingDomain {
        full: d.full,
        x: d.x.checked_sub(8).context("guide x")?,
        y: d.y.checked_sub(8).context("guide y")?,
        width: 144,
        height: 144,
    };
    expanded.validate()?;
    let origin = [d.x as f64, d.y as f64];
    let mut gate = model::Gate::new(temporal)?;
    let mut guide: Planes = std::array::from_fn(|_| vec![0.; 144 * 144]);
    let mut support = vec![true; 144 * 144];
    let mut qv_reads = Vec::new();
    let mid = (times[3] + times[4]) * 0.5;
    let guide_weights = temporal::weights(temporal.q, mid).map_err(anyhow::Error::msg)?;
    for (j, offset) in [0usize, 7].into_iter().enumerate() {
        let index = indices[offset];
        let s = gather(c, expanded, origin, mode, norm(offset), level, index, seed)?;
        let central = crop(&s, 144);
        let pass = usize::from(index >= 16);
        let beta = operator::beta(d, c.map.warps()[index].placed().unwrap(), c.profiles[pass]);
        gate.q(j, &central.planes, &central.support, &beta)?;
        for color in 0..4 {
            for pixel in 0..144 * 144 {
                guide[color][pixel] += guide_weights[j] as f32 * s.planes[color][pixel];
                support[pixel] &= s.support[pixel];
            }
        }
        qv_reads.push(index);
    }
    for (j, offset) in [1usize, 6].into_iter().enumerate() {
        let index = indices[offset];
        let s = gather(c, d, origin, mode, norm(offset), level, index, seed)?;
        let pass = usize::from(index >= 16);
        let beta = operator::beta(d, c.map.warps()[index].placed().unwrap(), c.profiles[pass]);
        gate.v(j, &s.planes, &s.support, &beta)?;
        qv_reads.push(index);
    }
    let rows = gate.finish(&c.noise[0], 1.10)?;
    let mut masks = std::array::from_fn(|_| vec![false; N]);
    for row in &rows {
        if row["accepted"] == true {
            let color = row["color"].as_u64().unwrap() as usize;
            let x = row["tile_quad"][0].as_u64().unwrap() as usize;
            let y = row["tile_quad"][1].as_u64().unwrap() as usize;
            for yy in y..y + 32 {
                for xx in x..x + 32 {
                    masks[color][yy * 128 + xx] = true;
                }
            }
        }
    }
    let (guide, mut valid) = finish_guide(&guide, &support)?;
    if missing_guide {
        valid.fill(false);
    }
    // Candidate creation precedes any R photons. The reference seed can change
    // without entering Q/V, guide, consumer sampling or candidate diagnostics.
    let mut m_reads = Vec::new();
    let outcomes = consumer::produce(
        c,
        report,
        [indices[3], indices[4]],
        &guide,
        &valid,
        indices[0],
        |index| {
            let offset = if index == indices[3] {
                3
            } else if index == indices[4] {
                4
            } else {
                anyhow::bail!("consumer read outsideM")
            };
            m_reads.push(index);
            gather(c, d, origin, mode, norm(offset), level, index, seed)
        },
    )?;
    let mut references = [zero(), zero()];
    let mut r_reads = Vec::new();
    for (j, offset) in [2usize, 5].into_iter().enumerate() {
        let index = indices[offset];
        let s = gather(
            c,
            d,
            origin,
            mode,
            norm(offset),
            level,
            index,
            reference_seed.unwrap_or(seed),
        )?;
        for state in 0..2 {
            let weight = temporal::weights(temporal.r, temporal.m[state])
                .map_err(anyhow::Error::msg)?[j] as f32;
            for color in 0..4 {
                for pixel in 0..N {
                    ensure!(
                        s.support[pixel] || !masks[color][pixel],
                        "reference unsupported on fixed mask"
                    );
                    references[state][color][pixel] += weight * s.planes[color][pixel];
                }
            }
        }
        r_reads.push(index);
    }
    ensure!(m_reads == [indices[3], indices[4]], "eachMloadedonce");
    Ok(Case {
        masks,
        qualification: json!(rows),
        outcomes,
        references,
        truths: [truth(mode, norm(3), level), truth(mode, norm(4), level)],
        qv_reads,
        r_reads,
        m_reads,
    })
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn flat_guide_has_exact_value_and_halo_poison_refuses() {
        let p: Planes = std::array::from_fn(|_| vec![1200.; 144 * 144]);
        let mut s = vec![true; 144 * 144];
        let (g, v) = finish_guide(&p, &s).unwrap();
        assert!(g.iter().flatten().all(|x| *x == 1200.));
        assert!(v.iter().all(|x| *x));
        // Outside central crop, but inside output(0,0)'s radius8 dependence.
        s[0] = false;
        let (_, v) = finish_guide(&p, &s).unwrap();
        assert!(!v[0]);
        assert!(v[32 * 128 + 32]);
    }
}
