//! `STREHL_FOLD_TRACE=1`: where a GPU fold's time goes, per step, printed
//! after the fold (round-2 performance plan, stage Q6b). Off by default; on,
//! it only reads the clock around steps that run anyway. Never arithmetic.
use std::sync::atomic::{AtomicBool, AtomicU64, Ordering};
use std::time::Instant;

pub const ENV: &str = "STREHL_FOLD_TRACE";

#[derive(Clone, Copy)]
pub(super) enum Step {
    /// The fold thread waiting for a decoded plane.
    WaitDecode,
    /// Uploading a plane (`GpuFold::stage`).
    Stage,
    ProbeSubmit,
    ProbeCollect,
    /// The fold's submission (`add_staged`).
    Add,
    /// Handing kept luma to the depth records.
    Luma,
    /// A decoder thread decoding a plane (and its group).
    Decode,
    /// A decoder thread waiting for room in the window.
    DecoderIdle,
    /// Within a plane's decode: member 1's file.
    DecodeFile,
    /// Within it: the capture identity.
    Identity,
    /// Within it: the group's other members (and their check).
    Group,
    /// When tracing only: waiting for the device to run the chunk's queued
    /// fold work, so [`Step::Finish`] is the readback alone.
    DeviceDrain,
    /// Reading the chunk's totals back from the device (`finish_chunk`).
    Finish,
    /// The desktop's per-plane admission maps: collecting the GPU fold's
    /// read-backs and writing their records (`emit_gpu_support`).
    Evidence,
}

const STEPS: usize = 14;
const NAMES: [&str; STEPS] = [
    "fold thread waiting for decodes",
    "upload (stage)",
    "probe submit",
    "probe collect",
    "fold submit",
    "luma hand-off",
    "decoder threads decoding",
    "decoder threads idle",
    "  of which member 1's decode",
    "  of which identity",
    "  of which members 2-4",
    "device draining queued fold work",
    "totals read back",
    "admission maps (collect, write)",
];

static ON: AtomicBool = AtomicBool::new(false);
static NANOS: [AtomicU64; STEPS] = [const { AtomicU64::new(0) }; STEPS];
static COUNT: [AtomicU64; STEPS] = [const { AtomicU64::new(0) }; STEPS];

/// Read the switch and clear the totals (once per fold).
pub(super) fn begin() {
    let on = std::env::var(ENV).is_ok_and(|v| v.trim() == "1");
    ON.store(on, Ordering::Relaxed);
    for (n, c) in NANOS.iter().zip(&COUNT) {
        n.store(0, Ordering::Relaxed);
        c.store(0, Ordering::Relaxed);
    }
}

/// Whether this fold is traced.
pub(super) fn on() -> bool {
    ON.load(Ordering::Relaxed)
}

/// Run `f`, adding its time to `step` when tracing.
pub(super) fn time<T>(step: Step, f: impl FnOnce() -> T) -> T {
    if !ON.load(Ordering::Relaxed) {
        return f();
    }
    let start = Instant::now();
    let out = f();
    NANOS[step as usize].fetch_add(start.elapsed().as_nanos() as u64, Ordering::Relaxed);
    COUNT[step as usize].fetch_add(1, Ordering::Relaxed);
    out
}

/// Print the totals, when tracing, for a fold of `wall` seconds.
pub(super) fn report(wall: f64) {
    if !ON.load(Ordering::Relaxed) {
        return;
    }
    eprintln!("fold trace      : {wall:.2} s of fold ({ENV})");
    for (k, name) in NAMES.iter().enumerate() {
        let (ns, n) = (
            NANOS[k].load(Ordering::Relaxed),
            COUNT[k].load(Ordering::Relaxed),
        );
        if n > 0 {
            eprintln!(
                "                  {name:<32} {:>8.2} s over {n:>5} ({:.1} ms each)",
                ns as f64 * 1e-9,
                ns as f64 * 1e-6 / n as f64
            );
        }
    }
}
