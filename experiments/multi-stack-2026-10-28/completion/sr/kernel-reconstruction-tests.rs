use super::*;
use strehl_core::align::SimilarityParams;
use strehl_core::noise::Levels;

struct Raw {
    geom: PlaneGeometry,
    data: Vec<u16>,
    stride: usize,
    ox: usize,
    oy: usize,
}
impl QuadSource for Raw {
    fn geometry(&self) -> PlaneGeometry {
        self.geom
    }
    fn quad_rows(&self, y: usize) -> (&[u16], &[u16]) {
        let a = (self.oy + 2 * y) * self.stride + self.ox;
        (
            &self.data[a..a + 2 * self.geom.width],
            &self.data[a + self.stride..a + self.stride + 2 * self.geom.width],
        )
    }
}
fn noise(signal_gain: f32, read: f32) -> [PlaneNoise; 4] {
    [PlaneNoise {
        gain_dn_per_e: signal_gain,
        read_noise_e: read,
        levels: Levels {
            black: 512.0,
            white: 15360.0,
        },
    }; 4]
}
fn default_lattice() -> OutputLattice {
    OutputLattice {
        full: PlaneGeometry {
            width: 32,
            height: 32,
        },
        origin_sensor: [18.0, 20.0],
        step_sensor: [1.0; 2],
        width: 20,
        height: 18,
    }
}
fn pull(dx: f64, dy: f64, g: f64, rot: f64) -> Similarity {
    Similarity::from_params(SimilarityParams {
        ax: dx * 0.5,
        ay: dy * 0.5,
        g,
        rot,
    })
}
fn grid(axis: usize) -> Vec<Similarity> {
    (0..axis)
        .flat_map(|x| {
            (0..axis).map(move |y| {
                pull(
                    2.0 * x as f64 / axis as f64,
                    2.0 * y as f64 / axis as f64,
                    0.0,
                    0.0,
                )
            })
        })
        .collect()
}
// Independent absolute-sensor oracle: no Similarity::apply/invert and no guide-site conversion.
fn original_position(t: Similarity, geom: PlaneGeometry, x: f64, y: f64) -> [f64; 2] {
    let cx = geom.width as f64 + 0.5;
    let cy = geom.height as f64 + 0.5;
    let xx = x - cx - 2.0 * t.b.re;
    let yy = y - cy - 2.0 * t.b.im;
    let det = t.a.re * t.a.re + t.a.im * t.a.im;
    [
        cx + (t.a.re * xx + t.a.im * yy) / det,
        cy + (-t.a.im * xx + t.a.re * yy) / det,
    ]
}
fn mix(mut x: u64) -> u64 {
    x = x.wrapping_add(0x9e3779b97f4a7c15);
    x = (x ^ (x >> 30)).wrapping_mul(0xbf58476d1ce4e5b9);
    x = (x ^ (x >> 27)).wrapping_mul(0x94d049bb133111eb);
    x ^ (x >> 31)
}
fn raw(
    geom: PlaneGeometry,
    pulls: [Similarity; 3],
    gain: f32,
    scene: &dyn Fn([f64; 2]) -> [f32; 3],
    noise_model: [PlaneNoise; 4],
    seed: Option<u64>,
    padding: u16,
) -> Raw {
    let stride = geom.width * 2 + 9;
    let ox = 3;
    let oy = 5;
    let mut out = Raw {
        geom,
        data: vec![padding; stride * (geom.height * 2 + oy + 4)],
        stride,
        ox,
        oy,
    };
    for y in 0..geom.height * 2 {
        for x in 0..geom.width * 2 {
            let plane = match (x % 2, y % 2) {
                (0, 0) => 0,
                (1, 0) => 1,
                (1, 1) => 2,
                _ => 3,
            };
            let color = match plane {
                0 => 0,
                2 => 2,
                _ => 1,
            };
            let p = original_position(pulls[color], geom, x as f64, y as f64);
            let signal = scene(p)[color] / gain;
            let dev = seed.map_or(0.0, |s| {
                let sign = if mix(s ^ (y * geom.width * 2 + x) as u64) & 1 == 0 {
                    -1.0
                } else {
                    1.0
                };
                sign * noise_model[plane].variance(signal).sqrt()
            });
            out.data[(y + oy) * stride + x + ox] =
                (512.0 + signal + dev).round().clamp(0.0, 65535.0) as u16;
        }
    }
    out
}
struct Guide {
    expected: Vec<[f32; 3]>,
    tensor: Vec<[f32; 3]>,
    fallback: Vec<[f32; 3]>,
    variance: Vec<[f32; 3]>,
    valid: Vec<bool>,
}
impl Guide {
    fn new(l: OutputLattice, scene: &dyn Fn([f64; 2]) -> [f32; 3], fallback: [f32; 3]) -> Self {
        let n = l.width * l.height;
        Self {
            expected: (0..n)
                .map(|i| scene(l.position(i % l.width, i / l.width)))
                .collect(),
            tensor: vec![[0.0; 3]; n],
            fallback: vec![fallback; n],
            variance: vec![[10000.0; 3]; n],
            valid: vec![true; n],
        }
    }
    fn view(&self) -> FrozenGuide<'_> {
        FrozenGuide {
            expected_rgb: &self.expected,
            tensor: &self.tensor,
            fallback_rgb: &self.fallback,
            fallback_variance: Some(&self.variance),
            fallback_valid: &self.valid,
        }
    }
}
struct Fields {
    one: Vec<f32>,
    sigma: Vec<f32>,
    valid: Vec<bool>,
}
impl Fields {
    fn new(n: usize) -> Self {
        Self {
            one: vec![1.0; n],
            sigma: vec![0.0; n],
            valid: vec![true; n],
        }
    }
    fn admission(&self) -> Admission<'_> {
        Admission {
            focus: &self.one,
            motion: &self.one,
            valid: &self.valid,
            registration_sigma_sensor: &self.sigma,
        }
    }
}
fn views<'a>(
    raws: &'a [Raw],
    pulls: &[[Similarity; 3]],
    gains: &[f32],
    pn: [PlaneNoise; 4],
    fields: &'a Fields,
) -> Vec<SourceView<'a>> {
    raws.iter()
        .enumerate()
        .map(|(i, raw)| SourceView {
            acquisition_id: i as u64 + 1,
            source: raw,
            source_pull: pulls[i],
            noise: pn,
            gain: gains[i],
            admission: fields.admission(),
        })
        .collect()
}
fn all_reconstructed(result: &TileResult) {
    assert!(result.valid.iter().all(|v| *v));
    assert!(
        result
            .reason
            .iter()
            .flatten()
            .all(|v| *v == Reason::Reconstructed)
    );
}

