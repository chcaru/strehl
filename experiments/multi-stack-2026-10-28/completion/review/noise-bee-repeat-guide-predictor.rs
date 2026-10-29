//! Same-color original-target to frozen-original-guide prediction.
//! This returns a noisy guide plug-in mean, not a certified conditional covariance.
use std::collections::BTreeSet;
use strehl_core::{
    CfaPlane,
    align::Similarity,
    noise,
    plane::{PlaneGeometry, QuadSource},
};
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
pub fn guide_value(
    source: &dyn QuadSource,
    plane: CfaPlane,
    q: [f64; 2],
    levels: noise::Levels,
    visited: &mut BTreeSet<(usize, usize)>,
) -> Option<f32> {
    let geometry = source.geometry();
    let bx = q[0].floor() as i64;
    let by = q[1].floor() as i64;
    let wx = weights((q[0] - bx as f64) as f32);
    let wy = weights((q[1] - by as f64) as f32);
    let (dx, dy) = plane.rggb_offset();
    let mut sum = 0.;
    for j in 0..4 {
        for i in 0..4 {
            let w = wx[i] * wy[j];
            if w == 0. {
                continue;
            }
            let x = bx - 1 + i as i64;
            let y = by - 1 + j as i64;
            if x < 0 || y < 0 || x >= geometry.width as i64 || y >= geometry.height as i64 {
                return None;
            }
            let x = x as usize;
            let y = y as usize;
            let (r0, r1) = source.quad_rows(y);
            let raw = if dy == 0 {
                r0[2 * x + dx]
            } else {
                r1[2 * x + dx]
            } as f32;
            if raw >= levels.white {
                return None;
            }
            if visited.len() >= 1_000_000 {
                return None;
            }
            visited.insert((x, y));
            sum += w * (raw - levels.black);
        }
    }
    sum.is_finite().then_some(sum)
}

