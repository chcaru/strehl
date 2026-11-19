//! Direct CFA access for plain-strip TIFF RAWs (Sony uncompressed), archived
//! or not, without materialising the original file a second time.
//!
//! [`decode_archive`] decodes an `STRHARC1` archive's CFA chunks in parallel
//! straight into a `u16` sample buffer, keeps only the metadata bytes before
//! and after the strip, and still verifies the archive's whole-file SHA-256:
//! on a little-endian host the sample buffer *is* the strip's original bytes,
//! so hashing prefix, samples and suffix in order hashes the original file.
//! [`read_plain`] does the same for an unarchived file by reading the strip
//! directly into the buffer.
//!
//! Both return `Ok(None)` when the file is not a single plain 14/16-bit CFA
//! strip of the shape [`crate::layout`] accepts; callers then use the
//! general route ([`crate::archive::read_original`] and a full decoder).
use crate::{
    MAGIC as TRANSPORT_MAGIC, MAX_CHUNK, MAX_CHUNKS, MAX_RAW, archive, raw_ifd, valid_cfa,
};
use anyhow::{Context, Result, bail, ensure};
use rayon::prelude::*;
use sha2::{Digest, Sha256};
use std::{
    fs::File,
    io::{Read, Seek, SeekFrom},
    path::Path,
};

/// Default crop from the raw IFD: `DefaultCropOrigin`/`DefaultCropSize`
/// (0xC61F/0xC620) or Sony's own pair (0x74C7/0x74C8). When both pairs are
/// present they must agree.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct Crop {
    pub x: usize,
    pub y: usize,
    pub width: usize,
    pub height: usize,
}

pub struct CfaFile {
    /// Original bytes before the strip: all TIFF metadata a decoder needs.
    pub prefix: Vec<u8>,
    pub width: usize,
    pub height: usize,
    /// Row-major samples, `width * height`, exactly the strip's values.
    pub samples: Vec<u16>,
    /// Crop declared in the raw IFD, validated against the strip.
    pub crop: Option<Crop>,
    /// Whether the original file's SHA-256 was checked (archives only).
    pub verified_sha256: bool,
    /// The original file's SHA-256 the archive's envelope declares (lower
    /// case hex); empty for an unarchived file.
    pub declared_sha256: String,
    /// A full archive decode's original bytes after the strip (the rest of
    /// the TIFF metadata) and the original file's length: with `prefix`,
    /// every metadata byte (`archive::sparse_from_parts`). Empty, and 0, for
    /// a partial decode or an unarchived file.
    pub suffix: Vec<u8>,
    pub original_length: u64,
    /// [`decode_archive_rows`]: the sample rows decoded (a superset of those
    /// asked for, whole chunks); every other row is unspecified. `None` when
    /// every row was decoded.
    pub decoded_rows: Option<Vec<bool>>,
}

fn u16_at(b: &[u8], at: usize) -> Option<u16> {
    Some(u16::from_le_bytes(
        b.get(at..at.checked_add(2)?)?.try_into().ok()?,
    ))
}
fn u32_at(b: &[u8], at: usize) -> Option<u32> {
    Some(u32::from_le_bytes(
        b.get(at..at.checked_add(4)?)?.try_into().ok()?,
    ))
}

/// Read a two-value integer tag (SHORT, LONG or integral RATIONAL) from the
/// IFD at `ifd`. `None` if absent or not representable.
fn pair(bytes: &[u8], ifd: usize, wanted: u16) -> Option<Option<(usize, usize)>> {
    let count = usize::from(u16_at(bytes, ifd)?);
    for i in 0..count {
        let p = ifd + 2 + 12 * i;
        if u16_at(bytes, p)? != wanted {
            continue;
        }
        let typ = u16_at(bytes, p + 2)?;
        let n = u32_at(bytes, p + 4)?;
        if n != 2 {
            return None;
        }
        let values = match typ {
            3 => (
                u16_at(bytes, p + 8)? as usize,
                u16_at(bytes, p + 10)? as usize,
            ),
            4 => {
                let at = u32_at(bytes, p + 8)? as usize;
                (u32_at(bytes, at)? as usize, u32_at(bytes, at + 4)? as usize)
            }
            5 => {
                let at = u32_at(bytes, p + 8)? as usize;
                let (a, b) = (u32_at(bytes, at)?, u32_at(bytes, at + 4)?);
                let (c, d) = (u32_at(bytes, at + 8)?, u32_at(bytes, at + 12)?);
                if b == 0 || d == 0 || a % b != 0 || c % d != 0 {
                    return None;
                }
                ((a / b) as usize, (c / d) as usize)
            }
            _ => return None,
        };
        return Some(Some(values));
    }
    Some(None)
}

/// The raw IFD's crop, or `Ok(None)` when it declares none. A declared crop
/// that is malformed, disagrees between the two tag pairs, falls outside the
/// buffer, or has an odd origin or size (which would change the CFA phase or
/// split a quad) is an error, never silently ignored.
pub fn crop(bytes: &[u8], total: usize) -> Result<Option<Crop>> {
    let Some((layout, ifd)) = raw_ifd(bytes, total) else {
        return Ok(None);
    };
    let read = |origin: u16, size: u16| -> Result<Option<Crop>> {
        let o = pair(bytes, ifd, origin).context("Unreadable crop origin tag")?;
        let s = pair(bytes, ifd, size).context("Unreadable crop size tag")?;
        Ok(match (o, s) {
            (Some((x, y)), Some((width, height))) => Some(Crop {
                x,
                y,
                width,
                height,
            }),
            (None, None) => None,
            _ => bail!("Crop origin and size tags must appear together"),
        })
    };
    let dng = read(0xC61F, 0xC620)?;
    let sony = read(0x74C7, 0x74C8)?;
    let crop = match (dng, sony) {
        (Some(a), Some(b)) => {
            ensure!(
                a == b,
                "The raw IFD's two crop declarations disagree: {a:?} and {b:?}"
            );
            a
        }
        (Some(c), None) | (None, Some(c)) => c,
        (None, None) => return Ok(None),
    };
    ensure!(
        crop.width >= 2
            && crop.height >= 2
            && crop.x + crop.width <= layout.width
            && crop.y + crop.height <= layout.height,
        "Declared crop {crop:?} lies outside the {}x{} buffer",
        layout.width,
        layout.height
    );
    ensure!(
        crop.x.is_multiple_of(2)
            && crop.y.is_multiple_of(2)
            && crop.width.is_multiple_of(2)
            && crop.height.is_multiple_of(2),
        "Declared crop {crop:?} is not aligned to the 2x2 colour pattern"
    );
    Ok(Some(crop))
}

