//! P43 -- is the deepest mote on the **sensor**, or on the **CPL**?
//!
//! # Why this exists
//!
//! [`defect-flat-census.rs`] proved a mote is really there: a resolved disc at
//! quad `(3434, 2305)`, **-3.483%** below its local background, with the odd and
//! even halves of the capture order agreeing to 0.12 percentage points. That
//! split is a null against **cloud** -- illumination cannot respect an arbitrary
//! partition of capture order, and dust cannot violate one.
//!
//! It is not a null against the **filter**. `BUILD-DEFECT.md:327` wrote the
//! concern down --
//!
//! > "CPL is a rotating element, and the flats were shot ~4.5 h after
//! > `bee-3-cpl`."
//!
//! -- and then the census pooled all 360 frames anyway. Nothing in this lane has
//! ever separated the with-CPL flats from the without-CPL flats, so nothing in
//! this lane has ever established that what it calls a *sensor* defect map is
//! not partly a *filter* defect map. That distinction is not cosmetic:
//!
//! - a mote on the sensor is in every frame this body will ever take;
//! - a mote on the CPL is present only in CPL captures -- **17 of the 26 corpus
//!   stacks** -- and the CPL is a *rotating* element, so its position depends on
//!   filter orientation, which is not recorded anywhere and changes between
//!   sessions. A fixed map coordinate would then be valid only by luck.
//!
//! # The control was already in the data
//!
//! `exiftool` over the 360 flats: ISO 100, f/5.6, 200 mm, one session. The
//! `ExposureTime` tag takes exactly nine values, forty frames each, and sorted
//! by filename it forms exactly **eighteen** constant runs of twenty --
//!
//! ```text
//!   1/250 1/125 1/60 1/30 1/20 1/13 1/10 1/8 1/5     DSC00083..00262
//!   1/250 1/125 1/60 1/30 1/20 1/13 1/10 1/8 1/5     DSC00263..00442
//! ```
//!
//! -- the nine-step ladder run **twice**, exposure-matched step for step. Same
//! paper, same lens, same session, twenty frames per step. The owner's account
//! of the campaign is that the flats were shot twice, with and without the CPL.
//! So the two blocks of 180 are a controlled pair and the filter is the only
//! intended difference between them.
//!
//! **A defect in both blocks is in the fixed optical path. A defect in one block
//! only is on the filter.** That is the whole experiment, and it needed no new
//! capture -- only for someone to notice that the ladder repeats.
//!
//! # This program predicts a null, which is the dangerous case
//!
//! Pre-registered in `experiments/BUILD-DEFECT/PREREG-cpl.txt` before any depth
//! was measured in either block: mote 2 should be in **both** blocks, because a
//! particle at height `z` blurs its shadow by roughly `z / N_eff`, and a 306 um
//! disc with 51 um edges at `N_eff ~ 5.6` puts the particle about **0.29 mm**
//! above the photosites. That is cover glass. A front filter 150-250 mm away
//! would blur by tens of millimetres and would not be a disc at all.
//!
//! A blind instrument returns "no difference" for free. So the null is only
//! reportable if the instrument is first shown to be able to say otherwise, and
//! [`main`] refuses to print a verdict unless all four commissioning arms pass:
//!
//! | arm | plants | requires |
//! |---|---|---|
//! | `G0` | nothing; splits block 1 odd/even | NOT block-specific -- the placebo |
//! | `G1` | -4% disc in block 2 only | block-specific, p at the judging bar |
//! | `G2` | -4% disc in **both** blocks | common, *not* block-specific |
//! | `G3` | divides the **real** mote out of block 2 | `DELTA` moves **positive** |
//!
//! `G2` is what stops `G1` being passed by a statistic that calls everything
//! block-specific. `G3` is the project's required **improvement** arm: a suite
//! of degradations cannot distinguish a metric that is blind to a defect from
//! one that scores the defect better, and this project has shipped exactly that
//! mistake. `G3`'s correct answer has a **sign**, so it is the arm most likely
//! to catch an error of mine.
//!
//! # Planting on the accumulated field is exact, not an approximation
//!
//! Each arm needs the 360 frames re-accumulated with a mask applied. Decoding
//! 360 raw files per arm would be wasteful, and it is unnecessary:
//!
//! ```text
//!   field_b = mean_f( q_f / median(q_f) )
//!   planted: q'_f = q_f * mask
//!   median(q'_f) = median(q_f)      <- mask touches ~200 of 8.25 M quads
//!   => field'_b = mean_f( q_f * mask / median(q_f) ) = mask * field_b
//! ```
//!
//! The equivalence holds only if the mask leaves the frame median alone, so
//! that is **checked numerically** rather than asserted -- see `median shift`
//! in the output. If it ever fails the arms are void and the program says so.
//!
//! # Counting
//!
//! Frames: `examined = used + undecodable + wrong-geometry + rejected-exposure`,
//! reported **per block**, because a CPL costs light and the exposure window
//! will therefore reject asymmetrically -- which is itself evidence about which
//! block wears the filter.
//!
//! Sites: `examined = common + block-specific + undefined + underpowered`.
//! `underpowered` is its own outcome. A site whose null is wider than its own
//! measured `DELTA` decides nothing, and this lane has already been bitten once
//! by an `UNDEFINED` that read as a `PASS`.

