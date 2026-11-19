//! STRHARC1: 48-byte header (magic, u64 LE original size, binary SHA-256),
//! followed by an unchanged STRHRAW1 transport stream. No lossy conversion.
//! Every complete read verifies the original bytes, including all metadata.
//!
//! STRHARC2 ([`crate::v2`]) has the same 48-byte envelope, then an index and
//! a code built for decoding. Every reader here takes either; the magic
//! decides. Format 1 stays readable for good.
use crate::{Decoded, Encoder, MAX_RAW, WORKERS, decode, v2};
use anyhow::{Context, Result, ensure};
use sha2::{Digest, Sha256};
use std::{
    fs::File,
    io::{self, BufReader, Read, Seek, SeekFrom, Write},
    path::Path,
    sync::Arc,
};

pub const EXTENSION: &str = "straw";
pub const ENCODING: &str = "strehl-archive-v1";
pub const ENCODING_V2: &str = v2::ENCODING;
pub const HEADER_BYTES: u64 = 48;
const MAGIC: &[u8; 8] = b"STRHARC1";

pub fn is_archive(path: &Path) -> bool {
    path.extension()
        .is_some_and(|e| e.eq_ignore_ascii_case(EXTENSION))
}

#[derive(Debug)]
pub struct Header {
    pub bytes: u64,
    pub sha256: String,
    /// 1 or 2.
    pub format: u8,
}

/// The storage format new archives are written in: 2, or 1 when
/// `STREHL_ARCHIVE_FORMAT=1` asks for the old one (a diagnostic switch).
pub fn default_format() -> u8 {
    match std::env::var("STREHL_ARCHIVE_FORMAT").as_deref() {
        Ok("1") => 1,
        _ => 2,
    }
}

pub fn write_header(mut out: impl Write, length: u64, sha256: &str) -> Result<()> {
    ensure!(
        length > 0 && length <= MAX_RAW,
        "Invalid archive RAW length"
    );
    ensure!(
        sha256.len() == 64 && sha256.bytes().all(|b| b.is_ascii_hexdigit()),
        "Invalid archive checksum"
    );
    out.write_all(MAGIC)?;
    out.write_all(&length.to_le_bytes())?;
    for i in (0..64).step_by(2) {
        out.write_all(&[u8::from_str_radix(&sha256[i..i + 2], 16)?])?;
    }
    Ok(())
}

pub fn read_header(mut input: impl Read) -> Result<Header> {
    let mut h = [0; HEADER_BYTES as usize];
    input
        .read_exact(&mut h)
        .context("Truncated RAW archive header")?;
    let format = if &h[..8] == MAGIC {
        1
    } else if &h[..8] == v2::MAGIC {
        2
    } else {
        anyhow::bail!("Unsupported RAW archive version")
    };
    let bytes = u64::from_le_bytes(h[8..16].try_into()?);
    ensure!(bytes > 0 && bytes <= MAX_RAW, "Invalid archive RAW length");
    Ok(Header {
        bytes,
        sha256: h[16..].iter().map(|b| format!("{b:02x}")).collect(),
        format,
    })
}

/// Restore the original bytes of an archive in either format, verifying
/// every byte against the envelope's SHA-256.
pub fn unpack(mut input: impl Read, output: impl Write) -> Result<Decoded> {
    let mut magic = [0u8; 8];
    input
        .read_exact(&mut magic)
        .context("Truncated RAW archive header")?;
    if &magic == v2::MAGIC {
        return v2::unpack(io::Cursor::new(magic).chain(input), output);
    }
    let mut input = io::Cursor::new(magic).chain(input);
    let header = read_header(&mut input)?;
    let decoded = decode(input, output, header.bytes, true)?;
    ensure!(
        decoded.sha256 == header.sha256,
        "RAW archive checksum mismatch"
    );
    Ok(decoded)
}

pub fn verify(path: &Path) -> Result<Decoded> {
    unpack(BufReader::new(File::open(path)?), io::sink())
}

