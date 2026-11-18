//! Prototypes sizing the second A7CR performance plan. Read-only on the capture.
//!
//!   bench2 pred DIR                 predictor inverse: product form against the row-buffered forms
//!   bench2 dec DIR N T MODE [pin]   decode throughput: N preloaded files decoded on T threads
//!                                   MODE letters: r = row-buffered predictor (else the product's),
//!                                   h = checksum on, s = streaming stores to the destination,
//!                                   o = each thread reads its own file (else files preloaded in RAM)
//!   bench2 ncc                      alignment NCC kernel: product form against offset lanes
//!   bench2 pipe DIR N IO DEC MODE [pin]  readers feeding decoders (see `pipe`); BENCH_FIRST=k skips k files
//!   bench2 fmt DIR                  bits per sample of candidate codes for a second archive format
mod fmt;
mod ncc;

use std::ops::Range;
use std::path::{Path, PathBuf};
use std::sync::atomic::{AtomicUsize, Ordering};
use std::time::Instant;

use sha2::{Digest, Sha256};

fn files(dir: &Path) -> Vec<PathBuf> {
    let mut v: Vec<PathBuf> = std::fs::read_dir(dir)
        .expect("capture folder")
        .filter_map(|e| e.ok().map(|e| e.path()))
        .filter(|p| {
            p.file_name()
                .and_then(|n| n.to_str())
                .is_some_and(|n| n.starts_with("frame-") && n.ends_with(".straw"))
        })
        .collect();
    v.sort();
    v
}

fn secs(t: Instant) -> f64 {
    t.elapsed().as_secs_f64()
}

struct Chunk {
    n: usize,
    mode: u8,
    width: usize,
    payload: Range<usize>,
}

/// The archive's chunk list and its declared SHA-256 (hex).
fn walk(file: &[u8]) -> (Vec<Chunk>, String) {
    let header = strehl_raw_codec::archive::read_header(file).unwrap();
    let body = strehl_raw_codec::archive::HEADER_BYTES as usize;
    let length = header.bytes as usize;
    let (mut at, mut total) = (body + 16, 0usize);
    let mut chunks = Vec::new();
    while total < length {
        let h = &file[at..at + 13];
        let n = u32::from_le_bytes(h[..4].try_into().unwrap()) as usize;
        let packed = u32::from_le_bytes(h[4..8].try_into().unwrap()) as usize;
        let width = u32::from_le_bytes(h[9..13].try_into().unwrap()) as usize;
        chunks.push(Chunk {
            n,
            mode: h[8],
            width,
            payload: at + 13..at + 13 + packed,
        });
        at += 13 + packed;
        total += n;
    }
    (chunks, header.sha256)
}

/// `strehl_raw_codec::cfa::unpredict_into` as it stands (copied; it is private).
fn unpredict_reference(planar: &[u8], width: usize, dst: &mut [u16]) {
    let n = dst.len();
    let (lo, hi) = planar.split_at(n);
    let residual = |i: usize| -> u16 {
        let z = u16::from(lo[i]) | (u16::from(hi[i]) << 8);
        ((z >> 1) as i16 ^ -((z & 1) as i16)) as u16
    };
    let rows = n / width;
    for y in 0..rows.min(2) {
        let row = y * width;
        dst[row] = residual(row);
        dst[row + 1] = residual(row + 1);
        for x in 2..width {
            dst[row + x] = dst[row + x - 2].wrapping_add(residual(row + x));
        }
    }
    for y in 2..rows {
        let row = y * width;
        let (above, current) = dst.split_at_mut(row);
        let up = &above[row - 2 * width..row - width];
        let cur = &mut current[..width];
        let r = |x: usize| residual(row + x);
        cur[0] = up[0].wrapping_add(r(0));
        cur[1] = up[1].wrapping_add(r(1));
        let last = width.saturating_sub(2).max(2);
        for x in 2..last {
            let sum = u32::from(cur[x - 2])
                + u32::from(up[x])
                + u32::from(up[x - 2])
                + u32::from(up[x + 2]);
            cur[x] = ((sum / 4) as u16).wrapping_add(r(x));
        }
        for x in last..width {
            let (left, upv, corner) = (
                u32::from(cur[x - 2]),
                u32::from(up[x]),
                u32::from(up[x - 2]),
            );
            let p = if corner >= left.max(upv) {
                left.min(upv)
            } else if corner <= left.min(upv) {
                left.max(upv)
            } else {
                left + upv - corner
            };
            cur[x] = (p as u16).wrapping_add(r(x));
        }
    }
}

