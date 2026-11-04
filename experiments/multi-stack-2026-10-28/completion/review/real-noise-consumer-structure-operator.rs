//! Original-u16 synthetic controls with exact production CFA coordinates.
use anyhow::{Context, Result, ensure};
use strehl_cli::session_sampling::SamplingDomain;
use strehl_core::{
    CfaPlane,
    align::Similarity,
    noise::NoiseModel,
    optics::{OpticalProfile, cfa_site_channel},
    plane::{PlaneGeometry, QuadSource},
};
const SIDE: usize = 128;
fn uniform(s: &mut u64) -> f32 {
    *s ^= *s << 13;
    *s ^= *s >> 7;
    *s ^= *s << 17;
    (((*s >> 40) as u32) as f32 + 0.5) / 16777216.
}
fn gaussian(s: &mut u64) -> f32 {
    (-2. * uniform(s).ln()).sqrt() * (std::f32::consts::TAU * uniform(s)).cos()
}
pub(crate) struct Plant {
    full: PlaneGeometry,
    first_y: usize,
    rows: Vec<u16>,
}
impl QuadSource for Plant {
    fn geometry(&self) -> PlaneGeometry {
        self.full
    }
    fn quad_rows(&self, y: usize) -> (&[u16], &[u16]) {
        let row = 2 * (y - self.first_y) * 2 * self.full.width;
        let w = 2 * self.full.width;
        (&self.rows[row..row + w], &self.rows[row + w..row + 2 * w])
    }
}
pub(crate) fn plant(
    domain: SamplingDomain,
    t: Similarity,
    p: Option<&OpticalProfile>,
    noise: &NoiseModel,
    gain: f32,
    mode: &str,
    temporal: f32,
    seed: u64,
) -> Result<Plant> {
    plant_at(
        domain,
        [domain.x as f64, domain.y as f64],
        t,
        p,
        noise,
        gain,
        mode,
        temporal,
        seed,
    )
}
pub(crate) fn plant_at(
    domain: SamplingDomain,
    signal_origin: [f64; 2],
    t: Similarity,
    p: Option<&OpticalProfile>,
    noise: &NoiseModel,
    gain: f32,
    mode: &str,
    temporal: f32,
    seed: u64,
) -> Result<Plant> {
    let pulls: [Similarity; 4] = std::array::from_fn(|c| {
        let (dx, dy) = CfaPlane::ALL[c].rggb_offset();
        OpticalProfile::compose(p, cfa_site_channel(dx, dy), t)
    });
    let full = domain.full;
    let center = [full.width as f64 * 0.5, full.height as f64 * 0.5];
    let mut bounds = [
        f64::INFINITY,
        f64::INFINITY,
        f64::NEG_INFINITY,
        f64::NEG_INFINITY,
    ];
    for (c, t) in pulls.iter().enumerate() {
        let (dx, dy) = CfaPlane::ALL[c].rggb_offset();
        let site = [dx as f64 * 0.5 - 0.25, dy as f64 * 0.5 - 0.25];
        for (x, y) in [
            (domain.x, domain.y),
            (domain.x + domain.width - 1, domain.y),
            (domain.x, domain.y + domain.height - 1),
            (domain.x + domain.width - 1, domain.y + domain.height - 1),
        ] {
            let q = t.apply_at(x as f64 + site[0], y as f64 + site[1], center[0], center[1]);
            bounds[0] = bounds[0].min(q.0 - site[0]);
            bounds[1] = bounds[1].min(q.1 - site[1]);
            bounds[2] = bounds[2].max(q.0 - site[0]);
            bounds[3] = bounds[3].max(q.1 - site[1]);
        }
    }
    let x0 = (bounds[0].floor() - 8.).max(0.) as usize;
    let y0 = (bounds[1].floor() - 8.).max(0.) as usize;
    let x1 = (bounds[2].ceil() + 9.).min(full.width as f64) as usize;
    let y1 = (bounds[3].ceil() + 9.).min(full.height as f64) as usize;
    ensure!(
        x1 > x0 && y1 > y0 && x1 - x0 < 384 && y1 - y0 < 384,
        "unbounded plant rectangle"
    );
    let mut out = Plant {
        full,
        first_y: y0,
        rows: vec![65535; 4 * full.width * (y1 - y0)],
    };
    let mut rng = seed.wrapping_mul(0x9e3779b97f4a7c15) | 1;
    for (c, t) in pulls.iter().enumerate() {
        let inverse = t.invert().context("singular pull")?;
        let (dx, dy) = CfaPlane::ALL[c].rggb_offset();
        let site = [dx as f64 * 0.5 - 0.25, dy as f64 * 0.5 - 0.25];
        for y in y0..y1 {
            for x in x0..x1 {
                let q =
                    inverse.apply_at(x as f64 + site[0], y as f64 + site[1], center[0], center[1]);
                let xx = (q.0 - signal_origin[0]) as f32;
                let yy = (q.1 - signal_origin[1]) as f32;
                let common = truth(mode, temporal as f64, c, xx as f64, yy as f64) as f32;
                let signal = common / gain;
                let pn = noise.plane(CfaPlane::ALL[c]);
                let v = signal
                    + if seed == 0 {
                        0.
                    } else {
                        gaussian(&mut rng) * pn.variance(signal).sqrt()
                    }
                    + pn.levels.black;
                out.rows[(2 * (y - y0) + dy) * 2 * full.width + 2 * x + dx] = if mode == "clipped" {
                    pn.levels.white as u16
                } else {
                    v.round().clamp(0., 65535.) as u16
                };
            }
        }
    }
    Ok(out)
}

