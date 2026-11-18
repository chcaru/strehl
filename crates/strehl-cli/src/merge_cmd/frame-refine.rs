//! A second registration pass over the gathered frames
//! (`STREHL_REFINE_FRAMES`; proposal item 10): off by default.
//!
//! # Why
//!
//! On the A7CR scarab four-shot run, gathered frames one plane apart sat
//! 0.13 px rms from each other on in-focus content, four apart 0.32-0.48 px,
//! eight apart 0.44-1.1 px; one similarity per frame pair removed nearly all
//! of it, and its scale grew by about 10 ppm per plane against a
//! magnification step of 124 ppm (the alignment's step about 8 % short;
//! `experiments/a7cr-fourshot-quality-2026-11-16/results-round2.md` R3). The
//! election reads one frame's content and loses nothing by it; a fusion that
//! averages neighbouring frames loses 4-8 % of fine amplitude (DERIVED).
//!
//! # How
//!
//! Every placed frame is gathered as the fold gathers it, and its green luma
//! kept for the next [`MAX_LAG`] frames. Each frame is measured against the
//! frames [`MIN_LAG`] to [`MAX_LAG`] planes before it with the lateral-colour
//! refinement's instrument (`strehl_core::ca_refine::measure`: per 256 px
//! tile with structure, the shift of the gradient magnitude by
//! cross-correlation; a trimmed fit of translation plus scale about the
//! centre). Every pair's scale and translation, divided by its distance in
//! planes, estimates one per-plane rate (weighted mean after trimming beyond
//! three MADs); frame `k` is corrected by `(k - reference)` times the rates,
//! the alignment's reference frame fixed. The gather then pulls each frame
//! through its placement composed with that displacement.
//!
//! Why one rate, not one residual per frame: round 2 found the residual
//! linear in plane distance (a magnification step about 8 % short), and a
//! first version that solved a free residual per frame from pairs two to four
//! planes apart integrated each pair's small bias into a drift (corrections
//! up to 2 400 ppm and 2.9 px rms on the scarab), as any chain of short
//! edges does.
//!
//! Measured per stack, never carried between scenes: this residual is a
//! fitted shrinkage, which the engineering rules forbid transferring.
//!
//! `placebo` applies each frame's displacement reversed (a control arm).
use super::*;
use std::sync::RwLock;
use strehl_core::align::{Cx, Similarity};

pub(super) const ENV: &str = "STREHL_REFINE_FRAMES";
/// Experiment hook: write every measured pair (earlier, later, scale,
/// translation x, y, weight) here as JSON. Changes no render.
pub(super) const DUMP_ENV: &str = "STREHL_REFINE_FRAMES_DUMP";
/// Pairs from this many planes apart...
const MIN_LAG: usize = 2;
/// ...to this many.
const MAX_LAG: usize = 4;

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
enum Mode {
    Off,
    On,
    Placebo,
}

fn mode() -> Result<Mode> {
    match std::env::var(ENV) {
        Err(std::env::VarError::NotPresent) => Ok(Mode::Off),
        Err(e) => Err(e).context(ENV),
        Ok(v) => match v.trim() {
            "" | "0" | "off" => Ok(Mode::Off),
            "1" | "on" => Ok(Mode::On),
            "placebo" => Ok(Mode::Placebo),
            other => anyhow::bail!("{ENV}={other:?} is not off, on or placebo"),
        },
    }
}

/// One measured pair: earlier frame, later frame, scale minus one,
/// translation x and y (plane px), weight.
type PairFit = (usize, usize, f64, f64, f64, f64);

/// Per frame: scale minus one, and translation (plane px), of the pull
/// correction about the full plane's centre.
static CORRECTION: RwLock<Option<Vec<(f64, f64, f64)>>> = RwLock::new(None);

/// `t` composed with frame `index`'s correction, or `t` itself.
pub(super) fn adjust(index: usize, t: Similarity) -> Similarity {
    let guard = CORRECTION.read().unwrap_or_else(|e| e.into_inner());
    let Some(c) = guard.as_ref().and_then(|v| v.get(index)) else {
        return t;
    };
    let (s, tx, ty) = *c;
    // t(C(z)) with C(z) = (1 + s) z + tau: a' = a (1 + s), b' = a tau + b.
    let k = 1.0 + s;
    Similarity {
        a: Cx::new(t.a.re * k, t.a.im * k),
        b: Cx::new(
            t.a.re * tx - t.a.im * ty + t.b.re,
            t.a.re * ty + t.a.im * tx + t.b.im,
        ),
    }
}

