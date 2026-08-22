//! `strehl stack` — the walking skeleton.
//!
//! What this is, precisely: `decode -> calibrate -> NO alignment -> ring
//! difference focus volume -> plain per-pixel argmax -> 16-bit TIFF`. That is
//! SYNTHESIS §8 step 0, and it deliberately implements the naive selector this
//! whole project argues against, because that selector is the **named baseline
//! artifact** every later quality claim must be a measured delta against, and
//! because running it is how the argmax noise defect gets measured on our own
//! data rather than on someone else's.
//!
//! So: no denoising, no smoothing of the winner map, no top-k, no blending. Its
//! job is to be the honest worst case.
//!
//! # Streaming, not materialised
//!
//! SYNTHESIS §9 lists never-materialise as one of four irreversible decisions,
//! so the skeleton obeys it even though 22 frames would fit. The file list is
//! split into a bounded number of chunks; each chunk is folded by one worker
//! that decodes a frame, folds it, and **drops it before decoding the next**.
//! Peak memory is O(workers), not O(frames), and the worker count is derived
//! from a memory budget rather than from the frame count.

use std::path::PathBuf;
use std::sync::atomic::{AtomicUsize, Ordering};
use std::time::Instant;

use anyhow::{Context, Result, bail, ensure};
use rayon::prelude::*;
use strehl_core::focus::FocusField;
use strehl_core::noise::{Levels, NoiseModel, Provenance};
use strehl_core::plane::{PlaneGeometry, QuadSource, green_luma};
use strehl_core::profile;
use strehl_core::stack::{Selection, speckle_fraction};
use strehl_core::{CfaPlane, Error};
use strehl_raw::Frame;

use crate::image_out;

/// Working-set ceiling used to size the worker pool. SYNTHESIS §3.2 ratchets
/// peak RSS at 8 GB independent of frame count; this leaves headroom for the
/// decoder's own scratch and the output buffers.
const MEMORY_BUDGET_BYTES: usize = 6 << 30;

/// A winner index this far from its 3x3 neighbourhood median is counted as
/// speckle rather than depth structure.
const SPECKLE_TOLERANCE: u16 = 2;

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct Roi {
    pub x: usize,
    pub y: usize,
    pub width: usize,
    pub height: usize,
}

pub fn parse_roi(s: &str) -> std::result::Result<Roi, String> {
    let parts: Vec<&str> = s.split(',').map(str::trim).collect();
    if parts.len() != 4 {
        return Err(format!("expected X,Y,W,H, got {s:?}"));
    }
    let v: std::result::Result<Vec<usize>, _> = parts.iter().map(|p| p.parse::<usize>()).collect();
    let v = v.map_err(|e| format!("{s:?}: {e}"))?;
    if v[2] == 0 || v[3] == 0 {
        return Err(format!("{s:?}: width and height must be non-zero"));
    }
    Ok(Roi {
        x: v[0],
        y: v[1],
        width: v[2],
        height: v[3],
    })
}

pub struct StackOptions {
    pub dir: PathBuf,
    pub out: PathBuf,
    pub limit: Option<usize>,
    pub srgb: bool,
    pub index_map: Option<PathBuf>,
    pub flat_roi: Option<Roi>,
}

