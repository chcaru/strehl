use super::*;
use crate::{
    Crop, ExportFormat, Heal, ImageOrigin, OutputSharpening, Resize, ResizeFilter, ScaleBar,
    export_image_with,
};

fn plant(width: u32, height: u32) -> LinearImage {
    let mut pixels = Vec::with_capacity(width as usize * height as usize * 3);
    for y in 0..height {
        for x in 0..width {
            pixels.extend([
                0.02 + (x % 97) as f32 / 110.0,
                0.03 + (y % 61) as f32 / 70.0,
                0.04 + ((x * 13 + y * 7) % 41) as f32 / 50.0,
            ]);
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

fn png(settings: &ExportSettings) -> ExportSettings {
    ExportSettings {
        format: ExportFormat::Png,
        color_space: OutputColorSpace::Srgb,
        hdr: false,
        ..settings.clone()
    }
}

/// The 8-bit values the JPEG path would encode, from a 16-bit PNG export
/// of the same settings (the staged pipeline does not depend on the format).
fn exported(
    image: &LinearImage,
    recipe: &DevelopmentRecipe,
    settings: &ExportSettings,
    extras: &ExportExtras<'_>,
) -> ([u32; 2], Vec<u8>) {
    let directory = tempfile::tempdir().unwrap();
    let path = directory.path().join("export.png");
    export_image_with(
        &path,
        image,
        recipe,
        &png(settings),
        extras,
        &AtomicBool::new(false),
    )
    .unwrap();
    let decoded = ::image::open(&path).unwrap().to_rgb16();
    let size = [decoded.width(), decoded.height()];
    let rgb = decoded
        .into_raw()
        .into_iter()
        .map(|v| ((u32::from(v) + 128) / 257) as u8)
        .collect();
    (size, rgb)
}

#[test]
fn preview_pixels_equal_the_exports_for_resize_sharpening_crop_and_scale_bar() {
    let image = plant(400, 300);
    let mut recipe = DevelopmentRecipe::default();
    recipe.global.exposure = 0.3;
    recipe.global.contrast = 15.0;
    recipe.heals.push(Heal {
        center: [0.5, 0.5],
        radius: [0.03, 0.04],
        source_offset: [0.08, 0.0],
        enabled: true,
    });
    recipe.scale_bar = Some(ScaleBar {
        length_um: 100.0,
        corner: Default::default(),
        style: Default::default(),
        enabled: true,
    });
    let extras = ExportExtras {
        um_per_px: Some(2.0),
        ..Default::default()
    };
    let web = ExportSettings {
        format: ExportFormat::Jpeg,
        color_space: OutputColorSpace::Srgb,
        hdr: false,
        quality: 90,
        resize: Some(Resize {
            long_edge: 160,
            filter: ResizeFilter::Mitchell,
        }),
        ..Default::default()
    };
    let cases = [
        ("resize", None, web.clone()),
        (
            "resize, sharpening, scale bar, crop",
            Some(Crop {
                min: [0.1, 0.15],
                max: [0.85, 0.9],
                angle_deg: 0.0,
            }),
            ExportSettings {
                sharpen: Some(OutputSharpening::default()),
                scale_bar: true,
                ..web.clone()
            },
        ),
        (
            "straightened crop, sharpening at full size",
            Some(Crop {
                min: [0.1, 0.1],
                max: [0.9, 0.9],
                angle_deg: 2.0,
            }),
            ExportSettings {
                resize: None,
                sharpen: Some(OutputSharpening {
                    amount: 0.8,
                    ..Default::default()
                }),
                ..web.clone()
            },
        ),
    ];
    for (name, crop, settings) in cases {
        let mut recipe = recipe.clone();
        recipe.crop = crop;
        let preview =
            render_export_preview(&image, &recipe, &settings, &extras, &AtomicBool::new(false))
                .unwrap()
                .expect(name);
        let (size, expected) = exported(&image, &recipe, &settings, &extras);
        assert_eq!(preview.size, size, "{name}");
        assert_eq!(preview.rgb.len(), expected.len(), "{name}");
        let differing = preview
            .rgb
            .iter()
            .zip(&expected)
            .filter(|(a, b)| a != b)
            .count();
        assert_eq!(
            differing, 0,
            "{name}: {differing} values differ from the export"
        );
        // Negative control: a different sharpening must be caught.
        let other = ExportSettings {
            sharpen: Some(OutputSharpening {
                amount: 1.6,
                ..Default::default()
            }),
            ..settings.clone()
        };
        let changed =
            render_export_preview(&image, &recipe, &other, &extras, &AtomicBool::new(false))
                .unwrap()
                .unwrap();
        assert_ne!(
            changed.rgb, expected,
            "{name}: the comparison must be able to fail"
        );
    }
}

#[test]
fn an_export_without_stages_is_the_development_and_cancellation_is_refused() {
    let image = plant(64, 48);
    let recipe = DevelopmentRecipe::default();
    let plain = ExportSettings {
        format: ExportFormat::Tiff,
        color_space: OutputColorSpace::DisplayP3,
        hdr: false,
        ..Default::default()
    };
    assert!(
        render_export_preview(
            &image,
            &recipe,
            &plain,
            &ExportExtras::default(),
            &AtomicBool::new(false)
        )
        .unwrap()
        .is_none()
    );
    // A resize that does not shrink is no stage either.
    let unchanged = ExportSettings {
        resize: Some(Resize {
            long_edge: 4096,
            filter: ResizeFilter::Mitchell,
        }),
        ..plain.clone()
    };
    assert!(
        render_export_preview(
            &image,
            &recipe,
            &unchanged,
            &ExportExtras::default(),
            &AtomicBool::new(false)
        )
        .unwrap()
        .is_none()
    );
    let staged = ExportSettings {
        resize: Some(Resize {
            long_edge: 32,
            filter: ResizeFilter::Mitchell,
        }),
        ..plain
    };
    assert!(
        render_export_preview(
            &image,
            &recipe,
            &staged,
            &ExportExtras::default(),
            &AtomicBool::new(true)
        )
        .is_err()
    );
    let preview = render_export_preview(
        &image,
        &recipe,
        &staged,
        &ExportExtras::default(),
        &AtomicBool::new(false),
    )
    .unwrap()
    .unwrap();
    assert_eq!(preview.size, [32, 24]);
    assert_eq!(preview.developed, [64, 48]);
}
