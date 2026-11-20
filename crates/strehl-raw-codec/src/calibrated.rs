//! Format 3: a **calibrated** archive, written only by an explicit "compact"
//! of a finished stack. NOT lossless: every CFA sample is stored to within
//! half a step of `k` noise sigma (the camera's own noise at that level), and
//! the camera's full-size embedded JPEG is dropped (its IFD then points at the
//! 1616 x 1080 preview, which is kept).
//!
//! # Why
//!
//! MEASURED (2026-11-20, `experiments/stack-storage-2026-11-20`): 81-92 % of a
//! lossless archive's sensor bits are the sensor's noise, which no lossless
//! method removes. At k = 1 an A7CR archive is 2.5-3 times smaller, and a
//! render from such frames stands where a render from frames with the same
//! amount of random noise added stands (rms difference to the lossless render
//! 8.77 against 8.73 in flat tiles, 33.7 against 34.1 in detail tiles; detail
//! energy 1.0003): what it costs a photograph is its added noise, +0.2 to
//! +0.5 % in amplitude on that render.
//!
//! # The quantiser
//!
//! A table on the sample's own value, nothing else (no prediction, no
//! neighbours: an error cannot spread or follow an edge). Raw values are
//! grouped into consecutive bins of ODD width, the widest with
//! `(w^2 - 1) / 12 <= (k sigma)^2 / 12` at the bin's middle under the injected
//! noise model (`sigma^2 = gain (v - black) + read^2`, DN); a sample is
//! restored as its bin's middle member, so a locally flat density keeps a
//! zero-mean error. Near black, where `k sigma < 2.83` DN, bins are one value
//! wide (exact); 16383 (clipped) has a bin of its own.
//!
//! # Layout (little-endian)
//!
//! | Offset | Bytes | Meaning |
//! | --- | ---: | --- |
//! | 0 | 8 | `STRHARC3` |
//! | 8 | 8 | restored ARW length |
//! | 16 | 32 | SHA-256 of the restored ARW (what a decode yields) |
//! | 48 | 8 | the original ARW's length |
//! | 56 | 32 | the original ARW's SHA-256 (the capture journal's binding) |
//! | 88 | 4 | k x 1000 |
//! | 92 | 8 x 3 | gain (DN/e-), read noise (DN), black (DN) the table was built from, f64 |
//! | 116 | 8 | the noise variance the table adds, as a fraction of the model's (f64) |
//! | 124 | 4 | n, the number of codes |
//! | 128 | 2n | each code's restored value, strictly increasing, the last 16383 |
//! | 128 + 2n | 32 | SHA-256 of every byte before it |
//! | 160 + 2n | rest | a format-2 archive of the *code file*: the restored ARW with each strip sample replaced by its code |
//!
//! A decode checks the head's SHA-256 and lets format 2 check the code file's,
//! so every stored byte is verified; the restored ARW is a pure function of
//! the two. Its SHA-256 (offset 16) is checked by [`unpack`] and is the
//! identity caches key on.

use crate::{MAX_RAW, layout, v2};
use anyhow::{Context, Result, bail, ensure};
use sha2::{Digest, Sha256};
use std::io::{Read, Write};

pub const MAGIC: &[u8; 8] = b"STRHARC3";
pub const ENCODING: &str = "strehl-archive-v3-calibrated";
const WHITE: u16 = 16383;
const FIXED: usize = 128;

fn hex(bytes: &[u8]) -> String {
    bytes.iter().map(|b| format!("{b:02x}")).collect()
}

fn unhex(s: &str) -> Result<[u8; 32]> {
    ensure!(
        s.len() == 64 && s.bytes().all(|b| b.is_ascii_hexdigit()),
        "Invalid SHA-256"
    );
    let mut out = [0u8; 32];
    for (i, o) in out.iter_mut().enumerate() {
        *o = u8::from_str_radix(&s[2 * i..2 * i + 2], 16)?;
    }
    Ok(out)
}

/// The noise model a table is built from, in DN.
#[derive(Clone, Copy, Debug, PartialEq)]
pub struct Noise {
    pub gain: f64,
    pub read: f64,
    pub black: f64,
}

impl Noise {
    fn sigma(&self, v: f64) -> f64 {
        (self.gain * (v - self.black).max(0.0) + self.read * self.read).sqrt()
    }
}