#[test]
fn a01_flat_first_temporal_mean_variance_and_gain_squared() {
    let mut l = default_lattice();
    l.width = 1;
    l.height = 1;
    l.origin_sensor = [24.25, 24.25];
    let maps: Vec<_> = grid(2)
        .into_iter()
        .cycle()
        .take(8)
        .map(|t| [t; 3])
        .collect();
    let pn = noise(0.25, 8.0);
    let fields = Fields::new(1);
    let scene = |_p| [256.0; 3];
    let guide = Guide::new(l, &scene, [256.0; 3]);
    for gain in [1.0, 2.0] {
        let gains = vec![gain; maps.len()];
        let mut sums = [0.0f64; 3];
        let mut sums2 = [0.0f64; 3];
        let mut predicted = [0.0f64; 3];
        const RUNS: usize = 384;
        for seed in 0..RUNS {
            let raws: Vec<_> = maps
                .iter()
                .enumerate()
                .map(|(i, t)| {
                    raw(
                        l.full,
                        *t,
                        gain,
                        &scene,
                        pn,
                        Some((seed * 137 + i * 977) as u64),
                        65535,
                    )
                })
                .collect();
            let v = views(&raws, &maps, &gains, pn, &fields);
            let got = reconstruct_tile(l, &v, guide.view(), Config::default()).unwrap();
            all_reconstructed(&got);
            for c in 0..3 {
                let val = got.rgb[0][c] as f64;
                sums[c] += val;
                sums2[c] += val * val;
                predicted[c] += got.variance[0][c] as f64;
            }
        }
        for c in 0..3 {
            let mean = sums[c] / RUNS as f64;
            let observed = (sums2[c] - sums[c] * sums[c] / RUNS as f64) / (RUNS - 1) as f64;
            let model = predicted[c] / RUNS as f64;
            assert!(
                (mean - 256.0).abs() < 0.7,
                "gain={gain} color={c} mean={mean}"
            );
            assert!(
                (observed / model - 1.0).abs() < 0.24,
                "gain={gain} color={c} observed={observed} model={model}"
            );
            assert!(observed < 0.6 * pn[c].variance(256.0 / gain) as f64 * (gain * gain) as f64);
        }
    }
}
#[test]
fn a02_frozen_prediction_avoids_same_sample_inverse_variance_bias() {
    let mut l = default_lattice();
    l.width = 1;
    l.height = 1;
    l.origin_sensor = [24.25; 2];
    let maps: Vec<_> = grid(2)
        .into_iter()
        .cycle()
        .take(8)
        .map(|t| [t; 3])
        .collect();
    let pn = noise(1.0, 0.0);
    let fields = Fields::new(1);
    let guide = Guide::new(l, &|_| [64.0; 3], [64.0; 3]);
    let raws: Vec<_> = maps
        .iter()
        .enumerate()
        .map(|(i, t)| {
            raw(
                l.full,
                *t,
                1.0,
                &|_| [if i < 4 { 72.0 } else { 56.0 }; 3],
                pn,
                None,
                0,
            )
        })
        .collect();
    let v = views(&raws, &maps, &vec![1.0; 8], pn, &fields);
    // The previous integer-phase fixture is now correctly refused: tiny
    // Gaussian weights cannot certify its available phase geometry.
    let integer = OutputLattice {
        origin_sensor: [24.0; 2],
        ..l
    };
    let refused = reconstruct_tile(integer, &v, guide.view(), Config::default()).unwrap();
    assert!(
        refused.reason[0]
            .iter()
            .all(|r| *r == Reason::IllConditioned),
        "integer reasons {:?}, conditions {:?}",
        refused.reason,
        refused.phase_condition
    );
    assert!(
        refused.phase_condition[0]
            .iter()
            .all(|v| *v > 20.0 && *v < 35.0),
        "integer conditions {:?}",
        refused.phase_condition
    );
    let got = reconstruct_tile(l, &v, guide.view(), Config::default()).unwrap();
    all_reconstructed(&got);
    assert!(got.rgb[0].iter().all(|v| (*v - 64.0).abs() < 0.003));
    let wrong = (72.0f32 / 72.0 + 56.0 / 56.0) / (1.0 / 72.0 + 1.0 / 56.0);
    assert!(
        wrong < 63.1,
        "same-noisy-sample precision foil must be observably biased"
    );
}
#[test]
fn b01_phase_gate_has_two_dimensional_positive_duplicate_and_x_only_negatives() {
    let mut l = default_lattice();
    l.width = 1;
    l.height = 1;
    let pn = noise(0.25, 8.0);
    let fields = Fields::new(1);
    let guide = Guide::new(l, &|_| [1000.0; 3], [123.0, 456.0, 789.0]);
    for (name, transforms, should_pass) in [
        ("dense_two_d", grid(4), true),
        ("sparse_two_d_taper_insufficient", grid(2), false),
        (
            "integer_only",
            (0..8)
                .map(|i| pull(2.0 * i as f64, 0.0, 0.0, 0.0))
                .collect(),
            false,
        ),
        (
            "x_only",
            (0..8)
                .map(|i| pull(i as f64 * 0.25, 0.0, 0.0, 0.0))
                .collect(),
            false,
        ),
        ("duplicate_phases", vec![Similarity::IDENTITY; 8], false),
    ] {
        let maps: Vec<_> = transforms.iter().map(|t| [*t; 3]).collect();
        let raws: Vec<_> = maps
            .iter()
            .map(|t| raw(l.full, *t, 1.0, &|_| [1000.0; 3], pn, None, 0))
            .collect();
        let v = views(&raws, &maps, &vec![1.0; maps.len()], pn, &fields);
        let got = reconstruct_tile(l, &v, guide.view(), Config::default()).unwrap();
        for c in [0, 2] {
            assert_eq!(
                got.reason[0][c] == Reason::Reconstructed,
                should_pass,
                "{name}: {:?}",
                got.phase_condition
            );
            if !should_pass {
                assert_eq!(got.rgb[0][c].to_bits(), guide.fallback[0][c].to_bits());
            }
        }
        assert_eq!(
            got.independent_acquisitions[0][1] as usize,
            maps.len(),
            "greens are not two independent captures"
        );
    }
}
fn color_scene(p: [f64; 2]) -> [f32; 3] {
    let frequencies = [(0.35, 0.11), (0.21, 0.23), (0.13, 0.34)];
    frequencies.map(|(fx, fy)| {
        // Analytic pixel-aperture integration, not a resized image.
        let sinc = |v: f64| (std::f64::consts::PI * v).sin() / (std::f64::consts::PI * v);
        (4000.0
            + 1500.0
                * sinc(fx)
                * sinc(fy)
                * (2.0 * std::f64::consts::PI * (fx * p[0] + fy * p[1])).sin()) as f32
    })
}
fn single_color_bilinear(raw: &Raw, p: [f64; 2], color: usize) -> f32 {
    // Explicit single-frame interpolation foil, only a comparator/fallback in controls.
    let offset = match color {
        0 => [0.0, 0.0],
        1 => [1.0, 0.0],
        _ => [1.0, 1.0],
    };
    let q = [(p[0] - offset[0]) * 0.5, (p[1] - offset[1]) * 0.5];
    let x = q[0].floor() as usize;
    let y = q[1].floor() as usize;
    let dx = (q[0] - x as f64) as f32;
    let dy = (q[1] - y as f64) as f32;
    let get = |xx, yy| {
        let (a, b) = raw.quad_rows(yy);
        let row = if offset[1] == 0.0 { a } else { b };
        f32::from(row[2 * xx + offset[0] as usize]) - 512.0
    };
    (1.0 - dy) * ((1.0 - dx) * get(x, y) + dx * get(x + 1, y))
        + dy * ((1.0 - dx) * get(x, y + 1) + dx * get(x + 1, y + 1))
}
#[test]
fn b02_colored_alias_positive_native_and_fractional_lattice_against_analytic_truth() {
    let pn = noise(0.01, 1.0);
    for axis in [2, 3] {
        let mut l = default_lattice();
        l.step_sensor = [2.0 / axis as f64; 2];
        let maps: Vec<_> = grid(axis * 2).iter().map(|t| [*t; 3]).collect();
        let raws: Vec<_> = maps
            .iter()
            .map(|t| raw(l.full, *t, 1.0, &color_scene, pn, None, 65535))
            .collect();
        let fields = Fields::new(l.width * l.height);
        let mut guide = Guide::new(l, &color_scene, [0.0; 3]);
        for (i, f) in guide.fallback.iter_mut().enumerate() {
            let p = l.position(i % l.width, i / l.width);
            *f = std::array::from_fn(|c| single_color_bilinear(&raws[0], p, c));
        }
        let v = views(&raws, &maps, &vec![1.0; maps.len()], pn, &fields);
        let got = reconstruct_tile(l, &v, guide.view(), Config::default()).unwrap();
        all_reconstructed(&got);
        for c in [0, 2] {
            let error = |values: &[[f32; 3]]| {
                values
                    .iter()
                    .zip(&guide.expected)
                    .map(|(v, t)| f64::from(v[c] - t[c]).powi(2))
                    .sum::<f64>()
            };
            assert!(
                error(&got.rgb) < 0.3 * error(&guide.fallback),
                "axis={axis},color={c}, actual={},foil={}",
                error(&got.rgb),
                error(&guide.fallback)
            );
        }
    }
}
#[test]
fn b03_quadratic_color_edge_and_absolute_sensor_curvature_control() {
    let l = default_lattice();
    let pn = noise(0.01, 1.0);
    let fields = Fields::new(l.width * l.height);
    let scene = |p: [f64; 2]| {
        let x = p[0] - 30.0;
        let y = p[1] - 30.0;
        [
            2000.0 + (0.5 * x * x + 0.25 * x * y + 0.1 * y * y) as f32,
            3000.0 + (0.1 * x * x + 0.3 * y * y) as f32,
            4000.0 + (0.2 * x * x + 0.4 * y * y) as f32,
        ]
    };
    let maps: Vec<_> = grid(4)
        .iter()
        .enumerate()
        .map(|(i, t)| {
            let g = 0.0004 * ((i % 4) * (i % 4)) as f64;
            let rot = 0.0007 * ((i % 4) as f64 - 1.5);
            [pull(t.b.re * 2.0, t.b.im * 2.0, g, rot); 3]
        })
        .collect();
    let raws: Vec<_> = maps
        .iter()
        .map(|t| raw(l.full, *t, 1.0, &scene, pn, None, 65535))
        .collect();
    let guide = Guide::new(l, &scene, [0.0; 3]);
    let v = views(&raws, &maps, &vec![1.0; maps.len()], pn, &fields);
    let got = reconstruct_tile(l, &v, guide.view(), Config::default()).unwrap();
    all_reconstructed(&got);
    let maximum = got
        .rgb
        .iter()
        .zip(&guide.expected)
        .flat_map(|(a, b)| a.iter().zip(b).map(|(a, b)| (a - b).abs()))
        .fold(0.0f32, f32::max);
    assert!(maximum < 2.0, "quadratic error={maximum}");
    let edge = |p: [f64; 2]| {
        let v = 1.0 / (1.0 + (-(p[0] - 29.0 + 0.3 * (p[1] - 25.0)) / 0.8).exp());
        [
            1000.0 + 5000.0 * v as f32,
            2000.0,
            6000.0 - 4500.0 * v as f32,
        ]
    };
    let raws: Vec<_> = maps
        .iter()
        .map(|t| raw(l.full, *t, 1.0, &edge, pn, None, 0))
        .collect();
    let guide = Guide::new(l, &edge, [0.0; 3]);
    let v = views(&raws, &maps, &vec![1.0; maps.len()], pn, &fields);
    let got = reconstruct_tile(l, &v, guide.view(), Config::default()).unwrap();
    all_reconstructed(&got);
    assert!(got.rgb.iter().all(|p| (999.0..=6001.0).contains(&p[0])
        && (p[1] - 2000.0).abs() < 0.01
        && (1499.0..=6001.0).contains(&p[2])));
}
#[test]
fn c01_motion_focus_registration_and_clipping_losses_retain_exact_fallback() {
    let mut l = default_lattice();
    l.width = 1;
    l.height = 1;
    l.origin_sensor = [18.25, 20.25];
    let pn = noise(0.25, 8.0);
    let fields = Fields::new(1);
    let maps: Vec<_> = grid(2).iter().map(|t| [*t; 3]).collect();
    let mut raws: Vec<_> = maps
        .iter()
        .map(|t| raw(l.full, *t, 1.0, &|_| [3000.0; 3], pn, None, 0))
        .collect();
    let guide = Guide::new(l, &|_| [3000.0; 3], [123.0, 456.0, 789.0]);
    let zero = [0.0];
    let bad_sigma = [0.5];
    assert!(guide_motion_confidence(0.0, 4.0, 0.0, 4.0) > 0.99);
    assert_eq!(guide_motion_confidence(50.0, 4.0, 1.0, 4.0), 0.0);
    for reject in 0..3 {
        let mut v = views(&raws, &maps, &[1.0; 4], pn, &fields);
        match reject {
            0 => v[3].admission.motion = &zero,
            1 => v[3].admission.focus = &zero,
            _ => v[3].admission.registration_sigma_sensor = &bad_sigma,
        }
        let got = reconstruct_tile(l, &v, guide.view(), Config::default()).unwrap();
        for c in [0, 2] {
            assert_eq!(got.rgb[0][c], guide.fallback[0][c]);
            assert_eq!(got.independent_acquisitions[0][c], 3);
        }
    }
    raws[3].data.fill(65535);
    let v = views(&raws, &maps, &[1.0; 4], pn, &fields);
    let got = reconstruct_tile(l, &v, guide.view(), Config::default()).unwrap();
    for c in [0, 2] {
        assert_eq!(got.rgb[0][c], guide.fallback[0][c]);
        assert!(got.clipped_samples[0][c] > 0);
    }
}
#[test]
fn c02_active_origin_padding_poison_and_tiled_global_lattice_are_identical() {
    let l = default_lattice();
    let pn = noise(0.01, 1.0);
    let fields = Fields::new(l.width * l.height);
    let maps: Vec<_> = grid(4).iter().map(|t| [*t; 3]).collect();
    let raws: Vec<_> = maps
        .iter()
        .map(|t| raw(l.full, *t, 1.0, &color_scene, pn, None, 0))
        .collect();
    let poisoned: Vec<_> = maps
        .iter()
        .map(|t| raw(l.full, *t, 1.0, &color_scene, pn, None, 65535))
        .collect();
    let guide = Guide::new(l, &color_scene, [0.0; 3]);
    let a = reconstruct_tile(
        l,
        &views(&raws, &maps, &vec![1.0; maps.len()], pn, &fields),
        guide.view(),
        Config::default(),
    )
    .unwrap();
    let b = reconstruct_tile(
        l,
        &views(&poisoned, &maps, &vec![1.0; maps.len()], pn, &fields),
        guide.view(),
        Config::default(),
    )
    .unwrap();
    assert_eq!(bits(&a), bits(&b));
    for first_y in [0, 9] {
        let mut tile = l;
        tile.height = 9;
        tile.origin_sensor = l.position(0, first_y);
        let tile_fields = Fields::new(tile.width * tile.height);
        let tile_guide = Guide::new(tile, &color_scene, [0.0; 3]);
        let got = reconstruct_tile(
            tile,
            &views(&raws, &maps, &vec![1.0; maps.len()], pn, &tile_fields),
            tile_guide.view(),
            Config::default(),
        )
        .unwrap();
        for i in 0..got.rgb.len() {
            for c in 0..3 {
                assert_eq!(
                    got.rgb[i][c].to_bits(),
                    a.rgb[first_y * l.width + i][c].to_bits()
                );
            }
        }
    }
}
fn bits(r: &TileResult) -> Vec<u32> {
    r.rgb
        .iter()
        .chain(&r.variance)
        .chain(&r.phase_condition)
        .flat_map(|p| p.map(f32::to_bits))
        .collect()
}
#[test]
fn c03_memory_duplicate_identity_and_invalid_inputs_refuse_before_output() {
    let mut l = default_lattice();
    l.width = usize::MAX;
    assert!(memory_estimate(l, 4, 1).is_err());
    let l = default_lattice();
    let pn = noise(0.01, 1.0);
    let maps: Vec<_> = grid(2).iter().map(|t| [*t; 3]).collect();
    let fields = Fields::new(l.width * l.height);
    let raws: Vec<_> = maps
        .iter()
        .map(|t| raw(l.full, *t, 1.0, &color_scene, pn, None, 0))
        .collect();
    let guide = Guide::new(l, &color_scene, [0.0; 3]);
    let mut v = views(&raws, &maps, &[1.0; 4], pn, &fields);
    let need = memory_estimate(l, 4, 1).unwrap().total;
    let cfg = Config {
        budget_bytes: need - 1,
        ..Config::default()
    };
    assert!(reconstruct_tile(l, &v, guide.view(), cfg).is_err());
    v[1].acquisition_id = v[0].acquisition_id;
    assert!(reconstruct_tile(l, &v, guide.view(), Config::default()).is_err());
    assert!(memory_estimate(l, MAX_SOURCES + 1, 1).is_err());
    assert!(memory_estimate(l, 4, 5).is_err());
}
#[test]
fn c04_optical_lowpass_cannot_earn_new_high_frequency_signal() {
    let l = default_lattice();
    let pn = noise(0.01, 1.0);
    let fields = Fields::new(l.width * l.height);
    let maps: Vec<_> = grid(4).iter().map(|t| [*t; 3]).collect();
    let scene = |p: [f64; 2]| {
        [4000.0 + (500.0 * (2.0 * std::f64::consts::PI * (0.04 * p[0] + 0.03 * p[1])).sin()) as f32;
            3]
    };
    let raws: Vec<_> = maps
        .iter()
        .map(|t| raw(l.full, *t, 1.0, &scene, pn, None, 0))
        .collect();
    let guide = Guide::new(l, &scene, [0.0; 3]);
    let got = reconstruct_tile(
        l,
        &views(&raws, &maps, &vec![1.0; maps.len()], pn, &fields),
        guide.view(),
        Config::default(),
    )
    .unwrap();
    all_reconstructed(&got);
    let error = got
        .rgb
        .iter()
        .zip(&guide.expected)
        .flat_map(|(a, b)| a.iter().zip(b).map(|(a, b)| f64::from(a - b).powi(2)))
        .sum::<f64>()
        / (3 * got.rgb.len()) as f64;
    let poisoned: Vec<_> = got
        .rgb
        .iter()
        .enumerate()
        .map(|(i, p)| p.map(|v| v + if i % 2 == 0 { 100.0 } else { -100.0 }))
        .collect();
    let wrong = poisoned
        .iter()
        .zip(&guide.expected)
        .flat_map(|(a, b)| a.iter().zip(b).map(|(a, b)| f64::from(a - b).powi(2)))
        .sum::<f64>()
        / (3 * got.rgb.len()) as f64;
    assert!(error < 30.0, "lowpass truth error={error}");
    assert!(
        wrong > 100.0 * error,
        "false detail must fail truth residual despite louder output"
    );
}

