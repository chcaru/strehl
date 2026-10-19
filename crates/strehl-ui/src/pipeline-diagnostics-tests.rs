use super::*;

fn ingest(progress: &mut PipelineProgress, fields: &str) {
    progress.ingest(&format!("STREHL_UI_PROGRESS {fields}\n"));
}
fn map(seq: usize) -> String {
    format!(
        "event=diagnostic seq={seq} frame=1 level=0 kind=focus-energy scope=frame scale=log width=2 height=1 min=0 max=9 folded=1 total=3 sampling=nearest data=00ff"
    )
}

#[test]
fn invalid_payloads_and_duplicate_sequences_cannot_replace_real_surface() {
    let mut p = PipelineProgress::default();
    ingest(&mut p, &map(1));
    let valid = p.diagnostic_surfaces[0].pixels.clone();
    for bad in [
        map(2).replace("data=00ff", "data=00fg"),
        map(2).replace("width=2", "width=129"),
        map(2).replace("min=0", "min=NaN"),
        map(2).replace("scope=frame", "scope=stack"),
        map(2).replace("folded=1", "folded=2"),
        map(2).replace("frame=1", "frame=3"),
        map(2).replace("data=00ff", "data=00"),
        format!("{} total=3", map(2)),
        map(1),
    ] {
        ingest(&mut p, &bad);
        assert_eq!(
            p.diagnostic_surfaces.len(),
            1,
            "malformed map was accepted: {bad}"
        );
        assert_eq!(&*p.diagnostic_surfaces[0].pixels, &*valid);
    }
    for seq in 2..=405 {
        ingest(&mut p, &map(seq));
    }
    assert_eq!(p.diagnostic_surfaces.len(), 384);
    assert_eq!(p.diagnostic_surfaces.front().unwrap().sequence, 22);
    assert_eq!(p.diagnostic_surfaces.back().unwrap().sequence, 405);
}

fn mask(
    seq: usize,
    kind: &str,
    frame: usize,
    folded: usize,
    level: usize,
    total: usize,
    data: &str,
) -> String {
    format!(
        "event=diagnostic seq={seq} frame={frame} level={level} kind={kind} scope={} scale=linear width=2 height=1 min=0 max=1 folded={folded} total={total} sampling=nearest data={data}",
        if kind == "gate-support" {
            "frame"
        } else {
            "stack"
        }
    )
}

#[test]
fn sampled_mask_history_survives_packet_eviction_and_preserves_actual_gaps_and_axes() {
    let mut progress = PipelineProgress::default();
    for frame in (0..1000).step_by(2) {
        ingest(
            &mut progress,
            &mask(
                frame + 1,
                "gate-support",
                frame,
                1,
                0,
                1000,
                if frame == 0 { "0000" } else { "00ff" },
            ),
        );
    }
    assert_eq!(progress.diagnostic_surfaces.len(), 384);
    assert!(
        progress.diagnostic_surfaces.front().unwrap().frame > 0,
        "fixture must evict the earliest real images"
    );
    let history = &progress.sampled_mask_history[0];
    assert_eq!(history.observations(), 500);
    assert_eq!(
        history.bins[0].fraction(),
        Some(0.0),
        "a received all-zero mask is real evidence"
    );
    assert_eq!(
        history.bins[1].fraction(),
        None,
        "an unobserved frame is not an all-zero mask"
    );
    assert_eq!(history.bins[998].fraction(), Some(0.5));
    ingest(
        &mut progress,
        &mask(1001, "gate-support", 0, 1, 0, 1000, "ffff"),
    );
    assert_eq!(
        progress.sampled_mask_history[0].observations(),
        500,
        "repeated identities cannot inflate history"
    );
    assert_eq!(
        progress.sampled_mask_history[0].bins[0].fraction(),
        Some(0.0),
        "the first actual observation remains stable"
    );
    ingest(
        &mut progress,
        &mask(1002, "averaging", 10, 7, 0, 1000, "ffff"),
    );
    let prefix = progress
        .sampled_mask_history
        .iter()
        .find(|history| history.kind == DiagnosticKind::Averaging)
        .unwrap();
    assert_eq!(prefix.bins[6].fraction(), Some(1.0));
    assert_eq!(
        prefix.bins[10].fraction(),
        None,
        "fallback history indexes accepted prefixes, never the last source identity"
    );
    let before = progress.sampled_mask_history[0].observations();
    for bad in [
        mask(1003, "gate-support", 1, 1, 0, 1000, "0080"),
        mask(1003, "gate-support", 1, 1, 0, 1000, "00gg"),
        mask(1003, "gate-support", 1, 1, 0, 1000, "ffff").replace("min=0", "min=-1"),
        mask(1003, "gate-support", 1, 1, 0, 1001, "ffff"),
    ] {
        ingest(&mut progress, &bad);
    }
    assert_eq!(progress.sampled_mask_history[0].observations(), before);
    assert_eq!(progress.diagnostic_surfaces.back().unwrap().sequence, 1002);
    progress.mark_complete();
    assert_eq!(progress.sampled_mask_history[0].observations(), 500);
    assert!(PipelineProgress::default().sampled_mask_history.is_empty());
}

