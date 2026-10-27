//! Shared bounded Sony metadata TIFF primitives, extracted from the owned focus reader.
//! Private to this crate. No image decoding, optical interpretation or correction.
use std::collections::BTreeSet;
use std::io::{Read, Seek, SeekFrom};

#[derive(Debug, thiserror::Error)]
pub(crate) enum SonyTiffError {
    #[error("metadata I/O: {0}")]
    Io(#[from] std::io::Error),
    #[error("unsupported metadata: {0}")]
    Unsupported(String),
    #[error("malformed metadata: {0}")]
    Malformed(String),
}

type Result<T> = std::result::Result<T, SonyTiffError>;
const MAX_ENTRIES: usize = 4096;
const READ_BUDGET: usize = 128 * 1024;

fn malformed(message: impl Into<String>) -> SonyTiffError {
    SonyTiffError::Malformed(message.into())
}
fn unsupported(message: impl Into<String>) -> SonyTiffError {
    SonyTiffError::Unsupported(message.into())
}

pub(crate) fn u16le(bytes: &[u8], offset: usize) -> u16 {
    u16::from_le_bytes([bytes[offset], bytes[offset + 1]])
}

pub(crate) fn u32le(bytes: &[u8], offset: usize) -> u32 {
    u32::from_le_bytes([
        bytes[offset],
        bytes[offset + 1],
        bytes[offset + 2],
        bytes[offset + 3],
    ])
}

#[derive(Clone, Copy)]
pub(crate) struct Entry {
    pub(crate) tag: u16,
    pub(crate) kind: u16,
    pub(crate) count: u32,
    pub(crate) value: u32,
    pub(crate) inline_offset: u64,
}

pub(crate) struct Directory {
    entries: Vec<Entry>,
}

impl Directory {
    pub(crate) fn get(&self, tag: u16) -> Option<Entry> {
        self.entries.iter().find(|e| e.tag == tag).copied()
    }

    pub(crate) fn required(&self, tag: u16) -> Result<Entry> {
        self.get(tag)
            .ok_or_else(|| unsupported(format!("required TIFF tag 0x{tag:04x} is absent")))
    }
}

pub(crate) struct Reader<'a, R> {
    inner: &'a mut R,
    size: u64,
    remaining: usize,
    visited: BTreeSet<u64>,
    accessed: Vec<(u64, u64)>,
    protected: Vec<(u64, u64)>,
    address_limit: Option<u64>,
}

impl<'a, R: Read + Seek> Reader<'a, R> {
    pub(crate) fn new(inner: &'a mut R) -> Result<Self> {
        let size = inner.seek(SeekFrom::End(0))?;
        Ok(Self {
            inner,
            size,
            remaining: READ_BUDGET,
            visited: BTreeSet::new(),
            accessed: Vec::new(),
            protected: Vec::new(),
            address_limit: None,
        })
    }

    pub(crate) fn range(&self, offset: u64, len: u64) -> Result<()> {
        if offset.checked_add(len).is_none_or(|end| end > self.size) {
            return Err(malformed("metadata range extends outside the file"));
        }
        Ok(())
    }

    pub(crate) fn bytes(&mut self, offset: u64, len: usize) -> Result<Vec<u8>> {
        self.range(offset, len as u64)?;
        let end = offset + len as u64; // checked by range
        if self.address_limit.is_some_and(|limit| end > limit) {
            return Err(malformed("metadata address limit exceeded"));
        }
        if self.protected.iter().any(|&(a, b)| offset < b && end > a) {
            return Err(malformed("metadata overlaps declared image payload"));
        }
        self.remaining = self
            .remaining
            .checked_sub(len)
            .ok_or_else(|| malformed("metadata read budget exceeded"))?;
        let mut bytes = vec![0; len];
        self.inner.seek(SeekFrom::Start(offset))?;
        self.inner.read_exact(&mut bytes).map_err(|error| {
            if error.kind() == std::io::ErrorKind::UnexpectedEof {
                malformed("metadata was truncated during reading")
            } else {
                SonyTiffError::Io(error)
            }
        })?;
        self.accessed.push((offset, end));
        Ok(bytes)
    }

