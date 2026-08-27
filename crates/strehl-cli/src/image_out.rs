//! 16-bit TIFF output, and the development pipeline that feeds it.
//!
//! `tiff` 0.11 has a strips-only encoder — there is no tiled writer — and no
//! BigTIFF is needed at this size: the binned 3516x2344 RGB image is 49 MB, the
//! full-resolution 7032x4688 RGB image 198 MB, and the index map 16 MB, all far
//! inside the 4 GB classic-TIFF limit. Tiled float BigTIFF is a v1 requirement
//! (SYNTHESIS §9), not a skeleton one.
//!
//! # The development pipeline, and the order of its steps
//!
//! Everything below the merge is *rendering*, and rendering is where a raw
//! pipeline is usually wrong. The order this module implements is:
//!
//! ```text
//!   merged CFA in raw DN
//!     -> subtract black, divide by (white - black)      [caller]
//!     -> as-shot white balance gains, green = 1         [caller]
//!     -> demosaic to full resolution                    [this module]
//!     -> camera RGB -> linear sRGB matrix               [this module]
//!     -> clamp to [0, 1]                                [this module]
//!     -> sRGB transfer curve                            [this module]
//!     -> 16-bit quantisation                            [this module]
//! ```
//!
//! Two orderings in that list are decisions rather than conventions, and both
//! are load-bearing:
//!
//! - **White balance precedes the demosaic.** Malvar-He-Cutler interpolates
//!   *colour differences* (`R - G`), which are only small when the channels
//!   share a scale. Demosaicing before white balance would hand the gradient
//!   correction a 2.9x red offset to treat as scene structure.
//! - **The demosaic precedes the matrix.** The matrix mixes channels; applying
//!   it first would smear every single-channel interpolation artifact across
//!   all three output channels, and would make the demosaic's own error term
//!   uninterpretable. It also has negative off-diagonal entries, so it can send
//!   a valid camera-RGB triple outside `[0, 1]` — which is why the clamp is
//!   after the matrix and not before it.
//!
//! The black subtraction and white balance stay in the callers because that is
//! where they already were, and because the *binned linear* path must keep
//! emitting exactly the bytes it emitted before this module grew (M85). See
//! `docs/research/M85-output-correctness.md`.
//!
//! # Chroma co-siting on the binned path
//!
//! The binned render collapses each 2x2 RGGB quad to one pixel, but the four
//! CFA sites are not in the same place. Taking the quad centre as the origin
//! and one *binned* pixel as the unit, red sits at `(-0.25, -0.25)`, blue at
//! `(+0.25, +0.25)`, and green — the mean of two samples on opposite corners —
//! lands on the centre exactly. Writing all three into one pixel as though they
//! were co-sited leaves red and blue **half a binned pixel apart on the
//! diagonal**, which is a colour fringe on every luminance edge in the frame.
//!
//! [`write_binned`] therefore resamples red by `(+0.25, +0.25)` and blue by
//! `(-0.25, -0.25)` onto green's grid before development. Green is not touched.
//! Measured in `docs/research/M95-chroma-cositing.md`: the correction removes
//! 89-97% of the misregistration and 51-60% of the chroma error at edges.
//!
//! # Where this actually runs, which is NOT where it says it runs
//!
//! It is tempting to read the paragraph above as "co-siting is on the render
//! you look at". **It is not, and that misreading has already cost a milestone
//! of effort** (`docs/research/BUILD-COSITE.md`). Both callers reach
//! [`write_binned`] only *after* a `if demosaic { .. return }` branch, and
//! `main.rs` resolves `demosaic: demosaic || (srgb && !binned)`. So `--srgb`
//! **demosaics** unless `--binned` is also passed, and the gallery render --
//! `stack DIR --merge pyramid --pyramid-gate 4.5 --srgb --auto-exposure` --
//! emits 7032x4688 through [`write_demosaiced`] and never enters this function.
//! Verified by rendering it: the shipped gallery TIFFs are 7032x4688.
//!
//! [`write_binned`] is reachable by exactly two invocations:
//!
//!   - `--linear-srgb` without `--demosaic`, and
//!   - `--srgb --binned`.
//!
//! (`--exposure`/`--auto-exposure` also claim the binned branch, but both are
//! refused without `--srgb`, so that route collapses into the second.) The
//! first of those is the *measurement* render, which is the opposite of what
//! the old wording implied: the serial resample below is charged to the file
//! quality is judged on and not to the file the photographer sees.
//!
//! It does remain true that the **byte-frozen** path never enters here; that
//! one writes through [`write_rgb16`].
//!
//! What this costs, measured on `coffee-bean` and reproduced in closed form
//! from [`keys_weights`]: the shift below retains 0.881 / 0.681 / 0.473 of
//! amplitude at 0.25 / 0.35 / 0.50 cyc/px in red and blue. On the demosaiced
//! render that cost is not paid at all -- Malvar-He-Cutler co-sites inherently,
//! by estimating every channel at every site.

use std::fs::File;
use std::io::BufWriter;
use std::path::Path;

use anyhow::{Context, Result};
use rayon::prelude::*;
use strehl_core::color;
use strehl_core::demosaic::{Mosaic, demosaic_row};
use tiff::encoder::{Rational, TiffEncoder, colortype};
use tiff::tags::{ResolutionUnit, Tag};

fn writer(path: &Path) -> Result<TiffEncoder<BufWriter<File>>> {
    if let Some(parent) = path.parent()
        && !parent.as_os_str().is_empty()
    {
        std::fs::create_dir_all(parent)
            .with_context(|| format!("creating {}", parent.display()))?;
    }
    let file = File::create(path).with_context(|| format!("creating {}", path.display()))?;
    TiffEncoder::new(BufWriter::new(file))
        .with_context(|| format!("starting TIFF {}", path.display()))
}

/// What the pixels in the file actually are, as a sentence a human or a print
/// shop can read.
///
/// A bare 16-bit RGB TIFF carries no colour space, and every reader that meets
/// one assumes sRGB. For the `--srgb` render that assumption is accidentally
/// right. For the **default measurement render it is completely wrong** — those
/// pixels are camera-native, in the sensor's own primaries — and the two files
/// are byte-indistinguishable to any tool that opens them. That is the
/// "undefined colour path" in the risk register, and a print-worthy claim is
/// not credible while it stands.
///
/// This does not replace an embedded ICC profile, which is the real fix and is
/// the next step: `tiff` 0.11 knows `Tag::IccProfile`, so it is a matter of
/// carrying the profile bytes. Stating the space in words is strictly better
/// than the nothing that was there before, and it cannot be silently ignored
/// the way a wrong default can.
fn color_description(dev: &Develop) -> String {
    let space = match (dev.matrix.is_some(), dev.srgb) {
        (true, true) => {
            "sRGB (IEC 61966-2-1): BT.709-6 primaries, D65 white point, sRGB transfer curve. \
             For viewing."
        }
        (true, false) => {
            "Linear sRGB: BT.709-6 primaries, D65 white point, NO transfer curve (gamma 1.0)."
        }
        (false, true) => {
            "Camera-native RGB (sensor primaries) with an sRGB transfer curve and NO colour \
             matrix. THIS IS NOT sRGB -- do not treat it as such."
        }
        (false, false) => {
            "Linear camera-native RGB (sensor primaries), NO colour matrix, no transfer curve. \
             THIS IS NOT sRGB -- do not treat it as such. This is the measurement output."
        }
    };
    // The white-balance ordering is part of the colour statement, not a
    // footnote to it: the noise model is calibrated in raw DN, BEFORE any gain,
    // and the white balance is applied after black subtraction and
    // normalisation by (white - black). A reader that assumes the opposite
    // order will mis-scale the per-channel noise by the WB gains, which on this
    // body run 2.13-2.86x in red.
    let wb = "White balance: as-shot per-channel gains, green = 1, applied AFTER black \
              subtraction and normalisation by (white - black), and AFTER the noise model, which \
              is calibrated in raw DN before any gain.";
    // The tone rendering is not reproducible from the pixels, so it has to be
    // in the file. It was not, and a toned and an untoned --srgb TIFF carried
    // byte-identical descriptions while looking completely different; the only
    // record of `contrast` was a stderr line that `gallery.ps1` deletes.
    //
    // Written ONLY when a tone rendering was applied. The measurement paths
    // have no tone, so their description -- and therefore their bytes -- cannot
    // move because of this.
    match &dev.tone {
        Some(t) => format!(
            "{space} {wb} Tone rendering: black {:.6}, white {:.6} (linear, luminance \
             percentiles {TONE_BLACK_PCT}/{TONE_WHITE_PCT} with white mapped to \
             {TONE_WHITE_TARGET}), black fraction removed {TONE_BLACK_FRACTION}, display-space \
             contrast {:.3}. Placement is a single luminance-derived gain applied to all three \
             channels, so chromaticity is preserved; the toe is soft, so no channel is clamped \
             to zero.",
            t.black, t.white, t.contrast
        ),
        None => format!("{space} {wb}"),
    }
}

// ===========================================================================
// ICC profile construction
//
// WHY THIS IS BUILT AND NOT VENDORED
// ----------------------------------
// A vendored profile is a binary blob with a licence attached, and this project
// has strict licence hygiene. Every number below comes from published,
// unencumbered colorimetry -- IEC 61966-2-1 for the sRGB primaries and transfer
// curve, ICC.1 for the D50 PCS illuminant, and the Bradford cone response
// matrix -- and the adaptation is performed here rather than copied, so the
// profile is derived from stated constants instead of inherited from a file
// nobody read. The unit tests check the derivation against the canonical
// published columns, which is what makes that claim checkable rather than
// merely asserted.
//
// WHY v2 AND NOT v4
// -----------------
// v2 (0x02100000) is honoured by every colour-managed reader in use, including
// old print RIPs. v4 buys parametric curves and little else here; a v4 profile
// that a RIP silently ignores is worse than a v2 one it honours, and this whole
// exercise exists because a tag no reader reads is decoration.
// ===========================================================================

/// ICC profile bytes for TIFF tag 34675.
///
/// Written with TIFF type **UNDEFINED (7)**, which is what the ICC embedding
/// technote specifies. The crate's blanket `[u8]` impl would write type BYTE
/// (1); readers are mostly lenient about that, but "mostly lenient" is the
/// posture that produced the defect this code exists to fix, so the spec type
/// is written instead of the convenient one.
struct IccBytes<'a>(&'a [u8]);

impl tiff::encoder::TiffValue for IccBytes<'_> {
    const BYTE_LEN: u8 = 1;
    const FIELD_TYPE: tiff::tags::Type = tiff::tags::Type::UNDEFINED;

    fn count(&self) -> usize {
        self.0.len()
    }

    fn data(&self) -> std::borrow::Cow<'_, [u8]> {
        std::borrow::Cow::Borrowed(self.0)
    }
}

/// The ICC PCS illuminant, D50. ICC.1:2010 §7.2.16.
///
/// These exact values are chosen so the s15Fixed16 encoding lands on the
/// canonical `0000F6D6 00010000 0000D32D` that every reader expects to see.
const PCS_D50: [f64; 3] = [0.964_203, 1.0, 0.824_905];

/// D65, the sRGB white point (IEC 61966-2-1).
const WHITE_D65: [f64; 3] = [0.950_47, 1.0, 1.088_83];

/// sRGB primaries as CIE xy chromaticities (IEC 61966-2-1).
const SRGB_PRIMARIES_XY: [[f64; 2]; 3] =
    [[0.6400, 0.3300], [0.3000, 0.6000], [0.1500, 0.0600]];

/// Bradford cone response matrix, and its inverse.
const BRADFORD: [[f64; 3]; 3] = [
    [0.8951, 0.2664, -0.1614],
    [-0.7502, 1.7135, 0.0367],
    [0.0389, -0.0685, 1.0296],
];

fn mat3_mul(a: [[f64; 3]; 3], b: [[f64; 3]; 3]) -> [[f64; 3]; 3] {
    let mut o = [[0.0; 3]; 3];
    for (i, row) in o.iter_mut().enumerate() {
        for (j, cell) in row.iter_mut().enumerate() {
            *cell = (0..3).map(|k| a[i][k] * b[k][j]).sum();
        }
    }
    o
}

fn mat3_vec(a: [[f64; 3]; 3], v: [f64; 3]) -> [f64; 3] {
    let mut o = [0.0; 3];
    for (i, cell) in o.iter_mut().enumerate() {
        *cell = (0..3).map(|k| a[i][k] * v[k]).sum();
    }
    o
}

fn mat3_inv(m: [[f64; 3]; 3]) -> [[f64; 3]; 3] {
    let det = m[0][0] * (m[1][1] * m[2][2] - m[1][2] * m[2][1])
        - m[0][1] * (m[1][0] * m[2][2] - m[1][2] * m[2][0])
        + m[0][2] * (m[1][0] * m[2][1] - m[1][1] * m[2][0]);
    assert!(det.abs() > 1e-12, "singular matrix in ICC construction");
    let c = |r: usize, col: usize| -> f64 {
        let (r0, r1) = ((r + 1) % 3, (r + 2) % 3);
        let (c0, c1) = ((col + 1) % 3, (col + 2) % 3);
        m[r0][c0] * m[r1][c1] - m[r0][c1] * m[r1][c0]
    };
    let mut o = [[0.0; 3]; 3];
    for (i, row) in o.iter_mut().enumerate() {
        for (j, cell) in row.iter_mut().enumerate() {
            // transpose of the cofactor matrix, divided by the determinant
            *cell = c(j, i) / det;
        }
    }
    o
}

/// The RGB-to-XYZ matrix for the sRGB primaries under their own white point,
/// then Bradford-adapted to the D50 PCS. Columns are the `rXYZ`/`gXYZ`/`bXYZ`
/// tag values.
fn srgb_to_xyz_d50() -> [[f64; 3]; 3] {
    // Each primary's XYZ at unit luminance, from its xy chromaticity.
    let mut p = [[0.0; 3]; 3];
    for (i, [x, y]) in SRGB_PRIMARIES_XY.iter().enumerate() {
        p[0][i] = x / y;
        p[1][i] = 1.0;
        p[2][i] = (1.0 - x - y) / y;
    }
    // Scale the columns so the primaries sum to the white point.
    let s = mat3_vec(mat3_inv(p), WHITE_D65);
    let mut m = [[0.0; 3]; 3];
    for i in 0..3 {
        for j in 0..3 {
            m[i][j] = p[i][j] * s[j];
        }
    }
    // Bradford: convert both whites to cone space, scale, convert back.
    let src = mat3_vec(BRADFORD, WHITE_D65);
    let dst = mat3_vec(BRADFORD, PCS_D50);
    let mut scale = [[0.0; 3]; 3];
    for i in 0..3 {
        scale[i][i] = dst[i] / src[i];
    }
    let adapt = mat3_mul(mat3_inv(BRADFORD), mat3_mul(scale, BRADFORD));
    mat3_mul(adapt, m)
}

