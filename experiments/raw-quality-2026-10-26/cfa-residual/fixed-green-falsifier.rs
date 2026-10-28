// Fixed retrospective falsifier for an unchanged-green color-residual extension.
// Reuse frozen independently authored source/gather/render controls, unchanged.
include!(concat!(
    env!("CARGO_MANIFEST_DIR"),
    "/../../experiments/raw-quality-2026-10-26/cfa-controls.rs"
));

#[test]
fn unchanged_green_residual_falsifier() {
    // This extension leaves the direct green sampler exactly unchanged, so its
    // existing independently evaluated flat-noise transport remains applicable.
    flat_noise_first();
    let frequency = 0.30_f32;
    let degrees = 73.0_f32;
    let (s, c) = degrees.to_radians().sin_cos();
    let scene = |_: usize, x: f32, y: f32| {
        2000.0 + 300.0 * (std::f32::consts::TAU * frequency * (c * x + s * y) + 0.37).sin()
    };
    let raw = source(scene);
    let pull = Pull {
        dx: -0.375,
        dy: 0.25,
        scale: 1.015,
        angle: 1.2_f32.to_radians(),
    };
    let off = render(&raw, pull, false);
    let direct = render(&raw, pull, true);
    // Give a putative color-residual method an optimistic oracle: exact scene
    // values at every R/B output site. No real residual method is asserted to
    // achieve this. This isolates the green sites it cannot alter.
    let mut oracle_rb = direct.clone();
    for y in 0..H {
        for x in 0..W {
            let ch = channel(x, y);
            if ch != 1 {
                let (sx, sy) = pull.at(x as f32, y as f32);
                oracle_rb[y * W + x] = encoded(scene(ch, sx, sy)) as f32 - BLACK;
            }
        }
    }
    let off_rgb = malvar(&off, W, H);
    let direct_rgb = malvar(&direct, W, H);
    let oracle_rgb = malvar(&oracle_rb, W, H);
    let mut square = [0.0_f64; 3];
    let mut count = 0;
    for y in 8..H - 8 {
        for x in 8..W - 8 {
            if channel(x, y) != 1 {
                continue;
            }
            let i = y * W + x;
            let (sx, sy) = pull.at(x as f32, y as f32);
            let truth = scene(1, sx, sy);
            assert_eq!(direct[i].to_bits(), oracle_rb[i].to_bits());
            assert_eq!(
                direct_rgb[3 * i + 1].to_bits(),
                oracle_rgb[3 * i + 1].to_bits(),
                "final MHC altered known green"
            );
            assert_eq!(direct[i].to_bits(), direct_rgb[3 * i + 1].to_bits());
            for (j, v) in [
                off_rgb[3 * i + 1],
                direct_rgb[3 * i + 1],
                oracle_rgb[3 * i + 1],
            ]
            .iter()
            .enumerate()
            {
                let e = *v - truth;
                square[j] += (e * e) as f64;
            }
            count += 1;
        }
    }
    let rms = square.map(|v| (v / count as f64).sqrt());
    let ratio = rms[1] / rms[0];
    println!(
        "CFA_RESIDUAL_FIXED frequency={frequency} degrees={degrees} pull=1 green_sites={count} off_rms={} direct_rms={} perfect_rb_rms={} direct_over_off={} green_unchanged_exact=true",
        rms[0], rms[1], rms[2], ratio
    );
    println!(
        "CFA_RESIDUAL_DECISION {}",
        if ratio > 1.05 {
            "UNCHANGED_GREEN_EXTENSION_CANNOT_REPAIR_THIS_FAILED_GREEN_WITNESS"
        } else {
            "THIS_WITNESS_DOES_NOT_ESTABLISH_A_GREEN_BLOCKER"
        }
    );
    assert!(rms.iter().all(|v| v.is_finite()) && rms[0] > 0.0);
    assert_eq!(rms[1], rms[2]);
}
