use super::*;

fn resize(pixels: &[f32], from: [u32; 2], to: [u32; 2], filter: ResizeFilter) -> Vec<f32> {
    resize_rgb(pixels, from, to, filter, &AtomicBool::new(false)).unwrap()
}

fn grey(width: u32, height: u32, f: impl Fn(u32, u32) -> f32) -> Vec<f32> {
    let mut out = Vec::with_capacity((width * height * 3) as usize);
    for y in 0..height {
        for x in 0..width {
            out.extend([f(x, y); 3]);
        }
    }
    out
}

#[test]
fn constants_survive_unclamped_including_hdr_light() {
    for filter in [ResizeFilter::Mitchell, ResizeFilter::Lanczos3] {
        for (from, to) in [
            ([97, 61], [40, 25]),
            ([64, 64], [64, 64]),
            ([30, 20], [7, 5]),
        ] {
            for level in [0.25f32, 5.0, 812.5] {
                let out = resize(&grey(from[0], from[1], |_, _| level), from, to, filter);
                assert_eq!(out.len(), (to[0] * to[1] * 3) as usize);
                assert!(
                    out.iter().all(|&v| v == level),
                    "{filter:?} {from:?}->{to:?} at {level}"
                );
            }
        }
    }
}

#[test]
fn downscale_is_anti_aliased_where_point_sampling_aliases() {
    // A Nyquist grating: alternate columns 0 and 1.
    let src = grey(96, 8, |x, _| (x % 2) as f32);
    // Negative control: nearest-centre sampling at 3x returns the grating's
    // phase, a full-contrast false pattern.
    let point: Vec<f32> = (0..32).map(|o| ((o * 3 + 1) % 2) as f32).collect();
    assert!(point.contains(&0.0) && point.contains(&1.0));
    for filter in [ResizeFilter::Mitchell, ResizeFilter::Lanczos3] {
        let out = resize(&src, [96, 8], [32, 8], filter);
        let worst = out.iter().map(|v| (v - 0.5).abs()).fold(0.0f32, f32::max);
        assert!(worst < 0.06, "{filter:?} left {worst} of the grating");
    }
}

#[test]
fn mitchell_overshoots_a_step_less_than_lanczos() {
    // A hard step downscaled 4x; overshoot is light the master does not hold.
    let src = grey(400, 4, |x, _| if x < 200 { 0.1 } else { 0.9 });
    let overshoot = |filter| {
        let out = resize(&src, [400, 4], [100, 4], filter);
        let hi = out.iter().copied().fold(f32::MIN, f32::max) - 0.9;
        let lo = 0.1 - out.iter().copied().fold(f32::MAX, f32::min);
        hi.max(lo) / 0.8
    };
    let (mitchell, lanczos) = (
        overshoot(ResizeFilter::Mitchell),
        overshoot(ResizeFilter::Lanczos3),
    );
    println!(
        "step overshoot at 4x: Mitchell {:.2}%, Lanczos 3 {:.2}%",
        mitchell * 100.0,
        lanczos * 100.0
    );
    // MEASURED when written: Mitchell 0.77 %, Lanczos 3 1.70 % of the step.
    assert!(lanczos > 0.01, "fixture must provoke Lanczos ringing");
    assert!(mitchell < lanczos / 2.0 && mitchell < 0.02);
}

#[test]
fn integer_reduction_preserves_the_mean() {
    let src = grey(64, 48, |x, y| ((x * 7 + y * 13) % 17) as f32 * 0.1);
    let mean = |v: &[f32]| v.iter().map(|&x| f64::from(x)).sum::<f64>() / v.len() as f64;
    let out = resize(&src, [64, 48], [32, 24], ResizeFilter::Mitchell);
    assert!((mean(&src) - mean(&out)).abs() < 2e-3);
}

#[test]
fn target_never_enlarges_and_keeps_aspect() {
    let r = Resize {
        long_edge: 2560,
        filter: ResizeFilter::Mitchell,
    };
    assert_eq!(r.target([7032, 4688]), Some([2560, 1707]));
    assert_eq!(r.target([4688, 7032]), Some([1707, 2560]));
    assert_eq!(r.target([2560, 1000]), None);
    assert_eq!(r.target([800, 600]), None);
    assert!(Resize { long_edge: 8, ..r }.validate().is_err());
}

#[test]
fn catmull_rom_is_exact_at_centres_and_on_ramps() {
    let (w, h) = (9u32, 7u32);
    let src = grey(w, h, |x, y| x as f32 * 0.5 + y as f32 * 0.25);
    for y in 0..h {
        for x in 0..w {
            let p = catmull_rom(&src, w, h, f64::from(x), f64::from(y));
            let i = ((y * w + x) * 3) as usize;
            assert_eq!(p[0], src[i]);
        }
    }
    // Interior: a linear ramp is reproduced between centres.
    let p = catmull_rom(&src, w, h, 3.25, 2.5);
    assert!((p[0] - (3.25 * 0.5 + 2.5 * 0.25)).abs() < 1e-5);
}
