// Test-only six-orientation native CFA consumer. Root owns all executions.
use super::shared_source_field::{hash16, hash32};
use super::*;
use serde_json::{Value, json};
use strehl_core::align::Similarity;
use strehl_core::pyramid::{Fallback, Hull, LevelSize, correction_variance_diagnostic as kernels};

include!(concat!(
    env!("CARGO_MANIFEST_DIR"),
    "/../../experiments/raw-quality-2026-10-27/dual-tree-cfa/transform.rs"
));

pub(crate) struct Arm {
    pub planes4: Vec<Vec<f32>>,
    pub rgb: Vec<f32>,
}
pub(crate) struct Comparison {
    pub canonical: Arm,
    pub candidate: Arm,
    pub uniform: Arm,
    pub gathered_source0: Arm,
    pub pre_hull_planes4: Vec<Vec<f32>>,
    pub mean_planes4: Vec<Vec<f32>>,
    pub native_width: usize,
    pub native_height: usize,
    pub evidence: Value,
}
pub(crate) struct Finished {
    pub planes4: Vec<Vec<f32>>,
    pub pre_hull_planes4: Vec<Vec<f32>>,
    pub uniform_planes4: Vec<Vec<f32>>,
    pub mean_planes4: Vec<Vec<f32>>,
    pub evidence: Value,
}
pub(crate) fn camera_rgb(
    planes4: &[Vec<f32>],
    width: usize,
    height: usize,
    levels: Levels,
    wb: [f32; 4],
) -> Result<Vec<f32>> {
    phase_packed_rgb::camera_rgb(planes4, width, height, levels, wb)
}
fn arm(
    planes4: Vec<Vec<f32>>,
    crop: align_cmd::CropRect,
    levels: Levels,
    wb: [f32; 4],
) -> Result<Arm> {
    let rgb = camera_rgb(&planes4, crop.width, crop.height, levels, wb)?;
    Ok(Arm { planes4, rgb })
}
fn config_guard(cfg: MergeConfig) -> Result<()> {
    ensure!(
        cfg.bands == 7
            && cfg.gate == 2.0
            && cfg.exponent == 2.0
            && cfg.sharpen_per_octave == 1.4
            && cfg.select == SelectMode::SoftPower
            && cfg.admission == AdmissionMode::HardFloor
            && cfg.base == BaseBand::Mean
            && cfg.fallback == Fallback::Mean
            && cfg.hull == Hull::InputRange
            && cfg.mean_coarse == 0
            && cfg.significance_scale == 0.,
        "fixed seven-level dual-tree settings"
    );
    Ok(())
}
fn plane_guard(known4: &[Vec<f32>], plan: &Plan) -> Result<()> {
    ensure!(
        known4.len() == 4
            && known4
                .iter()
                .all(|p| p.len() == plan.input_width * plan.input_height
                    && p.iter().all(|v| v.is_finite())),
        "actual gathered CFA shape/nonfinite"
    );
    Ok(())
}
fn scalar_fields(plan: &Plan) -> Vec<Vec<f32>> {
    plan.band_shapes()
        .into_iter()
        .flat_map(|(w, h)| (0..6).map(move |_| vec![0.; w * h]))
        .collect()
}
fn complex_fields(plan: &Plan) -> Vec<Vec<Complex>> {
    plan.band_shapes()
        .into_iter()
        .flat_map(|(w, h)| (0..6).map(move |_| vec![Complex::default(); w * h]))
        .collect()
}
fn squared(value: Complex) -> f32 {
    value.re * value.re + value.im * value.im
}
fn coefficients_hash(c: &Coefficients) -> Vec<String> {
    c.bands
        .iter()
        .map(|b| {
            let values = b
                .values
                .iter()
                .flat_map(|v| [v.re, v.im])
                .collect::<Vec<_>>();
            hash32(&values)
        })
        .collect()
}

