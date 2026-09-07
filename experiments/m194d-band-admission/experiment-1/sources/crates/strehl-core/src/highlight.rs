//! Highlight chroma roll-off: what happens to colour on the way to the ceiling.
//!
//! # The defect this exists for
//!
//! `color::Render::clip_highlights` (M109) already fixes the *pinned* case: a
//! sample at or above its own saturation ceiling is brought down to the neutral
//! ceiling `min_c ceiling[c]`, so a blown neutral renders neutral instead of
//! magenta. That fix is exact and it is kept; this module runs after it.
//!
//! What it does not fix is the *approach*. M109 section 16 measured why: of the
//! sensels pinned in at least one frame, only **21.02 %** are pinned in *every*
//! frame. The merge averages pinned and unpinned samples, so the merged value
//! lands strictly below `ceiling[c]` and a `v_c >= ceiling[c]` guard never
//! fires — while the channel that pinned stays suppressed relative to the ones
//! that did not. M109's own words: *"the guard asks a per-frame question of a
//! post-merge value"*.
//!
//! BUILD-HIGHLIGHT measured the size of that gap on `foam` (100 frames, pyramid
//! backend, one binary). Writing `u_c = v_c / ceiling[c]` — the sample's raw
//! level as a fraction of the 14-bit container, which is **independent of the
//! white-balance gain**, because `ceiling[c]` carries the same gain that `v_c`
//! does — the camera-native render (`OutputSpace::CameraLinear`, no matrix, so
//! `v` is readable directly) says:
//!
//! | channel | its ceiling in `v` | where the writer's `clamp(0,1)` cuts it | raw DN at that cut | pixels cut |
//! | --- | --- | --- | --- | --- |
//! | R | 2.8654 | `u = 0.3490` | 6 051 | 0.4007 % |
//! | G | 1.0689 | `u = 0.9355` | 15 360 | 0.3985 % |
//! | B | 1.6305 | `u = 0.6133` | 10 246 | 0.4950 % |
//!
//! **There are two ceilings in this pipeline and they are unequal in opposite
//! directions.** The sensor's container is equal in *raw* DN and therefore
//! unequal in `v` — white balance carries red to 2.6807x and blue to 1.5254x
//! green's height, so green runs out first. The writer's clamp is equal in `v`
//! and therefore unequal in raw DN — it cuts red at 6 051 DN, less than 37 % of
//! what the sensor recorded. The first asymmetry is the one that colours
//! highlights, because it is the one a *scene* walks into: a neutral highlight
//! is equal in `v` by construction, so it meets the writer's clamp on all three
//! channels at once and goes cleanly white, but it meets the container on green
//! alone.
//!
//! What survives into the merged file is the diluted form of that. `B/G` climbs
//! 1.0061 -> 1.1697 monotonically across the level deciles of `foam`'s hot edge
//! set, with green the argmax of `u` on **98.37 %** of those pixels: a one-sided
//! blue excess that grows with level, which a fixed white-balance gain cannot
//! produce because a gain is a constant multiple independent of level.
//!
//! # What this module does
//!
//! Below the knee it is the **identity, exactly** — the same safety argument
//! `clip_highlights` makes, and for the same reason: an unsaturated stack must
//! not move by one bit. Above it, the triple is blended toward the neutral of
//! **the same luminance**, so the correction removes chroma and never touches
//! brightness.
//!
//! ```text
//! u   = max_c v_c / ceiling[c]
//! t   = smoothstep((u - knee) / (top - knee))        0 at the knee, 1 at usable white
//! n   = 0.2126 * (M[0].v) + 0.7152 * (M[1].v) + 0.0722 * (M[2].v)
//! v'  = v + t * (n - v)
//! ```//!
//! `n` is the linear-sRGB luminance of the pixel, and it is also the value of
//! the **camera-space neutral with that luminance**: every row of
//! [`crate::color::camera_to_srgb`] sums to 1, so a triple `(n, n, n)` renders
//! to `(n, n, n)` and has luminance `n * (0.2126 + 0.7152 + 0.0722) = n`. The
//! blend is therefore luminance-preserving *exactly*, not to a tolerance —
//! [`tests::the_rolloff_preserves_luminance_exactly`] asserts it. Highlight
//! detail lives in luminance; the colour on a blown highlight does not.
//!
//! # Why `u`, and not the pixel's brightness
//!
//! Keying on `max_c v_c` would bleach genuinely bright saturated colours,
//! because white balance carries red to 2.6807x and blue to 1.5254x green's
//! height: a red object at `v_R = 1.5` is *nowhere near* saturated in raw terms
//! (red would need about 12 700 DN before `u_R` reached the knee) but it is well
//! above green's ceiling of 1.0689. `u` divides that gain back out, so the
//! driver is "how close is the closest raw plane to the container", which is the
//! question the sensor actually answers.
//!
//! # Why roll off toward neutral rather than reconstruct the clipped channel
//!
//! Reconstruction — inferring the suppressed channel from the unclipped ones
//! plus the local hue — recovers more, and it is the better fix where it can be
//! verified. It cannot be verified here: post-merge there is no per-pixel record
//! of *which* channel was clipped in *which* frames, because the pyramid backend
//! carries no censoring state (its own banner prints `not applied: ... clip
//! census`). Reconstructing from a value that is already an average of clipped
//! and unclipped samples would be inventing a measurement. That is the same
//! reason `clip_highlights` discards the headroom above the neutral ceiling
//! rather than keeping it.
//!
//! # Relationship to the hull clamp
//!
//! `pyramid::Hull::InputRange` clamps each reconstructed pixel to the range of
//! the frames that contributed to it. It is a base-octave tone correction and it
//! is *why* merged `foam` tops out at `Levels::white` rather than overshooting;
//! it is not the cause of the colour cast and this module does not fight it. The
//! clamp is per channel against that channel's own input range, so it cannot
//! equalise the three ceilings — only shrink each toward its own inputs.
//!
//! # Switching it off
//!
//! `STREHL_HIGHLIGHT_KNEE=off` restores the previous render **bit-exactly**
//! (the roll-off is skipped entirely, not evaluated at `t = 0`), and a numeric
//! value moves the knee, which is how the negative control in
//! `docs/research/BUILD-HIGHLIGHT.md` plants an exaggerated version of the
//! defect's opposite and shows the instrument responds. It is **on by default**
//! because it is a defect fix.

