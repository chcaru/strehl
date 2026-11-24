//! White placement from the subject (plan S4 and X6, ledger row
//! `shd-d-detail-2026-11-24`).
//!
//! The writer's tone ([`super::Tone`]) puts the frame's 99.9th percentile of
//! luminance at 0.90. On a subject with glints that percentile is the glints:
//! they set white and the body renders dark (the A7CR scarab). When the
//! capture records its subject (`manifest.json` `plan.subject`, rings
//! normalised to the sensor's active area), or one is given (`stack
//! --subject <json>`, [`ENV`]), white is placed on the subject's diffuse level
//! instead:
//!
//! * the samples: each output quad's native-site triple (as the frame's tone
//!   measures it), developed through the colour matrix, its brightest colour;
//!   the quads whose centre lies inside the outline;
//! * highlights set aside, two kinds:
//!   - pinned: a quad with any camera colour at or above [`PIN_NEAR`] of the
//!     sensor's saturation ceiling ([`strehl_core::color::Render::ceiling`]),
//!     and every quad within [`PIN_REACH`] of one (the merge blends a
//!     blown reflection's edge with unpinned samples, below the ceiling). A
//!     clipped sample is not a measurement of anything, least of all the
//!     body; on the A7CR scarab its broad sheen is pinned over 0.28 % of the
//!     subject and set white on its own;
//!   - compact glints: a sample brighter than [`HIGHLIGHT_RATIO`] times its
//!     neighbourhood's diffuse level, the largest [`BLOCK_PCT`]th percentile
//!     of the blocks of [`BLOCK`] quads around it (3 x 3 blocks). Glints are
//!     a few photosites across, far less than a quarter of a block, so they
//!     cannot raise a block's level;
//! * the diffuse top, the [`SUBJECT_PCT`]th percentile of what remains, is
//!   placed at [`SUBJECT_WHITE_TARGET`], and a shoulder from
//!   [`SHOULDER_KNEE`] ([`strehl_edit::highlight_shoulder`]) rolls the glints
//!   off below one instead of clipping them.
//!
//! The black point is the frame's, as before. Without a subject nothing here
//! runs and the render is byte for byte what it was.
use anyhow::{Context, Result, ensure};
use rayon::prelude::*;
use std::cell::RefCell;
use std::path::Path;

use super::Tone;

/// `stack --subject <json>` publishes its file here; `off` keeps a capture's
/// recorded subject out of the tone.
pub(crate) const ENV: &str = "STREHL_SUBJECT";
/// Where the subject's diffuse top lands, placed linear (plan X2's body rule
/// places the same statistic at 0.8 for exposure; 0.85 leaves the shoulder
/// a little more room than the frame rule's 0.90).
pub(crate) const SUBJECT_WHITE_TARGET: f32 = 0.85;
/// Where the highlight shoulder begins, placed linear: just below the diffuse
/// top, so the diffuse range is placed exactly as the frame rule places
/// tones and only the top few hundredths ease into the roll-off.
pub(crate) const SHOULDER_KNEE: f32 = 0.80;
/// The diffuse top's percentile of the subject's brightest colour.
pub(crate) const SUBJECT_PCT: f64 = 99.9;
/// A sample above this multiple of its neighbourhood's diffuse level is a
/// highlight (specular), not body.
pub(crate) const HIGHLIGHT_RATIO: f32 = 2.0;
/// Side of a neighbourhood block, quads (32 photosites).
pub(crate) const BLOCK: usize = 16;
/// A block's diffuse level: this percentile of its subject samples' brightest
/// colour.
pub(crate) const BLOCK_PCT: f64 = 75.0;
/// A camera colour at or above this fraction of its saturation ceiling marks
/// its quad pinned.
pub(crate) const PIN_NEAR: f32 = 0.95;
/// Quads within this many of a pinned one are set aside with it (8
/// photosites, about the restoration's own highlight guard).
pub(crate) const PIN_REACH: usize = 4;
/// Fewer subject quads than this and the frame rule stands.
const MIN_QUADS: usize = 4096;