/// Retain the compressed input as it is validated; never create a decoded file.
/// The caller owns the private partial file and commits only after success.
pub fn retain(
    input: impl Read,
    mut output: impl Write,
    length: u64,
    sha256: &str,
) -> Result<Decoded> {
    write_header(&mut output, length, sha256)?;
    struct Tee<R, W> {
        input: R,
        output: W,
    }
    impl<R: Read, W: Write> Read for Tee<R, W> {
        fn read(&mut self, bytes: &mut [u8]) -> io::Result<usize> {
            let n = self.input.read(bytes)?;
            self.output.write_all(&bytes[..n])?;
            Ok(n)
        }
    }
    let decoded = decode(Tee { input, output }, io::sink(), length, true)?;
    ensure!(
        decoded.sha256 == sha256,
        "RAW checksum mismatch; archive was not committed"
    );
    Ok(decoded)
}

/// Older identity-only senders are compressed on the receiving PC. Input is
/// bounded to MAX_RAW, and no uncompressed disk file is made.
pub fn pack(bytes: Vec<u8>, mut output: impl Write) -> Result<()> {
    ensure!(
        !bytes.is_empty() && bytes.len() as u64 <= MAX_RAW,
        "Invalid RAW size"
    );
    let hash = Sha256::digest(&bytes)
        .iter()
        .map(|b| format!("{b:02x}"))
        .collect::<String>();
    write_header(&mut output, bytes.len() as u64, &hash)?;
    let pool = Arc::new(
        rayon::ThreadPoolBuilder::new()
            .num_threads(WORKERS)
            .build()?,
    );
    io::copy(&mut Encoder::new(bytes.into(), pool)?, &mut output)?;
    Ok(())
}

/// Store `original` (SHA-256 `sha256`, lower-case hex) as an archive in
/// `format`, and before returning it decode the stored bytes again and check
/// them against `sha256`: an archive is the only copy of a capture, so no
/// file leaves here that does not restore exactly. Files that are not a
/// plain CFA strip are stored in format 1 whatever is asked.
pub fn store(original: &[u8], sha256: &str, format: u8) -> Result<(Vec<u8>, u8)> {
    ensure!(
        !original.is_empty() && original.len() as u64 <= MAX_RAW,
        "Invalid RAW size"
    );
    let (stored, format) = match (format == 2)
        .then(|| v2::encode(original, sha256))
        .transpose()?
        .flatten()
    {
        Some(bytes) => (bytes, 2),
        None => {
            let mut out = Vec::with_capacity(original.len() / 2);
            write_header(&mut out, original.len() as u64, sha256)?;
            let pool = Arc::new(
                rayon::ThreadPoolBuilder::new()
                    .num_threads(WORKERS)
                    .build()?,
            );
            io::copy(&mut Encoder::new(original.to_vec().into(), pool)?, &mut out)?;
            (out, 1)
        }
    };
    let check = unpack(stored.as_slice(), io::sink())?;
    ensure!(
        check.sha256 == sha256 && check.bytes == original.len() as u64,
        "A new archive did not restore its original; nothing was stored"
    );
    Ok((stored, format))
}

pub fn read_original(path: &Path) -> Result<Vec<u8>> {
    let mut input = BufReader::new(File::open(path)?);
    let header = read_header(&mut input)?;
    let mut bytes = Vec::with_capacity(header.bytes as usize);
    if header.format == 2 {
        let mut input = BufReader::new(File::open(path)?);
        v2::unpack(&mut input, &mut bytes)?;
        return Ok(bytes);
    }
    let decoded = decode(input, &mut bytes, header.bytes, true)?;
    ensure!(
        decoded.sha256 == header.sha256,
        "RAW archive checksum mismatch"
    );
    Ok(bytes)
}

