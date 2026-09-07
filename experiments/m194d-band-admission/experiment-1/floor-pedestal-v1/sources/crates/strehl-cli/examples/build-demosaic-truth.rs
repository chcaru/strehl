//! BUILD-DEMOSAIC -- is the gather flip's chroma excess **restored** or **created**?
//!
//! # The question
//!
//! V-GATHER upheld the full-resolution gather flip (`740e7056`) and reported an
//! unaccounted cost: **chroma (R-B) high-pass up 25.2% to 48.6%**, traced to a
//! *double demosaic* -- [`align_cmd::warp_frame_in_place_fullres`] demosaics the
//! mosaic, gathers each CFA site from its own channel plane, re-mosaics, and the
//! merge then demosaics that a second time.
//!
//! Two readings fit that number and they demand opposite actions:
//!
//! * **restored** -- the gather recovers chroma detail the half-resolution phase
//!   planes were smearing away, the excess is honest signal plus honest noise,
//!   and there is nothing to fix;
//! * **created** -- demosaicing twice interpolates already-interpolated values
//!   and manufactures chroma that was never in the CFA data.
//!
//! # Why this instrument and not a fourth detector
//!
//! `ORCH-veiling` 111 killed three real-image detectors on this question. The
//! arithmetic that killed the last one is the reason: with per-channel noise of
//! sd 400 DN the opponent axis `c = R + B - 2G` carries `sqrt(6) * 400 = 980 DN`,
//! so **demosaic chroma error and ordinary photon noise are the same size** at
//! these levels. No statistic computed on a real capture can separate them,
//! because on a real capture neither the true chroma nor the noise is known.
//!
//! So this instrument does not measure the difference between two arms, neither
//! of which is truth. It builds a scene whose true colour is known **analytically
//! at every real coordinate**, pushes it through the shipping code, and measures
//! each arm's error *against that truth*. Restored and created are then not a
//! matter of interpretation: restoration lowers the error and creation raises it.
//!
//! The scene is **noiseless** by default for exactly the reason above -- arm
//! `noise` re-runs it with sd 400 DN and reproduces the 980 DN figure
//! independently, which is a check on 111.4 rather than on the pipeline.
//!
//! # Commissioning
//!
//! `AGENTS.md`, and sections 110.6 and 111.3, require a planted defect, a planted
//! improvement, **and** a healthy control that superficially resembles the
//! defect. All three are arms here, plus one this instrument needs and the rule
//! does not name: a proof that the harness reproduces the shipping path
//! **bit-for-bit**, because the oracle and planted-defect arms are re-gathers,
//! and a re-gather that has drifted measures itself.
//!
//! ```text
//! cargo run --release -p strehl-cli --example build-demosaic-truth
//! ```

#[allow(dead_code)]
#[path = "../src/align_cmd.rs"]
mod align_cmd;

use std::f64::consts::TAU;
use std::path::PathBuf;

use anyhow::{Result, bail};
use rayon::prelude::*;
use strehl_core::align::{PlaneRef, Resampler, Similarity, SimilarityParams};
use strehl_core::demosaic::{Mosaic, demosaic_row};
use strehl_core::noise::Levels;
use strehl_core::plane::PlaneGeometry;
use strehl_raw::{Frame, Region};

use align_cmd::{WarpScratch, warp_frame_in_place_fullres, warp_frame_in_place_plane};

// ---------------------------------------------------------------------------
// geometry and capture constants
// ---------------------------------------------------------------------------

/// Quad-plane size. The full-resolution frame is twice this in each axis.
const GW: usize = 384;
const GH: usize = 384;

/// Sensor pedestal, as measured on the A7C II (M1).
const BLACK: f32 = 512.0;

/// As-shot white balance. Non-unity on purpose: the full-resolution gather
/// applies the balance before demosaicing and divides it out again on the way
/// back, and a unity balance would hide any error in that round trip. Arm
/// `unity-wb` runs the same scene with `[1, 1, 1]` to price that choice.
const WB: [f32; 4] = [2.0, 1.0, 1.5, f32::NAN];

/// Plane pixels dropped at every border before any statistic is taken.
///
/// Catmull-Rom's support is 2 plane px, the warps below displace by under 3, and
/// the 5x5 high-pass reaches 2 more. 24 is comfortably outside all of them, and
/// the coverage assertion in [`measure`] fails rather than trusting this number.
const MARGIN: usize = 24;

/// Index into `[R, G, B]` of the RGGB site at `(x, y)`.
///
/// Written out rather than imported because `align_cmd`'s copy is private. It is
/// pinned against `strehl_core::optics::cfa_site_channel` in [`commission_cfa`],
/// so the two cannot drift apart without the run failing.
#[inline]
fn rggb(x: usize, y: usize) -> usize {
    match (y % 2, x % 2) {
        (0, 0) => 0,
        (1, 1) => 2,
        _ => 1,
    }
}

// ---------------------------------------------------------------------------
// the scene: analytic, band-limited, evaluable at any real coordinate
// ---------------------------------------------------------------------------

/// One cosine component: amplitude in DN, frequency in cycles per
/// **full-resolution** pixel, phase in radians.
#[derive(Clone, Copy)]
struct Wave {
    a: f64,
    fx: f64,
    fy: f64,
    ph: f64,
}

impl Wave {
    #[inline]
    fn at(self, x: f64, y: f64) -> f64 {
        self.a * (TAU * (self.fx * x + self.fy * y) + self.ph).cos()
    }
}

/// A scene in **white-balanced DN** -- the units the demosaic works in and the
/// units a render's colour is decided in.
///
/// `R = l + c`, `G = l + g`, `B = l - c`, so `R - B = 2c` is the chroma axis
/// V-GATHER measured and `g` is the orthogonal green-magenta axis. An achromatic
/// scene is `c = g = 0` and its true `R - B` is **exactly zero at every real
/// coordinate** -- not small, zero -- which is what makes it decisive: any chroma
/// in the output of an achromatic scene is manufactured, with nothing to restore.
struct Scene {
    name: &'static str,
    base: f64,
    luma: Vec<Wave>,
    chroma: Vec<Wave>,
    green: Vec<Wave>,
}

impl Scene {
    /// True `[R, G, B]` in white-balanced DN at an arbitrary real coordinate.
    #[inline]
    fn rgb(&self, x: f64, y: f64) -> [f64; 3] {
        let l = self.base + self.luma.iter().map(|w| w.at(x, y)).sum::<f64>();
        let c = self.chroma.iter().map(|w| w.at(x, y)).sum::<f64>();
        let g = self.green.iter().map(|w| w.at(x, y)).sum::<f64>();
        [l + c, l + g, l - c]
    }
}

/// Luma structure spanning the band the demosaic actually has to reconstruct.
///
/// Frequencies run to 0.45 cyc/px, above the 0.25 cyc/px Nyquist of the red and
/// blue lattices and below the 0.5 cyc/px sensor Nyquist. That range is not
/// decoration: it is **where demosaic false colour is born**, because it is
/// exactly the luma a Bayer sensor samples densely enough to see but samples R
/// and B too sparsely to confirm. `demosaic.rs` already records 81.8% of
/// amplitude going into false colour at a 2.5 px period on a neutral subject.
fn luma_waves() -> Vec<Wave> {
    vec![
        Wave { a: 900.0, fx: 0.045, fy: 0.020, ph: 0.31 },
        Wave { a: 700.0, fx: 0.110, fy: -0.070, ph: 1.17 },
        Wave { a: 520.0, fx: 0.190, fy: 0.150, ph: 2.44 },
        Wave { a: 430.0, fx: -0.260, fy: 0.090, ph: 0.83 },
        Wave { a: 360.0, fx: 0.330, fy: 0.240, ph: 3.02 },
        Wave { a: 300.0, fx: 0.400, fy: -0.120, ph: 1.71 },
        Wave { a: 260.0, fx: 0.070, fy: 0.450, ph: 2.05 },
        Wave { a: 220.0, fx: -0.440, fy: 0.310, ph: 0.44 },
    ]
}

