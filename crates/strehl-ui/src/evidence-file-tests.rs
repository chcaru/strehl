use super::*;

/// An independent writer of the documented format (not the engine's code).
pub(crate) fn header_bytes(levels: &[([u16; 2], [u32; 2])], frames: u32) -> Vec<u8> {
    let mut bytes = b"STRHEVD1".to_vec();
    bytes.extend(VERSION.to_le_bytes());
    bytes.extend((levels.len() as u32).to_le_bytes());
    for (samples, extent) in levels {
        bytes.extend(samples[0].to_le_bytes());
        bytes.extend(samples[1].to_le_bytes());
        bytes.extend(extent[0].to_le_bytes());
        bytes.extend(extent[1].to_le_bytes());
    }
    bytes.extend(frames.to_le_bytes());
    bytes
}

pub(crate) fn record_bytes(
    frame: u32,
    level: u8,
    kind: u8,
    sequence: u32,
    payload: &[u8],
) -> Vec<u8> {
    let mut bytes = frame.to_le_bytes().to_vec();
    bytes.extend([level, kind, 0, 0]);
    bytes.extend(sequence.to_le_bytes());
    bytes.extend((payload.len() as u32).to_le_bytes());
    bytes.extend_from_slice(payload);
    bytes
}

pub(crate) fn support_payload(sites: &[bool]) -> Vec<u8> {
    let mut payload = vec![0u8; sites.len().div_ceil(8)];
    for (index, &on) in sites.iter().enumerate() {
        if on {
            payload[index / 8] |= 1 << (index % 8);
        }
    }
    payload
}

fn float_payload(min: f32, max: f32, samples: &[u8]) -> Vec<u8> {
    let mut payload = min.to_le_bytes().to_vec();
    payload.extend(max.to_le_bytes());
    payload.extend_from_slice(samples);
    payload
}

fn fixture() -> (Vec<u8>, Vec<bool>) {
    let mut bytes = header_bytes(&[([13, 7], [900, 600]), ([7, 4], [450, 300])], 3);
    let sites: Vec<bool> = (0..91).map(|i| [0, 12, 63, 64, 90].contains(&i)).collect();
    bytes.extend(record_bytes(1, 0, 0, 5, &support_payload(&sites)));
    bytes.extend(record_bytes(1, 1, 0, 6, &support_payload(&[false; 28])));
    let samples: Vec<u8> = (0..28).map(|i| i as u8 * 9).collect();
    bytes.extend(record_bytes(
        2,
        1,
        2,
        9,
        &float_payload(0.5, 80.0, &samples),
    ));
    bytes.extend(record_bytes(
        2,
        1,
        3,
        10,
        &float_payload(0.0, 4.0, &samples),
    ));
    (bytes, sites)
}

#[test]
fn records_decode_identically_however_the_bytes_are_split() {
    let (bytes, sites) = fixture();
    let mut whole = Vec::new();
    let mut decoder = EvidenceDecoder::default();
    decoder.feed(&bytes, &mut whole);
    assert_eq!(whole.len(), 4);
    let header = decoder.header().unwrap();
    assert_eq!(header.frames_total, 3);
    assert_eq!(header.analysis_extent(), [900, 600]);
    assert_eq!(header.levels[1].samples, [7, 4]);
    let support = &whole[0];
    assert_eq!(
        (
            support.surface.frame,
            support.surface.level,
            support.surface.sequence
        ),
        (1, 0, 5)
    );
    assert_eq!(support.surface.kind, DiagnosticKind::GateSupport);
    assert_eq!(support.surface.scope, DiagnosticScope::Frame);
    assert_eq!(
        (
            support.surface.min,
            support.surface.max,
            support.surface.folded
        ),
        (0.0, 1.0, 1)
    );
    let pixels: Vec<bool> = support.surface.pixels.iter().map(|&v| v == 255).collect();
    assert_eq!(pixels, sites);
    assert!(support.surface.pixels.iter().all(|&v| v == 0 || v == 255));
    let packed = support.packed.as_ref().unwrap();
    assert_eq!(packed.on, 5);
    for (index, &on) in sites.iter().enumerate() {
        assert_eq!(packed.bits[index / 64] & (1 << (index % 64)) != 0, on);
    }
    assert!(packed.bits[2..].iter().all(|&word| word == 0));
    let energy = &whole[2];
    assert_eq!(energy.surface.kind, DiagnosticKind::FocusEnergy);
    assert_eq!(energy.surface.scale, DiagnosticScale::Log);
    assert_eq!((energy.surface.min, energy.surface.max), (0.5, 80.0));
    assert_eq!(energy.surface.pixels[27], 27 * 9);
    assert!(energy.packed.is_none());
    assert_eq!(whole[3].surface.kind, DiagnosticKind::GateFloor);

    // One byte at a time: every torn header and record is held, not dropped.
    let mut split = Vec::new();
    let mut decoder = EvidenceDecoder::default();
    for byte in &bytes {
        decoder.feed(std::slice::from_ref(byte), &mut split);
    }
    assert_eq!(split.len(), whole.len());
    for (a, b) in split.iter().zip(&whole) {
        assert_eq!(a.surface.sequence, b.surface.sequence);
        assert_eq!(a.surface.pixels, b.surface.pixels);
    }
    assert_eq!((decoder.skipped(), decoder.failure()), (0, None));
}

