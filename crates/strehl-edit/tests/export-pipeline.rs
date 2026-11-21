//! P7 export stages: recipe switch, crop and straighten, resize, output
//! sharpening (with its flat-ROI control), scale bar, metadata, coverage.
use std::{path::Path, sync::atomic::AtomicBool};
use strehl_edit::*;
use tiff::{decoder::Decoder, tags::Tag};

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

fn textured(width: u32, height: u32) -> LinearImage {
    scene(width, height, |x, y| {
        let (x, y) = (x as f32, y as f32);
        [
            0.05 + 0.4 * ((x * 0.37).sin() * (y * 0.21).cos()).abs(),
            0.02 + 0.3 * ((x + 2.0 * y) * 0.11).sin().abs(),
            0.04 + 0.002 * x,
        ]
    })
}

fn sdr(format: ExportFormat) -> ExportSettings {
    ExportSettings {
        format,
        color_space: OutputColorSpace::Srgb,
        hdr: false,
        quality: 92,
        ..Default::default()
    }
}

fn export(
    dir: &Path,
    name: &str,
    image: &LinearImage,
    recipe: &DevelopmentRecipe,
    settings: &ExportSettings,
    extras: &ExportExtras<'_>,
) -> anyhow::Result<(ExportReport, std::path::PathBuf)> {
    let path = dir.join(name);
    let report = export_image_with(
        &path,
        image,
        recipe,
        settings,
        extras,
        &AtomicBool::new(false),
    )?;
    Ok((report, path))
}

/// Decoded TIFF: size, samples per pixel and u16 samples.
fn tiff16(path: &Path) -> (u32, u32, Vec<u16>) {
    let mut decoder = Decoder::new(std::fs::File::open(path).unwrap()).unwrap();
    let (w, h) = decoder.dimensions().unwrap();
    let tiff::decoder::DecodingResult::U16(v) = decoder.read_image().unwrap() else {
        panic!("16-bit TIFF expected")
    };
    (w, h, v)
}

fn tag_text(path: &Path, tag: Tag) -> Option<String> {
    let mut decoder = Decoder::new(std::fs::File::open(path).unwrap()).unwrap();
    decoder.get_tag_ascii_string(tag).ok()
}

#[test]
fn recipe_switch_is_off_by_default_and_reproduces_the_old_description_when_on() {
    let dir = tempfile::tempdir().unwrap();
    let image = textured(32, 24);
    let mut recipe = DevelopmentRecipe::default();
    recipe.global.exposure = 0.5;
    assert!(!ExportSettings::default().embed_recipe);
    let (_, off) = export(
        dir.path(),
        "off.tiff",
        &image,
        &recipe,
        &sdr(ExportFormat::Tiff),
        &Default::default(),
    )
    .unwrap();
    assert_eq!(
        tag_text(&off, Tag::ImageDescription).unwrap(),
        "sRGB / BT.709 primaries, D65, sRGB transfer"
    );
    let on_settings = ExportSettings {
        embed_recipe: true,
        ..sdr(ExportFormat::Tiff)
    };
    let (report, on) = export(
        dir.path(),
        "on.tiff",
        &image,
        &recipe,
        &on_settings,
        &Default::default(),
    )
    .unwrap();
    assert_eq!(report.metadata, vec!["recipe"]);
    let text = tag_text(&on, Tag::ImageDescription).unwrap();
    let json = text
        .strip_prefix("sRGB / BT.709 primaries, D65, sRGB transfer; Strehl development recipe: ")
        .unwrap();
    assert_eq!(
        serde_json::from_str::<DevelopmentRecipe>(json).unwrap(),
        recipe
    );
    assert_eq!(tiff16(&off).2, tiff16(&on).2, "the switch changes no pixel");
    // Only TIFF carries it.
    let png = ExportSettings {
        embed_recipe: true,
        ..sdr(ExportFormat::Png)
    };
    assert!(
        export(
            dir.path(),
            "x.png",
            &image,
            &recipe,
            &png,
            &Default::default()
        )
        .is_err()
    );
    assert!(!dir.path().join("x.png").exists());
}