/// s15Fixed16Number, ICC.1 §4.2.
fn s15(v: f64) -> [u8; 4] {
    ((v * 65536.0).round() as i32).to_be_bytes()
}

/// The sRGB electro-optical transfer function: encoded value to linear light.
///
/// This is the direction an ICC `TRC` tag stores, because a matrix/TRC profile
/// computes `PCS = Matrix * TRC(device)`. Storing the opposite direction is a
/// classic and completely silent error -- the image simply renders with the
/// wrong contrast -- so the direction is named here rather than left implied.
fn srgb_eotf(v: f64) -> f64 {
    if v <= 0.040_45 {
        v / 12.92
    } else {
        ((v + 0.055) / 1.055).powf(2.4)
    }
}

/// Build a v2 display profile for RGB data on sRGB primaries.
///
/// `linear` selects the transfer curve: `false` gives the sRGB curve, `true`
/// gives an identity curve for data that is already linear light.
///
/// Deterministic by construction. The creation date is fixed rather than taken
/// from the clock, because a profile that changes every run would make every
/// output file's hash change every run, and this project's epistemics rest on
/// byte-freezes.
fn icc_srgb_v2(linear: bool) -> Vec<u8> {
    let m = srgb_to_xyz_d50();

    let desc = if linear {
        "strehl linear sRGB (BT.709-6 primaries, D65, gamma 1.0)"
    } else {
        "strehl sRGB (IEC 61966-2-1)"
    };
    let cprt = "Constructed by strehl from published colorimetry \
                (IEC 61966-2-1 primaries and transfer curve, ICC.1 D50 PCS, \
                 Bradford adaptation). No rights reserved.";

    // -- tag payloads ------------------------------------------------------
    let xyz_tag = |c: usize| -> Vec<u8> {
        let mut v = b"XYZ \0\0\0\0".to_vec();
        for r in 0..3 {
            v.extend_from_slice(&s15(m[r][c]));
        }
        v
    };

    let mut wtpt = b"XYZ \0\0\0\0".to_vec();
    for v in PCS_D50 {
        wtpt.extend_from_slice(&s15(v));
    }

    let trc = {
        let mut v = b"curv\0\0\0\0".to_vec();
        if linear {
            // count 0 is the identity curve.
            v.extend_from_slice(&0u32.to_be_bytes());
        } else {
            const N: usize = 1024;
            v.extend_from_slice(&(N as u32).to_be_bytes());
            for i in 0..N {
                let y = srgb_eotf(i as f64 / (N - 1) as f64);
                v.extend_from_slice(&((y * 65535.0).round() as u16).to_be_bytes());
            }
        }
        v
    };

    // textDescriptionType, the v2 form of `desc`.
    let desc_tag = {
        let mut v = b"desc\0\0\0\0".to_vec();
        v.extend_from_slice(&((desc.len() + 1) as u32).to_be_bytes());
        v.extend_from_slice(desc.as_bytes());
        v.push(0);
        v.extend_from_slice(&[0u8; 4]); // unicode language code
        v.extend_from_slice(&[0u8; 4]); // unicode count
        v.extend_from_slice(&[0u8; 2]); // scriptcode code
        v.push(0); // scriptcode count
        v.extend_from_slice(&[0u8; 67]); // scriptcode description
        v
    };

    let cprt_tag = {
        let mut v = b"text\0\0\0\0".to_vec();
        v.extend_from_slice(cprt.as_bytes());
        v.push(0);
        v
    };

    // The adaptation actually applied, recorded so a reader can undo it.
    let chad_tag = {
        let src = mat3_vec(BRADFORD, WHITE_D65);
        let dst = mat3_vec(BRADFORD, PCS_D50);
        let mut scale = [[0.0; 3]; 3];
        for i in 0..3 {
            scale[i][i] = dst[i] / src[i];
        }
        let adapt = mat3_mul(mat3_inv(BRADFORD), mat3_mul(scale, BRADFORD));
        let mut v = b"sf32\0\0\0\0".to_vec();
        for row in adapt {
            for cell in row {
                v.extend_from_slice(&s15(cell));
            }
        }
        v
    };

    // `rTRC`, `gTRC` and `bTRC` share one payload: identical curves pointing at
    // one offset is normal ICC practice and is what most shipping profiles do.
    let tags: Vec<(&[u8; 4], Vec<u8>)> = vec![
        (b"desc", desc_tag),
        (b"wtpt", wtpt),
        (b"rXYZ", xyz_tag(0)),
        (b"gXYZ", xyz_tag(1)),
        (b"bXYZ", xyz_tag(2)),
        (b"rTRC", trc),
        (b"cprt", cprt_tag),
        (b"chad", chad_tag),
    ];

    // -- lay out ------------------------------------------------------------
    // Tag count includes the two aliased TRC entries, which carry no payload of
    // their own.
    let n_entries = tags.len() as u32 + 2;
    let table_bytes = 4 + 12 * n_entries as usize;
    let mut offset = 128 + table_bytes;

    let mut entries: Vec<([u8; 4], u32, u32)> = Vec::new();
    let mut payload: Vec<u8> = Vec::new();
    let mut trc_at = (0u32, 0u32);
    for (sig, data) in &tags {
        let at = offset as u32;
        let size = data.len() as u32;
        entries.push((**sig, at, size));
        if *sig == b"rTRC" {
            trc_at = (at, size);
        }
        payload.extend_from_slice(data);
        // Tag data must start on a 4-byte boundary.
        let pad = (4 - (data.len() % 4)) % 4;
        payload.extend(std::iter::repeat_n(0u8, pad));
        offset += data.len() + pad;
    }
    entries.push((*b"gTRC", trc_at.0, trc_at.1));
    entries.push((*b"bTRC", trc_at.0, trc_at.1));

    let total = 128 + table_bytes + payload.len();

    let mut out = Vec::with_capacity(total);
    out.extend_from_slice(&(total as u32).to_be_bytes()); // profile size
    out.extend_from_slice(&[0u8; 4]); // preferred CMM: none
    out.extend_from_slice(&0x0210_0000u32.to_be_bytes()); // v2.1
    out.extend_from_slice(b"mntr");
    out.extend_from_slice(b"RGB ");
    out.extend_from_slice(b"XYZ ");
    // Fixed creation date: 2026-01-01T00:00:00Z. See the determinism note above.
    for v in [2026u16, 1, 1, 0, 0, 0] {
        out.extend_from_slice(&v.to_be_bytes());
    }
    out.extend_from_slice(b"acsp");
    out.extend_from_slice(&[0u8; 4]); // platform
    out.extend_from_slice(&[0u8; 4]); // flags: not embedded, usable independently
    out.extend_from_slice(&[0u8; 4]); // device manufacturer
    out.extend_from_slice(&[0u8; 4]); // device model
    out.extend_from_slice(&[0u8; 8]); // device attributes
    out.extend_from_slice(&0u32.to_be_bytes()); // rendering intent: perceptual
    for v in PCS_D50 {
        out.extend_from_slice(&s15(v));
    }
    out.extend_from_slice(&[0u8; 4]); // profile creator
    out.extend_from_slice(&[0u8; 16]); // profile ID (MD5); zero = not computed
    out.extend_from_slice(&[0u8; 28]); // reserved
    debug_assert_eq!(out.len(), 128);

    out.extend_from_slice(&n_entries.to_be_bytes());
    for (sig, at, size) in &entries {
        out.extend_from_slice(sig);
        out.extend_from_slice(&at.to_be_bytes());
        out.extend_from_slice(&size.to_be_bytes());
    }
    out.extend_from_slice(&payload);
    debug_assert_eq!(out.len(), total);
    out
}

/// The profile to embed for a given development, or `None`.
///
/// **`None` is a deliberate answer, not a missing case.** When `dev.matrix` is
/// `None` the pixels are camera-native, in the sensor's own primaries, and this
/// code has no characterisation of them: `Develop::matrix`'s own documentation
/// says `None` is also what happens "when the decoder has no characterisation
/// for the body". There is therefore nothing to build a truthful profile from.
///
/// Writing an sRGB profile onto those pixels would be the worst option
/// available. Today they are mislabelled loudly -- the description shouts THIS
/// IS NOT sRGB -- and a human or a print shop can read it. An embedded sRGB
/// profile would replace that shout with a machine-readable assertion that a
/// colour-managed application would silently obey, converting a visible warning
/// into an invisible corruption. So the camera-native paths keep the text and
/// get no profile, and a reader that finds no profile falls back to exactly the
/// behaviour it has today rather than to something new and wrong.
///
/// **The third `None` is the same policy applied one step further in.** A
/// development that carries the colour matrix but *not* the transfer curve,
/// and yet has a [`Tone`] resolved, has had [`s_curve`] applied to **linear**
/// light -- see [`develop_pixel`], where the S-curve runs unconditionally and
/// the sRGB encode does not. Those pixels are not linear sRGB, so the
/// identity-TRC profile would describe them wrongly, and they are not sRGB
/// either. Nothing in this module describes them, so nothing is claimed.
///
/// That arm is **not reachable from the CLI today** -- [`OutputSpace::develop`]
/// sets `wants_tone` from `applies_curve`, so tone and curve arrive together --
/// and it is written anyway because `Develop` is a public struct whose four
/// fields are independently settable, and because the cost of getting this
/// wrong is measured rather than imagined: `icc_potency.py` ARM B moved
/// **92 DN** by substituting one profile for another on identical pixels, and
/// `BUILD-RENDER-icc`'s potency table puts a linear-for-sRGB swap at **50.39 DN
/// mean over 99.5% of pixels**. A wrong profile is not a cosmetic defect; it is
/// a machine-readable instruction to transform every pixel.
fn icc_for(dev: &Develop) -> Option<Vec<u8>> {
    match (dev.matrix.is_some(), dev.srgb, dev.tone.is_some()) {
        (true, true, _) => Some(icc_srgb_v2(false)),
        (true, false, false) => Some(icc_srgb_v2(true)),
        (true, false, true) => None,
        (false, _, _) => None,
    }
}

/// The print resolution written into every tagged master, in dots per inch.
///
/// **What it replaces.** `tiff` writes `XResolution = YResolution = 1/1` with
/// `ResolutionUnit::None` unless told otherwise (`encoder/mod.rs:696-698`), and
/// that default reached all 26 shipped masters. It declares *one pixel per
/// undefined unit*, which is not a small imprecision: Photoshop, Lightroom,
/// Capture One and every RIP read tags 282/283/296 to establish physical size,
/// so a `7032x4688` master either opens as a document 7032 by 4688 **inches**
/// -- about 590 by 390 feet -- or the application substitutes a default of its
/// own, and those defaults differ between applications. A print master whose
/// physical size is undefined is not a print master.
///
/// **Why 300 rather than 360.** At 300 dpi the 7032x4688 master is
/// `7032 / 300 = 23.44` by `4688 / 300 = 15.63` inches. The alternative worth
/// naming is 360, the native pitch of the Epson pigment printers this rig would
/// actually use, giving `7032 / 360 = 19.53` by `4688 / 360 = 13.02` inches.
/// Both are real, desirable print sizes and neither is wrong. 300 wins because
/// **this tag is advisory**: it declares an intended physical size and resamples
/// nothing, so no pixel is better or worse for the choice. Given that, the
/// interchange default is the one that behaves predictably in the widest set of
/// readers, and anyone driving an Epson can state 360 at print time without the
/// file having lost anything. Were the tag lossy the argument would run the
/// other way.
const PRINT_DPI: u32 = 300;

/// What tag 305 says on a **measurement** render, and why it is deliberately
/// not the build stamp.
///
/// [`crate::SOFTWARE`] carries the source commit, which is the whole point of
/// it -- an artifact that cannot name its build cannot be audited. But a commit
/// hash changes on every commit *by construction*, and the measurement renders
/// are hashed whole by `tests/byte-freezes.tsv`. Stamping the build into them
/// makes those rows a function of the commit they are checked at, so they would
/// go red on every commit forever and be re-baselined without anybody reading
/// them. A regression test that must be re-baselined routinely is not a
/// regression test.
///
/// MEASURED, and this is the measurement that forced the split: with the stamp
/// written unconditionally, `coffee-bean-20-gate2-unaligned` grew by 37 bytes
/// on a tree stamped `6e8c3898b2da-dirty` and by 31 on the same source stamped
/// `72b997e8e4ee`. The six-byte gap is the length of `-dirty`. The frozen hash
/// had become a function of which tree the test ran in.
///
/// So the split is by *kind of file*, using the discriminator this module
/// already trusts: a profile is emitted exactly when a colour matrix was
/// applied. A colorimetric render is a picture -- somebody looks at it, prints
/// it, keeps it -- and its provenance has to travel with it. A camera-native
/// render is measurement data whose provenance is recorded far more completely
/// in the freeze registry, which stores the entire invocation beside the hash.
/// The one that needs the stamp least is the one that cannot afford it.
const MEASUREMENT_SOFTWARE: &str = concat!("strehl ", env!("CARGO_PKG_VERSION"));

/// Interleaved RGB, 16 bits per channel, with the colour space stated in the
/// file.
///
/// Separate from [`write_rgb16`] so that the older four-argument signature
/// keeps compiling for its existing callers; new call sites should use this.
///
/// `pub` because the measurement write in `merge_cmd.rs` is the most important
/// caller there will ever be: that branch emits linear camera-native pixels,
/// which is precisely the file a reader is most likely to mistake for sRGB.
pub fn write_rgb16_described(
    path: &Path,
    width: u32,
    height: u32,
    data: &[u16],
    dev: &Develop,
) -> Result<()> {
    assert_eq!(data.len(), width as usize * height as usize * 3);
    let mut enc = writer(path)?;
    let mut img = enc
        .new_image::<colortype::RGB16>(width, height)
        .with_context(|| format!("starting image {}", path.display()))?;
    let desc = color_description(dev);
    img.encoder()
        .write_tag(Tag::ImageDescription, desc.as_str())
        .with_context(|| format!("tagging {}", path.display()))?;
    // The machine-readable half of the same statement. The description above is
    // for a human; this is the only part a colour-managed application reads.
    //
    // Whether a profile exists is also the line between the two kinds of file
    // this function writes, so it is computed once and reused below rather than
    // asked twice: a profile is emitted exactly when a colour matrix was
    // applied, which is exactly when the result is a picture somebody looks at
    // or prints. Without one the pixels are camera-native measurement data.
    let profile = icc_for(dev);
    if let Some(profile) = &profile {
        img.encoder()
            .write_tag(Tag::IccProfile, IccBytes(profile))
            .with_context(|| format!("embedding ICC profile in {}", path.display()))?;
    }
    img.encoder()
        .write_tag(
            Tag::Software,
            if profile.is_some() {
                crate::SOFTWARE
            } else {
                MEASUREMENT_SOFTWARE
            },
        )
        .with_context(|| format!("tagging {}", path.display()))?;
    if profile.is_some() {
        // Physical size, tags 282/283/296. Written through the crate's own
        // setter so all three move together: a resolution without a unit, or a
        // unit without a resolution, is the state this replaces.
        img.resolution(
            ResolutionUnit::Inch,
            Rational {
                n: PRINT_DPI,
                d: 1,
            },
        );
    }
    img.write_data(data)
        .with_context(|| format!("writing {}", path.display()))
}

