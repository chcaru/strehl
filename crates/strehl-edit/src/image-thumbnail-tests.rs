use super::*;
use std::fs;

#[test]
fn sparse_thumbnail_matches_native_linear_samples_and_preserves_metadata() {
    let root = tempfile::tempdir().unwrap();
    let path = root.path().join("linear.tiff");
    let image = LinearImage {
        width: 23,
        height: 17,
        pixels: (0..23 * 17 * 3)
            .map(|i| (i % 91) as f32 / 31.0 - 0.2)
            .collect(),
        origin: ImageOrigin::SceneLinear,
        baseline: Some(DisplayBaseline {
            black: 0.02,
            white: 1.1,
            contrast: 0.1,
            exposure_gain: 1.03,
        }),
        baked_recipe: None,
    };
    save_linear_tiff(&path, &image).unwrap();
    let (native, aperture) = load_tiff_thumbnail(&path, 128, &AtomicBool::new(false)).unwrap();
    assert_eq!(aperture, [23, 17]);
    assert_eq!(native.pixels, image.pixels);
    assert_eq!(native.baseline, image.baseline);
    let (small, _) = load_tiff_thumbnail(&path, 7, &AtomicBool::new(false)).unwrap();
    assert_eq!([small.width, small.height], [7, 5]);
    let mut saw_mixture = false;
    for y in 0..small.height {
        for x in 0..small.width {
            let positions = samples(y, image.height, small.height)
                .into_iter()
                .flat_map(|sy| {
                    samples(x, image.width, small.width)
                        .map(move |sx| (sy * image.width + sx) as usize * 3)
                })
                .collect::<Vec<_>>();
            saw_mixture |= positions[0] != positions[3];
            for c in 0..3 {
                let expected: f32 = positions
                    .iter()
                    .map(|&at| image.pixels[at + c] * 0.25)
                    .sum();
                assert_eq!(
                    small.pixels[(y * small.width + x) as usize * 3 + c],
                    expected
                );
            }
        }
    }
    assert!(saw_mixture);
    assert!(load_tiff_thumbnail(&path, 384, &AtomicBool::new(true)).is_err());
}

#[test]
fn srgb_thumbnail_decodes_color_before_averaging_and_rejects_truncation() {
    let root = tempfile::tempdir().unwrap();
    let path = root.path().join("color.tiff");
    let values = [
        0u16, 65535, 10000, 65535, 0, 50000, 0, 65535, 10000, 65535, 0, 50000,
    ];
    {
        let mut encoder = TiffEncoder::new(File::create(&path).unwrap()).unwrap();
        encoder
            .new_image::<colortype::RGB16>(2, 2)
            .unwrap()
            .write_data(&values)
            .unwrap();
    }
    let (small, _) = load_tiff_thumbnail(&path, 1, &AtomicBool::new(false)).unwrap();
    assert!((small.pixels[0] - 0.5).abs() < 1e-6);
    assert!((small.pixels[1] - 0.5).abs() < 1e-6);
    assert!(
        (small.pixels[2] - (srgb_decode(10000.0 / 65535.0) + srgb_decode(50000.0 / 65535.0)) * 0.5)
            .abs()
            < 1e-6
    );
    assert!(
        (small.pixels[0] - srgb_decode(0.5)).abs() > 0.2,
        "averaging encoded samples would be wrong"
    );
    let bytes = fs::read(&path).unwrap();
    fs::write(&path, &bytes[..bytes.len() / 2]).unwrap();
    assert!(load_tiff_thumbnail(&path, 384, &AtomicBool::new(false)).is_err());
}

