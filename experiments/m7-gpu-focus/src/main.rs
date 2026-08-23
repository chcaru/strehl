//! M7 — pricing the GPU fusion prize.
//!
//! SYNTHESIS risk 10: *"The GPU contribution format is being constrained by a
//! CPU measurement."* Fact 21 (196.8 ms/frame for ring-difference focus plus
//! fold) is scalar Rust. This crate ports the same measure to one `wgpu`
//! compute kernel, proves it agrees with the CPU, and measures what fusing it
//! with the merge is actually worth.
//!
//! Run `selftest` first, then `controls`, then `verify`, then `measure`.
//! Nothing downstream of a failing step is worth reading.

#[allow(dead_code)]
mod cpu;
mod decode;
mod gpu;

use std::path::{Path, PathBuf};
use std::time::Instant;

use rayon::prelude::*;

use cpu::{Noise, PlaneGeometry, Selection};
use decode::PackedFrame;
use gpu::{readback, run_jobs, stats, vram_mib, Gpu, Job, Params, Resident};

const MIB: f64 = 1024.0 * 1024.0;

fn main() {
    let args: Vec<String> = std::env::args().skip(1).collect();
    if args.is_empty() {
        eprintln!(
            "usage:\n  m7-gpu-focus selftest\n  m7-gpu-focus controls <dir> [--limit N]\n  \
             m7-gpu-focus verify <dir> [--limit N]\n  m7-gpu-focus measure <dir> [--limit N] [--reps R]\n  \
             m7-gpu-focus cpu <dir> [--limit N]"
        );
        std::process::exit(2);
    }
    let mode = args[0].clone();
    let dir = args.get(1).cloned().unwrap_or_default();
    let limit = flag_usize(&args, "--limit");
    let reps = flag_usize(&args, "--reps").unwrap_or(30);

    match mode.as_str() {
        "selftest" => selftest(),
        "controls" => controls(Path::new(&dir), limit),
        "verify" => verify(Path::new(&dir), limit),
        "measure" => measure(Path::new(&dir), limit, reps),
        "cpu" => cpu_only(Path::new(&dir), limit),
        other => {
            eprintln!("unknown mode {other}");
            std::process::exit(2);
        }
    }
}

fn flag_usize(args: &[String], name: &str) -> Option<usize> {
    args.iter()
        .position(|a| a == name)
        .and_then(|i| args.get(i + 1))
        .and_then(|v| v.parse().ok())
}

// ---------------------------------------------------------------------------
// shared helpers
// ---------------------------------------------------------------------------

fn noise_for(iso: f32) -> Noise {
    Noise {
        gain_dn_per_e: cpu::gain_dn_per_e(iso),
        read_noise_e: cpu::read_noise_e(iso),
    }
}

fn params_for(f: &PackedFrame, k: u32, noise: &Noise) -> Params {
    let g = f.geometry();
    Params {
        plane_w: g.width as u32,
        plane_h: g.height as u32,
        row_words: f.row_words as u32,
        frame_index: k,
        black: f.black,
        gain: noise.gain_dn_per_e,
        read_noise_e: noise.read_noise_e,
        sigma_eps: cpu::SIGMA_EPS,
    }
}

/// CPU focus field for one frame, using the copied `strehl-core` code path.
fn cpu_focus(f: &PackedFrame, noise: &Noise, inner_r: usize, outer_r: usize) -> Vec<f32> {
    let g = f.geometry();
    let mut luma = vec![0.0f32; g.pixels()];
    cpu::green_luma(f.samples(), f.active_w, g, f.black, &mut luma);
    let mut field = cpu::FocusField::new(g);
    field.compute_radii(&luma, noise, inner_r, outer_r);
    field.values().to_vec()
}

fn load_stack(dir: &Path, limit: Option<usize>) -> (Vec<PackedFrame>, Noise) {
    let paths = decode::list_arw(dir, limit).unwrap_or_else(|e| {
        eprintln!("{e}");
        std::process::exit(1);
    });
    println!("decoding {} frames from {}", paths.len(), dir.display());
    let t = Instant::now();
    let frames: Vec<PackedFrame> = paths
        .par_iter()
        .map(|p| decode::decode(p).unwrap_or_else(|e| panic!("{e}")))
        .collect();
    let secs = t.elapsed().as_secs_f64();
    let f0 = &frames[0];
    println!(
        "  decoded in {:.3} s ({:.1} ms/frame, rayon across files)",
        secs,
        1000.0 * secs / frames.len() as f64
    );
    println!(
        "  camera {} | active {}x{} | plane {}x{} | black {} white {} | ISO {:?}",
        f0.camera,
        f0.active_w,
        f0.active_h,
        f0.geometry().width,
        f0.geometry().height,
        f0.black,
        f0.white,
        f0.iso
    );
    println!(
        "  packed active area {:.2} MiB/frame, {:.3} GiB for the stack (padding excluded, rule 7)",
        f0.bytes() as f64 / MIB,
        (f0.bytes() * frames.len()) as f64 / MIB / 1024.0
    );
    for (k, f) in frames.iter().enumerate() {
        assert_eq!(f.geometry(), f0.geometry(), "frame {k} geometry differs");
        assert_eq!(f.black, f0.black, "frame {k} black level differs");
        assert_eq!(f.iso, f0.iso, "frame {k} ISO differs");
    }
    let iso = f0.iso.expect("no ISO tag: the noise model would be a guess");
    (frames, noise_for(iso))
}

fn resident_for(gpu: &Gpu, frames: &[PackedFrame], noise: &Noise, with_volume: bool) -> Resident {
    let words: Vec<&[u32]> = frames.iter().map(|f| f.words.as_slice()).collect();
    let params: Vec<Params> = frames
        .iter()
        .enumerate()
        .map(|(k, f)| params_for(f, k as u32, noise))
        .collect();
    Resident::new(
        gpu,
        frames[0].geometry(),
        frames[0].row_words as u32,
        &words,
        &params,
        with_volume,
    )
}

struct Pipelines {
    fused: wgpu::ComputePipeline,
    focus_write: wgpu::ComputePipeline,
    merge_only: wgpu::ComputePipeline,
    reset: wgpu::ComputePipeline,
    null: wgpu::ComputePipeline,
    read: wgpu::ComputePipeline,
    copy: wgpu::ComputePipeline,
    fused2: wgpu::ComputePipeline,
    focus_write_b: wgpu::ComputePipeline,
    fused_fast: wgpu::ComputePipeline,
    focus_write_fast: wgpu::ComputePipeline,
}

impl Pipelines {
    fn new(gpu: &Gpu) -> Self {
        Self {
            fused: gpu.pipeline(&gpu.m_a, "focus_merge_fused"),
            focus_write: gpu.pipeline(&gpu.m_a, "focus_write"),
            merge_only: gpu.pipeline(&gpu.m_a, "merge_only"),
            reset: gpu.pipeline(&gpu.m_a, "reset_kernel"),
            null: gpu.pipeline(&gpu.m_a, "null_kernel"),
            read: gpu.pipeline(&gpu.m_a, "read_kernel"),
            copy: gpu.pipeline(&gpu.m_a, "copy_kernel"),
            fused2: gpu.pipeline(&gpu.m_f, "focus2_merge_fused"),
            focus_write_b: gpu.pipeline(&gpu.m_b, "focus_write_b"),
            fused_fast: gpu.pipeline(&gpu.m_fast, "focus_merge_fused"),
            focus_write_fast: gpu.pipeline(&gpu.m_fast, "focus_write"),
        }
    }
}

fn reset_selection(gpu: &Gpu, res: &Resident, p: &Pipelines) {
    let groups = res.grid_linear(res.geom.pixels() as u64);
    run_jobs(gpu, res, &[Job::Linear(&p.reset, &res.bg_stream[0], groups)]);
}

// ---------------------------------------------------------------------------
// selftest
// ---------------------------------------------------------------------------

