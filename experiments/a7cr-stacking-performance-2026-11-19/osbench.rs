//! OS-primitive costs that a stacking engine pays, the same source on Windows
//! and Linux (std only): first-touch page faults, thread hand-offs, and file
//! reads (direct and cached).
//!
//!   rustc -O osbench.rs && osbench <scratch dir> [file GiB, default 4]
use std::alloc::{alloc, dealloc, Layout};
use std::fs::{File, OpenOptions};
use std::io::{Read, Write};
use std::path::PathBuf;
use std::sync::{Arc, Barrier};
use std::time::Instant;

const PAGE: usize = 4096;

#[cfg(windows)]
fn direct(o: &mut OpenOptions) {
    use std::os::windows::fs::OpenOptionsExt;
    o.custom_flags(0x2000_0000); // FILE_FLAG_NO_BUFFERING
}
#[cfg(unix)]
fn direct(o: &mut OpenOptions) {
    use std::os::unix::fs::OpenOptionsExt;
    o.custom_flags(0o40000); // O_DIRECT (x86-64)
}
#[cfg(windows)]
fn read_at(f: &File, buf: &mut [u8], at: u64) -> usize {
    use std::os::windows::fs::FileExt;
    f.seek_read(buf, at).unwrap()
}
#[cfg(unix)]
fn read_at(f: &File, buf: &mut [u8], at: u64) -> usize {
    use std::os::unix::fs::FileExt;
    f.read_at(buf, at).unwrap()
}

struct Aligned(*mut u8, Layout);
unsafe impl Send for Aligned {}
impl Aligned {
    fn new(len: usize) -> Self {
        let l = Layout::from_size_align(len, PAGE).unwrap();
        Aligned(unsafe { alloc(l) }, l)
    }
    fn slice(&mut self) -> &mut [u8] {
        unsafe { std::slice::from_raw_parts_mut(self.0, self.1.size()) }
    }
}
impl Drop for Aligned {
    fn drop(&mut self) {
        unsafe { dealloc(self.0, self.1) }
    }
}

/// First touch of fresh memory: `threads` threads each map `bytes / threads`
/// and write one byte per 4 KiB page.
fn faults(bytes: usize, threads: usize) -> (f64, f64) {
    let each = bytes / threads / PAGE * PAGE;
    let gate = Arc::new(Barrier::new(threads + 1));
    let hs: Vec<_> = (0..threads)
        .map(|_| {
            let gate = gate.clone();
            std::thread::spawn(move || {
                let mut m = Aligned::new(each);
                gate.wait();
                let t = Instant::now();
                let mut i = 0;
                while i < each {
                    unsafe { m.0.add(i).write_volatile(1) };
                    i += PAGE;
                }
                let touch = t.elapsed().as_secs_f64();
                let t = Instant::now();
                drop(m);
                (touch, t.elapsed().as_secs_f64())
            })
        })
        .collect();
    gate.wait();
    let t = Instant::now();
    let r: Vec<(f64, f64)> = hs.into_iter().map(|h| h.join().unwrap()).collect();
    let wall = t.elapsed().as_secs_f64();
    let pages = (each / PAGE * threads) as f64;
    let touch: f64 = r.iter().map(|x| x.0).sum::<f64>() / threads as f64;
    // ns per page on each thread, and pages per second of wall time
    (touch * 1e9 / (each / PAGE) as f64, pages / wall)
}

/// Second touch of memory that is already mapped: the cost with no fault.
fn retouch(bytes: usize) -> f64 {
    let mut m = Aligned::new(bytes);
    let mut i = 0;
    while i < bytes {
        unsafe { m.0.add(i).write_volatile(1) };
        i += PAGE;
    }
    let t = Instant::now();
    let mut i = 0;
    while i < bytes {
        unsafe { m.0.add(i).write_volatile(2) };
        i += PAGE;
    }
    t.elapsed().as_secs_f64() * 1e9 / (bytes / PAGE) as f64
}

/// Round trips between two threads through channels (a blocked thread woken
/// by another, as a decoder is by the fold).
fn ping(rounds: usize) -> f64 {
    use std::sync::mpsc::sync_channel;
    let (a, b) = sync_channel::<u32>(0);
    let (c, d) = sync_channel::<u32>(0);
    let h = std::thread::spawn(move || {
        while let Ok(v) = b.recv() {
            if c.send(v).is_err() {
                break;
            }
        }
    });
    let t = Instant::now();
    for i in 0..rounds {
        a.send(i as u32).unwrap();
        d.recv().unwrap();
    }
    let e = t.elapsed().as_secs_f64();
    drop(a);
    h.join().unwrap();
    e * 1e9 / rounds as f64
}

