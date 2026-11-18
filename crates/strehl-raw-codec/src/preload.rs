//! Whole files read ahead of their decode by reader threads, handed to the
//! decoder in memory: each file is read from storage once.
//!
//! # Why
//!
//! A decode-ahead render used to read every file twice: prefetch threads
//! copied it into a discarded buffer to warm the file cache, then the decoder
//! read it again from the cache. And the cache does not hold a 48 GB stack
//! beside the render, so most of it came from the drive anyway, through the
//! cache, at 1.7 GB/s where the drive delivers 5.7 (MEASURED 2026-11-18,
//! A7CR scarab stack, `experiments/a7cr-stacking-performance-2026-11-18`).
//!
//! # How a file is read ([`ReadMode::Auto`])
//!
//! The first 64 KiB are read through the file cache and timed. A file the
//! cache holds returns them in microseconds; then the rest is read through
//! the cache too (13-14 GB/s from memory). Otherwise the rest is read
//! unbuffered, straight from the drive into this buffer (Windows
//! `FILE_FLAG_NO_BUFFERING`): MEASURED 90 against 83 files/s on a Samsung 980
//! PRO and 114 against 73 on a WD SN8100, and it does not push the render's
//! own memory out of the cache. Elsewhere the read is always buffered.
//!
//! # Why the output cannot change
//!
//! Bytes are bytes: a decode that finds its file here decodes exactly the
//! bytes it would have read itself, with every check it makes on them.
//! Scheduling only.
use std::collections::HashMap;
use std::io::Read;
use std::path::{Path, PathBuf};
use std::sync::{Condvar, Mutex};
use std::time::{Duration, Instant};

/// `STREHL_READ_MODE`: `auto` (default), `buffered` or `unbuffered`.
pub const READ_MODE_ENV: &str = "STREHL_READ_MODE";
/// `STREHL_READ_AHEAD_MB`: bytes of files read and not yet decoded (default
/// 3072, at least the largest file).
pub const READ_AHEAD_ENV: &str = "STREHL_READ_AHEAD_MB";

const ALIGN: usize = 4096;
const PROBE: usize = 64 * 1024;
const PIECE: usize = 8 << 20;
/// A cached 64 KiB read returns in a few microseconds; the fastest drive
/// read of it takes tens. Between the two.
const CACHED_PROBE: Duration = Duration::from_micros(40);

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum ReadMode {
    Auto,
    Buffered,
    Unbuffered,
}

impl ReadMode {
    pub fn from_env() -> ReadMode {
        match std::env::var(READ_MODE_ENV).as_deref().map(str::trim) {
            Ok("buffered") => ReadMode::Buffered,
            Ok("unbuffered") => ReadMode::Unbuffered,
            _ => ReadMode::Auto,
        }
    }
}

/// A byte buffer whose start is 4 KiB aligned, as unbuffered reads need.
pub struct AlignedBuf {
    ptr: std::ptr::NonNull<u8>,
    cap: usize,
    len: usize,
}

// SAFETY: an owned allocation, like a Vec<u8>.
unsafe impl Send for AlignedBuf {}
unsafe impl Sync for AlignedBuf {}

impl AlignedBuf {
    fn layout(cap: usize) -> std::alloc::Layout {
        std::alloc::Layout::from_size_align(cap.max(ALIGN), ALIGN).expect("buffer layout")
    }

    fn with_capacity(cap: usize) -> AlignedBuf {
        let cap = cap.div_ceil(ALIGN).max(1) * ALIGN;
        // SAFETY: a non-zero size with a valid alignment.
        let ptr = unsafe { std::alloc::alloc(Self::layout(cap)) };
        let ptr = std::ptr::NonNull::new(ptr)
            .unwrap_or_else(|| std::alloc::handle_alloc_error(Self::layout(cap)));
        AlignedBuf { ptr, cap, len: 0 }
    }

