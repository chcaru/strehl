//! Archive format 2 (`STRHARC2`, plan stage Q19).
//!
//! Format 1 stores the camera host's transport stream: Zstd over the
//! reversible CFA predictor's residual bytes. Format 2 keeps the same
//! predictor (so the same residuals) and replaces Zstd with a code fitted to
//! them: each row's same-colour residuals in blocks of 32, a per-block shift
//! `k`, the `k` low bits of each zigzag residual stored raw and the high part
//! coded by a small canonical code per `k` per chunk, spread over eight
//! independent bit streams that one thread decodes in lockstep. Every chunk
//! carries a CRC-32 checked before it is decoded, on every route, and an
//! index after the envelope gives each chunk's place, so a row range is read
//! without walking the file. The envelope (original length and SHA-256) is
//! format 1's: the original file stays restorable byte for byte and its hash
//! stays its identity.
//!
//! MEASURED (2026-11-19, `examples/v2-bench.rs`, A7CR scarab archives,
//! 9600x6376): 4.3 % smaller than format 1 (8.16 bits per sample against
//! 8.53; 3 MB of each file is embedded previews that neither format
//! compresses); a one-thread decode about 8 % slower (95.6 ms a file against
//! 88.0), which full renders do not show (20.1 s against 20.4 s).
//!
//! Layout, all integers little-endian:
//!
//! ```text
//! envelope   magic "STRHARC2", u64 original length, 32-byte SHA-256
//! index      u32 index bytes (this field to the CRC, inclusive), u16 revision 1,
//!            u8 profile 0, u8 0, u32 width, u32 height, u64 strip offset,
//!            u32 rows per chunk, u32 chunk count,
//!            per chunk (36 bytes): u64 file offset, u32 stored bytes, u8 kind,
//!              3 zero bytes, u64 original offset, u32 original bytes, u64 CRC-32,
//!            u32 CRC-32 of the envelope and the index before it
//! payloads   in index order, contiguous, to the end of the file
//! ```
//!
//! Kinds: 0 Zstd bytes, 1 stored bytes, 2 sample rows (profile 0). The
//! chunks tile the original in order; byte chunks hold everything outside
//! the sample strip (the TIFF metadata), sample chunks tile the strip in
//! whole rows. A sample chunk:
//!
//! ```text
//! u16 mask of the shifts k used; per k in it, ascending: 64 code lengths, 4 bits each
//! 16 code lengths, 4 bits each, of the shift code
//! u32 byte length of the shift stream, then the stream: per block, in row
//!   order (row, colour, block), the code of its shift's difference (mod 16)
//!   from the block before it in its colour run (a run's first block: the
//!   first block of the run above; the chunk's first row: from 0)
//! u32 byte length of each of the 8 lanes, then the lanes
//! 8 zero bytes
//! ```
//!
//! Block `j` is written to lane `j % 8`: per sample the high part's code
//! (symbol 63 is an escape followed by the high part in 16 bits), then the
//! `k` low bits. Codes are canonical, at most 11 bits, read least
//! significant bit first. Every stream is exactly the bytes its bits need.
use crate::{MAX_CHUNK, MAX_RAW, cfa, predict};
use anyhow::{Context, Result, bail, ensure};
use rayon::prelude::*;
use sha2::{Digest, Sha256};
use std::io::{Read, Write};

pub const MAGIC: &[u8; 8] = b"STRHARC2";
pub const ENCODING: &str = "strehl-archive-v2";
/// Sample rows per chunk: 64 rows of a 9,600-pixel sensor are 1.2 MB of
/// samples. The predictor restarts at each chunk; MEASURED, 32 rows cost
/// 0.1 % more size and 128 rows saved under 0.1 %.
pub const ROWS: usize = 64;
const ENVELOPE: usize = 48;
const FIXED: usize = 32;
const ENTRY: usize = 36;
pub const MAX_ENTRIES: usize = 4096;
const BLOCK: usize = 32;
/// A block's shift: the bit length of its mean zigzag residual, less this.
const SHIFT_OFFSET: u32 = 3;
const LANES: usize = 8;
const SYMBOLS: usize = 64;
const ESCAPE: u32 = 63;
const MAX_BITS: u32 = 11;
const TABLE: usize = 1 << MAX_BITS;
const PAD: usize = 8;
const KIND_ZSTD: u8 = 0;
const KIND_STORED: u8 = 1;
const KIND_SAMPLES: u8 = 2;

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct Entry {
    pub offset: u64,
    pub stored: usize,
    pub kind: u8,
    pub start: usize,
    pub len: usize,
    pub crc: u32,
}

impl Entry {
    pub fn samples(&self) -> bool {
        self.kind == KIND_SAMPLES
    }
    pub fn payload(&self) -> std::ops::Range<usize> {
        self.offset as usize..self.offset as usize + self.stored
    }
}

#[derive(Clone, Debug)]
pub struct Index {
    pub length: usize,
    pub sha256: String,
    pub width: usize,
    pub height: usize,
    pub strip_offset: usize,
    pub rows_per_chunk: usize,
    pub entries: Vec<Entry>,
    /// Envelope and index bytes: where the first payload starts.
    pub body: usize,
}

impl Index {
    pub fn strip_end(&self) -> usize {
        self.strip_offset + 2 * self.width * self.height
    }
    /// The sample rows `e` holds.
    pub fn rows(&self, e: &Entry) -> std::ops::Range<usize> {
        let first = (e.start - self.strip_offset) / (2 * self.width);
        first..first + e.len / (2 * self.width)
    }
}

fn crc(bytes: &[u8]) -> u32 {
    crc32fast::hash(bytes)
}

fn hex(bytes: &[u8]) -> String {
    bytes.iter().map(|b| format!("{b:02x}")).collect()
}

