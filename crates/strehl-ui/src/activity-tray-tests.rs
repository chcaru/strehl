//! The tray: what it lists and the intent each control returns.
use super::*;
use crate::activity::{ActivityKind, Lane};
use eframe::egui::{Event, Modifiers, PointerButton, RawInput};
use std::{path::PathBuf, time::Duration};

struct Harness {
    ctx: egui::Context,
    time: f64,
    palette: LibraryPalette,
}
impl Harness {
    fn new() -> Self {
        let ctx = egui::Context::default();
        crate::theme::install(&ctx);
        Self {
            ctx,
            time: 0.0,
            palette: LibraryPalette::graphite(),
        }
    }
    /// One frame; a popover's first frame is egui's invisible sizing pass,
    /// so a fresh tray is drawn twice.
    fn frame(
        &mut self,
        activities: &Activities,
        quiet: (bool, bool),
        events: Vec<Event>,
    ) -> (egui::FullOutput, Option<TrayIntent>) {
        if self.time == 0.0 {
            self.once(activities, quiet, vec![]);
        }
        self.once(activities, quiet, events)
    }
    fn once(
        &mut self,
        activities: &Activities,
        quiet: (bool, bool),
        events: Vec<Event>,
    ) -> (egui::FullOutput, Option<TrayIntent>) {
        self.time += 1.0 / 60.0;
        let mut intent = None;
        let input = RawInput {
            events,
            time: Some(self.time),
            screen_rect: Some(Rect::from_min_size(Pos2::ZERO, Vec2::new(1680.0, 1050.0))),
            ..Default::default()
        };
        let palette = self.palette;
        let output = self.ctx.run(input, |ctx| {
            intent = show(
                ctx,
                Pos2::new(1554.0, 43.0),
                TrayInputs {
                    activities,
                    quiet_switch: quiet.0,
                    quiet_holds: quiet.1,
                    palette: &palette,
                    now: Instant::now(),
                    unix: unix_now(),
                },
            );
        });
        (output, intent)
    }
    fn click(
        &mut self,
        activities: &Activities,
        quiet: (bool, bool),
        at: Pos2,
    ) -> Option<TrayIntent> {
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
fn find(output: &egui::FullOutput, needle: &str) -> Option<Pos2> {
    fn visit(shape: &egui::Shape, needle: &str) -> Option<Pos2> {
        match shape {
            egui::Shape::Text(t) if t.galley.text() == needle => {
                Some(t.pos + t.galley.size() * 0.5)
            }
            egui::Shape::Vec(v) => v.iter().find_map(|s| visit(s, needle)),
            _ => None,
        }
    }
    output.shapes.iter().find_map(|s| visit(&s.shape, needle))
}
fn texts(output: &egui::FullOutput) -> Vec<String> {
    fn visit(shape: &egui::Shape, out: &mut Vec<String>) {
        match shape {
            egui::Shape::Text(t) => out.push(t.galley.text().to_owned()),
            egui::Shape::Vec(v) => v.iter().for_each(|s| visit(s, out)),
            _ => {}
        }
    }
    let mut out = Vec::new();
    output.shapes.iter().for_each(|s| visit(&s.shape, &mut out));
    out
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
    .with_cancel(CancelMode::Kill);
    stack.eta = Some(Duration::from_secs(198));
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
fn the_tray_lists_running_waiting_and_earlier_work() {
    let (activities, _, _) = busy();
    let mut harness = Harness::new();
    let (output, _) = harness.frame(&activities, (false, false), vec![]);
    let all = texts(&output);
    for text in [
        "ACTIVITY",
        "Quiet",
        "Stack · Blue weevil, dorsal",
        "WAITING · 1",
        "Stack · Bumblebee, frontal",
        "183 planes · about 1 min",
        "EARLIER TODAY",
        "FULL LOG",
        "Calibrate step",
        "REVEAL",
    ] {
        assert!(all.iter().any(|t| t == text), "{text} missing from {all:?}");
    }
    let detail = all
        .iter()
        .find(|t| t.starts_with("Merge · 120 of 299"))
        .expect("phase, frames and time left");
    assert!(
        detail.contains("3 min 18 s left") && detail.contains("ends "),
        "{detail}"
    );
    assert!(
        all.iter()
            .any(|t| t.starts_with("Step 7 suggested") && t.ends_with("took 1 min 8 s")),
        "{all:?}"
    );
    assert!(!all.iter().any(|t| t == "Quiet holds heavy work"));
    let (output, _) = harness.frame(&activities, (true, true), vec![]);
    assert!(find(&output, "Quiet holds heavy work").is_some());
    let (output, _) = harness.frame(&Activities::default(), (false, false), vec![]);
    assert!(find(&output, "Nothing running").is_some());
    assert!(find(&output, "EARLIER TODAY").is_none());
}

#[test]
fn every_control_returns_its_intent() {
    let (activities, stack_id, queue_id) = busy();
    let mut harness = Harness::new();
    let (output, _) = harness.frame(&activities, (false, false), vec![]);
    let at = find(&output, "STOP").unwrap();
    assert_eq!(
        harness.click(&activities, (false, false), at),
        Some(TrayIntent::Cancel(stack_id))
    );
    let at = find(&output, "REMOVE").unwrap();
    assert_eq!(
        harness.click(&activities, (false, false), at),
        Some(TrayIntent::Remove(queue_id))
    );
    let at = find(&output, "FULL LOG").unwrap();
    assert_eq!(
        harness.click(&activities, (false, false), at),
        Some(TrayIntent::FullLog)
    );
    let at = find(&output, "REVEAL").unwrap();
    assert_eq!(
        harness.click(&activities, (false, false), at),
        Some(TrayIntent::Action(ActionId::Reveal {
            path: PathBuf::from("exports/weevil-dorsal-web.jpg")
        }))
    );
    // The switch sits right of "Quiet".
    let quiet = find(&output, "Quiet").unwrap();
    assert_eq!(
        harness.click(&activities, (false, false), quiet + Vec2::new(40.0, 0.0)),
        Some(TrayIntent::SetQuiet(true))
    );
    assert_eq!(
        harness.click(&activities, (true, false), quiet + Vec2::new(40.0, 0.0)),
        Some(TrayIntent::SetQuiet(false))
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
        Some(TrayIntent::ResumeQueue)
    );
}

/// Offscreen picture of the tray for the side-by-side check against the
/// mockup's `capture-flight-jobs.png`. `STREHL_P5_SHOTS` names the folder.
#[test]
#[ignore = "needs a GPU; writes a PNG into STREHL_P5_SHOTS"]
fn offscreen_tray_picture() {
    let shots = PathBuf::from(std::env::var_os("STREHL_P5_SHOTS").expect("STREHL_P5_SHOTS"));
    std::fs::create_dir_all(&shots).unwrap();
    let (activities, _, _) = busy();
    let palette = LibraryPalette::graphite();
    crate::library_station::visual_tests::render(&shots.join("tray.png"), |ui| {
        ui.painter()
            .rect_filled(ui.max_rect(), CornerRadius::ZERO, palette.bg);
        show(
            ui.ctx(),
            Pos2::new(1554.0, 43.0),
            TrayInputs {
                activities: &activities,
                quiet_switch: false,
                quiet_holds: true,
                palette: &palette,
                now: Instant::now(),
                unix: unix_now(),
            },
        );
        true
    })
    .unwrap();
}
