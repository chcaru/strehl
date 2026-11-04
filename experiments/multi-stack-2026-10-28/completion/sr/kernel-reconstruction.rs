//! Experiment-only direct original-CFA color reconstruction.
//! Physical sensor coordinates, signed f32 samples, no aligned image or demosaic.
//! Phase certificates describe sampling geometry, not measured optical resolution.
use strehl_core::align::Similarity;
use strehl_core::noise::PlaneNoise;
use strehl_core::optics::{Channel, OpticalProfile};
use strehl_core::plane::{PlaneGeometry, QuadSource};

pub const MAX_ALIASES: usize = 16;
pub const MAX_SOURCES: usize = 64;
pub const TILE_LIMIT_BYTES: usize = 64 * 1024 * 1024;
type Result<T> = std::result::Result<T, String>;

#[derive(Clone, Copy, Debug)]
pub struct OutputLattice {
    pub full: PlaneGeometry,
    pub origin_sensor: [f64; 2],
    pub step_sensor: [f64; 2],
    pub width: usize,
    pub height: usize,
}
impl OutputLattice {
    pub fn position(self, x: usize, y: usize) -> [f64; 2] {
        [
            self.origin_sensor[0] + x as f64 * self.step_sensor[0],
            self.origin_sensor[1] + y as f64 * self.step_sensor[1],
        ]
    }
    fn pixels(self) -> Result<usize> {
        if self.full.width == 0
            || self.full.height == 0
            || self.full.width.checked_mul(2).is_none()
            || self.full.height.checked_mul(2).is_none()
            || self.width == 0
            || self.height == 0
            || self.origin_sensor.iter().any(|x| !x.is_finite())
            || self
                .step_sensor
                .iter()
                .any(|x| !x.is_finite() || *x < 0.5 || *x > 1.0)
        {
            return Err("invalid lattice: prototype supports sensor steps in [0.5,1]".into());
        }
        self.width
            .checked_mul(self.height)
            .filter(|n| *n <= isize::MAX as usize)
            .ok_or_else(|| "output lattice size overflow".into())
    }
}

/// Borrowed confidence only, never aligned source pixel values.
/// Focus is a normalized local mode-response proxy, not an arbitrary precision
/// scale. Only a qualified mode's one-width neighbourhood is admitted; the
/// absolute floor prevents normalization from resurrecting far-defocused data.
#[derive(Clone, Copy)]
pub struct Admission<'a> {
    /// Use focus_mode_response; all other values below exp(-1/2) are refused.
    pub focus: &'a [f32],
    pub motion: &'a [f32],
    pub valid: &'a [bool],
    pub registration_sigma_sensor: &'a [f32],
}
pub struct SourceView<'a> {
    /// Unique acquisition token assigned only after original-content duplicate checks.
    /// Caller retains the full original-byte identity; this token is not a content hash.
    pub acquisition_id: u64,
    pub source: &'a (dyn QuadSource + Sync),
    /// Anchor green-luma guide -> source green-luma guide, R/G/B respectively.
    pub source_pull: [Similarity; 3],
    /// CFA order [R,G1,B,G2].
    pub noise: [PlaneNoise; 4],
    pub gain: f32,
    pub admission: Admission<'a>,
}
pub fn channel_pulls(placement: Similarity, profile: Option<&OpticalProfile>) -> [Similarity; 3] {
    [Channel::Red, Channel::Green, Channel::Blue]
        .map(|c| OpticalProfile::compose(profile, c, placement))
}

/// Apply a stored WarpMap pull at a physical active sensor position.
/// WarpMap's fitting origin is (width/2,height/2) in guide pixels, which
/// corresponds to (width+0.5,height+0.5) sensor pixels. It is not the array
/// sample-centroid ((width-1)/2,(height-1)/2).
pub fn sensor_pull(pull: Similarity, full: PlaneGeometry, sensor: [f64; 2]) -> [f64; 2] {
    let q = pull.apply_at(
        (sensor[0] - 0.5) * 0.5,
        (sensor[1] - 0.5) * 0.5,
        full.width as f64 * 0.5,
        full.height as f64 * 0.5,
    );
    [2.0 * q.0 + 0.5, 2.0 * q.1 + 0.5]
}

