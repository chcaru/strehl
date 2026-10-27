use super::*;
use std::io::{Cursor, SeekFrom};

const RAW: usize = 1024;
const EXIF: usize = 512;
const MAKER: usize = 2048;
const IMAGE: usize = 18000;

#[derive(Clone)]
struct TestEntry {
    tag: u16,
    kind: u16,
    count: u32,
    bytes: Vec<u8>,
}
fn shorts(tag: u16, values: &[u16]) -> TestEntry {
    TestEntry {
        tag,
        kind: 3,
        count: values.len() as u32,
        bytes: values.iter().flat_map(|v| v.to_le_bytes()).collect(),
    }
}
fn longs(tag: u16, values: &[u32]) -> TestEntry {
    TestEntry {
        tag,
        kind: 4,
        count: values.len() as u32,
        bytes: values.iter().flat_map(|v| v.to_le_bytes()).collect(),
    }
}
fn signed(tag: u16, values: &[i16]) -> TestEntry {
    TestEntry {
        tag,
        kind: 8,
        count: values.len() as u32,
        bytes: values.iter().flat_map(|v| v.to_le_bytes()).collect(),
    }
}
fn text_entry(tag: u16, text: &str) -> TestEntry {
    let mut bytes = text.as_bytes().to_vec();
    bytes.push(0);
    TestEntry {
        tag,
        kind: 2,
        count: bytes.len() as u32,
        bytes,
    }
}
fn blob(tag: u16, bytes: Vec<u8>) -> TestEntry {
    TestEntry {
        tag,
        kind: 7,
        count: bytes.len() as u32,
        bytes,
    }
}
fn ratio(tag: u16, a: u32, b: u32) -> TestEntry {
    TestEntry {
        tag,
        kind: 5,
        count: 1,
        bytes: [a.to_le_bytes(), b.to_le_bytes()].concat(),
    }
}
fn word(out: &mut [u8], at: usize, value: u16) {
    out[at..at + 2].copy_from_slice(&value.to_le_bytes());
}
fn long(out: &mut [u8], at: usize, value: u32) {
    out[at..at + 4].copy_from_slice(&value.to_le_bytes());
}
fn put_ifd(out: &mut [u8], at: usize, entries: &[TestEntry], heap: &mut usize) {
    word(out, at, entries.len() as u16);
    for (i, e) in entries.iter().enumerate() {
        let p = at + 2 + i * 12;
        word(out, p, e.tag);
        word(out, p + 2, e.kind);
        long(out, p + 4, e.count);
        if e.tag == 0x927c {
            long(out, p + 4, 512);
            long(out, p + 8, MAKER as u32);
        } else if e.bytes.len() <= 4 {
            out[p + 8..p + 8 + e.bytes.len()].copy_from_slice(&e.bytes);
        } else {
            long(out, p + 8, *heap as u32);
            out[*heap..*heap + e.bytes.len()].copy_from_slice(&e.bytes);
            *heap += e.bytes.len();
        }
    }
    long(out, at + 2 + 12 * entries.len(), 0);
}

