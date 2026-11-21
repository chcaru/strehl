//! Heals and backdrop: the neighbourhood stage before per-pixel development,
//! applied identically by the export and the preview patch.
use std::sync::atomic::AtomicBool;
use strehl_edit::*;

fn scene(width: u32, height: u32, f: impl Fn(u32, u32) -> [f32; 3]) -> LinearImage {
    let mut pixels = Vec::with_capacity((width * height * 3) as usize);
    for y in 0..height {
        for x in 0..width {
            pixels.extend(f(x, y));
        }
    }
    LinearImage {
        width,
        height,
        pixels,
        origin: ImageOrigin::SceneLinear,
        baseline: None,
        baked_recipe: None,
    }
}

fn noise(i: u32) -> f32 {
    let mut z = u64::from(i).wrapping_mul(0x9e37_79b9_7f4a_7c15);
    z ^= z >> 29;
    z = z.wrapping_mul(0xbf58_476d_1ce4_e5b9);
    z ^= z >> 32;
    (z % 20_001) as f32 / 10_000.0 - 1.0
}

fn staged(image: &LinearImage, recipe: &DevelopmentRecipe) -> LinearImage {
    LinearImage {
        pixels: Neighbourhood::new(image, recipe).region([0, 0, image.width, image.height]),
        ..image.clone()
    }
}

fn dusty() -> LinearImage {
    scene(200, 150, |x, y| {
        let background = 0.2 + 0.001 * x as f32;
        let d = ((x as f32 - 60.0).powi(2) + (y as f32 - 70.0).powi(2)).sqrt();
        let v = if d < 5.0 {
            background * 0.2
        } else {
            background
        };
        [v, v * 0.9, v * 0.7]
    })
}

fn heal() -> Heal {
    Heal {
        enabled: true,
        center: [60.5 / 200.0, 70.5 / 150.0],
        radius: [8.0 / 200.0, 8.0 / 150.0],
        source_offset: [30.0 / 200.0, 0.0],
    }
}

#[test]
fn a_heal_takes_tone_matched_source_and_leaves_the_rest_bit_identical() {
    let image = dusty();
    let mut recipe = DevelopmentRecipe::default();
    recipe.heals.push(heal());
    recipe.validate().unwrap();
    let out = staged(&image, &recipe);
    let at = |img: &LinearImage, x: u32, y: u32| img.pixels[((y * 200 + x) * 3) as usize];
    let expected = 0.2 + 0.001 * 60.0;
    let healed = at(&out, 60, 70);
    assert!(
        (healed / expected - 1.0).abs() < 0.02,
        "spot became {healed}, want {expected}"
    );
    // Negative control: an unmatched clone of the brighter source misses by 11 %.
    let source = at(&image, 90, 70);
    assert!((source / expected - 1.0).abs() > 0.1);
    for y in 0..150 {
        for x in 0..200 {
            let outside = (x as f32 + 0.5 - 60.5).hypot(y as f32 + 0.5 - 70.5) > 8.5;
            if outside {
                let i = ((y * 200 + x) * 3) as usize;
                assert_eq!(out.pixels[i..i + 3], image.pixels[i..i + 3], "({x},{y})");
            }
        }
    }
}

fn studio() -> (LinearImage, DevelopmentRecipe) {
    // A noisy bright backdrop and a dark subject disc.
    let image = scene(1600, 1000, |x, y| {
        let d = ((x as f32 - 800.0).powi(2) + (y as f32 - 500.0).powi(2)).sqrt();
        let v = if d < 200.0 {
            0.04 * (1.0 + 0.5 * ((x as f32) * 0.3).sin())
        } else {
            0.8 * (1.0 + 0.05 * noise(y * 1600 + x))
        };
        [v; 3]
    });
    let recipe = DevelopmentRecipe {
        backdrop: Some(Backdrop {
            enabled: true,
            threshold: 0.5,
            softness: 1.0,
        }),
        ..Default::default()
    };
    (image, recipe)
}

fn stats(values: impl Iterator<Item = f32>) -> (f64, f64) {
    let v: Vec<f64> = values.map(f64::from).collect();
    let mean = v.iter().sum::<f64>() / v.len() as f64;
    let var = v.iter().map(|x| (x - mean).powi(2)).sum::<f64>() / v.len() as f64;
    (mean, var.sqrt())
}