    /// Room for `len` bytes, keeping this allocation when it is big enough.
    fn fit(mut self, len: usize) -> AlignedBuf {
        if self.cap >= len.div_ceil(ALIGN) * ALIGN {
            self.len = 0;
            self
        } else {
            AlignedBuf::with_capacity(len)
        }
    }

    fn spare(&mut self) -> &mut [u8] {
        // SAFETY: `cap` bytes are allocated; bytes past `len` are only
        // written by reads before they are counted into `len`. They may be
        // uninitialised, which `u8` and `read` tolerate (`read` only writes).
        unsafe {
            std::slice::from_raw_parts_mut(self.ptr.as_ptr().add(self.len), self.cap - self.len)
        }
    }

    pub fn capacity(&self) -> usize {
        self.cap
    }
}

impl std::ops::Deref for AlignedBuf {
    type Target = [u8];
    fn deref(&self) -> &[u8] {
        // SAFETY: the first `len` bytes were written by reads.
        unsafe { std::slice::from_raw_parts(self.ptr.as_ptr(), self.len) }
    }
}

impl Drop for AlignedBuf {
    fn drop(&mut self) {
        // SAFETY: allocated in `with_capacity` with this layout.
        unsafe { std::alloc::dealloc(self.ptr.as_ptr(), Self::layout(self.cap)) }
    }
}

/// How one file was read.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Source {
    /// From the system file cache.
    Cache,
    /// From the drive, bypassing the cache.
    Drive,
    /// Through the cache from the drive (buffered mode, or no unbuffered
    /// reads on this system).
    Buffered,
}

/// Read the whole of `path` into `buf` (reused when large enough).
pub fn read_whole(
    path: &Path,
    mode: ReadMode,
    buf: Option<AlignedBuf>,
) -> std::io::Result<(AlignedBuf, Source)> {
    let mut file = std::fs::File::open(path)?;
    let len = file.metadata()?.len() as usize;
    let mut buf = match buf {
        Some(b) => b.fit(len),
        None => AlignedBuf::with_capacity(len),
    };
    let unbuffered_ok = cfg!(windows);
    let mut source = Source::Buffered;
    let probe_first = mode == ReadMode::Auto && unbuffered_ok && len > PROBE;
    if probe_first {
        let start = Instant::now();
        read_into(&mut file, &mut buf, PROBE)?;
        if start.elapsed() <= CACHED_PROBE {
            source = Source::Cache;
        } else {
            source = Source::Drive;
        }
    } else if mode == ReadMode::Unbuffered && unbuffered_ok {
        source = Source::Drive;
    }
    if source == Source::Drive {
        drop(file);
        let mut raw = open_unbuffered(path)?;
        if !buf.len.is_multiple_of(ALIGN) {
            // A short probe read: unbuffered reads must start aligned.
            buf.len = 0;
        }
        if buf.len > 0 {
            use std::io::Seek;
            raw.seek(std::io::SeekFrom::Start(buf.len as u64))?;
        }
        read_into(&mut raw, &mut buf, len)?;
    } else {
        read_into(&mut file, &mut buf, len)?;
    }
    if buf.len != len {
        return Err(std::io::Error::new(
            std::io::ErrorKind::UnexpectedEof,
            format!("{} changed length while it was read", path.display()),
        ));
    }
    Ok((buf, source))
}

/// Read until `buf` holds `upto` bytes or the file ends. Unbuffered reads
/// need aligned offsets and sizes: each asks for a multiple of 4 KiB from an
/// aligned length (the file's end returns fewer, and ends the loop). A read
/// that stops short of `upto` elsewhere can only be buffered, where the next
/// request rounding past `upto` is harmless: the buffer has room for the
/// file's length rounded up, and the file ends there.
fn read_into(file: &mut std::fs::File, buf: &mut AlignedBuf, upto: usize) -> std::io::Result<()> {
    while buf.len < upto {
        let want = if buf.len.is_multiple_of(ALIGN) {
            (upto - buf.len).div_ceil(ALIGN) * ALIGN
        } else {
            upto - buf.len
        };
        let spare = buf.spare();
        let take = want.min(PIECE).min(spare.len());
        let n = file.read(&mut spare[..take])?;
        if n == 0 {
            break;
        }
        buf.len += n;
    }
    Ok(())
}

