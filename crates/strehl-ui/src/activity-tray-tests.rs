//! The tray: what it lists and the action each control returns.
use super::*;
use crate::activity::{ActivityKind, Lane};
use crate::notices::Source;
use eframe::egui::{Event, Modifiers, PointerButton, Pos2, RawInput, Rect, Vec2};
use std::{path::PathBuf, time::Duration};

struct Harness {
    ctx: egui::Context,
    time: f64,
    notices: Notices,
}
impl Harness {
    fn new() -> Self {
        let ctx = egui::Context::default();
        crate::theme::install(&ctx);
        Self {
            ctx,
            time: 0.0,
            notices: Notices::default(),
        }
    }
    /// One frame of the tray in a 430-wide column.
    fn frame(
        &mut self,
        activities: &Activities,
        quiet: (bool, bool),
        events: Vec<Event>,
    ) -> (egui::FullOutput, Option<TrayAction>) {
        self.time += 1.0 / 60.0;
        let mut action = None;
        let input = RawInput {
            events,
            time: Some(self.time),
            screen_rect: Some(Rect::from_min_size(Pos2::ZERO, Vec2::new(800.0, 1400.0))),
            ..Default::default()
        };
        let notices = &mut self.notices;
        let output = self.ctx.run(input, |ctx| {
            egui::CentralPanel::default().show(ctx, |ui| {
                action = tray(
                    ui,
                    TrayInputs {
                        activities,
                        notices,
                        status: "Ready",
                        quiet: quiet.0,
                        quiet_holds: quiet.1,
                        now: Instant::now(),
                        unix: unix_now(),
                    },
                );
            });
        });
        (output, action)
    }
    fn click(
        &mut self,
        activities: &Activities,
        quiet: (bool, bool),
        at: Pos2,
    ) -> Option<TrayAction> {
        // Clicks a second apart never pair up as double clicks.
        self.time += 1.0;
        let button = |pressed| Event::PointerButton {
            pos: at,
            button: PointerButton::Primary,
            pressed,
            modifiers: Modifiers::NONE,
        };
        let (_, first) = self.frame(
            activities,
            quiet,
            vec![Event::PointerMoved(at), button(true)],
        );
        let (_, second) = self.frame(activities, quiet, vec![button(false)]);
        second.or(first)
    }
}
fn unix_now() -> u64 {
    crate::workspace_history::timestamp()
}
fn visit(shape: &egui::Shape, out: &mut Vec<(String, Pos2)>) {
    match shape {
        egui::Shape::Text(t) => out.push((
            t.galley.text().to_owned(),
            t.visual_bounding_rect().center(),
        )),
        egui::Shape::Vec(v) => v.iter().for_each(|s| visit(s, out)),
        _ => {}
    }
}
fn texts(output: &egui::FullOutput) -> Vec<(String, Pos2)> {
    let mut out = Vec::new();
    output.shapes.iter().for_each(|s| visit(&s.shape, &mut out));
    out
}
fn find(output: &egui::FullOutput, needle: &str) -> Option<Pos2> {
    texts(output)
        .into_iter()
        .find(|(t, _)| t == needle)
        .map(|(_, at)| at)
}

fn busy() -> (Activities, u64, u64) {
    let mut activities = Activities::default();
    let now = Instant::now();
    activities.record(HistoryEntry {
        kind: ActivityKind::Export,
        title: "Export · 2 files".into(),
        stack: None,
        outcome: "done".into(),
        summary: "weevil-dorsal-web.jpg, weevil-dorsal-hdr.avif".into(),
        finished: unix_now(),
        took_seconds: Some(12.0),
        action: Some(ActionId::Reveal {
            path: PathBuf::from("exports/weevil-dorsal-web.jpg"),
        }),
        log: None,
    });
    activities.record(HistoryEntry {
        kind: ActivityKind::Calibration,
        title: "Calibrate step".into(),
        stack: None,
        outcome: "done".into(),
        summary: "Step 7 suggested · four-shot mode restored".into(),
        finished: unix_now(),
        took_seconds: Some(68.0),
        action: None,
        log: None,
    });
    activities.begin();
    let mut stack = ActivityStatus::new(
        ActivityKind::Stack,
        "run",
        "Stack · Blue weevil, dorsal",
        Lane::Heavy,
    )
    .with_phase("Merge")
    .with_progress(Some(120), Some(299))
    .with_cancel(CancelMode::Cooperative);
    stack.eta = Some(Duration::from_secs(198));
    stack.facts = "32 workers · 299 RAW · 61.4 GiB".into();
    let stack_id = stack.id;
    activities.report(stack);
    let mut queued = ActivityStatus::new(
        ActivityKind::Stack,
        "queued:7",
        "Stack · Bumblebee, frontal",
        Lane::Heavy,
    )
    .with_state(ActivityState::Waiting {
        for_what: "the stack before it".into(),
        gives_up: None,
    })
    .with_phase("183 planes · about 1 min")
    .with_cancel(CancelMode::Cooperative);
    queued.queued = Some(7);
    activities.report(queued);
    activities.end(now, unix_now());
    (activities, stack_id, 7)
}

