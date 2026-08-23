//! M8 — measuring decoder scratch as a quantity.
//!
//! `crates/strehl-cli/src/stack.rs` sizes its worker pool from
//! `per_worker_bytes = px * (14 + 12 + 4) + frame_bytes`, and `M2-rss-resolved.md`
//! showed that model under-counts the real per-worker cost by 13-24%. The
//! omitted term is believed to be the decoder's own scratch. This harness
//! isolates that term.
//!
//! Nothing here writes to `C:\dev\macro` or `D:\macro-dark-frames`. The only
//! files this program opens are opened read-only, by the decoder.
//!
//! Every mode emits CSV on stdout (a `#` line first, then rows) and commentary
//! on stderr, so a driver can redirect stdout and keep the log.

mod mem;

use std::path::{Path, PathBuf};
use std::sync::atomic::{AtomicU64, Ordering};
use std::sync::{Arc, Barrier};
use std::time::{Duration, Instant};

const MIB: f64 = 1024.0 * 1024.0;

/// Sensor geometry, MEASURED in M1. Used only to print the modelled figures
/// alongside the measured ones; nothing is derived from it.
const ACTIVE_W: usize = 7032;
const ACTIVE_H: usize = 4688;
const BUFFER_W: usize = 7168;
const BUFFER_H: usize = 5120;

fn frame_bytes_model() -> usize {
    BUFFER_W * BUFFER_H * 2
}

fn per_worker_bytes_model() -> usize {
    let px = (ACTIVE_W / 2) * (ACTIVE_H / 2);
    px * (14 + 12 + 4) + frame_bytes_model()
}

fn threads_env() -> String {
    std::env::var("RAYON_NUM_THREADS").unwrap_or_else(|_| "unset".into())
}

fn arw_paths(p: &Path, limit: Option<usize>) -> Vec<PathBuf> {
    if p.is_file() {
        return vec![p.to_path_buf()];
    }
    let mut v: Vec<PathBuf> = std::fs::read_dir(p)
        .unwrap_or_else(|e| panic!("reading {}: {e}", p.display()))
        .filter_map(|e| e.ok().map(|e| e.path()))
        .filter(|p| {
            p.extension()
                .and_then(|e| e.to_str())
                .map(|e| e.eq_ignore_ascii_case("arw"))
                .unwrap_or(false)
        })
        .collect();
    v.sort();
    if let Some(n) = limit {
        v.truncate(n);
    }
    assert!(!v.is_empty(), "no ARW files under {}", p.display());
    v
}

fn file_bytes(p: &Path) -> u64 {
    std::fs::metadata(p).map(|m| m.len()).unwrap_or(0)
}

/// Which corpus a run came from, so the darks can be told from the stacks in
/// the CSV without inferring it from file size.
fn set_name(p: &Path) -> String {
    let dir = if p.is_file() { p.parent().unwrap_or(p) } else { p };
    let leaf = dir
        .file_name()
        .map(|s| s.to_string_lossy().to_string())
        .unwrap_or_else(|| "?".into());
    let parent = dir
        .parent()
        .and_then(|q| q.file_name())
        .map(|s| s.to_string_lossy().to_string())
        .unwrap_or_default();
    if parent.contains("dark") {
        format!("dark-{leaf}")
    } else {
        leaf
    }
}

/// Write one byte per page so the pages are genuinely resident, and keep the
/// buffer alive across the call.
fn touch(buf: &mut [u8]) {
    let mut i = 0;
    while i < buf.len() {
        buf[i] = buf[i].wrapping_add(1);
        i += 4096;
    }
    std::hint::black_box(&buf[0]);
}

// ---------------------------------------------------------------------------
// selftest
// ---------------------------------------------------------------------------

struct Check {
    name: &'static str,
    ok: bool,
    detail: String,
}