/// Row buffers of the row-buffered predictor: nothing is read back from the
/// destination, so the destination may be write-only (mapped device memory).
#[derive(Default)]
struct Rows {
    /// Residuals of the one or two rows in hand.
    r: [Vec<u16>; 2],
    /// `up[x] + up[x - 2] + up[x + 2]` of the same rows.
    u: [Vec<u32>; 2],
    /// The two rows above (row `y - 2` at index `y & 1`).
    hist: [Vec<u16>; 2],
    /// The rows being built.
    cur: [Vec<u16>; 2],
}

impl Rows {
    fn fit(&mut self, width: usize) {
        for v in self.r.iter_mut().chain(&mut self.hist).chain(&mut self.cur) {
            v.resize(width, 0);
        }
        for v in &mut self.u {
            v.resize(width, 0);
        }
    }
}

#[inline]
fn unzig_row(lo: &[u8], hi: &[u8], out: &mut [u16]) {
    for ((o, &l), &h) in out.iter_mut().zip(lo).zip(hi) {
        let z = u16::from(l) | (u16::from(h) << 8);
        *o = (z >> 1) ^ 0u16.wrapping_sub(z & 1);
    }
}

#[inline]
fn up_sums(up: &[u16], last: usize, u: &mut [u32]) {
    if last <= 2 {
        return;
    }
    let n = last - 2;
    let (a, b, c) = (&up[..n], &up[2..2 + n], &up[4..4 + n]);
    for (((o, &a), &b), &c) in u[2..2 + n].iter_mut().zip(a).zip(b).zip(c) {
        *o = u32::from(a) + u32::from(b) + u32::from(c);
    }
}

#[inline]
fn med_tail(cur: &mut [u16], up: &[u16], r: &[u16], last: usize, width: usize) {
    for x in last..width {
        let (left, upv, corner) = (
            u32::from(cur[x - 2]),
            u32::from(up[x]),
            u32::from(up[x - 2]),
        );
        let p = if corner >= left.max(upv) {
            left.min(upv)
        } else if corner <= left.min(upv) {
            left.max(upv)
        } else {
            left + upv - corner
        };
        cur[x] = (p as u16).wrapping_add(r[x]);
    }
}

/// One interior row from the row two above it: two carried chains.
#[inline]
fn row_one(cur: &mut [u16], up: &[u16], r: &[u16], u: &[u32], width: usize) {
    let last = width.saturating_sub(2).max(2);
    let (mut a, mut b) = (up[0].wrapping_add(r[0]), up[1].wrapping_add(r[1]));
    cur[0] = a;
    cur[1] = b;
    let mut x = 2;
    while x + 1 < last {
        a = (((u32::from(a) + u[x]) >> 2) as u16).wrapping_add(r[x]);
        b = (((u32::from(b) + u[x + 1]) >> 2) as u16).wrapping_add(r[x + 1]);
        cur[x] = a;
        cur[x + 1] = b;
        x += 2;
    }
    if x < last {
        a = (((u32::from(a) + u[x]) >> 2) as u16).wrapping_add(r[x]);
        cur[x] = a;
    }
    med_tail(cur, up, r, last, width);
}

