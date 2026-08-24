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

use std::fs::File;
use std::io::BufWriter;
use std::path::Path;

use anyhow::{Context, Result};
use rayon::prelude::*;
use strehl_core::color;
use strehl_core::demosaic::{Mosaic, demosaic_row};
use tiff::encoder::{TiffEncoder, colortype};

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

/// Interleaved RGB, 16 bits per channel.
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
    /// Camera RGB to linear sRGB, from [`color::camera_to_srgb`].
    ///
    /// `None` means **camera-native RGB is emitted unchanged**, which is the
    /// pre-M85 behaviour and is what the corpus's measurements were taken on.
    /// It is also what happens when the decoder has no characterisation for the
    /// body: emitting camera-native and saying so beats inventing a matrix.
    pub matrix: Option<[[f32; 3]; 3]>,
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
/// The clamp sits between the matrix and the curve because the matrix has
/// negative off-diagonal terms and legitimately produces out-of-gamut values
/// for saturated scene colours: a strong red can land at `B < 0`. Clamping
/// there is *gamut clipping*, a real and lossy step, and it is the one place
/// this pipeline discards information it could have kept. Doing it before the
/// matrix instead would clip in the wrong space and shift hue.
#[inline]
fn develop_pixel(lin: [f32; 3], dev: &Develop) -> [u16; 3] {
    let v = match &dev.matrix {
        Some(m) => color::apply(m, lin),
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
    write_rgb16(path, width as u32, height as u32, &rgb)
}

/// Develop a binned quad grid — one output pixel per 2x2 sensor quad — and
/// write it.
///
/// `rgb_lin` is `width * height * 3` interleaved camera-RGB samples, already
/// black-subtracted, white balanced and divided by the level range.
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
    assert_eq!(rgb_lin.len(), width * height * 3);
    let mut rgb = vec![0u16; width * height * 3];
    let (src, _) = rgb_lin.as_chunks::<3>();
    let (dst, _) = rgb.as_chunks_mut::<3>();
    for (s, d) in src.iter().zip(dst.iter_mut()) {
        *d = develop_pixel(*s, dev);
    }
    write_rgb16(path, width as u32, height as u32, &rgb)
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
        let linear = color::apply(&m, saturated_green);
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
}
