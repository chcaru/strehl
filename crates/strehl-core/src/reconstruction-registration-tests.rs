use super::*;
use crate::{align::SimilarityParams, noise::Levels};
struct Raw {
    g: PlaneGeometry,
    stride: usize,
    data: Vec<u16>,
}
impl QuadSource for Raw {
    fn geometry(&self) -> PlaneGeometry {
        self.g
    }
    fn quad_rows(&self, y: usize) -> (&[u16], &[u16]) {
        let p = (2 * y + 5) * self.stride + 3;
        (
            &self.data[p..p + 2 * self.g.width],
            &self.data[p + self.stride..p + self.stride + 2 * self.g.width],
        )
    }
}
fn noise() -> [PlaneNoise; 4] {
    [PlaneNoise {
        gain_dn_per_e: 0.01,
        read_noise_e: 20.,
        levels: Levels {
            black: 512.,
            white: 15360.,
        },
    }; 4]
}
fn scene(x: f64, y: f64) -> f64 {
    6000.
        + 900. * (0.121 * x + 0.071 * y).sin()
        + 1100. * (-0.085 * x + 0.143 * y).cos()
        + 450. * (0.233 * x - 0.189 * y).sin()
}
fn raw(t: [Similarity; 3], f: &dyn Fn(f64, f64) -> f64) -> Raw {
    raw_with_geometry(
        t,
        f,
        PlaneGeometry {
            width: 256,
            height: 256,
        },
    )
}
fn raw_with_geometry(t: [Similarity; 3], f: &dyn Fn(f64, f64) -> f64, g: PlaneGeometry) -> Raw {
    let stride = 2 * g.width + 9;
    let mut out = Raw {
        g,
        stride,
        data: vec![65535; stride * (2 * g.height + 9)],
    };
    // Independent inverse in absolute active sensor coordinates; never use the
    // registration module's effective-site or crop conjugation helpers.
    for y in 0..2 * g.height {
        for x in 0..2 * g.width {
            let c = match (x % 2, y % 2) {
                (0, 0) => 0,
                (1, 1) => 2,
                _ => 1,
            };
            let t = t[c];
            let dx = x as f64 - g.width as f64 - 0.5 - 2. * t.b.re;
            let dy = y as f64 - g.height as f64 - 0.5 - 2. * t.b.im;
            let det = t.a.re * t.a.re + t.a.im * t.a.im;
            let ax = g.width as f64 + 0.5 + (t.a.re * dx + t.a.im * dy) / det;
            let ay = g.height as f64 + 0.5 + (-t.a.im * dx + t.a.re * dy) / det;
            out.data[(y + 5) * stride + x + 3] =
                (512. + f(ax, ay)).round().clamp(0., 65535.) as u16;
        }
    }
    out
}
#[path = "reconstruction-registration-wide-tests.rs"]
mod wide;
fn view(raw: &Raw, id: u64, t: [Similarity; 3]) -> OriginalView<'_> {
    OriginalView {
        acquisition_id: id,
        source: raw,
        color_pulls: t,
        noise: noise(),
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
fn transform() -> Similarity {
    Similarity::from_params(SimilarityParams {
        ax: 0.18,
        ay: -0.27,
        g: -0.0018,
        rot: 0.0007,
    })
}
#[test]
fn diagnostic_census_distinguishes_flat_structure_and_clipped_support_first() {
    let identity = [Similarity::IDENTITY; 3];
    let policy = Policy {
        geometry_lowpass_sigma_quad: 1.2,
        tile_quad: 46,
        grid_axis: 3,
        ..Policy::default()
    };
    for clipped in [false, true] {
        let source = raw(identity, &|_, _| if clipped { 65000. } else { 6000. });
        let a = view(&source, 0, identity);
        let b = view(&source, 1, identity);
        let d = diagnostics::measure_pair(&a, &b, window(), PlaneKind::Red, policy).unwrap();
        assert_eq!(d.tiles.len(), 9);
        assert_eq!(d.tiles.iter().filter(|t| t.training).count(), 5);
        assert!(d.witnessed.evidence.fitted_pair_global.is_none());
        for tile in d.tiles {
            assert!(!tile.retained_heldout);
            assert!(tile.fitted.is_none());
            assert_eq!(tile.seed.reference_derivatives_supported, !clipped);
            assert_eq!(tile.seed.original_search_supported, !clipped);
            if clipped {
                assert!(tile.seed.information.is_none());
                assert!(tile.seed.ncc.is_none());
            } else {
                let info = tile.seed.information.unwrap();
                assert!(!info.accepted);
                assert!(info.minimum_eigenvalue < info.minimum_eigenvalue_required);
                assert_eq!(tile.seed.ncc.unwrap().status, TileStatus::LowContrast);
            }
        }
    }
}

#[test]
fn diagnostic_census_preserves_witness_and_distinguishes_one_axis_from_two() {
    let identity = [Similarity::IDENTITY; 3];
    let t = [transform(); 3];
    let policy = Policy {
        geometry_lowpass_sigma_quad: 1.2,
        tile_quad: 46,
        grid_axis: 3,
        ..Policy::default()
    };
    for one_axis in [false, true] {
        let signal = |x: f64, y: f64| {
            if one_axis {
                6000. + 1100. * (0.143 * x).cos()
            } else {
                scene(x, y)
            }
        };
        let first = raw(identity, &signal);
        let second = raw(t, &signal);
        for color in [PlaneKind::Red, PlaneKind::GreenLuma, PlaneKind::Blue] {
            let a = view(&first, 0, identity);
            let b = view(&second, 1, t);
            let ordinary = measure_pair_with_footprints(&a, &b, window(), color, policy).unwrap();
            let d = diagnostics::measure_pair(&a, &b, window(), color, policy).unwrap();
            assert_eq!(
                format!("{:?}", ordinary.evidence),
                format!("{:?}", d.witnessed.evidence)
            );
            assert_eq!(
                ordinary.footprints.training,
                d.witnessed.footprints.training
            );
            assert_eq!(ordinary.footprints.heldout, d.witnessed.footprints.heldout);
            assert_eq!(d.tiles.len(), 9);
            let mut patch = build(&a, window(), color).unwrap();
            geometry_lowpass(
                &mut patch,
                &geometry_kernel(policy.geometry_lowpass_sigma_quad).unwrap(),
            );
            for tile in &d.tiles {
                let [x, y] = tile.reference_origin_crop_quad;
                let expected = information(&patch, x, y, policy.tile_quad, policy);
                let reported = tile.seed.information.unwrap();
                assert_eq!(reported.accepted, expected.is_some());
                if let Some(ratio) = expected {
                    assert_eq!(ratio.to_bits(), reported.ratio.to_bits());
                }
                if one_axis {
                    assert!(!reported.accepted);
                    assert!(reported.ratio < reported.minimum_ratio);
                } else {
                    assert!(reported.accepted);
                }
            }
            assert_eq!(
                d.tiles.iter().filter(|v| v.retained_heldout).count(),
                ordinary.evidence.heldout_tiles.len()
            );
        }
    }
}
#[test]
fn a01_flat_noise_and_one_axis_are_not_placement_evidence() {
    let identity = [Similarity::IDENTITY; 3];
    let scenes: [&dyn Fn(f64, f64) -> f64; 3] = [
        &|_: f64, _: f64| 6000.,
        &|x: f64, y: f64| 6000. + 12. * ((x * 73. + y * 47.).sin()),
        &|x: f64, _: f64| 6000. + 1000. * (x * 0.16).sin(),
    ];
    for f in scenes {
        let a = raw(identity, f);
        let b = raw(identity, f);
        let result = measure_pair(
            &view(&a, 11, identity),
            &view(&b, 22, identity),
            window(),
            PlaneKind::GreenLuma,
            Policy::default(),
        )
        .unwrap();
        assert!(!result.saved_map_supported);
        assert!(!result.refined_map_supported);
        assert_eq!(result.acquisitions, [11, 22]);
        assert!(result.heldout_tiles.is_empty());
    }
}
#[test]
fn b01_curved_scale_rotation_original_cfa_has_heldout_witness() {
    let identity = [Similarity::IDENTITY; 3];
    let moving = [transform(); 3];
    let a = raw(identity, &scene);
    let b = raw(moving, &scene);
    for color in [PlaneKind::Red, PlaneKind::GreenLuma, PlaneKind::Blue] {
        let result = measure_pair(
            &view(&a, 11, identity),
            &view(&b, 22, moving),
            window(),
            color,
            Policy::default(),
        )
        .unwrap();
        assert!(result.saved_map_supported, "{color:?}: {result:?}");
        assert!(result.refined_map_supported, "{color:?}: {result:?}");
        assert!(result.heldout_tiles.len() >= 4);
        assert_eq!(result.acquisitions, [11, 22]);
    }
}
#[test]
fn b02_wrong_saved_placement_is_not_validated_by_its_training_fit() {
    let identity = [Similarity::IDENTITY; 3];
    let actual = [transform(); 3];
    let mut wrong = actual;
    for t in &mut wrong {
        t.b.re += 0.35;
        t.b.im -= 0.2;
    }
    let a = raw(identity, &scene);
    let b = raw(actual, &scene);
    let result = measure_pair(
        &view(&a, 11, identity),
        &view(&b, 22, wrong),
        window(),
        PlaneKind::Red,
        Policy::default(),
    )
    .unwrap();
    assert!(!result.saved_map_supported, "{result:?}");
    assert!(result.refined_map_supported, "{result:?}");
    assert!(result.maximum_saved_disagreement_sensor > 0.5);
}
#[test]
fn c01_clip_and_spatially_inconsistent_motion_refuse_certificate() {
    let identity = [Similarity::IDENTITY; 3];
    let a = raw(identity, &scene);
    let scenes: [&dyn Fn(f64, f64) -> f64; 2] = [&|_: f64, _: f64| 16000., &|x: f64, y: f64| {
        scene(x + if y > 256. { 1.8 } else { -1.8 }, y)
    }];
    for f in scenes {
        let b = raw(identity, f);
        let result = measure_pair(
            &view(&a, 11, identity),
            &view(&b, 22, identity),
            window(),
            PlaneKind::Red,
            Policy::default(),
        )
        .unwrap();
        assert!(!result.saved_map_supported, "{result:?}");
    }
}
#[test]
fn c02_crop_and_site_gauge_match_absolute_sensor_oracle() {
    let t = transform();
    let w = window();
    let origins = [[13, 29], [43, 17]];
    for kind in [PlaneKind::Red, PlaneKind::GreenLuma, PlaneKind::Blue] {
        let effective = plane_pull(t, kind);
        let local = crop_pull(effective, w.full, 128, origins);
        let restored = uncrop_pull(local, w.full, 128, origins);
        for p in [[9., 14.], [111., 98.]] {
            let q = [p[0] + origins[0][0] as f64, p[1] + origins[0][1] as f64];
            let site = kind.offset();
            let sensor = [2. * q[0] + site[0], 2. * q[1] + site[1]];
            let delta = [sensor[0] - 256.5, sensor[1] - 256.5];
            let expected = [
                (256.5 + t.a.re * delta[0] - t.a.im * delta[1] + 2. * t.b.re - site[0]) * 0.5,
                (256.5 + t.a.im * delta[0] + t.a.re * delta[1] + 2. * t.b.im - site[1]) * 0.5,
            ];
            let got = local.apply_at(p[0], p[1], 64., 64.);
            let back = restored.apply_at(q[0], q[1], 128., 128.);
            assert!((got.0 + origins[1][0] as f64 - expected[0]).abs() < 1e-10);
            assert!((got.1 + origins[1][1] as f64 - expected[1]).abs() < 1e-10);
            assert!((back.0 - expected[0]).abs() < 1e-10 && (back.1 - expected[1]).abs() < 1e-10);
        }
    }
}
#[test]
fn c03_budget_duplicate_and_overlapping_holdout_refuse() {
    let identity = [Similarity::IDENTITY; 3];
    let a = raw(identity, &scene);
    let b = raw(identity, &scene);
    assert!(
        measure_pair(
            &view(&a, 1, identity),
            &view(&b, 1, identity),
            window(),
            PlaneKind::Red,
            Policy::default()
        )
        .is_err()
    );
    let cfg = Policy {
        budget_bytes: 1,
        ..Policy::default()
    };
    assert!(
        measure_pair(
            &view(&a, 1, identity),
            &view(&b, 2, identity),
            window(),
            PlaneKind::Red,
            cfg
        )
        .is_err()
    );
    let w = Window {
        side_quad: 96,
        ..window()
    };
    assert!(
        measure_pair(
            &view(&a, 1, identity),
            &view(&b, 2, identity),
            w,
            PlaneKind::Red,
            Policy::default()
        )
        .is_err()
    );
    assert!(
        reservation_bytes(Window {
            side_quad: usize::MAX,
            ..window()
        })
        .is_err()
    );
}
