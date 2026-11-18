//! Calibrated depth-guided fusion (`STREHL_FUSION=calibrated`; proposal item
//! 2). Two folds: the election, then the depth-guided fusion; at the write,
//! each plane becomes the fusion's fine bands, each brought to the election's
//! amplitude by one gain per band and channel, over the election's coarse
//! remainder.
//!
//! # Why
//!
//! `STREHL_FUSION=depth` doubles fine-detail signal-to-noise power against
//! the election but keeps only about 0.82 of the finest detail and lifts dark
//! areas by about 10 %. Round 1 of the A7CR four-shot quality investigation
//! measured both as calibration errors on a post-merge prototype
//! (`experiments/a7cr-fourshot-quality-2026-11-16/calibrated-fusion.py`):
//! with each band of the fusion brought back to the election's amplitude and
//! everything coarser than 32 px taken from the election, fine detail read
//! 1.00-1.04 of the election's at 0.72-0.75 of its noise, and dark areas
//! 0.95-1.01 of the election's level beyond 6 px from bright detail.
//!
//! # How
//!
//! Gaussian bands between sigma 0, 1, 2, 4, 8, 16 and 32 output px, taken
//! on each channel interleaved to full resolution from its four carried site
//! planes (without the carry, on each plane's quad grid at half those
//! sigmas). Bands must be taken at full resolution: a site plane holds
//! output detail above 0.25 cycles/px only aliased, and a first version that
//! split bands per plane left the fused fine detail at 0.92 of the
//! election's. Per band and channel the gain is
//! `<B(E_a) B(E_b)> / <B(F) B(E')>`: the election's signal power over the
//! fusion's cross-power with the election's other half (noise is independent
//! between halves, so neither term is biased by it), averaged over both
//! pairings. The output is `sum_k g_k B_k(F) + G_32(E)`, for the full stack
//! and for each half alike, so the optical restoration measures the
//! calibrated stack.
//!
//! # Limits
//!
//! Two folds and two depth measurements (about twice the render time); the
//! election's finished planes and halves are held through the second fold.
//! Needs the half-stacks the optical restoration keeps.
use super::*;
use std::sync::Mutex;
use std::sync::atomic::{AtomicU8, Ordering};

/// Band edges as Gaussian sigmas in output px (0-1, 1-2, 2-4, 4-8, 8-16 and
/// 16-32 px, the prototype's bands); coarser than the last, the election.
const OUTPUT_SIGMAS: [f32; BANDS + 1] = [0.0, 1.0, 2.0, 4.0, 8.0, 16.0, 32.0];
const BANDS: usize = 6;
/// Bounds on a band gain: outside them the calibration is refused for that
/// band (gain 1) and the log says so.
const GAIN_RANGE: (f64, f64) = (0.6, 1.8);

const NONE: u8 = 0;
const ELECTION: u8 = 1;
const FUSION: u8 = 2;
static PASS: AtomicU8 = AtomicU8::new(NONE);

struct ElectionPlanes {
    full: Vec<Vec<f32>>,
    halves: [Vec<Vec<f32>>; 2],
}

static KEPT: Mutex<Option<ElectionPlanes>> = Mutex::new(None);
/// This pass's finished half-stacks (even frames, odd frames), when the
/// calibrated mode asked the fold for them.
static HALVES: Mutex<Option<[Vec<Vec<f32>>; 2]>> = Mutex::new(None);

/// Where the fold's finished half-stacks go: to this module during a
/// calibrated pass (pass 2 hands its calibrated halves to the restoration
/// in [`combine`]), otherwise to the optical restoration.
pub(super) fn route_halves(even: Vec<Vec<f32>>, odd: Vec<Vec<f32>>) {
    if election_pass() || fusion_pass() {
        *HALVES.lock().unwrap_or_else(|e| e.into_inner()) = Some([even, odd]);
    } else {
        optical_restore::stash_halves(even, odd);
    }
}

fn take_pass_halves() -> Option<[Vec<Vec<f32>>; 2]> {
    HALVES.lock().unwrap_or_else(|e| e.into_inner()).take()
}