struct Fixture {
    bytes: Vec<u8>,
    raw: Vec<TestEntry>,
}
impl Fixture {
    fn new() -> Self {
        let mut distortion = vec![16];
        distortion.extend((0..16).map(|i| -(i as i16)));
        let mut shading = vec![16];
        shading.extend([0; 16]);
        let mut ca = vec![32];
        ca.extend([-2176; 16]);
        ca.extend([128; 16]);
        Self {
            bytes: Vec::new(),
            raw: vec![
                longs(0x0100, &[7168]),
                longs(0x0101, &[5120]),
                shorts(0x0102, &[14]),
                shorts(0x0103, &[7]),
                shorts(0x0106, &[32803]),
                longs(0x0111, &[IMAGE as u32]),
                longs(0x0117, &[32]),
                shorts(0x828d, &[2, 2]),
                TestEntry {
                    tag: 0x828e,
                    kind: 1,
                    count: 4,
                    bytes: vec![0, 1, 1, 2],
                },
                longs(0xc61f, &[12, 8]),
                longs(0xc620, &[7008, 4672]),
                longs(0x7038, &[7032, 4688]),
                longs(0x74c7, &[12, 8]),
                longs(0x74c8, &[7008, 4672]),
                shorts(0x7310, &[512; 4]),
                longs(0xc61d, &[16383]),
                shorts(0x7031, &[272]),
                signed(0x7032, &shading),
                shorts(0x7034, &[0]),
                signed(0x7035, &ca),
                shorts(0x7036, &[0]),
                signed(0x7037, &distortion),
            ],
        }
    }
    fn build(mut self) -> Self {
        let mut out = vec![0; 20000];
        out[..4].copy_from_slice(b"II*\0");
        long(&mut out, 4, 8);
        let mut heap = 4096;
        put_ifd(
            &mut out,
            8,
            &[
                text_entry(0x010f, "SONY"),
                text_entry(0x0110, "ILCE-7CM2"),
                text_entry(0x0131, "ILCE-7CM2 v2.00"),
                shorts(0x0112, &[1]),
                longs(0x014a, &[RAW as u32]),
                longs(0x8769, &[EXIF as u32]),
            ],
            &mut heap,
        );
        put_ifd(
            &mut out,
            EXIF,
            &[
                ratio(0x829a, 1, 5),
                ratio(0x829d, 56, 10),
                shorts(0x8827, &[100]),
                text_entry(0x9003, "2026:08:23 11:58:28"),
                ratio(0x920a, 2000, 10),
                text_entry(0xa434, "FE 100mm F2.8 Macro GM OSS + 2X Teleconverter"),
                blob(0x927c, vec![0; 8]),
            ],
            &mut heap,
        );
        // Independent forward encoder, never the candidate DECIPHER table.
        let mut plain = vec![0u8; 32];
        plain[9..11].copy_from_slice(&33094u16.to_le_bytes());
        let cipher = plain
            .into_iter()
            .map(|v| {
                if v < 249 {
                    (u32::from(v).pow(3) % 249) as u8
                } else {
                    v
                }
            })
            .collect();
        put_ifd(
            &mut out,
            MAKER,
            &[
                longs(0x2011, &[0]),
                longs(0x2012, &[0]),
                longs(0x2013, &[0]),
                blob(0x940c, cipher),
            ],
            &mut heap,
        );
        put_ifd(&mut out, RAW, &self.raw, &mut heap);
        out[IMAGE..IMAGE + 32].fill(0xa5);
        self.bytes = out;
        self
    }
    fn remove(&mut self, tag: u16) {
        self.raw.retain(|e| e.tag != tag);
    }
    fn replace(&mut self, entry: TestEntry) {
        self.remove(entry.tag);
        self.raw.push(entry);
    }
}
fn entry_offset(bytes: &[u8], ifd: usize, tag: u16) -> usize {
    (0..u16le(bytes, ifd) as usize)
        .map(|i| ifd + 2 + i * 12)
        .find(|&p| u16le(bytes, p) == tag)
        .unwrap()
}
fn read_fixture(f: Fixture) -> Result<Option<SonyOpticalMetadata>> {
    read_from_reader(&mut Cursor::new(f.bytes))
}

