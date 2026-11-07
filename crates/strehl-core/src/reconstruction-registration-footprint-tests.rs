use super::*;
fn patch(side: usize) -> Patch {
    Patch {
        origin: [0, 0],
        geometry: PlaneGeometry {
            width: side,
            height: side,
        },
        values: (0..side * side)
            .map(|i| {
                let x = (i % side) as f32;
                let y = (i / side) as f32;
                6000.
                    + 900. * (0.121 * x + 0.071 * y).sin()
                    + 1100. * (-0.085 * x + 0.143 * y).cos()
                    + 450. * (0.233 * x - 0.189 * y).sin()
            })
            .collect(),
        valid: vec![true; side * side],
        variance: 1.,
        gradient_variance: 0.5,
        pull: Similarity::IDENTITY,
    }
}
fn policy() -> Policy {
    Policy {
        geometry_lowpass_sigma_quad: 1.2,
        tile_quad: 46,
        grid_axis: 3,
        ..Policy::default()
    }
}
fn sets(t: Similarity) -> [footprint::Footprint; 2] {
    let a = patch(192);
    let b = patch(192);
    let mut sets = [
        footprint::Footprint::new(192),
        footprint::Footprint::new(192),
    ];
    for (iy, y) in [10, 73, 136].into_iter().enumerate() {
        for (ix, x) in [10, 73, 136].into_iter().enumerate() {
            assert!(footprint::visit(
                &a,
                &b,
                footprint::probe((x, y), t, 192, policy()),
                t.to_params(),
                Some(&mut sets[(ix + iy) % 2])
            ));
        }
    }
    sets.map(|s| s.original(4))
}
#[test]
fn a01_wide_exact_original_footprints_reject_shrinking_transform() {
    let t = Similarity {
        a: Cx::new(0.75, 0.),
        b: Cx::new(0., 0.),
    };
    let [train, held] = sets(t);
    // Independent audit enumeration: 568 same-color moving original sites.
    let count = train.cells[1]
        .iter()
        .zip(&held.cells[1])
        .filter(|(a, b)| **a != 0 && **b != 0)
        .count();
    assert_eq!(count, 568);
    assert!(train.overlaps(&held));
    let [train, held] = sets(Similarity::IDENTITY);
    assert!(!train.overlaps(&held));
    let t = Similarity {
        a: Cx::new(0.9997, 0.0002),
        b: Cx::new(0.21, -0.27),
    };
    let [train, held] = sets(t);
    assert!(!train.overlaps(&held));
}
#[test]
fn a02_reference_derivatives_and_original_gaussian_mask_are_included() {
    let p = patch(192);
    let mut f = footprint::Footprint::new(192);
    assert!(footprint::visit(
        &p,
        &p,
        footprint::probe((10, 10), Similarity::IDENTITY, 192, policy()),
        Similarity::IDENTITY.to_params(),
        Some(&mut f)
    ));
    let f = f.original(4);
    assert_eq!(f.cells[0][5 * 192 + 5], 1); // reference information (-1) then Gaussian (-4)
    assert_eq!(f.cells[0][4 * 192 + 5], 0);
    assert_eq!(f.cells[1][3 * 192 + 3], 1); // moving search (-3) then Gaussian (-4)
    assert_eq!(f.cells[1][2 * 192 + 3], 0);
}
#[test]
fn b01_later_changed_probe_cannot_read_invalid_filtered_zero() {
    let a = patch(192);
    let mut b = patch(192);
    let t = Similarity::IDENTITY;
    let p = footprint::probe((10, 10), t, 192, policy());
    let mut initial = footprint::Footprint::new(192);
    assert!(footprint::visit(
        &a,
        &b,
        p,
        t.to_params(),
        Some(&mut initial)
    ));
    let later = Similarity {
        a: Cx::new(0.999, 0.001),
        b: Cx::new(2., 0.3),
    };
    let q = footprint::probe((10, 10), later, 192, policy());
    let mut changed = footprint::Footprint::new(192);
    assert!(footprint::visit(
        &a,
        &b,
        q,
        later.to_params(),
        Some(&mut changed)
    ));
    let poison = changed.cells[1]
        .iter()
        .zip(&initial.cells[1])
        .position(|(a, b)| *a != 0 && *b == 0)
        .unwrap();
    b.valid[poison] = false;
    b.values[poison] = 0.;
    assert!(footprint::visit(&a, &b, p, t.to_params(), None));
    assert!(!footprint::visit(&a, &b, q, later.to_params(), None));
}
#[test]
fn b02_all_iterations_union_detects_overlap_not_only_final_transform() {
    let p = patch(192);
    let mut train = footprint::Footprint::new(192);
    for t in [
        Similarity::IDENTITY,
        Similarity {
            a: Cx::new(1., 0.002),
            b: Cx::new(8., 0.),
        },
    ] {
        assert!(footprint::visit(
            &p,
            &p,
            footprint::probe((10, 73), t, 192, policy()),
            t.to_params(),
            Some(&mut train)
        ));
    }
    let mut held = footprint::Footprint::new(192);
    assert!(footprint::visit(
        &p,
        &p,
        footprint::probe((73, 73), Similarity::IDENTITY, 192, policy()),
        Similarity::IDENTITY.to_params(),
        Some(&mut held)
    ));
    assert!(train.original(4).overlaps(&held.original(4)));
}
#[test]
fn b03_observer_preserves_training_numerical_bits_when_supported() {
    let a = patch(192);
    let b = patch(192);
    let ap = PlaneRef::from_geometry(&a.values, a.geometry).unwrap();
    let bp = PlaneRef::from_geometry(&b.values, b.geometry).unwrap();
    let spots = [(10, 10), (136, 10), (73, 73), (10, 136), (136, 136)];
    let cfg = AlignConfig {
        fine_tile: 46,
        fine_grid: (3, 3),
        fine_radius: 3,
        margin: 10,
        min_tiles: 4,
        fine_iters: 3,
        warp_tiles: true,
        ..AlignConfig::shallow()
    };
    let plain = refine_pair_observed(ap, bp, &spots, &cfg, Similarity::IDENTITY, None).unwrap();
    let mut traced = footprint::Footprint::new(192);
    let mut stages = 0;
    let mut observer = |trace: &PairTrace| {
        for pass in &trace.fine_passes {
            stages += 1;
            let m = &pass.stage.measurements;
            for tile in &m.tiles {
                assert!(footprint::visit(
                    &a,
                    &b,
                    tile.probe,
                    m.seed.unwrap(),
                    Some(&mut traced)
                ));
            }
        }
    };
    let observed = refine_pair_observed(
        ap,
        bp,
        &spots,
        &cfg,
        Similarity::IDENTITY,
        Some(&mut observer),
    )
    .unwrap();
    assert!(stages >= 1);
    let bits = |f: &crate::align::StageFit| {
        (
            [f.fit.ax, f.fit.ay, f.fit.g, f.fit.rot].map(f64::to_bits),
            [f.rms, f.lever_rms, f.peak_mean].map(f32::to_bits),
            [f.used, f.total, f.raw_n],
            f.rejected,
        )
    };
    assert_eq!(bits(&plain), bits(&observed));
}
#[test]
fn c01_original_footprint_dilation_matches_independent_square_union() {
    let mut f = footprint::Footprint::new(19);
    let mut oracle = vec![0u8; 19 * 19];
    for (x, y) in [(0usize, 0usize), (9, 7), (18, 18)] {
        f.cells[1][y * 19 + x] = 1;
        for yy in 0usize..19 {
            for xx in 0usize..19 {
                if xx.abs_diff(x) <= 4 && yy.abs_diff(y) <= 4 {
                    oracle[yy * 19 + xx] = 1;
                }
            }
        }
    }
    assert_eq!(f.original(4).cells[1], oracle);
}