/// The quantiser: each code's restored value, and each raw value's code.
#[derive(Clone, Debug)]
pub struct Table {
    pub k: f64,
    pub noise: Noise,
    pub values: Vec<u16>,
    code: Vec<u16>,
    /// Mean over the codes above black of the added variance, (w^2 - 1)/12,
    /// as a fraction of the model's variance at the code's value.
    pub added_variance: f64,
}

impl Table {
    pub fn new(k: f64, noise: Noise) -> Result<Self> {
        ensure!(
            (0.05..=4.0).contains(&k) && noise.gain > 0.0 && noise.read >= 0.0,
            "Invalid calibration"
        );
        let mut code = vec![0u16; usize::from(WHITE) + 1];
        let mut values = Vec::new();
        let mut widths = Vec::new();
        let mut v: usize = 0;
        while v < usize::from(WHITE) {
            let mut w = 1usize;
            loop {
                let w2 = w + 2;
                let mid = (v + (w2 - 1) / 2) as f64;
                let bound = (k * noise.sigma(mid)).powi(2);
                if v + w2 <= usize::from(WHITE) && ((w2 * w2 - 1) as f64) <= bound {
                    w = w2;
                } else {
                    break;
                }
            }
            let c = u16::try_from(values.len())?;
            code[v..v + w].fill(c);
            values.push((v + (w - 1) / 2) as u16);
            widths.push(w);
            v += w;
        }
        code[usize::from(WHITE)] = u16::try_from(values.len())?;
        values.push(WHITE);
        widths.push(1);
        let mut sum = 0.0;
        let mut n = 0usize;
        for (&value, &w) in values.iter().zip(&widths) {
            let s = noise.sigma(f64::from(value));
            if f64::from(value) > noise.black + 64.0 && value < WHITE {
                sum += ((w * w - 1) as f64 / 12.0) / (s * s);
                n += 1;
            }
        }
        Ok(Self {
            k,
            noise,
            values,
            code,
            added_variance: if n > 0 { sum / n as f64 } else { 0.0 },
        })
    }

    /// A table read from an archive: the codes come back, the inverse map is
    /// not needed.
    fn from_values(k: f64, noise: Noise, values: Vec<u16>, added_variance: f64) -> Result<Self> {
        ensure!(
            values.len() >= 2
                && values.windows(2).all(|w| w[0] < w[1])
                && values.last() == Some(&WHITE),
            "Invalid calibration table"
        );
        Ok(Self {
            k,
            noise,
            values,
            code: Vec::new(),
            added_variance,
        })
    }

    pub fn quantise(&self, v: u16) -> u16 {
        self.values[usize::from(self.code[usize::from(v)])]
    }
}

/// What a calibrated archive's head says.
#[derive(Clone, Debug)]
pub struct Head {
    pub restored_bytes: u64,
    pub restored_sha256: String,
    pub original_bytes: u64,
    pub original_sha256: String,
    pub table: Table,
    /// Where the embedded format-2 archive starts.
    pub inner: usize,
}

pub fn is_calibrated(bytes: &[u8]) -> bool {
    bytes.len() >= 8 && &bytes[..8] == MAGIC
}

/// Parse and check a head; `bytes` must hold at least the head.
pub fn parse_head(bytes: &[u8]) -> Result<Head> {
    ensure!(
        is_calibrated(bytes) && bytes.len() >= FIXED,
        "Not a calibrated archive"
    );
    let u64_at = |at: usize| u64::from_le_bytes(bytes[at..at + 8].try_into().unwrap());
    let f64_at = |at: usize| f64::from_le_bytes(bytes[at..at + 8].try_into().unwrap());
    let n = u32::from_le_bytes(bytes[124..128].try_into()?) as usize;
    ensure!((2..=16384).contains(&n), "Invalid calibration table size");
    let end = FIXED + 2 * n;
    ensure!(bytes.len() >= end + 32, "Truncated calibrated archive head");
    ensure!(
        Sha256::digest(&bytes[..end]).as_slice() == &bytes[end..end + 32],
        "Calibrated archive head checksum mismatch"
    );
    let values = bytes[FIXED..end]
        .as_chunks::<2>()
        .0
        .iter()
        .map(|c| u16::from_le_bytes([c[0], c[1]]))
        .collect();
    let restored_bytes = u64_at(8);
    let original_bytes = u64_at(48);
    ensure!(
        restored_bytes > 0 && restored_bytes <= MAX_RAW && original_bytes <= MAX_RAW,
        "Invalid archive RAW length"
    );
    let k = f64::from(u32::from_le_bytes(bytes[88..92].try_into()?)) / 1000.0;
    let noise = Noise {
        gain: f64_at(92),
        read: f64_at(100),
        black: f64_at(108),
    };
    Ok(Head {
        restored_bytes,
        restored_sha256: hex(&bytes[16..48]),
        original_bytes,
        original_sha256: hex(&bytes[56..88]),
        table: Table::from_values(k, noise, values, f64_at(116))?,
        inner: end + 32,
    })
}

