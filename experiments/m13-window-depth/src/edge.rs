//! Depth discontinuities: planting them, and measuring what a focus stacker
//! does to them.
//!
//! # Why this module exists
//!
//! **No plant in M11 contained a depth discontinuity.** Every planted surface
//! was continuous — fronto-parallel or linearly tilted — and M11 disclosed that
//! as the most likely way its wide-window recommendation could be wrong. A wide
//! focus window is exactly the configuration that smears an occluding boundary,
//! and M11's per-pixel selectivity metric `S` **cannot see that damage**: a
//! haloed edge can elect the correct source frame at every individual pixel and
//! still look obviously wrong to a human, because the *frame it elected* is
//! itself contaminated at that pixel.
//!
//! So this module supplies two things M11 did not have: a physically honest
//! occluding-edge plant, and a metric that can see edge damage.
//!
//! # The plant: layered occlusion, not a depth map
//!
//! A "depth step" rendered by blurring each half-plane with its own sigma is
//! **wrong**, and wrong in the direction that hides the artifact. At a real
//! occluding boundary the near surface is *in front of* the far one, so when
//! focus is on the far surface the near surface's defocus blur **spreads across
//! the boundary and covers background that is genuinely there**. A per-region
//! blur has no spreading term at all and therefore plants no halo to find.
//!
//! The render is the standard two-layer alpha composite (Porter & Duff's `over`,
//! 1984 — textbook compositing, and no GPL source was consulted for it):
//!
//! ```text
//! sigma_n(k) = sigma0 + alpha * |k - w_near|      near layer's defocus at frame k
//! sigma_f(k) = sigma0 + alpha * |k - w_far|       far layer's defocus at frame k
//!
//! N_k = blur(T_near * M, sigma_n(k))              pre-multiplied near layer
//! A_k = blur(M,          sigma_n(k))              its coverage
//! F_k = blur(T_far,      sigma_f(k))              far layer, which exists everywhere behind
//!
//! I_k = N_k + (1 - A_k) * F_k
//! ```
//!
//! `M` is the occluder's hard binary mask. Pre-multiplying `T_near` by `M`
//! before the blur and blurring `M` itself with the same kernel is what makes
//! the composite correct: the near layer's energy and its coverage spread
//! together, so `I_k` is a convex combination of real content at every pixel and
//! no invented brightness appears at the boundary.
//!
//! **The ideal output falls out of the same formula.** Setting `k = w_near =
//! w_far` gives every layer its own best focus at once:
//!
//! ```text
//! ideal = blur(T_near * M, sigma0) + (1 - blur(M, sigma0)) * blur(T_far, sigma0)
//! ```
//!
//! which is exactly the all-in-focus image a perfect stacker should produce.
//! **This makes the `Delta-w = 0` null exact by construction**, not merely
//! approximate: when `w_near == w_far == w`, frame `w` *is* `ideal`, asserted in
//! this module's tests. That is a much stronger null than "the metric happened
//! to read small", because it removes the depth step while keeping the intensity
//! edge, the two textures, the compositing arithmetic and the noise.
//!
//! **Nothing here resamples** (SYNTHESIS §5 item 11). The blur is a separable
//! Gaussian evaluated on the integer lattice; the mask is generated on the
//! lattice; no sub-pixel shift exists anywhere in the module.
//!
//! # The metric: two numbers, because one of them is blind on its own
//!
//! 1. **Bleed width `W_bleed`, in plane px.** Fraction of pixels at signed
//!    distance `d` from the boundary whose elected frame is nearer the *wrong*
//!    layer's depth than the right one, minus that fraction's own far-field
//!    baseline, summed over `d`. This is an **equivalent width**: it needs no
//!    threshold, it is in pixels, and against a selection map built by dilating
//!    the occluder mask by `R` px it returns exactly `R`. That exact
//!    recoverability is what makes it a metric and not a statistic.
//!
//! 2. **Excess edge error `H`, in DN and in units of the single-frame noise
//!    sigma.** `RMS(merged - ideal)` inside a band around the boundary, **minus
//!    the same quantity for the oracle selector** on the same frames. The
//!    subtraction is load-bearing: at an occluding boundary *no* per-pixel
//!    selector can reconstruct `ideal`, because every frame has the near layer
//!    spilling over the far one by some amount. `E_oracle` is that irreducible
//!    physical floor, and `H` is what the selector adds on top of it.
//!
//! Each sees what the other cannot. `W_bleed` is blind to a selector that is
//! uniformly wrong everywhere (no distance structure to integrate) and blind to
//! error inside the elected frame. `H` is blind to mis-selection between two
//! frames that happen to look alike at that pixel. Both are reported always.