/// Chroma structure kept **inside** the red/blue Nyquist of 0.25 cyc/px.
///
/// This is the healthy control's whole point: chroma the sensor can genuinely
/// resolve, so a path that reproduces it is right and a path that smears it is
/// wrong. Anything faster than 0.25 would be chroma no arm could recover, and
/// charging an arm for it would be charging it for the sensor.
fn chroma_waves(scale: f64) -> Vec<Wave> {
    vec![
        Wave { a: 420.0 * scale, fx: 0.030, fy: 0.045, ph: 0.62 },
        Wave { a: 300.0 * scale, fx: 0.095, fy: -0.060, ph: 2.31 },
        Wave { a: 210.0 * scale, fx: 0.160, fy: 0.130, ph: 1.05 },
        Wave { a: 150.0 * scale, fx: -0.200, fy: 0.055, ph: 2.87 },
    ]
}

fn green_waves(scale: f64) -> Vec<Wave> {
    vec![
        Wave { a: 330.0 * scale, fx: 0.050, fy: -0.035, ph: 1.94 },
        Wave { a: 190.0 * scale, fx: 0.140, fy: 0.105, ph: 0.28 },
    ]
}

fn scene_achromatic() -> Scene {
    Scene {
        name: "achromatic",
        base: 8000.0,
        luma: luma_waves(),
        chroma: Vec::new(),
        green: Vec::new(),
    }
}

fn scene_coloured() -> Scene {
    Scene {
        name: "coloured",
        base: 8000.0,
        luma: luma_waves(),
        chroma: chroma_waves(1.0),
        green: green_waves(1.0),
    }
}

/// The healthy control of 111.3: a *legitimately* very colourful subject.
///
/// Its true `R - B` high-pass is large, so it wears the defect's signature. A
/// statistic that confuses "has chroma" with "has chroma error" convicts it, and
/// that is the confound that convicted a photograph of pink fabric.
fn scene_vivid() -> Scene {
    Scene {
        name: "vivid",
        base: 8000.0,
        luma: luma_waves(),
        chroma: chroma_waves(3.0),
        green: green_waves(3.0),
    }
}

/// A featureless achromatic field. **The regime V-GATHER actually measured.**
///
/// `chroma_real.py` restricts its statistic to the flattest quantile of 128 px
/// tiles, so the content it is weighing is *noise*, not detail. This scene is
/// that regime with the tile selection removed, because a uniform field needs no
/// selection -- and it is also the regime of the owner's own observation, which
/// was isolated magenta pixels on **achromatic material**: brushed steel, and
/// white trichomes.
fn scene_flat() -> Scene {
    Scene {
        name: "flat",
        base: 8000.0,
        luma: Vec::new(),
        chroma: Vec::new(),
        green: Vec::new(),
    }
}

// ---------------------------------------------------------------------------
// building a synthetic capture whose truth is known
// ---------------------------------------------------------------------------

/// A deterministic Gaussian source. Fixed seed so every number below reproduces.
struct Lcg(u64);

impl Lcg {
    fn next_f64(&mut self) -> f64 {
        self.0 = self.0.wrapping_mul(6364136223846793005).wrapping_add(1442695040888963407);
        ((self.0 >> 11) as f64) / ((1u64 << 53) as f64)
    }
    /// Box-Muller, one value per call. Wasteful and irrelevant at this size.
    fn normal(&mut self) -> f64 {
        let u1 = self.next_f64().max(1e-12);
        let u2 = self.next_f64();
        (-2.0 * u1.ln()).sqrt() * (TAU * u2).cos()
    }
}

/// Mosaic the scene onto a synthetic [`Frame`], in raw DN.
///
/// The buffer is wider and taller than the active region and the active origin
/// is not `(0, 0)`, matching the hazards the real decoder presents; the origin is
/// even in both axes so the RGGB phase survives.
///
/// `noise_sd` is per-channel Gaussian in **white-balanced** DN, applied at the
/// photosite, which is where a sensor applies it.
fn mosaic(scene: &Scene, wb: [f32; 4], noise_sd: f64, seed: u64) -> Frame {
    let (fw, fh) = (2 * GW, 2 * GH);
    let (ox, oy) = (2usize, 4usize);
    let stride = fw + ox + 3;
    let buffer_height = fh + oy + 2;
    let gain = [wb[0] / wb[1], 1.0f32, wb[2] / wb[1]];
    let mut data = vec![0u16; stride * buffer_height];
    let mut rng = Lcg(seed);
    for y in 0..fh {
        for x in 0..fw {
            let ci = rggb(x, y);
            let wbdn = scene.rgb(x as f64, y as f64)[ci]
                + if noise_sd > 0.0 { noise_sd * rng.normal() } else { 0.0 };
            let raw = wbdn / gain[ci] as f64 + BLACK as f64;
            data[(oy + y) * stride + ox + x] = raw.round().clamp(0.0, u16::MAX as f64) as u16;
        }
    }
    Frame {
        data,
        stride,
        buffer_height,
        active: Region { x: ox, y: oy, width: fw, height: fh },
        levels: Levels { black: BLACK, white: 15360.0 },
        iso: Some(100.0),
        wb_coeffs: wb,
        xyz_to_cam_rgbe: [[0.0; 3]; 4],
        color_matrices: Vec::new(),
        // Deliberately a path that does not exist: `strehl_raw::identity`
        // returns EMPTY for it, so `profile_for_capture_env` declines and the
        // lateral-CA composition in both gathers is the identity. Asserted in
        // `commission_ca` rather than assumed.
        camera: "synthetic".to_string(),
        path: PathBuf::from("synthetic-no-such-file.ARW"),
    }
}

/// Black-subtracted, white-balanced full-resolution mosaic over the active
/// region -- the units [`strehl_core::demosaic::Mosaic`] documents.
fn wb_mosaic(frame: &Frame) -> Vec<f32> {
    let (fw, fh) = (frame.active.width, frame.active.height);
    let gain = wb_gains(&frame.wb_coeffs);
    let (stride, ax, ay) = (frame.stride, frame.active.x, frame.active.y);
    let black = frame.levels.black;
    let mut mos = vec![0f32; fw * fh];
    mos.par_chunks_mut(fw).enumerate().for_each(|(y, orow)| {
        let row = (ay + y) * stride + ax;
        for (x, o) in orow.iter_mut().enumerate() {
            *o = (frame.data[row + x] as f32 - black) * gain[rggb(x, y)];
        }
    });
    mos
}

fn wb_gains(wb: &[f32; 4]) -> [f32; 3] {
    let (r, g, b) = (wb[0], wb[1], wb[2]);
    if r.is_finite() && g.is_finite() && b.is_finite() && r > 0.0 && g > 0.0 && b > 0.0 {
        [r / g, 1.0, b / g]
    } else {
        [1.0, 1.0, 1.0]
    }
}

/// Three full-resolution channel planes, in white-balanced DN.
type Planes = [Vec<f32>; 3];

/// The shipped demosaic, whichever `STREHL_DEMOSAIC` selects.
fn demosaic_planes(mos: &[f32], fw: usize, fh: usize) -> Planes {
    let m = Mosaic { data: mos, width: fw, height: fh };
    let mut rp = vec![0f32; fw * fh];
    let mut gp = vec![0f32; fw * fh];
    let mut bp = vec![0f32; fw * fh];
    rp.par_chunks_mut(fw)
        .zip(gp.par_chunks_mut(fw))
        .zip(bp.par_chunks_mut(fw))
        .enumerate()
        .for_each_init(
            || vec![0f32; fw * 3],
            |buf, (y, ((rr, gg), bb))| {
                demosaic_row(&m, y, buf);
                for x in 0..fw {
                    rr[x] = buf[3 * x];
                    gg[x] = buf[3 * x + 1];
                    bb[x] = buf[3 * x + 2];
                }
            },
        );
    [rp, gp, bp]
}

