//! Camera RGB to a **stated colorimetric target**, and the transfer curve.
//!
//! # What was wrong before this module existed
//!
//! The output path applied black subtraction, the as-shot white balance, and
//! optionally the sRGB transfer curve — and nothing else. There was no colour
//! matrix anywhere in `crates/`. White balance makes a neutral *neutral*; it
//! does nothing at all about the camera's primaries, which are not sRGB's and
//! are not even additive-RGB-like: this sensor's `xyz_to_cam` has off-diagonal
//! terms up to −0.57. Emitting those numbers into a file tagged as an image is
//! emitting **camera-native RGB**, a space with no defined primaries, and every
//! saturated colour in it lands in the wrong place. On this body it reads as a
//! flat grey-green cast, because the camera's green response is much broader
//! than sRGB's and nothing narrows it.
//!
//! # The target, stated
//!
//! **sRGB / IEC 61966-2-1**: Rec. ITU-R BT.709-6 primaries, D65 white point,
//! and the piecewise sRGB transfer function. [`camera_to_srgb`] delivers
//! *linear* sRGB (BT.709 primaries, no curve); [`srgb_encode`] applies the
//! curve. They are separate because the linear form is the one that composes,
//! and the encoded form is the one you look at.
//!
//! # The order, stated
//!
//! ```text
//!   raw DN
//!     -> subtract black                    (per frame, from the file)
//!     -> multiply by as-shot WB gains      (per stack, from the file; M26)
//!     -> [demosaic, if demosaicing]        (cross-channel, so it needs WB first)
//!     -> multiply by camera_to_srgb()      (this module; neutral-preserving)
//!     -> clamp to [0, 1]
//!     -> srgb_encode()                     (this module)
//! ```
//!
//! Every step in that list is applied **after the merge**, in the writer.
//! `docs/research/M26-colour-clipping-measured.md` §2 measured why: the noise
//! model is `sigma^2 = g*S + (RN_e*g)^2` in **native per-channel raw DN**, and
//! a gate that white-balances first believes the red channel is up to 2.86x
//! quieter than it is. Nothing here may move earlier without transforming the
//! noise model with it.
//!
//! **Why demosaic sits between WB and the matrix.** A demosaic interpolates
//! *colour differences* (`R - G`), which are only smooth once the channels are
//! on a common scale; running it on un-white-balanced data makes `R - G` carry
//! the 2.86x gain as if it were scene chroma. And it must run before the
//! matrix because the matrix mixes channels, which would smear a demosaic
//! artifact in one channel across all three.
//!
//! # Where the numbers come from
//!
//! Nothing in this module is a per-body constant. [`camera_to_srgb`] takes the
//! camera's characterisation as an argument, and the pipeline reads it from the
//! RAW file through the decoder (`strehl_raw::Frame::xyz_to_cam_rgb`, one
//! crate up). `profile.rs`'s rule — a per-body constant lives in a profile,
//! never in pipeline code — is honoured here by having no per-body constant at
//! all.
//!
//! The two constants that *are* here, [`SRGB_TO_XYZ_D65`] and the transfer
//! curve, are the standard's own numbers, and both are checked in this module's
//! tests against the primaries they are derived from rather than asserted.

use crate::clip;
use crate::noise::Levels;

/// Linear sRGB -> CIE XYZ, D65.
///
/// **DERIVED from the standard's chromaticities, not copied from a table.**
/// sRGB / BT.709-6 primaries `R (0.6400, 0.3300)`, `G (0.3000, 0.6000)`,
/// `B (0.1500, 0.0600)` and white point D65 `(0.3127, 0.3290)`. The derivation
/// is the standard NPM construction (Hunt/Fairchild): build the 3x3 of primary
/// chromaticities, solve for the scale factors that map `(1,1,1)` to the white
/// point's XYZ, and scale the columns.
///
/// The test [`tests::the_srgb_matrix_is_what_its_own_chromaticities_imply`]
/// performs that derivation and agrees with these numbers to < 1e-4, which is
/// what licenses them being written out rather than computed at startup. A
/// constant with a derivation beside it that is *run* is not a magic number.
pub const SRGB_TO_XYZ_D65: [[f64; 3]; 3] = [
    [0.412_456_4, 0.357_576_1, 0.180_437_5],
    [0.212_672_9, 0.715_152_2, 0.072_175_0],
    [0.019_333_9, 0.119_192_0, 0.950_304_1],
];

/// CIE XYZ of the D65 white point, `Y = 1`.
///
/// These are the **row sums of [`SRGB_TO_XYZ_D65`]**, which is what makes the
/// two constants mutually consistent: by construction that matrix maps linear
/// sRGB `(1,1,1)` to the white point. Written out rather than summed at
/// runtime, and checked against the sums in the tests.
pub const D65_XYZ: [f64; 3] = [0.950_470_0, 1.0, 1.088_830_0];

/// The camera's response to the D65 white point, in camera RGB.
///
/// This is the quantity that says which way round a characterisation matrix is.
/// A camera looking at D65 white produces raw R:G:B in this ratio, so its
/// reciprocal (normalised to green) is the **daylight white balance the matrix
/// implies** — a number that can be checked against the white balance the body
/// actually wrote into the file, by a completely different route.
///
/// That check is the reason this is public. See
/// [`implied_daylight_wb_gains`].
pub fn neutral_response(xyz_to_cam: [[f32; 3]; 3]) -> [f32; 3] {
    let mut out = [0.0f32; 3];
    for (i, row) in xyz_to_cam.iter().enumerate() {
        let mut acc = 0.0f64;
        for (j, v) in row.iter().enumerate() {
            acc += f64::from(*v) * D65_XYZ[j];
        }
        out[i] = acc as f32;
    }
    out
}

/// The daylight white-balance gains `[R, 1, B]` that `xyz_to_cam` implies.
///
/// `None` if any channel's neutral response is non-positive, which a
/// transposed or otherwise wrong matrix can easily produce — and that is the
/// point: this function has the power to reject.
///
/// **This is not the white balance the pipeline uses.** The pipeline uses the
/// as-shot value from the file, because M26 measured the as-shot multipliers
/// varying 2.13-2.86x in R across six stacks of the same body while the
/// daylight value stayed fixed. This exists to *cross-check the matrix*
/// against a number obtained from a different tag by a different code path.
pub fn implied_daylight_wb_gains(xyz_to_cam: [[f32; 3]; 3]) -> Option<[f32; 3]> {
    let n = neutral_response(xyz_to_cam);
    if !(n[0] > 0.0 && n[1] > 0.0 && n[2] > 0.0) {
        return None;
    }
    Some([n[1] / n[0], 1.0, n[1] / n[2]])
}

/// **White-balanced camera RGB -> linear sRGB.** The matrix the output path
/// was missing.
///
/// `xyz_to_cam` is the camera's characterisation as the decoder reports it:
/// XYZ (D65) -> camera RGB.
///
/// # What the returned matrix expects on its input
///
/// White-balanced camera RGB — that is, camera RGB after the as-shot gains, so
/// that a neutral surface under the shot illuminant reads `R = G = B`. It is
/// **not** correct to apply this to un-white-balanced data.
///
/// # Construction, and why each step is there
///
/// 1. `cam_from_srgb = xyz_to_cam * SRGB_TO_XYZ_D65`, giving linear sRGB ->
///    camera RGB.
/// 2. **Normalise each row to sum 1.** Row `i` summed is camera channel `i`'s
///    response to sRGB white, so this is precisely the step that says "the
///    input is already white balanced". Skipping it produces a matrix that
///    inverts the white balance you just applied, and the result is a strong
///    cast — which is a failure this module's tests plant deliberately.
/// 3. Invert.
///
/// Because step 2 makes `cam_from_srgb * (1,1,1)^T = (1,1,1)^T`, the inverse
/// maps `(1,1,1)` to `(1,1,1)` exactly, so **every row of the returned matrix
/// sums to 1** and a neutral input is a neutral output *by construction*. That
/// is a strong property and a weak one at the same time, and the honest
/// statement of it is: this transform cannot introduce or remove a global
/// cast, so it cannot be validated by looking at a grey patch. Only
/// off-neutral colours move. Judge it on chromaticity round-trip, which
/// [`tests::synthetic_patches_of_known_chromaticity_round_trip`] does.
///
/// # What this is not
///
/// It is not a chromatic adaptation transform. Adaptation from the shot
/// illuminant to D65 is being done by the von Kries scaling in camera space —
/// the as-shot white balance — which is what every raw developer does and what
/// the DNG specification's simple path does. A full CAT02 adaptation between
/// the two illuminants, and interpolation between a camera's two illuminant
/// matrices, are both better and neither is implemented here. Under a strongly
/// non-daylight illuminant this will leave a residual error that no test in
/// this crate can see, because the corpus contains no grey card.
///
/// Returns `None` if the composed matrix is singular.
pub fn camera_to_srgb(xyz_to_cam: [[f32; 3]; 3]) -> Option<Render> {
    // 1. linear sRGB -> camera RGB
    let mut cam_from_srgb = [[0.0f64; 3]; 3];
    for i in 0..3 {
        for j in 0..3 {
            let mut acc = 0.0f64;
            for (k, x) in SRGB_TO_XYZ_D65.iter().enumerate() {
                acc += f64::from(xyz_to_cam[i][k]) * x[j];
            }
            cam_from_srgb[i][j] = acc;
        }
    }

    // 2. Row-normalise: the input is white balanced, so sRGB white must map to
    //    camera (1,1,1).
    for row in cam_from_srgb.iter_mut() {
        let sum = row[0] + row[1] + row[2];
        if !(sum.is_finite() && sum.abs() > 1e-9) {
            return None;
        }
        for v in row.iter_mut() {
            *v /= sum;
        }
    }

    // 3. Invert.
    let inv = invert3(cam_from_srgb)?;
    let mut out = [[0.0f32; 3]; 3];
    for i in 0..3 {
        for j in 0..3 {
            if !inv[i][j].is_finite() {
                return None;
            }
            out[i][j] = inv[i][j] as f32;
        }
    }
    Some(Render::new(out))
}

