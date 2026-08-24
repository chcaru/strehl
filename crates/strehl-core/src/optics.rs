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
//! M107 measured `eps_R = -704.5 ppm` on this path: a radial fit with
//! `R^2 = 0.9969` over 20 gated ROIs, permutation `p < 0.0005`, residual rms
//! **0.073 sensel**. The same fit run on a `G1 - G2` null — two greens, same
//! wavelength, different lattice site, so it carries every instrumental bias and
//! none of the chromatic signal — gets `R^2 = 0.0524` and **fails** its own
//! permutation null at `p = 0.7095`. That contrast is what makes the coefficient
//! a measurement rather than a curve through scatter.
//!
//! At the CFA half-diagonal of 2112.9 sensels that coefficient is **1.489
//! sensels, or 2.977 output pixels**, of red-against-green misregistration at
//! the corner. The owner inspects at 100%.
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
//! # This module is not wired to anything
//!
//! Nothing calls it. It is a tested unit awaiting a separate wiring commit, and
//! the correction is **opt-in by construction**: the entry point takes an
//! [`Option`], and [`None`] is a silent, exact no-op. The default linear render
//! path is byte-frozen, and a profile that is never supplied cannot move it.

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
    /// Red's radial magnification error relative to green.
    pub eps_r: f64,
    /// Blue's radial magnification error relative to green.
    ///
    /// **`None` on the shipped record**: M107 established red's coefficient but
    /// did not establish blue's, and an unmeasured coefficient is absent rather
    /// than zero. `None` makes blue an exact no-op; writing `0.0` would claim
    /// blue was measured and found uncorrected, which is a different and
    /// unsupported claim.
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
    /// `eps * half_diagonal` ~ 1.5 sensels. Nothing in this crate calls
    /// `compose` yet; a wiring commit must satisfy that precondition.
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
    measured_from: "M107 Instrument A: 20 gated ROIs over tweezers-cpl and bee-3-cpl",
    // Not recorded by the capture metadata M107 had to hand. Absent rather than
    // guessed: lateral CA varies with aperture and magnification, so a guess here
    // would silently widen the profile's claimed applicability.
    measured_at: None,
    version: 1,
    eps_r: -704.5e-6,
    eps_b: None,
    // Unattributed: degenerate with an optical-centre offset, and the same order
    // as the ~0.5 px/axis that CFA co-siting predicts. See the field docs.
    translation: (0.6294, -0.4240),
    fit_r: FitStats {
        r_squared: 0.9969,
        permutation_p: 0.0005,
        residual_rms_sensel: 0.073,
        n_regions: 20,
    },
};

const PROFILES: [&OpticalProfile; 1] = [&A7C2_FE100GM_2XTC_X4CPL];

/// Look up a profile by key. Absence is legal and means "apply nothing".
pub fn by_key(key: &str) -> Option<&'static OpticalProfile> {
    PROFILES.iter().copied().find(|p| p.key == key)
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
        // Blue is unmeasured on this record, so it is also a no-op -- and that
        // is absence, not a measured zero.
        assert_eq!(p.eps(Channel::Blue), None);
        assert_eq!(p.displacement_at(Channel::Green, 2112.9), 0.0);
        assert_eq!(p.displacement_at(Channel::Blue, 2112.9), 0.0);
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
        let mut rng = Rng(0xC0FFEE_1107);
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
        assert!(
            (aberration - 1.4885).abs() < 2e-3,
            "corner displacement {aberration} should be ~1.489 sensel"
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
    /// So this test asserts the literal numbers against their source of truth:
    /// `e10_transfer.py`'s 3-parameter fit, `eps = -704.5273607382725e-6` and
    /// `t = (0.6294433, -0.4240211)` plane px. A profile that drifts from the
    /// fit it claims to record is not a profile.
    #[test]
    fn the_shipped_coefficients_match_the_fit_they_claim() {
        let p = &A7C2_FE100GM_2XTC_X4CPL;

        // eps_R, in ppm, as fitted. Sign is load-bearing: red is imaged SMALL.
        assert!(p.eps_r < 0.0, "red is under-magnified; eps_r must be negative");
        assert!(
            (p.eps_r * 1e6 + 704.5).abs() < 0.05,
            "eps_r is {} ppm; the fit says -704.5 ppm",
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

        // Blue was never measured. Absence is not a measured zero.
        assert!(p.eps_b.is_none(), "eps_b must stay None until blue is measured");
    }

    /// The translation must be documented as unattributed. If a future edit
    /// quietly relabels it as an optical centre, this fails.
    #[test]
    fn the_translation_is_not_claimed_to_be_optical() {
        let p = &A7C2_FE100GM_2XTC_X4CPL;
        assert!(p.translation.0 != 0.0 || p.translation.1 != 0.0);
        // eps_b is absent, not zero: blue was never measured.
        assert!(p.eps_b.is_none());
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
}
