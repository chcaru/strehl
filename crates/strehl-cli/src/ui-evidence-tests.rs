use super::*;
use crate::ui_progress::{FrameTap, Progress, lattice};
use strehl_core::pyramid::{BandObservation, LevelSize, MergeObserver};

struct Scratch(PathBuf);
impl Scratch {
    fn new(label: &str) -> Self {
        let path = std::env::temp_dir().join(format!(
            "strehl-evidence-{label}-{}-{}",
            std::process::id(),
            std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .unwrap()
                .as_nanos()
        ));
        std::fs::create_dir_all(&path).unwrap();
        Self(path)
    }
}
impl Drop for Scratch {
    fn drop(&mut self) {
        let _ = std::fs::remove_dir_all(&self.0);
    }
}

/// One record read back: `(frame, level, kind, sequence, payload)`.
type Record = (usize, usize, u8, u32, Vec<u8>);

/// An independent reading of the documented format: header lattices, frames
/// and records.
fn read(path: &Path) -> (Vec<[usize; 2]>, usize, Vec<Record>) {
    let bytes = std::fs::read(path).unwrap();
    assert_eq!(&bytes[..8], b"STRHEVD1");
    let u32_at = |at: usize| u32::from_le_bytes(bytes[at..at + 4].try_into().unwrap());
    assert_eq!(u32_at(8), VERSION);
    let levels = u32_at(12) as usize;
    let lattices = (0..levels)
        .map(|k| {
            let at = 16 + 12 * k;
            [
                u16::from_le_bytes([bytes[at], bytes[at + 1]]) as usize,
                u16::from_le_bytes([bytes[at + 2], bytes[at + 3]]) as usize,
            ]
        })
        .collect();
    let mut at = 16 + 12 * levels;
    let frames = u32_at(at) as usize;
    at += 4;
    let mut records = Vec::new();
    while at < bytes.len() {
        let length = u32_at(at + 12) as usize;
        assert_eq!(&bytes[at + 6..at + 8], [0, 0], "reserved");
        records.push((
            u32_at(at) as usize,
            bytes[at + 4] as usize,
            bytes[at + 5],
            u32_at(at + 8),
            bytes[at + 16..at + 16 + length].to_vec(),
        ));
        at += 16 + length;
    }
    assert_eq!(at, bytes.len(), "whole records only");
    (lattices, frames, records)
}

fn hex_pixels(line: &str) -> Vec<u8> {
    let data = line
        .split_whitespace()
        .find_map(|field| field.strip_prefix("data="))
        .unwrap();
    (0..data.len() / 2)
        .map(|i| u8::from_str_radix(&data[2 * i..2 * i + 2], 16).unwrap())
        .collect()
}

fn field<'a>(line: &'a str, name: &str) -> &'a str {
    line.split_whitespace()
        .find_map(|part| part.strip_prefix(name)?.strip_prefix('='))
        .unwrap()
}

#[test]
fn float_maps_are_kept_for_at_most_384_planes_spread_evenly() {
    for total in [1, 2, 383, 384] {
        assert!((0..total).all(|frame| float_kept(frame, total)));
    }
    for total in [385, 1444, 6000] {
        let kept: Vec<usize> = (0..total).filter(|&f| float_kept(f, total)).collect();
        assert_eq!(kept.len(), MAX_FLOAT_PLANES, "{total}");
        assert_eq!((kept[0], *kept.last().unwrap()), (0, total - 1));
        let gaps: Vec<usize> = kept.windows(2).map(|w| w[1] - w[0]).collect();
        let (low, high) = (*gaps.iter().min().unwrap(), *gaps.iter().max().unwrap());
        assert!(high - low <= 1, "{total}: gaps {low}..{high} are not even");
    }
    assert!(!float_kept(1444, 1444));
}