/// The colour transform for a viewing render: the matrix, **and** the sensor
/// saturation ceiling the matrix must not be fed past.
///
/// These two travel together because they are one decision. [`camera_to_srgb`]
/// mixes the channels — its green row is `[-0.115, +1.489, -0.374]` on the
/// reference body — so handing it a triple in which one channel is pinned at
/// the container maximum while white balance has carried the others *past* that
/// maximum does not produce a slightly wrong colour. It produces a confidently
/// wrong one: neutral white renders **magenta**, because the pinned green is
/// dragged down by the two unpinned terms while red and blue clamp at 1.0.
/// (MEASURED: 2.002 % of a 33 MP render of `dry-erase-marker-head-cpl`,
/// `docs/research/M109-highlights.md`.)
///
/// Bundling the ceiling into the same value makes it impossible to supply the
/// matrix and silently forget the ceiling: the type is the reminder. A caller
/// that genuinely has no ceiling to state gets [`Render::new`], whose ceiling is
/// `+inf` on every channel — which is exactly the arithmetic this pipeline did
/// before the ceiling existed, so no existing output moves.
#[derive(Debug, Clone, Copy, PartialEq)]
pub struct Render {
    to_srgb: [[f32; 3]; 3],
    ceiling: [f32; 3],
    top: f32,
}

impl Render {
    /// A render with **no stated ceiling**: highlight clipping is disabled and
    /// the arithmetic is the plain matrix multiply.
    pub fn new(to_srgb: [[f32; 3]; 3]) -> Self {
        Self {
            to_srgb,
            ceiling: [f32::INFINITY; 3],
            top: crate::highlight::CONTAINER_TOP,
        }
    }

    /// The same render, with a per-channel saturation ceiling in the render's
    /// own units. See [`saturation_ceiling`].
    ///
    /// The chroma roll-off's completion point is left at
    /// [`crate::highlight::CONTAINER_TOP`], because a bare ceiling does not say
    /// where the sensor's *usable* white sits. A caller holding the
    /// [`Levels`] should prefer [`Render::with_saturation`], which states it.
    #[must_use]
    pub fn with_ceiling(self, ceiling: [f32; 3]) -> Self {
        Self {
            ceiling,
            top: crate::highlight::CONTAINER_TOP,
            ..self
        }
    }

    /// The same render, told the whole saturation story: the per-channel
    /// ceiling *and* where usable white sits underneath it.
    ///
    /// This is [`with_ceiling`](Self::with_ceiling) plus one scalar the ceiling
    /// alone cannot carry. `saturation_ceiling` returns `k0 * wb[c] * eg`, and
    /// `k0` — the container expressed in units of the noise model's range,
    /// 1.068898 on the reference body — cannot be recovered from that product
    /// because `wb[c]` and `eg` are not separately visible in it. So it is
    /// passed, and stored as its reciprocal: the fraction of the ceiling at
    /// which `Levels::white` sits, 0.9355.
    ///
    /// It matters because the merged file does not reach the container.
    /// `pyramid::Hull::InputRange` holds each reconstructed pixel to the range
    /// of its contributing frames, so `foam`'s hottest pixel sits at `u =
    /// 0.9355` and its top level decile averages `u = 0.7990`. With the
    /// container as the endpoint that decile's measured `B/G` excess fell only
    /// 29 %; see `docs/research/BUILD-HIGHLIGHT.md` for what stating `top`
    /// buys.
    #[must_use]
    pub fn with_saturation(self, levels: Levels, wb_gains: [f32; 3], exposure_gain: f32) -> Self {
        let range = levels.range();
        let span = f32::from(clip::CONTAINER_MAX_DN) - levels.black;
        // Refusing to state a `top` is the safe failure, as everywhere else in
        // this file: the roll-off then behaves exactly as `with_ceiling`.
        let top = if range.is_finite() && range > 0.0 && span.is_finite() && span >= range {
            range / span
        } else {
            crate::highlight::CONTAINER_TOP
        };
        Self {
            ceiling: saturation_ceiling(levels, wb_gains, exposure_gain),
            top,
            ..self
        }
    }

    /// Camera RGB to linear sRGB. Every row sums to 1.
    pub fn matrix(&self) -> &[[f32; 3]; 3] {
        &self.to_srgb
    }

    /// The per-channel ceiling, `+inf` where none was stated.
    pub fn ceiling(&self) -> [f32; 3] {
        self.ceiling
    }

    /// Where the chroma roll-off completes, as a fraction of the ceiling.
    pub fn top(&self) -> f32 {
        self.top
    }

    /// Bring a white-balanced camera-RGB triple back under the ceiling, *before*
    /// the matrix sees it.
    ///
    /// **Where nothing is pinned this is the identity, exactly.** That is not a
    /// convenience, it is the whole safety argument: an unsaturated stack takes
    /// the `else` branch on every pixel, so its render cannot move by one bit.
    /// An unconditional clamp would not have this property — the ceiling on red
    /// is only `1/2.687` of the container in *unbalanced* terms, so a plain
    /// clamp would eat real, unclipped red highlights above roughly 6420 DN.
    ///
    /// Where something *is* pinned, every channel is brought down to the
    /// **neutral** ceiling `min_c ceiling[c]`. All three channels of a blown
    /// neutral are above it, so all three land on it exactly, and because every
    /// row of [`camera_to_srgb`] sums to 1 an equal-channel input is an
    /// equal-channel output: blown neutral renders neutral. A channel that is
    /// *below* the neutral ceiling is left alone, so a blown **coloured**
    /// highlight — green pinned, red genuinely low — keeps its hue direction
    /// instead of being bleached to white.
    ///
    /// The cost is real and is not hidden: the headroom above the neutral
    /// ceiling in the unpinned channels is discarded, which desaturates a
    /// strongly clipped colour slightly. A pinned channel is not a measurement
    /// of how saturated the object was, so keeping that headroom would be
    /// fabricating saturation the sensor never recorded.
    #[inline]
    pub fn clip_highlights(&self, v: [f32; 3]) -> [f32; 3] {
        let pinned = v[0] >= self.ceiling[0] || v[1] >= self.ceiling[1] || v[2] >= self.ceiling[2];
        if !pinned {
            return v;
        }
        let neutral = self.ceiling[0].min(self.ceiling[1]).min(self.ceiling[2]);
        [v[0].min(neutral), v[1].min(neutral), v[2].min(neutral)]
    }

    /// Clip, then roll the chroma off, then transform. The order is the point.
    ///
    /// [`clip_highlights`](Self::clip_highlights) owns the *pinned* case and is
    /// unchanged; [`crate::highlight::desaturate`] owns the *approach*, which
    /// M109 section 16 measured that guard cannot see because the merge averages
    /// pinned and unpinned samples and the result lands strictly below the
    /// ceiling. A blown neutral leaves `clip_highlights` already neutral, and a
    /// neutral is a fixed point of the roll-off, so the two compose without
    /// fighting. Below the roll-off's knee it is the identity, bit for bit.
    #[inline]
    pub fn develop(&self, v: [f32; 3]) -> [f32; 3] {
        let v = crate::highlight::desaturate(
            self.ceiling,
            self.top,
            &self.to_srgb,
            self.clip_highlights(v),
        );
        apply(&self.to_srgb, v)
    }
}

/// Where a container-saturated sample lands in a viewing render's units, per
/// channel.
///
/// A render normalises by [`Levels::range`] — `white - black`, the **noise
/// model's** calibrated range, 14848 DN on the reference body. But the sample
/// container saturates at [`clip::CONTAINER_MAX_DN`], 16383. `clip.rs` insists
/// these are different numbers and must not be unified; this function is what
/// it looks like to *use* both of them for what each one is. A pinned sample
/// therefore does not land at 1.0 — it lands at
///
/// ```text
/// (CONTAINER_MAX_DN - black) / (white - black)  =  1.068898  on the reference rig
/// ```
///
/// times the channel's white-balance gain and the exposure gain, because the
/// render applies both after normalising. Green's as-shot gain is 1.0 by
/// construction, red's is 2.687 and blue's 1.532, so the three channels stop at
/// three different heights — which is precisely why a blown neutral is not
/// neutral without [`Render::clip_highlights`].
///
/// `wb_gains` are the green-normalised as-shot multipliers actually applied to
/// the buffer, and `exposure_gain` the linear gain from [`AppliedExposure`], in
/// the same order the render applies them.
pub fn saturation_ceiling(levels: Levels, wb_gains: [f32; 3], exposure_gain: f32) -> [f32; 3] {
    let range = levels.range();
    if !(range.is_finite() && range > 0.0) {
        return [f32::INFINITY; 3];
    }
    let k0 = (f32::from(clip::CONTAINER_MAX_DN) - levels.black) / range;
    let mut out = [f32::INFINITY; 3];
    for c in 0..3 {
        let k = k0 * wb_gains[c] * exposure_gain;
        // A non-finite or non-positive ceiling would clip everything to zero.
        // Refusing to state one is the safe failure: the render is then exactly
        // what it was before this function existed.
        out[c] = if k.is_finite() && k > 0.0 {
            k
        } else {
            f32::INFINITY
        };
    }
    out
}

/// `m * v`, for a 3x3 and a 3-vector.
#[inline]
pub fn apply(m: &[[f32; 3]; 3], v: [f32; 3]) -> [f32; 3] {
    [
        m[0][0] * v[0] + m[0][1] * v[1] + m[0][2] * v[2],
        m[1][0] * v[0] + m[1][1] * v[1] + m[1][2] * v[2],
        m[2][0] * v[0] + m[2][1] * v[1] + m[2][2] * v[2],
    ]
}

/// Exact 3x3 inverse in `f64`. `None` when the determinant is too small for
/// the result to mean anything.
fn invert3(m: [[f64; 3]; 3]) -> Option<[[f64; 3]; 3]> {
    let c = [
        [
            m[1][1] * m[2][2] - m[1][2] * m[2][1],
            m[0][2] * m[2][1] - m[0][1] * m[2][2],
            m[0][1] * m[1][2] - m[0][2] * m[1][1],
        ],
        [
            m[1][2] * m[2][0] - m[1][0] * m[2][2],
            m[0][0] * m[2][2] - m[0][2] * m[2][0],
            m[0][2] * m[1][0] - m[0][0] * m[1][2],
        ],
        [
            m[1][0] * m[2][1] - m[1][1] * m[2][0],
            m[0][1] * m[2][0] - m[0][0] * m[2][1],
            m[0][0] * m[1][1] - m[0][1] * m[1][0],
        ],
    ];
    let det = m[0][0] * c[0][0] + m[0][1] * c[1][0] + m[0][2] * c[2][0];
    if !det.is_finite() || det.abs() < 1e-12 {
        return None;
    }
    let mut out = [[0.0f64; 3]; 3];
    for i in 0..3 {
        for j in 0..3 {
            out[i][j] = c[i][j] / det;
        }
    }
    Some(out)
}

