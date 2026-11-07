//! Root-scheduled measured-placement operator replay; no photographed RAW input.
#![allow(dead_code)]
#[path = "local-registration.rs"]
mod local_registration;
#[path = "measured-trajectory-01.rs"]
mod measured;
fn main() {}
#[cfg(test)]
mod measured_controls {
    use super::{local_registration::*, measured::MEASURED};
    use strehl_core::{
        align::{Cx, Similarity},
        noise::{Levels, PlaneNoise},
        plane::{PlaneGeometry, QuadSource},
    };
    struct Raw {
        data: Vec<u16>,
        stride: usize,
    }
    impl QuadSource for Raw {
        fn geometry(&self) -> PlaneGeometry {
            PlaneGeometry {
                width: 256,
                height: 256,
            }
        }
        fn quad_rows(&self, y: usize) -> (&[u16], &[u16]) {
            let i = (2 * y + 3) * self.stride + 5;
            (
                &self.data[i..i + 512],
                &self.data[i + self.stride..i + self.stride + 512],
            )
        }
    }
    fn pulls() -> Vec<Similarity> {
        MEASURED
            .iter()
            .map(|(_, bits)| {
                let v = bits.map(f64::from_bits);
                Similarity {
                    a: Cx::new(v[0], v[1]),
                    b: Cx::new(v[2], v[3]),
                }
            })
            .collect()
    }
    fn scene(x: f64, y: f64) -> f64 {
        6000.
            + 900. * (0.121 * x + 0.071 * y).sin()
            + 1100. * (-0.085 * x + 0.143 * y).cos()
            + 450. * (0.233 * x - 0.189 * y).sin()
    }
    fn raw(t: Similarity) -> Raw {
        let stride = 523;
        let mut r = Raw {
            data: vec![65535; stride * 520],
            stride,
        };
        for y in 0..512 {
            for x in 0..512 {
                let dx = x as f64 - 256.5 - 2. * t.b.re;
                let dy = y as f64 - 256.5 - 2. * t.b.im;
                let det = t.a.re * t.a.re + t.a.im * t.a.im;
                let px = 256.5 + (t.a.re * dx + t.a.im * dy) / det;
                let py = 256.5 + (-t.a.im * dx + t.a.re * dy) / det;
                r.data[(y + 3) * stride + x + 5] = (512. + scene(px, py)).round() as u16;
            }
        }
        r
    }
    fn view(r: &Raw, i: usize, t: Similarity) -> OriginalView<'_> {
        OriginalView {
            acquisition_id: MEASURED[i].0 as u64,
            source: r,
            color_pulls: [t; 3],
            noise: [PlaneNoise {
                gain_dn_per_e: 0.01,
                read_noise_e: 20.,
                levels: Levels {
                    black: 512.,
                    white: 15360.,
                },
            }; 4],
            gain: 1.,
            frozen_expected_rgb: [6000.; 3],
        }
    }
    fn window() -> Window {
        Window {
            full: PlaneGeometry {
                width: 256,
                height: 256,
            },
            center_sensor: [256.5, 256.5],
            side_quad: 192,
        }
    }
    #[test]
    fn a01_selected_measured_curvature_is_not_a_linear_trajectory() {
        let p = pulls();
        let mut curvature = 0f64;
        for begin in [0, 7] {
            for i in begin + 1..begin + 6 {
                curvature =
                    curvature.max((p[i + 1].a - p[i].a * Cx::new(2., 0.) + p[i - 1].a).abs());
            }
        }
        assert!(curvature > 0.0001, "lost measured curvature: {curvature}");
        assert!(
            p.iter()
                .all(|p| p.b.re >= 0. && p.b.re < 1. && p.b.im >= 0. && p.b.im < 1.)
        );
    }
    #[test]
    fn b01_measured_curved_original_cfa_pairs_pass_the_same_heldout_bound() {
        let p = pulls();
        let r: Vec<_> = p.iter().map(|t| raw(*t)).collect();
        let pairs: Vec<_> = (0..6)
            .map(|i| (i, i + 1))
            .chain((7..13).map(|i| (i, i + 1)))
            .chain([(3, 10)])
            .collect();
        for (i, j) in pairs {
            for c in [PlaneKind::Red, PlaneKind::GreenLuma, PlaneKind::Blue] {
                let e = measure_pair(
                    &view(&r[i], i, p[i]),
                    &view(&r[j], j, p[j]),
                    window(),
                    c,
                    Policy::default(),
                )
                .unwrap();
                assert!(
                    e.saved_map_supported,
                    "sources{},{} color{c:?}: {e:?}",
                    MEASURED[i].0, MEASURED[j].0
                );
            }
        }
    }
    #[test]
    fn c01_shuffled_measured_placements_do_not_validate_original_samples() {
        let p = pulls();
        let r: Vec<_> = p.iter().map(|t| raw(*t)).collect();
        let mut refused = 0;
        for j in 1..7 {
            let e = measure_pair(
                &view(&r[0], 0, p[0]),
                &view(&r[j], j, p[(j + 2) % 7]),
                window(),
                PlaneKind::Red,
                Policy::default(),
            )
            .unwrap();
            refused += usize::from(!e.saved_map_supported);
        }
        assert!(refused >= 3, "shuffled map foil only refused{refused}/6");
    }
}
