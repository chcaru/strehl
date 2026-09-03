//! D15: Windows cold-device throughput with an explicit page-cache bypass.
//!
//! Every capture handle is read-only. `FILE_FLAG_NO_BUFFERING` plus aligned
//! buffers makes the device arms independent of the Windows system file cache.

#[cfg(not(windows))]
compile_error!("M-PHASE0-NVME is a Windows-only measurement");

use std::alloc::{Layout, alloc_zeroed, dealloc, handle_alloc_error};
use std::fs::OpenOptions;
use std::io::{self, Read};
use std::path::{Path, PathBuf};
use std::ptr::NonNull;
use std::sync::atomic::{AtomicU64, AtomicUsize, Ordering};
use std::time::{Duration, Instant, UNIX_EPOCH};

use std::os::windows::fs::OpenOptionsExt;

const DEFAULT_CAPTURE_DIR: &str = r"D:\personal\macro\112MSDCF";
const FILE_LIMIT: usize = 60;
const REGISTERED_BYTES: u64 = 2_252_959_744;
const ALIGNMENT: usize = 4096;
const BUFFER_BYTES: usize = 8 * 1024 * 1024;
const FILE_FLAG_NO_BUFFERING: u32 = 0x2000_0000;
const FILE_FLAG_SEQUENTIAL_SCAN: u32 = 0x0800_0000;
const TIMER_PLANT: Duration = Duration::from_millis(200);
const FNV_OFFSET: u64 = 0xcbf29ce484222325;
const FNV_PRIME: u64 = 0x100000001b3;

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

#[link(name = "kernel32")]
unsafe extern "system" {
    fn GetSystemTimes(idle: *mut FileTime, kernel: *mut FileTime, user: *mut FileTime) -> i32;
}

fn system_times() -> io::Result<[u64; 3]> {
    let mut idle = FileTime { low: 0, high: 0 };
    let mut kernel = FileTime { low: 0, high: 0 };
    let mut user = FileTime { low: 0, high: 0 };
    // SAFETY: all pointers are valid, writable FILETIME-compatible values.
    let ok = unsafe { GetSystemTimes(&mut idle, &mut kernel, &mut user) };
    if ok == 0 {
        return Err(io::Error::last_os_error());
    }
    Ok([idle.ticks(), kernel.ticks(), user.ticks()])
}

fn busy_percent(before: [u64; 3], after: [u64; 3]) -> f64 {
    let idle = after[0].saturating_sub(before[0]);
    let kernel = after[1].saturating_sub(before[1]);
    let user = after[2].saturating_sub(before[2]);
    let span = kernel.saturating_add(user);
    if span == 0 {
        0.0
    } else {
        100.0 * span.saturating_sub(idle) as f64 / span as f64
    }
}

struct AlignedBuffer {
    ptr: NonNull<u8>,
    layout: Layout,
}

impl AlignedBuffer {
    fn new() -> Self {
        let layout =
            Layout::from_size_align(BUFFER_BYTES, ALIGNMENT).expect("valid aligned-buffer layout");
        // SAFETY: `layout` is nonzero and valid. Zeroing makes creating the
        // mutable u8 slice sound before ReadFile overwrites it.
        let raw = unsafe { alloc_zeroed(layout) };
        let ptr = NonNull::new(raw).unwrap_or_else(|| handle_alloc_error(layout));
        assert_eq!(ptr.as_ptr() as usize % ALIGNMENT, 0);
        Self { ptr, layout }
    }

    fn as_mut_slice(&mut self) -> &mut [u8] {
        // SAFETY: the allocation is live, initialized, uniquely borrowed, and
        // has exactly `layout.size()` bytes.
        unsafe { std::slice::from_raw_parts_mut(self.ptr.as_ptr(), self.layout.size()) }
    }
}

impl Drop for AlignedBuffer {
    fn drop(&mut self) {
        // SAFETY: `ptr` came from `alloc_zeroed` with this exact layout and is
        // deallocated exactly once here.
        unsafe { dealloc(self.ptr.as_ptr(), self.layout) };
    }
}

