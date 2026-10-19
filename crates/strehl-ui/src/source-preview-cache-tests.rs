use super::*;
use std::io::Cursor;

struct Counted<'a> {
    source: Cursor<&'a [u8]>,
    reads: usize,
    bytes: usize,
}
impl<'a> Counted<'a> {
    fn new(bytes: &'a [u8]) -> Self {
        Self {
            source: Cursor::new(bytes),
            reads: 0,
            bytes: 0,
        }
    }
}
impl Read for Counted<'_> {
    fn read(&mut self, out: &mut [u8]) -> std::io::Result<usize> {
        self.reads += 1;
        let count = self.source.read(out)?;
        self.bytes += count;
        Ok(count)
    }
}
impl Seek for Counted<'_> {
    fn seek(&mut self, at: SeekFrom) -> std::io::Result<u64> {
        self.source.seek(at)
    }
}
fn stamp(name: &str) -> Stamp {
    Stamp {
        path: PathBuf::from(format!("cache-test/{name}")),
        bytes: 8,
        modified: SystemTime::UNIX_EPOCH,
    }
}
fn candidate() -> JpegCandidate {
    JpegCandidate {
        offset: 0,
        length: 8,
        orientation: 1,
    }
}

#[test]
fn compressed_reuse_skips_actual_reads_but_changed_file_stamp_forces_new_pixels() {
    let key = stamp("reuse");
    let stopped = AtomicBool::new(false);
    let mut reader = Counted::new(b"12345678");
    let first = payload(&mut reader, 8, Some(&key), candidate(), &stopped).unwrap();
    let second = payload(&mut reader, 8, Some(&key), candidate(), &stopped).unwrap();
    assert!(Arc::ptr_eq(&first, &second));
    assert_eq!((reader.reads, reader.bytes), (1, 8));
    let mut changed = key.clone();
    changed.modified += std::time::Duration::from_secs(1);
    let mut next = Counted::new(b"abcdefgh");
    assert_eq!(
        &*payload(&mut next, 8, Some(&changed), candidate(), &stopped).unwrap(),
        b"abcdefgh"
    );
    assert_eq!((next.reads, next.bytes), (1, 8));
    assert!(cache().lock().unwrap().payload(&key, candidate()).is_none());
    stopped.store(true, Ordering::Relaxed);
    assert!(payload(&mut next, 8, Some(&changed), candidate(), &stopped).is_err());
    assert_eq!(next.reads, 1, "even a warm hit respects cancellation");
}

#[test]
fn incomplete_payload_cannot_poison_later_valid_read() {
    let key = stamp("incomplete");
    let cancelled = AtomicBool::new(false);
    let mut short = Counted::new(b"bad");
    assert!(payload(&mut short, 8, Some(&key), candidate(), &cancelled).is_err());
    let mut full = Counted::new(b"12345678");
    assert_eq!(
        &*payload(&mut full, 8, Some(&key), candidate(), &cancelled).unwrap(),
        b"12345678"
    );
    assert_eq!(full.reads, 1);
}

#[test]
fn payload_and_catalog_retention_have_independent_hard_caps() {
    let mut cache = Cache::default();
    let block: Arc<[u8]> = vec![3; 16 * 1024 * 1024].into();
    for i in 0..5 {
        cache.insert_payload(stamp(&i.to_string()), candidate(), block.clone());
        assert!(cache.bytes <= PAYLOAD_BYTES);
    }
    assert_eq!(cache.payloads.len(), 3);
    assert!(cache.payload(&stamp("0"), candidate()).is_none());
    assert!(cache.payload(&stamp("4"), candidate()).is_some());
    // Entry count is also bounded when JPEGs are tiny; a byte cap alone cannot
    // bound a folder's metadata/path allocations.
    for i in 0..PAYLOAD_LIMIT + 20 {
        cache.insert_payload(
            stamp(&format!("tiny-{i}")),
            candidate(),
            Arc::from(&b"12345678"[..]),
        );
        assert!(cache.payloads.len() <= PAYLOAD_LIMIT);
    }
    for i in 0..CATALOG_LIMIT + 20 {
        cache.insert_catalog(
            stamp(&i.to_string()),
            Arc::from(vec![(candidate(), [80, 40])]),
        );
    }
    assert_eq!(cache.catalogs.len(), CATALOG_LIMIT);
    assert!(cache.catalog(&stamp("0")).is_none());
    assert!(
        cache
            .catalog(&stamp(&(CATALOG_LIMIT + 19).to_string()))
            .is_some()
    );
}

