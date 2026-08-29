//! Optical-path profiles — lateral chromatic aberration as *data*.
//!
//! # Why this is not [`crate::profile`]
//!
//! [`profile`](crate::profile) is "the only place a per-body constant may
//! appear", and it means *body*: its constants are properties of the A7C II
//! sensor and survive any change of lens. **Nothing in this module is a property
//! of the sensor.** The coefficients here belong to a whole optical path —
//! body **plus lens plus teleconverter plus filter** — and they change when any
//! element of that path changes. Putting them in `profile` would quietly break
//! that module's contract, which is why they live here instead.
//!
//! The concrete case: [`A7C2_FE100GM_2XTC_X4CPL`] was measured through a **2x
//! Viltrox teleconverter**. Take the teleconverter off and these numbers are
//! wrong — not slightly, structurally, because a teleconverter magnifies the
//! prime's aberrations along with the image and contributes its own. Published
//! CA figures for the bare FE 100mm F2.8 Macro GM do not describe this path and
//! must not be substituted.
//!
//! # What lateral CA is, and why the fix is one scalar
//!
//! Red and blue are imaged at a slightly different magnification than green, so
//! a scene point lands at a slightly different radius in each channel. The
//! displacement grows linearly with distance from the optical centre and
//! vanishes at it. One coefficient per channel describes the whole field.
//!
//! `eps_R = -508.4 ppm` is the median of six per-stack fits measured by
//! BUILD-CROP on the six DELIVERED masters of the same six stacks blue was
//! fitted on: 514 gated tiles, mean per-stack `R^2 = 0.9080`, residual rms
//! **0.0651 sensel**, tile-permutation `p = 0.0005` (0/2000). Per-stack range
//! -449.0..-572.9 ppm; mean absolute leave-one-out error 71.7 ppm.
//!
//! ## SUPERSEDED -- DO NOT ADOPT: `eps_R = -704.5 ppm` (M107)
//!
//! The superseded value was a radial fit with `R^2 = 0.9969` over **20 gated
//! ROIs on two subjects**, permutation `p < 0.0005`, residual rms 0.073 sensel.
//! Its internal statistics are excellent and are not the problem; its *support*
//! is. It over-corrects, and the refutation is a direct measurement of the
//! shipped product rather than an argument about coefficients:
//!
//! * Applying -704.5 ppm leaves red displaced **outward** by +131.6..+255.5 ppm
//!   on **6 of 6** stacks (median +192), `R^2 = 0.81..0.97`. Red does not merely
//!   fall short of neutral, it **crosses past it** onto the same side as blue,
//!   and R and B landing on the same side of an edge is what makes the magenta
//!   rim visible at 1:1 in `dry-erase-marker-head-cpl`.
//! * Blue is the control, and it is a strong one: the identical estimator on the
//!   identical tiles of the identical masters leaves blue at **+18 ppm median,
//!   straddling zero** (-28.0..+48.9). A generic instrument gain error would
//!   move both channels. Blue was fitted on 1071 tiles over six stacks; red was
//!   fitted on 20 ROIs over two. The weaker-evidenced arm is the one that
//!   disagrees with the corpus.
//! * The applied 704.5 ppm sat **above the entire 500.9..651.9 ppm range** of
//!   the six per-stack measurements recorded a few lines below it.
//!
//! A DISAGREEMENT RECORDED AS OPEN, NOT RESOLVED. BUILD-CHROMA S15 argues the
//! per-stack values are attenuated by regression dilution and de-attenuates them
//! to -593.8..-700.7 (median -658.7), which would leave -704.5 nearly right.
//! That argument predicts the delivered masters carry a **-45.8 ppm inward**
//! residual; the measurement above finds **+131.6..+255.5 ppm outward on 6/6**,
//! which is where it fails. The likely reason is that S15's dose is planted by
//! cubic-spline resampling an already-demosaiced plane, adding a second
//! interpolation the real correction explicitly does not have (see "Why applying
//! it is free" below). Its defence -- "symmetric blur cannot move a correlation
//! peak" -- is sound for a correlation estimator but does not transfer to a
//! gradient-regression one, and its own stated criterion of recovery = 1.000 was
//! not met (0.692..0.938). Measured here: a synthetic plant reads back at 0.775
//! of nominal, while the SAME estimator reads the code's own +704.5 ppm dose at
//! **0.996** on a controlled single-frame pair.
//!
//! At the CFA half-diagonal of 2112.9 sensels the shipped coefficient is **1.074
//! sensels, or 2.148 output pixels**, of red-against-green misregistration
//! removed at the corner. The owner inspects at 100%.
//!
//! # Why applying it is free
//!
//! [`Similarity`] is `z -> a*z + b`, applied about a centre by
//! [`Similarity::apply_at`]. A radial magnification by `1 + eps` about a point
//! `c` is `z -> c + (1 + eps)(z - c)`, which **is itself a similarity**, and
//! similarities are closed under composition. So the correction folds into the
//! transform the gather already applies: [`OpticalProfile::compose`] returns
//! *one* `Similarity` that does alignment and CA correction together.
//!
//! This matters more than it looks. Every aligned pixel is already resampled, so
//! a correction that composes rides that existing interpolation at no cost. A
//! correction needing its own pass would apply a second interpolation kernel,
//! and a second kernel application costs real sharpness — enough that it could
//! plausibly cost more than the fringing it removes. **Composition avoids that
//! trade entirely rather than winning it.**
//!
//! # The second term is a translation, and it is not attributed
//!
//! The radial fit has three parameters, not one. Written out,
//! `d = eps*(r.n) - (eps*c).n` — the second term is a **constant vector**
//! projected on each edge normal, which is exactly a uniform translation of the
//! channel. "The optical centre is at `c`" and "red is translated by `-eps*c`"
//! are therefore *the same two parameters*, and no amount of care with this
//! parameterisation can separate them.
//!
//! That term is doing real work: forcing it to zero costs **5.37x** in residual
//! rms (0.0725 -> 0.3896 plane px) and biases `eps` by 14%, so it cannot simply
//! be dropped. But it must not be labelled optical either. Read as a decentring
//! it puts the optical axis **1077 px from the plane centre, 51% of the
//! half-diagonal**, which is not a plausible decentring for a real lens. Read as
//! a translation it is **(+0.629, -0.424) plane px** — and the red site sits half
//! a quad from the greens in each axis, so **CFA co-siting predicts ~0.5 px per
//! axis**, which is the same order.
//!
//! So [`OpticalProfile::translation`] is carried as its own named field rather
//! than hidden inside a centre, and it is documented as **unattributed**. The
//! radial coefficient is lateral CA; the translation may be lattice, may be
//! optical, and this instrument cannot say which.
//!
//! # How this module is wired
//!
//! [`OpticalProfile::compose`] folds the correction into the registration
//! similarity, so a corrected frame is resampled exactly once rather than
//! twice. It has two call sites in the shipping binary, both in warp
//! application: `align_cmd.rs:1929` in `warp_frame_in_place_plane` and
//! `align_cmd.rs:2095` in `warp_frame_in_place_fullres`. The correction is
//! therefore reachable only where a warp is applied, which is why the
//! `STREHL_ALIGN=0` byte-freeze row is invariant to it.
//!
//! It is **on by default for a capture whose gear matches a profile**, resolved
//! in one place by [`resolve_for_capture`], and off for everything else. A
//! capture the library does not recognise still gets [`None`], which is a
//! silent, exact no-op. `STREHL_FIX_CA=off` forces it off regardless.
//!
//! This heading read "This module is not wired to anything / Nothing calls it"
//! for some time after the wiring landed. It is corrected in place rather than
//! quietly deleted because a stale "nobody calls this" in this very file
//! already cost one investigation, and the second-cheapest way to prevent the
//! third is to leave the correction where the claim was.

use crate::align::{Cx, Similarity};

/// Which channel a correction is being computed for.
///
/// Green is the reference: the merge elects on green, so green defines the
/// geometry the other channels are corrected *to*. [`Channel::Green`] therefore
/// has no coefficient and is always an exact no-op.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Channel {
    Red,
    Green,
    Blue,
}

/// The evidence behind a fitted coefficient, carried with it.
///
/// A coefficient without its fit statistics is an assertion. Keeping these
/// beside the number means a consumer can see how well determined it is, and a
/// future profile measured badly cannot masquerade as this one.
#[derive(Debug, Clone, Copy, PartialEq)]
pub struct FitStats {
    /// Coefficient of determination of the radial fit.
    pub r_squared: f64,
    /// Permutation-test p-value. The parent milestone reports `p < 0.0005`,
    /// recorded here as its bound rather than as an exact value.
    pub permutation_p: f64,
    /// Residual rms of the fit, in sensels.
    pub residual_rms_sensel: f64,
    /// How many gated regions the fit was made over.
    pub n_regions: u32,
}

