use super::*;
use strehl_core::pyramid::{FrameWorkspace, Hull, MergeConfig, level_sizes};

#[test]
fn dense_diagnostics_observe_real_coefficients_without_changing_the_lattice() {
    let (progress, lines) = Progress::captured(1);
    let size = LevelSize {
        width: 513,
        height: 387,
    };
    // Nonlinear coordinate pattern catches interpolation and transposition.
    let values: Vec<f32> = (0..size.pixels())
        .map(|i| {
            if ((i % size.width) * 17 + (i / size.width) * 31) % 11 < 5 {
                1.0
            } else {
                0.0
            }
        })
        .collect();
    progress.surface(
        0,
        0,
        "gate-support",
        "frame",
        "linear",
        1,
        size,
        |i| values[i],
        Some((0.0, 1.0)),
    );
    let lines = lines.lock().unwrap();
    let fields: std::collections::BTreeMap<_, _> = lines[0]
        .split_whitespace()
        .filter_map(|field| field.split_once('='))
        .collect();
    let width: usize = fields["width"].parse().unwrap();
    let height: usize = fields["height"].parse().unwrap();
    assert!(
        width > 64 && height > 48,
        "fixture must exercise the denser path"
    );
    assert!(width <= 128 && height <= 96);
    let bytes = fields["data"].as_bytes();
    assert_eq!(bytes.len(), width * height * 2);
    let mut on = 0;
    for y in 0..height {
        for x in 0..width {
            let sx = ((x as f64 + 0.5) * size.width as f64 / width as f64).floor() as usize;
            let sy = ((y as f64 + 0.5) * size.height as f64 / height as f64).floor() as usize;
            let expected = if values[sy * size.width + sx] > 0.0 {
                on += 1;
                b"ff"
            } else {
                b"00"
            };
            assert_eq!(
                &bytes[(y * width + x) * 2..(y * width + x + 1) * 2],
                expected
            );
        }
    }
    assert!(on > 0 && on < width * height);
}

#[test]
fn real_buffer_maps_are_bounded_and_keep_flat_support_distinct_from_signal() {
    let (progress, lines) = Progress::captured(41);
    let size = LevelSize {
        width: 16,
        height: 12,
    };
    let flat = vec![0.0; size.pixels()];
    let variance = vec![4.0; size.pixels()];
    let texture: Vec<_> = (0..size.pixels())
        .map(|i| if i % 2 == 0 { 20.0 } else { 0.0 })
        .collect();
    for frame in 0..41 {
        let tap = FrameTap::new(&progress, frame, 20);
        for level in 0..20 {
            tap.band(BandObservation {
                level,
                size,
                energy: Some(&texture),
                variance: Some(&variance),
                floor_multiplier: 2.0,
                weights: if frame == 0 { &flat } else { &texture },
            });
        }
    }
    let lines = lines.lock().unwrap();
    assert_eq!(lines.len(), 41 * 20 * 3);
    for frame in 0..41 {
        for level in 0..20 {
            for kind in ["focus-energy", "gate-floor", "gate-support"] {
                let needle = format!("frame={frame} level={level} kind={kind} ");
                assert_eq!(
                    lines.iter().filter(|line| line.contains(&needle)).count(),
                    1,
                    "every frame and scale must have its own measured {kind} map"
                );
            }
        }
    }
    assert!(lines.iter().all(|line| line.len() < 16 * 1024));
    let support = lines
        .iter()
        .find(|line| line.contains("frame=0 ") && line.contains("kind=gate-support "))
        .expect("flat control must be emitted");
    assert!(
        support
            .split("data=")
            .nth(1)
            .unwrap()
            .bytes()
            .all(|v| v == b'0')
    );
    assert!(
        lines.iter().any(|line| line.contains("kind=gate-support ")
            && line.split("data=").nth(1).unwrap().contains("ff")),
        "positive control must contain actual nonzero input weights"
    );
    assert!(
        lines
            .iter()
            .any(|line| line.contains("kind=gate-floor ") && line.contains("min=8e0 max=8e0")),
        "floor must read the caller's actual injected variance and multiplier"
    );
}