use std::sync::OnceLock;

/// The environment variable that moves or disables the knee.
pub const KNEE_ENV: &str = "STREHL_HIGHLIGHT_KNEE";

/// Where the roll-off starts, as a fraction of the container ceiling.
///
/// **0.60, anchored on the corpus's unsaturated stacks rather than tuned to the
/// residual.** `109MSDCF`'s documented per-channel maxima are 39–61 % of
/// `Levels::white`, which is `u <= 0.61 / 1.068898 = 0.5707`: a knee at 0.60
/// therefore leaves every stack that never approaches saturation **bit
/// identical**, with margin, and that null is a measurement rather than a hope
/// (`docs/research/BUILD-HIGHLIGHT.md`, the placebo arm).
///
/// In raw terms 0.60 of the container is 10 342 DN, 67 % of usable white. That
/// is the shoulder where per-frame container clipping starts to contribute:
/// BUILD-HIGHLIGHT's h1 measured green pinned at 16 383 DN on up to 0.1255 % of
/// a mid-stack `foam` frame while red and blue were pinned 5x and 137x less
/// often, and it is those frames' contribution, averaged into the merge, that
/// leaves the surviving green deficit.
///
/// **What the knee reaches, and what it does not** (BUILD-OUTPUT, measured on
/// the shipping binary against pin `b9b6921e`, `--srgb --auto-exposure`).
/// The roll-off is what removes `dry-erase-marker-head-cpl`'s top-of-scale
/// failure. That master had **0.9541 %** of pixels with blue at exactly 65535
/// while red and green sat near 0.964 of full scale -- a bright near-white
/// highlight whose blue channel reached the ceiling first, taking the hue with
/// it. With the roll-off the same stack renders **0.0000 %**; with
/// `STREHL_HIGHLIGHT_KNEE=off` it renders **0.6109 %**, reproducing the pinned
/// binary's number to four decimals. That is a planted-defect / planted-fix
/// pair on the real subject, not a synthetic one.
///
/// It does **not** reach `flowers-cpl`, and the reason is structural rather
/// than a matter of tuning. Knees of 0.60, 0.45 and 0.30 all produce the same
/// **0.4488 %** blue-at-65535 -- bit identical, not merely close. This module
/// works in **camera space against the container ceiling**, so it only sees
/// pixels the *sensor* drove near saturation. `flowers-cpl`'s blue reaches the
/// ceiling only after `--auto-exposure` adds +1.9 stops and the tone stage
/// re-normalises p99.9 luminance to 0.90, both of which happen downstream of
/// this function. Lowering the knee cannot help: there is nothing here for it
/// to act on. Anything that bounds that population has to live in the tone
/// stage, where a single luminance-derived gain is applied to all three
/// channels and therefore does not bound any one of them.
pub const DEFAULT_KNEE: f32 = 0.60;