/// Interleaved RGB, 16 bits per channel, **untagged**.
///
/// This is the byte-frozen measurement encoder, and it is deliberately NOT
/// routed through [`write_rgb16_described`], even though the file it produces
/// is the one most likely to be misread: it is linear camera-native RGB, and
/// every reader that meets an untagged TIFF assumes sRGB.
///
/// The reason is ownership, not disagreement. This function is the encoder
/// behind `merge_cmd.rs`'s measurement branch, whose output is pinned by
/// `tests/byte-freezes.tsv` (`coffee-bean-20-gate2-unaligned` and
/// `-sidecar`). Adding a tag here adds ~393 bytes of metadata and moves both
/// hashes without changing a single pixel. Those rows are being moved
/// concurrently for a different and larger reason, so re-baselining them here
/// would publish a hash that is stale on arrival and a `why` that describes
/// the wrong change -- which that registry explicitly calls worse than an
/// empty one.
///
/// **This is a known, deliberate gap, not an oversight.** Closing it is a
/// one-line switch to `write_rgb16_described` plus a single coordinated
/// re-baseline of both rows, once the merge core stops moving.
pub fn write_rgb16(path: &Path, width: u32, height: u32, data: &[u16]) -> Result<()> {
    assert_eq!(data.len(), width as usize * height as usize * 3);
    writer(path)?
        .write_image::<colortype::RGB16>(width, height, data)
        .with_context(|| format!("writing {}", path.display()))
}

/// Single-channel 16-bit grayscale.
pub fn write_gray16(path: &Path, width: u32, height: u32, data: &[u16]) -> Result<()> {
    assert_eq!(data.len(), width as usize * height as usize);
    writer(path)?
        .write_image::<colortype::Gray16>(width, height, data)
        .with_context(|| format!("writing {}", path.display()))
}

/// How merged CFA data is turned into a picture.
///
/// Default is the **measurement** rendering: camera-native RGB, linear, binned.
/// Every field that turns on is a step away from measurement and towards
/// looking at, and [`Develop::caveat`] is what says so on the terminal.
#[derive(Debug, Clone, Copy, Default)]
pub struct Develop {
    /// Camera RGB to linear sRGB, from [`color::camera_to_srgb`], together with
    /// the sensor saturation ceiling it must not be fed past (see
    /// [`color::Render`]).
    ///
    /// `None` means **camera-native RGB is emitted unchanged**, which is the
    /// pre-M85 behaviour and is what the corpus's measurements were taken on.
    /// It is also what happens when the decoder has no characterisation for the
    /// body: emitting camera-native and saying so beats inventing a matrix.
    pub matrix: Option<color::Render>,
    /// Apply the sRGB transfer curve. For looking at, not for measuring.
    pub srgb: bool,
    /// The photographic tone rendering, or `None` for none.
    ///
    /// Resolved per image by the writers, because the black and white points
    /// are order statistics of the frame and cannot be known before it exists.
    /// [`OutputSpace::develop`] sets [`Develop::wants_tone`]; the writers fill
    /// this in.
    pub tone: Option<Tone>,
    /// Whether a tone rendering should be measured and applied.
    ///
    /// Separate from `tone` so that the *decision* travels with the colour
    /// space -- where it belongs, since it is a rendering intent -- while the
    /// *numbers* are measured later from the pixels.
    pub wants_tone: bool,
}

impl Develop {
    /// The development the **measurement** branch performs: no colour matrix,
    /// camera-native primaries, transfer curve only if `srgb` was asked for.
    ///
    /// Exists so that the byte-frozen write site in `merge_cmd.rs` can state
    /// its colour space without constructing a `Develop` by hand and without
    /// having to know that "measurement" means `matrix: None`. That branch has
    /// `srgb` in scope already, so the call is
    /// `Develop::measurement(srgb)` and nothing else has to be threaded to it.
    ///
    /// This describes pixels, it does not change them: the measurement branch
    /// does its own arithmetic inline and deliberately does not route through
    /// [`develop_pixel`].
    pub fn measurement(srgb: bool) -> Self {
        Self {
            matrix: None,
            srgb,
            tone: None,
            wants_tone: false,
        }
    }

    /// One line describing what was done to the pixels, for the "wrote" report.
    pub fn caveat(&self) -> &'static str {
        match (self.matrix.is_some(), self.srgb) {
            (true, true) => "sRGB (BT.709 primaries, D65, sRGB transfer) -- for looking at",
            (true, false) => "linear sRGB (BT.709 primaries, D65, no transfer curve)",
            (false, true) => "camera-native RGB with an sRGB transfer curve -- NO colour matrix",
            (false, false) => "linear camera-native RGB",
        }
    }
}

/// Which colour space the user asked the render to land in.
///
/// This type exists to keep a *colour* decision out of the merge code. Before
/// it, "does the matrix get applied" was spelled `if srgb` at the point of use,
/// which silently welded two independent choices together: whether to move to
/// colorimetric primaries, and whether to apply a transfer curve. That weld is
/// why there was no way to ask for the one mode measurement actually needs.
///
/// **`LinearSrgb` is that mode, and it is not a convenience.** This project's
/// own rule is that quality is never judged on an `--srgb` render, because the
/// transfer curve is a strong non-linearity that changes every ratio a metric
/// computes. But the alternative on offer was camera-native RGB, whose
/// primaries are the sensor's and are *not stated anywhere*. So measurements
/// were being taken either through a curve or in an undeclared space. Applying
/// the matrix and stopping before the curve gives a stated colorimetric target
/// that is still linear, which is what the rule was reaching for.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Default)]
pub enum OutputSpace {
    /// Camera-native primaries, linear. The default, and the byte-frozen
    /// measurement output the corpus was built on.
    #[default]
    CameraLinear,
    /// Colorimetric primaries (sRGB/BT.709, D65), **linear** -- no transfer
    /// curve. `--linear-srgb`. Stated space, safe to measure in.
    LinearSrgb,
    /// Colorimetric primaries and the sRGB transfer curve. `--srgb`. For
    /// looking at, never for measuring.
    Srgb,
}

impl OutputSpace {
    /// Resolve the two mutually exclusive flags into one space.
    ///
    /// Returns an error rather than picking a winner: if both are passed the
    /// user has asked for two different files and guessing which they meant is
    /// how a measurement silently ends up in the wrong space.
    pub fn from_flags(srgb: bool, linear_srgb: bool) -> Result<Self> {
        match (srgb, linear_srgb) {
            (true, true) => anyhow::bail!(
                "--srgb and --linear-srgb ask for different files: --srgb applies the sRGB \
                 transfer curve, --linear-srgb stops before it. Pass one."
            ),
            (true, false) => Ok(Self::Srgb),
            (false, true) => Ok(Self::LinearSrgb),
            (false, false) => Ok(Self::CameraLinear),
        }
    }

    /// Whether the camera-to-colorimetric matrix should be applied.
    ///
    /// The matrix rides with **either** colorimetric mode. Previously it rode
    /// with the curve, which is the weld this type exists to break.
    pub fn wants_matrix(self) -> bool {
        matches!(self, Self::LinearSrgb | Self::Srgb)
    }

    /// Whether the sRGB transfer curve is applied. Only the viewing render.
    pub fn applies_curve(self) -> bool {
        matches!(self, Self::Srgb)
    }

    /// True for the default path whose bytes are frozen in
    /// `tests/byte-freezes.tsv`.
    pub fn is_measurement(self) -> bool {
        matches!(self, Self::CameraLinear)
    }

    /// Build the [`Develop`] for this space.
    ///
    /// `matrix` is what the characterisation yielded, or `None` when the body
    /// has none. A missing characterisation degrades to camera-native rather
    /// than inventing a matrix, and [`Develop::caveat`] says so out loud.
    ///
    /// The tone rendering rides with the **viewing** render and only with it.
    /// That placement is the whole safety argument: `--linear-srgb` and the
    /// default measurement output are untouched by it, so every number the
    /// corpus rests on is measured on exactly the pixels it always was, while
    /// the file a human opens is finally rendered like a photograph.
    pub fn develop(self, matrix: Option<color::Render>) -> Develop {
        Develop {
            matrix: if self.wants_matrix() { matrix } else { None },
            srgb: self.applies_curve(),
            tone: None,
            wants_tone: self.applies_curve(),
        }
    }
}

/// The photographic tone rendering, resolved to numbers for one image.
///
/// **Why this exists.** Until now the develop path was `black, white balance,
/// matrix, clamp, sRGB curve` and nothing else. That is colorimetrically
/// defensible and photographically dead: the sRGB transfer function is an
/// *encoding*, not a rendering. Every camera and every raw developer applies a
/// tone rendering on top of it, and without one the result is exactly what the
/// owner described -- a milky veil, lifted blacks, flat whites, muddy colour.
///
/// It went unnoticed through the entire corpus because every measurement this
/// project has ever made was taken on 16-bit **linear** crops, where the defect
/// is invisible by construction. The measurement discipline that kept the
/// numbers honest is precisely what hid this from us.
///
/// Three things are wrong with an untoned render, and this fixes them in order:
///
/// 1. **The blacks do not reach black.** Measured on `flower-inner-edge-cpl`,
///    the darkest 0.01% of the frame sits at 0.0038 linear, not 0. The sRGB
///    curve has a steep toe, so that renders as a **6% grey floor** -- the
///    veil. Subtracting a black point is what removes it.
/// 2. **The whites do not reach white.** The 99.9th percentile lands at 0.641
///    linear, leaving 0.64 stops of the output range simply unused.
/// 3. **There is no contrast rendering at all**, so midtones sit flat and
///    colour reads desaturated, because saturation is perceived largely through
///    local contrast.
#[derive(Debug, Clone, Copy, PartialEq)]
pub struct Tone {
    /// Linear value mapped to 0 -- the portion of the measured flare floor that
    /// is actually removed, i.e. the measured percentile already multiplied by
    /// [`TONE_BLACK_FRACTION`]. It is the effective number, so that everything
    /// downstream (the white point, the report, the file's description) is
    /// consistent with what the pixels were actually developed against.
    pub black: f32,
    /// Linear value mapped to 1.
    pub white: f32,
    /// Strength of the display-space S-curve, in `[0, 1]`.
    pub contrast: f32,
}

/// Where the black point is taken from, as a percentile of linear luminance.
///
/// Deliberately not the minimum: a single dead-black pixel would then set the
/// point for the whole frame and the subtraction would do nothing. 0.1% is low
/// enough to sit inside the flare floor and high enough to be a robust
/// statistic. It is an order statistic, so it is deterministic.
const TONE_BLACK_PCT: f64 = 0.1;

/// How much of the measured floor to actually remove.
///
/// Not 1.0, and the reason is physical. The floor is **flare**, not a residual
/// black-level error: the measured floor runs G 0.0035 > R 0.0017 while this
/// body's as-shot red gains are 2.13-2.86x, and a DN offset scaled by those
/// gains would put RED highest. Flare is scattered light, and scattered light
/// is **not uniform across the frame** -- it is worst next to bright subject
/// matter and near-absent in a corner. A single global constant is therefore
/// the wrong model for it no matter how well the constant is measured, and the
/// error it makes is one-sided: wherever the true local flare is less than the
/// global estimate, the subtraction eats signal.
///
/// So remove most of it and leave a margin. This is a deliberate trade of a
/// slightly less aggressive veil removal for not destroying data in the
/// regions where the estimate is too high. Chosen by looking at
/// `coffee-bubbles`, which is the subject where it matters most.
const TONE_BLACK_FRACTION: f32 = 0.85;

/// Where the white point is taken from.
///
/// The same percentile `--auto-exposure` uses, on purpose: M100 MEASURED that
/// choice by sweeping 7 percentiles x 5 targets x 2 statistics across seven
/// corpus stacks, and having two different white-point conventions in one
/// program is how a render stops being reproducible.
const TONE_WHITE_PCT: f64 = 99.9;

/// What the white percentile is mapped to. 0.90, again matching M100's
/// measured rule, leaving a little headroom above it rather than clipping the
/// brightest 0.1% of the frame flat.
const TONE_WHITE_TARGET: f32 = 0.90;

/// Width of the shadow toe, as a fraction of the black-to-white output range.
///
/// The toe replaces the hard clamp at zero. It has to be narrow: a wide toe is
/// just the veil coming back. The first attempt made the knee proportional to
/// the black point itself, which is fine when the floor is a fraction of a
/// percent of the range -- as it is on every real capture here -- and lifts the
/// floor to 17% grey when the floor is large. Scale-free in the normalised
/// output, so it behaves the same regardless of exposure.
///
/// At 0.004 the measured floor develops to roughly 2% grey on real subjects
/// (1.7% on `flower-inner-edge-cpl`, 2.2% on `coffee-bubbles`) instead of to a
/// hard zero, and everything below it stays distinguishable.
const TONE_TOE: f32 = 0.004;

/// Default S-curve strength. Chosen by LOOKING at the gallery, which is the
/// only way this can honestly be chosen -- the standing rule for this build is
/// that when the pictures and the number disagree, the pictures are right.
const TONE_CONTRAST: f32 = 0.55;