#[test]
fn a_recipe_with_non_ascii_names_embeds_as_escaped_json() {
    // Before P7 this TIFF export failed: TIFF ASCII tags refuse UTF-8.
    let dir = tempfile::tempdir().unwrap();
    let mut recipe = DevelopmentRecipe::default();
    recipe.regions.push(RegionAdjustment {
        id: "bug".into(),
        name: "昆虫 · weevil".into(),
        note: "élytres".into(),
        shape: RegionShape::Ellipse {
            center: [0.5, 0.5],
            radius: [0.2, 0.2],
        },
        feather: 0.3,
        enabled: true,
        adjustments: Adjustments {
            exposure: 0.4,
            ..Default::default()
        },
        source_range: None,
    });
    let settings = ExportSettings {
        embed_recipe: true,
        ..sdr(ExportFormat::Tiff)
    };
    let (_, path) = export(
        dir.path(),
        "u.tiff",
        &textured(24, 16),
        &recipe,
        &settings,
        &Default::default(),
    )
    .unwrap();
    let text = tag_text(&path, Tag::ImageDescription).unwrap();
    assert!(text.is_ascii());
    let json = text.split("Strehl development recipe: ").nth(1).unwrap();
    assert_eq!(
        serde_json::from_str::<DevelopmentRecipe>(json).unwrap(),
        recipe
    );
}

#[test]
fn an_unturned_crop_is_the_exact_window_of_the_full_export() {
    let dir = tempfile::tempdir().unwrap();
    let image = textured(97, 61);
    let mut recipe = DevelopmentRecipe::default();
    recipe.regions.push(RegionAdjustment {
        id: "r".into(),
        name: "r".into(),
        note: String::new(),
        shape: RegionShape::Ellipse {
            center: [0.45, 0.5],
            radius: [0.2, 0.3],
        },
        feather: 0.5,
        enabled: true,
        adjustments: Adjustments {
            exposure: 1.0,
            ..Default::default()
        },
        source_range: None,
    });
    let (_, full) = export(
        dir.path(),
        "full.tiff",
        &image,
        &recipe,
        &sdr(ExportFormat::Tiff),
        &Default::default(),
    )
    .unwrap();
    let crop = Crop {
        min: [0.2, 0.3],
        max: [0.7, 0.9],
        angle_deg: 0.0,
    };
    recipe.crop = Some(crop);
    let (report, cropped) = export(
        dir.path(),
        "crop.tiff",
        &image,
        &recipe,
        &sdr(ExportFormat::Tiff),
        &Default::default(),
    )
    .unwrap();
    let [x0, y0, x1, y1] = crop.pixel_rect(97, 61);
    assert_eq!((report.width, report.height), (x1 - x0, y1 - y0));
    assert_eq!(report.crop, Some(crop));
    let (_, _, a) = tiff16(&full);
    let (w, h, b) = tiff16(&cropped);
    for y in 0..h {
        for x in 0..w {
            let i = ((y * w + x) * 3) as usize;
            let j = (((y + y0) * 97 + x + x0) * 3) as usize;
            assert_eq!(
                &b[i..i + 3],
                &a[j..j + 3],
                "regions stay registered at ({x},{y})"
            );
        }
    }
}

/// A bright line through the centre descending to the right at `deg`.
fn horizon(deg: f32) -> LinearImage {
    let (sin, cos) = deg.to_radians().sin_cos();
    scene(400, 300, |x, y| {
        let d = (-(x as f32 + 0.5 - 200.0) * sin + (y as f32 + 0.5 - 150.0) * cos).abs();
        [0.05 + 0.9 * (-(d / 1.5).powi(2)).exp(); 3]
    })
}

fn ridge_rows(path: &Path) -> Vec<u32> {
    let (w, h, v) = tiff16(path);
    (0..w)
        .map(|x| {
            (0..h)
                .max_by_key(|&y| v[((y * w + x) * 3) as usize])
                .unwrap()
        })
        .collect()
}

