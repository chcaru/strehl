//! Export metadata: TIFF tags, an XMP packet (dc:creator, dc:rights,
//! dc:description) for PNG, JPEG and TIFF, and a TIFF-structured Exif block for
//! JPEG and AVIF. Nothing is written unless the export asks for it, so an
//! export without metadata keeps its earlier bytes.
//!
//! AVIF: `avif-serialize` 0.8.9 can add an Exif item (`Aviffy::set_exif`) but
//! has no XMP or other MIME item, so AVIF carries the Exif block only.
use anyhow::{Result, ensure};
use quick_xml::{
    Writer,
    events::{BytesEnd, BytesPI, BytesStart, BytesText, Event},
};
use serde::{Deserialize, Serialize};
use std::io::{self, Write};

const MAX_ARTIST: usize = 256;
const MAX_COPYRIGHT: usize = 512;
const MAX_DESCRIPTION: usize = 2048;
/// Lines Strehl's own TIFF reader interprets; a description may not mimic them.
const RESERVED_PREFIXES: [&str; 3] = ["DisplayBaseline: ", "BakedSourceRecipe: ", "Linear sRGB"];

/// Text written into the file. Empty fields are omitted.
#[derive(Debug, Clone, Default, PartialEq, Eq, Serialize, Deserialize)]
#[serde(default, deny_unknown_fields)]
pub struct ExportMetadata {
    #[serde(skip_serializing_if = "String::is_empty")]
    pub artist: String,
    #[serde(skip_serializing_if = "String::is_empty")]
    pub copyright: String,
    #[serde(skip_serializing_if = "String::is_empty")]
    pub description: String,
}

impl ExportMetadata {
    pub fn is_empty(&self) -> bool {
        self.artist.is_empty() && self.copyright.is_empty() && self.description.is_empty()
    }

    pub fn validate(&self) -> Result<()> {
        for (name, text, max, newlines) in [
            ("artist", &self.artist, MAX_ARTIST, false),
            ("copyright", &self.copyright, MAX_COPYRIGHT, false),
            ("description", &self.description, MAX_DESCRIPTION, true),
        ] {
            ensure!(
                text.len() <= max,
                "the {name} is limited to {max} UTF-8 bytes"
            );
            ensure!(
                !text
                    .chars()
                    .any(|c| c.is_control() && !(newlines && c == '\n')),
                "the {name} cannot contain control characters"
            );
        }
        let flat = self.description.replace('\n', " ");
        ensure!(
            !RESERVED_PREFIXES.iter().any(|p| flat.starts_with(p))
                && !flat.contains("camera-native"),
            "this description uses wording Strehl reserves for its masters"
        );
        Ok(())
    }
}

/// A civil date and time for the file's DateTime fields, supplied by the
/// caller (the desktop knows the local time zone; this crate does not).
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct ExportDateTime {
    pub year: u16,
    pub month: u8,
    pub day: u8,
    pub hour: u8,
    pub minute: u8,
    pub second: u8,
    /// Offset from UTC in minutes; written to XMP, not representable in TIFF.
    pub utc_offset_minutes: i16,
}

impl ExportDateTime {
    /// From Unix seconds and the zone offset in effect at that instant.
    pub fn from_unix_seconds(seconds: i64, utc_offset_minutes: i16) -> Self {
        let local = seconds + i64::from(utc_offset_minutes) * 60;
        let days = local.div_euclid(86_400);
        let rem = local.rem_euclid(86_400);
        // Civil-from-days (proleptic Gregorian), H. Hinnant's algorithm.
        let z = days + 719_468;
        let era = z.div_euclid(146_097);
        let doe = z.rem_euclid(146_097);
        let yoe = (doe - doe / 1460 + doe / 36_524 - doe / 146_096) / 365;
        let doy = doe - (365 * yoe + yoe / 4 - yoe / 100);
        let mp = (5 * doy + 2) / 153;
        let day = doy - (153 * mp + 2) / 5 + 1;
        let month = if mp < 10 { mp + 3 } else { mp - 9 };
        let year = yoe + era * 400 + i64::from(month <= 2);
        Self {
            year: year.clamp(0, 9999) as u16,
            month: month as u8,
            day: day as u8,
            hour: (rem / 3600) as u8,
            minute: (rem % 3600 / 60) as u8,
            second: (rem % 60) as u8,
            utc_offset_minutes,
        }
    }