/// Two interior rows (`y`, `y + 1`) at once: they depend only on rows
/// `y - 2` and `y - 1`, so their four chains are independent.
#[inline]
#[allow(clippy::too_many_arguments)]
fn row_pair(
    c0: &mut [u16],
    c1: &mut [u16],
    up0: &[u16],
    up1: &[u16],
    r0: &[u16],
    r1: &[u16],
    u0: &[u32],
    u1: &[u32],
    width: usize,
) {
    let last = width.saturating_sub(2).max(2);
    let (c0, c1) = (&mut c0[..width], &mut c1[..width]);
    let (r0, r1, u0, u1) = (&r0[..width], &r1[..width], &u0[..width], &u1[..width]);
    let (a16, b16) = (up0[0].wrapping_add(r0[0]), up0[1].wrapping_add(r0[1]));
    let (c16, d16) = (up1[0].wrapping_add(r1[0]), up1[1].wrapping_add(r1[1]));
    c0[0] = a16;
    c0[1] = b16;
    c1[0] = c16;
    c1[1] = d16;
    // The carried values live in 32-bit registers holding 16-bit values; each
    // step is add, shift, add, mask: `((sum / 4) as u16).wrapping_add(r)`.
    let (mut a, mut b, mut c, mut d) = (u32::from(a16), u32::from(b16), u32::from(c16), u32::from(d16));
    let mut x = 2;
    if last > 2 && last <= width {
        let pairs = (last - 2) / 2;
        let it = c0[2..2 + 2 * pairs]
            .chunks_exact_mut(2)
            .zip(c1[2..2 + 2 * pairs].chunks_exact_mut(2))
            .zip(u0[2..2 + 2 * pairs].chunks_exact(2).zip(u1[2..2 + 2 * pairs].chunks_exact(2)))
            .zip(r0[2..2 + 2 * pairs].chunks_exact(2).zip(r1[2..2 + 2 * pairs].chunks_exact(2)));
        for (((o0, o1), (p0, p1)), (q0, q1)) in it {
            a = (((a + p0[0]) >> 2) + u32::from(q0[0])) & 0xffff;
            b = (((b + p0[1]) >> 2) + u32::from(q0[1])) & 0xffff;
            c = (((c + p1[0]) >> 2) + u32::from(q1[0])) & 0xffff;
            d = (((d + p1[1]) >> 2) + u32::from(q1[1])) & 0xffff;
            o0[0] = a as u16;
            o0[1] = b as u16;
            o1[0] = c as u16;
            o1[1] = d as u16;
        }
        x = 2 + 2 * pairs;
    }
    if x < last {
        c0[x] = ((((a + u0[x]) >> 2) as u16).wrapping_add(r0[x])) as u16;
        c1[x] = ((((c + u1[x]) >> 2) as u16).wrapping_add(r1[x])) as u16;
    }
    med_tail(c0, up0, r0, last, width);
    med_tail(c1, up1, r1, last, width);
}

/// The same samples as `unpredict_reference`, built in row buffers and handed
/// to `emit` one row at a time, in order (`emit(row index, samples)`).
fn unpredict_rows(planar: &[u8], width: usize, rows: usize, st: &mut Rows, mut emit: impl FnMut(usize, &[u16])) {
    let n = rows * width;
    let (lo, hi) = planar.split_at(n);
    st.fit(width);
    let Rows { r, u, hist, cur } = st;
    for y in 0..rows.min(2) {
        let row = y * width;
        unzig_row(&lo[row..row + width], &hi[row..row + width], &mut r[0]);
        let (c, r) = (&mut cur[0][..width], &r[0][..width]);
        let (mut a, mut b) = (r[0], if width > 1 { r[1] } else { 0 });
        c[0] = a;
        if width > 1 {
            c[1] = b;
        }
        let mut x = 2;
        while x + 1 < width {
            a = a.wrapping_add(r[x]);
            b = b.wrapping_add(r[x + 1]);
            c[x] = a;
            c[x + 1] = b;
            x += 2;
        }
        if x < width {
            c[x] = a.wrapping_add(r[x]);
        }
        emit(y, c);
        std::mem::swap(&mut hist[y & 1], &mut cur[0]);
    }
    let mut y = 2;
    let last = width.saturating_sub(2).max(2);
    while y + 1 < rows {
        let (row0, row1) = (y * width, (y + 1) * width);
        let (ra, rb) = r.split_at_mut(1);
        unzig_row(&lo[row0..row0 + width], &hi[row0..row0 + width], &mut ra[0]);
        unzig_row(&lo[row1..row1 + width], &hi[row1..row1 + width], &mut rb[0]);
        let (ua, ub) = u.split_at_mut(1);
        up_sums(&hist[y & 1], last, &mut ua[0]);
        up_sums(&hist[(y + 1) & 1], last, &mut ub[0]);
        let (ca, cb) = cur.split_at_mut(1);
        row_pair(
            &mut ca[0],
            &mut cb[0],
            &hist[y & 1],
            &hist[(y + 1) & 1],
            &ra[0],
            &rb[0],
            &ua[0],
            &ub[0],
            width,
        );
        emit(y, &ca[0][..width]);
        emit(y + 1, &cb[0][..width]);
        std::mem::swap(&mut hist[y & 1], &mut ca[0]);
        std::mem::swap(&mut hist[(y + 1) & 1], &mut cb[0]);
        y += 2;
    }
    if y < rows {
        let row = y * width;
        unzig_row(&lo[row..row + width], &hi[row..row + width], &mut r[0]);
        up_sums(&hist[y & 1], last, &mut u[0]);
        let (ca, _) = cur.split_at_mut(1);
        row_one(&mut ca[0], &hist[y & 1], &r[0], &u[0], width);
        emit(y, &ca[0][..width]);
        std::mem::swap(&mut hist[y & 1], &mut ca[0]);
    }
}

