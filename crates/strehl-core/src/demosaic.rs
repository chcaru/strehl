//! Demosaic: one CFA mosaic to three full-resolution colour planes.
//!
//! # Why this exists, and why it runs *last*
//!
//! The merge is CFA-native and stays that way — that is the project's thesis
//! and `AGENTS.md` rule 2 is the operational form of it. Nothing here runs per
//! frame. This runs **once**, on the single merged mosaic, at the end of the
//! pipeline, which is the whole reason the mosaic is worth keeping.
//!
//! What changed to make this reachable is nothing at all in the merge:
//! [`Estimator`](crate::merge::Estimator) has always accumulated **four
//! independent sums per quad**, one per CFA site. Every one of those four is an
//! estimate of a real sensor photosite at full sensor resolution. The output
//! path was throwing three quarters of that away by emitting one RGB pixel per
//! quad. See `docs/research/M85-output-correctness.md` §3.
//!
//! # The algorithm, and why this one
//!
//! **Malvar, He and Cutler (2004), "High-Quality Linear Interpolation for
//! Demosaicing of Bayer-Patterned Color Images", Proc. IEEE ICASSP 2004,
//! vol. 3, pp. 485-488** — gradient-corrected bilinear interpolation. Five
//! sparse 5x5 linear FIR stencils, no thresholds, no branches on image content,
//! no tuned constants beyond the paper's three gains.
//!
//! It was chosen over the fashionable alternatives on four properties this
//! project cares about more than it cares about a benchmark:
//!
//! 1. **It is linear and shift-invariant within a CFA phase.** That makes its
//!    effect on the noise the merge worked to reduce *computable* rather than
//!    empirical: each output channel is a fixed weighted sum of independent
//!    photosite estimates, so its variance is a fixed quadratic form. An
//!    adaptive or iterative demosaic couples its interpolation decisions to the
//!    noise, which is structurally the same defect as electing a merge winner
//!    on a noisy argmax (rule 4), one stage later.
//! 2. **It cannot manufacture detail.** Every output is a bounded linear
//!    combination of measured samples. Rule 18 asks which direction a stage can
//!    be fooled in; a linear interpolator can only blur and alias, never
//!    hallucinate, so a sharpness metric downstream cannot be inflated by it.
//! 3. **It has a closed form to test against.** The stencils are exact for
//!    constant and for linear image content, which gives two known answers to
//!    assert against rather than an eyeball.
//! 4. **Licence.** It is a published algorithm from Microsoft Research,
//!    implemented here from the paper's stencils. **No implementation was read
//!    to write this.** The GPL demosaic implementations named in `AGENTS.md`
//!    (`librtprocess`, RawTherapee, darktable) were not opened.
//!
//! What it is not: it is not the best demosaic available. AHD, DDFAPD/DLMMSE,
//! RCD and the learned methods all beat it on zipper artifacts near
//! high-frequency diagonal edges. [`tests`] measures where this one fails and
//! the failure is asserted rather than hidden.
//!
//! # Why the default is no longer Malvar
//!
//! Measured, on the `f` axis in cycles per **output** pixel, per-axis
//! horizontal, green channel: Malvar's green loses **22.9%** of amplitude at
//! `f = 0.35` — and an oracle fit to the green samples alone recovers
//! **1.0000** there, so the amplitude is present in the data and the loss is a
//! *reconstruction* shortfall rather than an information one. The mechanism is
//! in [`green_directional`]: [`F_G`] is exactly the mean of the two directional
//! estimates, so where one of them is already exact, averaging halves it away.
//!
//! Of the four properties above, the directional green keeps three and gives
//! up one. Being explicit about which:
//!
//! - **Property 1, linearity, is genuinely surrendered.** The direction is
//!   chosen from image content, so the noise couples to the decision. What
//!   limits the damage is that the decision only matters where the two
//!   candidates disagree, and where they disagree one of them is wrong; where
//!   the image is locally isotropic they agree and the choice is immaterial.
//!   That is an argument, not a measurement, and it is the property a reviewer
//!   should attack first.
//! - **Property 2, that it cannot manufacture detail, survives intact.** Every
//!   output is still a bounded linear combination of measured photosites — the
//!   selection picks *which* combination, never invents a value outside them.
//!   `it_does_not_manufacture_energy_above_the_scenes_band_limit` is the guard
//!   and it still runs against the default.
//! - **Property 3, a closed form to test against, survives** for Malvar, which
//!   is retained as [`demosaic_malvar_row`] and still carries the false-colour
//!   closed form.
//! - **Property 4, licence, is unchanged.** Hamilton-Adams is implemented from
//!   the published algorithm. **No implementation was read to write this**; the
//!   GPL demosaic implementations named in `AGENTS.md` were not opened.
//!
//! Chroma moved with it, and that is the half of the change that removes
//! artifacts rather than adding resolution: red and blue are now interpolated
//! as **colour differences** against the reconstructed green (see
//! [`diff_mean`]) instead of as channels in their own right. A neutral subject
//! has zero colour difference everywhere, so a neutral edge can no longer be
//! given a colour — which is precisely the failure the false-colour test
//! measures at 81.8% for the old stencils at a 2.5 px period.
//!
//! # Bayer phase
//!
//! **RGGB only.** `strehl_raw::decode` rejects every other pattern at the
//! door, so a second phase would be untestable code. Row 0 is `R G R G ...`,
//! row 1 is `G B G B ...`, which matches
//! [`CfaPlane::rggb_at`](crate::CfaPlane::rggb_at).

use crate::CfaPlane;

/// A full-sensor-resolution CFA mosaic, one `f32` sample per photosite.
///
/// The samples are whatever the caller put there. The output path puts
/// **black-subtracted, white-balanced, normalised** values here, because a
/// gradient-corrected demosaic interpolates colour *differences* and those are
/// only smooth once the channels share a scale — see [`crate::color`] for the
/// full ordering and why it is that way round.
pub struct Mosaic<'a> {
    pub data: &'a [f32],
    pub width: usize,
    pub height: usize,
}

