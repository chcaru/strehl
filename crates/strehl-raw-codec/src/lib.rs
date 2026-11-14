//! Exact original-file transport, independent of camera RAW compression.
//!
//! Version 1 is deliberately distinct from the research Python wire format.
//! 16-byte header: magic, original length (u64 LE). Then independent chunks:
//! decoded length u32, payload length u32, method u8, CFA width u32, payload.
//! Methods: 0 = Zstd bytes, 8 = reversible CFA predictor + Zstd, 255 = identity.
//! The HTTP envelope binds the original length and SHA-256. No pixels are lost.
use anyhow::{Context, Result, bail, ensure};
use bytes::Bytes;
use rayon::ThreadPool;
use sha2::{Digest, Sha256};
use std::{
    collections::{BTreeMap, VecDeque},
    io::{self, Cursor, Read, Write},
    sync::{
        Arc,
        atomic::{AtomicBool, Ordering},
        mpsc::{self, Receiver},
    },
};

pub const ENCODING: &str = "strehl-raw-v1";
pub const ENCODING_HEADER: &str = "x-strehl-encoding";
pub const LENGTH_HEADER: &str = "x-strehl-decoded-length";
pub const MAX_RAW: u64 = 256 * 1024 * 1024;
pub const MAX_CHUNK: usize = 4 * 1024 * 1024;
pub const MAX_CHUNKS: usize = 1024;
pub const MAX_WIRE: u64 = MAX_RAW + 16 + 13 * MAX_CHUNKS as u64;
pub const WORKERS: usize = 4;
// Conservative workspace allowance beyond the single original byte body.
// Four bounded jobs, their results/current packet, Zstd contexts and thread stacks.
pub const WORKSPACE_BYTES: u64 = 96 * 1024 * 1024;
const MAGIC: &[u8; 8] = b"STRHRAW1";

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct Layout {
    pub width: usize,
    pub height: usize,
    pub offset: usize,
    pub length: usize,
}

/// Read only bounded, standard TIFF scalar tags. Anything unsupported falls
/// back to byte compression. This never decodes Sony's compressed RAW stream.
pub fn layout(bytes: &[u8]) -> Option<Layout> {
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
    if bytes.get(..4)? != b"II*\0" {
        return None;
    }
    let mut todo = vec![u32_at(bytes, 4)? as usize];
    let mut visited = Vec::new();
    let mut found = None;
    while let Some(at) = todo.pop() {
        if at == 0 {
            continue;
        }
        if visited.contains(&at) || visited.len() >= 16 {
            return None;
        }
        visited.push(at);
        let count = usize::from(u16_at(bytes, at)?);
        if count > 512 {
            return None;
        }
        let end = at.checked_add(2 + 12 * count)?;
        let next = u32_at(bytes, end)? as usize;
        let mut tags = BTreeMap::new();
        for i in 0..count {
            let p = at + 2 + 12 * i;
            let tag = u16_at(bytes, p)?;
            let typ = u16_at(bytes, p + 2)?;
            let n = u32_at(bytes, p + 4)?;
            if n == 1 && matches!(typ, 3 | 4) {
                let value = if typ == 3 {
                    u32::from(u16_at(bytes, p + 8)?)
                } else {
                    u32_at(bytes, p + 8)?
                };
                if tags.insert(tag, value).is_some() {
                    return None;
                }
            }
        }
        todo.extend([next, *tags.get(&330).unwrap_or(&0) as usize]);
        if tags.get(&262) == Some(&32803)
            && tags.get(&259) == Some(&1)
            && *tags.get(&277).unwrap_or(&1) == 1
        {
            let width = *tags.get(&256)? as usize;
            let height = *tags.get(&257)? as usize;
            let offset = *tags.get(&273)? as usize;
            let length = *tags.get(&279)? as usize;
            if !matches!(tags.get(&258), Some(14 | 16))
                || !(2..=32768).contains(&width)
                || !(2..=32768).contains(&height)
                || !width.is_multiple_of(2)
                || !height.is_multiple_of(2)
                || width.checked_mul(height)?.checked_mul(2)? != length
                || offset.checked_add(length)? > bytes.len()
                || found.is_some()
            {
                return None;
            }
            found = Some(Layout {
                width,
                height,
                offset,
                length,
            });
        }
    }
    found
}

