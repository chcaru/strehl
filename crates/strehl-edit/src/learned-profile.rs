//! Frozen, explicit profile composition in linear FP32. No inference or model
//! assets live here. The caller owns the input color/tone contract; this module
//! does not interpret a model's exposure output or imply Adobe compatibility.
//!
//! Order: linear BT.709 -> caller-declared RIMM transform -> explicit scale ->
//! spatial/brightness gain -> explicit tone curve -> normalized semantic color
//! tables -> inverse RIMM transform -> Amount blend in linear BT.709.
//! Tables are bounded SDR mappings with optional linear gamut extension; that
//! extension preserves headroom but is not an HDR profile-table implementation.
use anyhow::{Result, ensure};
use rayon::prelude::*;
use std::sync::{
    Arc,
    atomic::{AtomicBool, Ordering},
};

pub type Matrix3 = [[f32; 3]; 3];
pub const IDENTITY_MATRIX: Matrix3 = [[1., 0., 0.], [0., 1., 0.], [0., 0., 1.]];

/// Derived from BT.709/D65 and ProPhoto/D50 primaries with Bradford adaptation.
/// This is an explicit standards choice, not an assertion about a vendor's
/// internal transform. Callers may supply a separately validated matrix.
pub const LINEAR_709_TO_RIMM: Matrix3 = [
    [0.529_280_4, 0.330_153, 0.140_566_6],
    [0.098_366_22, 0.873_463_9, 0.028_169_824],
    [0.016_875_342, 0.117_659_41, 0.865_465_2],
];
pub const MAX_GAIN_SAMPLES: usize = 1_048_576;
pub const MAX_TONE_KNOTS: usize = 4096;
const MAX_IMAGE_DIMENSION: u32 = 1 << 20;

#[inline]
pub(crate) fn matrix_rgb(m: &Matrix3, p: [f32; 3]) -> [f32; 3] {
    m.map(|r| r[0] * p[0] + r[1] * p[1] + r[2] * p[2])
}

fn inverse(matrix: Matrix3) -> Result<Matrix3> {
    ensure!(
        matrix.iter().flatten().all(|v| v.is_finite()),
        "Nonfinite color matrix"
    );
    let m = matrix.map(|row| row.map(f64::from));
    let cofactors = [
        [
            m[1][1] * m[2][2] - m[1][2] * m[2][1],
            m[1][2] * m[2][0] - m[1][0] * m[2][2],
            m[1][0] * m[2][1] - m[1][1] * m[2][0],
        ],
        [
            m[0][2] * m[2][1] - m[0][1] * m[2][2],
            m[0][0] * m[2][2] - m[0][2] * m[2][0],
            m[0][1] * m[2][0] - m[0][0] * m[2][1],
        ],
        [
            m[0][1] * m[1][2] - m[0][2] * m[1][1],
            m[0][2] * m[1][0] - m[0][0] * m[1][2],
            m[0][0] * m[1][1] - m[0][1] * m[1][0],
        ],
    ];
    let det = (0..3).map(|c| m[0][c] * cofactors[0][c]).sum::<f64>();
    ensure!(det.is_finite() && det != 0., "Singular color matrix");
    let inv: Matrix3 =
        std::array::from_fn(|r| std::array::from_fn(|c| (cofactors[c][r] / det) as f32));
    ensure!(
        inv.iter().flatten().all(|v| v.is_finite()),
        "Unrepresentable inverse color matrix"
    );
    let norm = |a: Matrix3| {
        a.map(|r| r.iter().map(|v| f64::from(v.abs())).sum::<f64>())
            .into_iter()
            .fold(0., f64::max)
    };
    ensure!(
        norm(matrix) * norm(inv) <= 1e6,
        "Ill-conditioned color matrix"
    );
    Ok(inv)
}

/// Check a serialized matrix before allocating the profile's numeric fields.
pub(crate) fn validate_matrix(matrix: Matrix3) -> Result<()> {
    inverse(matrix).map(|_| ())
}