#[test]
fn records_that_disagree_with_their_lattice_are_skipped_never_reinterpreted() {
    let mut bytes = header_bytes(&[([13, 7], [900, 600])], 3);
    let good = support_payload(&[true; 91]);
    let mut dirty = good.clone();
    *dirty.last_mut().unwrap() |= 0x80; // a bit past site 90
    for record in [
        record_bytes(3, 0, 0, 1, &good),      // frame beyond frames_total
        record_bytes(0, 1, 0, 2, &good),      // no such level
        record_bytes(0, 0, 0, 0, &good),      // sequence zero
        record_bytes(0, 0, 0, 3, &good[1..]), // short payload
        record_bytes(0, 0, 0, 4, &dirty),     // dirty tail bits
        record_bytes(0, 0, 9, 5, &good),      // unknown kind
        record_bytes(0, 0, 1, 6, &good),      // reserved averaging kind
        record_bytes(0, 0, 2, 7, &float_payload(f32::NAN, 1.0, &[0; 91])),
        record_bytes(0, 0, 2, 8, &float_payload(2.0, 1.0, &[0; 91])),
        record_bytes(0, 0, 3, 9, &float_payload(-1.0, 1.0, &[0; 91])),
    ] {
        bytes.extend(record);
    }
    bytes.extend(record_bytes(2, 0, 0, 11, &good));
    let mut out = Vec::new();
    let mut decoder = EvidenceDecoder::default();
    decoder.feed(&bytes, &mut out);
    assert_eq!(decoder.skipped(), 10);
    assert_eq!(decoder.failure(), None);
    assert_eq!(out.len(), 1);
    assert_eq!((out[0].surface.frame, out[0].surface.sequence), (2, 11));
}

#[test]
fn untrustworthy_framing_stops_the_file() {
    for (label, bytes) in [
        ("magic", {
            let mut bytes = header_bytes(&[([2, 2], [4, 4])], 1);
            bytes[0] = b'X';
            bytes
        }),
        ("version", {
            let mut bytes = header_bytes(&[([2, 2], [4, 4])], 1);
            bytes[8] = 2;
            bytes
        }),
        ("lattice", header_bytes(&[([129, 2], [400, 4])], 1)),
        ("frames", header_bytes(&[([2, 2], [4, 4])], 0)),
        ("payload", {
            let mut bytes = header_bytes(&[([2, 2], [4, 4])], 1);
            bytes.extend(record_bytes(0, 0, 0, 1, &[0]));
            let at = bytes.len() - 5;
            bytes[at..at + 4].copy_from_slice(&(1u32 << 20).to_le_bytes());
            bytes
        }),
    ] {
        let mut out = Vec::new();
        let mut decoder = EvidenceDecoder::default();
        decoder.feed(&bytes, &mut out);
        decoder.feed(&record_bytes(0, 0, 0, 2, &[0]), &mut out);
        assert!(decoder.failure().is_some(), "{label}");
        assert!(out.is_empty(), "{label}");
    }
}