fn valid_cfa(length: usize, width: usize) -> bool {
    (2..=32768).contains(&width)
        && width.is_multiple_of(2)
        && length.is_multiple_of(2 * width)
        && length / (2 * width) >= 2
        && (length / (2 * width)).is_multiple_of(2)
}

#[inline]
fn prediction(samples: &[u16], i: usize, x: usize, y: usize, width: usize) -> u16 {
    let left = if x >= 2 { u32::from(samples[i - 2]) } else { 0 };
    if y < 2 {
        return left as u16;
    }
    let up = u32::from(samples[i - 2 * width]);
    if x < 2 {
        return up as u16;
    }
    let corner = u32::from(samples[i - 2 * width - 2]);
    if x + 2 < width {
        ((left + up + corner + u32::from(samples[i - 2 * width + 2])) / 4) as u16
    } else if corner >= left.max(up) {
        left.min(up) as u16
    } else if corner <= left.min(up) {
        left.max(up) as u16
    } else {
        (left + up - corner) as u16
    }
}

fn predict(bytes: &[u8], width: usize, inverse: bool) -> Result<Vec<u8>> {
    ensure!(
        bytes.len() <= MAX_CHUNK && valid_cfa(bytes.len(), width),
        "Invalid CFA chunk dimensions"
    );
    let n = bytes.len() / 2;
    let mut samples = if inverse {
        vec![0u16; n]
    } else {
        bytes
            .as_chunks::<2>()
            .0
            .iter()
            .map(|p| u16::from_le_bytes([p[0], p[1]]))
            .collect()
    };
    let mut out = vec![0u8; bytes.len()];
    for y in 0..n / width {
        for x in 0..width {
            let i = y * width + x;
            let p = prediction(&samples, i, x, y, width);
            if inverse {
                let z = u16::from_le_bytes([bytes[i], bytes[n + i]]);
                let d = (z >> 1) as i16 ^ -((z & 1) as i16);
                samples[i] = p.wrapping_add(d as u16);
                out[2 * i..2 * i + 2].copy_from_slice(&samples[i].to_le_bytes());
            } else {
                let d = samples[i].wrapping_sub(p) as i16;
                let z = ((d as u16) << 1) ^ ((d >> 15) as u16);
                out[i] = z as u8;
                out[n + i] = (z >> 8) as u8;
            }
        }
    }
    Ok(out)
}

#[derive(Clone, Copy)]
struct Part {
    offset: usize,
    length: usize,
    width: usize,
}
fn parts(bytes: &[u8]) -> VecDeque<Part> {
    fn plain(parts: &mut VecDeque<Part>, start: usize, end: usize) {
        for at in (start..end).step_by(MAX_CHUNK) {
            parts.push_back(Part {
                offset: at,
                length: (end - at).min(MAX_CHUNK),
                width: 0,
            });
        }
    }
    let mut result = VecDeque::new();
    if let Some(raw) = layout(bytes) {
        plain(&mut result, 0, raw.offset);
        let rows = 128.min(MAX_CHUNK / (raw.width * 2)) / 2 * 2;
        let stride = raw.width * 2 * rows;
        for at in (raw.offset..raw.offset + raw.length).step_by(stride) {
            result.push_back(Part {
                offset: at,
                length: (raw.offset + raw.length - at).min(stride),
                width: raw.width,
            });
        }
        plain(&mut result, raw.offset + raw.length, bytes.len());
    } else {
        plain(&mut result, 0, bytes.len());
    }
    result
}
fn pack(bytes: &[u8], part: Part) -> Result<Vec<u8>> {
    let raw = &bytes[part.offset..part.offset + part.length];
    let transformed;
    let input = if part.width != 0 {
        transformed = predict(raw, part.width, false)?;
        transformed.as_slice()
    } else {
        raw
    };
    let compressed = zstd::bulk::compress(input, 1)?;
    let (payload, method, width) = if compressed.len() < raw.len() {
        (
            compressed.as_slice(),
            if part.width == 0 { 0 } else { 8 },
            part.width,
        )
    } else {
        (raw, 255, 0)
    };
    let mut packet = Vec::with_capacity(13 + payload.len());
    packet.extend_from_slice(&(raw.len() as u32).to_le_bytes());
    packet.extend_from_slice(&(payload.len() as u32).to_le_bytes());
    packet.push(method);
    packet.extend_from_slice(&(width as u32).to_le_bytes());
    packet.extend_from_slice(payload);
    Ok(packet)
}