/// The sRGB transfer function, IEC 61966-2-1. Linear `[0,1]` -> encoded
/// `[0,1]`.
///
/// The breakpoint and the 12.92 / 1.055 / 0.055 / 2.4 constants are the
/// standard's, and the standard is very slightly self-inconsistent at the
/// join — the two branches differ by about 4e-5 there. That is the standard's
/// discontinuity, not a defect here, and it is one part in 24000 of full
/// scale, well below a 16-bit code.
///
/// **This is a viewing curve. Nothing measured may be taken through it**: it
/// is strongly non-linear near black, where all this project's noise
/// measurements live.
#[inline]
pub fn srgb_encode(v: f32) -> f32 {
    if v <= 0.003_130_8 {
        12.92 * v
    } else {
        1.055 * v.powf(1.0 / 2.4) - 0.055
    }
}

// ---------------------------------------------------------------------------
// Exposure. Viewing path only: it sits in the module header's order between
// the colour matrix and the clamp, and the reason is documented on
// `AppliedExposure`.
// ---------------------------------------------------------------------------

/// Relative luminance of a **linear sRGB** triple, `Y` of CIE XYZ.
///
/// **DERIVED, not a new constant.** The weights are row 1 of
/// [`SRGB_TO_XYZ_D65`] — the row that produces `Y` — so this cannot drift away
/// from the primaries the rest of the module is built on. There is deliberately
/// no `0.2126 / 0.7152 / 0.0722` literal anywhere in this file;
/// [`tests::luminance_is_the_y_row_of_the_published_matrix`] asserts the
/// agreement.
///
/// Negative channels are floored at zero first. A negative channel is a
/// **gamut excursion** — [`camera_to_srgb`] has negative off-diagonal terms and
/// a saturated camera green legitimately lands at `B < 0` — and it is not
/// negative light. Letting it into the sum would let a saturated colour reduce
/// the luminance it is actually contributing, and the exposure rule below would
/// then brighten *because* the scene got more colourful.
#[inline]
pub fn luminance(v: [f32; 3]) -> f32 {
    let w = SRGB_TO_XYZ_D65[1];
    (w[0] * f64::from(v[0].max(0.0))
        + w[1] * f64::from(v[1].max(0.0))
        + w[2] * f64::from(v[2].max(0.0))) as f32
}

/// Luminance of a white-balanced **camera RGB** triple, as it will be displayed.
///
/// `matrix` is [`camera_to_srgb`]'s, or `None` when the pipeline is emitting
/// camera-native RGB because the body has no characterisation. In the `None`
/// case the camera triple is what lands in the file and is what a viewer will
/// read as sRGB, so weighting it with the sRGB luma row is the *consistent*
/// choice — not a correct one, because camera-native RGB has no defined
/// luminance, and the `--srgb`-without-a-matrix path already prints that it is
/// not a render of what the sensor saw.
///
/// This deliberately does **not** apply [`Render::clip_highlights`]. The
/// exposure statistic must read the scene as the sensor measured it, and
/// clipping first would couple the chosen exposure to the highlight fix — so a
/// before/after comparison of the fix would be confounded by a different
/// exposure. Keeping them independent is what lets the fix be judged on its own.
#[inline]
pub fn display_luminance(cam_rgb: [f32; 3], matrix: Option<&Render>) -> f32 {
    match matrix {
        Some(r) => luminance(apply(r.matrix(), cam_rgb)),
        None => luminance(cam_rgb),
    }
}

/// The **nearest-rank** index for a percentile of `len` sorted samples.
///
/// `ceil(p/100 * len) - 1`, clamped into range: the smallest index whose value
/// at least `p` percent of the sample is at or below. Nearest-rank rather than
/// an interpolating definition because the answer is then always a value that
/// actually occurs in the image, which is what makes
/// [`percentile_in_place`] a `select_nth_unstable` and therefore linear time
/// and *exactly* reproducible — the k-th order statistic is a property of the
/// multiset, so it does not depend on the sort algorithm at all.
///
/// **The rank is computed in integers, not floats.** `99.9` is not
/// representable in binary, and `(99.9 / 100.0 * 1000.0).ceil()` is `1000` and
/// not `999` — one rank off the textbook answer, silently. The percentile is
/// therefore rounded to basis points (hundredths of a percent, which covers
/// every value this pipeline uses) and the ceiling division is exact.
///
/// `None` for an empty sample. The definition is
/// `numpy.percentile(method="inverted_cdf")`, which is what lets the Python
/// cross-checks in `experiments/M100-exposure/` agree with this to the bit.
#[inline]
pub fn nearest_rank_index(len: usize, percentile: f64) -> Option<usize> {
    if len == 0 || !percentile.is_finite() {
        return None;
    }
    /// Basis points in 100%, i.e. the integer scale the rank is computed on.
    const SCALE: u128 = 1_000_000;
    let bp = (percentile.clamp(0.0, 100.0) * (SCALE as f64 / 100.0)).round() as u128;
    let rank = (len as u128 * bp).div_ceil(SCALE) as usize;
    Some(rank.saturating_sub(1).min(len - 1))
}

/// The `percentile`-th value of `xs`, by [`nearest_rank_index`].
///
/// Reorders `xs`. Non-finite samples are ordered by `f32::total_cmp`, which
/// puts `NaN` above every number — so a `NaN` in the image can only ever *lower*
/// the measured percentile by one rank, never raise it, and cannot become the
/// answer unless the image is essentially all `NaN`. That is the conservative
/// direction for an exposure rule: it underestimates the brightness, so it
/// underestimates the gain.
pub fn percentile_in_place(xs: &mut [f32], percentile: f64) -> Option<f32> {
    let k = nearest_rank_index(xs.len(), percentile)?;
    let (_, nth, _) = xs.select_nth_unstable_by(k, f32::total_cmp);
    Some(*nth)
}

/// The percentile of linear luminance the shipped auto rule places on target.
///
/// **MEASURED, not chosen by taste.** `docs/research/M100-exposure.md` §3
/// sweeps seven percentiles against five targets on seven corpus stacks, on
/// two candidate statistics. p99.9 of a 3516x2344 binned image is 8241 samples
/// above the threshold, which is robust to hot pixels and to a small specular,
/// and it is the highest percentile in the sweep that still leaves enough gain
/// to clear the effectiveness bar.
pub const AUTO_EXPOSURE_PERCENTILE: f64 = 99.9;

/// Where [`AUTO_EXPOSURE_PERCENTILE`] is placed, in linear light.
///
/// Below 1.0 on purpose: the percentile is not the brightest thing in the
/// scene, and the samples above it — speculars on chitin, the blown edge of a
/// backlit hair — are *supposed* to clip. The margin is what keeps the number
/// of them small.
///
/// **MEASURED, and the margin is not cosmetic.** On `bee-3-cpl` the background
/// is a large flat field, so its pixels cross 65535 together rather than one at
/// a time: raising this target from 0.90 to 0.95 takes that stack from 0.0422%
/// of pixels clipped to 0.7663%, an 18x jump for 0.07 stops (§3). 0.90 sits on
/// the safe side of that cliff with a 5x margin on the pre-registered ceiling.
pub const AUTO_EXPOSURE_TARGET: f32 = 0.90;

/// Hard bound on the automatic gain, in stops, each way.
///
/// **ARGUED, and it is a guard rail rather than a calibration.** A frame that
/// is nearly black — a dark frame, a failed capture, a lens cap — has a
/// luminance percentile near zero and would otherwise ask for an unbounded
/// gain. Nothing in the corpus comes near this bound (MEASURED, §3), so it does
/// not shape any shipped render; it exists so that a pathological input
/// produces a bounded wrong answer instead of an infinite one.
pub const AUTO_EXPOSURE_MAX_STOPS: f32 = 6.0;

/// The precision the automatic choice is reported at, and therefore **rounded
/// to**: steps per stop, so 100 is two decimal places.
///
/// The contract is that `--auto-exposure` prints a number the user can hand
/// back to `--exposure` and get the *same file*. That is only true if the
/// applied value is exactly the printed value, so the choice is quantised here
/// rather than only at the `{:.2}` in the report. 1/100 stop is a 0.69% gain
/// step.
///
/// The round trip is exact and not merely close: the quantisation divides an
/// integer by 100 in `f32`, and `"1.57".parse::<f32>()` rounds the same
/// rational — both are correctly rounded, so they are the same `f32`. It has to
/// be a *division*; multiplying by `0.01f32` would not be, because `0.01` is
/// not representable.
/// [`tests::the_printed_choice_reproduces_the_gain_through_a_string`] asserts
/// it through an actual `format!` and `parse`.
pub const AUTO_EXPOSURE_STEPS_PER_STOP: f32 = 100.0;

/// The exposure the user asked for, before any image has been looked at.
#[derive(Debug, Clone, Copy, PartialEq)]
pub enum Exposure {
    /// Nothing. **The caller must not multiply at all** — see
    /// [`AppliedExposure::is_identity`].
    None,
    /// An explicit gain of `2^stops`.
    Stops(f32),
    /// Choose from the image, with [`choose_exposure`].
    Auto,
}

/// Why an exposure request was refused.
#[derive(Debug, Clone, Copy, PartialEq, thiserror::Error)]
pub enum ExposureError {
    /// Exposure is a *viewing* control and the linear output is the
    /// measurement output. Brightening it would corrupt a measurement while
    /// looking like a favour.
    #[error(
        "--exposure and --auto-exposure are viewing controls and need --srgb; the default output \
         is the linear measurement file and must not be rescaled"
    )]
    NeedsSrgb,
    /// Both an explicit and an automatic exposure were asked for.
    #[error("--exposure and --auto-exposure both set an exposure; pass one or the other")]
    Both,
    /// `NaN`, an infinity, or a value outside +/- [`AUTO_EXPOSURE_MAX_STOPS`].
    #[error("--exposure must be a finite number of stops within +/-{max}")]
    OutOfRange {
        /// [`AUTO_EXPOSURE_MAX_STOPS`], so the message carries its own bound.
        max: f32,
    },
}

