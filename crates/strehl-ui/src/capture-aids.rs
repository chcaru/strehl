//! Live JPEG viewing aids. These never alter captured RAWs or measure RAW quality.
use eframe::egui::{Color32, ColorImage};

pub(crate) struct Peaking {
    size: [usize; 2],
    strength: Vec<u8>,
}
impl Peaking {
    /// A fixed local high-pass response, independent of scene-wide contrast.
    /// A small absolute floor suppresses JPEG/flat-field noise; the user can raise it.
    pub fn analyze(image: &ColorImage) -> Self {
        let [w, h] = image.size;
        let luma: Vec<f32> = image
            .pixels
            .iter()
            .map(|p| 0.2126 * p.r() as f32 + 0.7152 * p.g() as f32 + 0.0722 * p.b() as f32)
            .collect();
        let mut strength = vec![0; w * h];
        if w >= 3 && h >= 3 {
            for y in 1..h - 1 {
                for x in 1..w - 1 {
                    let i = y * w + x;
                    strength[i] =
                        ((4.0 * luma[i] - luma[i - 1] - luma[i + 1] - luma[i - w] - luma[i + w])
                            .abs()
                            * 0.25)
                            .min(255.0) as u8;
                }
            }
        }
        Self {
            size: image.size,
            strength,
        }
    }
    pub fn overlay(&self, threshold: u8) -> ColorImage {
        let mut out = ColorImage::filled(self.size, Color32::TRANSPARENT);
        for (pixel, strength) in out.pixels.iter_mut().zip(&self.strength) {
            if *strength >= threshold.max(6) {
                *pixel = Color32::from_rgba_unmultiplied(0, 245, 210, 220);
            }
        }
        out
    }
}

pub(crate) fn phone_qr(link: &str) -> anyhow::Result<ColorImage> {
    use qrcode::{QrCode, types::Color};
    let code = QrCode::with_error_correction_level(link, qrcode::EcLevel::M)?;
    // Four-module quiet zone is part of the image, including in dark mode.
    let side = code.width() + 8;
    let mut image = ColorImage::filled([side, side], Color32::WHITE);
    for y in 0..code.width() {
        for x in 0..code.width() {
            if code[(x, y)] == Color::Dark {
                image.pixels[(y + 4) * side + x + 4] = Color32::BLACK;
            }
        }
    }
    Ok(image)
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn flat_first_then_edges_and_sensitivity() {
        let mut image = ColorImage::filled([64, 48], Color32::from_gray(127));
        let count = |p: &Peaking, t| p.overlay(t).pixels.iter().filter(|p| p.a() != 0).count();
        assert_eq!(count(&Peaking::analyze(&image), 6), 0);
        // Small alternating JPEG/quantization fluctuations must not light a flat ROI.
        for (i, p) in image.pixels.iter_mut().enumerate() {
            *p = Color32::from_gray(126 + (i % 3) as u8);
        }
        assert_eq!(count(&Peaking::analyze(&image), 6), 0);
        for y in 0..48 {
            for x in 32..64 {
                image.pixels[y * 64 + x] = Color32::from_gray(255);
            }
        }
        let peak = Peaking::analyze(&image);
        assert!(count(&peak, 18) > 0);
        assert!(count(&peak, 40) < count(&peak, 18));
    }
    #[test]
    fn qr_has_black_modules_and_complete_quiet_zone() {
        let qr = phone_qr(
            "http://10.0.0.178:8787/#key=000000000000000000000000000000000000000000000000",
        )
        .unwrap();
        let w = qr.size[0];
        if let Ok(folder) = std::env::var("STREHL_CAPTURE_EVIDENCE") {
            let bytes: Vec<u8> = qr
                .pixels
                .iter()
                .flat_map(|p| [p.r(), p.g(), p.b()])
                .collect();
            image::save_buffer(
                std::path::Path::new(&folder).join("phone-qr-fixture.png"),
                &bytes,
                w as u32,
                w as u32,
                image::ColorType::Rgb8,
            )
            .unwrap();
        }
        assert!(qr.pixels.contains(&Color32::BLACK));
        for y in 0..w {
            for x in 0..w {
                if x < 4 || y < 4 || x >= w - 4 || y >= w - 4 {
                    assert_eq!(qr.pixels[y * w + x], Color32::WHITE);
                }
            }
        }
    }
}