/// A retry constructs a new encoder over the same immutable original body.
/// At most four chunks are in flight; no full compressed-file copy is retained.
pub struct Encoder {
    bytes: Bytes,
    pool: Arc<ThreadPool>,
    parts: VecDeque<Part>,
    pending: VecDeque<Receiver<Result<Vec<u8>>>>,
    current: Cursor<Vec<u8>>,
    cancelled: Arc<AtomicBool>,
}
impl Encoder {
    pub fn new(bytes: Bytes, pool: Arc<ThreadPool>) -> Result<Self> {
        ensure!(
            !bytes.is_empty() && bytes.len() as u64 <= MAX_RAW,
            "Invalid original file size"
        );
        let parts = parts(&bytes);
        ensure!(
            parts.len() <= MAX_CHUNKS && parts.iter().all(|p| p.length <= MAX_CHUNK),
            "Too many or oversized chunks"
        );
        let mut header = MAGIC.to_vec();
        header.extend_from_slice(&(bytes.len() as u64).to_le_bytes());
        let mut encoder = Self {
            bytes,
            pool,
            parts,
            pending: VecDeque::new(),
            current: Cursor::new(header),
            cancelled: Arc::new(AtomicBool::new(false)),
        };
        for _ in 0..WORKERS {
            encoder.schedule();
        }
        Ok(encoder)
    }
    fn schedule(&mut self) {
        if let Some(part) = self.parts.pop_front() {
            let bytes = self.bytes.clone();
            let cancelled = self.cancelled.clone();
            let (tx, rx) = mpsc::channel();
            self.pool.spawn(move || {
                if !cancelled.load(Ordering::Relaxed) {
                    // A worker panic must fail this upload, never abort the service.
                    let result = std::panic::catch_unwind(|| pack(&bytes, part))
                        .unwrap_or_else(|_| Err(anyhow::anyhow!("Compression worker failed")));
                    let _ = tx.send(result);
                }
            });
            self.pending.push_back(rx);
        }
    }
}
impl Read for Encoder {
    fn read(&mut self, out: &mut [u8]) -> io::Result<usize> {
        if out.is_empty() {
            return Ok(0);
        }
        loop {
            let n = self.current.read(out)?;
            if n != 0 {
                return Ok(n);
            }
            let Some(pending) = self.pending.pop_front() else {
                return Ok(0);
            };
            let packet = pending
                .recv()
                .map_err(io::Error::other)?
                .map_err(io::Error::other)?;
            self.current = Cursor::new(packet);
            self.schedule();
        }
    }
}
impl Drop for Encoder {
    fn drop(&mut self) {
        self.cancelled.store(true, Ordering::Relaxed);
    }
}

#[derive(Debug)]
pub struct Decoded {
    pub bytes: u64,
    pub wire_bytes: u64,
    pub sha256: String,
    pub chunks: usize,
}
struct Counted<R> {
    reader: R,
    bytes: u64,
}
impl<R: Read> Read for Counted<R> {
    fn read(&mut self, out: &mut [u8]) -> io::Result<usize> {
        let n = self.reader.read(out)?;
        self.bytes += n as u64;
        if self.bytes > MAX_WIRE {
            return Err(io::Error::other("Encoded transfer exceeds wire limit"));
        }
        Ok(n)
    }
}

