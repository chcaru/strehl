//! Live JPEG viewing aids. These never alter captured RAWs or measure RAW quality.
use eframe::egui::{Color32, ColorImage};

pub(crate) struct Peaking {
    size: [usize; 2],
    strength: Vec<u8>,
    /// The Laplacian's energy over a fixed grid of tiles, for the live
    /// view's focus readout in the subject box.
    pub focus: FocusTiles,
}

/// Columns and rows of [`FocusTiles`], whatever the preview's size.
pub(crate) const FOCUS_COLUMNS: usize = 32;
pub(crate) const FOCUS_ROWS: usize = 24;

/// The sum of the squared luma Laplacian (the peaking filter's response
/// before its floor and scaling, in whole codes) and the pixels it was taken
/// at, per tile of a fixed grid over the preview. Summed on the client
/// thread with the peaking; the UI reduces at most 768 tiles to the subject
/// box once per preview or box ([`Self::focus_in`]). A focus aid on the
/// camera's JPEG: it rises as the box's detail sharpens, it is not a
/// measure of the RAW.
#[derive(Clone, Debug, Default, PartialEq)]
pub(crate) struct FocusTiles {
    pub size: [usize; 2],
    pub energy: Vec<u64>,
    pub pixels: Vec<u32>,
}

impl FocusTiles {
    /// The mean squared Laplacian over the normalised rectangle `x`, `y`,
    /// `width`, `height` (tiles weighted by their overlap), or `None` when
    /// it covers no measured pixel.
    pub fn focus_in(&self, x: f32, y: f32, width: f32, height: f32) -> Option<f32> {
        let [w, h] = self.size;
        if w == 0 || h == 0 || self.energy.len() != FOCUS_COLUMNS * FOCUS_ROWS {
            return None;
        }
        let overlap = |a0: f32, a1: f32, b0: f32, b1: f32| (a1.min(b1) - a0.max(b0)).max(0.0);
        let edge = |i: usize, n: usize, of: usize| (i * of / n) as f32 / of as f32;
        let (mut energy, mut pixels) = (0.0f64, 0.0f64);
        for row in 0..FOCUS_ROWS {
            let (t0, t1) = (edge(row, FOCUS_ROWS, h), edge(row + 1, FOCUS_ROWS, h));
            let oy = overlap(t0, t1, y, y + height);
            if oy <= 0.0 || t1 <= t0 {
                continue;
            }
            for column in 0..FOCUS_COLUMNS {
                let (l0, l1) = (
                    edge(column, FOCUS_COLUMNS, w),
                    edge(column + 1, FOCUS_COLUMNS, w),
                );
                let ox = overlap(l0, l1, x, x + width);
                if ox <= 0.0 || l1 <= l0 {
                    continue;
                }
                let share = f64::from(ox / (l1 - l0) * oy / (t1 - t0));
                let i = row * FOCUS_COLUMNS + column;
                energy += share * self.energy[i] as f64;
                pixels += share * f64::from(self.pixels[i]);
            }
        }
        (pixels > 0.0).then(|| (energy / pixels) as f32)
    }
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
        let mut focus = FocusTiles {
            size: image.size,
            energy: vec![0; FOCUS_COLUMNS * FOCUS_ROWS],
            pixels: vec![0; FOCUS_COLUMNS * FOCUS_ROWS],
        };
        if w >= 3 && h >= 3 {
            // Each tile's interior columns; a row is summed a tile at a
            // time, in integers (no per-pixel lookup or float chain).
            let spans: Vec<(usize, usize)> = (0..FOCUS_COLUMNS)
                .map(|t| {
                    (
                        (t * w / FOCUS_COLUMNS).max(1),
                        ((t + 1) * w / FOCUS_COLUMNS).min(w - 1),
                    )
                })
                .collect();
            for y in 1..h - 1 {
                let tiles = (y * FOCUS_ROWS / h) * FOCUS_COLUMNS;
                let (above, row, below) = (
                    &luma[(y - 1) * w..y * w],
                    &luma[y * w..(y + 1) * w],
                    &luma[(y + 1) * w..(y + 2) * w],
                );
                let out = &mut strength[y * w..(y + 1) * w];
                for (t, &(x0, x1)) in spans.iter().enumerate() {
                    if x1 <= x0 {
                        continue;
                    }
                    // Equal-length slices: no bounds checks in the loop. The
                    // Laplacian of 8-bit luma is at most 1,020, so a span's
                    // sum of squares fits a u32 for any width the decoder
                    // admits (8,192 px).
                    let mut energy = 0u32;
                    for (((((c, l), r), u), d), s) in row[x0..x1]
                        .iter()
                        .zip(&row[x0 - 1..x1 - 1])
                        .zip(&row[x0 + 1..x1 + 1])
                        .zip(&above[x0..x1])
                        .zip(&below[x0..x1])
                        .zip(out[x0..x1].iter_mut())
                    {
                        let lap = (4.0 * c - l - r - u - d).abs();
                        *s = (lap * 0.25).min(255.0) as u8;
                        let code = lap as i32;
                        energy += (code * code) as u32;
                    }
                    focus.energy[tiles + t] += u64::from(energy);
                    focus.pixels[tiles + t] += (x1 - x0) as u32;
                }
            }
        }
        Self {
            size: image.size,
            strength,
            focus,
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

/// A channel code at or above this counts as clipped in a camera JPEG:
/// decoders clamp at 255, and JPEG ringing leaves clipped areas at 254-255.
pub(crate) const PREVIEW_CLIP_CODE: u8 = 254;

/// Levels of the camera's live JPEG, computed beside [`Peaking::analyze`]
/// from the same image on the client thread. The camera has already applied
/// its tone curve, white balance and JPEG coding: an estimate of exposure,
/// not the RAW's levels (a test shot reads those; `capture-test-shot.rs`).
#[derive(Clone, Debug, PartialEq)]
pub(crate) struct PreviewLevels {
    /// Pixels per Rec. 709 luma code of the sRGB values, 0-255.
    pub histogram: [u32; 256],
    /// Pixels per code of the red, green and blue channels.
    pub channels: [[u32; 256]; 3],
    pub pixels: u64,
    /// Share of pixels with any channel at or above [`PREVIEW_CLIP_CODE`].
    pub clipped_share: f32,
    /// Share of pixels with every channel at or below [`PREVIEW_BLACK_CODE`].
    pub black_share: f32,
    /// The clipped pixels (1) of the `size` image, for the clipping overlay.
    pub clip: Vec<u8>,
    pub size: [usize; 2],
}

/// A pixel whose channels are all at or below this code is black in a
/// camera JPEG: shadow detail there is gone from the preview.
pub(crate) const PREVIEW_BLACK_CODE: u8 = 3;

impl PreviewLevels {
    /// Shown beside every display of these levels.
    pub const CAUTION: &'static str = "estimate from the camera preview, not the RAW";
    /// The short form, beside the histogram.
    pub const CAUTION_SHORT: &'static str = "estimate, not the RAW";

    pub fn analyze(image: &ColorImage) -> Self {
        let mut histogram = [0u32; 256];
        let mut channels = [[0u32; 256]; 3];
        let (mut clipped, mut black) = (0u64, 0u64);
        let mut clip = Vec::with_capacity(image.pixels.len());
        for p in &image.pixels {
            let (r, g, b) = (p.r(), p.g(), p.b());
            // Rec. 709 weights in integers, rounded half up.
            let luma =
                (2126 * u32::from(r) + 7152 * u32::from(g) + 722 * u32::from(b) + 5000) / 10_000;
            histogram[luma.min(255) as usize] += 1;
            channels[0][usize::from(r)] += 1;
            channels[1][usize::from(g)] += 1;
            channels[2][usize::from(b)] += 1;
            let top = r.max(g).max(b);
            let hot = top >= PREVIEW_CLIP_CODE;
            clipped += u64::from(hot);
            black += u64::from(top <= PREVIEW_BLACK_CODE);
            clip.push(u8::from(hot));
        }
        let pixels = image.pixels.len() as u64;
        let share = |n: u64| {
            if pixels == 0 {
                0.0
            } else {
                n as f32 / pixels as f32
            }
        };
        Self {
            histogram,
            channels,
            pixels,
            clipped_share: share(clipped),
            black_share: share(black),
            clip,
            size: image.size,
        }
    }

    /// The clipped pixels painted `color`, the rest transparent.
    pub fn clip_overlay(&self, color: Color32) -> ColorImage {
        let mut out = ColorImage::filled(self.size, Color32::TRANSPARENT);
        for (pixel, hot) in out.pixels.iter_mut().zip(&self.clip) {
            if *hot != 0 {
                *pixel = color;
            }
        }
        out
    }

    /// The luma code below which `share` of the pixels fall (0-1), or
    /// `None` for an empty image.
    pub fn percentile(&self, share: f32) -> Option<u8> {
        if self.pixels == 0 {
            return None;
        }
        let target = (share.clamp(0.0, 1.0) as f64 * self.pixels as f64).ceil() as u64;
        let mut seen = 0u64;
        for (code, count) in self.histogram.iter().enumerate() {
            seen += u64::from(*count);
            if seen >= target.max(1) {
                return Some(code as u8);
            }
        }
        Some(255)
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
#[path = "capture-aids-tests.rs"]
mod live_tests;

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
    /// Flat grey fills one bin and clips nothing; a white half clips half
    /// the frame whichever channel is at the top; a saturated primary is
    /// clipped though its luma is low.
    #[test]
    fn preview_levels_count_luma_and_clipped_channels() {
        let mut image = ColorImage::filled([40, 10], Color32::from_gray(127));
        let flat = PreviewLevels::analyze(&image);
        assert_eq!(flat.pixels, 400);
        assert_eq!(flat.histogram[127], 400);
        assert_eq!(flat.clipped_share, 0.0);
        assert_eq!(flat.percentile(0.01), Some(127));
        assert_eq!(flat.percentile(0.99), Some(127));
        for y in 0..10 {
            for x in 20..40 {
                image.pixels[y * 40 + x] = Color32::WHITE;
            }
        }
        let half = PreviewLevels::analyze(&image);
        assert_eq!(half.histogram[255], 200);
        assert!((half.clipped_share - 0.5).abs() < 1e-6);
        assert_eq!(half.percentile(0.25), Some(127));
        assert_eq!(half.percentile(0.75), Some(255));
        image.pixels[0] = Color32::from_rgb(0, 0, 255);
        let blue = PreviewLevels::analyze(&image);
        assert!(blue.clipped_share > half.clipped_share);
        let overlay = blue.clip_overlay(Color32::RED);
        assert_eq!(overlay.pixels[0], Color32::RED);
        assert_eq!(overlay.pixels[1], Color32::TRANSPARENT);
        assert_eq!(overlay.pixels[39], Color32::RED, "white is clipped");
        assert_eq!(blue.histogram[18], 1, "a clipped blue has a low luma");
        assert_eq!(
            PreviewLevels::analyze(&ColorImage::filled([0, 0], Color32::BLACK)).percentile(0.5),
            None
        );
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