/// Length of the head given its first 128 bytes.
pub fn head_len(first: &[u8]) -> Result<usize> {
    ensure!(first.len() >= FIXED, "Truncated calibrated archive head");
    let n = u32::from_le_bytes(first[124..128].try_into()?) as usize;
    ensure!((2..=16384).contains(&n), "Invalid calibration table size");
    Ok(FIXED + 2 * n + 32)
}

/// Little-endian TIFF reading for the JPEG redirect.
fn u16_at(b: &[u8], at: usize) -> Option<u16> {
    Some(u16::from_le_bytes(b.get(at..at + 2)?.try_into().ok()?))
}
fn u32_at(b: &[u8], at: usize) -> Option<u32> {
    Some(u32::from_le_bytes(b.get(at..at + 4)?.try_into().ok()?))
}

/// The main IFD chain's embedded JPEGs: `(entry offset of 0x0201, offset,
/// length, IFD offset)`.
fn chain_jpegs(b: &[u8]) -> Vec<(usize, usize, usize, usize)> {
    let mut out = Vec::new();
    if b.get(..4) != Some(b"II*\0") {
        return out;
    }
    let mut ifd = u32_at(b, 4).unwrap_or(0) as usize;
    let mut seen = 0;
    while ifd != 0 && seen < 8 {
        seen += 1;
        let Some(count) = u16_at(b, ifd) else { break };
        let (mut at, mut len) = (None, None);
        for i in 0..usize::from(count) {
            let p = ifd + 2 + 12 * i;
            match u16_at(b, p) {
                Some(0x0201) => at = Some((p, u32_at(b, p + 8).unwrap_or(0) as usize)),
                Some(0x0202) => len = u32_at(b, p + 8).map(|v| v as usize),
                _ => {}
            }
        }
        if let (Some((entry, offset)), Some(length)) = (at, len) {
            out.push((entry, offset, length, ifd));
        }
        ifd = u32_at(b, ifd + 2 + 12 * usize::from(count)).unwrap_or(0) as usize;
    }
    out
}

/// Point the largest embedded JPEG's IFD at the second largest (the camera's
/// preview), with that preview's dimensions, and zero the large JPEG's bytes.
/// Returns the bytes freed (0 when the file has no such pair).
pub fn drop_large_jpeg(b: &mut [u8], strip_start: usize) -> usize {
    let mut jpegs = chain_jpegs(b);
    jpegs.sort_by_key(|j| std::cmp::Reverse(j.2));
    let (Some(&(entry, offset, length, ifd)), Some(&(_, p_offset, p_length, p_ifd))) =
        (jpegs.first(), jpegs.get(1))
    else {
        return 0;
    };
    if offset + length > strip_start
        || offset < 8
        || b.get(offset..offset + 2) != Some(&[0xff, 0xd8])
        || b.get(p_offset..p_offset + 2) != Some(&[0xff, 0xd8])
    {
        return 0;
    }
    // The preview's dimensions, from its own IFD when it states them.
    let dims = |ifd: usize, b: &[u8]| -> Vec<(u16, u16, u32)> {
        let count = u16_at(b, ifd).unwrap_or(0);
        (0..usize::from(count))
            .filter_map(|i| {
                let p = ifd + 2 + 12 * i;
                let tag = u16_at(b, p)?;
                ((tag == 0x0100 || tag == 0x0101) && u32_at(b, p + 4)? == 1).then(|| {
                    let ty = u16_at(b, p + 2).unwrap_or(0);
                    let v = if ty == 3 {
                        u32::from(u16_at(b, p + 8).unwrap_or(0))
                    } else {
                        u32_at(b, p + 8).unwrap_or(0)
                    };
                    (tag, ty, v)
                })
            })
            .collect()
    };
    let preview_dims = dims(p_ifd, b);
    let count = u16_at(b, ifd).unwrap_or(0);
    for i in 0..usize::from(count) {
        let p = ifd + 2 + 12 * i;
        let tag = u16_at(b, p).unwrap_or(0);
        let ty = u16_at(b, p + 2).unwrap_or(0);
        if (tag == 0x0100 || tag == 0x0101)
            && let Some(&(_, _, v)) = preview_dims.iter().find(|d| d.0 == tag)
        {
            match ty {
                3 => b[p + 8..p + 10].copy_from_slice(&(v as u16).to_le_bytes()),
                4 => b[p + 8..p + 12].copy_from_slice(&v.to_le_bytes()),
                _ => {}
            }
        }
        if tag == 0x0202 {
            b[p + 8..p + 12].copy_from_slice(&(p_length as u32).to_le_bytes());
        }
    }
    b[entry + 8..entry + 12].copy_from_slice(&(p_offset as u32).to_le_bytes());
    b[offset..offset + length].fill(0);
    length
}

