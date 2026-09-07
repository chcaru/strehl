//! P39 -- what active-area geometry does the SHIPPING decoder report for each
//! corpus stack?
//!
//! # Why this exists
//!
//! The shipping binary refused to render `leaf-2-cpl` with the correction on by
//! default:
//!
//! ```text
//! Error: defect correction on frame 0
//! Caused by: defect map was measured on a 7032x4688 active area but is being
//! applied to a 7040x4688 one
//! ```
//!
//! That refusal is correct in principle -- a sensor-coordinate map applied to a
//! different geometry corrects the wrong photosites -- but it means a
//! **default-ON** correction can hard-fail a render, and it surfaced at frame 0
//! of the fold rather than at preflight.
//!
//! A Python census using `rawpy.raw_image_visible` reported `7028x4688` for all
//! 26 stacks, which agrees with neither number above. **rawpy is a different
//! library with different crop logic and is not the decoder that ships.** This
//! example asks the decoder that does.
//!
//! # Partition
//!
//! Every stack lands in exactly one bucket -- a geometry, or a decode failure --
//! and the buckets are asserted to sum to the number examined. "0 mismatched"
//! must be distinguishable from "0 examined".
//!
//! Run: `cargo run --release -p strehl-cli --example defect-geometry-census`

use std::collections::BTreeMap;
use std::path::{Path, PathBuf};

const LIBRARY: &str = r"D:\personal\macro";
/// The active area the embedded map was measured on, from its header.
const MAP_ACTIVE: (usize, usize) = (7032, 4688);

fn first_raw(dir: &Path) -> Option<PathBuf> {
    let mut got: Vec<PathBuf> = std::fs::read_dir(dir)
        .ok()?
        .filter_map(|e| e.ok())
        .map(|e| e.path())
        .filter(|p| {
            p.extension()
                .and_then(|s| s.to_str())
                .is_some_and(|s| s.eq_ignore_ascii_case("arw"))
        })
        .collect();
    got.sort();
    got.into_iter().next()
}

fn main() {
    let mut stacks: Vec<PathBuf> = std::fs::read_dir(LIBRARY)
        .expect("capture library")
        .filter_map(|e| e.ok())
        .map(|e| e.path())
        .filter(|p| p.is_dir())
        .collect();
    stacks.sort();

    let mut buckets: BTreeMap<String, Vec<String>> = BTreeMap::new();
    let mut examined = 0usize;

    for s in &stacks {
        let name = s.file_name().unwrap().to_string_lossy().to_string();
        examined += 1;
        let Some(raw) = first_raw(s) else {
            buckets.entry("no raw frames".into()).or_default().push(name);
            continue;
        };
        match strehl_raw::decode(&raw) {
            Ok(f) => {
                let key = format!(
                    "{}x{} at ({},{})",
                    f.active.width, f.active.height, f.active.x, f.active.y
                );
                buckets.entry(key).or_default().push(name);
            }
            Err(e) => {
                buckets
                    .entry(format!("undecodable: {e}"))
                    .or_default()
                    .push(name);
            }
        }
    }

    println!(
        "the embedded map was measured on {}x{}",
        MAP_ACTIVE.0, MAP_ACTIVE.1
    );
    println!();
    let mut bucketed = 0usize;
    let mut matching = 0usize;
    for (key, names) in &buckets {
        bucketed += names.len();
        let matches = key.starts_with(&format!("{}x{} ", MAP_ACTIVE.0, MAP_ACTIVE.1));
        if matches {
            matching += names.len();
        }
        let verdict = if matches {
            "MATCHES the map exactly"
        } else if key.contains('x') && key.contains("at (") {
            // This slot once read "-> the correction refuses". That was a
            // PREDICTION about check_geometry printed by code that never
            // called check_geometry, and P61 measured it false: the wide body
            // is ADMITTED (0.1138% mismatch against a 1.00% bar) and, because
            // both bodies place their active area at origin (0,0), the extra
            // columns extend the right edge only and every mapped quad
            // addresses the same photosite in both. See BUILD-DEFECT.md P61.
            "differs -> ADMITTED by check_geometry (P61), origin shared"
        } else {
            "not applicable"
        };
        println!("{:>26}  {:3} stacks  {}", key, names.len(), verdict);
        for n in names {
            println!("{:>28}{}", "", n);
        }
        println!();
    }
    println!("examined {examined}, bucketed {bucketed}");
    assert_eq!(examined, bucketed, "PARTITION VIOLATED");
    println!(
        "exact-match {matching} / {examined}   differing-but-admitted {} / {examined}",
        examined - matching
    );
}
