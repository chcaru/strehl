use super::*;

fn event(p: &mut PipelineProgress, fields: &str) {
    p.ingest(&format!("STREHL_UI_PROGRESS {fields}\n"));
}

#[test]
fn confidence_pass_has_real_attempt_progress_between_reconstruction_and_development() {
    let mut p = PipelineProgress::default();
    let mut journey = ProcessJourney::default();
    event(
        &mut p,
        "event=render-step name=reconstruct state=finished total=4",
    );
    event(
        &mut p,
        "event=confidence-pass state=started completed=0 compared=0 total=4",
    );
    let started = journey.observe(1, &p);
    assert_eq!(started[4].state, State::Finished);
    assert_eq!(started[5].title, Some("CONFIDENCE"));
    assert_eq!(started[5].state, State::Active);
    assert_eq!(started[5].fraction, Some(0.0));
    event(
        &mut p,
        "event=confidence-frame index=3 completed=2 compared=1 mapped=false total=4",
    );
    let middle = journey.observe(1, &p);
    assert_eq!(middle[5].value, "2 / 4");
    assert_eq!(middle[5].fraction, Some(0.5));
    assert_eq!(middle[5].detail, "1 compared · 1 refused");
    assert_eq!(middle[5].work, "F004 refused");
    assert!(
        middle
            .iter()
            .enumerate()
            .all(|(i, n)| i == 5 || n.state != State::Active)
    );
    event(
        &mut p,
        "event=confidence-pass state=finished completed=4 compared=3 total=4",
    );
    let done = journey.observe(1, &p);
    assert_eq!(done[5].fraction, Some(1.0));
    assert_ne!(
        done[5].state,
        State::Finished,
        "a completed confidence map is not a saved photograph"
    );
    event(
        &mut p,
        "event=render-step name=develop state=started total=4",
    );
    let developing = journey.observe(1, &p);
    assert_eq!(developing[5].title, None);
    assert_eq!(developing[5].state, State::Active);
    assert_eq!(
        developing[5].fraction, None,
        "confidence denominator cannot claim write/develop progress"
    );
    assert_eq!(developing[5].work, "3 compared · 1 refused");
}

#[test]
fn completed_confidence_cannot_reactivate_an_old_reconstruction_start_after_log_gap() {
    let mut p = PipelineProgress::default();
    let mut journey = ProcessJourney::default();
    event(
        &mut p,
        "event=render-step name=reconstruct state=started total=4",
    );
    assert_eq!(journey.observe(1, &p)[4].state, State::Active);
    // The reconstruct-finished line is deliberately absent, as after a log gap.
    event(
        &mut p,
        "event=confidence-pass state=started completed=0 compared=0 total=4",
    );
    let comparing = journey.observe(1, &p);
    assert_eq!(comparing[5].state, State::Active);
    assert_ne!(comparing[4].state, State::Active);
    event(
        &mut p,
        "event=confidence-pass state=finished completed=4 compared=3 total=4",
    );
    let finished = journey.observe(1, &p);
    assert_ne!(
        finished[4].state,
        State::Active,
        "completed later work cannot revive an older phase"
    );
    assert_eq!(finished[5].fraction, Some(1.0));
    assert_ne!(finished[5].state, State::Finished);
    event(
        &mut p,
        "event=render-step name=develop state=started total=4",
    );
    assert_eq!(journey.observe(1, &p)[5].state, State::Active);
}

#[test]
fn pair_bar_counts_refused_work_without_crediting_it_as_placement() {
    let mut p = PipelineProgress::default();
    event(&mut p, "event=align-phase name=pairs frames=4 total=6");
    event(
        &mut p,
        "event=align-pair i=0 j=2 completed=3 accepted=1 frames=4 total=6",
    );
    let mut journey = ProcessJourney::default();
    let nodes = journey.observe(1, &p);
    assert_eq!(nodes[1].value, "3 / 6");
    assert_eq!(nodes[1].fraction, Some(0.5));
    assert_eq!(nodes[1].detail, "1 direct fits");
    assert_ne!(nodes[1].state, State::Finished);
    event(
        &mut p,
        "event=align-result source=solved reference=0 placed=3 refused=1 frames=4 total=4",
    );
    let finished = journey.observe(1, &p);
    assert_eq!(
        finished[1].value, "3 / 6",
        "missing comparisons must remain missing after the result"
    );
    assert_eq!(finished[1].fraction, Some(0.5));
    assert_eq!(finished[1].detail, "3 placed · 1 refused");
}