fn unpredict_rowbuf(planar: &[u8], width: usize, dst: &mut [u16], st: &mut Rows) {
    let rows = dst.len() / width;
    unpredict_rows(planar, width, rows, st, |y, row| {
        dst[y * width..(y + 1) * width].copy_from_slice(row);
    });
}

fn chunks_of(path: &Path) -> Vec<(usize, Vec<u8>)> {
    let file = std::fs::read(path).unwrap();
    let (chunks, _) = walk(&file);
    chunks
        .iter()
        .filter(|c| c.mode == 8)
        .map(|c| (c.width, zstd::bulk::decompress(&file[c.payload.clone()], c.n).unwrap()))
        .collect()
}

fn pred(dir: &Path) {
    let paths = files(dir);
    for p in &paths[40..43] {
        let planar = chunks_of(p);
        let mut a: Vec<Vec<u16>> = planar.iter().map(|(_, b)| vec![0u16; b.len() / 2]).collect();
        let mut b = a.clone();
        let mut st = Rows::default();
        let mut best = [f64::INFINITY; 2];
        for _ in 0..5 {
            let t = Instant::now();
            for ((w, bytes), out) in planar.iter().zip(a.iter_mut()) {
                unpredict_reference(bytes, *w, out);
            }
            best[0] = best[0].min(secs(t));
            let t = Instant::now();
            for ((w, bytes), out) in planar.iter().zip(b.iter_mut()) {
                unpredict_rowbuf(bytes, *w, out, &mut st);
            }
            best[1] = best[1].min(secs(t));
        }
        let samples: usize = a.iter().map(Vec::len).sum();
        println!(
            "{}: {} CFA chunks, {:.1} M samples | product predictor {:.4} s ({:.2} ns/sample) | row-buffered, two rows at once {:.4} s ({:.2} ns/sample) | identical: {}",
            p.file_name().unwrap().to_string_lossy(),
            planar.len(),
            samples as f64 / 1e6,
            best[0],
            1e9 * best[0] / samples as f64,
            best[1],
            1e9 * best[1] / samples as f64,
            a == b
        );
    }
    let mut state = 0x9e3779b97f4a7c15u64;
    let mut next = || {
        state ^= state << 13;
        state ^= state >> 7;
        state ^= state << 17;
        state
    };
    let mut all = true;
    let mut cases = 0;
    let mut st = Rows::default();
    for width in [2usize, 3, 4, 5, 6, 7, 8, 9, 16, 33, 64, 257] {
        for rows in [1usize, 2, 3, 4, 5, 6, 9, 16, 17] {
            for extreme in [false, true] {
                let n = width * rows;
                let bytes: Vec<u8> = (0..2 * n)
                    .map(|_| if extreme { (next() as u8) | 0x80 } else { next() as u8 })
                    .collect();
                let (mut a, mut b) = (vec![0u16; n], vec![0u16; n]);
                unpredict_reference(&bytes, width, &mut a);
                unpredict_rowbuf(&bytes, width, &mut b, &mut st);
                all &= a == b;
                cases += 1;
            }
        }
    }
    println!("random residuals, {cases} shapes (widths 2-257, 1-17 rows, full-range values): identical: {all}");
}