/// Bytes of envelope and index, from the envelope and the index's first four
/// bytes (52 bytes); the index is then read whole and given to [`parse`].
pub fn head_len(first: &[u8]) -> Result<usize> {
    ensure!(
        first.len() >= ENVELOPE + 4 && &first[..8] == MAGIC,
        "Unsupported RAW archive version"
    );
    let n = u32::from_le_bytes(first[ENVELOPE..ENVELOPE + 4].try_into()?) as usize;
    ensure!(
        (FIXED + 4..=FIXED + ENTRY * MAX_ENTRIES + 4).contains(&n),
        "Invalid archive index"
    );
    Ok(ENVELOPE + n)
}

/// Parse and check the envelope and index (`head`, [`head_len`] bytes) of a
/// file `file_len` bytes long. Every chunk's place is checked against the
/// original and the file, so a reader can trust the index's arithmetic.
pub fn parse(head: &[u8], file_len: u64) -> Result<Index> {
    let body = head_len(head)?;
    ensure!(head.len() >= body, "Truncated archive index");
    let h = &head[..body];
    let stored = u32::from_le_bytes(h[body - 4..].try_into()?);
    ensure!(crc(&h[..body - 4]) == stored, "Archive index is damaged");
    let length = u64::from_le_bytes(h[8..16].try_into()?);
    ensure!(
        length > 0 && length <= MAX_RAW,
        "Invalid archive RAW length"
    );
    let length = length as usize;
    let at = |o: usize| ENVELOPE + o;
    let u32_at = |o: usize| u32::from_le_bytes(h[at(o)..at(o) + 4].try_into().unwrap()) as usize;
    ensure!(
        u16::from_le_bytes(h[at(4)..at(6)].try_into()?) == 1 && h[at(6)] == 0,
        "Unsupported archive revision or profile"
    );
    let (width, height) = (u32_at(8), u32_at(12));
    let strip_offset = u64::from_le_bytes(h[at(16)..at(24)].try_into()?) as usize;
    let (rows_per_chunk, count) = (u32_at(24), u32_at(28));
    ensure!(
        (2..=32768).contains(&width)
            && (2..=32768).contains(&height)
            && width % 2 == 0
            && height % 2 == 0
            && (2..=1024).contains(&rows_per_chunk)
            && rows_per_chunk % 2 == 0
            && count > 0
            && count <= MAX_ENTRIES
            && body == ENVELOPE + FIXED + ENTRY * count + 4
            && strip_offset
                .checked_add(2 * width * height)
                .is_some_and(|end| end <= length),
        "Invalid archive geometry"
    );
    let strip_end = strip_offset + 2 * width * height;
    let row_bytes = 2 * width;
    let mut entries = Vec::with_capacity(count);
    let (mut offset, mut start) = (body as u64, 0usize);
    for i in 0..count {
        let e = &h[at(FIXED + ENTRY * i)..at(FIXED + ENTRY * (i + 1))];
        let entry = Entry {
            offset: u64::from_le_bytes(e[..8].try_into()?),
            stored: u32::from_le_bytes(e[8..12].try_into()?) as usize,
            kind: e[12],
            start: u64::from_le_bytes(e[16..24].try_into()?) as usize,
            len: u32::from_le_bytes(e[24..28].try_into()?) as usize,
            crc: u32::try_from(u64::from_le_bytes(e[28..36].try_into()?))
                .context("Invalid chunk checksum")?,
        };
        ensure!(
            e[13..16] == [0, 0, 0]
                && entry.offset == offset
                && entry.start == start
                && entry.len > 0
                && entry.stored > 0
                && start + entry.len <= length,
            "Archive chunk {i} is out of place"
        );
        let end = start + entry.len;
        match entry.kind {
            KIND_ZSTD | KIND_STORED => ensure!(
                entry.len <= MAX_CHUNK
                    && (entry.kind == KIND_ZSTD || entry.stored == entry.len)
                    && (end <= strip_offset || start >= strip_end),
                "Archive chunk {i} is malformed"
            ),
            KIND_SAMPLES => ensure!(
                start >= strip_offset
                    && end <= strip_end
                    && (start - strip_offset).is_multiple_of(row_bytes)
                    && entry.len.is_multiple_of(row_bytes)
                    && (entry.len / row_bytes).is_multiple_of(2)
                    && entry.len / row_bytes <= rows_per_chunk
                    && entry.stored <= sample_bound(entry.len / 2),
                "Archive sample chunk {i} is malformed"
            ),
            _ => bail!("Unsupported archive chunk kind"),
        }
        offset += entry.stored as u64;
        start = end;
        entries.push(entry);
    }
    ensure!(start == length, "Archive chunks do not cover the original");
    ensure!(
        offset == file_len,
        "Archive length disagrees with its index"
    );
    Ok(Index {
        length,
        sha256: hex(&h[16..48]),
        width,
        height,
        strip_offset,
        rows_per_chunk,
        entries,
        body,
    })
}

/// The most a sample chunk of `n` samples may store: every sample escaped
/// with the longest code and 15 low bits, plus its headers.
fn sample_bound(n: usize) -> usize {
    n * (MAX_BITS as usize + 16 + 15) / 8 + n / BLOCK + 2 + 16 * SYMBOLS / 2 + 4 * LANES + PAD + 64
}

/// A byte chunk's original bytes, after its CRC.
pub fn chunk_bytes(e: &Entry, payload: &[u8]) -> Result<Vec<u8>> {
    ensure!(payload.len() == e.stored, "Truncated archive chunk");
    ensure!(
        crc(payload) == e.crc,
        "Archive chunk at {} is damaged",
        e.offset
    );
    Ok(match e.kind {
        KIND_STORED => payload.to_vec(),
        KIND_ZSTD => {
            ensure!(
                zstd::zstd_safe::find_frame_compressed_size(payload)
                    .map_err(|e| anyhow::anyhow!("Invalid Zstd frame: {e}"))?
                    == payload.len(),
                "Trailing data inside compressed chunk"
            );
            let raw = zstd::bulk::decompress(payload, e.len)?;
            ensure!(raw.len() == e.len, "Decoded chunk length mismatch");
            raw
        }
        _ => bail!("Not a byte chunk"),
    })
}

// ---------------------------------------------------------------- codes