/// Seekable original bytes for TIFF metadata readers. Plain files still seek
/// directly on disk. An archive is opened sparsely: only the chunks before the
/// first CFA chunk and after the last one (the TIFF metadata) are decoded, a
/// few kilobytes of reads. A read that touches the pixel strip first expands
/// the whole original in memory and verifies its SHA-256, so no strip byte is
/// served unverified. Metadata bytes are not hash-verified on this path; every
/// pixel decode ([`crate::cfa::decode_archive`], [`read_original`]) verifies
/// the whole file, metadata included.
pub enum OriginalReader {
    File(File),
    Memory(io::Cursor<Vec<u8>>),
    Sparse(Box<Sparse>),
}
pub struct Sparse {
    path: std::path::PathBuf,
    length: u64,
    prefix: Vec<u8>,
    suffix_start: u64,
    suffix: Vec<u8>,
    position: u64,
    full: Option<Vec<u8>>,
}
pub fn open_original(path: &Path) -> io::Result<OriginalReader> {
    if is_archive(path) {
        match open_sparse(path) {
            Ok(Some(sparse)) => Ok(OriginalReader::Sparse(Box::new(sparse))),
            Ok(None) => read_original(path)
                .map(|b| OriginalReader::Memory(io::Cursor::new(b)))
                .map_err(io::Error::other),
            Err(e) => Err(io::Error::other(e)),
        }
    } else {
        File::open(path).map(OriginalReader::File)
    }
}
/// [`open_original`]'s sparse reader from metadata already decoded (a full
/// CFA decode's `prefix` and `suffix`, `cfa::CfaFile`): the original's first
/// `prefix.len()` bytes and its last `suffix.len()` bytes of `length`. A read
/// of the bytes between expands and verifies the whole original from `path`,
/// as the sparse reader does.
pub fn sparse_from_parts(
    path: &Path,
    length: u64,
    prefix: Vec<u8>,
    suffix: Vec<u8>,
) -> OriginalReader {
    let suffix_start = length.saturating_sub(suffix.len() as u64);
    OriginalReader::Sparse(Box::new(Sparse {
        path: path.to_owned(),
        length,
        prefix,
        suffix_start,
        suffix,
        position: 0,
        full: None,
    }))
}

struct Entry {
    start: u64,
    n: usize,
    packed: usize,
    mode: u8,
    width: usize,
    at: u64,
}
/// [`open_sparse`] for format 2: the index places the metadata chunks.
fn open_sparse_v2(path: &Path) -> Result<Option<Sparse>> {
    let mut f = File::open(path)?;
    let file_len = f.metadata()?.len();
    let mut first = [0u8; 52];
    f.read_exact(&mut first)
        .context("Truncated RAW archive header")?;
    let mut head = first.to_vec();
    head.resize(v2::head_len(&first)?, 0);
    f.read_exact(&mut head[52..])
        .context("Truncated archive index")?;
    let index = v2::parse(&head, file_len)?;
    let (Some(first), Some(last)) = (
        index.entries.iter().position(|e| e.samples()),
        index.entries.iter().rposition(|e| e.samples()),
    ) else {
        return Ok(None);
    };
    let mut chunk = |e: &v2::Entry| -> Result<Vec<u8>> {
        let mut payload = vec![0u8; e.stored];
        f.seek(SeekFrom::Start(e.offset))?;
        f.read_exact(&mut payload)?;
        v2::chunk_bytes(e, &payload)
    };
    let mut prefix = Vec::new();
    for e in &index.entries[..first] {
        prefix.extend_from_slice(&chunk(e)?);
    }
    let mut suffix = Vec::new();
    for e in &index.entries[last + 1..] {
        suffix.extend_from_slice(&chunk(e)?);
    }
    let suffix_start = index
        .entries
        .get(last + 1)
        .map_or(index.length, |e| e.start) as u64;
    Ok(Some(Sparse {
        path: path.to_owned(),
        length: index.length as u64,
        prefix,
        suffix_start,
        suffix,
        position: 0,
        full: None,
    }))
}