use std::collections::BTreeMap;
use std::path::{Path, PathBuf};

/// White paper taped to a window, lens ~9 cm away, mostly-cloudy Seattle
/// daylight, shot twice -- with and without the CPL.
const FLATS: &str = r"D:\personal\macro\flat-fields\flat-fields";

/// First frame of block 2, established by the `ExposureTime` run structure
/// above. Frames sort by filename; everything before this is block 1.
const BLOCK2_FIRST: &str = "DSC00263";

/// Frames per exposure step, from the same EXIF census. Used only to slice the
/// per-step level ratio that labels which block wears the filter.
const STEP_LEN: usize = 20;

/// The nine shutter speeds, in capture order within a block. Recorded from
/// `exiftool`; this program does not read EXIF and does not depend on these
/// values being right for its main result -- they label rows in one table.
const LADDER: [&str; 9] = [
    "1/250", "1/125", "1/60", "1/30", "1/20", "1/13", "1/10", "1/8", "1/5",
];

/// Radius, in quads, of the box mean that estimates the illumination. Same
/// value as the census and as `ValidateParams::hp_radius`, on purpose: two
/// high-passes of different radius do not produce comparable depths.
const BG_RADIUS: usize = 64;

/// Radius, in quads, of the core a site's depth is averaged over. The census
/// integrates the same disc.
const CORE_RADIUS: i64 = 8;

/// Reject a frame whose median quad value is outside this fraction of the range
/// between black and white. Identical to the census.
const EXPOSURE_WINDOW: (f32, f32) = (0.06, 0.90);

/// The sites the shipping embedded map nominates, in quad coordinates.
const MAP_SITES: [(&str, usize, usize); 2] = [("mote 1", 3202, 119), ("mote 2", 3434, 2305)];

/// Border, in quads, excluded from the null and from the discovery search. The
/// census measured this: at a border of 8, **37 of the 40 deepest blobs sat on
/// the frame edge** -- optical falloff and a truncated box mean, not dust.
const SEARCH_BORDER: usize = BG_RADIUS;

/// Decimation of the clean-site grid that forms the `DELTA` null.
const NULL_STEP: usize = 16;

/// A null must have at least this many members or the site is `undefined`.
const MIN_NULL: usize = 200;

/// Discovery floor: an absolute one, in percentage points of `DELTA`. Below
/// this, a one-block-only deficit is not reported however good its p-value.
const DISCOVERY_DELTA_PP: f32 = 1.0;

/// Discovery floor: the rank bar, matching the shipping validator's.
const DISCOVERY_P: f32 = 0.0025;

/// Depth of the synthetic disc planted by `G1` and `G2`, as a fraction.
const PLANT_DEPTH: f32 = 0.04;

/// Radius, in quads, of the planted disc. Matches `CORE_RADIUS` so the planted
/// defect is exactly the size the statistic integrates.
const PLANT_RADIUS: i64 = CORE_RADIUS;

/// Where `G1` and `G2` plant. Fixed coordinates, chosen away from both map
/// sites and from every edge -- and **verified clean before use**, so that a
/// commissioning arm cannot be run on top of a real defect.
const PLANT_SITES: [(&str, usize, usize); 2] =
    [("G1 site", 1760, 1172), ("G2 site", 2600, 800)];

/// A plant site must read flatter than this in the base field, or the program
/// halts. A commissioning arm planted on a real mote proves nothing.
const PLANT_SITE_CLEAN: f32 = 0.005;

fn box_blur(src: &[f32], w: usize, h: usize, r: usize) -> Vec<f32> {
    let mut tmp = vec![0f32; w * h];
    for y in 0..h {
        let row = &src[y * w..y * w + w];
        let mut acc: f32 = row[..(r + 1).min(w)].iter().sum();
        let mut n = (r + 1).min(w);
        for x in 0..w {
            tmp[y * w + x] = acc / n as f32;
            if x >= r {
                acc -= row[x - r];
                n -= 1;
            }
            if x + r + 1 < w {
                acc += row[x + r + 1];
                n += 1;
            }
        }
    }
    let mut out = vec![0f32; w * h];
    for x in 0..w {
        let mut acc: f32 = (0..(r + 1).min(h)).map(|y| tmp[y * w + x]).sum();
        let mut n = (r + 1).min(h);
        for y in 0..h {
            out[y * w + x] = acc / n as f32;
            if y >= r {
                acc -= tmp[(y - r) * w + x];
                n -= 1;
            }
            if y + r + 1 < h {
                acc += tmp[(y + r + 1) * w + x];
                n += 1;
            }
        }
    }
    out
}

fn median_of(v: &[f32]) -> f32 {
    let mut s: Vec<f32> = v.iter().copied().filter(|x| x.is_finite()).collect();
    if s.is_empty() {
        return 0.0;
    }
    s.sort_by(|a, b| a.partial_cmp(b).unwrap());
    s[s.len() / 2]
}