/// Whether a camera-RGB triple (white-balanced, normalised, before the
/// matrix) has a colour at or near the sensor's saturation ceiling.
pub(crate) fn near_pin(v: [f32; 3], render: Option<&strehl_core::color::Render>) -> bool {
    render.is_some_and(|r| {
        let c = r.ceiling();
        (0..3).any(|i| c[i].is_finite() && v[i] >= PIN_NEAR * c[i])
    })
}

/// `mask` dilated by `r` (square), on a `w x h` grid.
fn dilate(mask: &[bool], w: usize, h: usize, r: usize) -> Vec<bool> {
    if r == 0 {
        return mask.to_vec();
    }
    let rows: Vec<bool> = (0..h)
        .into_par_iter()
        .flat_map_iter(|y| {
            let row = &mask[y * w..(y + 1) * w];
            (0..w).map(move |x| row[x.saturating_sub(r)..(x + r + 1).min(w)].contains(&true))
        })
        .collect();
    (0..w * h)
        .into_par_iter()
        .map(|i| {
            let (x, y) = (i % w, i / w);
            (y.saturating_sub(r)..(y + r + 1).min(h)).any(|yy| rows[yy * w + x])
        })
        .collect()
}

#[derive(Clone, Debug)]
pub(crate) struct Subject {
    pub rings: Vec<Vec<[f32; 2]>>,
    /// Where it came from, for the log.
    pub source: String,
    /// The output's rectangle in the active area, normalised (x, y, width,
    /// height); the whole area unless the render crops.
    pub crop: [f64; 4],
}

thread_local! {
    static SUBJECT: RefCell<Option<Subject>> = const { RefCell::new(None) };
}

/// Clears the subject when the render ends.
pub(crate) struct Active;

impl Drop for Active {
    fn drop(&mut self) {
        SUBJECT.with(|s| *s.borrow_mut() = None);
    }
}

/// The subject's rings from a JSON document: `strehl subject --json` output
/// or a `Subject` (`rings` at the top), or a capture manifest
/// (`plan.subject.rings`). `None` when it records none.
pub(crate) fn rings_from_json(v: &serde_json::Value) -> Result<Option<Vec<Vec<[f32; 2]>>>> {
    let rings = match v.get("rings") {
        Some(r) => r,
        None => match v.get("plan").and_then(|p| p.get("subject")) {
            Some(s) if !s.is_null() => s.get("rings").context("plan.subject has no rings")?,
            _ => return Ok(None),
        },
    };
    let rings: Vec<Vec<[f32; 2]>> =
        serde_json::from_value(rings.clone()).context("the subject's rings")?;
    if rings.is_empty() {
        return Ok(None);
    }
    ensure!(
        rings.len() <= 64,
        "a subject has at most 64 rings, not {}",
        rings.len()
    );
    for ring in &rings {
        ensure!(
            (3..=256).contains(&ring.len()),
            "a subject's ring has 3 to 256 points, not {}",
            ring.len()
        );
        ensure!(
            ring.iter()
                .flatten()
                .all(|v| v.is_finite() && (-0.001..=1.001).contains(v)),
            "a subject's points lie within the frame (0..1)"
        );
    }
    Ok(Some(rings))
}