pub fn run(opts: &StackOptions) -> Result<()> {
    let paths = crate::raw_paths(&opts.dir, opts.limit)?;
    ensure!(
        paths.len() < u16::MAX as usize,
        "{} frames exceeds the u16 winner-index range",
        paths.len()
    );
    let input_bytes: u64 = paths
        .iter()
        .filter_map(|p| std::fs::metadata(p).ok().map(|m| m.len()))
        .sum();

    // One frame up front, for geometry, levels, camera and ISO. The noise model
    // is built once here and injected; AGENTS.md rule 3 forbids any stage
    // deriving its own.
    let t_prologue = Instant::now();
    let first = strehl_raw::decode(&paths[0]).context("decoding the first frame")?;
    let prologue_secs = t_prologue.elapsed().as_secs_f64();

    let geom = first.geometry();
    let levels = first.levels;
    let camera = first.camera.clone();
    let iso = first.iso;
    let wb = first.wb_gains();
    let frame_bytes = first.allocated_bytes();
    drop(first);

    let noise = profile::noise_model_for(&camera, iso, levels);
    let middle = (paths.len() / 2) as u16;

    if let Some(roi) = opts.flat_roi {
        ensure!(
            roi.x + roi.width <= geom.width && roi.y + roi.height <= geom.height,
            "--flat-roi {},{},{},{} does not fit inside the {}x{} plane",
            roi.x,
            roi.y,
            roi.width,
            roi.height,
            geom.width,
            geom.height
        );
    }

    let plan = WorkerPlan::new(paths.len(), geom, frame_bytes);

    eprintln!("strehl stack -- naive per-pixel argmax baseline (SYNTHESIS §8 step 0)");
    eprintln!("camera          : {camera}");
    eprintln!(
        "iso             : {}",
        iso.map(|v| format!("{v:.0}")).unwrap_or("UNKNOWN".into())
    );
    eprintln!(
        "levels          : black {}, white {}",
        levels.black, levels.white
    );
    eprintln!(
        "white balance   : {}",
        wb.map(|g| format!("R {:.4}  G 1.0000  B {:.4} (green-normalised)", g[0], g[2]))
            .unwrap_or("UNAVAILABLE -- writing unbalanced linear output".into())
    );
    eprintln!("{}", provenance_line(&noise));
    eprintln!(
        "planes          : {} x {} per CFA plane (active {} x {} halved)",
        geom.width,
        geom.height,
        geom.width * 2,
        geom.height * 2
    );
    eprintln!(
        "frames          : {} from {}",
        paths.len(),
        opts.dir.display()
    );
    eprintln!("{}", plan.describe());
    eprintln!();

    let live = AtomicUsize::new(0);
    let peak_live = AtomicUsize::new(0);
    let ctx = FoldContext {
        geom,
        levels,
        noise: &noise,
        middle,
        roi: opts.flat_roi,
        live: &live,
        peak_live: &peak_live,
    };

    let t0 = Instant::now();
    let merged = paths
        .par_chunks(plan.chunk_len)
        .enumerate()
        .map(|(chunk_index, chunk)| ctx.fold_chunk((chunk_index * plan.chunk_len) as u16, chunk))
        .reduce_with(|a, b| match (a, b) {
            (Ok(mut a), Ok(b)) => {
                a.absorb(b)?;
                Ok(a)
            }
            (Err(e), _) | (Ok(_), Err(e)) => Err(e),
        })
        .expect("at least one chunk")?;
    let stack_secs = t0.elapsed().as_secs_f64();

    let n = merged.selection.frames_folded() as f64;
    ensure!(
        merged.selection.frames_folded() as usize == paths.len(),
        "folded {} frames, expected {}",
        merged.selection.frames_folded(),
        paths.len()
    );

    eprintln!("--- throughput (MEASURED) ---");
    eprintln!("wall clock      : {stack_secs:.3} s  (+{prologue_secs:.3} s prologue frame)");
    eprintln!("per frame       : {:.1} ms", 1000.0 * stack_secs / n);
    eprintln!(
        "throughput      : {:.1} MB/s over {:.1} MB of ARW",
        input_bytes as f64 / 1e6 / stack_secs,
        input_bytes as f64 / 1e6
    );
    eprintln!(
        "  decode        : {:.3} s summed across workers ({:.1} ms/frame)",
        merged.decode_secs,
        1000.0 * merged.decode_secs / n
    );
    eprintln!(
        "  focus + fold  : {:.3} s summed across workers ({:.1} ms/frame)",
        merged.fold_secs,
        1000.0 * merged.fold_secs / n
    );
    eprintln!(
        "in-flight frames: {} peak, bound {} (never O(N))",
        peak_live.load(Ordering::Relaxed),
        plan.chunks
    );
    eprintln!();

    report_winners(&merged.selection);

    let t_speckle = Instant::now();
    let speckle = speckle_fraction(merged.selection.index(), geom, SPECKLE_TOLERANCE);
    eprintln!("--- argmax defect (MEASURED) ---");
    eprintln!(
        "index speckle   : {:.3}% of pixels differ by more than {} from their 3x3 median index",
        100.0 * speckle,
        SPECKLE_TOLERANCE
    );
    eprintln!(
        "                  (depth is piecewise smooth, so this is argmax electing noise; {:.2} s to compute)",
        t_speckle.elapsed().as_secs_f64()
    );

    if let Some(roi) = opts.flat_roi {
        report_flat_roi(&merged, roi, geom, levels, &noise, middle)?;
    } else {
        eprintln!(
            "flat ROI        : not requested. Pass --flat-roi X,Y,W,H to measure the noise penalty."
        );
    }
    eprintln!();

    let t_write = Instant::now();
    write_outputs(&merged.selection, levels, wb, opts)?;
    eprintln!("write           : {:.3} s", t_write.elapsed().as_secs_f64());

    Ok(())
}