/// Residual = normalised field divided by its own large-radius box mean. Dust
/// is small and sharp; cloud is large and slow; this keeps the first.
fn residual(field: &[f32], w: usize, h: usize) -> Vec<f32> {
    let bg = box_blur(field, w, h, BG_RADIUS);
    field
        .iter()
        .zip(&bg)
        .map(|(f, b)| if *b > 0.0 { f / b } else { 1.0 })
        .collect()
}

/// Mean of `resid` over the `CORE_RADIUS` disc at `(px, py)`, minus one.
/// `None` if the disc leaves the grid -- which is an `undefined` outcome and
/// must never be silently returned as zero.
fn core_depth(resid: &[f32], w: usize, h: usize, px: usize, py: usize) -> Option<f32> {
    let (cx, cy) = (px as i64, py as i64);
    if cx - CORE_RADIUS < 0 || cy - CORE_RADIUS < 0 {
        return None;
    }
    if cx + CORE_RADIUS >= w as i64 || cy + CORE_RADIUS >= h as i64 {
        return None;
    }
    let mut s = 0f64;
    let mut n = 0u32;
    for dy in -CORE_RADIUS..=CORE_RADIUS {
        for dx in -CORE_RADIUS..=CORE_RADIUS {
            if dx * dx + dy * dy > CORE_RADIUS * CORE_RADIUS {
                continue;
            }
            s += resid[(cy + dy) as usize * w + (cx + dx) as usize] as f64;
            n += 1;
        }
    }
    if n == 0 {
        return None;
    }
    Some((s / n as f64) as f32 - 1.0)
}

/// A multiplicative disc, `1.0` everywhere except a `PLANT_RADIUS` core where
/// it is `1.0 - depth`. Applied to a whole block's accumulated field.
fn plant(field: &mut [f32], w: usize, h: usize, px: usize, py: usize, depth: f32) {
    let (cx, cy) = (px as i64, py as i64);
    for dy in -PLANT_RADIUS..=PLANT_RADIUS {
        for dx in -PLANT_RADIUS..=PLANT_RADIUS {
            if dx * dx + dy * dy > PLANT_RADIUS * PLANT_RADIUS {
                continue;
            }
            let (x, y) = (cx + dx, cy + dy);
            if x < 0 || y < 0 || x >= w as i64 || y >= h as i64 {
                continue;
            }
            field[y as usize * w + x as usize] *= 1.0 - depth;
        }
    }
}

/// Every site's `DELTA` is judged against this: the same statistic evaluated on
/// a decimated grid of sites that are far from every edge and from every known
/// mote. It absorbs whatever the two blocks differ by for reasons that are not
/// dust -- a rotated polariser changing the falloff, for instance -- so a leak
/// inflates the null and makes the verdict conservative rather than wrong.
fn delta_null(
    r1: &[f32],
    r2: &[f32],
    w: usize,
    h: usize,
    avoid: &[(usize, usize)],
) -> Vec<f32> {
    let mut out = Vec::new();
    let mut y = SEARCH_BORDER;
    while y < h.saturating_sub(SEARCH_BORDER) {
        let mut x = SEARCH_BORDER;
        while x < w.saturating_sub(SEARCH_BORDER) {
            let near = avoid.iter().any(|(ax, ay)| {
                let (dx, dy) = (x as i64 - *ax as i64, y as i64 - *ay as i64);
                dx * dx + dy * dy < (4 * CORE_RADIUS) * (4 * CORE_RADIUS)
            });
            if !near {
                if let (Some(d1), Some(d2)) = (
                    core_depth(r1, w, h, x, y),
                    core_depth(r2, w, h, x, y),
                ) {
                    out.push(d2 - d1);
                }
            }
            x += NULL_STEP;
        }
        y += NULL_STEP;
    }
    out
}

/// Distance from `(x, y)` to the nearest edge of the quad grid.
fn edge_dist(x: usize, y: usize, w: usize, h: usize) -> usize {
    x.min(y).min(w - 1 - x).min(h - 1 - y)
}

/// A `DELTA` null matched on **distance to the nearest edge**.
///
/// `PREREG-cpl.txt` section 8 raised this against itself: mote 2 sits 39 quads
/// from the bottom edge, and [`SEARCH_BORDER`] is 64, so mote 2 is *inside* the
/// band that [`delta_null`] excludes. An interior null therefore describes the
/// noise somewhere mote 2 is not. Near an edge the background box mean is
/// truncated and the optical falloff is steep, both of which can widen the
/// block-to-block difference -- so an interior null could understate the noise
/// at mote 2 and make its p optimistic.
///
/// The fix is to measure it rather than argue it: sample clean sites at the
/// **same** distance from an edge as the site being judged. Same falloff
/// regime, same truncation, same everything except the dust.
fn delta_null_matched(
    r1: &[f32],
    r2: &[f32],
    w: usize,
    h: usize,
    avoid: &[(usize, usize)],
    target: usize,
    tol: usize,
) -> Vec<f32> {
    let mut out = Vec::new();
    let mut y = CORE_RADIUS as usize + 1;
    while y < h - CORE_RADIUS as usize - 1 {
        let mut x = CORE_RADIUS as usize + 1;
        while x < w - CORE_RADIUS as usize - 1 {
            let d = edge_dist(x, y, w, h);
            if d.abs_diff(target) <= tol {
                let near = avoid.iter().any(|(ax, ay)| {
                    let (dx, dy) = (x as i64 - *ax as i64, y as i64 - *ay as i64);
                    dx * dx + dy * dy < (4 * CORE_RADIUS) * (4 * CORE_RADIUS)
                });
                if !near {
                    if let (Some(a), Some(b)) =
                        (core_depth(r1, w, h, x, y), core_depth(r2, w, h, x, y))
                    {
                        out.push(b - a);
                    }
                }
            }
            x += 4;
        }
        y += 4;
    }
    out
}