/// A synthetic packed frame: deterministic RGGB content over an
/// `active_w x active_h` active area, no padding.
fn synthetic_frame(
    active_w: usize,
    active_h: usize,
    seed: u32,
    f: impl Fn(usize, usize) -> u16,
) -> PackedFrame {
    let row_words = active_w / 2;
    let mut words = vec![0u32; row_words * active_h];
    for y in 0..active_h {
        for j in 0..row_words {
            let a = f(2 * j, y) as u32;
            let b = f(2 * j + 1, y) as u32;
            words[y * row_words + j] = a | (b << 16);
        }
    }
    PackedFrame {
        words,
        active_w,
        active_h,
        row_words,
        black: 512.0,
        white: 15360.0,
        iso: Some(100.0),
        camera: format!("SYNTHETIC-{seed}"),
        path: PathBuf::from("synthetic"),
    }
}

fn selftest() {
    let mut failures = 0usize;

    println!("== group 1: the exactness claim the kernel rests on ==");
    // Every green luma value is a multiple of 0.5 in [0, 14848]; a 7x7 sum of
    // them is at most 727552, and every multiple of 0.5 below 2^22 is exact in
    // f32. If this fails, the kernel's numerics argument is void.
    let mut rng = 0x1234_5678u32;
    let mut next = move || {
        rng ^= rng << 13;
        rng ^= rng >> 17;
        rng ^= rng << 5;
        rng
    };
    let mut worst = 0.0f64;
    for _ in 0..200_000 {
        let vals: Vec<f32> = (0..49).map(|_| (next() % 29697) as f32 * 0.5).collect();
        let s32: f32 = vals.iter().fold(0.0f32, |a, b| a + b);
        let s64: f64 = vals.iter().map(|v| *v as f64).sum();
        worst = worst.max((s32 as f64 - s64).abs());
    }
    report(
        &mut failures,
        "f32 accumulation of 49 luma samples is exact",
        worst == 0.0,
        format!("worst |f32 - f64| over 200000 draws = {worst:e}"),
    );

    let gpu = Gpu::new();
    println!(
        "  device: {} ({}), timestamp period {} ns",
        gpu.adapter_name, gpu.backend, gpu.ts_period_ns
    );
    let p = Pipelines::new(&gpu);
    println!("  all pipelines compiled (naga accepted every entry point)");

    // ---- group 2: flat plane --------------------------------------------
    println!("== group 2: a flat plane has zero focus everywhere, borders included ==");
    let flat = synthetic_frame(64, 48, 0, |_, _| 4512);
    let noise = noise_for(100.0);
    let (gflat, cflat) = focus_pair(&gpu, &p, &flat, &noise);
    let maxg = gflat.iter().cloned().fold(0.0f32, f32::max);
    let maxc = cflat.iter().cloned().fold(0.0f32, f32::max);
    report(
        &mut failures,
        "flat plane -> zero focus (GPU)",
        maxg == 0.0,
        format!("max GPU focus {maxg:e} (CPU {maxc:e})"),
    );

    // ---- group 3: agreement with the CPU on real structure ---------------
    println!("== group 3: GPU vs CPU vs f64 truth on structured synthetic data ==");
    let structured = synthetic_frame(256, 192, 1, |x, y| {
        let bar = if (x / 7 + y / 5) % 3 == 0 { 2600 } else { 700 };
        let ramp = (x * 11 + y * 3) % 900;
        (512 + bar + ramp) as u16
    });
    let (g, c) = focus_pair(&gpu, &p, &structured, &noise);
    let geom = structured.geometry();
    let mut luma = vec![0.0f32; geom.pixels()];
    cpu::green_luma(
        structured.samples(),
        structured.active_w,
        geom,
        structured.black,
        &mut luma,
    );
    let truth = exact_focus_par(&luma, geom, &noise, cpu::INNER_RADIUS, cpu::OUTER_RADIUS);
    // The parallel f64 reference is what `verify` runs on full frames. Check it
    // against the serial one here, so the expensive path is not itself an
    // unverified assumption.
    let truth_serial =
        cpu::exact_focus_f64(&luma, geom, &noise, cpu::INNER_RADIUS, cpu::OUTER_RADIUS);
    report(
        &mut failures,
        "the parallel f64 reference equals the serial one",
        truth == truth_serial,
        format!(
            "{} of {} values differ",
            truth
                .iter()
                .zip(&truth_serial)
                .filter(|(a, b)| a != b)
                .count(),
            truth.len()
        ),
    );
    let rep = compare_against_truth(&g, &c, &truth);
    report(
        &mut failures,
        "GPU vs CPU agreement",
        rep.max_rel_gc < 1e-5,
        format!(
            "{:.4}% bit-identical, max |dGPU-CPU| {:.3e}, max rel {:.3e}",
            100.0 * rep.identical_frac,
            rep.max_abs_gc,
            rep.max_rel_gc
        ),
    );
    report(
        &mut failures,
        "GPU is no further from f64 truth than the CPU is",
        rep.rms_gpu <= rep.rms_cpu * 1.05 + 1e-12,
        format!(
            "RMS vs truth: GPU {:.4e}, CPU {:.4e}; worst: GPU {:.3e}, CPU {:.3e}",
            rep.rms_gpu, rep.rms_cpu, rep.max_gpu, rep.max_cpu
        ),
    );
    // The same kernel with the raw fp32 divide, to demonstrate that the
    // division -- not the accumulation -- is what costs the agreement.
    let g_fast = gpu_focus_with(&gpu, &p.focus_write_fast, &structured, &noise);
    let rep_fast = compare_against_truth(&g_fast, &c, &truth);
    report(
        &mut failures,
        "the raw fp32 divide is measurably worse (diagnosis check)",
        rep_fast.max_abs_gc > rep.max_abs_gc,
        format!(
            "raw divide: {:.4}% identical, max |d| {:.3e}; refined: {:.4}% identical, max |d| {:.3e}",
            100.0 * rep_fast.identical_frac,
            rep_fast.max_abs_gc,
            100.0 * rep.identical_frac,
            rep.max_abs_gc
        ),
    );

    // ---- group 4: the ranking properties focus.rs asserts ----------------
    println!("== group 4: the ranking properties `focus.rs` tests, re-asserted on the GPU ==");
    let sharp = synthetic_frame(64, 64, 2, |x, _| if x >= 32 { 3512 } else { 2512 });
    let soft = synthetic_frame(64, 64, 3, |x, _| {
        let t = ((x as f32 - 26.0) / 12.0).clamp(0.0, 1.0);
        (2512.0 + 1000.0 * t) as u16
    });
    let (gs, _) = focus_pair(&gpu, &p, &sharp, &noise);
    let (gf, _) = focus_pair(&gpu, &p, &soft, &noise);
    let peak = |v: &[f32]| v.iter().cloned().fold(f32::MIN, f32::max);
    report(
        &mut failures,
        "a sharper edge scores higher than a blurred one",
        peak(&gs) > peak(&gf),
        format!("sharp {:.4} vs soft {:.4}", peak(&gs), peak(&gf)),
    );
    let dark = synthetic_frame(64, 64, 4, |x, _| if x % 16 == 8 { 812 } else { 712 });
    let bright = synthetic_frame(64, 64, 5, |x, _| if x % 16 == 8 { 12612 } else { 12512 });
    let (gd, _) = focus_pair(&gpu, &p, &dark, &noise);
    let (gb, _) = focus_pair(&gpu, &p, &bright, &noise);
    report(
        &mut failures,
        "the same contrast scores lower at a higher signal level",
        peak(&gd) > peak(&gb),
        format!("dark {:.4} vs bright {:.4}", peak(&gd), peak(&gb)),
    );

    // ---- group 5: the merge, including the tie-break ---------------------
    println!("== group 5: the fused merge reproduces `Selection`, including ties ==");
    // A linear ramp would be a trap here: a symmetric box mean of a linear
    // function equals its centre value, so the ring difference is zero in the
    // interior and every interior pixel would tie. Use the structured pattern.
    let a = synthetic_frame(64, 48, 6, |x, y| {
        let bar = if (x / 7 + y / 5) % 3 == 0 { 2600 } else { 700 };
        (512 + bar + (x * 11 + y * 3) % 900) as u16
    });
    let mut b = a.clone_shallow();
    // Perturb only R (even x of even rows), which the focus measure never
    // reads, so focus ties everywhere but the winning quad is identifiable.
    // 60000 is outside the range the generator can produce, so a match can
    // only have come from frame 1.
    const SENTINEL: u32 = 60000;
    for y in (0..b.active_h).step_by(2) {
        for j in 0..b.row_words {
            let w = b.words[y * b.row_words + j];
            b.words[y * b.row_words + j] = (w & 0xffff_0000) | SENTINEL;
        }
    }
    let tie_frames = vec![a.clone_shallow(), b];
    let res_tie = resident_for(&gpu, &tie_frames, &noise, false);
    reset_selection(&gpu, &res_tie, &p);
    let jobs: Vec<Job> = (0..tie_frames.len())
        .map(|k| Job::Tile(&p.fused, &res_tie.bg_stream[k]))
        .collect();
    run_jobs(&gpu, &res_tie, &jobs);
    let idx: Vec<u32> =
        bytemuck::cast_slice(&readback(&gpu, &res_tie.sel_index, res_tie.plane_bytes)).to_vec();
    let w0: Vec<u32> =
        bytemuck::cast_slice(&readback(&gpu, &res_tie.sel_w0, res_tie.plane_bytes)).to_vec();
    report(
        &mut failures,
        "every tie goes to the lower frame index",
        idx.iter().all(|v| *v == 0),
        format!(
            "{} of {} pixels won by frame 0",
            idx.iter().filter(|v| **v == 0).count(),
            idx.len()
        ),
    );
    report(
        &mut failures,
        "the winning quad is copied from the winning frame",
        w0.iter().all(|w| (w & 0xffff) != SENTINEL),
        "R channel never came from frame 1".to_string(),
    );

    // A strictly sharper second frame must take (almost) everything.
    let mut c = a.clone_shallow();
    for y in 0..c.active_h {
        for j in 0..c.row_words {
            let w = c.words[y * c.row_words + j];
            let boost = |v: u32| 512 + (v.saturating_sub(512) * 2).min(14848);
            c.words[y * c.row_words + j] = boost(w & 0xffff) | (boost(w >> 16) << 16);
        }
    }
    let sharp_frames = vec![a.clone_shallow(), c];
    let res2 = resident_for(&gpu, &sharp_frames, &noise, false);
    reset_selection(&gpu, &res2, &p);
    let jobs2: Vec<Job> = (0..sharp_frames.len())
        .map(|k| Job::Tile(&p.fused, &res2.bg_stream[k]))
        .collect();
    run_jobs(&gpu, &res2, &jobs2);
    let idx2: Vec<u32> =
        bytemuck::cast_slice(&readback(&gpu, &res2.sel_index, res2.plane_bytes)).to_vec();
    let f2: Vec<f32> =
        bytemuck::cast_slice(&readback(&gpu, &res2.sel_focus, res2.plane_bytes)).to_vec();
    let won = idx2.iter().filter(|v| **v == 1).count();
    report(
        &mut failures,
        "a strictly sharper frame wins",
        won as f64 / idx2.len() as f64 > 0.95,
        format!("frame 1 won {:.2}%", 100.0 * won as f64 / idx2.len() as f64),
    );

    // The same two frames through the CPU `Selection`, for a direct match.
    let mut sel = Selection::new(sharp_frames[0].geometry());
    for (k, f) in sharp_frames.iter().enumerate() {
        let cf = cpu_focus(f, &noise, cpu::INNER_RADIUS, cpu::OUTER_RADIUS);
        sel.fold(k as u16, &f.words, f.row_words, &cf);
    }
    report(
        &mut failures,
        "GPU fused merge == CPU Selection::fold (winner index)",
        idx2.iter().zip(&sel.index).all(|(g, c)| *g as u16 == *c),
        format!(
            "{} differing pixels",
            idx2.iter()
                .zip(&sel.index)
                .filter(|(g, c)| **g as u16 != **c)
                .count()
        ),
    );

    // ---- group 6: fused and unfused must agree ---------------------------
    println!("== group 6: fusion is an implementation detail, not a different answer ==");
    let res3 = resident_for(&gpu, &sharp_frames, &noise, false);
    reset_selection(&gpu, &res3, &p);
    let groups = res3.grid_linear(res3.geom.pixels() as u64);
    let mut jobs3: Vec<Job> = Vec::new();
    for k in 0..sharp_frames.len() {
        jobs3.push(Job::Tile(&p.focus_write, &res3.bg_stream[k]));
        jobs3.push(Job::Linear(&p.merge_only, &res3.bg_stream[k], groups));
    }
    run_jobs(&gpu, &res3, &jobs3);
    let idx3: Vec<u32> =
        bytemuck::cast_slice(&readback(&gpu, &res3.sel_index, res3.plane_bytes)).to_vec();
    let f3: Vec<f32> =
        bytemuck::cast_slice(&readback(&gpu, &res3.sel_focus, res3.plane_bytes)).to_vec();
    report(
        &mut failures,
        "fused and unfused give identical winner maps",
        idx2 == idx3,
        format!(
            "{} differing pixels",
            idx2.iter().zip(&idx3).filter(|(a, b)| a != b).count()
        ),
    );
    report(
        &mut failures,
        "fused and unfused give bit-identical focus",
        f2.iter().zip(&f3).all(|(a, b)| a.to_bits() == b.to_bits()),
        format!(
            "{} differing pixels",
            f2.iter()
                .zip(&f3)
                .filter(|(a, b)| a.to_bits() != b.to_bits())
                .count()
        ),
    );

    // ---- group 7: the null control must really do nothing ----------------
    println!("== group 7: the null control writes nothing ==");
    let before = readback(&gpu, &res3.sel_focus, res3.plane_bytes);
    run_jobs(&gpu, &res3, &[Job::Tile(&p.null, &res3.bg_stream[0])]);
    let after = readback(&gpu, &res3.sel_focus, res3.plane_bytes);
    report(
        &mut failures,
        "null kernel leaves memory untouched",
        before == after,
        "selection buffer unchanged after a null dispatch".to_string(),
    );

    println!();
    if failures == 0 {
        println!("ALL SELF-TESTS PASSED");
    } else {
        println!("{failures} SELF-TEST(S) FAILED");
        std::process::exit(1);
    }
}

