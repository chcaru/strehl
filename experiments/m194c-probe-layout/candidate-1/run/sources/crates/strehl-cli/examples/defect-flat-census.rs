//! P41 -- where is the dust, read off a white wall, with no statistic at all.
//!
//! # Why this exists
//!
//! Two lanes hunting the same mote disagree by a factor of 17. BUILD-DEFECT
//! reads mote 2 at quad `(3434, 2305)` at **-13.28%** on real subject stacks; a
//! second lane reads **-0.78%** at 1:1 on the delivered masters and shipped its
//! artifact labelled `NOT-REPRODUCED`. Both readings come from *subject*
//! frames, where a dust shadow sits on top of arbitrary image content and has
//! to be dug out with a significance test, a null model and a stationarity
//! bar. Two different diggers can dig differently and both be defensible.
//!
//! **A defocused, evenly lit white field removes the argument.** Dust attenuates
//! light multiplicatively; against a smooth bright background it is simply a
//! dark disc at a fixed place, and its depth can be read off with division. No
//! p-value, no null, no election. If the mote is real, it is *here*, in these
//! 360 frames, and this program will print its coordinate and its depth. If it
//! is not here, then whatever the subject-frame detectors are finding is not
//! sensor dust and my map is wrong.
//!
//! # The one confound, and how it is handled
//!
//! The flats were shot through a window under **moving cloud** over several
//! minutes, so the illumination is neither constant across the set nor uniform
//! across the frame. An illumination gradient read as dust would be a fabricated
//! defect map -- which is the exact failure this whole lane exists to avoid.
//!
//! Two separations, both cheap and both necessary:
//!
//! 1. **Per-frame normalisation** by the frame's own median removes the
//!    brightness *level*, which is what drifts between frames.
//! 2. **A large-radius high pass** removes the residual *gradient*, which is
//!    what drifts across a frame. Cloud illumination varies over hundreds of
//!    quads; a mote is tens. Dividing by a box mean of radius
//!    [`BG_RADIUS`] leaves the small and removes the large.
//!
//! And one check that the separation worked rather than an assertion that it
//! did: the set is split into **odd and even frames** and the residual computed
//! independently on each half. Cloud does not repeat across an arbitrary
//! partition of the capture order; dust does. A candidate that reads the same
//! depth on both halves is on the sensor. That is the commissioning arm, and it
//! is reported per candidate rather than in aggregate.
//!
//! # It is allowed to find nothing
//!
//! `DEPTH_FLOOR` is an absolute floor and `SPLIT_TOL` is a reproducibility bar.
//! A run that finds no quad passing both prints an empty table and says so.
//! "The deepest thing I saw" is not a detection, and a search that cannot fail
//! returns its least-bad candidate and calls it a find.
//!
//! # Every frame lands in exactly one counted bucket
//!
//! examined = used + undecodable + wrong-geometry + rejected-exposure. A run
//! that used zero frames must not be confusable with a run that found zero
//! motes.

use std::collections::BTreeMap;
use std::path::{Path, PathBuf};

/// White paper taped to a window, lens ~9 cm away, mostly-cloudy Seattle
/// daylight, with and without the CPL.
const FLATS: &str = r"D:\personal\macro\flat-fields\flat-fields";

/// Radius, in quads, of the box mean that estimates the illumination. Large
/// enough that a ~25-quad mote barely perturbs its own background, small enough
/// to track a cloud gradient. This is [`ValidateParams::hp_radius`]'s value, on
/// purpose: the flats and the subject-frame validator must high-pass the same
/// way or their depths are not comparable.
const BG_RADIUS: usize = 64;

/// A candidate must be at least this far below its local background. 1.5% is
/// the depth floor the shipping validator uses.
const DEPTH_FLOOR: f32 = 0.015;

/// Odd-half and even-half depths must agree within this fraction of the deeper
/// one. A cloud shadow that happened to sit still for half the capture would
/// fail this; dust cannot.
const SPLIT_TOL: f32 = 0.35;

/// Non-maximum suppression radius, in quads, when reducing a connected dark
/// blob to one reported coordinate.
const NMS_RADIUS: usize = 24;

/// Reject a frame whose median quad value is outside this fraction of the range
/// between black and white. Too dark and the multiplicative signal is buried in
/// read noise; too bright and the paper is clipping and dust cannot darken it.
const EXPOSURE_WINDOW: (f32, f32) = (0.06, 0.90);

/// The sites the shipping embedded map nominates, in quad coordinates.
const MAP_SITES: [(&str, usize, usize); 2] = [("mote 1", 3202, 119), ("mote 2", 3434, 2305)];

/// How many flat frames to feed to the shipping [`SiteValidator`] as a
/// calibration arm. 24 is above the 8 the CLI uses per stack, so if the
/// shipping instrument disagrees with division it is not for want of frames.
const CALIB_FRAMES: usize = 24;

