//! STRHARC1: 48-byte header (magic, u64 LE original size, binary SHA-256),
//! followed by an unchanged STRHRAW1 transport stream. No lossy conversion.
//! Every complete read verifies the original bytes, including all metadata.
use crate::{Decoded, Encoder, MAX_RAW, WORKERS, decode};
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
    ensure!(&h[..8] == MAGIC, "Unsupported RAW archive version");
    let bytes = u64::from_le_bytes(h[8..16].try_into()?);
    ensure!(bytes > 0 && bytes <= MAX_RAW, "Invalid archive RAW length");
    Ok(Header {
        bytes,
        sha256: h[16..].iter().map(|b| format!("{b:02x}")).collect(),
    })
}

pub fn unpack(mut input: impl Read, output: impl Write) -> Result<Decoded> {
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

pub fn read_original(path: &Path) -> Result<Vec<u8>> {
    let mut input = BufReader::new(File::open(path)?);
    let header = read_header(&mut input)?;
    let mut bytes = Vec::with_capacity(header.bytes as usize);
    let decoded = decode(input, &mut bytes, header.bytes, true)?;
    ensure!(
        decoded.sha256 == header.sha256,
        "RAW archive checksum mismatch"
    );
    Ok(bytes)
}

/// Seekable original bytes for TIFF metadata readers. Plain files still seek
/// directly on disk; archived files are verified and expanded only in memory.
pub enum OriginalReader {
    File(File),
    Memory(io::Cursor<Vec<u8>>),
}
pub fn open_original(path: &Path) -> io::Result<OriginalReader> {
    if is_archive(path) {
        read_original(path)
            .map(|b| OriginalReader::Memory(io::Cursor::new(b)))
            .map_err(io::Error::other)
    } else {
        File::open(path).map(OriginalReader::File)
    }
}
impl Read for OriginalReader {
    fn read(&mut self, out: &mut [u8]) -> io::Result<usize> {
        match self {
            Self::File(f) => f.read(out),
            Self::Memory(b) => b.read(out),
        }
    }
}
impl Seek for OriginalReader {
    fn seek(&mut self, pos: SeekFrom) -> io::Result<u64> {
        match self {
            Self::File(f) => f.seek(pos),
            Self::Memory(b) => b.seek(pos),
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
}