#[test]
fn sparse_kernel_events_are_observed_counts_not_fake_percentages() {
    let mut p = PipelineProgress::default();
    event(
        &mut p,
        "event=merge-step name=decode state=finished index=17 level=none total=259",
    );
    event(
        &mut p,
        "event=merge-step name=pyramid state=finished index=230 level=none total=259",
    );
    let nodes = ProcessJourney::default().observe(1, &p);
    assert_eq!(nodes[0].value, "1 observed");
    assert_eq!(nodes[2].value, "1 observed");
    assert_eq!(nodes[0].fraction, None);
    assert_eq!(nodes[2].fraction, None);
    assert_eq!(nodes[3].value, "—");
    assert_eq!(nodes[3].fraction, None);
}

#[test]
fn accepted_and_processed_are_separate_and_finished_fold_is_not_saved() {
    let mut p = PipelineProgress::default();
    event(
        &mut p,
        "event=frame-finished index=3 processed=4 accepted=3 total=4",
    );
    let nodes = ProcessJourney::default().observe(1, &p);
    assert_eq!(nodes[3].value, "4 / 4");
    assert_eq!(nodes[3].detail, "3 accepted into stack");
    assert_eq!(nodes[3].state, State::Active);
    assert_eq!(nodes[3].fraction, Some(1.0));
    assert_eq!(nodes[4].state, State::Waiting);
    assert_eq!(nodes[5].state, State::Waiting);
}

#[test]
fn cached_and_bypassed_geometry_do_not_invent_comparison_work() {
    for source in ["cache", "off"] {
        let mut p = PipelineProgress::default();
        let (placed, refused) = if source == "cache" { (3, 1) } else { (0, 0) };
        event(
            &mut p,
            &format!(
                "event=align-result source={source} reference=0 placed={placed} refused={refused} frames=4 total=4"
            ),
        );
        let nodes = ProcessJourney::default().observe(1, &p);
        assert_eq!(nodes[1].fraction, None);
        if source == "off" {
            assert_eq!(nodes[1].state, State::Bypassed);
            assert_eq!(nodes[1].value, "BYPASSED");
        } else {
            assert_eq!(nodes[1].unit, "frames placed");
            assert_eq!(nodes[1].value, "3 / 4");
        }
    }
}

#[test]
fn gathering_reads_fitted_samples_without_restarting_registration() {
    let mut p = PipelineProgress::default();
    event(
        &mut p,
        "event=align-result source=cache reference=0 placed=4 refused=0 frames=4 total=4",
    );
    event(
        &mut p,
        "event=merge-step name=gather state=started index=2 level=none total=4",
    );
    let nodes = ProcessJourney::default().observe(1, &p);
    assert_ne!(nodes[0].state, State::Active);
    assert_eq!(nodes[0].work, "gather ×1");
    assert_eq!(nodes[3].state, State::Active);
    assert_eq!(nodes[1].state, State::Finished);
    assert_eq!(nodes[1].value, "4 / 4");
    assert_eq!(nodes[1].fraction, None);
}

#[test]
fn reconstruction_remains_visible_and_save_waits_for_terminal_success() {
    let mut p = PipelineProgress::default();
    let mut journey = ProcessJourney::default();
    event(
        &mut p,
        "event=render-step name=reconstruct state=started total=4",
    );
    let rebuilding = journey.observe(1, &p);
    assert_eq!(rebuilding[4].state, State::Active);
    assert_eq!(rebuilding[4].fraction, None);
    event(
        &mut p,
        "event=render-step name=reconstruct state=finished total=4",
    );
    assert_eq!(journey.observe(1, &p)[4].state, State::Finished);
    event(&mut p, "event=render-step name=write state=started total=4");
    let writing = journey.observe(1, &p);
    assert_eq!(writing[4].value, "PLANES READY");
    assert_eq!(writing[5].state, State::Active);
    assert_eq!(writing[5].fraction, None);
    event(
        &mut p,
        "event=render-step name=write state=finished total=4",
    );
    let written = journey.observe(1, &p);
    assert_eq!(written[5].value, "TIFF WRITTEN");
    assert_ne!(written[5].state, State::Finished);
    p.mark_complete();
    assert_eq!(journey.observe(1, &p)[5].value, "SAVED");
    let reset = journey.observe(2, &PipelineProgress::default());
    assert!(reset.iter().all(|node| node.state == State::Waiting));
}