/// Where the roll-off completes for a caller that has not stated its usable
/// white: the container itself.
///
/// This is the conservative value — it makes the ramp as gentle as it can be —
/// and it is what [`crate::color::Render::with_ceiling`] uses. Callers that
/// know their [`crate::sensor::Levels`] should use
/// [`crate::color::Render::with_saturation`], which states `range / (container
/// - black)` = 0.9355 on the reference body instead.
pub const CONTAINER_TOP: f32 = 1.0;

/// BT.709 luminance weights, the ones linear sRGB is defined with. They sum to
/// 1, which is what makes the blend below luminance-preserving.
const LUMA: [f32; 3] = [0.2126, 0.7152, 0.0722];

/// The knee in force for this process, read once.
///
/// `None` means the roll-off is off and [`desaturate`] is the identity on every
/// input — the state the render was in before this module existed.
pub fn knee() -> Option<f32> {
    static KNEE: OnceLock<Option<f32>> = OnceLock::new();
    *KNEE.get_or_init(|| match std::env::var(KNEE_ENV) {
        Err(_) => Some(DEFAULT_KNEE),
        Ok(v) if v.trim().eq_ignore_ascii_case("off") || v.trim() == "0" => None,
        Ok(v) => match v.trim().parse::<f32>() {
            Ok(x) if x.is_finite() && x > 0.0 && x < 1.0 => {
                eprintln!("highlight: chroma roll-off knee moved to {x} (was {DEFAULT_KNEE})");
                Some(x)
            }
            _ => {
                eprintln!(
                    "{KNEE_ENV}={v:?} is not `off` or a number in (0, 1); \
                     using the default {DEFAULT_KNEE}"
                );
                Some(DEFAULT_KNEE)
            }
        },
    })
}

/// The linear-sRGB luminance of a white-balanced camera triple, which is also
/// the camera-space neutral that renders to that luminance.
///
/// `to_srgb` must be a matrix whose rows each sum to 1 —
/// [`crate::color::camera_to_srgb`] guarantees it and asserts it.
#[inline]
#[must_use]
pub fn neutral_luma(to_srgb: &[[f32; 3]; 3], v: [f32; 3]) -> f32 {
    let mut n = 0.0f32;
    for r in 0..3 {
        n += LUMA[r] * (to_srgb[r][0] * v[0] + to_srgb[r][1] * v[1] + to_srgb[r][2] * v[2]);
    }
    n
}