/// Decoded gain table axes are [brightness, y, x], with x contiguous.
#[derive(Clone, Copy, Debug)]
pub struct GainMapParameters {
    pub dimensions: [u32; 3],
    pub origin_yx: [f32; 2],
    pub spacing_yx: [f32; 2],
    /// R, G, B, minimum RGB, maximum RGB weights in the declared RIMM domain.
    pub input_weights: [f32; 5],
    pub gamma: f32,
}

#[derive(Clone, Debug)]
pub struct GainMap {
    values: Arc<[f32]>,
    parameters: GainMapParameters,
}

impl GainMap {
    pub fn new(values: Arc<[f32]>, parameters: GainMapParameters) -> Result<Self> {
        let [n, h, w] = parameters.dimensions;
        ensure!(
            (1..=64).contains(&n) && (1..=512).contains(&h) && (1..=512).contains(&w),
            "Gain dimensions exceed supported bounds"
        );
        let samples = n as usize * h as usize * w as usize;
        ensure!(
            samples <= MAX_GAIN_SAMPLES && values.len() == samples,
            "Incorrect or excessive gain data length"
        );
        ensure!(
            values.iter().all(|v| v.is_finite() && *v >= 0.),
            "Gains must be finite and nonnegative"
        );
        ensure!(
            parameters.origin_yx.iter().all(|v| v.is_finite()),
            "Nonfinite gain origin"
        );
        ensure!(
            parameters
                .spacing_yx
                .iter()
                .all(|v| v.is_finite() && *v > 0.),
            "Gain spacing must be finite and positive"
        );
        ensure!(
            parameters.input_weights.iter().all(|v| v.is_finite()),
            "Nonfinite gain weights"
        );
        ensure!(
            parameters.gamma.is_finite() && parameters.gamma > 0.,
            "Gain gamma must be finite and positive"
        );
        Ok(Self { values, parameters })
    }

    pub fn parameters(&self) -> GainMapParameters {
        self.parameters
    }

    /// `uv` is the pixel center in the full active photograph, never the crop.
    pub fn sample(&self, linear_rimm: [f32; 3], uv: [f32; 2]) -> Result<f32> {
        validate_pixel(linear_rimm, uv, [0., 0.], 1.)?;
        let gain = self.sample_inner(linear_rimm, uv);
        ensure!(gain.is_finite(), "Nonfinite sampled gain");
        Ok(gain)
    }

    #[inline]
    pub(crate) fn sample_inner(&self, p: [f32; 3], uv: [f32; 2]) -> f32 {
        let par = self.parameters;
        let [n, h, w] = par.dimensions.map(|v| v as usize);
        let x = ((uv[0] - par.origin_yx[1]) / par.spacing_yx[1]).clamp(0., (w - 1) as f32);
        let y = ((uv[1] - par.origin_yx[0]) / par.spacing_yx[0]).clamp(0., (h - 1) as f32);
        let weights = par.input_weights;
        let brightness = p[0] * weights[0]
            + p[1] * weights[1]
            + p[2] * weights[2]
            + p[0].min(p[1]).min(p[2]) * weights[3]
            + p[0].max(p[1]).max(p[2]) * weights[4];
        if !brightness.is_finite() {
            return f32::NAN;
        }
        // The public gain-map definition indexes brightness with N, not N-1.
        let z = (brightness.clamp(0., 1.).powf(par.gamma) * n as f32).min((n - 1) as f32);
        let low = [x as usize, y as usize, z as usize];
        let high = [
            (low[0] + 1).min(w - 1),
            (low[1] + 1).min(h - 1),
            (low[2] + 1).min(n - 1),
        ];
        let f = [x - low[0] as f32, y - low[1] as f32, z - low[2] as f32];
        let at = |z: usize, y: usize, x: usize| self.values[(z * h + y) * w + x];
        let plane = |z| {
            let a = lerp(at(z, low[1], low[0]), at(z, low[1], high[0]), f[0]);
            let b = lerp(at(z, high[1], low[0]), at(z, high[1], high[0]), f[0]);
            lerp(a, b, f[1])
        };
        lerp(plane(low[2]), plane(high[2]), f[2])
    }
}