/// A contrast S-curve applied in **display** space, after the transfer curve.
///
/// Display space is where raw developers put the tone curve, and it is the
/// right place: an S-curve in linear light crushes shadows violently because
/// linear light is not perceptually spaced.
///
/// `smoothstep` is the S: it fixes 0, 0.5 and 1 exactly, is monotonic on
/// `[0, 1]`, and has zero derivative at both ends, so it cannot introduce a
/// hard shoulder or a clipped toe. `strength` blends between the identity and
/// it, so the curve is continuous in the parameter and `0.0` is exactly "no
/// tone curve" -- which is what keeps the old rendering reachable.
///
/// Applied per channel, which is what makes colour come back: a per-channel
/// contrast curve stretches the distance between channels as well as the
/// distance between tones, and that is perceived as saturation.
#[inline]
fn s_curve(x: f32, strength: f32) -> f32 {
    let s = x * x * (3.0 - 2.0 * x);
    x + (s - x) * strength
}

impl Tone {
    /// Resolve a tone rendering from a sample of the image's linear luminance.
    ///
    /// `lum` is consumed and sorted in place; callers pass a subsample, because
    /// an order statistic does not need every pixel and the full-resolution
    /// path deliberately never materialises its float image.
    fn from_luminance(lum: &mut [f32]) -> Self {
        if lum.is_empty() {
            return Self {
                black: 0.0,
                white: 1.0,
                contrast: TONE_CONTRAST,
            };
        }
        lum.sort_unstable_by(f32::total_cmp);
        let at = |pct: f64| -> f32 {
            let i = ((pct / 100.0) * (lum.len() - 1) as f64).round() as usize;
            lum[i.min(lum.len() - 1)]
        };
        let black = at(TONE_BLACK_PCT) * TONE_BLACK_FRACTION;
        let white_src = at(TONE_WHITE_PCT);
        // Map the white percentile to TONE_WHITE_TARGET rather than to 1.0.
        // Computed from the EFFECTIVE black, not the measured one: deriving it
        // from the measured floor while subtracting only a fraction of that
        // floor leaves the white percentile landing above its target, which is
        // a silent exposure shift.
        let white = black + (white_src - black).max(1e-4) / TONE_WHITE_TARGET;
        Self {
            black,
            white,
            contrast: TONE_CONTRAST,
        }
    }

    /// One line for the "wrote" report, so a render can be reproduced and so
    /// the numbers are visible rather than hidden inside the binary.
    pub fn report(&self) -> String {
        format!(
            "tone            : black {:.5}, white {:.5} (linear), contrast {:.2}",
            self.black, self.white, self.contrast
        )
    }

    /// The factor that places a pixel's **luminance** between black and white,
    /// to be applied to all three channels equally.
    ///
    /// **This is the whole of the black/white placement, and it is deliberately
    /// not a per-channel subtraction.** The first version of this tone
    /// rendering subtracted one luminance-derived scalar from every channel:
    /// `(v[c] - black) * s`. That destroys chromaticity, because subtracting a
    /// constant from three numbers changes their ratios -- `(R-b)/(G-b)` is not
    /// `R/G` -- and the error diverges as a channel approaches `b`. On a
    /// saturated subject the weak channels sit *below* a luminance-derived
    /// black over most of the frame, so they clamped to zero and the render
    /// collapsed to one channel. MEASURED on `coffee-bubbles`, dark red liquid
    /// with `black = 0.01563` above its green and blue nearly everywhere:
    /// zero-green went 0.0011% -> 83.90%, zero-blue 0.0297% -> 88.32%, and the
    /// median luminance fell 5x. The swirl texture and the surface scratches
    /// were gone -- and on `foam` the crushed pixels had a median 3x3 local
    /// range of 847 DN against a frame median of 1774 DN, so what was deleted
    /// was structure, not noise.
    ///
    /// Scaling all three channels by one factor fixes it by construction:
    /// chromaticity is exactly preserved, hue and saturation cannot move, and
    /// **no channel can reach zero unless luminance itself is zero.**
    ///
    /// The honest cost, stated because it is a real trade and not a free win:
    /// a veiling flare is physically *additive*, so removing it correctly
    /// would change chromaticity, and this does not. It declines to, because
    /// the per-channel alternative needs a per-channel floor estimate, and a
    /// per-channel percentile on a saturated subject measures the SCENE rather
    /// than the flare -- which is the same defect wearing different clothes.
    /// Restoring saturation is what `contrast` is for; not destroying the weak
    /// channel is what this is for.
    ///
    /// **The soft toe.** Instead of `max((L - black) * s, 0)`, the placed value
    /// is smoothed into the floor with
    /// `(y + sqrt(y^2 + toe^2)) / 2` where `y = (L - black) * s`. For
    /// `y >> toe` that is exactly `y`, so normal tones are placed precisely as
    /// before. For `y << -toe` it decays toward zero instead of arriving there,
    /// and its derivative is positive everywhere, so no two shadow values are
    /// ever mapped onto one another. A hard clamp is unrecoverable by
    /// definition, which is what turns "slightly below the estimated black"
    /// into "no data at all".
    ///
    /// The smooth maximum alone tends to a positive constant as `L -> 0`, so
    /// the gain is capped at `s`, the pure white-point gain. That cap is not a
    /// patch: it says the tone may never brighten a pixel by more than exposure
    /// alone, and it makes the deepest shadows fall back to a plain gain with
    /// no subtraction at all, reaching zero exactly at zero.
    #[inline]
    fn gain(&self, lum: f32) -> f32 {
        let l = lum.max(0.0);
        if l <= 0.0 {
            return 0.0;
        }
        let s = 1.0 / (self.white - self.black);
        let y = (l - self.black) * s;
        let soft = 0.5 * (y + (y * y + TONE_TOE * TONE_TOE).sqrt());
        (soft / l).min(s)
    }
}

/// Luminance of a post-matrix linear triple, BT.709 weights.
#[inline]
fn luma709(v: [f32; 3]) -> f32 {
    0.2126 * v[0] + 0.7152 * v[1] + 0.0722 * v[2]
}

/// Bring an out-of-gamut triple inside `[0, 1]` by desaturating it toward the
/// neutral of the **same luminance**, by the smallest amount that works.
///
/// **Why a hard clamp is wrong.** The matrix has negative off-diagonal terms
/// and legitimately produces values outside `[0, 1]`; that is not an error, it
/// is what "this colour is outside sRGB" looks like in numbers. Clamping each
/// channel independently is the one response that is certainly wrong:
///
/// * it **moves hue**, because the three channels are treated separately and
///   only the offending one is changed;
/// * it **moves luminance**, because raising a negative blue to zero makes the
///   pixel lighter than the colour it is standing in for. MEASURED on
///   `flower-inner-edge-cpl`: the clamp's luminance error against the
///   unclamped value is 0.00117 at p99.9, where this map's is exactly 0.00000,
///   by construction;
/// * it is **not** rare. Blue lands below zero on 11.8% of that frame before
///   the tone stage and **40.5% after it**, because the tone stage subtracts a
///   black point in linear light and blue is the channel already nearest zero.
///   Adding a tone rendering made this four times worse, which is exactly why
///   it had to be fixed in the same breath.
///
/// **What this does instead.** Blend toward the grey of the same BT.709
/// luminance -- a straight line to the neutral axis, which is the hue-preserving
/// direction in linear light -- and take the smallest blend `t` that brings
/// every channel inside the range. Luminance is preserved exactly because the
/// endpoint has the same luminance as the start, and both ends of the range are
/// handled by one operation, since a saturated highlight pinned at 1.0 is the
/// same defect as a saturated shadow pinned at 0.0.
///
/// **Where nothing is out of gamut this is the identity, exactly**, which is
/// the same safety property [`color::Render::clip_highlights`] has and for the
/// same reason: an in-gamut render cannot move by one bit.
#[inline]
fn gamut_map(v: [f32; 3]) -> [f32; 3] {
    let lo = v[0].min(v[1]).min(v[2]);
    let hi = v[0].max(v[1]).max(v[2]);
    if lo >= 0.0 && hi <= 1.0 {
        return v;
    }
    // The target grey. Clamped so that `t == 1` is always a valid escape: a
    // pixel whose luminance is itself outside the range still lands in range.
    let y = luma709(v).clamp(0.0, 1.0);
    let mut t = 0.0f32;
    for c in 0..3 {
        if v[c] < 0.0 {
            // (1-t) v + t y >= 0  =>  t >= -v / (y - v)
            let d = y - v[c];
            if d > 1e-6 {
                t = t.max(-v[c] / d);
            }
        } else if v[c] > 1.0 {
            // (1-t) v + t y <= 1  =>  t >= (v - 1) / (v - y)
            let d = v[c] - y;
            if d > 1e-6 {
                t = t.max((v[c] - 1.0) / d);
            }
        }
    }
    let t = t.clamp(0.0, 1.0);
    let mut out = [0.0f32; 3];
    for (c, o) in out.iter_mut().enumerate() {
        // The final clamp is numerical belt-and-braces, not the gamut decision:
        // after the blend every channel is inside to within rounding.
        *o = (v[c] + (y - v[c]) * t).clamp(0.0, 1.0);
    }
    out
}

/// One white-balanced, normalised camera-RGB triple to 16-bit output.
///
/// Two clips happen here and they are not the same operation.
///
/// [`color::Render::clip_highlights`] runs **before** the matrix and is about
/// the *sensor*: a sample pinned at the container maximum is not a colour
/// measurement, and white balance has already carried the unpinned channels
/// past it, so the matrix must not be allowed to mix a pinned channel with an
/// unpinned one. Skipping it is what rendered blown neutral white as magenta
/// (M109). Where nothing is pinned it is exactly the identity.
///
/// The `clamp(0, 1)` below runs **after** the matrix and is about the *gamut*:
/// the matrix has negative off-diagonal terms and legitimately produces
/// out-of-gamut values for saturated scene colours, so a strong red can land at
/// `B < 0`. That is a real and lossy step, and it is the one place this pipeline
/// discards information it could have kept. Doing *that* one before the matrix
/// instead would clip in the wrong space and shift hue — which is why the
/// highlight clip has its own explicit ceiling rather than reusing this clamp.
#[inline]
fn develop_pixel(lin: [f32; 3], dev: &Develop) -> [u16; 3] {
    let v = match &dev.matrix {
        Some(r) => r.develop(lin),
        None => lin,
    };
    // The tone rendering is two stages either side of the transfer curve:
    // black/white placement in LINEAR light, where it is a physical statement
    // about flare and exposure; contrast in DISPLAY space, where it is a
    // perceptual one.
    //
    // The placement is a single gain derived from LUMINANCE and applied to all
    // three channels, not a per-channel subtraction. See `Tone::gain` -- the
    // per-channel form destroyed the weak channel on saturated subjects and
    // collapsed `coffee-bubbles` to a one-channel image.
    let v = match &dev.tone {
        Some(t) => {
            let g = t.gain(luma709(v));
            [v[0] * g, v[1] * g, v[2] * g]
        }
        None => v,
    };
    // Getting inside [0, 1] is a COLOUR decision on a viewing render and a
    // per-channel clamp on a measurement one. The measurement branch keeps the
    // clamp it always had, so its bytes cannot move; the picture gets the
    // hue- and luminance-preserving map.
    let v = if dev.tone.is_some() {
        gamut_map(v)
    } else {
        [
            v[0].clamp(0.0, 1.0),
            v[1].clamp(0.0, 1.0),
            v[2].clamp(0.0, 1.0),
        ]
    };
    let mut out = [0u16; 3];
    for c in 0..3 {
        let x = if dev.srgb { color::srgb_encode(v[c]) } else { v[c] };
        let x = match &dev.tone {
            Some(t) => s_curve(x, t.contrast),
            None => x,
        };
        out[c] = (x * u16::MAX as f32 + 0.5) as u16;
    }
    out
}

/// Develop a full-resolution CFA mosaic and write it.
///
/// `mosaic` is `width * height` samples in RGGB order, already black-subtracted,
/// white balanced and divided by the level range — but **not** clamped above,
/// because the demosaic and the matrix both need headroom to work in. `width`
/// and `height` are the sensor's, i.e. twice the merge's quad grid.
///
/// Rows are demosaiced in parallel and encoded in the same pass, so the
/// intermediate float RGB image is never materialised: peak extra memory is the
/// `u16` output plus one scratch row per worker.
/// Subsample stride for the tone pre-pass.
///
/// An order statistic does not need every pixel: at stride 7 on both axes a
/// 33 MP frame still contributes ~670k samples, which pins a 0.1th percentile
/// far tighter than the tone curve can resolve. The stride is coprime with the
/// 2-pixel CFA period so the sample does not land on one Bayer phase.
const TONE_STRIDE: usize = 7;

/// Measure the tone rendering from a demosaic-free approximation of the frame.
///
/// Each 2x2 quad is collapsed to one RGB triple and pushed through the same
/// matrix the real develop uses, which is enough for an order statistic and
/// avoids materialising the full float image the fast path exists to avoid.
fn tone_from_mosaic(m: &Mosaic, dev: &Develop) -> Tone {
    let mut lum = Vec::with_capacity((m.width / TONE_STRIDE + 1) * (m.height / TONE_STRIDE + 1));
    let mut y = 0;
    while y + 1 < m.height {
        let mut x = 0;
        while x + 1 < m.width {
            let i = y * m.width + x;
            // RGGB quad -> one triple.
            let r = m.data[i];
            let g = 0.5 * (m.data[i + 1] + m.data[i + m.width]);
            let b = m.data[i + m.width + 1];
            let v = match &dev.matrix {
                Some(rr) => rr.develop([r, g, b]),
                None => [r, g, b],
            };
            lum.push(luma709(v));
            x += 2 * TONE_STRIDE;
        }
        y += 2 * TONE_STRIDE;
    }
    Tone::from_luminance(&mut lum)
}

/// Measure the tone rendering from an already-materialised linear RGB image.
fn tone_from_rgb(width: usize, height: usize, rgb_lin: &[f32], dev: &Develop) -> Tone {
    let (px, _) = rgb_lin.as_chunks::<3>();
    let mut lum = Vec::with_capacity((width / TONE_STRIDE + 1) * (height / TONE_STRIDE + 1));
    let mut y = 0;
    while y < height {
        let mut x = 0;
        while x < width {
            let v = match &dev.matrix {
                Some(r) => r.develop(px[y * width + x]),
                None => px[y * width + x],
            };
            lum.push(luma709(v));
            x += TONE_STRIDE;
        }
        y += TONE_STRIDE;
    }
    Tone::from_luminance(&mut lum)
}

/// Fill in the measured tone if this render wants one, and say so on the
/// terminal. A render that silently invents a tone curve would be unreproducible
/// and unarguable; the numbers go on stderr with everything else.
fn resolve_tone(dev: &Develop, measure: impl FnOnce() -> Tone) -> Develop {
    if !dev.wants_tone || dev.tone.is_some() {
        return *dev;
    }
    let t = measure();
    eprintln!("{}", t.report());
    Develop {
        tone: Some(t),
        ..*dev
    }
}