/// Decode into a private partial file (or a sink for a duplicate). Caller must
/// check SHA-256 and fsync before committing. Trailing bytes are always refused.
pub fn decode(
    reader: impl Read,
    mut output: impl Write,
    length: u64,
    compressed: bool,
) -> Result<Decoded> {
    ensure!(length <= MAX_RAW, "Original file exceeds size limit");
    let mut input = Counted { reader, bytes: 0 };
    let mut hash = Sha256::new();
    let mut total = 0u64;
    let mut chunks = 0usize;
    if compressed {
        let mut header = [0u8; 16];
        input
            .read_exact(&mut header)
            .context("Truncated transport header")?;
        ensure!(&header[..8] == MAGIC, "Unsupported transport version");
        ensure!(
            u64::from_le_bytes(header[8..].try_into()?) == length && length > 0,
            "Original length disagrees with envelope"
        );
        while total < length {
            chunks += 1;
            ensure!(chunks <= MAX_CHUNKS, "Too many transport chunks");
            let mut h = [0u8; 13];
            input.read_exact(&mut h).context("Truncated chunk header")?;
            let n = u32::from_le_bytes(h[..4].try_into()?) as usize;
            let packed = u32::from_le_bytes(h[4..8].try_into()?) as usize;
            let mode = h[8];
            let width = u32::from_le_bytes(h[9..].try_into()?) as usize;
            ensure!(
                n > 0 && n <= MAX_CHUNK && packed > 0 && packed <= n && total + n as u64 <= length,
                "Invalid chunk lengths"
            );
            match mode {
                255 => ensure!(width == 0 && packed == n, "Invalid identity chunk"),
                0 => ensure!(width == 0, "Unexpected dimensions on byte chunk"),
                8 => ensure!(valid_cfa(n, width), "Invalid CFA chunk dimensions"),
                _ => bail!("Unsupported chunk method"),
            }
            let mut payload = vec![0u8; packed];
            input
                .read_exact(&mut payload)
                .context("Truncated chunk payload")?;
            let raw = if mode == 255 {
                payload
            } else {
                ensure!(
                    zstd::zstd_safe::find_frame_compressed_size(&payload)
                        .map_err(|e| anyhow::anyhow!("Invalid Zstd frame: {e}"))?
                        == packed,
                    "Trailing data inside compressed chunk"
                );
                let decoded = zstd::bulk::decompress(&payload, n)?;
                ensure!(decoded.len() == n, "Decoded chunk length mismatch");
                if mode == 8 {
                    predict(&decoded, width, true)?
                } else {
                    decoded
                }
            };
            hash.update(&raw);
            output.write_all(&raw)?;
            total += raw.len() as u64;
        }
    } else {
        let mut block = [0u8; 128 * 1024];
        while total < length {
            let wanted = (length - total).min(block.len() as u64) as usize;
            let n = input.read(&mut block[..wanted])?;
            ensure!(n > 0, "Transfer was incomplete");
            hash.update(&block[..n]);
            output.write_all(&block[..n])?;
            total += n as u64;
        }
    }
    ensure!(input.read(&mut [0u8; 1])? == 0, "Trailing transport bytes");
    Ok(Decoded {
        bytes: total,
        wire_bytes: input.bytes,
        chunks,
        sha256: hash.finalize().iter().map(|b| format!("{b:02x}")).collect(),
    })
}

#[cfg(test)]
mod tests {
    use super::*;