/// Code lengths (at most [`MAX_BITS`]) for `freq`; zero for unused symbols.
/// Huffman's construction, with the counts halved until no code is too long.
fn code_lengths<const N: usize>(freq: &[u64; N]) -> [u8; N] {
    let mut f = *freq;
    loop {
        let mut lengths = [0u8; N];
        let used: Vec<usize> = (0..N).filter(|&s| f[s] > 0).collect();
        if used.len() == 1 {
            lengths[used[0]] = 1;
            return lengths;
        }
        // Nodes: (weight, symbols under it). Small alphabet: plain sorting.
        let mut nodes: Vec<(u64, Vec<usize>)> = used.iter().map(|&s| (f[s], vec![s])).collect();
        while nodes.len() > 1 {
            nodes.sort_by(|a, b| b.0.cmp(&a.0).then_with(|| b.1[0].cmp(&a.1[0])));
            let (wa, a) = nodes.pop().unwrap();
            let (wb, b) = nodes.pop().unwrap();
            for &s in a.iter().chain(&b) {
                lengths[s] += 1;
            }
            nodes.push((wa + wb, [a, b].concat()));
        }
        if lengths.iter().all(|&l| u32::from(l) <= MAX_BITS) {
            return lengths;
        }
        for v in &mut f {
            if *v > 0 {
                *v = (*v).div_ceil(2);
            }
        }
    }
}

/// Canonical codes for `lengths`, bit-reversed for a least-significant-bit
/// first stream; `None` if the lengths over-subscribe the code space.
fn canonical<const N: usize>(lengths: &[u8; N]) -> Option<[u16; N]> {
    let mut count = [0u32; MAX_BITS as usize + 1];
    for &l in lengths {
        count[l as usize] += 1;
    }
    count[0] = 0;
    let mut space = 0u32;
    for (l, &c) in count.iter().enumerate().skip(1) {
        space += c << (MAX_BITS as usize - l);
    }
    if space > TABLE as u32 {
        return None;
    }
    let mut next = [0u32; MAX_BITS as usize + 2];
    let mut code = 0u32;
    for l in 1..=MAX_BITS as usize {
        code = (code + count[l - 1]) << 1;
        next[l] = code;
    }
    let mut codes = [0u16; N];
    for s in 0..N {
        let l = lengths[s] as usize;
        if l > 0 {
            let c = next[l];
            next[l] += 1;
            codes[s] = (c.reverse_bits() >> (32 - l)) as u16;
        }
    }
    Some(codes)
}

/// Set in a table entry for the escape symbol and for windows where no code
/// starts (a damaged stream): both leave the fast path.
const SLOW: u32 = 1 << 31;

/// The decoding table of shift `k`: for every 11-bit window,
/// `(symbol << k) << 8 | k << 4 | length`, with [`SLOW`] on the escape and
/// on windows no code starts.
fn table(lengths: &[u8; SYMBOLS], k: u32, out: &mut [u32; TABLE]) -> Result<()> {
    let codes = canonical(lengths).context("Over-subscribed archive code")?;
    out.fill(SLOW);
    for s in 0..SYMBOLS {
        let l = lengths[s] as usize;
        if l == 0 {
            continue;
        }
        let flag = if s as u32 == ESCAPE {
            SLOW
        } else {
            // No 16-bit residual has a larger high part: only a damaged
            // code could name one.
            ensure!((s as u32) << k <= 0xffff, "Invalid archive code");
            0
        };
        let entry = flag | ((s as u32) << k) << 8 | k << 4 | l as u32;
        let mut i = codes[s] as usize;
        while i < TABLE {
            out[i] = entry;
            i += 1 << l;
        }
    }
    Ok(())
}

#[inline]
fn unzigzag(z: u16) -> u16 {
    (z >> 1) ^ 0u16.wrapping_sub(z & 1)
}

/// The shift for a block of zigzag residuals summing to `sum` over `n`.
#[inline]
fn shift(sum: u64, n: usize) -> u32 {
    let mean = (sum / n as u64) as u32;
    (32 - (mean + 1).leading_zeros())
        .saturating_sub(SHIFT_OFFSET)
        .min(15)
}

/// The shift block `j`'s is coded against: the block before it in its
/// colour run, the first block of the run above for a run's first block,
/// and 0 for the chunk's first row's first blocks.
#[inline]
fn previous_shift(ks: &[u8], j: usize, per_row: usize, per_colour: usize) -> u8 {
    if !(j % per_row).is_multiple_of(per_colour) {
        ks[j - 1]
    } else if j >= per_row {
        ks[j - per_row]
    } else {
        0
    }
}

/// Blocks per colour in a row, and the samples of a colour in a row.
fn grid(width: usize) -> (usize, usize) {
    let half = width / 2;
    (half.div_ceil(BLOCK), half)
}

struct Bits {
    out: Vec<u8>,
    acc: u64,
    n: u32,
}

impl Bits {
    fn new() -> Self {
        Self {
            out: Vec::new(),
            acc: 0,
            n: 0,
        }
    }
    #[inline]
    fn put(&mut self, v: u32, bits: u32) {
        debug_assert!(bits <= 32 && (bits == 32 || v >> bits == 0));
        self.acc |= u64::from(v) << self.n;
        self.n += bits;
        if self.n >= 32 {
            self.out.extend_from_slice(&(self.acc as u32).to_le_bytes());
            self.acc >>= 32;
            self.n -= 32;
        }
    }
    fn finish(mut self) -> Vec<u8> {
        while self.n > 0 {
            self.out.push(self.acc as u8);
            self.acc >>= 8;
            self.n = self.n.saturating_sub(8);
        }
        self.out
    }
}