use strehl_core::noise::NoiseModel;
use strehl_core::plane::PlaneGeometry;

use crate::planted::{add_noise, gaussian_blur};

/// Where the occluding boundary runs, and what shape the occluder is.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum EdgeGeometry {
    /// Occluder fills `x < at`. Signed distance is `x - at`, exact.
    Vertical { at: usize },
    /// Occluder fills `y < at`. The orientation control: a Sobel-based operator
    /// is not isotropic, so a result that only holds on one axis is an artifact.
    Horizontal { at: usize },
    /// A bar of the given half-width centred at `at`, i.e. the "hair in front of
    /// a background" case that macro photographers actually complain about. Two
    /// boundaries `2*half_width` apart, so the halos from each side can collide.
    Bar { at: usize, half_width: usize },
}

impl EdgeGeometry {
    /// Signed distance from the boundary at tile pixel `(x, y)`: negative
    /// inside the occluder, positive outside, zero on the first covered pixel.
    ///
    /// For `Bar` the distance is to the *nearer* of its two boundaries, which is
    /// what makes the two halos superpose in the profile rather than cancel.
    #[inline]
    pub fn signed_distance(self, x: usize, y: usize) -> i32 {
        match self {
            EdgeGeometry::Vertical { at } => x as i32 - at as i32,
            EdgeGeometry::Horizontal { at } => y as i32 - at as i32,
            EdgeGeometry::Bar { at, half_width } => {
                let u = (x as i32 - at as i32).abs();
                u - half_width as i32
            }
        }
    }

    #[inline]
    pub fn is_occluder(self, x: usize, y: usize) -> bool {
        self.signed_distance(x, y) < 0
    }

    pub fn as_str(self) -> String {
        match self {
            EdgeGeometry::Vertical { at } => format!("vertical@{at}"),
            EdgeGeometry::Horizontal { at } => format!("horizontal@{at}"),
            EdgeGeometry::Bar { at, half_width } => format!("bar@{at}w{}", 2 * half_width),
        }
    }
}

/// One planted occluding-edge scene.
#[derive(Clone, Copy, Debug)]
pub struct EdgeSpec {
    pub frames: usize,
    /// Frame at which the **occluder** (near layer) is in focus.
    pub w_near: usize,
    /// Frame at which the **background** (far layer) is in focus.
    /// `w_far == w_near` is the exact null: no depth step at all.
    pub w_far: usize,
    /// Blur sigma of an in-focus layer, in plane px. Must be > 0 — a ladder
    /// starting at 0 hands the in-focus frame more noise than its neighbours
    /// (see `planted.rs`, module docs point 3).
    pub sigma0: f32,
    /// Extra blur sigma per frame of defocus mismatch, in plane px.
    pub alpha: f32,
    pub noise_scale: f32,
    pub seed: u64,
    pub geometry: EdgeGeometry,
}

impl EdgeSpec {
    pub fn depth_step(&self) -> i32 {
        self.w_far as i32 - self.w_near as i32
    }

    /// Widest blur any layer reaches, which is what the tile margin must clear.
    pub fn max_blur_radius(&self) -> usize {
        let last = self.frames.saturating_sub(1) as i32;
        let dn = (self.w_near as i32).max(last - self.w_near as i32);
        let df = (self.w_far as i32).max(last - self.w_far as i32);
        let s = self.sigma0 + self.alpha * dn.max(df) as f32;
        (3.0 * s).ceil() as usize
    }
}

/// A rendered scene: the frames a stacker would see, plus everything needed to
/// score what it did with them.
pub struct EdgeScene {
    /// Noisy frames — what the operator selects on and what the merge copies.
    pub frames: Vec<Vec<f32>>,
    /// The same frames with `noise_scale = 0`. Only ever used to build the
    /// oracle reference, never fed to an operator.
    pub clean: Vec<Vec<f32>>,
    /// The all-in-focus image: every layer at `sigma0`, hard occlusion.
    pub ideal: Vec<f32>,
    /// Per-pixel correct frame index over the whole tile.
    pub truth: Vec<u16>,
    /// The occluder's binary mask over the whole tile.
    pub mask: Vec<f32>,
}

