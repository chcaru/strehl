//! Edge-aware selection support: a focus window that does not cross a depth
//! discontinuity.
//!
//! # The defect this exists to remove
//!
//! [`crate::focus::FocusField`] aggregates gradient magnitude over a box of
//! radius [`WINDOW_RADIUS`] = 13. At a background pixel `p` lying within 13 px
//! of an occluding silhouette, that box also contains **foreground** content.
//! In the frame `k_F` where the foreground is sharp, the box sum at `p` is
//! dominated by the foreground's gradient energy, so the argmax elects `k_F`
//! for a pixel that is background. `p` is then rendered from a frame in which
//! its own content is defocused, and veiled by the foreground's defocus spill.
//! That band is the occlusion halo.
//!
//! # It is our length scale, and it is measured
//!
//! M121 measured the rim at `w50 = 10.0 px` with a `13.25 px` cutoff against
//! `WINDOW_RADIUS = 13`, and checked and rejected three physical alternatives
//! (SYNTHESIS facts 1778-1781). BUILD-HALO turned that single match into a
//! **dose-response** on `bee-3-cpl` at gate 0, one build, sweeping
//! [`crate::focus::WINDOW_RADIUS_ENV`]:
//!
//! | `WINDOW_RADIUS` | 3 | 6 | 9 | 13 | 20 | 26 |
//! | --- | --- | --- | --- | --- | --- | --- |
//! | rim `w50`, px | 8.75 | 8.75 | 9.50 | 10.75 | 19.00 | 25.75 |
//! | rim cutoff, px | 9.25 | 9.75 | 10.75 | 14.00 | 21.25 | 29.00 |
//!
//! Over `w9..w26`, where the instrument is clear of its own transition
//! exclusion, the cutoff is linear in the radius with slope **1.07** and
//! intercept **1.08** — that is `SOBEL_RADIUS + WINDOW_RADIUS`, the focus
//! operator's own [`SUPPORT_RADIUS`](crate::focus::SUPPORT_RADIUS), 1:1 over a
//! 3x range. The rim is the window.
//!
//! # Why the guide is elected at a NARROW radius
//!
//! The obvious construction — take pass one's winner field, find its depth
//! steps, shrink the window there — **does not work, and the ladder above is
//! what says so.** The winner field is itself haloed: the foreground's elected
//! frame is painted across the background out to one window radius, so the step
//! in `W` sits at `d ~ 13 px` from the true silhouette, not at `d = 0`. A window
//! truncated at that step still swallows the silhouette. The correction would
//! have to be iterated once per pixel of halo.
//!
//! So the guide is elected at [`GUIDE_RADIUS`] instead. Its own halo is 2-3 px
//! wide, so its steps sit on the true silhouette. It is noisy in low-contrast
//! regions — that is exactly why the shipped selection radius is wide — but it
//! is only ever read *near a strong luminance step*, where the focus measure is
//! far above its noise floor. The narrow field is used to locate edges, never
//! to elect the output.
//!
//! # What the scale map is
//!
//! For each pixel, the largest radius in [`LEVEL_RADII`] whose box does not
//! span more than `tau` frames of the (speckle-smoothed) guide. Equivalently a
//! quantised distance transform away from the silhouette: hard against the
//! edge the support collapses to 1 px, and it is back to the full 13 px by
//! 13 px out. Support is therefore **maximal everywhere it is safe** — this is
//! not a global window shrink, and the flat-field election is untouched.

use crate::boxfilter::box_mean;
use crate::focus::WINDOW_RADIUS;
use crate::plane::PlaneGeometry;

// ---------------------------------------------------------------------------
// Edge-aware smoothing: the domain transform
// ---------------------------------------------------------------------------

/// Iterations of the domain-transform recursive filter.
///
/// Three is the value the method is specified with. The filter is a one-tap
/// IIR, so a single pass is a decaying exponential whose impulse response is
/// visibly asymmetric; iterating with a geometrically-shrinking scale sums to
/// something very close to a Gaussian. Two is visibly boxy on a step, four
/// costs a third more for no visible change.
pub const DT_ITERATIONS: u32 = 3;

/// Edge-stopping scale of the guided regulariser, in units of the plane's own
/// **median absolute luma gradient**.
///
/// Not a DN threshold: it is normalised by a robust statistic of the image it
/// is running on, so it does not carry a brightness scale across stacks
/// (AGENTS.md). A neighbour whose luma differs by this much is half-stopped.
///
/// The value is deliberately loose. The regulariser only has to refuse to
/// cross an **occluding silhouette**, which is the largest luma step in a macro
/// frame by a wide margin; refusing to cross ordinary subject texture as well
/// would cost the noise averaging this filter exists to provide.
pub const DT_SIGMA_R: f32 = 12.0;

/// One-dimensional domain-transform recursive filter, run in place along rows.
///
/// `dom` holds the per-pixel domain derivative: the accumulated "distance"
/// from a pixel to its left neighbour, which is `1` in a flat region and grows
/// with the luma step between them. Feedback is `a^dom`, so a large step drives
/// the feedback to zero and the filter simply restarts on the far side. That is
/// the whole edge-awareness mechanism, and it is why this costs the same as a
/// box filter regardless of radius.
fn dt_rows(sig: &mut [f32], dom: &[f32], w: usize, h: usize, a: f32) {
    for y in 0..h {
        let row = &mut sig[y * w..(y + 1) * w];
        let d = &dom[y * w..(y + 1) * w];
        for x in 1..w {
            let v = a.powf(d[x]);
            row[x] += v * (row[x - 1] - row[x]);
        }
        for x in (0..w - 1).rev() {
            // `d[x + 1]` is the same edge, read from the other side: the
            // distance between x and x+1 is stored at x+1. Using `d[x]` here
            // would shift the filter by one pixel per pass and smear the very
            // steps it exists to respect.
            let v = a.powf(d[x + 1]);
            row[x] += v * (row[x + 1] - row[x]);
        }
    }
}

/// Transpose, so the vertical pass is the row pass on cache-friendly memory.
fn transpose(src: &[f32], w: usize, h: usize, dst: &mut [f32]) {
    // Blocked, because the naive loop is a cache miss per element and this runs
    // four times per frame per fold.
    const B: usize = 32;
    for y0 in (0..h).step_by(B) {
        for x0 in (0..w).step_by(B) {
            for y in y0..(y0 + B).min(h) {
                for x in x0..(x0 + B).min(w) {
                    dst[x * h + y] = src[y * w + x];
                }
            }
        }
    }
}

/// Edge-aware replacement for a box mean over the focus field, guided by the
/// **observed luma of the very frame whose focus field this is**.
///
/// # Why this has to exist
///
/// The election's total spill is a composition of *two* box cascades, not one:
/// [`crate::focus::SUPPORT_RADIUS`] = `SOBEL_RADIUS + WINDOW_RADIUS` = 14, then
/// [`crate::merge::REGULARISER_RADIUS`] = 8, for 22 px. Shrinking only the
/// focus window leaves the regulariser averaging the newly-correct narrow
/// responses straight back across the silhouette, which re-manufactures a rim
/// of its own radius. Measured at every step of the ladder in the module
/// header: the rim tracks the *total* support, so both cascades have to be told
/// about the depth step or neither is.
///
/// # Why the guide is this frame's own luma, and not the depth guide
///
/// The narrow depth guide is *itself* haloed — its rim is 2-3 px, which is
/// small but not zero, and BUILD-HALO measured a tight bright sheath surviving
/// precisely because the rim was narrower than the guide that was supposed to
/// mask it. **A mask cannot exclude what its own input has already mislabelled.**
/// The observed luma has no such circularity: it is the measurement, prior to
/// any election, so it cannot inherit the election's error.
///
/// Per-frame is also the physically correct choice. In the frame where the
/// foreground is sharp its silhouette is a hard luma step, so that frame's
/// focus field — the one whose spill *is* the halo — is stopped hardest. In
/// frames where the foreground is defocused the step is soft and the filter
/// smooths through it, which is correct, because there is no occluding edge in
/// that frame's focus field to protect.
///
/// `sigma_s` is in pixels and plays the role of the box radius. `scratch`,
/// `tmp` and `dom` are all `geom.pixels()` long and are overwritten.
pub fn domain_transform(
    focus: &[f32],
    luma: &[f32],
    geom: PlaneGeometry,
    sigma_s: f32,
    dst: &mut [f32],
    scratch: &mut [f32],
    tmp: &mut [f32],
    dom: &mut [f32],
) {
    let (w, h) = (geom.width, geom.height);
    let px = geom.pixels();
    assert_eq!(focus.len(), px);
    assert_eq!(luma.len(), px);

    // Robust normaliser for the luma gradient. The median of |dI/dx| over the
    // plane is dominated by the defocused background on a macro frame, so it
    // sits at the noise floor and an occluding silhouette is hundreds of times
    // it. Sampled on a stride to keep this O(px/17) rather than a full sort.
    let mut samp: Vec<f32> = Vec::with_capacity(px / 17 + 1);
    for y in 0..h {
        for x in 1..w {
            if (y * w + x) % 17 == 0 {
                samp.push((luma[y * w + x] - luma[y * w + x - 1]).abs());
            }
        }
    }
    let scale = if samp.is_empty() {
        1.0
    } else {
        samp.sort_unstable_by(|a, b| a.partial_cmp(b).unwrap_or(core::cmp::Ordering::Equal));
        samp[samp.len() / 2].max(f32::MIN_POSITIVE)
    };
    let k = 1.0 / (DT_SIGMA_R * scale);

    dst.copy_from_slice(focus);

    for it in 0..DT_ITERATIONS {
        // Geometrically shrinking scale, so the iterations sum to sigma_s.
        let n = DT_ITERATIONS;
        let sigma_h = sigma_s * 3.0f32.sqrt() * (2.0f32).powi((n - 1 - it) as i32)
            / ((4.0f32).powi(n as i32) - 1.0).sqrt();
        let a = (-(2.0f32).sqrt() / sigma_h.max(1e-6)).exp();

        // Horizontal.
        for y in 0..h {
            dom[y * w] = 1.0;
            for x in 1..w {
                let i = y * w + x;
                dom[i] = 1.0 + k * (luma[i] - luma[i - 1]).abs();
            }
        }
        dt_rows(dst, dom, w, h, a);

        // Vertical, as a transposed horizontal pass.
        transpose(dst, w, h, scratch);
        transpose(luma, w, h, tmp);
        for x in 0..w {
            dom[x * h] = 1.0;
            for y in 1..h {
                let i = x * h + y;
                dom[i] = 1.0 + k * (tmp[i] - tmp[i - 1]).abs();
            }
        }
        dt_rows(scratch, dom, h, w, a);
        transpose(scratch, h, w, dst);
    }
}

