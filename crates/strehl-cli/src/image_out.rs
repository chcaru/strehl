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
    /// Linear value mapped to 0. The measured flare/noise floor of the frame.
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
        let black = at(TONE_BLACK_PCT);
        let white_src = at(TONE_WHITE_PCT);
        // Map the white percentile to TONE_WHITE_TARGET rather than to 1.0.
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
    let v = match &dev.tone {
        Some(t) => {
            let s = 1.0 / (t.white - t.black);
            [
                (v[0] - t.black) * s,
                (v[1] - t.black) * s,
                (v[2] - t.black) * s,
            ]
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
        assert!(
            (t.black - 0.05).abs() < 2e-3,
            "black point {} missed the floor",
            t.black
        );

        let dev = Develop {
            matrix: None,
            srgb: true,
            tone: Some(t),
            wants_tone: true,
        };
        let at_floor = develop_pixel([t.black, t.black, t.black], &dev);
        assert_eq!(at_floor, [0, 0, 0], "the floor did not develop to black");

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
}