#[test]
fn disabled_observer_and_sparse_band_count_have_no_fictional_work() {
    let (mut progress, lines) = Progress::captured(10);
    progress.enabled = false;
    progress.merge_step(0, "decode", None, "started");
    FrameTap::new(&progress, 0, 4).phase(FoldPhase::FoldFinished(0));
    assert!(lines.lock().unwrap().is_empty());
    assert!(progress.diagnostics.lock().unwrap().bands.is_empty());
    progress.enabled = true;
    for frame in [2, 7] {
        FrameTap::new(&progress, frame, 4).phase(FoldPhase::FoldFinished(1));
    }
    let lines = lines.lock().unwrap();
    assert!(
        lines
            .iter()
            .any(|line| line.contains("event=band-work index=7 level=1 completed=2 total=10"))
    );
    assert!(
        !lines.iter().any(|line| line.contains("level=0")),
        "a refused/skipped frame cannot invent any band's completed fold"
    );
}

#[test]
fn coarse_preview_is_the_real_green_reconstruction_not_a_band_or_red_plane() {
    let (width, height) = (577, 385);
    let cfg = MergeConfig {
        bands: 4,
        hull: Hull::Unclamped,
        ..MergeConfig::default()
    };
    let sizes = level_sizes(width, height, cfg.bands);
    let red: Vec<_> = (0..width * height).map(|i| 20.0 + (i % 7) as f32).collect();
    let green_one: Vec<_> = (0..width * height)
        .map(|i| 200.0 + 80.0 * ((i % width) as f32 / 12.0).sin())
        .collect();
    let green_two: Vec<_> = (0..width * height)
        .map(|i| 300.0 + 60.0 * ((i / width) as f32 / 10.0).cos())
        .collect();
    let green: Vec<_> = green_one
        .iter()
        .zip(&green_two)
        .map(|(a, b)| 0.5 * (a + b))
        .collect();
    let mut merge = BandMerge::new(width, height, 4, cfg);
    let mut frame_workspace = FrameWorkspace::new(&sizes, 4);
    frame_workspace.next_frame();
    merge.add_frame(
        &[&red, &green_one, &green_two, &red],
        &green,
        &vec![9.0; width * height],
        &mut frame_workspace,
    );
    let preview = coarse_preview(&merge).expect("an actual retained level fits the viewport");
    assert_eq!(preview.level, 1);
    assert_eq!(
        preview.size,
        LevelSize {
            width: 289,
            height: 193
        }
    );
    assert_eq!(preview.frames, 1);
    assert!(preview.pixels.len() <= PREVIEW_WIDTH * PREVIEW_HEIGHT);
    // This oracle takes the original green samples down the independent
    // Gaussian-build path; it does not resolve or copy observer coefficients.
    let mut expected = Pyramid::zeros(&sizes);
    expected.build_gaussian(&green, &mut Workspace::new(&sizes));
    let error = preview
        .pixels
        .iter()
        .zip(expected.level(preview.level))
        .map(|(a, b)| (a - b).abs())
        .fold(0.0_f32, f32::max);
    assert!(
        error < 0.001,
        "single-frame reconstruction must match source green at its real coarse grid, error={error}"
    );
    let min = preview.pixels.iter().copied().fold(f32::INFINITY, f32::min);
    let max = preview
        .pixels
        .iter()
        .copied()
        .fold(f32::NEG_INFINITY, f32::max);
    assert!(
        min > 100.0 && max - min > 50.0,
        "the fixture must distinguish green from the dark red plane and from a flat placeholder"
    );
    let mut base_only = Pyramid::zeros(&sizes[preview.level..]);
    let last = base_only.levels() - 1;
    base_only
        .level_mut(last)
        .copy_from_slice(expected.level(expected.levels() - 1));
    let blurred = base_only.collapse(&mut Workspace::new(&sizes[preview.level..]));
    let distinct = preview
        .pixels
        .iter()
        .zip(blurred)
        .map(|(a, b)| (a - b).abs())
        .fold(0.0_f32, f32::max);
    assert!(
        distinct > 5.0,
        "coarser detail bands must materially contribute; this cannot pass with the old base-only image"
    );
}