#[test]
fn independent_big_endian_three_strip_fixture_preserves_rows_and_channels() {
    let root = tempfile::tempdir().unwrap();
    let path = root.path().join("big-endian.tiff");
    let mut bytes = b"MM\0*\0\0\0\x08".to_vec();
    bytes.extend(10u16.to_be_bytes());
    for (tag, kind, count, value) in [
        (256u16, 4u16, 1u32, 3u32),
        (257, 4, 1, 3),
        (258, 3, 3, 134),
        (259, 3, 1, 1),
        (262, 3, 1, 2),
        (273, 4, 3, 140),
        (277, 3, 1, 3),
        (278, 4, 1, 1),
        (279, 4, 3, 152),
        (284, 3, 1, 1),
    ] {
        bytes.extend(tag.to_be_bytes());
        bytes.extend(kind.to_be_bytes());
        bytes.extend(count.to_be_bytes());
        if kind == 3 && count == 1 {
            bytes.extend((value as u16).to_be_bytes());
            bytes.extend([0, 0]);
        } else {
            bytes.extend(value.to_be_bytes());
        }
    }
    bytes.extend([0; 4]);
    assert_eq!(bytes.len(), 134);
    for n in [16u16, 16, 16] {
        bytes.extend(n.to_be_bytes());
    }
    for n in [164u32, 182, 200, 18, 18, 18] {
        bytes.extend(n.to_be_bytes());
    }
    let samples: Vec<u16> = (0..27).map(|n| 1000 + n * 2100).collect();
    for n in &samples {
        bytes.extend(n.to_be_bytes());
    }
    fs::write(&path, bytes).unwrap();
    let (native, _) = load_tiff_thumbnail(&path, 384, &AtomicBool::new(false)).unwrap();
    for (actual, original) in native.pixels.iter().zip(samples) {
        assert!((*actual - srgb_decode(original as f32 / 65535.0)).abs() < 1e-7);
    }
    let (small, _) = load_tiff_thumbnail(&path, 2, &AtomicBool::new(false)).unwrap();
    for c in 0..3 {
        let expected = (native.pixels[c]
            + native.pixels[3 + c]
            + native.pixels[9 + c]
            + native.pixels[12 + c])
            * 0.25;
        assert!((small.pixels[c] - expected).abs() < 1e-7);
    }
}

#[test]
fn known_wide_primaries_and_compressed_fallback_match_managed_decoder() {
    let root = tempfile::tempdir().unwrap();
    for compressed in [false, true] {
        let path = root.path().join(format!("wide-{compressed}.tiff"));
        let values: Vec<u16> = (0..5 * 7)
            .flat_map(|n| [60000 - n * 131, 20000 + n * 219, 10000 + n * 71])
            .collect();
        let mut encoder = TiffEncoder::new(File::create(&path).unwrap()).unwrap();
        if compressed {
            encoder = encoder.with_compression(tiff::encoder::Compression::Lzw);
        }
        let mut output = encoder.new_image::<colortype::RGB16>(5, 7).unwrap();
        output.rows_per_strip(2).unwrap();
        output
            .encoder()
            .write_tag(
                Tag::IccProfile,
                IccBytes(&crate::icc::icc_output_v2(
                    crate::OutputColorSpace::Rec2020,
                    false,
                )),
            )
            .unwrap();
        output.write_data(&values).unwrap();
        let full = load_tiff(&path).unwrap();
        let (native, _) = load_tiff_thumbnail(&path, 384, &AtomicBool::new(false)).unwrap();
        assert_eq!(native.pixels, full.pixels);
        assert!(
            (native.pixels[0] - srgb_decode(60000.0 / 65535.0)).abs() > 0.1,
            "wide primaries must actually affect this fixture"
        );
    }
}

#[test]
fn sparse_navigation_is_not_a_full_lowpass_and_long_rows_are_rejected() {
    let root = tempfile::tempdir().unwrap();
    let path = root.path().join("checker.tiff");
    let image = LinearImage {
        width: 4,
        height: 4,
        pixels: (0..16)
            .flat_map(|i| [if (i / 4 + i % 4) % 2 == 0 { 1.0 } else { 0.0 }; 3])
            .collect(),
        origin: ImageOrigin::SceneLinear,
        baseline: None,
        baked_recipe: None,
    };
    save_linear_tiff(&path, &image).unwrap();
    let (small, _) = load_tiff_thumbnail(&path, 1, &AtomicBool::new(false)).unwrap();
    assert_eq!(small.pixels, [1.0; 3]);
    assert_eq!(
        image.preview(1).pixels,
        [0.5; 3],
        "a thumbnail must never become the editing/detail-analysis source"
    );
    let mut bytes = fs::read(&path).unwrap();
    // Corrupt the width tag only, preserving a valid directory. This must fail
    // before allocating a width-sized scanline or seeking image payloads.
    let offset = u32::from_le_bytes(bytes[4..8].try_into().unwrap()) as usize;
    let count = u16::from_le_bytes(bytes[offset..offset + 2].try_into().unwrap()) as usize;
    let width = (0..count)
        .map(|i| offset + 2 + i * 12)
        .find(|&i| u16::from_le_bytes(bytes[i..i + 2].try_into().unwrap()) == 256)
        .unwrap();
    bytes[width + 8..width + 12].copy_from_slice(&40_000u32.to_le_bytes());
    fs::write(&path, bytes).unwrap();
    assert!(
        load_tiff_thumbnail(&path, 384, &AtomicBool::new(false))
            .unwrap_err()
            .to_string()
            .contains("bounded thumbnail aperture")
    );
}