    pub fn now_utc() -> Self {
        let seconds = std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .map_or(0, |d| d.as_secs() as i64);
        Self::from_unix_seconds(seconds, 0)
    }

    pub fn validate(&self) -> Result<()> {
        ensure!(
            self.year <= 9999
                && (1..=12).contains(&self.month)
                && (1..=31).contains(&self.day)
                && self.hour < 24
                && self.minute < 60
                && self.second < 61
                && self.utc_offset_minutes.abs() <= 18 * 60,
            "invalid export date and time"
        );
        Ok(())
    }

    /// TIFF/Exif `YYYY:MM:DD HH:MM:SS`, in the stated local time.
    pub fn tiff(&self) -> String {
        format!(
            "{:04}:{:02}:{:02} {:02}:{:02}:{:02}",
            self.year, self.month, self.day, self.hour, self.minute, self.second
        )
    }

    /// XMP / ISO 8601 with its offset.
    pub fn xmp(&self) -> String {
        let offset = if self.utc_offset_minutes == 0 {
            "Z".to_owned()
        } else {
            let m = self.utc_offset_minutes.unsigned_abs();
            format!(
                "{}{:02}:{:02}",
                if self.utc_offset_minutes < 0 {
                    '-'
                } else {
                    '+'
                },
                m / 60,
                m % 60
            )
        };
        format!(
            "{:04}-{:02}-{:02}T{:02}:{:02}:{:02}{offset}",
            self.year, self.month, self.day, self.hour, self.minute, self.second
        )
    }
}

/// Seven-bit text for TIFF and Exif ASCII fields. The XMP packet keeps the
/// exact Unicode text; this is the fallback for readers of the ASCII tags.
pub(crate) fn ascii_text(text: &str) -> String {
    let mut out = String::with_capacity(text.len());
    for c in text.chars() {
        match c {
            c if c.is_ascii() && c != '\0' => out.push(c),
            '©' => out.push_str("(c)"),
            '®' => out.push_str("(R)"),
            'µ' | 'μ' => out.push('u'),
            '–' | '—' => out.push('-'),
            '‘' | '’' => out.push('\''),
            '“' | '”' => out.push('"'),
            _ => out.push('?'),
        }
    }
    out
}

/// JSON with every non-ASCII character escaped, so it fits a TIFF ASCII tag.
/// Identical to `serde_json::to_string` for ASCII-only content.
pub(crate) fn json_ascii<T: Serialize>(value: &T) -> Result<String> {
    let text = serde_json::to_string(value)?;
    if text.is_ascii() {
        return Ok(text);
    }
    let mut out = String::with_capacity(text.len() + 16);
    for c in text.chars() {
        if c.is_ascii() {
            out.push(c);
        } else {
            let mut units = [0u16; 2];
            for unit in c.encode_utf16(&mut units) {
                out.push_str(&format!("\\u{unit:04x}"));
            }
        }
    }
    Ok(out)
}