#[test]
fn writer_refuses_records_its_header_does_not_describe_and_joins_one_geometry() {
    let scratch = Scratch::new("writer");
    let header = Header {
        levels: vec![([13, 7], [900, 600]), ([7, 4], [450, 300])],
        frames: 3,
    };
    let (mut writer, opened) = Writer::open(&scratch.0, header.clone()).unwrap();
    assert_eq!(opened, Opened::Created);
    assert!(writer.append(2, 1, Kind::GateSupport, 1, &[0; 4]));
    assert!(!writer.append(3, 1, Kind::GateSupport, 2, &[0; 4]), "frame");
    assert!(!writer.append(0, 2, Kind::GateSupport, 3, &[0; 4]), "level");
    assert!(
        !writer.append(0, 0, Kind::GateSupport, 4, &[0; 11]),
        "payload"
    );
    assert!(
        !writer.append(0, 1, Kind::FocusEnergy, 5, &[0; 28]),
        "float payload"
    );
    assert!(writer.append(0, 1, Kind::FocusEnergy, 6, &[0; 36]));
    drop(writer);
    // A later pass of the same geometry appends; another geometry cannot.
    let (mut joined, opened) = Writer::open(&scratch.0, header.clone()).unwrap();
    assert_eq!(opened, Opened::Joined);
    assert!(joined.append(1, 0, Kind::GateSupport, 7, &[0xff; 12]));
    let mut other = header.clone();
    other.frames = 4;
    assert!(Writer::open(&scratch.0, other).is_err());
    drop(joined);
    let (lattices, frames, records) = read(&scratch.0.join(FILE_NAME));
    assert_eq!((lattices, frames), (vec![[13, 7], [7, 4]], 3));
    let identities: Vec<_> = records
        .iter()
        .map(|(f, l, k, s, p)| (*f, *l, *k, *s, p.len()))
        .collect();
    assert_eq!(
        identities,
        [(2, 1, 0, 1, 4), (0, 1, 2, 6, 36), (1, 0, 0, 7, 12)]
    );
}

/// The same observed bands, through a pass with and without the file.
fn observe(progress: &Progress, frames: usize, sizes: &[LevelSize]) {
    for frame in 0..frames {
        let tap = FrameTap::new(progress, frame, sizes.len());
        for (level, &size) in sizes.iter().enumerate() {
            let n = size.pixels();
            let weights: Vec<f32> = (0..n)
                .map(|i| {
                    if (i * 7 + frame * 3 + level) % 5 < 2 {
                        0.25
                    } else {
                        0.0
                    }
                })
                .collect();
            let energy: Vec<f32> = (0..n)
                .map(|i| (i % 97) as f32 * 3.5 + frame as f32)
                .collect();
            let variance: Vec<f32> = (0..n).map(|i| 1.0 + (i % 13) as f32).collect();
            let base = level + 1 == sizes.len();
            tap.band(BandObservation {
                level,
                size,
                energy: (!base).then_some(&energy[..]),
                variance: (!base).then_some(&variance[..]),
                #[cfg(feature = "temporal-energy")]
                absolute_floor: None,
                floor_multiplier: 2.0,
                weights: &weights,
            });
        }
    }
    // A stack map stays in the log either way.
    progress.surface(
        frames - 1,
        0,
        "averaging",
        "stack",
        "linear",
        frames,
        sizes[0],
        |i| (i % 2) as f32,
        Some((0.0, 1.0)),
    );
}

#[test]
fn the_file_carries_the_hex_lines_maps_byte_for_byte_and_the_log_keeps_the_rest() {
    let scratch = Scratch::new("equivalence");
    let sizes = [
        LevelSize {
            width: 513,
            height: 387,
        },
        LevelSize {
            width: 257,
            height: 194,
        },
        LevelSize {
            width: 129,
            height: 97,
        },
    ];
    let frames = 4;
    let (plain, plain_lines) = Progress::captured(frames);
    observe(&plain, frames, &sizes);
    let (filed, filed_lines) = Progress::captured(frames);
    filed.begin_evidence(&sizes, Some(&scratch.0.join("result.partial.tiff")));
    observe(&filed, frames, &sizes);

    let plain_lines = plain_lines.lock().unwrap();
    let filed_lines = filed_lines.lock().unwrap();
    assert_eq!(
        filed_lines[0],
        "STREHL_UI_PROGRESS event=evidence-file path=evidence.strehl version=1"
    );
    let maps = |lines: &[String]| -> Vec<String> {
        lines
            .iter()
            .filter(|line| line.contains("event=diagnostic "))
            .cloned()
            .collect()
    };
    let (plain_maps, filed_maps) = (maps(&plain_lines), maps(&filed_lines));
    // Per frame: 3 gate-support, 2 focus-energy, 2 gate-floor; one stack map.
    assert_eq!(plain_maps.len(), frames * 7 + 1);
    assert_eq!(filed_maps.len(), 1, "only the stack map stays in the log");
    assert!(filed_maps[0].contains("kind=averaging"));

    let (lattices, total, records) = read(&scratch.0.join(FILE_NAME));
    assert_eq!(total, frames);
    assert_eq!(
        lattices,
        sizes.iter().map(|&s| lattice(s)).collect::<Vec<_>>()
    );
    assert_eq!(
        lattices[0],
        [127, 96],
        "the aspect-preserving lattice, not 128 x 96"
    );
    assert_eq!(records.len(), frames * 7);
    // Every plane map in the file equals its hex line: same identity, same
    // sequence and the same bytes (bits for support, min/max and bytes else).
    for (line, (frame, level, kind, sequence, payload)) in plain_maps.iter().zip(&records) {
        assert_eq!(field(line, "frame").parse::<usize>().unwrap(), *frame);
        assert_eq!(field(line, "level").parse::<usize>().unwrap(), *level);
        assert_eq!(field(line, "seq").parse::<u32>().unwrap(), *sequence);
        let pixels = hex_pixels(line);
        match field(line, "kind") {
            "gate-support" => {
                assert_eq!(*kind, 0);
                assert_eq!(*payload, pack_support(&pixels));
                assert!(pixels.contains(&255) && pixels.contains(&0));
            }
            name => {
                assert_eq!(*kind, if name == "focus-energy" { 2 } else { 3 });
                let min: f32 = field(line, "min").parse().unwrap();
                let max: f32 = field(line, "max").parse().unwrap();
                assert_eq!(payload[..4], min.to_le_bytes());
                assert_eq!(payload[4..8], max.to_le_bytes());
                assert_eq!(payload[8..], pixels[..]);
            }
        }
    }
    // The stack map's sequence follows the plane maps', as one stream.
    assert_eq!(
        field(&filed_maps[0], "seq").parse::<u32>().unwrap(),
        records.last().unwrap().3 + 1
    );
}