pub fn write_demosaiced(
    path: &Path,
    width: usize,
    height: usize,
    mosaic: &[f32],
    dev: &Develop,
) -> Result<()> {
    assert_eq!(mosaic.len(), width * height);
    let m = Mosaic {
        data: mosaic,
        width,
        height,
    };
    let dev = &resolve_tone(dev, || tone_from_mosaic(&m, dev));
    let mut rgb = vec![0u16; width * height * 3];
    rgb.par_chunks_mut(width * 3).enumerate().for_each_init(
        || vec![0.0f32; width * 3],
        |scratch, (y, row)| {
            demosaic_row(&m, y, scratch);
            let (px_in, _) = scratch.as_chunks::<3>();
            let (px_out, _) = row.as_chunks_mut::<3>();
            for (src, dst) in px_in.iter().zip(px_out.iter_mut()) {
                *dst = develop_pixel(*src, dev);
            }
        },
    );
    write_rgb16_described(path, width as u32, height as u32, &rgb, dev)
}

/// Distance from the quad centre to the red and blue CFA sites, in binned
/// pixels. Red is at `-COSITE_SHIFT` on both axes and blue at `+COSITE_SHIFT`,
/// so each is resampled by the negation of its own offset.
///
/// This is geometry, not a tuning parameter: a 2x2 quad is one binned pixel
/// wide, and its corners are half of that from its centre on each axis.
const COSITE_SHIFT: f32 = 0.25;

/// Keys cubic-convolution weights for a fractional offset `t` in `[0, 1)`.
///
/// Keys, "Cubic convolution interpolation for digital image processing",
/// IEEE ASSP-29(6), 1981. `a = -1/2` is the choice that makes the interpolant
/// agree with the Taylor expansion of the sampled function to third order,
/// which is why it is the standard one and why it reproduces polynomials up to
/// degree two exactly. It is used here in preference to bilinear because this
/// correction must not cost more sharpness than the misregistration it removes,
/// and a bilinear kernel at `t = 0.25` is measurably wider.
///
/// The weights sum to one for every `t`, so a constant plane is invariant, and
/// at `t = 0` they are exactly `[0, 1, 0, 0]` — the identity.
#[inline]
fn keys_weights(t: f32) -> [f32; 4] {
    const A: f32 = -0.5;
    let (t2, t3) = (t * t, t * t * t);
    [
        A * (t3 - 2.0 * t2 + t),
        (A + 2.0) * t3 - (A + 3.0) * t2 + 1.0,
        -(A + 2.0) * t3 + (2.0 * A + 3.0) * t2 - A * t,
        -A * (t3 - t2),
    ]
}

/// Resample `src` at coordinates `(y + dy, x + dx)` with a separable Keys
/// kernel, clamping at the borders.
///
/// Separable because the kernel is: two 4-tap passes cost 8 multiplies per
/// pixel against 16 for the direct 2-D form, and the result is identical.
fn resample_shift(src: &[f32], width: usize, height: usize, dy: f32, dx: f32) -> Vec<f32> {
    debug_assert_eq!(src.len(), width * height);
    let taps = |d: f32| {
        let base = d.floor();
        (base as isize, keys_weights(d - base))
    };

    let (x0, wx) = taps(dx);
    let mut tmp = vec![0.0f32; width * height];
    tmp.par_chunks_mut(width)
        .zip(src.par_chunks(width))
        .for_each(|(dst, row)| {
            let last = width as isize - 1;
            for (x, out) in dst.iter_mut().enumerate() {
                let mut acc = 0.0f32;
                for (k, w) in wx.iter().enumerate() {
                    let j = (x as isize + x0 + k as isize - 1).clamp(0, last) as usize;
                    acc += w * row[j];
                }
                *out = acc;
            }
        });

    let (y0, wy) = taps(dy);
    let mut out = vec![0.0f32; width * height];
    out.par_chunks_mut(width).enumerate().for_each(|(y, dst)| {
        let last = height as isize - 1;
        for (k, w) in wy.iter().enumerate() {
            let yy = (y as isize + y0 + k as isize - 1).clamp(0, last) as usize;
            let row = &tmp[yy * width..yy * width + width];
            for (out, s) in dst.iter_mut().zip(row.iter()) {
                *out += w * s;
            }
        }
    });
    out
}

/// Develop a binned quad grid — one output pixel per 2x2 sensor quad — and
/// write it.
///
/// `rgb_lin` is `width * height * 3` interleaved camera-RGB samples, already
/// black-subtracted, white balanced and divided by the level range.
///
/// Red and blue are co-sited onto green's grid first — see the module header
/// for the geometry and the measurement. That happens **in linear light and
/// before the matrix**, because it is a correction of where the sensor sampled
/// and the matrix mixes channels: co-siting afterwards would be resampling a
/// blend of three already-misregistered planes.
///
/// **This is not the path that produces the corpus's linear TIFFs.** That one
/// lives in its callers and is byte-frozen; this is the same binning with a
/// colour matrix inserted, which is a different image on purpose.
pub fn write_binned(
    path: &Path,
    width: usize,
    height: usize,
    rgb_lin: &[f32],
    dev: &Develop,
) -> Result<()> {
    let rgb = develop_binned(width, height, rgb_lin, dev);
    write_rgb16_described(path, width as u32, height as u32, &rgb, dev)
}
/// The in-memory half of [`write_binned`]: co-site, develop, quantise.
///
/// Split out so the correction can be tested on values rather than on a file.
fn develop_binned(width: usize, height: usize, rgb_lin: &[f32], dev: &Develop) -> Vec<u16> {
    assert_eq!(rgb_lin.len(), width * height * 3);
    let (src, _) = rgb_lin.as_chunks::<3>();
    let dev = &resolve_tone(dev, || tone_from_rgb(width, height, rgb_lin, dev));

    let plane = |c: usize| src.iter().map(|p| p[c]).collect::<Vec<f32>>();
    let d = COSITE_SHIFT;
    let red = resample_shift(&plane(0), width, height, d, d);
    let blue = resample_shift(&plane(2), width, height, -d, -d);

    let mut rgb = vec![0u16; width * height * 3];
    let (dst, _) = rgb.as_chunks_mut::<3>();
    dst.par_iter_mut().enumerate().for_each(|(i, out)| {
        *out = develop_pixel([red[i], src[i][1], blue[i]], dev);
    });
    rgb
}

#[cfg(test)]
mod tests {
    use super::*;

    /// The A7C II's characterisation, MEASURED through `rawpy`/LibRaw in
    /// `docs/research/M26-colour-clipping-measured.md` §1 and reproduced
    /// through `rawler` in `docs/research/M85-output-correctness.md`.
    const A7C2: [[f32; 3]; 3] = [
        [0.7460, -0.2365, -0.0588],
        [-0.5687, 1.3442, 0.2474],
        [-0.0624, 0.1156, 0.6584],
    ];

    /// The default `Develop` must be the pre-M85 rendering, exactly.
    ///
    /// This is the tripwire on the measurement path: if a future edit gives
    /// `Develop` a non-identity default, every corpus number silently moves.
    #[test]
    fn the_default_development_is_the_identity_the_corpus_was_measured_on() {
        let dev = Develop::default();
        assert!(dev.matrix.is_none());
        assert!(!dev.srgb);
        for v in [0.0f32, 0.003, 0.25, 0.5, 0.75, 1.0] {
            let got = develop_pixel([v, v, v], &dev);
            let want = (v * u16::MAX as f32 + 0.5) as u16;
            assert_eq!(got, [want; 3], "value {v} was not passed through");
        }
        assert_eq!(dev.caveat(), "linear camera-native RGB");
    }

    /// `--linear-srgb` must apply the matrix and stop before the curve.
    ///
    /// This is the whole point of the mode, and it is a correctness dependency,
    /// not a convenience: the standing rule is that quality is never judged on
    /// an `--srgb` render, because the transfer curve moves every ratio a
    /// metric computes. The only alternative was camera-native, whose primaries
    /// are stated nowhere. If a future edit re-welds the matrix to the curve --
    /// which is exactly how this started, as a bare `if srgb` -- measurement
    /// silently goes back to happening in an undeclared space.
    #[test]
    fn linear_srgb_takes_the_matrix_and_stops_before_the_curve() {
        let m = color::camera_to_srgb(A7C2).expect("invertible");

        let lin = OutputSpace::LinearSrgb;
        assert!(lin.wants_matrix(), "linear sRGB must be colorimetric");
        assert!(!lin.applies_curve(), "linear sRGB must stay linear");
        assert!(!lin.is_measurement(), "it is not the byte-frozen path");
        let dev = lin.develop(Some(m));
        assert!(dev.matrix.is_some());
        assert!(!dev.srgb);
        assert_eq!(dev.caveat(), "linear sRGB (BT.709 primaries, D65, no transfer curve)");

        // The default must remain the byte-frozen measurement rendering, with
        // no matrix even when a characterisation is available.
        let cam = OutputSpace::CameraLinear;
        assert!(cam.is_measurement());
        let dev = cam.develop(Some(m));
        assert!(dev.matrix.is_none(), "the default must not acquire a matrix");
        assert!(!dev.srgb);

        // The viewing render keeps both.
        let dev = OutputSpace::Srgb.develop(Some(m));
        assert!(dev.matrix.is_some() && dev.srgb);

        // A body with no characterisation degrades to camera-native rather
        // than inventing a matrix, in every space.
        for s in [OutputSpace::CameraLinear, OutputSpace::LinearSrgb, OutputSpace::Srgb] {
            assert!(s.develop(None).matrix.is_none());
        }
    }

    /// The two colour flags are mutually exclusive, and asking for both is an
    /// error rather than a silent preference.
    #[test]
    fn asking_for_both_colour_flags_is_refused_rather_than_guessed() {
        assert_eq!(OutputSpace::from_flags(false, false).unwrap(), OutputSpace::CameraLinear);
        assert_eq!(OutputSpace::from_flags(true, false).unwrap(), OutputSpace::Srgb);
        assert_eq!(OutputSpace::from_flags(false, true).unwrap(), OutputSpace::LinearSrgb);
        assert!(
            OutputSpace::from_flags(true, true).is_err(),
            "both flags together must not silently resolve to one of them"
        );
        // The default is the measurement space, so a caller that forgets to
        // set it cannot accidentally move the corpus.
        assert!(OutputSpace::default().is_measurement());
    }

    /// The four development states must produce four *different* colour
    /// statements, and the two that are not sRGB must say so.
    ///
    /// The defect this guards is specific: a bare 16-bit RGB TIFF carries no
    /// colour space, so the measurement render (camera-native primaries) and
    /// the viewing render (sRGB) used to be byte-indistinguishable to any
    /// reader, and every reader defaults to assuming sRGB. That assumption is
    /// accidentally right for one of them and completely wrong for the other.
    /// If a future edit collapses these strings, that ambiguity comes back.
    #[test]
    fn every_development_state_states_a_different_colour_space_in_the_file() {
        let m = color::camera_to_srgb(A7C2).expect("invertible");
        let states = [
            Develop::default(),
            Develop {
                matrix: None,
                srgb: true,
                ..Develop::default()
            },
            Develop {
                matrix: Some(m),
                srgb: false,
                ..Develop::default()
            },
            Develop {
                matrix: Some(m),
                srgb: true,
                ..Develop::default()
            },
        ];
        let said: Vec<String> = states.iter().map(color_description).collect();
        for (i, a) in said.iter().enumerate() {
            for b in said.iter().skip(i + 1) {
                assert_ne!(a, b, "two development states describe themselves alike");
            }
        }
        // The two camera-native states must warn, and must not be mistakable
        // for sRGB by a reader skimming for the word.
        for dev in &states[..2] {
            let s = color_description(dev);
            assert!(s.contains("THIS IS NOT sRGB"), "unwarned: {s}");
            assert!(
                s.to_ascii_lowercase().contains("camera-native"),
                "unlabelled: {s}"
            );
        }
        // The white-balance ordering relative to the noise model is part of
        // the colour statement in every state, because the noise model is
        // calibrated before the gains and a reader that assumes otherwise
        // mis-scales per-channel noise by the WB gains.
        for dev in &states {
            let s = color_description(dev);
            assert!(s.contains("White balance"), "no WB ordering stated: {s}");
            assert!(s.contains("calibrated in raw DN"), "no noise order: {s}");
        }
    }

    /// The clamp is after the matrix, and both halves of that matter.
    ///
    /// **Half one: it clips real out-of-gamut colour.** A saturated camera
    /// green maps to a *negative* sRGB blue under this matrix, because the
    /// sensor's green filter passes wavelengths outside the sRGB gamut. That
    /// is a real, lossy step and this is where it happens.
    ///
    /// **Half two: values above 1.0 reach the matrix un-clamped.** The
    /// demosaic path deliberately does not clamp above before the matrix, so
    /// highlight headroom survives channel mixing instead of being flattened
    /// first. If a future edit moved the clamp earlier, the two inputs below
    /// would develop identically, and they must not.
    #[test]
    fn the_clamp_is_after_the_matrix_and_clips_real_out_of_gamut_colour() {
        let m = color::camera_to_srgb(A7C2).expect("invertible");
        let dev = Develop {
            matrix: Some(m),
            srgb: false,
            ..Develop::default()
        };

        let saturated_green = [0.2f32, 1.0, 0.15];
        let linear = color::apply(m.matrix(), saturated_green);
        assert!(
            linear[2] < 0.0 && linear[0] < 0.0,
            "the fixture is not out of gamut: it developed to {linear:?}"
        );
        let out = develop_pixel(saturated_green, &dev);
        assert_eq!(out[0], 0, "red should have clipped to zero, got {out:?}");
        assert_eq!(out[2], 0, "blue should have clipped to zero, got {out:?}");

        // The control: an in-gamut colour is not clipped, so the assertion
        // above is about gamut and not about the code clamping everything.
        let mild = [0.5f32, 0.5, 0.5];
        let out = develop_pixel(mild, &dev);
        assert!(
            out.iter().all(|v| *v > 0 && *v < u16::MAX),
            "an in-gamut neutral was clipped: {out:?}"
        );

        // Half two. `hot` exceeds 1.0 in red only. Clamping before the matrix
        // would collapse it onto `flat` exactly.
        let hot = [1.4f32, 0.55, 0.30];
        let flat = [1.0f32, 0.55, 0.30];
        assert_ne!(
            develop_pixel(hot, &dev),
            develop_pixel(flat, &dev),
            "an over-range input was clamped before the matrix saw it"
        );
        // ...and with no matrix there is nothing to see it, so they DO collapse.
        // That is the pre-M85 measurement path's behaviour, asserted so the two
        // paths cannot silently converge.
        let plain = Develop::default();
        assert_eq!(develop_pixel(hot, &plain), develop_pixel(flat, &plain));
    }