#[test]
fn a_straightened_crop_levels_a_horizon_descending_to_the_right() {
    let dir = tempfile::tempdir().unwrap();
    let image = horizon(6.0);
    let mut recipe = DevelopmentRecipe::default();
    let crop = Crop {
        min: [0.25, 0.25],
        max: [0.75, 0.75],
        angle_deg: 0.0,
    };
    recipe.crop = Some(crop);
    let (_, flat) = export(
        dir.path(),
        "flat.tiff",
        &image,
        &recipe,
        &sdr(ExportFormat::Tiff),
        &Default::default(),
    )
    .unwrap();
    let rows = ridge_rows(&flat);
    let drift = rows.iter().max().unwrap() - rows.iter().min().unwrap();
    assert!(
        drift > 15,
        "negative control: the unturned crop keeps the tilt ({drift})"
    );
    recipe.crop = Some(Crop {
        angle_deg: 6.0,
        ..crop
    });
    let (report, turned) = export(
        dir.path(),
        "turned.tiff",
        &image,
        &recipe,
        &sdr(ExportFormat::Tiff),
        &Default::default(),
    )
    .unwrap();
    assert_eq!((report.width, report.height), (200, 150));
    let rows = ridge_rows(&turned);
    let drift = rows.iter().max().unwrap() - rows.iter().min().unwrap();
    assert!(drift <= 1, "levelled horizon drifts {drift} rows");
    assert!((74..=75).contains(&rows[100]));
    // A turned crop past the photograph is refused before any file exists.
    recipe.crop = Some(Crop {
        min: [0.0, 0.0],
        max: [1.0, 1.0],
        angle_deg: 6.0,
    });
    assert!(
        export(
            dir.path(),
            "over.tiff",
            &image,
            &recipe,
            &sdr(ExportFormat::Tiff),
            &Default::default()
        )
        .is_err()
    );
    assert!(!dir.path().join("over.tiff").exists());
}

#[test]
fn resize_keeps_hdr_headroom_and_never_enlarges() {
    let dir = tempfile::tempdir().unwrap();
    let image = scene(300, 200, |_, _| [3.0; 3]);
    let recipe = DevelopmentRecipe::default();
    let settings = ExportSettings {
        speed: 10,
        resize: Some(Resize {
            long_edge: 100,
            filter: ResizeFilter::Mitchell,
        }),
        ..Default::default()
    };
    let (report, _) = export(
        dir.path(),
        "hdr.avif",
        &image,
        &recipe,
        &settings,
        &Default::default(),
    )
    .unwrap();
    assert_eq!((report.width, report.height), (100, 67));
    assert_eq!(report.resized_from, Some([300, 200]));
    let hdr = report.hdr_metadata.unwrap();
    // 3.0 x 203 nits survives; a 0..1 clamp would report 203.
    assert_eq!(hdr.max_content_light_nits, 609);
    assert_eq!((hdr.width, hdr.height), (100, 67));
    let larger = ExportSettings {
        resize: Some(Resize {
            long_edge: 1000,
            filter: ResizeFilter::Lanczos3,
        }),
        ..sdr(ExportFormat::Png)
    };
    let (report, _) = export(
        dir.path(),
        "same.png",
        &image,
        &recipe,
        &larger,
        &Default::default(),
    )
    .unwrap();
    assert_eq!(
        (report.width, report.height, report.resized_from),
        (300, 200, None)
    );
}

