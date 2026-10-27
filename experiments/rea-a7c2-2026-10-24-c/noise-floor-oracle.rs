//! Bounded identity-grid noise transport falsifier. No RAW or production edits.
//! Run through the root-wired strehl-core example; see noise-floor-design.md.
use serde_json::{Value, json};
use std::fs::{self, File};
use std::io::{BufWriter, Write};
use std::path::PathBuf;
use std::sync::Mutex;
use strehl_core::pyramid::{
    BandGain, BandMerge, BandObservation, FoldPhase, FrameWorkspace, LevelSize, MergeConfig,
    MergeObserver, Pyramid, Workspace, level_sizes,
};

type Rows = Vec<Vec<f64>>;
const TAPS: [f64; 5] = [1.0 / 16.0, 4.0 / 16.0, 6.0 / 16.0, 4.0 / 16.0, 1.0 / 16.0];
const EXACT_REL_TOL: f64 = 2e-5;

fn clamp(i: isize, n: usize) -> usize {
    i.clamp(0, n as isize - 1) as usize
}

// Independent scalar 2-D convolution. Uses S, not S squared: expectation of
// a locally averaged square is the average of the coefficient variances.
fn smooth(input: &[f64], sz: LevelSize) -> Vec<f64> {
    let mut out = vec![0.0; input.len()];
    for y in 0..sz.height {
        for x in 0..sz.width {
            for (dy, ky) in TAPS.iter().enumerate() {
                for (dx, kx) in TAPS.iter().enumerate() {
                    let sx = clamp(x as isize + dx as isize - 2, sz.width);
                    let sy = clamp(y as isize + dy as isize - 2, sz.height);
                    out[y * sz.width + x] += kx * ky * input[sy * sz.width + sx];
                }
            }
        }
    }
    out
}

// Compose 1-D Gaussian rows all the way back to original independent samples.
// Border aliases add into the same coefficient before any products/squares.
fn axis(n: usize, levels: usize) -> (Vec<Rows>, Vec<Rows>) {
    let mut identity = vec![vec![0.0; n]; n];
    for (i, row) in identity.iter_mut().enumerate() {
        row[i] = 1.0;
    }
    let mut gaussian = vec![identity];
    for k in 1..levels {
        let prev = &gaussian[k - 1];
        let mut next = vec![vec![0.0; n]; prev.len().div_ceil(2)];
        for (x, row) in next.iter_mut().enumerate() {
            for (t, weight) in TAPS.iter().enumerate() {
                let p = &prev[clamp(2 * x as isize + t as isize - 2, prev.len())];
                for (a, b) in row.iter_mut().zip(p) {
                    *a += weight * b;
                }
            }
        }
        gaussian.push(next);
    }
    let mut expanded = Vec::new();
    for k in 0..levels - 1 {
        let prev = &gaussian[k + 1];
        let mut next = vec![vec![0.0; n]; gaussian[k].len()];
        for (x, row) in next.iter_mut().enumerate() {
            let center = (x / 2) as isize;
            let phases: &[(isize, f64)] = if x % 2 == 0 {
                &[(-1, 0.125), (0, 0.75), (1, 0.125)]
            } else {
                &[(0, 0.5), (1, 0.5)]
            };
            for (offset, weight) in phases {
                let p = &prev[clamp(center + offset, prev.len())];
                for (a, b) in row.iter_mut().zip(p) {
                    *a += weight * b;
                }
            }
        }
        expanded.push(next);
    }
    (gaussian, expanded)
}

fn product_rows(a: &Rows, b: &Rows) -> Rows {
    a.iter()
        .zip(b)
        .map(|(a, b)| a.iter().zip(b).map(|(a, b)| a * b).collect())
        .collect()
}