/// Encode one sample chunk: `bytes` are `rows` rows of `width` samples.
fn encode_samples(bytes: &[u8], width: usize) -> Result<Vec<u8>> {
    let n = bytes.len() / 2;
    let rows = n / width;
    let planar = predict(bytes, width, false)?;
    let (lo, hi) = planar.split_at(n);
    let z = |i: usize| u16::from(lo[i]) | (u16::from(hi[i]) << 8);
    let (per_colour, half) = grid(width);
    let per_row = 2 * per_colour;
    let blocks = rows * per_row;
    // Each block's samples' indices, its shift, and the symbol counts per shift.
    let block = |j: usize| {
        let (y, q) = (j / per_row, j % per_row);
        let (p, b) = (q / per_colour, q % per_colour);
        let first = BLOCK * b;
        let count = BLOCK.min(half - first);
        (0..count).map(move |i| y * width + p + 2 * (first + i))
    };
    let mut ks = vec![0u8; blocks];
    let mut freq = [[0u64; SYMBOLS]; 16];
    for (j, k) in ks.iter_mut().enumerate() {
        let (sum, count) = block(j).fold((0u64, 0usize), |(s, c), i| (s + u64::from(z(i)), c + 1));
        let shift = shift(sum, count);
        *k = shift as u8;
        for i in block(j) {
            freq[shift as usize][((z(i) >> shift) as usize).min(ESCAPE as usize)] += 1;
        }
    }
    // A second pass: each block takes the neighbouring shift whose code
    // (built from the first pass's counts) spends the fewest bits on it.
    // MEASURED 0.1 % smaller than the mean's shift alone.
    let mut first = [[0u8; SYMBOLS]; 16];
    for k in 0..16 {
        if freq[k].iter().any(|&c| c > 0) {
            first[k] = code_lengths(&freq[k]);
        }
    }
    let cost = |j: usize, k: usize| -> Option<u64> {
        let l = &first[k];
        let mut bits = 0u64;
        for i in block(j) {
            let s = ((z(i) >> k) as usize).min(ESCAPE as usize);
            if l[s] == 0 {
                return None;
            }
            bits += u64::from(l[s]) + k as u64 + if s == ESCAPE as usize { 16 } else { 0 };
        }
        Some(bits)
    };
    freq = [[0u64; SYMBOLS]; 16];
    for (j, k) in ks.iter_mut().enumerate() {
        let k0 = usize::from(*k);
        let best = (k0.saturating_sub(1)..=(k0 + 1).min(15))
            .filter_map(|c| cost(j, c).map(|b| (b, c)))
            .min()
            .map_or(k0, |(_, c)| c);
        *k = best as u8;
        for i in block(j) {
            freq[best][((z(i) >> best) as usize).min(ESCAPE as usize)] += 1;
        }
    }
    let mut mask = 0u16;
    let mut lengths = [[0u8; SYMBOLS]; 16];
    let mut codes = [[0u16; SYMBOLS]; 16];
    for k in 0..16 {
        if freq[k].iter().any(|&c| c > 0) {
            mask |= 1 << k;
            lengths[k] = code_lengths(&freq[k]);
            codes[k] = canonical(&lengths[k]).context("Archive code construction failed")?;
        }
    }
    let mut lanes: Vec<Bits> = (0..LANES).map(|_| Bits::new()).collect();
    for (j, &k) in ks.iter().enumerate() {
        let k = u32::from(k);
        let (len, code) = (&lengths[k as usize], &codes[k as usize]);
        let lane = &mut lanes[j % LANES];
        for i in block(j) {
            let v = u32::from(z(i));
            let h = v >> k;
            let s = h.min(ESCAPE) as usize;
            lane.put(u32::from(code[s]), u32::from(len[s]));
            if s as u32 == ESCAPE {
                lane.put(h, 16);
            }
            lane.put(v & ((1 << k) - 1), k);
        }
    }
    let mut out = Vec::with_capacity(n * 2);
    out.extend_from_slice(&mask.to_le_bytes());
    for (k, lengths) in lengths.iter().enumerate() {
        if mask & (1 << k) != 0 {
            for pair in lengths.chunks(2) {
                out.push(pair[0] | (pair[1] << 4));
            }
        }
    }
    // The shifts, as differences from the block before in the same colour
    // run (the first block of a run: the one above it), coded like the
    // samples' high parts.
    let deltas: Vec<usize> = (0..blocks)
        .map(|j| usize::from(ks[j].wrapping_sub(previous_shift(&ks, j, per_row, per_colour)) & 15))
        .collect();
    let mut kfreq = [0u64; 16];
    for &d in &deltas {
        kfreq[d] += 1;
    }
    let klengths = code_lengths(&kfreq);
    let kcodes = canonical(&klengths).context("Archive code construction failed")?;
    for pair in klengths.chunks(2) {
        out.push(pair[0] | (pair[1] << 4));
    }
    let mut kbits = Bits::new();
    for &d in &deltas {
        kbits.put(u32::from(kcodes[d]), u32::from(klengths[d]));
    }
    let kbits = kbits.finish();
    out.extend_from_slice(&(kbits.len() as u32).to_le_bytes());
    out.extend_from_slice(&kbits);
    let lanes: Vec<Vec<u8>> = lanes.into_iter().map(Bits::finish).collect();
    for lane in &lanes {
        out.extend_from_slice(&(lane.len() as u32).to_le_bytes());
    }
    for lane in &lanes {
        out.extend_from_slice(lane);
    }
    out.extend_from_slice(&[0; PAD]);
    Ok(out)
}

/// A decoding thread's reused tables and residual rows.
#[derive(Default)]
pub struct Scratch {
    tables: Vec<[u32; TABLE]>,
    ks: Vec<u8>,
    z: Vec<u16>,
    rows: cfa::Rows,
}

/// Bytes past a lane's position that eight blocks' decode may read: 32
/// samples of at most 42 bits each, and the eight-byte window of the last.
const SLACK: usize = BLOCK * (MAX_BITS as usize + 16 + 15) / 8 + 8;

#[inline(always)]
fn peek(buf: &[u8], pos: usize) -> u64 {
    let i = pos >> 3;
    let w = match buf.get(i..i + 8) {
        Some(b) => u64::from_le_bytes(b.try_into().unwrap()),
        None => {
            let mut b = [0u8; 8];
            if i < buf.len() {
                b[..buf.len() - i].copy_from_slice(&buf[i..]);
            }
            u64::from_le_bytes(b)
        }
    };
    w >> (pos & 7)
}