#[test]
fn sampled_history_uses_fixed_bounded_bins_without_claiming_missing_captures() {
    let mut progress = PipelineProgress::default();
    for (sequence, frame) in [0, 63, 64, 65535].into_iter().enumerate() {
        ingest(
            &mut progress,
            &mask(sequence + 1, "gate-support", frame, 1, 63, 65536, "00ff"),
        );
    }
    let history = &progress.sampled_mask_history[0];
    assert_eq!(history.bins.len(), 1024);
    assert_eq!(history.range(0), 0..64);
    assert_eq!(history.range(1023), 65472..65536);
    assert_eq!(history.bins[0].observations(), 2);
    assert_eq!(history.bins[1].observations(), 1);
    assert_eq!(history.bins[2].fraction(), None);
    assert_eq!(history.observations(), 4);
    assert_eq!(history.bins[0].on_samples, 2);
    assert_eq!(history.bins[0].samples, 4);
    let mut uneven = PipelineProgress::default();
    for frame in 0..1025 {
        ingest(
            &mut uneven,
            &mask(frame + 1, "gate-support", frame, 1, 0, 1025, "00ff"),
        );
    }
    let history = &uneven.sampled_mask_history[0];
    assert_eq!(
        history.observations(),
        1025,
        "non-divisible bin boundaries must not alias or lose a real capture"
    );
    assert_eq!(history.range(0), 0..2);
    assert_eq!(history.range(1023), 1024..1025);
    assert!(history.bins.iter().all(|bin| bin.fraction() == Some(0.5)));
}

#[test]
fn signed_reconstruction_real_steps_sparse_counts_and_history_are_preserved() {
    let mut p = PipelineProgress::default();
    assert!(p.observed_stages.is_empty());
    ingest(&mut p, "event=stage name=read total=3");
    ingest(&mut p, "event=align-phase name=planes frames=3 total=3");
    ingest(
        &mut p,
        "event=merge-step index=1 name=gather state=skipped level=none total=3",
    );
    assert_eq!(p.merge_step, Some(MergeStep::Gather));
    assert_eq!(p.merge_step_state, Some(WorkState::Skipped));
    ingest(
        &mut p,
        "event=band-work index=2 level=1 completed=2 total=3",
    );
    ingest(
        &mut p,
        "event=band-work index=0 level=1 completed=1 total=3",
    );
    assert_eq!(
        p.merge_bands[&1],
        BandWork {
            completed: 2,
            total: 3,
            last_frame: 2
        }
    );
    assert!(!p.merge_bands.contains_key(&0));
    ingest(
        &mut p,
        "event=render-step name=reconstruct state=started total=3",
    );
    ingest(
        &mut p,
        "event=diagnostic seq=1 frame=2 level=0 kind=reconstructed scope=stack scale=linear width=2 height=1 min=-3 max=9 folded=2 total=3 sampling=nearest data=00ff",
    );
    assert_eq!(
        p.diagnostic_surfaces.len(),
        1,
        "negative reconstructed DN is physically permitted and cannot be silently discarded"
    );
    assert_eq!(p.diagnostic_surfaces[0].min, -3.0);
    assert_eq!(p.render_step, Some(RenderStep::Reconstruct));
    assert_eq!(
        p.observed_stages.iter().copied().collect::<Vec<_>>(),
        vec![
            Stage::Preparing,
            Stage::Alignment,
            Stage::Merge,
            Stage::Rendering
        ]
    );
    ingest(
        &mut p,
        "event=merge-step index=0 name=decode state=started level=none total=3",
    );
    assert_eq!(
        p.merge_step,
        Some(MergeStep::Gather),
        "late merge work cannot replace render state"
    );
}