#[inline]
fn lerp(a: f32, b: f32, t: f32) -> f32 {
    a * (1. - t) + b * t
}

/// Nominal table encoding, independent of RGB primaries and presentation.
#[derive(Clone, Copy, Debug)]
pub enum ColorEncoding {
    Linear,
    Srgb,
    Power { gamma: f32 },
}

impl ColorEncoding {
    fn validate(self) -> Result<()> {
        if let Self::Power { gamma } = self {
            ensure!(
                gamma.is_finite() && (0.01..=16.).contains(&gamma),
                "Unsupported table power gamma"
            );
        }
        Ok(())
    }

    #[inline]
    fn encode(self, value: f32) -> f32 {
        match self {
            Self::Linear => value,
            Self::Srgb if value <= 0.003_130_8 => value * 12.92,
            Self::Srgb => 1.055 * value.powf(1. / 2.4) - 0.055,
            Self::Power { gamma } => value.powf(1. / gamma),
        }
    }

    #[inline]
    fn decode(self, value: f32) -> f32 {
        match self {
            Self::Linear => value,
            Self::Srgb => crate::color::decode_srgb(value),
            Self::Power { gamma } => value.powf(gamma),
        }
    }
}

/// Immutable decoded color table. Construction converts C,R,G,B storage to
/// contiguous RGB triplets for neighboring-knot access in the pixel loop.
#[derive(Clone, Debug)]
pub struct ColorLut {
    values: Arc<[[f32; 3]]>,
    size: usize,
    source_to_table: Matrix3,
    table_to_source: Matrix3,
    encoding: ColorEncoding,
    gamut_extension: bool,
}

impl ColorLut {
    pub fn new(
        size: u32,
        channel_major_values: Arc<[f32]>,
        source_to_table: Matrix3,
        encoding: ColorEncoding,
        gamut_extension: bool,
    ) -> Result<Self> {
        ensure!((2..=32).contains(&size), "Color table edge must be 2..32");
        let size = size as usize;
        let volume = size * size * size;
        ensure!(
            channel_major_values.len() == 3 * volume,
            "Incorrect color table length"
        );
        ensure!(
            channel_major_values
                .iter()
                .all(|v| v.is_finite() && (0.0..=1.0).contains(v)),
            "Decoded SDR color table values must be in 0..1"
        );
        encoding.validate()?;
        let table_to_source = inverse(source_to_table)?;
        let values = (0..volume)
            .map(|i| {
                [
                    channel_major_values[i],
                    channel_major_values[volume + i],
                    channel_major_values[2 * volume + i],
                ]
            })
            .collect::<Vec<_>>()
            .into();
        Ok(Self {
            values,
            size,
            source_to_table,
            table_to_source,
            encoding,
            gamut_extension,
        })
    }

    pub fn apply(&self, source: [f32; 3]) -> Result<[f32; 3]> {
        ensure!(
            source.iter().all(|v| v.is_finite()),
            "Nonfinite color-table input"
        );
        let result = self.apply_inner(source);
        ensure!(
            result.iter().all(|v| v.is_finite()),
            "Nonfinite color-table output"
        );
        Ok(result)
    }

    #[inline]
    pub(crate) fn apply_inner(&self, source: [f32; 3]) -> [f32; 3] {
        let raw = matrix_rgb(&self.source_to_table, source);
        if raw.iter().any(|v| !v.is_finite()) {
            return [f32::NAN; 3];
        }
        let clipped = raw.map(|v| v.clamp(0., 1.));
        let encoded = clipped.map(|v| self.encoding.encode(v).clamp(0., 1.));
        let lookup = self.lookup(encoded);
        let result = std::array::from_fn(|c| {
            self.encoding.decode(lookup[c])
                + if self.gamut_extension {
                    raw[c] - clipped[c]
                } else {
                    0.
                }
        });
        matrix_rgb(&self.table_to_source, result)
    }

