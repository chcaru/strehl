//! Fixed linear observations gathered directly from original CFA samples.
//!
//! Filter and interpolation coefficients are composed and coalesced BEFORE any
//! sample is read. Consequently overlapping interpolants do not masquerade as
//! independent observations. Variance and cross-band covariance use one injected
//! temporal noise model evaluated at caller-supplied, frozen expected signals.
//! These observations alone establish neither repeat compatibility nor sharpness.
use crate::{
    CfaPlane,
    align::Similarity,
    noise::PlaneNoise,
    plane::{PlaneGeometry, QuadSource},
};

pub const MAX_BANDS: usize = 8;
const MAX_FILTER_TAPS: usize = 256;
const MAX_CONTRIBUTIONS: usize = 32_768;

#[derive(Clone, Copy, Debug)]
pub struct FilterTap {
    /// Offset from the query center in full-resolution reference sensor pixels.
    pub offset_sensor: [f64; 2],
    pub weight: f32,
}

#[derive(Clone, Copy, Debug)]
pub enum Kernel {
    Bilinear,
    CatmullRom,
}

/// One ORIGINAL acquisition and one of its four distinct RGGB planes.
pub struct OriginalView<'a> {
    pub acquisition_id: [u8; 32],
    pub source: &'a dyn QuadSource,
    pub plane: CfaPlane,
    /// Reference-guide to source-guide pull about the full guide center.
    /// Compose any local/color correction before supplying this transform.
    pub color_pull: Similarity,
    pub noise: PlaneNoise,
    /// Linear radiometric gain, applied after black subtraction. No clipping.
    pub gain: f32,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct OriginalSite {
    pub acquisition_id: [u8; 32],
    pub plane: CfaPlane,
    /// Original active-area same-color plane coordinates, not sensor coordinates.
    pub quad: [usize; 2],
}

#[derive(Clone, Debug)]
pub struct OriginalTap {
    pub site: OriginalSite,
    /// Includes photometric gain; entries beyond band_count are zero.
    pub band_weights: [f32; MAX_BANDS],
    /// Injected temporal variance in original black-subtracted DN squared.
    pub variance_dn2: f32,
}

#[derive(Debug)]
pub struct Observation {
    pub band_count: usize,
    pub values: [f32; MAX_BANDS],
    pub covariance: [[f32; MAX_BANDS]; MAX_BANDS],
    /// Sorted by original (row, column); zero aggregate coefficients are absent.
    pub taps: Vec<OriginalTap>,
    /// Checked peak allocation reservation, excluding caller-owned inputs.
    pub reservation_bytes: usize,
}