fn separable(v: &[f64], width: usize, x: &Rows, y: &Rows) -> Vec<f64> {
    let height = v.len() / width;
    let mut tmp = vec![0.0; height * x.len()];
    for iy in 0..height {
        for (ox, row) in x.iter().enumerate() {
            tmp[iy * x.len() + ox] = row
                .iter()
                .zip(&v[iy * width..(iy + 1) * width])
                .map(|(a, b)| a * b)
                .sum();
        }
    }
    let mut out = vec![0.0; x.len() * y.len()];
    for (oy, row) in y.iter().enumerate() {
        for ox in 0..x.len() {
            out[oy * x.len() + ox] = row
                .iter()
                .enumerate()
                .map(|(iy, a)| a * tmp[iy * x.len() + ox])
                .sum();
        }
    }
    out
}

fn composed(
    v: &[f64],
    width: usize,
    gx: &Rows,
    hx: &Rows,
    gy: &Rows,
    hy: &Rows,
) -> (Vec<f64>, Vec<f64>) {
    let g = separable(v, width, &product_rows(gx, gx), &product_rows(gy, gy));
    let h = separable(v, width, &product_rows(hx, hx), &product_rows(hy, hy));
    let cross = separable(v, width, &product_rows(gx, hx), &product_rows(gy, hy));
    let omitted: Vec<f64> = g.iter().zip(&h).map(|(a, b)| a + b).collect();
    let exact = omitted
        .iter()
        .zip(cross)
        .map(|(a, b)| a - 2.0 * b)
        .collect();
    (exact, omitted)
}

struct Case {
    name: &'static str,
    v: Vec<f64>,
}
fn cases(sz: LevelSize) -> Vec<Case> {
    let mut out = vec![
        Case {
            name: "constant-read",
            v: vec![1.0; sz.pixels()],
        },
        Case {
            name: "zero",
            v: vec![0.0; sz.pixels()],
        },
    ];
    for (name, split) in [("step-even", sz.width / 2), ("step-odd", sz.width / 2 + 1)] {
        out.push(Case {
            name,
            v: (0..sz.pixels())
                .map(|i| if i % sz.width < split { 1.0 } else { 10000.0 })
                .collect(),
        });
    }
    out.push(Case {
        name: "affine",
        v: (0..sz.pixels())
            .map(|i| 1.0 + (i % sz.width) as f64 + 3.0 * (i / sz.width) as f64)
            .collect(),
    });
    for (name, i) in [
        ("center-spike", (sz.height / 2) * sz.width + sz.width / 2),
        ("corner-spike", 0),
    ] {
        let mut v = vec![1.0; sz.pixels()];
        v[i] = 10000.0;
        out.push(Case { name, v });
    }
    out.push(Case {
        name: "constant-scaled",
        v: vec![17.0; sz.pixels()],
    });
    // Generated read+shot fixtures: read variance=4 DN^2, gain=0.5 DN/e,
    // dark mean=120 DN (V=64), light mean chosen for V ratio10 or100.
    // Weak amplitude8-DN, period8 sinusoid rides on the same mean used for V.
    for (name, ratio) in [("shot-step-10x-sine", 10.0), ("shot-step-100x-sine", 100.0)] {
        out.push(Case {
            name,
            v: (0..sz.pixels())
                .map(|i| {
                    let x = i % sz.width;
                    let mean = if x < sz.width / 2 {
                        120.0
                    } else {
                        (64.0 * ratio - 4.0) / 0.5
                    };
                    let signal = mean + 8.0 * (2.0 * std::f64::consts::PI * x as f64 / 8.0).sin();
                    4.0 + 0.5 * signal
                })
                .collect(),
        });
    }
    out
}

