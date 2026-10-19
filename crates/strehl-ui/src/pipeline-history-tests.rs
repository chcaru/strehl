use super::*;

fn ingest(progress: &mut PipelineProgress, fields: &str) {
    progress.ingest(&format!("STREHL_UI_PROGRESS {fields}\n"));
}

#[test]
fn alignment_history_preserves_only_valid_observed_phases_and_terminal_result() {
    let mut p = PipelineProgress::default();
    assert!(p.alignment_phase_history.is_empty());
    ingest(&mut p, "event=align-phase name=planes frames=10 total=10");
    for invalid in [
        "event=align-phase name=pyramids frames=10 total=9",
        "event=align-phase name=pyramids frames=11 total=11",
        "event=align-phase name=pyramids frames=10 total=10 total=10",
        "event=align-phase name=unknown frames=10 total=10",
        "event=align-phase name=cache frames=10 total=10",
    ] {
        ingest(&mut p, invalid);
        assert_eq!(
            p.alignment_phase_history,
            BTreeSet::from([AlignmentPhase::Planes]),
            "invalid phase changed history: {invalid}"
        );
    }
    ingest(&mut p, "event=align-phase name=pairs frames=10 total=45");
    ingest(
        &mut p,
        "event=align-result source=solved reference=5 placed=9 refused=1 frames=10 total=10",
    );
    ingest(
        &mut p,
        "event=align-result source=off reference=0 placed=0 refused=0 frames=10 total=10",
    );
    ingest(&mut p, "event=stage name=merge total=10");
    ingest(&mut p, "event=align-phase name=solve frames=10 total=10");
    ingest(&mut p, "event=stage name=render total=10");
    assert_eq!(
        p.alignment_phase_history,
        BTreeSet::from([
            AlignmentPhase::Planes,
            AlignmentPhase::Pairs,
            AlignmentPhase::Complete,
        ])
    );
    assert_eq!(p.alignment_phase, Some(AlignmentPhase::Complete));
    assert_eq!(p.alignment_source.as_deref(), Some("solved"));
    assert_eq!(p.frames_total, Some(10));
    assert_eq!(
        p.observed_stages,
        BTreeSet::from([Stage::Alignment, Stage::Merge, Stage::Rendering])
    );

    let mut cached = PipelineProgress::default();
    ingest(
        &mut cached,
        "event=align-phase name=cache frames=10 total=10",
    );
    ingest(
        &mut cached,
        "event=align-result source=cache reference=5 placed=10 refused=0 frames=10 total=10",
    );
    assert_eq!(
        cached.alignment_phase_history,
        BTreeSet::from([AlignmentPhase::Cache, AlignmentPhase::Complete])
    );
    assert!(
        cached.alignment_edge_observations.is_empty(),
        "loading cache cannot invent comparisons"
    );
    let mut bypassed = PipelineProgress::default();
    ingest(
        &mut bypassed,
        "event=align-result source=off reference=0 placed=0 refused=0 frames=10 total=10",
    );
    assert_eq!(
        bypassed.alignment_phase_history,
        BTreeSet::from([AlignmentPhase::Bypassed])
    );
}