/// Border, in quads, excluded from the open search.
///
/// **MEASURED, and it is not a tuning knob.** With a border of 8 the search
/// returned 100,467 quads below the floor and **37 of the 40 deepest blobs sat
/// at x=8-33 or x=3484-3511 or y=9-39 or y=2308-2335** -- that is, on the frame
/// edge. That is optical falloff plus a box mean truncated against the array
/// boundary, not dust. At 64 the search returns 3 blobs.
///
/// The honest consequence, stated rather than hidden: **mote 2 at quad
/// (3434, 2305) is 39 quads from the bottom edge, i.e. INSIDE this blind
/// zone.** The open search therefore cannot rule on it in either direction,
/// and the targeted read above -- which prints the neighbourhood so the disc
/// can be seen against its own local background -- is the measurement that
/// bears on it. Widening the border to reach mote 2 would have bought its
/// discovery at the price of 37 false ones.
const SEARCH_BORDER: usize = BG_RADIUS;

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

/// Residual = normalised field divided by its own large-radius box mean.
fn residual(field: &[f32], w: usize, h: usize) -> Vec<f32> {
    let bg = box_blur(field, w, h, BG_RADIUS);
    field
        .iter()
        .zip(&bg)
        .map(|(f, b)| if *b > 0.0 { f / b } else { 1.0 })
        .collect()
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
    let mut acc: Vec<[f64; 2]> = Vec::new();
    let mut calib: Vec<Vec<f32>> = Vec::new();
    let mut used = [0usize; 2];

    for (i, path) in frames.iter().enumerate() {
        let f = match strehl_raw::decode(path) {
            Ok(f) => f,
            Err(e) => {
                *rejected.entry(format!("undecodable: {e}")).or_default() += 1;
                continue;
            }
        };
        let a = (f.active.x, f.active.y, f.active.width, f.active.height);
        match geom {
            None => {
                geom = Some(a);
                acc = vec![[0.0; 2]; (a.2 / 2) * (a.3 / 2)];
            }
            Some(g) if g != a => {
                *rejected
                    .entry(format!("geometry {}x{} != first {}x{}", a.2, a.3, g.2, g.3))
                    .or_default() += 1;
                continue;
            }
            Some(_) => {}
        }
        let (q, qw, qh) = strehl_core::defect_map::quad_mean(&f.data, f.stride, a, f.levels.black);
        // Median off a coarse subsample: exact enough to normalise by, and
        // 64x cheaper than sorting 8.2 M floats 360 times.
        let sub: Vec<f32> = (0..qh)
            .step_by(8)
            .flat_map(|y| (0..qw).step_by(8).map(move |x| (y, x)))
            .map(|(y, x)| q[y * qw + x])
            .collect();
        let med = median_of(&sub);
        let range = f.levels.white - f.levels.black;
        let level = if range > 0.0 { med / range } else { 0.0 };
        if !(EXPOSURE_WINDOW.0..=EXPOSURE_WINDOW.1).contains(&level) {
            *rejected
                .entry(format!(
                    "exposure {:.0}% outside [{:.0}%, {:.0}%]",
                    100.0 * level,
                    100.0 * EXPOSURE_WINDOW.0,
                    100.0 * EXPOSURE_WINDOW.1
                ))
                .or_default() += 1;
            continue;
        }
        let half = i % 2;
        for (dst, v) in acc.iter_mut().zip(&q) {
            dst[half] += (*v / med) as f64;
        }
        if calib.len() < CALIB_FRAMES {
            calib.push(q);
        }
        used[half] += 1;
        if (i + 1) % 40 == 0 {
            eprintln!("  {}/{} frames", i + 1, examined);
        }
    }

    let Some((ax, ay, aw, ah)) = geom else {
        println!("examined {examined}, used 0 -- no frame decoded, nothing measured");
        return;
    };
    let (qw, qh) = (aw / 2, ah / 2);

    println!("== P41 flat-field dust census ==");
    println!("source        : {FLATS}");
    println!("active area   : {aw}x{ah} at ({ax},{ay})  ->  quad grid {qw}x{qh}");
    println!(
        "frames        : examined {examined} = used {} (odd {} / even {}) + rejected {}",
        used[0] + used[1],
        used[1],
        used[0],
        rejected.values().sum::<usize>()
    );
    for (why, n) in &rejected {
        println!("                rejected {n:>4}  {why}");
    }
    if used[0] < 8 || used[1] < 8 {
        println!("\nHALT: fewer than 8 frames in a half; the split-half arm has no power.");
        return;
    }

    let field: Vec<f32> = acc
        .iter()
        .map(|c| ((c[0] + c[1]) / (used[0] + used[1]) as f64) as f32)
        .collect();
    let fa: Vec<f32> = acc.iter().map(|c| (c[0] / used[0] as f64) as f32).collect();
    let fb: Vec<f32> = acc.iter().map(|c| (c[1] / used[1] as f64) as f32).collect();
    let r = residual(&field, qw, qh);
    let ra = residual(&fa, qw, qh);
    let rb = residual(&fb, qw, qh);

    // The null floor: how deep does this residual go where there is no dust?
    let mut sample: Vec<f32> = (0..qh)
        .step_by(5)
        .flat_map(|y| (0..qw).step_by(5).map(move |x| (y, x)))
        .map(|(y, x)| r[y * qw + x])
        .collect();
    sample.sort_by(|a, b| a.partial_cmp(b).unwrap());
    let pct = |p: f32| sample[((sample.len() - 1) as f32 * p) as usize];
    println!(
        "\nresidual null : p50 {:+.3}%   p01 {:+.3}%   p0.1 {:+.3}%   min {:+.3}%   (n={})",
        100.0 * (pct(0.50) - 1.0),
        100.0 * (pct(0.01) - 1.0),
        100.0 * (pct(0.001) - 1.0),
        100.0 * (sample[0] - 1.0),
        sample.len()
    );
    println!(
        "floors        : depth <= {:.1}%   split agreement within {:.0}%",
        -100.0 * DEPTH_FLOOR,
        100.0 * SPLIT_TOL
    );

    // What the shipping map says, read at the shipping map's own coordinates.
    println!("\n-- the embedded map's nominated sites, read off the flats --");
    for (name, px, py) in MAP_SITES {
        if px >= qw || py >= qh {
            println!("{name:8} ({px},{py})  OUTSIDE the {qw}x{qh} quad grid");
            continue;
        }
        // Core mean over the same radius the shipping validator integrates.
        let mut core = (0.0f32, 0usize);
        for dy in -8i32..=8 {
            for dx in -8i32..=8 {
                if dx * dx + dy * dy > 64 {
                    continue;
                }
                let (x, y) = (px as i32 + dx, py as i32 + dy);
                if x < 0 || y < 0 || x as usize >= qw || y as usize >= qh {
                    continue;
                }
                core.0 += r[y as usize * qw + x as usize];
                core.1 += 1;
            }
        }
        println!(
            "{name:8} quad ({px},{py}) = photosite ({},{})",
            2 * px,
            2 * py
        );
        println!(
            "         depth at centre {:+.3}%   over r=8 core {:+.3}%   odd {:+.3}%   even {:+.3}%",
            100.0 * (r[py * qw + px] - 1.0),
            100.0 * (core.0 / core.1 as f32 - 1.0),
            100.0 * (ra[py * qw + px] - 1.0),
            100.0 * (rb[py * qw + px] - 1.0),
        );
        // A picture, because a number at one coordinate cannot show a disc.
        println!("         neighbourhood, 5-quad steps, percent below local background:");
        for dy in (-30i32..=30).step_by(10) {
            let mut row = String::new();
            for dx in (-30i32..=30).step_by(5) {
                let (x, y) = (px as i32 + dx, py as i32 + dy);
                let v = if x < 0 || y < 0 || x as usize >= qw || y as usize >= qh {
                    f32::NAN
                } else {
                    100.0 * (r[y as usize * qw + x as usize] - 1.0)
                };
                row.push_str(&format!("{v:>7.2}"));
            }
            println!("           {dy:>+4} |{row}");
        }
    }

    // The open search: every quad that clears both floors, anywhere.
    println!("\n-- open search over all {} quads --", qw * qh);
    let mut cand: Vec<(usize, usize, f32)> = Vec::new();
    for y in SEARCH_BORDER..qh.saturating_sub(SEARCH_BORDER) {
        for x in SEARCH_BORDER..qw.saturating_sub(SEARCH_BORDER) {
            let v = r[y * qw + x];
            if 1.0 - v < DEPTH_FLOOR {
                continue;
            }
            cand.push((x, y, v));
        }
    }
    let below_floor = cand.len();
    cand.sort_by(|a, b| a.2.partial_cmp(&b.2).unwrap());
    let mut kept: Vec<(usize, usize, f32)> = Vec::new();
    for c in cand {
        if kept.iter().any(|k| {
            let (dx, dy) = (k.0 as i64 - c.0 as i64, k.1 as i64 - c.1 as i64);
            dx * dx + dy * dy < (NMS_RADIUS * NMS_RADIUS) as i64
        }) {
            continue;
        }
        kept.push(c);
        if kept.len() >= 40 {
            break;
        }
    }
    println!(
        "quads below {:.1}%: {below_floor}   distinct blobs after r={NMS_RADIUS} suppression: {}",
        -100.0 * DEPTH_FLOOR,
        kept.len()
    );
    println!(
        "blind zone    : {SEARCH_BORDER} quads at every edge, which CONTAINS mote 2 \
         at (3434,2305), 39 quads from the bottom. The open search decides nothing \
         about it; the targeted read above does."
    );
    let mut confirmed = 0usize;
    let mut split_rejected = 0usize;
    println!("\n  quad(x,y)      photosite      depth     odd      even    split   verdict");
    for (x, y, v) in &kept {
        let d = 1.0 - v;
        let da = 1.0 - ra[y * qw + x];
        let db = 1.0 - rb[y * qw + x];
        let deeper = da.abs().max(db.abs()).max(1e-6);
        let disagree = (da - db).abs() / deeper;
        let ok = da > 0.0 && db > 0.0 && disagree <= SPLIT_TOL;
        if ok {
            confirmed += 1;
        } else {
            split_rejected += 1;
        }
        println!(
            "  ({x:>4},{y:>4})  ({:>5},{:>5})  {:+7.2}% {:+7.2}% {:+7.2}%   {:>5.2}   {}",
            2 * x,
            2 * y,
            -100.0 * d,
            -100.0 * da,
            -100.0 * db,
            disagree,
            if ok { "DUST" } else { "split-rejected" }
        );
    }
    println!(
        "\nblobs: {} = {confirmed} DUST + {split_rejected} split-rejected",
        kept.len()
    );
    if confirmed == 0 {
        println!(
            "NOTHING FOUND. No quad in {qw}x{qh} is both {:.1}% below its local \
             background and reproducible across an odd/even split of the capture order.",
            -100.0 * DEPTH_FLOOR
        );
    }

    // ---- the calibration arm ----
    //
    // Everything above is an ad-hoc script. The number that governs the
    // shipping correction comes from `SiteValidator`, and a script agreeing
    // with itself proves nothing about the code that runs. So: feed the flats
    // to the shipping instrument and see whether it reads the depth that plain
    // division just read off the same photons.
    //
    // This is the arm the whole disagreement turns on. If `SiteValidator`
    // reads ~-3.5% here, it is calibrated and its -8% to -15% on real subject
    // stacks is a property of those stacks. If it reads -15% *here*, on a
    // smooth white wall where the true answer is visible in the ASCII picture
    // above, then my instrument over-reads and the lane that could not
    // reproduce me is closer to right than I am.
    println!("\n-- calibration: the SHIPPING SiteValidator, on these same flats --");
    let map = match strehl_core::defect_map::DefectMap::embedded_for("ILCE-7CM2") {
        Some(m) => m,
        None => {
            println!("no embedded map for ILCE-7CM2; calibration arm not run");
            return;
        }
    };
    if calib.len() < 8 {
        println!(
            "only {} frames retained; the validator needs 8. Arm not run.",
            calib.len()
        );
        return;
    }
    let params = strehl_core::defect_map::ValidateParams::default();
    let mut v = strehl_core::defect_map::SiteValidator::new(&map, params);
    for q in &calib {
        v.observe(q, qw, qh);
    }
    let (verdicts, report) = v.finish();
    println!(
        "frames {}   examined {} = confirmed {} + not-significant {} + too-shallow {} \
         + not-stationary {} + unmeasurable {}",
        report.frames,
        report.examined,
        report.confirmed,
        report.not_significant,
        report.too_shallow,
        report.not_stationary,
        report.unmeasurable
    );
    println!("\n  quad(x,y)     validator   division   ratio   p        presence  outcome");
    for vd in &verdicts {
        // The same site, read by the ad-hoc residual over the same core disc.
        let (px, py) = (vd.cx as usize, vd.cy as usize);
        let mut core = (0.0f32, 0usize);
        for dy in -(params.core_radius as i32)..=(params.core_radius as i32) {
            for dx in -(params.core_radius as i32)..=(params.core_radius as i32) {
                if (dx * dx + dy * dy) as usize > params.core_radius * params.core_radius {
                    continue;
                }
                let (x, y) = (px as i32 + dx, py as i32 + dy);
                if x < 0 || y < 0 || x as usize >= qw || y as usize >= qh {
                    continue;
                }
                core.0 += r[y as usize * qw + x as usize];
                core.1 += 1;
            }
        }
        let div = (core.0 / core.1 as f32 - 1.0) as f64;
        println!(
            "  ({px:>4},{py:>4})   {:+7.3}%   {:+7.3}%   {:>5.2}   {:.4}   {:.2}      {:?}",
            100.0 * vd.depth,
            100.0 * div,
            if div.abs() > 1e-9 {
                vd.depth / div
            } else {
                f64::NAN
            },
            vd.p,
            vd.presence,
            vd.outcome
        );
    }
}
