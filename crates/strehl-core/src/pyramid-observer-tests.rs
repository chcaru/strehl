use super::*;
use crate::pyramid::{FrameWorkspace, Hull, MergeConfig, Pyramid, Workspace, level_sizes};
use std::sync::Mutex;

#[derive(Default)]
struct Recorder {
    phases: Mutex<Vec<FoldPhase>>,
    active: Mutex<Vec<(usize, usize)>>,
}
impl MergeObserver for Recorder {
    fn phase(&self, phase: FoldPhase) {
        self.phases.lock().unwrap().push(phase);
    }
    fn band(&self, band: BandObservation<'_>) {
        assert_eq!(band.weights.len(), band.size.pixels());
        if let Some(energy) = band.energy {
            assert_eq!(energy.len(), band.weights.len());
        }
        self.active.lock().unwrap().push((
            band.level,
            band.weights.iter().filter(|v| **v > 0.0).count(),
        ));
    }
}

#[test]
fn observer_flat_control_and_real_band_work_cannot_change_output_bits() {
    // Flat input must produce zero selected support before textured input is
    // inspected. This validates observations, not the injected calibration.
    let (width, height) = (73, 51);
    let cfg = MergeConfig {
        bands: 3,
        hull: Hull::Unclamped,
        ..MergeConfig::default()
    };
    let sizes = level_sizes(width, height, cfg.bands);
    let mut plain = BandMerge::new(width, height, 1, cfg);
    let mut observed = BandMerge::new(width, height, 1, cfg);
    let mut placebo = BandMerge::new(width, height, 1, cfg);
    let mut pws = FrameWorkspace::new(&sizes, 1);
    let mut ows = FrameWorkspace::new(&sizes, 1);
    let mut xws = FrameWorkspace::new(&sizes, 1);
    let variance = vec![9.0; width * height];
    let recorder = Recorder::default();
    for frame in 0..3 {
        let pixels: Vec<_> = (0..width * height)
            .map(|i| {
                if frame == 0 {
                    100.0
                } else {
                    100.0
                        + if (i % width / 3 + i / width / 4 + frame) % 2 == 0 {
                            80.0
                        } else {
                            -80.0
                        }
                }
            })
            .collect();
        for ws in [&mut pws, &mut ows, &mut xws] {
            ws.next_frame();
        }
        plain.add_frame_with_gain(&[&pixels], &pixels, &variance, None, &mut pws);
        observed.add_frame_with_gain_observed(
            &[&pixels],
            &pixels,
            &variance,
            None,
            &mut ows,
            &recorder,
        );
        // The placebo is the exact disabled entry point, not a second merge.
        placebo.add_frame_with_gain(&[&pixels], &pixels, &variance, None, &mut xws);
        if frame == 0 {
            assert!(
                recorder
                    .active
                    .lock()
                    .unwrap()
                    .iter()
                    .all(|(_, active)| *active == 0),
                "a flat field cannot claim admitted detail"
            );
        }
    }
    let active = recorder.active.lock().unwrap();
    assert!(
        active.iter().any(|(_, active)| *active > 0),
        "positive control must actually exercise selected weights"
    );
    assert_eq!(active.len(), 3 * sizes.len());
    let phases = recorder.phases.lock().unwrap();
    let finished: Vec<_> = phases
        .iter()
        .filter_map(|phase| {
            if let FoldPhase::FoldFinished(level) = phase {
                Some(*level)
            } else {
                None
            }
        })
        .collect();
    assert_eq!(
        finished,
        (0..3).flat_map(|_| 0..sizes.len()).collect::<Vec<_>>()
    );
    let finish = |merge: &BandMerge| {
        merge
            .finish(&mut Workspace::new(&sizes))
            .into_iter()
            .flatten()
            .map(f32::to_bits)
            .collect::<Vec<_>>()
    };
    assert_eq!(finish(&plain), finish(&observed));
    assert_eq!(finish(&plain), finish(&placebo));
}

#[test]
fn sampled_accumulator_coefficients_reconstruct_the_actual_unclamped_finish() {
    let (width, height) = (43, 31);
    for select in [SelectMode::SoftPower, SelectMode::HardMax] {
        for fallback in [Fallback::Mean, Fallback::Best, Fallback::Power] {
            let cfg = MergeConfig {
                bands: 3,
                select,
                fallback,
                hull: Hull::Unclamped,
                ..MergeConfig::default()
            };
            let sizes = level_sizes(width, height, cfg.bands);
            let mut merge = BandMerge::new(width, height, 1, cfg);
            let mut ws = FrameWorkspace::new(&sizes, 1);
            for frame in 0..3 {
                let data: Vec<_> = (0..width * height)
                    .map(|i| {
                        if i % width < 15 {
                            50.0 + frame as f32
                        } else {
                            70.0 + ((i * 17 + frame * 31) % 103) as f32
                        }
                    })
                    .collect();
                ws.next_frame();
                merge.add_frame(&[&data], &data, &vec![4.0; width * height], &mut ws);
            }
            let mut diagnostic = Pyramid::zeros(&sizes);
            let mut seen = 0;
            merge.observe_accumulator(|view| {
                seen += 1;
                assert_eq!(view.frames, 3);
                for (i, value) in diagnostic.level_mut(view.level).iter_mut().enumerate() {
                    *value = view.coefficient(i);
                }
            });
            assert_eq!(seen, sizes.len());
            let observed = diagnostic.collapse(&mut Workspace::new(&sizes));
            let actual = merge.finish(&mut Workspace::new(&sizes)).remove(0);
            assert_eq!(
                observed.iter().map(|v| v.to_bits()).collect::<Vec<_>>(),
                actual.iter().map(|v| v.to_bits()).collect::<Vec<_>>(),
                "diagnostic resolver diverged for {select:?}/{fallback:?}"
            );
        }
    }
}