#[test]
fn exact_signed_tables_settings_and_header_provenance_are_preserved() {
    let f = Fixture::new().build();
    let expected = f.bytes.clone();
    let metadata = read_fixture(f).unwrap().unwrap();
    let table = metadata.distortion.table.unwrap();
    assert_eq!(table.prefix, 16);
    assert_eq!(table.samples, std::array::from_fn(|i| -(i as i16)));
    assert_eq!(
        metadata.distortion.setting.unwrap().value,
        0,
        "Off never erases a present table"
    );
    assert_eq!(table.source.tag, 0x7037);
    assert_eq!(table.source.tiff_type, 8);
    assert_eq!(table.source.count, 17);
    let offset = table.source.value_offset as usize;
    assert_eq!(table.raw_bytes, expected[offset..offset + 34]);
    assert_eq!(
        metadata.chromatic_aberration.table.unwrap().samples[..16],
        [-2176; 16]
    );
    assert_eq!(metadata.shading.setting.unwrap().value, 272);
    assert_eq!(
        metadata.maker_shading_setting.unwrap().value,
        0,
        "independent setting channels remain separate"
    );
    assert_eq!(metadata.lens_type3.unwrap().value, 33094);
    assert_eq!(
        metadata.geometry.default_crop_origin.unwrap().value,
        [12, 8]
    );
    assert_eq!(
        metadata.geometry.default_crop_size.unwrap().value,
        [7008, 4672]
    );
    assert_eq!(
        metadata.geometry.sony_image_size.unwrap().value,
        [7032, 4688]
    );
    assert_eq!(metadata.header_black.unwrap().value, [512; 4]);
    assert_eq!(
        metadata.header_white.unwrap().value,
        16383,
        "must not substitute native working white15360"
    );
    assert_eq!(metadata.iso.unwrap().value, 100);
    assert_eq!(metadata.exposure_time.unwrap().value, [1, 5]);
    assert_eq!(metadata.aperture.unwrap().value, [56, 10]);
    assert_eq!(metadata.focal_length.unwrap().value, [2000, 10]);
    assert!(metadata.metadata_bytes_read < 128 * 1024);
    assert_eq!(metadata.source_file_bytes, 20000);
}

#[test]
fn missing_partial_unknown_and_malformed_are_distinct() {
    let mut missing = Fixture::new();
    for tag in [0x7031, 0x7032, 0x7034, 0x7035, 0x7036, 0x7037] {
        missing.remove(tag);
    }
    assert!(read_fixture(missing.build()).unwrap().is_none());
    let mut partial = Fixture::new();
    partial.remove(0x7037);
    let result = read_fixture(partial.build()).unwrap().unwrap();
    assert_eq!(result.distortion.setting.unwrap().value, 0);
    assert!(result.distortion.table.is_none());
    let mut unknown = Fixture::new();
    unknown.replace(shorts(0x7036, &[231]));
    assert_eq!(
        read_fixture(unknown.build())
            .unwrap()
            .unwrap()
            .distortion
            .setting
            .unwrap()
            .value,
        231
    );
    let mut negative_setting = Fixture::new();
    negative_setting.replace(signed(0x7036, &[-1]));
    assert_eq!(
        read_fixture(negative_setting.build())
            .unwrap()
            .unwrap()
            .distortion
            .setting
            .unwrap()
            .value,
        -1
    );
    for entry in [
        shorts(0x7037, &[16; 17]),
        signed(0x7037, &[16; 16]),
        signed(0x7037, &[15; 17]),
        blob(0x7036, vec![0]),
    ] {
        let mut invalid = Fixture::new();
        invalid.replace(entry);
        assert!(matches!(
            read_fixture(invalid.build()),
            Err(SonyOpticalError::Malformed(_))
        ));
    }
    let mut wrong = Fixture::new().build();
    let model = entry_offset(&wrong.bytes, 8, 0x0110);
    let at = u32le(&wrong.bytes, model + 8) as usize;
    wrong.bytes[at..at + 10].copy_from_slice(b"ILCE-7RM5\0");
    assert!(matches!(
        read_fixture(wrong),
        Err(SonyOpticalError::Unsupported(_))
    ));
}