/// **The planted defect.** Bilinear demosaic: each channel interpolated from its
/// own samples with no gradient correction and no colour-difference stage.
///
/// This is the textbook demosaic every gradient-corrected method was invented to
/// beat, and its failure mode is precisely false colour on luma detail. If the
/// instrument cannot see this arm get worse, it cannot see anything.
fn demosaic_bilinear(mos: &[f32], fw: usize, fh: usize) -> Planes {
    let mut out = [vec![0f32; fw * fh], vec![0f32; fw * fh], vec![0f32; fw * fh]];
    for ch in 0..3 {
        let plane = &mut out[ch];
        for y in 0..fh {
            for x in 0..fw {
                let mut acc = 0.0f64;
                let mut n = 0usize;
                // Nearest same-channel sites within a 3x3 (green) or 5x5 (R/B)
                // neighbourhood; the measured site itself wins outright.
                let r = if ch == 1 { 1isize } else { 2isize };
                for dy in -r..=r {
                    for dx in -r..=r {
                        let (sx, sy) = (x as isize + dx, y as isize + dy);
                        if sx < 0 || sy < 0 || sx >= fw as isize || sy >= fh as isize {
                            continue;
                        }
                        let (sx, sy) = (sx as usize, sy as usize);
                        if rggb(sx, sy) != ch {
                            continue;
                        }
                        if dx == 0 && dy == 0 {
                            acc = mos[sy * fw + sx] as f64;
                            n = usize::MAX;
                            break;
                        }
                        let w = 1.0 / ((dx * dx + dy * dy) as f64);
                        acc += w * mos[sy * fw + sx] as f64;
                        n = n.saturating_add(1);
                    }
                    if n == usize::MAX {
                        break;
                    }
                }
                plane[y * fw + x] = if n == usize::MAX {
                    acc as f32
                } else {
                    // Re-walk for the weight normaliser; size makes this fine.
                    let mut wsum = 0.0f64;
                    for dy in -r..=r {
                        for dx in -r..=r {
                            let (sx, sy) = (x as isize + dx, y as isize + dy);
                            if sx < 0 || sy < 0 || sx >= fw as isize || sy >= fh as isize {
                                continue;
                            }
                            if rggb(sx as usize, sy as usize) != ch || (dx == 0 && dy == 0) {
                                continue;
                            }
                            wsum += 1.0 / ((dx * dx + dy * dy) as f64);
                        }
                    }
                    (acc / wsum.max(1e-9)) as f32
                };
            }
        }
    }
    out
}

/// **The planted defect, calibrated.** The oracle planes with a known chroma
/// perturbation of amplitude `d` DN added to red and subtracted from blue.
///
/// The first planted defect tried here was a bilinear warp-time demosaic, and it
/// **failed commissioning by reading as an improvement** -- correctly, as it
/// turns out, and that is reported as a finding rather than patched over. The
/// lesson is 110.6's in its sharpest form: a defect that is *also* a low-pass
/// cannot commission an error metric, because lowering an error by smoothing is
/// indistinguishable from lowering it by being right. This one cannot smooth:
/// it injects chroma and nothing else, at a known amplitude, so the metric must
/// rise **and rise by roughly the amount injected**.
///
/// The pattern alternates per *quad*, which is 0.25 cyc/full-res px -- inside the
/// red and blue Nyquist so it is not aliased away, and far enough above the 7x7
/// box high-pass corner to survive it.
fn planted_chroma(base: &Planes, fw: usize, fh: usize, d: f32) -> Planes {
    let mut out = base.clone();
    for y in 0..fh {
        for x in 0..fw {
            let w = if ((x / 2 + y / 2) % 2) == 0 { d } else { -d };
            out[0][y * fw + x] += w;
            out[2][y * fw + x] -= w;
        }
    }
    out
}

/// **The planted improvement / the oracle.** The scene's true channel planes.
///
/// Substituting these for the warp-time demosaic's output leaves everything else
/// on the shipping path untouched -- same gather, same re-mosaic, same final
/// Malvar -- so whatever error remains is *not* the warp-time demosaic's, and
/// whatever error disappears is exactly its.
fn oracle_planes(scene: &Scene, fw: usize, fh: usize) -> Planes {
    let mut out = [vec![0f32; fw * fh], vec![0f32; fw * fh], vec![0f32; fw * fh]];
    for y in 0..fh {
        for x in 0..fw {
            let t = scene.rgb(x as f64, y as f64);
            for ch in 0..3 {
                out[ch][y * fw + x] = t[ch] as f32;
            }
        }
    }
    out
}

// ---------------------------------------------------------------------------
// the arms
// ---------------------------------------------------------------------------

/// The full-resolution gather, from planes the caller supplies.
///
/// A transcription of [`align_cmd::warp_frame_in_place_fullres`] from its gather
/// loop onward, so that the oracle and planted-defect arms differ from the
/// shipping path in the planes and in nothing else. That claim is not asserted,
/// it is **tested**: `commission_harness` runs this against the shipping function
/// on the shipping demosaic and requires the two mosaics to be equal to the byte.
fn gather_from_planes(
    frame: &mut Frame,
    t: Similarity,
    geom: PlaneGeometry,
    resampler: Resampler,
    planes: &Planes,
) -> Result<f64> {
    let (gw, gh) = (geom.width, geom.height);
    let (fw, fh) = (2 * gw, 2 * gh);
    let black = frame.levels.black;
    let black_dn = black.round().clamp(0.0, u16::MAX as f32) as u16;
    let (stride, ax, ay) = (frame.stride, frame.active.x, frame.active.y);
    let gain = wb_gains(&frame.wb_coeffs);
    let ident = strehl_raw::identity(&frame.path);
    let ca = strehl_core::optics::profile_for_capture_env(ident.model.as_deref(), ident.lens_type3)?;
    let fgeom = PlaneGeometry { width: fw, height: fh };
    let (cx, cy) = (gw as f64 * 0.5, gh as f64 * 0.5);
    let mut dst = vec![0f32; gw * gh];
    let mut cover = vec![false; gw * gh];
    let mut covered_total = 0usize;

    for dy in 0..2usize {
        for dx in 0..2usize {
            let ch = strehl_core::optics::cfa_site_channel(dx, dy);
            let ci = rggb(dx, dy);
            let src = PlaneRef::from_geometry(&planes[ci], fgeom)
                .expect("plane does not match the frame geometry");
            let t_site = strehl_core::optics::OpticalProfile::compose(ca, ch, t);
            let (ox, oy) = (dx as f64 * 0.5, dy as f64 * 0.5);
            dst.par_chunks_mut(gw)
                .zip(cover.par_chunks_mut(gw))
                .enumerate()
                .for_each(|(py, (drow, crow))| {
                    for (px, (o, c)) in drow.iter_mut().zip(crow.iter_mut()).enumerate() {
                        let (sxp, syp) = t_site.apply_at(px as f64 + ox, py as f64 + oy, cx, cy);
                        match resampler.sample_checked(src, 2.0 * sxp, 2.0 * syp) {
                            Some(v) => {
                                *o = v;
                                *c = true;
                            }
                            None => {
                                *o = f32::NAN;
                                *c = false;
                            }
                        }
                    }
                });
            let inv = 1.0 / gain[ci];
            for py in 0..gh {
                let row = (ay + 2 * py + dy) * stride + ax + dx;
                let lo = py * gw;
                for px in 0..gw {
                    frame.data[row + 2 * px] = if cover[lo + px] {
                        covered_total += 1;
                        (dst[lo + px] * inv + black).round().clamp(0.0, u16::MAX as f32) as u16
                    } else {
                        black_dn
                    };
                }
            }
        }
    }
    Ok(covered_total as f64 / (4 * geom.pixels()) as f64)
}

