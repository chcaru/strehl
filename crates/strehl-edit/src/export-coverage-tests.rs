use super::*;
fn fixture() -> LinearImage {
    LinearImage {
        width: 4,
        height: 2,
        pixels: (0..24).map(|i| 0.02 + i as f32 * 0.025).collect(),
        origin: ImageOrigin::DisplayReferred,
        baseline: None,
        baked_recipe: None,
    }
}
#[test]
fn coverage_export_preserves_supported_rgb_metadata_alpha_and_ordinary_bytes() {
    let root = tempfile::tempdir().unwrap();
    let image = fixture();
    let recipe = DevelopmentRecipe::default();
    let cancel = AtomicBool::new(false);
    let mask = [255, 0, 255, 255, 0, 255, 255, 255];
    for format in [ExportFormat::Tiff, ExportFormat::Png] {
        let settings = ExportSettings {
            format,
            color_space: OutputColorSpace::Srgb,
            hdr: false,
            ..Default::default()
        };
        let suffix = if format == ExportFormat::Tiff {
            "tiff"
        } else {
            "png"
        };
        let ordinary = root.path().join(format!("ordinary.{suffix}"));
        let wrapper = root.path().join(format!("wrapper.{suffix}"));
        let alpha = root.path().join(format!("alpha.{suffix}"));
        export_image(&ordinary, &image, &recipe, &settings, &cancel).unwrap();
        export_image_with_coverage(&wrapper, &image, &recipe, &settings, &cancel, None).unwrap();
        assert_eq!(
            std::fs::read(&ordinary).unwrap(),
            std::fs::read(&wrapper).unwrap()
        );
        export_image_with_coverage(&alpha, &image, &recipe, &settings, &cancel, Some(&mask))
            .unwrap();
        let (rgb, rgba) = if format == ExportFormat::Tiff {
            let mut a =
                tiff::decoder::Decoder::new(std::fs::File::open(&ordinary).unwrap()).unwrap();
            let mut b = tiff::decoder::Decoder::new(std::fs::File::open(&alpha).unwrap()).unwrap();
            assert_eq!(
                a.get_tag_ascii_string(tiff::tags::Tag::ImageDescription)
                    .unwrap(),
                b.get_tag_ascii_string(tiff::tags::Tag::ImageDescription)
                    .unwrap()
            );
            assert_eq!(
                a.get_tag_u8_vec(tiff::tags::Tag::IccProfile).unwrap(),
                b.get_tag_u8_vec(tiff::tags::Tag::IccProfile).unwrap()
            );
            assert_eq!(
                b.get_tag_u16_vec(tiff::tags::Tag::ExtraSamples).unwrap(),
                vec![2]
            );
            let tiff::decoder::DecodingResult::U16(rgb) = a.read_image().unwrap() else {
                panic!()
            };
            let tiff::decoder::DecodingResult::U16(rgba) = b.read_image().unwrap() else {
                panic!()
            };
            (rgb, rgba)
        } else {
            use image::ImageDecoder;
            let mut a = image::codecs::png::PngDecoder::new(std::io::BufReader::new(
                std::fs::File::open(&ordinary).unwrap(),
            ))
            .unwrap();
            let mut b = image::codecs::png::PngDecoder::new(std::io::BufReader::new(
                std::fs::File::open(&alpha).unwrap(),
            ))
            .unwrap();
            assert_eq!(a.icc_profile().unwrap(), b.icc_profile().unwrap());
            (
                image::open(&ordinary).unwrap().into_rgb16().into_raw(),
                image::open(&alpha).unwrap().into_rgba16().into_raw(),
            )
        };
        for (i, (p, a)) in rgb.chunks_exact(3).zip(rgba.chunks_exact(4)).enumerate() {
            assert_eq!(p, &a[..3]);
            assert_eq!(a[3], u16::from(mask[i]) * 257);
        }
    }
}
#[test]
fn coverage_export_refuses_bad_masks_unsupported_formats_cancel_and_overwrite_before_publication() {
    let root = tempfile::tempdir().unwrap();
    let path = root.path().join("delivery.tiff");
    let image = fixture();
    let recipe = DevelopmentRecipe::default();
    let mask = [255; 8];
    let cancel = AtomicBool::new(false);
    let mut settings = ExportSettings {
        format: ExportFormat::Tiff,
        hdr: false,
        ..Default::default()
    };
    for invalid in [vec![255; 7], vec![1; 8]] {
        assert!(
            export_image_with_coverage(&path, &image, &recipe, &settings, &cancel, Some(&invalid))
                .is_err()
        );
        assert!(!path.exists());
    }
    for format in [ExportFormat::Jpeg, ExportFormat::Avif] {
        settings.format = format;
        assert!(
            export_image_with_coverage(&path, &image, &recipe, &settings, &cancel, Some(&mask))
                .is_err()
        );
        assert!(!path.exists());
    }
    settings.format = ExportFormat::Tiff;
    cancel.store(true, Ordering::Relaxed);
    assert!(
        export_image_with_coverage(&path, &image, &recipe, &settings, &cancel, Some(&mask))
            .is_err()
    );
    assert!(!path.exists());
    cancel.store(false, Ordering::Relaxed);
    std::fs::write(&path, b"existing").unwrap();
    assert!(
        export_image_with_coverage(&path, &image, &recipe, &settings, &cancel, Some(&mask))
            .is_err()
    );
    assert_eq!(std::fs::read(path).unwrap(), b"existing");
}