#[test]
fn a_growing_file_is_tailed_within_its_budget() {
    let directory = crate::jobs::tests::TestDirectory::new("evidence-tail");
    let path = directory.path().join(FILE_NAME);
    let mut tail = EvidenceTail::new(path.clone());
    assert!(
        matches!(tail.poll(1 << 16).unwrap(), (None, false)),
        "no file yet"
    );
    let (bytes, _) = fixture();
    let split = bytes.len() - 20;
    std::fs::write(&path, &bytes[..split]).unwrap();
    let (batch, more) = tail.poll(1 << 16).unwrap();
    assert!(!more);
    assert_eq!(
        batch.unwrap().records.len(),
        3,
        "the torn fourth record waits"
    );
    let mut file = std::fs::OpenOptions::new()
        .append(true)
        .open(&path)
        .unwrap();
    std::io::Write::write_all(&mut file, &bytes[split..]).unwrap();
    // Budget smaller than what is waiting: the rest is reported as more.
    let (batch, more) = tail.poll(8).unwrap();
    assert!(batch.is_none() && more);
    let (batch, more) = tail.poll(1 << 16).unwrap();
    assert!(!more);
    let records = batch.unwrap().records;
    assert_eq!(records.len(), 1);
    assert_eq!(records[0].surface.kind, DiagnosticKind::GateFloor);
    assert!(matches!(tail.poll(1 << 16).unwrap(), (None, false)));
    assert_eq!(tail.decoder().skipped(), 0);
}

#[test]
fn whole_reads_stream_records_and_report_a_torn_end() {
    let directory = crate::jobs::tests::TestDirectory::new("evidence-read");
    let path = directory.path().join(FILE_NAME);
    let (bytes, _) = fixture();
    std::fs::write(&path, &bytes[..bytes.len() - 3]).unwrap();
    let mut seen = Vec::new();
    let summary = read_into(&path, &AtomicBool::new(false), |header, record| {
        assert_eq!(header.frames_total, 3);
        seen.push(record.surface.sequence);
    })
    .unwrap();
    assert_eq!(seen, [5, 6, 9]);
    assert_eq!(summary.records, 3);
    assert!(summary.torn > 0 && summary.failure.is_none());
    assert!(read_into(&path, &AtomicBool::new(true), |_, _| ()).is_err());
}

#[test]
fn a_log_can_name_only_a_file_inside_its_run() {
    let run = Path::new("run");
    assert_eq!(named_path(run, FILE_NAME), Some(run.join(FILE_NAME)));
    for name in [
        "",
        ".",
        "..",
        "../evidence.strehl",
        "a/b",
        "a\\b",
        "C:evidence",
    ] {
        assert_eq!(named_path(run, name), None, "{name}");
    }
}

/// A summary payload as `merge_cmd/focus-evidence.rs` documents it.
fn focus_summary(usable: bool, reason: u16, frames: u32, text: &str) -> Vec<u8> {
    let mut out = vec![1, u8::from(usable)];
    out.extend(reason.to_le_bytes());
    for value in [frames, 900, 600, 1234, 5678] {
        out.extend(value.to_le_bytes());
    }
    out.extend(2.5f32.to_le_bytes());
    out.extend(7u64.to_le_bytes());
    for count in 1..=7u32 {
        out.extend((count * 10).to_le_bytes());
    }
    out.extend((text.len() as u16).to_le_bytes());
    out.extend(text.as_bytes());
    out
}

fn focus_file(dir: &Path, records: &[Vec<u8>]) -> PathBuf {
    let mut bytes = header_bytes(&[([13, 7], [900, 600]), ([7, 4], [450, 300])], 3);
    bytes.extend(record_bytes(1, 0, 0, 5, &support_payload(&[true; 91])));
    for record in records {
        bytes.extend(record);
    }
    let path = dir.join(FILE_NAME);
    std::fs::write(&path, bytes).unwrap();
    path
}