#[derive(Clone, Copy, Debug)]
enum ReadMode {
    Direct,
    Buffered,
}

impl ReadMode {
    fn label(self) -> &'static str {
        match self {
            Self::Direct => "FILE_FLAG_NO_BUFFERING",
            Self::Buffered => "buffered",
        }
    }
}

struct Arm {
    name: &'static str,
    mode: ReadMode,
    workers: usize,
    bytes: u64,
    elapsed: Duration,
    busy_percent: f64,
    checksum: u64,
}

impl Arm {
    fn decimal_gb_s(&self) -> f64 {
        self.bytes as f64 / self.elapsed.as_secs_f64() / 1e9
    }

    fn print(&self) {
        println!(
            "ARM,name={},mode={},workers={},compressed_input_bytes={},seconds={:.9},compressed_input_GB_s={:.6},machine_busy_percent={:.3},checksum={:016x}",
            self.name,
            self.mode.label(),
            self.workers,
            self.bytes,
            self.elapsed.as_secs_f64(),
            self.decimal_gb_s(),
            self.busy_percent,
            self.checksum,
        );
    }
}

fn select_files(dir: &Path) -> io::Result<Vec<PathBuf>> {
    let mut files = Vec::new();
    for entry in std::fs::read_dir(dir)? {
        let path = entry?.path();
        if path.is_file()
            && path
                .extension()
                .and_then(|value| value.to_str())
                .is_some_and(|value| value.eq_ignore_ascii_case("arw"))
        {
            files.push(path);
        }
    }
    files.sort();
    if files.len() < FILE_LIMIT {
        return Err(io::Error::other(format!(
            "{} has only {} ARWs; need {FILE_LIMIT}",
            dir.display(),
            files.len()
        )));
    }
    files.truncate(FILE_LIMIT);
    Ok(files)
}

fn manifest_fingerprint(paths: &[PathBuf]) -> io::Result<(u64, u64)> {
    let mut hash = FNV_OFFSET;
    let mut total = 0u64;
    for path in paths {
        let metadata = std::fs::metadata(path)?;
        total = total
            .checked_add(metadata.len())
            .ok_or_else(|| io::Error::other("byte total overflow"))?;
        for &byte in path.as_os_str().to_string_lossy().as_bytes() {
            hash ^= u64::from(byte);
            hash = hash.wrapping_mul(FNV_PRIME);
        }
        hash ^= metadata.len();
        hash = hash.wrapping_mul(FNV_PRIME);
        let modified = metadata
            .modified()?
            .duration_since(UNIX_EPOCH)
            .map_err(io::Error::other)?;
        hash ^= modified.as_nanos() as u64;
        hash = hash.wrapping_mul(FNV_PRIME);
    }
    Ok((hash, total))
}

fn read_one(path: &Path, mode: ReadMode, buffer: &mut AlignedBuffer) -> io::Result<(u64, u64)> {
    let expected = std::fs::metadata(path)?.len();
    if matches!(mode, ReadMode::Direct) && expected % ALIGNMENT as u64 != 0 {
        return Err(io::Error::other(format!(
            "{} length {expected} is not {ALIGNMENT}-byte aligned",
            path.display()
        )));
    }

    let mut options = OpenOptions::new();
    options.read(true);
    match mode {
        ReadMode::Direct => {
            options.custom_flags(FILE_FLAG_NO_BUFFERING | FILE_FLAG_SEQUENTIAL_SCAN);
        }
        // Do not request SEQUENTIAL_SCAN here: Windows may discard sequential
        // pages early, defeating the deliberately warm immediate reread.
        ReadMode::Buffered => {}
    }
    let mut file = options.open(path)?;

    let mut bytes = 0u64;
    let mut checksum = FNV_OFFSET ^ expected;
    loop {
        let count = file.read(buffer.as_mut_slice())?;
        if count == 0 {
            break;
        }
        bytes += count as u64;
        let data = buffer.as_mut_slice();
        checksum ^= u64::from(data[0]);
        checksum = checksum.wrapping_mul(FNV_PRIME);
        checksum ^= u64::from(data[count - 1]);
        checksum = checksum.wrapping_mul(FNV_PRIME);
        checksum ^= count as u64;
        checksum = checksum.wrapping_mul(FNV_PRIME);
    }
    if bytes != expected {
        return Err(io::Error::other(format!(
            "{} read {bytes} bytes, metadata says {expected}",
            path.display()
        )));
    }
    std::hint::black_box(checksum);
    Ok((bytes, checksum))
}

