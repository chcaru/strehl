//! The viewport/taskbar uses the exact largest frame embedded in the Windows ICO.
pub(crate) fn application_icon() -> eframe::egui::IconData {
    let image = image::load_from_memory_with_format(
        include_bytes!("../assets/strehl-256.png"),
        image::ImageFormat::Png,
    )
    .expect("the checked-in Strehl application icon must be a valid PNG")
    .into_rgba8();
    eframe::egui::IconData {
        width: image.width(),
        height: image.height(),
        rgba: image.into_raw(),
    }
}

#[cfg(test)]
mod tests {
    #[test]
    fn windows_icon_has_native_sizes_and_the_same_runtime_artwork() {
        let ico = include_bytes!("../assets/strehl.ico");
        let word = |offset| u16::from_le_bytes(ico[offset..offset + 2].try_into().unwrap());
        let dword =
            |offset| u32::from_le_bytes(ico[offset..offset + 4].try_into().unwrap()) as usize;
        assert_eq!((word(0), word(2), word(4)), (0, 1, 9));
        for (index, size) in [16, 20, 24, 32, 40, 48, 64, 128, 256]
            .into_iter()
            .enumerate()
        {
            let entry = 6 + index * 16;
            let dimension = if ico[entry] == 0 {
                256
            } else {
                usize::from(ico[entry])
            };
            assert_eq!(dimension, size);
            assert_eq!(ico[entry], ico[entry + 1]);
            assert_eq!((word(entry + 4), word(entry + 6)), (1, 32));
            let payload = &ico[dword(entry + 12)..dword(entry + 12) + dword(entry + 8)];
            if size <= 48 {
                assert_eq!(&payload[..4], &40_u32.to_le_bytes());
                assert_eq!(&payload[4..8], &(size as u32).to_le_bytes());
                assert_eq!(&payload[8..12], &((size * 2) as u32).to_le_bytes());
            } else {
                let decoded =
                    image::load_from_memory_with_format(payload, image::ImageFormat::Png).unwrap();
                assert_eq!(
                    (decoded.width(), decoded.height()),
                    (size as u32, size as u32)
                );
                if size == 256 {
                    let runtime = super::application_icon();
                    assert_eq!(decoded.into_rgba8().into_raw(), runtime.rgba);
                    assert!(
                        runtime
                            .rgba
                            .as_chunks::<4>()
                            .0
                            .iter()
                            .any(|pixel| pixel[3] == 0)
                    );
                    assert!(
                        runtime
                            .rgba
                            .as_chunks::<4>()
                            .0
                            .iter()
                            .any(|pixel| pixel[3] == 255)
                    );
                }
            }
        }
    }
}