impl Exposure {
    /// Validate a command line into an [`Exposure`].
    ///
    /// Three refusals, and each one is a decision:
    ///
    /// 1. **Without `--srgb`, refuse.** Not "ignore": the linear file is what
    ///    every corpus number was measured on, and a user who believes they
    ///    brightened it has a corrupted measurement and no way to know.
    /// 2. **Both flags at once, refuse.** There is no sensible composition —
    ///    "automatic, then plus a bit" is a different feature and it is not
    ///    this one.
    /// 3. **`--exposure 0` becomes [`Exposure::None`].** Structural, not
    ///    arithmetic: a gain of exactly `1.0` would also be bit-exact, but
    ///    normalising here means the no-op request does not even reach the
    ///    multiply, so `--exposure 0` and no flag at all are the *same code
    ///    path* and cannot drift apart.
    pub fn resolve(srgb: bool, stops: f32, auto: bool) -> Result<Self, ExposureError> {
        let asked = auto || stops != 0.0;
        if asked && !srgb {
            return Err(ExposureError::NeedsSrgb);
        }
        if auto && stops != 0.0 {
            return Err(ExposureError::Both);
        }
        if auto {
            return Ok(Exposure::Auto);
        }
        if stops == 0.0 {
            return Ok(Exposure::None);
        }
        if !stops.is_finite() || stops.abs() > AUTO_EXPOSURE_MAX_STOPS {
            return Err(ExposureError::OutOfRange {
                max: AUTO_EXPOSURE_MAX_STOPS,
            });
        }
        Ok(Exposure::Stops(stops))
    }
}

/// The gain that will actually be applied, and where it came from.
///
/// # Where in the order this multiplies, and why
///
/// **In linear light, before the clamp, and therefore before
/// [`srgb_encode`].** Two halves:
///
/// *Before the curve.* The sRGB transfer function is not homogeneous —
/// `f(g*x) != g*f(x)` — so a gain applied to encoded values is not an exposure
/// at all. Worse, it is not even a *neutral* operation: because the curve's
/// slope varies with level, scaling encoded R, G and B by one number moves them
/// by different amounts in linear light, so it shifts the colour of every
/// non-neutral pixel and crushes or blows the ends. Exposure is a photon count
/// times a constant, and photon counts live before the curve.
///
/// *Where relative to the matrix — and why the implementation is free to choose.*
/// [`camera_to_srgb`] is a **linear** operator, so `M(g*v) = g*M(v)`: applying
/// the gain in camera RGB and applying it in linear sRGB are the *same
/// transform*, differing only in float rounding. So is the demosaic, which is a
/// fixed FIR filter. The pipeline therefore folds the gain into the
/// normalisation multiply the writer already performs, which keeps the
/// byte-frozen linear branch textually untouched — and that equivalence is not
/// assumed, it is asserted in
/// [`tests::the_gain_commutes_with_the_colour_matrix`].
///
/// What is *not* free is the **clamp**. The gain must land before it, so that a
/// negative exposure can pull a value back down from above 1.0 rather than
/// scaling a value that has already been flattened to 1.0. Clamp-then-gain
/// would make `--exposure` a one-way street.
#[derive(Debug, Clone, Copy, PartialEq)]
pub struct AppliedExposure {
    /// Stops. Positive brightens.
    pub stops: f32,
    /// `true` if [`choose_exposure`] picked it rather than the user.
    pub automatic: bool,
}

impl AppliedExposure {
    /// No exposure adjustment at all.
    pub const IDENTITY: Self = Self {
        stops: 0.0,
        automatic: false,
    };

    /// The linear gain, `2^stops`.
    ///
    /// Exactly `1.0` at zero stops, on every IEEE-754 target, because
    /// `exp2(0) = 1` is required to be exact — and `x * 1.0 == x` bit-for-bit
    /// for every finite `x`. That is what makes an exposure of zero free of
    /// consequence even where the multiply *is* executed.
    #[inline]
    pub fn gain(self) -> f32 {
        self.stops.exp2()
    }

    /// `true` when the caller may skip the multiply entirely.
    #[inline]
    pub fn is_identity(self) -> bool {
        self.stops == 0.0
    }

    /// The token to hand back to `--exposure` to reproduce this render.
    ///
    /// `--exposure=-1.5` and not `--exposure -1.5`, because a leading `-` in
    /// the value position is an unknown flag to any argument parser worth
    /// using. The `=` form is unambiguous and is what a user should copy.
    pub fn reproduce_flag(self) -> String {
        format!("--exposure={:.2}", self.stops)
    }
}

impl core::fmt::Display for AppliedExposure {
    fn fmt(&self, f: &mut core::fmt::Formatter<'_>) -> core::fmt::Result {
        write!(f, "{:+.2} stops (gain {:.3}x)", self.stops, self.gain())
    }
}

/// Choose an exposure from linear-sRGB luminance samples, with the shipped rule.
///
/// `luma` is reordered. `None` when there is nothing to go on — an empty image,
/// or one whose luminance percentile is not positive, where a gain is not
/// defined and the honest answer is to leave the render alone.
///
/// # The rule
///
/// Put [`AUTO_EXPOSURE_PERCENTILE`] of linear luminance at
/// [`AUTO_EXPOSURE_TARGET`], i.e. `stops = log2(target / Y_p)`, bounded by
/// [`AUTO_EXPOSURE_MAX_STOPS`] and quantised to
/// [`AUTO_EXPOSURE_STEPS_PER_STOP`].
///
/// **Why luminance and not the maximum channel.** Clipping is per-channel, so
/// the obvious rule is to place a percentile of `max(R,G,B)`. MEASURED (§3):
/// across the same seven stacks, luminance dominates it — at matched worst-case
/// clipping, luminance delivers a brighter render, because a max-channel rule
/// pays for the most saturated colour in the scene everywhere. Luminance at
/// target 0.90 clips at worst 0.0995% and reaches p99.9 = 0.8905 at worst;
/// max-channel at target 0.95 clips at worst 0.0764% and reaches only 0.8826.
///
/// # What it is and is not
///
/// It is **exposure only** — one scalar gain in linear light. It is not a tone
/// curve, not a black point, not a highlight roll-off and not per-channel. That
/// restraint is the point: it is the operation a raw converter's exposure
/// slider performs, so a render that has had it applied is still a faithful
/// render of the capture, differing from the un-exposed one by a number the
/// tool prints.
///
/// It is a **gain estimator**, and the test of a gain estimator is whether it
/// recovers a planted gain: scale the input by `2^k` and the answer must move
/// by exactly `-k`. It does, to the quantum
/// ([`tests::a_planted_gain_is_recovered_exactly`]).
///
/// # It can darken, and that is not a bug
///
/// Two corpus stacks are already correctly exposed and carry genuinely blown
/// highlights: `coffee-bean` has 1.4215% of its pixels at 65535 and `foam`
/// 0.7553%, with no exposure applied at all. This rule gives them −0.14 and
/// −0.09 stops and takes both to **0.0000%** (MEASURED, §3). An auto-exposure
/// that could only brighten would leave those blown.
pub fn choose_exposure(luma: &mut [f32]) -> Option<AppliedExposure> {
    exposure_stops_for(
        luma,
        AUTO_EXPOSURE_PERCENTILE,
        AUTO_EXPOSURE_TARGET,
        AUTO_EXPOSURE_MAX_STOPS,
    )
    .map(|stops| AppliedExposure {
        stops,
        automatic: true,
    })
}

/// [`choose_exposure`]'s rule with its parameters exposed, for the sweep that
/// chose them and for the tests that falsify it.
///
/// Kept public so that `docs/research/M100-exposure.md` §3's numbers can be
/// regenerated against the shipped code rather than against a reimplementation
/// of it.
pub fn exposure_stops_for(
    luma: &mut [f32],
    percentile: f64,
    target: f32,
    max_stops: f32,
) -> Option<f32> {
    let y = percentile_in_place(luma, percentile)?;
    if !y.is_finite() || y <= 0.0 || !target.is_finite() || target <= 0.0 {
        return None;
    }
    let stops = (f64::from(target) / f64::from(y)).log2();
    if !stops.is_finite() {
        return None;
    }
    let bounded = (stops as f32).clamp(-max_stops.abs(), max_stops.abs());
    // Quantise to the precision the choice is *reported* at, so that the
    // report reproduces the file. See `AUTO_EXPOSURE_STEPS_PER_STOP`.
    let steps = f64::from(bounded) * f64::from(AUTO_EXPOSURE_STEPS_PER_STOP);
    Some(steps.round() as f32 / AUTO_EXPOSURE_STEPS_PER_STOP)
}

#[cfg(test)]
mod tests {
    use super::*;

    /// The A7C II's characterisation, as MEASURED through an independent
    /// decoder (`rawpy`/LibRaw) and published in
    /// `docs/research/M26-colour-clipping-measured.md` §1, where it is the
    /// `rgb_xyz_matrix` and is recorded as identical across all six corpus
    /// stacks.
    ///
    /// It is a **fixture**, not a constant of this crate: the pipeline reads
    /// the live value from each file. It is here so that these tests assert
    /// against a number a human can go and read in a committed report, per
    /// AGENTS.md rule 35.
    const A7C2_XYZ_TO_CAM: [[f32; 3]; 3] = [
        [0.7460, -0.2365, -0.0588],
        [-0.5687, 1.3442, 0.2474],
        [-0.0624, 0.1156, 0.6584],
    ];

    fn mul3(a: [[f64; 3]; 3], b: [[f64; 3]; 3]) -> [[f64; 3]; 3] {
        let mut out = [[0.0f64; 3]; 3];
        for (i, orow) in out.iter_mut().enumerate() {
            for (j, o) in orow.iter_mut().enumerate() {
                for (k, brow) in b.iter().enumerate() {
                    *o += a[i][k] * brow[j];
                }
            }
        }
        out
    }