/// The focus field's records: the maps reader skips them whole (as readers
/// that predate them do: this decoder is unchanged) and `read_focus` reads
/// them, seeking over the plane maps. A field is drawn only where it is
/// usable and an area has a depth.
#[test]
fn focus_records_are_skipped_by_the_maps_reader_and_read_by_read_focus() {
    let dir = tempfile::tempdir().unwrap();
    let mut depth = vec![255u8; 91];
    depth[0] = 0;
    depth[2] = 100;
    depth[14] = 127;
    depth[90] = 254;
    let mut share = vec![128u8; 91];
    share[2] = 30;
    let field = [
        record_bytes(0, 0, 9, u32::MAX - 2, &focus_summary(true, 0, 11, "")),
        record_bytes(0, 0, 7, u32::MAX - 1, &float_payload(0.0, 10.0, &depth)),
        record_bytes(0, 0, 8, u32::MAX, &float_payload(0.0, 1.0, &share)),
    ];
    let path = focus_file(dir.path(), &field);
    // The maps reader: one map, three skipped, no failure.
    let bytes = std::fs::read(&path).unwrap();
    let mut decoder = EvidenceDecoder::default();
    let mut out = Vec::new();
    decoder.feed(&bytes, &mut out);
    assert_eq!(
        (out.len(), decoder.skipped(), decoder.failure()),
        (1, 3, None)
    );
    let focus = read_focus(&path).unwrap().expect("a field");
    assert_eq!(
        (focus.lattice, focus.extent, focus.frames, focus.usable),
        ([13, 7], [900, 600], 11, true)
    );
    assert_eq!(
        (focus.usable_pixels, focus.seconds, focus.reservation_bytes),
        (1234, 2.5, 7)
    );
    assert_eq!(focus.flag_pixels, [10, 20, 30, 40, 50, 60, 70]);
    assert_eq!(focus.ordinal(0, 0), Some(0.0));
    assert_eq!(focus.ordinal(1, 1), Some(5.0));
    assert_eq!(focus.ordinal(12, 6), Some(10.0));
    assert_eq!(focus.ordinal(2, 0), None, "under a quarter usable");
    assert!(focus.ordinal_with_share(2, 0, 0.1).is_some());
    assert_eq!(focus.ordinal(3, 0), None, "no usable pixel");
    assert_eq!(focus.ordinal(13, 0), None, "outside the lattice");
    assert!((focus.share(2, 0) - 30.0 / 255.0).abs() < 1e-6);
    // Not usable: the reason, and nothing drawn.
    let refused = [record_bytes(
        0,
        0,
        9,
        u32::MAX,
        &focus_summary(false, 3, 299, "needs 6.35 GiB"),
    )];
    let focus = read_focus(&focus_file(dir.path(), &refused))
        .unwrap()
        .unwrap();
    assert_eq!(
        (focus.usable, focus.reason_code, focus.reason.as_str()),
        (false, 3, "needs 6.35 GiB")
    );
    assert_eq!(focus.ordinal(0, 0), None);
    // No field, a usable summary without its maps, or a torn summary: none.
    assert_eq!(read_focus(&focus_file(dir.path(), &[])).unwrap(), None);
    assert_eq!(
        read_focus(&focus_file(dir.path(), &field[..1])).unwrap(),
        None
    );
    let mut torn = field[0].clone();
    torn.truncate(torn.len() - 3);
    assert_eq!(read_focus(&focus_file(dir.path(), &[torn])).unwrap(), None);
    assert_eq!(read_focus(&dir.path().join("absent.strehl")).unwrap(), None);
}

/// The largest focus record (a 128 x 96 lattice) is within the framing limit
/// of the maps reader, which would otherwise stop reading the whole file.
#[test]
fn the_largest_focus_record_keeps_the_maps_reader_reading() {
    let mut bytes = header_bytes(&[([128, 96], [3504, 2336])], 3);
    bytes.extend(record_bytes(
        0,
        0,
        7,
        u32::MAX,
        &float_payload(0.0, 298.0, &[7; 128 * 96]),
    ));
    bytes.extend(record_bytes(
        2,
        0,
        0,
        5,
        &support_payload(&[true; 128 * 96]),
    ));
    let mut decoder = EvidenceDecoder::default();
    let mut out = Vec::new();
    decoder.feed(&bytes, &mut out);
    assert_eq!(
        (out.len(), decoder.skipped(), decoder.failure()),
        (1, 1, None)
    );
}

