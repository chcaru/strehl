use super::*;
use quick_xml::{Reader, events::Event};

fn meta() -> ExportMetadata {
    ExportMetadata {
        artist: "Chris & <Co>".into(),
        copyright: "© 2026 Chris".into(),
        description: "Weevil, 昆虫\nsecond line".into(),
    }
}

fn date() -> ExportDateTime {
    ExportDateTime::from_unix_seconds(1_700_000_000, 60)
}

#[test]
fn civil_dates_and_offsets_are_exact() {
    let epoch = ExportDateTime::from_unix_seconds(0, 0);
    assert_eq!(epoch.tiff(), "1970:01:01 00:00:00");
    assert_eq!(epoch.xmp(), "1970-01-01T00:00:00Z");
    assert_eq!(
        ExportDateTime::from_unix_seconds(1_700_000_000, 0).tiff(),
        "2023:11:14 22:13:20"
    );
    assert_eq!(date().tiff(), "2023:11:14 23:13:20");
    assert_eq!(date().xmp(), "2023-11-14T23:13:20+01:00");
    assert_eq!(
        ExportDateTime::from_unix_seconds(951_782_400, 0).tiff(),
        "2000:02:29 00:00:00"
    );
    let west = ExportDateTime::from_unix_seconds(0, -330);
    assert_eq!(west.xmp(), "1969-12-31T18:30:00-05:30");
    west.validate().unwrap();
}

#[test]
fn xmp_packet_round_trips_unicode_and_escapes_markup() {
    assert!(
        xmp_packet(&ExportMetadata::default(), None)
            .unwrap()
            .is_none()
    );
    let packet = xmp_packet(&meta(), Some(&date())).unwrap().unwrap();
    let text = String::from_utf8(packet.clone()).unwrap();
    assert!(text.starts_with("<?xpacket begin=\"\u{feff}\""));
    assert!(text.ends_with("<?xpacket end=\"w\"?>"));
    assert!(text.contains("Chris &amp; &lt;Co&gt;"));
    let mut reader = Reader::from_str(&text);
    let mut path = Vec::<String>::new();
    let mut found = Vec::new();
    let mut value = String::new();
    loop {
        match reader.read_event().unwrap() {
            Event::Start(e) => {
                path.push(String::from_utf8(e.name().as_ref().to_vec()).unwrap());
                value.clear();
            }
            Event::Text(t) => value.push_str(&t.decode().unwrap()),
            Event::GeneralRef(r) => {
                let name = r.decode().unwrap();
                value.push_str(quick_xml::escape::resolve_predefined_entity(&name).unwrap());
            }
            Event::End(_) => {
                let leaf = path.pop().unwrap();
                if !value.is_empty() {
                    let owner = if leaf == "rdf:li" {
                        path.iter().rev().find(|p| p.starts_with("dc:")).cloned()
                    } else {
                        Some(leaf)
                    };
                    found.push((owner.unwrap(), std::mem::take(&mut value)));
                }
            }
            Event::Eof => break,
            _ => {}
        }
    }
    assert!(found.contains(&("dc:creator".into(), "Chris & <Co>".into())));
    assert!(found.contains(&("dc:rights".into(), "© 2026 Chris".into())));
    assert!(found.contains(&("dc:description".into(), "Weevil, 昆虫\nsecond line".into())));
    assert!(found.contains(&("xmp:CreateDate".into(), "2023-11-14T23:13:20+01:00".into())));
}

fn ifd_ascii(block: &[u8]) -> Vec<(u16, String)> {
    assert_eq!(&block[..4], b"II*\0");
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
            assert_eq!(bytes.last(), Some(&0), "NUL-terminated");
            (tag, String::from_utf8(bytes[..n - 1].to_vec()).unwrap())
        })
        .collect()
}

#[test]
fn exif_block_is_a_sorted_ascii_ifd() {
    assert!(exif_block(&ExportMetadata::default(), None).is_none());
    let tags = ifd_ascii(&exif_block(&meta(), Some(&date())).unwrap());
    assert_eq!(
        tags,
        vec![
            (270, "Weevil, ?? second line".to_owned()),
            (305, "Strehl".to_owned()),
            (306, "2023:11:14 23:13:20".to_owned()),
            (315, "Chris & <Co>".to_owned()),
            (33_432, "(c) 2026 Chris".to_owned()),
        ]
    );
}

#[test]
fn ascii_fallbacks_and_json_escaping_are_lossless_where_promised() {
    assert_eq!(ascii_text("© µm – “x”"), "(c) um - \"x\"");
    let plain = serde_json::json!({"name": "plain"});
    assert_eq!(
        json_ascii(&plain).unwrap(),
        serde_json::to_string(&plain).unwrap()
    );
    let rich = serde_json::json!({"name": "昆虫 🦋 é"});
    let escaped = json_ascii(&rich).unwrap();
    assert!(escaped.is_ascii());
    assert_eq!(
        serde_json::from_str::<serde_json::Value>(&escaped).unwrap(),
        rich
    );
}