/// The blend weight at a given approach `u`, in `[0, 1]`.
///
/// The ramp starts at `knee` and **completes at `top`**, both expressed as
/// fractions of the container ceiling. `top` exists because the container is
/// not where the data stops: `pyramid::Hull::InputRange` holds the merged file
/// to the range of its contributing frames, so `foam` tops out at
/// [`crate::sensor::Levels::white`] — `u = 0.9355`, not 1.0. With the container
/// as the endpoint the correction is still incomplete exactly where it is
/// needed: `foam`'s top level decile averages `u = 0.7990`, at which
/// `t = 0.50`, and the measured result was that the decile's `B/G` excess fell
/// only 29 % (1.1697 to 1.1220). Moving the endpoint to usable white raises
/// that same `t` to 0.64 and completes the ramp at the top of the file.
/// [`crate::color::Render::with_saturation`] states the honest `top`;
/// [`crate::color::Render::with_ceiling`] leaves it at [`CONTAINER_TOP`], which
/// is the conservative choice for a caller that has not said where its usable
/// white is.
///
/// Smoothstep rather than a ramp so the first derivative is continuous at the
/// knee: a kink there would print as a visible contour ring around every
/// highlight, which is a worse artefact than the one being removed.
#[inline]
#[must_use]
pub fn weight(knee: f32, top: f32, u: f32) -> f32 {
    // NaN and infinity both take the early return, so a corrupt sample can
    // never be silently blended: it is left exactly as it arrived.
    if !u.is_finite() || u <= knee {
        return 0.0;
    }
    // Never let the ramp invert or divide by zero, whatever a caller states.
    let top = if top.is_finite() && top > knee {
        top
    } else {
        knee + f32::EPSILON.max(1e-3)
    };
    let x = ((u - knee) / (top - knee)).clamp(0.0, 1.0);
    x * x * (3.0 - 2.0 * x)
}

/// Roll the chroma of a white-balanced camera triple off toward neutral as it
/// approaches the container, preserving luminance exactly.
///
/// `ceiling` is [`crate::color::saturation_ceiling`]'s per-channel value in the
/// render's own units; `+inf` (a render with no stated ceiling) makes this the
/// identity, because `u` is then 0. `top` is where the ramp completes, as a
/// fraction of that ceiling — see [`weight`].
///
/// **Below the knee this returns `v` itself**, by an early return rather than by
/// arithmetic that happens to come out to zero, so an unsaturated stack is
/// bit-identical.
#[inline]
#[must_use]
pub fn desaturate(ceiling: [f32; 3], top: f32, to_srgb: &[[f32; 3]; 3], v: [f32; 3]) -> [f32; 3] {
    match knee() {
        None => v,
        Some(k) => desaturate_with(k, top, ceiling, to_srgb, v),
    }
}