    #[inline]
    fn lookup(&self, encoded: [f32; 3]) -> [f32; 3] {
        let p = encoded.map(|v| v * (self.size - 1) as f32);
        let lo = p.map(|v| v as usize);
        let hi = lo.map(|v| (v + 1).min(self.size - 1));
        let f: [f32; 3] = std::array::from_fn(|c| p[c] - lo[c] as f32);
        let at = |r, g, b| self.values[(r * self.size + g) * self.size + b];
        let mut result = [0.; 3];
        for r in 0..2 {
            for g in 0..2 {
                for b in 0..2 {
                    let value = at(
                        if r == 0 { lo[0] } else { hi[0] },
                        if g == 0 { lo[1] } else { hi[1] },
                        if b == 0 { lo[2] } else { hi[2] },
                    );
                    let weight = (if r == 0 { 1. - f[0] } else { f[0] })
                        * (if g == 0 { 1. - f[1] } else { f[1] })
                        * (if b == 0 { 1. - f[2] } else { f[2] });
                    for c in 0..3 {
                        result[c] += value[c] * weight;
                    }
                }
            }
        }
        result
    }
}

/// One explicitly supplied, channel-independent monotone curve. Outside its
/// knot domain, unit-slope tails preserve negative/HDR offsets instead of clipping.
/// Identity is exact; no default vendor profile or tone curve is inferred.
#[derive(Clone, Debug, Default)]
pub struct ProfileToneCurve {
    knots: Arc<[[f32; 2]]>,
    slopes: Arc<[f32]>,
}

impl ProfileToneCurve {
    pub fn identity() -> Self {
        Self::default()
    }

    pub fn piecewise_linear(knots: Arc<[[f32; 2]]>) -> Result<Self> {
        ensure!(
            (2..=MAX_TONE_KNOTS).contains(&knots.len()),
            "Tone curve requires 2..4096 knots"
        );
        ensure!(
            knots.iter().flatten().all(|v| v.is_finite()),
            "Nonfinite tone knot"
        );
        let mut slopes = Vec::with_capacity(knots.len() - 1);
        for pair in knots.windows(2) {
            ensure!(
                pair[1][0] > pair[0][0] && pair[1][1] >= pair[0][1],
                "Tone domain must increase and range must not decrease"
            );
            let slope = ((f64::from(pair[1][1]) - f64::from(pair[0][1]))
                / (f64::from(pair[1][0]) - f64::from(pair[0][0]))) as f32;
            ensure!(slope.is_finite(), "Unrepresentable tone slope");
            slopes.push(slope);
        }
        Ok(Self {
            knots,
            slopes: slopes.into(),
        })
    }

    /// [[domain minimum, domain maximum], [range minimum, range maximum]].
    /// None denotes exact identity, without an artificial finite domain.
    pub fn domain_and_range(&self) -> Option<[[f32; 2]; 2]> {
        let first = self.knots.first()?;
        let last = self.knots.last()?;
        Some([[first[0], last[0]], [first[1], last[1]]])
    }

    #[inline]
    fn apply(&self, value: f32) -> f32 {
        // A finite but extreme caller pixel can overflow an earlier operation.
        // Propagate it to the checked render boundary instead of indexing a curve.
        if !value.is_finite() {
            return value;
        }
        let Some(first) = self.knots.first() else {
            return value;
        };
        let last = self.knots.last().unwrap();
        if value <= first[0] {
            return first[1] + (value - first[0]);
        }
        if value >= last[0] {
            return last[1] + (value - last[0]);
        }
        let i = self.knots.partition_point(|k| k[0] <= value) - 1;
        self.knots[i][1] + (value - self.knots[i][0]) * self.slopes[i]
    }
}

