//! D11: Divan timing of the shipped decoder on real A7C II ARWs.
//!
//! The benchmark deliberately dispatches files serially. A fresh process and
//! `RAYON_NUM_THREADS` setting at each curve point then expose only the shipped
//! decoder's intra-frame scaling, rather than an outer file-level pool.

use std::path::{Path, PathBuf};
use std::sync::OnceLock;
use std::time::Duration;

use divan::counter::BytesCount;
use strehl_raw::Frame;

const DEFAULT_CAPTURE_DIR: &str = r"D:\personal\macro\112MSDCF";
const REGISTERED_SET_LEN: usize = 60;
const SELECTED_INDICES: [usize; 3] = [0, 29, 59];
const EXPECTED_ALLOCATED_BYTES: usize = 7168 * 5120 * 2;
const EXPECTED_ACTIVE_WIDTH: usize = 7032;
const EXPECTED_ACTIVE_HEIGHT: usize = 4688;
const INJECTED_DELAY: Duration = Duration::from_millis(200);
const FNV_OFFSET: u64 = 0xcbf29ce484222325;
const FNV_PRIME: u64 = 0x100000001b3;

struct Workload {
    paths: Vec<PathBuf>,
    compressed_bytes: u64,
    allocated_bytes: u64,
    sampled_checksums: Vec<u64>,
}

static WORKLOAD: OnceLock<Workload> = OnceLock::new();

#[derive(Clone, Copy)]
#[repr(C)]
struct FileTime {
    low: u32,
    high: u32,
}

impl FileTime {
    fn ticks(self) -> u64 {
        (u64::from(self.high) << 32) | u64::from(self.low)
    }
}

#[cfg(windows)]
#[link(name = "kernel32")]
unsafe extern "system" {
    fn GetSystemTimes(idle: *mut FileTime, kernel: *mut FileTime, user: *mut FileTime) -> i32;
}

#[cfg(windows)]
fn system_times() -> Option<[u64; 3]> {
    let mut idle = FileTime { low: 0, high: 0 };
    let mut kernel = FileTime { low: 0, high: 0 };
    let mut user = FileTime { low: 0, high: 0 };
    // SAFETY: all pointers are valid, writable FILETIME-compatible values.
    let ok = unsafe { GetSystemTimes(&mut idle, &mut kernel, &mut user) };
    (ok != 0).then(|| [idle.ticks(), kernel.ticks(), user.ticks()])
}

#[cfg(not(windows))]
fn system_times() -> Option<[u64; 3]> {
    None
}

fn busy_percent(before: [u64; 3], after: [u64; 3]) -> Option<f64> {
    let idle = after[0].checked_sub(before[0])?;
    let kernel = after[1].checked_sub(before[1])?;
    let user = after[2].checked_sub(before[2])?;
    let span = kernel.checked_add(user)?;
    (span != 0).then(|| 100.0 * (span.saturating_sub(idle)) as f64 / span as f64)
}

fn arw_files(dir: &Path) -> Vec<PathBuf> {
    let mut files: Vec<_> = std::fs::read_dir(dir)
        .unwrap_or_else(|e| panic!("reading {}: {e}", dir.display()))
        .map(|entry| entry.expect("reading directory entry").path())
        .filter(|path| {
            path.is_file()
                && path
                    .extension()
                    .and_then(|value| value.to_str())
                    .is_some_and(|value| value.eq_ignore_ascii_case("arw"))
        })
        .collect();
    files.sort();
    assert!(
        files.len() >= REGISTERED_SET_LEN,
        "{} has only {} ARWs; the registered workload needs {REGISTERED_SET_LEN}",
        dir.display(),
        files.len()
    );
    files.truncate(REGISTERED_SET_LEN);
    files
}

fn full_checksum(data: &[u16]) -> (u64, usize) {
    let mut hash = FNV_OFFSET;
    let mut nonzero = 0usize;
    for &sample in data {
        hash ^= u64::from(sample);
        hash = hash.wrapping_mul(FNV_PRIME);
        nonzero += usize::from(sample != 0);
    }
    (hash, nonzero)
}

fn sampled_checksum(frame: &Frame) -> u64 {
    let mut hash = FNV_OFFSET ^ frame.data.len() as u64;
    for i in 0..257usize {
        let x = (i.wrapping_mul(104_729).wrapping_add(17)) % frame.active.width;
        let y = (i.wrapping_mul(13_007).wrapping_add(31)) % frame.active.height;
        hash ^= u64::from(frame.sample(x, y));
        hash = hash.wrapping_mul(FNV_PRIME);
    }
    hash ^= frame.active.width as u64;
    hash = hash.wrapping_mul(FNV_PRIME);
    hash ^ frame.active.height as u64
}

fn checked_decode(path: &Path) -> Frame {
    let frame =
        strehl_raw::decode(path).unwrap_or_else(|e| panic!("decoding {}: {e}", path.display()));
    assert_eq!(
        frame.allocated_bytes(),
        EXPECTED_ALLOCATED_BYTES,
        "{} allocated-byte contract changed",
        path.display()
    );
    assert_eq!(
        (frame.active.width, frame.active.height),
        (EXPECTED_ACTIVE_WIDTH, EXPECTED_ACTIVE_HEIGHT),
        "{} active-area contract changed",
        path.display()
    );
    frame
}