#[test]
fn truncated_duplicate_cyclic_and_escaping_metadata_refuse() {
    let base = Fixture::new().build();
    for cut in [0, 4, 8, RAW + 2, RAW + 200, MAKER + 2, 4096, 4500] {
        let mut f = Fixture::new().build();
        f.bytes.truncate(cut);
        assert!(read_fixture(f).is_err(), "truncation at{cut} must refuse");
    }
    let mut duplicate = Fixture::new();
    duplicate.raw.push(shorts(0x7036, &[0]));
    assert!(matches!(
        read_fixture(duplicate.build()),
        Err(SonyOpticalError::Malformed(_))
    ));
    let mut cycle = Fixture::new().build();
    let sub = entry_offset(&cycle.bytes, 8, 0x014a);
    long(&mut cycle.bytes, sub + 8, 8);
    assert!(matches!(
        read_fixture(cycle),
        Err(SonyOpticalError::Malformed(_))
    ));
    let mut escape = Fixture::new().build();
    let table = entry_offset(&escape.bytes, RAW, 0x7037);
    long(&mut escape.bytes, table + 8, 19990);
    assert!(matches!(
        read_fixture(escape),
        Err(SonyOpticalError::Malformed(_))
    ));
    let mut image_overlap = Fixture::new().build();
    let table = entry_offset(&image_overlap.bytes, RAW, 0x7037);
    long(&mut image_overlap.bytes, table + 8, IMAGE as u32);
    assert!(matches!(
        read_fixture(image_overlap),
        Err(SonyOpticalError::Malformed(_))
    ));
    let mut large = base;
    long(&mut large.bytes, 4, 9 * 1024 * 1024);
    assert!(matches!(
        read_fixture(large),
        Err(SonyOpticalError::Malformed(_))
    ));
}

#[test]
fn focus_and_identity_public_interfaces_keep_their_old_optional_behavior() {
    let f = Fixture::new().build();
    let identity = crate::identity::identity_from_reader(&mut Cursor::new(&f.bytes));
    assert_eq!(identity.model.as_deref(), Some("ILCE-7CM2"));
    assert_eq!(identity.lens_type3, Some(33094));
    let focus: std::result::Result<
        Option<crate::sony_focus::SonyFocusMetadata>,
        crate::sony_focus::SonyFocusError,
    > = crate::sony_focus::read_from_reader(&mut Cursor::new(&f.bytes));
    assert!(
        focus.unwrap().is_none(),
        "optical metadata does not fabricate a hidden focus block"
    );
    let metadata = read_from_reader(&mut Cursor::new(&f.bytes))
        .unwrap()
        .unwrap();
    assert_eq!(metadata.model.value, identity.model.unwrap());
    assert_eq!(
        Some(metadata.lens_type3.unwrap().value),
        identity.lens_type3
    );
}

#[test]
fn bounded_header_reader_does_not_touch_declared_image_payload() {
    struct Guard {
        inner: Cursor<Vec<u8>>,
        read_bytes: usize,
    }
    impl Read for Guard {
        fn read(&mut self, buffer: &mut [u8]) -> std::io::Result<usize> {
            let at = self.inner.position() as usize;
            assert!(
                at + buffer.len() <= IMAGE || at >= IMAGE + 32,
                "image bytes were requested"
            );
            let count = self.inner.read(buffer)?;
            self.read_bytes += count;
            Ok(count)
        }
    }
    impl Seek for Guard {
        fn seek(&mut self, to: SeekFrom) -> std::io::Result<u64> {
            self.inner.seek(to)
        }
    }
    let mut guard = Guard {
        inner: Cursor::new(Fixture::new().build().bytes),
        read_bytes: 0,
    };
    let metadata = read_from_reader(&mut guard).unwrap().unwrap();
    assert_eq!(metadata.metadata_bytes_read, guard.read_bytes);
    assert!(guard.read_bytes < 128 * 1024);
}