fn make(path: &PathBuf, bytes: usize) {
    let mut f = File::create(path).unwrap();
    let mut block = vec![0u8; 8 << 20];
    let mut x = 0x9E37_79B9_7F4A_7C15u64;
    for b in block.chunks_mut(8) {
        x ^= x << 13;
        x ^= x >> 7;
        x ^= x << 17;
        b.copy_from_slice(&x.to_le_bytes());
    }
    let mut left = bytes;
    while left > 0 {
        let n = left.min(block.len());
        f.write_all(&block[..n]).unwrap();
        left -= n;
    }
    f.sync_all().unwrap();
}

/// `threads` readers, each over its own share of the file, in `block` pieces.
fn read(path: &PathBuf, bytes: usize, threads: usize, block: usize, unbuffered: bool) -> f64 {
    let each = bytes / threads / block * block;
    let gate = Arc::new(Barrier::new(threads + 1));
    let hs: Vec<_> = (0..threads)
        .map(|k| {
            let gate = gate.clone();
            let path = path.clone();
            std::thread::spawn(move || {
                let mut o = OpenOptions::new();
                o.read(true);
                if unbuffered {
                    direct(&mut o);
                }
                let f = o.open(&path).unwrap();
                let mut buf = Aligned::new(block);
                gate.wait();
                let base = (k * each) as u64;
                let mut done = 0usize;
                let mut sum = 0u64;
                while done < each {
                    let n = read_at(&f, buf.slice(), base + done as u64);
                    assert!(n > 0);
                    sum += buf.slice()[0] as u64;
                    done += n;
                }
                sum
            })
        })
        .collect();
    gate.wait();
    let t = Instant::now();
    for h in hs {
        h.join().unwrap();
    }
    (each * threads) as f64 / t.elapsed().as_secs_f64() / (1u64 << 30) as f64
}

/// Open, read 64 KiB and close `n` times: the per-file cost of small reads
/// (archive headers, journals).
fn opens(path: &PathBuf, n: usize) -> f64 {
    let mut buf = vec![0u8; 65536];
    let t = Instant::now();
    for _ in 0..n {
        let mut f = File::open(path).unwrap();
        f.read_exact(&mut buf).unwrap();
    }
    t.elapsed().as_secs_f64() * 1e6 / n as f64
}

fn main() {
    let args: Vec<String> = std::env::args().collect();
    let gib: usize = args.get(2).map_or(4, |s| s.parse().unwrap());
    println!("os={} cpus={}", std::env::consts::OS, std::thread::available_parallelism().unwrap());
    for &t in &[1usize, 4, 16] {
        let best = (0..3).map(|_| faults(8 << 30, t)).fold((f64::INFINITY, 0.0f64), |a, b| (a.0.min(b.0), a.1.max(b.1)));
        println!("first touch, {t:2} threads: {:.0} ns/page per thread, {:.2} M pages/s ({:.1} GiB/s)", best.0, best.1 / 1e6, best.1 * 4096.0 / (1u64 << 30) as f64);
    }
    println!("second touch (no fault): {:.1} ns/page", retouch(2 << 30));
    println!("thread round trip: {:.0} ns", (0..3).map(|_| ping(200_000)).fold(f64::INFINITY, f64::min));
    if let Some(dir) = args.get(1) {
        let path = PathBuf::from(dir).join("osbench.tmp");
        make(&path, gib << 30);
        let bytes = gib << 30;
        for &(t, block) in &[(1usize, 64usize << 20), (4, 64 << 20), (8, 64 << 20), (4, 1 << 20)] {
            let r = (0..2).map(|_| read(&path, bytes, t, block, true)).fold(0.0, f64::max);
            println!("direct read, {t} threads, {} MiB blocks: {r:.2} GiB/s", block >> 20);
        }
        read(&path, bytes, 4, 8 << 20, false);
        for &t in &[1usize, 4, 16] {
            let r = (0..2).map(|_| read(&path, bytes, t, 8 << 20, false)).fold(0.0, f64::max);
            println!("cached read, {t} threads, 8 MiB blocks: {r:.2} GiB/s");
        }
        println!("open + 64 KiB read + close: {:.1} us", opens(&path, 20_000));
        std::fs::remove_file(&path).unwrap();
    }
}