    /// A neutral survives the matrix as a neutral, at 16-bit precision.
    ///
    /// This is the property the row-normalisation in [`color::camera_to_srgb`]
    /// exists to guarantee, checked here at the point it actually ships rather
    /// than only in the unit that computes it.
    #[test]
    fn a_neutral_survives_the_shipping_path_as_a_neutral() {
        let dev = Develop {
            matrix: Some(color::camera_to_srgb(A7C2).expect("invertible")),
            srgb: true,
            ..Develop::default()
        };
        for v in [0.02f32, 0.2, 0.5, 0.9] {
            let out = develop_pixel([v, v, v], &dev);
            assert!(
                out[0].abs_diff(out[1]) <= 1 && out[1].abs_diff(out[2]) <= 1,
                "neutral {v} developed to {out:?}"
            );
        }
    }

    /// The whole-image writers agree with the per-pixel rule they are built
    /// from, including at the borders of the demosaic.
    #[test]
    fn the_writers_agree_with_the_per_pixel_development() {
        let (w, h) = (8usize, 6usize);
        let dev = Develop {
            matrix: Some(color::camera_to_srgb(A7C2).expect("invertible")),
            srgb: true,
            ..Develop::default()
        };
        // A flat mosaic demosaics to a flat image, so the expected answer is
        // known independently of the demosaic.
        let mosaic = vec![0.4f32; w * h];
        let dir = std::env::temp_dir().join("strehl-m85-image-out-test");
        std::fs::create_dir_all(&dir).unwrap();
        let path = dir.join("flat.tif");
        write_demosaiced(&path, w, h, &mosaic, &dev).unwrap();
        assert!(std::fs::metadata(&path).unwrap().len() > 0);
        let _ = std::fs::remove_file(&path);

        let rgb_lin = vec![0.4f32; w * h * 3];
        let path = dir.join("binned.tif");
        write_binned(&path, w, h, &rgb_lin, &dev).unwrap();
        assert!(std::fs::metadata(&path).unwrap().len() > 0);
        let _ = std::fs::remove_file(&path);
        let _ = std::fs::remove_dir(&dir);
    }

    /// The tags a print master is judged by, read back **out of the file**.
    ///
    /// This deliberately does not assert that [`PRINT_DPI`] equals `PRINT_DPI`.
    /// All 26 masters shipped carrying `XResolution 1/1`,
    /// `ResolutionUnit none` and `Software strehl 0.0.0` while every test in
    /// this file passed, because not one of them opened an artifact — the
    /// values came from `tiff`'s own defaults, several layers below anything
    /// under test. A constant-to-constant assertion would have passed then too.
    /// So this writes through the real encoder and decodes what landed.
    ///
    /// The unit is checked separately from the number because they fail
    /// independently, and `300` with `ResolutionUnit::None` is the *more*
    /// dangerous of the two failures: the physical size is just as undefined,
    /// but the file now looks configured to anyone who reads only tag 282.
    #[test]
    fn the_written_file_states_its_print_size_and_the_build_that_made_it() {
        let (w, h) = (4u32, 3u32);
        let dev = Develop {
            matrix: Some(color::camera_to_srgb(A7C2).expect("invertible")),
            srgb: true,
            ..Develop::default()
        };
        let dir = std::env::temp_dir().join("strehl-print-tags-test");
        std::fs::create_dir_all(&dir).unwrap();
        let path = dir.join("tags.tif");
        write_rgb16_described(&path, w, h, &vec![1000u16; (w * h) as usize * 3], &dev).unwrap();

        let file = std::fs::File::open(&path).unwrap();
        let mut dec = tiff::decoder::Decoder::new(std::io::BufReader::new(file))
            .expect("the writer produced a file the decoder cannot open");

        assert_eq!(
            dec.get_tag(Tag::ResolutionUnit).unwrap(),
            tiff::decoder::ifd::Value::Short(ResolutionUnit::Inch.to_u16()),
            "the file does not say which unit its resolution is in, so its \
             physical size is undefined whatever tags 282/283 say"
        );
        for tag in [Tag::XResolution, Tag::YResolution] {
            assert_eq!(
                dec.get_tag(tag).unwrap(),
                tiff::decoder::ifd::Value::Rational(PRINT_DPI, 1),
                "{tag:?} is not the declared print resolution"
            );
        }

        let software = dec.get_tag_ascii_string(Tag::Software).unwrap();
        assert_eq!(
            software,
            crate::SOFTWARE,
            "the file names a different build than the binary that wrote it"
        );
        assert!(
            software.contains('('),
            "tag 305 carries no build id, so the artifact cannot name its \
             source: {software}"
        );

        drop(dec);
        let _ = std::fs::remove_file(&path);
        let _ = std::fs::remove_dir(&dir);
    }

    /// The other half of the same decision: a **measurement** render carries
    /// neither the print size nor the build stamp, and that is not an oversight.
    ///
    /// This is the assertion that keeps `tests/byte-freezes.tsv` meaningful.
    /// Those rows hash the whole file, and [`crate::SOFTWARE`] contains the
    /// source commit, so stamping it here would make every frozen row a
    /// function of the commit it is checked at -- red on every commit, forever,
    /// and re-baselined by rote until nobody reads the diff. The freeze rows
    /// would still be *present*; they would simply have stopped meaning
    /// anything, which is the failure mode that is hard to see.
    ///
    /// Asserting the exact legacy string rather than "some string" is the
    /// point: `MEASUREMENT_SOFTWARE` may not drift by so much as a character
    /// without a frozen hash moving, so the test that guards it has to be
    /// exact.
    #[test]
    fn a_measurement_render_carries_neither_print_size_nor_build_stamp() {
        let (w, h) = (4u32, 3u32);
        let dev = Develop::measurement(true);
        assert!(
            icc_for(&dev).is_none(),
            "this arm is only a measurement render while it has no profile"
        );

        let dir = std::env::temp_dir().join("strehl-measurement-tags-test");
        std::fs::create_dir_all(&dir).unwrap();
        let path = dir.join("measure.tif");
        write_rgb16_described(&path, w, h, &vec![1000u16; (w * h) as usize * 3], &dev).unwrap();

        let file = std::fs::File::open(&path).unwrap();
        let mut dec = tiff::decoder::Decoder::new(std::io::BufReader::new(file)).unwrap();

        let software = dec.get_tag_ascii_string(Tag::Software).unwrap();
        assert_eq!(
            software, MEASUREMENT_SOFTWARE,
            "a measurement render's Software tag moved; every byte-freeze row \
             hashing this path has just changed for a reason unrelated to its \
             pixels"
        );
        assert!(
            !software.contains('('),
            "the build stamp reached a byte-frozen measurement render: {software}"
        );
        assert_eq!(
            dec.get_tag(Tag::ResolutionUnit).unwrap(),
            tiff::decoder::ifd::Value::Short(ResolutionUnit::None.to_u16()),
            "a measurement render declared a print resolution, which both \
             claims a physical size for camera-native data and moves the \
             frozen bytes"
        );

        drop(dec);
        let _ = std::fs::remove_file(&path);
        let _ = std::fs::remove_dir(&dir);
    }

    // ------------------------------------------------------------------
    // M95: chroma co-siting on the binned path.
    // `docs/research/M95-chroma-cositing.md`
    // ------------------------------------------------------------------

    /// The kernel's two structural properties, both of which the correction
    /// leans on: it sums to one, so a flat field cannot move; and at `t = 0` it
    /// is the identity, so a zero shift is exactly a no-op.
    ///
    /// The second property is why there is no "same blur, no shift" control for
    /// this operation — the blur is inseparable from the shift. The Python
    /// control that tried to build one (N3) returned digits identical to the
    /// uncorrected image and was retired for exactly this reason.
    #[test]
    fn the_keys_kernel_partitions_unity_and_is_the_identity_at_zero() {
        for i in 0..=100 {
            let t = i as f32 / 100.0;
            let w = keys_weights(t);
            let sum: f32 = w.iter().sum();
            assert!((sum - 1.0).abs() < 1e-6, "weights at t={t} sum to {sum}");
        }
        assert_eq!(keys_weights(0.0), [0.0, 1.0, 0.0, 0.0]);
    }

    /// The resample reproduces, exactly, the polynomials a third-order accurate
    /// interpolant is required to reproduce.
    ///
    /// This is the truth-by-construction test: the expected value is `f(x + d)`
    /// evaluated in closed form, not another implementation of the same idea.
    /// Borders are excluded because they are clamped, which is a deliberate
    /// choice and not an interpolation.
    #[test]
    fn the_cosite_resample_reproduces_low_order_polynomials_exactly() {
        let (w, h) = (16usize, 12usize);
        for (name, f) in [
            ("linear", (|x: f32, y: f32| 0.5 * x - 0.25 * y + 3.0) as fn(f32, f32) -> f32),
            ("quadratic", |x: f32, y: f32| 0.1 * x * x + 0.05 * y * y - 0.2 * x * y),
        ] {
            let src: Vec<f32> = (0..h)
                .flat_map(|y| (0..w).map(move |x| f(x as f32, y as f32)))
                .collect();
            for (dy, dx) in [(0.25f32, 0.25f32), (-0.25, -0.25)] {
                let out = resample_shift(&src, w, h, dy, dx);
                for y in 2..h - 2 {
                    for x in 2..w - 2 {
                        let want = f(x as f32 + dx, y as f32 + dy);
                        let got = out[y * w + x];
                        assert!(
                            (got - want).abs() < 1e-3,
                            "{name} at ({x},{y}) shift ({dy},{dx}): got {got}, want {want}"
                        );
                    }
                }
            }
        }
    }

    /// A constant plane is invariant, borders included.
    ///
    /// The border check is the point: clamping is the one place the kernel is
    /// not doing arithmetic on real neighbours, and a partition-of-unity kernel
    /// against clamped-but-equal samples must still return the constant.
    #[test]
    fn a_constant_plane_is_invariant_including_at_the_clamped_borders() {
        let (w, h) = (9usize, 7usize);
        let src = vec![0.375f32; w * h];
        for (dy, dx) in [(0.25f32, 0.25f32), (-0.25, -0.25)] {
            for v in resample_shift(&src, w, h, dy, dx) {
                assert!((v - 0.375).abs() < 1e-6, "constant moved to {v}");
            }
        }
    }

    /// Green is bit-identical through the binned path, and red and blue move in
    /// opposite directions by a known amount.
    ///
    /// This is the shipping-path form of the two controls that carry the
    /// measured result. **Green** is the null: it is not resampled, so every
    /// green sample must survive as the exact `u16` the uncorrected path would
    /// have written. A correction that improved the picture by blurring
    /// everything would fail here.
    ///
    /// **Red minus blue** is the direction control. On a field where red and
    /// blue are the same linear ramp of slope `s` in `x`, red is read at
    /// `x + 0.25` and blue at `x - 0.25`, so their developed difference must be
    /// `0.5 * s` — signed, so a correction applied backwards fails.
    #[test]
    fn the_binned_path_leaves_green_untouched_and_separates_red_from_blue() {
        let (w, h) = (24usize, 8usize);
        let dev = Develop::default(); // identity, so u16 = value * 65535
        let slope = 0.02f32;
        let mut lin = vec![0.0f32; w * h * 3];
        {
            let (px, _) = lin.as_chunks_mut::<3>();
            for (i, p) in px.iter_mut().enumerate() {
                let x = (i % w) as f32;
                let ramp = 0.2 + slope * x;
                // Green is deliberately a *different*, non-flat field, so that
                // "green survived" cannot be satisfied by it being constant.
                *p = [ramp, 0.9 - 0.01 * x, ramp];
            }
        }

        let out = develop_binned(w, h, &lin, &dev);
        let (px, _) = lin.as_chunks::<3>();
        let (got, _) = out.as_chunks::<3>();

        for (i, p) in px.iter().enumerate() {
            let want = develop_pixel([0.0, p[1], 0.0], &dev)[1];
            assert_eq!(got[i][1], want, "green moved at pixel {i}");
        }

        let want = (0.5 * slope * u16::MAX as f32).round() as i32;
        for y in 0..h {
            for x in 3..w - 3 {
                let p = got[y * w + x];
                let diff = p[0] as i32 - p[2] as i32;
                assert!(
                    (diff - want).abs() <= 2,
                    "red-blue separation at ({x},{y}) is {diff}, want {want}"
                );
            }
        }
    }

    /// The tone rendering must ride with the **viewing** render and only with
    /// it.
    ///
    /// This is the entire safety argument for adding a tone curve to a project
    /// whose corpus is 1786 measured facts. Every one of those measurements was
    /// taken on a linear render; if tone leaked onto the linear path, all of
    /// them would silently become measurements of something else. The byte-
    /// freeze tests would catch it for the two frozen rows, but this states the
    /// rule for every space rather than for the rows that happen to be frozen.
    #[test]
    fn tone_rides_with_the_viewing_render_and_never_with_a_measurement() {
        let m = color::camera_to_srgb(A7C2).expect("invertible");
        for (space, want) in [
            (OutputSpace::Srgb, true),
            (OutputSpace::LinearSrgb, false),
            (OutputSpace::CameraLinear, false),
        ] {
            assert_eq!(
                space.develop(Some(m)).wants_tone,
                want,
                "{space:?} disagrees about whether it is a photograph or a measurement"
            );
        }
        assert!(
            !Develop::measurement(true).wants_tone,
            "the measurement path asked for a tone curve"
        );
    }

    /// The S-curve is monotonic and endpoint-preserving.
    ///
    /// Monotonic because a tone curve that folds would invert local contrast --
    /// a highlight would render darker than the midtone next to it. Endpoint-
    /// preserving because black and white have already been placed by the time
    /// this runs, and a curve that moved them would undo that placement.
    #[test]
    fn the_contrast_curve_is_monotonic_and_leaves_the_endpoints_alone() {
        for strength in [0.0f32, 0.25, TONE_CONTRAST, 1.0] {
            assert!((s_curve(0.0, strength) - 0.0).abs() < 1e-6);
            assert!((s_curve(1.0, strength) - 1.0).abs() < 1e-6);
            assert!(
                (s_curve(0.5, strength) - 0.5).abs() < 1e-6,
                "the curve moved middle grey at strength {strength}"
            );
            let mut prev = f32::NEG_INFINITY;
            for i in 0..=1000 {
                let v = s_curve(i as f32 / 1000.0, strength);
                assert!(v >= prev - 1e-6, "curve folded at {i} for strength {strength}");
                prev = v;
            }
        }
        // Strength 0 must be exactly the identity, so the untoned rendering
        // stays reachable rather than being approximated.
        for i in 0..=100 {
            let x = i as f32 / 100.0;
            assert_eq!(s_curve(x, 0.0), x);
        }
    }

