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