#[test]
fn the_tray_lists_running_waiting_earlier_work_and_notices() {
    let (activities, _, _) = busy();
    let mut harness = Harness::new();
    harness
        .notices
        .push(Severity::Done, Source::Export, "Exported weevil.avif", None);
    harness.notices.push(
        Severity::Failure,
        Source::Stack,
        "The engine stopped",
        Some(notices::Action::OpenLog),
    );
    let (output, _) = harness.frame(&activities, (true, false), vec![]);
    let all: Vec<String> = texts(&output).into_iter().map(|(t, _)| t).collect();
    for text in [
        "ACTIVITY",
        "Quiet",
        "Stack · Blue weevil, dorsal",
        "STOP",
        "WAITING · 1",
        "start when the running stack ends",
        "Stack · Bumblebee, frontal",
        "183 planes · about 1 min",
        "REMOVE",
        "EARLIER TODAY",
        "FULL LOG",
        "Calibrate step",
        "REVEAL",
        "NOTICES",
        "MARK ALL READ",
        "The engine stopped",
        "Exported weevil.avif",
        "ENGINE LOG",
        "AGENT",
    ] {
        assert!(all.iter().any(|t| t == text), "{text} missing from {all:?}");
    }
    let detail = all
        .iter()
        .find(|t| t.starts_with("Merge · 120 / 299"))
        .expect("phase, planes and time left");
    assert!(
        detail.contains("3 min 18 s left · ends ")
            && detail.ends_with("32 workers · 299 RAW · 61.4 GiB"),
        "{detail}"
    );
    assert!(
        all.iter()
            .any(|t| t.starts_with("Step 7 suggested") && t.ends_with("took 1 min 8 s")),
        "{all:?}"
    );
    // The order of the mockup (running work, the queue, earlier today),
    // then the notices, newest first.
    let y = |text| find(&output, text).unwrap().y;
    assert!(y("The engine stopped") < y("Exported weevil.avif"));
    assert!(y("Stack · Blue weevil, dorsal") < y("WAITING · 1"));
    assert!(y("WAITING · 1") < y("EARLIER TODAY"));
    assert!(y("EARLIER TODAY") < y("NOTICES"));
    // A counted task shows its progress rule in the ok colour of the theme.
    let ok = crate::studio_theme::tokens(&harness.ctx).ok;
    let bar = output.shapes.iter().any(
        |s| matches!(&s.shape, egui::Shape::Rect(r) if r.rect.height() == 2.0 && r.fill == ok),
    );
    assert!(bar, "a counted task shows its progress rule");
    assert!(!all.iter().any(|t| t == "Quiet holds heavy work"));
    let (output, _) = harness.frame(&activities, (true, true), vec![]);
    assert!(find(&output, "Quiet holds heavy work").is_some());
    let (output, _) = harness.frame(&Activities::default(), (true, false), vec![]);
    assert!(find(&output, "Nothing running").is_some());
    assert!(find(&output, "EARLIER TODAY").is_none());
    assert!(find(&output, "WAITING · 1").is_none());
}