/// Set this render's subject: [`ENV`] (a file, or `off`), else the capture
/// folder's `manifest.json` `plan.subject`. Says which on stderr. `None` when
/// there is none: the tone is the frame rule's, unchanged.
pub(crate) fn activate(dir: &Path) -> Result<Option<Active>> {
    let given = match std::env::var(ENV) {
        Err(std::env::VarError::NotPresent) => None,
        Err(e) => return Err(e).context(ENV),
        Ok(v) if v.trim().is_empty() => None,
        Ok(v) => Some(v),
    };
    let (value, source) = match given.as_deref() {
        Some("off") => {
            eprintln!(
                "tone subject    : off ({ENV}=off / --subject off); white from the frame's 99.9th percentile"
            );
            return Ok(None);
        }
        Some(path) => {
            let text = std::fs::read_to_string(path)
                .with_context(|| format!("reading the subject {path}"))?;
            let v: serde_json::Value = serde_json::from_str(&text)
                .with_context(|| format!("parsing the subject {path}"))?;
            (v, format!("given ({path})"))
        }
        None => {
            let manifest = dir.join("manifest.json");
            let Ok(text) = std::fs::read_to_string(&manifest) else {
                return Ok(None);
            };
            let Ok(v) = serde_json::from_str::<serde_json::Value>(&text) else {
                return Ok(None);
            };
            (v, "the capture's manifest (plan.subject)".to_string())
        }
    };
    let rings = match rings_from_json(&value) {
        Ok(Some(r)) => r,
        Ok(None) if given.is_some() => anyhow::bail!("{source} records no subject rings"),
        Ok(None) => return Ok(None),
        Err(e) if given.is_some() => return Err(e),
        Err(e) => {
            eprintln!(
                "tone subject    : the manifest's subject is unusable ({e:#}); white from the frame"
            );
            return Ok(None);
        }
    };
    eprintln!(
        "tone subject    : {} ring(s) from {source}; white will be placed on the subject's diffuse level",
        rings.len()
    );
    SUBJECT.with(|s| {
        *s.borrow_mut() = Some(Subject {
            rings,
            source,
            crop: [0.0, 0.0, 1.0, 1.0],
        })
    });
    Ok(Some(Active))
}

/// The output covers `rect` (x, y, width, height) of a `full` plane: map the
/// active-area outline into it. Nothing without a subject.
pub(crate) fn set_crop(full: (usize, usize), rect: (usize, usize, usize, usize)) {
    SUBJECT.with(|s| {
        if let Some(s) = s.borrow_mut().as_mut() {
            let (fw, fh) = (full.0.max(1) as f64, full.1.max(1) as f64);
            s.crop = [
                rect.0 as f64 / fw,
                rect.1 as f64 / fh,
                rect.2 as f64 / fw,
                rect.3 as f64 / fh,
            ];
        }
    });
}

/// Whether this render has a subject for its tone.
pub(crate) fn active() -> bool {
    SUBJECT.with(|s| s.borrow().is_some())
}

fn percentile(v: &mut [f32], pct: f64) -> f32 {
    let i = (((pct / 100.0) * (v.len() - 1) as f64).round() as usize).min(v.len() - 1);
    *v.select_nth_unstable_by(i, f32::total_cmp).1
}

/// What [`measure`] found.
#[derive(Clone, Debug, PartialEq)]
pub(crate) struct Diffuse {
    /// Subject quads, and their share of the frame.
    pub quads: usize,
    pub share: f64,
    /// Subject quads set aside as highlights, all told and as pinned (or
    /// next to a pinned quad).
    pub highlights: usize,
    pub pinned: usize,
    /// The diffuse top: the kept samples' [`SUBJECT_PCT`]th percentile of the
    /// brightest colour, developed linear.
    pub top: f32,
    /// The subject's median luminance (BT.709), developed linear.
    pub median_luminance: f32,
}