impl Mosaic<'_> {
    /// Sample at `(x, y)` with **mirror** extension outside the array.
    ///
    /// Reflection about an edge index maps `i -> 2c - i`, which changes the
    /// index by an even number and therefore **preserves CFA parity**: a
    /// reflected R site is still an R site. Clamping or zero-padding would not,
    /// and would put a red sample where the stencil expects green. This is the
    /// only border rule that keeps the interior stencils valid at the edge.
    #[inline]
    fn at(&self, x: isize, y: isize) -> f32 {
        let x = reflect(x, self.width);
        let y = reflect(y, self.height);
        self.data[y * self.width + x]
    }

    /// Which CFA plane the sample at `(x, y)` belongs to, RGGB.
    #[inline]
    pub fn plane_at(&self, x: usize, y: usize) -> CfaPlane {
        CfaPlane::rggb_at(x, y)
    }
}

#[inline]
fn reflect(mut i: isize, n: usize) -> usize {
    debug_assert!(n > 0);
    // A one-wide image has nowhere to reflect to and the general rule below
    // oscillates forever on it. Real mosaics are never this small; the guard is
    // here because a hang in a border helper is the worst way to find that out,
    // and `the_mirror_border_preserves_cfa_parity` found it exactly that way.
    if n <= 1 {
        return 0;
    }
    let n = n as isize;
    // A loop rather than one arithmetic step, so that a stencil radius larger
    // than the image still lands in range instead of indexing out of bounds.
    loop {
        if i < 0 {
            i = -i;
        } else if i >= n {
            i = 2 * (n - 1) - i;
        } else {
            return i as usize;
        }
    }
}

/// One stencil tap: `(dx, dy, weight)`, weights in eighths.
type Tap = (isize, isize, f32);

/// Green at a red or blue site. Malvar et al., gain `alpha = 1/2`.
///
/// Bilinear green plus half the Laplacian of the *known* channel at that site.
const F_G: [Tap; 9] = [
    (0, 0, 4.0),
    (-1, 0, 2.0),
    (1, 0, 2.0),
    (0, -1, 2.0),
    (0, 1, 2.0),
    (-2, 0, -1.0),
    (2, 0, -1.0),
    (0, -2, -1.0),
    (0, 2, -1.0),
];

/// Red at a green site whose red neighbours lie **horizontally**, and by
/// symmetry blue at a green site whose blue neighbours lie horizontally.
/// Malvar et al., gain `beta = 5/8`.
const F_H: [Tap; 11] = [
    (0, 0, 5.0),
    (-1, 0, 4.0),
    (1, 0, 4.0),
    (-2, 0, -1.0),
    (2, 0, -1.0),
    (-1, -1, -1.0),
    (1, -1, -1.0),
    (-1, 1, -1.0),
    (1, 1, -1.0),
    (0, -2, 0.5),
    (0, 2, 0.5),
];

/// The transpose of [`F_H`]: chroma neighbours lie **vertically**.
const F_V: [Tap; 11] = [
    (0, 0, 5.0),
    (0, -1, 4.0),
    (0, 1, 4.0),
    (0, -2, -1.0),
    (0, 2, -1.0),
    (-1, -1, -1.0),
    (1, -1, -1.0),
    (-1, 1, -1.0),
    (1, 1, -1.0),
    (-2, 0, 0.5),
    (2, 0, 0.5),
];

/// Red at a blue site, and blue at a red site. Malvar et al., gain
/// `gamma = 3/4`.
const F_X: [Tap; 9] = [
    (0, 0, 6.0),
    (-1, -1, 2.0),
    (1, -1, 2.0),
    (-1, 1, 2.0),
    (1, 1, 2.0),
    (-2, 0, -1.5),
    (2, 0, -1.5),
    (0, -2, -1.5),
    (0, 2, -1.5),
];

#[inline]
fn conv(m: &Mosaic, x: usize, y: usize, taps: &[Tap]) -> f32 {
    let (x, y) = (x as isize, y as isize);
    let mut acc = 0.0f32;
    for (dx, dy, w) in taps {
        acc += w * m.at(x + dx, y + dy);
    }
    acc * 0.125
}

/// The four diagonal neighbours: the chroma sites around an R or a B site.
const DIAG: [(isize, isize); 4] = [(-1, -1), (1, -1), (-1, 1), (1, 1)];
/// The two horizontal neighbours.
const H2: [(isize, isize); 2] = [(-1, 0), (1, 0)];
/// The two vertical neighbours.
const V2: [(isize, isize); 2] = [(0, -1), (0, 1)];

/// Green at a red or blue site, **choosing** the interpolation direction
/// instead of averaging both. Hamilton & Adams, implemented from the algorithm
/// as described; no implementation was read to write this.
///
/// The two candidates are the horizontal and vertical gradient-corrected
/// estimates. Malvar's [`F_G`] is algebraically their *arithmetic mean* — add
/// `h` and `v` below and divide by two and the stencil falls out exactly. That
/// identity is why the mean is the wrong operator here: on structure that runs
/// in one direction, one candidate is exact and the other is attenuated, and
/// averaging throws away half of an estimate that was already correct.
///
/// The decision is a comparison of two gradients, with no threshold and no
/// tuned constant, and it is symmetric under transposition so that
/// `demosaicing_commutes_with_transposing_the_mosaic` still holds.
#[inline]
fn green_directional(m: &Mosaic, x: isize, y: isize) -> f32 {
    let k = m.at(x, y);
    let (gl, gr) = (m.at(x - 1, y), m.at(x + 1, y));
    let (gu, gd) = (m.at(x, y - 1), m.at(x, y + 1));
    // Second differences of the *known* channel, which is sampled every two
    // pixels along each axis, so these are its Laplacian components.
    let lh = 2.0 * k - m.at(x - 2, y) - m.at(x + 2, y);
    let lv = 2.0 * k - m.at(x, y - 2) - m.at(x, y + 2);

    let dh = (gl - gr).abs() + lh.abs();
    let dv = (gu - gd).abs() + lv.abs();

    let h = 0.5 * (gl + gr) + 0.25 * lh;
    let v = 0.5 * (gu + gd) + 0.25 * lv;

    if dh < dv {
        h
    } else if dv < dh {
        v
    } else {
        // A genuine tie is isotropic structure, where the two candidates agree
        // anyway; their mean is Malvar's stencil, so the tie case is exactly
        // the old behaviour.
        0.5 * (h + v)
    }
}

