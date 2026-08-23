//! Noise-normalised Tenengrad focus measure: Sobel gradient magnitude under a
//! 27x27 box window.
//!
//! ```text
//! g(p)     = sqrt(Gx(p)^2 + Gy(p)^2)            3x3 Sobel, scaled by 1/8
//! focus(p) = box_mean_13(g)(p) / max(sigma_L(p), EPS)
//! ```
//!
//! # This operator is a measurement result, not a preference
//!
//! It replaces `|mean_3x3 - mean_7x7| / sigma`, the ring difference the walking
//! skeleton shipped with. Two milestones decided it:
//!
//! - **M11** (`docs/research/M11-focus-bakeoff-measured.md`) ran a 47-operator
//!   pre-registered bake-off on two real stacks and scored it on a Pareto front
//!   of selectivity against merged-noise excess. `ring(1,3)` came **26-27th of
//!   36**: N = 1.3475x at 41-49% of the best selectivity. Tenengrad under a box
//!   window dominates it on **both** axes, and no setting of the ring's two
//!   radii closes the gap (SYNTHESIS fact 41).
//! - **M13** (`docs/research/M13-window-depth-measured.md`) set the window.
//!   M11 recommended 11x11; that is dominated. Over 36 occluding-edge cells the
//!   argmin of both mean and worst-case regret is **radius 13**, stable in all
//!   three noise seeds (SYNTHESIS fact 60).
//!
//! Neither says the operator is noise-free. **No operator measured is**: 0 of
//! 36 reached N <= 1.02x (fact 37). The escape from selection's noise penalty
//! is estimation, not a better selector — this measure only makes the selector
//! that the skeleton still is as good as a selector gets.
//!
//! # Why the magnitude and not the energy
//!
//! "Tenengrad" in the literature is usually `Gx^2 + Gy^2`. **The number M11
//! published is not that one.** `tenengrad-w5` in
//! `experiments/m11-focus-bakeoff/src/measures.rs` is `Kind::Tenengrad {
//! squared: false }` — the gradient *magnitude*, `degree = 1`, divided by
//! `sigma^1` — and the squared arm is a separate entry, `tenengrad-sq-w2`.
//! M13's `tenengrad-w13` is the same magnitude form. So is this. See
//! `docs/research/M14-tenengrad-implemented.md` for how that was established
//! from the committed CSVs rather than assumed.
//!
//! # The normalisation is a proxy, and this is where that is admitted
//!
//! `sigma_L` is the noise standard deviation of a **single** luma sample at
//! that signal level, from the injected noise model. It is **not** the standard
//! deviation of the windowed gradient magnitude, which is smaller by roughly
//! the window's tap count and is not even centred at zero, since `|grad|` is a
//! rectified quantity with a positive noise floor.
//!
//! It is kept anyway, and deliberately, because it is what was measured. M11
//! scored an un-normalised arm (`tenengrad-w2-nonorm`) and a box-normalised arm
//! (`tenengrad-w2-boxnorm`) precisely so the divisor would not be a confound,
//! and the published `N = 1.1324x` belongs to the pointwise-`sigma(L(p))` arm.
//! Substituting a "better" divisor here would silently invalidate that number.
//!
//! The reason it is adequate is unchanged from the ring: the merge consumes
//! only the *ranking* of `focus` across frames at a fixed pixel, and every
//! frame at that pixel divides by a sigma computed from nearly the same signal
//! level, so the omitted factor very nearly cancels out of the comparison.
//! **The divisor is not free, though** — it is a term in the centre-tap
//! fraction `phi`, and it is the whole reason `phi` is 0.139 here instead of
//! 0.0013 (fact 39, M13 §1.4).

use crate::boxfilter::box_mean;
use crate::noise::NoiseModel;
use crate::plane::PlaneGeometry;

/// Box-window radius, in plane pixels: a `27x27` mean of the gradient
/// magnitude.
///
/// **MEASURED, M13** (`docs/research/M13-window-depth-measured.md` §6.1,
/// SYNTHESIS fact 60): argmin of both mean regret (3.171 DN) and worst-case
/// regret (12.111 DN) over 36 occluding-edge cells, and argmin independently in
/// each of three noise seeds. Read it as the centre of the basin `w11-w15`,
/// which is flat to 0.87 DN against a 0.193 DN seed noise floor — not as a
/// value precise to the pixel.
///
/// **It may still move narrower.** Every one of M13's 7,200 measurements ran
/// with the merge regulariser off (`width = 1`), and SYNTHESIS open question 17
/// asks whether the optimum survives switching it on; if the regulariser is
/// already buying the variance reduction, the wide window's benefit shrinks
/// while its occlusion-halo cost does not. That is why this is one named
/// constant and not a number woven through the code.
pub const WINDOW_RADIUS: usize = 13;