fn chunk(kind: &[u8; 4], data: &[u8]) -> Vec<u8> {
    let mut body = kind.to_vec();
    body.extend_from_slice(data);
    let mut out = (data.len() as u32).to_be_bytes().to_vec();
    out.extend_from_slice(&body);
    out.extend_from_slice(&crc32(&body).to_be_bytes());
    out
}

#[test]
fn png_inserter_places_one_valid_itxt_before_the_first_idat_at_any_write_size() {
    assert_eq!(crc32(b"IEND"), 0xae42_6082, "CRC-32 of the IEND chunk type");
    let mut png = b"\x89PNG\r\n\x1a\n".to_vec();
    png.extend(chunk(b"IHDR", &[0; 13]));
    png.extend(chunk(b"iCCP", b"profile\0\0data"));
    let before = png.len();
    png.extend(chunk(b"IDAT", &[7; 300]));
    png.extend(chunk(b"IDAT", &[8; 5]));
    png.extend(chunk(b"IEND", &[]));
    let packet = b"<x:xmpmeta/>";
    let inserted = png_xmp_chunk(packet);
    for step in [1usize, 3, 7, 4096] {
        let mut writer = PngChunkInserter::new(Vec::new(), inserted.clone());
        for piece in png.chunks(step) {
            writer.write_all(piece).unwrap();
        }
        let out = writer.finish().unwrap();
        let mut expected = png[..before].to_vec();
        expected.extend_from_slice(&inserted);
        expected.extend_from_slice(&png[before..]);
        assert_eq!(out, expected, "write size {step}");
    }
    let body = &inserted[4..inserted.len() - 4];
    assert_eq!(&body[..4], b"iTXt");
    assert_eq!(
        u32::from_be_bytes(inserted[inserted.len() - 4..].try_into().unwrap()),
        crc32(body)
    );
    assert!(body.windows(packet.len()).any(|w| w == packet));
    // Negative control: a stream without image data is refused, not published.
    let mut truncated = PngChunkInserter::new(Vec::new(), inserted);
    truncated.write_all(&png[..before]).unwrap();
    assert!(truncated.finish().is_err());
}

#[test]
fn jpeg_inserter_places_xmp_after_jfif_and_exif_at_any_write_size() {
    let segment = |marker: u8, data: &[u8]| {
        let mut s = vec![0xff, marker];
        s.extend_from_slice(&((data.len() + 2) as u16).to_be_bytes());
        s.extend_from_slice(data);
        s
    };
    let mut jpeg = vec![0xff, 0xd8];
    jpeg.extend(segment(0xe0, b"JFIF\0\x01\x02\0\0\x01\0\x01\0\0"));
    jpeg.extend(segment(0xe1, b"Exif\0\0II*\0"));
    let before = jpeg.len();
    jpeg.extend(segment(0xe2, b"ICC_PROFILE\0\x01\x01data"));
    jpeg.extend(segment(0xdb, &[1; 65]));
    jpeg.extend([0xff, 0xd9]);
    let xmp = jpeg_xmp_segment(b"<x:xmpmeta/>").unwrap();
    for step in [1usize, 2, 5, 4096] {
        let mut writer = JpegSegmentInserter::new(Vec::new(), xmp.clone());
        for piece in jpeg.chunks(step) {
            writer.write_all(piece).unwrap();
        }
        let out = writer.finish().unwrap();
        let mut expected = jpeg[..before].to_vec();
        expected.extend_from_slice(&xmp);
        expected.extend_from_slice(&jpeg[before..]);
        assert_eq!(out, expected, "write size {step}");
    }
    assert!(jpeg_xmp_segment(&vec![b'a'; 70_000]).is_err());
}

#[test]
fn metadata_validation_refuses_controls_oversize_and_reserved_wording() {
    meta().validate().unwrap();
    for bad in [
        ExportMetadata {
            artist: "a\nb".into(),
            ..Default::default()
        },
        ExportMetadata {
            copyright: "x".repeat(513),
            ..Default::default()
        },
        ExportMetadata {
            description: "BakedSourceRecipe: {}".into(),
            ..Default::default()
        },
        ExportMetadata {
            description: "a camera-native file".into(),
            ..Default::default()
        },
        ExportMetadata {
            description: "tab\tseparated".into(),
            ..Default::default()
        },
    ] {
        assert!(bad.validate().is_err(), "{bad:?}");
    }
}