/// Inverse of the transport's reversible predictor, written as samples.
/// `planar` holds the zigzag residual low bytes then high bytes, as
/// [`crate::predict`] produces them. Bit-identical to `predict(.., true)`.
fn unpredict_into(planar: &[u8], width: usize, dst: &mut [u16]) {
    let rows = dst.len() / width;
    ROWS.with_borrow_mut(|st| {
        unpredict_rows(planar, width, rows, st, |y, row| {
            dst[y * width..(y + 1) * width].copy_from_slice(row);
        });
    });
}

thread_local! {
    /// [`unpredict_into`]'s row buffers, per decoding thread.
    static ROWS: std::cell::RefCell<Rows> = std::cell::RefCell::new(Rows::default());
}

/// Row buffers of the row-buffered predictor ([`unpredict_rows`]). Nothing
/// is read back from the destination, so it may be write-only memory.
#[derive(Default)]
pub(crate) struct Rows {
    /// Residuals of the one or two rows in hand.
    r: [Vec<u16>; 2],
    /// `up[x - 2] + up[x] + up[x + 2]` of the same rows.
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

/// A row's residuals from its zigzag low and high bytes.
#[inline]
fn unzig_row(lo: &[u8], hi: &[u8], out: &mut [u16]) {
    for ((o, &l), &h) in out.iter_mut().zip(lo).zip(hi) {
        let z = u16::from(l) | (u16::from(h) << 8);
        *o = (z >> 1) ^ 0u16.wrapping_sub(z & 1);
    }
}

/// The three above-row terms of each interior sample, `u[x] = up[x - 2] +
/// up[x] + up[x + 2]` for `x` in `2..last`: no carried dependency, so the
/// compiler vectorises it.
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

/// The last two columns: the median edge detector, as `predict` encodes them.
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

/// One interior row from the row two above it: two carried chains (the two
/// colours of the row), each `((left + u[x]) / 4) + r[x]` modulo 2^16.
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
/// `y - 2` and `y - 1`, so their four chains are independent and run
/// interleaved. The carried values live in 32-bit registers holding 16-bit
/// values; each step is add, shift, add, mask, which is
/// `((sum / 4) as u16).wrapping_add(r)` exactly.
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
    let (mut a, mut b, mut c, mut d) = (
        u32::from(a16),
        u32::from(b16),
        u32::from(c16),
        u32::from(d16),
    );
    let mut x = 2;
    if last > 2 && last <= width {
        let pairs = (last - 2) / 2;
        let span = 2..2 + 2 * pairs;
        let it = c0[span.clone()]
            .as_chunks_mut::<2>()
            .0
            .iter_mut()
            .zip(c1[span.clone()].as_chunks_mut::<2>().0)
            .zip(
                u0[span.clone()]
                    .as_chunks::<2>()
                    .0
                    .iter()
                    .zip(u1[span.clone()].as_chunks::<2>().0),
            )
            .zip(
                r0[span.clone()]
                    .as_chunks::<2>()
                    .0
                    .iter()
                    .zip(r1[span].as_chunks::<2>().0),
            );
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
        c0[x] = (((a + u0[x]) >> 2) as u16).wrapping_add(r0[x]);
        c1[x] = (((c + u1[x]) >> 2) as u16).wrapping_add(r1[x]);
    }
    med_tail(c0, up0, r0, last, width);
    med_tail(c1, up1, r1, last, width);
}

/// The samples [`unpredict_into`] writes, built in row buffers and handed to
/// `emit(row index, samples)` one row at a time, in order. Rows 0-1 carry
/// along the row from the left (`x - 2`); later rows predict from the row two
/// above and the left, `(left + up[x - 2] + up[x] + up[x + 2]) / 4`, with the
/// median edge detector on the last two columns, exactly as
/// [`crate::predict`] encodes. MEASURED (2026-11-18, `bench2 pred` on the
/// A7CR scarab archives): 0.39 ns per sample against 1.08 for the loop that
/// read each row back from the destination.
pub(crate) fn unpredict_rows(
    planar: &[u8],
    width: usize,
    rows: usize,
    st: &mut Rows,
    emit: impl FnMut(usize, &[u16]),
) {
    let n = rows * width;
    debug_assert!(planar.len() >= 2 * n);
    let (lo, hi) = planar.split_at(n);
    unpredict_rows_from(
        width,
        rows,
        st,
        |y, out| {
            let row = y * width;
            unzig_row(&lo[row..row + width], &hi[row..row + width], out);
        },
        emit,
    );
}

/// [`unpredict_rows`] over any residual source: `residual(y, out)` writes
/// row `y`'s residuals (the wrapped differences, not zigzagged). Archive
/// format 2 decodes its residuals into a row of its own.
pub(crate) fn unpredict_rows_from(
    width: usize,
    rows: usize,
    st: &mut Rows,
    mut residual: impl FnMut(usize, &mut [u16]),
    mut emit: impl FnMut(usize, &[u16]),
) {
    st.fit(width);
    let Rows { r, u, hist, cur } = st;
    for y in 0..rows.min(2) {
        residual(y, &mut r[0][..width]);
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
        let (ra, rb) = r.split_at_mut(1);
        residual(y, &mut ra[0][..width]);
        residual(y + 1, &mut rb[0][..width]);
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
        residual(y, &mut r[0][..width]);
        up_sums(&hist[y & 1], last, &mut u[0]);
        let (ca, _) = cur.split_at_mut(1);
        row_one(&mut ca[0], &hist[y & 1], &r[0], &u[0], width);
        emit(y, &ca[0][..width]);
        std::mem::swap(&mut hist[y & 1], &mut ca[0]);
    }
}

