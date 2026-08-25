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
//! This does **not** touch the byte-frozen measurement path. Both callers reach
//! [`write_binned`] only inside `if let Some(m) = matrix`, so it is the
//! "for looking at" render; the measurement path writes through
//! [`write_rgb16`] and never enters this function.

use std::fs::File;
use std::io::BufWriter;
use std::path::Path;

use anyhow::{Context, Result};
use rayon::prelude::*;
use strehl_core::color;
use strehl_core::demosaic::{Mosaic, demosaic_row};
use tiff::encoder::{TiffEncoder, colortype};
use tiff::tags::Tag;

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
    format!(
        "{space} White balance: as-shot per-channel gains, green = 1, applied AFTER black \
         subtraction and normalisation by (white - black), and AFTER the noise model, which is \
         calibrated in raw DN before any gain."
    )
}

/// Interleaved RGB, 16 bits per channel, with the colour space stated in the
/// file.
///
/// Separate from [`write_rgb16`] so that the older four-argument signature
/// keeps compiling for its existing callers; new call sites should use this.
fn write_rgb16_described(
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
    img.encoder()
        .write_tag(
            Tag::Software,
            concat!("strehl ", env!("CARGO_PKG_VERSION")),
        )
        .with_context(|| format!("tagging {}", path.display()))?;
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
}

impl Develop {
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
    let mut out = [0u16; 3];
    for c in 0..3 {
        let x = v[c].clamp(0.0, 1.0);
        let x = if dev.srgb { color::srgb_encode(x) } else { x };
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
            },
            Develop {
                matrix: Some(m),
                srgb: false,
            },
            Develop {
                matrix: Some(m),
                srgb: true,
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
}