fn provenance_line(noise: &NoiseModel) -> String {
    match noise.provenance {
        Provenance::Profile => format!(
            "noise model     : PROVENANCE=Profile -- camera profile at ISO {:.0}. Trustworthy for ranking; the gain is DERIVED from white-level consistency, not a photon-transfer measurement.",
            noise.iso
        ),
        Provenance::Measured => format!(
            "noise model     : PROVENANCE=Measured -- fitted from this stack at ISO {:.0}.",
            noise.iso
        ),
        Provenance::Fallback => concat!(
            "noise model     : PROVENANCE=Fallback -- NO CALIBRATION. Unity gain and 4 e- read ",
            "noise were guessed because the body is unprofiled or the file reported no ISO. ",
            "Every number below is untrustworthy."
        )
        .to_string(),
    }
}

/// How the stack is split across workers, and why.
struct WorkerPlan {
    workers: usize,
    chunks: usize,
    chunk_len: usize,
    per_worker_bytes: usize,
}

impl WorkerPlan {
    fn new(frames: usize, geom: PlaneGeometry, frame_bytes: usize) -> Self {
        // Selection is f32 focus + 4 u16 channels + u16 index; FocusField is
        // three f32 planes; luma is one more.
        let px = geom.pixels();
        let per_worker_bytes = px * (14 + 12 + 4) + frame_bytes;
        let by_memory = (MEMORY_BUDGET_BYTES / per_worker_bytes).max(1);
        let by_cpu = std::thread::available_parallelism()
            .map(|v| v.get())
            .unwrap_or(1);
        let workers = by_memory.min(by_cpu).min(frames);
        let chunk_len = frames.div_ceil(workers);
        Self {
            workers,
            chunks: frames.div_ceil(chunk_len),
            chunk_len,
            per_worker_bytes,
        }
    }

    fn describe(&self) -> String {
        format!(
            "workers         : {} chunks of <= {} frames ({} allowed by the {} MB budget, {} by CPU)\n\
             working set     : {:.0} MB/worker, {:.2} GB peak (DERIVED, O(workers) not O(frames))",
            self.chunks,
            self.chunk_len,
            self.workers,
            MEMORY_BUDGET_BYTES / (1 << 20),
            std::thread::available_parallelism()
                .map(|v| v.get())
                .unwrap_or(1),
            self.per_worker_bytes as f64 / 1e6,
            (self.chunks * self.per_worker_bytes) as f64 / 1e9,
        )
    }
}

/// One worker's partial result.
struct Partial {
    selection: Selection,
    /// Black-subtracted green over the flat ROI, from the middle frame, kept by
    /// whichever worker happened to decode it.
    middle_roi: Option<Vec<f32>>,
    decode_secs: f64,
    fold_secs: f64,
}

impl Partial {
    fn absorb(&mut self, other: Partial) -> Result<()> {
        self.selection.absorb(&other.selection)?;
        if self.middle_roi.is_none() {
            self.middle_roi = other.middle_roi;
        }
        self.decode_secs += other.decode_secs;
        self.fold_secs += other.fold_secs;
        Ok(())
    }
}

/// Everything a worker needs that is the same for every worker. The noise model
/// is borrowed, never cloned per worker — it is injected exactly once
/// (`AGENTS.md` rule 3).
struct FoldContext<'a> {
    geom: PlaneGeometry,
    levels: Levels,
    noise: &'a NoiseModel,
    middle: u16,
    roi: Option<Roi>,
    live: &'a AtomicUsize,
    peak_live: &'a AtomicUsize,
}