/// **The candidate fix.** Demosaic once, warp in RGB, never re-mosaic.
///
/// Same gather geometry and same resampler as the full-resolution path, but the
/// warped samples are kept as RGB instead of being written back into a mosaic for
/// a second demosaic to re-interpolate. It is not a drop-in -- the merge consumes
/// mosaics -- so this is an *upper bound on the prize*, not a patch.
fn once_rgb(planes: &Planes, t: Similarity, geom: PlaneGeometry, resampler: Resampler) -> Planes {
    let (gw, gh) = (geom.width, geom.height);
    let (fw, fh) = (2 * gw, 2 * gh);
    let fgeom = PlaneGeometry { width: fw, height: fh };
    let (cx, cy) = (gw as f64 * 0.5, gh as f64 * 0.5);
    let mut out = [vec![0f32; fw * fh], vec![0f32; fw * fh], vec![0f32; fw * fh]];
    for ch in 0..3 {
        let src = PlaneRef::from_geometry(&planes[ch], fgeom).expect("plane geometry");
        out[ch].par_chunks_mut(fw).enumerate().for_each(|(y, orow)| {
            for (x, o) in orow.iter_mut().enumerate() {
                let (sxp, syp) = t.apply_at(x as f64 * 0.5, y as f64 * 0.5, cx, cy);
                *o = resampler
                    .sample_checked(src, 2.0 * sxp, 2.0 * syp)
                    .unwrap_or(f32::NAN);
            }
        });
    }
    out
}

// ---------------------------------------------------------------------------
// measurement
// ---------------------------------------------------------------------------

#[derive(Clone, Copy, Default)]
struct Stat {
    /// rms of `(R - B)_arm - (R - B)_truth`, DN.
    chroma_err: f64,
    /// rms of `(R - B)_arm` after a 5x5 box high-pass, DN. The V-GATHER
    /// statistic: no truth anywhere in it.
    chroma_hp: f64,
    /// rms of `(R - B)_truth` after the same high-pass, DN.
    chroma_hp_true: f64,
    /// rms of `G_arm - G_truth`, DN.
    luma_err: f64,
    /// Largest `|chroma_err|` at any interior pixel, DN.
    chroma_max: f64,
    n: usize,
}

/// Where the truth lives for output pixel `(x, y)`.
///
/// Output full-resolution pixel `(2px + dx, 2py + dy)` is the CFA site whose
/// plane coordinate is `(px + dx/2, py + dy/2)`, which is `(x/2, y/2)` exactly.
/// The warp is solved in plane units, so the source full-resolution coordinate is
/// `2 * t.apply_at(x/2, y/2)`. This is the mapping
/// [`align_cmd::warp_frame_in_place_fullres`] implements; the shipped
/// per-phase-plane gather implements a *different* one, and the difference is a
/// real defect rather than a choice of reference -- see the report.
fn truth_planes(scene: &Scene, t: Similarity, geom: PlaneGeometry) -> Planes {
    let (gw, gh) = (geom.width, geom.height);
    let (fw, fh) = (2 * gw, 2 * gh);
    let (cx, cy) = (gw as f64 * 0.5, gh as f64 * 0.5);
    let mut r = vec![0f32; fw * fh];
    let mut g = vec![0f32; fw * fh];
    let mut b = vec![0f32; fw * fh];
    r.par_chunks_mut(fw)
        .zip(g.par_chunks_mut(fw))
        .zip(b.par_chunks_mut(fw))
        .enumerate()
        .for_each(|(y, ((rr, gg), bb))| {
            for x in 0..fw {
                let (sxp, syp) = t.apply_at(x as f64 * 0.5, y as f64 * 0.5, cx, cy);
                let v = scene.rgb(2.0 * sxp, 2.0 * syp);
                rr[x] = v[0] as f32;
                gg[x] = v[1] as f32;
                bb[x] = v[2] as f32;
            }
        });
    [r, g, b]
}

/// `v` minus its 7x7 box mean.
///
/// The radius is 3 because that is what V-GATHER's `chroma.py` and
/// `chroma_real.py` use (`hp(y, r=3)`), and a statistic meant to be compared with
/// a recorded one must be the same statistic.
fn highpass(v: &[f32], fw: usize, fh: usize) -> Vec<f32> {
    const R: isize = 3;
    let mut out = vec![0f32; fw * fh];
    out.par_chunks_mut(fw).enumerate().for_each(|(y, orow)| {
        for (x, o) in orow.iter_mut().enumerate() {
            let mut acc = 0.0f64;
            let mut n = 0usize;
            for dy in -R..=R {
                for dx in -R..=R {
                    let (sx, sy) = (x as isize + dx, y as isize + dy);
                    if sx < 0 || sy < 0 || sx >= fw as isize || sy >= fh as isize {
                        continue;
                    }
                    acc += v[sy as usize * fw + sx as usize] as f64;
                    n += 1;
                }
            }
            *o = (v[y * fw + x] as f64 - acc / n as f64) as f32;
        }
    });
    out
}

fn measure(arm: &Planes, truth: &Planes, fw: usize, fh: usize) -> Stat {
    let m = 2 * MARGIN;
    let rb_arm: Vec<f32> = (0..fw * fh).map(|i| arm[0][i] - arm[2][i]).collect();
    let rb_true: Vec<f32> = (0..fw * fh).map(|i| truth[0][i] - truth[2][i]).collect();
    let hp_arm = highpass(&rb_arm, fw, fh);
    let hp_true = highpass(&rb_true, fw, fh);

    let (mut se, mut sh, mut sht, mut sl, mut mx, mut n) = (0.0, 0.0, 0.0, 0.0, 0.0f64, 0usize);
    for y in m..fh - m {
        for x in m..fw - m {
            let i = y * fw + x;
            let a = rb_arm[i];
            assert!(a.is_finite(), "arm has a hole at ({x}, {y}); MARGIN is too small");
            let e = (a - rb_true[i]) as f64;
            se += e * e;
            sh += (hp_arm[i] as f64).powi(2);
            sht += (hp_true[i] as f64).powi(2);
            sl += ((arm[1][i] - truth[1][i]) as f64).powi(2);
            mx = mx.max(e.abs());
            n += 1;
        }
    }
    let d = n as f64;
    Stat {
        chroma_err: (se / d).sqrt(),
        chroma_hp: (sh / d).sqrt(),
        chroma_hp_true: (sht / d).sqrt(),
        luma_err: (sl / d).sqrt(),
        chroma_max: mx,
        n,
    }
}

// ---------------------------------------------------------------------------
// running one scene through every arm
// ---------------------------------------------------------------------------

struct Run {
    label: &'static str,
    stat: Stat,
}