#[derive(Clone, Debug)]
pub struct ProfileParameters {
    pub linear_709_to_rimm: Matrix3,
    /// Caller-specified linear multiplier; never implicitly derived from an EV head.
    pub pre_gain_scale: f32,
    pub tone_curve: ProfileToneCurve,
}

#[derive(Clone, Debug)]
pub struct PreparedLearnedProfile {
    gain: GainMap,
    tables: [Option<ColorLut>; 3],
    parameters: ProfileParameters,
    rimm_to_linear_709: Matrix3,
}

/// Native pixel crop. Dimensions/offsets refer to the complete active photograph.
/// For resampled previews use `apply_pixel` with each source footprint's center.
#[derive(Clone, Copy, Debug)]
pub struct ProfileRegion {
    pub full_size: [u32; 2],
    pub origin: [u32; 2],
    pub size: [u32; 2],
}

#[derive(Clone, Copy, Debug, Default)]
pub struct SemanticMaskPlanes<'a> {
    /// Optional crop-sized planes, row-major. Absence means zero semantic weight.
    pub subject: Option<&'a [f32]>,
    pub sky: Option<&'a [f32]>,
}

fn validate_pixel(rgb: [f32; 3], uv: [f32; 2], masks: [f32; 2], amount: f32) -> Result<()> {
    ensure!(rgb.iter().all(|v| v.is_finite()), "Nonfinite profile input");
    ensure!(
        uv.iter().all(|v| v.is_finite() && (0.0..=1.0).contains(v)),
        "Profile coordinates must refer to the full image in 0..1"
    );
    ensure!(
        masks
            .iter()
            .all(|v| v.is_finite() && (0.0..=1.0).contains(v)),
        "Semantic weights must be finite in 0..1"
    );
    ensure!(
        amount.is_finite() && (0.0..=1.0).contains(&amount),
        "Profile Amount must be finite in 0..1"
    );
    Ok(())
}

impl PreparedLearnedProfile {
    /// Tables' source matrices must map the post-tone RIMM domain to their
    /// declared linear primaries. Absent semantic tables consume no mask weight;
    /// an absent background passes its remaining weight through unchanged.
    pub fn new(
        gain: GainMap,
        background: Option<ColorLut>,
        subject: Option<ColorLut>,
        sky: Option<ColorLut>,
        parameters: ProfileParameters,
    ) -> Result<Self> {
        ensure!(
            parameters.pre_gain_scale.is_finite() && parameters.pre_gain_scale > 0.,
            "Profile scale must be finite and positive"
        );
        let rimm_to_linear_709 = inverse(parameters.linear_709_to_rimm)?;
        Ok(Self {
            gain,
            tables: [background, subject, sky],
            parameters,
            rimm_to_linear_709,
        })
    }

    /// Allocation-free application at a caller-supplied whole-image center.
    pub fn apply_pixel(
        &self,
        linear_709: [f32; 3],
        uv: [f32; 2],
        semantic_weights: [f32; 2],
        amount: f32,
    ) -> Result<[f32; 3]> {
        validate_pixel(linear_709, uv, semantic_weights, amount)?;
        let result = self.apply_inner(linear_709, uv, semantic_weights, amount);
        ensure!(
            result.iter().all(|v| v.is_finite()),
            "Nonfinite profile output"
        );
        Ok(result)
    }

    #[inline]
    fn apply_inner(&self, rgb: [f32; 3], uv: [f32; 2], masks: [f32; 2], amount: f32) -> [f32; 3] {
        if amount == 0. {
            return rgb;
        }
        let source = matrix_rgb(&self.parameters.linear_709_to_rimm, rgb)
            .map(|v| v * self.parameters.pre_gain_scale);
        let gain = self.gain.sample_inner(source, uv);
        let toned = source.map(|v| self.parameters.tone_curve.apply(v * gain));
        let subject = if self.tables[1].is_some() {
            masks[0]
        } else {
            0.
        };
        let sky = if self.tables[2].is_some() {
            masks[1]
        } else {
            0.
        };
        let background = (1. - subject - sky).max(0.);
        let weights = [background, subject, sky];
        let normalization = background + subject + sky;
        let mut composed = [0.; 3];
        for (table, weight) in self.tables.iter().zip(weights) {
            if weight == 0. {
                continue;
            }
            let p = table
                .as_ref()
                .map_or(toned, |table| table.apply_inner(toned));
            for c in 0..3 {
                composed[c] += p[c] * weight;
            }
        }
        let developed = matrix_rgb(
            &self.rimm_to_linear_709,
            composed.map(|v| v / normalization),
        );
        if amount == 1. {
            return developed;
        }
        std::array::from_fn(|c| lerp(rgb[c], developed[c], amount))
    }