#[test]
fn sampled_alignment_edges_are_classified_only_when_the_count_gap_identifies_them() {
    let mut p = PipelineProgress::default();
    ingest(&mut p, "event=align-phase name=pairs frames=20 total=190");
    let published = [
        ([0, 1], 1, 1, AlignmentOutcome::Accepted),
        ([0, 2], 2, 1, AlignmentOutcome::Refused),
        ([0, 5], 5, 2, AlignmentOutcome::Unknown),
        ([1, 8], 8, 5, AlignmentOutcome::Accepted),
        ([1, 11], 11, 5, AlignmentOutcome::Refused),
        ([1, 15], 15, 7, AlignmentOutcome::Unknown),
    ];
    for (pair, completed, accepted, _) in published {
        ingest(
            &mut p,
            &format!(
                "event=align-pair i={} j={} completed={completed} accepted={accepted} total=190 frames=20",
                pair[0], pair[1]
            ),
        );
    }
    assert_eq!(
        p.alignment_edge_observations
            .iter()
            .copied()
            .collect::<Vec<_>>(),
        published
            .into_iter()
            .map(|(pair, completed, _, outcome)| AlignmentEdgeObservation {
                pair,
                outcome,
                completed
            })
            .collect::<Vec<_>>()
    );
    assert_eq!(
        p.alignment_observed_pairs.len(),
        6,
        "a count of 15 cannot manufacture 15 endpoints"
    );
    let before = p.alignment_edge_observations.clone();
    for invalid in [
        "event=align-pair i=0 j=3 completed=14 accepted=7 total=190 frames=20",
        "event=align-pair i=0 j=3 completed=16 accepted=9 total=190 frames=20",
        "event=align-pair i=0 j=3 completed=16 accepted=6 total=190 frames=20",
        "event=align-pair i=0 j=20 completed=16 accepted=8 total=190 frames=20",
        "event=align-pair i=0 j=3 completed=16 accepted=8 total=189 frames=20",
        "event=align-pair i=0 j=3 completed=16 accepted=8 total=190 frames=20 accepted=8",
    ] {
        ingest(&mut p, invalid);
        assert_eq!(
            p.alignment_edge_observations, before,
            "invalid result added an outcome: {invalid}"
        );
    }
    assert_eq!(p.alignment_pairs, Some((15, 7, 190)));
    assert!(
        before
            .iter()
            .any(|edge| edge.outcome == AlignmentOutcome::Accepted)
    );
    assert!(
        before
            .iter()
            .any(|edge| edge.outcome == AlignmentOutcome::Refused)
    );
    assert!(
        before
            .iter()
            .any(|edge| edge.outcome == AlignmentOutcome::Unknown),
        "mixed sampled interval must exercise uncertainty"
    );
}

#[test]
fn recent_alignment_endpoints_roll_without_erasing_the_durable_atlas() {
    let mut p = PipelineProgress::default();
    ingest(&mut p, "event=align-phase name=pairs frames=40 total=780");
    let pairs: Vec<_> = (0..40)
        .flat_map(|i| (i + 1..40).map(move |j| [i, j]))
        .collect();
    for (index, pair) in pairs.iter().take(600).enumerate() {
        let completed = index + 1;
        ingest(
            &mut p,
            &format!(
                "event=align-pair i={} j={} completed={completed} accepted={} total=780 frames=40",
                pair[0],
                pair[1],
                completed / 2
            ),
        );
    }
    assert_eq!(p.alignment_observed_pairs.len(), 512);
    assert_eq!(p.alignment_edge_observations.len(), 600);
    assert_eq!(
        p.alignment_edge_observations.front().unwrap().pair,
        pairs[0]
    );
    assert_eq!(
        p.alignment_edge_observations.back().unwrap().pair,
        pairs[599]
    );
    assert_eq!(
        p.alignment_observed_pairs
            .iter()
            .copied()
            .collect::<Vec<_>>(),
        p.alignment_edge_observations
            .iter()
            .skip(88)
            .map(|edge| edge.pair)
            .collect::<Vec<_>>()
    );
    assert!(p.alignment_edge_observations.iter().all(|edge| edge.outcome
        == if edge.completed % 2 == 0 {
            AlignmentOutcome::Accepted
        } else {
            AlignmentOutcome::Refused
        }));
    assert_eq!(
        p.alignment_pairs,
        Some((600, 300, 780)),
        "bounded history must not change cumulative work"
    );
    assert!(!p.alignment_edge_history_saturated());
}

#[test]
fn deep_sparse_atlas_keeps_early_distinct_edges_after_512_and_later_stages() {
    let mut p = PipelineProgress::default();
    ingest(
        &mut p,
        "event=align-phase name=pairs total=33411 frames=259",
    );
    let first = AlignmentEdgeObservation {
        pair: [0, 258],
        outcome: AlignmentOutcome::Unknown,
        completed: 101,
    };
    ingest(
        &mut p,
        "event=align-pair i=0 j=258 completed=101 accepted=50 total=33411 frames=259",
    );
    let later: Vec<_> = (0..259)
        .flat_map(|i| (i + 1..259).map(move |j| [i, j]))
        .filter(|pair| *pair != first.pair)
        .take(753)
        .collect();
    for (index, pair) in later.iter().enumerate() {
        let completed = 102 + index;
        let accepted = 50 + index.div_ceil(2);
        ingest(
            &mut p,
            &format!(
                "event=align-pair i={} j={} completed={completed} accepted={accepted} total=33411 frames=259",
                pair[0], pair[1]
            ),
        );
    }
    assert_eq!(
        p.alignment_edge_observations.len(),
        754,
        "all754 actually received edges need to remain in the atlas"
    );
    assert_eq!(p.alignment_edge_observations.front(), Some(&first));
    assert_eq!(p.alignment_observed_pairs.len(), 512);
    assert!(
        !p.alignment_observed_pairs.contains(&first.pair),
        "the control must actually exercise rolling deletion from the recent lane"
    );
    ingest(
        &mut p,
        "event=align-pair i=2 j=7 completed=853 accepted=426 total=33411 frames=259",
    );
    assert_eq!(
        p.alignment_edge_observations.len(),
        754,
        "regressed count cannot add a durable edge"
    );
    ingest(&mut p, "event=stage name=merge total=259");
    ingest(&mut p, "event=stage name=render total=259");
    assert_eq!(p.alignment_edge_observations.front(), Some(&first));
    assert_eq!(
        p.alignment_edge_observations.back().unwrap().pair,
        *later.last().unwrap()
    );
    assert_eq!(p.alignment_edge_history_omitted, 0);
    assert!(!p.alignment_edge_history_saturated());
}