fn selftest() {
    println!("#kind,name,planted_bytes,ws_delta_bytes,commit_delta_bytes,ratio_ws,ratio_commit,verdict");
    let mut checks: Vec<Check> = Vec::new();

    // S0 -- do the counters mean anything at all?
    let c = mem::counters();
    let ok = c.cb as usize == std::mem::size_of::<mem::Pmc>()
        && c.working_set_size > 0
        && c.private_usage > 0
        && c.peak_working_set_size >= c.working_set_size
        && c.peak_pagefile_usage >= c.pagefile_usage;
    checks.push(Check {
        name: "S0 counters self-consistent",
        ok,
        detail: format!(
            "ws {:.1} MiB, commit {:.1} MiB, kernel peak ws {:.1} MiB",
            c.working_set_size as f64 / MIB,
            c.private_usage as f64 / MIB,
            c.peak_working_set_size as f64 / MIB
        ),
    });

    let s = mem::Sampler::start(Duration::from_micros(500));

    // S1 -- the null. Nothing happens for 2 s; how much does the instrument
    // wander on its own? Every later delta must clear this band.
    let (base_ws, base_commit) = s.reset();
    let t = Instant::now();
    let mut min_ws = base_ws;
    let mut min_commit = base_commit;
    while t.elapsed() < Duration::from_secs(2) {
        let (w, c) = mem::now();
        min_ws = min_ws.min(w);
        min_commit = min_commit.min(c);
        std::thread::sleep(Duration::from_millis(2));
    }
    let (pw, pc) = s.peak();
    let drift_ws = pw as i64 - min_ws as i64;
    let drift_commit = pc as i64 - min_commit as i64;
    let noise_floor = drift_ws.max(drift_commit).max(0) as u64;
    println!(
        "selftest,S1 idle drift (null),0,{},{},,,{}",
        drift_ws,
        drift_commit,
        if noise_floor < 8 << 20 { "PASS" } else { "FAIL" }
    );
    checks.push(Check {
        name: "S1 idle drift (null)",
        ok: noise_floor < 8 << 20,
        detail: format!(
            "ws {:.2} MiB, commit {:.2} MiB over 2 s of doing nothing",
            drift_ws as f64 / MIB,
            drift_commit as f64 / MIB
        ),
    });

    // S2 -- positive controls of known size, held live.
    for mib in [64usize, 256, 1024, 2048] {
        let planted = mib << 20;
        let (b_ws, b_commit) = s.reset();
        let mut buf = vec![0u8; planted];
        touch(&mut buf);
        let (p_ws, p_commit) = s.peak();
        let d_ws = p_ws as i64 - b_ws as i64;
        let d_commit = p_commit as i64 - b_commit as i64;
        drop(buf);
        let r_ws = d_ws as f64 / planted as f64;
        let r_commit = d_commit as f64 / planted as f64;
        let ok = (0.97..=1.15).contains(&r_ws) && (0.97..=1.15).contains(&r_commit);
        println!(
            "selftest,S2 known allocation {mib} MiB,{planted},{d_ws},{d_commit},{r_ws:.4},{r_commit:.4},{}",
            if ok { "PASS" } else { "FAIL" }
        );
        checks.push(Check {
            name: "S2 known allocation",
            ok,
            detail: format!("{mib} MiB planted, ws {r_ws:.4}x, commit {r_commit:.4}x"),
        });
    }

    // S3 -- the two instruments are genuinely different. An untouched
    // allocation is committed but not resident, so commit must rise and the
    // working set must not. If this fails, `ws` and `commit` are the same
    // number and the retention argument below is unsupportable.
    {
        let planted = 1024usize << 20;
        let (b_ws, b_commit) = s.reset();
        let buf = vec![0u8; planted];
        std::hint::black_box(&buf[0]);
        let (p_ws, p_commit) = s.peak();
        let d_ws = p_ws as i64 - b_ws as i64;
        let d_commit = p_commit as i64 - b_commit as i64;
        drop(buf);
        let ok = d_commit as f64 / planted as f64 > 0.97 && (d_ws as f64) < 0.10 * planted as f64;
        println!(
            "selftest,S3 committed but untouched,{planted},{d_ws},{d_commit},{:.4},{:.4},{}",
            d_ws as f64 / planted as f64,
            d_commit as f64 / planted as f64,
            if ok { "PASS" } else { "FAIL" }
        );
        checks.push(Check {
            name: "S3 commit and RSS are different instruments",
            ok,
            detail: format!(
                "untouched 1024 MiB: commit +{:.1} MiB, ws +{:.1} MiB",
                d_commit as f64 / MIB,
                d_ws as f64 / MIB
            ),
        });
    }

    // S4 -- how short a spike does the sampler miss? A spike's real lifetime is
    // its allocate-touch-free time plus any hold, so it is *measured* here
    // rather than assumed from the hold alone. The kernel peak has no sampling
    // window at all, which is why every headline condition uses it and the
    // sampler is only ever supporting detail.
    for (mib, hold_us) in [(8usize, 0u64), (8, 200), (64, 0), (512, 0), (512, 50_000)] {
        let planted = mib << 20;
        let mut caught = 0;
        let trials = 12;
        let mut total = Duration::ZERO;
        for _ in 0..trials {
            let (_, b_commit) = s.reset();
            let t = Instant::now();
            let mut buf = vec![0u8; planted];
            touch(&mut buf);
            if hold_us > 0 {
                std::thread::sleep(Duration::from_micros(hold_us));
            }
            drop(buf);
            total += t.elapsed();
            let (_, p_commit) = s.peak();
            if (p_commit as i64 - b_commit as i64) as f64 > 0.9 * planted as f64 {
                caught += 1;
            }
        }
        let rate = caught as f64 / trials as f64;
        let life_us = total.as_secs_f64() * 1e6 / trials as f64;
        // The claim under test is only that a spike lasting >= 1 ms (the
        // sampler's own interval in the concurrency sweep) is never missed.
        let ok = life_us < 1000.0 || rate == 1.0;
        println!(
            "selftest,S4 spike {mib} MiB hold {hold_us} us (life {life_us:.0} us),{planted},,,,{rate:.3},{}",
            if ok { "PASS" } else { "FAIL" }
        );
        checks.push(Check {
            name: "S4 sampler temporal resolution",
            ok,
            detail: format!("{mib} MiB, life {life_us:.0} us: caught {caught}/{trials}"),
        });
    }

    // S5 -- phase attribution. A peak in phase A must not leak into phase B.
    {
        let planted = 1024usize << 20;
        let (_, a_base) = s.reset();
        let mut buf = vec![0u8; planted];
        touch(&mut buf);
        std::thread::sleep(Duration::from_millis(50));
        let (_, a_peak) = s.peak();
        drop(buf);
        std::thread::sleep(Duration::from_millis(50));
        let (_, b_base) = s.reset();
        std::thread::sleep(Duration::from_millis(200));
        let (_, b_peak) = s.peak();
        let a_delta = a_peak as i64 - a_base as i64;
        let b_delta = b_peak as i64 - b_base as i64;
        let ok = a_delta as f64 > 0.9 * planted as f64 && (b_delta as f64) < 0.05 * planted as f64;
        println!(
            "selftest,S5 phase attribution,{planted},,{b_delta},{:.4},{:.4},{}",
            a_delta as f64 / planted as f64,
            b_delta as f64 / planted as f64,
            if ok { "PASS" } else { "FAIL" }
        );
        checks.push(Check {
            name: "S5 phase attribution",
            ok,
            detail: format!(
                "phase A +{:.1} MiB, phase B +{:.1} MiB",
                a_delta as f64 / MIB,
                b_delta as f64 / MIB
            ),
        });
    }

    // S6 -- the kernel peak is a genuine upper bound on the sampler.
    {
        let (kp_ws, kp_commit) = mem::kernel_peak();
        let ok = kp_ws > 0 && kp_commit >= 2048 << 20;
        println!(
            "selftest,S6 kernel peak >= largest planted,{},{},{},,,{}",
            2048usize << 20,
            kp_ws,
            kp_commit,
            if ok { "PASS" } else { "FAIL" }
        );
        checks.push(Check {
            name: "S6 kernel peak brackets the run",
            ok,
            detail: format!(
                "kernel peak ws {:.1} MiB, commit {:.1} MiB",
                kp_ws as f64 / MIB,
                kp_commit as f64 / MIB
            ),
        });
    }

    let samples = s.sample_count();
    drop(s);

    eprintln!("--- m8 selftest ---");
    let mut failed = 0;
    for c in &checks {
        eprintln!(
            "  [{}] {:<44} {}",
            if c.ok { "PASS" } else { "FAIL" },
            c.name,
            c.detail
        );
        if !c.ok {
            failed += 1;
        }
    }
    eprintln!("  sampler took {samples} samples");
    eprintln!(
        "  modelled per-worker (stack.rs): {} bytes = {:.1} MiB = {:.1} MB",
        per_worker_bytes_model(),
        per_worker_bytes_model() as f64 / MIB,
        per_worker_bytes_model() as f64 / 1e6
    );
    eprintln!(
        "  modelled frame buffer         : {} bytes = {:.1} MiB",
        frame_bytes_model(),
        frame_bytes_model() as f64 / MIB
    );
    if failed > 0 {
        eprintln!("  {failed} CHECK(S) FAILED -- nothing downstream is worth reading");
        std::process::exit(1);
    }
    eprintln!("  all checks passed");
}