pub struct FrozenGuide<'a> {
    /// Expected black-subtracted camera RGB in the output exposure units.
    /// Must be frozen separately from each target sensel whose weight uses it.
    pub expected_rgb: &'a [[f32; 3]],
    /// PSD structure tensor [xx,xy,yy], in the anchor sensor basis.
    pub tensor: &'a [[f32; 3]],
    /// Already tested native result sampled on this explicit output lattice.
    pub fallback_rgb: &'a [[f32; 3]],
    /// None means the native fallback has no propagated variance; no relative-variance gate.
    pub fallback_variance: Option<&'a [[f32; 3]]>,
    pub fallback_valid: &'a [bool],
}
#[derive(Clone, Copy, Debug)]
pub struct Config {
    pub sigma_sensor: f32,
    pub max_anisotropy: f32,
    pub max_registration_sigma_sensor: f32,
    pub max_phase_condition: f32,
    pub max_variance_ratio: f32,
    pub variance_floor: f32,
    pub budget_bytes: usize,
}
impl Default for Config {
    fn default() -> Self {
        Self {
            sigma_sensor: 0.35,
            max_anisotropy: 2.0,
            max_registration_sigma_sensor: 0.15,
            max_phase_condition: 20.0,
            max_variance_ratio: 1.25,
            variance_floor: 1e-6,
            budget_bytes: TILE_LIMIT_BYTES,
        }
    }
}
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
#[repr(u8)]
pub enum Reason {
    Reconstructed,
    TooFewAcquisitions,
    IllConditioned,
    RejectedOrMissing,
    ExcessVariance,
    MissingFallback,
}
#[derive(Debug)]
pub struct TileResult {
    pub rgb: Vec<[f32; 3]>,
    /// Temporal variance conditional on the frozen guide and admission fields.
    /// Adaptive focus/motion selection can alter unconditional variance.
    pub variance: Vec<[f32; 3]>,
    /// False denotes an unknown fallback variance; its numeric slot is NaN.
    pub variance_valid: Vec<[bool; 3]>,
    pub valid: Vec<bool>,
    pub reason: Vec<[Reason; 3]>,
    pub phase_condition: Vec<[f32; 3]>,
    pub independent_acquisitions: Vec<[u16; 3]>,
    pub accepted_samples: Vec<[u32; 3]>,
    pub clipped_samples: Vec<[u32; 3]>,
    pub reservation: MemoryEstimate,
}
#[derive(Clone, Copy, Debug)]
pub struct MemoryEstimate {
    pub outputs: usize,
    pub borrowed_tile_inputs: usize,
    pub scratch: usize,
    pub total: usize,
}
pub fn memory_estimate(
    lattice: OutputLattice,
    sources: usize,
    workers: usize,
) -> Result<MemoryEstimate> {
    let n = lattice.pixels()?;
    if sources == 0 || sources > MAX_SOURCES || workers == 0 || workers > 4 {
        return Err("source/worker count outside prototype bounds".into());
    }
    // Output Vec headers/allocator cushion, fixed Gram/Jacobi scratch per worker.
    let outputs = n.checked_mul(73).and_then(|v| v.checked_add(4096));
    let inputs = sources
        .checked_mul(13)
        .and_then(|v| v.checked_add(49))
        .and_then(|v| n.checked_mul(v));
    let scratch = workers
        .checked_mul(16384)
        .and_then(|v| v.checked_add(sources * 512));
    let (Some(outputs), Some(borrowed_tile_inputs), Some(scratch)) = (outputs, inputs, scratch)
    else {
        return Err("tile reservation overflow".into());
    };
    let total = outputs
        .checked_add(borrowed_tile_inputs)
        .and_then(|v| v.checked_add(scratch))
        .filter(|v| *v <= isize::MAX as usize)
        .ok_or("tile reservation overflow")?;
    Ok(MemoryEstimate {
        outputs,
        borrowed_tile_inputs,
        scratch,
        total,
    })
}

