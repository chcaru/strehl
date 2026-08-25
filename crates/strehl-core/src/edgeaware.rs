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
    /// Depth bin of **every** pixel. A treated pixel's window has to be able to
    /// see which of its untreated neighbours share its depth, so the binning is
    /// global even though the masking is not.
    bin: Vec<u8>,
    /// Depth bin per treated pixel, or [`UNTREATED`].
    layer: Vec<u8>,
    /// `(radius, fractions)` where `fractions[l] = box_mean(bin == l, radius)`:
    /// the share of each window belonging to layer `l`. Frame-independent, so
    /// it is computed once per radius and shared across every worker.
    fractions: Vec<(usize, Vec<Vec<f32>>)>,
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
        for i in 0..px {
            if hi_b[i] - lo_b[i] > tau && sharp[i] > floor {
                layer[i] = bin[i];
            }
        }

        let mut fractions: Vec<(usize, Vec<Vec<f32>>)> = Vec::with_capacity(radii.len());
        let mut ind = vec![0.0f32; px];
        for &r in radii {
            let mut per_layer = vec![vec![0.0f32; px]; N_LAYERS];
            for l in 0..N_LAYERS {
                for i in 0..px {
                    ind[i] = f32::from(u8::from(bin[i] as usize == l));
                }
                box_mean(&ind, geom, r, &mut scratch, &mut per_layer[l]);
            }
            fractions.push((r, per_layer));
        }

        // Withdraw any pixel whose own layer is too thin a slice of its window
        // to elect on, at ANY radius it will be used at. This is the antenna
        // case, and it is the scale ladder's failure mode arriving by a
        // different road.
        for i in 0..px {
            if layer[i] == UNTREATED {
                continue;
            }
            let l = layer[i] as usize;
            if fractions
                .iter()
                .any(|(_, f)| f[l][i] < MIN_LAYER_FRACTION)
            {
                layer[i] = UNTREATED;
            }
        }

        Self {
            geom,
            bin,
            layer,
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
        for l in 0..N_LAYERS {
            if hist[l] == 0 {
                continue;
            }
            for i in 0..px {
                tmp[i] = if self.bin[i] as usize == l { src[i] } else { 0.0 };
            }
            box_mean(tmp, self.geom, radius, scratch, acc);
            for i in 0..px {
                if self.layer[i] as usize == l {
                    let f = fractions[l][i];
                    if f > 0.0 {
                        dst[i] = acc[i] / f;
                    }
                }
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
            let l = s.layer[i];
            if l == UNTREATED {
                continue;
            }
            treated += 1;
            for (r, f) in &s.fractions {
                assert!(
                    f[l as usize][i] >= MIN_LAYER_FRACTION,
                    "pixel {i} elects on {:.4} of its radius-{r} window, below the {MIN_LAYER_FRACTION} floor",
                    f[l as usize][i]
                );
            }
        }
        assert!(treated > 0, "nothing was treated, so the invariant is vacuous");
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
}
