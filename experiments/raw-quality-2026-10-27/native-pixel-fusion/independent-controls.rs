// Independent retained truth fixtures and fixed guards. Root builds/runs only.
include!(concat!(
    env!("CARGO_MANIFEST_DIR"),
    "/../../experiments/raw-quality-2026-10-26/insect-color/fixtures.rs"
));
use super::{Accumulator, Arm, Comparison, compare_generated};

fn arms(c: &Comparison) -> [(&'static str, &Arm); 5] {
    [
        ("canonical", &c.baseline),
        ("native-pixel", &c.native),
        ("uniform", &c.uniform),
        ("forced-source0", &c.forced),
        ("gathered-source0", &c.gathered_source0),
    ]
}
fn save_image(out: &Path, name: &str, rgb: &[f32], w: usize, h: usize) -> Value {
    use std::io::Write;
    assert_eq!(rgb.len(), w * h * 3);
    let bytes = rgb.iter().flat_map(|v| v.to_le_bytes()).collect::<Vec<_>>();
    let path = out.join(format!("{name}.f32"));
    std::fs::OpenOptions::new()
        .write(true)
        .create_new(true)
        .open(&path)
        .unwrap()
        .write_all(&bytes)
        .unwrap();
    json!({"path":path,"sha256":Sha256::digest(&bytes).iter().map(|v|format!("{v:02x}")).collect::<String>(),
        "width":w,"height":h,"format":"row-major camera-linear RGB f32 little-endian",
        "complete_generated_output":true})
}
fn score_truth(rgb: &[f32], truth: &[f32], win: Window) -> Score {
    let w = 2 * crop().width;
    assert_eq!(rgb.len(), truth.len());
    assert_eq!(rgb.len(), w * 2 * crop().height * 3);
    let n = ((win.x1 - win.x0) * (win.y1 - win.y0)) as f64;
    let mut sums = [[0.0; 4]; 3];
    let (mut err, mut green, mut chroma) = (0.0, 0.0, 0.0);
    for y in win.y0..win.y1 {
        for x in win.x0..win.x1 {
            let p = ((y - 2 * crop().y) * w + x - 2 * crop().x) * 3;
            let mut e = [0.0; 3];
            for ch in 0..3 {
                let t = f64::from(truth[p + ch]);
                let v = f64::from(rgb[p + ch]);
                assert!(v.is_finite());
                e[ch] = v - t;
                err += e[ch] * e[ch];
                for (a, b) in sums[ch].iter_mut().zip([t, v, t * t, t * v]) {
                    *a += b;
                }
            }
            green += e[1] * e[1];
            chroma += (e[0] - e[1]).powi(2) + (e[2] - e[1]).powi(2);
        }
    }
    let mut recovery = [0.0; 3];
    let mut truth_sd = [0.0; 3];
    for ch in 0..3 {
        let [st, sv, tt, tv] = sums[ch];
        let vv = (tt - st * st / n).max(0.0);
        truth_sd[ch] = (vv / n).sqrt();
        if vv > 1e-12 {
            recovery[ch] = (tv - st * sv / n) / vv;
        }
    }
    Score {
        rgb: (err / (3.0 * n)).sqrt(),
        green: (green / n).sqrt(),
        chroma: (chroma / (2.0 * n)).sqrt(),
        recovery,
        truth_sd,
    }
}
fn retention(b: &Score, a: &Score, ratio: f64) -> bool {
    (0..3).all(|ch| {
        b.truth_sd[ch] <= 1e-4
            || b.recovery[ch] < 0.5
            || a.recovery[ch].clamp(0.0, 1.0) >= ratio * b.recovery[ch].min(1.0)
    })
}
fn error_guard(b: &Score, a: &Score) -> bool {
    a.rgb <= 1.05 * b.rgb && a.chroma <= 1.05 * b.chroma
}
fn severe_component(b: &Score, a: &Score) -> bool {
    !retention(b, a, 0.8)
        || (0..3).any(|ch| b.truth_sd[ch] > 1e-4 && b.recovery[ch] <= 1.20 && a.recovery[ch] > 1.35)
}

// Retained cross-scale-source-prior component formula, with the common current
// fixture WB/noise/gather contract. These are independent of the new merger.
fn component(which: usize, ch: usize, x: f64, y: f64, source: Option<usize>) -> f64 {
    let focus = if which == 0 { 0.0 } else { 4.0 };
    let sigma = 0.65 + 3.0 * source.map_or(0.0, |k| (k as f64 - focus).abs());
    let (f, amplitude) = if which == 0 {
        (0.10, [0.045, 0.050, 0.040][ch])
    } else {
        (0.022, [0.090, 0.100, 0.085][ch])
    };
    let (dx, dy, phase) = if which == 0 {
        [(1.0, 0.0, 0.37), (0.8, 0.6, 1.13), (-0.6, 0.8, 2.07)][ch]
    } else {
        [(0.0, 1.0, 0.81), (0.6, -0.8, 1.71), (0.8, 0.6, 2.63)][ch]
    };
    amplitude
        * (-0.5 * (TAU * f * sigma).powi(2)).exp()
        * (TAU * f * (dx * x + dy * y) + phase).cos()
}
fn near_far(ch: usize, x: f64, y: f64, k: Option<usize>) -> f64 {
    0.27 + component(0, ch, x, y, k) + component(1, ch, x, y, k)
}
fn custom_truth(f: impl Fn(usize, f64, f64, Option<usize>) -> f64) -> Vec<f32> {
    let mut v = Vec::new();
    for y in 2 * crop().y..2 * (crop().y + crop().height) {
        for x in 2 * crop().x..2 * (crop().x + crop().width) {
            for ch in 0..3 {
                v.push(f(ch, x as f64, y as f64, None) as f32);
            }
        }
    }
    v
}
fn custom_frames(
    iso: f32,
    noise: &NoiseModel,
    acquisition_noise: f64,
    f: impl Fn(usize, f64, f64, Option<usize>) -> f64,
) -> Vec<Frame> {
    transforms()
        .iter()
        .enumerate()
        .map(|(k, &t)| {
            let mut frame = fixture_with_acquisition_noise(Scene::Flat, k, t, iso, noise, 0.0);
            let determinant = t.a.re * t.a.re + t.a.im * t.a.im;
            for y in 0..H {
                for x in 0..W {
                    let u = x as f64 - W as f64 / 2.0 - 2.0 * t.b.re;
                    let v = y as f64 - H as f64 / 2.0 - 2.0 * t.b.im;
                    let wx = W as f64 / 2.0 + (t.a.re * u + t.a.im * v) / determinant;
                    let wy = H as f64 / 2.0 + (-t.a.im * u + t.a.re * v) / determinant;
                    let signal = (f(channel(x, y), wx, wy, Some(k)) * f64::from(levels().range())
                        / f64::from(GAIN[channel(x, y)])) as f32;
                    let value = 512.0
                        + f64::from(signal)
                        + acquisition_noise
                            * gaussian(x, y, k)
                            * f64::from(noise.sigma(cfa(x, y), signal));
                    assert!(value > 512.0 && value < 15360.0);
                    frame.data[(frame.active.y + y) * frame.stride + frame.active.x + x] =
                        value.round() as u16;
                }
            }
            frame
        })
        .collect()
}
fn two_components(rgb: &[f32]) -> [[f64; 3]; 2] {
    let mut answer = [[0.0; 3]; 2];
    let n = ((INTERIOR.x1 - INTERIOR.x0) * (INTERIOR.y1 - INTERIOR.y0)) as f64;
    for ch in 0..3 {
        let mut s = [0.0; 8];
        for y in INTERIOR.y0..INTERIOR.y1 {
            for x in INTERIOR.x0..INTERIOR.x1 {
                let a = component(0, ch, x as f64, y as f64, None);
                let b = component(1, ch, x as f64, y as f64, None);
                let p = ((y - 2 * crop().y) * 2 * crop().width + x - 2 * crop().x) * 3;
                let v = f64::from(rgb[p + ch]);
                for (p, q) in s
                    .iter_mut()
                    .zip([a, b, v, a * a, b * b, a * b, a * v, b * v])
                {
                    *p += q;
                }
            }
        }
        let aa = s[3] - s[0] * s[0] / n;
        let bb = s[4] - s[1] * s[1] / n;
        let ab = s[5] - s[0] * s[1] / n;
        let av = s[6] - s[0] * s[2] / n;
        let bv = s[7] - s[1] * s[2] / n;
        let det = aa * bb - ab * ab;
        assert!(det > 0.1 * aa * bb && aa > 1e-4 && bb > 1e-4);
        answer[0][ch] = (av * bb - bv * ab) / det;
        answer[1][ch] = (bv * aa - av * ab) / det;
    }
    answer
}
fn components_retained(b: &[[f64; 3]; 2], a: &[[f64; 3]; 2], ratio: f64) -> bool {
    (0..2).all(|k| {
        (0..3).all(|ch| b[k][ch] < 0.5 || a[k][ch].clamp(0.0, 1.0) >= ratio * b[k][ch].min(1.0))
    })
}
fn commission_guards() -> Value {
    let inherited = commission();
    let flat = truth_image(Scene::Flat);
    let mut noisy = flat.clone();
    for (p, v) in noisy.iter_mut().enumerate() {
        *v += 0.03
            * gaussian(
                p / 3 % (2 * crop().width),
                p / 3 / (2 * crop().width),
                p % 3,
            ) as f32;
    }
    let good = score_truth(&flat, &flat, INTERIOR);
    let bad = score_truth(&noisy, &flat, INTERIOR);
    assert!(!error_guard(&good, &bad) && bad.rgb > 0.02);
    let mut thin_records = Vec::new();
    for inverted in [false, true] {
        let truth = if inverted {
            custom_truth(|c, x, y, k| 0.5 - radiance(Scene::ThinDepth, c, x, y, k))
        } else {
            truth_image(Scene::ThinDepth)
        };
        for win in [THIN_FAR, THIN_NEAR] {
            let mut erased = truth.clone();
            for y in win.y0..win.y1 {
                for x in win.x0..win.x1 {
                    let p = ((y - 2 * crop().y) * 2 * crop().width + x - 2 * crop().x) * 3;
                    erased[p..p + 3].fill(0.25);
                }
            }
            let b = score_truth(&truth, &truth, win);
            let a = score_truth(&erased, &truth, win);
            assert!(!retention(&b, &a, 0.98) && severe_component(&b, &a));
            thin_records.push(json!({"dark":inverted,"region":win.name,"erased":score_json(&a)}));
        }
    }
    let truth = custom_truth(near_far);
    let exact = two_components(&truth);
    assert!(exact.iter().flatten().all(|v| (*v - 1.0).abs() < 1e-5));
    let mut half = truth.clone();
    for y in 2 * crop().y..2 * (crop().y + crop().height) {
        for x in 2 * crop().x..2 * (crop().x + crop().width) {
            for ch in 0..3 {
                let p = ((y - 2 * crop().y) * 2 * crop().width + x - 2 * crop().x) * 3 + ch;
                half[p] -= (0.5 * component(1, ch, x as f64, y as f64, None)) as f32;
            }
        }
    }
    let h = two_components(&half);
    assert!(h[0].iter().all(|v| (*v - 1.0).abs() < 1e-5));
    assert!(h[1].iter().all(|v| (*v - 0.5).abs() < 1e-5));
    assert!(!components_retained(&exact, &h, 0.98) && !components_retained(&exact, &h, 0.8));
    let mut over = truth_image(Scene::Neutral);
    let neutral = over.clone();
    for v in &mut over {
        *v = 0.25 + 1.4 * (*v - 0.25);
    }
    let b = score_truth(&neutral, &neutral, INTERIOR);
    let a = score_truth(&over, &neutral, INTERIOR);
    assert!(severe_component(&b, &a));
    let mut false_colour = neutral.clone();
    for p in false_colour.chunks_exact_mut(3) {
        p[0] += 0.03;
    }
    assert!(!error_guard(
        &b,
        &score_truth(&false_colour, &neutral, INTERIOR)
    ));
    json!({"inherited":inherited,"flat_added_noise":score_json(&bad),"thin_erasure":thin_records,
        "near_far_exact":exact,"near_far_half_far":h,"excess_contrast_rejected":true,"false_colour_rejected":true})
}
fn accumulator_controls() -> Value {
    let n = 7;
    let mut a = Accumulator::new(n);
    let mut numerator = vec![vec![0.0f64; n]; 4];
    let mut means = vec![vec![0.0f64; n]; 4];
    let mut den = vec![0.0f64; n];
    for k in 0..3 {
        let planes = (0..4)
            .map(|ch| {
                (0..n)
                    .map(|j| 100.0 + 31.0 * ch as f32 + 17.0 * k as f32 + j as f32 * 0.25)
                    .collect()
            })
            .collect::<Vec<Vec<f32>>>();
        let weights = (0..n)
            .map(|j| match j % 3 {
                0 => 0.0,
                1 => (k + 1) as f32,
                _ => {
                    if k == 2 {
                        1.0
                    } else {
                        0.0
                    }
                }
            })
            .collect::<Vec<_>>();
        a.add(&planes, &weights).unwrap();
        for j in 0..n {
            den[j] += f64::from(weights[j]);
            for ch in 0..4 {
                numerator[ch][j] += f64::from(weights[j]) * f64::from(planes[ch][j]);
                means[ch][j] += f64::from(planes[ch][j]);
            }
        }
    }
    let result = a.finish().unwrap();
    for j in 0..n {
        for ch in 0..4 {
            let expected = if den[j] > 0.0 {
                numerator[ch][j] / den[j]
            } else {
                means[ch][j] / 3.0
            };
            assert!((f64::from(result[ch][j]) - expected).abs() < 0.001);
        }
    }
    let mut source = vec![vec![1234.5; n]; 4];
    source[0][0] = -0.0;
    source[2][1] = -0.25;
    for count in [1, 3] {
        let mut equal = Accumulator::new(n);
        for k in 0..count {
            equal
                .add(&source, &vec![if k == 0 { 0.0 } else { (k + 1) as f32 }; n])
                .unwrap();
        }
        assert!(exact(&equal.finish().unwrap(), &source));
    }
    let w0 = 80.0f32.exp();
    let w1 = 79.5f32.exp();
    assert!(w0.is_finite() && w1.is_finite());
    let mut high = Accumulator::new(1);
    high.add(&vec![vec![60000.0]; 4], &[w0]).unwrap();
    high.add(&vec![vec![64000.0]; 4], &[w1]).unwrap();
    let high = high.finish().unwrap();
    let expected =
        (f64::from(w0) * 60000.0 + f64::from(w1) * 64000.0) / (f64::from(w0) + f64::from(w1));
    assert!(
        high.iter()
            .all(|p| p[0].is_finite() && (f64::from(p[0]) - expected).abs() < 0.05)
    );
    // Even equal tuples must not let a nonfinite denominator escape validation.
    let mut overflow = Accumulator::new(1);
    overflow.add(&vec![vec![1.0]; 4], &[f32::MAX]).unwrap();
    let second = overflow.add(&vec![vec![1.0]; 4], &[f32::MAX]);
    assert!(second.is_err() || overflow.finish().is_err());
    assert!(Accumulator::new(1).finish().is_err());
    json!({"mixed_shared_denominator_oracle":true,"zero_denominator_averages_all_sources":true,
        "equal_and_single_exact":true,"high_dn_values":[60000,64000],"high_finite_weights":[w0,w1],
        "high_expected_dn":expected,"high_output_dn":high,"nonfinite_sum_cannot_escape_equal_override":true})
}

fn run_case(
    out: &Path,
    name: &str,
    frames: &[Frame],
    truth: &[f32],
    windows: &[Window],
    noise: &NoiseModel,
    flat: bool,
    neutral: bool,
    glint: bool,
    joint: bool,
    zero: bool,
    single: bool,
) -> (Value, bool, bool) {
    let ts = transforms();
    let ts = if single { &ts[2..3] } else { &ts[..] };
    let original = frames.iter().map(|f| hash(&f.data)).collect::<Vec<_>>();
    let c = compare_generated(frames, ts, crop(), noise, MergeConfig::default()).unwrap();
    let outputs=arms(&c).iter().map(|(arm,a)|json!({"arm":arm,"master":save_image(out,&format!("{name}-{arm}"),&a.rgb,c.native_width,c.native_height)})).collect::<Vec<_>>();
    let truth_file = save_image(
        out,
        &format!("{name}-truth"),
        truth,
        c.native_width,
        c.native_height,
    );
    let (mut strict, mut severe) = (true, false);
    let mut rows = Vec::new();
    for &win in windows {
        let b = score_truth(&c.baseline.rgb, truth, win);
        let a = score_truth(&c.native.rgb, truth, win);
        let u = score_truth(&c.uniform.rgb, truth, win);
        let no_harm = error_guard(&b, &a) && retention(&b, &a, 0.98);
        let flat_bad = flat && a.rgb > 1.20 * b.rgb && a.rgb > 1.25 * u.rgb;
        let colour_bad = neutral && a.chroma > 1.50 * b.chroma && a.chroma > 0.0025;
        let glint_bad = glint && a.rgb > 1.50 * b.rgb && a.rgb > 0.0025;
        let loss = !flat && severe_component(&b, &a);
        strict &= no_harm;
        severe |= flat_bad || colour_bad || glint_bad || loss;
        rows.push(json!({"region":win.name,"native_xyxy":[win.x0,win.y0,win.x1,win.y1],
            "arms":arms(&c).iter().map(|(name,arm)|json!({"name":name,"score":score_json(&score_truth(&arm.rgb,truth,win))})).collect::<Vec<_>>(),
            "strict_no_harm":no_harm,"severe_flat":flat_bad,"severe_neutral_colour":colour_bad,
            "severe_glint_neighbor":glint_bad,"severe_component":loss}));
    }
    let mut components = Value::Null;
    let mut wrong_source_rejected = None;
    if joint {
        let b = two_components(&c.baseline.rgb);
        let a = two_components(&c.native.rgb);
        let forced = two_components(&c.forced.rgb);
        let live = b.iter().flatten().all(|v| *v >= 0.5);
        let retained = components_retained(&b, &a, 0.98);
        let serious = !components_retained(&b, &a, 0.8);
        let wrong = (0..3)
            .any(|ch| b[1][ch] >= 0.5 && forced[1][ch].clamp(0.0, 1.0) < 0.8 * b[1][ch].min(1.0));
        strict &= retained && live;
        severe |= serious;
        wrong_source_rejected = Some(wrong);
        components = json!({"order":["near-fine","far-coarse"],"canonical":b,"candidate":a,
            "uniform":two_components(&c.uniform.rgb),"forced_source0":forced,"canonical_both_live":live,
            "strict_retention":retained,"severe_loss":serious,"wrong_source_far_guard_rejected":wrong});
    }
    let record = json!({"name":name,"iso":noise.iso,"windows":rows,"components":components,
        "truth":truth_file,"outputs":outputs,"evidence":c.evidence,"strict_no_harm":strict,
        "severe_generated_loss":severe,"zero_evidence_case":zero,"singleton_case":single});
    write(&out.join(format!("{name}.json")), &record);
    assert_eq!(
        (c.native_width, c.native_height),
        (2 * crop().width, 2 * crop().height)
    );
    assert!(
        frames
            .iter()
            .zip(&original)
            .all(|(f, h)| hash(&f.data) == *h)
    );
    assert!(exact(&c.forced.planes4, &c.gathered_source0.planes4));
    assert!(exact_slice(&c.forced.rgb, &c.gathered_source0.rgb));
    if zero {
        assert_eq!(
            c.evidence["native"]["unsupported_pixels"].as_u64(),
            Some((crop().width * crop().height) as u64)
        );
        assert!(exact(&c.native.planes4, &c.uniform.planes4));
    }
    if single {
        assert!(exact(&c.native.planes4, &c.gathered_source0.planes4));
        assert!(exact_slice(&c.native.rgb, &c.gathered_source0.rgb));
    }
    if let Some(rejected) = wrong_source_rejected {
        assert!(
            rejected,
            "fixed source0 foil not caught by far/coarse guard"
        );
    }
    (record, strict, severe)
}

// One root-approved larger FLAT only; matches the full-photo finest exponent
// cap without tuning the small structured fixtures or retaining a source volume.
fn full_exponent_flat(out: &Path) -> (Value, bool, bool) {
    let noise = profile::noise_model_for("ILCE-7CM2", Some(100.0), levels());
    let ts = transforms();
    let extent = 1088;
    let stride = extent + 29;
    let frames = ts
        .iter()
        .enumerate()
        .map(|(k, &t)| {
            let mut frame = fixture_with_acquisition_noise(Scene::Flat, k, t, 100.0, &noise, 0.0);
            frame.stride = stride;
            frame.buffer_height = extent + 29;
            frame.active = Region {
                x: 7,
                y: 11,
                width: extent,
                height: extent,
            };
            frame.data = vec![64999; stride * frame.buffer_height];
            for y in 0..extent {
                for x in 0..extent {
                    let signal = 0.25 * levels().range() / GAIN[channel(x, y)];
                    let v = 512.0
                        + f64::from(signal)
                        + gaussian(x, y, k) * f64::from(noise.sigma(cfa(x, y), signal));
                    assert!(v > 512.0 && v < 15360.0);
                    frame.data[(frame.active.y + y) * stride + frame.active.x + x] =
                        v.round() as u16;
                }
            }
            frame
        })
        .collect::<Vec<_>>();
    let originals = frames.iter().map(|f| hash(&f.data)).collect::<Vec<_>>();
    let big = align_cmd::CropRect {
        x: 8,
        y: 8,
        width: 512,
        height: 512,
    };
    let cfg = MergeConfig::default();
    let sizes = strehl_core::pyramid::level_sizes(big.width, big.height, cfg.bands);
    let actual_bands = sizes.len() - 1;
    assert_eq!(actual_bands, 6);
    assert_eq!(cfg.exponent_at(0, actual_bands), 8.0);
    let c = compare_generated(&frames, &ts, big, &noise, cfg).unwrap();
    let mut scores = Vec::new();
    let mut errors = Vec::new();
    for (name, a) in arms(&c) {
        let (mut rgb, mut chroma, mut n) = (0.0, 0.0, 0usize);
        for y in 32..c.native_height - 32 {
            for x in 32..c.native_width - 32 {
                let p = (y * c.native_width + x) * 3;
                let e = [0, 1, 2].map(|ch| f64::from(a.rgb[p + ch]) - 0.25);
                rgb += e.iter().map(|v| v * v).sum::<f64>();
                chroma += (e[0] - e[1]).powi(2) + (e[2] - e[1]).powi(2);
                n += 1;
            }
        }
        let rgb = (rgb / (3 * n) as f64).sqrt();
        let chroma = (chroma / (2 * n) as f64).sqrt();
        errors.push((rgb, chroma));
        scores.push(json!({"arm":name,"rgb_rmse":rgb,"chroma_rmse":chroma,
            "master":save_image(out,&format!("full-finest-flat-{name}"),&a.rgb,c.native_width,c.native_height)}));
    }
    let b = errors[0];
    let a = errors[1];
    let u = errors[2];
    let strict = a.0 <= 1.05 * b.0 && a.1 <= 1.05 * b.1;
    let severe = a.0 > 1.20 * b.0 && a.0 > 1.25 * u.0;
    let record = json!({"name":"full-finest-exponent-flat-iso100","active_extent":[extent,extent],"crop_quad":[8,8,512,512],
        "scored_output_xyxy":[32,32,992,992],"truth_constant_camera_rgb":[0.25,0.25,0.25],
        "effective_ac_bands":actual_bands,"effective_exponents":(0..actual_bands).map(|k|cfg.exponent_at(k,actual_bands)).collect::<Vec<_>>(),
        "strict_no_harm":strict,"severe_generated_loss":severe,"arms":scores,"evidence":c.evidence});
    write(&out.join("full-finest-flat.json"), &record);
    assert!(
        frames
            .iter()
            .zip(&originals)
            .all(|(f, h)| hash(&f.data) == *h)
    );
    assert!(exact(&c.forced.planes4, &c.gathered_source0.planes4));
    (record, strict, severe)
}

#[test]
#[ignore = "root-scheduled actual-consumer screen; requires STREHL_NATIVE_PIXEL_OUT"]
fn fixed_native_pixel_screen() {
    let out = PathBuf::from(
        std::env::var_os("STREHL_NATIVE_PIXEL_OUT").expect("fresh root-owned output required"),
    );
    assert!(out.is_absolute() && !out.exists());
    std::fs::create_dir(&out).unwrap();
    let operator = accumulator_controls();
    let commission = commission_guards();
    write(
        &out.join("operator-controls.json"),
        &json!({"operator":operator,"guard_commission":commission}),
    );
    let (mut records, mut strict_all, mut severe_any) = (Vec::new(), true, false);
    // All flat acquisition/consumer runs precede structured cases.
    for iso in [100.0f32, 400.0] {
        let noise = profile::noise_model_for("ILCE-7CM2", Some(iso), levels());
        let frames = transforms()
            .iter()
            .enumerate()
            .map(|(k, &t)| fixture(Scene::Flat, k, t, iso, &noise))
            .collect::<Vec<_>>();
        let (r, s, v) = run_case(
            &out,
            &format!("flat-iso{iso}"),
            &frames,
            &truth_image(Scene::Flat),
            &[INTERIOR],
            &noise,
            true,
            false,
            false,
            false,
            false,
            false,
        );
        records.push(r);
        strict_all &= s;
        severe_any |= v;
    }
    let (r, s, v) = full_exponent_flat(&out);
    records.push(r);
    strict_all &= s;
    severe_any |= v;
    let noise = profile::noise_model_for("ILCE-7CM2", Some(100.0), levels());
    let zero = custom_frames(100.0, &noise, 0.0, |_, _, _, k| {
        0.25 + 0.01 * k.unwrap_or(2) as f64
    });
    let (r, _, _) = run_case(
        &out,
        "zero-evidence-distinct-constants",
        &zero,
        &custom_truth(|_, _, _, _| 0.27),
        &[INTERIOR],
        &noise,
        true,
        false,
        false,
        false,
        true,
        false,
    );
    records.push(r);
    for scene in [
        Scene::Neutral,
        Scene::Cofocused,
        Scene::ColourOnly,
        Scene::ThinDepth,
        Scene::Radial,
        Scene::ClippedGlint,
    ] {
        let frames = transforms()
            .iter()
            .enumerate()
            .map(|(k, &t)| fixture(scene, k, t, 100.0, &noise))
            .collect::<Vec<_>>();
        let windows: &[Window] = match scene {
            Scene::ThinDepth => &[THIN_FAR, THIN_NEAR, JUNCTION],
            Scene::Radial => &[RADIAL],
            Scene::ClippedGlint => &[OUTSIDE, NEAR],
            _ => &[INTERIOR],
        };
        let (r, s, v) = run_case(
            &out,
            scene.name(),
            &frames,
            &truth_image(scene),
            windows,
            &noise,
            false,
            scene == Scene::Neutral,
            scene == Scene::ClippedGlint,
            false,
            false,
            false,
        );
        records.push(r);
        strict_all &= s;
        severe_any |= v;
        if scene == Scene::ThinDepth {
            let (r, _, _) = run_case(
                &out,
                "single-source2",
                &frames[2..3],
                &truth_image(scene),
                windows,
                &noise,
                false,
                false,
                false,
                false,
                false,
                true,
            );
            records.push(r);
        }
    }
    let dark = custom_frames(100.0, &noise, 1.0, |c, x, y, k| {
        0.5 - radiance(Scene::ThinDepth, c, x, y, k)
    });
    let (r, s, v) = run_case(
        &out,
        "dark-crossed-thin-depths",
        &dark,
        &custom_truth(|c, x, y, k| 0.5 - radiance(Scene::ThinDepth, c, x, y, k)),
        &[THIN_FAR, THIN_NEAR, JUNCTION],
        &noise,
        false,
        false,
        false,
        false,
        false,
        false,
    );
    records.push(r);
    strict_all &= s;
    severe_any |= v;
    for iso in [100.0f32, 400.0] {
        let noise = profile::noise_model_for("ILCE-7CM2", Some(iso), levels());
        let frames = custom_frames(iso, &noise, 1.0, near_far);
        let (r, s, v) = run_case(
            &out,
            &format!("near-fine-far-coarse-iso{iso}"),
            &frames,
            &custom_truth(near_far),
            &[INTERIOR],
            &noise,
            false,
            false,
            false,
            true,
            false,
            false,
        );
        records.push(r);
        strict_all &= s;
        severe_any |= v;
    }
    write(
        &out.join("screen.json"),
        &json!({"status":"SCREEN_COMPLETE","strict_no_harm_all":strict_all,
        "severe_generated_loss":severe_any,"photographic_improvement_claimed":false,"cases":records,
        "operator":operator,"guard_commission":commission,"small_fixture_noise":format!("{noise:?}"),
        "scope":"one fixed actual-consumer screen; small structured scenes have4 effective AC bands; large flat has6 and full finest exponent8; no parameter rescue or general promotion"}),
    );
    eprintln!(
        "NATIVE_PIXEL_SCREEN strict_no_harm_all={strict_all} severe_generated_loss={severe_any}"
    );
}