/// The common case of one sample: the code's table entry `e` read from the
/// window `v` at `pos`; returns the zigzag residual.
#[inline(always)]
fn ordinary(pos: &mut usize, e: u32, v: u64) -> u32 {
    let len = e & 15;
    let k = (e >> 4) & 15;
    *pos += (len + k) as usize;
    (e >> 8) | ((v >> len) as u32 & ((1u32 << k) - 1))
}

/// An escape (the high part in 16 bits after the code) or a window where no
/// code starts, which marks the chunk damaged. A residual wider than 16
/// bits can only come from a damaged stream and is marked too.
#[cold]
#[inline(never)]
fn escape(buf: &[u8], pos: &mut usize, e: u32, v: u64, bad: &mut u32) -> u32 {
    let len = e & 15;
    let k = (e >> 4) & 15;
    if len == 0 {
        *bad = 1;
        *pos += 1;
        return 0;
    }
    let h = ((v >> len) & 0xffff) as u32;
    *pos += (len + 16) as usize;
    let low = (peek(buf, *pos) as u32) & ((1u32 << k) - 1);
    *pos += k as usize;
    let z = (h << k) | low;
    *bad |= z >> 16;
    z
}

/// One sample from a lane at `pos`, any position.
#[inline(always)]
fn sample(buf: &[u8], pos: &mut usize, t: &[u32; TABLE], bad: &mut u32) -> u32 {
    let v = peek(buf, *pos);
    let e = t[(v & (TABLE as u64 - 1)) as usize];
    if e & SLOW == 0 {
        ordinary(pos, e, v)
    } else {
        escape(buf, pos, e, v, bad)
    }
}

/// Eight full blocks, one per lane, decoded in lockstep: the chains of eight
/// independent streams interleave. Optimistic: on an escape or a damaged
/// window it stops and returns `false`, leaving `pos` as it was, and the
/// caller decodes the group again on the checked path. Escapes are rare
/// (about one sample in 80,000 on A7CR frames), so the loop holds no call
/// and its eight positions stay in registers.
///
/// # Safety
/// Every `pos[l] / 8 + SLACK <= buf.len()`, and every
/// `out[l] + 2 * BLOCK <= z.len()`.
#[inline(always)]
unsafe fn group(
    buf: &[u8],
    pos: &mut [usize; LANES],
    t: &[&[u32; TABLE]; LANES],
    out: &[usize; LANES],
    z: &mut [u16],
) -> bool {
    let b = buf.as_ptr();
    let zp = z.as_mut_ptr();
    let [
        mut p0,
        mut p1,
        mut p2,
        mut p3,
        mut p4,
        mut p5,
        mut p6,
        mut p7,
    ] = *pos;
    for i in (0..2 * BLOCK).step_by(2) {
        macro_rules! step {
            ($p:ident, $l:literal) => {
                // SAFETY: the caller's bounds: SLACK covers 32 samples of
                // the longest kind and the window of the last; the block's
                // outputs lie inside `z`.
                let w = unsafe { b.add($p >> 3).cast::<u64>().read_unaligned() };
                let v = u64::from_le(w) >> ($p & 7);
                let e = t[$l][(v & (TABLE as u64 - 1)) as usize];
                if e & SLOW != 0 {
                    return false;
                }
                let len = e & 15;
                let k = (e >> 4) & 15;
                $p += (len + k) as usize;
                let value = (e >> 8) | ((v >> len) as u32 & ((1u32 << k) - 1));
                unsafe { *zp.add(out[$l] + i) = value as u16 };
            };
        }
        step!(p0, 0);
        step!(p1, 1);
        step!(p2, 2);
        step!(p3, 3);
        step!(p4, 4);
        step!(p5, 5);
        step!(p6, 6);
        step!(p7, 7);
    }
    *pos = [p0, p1, p2, p3, p4, p5, p6, p7];
    true
}

/// [`group`] compiled for BMI2's flag-free shifts and bit extraction.
///
/// # Safety
/// As [`group`], on a processor with BMI2.
#[cfg(target_arch = "x86_64")]
#[target_feature(enable = "bmi1,bmi2")]
unsafe fn group_bmi2(
    buf: &[u8],
    pos: &mut [usize; LANES],
    t: &[&[u32; TABLE]; LANES],
    out: &[usize; LANES],
    z: &mut [u16],
) -> bool {
    // SAFETY: forwarded.
    unsafe { group(buf, pos, t, out, z) }
}

/// [`group`] in the best form this processor runs.
///
/// # Safety
/// As [`group`].
unsafe fn group_best(
    buf: &[u8],
    pos: &mut [usize; LANES],
    t: &[&[u32; TABLE]; LANES],
    out: &[usize; LANES],
    z: &mut [u16],
) -> bool {
    #[cfg(target_arch = "x86_64")]
    if std::is_x86_feature_detected!("bmi2") {
        // SAFETY: forwarded; the feature was detected.
        return unsafe { group_bmi2(buf, pos, t, out, z) };
    }
    // SAFETY: forwarded.
    unsafe { group(buf, pos, t, out, z) }
}