/// Where the row-buffered predictor's time goes, on one chunk kept in cache.
fn predparts(dir: &Path) {
    let paths = files(dir);
    let planar = chunks_of(&paths[41]);
    let (width, bytes) = &planar[20];
    let width = *width;
    let n = bytes.len() / 2;
    let rows = n / width;
    let (lo, hi) = bytes.split_at(n);
    let mut st = Rows::default();
    st.fit(width);
    let mut out = vec![0u16; n];
    let reps = 40;
    let per = |t: Instant| 1e9 * secs(t) / (reps * n) as f64;
    let last = width - 2;
    // (a) residuals only
    let t = Instant::now();
    for _ in 0..reps {
        for y in 0..rows {
            unzig_row(&lo[y * width..(y + 1) * width], &hi[y * width..(y + 1) * width], &mut st.r[y & 1]);
        }
        std::hint::black_box(&st.r);
    }
    let a = per(t);
    // (b) the three-neighbour sums only (from a fixed row)
    let up: Vec<u16> = (0..width).map(|x| (x * 37 % 16000) as u16).collect();
    let t = Instant::now();
    for _ in 0..reps {
        for y in 0..rows {
            up_sums(&up, last, &mut st.u[y & 1]);
        }
        std::hint::black_box(&st.u);
    }
    let b = per(t);
    // (c) the chains only, two rows at once, from fixed inputs
    let r0: Vec<u16> = (0..width).map(|x| (x * 13 % 64) as u16).collect();
    let mut u0 = vec![0u32; width];
    up_sums(&up, last, &mut u0);
    let (mut c0, mut c1) = (vec![0u16; width], vec![0u16; width]);
    let t = Instant::now();
    for _ in 0..reps {
        for _ in 0..rows / 2 {
            row_pair(&mut c0, &mut c1, &up, &up, &r0, &r0, &u0, &u0, width);
        }
        std::hint::black_box((&c0, &c1));
    }
    let c = per(t);
    // (d) the copy out only
    let t = Instant::now();
    for _ in 0..reps {
        for y in 0..rows {
            out[y * width..(y + 1) * width].copy_from_slice(&c0);
        }
        std::hint::black_box(&out);
    }
    let d = per(t);
    // (e) everything
    let t = Instant::now();
    for _ in 0..reps {
        unpredict_rowbuf(bytes, width, &mut out, &mut st);
        std::hint::black_box(&out);
    }
    let e = per(t);
    let mut reference = vec![0u16; n];
    let t = Instant::now();
    for _ in 0..reps {
        unpredict_reference(bytes, width, &mut reference);
        std::hint::black_box(&reference);
    }
    let f = per(t);
    println!(
        "one chunk ({rows} rows x {width}) in cache, ns per sample: residuals {a:.3} | neighbour sums {b:.3} | chains {c:.3} | copy out {d:.3} | whole row-buffered {e:.3} | product {f:.3} | identical {}",
        out == reference
    );
}

#[derive(Default)]
struct State {
    scratch: Vec<u8>,
    rows: Rows,
    samples: Vec<u16>,
    file: Vec<u8>,
}

#[cfg(target_arch = "x86_64")]
#[inline]
fn stream_copy(dst: &mut [u16], src: &[u16]) {
    use std::arch::x86_64::{__m128i, _mm_loadu_si128, _mm_stream_si128};
    let n = dst.len().min(src.len());
    let (d, s) = (dst.as_mut_ptr(), src.as_ptr());
    if (d as usize) % 16 != 0 {
        dst[..n].copy_from_slice(&src[..n]);
        return;
    }
    let mut i = 0;
    // SAFETY: both ranges are in bounds; the destination is 16-byte aligned.
    unsafe {
        while i + 8 <= n {
            _mm_stream_si128(d.add(i).cast::<__m128i>(), _mm_loadu_si128(s.add(i).cast::<__m128i>()));
            i += 8;
        }
    }
    dst[i..n].copy_from_slice(&src[i..n]);
}

/// One archive decoded on the calling thread. Returns whether the checksum
/// matched (true when not asked for).
#[allow(clippy::too_many_arguments)]
fn decode_one(
    file: &[u8],
    ctx: &mut zstd::bulk::Decompressor<'static>,
    st: &mut State,
    rowbuf: bool,
    hash: bool,
    stream: bool,
    times: &mut [f64; 3],
) -> bool {
    let (chunks, declared) = walk(file);
    let total: usize = chunks.iter().filter(|c| c.mode == 8).map(|c| c.n / 2).sum();
    st.samples.resize(total, 0);
    let mut sha = Sha256::new();
    let mut filled = 0usize;
    let State { scratch, rows, samples, .. } = st;
    for c in &chunks {
        let payload = &file[c.payload.clone()];
        match c.mode {
            8 => {
                scratch.resize(c.n, 0);
                let t = Instant::now();
                let got = ctx.decompress_to_buffer(payload, &mut scratch[..]).unwrap();
                times[0] += secs(t);
                assert_eq!(got, c.n);
                let dst = &mut samples[filled..filled + c.n / 2];
                let t = Instant::now();
                if rowbuf {
                    let height = c.n / 2 / c.width;
                    let width = c.width;
                    unpredict_rows(scratch, width, height, rows, |y, row| {
                        if hash {
                            let bytes: &[u8] =
                                unsafe { std::slice::from_raw_parts(row.as_ptr().cast::<u8>(), row.len() * 2) };
                            sha.update(bytes);
                        }
                        let out = &mut dst[y * width..(y + 1) * width];
                        if stream {
                            stream_copy(out, row);
                        } else {
                            out.copy_from_slice(row);
                        }
                    });
                    times[1] += secs(t);
                } else {
                    unpredict_reference(scratch, c.width, dst);
                    times[1] += secs(t);
                    if hash {
                        let t = Instant::now();
                        let bytes: &[u8] = unsafe { std::slice::from_raw_parts(dst.as_ptr().cast::<u8>(), c.n) };
                        sha.update(bytes);
                        times[2] += secs(t);
                    }
                }
                filled += c.n / 2;
            }
            255 => {
                if hash {
                    sha.update(payload);
                }
            }
            _ => {
                scratch.resize(c.n, 0);
                let got = ctx.decompress_to_buffer(payload, &mut scratch[..]).unwrap();
                assert_eq!(got, c.n);
                if hash {
                    sha.update(&scratch[..c.n]);
                }
            }
        }
    }
    if !hash {
        return true;
    }
    let sum: String = sha.finalize().iter().map(|b| format!("{b:02x}")).collect();
    sum == declared
}