fn report(failures: &mut usize, name: &str, ok: bool, detail: String) {
    println!("  [{}] {name}: {detail}", if ok { "PASS" } else { "FAIL" });
    if !ok {
        *failures += 1;
    }
}

impl PackedFrame {
    fn clone_shallow(&self) -> PackedFrame {
        PackedFrame {
            words: self.words.clone(),
            active_w: self.active_w,
            active_h: self.active_h,
            row_words: self.row_words,
            black: self.black,
            white: self.white,
            iso: self.iso,
            camera: self.camera.clone(),
            path: self.path.clone(),
        }
    }
}

/// GPU focus field and CPU focus field for one frame, same radii, same input.
fn focus_pair(gpu: &Gpu, p: &Pipelines, f: &PackedFrame, noise: &Noise) -> (Vec<f32>, Vec<f32>) {
    let g = gpu_focus_with(gpu, &p.focus_write, f, noise);
    let c = cpu_focus(f, noise, cpu::INNER_RADIUS, cpu::OUTER_RADIUS);
    (g, c)
}

fn gpu_focus_with(
    gpu: &Gpu,
    pipeline: &wgpu::ComputePipeline,
    f: &PackedFrame,
    noise: &Noise,
) -> Vec<f32> {
    let frames = std::slice::from_ref(f);
    let res = resident_for(gpu, frames, noise, false);
    run_jobs(gpu, &res, &[Job::Tile(pipeline, &res.bg_stream[0])]);
    bytemuck::cast_slice(&readback(gpu, &res.focus_io, res.plane_bytes)).to_vec()
}