/// Measure the subject's diffuse top on a `qw x qh` quad grid; `quad(x, y)`
/// is the quad's developed linear triple and whether it is pinned
/// ([`near_pin`]); `inside` the subject's quads.
pub(crate) fn measure(
    qw: usize,
    qh: usize,
    inside: &[bool],
    quad: impl Fn(usize, usize) -> ([f32; 3], bool) + Sync,
) -> Option<Diffuse> {
    assert_eq!(inside.len(), qw * qh);
    let quads = inside.iter().filter(|v| **v).count();
    if quads < MIN_QUADS {
        return None;
    }
    // Brightest colour and luminance of every subject quad (NaN outside),
    // and the pinned quads anywhere within reach of the subject.
    let near: Vec<bool> = dilate(inside, qw, qh, PIN_REACH);
    let ((bright, lum), pinned): ((Vec<f32>, Vec<f32>), Vec<bool>) = (0..qw * qh)
        .into_par_iter()
        .map(|i| {
            if !near[i] {
                return ((f32::NAN, f32::NAN), false);
            }
            let (v, pin) = quad(i % qw, i / qw);
            if !inside[i] {
                return ((f32::NAN, f32::NAN), pin);
            }
            (
                (
                    v[0].max(v[1]).max(v[2]),
                    0.2126 * v[0] + 0.7152 * v[1] + 0.0722 * v[2],
                ),
                pin,
            )
        })
        .unzip();
    let pinned = dilate(&pinned, qw, qh, PIN_REACH);
    // Each block's diffuse level.
    let (bw, bh) = (qw.div_ceil(BLOCK), qh.div_ceil(BLOCK));
    let level: Vec<f32> = (0..bw * bh)
        .into_par_iter()
        .map(|b| {
            let (bx, by) = (b % bw, b / bw);
            let mut v: Vec<f32> = Vec::with_capacity(BLOCK * BLOCK);
            for y in by * BLOCK..((by + 1) * BLOCK).min(qh) {
                for x in bx * BLOCK..((bx + 1) * BLOCK).min(qw) {
                    let m = bright[y * qw + x];
                    if !m.is_nan() {
                        v.push(m);
                    }
                }
            }
            if v.len() * 4 < BLOCK * BLOCK {
                f32::NAN
            } else {
                percentile(&mut v, BLOCK_PCT)
            }
        })
        .collect();
    // The largest level in the 3 x 3 blocks around each block.
    let local: Vec<f32> = (0..bw * bh)
        .into_par_iter()
        .map(|b| {
            let (bx, by) = (b % bw, b / bw);
            let mut best = f32::NAN;
            for y in by.saturating_sub(1)..(by + 2).min(bh) {
                for x in bx.saturating_sub(1)..(bx + 2).min(bw) {
                    let l = level[y * bw + x];
                    if !l.is_nan() && (best.is_nan() || l > best) {
                        best = l;
                    }
                }
            }
            best
        })
        .collect();
    let mut kept: Vec<f32> = Vec::with_capacity(quads);
    let (mut highlights, mut pinned_count) = (0usize, 0usize);
    for (i, &m) in bright.iter().enumerate() {
        if m.is_nan() {
            continue;
        }
        let l = local[(i / qw / BLOCK) * bw + (i % qw) / BLOCK];
        if pinned[i] {
            highlights += 1;
            pinned_count += 1;
        } else if !l.is_nan() && m > HIGHLIGHT_RATIO * l.max(0.0) {
            highlights += 1;
        } else {
            kept.push(m);
        }
    }
    if kept.len() < MIN_QUADS {
        return None;
    }
    let top = percentile(&mut kept, SUBJECT_PCT);
    let mut l: Vec<f32> = lum.into_iter().filter(|v| !v.is_nan()).collect();
    let median_luminance = percentile(&mut l, 50.0);
    Some(Diffuse {
        quads,
        share: quads as f64 / (qw * qh) as f64,
        highlights,
        pinned: pinned_count,
        top,
        median_luminance,
    })
}

/// The subject's quads on a `qw x qh` quad grid covering the crop.
fn raster(s: &Subject, qw: usize, qh: usize) -> Vec<bool> {
    let [x0, y0, w, h] = s.crop;
    let rings: Vec<Vec<[f32; 2]>> = s
        .rings
        .iter()
        .map(|r| {
            r.iter()
                .map(|p| {
                    [
                        ((f64::from(p[0]) - x0) / w) as f32,
                        ((f64::from(p[1]) - y0) / h) as f32,
                    ]
                })
                .collect()
        })
        .collect();
    strehl_core::subject::rasterize(&rings, qw, qh, [1.0 / qw as f64, 1.0 / qh as f64])
}