// ---------------------------------------------------------------------------
// null -- on real data
// ---------------------------------------------------------------------------

/// The null is the process doing no decoding, on the real corpus: the file list
/// is real, the file is really opened, and its bytes are really read into a
/// buffer of *exactly known* size. That last step doubles as a positive control
/// whose planted size is a real ARW rather than a synthetic number.
fn null(dir: &Path, limit: Option<usize>) {
    let paths = arw_paths(dir, limit);
    println!("#kind,phase,path,planted_bytes,base_ws,base_commit,peak_ws,peak_commit,delta_ws,delta_commit,ratio_commit,threads");
    let s = mem::Sampler::start(Duration::from_micros(500));
    let threads = threads_env();

    // Phase 1: idle, with the file list enumerated but nothing decoded.
    let (b_ws, b_commit) = s.reset();
    std::thread::sleep(Duration::from_secs(2));
    let (p_ws, p_commit) = s.peak();
    println!(
        "null,idle-with-real-file-list,{},0,{b_ws},{b_commit},{p_ws},{p_commit},{},{},,{threads}",
        dir.display(),
        p_ws as i64 - b_ws as i64,
        p_commit as i64 - b_commit as i64
    );

    // Phase 2: read real ARW bytes without decoding them. Known planted size.
    for p in paths.iter().take(8) {
        let n = file_bytes(p);
        let (b_ws, b_commit) = s.reset();
        let mut bytes = std::fs::read(p).expect("read");
        touch(&mut bytes);
        let (p_ws, p_commit) = s.peak();
        let d_ws = p_ws as i64 - b_ws as i64;
        let d_commit = p_commit as i64 - b_commit as i64;
        drop(bytes);
        println!(
            "null,read-not-decode,{},{n},{b_ws},{b_commit},{p_ws},{p_commit},{d_ws},{d_commit},{:.4},{threads}",
            p.file_name().unwrap().to_string_lossy(),
            d_commit as f64 / n as f64
        );
    }

    // Phase 3: back to idle, to show the read did not ratchet the baseline.
    let (b_ws, b_commit) = s.reset();
    std::thread::sleep(Duration::from_secs(2));
    let (p_ws, p_commit) = s.peak();
    println!(
        "null,idle-after-reads,{},0,{b_ws},{b_commit},{p_ws},{p_commit},{},{},,{threads}",
        dir.display(),
        p_ws as i64 - b_ws as i64,
        p_commit as i64 - b_commit as i64
    );
}