#[test]
fn present_zero_lens_slot_and_rational_bytes_do_not_become_guessed_values() {
    let mut f = Fixture::new().build();
    let lens = entry_offset(&f.bytes, MAKER, 0x940c);
    let at = u32le(&f.bytes, lens + 8) as usize;
    f.bytes[at + 9] = 0;
    f.bytes[at + 10] = 0;
    let aperture = entry_offset(&f.bytes, EXIF, 0x829d);
    let at = u32le(&f.bytes, aperture + 8) as usize;
    long(&mut f.bytes, at + 4, 0);
    let metadata = read_from_reader(&mut Cursor::new(&f.bytes))
        .unwrap()
        .unwrap();
    assert_eq!(metadata.lens_type3.unwrap().value, 0);
    assert_eq!(metadata.aperture.unwrap().value, [56, 0]);
    assert_eq!(
        crate::identity::identity_from_reader(&mut Cursor::new(&f.bytes)).lens_type3,
        None,
        "legacy profile identity still declines an unpopulated slot"
    );
}

#[test]
fn shared_read_budget_and_optical_address_guard_are_exercised() {
    let mut bytes = Cursor::new(vec![0; 128 * 1024 + 1]);
    let mut reader = Reader::new(&mut bytes).unwrap();
    assert_eq!(reader.bytes(0, 128 * 1024).unwrap().len(), 128 * 1024);
    assert!(matches!(
        reader.bytes(0, 1),
        Err(SonyTiffError::Malformed(_))
    ));
    let mut bytes = Cursor::new(vec![0; 16]);
    let mut reader = Reader::new(&mut bytes).unwrap();
    reader.limit_address(8);
    assert!(matches!(
        reader.bytes(7, 2),
        Err(SonyTiffError::Malformed(_))
    ));
}
#[test]
fn setting_width_signedness_and_inline_provenance_are_lossless() {
    let cases: [(u16, u32, i64, usize); 7] = [
        (3, 65535, 65535, 2),
        (8, 65535, -1, 2),
        (8, 32768, -32768, 2),
        (4, 0, 0, 4),
        (4, 231, 231, 4),
        (4, 0x8000_0000, 2_147_483_648, 4),
        (4, u32::MAX, 4_294_967_295, 4),
    ];
    for tag in [0x7031, 0x7034, 0x7036, 0x2011, 0x2012, 0x2013] {
        for (kind, bits, expected, width) in cases {
            let mut f = Fixture::new().build();
            let directory = if tag < 0x7000 { MAKER } else { RAW };
            let at = entry_offset(&f.bytes, directory, tag);
            word(&mut f.bytes, at + 2, kind);
            long(&mut f.bytes, at + 4, 1);
            long(&mut f.bytes, at + 8, bits);
            let metadata = read_fixture(f).unwrap().unwrap();
            let setting = match tag {
                0x7031 => metadata.shading.setting,
                0x7034 => metadata.chromatic_aberration.setting,
                0x7036 => metadata.distortion.setting,
                0x2011 => metadata.maker_shading_setting,
                0x2012 => metadata.maker_ca_setting,
                _ => metadata.maker_distortion_setting,
            }
            .unwrap();
            assert_eq!(setting.value, expected, "tag {tag:x} kind {kind}");
            assert_eq!(
                setting.source,
                TagSource {
                    tag,
                    tiff_type: kind,
                    count: 1,
                    value_offset: (at + 8) as u64
                }
            );
            assert_eq!(setting.raw_bytes, bits.to_le_bytes()[..width]);
        }
    }
}

#[test]
fn all_setting_channels_refuse_wrong_type_or_nonscalar_count() {
    for tag in [0x7031, 0x7034, 0x7036, 0x2011, 0x2012, 0x2013] {
        for (kind, count) in [
            (1, 1),
            (2, 1),
            (7, 1),
            (9, 1),
            (4, 0),
            (4, 2),
            (3, 2),
            (8, 0),
            (8, 2),
        ] {
            let mut f = Fixture::new().build();
            let directory = if tag < 0x7000 { MAKER } else { RAW };
            let at = entry_offset(&f.bytes, directory, tag);
            word(&mut f.bytes, at + 2, kind);
            long(&mut f.bytes, at + 4, count);
            assert!(
                matches!(read_fixture(f), Err(SonyOpticalError::Malformed(_))),
                "tag {tag:x} kind {kind} count {count}"
            );
        }
    }
}