struct TruthReport {
    identical_frac: f64,
    max_abs_gc: f64,
    max_rel_gc: f64,
    rms_gpu: f64,
    rms_cpu: f64,
    max_gpu: f64,
    max_cpu: f64,
}

fn compare_against_truth(g: &[f32], c: &[f32], truth: &[f64]) -> TruthReport {
    let n = g.len();
    let mut identical = 0usize;
    let (mut max_abs, mut max_rel) = (0.0f64, 0.0f64);
    let (mut sg, mut sc) = (0.0f64, 0.0f64);
    let (mut mg, mut mc) = (0.0f64, 0.0f64);
    for i in 0..n {
        if g[i].to_bits() == c[i].to_bits() {
            identical += 1;
        }
        let d = (g[i] as f64 - c[i] as f64).abs();
        max_abs = max_abs.max(d);
        let scale = (g[i].abs().max(c[i].abs()) as f64).max(1e-12);
        max_rel = max_rel.max(d / scale);
        let eg = (g[i] as f64 - truth[i]).abs();
        let ec = (c[i] as f64 - truth[i]).abs();
        sg += eg * eg;
        sc += ec * ec;
        mg = mg.max(eg);
        mc = mc.max(ec);
    }
    TruthReport {
        identical_frac: identical as f64 / n as f64,
        max_abs_gc: max_abs,
        max_rel_gc: max_rel,
        rms_gpu: (sg / n as f64).sqrt(),
        rms_cpu: (sc / n as f64).sqrt(),
        max_gpu: mg,
        max_cpu: mc,
    }
}

/// Independent f64 reference: naive clamped gather, no separable trick, no
/// running sums. Written from the documented border policy, not from the
/// implementation, so it can disagree with both.
fn exact_focus_par(
    luma: &[f32],
    geom: PlaneGeometry,
    noise: &Noise,
    inner_r: usize,
    outer_r: usize,
) -> Vec<f64> {
    let (w, h) = (geom.width, geom.height);
    let mut out = vec![0.0f64; geom.pixels()];
    let g = noise.gain_dn_per_e as f64;
    let read_dn = noise.read_noise_e as f64 * g;
    out.par_chunks_mut(w).enumerate().for_each(|(py, row)| {
        let mean = |px: usize, py: usize, r: usize| -> f64 {
            let x0 = px.saturating_sub(r);
            let x1 = (px + r).min(w - 1);
            let y0 = py.saturating_sub(r);
            let y1 = (py + r).min(h - 1);
            let mut sum = 0.0f64;
            let mut n = 0u32;
            for yy in y0..=y1 {
                let base = yy * w;
                for xx in x0..=x1 {
                    sum += luma[base + xx] as f64;
                    n += 1;
                }
            }
            sum / n as f64
        };
        for (px, o) in row.iter_mut().enumerate() {
            let ring = (mean(px, py, inner_r) - mean(px, py, outer_r)).abs();
            let s = (luma[py * w + px] as f64).max(0.0);
            let var = g * s + read_dn * read_dn;
            let sigma = (0.5 * var).sqrt().max(cpu::SIGMA_EPS as f64);
            *o = ring / sigma;
        }
    });
    out
}

// ---------------------------------------------------------------------------
// controls
// ---------------------------------------------------------------------------