#[test]
fn readonly_prefix_view_matches_real_absorb_for_selection_and_all_fallback_modes() {
    let (width, height) = (43, 31);
    let mut saw_admitted = false;
    let mut saw_fallback = false;
    for select in [SelectMode::SoftPower, SelectMode::HardMax] {
        for fallback in [
            Fallback::Mean,
            Fallback::Best,
            Fallback::TopK,
            Fallback::Power,
        ] {
            for gate in [0.0, 1.0e10] {
                let cfg = MergeConfig {
                    bands: 2,
                    select,
                    fallback,
                    fallback_k: 3,
                    gate,
                    hull: Hull::Unclamped,
                    ..MergeConfig::default()
                };
                let sizes = level_sizes(width, height, cfg.bands);
                let mut prefix = BandMerge::new(width, height, 4, cfg);
                let mut current = BandMerge::new(width, height, 4, cfg);
                let mut workspace = FrameWorkspace::new(&sizes, 4);
                for frame in 0..5 {
                    let planes: Vec<Vec<f32>> = (0..4)
                        .map(|plane| {
                            (0..width * height)
                                .map(|index| {
                                    if index % width < 14 {
                                        200.0 + frame as f32 * (plane + 1) as f32
                                    } else {
                                        200.0
                                            + (((index * 7 + frame * 13) % 37) as f32 - 18.0)
                                                * (plane + 1) as f32
                                    }
                                })
                                .collect()
                        })
                        .collect();
                    let green: Vec<_> = planes[1]
                        .iter()
                        .zip(&planes[2])
                        .map(|(a, b)| 0.5 * (a + b))
                        .collect();
                    let refs: Vec<_> = planes.iter().map(Vec::as_slice).collect();
                    workspace.next_frame();
                    let destination = if frame < 2 { &mut prefix } else { &mut current };
                    destination.add_frame(&refs, &green, &vec![9.0; green.len()], &mut workspace);
                }
                let output_bits = |merge: &BandMerge| {
                    merge
                        .finish(&mut Workspace::new(&sizes))
                        .into_iter()
                        .flatten()
                        .map(f32::to_bits)
                        .collect::<Vec<_>>()
                };
                let before_prefix = output_bits(&prefix);
                let before_current = output_bits(&current);
                let mut absorbed = prefix.clone();
                absorbed.absorb(&current);
                let mut actual = Vec::new();
                absorbed.observe_accumulator(|band| {
                    actual.push(
                        (0..band.size.pixels())
                            .map(|index| (band.coefficient(index).to_bits(), band.averaging(index)))
                            .collect::<Vec<_>>(),
                    );
                });
                let mut visited = 0;
                prefix.observe_accumulator_with(&current, |band| {
                    visited += 1; assert_eq!(band.frames, 5);
                    for index in 0..band.size.pixels() {
                        let observed = (band.coefficient(index).to_bits(), band.averaging(index));
                        assert_eq!(observed, actual[band.level][index], "virtual reduction differs at {select:?}/{fallback:?}/gate{gate}/level{} /pixel{index}", band.level);
                        saw_fallback |= observed.1;
                        saw_admitted |= !observed.1 && band.level + 1 < sizes.len();
                    }
                });
                assert_eq!(visited, sizes.len());
                assert_eq!(
                    output_bits(&prefix),
                    before_prefix,
                    "observing cannot change the retained canonical state"
                );
                assert_eq!(
                    output_bits(&current),
                    before_current,
                    "observing cannot change the active chunk"
                );
            }
        }
    }
    assert!(
        saw_admitted && saw_fallback,
        "the fixture must actually traverse both resolution branches"
    );
}