// ---------------------------------------------------------------------------
// single -- one decode in isolation
// ---------------------------------------------------------------------------

fn single(dir: &Path, limit: Option<usize>) {
    let paths = arw_paths(dir, limit);
    let set = set_name(dir);
    println!("#kind,set,path,file_bytes,alloc_bytes,active_px,threads,idx,base_ws,base_commit,peak_ws,peak_commit,hold_ws,hold_commit,after_ws,after_commit,decode_secs");
    let s = mem::Sampler::start(Duration::from_micros(500));
    let threads = threads_env();

    for (i, p) in paths.iter().enumerate() {
        let n = file_bytes(p);
        let (b_ws, b_commit) = s.reset();
        let t = Instant::now();
        let frame = strehl_raw::decode(p).expect("decode");
        let secs = t.elapsed().as_secs_f64();
        let (p_ws, p_commit) = s.peak();
        let (h_ws, h_commit) = mem::now();
        let alloc = frame.allocated_bytes();
        let active = frame.active.pixels();
        drop(frame);
        std::thread::sleep(Duration::from_millis(20));
        let (a_ws, a_commit) = mem::now();
        println!(
            "single,{set},{},{n},{alloc},{active},{threads},{i},{b_ws},{b_commit},{p_ws},{p_commit},{h_ws},{h_commit},{a_ws},{a_commit},{secs:.4}",
            p.file_name().unwrap().to_string_lossy()
        );
    }
}