fn open_sparse(path: &Path) -> Result<Option<Sparse>> {
    let mut f = BufReader::new(File::open(path)?);
    let header = read_header(&mut f)?;
    if header.format == 2 {
        return open_sparse_v2(path);
    }
    let mut magic = [0u8; 16];
    f.read_exact(&mut magic)?;
    ensure!(
        &magic[..8] == crate::MAGIC && u64::from_le_bytes(magic[8..].try_into()?) == header.bytes,
        "Unsupported or inconsistent transport header"
    );
    let mut entries = Vec::new();
    let (mut at, mut total) = (HEADER_BYTES + 16, 0u64);
    while total < header.bytes {
        ensure!(
            entries.len() < crate::MAX_CHUNKS,
            "Too many transport chunks"
        );
        let mut h = [0u8; 13];
        f.read_exact(&mut h).context("Truncated chunk header")?;
        let n = u32::from_le_bytes(h[..4].try_into()?) as usize;
        let packed = u32::from_le_bytes(h[4..8].try_into()?) as usize;
        ensure!(
            n > 0
                && n <= crate::MAX_CHUNK
                && packed > 0
                && packed <= n
                && total + n as u64 <= header.bytes,
            "Invalid chunk lengths"
        );
        entries.push(Entry {
            start: total,
            n,
            packed,
            mode: h[8],
            width: u32::from_le_bytes(h[9..].try_into()?) as usize,
            at: at + 13,
        });
        f.seek_relative(packed as i64)?;
        at += 13 + packed as u64;
        total += n as u64;
    }
    let (Some(first), Some(last)) = (
        entries.iter().position(|e| e.mode == 8),
        entries.iter().rposition(|e| e.mode == 8),
    ) else {
        return Ok(None);
    };
    let mut chunk = |e: &Entry| -> Result<Vec<u8>> {
        // Re-frame the one chunk as a single-chunk transport stream so the
        // standard bounded decoder validates it.
        let mut stream = crate::MAGIC.to_vec();
        stream.extend_from_slice(&(e.n as u64).to_le_bytes());
        stream.extend_from_slice(&(e.n as u32).to_le_bytes());
        stream.extend_from_slice(&(e.packed as u32).to_le_bytes());
        stream.push(e.mode);
        stream.extend_from_slice(&(e.width as u32).to_le_bytes());
        let body = stream.len();
        stream.resize(body + e.packed, 0);
        f.seek(SeekFrom::Start(e.at))?;
        f.read_exact(&mut stream[body..])?;
        let mut out = Vec::with_capacity(e.n);
        decode(stream.as_slice(), &mut out, e.n as u64, true)?;
        Ok(out)
    };
    let mut prefix = Vec::new();
    for e in &entries[..first] {
        prefix.extend_from_slice(&chunk(e)?);
    }
    let mut suffix = Vec::new();
    for e in &entries[last + 1..] {
        suffix.extend_from_slice(&chunk(e)?);
    }
    let suffix_start = entries.get(last + 1).map_or(header.bytes, |e| e.start);
    Ok(Some(Sparse {
        path: path.to_owned(),
        length: header.bytes,
        prefix,
        suffix_start,
        suffix,
        position: 0,
        full: None,
    }))
}
impl Sparse {
    fn read(&mut self, out: &mut [u8]) -> io::Result<usize> {
        if self.position >= self.length || out.is_empty() {
            return Ok(0);
        }
        let p = self.position;
        let n = if let Some(full) = &self.full {
            let at = p as usize;
            let n = out.len().min(full.len() - at);
            out[..n].copy_from_slice(&full[at..at + n]);
            n
        } else if p < self.prefix.len() as u64 {
            let at = p as usize;
            let n = out.len().min(self.prefix.len() - at);
            out[..n].copy_from_slice(&self.prefix[at..at + n]);
            n
        } else if p >= self.suffix_start {
            let at = (p - self.suffix_start) as usize;
            let n = out.len().min(self.suffix.len() - at);
            out[..n].copy_from_slice(&self.suffix[at..at + n]);
            n
        } else {
            // The pixel strip: expand and verify everything, then serve it.
            self.full = Some(read_original(&self.path).map_err(io::Error::other)?);
            return self.read(out);
        };
        self.position += n as u64;
        Ok(n)
    }
}
impl Read for OriginalReader {
    fn read(&mut self, out: &mut [u8]) -> io::Result<usize> {
        match self {
            Self::File(f) => f.read(out),
            Self::Memory(b) => b.read(out),
            Self::Sparse(s) => s.read(out),
        }
    }
}
impl Seek for OriginalReader {
    fn seek(&mut self, pos: SeekFrom) -> io::Result<u64> {
        match self {
            Self::File(f) => f.seek(pos),
            Self::Memory(b) => b.seek(pos),
            Self::Sparse(s) => {
                let target = match pos {
                    SeekFrom::Start(n) => Some(n),
                    SeekFrom::End(d) => s.length.checked_add_signed(d),
                    SeekFrom::Current(d) => s.position.checked_add_signed(d),
                };
                s.position = target.ok_or_else(|| {
                    io::Error::new(io::ErrorKind::InvalidInput, "seek before start")
                })?;
                Ok(s.position)
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn exact_archive_and_refusal_controls() {
        let original = crate::tests::fixture(128, 260);
        let mut archive = Vec::new();
        pack(original.clone(), &mut archive).unwrap();
        let mut restored = Vec::new();
        unpack(archive.as_slice(), &mut restored).unwrap();
        assert_eq!(restored, original);
        assert!(archive.len() < original.len());
        // A valid stream with the wrong envelope hash must fail too.
        let mut wrong = archive.clone();
        wrong[16] ^= 1;
        assert!(unpack(wrong.as_slice(), io::sink()).is_err());
        for n in [0, 47, 63, archive.len() - 1] {
            assert!(unpack(&archive[..n], io::sink()).is_err());
        }
        let mut oversized = archive.clone();
        oversized[8..16].copy_from_slice(&(MAX_RAW + 1).to_le_bytes());
        assert!(unpack(oversized.as_slice(), io::sink()).is_err());
        let mut tail = archive.clone();
        tail.push(0);
        assert!(unpack(tail.as_slice(), io::sink()).is_err());
        let h = read_header(archive.as_slice()).unwrap();
        let mut retained = Vec::new();
        retain(
            &archive[HEADER_BYTES as usize..],
            &mut retained,
            h.bytes,
            &h.sha256,
        )
        .unwrap();
        assert_eq!(retained, archive);
    }
    #[test]
    fn sparse_reader_serves_metadata_and_verifies_before_any_strip_byte() {
        let original = crate::tests::fixture(128, 520);
        let dir = tempfile::tempdir().unwrap();
        let path = dir.path().join("frame.ARW.straw");
        let mut archive = Vec::new();
        pack(original.clone(), &mut archive).unwrap();
        std::fs::write(&path, &archive).unwrap();
        let mut r = open_original(&path).unwrap();
        assert!(matches!(r, OriginalReader::Sparse(_)));
        let mut head = [0u8; 256];
        r.read_exact(&mut head).unwrap();
        assert_eq!(head, original[..256]);
        let mut tail = Vec::new();
        r.seek(SeekFrom::End(-101)).unwrap();
        r.read_to_end(&mut tail).unwrap();
        assert_eq!(tail, original[original.len() - 101..]);
        // Reading across the strip returns exactly the original bytes.
        let mut all = Vec::new();
        r.seek(SeekFrom::Start(0)).unwrap();
        r.read_to_end(&mut all).unwrap();
        assert_eq!(all, original);
        // A corrupted strip chunk: metadata still reads, the strip refuses.
        let mut bad = archive.clone();
        let first = HEADER_BYTES as usize + 16;
        let prefix_packed = u32::from_le_bytes(bad[first + 4..first + 8].try_into().unwrap());
        let strip_payload = first + 13 + prefix_packed as usize + 13;
        assert_eq!(bad[strip_payload - 5], 8, "first strip chunk is CFA");
        bad[strip_payload + 40] ^= 0x40;
        std::fs::write(&path, &bad).unwrap();
        let mut r = open_original(&path).unwrap();
        r.read_exact(&mut head).unwrap();
        assert_eq!(head, original[..256]);
        r.seek(SeekFrom::Start(300)).unwrap();
        assert!(r.read(&mut head).is_err());
    }
}