fn run_scene(
    scene: &Scene,
    t: Similarity,
    resampler: Resampler,
    wb: [f32; 4],
    noise_sd: f64,
) -> Result<Vec<Run>> {
    let geom = PlaneGeometry { width: GW, height: GH };
    let (fw, fh) = (2 * GW, 2 * GH);
    let base = mosaic(scene, wb, noise_sd, 0x5EED_1234_ABCD_0001);
    let truth_warped = truth_planes(scene, t, geom);
    let truth_still = truth_planes(scene, Similarity::IDENTITY, geom);

    let src_planes = demosaic_planes(&wb_mosaic(&base), fw, fh);
    let mut out = Vec::new();

    // Floor: one demosaic, no warp at all. Everything below must pay at least
    // this, because every arm ends in the same final Malvar.
    out.push(Run { label: "nowarp", stat: measure(&src_planes, &truth_still, fw, fh) });

    // The two shipping arms, called through the exported functions rather than
    // through `warp_frame_in_place`, so that an ambient STREHL_FULLRES_GATHER
    // cannot move both onto the same path and report a null it could not fail.
    let mut scratch = WarpScratch::new(geom);

    let mut f = base.clone();
    warp_frame_in_place_plane(&mut f, t, geom, resampler, &mut scratch)?;
    out.push(Run {
        label: "plane",
        stat: measure(&demosaic_planes(&wb_mosaic(&f), fw, fh), &truth_warped, fw, fh),
    });

    let mut f = base.clone();
    warp_frame_in_place_fullres(&mut f, t, geom, resampler, &mut scratch)?;
    let shipped_fullres = f.data.clone();
    out.push(Run {
        label: "fullres",
        stat: measure(&demosaic_planes(&wb_mosaic(&f), fw, fh), &truth_warped, fw, fh),
    });

    // Harness fidelity: the re-gather, fed the shipping demosaic, must reproduce
    // the shipping function to the byte.
    let mut f = base.clone();
    gather_from_planes(&mut f, t, geom, resampler, &src_planes)?;
    if f.data != shipped_fullres {
        let diff = f.data.iter().zip(&shipped_fullres).filter(|(a, b)| a != b).count();
        bail!("harness re-gather differs from warp_frame_in_place_fullres at {diff} samples");
    }

    // Planted improvement: same path, perfect warp-time demosaic.
    let oracle = oracle_planes(scene, fw, fh);
    let mut f = base.clone();
    gather_from_planes(&mut f, t, geom, resampler, &oracle)?;
    out.push(Run {
        label: "oracle",
        stat: measure(&demosaic_planes(&wb_mosaic(&f), fw, fh), &truth_warped, fw, fh),
    });

    // Planted defect, calibrated: the oracle with a known chroma injection. Two
    // amplitudes, so the metric is required to be monotone as well as awake.
    for (label, d) in [("oracle+100", 100.0f32), ("oracle+300", 300.0)] {
        let mut f = base.clone();
        gather_from_planes(&mut f, t, geom, resampler, &planted_chroma(&oracle, fw, fh, d))?;
        out.push(Run {
            label,
            stat: measure(&demosaic_planes(&wb_mosaic(&f), fw, fh), &truth_warped, fw, fh),
        });
    }

    // Reported, not commissioning: a bilinear warp-time demosaic. It is here
    // because it failed as a planted defect, and why it failed is a result.
    let mut f = base.clone();
    gather_from_planes(&mut f, t, geom, resampler, &demosaic_bilinear(&wb_mosaic(&base), fw, fh))?;
    out.push(Run {
        label: "bilin",
        stat: measure(&demosaic_planes(&wb_mosaic(&f), fw, fh), &truth_warped, fw, fh),
    });

    // Candidate fix: one demosaic, warped in RGB.
    out.push(Run {
        label: "once",
        stat: measure(&once_rgb(&src_planes, t, geom, resampler), &truth_warped, fw, fh),
    });

    Ok(out)
}

fn print_table(title: &str, runs: &[Run]) {
    println!("\n  {title}");
    println!(
        "    {:<9} {:>12} {:>12} {:>12} {:>11} {:>10}",
        "arm", "chroma err", "chroma HP", "true HP", "chroma max", "luma err"
    );
    for r in runs {
        println!(
            "    {:<9} {:>12.2} {:>12.2} {:>12.2} {:>11.1} {:>10.2}",
            r.label,
            r.stat.chroma_err,
            r.stat.chroma_hp,
            r.stat.chroma_hp_true,
            r.stat.chroma_max,
            r.stat.luma_err
        );
    }
}

fn get<'a>(runs: &'a [Run], label: &str) -> &'a Stat {
    &runs.iter().find(|r| r.label == label).expect("arm is present").stat
}

// ---------------------------------------------------------------------------
// commissioning
// ---------------------------------------------------------------------------

fn commission_cfa() -> Result<()> {
    use strehl_core::optics::{Channel, cfa_site_channel};
    for dy in 0..2 {
        for dx in 0..2 {
            let want = match cfa_site_channel(dx, dy) {
                Channel::Red => 0,
                Channel::Green => 1,
                Channel::Blue => 2,
            };
            if rggb(dx, dy) != want {
                bail!("local rggb({dx},{dy}) disagrees with cfa_site_channel");
            }
        }
    }
    println!("  C0 CFA parity          : rggb() agrees with cfa_site_channel at all four sites   PASS");
    Ok(())
}

fn commission_ca(frame: &Frame) -> Result<()> {
    let ident = strehl_raw::identity(&frame.path);
    let ca = strehl_core::optics::profile_for_capture_env(ident.model.as_deref(), ident.lens_type3)?;
    if ca.is_some() {
        bail!("a lateral-CA profile matched the synthetic frame; the arms are not isolated");
    }
    println!("  C0 CA isolation        : profile_for_capture_env declines the synthetic frame     PASS");
    Ok(())
}

/// The identity null: with no warp, the full-resolution gather is documented as a
/// bit-exact no-op, so it must land exactly on the `nowarp` floor.
fn commission_identity(scene: &Scene, resampler: Resampler) -> Result<()> {
    let geom = PlaneGeometry { width: GW, height: GH };
    let (fw, fh) = (2 * GW, 2 * GH);
    let base = mosaic(scene, WB, 0.0, 0x5EED_1234_ABCD_0001);
    let truth = truth_planes(scene, Similarity::IDENTITY, geom);
    let floor = measure(&demosaic_planes(&wb_mosaic(&base), fw, fh), &truth, fw, fh);
    let mut scratch = WarpScratch::new(geom);
    let mut f = base.clone();
    warp_frame_in_place_fullres(&mut f, Similarity::IDENTITY, geom, resampler, &mut scratch)?;
    let got = measure(&demosaic_planes(&wb_mosaic(&f), fw, fh), &truth, fw, fh);
    let d = (got.chroma_err - floor.chroma_err).abs();
    if d > 1e-6 {
        bail!("identity warp moved the chroma error by {d} DN; it is documented as a no-op");
    }
    println!(
        "  C1 identity null       : fullres at IDENTITY = nowarp floor, {:.4} DN both            PASS",
        floor.chroma_err
    );
    Ok(())
}

// ---------------------------------------------------------------------------
// part C: does this harness see the phenomenon on REAL sensor data?
// ---------------------------------------------------------------------------

/// A window of a real decoded frame, re-packaged as a [`Frame`].
///
/// The origin is forced even in both axes so the RGGB phase survives the crop.
/// The path is deliberately replaced with a non-existent one: the lateral-CA
/// profile is radial about the *frame* centre, and a crop has a different centre,
/// so keeping the real path would apply a correctly-measured aberration at the
/// wrong radius. CA composes identically into both arms, so it is not the
/// variable under test and declining it costs nothing.
fn real_window(path: &std::path::Path, x0: usize, y0: usize, gw: usize, gh: usize) -> Result<Frame> {
    let raw = strehl_raw::decode(path)?;
    let (fw, fh) = (2 * gw, 2 * gh);
    let (x0, y0) = (x0 & !1, y0 & !1);
    if x0 + fw > raw.active.width || y0 + fh > raw.active.height {
        bail!(
            "window {fw}x{fh} at ({x0}, {y0}) does not fit the {}x{} active area",
            raw.active.width,
            raw.active.height
        );
    }
    let (ox, oy) = (2usize, 4usize);
    let stride = fw + ox + 3;
    let buffer_height = fh + oy + 2;
    let mut data = vec![0u16; stride * buffer_height];
    for y in 0..fh {
        let src = (raw.active.y + y0 + y) * raw.stride + raw.active.x + x0;
        let dst = (oy + y) * stride + ox;
        data[dst..dst + fw].copy_from_slice(&raw.data[src..src + fw]);
    }
    Ok(Frame {
        data,
        stride,
        buffer_height,
        active: Region { x: ox, y: oy, width: fw, height: fh },
        levels: raw.levels,
        iso: raw.iso,
        wb_coeffs: raw.wb_coeffs,
        xyz_to_cam_rgbe: raw.xyz_to_cam_rgbe,
        color_matrices: raw.color_matrices,
        camera: raw.camera,
        path: PathBuf::from("synthetic-no-such-file.ARW"),
    })
}