fn controls(dir: &Path, limit: Option<usize>) {
    let (frames, noise) = load_stack(dir, limit.or(Some(4)));
    let gpu = Gpu::new();
    println!("device: {} ({})", gpu.adapter_name, gpu.backend);
    let (before, _) = vram_mib();
    let res = resident_for(&gpu, &frames, &noise, false);
    let p = Pipelines::new(&gpu);
    let (after, ours) = vram_mib();
    println!(
        "VRAM: {before:?} MiB used before allocation, {after:?} MiB after, {ours:?} MiB attributed to this process"
    );

    let reps = 50usize;
    let bytes_frame = res.frame_bytes as f64;
    let words = res.frame_bytes / 4;

    // -- null: dispatch overhead, same grid as the focus kernel ------------
    let mut null_gpu_v = Vec::new();
    let mut null_wall_v = Vec::new();
    for i in 0..reps + 3 {
        let (w, g) = run_jobs(&gpu, &res, &[Job::Tile(&p.null, &res.bg_stream[0])]);
        if i >= 3 {
            null_gpu_v.push(g);
            null_wall_v.push(w);
        }
    }
    let (gx, gy) = res.grid_2d();
    println!("\n-- NULL control: one dispatch, {gx}x{gy} workgroups, zero memory traffic");
    println!("   gpu  ms: {}", stats(&null_gpu_v));
    println!("   wall ms: {}", stats(&null_wall_v));
    let null_gpu = stats(&null_gpu_v).median;

    // -- D2D bandwidth via the copy engine ---------------------------------
    let copies = 16usize;
    let mut d2d = Vec::new();
    for i in 0..reps + 3 {
        let jobs: Vec<Job> = (0..copies)
            .map(|_| Job::Copy(&res.frames[0], &res.scratch, res.frame_bytes))
            .collect();
        let (_, g) = run_jobs(&gpu, &res, &jobs);
        if i >= 3 {
            d2d.push(g);
        }
    }
    let s = stats(&d2d);
    let moved = copies as f64 * bytes_frame;
    println!(
        "\n-- D2D control: {copies} x copy_buffer_to_buffer of {:.2} MiB",
        bytes_frame / MIB
    );
    println!("   gpu ms: {s}");
    println!(
        "   payload {:.3} GiB -> {:.1} GB/s one-way, {:.1} GB/s counting read+write",
        moved / MIB / 1024.0,
        moved / (s.median / 1000.0) / 1e9,
        2.0 * moved / (s.median / 1000.0) / 1e9
    );
    let d2d_rw_gbs = 2.0 * moved / (s.median / 1000.0) / 1e9;

    // -- read kernel -------------------------------------------------------
    let groups = res.grid_linear(words);
    let mut rd = Vec::new();
    for i in 0..reps + 3 {
        let jobs: Vec<Job> = (0..res.n())
            .map(|k| Job::Linear(&p.read, &res.bg_stream[k], groups))
            .collect();
        let (_, g) = run_jobs(&gpu, &res, &jobs);
        if i >= 3 {
            rd.push(g);
        }
    }
    let s = stats(&rd);
    let read_bytes = res.n() as f64 * bytes_frame;
    println!("\n-- READ control: every word of {} frames read once", res.n());
    println!("   gpu ms: {s}");
    println!(
        "   {:.3} GiB read -> {:.1} GB/s | predicted from the D2D rate {:.3} ms, measured {:.3} ms",
        read_bytes / MIB / 1024.0,
        read_bytes / (s.median / 1000.0) / 1e9,
        1000.0 * read_bytes / (d2d_rw_gbs * 1e9),
        s.median
    );

    // -- copy kernel: read + write -----------------------------------------
    let mut cp = Vec::new();
    for i in 0..reps + 3 {
        let jobs: Vec<Job> = (0..res.n())
            .map(|k| Job::Linear(&p.copy, &res.bg_stream[k], groups))
            .collect();
        let (_, g) = run_jobs(&gpu, &res, &jobs);
        if i >= 3 {
            cp.push(g);
        }
    }
    let s = stats(&cp);
    let cp_bytes = 2.0 * res.n() as f64 * bytes_frame;
    println!(
        "\n-- COPY control: every word of {} frames read and written",
        res.n()
    );
    println!("   gpu ms: {s}");
    println!(
        "   {:.3} GiB moved -> {:.1} GB/s | predicted {:.3} ms, measured {:.3} ms, ratio {:.3}",
        cp_bytes / MIB / 1024.0,
        cp_bytes / (s.median / 1000.0) / 1e9,
        1000.0 * cp_bytes / (d2d_rw_gbs * 1e9),
        s.median,
        s.median / (1000.0 * cp_bytes / (d2d_rw_gbs * 1e9))
    );
    println!(
        "   CAVEAT: the destination is one {:.2} MiB buffer, which fits in the 5090's 96 MiB L2, \n\
         \x20  so the write half may never reach DRAM. The read half ({:.3} GiB across {} distinct\n\
         \x20  buffers) cannot be cached, and gives a DRAM-traffic floor of {:.1} GB/s. Use the\n\
         \x20  READ control, not this one, as the bandwidth reference for the focus kernel.",
        bytes_frame / MIB,
        read_bytes / MIB / 1024.0,
        res.n(),
        read_bytes / (s.median / 1000.0) / 1e9
    );

    // -- H2D upload ---------------------------------------------------------
    let mut up = Vec::new();
    for _ in 0..10 {
        let t0 = Instant::now();
        for (k, f) in frames.iter().enumerate() {
            gpu.queue
                .write_buffer(&res.frames[k], 0, bytemuck::cast_slice(&f.words));
        }
        gpu.queue.submit([]);
        gpu.device.poll(wgpu::PollType::wait_indefinitely()).unwrap();
        up.push(t0.elapsed().as_secs_f64() * 1000.0);
    }
    let s = stats(&up);
    let up_bytes = res.n() as f64 * bytes_frame;
    println!(
        "\n-- H2D control (a): {} frames uploaded with queue.write_buffer",
        res.n()
    );
    println!("   wall ms: {s}");
    println!(
        "   {:.3} GiB -> {:.1} GB/s, {:.3} ms per {:.2} MiB frame",
        up_bytes / MIB / 1024.0,
        up_bytes / (s.median / 1000.0) / 1e9,
        s.median / res.n() as f64,
        bytes_frame / MIB
    );

    // (b) The same bytes through a persistent mapped staging buffer, which is
    // what a real pipeline would use. `write_buffer` goes via wgpu's staging
    // belt and charges an extra CPU memcpy; this measures the PCIe path.
    let stage = gpu.device.create_buffer(&wgpu::BufferDescriptor {
        label: Some("h2d-stage"),
        size: res.frame_bytes,
        usage: wgpu::BufferUsages::MAP_WRITE | wgpu::BufferUsages::COPY_SRC,
        mapped_at_creation: false,
    });
    let mut up2 = Vec::new();
    let mut memcpy_ms = Vec::new();
    for _ in 0..10 {
        let mut total = 0.0;
        let mut mem = 0.0;
        for (k, f) in frames.iter().enumerate() {
            stage.map_async(wgpu::MapMode::Write, .., |_| {});
            gpu.device.poll(wgpu::PollType::wait_indefinitely()).unwrap();
            let t_m = Instant::now();
            stage
                .get_mapped_range_mut(..)
                .unwrap()
                .copy_from_slice(bytemuck::cast_slice(&f.words));
            mem += t_m.elapsed().as_secs_f64() * 1000.0;
            stage.unmap();
            let t0 = Instant::now();
            let mut enc = gpu.device.create_command_encoder(&Default::default());
            enc.copy_buffer_to_buffer(&stage, 0, &res.frames[k], 0, res.frame_bytes);
            gpu.queue.submit([enc.finish()]);
            gpu.device.poll(wgpu::PollType::wait_indefinitely()).unwrap();
            total += t0.elapsed().as_secs_f64() * 1000.0;
        }
        up2.push(total);
        memcpy_ms.push(mem);
    }
    let s2 = stats(&up2);
    let sm = stats(&memcpy_ms);
    println!(
        "\n-- H2D control (b): the same {} frames through a mapped staging buffer",
        res.n()
    );
    println!("   PCIe copy wall ms: {s2}");
    println!("   host memcpy into the mapping, wall ms: {sm}");
    println!(
        "   {:.3} GiB -> {:.1} GB/s for the buffer-to-buffer copy alone ({:.3} ms per {:.2} MiB \n\
         \x20  frame). That rate is far above PCIe 5.0 x16 (~63 GB/s), so the mapped staging\n\
         \x20  buffer is device-local host-visible (ReBAR): the host memcpy *is* the PCIe\n\
         \x20  transfer, at {:.1} GB/s, and the copy that follows is device-to-device.",
        up_bytes / MIB / 1024.0,
        up_bytes / (s2.median / 1000.0) / 1e9,
        s2.median / res.n() as f64,
        bytes_frame / MIB,
        up_bytes / (sm.median / 1000.0) / 1e9
    );
    println!(
        "   END TO END through wgpu: {:.1} ms for the stack ({:.1} GB/s), against fact 10's \n\
         \x20  56.9 GB/s H2D measured with CUDA. wgpu exposes no pinned-host + copy-engine path,\n\
         \x20  so this is an API ceiling, not a hardware one.",
        sm.median + s2.median,
        up_bytes / ((sm.median + s2.median) / 1000.0) / 1e9
    );

    println!("\nnull-kernel floor (median GPU ms per dispatch): {null_gpu:.4}");
    let (_, ours) = vram_mib();
    println!("VRAM attributed to this process at exit: {ours:?} MiB");
}

// ---------------------------------------------------------------------------
// verify
// ---------------------------------------------------------------------------