#[test]
fn coarse_preview_skips_unbounded_and_empty_pyramids_instead_of_reconstructing_full_size() {
    let cfg = MergeConfig {
        bands: 0,
        ..MergeConfig::default()
    };
    let sizes = level_sizes(600, 400, 0);
    let mut merge = BandMerge::new(600, 400, 1, cfg);
    assert!(coarse_preview(&merge).is_none());
    let mut workspace = FrameWorkspace::new(&sizes, 1);
    workspace.next_frame();
    let flat = vec![50.0; 600 * 400];
    merge.add_frame(&[&flat], &flat, &vec![4.0; flat.len()], &mut workspace);
    assert!(
        coarse_preview(&merge).is_none(),
        "no retained level fits; a full-size observer allocation would violate the bound"
    );
}

#[test]
fn coarse_preview_is_bounded_on_the_wire_and_advances_inside_canonical_chunks() {
    let cfg = MergeConfig {
        bands: 2,
        ..MergeConfig::default()
    };
    let sizes = level_sizes(32, 24, cfg.bands);
    let mut merge = BandMerge::new(32, 24, 1, cfg);
    let mut workspace = FrameWorkspace::new(&sizes, 1);
    let pixels: Vec<_> = (0..32 * 24)
        .map(|index| 100.0 + (index % 21) as f32)
        .collect();
    let (progress, lines) = Progress::captured(100);
    for chunk in 0..100 {
        workspace.next_frame();
        merge.add_frame(
            &[&pixels],
            &pixels,
            &vec![4.0; pixels.len()],
            &mut workspace,
        );
        progress.live_accumulator(None, &merge, chunk);
        progress.accumulator(&merge, chunk, chunk, 100);
    }
    let lines = lines.lock().unwrap();
    let previews = lines
        .iter()
        .filter(|line| line.contains("kind=preview "))
        .collect::<Vec<_>>();
    assert_eq!(
        previews.len(),
        100,
        "every accepted frame must appear, including beyond the retired96-state cap"
    );
    for folded in 1..=100 {
        assert!(previews[folded - 1].contains(&format!("folded={folded} ")));
        for level in 0..sizes.len() {
            for kind in ["averaging", "coefficient"] {
                assert_eq!(
                    lines
                        .iter()
                        .filter(|line| {
                            line.contains(&format!("level={level} kind={kind} "))
                                && line.contains(&format!("folded={folded} "))
                        })
                        .count(),
                    1,
                    "the chunk boundary must not replay its last live generation"
                );
            }
        }
    }
    assert!(previews[0].contains("frame=0 "));
    assert!(previews.last().unwrap().contains("frame=99 "));
    assert!(previews[0].contains("folded=1 "));
    assert!(previews.last().unwrap().contains("folded=100 "));
    assert!(
        previews
            .iter()
            .all(|line| line.contains("scope=stack scale=linear"))
    );
    assert!(lines.iter().all(|line| line.len() < 512 * 1024));
    drop(lines);
    let (large, output) = Progress::captured(1);
    large.surface(
        0,
        3,
        "preview",
        "stack",
        "linear",
        1,
        LevelSize {
            width: 512,
            height: 384,
        },
        |index| index as f32,
        None,
    );
    let output = output.lock().unwrap();
    assert_eq!(output.len(), 1);
    assert!(output[0].contains("width=512 height=384 "));
    assert_eq!(
        output[0].split("data=").nth(1).unwrap().len(),
        512 * 384 * 2
    );
    assert!(
        output[0].len() > 128 * 1024 && output[0].len() < 512 * 1024,
        "exercise the real increased line-bound path"
    );
}