/// Decode one sample chunk's payload (CRC included) into its samples,
/// handed row by row to `emit` in order, as [`cfa::unpredict_rows`] does.
pub fn decode_samples(
    e: &Entry,
    payload: &[u8],
    width: usize,
    st: &mut Scratch,
    emit: impl FnMut(usize, &[u16]),
) -> Result<()> {
    ensure!(payload.len() == e.stored, "Truncated archive chunk");
    ensure!(
        crc(payload) == e.crc,
        "Archive chunk at {} is damaged",
        e.offset
    );
    let rows = e.len / (2 * width);
    let (per_colour, half) = grid(width);
    let per_row = 2 * per_colour;
    let blocks = rows * per_row;
    let mut at = 0usize;
    fn take_bytes<'a>(payload: &'a [u8], at: &mut usize, n: usize) -> Result<&'a [u8]> {
        let r = payload
            .get(*at..*at + n)
            .context("Truncated sample chunk")?;
        *at += n;
        Ok(r)
    }
    let take = |at: &mut usize, n: usize| take_bytes(payload, at, n);
    let mask = u16::from_le_bytes(take(&mut at, 2)?.try_into()?);
    let mut slot = [usize::MAX; 16];
    let mut used = 0;
    for (k, slot) in slot.iter_mut().enumerate() {
        if mask & (1 << k) != 0 {
            let packed = take(&mut at, SYMBOLS / 2)?;
            let mut lengths = [0u8; SYMBOLS];
            for (i, b) in packed.iter().enumerate() {
                lengths[2 * i] = b & 15;
                lengths[2 * i + 1] = b >> 4;
            }
            ensure!(
                lengths.iter().all(|&l| u32::from(l) <= MAX_BITS),
                "Invalid archive code"
            );
            if st.tables.len() <= used {
                st.tables.push([0; TABLE]);
            }
            table(&lengths, k as u32, &mut st.tables[used])?;
            *slot = used;
            used += 1;
        }
    }
    let packed = take(&mut at, 8)?;
    let mut klengths = [0u8; 16];
    for (i, b) in packed.iter().enumerate() {
        klengths[2 * i] = b & 15;
        klengths[2 * i + 1] = b >> 4;
    }
    ensure!(
        klengths.iter().all(|&l| u32::from(l) <= MAX_BITS),
        "Invalid archive code"
    );
    let kcodes = canonical(&klengths).context("Over-subscribed archive code")?;
    let mut ktable = [0u16; TABLE];
    for s in 0..16 {
        let l = klengths[s] as usize;
        let mut i = kcodes[s] as usize;
        while l > 0 && i < TABLE {
            ktable[i] = ((s as u16) << 4) | l as u16;
            i += 1 << l;
        }
    }
    let kbytes = u32::from_le_bytes(take(&mut at, 4)?.try_into()?) as usize;
    let kstream = take(&mut at, kbytes)?;
    st.ks.resize(blocks, 0);
    let mut kpos = 0usize;
    for j in 0..blocks {
        let e = ktable[(peek(kstream, kpos) & (TABLE as u64 - 1)) as usize];
        ensure!(e != 0, "Archive shift code is damaged");
        kpos += usize::from(e & 15);
        let k = previous_shift(&st.ks, j, per_row, per_colour).wrapping_add((e >> 4) as u8) & 15;
        st.ks[j] = k;
    }
    ensure!(
        kpos.div_ceil(8) == kbytes,
        "Archive shift stream ends out of place"
    );
    let ks = &st.ks;
    let k_of = |j: usize| ks[j];
    let mut lane_at = [0usize; LANES];
    let mut lane_end = [0usize; LANES];
    let mut sizes = [0usize; LANES];
    for s in &mut sizes {
        *s = u32::from_le_bytes(take(&mut at, 4)?.try_into()?) as usize;
    }
    for l in 0..LANES {
        lane_at[l] = at * 8;
        at += sizes[l];
        lane_end[l] = at * 8;
    }
    ensure!(
        at + PAD == payload.len(),
        "Sample chunk lanes disagree with its length"
    );
    for j in 0..blocks {
        ensure!(
            slot[k_of(j) as usize] != usize::MAX,
            "Block shift has no code"
        );
    }
    st.z.resize(rows * width, 0);
    let z = &mut st.z;
    let tables = &st.tables;
    let mut bad = 0u32;
    let mut pos = lane_at;
    let full = |b: usize| half.is_multiple_of(BLOCK) || (b % per_row) % per_colour + 1 < per_colour;
    let mut j = 0;
    while j < blocks {
        let group = LANES.min(blocks - j);
        // Eight full blocks: their lanes decoded in lockstep, the chains of
        // eight independent streams interleaved.
        let mut fast = false;
        if group == LANES
            && (j..j + LANES).all(full)
            && pos.iter().all(|&p| p / 8 + SLACK <= payload.len())
        {
            let mut base = [0usize; LANES];
            let mut t: [&[u32; TABLE]; LANES] = [&tables[0]; LANES];
            for l in 0..LANES {
                let b = j + l;
                let (y, q) = (b / per_row, b % per_row);
                let (p, c) = (q / per_colour, q % per_colour);
                base[l] = y * width + p + 2 * BLOCK * c;
                t[l] = &tables[slot[k_of(b) as usize]];
            }
            assert!(base.iter().all(|&o| o + 2 * BLOCK <= z.len()));
            // SAFETY: both bounds were checked just above.
            fast = unsafe { group_best(payload, &mut pos, &t, &base, z) };
        }
        if !fast {
            for b in j..j + group {
                let (y, q) = (b / per_row, b % per_row);
                let (p, c) = (q / per_colour, q % per_colour);
                let first = BLOCK * c;
                let t = &tables[slot[k_of(b) as usize]];
                let l = b % LANES;
                for i in 0..BLOCK.min(half - first) {
                    let v = sample(payload, &mut pos[l], t, &mut bad);
                    z[y * width + p + 2 * (first + i)] = v as u16;
                }
            }
        }
        j += group;
    }
    for l in 0..LANES {
        // A lane is exactly the bytes its bits need.
        ensure!(
            (pos[l] - lane_at[l]).div_ceil(8) * 8 == lane_end[l] - lane_at[l],
            "Archive lane {l} ends out of place"
        );
    }
    ensure!(bad == 0, "Archive sample chunk is damaged");
    let Scratch {
        z, rows: st_rows, ..
    } = st;
    cfa::unpredict_rows_from(
        width,
        rows,
        st_rows,
        |y, out| {
            for (o, &v) in out.iter_mut().zip(&z[y * width..(y + 1) * width]) {
                *o = unzigzag(v);
            }
        },
        emit,
    );
    Ok(())
}

// ---------------------------------------------------------------- whole files