/// Radius of the gradient stencil. A 3x3 Sobel, so 1.
pub const SOBEL_RADIUS: usize = 1;

/// The furthest luma sample the focus value at a pixel reads, in plane pixels.
///
/// `SOBEL_RADIUS + WINDOW_RADIUS = 14`, so the read extent is a `29x29` square
/// and the sensitivity kernel has `29^2 = 841` taps. **Anything that sizes a
/// tile margin, or the `halo()` rectangle expansion of SYNTHESIS fact 32, from
/// the focus operator must use this** — M13 §6.3. It is 4.7x the ring's, so a
/// margin that was correct before is not correct now.
pub const SUPPORT_RADIUS: usize = SOBEL_RADIUS + WINDOW_RADIUS;

/// Divisor floor, in DN. Guards the case where the noise model returns zero or
/// something denormal; it is far below any real sensor's read-noise floor.
const SIGMA_EPS: f32 = 1e-3;

/// 3x3 Sobel gradient magnitude, `sqrt(Gx^2 + Gy^2)`, replicate-clamped at the
/// border.
///
/// The `1/8` on each component is cosmetic — the merge only compares a measure
/// against itself on other frames at the same pixel, and both the argmax and
/// any positive-scaled regulariser are invariant to it — but it is applied
/// because it puts the response in DN/px, and because it is what
/// `experiments/m11-focus-bakeoff/src/measures.rs::sobel` did when the ruling
/// numbers were measured.
///
/// # Precision
///
/// `f32` throughout, and that is safe here. At the A7C II's 15360 DN white
/// level and 512 DN black the largest possible component is
/// `0.125 * 4 * 14848 = 7424` DN/px, so `Gx^2 + Gy^2 <= 1.10e8` — well inside
/// f32's range, but past `2^24`, so the squares are inexact. The error is
/// **relative** (<= 2^-23 each, halved again by the square root), which puts
/// the worst-case absolute error on `g` near `1e-3` DN — three orders below the
/// DN quantisation of the input. Accumulating 841 of these is the part that
/// needs care, and that happens in [`box_mean`], which keeps an f64 sum.
pub fn gradient_magnitude(luma: &[f32], geom: PlaneGeometry, out: &mut [f32]) {
    assert_eq!(luma.len(), geom.pixels());
    assert_eq!(out.len(), geom.pixels());
    let (w, h) = (geom.width, geom.height);
    for y in 0..h {
        for x in 0..w {
            let (xi, yi) = (x as isize, y as isize);
            let at = |dx: isize, dy: isize| {
                let sx = (xi + dx).clamp(0, w as isize - 1) as usize;
                let sy = (yi + dy).clamp(0, h as isize - 1) as usize;
                luma[sy * w + sx]
            };
            let gx =
                at(1, -1) + 2.0 * at(1, 0) + at(1, 1) - at(-1, -1) - 2.0 * at(-1, 0) - at(-1, 1);
            let gy =
                at(-1, 1) + 2.0 * at(0, 1) + at(1, 1) - at(-1, -1) - 2.0 * at(0, -1) - at(1, -1);
            let (gx, gy) = (0.125 * gx, 0.125 * gy);
            out[y * w + x] = (gx * gx + gy * gy).sqrt();
        }
    }
}

/// Reusable buffers plus the computed focus field for one plane.
///
/// Allocated once per worker and reused for every frame that worker folds. At
/// 8.2 MP this is 99 MB, so allocating per frame would dominate the run.
pub struct FocusField {
    geom: PlaneGeometry,
    /// Holds the windowed gradient mean, then is overwritten in place with the
    /// focus value. The normalisation is elementwise and reads each element
    /// once, so no fourth full-plane buffer is needed.
    focus: Vec<f32>,
    grad: Vec<f32>,
    scratch: Vec<f32>,
}

impl FocusField {
    pub fn new(geom: PlaneGeometry) -> Self {
        Self {
            geom,
            focus: vec![0.0; geom.pixels()],
            grad: vec![0.0; geom.pixels()],
            scratch: vec![0.0; geom.pixels()],
        }
    }

    pub fn geometry(&self) -> PlaneGeometry {
        self.geom
    }

    /// Bytes of scratch this holds, for the memory budget report.
    ///
    /// **Three f32 planes, unchanged by M14.** The ring held `inner`, `outer`
    /// and a box-filter `scratch`; Tenengrad holds `grad`, the same `scratch`
    /// and the output. The per-worker term in `strehl-cli`'s `WorkerPlan` and
    /// M8's measured ratchet (SYNTHESIS §5, fact 33) are therefore untouched.
    pub fn allocated_bytes(&self) -> usize {
        3 * self.geom.pixels() * std::mem::size_of::<f32>()
    }