#[test]
fn refused_chunks_preserve_progress_without_inventing_new_accumulator_maps() {
    let cfg = MergeConfig {
        bands: 2,
        ..MergeConfig::default()
    };
    let sizes = level_sizes(32, 24, cfg.bands);
    let mut merge = BandMerge::new(32, 24, 1, cfg);
    let mut workspace = FrameWorkspace::new(&sizes, 1);
    let (progress, lines) = Progress::captured(3);
    let pixels: Vec<_> = (0..32 * 24)
        .map(|index| 100.0 + (index % 21) as f32)
        .collect();
    workspace.next_frame();
    merge.add_frame(
        &[&pixels],
        &pixels,
        &vec![4.0; pixels.len()],
        &mut workspace,
    );
    progress.frame_finished(0, true);
    progress.accumulator(&merge, 0, 0, 3);
    let first_len = lines.lock().unwrap().len();
    assert_eq!(merge.frames(), 1);

    // Actual caller behaviour for a wholly refused chunk: completed input
    // advances, but no frame is added to the canonical accumulator.
    progress.frame_finished(1, false);
    progress.accumulator(&merge, 1, 1, 3);
    assert_eq!(
        merge.frames(),
        1,
        "the refused fixture must leave the accepted accumulator unchanged"
    );
    {
        let counts = progress.counts.lock().unwrap();
        assert_eq!(
            counts.processed, 2,
            "the refused input must still count as processed"
        );
        assert_eq!(
            counts.accepted, 1,
            "the refused input must not count as accepted"
        );
    }
    {
        let lines = lines.lock().unwrap();
        let refused = &lines[first_len..];
        assert!(
            !refused.iter().any(|line| line.contains("kind=preview ")),
            "a new chunk index is not a new accepted image"
        );
        assert!(
            !refused
                .iter()
                .any(|line| line.contains("event=diagnostic ")),
            "refused-only work cannot replay retained evidence as a new map generation"
        );
        assert!(
            refused
                .iter()
                .any(|line| line.contains("event=frame-finished index=1 processed=2 accepted=1 ")),
            "the refusal must remain visible as actual processed work"
        );
    }

    workspace.next_frame();
    let next_pixels: Vec<_> = pixels.iter().map(|value| value + 20.0).collect();
    merge.add_frame(
        &[&next_pixels],
        &next_pixels,
        &vec![4.0; pixels.len()],
        &mut workspace,
    );
    progress.frame_finished(2, true);
    progress.accumulator(&merge, 2, 2, 3);
    let lines = lines.lock().unwrap();
    let previews: Vec<_> = lines
        .iter()
        .filter(|line| line.contains("kind=preview "))
        .collect();
    assert_eq!(
        previews.len(),
        2,
        "preview must resume when another frame really enters the accumulator"
    );
    assert!(previews[0].contains("folded=1 "));
    assert!(previews[1].contains("frame=2 ") && previews[1].contains("folded=2 "));
}

#[test]
fn preview_enabled_disabled_and_placebo_leave_final_float_hashes_identical() {
    use sha2::{Digest, Sha256};
    let (width, height) = (97, 65);
    let cfg = MergeConfig {
        bands: 3,
        ..MergeConfig::default()
    };
    let sizes = level_sizes(width, height, cfg.bands);
    let mut merges = std::array::from_fn::<_, 3, _>(|_| BandMerge::new(width, height, 1, cfg));
    let mut workspaces = std::array::from_fn::<_, 3, _>(|_| FrameWorkspace::new(&sizes, 1));
    let (enabled, real_lines) = Progress::captured(3);
    let (mut disabled, disabled_lines) = Progress::captured(3);
    disabled.enabled = false;
    let (mut placebo, placebo_lines) = Progress::captured(3);
    placebo.enabled = false;
    for frame in 0..3 {
        let pixels: Vec<_> = (0..width * height)
            .map(|index| {
                if frame == 0 {
                    100.0
                } else {
                    100.0 + ((index * 7 + frame * 13) % 73) as f32
                }
            })
            .collect();
        for (merge, workspace) in merges.iter_mut().zip(&mut workspaces) {
            workspace.next_frame();
            merge.add_frame(&[&pixels], &pixels, &vec![9.0; pixels.len()], workspace);
        }
        disabled.accumulator(&merges[0], frame, frame, 3);
        enabled.accumulator(&merges[1], frame, frame, 3);
        placebo.accumulator(&merges[2], frame, frame, 3);
        let preview = coarse_preview(&merges[1]).unwrap();
        let spread = preview
            .pixels
            .iter()
            .copied()
            .fold(f32::NEG_INFINITY, f32::max)
            - preview.pixels.iter().copied().fold(f32::INFINITY, f32::min);
        if frame == 0 {
            assert!(spread < 0.001, "flat placebo must remain flat");
        } else {
            assert!(
                spread > 5.0,
                "the later preview must actually change with measured stack content"
            );
        }
    }
    let hashes: Vec<_> = merges
        .iter()
        .map(|merge| {
            let mut hash = Sha256::new();
            for value in merge
                .finish(&mut Workspace::new(&sizes))
                .into_iter()
                .flatten()
            {
                hash.update(value.to_le_bytes());
            }
            hash.finalize()
                .iter()
                .map(|byte| format!("{byte:02x}"))
                .collect::<String>()
        })
        .collect();
    assert_eq!(
        hashes[0], hashes[1],
        "enabled observer must preserve final bytes"
    );
    assert_eq!(
        hashes[0], hashes[2],
        "disabled placebo must preserve final bytes"
    );
    assert!(disabled_lines.lock().unwrap().is_empty());
    assert!(placebo_lines.lock().unwrap().is_empty());
    assert_eq!(
        real_lines
            .lock()
            .unwrap()
            .iter()
            .filter(|line| line.contains("kind=preview "))
            .count(),
        3,
        "equality cannot pass by silently skipping the preview code"
    );
}