/// [`desaturate`] with the knee supplied rather than read from the environment,
/// so tests and controls do not depend on process state.
#[inline]
#[must_use]
pub fn desaturate_with(
    knee: f32,
    top: f32,
    ceiling: [f32; 3],
    to_srgb: &[[f32; 3]; 3],
    v: [f32; 3],
) -> [f32; 3] {
    let mut u = 0.0f32;
    for c in 0..3 {
        let x = v[c] / ceiling[c];
        if x > u {
            u = x;
        }
    }
    let t = weight(knee, top, u);
    if t <= 0.0 {
        return v;
    }
    let n = neutral_luma(to_srgb, v);
    if !n.is_finite() {
        return v;
    }
    [
        v[0] + t * (n - v[0]),
        v[1] + t * (n - v[1]),
        v[2] + t * (n - v[2]),
    ]
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::color::{camera_to_srgb, saturation_ceiling};
    use crate::noise::Levels;

    /// The A7C II's characterisation, as MEASURED through an independent
    /// decoder (`rawpy`/LibRaw) and published in
    /// `docs/research/M26-colour-clipping-measured.md` §1. It is a **fixture**,
    /// not a constant of this crate — the pipeline reads the live value from
    /// each file — and it is the same fixture `color.rs`'s own tests use, per
    /// AGENTS.md rule 35.
    const A7C2_XYZ_TO_CAM: [[f32; 3]; 3] = [
        [0.7460, -0.2365, -0.0588],
        [-0.5687, 1.3442, 0.2474],
        [-0.0624, 0.1156, 0.6584],
    ];

    /// As-shot green-normalised gains on the reference rig, from the same
    /// report: `2751/1024` and `1569/1024` against green's 1.
    const A7C2_WB: [f32; 3] = [2751.0 / 1024.0, 1.0, 1569.0 / 1024.0];

    /// `foam`'s own as-shot gains, as reported by `strehl probe
    /// D:\personal\macro\foam`: `2745/1024` and `1562/1024`. They differ from
    /// the rig fixture in the third decimal, which is enough to move a B/G ratio
    /// in the fourth, so the test that reproduces BUILD-CHROMA's statistic uses
    /// the stack's own numbers.
    const FOAM_WB: [f32; 3] = [2745.0 / 1024.0, 1.0, 1562.0 / 1024.0];

    const RIG: Levels = Levels {
        black: 512.0,
        white: 15360.0,
    };

    /// Where usable white sits on the rig, as a fraction of the container:
    /// `(white - black) / (CONTAINER_MAX_DN - black) = 14848 / 15871`.
    const RIG_TOP: f32 = 14848.0 / 15871.0;

    fn rig() -> ([f32; 3], [[f32; 3]; 3]) {
        let render = camera_to_srgb(A7C2_XYZ_TO_CAM).expect("invertible");
        (saturation_ceiling(RIG, A7C2_WB, 1.0), *render.matrix())
    }

    /// The rows of the render matrix sum to 1 and the luma weights sum to 1.
    /// Both are load-bearing: together they are why a neutral input is a neutral
    /// output and why the blend cannot change luminance.
    #[test]
    fn the_two_sums_the_blend_rests_on_are_both_one() {
        let (_, m) = rig();
        for (r, row) in m.iter().enumerate() {
            let s = row[0] + row[1] + row[2];
            assert!((s - 1.0).abs() < 2e-6, "row {r} sums to {s}, not 1");
        }
        let s = LUMA[0] + LUMA[1] + LUMA[2];
        assert!((s - 1.0).abs() < 1e-6, "luma weights sum to {s}, not 1");
    }

    /// **The null, as an identity rather than an observation.** Nothing below
    /// the knee moves by a single bit, on any hue.
    ///
    /// Power to fail: the *same sweep* is checked in both directions — every
    /// triple whose approach exceeds the knee is asserted to move, and the count
    /// of each is asserted non-trivial, so a roll-off that did nothing would
    /// fail the second half and a roll-off that touched everything would fail
    /// the first.
    #[test]
    fn nothing_below_the_knee_moves_by_a_single_bit() {
        let (ceil, m) = rig();
        let (mut below, mut above) = (0usize, 0usize);
        for i in 0..=200 {
            let s = i as f32 / 200.0;
            for hue in [
                [1.0f32, 1.0, 1.0],
                [1.0, 0.3, 0.2],
                [0.2, 0.4, 1.0],
                [0.6, 1.0, 0.5],
            ] {
                let v = [
                    s * ceil[0] * hue[0],
                    s * ceil[1] * hue[1],
                    s * ceil[2] * hue[2],
                ];
                let u = (v[0] / ceil[0]).max(v[1] / ceil[1]).max(v[2] / ceil[2]);
                let out = desaturate_with(DEFAULT_KNEE, RIG_TOP, ceil, &m, v);
                if u <= DEFAULT_KNEE {
                    assert_eq!(out, v, "moved a triple below the knee: u {u}");
                    below += 1;
                } else {
                    assert_ne!(out, v, "a triple above the knee did not move: u {u}");
                    above += 1;
                }
            }
        }
        assert!(
            below > 400 && above > 200,
            "degenerate sweep: {below} / {above}"
        );
    }

    /// Luminance is preserved exactly, at every weight and on every hue. This is
    /// the answer to "does the fix cost highlight detail": detail is luminance,
    /// and luminance does not move.
    #[test]
    fn the_rolloff_preserves_luminance_exactly() {
        let (ceil, m) = rig();
        for hue in [
            [1.0f32, 1.0, 1.0],
            [0.35, 1.0, 0.62],
            [1.0, 0.5, 0.9],
            [0.9, 0.95, 1.0],
        ] {
            for i in 0..=40 {
                let s = 0.70 + i as f32 / 40.0 * 0.30;
                let v = [
                    s * ceil[0] * hue[0],
                    s * ceil[1] * hue[1],
                    s * ceil[2] * hue[2],
                ];
                let before = neutral_luma(&m, v);
                let after = neutral_luma(&m, desaturate_with(DEFAULT_KNEE, RIG_TOP, ceil, &m, v));
                assert!(
                    (after - before).abs() <= 4e-6 * before.abs().max(1.0),
                    "luminance moved {before} -> {after} on hue {hue:?} at s {s}"
                );
            }
        }
    }

    /// **The defect, on the numbers that were measured, and the fix.**
    ///
    /// The top level decile of `foam`'s hot edge set reads mean
    /// `u_R 0.2886, u_G 0.7990, u_B 0.5653` — a green four fifths of the way to
    /// its container ceiling while red is barely a quarter of the way to its
    /// own. Rendered through the matrix that is a blue excess of
    /// `B/G = 1.135`, which is BUILD-CHROMA section 25's statistic.
    ///
    /// Power to fail: the identical input is first asserted to *carry* the
    /// excess. If a future edit made the render neutral for some other reason
    /// the first assertion would fail rather than the test quietly passing.
    #[test]
    fn foams_measured_blue_excess_collapses_toward_neutral() {
        let render = camera_to_srgb(A7C2_XYZ_TO_CAM).expect("invertible");
        let m = *render.matrix();
        let ceil = saturation_ceiling(RIG, FOAM_WB, 1.0);
        // BUILD-HIGHLIGHT h3 section G, decile 9 of foam's hot edge set.
        let v = [0.2886 * ceil[0], 0.7990 * ceil[1], 0.5653 * ceil[2]];
        let bg = |x: [f32; 3]| {
            let o = crate::color::apply(&m, x);
            o[2] / o[1]
        };
        let before = bg(v);
        assert!(
            (before - 1.135).abs() < 0.02,
            "the defect did not reproduce: rendered B/G is {before}, not 1.135 \
             -- this test is then measuring something other than the reported \
             failure"
        );
        let after = bg(desaturate_with(DEFAULT_KNEE, RIG_TOP, ceil, &m, v));
        assert!(
            after < before - 0.05,
            "B/G is still {after} after the roll-off (was {before})"
        );
        assert!(
            after >= 1.0,
            "the roll-off overshot past neutral into a green excess: {after}"
        );
    }

    /// A genuinely saturated colour whose raw planes are all well below the
    /// container is untouched, however bright white balance makes it look.
    ///
    /// A red object at `v_R = 1.5` is above green's ceiling of 1.0689 and would
    /// be bleached by any driver keyed on `max_c v_c`. Its red plane is at
    /// `u_R = 0.52` — about 8 600 DN of a 16 383 DN container — so it is not
    /// near saturation at all and this driver leaves it alone.
    #[test]
    fn a_bright_saturated_colour_below_the_container_is_untouched() {
        let (ceil, m) = rig();
        let red = [1.5f32, 0.30, 0.25];
        assert!(
            red[0] > ceil[1],
            "the test's premise is wrong: {red:?} {ceil:?}"
        );
        assert_eq!(desaturate_with(DEFAULT_KNEE, RIG_TOP, ceil, &m, red), red);
        // Power to fail: a driver on max_c v_c would have fired here.
        assert!(
            weight(DEFAULT_KNEE, RIG_TOP, red[0] / ceil[1]) > 0.5,
            "the premise of this test is that a v-keyed driver WOULD have fired"
        );
    }

    /// A render with no stated ceiling — [`crate::color::Render::new`] — gets no
    /// roll-off, so nothing that never asked for a ceiling can move.
    #[test]
    fn no_ceiling_means_no_rolloff() {
        let (_, m) = rig();
        let inf = [f32::INFINITY; 3];
        for v in [[0.1f32, 0.2, 0.3], [9.0, 9.0, 9.0], [1e9, 1.0, 1.0]] {
            assert_eq!(desaturate_with(DEFAULT_KNEE, RIG_TOP, inf, &m, v), v);
        }
    }

    /// The roll-off commutes with the exposure gain, for the same reason the
    /// ceiling does: `u` is a ratio and the gain is in both halves of it. The
    /// blend is linear in `v` at fixed `t`, and `t` depends only on `u`.
    #[test]
    fn the_rolloff_commutes_with_the_exposure_gain() {
        let render = camera_to_srgb(A7C2_XYZ_TO_CAM).expect("invertible");
        let m = *render.matrix();
        for g in [0.5f32, 0.847, 1.0, 2.97] {
            let at_gain = saturation_ceiling(RIG, A7C2_WB, g);
            let at_one = saturation_ceiling(RIG, A7C2_WB, 1.0);
            for v in [[0.9f32, 0.9, 0.9], [2.4, 0.95, 1.4], [0.2, 1.05, 0.3]] {
                let folded = desaturate_with(
                    DEFAULT_KNEE,
                    RIG_TOP,
                    at_gain,
                    &m,
                    [v[0] * g, v[1] * g, v[2] * g],
                );
                let after = desaturate_with(DEFAULT_KNEE, RIG_TOP, at_one, &m, v).map(|x| x * g);
                for c in 0..3 {
                    assert!(
                        (folded[c] - after[c]).abs() <= 4e-6 * folded[c].abs().max(1.0),
                        "gain {g}: {folded:?} vs {after:?}"
                    );
                }
            }
        }
    }

    /// The weight is continuous and monotone, is exactly 0 at the knee and
    /// exactly 1 at its stated endpoint, and never leaves `[0, 1]`.
    #[test]
    fn the_weight_is_a_well_behaved_ramp() {
        assert_eq!(weight(0.70, 1.0, 0.70), 0.0);
        assert_eq!(weight(0.70, 1.0, 0.0), 0.0);
        assert_eq!(weight(0.70, 1.0, -3.0), 0.0);
        assert_eq!(weight(0.70, 1.0, f32::NAN), 0.0);
        assert!((weight(0.70, 1.0, 1.0) - 1.0).abs() < 1e-6);
        assert!((weight(0.70, 1.0, 4.0) - 1.0).abs() < 1e-6);
        let mut last = 0.0;
        for i in 0..=1000 {
            let u = i as f32 / 1000.0;
            let w = weight(0.70, 1.0, u);
            assert!((0.0..=1.0).contains(&w), "weight {w} out of range at u {u}");
            assert!(w >= last - 1e-7, "weight fell at u {u}: {last} -> {w}");
            last = w;
        }
    }

    /// **The endpoint is load-bearing, and this is the measurement that says
    /// so.** `foam`'s hot edge set tops out at `u = 0.9355`, because
    /// `Hull::InputRange` holds the merge to the range of its inputs, and its
    /// top level decile *averages* `u_G = 0.7990`. Ending the ramp at the
    /// container leaves that decile 50 % corrected; ending it at usable white
    /// takes it to 64 %, and takes the hottest pixel from 93 % to a complete 1.
    ///
    /// Power to fail in both directions: the container endpoint is asserted to
    /// be *insufficient* as well as the usable-white endpoint sufficient, so
    /// this cannot pass by the two being accidentally equal.
    #[test]
    fn ending_the_ramp_at_usable_white_is_what_finishes_the_correction() {
        // Measured: foam-cam.tif, where green's writer clamp cuts.
        let u_hot = 0.93554f32;
        // Measured: h3 section G, the mean of decile 9's argmax channel.
        let u_decile9 = 0.7990f32;

        let hot_c = weight(DEFAULT_KNEE, CONTAINER_TOP, u_hot);
        let hot_u = weight(DEFAULT_KNEE, RIG_TOP, u_hot);
        assert!(
            hot_c < 0.94,
            "the container endpoint should not finish: {hot_c}"
        );
        assert!(hot_u > 0.999, "usable white should finish: {hot_u}");

        let d9_c = weight(DEFAULT_KNEE, CONTAINER_TOP, u_decile9);
        let d9_u = weight(DEFAULT_KNEE, RIG_TOP, u_decile9);
        assert!(
            (0.48..0.52).contains(&d9_c),
            "the container endpoint should leave the top decile about half \
             corrected, but t is {d9_c}"
        );
        assert!(
            d9_u > d9_c * 1.20,
            "usable white should correct the top decile materially harder: \
             {d9_u} vs {d9_c}"
        );
        // And it is still exactly 0 below the knee, which is the null.
        assert_eq!(weight(DEFAULT_KNEE, RIG_TOP, 0.5707), 0.0);
    }

    /// A degenerate `top` must not invert the ramp or divide by zero. Stating
    /// nonsense costs the caller the endpoint, not the render.
    #[test]
    fn a_nonsense_endpoint_degrades_to_a_ramp_rather_than_a_division() {
        for bad in [0.0f32, 0.3, -1.0, f32::NAN, f32::INFINITY] {
            for i in 0..=100 {
                let u = i as f32 / 100.0;
                let w = weight(DEFAULT_KNEE, bad, u);
                assert!((0.0..=1.0).contains(&w), "top {bad}, u {u}: weight {w}");
                if u <= DEFAULT_KNEE {
                    assert_eq!(w, 0.0, "top {bad}: the null broke at u {u}");
                }
            }
        }
    }

    /// The endpoint `Render::with_saturation` derives is the reciprocal of the
    /// `k0` inside `saturation_ceiling`, which is the whole reason it has to be
    /// passed separately: the ceiling is `k0 * wb * eg` and `k0` is not
    /// recoverable from that product.
    #[test]
    fn the_stated_endpoint_is_the_reciprocal_of_the_ceilings_k0() {
        let render = camera_to_srgb(A7C2_XYZ_TO_CAM).expect("invertible");
        for eg in [0.5f32, 1.0, 2.97] {
            let r = render.with_saturation(RIG, A7C2_WB, eg);
            let k0 = r.ceiling()[1] / eg; // green's gain is 1 by construction
            assert!(
                (r.top() - 1.0 / k0).abs() < 2e-6,
                "eg {eg}: top {} vs 1/k0 {}",
                r.top(),
                1.0 / k0
            );
            assert!(
                (r.top() - RIG_TOP).abs() < 2e-6,
                "the endpoint must not depend on the exposure gain: {}",
                r.top()
            );
        }
        // A caller that states only a ceiling gets the conservative endpoint.
        let bare = render.with_ceiling(saturation_ceiling(RIG, A7C2_WB, 1.0));
        assert_eq!(bare.top(), CONTAINER_TOP);
    }

    /// A blown neutral is already neutral, so the roll-off is a no-op on the
    /// output of `clip_highlights`. The two fixes compose without fighting.
    #[test]
    fn a_neutral_triple_is_a_fixed_point() {
        let (ceil, m) = rig();
        let k = ceil[0].min(ceil[1]).min(ceil[2]);
        for s in [0.5f32, 0.9, 1.0] {
            let v = [k * s, k * s, k * s];
            let out = desaturate_with(DEFAULT_KNEE, RIG_TOP, ceil, &m, v);
            for c in 0..3 {
                assert!(
                    (out[c] - v[c]).abs() < 1e-6,
                    "a neutral moved: {v:?} -> {out:?}"
                );
            }
        }
    }
}