/// V-GATHER's statistic, on planes rather than on rendered masters: chroma `R-B`
/// high-pass rms restricted to the flattest quantile of 128 px tiles, with the
/// tile selection made **once** on the mean of the arms so the site list is
/// common to all of them.
///
/// Returns `(name, chroma_hp, luma_hp, corr_rb)` per arm. The luma leg matters
/// because V-GATHER reported both, and the *ratio* of the two ratios is the
/// quantity that separates a chroma-specific defect from a broadband bandwidth
/// change. `corr_rb` is the Pearson correlation of the high-passed R and B
/// planes over the same tiles: it tests the proposed mechanism directly, since
/// `var(R-B) = var R + var B - 2 rho sqrt(var R var B)` makes any suppression of
/// `R-B` at fixed per-channel variance a statement about `rho` and nothing else.
fn flat_tile_chroma(
    arms: &[(&str, Planes)],
    sel_ref: &Planes,
    fw: usize,
    fh: usize,
    q: f64,
) -> Vec<(String, f64, f64, f64)> {
    const T: usize = 128;
    let (tw, th) = (fw / T, fh / T);
    // Tile selection is made on ONE fixed reference arm, not on the mean of the
    // arms being compared. V-GATHER selects on `(l0+l1)/2`, which makes the site
    // list move when the arms move; adding a fourth arm to that scheme changed
    // the `plane` reading from 15.92 to 41.68 DN on the same pixels, which is
    // how this was caught. The unwarped frame is the natural reference for "the
    // subject is flat here" and is common to every comparison.
    let mean_l: Vec<f64> = (0..fw * fh)
        .map(|i| (0.2126 * sel_ref[0][i] + 0.7152 * sel_ref[1][i] + 0.0722 * sel_ref[2][i]) as f64)
        .collect();
    let mut std: Vec<f64> = Vec::with_capacity(tw * th);
    for ty in 0..th {
        for tx in 0..tw {
            // The outer tile ring is excluded for every arm alike. The gather
            // reads outside the frame there, and `once_rgb` reports that
            // honestly as NaN rather than inventing an edge-clamped value; a
            // border tile would therefore compare a real arm against a hole.
            let border = tx == 0 || ty == 0 || tx + 1 == tw || ty + 1 == th;
            if border {
                std.push(f64::INFINITY);
                continue;
            }
            let (mut s, mut s2) = (0.0f64, 0.0f64);
            for y in ty * T..(ty + 1) * T {
                for x in tx * T..(tx + 1) * T {
                    let v = mean_l[y * fw + x];
                    s += v;
                    s2 += v * v;
                }
            }
            let n = (T * T) as f64;
            std.push((s2 / n - (s / n).powi(2)).max(0.0).sqrt());
        }
    }
    let mut sorted: Vec<f64> = std.iter().copied().filter(|v| v.is_finite()).collect();
    sorted.sort_by(|a, b| a.partial_cmp(b).unwrap());
    let thr = sorted[((sorted.len() as f64 * q) as usize).min(sorted.len() - 1)];
    let sel: Vec<bool> = std.iter().map(|s| *s <= thr).collect();

    arms.iter()
        .map(|(name, p)| {
            let rms = |plane: &[f32]| {
                let hp = highpass(plane, fw, fh);
                let (mut acc, mut n) = (0.0f64, 0usize);
                for ty in 0..th {
                    for tx in 0..tw {
                        if !sel[ty * tw + tx] {
                            continue;
                        }
                        for y in ty * T..(ty + 1) * T {
                            for x in tx * T..(tx + 1) * T {
                                acc += (hp[y * fw + x] as f64).powi(2);
                                n += 1;
                            }
                        }
                    }
                }
                (acc / n as f64).sqrt()
            };
            let rb: Vec<f32> = (0..fw * fh).map(|i| p[0][i] - p[2][i]).collect();
            let lum: Vec<f32> = (0..fw * fh)
                .map(|i| 0.2126 * p[0][i] + 0.7152 * p[1][i] + 0.0722 * p[2][i])
                .collect();
            // Pearson rho of the high-passed R and B planes over the admitted
            // tiles. Means are ~0 by construction (the high pass removes them),
            // but they are subtracted anyway rather than assumed away.
            let (rhp, bhp) = (highpass(&p[0], fw, fh), highpass(&p[2], fw, fh));
            let (mut sr, mut sb, mut srr, mut sbb, mut srb, mut n) =
                (0.0f64, 0.0f64, 0.0f64, 0.0f64, 0.0f64, 0usize);
            for ty in 0..th {
                for tx in 0..tw {
                    if !sel[ty * tw + tx] {
                        continue;
                    }
                    for y in ty * T..(ty + 1) * T {
                        for x in tx * T..(tx + 1) * T {
                            let (a, b) = (rhp[y * fw + x] as f64, bhp[y * fw + x] as f64);
                            sr += a;
                            sb += b;
                            srr += a * a;
                            sbb += b * b;
                            srb += a * b;
                            n += 1;
                        }
                    }
                }
            }
            let nf = n as f64;
            let (cr, cb) = (srr / nf - (sr / nf).powi(2), sbb / nf - (sb / nf).powi(2));
            let cov = srb / nf - (sr / nf) * (sb / nf);
            let rho = cov / (cr.max(1e-30) * cb.max(1e-30)).sqrt();
            ((*name).to_string(), rms(&rb), rms(&lum), rho)
        })
        .collect()
}