#[test]
fn live_preview_accrues_inside_uneven_chunks_without_changing_canonical_output_hashes() {
    use sha2::{Digest, Sha256};
    use std::collections::BTreeSet;
    let (width, height) = (43, 31);
    let cfg = MergeConfig {
        bands: 2,
        hull: Hull::Unclamped,
        ..MergeConfig::default()
    };
    let sizes = level_sizes(width, height, cfg.bands);
    for partitions in [[4, 1, 3], [1, 4, 3]] {
        let mut hashes = Vec::new();
        for mode in 0..3 {
            let (mut progress, lines) = Progress::captured(8);
            progress.enabled = mode == 1;
            let mut prefix: Option<BandMerge> = None;
            let mut current = BandMerge::new(width, height, 1, cfg);
            let mut workspace = FrameWorkspace::new(&sizes, 1);
            let mut frame = 0;
            let mut combines_prior_work = false;
            let mut includes_new_work = false;
            for (chunk, length) in partitions.into_iter().enumerate() {
                for _ in 0..length {
                    let pixels: Vec<_> = (0..width * height)
                        .map(|index| {
                            let x = index % width;
                            let y = index / width;
                            200.0
                                + if ((x + frame * 5) / (2 + frame % 3) + y / 4) % 2 == 0 {
                                    10.0 + frame as f32 * 8.0
                                } else {
                                    -10.0 - frame as f32 * 8.0
                                }
                        })
                        .collect();
                    workspace.next_frame();
                    current.add_frame(
                        &[&pixels],
                        &pixels,
                        &vec![9.0; pixels.len()],
                        &mut workspace,
                    );
                    progress.live_accumulator(prefix.as_ref(), &current, frame);
                    if mode == 1
                        && let Some(old) = prefix.as_ref()
                    {
                        let actual = coarse_preview_with(Some(old), &current).unwrap();
                        let mut physical = old.clone();
                        physical.absorb(&current);
                        let expected = coarse_preview(&physical).unwrap();
                        assert_eq!(actual.frames, frame + 1);
                        assert_eq!(
                            actual
                                .pixels
                                .iter()
                                .map(|v| v.to_bits())
                                .collect::<Vec<_>>(),
                            expected
                                .pixels
                                .iter()
                                .map(|v| v.to_bits())
                                .collect::<Vec<_>>(),
                            "the live image must represent the exact pending canonical union"
                        );
                        let current_only = coarse_preview(&current).unwrap();
                        let prefix_only = coarse_preview(old).unwrap();
                        combines_prior_work |= actual
                            .pixels
                            .iter()
                            .zip(current_only.pixels)
                            .any(|(a, b)| (a - b).abs() > 1.0);
                        includes_new_work |= actual
                            .pixels
                            .iter()
                            .zip(prefix_only.pixels)
                            .any(|(a, b)| (a - b).abs() > 1.0);
                    }
                    frame += 1;
                }
                if let Some(old) = prefix.as_mut() {
                    old.absorb(&current);
                } else {
                    prefix = Some(std::mem::replace(
                        &mut current,
                        BandMerge::new(width, height, 1, cfg),
                    ));
                }
                progress.accumulator(prefix.as_ref().unwrap(), frame - 1, chunk, partitions.len());
                current.reset_for_reuse();
            }
            let final_merge = prefix.unwrap();
            assert_eq!(final_merge.frames(), 8);
            let mut hash = Sha256::new();
            for value in final_merge
                .finish(&mut Workspace::new(&sizes))
                .into_iter()
                .flatten()
            {
                hash.update(value.to_le_bytes());
            }
            hashes.push(
                hash.finalize()
                    .iter()
                    .map(|byte| format!("{byte:02x}"))
                    .collect::<String>(),
            );
            let lines = lines.lock().unwrap();
            let previews: Vec<_> = lines
                .iter()
                .filter(|line| line.contains("kind=preview "))
                .collect();
            if mode == 1 {
                assert!(
                    combines_prior_work && includes_new_work,
                    "both prefix-only and current-only fake accrual must fail the fixture"
                );
                assert_eq!(
                    previews.len(),
                    8,
                    "one real image after every accepted fold, not just the three chunk boundaries"
                );
                for (index, line) in previews.iter().enumerate() {
                    assert!(line.contains(&format!("folded={} ", index + 1)));
                }
                let images: BTreeSet<_> = previews
                    .iter()
                    .map(|line| line.split("data=").nth(1).unwrap())
                    .collect();
                assert!(
                    images.len() >= 6,
                    "a repeated/static preview cannot pass even if its progress label advances"
                );
                assert!(
                    previews
                        .iter()
                        .take(partitions[0])
                        .all(|line| !line.contains("folded=0 "))
                );
            } else {
                assert!(
                    lines.is_empty(),
                    "disabled and placebo observers remain inert"
                );
            }
        }
        assert_eq!(
            hashes[0], hashes[1],
            "live preview changed canonical output bytes for {partitions:?}"
        );
        assert_eq!(
            hashes[0], hashes[2],
            "placebo output differs for {partitions:?}"
        );
    }
}

