// Bounded generated actual-gather falsifier. Compiled only into CLI tests.
// No RAW input, alternate gather, alignment fit, or photographic quality claim.
use super::*;
use serde_json::{Value, json};
use sha2::{Digest, Sha256};
use std::fs;
use std::sync::Mutex;
use strehl_core::align::{Similarity, SimilarityParams};
use strehl_core::noise::{PlaneNoise, Provenance as NoiseProvenance};
use strehl_core::pyramid::{
    BandObservation, Fallback, FoldPhase, LevelSize, MergeObserver, Pyramid,
};
use strehl_core::spatial_noise_floor::{Mode, Plan};
use strehl_raw::Region;

const SIDE: usize = 144;
const ANALYSIS_SIDE: usize = SIDE / 2 - 8;
const BANDS: usize = 2;
const GROUP: usize = 8;
const SEED: u64 = 0xded9_2026_1024_0001;
const MODES: [Mode; 4] = [Mode::Off, Mode::On, Mode::Shift, Mode::Smooth];
const ARM_NAMES: [&str; 4] = ["current", "normalized", "shift_placebo", "variance_smooth"];
const REGIONS: [&str; 9] = [
    "all",
    "interior",
    "border",
    "centre_neighbourhood",
    "left_border_neighbourhood",
    "even_even",
    "odd_even",
    "even_odd",
    "odd_odd",
];

#[derive(Clone)]
struct Seen {
    energy: Vec<f32>,
    variance: Vec<f32>,
    admitted: Vec<bool>,
    multiplier: f32,
}
#[derive(Default)]
struct Trace(Mutex<Vec<Seen>>);
impl MergeObserver for Trace {
    fn phase(&self, _: FoldPhase) {}
    fn band(&self, band: BandObservation<'_>) {
        if let (Some(energy), Some(variance)) = (band.energy, band.variance) {
            self.0.lock().unwrap().push(Seen {
                energy: energy.to_vec(),
                variance: variance.to_vec(),
                admitted: band.weights.iter().map(|&w| w > 0.0).collect(),
                multiplier: band.floor_multiplier,
            });
        }
    }
}
struct Runner {
    merge: BandMerge,
    workspace: FrameWorkspace,
}
impl Runner {
    fn new(size: LevelSize, mode: Mode) -> Self {
        let cfg = MergeConfig {
            bands: BANDS,
            gate: 2.0,
            exponent: 2.0,
            sharpen_per_octave: 1.4,
            mean_coarse: 0,
            significance_scale: 0.0,
            admission: AdmissionMode::HardFloor,
            base: BaseBand::Mean,
            fallback: Fallback::Mean,
            ..MergeConfig::default()
        };
        let merge = BandMerge::new(size.width, size.height, 1, cfg);
        let mut workspace = FrameWorkspace::new(merge.sizes(), 1);
        workspace.set_spatial_noise_floor_mode(mode);
        Self { merge, workspace }
    }
    fn fold(&mut self, luma: &[f32], variance: &[f32], beta: &[f32]) -> Vec<Seen> {
        self.workspace.next_frame();
        let trace = Trace::default();
        self.merge.add_frame_with_gain_observed(
            &[luma],
            luma,
            variance,
            Some(beta),
            &mut self.workspace,
            &trace,
        );
        trace.0.into_inner().unwrap()
    }
    fn averaging(&self) -> Vec<Vec<bool>> {
        let mut result = Vec::new();
        self.merge.observe_accumulator(|o| {
            if o.level < BANDS {
                result.push((0..o.size.pixels()).map(|i| o.averaging(i)).collect());
            }
        });
        result
    }
}