impl EdgeScene {
    /// Render the scene from two real textures.
    ///
    /// `tex_near` and `tex_far` must be distinct real image content of the same
    /// tile geometry — the milestone brief requires the textures be real so the
    /// noise and detail statistics are honest, and requires them independent so
    /// that "the selector chose the wrong layer" is actually detectable.
    ///
    /// `dilate_selection` is the **positive control hook**: it is not used in
    /// rendering at all, and exists only so a caller can build a selection map
    /// with a halo of known width. See `halo_positive_control`.
    pub fn render(
        tex_near: &[f32],
        tex_far: &[f32],
        geom: PlaneGeometry,
        spec: EdgeSpec,
        noise: Option<&NoiseModel>,
    ) -> Self {
        let n = geom.pixels();
        assert_eq!(tex_near.len(), n);
        assert_eq!(tex_far.len(), n);

        let mut mask = vec![0.0f32; n];
        let mut truth = vec![0u16; n];
        for y in 0..geom.height {
            for x in 0..geom.width {
                let p = y * geom.width + x;
                if spec.geometry.is_occluder(x, y) {
                    mask[p] = 1.0;
                    truth[p] = spec.w_near as u16;
                } else {
                    truth[p] = spec.w_far as u16;
                }
            }
        }

        let premul: Vec<f32> = tex_near.iter().zip(&mask).map(|(t, m)| t * m).collect();

        let composite = |sigma_n: f32, sigma_f: f32| -> Vec<f32> {
            let mut near = vec![0.0f32; n];
            let mut cover = vec![0.0f32; n];
            let mut far = vec![0.0f32; n];
            gaussian_blur(&premul, geom, sigma_n, &mut near);
            gaussian_blur(&mask, geom, sigma_n, &mut cover);
            gaussian_blur(tex_far, geom, sigma_f, &mut far);
            (0..n)
                .map(|i| near[i] + (1.0 - cover[i]) * far[i])
                .collect()
        };

        let ideal = composite(spec.sigma0, spec.sigma0);

        let clean: Vec<Vec<f32>> = (0..spec.frames)
            .map(|k| {
                let dn = (k as i32 - spec.w_near as i32).unsigned_abs() as f32;
                let df = (k as i32 - spec.w_far as i32).unsigned_abs() as f32;
                composite(spec.sigma0 + spec.alpha * dn, spec.sigma0 + spec.alpha * df)
            })
            .collect();

        let frames: Vec<Vec<f32>> = match (noise, spec.noise_scale > 0.0) {
            (Some(model), true) => clean
                .iter()
                .enumerate()
                .map(|(k, f)| {
                    let mut out = vec![0.0f32; n];
                    add_noise(
                        f,
                        model,
                        spec.noise_scale,
                        spec.seed
                            .wrapping_mul(0x0100_0000_01B3)
                            .wrapping_add(k as u64 + 1),
                        &mut out,
                    );
                    out
                })
                .collect(),
            _ => clean.clone(),
        };

        EdgeScene {
            frames,
            clean,
            ideal,
            truth,
            mask,
        }
    }

    /// The best output any per-pixel frame selector can produce on these frames:
    /// take the ground-truth frame at every pixel, from the **noise-free** stack.
    ///
    /// Noise-free because the point of this reference is to isolate the
    /// *selection* error from the noise the selector inherits — otherwise the
    /// irreducible floor would move with the noise realisation and `H` would
    /// stop being a property of the window.
    pub fn oracle(&self) -> Vec<f32> {
        self.truth
            .iter()
            .enumerate()
            .map(|(p, k)| self.clean[*k as usize][p])
            .collect()
    }
}

/// The per-distance profile both headline numbers are read off.
pub struct EdgeProfile {
    /// Signed distance in plane px; negative inside the occluder.
    pub d: Vec<i32>,
    /// Fraction electing a frame nearer the wrong layer's depth than the right.
    pub wrong: Vec<f64>,
    /// Fraction electing exactly the ground-truth frame — M11's `S`, resolved by
    /// distance from the boundary.
    pub exact: Vec<f64>,
    /// `RMS(merged - ideal)` in DN.
    pub e_merged: Vec<f64>,
    /// `RMS(oracle - ideal)` in DN — the irreducible physical floor.
    pub e_oracle: Vec<f64>,
    /// `mean(merged - ideal)` in DN. Carries the *sign* of the artifact, which
    /// is what a human sees as a bright or dark fringe; RMS cannot show it.
    pub bias: Vec<f64>,
    pub count: Vec<usize>,
}