/// The radii the support may take, ascending. The last is [`WINDOW_RADIUS`],
/// so a pixel far from any depth step elects on exactly the shipped operator.
pub const LEVEL_RADII: [usize; 5] = [1, 2, 4, 8, WINDOW_RADIUS];

/// Level index of the full, shipped radius.
pub const FULL_LEVEL: u8 = (LEVEL_RADII.len() - 1) as u8;

/// Radius the depth guide is elected at. Level 1 of [`LEVEL_RADII`].
///
/// Small enough that its own halo cannot displace the silhouette it is used to
/// locate, and large enough (a `5x5` mean of the gradient magnitude, 25 taps)
/// that it is not a single-pixel decision. It is deliberately the same radius
/// as [`FINE_WINDOW_RADIUS`](crate::focus::FINE_WINDOW_RADIUS), which M21
/// measured as the scale at which occlusion bimodality is *visible* (4.38x
/// enrichment) rather than destroyed (0.36x at the selection radius). The
/// guide is looking for exactly that structure.
pub const GUIDE_LEVEL: u8 = 1;

/// Radius the winner-field speckle is averaged over before its local range is
/// taken.
///
/// A range is a max minus a min and is the least robust spread there is: on a
/// 299-frame stack the raw winner field speckles by a few frames even on flat,
/// well-decided ground, and an unsmoothed range over a `27x27` box would read
/// that speckle as a depth step and collapse the support over the whole frame.
/// A step survives this mean; speckle does not.
const SPECKLE_RADIUS: usize = 2;

/// Per-pixel selection support, as an index into [`LEVEL_RADII`].
#[derive(Debug, Clone)]
pub struct SelectionScale {
    geom: PlaneGeometry,
    level: Vec<u8>,
}

impl SelectionScale {
    /// A constant-radius map. `SelectionScale::uniform(geom, FULL_LEVEL)` is
    /// the shipped operator exactly, and is how the guide pass asks for a
    /// narrow radius without a second code path.
    #[must_use]
    pub fn uniform(geom: PlaneGeometry, level: u8) -> Self {
        assert!((level as usize) < LEVEL_RADII.len(), "level {level} unknown");
        Self {
            geom,
            level: vec![level; geom.pixels()],
        }
    }

    /// Build the scale map from a **narrow-radius** guide winner field.
    ///
    /// `tau` is the number of frames of guide variation a box is allowed to
    /// span before it is judged to cross a depth discontinuity. It is in
    /// frames, so it is a property of the bracket and not of the sensor.
    ///
    /// `response` is the guide election's own winning focus value per pixel.
    /// **It is not optional and the fix does not work without it.** In a
    /// defocused background no frame is in focus, so the narrow guide's argmax
    /// is noise and is distributed across the whole bracket; its local range is
    /// then ~N frames everywhere and the range test alone marks the entire
    /// background as a depth discontinuity. Measured on `bee-3-cpl` at 299
    /// frames, the range test alone treated **47.53%** of the plane and put
    /// **24.67%** of it at a 1 px support, which raised background |grad| by
    /// **31.4%** — a noise explosion, not a halo fix. A pixel is only treated
    /// when there is genuinely sharp content within reach of its window.
    ///
    /// `min_level` floors the support. Radius 1 and 2 are real settings of this
    /// operator but they are not sound *elections*: the argmax of N noisy
    /// responses is biased upward by roughly `sd * sqrt(2 ln N)`, and at 299
    /// frames a 3x3 box mean of the gradient magnitude is nowhere near enough
    /// support to survive that. The floor is what keeps the cure smaller than
    /// the disease.
    ///
    /// `conf` is in multiples of the plane's own **median** guide response, so
    /// it is a property of this image and not a DN threshold carried across
    /// stacks (AGENTS.md). On a macro frame the majority of the plane is
    /// defocused background, which puts the median at the noise floor.
    ///
    /// Passing a *wide*-radius winner field here is the one way to use this
    /// module wrong; see the module header. Nothing can detect that from the
    /// slice alone, which is why the guide radius is a named constant here
    /// rather than a caller's choice.
    #[must_use]
    pub fn from_guide(
        winner: &[u16],
        response: &[f32],
        geom: PlaneGeometry,
        tau: f32,
        min_level: u8,
        conf: f32,
    ) -> Self {
        assert_eq!(winner.len(), geom.pixels());
        assert_eq!(response.len(), geom.pixels());
        assert!(tau > 0.0, "tau must be positive, got {tau}");
        assert!((min_level as usize) < LEVEL_RADII.len(), "min_level {min_level}");
        let px = geom.pixels();

        // Speckle-smooth the guide. `u16::MAX` is `FocusStats`' "no frame"
        // sentinel; it cannot survive into an arithmetic mean, so it is
        // replaced by the local mean's other members via a two-pass approach:
        // undecided pixels are simply excluded from being *sources* by
        // carrying them at the plane median. In a completed fold there are
        // none, and this is the guard, not the path.
        let mut w: Vec<f32> = winner.iter().map(|&k| f32::from(k)).collect();
        let decided: Vec<f32> = w.iter().copied().filter(|v| *v < 65535.0).collect();
        if decided.len() < px {
            let fill = if decided.is_empty() {
                0.0
            } else {
                decided.iter().sum::<f32>() / decided.len() as f32
            };
            for v in w.iter_mut() {
                if *v >= 65535.0 {
                    *v = fill;
                }
            }
        }
        let mut scratch = vec![0.0f32; px];
        let mut smooth = vec![0.0f32; px];
        crate::boxfilter::box_mean(&w, geom, SPECKLE_RADIUS, &mut scratch, &mut smooth);

        // Nested dilations/erosions: a box max of radius `a` composed with one
        // of radius `b` is a box max of radius `a + b`, exactly, so the five
        // radii cost 3+3+5+9+11 taps per axis instead of 3+5+9+17+27.
        let mut hi = smooth.clone();
        let mut lo = smooth.clone();
        let mut level = vec![0u8; px];
        let mut prev = 0usize;
        for (l, &r) in LEVEL_RADII.iter().enumerate() {
            let step = r - prev;
            prev = r;
            box_extremum(&mut hi, geom, step, &mut scratch, true);
            box_extremum(&mut lo, geom, step, &mut scratch, false);
            for i in 0..px {
                if hi[i] - lo[i] <= tau {
                    level[i] = l as u8;
                }
            }
        }

        // The confidence veto. `sharp` is the strongest guide response within
        // one full window, so a pixel is treated only when the window it is
        // about to have taken away actually contains sharp content. Both sides
        // of the comparison are a max-over-window, so the upward bias that an
        // extremum carries over noise cancels instead of having to be modelled.
        let mut sharp = response.to_vec();
        for v in sharp.iter_mut() {
            if !v.is_finite() {
                *v = 0.0;
            }
        }
        box_extremum(&mut sharp, geom, LEVEL_RADII[FULL_LEVEL as usize], &mut scratch, true);
        let floor = conf * percentile(&sharp, FLOOR_Q);
        for i in 0..px {
            level[i] = if sharp[i] > floor {
                level[i].max(min_level)
            } else {
                FULL_LEVEL
            };
        }
        Self { geom, level }
    }

    /// Choose each pixel's window radius from the **calibrated noise model**,
    /// capped by its distance to the nearest depth discontinuity.
    ///
    /// # The rule
    ///
    /// ```text
    /// radius(p) = min( r_noise(p), r_geom(p) )
    /// ```
    ///
    /// `r_noise` is the **smallest** radius at which this pixel's through-focus
    /// peak still clears the calibrated noise floor by `margin`. `r_geom` is
    /// the distance to the nearest depth step, so no window ever spans a
    /// silhouette. Away from edges the noise term binds and the window is as
    /// small as the sensor allows; against a silhouette the geometry term binds
    /// and the window collapses.
    ///
    /// # Why this is not [`from_guide`](Self::from_guide), which failed
    ///
    /// `from_guide` shrank the window wherever the guide saw an edge, with no
    /// check that the smaller window could still elect. It cut support from 729
    /// samples to 81, the argmax of 299 noisy responses became close to random,
    /// and background `|grad|` rose **31.4%** — a noise explosion traded for a
    /// halo. The missing half of that rule was any reason to believe the
    /// smaller window was *sufficient*. That reason is the noise model, which
    /// this project has calibrated and which is the whole thesis: the radius is
    /// not a constant to be tuned, it is a quantity to be **solved for** per
    /// pixel.
    ///
    /// # The scaling law
    ///
    /// The focus measure is a box mean of `|grad|` over `(2r+1)^2` samples, so
    /// its noise falls as the square root of the sample count:
    ///
    /// ```text
    /// sd(r) = FOCUS_NOISE_SD * (2 * WINDOW_RADIUS + 1) / (2r + 1)
    /// ```
    ///
    /// [`FOCUS_NOISE_SD`](crate::merge::FOCUS_NOISE_SD) is calibrated *at*
    /// `WINDOW_RADIUS`, which is why it appears against that reference rather
    /// than bare. Reading a constant calibrated at radius 13 as though it held
    /// at another radius is a live miscalibration this build has already paid
    /// for once; here the radius is explicit on both sides, so it cannot be
    /// read wrong silently.
    ///
    /// `margin` is in the same units as [`crate::merge::Gate`]'s threshold:
    /// multiples of the standard deviation of a *difference* of two independent
    /// responses, hence the `sqrt(2)`.
    ///
    /// # What binds where, and what pays for it
    ///
    /// On flat background near a silhouette the noise term asks for a *large*
    /// window — correctly; there is nothing there to discriminate with — and
    /// the geometry term overrides it to a small one. The election there is
    /// then genuinely under-determined. **That is accepted deliberately.** When
    /// no frame has content at a pixel, every frame renders it almost
    /// identically, so an arbitrary election is invisible. What is emphatically
    /// *not* invisible is electing the frame in which a defocused foreground is
    /// spilling across that pixel, which is what the uncapped window does, and
    /// which is the halo. The residual scatter is what the guided regulariser
    /// ([`domain_transform`]) is for. That is precisely the trade being made:
    /// buy noise robustness with edge-aware smoothing, not with window radius.
    #[must_use]
    pub fn from_acuity(
        excess: &[f32],
        guide: &[u16],
        geom: PlaneGeometry,
        tau: f32,
        margin: f32,
    ) -> Self {
        assert_eq!(excess.len(), geom.pixels());
        assert_eq!(guide.len(), geom.pixels());
        assert!(margin > 0.0, "margin must be positive, got {margin}");
        assert!(tau > 0.0, "tau must be positive, got {tau}");
        let px = geom.pixels();
        let mut scratch = vec![0.0f32; px];

        // --- r_noise -------------------------------------------------------
        //
        // The *signal* `excess` reports is radius-independent to first order: a
        // box mean of a locally homogeneous quantity does not depend on the
        // box. So the same excess can be put to every candidate radius, and the
        // only question is whether that radius' noise floor is low enough to
        // resolve it. Ascending order, first hit wins, so this is the SMALLEST
        // sufficient radius.
        let sd_at = |r: usize| {
            crate::merge::FOCUS_NOISE_SD * (2 * WINDOW_RADIUS + 1) as f32 / (2 * r + 1) as f32
        };
        let need: Vec<f32> = LEVEL_RADII
            .iter()
            .map(|&r| margin * core::f32::consts::SQRT_2 * sd_at(r))
            .collect();
        let mut level = vec![FULL_LEVEL; px];
        for i in 0..px {
            for (l, n) in need.iter().enumerate() {
                if excess[i] >= *n {
                    level[i] = l as u8;
                    break;
                }
            }
        }

        // --- r_geom --------------------------------------------------------
        //
        // A pixel sits on a depth step when the guide varies by more than `tau`
        // frames across its box. The dilate/erode pair is a local range, and
        // composing radius steps gives the range at successively larger radii
        // for a few taps per axis each, exactly as `from_guide` does.
        //
        // Reading outward from the silhouette, the first radius at which a
        // pixel's box catches the step is its cap: it may use every radius
        // strictly below that, and none at or above it.
        let mut w: Vec<f32> = guide.iter().map(|&k| f32::from(k)).collect();
        let decided: Vec<f32> = w.iter().copied().filter(|v| *v < 65535.0).collect();
        let fill = if decided.is_empty() {
            0.0
        } else {
            decided.iter().sum::<f32>() / decided.len() as f32
        };
        for v in w.iter_mut() {
            if *v >= 65535.0 {
                *v = fill;
            }
        }
        let mut smooth = vec![0.0f32; px];
        box_mean(&w, geom, SPECKLE_RADIUS, &mut scratch, &mut smooth);

        let mut hi = smooth.clone();
        let mut lo = smooth;
        let mut capped = vec![false; px];
        let mut prev = 0usize;
        for (l, &r) in LEVEL_RADII.iter().enumerate() {
            box_extremum(&mut hi, geom, r - prev, &mut scratch, true);
            box_extremum(&mut lo, geom, r - prev, &mut scratch, false);
            prev = r;
            for i in 0..px {
                // The range is monotone in the radius, so the first failure is
                // the cap and no later level may raise it back.
                if !capped[i] && hi[i] - lo[i] > tau {
                    capped[i] = true;
                    level[i] = level[i].min(l.saturating_sub(1) as u8);
                }
            }
        }
        Self { geom, level }
    }