    /// Nonrecursive walk of the four relevant IFDs. Other directory links are not followed.
    pub(crate) fn directory(
        &mut self,
        offset: u64,
        enclosing: Option<(u64, u64)>,
    ) -> Result<Directory> {
        if !self.visited.insert(offset) {
            return Err(malformed("cyclic or aliased TIFF directory"));
        }
        if self.visited.len() > 4 {
            return Err(malformed("too many metadata directories"));
        }
        let count = u16le(&self.bytes(offset, 2)?, 0) as usize;
        if count > MAX_ENTRIES {
            return Err(malformed("excessive TIFF directory entry count"));
        }
        let len = 2 + count * 12 + 4;
        if let Some((start, length)) = enclosing {
            let end = start
                .checked_add(length)
                .ok_or_else(|| malformed("maker-note range overflow"))?;
            if offset < start || offset.checked_add(len as u64).is_none_or(|n| n > end) {
                return Err(malformed("directory exceeds its maker-note value"));
            }
        }
        let bytes = self.bytes(offset + 2, len - 2)?;
        let mut tags = BTreeSet::new();
        let mut entries = Vec::with_capacity(count);
        for i in 0..count {
            let at = i * 12;
            let tag = u16le(&bytes, at);
            if !tags.insert(tag) {
                return Err(malformed(format!("duplicate TIFF tag 0x{tag:04x}")));
            }
            entries.push(Entry {
                tag,
                kind: u16le(&bytes, at + 2),
                count: u32le(&bytes, at + 4),
                value: u32le(&bytes, at + 8),
                inline_offset: offset + 2 + at as u64 + 8,
            });
        }
        Ok(Directory { entries })
    }

    pub(crate) fn typed_bytes(&mut self, entry: Entry, kind: u16, count: u32) -> Result<Vec<u8>> {
        if entry.kind != kind || entry.count != count {
            return Err(malformed(format!(
                "tag 0x{:04x} has unexpected type/count ({}/{})",
                entry.tag, entry.kind, entry.count
            )));
        }
        let width = match kind {
            1 | 2 | 6 | 7 => 1,
            3 | 8 => 2,
            4 => 4,
            5 => 8,
            _ => return Err(unsupported("unsupported internal TIFF field type")),
        };
        let len = (count as usize)
            .checked_mul(width)
            .ok_or_else(|| malformed("TIFF value length overflow"))?;
        let offset = if len <= 4 {
            entry.inline_offset
        } else {
            entry.value as u64
        };
        self.bytes(offset, len)
    }

    pub(crate) fn text(&mut self, entry: Entry) -> Result<String> {
        if entry.kind != 2 || entry.count == 0 || entry.count > 256 {
            return Err(malformed("invalid camera identity string"));
        }
        let mut bytes = self.typed_bytes(entry, 2, entry.count)?;
        while bytes.last() == Some(&0) {
            bytes.pop();
        }
        if !bytes.is_ascii() || bytes.contains(&0) {
            return Err(malformed("non-ASCII or embedded-NUL camera identity"));
        }
        String::from_utf8(bytes).map_err(|_| malformed("invalid camera identity"))
    }

    pub(crate) fn pointer(entry: Entry) -> Result<u64> {
        if entry.kind != 4 || entry.count != 1 {
            return Err(malformed("directory pointer must be one TIFF LONG"));
        }
        Ok(entry.value as u64)
    }

    pub(crate) fn pair(&mut self, entry: Entry) -> Result<[u16; 2]> {
        let raw = match entry.kind {
            3 => {
                let bytes = self.typed_bytes(entry, 3, 2)?;
                [u16le(&bytes, 0) as u32, u16le(&bytes, 2) as u32]
            }
            4 => {
                let bytes = self.typed_bytes(entry, 4, 2)?;
                [u32le(&bytes, 0), u32le(&bytes, 4)]
            }
            _ => {
                return Err(malformed(
                    "geometry field must contain SHORT or LONG values",
                ));
            }
        };
        Ok([
            u16::try_from(raw[0]).map_err(|_| unsupported("geometry exceeds hidden u16 layout"))?,
            u16::try_from(raw[1]).map_err(|_| unsupported("geometry exceeds hidden u16 layout"))?,
        ])
    }

    /// Optical headers are additionally limited in address; focus layout policy is unchanged.
    pub(crate) fn limit_address(&mut self, limit: u64) {
        self.address_limit = Some(limit);
    }

    pub(crate) fn file_bytes(&self) -> u64 {
        self.size
    }

    pub(crate) fn bytes_read(&self) -> usize {
        READ_BUDGET - self.remaining
    }

    /// Protect declared strips/tiles and reject earlier metadata graph overlap.
    pub(crate) fn protect(&mut self, ranges: Vec<(u64, u64)>) -> Result<()> {
        for &(start, end) in &ranges {
            if start >= end {
                return Err(malformed("empty or reversed image payload range"));
            }
            self.range(start, end - start)?;
            if self.accessed.iter().any(|&(a, b)| a < end && b > start) {
                return Err(malformed(
                    "metadata directory overlaps declared image payload",
                ));
            }
        }
        self.protected = ranges;
        Ok(())
    }
}