/// `tone` with white on the subject's diffuse level and the shoulder, when
/// this render has a subject; else `tone` unchanged. `quad(x, y)` is the
/// developed linear triple of quad `(x, y)` of the `qw x qh` grid the tone
/// was measured on, and whether it is pinned ([`near_pin`]).
pub(crate) fn place(
    tone: Tone,
    qw: usize,
    qh: usize,
    quad: impl Fn(usize, usize) -> ([f32; 3], bool) + Sync,
) -> Tone {
    let Some(subject) = SUBJECT.with(|s| s.borrow().clone()) else {
        return tone;
    };
    let inside = raster(&subject, qw, qh);
    let Some(d) = measure(qw, qh, &inside, quad) else {
        eprintln!(
            "tone subject    : too few subject samples inside the outline from {}; white from the frame's 99.9th percentile",
            subject.source
        );
        return tone;
    };
    let placed = placed_tone(tone, d.top);
    let at = |t: &Tone, l: f32| (l - t.black) / (t.white - t.black);
    eprintln!(
        "tone subject    : subject {:.1} % of the frame ({} quads, from {}); {:.3} % of it set aside as \
         highlights ({:.3} % pinned: a colour at {PIN_NEAR} of saturation or within {PIN_REACH} quads \
         of one; the rest brighter than {HIGHLIGHT_RATIO} x the local diffuse level, the \
         {BLOCK_PCT}th percentile of {BLOCK}-quad blocks, 3 x 3 around); diffuse top \
         (p{SUBJECT_PCT} of the brightest colour) {:.5} -> {SUBJECT_WHITE_TARGET}; white {:.5} -> \
         {:.5} ({:+.2} stops); subject median luminance {:.5}, placed {:.3} -> {:.3}; shoulder from \
         {SHOULDER_KNEE}",
        100.0 * d.share,
        d.quads,
        subject.source,
        100.0 * d.highlights as f64 / d.quads as f64,
        100.0 * d.pinned as f64 / d.quads as f64,
        d.top,
        tone.white,
        placed.white,
        -((placed.white - placed.black) / (tone.white - tone.black)).log2(),
        d.median_luminance,
        at(&tone, d.median_luminance),
        at(&placed, d.median_luminance),
    );
    placed
}