/// The XMP packet, or `None` when there is nothing to say.
pub(crate) fn xmp_packet(
    meta: &ExportMetadata,
    date: Option<&ExportDateTime>,
) -> Result<Option<Vec<u8>>> {
    if meta.is_empty() && date.is_none() {
        return Ok(None);
    }
    let mut w = Writer::new(Vec::new());
    w.write_event(Event::PI(BytesPI::new(
        "xpacket begin=\"\u{feff}\" id=\"W5M0MpCehiHzreSzNTczkc9d\"",
    )))?;
    w.write_event(Event::Start(
        BytesStart::new("x:xmpmeta").with_attributes([("xmlns:x", "adobe:ns:meta/")]),
    ))?;
    w.write_event(Event::Start(BytesStart::new("rdf:RDF").with_attributes([
        ("xmlns:rdf", "http://www.w3.org/1999/02/22-rdf-syntax-ns#"),
    ])))?;
    w.write_event(Event::Start(
        BytesStart::new("rdf:Description").with_attributes([
            ("rdf:about", ""),
            ("xmlns:dc", "http://purl.org/dc/elements/1.1/"),
            ("xmlns:xmp", "http://ns.adobe.com/xap/1.0/"),
        ]),
    ))?;
    let text = |w: &mut Writer<Vec<u8>>, name: &str, value: &str| -> io::Result<()> {
        w.write_event(Event::Start(BytesStart::new(name)))?;
        w.write_event(Event::Text(BytesText::new(value)))?;
        w.write_event(Event::End(BytesEnd::new(name)))
    };
    let container =
        |w: &mut Writer<Vec<u8>>, name: &str, kind: &str, value: &str| -> io::Result<()> {
            w.write_event(Event::Start(BytesStart::new(name)))?;
            w.write_event(Event::Start(BytesStart::new(kind)))?;
            let item = if kind == "rdf:Alt" {
                BytesStart::new("rdf:li").with_attributes([("xml:lang", "x-default")])
            } else {
                BytesStart::new("rdf:li")
            };
            w.write_event(Event::Start(item))?;
            w.write_event(Event::Text(BytesText::new(value)))?;
            w.write_event(Event::End(BytesEnd::new("rdf:li")))?;
            w.write_event(Event::End(BytesEnd::new(kind)))?;
            w.write_event(Event::End(BytesEnd::new(name)))
        };
    if !meta.artist.is_empty() {
        container(&mut w, "dc:creator", "rdf:Seq", &meta.artist)?;
    }
    if !meta.copyright.is_empty() {
        container(&mut w, "dc:rights", "rdf:Alt", &meta.copyright)?;
    }
    if !meta.description.is_empty() {
        container(&mut w, "dc:description", "rdf:Alt", &meta.description)?;
    }
    text(&mut w, "xmp:CreatorTool", "Strehl")?;
    if let Some(date) = date {
        text(&mut w, "xmp:CreateDate", &date.xmp())?;
        text(&mut w, "xmp:ModifyDate", &date.xmp())?;
    }
    w.write_event(Event::End(BytesEnd::new("rdf:Description")))?;
    w.write_event(Event::End(BytesEnd::new("rdf:RDF")))?;
    w.write_event(Event::End(BytesEnd::new("x:xmpmeta")))?;
    w.write_event(Event::PI(BytesPI::new("xpacket end=\"w\"")))?;
    Ok(Some(w.into_inner()))
}

/// A little-endian TIFF block holding IFD0 ASCII tags, the form JPEG APP1 and
/// the AVIF Exif item take. `None` when there is nothing to say.
pub(crate) fn exif_block(meta: &ExportMetadata, date: Option<&ExportDateTime>) -> Option<Vec<u8>> {
    let mut entries: Vec<(u16, String)> = Vec::new();
    let mut push = |tag: u16, text: &str| {
        if !text.is_empty() {
            entries.push((tag, ascii_text(text)));
        }
    };
    push(270, &meta.description.replace('\n', " "));
    push(305, "Strehl");
    if let Some(date) = date {
        push(306, &date.tiff());
    }
    push(315, &meta.artist);
    push(33_432, &meta.copyright);
    if meta.is_empty() && date.is_none() {
        return None;
    }
    entries.sort_by_key(|(tag, _)| *tag);
    let mut out = Vec::new();
    out.extend_from_slice(b"II");
    out.extend_from_slice(&42u16.to_le_bytes());
    out.extend_from_slice(&8u32.to_le_bytes());
    out.extend_from_slice(&(entries.len() as u16).to_le_bytes());
    let mut data_at = 8 + 2 + entries.len() * 12 + 4;
    let mut data = Vec::new();
    for (tag, text) in &entries {
        let mut bytes = text.as_bytes().to_vec();
        bytes.push(0);
        out.extend_from_slice(&tag.to_le_bytes());
        out.extend_from_slice(&2u16.to_le_bytes()); // ASCII
        out.extend_from_slice(&(bytes.len() as u32).to_le_bytes());
        if bytes.len() <= 4 {
            let mut inline = [0u8; 4];
            inline[..bytes.len()].copy_from_slice(&bytes);
            out.extend_from_slice(&inline);
        } else {
            out.extend_from_slice(&(data_at as u32).to_le_bytes());
            data_at += bytes.len() + bytes.len() % 2;
            data.extend_from_slice(&bytes);
            if bytes.len() % 2 == 1 {
                data.push(0);
            }
        }
    }
    out.extend_from_slice(&0u32.to_le_bytes());
    out.extend_from_slice(&data);
    Some(out)
}