/// Whether `STREHL_FUSION=calibrated` was asked for.
pub(super) fn requested() -> bool {
    std::env::var(depth_guide::ENV)
        .ok()
        .is_some_and(|v| v.trim() == "calibrated")
}

/// The calibrated mode's first pass: the plain election, kept, not written.
pub(super) fn election_pass() -> bool {
    PASS.load(Ordering::Relaxed) == ELECTION
}

/// The calibrated mode's second pass: the fusion, combined at the write.
pub(super) fn fusion_pass() -> bool {
    PASS.load(Ordering::Relaxed) == FUSION
}

/// Resets the pass and drops the kept planes, however the render ends.
struct Reset;

impl Drop for Reset {
    fn drop(&mut self) {
        PASS.store(NONE, Ordering::Relaxed);
        *KEPT.lock().unwrap_or_else(|e| e.into_inner()) = None;
        *HALVES.lock().unwrap_or_else(|e| e.into_inner()) = None;
    }
}

/// Run the two folds.
pub(super) fn run(opts: &MergeOptions) -> Result<()> {
    let _reset = Reset;
    eprintln!(
        "fusion          : CALIBRATED ({}=calibrated) -- pass 1 of 2: the election, kept for \
         calibration and its coarse levels",
        depth_guide::ENV
    );
    PASS.store(ELECTION, Ordering::Relaxed);
    run_pyramid_once(opts).context("calibrated fusion: the election pass")?;
    ensure!(
        KEPT.lock().unwrap_or_else(|e| e.into_inner()).is_some(),
        "calibrated fusion: the election pass kept no planes"
    );
    eprintln!(
        "fusion          : CALIBRATED -- pass 2 of 2: the depth-guided fusion, its bands brought \
         to the election's amplitude"
    );
    PASS.store(FUSION, Ordering::Relaxed);
    run_pyramid_once(opts).context("calibrated fusion: the fusion pass")
}

/// Pass 1, at the write: keep the election's finished planes and halves.
pub(super) fn keep(full: Vec<Vec<f32>>) -> Result<()> {
    let halves = take_pass_halves().with_context(|| {
        format!(
            "{}=calibrated: the election pass kept no half-stacks (a half folded no frames?)",
            depth_guide::ENV
        )
    })?;
    *KEPT.lock().unwrap_or_else(|e| e.into_inner()) = Some(ElectionPlanes { full, halves });
    eprintln!("fusion          : election planes and half-stacks kept for pass 2");
    Ok(())
}

fn channel_of(p: usize, planes: usize) -> usize {
    if planes == BAND_PLANES {
        [0, 1, 1, 2][p]
    } else {
        colour_carry::plane_channel(p)
    }
}

/// One image the calibration works on: a channel interleaved to full
/// resolution from its four carried site planes, or (without the carry) one
/// plane on its own quad grid.
#[derive(Clone, Copy)]
enum Unit {
    Channel(usize),
    Plane(usize),
}

/// The units of a render with `n` planes on a `w x h` quad grid, each with
/// its channel, image size and band-edge sigmas in its own pixels.
fn units(n: usize, w: usize, h: usize) -> Vec<(Unit, usize, usize, usize, [f32; BANDS + 1])> {
    if n == colour_carry::PLANES {
        (0..3)
            .map(|c| (Unit::Channel(c), c, 2 * w, 2 * h, OUTPUT_SIGMAS))
            .collect()
    } else {
        // A quad-grid plane's pixel is two output px.
        let half = OUTPUT_SIGMAS.map(|s| 0.5 * s);
        (0..n)
            .map(|p| (Unit::Plane(p), channel_of(p, n), w, h, half))
            .collect()
    }
}

fn extract(set: &[Vec<f32>], unit: Unit, w: usize, h: usize) -> Vec<f32> {
    match unit {
        Unit::Plane(p) => set[p].clone(),
        Unit::Channel(c) => {
            let mut img = vec![0.0f32; 4 * w * h];
            img.par_chunks_mut(2 * w).enumerate().for_each(|(y, row)| {
                let (py, dy) = (y / 2, y % 2);
                for (x, o) in row.iter_mut().enumerate() {
                    let p = colour_carry::plane_of(x % 2, dy, c);
                    *o = set[p][py * w + x / 2];
                }
            });
            img
        }
    }
}