/// Everything the caller records for one `(operator, window, regulariser)` cell.
#[derive(Clone, Copy, Debug, Default)]
pub struct EdgeSummary {
    /// Equivalent width of the mis-selection bleed on the **background** side,
    /// in plane px, baseline-subtracted.
    pub bleed_bg: f64,
    /// The same on the occluder side.
    pub bleed_fg: f64,
    /// `mean_band(e_merged) - mean_band(e_oracle)`, in DN, over `|d| <= band`.
    pub excess_dn: f64,
    /// The same divided by the single-frame noise sigma of the ROI, so it can be
    /// read as "how many noise sigmas of damage".
    pub excess_sigma: f64,
    /// `mean_band(e_merged)` in DN — the total, un-subtracted error in the band.
    pub band_rms: f64,
    /// `mean_band(e_oracle)` in DN — the irreducible floor in the band.
    pub floor_rms: f64,
    /// `RMS(merged - ideal)` **outside** the band, i.e. the smooth-surface half
    /// of the objective, in DN.
    pub far_rms: f64,
    /// Per-pixel election accuracy over the whole tile interior — M11's `S`, so
    /// the two metrics can be compared on identical data.
    pub acc: f64,
    /// Election accuracy restricted to `|d| <= band`.
    pub acc_band: f64,
    /// Peak absolute signed bias over the background side of the band, in DN.
    pub peak_bias: f64,
}

/// Bands, baselines and the interior inset, in one place so the analysis and the
/// controls cannot silently disagree about them.
#[derive(Clone, Copy, Debug)]
pub struct ProfileConfig {
    /// Distances `|d| <= band` count as "at the edge".
    pub band: i32,
    /// Distances in `[baseline_lo, baseline_hi]` define the far-field baseline.
    /// Must lie beyond any halo the sweep can produce, which is checked by
    /// asserting the baseline is small.
    pub baseline_lo: i32,
    pub baseline_hi: i32,
    /// Maximum `|d|` retained in the profile.
    pub max_d: i32,
}

impl Default for ProfileConfig {
    fn default() -> Self {
        Self {
            band: 24,
            baseline_lo: 96,
            baseline_hi: 128,
            max_d: 128,
        }
    }
}

/// Build the signed-distance profile of a selection map against a scene.
///
/// `region` selects which tile pixels are scored — the caller passes the ROI
/// interior, inset far enough that no scored pixel's operator window was
/// clamped at the tile border.
#[allow(clippy::too_many_arguments)]
pub fn profile(
    scene: &EdgeScene,
    geom: PlaneGeometry,
    spec: EdgeSpec,
    selection: &[u16],
    merged: &[f32],
    oracle: &[f32],
    region: &[usize],
    cfg: ProfileConfig,
) -> EdgeProfile {
    let span = (2 * cfg.max_d + 1) as usize;
    let off = cfg.max_d;
    let mut wrong = vec![0.0f64; span];
    let mut exact = vec![0.0f64; span];
    let mut se_m = vec![0.0f64; span];
    let mut se_o = vec![0.0f64; span];
    let mut bias = vec![0.0f64; span];
    let mut count = vec![0usize; span];

    for &p in region {
        let (x, y) = (p % geom.width, p / geom.width);
        let d = spec.geometry.signed_distance(x, y);
        if d.abs() > cfg.max_d {
            continue;
        }
        let bin = (d + off) as usize;
        let sel = selection[p] as i32;
        let (right, other) = if d < 0 {
            (spec.w_near as i32, spec.w_far as i32)
        } else {
            (spec.w_far as i32, spec.w_near as i32)
        };
        // Strictly nearer the wrong layer. A tie is not counted as damage: with
        // `w_near == w_far` (the null) every pixel ties, so the null reads
        // exactly zero rather than one half.
        if (sel - other).abs() < (sel - right).abs() {
            wrong[bin] += 1.0;
        }
        if sel == scene.truth[p] as i32 {
            exact[bin] += 1.0;
        }
        let em = (merged[p] - scene.ideal[p]) as f64;
        let eo = (oracle[p] - scene.ideal[p]) as f64;
        se_m[bin] += em * em;
        se_o[bin] += eo * eo;
        bias[bin] += em;
        count[bin] += 1;
    }

    let mut out = EdgeProfile {
        d: Vec::new(),
        wrong: Vec::new(),
        exact: Vec::new(),
        e_merged: Vec::new(),
        e_oracle: Vec::new(),
        bias: Vec::new(),
        count: Vec::new(),
    };
    for bin in 0..span {
        if count[bin] == 0 {
            continue;
        }
        let n = count[bin] as f64;
        out.d.push(bin as i32 - off);
        out.wrong.push(wrong[bin] / n);
        out.exact.push(exact[bin] / n);
        out.e_merged.push((se_m[bin] / n).sqrt());
        out.e_oracle.push((se_o[bin] / n).sqrt());
        out.bias.push(bias[bin] / n);
        out.count.push(count[bin]);
    }
    out
}