/// A lateral-CA profile for one complete optical path.
///
/// Coefficients are **scale minus one**, matching
/// [`SimilarityParams::g`](crate::align::SimilarityParams::g): `-704.5e-6` means
/// red is imaged 0.07% smaller than green, so correcting it magnifies red.
#[derive(Debug, Clone, Copy, PartialEq)]
pub struct OpticalProfile {
    /// Stable key for lookup.
    pub key: &'static str,
    /// The **entire** optical path. Every element affects the coefficients, so
    /// every element is named.
    pub optical_path: &'static str,
    /// Which stacks the coefficients were fitted from.
    pub measured_from: &'static str,
    /// Aperture and magnification at measurement time. Lateral CA varies with
    /// both, so a profile that does not record them cannot be checked for
    /// applicability. `None` means it was not recorded — which is itself
    /// information, and is not the same as "any".
    pub measured_at: Option<&'static str>,
    /// Schema version of this record.
    pub version: u32,
    /// The largest **normalised field height** the fit actually observed, where
    /// `1.0` is the corner (half the full-resolution sensel diagonal).
    ///
    /// Lateral CA is zero at the optical centre by construction and grows with
    /// field height, so a radial coefficient is most load-bearing exactly where
    /// a macro subject usually has nothing in frame. A high `r_squared` over a
    /// narrow radial band is entirely consistent with an unconstrained
    /// extrapolation into the corners, so goodness of fit does **not** answer
    /// the question this field answers.
    ///
    /// On the shipped record this is `Some(0.788)`: the 20 gated ROIs span
    /// `r = 0.208..0.788` with six of ten annuli populated, so the coefficient
    /// has a genuine 3.8x radial lever arm — but the corner is a **1.27x linear
    /// extrapolation** beyond the outermost measured point, and annuli
    /// `0.80..1.00` are empty. Roughly 21% of the corner correction comes from
    /// the model's shape rather than from measured points.
    ///
    /// `None` means the support was not recorded, which is not the same as
    /// "measured to the corner". Nothing in this module clamps to this radius —
    /// it is declared so a consumer can decide, not silently enforced, because
    /// a clamp is a behavioural change that has not been validated on a render.
    pub support_r_max: Option<f64>,
    /// Red's radial magnification error relative to green.
    pub eps_r: f64,
    /// Blue's radial magnification error relative to green.
    ///
    /// `None` means **never measured**, and is an exact no-op. It is not the
    /// same as `Some(0.0)`, which claims blue *was* measured and found
    /// uncorrected. That distinction is the whole reason this is an `Option`,
    /// and it is why blue shipped uncorrected for as long as it did: M107
    /// established red and left this `None`, correctly, and nothing afterwards
    /// noticed that "absent" had quietly become "fine".
    ///
    /// **Measured on the shipped record by BUILD-CHROMA** — see that field's
    /// value for provenance. Two caveats travel with it, and they are recorded
    /// here rather than in the report because this is where a future reader will
    /// be standing when they need them:
    ///
    /// 1. **Blue is the weaker arm.** Red's coefficient is stable to ~5 % across
    ///    the structure-gate ladder; blue's moves **26–85 %** over the same
    ///    ladder, and its per-stack fit `R²` runs 0.32–0.88 against red's
    ///    0.77–0.99. `174.4e-6` is not as solid a number as `-704.5e-6` and
    ///    should not be read as one.
    /// 2. **Blue's radial profile may not be a pure linear scale.** On
    ///    `coffee-bean` the de-translated per-annulus coefficient falls
    ///    monotonically from ~242 ppm at `r = 451` plane px to ~164 ppm at
    ///    `r = 1431`. A single `eps` fits a straight line through that, so it
    ///    over-corrects the inner field and under-corrects the outer. The
    ///    residual is still 6x smaller than doing nothing, which is why it
    ///    ships, but a second-order term is the obvious next measurement and
    ///    this field cannot express one.
    pub eps_b: Option<f64>,
    /// Uniform displacement of this channel relative to green, in plane px.
    ///
    /// **The cause of this term is not attributed.** It is mathematically
    /// degenerate with an optical-centre offset — they are the same two
    /// parameters — and its measured magnitude, `(+0.629, -0.424)` plane px, is
    /// the same order as the `~0.5` px per axis that CFA co-siting predicts
    /// between the red site and the greens. It may be lens decentring, it may be
    /// lattice, and M107's instrument cannot separate them.
    ///
    /// It is kept because dropping it costs 5.37x in fit residual, and named
    /// honestly because calling it an optical centre would assert an attribution
    /// that was never measured.
    pub translation: (f64, f64),
    /// Evidence for [`eps_r`](Self::eps_r).
    pub fit_r: FitStats,
    /// Evidence for [`eps_b`](Self::eps_b), or `None` when blue is unmeasured.
    ///
    /// Separate from [`fit_r`](Self::fit_r) rather than folded into it because
    /// the two coefficients on this record were measured by different
    /// milestones, on different corpora, to different standards. One `FitStats`
    /// covering both would average a strong arm with a weak one and report a
    /// confidence neither of them has.
    pub fit_b: Option<FitStats>,
    /// EXIF `Model` of the body this profile was measured on, compared
    /// **verbatim** by [`Self::matches_gear`].
    ///
    /// Stored as a plain `&str` rather than as a `strehl_raw::CaptureIdentity`
    /// because `strehl-raw` depends on `strehl-core` and not the reverse —
    /// naming that type here would invert the dependency. The bridge belongs in
    /// the CLI, which depends on both.
    pub body_model: &'static str,
    /// Sony `LensType3` of the **composed** optical path, per SYNTHESIS fact 26.
    ///
    /// `33094` is the corpus rig — `FE 100mm F2.8 Macro GM OSS + 2X
    /// Teleconverter`. The same lens **without** the teleconverter is `32893`,
    /// a different integer, which is precisely what makes the guard possible.
    ///
    /// Keyed on `LensType3` and not on `LensModel`: the latter is a display
    /// string, and fact 26 forbids `LensType` (reads 65535 on every corpus
    /// frame) and `LensType2` (reads 0 on 22 of 24).
    pub lens_type3: u16,
}

impl OpticalProfile {
    /// The coefficient for one channel, or `None` when there is nothing to
    /// apply.
    ///
    /// Green is always `None` by construction, and so is any channel whose
    /// coefficient was never measured.
    #[inline]
    pub fn eps(&self, ch: Channel) -> Option<f64> {
        match ch {
            Channel::Green => None,
            Channel::Red => Some(self.eps_r),
            Channel::Blue => self.eps_b,
        }
    }

    /// Fold the correction for `ch` into an alignment transform.
    ///
    /// Returns a single [`Similarity`] performing both, so the gather applies
    /// **one** interpolation, not two.
    ///
    /// # Order
    ///
    /// The alignment map takes an output point to a source point; the CA
    /// displacement is a property of where light landed on the *sensor*, so the
    /// radial rescale is applied in that source frame, after alignment. Applying
    /// it in the wrong frame would leave an error proportional to the alignment
    /// translation, which is not small.
    ///
    /// # Direction, and the coordinate frame it assumes
    ///
    /// **Every transform in this crate is a PULL** (`warpmap.rs:14-30`):
    /// `dst(p) = src(T(p))`, so `T` maps the pixel you *want* to the pixel you
    /// must *sample*. A channel imaged at magnification `(1 + eps)` records a
    /// scene point `u` at `(1 + eps) u`, so the pull must sample there:
    ///
    /// ```text
    /// s = 1 + eps          NOT 1 / (1 + eps)
    /// ```
    ///
    /// The measured displacement model is `observed = (1 + eps) * truth + t`
    /// (`e10_transfer.py::fit3` / `predict`), so the translation is **added
    /// after the scale**: composed with `q = a*z + b` this is `a' = s*a`,
    /// `b' = s*b + t`. Both closed forms, and a single similarity — the
    /// correction rides the gather's existing interpolation and adds no second
    /// resampling pass.
    ///
    /// **This function scales about the coordinate ORIGIN, not about the plane
    /// centre.** `z` must already be plane-centre-relative. Feeding it absolute
    /// warpmap coordinates would introduce a uniform red offset of order
    /// `eps * half_diagonal` ~ 1.5 sensels. Two live call sites satisfy that
    /// precondition today — `align_cmd.rs:1929` and `align_cmd.rs:2095`, which
    /// deinterleave the CFA into four half-resolution single-site planes and
    /// pass centre-relative coordinates. **Measured, not assumed:** the wiring
    /// was tested for exactly this bug in 2026-08 by predicting the 2.98 px
    /// uniform offset it would produce and looking for it; the measurement came
    /// back 0.24 px (ratio 0.081), refuting the hypothesis. See
    /// `experiments/BUILD-CROP/caorigin.py`.
    ///
    /// (This paragraph read "Nothing in this crate calls `compose` yet" until
    /// 2026-08-28, long after those two call sites landed. A reader took it at
    /// face value, inferred the precondition was therefore unenforced, and spent
    /// an investigation on a wiring bug that did not exist. A stale "nobody
    /// calls this" is more expensive than no comment at all.)
    ///
    /// An earlier version of this doc comment specified `q' = (q - t) / (1 +
    /// eps)` with `s = 1/(1 + eps)`. That was the inverted convention, and the
    /// code implemented it: measured on a real render it made the aberration
    /// **7.2 % worse**. It is kept named here because `cargo doc` is how the
    /// next agent will learn this function.
    ///
    /// With no profile, or a channel with no coefficient, or a profile whose
    /// terms are all zero, the input is returned **bit-for-bit unchanged** — the
    /// early return exists so that the no-op case cannot be perturbed by
    /// floating-point arithmetic that is algebraically the identity but not
    /// bitwise so.
    #[inline]
    pub fn compose(profile: Option<&OpticalProfile>, ch: Channel, t: Similarity) -> Similarity {
        let Some(p) = profile else { return t };
        let Some(eps) = p.eps(ch) else { return t };
        let (tx, ty) = p.translation;
        if eps == 0.0 && tx == 0.0 && ty == 0.0 {
            return t;
        }
        // THE DIRECTION, AND WHY IT IS WRITTEN OUT.
        //
        // `warpmap` documents its transforms as **pulls**: a destination
        // coordinate maps to a source coordinate, `dst(p) = src(T(p))`, with no
        // inversion anywhere. That module also warns that inverting is the most
        // likely bug in a consumer of it, and that it is silent. It was.
        //
        // A channel imaged at magnification (1 + eps) records the scene point u
        // at x = (1 + eps) * u, i.e. `src(x) = scene(x / (1 + eps))`. Wanting
        // `dst(p) = scene(p)` forces `T(p) / (1 + eps) = p`, so
        //
        //     s = 1 + eps
        //
        // NOT 1 / (1 + eps). This shipped inverted, and applying it to a real
        // render made the measured aberration 7.2% WORSE while the corrected
        // direction removed 94.3% of it (M107b P5). Every unit test here passed
        // both ways, because round-trip, composition and no-op are all
        // sign-symmetric; see `a_planted_magnification_is_actually_undone`,
        // which is the test that can tell the two apart.
        let s = 1.0 + eps;
        // Real scalar times complex, written out rather than via Cx::mul, so no
        // cross term multiplies a zero into a signed zero.
        //
        // The translation is ADDED after the scale, not subtracted before it,
        // because the measured model is `observed = (1 + eps) * truth + t` and
        // the pull must land on `observed`. Composing with an alignment `a z + b`
        // gives `s*a*z + (s*b + t)` — still a Similarity, so L6 is unaffected.
        Similarity {
            a: Cx::new(t.a.re * s, t.a.im * s),
            b: Cx::new(t.b.re * s + tx, t.b.im * s + ty),
        }
    }

    /// Radial displacement, in plane px, that this channel suffers at `radius`.
    ///
    /// The quantity the correction removes, for reporting and for tests.
    #[inline]
    pub fn displacement_at(&self, ch: Channel, radius: f64) -> f64 {
        self.eps(ch).map_or(0.0, |e| e * radius)
    }
}