/// A preview's revision sample (P2's kind 6, `u32 folded, u16 preview_w,
/// u16 preview_h, u16 w, u16 h, f32 min, f32 max`, then `w x h` bytes) at
/// the 64 x 48 lattice, as P2's engine writes one per generation.
fn revision_sample(folded: u32) -> Vec<u8> {
    let mut out = folded.to_le_bytes().to_vec();
    for value in [512u16, 384, 64, 48] {
        out.extend(value.to_le_bytes());
    }
    out.extend(0f32.to_le_bytes());
    out.extend(1f32.to_le_bytes());
    out.extend([9u8; 64 * 48]);
    out
}

/// Every kind number is defined once and distinct; E5's are 7, 8 and 9.
#[test]
fn record_kinds_are_distinct() {
    let mut numbers = kind::ALL.to_vec();
    numbers.sort_unstable();
    numbers.dedup();
    assert_eq!(numbers, (0..10).collect::<Vec<u8>>());
    assert_eq!(
        [kind::FOCUS_DEPTH, kind::FOCUS_SHARE, kind::FOCUS_SUMMARY],
        [7, 8, 9]
    );
}

/// A file holding P2's revision samples (kind 6, frame 0 among them) and
/// E5's field reads both ways: the maps reader never returns a focus record
/// and stops for neither, and `read_focus` takes only kinds 7-9, so P2's
/// frame-0 sample is not read as a summary.
#[test]
fn revision_samples_and_the_focus_field_share_a_file() {
    let dir = tempfile::tempdir().unwrap();
    let depth = vec![127u8; 91];
    let share = vec![200u8; 91];
    let records = [
        record_bytes(0, 0, 6, 6, &revision_sample(1)),
        record_bytes(1, 0, 6, 7, &revision_sample(2)),
        record_bytes(0, 0, 9, u32::MAX - 2, &focus_summary(true, 0, 11, "")),
        record_bytes(0, 0, 7, u32::MAX - 1, &float_payload(0.0, 10.0, &depth)),
        record_bytes(0, 0, 8, u32::MAX, &float_payload(0.0, 1.0, &share)),
    ];
    let path = focus_file(dir.path(), &records);
    let bytes = std::fs::read(&path).unwrap();
    let mut decoder = EvidenceDecoder::default();
    let mut out = Vec::new();
    decoder.feed(&bytes, &mut out);
    assert_eq!(decoder.failure(), None);
    // Six records: the gate map, two samples, three focus records. A reader
    // that knows kind 6 returns the samples; one that does not skips them.
    assert_eq!(out.len() + decoder.skipped(), 6);
    assert!(decoder.skipped() >= 3, "the focus records are skipped");
    assert!(out.iter().all(|r| r.surface.sequence < u32::MAX as u64 - 2));
    let focus = read_focus(&path).unwrap().expect("the field");
    assert_eq!((focus.frames, focus.usable), (11, true));
    assert_eq!(focus.ordinal(0, 0), Some(5.0));
}

/// A preview's revision sample record (kind 6), taken at the lattice the
/// desktop's `compare` uses, by this test's own sampler.
pub(crate) fn sample_payload(
    folded: u32,
    size: [usize; 2],
    range: (f32, f32),
    full: &[u8],
) -> Vec<u8> {
    let [pw, ph] = size;
    let scale = (64.0 / pw as f64).min(48.0 / ph as f64).min(1.0);
    let (w, h) = (
        ((pw as f64 * scale).floor() as usize).max(1),
        ((ph as f64 * scale).floor() as usize).max(1),
    );
    let mut payload = folded.to_le_bytes().to_vec();
    for value in [pw, ph, w, h] {
        payload.extend((value as u16).to_le_bytes());
    }
    payload.extend(range.0.to_le_bytes());
    payload.extend(range.1.to_le_bytes());
    for y in 0..h {
        for x in 0..w {
            let sx = ((2 * x + 1) * pw / (2 * w)).min(pw - 1);
            let sy = ((2 * y + 1) * ph / (2 * h)).min(ph - 1);
            payload.push(full[sy * pw + sx]);
        }
    }
    payload
}