impl Observation {
    /// Exact original sample overlap; separate acquisitions and CFA planes do
    /// not share temporal noise. This does not imply absence of fixed pattern.
    pub fn shares_original_samples(&self, other: &Self) -> bool {
        let (Some(a), Some(b)) = (self.taps.first(), other.taps.first()) else {
            return false;
        };
        if a.site.acquisition_id != b.site.acquisition_id || a.site.plane != b.site.plane {
            return false;
        }
        let (mut i, mut j) = (0, 0);
        while i < self.taps.len() && j < other.taps.len() {
            let a = self.taps[i].site.quad;
            let b = other.taps[j].site.quad;
            match (a[1], a[0]).cmp(&(b[1], b[0])) {
                std::cmp::Ordering::Equal => return true,
                std::cmp::Ordering::Less => i += 1,
                std::cmp::Ordering::Greater => j += 1,
            }
        }
        false
    }
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Refusal {
    InvalidInput,
    Budget,
    MissingSupport,
    Clipped,
    UnknownExpectedSignal,
    NonFiniteArithmetic,
}

#[derive(Clone, Copy)]
struct Contribution {
    x: i64,
    y: i64,
    weights: [f32; MAX_BANDS],
}

fn weights(kernel: Kernel, f: f32) -> ([f32; 4], i64, usize) {
    match kernel {
        Kernel::Bilinear => ([1. - f, f, 0., 0.], 0, 2),
        Kernel::CatmullRom => {
            let f2 = f * f;
            let f3 = f2 * f;
            (
                [
                    -0.5 * f3 + f2 - 0.5 * f,
                    1.5 * f3 - 2.5 * f2 + 1.,
                    -1.5 * f3 + 2. * f2 + 0.5 * f,
                    0.5 * f3 - 0.5 * f2,
                ],
                -1,
                4,
            )
        }
    }
}

/// Observe fixed filters in one original acquisition. `frozen_expected` returns
/// a black-subtracted expected signal in that original source's DN. It must be
/// frozen independently of the target noise being assessed; this function does
/// not fit, smooth or otherwise invent an expected signal. None means unknown.
/// The caller must retain guide provenance and its original-sample dependencies.
///
/// All four planes share sensor coordinates, while interpolation retains each
/// plane's physical RGGB offset. No border replication or sample clamping occurs.
/// Canceled coefficients have no read, clipping or noise-model dependency.
pub fn observe(
    view: &OriginalView<'_>,
    full_quad: PlaneGeometry,
    center_sensor: [f64; 2],
    filters: &[&[FilterTap]],
    kernel: Kernel,
    budget_bytes: usize,
    mut frozen_expected: impl FnMut(OriginalSite) -> Option<f32>,
) -> Result<Observation, Refusal> {
    let geometry = view.source.geometry();
    let n = view.noise;
    let pull = view.color_pull;
    if geometry != full_quad
        || filters.is_empty()
        || filters.len() > MAX_BANDS
        || [
            geometry.width,
            geometry.height,
            full_quad.width,
            full_quad.height,
        ]
        .iter()
        .any(|&d| d == 0 || d > (1 << 30))
        || !center_sensor.iter().all(|x| x.is_finite())
        || ![pull.a.re, pull.a.im, pull.b.re, pull.b.im]
            .iter()
            .all(|x| x.is_finite())
        || pull.invert().is_none()
        || ![
            view.gain,
            n.gain_dn_per_e,
            n.read_noise_e,
            n.levels.black,
            n.levels.white,
        ]
        .iter()
        .all(|x| x.is_finite())
        || view.gain <= 0.
        || n.gain_dn_per_e <= 0.
        || n.read_noise_e < 0.
        || n.levels.black < 0.
        || n.levels.white > u16::MAX as f32
        || n.levels.white <= n.levels.black
        || filters.iter().any(|f| {
            f.is_empty()
                || f.len() > MAX_FILTER_TAPS
                || f.iter().any(|t| {
                    !t.weight.is_finite() || !t.offset_sensor.iter().all(|x| x.is_finite())
                })
        })
    {
        return Err(Refusal::InvalidInput);
    }
    let taps_per = match kernel {
        Kernel::Bilinear => 4,
        Kernel::CatmullRom => 16,
    };
    let capacity = filters
        .iter()
        .map(|f| f.len())
        .sum::<usize>()
        .checked_mul(taps_per)
        .ok_or(Refusal::Budget)?;
    let reservation_bytes = capacity
        .checked_mul(std::mem::size_of::<Contribution>() + std::mem::size_of::<OriginalTap>())
        .and_then(|x| x.checked_add(std::mem::size_of::<Observation>()))
        .ok_or(Refusal::Budget)?;
    if capacity > MAX_CONTRIBUTIONS || reservation_bytes > budget_bytes {
        return Err(Refusal::Budget);
    }
    let mut contributions = Vec::new();
    contributions
        .try_reserve_exact(capacity)
        .map_err(|_| Refusal::Budget)?;
    let (ox, oy) = view.plane.rggb_offset();
    for (band, filter) in filters.iter().enumerate() {
        for tap in *filter {
            if tap.weight == 0. {
                continue;
            }
            let qx = (center_sensor[0] + tap.offset_sensor[0] - 0.5) * 0.5;
            let qy = (center_sensor[1] + tap.offset_sensor[1] - 0.5) * 0.5;
            let (sx, sy) = pull.apply_at(
                qx,
                qy,
                full_quad.width as f64 * 0.5,
                full_quad.height as f64 * 0.5,
            );
            let x = sx + 0.25 - ox as f64 * 0.5;
            let y = sy + 0.25 - oy as f64 * 0.5;
            if !x.is_finite()
                || !y.is_finite()
                || x.abs() > (1u64 << 40) as f64
                || y.abs() > (1u64 << 40) as f64
            {
                return Err(Refusal::MissingSupport);
            }
            let (ix, iy) = (x.floor() as i64, y.floor() as i64);
            let (wx, start, count) = weights(kernel, (x - ix as f64) as f32);
            let (wy, _, _) = weights(kernel, (y - iy as f64) as f32);
            for (dy, &yv) in wy.iter().enumerate().take(count) {
                for (dx, &xv) in wx.iter().enumerate().take(count) {
                    let w = tap.weight * xv * yv;
                    if w != 0. {
                        let mut c = Contribution {
                            x: ix + start + dx as i64,
                            y: iy + start + dy as i64,
                            weights: [0.; MAX_BANDS],
                        };
                        c.weights[band] = w;
                        contributions.push(c);
                    }
                }
            }
        }
    }
    // Deterministic reduction, without a heap-allocating tree or sort.
    contributions.sort_unstable_by_key(|c| (c.y, c.x));
    // Equal-site input order is not mathematically significant, but deterministic
    // for a fixed input. No floating point threshold discards small coefficients.
    let mut used = 0;
    for read in 0..contributions.len() {
        let c = contributions[read];
        if used > 0 && contributions[used - 1].x == c.x && contributions[used - 1].y == c.y {
            for band in 0..filters.len() {
                contributions[used - 1].weights[band] += c.weights[band];
            }
        } else {
            contributions[used] = c;
            used += 1;
        }
    }
    contributions.truncate(used);
    contributions.retain(|c| c.weights.iter().any(|&w| w != 0.));
    let mut out = Observation {
        band_count: filters.len(),
        values: [0.; MAX_BANDS],
        covariance: [[0.; MAX_BANDS]; MAX_BANDS],
        taps: Vec::new(),
        reservation_bytes,
    };
    out.taps
        .try_reserve_exact(contributions.len())
        .map_err(|_| Refusal::Budget)?;
    for c in contributions {
        if c.x < 0 || c.y < 0 || c.x >= geometry.width as i64 || c.y >= geometry.height as i64 {
            return Err(Refusal::MissingSupport);
        }
        let site = OriginalSite {
            acquisition_id: view.acquisition_id,
            plane: view.plane,
            quad: [c.x as usize, c.y as usize],
        };
        let expected = frozen_expected(site)
            .filter(|s| s.is_finite())
            .ok_or(Refusal::UnknownExpectedSignal)?;
        let variance = n.variance(expected);
        let (r0, r1) = view.source.quad_rows(site.quad[1]);
        let row = if oy == 0 { r0 } else { r1 };
        let raw = *row
            .get(2 * site.quad[0] + ox)
            .ok_or(Refusal::MissingSupport)? as f32;
        if raw >= n.levels.white {
            return Err(Refusal::Clipped);
        }
        let value = raw - n.levels.black;
        let mut w = c.weights;
        for weight in w.iter_mut().take(filters.len()) {
            *weight *= view.gain;
        }
        for a in 0..filters.len() {
            out.values[a] += w[a] * value;
            for b in 0..filters.len() {
                out.covariance[a][b] += w[a] * w[b] * variance;
            }
        }
        out.taps.push(OriginalTap {
            site,
            band_weights: w,
            variance_dn2: variance,
        });
    }
    if !out
        .values
        .iter()
        .chain(out.covariance.iter().flatten())
        .all(|x| x.is_finite())
    {
        return Err(Refusal::NonFiniteArithmetic);
    }
    Ok(out)
}

/// Predeclared same-color-scale bands: high=identity-low1, mid=low1-low2,
/// low=low2. low1 is the separable [1,2,1]/4 filter at +/-2 SENSOR pixels;
/// low2 is its convolution with itself, [1,4,6,4,1]/16 at +/-4 sensor pixels.
pub fn binomial_bands() -> [Vec<FilterTap>; 3] {
    let mut bands: [Vec<FilterTap>; 3] = std::array::from_fn(|_| Vec::with_capacity(25));
    let a = [0., 0.25, 0.5, 0.25, 0.];
    let b = [1., 4., 6., 4., 1.].map(|x| x / 16.);
    for y in 0..5 {
        for x in 0..5 {
            let low1 = a[x] * a[y];
            let low2 = b[x] * b[y];
            let identity = if x == 2 && y == 2 { 1. } else { 0. };
            for (band, weight) in [identity - low1, low1 - low2, low2].into_iter().enumerate() {
                if weight != 0. {
                    bands[band].push(FilterTap {
                        offset_sensor: [(x as f64 - 2.) * 2., (y as f64 - 2.) * 2.],
                        weight,
                    });
                }
            }
        }
    }
    bands
}

#[cfg(test)]
#[path = "repeat-evidence-tests.rs"]
mod tests;