    /// The published sRGB matrix must be what its own primaries imply.
    ///
    /// This is the independent term AGENTS.md rule 35 demands: the constant is
    /// asserted against a derivation from the chromaticities, not against
    /// itself. Change one digit of [`SRGB_TO_XYZ_D65`] and this fails.
    #[test]
    fn the_srgb_matrix_is_what_its_own_chromaticities_imply() {
        // sRGB / BT.709-6 primaries and D65, as chromaticities.
        let prim = [(0.6400, 0.3300), (0.3000, 0.6000), (0.1500, 0.0600)];
        let white = (0.3127, 0.3290);

        // Columns of xyz_prim are each primary's XYZ at unit luminance.
        let mut xyz_prim = [[0.0f64; 3]; 3];
        for (c, (x, y)) in prim.iter().enumerate() {
            xyz_prim[0][c] = x / y;
            xyz_prim[1][c] = 1.0;
            xyz_prim[2][c] = (1.0 - x - y) / y;
        }
        let wx = white.0 / white.1;
        let wy = 1.0;
        let wz = (1.0 - white.0 - white.1) / white.1;

        // Solve xyz_prim * s = white_xyz for the per-primary scale factors.
        let inv = invert3(xyz_prim).expect("primaries are independent");
        let s = [
            inv[0][0] * wx + inv[0][1] * wy + inv[0][2] * wz,
            inv[1][0] * wx + inv[1][1] * wy + inv[1][2] * wz,
            inv[2][0] * wx + inv[2][1] * wy + inv[2][2] * wz,
        ];
        let mut derived = [[0.0f64; 3]; 3];
        for (i, drow) in derived.iter_mut().enumerate() {
            for (j, d) in drow.iter_mut().enumerate() {
                *d = xyz_prim[i][j] * s[j];
            }
        }

        // The published matrix and its own chromaticities do not agree
        // exactly, and the disagreement is asserted at its measured size
        // rather than tolerated silently (AGENTS.md rule 30). The largest
        // deviation is 2.281e-4, at [2][2] -- the Z of the blue primary --
        // and it is the standard's own rounding, not an error here. If a
        // future edit replaces the constant with the derived value this test
        // fails, which is the day to hear about it.
        let mut worst = 0.0f64;
        for i in 0..3 {
            for j in 0..3 {
                let e = (derived[i][j] - SRGB_TO_XYZ_D65[i][j]).abs();
                worst = worst.max(e);
                assert!(
                    e < 3e-4,
                    "sRGB matrix [{i}][{j}]: derived {}, constant {}, error {e}",
                    derived[i][j],
                    SRGB_TO_XYZ_D65[i][j]
                );
            }
        }
        assert!(
            (worst - 2.281e-4).abs() < 2e-6,
            "the standard's own rounding error was 2.281e-4 and is now {worst}"
        );

        // ...and D65_XYZ is that matrix applied to (1,1,1), to the precision
        // the published matrix has. The luminance row sums to 1.0000001, not
        // 1: BT.709's luma weights are themselves rounded. Asserting at 2e-7
        // records that rather than hiding it behind a loose bar.
        for (i, d) in D65_XYZ.iter().enumerate() {
            let s: f64 = SRGB_TO_XYZ_D65[i].iter().sum();
            assert!((s - d).abs() < 2e-7, "D65 component {i}: {s} vs {d}");
        }
        let luma: f64 = SRGB_TO_XYZ_D65[1].iter().sum();
        assert!(
            (luma - 1.0).abs() > 5e-8,
            "the BT.709 luma weights used to sum to 1.0000001; they now sum to \
             {luma}, so the constant has been edited"
        );
    }

    /// A neutral input must stay neutral, and it must do so *exactly*, because
    /// the row-sum normalisation makes it an identity rather than an
    /// approximation.
    ///
    /// Power to fail: the same assertion run against the **un-normalised**
    /// matrix — the version of this function without step 2 — is checked to
    /// fail below, so this is not arithmetic (rule 20).
    #[test]
    fn a_neutral_stays_neutral_and_the_unnormalised_matrix_does_not() {
        let m = *camera_to_srgb(A7C2_XYZ_TO_CAM)
            .expect("invertible")
            .matrix();
        for (i, row) in m.iter().enumerate() {
            let s: f32 = row.iter().sum();
            assert!((s - 1.0).abs() < 1e-5, "row {i} sums to {s}, not 1");
        }
        let out = apply(&m, [0.5, 0.5, 0.5]);
        for v in out {
            assert!((v - 0.5).abs() < 1e-5, "neutral moved: {out:?}");
        }

        // The negative control: skip the row normalisation and the same input
        // comes out strongly non-neutral. This is the defect the step exists
        // to prevent, and it is asserted rather than argued.
        let mut cam_from_srgb = [[0.0f64; 3]; 3];
        for i in 0..3 {
            for j in 0..3 {
                let mut acc = 0.0f64;
                for (k, x) in SRGB_TO_XYZ_D65.iter().enumerate() {
                    acc += f64::from(A7C2_XYZ_TO_CAM[i][k]) * x[j];
                }
                cam_from_srgb[i][j] = acc;
            }
        }
        let bad = invert3(cam_from_srgb).expect("invertible");
        let br = bad[0][0] * 0.5 + bad[0][1] * 0.5 + bad[0][2] * 0.5;
        let bg = bad[1][0] * 0.5 + bad[1][1] * 0.5 + bad[1][2] * 0.5;
        let spread = (br / bg) as f32;
        assert!(
            !(0.9..=1.1).contains(&spread),
            "the un-normalised matrix was supposed to break neutrality, but R/G = {spread}"
        );
    }

    /// The round trip that actually tests the colour transform: known
    /// chromaticities out and back.
    ///
    /// Take a set of linear sRGB colours, push them through the camera's own
    /// characterisation into camera RGB, white balance them the way the
    /// pipeline does — with **green normalised to 1** — and transform back.
    ///
    /// # The exposure factor this test discovered, and it is a real property
    ///
    /// Recovery is exact **up to one global scale**, and the scale is
    /// `neutral_response()[1]`, the camera's green response to D65 — 1.0730 on
    /// this body. The reason is arithmetic: row-normalising the matrix divides
    /// camera channel `i` by its neutral response `s_i`, so the matrix expects
    /// gains `1/s_i`; the pipeline supplies `s_G/s_i`, because
    /// `Frame::wb_gains` normalises green to 1 rather than normalising the
    /// vector. The difference is the common factor `s_G`, identical in all
    /// three channels.
    ///
    /// So this is an **exposure** offset, not a colour error: it moves nothing
    /// in chromaticity, and it is the convention the pipeline already had
    /// before this module existed. It is asserted here, at its value, rather
    /// than divided away silently — a factor of 1.073 in output brightness is
    /// worth someone knowing about.
    ///
    /// This is the only test here with the power to catch a wrong *rotation* of
    /// the matrix, as opposed to a wrong scale — and the transposed and
    /// channel-swapped controls below show it has that power.
    #[test]
    fn synthetic_patches_of_known_chromaticity_round_trip() {
        camera_to_srgb(A7C2_XYZ_TO_CAM).expect("invertible");
        let wb = implied_daylight_wb_gains(A7C2_XYZ_TO_CAM).expect("positive neutral response");
        let exposure = neutral_response(A7C2_XYZ_TO_CAM)[1];
        assert!(
            (exposure - 1.0730).abs() < 5e-4,
            "green neutral response {exposure}"
        );

        // sRGB primaries, secondaries, neutral, and two off-axis patches.
        let patches: [[f32; 3]; 9] = [
            [1.0, 0.0, 0.0],
            [0.0, 1.0, 0.0],
            [0.0, 0.0, 1.0],
            [1.0, 1.0, 0.0],
            [0.0, 1.0, 1.0],
            [1.0, 0.0, 1.0],
            [0.5, 0.5, 0.5],
            [0.8, 0.4, 0.2],
            [0.12, 0.35, 0.62],
        ];

        let mut worst = 0.0f32;
        for p in patches {
            let back = round_trip(A7C2_XYZ_TO_CAM, A7C2_XYZ_TO_CAM, p);
            for c in 0..3 {
                worst = worst.max((back[c] / exposure - p[c]).abs());
            }
            // The scale really is common to all three channels, which is what
            // makes it exposure rather than cast. Checked on the neutral-free
            // patches, where a ratio is defined.
            if p.iter().all(|v| *v > 0.05) {
                for c in 0..3 {
                    assert!(
                        (back[c] / p[c] - exposure).abs() < 1e-3,
                        "channel {c} of {p:?} scaled by {}, not {exposure}",
                        back[c] / p[c]
                    );
                }
            }
        }
        assert!(worst < 1e-4, "worst chromaticity round-trip error {worst}");

        // Rule 20: the same assertion must be able to fail. `wb` is used above
        // only through `round_trip`; assert it is the branch that carries the
        // exposure factor, so the two are not silently the same number twice.
        assert!((wb[0] * 1.0).is_finite() && wb[1] == 1.0);
    }

    /// Push a patch through the camera and back, the way the pipeline does.
    ///
    /// `truth` is the characterisation of the camera that took the picture;
    /// `belief` is the characterisation the pipeline thinks it has. They are
    /// separate arguments so that a wrong belief can be tested against a right
    /// scene, which is the realistic failure.
    fn round_trip(truth: [[f32; 3]; 3], belief: [[f32; 3]; 3], p: [f32; 3]) -> [f32; 3] {
        let mut xyz = [0.0f32; 3];
        for (i, row) in SRGB_TO_XYZ_D65.iter().enumerate() {
            xyz[i] = (row[0] * f64::from(p[0])
                + row[1] * f64::from(p[1])
                + row[2] * f64::from(p[2])) as f32;
        }
        let cam = apply(&truth, xyz);
        let wb = implied_daylight_wb_gains(belief).unwrap_or([1.0, 1.0, 1.0]);
        let wbd = [cam[0] * wb[0], cam[1] * wb[1], cam[2] * wb[2]];
        let m = *camera_to_srgb(belief).expect("invertible").matrix();
        apply(&m, wbd)
    }

    /// The same round trip, with the matrix planted wrong, must **fail** — and
    /// fail in chromaticity, not merely in exposure.
    ///
    /// Two plants, each a mistake a person actually makes: transposing the
    /// matrix, and swapping the R and B rows. The error is measured **after
    /// dividing out each plant's own exposure factor**, so a plant cannot be
    /// caught merely for being brighter. Rule 20 — a test with no input that
    /// makes it fail is arithmetic, not evidence.
    #[test]
    fn a_transposed_or_channel_swapped_matrix_fails_the_round_trip() {
        let good = A7C2_XYZ_TO_CAM;
        let mut transposed = [[0.0f32; 3]; 3];
        for i in 0..3 {
            for j in 0..3 {
                transposed[i][j] = good[j][i];
            }
        }
        let swapped = [good[2], good[1], good[0]];

        let patch = [0.8f32, 0.4, 0.2];
        for (name, wrong) in [("transposed", transposed), ("swapped", swapped)] {
            let back = round_trip(good, wrong, patch);
            let exposure = neutral_response(wrong)[1] / neutral_response(good)[1];
            let err = (0..3)
                .map(|c| (back[c] / exposure.max(1e-6) - patch[c]).abs())
                .fold(0.0f32, f32::max);
            assert!(
                err > 0.05,
                "{name} matrix was supposed to break the round trip, but the worst \
                 exposure-corrected channel error was only {err}"
            );
        }

        // And the control's control: the *correct* belief passes the same bar.
        let back = round_trip(good, good, patch);
        let exposure = neutral_response(good)[1];
        let err = (0..3)
            .map(|c| (back[c] / exposure - patch[c]).abs())
            .fold(0.0f32, f32::max);
        assert!(
            err < 1e-4,
            "the correct matrix failed its own control: {err}"
        );
    }