/// The owner's macro path, and the first concrete citizen of the pluggable-optics
/// requirement.
///
/// **Every element named here affects the coefficient.** In particular the 2x
/// teleconverter: remove it and this record does not describe the path.
pub const A7C2_FE100GM_2XTC_X4CPL: OpticalProfile = OpticalProfile {
    key: "a7c2-fe100gm-2xtc-x4cpl",
    optical_path: "Sony A7C II + FE 100mm F2.8 Macro GM + 2x Viltrox teleconverter \
                   + Breakthrough X4 circular polariser",
    measured_from: "M107 Instrument A: 20 gated ROIs over tweezers-cpl and bee-3-cpl (red); \
                    BUILD-CHROMA: 1071 gated tiles over six stacks (blue)",
    // RECORDED by BUILD-CHROMA (Item 3), where this was `None`. The apertures
    // are read from the ARWs of the six stacks the blue arm was fitted on:
    // five at f/5.6, one (coffee-bean) at f/8, all at 200 mm effective.
    //
    // **The guard deliberately does NOT gate on this**, and the reason is
    // measured rather than assumed. Lateral CA does vary with aperture in
    // general, which is what the previous comment here warned about. But in the
    // only aperture comparison this corpus can make, it does not vary enough to
    // matter: the two largest per-stack eps_r are 651.9 ppm (couch-fibers-cpl,
    // f/5.6) and 650.7 ppm (coffee-bean, f/8) -- **1.2 ppm apart, 0.2 %, across
    // a full stop** -- while the spread among the five stacks that share f/5.6
    // is 500.9..651.9 ppm, or 151 ppm. Subject-to-subject variation dwarfs the
    // aperture term by two orders of magnitude, so declining on aperture would
    // switch off a correction that measurably works, for a difference this
    // corpus cannot even detect.
    //
    // LIMITATION, and it is the same shape as the guard's: n = 1 at f/8 and
    // **nothing at f/11**, which `docs/captures-needed.md` lists as a gap. This
    // records what was measured; it is not a licence for every aperture.
    measured_at: Some("f/5.6 (5 stacks) and f/8 (1 stack), 200 mm effective; f/11 untested"),
    version: 1,
    // RETAINED CONSERVATIVELY at the superseded fit's support. The M107 fit this
    // described spanned r = 0.208..0.788 over 20 gated ROIs, six of ten annuli
    // populated, outer two empty, corner a 1.27x linear extrapolation.
    //
    // The BUILD-CROP fit that now sets `eps_r` reaches further -- its 512 px tile
    // grid tops out at r/corner = 0.916 -- but which annuli are actually
    // populated depends on each stack's gradient gating and was NOT verified
    // per-annulus. Over-declaring support is the failure this field exists to
    // prevent, so the smaller number stands until someone measures the larger.
    // Declared, not enforced.
    support_r_max: Some(0.788),
    // Measured by BUILD-CROP on the six DELIVERED masters of the six stacks
    // blue was fitted on (tweezers-cpl, bee-3-cpl, coffee-bean, lavendar-cpl,
    // couch-fibers-cpl, bee-2-cpl): the median of six per-stack fits, 514 gated
    // tiles, per-stack range -449.0..-572.9 ppm, mean |LOO error| 71.7 ppm.
    //
    // SUPERSEDED -- DO NOT ADOPT: -704.5e-6, the M107 20-ROI fit. It leaves red
    // displaced OUTWARD on 6 of 6 stacks (+131.6..+255.5 ppm, median +192),
    // i.e. past neutral and onto blue's side, which is the magenta rim visible
    // at 1:1 in dry-erase-marker-head-cpl. Blue, measured by the same estimator
    // on the same tiles, straddles zero at +18 ppm median. See the module docs
    // for the full refutation and for the BUILD-CHROMA S15 disagreement, which
    // is recorded as OPEN.
    //
    // METHOD, and it needs no CA-off renders: every delivered master already
    // carries a known exactly-applied dose -- the shipping correction itself --
    // so native = measured_residual - applied_push. The fit is magnification AND
    // uniform translation JOINTLY; fitting a radial slope through the origin
    // conflates the two and inflated this coefficient by 32% in an earlier pass
    // of this same work.
    //
    // STATED UNCERTAINTY: on the one subject where both routes were run, the
    // residual route reads -501.2 ppm and a direct fit to a CA-off render reads
    // -583.5 ppm, an 82.3 ppm discrepancy that is NOT resolved. -508.4 is better
    // than -704.5 under either route, and worse than it only under S15's
    // de-attenuated hypothesis, which the 6/6 outward residual refutes.
    eps_r: -508.4e-6,
    // MEASURED, where this was `None` until BUILD-CHROMA.
    //
    // +174.4 ppm: the leave-one-out median of six de-attenuated per-stack
    // measurements. Per-stack range 101.3-222.7 ppm. Against the 0.363 plane px
    // of blue displacement the corner carries today, the LOO median leaves
    // **0.059 px** -- an 84 % reduction, and it is a leave-one-out figure, so no
    // stack is scored against a coefficient its own data set.
    //
    // The sign opposes red's, and that was not imposed: the two channels were
    // fitted independently against green, and blue coming out positive while red
    // is negative is what lateral CA looks like when the two flank green in the
    // dispersion curve. A sign error in either arm would have broken that.
    //
    // Read the field docs before trusting this to the same precision as eps_r.
    // It is the weaker arm and it may want a second-order term.
    eps_b: Some(174.4e-6),
    // Unattributed: degenerate with an optical-centre offset, and the same order
    // as the ~0.5 px/axis that CFA co-siting predicts. See the field docs.
    translation: (0.6294, -0.4240),
    // Red's evidence, RE-MEASURED by BUILD-CROP together with `eps_r`. Both arms
    // now count gated tiles in `n_regions`, so red's 514 and blue's 1071 are
    // finally the same kind of number -- unlike the superseded record, where
    // red's 20 counted M107 ROIs and the two were not comparable as sample
    // sizes. `r_squared` is the mean of the six per-stack joint fits (range
    // 0.810-0.966); `permutation_p` is the pooled tile-permutation null, 0 of
    // 2000 shuffles reaching the observed magnification.
    fit_r: FitStats {
        r_squared: 0.9080,
        permutation_p: 0.0005,
        residual_rms_sensel: 0.0651,
        n_regions: 514,
    },
    // Blue's evidence, kept separate from red's because it is weaker and saying
    // so is the point. `n_regions` counts gated tiles, not M107 ROIs, so the two
    // counts are not comparable as sample sizes -- they are different
    // instruments. `r_squared` is the mean of the six per-stack radial fits
    // (range 0.32-0.88); `permutation_p` is from the pooled tile-permutation
    // null, which is the same null red's was scored against.
    fit_b: Some(FitStats {
        r_squared: 0.579,
        permutation_p: 0.0005,
        residual_rms_sensel: 0.152,
        n_regions: 1071,
    }),
    // The gear this profile describes, and the two fields the guard compares.
    // 33094 is the composed path WITH the 2x teleconverter; the bare lens is
    // 32893 and must not match.
    body_model: "ILCE-7CM2",
    lens_type3: 33094,
};

const PROFILES: [&OpticalProfile; 1] = [&A7C2_FE100GM_2XTC_X4CPL];

/// Which colour a CFA site carries, for an **RGGB** mosaic.
///
/// This exists so that the wiring patch in the gather loop is one line with no
/// arithmetic in it. `warp_frame_in_place` deinterleaves the mosaic as
/// `for dy in 0..2 { for dx in 0..2 { ... } }`, so `(dx, dy)` names the site:
///
/// ```text
/// (0,0) R     (1,0) G1
/// (0,1) G2    (1,1) B
/// ```
///
/// Both greens map to [`Channel::Green`], which has no coefficient by
/// construction, so both green gathers stay **bitwise identical** to today
/// (bar L1).
///
/// **This used to say only red moves.** That was true while `eps_b` was `None`.
/// BUILD-CHROMA measured blue, so the blast radius is now **two of four
/// gathers** — red and blue — and the greens remain bitwise frozen. The
/// green freeze is the invariant that actually matters here, because green is
/// the channel the focus measure and the election are computed on.
pub fn cfa_site_channel(dx: usize, dy: usize) -> Channel {
    match (dx, dy) {
        (0, 0) => Channel::Red,
        (1, 1) => Channel::Blue,
        _ => Channel::Green,
    }
}

/// Look up a profile by key. Absence is legal and means "apply nothing".
pub fn by_key(key: &str) -> Option<&'static OpticalProfile> {
    PROFILES.iter().copied().find(|p| p.key == key)
}

/// The same optical path with the **translation term zeroed**, which is the form
/// that should actually be applied.
///
/// Measured on `bee-3-cpl`: the radial term alone removes **99.6 %** of the
/// render-domain radial R−G slope (141.1 → 0.6 ppm), while adding the fitted
/// translation leaves **17.3 ppm** — 12x the residual. The translation is also
/// structurally unattributed: it is degenerate with an optical-centre offset and
/// is the same order as the ~0.5 px/axis CFA co-siting predicts.
///
/// So it is **recorded** in [`A7C2_FE100GM_2XTC_X4CPL`] as provenance and
/// **not applied** here. `the_two_profiles_differ_only_in_translation` pins the
/// pair so they cannot drift apart.
pub const A7C2_FE100GM_2XTC_X4CPL_RADIAL: OpticalProfile = OpticalProfile {
    translation: (0.0, 0.0),
    ..A7C2_FE100GM_2XTC_X4CPL
};

/// The environment variable that selects a lateral-CA profile.
///
/// Named here so the string lives in exactly one place: a switch whose name is
/// spelled independently in the code and in a harness's argv is a switch that
/// will eventually be set and not read, which is the failure this whole module
/// was already guilty of once (fact 1449 — 287 passing tests and zero
/// consumers).
pub const CA_ENV: &str = "STREHL_FIX_CA";

/// Why a CA profile was refused. Refusing loudly is the point: silently applying
/// the wrong optical profile is worse than applying none.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum CaConfigError {
    /// The operator named a profile that does not exist — most likely a typo.
    /// Treated as an error rather than as absence, because a typo that silently
    /// disables the correction looks exactly like the correction not working.
    UnknownProfile { key: String },
}

impl core::fmt::Display for CaConfigError {
    fn fmt(&self, f: &mut core::fmt::Formatter<'_>) -> core::fmt::Result {
        match self {
            CaConfigError::UnknownProfile { key } => {
                write!(f, "unknown lateral-CA profile {key:?}; known profiles: ")?;
                for (i, p) in PROFILES.iter().enumerate() {
                    if i > 0 {
                        write!(f, ", ")?;
                    }
                    write!(f, "{}", p.key)?;
                }
                Ok(())
            }
        }
    }
}

impl std::error::Error for CaConfigError {}