impl FoldContext<'_> {
    fn fold_chunk(&self, first_index: u16, chunk: &[PathBuf]) -> Result<Partial> {
        let mut selection = Selection::new(self.geom);
        let mut field = FocusField::new(self.geom);
        let mut luma = vec![0.0f32; self.geom.pixels()];
        let mut middle_roi = None;
        let (mut decode_secs, mut fold_secs) = (0.0, 0.0);

        for (offset, path) in chunk.iter().enumerate() {
            let index = first_index + offset as u16;

            let t = Instant::now();
            let in_flight = self.live.fetch_add(1, Ordering::Relaxed) + 1;
            self.peak_live.fetch_max(in_flight, Ordering::Relaxed);
            let frame = match strehl_raw::decode(path) {
                Ok(f) => f,
                Err(e) => {
                    self.live.fetch_sub(1, Ordering::Relaxed);
                    return Err(e).with_context(|| format!("frame {index}"));
                }
            };
            decode_secs += t.elapsed().as_secs_f64();

            let t = Instant::now();
            let result = self.fold_one(
                &mut selection,
                &mut field,
                &mut luma,
                index,
                &frame,
                &mut middle_roi,
            );
            // Explicit: the frame is gone before the next decode starts. This
            // is the whole memory argument.
            drop(frame);
            self.live.fetch_sub(1, Ordering::Relaxed);
            fold_secs += t.elapsed().as_secs_f64();
            result?;
        }

        Ok(Partial {
            selection,
            middle_roi,
            decode_secs,
            fold_secs,
        })
    }

    fn fold_one(
        &self,
        selection: &mut Selection,
        field: &mut FocusField,
        luma: &mut [f32],
        index: u16,
        frame: &Frame,
        middle_roi: &mut Option<Vec<f32>>,
    ) -> Result<()> {
        if frame.levels != self.levels {
            bail!(
                "frame {index} ({}) has levels black {} white {}, but the stack was calibrated at black {} white {}",
                frame.path.display(),
                frame.levels.black,
                frame.levels.white,
                self.levels.black,
                self.levels.white
            );
        }
        green_luma(frame, self.levels.black, luma);
        field.compute(luma, self.noise);
        selection
            .fold(index, frame, field.values())
            .map_err(|e| match e {
                Error::DimensionMismatch { got, want, .. } => anyhow::anyhow!(
                    "frame {index} ({}) has plane geometry {got:?}, expected {want:?}",
                    frame.path.display()
                ),
                other => anyhow::anyhow!(other),
            })?;
        if index == self.middle
            && let Some(roi) = self.roi
        {
            *middle_roi = Some(roi_green(frame, roi, self.levels.black));
        }
        Ok(())
    }
}

/// Black-subtracted `(G1 + G2) / 2` over an ROI in plane coordinates.
fn roi_green(frame: &Frame, roi: Roi, black: f32) -> Vec<f32> {
    let (g1x, g1y) = CfaPlane::G1.rggb_offset();
    let (g2x, g2y) = CfaPlane::G2.rggb_offset();
    let mut out = Vec::with_capacity(roi.width * roi.height);
    for py in roi.y..roi.y + roi.height {
        let (row0, row1) = frame.quad_rows(py);
        let g1_row = if g1y == 0 { row0 } else { row1 };
        let g2_row = if g2y == 0 { row0 } else { row1 };
        for px in roi.x..roi.x + roi.width {
            let g1 = g1_row[2 * px + g1x] as f32 - black;
            let g2 = g2_row[2 * px + g2x] as f32 - black;
            out.push(0.5 * (g1 + g2));
        }
    }
    out
}

fn mean_and_sigma(v: &[f32]) -> (f64, f64) {
    if v.is_empty() {
        return (0.0, 0.0);
    }
    let n = v.len() as f64;
    let mean = v.iter().map(|x| *x as f64).sum::<f64>() / n;
    let var = v.iter().map(|x| (*x as f64 - mean).powi(2)).sum::<f64>() / n;
    (mean, var.sqrt())
}