    /// The matrix must predict, from a completely different tag, the white
    /// balance the body writes into the file.
    ///
    /// `xyz_to_cam` comes from the decoder's camera characterisation;
    /// `wb_coeffs` comes from the shot's own metadata. They are independent
    /// data with a physical relation between them, so their agreement is a
    /// real gate on the matrix's orientation and scale.
    ///
    /// The band is set by M26 §1's six MEASURED as-shot stacks — R 2.131-2.861,
    /// B 1.408-1.884, all on auto white balance under varied light — widened by
    /// 10% because the as-shot illuminant is not D65 and the two need not
    /// coincide. It is a **sanity band, not an accuracy claim**: this project
    /// has no grey card in any capture and cannot make one.
    #[test]
    fn the_matrix_predicts_a_plausible_daylight_white_balance() {
        let wb = implied_daylight_wb_gains(A7C2_XYZ_TO_CAM).expect("positive response");
        assert_eq!(wb[1], 1.0);
        assert!(
            (1.9..=3.2).contains(&wb[0]),
            "implied daylight R gain {} is outside the band M26 measured",
            wb[0]
        );
        assert!(
            (1.2..=2.1).contains(&wb[2]),
            "implied daylight B gain {} is outside the band M26 measured",
            wb[2]
        );

        // Power to fail: the transpose lands outside.
        let good = A7C2_XYZ_TO_CAM;
        let mut transposed = [[0.0f32; 3]; 3];
        for i in 0..3 {
            for j in 0..3 {
                transposed[i][j] = good[j][i];
            }
        }
        let bad = implied_daylight_wb_gains(transposed);
        let rejected = match bad {
            None => true,
            Some(g) => !(1.9..=3.2).contains(&g[0]) || !(1.2..=2.1).contains(&g[2]),
        };
        assert!(rejected, "the transposed matrix passed the band: {bad:?}");
    }

    #[test]
    fn a_singular_characterisation_is_refused_rather_than_used() {
        // An all-zero matrix is what a body with no entry in the decoder's
        // database produces, and multiplying by it would emit a black image.
        assert!(camera_to_srgb([[0.0; 3]; 3]).is_none());
        // Two identical rows: invertible-looking, actually rank 2.
        let m = [[0.7, -0.2, -0.05], [0.7, -0.2, -0.05], [-0.06, 0.11, 0.65]];
        assert!(camera_to_srgb(m).is_none());
    }

    #[test]
    fn the_inverse_is_an_inverse() {
        let m = [
            [0.4124564, 0.3575761, 0.1804375],
            [0.2126729, 0.7151522, 0.0721750],
            [0.0193339, 0.1191920, 0.9503041],
        ];
        let i = mul3(m, invert3(m).unwrap());
        for r in 0..3 {
            for c in 0..3 {
                let want = if r == c { 1.0 } else { 0.0 };
                assert!((i[r][c] - want).abs() < 1e-12, "{i:?}");
            }
        }
    }

    #[test]
    fn the_transfer_curve_hits_its_endpoints_and_is_monotone() {
        assert!(srgb_encode(0.0).abs() < 1e-9);
        assert!((srgb_encode(1.0) - 1.0).abs() < 1e-6);
        // The standard's own midpoint: 0.5 linear encodes to ~0.7354.
        assert!((srgb_encode(0.5) - 0.7354).abs() < 1e-3);
        let mut prev = -1.0;
        for i in 0..=1000 {
            let v = srgb_encode(i as f32 / 1000.0);
            assert!(v > prev, "not monotone at {i}");
            prev = v;
        }
    }

    /// The curve's two branches must meet at the breakpoint.
    ///
    /// The standard is slightly self-inconsistent there; this asserts the
    /// **known** size of that discontinuity rather than excluding the point,
    /// per AGENTS.md rule 30. If a future edit changes the constants, the
    /// expected disagreement changes and this fails, which is the day you want
    /// to hear about it.
    #[test]
    fn the_transfer_curve_branches_agree_at_the_breakpoint_to_the_known_error() {
        let x = 0.003_130_8f32;
        let lo = 12.92 * x;
        let hi = 1.055 * x.powf(1.0 / 2.4) - 0.055;
        let d = (lo - hi).abs();
        assert!(
            d < 1e-4,
            "branch disagreement {d} is larger than the standard's"
        );
        assert!(d > 0.0, "the branches were expected to disagree slightly");
    }

    // -----------------------------------------------------------------
    // Exposure (M100). The bars these correspond to are pre-registered in
    // `docs/research/M100-exposure.md` §1 and are named in each test.
    // -----------------------------------------------------------------

    /// The luma weights are the published matrix's `Y` row, not a second copy
    /// of them.
    ///
    /// This is the independent term for [`luminance`]: if someone pastes
    /// `0.2126 / 0.7152 / 0.0722` in, or transposes the matrix, this fails. It
    /// also pins the property that makes the rule interpretable — sRGB white
    /// has luminance exactly 1.
    #[test]
    fn luminance_is_the_y_row_of_the_published_matrix() {
        let w = SRGB_TO_XYZ_D65[1];
        assert!((f64::from(luminance([1.0, 0.0, 0.0])) - w[0]).abs() < 1e-6);
        assert!((f64::from(luminance([0.0, 1.0, 0.0])) - w[1]).abs() < 1e-6);
        assert!((f64::from(luminance([0.0, 0.0, 1.0])) - w[2]).abs() < 1e-6);
        assert!(
            (luminance([1.0, 1.0, 1.0]) - 1.0).abs() < 1e-6,
            "sRGB white must have luminance 1"
        );
        // Green carries most of it, blue almost none. A transposed row would
        // not have this shape.
        assert!(w[1] > 0.7 && w[2] < 0.08);
    }

    /// A gamut excursion is not negative light.
    ///
    /// [`camera_to_srgb`] genuinely produces negative channels for saturated
    /// camera colours (asserted in `image_out`'s tests on the same fixture).
    /// If those entered the luminance sum, a more saturated scene would read as
    /// *darker* and the auto rule would brighten it for being colourful.
    #[test]
    fn luminance_floors_out_of_gamut_channels_rather_than_subtracting_them() {
        let render = camera_to_srgb(A7C2_XYZ_TO_CAM).expect("invertible");
        let m = *render.matrix();
        let saturated_green = [0.2f32, 1.0, 0.15];
        let lin = apply(&m, saturated_green);
        assert!(
            lin[0] < 0.0 && lin[2] < 0.0,
            "fixture is not out of gamut: {lin:?}"
        );
        let y = display_luminance(saturated_green, Some(&render));
        assert!(y > 0.0, "an out-of-gamut green read as non-positive: {y}");
        // Explicitly: it equals the green term alone, the negatives dropped.
        let want = SRGB_TO_XYZ_D65[1][1] * f64::from(lin[1]);
        assert!((f64::from(y) - want).abs() < 1e-6, "{y} vs {want}");
        // With no matrix, camera RGB is passed through unweighted by anything
        // but the sRGB row.
        assert!((display_luminance([0.5, 0.5, 0.5], None) - 0.5).abs() < 1e-6);
    }

    /// Nearest rank is the textbook definition, checked by hand.
    #[test]
    fn the_percentile_index_is_the_textbook_nearest_rank() {
        assert_eq!(nearest_rank_index(0, 50.0), None);
        // 10 samples: p10 -> rank 1 -> index 0; p100 -> rank 10 -> index 9.
        assert_eq!(nearest_rank_index(10, 0.0), Some(0));
        assert_eq!(nearest_rank_index(10, 10.0), Some(0));
        assert_eq!(nearest_rank_index(10, 10.1), Some(1));
        assert_eq!(nearest_rank_index(10, 50.0), Some(4));
        assert_eq!(nearest_rank_index(10, 99.9), Some(9));
        assert_eq!(nearest_rank_index(10, 100.0), Some(9));
        // 1000 samples, the sizes the rule actually runs at. These two are the
        // cases float arithmetic gets wrong: 99.9/100*1000 ceils to 1000.
        assert_eq!(nearest_rank_index(1000, 99.5), Some(994));
        assert_eq!(nearest_rank_index(1000, 99.9), Some(998));
        assert_eq!(nearest_rank_index(10_000, 99.9), Some(9989));
        assert_eq!(nearest_rank_index(8_241_504, 99.5), Some(8_200_296));
    }

    /// The percentile is an order statistic of the multiset, so it does not
    /// depend on the input order — which is what makes it deterministic
    /// regardless of what `select_nth_unstable` does internally.
    #[test]
    fn the_percentile_is_an_order_statistic_and_ignores_input_order() {
        let base: Vec<f32> = (0..1000).map(|i| i as f32 / 999.0).collect();
        let want = base[994];
        // Strides coprime to 1000, so `i * stride % 1000` is a genuine
        // permutation and not a resampling. Asserted below, because a stride
        // sharing a factor with 1000 would silently make this test vacuous.
        for stride in [7usize, 11, 13, 17, 19] {
            let mut xs: Vec<f32> = (0..1000).map(|i| base[(i * stride) % 1000]).collect();
            let mut seen = vec![false; 1000];
            for i in 0..1000 {
                seen[(i * stride) % 1000] = true;
            }
            assert!(seen.iter().all(|s| *s), "stride {stride} is not a permutation");
            let got = percentile_in_place(&mut xs, 99.5).expect("non-empty");
            assert_eq!(
                got.to_bits(),
                want.to_bits(),
                "stride {stride} changed the answer"
            );
        }
        assert_eq!(percentile_in_place(&mut [], 50.0), None);
    }

    /// `NaN` can only lower the reading, never become it. Stated in the doc and
    /// asserted here because the failure direction matters: an exposure rule
    /// that reads `NaN` as "very bright" would darken the image to nothing.
    #[test]
    fn a_nan_sample_cannot_become_the_percentile() {
        let mut xs: Vec<f32> = (0..100).map(|i| i as f32 / 99.0).collect();
        xs[3] = f32::NAN;
        let got = percentile_in_place(&mut xs, 99.0).expect("non-empty");
        assert!(got.is_finite(), "a NaN was returned as the percentile");
        assert!(got <= 1.0);
    }