pub(crate) struct Accumulator {
    plan: Plan,
    cfg: MergeConfig,
    gains2: [f32; 4],
    numerator: [Vec<Vec<Complex>>; 4],
    denominator: Vec<Vec<f32>>,
    scale: Vec<Vec<f32>>,
    mean: Vec<Vec<f32>>,
    low: Vec<Vec<f32>>,
    high: Vec<Vec<f32>>,
    count: usize,
    source_ids: Vec<usize>,
}
impl Accumulator {
    pub(crate) fn new(plan: Plan, cfg: MergeConfig, wb: [f32; 4]) -> Result<Self> {
        plan.validate()?;
        config_guard(cfg)?;
        ensure!(
            wb[..3].iter().all(|v| v.is_finite() && *v > 0.),
            "fixed WB gains"
        );
        let gains2 = [wb[0] / wb[1], 1., 1., wb[2] / wb[1]].map(|v| v * v);
        ensure!(
            gains2.iter().all(|v| v.is_finite()),
            "WB energy gain overflow"
        );
        let n = plan.input_width * plan.input_height;
        Ok(Self {
            numerator: std::array::from_fn(|_| complex_fields(&plan)),
            denominator: scalar_fields(&plan),
            scale: scalar_fields(&plan),
            mean: vec![vec![0.; n]; 4],
            low: vec![vec![f32::INFINITY; n]; 4],
            high: vec![vec![f32::NEG_INFINITY; n]; 4],
            plan,
            cfg,
            gains2,
            count: 0,
            source_ids: Vec::new(),
        })
    }
    pub(crate) fn add_source(
        &mut self,
        frame: &Frame,
        source_id: usize,
        known4: &[Vec<f32>],
        noise: &NoiseModel,
        gather: impl Fn(&Frame) -> Result<Vec<Vec<f32>>>,
    ) -> Result<Value> {
        plane_guard(known4, &self.plan)?;
        ensure!(
            self.count < 299 && source_id < 299 && !self.source_ids.contains(&source_id),
            "unique original source ordinal required"
        );
        validate_pyramid_frame(frame, frame.geometry(), source_id)?;
        let source_hash = hash16(&frame.data);
        let started = Instant::now();
        let signal_start = Instant::now();
        let mut energy = scalar_fields(&self.plan);
        let mut signal_hashes = Vec::new();
        for p in 0..4 {
            let wave = forward_phase(&known4[p], &self.plan)?;
            signal_hashes.push(coefficients_hash(&wave));
            for (out, band) in energy.iter_mut().zip(&wave.bands) {
                for (e, &z) in out.iter_mut().zip(&band.values) {
                    *e += self.gains2[p] * squared(z);
                }
            }
        }
        let signal_energy_seconds = signal_start.elapsed().as_secs_f64();
        let probe_start = Instant::now();
        let original_variance = boundary_cfa_wavelet::original_variances(frame, noise)?;
        let original_variance_sha256 = hash32(&original_variance);
        let seeds: [usize; 16] =
            std::array::from_fn(|draw| boundary_cfa_wavelet::probe_seed(source_id, draw));
        let mut variance = scalar_fields(&self.plan);
        let mut pair_power_means = Vec::new();
        for pair in 0..8 {
            let a_source =
                boundary_cfa_wavelet::noisy_source(frame, &original_variance, seeds[2 * pair])?;
            let a_planes = gather(&a_source)?;
            drop(a_source);
            plane_guard(&a_planes, &self.plan)?;
            let mut a = a_planes
                .iter()
                .map(|p| forward_phase(p, &self.plan).map(Some))
                .collect::<Result<Vec<_>>>()?;
            drop(a_planes);
            let b_source =
                boundary_cfa_wavelet::noisy_source(frame, &original_variance, seeds[2 * pair + 1])?;
            let b_planes = gather(&b_source)?;
            drop(b_source);
            plane_guard(&b_planes, &self.plan)?;
            let mut pair_sum = 0.0f64; // receipt only; operator is entirelyf32
            let mut pair_count = 0usize;
            for p in 0..4 {
                let first = a[p].take().context("probe pair member absent")?;
                let second = forward_phase(&b_planes[p], &self.plan)?;
                for ((out, aa), bb) in variance.iter_mut().zip(&first.bands).zip(&second.bands) {
                    for ((v, x), y) in out.iter_mut().zip(&aa.values).zip(&bb.values) {
                        let delta = Complex {
                            re: x.re - y.re,
                            im: x.im - y.im,
                        };
                        let q = self.gains2[p] * squared(delta);
                        ensure!(q.is_finite() && q >= 0., "nonfinite propagated noise power");
                        *v += q / 16.0;
                        pair_sum += 0.5 * q as f64;
                        pair_count += 1;
                    }
                }
            }
            pair_power_means.push(pair_sum / pair_count as f64);
        }
        drop(original_variance);
        let probe_seconds = probe_start.elapsed().as_secs_f64();
        let field_start = Instant::now();
        let mut energy_hashes = Vec::new();
        let mut floor_hashes = Vec::new();
        let mut raw_weight_hashes = Vec::new();
        let mut positive_counts = Vec::new();
        for b in 0..energy.len() {
            let k = b / 6;
            let size = LevelSize {
                width: self.plan.padded_width >> (k + 1),
                height: self.plan.padded_height >> (k + 1),
            };
            let smoothed = kernels::smooth(&energy[b], size);
            let vv = kernels::smooth(&variance[b], size);
            energy_hashes.push(hash32(&smoothed));
            let floor = vv.iter().map(|v| 2.0 * v).collect::<Vec<_>>();
            floor_hashes.push(hash32(&floor));
            let mut raw_weights = Vec::with_capacity(smoothed.len());
            for j in 0..smoothed.len() {
                ensure!(
                    smoothed[j].is_finite()
                        && smoothed[j] >= 0.
                        && floor[j].is_finite()
                        && floor[j] >= 0.,
                    "invalid smoothed evidence"
                );
                let weight = kernels::soft_weight(
                    (smoothed[j] - floor[j]).max(0.),
                    floor[j],
                    self.cfg.exponent_at(k, 7),
                );
                ensure!(
                    weight.is_finite() && weight >= 0.,
                    "invalid shared coefficient weight"
                );
                raw_weights.push(weight);
                if weight > self.scale[b][j] {
                    let factor = self.scale[b][j] / weight;
                    for p in 0..4 {
                        self.numerator[p][b][j].re *= factor;
                        self.numerator[p][b][j].im *= factor;
                    }
                    self.denominator[b][j] *= factor;
                    self.scale[b][j] = weight;
                }
                let relative = if weight > 0. {
                    weight / self.scale[b][j]
                } else {
                    0.
                };
                self.denominator[b][j] += relative;
                ensure!(
                    self.denominator[b][j].is_finite(),
                    "nonfinite shared denominator"
                );
                energy[b][j] = relative;
            }
            raw_weight_hashes.push(hash32(&raw_weights));
            positive_counts.push(raw_weights.iter().filter(|&&v| v > 0.).count());
        }
        drop(variance);
        let field_seconds = field_start.elapsed().as_secs_f64();
        let fold_start = Instant::now();
        for p in 0..4 {
            // Deliberate second signal analysis; first pass released beforeprobes.
            let wave = forward_phase(&known4[p], &self.plan)?;
            ensure!(
                coefficients_hash(&wave) == signal_hashes[p],
                "signal transform not replayable"
            );
            for ((sum, band), weight) in self.numerator[p].iter_mut().zip(&wave.bands).zip(&energy)
            {
                for ((out, &value), &w) in sum.iter_mut().zip(&band.values).zip(weight) {
                    out.re += w * value.re;
                    out.im += w * value.im;
                    ensure!(
                        out.re.is_finite() && out.im.is_finite(),
                        "coefficient numerator overflow"
                    );
                }
            }
            for j in 0..known4[p].len() {
                self.mean[p][j] += known4[p][j];
                self.low[p][j] = self.low[p][j].min(known4[p][j]);
                self.high[p][j] = self.high[p][j].max(known4[p][j]);
                ensure!(self.mean[p][j].is_finite(), "spatial mean overflow");
            }
        }
        self.count += 1;
        self.source_ids.push(source_id);
        ensure!(
            hash16(&frame.data) == source_hash,
            "original source modified"
        );
        Ok(json!({"source_index":source_id,"source_sha256":source_hash,
            "known4_sha256":known4.iter().map(|v|hash32(v)).collect::<Vec<_>>(),
            "original_variance_sha256":original_variance_sha256,
            "probe_pairs":8,"probe_draws":16,"probe_seeds":seeds,
            "probe_pair_wb_complex_power_mean":pair_power_means,
            "signal_analyses_per_phase":2,"probe_analyses_per_phase":16,
            "signal_coefficient_sha256":signal_hashes,"energy_sha256":energy_hashes,
            "floor_sha256":floor_hashes,"raw_weight_sha256":raw_weight_hashes,
            "positive_weight_coefficients":positive_counts,
            "signal_energy_seconds":signal_energy_seconds,"probe_seconds":probe_seconds,
            "field_seconds":field_seconds,"signal_reanalysis_and_fold_seconds":fold_start.elapsed().as_secs_f64(),
            "source_seconds":started.elapsed().as_secs_f64(),"original_unchanged":true,
            "reconstruction_planes_per_shared_field":4,"real_imaginary_share_weight":true,
            "noise_accumulation":"f32 phase/pair WB-power sum divided by16 before common smoothing",
            "simultaneous_gathered_probe_count":1,"pair_A_full_coefficient_map_retained":true}))
    }
    pub(crate) fn finish(mut self) -> Result<Finished> {
        ensure!(self.count > 0, "empty dual-tree accumulator");
        let started = Instant::now();
        for p in &mut self.mean {
            for v in p {
                *v /= self.count as f32;
            }
        }
        let mut pre_hull = Vec::new();
        let mut uniform = Vec::new();
        for p in 0..4 {
            let mut wave = forward_phase(&self.mean[p], &self.plan)?;
            uniform.push(inverse_phase(&wave, &self.plan)?);
            for (b, band) in wave.bands.iter_mut().enumerate() {
                for (j, z) in band.values.iter_mut().enumerate() {
                    if self.denominator[b][j] > 0. {
                        z.re = self.numerator[p][b][j].re / self.denominator[b][j];
                        z.im = self.numerator[p][b][j].im / self.denominator[b][j];
                    }
                }
            }
            pre_hull.push(inverse_phase(&wave, &self.plan)?);
        }
        let mut planes = pre_hull.clone();
        let mut clamped = [0usize; 4];
        for p in 0..4 {
            for j in 0..planes[p].len() {
                ensure!(
                    self.low[p][j].is_finite()
                        && self.high[p][j].is_finite()
                        && self.low[p][j] <= self.high[p][j],
                    "invalid actual input hull"
                );
                planes[p][j] = planes[p][j].clamp(self.low[p][j], self.high[p][j]);
                clamped[p] += usize::from(planes[p][j].to_bits() != pre_hull[p][j].to_bits());
            }
        }
        let evidence = json!({"source_count":self.count,"source_ids":self.source_ids,
            "input_phase_dimensions":[self.plan.input_width,self.plan.input_height],
            "extended_phase_dimensions":[self.plan.padded_width,self.plan.padded_height],
            "levels":7,"directions":6,"real_trees":4,"CFA_phases":4,
            "exponents":(0..7).map(|k|self.cfg.exponent_at(k,7)).collect::<Vec<_>>(),
            "wb_squared_energy_gains":self.gains2,
            "terminal_base":"four LL arrays of transform of source-order gathered spatial mean",
            "fallback":"same spatial mean transform at zero totalweight; no coefficient-copy shortcut",
            "fallback_coefficients":self.denominator.iter().map(|b|b.iter().filter(|&&v|v==0.).count()).collect::<Vec<_>>(),
            "denominator_sha256":self.denominator.iter().map(|b|hash32(b)).collect::<Vec<_>>(),
            "scale_sha256":self.scale.iter().map(|b|hash32(b)).collect::<Vec<_>>(),
            "hull":"actual gathered per-site InputRange","hull_changed_sites":clamped,
            "finish_seconds":started.elapsed().as_secs_f64(),"admission":false,"quality_claim":false});
        Ok(Finished {
            planes4: planes,
            pre_hull_planes4: pre_hull,
            uniform_planes4: uniform,
            mean_planes4: self.mean,
            evidence,
        })
    }
}