/// Policy neighbourhood in measured through-focus width units. This is a
/// declared locality boundary, not a calibrated probability of optical focus.
/// `qualified` must include complete support, resolved modes, and the shared
/// full-track quality flags. A finite width alone is insufficient.
pub fn focus_mode_response(ordinal: f32, mode: f32, width: f32, qualified: bool) -> f32 {
    if !qualified || !ordinal.is_finite() || !mode.is_finite() || !width.is_finite() || width <= 0.0
    {
        return 0.0;
    }
    let distance = (ordinal - mode) / width;
    if distance.abs() > 1.0 {
        0.0
    } else {
        (-0.5 * distance * distance).exp()
    }
}
fn focus_admitted(response: f32) -> bool {
    response >= (-0.5_f32).exp()
}

/// Noise-normalized guide disagreement helper for an independently prepared guide.
/// The structure allowance is signal variation, never a privately fitted noise model.
pub fn guide_motion_confidence(
    difference: f32,
    injected_difference_variance: f32,
    structure_allowance: f32,
    threshold_sigma: f32,
) -> f32 {
    if !difference.is_finite()
        || !injected_difference_variance.is_finite()
        || !structure_allowance.is_finite()
        || injected_difference_variance < 0.0
        || structure_allowance < 0.0
        || !threshold_sigma.is_finite()
        || threshold_sigma <= 0.0
    {
        return 0.0;
    }
    let bound = threshold_sigma * (injected_difference_variance + structure_allowance).sqrt();
    if bound == 0.0 {
        return if difference == 0.0 { 1.0 } else { 0.0 };
    }
    let u = difference.abs() / bound;
    if u >= 1.0 { 0.0 } else { (1.0 - u * u).powi(2) }
}

struct Gram {
    re: [[f32; MAX_ALIASES]; MAX_ALIASES],
    im: [[f32; MAX_ALIASES]; MAX_ALIASES],
    columns: usize,
    axis: [usize; 2],
    total_weight: f32,
}
impl Gram {
    fn new(axis: [usize; 2]) -> Self {
        Self {
            re: [[0.0; MAX_ALIASES]; MAX_ALIASES],
            im: [[0.0; MAX_ALIASES]; MAX_ALIASES],
            columns: axis[0] * axis[1],
            axis,
            total_weight: 0.0,
        }
    }
    fn add(&mut self, delta: [f32; 2], weight: f32) {
        let mut cs = [(0.0f32, 0.0f32); MAX_ALIASES];
        for x in 0..self.axis[0] {
            for y in 0..self.axis[1] {
                let phase = std::f32::consts::PI * (x as f32 * delta[0] + y as f32 * delta[1]);
                let (s, c) = phase.sin_cos();
                cs[x * self.axis[1] + y] = (c, s);
            }
        }
        for i in 0..self.columns {
            for j in i..self.columns {
                self.re[i][j] += weight * (cs[i].0 * cs[j].0 + cs[i].1 * cs[j].1);
                self.im[i][j] += weight * (cs[i].0 * cs[j].1 - cs[i].1 * cs[j].0);
            }
        }
        self.total_weight += weight;
    }
    fn condition(&self) -> f32 {
        if self.total_weight <= 0.0 {
            return f32::INFINITY;
        }
        const N: usize = 2 * MAX_ALIASES;
        let mut a = [[0.0f32; N]; N];
        let k = self.columns;
        for i in 0..k {
            for j in 0..k {
                let (re, im) = if i <= j {
                    (self.re[i][j], self.im[i][j])
                } else {
                    (self.re[j][i], -self.im[j][i])
                };
                let re = re / self.total_weight;
                let im = im / self.total_weight;
                a[i][j] = re;
                a[i + k][j + k] = re;
                a[i][j + k] = -im;
                a[i + k][j] = im;
            }
        }
        let size = 2 * k;
        // Cyclic Jacobi; residual row sums below make the final eigenvalue
        // bounds conservative even if the fixed iteration cap is reached.
        for _ in 0..24 {
            let mut maximum = 0.0f32;
            for p in 0..size {
                for q in p + 1..size {
                    let off = a[p][q];
                    maximum = maximum.max(off.abs());
                    if off.abs() < 1e-6 {
                        continue;
                    }
                    let tau = (a[q][q] - a[p][p]) / (2.0 * off);
                    let t = if tau >= 0.0 {
                        1.0 / (tau + (1.0 + tau * tau).sqrt())
                    } else {
                        -1.0 / (-tau + (1.0 + tau * tau).sqrt())
                    };
                    let c = 1.0 / (1.0 + t * t).sqrt();
                    let s = t * c;
                    let pp = a[p][p];
                    let qq = a[q][q];
                    a[p][p] = pp - t * off;
                    a[q][q] = qq + t * off;
                    a[p][q] = 0.0;
                    a[q][p] = 0.0;
                    for r in 0..size {
                        if r != p && r != q {
                            let rp = a[r][p];
                            let rq = a[r][q];
                            a[r][p] = c * rp - s * rq;
                            a[p][r] = a[r][p];
                            a[r][q] = s * rp + c * rq;
                            a[q][r] = a[r][q];
                        }
                    }
                }
            }
            if maximum < 1e-5 {
                break;
            }
        }
        let mut lo = f32::INFINITY;
        let mut hi = 0.0f32;
        for i in 0..size {
            let mut residual = 0.0;
            for j in 0..size {
                if i != j {
                    residual += a[i][j].abs();
                }
            }
            lo = lo.min(a[i][i] - residual);
            hi = hi.max(a[i][i] + residual);
        }
        if lo <= 1e-6 || !hi.is_finite() {
            f32::INFINITY
        } else {
            (hi / lo).sqrt()
        }
    }
}