    /// Compute the focus field for one frame's black-subtracted green luma.
    ///
    /// Cost is **O(1) in [`WINDOW_RADIUS`]**, because [`box_mean`] is a
    /// separable running sum. M13 measured the whole operator flat in the
    /// radius to within 2.53% over w1-w40; a naive `(2w+1)^2` gather at radius
    /// 13 would be 841x the taps and would invalidate that result.
    pub fn compute(&mut self, luma: &[f32], noise: &NoiseModel) {
        assert_eq!(luma.len(), self.geom.pixels());
        gradient_magnitude(luma, self.geom, &mut self.grad);
        box_mean(
            &self.grad,
            self.geom,
            WINDOW_RADIUS,
            &mut self.scratch,
            &mut self.focus,
        );
        for (focus, l) in self.focus.iter_mut().zip(luma) {
            let sigma = noise.green_luma_sigma(*l).max(SIGMA_EPS);
            *focus /= sigma;
        }
    }

    pub fn values(&self) -> &[f32] {
        &self.focus
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::noise::{Levels, NoiseModel, PlaneNoise, Provenance};

    fn model() -> NoiseModel {
        let p = PlaneNoise {
            gain_dn_per_e: 0.229,
            read_noise_e: 1.47,
            levels: Levels {
                black: 512.0,
                white: 15360.0,
            },
        };
        NoiseModel::new([p; 4], 100.0, Provenance::Profile)
    }

    fn geometry(w: usize, h: usize) -> PlaneGeometry {
        PlaneGeometry {
            width: w,
            height: h,
        }
    }

    fn field(w: usize, h: usize, luma: &[f32]) -> Vec<f32> {
        let mut f = FocusField::new(geometry(w, h));
        f.compute(luma, &model());
        f.values().to_vec()
    }

    /// The un-normalised response, `box_mean_r(|grad|)`, on the shipped code
    /// path. Only the divisor differs from [`FocusField::compute`]; this is
    /// M11's `Norm::None` arm, and it is what makes the analytic centre-tap
    /// anchors below testable.
    fn unnormalised(w: usize, h: usize, luma: &[f32], radius: usize) -> Vec<f32> {
        let geom = geometry(w, h);
        let (mut grad, mut scratch, mut out) = (
            vec![0.0f32; geom.pixels()],
            vec![0.0f32; geom.pixels()],
            vec![0.0f32; geom.pixels()],
        );
        gradient_magnitude(luma, geom, &mut grad);
        if radius == 0 {
            return grad;
        }
        box_mean(&grad, geom, radius, &mut scratch, &mut out);
        out
    }

    /// The retired ring difference, `|mean_3x3 - mean_7x7| / sigma`, kept only
    /// so the two regression tests below can measure the replacement against
    /// the thing it replaced on the axes M11 scored. This is a verbatim copy of
    /// the operator `focus.rs` shipped before M14 and must not be revived.
    fn ring_field(w: usize, h: usize, luma: &[f32]) -> Vec<f32> {
        let geom = geometry(w, h);
        let (mut scratch, mut inner, mut outer) = (
            vec![0.0f32; geom.pixels()],
            vec![0.0f32; geom.pixels()],
            vec![0.0f32; geom.pixels()],
        );
        box_mean(luma, geom, 1, &mut scratch, &mut inner);
        box_mean(luma, geom, 3, &mut scratch, &mut outer);
        let noise = model();
        for i in 0..geom.pixels() {
            let ring = (inner[i] - outer[i]).abs();
            inner[i] = ring / noise.green_luma_sigma(luma[i]).max(SIGMA_EPS);
        }
        inner
    }

    #[test]
    fn a_flat_plane_has_zero_focus_everywhere_including_the_border() {
        // The border policy is load-bearing twice over: a zero-padded box would
        // leave a bright rim here, and so would a zero-padded Sobel.
        let luma = vec![4000.0f32; 61 * 45];
        let got = field(61, 45, &luma);
        assert!(
            got.iter().all(|v| *v < 1e-3),
            "max was {:?}",
            got.iter().cloned().fold(f32::MIN, f32::max)
        );
    }

    #[test]
    fn resolved_texture_scores_higher_than_the_same_texture_blurred() {
        // NOTE for anyone restoring the pre-M14 version of this test: a single
        // monotone step will NOT discriminate here. The mean of |grad| over a
        // window wider than the blur is the total variation across the window
        // divided by its area, and blurring a monotone edge conserves total
        // variation exactly. Texture is what defocus actually destroys, because
        // texture's gradients change sign and cancel; use texture.
        let (w, h) = (64usize, 64usize);
        let sharp: Vec<f32> = (0..w * h)
            .map(|i| {
                let (x, y) = ((i % w) as f32, (i / w) as f32);
                2000.0
                    + 400.0 * (x * 1.9).sin() * (y * 1.7).cos()
                    + 250.0 * (x * 0.83 + y * 0.61).sin()
            })
            .collect();
        let mut scratch = vec![0.0f32; w * h];
        let mut soft = vec![0.0f32; w * h];
        box_mean(&sharp, geometry(w, h), 2, &mut scratch, &mut soft);

        let a = field(w, h, &sharp);
        let b = field(w, h, &soft);
        let interior = |v: &[f32]| -> f64 {
            let m = SUPPORT_RADIUS;
            let mut s = 0.0f64;
            let mut n = 0usize;
            for y in m..h - m {
                for x in m..w - m {
                    s += v[y * w + x] as f64;
                    n += 1;
                }
            }
            s / n as f64
        };
        let (sh, so) = (interior(&a), interior(&b));
        assert!(sh > 1.5 * so, "sharp {sh:.4} vs soft {so:.4}");
    }

    #[test]
    fn normalisation_penalises_the_same_contrast_at_a_higher_signal_level() {
        // Shot noise grows with signal, so an equal-DN feature is less evidence
        // of detail on a bright background than on a dark one. That is the
        // whole point of dividing by sigma.
        let (w, h) = (41usize, 41usize);
        let build = |base: f32| {
            let mut v = vec![base; w * h];
            for y in 0..h {
                v[y * w + 20] = base + 100.0;
            }
            v
        };
        let dark = field(w, h, &build(200.0));
        let bright = field(w, h, &build(12000.0));
        let peak = |v: &[f32]| v.iter().cloned().fold(f32::MIN, f32::max);
        assert!(peak(&dark) > peak(&bright));
    }

    #[test]
    fn focus_is_finite_and_non_negative_at_zero_signal() {
        // Below the read-noise floor sigma is small but never zero.
        let luma = vec![0.0f32; 33 * 33];
        let got = field(33, 33, &luma);
        assert!(got.iter().all(|v| v.is_finite() && *v >= 0.0));
    }

    #[test]
    fn the_running_sum_agrees_with_a_naive_gather_of_the_same_operator() {
        // The cost result (M13 §5, flat in radius) depends entirely on the box
        // being a running sum. This pins the two forms together so the fast
        // path cannot drift from the definition it is standing in for.
        let (w, h) = (37usize, 29usize);
        let luma: Vec<f32> = (0..w * h)
            .map(|i| {
                let (x, y) = ((i % w) as f32, (i / w) as f32);
                3000.0 + 900.0 * (x * 0.7).sin() * (y * 1.3).cos() + 40.0 * ((i * 7919) % 13) as f32
            })
            .collect();
        let got = field(w, h, &luma);

        let geom = geometry(w, h);
        let mut grad = vec![0.0f32; geom.pixels()];
        gradient_magnitude(&luma, geom, &mut grad);
        let noise = model();
        for y in 0..h {
            for x in 0..w {
                let (x0, x1) = (
                    x.saturating_sub(WINDOW_RADIUS),
                    (x + WINDOW_RADIUS).min(w - 1),
                );
                let (y0, y1) = (
                    y.saturating_sub(WINDOW_RADIUS),
                    (y + WINDOW_RADIUS).min(h - 1),
                );
                let (mut sum, mut n) = (0.0f64, 0u32);
                for yy in y0..=y1 {
                    for xx in x0..=x1 {
                        sum += grad[yy * w + xx] as f64;
                        n += 1;
                    }
                }
                let i = y * w + x;
                let want = (sum / n as f64) as f32 / noise.green_luma_sigma(luma[i]).max(SIGMA_EPS);
                let tol = 1e-3 * want.abs().max(1e-3);
                assert!(
                    (got[i] - want).abs() <= tol,
                    "at ({x},{y}): got {} want {want}",
                    got[i]
                );
            }
        }
    }

    // ---------------------------------------------------------------- plants

    /// SplitMix64, so both plants below are byte-reproducible on any machine.
    struct Rng(u64);

    impl Rng {
        fn next_u64(&mut self) -> u64 {
            self.0 = self.0.wrapping_add(0x9E37_79B9_7F4A_7C15);
            let mut z = self.0;
            z = (z ^ (z >> 30)).wrapping_mul(0xBF58_476D_1CE4_E5B9);
            z = (z ^ (z >> 27)).wrapping_mul(0x94D0_49BB_1331_11EB);
            z ^ (z >> 31)
        }

        fn unit(&mut self) -> f32 {
            (self.next_u64() >> 40) as f32 / 16_777_216.0
        }

        /// Irwin-Hall(12) - 6: mean 0, variance 1, bounded at +/-6 sigma.
        fn normal(&mut self) -> f32 {
            (0..12).map(|_| self.unit()).sum::<f32>() - 6.0
        }
    }

    /// Winner index per pixel by argmax over frames, with the same lowest-index
    /// tie-break `Selection::beats` uses.
    fn winners(fields: &[Vec<f32>]) -> Vec<usize> {
        let n = fields[0].len();
        (0..n)
            .map(|i| {
                let mut best = 0usize;
                for k in 1..fields.len() {
                    if fields[k][i] > fields[best][i] {
                        best = k;
                    }
                }
                best
            })
            .collect()
    }

    /// A selector with no coupling to the pixel's own noise at all: M2's
    /// placebo, and the control every claim below is quoted against.
    fn random_fields(frames: usize, pixels: usize) -> Vec<Vec<f32>> {
        (0..frames)
            .map(|k| {
                (0..pixels)
                    .map(|i| Rng(0xF10C ^ (i as u64) << 20 ^ (k as u64)).unit())
                    .collect()
            })
            .collect()
    }

    fn sd_interior(v: &[f32], w: usize, h: usize, margin: usize) -> f64 {
        let mut s = Vec::with_capacity((w - 2 * margin) * (h - 2 * margin));
        for y in margin..h - margin {
            for x in margin..w - margin {
                s.push(v[y * w + x] as f64);
            }
        }
        let mean = s.iter().sum::<f64>() / s.len() as f64;
        (s.iter().map(|v| (v - mean).powi(2)).sum::<f64>() / s.len() as f64).sqrt()
    }

    #[test]
    fn tenengrad_elects_less_of_the_pixels_own_noise_than_the_ring_did() {
        // M11's noise axis, in miniature: N = sd(argmax-merged flat region) /
        // sd(the same region in one frame). MEASURED on real frames, N is
        // 1.3475x for ring(1,3) and 1.1324x for tenengrad-w5 (SYNTHESIS fact
        // 41); M13 measures 1.0864x at the w13 shipped here. This plant is
        // synthetic and its absolute numbers are its own, but the ORDERING is
        // the published claim and it is what this pins.
        //
        // Rule 11's placebo is the third arm: a selector with an identical
        // winner histogram but no coupling to the pixel's own noise must land
        // at 1.0. Without it, any ratio above 1 could be the plant's fault.
        let (w, h, frames) = (128usize, 128usize, 22usize);
        let noise = model();
        let level = 2000.0f32;
        let sigma = noise.green_luma_sigma(level);
        let mut rng = Rng(0x5EED_0001);
        let planes: Vec<Vec<f32>> = (0..frames)
            .map(|_| (0..w * h).map(|_| level + sigma * rng.normal()).collect())
            .collect();

        let merged = |fields: &[Vec<f32>]| -> f64 {
            let win = winners(fields);
            let out: Vec<f32> = (0..w * h).map(|i| planes[win[i]][i]).collect();
            sd_interior(&out, w, h, 24)
        };
        let single = sd_interior(&planes[frames / 2], w, h, 24);

        let ten: Vec<Vec<f32>> = planes.iter().map(|p| field(w, h, p)).collect();
        let ring: Vec<Vec<f32>> = planes.iter().map(|p| ring_field(w, h, p)).collect();
        let placebo = random_fields(frames, w * h);

        let (n_ten, n_ring, n_placebo) = (
            merged(&ten) / single,
            merged(&ring) / single,
            merged(&placebo) / single,
        );
        println!(
            "flat plant: N(tenengrad-w{WINDOW_RADIUS}) = {n_ten:.4}, N(ring-1-3) = {n_ring:.4}, \
             N(placebo) = {n_placebo:.4}, single sd = {single:.3} DN"
        );

        assert!(
            (n_placebo - 1.0).abs() < 0.03,
            "the placebo must not manufacture an excess, got {n_placebo:.4}"
        );
        assert!(
            n_ring > 1.10,
            "the ring's defect must reproduce on this plant, got {n_ring:.4}"
        );
        assert!(
            n_ten < n_ring,
            "tenengrad {n_ten:.4} must elect less noise than the ring {n_ring:.4}"
        );
        // The measured gap on real frames is 1.3475 -> 1.0864, i.e. the excess
        // falls by 74%. Require most of that here, not merely a sign.
        assert!(
            (n_ten - 1.0) < 0.5 * (n_ring - 1.0),
            "tenengrad excess {:.4} must be less than half the ring's {:.4}",
            n_ten - 1.0,
            n_ring - 1.0
        );
    }

    #[test]
    fn tenengrad_picks_the_correct_frame_far_more_often_than_the_ring_did() {
        // M11's selectivity axis. The plant is FRONTO-PARALLEL: one true frame
        // everywhere. That is deliberate and it is also a limit -- SYNTHESIS
        // fact 62 says such a plant cannot produce a window optimum, so this
        // test may never be quoted as evidence about WINDOW_RADIUS. It compares
        // two fixed operators, which is a question a flat plant can answer.
        let (w, h, frames) = (96usize, 96usize, 15usize);
        let truth = 7usize;
        let geom = geometry(w, h);
        let sharp: Vec<f32> = (0..w * h)
            .map(|i| {
                let (x, y) = ((i % w) as f32, (i / w) as f32);
                2400.0
                    + 500.0 * (x * 1.61).sin() * (y * 1.37).cos()
                    + 300.0 * (x * 0.53 - y * 0.71).sin()
                    + 200.0 * (x * 2.31 + y * 0.19).cos()
            })
            .collect();

        let mut rng = Rng(0x5EED_0002);
        let noise = model();
        let mut scratch = vec![0.0f32; w * h];
        let planes: Vec<Vec<f32>> = (0..frames)
            .map(|k| {
                let blur = k.abs_diff(truth);
                let mut plane = vec![0.0f32; w * h];
                if blur == 0 {
                    plane.copy_from_slice(&sharp);
                } else {
                    box_mean(&sharp, geom, blur, &mut scratch, &mut plane);
                }
                for v in plane.iter_mut() {
                    *v += noise.green_luma_sigma(*v) * rng.normal();
                }
                plane
            })
            .collect();

        let hit_rate = |fields: &[Vec<f32>]| -> f64 {
            let win = winners(fields);
            let m = SUPPORT_RADIUS + 2;
            let (mut hit, mut n) = (0usize, 0usize);
            for y in m..h - m {
                for x in m..w - m {
                    if win[y * w + x] == truth {
                        hit += 1;
                    }
                    n += 1;
                }
            }
            hit as f64 / n as f64
        };

        let ten: Vec<Vec<f32>> = planes.iter().map(|p| field(w, h, p)).collect();
        let ring: Vec<Vec<f32>> = planes.iter().map(|p| ring_field(w, h, p)).collect();
        let placebo = random_fields(frames, w * h);
        let (a_ten, a_ring, a_placebo) = (hit_rate(&ten), hit_rate(&ring), hit_rate(&placebo));
        println!(
            "planted plant: exact-hit tenengrad-w{WINDOW_RADIUS} = {a_ten:.4}, ring-1-3 = \
             {a_ring:.4}, placebo = {a_placebo:.4}, chance = {:.4}",
            1.0 / frames as f64
        );

        let chance = 1.0 / frames as f64;
        assert!(
            (a_placebo - chance).abs() < 0.02,
            "the placebo must sit at chance {chance:.4}, got {a_placebo:.4}"
        );
        assert!(
            a_ring > chance,
            "the ring must beat chance or the plant is broken, got {a_ring:.4}"
        );
        assert!(
            a_ten > a_ring,
            "tenengrad {a_ten:.4} must beat the ring {a_ring:.4}"
        );
        assert!(
            a_ten > 0.9,
            "tenengrad should be near-perfect on a fronto-parallel plant, got {a_ten:.4}"
        );
    }

    // ------------------------------------------------------- centre-tap probe

    /// How much of this measure's response at a pixel comes from that pixel's
    /// own value, by finite difference on the shipped code path.
    ///
    /// Shift invariance away from the border makes `d focus(q) / d luma(p)` a
    /// function of `q - p` alone, so perturbing one pixel yields the whole
    /// sensitivity kernel and `phi = |dr(0)| / sum |dr(d)|` falls straight out.
    ///
    /// `probe` selects the stage: the shipped normalised operator, or M11's
    /// `Norm::None` arm at a given radius. The distinction matters — fact 39 is
    /// that windowing and normalisation each contribute a centre tap, so phi is
    /// a property of the **configured stage**, never of the kernel.
    fn centre_tap_fraction(
        delta: f32,
        amplitude: f32,
        reach: usize,
        probe: impl Fn(usize, usize, &[f32]) -> Vec<f32>,
    ) -> (f64, usize) {
        // Big enough that every window the probe touches is unclamped: a pixel
        // `reach` away reads a further SUPPORT_RADIUS, so the centre needs that
        // much clear space on all sides.
        let side = 2 * (reach + SUPPORT_RADIUS) + 3;
        let (w, h) = (side, side);
        // Deterministic textured field. A flat field will not do: the response
        // is identically zero there and the finite difference would measure the
        // rectification kink instead of the operator.
        let luma: Vec<f32> = (0..w * h)
            .map(|i| {
                let (x, y) = ((i % w) as f32, (i / w) as f32);
                3000.0
                    + amplitude * (x * 1.31).sin() * (y * 1.07).cos()
                    + 0.5 * amplitude * (x * 0.37 + y * 0.29).sin()
            })
            .collect();
        let base = probe(w, h, &luma);
        let mut bumped = luma.clone();
        let centre = (h / 2) * w + w / 2;
        bumped[centre] += delta;
        let bump = probe(w, h, &bumped);

        let (mut at_centre, mut total, mut taps) = (0.0f64, 0.0f64, 0usize);
        for dy in 0..2 * reach + 1 {
            for dx in 0..2 * reach + 1 {
                let q = (h / 2 + dy - reach) * w + (w / 2 + dx - reach);
                let d = ((bump[q] - base[q]) as f64 / delta as f64).abs();
                if d > 1e-6 {
                    taps += 1;
                }
                if dx == reach && dy == reach {
                    at_centre = d;
                }
                total += d;
            }
        }
        (at_centre / total, taps)
    }

    #[test]
    fn centre_tap_fraction_and_read_extent_are_what_m13_specified() {
        // Successor to `centre_tap_fraction_is_the_value_m9_measured`, which
        // pinned phi = 1/18 and 49 taps for ring(1,3). M11 and M13 §6.4 both
        // said this test must be UPDATED, not deleted: phi is the quantity M9
        // measured argmax's noise excess to track (rho = +0.918 / +0.894
        // against support radius's -0.170 / -0.243, SYNTHESIS fact 35), so a
        // regression in it means the merge's noise-election behaviour changed.
        //
        // What can and cannot be pinned is different now, and that difference
        // is the point:
        //
        //   - The TAP COUNT is analytic. `(2*(SOBEL_RADIUS + WINDOW_RADIUS)+1)^2
        //     = 29^2 = 841`. It pins both radii exactly and it is asserted
        //     exactly.
        //   - phi ITSELF IS NOT. For ring(1,3), phi = 1/(2*(2*inner+1)^2) is a
        //     property of the kernel alone. Under a box window plus pointwise
        //     sigma normalisation it is texture- and probe-dependent: M13 §1.4
        //     measures 0.1390 at w13 on 109MSDCF texture at delta = 8 DN, and
        //     0.1321 / 0.1107 at delta = 1 / 32 DN on the SAME ROI. Pinning
        //     0.1390 to 4 dp would pin a property of one ROI and one probe
        //     amplitude. Step 2 below shows it moving 47x on this plant alone.
        //   - The un-normalised arm IS analytic, and it is asserted, because it
        //     is the half of fact 39 that does not depend on the scene. So are
        //     the two structural relations phi does obey: the divisor dominates
        //     the centre tap, and phi tracks texture contrast.

        // 1. Read extent, on the shipped operator. Analytic, exact.
        let reach = SUPPORT_RADIUS + 2;
        let (phi, taps) = centre_tap_fraction(8.0, 120.0, reach, field);
        let analytic_taps = (2 * SUPPORT_RADIUS + 1).pow(2);
        assert_eq!(analytic_taps, 841);
        assert_eq!(
            taps,
            analytic_taps,
            "read extent must be the {}x{} square that a {}x{} Sobel under a \
             {}x{} box implies, got {taps} taps",
            2 * SUPPORT_RADIUS + 1,
            2 * SUPPORT_RADIUS + 1,
            2 * SOBEL_RADIUS + 1,
            2 * SOBEL_RADIUS + 1,
            2 * WINDOW_RADIUS + 1,
            2 * WINDOW_RADIUS + 1,
        );

        // 2. phi on the whole configured stage. NOT pinned to a number, and
        // this is the evidence for why not. M13 §6.4 suggested a bracket of
        // `0.10 < phi < 0.18` around its measured 0.1390. **That bracket does
        // not survive off 109MSDCF texture.** On this synthetic probe phi is a
        // near-linear function of texture contrast, spanning 47x over a 64x
        // amplitude range while the operator does not change at all:
        //
        //     amplitude   30     60    120    240    480    960   1920
        //     phi     0.0085 0.0228 0.0516 0.1036 0.1864 0.2959 0.3987
        //
        // (delta = 8 DN; measured by this same probe.) Landing inside
        // 0.10-0.18 needs an amplitude near 330 DN, chosen to match one ROI.
        // Asserting the bracket would therefore pin the plant, which is the
        // exact failure M13 §6.4 said to avoid. What IS operator-intrinsic is
        // asserted instead, below.
        println!(
            "phi(tenengrad-w{WINDOW_RADIUS}, sigma-normalised) = {phi:.5} on synthetic \
             texture at amplitude 120 DN (M13: 0.1390 on real 109MSDCF texture)"
        );
        assert!(
            (0.005..0.30).contains(&phi),
            "phi {phi:.5} left even the loose sanity band; something structural changed"
        );

        // 3. The analytic anchors, on M11's Norm::None arm.
        //
        // (a) At window 0 the un-normalised response is the bare Sobel
        //     magnitude, and BOTH Sobel kernels have a zero centre weight, so a
        //     perturbation at p cannot change the response AT p. phi is exactly
        //     zero, not approximately -- this is a derivation, and M13's
        //     phi-nonorm CSV measures 0.0000000000 for it. The 8 taps are the
        //     8 neighbours that do respond; a 3x3 stencil with a live centre
        //     would report 9.
        let (phi_w0, taps_w0) = centre_tap_fraction(8.0, 120.0, SOBEL_RADIUS + 2, |w, h, l| {
            unnormalised(w, h, l, 0)
        });
        assert_eq!(phi_w0, 0.0, "the Sobel centre weight is 0 in Gx and Gy");
        assert_eq!(
            taps_w0, 8,
            "a 3x3 stencil with a dead centre has 8 live taps"
        );

        // (b) At window 13 the box mean dilutes that single live tap over its
        //     own area, so phi_nonorm -> 1/(2w+1)^2 from below. M13 §1.4
        //     measures the ratio climbing 0.62 -> 0.978 across w1 -> w40, and
        //     0.94 at w13 (0.00128784 measured against 0.00137174 analytic).
        //     The shortfall is the Sobel's own 3x3 support, which is not a
        //     point.
        let (phi_nonorm, taps_nonorm) = centre_tap_fraction(8.0, 120.0, reach, |w, h, l| {
            unnormalised(w, h, l, WINDOW_RADIUS)
        });
        assert_eq!(taps_nonorm, analytic_taps);
        let analytic = 1.0 / ((2 * WINDOW_RADIUS + 1) as f64).powi(2);
        assert!((analytic - 1.0 / 729.0).abs() < 1e-12);
        let ratio = phi_nonorm / analytic;
        println!(
            "phi(tenengrad-w{WINDOW_RADIUS}, un-normalised) = {phi_nonorm:.8}, analytic \
             1/{}^2 = {analytic:.8}, ratio {ratio:.4} (M13 measured 0.94)",
            2 * WINDOW_RADIUS + 1
        );
        assert!(
            (0.88..1.0).contains(&ratio),
            "un-normalised phi {phi_nonorm:.8} is {ratio:.4} of the analytic \
             {analytic:.8}; M13 §1.4 measures 0.94 at w13 and the limit is 1.0 \
             from below"
        );

        // 4. Fact 39, on this code path: windowing and pointwise normalisation
        //    each re-introduce a centre tap, and at this window the DIVISOR is
        //    the one that matters. The operator's own diluted tap is 1/729 of
        //    its response; the configured stage's is tens of times larger. If
        //    the divisor were ever dropped or moved off the centre pixel, this
        //    ratio would collapse to 1 and the merge's noise-election
        //    behaviour would change with it.
        assert!(
            phi > 20.0 * phi_nonorm,
            "the sigma divisor must dominate the centre tap: phi {phi:.5} vs \
             un-normalised {phi_nonorm:.8}"
        );

        // 5. And the texture dependence itself, asserted rather than asserted
        //    around. Quadrupling the probe's contrast must move phi several
        //    fold, because the divisor's centre tap scales with the response
        //    while the operator's does not. This is the property that makes a
        //    4-dp pin meaningless, so it is the property the test states.
        let (phi_hi, _) = centre_tap_fraction(8.0, 480.0, reach, field);
        println!("phi at amplitude 480 DN = {phi_hi:.5}, at 120 DN = {phi:.5}");
        assert!(
            phi_hi > 2.5 * phi,
            "phi must track texture contrast: {phi_hi:.5} at 480 DN against \
             {phi:.5} at 120 DN"
        );

        // 6. Discrimination. The tap count is what pins WINDOW_RADIUS, and it
        //    does so exactly: a one-step change moves it by 4*SUPPORT_RADIUS+4
        //    = 60 taps.
        assert_ne!(analytic_taps, (2 * (SUPPORT_RADIUS - 1) + 1).pow(2));
        assert_ne!(analytic_taps, (2 * (SUPPORT_RADIUS + 1) + 1).pow(2));
    }
}