#[derive(Clone, Copy, Default)]
struct Moments {
    n: usize,
    mean: f64,
    m2: f64,
}
impl Moments {
    fn add(&mut self, value: f64) {
        self.n += 1;
        let delta = value - self.mean;
        self.mean += delta / self.n as f64;
        self.m2 += delta * (value - self.mean);
    }
    fn se(&self) -> f64 {
        if self.n < 2 {
            0.0
        } else {
            (self.m2 / ((self.n - 1) * self.n) as f64).sqrt()
        }
    }
    fn json(&self) -> Value {
        json!({"mean":self.mean,"temporal_se":self.se(),"independent_pairs":self.n})
    }
}
struct Rng(u64);
impl Rng {
    fn uniform(&mut self) -> f64 {
        self.0 = self.0.wrapping_add(0x9e37_79b9_7f4a_7c15);
        let mut z = self.0;
        z = (z ^ (z >> 30)).wrapping_mul(0xbf58_476d_1ce4_e5b9);
        z = (z ^ (z >> 27)).wrapping_mul(0x94d0_49bb_1331_11eb);
        z ^= z >> 31;
        ((z >> 11) as f64 + 0.5) / ((1u64 << 53) as f64)
    }
    fn normal_pair(&mut self) -> (f64, f64) {
        let r = (-2.0 * self.uniform().ln()).sqrt();
        let theta = std::f64::consts::TAU * self.uniform();
        (r * theta.cos(), r * theta.sin())
    }
}
fn noise(read_dominant: bool) -> NoiseModel {
    let plane = PlaneNoise {
        gain_dn_per_e: if read_dominant { 0.001 } else { 0.5 },
        read_noise_e: if read_dominant { 20_000.0 } else { 4.0 },
        levels: Levels {
            black: 512.0,
            white: 15_360.0,
        },
    };
    NoiseModel::new([plane; 4], 100.0, NoiseProvenance::Fallback)
}
fn clean_frame(pattern: &str) -> Frame {
    let mut data = vec![0; SIDE * SIDE];
    for y in 0..SIDE {
        for x in 0..SIDE {
            let signal: f64 = match pattern {
                "flat_read" | "flat_shot" => 2000.0,
                "step_up" if x >= SIDE / 2 => 10000.0,
                "step_down" if x < SIDE / 2 => 10000.0,
                "spike_even" if x == SIDE / 2 && y == SIDE / 2 => 10000.0,
                "spike_odd" if x == SIDE / 2 + 1 && y == SIDE / 2 => 10000.0,
                // At the left compact-pyramid boundary, still inside valid source support.
                "border_spike" if x == 9 && y == SIDE / 2 => 10000.0,
                "weak_texture" => 2000.0 + 40.0 * (x as f64 * 0.8).sin() * (y as f64 * 0.6).cos(),
                _ => 2000.0,
            };
            data[y * SIDE + x] = (512.0 + signal).round() as u16;
        }
    }
    Frame {
        data,
        stride: SIDE,
        buffer_height: SIDE,
        active: Region {
            x: 0,
            y: 0,
            width: SIDE,
            height: SIDE,
        },
        levels: Levels {
            black: 512.0,
            white: 15_360.0,
        },
        iso: Some(100.0),
        wb_coeffs: [2.861, 1.0, 1.482, f32::NAN],
        xyz_to_cam_rgbe: [[0.0; 3]; 4],
        color_matrices: Vec::new(),
        camera: "REA covariance synthetic fixture".into(),
        path: PathBuf::from("REA-NO-SUCH-SYNTHETIC-RAW.ARW"),
    }
}
fn noisy_frame(clean: &Frame, model: &NoiseModel, rng: &mut Rng) -> (Frame, f64, usize) {
    let mut frame = clean.clone();
    let plane = model.plane(CfaPlane::G1);
    let mut normalized_square = 0.0;
    let mut clipped = 0;
    for (sample, &truth) in frame.data.iter_mut().zip(&clean.data) {
        let signal = f64::from(truth) - f64::from(plane.levels.black);
        let (read, shot) = rng.normal_pair();
        let delta = read * f64::from(plane.read_floor_dn())
            + shot * (f64::from(plane.gain_dn_per_e) * signal).sqrt();
        let value = (f64::from(truth) + delta).round();
        clipped += usize::from(value <= 0.0 || value >= f64::from(u16::MAX));
        *sample = value.clamp(0.0, f64::from(u16::MAX)) as u16;
        normalized_square += (f64::from(*sample) - f64::from(truth)).powi(2)
            / f64::from(plane.variance(signal as f32));
    }
    (frame, normalized_square / frame_pixels() as f64, clipped)
}
fn frame_pixels() -> usize {
    SIDE * SIDE
}

