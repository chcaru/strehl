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
    assert!(
        filed_maps.is_empty(),
        "the averaging map moved to the file too"
    );

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
    assert_eq!(records.len(), frames * 7 + 1);
    // Every plane map in the file equals its hex line: same identity, same
    // sequence and the same bytes (bits for support, min/max and bytes else).
    for (line, (frame, level, kind, sequence, payload)) in
        plain_maps.iter().zip(&records).take(frames * 7)
    {
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
    // The stack's averaging map follows as kind 1: its accepted count, then
    // the same bits, in the same stream.
    let (line, (frame, level, kind, sequence, payload)) =
        (plain_maps.last().unwrap(), records.last().unwrap());
    assert!(line.contains("kind=averaging"));
    assert_eq!((*frame, *level, *kind), (frames - 1, 0, 1));
    assert_eq!(field(line, "seq").parse::<u32>().unwrap(), *sequence);
    assert_eq!(payload[..4], (frames as u32).to_le_bytes());
    assert_eq!(payload[4..], pack_support(&hex_pixels(line))[..]);
}

/// The live side file read back: `(frame, level, kind, sequence, folded,
/// [w, h], min, max, bytes)` per record.
type LiveRecord = (usize, usize, u8, u32, u32, [usize; 2], f32, f32, Vec<u8>);

fn read_live(path: &Path) -> (usize, Vec<LiveRecord>) {
    let bytes = std::fs::read(path).unwrap();
    assert_eq!(&bytes[..8], b"STRHLIV1");
    let u32_at = |at: usize| u32::from_le_bytes(bytes[at..at + 4].try_into().unwrap());
    let u16_at = |at: usize| u16::from_le_bytes([bytes[at], bytes[at + 1]]) as usize;
    let f32_at = |at: usize| f32::from_le_bytes(bytes[at..at + 4].try_into().unwrap());
    assert_eq!(u32_at(8), LIVE_VERSION);
    let (frames, count) = (u32_at(12) as usize, u32_at(16) as usize);
    let mut at = 20;
    let mut records = Vec::new();
    while at < bytes.len() {
        let length = u32_at(at + 12) as usize;
        let p = at + 16;
        let size = [u16_at(p + 4), u16_at(p + 6)];
        assert_eq!(length, 16 + size[0] * size[1]);
        records.push((
            u32_at(at) as usize,
            bytes[at + 4] as usize,
            bytes[at + 5],
            u32_at(at + 8),
            u32_at(p),
            size,
            f32_at(p + 8),
            f32_at(p + 12),
            bytes[p + 16..p + length].to_vec(),
        ));
        at = p + length;
    }
    assert_eq!(records.len(), count);
    (frames, records)
}