/// Encode `original` (whose SHA-256 is `sha256`) as format 2, or `None` when
/// it is not a single plain CFA strip ([`crate::layout`]); such files stay
/// format 1. Sample chunks are encoded in parallel on the current pool.
pub fn encode(original: &[u8], sha256: &str) -> Result<Option<Vec<u8>>> {
    ensure!(
        !original.is_empty() && original.len() as u64 <= MAX_RAW,
        "Invalid original file size"
    );
    ensure!(
        sha256.len() == 64 && sha256.bytes().all(|b| b.is_ascii_hexdigit()),
        "Invalid archive checksum"
    );
    let Some(layout) = crate::layout(original) else {
        return Ok(None);
    };
    let (w, h) = (layout.width, layout.height);
    let strip_end = layout.offset + layout.length;
    // (kind hint, original range): byte pieces around the strip, row chunks in it.
    let mut pieces: Vec<(bool, std::ops::Range<usize>)> = Vec::new();
    let bytes = |pieces: &mut Vec<_>, a: usize, b: usize| {
        for s in (a..b).step_by(MAX_CHUNK) {
            pieces.push((false, s..(s + MAX_CHUNK).min(b)));
        }
    };
    bytes(&mut pieces, 0, layout.offset);
    let rows_per = ROWS;
    for y in (0..h).step_by(rows_per) {
        let a = layout.offset + 2 * w * y;
        pieces.push((true, a..a + 2 * w * rows_per.min(h - y)));
    }
    bytes(&mut pieces, strip_end, original.len());
    ensure!(pieces.len() <= MAX_ENTRIES, "Too many archive chunks");
    let encoded: Vec<(u8, Vec<u8>)> = pieces
        .par_iter()
        .map(|(samples, r)| -> Result<(u8, Vec<u8>)> {
            let raw = &original[r.clone()];
            if *samples {
                return Ok((KIND_SAMPLES, encode_samples(raw, w)?));
            }
            let z = zstd::bulk::compress(raw, 1)?;
            Ok(if z.len() < raw.len() {
                (KIND_ZSTD, z)
            } else {
                (KIND_STORED, raw.to_vec())
            })
        })
        .collect::<Result<_>>()?;
    let body = ENVELOPE + FIXED + ENTRY * pieces.len() + 4;
    let total = body + encoded.iter().map(|(_, p)| p.len()).sum::<usize>();
    let mut out = Vec::with_capacity(total);
    out.extend_from_slice(MAGIC);
    out.extend_from_slice(&(original.len() as u64).to_le_bytes());
    for i in (0..64).step_by(2) {
        out.push(u8::from_str_radix(&sha256[i..i + 2], 16)?);
    }
    out.extend_from_slice(&((body - ENVELOPE) as u32).to_le_bytes());
    out.extend_from_slice(&1u16.to_le_bytes());
    out.extend_from_slice(&[0, 0]);
    out.extend_from_slice(&(w as u32).to_le_bytes());
    out.extend_from_slice(&(h as u32).to_le_bytes());
    out.extend_from_slice(&(layout.offset as u64).to_le_bytes());
    out.extend_from_slice(&(rows_per as u32).to_le_bytes());
    out.extend_from_slice(&(pieces.len() as u32).to_le_bytes());
    let mut offset = body as u64;
    for ((_, r), (kind, payload)) in pieces.iter().zip(&encoded) {
        out.extend_from_slice(&offset.to_le_bytes());
        out.extend_from_slice(&(payload.len() as u32).to_le_bytes());
        out.extend_from_slice(&[*kind, 0, 0, 0]);
        out.extend_from_slice(&(r.start as u64).to_le_bytes());
        out.extend_from_slice(&(r.len() as u32).to_le_bytes());
        out.extend_from_slice(&u64::from(crc(payload)).to_le_bytes());
        offset += payload.len() as u64;
    }
    let c = crc(&out);
    out.extend_from_slice(&c.to_le_bytes());
    debug_assert_eq!(out.len(), body);
    for (_, payload) in &encoded {
        out.extend_from_slice(payload);
    }
    Ok(Some(out))
}

/// Decode a whole format-2 archive from a stream into the original bytes,
/// verifying every chunk's CRC and the whole file's SHA-256 against the
/// envelope. The stream must end exactly where the index says.
pub fn unpack(mut input: impl Read, mut output: impl Write) -> Result<crate::Decoded> {
    let mut first = [0u8; ENVELOPE + 4];
    input
        .read_exact(&mut first)
        .context("Truncated RAW archive header")?;
    let n = head_len(&first)?;
    let mut head = first.to_vec();
    head.resize(n, 0);
    input
        .read_exact(&mut head[ENVELOPE + 4..])
        .context("Truncated archive index")?;
    // The file's length is the index's own sum; checked again at the end.
    let claimed = claimed_len(&head)?;
    let index = parse(&head, claimed)?;
    let mut hash = Sha256::new();
    let mut st = Scratch::default();
    let mut payload = Vec::new();
    let mut row = Vec::new();
    for e in &index.entries {
        payload.resize(e.stored, 0);
        input
            .read_exact(&mut payload)
            .context("Truncated archive chunk")?;
        if e.samples() {
            row.clear();
            decode_samples(e, &payload, index.width, &mut st, |_, r| {
                #[cfg(target_endian = "little")]
                row.extend_from_slice(cfa::sample_bytes(r));
                #[cfg(target_endian = "big")]
                row.extend(r.iter().flat_map(|v| v.to_le_bytes()));
            })?;
            hash.update(&row);
            output.write_all(&row)?;
        } else {
            let raw = chunk_bytes(e, &payload)?;
            hash.update(&raw);
            output.write_all(&raw)?;
        }
    }
    ensure!(input.read(&mut [0u8; 1])? == 0, "Trailing archive bytes");
    let sum = hex(&hash.finalize());
    ensure!(sum == index.sha256, "RAW archive checksum mismatch");
    Ok(crate::Decoded {
        bytes: index.length as u64,
        wire_bytes: claimed,
        sha256: sum,
        chunks: index.entries.len(),
    })
}