    pub(crate) fn fixture(width: usize, height: usize) -> Vec<u8> {
        let offset = 256;
        let mut data = vec![0u8; offset + width * height * 2 + 101];
        data[..4].copy_from_slice(b"II*\0");
        data[4..8].copy_from_slice(&8u32.to_le_bytes());
        let tags = [
            (256, width),
            (257, height),
            (258, 16),
            (259, 1),
            (262, 32803),
            (273, offset),
            (277, 1),
            (279, width * height * 2),
        ];
        data[8..10].copy_from_slice(&(tags.len() as u16).to_le_bytes());
        for (i, (tag, value)) in tags.into_iter().enumerate() {
            let p = 10 + i * 12;
            data[p..p + 2].copy_from_slice(&(tag as u16).to_le_bytes());
            data[p + 2..p + 4].copy_from_slice(&4u16.to_le_bytes());
            data[p + 4..p + 8].copy_from_slice(&1u32.to_le_bytes());
            data[p + 8..p + 12].copy_from_slice(&(value as u32).to_le_bytes());
        }
        for i in 0..width * height {
            let value = ((i / width) * 7 + (i % width) * 3 + (i % 2) * 400) as u16;
            data[offset + 2 * i..offset + 2 * i + 2].copy_from_slice(&value.to_le_bytes());
        }
        let end = data.len();
        data[end - 101..].fill(79);
        data
    }
    fn encoded(data: &[u8]) -> Vec<u8> {
        let pool = Arc::new(
            rayon::ThreadPoolBuilder::new()
                .num_threads(WORKERS)
                .build()
                .unwrap(),
        );
        let mut result = Vec::new();
        Encoder::new(data.to_vec().into(), pool)
            .unwrap()
            .read_to_end(&mut result)
            .unwrap();
        result
    }
    #[test]
    fn exact_roundtrip_cfa_generic_and_full_u16_boundaries() {
        let cfa = fixture(128, 260);
        assert_eq!(layout(&cfa).unwrap().height, 260);
        for data in [cfa, (0..20001).map(|i| (i * 73) as u8).collect()] {
            let wire = encoded(&data);
            let mut decoded = Vec::new();
            let receipt = decode(wire.as_slice(), &mut decoded, data.len() as u64, true).unwrap();
            assert_eq!(decoded, data);
            assert_eq!(receipt.wire_bytes, wire.len() as u64);
        }
        let values: Vec<u8> = (0..65536u32)
            .flat_map(|n| (n as u16).to_le_bytes())
            .collect();
        for width in [2, 4, 128, 32768] {
            assert_eq!(
                predict(&predict(&values, width, false).unwrap(), width, true).unwrap(),
                values
            );
        }
        // Independently calculated first two rows: left-of-same-CFA prediction.
        let raw: Vec<u8> = [0u16, 65535, 1, 65534, 32768, 32767, 0, 65535]
            .into_iter()
            .flat_map(u16::to_le_bytes)
            .collect();
        let z = predict(&raw, 4, false).unwrap();
        assert_eq!(
            z,
            [
                0, 1, 2, 1, 255, 254, 255, 255, 0, 0, 0, 0, 255, 255, 255, 255
            ]
        );
    }
    #[test]
    fn malformed_and_bomb_inputs_fail_before_commit() {
        let data = fixture(32, 132);
        let good = encoded(&data);
        let mut wrong_magic = good.clone();
        wrong_magic[7] ^= 1;
        let mut wrong_length = good.clone();
        wrong_length[8] ^= 1;
        let mut oversized = good.clone();
        oversized[16..20].copy_from_slice(&u32::MAX.to_le_bytes());
        let mut unknown = good.clone();
        unknown[24] = 5;
        let mut trailing = good.clone();
        trailing.push(1);
        for bad in [
            good[..15].to_vec(),
            good[..good.len() - 1].to_vec(),
            wrong_magic,
            wrong_length,
            oversized,
            unknown,
            trailing,
        ] {
            assert!(decode(bad.as_slice(), io::sink(), data.len() as u64, true).is_err());
        }
        // A tiny declared output cannot cause a large Zstd expansion allocation.
        let payload = zstd::bulk::compress(&vec![0u8; 1024 * 1024], 1).unwrap();
        let mut bomb = MAGIC.to_vec();
        bomb.extend_from_slice(&1024u64.to_le_bytes());
        bomb.extend_from_slice(&1024u32.to_le_bytes());
        bomb.extend_from_slice(&(payload.len() as u32).to_le_bytes());
        bomb.push(0);
        bomb.extend_from_slice(&0u32.to_le_bytes());
        bomb.extend_from_slice(&payload);
        assert!(decode(bomb.as_slice(), io::sink(), 1024, true).is_err());
        assert!(decode(&b"abc"[..], io::sink(), 2, false).is_err());
        assert!(decode(&b"a"[..], io::sink(), 2, false).is_err());
    }
    #[test]
    fn malformed_tiff_falls_back_and_preserves_bytes() {
        let mut data = fixture(32, 4);
        // Invalid strip byte count; never apply a guessed CFA layout.
        data[10 + 7 * 12 + 8..10 + 7 * 12 + 12].copy_from_slice(&u32::MAX.to_le_bytes());
        assert!(layout(&data).is_none());
        let mut output = Vec::new();
        decode(
            encoded(&data).as_slice(),
            &mut output,
            data.len() as u64,
            true,
        )
        .unwrap();
        assert_eq!(data, output);
    }
}

pub mod archive;