fn initialise_workload() -> Workload {
    let dir = std::env::var_os("IOPERF_ARW_DIR")
        .map(PathBuf::from)
        .unwrap_or_else(|| PathBuf::from(DEFAULT_CAPTURE_DIR));
    let all = arw_files(&dir);
    let paths: Vec<_> = SELECTED_INDICES
        .iter()
        .map(|&index| all[index].clone())
        .collect();

    let compressed_bytes = paths
        .iter()
        .map(|path| {
            std::fs::metadata(path)
                .unwrap_or_else(|e| panic!("metadata for {}: {e}", path.display()))
                .len()
        })
        .sum();

    let mut allocated_bytes = 0u64;
    let mut sampled_checksums = Vec::with_capacity(paths.len());
    println!("PREFLIGHT_BEGIN,untimed,page_cache_warmup=true");
    for path in &paths {
        let frame = checked_decode(path);
        let (checksum, nonzero) = full_checksum(&frame.data);
        assert!(
            nonzero > frame.active.pixels() / 2,
            "{} decoded mostly/all zero: {nonzero} nonzero samples",
            path.display()
        );
        let sampled = sampled_checksum(&frame);
        allocated_bytes += frame.allocated_bytes() as u64;
        sampled_checksums.push(sampled);
        println!(
            "PREFLIGHT_FILE,path={},compressed_bytes={},allocated_bytes={},active={}x{},nonzero={},full_fnv64={checksum:016x},sampled_fnv64={sampled:016x}",
            path.display(),
            std::fs::metadata(path).expect("preflight metadata").len(),
            frame.allocated_bytes(),
            frame.active.width,
            frame.active.height,
            nonzero,
        );
    }
    println!(
        "PREFLIGHT_TOTAL,files={},compressed_input_bytes={},allocated_output_bytes={},input_to_output_ratio={:.9}",
        paths.len(),
        compressed_bytes,
        allocated_bytes,
        compressed_bytes as f64 / allocated_bytes as f64,
    );
    println!(
        "DIVAN_COUNTER,meaning=allocated_output_bytes_per_second,compressed_input_rate=displayed_rate*{:.9}",
        compressed_bytes as f64 / allocated_bytes as f64,
    );

    Workload {
        paths,
        compressed_bytes,
        allocated_bytes,
        sampled_checksums,
    }
}

fn workload() -> &'static Workload {
    WORKLOAD.get_or_init(initialise_workload)
}

fn decode_iteration(delay: Duration) -> u64 {
    let workload = workload();
    let mut combined = FNV_OFFSET;
    for (index, path) in workload.paths.iter().enumerate() {
        let frame = checked_decode(path);
        let sampled = sampled_checksum(&frame);
        assert_eq!(
            sampled,
            workload.sampled_checksums[index],
            "{} changed from untimed preflight",
            path.display()
        );

        // Both the sampled values and the allocation itself escape to an
        // optimisation barrier. The decoder call therefore cannot become a
        // benchmark no-op.
        divan::black_box(frame.data.as_slice());
        combined ^= divan::black_box(sampled);
        combined = combined.wrapping_mul(FNV_PRIME);
    }
    if !delay.is_zero() {
        std::thread::sleep(delay);
    }
    divan::black_box(combined)
}

#[divan::bench(sample_count = 7, sample_size = 1)]
fn decode_real_arw(bencher: divan::Bencher) {
    let bytes = workload().allocated_bytes;
    bencher
        .counter(BytesCount::new(bytes))
        .bench_local(|| decode_iteration(Duration::ZERO));
}

#[divan::bench(sample_count = 7, sample_size = 1)]
fn decode_real_arw_plus_200ms(bencher: divan::Bencher) {
    let bytes = workload().allocated_bytes;
    bencher
        .counter(BytesCount::new(bytes))
        .bench_local(|| decode_iteration(INJECTED_DELAY));
}

fn main() {
    let before = system_times();
    let requested: usize = std::env::var("RAYON_NUM_THREADS")
        .expect("set RAYON_NUM_THREADS explicitly")
        .parse()
        .expect("RAYON_NUM_THREADS must be an integer");
    assert!(
        [1, 2, 4, 8, 16, 32].contains(&requested),
        "RAYON_NUM_THREADS must be one of 1,2,4,8,16,32"
    );

    let workload = workload();
    let actual = rayon::current_num_threads();
    assert_eq!(
        actual, requested,
        "Rayon global pool does not match the requested curve point"
    );
    println!(
        "RUN_CONFIG,rayon_threads={actual},compressed_input_bytes={},allocated_output_bytes={},injected_delay_ms={}",
        workload.compressed_bytes,
        workload.allocated_bytes,
        INJECTED_DELAY.as_millis(),
    );

    divan::main();

    if let (Some(before), Some(after)) = (before, system_times())
        && let Some(busy) = busy_percent(before, after)
    {
        println!("RUN_CONTENTION,machine_busy_percent={busy:.3}");
    }
}