#[test]
fn the_buffered_path_without_work_matches_the_fused_path_byte_for_byte() {
    // Sharpening with amount 0 routes through the f32 buffer and does nothing.
    let dir = tempfile::tempdir().unwrap();
    let image = textured(64, 48);
    let mut recipe = DevelopmentRecipe::default();
    recipe.global.contrast = 25.0;
    for (format, space) in [
        (ExportFormat::Tiff, OutputColorSpace::DisplayP3),
        (ExportFormat::Png, OutputColorSpace::Srgb),
        (ExportFormat::Avif, OutputColorSpace::Rec2020),
    ] {
        let plain = ExportSettings {
            color_space: space,
            speed: 10,
            ..sdr(format)
        };
        let idle = ExportSettings {
            sharpen: Some(OutputSharpening {
                amount: 0.0,
                ..Default::default()
            }),
            ..plain.clone()
        };
        let (_, a) = export(
            dir.path(),
            &format!("a-{format:?}"),
            &image,
            &recipe,
            &plain,
            &Default::default(),
        )
        .unwrap();
        let (report, b) = export(
            dir.path(),
            &format!("b-{format:?}"),
            &image,
            &recipe,
            &idle,
            &Default::default(),
        )
        .unwrap();
        assert!(!report.sharpened);
        assert_eq!(
            std::fs::read(a).unwrap(),
            std::fs::read(b).unwrap(),
            "{format:?}"
        );
    }
}

/// Mean squared forward difference of coded values over an interior ROI.
fn gradient_energy(path: &Path, roi: [u32; 4]) -> f64 {
    let (w, _, v) = tiff16(path);
    let at = |x: u32, y: u32| f64::from(v[((y * w + x) * 3 + 1) as usize]) / 65535.0;
    let mut sum = 0.0;
    let mut n = 0.0;
    for y in roi[1]..roi[3] {
        for x in roi[0]..roi[2] {
            let dx = at(x + 1, y) - at(x, y);
            let dy = at(x, y + 1) - at(x, y);
            sum += dx * dx + dy * dy;
            n += 1.0;
        }
    }
    sum / n
}

fn noise(i: u32) -> f32 {
    // Deterministic uniform noise in -1..1.
    let mut z = u64::from(i).wrapping_mul(0x9e37_79b9_7f4a_7c15);
    z ^= z >> 29;
    z = z.wrapping_mul(0xbf58_476d_1ce4_e5b9);
    z ^= z >> 32;
    (z % 20_001) as f32 / 10_000.0 - 1.0
}

#[test]
fn output_sharpening_passes_the_flat_roi_control_before_any_edge_claim() {
    // Engineering ledger rule 9: the flat-ROI control runs first; a metric that
    // fails it invalidates every number computed with it.
    let dir = tempfile::tempdir().unwrap();
    let recipe = DevelopmentRecipe::default();
    let flat = scene(160, 160, |x, y| {
        [0.18 * (1.0 + 0.08 * noise(y * 160 + x)); 3]
    });
    let roi = [8, 8, 150, 150];
    let run = |name: &str, image: &LinearImage, sharpen: Option<OutputSharpening>| {
        let settings = ExportSettings {
            sharpen,
            ..sdr(ExportFormat::Tiff)
        };
        export(
            dir.path(),
            name,
            image,
            &recipe,
            &settings,
            &Default::default(),
        )
        .unwrap()
        .1
    };
    let base = gradient_energy(&run("flat.tiff", &flat, None), roi);
    let conservative = gradient_energy(
        &run("flat-usm.tiff", &flat, Some(OutputSharpening::default())),
        roi,
    );
    let uncored = gradient_energy(
        &run(
            "flat-raw.tiff",
            &flat,
            Some(OutputSharpening {
                threshold: 0.0,
                ..Default::default()
            }),
        ),
        roi,
    );
    println!(
        "flat ROI gradient energy: plain {base:.3e}, default {:+.2}%, uncored {:+.2}%",
        (conservative / base - 1.0) * 100.0,
        (uncored / base - 1.0) * 100.0
    );
    // The control can fail: without coring the same pass inflates flat ground.
    assert!(uncored > base * 1.10, "metric must see sharpened noise");
    assert!(
        conservative < base * 1.01,
        "default sharpening raised flat-ROI energy"
    );
    // Only now the edge: a soft step gains acutance under the default.
    let edge = scene(160, 160, |x, _| {
        let t = 1.0 / (1.0 + (-(x as f32 - 80.0) / 0.5).exp());
        [0.03 + 0.5 * t; 3]
    });
    let edge_roi = [70, 8, 90, 150];
    let plain = gradient_energy(&run("edge.tiff", &edge, None), edge_roi);
    let sharpened = gradient_energy(
        &run("edge-usm.tiff", &edge, Some(OutputSharpening::default())),
        edge_roi,
    );
    println!(
        "edge ROI gradient energy: {:+.2}%",
        (sharpened / plain - 1.0) * 100.0
    );
    assert!(sharpened > plain * 1.05);
}