fn verify(dir: &Path, limit: Option<usize>) {
    let (frames, noise) = load_stack(dir, limit);
    let geom = frames[0].geometry();
    let gpu = Gpu::new();
    let p = Pipelines::new(&gpu);
    let res = resident_for(&gpu, &frames, &noise, false);
    let (_, ours) = vram_mib();
    println!(
        "device: {} ({}); VRAM attributed to this process {ours:?} MiB",
        gpu.adapter_name, gpu.backend
    );

    println!("\n== per-frame focus field: GPU vs CPU vs an independent f64 reference ==");
    println!("frame |  identical |   max |d|  |   max rel  | GPU RMS vs f64 | CPU RMS vs f64");
    let mut worst_rel = 0.0f64;
    let mut total_identical = 0u64;
    let mut total_px = 0u64;
    let mut worst_gpu = 0.0f64;
    let mut worst_cpu = 0.0f64;
    for (k, f) in frames.iter().enumerate() {
        run_jobs(&gpu, &res, &[Job::Tile(&p.focus_write, &res.bg_stream[k])]);
        let g: Vec<f32> =
            bytemuck::cast_slice(&readback(&gpu, &res.focus_io, res.plane_bytes)).to_vec();
        let c = cpu_focus(f, &noise, cpu::INNER_RADIUS, cpu::OUTER_RADIUS);
        let mut luma = vec![0.0f32; geom.pixels()];
        cpu::green_luma(f.samples(), f.active_w, geom, f.black, &mut luma);
        let truth = exact_focus_par(&luma, geom, &noise, cpu::INNER_RADIUS, cpu::OUTER_RADIUS);
        let rep = compare_against_truth(&g, &c, &truth);
        worst_rel = worst_rel.max(rep.max_rel_gc);
        worst_gpu = worst_gpu.max(rep.max_gpu);
        worst_cpu = worst_cpu.max(rep.max_cpu);
        total_identical += (rep.identical_frac * g.len() as f64).round() as u64;
        total_px += g.len() as u64;
        println!(
            "{k:5} | {:9.5}% | {:10.3e} | {:10.3e} | {:14.4e} | {:14.4e}",
            100.0 * rep.identical_frac,
            rep.max_abs_gc,
            rep.max_rel_gc,
            rep.rms_gpu,
            rep.rms_cpu
        );
    }
    println!(
        "\noverall: {:.6}% of {total_px} plane pixels bit-identical; worst relative GPU-CPU \
         difference {worst_rel:.3e}",
        100.0 * total_identical as f64 / total_px as f64
    );
    println!(
        "worst absolute error against the f64 reference: GPU {worst_gpu:.3e}, CPU {worst_cpu:.3e}"
    );

    println!("\n== the merge: GPU fused argmax vs the CPU `Selection` fold ==");
    reset_selection(&gpu, &res, &p);
    let jobs: Vec<Job> = (0..frames.len())
        .map(|k| Job::Tile(&p.fused, &res.bg_stream[k]))
        .collect();
    run_jobs(&gpu, &res, &jobs);
    let gidx: Vec<u32> =
        bytemuck::cast_slice(&readback(&gpu, &res.sel_index, res.plane_bytes)).to_vec();
    let gfoc: Vec<f32> =
        bytemuck::cast_slice(&readback(&gpu, &res.sel_focus, res.plane_bytes)).to_vec();
    let gw0: Vec<u32> = bytemuck::cast_slice(&readback(&gpu, &res.sel_w0, res.plane_bytes)).to_vec();
    let gw1: Vec<u32> = bytemuck::cast_slice(&readback(&gpu, &res.sel_w1, res.plane_bytes)).to_vec();

    let mut sel = Selection::new(geom);
    let mut fields: Vec<Vec<f32>> = Vec::with_capacity(frames.len());
    for (k, f) in frames.iter().enumerate() {
        let c = cpu_focus(f, &noise, cpu::INNER_RADIUS, cpu::OUTER_RADIUS);
        sel.fold(k as u16, &f.words, f.row_words, &c);
        fields.push(c);
    }

    let n = geom.pixels();
    let mut idx_diff = 0usize;
    let mut focus_diff = 0usize;
    let mut quad_diff = 0usize;
    let mut margins: Vec<f64> = Vec::new();
    for i in 0..n {
        if gidx[i] as u16 != sel.index[i] {
            idx_diff += 1;
            let mut v: Vec<f32> = fields.iter().map(|f| f[i]).collect();
            v.sort_by(|a, b| b.partial_cmp(a).unwrap());
            margins.push((v[0] - v[1]) as f64);
        }
        if gfoc[i].to_bits() != sel.focus[i].to_bits() {
            focus_diff += 1;
        }
        if gw0[i] != sel.w0[i] || gw1[i] != sel.w1[i] {
            quad_diff += 1;
        }
    }
    println!(
        "winner index : {idx_diff} of {n} differ ({:.6}%)",
        100.0 * idx_diff as f64 / n as f64
    );
    println!(
        "winning focus: {focus_diff} of {n} differ bitwise ({:.6}%)",
        100.0 * focus_diff as f64 / n as f64
    );
    println!(
        "winning quad : {quad_diff} of {n} differ ({:.6}%)",
        100.0 * quad_diff as f64 / n as f64
    );
    if !margins.is_empty() {
        let s = stats(&margins);
        println!("  top-2 focus margin at the disagreeing pixels: {s}");
        let mut sample: Vec<f32> = gfoc.iter().step_by(97).cloned().collect();
        sample.sort_by(|a, b| a.partial_cmp(b).unwrap());
        let median_focus = sample[sample.len() / 2] as f64;
        println!(
            "  the median winning focus value is {median_focus:.4}, so the contested margin is \
             {:.2e} of it",
            s.median / median_focus.max(1e-12)
        );
    }
    let mut green_diff = 0usize;
    let mut max_green = 0.0f64;
    for i in 0..n {
        let gg = 0.5 * (((gw0[i] >> 16) & 0xffff) as f64 + (gw1[i] & 0xffff) as f64);
        let cg = 0.5 * (((sel.w0[i] >> 16) & 0xffff) as f64 + (sel.w1[i] & 0xffff) as f64);
        if gg != cg {
            green_diff += 1;
            max_green = max_green.max((gg - cg).abs());
        }
    }
    println!(
        "emitted green: {green_diff} of {n} pixels differ ({:.6}%), largest difference {max_green:.1} DN",
        100.0 * green_diff as f64 / n as f64
    );
}

// ---------------------------------------------------------------------------
// CPU baseline
// ---------------------------------------------------------------------------

struct CpuBaseline {
    per_frame_ms: Vec<f64>,
    serial_total_ms: f64,
    parallel_total_ms: Vec<f64>,
    threads: usize,
    chunks: usize,
}

/// Worker state for the parallel baseline, allocated *outside* the timed
/// region. 22 workers each need ~350 MiB of scratch; allocating that inside the
/// timer would measure the page-fault storm rather than the focus measure, and
/// would flatter the GPU.
struct Worker {
    sel: Selection,
    field: cpu::FocusField,
    luma: Vec<f32>,
}

fn cpu_baseline(frames: &[PackedFrame], noise: &Noise, reps: usize) -> CpuBaseline {
    let geom = frames[0].geometry();

    // Serial: one worker, exactly what a single `fold_one` does per frame.
    let mut sel = Selection::new(geom);
    let mut field = cpu::FocusField::new(geom);
    let mut luma = vec![0.0f32; geom.pixels()];
    // Touch every page once so the serial timing is not a first-touch
    // measurement either.
    cpu::green_luma(frames[0].samples(), frames[0].active_w, geom, frames[0].black, &mut luma);
    field.compute(&luma, noise);
    sel.fold(0, &frames[0].words, frames[0].row_words, field.values());
    let mut sel = Selection::new(geom);

    let mut per_frame_ms = Vec::new();
    let t_all = Instant::now();
    for (k, f) in frames.iter().enumerate() {
        let t = Instant::now();
        cpu::green_luma(f.samples(), f.active_w, geom, f.black, &mut luma);
        field.compute(&luma, noise);
        sel.fold(k as u16, &f.words, f.row_words, field.values());
        per_frame_ms.push(t.elapsed().as_secs_f64() * 1000.0);
    }
    let serial_total_ms = t_all.elapsed().as_secs_f64() * 1000.0;

    // Parallel: the shape `strehl-cli` runs -- chunks across rayon, one
    // Selection per worker, then absorb. Worker state is allocated and
    // first-touched before the clock starts.
    let threads = rayon::current_num_threads();
    let chunk = frames.len().div_ceil(threads.min(frames.len()));
    let chunks = frames.len().div_ceil(chunk);
    let mut workers: Vec<Worker> = (0..chunks)
        .map(|_| Worker {
            sel: Selection::new(geom),
            field: cpu::FocusField::new(geom),
            luma: vec![0.0f32; geom.pixels()],
        })
        .collect();
    for w in workers.iter_mut() {
        w.luma.fill(1.0);
        w.sel.focus.fill(f32::NEG_INFINITY);
    }

    let mut parallel_total_ms = Vec::new();
    for _ in 0..reps {
        for w in workers.iter_mut() {
            w.sel = Selection::new(geom);
        }
        let t_par = Instant::now();
        workers
            .par_iter_mut()
            .zip(frames.par_chunks(chunk))
            .enumerate()
            .for_each(|(ci, (w, group))| {
                for (j, f) in group.iter().enumerate() {
                    let k = (ci * chunk + j) as u16;
                    cpu::green_luma(f.samples(), f.active_w, geom, f.black, &mut w.luma);
                    w.field.compute(&w.luma, noise);
                    w.sel.fold(k, &f.words, f.row_words, w.field.values());
                }
            });
        let mut merged = Selection::new(geom);
        for w in &workers {
            merged.absorb(&w.sel);
        }
        parallel_total_ms.push(t_par.elapsed().as_secs_f64() * 1000.0);
    }

    CpuBaseline {
        per_frame_ms,
        serial_total_ms,
        parallel_total_ms,
        threads,
        chunks,
    }
}

fn cpu_only(dir: &Path, limit: Option<usize>) {
    let (frames, noise) = load_stack(dir, limit);
    let b = cpu_baseline(&frames, &noise, 5);
    report_cpu(&b, frames.len());
}