#[test]
fn gpu_maps_are_the_cpu_observers_maps_in_either_destination() {
    let sizes = [
        LevelSize {
            width: 300,
            height: 200,
        },
        LevelSize {
            width: 150,
            height: 100,
        },
    ];
    // What the CPU observer emits for these weights ...
    let weights = |level: usize, size: LevelSize| -> Vec<f32> {
        (0..size.pixels())
            .map(|i| {
                if (i / 3 + level).is_multiple_of(4) {
                    1.5
                } else {
                    0.0
                }
            })
            .collect()
    };
    let (cpu, cpu_lines) = Progress::captured(2);
    for (level, &size) in sizes.iter().enumerate() {
        let w = weights(level, size);
        cpu.surface(
            1,
            level,
            "gate-support",
            "frame",
            "linear",
            1,
            size,
            |i| {
                if w[i] > 0.0 { 1.0 } else { 0.0 }
            },
            Some((0.0, 1.0)),
        );
    }
    // ... and the GPU fold's bits for the same weights, sampled as the
    // device kernel samples them.
    let bits: Vec<Vec<u8>> = sizes
        .iter()
        .enumerate()
        .map(|(level, &size)| {
            let [lw, lh] = lattice(size);
            let w = weights(level, size);
            let mut bits = vec![0u8; (lw * lh).div_ceil(8)];
            for s in 0..lw * lh {
                let sx = ((2 * (s % lw) + 1) * size.width / (2 * lw)).min(size.width - 1);
                let sy = ((2 * (s / lw) + 1) * size.height / (2 * lh)).min(size.height - 1);
                if w[sy * size.width + sx] > 0.0 {
                    bits[s / 8] |= 1 << (s % 8);
                }
            }
            bits
        })
        .collect();
    let (gpu, gpu_lines) = Progress::captured(2);
    gpu.gpu_support(1, &bits, &sizes);
    assert_eq!(*gpu_lines.lock().unwrap(), *cpu_lines.lock().unwrap());
    // With a file, the same bits are its records.
    let scratch = Scratch::new("gpu");
    let (filed, filed_lines) = Progress::captured(2);
    filed.begin_evidence(&sizes, Some(&scratch.0.join("out.tiff")));
    filed.gpu_support(1, &bits, &sizes);
    assert_eq!(filed_lines.lock().unwrap().len(), 1, "only the file's name");
    let (_, _, records) = read(&scratch.0.join(FILE_NAME));
    for (level, record) in records.iter().enumerate() {
        assert_eq!((record.0, record.1, record.2), (1, level, 0));
        assert_eq!(record.4, bits[level]);
        assert_eq!(
            record.4,
            pack_support(&hex_pixels(&cpu_lines.lock().unwrap()[level]))
        );
    }
}

#[test]
fn a_disabled_or_outputless_pass_writes_no_file() {
    let scratch = Scratch::new("disabled");
    let sizes = [LevelSize {
        width: 8,
        height: 6,
    }];
    let (off, lines) = Progress::captured_enabled(false);
    off.begin_evidence(&sizes, Some(&scratch.0.join("out.tiff")));
    off.gpu_support(0, &[vec![0xff; 6]], &sizes);
    assert!(lines.lock().unwrap().is_empty());
    let (on, lines) = Progress::captured(1);
    on.begin_evidence(&sizes, None);
    assert!(lines.lock().unwrap().is_empty());
    assert!(!scratch.0.join(FILE_NAME).exists());
}