    #[must_use]
    pub fn geometry(&self) -> PlaneGeometry {
        self.geom
    }

    #[must_use]
    pub fn levels(&self) -> &[u8] {
        &self.level
    }

    /// How many pixels sit at each level. For the render log: a scale map that
    /// is all-`FULL_LEVEL` is a no-op and a map that is mostly level 0 has
    /// collapsed the whole election, and both are worth seeing before the
    /// image is judged.
    #[must_use]
    pub fn histogram(&self) -> [usize; LEVEL_RADII.len()] {
        let mut h = [0usize; LEVEL_RADII.len()];
        for &l in &self.level {
            h[l as usize] += 1;
        }
        h
    }

    /// Fraction of the plane whose support was reduced below the shipped radius.
    #[must_use]
    pub fn treated_fraction(&self) -> f64 {
        let n = self.level.iter().filter(|&&l| l < FULL_LEVEL).count();
        n as f64 / self.level.len().max(1) as f64
    }

    /// True when every pixel is at the shipped radius, so the caller can skip
    /// the multi-scale path entirely and stay bit-identical.
    #[must_use]
    pub fn is_full_everywhere(&self) -> bool {
        self.level.iter().all(|&l| l == FULL_LEVEL)
    }
}

/// Gather `src` into a per-pixel multi-scale aggregate.
///
/// `per_level[l]` must already hold the level-`l` field over the whole plane;
/// `dst[i]` takes `per_level[level[i]][i]`. Factored out so the focus operator
/// and the merge regulariser select levels through identical code — a
/// disagreement between them would put the election and the gate on different
/// supports without anything noticing.
pub fn gather_levels(levels: &[u8], per_level: &[&[f32]], dst: &mut [f32]) {
    assert_eq!(levels.len(), dst.len());
    for (i, d) in dst.iter_mut().enumerate() {
        let l = levels[i] as usize;
        *d = per_level[l.min(per_level.len() - 1)][i];
    }
}

/// Value at quantile `q` of the finite entries of `v`.
///
/// The confidence veto needs a reference for "dead ground", and the deadest
/// ground in the frame is the quietest place in it, so a low percentile of the
/// response estimates the noise ceiling far more robustly than the median. The
/// median moves with how much of the plane happens to be subject, which varies
/// enormously between a bee filling the frame and a pencil tip in a corner.
fn percentile(v: &[f32], q: f32) -> f32 {
    let mut w: Vec<f32> = v.iter().copied().filter(|x| x.is_finite()).collect();
    if w.is_empty() {
        return 0.0;
    }
    let k = (((w.len() - 1) as f32) * q).round().clamp(0.0, (w.len() - 1) as f32) as usize;
    w.select_nth_unstable_by(k, |a, b| a.total_cmp(b));
    w[k]
}

/// Quantile used as the dead-ground reference for the confidence veto.
pub const FLOOR_Q: f32 = 0.10;

/// Separable box max (`want_max`) or min, radius `radius`, clamped to the
/// plane, **in place**.
///
/// Border policy matches [`crate::boxfilter::box_mean`]: the window is
/// intersected with the plane rather than padded, so no read leaves the buffer
/// and no invented value can enter an extremum.
fn box_extremum(
    buf: &mut [f32],
    geom: PlaneGeometry,
    radius: usize,
    scratch: &mut [f32],
    want_max: bool,
) {
    if radius == 0 {
        return;
    }
    let (w, h) = (geom.width, geom.height);
    if w == 0 || h == 0 {
        return;
    }
    let pick = |a: f32, b: f32| if want_max { a.max(b) } else { a.min(b) };

    for y in 0..h {
        let row = &buf[y * w..(y + 1) * w];
        let out = &mut scratch[y * w..(y + 1) * w];
        for x in 0..w {
            let a = x.saturating_sub(radius);
            let b = (x + radius).min(w - 1);
            let mut acc = row[a];
            for v in &row[a + 1..=b] {
                acc = pick(acc, *v);
            }
            out[x] = acc;
        }
    }
    for y in 0..h {
        let a = y.saturating_sub(radius);
        let b = (y + radius).min(h - 1);
        for x in 0..w {
            let mut acc = scratch[a * w + x];
            for yy in a + 1..=b {
                acc = pick(acc, scratch[yy * w + x]);
            }
            buf[y * w + x] = acc;
        }
    }
}

/// Depth-layer masked support: the operator that actually removes the halo.
///
/// # Why the scale ladder above is not enough
///
/// [`SelectionScale`] attacks the contamination by making the window smaller
/// than the distance to the discontinuity. That works, and it is what the
/// dose-response predicts, but it pays for the halo with the election's own
/// statistical power. At `--gate 0` the merge is a pure *selection* — the
/// gate census reports `n_eff = 1.000` on every pixel — so the output pixel IS
/// the elected frame's sample, and an election made on 81 gradient samples
/// (radius 4) instead of 729 (radius 13) elects a visibly more random frame.
/// Measured on `bee-3-cpl` across four operating points, every scale-ladder arm
/// moved the M121 statistic the WRONG way. Shrinking support is the wrong
/// lever.
///
/// # What this does instead
///
/// Keep the full 13 px radius and drop only the samples that do not belong to
/// the pixel's own depth. For a background pixel one radius outside a
/// silhouette, roughly half its window is still background, so the masked
/// support is ~350 samples rather than 81 — it discards the contamination
/// without discarding the statistics.
///
/// The exact operator is a joint bilateral filter of the gradient magnitude,
/// with the range term driven by the *narrow* guide winner field:
///
/// ```text
/// focus_k(p) = sum_q g_k(q) K(w(q) - w(p)) / sum_q K(w(q) - w(p))
/// ```
///
/// which is not separable as written. It is made separable exactly the way a
/// bilateral grid is: quantise the range axis into [`N_LAYERS`] bins, run one
/// ordinary separable box filter per bin, and have each pixel read the bin its
/// own guide winner falls in. The cost is `N_LAYERS + 1` box filters per frame
/// in place of one, which is the same order as the scale ladder it replaces.
///
/// Because `box_mean` normalises numerator and denominator by the identical
/// window area, the border handling cancels and the ratio is the exact masked
/// mean at every pixel including the edges of the plane.
///
/// # The support floor
///
/// A pixel whose own layer occupies too little of its window (a hair, an
/// antenna) would get a masked mean off a handful of samples, which is the
/// scale ladder's failure again by another route. [`MIN_LAYER_FRACTION`] is the
/// guard: below it the pixel keeps the shipped full-window response.
pub struct LayerSupport {
    geom: PlaneGeometry,
    /// Depth bin per treated pixel, or [`UNTREATED`].
    layer: Vec<u8>,
    /// Position on the depth axis in **bin-centre units**, for every pixel.
    ///
    /// This is the continuous value `bin` is the rounding of, and it is what
    /// makes the grid interpolated rather than quantised. Hard-assigning each
    /// pixel to one bin makes two neighbours whose guide winners differ by a
    /// hair use two completely different supports, and that discontinuity was
    /// visible as blotching at treated transitions.
    pos: Vec<f32>,
    /// How much of the masked response each pixel takes, in `[0, 1]`.
    ///
    /// Treatment used to be a hard switch, and that put a **cliff at the
    /// treatment boundary**: a masked pixel and its full-window neighbour
    /// could differ by far more than either differed from the truth, which
    /// read as hard-edged blobs hugging silhouettes. Interpolating the depth
    /// axis does not help — the discontinuity is in whether the pixel is
    /// treated at all, not in which bin it landed. So every guard that used to
    /// veto now ramps instead, and the three ramps multiply.
    blend: Vec<f32>,
    /// `(radius, fractions)` where `fractions[l] = box_mean(tent(pos - l), radius)`:
    /// the **tent-weighted** share of each window belonging to layer `l`.
    /// Frame-independent, so it is computed once per radius and shared across
    /// every worker.
    fractions: Vec<(usize, Vec<Vec<f32>>)>,
}

/// Width of the feather on every guard, as a multiple of its threshold.
///
/// The guards multiply, so a wide feather compounds: at 2.0 a pixel would have
/// to clear twice the depth step AND twice the confidence floor AND twice the
/// support floor to be treated at full strength, and almost none do. That
/// silently applies the fix at partial strength everywhere and leaves halo on
/// the plate. Keep the transition thin -- enough to remove the cliff, not
/// enough to dilute the treatment.
pub const FEATHER: f32 = 1.25;