fn run_real(path: &std::path::Path, x0: usize, y0: usize, gw: usize, gh: usize) -> Result<()> {
    let geom = PlaneGeometry { width: gw, height: gh };
    let (fw, fh) = (2 * gw, 2 * gh);
    let resampler = Resampler::CatmullRom;
    let t = Similarity::from_params(SimilarityParams { ax: 0.37, ay: 0.23, g: 0.0004, rot: 0.0006 });
    let base = real_window(path, x0, y0, gw, gh)?;
    println!(
        "  window {fw}x{fh} at ({x0}, {y0}) of {}   ISO {}   black {:.0}",
        path.file_name().unwrap().to_string_lossy(),
        base.iso.map(|v| v.to_string()).unwrap_or_else(|| "?".into()),
        base.levels.black
    );

    let mut scratch = WarpScratch::new(geom);
    let nowarp = demosaic_planes(&wb_mosaic(&base), fw, fh);
    let mut f = base.clone();
    warp_frame_in_place_plane(&mut f, t, geom, resampler, &mut scratch)?;
    let plane = demosaic_planes(&wb_mosaic(&f), fw, fh);
    let mut f = base.clone();
    warp_frame_in_place_fullres(&mut f, t, geom, resampler, &mut scratch)?;
    let fullres = demosaic_planes(&wb_mosaic(&f), fw, fh);

    println!("\n  camera-native RGB -- the space the demosaic and the merge work in");
    // `once` is the candidate fix: demosaic exactly once, warp the RGB planes.
    // It is measured here not to propose it but because the statistic's response
    // to it is part of the evidence about what the statistic is detecting.
    let once = once_rgb(&nowarp, t, geom, resampler);
    let arms = vec![
        ("nowarp", nowarp.clone()),
        ("plane", plane.clone()),
        ("fullres", fullres.clone()),
        ("once", once.clone()),
    ];
    for q in [0.05, 0.10, 0.25, 1.00] {
        let r = flat_tile_chroma(&arms, &nowarp, fw, fh, q);
        let (n, p, fr) = (r[0].1, r[1].1, r[2].1);
        let (lp, lf) = (r[1].2, r[2].2);
        println!(
            "  q={q:<5} chroma HP  nowarp {n:8.2}   plane {p:8.2}   fullres {fr:8.2}   \
             plane->fullres {:+6.1}%   fullres/nowarp {:.3}   luma p->f {:+6.1}%   \
             chroma/luma {:.4}",
            100.0 * (fr / p - 1.0),
            fr / n,
            100.0 * (lf / lp - 1.0),
            (fr / p) / (lf / lp)
        );
        println!(
            "          rho(R_hp,B_hp)  nowarp {:+.4}   plane {:+.4}   fullres {:+.4}   \
             once {:+.4}      once: chroma {:8.2} luma {:8.2}  chroma/luma vs plane {:.4}",
            r[0].3,
            r[1].3,
            r[2].3,
            r[3].3,
            r[3].1,
            r[3].2,
            (r[3].1 / p) / (r[3].2 / lp)
        );
    }

    // Is the sign a property of THIS warp? A focus bracket's frames carry a wide
    // spread of displacements and scales, and a statistic that changes sign with
    // warp magnitude would make a single-warp measurement worthless. Swept rather
    // than argued.
    println!("\n  warp sweep, camera-native, q=0.10 -- is the sign a property of one warp?");
    println!(
        "    {:>7} {:>7} {:>9} {:>9} {:>9} {:>10}",
        "trans", "scale%", "nowarp", "plane", "fullres", "p->f"
    );
    for (ax, ay, g, rot) in [
        (0.05, 0.03, 0.0, 0.0),
        (0.25, 0.15, 0.0, 0.0),
        (0.50, 0.50, 0.0, 0.0),
        (1.37, 0.83, 0.0, 0.0),
        (3.10, -2.40, 0.0, 0.0),
        (0.37, 0.23, 0.005, 0.0),
        (0.37, 0.23, 0.023, 0.0),
        (0.37, 0.23, 0.0, 0.004),
        (2.50, 1.75, 0.012, 0.002),
    ] {
        let tw = Similarity::from_params(SimilarityParams { ax, ay, g, rot });
        let mut f = base.clone();
        warp_frame_in_place_plane(&mut f, tw, geom, resampler, &mut scratch)?;
        let a = demosaic_planes(&wb_mosaic(&f), fw, fh);
        let mut f = base.clone();
        warp_frame_in_place_fullres(&mut f, tw, geom, resampler, &mut scratch)?;
        let b = demosaic_planes(&wb_mosaic(&f), fw, fh);
        let arms = vec![("nowarp", nowarp.clone()), ("plane", a), ("fullres", b)];
        let r = flat_tile_chroma(&arms, &nowarp, fw, fh, 0.10);
        println!(
            "    {:>7.2} {:>7.2} {:>9.2} {:>9.2} {:>9.2} {:>+9.1}%",
            (ax * ax + ay * ay).sqrt(),
            g * 100.0,
            r[0].1,
            r[1].1,
            r[2].1,
            100.0 * (r[2].1 / r[1].1 - 1.0)
        );
    }

    // The space V-GATHER's statistic was actually taken in. `chroma_real.py`
    // reads `--linear-srgb --demosaic` masters, so its `R - B` is an sRGB
    // difference, not a camera one. The transform is a fixed linear map, so a
    // global gain cancels out of every ratio below and the exposure stage can be
    // skipped without changing a single number in this table.
    let Some(xyz_to_cam) = base.xyz_to_cam_rgb() else {
        println!("\n  linear sRGB: SKIPPED, this file carries no usable characterisation");
        return Ok(());
    };
    let Some(render) = strehl_core::color::camera_to_srgb(xyz_to_cam) else {
        println!("\n  linear sRGB: SKIPPED, camera_to_srgb declined the characterisation");
        return Ok(());
    };
    let m = *render.matrix();
    println!(
        "\n  linear sRGB -- the space V-GATHER's statistic was taken in\n  \
         camera->sRGB matrix rows: [{:.3} {:.3} {:.3}] [{:.3} {:.3} {:.3}] [{:.3} {:.3} {:.3}]",
        m[0][0], m[0][1], m[0][2], m[1][0], m[1][1], m[1][2], m[2][0], m[2][1], m[2][2]
    );
    let to_srgb = |p: &Planes| -> Planes {
        let mut o = [vec![0f32; fw * fh], vec![0f32; fw * fh], vec![0f32; fw * fh]];
        for i in 0..fw * fh {
            let v = strehl_core::color::apply(&m, [p[0][i], p[1][i], p[2][i]]);
            o[0][i] = v[0];
            o[1][i] = v[1];
            o[2][i] = v[2];
        }
        o
    };
    let arms = vec![
        ("nowarp", to_srgb(&nowarp)),
        ("plane", to_srgb(&plane)),
        ("fullres", to_srgb(&fullres)),
        ("once", to_srgb(&once)),
    ];
    let sel_ref = to_srgb(&nowarp);
    for q in [0.05, 0.10, 0.25, 1.00] {
        let r = flat_tile_chroma(&arms, &sel_ref, fw, fh, q);
        let (n, p, fr) = (r[0].1, r[1].1, r[2].1);
        let (lp, lf) = (r[1].2, r[2].2);
        println!(
            "  q={q:<5} chroma HP  nowarp {n:8.2}   plane {p:8.2}   fullres {fr:8.2}   \
             plane->fullres {:+6.1}%   fullres/nowarp {:.3}   luma p->f {:+6.1}%   \
             chroma/luma {:.4}",
            100.0 * (fr / p - 1.0),
            fr / n,
            100.0 * (lf / lp - 1.0),
            (fr / p) / (lf / lp)
        );
        println!(
            "          rho(R_hp,B_hp)  nowarp {:+.4}   plane {:+.4}   fullres {:+.4}   \
             once {:+.4}   once: chroma {:8.2} luma {:8.2}  chroma/luma vs plane {:.4}",
            r[0].3,
            r[1].3,
            r[2].3,
            r[3].3,
            r[3].1,
            r[3].2,
            (r[3].1 / p) / (r[3].2 / lp)
        );
    }
    Ok(())
}


// ---------------------------------------------------------------------------
// main
// ---------------------------------------------------------------------------

/// The warp every arm is measured under: a realistic frame-to-frame similarity.
///
/// M10 measured 4.6% scale drift across 105 frames, so ~0.04% per frame; the
/// translation is sub-pixel because that is where an interpolator does its work
/// and an integer shift would make Catmull-Rom the identity and the whole
/// question vanish.
fn warp() -> Similarity {
    Similarity::from_params(SimilarityParams { ax: 0.37, ay: 0.23, g: 0.0004, rot: 0.0006 })
}