#[test]
fn latest_observed_operation_is_stopped_without_erasing_accrued_counts() {
    let mut p = PipelineProgress::default();
    let mut journey = ProcessJourney::default();
    event(
        &mut p,
        "event=frame-finished index=0 processed=1 accepted=1 total=4",
    );
    event(
        &mut p,
        "event=merge-step name=fold state=started index=3 level=2 total=4",
    );
    let active = journey.observe(1, &p);
    assert_eq!(active[3].state, State::Active);
    assert_eq!(active[3].detail, "1 accepted into stack");
    assert_eq!(active[3].work, "fold ×1");
    event(
        &mut p,
        "event=merge-step name=fold state=finished index=3 level=2 total=4",
    );
    let _ = journey.observe(1, &p);
    p.mark_cancelled();
    let stopped = journey.observe(1, &p);
    assert_eq!(stopped[3].state, State::Stopped);
    assert_eq!(stopped[3].value, "1 / 4");
    assert_eq!(stopped[3].fraction, Some(0.25));
    assert_eq!(stopped[3].detail, "cancelled");
    assert!(stopped.iter().all(|node| node.work.is_empty()));
    assert_eq!(stopped[5].state, State::Waiting);
}

#[test]
fn sub_200ms_interleaved_workers_cannot_move_the_phase_anchor() {
    // Failure stimulus: every one of these events used to move or remove LIVE
    // because the last kernel event masqueraded as the whole pipeline phase.
    // Exercise real parsing and actual painted LIVE position, not an expected
    // phase copied from a helper. Several captures work concurrently.
    let ctx = egui::Context::default();
    let mut journey = ProcessJourney::default();
    let mut p = PipelineProgress::default();
    event(
        &mut p,
        "event=frame-finished index=7 processed=1 accepted=1 total=8",
    );
    let events = [
        "event=merge-step name=decode state=started index=3 level=none total=8",
        "event=merge-step name=gather state=started index=2 level=none total=8",
        "event=merge-step name=pyramid state=started index=1 level=none total=8",
        "event=merge-step name=focus state=started index=0 level=2 total=8",
        "event=merge-step name=fold state=started index=0 level=2 total=8",
        "event=merge-step name=decode state=finished index=3 level=none total=8",
        "event=merge-step name=gather state=finished index=2 level=none total=8",
        "event=merge-step name=pyramid state=finished index=1 level=none total=8",
        "event=merge-step name=fold state=finished index=0 level=2 total=8",
        "event=merge-step name=decode state=started index=4 level=none total=8",
    ];
    let draw = |journey: &mut ProcessJourney, p: &PipelineProgress, time: f64| {
        ctx.run(
            egui::RawInput {
                screen_rect: Some(Rect::from_min_size(
                    egui::Pos2::ZERO,
                    egui::vec2(1000.0, HEIGHT),
                )),
                time: Some(time),
                ..Default::default()
            },
            |ctx| {
                egui::CentralPanel::default()
                    .frame(egui::Frame::NONE)
                    .show(ctx, |ui| journey.show(ui, ui.max_rect(), 1, p));
            },
        )
    };
    let anchor = |output: &egui::FullOutput| {
        let live: Vec<_> = output
            .shapes
            .iter()
            .filter_map(|shape| match &shape.shape {
                egui::Shape::Text(text) if text.galley.text() == "LIVE" => Some(text.pos),
                _ => None,
            })
            .collect();
        assert_eq!(live.len(), 1);
        (live[0].x / (1000.0 / 6.0)).floor() as usize
    };
    let mut concurrent = false;
    let mut no_open_work = false;
    for (index, fields) in events.iter().enumerate() {
        event(&mut p, fields);
        let time = index as f64 * 0.015;
        assert!(time < 0.2);
        let nodes = journey.observe(1, &p);
        assert_eq!(nodes[3].value, "1 / 8");
        assert_eq!(nodes[3].detail, "1 accepted into stack");
        assert_eq!(nodes[3].fraction, Some(0.125));
        assert!(
            nodes
                .iter()
                .enumerate()
                .all(|(i, n)| (n.state == State::Active) == (i == 3))
        );
        assert_eq!(anchor(&draw(&mut journey, &p, time)), 3);
        if index == 4 {
            assert_eq!(nodes[0].work, "decode ×1 · gather ×1");
            assert_eq!(nodes[2].work, "scales ×1");
            assert_eq!(nodes[3].work, "fold ×1");
            concurrent = true;
        }
        if index == 8 {
            assert!(nodes.iter().all(|node| node.work.is_empty()));
            no_open_work = true;
        }
    }
    assert!(concurrent && no_open_work);
    assert_eq!(journey.observe(1, &p)[0].value, "1 observed");
    assert_eq!(journey.observe(1, &p)[2].value, "1 observed");
    event(
        &mut p,
        "event=render-step name=reconstruct state=started total=8",
    );
    assert_eq!(anchor(&draw(&mut journey, &p, 0.15)), 4);
    assert!(journey.observe(1, &p).iter().all(|n| n.work.is_empty()));
}