/// Environment override for [`FEATHER`], so the constant can be chosen from
/// real composites rather than from a synthetic probe.
pub const FEATHER_ENV: &str = "STREHL_EDGE_FEATHER";

/// Feather width actually in force, from [`FEATHER_ENV`] or [`FEATHER`].
#[must_use]
pub fn feather() -> f32 {
    static CACHED: std::sync::OnceLock<f32> = std::sync::OnceLock::new();
    *CACHED.get_or_init(|| match std::env::var(FEATHER_ENV) {
        Err(_) => FEATHER,
        Ok(s) => {
            let v: f32 = s.trim().parse().unwrap_or_else(|_| {
                panic!("{FEATHER_ENV}={s:?} is not a number")
            });
            assert!(
                v > 1.0 && v.is_finite(),
                "{FEATHER_ENV}={v} must exceed 1.0; at 1.0 the guards are hard \
                 switches again and the treatment boundary is a cliff"
            );
            v
        }
    })
}

/// Through-focus bimodality at a pixel, folded over the frames as they stream.
///
/// # Why this exists
///
/// Masking can only *choose* among samples that exist. The pixels nearest a
/// silhouette have no clean background sample in **any** frame, which is why
/// both the tight rim and the coverage-boundary blobs survived every masking
/// and feathering change. Reconstructing them needs the forward model
/// `I_k = a*(F conv PSF_k) + (1-a)*(B conv PSF_k)`, and **this is its
/// detector**: at an occluding edge the through-focus response is genuinely
/// bimodal, one peak where the foreground is sharp and one where the
/// background is.
///
/// # The streaming approximation
///
/// Storing a full response curve per pixel is `frames * 4` bytes per pixel --
/// 9.8 GB on a 299-frame bracket at this sensor. Instead this keeps the two
/// strongest peaks that are at least [`MODE_SEPARATION`] frames apart, updated
/// in one pass. Two `(f32, u16)` pairs is 12 bytes per pixel, constant in the
/// frame count, so it rides the guide pass at no extra decode cost.
///
/// The approximation is that a peak can be absorbed by a stronger neighbour
/// before its own true maximum arrives. For two well-separated modes -- which
/// is the only case this is asked about -- that does not change which two
/// modes are found.
pub struct BimodalStats {
    geom: PlaneGeometry,
    r1: Vec<f32>,
    k1: Vec<u16>,
    r2: Vec<f32>,
    k2: Vec<u16>,
    /// Running `sum` and `sum of squares` of the through-focus response, for
    /// the per-pixel baseline both peaks are judged against.
    ///
    /// This exists because the obvious statistic is wrong. Measured on
    /// `bee-2-cpl`: a plain `r2 / r1` ratio fires on **54.2%** of clean
    /// defocused ground, and at any threshold controlling that false-positive
    /// rate the near-silhouette pixels fire **3-4x LESS** than clean ground
    /// (enrichment 0.27x / 0.32x). The reason is that on featureless ground
    /// *neither* peak is real, so the ratio tends to 1 by noise alone —
    /// `r2 / r1` measures the ABSENCE of a dominant peak, not the presence of
    /// two. It is the same defect as `edge_overshoot`: an unnormalised ratio
    /// reports whatever dominates its denominator.
    ///
    /// Normalising against [`crate::merge::FOCUS_NOISE_SD`] would not fix it
    /// either, because that constant is calibrated for
    /// [`WINDOW_RADIUS`](crate::focus::WINDOW_RADIUS) and the guide runs at
    /// radius 4. The pixel's own curve is the only baseline available that is
    /// correct at whatever radius it is handed.
    sum: Vec<f64>,
    sumsq: Vec<f64>,
    /// `u16::MAX` marks a mode that has not been populated yet.
    frames: u32,
}

/// Smallest gap, in frames, between two peaks for them to count as separate
/// modes rather than one peak sampled twice.
///
/// A single in-focus peak has a through-focus width set by the depth of field;
/// `edge_tau` solves to ~36 frames on `bee-3-cpl` for the depth STEP, so a
/// separation floor well inside that would re-detect one peak as two.
pub const MODE_SEPARATION: u16 = 20;

impl BimodalStats {
    #[must_use]
    pub fn new(geom: PlaneGeometry) -> Self {
        let px = geom.pixels();
        Self {
            geom,
            r1: vec![f32::NEG_INFINITY; px],
            k1: vec![u16::MAX; px],
            r2: vec![f32::NEG_INFINITY; px],
            k2: vec![u16::MAX; px],
            sum: vec![0.0; px],
            sumsq: vec![0.0; px],
            frames: 0,
        }
    }

    #[inline]
    fn offer(&mut self, i: usize, r: f32, k: u16) {
        let far = |a: u16, b: u16| a != u16::MAX && b != u16::MAX && a.abs_diff(b) >= MODE_SEPARATION;
        if self.k1[i] == u16::MAX || !far(k, self.k1[i]) {
            // Same mode as the incumbent leader (or the first sample seen).
            if r > self.r1[i] {
                self.r1[i] = r;
                self.k1[i] = k;
            }
            return;
        }
        if self.k2[i] != u16::MAX && !far(k, self.k2[i]) {
            if r > self.r2[i] {
                self.r2[i] = r;
                self.k2[i] = k;
            }
        } else if r > self.r2[i] {
            self.r2[i] = r;
            self.k2[i] = k;
        }
        if self.r2[i] > self.r1[i] {
            let (rr, kk) = (self.r1[i], self.k1[i]);
            self.r1[i] = self.r2[i];
            self.k1[i] = self.k2[i];
            self.r2[i] = rr;
            self.k2[i] = kk;
        }
    }

    /// Fold one frame's focus response. `response` must be the **narrow**
    /// (guide-radius) field: a 13 px window smears the two modes into one and
    /// is exactly the measurement this is trying to see past.
    pub fn fold(&mut self, frame_index: u16, response: &[f32]) -> Result<(), String> {
        if response.len() != self.geom.pixels() {
            return Err(format!(
                "frame {frame_index}: response is {} long, want {}",
                response.len(),
                self.geom.pixels()
            ));
        }
        for i in 0..response.len() {
            let r = response[i];
            if r.is_finite() {
                self.offer(i, r, frame_index);
                self.sum[i] += f64::from(r);
                self.sumsq[i] += f64::from(r) * f64::from(r);
            }
        }
        self.frames += 1;
        Ok(())
    }

    pub fn absorb(&mut self, other: &Self) -> Result<(), String> {
        if other.geom != self.geom {
            return Err("cannot absorb a different geometry".to_string());
        }
        for i in 0..self.geom.pixels() {
            if other.k1[i] != u16::MAX {
                self.offer(i, other.r1[i], other.k1[i]);
            }
            if other.k2[i] != u16::MAX {
                self.offer(i, other.r2[i], other.k2[i]);
            }
            self.sum[i] += other.sum[i];
            self.sumsq[i] += other.sumsq[i];
        }
        self.frames += other.frames;
        Ok(())
    }

    /// Baseline mean and SD of each pixel's own through-focus response.
    fn baseline(&self, i: usize) -> (f32, f32) {
        let n = f64::from(self.frames).max(1.0);
        let mu = self.sum[i] / n;
        let var = (self.sumsq[i] / n - mu * mu).max(0.0);
        (mu as f32, (var.sqrt()) as f32)
    }

    /// Significance of the **second** mode, in standard deviations of the
    /// pixel's own through-focus response.
    ///
    /// This is the discriminating quantity, and the first mode is not: `r1` is
    /// the maximum by construction, so it is significant almost everywhere. A
    /// genuine occluding-edge pixel is one where a *second*, well-separated
    /// peak also stands clear of the pixel's own baseline — the foreground
    /// coming sharp in one bracket and the background in another.
    ///
    /// Returns 0 where no separated second peak exists.
    #[must_use]
    pub fn second_mode_z(&self) -> Vec<f32> {
        (0..self.geom.pixels())
            .map(|i| {
                if self.k2[i] == u16::MAX || !self.r2[i].is_finite() {
                    return 0.0;
                }
                let (mu, sd) = self.baseline(i);
                if !(sd > 0.0) {
                    return 0.0;
                }
                ((self.r2[i] - mu) / sd).max(0.0)
            })
            .collect()
    }

    /// Significance of the first (strongest) mode, same units. Reported only
    /// so the second can be read against it -- a pixel where *neither* peak
    /// clears the baseline is featureless ground, not a bimodal edge, and the
    /// two numbers together say which.
    #[must_use]
    pub fn first_mode_z(&self) -> Vec<f32> {
        (0..self.geom.pixels())
            .map(|i| {
                if self.k1[i] == u16::MAX || !self.r1[i].is_finite() {
                    return 0.0;
                }
                let (mu, sd) = self.baseline(i);
                if !(sd > 0.0) {
                    return 0.0;
                }
                ((self.r1[i] - mu) / sd).max(0.0)
            })
            .collect()
    }

    /// Raw height of the through-focus peak above the pixel's own baseline, in
    /// **focus units** rather than z-units.
    ///
    /// This is the discrimination the election actually has to work with: how
    /// far the winning frame's response stands above the typical frame's. It is
    /// deliberately *not* normalised by the pixel's own scatter, because the
    /// adaptive-radius rule has to compare it against the **calibrated** noise
    /// model — the entire point is to spend window radius only where the sensor
    /// says it is needed, and a self-normalised statistic has already divided
    /// exactly that information out.
    ///
    /// Debiased. The maximum of `n` noisy responses stands above the truth by
    /// roughly `sd * sqrt(2 ln n)` even when there is no peak at all, so on
    /// featureless ground the raw excess is pure upward bias — at 299 frames
    /// that is `3.4 sd` of pure artefact. Subtracting the expected bias makes
    /// "zero" mean "no resolvable peak", which is the reading
    /// [`SelectionScale::from_acuity`] needs. Clamped at zero, because a
    /// negative excess is not evidence of anti-focus.
    #[must_use]
    pub fn peak_excess(&self) -> Vec<f32> {
        let n = self.frames.max(2) as f32;
        let bias = (2.0 * n.ln()).sqrt();
        (0..self.geom.pixels())
            .map(|i| {
                if self.k1[i] == u16::MAX || !self.r1[i].is_finite() {
                    return 0.0;
                }
                let (mu, sd) = self.baseline(i);
                (self.r1[i] - mu - bias * sd).max(0.0)
            })
            .collect()
    }