fn gather(
    mut frame: Frame,
    transform: Similarity,
    domain: PyramidDomain,
    scratch: &mut WarpScratch,
) -> Result<(Vec<f32>, usize)> {
    // Production dispatch, production demosaic/resampler/u16 rounding, production extraction.
    // No alternate implementation of interpolation is present in this fixture.
    align_cmd::warp_frame_in_place(
        &mut frame,
        transform,
        domain.full,
        Resampler::CatmullRom,
        scratch,
    )?;
    let n = domain.analysis().pixels();
    let mut planes = vec![vec![0.0; n]; 2];
    extract_planes(
        &frame.data,
        frame.stride,
        frame.active.x,
        frame.active.y,
        frame.levels.black,
        domain,
        &BAND_PLANE_OFFSETS[1..3],
        &mut planes,
    )?;
    let clamped = planes.iter().flatten().filter(|&&x| x <= 0.0).count();
    Ok((
        (0..n)
            .map(|i| 0.5 * (planes[0][i] + planes[1][i]))
            .collect(),
        clamped,
    ))
}
fn pyramid(src: &[f32], sizes: &[LevelSize], gaussian: bool) -> Pyramid {
    let mut result = Pyramid::zeros(sizes);
    let mut workspace = Workspace::new(sizes);
    if gaussian {
        result.build_gaussian(src, &mut workspace);
    } else {
        result.build(src, &mut workspace);
    }
    result
}
// Scalar energy-statistic oracle, commissioned against the production observer.
// This copies no gather, variance transport, or gate implementation.
fn smooth(values: &[f32], size: LevelSize) -> Vec<f32> {
    let kernel = [0.0625f32, 0.25, 0.375, 0.25, 0.0625];
    let mut tmp = vec![0.0; size.pixels()];
    let mut result = vec![0.0; size.pixels()];
    for y in 0..size.height {
        for x in 0..size.width {
            for (t, &k) in kernel.iter().enumerate() {
                let xx = (x as isize + t as isize - 2).clamp(0, size.width as isize - 1) as usize;
                tmp[y * size.width + x] += k * values[y * size.width + xx];
            }
        }
    }
    for y in 0..size.height {
        for (t, &k) in kernel.iter().enumerate() {
            let yy = (y as isize + t as isize - 2).clamp(0, size.height as isize - 1) as usize;
            for x in 0..size.width {
                result[y * size.width + x] += k * tmp[yy * size.width + x];
            }
        }
    }
    result
}
fn energy(values: &[f32], size: LevelSize) -> Vec<f32> {
    smooth(&values.iter().map(|v| v * v).collect::<Vec<_>>(), size)
}
fn region_masks(size: LevelSize) -> Vec<Vec<usize>> {
    (0..REGIONS.len())
        .map(|region| {
            (0..size.pixels())
                .filter(|&i| {
                    let (x, y) = (i % size.width, i / size.width);
                    let border = x < 4 || y < 4 || x + 4 >= size.width || y + 4 >= size.height;
                    let centre =
                        x.abs_diff(size.width / 2) <= 4 && y.abs_diff(size.height / 2) <= 4;
                    match region {
                        0 => true,
                        1 => !border,
                        2 => border,
                        3 => centre,
                        4 => x < 5 && y.abs_diff(size.height / 2) <= 4,
                        5 => x % 2 == 0 && y % 2 == 0,
                        6 => x % 2 == 1 && y % 2 == 0,
                        7 => x % 2 == 0 && y % 2 == 1,
                        _ => x % 2 == 1 && y % 2 == 1,
                    }
                })
                .collect()
        })
        .collect()
}
fn mean(values: &[f32], indices: &[usize]) -> f64 {
    indices.iter().map(|&i| f64::from(values[i])).sum::<f64>() / indices.len() as f64
}
fn digest(bytes: &[u8]) -> String {
    Sha256::digest(bytes)
        .iter()
        .map(|b| format!("{b:02x}"))
        .collect()
}
fn effective(plan: &Plan, variance: &[f32], sizes: &[LevelSize], mode: Mode) -> Vec<Vec<f32>> {
    if mode == Mode::Off {
        let p = pyramid(variance, sizes, true);
        (0..BANDS).map(|k| p.level(k).to_vec()).collect()
    } else {
        plan.transport(variance, mode)
    }
}

struct ArmTotals {
    floor: Vec<Vec<f64>>,
    admitted: Vec<Vec<usize>>,
    group_any: Vec<Vec<bool>>,
    fallback: Vec<Vec<usize>>,
    errors: Vec<Vec<Moments>>,
    error_square: Vec<Vec<f64>>,
}
impl ArmTotals {
    fn new(sizes: &[LevelSize]) -> Self {
        Self {
            floor: sizes[..BANDS]
                .iter()
                .map(|s| vec![0.0; s.pixels()])
                .collect(),
            admitted: sizes[..BANDS].iter().map(|s| vec![0; s.pixels()]).collect(),
            group_any: sizes[..BANDS]
                .iter()
                .map(|s| vec![false; s.pixels()])
                .collect(),
            fallback: sizes[..BANDS].iter().map(|s| vec![0; s.pixels()]).collect(),
            errors: vec![vec![Moments::default(); REGIONS.len()]; BANDS],
            error_square: sizes[..BANDS]
                .iter()
                .map(|s| vec![0.0; s.pixels()])
                .collect(),
        }
    }
    fn finish_group(&mut self, actual: Option<&[Vec<bool>]>) {
        for k in 0..BANDS {
            for i in 0..self.group_any[k].len() {
                let fallback = !self.group_any[k][i];
                if let Some(actual) = actual {
                    assert_eq!(actual[k][i], fallback);
                }
                self.fallback[k][i] += usize::from(fallback);
                self.group_any[k][i] = false;
            }
        }
    }
}