fn report_cpu(b: &CpuBaseline, n: usize) {
    let s = stats(&b.per_frame_ms);
    let sp = stats(&b.parallel_total_ms);
    println!("\n== CPU baseline: green_luma + FocusField::compute + Selection::fold ==");
    println!("  per frame, single thread (ms): {s}");
    println!(
        "  serial total for {n} frames      : {:.1} ms ({:.1} ms/frame)",
        b.serial_total_ms,
        b.serial_total_ms / n as f64
    );
    println!(
        "  rayon, {} chunks on {} threads, buffers pre-allocated (ms): {sp}",
        b.chunks, b.threads
    );
    println!(
        "  best parallel wall clock: {:.1} ms for {n} frames ({:.1} ms/frame)",
        sp.min,
        sp.min / n as f64
    );
    println!(
        "  summed CPU time across workers: {:.1} ms -> {:.1} ms/frame, which is the quantity \n\
         \x20 fact 21 reports (per-frame CPU time under concurrency, not wall clock)",
        sp.median * b.chunks.min(b.threads) as f64,
        sp.median * b.chunks.min(b.threads) as f64 / n as f64
    );
}

// ---------------------------------------------------------------------------
// measure
// ---------------------------------------------------------------------------

type Row = (String, gpu::Stats, gpu::Stats, f64, f64);

/// Time one variant: one cold run, then `reps` warm runs. The selection is
/// reset before every run, outside the timed region, so no variant benefits
/// from a selection the previous run already filled in.
#[allow(clippy::too_many_arguments)]
fn run_variant(
    gpu: &Gpu,
    res: &Resident,
    p: &Pipelines,
    reps: usize,
    name: &str,
    jobs: &[Job],
    dispatches: usize,
    bytes: f64,
) -> Row {
    reset_selection(gpu, res, p);
    let (cold_wall, cold_gpu) = run_jobs(gpu, res, jobs);
    let mut gpu_ms = Vec::new();
    let mut wall_ms = Vec::new();
    for _ in 0..reps {
        reset_selection(gpu, res, p);
        let (w, g) = run_jobs(gpu, res, jobs);
        gpu_ms.push(g);
        wall_ms.push(w);
    }
    let sg = stats(&gpu_ms);
    let sw = stats(&wall_ms);
    println!("\n-- {name}");
    println!("   cold (first run after pipeline creation): gpu {cold_gpu:.3} ms, wall {cold_wall:.3} ms");
    println!("   warm gpu  ms: {sg}");
    println!("   warm wall ms: {sw}");
    println!(
        "   {dispatches} dispatch(es)/frame; essential traffic {:.3} GiB -> {:.1} GB/s achieved",
        bytes / MIB / 1024.0,
        bytes / (sg.median / 1000.0) / 1e9
    );
    (name.to_string(), sg, sw, cold_gpu, bytes)
}