    /// Balance between the two modes: `z2 / z1`, in `[0, 1]`.
    ///
    /// **This is the discriminating quantity, and the one to build on.**
    /// Measured across three subjects, from the silhouette outward:
    ///
    /// | subject | rim | far | swing |
    /// |---|---|---|---|
    /// | `bee-2-cpl` | 0.838 | 0.115 | 7.3x |
    /// | `flower-bud-with-background-fern-cpl` | 0.873 | 0.166 | 5.3x |
    /// | `flower-inner-edge-cpl` | 0.751 | 0.086 | 8.8x |
    ///
    /// Monotonic in every distance band in all three. Near 1 at a silhouette,
    /// where the window holds comparable amounts of two depths and each comes
    /// sharp in a different bracket; near 0 on ordinary ground, where one
    /// depth dominates.
    ///
    /// It is *not* the naive `r2 / r1` ratio, which fails for the opposite
    /// reason — see the note on [`Self::sum`]. Both peaks are first referred
    /// to the pixel's own baseline, so a pixel with no real peak at all scores
    /// zero instead of one.
    ///
    /// The obvious objection — that anything would look elevated near an edge
    /// because there is more contrast there — is refuted rather than argued:
    /// [`Self::first_mode_z`] moves the *opposite* way over the same bands
    /// (3.17 -> 6.28, 3.01 -> 5.57, 3.32 -> 7.41), so the second mode is not
    /// riding a general rise in contrast.
    #[must_use]
    pub fn mode_balance(&self) -> Vec<f32> {
        let z1 = self.first_mode_z();
        let z2 = self.second_mode_z();
        (0..self.geom.pixels())
            .map(|i| if z1[i] > 0.0 { (z2[i] / z1[i]).clamp(0.0, 1.0) } else { 0.0 })
            .collect()
    }

    /// Frame distance between the two modes, or 0 where there is no second.
    #[must_use]
    pub fn separation(&self) -> Vec<u16> {
        (0..self.geom.pixels())
            .map(|i| {
                if self.k2[i] == u16::MAX {
                    0
                } else {
                    self.k1[i].abs_diff(self.k2[i])
                }
            })
            .collect()
    }

    #[must_use]
    pub fn frames_folded(&self) -> u32 {
        self.frames
    }

    #[must_use]
    pub fn allocated_bytes(&self) -> usize {
        self.geom.pixels() * (2 * size_of::<f32>() + 2 * size_of::<u16>() + 2 * size_of::<f64>())
    }
}

/// Hermite ramp from 0 at `lo` to 1 at `hi`. Used to turn every hard veto in
/// this module into a feathered one.
#[inline]
#[must_use]
pub fn smoothstep(lo: f32, hi: f32, v: f32) -> f32 {
    if !(hi > lo) {
        return f32::from(u8::from(v >= hi));
    }
    let t = ((v - lo) / (hi - lo)).clamp(0.0, 1.0);
    t * t * (3.0 - 2.0 * t)
}

/// Triangular (tent) weight of a sample at depth-axis position `p` against bin
/// `l`. Adjacent bins overlap, and the weights of the two bins straddling any
/// `p` sum to exactly 1, so the splat conserves mass.
#[inline]
#[must_use]
pub fn tent(p: f32, l: usize) -> f32 {
    (1.0 - (p - l as f32).abs()).max(0.0)
}

/// The two bins straddling `p`, and the blend weight of the upper one.
#[inline]
#[must_use]
fn straddle(p: f32) -> (usize, usize, f32) {
    let c = p.clamp(0.0, (N_LAYERS - 1) as f32);
    let l0 = c.floor() as usize;
    let l1 = (l0 + 1).min(N_LAYERS - 1);
    (l0, l1, c - l0 as f32)
}

/// Number of quantisation bins on the depth (guide-winner) axis.
///
/// Six over a 299-frame bracket is a bin width of ~50 frames, comfortably
/// finer than the depth steps the range test fires on (`tau` solves to 36
/// frames on `bee-3-cpl`) and coarse enough that each bin still holds enough
/// of the plane to support a 27x27 window.
pub const N_LAYERS: usize = 6;

/// Sentinel in [`LayerSupport::layers`]: this pixel uses the shipped
/// full-window response and is not touched.
pub const UNTREATED: u8 = u8::MAX;

/// Smallest share of a window that may belong to the pixel's own layer before
/// the masked mean is abandoned in favour of the shipped full-window one.
pub const MIN_LAYER_FRACTION: f32 = 0.12;

impl LayerSupport {
    /// Build the layer masks from a **narrow-radius** guide winner field.
    ///
    /// `tau`, `response` and `conf` mean exactly what they mean in
    /// [`SelectionScale::from_guide`], and the confidence veto is load-bearing
    /// here for the same reason: over defocused ground the guide's argmax is
    /// noise, and without the veto every one of those pixels would be handed a
    /// masked mean built from a random depth bin.
    #[must_use]
    pub fn from_guide(
        winner: &[u16],
        response: &[f32],
        geom: PlaneGeometry,
        tau: f32,
        conf: f32,
        radii: &[usize],
    ) -> Self {
        assert_eq!(winner.len(), geom.pixels());
        assert_eq!(response.len(), geom.pixels());
        assert!(tau > 0.0, "tau must be positive, got {tau}");
        assert!(!radii.is_empty(), "at least one support radius is required");
        let px = geom.pixels();
        let detect = *radii.iter().max().expect("non-empty");
        let mut scratch = vec![0.0f32; px];

        let mut w: Vec<f32> = winner
            .iter()
            .map(|&k| if k == u16::MAX { f32::NAN } else { f32::from(k) })
            .collect();
        let fill = percentile(&w, 0.5);
        for v in w.iter_mut() {
            if !v.is_finite() {
                *v = fill;
            }
        }

        // Speckle-smooth the guide before quantising, so single-pixel argmax
        // noise cannot move a pixel into a neighbouring depth bin on its own.
        let mut smooth = vec![0.0f32; px];
        box_mean(&w, geom, SPECKLE_RADIUS, &mut scratch, &mut smooth);

        // Bin the depth axis over the guide's own robust span. Using the
        // measured span rather than the frame count keeps the bins useful on a
        // shallow bracket, where all the winners sit in a narrow range.
        let (lo, hi) = (percentile(&smooth, 0.01), percentile(&smooth, 0.99));
        let width = ((hi - lo) / N_LAYERS as f32).max(1.0);
        // Continuous position on the depth axis, in bin-CENTRE units: bin `l`
        // is centred at `lo + (l + 0.5) * width`, so a pixel at value `v` sits
        // at `(v - lo) / width - 0.5`. `bin` is this rounded; `pos` keeps the
        // remainder, which is what the tent interpolates over.
        let pos: Vec<f32> = smooth
            .iter()
            .map(|&v| ((v - lo) / width - 0.5).clamp(0.0, (N_LAYERS - 1) as f32))
            .collect();
        let bin_of =
            |v: f32| -> u8 { (((v - lo) / width).floor().clamp(0.0, (N_LAYERS - 1) as f32)) as u8 };
        let bin: Vec<u8> = smooth.iter().map(|&v| bin_of(v)).collect();

        // Treat a pixel only where the guide really steps within a window AND
        // there is sharp content in reach to justify it.
        let mut hi_b = smooth.clone();
        let mut lo_b = smooth.clone();
        box_extremum(&mut hi_b, geom, detect, &mut scratch, true);
        box_extremum(&mut lo_b, geom, detect, &mut scratch, false);

        let mut sharp = response.to_vec();
        for v in sharp.iter_mut() {
            if !v.is_finite() {
                *v = 0.0;
            }
        }
        box_extremum(&mut sharp, geom, detect, &mut scratch, true);
        let floor = conf * percentile(&sharp, FLOOR_Q);

        let mut layer = vec![UNTREATED; px];
        let mut blend = vec![0.0f32; px];
        for i in 0..px {
            // Both guards ramp rather than switch. A pixel just over the depth
            // step or just over the confidence floor now takes only a sliver
            // of the masked response, so the treated region fades in instead
            // of starting at full strength against an untreated neighbour.
            let w = smoothstep(tau, feather() * tau, hi_b[i] - lo_b[i])
                * smoothstep(floor, feather() * floor, sharp[i]);
            if w > 0.0 {
                layer[i] = bin[i];
                blend[i] = w;
            }
        }

        let mut fractions: Vec<(usize, Vec<Vec<f32>>)> = Vec::with_capacity(radii.len());
        let mut ind = vec![0.0f32; px];
        for &r in radii {
            let mut per_layer = vec![vec![0.0f32; px]; N_LAYERS];
            for l in 0..N_LAYERS {
                for i in 0..px {
                    // Soft splat. Every pixel contributes to the two bins that
                    // straddle it, with weights summing to 1, so no sample is
                    // lost and no bin boundary is a cliff.
                    ind[i] = tent(pos[i], l);
                }
                box_mean(&ind, geom, r, &mut scratch, &mut per_layer[l]);
            }
            fractions.push((r, per_layer));
        }

        // Withdraw any pixel whose own support is too thin a slice of its
        // window to elect on, at ANY radius it will be used at. This is the
        // antenna case, and it is the scale ladder's failure mode arriving by
        // a different road. The test uses the same interpolated denominator
        // the merge will divide by, not the hard bin's share, and it too
        // ramps: support fading out is a fade back to the shipped response.
        for i in 0..px {
            if layer[i] == UNTREATED {
                continue;
            }
            let (l0, l1, a) = straddle(pos[i]);
            let thinnest = fractions
                .iter()
                .map(|(_, f)| (1.0 - a) * f[l0][i] + a * f[l1][i])
                .fold(f32::INFINITY, f32::min);
            blend[i] *= smoothstep(
                MIN_LAYER_FRACTION,
                feather() * MIN_LAYER_FRACTION,
                thinnest,
            );
            if blend[i] <= 0.0 {
                layer[i] = UNTREATED;
            }
        }

        Self {
            geom,
            layer,
            pos,
            blend,
            fractions,
        }
    }

    #[must_use]
    pub fn geometry(&self) -> PlaneGeometry {
        self.geom
    }

    #[must_use]
    pub fn layers(&self) -> &[u8] {
        &self.layer
    }

    /// How much of the masked response each pixel takes, in `[0, 1]`.
    ///
    /// Zero is untreated, one is fully masked, everything between is the
    /// feathered boundary. This is the map to consult when asking *where the
    /// fix reaches*, which is a different question from where a detector
    /// fires: the coverage boundary — pixels the guards wanted to treat but
    /// the layer floor withdrew from — sits at intermediate values here.
    #[must_use]
    pub fn blend(&self) -> &[f32] {
        &self.blend
    }

    /// Share of the plane whose support is masked to its own depth layer.
    #[must_use]
    pub fn treated_fraction(&self) -> f64 {
        let n = self.layer.iter().filter(|&&l| l != UNTREATED).count();
        n as f64 / self.layer.len() as f64
    }

    /// Per-layer treated counts, for the render log.
    #[must_use]
    pub fn histogram(&self) -> [usize; N_LAYERS] {
        let mut h = [0usize; N_LAYERS];
        for &l in &self.layer {
            if l != UNTREATED {
                h[l as usize] += 1;
            }
        }
        h
    }