fn relative_max(a: &[f64], b: &[f64]) -> f64 {
    assert_eq!(a.len(), b.len(), "comparison arrays differ in length");
    a.iter()
        .zip(b)
        .map(|(a, b)| (a - b).abs() / a.abs().max(1e-12))
        .fold(0.0, f64::max)
}
fn stats(reference: &[f64], estimate: &[f64], indices: &[usize]) -> Value {
    if indices.is_empty() {
        return Value::Null;
    }
    let mut rel: Vec<f64> = indices
        .iter()
        .map(|&i| (estimate[i] - reference[i]) / reference[i].max(1e-12))
        .collect();
    rel.sort_by(f64::total_cmp);
    let n = indices.len() as f64;
    json!({"count":indices.len(),"reference_mean":indices.iter().map(|&i|reference[i]).sum::<f64>()/n,
        "estimate_mean":indices.iter().map(|&i|estimate[i]).sum::<f64>()/n,
        "mean_relative_error":rel.iter().sum::<f64>()/n,"relative_rmse":(rel.iter().map(|v|v*v).sum::<f64>()/n).sqrt(),
        "min_relative_error":rel[0],"max_relative_error":rel[rel.len()-1],"median_relative_error":rel[rel.len()/2]})
}
fn regions(sz: LevelSize) -> Vec<(String, Vec<usize>)> {
    let all: Vec<_> = (0..sz.pixels()).collect();
    let interior: Vec<_> = all
        .iter()
        .copied()
        .filter(|i| {
            i % sz.width >= 6
                && i % sz.width + 6 < sz.width
                && i / sz.width >= 6
                && i / sz.width + 6 < sz.height
        })
        .collect();
    let border: Vec<_> = all
        .iter()
        .copied()
        .filter(|i| {
            i % sz.width < 2
                || i % sz.width + 2 >= sz.width
                || i / sz.width < 2
                || i / sz.width + 2 >= sz.height
        })
        .collect();
    let mut out = vec![
        ("all".into(), all),
        ("interior-margin6".into(), interior),
        ("border-width2".into(), border),
    ];
    for py in 0..2 {
        for px in 0..2 {
            out.push((
                format!("phase-{px}-{py}"),
                (0..sz.pixels())
                    .filter(|i| i % sz.width % 2 == px && i / sz.width % 2 == py)
                    .collect(),
            ));
        }
    }
    out
}