#[cfg(windows)]
fn pin(logical: usize) {
    unsafe extern "system" {
        fn GetCurrentThread() -> isize;
        fn SetThreadAffinityMask(thread: isize, mask: usize) -> usize;
    }
    // SAFETY: a valid one-bit mask for the calling thread.
    unsafe {
        SetThreadAffinityMask(GetCurrentThread(), 1usize << logical);
    }
}

#[cfg(not(windows))]
fn pin(_logical: usize) {}

fn dec(dir: &Path, n: usize, threads: usize, mode: &str, pinning: &str) {
    let (rowbuf, hash, stream, own) = (
        mode.contains('r'),
        mode.contains('h'),
        mode.contains('s'),
        mode.contains('o'),
    );
    let paths = files(dir);
    let paths: Vec<PathBuf> = paths.into_iter().skip(100).take(n).collect();
    let preloaded: Vec<Vec<u8>> = if own {
        Vec::new()
    } else {
        paths.iter().map(|p| std::fs::read(p).unwrap()).collect()
    };
    // Each preloaded file is decoded `reps` times so the run is long enough to time.
    let reps = if own { 1 } else { (threads * 12).div_ceil(n).max(1) };
    let jobs = paths.len() * reps;
    let next = AtomicUsize::new(0);
    let bad = AtomicUsize::new(0);
    let per_thread: Vec<std::sync::Mutex<(usize, f64, [f64; 3])>> =
        (0..threads).map(|_| std::sync::Mutex::new((0, 0.0, [0.0; 3]))).collect();
    let t = Instant::now();
    std::thread::scope(|s| {
        for i in 0..threads {
            let (next, bad, paths, preloaded, per_thread) = (&next, &bad, &paths, &preloaded, &per_thread);
            s.spawn(move || {
                match pinning {
                    // One thread per physical core (logical processors 0, 2, 4, ...).
                    "cores" => pin((2 * i) % 32),
                    // The first half of the cores only (the 3D V-Cache half here).
                    "ccd0" => pin((2 * i) % 16),
                    // The second half of the cores only.
                    "ccd1" => pin(16 + (2 * i) % 16),
                    _ => {}
                }
                let mut st = State::default();
                let mut ctx = zstd::bulk::Decompressor::new().unwrap();
                let mut mine = (0usize, 0.0f64, [0.0f64; 3]);
                loop {
                    let j = next.fetch_add(1, Ordering::Relaxed);
                    if j >= jobs {
                        break;
                    }
                    let k = j % paths.len();
                    let t = Instant::now();
                    let ok = if own {
                        use std::io::Read;
                        let mut file = std::mem::take(&mut st.file);
                        file.clear();
                        std::fs::File::open(&paths[k]).unwrap().read_to_end(&mut file).unwrap();
                        let ok = decode_one(&file, &mut ctx, &mut st, rowbuf, hash, stream, &mut mine.2);
                        st.file = file;
                        ok
                    } else {
                        decode_one(&preloaded[k], &mut ctx, &mut st, rowbuf, hash, stream, &mut mine.2)
                    };
                    mine.0 += 1;
                    mine.1 += secs(t);
                    if !ok {
                        bad.fetch_add(1, Ordering::Relaxed);
                    }
                    std::hint::black_box(st.samples[st.samples.len() / 2]);
                }
                *per_thread[i].lock().unwrap() = mine;
            });
        }
    });
    let wall = secs(t);
    let per: Vec<(usize, f64, [f64; 3])> = per_thread.iter().map(|m| *m.lock().unwrap()).collect();
    let files_done: usize = per.iter().map(|p| p.0).sum();
    let mean = |f: &dyn Fn(&(usize, f64, [f64; 3])) -> f64| {
        1e3 * per.iter().map(f).sum::<f64>() / files_done.max(1) as f64
    };
    let half = threads / 2;
    let side = |range: Range<usize>| {
        let (n, s) = per[range].iter().fold((0usize, 0.0), |a, p| (a.0 + p.0, a.1 + p.1));
        1e3 * s / n.max(1) as f64
    };
    println!(
        "mode {mode:<4} pin {pinning:<5} {threads:>2} threads, {files_done} decodes of {} files: {wall:.2} s, {:.1} files/s | per file {:.1} ms: zstd {:.1}, predictor{} {:.1}, checksum {:.1} | first half of threads {:.1} ms, second half {:.1} ms | checksum failures {}",
        paths.len(),
        files_done as f64 / wall,
        mean(&|p| p.1),
        mean(&|p| p.2[0]),
        if rowbuf && hash { "+checksum" } else { "" },
        mean(&|p| p.2[1]),
        mean(&|p| p.2[2]),
        side(0..half.max(1)),
        side(half..threads),
        bad.load(Ordering::Relaxed)
    );
}