fn generated_gather(
    frame: &Frame,
    warp: Similarity,
    crop: align_cmd::CropRect,
) -> Result<Vec<Vec<f32>>> {
    ensure!(
        !frame.path.exists() && frame.active.width <= 512 && frame.active.height <= 512,
        "bounded generated original source"
    );
    ensure!(
        align_cmd::fullres_gather_enabled()
            && gatefloor::enabled()
            && align_cmd::direct_plane_mode()? == align_cmd::DirectPlaneMode::Off
            && !align_cmd::native_gpu_integration::gpu_gather_enabled()?,
        "held CPU/remosaic generated consumer"
    );
    let identity = strehl_raw::identity(&frame.path);
    ensure!(
        strehl_core::optics::profile_for_capture_env(
            identity.model.as_deref(),
            identity.lens_type3
        )?
        .is_none()
            && phase_packed_rgb::full_stack::full_source_supported(
                warp,
                frame.geometry(),
                crop,
                None
            ),
        "generated CA-off covered source support"
    );
    let mut current = frame.clone();
    let mut planes = vec![vec![0.0; crop.width * crop.height]; 4];
    align_cmd::warp_frame_in_place(
        &mut current,
        warp,
        frame.geometry(),
        Resampler::CatmullRom,
        &mut WarpScratch::new(frame.geometry()),
    )?;
    extract_planes(
        &current.data,
        current.stride,
        current.active.x,
        current.active.y,
        current.levels.black,
        PyramidDomain::cropped(frame.geometry(), crop)?,
        &BAND_PLANE_OFFSETS,
        &mut planes,
    )?;
    Ok(planes)
}