/// Known colored two-dimensional signal in continuous reference quad coordinates.
/// Frequencies up to1.11rad/quad (~.177cycles/CFA-plane pixel), well above old .11.
pub fn truth(mode: &str, t: f64, c: usize, x: f64, y: f64) -> f64 {
    let phase = [0.1, 0.7, 1.3, 1.9][c];
    let z = (t - 4.) / 4. * if mode == "quadratic-slope" { 0.85 } else { 1. };
    let (xx, yy) = if mode == "shift" {
        (
            x + 1.5 * (t >= 5.) as u8 as f64,
            y - 0.9 * (t >= 5.) as u8 as f64,
        )
    } else {
        (x, y)
    };
    let texture =
        90. * (0.73 * xx + 0.39 * yy + phase).sin() + 65. * (0.27 * xx - 1.11 * yy + phase).cos();
    let scale = match mode {
        "quadratic" | "quadratic-unequal" | "quadratic-opposite" | "quadratic-slope" => {
            1. + 0.12 * z - 0.16 * z * z
        }
        "cubic" => 1. + 0.42 * z * z * z,
        "focus" => (-2.2 * (z - 0.25).powi(2)).exp(),
        "step" => {
            if t >= 5. {
                0.1
            } else {
                1.
            }
        }
        _ => 1.,
    };
    if mode == "flat" {
        1200.
    } else {
        (if mode == "quadratic-unequal" {
            1260.
        } else {
            1200.
        }) + scale
            * texture
            * if mode == "quadratic-opposite" {
                -1.
            } else if mode == "quadratic-unequal" {
                0.8
            } else {
                1.
            }
            + if mode.starts_with("quadratic") {
                12. * z + 9. * z * z
            } else {
                0.
            }
    }
}
fn weights(f: f32) -> [f32; 4] {
    let f2 = f * f;
    let f3 = f2 * f;
    [
        -0.5 * f3 + f2 - 0.5 * f,
        1.5 * f3 - 2.5 * f2 + 1.,
        -1.5 * f3 + 2. * f2 + 0.5 * f,
        0.5 * f3 - 0.5 * f2,
    ]
}
/// Exact squared norm of the same linear original taps (no iid beta assumption).
/// Spatial covariance is not discarded into pixel-confidence intervals: the gate
/// aggregates fixed blocks and calibrates its false-refusal rate by acquisition.
pub fn beta(domain: SamplingDomain, t: Similarity, p: Option<&OpticalProfile>) -> [Vec<f64>; 4] {
    std::array::from_fn(|c| {
        let (dx, dy) = CfaPlane::ALL[c].rggb_offset();
        let site = [dx as f64 * 0.5 - 0.25, dy as f64 * 0.5 - 0.25];
        let pull = OpticalProfile::compose(p, cfa_site_channel(dx, dy), t);
        (0..domain.width * domain.height)
            .map(|i| {
                let q = pull.apply_at(
                    (domain.x + i % domain.width) as f64 + site[0],
                    (domain.y + i / domain.width) as f64 + site[1],
                    domain.full.width as f64 * 0.5,
                    domain.full.height as f64 * 0.5,
                );
                let x = q.0 - site[0];
                let y = q.1 - site[1];
                let wx = weights((x - x.floor()) as f32);
                let wy = weights((y - y.floor()) as f32);
                wx.iter().map(|v| f64::from(*v).powi(2)).sum::<f64>()
                    * wy.iter().map(|v| f64::from(*v).powi(2)).sum::<f64>()
            })
            .collect()
    })
}
#[test]
fn a00_tap_norm_against_independent_public_impulses() {
    use strehl_core::align::{PlaneRef, sample_catmull_rom};
    for fx in [0., 0.13, 0.5, 0.91, 1.] {
        for fy in [0., 0.29, 0.5, 0.83, 1.] {
            let mut actual = 0.;
            for i in 0..16 {
                let mut pixels = [0.; 16];
                pixels[i] = 1.;
                let p = PlaneRef::from_geometry(
                    &pixels,
                    PlaneGeometry {
                        width: 4,
                        height: 4,
                    },
                )
                .unwrap();
                let h = sample_catmull_rom(p, 1. + fx, 1. + fy);
                actual += f64::from(h).powi(2);
            }
            let expected = weights(fx as f32)
                .iter()
                .map(|v| f64::from(*v).powi(2))
                .sum::<f64>()
                * weights(fy as f32)
                    .iter()
                    .map(|v| f64::from(*v).powi(2))
                    .sum::<f64>();
            assert!(
                (actual - expected).abs() < 1e-7,
                "{fx} {fy}: {actual} {expected}"
            );
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use strehl_cli::session_reconstruction_sampling::RegionSampler;
    use strehl_core::{
        align::{Resampler, SimilarityParams},
        noise::{Levels, PlaneNoise, Provenance},
    };
    struct ArraySource {
        g: PlaneGeometry,
        p: Vec<u16>,
    }
    impl QuadSource for ArraySource {
        fn geometry(&self) -> PlaneGeometry {
            self.g
        }
        fn quad_rows(&self, y: usize) -> (&[u16], &[u16]) {
            let w = 2 * self.g.width;
            (
                &self.p[2 * y * w..(2 * y + 1) * w],
                &self.p[(2 * y + 1) * w..(2 * y + 2) * w],
            )
        }
    }
    #[test]
    fn actual_region_sampler_impulses_verify_beta_phase_and_gauge() {
        let full = PlaneGeometry {
            width: 64,
            height: 64,
        };
        let d = SamplingDomain {
            full,
            x: 19,
            y: 22,
            width: 1,
            height: 1,
        };
        let levels = Levels {
            black: 1000.,
            white: 65535.,
        };
        for t in [
            Similarity::IDENTITY,
            Similarity::from_params(SimilarityParams {
                ax: 0.27,
                ay: 0.83,
                g: 0.013,
                rot: -0.021,
            }),
        ] {
            let theoretical = beta(d, t, None);
            let mut sampler = RegionSampler::new(d, 1 << 20).unwrap();
            for c in 0..4 {
                let (dx, dy) = CfaPlane::ALL[c].rggb_offset();
                let site = (dx as f64 * 0.5 - 0.25, dy as f64 * 0.5 - 0.25);
                let p = t.apply_at(d.x as f64 + site.0, d.y as f64 + site.1, 32., 32.);
                let bx = (p.0 - site.0).floor() as usize - 1;
                let by = (p.1 - site.1).floor() as usize - 1;
                let mut actual = 0.;
                for yy in 0..4 {
                    for xx in 0..4 {
                        let mut source = ArraySource {
                            g: full,
                            p: vec![1000; 4 * full.pixels()],
                        };
                        source.p[(2 * (by + yy) + dy) * 2 * full.width + 2 * (bx + xx) + dx] = 2000;
                        let s = sampler
                            .gather(&source, levels, t, None, Resampler::CatmullRom)
                            .unwrap();
                        assert!(s.support[0]);
                        let h = f64::from(s.planes[c][0]) / 1000.;
                        actual += h * h;
                    }
                }
                assert!(
                    (actual - theoretical[c][0]).abs() < 2e-7,
                    "c{c} {actual} {}",
                    theoretical[c][0]
                );
            }
        }
    }
    #[test]
    fn negative_weight_clipped_original_tap_refuses_whole_predeclared_block() {
        let full = PlaneGeometry {
            width: 160,
            height: 160,
        };
        let d = SamplingDomain {
            full,
            x: 16,
            y: 16,
            width: 128,
            height: 128,
        };
        let levels = Levels {
            black: 512.,
            white: 15360.,
        };
        let t = Similarity::from_params(SimilarityParams {
            ax: 0.25,
            ay: 0.25,
            ..Default::default()
        });
        let pn = PlaneNoise {
            gain_dn_per_e: 0.22893773,
            read_noise_e: 4.2,
            levels,
        };
        let noise = NoiseModel::new([pn; 4], 100., Provenance::Profile);
        let mut source = ArraySource {
            g: full,
            p: vec![1712; 4 * full.pixels()],
        };
        let original = (2 * 31) * 2 * full.width + 2 * 31;
        source.p[original] = 15360;
        let mut sampler = RegionSampler::new(d, 8 << 20).unwrap();
        let b = beta(d, t, None);
        let mut gate = crate::model::Gate::new();
        let sample = sampler
            .gather(&source, levels, t, None, Resampler::CatmullRom)
            .unwrap();
        assert!(sample.clipped[16 * 128 + 16]);
        assert!(!sample.support[16 * 128 + 16]);
        gate.q(0, &sample.planes, &sample.support, &b, 1.).unwrap();
        source.p[original] = 1712;
        for j in 1..3 {
            let sample = sampler
                .gather(&source, levels, t, None, Resampler::CatmullRom)
                .unwrap();
            gate.q(j, &sample.planes, &sample.support, &b, 1.).unwrap();
        }
        for j in 0..3 {
            let sample = sampler
                .gather(&source, levels, t, None, Resampler::CatmullRom)
                .unwrap();
            gate.v(j, &sample.planes, &sample.support, &b, 1.).unwrap();
        }
        let rows = gate.finish(&noise, 1.).unwrap();
        assert!(rows[..4].iter().all(|r| r["accepted"] == false));
        assert!(
            rows[..4]
                .iter()
                .all(|r| r["supported"].as_u64().unwrap() < 1024)
        );
        assert!(rows[4..].iter().any(|r| r["accepted"] == true));
    }
}