const NO_BUFFERING: u32 = 0x2000_0000;

/// Drop a file's pages from the system cache (opening it unbuffered does).
fn purge(path: &Path) {
    #[cfg(windows)]
    {
        use std::os::windows::fs::OpenOptionsExt;
        let _ = std::fs::OpenOptions::new().read(true).custom_flags(NO_BUFFERING).open(path);
    }
    #[cfg(not(windows))]
    let _ = path;
}

/// A page-aligned window into a heap buffer, for unbuffered reads.
struct Aligned {
    store: Vec<u8>,
    at: usize,
    len: usize,
}

impl Aligned {
    fn new(capacity: usize) -> Self {
        let store = vec![0u8; capacity + 8192];
        let at = (4096 - store.as_ptr() as usize % 4096) % 4096;
        Self { store, at, len: 0 }
    }
    fn bytes(&self) -> &[u8] {
        &self.store[self.at..self.at + self.len]
    }
    fn fill(&mut self, path: &Path, unbuffered: bool) {
        use std::io::Read;
        let mut options = std::fs::OpenOptions::new();
        options.read(true);
        #[cfg(windows)]
        if unbuffered {
            use std::os::windows::fs::OpenOptionsExt;
            options.custom_flags(NO_BUFFERING);
        }
        let mut f = options.open(path).unwrap();
        let size = f.metadata().unwrap().len() as usize;
        let want = size.next_multiple_of(4096);
        assert!(want <= self.store.len() - self.at);
        let mut got = 0;
        while got < size {
            let n = f.read(&mut self.store[self.at + got..self.at + want]).unwrap();
            if n == 0 {
                break;
            }
            got += n;
        }
        assert_eq!(got, size);
        self.len = size;
    }
}