pub fn predict(
    original_quad: [usize; 2],
    plane: CfaPlane,
    target_pull: Similarity,
    full: PlaneGeometry,
    guides: [&dyn QuadSource; 2],
    guide_pulls: [Similarity; 2],
    levels: [noise::Levels; 2],
    temporal_weights: [f64; 2],
    visited: &mut [BTreeSet<(usize, usize)>; 2],
) -> Option<f32> {
    if guides.iter().any(|g| g.geometry() != full)
        || !temporal_weights
            .iter()
            .all(|w| w.is_finite() && *w >= 0. && *w <= 1.)
        || (temporal_weights.iter().sum::<f64>() - 1.).abs() > 1e-12
    {
        return None;
    }
    let (dx, dy) = plane.rggb_offset();
    let site = [dx as f64 * 0.5 - 0.25, dy as f64 * 0.5 - 0.25];
    let inverse = target_pull.invert()?;
    let reference = inverse.apply_at(
        original_quad[0] as f64 + site[0],
        original_quad[1] as f64 + site[1],
        full.width as f64 * 0.5,
        full.height as f64 * 0.5,
    );
    let mut mean = 0.;
    for g in 0..2 {
        let q = guide_pulls[g].apply_at(
            reference.0,
            reference.1,
            full.width as f64 * 0.5,
            full.height as f64 * 0.5,
        );
        mean += temporal_weights[g] as f32
            * guide_value(
                guides[g],
                plane,
                [q.0 - site[0], q.1 - site[1]],
                levels[g],
                &mut visited[g],
            )?;
    }
    mean.is_finite().then_some(mean)
}
#[cfg(test)]
mod tests {
    use super::*;
    use strehl_core::align::Cx;
    struct Raw {
        full: PlaneGeometry,
        pixels: Vec<u16>,
    }
    impl Raw {
        fn new(full: PlaneGeometry, ax: u16, ay: u16) -> Self {
            let mut pixels = vec![0; 4 * full.width * full.height];
            for y in 0..full.height {
                for x in 0..full.width {
                    for c in CfaPlane::ALL {
                        let (dx, dy) = c.rggb_offset();
                        pixels[(2 * y + dy) * 2 * full.width + 2 * x + dx] =
                            512 + 100 + ax * x as u16 + ay * y as u16 + ((dx + 2 * dy) * 17) as u16;
                    }
                }
            }
            Self { full, pixels }
        }
    }
    impl QuadSource for Raw {
        fn geometry(&self) -> PlaneGeometry {
            self.full
        }
        fn quad_rows(&self, y: usize) -> (&[u16], &[u16]) {
            let w = 2 * self.full.width;
            (
                &self.pixels[2 * y * w..(2 * y + 1) * w],
                &self.pixels[(2 * y + 1) * w..(2 * y + 2) * w],
            )
        }
    }
    fn levels() -> noise::Levels {
        noise::Levels {
            black: 512.,
            white: 15000.,
        }
    }
    fn identity() -> Similarity {
        Similarity {
            a: Cx::new(1., 0.),
            b: Cx::new(0., 0.),
        }
    }
    #[test]
    fn absolute_sensor_oracle_nonidentity_color_pulls_and_heterogeneous_linear_guides() {
        let full = PlaneGeometry {
            width: 129,
            height: 117,
        };
        let g0 = Raw::new(full, 3, 5);
        let g1 = Raw::new(full, 7, 2);
        for (c, plane) in CfaPlane::ALL.into_iter().enumerate() {
            let target = Similarity {
                a: Cx::new(0.997 + c as f64 * 0.0002, 0.012),
                b: Cx::new(0.3, -0.2),
            };
            let pulls = [
                Similarity {
                    a: Cx::new(1.007, -0.009 + c as f64 * 0.0003),
                    b: Cx::new(-0.4, 0.7),
                },
                Similarity {
                    a: Cx::new(0.989, 0.016),
                    b: Cx::new(0.8, -0.5),
                },
            ];
            let mut visited = std::array::from_fn(|_| BTreeSet::new());
            let got = predict(
                [50, 60],
                plane,
                target,
                full,
                [&g0, &g1],
                pulls,
                [levels(); 2],
                [0.23, 0.77],
                &mut visited,
            )
            .unwrap();
            // Independent absolute SENSOR oracle: center=N+0.5, translations2b;
            // directly invert complex2x2 matrix, never call apply_at or predictor gauge.
            let (dx, dy) = plane.rggb_offset();
            let center = [full.width as f64 + 0.5, full.height as f64 + 0.5];
            let a = target.a;
            let u = 100. + dx as f64 - center[0] - 2. * target.b.re;
            let v = 120. + dy as f64 - center[1] - 2. * target.b.im;
            let den = a.re * a.re + a.im * a.im;
            let reference = [
                center[0] + (a.re * u + a.im * v) / den,
                center[1] + (-a.im * u + a.re * v) / den,
            ];
            let mut expected = 0.;
            for j in 0..2 {
                let p = pulls[j];
                let x = reference[0] - center[0];
                let y = reference[1] - center[1];
                let sensor = [
                    center[0] + p.a.re * x - p.a.im * y + 2. * p.b.re,
                    center[1] + p.a.im * x + p.a.re * y + 2. * p.b.im,
                ];
                let q = [(sensor[0] - dx as f64) / 2., (sensor[1] - dy as f64) / 2.];
                let (ax, ay) = if j == 0 { (3., 5.) } else { (7., 2.) };
                expected +=
                    [0.23, 0.77][j] * (100. + ax * q[0] + ay * q[1] + ((dx + 2 * dy) * 17) as f64);
            }
            assert!(
                (f64::from(got) - expected).abs() < 0.001,
                "color{c}: {got} vs{expected}"
            );
            assert!(visited.iter().all(|v| v.len() == 16));
        }
    }
    #[test]
    fn negative_weight_clipped_guide_tap_and_missing_border_refuse() {
        let full = PlaneGeometry {
            width: 64,
            height: 64,
        };
        let mut g0 = Raw::new(full, 3, 5);
        let g1 = Raw::new(full, 7, 2);
        let mut p = identity();
        p.b = Cx::new(0.25, 0.25);
        let mut visited = std::array::from_fn(|_| BTreeSet::new());
        assert!(
            predict(
                [30, 30],
                CfaPlane::R,
                identity(),
                full,
                [&g0, &g1],
                [p, identity()],
                [levels(); 2],
                [0.5, 0.5],
                &mut visited
            )
            .is_some()
        );
        // x29 is the negative Catmull lobe; y30 is a positive central lobe.
        g0.pixels[2 * 30 * 128 + 2 * 29] = 15000;
        let mut visited = std::array::from_fn(|_| BTreeSet::new());
        assert!(
            predict(
                [30, 30],
                CfaPlane::R,
                identity(),
                full,
                [&g0, &g1],
                [p, identity()],
                [levels(); 2],
                [0.5, 0.5],
                &mut visited
            )
            .is_none()
        );
        let mut visited = std::array::from_fn(|_| BTreeSet::new());
        assert!(
            predict(
                [0, 0],
                CfaPlane::R,
                identity(),
                full,
                [&g0, &g1],
                [p, identity()],
                [levels(); 2],
                [0.5, 0.5],
                &mut visited
            )
            .is_none()
        );
    }
    #[test]
    fn wrong_full_gauge_and_extrapolation_refuse() {
        let full = PlaneGeometry {
            width: 64,
            height: 64,
        };
        let g = Raw::new(full, 1, 1);
        let mut visited = std::array::from_fn(|_| BTreeSet::new());
        assert!(
            predict(
                [30, 30],
                CfaPlane::R,
                identity(),
                PlaneGeometry { width: 65, ..full },
                [&g, &g],
                [identity(); 2],
                [levels(); 2],
                [0.5, 0.5],
                &mut visited
            )
            .is_none()
        );
        assert!(
            predict(
                [30, 30],
                CfaPlane::R,
                identity(),
                full,
                [&g, &g],
                [identity(); 2],
                [levels(); 2],
                [-0.1, 1.1],
                &mut visited
            )
            .is_none()
        );
    }
}