// ---------------------------------------------------------------------------
// seq -- N decodes one at a time, in one process
// ---------------------------------------------------------------------------

/// The retention discriminator. True scratch is transient and cannot accumulate
/// when only one decode is ever live; anything that *does* accumulate here is
/// the allocator holding freed memory. So: does the kernel peak grow with the
/// number of sequential decodes, plateau, or step?
fn seq(dir: &Path, limit: Option<usize>) {
    let paths = arw_paths(dir, limit);
    let set = set_name(dir);
    println!("#kind,set,i,path,file_bytes,alloc_bytes,threads,cur_ws,cur_commit,kpeak_ws,kpeak_commit,decode_secs");
    let threads = threads_env();
    for (i, p) in paths.iter().enumerate() {
        let n = file_bytes(p);
        let t = Instant::now();
        let frame = strehl_raw::decode(p).expect("decode");
        let secs = t.elapsed().as_secs_f64();
        let alloc = frame.allocated_bytes();
        drop(frame);
        std::thread::sleep(Duration::from_millis(10));
        let (cur_ws, cur_commit) = mem::now();
        let (kp_ws, kp_commit) = mem::kernel_peak();
        println!(
            "seq,{set},{i},{},{n},{alloc},{threads},{cur_ws},{cur_commit},{kp_ws},{kp_commit},{secs:.4}",
            p.file_name().unwrap().to_string_lossy()
        );
    }
}

// ---------------------------------------------------------------------------
// conc -- K decodes genuinely overlapping
// ---------------------------------------------------------------------------

#[derive(Clone, Copy, PartialEq)]
enum ConcMode {
    /// Each thread decodes and drops in a loop, so K decodes are live at once.
    Drop,
    /// Each thread decodes once and holds the frame, so K *frames* are live but
    /// only the tail of the decodes overlaps.
    Hold,
}