#[test]
fn every_control_returns_its_action() {
    let (activities, stack_id, queue_id) = busy();
    let mut harness = Harness::new();
    harness.notices.push(
        Severity::Failure,
        Source::Stack,
        "The engine stopped",
        Some(notices::Action::OpenLog),
    );
    let (output, _) = harness.frame(&activities, (false, false), vec![]);
    let at = |text| find(&output, text).unwrap_or_else(|| panic!("{text}"));
    let cases = [
        ("STOP", TrayAction::Cancel(stack_id)),
        ("REMOVE", TrayAction::Remove(queue_id)),
        ("FULL LOG", TrayAction::OpenLog),
        (
            "REVEAL",
            TrayAction::Action(ActionId::Reveal {
                path: PathBuf::from("exports/weevil-dorsal-web.jpg"),
            }),
        ),
        ("LOG", TrayAction::Notice(notices::Action::OpenLog)),
        ("ENGINE LOG", TrayAction::OpenLog),
        ("AGENT", TrayAction::OpenAgent),
    ];
    for (text, expected) in cases {
        let point = at(text);
        assert_eq!(
            harness.click(&activities, (false, false), point),
            Some(expected),
            "{text}"
        );
    }
    // The switch sits right of "Quiet".
    let quiet = at("Quiet");
    assert_eq!(
        harness.click(&activities, (false, false), quiet + Vec2::new(30.0, 0.0)),
        Some(TrayAction::SetQuiet(true))
    );
    assert_eq!(
        harness.click(&activities, (true, false), quiet + Vec2::new(30.0, 0.0)),
        Some(TrayAction::SetQuiet(false))
    );
    // A paused queue offers Resume.
    let mut paused = Activities::default();
    paused.begin();
    let mut queued =
        ActivityStatus::new(ActivityKind::Stack, "queued:1", "Stack · Bee", Lane::Heavy)
            .with_state(ActivityState::Waiting {
                for_what: "you to resume the queue".into(),
                gives_up: None,
            });
    queued.queued = Some(1);
    paused.report(queued);
    paused.end(Instant::now(), unix_now());
    let (output, _) = harness.frame(&paused, (false, false), vec![]);
    let at = find(&output, "RESUME").expect("a paused queue offers Resume");
    assert_eq!(
        harness.click(&paused, (false, false), at),
        Some(TrayAction::ResumeQueue)
    );
}

#[test]
fn work_that_cannot_stop_offers_no_stop_and_dismiss_removes_a_notice() {
    let mut activities = Activities::default();
    activities.begin();
    activities.report(
        ActivityStatus::running(ActivityKind::CompactApply, "Compacting", Lane::Heavy)
            .with_cancel(CancelMode::None),
    );
    activities.end(Instant::now(), unix_now());
    let mut harness = Harness::new();
    harness
        .notices
        .push(Severity::Info, Source::App, "Preferences saved", None);
    let (output, _) = harness.frame(&activities, (true, false), vec![]);
    assert!(find(&output, "Compacting").is_some());
    assert!(
        find(&output, "STOP").is_none(),
        "compaction runs to its end"
    );
    let dismiss = find(&output, "Dismiss").unwrap();
    harness.click(&activities, (true, false), dismiss);
    assert_eq!(harness.notices.len(), 0);
    let (output, _) = harness.frame(&activities, (true, false), vec![]);
    assert!(find(&output, "No notices").is_some());
}

/// Offscreen pictures of the tray in each theme, for the side-by-side check
/// against the mockup's `capture-flight-jobs.png`. `STREHL_P5_SHOTS` names
/// the folder.
#[test]
#[ignore = "needs a GPU; writes PNGs into STREHL_P5_SHOTS"]
fn offscreen_tray_pictures() {
    use crate::studio_theme::{Surround, ThemeName};
    let shots = PathBuf::from(std::env::var_os("STREHL_P5_SHOTS").expect("STREHL_P5_SHOTS"));
    std::fs::create_dir_all(&shots).unwrap();
    let (activities, _, _) = busy();
    for (name, theme) in [
        ("graphite", ThemeName::Graphite),
        ("instrument", ThemeName::Instrument),
        ("lightbox", ThemeName::Lightbox),
    ] {
        let mut notices = Notices::default();
        notices.push(
            Severity::Failure,
            Source::Stack,
            "The engine stopped",
            Some(notices::Action::OpenLog),
        );
        let destination = shots.join(format!("tray-{name}.png"));
        crate::library_station::visual_tests::render(&destination, |ui| {
            crate::studio_theme::apply(ui.ctx(), theme, Surround::Theme, false);
            let t = crate::studio_theme::tokens(ui.ctx());
            ui.painter().rect_filled(ui.max_rect(), 0.0, t.bg);
            let area = Rect::from_min_size(Pos2::new(1124.0, 43.0), Vec2::new(432.0, 1000.0));
            ui.scope_builder(egui::UiBuilder::new().max_rect(area), |ui| {
                egui::Frame::new()
                    .fill(t.panel)
                    .stroke(egui::Stroke::new(1.0_f32, t.line2))
                    .show(ui, |ui| {
                        tray(
                            ui,
                            TrayInputs {
                                activities: &activities,
                                notices: &mut notices,
                                status: "Ready",
                                quiet: true,
                                quiet_holds: true,
                                now: Instant::now(),
                                unix: unix_now(),
                            },
                        )
                    });
            });
            true
        })
        .unwrap();
    }
}