/// The supply a fold could have: `io` threads read whole files in plan order
/// and hand them to `decoders` threads (row-buffered predictor, checksum on
/// unless MODE lacks `h`). MODE `u` reads unbuffered, `c` purges the files
/// from the system cache first (a cold start).
fn pipe(dir: &Path, n: usize, io: usize, decoders: usize, mode: &str, pinning: &str) {
    let (hash, unbuffered, cold) = (mode.contains('h'), mode.contains('u'), mode.contains('c'));
    let paths = files(dir);
    let first = std::env::var("BENCH_FIRST")
        .ok()
        .and_then(|v| v.parse().ok())
        .unwrap_or(if cold { 300 } else { 100 });
    let paths: Vec<PathBuf> = paths.into_iter().skip(first).take(n).collect();
    if cold {
        for p in &paths {
            purge(p);
        }
    }
    let slots = decoders + io + 4;
    let (spare_tx, spare_rx) = std::sync::mpsc::channel::<Aligned>();
    for _ in 0..slots {
        spare_tx.send(Aligned::new(80 << 20)).unwrap();
    }
    let spare_rx = std::sync::Mutex::new(spare_rx);
    let (full_tx, full_rx) = std::sync::mpsc::sync_channel::<Aligned>(slots);
    let full_rx = std::sync::Mutex::new(full_rx);
    let next = AtomicUsize::new(0);
    let bad = AtomicUsize::new(0);
    let decode_busy = std::sync::Mutex::new(0f64);
    let read_busy = std::sync::Mutex::new(0f64);
    let starved = std::sync::Mutex::new(0f64);
    let t = Instant::now();
    std::thread::scope(|s| {
        for _ in 0..io {
            let (next, paths, spare_rx, full_tx, read_busy) = (&next, &paths, &spare_rx, full_tx.clone(), &read_busy);
            s.spawn(move || {
                let mut busy = 0.0;
                loop {
                    let k = next.fetch_add(1, Ordering::Relaxed);
                    if k >= paths.len() {
                        break;
                    }
                    let mut buf = spare_rx.lock().unwrap().recv().unwrap();
                    let t = Instant::now();
                    buf.fill(&paths[k], unbuffered);
                    busy += secs(t);
                    full_tx.send(buf).unwrap();
                }
                *read_busy.lock().unwrap() += busy;
            });
        }
        drop(full_tx);
        for i in 0..decoders {
            let (full_rx, spare_tx, bad, decode_busy, starved) = (&full_rx, spare_tx.clone(), &bad, &decode_busy, &starved);
            s.spawn(move || {
                match pinning {
                    "cores" => pin((2 * i) % 32),
                    _ => {}
                }
                let mut st = State::default();
                let mut ctx = zstd::bulk::Decompressor::new().unwrap();
                let mut times = [0.0; 3];
                let (mut busy, mut idle) = (0.0, 0.0);
                loop {
                    let t = Instant::now();
                    let got = full_rx.lock().unwrap().recv();
                    idle += secs(t);
                    let Ok(buf) = got else { break };
                    let t = Instant::now();
                    if !decode_one(buf.bytes(), &mut ctx, &mut st, true, hash, false, &mut times) {
                        bad.fetch_add(1, Ordering::Relaxed);
                    }
                    busy += secs(t);
                    let _ = spare_tx.send(buf);
                }
                *decode_busy.lock().unwrap() += busy;
                *starved.lock().unwrap() += idle;
            });
        }
    });
    let wall = secs(t);
    println!(
        "pipe mode {mode:<4} {io} readers -> {decoders} decoders ({pinning}), {} files: {wall:.2} s, {:.1} files/s ({:.2} GB/s read) | readers busy {:.0} %, decoders busy {:.0} % (waiting for a file {:.0} %) | checksum failures {}",
        paths.len(),
        paths.len() as f64 / wall,
        paths.len() as f64 * 62.0e6 / 1e9 / wall,
        100.0 * *read_busy.lock().unwrap() / (wall * io as f64),
        100.0 * *decode_busy.lock().unwrap() / (wall * decoders as f64),
        100.0 * *starved.lock().unwrap() / (wall * decoders as f64),
        bad.load(Ordering::Relaxed)
    );
}

fn main() {
    let a: Vec<String> = std::env::args().collect();
    match a.get(1).map(String::as_str) {
        Some("pipe") => pipe(
            Path::new(&a[2]),
            a[3].parse().unwrap(),
            a[4].parse().unwrap(),
            a[5].parse().unwrap(),
            &a[6],
            a.get(7).map_or("none", String::as_str),
        ),
        Some("fmt") => fmt::run(Path::new(&a[2]), |p| {
            let file = std::fs::read(p).unwrap();
            let width = walk(&file).0.iter().find(|c| c.mode == 8).unwrap().width;
            let mut st = State::default();
            let mut ctx = zstd::bulk::Decompressor::new().unwrap();
            decode_one(&file, &mut ctx, &mut st, true, false, false, &mut [0.0; 3]);
            (st.samples, width, file.len() as u64)
        }),
        Some("pred") => pred(Path::new(&a[2])),
        Some("predparts") => predparts(Path::new(&a[2])),
        Some("dec") => dec(
            Path::new(&a[2]),
            a[3].parse().unwrap(),
            a[4].parse().unwrap(),
            &a[5],
            a.get(6).map_or("none", String::as_str),
        ),
        Some("ncc") => ncc::run(),
        _ => eprintln!("see the module comment"),
    }
}
