//! P61 -- does the geometry check REFUSE the 7040-wide bodies, or admit them?
//!
//! # Why this is not answerable by reading either instrument
//!
//! `defect-geometry-census` (P39) prints, against every 7040x4688 stack:
//!
//! ```text
//! 7040x4688 at (0,0)   11 stacks  DOES NOT MATCH -> the correction refuses
//! ```
//!
//! That string is an **assertion the census never tests.** It compares the
//! geometry tuple to a constant and prints a conclusion about what
//! `check_geometry` would do, without calling it. Meanwhile the code says:
//!
//! ```text
//! pub const MAX_ACTIVE_MISMATCH_FRAC: f64 = 0.01;
//! ```
//!
//! and `|7032 - 7040| / 7032 = 0.114%`, which is **inside** a 1% bar. So the
//! census's label and the constant disagree, and one of them is wrong. This is
//! the project's own recurring defect -- a value that is computed and printed
//! but that nothing conditions on -- appearing in an instrument I wrote.
//!
//! # Why the answer matters more than it looks
//!
//! The two possibilities are not a near miss and a slightly-worse near miss.
//! They are opposite failures, and the *better*-looking one is the dangerous
//! one:
//!
//! * **If it refuses**, then turning the correction on by default hard-fails
//!   11 of 26 corpus stacks at frame 0 of the fold. Loud, safe, unshippable.
//! * **If it admits**, then a map whose coordinates were measured on a
//!   7032-wide active area is applied to a 7040-wide one, and every corrected
//!   quad may land on the wrong photosites -- **silently**. A tolerance that
//!   converts a hard refusal into a quiet misregistration has made the failure
//!   invisible rather than fixed it.
//!
//! Under `CoordSpace::Active` the origin is the active rectangle's own
//! `(ax, ay)`, so whether the 8 extra columns shift the mapped coordinates
//! depends on where the decoder places them. This probe reports the offset
//! rather than assuming it is zero.
//!
//! # What is measured
//!
//! 1. The literal `Result` of `check_geometry` at both geometries -- called,
//!    not predicted.
//! 2. The mismatch fraction against the bar, so the verdict is arithmetic.
//! 3. Whether a real 7040 frame and a real 7032 frame put their active origin
//!    in the same place, which decides whether admission implies displacement.
//!
//! Run: `cargo run --release -p strehl-cli --example defect-geometry-verdict`

use std::path::{Path, PathBuf};

use strehl_core::defect_map::DefectMap;

const MAP_ACTIVE: (usize, usize) = (7032, 4688);
const WIDE_ACTIVE: (usize, usize) = (7040, 4688);

/// One stack of each observed geometry, to read the active origin from a real
/// decode rather than from the census's summary of one.
const NARROW_STACK: &str = r"D:\personal\macro\coffee-bubbles";
const WIDE_STACK: &str = r"D:\personal\macro\tweezers-cpl";

fn first_raw(dir: &Path) -> Option<PathBuf> {
    let mut v: Vec<PathBuf> = std::fs::read_dir(dir)
        .ok()?
        .filter_map(|e| e.ok())
        .map(|e| e.path())
        .filter(|p| p.extension().is_some_and(|x| x.eq_ignore_ascii_case("ARW")))
        .collect();
    v.sort();
    v.into_iter().next()
}