#[test]
fn every_accepted_state_is_emitted_immediately_even_when_all_later_inputs_refuse() {
    let cfg = MergeConfig {
        bands: 2,
        ..MergeConfig::default()
    };
    let sizes = level_sizes(32, 24, cfg.bands);
    let mut merge = BandMerge::new(32, 24, 1, cfg);
    let mut workspace = FrameWorkspace::new(&sizes, 1);
    let (progress, lines) = Progress::captured(259);
    for accepted in 0..2 {
        let pixels: Vec<_> = (0..32 * 24)
            .map(|index| 100.0 + ((index * (accepted + 1)) % 41) as f32)
            .collect();
        workspace.next_frame();
        merge.add_frame(
            &[&pixels],
            &pixels,
            &vec![4.0; pixels.len()],
            &mut workspace,
        );
        progress.live_accumulator(None, &merge, accepted);
    }
    assert_eq!(
        lines
            .lock()
            .unwrap()
            .iter()
            .filter(|line| line.contains("kind=preview "))
            .count(),
        2,
        "accepted count2 must be visible now, not at the end of a259-input job"
    );
    // All later inputs are refused: final canonical state still has two
    // accepted frames, despite finishing the259-input job.
    progress.accumulator(&merge, 258, 0, 1);
    let lines = lines.lock().unwrap();
    let previews: Vec<_> = lines
        .iter()
        .filter(|line| line.contains("kind=preview "))
        .collect();
    assert_eq!(previews.len(), 2);
    assert!(previews[0].contains("folded=1 "));
    assert!(
        previews[1].contains("folded=2 "),
        "final acceptance must not vanish because subsequent inputs were refused"
    );
    assert!(
        previews.iter().all(|line| !line.contains("folded=259 ")),
        "processed inputs cannot be invented as accepted image contributors"
    );
}

