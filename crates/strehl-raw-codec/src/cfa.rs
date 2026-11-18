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
fn sample_bytes(samples: &[u16]) -> &[u8] {
    // SAFETY: u16 has no padding and alignment 2 >= 1; on a little-endian host
    // these are exactly the strip's original little-endian bytes.
    unsafe { std::slice::from_raw_parts(samples.as_ptr().cast::<u8>(), samples.len() * 2) }
}

/// Decode an archive whose original is a plain CFA-strip TIFF directly into
/// samples. `buffer` is reused when its length matches.
pub fn decode_archive(path: &Path, buffer: Option<Vec<u16>>) -> Result<Option<CfaFile>> {
    decode_archive_impl(path, buffer, None, false)
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
    decode_archive_impl(path, buffer, None, true)
}

/// A decoding thread's reused state for [`decode_archive_serial`].
struct Resident {
    file: Vec<u8>,
    scratch: Vec<u8>,
    zstd: zstd::bulk::Decompressor<'static>,
}

thread_local! {
    static RESIDENT: std::cell::RefCell<Option<Resident>> = const { std::cell::RefCell::new(None) };
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
    decode_archive_impl(path, buffer, Some(rows), false)
}

fn decode_archive_impl(
    path: &Path,
    buffer: Option<Vec<u16>>,
    rows: Option<&[bool]>,
    serial: bool,
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
                file: Vec::new(),
                scratch: Vec::new(),
                zstd: zstd::bulk::Decompressor::new()?,
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
    let mut file = match sparse.as_mut() {
        None if resident.is_some() => {
            let r = resident.as_mut().expect("resident state");
            let mut file = std::mem::take(&mut r.file);
            file.clear();
            File::open(path)
                .and_then(|mut f| f.read_to_end(&mut file))
                .with_context(|| format!("Read {}", path.display()))?;
            file
        }
        None => std::fs::read(path).with_context(|| format!("Read {}", path.display()))?,
        Some(f) => {
            let len = f.metadata()?.len() as usize;
            let mut file = vec![0u8; len];
            let head = (archive::HEADER_BYTES as usize + 16).min(len);
            read_at(f, &mut file[..head], 0)?;
            file
        }
    };
    let header = archive::read_header(&file[..])?;
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
            if let Some(f) = sparse.as_mut() {
                read_at(f, &mut file[c.payload.clone()], c.payload.start as u64)?;
            }
            jobs.push((c, head));
        }
        rest = tail;
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
                    unpredict_into(&r.scratch[..c.n], c.width, dst);
                }
                _ => {
                    let raw = decode_bytes(&file, c)?;
                    for (d, b) in dst.iter_mut().zip(raw.as_chunks::<2>().0) {
                        *d = u16::from_le_bytes(*b);
                    }
                }
            }
            #[cfg(target_endian = "little")]
            hash.update(sample_bytes(dst));
        }
        let mut suffix = Vec::new();
        for c in &chunks[last + 1..] {
            suffix.extend_from_slice(&decode_bytes(&file, c)?);
        }
        hash.update(&suffix);
        let sum: String = hash.finalize().iter().map(|b| format!("{b:02x}")).collect();
        ensure!(sum == header.sha256, "RAW archive checksum mismatch");
        let crop = crop(&prefix, length)?;
        if let Some(mut r) = resident.take() {
            r.file = file;
            RESIDENT.with_borrow_mut(|slot| *slot = Some(r));
        }
        return Ok(Some(CfaFile {
            prefix,
            width: layout.width,
            height: layout.height,
            samples,
            crop,
            verified_sha256: true,
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
            decoded_rows,
        }));
    }
    let mut suffix = Vec::new();
    for c in &chunks[last + 1..] {
        suffix.extend_from_slice(&decode_bytes(&file, c)?);
    }
    drop(file);
    let mut hash = Sha256::new();
    hash.update(&prefix);
    #[cfg(target_endian = "little")]
    hash.update(sample_bytes(&samples));
    hash.update(&suffix);
    let sum: String = hash.finalize().iter().map(|b| format!("{b:02x}")).collect();
    ensure!(sum == header.sha256, "RAW archive checksum mismatch");
    let crop = crop(&prefix, length)?;
    Ok(Some(CfaFile {
        prefix,
        width: layout.width,
        height: layout.height,
        samples,
        crop,
        verified_sha256: true,
        decoded_rows: None,
    }))
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