fn report_winners(selection: &Selection) {
    let frames = selection.frames_folded() as usize;
    let mut hist = vec![0u64; frames];
    for i in selection.index() {
        hist[*i as usize] += 1;
    }
    let total = selection.geometry().pixels() as f64;
    eprintln!("--- winner distribution ---");
    if frames <= 40 {
        for (k, count) in hist.iter().enumerate() {
            let pct = 100.0 * *count as f64 / total;
            let bar = "#".repeat((pct * 0.8).round() as usize);
            eprintln!("  frame {k:>3} : {pct:6.2}%  {bar}");
        }
    } else {
        let won = hist.iter().filter(|c| **c > 0).count();
        eprintln!("  {won} of {frames} frames won at least one pixel");
    }
    eprintln!();
}

fn report_flat_roi(
    merged: &Partial,
    roi: Roi,
    geom: PlaneGeometry,
    levels: Levels,
    noise: &NoiseModel,
    middle: u16,
) -> Result<()> {
    let stacked: Vec<f32> = (roi.y..roi.y + roi.height)
        .flat_map(|py| (roi.x..roi.x + roi.width).map(move |px| (px, py)))
        .map(|(px, py)| merged.selection.green_mean(geom.index(px, py)) - levels.black)
        .collect();
    let single = merged
        .middle_roi
        .as_ref()
        .context("the middle frame's ROI was never captured")?;

    let (stack_mean, stack_sigma) = mean_and_sigma(&stacked);
    let (single_mean, single_sigma) = mean_and_sigma(single);
    let ratio = stack_sigma / single_sigma;

    let mut roi_index: Vec<u16> = (roi.y..roi.y + roi.height)
        .flat_map(|py| (roi.x..roi.x + roi.width).map(move |px| (px, py)))
        .map(|(px, py)| merged.selection.index()[geom.index(px, py)])
        .collect();
    roi_index.sort_unstable();
    let distinct = {
        let mut d = roi_index.clone();
        d.dedup();
        d.len()
    };

    eprintln!();
    eprintln!("--- flat-ROI noise control (MEASURED) ---");
    eprintln!(
        "roi             : x {} y {} w {} h {} in plane coordinates ({} px)",
        roi.x,
        roi.y,
        roi.width,
        roi.height,
        stacked.len()
    );
    eprintln!(
        "stacked green   : sigma {stack_sigma:8.3} DN   mean {stack_mean:9.2} DN   (argmax over {} frames)",
        merged.selection.frames_folded()
    );
    eprintln!(
        "single frame {middle:<3}: sigma {single_sigma:8.3} DN   mean {single_mean:9.2} DN   (no stacking at all)"
    );
    eprintln!(
        "model predicts  : sigma {:8.3} DN for one green-luma sample at that level",
        noise.green_luma_sigma(single_mean as f32)
    );
    eprintln!("RATIO           : {ratio:.3}x");
    eprintln!(
        "                  A RATIO ABOVE 1.0 MEANS THE STACK IS NOISIER THAN ONE UNSTACKED FRAME."
    );
    eprintln!(
        "winners in roi  : {distinct} distinct frames, median {}",
        roi_index[roi_index.len() / 2]
    );
    Ok(())
}

fn srgb_encode(v: f32) -> f32 {
    if v <= 0.003_130_8 {
        12.92 * v
    } else {
        1.055 * v.powf(1.0 / 2.4) - 0.055
    }
}