    /// The measured black and white points land where the develop claims.
    ///
    /// The veil the owner saw was a lifted black floor rendered through the
    /// steep toe of the sRGB curve. This asserts the two facts that remove it:
    /// the measured floor develops to 0, and the measured white percentile
    /// develops to the stated target rather than to some unstated fraction.
    #[test]
    fn the_tone_places_the_measured_floor_at_black_and_the_white_at_its_target() {
        // A floor well above zero -- the defect, reproduced.
        let mut lum: Vec<f32> = (0..10_000)
            .map(|i| 0.05 + 0.60 * (i as f32 / 9_999.0))
            .collect();
        let t = Tone::from_luminance(&mut lum);
        // `black` is the floor ACTUALLY REMOVED, so it is the measured floor
        // scaled by TONE_BLACK_FRACTION. The margin is deliberate: the floor is
        // scattered light, which is not uniform across the frame, so a global
        // constant is always too large somewhere.
        let want_black = 0.05 * TONE_BLACK_FRACTION;
        assert!(
            (t.black - want_black).abs() < 2e-3,
            "black point {} missed the effective floor {want_black}",
            t.black
        );

        let dev = Develop {
            matrix: None,
            srgb: true,
            tone: Some(t),
            wants_tone: true,
        };
        let at_floor = develop_pixel([t.black, t.black, t.black], &dev);
        // NOT `== [0, 0, 0]`. That assertion encoded the hard clamp, and the
        // hard clamp was the defect: it is what made everything below the
        // estimated black indistinguishable from everything else below it, and
        // on saturated subjects it deleted whole channels. The contract now is
        // that the floor develops to a genuinely dark value and that nothing
        // below it is destroyed.
        //
        // This ramp's floor is 0.05 against a 0.60 range -- pathological, and
        // about ten times the fraction any real capture shows. The realistic
        // case is pinned tightly below.
        assert!(
            at_floor[1] < (0.20 * u16::MAX as f32) as u16,
            "the floor developed to {at_floor:?}, which is not dark"
        );

        // A realistic floor: `flower-inner-edge-cpl` measures black 0.0047
        // against white 0.7116. There the toe must be nearly invisible.
        let real = Tone {
            black: 0.0047,
            white: 0.7116,
            contrast: TONE_CONTRAST,
        };
        let real_dev = Develop {
            matrix: None,
            srgb: true,
            tone: Some(real),
            wants_tone: true,
        };
        let real_floor = develop_pixel([real.black, real.black, real.black], &real_dev);
        assert!(
            real_floor[1] < (0.04 * u16::MAX as f32) as u16,
            "a realistic floor developed to {real_floor:?} -- the veil is back"
        );
        // And it is not zero, because zero is unrecoverable.
        assert!(
            real_floor[1] > 0,
            "the realistic floor hard-clamped to zero after all"
        );

        // The 99.9th percentile of the ramp must land on TONE_WHITE_TARGET in
        // linear light, i.e. on the sRGB encoding of 0.90 after the curve --
        // then unchanged by the S-curve only insofar as the curve maps it.
        let want = (s_curve(color::srgb_encode(TONE_WHITE_TARGET), t.contrast)
            * u16::MAX as f32)
            .round() as i32;
        let hi = lum[(0.999 * (lum.len() - 1) as f32) as usize];
        let got = develop_pixel([hi, hi, hi], &dev)[1] as i32;
        assert!(
            (got - want).abs() <= 64,
            "the white percentile developed to {got}, want {want}"
        );
    }

    /// A tone curve must not turn a neutral into a colour cast.    ///
    /// It is applied per channel, which is what restores saturation, and that
    /// is exactly the shape of operation that can tint greys if the three
    /// channels are given different endpoints. They are not -- the black and
    /// white points are scalars measured from luminance -- and this pins that
    /// down, because measuring them per channel would be an easy and
    /// plausible-looking future "improvement" that silently tints the image.
    #[test]
    fn the_tone_curve_does_not_tint_a_neutral() {
        let mut lum: Vec<f32> = (0..2_000).map(|i| 0.01 + i as f32 / 2_000.0).collect();
        let dev = Develop {
            matrix: Some(color::camera_to_srgb(A7C2).expect("invertible")),
            srgb: true,
            tone: Some(Tone::from_luminance(&mut lum)),
            wants_tone: true,
        };
        for v in [0.05f32, 0.2, 0.5, 0.9] {
            let out = develop_pixel([v, v, v], &dev);
            assert!(
                out[0].abs_diff(out[1]) <= 1 && out[1].abs_diff(out[2]) <= 1,
                "neutral {v} developed to {out:?} once toned"
            );
        }
    }

    /// **The test that was missing, and why it was missing.**
    ///
    /// Every tone test in this crate fed `develop_pixel` a NEUTRAL or a scalar
    /// ramp. `the_tone_curve_does_not_tint_a_neutral` above was written
    /// deliberately, to pin down a real risk, and it is correct as far as it
    /// goes -- but a luminance-derived scalar black cannot tint a neutral *by
    /// construction*, so it could never fail. The suite proved the one property
    /// the design could not violate and left the one it did violate untested.
    ///
    /// The failing case is a SATURATED pixel, where the weak channels sit below
    /// the luminance-derived black. Under the old per-channel subtraction they
    /// went negative and clamped to zero: `coffee-bubbles` reached 83.9%
    /// zero-green and 88.3% zero-blue and rendered as a flat one-channel red
    /// field. Nothing here is neutral, so nothing here was covered.
    #[test]
    fn the_tone_curve_preserves_chromaticity_on_a_saturated_pixel() {
        // A realistic tone, and `contrast: 0` with `srgb: false` so the only
        // stage under test is the black/white placement. The display-space
        // stages after it are per-channel BY DESIGN -- that is what restores
        // saturation -- so they must be switched off here or this would be
        // asserting against the feature instead of against the defect.
        //
        // This deliberately runs through `develop_pixel`, not through
        // `Tone::gain`. An earlier draft called `gain` directly and could never
        // have failed: `gain` returns one scalar, so chromaticity preservation
        // is true of it by construction. Reinstating the original defect
        // verbatim left that draft GREEN. The property only means something
        // when it is asserted of the pipeline that actually renders pixels.
        let tone = Tone {
            black: 0.0047,
            white: 0.7116,
            contrast: 0.0,
        };
        let dev = Develop {
            matrix: None,
            srgb: false,
            tone: Some(tone),
            wants_tone: true,
        };

        // Dark, strongly saturated colours whose weak channels are BELOW the
        // black point -- exactly the population that was destroyed.
        for v in [
            [0.30f32, 0.004, 0.002],
            [0.004, 0.30, 0.002],
            [0.002, 0.004, 0.30],
            [0.12, 0.0045, 0.003],
        ] {
            assert!(
                v.iter().any(|&c| c < tone.black),
                "test case {v:?} does not exercise the failing regime"
            );
            let out = develop_pixel(v, &dev);
            for (a, b) in [(0, 1), (1, 2), (0, 2)] {
                let before = (v[a] / v[b]) as f64;
                let after = out[a] as f64 / out[b] as f64;
                let rel = (after - before).abs() / before;
                // The bound is set by 16-bit quantisation of the weak channel,
                // which lands around 300 DN here, not by the algorithm -- which
                // preserves the ratio exactly.
                assert!(
                    rel < 0.02,
                    "channel ratio {a}/{b} moved {rel:.4} on {v:?} -> {out:?}"
                );
            }
        }
    }

    /// No channel carrying signal may be driven to zero.
    ///
    /// This is the property whose absence deleted structure rather than noise:
    /// on `foam` the crushed pixels had a median 3x3 local range of 847 DN
    /// against a frame median of 1774 DN. A zero is unrecoverable, so this is
    /// the difference between "darker than I would like" and "gone".
    #[test]
    fn the_tone_curve_cannot_zero_a_channel_that_carries_signal() {
        let mut lum: Vec<f32> = (0..2_000).map(|i| 0.01 + i as f32 / 2_000.0).collect();
        let dev = Develop {
            matrix: None,
            srgb: true,
            tone: Some(Tone::from_luminance(&mut lum)),
            wants_tone: true,
        };
        for v in [
            [0.30f32, 0.004, 0.002],
            [0.20, 0.002, 0.001],
            [0.05, 0.001, 0.0005],
        ] {
            let out = develop_pixel(v, &dev);
            assert!(
                out.iter().all(|&c| c > 0),
                "developed {v:?} to {out:?} -- a channel with signal reached zero"
            );
        }
    }

    /// The toe is strictly monotonic, so shadow detail is compressed and never
    /// merged.
    ///
    /// A hard clamp maps every value below the black point onto the same zero,
    /// which is exactly how distinct shadow tones stop being distinguishable.
    /// Two different inputs must never produce the same output.
    #[test]
    fn the_tone_toe_never_merges_two_shadow_values() {
        let mut lum: Vec<f32> = (0..2_000).map(|i| 0.01 + i as f32 / 2_000.0).collect();
        let tone = Tone::from_luminance(&mut lum);
        let placed = |l: f32| l * tone.gain(l);
        let mut prev = placed(0.0);
        // Sweep from true zero up through and well past the black point.
        for i in 1..=4_000 {
            let l = tone.black * 4.0 * i as f32 / 4_000.0;
            let cur = placed(l);
            assert!(
                cur > prev,
                "toe is flat at luminance {l}: {prev} -> {cur} (black {})",
                tone.black
            );
            prev = cur;
        }
        assert_eq!(placed(0.0), 0.0, "true black must stay black");
    }

    /// The gamut map is the identity on everything already inside the gamut.
    ///
    /// This is the whole safety argument, and it is the same one
    /// `clip_highlights` makes: a render with no out-of-gamut pixels cannot
    /// move by one bit, so this change cannot quietly restyle images it was not
    /// meant to touch.
    #[test]
    fn the_gamut_map_is_exactly_the_identity_inside_the_gamut() {
        for r in 0..=10 {
            for g in 0..=10 {
                for b in 0..=10 {
                    let v = [r as f32 / 10.0, g as f32 / 10.0, b as f32 / 10.0];
                    assert_eq!(gamut_map(v), v, "moved an in-gamut colour {v:?}");
                }
            }
        }
    }

    /// It brings out-of-gamut colour inside, and preserves luminance while
    /// doing it.
    ///
    /// Luminance preservation is the property a per-channel clamp does not
    /// have, and it is the reason to prefer this: raising a negative blue to
    /// zero makes the pixel lighter than the colour it stands in for. MEASURED
    /// on `flower-inner-edge-cpl`, the clamp's luminance error at p99.9 is
    /// 0.00117 against this map's 0.00000.
    #[test]
    fn the_gamut_map_lands_inside_and_keeps_the_luminance() {
        let cases = [
            [0.30f32, 0.60, -0.05],  // the common one: slightly negative blue
            [-0.20, 0.50, 0.40],
            [0.10, 1.30, 0.20],      // out at the top instead
            [1.40, 0.90, -0.30],     // out at both ends at once
            [0.02, 0.02, -0.001],    // near black, a hair negative
        ];
        for v in cases {
            let out = gamut_map(v);
            for (c, o) in out.iter().enumerate() {
                assert!(
                    (0.0..=1.0).contains(o),
                    "channel {c} of {v:?} left the gamut at {o}"
                );
            }
            let want = luma709(v).clamp(0.0, 1.0);
            assert!(
                (luma709(out) - want).abs() < 1e-4,
                "{v:?} -> {out:?} changed luminance {want} -> {}",
                luma709(out)
            );
        }
    }

    /// It desaturates rather than reaching for grey.
    ///
    /// The minimal blend matters: a map that went further than necessary would
    /// wash out every saturated colour in the frame, which is the failure mode
    /// of a naive "clamp by desaturating to neutral". A colour that is barely
    /// outside must come back barely changed.
    #[test]
    fn the_gamut_map_moves_a_colour_only_as_far_as_it_must() {
        let barely = [0.40f32, 0.55, -0.002];
        let out = gamut_map(barely);
        let moved: f32 = (0..3).map(|c| (out[c] - barely[c]).abs()).sum();
        assert!(
            moved < 0.02,
            "a colour 0.002 outside the gamut moved by {moved}: {barely:?} -> {out:?}"
        );
        // ... and a deeply out-of-gamut colour must still be visibly coloured,
        // not flattened to grey.
        let deep = [0.90f32, 0.20, -0.40];
        let out = gamut_map(deep);
        let spread = out[0].max(out[1]).max(out[2]) - out[0].min(out[1]).min(out[2]);
        assert!(spread > 0.15, "a saturated colour flattened to {out:?}");
    }

    /// The measurement paths keep the per-channel clamp they always had.
    ///
    /// The gamut map rides with the tone rendering, so `--linear-srgb`,
    /// camera-linear and `Develop::measurement` are arithmetically untouched.
    /// If that ever stops being true, every frozen number in the corpus is
    /// measuring something new, and this is the test that says so.
    #[test]
    fn a_measurement_render_still_clamps_per_channel_and_does_not_gamut_map() {
        let m = color::camera_to_srgb(A7C2).expect("invertible");
        let dev = Develop {
            matrix: Some(m),
            srgb: false,
            tone: None,
            wants_tone: false,
        };
        // A colour the matrix sends out of gamut on two channels at once.
        let saturated_green = [0.2f32, 1.0, 0.15];
        let lin = color::apply(m.matrix(), saturated_green);
        assert!(lin[0] < 0.0 && lin[2] < 0.0, "fixture is in gamut: {lin:?}");
        let out = develop_pixel(saturated_green, &dev);
        assert_eq!(
            [out[0], out[2]],
            [0, 0],
            "a measurement render gamut-mapped instead of clamping: {out:?}"
        );
    }

    // -- ICC ---------------------------------------------------------------