/// Two-sided rank of `|d|` in `null`. Returns the fraction of the null at least
/// as extreme, so small means block-specific.
fn rank_p(d: f32, null: &[f32]) -> f32 {
    if null.is_empty() {
        return 1.0;
    }
    let n = null.iter().filter(|x| x.abs() >= d.abs()).count();
    (n as f32 + 1.0) / (null.len() as f32 + 1.0)
}

/// The four outcomes a site can land in. They are an enum rather than a pair of
/// booleans so that `Undefined` cannot be read as `Common`.
#[derive(Clone, Copy, PartialEq, Eq, Debug)]
enum Outcome {
    Common,
    BlockSpecific,
    Underpowered,
    Undefined,
}

fn classify(d1: Option<f32>, d2: Option<f32>, null: &[f32]) -> (Outcome, f32, f32) {
    let (Some(a), Some(b)) = (d1, d2) else {
        return (Outcome::Undefined, f32::NAN, f32::NAN);
    };
    if null.len() < MIN_NULL {
        return (Outcome::Undefined, b - a, f32::NAN);
    }
    let delta = b - a;
    let p = rank_p(delta, null);
    // The null's own spread. If |DELTA| does not clear it, the site decides
    // nothing -- it is not evidence of sameness.
    let mut mag: Vec<f32> = null.iter().map(|x| x.abs()).collect();
    mag.sort_by(|x, y| x.partial_cmp(y).unwrap());
    let p95 = mag[((mag.len() - 1) as f32 * 0.95) as usize];
    if p <= DISCOVERY_P && delta.abs() >= DISCOVERY_DELTA_PP / 100.0 {
        (Outcome::BlockSpecific, delta, p)
    } else if delta.abs() <= p95 {
        (Outcome::Common, delta, p)
    } else {
        (Outcome::Underpowered, delta, p)
    }
}