#[derive(Clone)]
struct ObservedBand {
    level: usize,
    size: LevelSize,
    energy: Vec<f32>,
    variance: Vec<f32>,
    multiplier: f32,
}
#[derive(Default)]
struct Observed {
    bands: Mutex<Vec<ObservedBand>>,
}
impl MergeObserver for Observed {
    fn phase(&self, _: FoldPhase) {}
    fn band(&self, b: BandObservation<'_>) {
        assert_eq!(b.energy.is_some(), b.variance.is_some());
        if let (Some(e), Some(v)) = (b.energy, b.variance) {
            self.bands.lock().unwrap().push(ObservedBand {
                level: b.level,
                size: b.size,
                energy: e.to_vec(),
                variance: v.to_vec(),
                multiplier: b.floor_multiplier,
            });
        }
    }
}
fn validate_observation(bands: &[ObservedBand], sizes: &[LevelSize]) -> Result<(), &'static str> {
    if bands.len() != sizes.len() - 1 {
        return Err("missing or extra observed bands");
    }
    for (k, b) in bands.iter().enumerate() {
        if b.level != k || b.size != sizes[k] {
            return Err("wrong observed band order or geometry");
        }
        if b.energy.len() != sizes[k].pixels() || b.variance.len() != sizes[k].pixels() {
            return Err("wrong observed array length");
        }
        if !b.multiplier.is_finite() || !b.energy.iter().chain(&b.variance).all(|x| x.is_finite()) {
            return Err("nonfinite observation");
        }
    }
    Ok(())
}
fn check_consumer(
    sz: LevelSize,
    sizes: &[LevelSize],
    source: &[f32],
    variance: &[f32],
    beta: &BandGain,
) -> Value {
    let mut ws = Workspace::new(sizes);
    let mut p = Pyramid::zeros(sizes);
    p.build(source, &mut ws);
    let mut var = Pyramid::zeros(sizes);
    var.build_gaussian(variance, &mut ws);
    let cfg = MergeConfig {
        bands: sizes.len() - 1,
        ..Default::default()
    };
    let mut merge = BandMerge::new(sz.width, sz.height, 1, cfg);
    let mut fw = FrameWorkspace::new(sizes, 1);
    #[cfg(feature = "spatial-noise-floor")]
    fw.set_spatial_noise_floor_mode(strehl_core::spatial_noise_floor::Mode::Off);
    let obs = Observed::default();
    merge.add_frame_with_gain_observed(&[source], source, variance, None, &mut fw, &obs);
    let mut max_energy_error = 0.0_f64;
    let mut max_floor_error = 0.0_f64;
    let observed_bands = obs.bands.into_inner().unwrap();
    validate_observation(&observed_bands, sizes).expect("complete finite actual observations");
    assert!(
        validate_observation(&[], sizes).is_err(),
        "empty observer placebo accepted"
    );
    assert!(
        validate_observation(&observed_bands[..observed_bands.len() - 1], sizes).is_err(),
        "partial observer placebo accepted"
    );
    let mut bad = observed_bands.clone();
    bad[0].level += 1;
    assert!(
        validate_observation(&bad, sizes).is_err(),
        "wrong-order placebo accepted"
    );
    let mut bad = observed_bands.clone();
    bad[0].energy.pop();
    assert!(
        validate_observation(&bad, sizes).is_err(),
        "short-observation placebo accepted"
    );
    let mut bad = observed_bands.clone();
    bad[0].variance[0] = f32::NAN;
    assert!(
        validate_observation(&bad, sizes).is_err(),
        "nonfinite-observation placebo accepted"
    );
    for (k, band) in observed_bands.iter().enumerate() {
        let energy = &band.energy;
        let v = &band.variance;
        let multiplier = band.multiplier;
        let expected = smooth(
            &p.level(k)
                .iter()
                .map(|v| f64::from(*v).powi(2))
                .collect::<Vec<_>>(),
            sizes[k],
        );
        let energy_scale = expected.iter().copied().fold(0.0, f64::max).max(1.0);
        for (i, &e) in energy.iter().enumerate() {
            max_energy_error =
                max_energy_error.max((f64::from(e) - expected[i]).abs() / energy_scale);
            let current = cfg.gate * beta.beta(k) * var.level(k)[i].max(0.0);
            let observed = multiplier * v[i].max(0.0);
            max_floor_error = max_floor_error.max(f64::from((current - observed).abs()));
        }
    }
    assert!(
        max_energy_error < 2e-6,
        "independent S differs from actual consumer"
    );
    assert_eq!(
        max_floor_error, 0.0,
        "current floor formula not actual consumer"
    );
    json!({"observer_completeness_placebos_rejected":true,"observed_band_count":observed_bands.len(),"smooth_vs_observer_max_scaled_absolute_error":max_energy_error,"floor_vs_observer_max_absolute_error":max_floor_error})
}