#[test]
fn all_six_operations_paint_together_and_idle_time_changes_no_progress() {
    let ctx = egui::Context::default();
    let mut journey = ProcessJourney::default();
    let mut p = PipelineProgress::default();
    event(
        &mut p,
        "event=frame-finished index=0 processed=1 accepted=1 total=4",
    );
    let draw = |journey: &mut ProcessJourney, time| {
        ctx.run(
            egui::RawInput {
                screen_rect: Some(Rect::from_min_size(
                    egui::Pos2::ZERO,
                    egui::vec2(1000.0, HEIGHT),
                )),
                time: Some(time),
                ..Default::default()
            },
            |ctx| {
                egui::CentralPanel::default()
                    .frame(egui::Frame::NONE)
                    .show(ctx, |ui| {
                        journey.show(ui, ui.max_rect(), 1, &p);
                    });
            },
        )
    };
    let first = draw(&mut journey, 0.0);
    let later = draw(&mut journey, 1000.0);
    let labels = |output: &egui::FullOutput| -> Vec<String> {
        output
            .shapes
            .iter()
            .filter_map(|shape| match &shape.shape {
                egui::Shape::Text(text) => Some(text.galley.text().to_owned()),
                _ => None,
            })
            .collect()
    };
    let first_labels = labels(&first);
    assert!(
        TITLES
            .iter()
            .all(|title| first_labels.iter().any(|text| text == title))
    );
    assert_eq!(
        first_labels,
        labels(&later),
        "wall time without evidence must not advance the journey"
    );
    assert_eq!(journey.observe(1, &p)[3].fraction, Some(0.25));
}

#[test]
fn active_operation_is_explicit_and_compact_text_stays_inside_its_node() {
    let ctx = egui::Context::default();
    let mut journey = ProcessJourney::default();
    let mut p = PipelineProgress::default();
    event(
        &mut p,
        "event=render-step name=write state=started total=259",
    );
    let output = ctx.run(
        egui::RawInput {
            screen_rect: Some(Rect::from_min_size(
                egui::Pos2::ZERO,
                egui::vec2(1000.0, HEIGHT),
            )),
            ..Default::default()
        },
        |ctx| {
            egui::CentralPanel::default()
                .frame(egui::Frame::NONE)
                .show(ctx, |ui| {
                    journey.show(ui, ui.max_rect(), 1, &p);
                });
        },
    );
    let mut live = 0;
    for shape in &output.shapes {
        if let egui::Shape::Text(text) = &shape.shape {
            live += usize::from(text.galley.text() == "LIVE");
            let bounds = Rect::from_min_size(text.pos, text.galley.size());
            assert!(
                shape.clip_rect.expand(0.1).contains_rect(bounds),
                "clipped journey text: {}",
                text.galley.text()
            );
        }
    }
    assert_eq!(
        live, 1,
        "one actual active operation must have an explicit LIVE label"
    );
    assert_eq!(
        journey.observe(1, &p)[5].fraction,
        None,
        "LIVE is not an invented within-write percentage"
    );
}