#[test]
fn sharpening_keeps_hue_and_saturation() {
    let dir = tempfile::tempdir().unwrap();
    let image = scene(80, 40, |x, _| {
        if x < 40 {
            [0.05, 0.02, 0.01]
        } else {
            [0.4, 0.16, 0.08]
        }
    });
    let settings = ExportSettings {
        sharpen: Some(OutputSharpening::default()),
        ..sdr(ExportFormat::Tiff)
    };
    let (report, path) = export(
        dir.path(),
        "c.tiff",
        &image,
        &DevelopmentRecipe::default(),
        &settings,
        &Default::default(),
    )
    .unwrap();
    assert!(report.sharpened);
    let (w, _, v) = tiff16(&path);
    for x in 30..50u32 {
        let i = ((20 * w + x) * 3) as usize;
        let lin = |c: usize| {
            let e = f64::from(v[i + c]) / 65535.0;
            if e <= 0.04045 {
                e / 12.92
            } else {
                ((e + 0.055) / 1.055).powf(2.4)
            }
        };
        let ratio = lin(0) / lin(2);
        assert!((ratio - 5.0).abs() < 0.2, "x={x}: red/blue {ratio}");
    }
}

fn png_rgb16(path: &Path) -> (u32, u32, Vec<u16>) {
    let image = image::open(path).unwrap().into_rgb16();
    (image.width(), image.height(), image.into_raw())
}

#[test]
fn the_scale_bar_burns_at_its_calibrated_length_and_follows_resize() {
    let dir = tempfile::tempdir().unwrap();
    let image = scene(400, 300, |_, _| [0.0; 3]);
    let recipe = DevelopmentRecipe {
        scale_bar: Some(ScaleBar {
            enabled: true,
            length_um: 100.0,
            corner: ScaleBarCorner::BottomRight,
            style: ScaleBarStyle::Light,
        }),
        ..Default::default()
    };
    let on = ExportSettings {
        scale_bar: true,
        ..sdr(ExportFormat::Png)
    };
    let extras = ExportExtras {
        um_per_px: Some(0.5),
        ..Default::default()
    };
    let bar_columns = |path: &Path| {
        let (w, h, v) = png_rgb16(path);
        let row = (0..h)
            .rev()
            .find(|&y| (0..w).any(|x| v[((y * w + x) * 3) as usize] > 60_000))
            .unwrap();
        let cols: Vec<u32> = (0..w)
            .filter(|&x| v[((row * w + x) * 3) as usize] > 30_000)
            .collect();
        (row, cols, v, w)
    };
    let (report, path) = export(dir.path(), "bar.png", &image, &recipe, &on, &extras).unwrap();
    let bar = report.scale_bar.unwrap();
    assert_eq!(bar.length_px, 200.0);
    let (row, cols, v, w) = bar_columns(&path);
    assert_eq!(cols.len(), 200, "bar spans its calibrated length");
    assert_eq!(
        (cols[0], *cols.last().unwrap()),
        (188, 387),
        "4 % margin at the right"
    );
    assert!(row > 280);
    let label_pixels = (200..row - 2)
        .flat_map(|y| (150..400).map(move |x| (x, y)))
        .filter(|&(x, y)| v[((y * w + x) * 3) as usize] > 30_000)
        .count();
    if scale_bar_font().is_some() {
        assert_eq!(bar.label.as_deref(), Some("100 µm"));
        assert!(label_pixels > 50, "label drawn above the bar");
    } else {
        assert!(bar.label.is_none() && label_pixels == 0);
    }
    // Half size: each output pixel is 1 µm, so the bar is 100 px.
    let small = ExportSettings {
        resize: Some(Resize {
            long_edge: 200,
            filter: ResizeFilter::Mitchell,
        }),
        ..on.clone()
    };
    let (report, path) = export(dir.path(), "half.png", &image, &recipe, &small, &extras).unwrap();
    assert_eq!(report.scale_bar.unwrap().um_per_px, 1.0);
    assert_eq!(bar_columns(&path).1.len(), 100);
    // Refusals: no calibration, or a bar longer than the photograph.
    assert!(
        export(
            dir.path(),
            "nocal.png",
            &image,
            &recipe,
            &on,
            &Default::default()
        )
        .is_err()
    );
    let mut long = recipe.clone();
    long.scale_bar.as_mut().unwrap().length_um = 500.0;
    let error = export(dir.path(), "long.png", &image, &long, &on, &extras).unwrap_err();
    assert!(error.to_string().contains("choose about 50 µm"), "{error}");
    // Switch off: the recipe's bar is not burned and the bytes are plain.
    let (_, off) = export(
        dir.path(),
        "off.png",
        &image,
        &recipe,
        &sdr(ExportFormat::Png),
        &extras,
    )
    .unwrap();
    let (_, plain) = export(
        dir.path(),
        "plain.png",
        &image,
        &DevelopmentRecipe::default(),
        &sdr(ExportFormat::Png),
        &extras,
    )
    .unwrap();
    assert_eq!(std::fs::read(off).unwrap(), std::fs::read(plain).unwrap());
}

