use super::*;

fn event(progress: &mut PipelineProgress, fields: &str) {
    progress.ingest(&format!("STREHL_UI_PROGRESS {fields}\n"));
}

#[test]
fn parallel_source_order_counts_refused_attempts_separately_and_never_marks_saved() {
    let mut progress = PipelineProgress::default();
    event(
        &mut progress,
        "event=confidence-pass state=started completed=0 compared=0 total=4",
    );
    for receipt in [
        "event=confidence-frame index=2 completed=1 compared=1 mapped=true total=4",
        "event=confidence-frame index=0 completed=2 compared=1 mapped=false total=4",
        "event=confidence-frame index=3 completed=3 compared=2 mapped=true total=4",
        "event=confidence-frame index=1 completed=4 compared=3 mapped=true total=4",
        "event=confidence-pass state=finished completed=4 compared=3 total=4",
    ] {
        event(&mut progress, receipt);
    }
    let pass = progress.confidence.unwrap();
    assert_eq!(
        (pass.completed, pass.compared, pass.total, pass.state),
        (4, 3, 4, WorkState::Finished)
    );
    assert_eq!(
        pass.observations,
        BTreeMap::from([(0, false), (1, true), (2, true), (3, true)])
    );
    assert_eq!(progress.stage, Stage::Rendering);
    assert_eq!(
        progress.frames_accepted, None,
        "confidence attempts cannot rewrite merge acceptance"
    );
}

#[test]
fn invalid_or_regressing_confidence_receipts_do_not_replace_real_progress() {
    let mut progress = PipelineProgress::default();
    event(
        &mut progress,
        "event=confidence-frame index=2 completed=3 compared=2 mapped=true total=8",
    );
    let before = progress.confidence.clone();
    for receipt in [
        "event=confidence-pass state=started completed=0 compared=0 total=8",
        "event=confidence-pass state=finished completed=7 compared=2 total=8",
        "event=confidence-frame index=4 completed=2 compared=1 mapped=true total=8",
        "event=confidence-frame index=4 completed=4 compared=4 mapped=true total=8",
        "event=confidence-frame index=4 completed=4 compared=3 mapped=false total=8",
        "event=confidence-frame index=4 completed=4 compared=2 mapped=true total=8",
        "event=confidence-frame index=2 completed=4 compared=3 mapped=true total=8",
        "event=confidence-frame index=8 completed=4 compared=3 mapped=true total=8",
        "event=confidence-frame index=4 completed=4 compared=3 mapped=1 total=8",
        "event=confidence-frame index=4 completed=4 compared=3 mapped=true total=9",
        "event=confidence-frame index=4 completed=4 compared=3 mapped=true total=8 total=8",
        "event=confidence-pass state=skipped completed=8 compared=2 total=8",
    ] {
        event(&mut progress, receipt);
        assert_eq!(
            progress.confidence, before,
            "accepted malformed receipt {receipt}"
        );
    }
    assert_eq!(
        progress.confidence.as_ref().unwrap().observations.len(),
        1,
        "a log gap carries cumulative work, never invented source identities"
    );
    event(
        &mut progress,
        "event=render-step name=develop state=started total=8",
    );
    event(
        &mut progress,
        "event=confidence-pass state=finished completed=8 compared=6 total=8",
    );
    assert_eq!(
        progress.confidence, before,
        "late confidence cannot return the render phase to comparisons"
    );
}