/// `tone` with the diffuse top `top` placed at [`SUBJECT_WHITE_TARGET`] (from
/// the same effective black, as the frame rule does) and the shoulder on.
pub(crate) fn placed_tone(tone: Tone, top: f32) -> Tone {
    Tone {
        white: tone.black + (top - tone.black).max(1e-4) / SUBJECT_WHITE_TARGET,
        shoulder: Some(SHOULDER_KNEE),
        ..tone
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    /// A body of level 0.2 with texture to 0.3 and sparse glints at 20 x:
    /// the glints are set aside and the diffuse top is the body's.
    #[test]
    fn glints_are_set_aside_and_the_body_sets_white() {
        let (qw, qh) = (400usize, 300usize);
        let inside: Vec<bool> = (0..qw * qh)
            .map(|i| {
                let (x, y) = ((i % qw) as f64, (i / qw) as f64);
                ((x - 200.0) / 150.0).powi(2) + ((y - 150.0) / 110.0).powi(2) < 1.0
            })
            .collect();
        let body = |x: usize, y: usize| -> [f32; 3] {
            if (x * 7 + y * 13).is_multiple_of(997) {
                return [6.0, 5.0, 4.0];
            }
            let t = 0.2 + 0.1 * (((x * 31 + y * 17) % 100) as f32 / 100.0);
            [t * 0.8, t, t * 0.6]
        };
        let d = measure(qw, qh, &inside, |x, y| (body(x, y), false)).expect("a subject");
        assert!(d.highlights > 0 && d.pinned == 0);
        assert!(d.top <= 0.3 && d.top > 0.29, "{}", d.top);
        // Without the outline's set-aside the glints would set it.
        let mut all: Vec<f32> = (0..qw * qh)
            .filter(|&i| inside[i])
            .map(|i| {
                let v = body(i % qw, i / qw);
                v[0].max(v[1]).max(v[2])
            })
            .collect();
        assert!(percentile(&mut all, SUBJECT_PCT) > 1.0);
        // A broad pinned sheen (a band 30 quads tall, 2 % of the subject or
        // more) is too large for the local rule; pinned, it is set aside
        // with a rim of PIN_REACH quads (its blended edge, below the pin).
        let sheen = |y: usize| (140..170).contains(&y);
        let rim = |y: usize| (140 - PIN_REACH..170 + PIN_REACH).contains(&y);
        let with_sheen = |x: usize, y: usize| -> ([f32; 3], bool) {
            if sheen(y) {
                ([1.0; 3], true)
            } else if rim(y) {
                ([0.7; 3], false)
            } else {
                (body(x, y), false)
            }
        };
        let s = measure(qw, qh, &inside, with_sheen).expect("a subject");
        assert!(s.top <= 0.3, "{}", s.top);
        assert!(s.pinned > 0);
        // Unmarked, the same sheen sets the diffuse top.
        let unmarked = measure(qw, qh, &inside, |x, y| (with_sheen(x, y).0, false)).unwrap();
        assert!(unmarked.top >= 0.7, "{}", unmarked.top);
        let base = Tone {
            black: 0.001,
            white: 6.0,
            contrast: 0.55,
            shoulder: None,
        };
        let t = placed_tone(base, d.top);
        assert!(((d.top - t.black) / (t.white - t.black) - SUBJECT_WHITE_TARGET).abs() < 1e-6);
        assert_eq!(t.shoulder, Some(SHOULDER_KNEE));
    }

    /// Too small an outline leaves the frame rule.
    #[test]
    fn a_tiny_subject_is_refused() {
        let inside = vec![false; 100 * 100];
        assert!(measure(100, 100, &inside, |_, _| ([0.5; 3], false)).is_none());
    }

    /// The JSON forms: `strehl subject --json` / a Subject, and a manifest.
    #[test]
    fn rings_are_read_from_either_form() {
        let ring = serde_json::json!([[[0.1, 0.1], [0.9, 0.1], [0.5, 0.9]]]);
        let direct = serde_json::json!({"rings": ring, "cell_px": 8});
        let manifest = serde_json::json!({"plan": {"start": 1, "subject": {"rings": ring}}});
        let none = serde_json::json!({"plan": {"start": 1}});
        assert_eq!(rings_from_json(&direct).unwrap().unwrap().len(), 1);
        assert_eq!(rings_from_json(&manifest).unwrap().unwrap()[0].len(), 3);
        assert!(rings_from_json(&none).unwrap().is_none());
        let bad = serde_json::json!({"rings": [[[0.1, 0.1], [2.0, 0.1], [0.5, 0.9]]]});
        assert!(rings_from_json(&bad).is_err());
    }

    /// The shoulder: identity to the knee, continuous and below one above it,
    /// chromaticity kept.
    #[test]
    fn the_shoulder_rolls_off_without_clipping() {
        let k = SHOULDER_KNEE;
        assert_eq!(
            strehl_edit::highlight_shoulder([0.5, 0.79, 0.2], k),
            [0.5, 0.79, 0.2]
        );
        let just = strehl_edit::highlight_shoulder([0.0, k + 1e-4, 0.0], k)[1];
        assert!((just - (k + 1e-4)).abs() < 1e-5);
        let mut last = 0.0;
        for m in [0.85f32, 1.0, 1.5, 2.0] {
            let v = strehl_edit::highlight_shoulder([m * 0.5, m, m * 0.25], k);
            assert!(v[1] < 1.0 && v[1] > last, "{m}: {v:?}");
            assert!((v[0] / v[1] - 0.5).abs() < 1e-6 && (v[2] / v[1] - 0.25).abs() < 1e-6);
            last = v[1];
        }
        assert!(strehl_edit::highlight_shoulder([30.0; 3], k)[0] <= 1.0);
    }
}