/// One point of the concurrency sweep, in its own process so the kernel peak
/// (which has no sampling error) is the instrument.
fn conc(dir: &Path, k: usize, reps: usize, mode: ConcMode, limit: Option<usize>) {
    let paths = Arc::new(arw_paths(dir, limit));
    let threads = threads_env();
    println!("#kind,k,reps,mode,threads,n_decodes,base_ws,base_commit,kpeak_ws,kpeak_commit,samp_peak_ws,samp_peak_commit,elapsed_secs,mean_file_bytes,alloc_bytes");

    // The base is measured before any thread starts, in this same process.
    std::thread::sleep(Duration::from_millis(200));
    let s = mem::Sampler::start(Duration::from_millis(1));
    let (base_ws, base_commit) = s.reset();

    let decodes = Arc::new(AtomicU64::new(0));
    let alloc = Arc::new(AtomicU64::new(0));
    let t0 = Instant::now();

    if k > 0 {
        let barrier = Arc::new(Barrier::new(k));
        let mut handles = Vec::with_capacity(k);
        for tid in 0..k {
            let paths = paths.clone();
            let barrier = barrier.clone();
            let decodes = decodes.clone();
            let alloc = alloc.clone();
            handles.push(std::thread::spawn(move || {
                barrier.wait();
                let mut held = Vec::new();
                for rep in 0..reps {
                    let p = &paths[(tid + rep * k) % paths.len()];
                    let frame = strehl_raw::decode(p).expect("decode");
                    alloc.store(frame.allocated_bytes() as u64, Ordering::Relaxed);
                    decodes.fetch_add(1, Ordering::Relaxed);
                    match mode {
                        ConcMode::Drop => drop(frame),
                        ConcMode::Hold => held.push(frame),
                    }
                }
                if mode == ConcMode::Hold {
                    barrier.wait();
                }
                std::hint::black_box(&held);
                drop(held);
            }));
        }
        for h in handles {
            h.join().expect("worker");
        }
    }

    let elapsed = t0.elapsed().as_secs_f64();
    let (sp_ws, sp_commit) = s.peak();
    drop(s);
    let (kp_ws, kp_commit) = mem::kernel_peak();
    let mean_file = if paths.is_empty() {
        0
    } else {
        paths.iter().map(|p| file_bytes(p)).sum::<u64>() / paths.len() as u64
    };
    let mode_s = match mode {
        ConcMode::Drop => "drop",
        ConcMode::Hold => "hold",
    };
    println!(
        "conc,{k},{reps},{mode_s},{threads},{},{base_ws},{base_commit},{kp_ws},{kp_commit},{sp_ws},{sp_commit},{elapsed:.3},{mean_file},{}",
        decodes.load(Ordering::Relaxed),
        alloc.load(Ordering::Relaxed)
    );
    eprintln!(
        "k={k} {mode_s}: kernel peak ws {:.1} MiB, commit {:.1} MiB; base ws {:.1} MiB, commit {:.1} MiB; {elapsed:.2} s",
        kp_ws as f64 / MIB,
        kp_commit as f64 / MIB,
        base_ws as f64 / MIB,
        base_commit as f64 / MIB
    );
}

// ---------------------------------------------------------------------------

fn usage() -> ! {
    eprintln!(
        "usage:
  m8-scratch selftest
  m8-scratch null   <dir-or-file> [--limit N]
  m8-scratch single <dir-or-file> [--limit N]
  m8-scratch seq    <dir-or-file> [--limit N]
  m8-scratch conc   <dir> --k K [--reps R] [--hold] [--limit N]

Pin RAYON_NUM_THREADS before every run. An unpinned peak-RSS number is
uninterpretable (SYNTHESIS fact 22)."
    );
    std::process::exit(2)
}

fn main() {
    let args: Vec<String> = std::env::args().skip(1).collect();
    if args.is_empty() {
        usage();
    }
    let mut limit = None;
    let mut k = 1usize;
    let mut reps = 4usize;
    let mut mode = ConcMode::Drop;
    let mut i = 1;
    while i < args.len() {
        match args[i].as_str() {
            "--limit" => {
                limit = Some(args[i + 1].parse().expect("--limit N"));
                i += 2;
            }
            "--k" => {
                k = args[i + 1].parse().expect("--k K");
                i += 2;
            }
            "--reps" => {
                reps = args[i + 1].parse().expect("--reps R");
                i += 2;
            }
            "--hold" => {
                mode = ConcMode::Hold;
                i += 1;
            }
            _ => i += 1,
        }
    }
    let positional: Vec<&String> = args
        .iter()
        .skip(1)
        .filter(|a| !a.starts_with("--"))
        .enumerate()
        .filter(|(j, _)| {
            // Drop values that belong to a preceding flag.
            let idx = *j;
            let _ = idx;
            true
        })
        .map(|(_, a)| a)
        .collect();
    let target = positional
        .iter()
        .find(|a| Path::new(a).exists())
        .map(|a| PathBuf::from(a.as_str()));

    match args[0].as_str() {
        "selftest" => selftest(),
        "null" => null(&target.unwrap_or_else(|| usage()), limit),
        "single" => single(&target.unwrap_or_else(|| usage()), limit),
        "seq" => seq(&target.unwrap_or_else(|| usage()), limit),
        "conc" => conc(&target.unwrap_or_else(|| usage()), k, reps, mode, limit),
        _ => usage(),
    }
}