#[test]
fn rejected_stage_events_do_not_manufacture_observed_history() {
    let mut p = PipelineProgress::default();
    ingest(&mut p, "event=stage name=read total=3");
    for bad in [
        "event=stage name=render total=3 total=3",
        "event=stage name=render total=0",
        "event=stage name=render total=4",
        "event=stage name=render total=999999999",
        "event=stage name=unknown total=3",
        "event=stage name=render total=3 unstructured",
    ] {
        ingest(&mut p, bad);
        assert_eq!(
            p.stage,
            Stage::Preparing,
            "invalid event advanced stage: {bad}"
        );
        assert_eq!(p.observed_stages, [Stage::Preparing].into_iter().collect());
    }
    ingest(&mut p, "event=stage name=merge total=3");
    ingest(&mut p, "event=stage name=alignment total=3");
    assert_eq!(
        p.observed_stages,
        [Stage::Preparing, Stage::Merge].into_iter().collect(),
        "late alignment must not invent historical observation"
    );
    ingest(&mut p, "event=stage name=render total=3");
    ingest(&mut p, "event=frame-started index=2 total=3");
    assert!(
        p.processing_frame.is_none(),
        "late merge identity cannot replace actual render phase"
    );
}

#[test]
fn coarse_preview_accepts_its_bounded_full_payload_without_claiming_finished_reconstruction() {
    let mut progress = PipelineProgress::default();
    let payload = format!(
        "event=diagnostic seq=1 frame=7 level=3 kind=preview scope=stack scale=linear width=512 height=384 min=-4 max=200 folded=6 total=12 sampling=nearest data={}",
        "00ff".repeat(512 * 384 / 2)
    );
    assert!(
        payload.len() > 16 * 1024,
        "must exercise the prior line-size failure"
    );
    // Feed a real long record in arbitrary transport-sized chunks.
    let wire = format!("STREHL_UI_PROGRESS {payload}\n");
    for chunk in wire.as_bytes().chunks(379) {
        progress.ingest(std::str::from_utf8(chunk).unwrap());
    }
    assert_eq!(progress.diagnostic_surfaces.len(), 1);
    let preview = &progress.diagnostic_surfaces[0];
    assert_eq!(preview.kind, DiagnosticKind::Preview);
    assert_eq!(preview.scope, DiagnosticScope::Stack);
    assert_eq!(
        (preview.width, preview.height, preview.level, preview.folded),
        (512, 384, 3, 6)
    );
    assert_eq!(preview.pixels.len(), 512 * 384);
    assert_eq!(preview.min, -4.0);
    assert_eq!(progress.stage, Stage::Merge);
    assert_eq!(
        progress.render_step, None,
        "a pre-hull coarse preview is not finished reconstruction"
    );
    for bad in [
        payload
            .replace("seq=1", "seq=2")
            .replace("width=512", "width=513"),
        payload
            .replace("seq=1", "seq=2")
            .replace("height=384", "height=385"),
        payload
            .replace("seq=1", "seq=2")
            .replace("scope=stack", "scope=frame"),
        payload
            .replace("seq=1", "seq=2")
            .replace("scale=linear", "scale=log"),
        payload
            .replace("seq=1", "seq=2")
            .replace("kind=preview", "kind=reconstructed"),
    ] {
        ingest(&mut progress, &bad);
        assert_eq!(progress.diagnostic_surfaces.len(), 1);
    }
    ingest(&mut progress, &map(2).replace("total=3", "total=12"));
    assert_eq!(
        progress.diagnostic_surfaces.len(),
        2,
        "oversized/malformed records must not poison subsequent ordinary observations"
    );
}