fn read_set(paths: &[PathBuf], mode: ReadMode, workers: usize) -> io::Result<(u64, u64)> {
    let workers = workers.clamp(1, paths.len());
    let next = AtomicUsize::new(0);
    let checksums: Vec<_> = (0..paths.len()).map(|_| AtomicU64::new(0)).collect();
    std::thread::scope(|scope| {
        let mut handles = Vec::with_capacity(workers);
        for _ in 0..workers {
            let next = &next;
            let checksums = &checksums;
            handles.push(scope.spawn(move || -> io::Result<u64> {
                let mut buffer = AlignedBuffer::new();
                let mut bytes = 0u64;
                loop {
                    let index = next.fetch_add(1, Ordering::Relaxed);
                    let Some(path) = paths.get(index) else {
                        break;
                    };
                    let (file_bytes, file_checksum) = read_one(path, mode, &mut buffer)?;
                    bytes += file_bytes;
                    checksums[index].store(file_checksum, Ordering::Relaxed);
                }
                Ok(bytes)
            }));
        }

        let mut bytes = 0u64;
        for handle in handles {
            bytes += handle
                .join()
                .map_err(|_| io::Error::other("read worker panicked"))??;
        }
        let mut checksum = FNV_OFFSET;
        for (index, value) in checksums.iter().enumerate() {
            let file_checksum = value.load(Ordering::Relaxed);
            if file_checksum == 0 {
                return Err(io::Error::other(format!(
                    "file {index} has no consumption checksum"
                )));
            }
            checksum ^= file_checksum;
            checksum = checksum.wrapping_mul(FNV_PRIME);
        }
        std::hint::black_box(checksum);
        Ok((bytes, checksum))
    })
}

fn run_arm(
    name: &'static str,
    paths: &[PathBuf],
    expected_bytes: u64,
    mode: ReadMode,
    workers: usize,
) -> io::Result<Arm> {
    let cpu_before = system_times()?;
    let started = Instant::now();
    let (bytes, checksum) = read_set(paths, mode, workers)?;
    let elapsed = started.elapsed();
    let cpu_after = system_times()?;
    if bytes != expected_bytes {
        return Err(io::Error::other(format!(
            "{name} read {bytes} bytes; expected {expected_bytes}"
        )));
    }
    let arm = Arm {
        name,
        mode,
        workers,
        bytes,
        elapsed,
        busy_percent: busy_percent(cpu_before, cpu_after),
        checksum,
    };
    arm.print();
    Ok(arm)
}

fn commission_timer() -> bool {
    let empty_started = Instant::now();
    std::hint::black_box(());
    let empty = empty_started.elapsed();

    let planted_started = Instant::now();
    std::thread::sleep(TIMER_PLANT);
    std::hint::black_box(());
    let planted = planted_started.elapsed();
    let delta = planted.saturating_sub(empty);
    let pass = (Duration::from_millis(150)..=Duration::from_millis(400)).contains(&planted)
        && delta >= Duration::from_millis(150);
    println!(
        "TIMER_CONTROL,empty_seconds={:.9},planted_ms={},observed_seconds={:.9},delta_seconds={:.9},verdict={}",
        empty.as_secs_f64(),
        TIMER_PLANT.as_millis(),
        planted.as_secs_f64(),
        delta.as_secs_f64(),
        if pass { "PASS" } else { "FAIL" },
    );
    pass
}