/// Clears the correction when the render ends, however it ends.
pub(super) struct Installed;

impl Drop for Installed {
    fn drop(&mut self) {
        *CORRECTION.write().unwrap_or_else(|e| e.into_inner()) = None;
    }
}

/// Measure and install, when `STREHL_REFINE_FRAMES` asks. Prints the
/// measurement.
pub(super) fn install_if_requested(
    source: &impl PyramidFrameSource,
    frames: usize,
    domain: PyramidDomain,
    levels: Levels,
    warps: Option<&WarpMap>,
) -> Result<Option<Installed>> {
    let m = mode()?;
    if m == Mode::Off || ca_refine::preview_active() {
        return Ok(None);
    }
    let Some(map) = warps else {
        eprintln!("frame refine    : NOT APPLIED -- {ENV} set, but the render is not aligned");
        return Ok(None);
    };
    let started = Instant::now();
    let g = domain.analysis();
    let (w, h) = (g.width, g.height);
    let mut scratch = WarpScratch::new(domain.full);
    let mut planes: Vec<Vec<f32>> = (0..BAND_PLANES).map(|_| vec![0.0; g.pixels()]).collect();
    let mut luma = vec![0.0; g.pixels()];
    let mut ring: std::collections::VecDeque<(usize, Vec<f32>)> = Default::default();
    // (earlier, later, scale, tx, ty, weight) per measured pair.
    let mut measured: Vec<PairFit> = Vec::new();
    let mut placed = vec![false; frames];
    for (i, is_placed) in placed.iter_mut().enumerate() {
        let ok = load_frame(
            source,
            i,
            domain,
            levels,
            warps,
            None,
            &mut scratch,
            None,
            &mut planes,
            &mut luma,
        )
        .with_context(|| format!("{ENV}: gathering frame {i}"))?;
        while ring.front().is_some_and(|(k, _)| i - k > MAX_LAG) {
            ring.pop_front();
        }
        if !ok {
            continue;
        }
        *is_placed = true;
        let fits: Vec<(usize, Option<strehl_core::ca_refine::ChannelFit>)> = ring
            .par_iter()
            .filter(|(k, _)| i - k >= MIN_LAG)
            .map(|(k, reference)| {
                // Red is the moving frame, green the earlier one; blue is
                // unused.
                let rgb: Vec<f32> = luma
                    .iter()
                    .zip(reference)
                    .flat_map(|(a, b)| [*a, *b, *a])
                    .collect();
                (
                    *k,
                    strehl_core::ca_refine::measure(w, h, &rgb).map(|r| r.red),
                )
            })
            .collect();
        for (k, fit) in fits {
            if let Some(f) = fit
                && f.kept >= strehl_core::ca_refine::MIN_TILES
                && f.rms > 0.0
            {
                let wgt = f.kept as f64 / (f.rms * f.rms);
                measured.push((k, i, f.scale, f.translation.0, f.translation.1, wgt));
            }
        }
        ring.push_back((i, luma.clone()));
    }
    ensure!(
        !measured.is_empty(),
        "{ENV}: no frame pair carried enough structure to measure"
    );
    if let Ok(path) = std::env::var(DUMP_ENV) {
        let rows: Vec<serde_json::Value> = measured
            .iter()
            .map(|p| serde_json::json!([p.0, p.1, p.2, p.3, p.4, p.5]))
            .collect();
        std::fs::write(&path, serde_json::to_string(&rows)?)?;
    }
    let anchor = map.provenance().reference.min(frames - 1);
    // Per-plane rates: each pair's scale and translation over its distance,
    // combined by a weighted mean after trimming beyond 3 MADs.
    let rate = |pick: fn(&PairFit) -> f64| -> f64 {
        let v: Vec<(f64, f64)> = measured
            .iter()
            .map(|p| (pick(p) / (p.1 - p.0) as f64, p.5))
            .collect();
        let mut xs: Vec<f64> = v.iter().map(|x| x.0).collect();
        xs.sort_by(f64::total_cmp);
        let med = xs[xs.len() / 2];
        let mut dev: Vec<f64> = xs.iter().map(|x| (x - med).abs()).collect();
        dev.sort_by(f64::total_cmp);
        let mad = dev[dev.len() / 2].max(1e-12);
        let (s, w) = v
            .iter()
            .filter(|(x, _)| (x - med).abs() <= 3.0 * mad)
            .fold((0.0, 0.0), |(s, w), (x, wt)| (s + x * wt, w + wt));
        if w > 0.0 { s / w } else { med }
    };
    let (rs, rx, ry) = (rate(|p| p.2), rate(|p| p.3), rate(|p| p.4));
    // The instrument's centre is the analysis plane's; the pull's is the full
    // plane's. `d = tau + s (p - c_a)` is `tau - s delta + s z` about the
    // full plane's centre, `delta = c_a - c_full`.
    let r = domain.rect;
    let (fw, fh) = (domain.full.width as f64, domain.full.height as f64);
    let delta = (
        r.x as f64 + w as f64 * 0.5 - fw * 0.5,
        r.y as f64 + h as f64 * 0.5 - fh * 0.5,
    );
    let sign = if m == Mode::Placebo { -1.0 } else { 1.0 };
    let correction: Vec<(f64, f64, f64)> = (0..frames)
        .map(|k| {
            if !placed[k] {
                return (0.0, 0.0, 0.0);
            }
            let d = k as f64 - anchor as f64;
            let s = rs * d;
            (
                sign * s,
                sign * (rx * d - s * delta.0),
                sign * (ry * d - s * delta.1),
            )
        })
        .collect();
    // Report: the scale per pair by distance (the model is linear in it),
    // and what the per-plane rates leave of the pairs.
    let by_lag: Vec<String> = (MIN_LAG..=MAX_LAG)
        .map(|lag| {
            let mut v: Vec<f64> = measured
                .iter()
                .filter(|p| p.1 - p.0 == lag)
                .map(|p| p.2)
                .collect();
            v.sort_by(f64::total_cmp);
            match v.get(v.len() / 2) {
                Some(m) => format!("{lag}: {:+.1}", m * 1e6),
                None => format!("{lag}: -"),
            }
        })
        .collect();
    let left = (measured
        .iter()
        .map(|p| (p.2 - rs * (p.1 - p.0) as f64).powi(2))
        .sum::<f64>()
        / measured.len() as f64)
        .sqrt();
    eprintln!(
        "frame refine    : {} ({ENV}) -- {} frame pairs {MIN_LAG}-{MAX_LAG} planes apart measured \
         on the gathered green; median pair scale by distance (ppm) {}; per-plane rates scale \
         {:+.2} ppm, translation ({:+.4}, {:+.4}) px, applied as (frame - {anchor}) times the rate \
         (pair scale left {:.1} ppm rms); {:.1} s",
        if m == Mode::Placebo {
            "PLACEBO (corrections reversed)"
        } else {
            "ON"
        },
        measured.len(),
        by_lag.join(", "),
        rs * 1e6,
        rx,
        ry,
        left * 1e6,
        started.elapsed().as_secs_f64()
    );
    *CORRECTION.write().unwrap_or_else(|e| e.into_inner()) = Some(correction);
    Ok(Some(Installed))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn the_correction_composes_before_the_placement() {
        *CORRECTION.write().unwrap() = Some(vec![(1e-3, 0.5, -0.25)]);
        let t = Similarity {
            a: Cx::new(1.01, 0.002),
            b: Cx::new(3.0, -2.0),
        };
        let got = adjust(0, t);
        *CORRECTION.write().unwrap() = None;
        let z = (40.0, -70.0);
        // C(z) = (1 + s) z + tau, then t.
        let c = (1.001 * z.0 + 0.5, 1.001 * z.1 - 0.25);
        let want = (
            t.a.re * c.0 - t.a.im * c.1 + t.b.re,
            t.a.re * c.1 + t.a.im * c.0 + t.b.im,
        );
        let have = (
            got.a.re * z.0 - got.a.im * z.1 + got.b.re,
            got.a.re * z.1 + got.a.im * z.0 + got.b.im,
        );
        assert!((have.0 - want.0).abs() < 1e-9 && (have.1 - want.1).abs() < 1e-9);
    }
}