/// Compact one original ARW. Returns the archive, the restored ARW's SHA-256
/// and the bytes of the dropped JPEG. The archive is decoded again and
/// checked before it is returned.
pub fn encode(
    original: &[u8],
    original_sha256: &str,
    table: &Table,
) -> Result<(Vec<u8>, String, usize)> {
    ensure!(
        !original.is_empty() && original.len() as u64 <= MAX_RAW,
        "Invalid RAW size"
    );
    ensure!(
        hex(&Sha256::digest(original)) == original_sha256,
        "The RAW does not match its recorded SHA-256; not compacted"
    );
    let lay = layout(original).context("Not a plain CFA-strip RAW; it cannot be compacted")?;
    ensure!(
        lay.length == 2 * lay.width * lay.height && lay.offset + lay.length <= original.len(),
        "Not a 16-bit CFA strip"
    );
    let mut restored = original.to_vec();
    let dropped = drop_large_jpeg(&mut restored, lay.offset);
    let mut codes = Vec::with_capacity(restored.len());
    codes.extend_from_slice(&restored[..lay.offset]);
    for pair in original[lay.offset..lay.offset + lay.length]
        .as_chunks::<2>()
        .0
        .iter()
    {
        let v = u16::from_le_bytes([pair[0], pair[1]]);
        ensure!(v <= WHITE, "Sample above 14 bits; not compacted");
        let c = table.code[usize::from(v)];
        codes.extend_from_slice(&c.to_le_bytes());
    }
    codes.extend_from_slice(&restored[lay.offset + lay.length..]);
    for (dst, pair) in restored[lay.offset..lay.offset + lay.length]
        .as_chunks_mut::<2>()
        .0
        .iter_mut()
        .zip(
            original[lay.offset..lay.offset + lay.length]
                .as_chunks::<2>()
                .0
                .iter(),
        )
    {
        let v = table.quantise(u16::from_le_bytes([pair[0], pair[1]]));
        dst.copy_from_slice(&v.to_le_bytes());
    }
    let restored_sha = hex(&Sha256::digest(&restored));
    let codes_sha = hex(&Sha256::digest(&codes));
    let inner =
        v2::encode(&codes, &codes_sha)?.context("The code file is not a plain CFA strip")?;
    let mut out = Vec::with_capacity(inner.len() + 33_000);
    out.extend_from_slice(MAGIC);
    out.extend_from_slice(&(restored.len() as u64).to_le_bytes());
    out.extend_from_slice(&unhex(&restored_sha)?);
    out.extend_from_slice(&(original.len() as u64).to_le_bytes());
    out.extend_from_slice(&unhex(original_sha256)?);
    out.extend_from_slice(&((table.k * 1000.0).round() as u32).to_le_bytes());
    for x in [
        table.noise.gain,
        table.noise.read,
        table.noise.black,
        table.added_variance,
    ] {
        out.extend_from_slice(&x.to_le_bytes());
    }
    out.extend_from_slice(&u32::try_from(table.values.len())?.to_le_bytes());
    for v in &table.values {
        out.extend_from_slice(&v.to_le_bytes());
    }
    let digest = Sha256::digest(&out);
    out.extend_from_slice(&digest);
    out.extend_from_slice(&inner);
    let mut check = Vec::with_capacity(restored.len());
    let decoded = unpack(out.as_slice(), &mut check)?;
    ensure!(
        decoded.sha256 == restored_sha && check == restored,
        "A compacted archive did not restore its calibrated RAW; nothing was written"
    );
    Ok((out, restored_sha, dropped))
}