fn main() -> Result<()> {
    let resampler = Resampler::CatmullRom;
    let t = warp();

    println!("BUILD-DEMOSAIC -- is the gather flip's chroma excess restored or created?");
    println!(
        "  synthetic scenes {}x{} full-res, quad plane {GW}x{GH}, margin {MARGIN} plane px, {:?}",
        2 * GW,
        2 * GH,
        resampler
    );
    let p = t.to_params();
    println!(
        "  warp: translation ({:.2}, {:.2}) plane px, scale {:+.4}%, rotation {:+.4} rad",
        p.ax,
        p.ay,
        p.g * 100.0,
        p.rot
    );
    println!("  chroma is R-B in white-balanced DN; the high pass is V-GATHER's 7x7 box\n");

    println!("== commissioning ==");
    commission_cfa()?;
    commission_ca(&mosaic(&scene_achromatic(), WB, 0.0, 1))?;
    commission_identity(&scene_achromatic(), resampler)?;

    // ---------------------------------------------------------------- part B
    println!("\n== part B: synthetic scenes, error measured against a KNOWN truth ==");
    let flat = run_scene(&scene_flat(), t, resampler, WB, 400.0)?;
    print_table(
        "FLAT + noise sd 400 DN -- V-GATHER's regime (flattest tiles) and the owner's\n  \
         (magenta pixels on brushed steel). True R-B is EXACTLY 0 everywhere.",
        &flat,
    );
    let ach = run_scene(&scene_achromatic(), t, resampler, WB, 0.0)?;
    print_table(
        "ACHROMATIC detail, noiseless -- luma to 0.45 cyc/px, true R-B EXACTLY 0 everywhere",
        &ach,
    );
    let col = run_scene(&scene_coloured(), t, resampler, WB, 0.0)?;
    print_table("COLOURED -- real chroma detail inside the R/B Nyquist", &col);
    let viv = run_scene(&scene_vivid(), t, resampler, WB, 0.0)?;
    print_table(
        "VIVID -- healthy control (111.3): 3x the chroma, wears the defect's signature",
        &viv,
    );

    // ------------------------------------------------- commissioning verdicts
    println!("\n== commissioning, on the arms above ==");
    let mut fails: Vec<String> = Vec::new();
    for (name, runs) in [("flat", &flat), ("achromatic", &ach), ("coloured", &col), ("vivid", &viv)]
    {
        let (o, d1, d3) = (get(runs, "oracle"), get(runs, "oracle+100"), get(runs, "oracle+300"));
        let ok = d1.chroma_err > o.chroma_err && d3.chroma_err > d1.chroma_err;
        if !ok {
            fails.push(format!("C2 planted chroma is not monotone on `{name}`"));
        }
        println!(
            "  C2 planted defect  {name:<11}: oracle {:8.2} -> +100 DN {:8.2} -> +300 DN {:8.2}   {}",
            o.chroma_err,
            d1.chroma_err,
            d3.chroma_err,
            if ok { "PASS" } else { "FAIL" }
        );
    }
    for (name, runs) in [("flat", &flat), ("achromatic", &ach), ("coloured", &col), ("vivid", &viv)]
    {
        let (o, f) = (get(runs, "oracle"), get(runs, "fullres"));
        let ok = o.chroma_err < f.chroma_err;
        if !ok {
            fails.push(format!("C3 the oracle did not beat the shipping path on `{name}`"));
        }
        println!(
            "  C3 planted improve {name:<11}: oracle {:8.2} < shipping fullres {:8.2}            {}",
            o.chroma_err,
            f.chroma_err,
            if ok { "PASS" } else { "FAIL" }
        );
    }
    {
        let vt = get(&viv, "nowarp").chroma_hp_true;
        let am = get(&ach, "nowarp").chroma_hp;
        let ve = get(&viv, "oracle").chroma_err;
        let ok = vt > 3.0 * am && ve < get(&viv, "fullres").chroma_err;
        if !ok {
            fails.push("C4 the healthy control did not behave as a healthy control".into());
        }
        println!(
            "  C4 healthy control        : vivid TRUE chroma HP {vt:.1} DN is {:.1}x the achromatic\n\
             \x20                              scene's MANUFACTURED HP {am:.1} DN, and the metric still\n\
             \x20                              ranks the oracle best on it ({ve:.1} DN)             {}",
            vt / am,
            if ok { "PASS" } else { "FAIL" }
        );
    }
    println!("  C5 harness fidelity       : re-gather == warp_frame_in_place_fullres to the byte");
    println!("                              (checked inside every run above; a mismatch aborts)  PASS");

    // ---------------------------------------------------------------- part C
    println!("\n== part C: does this harness see the phenomenon on REAL sensor data? ==");
    println!("  V-GATHER measured chroma (R-B) high-pass rising 25.2% to 48.6% plane -> fullres,");
    println!("  on rendered masters, restricted to the flattest tiles. Same statistic here, on a");
    println!("  window of a real capture, one frame, no merge and no render:");
    let dir = std::env::args().nth(1).unwrap_or_else(|| r"D:\personal\macro\wrapped-text-1".into());
    let mut frames: Vec<PathBuf> = std::fs::read_dir(&dir)?
        .filter_map(|e| e.ok().map(|e| e.path()))
        .filter(|p| p.extension().is_some_and(|e| e.eq_ignore_ascii_case("ARW")))
        .collect();
    frames.sort();
    if frames.is_empty() {
        println!("  SKIPPED: no .ARW under {dir}");
    } else {
        run_real(&frames[0], 1024, 1024, 768, 768)?;
    }
    // A second subject, because the owner's magenta observation was on brushed
    // steel and white trichomes rather than on paper, and a mechanism that only
    // shows on one subject is a subject, not a mechanism.
    for other in [r"D:\personal\macro\tweezers-cpl", r"D:\personal\macro\lavendar-cpl"] {
        let mut fs: Vec<PathBuf> = std::fs::read_dir(other)
            .into_iter()
            .flatten()
            .filter_map(|e| e.ok().map(|e| e.path()))
            .filter(|p| p.extension().is_some_and(|e| e.eq_ignore_ascii_case("ARW")))
            .collect();
        fs.sort();
        if let Some(f) = fs.first() {
            println!();
            run_real(f, 1024, 1024, 768, 768)?;
        }
    }

    println!("\n== the reading ==");
    for (name, runs) in [("flat+noise", &flat), ("achromatic", &ach), ("coloured", &col), ("vivid", &viv)]
    {
        let (n, pl, fr, or, on) = (
            get(runs, "nowarp"),
            get(runs, "plane"),
            get(runs, "fullres"),
            get(runs, "oracle"),
            get(runs, "once"),
        );
        println!(
            "  {name:<11} chroma err vs truth: nowarp {:8.2}  plane {:8.2}  fullres {:8.2}  \
             oracle {:8.2}  once {:8.2}",
            n.chroma_err, pl.chroma_err, fr.chroma_err, or.chroma_err, on.chroma_err
        );
        println!(
            "  {:<11} fullres - plane {:+8.2} DN     fullres - oracle {:+8.2} DN (the warp-time \
             demosaic's own)     fullres - once {:+8.2} DN",
            "",
            fr.chroma_err - pl.chroma_err,
            fr.chroma_err - or.chroma_err,
            fr.chroma_err - on.chroma_err
        );
    }

    println!("\n== V-GATHER's own ceiling argument, restated with a truth behind it ==");
    println!("  `chroma.py`: NOGATHER (mosaic -> Malvar, no resampling) is the CEILING on restored");
    println!("  noise -- resampling can only attenuate, so an arm ABOVE it manufactured the excess.");
    for (name, runs) in [("flat+noise", &flat), ("achromatic", &ach), ("coloured", &col), ("vivid", &viv)]
    {
        let (n, pl, fr) = (get(runs, "nowarp"), get(runs, "plane"), get(runs, "fullres"));
        println!(
            "  {name:<11} chroma HP: nowarp {:8.2}  plane {:8.2} ({:.3}x)  fullres {:8.2} ({:.3}x)",
            n.chroma_hp,
            pl.chroma_hp,
            pl.chroma_hp / n.chroma_hp,
            fr.chroma_hp,
            fr.chroma_hp / n.chroma_hp
        );
    }

    println!("\n== 111.4's arithmetic, checked independently ==");
    println!(
        "  111.4: per-channel sd 400 DN puts sqrt(2)*400 = 566 DN on R-B before any high pass.\n  \
         Measured on the FLAT scene, whose true chroma is zero, so every DN below is error:\n  \
         nowarp chroma err {:.2} DN, chroma HP {:.2} DN.",
        get(&flat, "nowarp").chroma_err,
        get(&flat, "nowarp").chroma_hp
    );

    println!("\n== white balance control ==");
    let unity = run_scene(&scene_achromatic(), t, resampler, [1.0, 1.0, 1.0, f32::NAN], 0.0)?;
    print_table("ACHROMATIC, unity white balance -- isolates the WB round trip", &unity);

    if !fails.is_empty() {
        for f in &fails {
            println!("\nCOMMISSIONING FAILURE: {f}");
        }
        bail!("{} commissioning arm(s) failed; no verdict is reportable", fails.len());
    }
    println!("\n  n = {} interior pixels per synthetic arm", get(&ach, "nowarp").n);
    Ok(())
}