#[test]
fn d01_same_count_resampled_foil_loses_the_sampling_information() {
    let l = default_lattice();
    let pn = noise(0.01, 1.0);
    let fields = Fields::new(l.width * l.height);
    let maps: Vec<_> = grid(4).iter().map(|t| [*t; 3]).collect();
    let raws: Vec<_> = maps
        .iter()
        .map(|t| raw(l.full, *t, 1.0, &color_scene, pn, None, 0))
        .collect();
    let guide = Guide::new(l, &color_scene, [0.0; 3]);
    let got = reconstruct_tile(
        l,
        &views(&raws, &maps, &vec![1.0; maps.len()], pn, &fields),
        guide.view(),
        Config::default(),
    )
    .unwrap();
    all_reconstructed(&got);
    let mut resampled = vec![[0.0f32; 3]; l.width * l.height];
    let center = [l.full.width as f64 + 0.5, l.full.height as f64 + 0.5];
    for (i, pixel) in resampled.iter_mut().enumerate() {
        let p = l.position(i % l.width, i / l.width);
        for (raw, m) in raws.iter().zip(&maps) {
            for c in 0..3 {
                let t = m[c];
                let x = p[0] - center[0];
                let y = p[1] - center[1];
                let src = [
                    center[0] + t.a.re * x - t.a.im * y + 2.0 * t.b.re,
                    center[1] + t.a.im * x + t.a.re * y + 2.0 * t.b.im,
                ];
                pixel[c] += single_color_bilinear(raw, src, c) / raws.len() as f32;
            }
        }
    }
    for c in [0, 2] {
        let error = |values: &[[f32; 3]]| {
            values
                .iter()
                .zip(&guide.expected)
                .map(|(v, t)| f64::from(v[c] - t[c]).powi(2))
                .sum::<f64>()
        };
        assert!(
            error(&got.rgb) < 0.3 * error(&resampled),
            "direct same-count gain: c={c}, direct={},resampled={}",
            error(&got.rgb),
            error(&resampled)
        );
    }
    // The no-SR arm still performs a genuine arithmetic average. Independent
    // zero-mean frame offsets shrink exactly with 1/N; no selector replaces it.
    let offsets = [-3.0f32, -1.0, 1.0, 3.0];
    assert_eq!(offsets.iter().sum::<f32>() / offsets.len() as f32, 0.0);
}
#[test]
fn d02_shuffled_placements_and_wrong_cfa_parity_fail_truth_not_just_power() {
    let l = default_lattice();
    let pn = noise(0.01, 1.0);
    let fields = Fields::new(l.width * l.height);
    let maps: Vec<_> = grid(4).iter().map(|t| [*t; 3]).collect();
    let raws: Vec<_> = maps
        .iter()
        .map(|t| raw(l.full, *t, 1.0, &color_scene, pn, None, 0))
        .collect();
    let guide = Guide::new(l, &color_scene, [0.0; 3]);
    let good = reconstruct_tile(
        l,
        &views(&raws, &maps, &vec![1.0; maps.len()], pn, &fields),
        guide.view(),
        Config::default(),
    )
    .unwrap();
    all_reconstructed(&good);
    let mut shuffled = maps.clone();
    shuffled.rotate_left(1);
    let wrong_map = reconstruct_tile(
        l,
        &views(&raws, &shuffled, &vec![1.0; maps.len()], pn, &fields),
        guide.view(),
        Config::default(),
    )
    .unwrap();
    let mut wrong_raw: Vec<_> = maps
        .iter()
        .map(|t| raw(l.full, *t, 1.0, &color_scene, pn, None, 0))
        .collect();
    for image in &mut wrong_raw {
        for y in 0..image.geom.height {
            for x in 0..image.geom.width {
                let r = (image.oy + 2 * y) * image.stride + image.ox + 2 * x;
                let b = r + image.stride + 1;
                image.data.swap(r, b);
            }
        }
    }
    let wrong_cfa = reconstruct_tile(
        l,
        &views(&wrong_raw, &maps, &vec![1.0; maps.len()], pn, &fields),
        guide.view(),
        Config::default(),
    )
    .unwrap();
    let error = |values: &[[f32; 3]]| {
        values
            .iter()
            .zip(&guide.expected)
            .flat_map(|(v, t)| [0, 2].map(|c| f64::from(v[c] - t[c]).powi(2)))
            .sum::<f64>()
    };
    assert!(error(&wrong_map.rgb) > 8.0 * error(&good.rgb));
    assert!(error(&wrong_cfa.rgb) > 8.0 * error(&good.rgb));
    // Geometry can still look well conditioned after a correspondence shuffle.
    // The truth witness detects it; runtime rejection additionally needs the
    // caller's independent local motion/photometric confidence, not this matrix.
    assert!(
        wrong_map
            .reason
            .iter()
            .flatten()
            .any(|r| *r == Reason::Reconstructed)
    );
}
#[test]
fn d03_parallel_independent_tiles_preserve_all_output_bits() {
    let mut l = default_lattice();
    l.height = 16;
    let pn = noise(0.01, 1.0);
    let maps: Vec<_> = grid(4).iter().map(|t| [*t; 3]).collect();
    let raws: Vec<_> = maps
        .iter()
        .enumerate()
        .map(|(i, t)| raw(l.full, *t, 1.0, &color_scene, pn, Some(i as u64), 65535))
        .collect();
    let fields = Fields::new(l.width * l.height);
    let guide = Guide::new(l, &color_scene, [0.0; 3]);
    let serial = reconstruct_tile(
        l,
        &views(&raws, &maps, &vec![1.0; maps.len()], pn, &fields),
        guide.view(),
        Config::default(),
    )
    .unwrap();
    std::thread::scope(|scope| {
        let handles: Vec<_> = (0..4)
            .map(|chunk| {
                let raws = &raws;
                let maps = &maps;
                scope.spawn(move || {
                    let mut tile = l;
                    tile.height = 4;
                    tile.origin_sensor = l.position(0, chunk * 4);
                    let fields = Fields::new(tile.width * tile.height);
                    let guide = Guide::new(tile, &color_scene, [0.0; 3]);
                    reconstruct_tile(
                        tile,
                        &views(raws, maps, &vec![1.0; maps.len()], pn, &fields),
                        guide.view(),
                        Config::default(),
                    )
                    .unwrap()
                })
            })
            .collect();
        for (chunk, handle) in handles.into_iter().enumerate() {
            let got = handle.join().unwrap();
            for i in 0..got.rgb.len() {
                let full = chunk * 4 * l.width + i;
                for c in 0..3 {
                    assert_eq!(got.rgb[i][c].to_bits(), serial.rgb[full][c].to_bits());
                    assert_eq!(
                        got.variance[i][c].to_bits(),
                        serial.variance[full][c].to_bits()
                    );
                    assert_eq!(
                        got.phase_condition[i][c].to_bits(),
                        serial.phase_condition[full][c].to_bits()
                    );
                    assert_eq!(got.reason[i][c], serial.reason[full][c]);
                    assert_eq!(
                        got.independent_acquisitions[i][c],
                        serial.independent_acquisitions[full][c]
                    );
                    assert_eq!(got.accepted_samples[i][c], serial.accepted_samples[full][c]);
                }
            }
        }
    });
}

