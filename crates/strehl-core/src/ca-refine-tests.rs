use super::*;

/// A band-limited texture as a sum of plane waves, so a displaced copy can be
/// sampled exactly at its displaced positions.
struct Texture {
    waves: Vec<(f64, f64, f64, f64)>,
}

impl Texture {
    fn new(seed: u64, only_x: bool) -> Self {
        let mut s = seed;
        let mut next = || {
            s = s
                .wrapping_mul(6364136223846793005)
                .wrapping_add(1442695040888963407);
            ((s >> 11) as f64) / ((1u64 << 53) as f64)
        };
        let waves = (0..48)
            .map(|_| {
                let wavelength = 5.0 + 35.0 * next();
                let angle = if only_x {
                    0.0
                } else {
                    std::f64::consts::TAU * next()
                };
                let k = std::f64::consts::TAU / wavelength;
                (
                    k * angle.cos(),
                    k * angle.sin(),
                    std::f64::consts::TAU * next(),
                    0.5 + next(),
                )
            })
            .collect();
        Self { waves }
    }

    fn at(&self, x: f64, y: f64) -> f64 {
        self.waves
            .iter()
            .map(|(kx, ky, ph, a)| a * (kx * x + ky * y + ph).sin())
            .sum()
    }
}

/// Green is the texture; red and blue are the texture displaced by
/// `t + s * (p - centre)`, with their own gain and offset.
fn image(
    w: usize,
    h: usize,
    tex: &Texture,
    red: ((f64, f64), f64),
    blue: ((f64, f64), f64),
) -> Vec<f32> {
    let (cx, cy) = (w as f64 * 0.5, h as f64 * 0.5);
    let mut rgb = vec![0.0f32; w * h * 3];
    for y in 0..h {
        for x in 0..w {
            let (px, py) = (x as f64, y as f64);
            let shifted = |((tx, ty), s): ((f64, f64), f64)| {
                let (dx, dy) = (tx + s * (px - cx), ty + s * (py - cy));
                tex.at(px - dx, py - dy)
            };
            let i = (y * w + x) * 3;
            rgb[i] = (0.6 * shifted(red) + 7.0) as f32;
            rgb[i + 1] = (tex.at(px, py) + 6.0) as f32;
            rgb[i + 2] = (1.4 * shifted(blue) + 9.0) as f32;
        }
    }
    rgb
}

#[test]
fn a_planted_translation_and_scale_are_recovered_per_channel() {
    let (w, h) = (1536, 1280);
    let tex = Texture::new(7, false);
    let red = ((0.30, -0.20), 400e-6);
    let blue = ((-0.15, 0.25), -300e-6);
    let r = measure(w, h, &image(w, h, &tex, red, blue)).expect("a textured image must fit");
    for (name, fit, planted) in [("red", r.red, red), ("blue", r.blue, blue)] {
        let close = |got: f64, want: f64| (got - want).abs() < 0.02;
        assert!(
            close(fit.translation.0, planted.0.0) && close(fit.translation.1, planted.0.1),
            "{name} translation {:?} vs planted {:?}",
            fit.translation,
            planted.0
        );
        assert!(
            (fit.scale - planted.1).abs() < 25e-6,
            "{name} scale {:.1} ppm vs planted {:.1}",
            fit.scale * 1e6,
            planted.1 * 1e6
        );
        assert!(fit.kept >= MIN_TILES && fit.kept <= fit.measured);
    }
}

#[test]
fn identical_channels_with_different_gains_read_zero() {
    let (w, h) = (1536, 1280);
    let tex = Texture::new(11, false);
    let r = measure(
        w,
        h,
        &image(w, h, &tex, ((0.0, 0.0), 0.0), ((0.0, 0.0), 0.0)),
    )
    .unwrap();
    for fit in [r.red, r.blue] {
        assert!(
            fit.translation.0.abs() < 0.005 && fit.translation.1.abs() < 0.005,
            "{fit:?}"
        );
        assert!(fit.scale.abs() < 5e-6, "{fit:?}");
    }
}