// SplitMix64 iid-like deterministic uniform draws, no sample centering or
// renormalization. Every draw uses the same supplied V, independent of output.
fn uniform(state: &mut u64) -> f64 {
    *state = state.wrapping_add(0x9e3779b97f4a7c15);
    let mut z = *state;
    z = (z ^ (z >> 30)).wrapping_mul(0xbf58476d1ce4e5b9);
    z = (z ^ (z >> 27)).wrapping_mul(0x94d049bb133111eb);
    let u = ((z ^ (z >> 31)) >> 11) as f64 / (1u64 << 53) as f64;
    (2.0 * u - 1.0) * 3.0_f64.sqrt()
}
fn repetitions(
    v: &[f64],
    exact: &[Vec<f64>],
    sizes: &[LevelSize],
    trials: usize,
    seed: u64,
) -> Value {
    if trials == 0 {
        return Value::Null;
    }
    let groups: Vec<_> = sizes[..sizes.len() - 1]
        .iter()
        .copied()
        .map(regions)
        .collect();
    let mut means: Vec<Vec<Vec<f64>>> = groups
        .iter()
        .map(|g| g.iter().map(|_| Vec::new()).collect())
        .collect();
    let mut ws = Workspace::new(sizes);
    let mut p = Pyramid::zeros(sizes);
    let mut state = seed;
    for _ in 0..trials {
        let noise: Vec<f32> = v
            .iter()
            .map(|v| (v.sqrt() * uniform(&mut state)) as f32)
            .collect();
        p.build(&noise, &mut ws);
        for k in 0..p.bands() {
            let energy = smooth(
                &p.level(k)
                    .iter()
                    .map(|n| f64::from(*n).powi(2))
                    .collect::<Vec<_>>(),
                sizes[k],
            );
            for (g, (_, indices)) in groups[k].iter().enumerate() {
                if !indices.is_empty() {
                    means[k][g].push(
                        indices.iter().map(|&i| energy[i]).sum::<f64>() / indices.len() as f64,
                    );
                }
            }
        }
    }
    let mut out = Vec::new();
    for k in 0..means.len() {
        for (g, (name, indices)) in groups[k].iter().enumerate() {
            if !indices.is_empty() {
                let draws = &means[k][g];
                let mean = draws.iter().sum::<f64>() / trials as f64;
                let se = if trials > 1 {
                    (draws.iter().map(|x| (x - mean).powi(2)).sum::<f64>()
                        / ((trials - 1) * trials) as f64)
                        .sqrt()
                } else {
                    0.0
                };
                let reference =
                    indices.iter().map(|&i| exact[k][i]).sum::<f64>() / indices.len() as f64;
                out.push(json!({"band":k,"region":name,"draws":trials,"oracle_mean":reference,"empirical_mean":mean,"standard_error_across_draws":se,"z_score":if se>0.0 {Some((mean-reference)/se)}else{None}}));
            }
        }
    }
    json!(out)
}