fn write_outputs(
    selection: &Selection,
    levels: Levels,
    wb: Option<[f32; 3]>,
    opts: &StackOptions,
) -> Result<()> {
    let geom = selection.geometry();
    let n = geom.pixels();
    let range = levels.range();
    ensure!(range > 0.0, "white level is not above black level");
    let gains = wb.unwrap_or([1.0, 1.0, 1.0]);

    let encode = |raw: f32, gain: f32| -> u16 {
        let v = ((raw - levels.black).max(0.0) * gain / range).min(1.0);
        let v = if opts.srgb { srgb_encode(v) } else { v };
        (v * u16::MAX as f32 + 0.5) as u16
    };

    let r = selection.plane(CfaPlane::R);
    let b = selection.plane(CfaPlane::B);
    let mut rgb = vec![0u16; n * 3];
    let (pixels, _) = rgb.as_chunks_mut::<3>();
    for (i, px) in pixels.iter_mut().enumerate() {
        px[0] = encode(r[i] as f32, gains[0]);
        px[1] = encode(selection.green_mean(i), gains[1]);
        px[2] = encode(b[i] as f32, gains[2]);
    }
    image_out::write_rgb16(&opts.out, geom.width as u32, geom.height as u32, &rgb)?;
    eprintln!(
        "wrote           : {} ({} x {}, 16-bit RGB, {}, binned from one 2x2 quad per pixel -- NOT demosaiced)",
        opts.out.display(),
        geom.width,
        geom.height,
        if opts.srgb { "sRGB transfer" } else { "linear" }
    );

    if let Some(path) = &opts.index_map {
        ensure!(
            (0..n).all(|i| selection.is_decided(i)),
            "some pixels were never decided; the index map would be meaningless"
        );
        image_out::write_gray16(
            path,
            geom.width as u32,
            geom.height as u32,
            selection.index(),
        )?;
        eprintln!(
            "wrote           : {} ({} x {}, 16-bit gray, literal frame index 0..{} -- autoscale to view)",
            path.display(),
            geom.width,
            geom.height,
            selection.frames_folded().saturating_sub(1)
        );
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn roi_parses_four_unsigned_fields() {
        assert_eq!(
            parse_roi("10,20,30,40").unwrap(),
            Roi {
                x: 10,
                y: 20,
                width: 30,
                height: 40
            }
        );
        assert_eq!(parse_roi(" 1 , 2 , 3 , 4 ").unwrap().width, 3);
    }

    #[test]
    fn roi_rejects_malformed_and_degenerate_input() {
        assert!(parse_roi("1,2,3").is_err());
        assert!(parse_roi("1,2,3,4,5").is_err());
        assert!(parse_roi("a,2,3,4").is_err());
        assert!(parse_roi("-1,2,3,4").is_err());
        assert!(parse_roi("1,2,0,4").is_err());
        assert!(parse_roi("1,2,3,0").is_err());
    }

    #[test]
    fn srgb_transfer_hits_its_endpoints_and_is_monotone() {
        assert!(srgb_encode(0.0).abs() < 1e-9);
        assert!((srgb_encode(1.0) - 1.0).abs() < 1e-6);
        // The standard 0.5 reference point.
        assert!((srgb_encode(0.5) - 0.7354).abs() < 1e-3);
        let mut prev = -1.0;
        for i in 0..=100 {
            let v = srgb_encode(i as f32 / 100.0);
            assert!(v > prev);
            prev = v;
        }
    }

    #[test]
    fn worker_plan_is_bounded_by_memory_not_by_frame_count() {
        let geom = PlaneGeometry::from_active(7032, 4688);
        // 400 frames must not give 400 workers.
        let plan = WorkerPlan::new(400, geom, 73_400_320);
        assert!(plan.chunks <= plan.workers);
        assert!(plan.per_worker_bytes * plan.chunks <= MEMORY_BUDGET_BYTES);
        assert!(plan.chunk_len * plan.chunks >= 400);
        // And a stack smaller than the worker count does not over-split.
        let small = WorkerPlan::new(3, geom, 73_400_320);
        assert!(small.chunks <= 3);
    }

    #[test]
    fn every_frame_is_covered_exactly_once_by_the_chunking() {
        let geom = PlaneGeometry::from_active(7032, 4688);
        for frames in [1usize, 2, 3, 22, 60, 199, 200] {
            let plan = WorkerPlan::new(frames, geom, 73_400_320);
            let mut seen = 0usize;
            for c in 0..plan.chunks {
                let start = c * plan.chunk_len;
                let end = ((c + 1) * plan.chunk_len).min(frames);
                assert!(start < end, "empty chunk for {frames} frames");
                seen += end - start;
            }
            assert_eq!(seen, frames);
        }
    }

    #[test]
    fn mean_and_sigma_match_the_population_definition() {
        let (m, s) = mean_and_sigma(&[2.0, 4.0, 4.0, 4.0, 5.0, 5.0, 7.0, 9.0]);
        assert!((m - 5.0).abs() < 1e-9);
        assert!((s - 2.0).abs() < 1e-9);
        assert_eq!(mean_and_sigma(&[]), (0.0, 0.0));
    }
}