/// Map a code file's strip back to values, in place.
pub fn restore_strip(file: &mut [u8], table: &Table) -> Result<()> {
    let lay = layout(file).context("Calibrated archive holds no CFA strip")?;
    let n = table.values.len();
    for pair in file[lay.offset..lay.offset + lay.length]
        .as_chunks_mut::<2>()
        .0
        .iter_mut()
    {
        let c = usize::from(u16::from_le_bytes([pair[0], pair[1]]));
        ensure!(c < n, "Calibration code out of range");
        pair.copy_from_slice(&table.values[c].to_le_bytes());
    }
    Ok(())
}

/// Codes to values, for a decode that has the strip as samples.
pub fn restore_samples(samples: &mut [u16], table: &Table) -> Result<()> {
    let n = table.values.len();
    for s in samples {
        let c = usize::from(*s);
        ensure!(c < n, "Calibration code out of range");
        *s = table.values[c];
    }
    Ok(())
}

/// Restore the calibrated ARW, checking the head, the code file (format 2)
/// and the restored bytes' SHA-256.
pub fn unpack(mut input: impl Read, mut output: impl Write) -> Result<crate::Decoded> {
    let mut first = vec![0u8; FIXED];
    input
        .read_exact(&mut first)
        .context("Truncated calibrated archive head")?;
    let mut head = first.clone();
    head.resize(head_len(&first)?, 0);
    input
        .read_exact(&mut head[FIXED..])
        .context("Truncated calibrated archive head")?;
    let h = parse_head(&head)?;
    let mut codes = Vec::with_capacity(h.restored_bytes as usize);
    let inner = v2::unpack(&mut input, &mut codes)?;
    ensure!(
        codes.len() as u64 == h.restored_bytes,
        "Calibrated archive length disagrees with its head"
    );
    restore_strip(&mut codes, &h.table)?;
    let sha = hex(&Sha256::digest(&codes));
    if sha != h.restored_sha256 {
        bail!("Calibrated archive checksum mismatch");
    }
    output.write_all(&codes)?;
    Ok(crate::Decoded {
        bytes: codes.len() as u64,
        sha256: sha,
        ..inner
    })
}

#[cfg(test)]
mod tests {
    use super::*;

    const A7CR: Noise = Noise {
        gain: 0.4040,
        read: 1.334,
        black: 512.0,
    };

    /// Every bin is odd, contiguous, restored at its middle, within the
    /// k-sigma bound; near black the values are exact; 16383 is its own bin.
    #[test]
    fn the_table_keeps_each_sample_within_half_a_step_of_k_sigma() {
        for k in [0.5, 1.0, 2.0] {
            let t = Table::new(k, A7CR).unwrap();
            for v in 0..=WHITE {
                let r = t.quantise(v);
                let err = f64::from(r) - f64::from(v);
                let bound = (k * A7CR.sigma(f64::from(r))).max(1.0) / 2.0;
                assert!(err.abs() <= bound + 1e-9, "k {k} v {v} -> {r}");
                // A 3-wide bin needs (k sigma)^2 >= 8 at its middle.
                if k * A7CR.sigma(f64::from(v) + 1.0) < 8f64.sqrt() {
                    assert_eq!(r, v, "near black is exact");
                }
            }
            assert_eq!(t.quantise(WHITE), WHITE);
            assert_ne!(t.quantise(WHITE - 1), WHITE);
            // The fork's quant.py at k = 1 added 0.82 of (k sigma)^2 / 12.
            assert!(t.added_variance > 0.5 * k * k / 12.0 && t.added_variance <= k * k / 12.0);
        }
    }