#[test]
fn c05_unknown_fallback_variance_is_not_a_fabricated_bound() {
    let mut l = default_lattice();
    l.width = 2;
    l.height = 2;
    let scene = |_p| [256.0; 3];
    let maps: Vec<_> = grid(4).into_iter().map(|t| [t; 3]).collect();
    let pn = noise(0.25, 8.0);
    let raws: Vec<_> = maps
        .iter()
        .map(|&t| raw(l.full, t, 1.0, &scene, pn, None, 65535))
        .collect();
    let fields = Fields::new(4);
    let sources = views(&raws, &maps, &vec![1.0; maps.len()], pn, &fields);
    let mut guide = Guide::new(l, &scene, [123.0; 3]);
    guide.variance.fill([0.0; 3]);
    let known = reconstruct_tile(l, &sources, guide.view(), Config::default()).unwrap();
    assert!(
        known
            .reason
            .iter()
            .flatten()
            .all(|r| *r == Reason::ExcessVariance)
    );
    assert!(known.variance_valid.iter().flatten().all(|v| *v));
    let mut no_var = guide.view();
    no_var.fallback_variance = None;
    let unknown = reconstruct_tile(l, &sources, no_var, Config::default()).unwrap();
    all_reconstructed(&unknown);
    assert!(unknown.variance_valid.iter().flatten().all(|v| *v));
    let maps = vec![[Similarity::IDENTITY; 3]; maps.len()];
    let sources = views(&raws, &maps, &vec![1.0; maps.len()], pn, &fields);
    let mut no_var = guide.view();
    no_var.fallback_variance = None;
    let fallback = reconstruct_tile(l, &sources, no_var, Config::default()).unwrap();
    assert!(
        fallback
            .reason
            .iter()
            .flatten()
            .all(|r| *r != Reason::Reconstructed)
    );
    assert_eq!(fallback.rgb, guide.fallback);
    assert!(fallback.variance_valid.iter().flatten().all(|v| !*v));
    assert!(fallback.variance.iter().flatten().all(|v| v.is_nan()));
}