fn main() {
    println!("{}", "=".repeat(72));
    println!("P61 -- is the 7040-wide body refused, or silently admitted?");
    println!("{}", "=".repeat(72));

    let Some(map) = DefectMap::embedded_for("ILCE-7CM2") else {
        println!("REFUSED: no embedded map for ILCE-7CM2; nothing to check");
        std::process::exit(2);
    };
    println!("map declares : sensor {}x{}", map.sensor_w, map.sensor_h);
    println!("map coords   : {:?}", map.coords);
    println!("dust quads   : {}", map.dust.len());
    println!("bar          : MAX_ACTIVE_MISMATCH_FRAC = {}", DefectMap::MAX_ACTIVE_MISMATCH_FRAC);
    println!();

    // ---- 1. call the check, do not predict it ---------------------------
    println!("-- check_geometry CALLED (not predicted) --");
    let mut admitted_wide = false;
    for (label, (w, h)) in [("narrow 7032", MAP_ACTIVE), ("wide   7040", WIDE_ACTIVE)] {
        let frac = (map.sensor_w as f64 - w as f64).abs() / map.sensor_w as f64;
        match map.check_geometry(w, h) {
            Ok(()) => {
                println!("  {label}x{h}  ADMITTED   mismatch {:.4}% vs bar {:.2}%", frac * 100.0, DefectMap::MAX_ACTIVE_MISMATCH_FRAC * 100.0);
                if (w, h) == WIDE_ACTIVE {
                    admitted_wide = true;
                }
            }
            Err(e) => println!("  {label}x{h}  REFUSED    {e}"),
        }
    }
    println!();

    // ---- 2. does admission imply displacement? --------------------------
    println!("-- active origin, read from a real frame of each geometry --");
    let mut origins = Vec::new();
    for (label, dir) in [("narrow", NARROW_STACK), ("wide  ", WIDE_STACK)] {
        let Some(p) = first_raw(Path::new(dir)) else {
            println!("  {label}  no raw in {dir} -- cannot read origin");
            continue;
        };
        match strehl_raw::decode(&p) {
            Ok(f) => {
                println!(
                    "  {label}  {}x{} at ({},{})   {}",
                    f.active.width,
                    f.active.height,
                    f.active.x,
                    f.active.y,
                    p.file_name().unwrap_or_default().to_string_lossy()
                );
                origins.push((f.active.x, f.active.y, f.active.width));
            }
            Err(e) => println!("  {label}  decode failed: {e}"),
        }
    }
    println!();

    // ---- verdict, gated on the measurement ------------------------------
    println!("{}", "-".repeat(72));
    if origins.len() < 2 {
        println!("REFUSED: could not read both geometries; no verdict.");
        println!("  A partial reading here would be a claim about displacement");
        println!("  built on one of the two frames it needs.");
        std::process::exit(3);
    }
    let (nx, ny, nw) = origins[0];
    let (wx, wy, ww) = origins[1];
    let same_origin = nx == wx && ny == wy;
    let width_delta = ww as i64 - nw as i64;

    println!("active origin same in both : {same_origin}  (narrow ({nx},{ny}), wide ({wx},{wy}))");
    println!("active width delta         : {width_delta} photosites = {} quads", width_delta / 2);
    println!();

    if admitted_wide {
        println!("VERDICT: the wide body is ADMITTED, not refused.");
        println!("  The census's 'the correction refuses' label is WRONG -- it");
        println!("  printed a prediction about a function it never called.");
        if same_origin {
            println!();
            println!("  Both geometries share active origin ({nx},{ny}), so a mapped");
            println!("  quad at (px,py) addresses the SAME photosite in both. The");
            println!("  extra {width_delta} columns extend the right edge only.");
            println!("  Displacement is therefore ZERO and admission is SAFE for");
            println!("  every quad the map names, PROVIDED no named quad lies");
            println!("  beyond the narrower width -- checked next.");
            let maxpx = map.dust.iter().map(|d| d.px).max().unwrap_or(0) as usize;
            let limit = nw / 2;
            println!("  max mapped quad px {maxpx}, narrow quad limit {limit}  -> {}",
                if maxpx < limit { "all named quads inside both" } else { "SOME NAMED QUADS OUTSIDE THE NARROW FRAME" });
        } else {
            println!();
            println!("  The origins DIFFER, so an admitted map is applied at a");
            println!("  shifted origin and every corrected quad lands on the wrong");
            println!("  photosites. This is a SILENT MISREGISTRATION and it is");
            println!("  worse than the refusal it replaced.");
            std::process::exit(1);
        }
    } else {
        println!("VERDICT: the wide body is REFUSED.");
        println!("  Turning the correction on by default therefore hard-fails 11 of");
        println!("  26 corpus stacks. Loud and safe, but not shippable as a default.");
        std::process::exit(1);
    }
}