struct Raw {
    data: Vec<u16>,
}
impl QuadSource for Raw {
    fn geometry(&self) -> PlaneGeometry {
        PlaneGeometry {
            width: 256,
            height: 256,
        }
    }
    fn quad_rows(&self, y: usize) -> (&[u16], &[u16]) {
        let i = 2 * y * 512;
        (&self.data[i..i + 512], &self.data[i + 512..i + 1024])
    }
}
fn raw(transform: Similarity) -> Raw {
    let mut data = vec![0; 512 * 512];
    // Independent absolute sensor-coordinate inverse of the physical transform.
    for y in 0..512 {
        for x in 0..512 {
            let dx = x as f64 - 256.5 - 2. * transform.b.re;
            let dy = y as f64 - 256.5 - 2. * transform.b.im;
            let det = transform.a.re * transform.a.re + transform.a.im * transform.a.im;
            let xx = 256.5 + (transform.a.re * dx + transform.a.im * dy) / det;
            let yy = 256.5 + (transform.a.re * dy - transform.a.im * dx) / det;
            data[y * 512 + x] = (6512.
                + 900. * (0.061 * xx + 0.036 * yy).sin()
                + 1100. * (-0.043 * xx + 0.072 * yy).cos()
                + 450. * (0.117 * xx - 0.094 * yy).sin())
            .round() as u16;
        }
    }
    Raw { data }
}
fn view(source: &Raw, id: u64, pull: Similarity) -> OriginalView<'_> {
    OriginalView {
        acquisition_id: id,
        source,
        color_pulls: [pull; 3],
        noise: [PlaneNoise {
            gain_dn_per_e: 0.01,
            read_noise_e: 20.,
            levels: crate::noise::Levels {
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
fn d01_pair_path_refuses_actual_shrinking_overlap_and_keeps_near_identity() {
    let a = raw(Similarity::IDENTITY);
    for t in [
        Similarity::IDENTITY,
        Similarity {
            a: Cx::new(0.75, 0.),
            b: Cx::new(0., 0.),
        },
    ] {
        let b = raw(t);
        let result = measure_pair(
            &view(&a, 1, Similarity::IDENTITY),
            &view(&b, 2, t),
            window(),
            PlaneKind::Red,
            policy(),
        )
        .unwrap();
        if t.a.re == 1. {
            assert!(result.saved_map_supported, "{result:?}");
            assert_eq!(result.heldout_tiles.len(), 4);
        } else {
            assert_eq!(
                result.refusal.as_deref(),
                Some("training and held-out original evidence overlap")
            );
            assert!(!result.saved_map_supported);
            assert!(result.heldout_tiles.is_empty());
        }
    }
}
#[test]
fn d02_pair_path_refuses_invalid_tap_reached_only_after_training_moves() {
    let a = raw(Similarity::IDENTITY);
    let actual = Similarity {
        a: Cx::new(1., 0.),
        b: Cx::new(1.1, 0.),
    };
    let mut b = raw(actual);
    // Source crop origin32. Seed search max filtered x59 + Gaussian4 =63;
    // the later fitted translation reaches original local x64.
    b.data[(2 * (32 + 30)) * 512 + 2 * (32 + 64)] = 15360;
    let result = measure_pair(
        &view(&a, 1, Similarity::IDENTITY),
        &view(&b, 2, Similarity::IDENTITY),
        window(),
        PlaneKind::Red,
        policy(),
    )
    .unwrap();
    assert_eq!(
        result.refusal.as_deref(),
        Some("training iteration reached unsupported original taps"),
        "{result:?}"
    );
    assert!(!result.saved_map_supported);
    assert!(result.heldout_tiles.is_empty());
}