/// Resolve the lateral-CA profile from the `STREHL_FIX_CA` setting.
///
/// **This is the operator override.** The default-on path is
/// [`default_profile_for_gear`]; this function is what `STREHL_FIX_CA` reaches.
///
/// ## Correction: the 54.1 % transfer figure is not reproduced
///
/// This doc used to read *"Off by default, and it must stay that way"*, on this
/// evidence: the out-of-sample transfer arm (L4) **split** — a profile fitted on
/// `tweezers-cpl` recovered 95.0 % of the in-sample reduction on `bee-3-cpl`,
/// but the reverse direction recovered only **54.1 %** against a registered 60 %
/// bar. That asymmetry was the whole case for default-off.
///
/// **BUILD-CHROMA does not reproduce it.** Running leave-one-out transfer over
/// six stacks with 1071 gated tiles, the two directions recover **93.7 %** and
/// **93.3 %** — symmetric, and both far above the 60 % bar. The measured corner
/// residual left by the shipped red coefficient is **0.071 plane px** against
/// **1.519 px** uncorrected.
///
/// The old number is **stated, not deleted**. Two instruments disagree: M107 had
/// 8 ROIs per side, BUILD-CHROMA has ~180 tiles per stack, and the more likely
/// reading is that 54.1 % was small-sample scatter rather than real asymmetry —
/// but that is an inference, not a measurement, and nobody has re-run M107's
/// instrument to settle it. Treat 54.1 % as **unreproduced**, not as refuted.
///
/// Fact 52 still stands as written: a scalar fitted on one scene should not be
/// transferred blind. What changed is that the scalar is no longer fitted on one
/// scene, and that the thing it is now keyed to is the **gear**, not the scene.
///
/// ## Correction: the teleconverter *can* be detected from the frames
///
/// **The value must NAME the optical path**, not merely be truthy — that part is
/// unchanged and still right for this function. The shipped profile includes a
/// **2x teleconverter**; take it off and the coefficient does not describe the
/// path.
///
/// But this doc also used to assert *"There is no way to detect that from the
/// frames."* **That is false.** The ARW records it twice over:
/// `LensModel` reads `FE 100mm F2.8 Macro GM OSS + 2X Teleconverter` in plain
/// text, and Sony's `LensType3` reads **33094** for the composed path against
/// **32893** for the bare lens. `strehl_raw::identity` already parses both.
/// Detection was available the whole time this file said it was not, which is
/// why [`default_profile_for_gear`] can exist at all.
///
/// ```text
/// STREHL_FIX_CA unset / "" / "0"        -> Ok(None)      silent no-op
/// STREHL_FIX_CA "a7c2-fe100gm-2xtc-x4cpl" -> Ok(Some(..)) radial term only
/// STREHL_FIX_CA "1" / "true" / "on"     -> Err(..)       refuses to guess
/// STREHL_FIX_CA "typo"                  -> Err(..)       refuses silently-off
/// ```
///
/// `1`/`true`/`on` are rejected deliberately. They are the natural thing to type
/// and they are exactly the request this function cannot honour, because "yes,
/// correct CA" does not say *which lens*.
///
/// Takes the value as an argument rather than reading the environment, so it is
/// testable without mutating global process state from parallel test threads.
pub fn profile_from_setting(
    value: Option<&str>,
) -> Result<Option<&'static OpticalProfile>, CaConfigError> {
    let raw = match value {
        None => return Ok(None),
        Some(v) => v.trim(),
    };
    if raw.is_empty() || raw == "0" || raw.eq_ignore_ascii_case("off") || raw.eq_ignore_ascii_case("false") {
        return Ok(None);
    }
    // The radial-only forms are what get applied; see the const's docs.
    if raw == A7C2_FE100GM_2XTC_X4CPL.key {
        return Ok(Some(&A7C2_FE100GM_2XTC_X4CPL_RADIAL));
    }
    Err(CaConfigError::UnknownProfile { key: raw.to_string() })
}

/// [`profile_from_setting`] applied to [`CA_ENV`] in the process environment.
///
/// This is the entry point the render path calls. It is deliberately a plain
/// function rather than a cached `OnceLock`: the cost is one `getenv` and one
/// string compare per frame, which is nothing next to a four-plane gather, and
/// a cache here would make the switch un-testable within a process and would
/// silently ignore an environment change between stacks.
///
/// An unreadable/typo'd value is an `Err`, not a `None`. A typo that silently
/// disables the correction is indistinguishable from the correction not
/// working, which is the exact failure mode this whole milestone is trying to
/// escape.
pub fn active_profile() -> Result<Option<&'static OpticalProfile>, CaConfigError> {
    profile_from_setting(std::env::var(CA_ENV).ok().as_deref())
}

/// The form of a profile that is actually **applied**: translation zeroed.
///
/// The recorded const keeps the fitted translation as provenance; the radial
/// twin is what touches a render. See [`A7C2_FE100GM_2XTC_X4CPL_RADIAL`].
fn applied_form(recorded: &'static OpticalProfile) -> &'static OpticalProfile {
    if recorded.key == A7C2_FE100GM_2XTC_X4CPL.key {
        return &A7C2_FE100GM_2XTC_X4CPL_RADIAL;
    }
    // A profile with no registered radial-only twin. Unreachable today, and
    // `every_profile_has_a_radial_form` exists to keep it that way: if that test
    // fails, this line applies an unattributed translation to a real render.
    recorded
}

/// Does a capture's gear match a profile's gear? **Three-valued on purpose.**
///
/// The middle case is the important one. `Unknown` means *not enough evidence to
/// say*, and it must never be collapsed into `Match`: treating an unidentifiable
/// file as a match applies one photographer's measured aberration to someone
/// else's glass at full strength. Collapsing it into `Mismatch` merely declines
/// to help, which is the safe direction and the one taken here.
///
/// This mirrors `strehl_raw::CaptureIdentity::same_gear_as`, which is
/// three-valued for the same reason and compares the same two fields.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum GearMatch {
    /// Body and composed lens id both match. Safe to apply.
    Match,
    /// At least one field is present and differs. Do not apply.
    Mismatch,
    /// A field the decision needs is absent. Do not apply, and say why.
    Unknown,
}

impl OpticalProfile {
    /// Whether this profile describes the gear that took a given frame.
    ///
    /// Compares exactly two fields, both stable across a stack and a session:
    /// [`body_model`](Self::body_model) verbatim, and
    /// [`lens_type3`](Self::lens_type3) as an integer (SYNTHESIS fact 26).
    ///
    /// Deliberately does **not** consult `LensModel` (a display string),
    /// `FNumber` or `FocalLength`: identical gear spans f/5.6–f/11 in this
    /// corpus, so a per-shot field would decline valid frames.
    ///
    /// Note that this cannot see everything that matters. The profile's path
    /// also names a **Breakthrough X4 circular polariser**, and a filter in
    /// front of the lens is invisible to EXIF and always will be. The guard
    /// therefore bounds the risk, it does not eliminate it: it can tell a
    /// different lens from this one, and it cannot tell a filter change.
    pub fn matches_gear(&self, body_model: Option<&str>, lens_type3: Option<u16>) -> GearMatch {
        let (Some(model), Some(lens)) = (body_model, lens_type3) else {
            return GearMatch::Unknown;
        };
        if model == self.body_model && lens == self.lens_type3 {
            GearMatch::Match
        } else {
            GearMatch::Mismatch
        }
    }
}

/// Why the CA path reached the decision it reached.
///
/// Exists so a status line can be **derived from the decision** instead of
/// reconstructed from the switch. Reconstruction is the bug class: before the
/// default-on flip, the environment variable and the behaviour were the same
/// thing, so reading the variable was correct; the flip decoupled them and every
/// consumer still reading the variable silently began lying. V-CA found one such
/// consumer printing `CORRECTING` for an uncorrected render and `off` for a
/// corrected one — wrong in **both** directions, on the one switch the flip
/// makes load-bearing.
///
/// The fix is not to invert a second reconstruction. It is to make the reason a
/// **return value of the resolution itself**, so that a caller cannot obtain the
/// explanation without obtaining the decision it explains.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum CaReason {
    /// The operator refused the correction explicitly.
    OperatorOff {
        /// What they actually typed, echoed so a surprising spelling is visible.
        setting: String,
    },
    /// The operator named a profile, which outranks the guard.
    OperatorNamed { setting: String },
    /// Nobody spoke and the guard recognised the gear. **The default-on case.**
    GearMatched { body: String, lens_type3: u16 },
    /// Nobody spoke and the guard declined. Carries what it declined **on**.
    GearDeclined {
        body: Option<String>,
        lens_type3: Option<u16>,
    },
}

/// A resolved CA decision: the profile the pixels will use, and why.
///
/// The two fields are produced together by [`resolve_for_capture`] and must be
/// consumed together. `Display` renders the prologue line.
#[derive(Debug, Clone, PartialEq)]
pub struct CaDecision {
    /// Exactly what the gather will apply. `None` means no correction.
    pub profile: Option<&'static OpticalProfile>,
    /// Why [`profile`](Self::profile) is what it is.
    pub reason: CaReason,
}

impl CaDecision {
    /// Is the render correcting? Reads [`profile`](Self::profile), never the
    /// reason, so the two cannot disagree about the headline state.
    #[inline]
    pub fn is_correcting(&self) -> bool {
        self.profile.is_some()
    }
}

impl core::fmt::Display for CaDecision {
    fn fmt(&self, f: &mut core::fmt::Formatter<'_>) -> core::fmt::Result {
        // The CORRECTING/off word is taken from `self.profile` -- the same value
        // the gather uses -- and never from the reason. A reason that somehow
        // disagreed would produce a visibly odd line rather than a confident
        // wrong one.
        match (&self.profile, &self.reason) {
            (Some(p), CaReason::OperatorNamed { setting }) => write!(
                f,
                "CORRECTING, profile {:?} (operator asked for {setting:?})",
                p.key
            ),
            (Some(p), CaReason::GearMatched { body, lens_type3 }) => write!(
                f,
                "CORRECTING, profile {:?} (gear matched {body:?} / lens {lens_type3}; default on)",
                p.key
            ),
            (None, CaReason::OperatorOff { setting }) => {
                write!(f, "off (operator asked for {setting:?})")
            }
            (None, CaReason::GearDeclined { body, lens_type3 }) => match (body, lens_type3) {
                // Named a body and a lens, neither matched a profile. The
                // operator needs to see WHICH gear was rejected.
                (Some(b), Some(l)) => write!(
                    f,
                    "off (no profile for body {b:?} / lens {l}; correction is gear-guarded)"
                ),
                // Identity unreadable. A different problem with a different fix,
                // so it gets a different sentence.
                _ => write!(
                    f,
                    "off (capture identity unreadable: body {} / lens {}; \
                     name a profile with {CA_ENV} to override)",
                    body.as_deref().unwrap_or("?"),
                    lens_type3.map_or("?".to_string(), |l| l.to_string()),
                ),
            },
            // Structurally unreachable: every arm above pairs a profile state
            // with the reason that produced it. Printed rather than panicked
            // because a prologue must never take down a render.
            (p, r) => write!(
                f,
                "INCONSISTENT (profile {:?}, reason {r:?}) -- please report",
                p.map(|x| x.key)
            ),
        }
    }
}