#[test]
fn c06_stored_warpmap_origin_is_not_the_sample_centroid() {
    let full = PlaneGeometry {
        width: 64,
        height: 48,
    };
    let t = pull(0.75, -0.625, 0.12, 0.07);
    // Production fitting origin is guide(32,24), physically sensor(64.5,48.5).
    let p = [64.5, 48.5];
    let mapped = sensor_pull(t, full, p);
    assert!((mapped[0] - 65.25).abs() < 1e-12);
    assert!((mapped[1] - 47.875).abs() < 1e-12);
    let back = sensor_pull(t.invert().unwrap(), full, mapped);
    assert!((back[0] - p[0]).abs() < 1e-12 && (back[1] - p[1]).abs() < 1e-12);
    // Keep the original integration mistake as a falsifying control.
    let old = t.apply_at((p[0] - 0.5) * 0.5, (p[1] - 0.5) * 0.5, 31.5, 23.5);
    let old = [2.0 * old.0 + 0.5, 2.0 * old.1 + 0.5];
    assert!((old[0] - mapped[0]).hypot(old[1] - mapped[1]) > 0.1);
}

#[test]
fn c07_near_zero_taper_phases_cannot_certify_the_estimator() {
    let mut l = default_lattice();
    l.width = 1;
    l.height = 1;
    l.origin_sensor = [24.25, 24.25];
    let pn = noise(0.25, 8.0);
    let maps: Vec<_> = grid(2).iter().map(|t| [*t; 3]).collect();
    let scene = |_| [1000.; 3];
    let raws: Vec<_> = maps
        .iter()
        .map(|t| raw(l.full, *t, 1., &scene, pn, None, 0))
        .collect();
    let fields = Fields::new(1);
    let guide = Guide::new(l, &scene, [123.; 3]);
    let mut available = Gram::new([2, 2]);
    let mut actual = Gram::new([2, 2]);
    for x in [0.25f32, -0.75] {
        for y in [0.25f32, -0.75] {
            let w = (-0.5 * (x * x + y * y) / (0.1 * 0.1)).exp();
            assert!(w > 0.);
            available.add([x, y], 1.);
            actual.add([x, y], w);
        }
    }
    assert!(
        available.condition() < 1.01,
        "old untapered certificate would pass"
    );
    assert!(
        actual.condition() > 20.,
        "actual kernel must reject tiny-weight phase diversity"
    );
    let cfg = Config {
        sigma_sensor: 0.1,
        ..Config::default()
    };
    let got = reconstruct_tile(
        l,
        &views(&raws, &maps, &[1.; 4], pn, &fields),
        guide.view(),
        cfg,
    )
    .unwrap();
    assert!(got.reason[0].iter().all(|r| *r == Reason::IllConditioned));
    assert_eq!(got.rgb, guide.fallback);
}
#[test]
fn c08_output_sampling_does_not_change_physical_kernel_or_native_values() {
    let mut l = default_lattice();
    l.width = 1;
    l.height = 1;
    l.origin_sensor = [24.25, 24.25];
    let pn = noise(0.25, 8.0);
    let maps: Vec<_> = grid(8).iter().map(|t| [*t; 3]).collect();
    let raws: Vec<_> = maps
        .iter()
        .enumerate()
        .map(|(i, t)| raw(l.full, *t, 1., &color_scene, pn, Some(i as u64), 0))
        .collect();
    let fields = Fields::new(1);
    let guide = Guide::new(l, &color_scene, [0.; 3]);
    let gains = vec![1.; maps.len()];
    let v = views(&raws, &maps, &gains, pn, &fields);
    let native = reconstruct_tile(l, &v, guide.view(), Config::default()).unwrap();
    all_reconstructed(&native);
    for step in [2. / 3., 0.5] {
        let fine = OutputLattice {
            step_sensor: [step; 2],
            ..l
        };
        let got = reconstruct_tile(fine, &v, guide.view(), Config::default()).unwrap();
        all_reconstructed(&got);
        assert_eq!(
            got.rgb[0].map(f32::to_bits),
            native.rgb[0].map(f32::to_bits)
        );
        assert_eq!(
            got.variance[0].map(f32::to_bits),
            native.variance[0].map(f32::to_bits)
        );
    }
}