    /// The derivation is checked against the columns published in the ICC's own
    /// sRGB profile, NOT against itself.
    ///
    /// A test that re-ran my arithmetic and compared it to my arithmetic would
    /// pass for any matrix at all, including a transposed or unadapted one.
    /// These four numbers come from outside this file, so the derivation can
    /// actually fail them.
    #[test]
    fn the_derived_primaries_match_the_published_srgb_icc_columns() {
        let m = srgb_to_xyz_d50();
        let want = [
            [0.4360, 0.2225, 0.0139],
            [0.3851, 0.7169, 0.0971],
            [0.1431, 0.0606, 0.7141],
        ];
        for (c, col) in want.iter().enumerate() {
            for (r, w) in col.iter().enumerate() {
                assert!(
                    (m[r][c] - w).abs() < 5e-4,
                    "column {c} row {r}: derived {:.6}, published {w:.6}",
                    m[r][c]
                );
            }
        }
    }

    /// The defining property of a correctly adapted matrix: white in gives the
    /// PCS white out. This catches an unadapted (D65) matrix, which the
    /// published-columns test would also catch, but this one states *why*.
    #[test]
    fn the_primary_columns_sum_to_the_pcs_white() {
        let m = srgb_to_xyz_d50();
        for r in 0..3 {
            let sum: f64 = (0..3).map(|c| m[r][c]).sum();
            assert!(
                (sum - PCS_D50[r]).abs() < 1e-3,
                "row {r} sums to {sum:.6}, PCS D50 is {:.6}",
                PCS_D50[r]
            );
        }
    }

    /// The TRC must store device-to-linear. Storing the inverse renders with
    /// visibly wrong contrast and nothing else complains.
    #[test]
    fn the_transfer_curve_is_stored_in_the_decoding_direction() {
        assert!((srgb_eotf(0.0)).abs() < 1e-9);
        assert!((srgb_eotf(1.0) - 1.0).abs() < 1e-9);
        // Mid-grey 0.5 encoded is ~0.214 linear. If this reads ~0.735 the
        // curve has been stored backwards.
        assert!(
            (srgb_eotf(0.5) - 0.2140).abs() < 1e-3,
            "srgb_eotf(0.5) = {:.4}",
            srgb_eotf(0.5)
        );
    }

    #[test]
    fn the_profile_is_structurally_well_formed_and_deterministic() {
        for linear in [false, true] {
            let p = icc_srgb_v2(linear);
            assert_eq!(
                u32::from_be_bytes(p[0..4].try_into().unwrap()) as usize,
                p.len(),
                "header size field disagrees with the actual length"
            );
            assert_eq!(&p[36..40], b"acsp", "missing ICC file signature");
            assert_eq!(&p[12..16], b"mntr");
            assert_eq!(&p[16..20], b"RGB ");
            assert_eq!(&p[20..24], b"XYZ ");
            assert_eq!(
                u32::from_be_bytes(p[8..12].try_into().unwrap()),
                0x0210_0000,
                "must stay v2 for reader compatibility"
            );
            // Canonical D50 encoding in the header's PCS illuminant field.
            assert_eq!(&p[68..80], &[0, 0, 0xF6, 0xD6, 0, 1, 0, 0, 0, 0, 0xD3, 0x2D]);

            // Every tag must lie inside the file and start 4-byte aligned.
            let n = u32::from_be_bytes(p[128..132].try_into().unwrap()) as usize;
            assert!(n >= 9, "too few tags: {n}");
            let mut sigs = Vec::new();
            for i in 0..n {
                let e = 132 + 12 * i;
                let sig = &p[e..e + 4];
                let off = u32::from_be_bytes(p[e + 4..e + 8].try_into().unwrap()) as usize;
                let len = u32::from_be_bytes(p[e + 8..e + 12].try_into().unwrap()) as usize;
                assert!(off % 4 == 0, "tag {sig:?} is not 4-byte aligned");
                assert!(off + len <= p.len(), "tag {sig:?} runs past the end");
                sigs.push(std::str::from_utf8(sig).unwrap().to_string());
            }
            for req in ["desc", "wtpt", "rXYZ", "gXYZ", "bXYZ", "rTRC", "gTRC", "bTRC", "cprt"] {
                assert!(sigs.contains(&req.to_string()), "missing required tag {req}");
            }
            // Determinism: a clock-derived date would break every byte-freeze.
            assert_eq!(p, icc_srgb_v2(linear), "profile is not deterministic");
        }
    }

    /// The camera-native paths must get NO profile.
    ///
    /// Embedding sRGB there would turn a loud, human-readable warning into a
    /// machine-readable lie that a colour-managed reader obeys silently.
    #[test]
    fn only_the_colorimetric_paths_get_a_profile() {
        let m = color::camera_to_srgb(A7C2).expect("invertible");
        let with = |space: OutputSpace, mat| icc_for(&space.develop(mat)).is_some();

        assert!(with(OutputSpace::Srgb, Some(m)), "sRGB must be labelled");
        assert!(with(OutputSpace::LinearSrgb, Some(m)), "linear sRGB must be labelled");
        assert!(
            !with(OutputSpace::CameraLinear, Some(m)),
            "camera-native must NOT claim to be sRGB, even when a matrix exists"
        );
        assert!(
            !with(OutputSpace::CameraLinear, None),
            "camera-native without a characterisation must not be labelled"
        );
        // The fourth row of the decision table, and the dangerous one: the
        // body has no characterisation, so `--srgb` yields camera primaries
        // carrying an sRGB transfer curve. It looks like sRGB in every way a
        // reader can check except the primaries, which is exactly why it must
        // not be told it is sRGB. Omitting this case left the suite passing
        // for an `icc_for` that keyed on `dev.srgb` alone.
        assert!(
            !with(OutputSpace::Srgb, None),
            "an uncharacterised body's --srgb render must NOT claim sRGB \
             primaries it does not have"
        );

        // The two colorimetric profiles must differ, or the transfer curve is
        // not actually being varied and one of the two files is mislabelled.
        let srgb = icc_for(&OutputSpace::Srgb.develop(Some(m))).unwrap();
        let lin = icc_for(&OutputSpace::LinearSrgb.develop(Some(m))).unwrap();
        assert_ne!(srgb, lin, "sRGB and linear sRGB got the same profile");
    }

    /// Locate one ICC tag's payload inside a profile, by signature.
    ///
    /// Deliberately a byte walk of the tag table rather than a field of a
    /// parsed struct: the point of the test below is to read what **landed in
    /// the file**, and a parser shared with the writer would agree with the
    /// writer by construction.
    fn icc_tag<'a>(p: &'a [u8], want: &[u8; 4]) -> Option<&'a [u8]> {
        let n = u32::from_be_bytes(p[128..132].try_into().ok()?) as usize;
        for i in 0..n {
            let e = 132 + 12 * i;
            if &p[e..e + 4] == want {
                let off = u32::from_be_bytes(p[e + 4..e + 8].try_into().ok()?) as usize;
                let len = u32::from_be_bytes(p[e + 8..e + 12].try_into().ok()?) as usize;
                return p.get(off..off + len);
            }
        }
        None
    }

    /// The embedded profile must state the transfer curve the pixels were
    /// actually written with, read back **out of a real file**.
    ///
    /// **The hole this closes, and why the existing tests could not.**
    /// [`only_the_colorimetric_paths_get_a_profile`] asserts that a profile is
    /// present on the two colorimetric paths, absent on the camera-native ones,
    /// and that the two colorimetric profiles are `assert_ne!` to each other.
    /// **Every one of those passes if the two arms of [`icc_for`] are
    /// exchanged** -- `--srgb` labelled linear and `--linear-srgb` labelled
    /// sRGB -- because an inequality fixes no identity. Nothing else in the
    /// crate could tell the two apart either, since
    /// [`the_profile_is_structurally_well_formed_and_deterministic`] checks
    /// each profile against itself and
    /// [`the_derived_primaries_match_the_published_srgb_icc_columns`] checks
    /// only the matrix, which the two profiles share.
    ///
    /// That swap is not a cosmetic defect. It is a machine-readable
    /// instruction to transform every pixel, and the transform was measured:
    /// `experiments/BUILD-RENDER-icc/potency.py` puts a linear-for-sRGB TRC
    /// swap at **50.39 DN mean, 73 DN max, on 99.5% of pixels**, and
    /// `experiments/BUILD-RENDER-print/icc_potency.py` ARM B moves **92 DN**
    /// by substituting a different profile onto identical pixels. This project
    /// has a standing rule that a wrong profile is worse than none; until this
    /// test existed, only the *none* half of it was enforced.
    ///
    /// **What can make it fail** (rule 20): exchanging the two arms of
    /// `icc_for`; storing the TRC in the encoding direction; giving `gTRC` or
    /// `bTRC` a different curve from `rTRC`; handing a profile to a
    /// camera-native or tone-in-linear render. The first of those is the one
    /// that was live, and it is the commissioning arm recorded in
    /// `docs/research/BUILD-OUTPUT.md`.
    #[test]
    fn the_embedded_profile_states_the_transfer_curve_the_pixels_carry() {
        let m = color::camera_to_srgb(A7C2).expect("invertible");
        // A resolved tone, as the writers fill in for a viewing render. The
        // numbers are a plausible mid-corpus pair and nothing depends on them;
        // what matters is that `tone` is `Some`, because that is the field the
        // third `None` arm of `icc_for` keys on.
        let toned = Tone {
            black: 0.008_30,
            white: 1.004_73,
            contrast: TONE_CONTRAST,
        };
        let with_tone = |matrix, srgb| Develop {
            matrix,
            srgb,
            tone: Some(toned),
            wants_tone: true,
        };

        // `Some(true)` = a profile whose TRC is sRGB's; `Some(false)` = a
        // profile whose TRC is the identity; `None` = no profile at all.
        let cases: [(&str, Develop, Option<bool>); 6] = [
            (
                "--srgb, as the writer resolves it",
                with_tone(Some(m), true),
                Some(true),
            ),
            (
                "--srgb with no tone rendering",
                OutputSpace::Srgb.develop(Some(m)),
                Some(true),
            ),
            (
                "--linear-srgb",
                OutputSpace::LinearSrgb.develop(Some(m)),
                Some(false),
            ),
            ("camera-native linear", Develop::measurement(false), None),
            (
                "camera-native with an sRGB curve",
                Develop::measurement(true),
                None,
            ),
            (
                "colorimetric, tone applied in LINEAR light",
                with_tone(Some(m), false),
                None,
            ),
        ];

        let dir = std::env::temp_dir().join("strehl-icc-trc-test");
        std::fs::create_dir_all(&dir).unwrap();
        let (w, h) = (4u32, 3u32);

        for (label, dev, want) in cases {
            let path = dir.join(format!("{}.tif", label.replace(['-', ' ', ','], "_")));
            write_rgb16_described(&path, w, h, &vec![1000u16; (w * h) as usize * 3], &dev).unwrap();
            let file = std::fs::File::open(&path).unwrap();
            let mut dec = tiff::decoder::Decoder::new(std::io::BufReader::new(file)).unwrap();
            let got = dec.get_tag_u8_vec(Tag::IccProfile).ok();
            drop(dec);
            let _ = std::fs::remove_file(&path);

            let Some(want_srgb_curve) = want else {
                assert!(
                    got.is_none(),
                    "{label}: a profile reached a render no profile in this \
                     module describes, which is the one outcome this policy \
                     calls worse than an unlabelled file"
                );
                continue;
            };
            let p = got.unwrap_or_else(|| panic!("{label}: no ICC profile in the file"));

            // The curve, read out of the file's own tag table.
            let trc = icc_tag(&p, b"rTRC").unwrap_or_else(|| panic!("{label}: no rTRC"));
            assert_eq!(&trc[0..4], b"curv", "{label}: rTRC is not a curveType");
            let count = u32::from_be_bytes(trc[4 + 4..4 + 8].try_into().unwrap()) as usize;
            if want_srgb_curve {
                assert!(
                    count > 1,
                    "{label}: the pixels carry the sRGB transfer curve but the \
                     profile stores an identity/gamma TRC (count {count}). A \
                     reader obeying this will linearise data that is already \
                     linear."
                );
                let at = |i: usize| -> f64 {
                    let o = 12 + 2 * i;
                    f64::from(u16::from_be_bytes(trc[o..o + 2].try_into().unwrap())) / 65535.0
                };
                assert!(at(0).abs() < 1e-6, "{label}: TRC(0) = {}", at(0));
                assert!(
                    (at(count - 1) - 1.0).abs() < 1e-6,
                    "{label}: TRC(1) = {}",
                    at(count - 1)
                );
                // Mid-point 0.5 encoded is 0.2140 linear. 0.735 is the same
                // curve stored backwards, and renders with wrong contrast
                // while every structural check still passes.
                let mid = at(count / 2);
                assert!(
                    (mid - 0.2140).abs() < 5e-3,
                    "{label}: TRC(0.5) = {mid:.4}, expected the sRGB decoding \
                     direction 0.2140 (0.735 means it is stored backwards)"
                );
            } else {
                assert_eq!(
                    count, 0,
                    "{label}: the pixels are LINEAR but the profile stores a \
                     {count}-point transfer curve. A reader obeying this \
                     applies a decode that was never encoded."
                );
            }

            // One curve for three channels, or the file has a colour cast that
            // only a colour-managed reader sees.
            for sig in [b"gTRC", b"bTRC"] {
                assert_eq!(
                    icc_tag(&p, sig).unwrap(),
                    trc,
                    "{label}: {} differs from rTRC",
                    std::str::from_utf8(sig).unwrap()
                );
            }

            // The human-readable half must agree with the machine-readable
            // half. A profile named "gamma 1.0" carrying the sRGB curve is a
            // mislabel a person would act on.
            let desc = icc_tag(&p, b"desc").unwrap();
            let name = String::from_utf8_lossy(&desc[12..]);
            assert_eq!(
                name.contains("gamma 1.0"),
                !want_srgb_curve,
                "{label}: profile description and profile curve disagree: {}",
                name.split('\0').next().unwrap_or("")
            );

            // The primaries that landed in the file, against the derivation
            // this module publishes. Catches a garbled or transposed matrix
            // that survives the in-memory tests.
            let want_m = srgb_to_xyz_d50();
            for (c, sig) in [b"rXYZ", b"gXYZ", b"bXYZ"].into_iter().enumerate() {
                let t = icc_tag(&p, sig).unwrap();
                for r in 0..3 {
                    let o = 8 + 4 * r;
                    let v =
                        f64::from(i32::from_be_bytes(t[o..o + 4].try_into().unwrap())) / 65536.0;
                    assert!(
                        (v - want_m[r][c]).abs() < 2e-5,
                        "{label}: column {c} row {r} landed at {v:.6}, derived \
                         {:.6}",
                        want_m[r][c]
                    );
                }
            }
        }
        let _ = std::fs::remove_dir(&dir);
    }
}