/// Resolve the CA decision **and its explanation** in one pass.
///
/// This is the single source of truth. [`profile_for_capture`] is a thin
/// projection of it, so the profile a status line reports and the profile the
/// gather applies are not merely equal by inspection — they are the same value.
///
/// See [`profile_for_capture`] for the truth table and for why default-on is
/// defensible; this function adds only the reason.
pub fn resolve_for_capture(
    setting: Option<&str>,
    body_model: Option<&str>,
    lens_type3: Option<u16>,
) -> Result<CaDecision, CaConfigError> {
    if let Some(raw) = setting.filter(|s| !s.trim().is_empty()) {
        let trimmed = raw.trim().to_string();
        // `profile_from_setting` owns the off-words and the typo error; this
        // must not re-implement either, or the two spellings of "off" drift.
        return Ok(match profile_from_setting(Some(raw))? {
            Some(p) => CaDecision {
                profile: Some(p),
                reason: CaReason::OperatorNamed { setting: trimmed },
            },
            None => CaDecision {
                profile: None,
                reason: CaReason::OperatorOff { setting: trimmed },
            },
        });
    }
    Ok(
        match PROFILES
            .iter()
            .copied()
            .find(|p| p.matches_gear(body_model, lens_type3) == GearMatch::Match)
        {
            Some(p) => CaDecision {
                profile: Some(applied_form(p)),
                // Unwraps are sound: `matches_gear` returns `Match` only when
                // both fields are `Some`.
                reason: CaReason::GearMatched {
                    body: body_model.expect("Match implies a body").to_string(),
                    lens_type3: lens_type3.expect("Match implies a lens"),
                },
            },
            None => CaDecision {
                profile: None,
                reason: CaReason::GearDeclined {
                    body: body_model.map(str::to_string),
                    lens_type3,
                },
            },
        },
    )
}

/// [`resolve_for_capture`] with the setting read from [`CA_ENV`].
///
/// What a prologue should call. Pair it with [`profile_for_capture_env`] on the
/// same frame and the two agree by construction.
pub fn resolve_for_capture_env(
    body_model: Option<&str>,
    lens_type3: Option<u16>,
) -> Result<CaDecision, CaConfigError> {
    resolve_for_capture(
        std::env::var(CA_ENV).ok().as_deref(),
        body_model,
        lens_type3,
    )
}

/// Resolve the profile for a capture, **default-on when the gear is recognised**.
///
/// This is the function the render path should call. It supersedes
/// [`active_profile`] for any caller that can supply an identity, and it is the
/// whole of the default-on change:
///
/// ```text
/// operator set STREHL_FIX_CA   -> the operator's word, in BOTH directions
/// unset, gear matches a profile -> Ok(Some(..))   the default-on case
/// unset, gear known but different -> Ok(None)     declines
/// unset, gear unreadable        -> Ok(None)       declines
/// ```
///
/// **The operator can still turn it off**, and that is not incidental. Under
/// default-off, `STREHL_FIX_CA=off` was indistinguishable from doing nothing;
/// under default-on it is the only way to get an uncorrected render, so it has
/// to keep working. `profile_from_setting` already treats `off`/`0`/`false` as
/// `Ok(None)`, and routing through it here means the operator's explicit refusal
/// beats the gear match.
///
/// ## Why default-on is defensible now, when it was not before
///
/// The objection recorded on [`profile_from_setting`] was transfer: a
/// coefficient fitted on one scene might not describe another. That objection is
/// answered not by measuring per-bracket — BUILD-CHROMA built that instrument
/// and it was **3.6x worse** than the fixed profile — but by observing that
/// lateral CA is a property of the **glass**, and that the glass is recorded in
/// the file. A profile keyed to gear is not a scalar transferred across scenes;
/// it is a constant applied to the instrument it was measured on.
///
/// ## The limitation, stated because it is real
///
/// **This guard has never declined a real file.** All 26 corpus stacks are the
/// same body, same lens, same teleconverter, so the negative path has no natural
/// test case and the guard is correct **by construction, not by experiment**. A
/// guard that has only ever said yes is a guard that has not been tested where it
/// matters.
///
/// The synthetic negatives below (`the_guard_declines_the_bare_lens`,
/// `the_guard_declines_an_unreadable_file`, `the_guard_declines_a_different_body`)
/// exercise the matcher directly and are cheap and real as far as they go — the
/// matcher takes plain scalars precisely so a negative needs no fabricated EXIF
/// bytes. What they cannot exercise is the *parse*: whether a genuine non-TC ARW
/// yields `lens_type3 == Some(32893)` rather than `None`. `strehl_raw::identity`
/// has its own synthetic bare-lens fixture for that, but no real file has ever
/// been through the whole path.
///
/// **Ask on the capture list: a short bracket shot without the teleconverter.**
/// It would exercise the negative path end to end and give the corpus its first
/// non-TC optical sample.
pub fn profile_for_capture(
    setting: Option<&str>,
    body_model: Option<&str>,
    lens_type3: Option<u16>,
) -> Result<Option<&'static OpticalProfile>, CaConfigError> {
    // A PROJECTION of `resolve_for_capture`, not a second implementation. The
    // status line and the gather therefore read the same value rather than two
    // values that happen to agree -- which is exactly the property that was
    // missing when the prologue reconstructed its state from the environment.
    Ok(resolve_for_capture(setting, body_model, lens_type3)?.profile)
}