fn metadata() -> ExportExtras<'static> {
    ExportExtras {
        date_time: Some(ExportDateTime::from_unix_seconds(1_793_781_369, 60)),
        ..Default::default()
    }
}

fn described(format: ExportFormat) -> ExportSettings {
    ExportSettings {
        metadata: ExportMetadata {
            artist: "Chris Caruso".into(),
            copyright: "© 2026 Chris Caruso".into(),
            description: "Weevil on moss".into(),
        },
        speed: 10,
        ..sdr(format)
    }
}

fn find(haystack: &[u8], needle: &[u8]) -> Option<usize> {
    haystack.windows(needle.len()).position(|w| w == needle)
}

#[test]
fn metadata_reaches_every_format_without_changing_pixels() {
    let dir = tempfile::tempdir().unwrap();
    let image = textured(64, 40);
    let recipe = DevelopmentRecipe::default();
    // TIFF: native tags plus XMP (tag 700).
    let (report, tiff) = export(
        dir.path(),
        "m.tiff",
        &image,
        &recipe,
        &described(ExportFormat::Tiff),
        &metadata(),
    )
    .unwrap();
    assert_eq!(report.metadata, vec!["tiff-tags", "xmp"]);
    assert_eq!(tag_text(&tiff, Tag::Artist).unwrap(), "Chris Caruso");
    assert_eq!(
        tag_text(&tiff, Tag::Copyright).unwrap(),
        "(c) 2026 Chris Caruso"
    );
    assert_eq!(
        tag_text(&tiff, Tag::ImageDescription).unwrap(),
        "Weevil on moss"
    );
    assert_eq!(
        tag_text(&tiff, Tag::DateTime).unwrap(),
        "2026:11:04 09:36:09"
    );
    let mut decoder = Decoder::new(std::fs::File::open(&tiff).unwrap()).unwrap();
    let xmp = String::from_utf8(decoder.get_tag_u8_vec(Tag::Unknown(700)).unwrap()).unwrap();
    assert!(xmp.contains("© 2026 Chris Caruso") && xmp.contains("2026-11-04T09:36:09+01:00"));
    let (_, plain) = export(
        dir.path(),
        "p.tiff",
        &image,
        &recipe,
        &sdr(ExportFormat::Tiff),
        &Default::default(),
    )
    .unwrap();
    assert_eq!(tiff16(&tiff).2, tiff16(&plain).2);
    // PNG: an iTXt XMP chunk before the image data.
    let (report, png) = export(
        dir.path(),
        "m.png",
        &image,
        &recipe,
        &described(ExportFormat::Png),
        &metadata(),
    )
    .unwrap();
    assert_eq!(report.metadata, vec!["xmp"]);
    let bytes = std::fs::read(&png).unwrap();
    let itxt = find(&bytes, b"iTXtXML:com.adobe.xmp\0").unwrap();
    assert!(itxt < find(&bytes, b"IDAT").unwrap());
    let (_, plain) = export(
        dir.path(),
        "p.png",
        &image,
        &recipe,
        &sdr(ExportFormat::Png),
        &Default::default(),
    )
    .unwrap();
    assert_eq!(png_rgb16(&png), png_rgb16(&plain));
    // JPEG: Exif and XMP APP1 segments.
    let (report, jpeg) = export(
        dir.path(),
        "m.jpg",
        &image,
        &recipe,
        &described(ExportFormat::Jpeg),
        &metadata(),
    )
    .unwrap();
    assert_eq!(report.metadata, vec!["exif", "xmp"]);
    let bytes = std::fs::read(&jpeg).unwrap();
    assert!(
        find(&bytes, b"Exif\0\0II*\0").unwrap()
            < find(&bytes, b"http://ns.adobe.com/xap/1.0/\0").unwrap()
    );
    assert!(find(&bytes, "© 2026 Chris Caruso".as_bytes()).is_some());
    let (_, plain) = export(
        dir.path(),
        "p.jpg",
        &image,
        &recipe,
        &sdr(ExportFormat::Jpeg),
        &Default::default(),
    )
    .unwrap();
    let decode = |p: &Path| image::open(p).unwrap().into_rgb8().into_raw();
    assert_eq!(decode(&jpeg), decode(&plain));
    // AVIF: avif-serialize 0.8.9 carries Exif, not XMP.
    let avif = ExportSettings {
        format: ExportFormat::Avif,
        ..described(ExportFormat::Avif)
    };
    let (report, path) = export(dir.path(), "m.avif", &image, &recipe, &avif, &metadata()).unwrap();
    assert_eq!(report.metadata, vec!["exif"]);
    let bytes = std::fs::read(path).unwrap();
    assert!(find(&bytes, b"Exif").is_some() && find(&bytes, b"Chris Caruso").is_some());
}