/// The file length an index describes: its last chunk's end.
fn claimed_len(head: &[u8]) -> Result<u64> {
    let body = head_len(head)?;
    ensure!(
        body >= ENVELOPE + FIXED + ENTRY + 4,
        "Invalid archive index"
    );
    let last = body - 4 - ENTRY;
    let offset = u64::from_le_bytes(head[last..last + 8].try_into()?);
    let stored = u32::from_le_bytes(head[last + 8..last + 12].try_into()?);
    offset
        .checked_add(u64::from(stored))
        .context("Invalid archive index")
}

/// Whether `bytes` begin with format 2's magic.
pub fn is_v2(bytes: &[u8]) -> bool {
    bytes.get(..8) == Some(MAGIC)
}

#[cfg(test)]
mod tests {
    use super::*;

    fn sha(bytes: &[u8]) -> String {
        hex(&Sha256::digest(bytes))
    }

    fn noisy(width: usize, height: usize, seed: u64, amplitude: u32) -> Vec<u8> {
        let mut data = crate::tests::fixture(width, height);
        let mut s = seed | 1;
        for i in 0..width * height {
            s ^= s << 13;
            s ^= s >> 7;
            s ^= s << 17;
            let base = ((i / width) * 7 + (i % width) * 3 + (i % 2) * 400) as u32;
            let v = (base + (s as u32 % amplitude.max(1))) as u16;
            data[256 + 2 * i..258 + 2 * i].copy_from_slice(&v.to_le_bytes());
        }
        data
    }

    fn roundtrip(original: &[u8]) -> Vec<u8> {
        let encoded = encode(original, &sha(original)).unwrap().unwrap();
        let mut back = Vec::new();
        let d = unpack(encoded.as_slice(), &mut back).unwrap();
        assert_eq!(back, original);
        assert_eq!(d.sha256, sha(original));
        assert_eq!(d.wire_bytes, encoded.len() as u64);
        encoded
    }

    #[test]
    fn every_geometry_and_hostile_content_round_trips_exactly() {
        for (w, h) in [
            (2, 2),
            (4, 6),
            (64, 64),
            (66, 34),
            (130, 70),
            (128, 520),
            (200, 96),
        ] {
            roundtrip(&crate::tests::fixture(w, h));
            for amplitude in [1, 9, 300, 65536] {
                roundtrip(&noisy(
                    w,
                    h,
                    (w * h) as u64 + u64::from(amplitude),
                    amplitude,
                ));
            }
        }
        // All zero, all full scale, alternating extremes: escapes and k = 15.
        for fill in [[0u8, 0], [255, 255], [0, 128]] {
            let mut d = crate::tests::fixture(96, 64);
            for i in 0..96 * 64 {
                let v = if fill == [0, 128] && i % 3 == 0 {
                    [255, 255]
                } else {
                    fill
                };
                d[256 + 2 * i..258 + 2 * i].copy_from_slice(&v);
            }
            roundtrip(&d);
        }
    }

    #[test]
    fn a_non_cfa_file_is_left_to_format_1() {
        let generic: Vec<u8> = (0..20001).map(|i| (i * 73) as u8).collect();
        assert!(encode(&generic, &sha(&generic)).unwrap().is_none());
    }

    #[test]
    fn code_lengths_respect_the_limit_and_the_code_space() {
        let mut f = [0u64; SYMBOLS];
        for (s, v) in f.iter_mut().enumerate() {
            *v = 1 << (s.min(40));
        }
        let l = code_lengths(&f);
        assert!(l.iter().all(|&x| x >= 1 && u32::from(x) <= MAX_BITS));
        assert!(canonical(&l).is_some());
        let mut one = [0u64; SYMBOLS];
        one[3] = 10;
        assert_eq!(code_lengths(&one)[3], 1);
        let mut over = [0u8; SYMBOLS];
        over[..3].fill(1);
        assert!(canonical(&over).is_none());
    }

    /// Any flipped bit is refused: by the chunk's CRC, the index's CRC or the
    /// envelope's hash, never decoded into wrong bytes.
    #[test]
    fn damage_anywhere_is_refused() {
        let original = noisy(128, 96, 7, 300);
        let good = roundtrip(&original);
        let mut step = good.len() / 97;
        step = step.max(1);
        for at in (0..good.len())
            .step_by(step)
            .chain([8, 20, 48, 60, good.len() - 1])
        {
            let mut bad = good.clone();
            bad[at] ^= 0x10;
            assert!(
                unpack(bad.as_slice(), std::io::sink()).is_err(),
                "byte {at}"
            );
        }
        for n in [0, 47, 52, good.len() - 1] {
            assert!(unpack(&good[..n], std::io::sink()).is_err());
        }
        let mut tail = good.clone();
        tail.push(0);
        assert!(unpack(tail.as_slice(), std::io::sink()).is_err());
    }

    /// A stream whose CRC was recomputed after damage (an encoder fault, not
    /// bit rot) still cannot make the decoder read out of bounds or panic.
    #[test]
    fn a_forged_crc_on_damaged_lanes_fails_cleanly() {
        let original = noisy(130, 70, 3, 9000);
        let good = encode(&original, &sha(&original)).unwrap().unwrap();
        let index = parse(&good[..head_len(&good).unwrap()], good.len() as u64).unwrap();
        let e = index.entries.iter().find(|e| e.samples()).unwrap().clone();
        let mut seed = 0x1234_5678u64;
        for _ in 0..200 {
            let mut payload = good[e.payload()].to_vec();
            for _ in 0..4 {
                seed ^= seed << 13;
                seed ^= seed >> 7;
                seed ^= seed << 17;
                let i = (seed as usize) % payload.len();
                payload[i] ^= (seed >> 32) as u8 | 1;
            }
            let forged = Entry {
                crc: crc(&payload),
                ..e.clone()
            };
            let mut st = Scratch::default();
            let _ = decode_samples(&forged, &payload, index.width, &mut st, |_, _| {});
        }
    }
}