fn run_size(sz: LevelSize, trials: usize, maps: &mut impl Write) -> Value {
    let sizes = level_sizes(sz.width, sz.height, 3);
    let nb = sizes.len() - 1;
    assert!(nb > 0);
    let cases = cases(sz);
    let (gx, hx) = axis(sz.width, sizes.len());
    let (gy, hy) = axis(sz.height, sizes.len());
    let mut oracle: Vec<Vec<Vec<f64>>> = cases
        .iter()
        .map(|_| sizes[..nb].iter().map(|s| vec![0.0; s.pixels()]).collect())
        .collect();
    let mut ws = Workspace::new(&sizes);
    let mut p = Pyramid::zeros(&sizes);
    let mut impulse = vec![0.0; sz.pixels()];
    for j in 0..sz.pixels() {
        impulse[j] = 1.0;
        p.build(&impulse, &mut ws);
        impulse[j] = 0.0;
        for (case, dst) in cases.iter().zip(&mut oracle) {
            if case.v[j] != 0.0 {
                for (k, level) in dst.iter_mut().enumerate() {
                    for (a, &b) in level.iter_mut().zip(p.level(k)) {
                        *a += case.v[j] * f64::from(b).powi(2);
                    }
                }
            }
        }
    }
    for case in &mut oracle {
        for (k, level) in case.iter_mut().enumerate() {
            *level = smooth(level, sizes[k]);
        }
    }
    let beta = BandGain::measure(nb);
    let consumer_source: Vec<f32> = (0..sz.pixels())
        .map(|i| ((i * 17 + i / sz.width * 3) % 23) as f32 - 11.0)
        .collect();
    let consumer = check_consumer(
        sz,
        &sizes,
        &consumer_source,
        &cases[2].v.iter().map(|v| *v as f32).collect::<Vec<_>>(),
        &beta,
    );
    let mut corner = vec![0.0; sz.pixels()];
    corner[0] = 1.0;
    let consumer_corner = check_consumer(sz, &sizes, &corner, &vec![1.0; sz.pixels()], &beta);
    let mut rows = Vec::new();
    let mut max_composed = 0.0_f64;
    let mut max_wrong_cross = 0.0_f64;
    let mut max_shift = 0.0_f64;
    for (ci, case) in cases.iter().enumerate() {
        let vf: Vec<f32> = case.v.iter().map(|v| *v as f32).collect();
        let mut vp = Pyramid::zeros(&sizes);
        vp.build_gaussian(&vf, &mut ws);
        #[cfg(feature = "spatial-noise-floor")]
        let actual_transport = strehl_core::spatial_noise_floor::Plan::new(&sizes)
            .transport(&vf, strehl_core::spatial_noise_floor::Mode::On);
        #[cfg(feature = "spatial-noise-floor")]
        let actual_smooth = strehl_core::spatial_noise_floor::Plan::new(&sizes)
            .transport(&vf, strehl_core::spatial_noise_floor::Mode::Smooth);
        #[cfg(feature = "spatial-noise-floor")]
        for fields in [&actual_transport, &actual_smooth] {
            assert_eq!(
                fields.len(),
                nb.min(2),
                "missing or extra actual transport bands"
            );
            for (k, field) in fields.iter().enumerate() {
                assert_eq!(
                    field.len(),
                    sizes[k].pixels(),
                    "wrong actual transport dimensions"
                );
                assert!(
                    field.iter().all(|x| x.is_finite() && *x >= 0.0),
                    "invalid actual transport values"
                );
            }
        }
        for k in 0..nb {
            let exact = &oracle[ci][k];
            #[cfg(feature = "spatial-noise-floor")]
            if k < actual_transport.len() {
                let expected: Vec<f64> = exact
                    .iter()
                    .zip(&oracle[0][k])
                    .map(|(a, b)| a / b)
                    .collect();
                let actual: Vec<f64> = actual_transport[k].iter().map(|x| f64::from(*x)).collect();
                let error = relative_max(&expected, &actual);
                assert!(
                    error < 8e-5,
                    "actual f32 sparse plan disagrees with independent impulse oracle: {error}"
                );
                let expected_smooth = smooth(
                    &vp.level(k)
                        .iter()
                        .map(|x| f64::from(*x))
                        .collect::<Vec<_>>(),
                    sizes[k],
                );
                let actual_smooth: Vec<f64> =
                    actual_smooth[k].iter().map(|x| f64::from(*x)).collect();
                assert!(
                    relative_max(&expected_smooth, &actual_smooth) < 2e-6,
                    "cheap variance smoothing comparator disagrees with independent S"
                );
            }

            let (computed, omitted) = composed(&case.v, sz.width, &gx[k], &hx[k], &gy[k], &hy[k]);
            let computed = smooth(&computed, sizes[k]);
            let omitted = smooth(&omitted, sizes[k]);
            let err = relative_max(exact, &computed);
            max_composed = max_composed.max(err);
            assert!(
                err < EXACT_REL_TOL,
                "separable/impulse mismatch {err} {} band{k}",
                case.name
            );
            let current: Vec<f64> = vp
                .level(k)
                .iter()
                .map(|v| f64::from(beta.beta(k) * v.max(0.0)))
                .collect();
            let mut shifted = case.v.clone();
            for y in 0..sz.height {
                for x in 0..sz.width {
                    shifted[y * sz.width + x] = case.v[y * sz.width + (x + 1) % sz.width];
                }
            }
            let (shifted, _) = composed(&shifted, sz.width, &gx[k], &hx[k], &gy[k], &hy[k]);
            let shifted = smooth(&shifted, sizes[k]);
            max_wrong_cross = max_wrong_cross.max(relative_max(exact, &omitted));
            max_shift = max_shift.max(relative_max(exact, &shifted));
            for (region, indices) in regions(sizes[k]) {
                rows.push(json!({"case":case.name,"band":k,"region":region,"beta":beta.beta(k),"current":stats(exact,&current,&indices),"omitted_cross_foil":stats(exact,&omitted,&indices),"shifted_variance_foil":stats(exact,&shifted,&indices),"separable_max_relative_error":err}));
            }
            for i in 0..exact.len() {
                writeln!(
                    maps,
                    "{},{},{},{},{},{},{:.12e},{:.12e},{:.12e},{:.12e},{:.12e}",
                    sz.width,
                    sz.height,
                    case.name,
                    k,
                    i % sizes[k].width,
                    i / sizes[k].width,
                    exact[i],
                    computed[i],
                    current[i],
                    omitted[i],
                    shifted[i]
                )
                .unwrap();
            }
        }
    }
    assert!(max_wrong_cross > 0.05, "omitted-cross foil did not fail");
    assert!(max_shift > 0.05, "shift foil did not fail");
    for k in 0..nb {
        assert!(oracle[1][k].iter().all(|x| *x == 0.0));
        for (a, b) in oracle[0][k].iter().zip(&oracle[7][k]) {
            assert!((17.0 * a - b).abs() < 1e-8, "variance scaling failed");
        }
    }
    let mc:Vec<_>=[0usize,2,4,6].iter().map(|&ci|json!({"case":cases[ci].name,"results":repetitions(&cases[ci].v,&oracle[ci],&sizes,trials,0x1357_2468_abcd_0000+ci as u64+sz.pixels() as u64)})).collect();
    json!({"width":sz.width,"height":sz.height,"bands":nb,"beta":beta.all(),"consumer":consumer,"consumer_corner":consumer_corner,"max_separable_relative_error":max_composed,"max_omitted_cross_foil_relative_error":max_wrong_cross,"max_shift_foil_relative_error":max_shift,"zero_and_scale_controls_passed":true,"comparisons":rows,"independent_uniform_repetitions":mc})
}

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let mut args = std::env::args().skip(1);
    let mut out = None;
    let mut shapes = Vec::new();
    let mut trials = 0usize;
    while let Some(arg) = args.next() {
        match arg.as_str() {
            "--out" => out = Some(PathBuf::from(args.next().ok_or("--out value missing")?)),
            "--size" => {
                let arg = args.next().ok_or("--size value missing")?;
                let (w, h) = arg.split_once('x').ok_or("size must be WxH")?;
                let width = w.parse::<usize>()?;
                let height = h.parse::<usize>()?;
                if !(16..=96).contains(&width) || !(16..=96).contains(&height) {
                    return Err("dimensions must be 16..96".into());
                }
                shapes.push(LevelSize { width, height });
            }
            "--trials" => {
                trials = args.next().ok_or("--trials missing")?.parse()?;
                if trials > 4096 {
                    return Err("trials limit4096".into());
                }
            }
            _ => return Err(format!("unknown argument {arg}").into()),
        }
    }
    let out =
        out.ok_or("usage: noise-floor-oracle --out DIRECTORY [--size 32x32] [--trials 128]")?;
    if shapes.is_empty() {
        shapes = vec![
            LevelSize {
                width: 32,
                height: 32,
            },
            LevelSize {
                width: 33,
                height: 31,
            },
            LevelSize {
                width: 64,
                height: 64,
            },
        ];
    }
    fs::create_dir_all(&out)?;
    let mut maps = BufWriter::new(File::create(out.join("noise-floor-maps.csv"))?);
    writeln!(
        maps,
        "width,height,case,band,x,y,impulse_oracle,separable,current_beta_gaussian,omitted_cross_foil,shifted_variance_foil"
    )?;
    let mut result = Vec::new();
    for sz in shapes {
        eprintln!(
            "noise-floor oracle {}x{}; independent draws={trials}",
            sz.width, sz.height
        );
        result.push(run_size(sz, trials, &mut maps));
    }
    maps.flush()?;
    let report = json!({"status":"MEASURED","scope":"identity linear guide only; independent level0 variance; no sensor calibration or photographic claim","source_base":"0d466788f46477ad31a5cdc264b93f7548d53b9e","exact_tolerance_relative":EXACT_REL_TOL,"trials":trials,"rayon_num_threads":std::env::var("RAYON_NUM_THREADS").ok(),"shapes":result});
    fs::write(
        out.join("noise-floor-results.json"),
        serde_json::to_vec_pretty(&report)?,
    )?;
    eprintln!(
        "all deterministic algebra and consumer controls passed; beta discrepancies reported without renormalization"
    );
    Ok(())
}