#[test]
fn virtual_top_k_absorb_preserves_earlier_chunk_on_equal_keys() {
    // Equal green magnitudes with opposite signed coefficients expose the
    // canonical tie rule when three of four tied samples are retained.
    let cfg = MergeConfig {
        bands: 2,
        fallback: Fallback::TopK,
        fallback_k: 3,
        gate: 1.0e10,
        hull: Hull::Unclamped,
        ..MergeConfig::default()
    };
    let (width, height) = (43, 31);
    let sizes = level_sizes(width, height, cfg.bands);
    let mut prefix = BandMerge::new(width, height, 4, cfg);
    let mut current = BandMerge::new(width, height, 4, cfg);
    let mut workspace = FrameWorkspace::new(&sizes, 4);
    for frame in 0..4 {
        let sign = if frame < 2 { 1.0 } else { -1.0 };
        let green: Vec<_> = (0..width * height)
            .map(|index| {
                200.0
                    + sign
                        * if (index % width / 4 + index / width / 4) % 2 == 0 {
                            40.0
                        } else {
                            -40.0
                        }
            })
            .collect();
        workspace.next_frame();
        let destination = if frame < 2 { &mut prefix } else { &mut current };
        destination.add_frame(
            &[&green, &green, &green, &green],
            &green,
            &vec![9.0; green.len()],
            &mut workspace,
        );
    }
    let mut absorbed = prefix.clone();
    absorbed.absorb(&current);
    let slots = cfg.fallback_slots();
    let mut exact_opposite_ties = 0;
    for (level, size) in sizes.iter().enumerate().take(sizes.len() - 1) {
        let slot = level * 4 + 1;
        for index in 0..size.pixels() {
            let at = index * slots;
            if prefix.fkey[level][at] > 0.0
                && prefix.fkey[level][at] == current.fkey[level][at]
                && prefix.fval[slot][at] * current.fval[slot][at] < 0.0
            {
                exact_opposite_ties += 1;
            }
        }
    }
    assert!(
        exact_opposite_ties > 0,
        "the stimulus must actually contain exact equal keys with opposite signed coefficients"
    );
    let mut expected = Vec::new();
    absorbed.observe_accumulator(|band| {
        expected.push(
            (0..band.size.pixels())
                .map(|index| band.coefficient(index).to_bits())
                .collect::<Vec<_>>(),
        )
    });
    let mut reversed = current.clone();
    reversed.absorb(&prefix);
    let mut differs_when_order_reversed = false;
    reversed.observe_accumulator(|band| {
        differs_when_order_reversed |= (0..band.size.pixels())
            .any(|index| band.coefficient(index).to_bits() != expected[band.level][index]);
    });
    assert!(
        differs_when_order_reversed,
        "right-first tie handling must demonstrably fail this fixture"
    );
    let mut nonzero = false;
    prefix.observe_accumulator_with(&current, |band| {
        for index in 0..band.size.pixels() {
            let coefficient = band.coefficient(index);
            assert_eq!(coefficient.to_bits(), expected[band.level][index]);
            nonzero |= band.level + 1 < sizes.len() && coefficient.abs() > 1.0;
        }
    });
    assert!(
        nonzero,
        "the tied fallback must produce visible detail so zero padding cannot make the check vacuous"
    );
}

#[test]
fn virtual_absorb_preserves_floor_pedestal_admission_and_empty_chunk_semantics() {
    use crate::pyramid::AdmissionMode;
    let cfg = MergeConfig {
        bands: 2,
        admission: AdmissionMode::FloorPedestalV1,
        fallback: Fallback::Mean,
        hull: Hull::Unclamped,
        ..MergeConfig::default()
    };
    let (width, height) = (43, 31);
    let sizes = level_sizes(width, height, cfg.bands);
    let mut prefix = BandMerge::new(width, height, 1, cfg);
    let mut current = BandMerge::new(width, height, 1, cfg);
    let mut workspace = FrameWorkspace::new(&sizes, 1);
    for frame in 0..4 {
        let pixels: Vec<_> = (0..width * height)
            .map(|index| 100.0 + ((index * 5 + frame * 17) % 53) as f32)
            .collect();
        workspace.next_frame();
        let destination = if frame < 3 { &mut prefix } else { &mut current };
        destination.add_frame(
            &[&pixels],
            &pixels,
            &vec![9.0; pixels.len()],
            &mut workspace,
        );
    }
    for other in [&current, &BandMerge::new(width, height, 1, cfg)] {
        let mut physical = prefix.clone();
        physical.absorb(other);
        let mut expected = Vec::new();
        physical.observe_accumulator(|band| {
            expected.push(
                (0..band.size.pixels())
                    .map(|index| (band.coefficient(index).to_bits(), band.averaging(index)))
                    .collect::<Vec<_>>(),
            )
        });
        let mut count = 0;
        prefix.observe_accumulator_with(other, |band| {
            assert_eq!(band.frames, (prefix.frames() + other.frames()) as usize);
            for index in 0..band.size.pixels() {
                count += 1;
                assert_eq!(
                    (band.coefficient(index).to_bits(), band.averaging(index)),
                    expected[band.level][index]
                );
            }
        });
        assert!(
            count > width * height,
            "every coarse level as well as the input level must be compared"
        );
    }
}