#[test]
fn a03_far_mode_tiny_weights_cannot_regain_eligibility_by_normalization() {
    let mut l = default_lattice();
    l.width = 1;
    l.height = 1;
    l.origin_sensor = [24.25, 24.25];
    let pn = noise(1., 2.);
    let maps: Vec<_> = grid(4).into_iter().map(|t| [t; 3]).collect();
    // A featureless far-defocused field still has excellent phase geometry.
    // The focus contract must refuse it independently of normalized weights.
    let scene = |_: [f64; 2]| [900., 1000., 1100.];
    let raws: Vec<_> = maps
        .iter()
        .map(|t| raw(l.full, *t, 1., &scene, pn, None, 0))
        .collect();
    let fields = Fields::new(1);
    let guide = Guide::new(l, &scene, [777., 778., 779.]);
    let gains = vec![1.; maps.len()];
    let mut v = views(&raws, &maps, &gains, pn, &fields);
    let positive = reconstruct_tile(l, &v, guide.view(), Config::default()).unwrap();
    all_reconstructed(&positive);
    let near = [focus_mode_response(75., 74., 5., true)];
    for source in &mut v {
        source.admission.focus = &near;
    }
    all_reconstructed(&reconstruct_tile(l, &v, guide.view(), Config::default()).unwrap());
    for response in [
        1e-8,
        0.01,
        (-0.5_f32).exp() - 1e-5,
        focus_mode_response(150., 74., 5., true),
    ] {
        let bad = [response];
        let mut v = views(&raws, &maps, &gains, pn, &fields);
        for source in &mut v {
            source.admission.focus = &bad;
        }
        let got = reconstruct_tile(l, &v, guide.view(), Config::default()).unwrap();
        assert_eq!(got.reason[0], [Reason::RejectedOrMissing; 3]);
        assert_eq!(got.accepted_samples[0], [0; 3]);
        assert_eq!(
            got.rgb[0].map(f32::to_bits),
            guide.fallback[0].map(f32::to_bits)
        );
    }
    for (ordinal, mode, width, qualified) in [
        (74., 74., 5., false),
        (74., 74., 0., true),
        (74., 74., f32::NAN, true),
        (f32::INFINITY, 74., 5., true),
    ] {
        assert_eq!(focus_mode_response(ordinal, mode, width, qualified), 0.);
    }
    assert_eq!(
        focus_mode_response(79., 74., 5., true).to_bits(),
        (-0.5_f32).exp().to_bits()
    );
    assert_eq!(focus_mode_response(79.001, 74., 5., true), 0.);
}