#[cfg(windows)]
fn open_unbuffered(path: &Path) -> std::io::Result<std::fs::File> {
    use std::os::windows::fs::OpenOptionsExt;
    const FILE_FLAG_NO_BUFFERING: u32 = 0x2000_0000;
    const FILE_FLAG_SEQUENTIAL_SCAN: u32 = 0x0800_0000;
    std::fs::OpenOptions::new()
        .read(true)
        .custom_flags(FILE_FLAG_NO_BUFFERING | FILE_FLAG_SEQUENTIAL_SCAN)
        .open(path)
}

#[cfg(not(windows))]
fn open_unbuffered(path: &Path) -> std::io::Result<std::fs::File> {
    std::fs::File::open(path)
}

enum Entry {
    /// A reader is reading it.
    Reading,
    Ready(AlignedBuf),
    /// Its decode came first and read it itself: a reader must not read it.
    Gone,
}

#[derive(Default)]
struct Shelf {
    files: HashMap<PathBuf, Entry>,
    /// Bytes of `Ready` and `Reading` files.
    bytes: usize,
    /// Buffers handed back by decodes, for the next reads.
    spare: Vec<AlignedBuf>,
    /// Bumped by [`clear`]: a read begun before it is discarded.
    generation: u64,
    counts: [u64; 3],
    bytes_read: u64,
    read_time: Duration,
}

static SHELF: Mutex<Option<Shelf>> = Mutex::new(None);
static CHANGED: Condvar = Condvar::new();

fn limit() -> usize {
    std::env::var(READ_AHEAD_ENV)
        .ok()
        .and_then(|v| v.trim().parse::<usize>().ok())
        .filter(|&mb| mb > 0)
        .unwrap_or(3072)
        << 20
}

fn shelf() -> std::sync::MutexGuard<'static, Option<Shelf>> {
    SHELF.lock().unwrap_or_else(|e| e.into_inner())
}

/// Read `path` and keep it for its decode ([`take`]). Waits while the files
/// kept and not yet decoded reach the read-ahead limit; returns without
/// reading if the file is already kept or being read, or once [`clear`] is
/// called. A failed read keeps nothing: the decode reads the file itself
/// and reports the error.
pub fn fetch(path: &Path) {
    let Ok(meta) = std::fs::metadata(path) else {
        return;
    };
    let size = (meta.len() as usize).div_ceil(ALIGN) * ALIGN;
    let limit = limit().max(size);
    let (generation, buf) = {
        let mut guard = shelf();
        loop {
            let st = guard.get_or_insert_with(Shelf::default);
            if st.files.contains_key(path) {
                return;
            }
            if st.bytes + size <= limit {
                st.files.insert(path.to_owned(), Entry::Reading);
                st.bytes += size;
                break (st.generation, st.spare.pop());
            }
            let g = st.generation;
            guard = CHANGED.wait(guard).unwrap_or_else(|e| e.into_inner());
            if guard.as_ref().is_none_or(|st| st.generation != g) {
                return;
            }
        }
    };
    let start = Instant::now();
    let read = read_whole(path, ReadMode::from_env(), buf);
    let took = start.elapsed();
    let mut guard = shelf();
    let st = guard.get_or_insert_with(Shelf::default);
    if st.generation != generation {
        return;
    }
    match read {
        Ok((buf, source)) => {
            st.counts[source as usize] += 1;
            st.bytes_read += buf.len() as u64;
            st.read_time += took;
            st.files.insert(path.to_owned(), Entry::Ready(buf));
        }
        Err(_) => {
            st.files.remove(path);
            st.bytes -= size;
        }
    }
    drop(guard);
    CHANGED.notify_all();
}

