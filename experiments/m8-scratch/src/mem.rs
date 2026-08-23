//! Windows process memory counters, and a background sampler.
//!
//! Two instruments, deliberately kept separate because they fail differently.
//!
//! 1. **Kernel-maintained peaks** — `PeakWorkingSetSize` and
//!    `PeakPagefileUsage`. The kernel updates these as the process touches
//!    pages, so they have **no sampling error**. They are peaks over the whole
//!    process lifetime and cannot be reset, which is why every headline
//!    condition in this experiment runs in its own process.
//! 2. **A polling sampler** — a thread reading `WorkingSetSize` and
//!    `PrivateUsage` every `interval`. It can attribute a peak to a *phase*,
//!    which the kernel counters cannot, but it can miss a spike shorter than
//!    its interval. `selftest` measures that miss rate rather than assuming it.
//!
//! `WorkingSetSize` is resident physical memory (RSS) and the OS may trim it.
//! `PrivateUsage` is private committed bytes: what the allocator has actually
//! asked the OS to back. Retention shows up in commit even when the working
//! set has been trimmed, so both are always reported.

use std::sync::atomic::{AtomicBool, AtomicU64, Ordering};
use std::sync::Arc;
use std::thread::{self, JoinHandle};
use std::time::Duration;

/// `PROCESS_MEMORY_COUNTERS_EX`.
#[repr(C)]
#[derive(Clone, Copy, Default, Debug)]
pub struct Pmc {
    pub cb: u32,
    pub page_fault_count: u32,
    pub peak_working_set_size: usize,
    pub working_set_size: usize,
    pub quota_peak_paged_pool_usage: usize,
    pub quota_paged_pool_usage: usize,
    pub quota_peak_non_paged_pool_usage: usize,
    pub quota_non_paged_pool_usage: usize,
    pub pagefile_usage: usize,
    pub peak_pagefile_usage: usize,
    pub private_usage: usize,
}

extern "system" {
    fn GetCurrentProcess() -> *mut std::ffi::c_void;
    fn K32GetProcessMemoryInfo(process: *mut std::ffi::c_void, counters: *mut Pmc, cb: u32) -> i32;
}

/// Full counter block for this process.
pub fn counters() -> Pmc {
    let mut c = Pmc {
        cb: std::mem::size_of::<Pmc>() as u32,
        ..Default::default()
    };
    let ok = unsafe { K32GetProcessMemoryInfo(GetCurrentProcess(), &mut c, c.cb) };
    assert!(ok != 0, "K32GetProcessMemoryInfo failed");
    c
}

/// Current `(working set, private commit)` in bytes.
pub fn now() -> (u64, u64) {
    let c = counters();
    (c.working_set_size as u64, c.private_usage as u64)
}

/// Kernel-maintained `(peak working set, peak commit)` in bytes, for the whole
/// process lifetime. No sampling error.
pub fn kernel_peak() -> (u64, u64) {
    let c = counters();
    (c.peak_working_set_size as u64, c.peak_pagefile_usage as u64)
}

/// A polling peak detector with a resettable phase window.
pub struct Sampler {
    stop: Arc<AtomicBool>,
    peak_ws: Arc<AtomicU64>,
    peak_commit: Arc<AtomicU64>,
    samples: Arc<AtomicU64>,
    handle: Option<JoinHandle<()>>,
}

impl Sampler {
    /// `interval` below ~1 ms is served by a yielding spin, because Windows
    /// `Sleep` granularity is far coarser than that. A spin burns one core, so
    /// concurrency sweeps use the millisecond path.
    pub fn start(interval: Duration) -> Self {
        let stop = Arc::new(AtomicBool::new(false));
        let peak_ws = Arc::new(AtomicU64::new(0));
        let peak_commit = Arc::new(AtomicU64::new(0));
        let samples = Arc::new(AtomicU64::new(0));
        let (s, w, c, n) = (
            stop.clone(),
            peak_ws.clone(),
            peak_commit.clone(),
            samples.clone(),
        );
        let handle = thread::spawn(move || {
            while !s.load(Ordering::Relaxed) {
                let (ws, commit) = now();
                w.fetch_max(ws, Ordering::Relaxed);
                c.fetch_max(commit, Ordering::Relaxed);
                n.fetch_add(1, Ordering::Relaxed);
                if interval < Duration::from_millis(1) {
                    thread::yield_now();
                } else {
                    thread::sleep(interval);
                }
            }
        });
        Self {
            stop,
            peak_ws,
            peak_commit,
            samples,
            handle: Some(handle),
        }
    }

    /// Start a new phase window at the current values. Returns them.
    pub fn reset(&self) -> (u64, u64) {
        let (ws, commit) = now();
        self.peak_ws.store(ws, Ordering::Relaxed);
        self.peak_commit.store(commit, Ordering::Relaxed);
        (ws, commit)
    }

    /// Peak `(working set, commit)` since the last [`Sampler::reset`].
    pub fn peak(&self) -> (u64, u64) {
        (
            self.peak_ws.load(Ordering::Relaxed),
            self.peak_commit.load(Ordering::Relaxed),
        )
    }

    pub fn sample_count(&self) -> u64 {
        self.samples.load(Ordering::Relaxed)
    }
}

impl Drop for Sampler {
    fn drop(&mut self) {
        self.stop.store(true, Ordering::Relaxed);
        if let Some(h) = self.handle.take() {
            let _ = h.join();
        }
    }
}