#[test]
fn single_orientation_structure_constrains_only_its_normal() {
    // Vertical stripes only: a horizontal shift is measurable, a vertical one
    // is not, and the fit must not invent one.
    let (w, h) = (1536, 1280);
    let tex = Texture::new(3, true);
    let r = measure(
        w,
        h,
        &image(w, h, &tex, ((0.25, 0.0), 0.0), ((-0.2, 0.0), 0.0)),
    )
    .unwrap();
    assert!((r.red.translation.0 - 0.25).abs() < 0.02, "{:?}", r.red);
    assert!((r.blue.translation.0 + 0.2).abs() < 0.02, "{:?}", r.blue);
    assert!(
        r.red.translation.1.abs() < 0.05 && r.blue.translation.1.abs() < 0.05,
        "{:?} {:?}",
        r.red,
        r.blue
    );
}

#[test]
fn a_featureless_image_gives_no_fit() {
    let (w, h) = (640, 480);
    let rgb = vec![0.5f32; w * h * 3];
    assert!(measure(w, h, &rgb).is_none());
}

#[test]
fn edge_tiles_do_not_vote_on_the_shift_along_their_edges() {
    // Left half: vertical stripes, which see only a horizontal shift. Right
    // half: texture in every direction. A vertical shift is planted
    // everywhere; the stripe tiles cannot see it and must not pull the fit
    // toward zero.
    let (w, h) = (1536, 1280);
    let (stripes, texture) = (Texture::new(3, true), Texture::new(7, false));
    let planted = (0.25, 0.30);
    let f = |x: f64, y: f64| {
        if x < w as f64 * 0.5 {
            stripes.at(x, y)
        } else {
            texture.at(x, y)
        }
    };
    let mut rgb = vec![0.0f32; w * h * 3];
    for y in 0..h {
        for x in 0..w {
            let (px, py) = (x as f64, y as f64);
            let i = (y * w + x) * 3;
            let shifted = f(px - planted.0, py - planted.1);
            rgb[i] = (0.6 * shifted + 7.0) as f32;
            rgb[i + 1] = (f(px, py) + 6.0) as f32;
            rgb[i + 2] = (1.4 * shifted + 9.0) as f32;
        }
    }
    let r = measure(w, h, &rgb).unwrap();
    for fit in [r.red, r.blue] {
        assert!(
            (fit.translation.1 - planted.1).abs() < 0.04,
            "vertical shift {:.3} vs planted {}: edge tiles voted along their edges ({fit:?})",
            fit.translation.1,
            planted.1
        );
    }
}

/// An RGGB mosaic of the texture: green sites sample it in place, red and
/// blue sites sample it displaced.
fn mosaic(w: usize, h: usize, tex: &Texture, red: (f64, f64), blue: (f64, f64)) -> Vec<f32> {
    let mut m = vec![0.0f32; w * h];
    for y in 0..h {
        for x in 0..w {
            let (px, py) = (x as f64, y as f64);
            m[y * w + x] = match (y % 2, x % 2) {
                (0, 0) => 0.6 * tex.at(px - red.0, py - red.1) + 7.0,
                (1, 1) => 1.4 * tex.at(px - blue.0, py - blue.1) + 9.0,
                _ => tex.at(px, py) + 6.0,
            } as f32;
        }
    }
    m
}

#[test]
fn the_mosaic_path_recovers_a_planted_shift_and_reads_zero_without_one() {
    let (w, h) = (1536, 1280);
    let tex = Texture::new(7, false);
    let null = measure_mosaic(w, h, &mosaic(w, h, &tex, (0.0, 0.0), (0.0, 0.0))).unwrap();
    for fit in [null.red, null.blue] {
        assert!(
            fit.translation.0.abs() < 0.01 && fit.translation.1.abs() < 0.01,
            "CFA siting must not read as a shift: {fit:?}"
        );
    }
    let r = measure_mosaic(w, h, &mosaic(w, h, &tex, (0.3, -0.2), (-0.25, 0.15))).unwrap();
    assert!(
        (r.red.translation.0 - 0.3).abs() < 0.04 && (r.red.translation.1 + 0.2).abs() < 0.04,
        "{:?}",
        r.red
    );
    assert!(
        (r.blue.translation.0 + 0.25).abs() < 0.04 && (r.blue.translation.1 - 0.15).abs() < 0.04,
        "{:?}",
        r.blue
    );
}
