use super::*;

fn color_fixture() -> Vec<u8> {
    let image = image::RgbImage::from_fn(64, 48, |x, y| {
        image::Rgb(match (x < 32, y < 24) {
            (true, true) => [230, 20, 20],
            (false, true) => [20, 230, 20],
            (true, false) => [20, 20, 230],
            (false, false) => [230, 230, 20],
        })
    });
    let mut bytes = Vec::new();
    image::codecs::jpeg::JpegEncoder::new_with_quality(&mut bytes, 95)
        .encode_image(&image)
        .unwrap();
    bytes
}

#[test]
fn reduction_is_real_and_all_eight_orientations_preserve_corner_identity_and_aperture() {
    let bytes = color_fixture();
    let cancel = AtomicBool::new(false);
    let (reduced, original) = decode(&bytes, 16, &cancel).unwrap();
    assert_eq!(original, [64, 48]);
    assert_eq!(
        [reduced.width(), reduced.height()],
        [16, 12],
        "must really reduce IDCT pixels"
    );
    let orders = [
        [0, 1, 2, 3],
        [1, 0, 3, 2],
        [3, 2, 1, 0],
        [2, 3, 0, 1],
        [0, 2, 1, 3],
        [2, 0, 3, 1],
        [3, 1, 2, 0],
        [1, 3, 0, 2],
    ];
    let palette = [
        [230_i32, 20, 20],
        [20, 230, 20],
        [20, 20, 230],
        [230, 230, 20],
    ];
    for orientation in 1..=8 {
        let image = orient(reduced.clone(), orientation).into_rgb8();
        let expected_size = if orientation >= 5 { [12, 16] } else { [16, 12] };
        assert_eq!([image.width(), image.height()], expected_size);
        for (corner, (x, y)) in [
            (2, 2),
            (image.width() - 3, 2),
            (2, image.height() - 3),
            (image.width() - 3, image.height() - 3),
        ]
        .into_iter()
        .enumerate()
        {
            let pixel = image.get_pixel(x, y).0;
            let closest = palette
                .iter()
                .enumerate()
                .min_by_key(|(_, target)| {
                    pixel
                        .iter()
                        .zip(*target)
                        .map(|(&a, &b)| (i32::from(a) - b).abs())
                        .sum::<i32>()
                })
                .unwrap()
                .0;
            assert_eq!(
                closest,
                orders[usize::from(orientation - 1)][corner],
                "orientation {orientation}, corner {corner}"
            );
        }
    }
    let (native, aperture) = decode(&bytes, 64, &cancel).unwrap();
    assert_eq!(aperture, original);
    assert_eq!(
        native.into_rgba8(),
        decode_jpeg(&bytes).unwrap().into_rgba8(),
        "native-resolution requests keep the previous decoder exactly"
    );
}

#[test]
fn grayscale_reduction_retains_luminance_and_full_source_dimensions() {
    let mut bytes = Vec::new();
    let image =
        image::GrayImage::from_fn(64, 48, |x, _| image::Luma([if x < 32 { 40 } else { 210 }]));
    image::codecs::jpeg::JpegEncoder::new_with_quality(&mut bytes, 95)
        .encode_image(&image)
        .unwrap();
    let (image, aperture) = decode(&bytes, 16, &AtomicBool::new(false)).unwrap();
    assert_eq!(aperture, [64, 48]);
    assert_eq!([image.width(), image.height()], [16, 12]);
    let rgba = image.into_rgba8();
    let left = rgba.get_pixel(2, 6).0;
    let right = rgba.get_pixel(13, 6).0;
    assert!(left[0] < 50 && right[0] > 200);
    assert_eq!(left[0], left[1]);
    assert_eq!(left[1], left[2]);
    assert_eq!(left[3], 255);
}

/// A deliberately tiny, constant four-component baseline JPEG. Every block
/// has zero DC delta and EOB, so no camera/library fixture or external codec is
/// needed to exercise a real unusual-color fallback.
fn cmyk_fixture() -> Vec<u8> {
    let mut bytes = vec![0xff, 0xd8];
    let mut marker = |id: u8, data: &[u8]| {
        bytes.extend([0xff, id]);
        bytes.extend(((data.len() + 2) as u16).to_be_bytes());
        bytes.extend(data);
    };
    marker(0xee, b"Adobe\0\x64\0\0\0\0\0");
    let mut quant = vec![0];
    quant.extend([1; 64]);
    marker(0xdb, &quant);
    let mut frame = vec![8, 0, 32, 0, 64, 4];
    for id in 1..=4 {
        frame.extend([id, 0x11, 0]);
    }
    marker(0xc0, &frame);
    let mut huffman = vec![0, 1];
    huffman.extend([0; 15]);
    huffman.push(0);
    huffman.extend([0x10, 1]);
    huffman.extend([0; 15]);
    huffman.push(0);
    marker(0xc4, &huffman);
    marker(0xda, &[4, 1, 0, 2, 0, 3, 0, 4, 0, 0, 63, 0]);
    // 8*4 MCUs, four components, two zero bits per block.
    bytes.extend([0; 32]);
    bytes.extend([0xff, 0xd9]);
    bytes
}

#[test]
fn cmyk_is_a_real_existing_decoder_fallback_not_an_rgb_reinterpretation() {
    let bytes = cmyk_fixture();
    let cancel = AtomicBool::new(false);
    assert!(scaled(&bytes, 16, &cancel).unwrap().is_none());
    let original = decode_jpeg(&bytes).unwrap().into_rgba8();
    let (image, aperture) = decode(&bytes, 16, &cancel).unwrap();
    assert_eq!(aperture, [64, 32]);
    assert_eq!(image.into_rgba8(), original);
}

#[test]
fn cancellation_is_terminal_even_after_the_reader_has_started() {
    let cancelled = AtomicBool::new(false);
    let mut reader = Cancellable {
        cursor: Cursor::new(&b"abcdef"[..]),
        cancelled: &cancelled,
    };
    let mut output = [0; 3];
    reader.read_exact(&mut output).unwrap();
    assert_eq!(&output, b"abc");
    cancelled.store(true, Ordering::Relaxed);
    let error = reader.read_exact(&mut output).unwrap_err();
    assert_ne!(
        error.kind(),
        std::io::ErrorKind::Interrupted,
        "read_exact must not retry indefinitely"
    );
    assert!(decode(&color_fixture(), 16, &cancelled).is_err());
}