pub(crate) fn compare_generated(
    frames: &[Frame],
    transforms: &[Similarity],
    crop: align_cmd::CropRect,
    noise: &NoiseModel,
    cfg: MergeConfig,
) -> Result<Comparison> {
    config_guard(cfg)?;
    ensure!(
        !frames.is_empty() && frames.len() <= 8 && frames.len() == transforms.len(),
        "bounded generated source count"
    );
    let first = &frames[0];
    let full = first.geometry();
    let wb = first.wb_coeffs;
    ensure!(
        first.active.width <= 512 && first.active.height <= 512,
        "bounded generated native extent"
    );
    for (index, f) in frames.iter().enumerate() {
        ensure!(
            !f.path.exists()
                && f.geometry() == full
                && f.active == first.active
                && f.stride == first.stride
                && f.levels == first.levels
                && f.camera == first.camera
                && f.iso == first.iso
                && f.wb_coeffs[..3] == wb[..3],
            "generated metadata/support"
        );
        validate_pyramid_frame(f, full, index)?;
    }
    let entries = frames
        .iter()
        .map(|f| (f.path.to_string_lossy(), f.allocated_bytes() as u64))
        .collect::<Vec<_>>();
    let map = WarpMap::new(
        strehl_core::warpmap::Provenance {
            stack: StackIdentity::from_entries("dual-tree-generated", &entries),
            strategy: "supplied generated geometry".into(),
            heldout_px: None,
            cycle_floor_px: None,
            reference: 0,
            note: "fixed six-orientation native CFA".into(),
        },
        full,
        Resampler::CatmullRom,
        transforms.iter().copied().map(FrameWarp::Placed).collect(),
    );
    struct Source<'a>(&'a [Frame]);
    impl PyramidFrameSource for Source<'_> {
        fn len(&self) -> usize {
            self.0.len()
        }
        fn decode(&self, i: usize) -> Result<Frame> {
            Ok(self.0[i].clone())
        }
    }
    let source = Source(frames);
    let sizes = level_sizes(crop.width, crop.height, cfg.bands);
    let mut canonical = BandWorker::new(PyramidDomain::cropped(full, crop)?, cfg);
    let mut accumulator = Accumulator::new(Plan::new(crop.width, crop.height)?, cfg, wb)?;
    let mut gathered0 = None;
    let mut rows = Vec::new();
    for (index, frame) in frames.iter().enumerate() {
        ensure!(
            canonical.fold(&source, index, frame.levels, noise, Some(&map), None)?,
            "canonical generated source refused"
        );
        // Commission the probe consumer against the same current signal gather.
        let check = generated_gather(frame, transforms[index], crop)?;
        ensure!(
            check
                .iter()
                .zip(&canonical.planes)
                .all(|(a, b)| a.len() == b.len()
                    && a.iter().zip(b).all(|(a, b)| a.to_bits() == b.to_bits())),
            "candidate probe gather differs from actual canonical gather"
        );
        if index == 0 {
            gathered0 = Some(canonical.planes.clone());
        }
        rows.push(
            accumulator.add_source(frame, index, &canonical.planes, noise, |f| {
                generated_gather(f, transforms[index], crop)
            })?,
        );
    }
    let finished = accumulator.finish()?;
    let evidence = json!({"frames":rows,"candidate":finished.evidence,
        "canonical_level_sizes":sizes.iter().map(|s|[s.width,s.height]).collect::<Vec<_>>(),
        "canonical_exponents":(0..sizes.len()-1).map(|k|cfg.exponent_at(k,sizes.len()-1)).collect::<Vec<_>>(),
        "canonical_exponent_bits":(0..sizes.len()-1).map(|k|cfg.exponent_at(k,sizes.len()-1).to_bits()).collect::<Vec<_>>(),
        "candidate_exponent_bits":(0..7).map(|k|cfg.exponent_at(k,7).to_bits()).collect::<Vec<_>>(),
        "generated_basis_only_comparison":false,
        "candidate_effective_levels":7,"signal_gather_check_exact":true,
        "causal_baseline":"actual unchanged BandWorker; separate canonical rather than an amount knob",
        "quality_claim":false,"admission":false});
    Ok(Comparison {
        canonical: arm(
            canonical.merge.finish(&mut Workspace::new(&sizes)),
            crop,
            first.levels,
            wb,
        )?,
        candidate: arm(finished.planes4, crop, first.levels, wb)?,
        uniform: arm(finished.uniform_planes4, crop, first.levels, wb)?,
        gathered_source0: arm(gathered0.context("source0 absent")?, crop, first.levels, wb)?,
        pre_hull_planes4: finished.pre_hull_planes4,
        mean_planes4: finished.mean_planes4,
        native_width: 2 * crop.width,
        native_height: 2 * crop.height,
        evidence,
    })
}
