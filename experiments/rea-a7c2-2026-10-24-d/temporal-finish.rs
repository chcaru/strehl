// d adapter, nested beneath the SHA-bound c reconstruction fixture.
// The only merge, guide filtering and reconstruction implementations are core's.
use super::*;
use strehl_core::pyramid::temporal_energy::{Guide, Mode as TemporalMode, Ready, Ring};

const NAMES: [&str; 4] = ["direct", "ring-off", "temporal", "wrong-neighbor-placebo"];
#[derive(Clone)]
struct Case {
    name: &'static str,
    n: usize,
    kind: &'static str,
    amplitude: f64,
    geometry: &'static str,
    default_exponent: bool,
    constant: bool,
    seed: u64,
}
fn config(case: &Case) -> MergeConfig {
    let mut cfg = recon_config(Hull::InputRange);
    if !case.default_exponent {
        let full = MergeConfig {
            bands: 7,
            exponent: 2.0,
            sharpen_per_octave: 1.4,
            ..cfg
        };
        cfg.exponent = full.exponent_at(2, 7);
    }
    cfg
}
fn transform(case: &Case, original: usize) -> Similarity {
    if case.constant || case.geometry == "identity" {
        return Similarity::IDENTITY;
    }
    if case.geometry == "curved" {
        let scales = [1.0, 0.972665, 0.94686, 0.90907, 0.85714];
        let q = 4.0 * original as f64 / (case.n - 1).max(1) as f64;
        let lo = (q.floor() as usize).min(3);
        let scale = scales[lo] + (scales[lo + 1] - scales[lo]) * (q - lo as f64);
        return Similarity::from_params(SimilarityParams {
            g: scale - 1.0,
            ..Default::default()
        });
    }
    Similarity::from_params(SimilarityParams {
        ax: [0.0, 0.25, -0.25, 0.25][original % 4],
        ay: [0.0, -0.25, 0.25, 0.25][original % 4],
        ..Default::default()
    })
}
fn attenuation(i: usize, peak: usize, broad: bool) -> f64 {
    let sigma = if broad {
        i.abs_diff(peak) as f64 * 0.7
    } else if i == peak {
        0.0
    } else {
        20.0
    };
    (-0.5 * sigma * sigma * 0.8f64.powi(2)).exp()
}
fn latent(case: &Case, x: f64, y: f64, channel: usize, frame: Option<usize>, present: bool) -> f64 {
    let centre = case.n / 2;
    let early = case.n / 4;
    let late = case.n - 1 - early;
    let response = |peak: usize, broad: bool| {
        frame.map_or(1.0, |i| {
            if case.constant {
                1.0
            } else {
                attenuation(i, peak, broad)
            }
        })
    };
    let a = if present { case.amplitude } else { 0.0 };
    let fine = (0.8 * x).cos();
    let fine_y = (0.8 * y + 0.3).cos();
    let base = 2000.0;
    match case.kind {
        "flat" => base,
        "one" => base + a * response(centre, false) * fine,
        "broad" => base + a * response(centre, true) * fine,
        "separated-lobes" => {
            let detail = if x < 72.0 {
                response(early, false) * fine
            } else {
                response(late, false) * fine_y
            };
            base + a * detail
        }
        "two-lobes" => base + a * (response(early, false) * fine + response(late, false) * fine_y),
        "fine-coarse" => {
            let coarse_response = frame.map_or(1.0, |i| {
                let sigma = if i == late { 0.0 } else { 32.0 };
                (-0.5 * sigma * sigma * 0.075f64.powi(2)).exp()
            });
            base + a * response(early, false) * fine + 3.0 * a * coarse_response * (0.075 * y).cos()
        }
        "colored" | "colored-nuisance" => {
            let color = [1.5, 1.0, 1.0, 0.55][channel];
            let detail = a * color * response(centre, true) * (fine + 0.6 * fine_y);
            // The same broad nuisance remains in the detail-present and absent
            // source pair. It is absent from the ideal truth (frame=None).
            let nuisance = if case.kind == "colored-nuisance" && frame.is_some() {
                350.0 * (-((x - 72.0).powi(2) + (y - 72.0).powi(2)) / (2.0 * 18.0f64.powi(2))).exp()
            } else {
                0.0
            };
            base + detail + nuisance
        }
        _ => panic!("unknown temporal scene"),
    }
}
fn temporal_source(case: &Case, original: Option<usize>, present: bool) -> Frame {
    let mut frame = clean_frame("flat_shot");
    frame.wb_coeffs = [1.0, 1.0, 1.0, f32::NAN];
    let t = original.map_or(Similarity::IDENTITY, |i| transform(case, i));
    let inverse = t.invert().unwrap();
    let centre = SIDE as f64 / 4.0;
    for y in 0..SIDE {
        for x in 0..SIDE {
            let (wx, wy) = inverse.apply_at(x as f64 * 0.5, y as f64 * 0.5, centre, centre);
            let channel = match (x % 2, y % 2) {
                (0, 0) => 0,
                (1, 0) => 1,
                (0, 1) => 2,
                _ => 3,
            };
            frame.data[y * SIDE + x] = (512.0
                + latent(case, 2.0 * wx, 2.0 * wy, channel, original, present))
            .round() as u16;
        }
    }
    frame
}
// Geometry and latent focus are independent for this alternate reference.
// Existing primary source generation is unchanged.
fn reference_source(
    case: &Case,
    geometry_index: Option<usize>,
    present: bool,
    omit_fine: bool,
) -> Frame {
    let mut frame = clean_frame("flat_shot");
    frame.wb_coeffs = [1.0, 1.0, 1.0, f32::NAN];
    let t = geometry_index.map_or(Similarity::IDENTITY, |i| transform(case, i));
    let inverse = t.invert().unwrap();
    let centre = SIDE as f64 / 4.0;
    for y in 0..SIDE {
        for x in 0..SIDE {
            let (wx, wy) = inverse.apply_at(x as f64 * 0.5, y as f64 * 0.5, centre, centre);
            let channel = match (x % 2, y % 2) {
                (0, 0) => 0,
                (1, 0) => 1,
                (0, 1) => 2,
                _ => 3,
            };
            let mut value = latent(case, 2.0 * wx, 2.0 * wy, channel, None, present);
            if omit_fine && present {
                if case.kind == "fine-coarse" {
                    value -= case.amplitude * (0.8 * 2.0 * wx).cos();
                } else {
                    value = latent(case, 2.0 * wx, 2.0 * wy, channel, None, false);
                }
            }
            frame.data[y * SIDE + x] = (512.0 + value).round() as u16;
        }
    }
    frame
}
fn transferred_reference(
    case: &Case,
    present: bool,
    domain: PyramidDomain,
) -> Result<Vec<Vec<f32>>> {
    assert_eq!(
        reference_source(case, None, present, false).data,
        temporal_source(case, None, present).data,
        "identity all-sharp helper disagrees with retained ideal source"
    );
    let mut sum = vec![vec![0.0; domain.analysis().pixels()]; 4];
    let mut scratch = WarpScratch::new(domain.full);
    for i in 0..case.n {
        let source = reference_source(case, Some(i), present, false);
        let planes = gather_four(source, transform(case, i), domain, &mut scratch)?;
        for c in 0..4 {
            for j in 0..sum[c].len() {
                sum[c][j] += planes[c][j] / case.n as f32;
            }
        }
    }
    Ok(sum)
}
struct Data {
    planes: Vec<Vec<f32>>,
    luma: Vec<f32>,
    variance: Vec<f32>,
    sha: String,
}
fn data(
    case: &Case,
    repeat: usize,
    original: usize,
    noisy: bool,
    present: bool,
    domain: PyramidDomain,
    scratch: &mut WarpScratch,
) -> Result<Data> {
    let clean = temporal_source(case, Some(original), present);
    let frame = if noisy {
        // Detail presence never changes the standard draws. Removing detail
        // changes shot variance naturally through the SAME injected model.
        let seed = SEED
            .wrapping_add(case.seed)
            .wrapping_add(repeat as u64 * 0x10000001)
            .wrapping_add(original as u64 * 0x10001);
        let (f, _, clipped) = noisy_frame(&clean, &noise(false), &mut Rng(seed));
        ensure!(clipped == 0, "generated sensor noise clipped");
        f
    } else {
        clean
    };
    let mut bytes = Vec::with_capacity(frame.data.len() * 2);
    for &v in &frame.data {
        bytes.extend_from_slice(&v.to_le_bytes());
    }
    let sha = digest(&bytes);
    let planes = gather_four(frame, transform(case, original), domain, scratch)?;
    let luma = luma_of(&planes);
    let mut variance = vec![0.0; luma.len()];
    luma_variance(&luma, &noise(false), &mut variance);
    Ok(Data {
        planes,
        luma,
        variance,
        sha,
    })
}
#[derive(Clone)]
struct BandTrace {
    level: usize,
    energy: Option<Vec<f32>>,
    floor: Option<Vec<f32>>,
    weights: Vec<f32>,
}
#[derive(Default)]
struct TemporalTrace(Mutex<Vec<BandTrace>>);
impl MergeObserver for TemporalTrace {
    fn supports_absolute_floor(&self) -> bool { true }
    fn phase(&self, _: FoldPhase) {}
    fn band(&self, b: BandObservation<'_>) {
        let floor = b.absolute_floor.map(<[f32]>::to_vec).or_else(|| {
            b.variance
                .map(|v| v.iter().map(|&x| b.floor_multiplier * x.max(0.0)).collect())
        });
        self.0.lock().unwrap().push(BandTrace {
            level: b.level,
            energy: b.energy.map(<[f32]>::to_vec),
            floor,
            weights: b.weights.to_vec(),
        });
    }
}
struct Engine {
    merge: BandMerge,
    ws: FrameWorkspace,
    ring: Option<Ring>,
    folded: Vec<usize>,
}
impl Engine {
    fn new(case: &Case, size: LevelSize, mode: Option<TemporalMode>) -> Self {
        let merge = BandMerge::new(size.width, size.height, 4, config(case));
        let mut ws = FrameWorkspace::new(merge.sizes(), 4);
        ws.set_spatial_noise_floor_mode(Mode::Off);
        Self {
            merge,
            ws,
            ring: mode.map(|m| Ring::new(case.n, m)),
            folded: Vec::new(),
        }
    }
    fn original(&mut self, index: usize, d: &Data, beta: &[f32]) -> Vec<BandTrace> {
        self.ws.next_frame();
        let refs: Vec<_> = d.planes.iter().map(Vec::as_slice).collect();
        let trace = TemporalTrace::default();
        self.merge.add_frame_with_gain_observed(
            &refs,
            &d.luma,
            &d.variance,
            Some(beta),
            &mut self.ws,
            &trace,
        );
        self.folded.push(index);
        trace.0.into_inner().unwrap()
    }
    fn ready(&mut self, r: &Ready, d: &Data, beta: &[f32]) -> Vec<BandTrace> {
        let refs: Vec<_> = d.planes.iter().map(Vec::as_slice).collect();
        let trace = TemporalTrace::default();
        self.merge.add_frame_with_temporal_guide(
            r.source_index(),
            &refs,
            &d.luma,
            &d.variance,
            Some(beta),
            &mut self.ws,
            r,
            Some(&trace),
        );
        self.folded.push(r.source_index());
        trace.0.into_inner().unwrap()
    }
    fn coarse(&self) -> Vec<(Vec<f32>, Vec<bool>)> {
        let mut result = Vec::new();
        self.merge.observe_accumulator(|o| {
            if o.level >= 2 {
                result.push((
                    (0..o.size.pixels()).map(|i| o.coefficient(i)).collect(),
                    (0..o.size.pixels()).map(|i| o.averaging(i)).collect(),
                ));
            }
        });
        result
    }
    fn finish(&self) -> Vec<Vec<f32>> {
        self.merge.finish(&mut Workspace::new(self.merge.sizes()))
    }
}
fn compare_trace(raw: &[BandTrace], observed: &[BandTrace], ready: &Ready) {
    assert_eq!(raw.len(), observed.len());
    for (a, b) in raw.iter().zip(observed) {
        assert_eq!(a.level, b.level);
        if a.level >= 2 || ready.is_original() {
            assert_eq!(a.energy, b.energy, "untouched energy changed");
            assert_eq!(a.floor, b.floor, "untouched complete floor changed");
            assert_eq!(a.weights, b.weights, "untouched weights changed");
        } else {
            let band = &ready.bands().unwrap()[a.level];
            assert_eq!(b.energy.as_ref().unwrap(), &band.energy);
            assert_eq!(b.floor.as_ref().unwrap(), &band.floor);
        }
    }
}
struct StackResult {
    outputs: Vec<Vec<Vec<f32>>>,
    diagnostics: Value,
}
#[allow(clippy::too_many_arguments)]
fn stack(
    case: &Case,
    repeat: usize,
    noisy: bool,
    present: bool,
    reverse: bool,
    chunks: &[usize],
    domain: PyramidDomain,
    beta: &[Vec<f32>],
) -> Result<StackResult> {
    let size = LevelSize {
        width: domain.rect.width,
        height: domain.rect.height,
    };
    let modes = [
        None,
        Some(TemporalMode::Off),
        Some(TemporalMode::On),
        Some(TemporalMode::ShiftNeighbors),
    ];
    let mut engines: Vec<_> = modes.iter().map(|&m| Engine::new(case, size, m)).collect();
    let mut scratch = WarpScratch::new(domain.full);
    let mut previous: Option<(usize, Vec<BandTrace>, String)> = None;
    let mut endpoints = vec![0; 4];
    let mut peak = Value::Null;
    let mut weak_mask: Vec<usize> = Vec::new();
    let mut lost_crossings: Vec<usize> = Vec::new();
    let mut retained_max = 0;
    let mut low = vec![vec![f32::INFINITY; size.pixels()]; 4];
    let mut high = vec![vec![f32::NEG_INFINITY; size.pixels()]; 4];
    let mut position = 0;
    let mut chunk = 0;
    while position < case.n {
        let end = (position + chunks[chunk % chunks.len()]).min(case.n);
        for index in position..end {
            let original = if reverse { case.n - 1 - index } else { index };
            let d = data(case, repeat, original, noisy, present, domain, &mut scratch)?;
            for c in 0..4 {
                for i in 0..size.pixels() {
                    low[c][i] = low[c][i].min(d.planes[c][i]);
                    high[c][i] = high[c][i].max(d.planes[c][i]);
                }
            }
            let refs: Vec<_> = d.planes.iter().map(Vec::as_slice).collect();
            let guide: Guide = {
                let first = &mut engines[0];
                first.merge.temporal_guide(
                    index,
                    &refs,
                    &d.luma,
                    &d.variance,
                    Some(&beta[original]),
                    &mut first.ws,
                )
            };
            let raw = engines[0].original(index, &d, &beta[original]);
            if !noisy && present && index == case.n / 2 && case.kind == "one" {
                let energy = raw[0].energy.as_ref().unwrap();
                let floor = raw[0].floor.as_ref().unwrap();
                let interior: Vec<_> = (0..size.pixels())
                    .filter(|&i| {
                        let (x, y) = (i % size.width, i / size.width);
                        x >= 8 && y >= 8 && x + 8 < size.width && y + 8 < size.height
                    })
                    .collect();
                let ratios: Vec<_> = interior
                    .iter()
                    .map(|&i| f64::from(energy[i] / floor[i]))
                    .collect();
                weak_mask = interior
                    .iter()
                    .copied()
                    .filter(|&i| {
                        let ratio = energy[i] / floor[i];
                        ratio > 1.0 && ratio <= 2.0 && raw[0].weights[i] > 0.0
                    })
                    .collect();
                peak = json!({"band0_noiseless_energy_floor_ratio_min":ratios.iter().copied().fold(f64::INFINITY,f64::min),
                    "ratio_max":ratios.iter().copied().fold(f64::NEG_INFINITY,f64::max),
                    "fraction_in_1_to_2":ratios.iter().filter(|&&v|v>1.0&&v<=2.0).count() as f64/ratios.len() as f64,
                    "ratio_mean":ratios.iter().sum::<f64>()/ratios.len() as f64});
            }
            let mut pending = Vec::new();
            for arm in 1..4 {
                let ring = engines[arm].ring.as_mut().unwrap();
                let ready = ring.push(guide.clone());
                retained_max = retained_max.max(ring.retained_guides());
                assert!(
                    ring.retained_guides() <= 3,
                    "guide ring grew with stack length"
                );
                if let Some(ready) = ready {
                    if ready.is_original() {
                        endpoints[arm] += 1;
                    }
                    if ready.source_index() == index {
                        let seen = engines[arm].ready(&ready, &d, &beta[original]);
                        compare_trace(&raw, &seen, &ready);
                    } else {
                        pending.push((arm, ready));
                    }
                }
            }
            let current_sha = d.sha.clone();
            drop(d); // delayed coefficients are gathered at their consumer, never cached.
            if !pending.is_empty() {
                let centre = pending[0].1.source_index();
                assert!(pending.iter().all(|(_, r)| r.source_index() == centre));
                let (prior_index, prior_trace, prior_sha) = previous.as_ref().unwrap();
                assert_eq!(*prior_index, centre, "lost or duplicated lookahead source");
                let original = if reverse { case.n - 1 - centre } else { centre };
                let central = data(case, repeat, original, noisy, present, domain, &mut scratch)?;
                assert_eq!(central.sha, *prior_sha, "central u16 regeneration changed");
                for (arm, ready) in pending {
                    let seen = engines[arm].ready(&ready, &central, &beta[original]);
                    compare_trace(prior_trace, &seen, &ready);
                    if arm == 2 && !noisy && present && case.kind == "one" && centre == case.n / 2 {
                        lost_crossings = weak_mask
                            .iter()
                            .copied()
                            .filter(|&i| seen[0].weights[i] <= 0.0)
                            .collect();
                        let e = seen[0].energy.as_ref().unwrap();
                        let f = seen[0].floor.as_ref().unwrap();
                        let ratios: Vec<_> =
                            weak_mask.iter().map(|&i| f64::from(e[i] / f[i])).collect();
                        peak["actual_positive_direct_sites"] = json!(weak_mask.len());
                        peak["actual_positive_direct_to_zero_on_sites"] =
                            json!(lost_crossings.len());
                        peak["filtered_energy_full_floor_ratio_on_weak_sites"] =
                            if ratios.is_empty() {
                                Value::Null
                            } else {
                                json!({"min":ratios.iter().copied().fold(f64::INFINITY,f64::min),
                                "max":ratios.iter().copied().fold(f64::NEG_INFINITY,f64::max),
                                "mean":ratios.iter().sum::<f64>()/ratios.len() as f64})
                            };
                    }
                }
            }
            previous = Some((index, raw, current_sha));
        }
        position = end;
        chunk += 1;
    }
    for arm in 1..4 {
        if let Some(ready) = engines[arm].ring.as_mut().unwrap().finish() {
            let index = ready.source_index();
            let original = if reverse { case.n - 1 - index } else { index };
            let d = data(case, repeat, original, noisy, present, domain, &mut scratch)?;
            let (last, last_trace, sha) = previous.as_ref().unwrap();
            assert_eq!(*last, index);
            assert_eq!(*sha, d.sha);
            let seen = engines[arm].ready(&ready, &d, &beta[original]);
            compare_trace(last_trace, &seen, &ready);
            endpoints[arm] += usize::from(ready.is_original());
        }
    }
    if !weak_mask.is_empty() {
        for arm in [0usize, 2] {
            engines[arm].merge.observe_accumulator(|o| {
                if o.level==0 {
                    let count=weak_mask.iter().filter(|&&i|o.averaging(i)).count();
                    let lost_count=lost_crossings.iter().filter(|&&i|o.averaging(i)).count();
                    peak[if arm==0 {"direct_final_band0_fallback"} else {"on_final_band0_fallback"}]=
                        json!({"weak_sites":weak_mask.len(),"all_zero_weak_sites":count,
                            "lost_crossing_sites":lost_crossings.len(),"all_zero_lost_crossing_sites":lost_count});
                }
            });
        }
    }
    let order: Vec<_> = (0..case.n).collect();
    let coarse = engines[0].coarse();
    for e in &engines {
        assert_eq!(
            e.folded, order,
            "each source must fold exactly once in declared order"
        );
        assert_eq!(e.coarse(), coarse, "coarser bands/base changed");
    }
    let outputs: Vec<_> = engines.iter().map(Engine::finish).collect();
    for image in &outputs {
        for c in 0..4 {
            for i in 0..size.pixels() {
                ensure!(
                    image[c][i] >= low[c][i] - 0.001 && image[c][i] <= high[c][i] + 0.001,
                    "original input hull was violated"
                );
            }
        }
    }
    assert_eq!(endpoints[1], case.n, "Off must always dispatch legacy");
    assert_eq!(
        endpoints[2],
        case.n.min(2),
        "candidate endpoint/short handling changed"
    );
    assert_eq!(
        endpoints[3],
        case.n.min(2),
        "placebo endpoint/short handling changed"
    );
    assert_eq!(
        outputs[0], outputs[1],
        "disabled ring is not exact legacy finish"
    );
    if case.n < 3 || case.constant {
        assert_eq!(outputs[0], outputs[2], "short/constant stack changed");
    }
    Ok(StackResult {
        outputs,
        diagnostics: json!({"retained_guides_max":retained_max,
        "original_dispatches":endpoints,"folded_exactly_once":true,"coarse_base_exact":true,"original_hull_verified":true,"one_frame_peak":peak}),
    })
}
fn betas(case: &Case, domain: PyramidDomain) -> Result<Vec<Vec<f32>>> {
    let mut scratch = WarpScratch::new(domain.full);
    let mut result: Vec<Vec<f32>> = Vec::new();
    for i in 0..case.n {
        if case.constant && i > 0 {
            result.push(result[0].clone());
            continue;
        }
        let frame = temporal_source(case, Some(i), true);
        let mut p = gatefloor::Probe::new(domain, 3);
        let beta: Vec<_> = p
            .measure(
                &frame,
                37 + i,
                transform(case, i),
                Resampler::CatmullRom,
                &mut scratch,
            )?
            .iter()
            .copied()
            .take_while(|b| b.is_finite())
            .collect();
        ensure!(beta.len() >= 2, "two changed bands need finite actual beta");
        result.push(beta);
    }
    Ok(result)
}
fn truth(case: &Case, present: bool, domain: PyramidDomain) -> Result<Vec<Vec<f32>>> {
    gather_four(
        temporal_source(case, None, present),
        Similarity::IDENTITY,
        domain,
        &mut WarpScratch::new(domain.full),
    )
}
fn percentile(values: &mut [f64], q: f64) -> f64 {
    values.sort_by(f64::total_cmp);
    values[((values.len() - 1) as f64 * q).round() as usize]
}
fn tails(image: &[Vec<f32>], reference: &[Vec<f32>]) -> [f64; 5] {
    let mut errors: Vec<_> = image
        .iter()
        .zip(reference)
        .flat_map(|(a, b)| a.iter().zip(b).map(|(x, y)| f64::from((x - y).abs())))
        .collect();
    let frac = errors.iter().filter(|&&e| e > 20.0).count() as f64 / errors.len() as f64;
    [
        percentile(&mut errors, 0.99),
        percentile(&mut errors, 0.999),
        *errors.last().unwrap(),
        frac,
        errors.iter().filter(|&&e| e > 40.0).count() as f64 / errors.len() as f64,
    ]
}
fn subtract(a: &[Vec<f32>], b: &[Vec<f32>]) -> Vec<Vec<f32>> {
    a.iter()
        .zip(b)
        .map(|(x, y)| x.iter().zip(y).map(|(a, b)| a - b).collect())
        .collect()
}
fn max_difference_in(a: &[Vec<f32>], b: &[Vec<f32>], indices: &[usize]) -> f32 {
    a.iter()
        .zip(b)
        .flat_map(|(x, y)| indices.iter().map(move |&i| (x[i] - y[i]).abs()))
        .fold(0.0, f32::max)
}
fn max_difference(a: &[Vec<f32>], b: &[Vec<f32>]) -> f32 {
    a.iter()
        .flatten()
        .zip(b.iter().flatten())
        .map(|(x, y)| (x - y).abs())
        .fold(0.0, f32::max)
}
#[allow(clippy::too_many_arguments)]
fn run_case(case: &Case, repeats: usize, domain: PyramidDomain, out: &Path) -> Result<Value> {
    let size = LevelSize {
        width: domain.rect.width,
        height: domain.rect.height,
    };
    let reference = truth(case, true, domain)?;
    let background = truth(case, false, domain)?;
    let difference_truth = subtract(&reference, &background);
    let mut regions = recon_regions(size, "step_lines");
    // Primary placebo interpretation excludes its circular-wrap footprint.
    // At level0, the maximum x shift is8; twelve quad pixels also leave
    // the spatial energy filter's support clear of the wrap seam.
    regions[1] = (0..size.pixels())
        .filter(|&i| {
            let (x, y) = (i % size.width, i / size.width);
            x >= 12 && x + 12 < size.width && y >= 4 && y + 4 < size.height
        })
        .collect();
    if case.kind == "separated-lobes" {
        for (slot, left, right) in [(2usize, 32.0, 56.0), (4usize, 88.0, 112.0)] {
            regions[slot] = (0..size.pixels())
                .filter(|&i| {
                    let (x, y) = (
                        8.0 + 2.0 * (i % size.width) as f64,
                        8.0 + 2.0 * (i / size.width) as f64,
                    );
                    x >= left && x < right && y >= 24.0 && y < 120.0
                })
                .collect();
        }
    }
    let beta = betas(case, domain)?;
    let folder = out.join(case.name);
    fs::create_dir(&folder)?;
    let reference_file = save_output(&folder, "truth", &reference, size)?;
    let transferred = transferred_reference(case, true, domain)?;
    let transferred_absent = transferred_reference(case, false, domain)?;
    let transferred_difference = subtract(&transferred, &transferred_absent);
    let transferred_file = save_output(&folder, "all-sharp-same-gather-mean", &transferred, size)?;
    let fine_background = gather_four(
        reference_source(case, None, true, true),
        Similarity::IDENTITY,
        domain,
        &mut WarpScratch::new(domain.full),
    )?;
    let fine_component = subtract(&reference, &fine_background);
    let zeros = vec![vec![0.0; size.pixels()]; 4];
    let fine_foil: Vec<_> = fine_component
        .iter()
        .map(|p| smooth(&smooth(p, size), size))
        .collect();
    let fine_foil_projection = projection(&fine_foil, &fine_component, &zeros, &regions[2]);

    let foil: Vec<_> = reference
        .iter()
        .map(|p| smooth(&smooth(p, size), size))
        .collect();
    if case.kind != "flat" {
        ensure!(
            mse(&fine_foil, &fine_component, &regions[2]) > 1.0,
            "blur foil failed to expose isolated fine-detail loss"
        );
        ensure!(
            fine_foil_projection.is_some_and(|p| p < 0.8),
            "blur foil retained isolated fine-component projection"
        );
    }
    let mut stats: Vec<_> = (0..4).map(|_| ImageStats::new(size)).collect();
    let mut tail_stats = vec![vec![Moments::default(); 5]; 4];
    let mut causal = vec![vec![Moments::default(); RECON_REGIONS.len()]; 4];
    let mut causal_delta = causal.clone();
    let mut transfer_error = causal.clone();
    let mut transfer_delta = causal.clone();
    let mut transfer_causal = causal.clone();
    let mut placebo_delta = Moments::default();
    let mut first = Vec::new();
    let noiseless = stack(case, 0, false, true, false, &[case.n], domain, &beta)?;
    let reversed = stack(case, 0, false, true, true, &[1, 2, 4], domain, &beta)?;
    let segmented = stack(case, 0, false, true, false, &[1, 2, 7, 3], domain, &beta)?;
    for arm in 0..4 {
        assert_eq!(
            noiseless.outputs[arm], segmented.outputs[arm],
            "chunk boundary changed fold result"
        );
        ensure!(
            max_difference(&noiseless.outputs[arm], &reversed.outputs[arm]) < 0.02,
            "symmetric source reversal changed reconstruction beyond f32 summation tolerance"
        );
        save_output(
            &folder,
            &format!("noiseless-{}", NAMES[arm]),
            &noiseless.outputs[arm],
            size,
        )?;
    }
    if case.name == "one-frame-weak" {
        ensure!(
            noiseless.diagnostics["one_frame_peak"]["fraction_in_1_to_2"]
                .as_f64()
                .unwrap()
                > 0.25,
            "prescribed weak peak did not exercise actual 1<E/F<=2 on a material interior region"
        );
    }
    for repeat in 0..repeats {
        let actual = stack(case, repeat, true, true, false, &[7, 1, 13], domain, &beta)?;
        let absent = if case.kind == "flat" {
            None
        } else {
            Some(stack(
                case,
                repeat,
                true,
                false,
                false,
                &[7, 1, 13],
                domain,
                &beta,
            )?)
        };
        placebo_delta.add(f64::from(max_difference_in(
            &actual.outputs[2],
            &actual.outputs[3],
            &regions[1],
        )));
        for arm in 0..4 {
            stats[arm].add(
                &actual.outputs[arm],
                &reference,
                &background,
                &background,
                &actual.outputs[0],
                &regions,
            );
            for (r, indices) in regions.iter().enumerate() {
                let err = mse(&actual.outputs[arm], &transferred, indices);
                transfer_error[arm][r].add(err);
                transfer_delta[arm][r].add(err - mse(&actual.outputs[0], &transferred, indices));
            }
            for (i, value) in tails(&actual.outputs[arm], &reference)
                .into_iter()
                .enumerate()
            {
                tail_stats[arm][i].add(value);
            }
            if let Some(absent) = &absent {
                let recovered = subtract(&actual.outputs[arm], &absent.outputs[arm]);
                for (r, indices) in regions.iter().enumerate() {
                    let error = mse(&recovered, &difference_truth, indices);
                    causal[arm][r].add(error);
                    transfer_causal[arm][r].add(mse(&recovered, &transferred_difference, indices));
                    let baseline = subtract(&actual.outputs[0], &absent.outputs[0]);
                    causal_delta[arm][r].add(error - mse(&baseline, &difference_truth, indices));
                }
            }
            if repeat == 0 {
                first.push(save_output(
                    &folder,
                    &format!("first-{}", NAMES[arm]),
                    &actual.outputs[arm],
                    size,
                )?);
            }
        }
    }
    let mut arms = Vec::new();
    for arm in 0..4 {
        let (mean, metrics) = stats[arm].finish(&reference, &regions, repeats);
        let file = save_output(&folder, &format!("mean-{}", NAMES[arm]), &mean, size)?;
        arms.push(json!({"arm":NAMES[arm],"metrics":metrics,"first":first[arm],"mean":file,
            "tail_statistics":{"p99_absolute_dn":repeat_moments(&tail_stats[arm][0]),
                "p999_absolute_dn":repeat_moments(&tail_stats[arm][1]),"max_absolute_dn":repeat_moments(&tail_stats[arm][2]),
                "fraction_absolute_error_over20dn":repeat_moments(&tail_stats[arm][3]),
                "fraction_absolute_error_over40dn":repeat_moments(&tail_stats[arm][4])},
            "causal_present_minus_absent_mse":causal[arm].iter().enumerate().map(|(r,m)|json!({
                "region":RECON_REGIONS[r],"mse_dn2":repeat_moments(m),"paired_delta_to_direct":repeat_moments(&causal_delta[arm][r]),
                "same_gather_difference_mse":repeat_moments(&transfer_causal[arm][r])})).collect::<Vec<_>>(),
            "noiseless_mse":regions.iter().enumerate().map(|(r,idx)|json!({"region":RECON_REGIONS[r],
                "mse_dn2":mse(&noiseless.outputs[arm],&reference,idx)})).collect::<Vec<_>>(),
            "same_gather_reference_mse":transfer_error[arm].iter().enumerate().map(|(r,m)|json!({
                "region":RECON_REGIONS[r],"mse_dn2":repeat_moments(m),
                "paired_delta_to_direct":repeat_moments(&transfer_delta[arm][r])})).collect::<Vec<_>>(),
            "noiseless_same_gather_reference_mse":regions.iter().enumerate().map(|(r,idx)|json!({
                "region":RECON_REGIONS[r],"mse_dn2":mse(&noiseless.outputs[arm],&transferred,idx)})).collect::<Vec<_>>(),
            "reversal_max_dn":max_difference(&noiseless.outputs[arm],&reversed.outputs[arm])}));
    }
    if case.name == "flat-n5" {
        ensure!(
            placebo_delta.mean > 0.001,
            "shifted-neighbor placebo did not reach actual output"
        );
    }
    let cfg = config(case);
    let report = json!({"case":case.name,"n":case.n,"kind":case.kind,"amplitude_dn":case.amplitude,
        "geometry":case.geometry,"independent_stack_repeats":repeats,"noise":"injected read+Gaussian shot approximation; independent sensor draws across original frame indices",
        "actual_bands":3,"resolved_exponents":(0..3).map(|k|cfg.exponent_at(k,3)).collect::<Vec<_>>(),
        "base_exponent_override":if case.default_exponent {None} else {Some(cfg.exponent)},
        "actual_beta":beta,"truth":reference_file,"same_gather_reference":transferred_file,
        "same_gather_reference_rule":"mean of all-sharp original u16 sources through each actual inverse placement and gather; no source selector",
        "arms":arms,"controls":noiseless.diagnostics,
        "two_lobes_scope":if case.kind=="two-lobes" {Some("overlapping transparent-superposition stress; ideal sum may be unattainable by coefficient averaging")}
            else if case.kind=="separated-lobes" {Some("disjoint left/right fine supports with focus peaks2/6; protected regions exclude the transition")} else {None},
        "separated_depth_protected_windows":if case.kind=="separated-lobes" {
            Some(json!({"detail_left_native":[32,24,24,96],"texture_right_native":[88,24,24,96],"transition_x_native":72}))
        } else {None},
        "fine_foil_projection":fine_foil_projection,"fine_foil_mse":mse(&fine_foil,&fine_component,&regions[2]),
        "mixed_template_foil_projection_diagnostic":projection(&foil,&reference,&background,&regions[2]),
        "blur_foil_detail_mse":mse(&foil,&reference,&regions[2]),
        "on_vs_placebo_interior_max_dn":repeat_moments(&placebo_delta),
        "interior_region_quad":{"x":12,"y":4,"width":size.width-24,"height":size.height-8},
        "tail_scope":"whole image, including borders; primary placebo interpretation uses declared interior",
        "causal_pair":"same standard noise draws, nuisance, geometry and model; detail removal naturally changes shot variance",
        "claim":"generated reconstruction falsifier; not photographic quality or calibrated admission probability"});
    fs::write(
        folder.join("report.json"),
        serde_json::to_vec_pretty(&report)?,
    )?;
    Ok(report)
}
fn case(name: &'static str, n: usize, kind: &'static str, amplitude: f64, seed: u64) -> Case {
    Case {
        name,
        n,
        kind,
        amplitude,
        geometry: "phase",
        default_exponent: false,
        constant: false,
        seed,
    }
}
#[test]
#[ignore = "root schedules fixed temporal evidence screen; new absolute output directory required"]
fn temporal_finish_falsifier() -> Result<()> {
    let out = PathBuf::from(
        std::env::var_os("STREHL_TEMPORAL_TEST_OUT").context("set STREHL_TEMPORAL_TEST_OUT")?,
    );
    ensure!(
        out.is_absolute() && !out.exists(),
        "fresh absolute output required"
    );
    let repeats: usize = std::env::var("STREHL_TEMPORAL_REPEATS")
        .unwrap_or_else(|_| "16".into())
        .parse()?;
    ensure!([8, 16, 32].contains(&repeats), "repeats must be8,16,32");
    ensure!(
        std::env::var("STREHL_FIX_CA").as_deref() == Ok("0"),
        "synthetic CA must be off"
    );
    ensure!(
        align_cmd::fullres_gather_enabled(),
        "normal fullres gather required"
    );
    ensure!(
        std::env::var("STREHL_GATE_FLOOR_SCALE").is_err(),
        "unset floor scales"
    );
    ensure!(
        std::env::var("STREHL_DEMOSAIC").is_err(),
        "unset demosaic override"
    );
    let root = PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../..");
    let helper_hashes = [
        (
            "noise-floor-gather.rs",
            "59d82721432978bfd60324a5a832ad0ee4b6434257ac909501ce2be0bf3a45cd",
        ),
        (
            "noise-floor-reconstruction.rs",
            "bb7515c9ead0902b5c02217b0fea9ce112d5fb3ec167140240d62850bf9b9f48",
        ),
    ];
    for (name, hash) in helper_hashes {
        let bytes = fs::read(root.join("experiments/rea-a7c2-2026-10-24-c").join(name))?;
        ensure!(
            digest(&bytes) == hash,
            "frozen c helper source changed: {name}"
        );
    }
    let domain = PyramidDomain::cropped(
        PlaneGeometry {
            width: SIDE / 2,
            height: SIDE / 2,
        },
        align_cmd::CropRect {
            x: 4,
            y: 4,
            width: ANALYSIS_SIDE,
            height: ANALYSIS_SIDE,
        },
    )?;
    fs::create_dir(&out)?;
    let mut cases = vec![
        case("flat-n5", 5, "flat", 0.0, 1),
        case("flat-n33", 33, "flat", 0.0, 2),
        case("flat-n299", 299, "flat", 0.0, 3),
        case("one-frame-weak", 9, "one", 55.0, 10),
        case("one-frame-strong", 9, "one", 240.0, 11),
        case("broad-focus", 9, "broad", 120.0, 12),
        case("two-same-band-lobes", 9, "two-lobes", 160.0, 13),
        case(
            "two-spatially-separated-depths",
            9,
            "separated-lobes",
            160.0,
            16,
        ),
        case("near-fine-far-coarse", 9, "fine-coarse", 120.0, 14),
        case("colored-structure", 9, "colored", 120.0, 15),
        case("colored-broad-nuisance", 9, "colored-nuisance", 120.0, 15),
    ];
    let mut risk = case("one-frame-weak-small-default", 9, "one", 55.0, 10);
    risk.default_exponent = true;
    cases.push(risk);
    let mut curved = case("near-fine-far-coarse-curved", 9, "fine-coarse", 120.0, 14);
    curved.geometry = "curved";
    cases.push(curved);
    let sources = [
        "experiments/rea-a7c2-2026-10-24-d/temporal-finish.rs",
        "crates/strehl-core/src/temporal-energy.rs",
        "crates/strehl-core/src/pyramid.rs",
        "crates/strehl-cli/src/merge_cmd.rs",
        "crates/strehl-cli/src/align_cmd.rs",
        "crates/strehl-cli/src/merge_cmd/gatefloor.rs",
    ];
    let hashes: Vec<_> = sources
        .iter()
        .map(|p| -> Result<Value> {
            Ok(json!({"path":p,"sha256":digest(&fs::read(root.join(p))?)}))
        })
        .collect::<Result<_>>()?;
    let exe = std::env::current_exe()?;
    let environment: std::collections::BTreeMap<_, _> = std::env::vars()
        .filter(|(k, _)| k.starts_with("STREHL_") || k == "RAYON_NUM_THREADS")
        .collect();
    fs::write(
        out.join("plan.json"),
        serde_json::to_vec_pretty(&json!({
            "schema":"rea-temporal-finish-v1","status":"RUNNING until summary.json exists",
            "source_hashes":hashes,"frozen_c_helper_bindings":helper_hashes,
            "executable":exe,"executable_sha256":digest(&fs::read(&exe)?),"software":crate::SOFTWARE,
            "environment":environment,"workers":rayon::current_num_threads(),"repeats":repeats,
            "source_native":[SIDE,SIDE],"analysis_quad":[ANALYSIS_SIDE,ANALYSIS_SIDE],
            "modes":NAMES,"kernel":[0.25,0.5,0.25],"filtered_bands":[0,1],
        "placebo_addressing":"positive-x lookup in each neighboring E/F row with circular wrap; shift=max(1,8>>level); center unchanged",
        "placebo_primary_region":"exclude12 level0 quad pixels at each x edge,4 at each y edge",
            "floor":"complete per-frame gate*measured_beta*V, filtered once with E before rectification",
            "primary_exponents":[8.0,8.0,7.6832],"small_default_control":[3.92,2.8,2.0],
            "storage":"regenerated original u16 CFA; core bounded guide rings and one bounded observer snapshot; no aligned-frame volume",
            "source_order":"declared order; unchanged endpoints and N<3; exactly-once folding checked",
            "secondary_metrics":"signed template projection is not literal line strength; paired present/absent fidelity controls nuisance spill",
        }))?,
    )?;
    let mut results = Vec::new();
    for c in &cases {
        eprintln!(
            "temporal actual-finish case {}/{}: {}, N={}",
            results.len() + 1,
            cases.len(),
            c.name,
            c.n
        );
        results.push(run_case(c, repeats, domain, &out)?);
    }
    // Cheap exact controls after the flat ladder and image cases.
    let mut controls = Vec::new();
    for n in [1, 2, 5] {
        let mut c = case("mechanical", n, "one", 120.0, 99);
        c.constant = n == 5;
        c.geometry = "identity";
        let b = betas(&c, domain)?;
        let r = stack(&c, 0, false, true, false, &[1, 2], domain, &b)?;
        controls.push(
            json!({"n":n,"constant":c.constant,"diagnostics":r.diagnostics,
            "off_exact":r.outputs[0]==r.outputs[1],"candidate_exact":r.outputs[0]==r.outputs[2]}),
        );
    }
    fs::write(
        out.join("summary.json"),
        serde_json::to_vec_pretty(&json!({
            "schema":"rea-temporal-finish-summary-v1","status":"COMPLETE","quality_claim":false,"cases":results,"mechanical_controls":controls
        }))?,
    )?;
    Ok(())
}