#[test]
fn actual_tiff_directory_and_jpeg_headers_are_scanned_once_across_tiers() {
    let mut jpeg = Vec::new();
    image::codecs::jpeg::JpegEncoder::new(&mut jpeg)
        .encode(
            &vec![120; 48 * 32 * 3],
            48,
            32,
            image::ExtendedColorType::Rgb8,
        )
        .unwrap();
    let mut bytes = vec![0_u8; 128];
    bytes[..8].copy_from_slice(&[b'I', b'I', 42, 0, 8, 0, 0, 0]);
    bytes[8..10].copy_from_slice(&2_u16.to_le_bytes());
    for (i, (tag, value)) in [(513_u16, 128_u32), (514, jpeg.len() as u32)]
        .into_iter()
        .enumerate()
    {
        let entry = &mut bytes[10 + 12 * i..22 + 12 * i];
        entry[..2].copy_from_slice(&tag.to_le_bytes());
        entry[2..4].copy_from_slice(&4_u16.to_le_bytes());
        entry[4..8].copy_from_slice(&1_u32.to_le_bytes());
        entry[8..12].copy_from_slice(&value.to_le_bytes());
    }
    bytes.extend(jpeg);
    let mut key = stamp("tiff-catalog");
    key.bytes = bytes.len() as u64;
    let mut reader = Counted::new(&bytes);
    let cancel = AtomicBool::new(false);
    let first = catalog(&mut reader, key.bytes, Some(&key), &cancel).unwrap();
    assert_eq!(first.len(), 1);
    assert_eq!(first[0].1, [48, 32]);
    let cold_reads = reader.reads;
    assert!(
        cold_reads >= 4,
        "fixture must traverse TIFF and JPEG headers"
    );
    for side in [240, 960, 1920] {
        let next = catalog(&mut reader, key.bytes, Some(&key), &cancel).unwrap();
        let (_, aperture) = rank_candidates(next.to_vec(), false, true, side).unwrap();
        assert_eq!(aperture, [48, 32]);
        assert_eq!(
            reader.reads, cold_reads,
            "a new tier must reuse the directory"
        );
    }
    key.modified += std::time::Duration::from_secs(1);
    catalog(&mut reader, key.bytes, Some(&key), &cancel).unwrap();
    assert!(
        reader.reads > cold_reads,
        "changed source requires real header reads"
    );
}

#[test]
fn equal_recent_timestamps_cannot_reuse_orientation_or_jpeg_bytes() {
    let directory = crate::jobs::tests::TestDirectory::new("preview-cache-equal-timestamps");
    let path = directory.path().join("rewritten-camera.arw");
    let modified = SystemTime::now();
    let cancel = AtomicBool::new(false);
    let mut jpeg = Vec::new();
    image::codecs::jpeg::JpegEncoder::new(&mut jpeg)
        .encode(
            &vec![120; 48 * 32 * 3],
            48,
            32,
            image::ExtendedColorType::Rgb8,
        )
        .unwrap();
    let mut bytes = vec![0_u8; 128];
    bytes[..8].copy_from_slice(&[b'I', b'I', 42, 0, 8, 0, 0, 0]);
    bytes[8..10].copy_from_slice(&3_u16.to_le_bytes());
    for (i, (tag, kind, value)) in [
        (513_u16, 4_u16, 128_u32),
        (514, 4, jpeg.len() as u32),
        (274, 3, 1),
    ]
    .into_iter()
    .enumerate()
    {
        let entry = &mut bytes[10 + 12 * i..22 + 12 * i];
        entry[..2].copy_from_slice(&tag.to_le_bytes());
        entry[2..4].copy_from_slice(&kind.to_le_bytes());
        entry[4..8].copy_from_slice(&1_u32.to_le_bytes());
        entry[8..12].copy_from_slice(&value.to_le_bytes());
    }
    bytes.extend(jpeg);
    let mut previous = None;
    for orientation in [1_u32, 6] {
        bytes[42..46].copy_from_slice(&orientation.to_le_bytes());
        std::fs::write(&path, &bytes).unwrap();
        let mut file = std::fs::OpenOptions::new()
            .read(true)
            .write(true)
            .open(&path)
            .unwrap();
        file.set_times(std::fs::FileTimes::new().set_modified(modified))
            .unwrap();
        let metadata = file.metadata().unwrap();
        if let Some(prior) = previous {
            assert_eq!(
                metadata.modified().unwrap(),
                prior,
                "the collision must occur"
            );
        }
        previous = Some(metadata.modified().unwrap());
        let stamp = Stamp::new(&path, &metadata);
        assert!(stamp.is_none(), "a recent rewrite is not a stable identity");
        let actual = catalog(&mut file, metadata.len(), stamp.as_ref(), &cancel).unwrap();
        assert_eq!(actual[0].0.orientation, orientation as u16);
        let decoded = load_browser(&path, 100, false, true, &cancel).unwrap();
        assert_eq!(
            decoded.size,
            if orientation == 1 { [48, 32] } else { [32, 48] }
        );
    }
    // Stable historical files can still reuse their directory and compressed
    // payload. A future timestamp must never opt into that fast path.
    let file = std::fs::OpenOptions::new().write(true).open(&path).unwrap();
    for (time, cacheable) in [
        (SystemTime::UNIX_EPOCH + Duration::from_secs(10), true),
        (SystemTime::now() + Duration::from_secs(10), false),
    ] {
        file.set_times(std::fs::FileTimes::new().set_modified(time))
            .unwrap();
        assert_eq!(
            Stamp::new(&path, &file.metadata().unwrap()).is_some(),
            cacheable
        );
    }
}