/// Median of a slice, by value. Local so nothing depends on sort order elsewhere.
fn median(mut v: Vec<f64>) -> f64 {
    if v.is_empty() {
        return 0.0;
    }
    v.sort_by(|a, b| a.partial_cmp(b).unwrap());
    let n = v.len();
    if n % 2 == 1 {
        v[n / 2]
    } else {
        0.5 * (v[n / 2 - 1] + v[n / 2])
    }
}

/// Equivalent width of the bleed on one side of the boundary, in plane px.
///
/// ```text
/// W = sum over d in [1, baseline_lo) of max(0, wrong(d) - baseline)
/// ```
///
/// with `baseline = median(wrong(d))` over the far band. No threshold, no fit,
/// and against a mask dilated by exactly `R` px it returns exactly `R` — which
/// is the positive control and is asserted in `selftest`.
///
/// `sign` is `+1` for the background side and `-1` for the occluder side.
pub fn bleed_width(p: &EdgeProfile, cfg: ProfileConfig, sign: i32) -> f64 {
    let base = median(
        p.d.iter()
            .zip(&p.wrong)
            .filter(|(d, _)| {
                let u = **d * sign;
                u >= cfg.baseline_lo && u <= cfg.baseline_hi
            })
            .map(|(_, w)| *w)
            .collect(),
    );
    p.d.iter()
        .zip(&p.wrong)
        .filter(|(d, _)| {
            let u = **d * sign;
            (1..cfg.baseline_lo).contains(&u)
        })
        .map(|(_, w)| (*w - base).max(0.0))
        .sum()
}

/// Summarise a profile into the recorded row.
pub fn summarise(
    p: &EdgeProfile,
    cfg: ProfileConfig,
    single_sigma: f64,
    acc: f64,
    far_rms: f64,
) -> EdgeSummary {
    let in_band = |d: i32| d.abs() <= cfg.band;
    let mean_of = |sel: &dyn Fn(usize) -> f64| -> f64 {
        let mut num = 0.0;
        let mut den = 0.0;
        for (i, d) in p.d.iter().enumerate() {
            if in_band(*d) {
                num += sel(i) * p.count[i] as f64;
                den += p.count[i] as f64;
            }
        }
        if den > 0.0 {
            num / den
        } else {
            0.0
        }
    };
    let band_rms = mean_of(&|i| p.e_merged[i]);
    let floor_rms = mean_of(&|i| p.e_oracle[i]);
    let acc_band = mean_of(&|i| p.exact[i]);
    let peak_bias =
        p.d.iter()
            .zip(&p.bias)
            .filter(|(d, _)| (0..=cfg.band).contains(*d))
            .map(|(_, b)| b.abs())
            .fold(0.0f64, f64::max);
    EdgeSummary {
        bleed_bg: bleed_width(p, cfg, 1),
        bleed_fg: bleed_width(p, cfg, -1),
        excess_dn: band_rms - floor_rms,
        excess_sigma: if single_sigma > 0.0 {
            (band_rms - floor_rms) / single_sigma
        } else {
            0.0
        },
        band_rms,
        floor_rms,
        far_rms,
        acc,
        acc_band,
        peak_bias,
    }
}

