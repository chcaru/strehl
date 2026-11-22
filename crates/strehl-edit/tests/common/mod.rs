//! Reading exported files back, container by container, without the writer's
//! code: PNG chunks, JPEG segments, TIFF IFDs and the AVIF (ISOBMFF) boxes
//! the export writes. Shared by `export-stamp.rs` and `export-freeze.rs`.
#![allow(dead_code)]

/// Every PNG chunk after the signature: (type, data).
pub fn png_chunks(bytes: &[u8]) -> Vec<([u8; 4], Vec<u8>)> {
    assert_eq!(&bytes[..8], b"\x89PNG\r\n\x1a\n", "PNG signature");
    let mut at = 8;
    let mut out = Vec::new();
    while at < bytes.len() {
        let n = u32::from_be_bytes(bytes[at..at + 4].try_into().unwrap()) as usize;
        let kind: [u8; 4] = bytes[at + 4..at + 8].try_into().unwrap();
        out.push((kind, bytes[at + 8..at + 8 + n].to_vec()));
        at += 12 + n;
    }
    out
}

/// The JPEG marker segments before the scan: (marker, payload).
pub fn jpeg_segments(bytes: &[u8]) -> Vec<(u8, Vec<u8>)> {
    assert_eq!(&bytes[..2], [0xff, 0xd8], "JPEG SOI");
    let mut at = 2;
    let mut out = Vec::new();
    loop {
        assert_eq!(bytes[at], 0xff, "marker at {at}");
        let marker = bytes[at + 1];
        let n = u16::from_be_bytes([bytes[at + 2], bytes[at + 3]]) as usize;
        out.push((marker, bytes[at + 4..at + 2 + n].to_vec()));
        at += 2 + n;
        if marker == 0xda {
            return out;
        }
    }
}

/// The ASCII entries of a little-endian TIFF block's first IFD.
pub fn ifd_ascii(block: &[u8]) -> Vec<(u16, String)> {
    assert_eq!(&block[..4], b"II*\0", "little-endian TIFF header");
    let at = u32::from_le_bytes(block[4..8].try_into().unwrap()) as usize;
    let count = u16::from_le_bytes([block[at], block[at + 1]]) as usize;
    (0..count)
        .map(|i| {
            let e = &block[at + 2 + i * 12..at + 14 + i * 12];
            let tag = u16::from_le_bytes([e[0], e[1]]);
            assert_eq!(u16::from_le_bytes([e[2], e[3]]), 2, "ASCII type");
            let n = u32::from_le_bytes(e[4..8].try_into().unwrap()) as usize;
            let bytes = if n <= 4 {
                e[8..8 + n].to_vec()
            } else {
                let off = u32::from_le_bytes(e[8..12].try_into().unwrap()) as usize;
                block[off..off + n].to_vec()
            };
            (tag, String::from_utf8(bytes[..n - 1].to_vec()).unwrap())
        })
        .collect()
}

/// One ISOBMFF box: type and payload (after the 8-byte header).
fn boxes(bytes: &[u8]) -> Vec<([u8; 4], &[u8])> {
    let mut at = 0;
    let mut out = Vec::new();
    while at + 8 <= bytes.len() {
        let n = u32::from_be_bytes(bytes[at..at + 4].try_into().unwrap()) as usize;
        assert!(n >= 8, "box sizes 0 and 1 are not written by the exporter");
        let kind: [u8; 4] = bytes[at + 4..at + 8].try_into().unwrap();
        out.push((kind, &bytes[at + 8..at + n]));
        at += n;
    }
    assert_eq!(at, bytes.len(), "boxes fill their parent");
    out
}

fn child<'a>(bytes: &'a [u8], kind: &[u8; 4]) -> &'a [u8] {
    boxes(bytes)
        .into_iter()
        .find(|(k, _)| k == kind)
        .unwrap_or_else(|| panic!("no {} box", String::from_utf8_lossy(kind)))
        .1
}

fn uint(bytes: &[u8], at: &mut usize, size: usize) -> u64 {
    let mut v = 0u64;
    for _ in 0..size {
        v = (v << 8) | u64::from(bytes[*at]);
        *at += 1;
    }
    v
}