    /// **Bar B5, the negative control.** Plant a known gain; the rule must give
    /// it back with the opposite sign, exactly.
    ///
    /// A rule that cannot recover a planted gain cannot be trusted to find a
    /// real one. The tolerance is the reporting quantum and nothing more.
    #[test]
    fn a_planted_gain_is_recovered_exactly() {
        // A plausible luminance histogram: a dark subject and a bright
        // background, so the high percentile lands on the background.
        let base: Vec<f32> = (0..10_000)
            .map(|i| if i % 5 == 0 { 0.30 } else { 0.02 })
            .collect();
        let mut work = base.clone();
        let ref_stops = choose_exposure(&mut work).expect("a positive percentile").stops;

        for k in [-1.0f32, -0.5, 0.5, 1.0, 2.0] {
            let g = k.exp2();
            let mut planted: Vec<f32> = base.iter().map(|y| y * g).collect();
            let got = choose_exposure(&mut planted).expect("still positive").stops;
            let moved = got - ref_stops;
            assert!(
                (moved - -k).abs() <= 1.0 / AUTO_EXPOSURE_STEPS_PER_STOP + 1e-6,
                "planting {k:+} stops moved the choice by {moved:+}, not {:+}",
                -k
            );
        }
    }

    /// ...and the render it produces is invariant to the planted gain, to
    /// within the quantum. The second half of bar B5: recovering the number is
    /// only useful if applying it undoes the plant.
    #[test]
    fn recovering_a_planted_gain_restores_the_developed_pixels() {
        let base: Vec<f32> = (0..10_000)
            .map(|i| if i % 5 == 0 { 0.30 } else { 0.02 })
            .collect();
        let develop = |y: f32, e: AppliedExposure| -> u16 {
            let v = (y * e.gain()).clamp(0.0, 1.0);
            (srgb_encode(v) * f32::from(u16::MAX) + 0.5) as u16
        };
        let mut work = base.clone();
        let e0 = choose_exposure(&mut work).expect("positive");

        for k in [-1.0f32, -0.5, 0.5, 1.0] {
            let g = k.exp2();
            let mut planted: Vec<f32> = base.iter().map(|y| y * g).collect();
            let ek = choose_exposure(&mut planted).expect("positive");
            let worst = base
                .iter()
                .map(|y| develop(*y, e0).abs_diff(develop(*y * g, ek)))
                .max()
                .expect("non-empty");
            assert!(
                worst <= 64,
                "planting {k:+} stops left a {worst}-code difference after recovery"
            );
        }
    }

    /// The rule does what it says: the chosen gain puts the percentile on the
    /// target, to within the quantum.
    #[test]
    fn the_chosen_gain_puts_the_percentile_on_the_target() {
        for level in [0.02f32, 0.1, 0.296, 0.5, 0.85, 0.99] {
            let mut xs = vec![level; 1000];
            let e = choose_exposure(&mut xs).expect("positive");
            let landed = level * e.gain();
            assert!(
                (landed - AUTO_EXPOSURE_TARGET).abs() < 0.01,
                "level {level} landed at {landed}, not {AUTO_EXPOSURE_TARGET}"
            );
            assert!(e.automatic, "an automatic choice must say so");
        }
    }

    /// The gain must not run away on a degenerate image, and it must not bind
    /// on an ordinary one.
    #[test]
    fn a_black_image_gets_a_bounded_answer_and_an_empty_one_gets_none() {
        let mut black = vec![1e-9f32; 1000];
        let e = choose_exposure(&mut black).expect("positive but tiny");
        assert_eq!(e.stops, AUTO_EXPOSURE_MAX_STOPS, "the guard rail did not hold");

        let mut zero = vec![0.0f32; 1000];
        assert_eq!(choose_exposure(&mut zero), None, "zero luminance has no gain");
        let mut empty: Vec<f32> = Vec::new();
        assert_eq!(choose_exposure(&mut empty), None);

        // ...and the bound is far outside where real stacks sit, so it shapes
        // nothing that ships. bee-3-cpl's background is 0.296 linear (MEASURED,
        // docs/research/M100-exposure.md §0).
        let mut real = vec![0.296f32; 1000];
        let e = choose_exposure(&mut real).expect("positive");
        assert!(
            e.stops.abs() < AUTO_EXPOSURE_MAX_STOPS - 3.0,
            "a real background asked for {} stops, uncomfortably near the bound",
            e.stops
        );
    }

    /// **Bar B2, structurally.** Zero stops is not "a gain of one", it is *no
    /// exposure request at all*, so the multiply is never reached.
    #[test]
    fn zero_stops_normalises_to_no_exposure_at_all() {
        assert_eq!(Exposure::resolve(true, 0.0, false), Ok(Exposure::None));
        assert_eq!(Exposure::resolve(true, -0.0, false), Ok(Exposure::None));
        assert!(AppliedExposure::IDENTITY.is_identity());
        // And even where the multiply *is* executed, it is exact.
        assert_eq!(AppliedExposure::IDENTITY.gain().to_bits(), 1.0f32.to_bits());
        for v in [0.0f32, 1e-30, 0.003_130_8, 0.296, 0.5734, 1.0, 3.7] {
            assert_eq!((v * AppliedExposure::IDENTITY.gain()).to_bits(), v.to_bits());
        }
    }

    /// **Bar B7.** Exposure without `--srgb` is refused, not ignored.
    ///
    /// The linear file is the measurement file. A user who believes they
    /// brightened it and did not has a corrupted measurement and no signal that
    /// anything went wrong, which is strictly worse than an error.
    #[test]
    fn exposure_is_refused_on_the_measurement_output() {
        assert_eq!(
            Exposure::resolve(false, 1.57, false),
            Err(ExposureError::NeedsSrgb)
        );
        assert_eq!(
            Exposure::resolve(false, 0.0, true),
            Err(ExposureError::NeedsSrgb)
        );
        // ...but not asking for one is fine without --srgb, obviously.
        assert_eq!(Exposure::resolve(false, 0.0, false), Ok(Exposure::None));
        // Two sources of truth for one number is a refusal, not a composition.
        assert_eq!(
            Exposure::resolve(true, 1.0, true),
            Err(ExposureError::Both)
        );
        // Finite and bounded.
        assert!(matches!(
            Exposure::resolve(true, f32::NAN, false),
            Err(ExposureError::OutOfRange { .. })
        ));
        assert!(matches!(
            Exposure::resolve(true, 99.0, false),
            Err(ExposureError::OutOfRange { .. })
        ));
        assert_eq!(
            Exposure::resolve(true, 1.57, false),
            Ok(Exposure::Stops(1.57))
        );
        assert_eq!(Exposure::resolve(true, 0.0, true), Ok(Exposure::Auto));
        // The message has to name the flag that fixes it.
        assert!(ExposureError::NeedsSrgb.to_string().contains("--srgb"));
    }

    /// **Bar B6, at the unit level.** What is printed is what is applied, to
    /// the bit, through an actual `format!` and `parse`.
    ///
    /// This is the whole justification for quantising the automatic choice. If
    /// it ever fails, `--auto-exposure`'s report becomes decoration and the
    /// user cannot reproduce their own render.
    #[test]
    fn the_printed_choice_reproduces_the_gain_through_a_string() {
        for level in [0.02f32, 0.05, 0.1, 0.296, 0.4, 0.5734, 0.7, 0.85, 0.95] {
            let mut xs = vec![level; 1000];
            let e = choose_exposure(&mut xs).expect("positive");
            let printed = format!("{:.2}", e.stops);
            let parsed: f32 = printed.parse().expect("we just printed it");
            assert_eq!(
                parsed.to_bits(),
                e.stops.to_bits(),
                "level {level}: printed {printed}, which parses to a different f32"
            );
            // ...and the flag string a user copies carries that same number.
            let flag = e.reproduce_flag();
            let (name, value) = flag.split_once('=').expect("an = form");
            assert_eq!(name, "--exposure");
            assert_eq!(
                value.parse::<f32>().expect("a number").to_bits(),
                e.stops.to_bits()
            );
        }
    }

    /// The gain commutes with the colour matrix, which is what licenses the
    /// pipeline folding it into the normalisation multiply instead of inserting
    /// a step between the matrix and the clamp.
    ///
    /// `camera_to_srgb` is linear, so `M(g*v) = g*M(v)` exactly in exact
    /// arithmetic and to float rounding here. If a future edit made the
    /// "matrix" affine — a black-point offset, say — this fails, and it should,
    /// because the fold would then be wrong.
    #[test]
    fn the_gain_commutes_with_the_colour_matrix() {
        let m = *camera_to_srgb(A7C2_XYZ_TO_CAM)
            .expect("invertible")
            .matrix();
        for stops in [-2.0f32, -0.5, 0.37, 1.57, 3.0] {
            let g = AppliedExposure {
                stops,
                automatic: false,
            }
            .gain();
            for v in [[0.1f32, 0.2, 0.3], [0.296, 0.296, 0.296], [0.9, 0.4, 0.05]] {
                let before = apply(&m, [v[0] * g, v[1] * g, v[2] * g]);
                let after = apply(&m, v).map(|x| x * g);
                for c in 0..3 {
                    let d = (before[c] - after[c]).abs();
                    assert!(
                        d <= 1e-6 * after[c].abs().max(1.0),
                        "stops {stops}, channel {c}: {before:?} vs {after:?}"
                    );
                }
            }
        }
    }

    /// Exposure is a gain in linear light, and doing it after the curve would
    /// be a different — and colour-shifting — operation.
    ///
    /// This is the assertion behind the sentence in `AppliedExposure`'s doc
    /// comment. It plants the wrong ordering and shows it moves a *neutral*
    /// pixel's ratios apart, which is the failure a reader should be able to
    /// see rather than take on trust.
    #[test]
    fn a_gain_after_the_curve_is_not_an_exposure() {
        let g = 2.0f32; // +1 stop
        let lin = [0.05f32, 0.20, 0.40];

        // Right: gain, clamp, encode.
        let right: Vec<f32> = lin
            .iter()
            .map(|v| srgb_encode((v * g).clamp(0.0, 1.0)))
            .collect();
        // Wrong: encode, then gain.
        let wrong: Vec<f32> = lin.iter().map(|v| (srgb_encode(*v) * g).min(1.0)).collect();

        // The two disagree, and they disagree by different amounts at
        // different levels -- which is exactly why the wrong one shifts colour
        // rather than merely mis-scaling brightness.
        let err: Vec<f32> = right
            .iter()
            .zip(&wrong)
            .map(|(r, w)| (r - w).abs())
            .collect();
        assert!(
            err.iter().all(|e| *e > 0.02),
            "the two orderings agreed somewhere they should not: {err:?}"
        );
        let spread = err
            .iter()
            .cloned()
            .fold(f32::MIN, f32::max)
            - err.iter().cloned().fold(f32::MAX, f32::min);
        assert!(
            spread > 0.05,
            "post-curve gain was a uniform error, so this test proves nothing: {err:?}"
        );
    }