    /// True when nothing is treated, so callers can take the shipped path and
    /// stay byte-identical rather than running an operator that is the identity.
    #[must_use]
    pub fn is_empty(&self) -> bool {
        self.layer.iter().all(|&l| l == UNTREATED)
    }

    /// Replace `dst` with the layer-masked mean of `src` at `radius` wherever a
    /// pixel is treated, leaving every other pixel exactly as the caller left
    /// it.
    ///
    /// `dst` must already hold the ordinary full-window box mean of `src` at the
    /// same radius; only the treated pixels are overwritten, which is what
    /// keeps the untreated majority bit-identical to the shipped operator.
    ///
    /// Because `box_mean` normalises numerator and denominator by the identical
    /// window area, the border handling cancels and the ratio is the exact
    /// masked mean at every pixel including the edges of the plane.
    pub fn apply_at(
        &self,
        src: &[f32],
        radius: usize,
        scratch: &mut [f32],
        tmp: &mut [f32],
        acc: &mut [f32],
        dst: &mut [f32],
    ) {
        let px = self.geom.pixels();
        assert_eq!(src.len(), px);
        assert_eq!(dst.len(), px);
        let fractions = &self
            .fractions
            .iter()
            .find(|(r, _)| *r == radius)
            .unwrap_or_else(|| {
                panic!("LayerSupport was not built for radius {radius}; pass it to from_guide")
            })
            .1;
        let hist = self.histogram();
        // A layer must be filtered if any treated pixel STRADDLES it, which is
        // not the same as any treated pixel rounding to it: a pixel at 2.4
        // draws on bins 2 and 3. Skipping on the hard histogram would silently
        // drop the upper half of every such blend.
        let mut needed = [false; N_LAYERS];
        for i in 0..px {
            if self.layer[i] != UNTREATED {
                let (l0, l1, _) = straddle(self.pos[i]);
                needed[l0] = true;
                needed[l1] = true;
            }
        }
        debug_assert!(
            hist.iter().enumerate().all(|(l, &n)| n == 0 || needed[l]),
            "every occupied hard bin must also be straddled"
        );
        // Accumulate the interpolated numerator and denominator separately.
        // `acc` holds one layer's box-filtered numerator at a time; `dst` is
        // built up as the tent-weighted blend of the two straddling layers,
        // and `num`/`den` keep the running totals.
        let mut num = vec![0.0f32; px];
        let mut den = vec![0.0f32; px];
        for l in 0..N_LAYERS {
            if !needed[l] {
                continue;
            }
            for i in 0..px {
                // Soft splat of the signal, matching the soft splat the
                // fractions were built from.
                tmp[i] = tent(self.pos[i], l) * src[i];
            }
            box_mean(tmp, self.geom, radius, scratch, acc);
            for i in 0..px {
                if self.layer[i] == UNTREATED {
                    continue;
                }
                let (l0, l1, a) = straddle(self.pos[i]);
                let w = if l == l0 { 1.0 - a } else { 0.0 } + if l == l1 { a } else { 0.0 };
                if w > 0.0 {
                    num[i] += w * acc[i];
                    den[i] += w * fractions[l][i];
                }
            }
        }
        for i in 0..px {
            if self.layer[i] != UNTREATED && den[i] > 0.0 {
                // `dst` arrives holding the shipped full-window response, so
                // this is a fade between the two, not a replacement.
                let b = self.blend[i];
                dst[i] = b * (num[i] / den[i]) + (1.0 - b) * dst[i];
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn geom(w: usize, h: usize) -> PlaneGeometry {
        PlaneGeometry {
            width: w,
            height: h,
        }
    }

    /// A response plane that clears the confidence veto everywhere, so the
    /// range/tau geometry can be tested on its own. The veto has its own tests.
    fn confident(g: PlaneGeometry) -> Vec<f32> {
        vec![100.0; g.pixels()]
    }

    /// `conf = 0` disables the veto: every positive response clears a floor of
    /// zero. The geometry tests use it so they measure one thing each.
    const VETO_OFF: f32 = 0.0;

    /// The veto is what makes the whole thing usable and it needs its own
    /// plant: a defocused background elects a RANDOM guide winner, whose local
    /// range is the whole bracket, and without the veto every one of those
    /// pixels is treated at the narrowest support. That is the exact failure
    /// measured on `bee-3-cpl` (47.53% of the plane treated, background |grad|
    /// up 31.4%).
    #[test]
    fn a_noisy_guide_over_dead_ground_is_not_treated() {
        let g = geom(96, 96);
        let mut state = 12345u32;
        let winner: Vec<u16> = (0..g.pixels())
            .map(|_| {
                state = state.wrapping_mul(1664525).wrapping_add(1013904223);
                (state >> 16) as u16 % 299
            })
            .collect();
        // Response at the noise floor everywhere: nothing here is in focus in
        // any frame, which is what "defocused background" means.
        let response = vec![1.0f32; g.pixels()];
        let s = SelectionScale::from_guide(&winner, &response, g, 8.0, 0, 2.0);
        assert!(
            s.is_full_everywhere(),
            "a random guide over dead ground was treated: {:?}",
            s.histogram()
        );
    }

    /// ...and the same random guide IS treated where real detail exists, or
    /// the veto would simply have turned the feature off.
    #[test]
    fn the_veto_admits_ground_that_carries_sharp_detail() {
        let g = geom(96, 96);
        let winner: Vec<u16> = (0..g.pixels())
            .map(|i| if i % g.width < 48 { 10 } else { 250 })
            .collect();
        let mut response = vec![1.0f32; g.pixels()];
        for y in 20..76 {
            for x in 20..76 {
                response[y * g.width + x] = 40.0;
            }
        }
        let s = SelectionScale::from_guide(&winner, &response, g, 8.0, 0, 2.0);
        assert!(
            s.treated_fraction() > 0.0,
            "the veto rejected a real silhouette with real detail"
        );
        assert!(
            s.levels()[2 * g.width + 47] == FULL_LEVEL,
            "the step was treated far outside the detail that justifies it"
        );
    }

    /// The property the whole fix rests on: at an occluding edge, a background
    /// pixel's masked mean must see ONLY background. The plant is a plane that
    /// is 0 on the foreground side and 1 on the background side; a background
    /// pixel a few px from the step reads 0.5 under the shipped box mean (which
    /// is the halo, in one line) and must read 1.0 here.
    #[test]
    fn the_masked_mean_excludes_the_other_depth() {
        let g = geom(160, 41);
        let step = 80usize;
        let winner: Vec<u16> = (0..g.pixels())
            .map(|i| if i % g.width < step { 20u16 } else { 260u16 })
            .collect();
        let response = vec![50.0f32; g.pixels()];
        let radius = 13usize;
        let s = LayerSupport::from_guide(&winner, &response, g, 8.0, VETO_OFF, &[radius]);
        assert!(s.treated_fraction() > 0.0, "nothing was treated");

        // 0 on the near side, 1 on the far side.
        let src: Vec<f32> = (0..g.pixels())
            .map(|i| if i % g.width < step { 0.0 } else { 1.0 })
            .collect();
        let (mut scratch, mut tmp, mut acc) = (
            vec![0.0f32; g.pixels()],
            vec![0.0f32; g.pixels()],
            vec![0.0f32; g.pixels()],
        );
        let mut dst = vec![0.0f32; g.pixels()];
        box_mean(&src, g, radius, &mut scratch, &mut dst);

        let probe = 20 * g.width + step + 4;
        let plain = dst[probe];
        s.apply_at(&src, radius, &mut scratch, &mut tmp, &mut acc, &mut dst);
        assert!(
            plain < 0.85,
            "the plant is wrong: the plain box mean should be contaminated, got {plain}"
        );
        assert!(
            (dst[probe] - 1.0).abs() < 1e-5,
            "masked mean still sees the other layer: {} (plain was {plain})",
            dst[probe]
        );
    }

    /// An untreated pixel must come out of `apply_at` exactly as it went in, or
    /// the feature cannot ship dark.
    #[test]
    fn untreated_pixels_are_left_bit_identical() {
        let g = geom(160, 41);
        let winner: Vec<u16> = (0..g.pixels())
            .map(|i| if i % g.width < 80 { 20u16 } else { 260u16 })
            .collect();
        let response = vec![50.0f32; g.pixels()];
        let s = LayerSupport::from_guide(&winner, &response, g, 8.0, VETO_OFF, &[13]);
        let src: Vec<f32> = (0..g.pixels()).map(|i| (i % 37) as f32).collect();
        let (mut scratch, mut tmp, mut acc) = (
            vec![0.0f32; g.pixels()],
            vec![0.0f32; g.pixels()],
            vec![0.0f32; g.pixels()],
        );
        let mut dst = vec![0.0f32; g.pixels()];
        box_mean(&src, g, 13, &mut scratch, &mut dst);
        let before = dst.clone();
        s.apply_at(&src, 13, &mut scratch, &mut tmp, &mut acc, &mut dst);
        for i in 0..g.pixels() {
            if s.layers()[i] == UNTREATED {
                assert_eq!(dst[i], before[i], "untreated pixel {i} was modified");
            }
        }
    }

    /// Over dead ground the guide's argmax is noise; the veto must keep the
    /// masking away from it entirely. This is the failure that killed the
    /// scale-ladder version, measured at 47.53% of the plane treated.
    #[test]
    fn layer_masking_does_not_fire_over_dead_ground() {
        let g = geom(96, 96);
        let mut state = 12345u32;
        let winner: Vec<u16> = (0..g.pixels())
            .map(|_| {
                state = state.wrapping_mul(1664525).wrapping_add(1013904223);
                (state >> 16) as u16 % 299
            })
            .collect();
        let response = vec![1.0f32; g.pixels()];
        let s = LayerSupport::from_guide(&winner, &response, g, 8.0, 2.0, &[13]);
        assert!(
            s.is_empty(),
            "a random guide over dead ground was masked: {:?}",
            s.histogram()
        );
    }

    /// The guarantee `MIN_LAYER_FRACTION` exists to make, stated directly: no
    /// treated pixel may ever elect on a slice of its window thinner than the
    /// floor, at any radius the support was built for. Asserting the invariant
    /// rather than a hand-computed instance, because the speckle smooth
    /// dilates thin features by `SPECKLE_RADIUS` before they are binned and
    /// hand-arithmetic on the raw width gets that wrong.
    #[test]
    fn no_treated_pixel_elects_on_less_than_the_floor() {
        let g = geom(160, 41);
        let winner: Vec<u16> = (0..g.pixels())
            .map(|i| {
                let x = i % g.width;
                if (80..82).contains(&x) {
                    260u16
                } else if x > 120 {
                    140u16
                } else {
                    20u16
                }
            })
            .collect();
        let response = vec![50.0f32; g.pixels()];
        let s = LayerSupport::from_guide(&winner, &response, g, 8.0, VETO_OFF, &[13, 8]);
        let mut treated = 0usize;
        for i in 0..g.pixels() {
            if s.layer[i] == UNTREATED {
                continue;
            }
            treated += 1;
            // The quantity that must clear the floor is the denominator the
            // merge actually divides by, which since the grid became
            // interpolated is the tent blend of the two straddling bins --
            // not the hard bin's own share.
            let (l0, l1, a) = straddle(s.pos[i]);
            for (r, f) in &s.fractions {
                let den = (1.0 - a) * f[l0][i] + a * f[l1][i];
                assert!(
                    den >= MIN_LAYER_FRACTION,
                    "pixel {i} elects on {den:.4} of its radius-{r} window, below the {MIN_LAYER_FRACTION} floor",
                );
            }
        }
        assert!(treated > 0, "nothing was treated, so the invariant is vacuous");
    }

    #[test]
    fn the_grid_is_continuous_across_a_bin_boundary() {
        // The blotching this replaced was a CLIFF: two neighbouring pixels
        // whose guide winners differ by one DN could land in different hard
        // bins and then use two unrelated supports. Sweep a depth ramp past
        // every bin boundary and assert the masked result never jumps.
        let g = geom(96, 24);
        let winner: Vec<u16> = (0..g.pixels())
            .map(|i| (20 + (i % g.width) * 2) as u16)
            .collect();
        let response = vec![50.0f32; g.pixels()];
        let s = LayerSupport::from_guide(&winner, &response, g, 1.0, VETO_OFF, &[8]);

        // A signal that varies with depth, so a change of support is visible.
        let src: Vec<f32> = winner.iter().map(|&w| f32::from(w)).collect();
        let mut dst = src.clone();
        let px = g.pixels();
        let (mut sc, mut tmp, mut acc) = (vec![0.0; px], vec![0.0; px], vec![0.0; px]);
        s.apply_at(&src, 8, &mut sc, &mut tmp, &mut acc, &mut dst);

        let y = g.height / 2;
        let mut worst = 0.0f32;
        for x in 1..g.width {
            let (i0, i1) = (y * g.width + x - 1, y * g.width + x);
            if s.layer[i0] != UNTREATED && s.layer[i1] != UNTREATED {
                worst = worst.max((dst[i0] - dst[i1]).abs());
            }
        }
        // Adjacent pixels are 2 DN apart on the ramp; the masked mean may lag
        // but must not step by anything like a bin width (~50 DN here).
        assert!(
            worst < 8.0,
            "masked mean jumps {worst:.2} between adjacent pixels -- grid is quantised, not interpolated"
        );
    }

    #[test]
    fn treatment_fades_in_rather_than_switching_on() {
        // The blobs hugging silhouettes were the TREATMENT BOUNDARY, not the
        // depth bins: a fully-masked pixel sat directly against a fully
        // full-window neighbour. Assert the blend actually takes intermediate
        // values, so that boundary is a ramp and not a cliff.
        let g = geom(96, 32);
        // A depth profile whose STEEPNESS grows across the frame, so the local
        // range statistic sweeps up through tau. A synthetic hard step is the
        // wrong probe here: it crosses tau within a single pixel, so a tight
        // feather correctly produces no partial zone at all.
        let winner: Vec<u16> = (0..g.pixels())
            .map(|i| {
                let x = (i % g.width) as f32;
                (40.0 + x * x / 24.0) as u16
            })
            .collect();
        let response = vec![80.0f32; g.pixels()];
        let s = LayerSupport::from_guide(&winner, &response, g, 8.0, VETO_OFF, &[8]);

        let mut partial = 0usize;
        let mut full = 0usize;
        for i in 0..g.pixels() {
            if s.layer[i] == UNTREATED {
                continue;
            }
            let b = s.blend[i];
            assert!(
                (0.0..=1.0).contains(&b),
                "blend {b} out of range at {i}"
            );
            if b > 0.02 && b < 0.98 {
                partial += 1;
            } else if b >= 0.98 {
                full += 1;
            }
        }
        assert!(
            partial > 0,
            "no pixel is partially treated -- treatment is still a hard switch"
        );
        assert!(full > 0, "no pixel is fully treated -- the ramp never reaches strength");
    }

    #[test]
    fn an_untreated_pixel_keeps_the_shipped_response_exactly() {
        // The fade must be an identity where blend is zero, or turning the
        // feature on would perturb ground it has no business touching.
        let g = geom(64, 32);
        let winner: Vec<u16> = vec![100u16; g.pixels()];
        let response = vec![50.0f32; g.pixels()];
        let s = LayerSupport::from_guide(&winner, &response, g, 8.0, VETO_OFF, &[8]);
        let src: Vec<f32> = (0..g.pixels()).map(|i| (i % 17) as f32).collect();
        let shipped = src.clone();
        let mut dst = shipped.clone();
        let px = g.pixels();
        let (mut sc, mut tmp, mut acc) = (vec![0.0; px], vec![0.0; px], vec![0.0; px]);
        s.apply_at(&src, 8, &mut sc, &mut tmp, &mut acc, &mut dst);
        for i in 0..px {
            if s.layer[i] == UNTREATED {
                assert!(
                    (dst[i] - shipped[i]).abs() < f32::EPSILON,
                    "untreated pixel {i} moved from {} to {}",
                    shipped[i],
                    dst[i]
                );
            }
        }
    }

    #[test]
    fn a_single_peak_is_not_bimodal() {
        // The failure that would waste everyone's time is a detector that
        // fires everywhere. A pixel with one clean through-focus peak must
        // report no separated second mode.
        let g = geom(8, 8);
        let mut b = BimodalStats::new(g);
        for k in 0..60u16 {
            let d = f32::from(k) - 30.0;
            let r = 100.0 * (-d * d / 50.0).exp();
            b.fold(k, &vec![r; g.pixels()]).unwrap();
        }
        let p = b.second_mode_z();
        assert!(
            p.iter().all(|&v| v < 0.5),
            "single Gaussian peak reported a second mode at z={:.3}",
            p.iter().cloned().fold(0.0, f32::max)
        );
    }

    #[test]
    fn two_separated_peaks_are_bimodal() {
        // The occluding-edge case: one peak where the foreground is sharp and
        // one where the background is. Both must be found, and the reported
        // separation must be the real one.
        let g = geom(8, 8);
        let mut b = BimodalStats::new(g);
        for k in 0..100u16 {
            let d1 = f32::from(k) - 20.0;
            let d2 = f32::from(k) - 75.0;
            let r = 100.0 * (-d1 * d1 / 40.0).exp() + 80.0 * (-d2 * d2 / 40.0).exp();
            b.fold(k, &vec![r; g.pixels()]).unwrap();
        }
        let p = b.second_mode_z();
        let s = b.separation();
        assert!(
            p.iter().all(|&v| v > 1.5),
            "two clear modes reported second-mode z as low as {:.3}",
            p.iter().cloned().fold(f32::INFINITY, f32::min)
        );
        assert!(
            s.iter().all(|&v| (50..=60).contains(&v)),
            "separation should be ~55 frames, got {:?}",
            s[0]
        );
    }

    #[test]
    fn absorbing_chunks_finds_the_same_modes_as_one_pass() {
        // The fold runs per rayon chunk and is then absorbed, so a chunked
        // run must agree with a single-threaded one or the detector would
        // depend on thread count.
        let g = geom(4, 4);
        let curve = |k: u16| {
            let (d1, d2) = (f32::from(k) - 15.0, f32::from(k) - 70.0);
            90.0 * (-d1 * d1 / 30.0).exp() + 70.0 * (-d2 * d2 / 30.0).exp()
        };
        let mut whole = BimodalStats::new(g);
        for k in 0..90u16 {
            whole.fold(k, &vec![curve(k); g.pixels()]).unwrap();
        }
        let mut a = BimodalStats::new(g);
        let mut c = BimodalStats::new(g);
        for k in 0..45u16 {
            a.fold(k, &vec![curve(k); g.pixels()]).unwrap();
        }
        for k in 45..90u16 {
            c.fold(k, &vec![curve(k); g.pixels()]).unwrap();
        }
        a.absorb(&c).unwrap();
        let (pw, pa) = (whole.second_mode_z(), a.second_mode_z());
        for i in 0..g.pixels() {
            assert!(
                (pw[i] - pa[i]).abs() < 1e-3,
                "chunked second-mode z {:.4} != whole-pass {:.4}",
                pa[i],
                pw[i]
            );
        }
    }

    #[test]
    fn the_tent_splat_conserves_mass() {
        // Every pixel must splat with total weight exactly 1, or the masked
        // mean's denominator stops being a fraction of the window and
        // MIN_LAYER_FRACTION stops meaning what it says.
        for k in 0..=40 {
            let p = k as f32 * (N_LAYERS - 1) as f32 / 40.0;
            let total: f32 = (0..N_LAYERS).map(|l| tent(p, l)).sum();
            assert!(
                (total - 1.0).abs() < 1e-5,
                "position {p:.3} splats to total weight {total:.6}, not 1"
            );
        }
    }

    #[test]
    fn the_minimum_level_floors_the_support() {
        let g = geom(120, 9);
        let winner: Vec<u16> = (0..g.pixels())
            .map(|i| if i % g.width < 60 { 10u16 } else { 200u16 })
            .collect();
        let s = SelectionScale::from_guide(&winner, &confident(g), g, 8.0, 2, VETO_OFF);
        assert!(
            s.levels().iter().all(|&l| l >= 2),
            "support fell below the floor: {:?}",
            s.histogram()
        );
        assert!(s.treated_fraction() > 0.0, "the floor disabled the fix");
    }

    #[test]
    fn a_flat_guide_leaves_every_pixel_at_the_shipped_radius() {
        // The no-op case has to be exact, not approximate: a stack with no
        // depth discontinuity must elect on the operator M13 measured, or the
        // whole window ruling silently stops applying to most of the corpus.
        let g = geom(80, 80);
        let winner = vec![120u16; g.pixels()];
        let s = SelectionScale::from_guide(&winner, &confident(g), g, 8.0, 0, VETO_OFF);
        assert!(s.is_full_everywhere(), "hist {:?}", s.histogram());
        assert_eq!(s.treated_fraction(), 0.0);
    }

    #[test]
    fn a_gentle_tilt_is_not_a_discontinuity() {
        // A tilted subject sweeps the winner field smoothly. If that read as a
        // depth step the support would collapse across the whole plane and the
        // fix would be a global window shrink wearing a disguise. One frame per
        // pixel over a 13 px radius spans 26 frames, so tau = 40 must keep it.
        let g = geom(120, 40);
        let winner: Vec<u16> = (0..g.pixels()).map(|i| (i % g.width) as u16).collect();
        let s = SelectionScale::from_guide(&winner, &confident(g), g, 40.0, 0, VETO_OFF);
        assert!(
            s.is_full_everywhere(),
            "a 1 frame/px tilt collapsed the support: {:?}",
            s.histogram()
        );
    }

    #[test]
    fn a_step_collapses_the_support_at_the_step_and_only_near_it() {
        // The shape of the treated band is the whole claim: 1 px of support
        // against the silhouette, the full 13 px back by 13 px out. A map that
        // is wide everywhere does nothing; one that is narrow everywhere is a
        // blur.
        let g = geom(120, 9);
        let winner: Vec<u16> = (0..g.pixels())
            .map(|i| if i % g.width < 60 { 10u16 } else { 200u16 })
            .collect();
        let s = SelectionScale::from_guide(&winner, &confident(g), g, 8.0, 0, VETO_OFF);
        let mid = 4 * g.width;
        let row = &s.levels()[mid..mid + g.width];
        assert_eq!(row[59], 0, "hard against the step the support must be 1 px");
        assert_eq!(row[60], 0);
        assert_eq!(
            row[59 - WINDOW_RADIUS - SPECKLE_RADIUS],
            FULL_LEVEL,
            "the shipped radius must be back by one window out: {row:?}"
        );
        assert_eq!(row[0], FULL_LEVEL, "far from the step nothing is treated");
        // Monotone: support may only shrink as the step is approached.
        for x in 1..58 {
            assert!(
                row[x] <= row[x - 1],
                "support is not monotone approaching the step at x={x}: {row:?}"
            );
        }
    }

    #[test]
    fn speckle_alone_does_not_collapse_the_support() {
        // Regression on the reason SPECKLE_RADIUS exists. A +/-3 frame
        // checkerboard has a raw local range of 6 everywhere; at tau = 8 an
        // unsmoothed range would still pass, so the plant is +/-6 (range 12,
        // over tau) which an unsmoothed implementation fails and this one must
        // not.
        let g = geom(80, 80);
        let winner: Vec<u16> = (0..g.pixels())
            .map(|i| {
                let (x, y) = (i % g.width, i / g.width);
                if (x + y) % 2 == 0 { 94 } else { 106 }
            })
            .collect();
        let s = SelectionScale::from_guide(&winner, &confident(g), g, 8.0, 0, VETO_OFF);
        assert!(
            s.is_full_everywhere(),
            "speckle read as depth: {:?}",
            s.histogram()
        );
    }

    #[test]
    fn box_extremum_composes_exactly() {
        // The nested-dilation shortcut is load-bearing for the cost, and it is
        // only valid because box dilations compose. If that ever stops being
        // true the scale map silently uses the wrong radii.
        let g = geom(40, 1);
        let src: Vec<f32> = (0..40).map(|i| ((i * 7) % 13) as f32).collect();
        let mut scratch = vec![0.0; 40];

        let mut composed = src.clone();
        box_extremum(&mut composed, g, 2, &mut scratch, true);
        box_extremum(&mut composed, g, 3, &mut scratch, true);

        let mut direct = src.clone();
        box_extremum(&mut direct, g, 5, &mut scratch, true);

        assert_eq!(composed, direct);
    }

    #[test]
    fn uniform_is_the_shipped_operator_at_the_full_level() {
        let g = geom(16, 16);
        let s = SelectionScale::uniform(g, FULL_LEVEL);
        assert!(s.is_full_everywhere());
        assert_eq!(LEVEL_RADII[FULL_LEVEL as usize], WINDOW_RADIUS);
    }

    // -- the guided regulariser ------------------------------------------

    /// A step in the guide must stop the filter. This is the property the whole
    /// fix rests on: if focus energy crosses a silhouette here, the rim is
    /// re-manufactured at the regulariser's radius no matter how narrow the
    /// selection window was made.
    #[test]
    fn domain_transform_does_not_carry_focus_across_a_luma_step() {
        let (w, h) = (96usize, 24usize);
        let g = geom(w, h);
        // Luma: hard step at x = 48. Focus: all the energy on the left.
        let mut luma = vec![0.0f32; w * h];
        let mut focus = vec![0.0f32; w * h];
        for y in 0..h {
            for x in 0..w {
                luma[y * w + x] = if x < 48 { 1000.0 } else { 0.0 };
                focus[y * w + x] = if x < 48 { 1.0 } else { 0.0 };
            }
        }
        let (mut dst, mut s1, mut s2, mut s3) = (
            vec![0.0f32; w * h],
            vec![0.0f32; w * h],
            vec![0.0f32; w * h],
            vec![0.0f32; w * h],
        );
        domain_transform(&focus, &luma, g, 8.0, &mut dst, &mut s1, &mut s2, &mut s3);

        // Read the "background" side, just across the step.
        let leak: f32 = (0..h).map(|y| dst[y * w + 50]).sum::<f32>() / h as f32;

        // The shipped box mean at radius 8 puts 7/17 of the left side's energy
        // at x = 50. Anything near that is a re-manufactured rim.
        let mut bs = vec![0.0f32; w * h];
        let mut sc = vec![0.0f32; w * h];
        crate::boxfilter::box_mean(&focus, g, 8, &mut sc, &mut bs);
        let box_leak: f32 = (0..h).map(|y| bs[y * w + 50]).sum::<f32>() / h as f32;

        assert!(
            box_leak > 0.3,
            "the box must leak for this test to mean anything, got {box_leak:.4}"
        );
        assert!(
            leak < 0.02,
            "focus energy crossed the silhouette: guided {leak:.4} vs box {box_leak:.4}"
        );
    }

    /// ...but it must still be a smoother. An edge-aware filter that refuses to
    /// average anywhere is not buying back the noise robustness the narrow
    /// window gave up, and the adaptive rule is unsafe without that.
    #[test]
    fn domain_transform_still_averages_within_a_flat_region() {
        let (w, h) = (96usize, 32usize);
        let g = geom(w, h);
        let luma = vec![500.0f32; w * h];
        // Deterministic zero-mean chequer: pure "noise" with no edges.
        let focus: Vec<f32> = (0..w * h)
            .map(|i| if (i % 7 == 0) ^ (i % 3 == 0) { 1.0 } else { -1.0 })
            .collect();
        let (mut dst, mut s1, mut s2, mut s3) = (
            vec![0.0f32; w * h],
            vec![0.0f32; w * h],
            vec![0.0f32; w * h],
            vec![0.0f32; w * h],
        );
        domain_transform(&focus, &luma, g, 8.0, &mut dst, &mut s1, &mut s2, &mut s3);

        let var_in = focus.iter().map(|v| v * v).sum::<f32>() / focus.len() as f32;
        // Interior only: the IIR has no data beyond the border to average with.
        let mut n = 0.0f32;
        let mut var_out = 0.0f32;
        for y in 12..h - 12 {
            for x in 12..w - 12 {
                var_out += dst[y * w + x] * dst[y * w + x];
                n += 1.0;
            }
        }
        var_out /= n;
        assert!(
            var_out < var_in * 0.15,
            "flat-region smoothing too weak: var {var_in:.4} -> {var_out:.4}"
        );
    }

    // -- the adaptive radius ---------------------------------------------

    /// The two terms of `min(r_noise, r_geom)` must each bind where they should.
    #[test]
    fn acuity_shrinks_at_a_depth_step_and_at_high_contrast_but_not_on_clean_flat_ground() {
        let (w, h) = (128usize, 64usize);
        let g = geom(w, h);
        // Guide: foreground (frame 250) left of x = 64, background (frame 10)
        // right of it. A genuine occluding silhouette.
        let guide: Vec<u16> = (0..w * h)
            .map(|i| if i % w < 64 { 250 } else { 10 })
            .collect();
        // Excess: strong on the left (sharp foreground), nil on the right
        // (featureless defocused background).
        let strong = crate::merge::FOCUS_NOISE_SD * 100.0;
        let excess: Vec<f32> = (0..w * h)
            .map(|i| if i % w < 64 { strong } else { 0.0 })
            .collect();

        let s = SelectionScale::from_acuity(&excess, &guide, g, 4.0, 4.0);
        let lv = s.levels();
        let at = |x: usize, y: usize| lv[y * w + x] as usize;

        // Hard against the step, both sides: the geometry term binds.
        assert!(
            LEVEL_RADII[at(63, 32)] <= 2 && LEVEL_RADII[at(65, 32)] <= 2,
            "support did not collapse at the silhouette: {} | {}",
            LEVEL_RADII[at(63, 32)],
            LEVEL_RADII[at(65, 32)]
        );
        // Deep in the featureless background: nothing to discriminate with, so
        // the noise term asks for — and gets — the full shipped window.
        assert_eq!(
            LEVEL_RADII[at(120, 32)],
            WINDOW_RADIUS,
            "flat clean ground must keep the shipped window"
        );
        // Deep in high-contrast foreground, far from the step: the noise term
        // binds and hands back radius. THIS is the contamination-radius win —
        // it happens without any edge being detected at all.
        assert!(
            LEVEL_RADII[at(8, 32)] < WINDOW_RADIUS,
            "strong signal should not need the full window, got {}",
            LEVEL_RADII[at(8, 32)]
        );
    }

    /// With no depth step anywhere, the rule must reduce to the noise term
    /// alone — and on a plane with no resolvable peak that is the shipped
    /// operator, byte for byte. A fix that perturbs clean flat ground is not a
    /// fix.
    #[test]
    fn acuity_is_the_shipped_operator_on_a_featureless_plane() {
        let g = geom(64, 64);
        let guide = vec![100u16; g.pixels()];
        let excess = vec![0.0f32; g.pixels()];
        let s = SelectionScale::from_acuity(&excess, &guide, g, 4.0, 4.0);
        assert!(
            s.is_full_everywhere(),
            "histogram {:?}",
            s.histogram()
        );
    }

    /// The margin has to be load-bearing in the right direction: asking for
    /// more confidence must never *shrink* the window. `FEATHER` was chosen
    /// from one synthetic probe and turned out not to be load-bearing at all;
    /// this asserts the monotonicity rather than a number, so it cannot go
    /// stale the same way.
    #[test]
    fn a_stricter_margin_never_asks_for_less_support() {
        let g = geom(64, 64);
        let guide = vec![100u16; g.pixels()];
        let excess: Vec<f32> = (0..g.pixels())
            .map(|i| crate::merge::FOCUS_NOISE_SD * (i % 40) as f32)
            .collect();
        let loose = SelectionScale::from_acuity(&excess, &guide, g, 4.0, 2.0);
        let tight = SelectionScale::from_acuity(&excess, &guide, g, 4.0, 8.0);
        for i in 0..g.pixels() {
            assert!(
                tight.levels()[i] >= loose.levels()[i],
                "at {i}: margin 8 gave level {} but margin 2 gave {}",
                tight.levels()[i],
                loose.levels()[i]
            );
        }
    }
}