/// [`profile_for_capture`] with the setting read from [`CA_ENV`].
///
/// The entry point for the render path. Like [`active_profile`] it re-reads the
/// environment per call rather than caching, so a harness can change the switch
/// between stacks within one process.
pub fn profile_for_capture_env(
    body_model: Option<&str>,
    lens_type3: Option<u16>,
) -> Result<Option<&'static OpticalProfile>, CaConfigError> {
    profile_for_capture(
        std::env::var(CA_ENV).ok().as_deref(),
        body_model,
        lens_type3,
    )
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::align::SimilarityParams;

    /// Deterministic scalar PRNG, so a failure is reproducible from the seed
    /// alone.
    struct Rng(u64);

    impl Rng {
        fn next_u64(&mut self) -> u64 {
            // SplitMix64.
            self.0 = self.0.wrapping_add(0x9E37_79B9_7F4A_7C15);
            let mut z = self.0;
            z = (z ^ (z >> 30)).wrapping_mul(0xBF58_476D_1CE4_E5B9);
            z = (z ^ (z >> 27)).wrapping_mul(0x94D0_49BB_1331_11EB);
            z ^ (z >> 31)
        }

        /// Uniform in `[-1, 1)`.
        fn signed(&mut self) -> f64 {
            (self.next_u64() as f64 / u64::MAX as f64) * 2.0 - 1.0
        }
    }

    fn bits(t: Similarity) -> [u64; 4] {
        [
            t.a.re.to_bits(),
            t.a.im.to_bits(),
            t.b.re.to_bits(),
            t.b.im.to_bits(),
        ]
    }

    fn zero_profile() -> OpticalProfile {
        OpticalProfile {
            eps_r: 0.0,
            eps_b: Some(0.0),
            translation: (0.0, 0.0),
            ..A7C2_FE100GM_2XTC_X4CPL
        }
    }

    /// **Bar L1.** A zero coefficient must be a *bitwise* no-op, not merely an
    /// equal one.
    ///
    /// Scored on `to_bits`, deliberately. `==` cannot distinguish `+0.0` from
    /// `-0.0`, so a bar written with `==` would pass on a transform whose signed
    /// zeros had been flipped by arithmetic that is algebraically the identity.
    /// The frozen linear path is a byte freeze; "equal" is not the standard it
    /// is held to.
    #[test]
    fn l1_zero_correction_is_bitwise_identity() {
        let zero = zero_profile();
        let mut rng = Rng(0x5EED_1107);
        let mut n = 0usize;

        // Adversarial cases first: signed zeros, subnormals, and extreme scales
        // are where "algebraically the identity" stops being bitwise so.
        let nasty = [
            Similarity::IDENTITY,
            Similarity {
                a: Cx::new(-0.0, -0.0),
                b: Cx::new(-0.0, 0.0),
            },
            Similarity {
                a: Cx::new(f64::MIN_POSITIVE / 4.0, -f64::MIN_POSITIVE / 3.0),
                b: Cx::new(-0.0, f64::MIN_POSITIVE),
            },
            Similarity {
                a: Cx::new(1.0e300, -1.0e300),
                b: Cx::new(1.0e-300, -1.0e-300),
            },
        ];

        for t in nasty {
            for ch in [Channel::Red, Channel::Green, Channel::Blue] {
                assert_eq!(
                    bits(OpticalProfile::compose(Some(&zero), ch, t)),
                    bits(t),
                    "zero correction perturbed bits of {t:?} on {ch:?}"
                );
                // Absence must be a no-op on the same standard.
                assert_eq!(bits(OpticalProfile::compose(None, ch, t)), bits(t));
                n += 1;
            }
        }

        for _ in 0..4000 {
            let t = Similarity::from_params(SimilarityParams {
                ax: rng.signed() * 500.0,
                ay: rng.signed() * 500.0,
                g: rng.signed() * 0.2,
                rot: rng.signed() * 0.05,
            });
            for ch in [Channel::Red, Channel::Green, Channel::Blue] {
                assert_eq!(
                    bits(OpticalProfile::compose(Some(&zero), ch, t)),
                    bits(t),
                    "zero correction perturbed bits of {t:?} on {ch:?}"
                );
                assert_eq!(bits(OpticalProfile::compose(None, ch, t)), bits(t));
                n += 1;
            }
        }

        assert!(n >= 10_000, "L1 registered >= 10000 cases, ran {n}");
    }

    /// Green has no coefficient, so the shipped profile must not move it either
    /// — **bar L5** at the unit level.
    #[test]
    fn l5_green_is_never_touched() {
        let p = &A7C2_FE100GM_2XTC_X4CPL;
        let mut rng = Rng(0x600D_5EED_1107);
        for _ in 0..2000 {
            let t = Similarity::from_params(SimilarityParams {
                ax: rng.signed() * 500.0,
                ay: rng.signed() * 500.0,
                g: rng.signed() * 0.2,
                rot: rng.signed() * 0.05,
            });
            assert_eq!(
                bits(OpticalProfile::compose(Some(p), Channel::Green, t)),
                bits(t)
            );
        }
        assert_eq!(p.eps(Channel::Green), None);
        assert_eq!(p.displacement_at(Channel::Green, 2112.9), 0.0);
        // Blue USED to be a no-op here, because it was unmeasured. It is
        // measured now, so this asserts the opposite: blue must move, and must
        // move in the direction opposite to red. If a future edit reverts
        // `eps_b` to `None`, this fails rather than silently going quiet.
        assert_eq!(p.eps(Channel::Blue), Some(174.4e-6));
        assert!(
            p.displacement_at(Channel::Blue, 2112.9) > 0.0,
            "blue is imaged LARGE; its displacement must be positive"
        );
        assert!(
            p.displacement_at(Channel::Red, 2112.9) < 0.0,
            "red is imaged SMALL; the two channels must flank green"
        );
    }

    /// **Bar L6.** Composing then applying once must equal applying then
    /// rescaling radially — to `<= 1e-12` relative, the bar as registered.
    ///
    /// This is the bar that decides whether the correction is free. If it fails,
    /// the correction is not a closed-form composition and needs its own
    /// resampling pass.
    #[test]
    fn l6_composition_is_exact() {
        let p = &A7C2_FE100GM_2XTC_X4CPL;
        let s = 1.0 + p.eps_r;
        let (tx, ty) = p.translation;
        let mut rng = Rng(0x00C0_FFEE_1107);
        let mut worst = 0.0f64;

        for _ in 0..20_000 {
            let t = Similarity::from_params(SimilarityParams {
                ax: rng.signed() * 400.0,
                ay: rng.signed() * 400.0,
                g: rng.signed() * 0.1,
                rot: rng.signed() * 0.03,
            });
            let composed = OpticalProfile::compose(Some(p), Channel::Red, t);

            // A point anywhere on a full-frame CFA plane.
            let z = Cx::new(rng.signed() * 1758.0, rng.signed() * 1172.0);

            // Route A: one transform.
            let a = composed.apply(z);
            // Route B: align, then apply the measured displacement separately.
            let q = t.apply(z);
            let b = Cx::new(q.re * s + tx, q.im * s + ty);

            let scale = (b.re.abs() + b.im.abs()).max(1.0);
            let err = ((a.re - b.re).abs() + (a.im - b.im).abs()) / scale;
            worst = worst.max(err);
        }

        assert!(
            worst <= 1e-12,
            "L6 bar is <= 1e-12 relative; worst was {worst:e}. Above 1e-9 the \
             correction is not a closed-form composition and would need its own \
             resampling pass."
        );
    }

    /// The correction must *undo* the aberration, not double it.
    ///
    /// A sign error here is the failure mode that would look like a working fix
    /// while making the defect twice as bad, and it is exactly the shape of the
    /// 1.0-sensel artefact this milestone manufactured and disclosed once
    /// already.
    #[test]
    fn correction_opposes_the_aberration() {
        // Isolate the radial term: the translation is a separate, unattributed
        // effect and would otherwise mask the sign being tested here.
        let p = &OpticalProfile {
            translation: (0.0, 0.0),
            ..A7C2_FE100GM_2XTC_X4CPL
        };

        // Red is imaged SMALL (negative eps). Under the pull convention the
        // transform returns the SOURCE coordinate to sample, so magnifying the
        // output means sampling nearer the centre: the scale must be < 1.
        let s = 1.0 + p.eps_r;
        assert!(p.eps_r < 0.0);
        assert!(
            s < 1.0,
            "under a pull, magnifying an under-magnified channel samples inward"
        );

        // THE NON-CIRCULAR CLAUSE. Everything above restates the implementation.
        // This states the PHYSICS: a scene feature at radius u is recorded by an
        // (1 + eps)-magnified channel at radius (1 + eps) * u, so the corrected
        // image, asked for radius u, must sample exactly there.
        let r = 2112.9;
        let t = Similarity::IDENTITY;
        let composed = OpticalProfile::compose(Some(p), Channel::Red, t);
        let moved = composed.apply(Cx::new(r, 0.0));
        let where_the_aberration_put_it = (1.0 + p.eps_r) * r;
        assert!(
            (moved.re - where_the_aberration_put_it).abs() < 1e-9,
            "correction samples {} but the aberration put the feature at {}",
            moved.re,
            where_the_aberration_put_it
        );

        // The sample point moves inward by exactly the aberration.
        let shift = moved.re - r;
        assert!(
            shift < 0.0,
            "corrected red must sample inward under a pull, moved {shift}"
        );
        let aberration = -p.displacement_at(Channel::Red, r);
        assert!(
            (shift + aberration).abs() < 1e-9,
            "sample shift {shift} is not minus the aberration {aberration}"
        );
        // The published corner figure, in sensels. Two CFA plane px per sensel
        // is *not* applied here: the fit is in plane px and so is this.
        //
        // Was 1.4885 under the superseded -704.5 ppm. The number moved because
        // the coefficient did; if it moves again without `eps_r` moving, the
        // geometry has drifted and that is the bug this pin exists to catch.
        assert!(
            (aberration - 1.0742).abs() < 2e-3,
            "corner displacement {aberration} should be ~1.074 sensel"
        );
    }

    /// The test that could have caught the inverted sign, and did not exist.
    ///
    /// Every other test here is sign-symmetric: round-trip, composition and the
    /// bitwise no-op all hold for `+eps` and `-eps` alike. This one plants a
    /// known magnification in a synthetic channel, corrects it, and asserts the
    /// feature lands back where the scene put it. Applying the correction the
    /// wrong way round doubles the error instead of removing it, so the wrong
    /// sign cannot pass.
    #[test]
    fn a_planted_magnification_is_actually_undone() {
        let planted = 2.0e-3;
        let p = OpticalProfile {
            eps_r: planted,
            eps_b: None,
            translation: (0.0, 0.0),
            ..A7C2_FE100GM_2XTC_X4CPL
        };
        let composed = OpticalProfile::compose(Some(&p), Channel::Red, Similarity::IDENTITY);

        for &u in &[1.0, 137.5, 900.0, 2112.9] {
            for &(dx, dy) in &[(1.0, 0.0), (0.0, 1.0), (0.6, -0.8)] {
                // Where an (1 + planted)-magnified channel records the feature.
                let rec = Cx::new((1.0 + planted) * u * dx, (1.0 + planted) * u * dy);
                // Asking the corrected image for the scene position must sample
                // exactly the recorded position.
                let asked = composed.apply(Cx::new(u * dx, u * dy));
                let err = ((asked.re - rec.re).powi(2) + (asked.im - rec.im).powi(2)).sqrt();
                assert!(err < 1e-9, "u={u} dir=({dx},{dy}): residual {err}");

                // And the inverted convention must NOT pass, or this test is
                // as vacuous as the ones it exists to backstop.
                let wrong = Cx::new(u * dx / (1.0 + planted), u * dy / (1.0 + planted));
                let wrong_err =
                    ((wrong.re - rec.re).powi(2) + (wrong.im - rec.im).powi(2)).sqrt();
                if u > 1.0 {
                    assert!(
                        wrong_err > 1e-6,
                        "u={u}: the inverted convention is indistinguishable here"
                    );
                }
            }
        }
    }

    /// The pull direction, tested at a coefficient large enough that the two
    /// conventions cannot be confused for one another.
    ///
    /// At `eps = 0.05`, `1 + eps` and `1 / (1 + eps)` differ by 4.8% — 47.6 px
    /// at r = 1000. The old code shipped the reciprocal, and this test as it was
    /// originally written asserted the reciprocal too, because it asked the
    /// correction to map an ABERRATED coordinate to a true one. A pull does the
    /// opposite: it maps the coordinate you WANT to the coordinate you must
    /// SAMPLE. Getting that backwards is the whole of the defect.
    #[test]
    fn the_pull_maps_wanted_to_sampled_not_the_reverse() {
        let strong = OpticalProfile {
            eps_r: 0.05,
            translation: (0.0, 0.0),
            ..A7C2_FE100GM_2XTC_X4CPL
        };
        let composed = OpticalProfile::compose(Some(&strong), Channel::Red, Similarity::IDENTITY);
        let r = 1000.0;
        let sampled = composed.apply(Cx::new(r, 0.0)).re;

        // Asking for r must sample where the aberration recorded r.
        let recorded = r * (1.0 + strong.eps_r);
        assert!(
            (sampled - recorded).abs() < 1e-9,
            "asked for {r}, sampled {sampled}, aberration recorded it at {recorded}"
        );

        // The reciprocal convention is 47.6 px away here, so a regression to it
        // cannot hide inside a tolerance.
        let reciprocal = r / (1.0 + strong.eps_r);
        assert!(
            (sampled - reciprocal).abs() > 40.0,
            "the two conventions are only {} px apart; this test cannot discriminate",
            (sampled - reciprocal).abs()
        );
    }

    /// A non-zero translation must still compose exactly, and the round trip
    /// must return the point: apply the measured displacement, correct it, and
    /// land back where you started.
    #[test]
    fn translation_composes_exactly_and_round_trips() {
        let p = &A7C2_FE100GM_2XTC_X4CPL;
        let (tx, ty) = p.translation;
        let s = 1.0 + p.eps_r;
        let t = Similarity::from_params(SimilarityParams {
            ax: 12.5,
            ay: -7.25,
            g: 0.013,
            rot: 0.002,
        });
        let composed = OpticalProfile::compose(Some(p), Channel::Red, t);
        let z = Cx::new(811.0, -455.0);
        let q = t.apply(z);
        let expect = Cx::new(q.re * s + tx, q.im * s + ty);
        let got = composed.apply(z);
        assert!((got.re - expect.re).abs() < 1e-9);
        assert!((got.im - expect.im).abs() < 1e-9);

        // The full measured displacement model, `observed = (1+eps)*truth + t`.
        // The pull, asked for the true position, must sample the observed one.
        let corrected = OpticalProfile::compose(Some(p), Channel::Red, Similarity::IDENTITY);
        let truth = Cx::new(640.0, -320.0);
        let observed = Cx::new(
            truth.re * (1.0 + p.eps_r) + tx,
            truth.im * (1.0 + p.eps_r) + ty,
        );
        let sampled = corrected.apply(truth);
        assert!(
            (sampled.re - observed.re).abs() < 1e-9 && (sampled.im - observed.im).abs() < 1e-9,
            "asked for truth, sampled ({}, {}), model says ({}, {})",
            sampled.re,
            sampled.im,
            observed.re,
            observed.im
        );
    }

    /// The shipped profiles must DECLARE their radial support, and it must be
    /// honest about not reaching the corner.
    ///
    /// R6 measured `r = 0.208..0.788` over the 20 gated ROIs, with the outer
    /// two annuli empty. If someone later widens the fit set, this test fails
    /// and forces the declaration to be updated with it — which is the point.
    /// A profile whose support silently drifts out of date is worse than one
    /// with no support field at all, because it looks checked.
    #[test]
    fn the_shipped_profiles_declare_a_support_radius_short_of_the_corner() {
        for p in [&A7C2_FE100GM_2XTC_X4CPL, &A7C2_FE100GM_2XTC_X4CPL_RADIAL] {
            let r = p
                .support_r_max
                .unwrap_or_else(|| panic!("{} ships without declaring its support", p.key));
            assert!(
                (r - 0.788).abs() < 5e-4,
                "{} declares support {r}, R6 measured 0.788",
                p.key
            );
            assert!(
                r < 1.0,
                "{} claims support to the corner; R6 found the outer two annuli empty",
                p.key
            );
        }
    }

    /// The RGGB site map, and the blast radius it implies.
    ///
    /// `warp_frame_in_place` already gathers each of the four CFA sites
    /// separately (`align_cmd.rs:1253-1287`), so wiring the correction means
    /// composing a per-site transform inside a loop that already exists.
    #[test]
    fn the_cfa_site_map_leaves_both_greens_bitwise_frozen() {
        assert_eq!(cfa_site_channel(0, 0), Channel::Red);
        assert_eq!(cfa_site_channel(1, 0), Channel::Green);
        assert_eq!(cfa_site_channel(0, 1), Channel::Green);
        assert_eq!(cfa_site_channel(1, 1), Channel::Blue);

        // The claim that matters. This test used to require that exactly ONE of
        // the four gathers moved, because blue was unmeasured. Blue is measured
        // now, so the invariant that survives is the one that was always the
        // real point: BOTH GREEN GATHERS ARE BITWISE FROZEN. Green is the
        // channel the focus measure and the election run on, so a green that
        // moved would change which frame wins, and every merge number in the
        // corpus with it.
        let p = Some(&A7C2_FE100GM_2XTC_X4CPL_RADIAL);
        let t = Similarity::from_params(SimilarityParams {
            ax: 7.5,
            ay: -3.25,
            g: 0.041,
            rot: 0.012,
        });
        let mut moved = 0;
        for dy in 0..2 {
            for dx in 0..2 {
                let c = cfa_site_channel(dx, dy);
                let got = OpticalProfile::compose(p, c, t);
                let same = got.a.re.to_bits() == t.a.re.to_bits()
                    && got.a.im.to_bits() == t.a.im.to_bits()
                    && got.b.re.to_bits() == t.b.re.to_bits()
                    && got.b.im.to_bits() == t.b.im.to_bits();
                if same {
                    assert_eq!(c, Channel::Green, "a frozen gather must be green");
                } else {
                    moved += 1;
                    assert_ne!(c, Channel::Green, "green must never move");
                }
            }
        }
        assert_eq!(moved, 2, "red and blue move; the two greens do not");
    }

    /// The gate is OFF by default and REFUSES rather than guessing.
    ///
    /// L4 split — 0.950 one direction, 0.541 the other against a 0.60 bar — so
    /// the coefficient's transfer is measured to be uneven and default-on would
    /// be a regression risk. And the profile includes a 2x teleconverter that
    /// cannot be detected from the frames, so a truthy value like `1` is a
    /// request this function cannot honour.
    #[test]
    fn the_ca_gate_is_off_by_default_and_refuses_to_guess() {
        // Absence and the off-forms are silent no-ops.
        for off in [None, Some(""), Some("  "), Some("0"), Some("off"), Some("OFF"), Some("false")] {
            assert_eq!(
                profile_from_setting(off),
                Ok(None),
                "{off:?} must be a silent no-op"
            );
        }

        // Truthy-but-unspecific values are REFUSED, not accepted.
        for truthy in ["1", "true", "on", "yes", "TRUE"] {
            let e = profile_from_setting(Some(truthy)).unwrap_err();
            assert_eq!(e, CaConfigError::UnknownProfile { key: truthy.to_string() },
                "{truthy:?} must be refused: it does not say which lens");
        }

        // A typo is an ERROR, not absence. A silently-disabled correction looks
        // exactly like a correction that does not work.
        assert!(profile_from_setting(Some("a7c2-fe100gm-2xtc")).is_err());
        assert!(profile_from_setting(Some("A7C2-FE100GM-2XTC-X4CPL")).is_err(),
            "the key is case-sensitive; a near-miss must not silently apply");

        // The error names the known keys, so the operator can fix it.
        let msg = profile_from_setting(Some("nope")).unwrap_err().to_string();
        assert!(msg.contains("nope") && msg.contains("a7c2-fe100gm-2xtc-x4cpl"), "{msg}");
    }

    /// Naming the path resolves to the RADIAL-ONLY form, never the raw record.
    #[test]
    fn the_gate_applies_the_radial_term_only() {
        let got = profile_from_setting(Some("a7c2-fe100gm-2xtc-x4cpl")).unwrap().unwrap();
        assert_eq!(got.translation, (0.0, 0.0),
            "the fitted translation is recorded, not applied: it leaves 17.3 ppm vs 0.6 ppm");
        assert_eq!(got.eps_r, A7C2_FE100GM_2XTC_X4CPL.eps_r);
        // Whitespace is tolerated; the key is not.
        assert!(profile_from_setting(Some(" a7c2-fe100gm-2xtc-x4cpl ")).unwrap().is_some());
    }

    /// The applied profile and the recorded one must not drift apart. They differ
    /// only in the term §12.1 measured to be harmful.
    #[test]
    fn the_two_profiles_differ_only_in_translation() {
        let rec = &A7C2_FE100GM_2XTC_X4CPL;
        let app = &A7C2_FE100GM_2XTC_X4CPL_RADIAL;
        assert_eq!(rec.key, app.key);
        assert_eq!(rec.optical_path, app.optical_path);
        assert_eq!(rec.measured_from, app.measured_from);
        assert_eq!(rec.version, app.version);
        assert_eq!(rec.eps_r, app.eps_r);
        assert_eq!(rec.eps_b, app.eps_b);
        assert_eq!(rec.fit_r.r_squared, app.fit_r.r_squared);
        assert_ne!(rec.translation, app.translation);
        assert_eq!(app.translation, (0.0, 0.0));
    }

    /// The measured datum itself, pinned — not just the code path that uses it.
    ///
    /// Independent verification mutated the shipped `translation` constant three
    /// ways — flipped both signs, scaled it 10x, swapped its axes — and **all
    /// three survived with 281 tests passing.** Every test that touched
    /// translation re-read `p.translation` and recomputed its own expectation
    /// from it, so the suite was self-consistent for any non-zero pair. The
    /// *direction of the code path* was pinned; the *value and sign of the
    /// datum* were not. Given that this term was inverted alongside the radial
    /// one, nothing here would have caught it had it stayed inverted.
    ///
    /// So this test asserts the literal numbers against their source of truth.
    /// For `eps_r` that source is now BUILD-CROP's six-stack fit on the
    /// delivered masters, median `-508.4e-6`; it was `e10_transfer.py`'s
    /// 3-parameter fit at `-704.5273607382725e-6`, which is SUPERSEDED and
    /// documented as such beside the field. The translation is unchanged at
    /// `t = (0.6294433, -0.4240211)` plane px. A profile that drifts from the
    /// fit it claims to record is not a profile.
    #[test]
    fn the_shipped_coefficients_match_the_fit_they_claim() {
        let p = &A7C2_FE100GM_2XTC_X4CPL;

        // eps_R, in ppm, as fitted. Sign is load-bearing: red is imaged SMALL.
        assert!(p.eps_r < 0.0, "red is under-magnified; eps_r must be negative");
        assert!(
            (p.eps_r * 1e6 + 508.4).abs() < 0.05,
            "eps_r is {} ppm; the fit says -508.4 ppm",
            p.eps_r * 1e6
        );

        // The translation, both components, sign and magnitude.
        let (tx, ty) = p.translation;
        assert!(
            tx > 0.0 && ty < 0.0,
            "fitted translation is (+x, -y), got ({tx}, {ty})"
        );
        assert!((tx - 0.6294).abs() < 5e-5, "tx is {tx}; the fit says +0.6294 plane px");
        assert!((ty + 0.4240).abs() < 5e-5, "ty is {ty}; the fit says -0.4240 plane px");
        // An axis swap must not pass: the two components differ by 48 %.
        assert!(
            (tx.abs() - ty.abs()).abs() > 0.15,
            "the components are too close to discriminate an axis swap"
        );

        // Blue was unmeasured when this record shipped and is measured now.
        // Pin the value, not merely its presence: a coefficient that drifts is
        // worse than one that is absent, because it still looks measured.
        assert_eq!(
            p.eps_b,
            Some(174.4e-6),
            "eps_b is the BUILD-CHROMA leave-one-out median; changing it needs a re-measurement"
        );
        let b = p.eps_b.unwrap();
        assert!(b > 0.0, "blue is over-magnified; eps_b must be positive");
        assert!(
            b.signum() != p.eps_r.signum(),
            "red and blue must flank green in sign; same-sign means a fit error in one arm"
        );
        // The evidence for blue must travel with it, and must not be silently
        // borrowed from red's much stronger fit.
        let fb = p.fit_b.expect("a measured eps_b must carry its FitStats");
        assert!(
            fb.r_squared < p.fit_r.r_squared,
            "blue is the weaker arm; if its R2 ever exceeds red's, the records have been crossed"
        );
    }

    /// The translation must be documented as unattributed. If a future edit
    /// quietly relabels it as an optical centre, this fails.
    #[test]
    fn the_translation_is_not_claimed_to_be_optical() {
        let p = &A7C2_FE100GM_2XTC_X4CPL;
        assert!(p.translation.0 != 0.0 || p.translation.1 != 0.0);
    }

    #[test]
    fn lookup_is_by_key_and_absence_is_legal() {
        assert!(by_key("a7c2-fe100gm-2xtc-x4cpl").is_some());
        assert!(by_key("a7c2-fe100gm").is_none(), "a different path must not match");
        assert!(by_key("").is_none());
    }

    /// The record must name the teleconverter. If someone drops it from the
    /// path string, the profile silently starts claiming to describe the bare
    /// lens, and that is the misuse the module docs exist to prevent.
    #[test]
    fn the_profile_names_its_whole_path() {
        let p = &A7C2_FE100GM_2XTC_X4CPL;
        for required in ["A7C II", "100mm", "teleconverter", "polariser"] {
            assert!(
                p.optical_path.contains(required),
                "optical path must name {required}: {}",
                p.optical_path
            );
        }
        assert!(p.measured_from.contains("M107"));
    }

    // ---------------------------------------------------------------------
    // The gear guard, and the default-on path it gates.
    //
    // These are the tests standing in for an experiment that cannot be run:
    // every stack in the corpus is the same body, lens and teleconverter, so
    // the guard has never declined a real file. The matcher takes plain
    // scalars precisely so that a negative case costs nothing to construct.
    // ---------------------------------------------------------------------

    /// The corpus rig, as `strehl_raw::identity` reads it off a real ARW.
    const RIG: (Option<&str>, Option<u16>) = (Some("ILCE-7CM2"), Some(33094));

    /// **The synthetic negative that matters most.** Same body, same glass,
    /// teleconverter removed.
    ///
    /// This is the misuse the whole module was written to prevent: the profile's
    /// coefficient was fitted *through* a 2x teleconverter, and a teleconverter
    /// magnifies the prime's residual aberration along with the image. Applied
    /// to the bare lens it would be roughly twice the correction the path needs,
    /// which turns a real defect into an equally real one of opposite sign.
    ///
    /// `32893` is not invented here: it is the id `strehl_raw::identity`'s own
    /// bare-lens fixture reports, two bytes different from `33094`.
    #[test]
    fn the_guard_declines_the_bare_lens() {
        let p = &A7C2_FE100GM_2XTC_X4CPL;
        assert_eq!(
            p.matches_gear(Some("ILCE-7CM2"), Some(32893)),
            GearMatch::Mismatch,
            "the bare lens is a DIFFERENT optical path and must not match"
        );
        assert_eq!(
            profile_for_capture(None, Some("ILCE-7CM2"), Some(32893)).unwrap(),
            None,
            "default-on must decline gear it was not measured on"
        );
        // And the two ids must stay distinct. If a future edit ever set the
        // profile's id to the bare lens's, the guard would silently invert.
        assert_ne!(p.lens_type3, 32893);
    }

    /// A file that says nothing must be declined, not guessed at.
    ///
    /// `Unknown` is a third value and this pins that it does not collapse into
    /// `Match`. The dangerous direction is unmistakable: an unreadable file
    /// treated as a match applies a measured aberration to unknown glass.
    #[test]
    fn the_guard_declines_an_unreadable_file() {
        let p = &A7C2_FE100GM_2XTC_X4CPL;
        assert_eq!(p.matches_gear(None, None), GearMatch::Unknown);
        // Half-known is still unknown: BOTH fields are required.
        assert_eq!(p.matches_gear(Some("ILCE-7CM2"), None), GearMatch::Unknown);
        assert_eq!(p.matches_gear(None, Some(33094)), GearMatch::Unknown);

        for (m, l) in [(None, None), (Some("ILCE-7CM2"), None), (None, Some(33094))] {
            assert_eq!(
                profile_for_capture(None, m, l).unwrap(),
                None,
                "an unidentified capture must get no profile"
            );
        }
    }

    /// The same lens on a different body is a different path.
    #[test]
    fn the_guard_declines_a_different_body() {
        let p = &A7C2_FE100GM_2XTC_X4CPL;
        assert_eq!(
            p.matches_gear(Some("ILCE-7RM5"), Some(33094)),
            GearMatch::Mismatch
        );
        // Verbatim comparison, so a near-miss is a miss. Sensor geometry
        // differs between bodies and the coefficient is in normalised field
        // height, so "close enough" is not a thing here.
        assert_eq!(
            p.matches_gear(Some("ilce-7cm2"), Some(33094)),
            GearMatch::Mismatch,
            "the body model is compared verbatim, as CaptureIdentity does"
        );
        assert_eq!(
            profile_for_capture(None, Some("ILCE-7RM5"), Some(33094)).unwrap(),
            None
        );
    }

    /// **The default-on case.** Recognised gear, operator silent, correction on.
    #[test]
    fn matching_gear_gets_the_profile_with_no_environment_set() {
        let (m, l) = RIG;
        let got = profile_for_capture(None, m, l).unwrap();
        assert!(got.is_some(), "this is the default-on change; it must apply");
        let got = got.unwrap();
        assert_eq!(got.key, A7C2_FE100GM_2XTC_X4CPL.key);
        // Empty and whitespace-only mean "said nothing", like an unset variable.
        for quiet in ["", "   "] {
            assert!(
                profile_for_capture(Some(quiet), m, l).unwrap().is_some(),
                "{quiet:?} must not be read as a refusal"
            );
        }
    }

    /// Default-on must apply the **radial-only** form, not the recorded one.
    ///
    /// The recorded const carries a fitted translation that is structurally
    /// unattributed and measured to be 12x worse than dropping it. Default-on
    /// silently applying it to every frame would be the worst version of this
    /// change, and it is a one-word slip away.
    #[test]
    fn the_default_on_path_applies_the_radial_form() {
        let (m, l) = RIG;
        let got = profile_for_capture(None, m, l).unwrap().unwrap();
        assert_eq!(got.translation, (0.0, 0.0), "the translation must not ship");
        // Compared BY VALUE, not by pointer. These profiles are `const`, not
        // `static`, so `&CONST` is const-promoted independently at each use site
        // and `ptr::eq` can be false for two references to the same constant.
        // An identity test written with `ptr::eq` here fails for a reason that
        // has nothing to do with the profile being right.
        assert_eq!(*got, A7C2_FE100GM_2XTC_X4CPL_RADIAL);
        // The env path and the default path must land on the same profile.
        let via_env = profile_from_setting(Some(A7C2_FE100GM_2XTC_X4CPL.key))
            .unwrap()
            .unwrap();
        assert_eq!(*got, *via_env, "two routes, one profile");
    }

    /// Every profile must have a registered radial-only twin.
    ///
    /// `applied_form` falls back to the recorded profile for an unregistered
    /// key, which would apply an unattributed translation to a real render.
    /// This is the test that keeps that branch unreachable.
    #[test]
    fn every_profile_has_a_radial_form() {
        for p in PROFILES {
            let applied = applied_form(p);
            assert_eq!(
                applied.translation,
                (0.0, 0.0),
                "profile {} has no radial-only twin registered in applied_form",
                p.key
            );
            assert_eq!(applied.key, p.key);
            assert_eq!(applied.eps_r, p.eps_r);
            assert_eq!(applied.eps_b, p.eps_b);
        }
    }

    /// **Default-on makes the off switch load-bearing.**
    ///
    /// Under default-off, `STREHL_FIX_CA=off` was indistinguishable from doing
    /// nothing and could have rotted unnoticed. Under default-on it is the only
    /// way to obtain an uncorrected render, so it is now on the critical path
    /// for every A/B comparison anyone runs against this correction.
    #[test]
    fn the_operator_can_turn_it_off_on_matching_gear() {
        let (m, l) = RIG;
        for off in ["0", "off", "false", "OFF", " off "] {
            assert_eq!(
                profile_for_capture(Some(off), m, l).unwrap(),
                None,
                "{off:?} must defeat the gear match"
            );
        }
    }

    /// The operator's word outranks the gear match in both directions, and a
    /// typo is still an error rather than a silent fallback to the default.
    ///
    /// This is the sharp edge of default-on: a typo'd override must NOT quietly
    /// resolve to the gear-matched profile, because then the operator's stated
    /// intent has been discarded without a word.
    #[test]
    fn a_typod_override_errors_rather_than_falling_back_to_the_default() {
        let (m, l) = RIG;
        assert!(profile_for_capture(Some("nope"), m, l).is_err());
        // Truthy values are still refused: "yes, correct CA" does not say which
        // lens, and under default-on it does not need to -- so typing it is a
        // sign the operator believes something untrue about the switch.
        for truthy in ["1", "true", "on"] {
            assert!(profile_for_capture(Some(truthy), m, l).is_err(), "{truthy}");
        }
        // An override naming a real profile applies even on unknown gear: the
        // operator is allowed to know something EXIF does not.
        let forced =
            profile_for_capture(Some(A7C2_FE100GM_2XTC_X4CPL.key), None, None).unwrap();
        assert!(forced.is_some(), "an explicit profile must not need the guard");
    }

    /// **The truth table V-CA's blocker was about.** One row per case,
    /// asserting the resolved decision and the printed line **together**, so
    /// they cannot drift apart again.
    ///
    /// The defect this pins was not that the string was ugly. It was that the
    /// string was computed from a *different input* than the pixels were, so
    /// the two were free to disagree — and they did, in both directions.
    /// Asserting only the string would leave that freedom intact; asserting
    /// only the profile would not have caught the original bug at all.
    #[test]
    fn the_status_line_matches_the_decision_on_every_row() {
        let (m, l) = RIG;
        let key = A7C2_FE100GM_2XTC_X4CPL.key;

        // Row 1: operator silent, gear matches -> CORRECTING (default on).
        let d = resolve_for_capture(None, m, l).unwrap();
        assert!(d.is_correcting(), "silent + matching gear must correct");
        let s = d.to_string();
        assert!(s.starts_with("CORRECTING"), "{s}");
        assert!(s.contains(key), "the line must name the profile: {s}");
        assert!(s.contains("default on"), "and say WHY it is on: {s}");

        // Row 2: operator says off, gear matches -> off. This is the row that
        // printed `CORRECTING, profile "off"` before the fix.
        let d = resolve_for_capture(Some("off"), m, l).unwrap();
        assert!(!d.is_correcting(), "an explicit off must defeat the guard");
        let s = d.to_string();
        assert!(s.starts_with("off ("), "{s}");
        assert!(!s.contains("CORRECTING"), "the inverted line, verbatim: {s}");
        assert!(s.contains("\"off\""), "echo what the operator typed: {s}");

        // Row 3: operator names the profile -> CORRECTING, and says so.
        let d = resolve_for_capture(Some(key), m, l).unwrap();
        assert!(d.is_correcting());
        let s = d.to_string();
        assert!(s.contains("operator asked for"), "{s}");

        // Row 4: gear declined. The operator must be told WHAT was declined.
        let d = resolve_for_capture(None, Some("ILCE-7RM5"), Some(32893)).unwrap();
        assert!(!d.is_correcting(), "unrecognised gear must not be corrected");
        let s = d.to_string();
        assert!(s.starts_with("off ("), "{s}");
        assert!(
            s.contains("ILCE-7RM5") && s.contains("32893"),
            "a decline must name the body AND lens it declined on: {s}"
        );

        // Row 5: identity unreadable -- a different problem, so a different
        // sentence, and it must point at the override.
        let d = resolve_for_capture(None, None, None).unwrap();
        assert!(!d.is_correcting());
        let s = d.to_string();
        assert!(s.contains("unreadable"), "{s}");
        assert!(s.contains(CA_ENV), "tell them how to override: {s}");
    }

    /// The reported profile and the applied profile are **the same value**, not
    /// two values that agree.
    ///
    /// This is the structural half of the fix. `profile_for_capture` is a
    /// projection of `resolve_for_capture`, so a future edit that reintroduces a
    /// second reconstruction has to defeat this test to do it.
    #[test]
    fn the_reported_profile_is_the_applied_profile() {
        let cases: [(Option<&str>, Option<&str>, Option<u16>); 8] = [
            (None, Some("ILCE-7CM2"), Some(33094)),
            (None, Some("ILCE-7CM2"), Some(32893)),
            (None, Some("ILCE-7RM5"), Some(33094)),
            (None, None, None),
            (Some("off"), Some("ILCE-7CM2"), Some(33094)),
            (Some("0"), Some("ILCE-7CM2"), Some(33094)),
            (Some(""), Some("ILCE-7CM2"), Some(33094)),
            (
                Some(A7C2_FE100GM_2XTC_X4CPL.key),
                Some("ILCE-7RM5"),
                Some(1),
            ),
        ];
        for (set, m, l) in cases {
            let decision = resolve_for_capture(set, m, l).unwrap();
            let applied = profile_for_capture(set, m, l).unwrap();
            assert_eq!(
                decision.profile, applied,
                "status and gather disagree for {set:?} / {m:?} / {l:?}"
            );
            // And the headline word must follow the profile, not the reason.
            assert_eq!(decision.is_correcting(), applied.is_some());
            let s = decision.to_string();
            assert_eq!(
                s.starts_with("CORRECTING"),
                applied.is_some(),
                "printed {s:?} but the gather gets {:?}",
                applied.map(|p| p.key)
            );
            assert!(!s.contains("INCONSISTENT"), "unreachable arm reached: {s}");
        }
    }

    /// An error must stay an error through the reason-bearing path too.
    ///
    /// A typo'd override that quietly resolved to the gear default would
    /// discard the operator's stated intent without a word — the same class of
    /// silent disagreement, one level up.
    #[test]
    fn resolve_propagates_the_typo_error_rather_than_defaulting() {
        let (m, l) = RIG;
        assert!(resolve_for_capture(Some("nope"), m, l).is_err());
        for truthy in ["1", "true", "on"] {
            assert!(resolve_for_capture(Some(truthy), m, l).is_err(), "{truthy}");
        }
    }
}