/// What an exported AVIF holds: its items (id, type, bytes, read through
/// `iloc` from the file) and the colour properties of the image.
#[derive(Debug)]
pub struct Avif {
    pub items: Vec<(u16, [u8; 4], Vec<u8>)>,
    pub size: [u32; 2],
    /// `nclx` primaries, transfer, matrix and full range.
    pub colr: Option<(u16, u16, u16, bool)>,
    /// Content light level: max and average.
    pub clli: Option<(u16, u16)>,
}

impl Avif {
    pub fn item(&self, kind: &[u8; 4]) -> Option<&[u8]> {
        self.items
            .iter()
            .find(|(_, k, _)| k == kind)
            .map(|(_, _, b)| b.as_slice())
    }

    /// The Exif item's TIFF block (after its 4-byte header offset).
    pub fn exif_tiff(&self) -> Option<&[u8]> {
        let item = self.item(b"Exif")?;
        let skip = u32::from_be_bytes(item[..4].try_into().unwrap()) as usize;
        Some(&item[4 + skip..])
    }
}

pub fn read_avif(file: &[u8]) -> Avif {
    let top = boxes(file);
    assert_eq!(top[0].0, *b"ftyp");
    let meta = &child(file, b"meta")[4..]; // full box
    // iinf: entry count, then infe boxes (version 2: id, protection, type).
    let iinf = &child(meta, b"iinf")[4..];
    let version = child(meta, b"iinf")[0];
    let skip = if version == 0 { 2 } else { 4 };
    let mut kinds = Vec::new();
    for (kind, infe) in boxes(&iinf[skip..]) {
        assert_eq!(&kind, b"infe");
        assert!(infe[0] >= 2, "infe version 2 or 3");
        let id = u16::from_be_bytes([infe[4], infe[5]]);
        let item_type: [u8; 4] = infe[8..12].try_into().unwrap();
        kinds.push((id, item_type));
    }
    // iloc: every extent read from the file, construction method 0.
    let iloc = child(meta, b"iloc");
    let version = iloc[0];
    let mut at = 4;
    let sizes = (
        iloc[at] >> 4,
        iloc[at] & 15,
        iloc[at + 1] >> 4,
        iloc[at + 1] & 15,
    );
    at += 2;
    let (offset_size, length_size, base_size, index_size) = (
        sizes.0 as usize,
        sizes.1 as usize,
        sizes.2 as usize,
        if version > 0 { sizes.3 as usize } else { 0 },
    );
    let count = if version < 2 {
        uint(iloc, &mut at, 2)
    } else {
        uint(iloc, &mut at, 4)
    };
    let mut items = Vec::new();
    for _ in 0..count {
        let id = if version < 2 {
            uint(iloc, &mut at, 2)
        } else {
            uint(iloc, &mut at, 4)
        } as u16;
        if version > 0 {
            let method = uint(iloc, &mut at, 2) & 15;
            assert_eq!(method, 0, "file offsets");
        }
        let _reference = uint(iloc, &mut at, 2);
        let base = uint(iloc, &mut at, base_size) as usize;
        let extents = uint(iloc, &mut at, 2);
        let mut data = Vec::new();
        for _ in 0..extents {
            uint(iloc, &mut at, index_size);
            let offset = uint(iloc, &mut at, offset_size) as usize;
            let length = uint(iloc, &mut at, length_size) as usize;
            data.extend_from_slice(&file[base + offset..base + offset + length]);
        }
        let kind = kinds
            .iter()
            .find(|(i, _)| *i == id)
            .map(|(_, k)| *k)
            .expect("every located item is named");
        items.push((id, kind, data));
    }
    let ipco = child(child(meta, b"iprp"), b"ipco");
    let mut size = [0, 0];
    let mut colr = None;
    let mut clli = None;
    for (kind, data) in boxes(ipco) {
        match &kind {
            b"ispe" => {
                size = [
                    u32::from_be_bytes(data[4..8].try_into().unwrap()),
                    u32::from_be_bytes(data[8..12].try_into().unwrap()),
                ];
            }
            b"colr" if &data[..4] == b"nclx" => {
                colr = Some((
                    u16::from_be_bytes([data[4], data[5]]),
                    u16::from_be_bytes([data[6], data[7]]),
                    u16::from_be_bytes([data[8], data[9]]),
                    data[10] & 0x80 != 0,
                ));
            }
            b"clli" => {
                clli = Some((
                    u16::from_be_bytes([data[0], data[1]]),
                    u16::from_be_bytes([data[2], data[3]]),
                ));
            }
            _ => {}
        }
    }
    Avif {
        items,
        size,
        colr,
        clli,
    }
}