/// The positive control for `bleed_width`: a selection map whose halo is planted
/// at a known width.
///
/// Every pixel within `radius` px on the background side of the boundary is set
/// to the occluder's frame; everything else is ground truth. `bleed_width` must
/// return `radius` **exactly**, because `wrong(d) = 1` for `d` in `[0, radius)`
/// and `0` beyond, and the far baseline is `0`.
///
/// Note the off-by-one convention this fixes: `d = 0` is the first *covered*
/// pixel (it is background at distance zero), so a dilation that reaches `d <
/// radius` spans radii `0 .. radius-1`, and the sum in `bleed_width` runs from
/// `d = 1`, giving `radius - 1`. The control asserts the value it actually
/// produces rather than the value that sounds right, and the report quotes
/// widths on that convention throughout.
pub fn halo_positive_control(
    scene: &EdgeScene,
    geom: PlaneGeometry,
    spec: EdgeSpec,
    radius: i32,
) -> Vec<u16> {
    let mut sel = scene.truth.clone();
    for y in 0..geom.height {
        for x in 0..geom.width {
            let d = spec.geometry.signed_distance(x, y);
            if (0..radius).contains(&d) {
                sel[y * geom.width + x] = spec.w_near as u16;
            }
        }
    }
    sel
}

#[cfg(test)]
mod tests {
    use super::*;

    fn geom() -> PlaneGeometry {
        PlaneGeometry {
            width: 320,
            height: 96,
        }
    }

    fn textures(g: PlaneGeometry) -> (Vec<f32>, Vec<f32>) {
        let near: Vec<f32> = (0..g.pixels())
            .map(|i| 1500.0 + 200.0 * ((i % 13) as f32 * 0.7).sin())
            .collect();
        let far: Vec<f32> = (0..g.pixels())
            .map(|i| 2500.0 + 300.0 * ((i % 29) as f32 * 0.3).cos())
            .collect();
        (near, far)
    }

    fn spec(step: i32) -> EdgeSpec {
        EdgeSpec {
            frames: 21,
            w_near: 4,
            w_far: (4 + step) as usize,
            sigma0: 0.8,
            alpha: 0.35,
            noise_scale: 0.0,
            seed: 7,
            geometry: EdgeGeometry::Vertical { at: 160 },
        }
    }

    #[test]
    fn a_zero_depth_step_renders_the_ideal_image_exactly() {
        let g = geom();
        let (near, far) = textures(g);
        let s = spec(0);
        let scene = EdgeScene::render(&near, &far, g, s, None);
        for (a, b) in scene.clean[4].iter().zip(scene.ideal.iter()) {
            assert!((a - b).abs() < 1e-2, "{a} vs {b}");
        }
    }

    #[test]
    fn the_positive_control_recovers_its_planted_width() {
        let g = geom();
        let (near, far) = textures(g);
        let s = spec(8);
        let scene = EdgeScene::render(&near, &far, g, s, None);
        let cfg = ProfileConfig {
            band: 24,
            baseline_lo: 96,
            baseline_hi: 128,
            max_d: 140,
        };
        let region: Vec<usize> = (0..g.pixels()).collect();
        let oracle = scene.oracle();
        for r in [0, 1, 5, 13, 31] {
            let sel = halo_positive_control(&scene, g, s, r);
            let merged: Vec<f32> = sel
                .iter()
                .enumerate()
                .map(|(p, k)| scene.frames[*k as usize][p])
                .collect();
            let p = profile(&scene, g, s, &sel, &merged, &oracle, &region, cfg);
            let got = bleed_width(&p, cfg, 1);
            let want = (r - 1).max(0) as f64;
            assert!(
                (got - want).abs() < 1e-9,
                "planted {r} px -> recovered {got}, expected {want}"
            );
        }
    }

    #[test]
    fn the_null_reads_zero_on_ground_truth() {
        let g = geom();
        let (near, far) = textures(g);
        let s = spec(8);
        let scene = EdgeScene::render(&near, &far, g, s, None);
        let cfg = ProfileConfig {
            band: 24,
            baseline_lo: 96,
            baseline_hi: 128,
            max_d: 140,
        };
        let region: Vec<usize> = (0..g.pixels()).collect();
        let oracle = scene.oracle();
        let p = profile(&scene, g, s, &scene.truth, &oracle, &oracle, &region, cfg);
        assert!(bleed_width(&p, cfg, 1).abs() < 1e-12);
        assert!(bleed_width(&p, cfg, -1).abs() < 1e-12);
    }
}