#[test]
fn every_image_and_scale_accumulates_across_refused_chunks_without_changing_output_bytes() {
    use sha2::{Digest, Sha256};
    use std::collections::{BTreeMap, BTreeSet};

    const TOTAL: usize = 109;
    const REFUSED: [usize; 6] = [3, 17, 39, 40, 97, 108];
    let (width, height) = (43, 31);
    let cfg = MergeConfig {
        bands: 2,
        hull: Hull::Unclamped,
        ..MergeConfig::default()
    };
    let sizes = level_sizes(width, height, cfg.bands);
    let variance = vec![9.0; width * height];
    let accepted_frames: Vec<_> = (0..TOTAL)
        .filter(|frame| !REFUSED.contains(frame))
        .collect();
    assert!(
        accepted_frames.len() > 96,
        "exercise every retired frame budget"
    );

    for partitions in [[39, 2, 68], [1, 57, 51]] {
        let mut hashes = Vec::new();
        for mode in 0..3 {
            let (mut progress, lines) = Progress::captured(TOTAL);
            progress.enabled = mode == 1;
            let mut prefix: Option<BandMerge> = None;
            let mut current = BandMerge::new(width, height, 1, cfg);
            let mut workspace = FrameWorkspace::new(&sizes, 1);
            let mut frame = 0;
            let mut accepted = 0;
            let mut saw_refused_only_chunk = false;

            for (chunk, length) in partitions.into_iter().enumerate() {
                let before_chunk = accepted;
                for _ in 0..length {
                    progress.frame_started(frame);
                    progress.merge_step(frame, "decode", None, "started");
                    progress.merge_step(frame, "decode", None, "finished");
                    if REFUSED.contains(&frame) {
                        progress.merge_step(frame, "gather", None, "skipped");
                        progress.frame_finished(frame, false);
                        frame += 1;
                        continue;
                    }
                    // Start with a truly flat control. Later captures change
                    // spatial frequency, phase and contrast, so a repeated
                    // photograph with a new count cannot satisfy this fixture.
                    let pixels: Vec<_> = (0..width * height)
                        .map(|index| {
                            if frame == 0 {
                                return 200.0;
                            }
                            let (x, y) = (index % width, index / width);
                            200.0
                                + if ((x + frame * 5) / (2 + frame % 3) + y / 4) % 2 == 0 {
                                    10.0 + frame as f32 * 1.5
                                } else {
                                    -10.0 - frame as f32 * 1.5
                                }
                        })
                        .collect();
                    workspace.next_frame();
                    if let Some(observer) = progress.observer() {
                        current.add_frame_with_gain_observed(
                            &[&pixels],
                            &pixels,
                            &variance,
                            None,
                            &mut workspace,
                            &FrameTap::new(observer, frame, sizes.len()),
                        );
                    } else {
                        current.add_frame_with_gain(
                            &[&pixels],
                            &pixels,
                            &variance,
                            None,
                            &mut workspace,
                        );
                    }
                    accepted += 1;
                    progress.frame_finished(frame, true);
                    let start = lines.lock().unwrap().len();
                    progress.live_accumulator(prefix.as_ref(), &current, frame);
                    if mode == 1 {
                        // Independently materialize the *accumulator union*,
                        // never an aligned frame, and compare all wire samples.
                        // This rejects either prefix-only or current-only maps.
                        let mut physical = prefix
                            .clone()
                            .unwrap_or_else(|| BandMerge::new(width, height, 1, cfg));
                        physical.absorb(&current);
                        let (expected, expected_lines) = Progress::captured(TOTAL);
                        expected.accumulator(&physical, frame, chunk, partitions.len());
                        let actual = lines.lock().unwrap();
                        let expected = expected_lines.lock().unwrap();
                        let without_sequence = |line: &String| {
                            line.split_whitespace()
                                .filter(|field| !field.starts_with("seq="))
                                .collect::<Vec<_>>()
                                .join(" ")
                        };
                        assert_eq!(
                            actual[start..]
                                .iter()
                                .map(without_sequence)
                                .collect::<Vec<_>>(),
                            expected.iter().map(without_sequence).collect::<Vec<_>>(),
                            "every live map and photograph must describe the actual accepted union at input{frame}"
                        );
                        assert_eq!(physical.frames() as usize, accepted);
                    }
                    frame += 1;
                }
                saw_refused_only_chunk |= accepted == before_chunk;
                if let Some(old) = prefix.as_mut() {
                    old.absorb(&current);
                } else {
                    prefix = Some(std::mem::replace(
                        &mut current,
                        BandMerge::new(width, height, 1, cfg),
                    ));
                }
                let before_boundary = lines.lock().unwrap().len();
                progress.accumulator(prefix.as_ref().unwrap(), frame - 1, chunk, partitions.len());
                assert_eq!(
                    lines.lock().unwrap().len(),
                    before_boundary,
                    "a canonical boundary cannot duplicate the last accepted generation"
                );
                current.reset_for_reuse();
            }
            assert_eq!(frame, TOTAL);
            assert_eq!(accepted, accepted_frames.len());
            if partitions == [39, 2, 68] {
                assert!(
                    saw_refused_only_chunk,
                    "the refusal-only chunk must actually occur"
                );
            }
            let mut hash = Sha256::new();
            for value in prefix
                .unwrap()
                .finish(&mut Workspace::new(&sizes))
                .into_iter()
                .flatten()
            {
                hash.update(value.to_le_bytes());
            }
            hashes.push(hash.finalize().to_vec());

            let lines = lines.lock().unwrap();
            if mode != 1 {
                assert!(lines.is_empty(), "off and placebo modes must remain inert");
                continue;
            }
            let mut maps = BTreeMap::new();
            let mut previews = Vec::new();
            for line in lines
                .iter()
                .filter(|line| line.contains("event=diagnostic "))
            {
                let fields: BTreeMap<_, _> = line
                    .split_whitespace()
                    .filter_map(|field| field.split_once('='))
                    .collect();
                let source: usize = fields["frame"].parse().unwrap();
                let level: usize = fields["level"].parse().unwrap();
                let folded: usize = fields["folded"].parse().unwrap();
                let kind = fields["kind"];
                *maps.entry((source, level, kind, folded)).or_insert(0) += 1;
                if kind == "preview" {
                    previews.push((source, folded, fields["data"]));
                }
            }
            for (position, &source) in accepted_frames.iter().enumerate() {
                for level in 0..sizes.len() {
                    let mut kinds = vec![
                        ("gate-support", 1),
                        ("averaging", position + 1),
                        ("coefficient", position + 1),
                    ];
                    if level < cfg.bands {
                        kinds.extend([("focus-energy", 1), ("gate-floor", 1)]);
                    }
                    for (kind, folded) in kinds {
                        assert_eq!(
                            maps.get(&(source, level, kind, folded)),
                            Some(&1),
                            "missing or repeated {kind} at input{source}/scale{level}/accepted{folded}"
                        );
                    }
                }
            }
            assert!(
                maps.keys()
                    .all(|(source, _, _, _)| !REFUSED.contains(source)),
                "refused inputs cannot own maps of invented folds"
            );
            let identities: Vec<_> = previews
                .iter()
                .map(|&(source, folded, _)| (source, folded))
                .collect();
            let expected: Vec<_> = accepted_frames
                .iter()
                .enumerate()
                .map(|(position, &source)| (source, position + 1))
                .collect();
            assert_eq!(
                identities, expected,
                "every accepted input must immediately produce one photograph"
            );
            let distinct: BTreeSet<_> = previews.iter().map(|preview| preview.2).collect();
            assert!(
                distinct.len() > 32,
                "the fixture must defeat a static photograph and retired32-frame sampling"
            );
            assert!(
                previews[0].2.bytes().all(|byte| byte == b'0'),
                "the flat control cannot invent texture"
            );
            let static_control: BTreeSet<_> = previews.iter().map(|_| previews[0].2).collect();
            assert!(
                static_control.len() <= 32,
                "the liveness witness must reject repeated content"
            );
            assert_ne!(
                identities.iter().step_by(7).copied().collect::<Vec<_>>(),
                expected,
                "the reported seven-input cadence must fail the identity criterion"
            );
        }
        assert_eq!(
            hashes[0], hashes[1],
            "every-frame observers changed final bytes for {partitions:?}"
        );
        assert_eq!(
            hashes[0], hashes[2],
            "placebo changed final bytes for {partitions:?}"
        );
    }
}