    /// Writes no additional full-frame buffer. Rows are parallel; cancellation is
    /// observed at row boundaries and every 64 pixels. On error/cancellation the
    /// destination may be partially written and must not replace the live image.
    pub fn render_region(
        &self,
        input: &[f32],
        output: &mut [f32],
        region: ProfileRegion,
        masks: SemanticMaskPlanes<'_>,
        amount: f32,
        cancelled: &AtomicBool,
    ) -> Result<()> {
        ensure!(
            region
                .full_size
                .iter()
                .all(|n| (1..=MAX_IMAGE_DIMENSION).contains(n)),
            "Invalid full photograph dimensions"
        );
        for axis in 0..2 {
            ensure!(
                region.size[axis] > 0
                    && u64::from(region.origin[axis]) + u64::from(region.size[axis])
                        <= u64::from(region.full_size[axis]),
                "Profile crop exceeds full photograph"
            );
        }
        let count = (region.size[0] as usize)
            .checked_mul(region.size[1] as usize)
            .ok_or_else(|| anyhow::anyhow!("Profile crop overflows address space"))?;
        let samples = count
            .checked_mul(3)
            .ok_or_else(|| anyhow::anyhow!("Profile buffer overflows address space"))?;
        ensure!(
            input.len() == samples && output.len() == samples,
            "Incorrect RGB buffer extent"
        );
        ensure!(
            masks.subject.is_none_or(|m| m.len() == count)
                && masks.sky.is_none_or(|m| m.len() == count),
            "Incorrect semantic mask extent"
        );
        ensure!(
            amount.is_finite() && (0.0..=1.0).contains(&amount),
            "Profile Amount must be finite in 0..1"
        );
        ensure!(
            !cancelled.load(Ordering::Relaxed),
            "Profile rendering cancelled"
        );
        let width = region.size[0] as usize;
        output
            .par_chunks_mut(width * 3)
            .zip(input.par_chunks(width * 3))
            .enumerate()
            .try_for_each(|(y, (out, src))| -> Result<()> {
                let v = (region.origin[1] as f32 + y as f32 + 0.5) / region.full_size[1] as f32;
                for x in 0..width {
                    if x % 64 == 0 {
                        ensure!(
                            !cancelled.load(Ordering::Relaxed),
                            "Profile rendering cancelled"
                        );
                    }
                    let i = y * width + x;
                    let weights = [
                        masks.subject.map_or(0., |m| m[i]),
                        masks.sky.map_or(0., |m| m[i]),
                    ];
                    let p = [src[3 * x], src[3 * x + 1], src[3 * x + 2]];
                    ensure!(
                        p.iter().all(|v| v.is_finite())
                            && weights
                                .iter()
                                .all(|v| v.is_finite() && (0.0..=1.0).contains(v)),
                        "Nonfinite RGB or invalid semantic sample"
                    );
                    let u = (region.origin[0] as f32 + x as f32 + 0.5) / region.full_size[0] as f32;
                    let value = self.apply_inner(p, [u, v], weights, amount);
                    ensure!(
                        value.iter().all(|v| v.is_finite()),
                        "Nonfinite profile output"
                    );
                    out[3 * x..3 * x + 3].copy_from_slice(&value);
                }
                Ok(())
            })
    }
}

#[cfg(test)]
#[path = "learned-profile-tests.rs"]
mod tests;