#[test]
fn saturated_atlas_preserves_its_oldest_evidence_and_counts_only_valid_omitted_events() {
    let mut p = PipelineProgress::default();
    // Seed a coherent full history to exercise the cap without parsing65k
    // setup lines. Every seeded pair is distinct and within the364-frame graph.
    let pairs: Vec<_> = (0..364)
        .flat_map(|i| (i + 1..364).map(move |j| [i, j]))
        .take(65538)
        .collect();
    ingest(
        &mut p,
        "event=align-phase name=pairs total=66066 frames=364",
    );
    p.alignment_pairs = Some((65536, 32768, 66066));
    p.alignment_edge_observations = pairs
        .iter()
        .copied()
        .take(65536)
        .enumerate()
        .map(|(index, pair)| AlignmentEdgeObservation {
            pair,
            completed: index + 1,
            outcome: if (index + 1) % 2 == 0 {
                AlignmentOutcome::Accepted
            } else {
                AlignmentOutcome::Refused
            },
        })
        .collect();
    p.alignment_observed_pairs = pairs.iter().copied().skip(65536 - 512).take(512).collect();
    let first = *p.alignment_edge_observations.front().unwrap();
    let last = *p.alignment_edge_observations.back().unwrap();
    assert!(
        !p.alignment_edge_history_saturated(),
        "a full but complete received history has not omitted an event yet"
    );
    for (index, pair) in pairs.iter().enumerate().skip(65536) {
        let completed = index + 1;
        ingest(
            &mut p,
            &format!(
                "event=align-pair i={} j={} completed={completed} accepted={} total=66066 frames=364",
                pair[0],
                pair[1],
                completed / 2
            ),
        );
    }
    assert_eq!(p.alignment_edge_observations.len(), 65536);
    assert_eq!(p.alignment_edge_observations.front(), Some(&first));
    assert_eq!(
        p.alignment_edge_observations.back(),
        Some(&last),
        "saturation cannot erase earlier atlas evidence"
    );
    assert_eq!(p.alignment_edge_history_omitted, 2);
    assert!(p.alignment_edge_history_saturated());
    assert_eq!(p.alignment_observed_pairs.len(), 512);
    assert_eq!(p.alignment_observed_pairs.back(), pairs.last());
    assert_eq!(
        p.alignment_pairs,
        Some((65538, 32769, 66066)),
        "work counters continue even when retained atlas evidence is capped"
    );
    for invalid in [
        "event=align-pair i=2 j=3 completed=65537 accepted=32768 total=66066 frames=364",
        "event=align-pair i=2 j=364 completed=65539 accepted=32769 total=66066 frames=364",
        "event=align-pair i=2 j=3 completed=65539 accepted=32769 total=66066 frames=364 accepted=32769",
    ] {
        ingest(&mut p, invalid);
    }
    assert_eq!(
        p.alignment_edge_history_omitted, 2,
        "invalid/regressed events must not inflate the omitted-evidence count"
    );
    ingest(&mut p, "event=stage name=merge total=364");
    ingest(&mut p, "event=stage name=render total=364");
    assert_eq!(p.alignment_edge_observations.front(), Some(&first));
    assert_eq!(p.alignment_edge_history_omitted, 2);
}

