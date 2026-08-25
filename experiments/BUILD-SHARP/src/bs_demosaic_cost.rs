//! What does demosaic-before-gather actually cost?
//!
//! BUILD-SHARP's diagnosis (docs/research/BUILD-SHARP.md §5.1) found that the
//! gather runs on the CFA quad plane and the demosaic then doubles the grid, so
//! a feature at 0.25 cycles/output-px sits at 0.5 cycles/plane-px and sees
//! kernel MTF 0.6251 instead of 0.9402 — a free 1.50x contrast at the top of
//! the real detail band, if the order is reversed.
//!
//! The objection is cost. This measures it instead of estimating it. Run in
//! the pinned tree; it touches nothing in the shared working tree.

use std::time::Instant;
use strehl_core::demosaic::{demosaic, Mosaic};

fn main() {
    // The owner's sensor, as the render log reports it.
    let (w, h) = (7032usize, 4688usize);
    let reps = 5;

    // A deterministic mosaic with real structure, so the branch predictor and
    // the gradient stencils see something like a photograph rather than a
    // constant. Content does not change the operation count, but a constant
    // field can flatter a memory-bound kernel.
    let mut data = vec![0f32; w * h];
    for y in 0..h {
        for x in 0..w {
            let v = ((x * 7 + y * 13) % 251) as f32 / 251.0;
            data[y * w + x] = v * 0.8 + 0.1;
        }
    }
    let m = Mosaic { data: &data, width: w, height: h };
    let mut out = vec![0f32; w * h * 3];

    // Warm the caches and the pages; the first pass pays for first-touch on a
    // 396 MB output buffer and is not representative.
    demosaic(&m, &mut out);

    let mut best = f64::INFINITY;
    let mut total = 0.0;
    for _ in 0..reps {
        let t = Instant::now();
        demosaic(&m, &mut out);
        let s = t.elapsed().as_secs_f64();
        total += s;
        best = best.min(s);
    }

    let mean = total / reps as f64;
    println!("demosaic {w}x{h} -> RGB f32");
    println!("  best   : {:.1} ms/frame", best * 1e3);
    println!("  mean   : {:.1} ms/frame  (n={reps})", mean * 1e3);
    println!("  299 frames, single-threaded: {:.1} s summed", mean * 299.0);
    println!();
    println!("compare: decode measured at 67-70 ms/frame, ~20 s summed per pass,");
    println!("and the pipeline already runs THREE passes (zero, one, two).");
    // Guard: a demosaic that returns instantly did not run.
    assert!(best > 1e-4, "demosaic returned in {best}s -- it did not run");
    assert!(out.iter().any(|v| *v != 0.0), "output is all zero");
}