/// One live record: frame, level, kind, sequence, folded, size, range, bytes.
pub(crate) type LiveRecord = (u32, u8, u8, u32, u32, [usize; 2], (f32, f32), Vec<u8>);

/// A live file of `records`, by this test's own writer.
pub(crate) fn live_bytes(frames: u32, records: &[LiveRecord]) -> Vec<u8> {
    let mut bytes = b"STRHLIV1".to_vec();
    bytes.extend(LIVE_VERSION.to_le_bytes());
    bytes.extend(frames.to_le_bytes());
    bytes.extend((records.len() as u32).to_le_bytes());
    for (frame, level, kind, sequence, folded, size, range, pixels) in records {
        let mut payload = folded.to_le_bytes().to_vec();
        payload.extend((size[0] as u16).to_le_bytes());
        payload.extend((size[1] as u16).to_le_bytes());
        payload.extend(range.0.to_le_bytes());
        payload.extend(range.1.to_le_bytes());
        payload.extend_from_slice(pixels);
        bytes.extend(record_bytes(*frame, *level, *kind, *sequence, &payload));
    }
    bytes
}

pub(crate) fn preview_pixels(generation: usize, [w, h]: [usize; 2]) -> Vec<u8> {
    (0..w * h)
        .map(|i| ((i * 7 + i / w * 3 + generation * 11 * (i % 5)) % 251) as u8)
        .collect()
}

#[test]
fn stack_records_decode_as_averaging_maps_and_revision_samples() {
    let mut bytes = header_bytes(&[([13, 7], [900, 600])], 3);
    let sites: Vec<bool> = (0..91).map(|i| i % 3 == 0).collect();
    let mut averaging = 2u32.to_le_bytes().to_vec();
    averaging.extend(support_payload(&sites));
    bytes.extend(record_bytes(1, 0, 1, 4, &averaging));
    let full = preview_pixels(1, [300, 210]);
    bytes.extend(record_bytes(
        1,
        0,
        6,
        5,
        &sample_payload(2, [300, 210], (1.0, 9.0), &full),
    ));
    // A sample whose lattice disagrees with its preview is skipped.
    let mut wrong = sample_payload(2, [300, 210], (1.0, 9.0), &full);
    wrong[8] = 63;
    bytes.extend(record_bytes(1, 0, 6, 6, &wrong));
    // So is an averaging map that claims more accepted planes than exist.
    let mut beyond = 4u32.to_le_bytes().to_vec();
    beyond.extend(support_payload(&sites));
    bytes.extend(record_bytes(1, 0, 1, 7, &beyond));
    let mut out = Vec::new();
    let mut decoder = EvidenceDecoder::default();
    decoder.feed(&bytes, &mut out);
    assert_eq!((out.len(), decoder.skipped()), (2, 2));
    let map = &out[0];
    assert_eq!(map.role, Role::Averaging);
    assert_eq!(
        (map.surface.kind, map.surface.scope, map.surface.folded),
        (DiagnosticKind::Averaging, DiagnosticScope::Stack, 2)
    );
    assert_eq!(map.packed.as_ref().unwrap().on, 31);
    let sample = &out[1];
    assert_eq!(sample.role, Role::RevisionSample);
    assert_eq!((sample.surface.width, sample.surface.height), (64, 44));
    assert_eq!(
        (
            sample.surface.min,
            sample.surface.max,
            sample.surface.folded
        ),
        (1.0, 9.0, 2)
    );
}

