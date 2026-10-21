use image::ImageDecoder;
use std::{io::Cursor, sync::atomic::AtomicBool};
use strehl_edit::*;

fn photograph() -> LinearImage {
    let colors = [
        [0.03, 0.18, 0.55],
        [0.8, 0.21, 0.02],
        [0.16, 0.65, 0.08],
        [0.5; 3],
    ];
    LinearImage {
        width: 64,
        height: 32,
        origin: ImageOrigin::SceneLinear,
        baseline: None,
        baked_recipe: None,
        pixels: (0..2048).flat_map(|i| colors[i % 64 / 16]).collect(),
    }
}
fn settings(format: ExportFormat, color_space: OutputColorSpace) -> ExportSettings {
    ExportSettings {
        format,
        color_space,
        hdr: false,
        ..Default::default()
    }
}

#[test]
fn sdr_formats_have_real_bit_depth_and_embedded_profiles() {
    let dir = tempfile::tempdir().unwrap();
    let src = photograph();
    let recipe = DevelopmentRecipe::default();
    for space in [
        OutputColorSpace::Srgb,
        OutputColorSpace::DisplayP3,
        OutputColorSpace::Rec2020,
    ] {
        for format in [ExportFormat::Png, ExportFormat::Jpeg, ExportFormat::Tiff] {
            let path = dir.path().join(format!("{space:?}-{format:?}"));
            let report = export_image(
                &path,
                &src,
                &recipe,
                &settings(format, space),
                &AtomicBool::new(false),
            )
            .unwrap();
            assert!(report.bytes > 100);
            let bytes = std::fs::read(&path).unwrap();
            let (profile, decoded) = match format {
                ExportFormat::Png => {
                    let mut decoder =
                        image::codecs::png::PngDecoder::new(Cursor::new(&bytes)).unwrap();
                    assert_eq!(decoder.color_type(), image::ColorType::Rgb16);
                    (
                        decoder.icc_profile().unwrap().unwrap(),
                        image::load_from_memory_with_format(&bytes, image::ImageFormat::Png)
                            .unwrap(),
                    )
                }
                ExportFormat::Jpeg => {
                    let mut decoder =
                        image::codecs::jpeg::JpegDecoder::new(Cursor::new(&bytes)).unwrap();
                    assert_eq!(decoder.color_type(), image::ColorType::Rgb8);
                    (
                        decoder.icc_profile().unwrap().unwrap(),
                        image::load_from_memory_with_format(&bytes, image::ImageFormat::Jpeg)
                            .unwrap(),
                    )
                }
                ExportFormat::Tiff => {
                    let loaded = load_tiff(&path).unwrap();
                    let reference = src.render_sdr16(&recipe).unwrap();
                    let actual = loaded.render_sdr16(&recipe).unwrap();
                    assert!(
                        reference
                            .iter()
                            .zip(actual)
                            .all(|(&a, b)| a.abs_diff(b) <= 8),
                        "{space:?} roundtrip changed appearance"
                    );
                    continue;
                }
                _ => unreachable!(),
            };
            assert_eq!(&profile[36..40], b"acsp");
            assert_eq!((decoded.width(), decoded.height()), (64, 32));
            let name = String::from_utf8_lossy(&profile);
            assert!(name.contains(match space {
                OutputColorSpace::Srgb => "sRGB",
                OutputColorSpace::DisplayP3 => "Display P3",
                OutputColorSpace::Rec2020 => "Rec.2020",
            }));
            if space == OutputColorSpace::Srgb {
                let expected = src.render_sdr8(&recipe).unwrap();
                let actual = decoded.to_rgb8().into_raw();
                assert!(
                    expected
                        .iter()
                        .zip(actual)
                        .all(|(&a, b)| a.abs_diff(b) <= 3),
                    "neutral export changed pixel codes"
                );
            }
        }
    }
}