fn main() -> io::Result<()> {
    if !commission_timer() {
        return Err(io::Error::other("timer commissioning failed"));
    }

    let dir = std::env::var_os("IOPERF_ARW_DIR")
        .map(PathBuf::from)
        .unwrap_or_else(|| PathBuf::from(DEFAULT_CAPTURE_DIR));
    let paths = select_files(&dir)?;
    let (manifest_before, total_bytes) = manifest_fingerprint(&paths)?;
    if total_bytes != REGISTERED_BYTES {
        return Err(io::Error::other(format!(
            "workload has {total_bytes} bytes; preregistered {REGISTERED_BYTES}"
        )));
    }
    println!(
        "WORKLOAD,dir={},files={},first={},last={},compressed_input_bytes={},manifest_fnv64={manifest_before:016x},alignment={},buffer_bytes={},run_label={}",
        dir.display(),
        paths.len(),
        paths.first().expect("60 files").display(),
        paths.last().expect("60 files").display(),
        total_bytes,
        ALIGNMENT,
        BUFFER_BYTES,
        std::env::var("IOPERF_RUN_LABEL").unwrap_or_else(|_| "unlabelled".into()),
    );

    let direct_qd1_before = run_arm(
        "direct_qd1_before",
        &paths,
        total_bytes,
        ReadMode::Direct,
        1,
    )?;
    let direct_qd8_before = run_arm(
        "direct_qd8_before",
        &paths,
        total_bytes,
        ReadMode::Direct,
        8,
    )?;
    let _buffered_first = run_arm("buffered_first", &paths, total_bytes, ReadMode::Buffered, 8)?;
    let buffered_warm = run_arm("buffered_warm", &paths, total_bytes, ReadMode::Buffered, 8)?;
    let direct_qd8_after = run_arm(
        "direct_qd8_after_warm",
        &paths,
        total_bytes,
        ReadMode::Direct,
        8,
    )?;
    let direct_qd1_after = run_arm(
        "direct_qd1_after_warm",
        &paths,
        total_bytes,
        ReadMode::Direct,
        1,
    )?;

    let warm_over_direct = buffered_warm.decimal_gb_s() / direct_qd8_after.decimal_gb_s();
    let direct_after_over_before =
        direct_qd8_after.decimal_gb_s() / direct_qd8_before.decimal_gb_s();
    let qd1_after_over_before = direct_qd1_after.decimal_gb_s() / direct_qd1_before.decimal_gb_s();
    let cache_control_pass = warm_over_direct >= 1.5;
    println!(
        "CACHE_CONTROL,warm_over_after_warm_direct={warm_over_direct:.6},direct_qd8_after_over_before={direct_after_over_before:.6},direct_qd1_after_over_before={qd1_after_over_before:.6},required_warm_ratio=1.5,verdict={}",
        if cache_control_pass { "PASS" } else { "FAIL" },
    );
    println!(
        "PRIMARY_COLD,definition=FILE_FLAG_NO_BUFFERING_8_workers_before_buffered_prime,compressed_input_bytes={},seconds={:.9},compressed_input_GB_s={:.6},assumed_GB_s=5.000000,machine_busy_percent={:.3}",
        direct_qd8_before.bytes,
        direct_qd8_before.elapsed.as_secs_f64(),
        direct_qd8_before.decimal_gb_s(),
        direct_qd8_before.busy_percent,
    );

    let (manifest_after, total_after) = manifest_fingerprint(&paths)?;
    let captures_unchanged = manifest_before == manifest_after && total_bytes == total_after;
    println!(
        "READ_ONLY_CHECK,before_fnv64={manifest_before:016x},after_fnv64={manifest_after:016x},before_bytes={total_bytes},after_bytes={total_after},verdict={}",
        if captures_unchanged { "PASS" } else { "FAIL" },
    );
    if !captures_unchanged {
        return Err(io::Error::other("capture metadata changed during run"));
    }
    if !cache_control_pass {
        return Err(io::Error::other(
            "cache control failed: warm read was not at least 1.5x direct",
        ));
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn direct_io_buffer_meets_registered_alignment() {
        let buffer = AlignedBuffer::new();
        assert_eq!(buffer.ptr.as_ptr() as usize % ALIGNMENT, 0);
        assert_eq!(buffer.layout.size() % ALIGNMENT, 0);
    }
}