    /// A synthetic plain-strip TIFF with three embedded JPEGs in the main
    /// IFD chain, the largest in the last IFD, as the A7CR writes them.
    fn tiff(width: usize, height: usize) -> Vec<u8> {
        let strip_at = 4096usize;
        let len = strip_at + 2 * width * height + 64;
        let mut b = vec![0u8; len];
        b[..4].copy_from_slice(b"II*\0");
        b[4..8].copy_from_slice(&8u32.to_le_bytes());
        let entry = |b: &mut Vec<u8>, p: usize, tag: u16, ty: u16, v: u32| {
            b[p..p + 2].copy_from_slice(&tag.to_le_bytes());
            b[p + 2..p + 4].copy_from_slice(&ty.to_le_bytes());
            b[p + 4..p + 8].copy_from_slice(&1u32.to_le_bytes());
            b[p + 8..p + 12].copy_from_slice(&v.to_le_bytes());
        };
        // IFD0 at 8: the raw image tags and the preview JPEG; next IFD at 512.
        let ifd0 = [
            (0x0100, 4, width as u32),
            (0x0101, 4, height as u32),
            (0x0102, 3, 16),
            (0x0103, 3, 1),
            (0x0106, 3, 32803),
            (0x0111, 4, strip_at as u32),
            (0x0115, 3, 1),
            (0x0117, 4, (2 * width * height) as u32),
            (0x0201, 4, 1024),
            (0x0202, 4, 100),
        ];
        b[8..10].copy_from_slice(&(ifd0.len() as u16).to_le_bytes());
        for (i, &(tag, ty, v)) in ifd0.iter().enumerate() {
            entry(&mut b, 10 + 12 * i, tag, ty, v);
        }
        let next0 = 10 + 12 * ifd0.len();
        b[next0..next0 + 4].copy_from_slice(&512u32.to_le_bytes());
        // IFD at 512: the large JPEG, with its own dimensions.
        let big = [
            (0x0100, 4, 9504u32),
            (0x0101, 4, 6336),
            (0x0201, 4, 2048),
            (0x0202, 4, 1500),
        ];
        b[512..514].copy_from_slice(&(big.len() as u16).to_le_bytes());
        for (i, &(tag, ty, v)) in big.iter().enumerate() {
            entry(&mut b, 514 + 12 * i, tag, ty, v);
        }
        for (at, n) in [(1024usize, 100usize), (2048, 1500)] {
            b[at] = 0xff;
            b[at + 1] = 0xd8;
            for x in 2..n {
                b[at + x] = (x * 7 % 251) as u8;
            }
        }
        let mut s = 1u32;
        for i in 0..width * height {
            s = s.wrapping_mul(1664525).wrapping_add(1013904223);
            let v = (512 + (s >> 20) % 9000 + (i % 97) as u32 * 30).min(16383) as u16;
            b[strip_at + 2 * i..strip_at + 2 * i + 2].copy_from_slice(&v.to_le_bytes());
        }
        b
    }

    #[test]
    fn a_compacted_raw_restores_its_quantised_strip_and_points_at_the_preview() {
        let original = tiff(256, 128);
        let sha = hex(&Sha256::digest(&original));
        let table = Table::new(1.0, A7CR).unwrap();
        let (archive, restored_sha, dropped) = encode(&original, &sha, &table).unwrap();
        assert_eq!(dropped, 1500);
        let h = parse_head(&archive).unwrap();
        assert_eq!(h.original_sha256, sha);
        assert_eq!(h.restored_sha256, restored_sha);
        let mut restored = Vec::new();
        unpack(archive.as_slice(), &mut restored).unwrap();
        let lay = layout(&original).unwrap();
        for i in 0..lay.width * lay.height {
            let at = lay.offset + 2 * i;
            let v = u16::from_le_bytes([original[at], original[at + 1]]);
            let r = u16::from_le_bytes([restored[at], restored[at + 1]]);
            assert_eq!(r, table.quantise(v));
        }
        // The large JPEG's IFD now names the preview and its bytes are gone.
        assert_eq!(u32_at(&restored, 514 + 12 * 2 + 8), Some(1024));
        assert_eq!(u32_at(&restored, 514 + 12 * 3 + 8), Some(100));
        assert!(restored[2048..2048 + 1500].iter().all(|&x| x == 0));
        assert_eq!(&restored[1024..1124], &original[1024..1124]);
        // Smaller than the lossless format 2.
        assert!(archive.len() < v2::encode(&original, &sha).unwrap().unwrap().len());
    }

    #[test]
    fn a_damaged_head_or_body_or_a_wrong_hash_is_refused() {
        let original = tiff(128, 64);
        let sha = hex(&Sha256::digest(&original));
        let table = Table::new(1.0, A7CR).unwrap();
        assert!(encode(&original, &"0".repeat(64), &table).is_err());
        let (archive, _, _) = encode(&original, &sha, &table).unwrap();
        for at in [20usize, 130, archive.len() - 10] {
            let mut bad = archive.clone();
            bad[at] ^= 0x10;
            assert!(
                unpack(bad.as_slice(), std::io::sink()).is_err(),
                "byte {at}"
            );
        }
    }
}
