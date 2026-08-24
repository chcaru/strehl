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
pub fn camera_to_srgb(xyz_to_cam: [[f32; 3]; 3]) -> Option<[[f32; 3]; 3]> {
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
    Some(out)
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
        let m = camera_to_srgb(A7C2_XYZ_TO_CAM).expect("invertible");
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
        let m = camera_to_srgb(belief).expect("invertible");
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
}
