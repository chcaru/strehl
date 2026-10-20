//! Independent choice points: odd edge bins, asymmetric ellipse coordinates,
//! and metadata corruption in the inexpensive SDR-only path.
use std::sync::atomic::AtomicBool;
use strehl_edit::*;

fn image(width: u32, height: u32, pixel: impl Fn(u32, u32) -> [f32; 3]) -> LinearImage {
    let mut pixels = Vec::new();
    for y in 0..height {
        for x in 0..width {
            pixels.extend_from_slice(&pixel(x, y));
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

#[test]
fn odd_coarse_bins_include_the_last_source_row_and_column() {
    let image = image(41, 29, |x, y| {
        [if x == 37 || y == 23 { 1.0 } else { 0.0 }; 3]
    });
    let patch = image
        .render_display_region(
            &DevelopmentRecipe::default(),
            DisplayRegionRequest {
                min: [3, 5],
                max: [38, 24],
                stride: 8,
            },
            &AtomicBool::new(false),
        )
        .unwrap();
    assert_eq!(patch.size, [5, 3]);
    assert_eq!(patch.source_samples, 35 * 19);
    // Independent count: a 35-pixel bottom row plus an 18-pixel right edge.
    // Five seven-wide bins; the three row bins have heights 6, 6, and 7.
    let mut total = 0.0;
    let mut nonzero = 0;
    for (i, p) in patch.rgba_linear.as_chunks::<4>().0.iter().enumerate() {
        total += f64::from(p[0]) * 7.0 * [6.0, 6.0, 7.0][i / 5];
        nonzero += usize::from(p[0] > 0.0);
        assert_eq!(&p[..3], &[p[0]; 3], "a gray pattern acquired chroma");
        assert_eq!(p[3], 1.0);
    }
    assert_eq!(nonzero, 7, "the bottom and right edge must both appear");
    assert!(
        (total - 53.0).abs() < 1e-5,
        "source coverage changed: {total}"
    );
}

#[test]
fn asymmetric_native_region_keeps_ellipse_on_the_full_photograph() {
    let image = image(83, 37, |_, _| [0.125; 3]);
    let mut recipe = DevelopmentRecipe::default();
    recipe.regions.push(RegionAdjustment {
        id: "independent-ellipse".into(),
        name: "Off-center ellipse".into(),
        note: String::new(),
        shape: RegionShape::Ellipse {
            center: [0.70, 0.30],
            radius: [0.12, 0.18],
        },
        feather: 0.0,
        enabled: true,
        adjustments: Adjustments {
            exposure: 1.0,
            ..Default::default()
        },
        source_range: None,
    });
    let region = DisplayRegionRequest {
        min: [41, 3],
        max: [79, 28],
        stride: 1,
    };
    let patch = image
        .render_display_region(&recipe, region, &AtomicBool::new(false))
        .unwrap();
    let whole = image.render_sdr8(&recipe).unwrap();
    let mut changed = 0;
    let mut unchanged = 0;
    for y in 3..28 {
        for x in 41..79 {
            let i = ((y - 3) * 38 + x - 41) as usize;
            let full = (y * 83 + x) as usize;
            assert_eq!(&patch.rgb[i * 3..i * 3 + 3], &whole[full * 3..full * 3 + 3]);
            let linear = patch.rgba_linear[i * 4];
            if (54..62).contains(&x) && (8..14).contains(&y) {
                assert_eq!(linear, 0.25, "interior ellipse moved with the crop");
                changed += 1;
            }
            if x > 70 || y > 23 {
                assert_eq!(linear, 0.125, "unmarked flat field changed");
                unchanged += 1;
            }
        }
    }
    assert!(
        changed > 20 && unchanged > 100,
        "both spatial controls must be exercised"
    );
    let flat = image
        .render_display_region(
            &DevelopmentRecipe::default(),
            DisplayRegionRequest {
                stride: 8,
                ..region
            },
            &AtomicBool::new(false),
        )
        .unwrap();
    assert!(
        flat.rgba_linear
            .as_chunks::<4>()
            .0
            .iter()
            .all(|p| p[..3] == [0.125; 3])
    );
}

#[test]
fn sdr_only_path_rejects_nonfinite_baseline_without_reading_unrequested_pixels() {
    let mut image = image(17, 11, |_, _| [0.2; 3]);
    let region = DisplayRegionRequest {
        min: [2, 3],
        max: [7, 8],
        stride: 1,
    };
    // A valid crop must not fail merely because an unrequested pixel is invalid.
    image.pixels[0] = f32::NAN;
    assert!(
        image
            .render_display_region_mode(
                &DevelopmentRecipe::default(),
                region,
                &AtomicBool::new(false),
                false
            )
            .is_ok()
    );
    image.baseline = Some(DisplayBaseline {
        black: 0.0,
        white: 1.0,
        contrast: f32::NAN,
        exposure_gain: 1.0,
    });
    assert!(
        image
            .render_display_region_mode(
                &DevelopmentRecipe::default(),
                region,
                &AtomicBool::new(false),
                false
            )
            .is_err()
    );
}