#[test]
fn the_backdrop_is_smoothed_from_backdrop_only_and_the_subject_is_untouched() {
    let (image, recipe) = studio();
    let out = staged(&image, &recipe);
    let w = 1600u32;
    let ring = |img: &LinearImage, lo: f32, hi: f32| {
        let mut values = Vec::new();
        for y in 0..1000u32 {
            for x in 0..w {
                let d = ((x as f32 - 800.0).powi(2) + (y as f32 - 500.0).powi(2)).sqrt();
                if d >= lo && d < hi {
                    values.push(img.pixels[((y * w + x) * 3) as usize]);
                }
            }
        }
        values
    };
    let (_, before) = stats(ring(&image, 300.0, 400.0).into_iter());
    let (mean, after) = stats(ring(&out, 300.0, 400.0).into_iter());
    println!("backdrop noise sd {before:.5} -> {after:.5}");
    assert!(after < before / 4.0, "{before} -> {after}");
    assert!(
        (mean / 0.8 - 1.0).abs() < 0.005,
        "backdrop level kept: {mean}"
    );
    // The subject, far below the key, is bit-identical.
    let subject = ring(&image, 0.0, 190.0);
    assert_eq!(ring(&out, 0.0, 190.0), subject);
    // No subject bleed into the backdrop right next to it.
    let (edge, _) = stats(ring(&out, 203.0, 206.0).into_iter());
    assert!(
        edge > 0.8 * 0.98,
        "backdrop next to the subject darkened to {edge}"
    );
}

#[test]
fn any_rect_with_its_halo_equals_the_whole_photograph_pass() {
    let (image, mut recipe) = studio();
    recipe.heals.push(Heal {
        enabled: true,
        center: [0.3, 0.3],
        radius: [0.01, 0.016],
        source_offset: [0.1, 0.05],
    });
    let stage = Neighbourhood::new(&image, &recipe);
    assert_eq!(
        stage.halo(),
        3,
        "key 1 + smoothing 2 at a 1600 px long edge"
    );
    let full = stage.region([0, 0, 1600, 1000]);
    for rect in [
        [0, 0, 37, 29],
        [590, 290, 1010, 711],
        [1590, 990, 1600, 1000],
        [400, 250, 401, 900],
    ] {
        let part = stage.region(rect);
        let width = (rect[2] - rect[0]) as usize;
        for y in rect[1]..rect[3] {
            for x in rect[0]..rect[2] {
                let i = (((y - rect[1]) as usize * width) + (x - rect[0]) as usize) * 3;
                let j = ((y * 1600 + x) * 3) as usize;
                assert_eq!(part[i..i + 3], full[j..j + 3], "{rect:?} at ({x},{y})");
            }
        }
    }
}

fn textured() -> (LinearImage, DevelopmentRecipe) {
    let image = scene(300, 600, |x, y| {
        let v = 0.3 + 0.25 * ((x as f32 * 0.21).sin() * (y as f32 * 0.13).cos());
        let v = if y > 300 { v + 0.5 } else { v } + 0.02 * noise(y * 300 + x);
        [v, v * 0.8, v * 0.6]
    });
    let mut recipe = DevelopmentRecipe::default();
    recipe.global.exposure = -0.3;
    recipe.heals.push(Heal {
        enabled: true,
        center: [0.4, 0.45],
        radius: [0.05, 0.025],
        source_offset: [0.2, 0.1],
    });
    recipe.backdrop = Some(Backdrop {
        enabled: true,
        threshold: 0.7,
        softness: 0.5,
    });
    (image, recipe)
}

#[test]
fn the_preview_patch_with_its_halo_matches_the_export_pixels() {
    let (image, recipe) = textured();
    let reference = staged(&image, &recipe);
    let plain = recipe.without_neighbourhood();
    // Crosses the stage's 256-row bands and starts off the origin.
    for stride in [1, 2, 4] {
        let request = DisplayRegionRequest {
            min: [37, 100],
            max: [260, 520],
            stride,
        };
        let patch = image
            .render_display_region(&recipe, request, &AtomicBool::new(false))
            .unwrap();
        let want = reference
            .render_display_region(&plain, request, &AtomicBool::new(false))
            .unwrap();
        assert_eq!(patch.rgb, want.rgb, "stride {stride}");
        assert_eq!(patch.rgba_linear, want.rgba_linear, "stride {stride}");
        // Negative control: without the stage the patch differs.
        let unstaged = image
            .render_display_region(&plain, request, &AtomicBool::new(false))
            .unwrap();
        assert_ne!(patch.rgb, unstaged.rgb);
    }
    // The export and the other renderers apply the same stage.
    let dir = tempfile::tempdir().unwrap();
    let path = dir.path().join("e.tiff");
    let settings = ExportSettings {
        format: ExportFormat::Tiff,
        color_space: OutputColorSpace::Srgb,
        hdr: false,
        ..Default::default()
    };
    export_image(&path, &image, &recipe, &settings, &AtomicBool::new(false)).unwrap();
    let mut decoder = tiff::decoder::Decoder::new(std::fs::File::open(&path).unwrap()).unwrap();
    let tiff::decoder::DecodingResult::U16(exported) = decoder.read_image().unwrap() else {
        panic!()
    };
    assert_eq!(exported, reference.render_sdr16(&plain).unwrap());
    assert_eq!(
        image.render_sdr8(&recipe).unwrap(),
        reference.render_sdr8(&plain).unwrap()
    );
    assert_eq!(
        image
            .render_region_sdr8(&recipe, [0.1, 0.2], [0.9, 0.7], 120)
            .unwrap(),
        reference
            .render_region_sdr8(&plain, [0.1, 0.2], [0.9, 0.7], 120)
            .unwrap()
    );
}
