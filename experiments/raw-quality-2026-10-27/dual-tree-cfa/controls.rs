// Independently chosen fixed controls. Root alone builds and executes.
use super::*;
use anyhow::{Context, ensure};
use sha2::{Digest, Sha256};
use std::{
    fs::OpenOptions,
    io::Write,
    path::{Path, PathBuf},
};
use strehl_core::{CfaPlane, align::Cx, profile};
use strehl_raw::Region;

const W: usize = 160;
const H: usize = 144;
const N: usize = 5;
const RANGE: f32 = 14848.;
const GAIN: [f32; 3] = [1.6, 1., 2.];
const TAU: f32 = std::f32::consts::TAU;
const PR_MAX: f32 = 0.05;
const PR_RMS: f32 = 0.01;

fn crop() -> crate::align_cmd::CropRect {
    crate::align_cmd::CropRect {
        x: 8,
        y: 8,
        width: 64,
        height: 56,
    }
}
fn levels() -> Levels {
    Levels {
        black: 512.,
        white: 15360.,
    }
}
fn ch(x: usize, y: usize) -> usize {
    match (x % 2, y % 2) {
        (0, 0) => 0,
        (1, 1) => 2,
        _ => 1,
    }
}
fn phase(x: usize, y: usize) -> CfaPlane {
    match (x % 2, y % 2) {
        (0, 0) => CfaPlane::R,
        (1, 0) => CfaPlane::G1,
        (0, 1) => CfaPlane::G2,
        _ => CfaPlane::B,
    }
}
fn sha(bytes: &[u8]) -> String {
    Sha256::digest(bytes)
        .iter()
        .map(|x| format!("{x:02x}"))
        .collect()
}
fn save_json(path: &Path, v: &Value) -> Result<()> {
    let mut f = OpenOptions::new().write(true).create_new(true).open(path)?;
    serde_json::to_writer_pretty(&mut f, v)?;
    f.write_all(b"\n")?;
    Ok(())
}
fn bytes_file(path: &Path, bytes: &[u8]) -> Result<Value> {
    OpenOptions::new()
        .write(true)
        .create_new(true)
        .open(path)?
        .write_all(bytes)?;
    Ok(json!({"path":path,"bytes":bytes.len(),"sha256":sha(bytes)}))
}
fn image(out: &Path, name: &str, rgb: &[f32], w: usize, h: usize) -> Result<Value> {
    ensure!(rgb.len() == 3 * w * h && rgb.iter().all(|x| x.is_finite()));
    let f32_ref = bytes_file(
        &out.join(format!("{name}.f32")),
        &rgb.iter().flat_map(|x| x.to_le_bytes()).collect::<Vec<_>>(),
    )?;
    let mut ppm = format!("P6\n{w} {h}\n255\n").into_bytes();
    for &v in rgb {
        let x = v.clamp(0., 1.);
        let s = if x <= 0.0031308 {
            12.92 * x
        } else {
            1.055 * x.powf(1. / 2.4) - 0.055
        };
        ppm.push((255. * s).round().clamp(0., 255.) as u8);
    }
    let ppm_ref = bytes_file(&out.join(format!("{name}.ppm")), &ppm)?;
    Ok(json!({"float":f32_ref,"preview":ppm_ref,"dimensions":[w,h],
        "complete_generated_output":true,"display":"fixed camera RGB clipped0..1 then sRGB curve; no color-calibrated display claim"}))
}
fn hash32(mut x: u32) -> u32 {
    x ^= x >> 16;
    x = x.wrapping_mul(0x7feb352d);
    x ^= x >> 15;
    x = x.wrapping_mul(0x846ca68b);
    x ^ (x >> 16)
}
fn gaussian(x: usize, y: usize, k: usize) -> f32 {
    let s = x as u32 ^ ((y as u32) << 16) ^ (k as u32).wrapping_mul(0x9e3779b9) ^ 0x4d397817;
    let u = ((hash32(s) as f64 + 0.5) / 4294967296.) as f32;
    let v = ((hash32(s ^ 0xa73126bd) as f64 + 0.5) / 4294967296.) as f32;
    (-2. * u.max(f32::MIN_POSITIVE).ln()).sqrt() * (TAU * v).cos()
}
#[derive(Clone, Copy, Debug)]
enum Scene {
    Flat,
    ColourFlat,
    Oriented15,
    Oriented75,
    Colour,
    NearFar,
    Curved,
    Glint,
}
impl Scene {
    fn name(self) -> &'static str {
        match self {
            Self::Flat => "flat-neutral",
            Self::ColourFlat => "flat-colour",
            Self::Oriented15 => "single-direction15",
            Self::Oriented75 => "single-direction75",
            Self::Colour => "different-source-independent-colour",
            Self::NearFar => "near-fine-far-coarse",
            Self::Curved => "curved-boundary-crossing",
            Self::Glint => "glint-adjacent-thin-detail",
        }
    }
    fn flat(self) -> bool {
        matches!(self, Self::Flat | Self::ColourFlat)
    }
}
fn sigma(k: Option<usize>, focus: usize) -> f32 {
    0.65 + 1.25 * k.map_or(0., |j| (j as f32 - focus as f32).abs())
}
fn wave(f: f32, angle: f32, offset: f32, x: f32, y: f32, s: f32) -> f32 {
    (-0.5 * (TAU * f * s).powi(2)).exp()
        * (TAU * f * (angle.cos() * x + angle.sin() * y) + offset).cos()
}
fn component(which: usize, c: usize, x: f32, y: f32, k: Option<usize>) -> f32 {
    let (f, a, angle, offset, focus) = if which == 0 {
        (0.105, [0.045, 0.050, 0.040][c], 0.31, 0.43, 0)
    } else {
        (0.022, [0.090, 0.100, 0.085][c], 1.13, 0.81, 4)
    };
    a * wave(f, angle, offset, x, y, sigma(k, focus))
}
fn gauss(x: f32, y: f32, sx: f32, sy: f32) -> f32 {
    (-0.5 * ((x / sx).powi(2) + (y / sy).powi(2))).exp()
}
fn radiance(scene: Scene, c: usize, x: f32, y: f32, k: Option<usize>) -> f32 {
    match scene {
        Scene::Flat => 0.25,
        Scene::ColourFlat => [0.16, 0.25, 0.34][c],
        Scene::Oriented15 | Scene::Oriented75 => {
            let angle = if matches!(scene, Scene::Oriented15) {
                15.0f32
            } else {
                75.0f32
            }
            .to_radians();
            0.25 + 0.075 * wave(0.105, angle, 0.37, x, y, sigma(k, 2))
        }
        Scene::Colour => {
            let (amp, angle, focus) = match c {
                0 => (0.08, 0.27, 1),
                1 => (8. / RANGE, 1.23, 2),
                _ => (0.075, -0.78, 3),
            };
            0.25 + amp * wave(0.09, angle, 0.73 + 0.21 * c as f32, x, y, sigma(k, focus))
        }
        Scene::NearFar => 0.27 + component(0, c, x, y, k) + component(1, c, x, y, k),
        Scene::Curved => {
            // Independent two-layer blur/coverage fixture, not a pupil-visibility oracle.
            let sn = sigma(k, 4);
            let sf = sigma(k, 0);
            let far = 0.23 + 0.065 * wave(0.08, 1.4, 0.91, x, y, sf);
            let mut mass = 0.;
            let mut coverage = 0.;
            let mut premult = 0.;
            for (dx, dy) in [
                (-1., -1.),
                (0., -1.),
                (1., -1.),
                (-1., 0.),
                (0., 0.),
                (1., 0.),
                (-1., 1.),
                (0., 1.),
                (1., 1.),
            ] {
                let w = if dx == 0. && dy == 0. {
                    4.
                } else if dx == 0. || dy == 0. {
                    2.
                } else {
                    1.
                };
                let xx = x + dx * sn;
                let yy = y + dy * sn;
                mass += w;
                if (xx - 80.).powi(2) + (yy - 75.).powi(2) < 32.0f32.powi(2) {
                    let bright = 0.13 * (-0.5 * ((yy - 73.) / 1.2).powi(2)).exp();
                    let dark = 0.11 * (-0.5 * ((yy - 79.) / 1.2).powi(2)).exp();
                    coverage += w;
                    premult += w * ([0.31, 0.29, 0.27][c] + bright - dark);
                }
            }
            premult / mass + (1. - coverage / mass) * far
        }
        Scene::Glint => {
            let d = k.map_or(0., |j| j as f32);
            let sx = (1.5f32.powi(2) + (3. * d).powi(2)).sqrt();
            let sy = (1.5f32.powi(2) + (0.5 * d).powi(2)).sqrt();
            let glint =
                [0.60, 0.48, 0.34][c] * 2.25 / (sx * sy) * gauss(x - 59.3, y - 64.7, sx, sy);
            let s = sigma(k, 4);
            let width = (0.9f32.powi(2) + s * s).sqrt();
            let line = 0.08 * 0.9 / width * (-0.5 * ((y - 72.4) / width).powi(2)).exp();
            0.16 + glint + line + 0.025 * wave(0.035, 0.4, 0.2, x, y, s)
        }
    }
}
fn transforms() -> Vec<Similarity> {
    [
        (-0.46, 0.32),
        (0.37, -0.21),
        (0., 0.),
        (0.23, 0.44),
        (-0.18, -0.39),
    ]
    .iter()
    .enumerate()
    .map(|(k, &(x, y))| {
        let j = k as f64 - 2.;
        Similarity {
            a: Cx::new(1. + 0.0008 * j, 0.0004 * j),
            b: Cx::new(x / 2., y / 2.),
        }
    })
    .collect()
}
fn fixture(
    scene: Scene,
    k: usize,
    t: Similarity,
    iso: f32,
    noise: &NoiseModel,
    add_noise: bool,
) -> Frame {
    let active = Region {
        x: 7,
        y: 11,
        width: W,
        height: H,
    };
    let stride = W + 29;
    let height = H + 29;
    let mut frame = Frame {
        data: vec![64999; stride * height],
        stride,
        buffer_height: height,
        active,
        levels: levels(),
        iso: Some(iso),
        wb_coeffs: [GAIN[0], GAIN[1], GAIN[2], f32::NAN],
        xyz_to_cam_rgbe: [[1., 0., 0.], [0., 1., 0.], [0., 0., 1.], [0.; 3]],
        color_matrices: Vec::new(),
        camera: "ILCE-7CM2".into(),
        path: PathBuf::from(format!("nonexistent-dual-tree-{}-{k}.ARW", scene.name())),
    };
    assert!(!frame.path.exists());
    let det = t.a.re * t.a.re + t.a.im * t.a.im;
    for y in 0..H {
        for x in 0..W {
            let u = x as f64 - W as f64 / 2. - 2. * t.b.re;
            let v = y as f64 - H as f64 / 2. - 2. * t.b.im;
            let wx = W as f64 / 2. + (t.a.re * u + t.a.im * v) / det;
            let wy = H as f64 / 2. + (-t.a.im * u + t.a.re * v) / det;
            let signal =
                radiance(scene, ch(x, y), wx as f32, wy as f32, Some(k)) * RANGE / GAIN[ch(x, y)];
            let value = 512.
                + signal
                + if add_noise {
                    gaussian(x, y, k) * noise.sigma(phase(x, y), signal)
                } else {
                    0.
                };
            assert!(
                value > 512. && value < 15360.,
                "fixture clipping is not intended"
            );
            frame.data[(active.y + y) * stride + active.x + x] = value.round() as u16;
        }
    }
    frame
}
fn truth(scene: Scene) -> Vec<f32> {
    let c = crop();
    let mut out = Vec::new();
    for y in 2 * c.y..2 * (c.y + c.height) {
        for x in 2 * c.x..2 * (c.x + c.width) {
            for channel in 0..3 {
                out.push(radiance(scene, channel, x as f32, y as f32, None));
            }
        }
    }
    out
}
#[derive(Clone, Copy)]
struct Score {
    rgb: f32,
    green: f32,
    chroma: f32,
    recovery: [f32; 3],
    sd: [f32; 3],
}
fn score(values: &[f32], truth: &[f32]) -> Score {
    assert_eq!(values.len(), truth.len());
    let c = crop();
    let w = 2 * c.width;
    let h = 2 * c.height;
    let mut error = [0.; 3];
    let mut sums = [[0.; 4]; 3];
    let mut n = 0.;
    // Center before accumulating f32 moments; flat/weak-green variance must not
    // be manufactured by subtracting two large almost-equal raw second moments.
    let origin = 3 * (12 * w + 12);
    for y in 12..h - 12 {
        for x in 12..w - 12 {
            let i = 3 * (y * w + x);
            let mut e = [0.; 3];
            n += 1.;
            for channel in 0..3 {
                let a = truth[i + channel];
                let b = values[i + channel];
                assert!(b.is_finite());
                e[channel] = b - a;
                error[0] += e[channel] * e[channel];
                let da = a - truth[origin + channel];
                let db = b - values[origin + channel];
                for (v, z) in sums[channel].iter_mut().zip([da, db, da * da, da * db]) {
                    *v += z;
                }
            }
            error[1] += e[1] * e[1];
            error[2] += (e[0] - e[1]).powi(2) + (e[2] - e[1]).powi(2);
        }
    }
    let mut recovery = [0.; 3];
    let mut sd = [0.; 3];
    for channel in 0..3 {
        let [a, b, aa, ab] = sums[channel];
        let variance = (aa - a * a / n).max(0.);
        sd[channel] = (variance / n).sqrt();
        if variance > 1e-4 {
            recovery[channel] = (ab - a * b / n) / variance;
        }
    }
    Score {
        rgb: RANGE * (error[0] / (3. * n)).sqrt(),
        green: RANGE * (error[1] / n).sqrt(),
        chroma: RANGE * (error[2] / (2. * n)).sqrt(),
        recovery,
        sd,
    }
}
fn sj(s: Score) -> Value {
    json!({"rgb_rmse_dn":s.rgb,"green_rmse_dn":s.green,"chroma_rmse_dn":s.chroma,
    "channel_projection":s.recovery,"truth_sd_normalized":s.sd})
}
fn error_guard(b: Score, a: Score, flat: bool) -> bool {
    let offset = if flat { 0.5 } else { 1. };
    a.rgb <= 1.10 * b.rgb + offset
        && a.green <= 1.10 * b.green + offset
        && a.chroma <= 1.10 * b.chroma + offset
}
fn retention(b: Score, a: Score) -> bool {
    (0..3).all(|c| {
        b.sd[c] < 1e-3
            || b.recovery[c] < 0.5
            || (a.recovery[c] >= 0.95 * b.recovery[c].min(1.) && a.recovery[c] <= 1.10)
    })
}
fn two_components(rgb: &[f32]) -> [[f32; 3]; 2] {
    let c = crop();
    let w = 2 * c.width;
    let h = 2 * c.height;
    let mut answer = [[0.; 3]; 2];
    for channel in 0..3 {
        let mut sums = [0.; 8];
        let mut n = 0.;
        for y in 12..h - 12 {
            for x in 12..w - 12 {
                let a = component(0, channel, (x + 2 * c.x) as f32, (y + 2 * c.y) as f32, None);
                let b = component(1, channel, (x + 2 * c.x) as f32, (y + 2 * c.y) as f32, None);
                let v = rgb[3 * (y * w + x) + channel];
                n += 1.;
                for (s, z) in sums
                    .iter_mut()
                    .zip([a, b, v, a * a, b * b, a * b, a * v, b * v])
                {
                    *s += z;
                }
            }
        }
        let [a, b, v, aa, bb, ab, av, bv] = sums;
        let aa = aa - a * a / n;
        let bb = bb - b * b / n;
        let ab = ab - a * b / n;
        let av = av - a * v / n;
        let bv = bv - b * v / n;
        let det = aa * bb - ab * ab;
        assert!(det > 0.1 * aa * bb && aa > 1e-4 && bb > 1e-4);
        answer[0][channel] = (av * bb - bv * ab) / det;
        answer[1][channel] = (bv * aa - av * ab) / det;
    }
    answer
}
fn component_guard(b: [[f32; 3]; 2], a: [[f32; 3]; 2]) -> bool {
    (0..2).all(|k| {
        (0..3).all(|c| b[k][c] < 0.5 || (a[k][c] >= 0.95 * b[k][c].min(1.) && a[k][c] <= 1.10))
    })
}
fn errors(a: &[f32], b: &[f32]) -> (f32, f32) {
    assert_eq!(a.len(), b.len());
    let mut max = 0.0f32;
    let mut sum = 0.;
    for (&x, &y) in a.iter().zip(b) {
        assert!(x.is_finite() && y.is_finite());
        let e = (x - y).abs();
        max = max.max(e);
        sum += e * e;
    }
    (max, (sum / a.len() as f32).sqrt())
}
fn pr(a: &[f32], b: &[f32]) -> Value {
    let (max, rms) = errors(a, b);
    json!({"max_dn":max,"rms_dn":rms,"pass":max<=PR_MAX && rms<=PR_RMS})
}
fn plane_pr(a: &[Vec<f32>], b: &[Vec<f32>]) -> Value {
    assert_eq!(a.len(), 4);
    assert_eq!(b.len(), 4);
    Value::Array(a.iter().zip(b).map(|(x, y)| pr(x, y)).collect())
}
fn all_pr(v: &Value) -> bool {
    v.as_array().unwrap().iter().all(|r| r["pass"] == true)
}
fn mechanics(out: &Path) -> Result<Value> {
    let mut records = Vec::new();
    let mut all = true;
    for (w, h) in [(64, 56), (65, 57)] {
        let plan = Plan::new(w, h)?;
        ensure!(plan.levels == 7);
        let mut x = vec![0.; w * h];
        for y in 0..h {
            for i in 0..w {
                x[y * w + i] =
                    12000. + 9000. * (0.37 * i as f32 + 0.19 * y as f32).sin() + 23. * y as f32;
            }
        }
        x[0] = -53.;
        x[w - 1] = 64000.;
        x[(h - 1) * w] = 53123.;
        x[w * h - 1] = -21.;
        x[(h / 2) * w + w / 2] = 62000.;
        let before = sha(&x.iter().flat_map(|v| v.to_le_bytes()).collect::<Vec<_>>());
        let coeff = forward_phase(&x, &plan)?;
        let back = inverse_phase(&coeff, &plan)?;
        let roundtrip = pr(&x, &back);
        all &= roundtrip["pass"] == true;
        let mut foil = forward_phase(&x, &plan)?;
        for band in &mut foil.bands {
            for z in &mut band.values {
                z.im = -z.im;
            }
        }
        let bad_phase = inverse_phase(&foil, &plan)?;
        let phase_error = errors(&x, &bad_phase);
        let phase_rejected = phase_error.1 > PR_RMS && phase_error.0 > PR_MAX;
        let mut swapped = forward_phase(&x, &plan)?;
        let (left, right) = swapped.bands.split_at_mut(4);
        std::mem::swap(&mut left[0].values, &mut right[0].values);
        let bad_direction = inverse_phase(&swapped, &plan)?;
        let direction_error = errors(&x, &bad_direction);
        let direction_rejected = direction_error.1 > PR_RMS;
        let mut scaled = forward_phase(&x, &plan)?;
        for low in &mut scaled.low {
            for v in low {
                *v *= 2.;
            }
        }
        let bad_scale = inverse_phase(&scaled, &plan)?;
        let scale_error = errors(&x, &bad_scale);
        let scale_rejected = scale_error.1 > PR_RMS;
        let unchanged = before == sha(&x.iter().flat_map(|v| v.to_le_bytes()).collect::<Vec<_>>());
        all &= phase_rejected && direction_rejected && scale_rejected && unchanged;
        records.push(json!({"input_dimensions":[w,h],"padded_dimensions":[plan.padded_width,plan.padded_height],
            "input_sha256":before,"input_unchanged":unchanged,"roundtrip_pre_hull":roundtrip,
            "one_sided_conjugation_error":phase_error,"one_sided_phase_rejected":phase_rejected,
            "one_sided_LH_plus_HH_plus_swap_error":direction_error,"direction_foil_rejected":direction_rejected,
            "lowpass_gain2_error":scale_error,"scale_foil_rejected":scale_rejected}));
    }
    let plan = Plan::new(128, 128)?;
    let mut directional = Vec::new();
    let mut winners = Vec::new();
    for degrees in [-75.0f32, -45., -15., 15., 45., 75.] {
        let angle = degrees.to_radians();
        let x = (0..128 * 128)
            .map(|i| {
                1000.
                    * (TAU
                        * 0.18
                        * (angle.cos() * (i % 128) as f32 + angle.sin() * (i / 128) as f32)
                        + 0.31)
                        .cos()
            })
            .collect::<Vec<_>>();
        let coeff = forward_phase(&x, &plan)?;
        let mut energy = [0.; 6];
        for band in &coeff.bands {
            if band.level == 1 {
                ensure!(band.direction < 6 && band.width >= 20 && band.height >= 20);
                for y in 12..20 {
                    for x in 12..20 {
                        let z = &band.values[y * band.width + x];
                        energy[band.direction] += z.re * z.re + z.im * z.im;
                    }
                }
            }
        }
        let mut order = (0..6).collect::<Vec<_>>();
        order.sort_by(|&a, &b| energy[b].total_cmp(&energy[a]));
        let margin = energy[order[0]] / energy[order[1]].max(f32::MIN_POSITIVE);
        winners.push(order[0]);
        directional.push(json!({"wavevector_degrees":degrees,"phase_radians":0.31,"cycles_per_phase_pixel":0.18,
            "level_zero_based":1,"coefficient_roi_xyxy":[12,12,20,20],"energy":energy,"peak_band":order[0],"peak_margin":margin}));
    }
    winners.sort_unstable();
    winners.dedup();
    let angular_pass = winners.len() == 6
        && directional
            .iter()
            .all(|r| r["peak_margin"].as_f64().unwrap() >= 1.05);
    all &= angular_pass;
    let result = json!({"status":"TRANSFORM_MECHANICS_OBSERVED","pass":all,"max_dn_bound":PR_MAX,"rms_dn_bound":PR_RMS,
        "signed_roundtrips":records,"directional_commission":directional,"six_distinct_directions_pass":angular_pass,
        "no_hull_or_exact_copy_shortcut":true});
    save_json(&out.join("mechanics.json"), &result)?;
    Ok(result)
}
fn score_destroyers(out: &Path) -> Result<Value> {
    let t = truth(Scene::Flat);
    let mut noise = t.clone();
    for (i, v) in noise.iter_mut().enumerate() {
        *v += 0.03
            * gaussian(
                i / 3 % (2 * crop().width),
                i / 3 / (2 * crop().width),
                i % 3,
            );
    }
    let flat_rejected = !error_guard(score(&t, &t), score(&noise, &t), true);
    let t2 = truth(Scene::NearFar);
    let c = crop();
    let w = 2 * c.width;
    let mut erased = t2.clone();
    let mut over = t2.clone();
    for y in 0..2 * c.height {
        for x in 0..w {
            for channel in 0..3 {
                let p = 3 * (y * w + x) + channel;
                erased[p] -=
                    component(1, channel, (x + 2 * c.x) as f32, (y + 2 * c.y) as f32, None);
                over[p] +=
                    0.5 * component(0, channel, (x + 2 * c.x) as f32, (y + 2 * c.y) as f32, None);
            }
        }
    }
    let b = two_components(&t2);
    let erased_rejected = !component_guard(b, two_components(&erased));
    let over_rejected = !component_guard(b, two_components(&over));
    let colour = truth(Scene::Colour);
    let mut false_green = colour.clone();
    for p in false_green.chunks_exact_mut(3) {
        p[1] += 0.04;
    }
    let green_rejected = !error_guard(score(&colour, &colour), score(&false_green, &colour), false);
    let panels = json!({"added_flat_noise":image(out,"destroyer-added-flat-noise",&noise,w,2*c.height)?,
        "erased_far_coarse":image(out,"destroyer-erased-far-coarse",&erased,w,2*c.height)?,
        "overcontrasted_near":image(out,"destroyer-overcontrasted-near",&over,w,2*c.height)?,
        "false_green":image(out,"destroyer-false-green",&false_green,w,2*c.height)?});
    Ok(
        json!({"pass":flat_rejected && erased_rejected && over_rejected && green_rejected,
        "flat_noise_rejected":flat_rejected,"erased_coarse_rejected":erased_rejected,
        "overcontrast_rejected":over_rejected,"false_green_rejected":green_rejected,"panels":panels}),
    )
}
fn frame_binding(out: &Path, frame: &Frame, k: usize) -> Result<Value> {
    let mut active = Vec::new();
    for y in 0..H {
        for x in 0..W {
            active.extend_from_slice(
                &frame.data[(frame.active.y + y) * frame.stride + frame.active.x + x].to_le_bytes(),
            );
        }
    }
    let original = bytes_file(&out.join(format!("original-{k}.u16")), &active)?;
    let full = frame
        .data
        .iter()
        .flat_map(|x| x.to_le_bytes())
        .collect::<Vec<_>>();
    Ok(
        json!({"original_active":original,"dimensions":[W,H],"full_storage_sha256":sha(&full),
        "active_origin":[frame.active.x,frame.active.y],"stride":frame.stride,"padding_sentinel":64999}),
    )
}
fn run() -> Result<()> {
    let out = PathBuf::from(
        std::env::var_os("STREHL_DUAL_TREE_CFA_CONTROL_OUT").context("missing control output")?,
    );
    ensure!(!out.exists(), "fresh immutable output required");
    std::fs::create_dir_all(&out)?;
    let mut records = Vec::new();
    let mut quality = true;
    let mechanical = mechanics(&out)?;
    let destroyers = score_destroyers(&out)?;
    save_json(&out.join("guard-destroyers.json"), &destroyers)?;
    let mut mechanical_pass = mechanical["pass"] == true && destroyers["pass"] == true;
    if !mechanical_pass {
        save_json(
            &out.join("screen.json"),
            &json!({"status":"MECHANICAL_REFUSAL","all_cases_completed":false,
            "mechanical_pass":false,"quality_pass":false,"admission":false,"photographic_admission":false,
            "mechanics":mechanical,"guard_destroyers":destroyers,"cases":records}),
        )?;
        anyhow::bail!("fixed transform or score mechanics refused; observations saved");
    }
    let ts = transforms();
    let cfg = MergeConfig::default();
    // Flats are the first actual gather/fold cases. Singleton nulls follow the eight cases.
    for scene in [
        Scene::Flat,
        Scene::ColourFlat,
        Scene::Oriented15,
        Scene::Oriented75,
        Scene::Colour,
        Scene::NearFar,
        Scene::Curved,
        Scene::Glint,
    ] {
        let iso = if matches!(scene, Scene::ColourFlat) {
            400.
        } else {
            100.
        };
        let noise = profile::noise_model_for("ILCE-7CM2", Some(iso), levels());
        let frames = ts
            .iter()
            .enumerate()
            .map(|(k, &t)| fixture(scene, k, t, iso, &noise, true))
            .collect::<Vec<_>>();
        let dir = out.join(scene.name());
        std::fs::create_dir(&dir)?;
        let mut sources = Vec::new();
        for (k, f) in frames.iter().enumerate() {
            sources.push(frame_binding(&dir, f, k)?);
        }
        let comparison = compare_generated(&frames, &ts, crop(), &noise, cfg.clone())?;
        let c = crop();
        ensure!(comparison.native_width == 2 * c.width && comparison.native_height == 2 * c.height);
        let uniform_pr = plane_pr(&comparison.uniform.planes4, &comparison.mean_planes4);
        mechanical_pass &= all_pr(&uniform_pr);
        let truth = truth(scene);
        let b = score(&comparison.canonical.rgb, &truth);
        let a = score(&comparison.candidate.rgb, &truth);
        let errors_pass = error_guard(b, a, scene.flat());
        let channel_pass = scene.flat() || retention(b, a);
        let components = if matches!(scene, Scene::NearFar) {
            let bp = two_components(&comparison.canonical.rgb);
            let ap = two_components(&comparison.candidate.rgb);
            json!({"baseline":bp,"candidate":ap,"pass":component_guard(bp,ap)})
        } else {
            json!({"pass":true,"applicable":false})
        };
        let case_quality = errors_pass && channel_pass && components["pass"] == true;
        quality &= case_quality;
        let mut panels = serde_json::Map::new();
        for (name, rgb) in [
            ("truth", &truth),
            ("canonical", &comparison.canonical.rgb),
            ("candidate", &comparison.candidate.rgb),
            ("uniform", &comparison.uniform.rgb),
            ("gathered-source0", &comparison.gathered_source0.rgb),
        ] {
            panels.insert(
                name.into(),
                image(&dir, name, rgb, 2 * c.width, 2 * c.height)?,
            );
        }
        let unchanged = frames.iter().zip(&sources).all(|(f, r)| {
            sha(&f
                .data
                .iter()
                .flat_map(|x| x.to_le_bytes())
                .collect::<Vec<_>>())
                == r["full_storage_sha256"].as_str().unwrap()
        });
        mechanical_pass &= unchanged;
        let record = json!({"scene":scene.name(),"iso":iso,"noise_model":format!("{noise:?}"),"source_count":N,
            "originals":sources,"input_storage_unchanged":unchanged,"canonical":sj(b),"candidate":sj(a),
            "uniform":sj(score(&comparison.uniform.rgb,&truth)),"gathered_source0":sj(score(&comparison.gathered_source0.rgb,&truth)),
            "error_guard":errors_pass,"channel_retention_guard":channel_pass,"components":components,
            "quality_pass":case_quality,"uniform_actual_transform_vs_gathered_mean":uniform_pr,
            "consumer_evidence":comparison.evidence,"panels":panels});
        save_json(&dir.join("case.json"), &record)?;
        records.push(record);
        if !mechanical_pass {
            break;
        }
    }
    let mut singleton = Value::Null;
    if mechanical_pass {
        let noise = profile::noise_model_for("ILCE-7CM2", Some(100.), levels());
        let mut rows = Vec::new();
        for (scene, k) in [(Scene::ColourFlat, 2), (Scene::Colour, 0)] {
            let t = ts[k];
            let frame = fixture(scene, k, t, 100., &noise, false);
            let dir = out.join(format!("singleton-{}", scene.name()));
            std::fs::create_dir(&dir)?;
            let original = frame_binding(&dir, &frame, k)?;
            let one = compare_generated(&[frame], &[t], crop(), &noise, cfg.clone())?;
            let candidate_pr = plane_pr(&one.pre_hull_planes4, &one.gathered_source0.planes4);
            let uniform_pr = plane_pr(&one.uniform.planes4, &one.gathered_source0.planes4);
            mechanical_pass &= all_pr(&candidate_pr) && all_pr(&uniform_pr);
            let fallback = one.evidence["candidate"]["fallback_coefficients"]
                .as_array()
                .context("fallback receipt")?;
            let fallback_exercised = fallback.iter().any(|n| n.as_u64().unwrap_or(0) > 0);
            if scene.flat() {
                mechanical_pass &= fallback_exercised;
            }
            let panels = json!({"candidate":image(&dir,"candidate",&one.candidate.rgb,2*crop().width,2*crop().height)?,
                "gathered_source0":image(&dir,"gathered-source0",&one.gathered_source0.rgb,2*crop().width,2*crop().height)?});
            rows.push(json!({"scene":scene.name(),"source_index":k,"original":original,
                "input":"one source without acquisition noise; profile still injected",
                "pre_hull_vs_actual_gather":candidate_pr,"uniform_vs_actual_gather":uniform_pr,
                "fallback_exercised":fallback_exercised,"consumer_evidence":one.evidence,"panels":panels}));
        }
        singleton = json!({"rows":rows,"zero_evidence_interpretation":"constant singleton must exercise at least one actual mean fallback coefficient; structured fractional singleton separately exercises selected AC reconstruction"});
        save_json(&out.join("singleton.json"), &singleton)?;
    }
    let complete = records.len() == 8 && !singleton.is_null();
    let screen = json!({"status":if complete {"COMPLETE_DUAL_TREE_GENERATED_DIAGNOSTIC"} else {"MECHANICAL_REFUSAL"},
        "all_cases_completed":complete,"mechanical_pass":mechanical_pass,"quality_pass":quality && complete,
        "admission":false,"photographic_admission":false,"RAW_reads":0,"mechanics":mechanical,
        "guard_destroyers":destroyers,"singleton":singleton,"cases":records,
        "protocol":{"cfg":format!("{cfg:?}"),"original_dimensions":[W,H],"crop_quad_xywh":[8,8,64,56],
            "fixed_seven_candidate_levels":true,"geometry":ts.iter().map(|t|json!([t.a.re,t.a.im,t.b.re,t.b.im])).collect::<Vec<_>>(),
            "generated_basis_only_comparison":false,"baseline_level_disclosure":"each consumer_evidence records actual canonical level sizes/exponents and seven candidate exponents; tiny fixtures do not isolate representation from scale count",
            "white_balance_rgb":GAIN,"max_dn_roundtrip":PR_MAX,"rms_dn_roundtrip":PR_RMS,
            "error_guard":"eachRGB/G/chroma<=1.10canonical+0.5DNflat/1DNstructure",
            "component_guard":"eligiblecanonical>=.5; candidate>=.95min(canonical,1) and<=1.10truth",
            "quality_failure_stops_photo":false,"mechanical_failure_stops_photo":true,
            "truth_scope":"independent analytic visible radiance; curved coverage is simplified, not pupil physics"}});
    save_json(&out.join("screen.json"), &screen)?;
    ensure!(
        mechanical_pass && complete,
        "mechanical refusal; complete diagnostic receipt retained"
    );
    Ok(())
}

#[test]
#[ignore]
fn generated_controls() {
    run().unwrap();
}
