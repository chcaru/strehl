//! The live view's per-preview analysis: its cost on the client thread.
use super::*;
use std::time::Instant;

/// A deterministic camera-preview-like image: dark surround, a textured
/// ellipse, a few clipped specular points.
fn preview(width: usize, height: usize) -> ColorImage {
    let mut image = ColorImage::filled([width, height], Color32::BLACK);
    let (cx, cy) = (width as f32 * 0.5, height as f32 * 0.5);
    let (rx, ry) = (width as f32 * 0.34, height as f32 * 0.3);
    for y in 0..height {
        for x in 0..width {
            let (dx, dy) = ((x as f32 - cx) / rx, (y as f32 - cy) / ry);
            let r = dx * dx + dy * dy;
            if r > 1.0 {
                continue;
            }
            let band = (dx * 9.0).sin() * 0.5 + 0.5;
            let speckle = ((x * 7919 + y * 104_729) % 97) as f32 / 97.0 - 0.5;
            let v = (0.25 + 0.55 * band + 0.1 * speckle).clamp(0.0, 1.0);
            image.pixels[y * width + x] = if (x * 31 + y * 17) % 997 == 0 {
                Color32::WHITE
            } else {
                Color32::from_rgb(
                    (40.0 + 60.0 * v) as u8,
                    (90.0 + 150.0 * v) as u8,
                    (110.0 + 120.0 * v) as u8,
                )
            };
        }
    }
    image
}

/// The same picture with its detail softened by a box blur of `radius`.
fn blurred(image: &ColorImage, radius: usize) -> ColorImage {
    let [w, h] = image.size;
    let mut out = image.clone();
    for y in 0..h {
        for x in 0..w {
            let (mut sum, mut n) = ([0u32; 3], 0u32);
            for yy in y.saturating_sub(radius)..(y + radius + 1).min(h) {
                for xx in x.saturating_sub(radius)..(x + radius + 1).min(w) {
                    let p = image.pixels[yy * w + xx];
                    sum[0] += u32::from(p.r());
                    sum[1] += u32::from(p.g());
                    sum[2] += u32::from(p.b());
                    n += 1;
                }
            }
            out.pixels[y * w + x] =
                Color32::from_rgb((sum[0] / n) as u8, (sum[1] / n) as u8, (sum[2] / n) as u8);
        }
    }
    out
}

/// The channel histograms count every pixel once; black and clipped
/// shares follow the codes.
#[test]
fn channels_and_black_share() {
    let mut image = ColorImage::filled([20, 10], Color32::from_gray(2));
    for x in 0..5 {
        image.pixels[x] = Color32::from_rgb(255, 10, 40);
    }
    let levels = PreviewLevels::analyze(&image);
    for channel in &levels.channels {
        assert_eq!(channel.iter().sum::<u32>(), 200);
    }
    assert_eq!(levels.channels[0][255], 5);
    assert_eq!(levels.channels[1][10], 5);
    assert_eq!(levels.channels[2][2], 195);
    assert!((levels.black_share - 195.0 / 200.0).abs() < 1e-6);
    assert!((levels.clipped_share - 5.0 / 200.0).abs() < 1e-6);
    assert_eq!(levels.histogram[2], 195);
    // Integer luma: 0.2126 * 255 + 0.7152 * 10 + 0.0722 * 40 = 64.24.
    assert_eq!(levels.histogram[64], 5);
}

/// The subject box's focus is the mean squared Laplacian of the tiles it
/// covers: nothing on a flat picture, more where the detail is, and it
/// falls as the same picture is softened.
#[test]
fn focus_in_the_box_follows_the_detail() {
    let flat = Peaking::analyze(&ColorImage::filled([64, 48], Color32::from_gray(90)));
    assert_eq!(flat.focus.focus_in(0.0, 0.0, 1.0, 1.0), Some(0.0));
    let sharp = preview(320, 240);
    let peaks = Peaking::analyze(&sharp);
    let whole = peaks.focus.focus_in(0.0, 0.0, 1.0, 1.0).unwrap();
    let total: f64 = peaks.focus.energy.iter().map(|e| *e as f64).sum();
    let count: f64 = peaks.focus.pixels.iter().map(|n| f64::from(*n)).sum();
    assert!(((total / count) as f32 - whole).abs() / whole < 1e-4);
    assert_eq!(count as usize, 318 * 238, "every interior pixel once");
    let subject = peaks.focus.focus_in(0.25, 0.25, 0.5, 0.5).unwrap();
    let corner = peaks.focus.focus_in(0.0, 0.0, 0.1, 0.1).unwrap();
    assert!(
        subject > whole && corner < whole * 0.05,
        "{subject} {whole} {corner}"
    );
    let mut last = subject;
    for radius in [1, 2, 4] {
        let soft = Peaking::analyze(&blurred(&sharp, radius))
            .focus
            .focus_in(0.25, 0.25, 0.5, 0.5)
            .unwrap();
        assert!(soft < last * 0.8, "radius {radius}: {soft} after {last}");
        last = soft;
    }
    assert_eq!(
        peaks.focus.focus_in(1.2, 0.0, 0.5, 0.5),
        None,
        "off the picture"
    );
}

fn median_ms(mut runs: Vec<f64>) -> f64 {
    runs.sort_by(f64::total_cmp);
    runs[runs.len() / 2]
}

/// Milliseconds per preview of the client thread's analysis:
/// `cargo test --release --locked -p strehl-ui preview_analysis_cost -- --ignored --nocapture`.
#[test]
#[ignore = "benchmark: prints ms per preview"]
fn preview_analysis_cost() {
    for (width, height) in [(640, 480), (960, 640), (1024, 680)] {
        let image = preview(width, height);
        let (mut peaking, mut levels, mut reduce) = (Vec::new(), Vec::new(), Vec::new());
        for i in 0..60 {
            let t = Instant::now();
            let peaks = std::hint::black_box(Peaking::analyze(std::hint::black_box(&image)));
            peaking.push(t.elapsed().as_secs_f64() * 1000.0);
            let t = Instant::now();
            std::hint::black_box(PreviewLevels::analyze(std::hint::black_box(&image)));
            levels.push(t.elapsed().as_secs_f64() * 1000.0);
            // The UI's share: the subject box from the tiles.
            let t = Instant::now();
            let at = 0.1 + 0.001 * i as f32;
            std::hint::black_box(peaks.focus.focus_in(at, at, 0.8, 0.8));
            reduce.push(t.elapsed().as_secs_f64() * 1000.0);
        }
        println!(
            "preview_analysis {width}x{height}: peaking median {:.3} ms, levels median {:.3} ms, \
             subject box from tiles median {:.4} ms",
            median_ms(peaking),
            median_ms(levels),
            median_ms(reduce)
        );
    }
}