fn crc32(bytes: &[u8]) -> u32 {
    let mut crc = 0xffff_ffffu32;
    for &b in bytes {
        crc ^= u32::from(b);
        for _ in 0..8 {
            crc = if crc & 1 != 0 {
                (crc >> 1) ^ 0xedb8_8320
            } else {
                crc >> 1
            };
        }
    }
    !crc
}

/// A PNG `iTXt` chunk carrying the XMP packet under the registered keyword.
pub(crate) fn png_xmp_chunk(packet: &[u8]) -> Vec<u8> {
    let mut body = Vec::with_capacity(packet.len() + 32);
    body.extend_from_slice(b"iTXt");
    body.extend_from_slice(b"XML:com.adobe.xmp\0");
    body.extend_from_slice(&[0, 0]); // uncompressed, method 0
    body.extend_from_slice(b"\0\0"); // no language, no translated keyword
    body.extend_from_slice(packet);
    let mut chunk = Vec::with_capacity(body.len() + 8);
    chunk.extend_from_slice(&((body.len() - 4) as u32).to_be_bytes());
    chunk.extend_from_slice(&body);
    chunk.extend_from_slice(&crc32(&body).to_be_bytes());
    chunk
}

enum PngState {
    Signature(usize),
    Header([u8; 8], usize),
    Body(u64),
    Done,
}

/// Inserts one chunk before the first `IDAT` of a PNG stream, passing every
/// other byte through unchanged.
pub(crate) struct PngChunkInserter<W> {
    inner: W,
    chunk: Option<Vec<u8>>,
    state: PngState,
}

impl<W: Write> PngChunkInserter<W> {
    pub(crate) fn new(inner: W, chunk: Vec<u8>) -> Self {
        Self {
            inner,
            chunk: Some(chunk),
            state: PngState::Signature(8),
        }
    }

    pub(crate) fn finish(mut self) -> Result<W> {
        ensure!(
            self.chunk.is_none(),
            "PNG stream ended before its image data"
        );
        self.inner.flush()?;
        Ok(self.inner)
    }
}

impl<W: Write> Write for PngChunkInserter<W> {
    fn write(&mut self, buf: &[u8]) -> io::Result<usize> {
        let mut rest = buf;
        while !rest.is_empty() {
            match &mut self.state {
                PngState::Done => {
                    self.inner.write_all(rest)?;
                    rest = &[];
                }
                PngState::Signature(left) => {
                    let n = (*left).min(rest.len());
                    self.inner.write_all(&rest[..n])?;
                    *left -= n;
                    rest = &rest[n..];
                    if *left == 0 {
                        self.state = PngState::Header([0; 8], 0);
                    }
                }
                PngState::Header(header, filled) => {
                    let n = (8 - *filled).min(rest.len());
                    header[*filled..*filled + n].copy_from_slice(&rest[..n]);
                    *filled += n;
                    rest = &rest[n..];
                    if *filled == 8 {
                        let header = *header;
                        if &header[4..8] == b"IDAT"
                            && let Some(chunk) = self.chunk.take()
                        {
                            self.inner.write_all(&chunk)?;
                        }
                        self.inner.write_all(&header)?;
                        let length =
                            u32::from_be_bytes([header[0], header[1], header[2], header[3]]);
                        // Chunk data and its CRC; after the insertion all passes through.
                        self.state = PngState::Body(u64::from(length) + 4);
                    }
                }
                PngState::Body(left) => {
                    let n = (*left).min(rest.len() as u64) as usize;
                    self.inner.write_all(&rest[..n])?;
                    *left -= n as u64;
                    rest = &rest[n..];
                    if *left == 0 {
                        self.state = if self.chunk.is_none() {
                            PngState::Done
                        } else {
                            PngState::Header([0; 8], 0)
                        };
                    }
                }
            }
        }
        Ok(buf.len())
    }