#[test]
fn stack_maps_move_to_the_files_and_the_live_file_holds_the_newest_generation() {
    use strehl_core::pyramid::{BandMerge, FrameWorkspace, MergeConfig, level_sizes};
    let scratch = Scratch::new("stack");
    let cfg = MergeConfig {
        bands: 3,
        ..MergeConfig::default()
    };
    let (w, h, frames) = (600, 420, 5);
    let sizes = level_sizes(w, h, cfg.bands);
    let fold = |progress: &Progress| {
        let mut merge = BandMerge::new(w, h, 1, cfg);
        let mut workspace = FrameWorkspace::new(&sizes, 1);
        for frame in 0..frames {
            let pixels: Vec<f32> = (0..w * h)
                .map(|i| 100.0 + ((i * (frame + 3) + i / w * 7) % 97) as f32)
                .collect();
            workspace.next_frame();
            merge.add_frame(
                &[&pixels],
                &pixels,
                &vec![4.0; pixels.len()],
                &mut workspace,
            );
            progress.live_accumulator(None, &merge, frame);
        }
        progress.reconstruction(
            &[vec![1.0; w * h], vec![2.0; w * h], vec![3.0; w * h]],
            sizes[0],
            frames - 1,
            frames,
        );
    };
    let (plain, plain_lines) = Progress::captured(frames);
    fold(&plain);
    let (filed, filed_lines) = Progress::captured(frames);
    filed.begin_evidence(&sizes, Some(&scratch.0.join("result.tiff")));
    fold(&filed);
    let plain_lines = plain_lines.lock().unwrap();
    let filed_lines = filed_lines.lock().unwrap();
    let kinds = |lines: &[String], kind: &str| -> Vec<String> {
        lines
            .iter()
            .filter(|line| line.contains(&format!("kind={kind} ")))
            .cloned()
            .collect()
    };
    assert!(filed_lines.contains(&format!(
        "STREHL_UI_PROGRESS event=live-file path={LIVE_FILE_NAME} version={LIVE_VERSION}"
    )));
    // Only the one reconstruction stays in the log.
    for kind in ["averaging", "coefficient", "preview"] {
        assert_eq!(
            kinds(&plain_lines, kind).len(),
            frames * if kind == "preview" { 1 } else { sizes.len() }
        );
        assert!(kinds(&filed_lines, kind).is_empty(), "{kind}");
    }
    assert_eq!(
        kinds(&filed_lines, "reconstructed"),
        kinds(&plain_lines, "reconstructed")
    );

    // Every generation's averaging maps and preview sample, in the file.
    let (_, _, records) = read(&scratch.0.join(FILE_NAME));
    let averaging: Vec<_> = records.iter().filter(|r| r.2 == 1).collect();
    let plain_averaging = kinds(&plain_lines, "averaging");
    assert_eq!(averaging.len(), plain_averaging.len());
    for (record, line) in averaging.iter().zip(&plain_averaging) {
        assert_eq!(record.3, field(line, "seq").parse::<u32>().unwrap());
        assert_eq!(
            record.4[..4],
            field(line, "folded").parse::<u32>().unwrap().to_le_bytes()
        );
        assert_eq!(record.4[4..], pack_support(&hex_pixels(line))[..]);
    }
    let samples: Vec<_> = records.iter().filter(|r| r.2 == 6).collect();
    let plain_previews = kinds(&plain_lines, "preview");
    assert_eq!(samples.len(), frames);
    let mut changed = 0;
    for (record, line) in samples.iter().zip(&plain_previews) {
        let payload = &record.4;
        let u16_at = |at: usize| u16::from_le_bytes([payload[at], payload[at + 1]]) as usize;
        let (pw, ph) = (u16_at(4), u16_at(6));
        let (sw, sh) = (u16_at(8), u16_at(10));
        assert_eq!(pw, field(line, "width").parse::<usize>().unwrap());
        assert_eq!(ph, field(line, "height").parse::<usize>().unwrap());
        assert!(sw <= 64 && sh <= 48 && sw * sh == payload.len() - 20);
        assert_eq!(record.3, field(line, "seq").parse::<u32>().unwrap());
        assert_eq!(
            payload[12..16],
            field(line, "min").parse::<f32>().unwrap().to_le_bytes()
        );
        assert_eq!(
            payload[16..20],
            field(line, "max").parse::<f32>().unwrap().to_le_bytes()
        );
        // Each sample is the preview's own byte at the revision lattice.
        let full = hex_pixels(line);
        for y in 0..sh {
            for x in 0..sw {
                let sx = ((2 * x + 1) * pw / (2 * sw)).min(pw - 1);
                let sy = ((2 * y + 1) * ph / (2 * sh)).min(ph - 1);
                assert_eq!(payload[20 + y * sw + x], full[sy * pw + sx]);
            }
        }
        changed += usize::from(payload[20..] != samples[0].4[20..]);
    }
    assert!(changed > 0, "the samples follow a changing preview");

    // The live file: the newest generation only, byte for byte its maps.
    let (total, live) = read_live(&scratch.0.join(LIVE_FILE_NAME));
    assert_eq!(total, frames);
    assert!(!scratch.0.join(format!("{LIVE_FILE_NAME}.partial")).exists());
    let newest = |lines: &[String], kind: &str, level: usize| -> String {
        kinds(lines, kind)
            .into_iter()
            .rfind(|line| field(line, "level").parse::<usize>().unwrap() == level)
            .unwrap()
    };
    assert_eq!(live.len(), sizes.len() + 1);
    for record in &live {
        let (frame, level, kind, sequence, folded, size, min, max, bytes) = record;
        let name = if *kind == 4 { "coefficient" } else { "preview" };
        let line = newest(&plain_lines, name, *level);
        assert_eq!(*frame, frames - 1);
        assert_eq!(*folded as usize, frames);
        assert_eq!(*sequence, field(&line, "seq").parse::<u32>().unwrap());
        assert_eq!(size[0], field(&line, "width").parse::<usize>().unwrap());
        assert_eq!(*min, field(&line, "min").parse::<f32>().unwrap());
        assert_eq!(*max, field(&line, "max").parse::<f32>().unwrap());
        assert_eq!(*bytes, hex_pixels(&line));
    }
    assert_eq!(live.iter().filter(|r| r.2 == 5).count(), 1);
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
    assert_eq!(
        filed_lines.lock().unwrap().len(),
        2,
        "only the two files' names"
    );
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