fn validate(
    lattice: OutputLattice,
    sources: &[SourceView<'_>],
    guide: &FrozenGuide<'_>,
    cfg: Config,
) -> Result<MemoryEstimate> {
    let n = lattice.pixels()?;
    let m = memory_estimate(lattice, sources.len(), 1)?;
    if cfg.budget_bytes > TILE_LIMIT_BYTES || m.total > cfg.budget_bytes {
        return Err(format!(
            "tile requires {} bytes, budget {} (hard cap {})",
            m.total, cfg.budget_bytes, TILE_LIMIT_BYTES
        ));
    }
    if !cfg.sigma_sensor.is_finite()
        || !(0.1..=1.0).contains(&cfg.sigma_sensor)
        || !cfg.max_anisotropy.is_finite()
        || !(1.0..=4.0).contains(&cfg.max_anisotropy)
        || !cfg.max_registration_sigma_sensor.is_finite()
        || cfg.max_registration_sigma_sensor <= 0.0
        || !cfg.max_phase_condition.is_finite()
        || cfg.max_phase_condition < 1.0
        || !cfg.max_variance_ratio.is_finite()
        || cfg.max_variance_ratio <= 0.0
        || !cfg.variance_floor.is_finite()
        || cfg.variance_floor <= 0.0
    {
        return Err("invalid reconstruction configuration".into());
    }
    if guide.expected_rgb.len() != n
        || guide.tensor.len() != n
        || guide.fallback_rgb.len() != n
        || guide.fallback_variance.is_some_and(|v| v.len() != n)
        || guide.fallback_valid.len() != n
    {
        return Err("guide dimensions disagree with lattice".into());
    }
    for i in 0..n {
        if guide.expected_rgb[i].iter().any(|v| !v.is_finite())
            || guide.tensor[i].iter().any(|v| !v.is_finite())
            || guide.tensor[i][0] < 0.0
            || guide.tensor[i][2] < 0.0
            || guide.tensor[i][0] * guide.tensor[i][2] + 1e-6 < guide.tensor[i][1].powi(2)
            || (guide.fallback_valid[i]
                && (guide.fallback_rgb[i].iter().any(|v| !v.is_finite())
                    || guide.fallback_variance.is_some_and(|variance| {
                        variance[i].iter().any(|v| !v.is_finite() || *v < 0.0)
                    })))
        {
            return Err("nonfinite/invalid frozen guide or fallback".into());
        }
    }
    for (s, src) in sources.iter().enumerate() {
        if sources[..s]
            .iter()
            .any(|v| v.acquisition_id == src.acquisition_id)
        {
            return Err("duplicate original acquisition identity".into());
        }
        if src.source.geometry() != lattice.full
            || !src.gain.is_finite()
            || src.gain <= 0.0
            || src.source_pull.iter().any(|p| {
                p.invert().is_none()
                    || !p.a.re.is_finite()
                    || !p.a.im.is_finite()
                    || !p.b.re.is_finite()
                    || !p.b.im.is_finite()
            })
        {
            return Err("source geometry/gain/pull invalid".into());
        }
        for pn in src.noise {
            if !pn.gain_dn_per_e.is_finite()
                || pn.gain_dn_per_e < 0.0
                || !pn.read_noise_e.is_finite()
                || pn.read_noise_e < 0.0
                || !pn.levels.black.is_finite()
                || !pn.levels.white.is_finite()
                || pn.levels.white <= pn.levels.black
                || pn.levels.white > 65535.0
            {
                return Err("invalid injected plane noise/levels".into());
            }
        }
        let a = src.admission;
        if a.focus.len() != n
            || a.motion.len() != n
            || a.valid.len() != n
            || a.registration_sigma_sensor.len() != n
            || a.focus
                .iter()
                .chain(a.motion)
                .any(|v| !v.is_finite() || !(0.0..=1.0).contains(v))
            || a.registration_sigma_sensor
                .iter()
                .any(|v| !v.is_finite() || *v < 0.0)
        {
            return Err("invalid source admission field".into());
        }
    }
    Ok(m)
}

pub fn reconstruct_tile(
    lattice: OutputLattice,
    sources: &[SourceView<'_>],
    guide: FrozenGuide<'_>,
    cfg: Config,
) -> Result<TileResult> {
    let reservation = validate(lattice, sources, &guide, cfg)?;
    let n = lattice.pixels()?;
    let mut out = TileResult {
        rgb: vec![[0.0; 3]; n],
        variance: vec![[f32::NAN; 3]; n],
        variance_valid: vec![[false; 3]; n],
        valid: vec![false; n],
        reason: vec![[Reason::RejectedOrMissing; 3]; n],
        phase_condition: vec![[f32::INFINITY; 3]; n],
        independent_acquisitions: vec![[0; 3]; n],
        accepted_samples: vec![[0; 3]; n],
        clipped_samples: vec![[0; 3]; n],
        reservation,
    };
    let axis = lattice.step_sensor.map(|s| (2.0 / s).ceil() as usize);
    for y in 0..lattice.height {
        for x in 0..lattice.width {
            let i = y * lattice.width + x;
            let p = lattice.position(x, y);
            let tensor = guide.tensor[i];
            let angle = 0.5 * (2.0 * tensor[1]).atan2(tensor[0] - tensor[2]);
            let (ny, nx) = angle.sin_cos();
            let coherence = ((tensor[0] - tensor[2]).powi(2) + 4.0 * tensor[1] * tensor[1]).sqrt()
                / (tensor[0] + tensor[2] + 1e-12);
            let stretch = 1.0 + (cfg.max_anisotropy - 1.0) * coherence.clamp(0.0, 1.0);
            // Physical support is in sensor units; a denser output grid is
            // not evidence for a narrower optical reconstruction kernel.
            let sigma = cfg.sigma_sensor;
            let radius = (3.0 * sigma * stretch).max(2.0);
            out.valid[i] = true;
            for color in 0..3 {
                let mut sum = 0.0f32;
                let mut weight = 0.0f32;
                let mut variance_sum = 0.0f32;
                let mut gram = Gram::new(axis);
                let mut acquisitions = 0u16;
                let mut samples = 0u32;
                let mut clipped = 0u32;
                for src in sources {
                    let a = src.admission;
                    if !a.valid[i]
                        || !focus_admitted(a.focus[i])
                        || a.registration_sigma_sensor[i] > cfg.max_registration_sigma_sensor
                    {
                        continue;
                    }
                    let confidence = a.focus[i] * a.motion[i];
                    if confidence <= 0.0 {
                        continue;
                    }
                    let pull = src.source_pull[color];
                    let inverse = pull.invert().ok_or("invalid pull")?;
                    let center = sensor_pull(pull, lattice.full, p);
                    let extent = radius as f64 * pull.scale();
                    let xmin = (center[0] - extent).ceil().max(0.0) as usize;
                    let ymin = (center[1] - extent).ceil().max(0.0) as usize;
                    let xmax = (center[0] + extent)
                        .floor()
                        .min((lattice.full.width * 2 - 1) as f64);
                    let ymax = (center[1] + extent)
                        .floor()
                        .min((lattice.full.height * 2 - 1) as f64);
                    if xmax < 0.0 || ymax < 0.0 || xmin as f64 > xmax || ymin as f64 > ymax {
                        continue;
                    }
                    let mut frame_has_sample = false;
                    for sy in ymin..=ymax as usize {
                        let (r0, r1) = src.source.quad_rows(sy / 2);
                        let row = if sy % 2 == 0 { r0 } else { r1 };
                        if row.len() < lattice.full.width * 2 {
                            return Err("QuadSource returned a short active row".into());
                        }
                        for sx in xmin..=xmax as usize {
                            let plane = match (sx % 2, sy % 2) {
                                (0, 0) => 0,
                                (1, 0) => 1,
                                (1, 1) => 2,
                                _ => 3,
                            };
                            let sample_color = match plane {
                                0 => 0,
                                2 => 2,
                                _ => 1,
                            };
                            if sample_color != color {
                                continue;
                            }
                            let sensor_point =
                                sensor_pull(inverse, lattice.full, [sx as f64, sy as f64]);
                            let d = [
                                (sensor_point[0] - p[0]) as f32,
                                (sensor_point[1] - p[1]) as f32,
                            ];
                            if d[0] * d[0] + d[1] * d[1] > radius * radius {
                                continue;
                            }
                            let pn = src.noise[plane];
                            let raw = row[sx];
                            if f32::from(raw) >= pn.levels.white {
                                clipped += 1;
                                continue;
                            }
                            let predicted_source_signal = guide.expected_rgb[i][color] / src.gain;
                            let var = (pn.variance(predicted_source_signal) * src.gain * src.gain)
                                .max(cfg.variance_floor);
                            let normal = d[0] * nx + d[1] * ny;
                            let tangent = -d[0] * ny + d[1] * nx;
                            let kernel = (-0.5
                                * ((normal / sigma).powi(2)
                                    + (tangent / (sigma * stretch)).powi(2)))
                            .exp();
                            let precision = confidence / var;
                            let w = kernel * precision;
                            if w <= 0.0 || !w.is_finite() {
                                continue;
                            }
                            let value = (f32::from(raw) - pn.levels.black) * src.gain;
                            sum += w * value;
                            weight += w;
                            variance_sum += w * w * var;
                            // Certificate uses the exact positive estimator weights,
                            // including Gaussian taper and all admission factors.
                            gram.add(d, w);
                            samples += 1;
                            frame_has_sample = true;
                        }
                    }
                    if frame_has_sample {
                        acquisitions += 1;
                    }
                }
                let condition = gram.condition();
                out.phase_condition[i][color] = condition;
                out.independent_acquisitions[i][color] = acquisitions;
                out.accepted_samples[i][color] = samples;
                out.clipped_samples[i][color] = clipped;
                let needed = (axis[0] * axis[1]).div_ceil(if color == 1 { 2 } else { 1 });
                let var = if weight > 0.0 {
                    variance_sum / (weight * weight)
                } else {
                    f32::INFINITY
                };
                let reason = if weight <= 0.0 {
                    Reason::RejectedOrMissing
                } else if (acquisitions as usize) < needed {
                    Reason::TooFewAcquisitions
                } else if condition > cfg.max_phase_condition {
                    Reason::IllConditioned
                } else if !var.is_finite()
                    || (guide.fallback_valid[i]
                        && guide.fallback_variance.is_some_and(|variance| {
                            var > cfg.max_variance_ratio * variance[i][color]
                        }))
                {
                    Reason::ExcessVariance
                } else {
                    Reason::Reconstructed
                };
                out.reason[i][color] = reason;
                if reason == Reason::Reconstructed {
                    out.rgb[i][color] = sum / weight;
                    out.variance[i][color] = var;
                    out.variance_valid[i][color] = true;
                } else if guide.fallback_valid[i] {
                    out.rgb[i][color] = guide.fallback_rgb[i][color];
                    if let Some(variance) = guide.fallback_variance {
                        out.variance[i][color] = variance[i][color];
                        out.variance_valid[i][color] = true;
                    }
                } else {
                    out.valid[i] = false;
                    out.reason[i][color] = Reason::MissingFallback;
                }
            }
        }
    }
    Ok(out)
}

#[cfg(test)]
#[path = "kernel-reconstruction-tests.rs"]
mod tests;