    fn flush(&mut self) -> io::Result<()> {
        self.inner.flush()
    }
}

const XMP_APP1: &[u8] = b"http://ns.adobe.com/xap/1.0/\0";

/// A JPEG APP1 segment carrying the XMP packet.
pub(crate) fn jpeg_xmp_segment(packet: &[u8]) -> Result<Vec<u8>> {
    let length = 2 + XMP_APP1.len() + packet.len();
    ensure!(
        length <= 0xffff,
        "the XMP metadata is too large for a JPEG segment"
    );
    let mut segment = vec![0xff, 0xe1];
    segment.extend_from_slice(&(length as u16).to_be_bytes());
    segment.extend_from_slice(XMP_APP1);
    segment.extend_from_slice(packet);
    Ok(segment)
}

enum JpegState {
    Soi(usize),
    Header([u8; 4], usize),
    Body(usize),
    Done,
}

/// Inserts one segment after the leading APP0/APP1 segments (JFIF and Exif)
/// of a JPEG stream, passing every other byte through unchanged.
pub(crate) struct JpegSegmentInserter<W> {
    inner: W,
    segment: Option<Vec<u8>>,
    state: JpegState,
}

impl<W: Write> JpegSegmentInserter<W> {
    pub(crate) fn new(inner: W, segment: Vec<u8>) -> Self {
        Self {
            inner,
            segment: Some(segment),
            state: JpegState::Soi(2),
        }
    }

    pub(crate) fn finish(mut self) -> Result<W> {
        ensure!(
            self.segment.is_none(),
            "JPEG stream ended before its first table"
        );
        self.inner.flush()?;
        Ok(self.inner)
    }
}

impl<W: Write> Write for JpegSegmentInserter<W> {
    fn write(&mut self, buf: &[u8]) -> io::Result<usize> {
        let mut rest = buf;
        while !rest.is_empty() {
            match &mut self.state {
                JpegState::Done => {
                    self.inner.write_all(rest)?;
                    rest = &[];
                }
                JpegState::Soi(left) => {
                    let n = (*left).min(rest.len());
                    self.inner.write_all(&rest[..n])?;
                    *left -= n;
                    rest = &rest[n..];
                    if *left == 0 {
                        self.state = JpegState::Header([0; 4], 0);
                    }
                }
                JpegState::Header(header, filled) => {
                    let n = (4 - *filled).min(rest.len());
                    header[*filled..*filled + n].copy_from_slice(&rest[..n]);
                    *filled += n;
                    rest = &rest[n..];
                    if *filled == 4 {
                        let header = *header;
                        if header[0] == 0xff && matches!(header[1], 0xe0 | 0xe1) {
                            self.inner.write_all(&header)?;
                            let length = usize::from(u16::from_be_bytes([header[2], header[3]]));
                            self.state = JpegState::Body(length.saturating_sub(2));
                        } else {
                            if let Some(segment) = self.segment.take() {
                                self.inner.write_all(&segment)?;
                            }
                            self.inner.write_all(&header)?;
                            self.state = JpegState::Done;
                        }
                    }
                }
                JpegState::Body(left) => {
                    let n = (*left).min(rest.len());
                    self.inner.write_all(&rest[..n])?;
                    *left -= n;
                    rest = &rest[n..];
                    if *left == 0 {
                        self.state = JpegState::Header([0; 4], 0);
                    }
                }
            }
        }
        Ok(buf.len())
    }

    fn flush(&mut self) -> io::Result<()> {
        self.inner.flush()
    }
}

#[cfg(test)]
#[path = "metadata-tests.rs"]
mod tests;