fn main() {
    let mut frames: Vec<PathBuf> = std::fs::read_dir(Path::new(FLATS))
        .expect("flat-field directory")
        .filter_map(|e| e.ok())
        .map(|e| e.path())
        .filter(|p| {
            p.extension()
                .and_then(|s| s.to_str())
                .is_some_and(|s| s.eq_ignore_ascii_case("arw"))
        })
        .collect();
    frames.sort();

    let examined = frames.len();
    let mut rejected: BTreeMap<String, usize> = BTreeMap::new();
    let mut geom: Option<(usize, usize, usize, usize)> = None;
    // [block][half] -- half is odd/even *within* the block, which is what makes
    // G0 possible without a second decode pass.
    let mut acc: Vec<[f64; 4]> = Vec::new();
    let mut used = [[0usize; 2]; 2];
    let mut rej_block = [0usize; 2];
    // Per-frame level, kept so the CPL labelling gate can slice it by step.
    let mut levels: Vec<(usize, usize, f32)> = Vec::new();
    let mut median_shift: f32 = 0.0;

    for path in frames.iter() {
        let stem = path.file_stem().and_then(|s| s.to_str()).unwrap_or("");
        let block = usize::from(stem >= BLOCK2_FIRST);
        let f = match strehl_raw::decode(path) {
            Ok(f) => f,
            Err(e) => {
                *rejected.entry(format!("undecodable: {e}")).or_default() += 1;
                rej_block[block] += 1;
                continue;
            }
        };
        let a = (f.active.x, f.active.y, f.active.width, f.active.height);
        match geom {
            None => {
                geom = Some(a);
                acc = vec![[0.0; 4]; (a.2 / 2) * (a.3 / 2)];
            }
            Some(g) if g != a => {
                *rejected
                    .entry(format!("geometry {}x{} != first {}x{}", a.2, a.3, g.2, g.3))
                    .or_default() += 1;
                rej_block[block] += 1;
                continue;
            }
            Some(_) => {}
        }
        let (q, qw, qh) = strehl_core::defect_map::quad_mean(&f.data, f.stride, a, f.levels.black);
        let sub: Vec<f32> = (0..qh)
            .step_by(8)
            .flat_map(|y| (0..qw).step_by(8).map(move |x| (y, x)))
            .map(|(y, x)| q[y * qw + x])
            .collect();
        let med = median_of(&sub);
        let range = f.levels.white - f.levels.black;
        let level = if range > 0.0 { med / range } else { 0.0 };

        // The plant-on-the-field equivalence needs median(q * mask) == median(q).
        // Measure it once, on the first used frame, rather than asserting it.
        if median_shift == 0.0 && med > 0.0 {
            let mut probe = q.clone();
            for (_, px, py) in PLANT_SITES {
                plant(&mut probe, qw, qh, px, py, PLANT_DEPTH);
            }
            let sub2: Vec<f32> = (0..qh)
                .step_by(8)
                .flat_map(|y| (0..qw).step_by(8).map(move |x| (y, x)))
                .map(|(y, x)| probe[y * qw + x])
                .collect();
            median_shift = (median_of(&sub2) / med - 1.0).abs();
        }

        if !(EXPOSURE_WINDOW.0..=EXPOSURE_WINDOW.1).contains(&level) {
            *rejected
                .entry(format!(
                    "exposure outside [{:.0}%, {:.0}%]",
                    100.0 * EXPOSURE_WINDOW.0,
                    100.0 * EXPOSURE_WINDOW.1
                ))
                .or_default() += 1;
            rej_block[block] += 1;
            levels.push((block, usize::MAX, level));
            continue;
        }
        let half = used[block][0] + used[block][1];
        let slot = block * 2 + (half % 2);
        for (dst, v) in acc.iter_mut().zip(&q) {
            dst[slot] += (*v / med) as f64;
        }
        used[block][half % 2] += 1;
        levels.push((block, half, level));
    }

    let Some((ax, ay, aw, ah)) = geom else {
        println!("examined {examined}, used 0 -- no frame decoded, nothing measured");
        return;
    };
    let (qw, qh) = (aw / 2, ah / 2);

    println!("== P43 -- sensor or CPL? the flats, split by filter block ==");
    println!("source        : {FLATS}");
    println!("active area   : {aw}x{ah} at ({ax},{ay})  ->  quad grid {qw}x{qh}");
    let u1 = used[0][0] + used[0][1];
    let u2 = used[1][0] + used[1][1];
    println!(
        "frames        : examined {examined} = used {} + rejected {}",
        u1 + u2,
        rejected.values().sum::<usize>()
    );
    println!(
        "  block 1 (..{}) : used {u1:>3} (odd {} / even {})  rejected {}",
        BLOCK2_FIRST, used[0][1], used[0][0], rej_block[0]
    );
    println!(
        "  block 2 ({}..) : used {u2:>3} (odd {} / even {})  rejected {}",
        BLOCK2_FIRST, used[1][1], used[1][0], rej_block[1]
    );
    for (why, n) in &rejected {
        println!("                rejected {n:>4}  {why}");
    }
    println!("plant equivalence: |median shift| = {:.3e}", median_shift);
    if u1 < 16 || u2 < 16 {
        println!("\nHALT: a block has fewer than 16 usable frames; no power. Nothing claimed.");
        return;
    }

    // ---- GATE C1: which block wears the filter ----
    println!("\n-- C1: which block wears the CPL --");
    let mut ratios: Vec<f32> = Vec::new();
    for step in 0..LADDER.len() {
        let lo = step * STEP_LEN;
        let hi = lo + STEP_LEN;
        let mean_of = |b: usize| -> f32 {
            let v: Vec<f32> = levels
                .iter()
                .filter(|(bb, idx, _)| *bb == b && *idx != usize::MAX)
                .map(|(_, _, l)| *l)
                .collect();
            let s: Vec<f32> = v
                .iter()
                .enumerate()
                .filter(|(i, _)| *i >= lo && *i < hi)
                .map(|(_, l)| *l)
                .collect();
            if s.is_empty() {
                f32::NAN
            } else {
                s.iter().sum::<f32>() / s.len() as f32
            }
        };
        // Levels are recorded in capture order per block, but rejected frames
        // are not accumulated, so slice the RAW per-block level list instead.
        let raw: Vec<Vec<f32>> = (0..2)
            .map(|b| {
                levels
                    .iter()
                    .filter(|(bb, _, _)| *bb == b)
                    .map(|(_, _, l)| *l)
                    .collect()
            })
            .collect();
        let seg = |b: usize| -> f32 {
            let v = &raw[b];
            if hi > v.len() {
                return f32::NAN;
            }
            let s = &v[lo..hi];
            s.iter().sum::<f32>() / s.len() as f32
        };
        let (a1, a2) = (seg(0), seg(1));
        let _ = mean_of;
        let r = a2 / a1;
        ratios.push(r);
        println!(
            "  {:>6}   block1 {:7.4}   block2 {:7.4}   ratio {:6.3}   {:+.2} stops",
            LADDER[step],
            a1,
            a2,
            r,
            r.log2()
        );
    }
    let finite: Vec<f32> = ratios.iter().copied().filter(|x| x.is_finite()).collect();
    let all_same_side = finite.iter().all(|r| *r < 1.0) || finite.iter().all(|r| *r > 1.0);
    let logs: Vec<f32> = finite.iter().map(|r| r.log2()).collect();
    let spread = logs.iter().cloned().fold(f32::MIN, f32::max)
        - logs.iter().cloned().fold(f32::MAX, f32::min);
    let mean_stops = logs.iter().sum::<f32>() / logs.len() as f32;
    println!(
        "  C1: {} of {} steps finite, same side {}, spread {:.3} stops, mean {:+.2} stops",
        finite.len(),
        ratios.len(),
        all_same_side,
        spread,
        mean_stops
    );
    let labelled = all_same_side && spread < 0.5 && finite.len() == ratios.len();
    let (n_cpl, n_bare) = if !labelled {
        println!("  C1 FAILS -> blocks reported as 1 and 2; NO filter label claimed.");
        ("block 2", "block 1")
    } else if mean_stops < 0.0 {
        println!("  C1 PASSES -> block 2 is DARKER by {:.2} stops = the CPL block.", -mean_stops);
        ("block 2 (CPL)", "block 1 (bare)")
    } else {
        println!("  C1 PASSES -> block 1 is DARKER by {mean_stops:.2} stops = the CPL block.");
        ("block 1 (CPL)", "block 2 (bare)")
    };

    // ---- fields and residuals ----
    let field = |slots: &[usize], den: usize| -> Vec<f32> {
        acc.iter()
            .map(|c| (slots.iter().map(|s| c[*s]).sum::<f64>() / den as f64) as f32)
            .collect()
    };
    let f1 = field(&[0, 1], u1);
    let f2 = field(&[2, 3], u2);
    let f1_odd = field(&[1], used[0][1]);
    let f1_even = field(&[0], used[0][0]);

    let avoid: Vec<(usize, usize)> = MAP_SITES
        .iter()
        .map(|(_, x, y)| (*x, *y))
        .chain(PLANT_SITES.iter().map(|(_, x, y)| (*x, *y)))
        .collect();

    // Plant sites must be clean before they can commission anything.
    let base1 = residual(&f1, qw, qh);
    let base2 = residual(&f2, qw, qh);
    println!("\n-- plant sites must be clean before they can commission anything --");
    let mut plant_ok = true;
    for (name, px, py) in PLANT_SITES {
        let (d1, d2) = (
            core_depth(&base1, qw, qh, px, py),
            core_depth(&base2, qw, qh, px, py),
        );
        match (d1, d2) {
            (Some(a), Some(b)) => {
                let ok = a.abs() < PLANT_SITE_CLEAN && b.abs() < PLANT_SITE_CLEAN;
                println!(
                    "  {name:8} ({px},{py})  block1 {:+.3}%  block2 {:+.3}%  {}",
                    100.0 * a,
                    100.0 * b,
                    if ok { "clean" } else { "NOT CLEAN" }
                );
                plant_ok &= ok;
            }
            _ => {
                println!("  {name:8} ({px},{py})  UNDEFINED -- core leaves the grid");
                plant_ok = false;
            }
        }
    }
    if !plant_ok {
        println!("\nHALT: a commissioning site is not clean. Arms would prove nothing.");
        return;
    }

    // ---- the commissioning arms ----
    println!("\n-- commissioning: the verdict is VOID unless all four pass --");
    let mut arms_pass = true;

    // G0: block 1 odd vs block 1 even. Cannot differ by filter.
    {
        let ra = residual(&f1_odd, qw, qh);
        let rb = residual(&f1_even, qw, qh);
        let null = delta_null(&ra, &rb, qw, qh, &avoid);
        let (_, px, py) = MAP_SITES[1];
        let (out, d, p) = classify(
            core_depth(&ra, qw, qh, px, py),
            core_depth(&rb, qw, qh, px, py),
            &null,
        );
        let ok = out != Outcome::BlockSpecific;
        arms_pass &= ok;
        println!(
            "  G0 placebo    mote 2, block1 odd vs even   DELTA {:+.3} pp  p {:.4}  {:?}  {}",
            100.0 * d,
            p,
            out,
            if ok { "PASS" } else { "FAIL" }
        );
    }

    // G1: plant a block-specific disc.
    {
        let mut g2f = f2.clone();
        let (_, px, py) = PLANT_SITES[0];
        plant(&mut g2f, qw, qh, px, py, PLANT_DEPTH);
        let rb = residual(&g2f, qw, qh);
        let null = delta_null(&base1, &rb, qw, qh, &avoid);
        let (out, d, p) = classify(
            core_depth(&base1, qw, qh, px, py),
            core_depth(&rb, qw, qh, px, py),
            &null,
        );
        let ok = out == Outcome::BlockSpecific;
        arms_pass &= ok;
        println!(
            "  G1 planted    -{:.0}% in block 2 only        DELTA {:+.3} pp  p {:.4}  {:?}  {}",
            100.0 * PLANT_DEPTH,
            100.0 * d,
            p,
            out,
            if ok { "PASS" } else { "FAIL" }
        );
    }

    // G2: plant the same disc in both blocks.
    {
        let (mut a, mut b) = (f1.clone(), f2.clone());
        let (_, px, py) = PLANT_SITES[1];
        plant(&mut a, qw, qh, px, py, PLANT_DEPTH);
        plant(&mut b, qw, qh, px, py, PLANT_DEPTH);
        let (ra, rb) = (residual(&a, qw, qh), residual(&b, qw, qh));
        let null = delta_null(&ra, &rb, qw, qh, &avoid);
        let (out, d, p) = classify(
            core_depth(&ra, qw, qh, px, py),
            core_depth(&rb, qw, qh, px, py),
            &null,
        );
        let ok = out == Outcome::Common;
        arms_pass &= ok;
        println!(
            "  G2 common     -{:.0}% in BOTH blocks         DELTA {:+.3} pp  p {:.4}  {:?}  {}",
            100.0 * PLANT_DEPTH,
            100.0 * d,
            p,
            out,
            if ok { "PASS" } else { "FAIL" }
        );
    }

    // G3: the improvement arm. Divide the real mote out of block 2 and require
    // DELTA to move POSITIVE. A statistic that only grows under change fails.
    {
        let (_, px, py) = MAP_SITES[1];
        let d2_before = core_depth(&base2, qw, qh, px, py);
        let mut b = f2.clone();
        // Remove the mote by dividing block 2's field by its own residual over
        // the core. That is the measured profile, not a model of it.
        let (cx, cy) = (px as i64, py as i64);
        for dy in -CORE_RADIUS..=CORE_RADIUS {
            for dx in -CORE_RADIUS..=CORE_RADIUS {
                if dx * dx + dy * dy > CORE_RADIUS * CORE_RADIUS {
                    continue;
                }
                let i = (cy + dy) as usize * qw + (cx + dx) as usize;
                let r = base2[i];
                if r > 0.0 {
                    b[i] /= r;
                }
            }
        }
        let rb = residual(&b, qw, qh);
        let null = delta_null(&base1, &rb, qw, qh, &avoid);
        let d_before = core_depth(&base2, qw, qh, px, py).unwrap_or(f32::NAN)
            - core_depth(&base1, qw, qh, px, py).unwrap_or(f32::NAN);
        let (out, d_after, p) = classify(
            core_depth(&base1, qw, qh, px, py),
            core_depth(&rb, qw, qh, px, py),
            &null,
        );
        let moved_positive = d_after > d_before;
        let ok = moved_positive && out == Outcome::BlockSpecific;
        arms_pass &= ok;
        println!(
            "  G3 improved   mote 2 divided out of block 2",
        );
        println!(
            "                block 2 depth {:+.3}% -> {:+.3}%   DELTA {:+.3} -> {:+.3} pp  p {:.4}  {:?}  {}",
            100.0 * d2_before.unwrap_or(f32::NAN),
            100.0 * core_depth(&rb, qw, qh, px, py).unwrap_or(f32::NAN),
            100.0 * d_before,
            100.0 * d_after,
            p,
            out,
            if ok { "PASS" } else { "FAIL" }
        );
    }

    if !arms_pass {
        println!("\nHALT: a commissioning arm failed. No verdict is reported on the real data.");
        return;
    }
    println!("  all four arms PASS -- the discriminator can tell the cases apart.");

    // ---- the real question ----
    let null = delta_null(&base1, &base2, qw, qh, &avoid);
    let mut mag: Vec<f32> = null.iter().map(|x| x.abs()).collect();
    mag.sort_by(|x, y| x.partial_cmp(y).unwrap());
    println!("\n-- the map's sites, block 1 vs block 2 --");
    println!(
        "   DELTA null: n {}   p50 {:.3} pp   p95 {:.3} pp   p99.75 {:.3} pp",
        null.len(),
        100.0 * mag[mag.len() / 2],
        100.0 * mag[((mag.len() - 1) as f32 * 0.95) as usize],
        100.0 * mag[((mag.len() - 1) as f32 * 0.9975) as usize]
    );
    println!(
        "   {:8} {:>10} {:>10} {:>10} {:>8}  {}",
        "site", n_bare, n_cpl, "DELTA", "p", "outcome"
    );
    let mut tally: BTreeMap<String, usize> = BTreeMap::new();
    for (name, px, py) in MAP_SITES {
        let (d1, d2) = (
            core_depth(&base1, qw, qh, px, py),
            core_depth(&base2, qw, qh, px, py),
        );
        let (out, d, p) = classify(d1, d2, &null);
        *tally.entry(format!("{out:?}")).or_default() += 1;
        let fmt = |v: Option<f32>| match v {
            Some(x) => format!("{:+.3}%", 100.0 * x),
            None => "  --  ".to_string(),
        };
        println!(
            "   {:8} {:>10} {:>10} {:>+10.3} {:>8.4}  {:?}",
            name,
            fmt(d1),
            fmt(d2),
            100.0 * d,
            p,
            out
        );
    }
    let total: usize = tally.values().sum();
    println!(
        "   partition: examined {total} = {}",
        tally
            .iter()
            .map(|(k, v)| format!("{v} {k}"))
            .collect::<Vec<_>>()
            .join(" + ")
    );

    // ---- the threat this lane raised against itself, closed by measurement ----
    println!("\n-- edge-matched null: PREREG section 8's threat, measured not argued --");
    println!(
        "   mote 2 is {} quads from the nearest edge; SEARCH_BORDER is {}, so the",
        edge_dist(MAP_SITES[1].1, MAP_SITES[1].2, qw, qh),
        SEARCH_BORDER
    );
    println!("   interior null above describes noise somewhere mote 2 is not.");
    for (name, px, py) in MAP_SITES {
        let target = edge_dist(px, py, qw, qh);
        let mnull = delta_null_matched(&base1, &base2, qw, qh, &avoid, target, 8);
        let (d1, d2) = (
            core_depth(&base1, qw, qh, px, py),
            core_depth(&base2, qw, qh, px, py),
        );
        let (out, d, p) = classify(d1, d2, &mnull);
        if mnull.len() < MIN_NULL {
            println!(
                "   {name:8} edge-dist {target:>4}  matched null n={} < {MIN_NULL} -> UNDEFINED, no claim",
                mnull.len()
            );
            continue;
        }
        let mut mm: Vec<f32> = mnull.iter().map(|x| x.abs()).collect();
        mm.sort_by(|x, y| x.partial_cmp(y).unwrap());
        let mp95 = mm[((mm.len() - 1) as f32 * 0.95) as usize];
        println!(
            "   {name:8} edge-dist {target:>4}  matched null n={:<5} p95 {:.3} pp   DELTA {:+.3} pp  p {:.4}  {:?}",
            mnull.len(),
            100.0 * mp95,
            100.0 * d,
            p,
            out
        );
        // How much of this mote could be on the filter and still hide here?
        // A wholly filter-borne mote would put its entire depth into DELTA.
        let depth = d1.unwrap_or(f32::NAN).abs().max(d2.unwrap_or(f32::NAN).abs());
        if depth > 0.0 {
            println!(
                "            depth {:.3}%; a wholly filter-borne mote would give DELTA {:.3} pp.",
                100.0 * depth,
                100.0 * depth
            );
            println!(
                "            hiding under this null bounds the filter-borne share at <= {:.2}%",
                100.0 * mp95 / depth
            );
        }
    }

    // ---- the discovery arm: filter dust the map does not model ----
    println!("\n-- open search for FILTER-specific dust (present in one block only) --");
    println!(
        "   floors: |DELTA| >= {:.1} pp AND p <= {:.4} AND >= {} quads from every edge",
        DISCOVERY_DELTA_PP, DISCOVERY_P, SEARCH_BORDER
    );
    let bar = mag[((mag.len() as f32 - 1.0) * (1.0 - DISCOVERY_P)) as usize];
    let floor = (DISCOVERY_DELTA_PP / 100.0).max(bar);
    println!(
        "   effective bar = max(absolute {:.1} pp, rank {:.4} = {:.3} pp) = {:.3} pp",
        DISCOVERY_DELTA_PP,
        DISCOVERY_P,
        100.0 * bar,
        100.0 * floor
    );
    let mut hits: Vec<(f32, usize, usize)> = Vec::new();
    let mut scanned = 0usize;
    let mut y = SEARCH_BORDER;
    while y < qh.saturating_sub(SEARCH_BORDER) {
        let mut x = SEARCH_BORDER;
        while x < qw.saturating_sub(SEARCH_BORDER) {
            scanned += 1;
            if let (Some(a), Some(b)) = (
                core_depth(&base1, qw, qh, x, y),
                core_depth(&base2, qw, qh, x, y),
            ) {
                let d = b - a;
                if d.abs() >= floor {
                    hits.push((d, x, y));
                }
            }
            x += 4;
        }
        y += 4;
    }
    hits.sort_by(|a, b| a.0.abs().partial_cmp(&b.0.abs()).unwrap().reverse());
    // Non-maximum suppression so one blob is one report.
    let mut kept: Vec<(f32, usize, usize)> = Vec::new();
    for h in &hits {
        if kept.iter().any(|k| {
            let (dx, dy) = (k.1 as i64 - h.1 as i64, k.2 as i64 - h.2 as i64);
            dx * dx + dy * dy < (3 * CORE_RADIUS) * (3 * CORE_RADIUS)
        }) {
            continue;
        }
        kept.push(*h);
    }
    println!(
        "   scanned {scanned} sites -> {} above the bar -> {} after suppression",
        hits.len(),
        kept.len()
    );
    if kept.is_empty() {
        println!("   NO filter-specific defect found at this sensitivity.");
        println!("   Sensitivity is not asserted: G1 planted -{:.0}% and it was", 100.0 * PLANT_DEPTH);
        println!("   detected, so the search resolves a disc of that depth and radius.");
    } else {
        for (d, x, y) in kept.iter().take(20) {
            let p = rank_p(*d, &null);
            println!(
                "   quad ({x},{y})  DELTA {:+.3} pp  p {:.4}  deficit in {}",
                100.0 * d,
                p,
                if *d < 0.0 { "block 2" } else { "block 1" }
            );
        }
    }
}