/// The bytes [`fetch`] read for `path`, waiting if a reader is reading them
/// now; `None` when no reader has them (the caller reads the file itself).
pub fn take(path: &Path) -> Option<AlignedBuf> {
    let mut guard = shelf();
    loop {
        let st = guard.as_mut()?;
        match st.files.get(path) {
            None | Some(Entry::Gone) => {
                st.files.insert(path.to_owned(), Entry::Gone);
                return None;
            }
            Some(Entry::Reading) => {
                guard = CHANGED.wait(guard).unwrap_or_else(|e| e.into_inner());
            }
            Some(Entry::Ready(_)) => {
                let Some(Entry::Ready(buf)) = st.files.remove(path) else {
                    unreachable!("checked above");
                };
                st.bytes -= buf.capacity().min(st.bytes);
                drop(guard);
                CHANGED.notify_all();
                return Some(buf);
            }
        }
    }
}

/// Hand a decoded file's buffer back for the next read.
pub fn recycle(buf: AlignedBuf) {
    let mut guard = shelf();
    if let Some(st) = guard.as_mut()
        && st.spare.len() < 8
    {
        st.spare.push(buf);
    }
}

/// Drop every kept file and wake every waiting reader: the render that
/// asked for them is over (or failed).
pub fn clear() {
    let mut guard = shelf();
    if let Some(st) = guard.as_mut() {
        st.generation += 1;
        st.files.clear();
        st.bytes = 0;
        st.spare.clear();
    }
    drop(guard);
    CHANGED.notify_all();
}

/// Files read since the last call: from the cache, from the drive
/// unbuffered, buffered; total bytes; time spent reading (summed over
/// readers).
pub fn take_stats() -> ([u64; 3], u64, Duration) {
    let mut guard = shelf();
    guard.as_mut().map_or(([0; 3], 0, Duration::ZERO), |st| {
        let out = (st.counts, st.bytes_read, st.read_time);
        st.counts = [0; 3];
        st.bytes_read = 0;
        st.read_time = Duration::ZERO;
        out
    })
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn whole_reads_return_the_file_in_every_mode() {
        let dir = tempfile::tempdir().unwrap();
        for len in [
            0usize,
            1,
            4095,
            4096,
            4097,
            PROBE - 1,
            PROBE,
            PROBE + 1,
            3 * PIECE + 12345,
        ] {
            let path = dir.path().join(format!("f{len}"));
            let bytes: Vec<u8> = (0..len).map(|i| (i * 31 + len) as u8).collect();
            std::fs::write(&path, &bytes).unwrap();
            for mode in [ReadMode::Auto, ReadMode::Buffered, ReadMode::Unbuffered] {
                let (buf, _) = read_whole(&path, mode, None).unwrap();
                assert_eq!(&buf[..], &bytes[..], "len {len} {mode:?}");
                assert_eq!(buf.as_ptr() as usize % ALIGN, 0);
                // Reused, a larger buffer still returns exactly the file.
                let big = AlignedBuf::with_capacity(len + 3 * ALIGN);
                let (buf, _) = read_whole(&path, mode, Some(big)).unwrap();
                assert_eq!(&buf[..], &bytes[..], "len {len} {mode:?} reused");
            }
        }
    }

    #[test]
    fn fetched_files_are_taken_once_and_cleared() {
        let dir = tempfile::tempdir().unwrap();
        let path = dir.path().join("a");
        std::fs::write(&path, b"abc").unwrap();
        fetch(&path);
        assert_eq!(take(&path).as_deref(), Some(&b"abc"[..]));
        assert!(take(&path).is_none());
        fetch(&path);
        clear();
        assert!(take(&path).is_none());
    }
}