#[test]
fn merge_history_is_sparse_durable_and_keeps_skips_distinct_from_finished_work() {
    let mut p = PipelineProgress::default();
    for event in [
        "event=merge-step index=6 name=decode state=started level=none total=10",
        "event=merge-step index=6 name=decode state=finished level=none total=10",
        "event=merge-step index=6 name=gather state=skipped level=none total=10",
        "event=merge-step index=9 name=pyramid state=finished level=none total=10",
        "event=merge-step index=9 name=focus state=started level=3 total=10",
        "event=merge-step index=9 name=fold state=started level=3 total=10",
        "event=merge-step index=9 name=fold state=finished level=3 total=10",
        "event=band-work index=2 level=5 completed=6 total=10",
    ] {
        ingest(&mut p, event);
    }
    assert_eq!(
        p.merge_frame_observations
            .keys()
            .copied()
            .collect::<Vec<_>>(),
        vec![2, 6, 9]
    );
    assert_eq!(
        p.merge_frame_observations[&6].decode,
        Some(WorkState::Finished)
    );
    assert_eq!(
        p.merge_frame_observations[&6].gather,
        Some(WorkState::Skipped)
    );
    assert!(p.merge_frame_observations[&6].extract.is_none());
    assert_eq!(
        p.merge_frame_observations[&9].pyramid,
        Some(WorkState::Finished)
    );
    assert!(p.merge_frame_observations[&9].focus_observed(3));
    assert_eq!(
        p.merge_frame_observations[&9].fold_state(3),
        Some(WorkState::Finished)
    );
    assert!(!p.merge_frame_observations[&9].focus_observed(2));
    assert!(p.merge_frame_observations[&9].fold_state(2).is_none());
    assert_eq!(
        p.merge_frame_observations[&2].fold_state(5),
        Some(WorkState::Finished)
    );
    assert_eq!(
        p.merge_frame_observations[&2].fold_started, 0,
        "completed-only event cannot fabricate a received start"
    );
    assert_eq!(
        p.merge_frame_observations[&2].focus_started, 0,
        "band completion cannot fabricate a received focus callback"
    );
    assert_eq!(p.merge_bands[&5].completed, 6);
    let saved = p.merge_frame_observations.clone();
    for bad in [
        "event=merge-step index=6 name=decode state=started level=none total=10",
        "event=merge-step index=6 name=gather state=finished level=none total=10",
        "event=merge-step index=9 name=fold state=started level=3 total=10",
        "event=merge-step index=9 name=focus state=started level=3 total=10",
        "event=merge-step index=4 name=decode state=skipped level=none total=10",
        "event=merge-step index=4 name=focus state=finished level=1 total=10",
        "event=merge-step index=4 name=fold state=started level=64 total=10",
        "event=merge-step index=4 name=decode state=finished level=none total=11",
        "event=merge-step index=4 name=decode state=finished level=none total=10 total=10",
        "event=band-work index=4 level=5 completed=5 total=10",
        "event=render-step name=write state=skipped total=10",
    ] {
        ingest(&mut p, bad);
        assert_eq!(
            p.merge_frame_observations, saved,
            "bad observation changed durable work: {bad}"
        );
        assert_eq!(
            p.stage,
            Stage::Merge,
            "malformed work changed phase history: {bad}"
        );
    }
    ingest(&mut p, "event=stage name=render total=10");
    ingest(
        &mut p,
        "event=merge-step index=4 name=decode state=started level=none total=10",
    );
    p.mark_complete();
    assert_eq!(
        p.merge_frame_observations, saved,
        "later phases must retain exact observed work"
    );
}

#[test]
fn merge_history_honors_capture_and_level_limits_without_allocating_missing_frames() {
    let mut p = PipelineProgress::default();
    ingest(
        &mut p,
        "event=merge-step index=65535 name=focus state=started level=63 total=65536",
    );
    ingest(
        &mut p,
        "event=band-work index=65535 level=63 completed=65536 total=65536",
    );
    assert_eq!(p.merge_frame_observations.len(), 1);
    assert!(p.merge_frame_observations[&65535].focus_observed(63));
    assert_eq!(
        p.merge_frame_observations[&65535].fold_state(63),
        Some(WorkState::Finished)
    );
    assert!(!p.merge_frame_observations[&65535].focus_observed(64));
    assert!(
        p.merge_frame_observations[&65535]
            .fold_state(usize::MAX)
            .is_none()
    );
    for invalid in [
        "event=merge-step index=65536 name=decode state=started level=none total=65536",
        "event=merge-step index=0 name=decode state=started level=none total=65537",
        "event=band-work index=0 level=64 completed=1 total=65536",
    ] {
        ingest(&mut p, invalid);
    }
    assert_eq!(p.merge_frame_observations.len(), 1);
    assert_eq!(p.frames_total, Some(65536));
}