#[test]
fn all_avif_gamuts_signal_primaries_transfer_and_matrix_together() {
    let dir = tempfile::tempdir().unwrap();
    let mut src = photograph();
    src.pixels.iter_mut().for_each(|v| *v *= 3.0);
    for (space, cp, mc) in [
        (OutputColorSpace::Srgb, 1, 1),
        (OutputColorSpace::DisplayP3, 12, 1),
        (OutputColorSpace::Rec2020, 9, 9),
    ] {
        for hdr in [false, true] {
            let path = dir.path().join(format!("{space:?}-{hdr}.avif"));
            let report = export_image(
                &path,
                &src,
                &DevelopmentRecipe::default(),
                &ExportSettings {
                    color_space: space,
                    hdr,
                    speed: 10,
                    ..Default::default()
                },
                &AtomicBool::new(false),
            )
            .unwrap();
            assert_eq!(report.bit_depth, 10);
            let bytes = std::fs::read(path).unwrap();
            let at = bytes.windows(4).position(|w| w == b"nclx").unwrap();
            assert_eq!(
                &bytes[at + 4..at + 10],
                &[0, cp, 0, if hdr { 16 } else { 13 }, 0, mc]
            );
            assert_eq!(bytes[at + 10] & 128, 128);
            let av1 = bytes.windows(4).position(|w| w == b"av1C").unwrap();
            assert_eq!(bytes[av1 + 6] & 0x4c, 0x40, "10-bit444 required");
            if hdr {
                assert!(report.hdr_metadata.unwrap().max_content_light_nits > 203);
            }
        }
    }
}

#[test]
fn cancelled_invalid_and_existing_destinations_remain_untouched() {
    let dir = tempfile::tempdir().unwrap();
    let src = photograph();
    let recipe = DevelopmentRecipe::default();
    for format in [
        ExportFormat::Avif,
        ExportFormat::Tiff,
        ExportFormat::Png,
        ExportFormat::Jpeg,
    ] {
        let path = dir.path().join(format!("{format:?}"));
        let opts = settings(format, OutputColorSpace::Srgb);
        assert!(export_image(&path, &src, &recipe, &opts, &AtomicBool::new(true)).is_err());
        assert!(!path.exists());
        std::fs::write(&path, b"preserve me").unwrap();
        assert!(export_image(&path, &src, &recipe, &opts, &AtomicBool::new(false)).is_err());
        assert_eq!(std::fs::read(&path).unwrap(), b"preserve me");
    }
    let path = dir.path().join("bad.png");
    let mut opts = settings(ExportFormat::Png, OutputColorSpace::DisplayP3);
    opts.hdr = true;
    assert!(export_image(&path, &src, &recipe, &opts, &AtomicBool::new(false)).is_err());
    assert!(!path.exists());
}

#[test]
fn default_export_is_highest_supported_hdr_rec2020_avif() {
    let settings = ExportSettings::default();
    assert_eq!(settings.format, ExportFormat::Avif);
    assert_eq!(settings.color_space, OutputColorSpace::Rec2020);
    assert!(settings.hdr);
    assert_eq!(settings.quality, 100);
}

#[test]
fn neutral_reference_white_has_exact_luminance_metadata_in_every_gamut() {
    let dir = tempfile::tempdir().unwrap();
    let mut src = photograph();
    src.pixels.fill(1.0);
    for space in [
        OutputColorSpace::Srgb,
        OutputColorSpace::DisplayP3,
        OutputColorSpace::Rec2020,
    ] {
        let report = export_image(
            &dir.path().join(format!("white-{space:?}.avif")),
            &src,
            &DevelopmentRecipe::default(),
            &ExportSettings {
                color_space: space,
                speed: 10,
                ..Default::default()
            },
            &AtomicBool::new(false),
        )
        .unwrap()
        .hdr_metadata
        .unwrap();
        assert_eq!(report.max_content_light_nits, 203);
        assert_eq!(report.average_light_nits, 203);
        assert_eq!(report.clipped_samples, 0);
    }
}

#[test]
fn finite_input_that_overflows_development_cannot_publish_black_hdr_pixels() {
    let dir = tempfile::tempdir().unwrap();
    let mut src = photograph();
    src.pixels.fill(f32::MAX / 4.0);
    let path = dir.path().join("overflow.avif");
    let error = export_image(
        &path,
        &src,
        &DevelopmentRecipe::default(),
        &ExportSettings::default(),
        &AtomicBool::new(false),
    )
    .unwrap_err();
    assert!(error.to_string().contains("non-finite"));
    assert!(!path.exists());
}