#[allow(clippy::too_many_arguments)]
fn run_case(
    pattern: &str,
    geometry: &str,
    transform: Similarity,
    trials: usize,
    case_index: usize,
    domain: PyramidDomain,
    sizes: &[LevelSize],
    output: &Path,
) -> Result<Value> {
    let clean = clean_frame(pattern);
    let model = noise(pattern == "flat_read");
    let mut scratch = WarpScratch::new(domain.full);
    let (reference, reference_clamped) = gather(clean.clone(), transform, domain, &mut scratch)?;
    let reference_pyramid = pyramid(&reference, sizes, false);
    let mut frozen_v = vec![0.0; reference.len()];
    luma_variance(&reference, &model, &mut frozen_v);
    let mut probe = gatefloor::Probe::new(domain, BANDS + 1);
    let raw_beta = probe
        .measure(&clean, 37, transform, Resampler::CatmullRom, &mut scratch)?
        .to_vec();
    let beta: Vec<_> = raw_beta
        .iter()
        .copied()
        .take_while(|b| b.is_finite())
        .collect();
    ensure!(
        beta.len() == BANDS,
        "tiny actual probe did not certify both bands: {raw_beta:?}"
    );
    let plan = Plan::new(sizes);
    let frozen: Vec<_> = MODES
        .iter()
        .map(|&m| effective(&plan, &frozen_v, sizes, m))
        .collect();
    let regions: Vec<_> = sizes[..BANDS].iter().map(|&s| region_masks(s)).collect();
    let mut arms: Vec<_> = (0..8).map(|_| ArmTotals::new(sizes)).collect();
    let mut runners: Vec<_> = MODES.iter().map(|&m| Runner::new(sizes[0], m)).collect();
    let mut truth_sum: Vec<_> = sizes[..BANDS]
        .iter()
        .map(|s| vec![0.0f64; s.pixels()])
        .collect();
    let mut residual_sum = truth_sum.clone();
    let mut truth_square = truth_sum.clone();
    let mut truth_stats = vec![vec![Moments::default(); REGIONS.len()]; BANDS];
    let mut residual_stats = truth_stats.clone();
    let mut wrong_double_floor = truth_stats.clone();
    let mut source_variance_ratio = Moments::default();
    let mut input_clipped = 0;
    let mut gathered_clamped = 0;
    let mut oracle_max_error = 0.0f32;
    let mut observed_variance_max_error = 0.0f32;
    let mut rng = Rng(SEED.wrapping_add((case_index as u64).wrapping_mul(0x10000001)));
    for trial in 0..trials {
        let (fa, va, ca) = noisy_frame(&clean, &model, &mut rng);
        let (fb, vb, cb) = noisy_frame(&clean, &model, &mut rng);
        source_variance_ratio.add(0.5 * (va + vb));
        input_clipped += ca + cb;
        let (a, ac) = gather(fa, transform, domain, &mut scratch)?;
        let (b, bc) = gather(fb, transform, domain, &mut scratch)?;
        gathered_clamped += ac + bc;
        let ap = pyramid(&a, sizes, false);
        let bp = pyramid(&b, sizes, false);
        let mut noisy_v = vec![0.0; a.len()];
        luma_variance(&a, &model, &mut noisy_v);
        let seen: Vec<_> = runners
            .iter_mut()
            .map(|r| r.fold(&a, &noisy_v, &beta))
            .collect();
        if trial == 0 {
            // Commission all four actual effective fields and all fixed-V gates.
            for mode in 0..4 {
                let expected_noisy = effective(&plan, &noisy_v, sizes, MODES[mode]);
                let mut fixed_runner = Runner::new(sizes[0], MODES[mode]);
                let fixed_seen = fixed_runner.fold(&a, &frozen_v, &beta);
                for k in 0..BANDS {
                    for i in 0..sizes[k].pixels() {
                        observed_variance_max_error = observed_variance_max_error
                            .max((expected_noisy[k][i] - seen[mode][k].variance[i]).abs());
                        assert_eq!(
                            expected_noisy[k][i].to_bits(),
                            seen[mode][k].variance[i].to_bits()
                        );
                        assert_eq!(
                            frozen[mode][k][i].to_bits(),
                            fixed_seen[k].variance[i].to_bits()
                        );
                        assert_eq!(
                            fixed_seen[k].admitted[i],
                            fixed_seen[k].energy[i] > fixed_seen[k].multiplier * frozen[mode][k][i]
                        );
                    }
                }
            }
        }
        for k in 0..BANDS {
            let size = sizes[k];
            // Difference of two independent noisy gathers removes deterministic signal.
            // Difference to the noiseless gathered source separately exposes bias/nonlinearity.
            let difference: Vec<_> = ap
                .level(k)
                .iter()
                .zip(bp.level(k))
                .map(|(x, y)| (x - y) * std::f32::consts::FRAC_1_SQRT_2)
                .collect();
            let residual: Vec<_> = ap
                .level(k)
                .iter()
                .zip(reference_pyramid.level(k))
                .map(|(x, y)| x - y)
                .collect();
            let truth = energy(&difference, size);
            let residual_energy = energy(&residual, size);
            let signal_plus_noise = energy(ap.level(k), size);
            for i in 0..size.pixels() {
                oracle_max_error =
                    oracle_max_error.max((signal_plus_noise[i] - seen[0][k].energy[i]).abs());
                assert_eq!(
                    signal_plus_noise[i].to_bits(),
                    seen[0][k].energy[i].to_bits(),
                    "energy statistic oracle does not match actual merge"
                );
                truth_sum[k][i] += f64::from(truth[i]);
                truth_square[k][i] += f64::from(truth[i]).powi(2);
                residual_sum[k][i] += f64::from(residual_energy[i]);
            }
            for r in 0..REGIONS.len() {
                let m = mean(&truth, &regions[k][r]);
                truth_stats[k][r].add(m);
                residual_stats[k][r].add(mean(&residual_energy, &regions[k][r]));
                wrong_double_floor[k][r]
                    .add(2.0 * f64::from(beta[k]) * mean(&frozen[0][k], &regions[k][r]) - m);
            }
            for state in 0..2 {
                for mode in 0..4 {
                    let total = &mut arms[state * 4 + mode];
                    let vv = if state == 0 {
                        &frozen[mode][k]
                    } else {
                        &seen[mode][k].variance
                    };
                    let predicted: Vec<_> = vv.iter().map(|v| beta[k] * v).collect();
                    for i in 0..size.pixels() {
                        let admitted = seen[mode][k].energy[i] > 2.0 * predicted[i];
                        if state == 1 {
                            assert_eq!(admitted, seen[mode][k].admitted[i], "actual gate mismatch");
                            assert_eq!(
                                seen[mode][k].energy[i].to_bits(),
                                seen[0][k].energy[i].to_bits()
                            );
                            assert_eq!(
                                seen[mode][k].multiplier.to_bits(),
                                (2.0 * beta[k]).to_bits()
                            );
                        }
                        total.floor[k][i] += f64::from(predicted[i]);
                        total.error_square[k][i] +=
                            (f64::from(predicted[i]) - f64::from(truth[i])).powi(2);
                        total.admitted[k][i] += usize::from(admitted);
                        total.group_any[k][i] |= admitted;
                    }
                    for r in 0..REGIONS.len() {
                        total.errors[k][r]
                            .add(mean(&predicted, &regions[k][r]) - mean(&truth, &regions[k][r]));
                    }
                }
            }
        }
        if (trial + 1) % GROUP == 0 {
            for mode in 0..4 {
                let actual = runners[mode].averaging();
                arms[mode].finish_group(None);
                arms[4 + mode].finish_group(Some(&actual));
            }
            runners = MODES.iter().map(|&m| Runner::new(sizes[0], m)).collect();
        }
    }
    ensure!(
        input_clipped == 0,
        "noise fixture clipped at sensor storage bounds"
    );
    let mut level_reports = Vec::new();
    let mut summaries = Vec::new();
    for k in 0..BANDS {
        let mut regional = Vec::new();
        for r in 0..REGIONS.len() {
            let measured = truth_stats[k][r];
            let mut estimates = Vec::new();
            for (arm, total) in arms.iter().enumerate() {
                let err = total.errors[k][r];
                let indices = &regions[k][r];
                let admission = indices
                    .iter()
                    .map(|&i| total.admitted[k][i] as f64 / trials as f64)
                    .sum::<f64>()
                    / indices.len() as f64;
                let fallback = indices
                    .iter()
                    .map(|&i| total.fallback[k][i] as f64 / (trials / GROUP) as f64)
                    .sum::<f64>()
                    / indices.len() as f64;
                estimates.push(json!({
                    "variance_source":if arm < 4 {"frozen_noiseless_luma"} else {"actual_noisy_luma"},
                    "arm":ARM_NAMES[arm % 4],"prediction_minus_truth":err.json(),
                    "relative_error":err.mean / measured.mean,
                    "admission_fraction":admission,"eight_frame_mean_fallback_fraction":fallback,
                    "admission_basis":if arm<4 {"counterfactual exact hard-floor inequality, commissioned on first actual fold"} else {"actual observed weights and actual accumulator"},
                }));
            }
            let item = json!({"region":REGIONS[r],"pixels":regions[k][r].len(),
                "temporal_pair_noise_energy":measured.json(),
                "noiseless_reference_residual_energy":residual_stats[k][r].json(),
                "estimates":estimates,"wrong_double_floor_error":wrong_double_floor[k][r].json()});
            regional.push(item);
        }
        let maps: Vec<_> = arms.iter().enumerate().map(|(arm, total)| json!({
            "variance_source":if arm < 4 {"frozen_noiseless_luma"} else {"actual_noisy_luma"},
            "arm":ARM_NAMES[arm%4],
            "predicted_noise_energy_mean":total.floor[k].iter().map(|v| v/trials as f64).collect::<Vec<_>>(),
            "prediction_error_temporal_se":(0..sizes[k].pixels()).map(|i| {
                let sum = total.floor[k][i] - truth_sum[k][i];
                ((total.error_square[k][i] - sum*sum/trials as f64).max(0.0) / (trials*(trials-1)) as f64).sqrt()
            }).collect::<Vec<_>>(),
            "admission_fraction":total.admitted[k].iter().map(|&n| n as f64/trials as f64).collect::<Vec<_>>(),
            "eight_frame_mean_fallback_fraction":total.fallback[k].iter().map(|&n| n as f64/(trials/GROUP) as f64).collect::<Vec<_>>(),
        })).collect();
        summaries.push(json!({"level":k,"regions":regional}));
        level_reports.push(json!({
            "level":k,"size":[sizes[k].width,sizes[k].height],"beta":beta[k],
            "regions":regional,"arms":maps,
            "pair_noise_energy_mean":truth_sum[k].iter().map(|v|v/trials as f64).collect::<Vec<_>>(),
            "pair_noise_energy_temporal_se":(0..sizes[k].pixels()).map(|i| {
                ((truth_square[k][i] - truth_sum[k][i].powi(2)/trials as f64).max(0.0) / (trials*(trials-1)) as f64).sqrt()
            }).collect::<Vec<_>>(),
            "noiseless_reference_residual_energy_mean":residual_sum[k].iter().map(|v|v/trials as f64).collect::<Vec<_>>(),
            "noiseless_signal_energy":energy(reference_pyramid.level(k),sizes[k]),
        }));
    }
    // Flat controls are executed first. Deliberately doubling a floor must be detectable.
    if pattern.starts_with("flat") {
        let bad = wrong_double_floor[0][1];
        ensure!(
            bad.mean.abs() > 5.0 * bad.se(),
            "known wrong floor was not detected"
        );
        ensure!(
            (source_variance_ratio.mean - 1.0).abs() < 0.03,
            "generated source variance does not match injected model"
        );
        for mode in 1..4 {
            ensure!(
                frozen[mode]
                    .iter()
                    .flatten()
                    .zip(frozen[0].iter().flatten())
                    .all(|(a, b)| (*a - *b).abs() <= 1e-5 * b.abs().max(1.0)),
                "constant-variance arm is not a null"
            );
        }
    }
    let plane = model.plane(CfaPlane::G1);
    let report = json!({
        "schema":"rea-actual-gather-noise-floor-v1","case_index":case_index,
        "pattern":pattern,"geometry":geometry,
        "transform_quad":{"a_re":transform.a.re,"a_im":transform.a.im,"b_re":transform.b.re,"b_im":transform.b.im},
        "native_size":[SIDE,SIDE],"crop_quad":[domain.rect.x,domain.rect.y,domain.rect.width,domain.rect.height],
        "trials_independent_pairs":trials,"group_size":GROUP,"seed":SEED.wrapping_add((case_index as u64).wrapping_mul(0x10000001)),
        "noise":{"gain_dn_per_e":plane.gain_dn_per_e,"read_noise_e":plane.read_noise_e,
            "distribution":"independent Gaussian read and Gaussian shot approximation with exact stated second moments before u16 rounding; no empirical centering/scaling",
            "source_empirical_squared_residual_over_model_variance":source_variance_ratio.json(),
            "sensor_storage_clipped_samples":input_clipped},
        "measured_probe_beta":beta,"probe_index_seed":37,"probe_requested_bands":BANDS+1,"probe_template_wb":[2.861,1.0,1.482],
        "gathered_green_clamped_samples":gathered_clamped,"noiseless_green_clamped_samples":reference_clamped,
        "oracle_max_absolute_energy_error":oracle_max_error,
        "observed_variance_max_absolute_error":observed_variance_max_error,
        "levels":level_reports,
        "interpretation":"Temporal pair energy estimates actual gathered noise; squared deterministic signal is separately reported. Residual-vs-pair disagreement can reveal nonlinearity/bias. Better floor prediction is not evidence of photographic improvement.",
    });
    let file = format!("{case_index:02}-{pattern}-{geometry}.json");
    fs::write(output.join(&file), serde_json::to_vec(&report)?)?;
    Ok(
        json!({"file":file,"pattern":pattern,"geometry":geometry,"beta":beta,
        "source_variance_ratio":source_variance_ratio.json(),"gathered_clamped":gathered_clamped,
        "levels":summaries}),
    )
}