fn store(set: &mut [Vec<f32>], unit: Unit, w: usize, img: Vec<f32>) {
    match unit {
        Unit::Plane(p) => set[p] = img,
        Unit::Channel(c) => {
            for dy in 0..2 {
                for dx in 0..2 {
                    let p = colour_carry::plane_of(dx, dy, c);
                    set[p].par_chunks_mut(w).enumerate().for_each(|(py, row)| {
                        let src = &img[(2 * py + dy) * 2 * w..(2 * py + dy + 1) * 2 * w];
                        for (px, o) in row.iter_mut().enumerate() {
                            *o = src[2 * px + dx];
                        }
                    });
                }
            }
        }
    }
}

fn step(sig: &[f32; BANDS + 1], k: usize) -> f32 {
    (sig[k + 1] * sig[k + 1] - sig[k] * sig[k]).sqrt()
}

/// Per band, `sum B_k(a) B_k(b)` over the image (a cascade of Gaussians).
fn band_dots(a: &[f32], b: &[f32], w: usize, h: usize, sig: &[f32; BANDS + 1]) -> [f64; BANDS] {
    let (mut pa, mut pb) = (a.to_vec(), b.to_vec());
    let mut out = [0.0f64; BANDS];
    for (k, o) in out.iter_mut().enumerate() {
        let s = step(sig, k);
        let (ca, cb) = (
            self_flat::gaussian(&pa, w, h, s),
            self_flat::gaussian(&pb, w, h, s),
        );
        *o = pa
            .par_iter()
            .zip(&ca)
            .zip(pb.par_iter().zip(&cb))
            .map(|((x, cx), (y, cy))| f64::from(x - cx) * f64::from(y - cy))
            .sum();
        (pa, pb) = (ca, cb);
    }
    out
}

/// `sum_k g_k B_k(f) + G_last(e)`.
fn calibrated(
    f: Vec<f32>,
    e: Vec<f32>,
    w: usize,
    h: usize,
    sig: &[f32; BANDS + 1],
    gains: &[f32; BANDS],
) -> Vec<f32> {
    let mut out = vec![0.0f32; f.len()];
    let mut pf = f;
    for (k, g) in gains.iter().enumerate() {
        let cf = self_flat::gaussian(&pf, w, h, step(sig, k));
        out.par_iter_mut()
            .zip(pf.par_iter().zip(&cf))
            .for_each(|(o, (a, b))| *o += g * (a - b));
        pf = cf;
    }
    let mut pe = e;
    for k in 0..BANDS {
        pe = self_flat::gaussian(&pe, w, h, step(sig, k));
    }
    out.par_iter_mut().zip(&pe).for_each(|(o, v)| *o += v);
    out
}