#[test]
fn coverage_follows_the_crop_and_refuses_a_resize() {
    let dir = tempfile::tempdir().unwrap();
    let image = textured(40, 30);
    let mask: Vec<u8> = (0..40 * 30)
        .map(|i| if (i % 40 + i / 40) % 3 == 0 { 0 } else { 255 })
        .collect();
    let mut recipe = DevelopmentRecipe::default();
    let crop = Crop {
        min: [0.25, 0.2],
        max: [0.75, 0.8],
        angle_deg: 0.0,
    };
    recipe.crop = Some(crop);
    let extras = ExportExtras {
        coverage: Some(&mask),
        ..Default::default()
    };
    let (_, path) = export(
        dir.path(),
        "a.tiff",
        &image,
        &recipe,
        &sdr(ExportFormat::Tiff),
        &extras,
    )
    .unwrap();
    let mut decoder = Decoder::new(std::fs::File::open(&path).unwrap()).unwrap();
    let (w, h) = decoder.dimensions().unwrap();
    let tiff::decoder::DecodingResult::U16(rgba) = decoder.read_image().unwrap() else {
        panic!()
    };
    let [x0, y0, ..] = crop.pixel_rect(40, 30);
    for y in 0..h {
        for x in 0..w {
            let a = rgba[((y * w + x) * 4 + 3) as usize];
            assert_eq!(a, u16::from(mask[((y + y0) * 40 + x + x0) as usize]) * 257);
        }
    }
    let resized = ExportSettings {
        resize: Some(Resize {
            long_edge: 16,
            filter: ResizeFilter::Mitchell,
        }),
        ..sdr(ExportFormat::Png)
    };
    assert!(export(dir.path(), "b.png", &image, &recipe, &resized, &extras).is_err());
    assert!(!dir.path().join("b.png").exists());
}