// Reuse one workspace across mode/constant transitions to detect stale effective fields.
fn commission_workspace_transitions(sizes: &[LevelSize]) {
    let luma: Vec<_> = (0..sizes[0].pixels())
        .map(|i| 2000.0 + (i % 11) as f32)
        .collect();
    let variance: Vec<_> = (0..luma.len())
        .map(|i| 100.0 + (i % 17) as f32 * 50.0)
        .collect();
    let constant = vec![731.0; luma.len()];
    let plan = Plan::new(sizes);
    let mut runner = Runner::new(sizes[0], Mode::On);
    for (mode, vv) in [
        (Mode::On, &variance),
        (Mode::Off, &variance),
        (Mode::On, &variance),
        (Mode::On, &constant),
        (Mode::Smooth, &variance),
        (Mode::Shift, &variance),
    ] {
        runner.workspace.set_spatial_noise_floor_mode(mode);
        let expected = effective(&plan, vv, sizes, mode);
        let seen = runner.fold(&luma, vv, &[0.7, 0.07]);
        for k in 0..BANDS {
            assert_eq!(
                seen[k].variance, expected[k],
                "stale effective variance after mode/constant transition"
            );
        }
    }
}

#[test]
#[ignore = "explicit bounded covariance experiment; root schedules build/run and fresh output directory"]
fn actual_gather_covariance_falsifier() -> Result<()> {
    let out = PathBuf::from(
        std::env::var_os("STREHL_GATHER_NOISE_OUT")
            .context("set STREHL_GATHER_NOISE_OUT to a fresh directory outside capture corpora")?,
    );
    ensure!(
        out.is_absolute() && !out.exists(),
        "output must be a new absolute directory"
    );
    let trials: usize = std::env::var("STREHL_GATHER_NOISE_TRIALS")
        .unwrap_or_else(|_| "128".into())
        .parse()?;
    ensure!(
        (16..=256).contains(&trials) && trials % GROUP == 0,
        "trials must be a multiple of8 in16..256"
    );
    ensure!(
        align_cmd::fullres_gather_enabled(),
        "this fixture commissions the normal full-resolution gather"
    );
    ensure!(
        std::env::var("STREHL_FIX_CA").as_deref() == Ok("0"),
        "set STREHL_FIX_CA=0 for synthetic identity"
    );
    ensure!(
        std::env::var("STREHL_GATE_FLOOR_SCALE").is_err(),
        "unset gate-floor scaling"
    );
    ensure!(
        std::env::var("STREHL_GATE_FLOOR").map_or(true, |s| s != "white" && s != "debug"),
        "use the ordinary measured probe"
    );
    let full = PlaneGeometry {
        width: SIDE / 2,
        height: SIDE / 2,
    };
    let domain = PyramidDomain::cropped(
        full,
        align_cmd::CropRect {
            x: 4,
            y: 4,
            width: ANALYSIS_SIDE,
            height: ANALYSIS_SIDE,
        },
    )?;
    let sizes = level_sizes(ANALYSIS_SIDE, ANALYSIS_SIDE, BANDS);
    ensure!(
        sizes.len() == BANDS + 1,
        "fixture does not reach requested pyramid depth"
    );
    commission_workspace_transitions(&sizes);
    let geometries = [
        ("identity", Similarity::IDENTITY),
        (
            "native-half-x",
            Similarity::from_params(SimilarityParams {
                ax: 0.25,
                ..Default::default()
            }),
        ),
        (
            "native-minus-half-x",
            Similarity::from_params(SimilarityParams {
                ax: -0.25,
                ..Default::default()
            }),
        ),
        (
            "native-half-xy",
            Similarity::from_params(SimilarityParams {
                ax: 0.25,
                ay: 0.25,
                ..Default::default()
            }),
        ),
        (
            "m103-rung144",
            Similarity::from_params(SimilarityParams {
                g: 0.94686 - 1.0,
                ..Default::default()
            }),
        ),
        (
            "m103-rung298",
            Similarity::from_params(SimilarityParams {
                g: 0.85714 - 1.0,
                ..Default::default()
            }),
        ),
    ];
    let patterns = [
        "flat_read",
        "flat_shot",
        "step_up",
        "step_down",
        "spike_even",
        "spike_odd",
        "border_spike",
        "weak_texture",
    ];
    fs::create_dir(&out)?;
    let root = PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../..");
    let source_paths = [
        "experiments/rea-a7c2-2026-10-24-c/noise-floor-gather.rs",
        "crates/strehl-cli/src/merge_cmd.rs",
        "crates/strehl-cli/src/merge_cmd/gatefloor.rs",
        "crates/strehl-cli/src/align_cmd.rs",
        "crates/strehl-core/src/pyramid.rs",
        "crates/strehl-core/src/pyramid-observer.rs",
        "crates/strehl-core/src/spatial-noise-floor.rs",
        "crates/strehl-core/src/noise.rs",
        "experiments/M103-halfdrift/data/truth-dense.json",
    ];
    let source_hashes: Vec<_> = source_paths
        .iter()
        .map(|p| -> Result<Value> {
            Ok(json!({"path":p,"sha256":digest(&fs::read(root.join(p))?)}))
        })
        .collect::<Result<_>>()?;
    let executable = std::env::current_exe()?;
    let environment: std::collections::BTreeMap<_, _> = std::env::vars()
        .filter(|(k, _)| k.starts_with("STREHL_") || k == "RAYON_NUM_THREADS")
        .collect();
    let receipt = json!({
        "schema":"rea-actual-gather-noise-floor-plan-v1",
        "status":"RUNNING: summary.json is written only after all cases complete",
        "source_hashes":source_hashes,"executable":executable,
        "executable_sha256":digest(&fs::read(&executable)?),"software":crate::SOFTWARE,
        "environment":environment,"rayon_threads":rayon::current_num_threads(),
        "trials_independent_pairs_per_case":trials,"case_count":patterns.len()*geometries.len(),
        "order":"both flat controls across all geometries before non-flat cases",
        "geometry_source":"M103 truth-dense measured rungs144 and298 plus identity; exact similarity, no alignment estimation. Original scale curvature is retained, no fitted scene correction.",
        "consumer":"actual align_cmd::warp_frame_in_place, extract_planes, gatefloor::Probe, luma_variance, BandMerge observed gate and accumulator. Explicit mode override for all four arms.",
        "source_noise":"single injected NoiseModel per case, independent Gaussian read+shot approximation, u16 CFA storage, no PRNU",
        "se_definition":"standard error across independent trial pairs of regional mean; pixels are not independent replicates",
        "mechanical_controls":"constant-V arm null; wrong 2x floor detected on flat; exact observer energy/effective-V/gate/8-frame fallback correspondence",
        "scientific_result":"No numerical improvement threshold is asserted by this test; use regional bias+SE and held-out photographic controls.",
    });
    fs::write(out.join("plan.json"), serde_json::to_vec_pretty(&receipt)?)?;
    let mut cases = Vec::new();
    for pattern in patterns {
        for &(name, transform) in &geometries {
            let index = cases.len();
            eprintln!(
                "actual gather covariance case {}/{}: {pattern}/{name}",
                index + 1,
                patterns.len() * geometries.len()
            );
            cases.push(run_case(
                pattern, name, transform, trials, index, domain, &sizes, &out,
            )?);
        }
    }
    fs::write(
        out.join("summary.json"),
        serde_json::to_vec_pretty(&json!({
            "schema":"rea-actual-gather-noise-floor-summary-v1","status":"COMPLETE","cases":cases,
            "quality_claim":false,
        }))?,
    )?;
    Ok(())
}