/// The predictor's inverse as it was written before [`unpredict_rows`]: the
/// reference the row-buffered form is tested against.
#[cfg(test)]
fn unpredict_reference(planar: &[u8], width: usize, dst: &mut [u16]) {
    let n = dst.len();
    debug_assert_eq!(planar.len(), 2 * n);
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

/// Fill `buf` from `f` at byte `at`.
fn read_at(f: &mut File, buf: &mut [u8], at: u64) -> Result<()> {
    f.seek(SeekFrom::Start(at))?;
    f.read_exact(buf).context("Truncated archive")?;
    Ok(())
}

/// Fill `buf` from the file at `path`, byte `at`, through a handle of its own.
fn read_exact_at(path: &Path, buf: &mut [u8], at: u64) -> Result<()> {
    let mut f = File::open(path).with_context(|| format!("Open {}", path.display()))?;
    read_at(&mut f, buf, at)
}

struct Chunk {
    start: usize,
    n: usize,
    mode: u8,
    width: usize,
    payload: std::ops::Range<usize>,
}

fn decode_bytes(file: &[u8], c: &Chunk) -> Result<Vec<u8>> {
    let payload = &file[c.payload.clone()];
    Ok(match c.mode {
        255 => payload.to_vec(),
        0 | 8 => {
            ensure!(
                zstd::zstd_safe::find_frame_compressed_size(payload)
                    .map_err(|e| anyhow::anyhow!("Invalid Zstd frame: {e}"))?
                    == payload.len(),
                "Trailing data inside compressed chunk"
            );
            let raw = zstd::bulk::decompress(payload, c.n)?;
            ensure!(raw.len() == c.n, "Decoded chunk length mismatch");
            if c.mode == 8 {
                crate::predict(&raw, c.width, true)?
            } else {
                raw
            }
        }
        _ => bail!("Unsupported chunk method"),
    })
}

#[cfg(target_endian = "little")]
pub(crate) fn sample_bytes(samples: &[u16]) -> &[u8] {
    // SAFETY: u16 has no padding and alignment 2 >= 1; on a little-endian host
    // these are exactly the strip's original little-endian bytes.
    unsafe { std::slice::from_raw_parts(samples.as_ptr().cast::<u8>(), samples.len() * 2) }
}

/// Decode an archive whose original is a plain CFA-strip TIFF directly into
/// samples. `buffer` is reused when its length matches.
pub fn decode_archive(path: &Path, buffer: Option<Vec<u16>>) -> Result<Option<CfaFile>> {
    decode_archive_impl(path, buffer, None, false, None)
}

/// [`decode_archive`] (`serial`: [`decode_archive_serial`]) that skips the
/// whole-file SHA-256 when the envelope declares exactly `trusted`: the
/// caller already holds a verification of this file (a transfer receipt or
/// an earlier verified decode, `strehl_raw::trust`). The same samples; the
/// result's `verified_sha256` says whether the hash was checked now. With a
/// different declared hash, or `None`, the file is verified as always.
pub fn decode_archive_trusting(
    path: &Path,
    buffer: Option<Vec<u16>>,
    serial: bool,
    trusted: Option<&str>,
) -> Result<Option<CfaFile>> {
    decode_archive_impl(path, buffer, None, serial, trusted)
}

/// [`decode_archive`] on the calling thread alone, for callers that already
/// run many decodes at once (a decode-ahead thread, a group's members): the
/// chunks are decoded in order through this thread's reused file buffer,
/// Zstd context and scratch, and each chunk's samples are hashed while they
/// are still in cache. Same samples, same checksum verdict, same errors.
/// MEASURED on the A7CR scarab archives (harness `decode2`, 2026-11-17):
/// 74 files/s on 16 threads against 50 for the pool-parallel decode, whose
/// every decode streams its file, samples and checksum through memory.
pub fn decode_archive_serial(path: &Path, buffer: Option<Vec<u16>>) -> Result<Option<CfaFile>> {
    decode_archive_impl(path, buffer, None, true, None)
}

/// A decoding thread's reused state for [`decode_archive_serial`].
struct Resident {
    /// This thread's file buffer, for files no reader read.
    read: Option<crate::preload::AlignedBuf>,
    scratch: Vec<u8>,
    zstd: zstd::bulk::Decompressor<'static>,
    rows: Rows,
    v2: crate::v2::Scratch,
}

thread_local! {
    static RESIDENT: std::cell::RefCell<Option<Resident>> = const { std::cell::RefCell::new(None) };
    /// A pool thread's format-2 tables and rows, for the parallel decode.
    static V2: std::cell::RefCell<crate::v2::Scratch> = std::cell::RefCell::new(Default::default());
}

/// [`decode_archive`] of only the CFA chunks holding a row `rows` marks (one
/// flag per sample row of the strip; rows past its end count as unmarked).
/// The chunks are independent (each its own Zstd frame, its predictor
/// restarting at the chunk's first rows), so a decoded row equals the full
/// decode's. **No checksum is possible on part of a file**: callers must
/// already trust these bytes, e.g. from a verified full decode of the same
/// file earlier in the process. [`CfaFile::decoded_rows`] says which rows
/// hold samples.
pub fn decode_archive_rows(
    path: &Path,
    rows: &[bool],
    buffer: Option<Vec<u16>>,
) -> Result<Option<CfaFile>> {
    decode_archive_impl(path, buffer, Some(rows), false, None)
}

/// An archive's bytes: read here, or read whole by a reader thread
/// (`preload`). Only a partial decode writes into them, and it always reads
/// its own.
enum FileBytes {
    Owned(Vec<u8>),
    Read(crate::preload::AlignedBuf),
}

impl std::ops::Deref for FileBytes {
    type Target = [u8];
    fn deref(&self) -> &[u8] {
        match self {
            FileBytes::Owned(v) => v,
            FileBytes::Read(b) => b,
        }
    }
}

impl std::ops::DerefMut for FileBytes {
    fn deref_mut(&mut self) -> &mut [u8] {
        match self {
            FileBytes::Owned(v) => v,
            FileBytes::Read(_) => unreachable!("a partial decode reads its own bytes"),
        }
    }
}

impl FileBytes {
    /// Give a whole-file buffer back to the decoding thread for its next
    /// file that no reader read.
    fn release(self, resident: Option<&mut Resident>) {
        match (self, resident) {
            (FileBytes::Read(b), Some(r)) if r.read.is_none() => r.read = Some(b),
            (FileBytes::Read(b), _) => crate::preload::recycle(b),
            (FileBytes::Owned(_), _) => {}
        }
    }
}

fn decode_archive_impl(
    path: &Path,
    buffer: Option<Vec<u16>>,
    rows: Option<&[bool]>,
    serial: bool,
    trusted: Option<&str>,
) -> Result<Option<CfaFile>> {
    if cfg!(target_endian = "big") {
        return Ok(None);
    }
    // The serial decode's thread state, taken for this call and put back at
    // its end (an early return or error simply builds a fresh one next time).
    let mut resident = if serial {
        match RESIDENT.with_borrow_mut(Option::take) {
            Some(r) => Some(r),
            None => Some(Resident {
                read: None,
                scratch: Vec::new(),
                zstd: zstd::bulk::Decompressor::new()?,
                rows: Rows::default(),
                v2: Default::default(),
            }),
        }
    } else {
        None
    };
    // A partial decode reads only what it uses: the envelope, every chunk
    // header, the prefix chunks and the wanted chunks, into a buffer of the
    // file's length whose other bytes stay zero (and, untouched, unbacked).
    let mut sparse = match rows {
        Some(_) => Some(File::open(path).with_context(|| format!("Open {}", path.display()))?),
        None => None,
    };
    // A serial decode's file: read whole by a reader thread already
    // (`preload`), or read whole here the same way (unbuffered when the file
    // cache does not hold it). The same bytes either way.
    let preloaded = match resident.as_mut() {
        Some(r) => match crate::preload::take(path) {
            Some(b) => Some(b),
            None => Some(
                crate::preload::read_whole(
                    path,
                    crate::preload::ReadMode::from_env(),
                    r.read.take(),
                )
                .with_context(|| format!("Read {}", path.display()))?
                .0,
            ),
        },
        None => None,
    };
    let mut file = match sparse.as_mut() {
        None if preloaded.is_some() => FileBytes::Read(preloaded.expect("checked")),
        None => FileBytes::Owned(
            std::fs::read(path).with_context(|| format!("Read {}", path.display()))?,
        ),
        Some(f) => {
            let len = f.metadata()?.len() as usize;
            let mut file = vec![0u8; len];
            let head = (archive::HEADER_BYTES as usize + 16).min(len);
            read_at(f, &mut file[..head], 0)?;
            FileBytes::Owned(file)
        }
    };
    if crate::v2::is_v2(&file) {
        return decode_v2(path, file, sparse, buffer, rows, resident, trusted);
    }
    let header = archive::read_header(&file[..])?;
    // Skip the whole-file hash only for the exact hash the caller trusts.
    let hashing = !trusted.is_some_and(|s| s.eq_ignore_ascii_case(&header.sha256));
    let length = header.bytes as usize;
    let body = archive::HEADER_BYTES as usize;
    ensure!(
        file.len() >= body + 16 && &file[body..body + 8] == TRANSPORT_MAGIC,
        "Unsupported transport version"
    );
    ensure!(
        u64::from_le_bytes(file[body + 8..body + 16].try_into()?) == header.bytes,
        "Original length disagrees with envelope"
    );
    // Walk chunk headers; payloads are not touched yet.
    let mut chunks = Vec::new();
    let (mut at, mut total) = (body + 16, 0usize);
    while total < length {
        ensure!(chunks.len() < MAX_CHUNKS, "Too many transport chunks");
        if let Some(f) = sparse.as_mut()
            && at + 13 <= file.len()
        {
            read_at(f, &mut file[at..at + 13], at as u64)?;
        }
        let h = file.get(at..at + 13).context("Truncated chunk header")?;
        let n = u32::from_le_bytes(h[..4].try_into()?) as usize;
        let packed = u32::from_le_bytes(h[4..8].try_into()?) as usize;
        let mode = h[8];
        let width = u32::from_le_bytes(h[9..].try_into()?) as usize;
        ensure!(
            n > 0 && n <= MAX_CHUNK && packed > 0 && packed <= n && total + n <= length,
            "Invalid chunk lengths"
        );
        match mode {
            255 => ensure!(width == 0 && packed == n, "Invalid identity chunk"),
            0 => ensure!(width == 0, "Unexpected dimensions on byte chunk"),
            8 => ensure!(valid_cfa(n, width), "Invalid CFA chunk dimensions"),
            _ => bail!("Unsupported chunk method"),
        }
        let payload = at + 13..at + 13 + packed;
        ensure!(payload.end <= file.len(), "Truncated chunk payload");
        chunks.push(Chunk {
            start: total,
            n,
            mode,
            width,
            payload: payload.clone(),
        });
        at = payload.end;
        total += n;
    }
    ensure!(at == file.len(), "Trailing archive bytes");
    ensure!(length as u64 <= MAX_RAW, "Original file exceeds size limit");
    // Prefix: every chunk before the first CFA chunk.
    let Some(first_cfa) = chunks.iter().position(|c| c.mode == 8) else {
        return Ok(None);
    };
    if let Some(f) = sparse.as_mut() {
        for c in &chunks[..first_cfa] {
            read_at(f, &mut file[c.payload.clone()], c.payload.start as u64)?;
        }
    }
    let mut prefix = Vec::with_capacity(chunks[first_cfa].start);
    for c in &chunks[..first_cfa] {
        prefix.extend_from_slice(&decode_bytes(&file, c)?);
    }
    let Some((layout, _)) = raw_ifd(&prefix, length) else {
        return Ok(None);
    };
    if layout.offset != prefix.len() {
        return Ok(None);
    }
    let strip_end = layout.offset + layout.length;
    let Some(last) = chunks.iter().rposition(|c| c.start < strip_end) else {
        return Ok(None);
    };
    if chunks[last].start + chunks[last].n != strip_end {
        return Ok(None);
    }
    let strip = &chunks[first_cfa..=last];
    let row_bytes = 2 * layout.width;
    if strip.iter().any(|c| {
        (c.start - layout.offset) % row_bytes != 0
            || c.n % row_bytes != 0
            || (c.mode == 8 && c.width != layout.width)
    }) {
        return Ok(None);
    }
    let count = layout.width * layout.height;
    let mut samples = match buffer {
        Some(b) if b.len() == count => b,
        _ => vec![0u16; count],
    };
    // Disjoint destination slices, one per strip chunk; with `rows`, only the
    // chunks holding a marked row.
    let chunk_rows = |c: &Chunk| {
        let first = (c.start - layout.offset) / row_bytes;
        first..first + c.n / row_bytes
    };
    let wanted =
        |c: &Chunk| rows.is_none_or(|r| chunk_rows(c).any(|y| r.get(y).copied().unwrap_or(false)));
    let mut decoded_rows = rows.map(|_| vec![false; layout.height]);
    let mut jobs = Vec::with_capacity(strip.len());
    let mut rest = samples.as_mut_slice();
    for c in strip {
        let (head, tail) = rest.split_at_mut(c.n / 2);
        if wanted(c) {
            if let Some(d) = decoded_rows.as_mut() {
                d[chunk_rows(c)].fill(true);
            }
            jobs.push((c, head));
        }
        rest = tail;
    }
    if sparse.is_some() {
        // The wanted chunks' payloads, read at once on separate handles (a
        // synchronous handle serialises its reads), so the drive sees many
        // requests: MEASURED 2.3 GB/s for the reference pass's partial
        // decodes read one chunk after another (2026-11-18). The same bytes.
        let mut wanted_payloads: Vec<std::ops::Range<usize>> =
            jobs.iter().map(|(c, _)| c.payload.clone()).collect();
        wanted_payloads.sort_by_key(|r| r.start);
        let mut slices: Vec<(u64, &mut [u8])> = Vec::with_capacity(wanted_payloads.len());
        let mut rest_file: &mut [u8] = &mut file;
        let mut base = 0usize;
        for r in wanted_payloads {
            let (_, tail) = rest_file.split_at_mut(r.start - base);
            let (piece, tail) = tail.split_at_mut(r.len());
            slices.push((r.start as u64, piece));
            rest_file = tail;
            base = r.end;
        }
        slices
            .into_par_iter()
            .try_for_each(|(at, piece)| read_exact_at(path, piece, at))?;
    }
    if let Some(r) = resident.as_mut() {
        // In order, on this thread; each chunk hashed while its samples are
        // in cache. The prefix, then the samples, then the suffix: the bytes
        // the parallel route hashes, in the same order.
        let mut hash = Sha256::new();
        hash.update(&prefix);
        for (c, dst) in jobs {
            let payload = &file[c.payload.clone()];
            match c.mode {
                8 => {
                    ensure!(
                        zstd::zstd_safe::find_frame_compressed_size(payload)
                            .map_err(|e| anyhow::anyhow!("Invalid Zstd frame: {e}"))?
                            == payload.len(),
                        "Trailing data inside compressed chunk"
                    );
                    if r.scratch.len() < c.n {
                        r.scratch.resize(c.n, 0);
                    }
                    let got = r
                        .zstd
                        .decompress_to_buffer(payload, &mut r.scratch[..c.n])?;
                    ensure!(got == c.n, "Decoded chunk length mismatch");
                    // Each finished row is written once and hashed from the
                    // row buffer: the same bytes in the same order.
                    let w = c.width;
                    let Resident { scratch, rows, .. } = r;
                    unpredict_rows(&scratch[..c.n], w, dst.len() / w, rows, |y, row| {
                        dst[y * w..(y + 1) * w].copy_from_slice(row);
                        #[cfg(target_endian = "little")]
                        if hashing {
                            hash.update(sample_bytes(row));
                        }
                    });
                }
                _ => {
                    let raw = decode_bytes(&file, c)?;
                    for (d, b) in dst.iter_mut().zip(raw.as_chunks::<2>().0) {
                        *d = u16::from_le_bytes(*b);
                    }
                    #[cfg(target_endian = "little")]
                    if hashing {
                        hash.update(sample_bytes(dst));
                    }
                }
            }
        }
        let mut suffix = Vec::new();
        for c in &chunks[last + 1..] {
            suffix.extend_from_slice(&decode_bytes(&file, c)?);
        }
        if hashing {
            hash.update(&suffix);
            let sum: String = hash.finalize().iter().map(|b| format!("{b:02x}")).collect();
            ensure!(sum == header.sha256, "RAW archive checksum mismatch");
        }
        let crop = crop(&prefix, length)?;
        if let Some(mut r) = resident.take() {
            file.release(Some(&mut r));
            RESIDENT.with_borrow_mut(|slot| *slot = Some(r));
        }
        return Ok(Some(CfaFile {
            prefix,
            width: layout.width,
            height: layout.height,
            samples,
            crop,
            verified_sha256: hashing,
            declared_sha256: header.sha256,
            suffix,
            original_length: length as u64,
            decoded_rows: None,
        }));
    }
    jobs.into_par_iter()
        .try_for_each(|(c, dst)| -> Result<()> {
            let payload = &file[c.payload.clone()];
            match c.mode {
                8 => {
                    ensure!(
                        zstd::zstd_safe::find_frame_compressed_size(payload)
                            .map_err(|e| anyhow::anyhow!("Invalid Zstd frame: {e}"))?
                            == payload.len(),
                        "Trailing data inside compressed chunk"
                    );
                    let planar = zstd::bulk::decompress(payload, c.n)?;
                    ensure!(planar.len() == c.n, "Decoded chunk length mismatch");
                    unpredict_into(&planar, c.width, dst);
                }
                _ => {
                    let raw = decode_bytes(&file, c)?;
                    for (d, b) in dst.iter_mut().zip(raw.as_chunks::<2>().0) {
                        *d = u16::from_le_bytes(*b);
                    }
                }
            }
            Ok(())
        })?;
    if decoded_rows.is_some() {
        drop(file);
        let crop = crop(&prefix, length)?;
        return Ok(Some(CfaFile {
            prefix,
            width: layout.width,
            height: layout.height,
            samples,
            crop,
            verified_sha256: false,
            declared_sha256: header.sha256,
            suffix: Vec::new(),
            original_length: 0,
            decoded_rows,
        }));
    }
    let mut suffix = Vec::new();
    for c in &chunks[last + 1..] {
        suffix.extend_from_slice(&decode_bytes(&file, c)?);
    }
    drop(file);
    if hashing {
        let mut hash = Sha256::new();
        hash.update(&prefix);
        #[cfg(target_endian = "little")]
        hash.update(sample_bytes(&samples));
        hash.update(&suffix);
        let sum: String = hash.finalize().iter().map(|b| format!("{b:02x}")).collect();
        ensure!(sum == header.sha256, "RAW archive checksum mismatch");
    }
    let crop = crop(&prefix, length)?;
    Ok(Some(CfaFile {
        prefix,
        width: layout.width,
        height: layout.height,
        samples,
        crop,
        verified_sha256: hashing,
        declared_sha256: header.sha256,
        suffix,
        original_length: length as u64,
        decoded_rows: None,
    }))
}

/// [`decode_archive_impl`] for an archive in format 2 (`crate::v2`): the same
/// results, errors and checksum verdict. Its index places every chunk, so a
/// partial decode reads the index, the metadata and the wanted chunks only;
/// every chunk's CRC is checked before it is decoded, on every route.
fn decode_v2(
    path: &Path,
    mut file: FileBytes,
    mut sparse: Option<File>,
    buffer: Option<Vec<u16>>,
    rows: Option<&[bool]>,
    mut resident: Option<Resident>,
    trusted: Option<&str>,
) -> Result<Option<CfaFile>> {
    use crate::v2;
    let file_len = file.len() as u64;
    let head = v2::head_len(&file)?;
    ensure!(file.len() >= head, "Truncated archive index");
    if let Some(f) = sparse.as_mut() {
        read_at(f, &mut file[..head], 0)?;
    }
    let index = v2::parse(&file[..head], file_len)?;
    let hashing = !trusted.is_some_and(|s| s.eq_ignore_ascii_case(&index.sha256));
    let Some(first) = index.entries.iter().position(|e| e.samples()) else {
        return Ok(None);
    };
    let last = index
        .entries
        .iter()
        .rposition(|e| e.samples())
        .expect("found");
    ensure!(
        index.entries[first..=last].iter().all(|e| e.samples()),
        "Archive sample chunks are not contiguous"
    );
    let outside = |e: &v2::Entry| !e.samples();
    if let Some(f) = sparse.as_mut() {
        for e in index.entries.iter().filter(|e| outside(e)) {
            read_at(f, &mut file[e.payload()], e.offset)?;
        }
    }
    let mut prefix = Vec::with_capacity(index.strip_offset);
    for e in &index.entries[..first] {
        prefix.extend_from_slice(&v2::chunk_bytes(e, &file[e.payload()])?);
    }
    // The metadata must describe the strip the index declares, as format 1's
    // route requires of its chunks; otherwise the general route decodes it.
    let Some((layout, _)) = raw_ifd(&prefix, index.length) else {
        return Ok(None);
    };
    if layout.offset != prefix.len()
        || layout.offset != index.strip_offset
        || (layout.width, layout.height) != (index.width, index.height)
    {
        return Ok(None);
    }
    let width = index.width;
    let count = width * index.height;
    let mut samples = match buffer {
        Some(b) if b.len() == count => b,
        _ => vec![0u16; count],
    };
    let strip = &index.entries[first..=last];
    let wanted = |e: &v2::Entry| {
        rows.is_none_or(|r| index.rows(e).any(|y| r.get(y).copied().unwrap_or(false)))
    };
    let mut decoded_rows = rows.map(|_| vec![false; index.height]);
    let mut jobs = Vec::with_capacity(strip.len());
    let mut rest = samples.as_mut_slice();
    for e in strip {
        let (head, tail) = rest.split_at_mut(e.len / 2);
        if wanted(e) {
            if let Some(d) = decoded_rows.as_mut() {
                d[index.rows(e)].fill(true);
            }
            jobs.push((e, head));
        }
        rest = tail;
    }
    if sparse.is_some() {
        // The wanted payloads at once on separate handles, as format 1 does.
        let mut slices: Vec<(u64, &mut [u8])> = Vec::with_capacity(jobs.len());
        let mut rest_file: &mut [u8] = &mut file;
        let mut base = 0usize;
        for (e, _) in &jobs {
            let r = e.payload();
            let (_, tail) = rest_file.split_at_mut(r.start - base);
            let (piece, tail) = tail.split_at_mut(r.len());
            slices.push((r.start as u64, piece));
            rest_file = tail;
            base = r.end;
        }
        slices
            .into_par_iter()
            .try_for_each(|(at, piece)| read_exact_at(path, piece, at))?;
    }
    let suffix = |file: &[u8]| -> Result<Vec<u8>> {
        let mut suffix = Vec::new();
        for e in &index.entries[last + 1..] {
            suffix.extend_from_slice(&v2::chunk_bytes(e, &file[e.payload()])?);
        }
        Ok(suffix)
    };
    let done = |samples: Vec<u16>,
                suffix: Vec<u8>,
                verified: bool,
                decoded_rows: Option<Vec<bool>>|
     -> Result<Option<CfaFile>> {
        Ok(Some(CfaFile {
            crop: crop(&prefix, index.length)?,
            prefix: prefix.clone(),
            width,
            height: index.height,
            samples,
            verified_sha256: verified,
            declared_sha256: index.sha256.clone(),
            original_length: if decoded_rows.is_some() {
                0
            } else {
                index.length as u64
            },
            suffix,
            decoded_rows,
        }))
    };
    if let Some(mut r) = resident.take() {
        // In order on this thread, each row hashed while it is in cache.
        let mut hash = Sha256::new();
        hash.update(&prefix);
        for (e, dst) in jobs {
            v2::decode_samples(e, &file[e.payload()], width, &mut r.v2, |y, row| {
                dst[y * width..(y + 1) * width].copy_from_slice(row);
                #[cfg(target_endian = "little")]
                if hashing {
                    hash.update(sample_bytes(row));
                }
            })?;
        }
        let suffix = suffix(&file)?;
        if hashing {
            hash.update(&suffix);
            let sum: String = hash.finalize().iter().map(|b| format!("{b:02x}")).collect();
            ensure!(sum == index.sha256, "RAW archive checksum mismatch");
        }
        file.release(Some(&mut r));
        RESIDENT.with_borrow_mut(|slot| *slot = Some(r));
        return done(samples, suffix, hashing, None);
    }
    jobs.into_par_iter()
        .try_for_each(|(e, dst)| -> Result<()> {
            V2.with_borrow_mut(|st| {
                v2::decode_samples(e, &file[e.payload()], width, st, |y, row| {
                    dst[y * width..(y + 1) * width].copy_from_slice(row);
                })
            })
        })?;
    if decoded_rows.is_some() {
        drop(file);
        return done(samples, Vec::new(), false, decoded_rows);
    }
    let suffix = suffix(&file)?;
    drop(file);
    if hashing {
        let mut hash = Sha256::new();
        hash.update(&prefix);
        #[cfg(target_endian = "little")]
        hash.update(sample_bytes(&samples));
        hash.update(&suffix);
        let sum: String = hash.finalize().iter().map(|b| format!("{b:02x}")).collect();
        ensure!(sum == index.sha256, "RAW archive checksum mismatch");
    }
    done(samples, suffix, hashing, None)
}

/// Read an unarchived plain-strip TIFF's samples directly into `buffer`.
pub fn read_plain(path: &Path, buffer: Option<Vec<u16>>) -> Result<Option<CfaFile>> {
    if cfg!(target_endian = "big") {
        return Ok(None);
    }
    let mut f = File::open(path).with_context(|| format!("Open {}", path.display()))?;
    let total = f.metadata()?.len() as usize;
    let mut head = vec![0u8; total.min(8 * 1024 * 1024)];
    f.read_exact(&mut head)?;
    let Some((layout, _)) = raw_ifd(&head, total) else {
        return Ok(None);
    };
    if layout.offset > head.len() {
        return Ok(None);
    }
    head.truncate(layout.offset);
    let count = layout.width * layout.height;
    let mut samples = match buffer {
        Some(b) if b.len() == count => b,
        _ => vec![0u16; count],
    };
    f.seek(SeekFrom::Start(layout.offset as u64))?;
    #[cfg(target_endian = "little")]
    {
        // SAFETY: as in `sample_bytes`, mutable; every byte is overwritten.
        let bytes =
            unsafe { std::slice::from_raw_parts_mut(samples.as_mut_ptr().cast::<u8>(), count * 2) };
        f.read_exact(bytes)?;
    }
    let crop = crop(&head, total)?;
    Ok(Some(CfaFile {
        prefix: head,
        width: layout.width,
        height: layout.height,
        samples,
        crop,
        verified_sha256: false,
        declared_sha256: String::new(),
        suffix: Vec::new(),
        original_length: 0,
        decoded_rows: None,
    }))
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::tests::fixture;

    fn with_crop(mut data: Vec<u8>, dng: Option<[u16; 4]>, sony: Option<[u16; 4]>) -> Vec<u8> {
        // Rebuild the fixture's single IFD with extra SHORT pairs appended.
        let count = usize::from(u16_at(&data, 8).unwrap());
        let mut entries: Vec<[u8; 12]> = (0..count)
            .map(|i| data[10 + 12 * i..22 + 12 * i].try_into().unwrap())
            .collect();
        for (tags, values) in [((0xC61Fu16, 0xC620u16), dng), ((0x74C7, 0x74C8), sony)] {
            if let Some(v) = values {
                for (tag, (a, b)) in [(tags.0, (v[0], v[1])), (tags.1, (v[2], v[3]))] {
                    let mut e = [0u8; 12];
                    e[..2].copy_from_slice(&tag.to_le_bytes());
                    e[2..4].copy_from_slice(&3u16.to_le_bytes());
                    e[4..8].copy_from_slice(&2u32.to_le_bytes());
                    e[8..10].copy_from_slice(&a.to_le_bytes());
                    e[10..12].copy_from_slice(&b.to_le_bytes());
                    entries.push(e);
                }
            }
        }
        entries.sort_by_key(|e| u16::from_le_bytes([e[0], e[1]]));
        assert!(10 + 12 * entries.len() + 4 <= 256);
        data[8..10].copy_from_slice(&(entries.len() as u16).to_le_bytes());
        for (i, e) in entries.iter().enumerate() {
            data[10 + 12 * i..22 + 12 * i].copy_from_slice(e);
        }
        let end = 10 + 12 * entries.len();
        data[end..end + 4].fill(0);
        data
    }

    fn archived(original: &[u8]) -> tempfile::TempPath {
        let file = tempfile::Builder::new()
            .suffix(".ARW.straw")
            .tempfile()
            .unwrap();
        let mut out = Vec::new();
        archive::pack(original.to_vec(), &mut out).unwrap();
        std::fs::write(file.path(), out).unwrap();
        file.into_temp_path()
    }

    fn archived_as(original: &[u8], format: u8) -> tempfile::TempPath {
        let sha: String = Sha256::digest(original)
            .iter()
            .map(|b| format!("{b:02x}"))
            .collect();
        let (bytes, stored) = archive::store(original, &sha, format).unwrap();
        assert_eq!(stored, format);
        let file = tempfile::Builder::new()
            .suffix(".ARW.straw")
            .tempfile()
            .unwrap();
        std::fs::write(file.path(), bytes).unwrap();
        file.into_temp_path()
    }

    /// Format 2 gives exactly format 1's samples, metadata, crop and
    /// checksum verdicts on every route (pool, serial, trusted, row range,
    /// metadata reader, whole original), and refuses a damaged chunk even
    /// when the whole-file hash is trusted and skipped.
    #[test]
    fn format_2_decodes_like_format_1_on_every_route() {
        for (w, h, cropped) in [(128, 520, true), (200, 96, false), (66, 34, false)] {
            let mut original = fixture(w, h);
            if cropped {
                original = with_crop(original, Some([4, 2, 120, 512]), None);
            }
            let one = archived_as(&original, 1);
            let two = archived_as(&original, 2);
            let a = decode_archive(&one, None).unwrap().unwrap();
            let b = decode_archive(&two, None).unwrap().unwrap();
            assert!(a.verified_sha256 && b.verified_sha256);
            assert_eq!(a.samples, b.samples);
            assert_eq!(a.prefix, b.prefix);
            assert_eq!(a.suffix, b.suffix);
            assert_eq!(a.crop, b.crop);
            assert_eq!(a.declared_sha256, b.declared_sha256);
            assert_eq!(a.original_length, b.original_length);
            for _ in 0..2 {
                let s = decode_archive_serial(&two, Some(vec![9; w * h]))
                    .unwrap()
                    .unwrap();
                assert!(s.verified_sha256);
                assert_eq!(s.samples, a.samples);
                assert_eq!(s.suffix, a.suffix);
            }
            for serial in [false, true] {
                let t = decode_archive_trusting(&two, None, serial, Some(&a.declared_sha256))
                    .unwrap()
                    .unwrap();
                assert!(!t.verified_sha256);
                assert_eq!(t.samples, a.samples);
            }
            for wanted in [
                vec![0usize],
                vec![h - 1],
                vec![h / 2, h / 2 + 1],
                Vec::new(),
            ] {
                let mut rows = vec![false; h];
                for &y in &wanted {
                    rows[y] = true;
                }
                let part = decode_archive_rows(&two, &rows, Some(vec![0xBEEF; w * h]))
                    .unwrap()
                    .unwrap();
                let decoded = part.decoded_rows.unwrap();
                for &y in &wanted {
                    assert!(decoded[y]);
                }
                assert_eq!(decoded.iter().any(|d| *d), !wanted.is_empty());
                for (y, d) in decoded.iter().enumerate() {
                    if *d {
                        assert_eq!(
                            part.samples[y * w..(y + 1) * w],
                            a.samples[y * w..(y + 1) * w]
                        );
                    }
                }
            }
            assert_eq!(archive::read_original(&two).unwrap(), original);
            assert!(archive::verify(&two).is_ok());
            let mut r = archive::open_original(&two).unwrap();
            assert!(matches!(r, archive::OriginalReader::Sparse(_)));
            let mut all = Vec::new();
            r.read_to_end(&mut all).unwrap();
            assert_eq!(all, original);
            let header = archive::read_header(std::fs::File::open(&two).unwrap()).unwrap();
            assert_eq!(
                (header.format, header.sha256),
                (2, a.declared_sha256.clone())
            );
            // One flipped bit near the end: the last sample chunk or the metadata after it.
            let mut bad = std::fs::read(&two).unwrap();
            let n = bad.len();
            bad[n - 40] ^= 0x04;
            let damaged = tempfile::Builder::new()
                .suffix(".ARW.straw")
                .tempfile()
                .unwrap();
            std::fs::write(damaged.path(), &bad).unwrap();
            for serial in [false, true] {
                assert!(
                    decode_archive_trusting(damaged.path(), None, serial, Some(&a.declared_sha256))
                        .is_err()
                );
            }
            assert!(archive::verify(damaged.path()).is_err());
        }
    }

    #[test]
    fn archive_decodes_to_the_exact_strip_samples_and_metadata() {
        let original = with_crop(
            fixture(128, 520),
            Some([4, 2, 120, 512]),
            Some([4, 2, 120, 512]),
        );
        let path = archived(&original);
        let cfa = decode_archive(&path, Some(vec![7u16; 128 * 520]))
            .unwrap()
            .unwrap();
        assert!(cfa.verified_sha256);
        assert_eq!((cfa.width, cfa.height), (128, 520));
        assert_eq!(cfa.prefix, original[..256]);
        let expected: Vec<u16> = original[256..256 + 128 * 520 * 2]
            .as_chunks::<2>()
            .0
            .iter()
            .map(|b| u16::from_le_bytes(*b))
            .collect();
        assert_eq!(cfa.samples, expected);
        // The serial decode: the same samples, prefix, crop and verdict, twice
        // on one thread (its reused buffers must not leak between files).
        for _ in 0..2 {
            let serial = decode_archive_serial(&path, None).unwrap().unwrap();
            assert!(serial.verified_sha256);
            assert_eq!(serial.samples, expected);
            assert_eq!(serial.prefix, cfa.prefix);
            assert_eq!(serial.crop, cfa.crop);
        }
        assert_eq!(
            cfa.crop,
            Some(Crop {
                x: 4,
                y: 2,
                width: 120,
                height: 512
            })
        );
        // Unarchived file gives the same samples and crop, unverified.
        let plain = tempfile::NamedTempFile::new().unwrap();
        std::fs::write(plain.path(), &original).unwrap();
        let p = read_plain(plain.path(), None).unwrap().unwrap();
        assert_eq!(p.samples, expected);
        assert_eq!(p.crop, cfa.crop);
        assert!(!p.verified_sha256);
    }

    /// A row-range decode returns exactly the full decode's rows over every
    /// chunk holding a requested row, says which rows those are, and covers
    /// every requested row; with nothing requested it decodes nothing.
    #[test]
    fn row_range_decode_equals_the_full_decode_on_its_rows() {
        let original = with_crop(
            fixture(128, 520),
            Some([4, 2, 120, 512]),
            Some([4, 2, 120, 512]),
        );
        let path = archived(&original);
        let full = decode_archive(&path, None).unwrap().unwrap();
        for wanted in [
            vec![0usize],
            vec![519],
            vec![100, 101, 102],
            vec![5, 300, 517],
            (0..520).collect(),
            Vec::new(),
        ] {
            let mut rows = vec![false; 520];
            for &y in &wanted {
                rows[y] = true;
            }
            let part = decode_archive_rows(&path, &rows, Some(vec![0xBEEF; 128 * 520]))
                .unwrap()
                .unwrap();
            assert!(!part.verified_sha256);
            assert_eq!(part.prefix, full.prefix);
            assert_eq!(part.crop, full.crop);
            let decoded = part.decoded_rows.expect("decoded rows reported");
            assert_eq!(decoded.len(), 520);
            for &y in &wanted {
                assert!(decoded[y], "requested row {y} not decoded");
            }
            if wanted.is_empty() {
                assert!(decoded.iter().all(|d| !d));
            }
            for (y, d) in decoded.iter().enumerate() {
                if *d {
                    assert_eq!(
                        part.samples[y * 128..(y + 1) * 128],
                        full.samples[y * 128..(y + 1) * 128],
                        "row {y}"
                    );
                }
            }
        }
    }

    /// A trusted hash skips only the check of that exact hash: the same
    /// samples, reported unverified; any other hash, or a file whose envelope
    /// was altered, is verified (and refused when wrong) as always.
    #[test]
    fn a_trusted_hash_skips_only_its_own_check() {
        let original = fixture(128, 520);
        let path = archived(&original);
        let full = decode_archive(&path, None).unwrap().unwrap();
        assert!(full.verified_sha256);
        assert_eq!(full.declared_sha256.len(), 64);
        for serial in [false, true] {
            let sha = full.declared_sha256.to_ascii_uppercase();
            let skip = decode_archive_trusting(&path, None, serial, Some(&sha))
                .unwrap()
                .unwrap();
            assert!(!skip.verified_sha256);
            assert_eq!(skip.samples, full.samples);
            assert_eq!(skip.prefix, full.prefix);
            let other = decode_archive_trusting(&path, None, serial, Some("00"))
                .unwrap()
                .unwrap();
            assert!(other.verified_sha256);
        }
        let bad = tempfile::Builder::new()
            .suffix(".straw")
            .tempfile()
            .unwrap();
        let mut wrong_hash = std::fs::read(&path).unwrap();
        wrong_hash[20] ^= 1;
        std::fs::write(bad.path(), &wrong_hash).unwrap();
        for serial in [false, true] {
            assert!(
                decode_archive_trusting(bad.path(), None, serial, Some(&full.declared_sha256))
                    .is_err()
            );
        }
    }

    /// The row-buffered inverse writes exactly what the reference loop
    /// writes, on full-range random residuals at every width from 2 to 257
    /// and every row count from 1 to 17 (odd and even, below and past the
    /// two carried rows and the paired rows).
    #[test]
    fn row_buffered_unpredict_equals_the_reference_loop() {
        let mut seed = 0x9E37_79B9_7F4A_7C15u64;
        let mut next = move || {
            seed ^= seed << 13;
            seed ^= seed >> 7;
            seed ^= seed << 17;
            seed
        };
        let mut st = Rows::default();
        for width in 2..=257usize {
            for rows in 1..=17usize {
                let n = width * rows;
                let planar: Vec<u8> = (0..2 * n).map(|_| next() as u8).collect();
                let mut want = vec![0u16; n];
                unpredict_reference(&planar, width, &mut want);
                let mut got = vec![0xA5A5u16; n];
                let mut seen = 0;
                unpredict_rows(&planar, width, rows, &mut st, |y, row| {
                    assert_eq!(y, seen, "rows are emitted in order");
                    seen += 1;
                    got[y * width..(y + 1) * width].copy_from_slice(row);
                });
                assert_eq!(seen, rows);
                assert_eq!(got, want, "width {width}, rows {rows}");
                let mut via = vec![0u16; n];
                unpredict_into(&planar, width, &mut via);
                assert_eq!(via, want, "width {width}, rows {rows}");
            }
        }
    }

    #[test]
    fn unpredict_matches_the_reference_inverse_for_every_width() {
        let values: Vec<u8> = (0..65536u32 * 2)
            .map(|n| (n.wrapping_mul(2654435761) >> 13) as u16)
            .flat_map(u16::to_le_bytes)
            .collect();
        for width in [2, 4, 6, 128, 32768] {
            let n = values.len() / 2 / (2 * width) * (2 * width);
            let input = &values[..2 * n];
            let planar = crate::predict(input, width, false).unwrap();
            let mut dst = vec![0u16; n];
            unpredict_into(&planar, width, &mut dst);
            let back: Vec<u8> = dst.iter().flat_map(|v| v.to_le_bytes()).collect();
            assert_eq!(back, input, "width {width}");
        }
    }

    #[test]
    fn corrupt_truncated_wrong_hash_and_bad_crops_are_refused() {
        let original = fixture(128, 520);
        let path = archived(&original);
        let good = std::fs::read(&path).unwrap();
        let bad = tempfile::Builder::new()
            .suffix(".straw")
            .tempfile()
            .unwrap();
        let mut wrong_hash = good.clone();
        wrong_hash[20] ^= 1;
        let mut flipped = good.clone();
        let n = flipped.len();
        flipped[n - 300] ^= 0x10;
        for data in [
            wrong_hash,
            flipped,
            good[..good.len() - 1].to_vec(),
            [good.clone(), vec![0]].concat(),
        ] {
            std::fs::write(bad.path(), &data).unwrap();
            assert!(decode_archive(bad.path(), None).is_err());
            assert!(decode_archive_serial(bad.path(), None).is_err());
        }
        // Disagreeing pairs, odd origin and out-of-buffer crops are errors.
        for (dng, sony) in [
            (Some([4, 2, 120, 512]), Some([4, 4, 120, 512])),
            (Some([3, 2, 120, 512]), None),
            (Some([16, 2, 120, 512]), None),
        ] {
            let data = with_crop(fixture(128, 520), dng, sony);
            assert!(crop(&data, data.len()).is_err());
        }
        // No crop declared: none reported.
        assert_eq!(crop(&original, original.len()).unwrap(), None);
        // A non-CFA original falls back to the general route.
        let generic: Vec<u8> = (0..20001).map(|i| (i * 73) as u8).collect();
        let path = archived(&generic);
        assert!(decode_archive(&path, None).unwrap().is_none());
    }
}