/// Every place an export names its software, its artist, copyright,
/// description and date, read from the file.
#[derive(Debug, Default, PartialEq)]
pub struct Said {
    /// (container, text): `tiff`, `exif`, `png-text`, `xmp`.
    pub software: Vec<(&'static str, String)>,
    pub artist: Vec<String>,
    pub copyright: Vec<String>,
    pub description: Vec<String>,
    pub dated: bool,
}

fn xmp_said(packet: &[u8], said: &mut Said) {
    let text = std::str::from_utf8(packet).unwrap();
    let between = |open: &str, close: &str| -> Option<String> {
        let start = text.find(open)? + open.len();
        let end = text[start..].find(close)? + start;
        Some(text[start..end].to_owned())
    };
    if let Some(tool) = between("<xmp:CreatorTool>", "</xmp:CreatorTool>") {
        said.software.push(("xmp", tool));
    }
    let li = |name: &str| {
        let block = between(&format!("<{name}>"), &format!("</{name}>"))?;
        let start = block.find('>').map(|i| i + 1)?;
        let li = block[start..].find("<rdf:li")? + start;
        let open = block[li..].find('>')? + li + 1;
        let close = block[open..].find("</rdf:li>")? + open;
        Some(block[open..close].to_owned())
    };
    said.artist.extend(li("dc:creator"));
    said.copyright.extend(li("dc:rights"));
    said.description.extend(li("dc:description"));
    said.dated |= text.contains("xmp:CreateDate");
}

fn exif_said(block: &[u8], said: &mut Said) {
    for (tag, text) in ifd_ascii(block) {
        match tag {
            270 => said.description.push(text),
            305 => said.software.push(("exif", text)),
            306 => said.dated = true,
            315 => said.artist.push(text),
            33_432 => said.copyright.push(text),
            _ => {}
        }
    }
}

/// What the exported file at `path` says, by its extension.
pub fn said(path: &std::path::Path) -> Said {
    let bytes = std::fs::read(path).unwrap();
    let mut said = Said::default();
    match path.extension().and_then(|e| e.to_str()) {
        Some("png") => {
            for (kind, data) in png_chunks(&bytes) {
                match &kind {
                    b"tEXt" => {
                        let nul = data.iter().position(|&b| b == 0).unwrap();
                        if &data[..nul] == b"Software" {
                            let text = String::from_utf8(data[nul + 1..].to_vec()).unwrap();
                            said.software.push(("png-text", text));
                        }
                    }
                    b"iTXt" if data.starts_with(b"XML:com.adobe.xmp\0") => {
                        xmp_said(&data[22..], &mut said);
                    }
                    _ => {}
                }
            }
        }
        Some("jpg") => {
            for (marker, data) in jpeg_segments(&bytes) {
                if marker == 0xe1 && data.starts_with(b"Exif\0\0") {
                    exif_said(&data[6..], &mut said);
                } else if marker == 0xe1 && data.starts_with(b"http://ns.adobe.com/xap/1.0/\0") {
                    xmp_said(&data[29..], &mut said);
                }
            }
        }
        Some("avif") => {
            if let Some(block) = read_avif(&bytes).exif_tiff() {
                exif_said(block, &mut said);
            }
        }
        Some("tiff") => {
            use tiff::{decoder::Decoder, tags::Tag};
            let mut decoder = Decoder::new(std::io::Cursor::new(&bytes)).unwrap();
            let mut ascii = |tag| decoder.get_tag_ascii_string(tag).ok();
            if let Some(text) = ascii(Tag::Software) {
                said.software.push(("tiff", text));
            }
            said.artist.extend(ascii(Tag::Artist));
            said.copyright.extend(ascii(Tag::Copyright));
            said.dated = ascii(Tag::DateTime).is_some();
            if let Ok(packet) = decoder.get_tag_u8_vec(Tag::Unknown(700)) {
                xmp_said(&packet, &mut said);
            }
        }
        other => panic!("not an export: {other:?}"),
    }
    said
}