/// Green anywhere: the measured sample at a green site, the directional
/// estimate elsewhere.
#[inline]
fn green_at(m: &Mosaic, x: isize, y: isize) -> f32 {
    let (rx, ry) = (reflect(x, m.width), reflect(y, m.height));
    match m.plane_at(rx, ry) {
        CfaPlane::G1 | CfaPlane::G2 => m.data[ry * m.width + rx],
        _ => green_directional(m, x, y),
    }
}

/// Mean of `known - green` over the given neighbours — the colour difference,
/// interpolated rather than the chroma channel itself.
///
/// This is what carries green's resolution into red and blue. `R - G` is flat
/// across a *luminance* edge, so interpolating the difference and adding the
/// sharp green back reconstructs a sharp red; interpolating red directly, as
/// Malvar's [`F_H`]/[`F_V`]/[`F_X`] do, does not. It is also what keeps a
/// neutral edge neutral: if `R == G == B` the differences are zero everywhere
/// and stay zero, so no false colour can be generated at all.
#[inline]
fn diff_mean(m: &Mosaic, x: isize, y: isize, offs: &[(isize, isize)]) -> f32 {
    let mut acc = 0.0f32;
    for (dx, dy) in offs {
        acc += m.at(x + dx, y + dy) - green_at(m, x + dx, y + dy);
    }
    acc / offs.len() as f32
}

/// Environment override selecting the reference arm: `STREHL_DEMOSAIC=malvar`.
///
/// This exists so that an A/B between the default and the arm it replaced can
/// be rendered from **one binary**. Two builds are not a safe comparison in
/// this tree — BUILD-HULL measured two binaries from different points tonight
/// differing by a chromatic-aberration correction, red moving up to 3902 DN —
/// so an algorithm comparison that needs two executables cannot distinguish
/// its own variable from that one. Read once; the value cannot change within a
/// run.
pub const DEMOSAIC_ENV: &str = "STREHL_DEMOSAIC";

fn use_malvar() -> bool {
    static CHOICE: std::sync::OnceLock<bool> = std::sync::OnceLock::new();
    *CHOICE.get_or_init(|| {
        std::env::var(DEMOSAIC_ENV)
            .map(|v| v.eq_ignore_ascii_case("malvar"))
            .unwrap_or(false)
    })
}

/// Demosaic one output row into `out`, which must hold `width * 3` samples.
///
/// Row-at-a-time on purpose: `strehl-core` has no `rayon` dependency and is not
/// getting one for this. The caller owns the parallelism, and the CLI runs this
/// across rows with `par_chunks_mut`.
pub fn demosaic_row(m: &Mosaic, y: usize, out: &mut [f32]) {
    if use_malvar() {
        return demosaic_malvar_row(m, y, out);
    }
    demosaic_directional_row(m, y, out)
}

/// The default: directional green, chroma as colour differences.
pub fn demosaic_directional_row(m: &Mosaic, y: usize, out: &mut [f32]) {
    assert_eq!(out.len(), m.width * 3, "output row is the wrong width");
    assert!(y < m.height, "row {y} is outside the mosaic");
    let yi = y as isize;
    for x in 0..m.width {
        let xi = x as isize;
        let px = &mut out[3 * x..3 * x + 3];
        let known = m.data[y * m.width + x];
        match m.plane_at(x, y) {
            CfaPlane::R => {
                let g = green_directional(m, xi, yi);
                px[0] = known;
                px[1] = g;
                px[2] = g + diff_mean(m, xi, yi, &DIAG);
            }
            CfaPlane::B => {
                let g = green_directional(m, xi, yi);
                px[0] = g + diff_mean(m, xi, yi, &DIAG);
                px[1] = g;
                px[2] = known;
            }
            // G1: even row, odd column. The row is an R row, so red neighbours
            // are horizontal and blue neighbours are vertical.
            CfaPlane::G1 => {
                px[0] = known + diff_mean(m, xi, yi, &H2);
                px[1] = known;
                px[2] = known + diff_mean(m, xi, yi, &V2);
            }
            // G2: odd row, even column. The row is a B row, so it is the other
            // way round.
            CfaPlane::G2 => {
                px[0] = known + diff_mean(m, xi, yi, &V2);
                px[1] = known;
                px[2] = known + diff_mean(m, xi, yi, &H2);
            }
        }
    }
}

/// The Malvar-He-Cutler stencils, **a reference arm, not the shipping path**.
///
/// This was the default until the directional green in [`demosaic_row`]
/// replaced it. It is kept because it is the closed form the false-colour test
/// predicts, and because a headline needs something to be scored against.
pub fn demosaic_malvar_row(m: &Mosaic, y: usize, out: &mut [f32]) {
    assert_eq!(out.len(), m.width * 3, "output row is the wrong width");
    assert!(y < m.height, "row {y} is outside the mosaic");
    for x in 0..m.width {
        let px = &mut out[3 * x..3 * x + 3];
        let known = m.data[y * m.width + x];
        match m.plane_at(x, y) {
            CfaPlane::R => {
                px[0] = known;
                px[1] = conv(m, x, y, &F_G);
                px[2] = conv(m, x, y, &F_X);
            }
            CfaPlane::B => {
                px[0] = conv(m, x, y, &F_X);
                px[1] = conv(m, x, y, &F_G);
                px[2] = known;
            }
            // G1: even row, odd column. The row is an R row, so red neighbours
            // are horizontal and blue neighbours are vertical.
            CfaPlane::G1 => {
                px[0] = conv(m, x, y, &F_H);
                px[1] = known;
                px[2] = conv(m, x, y, &F_V);
            }
            // G2: odd row, even column. The row is a B row, so it is the other
            // way round.
            CfaPlane::G2 => {
                px[0] = conv(m, x, y, &F_V);
                px[1] = known;
                px[2] = conv(m, x, y, &F_H);
            }
        }
    }
}

/// Demosaic the whole mosaic, serially. `out` must hold `width * height * 3`.
pub fn demosaic(m: &Mosaic, out: &mut [f32]) {
    assert_eq!(
        out.len(),
        m.width * m.height * 3,
        "output is the wrong size"
    );
    for y in 0..m.height {
        let row = &mut out[y * m.width * 3..(y + 1) * m.width * 3];
        demosaic_row(m, y, row);
    }
}