fn measure(dir: &Path, limit: Option<usize>, reps: usize) {
    let (frames, noise) = load_stack(dir, limit);
    let n = frames.len();
    let geom = frames[0].geometry();

    let b = cpu_baseline(&frames, &noise, 5);
    report_cpu(&b, n);

    let gpu = Gpu::new();
    let (vram_before, _) = vram_mib();
    let res = resident_for(&gpu, &frames, &noise, true);
    let p = Pipelines::new(&gpu);
    let (vram_after, ours) = vram_mib();
    println!("\n== GPU ==");
    println!("device: {} ({})", gpu.adapter_name, gpu.backend);
    let modelled = (n as u64 * res.frame_bytes
        + 5 * res.plane_bytes
        + n as u64 * res.plane_bytes
        + res.frame_bytes) as f64
        / MIB;
    println!(
        "resident model: {n} frames x {:.2} MiB + 5 x {:.2} MiB selection/focus + {n} x {:.2} MiB \
         volume + {:.2} MiB scratch = {modelled:.0} MiB",
        res.frame_bytes as f64 / MIB,
        res.plane_bytes as f64 / MIB,
        res.plane_bytes as f64 / MIB,
        res.frame_bytes.max(res.plane_bytes) as f64 / MIB
    );
    println!("  nvidia-smi: {vram_before:?} MiB used before, {vram_after:?} MiB after, {ours:?} MiB ours");
    if let (Some(a), Some(bb)) = (vram_after, vram_before) {
        println!(
            "  delta {} MiB vs {modelled:.0} MiB modelled -- a delta far below the model means the \
             allocation spilled to system RAM (WDDM does not raise OOM)",
            a as i64 - bb as i64
        );
    }

    let groups_px = res.grid_linear(geom.pixels() as u64);
    let mut rows: Vec<(String, gpu::Stats, gpu::Stats, f64, f64)> = Vec::new();

    let fb = res.frame_bytes as f64;
    let pb = res.plane_bytes as f64;

    // Inline null and read controls, so the bandwidth model below is built from
    // numbers measured in this same process, on this same allocation.
    let mut nullv = Vec::new();
    for i in 0..23 {
        let (_, g) = run_jobs(&gpu, &res, &[Job::Tile(&p.null, &res.bg_stream[0])]);
        if i >= 3 {
            nullv.push(g);
        }
    }
    let null_floor_ms = stats(&nullv).median;
    let groups_w = res.grid_linear(res.frame_bytes / 4);
    let mut readv = Vec::new();
    for i in 0..23 {
        let jobs: Vec<Job> = (0..n)
            .map(|k| Job::Linear(&p.read, &res.bg_stream[k], groups_w))
            .collect();
        let (_, g) = run_jobs(&gpu, &res, &jobs);
        if i >= 3 {
            readv.push(g);
        }
    }
    let read_ms = stats(&readv).median;
    let read_gbs = n as f64 * fb / (read_ms / 1000.0) / 1e9;
    let (gx, gy) = res.grid_2d();
    println!("\n-- inline controls");
    println!("   NULL : one dispatch of {gx}x{gy} workgroups, no traffic: {}", stats(&nullv));
    println!("   READ : {n} frames read once: {}", stats(&readv));
    println!(
        "          {:.3} GiB -> {read_gbs:.1} GB/s (the bandwidth ceiling used in the model below)",
        n as f64 * fb / MIB / 1024.0
    );

    // A) fused: focus + merge in one dispatch per frame.
    {
        let jobs: Vec<Job> = (0..n)
            .map(|k| Job::Tile(&p.fused, &res.bg_stream[k]))
            .collect();
        rows.push(run_variant(
            &gpu,
            &res,
            &p,
            reps,
            "A  fused    (focus+merge, 1 dispatch/frame)",
            &jobs,
            1,
            n as f64 * (fb + 2.0 * pb),
        ));
    }
    // F) the same fused kernel with the raw fp32 divide instead of div_rn().
    //    The difference between A and F is the price of numerical exactness.
    {
        let jobs: Vec<Job> = (0..n)
            .map(|k| Job::Tile(&p.fused_fast, &res.bg_stream[k]))
            .collect();
        rows.push(run_variant(
            &gpu,
            &res,
            &p,
            reps,
            "F  fused/raw (variant A with the raw fp32 divide, not div_rn)",
            &jobs,
            1,
            n as f64 * (fb + 2.0 * pb),
        ));
    }
    // B) unfused streaming: focus written out, merge reads it back.
    {
        let mut jobs: Vec<Job> = Vec::new();
        for k in 0..n {
            jobs.push(Job::Tile(&p.focus_write, &res.bg_stream[k]));
            jobs.push(Job::Linear(&p.merge_only, &res.bg_stream[k], groups_px));
        }
        rows.push(run_variant(
            &gpu,
            &res,
            &p,
            reps,
            "B  unfused  (focus -> memory -> merge, 2 dispatches/frame)",
            &jobs,
            2,
            n as f64 * (fb + 4.0 * pb),
        ));
    }
    // C) full focus volume materialised, then merged.
    {
        let mut jobs: Vec<Job> = Vec::new();
        for k in 0..n {
            jobs.push(Job::Tile(&p.focus_write, &res.bg_vol[k]));
        }
        for k in 0..n {
            jobs.push(Job::Linear(&p.merge_only, &res.bg_vol[k], groups_px));
        }
        rows.push(run_variant(
            &gpu,
            &res,
            &p,
            reps,
            "C  volume   (all N focus fields resident, then merged)",
            &jobs,
            2,
            n as f64 * (fb + 4.0 * pb),
        ));
    }
    // D) two focus measures fused into one dispatch.
    {
        let jobs: Vec<Job> = (0..n)
            .map(|k| Job::Tile(&p.fused2, &res.bg_stream[k]))
            .collect();
        rows.push(run_variant(
            &gpu,
            &res,
            &p,
            reps,
            "D  fused2   (two measures + merge, 1 dispatch/frame)",
            &jobs,
            1,
            n as f64 * (fb + 2.0 * pb),
        ));
    }
    // E) the same two measures as separate passes over the stack.
    {
        let mut jobs: Vec<Job> = Vec::new();
        for k in 0..n {
            jobs.push(Job::Tile(&p.focus_write, &res.bg_stream[k]));
            jobs.push(Job::Tile(&p.focus_write_b, &res.bg_stream[k]));
            jobs.push(Job::Linear(&p.merge_only, &res.bg_stream[k], groups_px));
        }
        rows.push(run_variant(
            &gpu,
            &res,
            &p,
            reps,
            "E  unfused2 (two measures as two passes + merge, 3 dispatches/frame)",
            &jobs,
            3,
            n as f64 * (2.0 * fb + 6.0 * pb),
        ));
    }

    let mut up = Vec::new();
    for _ in 0..10 {
        let t0 = Instant::now();
        for (k, f) in frames.iter().enumerate() {
            gpu.queue
                .write_buffer(&res.frames[k], 0, bytemuck::cast_slice(&f.words));
        }
        gpu.queue.submit([]);
        gpu.device.poll(wgpu::PollType::wait_indefinitely()).unwrap();
        up.push(t0.elapsed().as_secs_f64() * 1000.0);
    }
    let su = stats(&up);
    println!("\n-- H2D upload of the whole stack");
    println!("   wall ms: {su}");
    println!(
        "   {:.3} GiB -> {:.1} GB/s",
        n as f64 * fb / MIB / 1024.0,
        n as f64 * fb / (su.median / 1000.0) / 1e9
    );

    println!("\n== summary (median warm GPU ms for {n} frames, {reps} reps) ==");
    for (name, sg, sw, cold, bytes) in &rows {
        println!(
            "{name:<58} gpu {:8.3}  wall {:8.3}  cold {:8.3}  {:7.1} GB/s",
            sg.median,
            sw.median,
            cold,
            bytes / (sg.median / 1000.0) / 1e9
        );
    }
    if rows.len() >= 5 {
        let fused = rows[0].1.median;
        let fast = rows[1].1.median;
        let unfused = rows[2].1.median;
        let volume = rows[3].1.median;
        let fused2 = rows[4].1.median;
        let unfused2 = rows[5].1.median;
        println!("\n== the fusion prize ==");
        println!(
            "prize 1, focus+merge     : {:.3} ms (unfused {unfused:.3} - fused {fused:.3}), {:.1}% of the unfused path",
            unfused - fused,
            100.0 * (unfused - fused) / unfused
        );
        println!(
            "prize 1b, vs full volume : {:.3} ms (volume {volume:.3} - fused {fused:.3})",
            volume - fused
        );
        println!(
            "prize 2, two measures    : {:.3} ms (unfused2 {unfused2:.3} - fused2 {fused2:.3}), {:.1}% of the unfused path",
            unfused2 - fused2,
            100.0 * (unfused2 - fused2) / unfused2
        );
        println!(
            "price of exactness       : {:.3} ms (div_rn {fused:.3} - raw divide {fast:.3}), \
             {:.2}% of variant A",
            fused - fast,
            100.0 * (fused - fast) / fused
        );
        println!(
            "\nCPU focus+fold for the same {n} frames: {:.1} ms serial, {:.1} ms best parallel \
             ({} chunks on {} threads)",
            b.serial_total_ms,
            stats(&b.parallel_total_ms).min,
            b.chunks,
            b.threads
        );
        println!(
            "GPU fused speedup vs serial CPU: {:.1}x; vs the best parallel CPU: {:.1}x",
            b.serial_total_ms / fused,
            stats(&b.parallel_total_ms).min / fused
        );

        // --- is it bandwidth bound? show the arithmetic, do not assert it ---
        let halo = 3u64;
        let tile_px = (gpu::TILE_W as u64 + 2 * halo) * (gpu::TILE_H as u64 + 2 * halo);
        let out_px = gpu::TILE_W as u64 * gpu::TILE_H as u64;
        let amp = tile_px as f64 / out_px as f64;
        let wgs = (geom.width as u64).div_ceil(gpu::TILE_W as u64)
            * (geom.height as u64).div_ceil(gpu::TILE_H as u64);
        let tile_bytes = wgs as f64 * tile_px as f64 * 8.0;
        println!("\n== bandwidth model for variant A (all DERIVED from the controls) ==");
        println!(
            "halo amplification: a {}x{} workgroup loads a {}x{} tile = {tile_px} plane pixels for \
             {out_px} outputs, i.e. {amp:.3}x",
            gpu::TILE_W,
            gpu::TILE_H,
            gpu::TILE_W as u64 + 2 * halo,
            gpu::TILE_H as u64 + 2 * halo
        );
        println!(
            "  tile loads      : {:.1} MiB/frame x {n} = {:.3} GiB",
            tile_bytes / MIB,
            n as f64 * tile_bytes / MIB / 1024.0
        );
        println!(
            "  selection reads : 2 x {:.1} MiB/frame x {n} = {:.3} GiB",
            pb / MIB,
            n as f64 * 2.0 * pb / MIB / 1024.0
        );
        let model_bytes = n as f64 * (tile_bytes + 2.0 * pb);
        println!(
            "  total (excluding winner writes) {:.3} GiB",
            model_bytes / MIB / 1024.0
        );
        println!(
            "  at the READ control's rate this is {:.3} ms; add {n} dispatches x the null floor \
             = {:.3} ms",
            model_bytes / (read_gbs * 1e9) * 1000.0,
            n as f64 * null_floor_ms
        );
        let predicted = model_bytes / (read_gbs * 1e9) * 1000.0 + n as f64 * null_floor_ms;
        println!(
            "  predicted {predicted:.3} ms vs measured {fused:.3} ms -> measured/predicted = \
             {:.3}",
            fused / predicted
        );
        println!(
            "  the kernel achieves {:.1} GB/s of memory-system traffic against a measured read \
             ceiling of {read_gbs:.1} GB/s, i.e. {:.0}% of it: BANDWIDTH BOUND.",
            model_bytes / (fused / 1000.0) / 1e9,
            100.0 * model_bytes / (fused / 1000.0) / 1e9 / read_gbs
        );
        println!(
            "\n  the prize itself is one extra round trip of the focus field: 2 x {:.1} MiB x {n} \
             = {:.3} GiB",
            pb / MIB,
            n as f64 * 2.0 * pb / MIB / 1024.0
        );
        let prize_pred = n as f64 * 2.0 * pb / (read_gbs * 1e9) * 1000.0 + n as f64 * null_floor_ms;
        println!(
            "  predicted {prize_pred:.3} ms vs measured {:.3} ms -> {:.3}",
            unfused - fused,
            (unfused - fused) / prize_pred
        );
    }
    let (_, ours) = vram_mib();
    println!("\nVRAM attributed to this process at exit: {ours:?} MiB");
}