#[test]
fn unplaced_frames_are_named_with_a_single_token_reason() {
    use strehl_core::warpmap::{FrameWarp, Provenance, StackIdentity, WarpMap};
    let reason = "outside reference's measured edge component (gap = 3)";
    let warps = WarpMap::new(
        Provenance {
            stack: StackIdentity::from_entries("generated", &[("a", 1), ("b", 2), ("c", 3)]),
            strategy: "generated".into(),
            heldout_px: None,
            cycle_floor_px: None,
            reference: 0,
            note: "observer control".into(),
        },
        strehl_core::plane::PlaneGeometry {
            width: 8,
            height: 6,
        },
        strehl_core::align::Resampler::CatmullRom,
        vec![
            FrameWarp::Placed(strehl_core::align::Similarity::IDENTITY),
            FrameWarp::Refused(reason.into()),
            FrameWarp::Refused("   ".into()),
        ],
    );
    let (progress, lines) = Progress::captured(3);
    progress.unplaced_frames(&warps);
    assert_eq!(
        *lines.lock().unwrap(),
        [
            "STREHL_UI_PROGRESS event=frame-unplaced frame=1 \
             reason=outside-reference_s-measured-edge-component-(gap---3) total=3",
            "STREHL_UI_PROGRESS event=frame-unplaced frame=2 reason=unstated total=3",
        ]
    );
    let (off, lines) = Progress::captured_enabled(false);
    off.unplaced_frames(&warps);
    assert!(lines.lock().unwrap().is_empty());
}

/// The focus field joins the file the render created (its own header, even
/// when the caller's differs), after every plane map, at level 0's lattice
/// with the largest sequences; without a render file it makes one. Records
/// the format cannot hold are refused whole.
#[test]
fn focus_records_join_the_render_file_with_the_last_sequences() {
    let scratch = Scratch::new("focus");
    let header = Header {
        levels: vec![([13, 7], [900, 600]), ([7, 4], [450, 300])],
        frames: 3,
    };
    let (mut writer, _) = Writer::open(&scratch.0, header.clone()).unwrap();
    assert!(writer.append(2, 1, Kind::GateSupport, 9, &[0; 4]));
    drop(writer);
    let other = Header {
        levels: vec![([5, 5], [50, 50])],
        frames: 3,
    };
    let path = write_focus(&scratch.0, other.clone(), |lattice| {
        assert_eq!(lattice, [13, 7], "the render's level 0");
        vec![
            (Kind::FocusSummary, vec![1; 40]),
            (Kind::FocusDepth, vec![0; 8 + 91]),
            (Kind::FocusShare, vec![0; 8 + 91]),
        ]
    })
    .unwrap();
    let (lattices, _, records) = read(&path);
    assert_eq!(lattices, vec![[13, 7], [7, 4]]);
    let identities: Vec<_> = records
        .iter()
        .map(|(f, l, k, s, p)| (*f, *l, *k, *s, p.len()))
        .collect();
    assert_eq!(
        identities,
        [
            (2, 1, 0, 9, 4),
            (0, 0, 6, u32::MAX - 2, 40),
            (0, 0, 4, u32::MAX - 1, 99),
            (0, 0, 5, u32::MAX, 99),
        ]
    );
    // Every payload fits the framing limit of readers that predate them.
    assert!(records.iter().all(|r| r.4.len() <= 8 + 128 * 96));
    // A depth map of another lattice is refused, and nothing is written.
    let before = std::fs::metadata(&path).unwrap().len();
    assert!(
        write_focus(&scratch.0, other.clone(), |_| vec![
            (Kind::FocusSummary, vec![1; 40]),
            (Kind::FocusDepth, vec![0; 8 + 25]),
        ])
        .is_err()
    );
    assert!(
        write_focus(&scratch.0, other.clone(), |_| vec![(
            Kind::FocusSummary,
            vec![0; MAX_SUMMARY_BYTES + 1]
        )])
        .is_err()
    );
    assert_eq!(std::fs::metadata(&path).unwrap().len(), before);
    // A folder this process made no file in gets one with the caller's grid.
    let fresh = Scratch::new("focus-fresh");
    let path = write_focus(&fresh.0, other, |lattice| {
        assert_eq!(lattice, [5, 5]);
        vec![(Kind::FocusSummary, vec![0; 66])]
    })
    .unwrap();
    let (lattices, frames, records) = read(&path);
    assert_eq!((lattices, frames, records.len()), (vec![[5, 5]], 3, 1));
}
