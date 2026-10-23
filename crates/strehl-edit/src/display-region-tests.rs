use super::*;
use crate::{Adjustments, RegionAdjustment, RegionShape};

fn plant(width: u32, height: u32, pixel: impl Fn(u32, u32) -> [f32; 3]) -> LinearImage {
    let mut pixels = Vec::with_capacity(width as usize * height as usize * 3);
    for y in 0..height {
        for x in 0..width {
            pixels.extend(pixel(x, y));
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

fn render(
    image: &LinearImage,
    recipe: &DevelopmentRecipe,
    min: [u32; 2],
    max: [u32; 2],
    stride: u32,
) -> DisplayRegion {
    image
        .render_display_region(
            recipe,
            DisplayRegionRequest { min, max, stride },
            &AtomicBool::new(false),
        )
        .unwrap()
}

#[test]
fn coarse_preview_rejects_checker_aliasing_and_preserves_a_flat_control() {
    let checker = plant(
        128,
        96,
        |x, y| if (x + y) % 2 == 0 { [0.0; 3] } else { [1.0; 3] },
    );
    let coarse = render(
        &checker,
        &DevelopmentRecipe::default(),
        [0, 0],
        [128, 96],
        8,
    );
    assert!(
        coarse
            .rgba_linear
            .as_chunks::<4>()
            .0
            .iter()
            .all(|p| p[..3] == [0.5; 3])
    );
    let native = render(
        &checker,
        &DevelopmentRecipe::default(),
        [32, 24],
        [64, 48],
        1,
    );
    assert!(
        native.rgb.contains(&0) && native.rgb.contains(&255),
        "Native detail must recover the alternating pixels"
    );
    let flat = plant(128, 96, |_, _| [0.25; 3]);
    let coarse = render(&flat, &DevelopmentRecipe::default(), [0, 0], [128, 96], 8);
    let native = render(&flat, &DevelopmentRecipe::default(), [32, 24], [64, 48], 1);
    assert!(
        coarse
            .rgba_linear
            .as_chunks::<4>()
            .0
            .iter()
            .all(|p| p[..3] == [0.25; 3])
    );
    assert!(
        native
            .rgba_linear
            .as_chunks::<4>()
            .0
            .iter()
            .all(|p| p[..3] == [0.25; 3]),
        "Refinement must not manufacture contrast on a flat field"
    );
}

#[test]
fn native_region_matches_original_sdr_and_keeps_global_annotation_coordinates() {
    let image = plant(63, 47, |x, y| {
        [0.03 + x as f32 * 0.005, 0.02 + y as f32 * 0.009, 0.1]
    });
    let mut recipe = DevelopmentRecipe::default();
    recipe.regions.push(RegionAdjustment {
        id: "right".into(),
        name: "Right".into(),
        note: String::new(),
        shape: RegionShape::Rectangle {
            min: [0.5, 0.0],
            max: [1.0, 1.0],
        },
        feather: 0.0,
        enabled: true,
        source_range: None,
        adjustments: Adjustments {
            exposure: 1.0,
            ..Default::default()
        },
    });
    let patch = render(&image, &recipe, [21, 9], [54, 31], 1);
    let mut changed_left = false;
    let mut changed_right = false;
    for y in 9..31 {
        for x in 21..54 {
            let p = ((y - 9) * 33 + x - 21) as usize;
            let expected = image
                .display_pixel((y * 63 + x) as usize, &recipe)
                .map(|v| (v * 255.0 + 0.5) as u8);
            assert_eq!(&patch.rgb[p * 3..p * 3 + 3], &expected);
            let original = image
                .display_pixel((y * 63 + x) as usize, &DevelopmentRecipe::default())
                .map(|v| (v * 255.0 + 0.5) as u8);
            if x < 31 {
                changed_left |= expected != original;
            }
            if x > 32 {
                changed_right |= expected != original;
            }
        }
    }
    assert!(
        !changed_left && changed_right,
        "The region must remain on the full photo's right half"
    );
    assert_eq!(patch.source_samples, 33 * 22);
}

#[test]
fn float_display_keeps_real_highlights_and_sdr_import_has_no_invented_headroom() {
    let mut image = plant(16, 4, |x, _| [x as f32 * 0.25; 3]);
    let hdr = render(&image, &DevelopmentRecipe::default(), [0, 0], [16, 4], 1);
    assert!(hdr.rgba_linear.iter().any(|&v| v > 3.0));
    image.origin = ImageOrigin::DisplayReferred;
    let sdr = render(&image, &DevelopmentRecipe::default(), [0, 0], [16, 4], 1);
    assert!(sdr.rgba_linear.iter().all(|&v| v <= 1.0));
}

#[test]
fn invalid_and_cancelled_work_is_refused_before_publication() {
    let image = plant(64, 48, |_, _| [0.1; 3]);
    let request = DisplayRegionRequest {
        min: [0, 0],
        max: [64, 48],
        stride: 1,
    };
    assert!(
        image
            .render_display_region(
                &DevelopmentRecipe::default(),
                request,
                &AtomicBool::new(true)
            )
            .is_err()
    );
    for bad in [
        DisplayRegionRequest {
            stride: 3,
            ..request
        },
        DisplayRegionRequest {
            max: [65, 48],
            ..request
        },
        DisplayRegionRequest {
            min: [64, 0],
            ..request
        },
    ] {
        assert!(
            image
                .render_display_region(&DevelopmentRecipe::default(), bad, &AtomicBool::new(false))
                .is_err()
        );
    }
}

#[test]
fn sdr_only_pixels_match_combined_without_allocating_float_payload() {
    let image = plant(71, 53, |x, y| [x as f32 / 71.0, y as f32 / 53.0, 0.3]);
    let request = DisplayRegionRequest {
        min: [5, 7],
        max: [68, 51],
        stride: 4,
    };
    let both = render(
        &image,
        &DevelopmentRecipe::default(),
        request.min,
        request.max,
        request.stride,
    );
    let sdr = image
        .render_display_region_mode(
            &DevelopmentRecipe::default(),
            request,
            &AtomicBool::new(false),
            false,
        )
        .unwrap();
    assert_eq!(sdr.rgb, both.rgb);
    assert!(sdr.rgba_linear.is_empty());
    assert_eq!(sdr.source_samples, 63 * 44);
}
#[test]
fn cancellation_during_development_publishes_no_partial_pixels() {
    let image = plant(2048, 1536, |_, _| [0.2; 3]);
    let cancel = std::sync::Arc::new(AtomicBool::new(false));
    let worker_cancel = cancel.clone();
    let worker = std::thread::spawn(move || {
        image.render_display_region(
            &DevelopmentRecipe::default(),
            DisplayRegionRequest {
                min: [0, 0],
                max: [2048, 1536],
                stride: 1,
            },
            &worker_cancel,
        )
    });
    std::thread::sleep(std::time::Duration::from_millis(1));
    cancel.store(true, Ordering::Relaxed);
    assert!(
        worker.join().unwrap().is_err(),
        "A cancelled refinement must not return a partially developed patch"
    );
}
