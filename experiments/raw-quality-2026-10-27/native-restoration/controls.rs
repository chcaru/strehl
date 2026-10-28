// Independent fixed fixtures/guards. Root alone executes; quality failure is retained.
use super::*;
use serde::Deserialize;
use std::{
    f32::consts::TAU,
    fs::OpenOptions,
    io::Write,
    path::{Path, PathBuf},
};
use strehl_core::{
    CfaPlane,
    noise::{NoiseModel, PlaneNoise, Provenance},
};

const W: usize = 128;
const Q: usize = W / 2;
const RANGE: f32 = 14848.;
const PHASES: [CfaPlane; 4] = [CfaPlane::R, CfaPlane::G1, CfaPlane::G2, CfaPlane::B];
fn levels() -> Levels {
    Levels {
        black: 512.,
        white: 15360.,
    }
}
#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct Config {
    schema: u32,
    out_dir: PathBuf,
    expected_test_executable_sha256: String,
}
#[derive(Clone, Copy, Debug)]
enum Scene {
    Flat,
    ColourFlat,
    SharpStep,
    BlurredLines,
    Glints,
    Colour,
    NearFar,
    Asymmetric,
}
impl Scene {
    fn name(self) -> &'static str {
        match self {
            Self::Flat => "flat-neutral",
            Self::ColourFlat => "flat-colour",
            Self::SharpStep => "sharp-step",
            Self::BlurredLines => "blurred-step-close-lines",
            Self::Glints => "neutral-colour-glints",
            Self::Colour => "independent-colour",
            Self::NearFar => "near-fine-far-coarse",
            Self::Asymmetric => "asymmetric-mismatch",
        }
    }
    fn flat(self) -> bool {
        matches!(self, Self::Flat | Self::ColourFlat)
    }
}
fn component(scene: Scene, k: usize, ch: usize, x: f32, y: f32) -> f32 {
    match scene {
        Scene::Colour => {
            if k == 0 {
                [700., 0., 0.][ch] * (TAU * (22. * x + 6. * y) / W as f32 + 0.31).cos()
            } else {
                [0., 8., 600.][ch] * (TAU * (-10. * x + 18. * y) / W as f32 + 0.79).cos()
            }
        }
        Scene::NearFar => {
            if k == 0 {
                [450., 500., 400.][ch] * (TAU * (14. * x + 4. * y) / W as f32 + 0.43).cos()
            } else {
                [650., 550., 700.][ch] * (TAU * 3. * y / W as f32 + 0.17).cos()
            }
        }
        _ => 0.,
    }
}
fn truth(scene: Scene, ch: usize, x: f32, y: f32) -> f32 {
    match scene {
        Scene::Flat => 3000.,
        Scene::ColourFlat => [1800., 3000., 4200.][ch],
        Scene::SharpStep => {
            if x >= 64. {
                6000.
            } else {
                2000.
            }
        }
        Scene::BlurredLines | Scene::Asymmetric => {
            if y < 56. {
                if x >= 64. { 6000. } else { 2000. }
            } else {
                let bright = (26.0..29.0).contains(&x)
                    || (32.0..35.0).contains(&x)
                    || (59.0..60.0).contains(&x);
                let dark = (84.0..87.0).contains(&x)
                    || (90.0..93.0).contains(&x)
                    || (69.0..70.0).contains(&x);
                3500.
                    + if bright {
                        1500.
                    } else if dark {
                        -1500.
                    } else {
                        0.
                    }
            }
        }
        Scene::Glints => {
            let g = |cx: f32, cy: f32, s: f32| {
                (-((x - cx).powi(2) + (y - cy).powi(2)) / (2. * s * s)).exp()
            };
            1500.
                + 9000. * g(38.3, 38.7, 1.15)
                + [10000., 2400., 500.][ch] * g(90.1, 40.4, 1.4)
                + [400., 2500., 10500.][ch] * g(63.2, 90.6, 1.0)
        }
        Scene::Colour | Scene::NearFar => {
            3000. + component(scene, 0, ch, x, y) + component(scene, 1, ch, x, y)
        }
    }
}
// Independent input blur: full-native Gaussian quadrature, not the candidate's
// two-native-pixel binomial. This is a synthetic appearance plant, not optics.
fn input(scene: Scene, ch: usize, x: f32, y: f32) -> f32 {
    match scene {
        Scene::BlurredLines => {
            let mut sum = 0.;
            let mut weight = 0.;
            for dy in -3..=3 {
                for dx in -3..=3 {
                    let a = (-((dx * dx + dy * dy) as f32) / (2. * 0.9f32.powi(2))).exp();
                    sum += a * truth(scene, ch, x + dx as f32, y + dy as f32);
                    weight += a;
                }
            }
            sum / weight
        }
        Scene::Asymmetric => {
            0.15 * truth(scene, ch, x - 1., y)
                + 0.55 * truth(scene, ch, x, y)
                + 0.30 * truth(scene, ch, x + 1., y)
        }
        Scene::NearFar => {
            3000. + 0.80 * component(scene, 0, ch, x, y) + component(scene, 1, ch, x, y)
        }
        _ => truth(scene, ch, x, y),
    }
}
fn hash32(mut x: u32) -> u32 {
    x ^= x >> 16;
    x = x.wrapping_mul(0x7feb352d);
    x ^= x >> 15;
    x = x.wrapping_mul(0x846ca68b);
    x ^ (x >> 16)
}
fn gaussian(i: usize, k: usize) -> f32 {
    let s = (i as u32) ^ (k as u32).wrapping_mul(0x9e3779b9) ^ 0x6d419e23;
    let u = (hash32(s) as f64 + 0.5) / 4294967296.;
    let v = (hash32(s ^ 0xa73126bd) as f64 + 0.5) / 4294967296.;
    ((-2. * u.ln()).sqrt() * (std::f64::consts::TAU * v).cos()) as f32
}
fn noise() -> NoiseModel {
    let shot = [0.15f32, 0.13, 0.17, 0.21];
    let read = [9.0f32, 8., 11., 13.];
    NoiseModel::new(
        std::array::from_fn(|p| PlaneNoise {
            gain_dn_per_e: shot[p],
            read_noise_e: read[p].sqrt() / shot[p],
            levels: levels(),
        }),
        100.,
        Provenance::Fallback,
    )
}
fn packed(scene: Scene, k: usize, model: &NoiseModel) -> (Vec<Vec<f32>>, Vec<u16>) {
    let mut p = vec![vec![0.; Q * Q]; 4];
    let mut raw = vec![0u16; W * W];
    for y in 0..W {
        for x in 0..W {
            let phase = 2 * (y % 2) + x % 2;
            let ch = [0, 1, 1, 2][phase];
            let s = input(scene, ch, x as f32, y as f32);
            let n = if scene.flat() {
                model.sigma(PHASES[phase], s) * gaussian(y * W + x, k)
            } else {
                0.
            };
            let code = (s + n + 512.).round().clamp(0., 16383.) as u16;
            raw[y * W + x] = code;
            p[phase][(y / 2) * Q + x / 2] = code as f32 - 512.;
        }
    }
    (p, raw)
}
fn physical_truth(scene: Scene) -> Vec<f32> {
    let mut out = vec![0.; W * W * 3];
    for y in 0..W {
        for x in 0..W {
            for c in 0..3 {
                out[(y * W + x) * 3 + c] = truth(scene, c, x as f32, y as f32);
            }
        }
    }
    out
}
fn develop(p: &[Vec<f32>]) -> Result<Vec<f32>> {
    let mut rgb = camera_rgb(p, Q, Q, levels(), [1.; 4])?;
    ensure!(
        rgb.len() == W * W * 3 && rgb.iter().all(|x| x.is_finite()),
        "complete finite actual MHC"
    );
    for x in &mut rgb {
        *x *= RANGE;
    }
    Ok(rgb)
}
fn same(a: &[Vec<f32>], b: &[Vec<f32>]) -> bool {
    a.len() == b.len()
        && a.iter().zip(b).all(|(a, b)| {
            a.len() == b.len() && a.iter().zip(b).all(|(a, b)| a.to_bits() == b.to_bits())
        })
}
fn range_ok(src: &[Vec<f32>], out: &[Vec<f32>]) -> bool {
    // Independent range enumeration: reflection adds no new value to this
    // valid-neighbor set, including every boundary and corner.
    (0..4).all(|p| {
        (0..Q).all(|y| {
            (0..Q).all(|x| {
                let mut lo = f32::INFINITY;
                let mut hi = f32::NEG_INFINITY;
                for yy in y.saturating_sub(1)..=(y + 1).min(Q - 1) {
                    for xx in x.saturating_sub(1)..=(x + 1).min(Q - 1) {
                        lo = lo.min(src[p][yy * Q + xx]);
                        hi = hi.max(src[p][yy * Q + xx]);
                    }
                }
                out[p][y * Q + x] >= lo && out[p][y * Q + x] <= hi
            })
        })
    })
}
#[derive(Clone, Copy)]
struct Score {
    rgb: f64,
    green: f64,
    chroma: f64,
}
fn score(a: &[f32], t: &[f32]) -> Score {
    let (mut rgb, mut green, mut chroma, mut n) = (0., 0., 0., 0.);
    for y in 8..W - 8 {
        for x in 8..W - 8 {
            let i = (y * W + x) * 3;
            let e: [f64; 3] = std::array::from_fn(|c| (a[i + c] - t[i + c]) as f64);
            rgb += e.iter().map(|v| v * v).sum::<f64>();
            green += e[1] * e[1];
            chroma += (e[0] - e[1]).powi(2) + (e[2] - e[1]).powi(2);
            n += 1.;
        }
    }
    Score {
        rgb: (rgb / (3. * n)).sqrt(),
        green: (green / n).sqrt(),
        chroma: (chroma / (2. * n)).sqrt(),
    }
}
fn error_guard(base: Score, arm: Score, flat: bool) -> bool {
    let floor = if flat { 0.5 } else { 1.0 };
    arm.rgb <= 1.10 * base.rgb + floor
        && arm.green <= 1.10 * base.green + floor
        && arm.chroma <= 1.10 * base.chroma + floor
}
fn score_json(s: Score) -> Value {
    json!({"rgb_rmse_dn":s.rgb,"green_rmse_dn":s.green,"chroma_rmse_dn":s.chroma})
}
fn recovery(scene: Scene, rgb: &[f32]) -> Vec<f64> {
    if !matches!(scene, Scene::Colour | Scene::NearFar) {
        return Vec::new();
    }
    let (mut g00, mut g01, mut g11, mut b0, mut b1) = (0., 0., 0., 0., 0.);
    for y in 0..W {
        for x in 0..W {
            for c in 0..3 {
                let a = component(scene, 0, c, x as f32, y as f32) as f64;
                let b = component(scene, 1, c, x as f32, y as f32) as f64;
                let v = (rgb[(y * W + x) * 3 + c] - 3000.) as f64;
                g00 += a * a;
                g01 += a * b;
                g11 += b * b;
                b0 += a * v;
                b1 += b * v;
            }
        }
    }
    let det = g00 * g11 - g01 * g01;
    assert!(det > 1.);
    vec![(b0 * g11 - b1 * g01) / det, (b1 * g00 - b0 * g01) / det]
}
fn component_guard(base: &[f64], arm: &[f64]) -> bool {
    base.len() == arm.len()
        && base
            .iter()
            .zip(arm)
            .all(|(b, a)| *b >= 0.25 && *a >= 0.95 * b && *a <= 1.10)
}
fn record(path: &Path) -> Result<Value> {
    Ok(json!({"path":path,"bytes":std::fs::metadata(path)?.len(),"sha256":replay::sha(path)?}))
}
fn write_bytes(path: &Path, bytes: &[u8]) -> Result<Value> {
    OpenOptions::new()
        .write(true)
        .create_new(true)
        .open(path)?
        .write_all(bytes)?;
    record(path)
}
fn panel(out: &Path, name: &str, rgb: &[f32]) -> Result<Value> {
    ensure!(
        rgb.len() == W * W * 3 && rgb.iter().all(|x| x.is_finite()),
        "finite complete panel"
    );
    let master = write_bytes(
        &out.join(format!("{name}.f32")),
        &rgb.iter().flat_map(|v| v.to_le_bytes()).collect::<Vec<_>>(),
    )?;
    let mut ppm = format!("P6\n{W} {W}\n255\n").into_bytes();
    for v in rgb {
        let x = (*v / RANGE).clamp(0., 1.);
        let y = if x <= 0.0031308 {
            12.92 * x
        } else {
            1.055 * x.powf(1. / 2.4) - 0.055
        };
        ppm.push((255. * y).round() as u8);
    }
    let preview = write_bytes(&out.join(format!("{name}.ppm")), &ppm)?;
    Ok(
        json!({"master":master,"preview":preview,"width":W,"height":W,"units":"camera-linear RGB DN f32 LE","display":"fixed DN/14848 then sRGB curve; camera channels, no color calibration; complete unresized"}),
    )
}
pub(super) fn run() -> Result<()> {
    let config_path = PathBuf::from(
        std::env::var_os("STREHL_NATIVE_RESTORATION_CONFIG").context("config required")?,
    );
    let cfg: Config = serde_json::from_slice(&std::fs::read(&config_path)?)?;
    ensure!(
        cfg.schema == 1
            && replay::sha(&std::env::current_exe()?)? == cfg.expected_test_executable_sha256,
        "config/build binding"
    );
    let root = Path::new(env!("CARGO_MANIFEST_DIR"))
        .join("../..")
        .canonicalize()?;
    ensure!(
        cfg.out_dir.is_absolute()
            && !cfg.out_dir.exists()
            && cfg
                .out_dir
                .parent()
                .context("output parent")?
                .canonicalize()?
                .starts_with(root.join("outputs").canonicalize()?),
        "fresh bounded output"
    );
    std::fs::create_dir(&cfg.out_dir)?;
    let model = noise();
    let mut hard = true;
    let mut cases = Vec::new();
    // Mechanical nulls include unequal phase DC and signed finite samples.
    let dc = vec![
        vec![1800.; Q * Q],
        vec![2800.; Q * Q],
        vec![3000.; Q * Q],
        vec![4200.; Q * Q],
    ];
    let dc_exact = same(&dc, &apply(&dc, Q, Q, Correction::Bounded)?);
    let mut signed = dc.clone();
    signed[0][0] = -17.25;
    signed[3][Q * Q - 1] = 16001.5;
    let signed_off_exact = same(&signed, &apply(&signed, Q, Q, Correction::Off)?);
    let mut nan = dc.clone();
    nan[1][Q + 2] = f32::NAN;
    let nonfinite_rejected = apply(&nan, Q, Q, Correction::Bounded).is_err();
    hard &= dc_exact && signed_off_exact && nonfinite_rejected;
    // Commission the SAME error/component guards before the real cases.
    let t = physical_truth(Scene::NearFar);
    let zero = score(&t, &t);
    let mut wrong = t.clone();
    for i in (1..wrong.len()).step_by(3) {
        wrong[i] += 100.;
    }
    let false_green_rejected = !error_guard(zero, score(&wrong, &t), false);
    let mut erased = t.clone();
    for y in 0..W {
        for x in 0..W {
            for c in 0..3 {
                erased[(y * W + x) * 3 + c] -= component(Scene::NearFar, 1, c, x as f32, y as f32);
            }
        }
    }
    let erased_coarse_rejected = !component_guard(
        &recovery(Scene::NearFar, &t),
        &recovery(Scene::NearFar, &erased),
    );
    let mut bad_range = dc.clone();
    bad_range[0][Q + 1] += 1.;
    let wrong_range_rejected = !range_ok(&dc, &bad_range);
    hard &= false_green_rejected && erased_coarse_rejected && wrong_range_rejected;
    let mut commission = json!({"dc_exact":dc_exact,"signed_off_exact":signed_off_exact,"nonfinite_rejected":nonfinite_rejected,
        "false_green_rejected":false_green_rejected,"erased_coarse_rejected":erased_coarse_rejected,"wrong_range_rejected":wrong_range_rejected});
    let destroys = cfg.out_dir.join("guard-destroyers");
    std::fs::create_dir(&destroys)?;
    commission["panels"] = json!({"truth":panel(&destroys,"truth",&t)?,"false_green":panel(&destroys,"false-green",&wrong)?,"erased_coarse":panel(&destroys,"erased-coarse",&erased)?});
    replay::save(&cfg.out_dir.join("commission.json"), &commission)?;
    for (k, scene) in [
        Scene::Flat,
        Scene::ColourFlat,
        Scene::SharpStep,
        Scene::BlurredLines,
        Scene::Glints,
        Scene::Colour,
        Scene::NearFar,
        Scene::Asymmetric,
    ]
    .into_iter()
    .enumerate()
    {
        let dest = cfg.out_dir.join(scene.name());
        std::fs::create_dir(&dest)?;
        let (src, raw) = packed(scene, k, &model);
        let before = src.clone();
        let off = apply(&src, Q, Q, Correction::Off)?;
        let bounded = apply(&src, Q, Q, Correction::Bounded)?;
        let unbounded = apply(&src, Q, Q, Correction::Unbounded)?;
        let no_op = same(&src, &off);
        let unchanged = same(&src, &before);
        let local_range = range_ok(&src, &bounded);
        let base_rgb = develop(&src)?;
        let off_rgb = develop(&off)?;
        let b_rgb = develop(&bounded)?;
        let u_rgb = develop(&unbounded)?;
        let actual_no_op = base_rgb
            .iter()
            .zip(&off_rgb)
            .all(|(a, b)| a.to_bits() == b.to_bits());
        let truth_rgb = physical_truth(scene);
        let base_score = score(&base_rgb, &truth_rgb);
        let b_score = score(&b_rgb, &truth_rgb);
        let u_score = score(&u_rgb, &truth_rgb);
        let rb = recovery(scene, &base_rgb);
        let rc = recovery(scene, &b_rgb);
        let ru = recovery(scene, &u_rgb);
        let mut sharp_step = Value::Null;
        if matches!(scene, Scene::SharpStep) {
            let bounded_exact = same(&src, &bounded);
            let mut analytic_exact = true;
            for p in 0..4 {
                for y in 2..Q - 2 {
                    for x in 2..Q - 2 {
                        let expected = if x == Q / 2 - 2 || x == Q / 2 - 1 {
                            1500.
                        } else if x == Q / 2 || x == Q / 2 + 1 {
                            6500.
                        } else {
                            src[p][y * Q + x]
                        };
                        analytic_exact &= unbounded[p][y * Q + x].to_bits() == expected.to_bits();
                    }
                }
            }
            let changed = base_rgb
                .iter()
                .zip(&u_rgb)
                .any(|(a, b)| a.to_bits() != b.to_bits());
            let foil_guard_rejected = !error_guard(base_score, u_score, false);
            hard &= bounded_exact && analytic_exact && changed && foil_guard_rejected;
            sharp_step = json!({"bounded_cfa_exact":bounded_exact,"unbounded_analytic_exact":analytic_exact,"step_dn":4000.,"excursion_dn":500.,"fraction":0.125,"unbounded_actual_MHC_changed":changed,"unbounded_error_guard_rejected":foil_guard_rejected});
        }
        let errors_pass = error_guard(base_score, b_score, scene.flat());
        let components_pass = component_guard(&rb, &rc);
        hard &= no_op && unchanged && local_range && actual_no_op;
        let mut row = json!({"case":scene.name(),"no_op_cfa_exact":no_op,"no_op_MHC_exact":actual_no_op,"inputs_unchanged":unchanged,"bounded_local_range":local_range,"sharp_step":sharp_step,
            "baseline_score":score_json(base_score),"bounded_score":score_json(b_score),"unbounded_score":score_json(u_score),"error_guard_pass":errors_pass,"component_guard_pass":components_pass,
            "baseline_component_recovery":rb,"bounded_component_recovery":rc,"unbounded_component_recovery":ru,"quality_pass":errors_pass&&components_pass,"admission":false});
        row["original_u16"] = write_bytes(
            &dest.join("original-cfa.u16le"),
            &raw.iter().flat_map(|v| v.to_le_bytes()).collect::<Vec<_>>(),
        )?;
        row["panels"] = json!({"truth":panel(&dest,"truth",&truth_rgb)?,"baseline":panel(&dest,"baseline",&base_rgb)?,"off":panel(&dest,"off",&off_rgb)?,"bounded":panel(&dest,"bounded",&b_rgb)?,"unbounded":panel(&dest,"unbounded",&u_rgb)?});
        replay::save(&dest.join("result.json"), &row)?;
        cases.push(row);
    }
    let quality = cases.iter().all(|r| r["quality_pass"] == true);
    let mut screen = json!({"status":if hard{"COMPLETE_GENERATED_DIAGNOSTIC"}else{"MECHANICAL_FAILURE"},"all_cases_completed":true,"hard_valid":hard,"quality_pass":quality,"admission":false,"photographic_admission":false,"RAW_reads":0});
    screen["cases"] = json!(cases);
    screen["commission"] = commission;
    screen["protocol"] = json!({"native_dimensions":[W,W],"phase_pitch_native_px":2,"score_interior_xywh":[8,8,W-16,W-16],"component_projection":"joint two-known-template projection over complete128 panel; no gradient score", "error_guard":"RGB/G/chroma <=1.10 baseline +0.5DN flat or1DN structure", "component_guard":"baseline>=.25; candidate>=.95baseline and <=1.10 truth", "noise":"one synthetic injected NoiseModel ISO100, unequal phase shot/read; no post-merge noise claim or division by N", "shot_dn_per_e":[0.15,0.13,0.17,0.21],"read_variance_dn2":[9,8,11,13],"near_far_scope":"known fine/coarse superposition, not an occlusion/physical visibility oracle","display":"identical camera-DN fixed transform, no color calibration; photo replay uses actual pinned writer", "quality_failure_policy":"retained; root may separately observe finite complete photographs"});
    replay::save(&cfg.out_dir.join("screen.json"), &screen)?;
    ensure!(
        hard,
        "mechanical guard failure; diagnostic evidence retained"
    );
    Ok(())
}
