//! The native lossless-JPEG decoder against the linked decoder, file by file:
//! every sample and every metadata field must be identical. Needs captures,
//! so it is ignored by default:
//!
//! ```text
//! STREHL_RAW_VERIFY_DIRS="D:\a;D:\b" cargo test --release -p strehl-raw \
//!     --test lossless-jpeg -- --ignored --nocapture
//! ```
//!
//! Each directory is searched recursively for `.ARW` files.
use std::path::{Path, PathBuf};
use std::sync::atomic::{AtomicUsize, Ordering};

use rayon::prelude::*;

fn arw_files(dir: &Path, out: &mut Vec<PathBuf>) {
    let Ok(entries) = std::fs::read_dir(dir) else {
        return;
    };
    for e in entries.flatten() {
        let p = e.path();
        if p.is_dir() {
            arw_files(&p, out);
        } else if p.extension().is_some_and(|x| x.eq_ignore_ascii_case("arw")) {
            out.push(p);
        }
    }
}

fn differences(a: &strehl_raw::Frame, b: &strehl_raw::Frame) -> Vec<String> {
    let mut d = Vec::new();
    if a.data != b.data {
        let first = a
            .data
            .iter()
            .zip(&b.data)
            .position(|(x, y)| x != y)
            .map(|i| format!("first at ({}, {})", i % a.stride, i / a.stride));
        let count = a.data.iter().zip(&b.data).filter(|(x, y)| x != y).count();
        d.push(format!(
            "samples: {count} differ of {} (lengths {} / {}) {:?}",
            a.data.len(),
            a.data.len(),
            b.data.len(),
            first
        ));
    }
    let bits = |v: &[f32]| v.iter().map(|x| x.to_bits()).collect::<Vec<_>>();
    let checks = [
        ("stride", a.stride != b.stride),
        ("buffer_height", a.buffer_height != b.buffer_height),
        ("active", a.active != b.active),
        (
            "black",
            a.levels.black.to_bits() != b.levels.black.to_bits(),
        ),
        (
            "white",
            a.levels.white.to_bits() != b.levels.white.to_bits(),
        ),
        ("iso", a.iso.map(f32::to_bits) != b.iso.map(f32::to_bits)),
        ("wb", bits(&a.wb_coeffs) != bits(&b.wb_coeffs)),
        (
            "xyz_to_cam",
            bits(a.xyz_to_cam_rgbe.as_flattened()) != bits(b.xyz_to_cam_rgbe.as_flattened()),
        ),
        ("camera", a.camera != b.camera),
    ];
    d.extend(checks.iter().filter(|c| c.1).map(|c| c.0.to_string()));
    let mats = |f: &strehl_raw::Frame| {
        let mut m: Vec<_> = f
            .color_matrices
            .iter()
            .map(|(n, m)| (n.clone(), bits(m.as_flattened())))
            .collect();
        m.sort();
        m
    };
    if mats(a) != mats(b) {
        d.push("color_matrices".into());
    }
    d
}

#[test]
#[ignore = "needs RAW captures: set STREHL_RAW_VERIFY_DIRS"]
fn the_native_decoder_matches_the_linked_decoder_on_every_file() {
    let dirs = std::env::var("STREHL_RAW_VERIFY_DIRS").expect("STREHL_RAW_VERIFY_DIRS");
    let mut files = Vec::new();
    for d in dirs.split(';').filter(|s| !s.trim().is_empty()) {
        arw_files(Path::new(d.trim()), &mut files);
    }
    files.sort();
    assert!(!files.is_empty(), "no .ARW files under {dirs}");
    let same = AtomicUsize::new(0);
    let failures: Vec<String> = files
        .par_iter()
        .filter_map(|p| {
            let native = strehl_raw::decode(p);
            let linked = strehl_raw::decode_linked(p);
            let problem = match (native, linked) {
                (Ok(a), Ok(b)) => {
                    let mut d = differences(&a, &b);
                    // Into a reused buffer full of another value: the same frame.
                    match strehl_raw::decode_into(p, vec![0xABCD; b.data.len()]) {
                        Ok(r) => d.extend(
                            differences(&r, &b)
                                .into_iter()
                                .map(|x| format!("reused buffer: {x}")),
                        ),
                        Err(e) => d.push(format!("reused buffer: {e}")),
                    }
                    (!d.is_empty()).then(|| d.join("; "))
                }
                (Err(a), Err(b)) => (a.to_string() != b.to_string())
                    .then(|| format!("both failed, differently: {a} / {b}")),
                (a, b) => Some(format!(
                    "one failed: native {:?}, linked {:?}",
                    a.err().map(|e| e.to_string()),
                    b.err().map(|e| e.to_string())
                )),
            };
            if problem.is_none() {
                same.fetch_add(1, Ordering::Relaxed);
            }
            problem.map(|m| format!("{}: {m}", p.display()))
        })
        .collect();
    eprintln!(
        "{} files, {} identical, {} differ",
        files.len(),
        same.load(Ordering::Relaxed),
        failures.len()
    );
    for f in failures.iter().take(20) {
        eprintln!("  {f}");
    }
    assert!(failures.is_empty());
}