#[test]
fn revision_samples_give_the_full_previews_revision_trace() {
    // The trace the desktop computes from whole previews, against the one
    // it computes from the engine's samples: the same summaries.
    let size = [300, 210];
    let mut full_field = crate::process_revision::RevisionField::default();
    let mut sampled = crate::process_revision::RevisionField::default();
    let mut decoder = EvidenceDecoder::default();
    let mut out = Vec::new();
    decoder.feed(&header_bytes(&[([13, 7], [900, 600])], 40), &mut out);
    for generation in 1..=30u32 {
        let pixels = preview_pixels(generation as usize, size);
        let range = (generation as f32, 400.0 + generation as f32);
        let preview = DiagnosticSurface {
            sequence: u64::from(generation) * 10,
            frame: generation as usize,
            level: 1,
            kind: DiagnosticKind::Preview,
            scope: DiagnosticScope::Stack,
            scale: DiagnosticScale::Linear,
            width: size[0],
            height: size[1],
            min: range.0,
            max: range.1,
            pixels: pixels.clone().into(),
            folded: generation as usize,
        };
        full_field.observe(&preview, [900, 600]);
        let payload = sample_payload(generation, size, range, &pixels);
        decoder.feed(
            &record_bytes(generation, 0, 6, generation * 10, &payload),
            &mut out,
        );
        let sample = out.pop().unwrap();
        sampled.observe(&sample.surface, [900, 600]);
    }
    let summary = |field: &crate::process_revision::RevisionField| {
        field
            .history()
            .iter()
            .map(|r| {
                (
                    r.sequence,
                    [r.from, r.to, r.from_frame, r.to_frame],
                    [r.changed_samples, r.total_samples],
                    r.range_dn.map(f32::to_bits),
                )
            })
            .collect::<Vec<_>>()
    };
    assert_eq!(summary(&full_field).len(), 29);
    assert!(
        summary(&full_field).iter().any(|r| r.2[0] > 0),
        "revisions must occur"
    );
    assert_eq!(summary(&sampled), summary(&full_field));
    let (a, b) = (full_field.latest().unwrap(), sampled.latest().unwrap());
    assert_eq!((a.width, a.height), (b.width, b.height));
    assert_eq!(
        a.signed_dn.iter().map(|v| v.to_bits()).collect::<Vec<_>>(),
        b.signed_dn.iter().map(|v| v.to_bits()).collect::<Vec<_>>()
    );
}

#[test]
fn the_live_file_is_read_whole_when_replaced_and_partial_files_are_refused() {
    let directory = crate::jobs::tests::TestDirectory::new("live-tail");
    let path = directory.path().join(LIVE_FILE_NAME);
    let mut tail = LiveTail::new(path.clone());
    assert!(tail.poll().is_none(), "no file yet");
    let preview = preview_pixels(3, [300, 210]);
    let first = live_bytes(
        5,
        &[
            (2, 0, 4, 8, 3, [13, 7], (-4.0, 6.0), vec![9; 91]),
            (2, 1, 5, 9, 3, [300, 210], (1.0, 9.0), preview.clone()),
        ],
    );
    std::fs::write(&path, &first).unwrap();
    let set = tail.poll().unwrap();
    assert_eq!(set.frames_total, 5);
    assert_eq!(set.surfaces.len(), 2);
    let coefficient = &set.surfaces[0];
    assert_eq!(
        (
            coefficient.kind,
            coefficient.scale,
            coefficient.folded,
            coefficient.min
        ),
        (
            DiagnosticKind::Coefficient,
            DiagnosticScale::Symmetric,
            3,
            -4.0
        )
    );
    let shown = &set.surfaces[1];
    assert_eq!(
        (shown.kind, shown.width, shown.height),
        (DiagnosticKind::Preview, 300, 210)
    );
    assert_eq!(&shown.pixels[..], &preview[..]);
    assert!(tail.poll().is_none(), "unchanged");
    // A newer generation replaces it whole.
    let second = live_bytes(
        5,
        &[(
            4,
            1,
            5,
            20,
            5,
            [300, 210],
            (1.0, 9.0),
            preview_pixels(5, [300, 210]),
        )],
    );
    std::fs::write(&path, &second).unwrap();
    assert_eq!(tail.poll().unwrap().surfaces[0].folded, 5);
    // A cut or miscounted file shows nothing, and is read again later.
    let mut miscounted = second.clone();
    miscounted[16] = 2;
    for broken in [&second[..second.len() - 1], &miscounted[..]] {
        assert!(decode_live(broken).is_err());
    }
    std::fs::write(&path, &second[..second.len() - 7]).unwrap();
    assert!(tail.poll().is_none());
    std::fs::write(&path, &first).unwrap();
    assert_eq!(tail.poll().unwrap().surfaces.len(), 2);
    assert!(read_live(&path).is_ok());
}