/// Pass 2, at the write: replace the fusion's `planes` and its halves by the
/// calibrated combination with the kept election.
pub(super) fn combine(planes: &mut [Vec<f32>], w: usize, h: usize) -> Result<()> {
    let started = Instant::now();
    let kept = KEPT
        .lock()
        .unwrap_or_else(|e| e.into_inner())
        .take()
        .context("calibrated fusion: no election planes were kept")?;
    let n = planes.len();
    ensure!(
        kept.full.len() == n
            && kept.halves.iter().all(|hv| hv.len() == n)
            && kept.full.iter().all(|p| p.len() == w * h)
            && planes.iter().all(|p| p.len() == w * h),
        "calibrated fusion: the election's planes do not match the fusion's"
    );
    let mut fh = take_pass_halves().with_context(|| {
        format!(
            "{}=calibrated: the fusion pass kept no half-stacks (a half folded no frames?)",
            depth_guide::ENV
        )
    })?;
    ensure!(
        fh.iter()
            .all(|hv| hv.len() == n && hv.iter().all(|p| p.len() == w * h)),
        "calibrated fusion: the fusion's half-stacks do not match its planes"
    );
    let units = units(n, w, h);
    // Per channel and band: the election's signal power and the fusion's
    // cross-power with the election's other half, both pairings.
    let mut num = [[0.0f64; BANDS]; 3];
    let mut den = [[0.0f64; BANDS]; 3];
    for &(unit, c, uw, uh, sig) in &units {
        let ea = extract(&kept.halves[0], unit, w, h);
        let eb = extract(&kept.halves[1], unit, w, h);
        let ee = band_dots(&ea, &eb, uw, uh, &sig);
        let fa = extract(&fh[0], unit, w, h);
        let fe = band_dots(&fa, &eb, uw, uh, &sig);
        drop(fa);
        let fb = extract(&fh[1], unit, w, h);
        let ef = band_dots(&fb, &ea, uw, uh, &sig);
        for k in 0..BANDS {
            num[c][k] += ee[k];
            den[c][k] += 0.5 * (fe[k] + ef[k]);
        }
    }
    let mut refused = Vec::new();
    let gains: [[f32; BANDS]; 3] = std::array::from_fn(|c| {
        std::array::from_fn(|k| {
            let g = num[c][k] / den[c][k];
            if g.is_finite() && (GAIN_RANGE.0..=GAIN_RANGE.1).contains(&g) {
                g as f32
            } else {
                refused.push(format!("{} band {k} ({g:.3})", ["R", "G", "B"][c]));
                1.0
            }
        })
    });
    for &(unit, c, uw, uh, sig) in &units {
        let f = extract(planes, unit, w, h);
        let e = extract(&kept.full, unit, w, h);
        store(planes, unit, w, calibrated(f, e, uw, uh, &sig, &gains[c]));
        for (half, e_half) in fh.iter_mut().zip(&kept.halves) {
            let f = extract(half, unit, w, h);
            let e = extract(e_half, unit, w, h);
            store(half, unit, w, calibrated(f, e, uw, uh, &sig, &gains[c]));
        }
    }
    // The restoration measures the calibrated stack (a no-op without it).
    let [even, odd] = fh;
    optical_restore::stash_halves(even, odd);
    let edges: Vec<String> = OUTPUT_SIGMAS
        .windows(2)
        .map(|s| format!("{}-{}", s[0], s[1]))
        .collect();
    eprintln!(
        "fusion          : CALIBRATED -- band gains (fusion to election amplitude, output px {}; {}): \
         R {}, G {}, B {}; coarser than {} output px from the election; {:.1} s",
        edges.join(" / "),
        if n == colour_carry::PLANES {
            "each channel at full resolution"
        } else {
            "each plane on its quad grid"
        },
        fmt_gains(&gains[0]),
        fmt_gains(&gains[1]),
        fmt_gains(&gains[2]),
        OUTPUT_SIGMAS[BANDS],
        started.elapsed().as_secs_f64()
    );
    if !refused.is_empty() {
        eprintln!(
            "                  gains outside {:.1}-{:.1} left at 1: {}",
            GAIN_RANGE.0,
            GAIN_RANGE.1,
            refused.join(", ")
        );
    }
    Ok(())
}

fn fmt_gains(g: &[f32; BANDS]) -> String {
    g.iter()
        .map(|v| format!("{v:.3}"))
        .collect::<Vec<_>>()
        .join("/")
}

#[cfg(test)]
mod tests {
    use super::*;

    /// With unit gains and the election equal to the fusion, the
    /// calibration returns its input; the channel round trip is exact.
    #[test]
    fn unit_gains_reproduce_the_input() {
        let (w, h) = (24usize, 20usize);
        let planes: Vec<Vec<f32>> = (0..colour_carry::PLANES)
            .map(|p| (0..w * h).map(|i| ((i * 31 + p * 7) % 53) as f32).collect())
            .collect();
        for c in 0..3 {
            let img = extract(&planes, Unit::Channel(c), w, h);
            let mut copy = planes.clone();
            store(&mut copy, Unit::Channel(c), w, img.clone());
            assert_eq!(copy, planes);
            let out = calibrated(
                img.clone(),
                img.clone(),
                2 * w,
                2 * h,
                &[0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0],
                &[1.0; BANDS],
            );
            for (a, b) in out.iter().zip(&img) {
                assert!((a - b).abs() < 1e-3, "{a} vs {b}");
            }
        }
    }
}