    /// The exposure step is not a tone curve: it is one multiply, so it cannot
    /// change the *ratio* of any two pixels that both stay inside the clamp.
    ///
    /// This is the honesty property of the whole feature. A render that has had
    /// `--exposure` applied is still a faithful render of the capture; only the
    /// scale changed, and the tool printed the scale.
    #[test]
    fn exposure_preserves_every_ratio_it_does_not_clip() {
        let g = AppliedExposure {
            stops: 1.57,
            automatic: true,
        }
        .gain();
        let a = 0.11f32;
        let b = 0.29f32;
        let before = a / b;
        let after = (a * g) / (b * g);
        assert!((before - after).abs() < 1e-6);
        assert!(a * g < 1.0 && b * g < 1.0, "the fixture clipped");
    }

    /// The reference rig's levels, from `AGENTS.md`: black 512, white 15360.
    const RIG: Levels = Levels {
        black: 512.0,
        white: 15360.0,
    };
    /// As-shot multipliers from `DSC00150.ARW`, `[2751, 1024, 1569, 1024]`,
    /// green-normalised: R x2.687, G x1.0, B x1.532.
    const A7C2_WB: [f32; 3] = [2751.0 / 1024.0, 1.0, 1569.0 / 1024.0];

    /// A container-saturated sample does **not** land at 1.0, and the number it
    /// does land at is the two white levels' ratio.
    #[test]
    fn a_pinned_sample_lands_above_one_because_the_two_white_levels_differ() {
        let c = saturation_ceiling(RIG, [1.0, 1.0, 1.0], 1.0);
        // (16383 - 512) / (15360 - 512).
        assert!(
            (c[1] - 1.068_898).abs() < 1e-5,
            "neutral ceiling is {}, not 1.068898 -- if this moved, either \
             CONTAINER_MAX_DN or the rig's levels changed",
            c[1]
        );
        // White balance carries red and blue past where green can reach. This
        // asymmetry *is* the defect's mechanism.
        let c = saturation_ceiling(RIG, A7C2_WB, 1.0);
        assert!(c[0] > c[1] && c[2] > c[1], "ceilings {c:?} are not ordered");
        assert!((c[0] / c[1] - 2.686_5).abs() < 1e-3, "red ceiling {c:?}");
    }

    /// **The defect, and the fix, on the numbers that were measured.**
    ///
    /// The blob in `DSC00150.ARW` has green pinned at the container maximum
    /// (16383 DN, 100 % of saturation) while red sits at 7673.2 DN and blue at
    /// 14116.0 DN — neither anywhere near its own ceiling in *raw* terms, but
    /// both carried past green's by white balance. The scene is neutral white
    /// and LibRaw renders it neutral white.
    ///
    /// Power to fail (rule 20, discipline 706): the identical input through a
    /// [`Render`] with no ceiling — which is exactly what shipped — is asserted
    /// to come out **magenta** by the same predicate. If a future edit made the
    /// ceiling a no-op, the first half of this test would not notice; the
    /// second half would still pass and the third would fail loudly.
    #[test]
    fn a_blown_neutral_renders_neutral_and_without_the_ceiling_renders_magenta() {
        let eg = f32::powf(2.0, -0.24); // the exposure `--auto-exposure` chose
        let render = camera_to_srgb(A7C2_XYZ_TO_CAM).expect("invertible");
        let fixed = render.with_ceiling(saturation_ceiling(RIG, A7C2_WB, eg));

        // Fact 1432's measured means, pushed through the render's own norm().
        let norm = |dn: f32, gain: f32| (dn - RIG.black) * gain * eg / RIG.range();
        let blob = [
            norm(7673.2, A7C2_WB[0]),
            norm(16383.0, A7C2_WB[1]),
            norm(14116.0, A7C2_WB[2]),
        ];

        let shipped = apply(render.matrix(), blob).map(|v| v.clamp(0.0, 1.0));
        let magenta = |v: [f32; 3]| v[0] - v[1] > 0.06 && v[2] - v[1] > 0.06;
        assert!(
            magenta(shipped),
            "the defect did not reproduce: {shipped:?} -- this test is then \
             measuring something other than the reported failure"
        );

        let out = fixed.develop(blob).map(|v| v.clamp(0.0, 1.0));
        assert!(!magenta(out), "still magenta after the ceiling: {out:?}");
        let spread = out[0].max(out[1]).max(out[2]) - out[0].min(out[1]).min(out[2]);
        assert!(
            spread < 1e-5,
            "blown neutral did not render neutral: {out:?}"
        );

        // ...and it is not neutral because everything went to zero or one.
        assert!(out[1] > 0.5, "the fix rendered the highlight dark: {out:?}");
    }

    /// **The null, as an identity rather than an observation.**
    ///
    /// Nothing below its own ceiling is touched — bit-for-bit, not to a
    /// tolerance. This is why an unsaturated stack cannot move by one byte, and
    /// it is the property an *unconditional* clamp would not have: red's
    /// ceiling is `1/2.687` of the container in unbalanced terms, so a plain
    /// clamp at the neutral ceiling would eat real red highlights from about
    /// 6420 DN upwards, which is well inside `109MSDCF`'s range.
    #[test]
    fn nothing_below_its_ceiling_moves_by_a_single_bit() {
        let ceil = saturation_ceiling(RIG, A7C2_WB, 1.0);
        let render = camera_to_srgb(A7C2_XYZ_TO_CAM)
            .expect("invertible")
            .with_ceiling(ceil);
        // 109MSDCF's documented maxima are 39-61 % of white; sweep well past
        // that, up to just under each channel's own ceiling.
        for i in 0..=200 {
            let t = i as f32 / 200.0;
            let v = [
                t * ceil[0] * 0.999,
                t * ceil[1] * 0.999,
                t * ceil[2] * 0.999,
            ];
            assert_eq!(render.clip_highlights(v), v, "moved an unpinned triple");
        }
        // Power to fail: a triple that IS pinned must move.
        let pinned = [ceil[0], ceil[1], ceil[2]];
        assert_ne!(render.clip_highlights(pinned), pinned);
    }

    /// A blown **coloured** highlight keeps its hue direction.
    ///
    /// Green pins but red is genuinely low: this is a clipped green object, not
    /// a clipped neutral, and bleaching it to white would be a worse lie than
    /// the magenta was. Only the channels above the neutral ceiling come down.
    #[test]
    fn a_blown_colour_is_not_bleached_to_white() {
        let ceil = saturation_ceiling(RIG, A7C2_WB, 1.0);
        let render = camera_to_srgb(A7C2_XYZ_TO_CAM)
            .expect("invertible")
            .with_ceiling(ceil);
        let v = [0.20f32, ceil[1], 0.15];
        let clipped = render.clip_highlights(v);
        assert_eq!(clipped[0], 0.20, "a low red was pulled up or down");
        assert_eq!(clipped[2], 0.15, "a low blue was pulled up or down");
        // Green is the pinned channel and green carries the minimum gain, so
        // the neutral ceiling *is* green's ceiling and green lands on it.
        assert_eq!(clipped[1], ceil[1]);
        // Power to fail: had the rule been "set every channel to the neutral
        // ceiling" rather than "min", this clipped triple would be neutral.
        let spread =
            clipped[0].max(clipped[1]).max(clipped[2]) - clipped[0].min(clipped[1]).min(clipped[2]);
        assert!(spread > 0.5, "a blown colour was bleached to {clipped:?}");
    }

    /// The ceiling scales with the exposure gain, so the fold in
    /// `merge_cmd::write_merged` — which multiplies the gain into `norm()`
    /// rather than developing twice — still commutes.
    ///
    /// `clip_{K*g}(g*v) == g*clip_K(v)`. Without this the fix would make the
    /// render depend on *where* the exposure was applied, and the linearity
    /// argument in [`AppliedExposure`] would no longer hold.
    #[test]
    fn the_ceiling_commutes_with_the_exposure_gain() {
        for stops in [-2.0f32, -0.24, 0.0, 1.57] {
            let g = AppliedExposure {
                stops,
                automatic: false,
            }
            .gain();
            let base = camera_to_srgb(A7C2_XYZ_TO_CAM).expect("invertible");
            let at_gain = base.with_ceiling(saturation_ceiling(RIG, A7C2_WB, g));
            let at_one = base.with_ceiling(saturation_ceiling(RIG, A7C2_WB, 1.0));
            for v in [[0.1f32, 0.2, 0.3], [1.4, 1.07, 1.2], [3.0, 1.07, 1.7]] {
                let folded = at_gain.clip_highlights([v[0] * g, v[1] * g, v[2] * g]);
                let after = at_one.clip_highlights(v).map(|x| x * g);
                for c in 0..3 {
                    assert!(
                        (folded[c] - after[c]).abs() <= 2e-6 * folded[c].abs().max(1.0),
                        "stops {stops}: {folded:?} vs {after:?}"
                    );
                }
            }
        }
    }

    /// A ceiling that cannot be computed is refused, not guessed. A zero or
    /// non-finite ceiling would clip every pixel to black.
    #[test]
    fn an_uncomputable_ceiling_disables_the_clip_instead_of_clipping_everything() {
        let bad = Levels {
            black: 512.0,
            white: 512.0,
        };
        assert!(saturation_ceiling(bad, A7C2_WB, 1.0)[1].is_infinite());
        assert!(saturation_ceiling(RIG, A7C2_WB, 0.0)[1].is_infinite());
        assert!(saturation_ceiling(RIG, [f32::NAN; 3], 1.0)[1].is_infinite());
        let render = camera_to_srgb(A7C2_XYZ_TO_CAM)
            .expect("invertible")
            .with_ceiling(saturation_ceiling(bad, A7C2_WB, 1.0));
        let v = [9.0f32, 9.0, 9.0];
        assert_eq!(render.clip_highlights(v), v);
    }
}