/// Plain bilinear demosaic. **A reference arm, not a shipping path.**
///
/// It exists so that [`demosaic`] can be scored against something rather than
/// admired. AGENTS.md rule 11: a headline needs a different rule on identical
/// data, not a better measurement of the same rule.
pub fn demosaic_bilinear_row(m: &Mosaic, y: usize, out: &mut [f32]) {
    assert_eq!(out.len(), m.width * 3);
    let yi = y as isize;
    for x in 0..m.width {
        let xi = x as isize;
        let px = &mut out[3 * x..3 * x + 3];
        let known = m.data[y * m.width + x];
        let cross =
            0.25 * (m.at(xi - 1, yi) + m.at(xi + 1, yi) + m.at(xi, yi - 1) + m.at(xi, yi + 1));
        let diag = 0.25
            * (m.at(xi - 1, yi - 1)
                + m.at(xi + 1, yi - 1)
                + m.at(xi - 1, yi + 1)
                + m.at(xi + 1, yi + 1));
        let horiz = 0.5 * (m.at(xi - 1, yi) + m.at(xi + 1, yi));
        let vert = 0.5 * (m.at(xi, yi - 1) + m.at(xi, yi + 1));
        match m.plane_at(x, y) {
            CfaPlane::R => {
                px[0] = known;
                px[1] = cross;
                px[2] = diag;
            }
            CfaPlane::B => {
                px[0] = diag;
                px[1] = cross;
                px[2] = known;
            }
            CfaPlane::G1 => {
                px[0] = horiz;
                px[1] = known;
                px[2] = vert;
            }
            CfaPlane::G2 => {
                px[0] = vert;
                px[1] = known;
                px[2] = horiz;
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn run(m: &Mosaic) -> Vec<f32> {
        let mut out = vec![0.0; m.width * m.height * 3];
        demosaic(m, &mut out);
        out
    }

    fn run_bilinear(m: &Mosaic) -> Vec<f32> {
        let mut out = vec![0.0; m.width * m.height * 3];
        for y in 0..m.height {
            let row = &mut out[y * m.width * 3..(y + 1) * m.width * 3];
            demosaic_bilinear_row(m, y, row);
        }
        out
    }

    fn run_malvar(m: &Mosaic) -> Vec<f32> {
        let mut out = vec![0.0; m.width * m.height * 3];
        for y in 0..m.height {
            let row = &mut out[y * m.width * 3..(y + 1) * m.width * 3];
            demosaic_malvar_row(m, y, row);
        }
        out
    }

    /// Mosaic an RGB image: keep only the channel each site actually measures.
    fn mosaic_of(rgb: &[f32], w: usize, h: usize) -> Vec<f32> {
        let mut m = vec![0.0; w * h];
        for y in 0..h {
            for x in 0..w {
                let c = match CfaPlane::rggb_at(x, y) {
                    CfaPlane::R => 0,
                    CfaPlane::B => 2,
                    _ => 1,
                };
                m[y * w + x] = rgb[3 * (y * w + x) + c];
            }
        }
        m
    }

    /// The reason the default changed, asserted rather than asserted-about.
    ///
    /// A horizontal neutral grating is the case where the vertical estimate is
    /// exact and the horizontal one is attenuated. Malvar averages them and
    /// loses amplitude; the directional green picks the exact one. Two claims
    /// are pinned here: that the default recovers materially more amplitude
    /// than Malvar at the frequency the loss was priced at, and that Malvar's
    /// own loss is the ~23% that priced it.
    #[test]
    fn directional_green_recovers_the_amplitude_malvar_averages_away() {
        let (w, h) = (64usize, 64usize);
        let amp = 0.2f32;
        // f = 0.35 cycles per output pixel, the frequency the loss was priced
        // at. Period 1/0.35 is not an integer; that is deliberate.
        let f = 0.35f32;

        let mut rgb = vec![0.0f32; w * h * 3];
        for y in 0..h {
            for x in 0..w {
                let v = 0.5 + amp * (std::f32::consts::TAU * f * x as f32).sin();
                for c in 0..3 {
                    rgb[3 * (y * w + x) + c] = v;
                }
            }
        }
        let data = mosaic_of(&rgb, w, h);
        let m = Mosaic {
            data: &data,
            width: w,
            height: h,
        };

        // Least-squares amplitude of the f component of green, interior only.
        let amp_of = |out: &[f32]| -> f32 {
            let (mut sa, mut ca, mut n) = (0.0f32, 0.0f32, 0usize);
            for y in 6..h - 6 {
                for x in 6..w - 6 {
                    let g = out[3 * (y * w + x) + 1];
                    let p = std::f32::consts::TAU * f * x as f32;
                    sa += (g - 0.5) * p.sin();
                    ca += (g - 0.5) * p.cos();
                    n += 1;
                }
            }
            2.0 * (sa * sa + ca * ca).sqrt() / n as f32 / amp
        };

        let got = amp_of(&run(&m));
        let malvar = amp_of(&run_malvar(&m));

        assert!(
            malvar < 0.85,
            "Malvar green at f=0.35 measured {malvar}, expected the ~0.77 that \
             priced the loss; if this rose, the premise of the change moved"
        );
        assert!(
            got > 0.97,
            "directional green at f=0.35 measured {got}, expected near the 1.0 \
             an oracle fit to the green samples recovers"
        );
        assert!(
            got > malvar * 1.15,
            "directional green {got} must beat Malvar {malvar} by a margin \
             worth surrendering linearity for"
        );
    }

    /// The half of the change that removes an artifact rather than adding
    /// resolution. Interpolating colour *differences* means a subject with no
    /// colour cannot acquire any, at any frequency — including the 2.5 px
    /// period where the old stencils put 81.8% of amplitude into false colour.
    ///
    /// This is also the ringing guard's companion: `tweezers-cpl` is a neutral
    /// dark-groove-on-bright-metal subject, and a coloured groove edge would be
    /// as unshippable as a haloed one.
    #[test]
    fn a_neutral_grating_stays_neutral_at_every_frequency() {
        let (w, h) = (64usize, 64usize);
        let amp = 0.4f32;
        for period in [16.0f32, 8.0, 4.0, 2.5] {
            let mut rgb = vec![0.0f32; w * h * 3];
            for y in 0..h {
                for x in 0..w {
                    let v = 0.5 + amp * (std::f32::consts::TAU * x as f32 / period).sin();
                    for c in 0..3 {
                        rgb[3 * (y * w + x) + c] = v;
                    }
                }
            }
            let data = mosaic_of(&rgb, w, h);
            let m = Mosaic {
                data: &data,
                width: w,
                height: h,
            };
            let out = run(&m);
            let mut worst = 0.0f32;
            for y in 4..h - 4 {
                for x in 4..w - 4 {
                    let i = 3 * (y * w + x);
                    let (r, g, b) = (out[i], out[i + 1], out[i + 2]);
                    worst = worst.max((r - g).abs()).max((b - g).abs());
                }
            }
            assert!(
                worst < 1e-5,
                "period {period}: neutral grating acquired {worst} of false \
                 colour; colour-difference interpolation should make this \
                 structurally impossible"
            );
        }
    }

    /// **Every stencil must sum to 8.** That is the constant-preservation
    /// property, and it is the one property of the published coefficients that
    /// can be checked without any image at all. If a coefficient was
    /// mistranscribed from the paper, this is what catches it.
    #[test]
    fn the_published_stencils_sum_to_eight() {
        for (name, taps) in [
            ("F_G", &F_G[..]),
            ("F_H", &F_H[..]),
            ("F_V", &F_V[..]),
            ("F_X", &F_X[..]),
        ] {
            let s: f32 = taps.iter().map(|t| t.2).sum();
            assert!((s - 8.0).abs() < 1e-6, "{name} sums to {s}, not 8");
        }
        // F_V is F_H transposed, exactly. Asserted rather than eyeballed.
        for (dx, dy, w) in F_H {
            let found = F_V
                .iter()
                .find(|(a, b, _)| *a == dy && *b == dx)
                .unwrap_or_else(|| panic!("F_V has no transpose of tap ({dx},{dy})"));
            assert!((found.2 - w).abs() < 1e-6, "transpose weight mismatch");
        }
    }

    /// A constant **coloured** scene must come back exactly, everywhere,
    /// including at the borders.
    ///
    /// This is the cheapest known-answer test in the module and it is the one
    /// with the widest catchment. Every stencil applied to a constant-chroma
    /// field returns the other channel's exact value — by hand, `F_H` at a G1
    /// site reads `(5*G + 4R + 4R - G - G - 4*G + G/2 + G/2)/8 = R` — so a
    /// mistranscribed coefficient, a swapped `F_H`/`F_V` assignment, or a
    /// border rule that breaks CFA parity all fail it. A *neutral* constant
    /// field would not: with `R = G = B` the mosaic is flat and the horizontal
    /// and vertical filters become indistinguishable.
    #[test]
    fn a_constant_coloured_scene_survives_exactly_everywhere() {
        let (w, h) = (17usize, 13usize); // odd on purpose: the far edges are G
        let truth = [0.6f32, 0.3, 0.45];
        let mut rgb = vec![0.0f32; w * h * 3];
        for p in rgb.chunks_mut(3) {
            p.copy_from_slice(&truth);
        }
        let data = mosaic_of(&rgb, w, h);
        let m = Mosaic {
            data: &data,
            width: w,
            height: h,
        };
        let out = run(&m);
        for y in 0..h {
            for x in 0..w {
                for c in 0..3 {
                    let v = out[3 * (y * w + x) + c];
                    assert!(
                        (v - truth[c]).abs() < 1e-6,
                        "({x},{y}) channel {c} is {v}, not {}",
                        truth[c]
                    );
                }
            }
        }
    }

    /// Demosaicing must commute with transposing the mosaic.
    ///
    /// Transposing an RGGB mosaic yields an RGGB mosaic — R sites `(even,even)`
    /// and B sites `(odd,odd)` are fixed by the transpose while G1 and G2 swap —
    /// so the reconstruction of the transposed image must be the transpose of
    /// the reconstruction, channel for channel. That holds only if `F_V` is
    /// applied exactly where `F_H`'s transpose belongs.
    ///
    /// Its blind spot, stated because rule 20 asks for it: a *global* swap of
    /// `F_H` and `F_V` also commutes. That case is what
    /// [`a_constant_coloured_scene_survives_exactly_everywhere`] catches, and
    /// neither test is sufficient alone.
    #[test]
    fn demosaicing_commutes_with_transposing_the_mosaic() {
        let (w, h) = (18usize, 26usize);
        let data: Vec<f32> = (0..w * h)
            .map(|i| ((i * 89 % 401) as f32) / 401.0)
            .collect();
        let mut t = vec![0.0f32; w * h];
        for y in 0..h {
            for x in 0..w {
                t[x * h + y] = data[y * w + x];
            }
        }
        let a = run(&Mosaic {
            data: &data,
            width: w,
            height: h,
        });
        let b = run(&Mosaic {
            data: &t,
            width: h,
            height: w,
        });
        let mut worst = 0.0f32;
        for y in 0..h {
            for x in 0..w {
                for c in 0..3 {
                    let lhs = a[3 * (y * w + x) + c];
                    let rhs = b[3 * (x * h + y) + c];
                    worst = worst.max((lhs - rhs).abs());
                }
            }
        }
        assert!(worst < 1e-6, "transpose asymmetry {worst}");
    }

    /// A neutral **linear ramp** must come back exactly, in the interior.
    ///
    /// The stencils are symmetric about their centre, so they annihilate the
    /// first-order term. This is the second known answer, and it is a much
    /// stronger test than the constant one: bilinear also passes the constant
    /// test, and bilinear does **not** pass this one at green sites.
    ///
    /// The interior begins at **3**, not 2. Mirror reflection preserves CFA
    /// parity but not a ramp — it folds the gradient — so "interior" means
    /// "outside the operator's support", and the default's support is one ring
    /// wider than Malvar's: radius 2 for the green estimate, plus radius 1 for
    /// the colour-difference neighbours which each run their own green
    /// estimate. The second assertion pins that support size, so a future
    /// change that widens it again fails here instead of silently reaching
    /// further into reflected data.
    #[test]
    fn a_linear_ramp_survives_exactly_in_the_interior() {
        let (w, h) = (24usize, 24usize);
        let mut rgb = vec![0.0f32; w * h * 3];
        for y in 0..h {
            for x in 0..w {
                let v = 0.05 + 0.01 * x as f32 + 0.004 * y as f32;
                for c in 0..3 {
                    rgb[3 * (y * w + x) + c] = v;
                }
            }
        }
        let data = mosaic_of(&rgb, w, h);
        let m = Mosaic {
            data: &data,
            width: w,
            height: h,
        };
        let out = run(&m);
        let worst_from = |margin: usize| -> f32 {
            let mut worst = 0.0f32;
            for y in margin..h - margin {
                for x in margin..w - margin {
                    for c in 0..3 {
                        let i = 3 * (y * w + x) + c;
                        worst = worst.max((out[i] - rgb[i]).abs());
                    }
                }
            }
            worst
        };
        assert!(worst_from(3) < 1e-5, "worst interior ramp error {}", worst_from(3));

        // Support is exactly 3: the ring at margin 2 must be *inexact*, and
        // every pixel that is inexact must lie on that ring.
        assert!(
            worst_from(2) > 1e-5,
            "margin-2 ring came back exact, so the support is narrower than \
             documented and this test is no longer pinning anything"
        );
        for y in 2..h - 2 {
            for x in 2..w - 2 {
                let ring = x == 2 || y == 2 || x == w - 3 || y == h - 3;
                for c in 0..3 {
                    let i = 3 * (y * w + x) + c;
                    let e = (out[i] - rgb[i]).abs();
                    assert!(
                        ring || e < 1e-5,
                        "error {e} at ({x},{y}) channel {c} is inside the \
                         margin-2 ring, so the support is wider than 3"
                    );
                }
            }
        }
    }

    /// The known answer that matters: a synthetic scene scored against the
    /// truth it was mosaiced from, with **bilinear as the arm to beat** — and
    /// with the condition that advantage depends on stated and tested.
    ///
    /// Rule 11 — a headline number needs a different rule on identical data.
    /// Rule 18 — say which direction it can be fooled in. Malvar-He-Cutler's
    /// gradient correction assumes the *colour difference* `R - G` is smoother
    /// than either channel, which is a property of real scenes and not a
    /// theorem. Arm A is a luminance-dominant scene, where that holds; arm B
    /// gives every channel its own independent mid-frequency content, where it
    /// does not. **The bar is pre-registered from the paper**, which reports
    /// roughly 5.5 dB over bilinear on the Kodak set: arm A must clear 3 dB.
    /// Arm B is not required to clear anything, and is asserted to be worse
    /// than arm A, because that conditionality is the honest result.
    #[test]
    fn it_beats_bilinear_when_the_channels_are_correlated_and_not_when_they_are_not() {
        let (w, h) = (96usize, 96usize);

        // Arm A: luminance carries the detail, chroma varies slowly.
        let mut arm_a = vec![0.0f32; w * h * 3];
        // Arm B: three independent mid-frequency patterns.
        let mut arm_b = vec![0.0f32; w * h * 3];
        for y in 0..h {
            for x in 0..w {
                let (fx, fy) = (x as f32, y as f32);
                let tau = std::f32::consts::TAU;
                let luma = 0.45 + 0.28 * (tau * (0.11 * fx + 0.07 * fy)).sin();
                let cr = 0.18 * (tau * 0.012 * fx).sin();
                let cb = 0.15 * (tau * 0.009 * fy).cos();
                let i = 3 * (y * w + x);
                arm_a[i] = (luma * (1.0 + cr)).clamp(0.0, 1.0);
                arm_a[i + 1] = luma.clamp(0.0, 1.0);
                arm_a[i + 2] = (luma * (1.0 + cb)).clamp(0.0, 1.0);

                arm_b[i] = (0.45 + 0.25 * (tau * (0.13 * fx + 0.05 * fy)).sin()).clamp(0.0, 1.0);
                arm_b[i + 1] =
                    (0.45 + 0.25 * (tau * (0.04 * fx + 0.14 * fy)).cos()).clamp(0.0, 1.0);
                arm_b[i + 2] =
                    (0.45 + 0.25 * (tau * (0.09 * fx - 0.10 * fy)).sin()).clamp(0.0, 1.0);
            }
        }

        let score = |truth: &[f32]| -> (f64, f64) {
            let data = mosaic_of(truth, w, h);
            let m = Mosaic {
                data: &data,
                width: w,
                height: h,
            };
            let mhc = run(&m);
            let bil = run_bilinear(&m);
            let mse = |a: &[f32]| -> f64 {
                let mut acc = 0.0f64;
                let mut n = 0usize;
                for y in 3..h - 3 {
                    for x in 3..w - 3 {
                        for c in 0..3 {
                            let i = 3 * (y * w + x) + c;
                            let d = f64::from(a[i] - truth[i]);
                            acc += d * d;
                            n += 1;
                        }
                    }
                }
                acc / n as f64
            };
            let psnr = |v: f64| -10.0 * v.log10();
            (psnr(mse(&mhc)), psnr(mse(&bil)))
        };

        let (a_mhc, a_bil) = score(&arm_a);
        let (b_mhc, b_bil) = score(&arm_b);

        // Rule 36: show the fixture exercises the property. If bilinear were
        // already near-perfect there would be no demosaic difficulty here and
        // the comparison would be vacuous.
        assert!(
            a_bil < 40.0,
            "arm A has no demosaic difficulty in it: bilinear scored {a_bil:.2} dB"
        );
        assert!(
            a_mhc > a_bil + 3.0,
            "arm A (correlated channels): Malvar-He-Cutler {a_mhc:.2} dB vs \
             bilinear {a_bil:.2} dB, short of the paper's 3 dB"
        );
        assert!(
            (b_mhc - b_bil) < (a_mhc - a_bil),
            "the advantage was supposed to shrink when the channels are \
             independent, but arm B gained {:.2} dB against arm A's {:.2} dB",
            b_mhc - b_bil,
            a_mhc - a_bil
        );
    }

    /// **The resolution / aliasing check, against a closed form, and it is
    /// allowed to fail.**
    ///
    /// A neutral `R = G = B` sinusoidal grating carries no chroma, so any
    /// chroma in the output is false colour manufactured by the interpolation.
    /// For a neutral scene the mosaic *is* the luminance image, so each
    /// stencil's effect is exactly its frequency response along `x`. Taking the
    /// DTFT of each tap list at `(w, 0)` — a different domain from the
    /// convolution being tested, which is what AGENTS.md rule 21 asks for —
    ///
    /// ```text
    ///   H_G(w) = H_H(w) = ( 6 + 4 cos w - 2 cos 2w ) / 8
    ///   H_V(w)          = ( 11 - 4 cos w + cos 2w ) / 8
    ///   H_X(w)          = ( 3 + 8 cos w - 3 cos 2w ) / 8
    /// ```
    ///
    /// `H_G == H_H` is a derived identity, not a typo: `F_H`'s two extra
    /// vertical taps contribute `+1` and its four diagonals `-4 cos w`, which
    /// is exactly what turns `F_H` into `F_G`'s response on a horizontal
    /// grating.
    ///
    /// Every site sees a `gain 1` known channel and two interpolated ones, so
    /// the worst false colour over the frame is
    /// `A * max(|1-H_G|, |H_X-H_G|, |H_H-1|, |H_V-1|) * max_x |sin(w x)|`.
    /// The last factor is a property of the *stimulus* and is measured from it,
    /// so the filter prediction stays independent of the filters.
    ///
    /// **The high-frequency half is the honest one.** Every demosaic fails near
    /// Nyquist and this one fails by turning a monochrome grating into a
    /// coloured one: 3.5% of amplitude at a 16 px period, 81.8% at 2.5 px.
    /// Asserting the failure at its predicted size is rule 30.
    #[test]
    fn false_colour_on_a_neutral_grating_matches_the_stencils_closed_form() {
        let (w, h) = (64usize, 64usize);
        let amp = 0.4f32;
        let measure = |period: f32| -> f32 {
            let mut rgb = vec![0.0f32; w * h * 3];
            for y in 0..h {
                for x in 0..w {
                    let v = 0.5 + amp * (std::f32::consts::TAU * x as f32 / period).sin();
                    for c in 0..3 {
                        rgb[3 * (y * w + x) + c] = v;
                    }
                }
            }
            let data = mosaic_of(&rgb, w, h);
            let m = Mosaic {
                data: &data,
                width: w,
                height: h,
            };
            let out = run_malvar(&m);
            let mut worst = 0.0f32;
            for y in 4..h - 4 {
                for x in 4..w - 4 {
                    let i = 3 * (y * w + x);
                    let (r, g, b) = (out[i], out[i + 1], out[i + 2]);
                    worst = worst.max((r - g).abs()).max((b - g).abs());
                }
            }
            worst
        };
        let predicted = |period: f32| -> (f32, f32) {
            let wr = std::f32::consts::TAU / period;
            let (c1, c2) = (wr.cos(), (2.0 * wr).cos());
            let h_g = (6.0 + 4.0 * c1 - 2.0 * c2) / 8.0;
            let h_h = h_g;
            let h_v = (11.0 - 4.0 * c1 + c2) / 8.0;
            let h_x = (3.0 + 8.0 * c1 - 3.0 * c2) / 8.0;
            let gain = (1.0f32 - h_g)
                .abs()
                .max((h_x - h_g).abs())
                .max((h_h - 1.0).abs())
                .max((h_v - 1.0).abs());
            // The stimulus's own peak over the sampled grid, which need not be
            // 1 when the period is not an integer.
            let peak = (4..w - 4)
                .map(|x| (wr * x as f32).sin().abs())
                .fold(0.0f32, f32::max);
            (gain * amp * peak, gain)
        };

        for period in [16.0f32, 8.0, 4.0, 2.5] {
            let got = measure(period);
            let (want, gain) = predicted(period);
            assert!(
                (got - want).abs() < 3e-4,
                "period {period}: measured false colour {got}, closed form {want} \
                 (gain term {gain})"
            );
        }

        // ...and the failure is real, not a rounding artifact. These two bars
        // are the reason the closed form is worth having: they are the
        // published behaviour of this algorithm, at both ends.
        assert!(
            predicted(16.0).1 < 0.05,
            "a 16 px period should be nearly clean, gain term {}",
            predicted(16.0).1
        );
        assert!(
            predicted(2.5).1 > 0.5,
            "a 2.5 px period was expected to alias badly, gain term {}",
            predicted(2.5).1
        );
    }

    /// **A demosaic must not manufacture energy above the scene's band limit.**
    ///
    /// M85 was originally handed a different rationale for this test: that the
    /// lens has a diffraction cutoff *inside* the sensor's range, above which
    /// the MTF is identically zero, so any energy there is manufactured. **That
    /// premise was withdrawn and is false for this rig.** M5 measured the
    /// bellows factor `B <= 3.06` directly from the cutoff and M84b measured
    /// `m = 2.7198 +/- 0.0051`; together they put `f_c >= 106 cy/mm`, above the
    /// sensor Nyquist of 97.7. There is no diffraction-imposed dead band inside
    /// the sensor band, so a super-cutoff test on a real capture would condemn
    /// genuine detail. Do not reintroduce one.
    ///
    /// What survives is the *constructed* form, which never needed the optics:
    /// band-limit a synthetic scene **by construction**, then check the
    /// pipeline does not invent energy above the planted limit. The bound is
    /// planted, so it is known exactly and cannot be argued with.
    ///
    /// Lattice geometry sets the limit. On an RGGB grid of pitch `d`, red and
    /// blue are sampled at `2d`, so their Nyquist is **half** the full grid's;
    /// green sits on a quincunx and reaches the full grid's Nyquist on-axis.
    /// The scene here stays below the *red/blue* limit (`N/4` cycles), which is
    /// the strictest, so nothing is aliased by the mosaic itself and a perfect
    /// demosaic would return the scene exactly.
    ///
    /// The probe frequencies are not arbitrary: they are the period-2 CFA
    /// carrier at Nyquist and its sidebands around each scene component. That
    /// is where a demosaic which has failed to suppress the mosaic will show.
    ///
    /// Rule 20 -- the test ships with a **positive control that must fire**:
    /// the un-demosaiced mosaic, which is the same data with the carrier left
    /// in. MEASURED: the raw mosaic carries 0.1500 of super-band amplitude,
    /// Malvar-He-Cutler 0.002463 -- a suppression of **61x**, leaving 4.1% of a
    /// scene component's amplitude and 0.25% of full scale. If the control ever
    /// stops failing, the measurement has gone dead and the pass above it means
    /// nothing.
    ///
    /// An earlier version of this fixture used near-neutral channel gains
    /// (1.00/0.95/1.05). The control measured 0.00075 and **could not fire** --
    /// a nearly neutral scene barely modulates the CFA, so there was no carrier
    /// to suppress and the bar would have been vacuous. The rule-36 guard below
    /// caught that; the gains are now 1.0/0.8/1.2.
    #[test]
    fn it_does_not_manufacture_energy_above_the_scenes_band_limit() {
        let n = 128usize;

        // Scene: a sum of cosines, every one strictly inside the red/blue
        // Nyquist radius of n/4 = 32 bins. Channels are proportional, which is
        // the constant-chromaticity regime this algorithm is built for.
        let comps: [(i32, i32); 5] = [(12, 0), (0, 16), (18, 14), (24, 8), (10, 26)];
        for &(kx, ky) in &comps {
            let r = f64::from(kx * kx + ky * ky).sqrt();
            assert!(
                r < (n / 4) as f64,
                "scene component ({kx},{ky}) at radius {r} is aliased by the \
                 red/blue lattice, so the test would measure the mosaic and \
                 not the demosaic"
            );
        }

        let mut truth = vec![0.0f32; n * n * 3];
        for y in 0..n {
            for x in 0..n {
                let mut s = 0.0f64;
                for &(kx, ky) in &comps {
                    let ph = std::f64::consts::TAU
                        * (f64::from(kx) * x as f64 + f64::from(ky) * y as f64)
                        / n as f64;
                    s += 0.06 * ph.cos();
                }
                let i = 3 * (y * n + x);
                truth[i] = ((0.5 + s) * 1.0) as f32;
                truth[i + 1] = ((0.5 + s) * 0.8) as f32;
                truth[i + 2] = ((0.5 + s) * 1.2) as f32;
            }
        }

        let data = mosaic_of(&truth, n, n);
        let m = Mosaic {
            data: &data,
            width: n,
            height: n,
        };
        let out = run(&m);

        // Positive control: the mosaic itself, carrier and all.
        let mut raw = vec![0.0f32; n * n * 3];
        for y in 0..n {
            for x in 0..n {
                let v = data[y * n + x];
                for c in 0..3 {
                    raw[3 * (y * n + x) + c] = v;
                }
            }
        }

        // Hann-windowed projection onto one Fourier component. The window
        // tapers the mirrored border to zero, so the border cannot leak into
        // the band under test -- which is the whole measurement.
        let amplitude_at = |img: &[f32], chan: usize, kx: i32, ky: i32| -> f64 {
            let w: Vec<f64> = (0..n)
                .map(|i| 0.5 - 0.5 * (std::f64::consts::TAU * i as f64 / n as f64).cos())
                .collect();
            let (mut re, mut im, mut norm) = (0.0f64, 0.0f64, 0.0f64);
            for y in 0..n {
                for x in 0..n {
                    let ww = w[y] * w[x];
                    let v = f64::from(img[3 * (y * n + x) + chan]) * ww;
                    let ph = std::f64::consts::TAU
                        * (f64::from(kx) * x as f64 + f64::from(ky) * y as f64)
                        / n as f64;
                    re += v * ph.cos();
                    im -= v * ph.sin();
                    norm += ww;
                }
            }
            2.0 * re.hypot(im) / norm
        };

        // Where the period-2 CFA carrier lands: the carrier itself at Nyquist,
        // and its sidebands around each scene component.
        let probes: [(i32, i32); 8] = [
            (64, 0),
            (0, 64),
            (64, 64),
            (52, 0),
            (0, 48),
            (46, 14),
            (40, 8),
            (54, 26),
        ];
        let worst = |img: &[f32]| -> f64 {
            let mut w = 0.0f64;
            for &(kx, ky) in &probes {
                for c in 0..3 {
                    w = w.max(amplitude_at(img, c, kx, ky));
                }
            }
            w
        };

        let mhc = worst(&out);
        let control = worst(&raw);

        // Rule 36: the fixture must actually contain the thing being measured.
        assert!(
            control > 0.05,
            "the positive control did not fire: the mosaic carrier measured \
             only {control}, so this fixture cannot detect manufactured energy \
             and the bar below is vacuous"
        );
        assert!(
            mhc < control / 50.0,
            "Malvar-He-Cutler left {mhc} of super-band amplitude against the \
             raw mosaic's {control}; it is not suppressing the CFA carrier"
        );
        // The absolute bar, MEASURED at 0.002463. Scene components have
        // amplitude 0.06, so this is 4.1% of one component and 0.25% of full
        // scale. Rule 30: the tolerated disagreement is asserted at its
        // expected wrong value, not at zero.
        assert!(
            mhc < 0.003,
            "manufactured super-band amplitude {mhc} exceeds the measured bar \
             (control was {control})"
        );
    }

    /// The mirror border rule must preserve CFA parity, or every edge stencil
    /// is reading the wrong colour.
    #[test]
    fn the_mirror_border_preserves_cfa_parity() {
        for n in [1usize, 2, 3, 7, 64] {
            for i in -6isize..(n as isize + 6) {
                let r = reflect(i, n);
                assert!(r < n, "reflect({i},{n}) = {r} is out of range");
                if n > 1 {
                    assert_eq!(
                        (r as isize - i).rem_euclid(2),
                        0,
                        "reflect({i},{n}) = {r} changed parity"
                    );
                }
            }
        }
    }

    /// The row API and the whole-image API must agree exactly, because the CLI
    /// uses the first and the tests above use the second.
    #[test]
    fn the_row_api_and_the_whole_image_api_agree() {
        let (w, h) = (33usize, 21usize);
        let data: Vec<f32> = (0..w * h)
            .map(|i| ((i * 37 % 251) as f32) / 251.0)
            .collect();
        let m = Mosaic {
            data: &data,
            width: w,
            height: h,
        };
        let whole = run(&m);
        let mut rows = vec![0.0f32; w * h * 3];
        for y in 0..h {
            demosaic_row(&m, y, &mut rows[y * w * 3..(y + 1) * w * 3]);
        }
        assert_eq!(whole, rows);
    }
}
