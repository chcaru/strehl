//! Glance mode (Studio 2, 7.4; mockup `glance.html`): a full-screen status
//! readable from across the room. The colour bar says the state (green: fine;
//! amber: needs you; red: stopped; blue: done), the dial has one tick per
//! plane (pooled above 180), and four health lines and a sentence say what
//! happens next. `G` opens it from the in-flight view; Escape returns.
use eframe::egui::{self, Align2, Color32, Rect, Stroke, TextureId, Ui};

use super::flight::{self, Headline};
use super::follow::Progress;
use super::style::{self, CapturePalette, Mark};
use crate::capture_client::{Snapshot, host::HostPhase};

/// The state glance mode reads out.
#[derive(Clone, Debug, PartialEq, Eq)]
pub(crate) enum GlanceState {
    /// Running; nothing needs the user.
    Fine,
    /// Waiting for the user (paused, or a problem it cannot solve alone).
    NeedsYou(String),
    /// Stopped before the plan's end, or the camera faulted.
    Stopped(String),
    /// Finished.
    Done(String),
}

impl GlanceState {
    pub fn color(&self, palette: &CapturePalette) -> Color32 {
        match self {
            Self::Fine => palette.ok,
            Self::NeedsYou(_) => palette.warn,
            Self::Stopped(_) => palette.bad,
            Self::Done(_) => palette.info,
        }
    }
}

/// What the screen says will happen when the capture finishes.
#[derive(Clone, Copy, Debug, Default, PartialEq, Eq)]
pub(crate) struct Next {
    pub stack: bool,
    pub power_down: bool,
}

/// The state from the host's phase, its failure and the transfer.
pub(crate) fn glance_state(s: &Snapshot, h: &Headline) -> GlanceState {
    let host = &s.host;
    if let Some(failure) = &host.failure {
        return GlanceState::Stopped(format!(
            "{} at plane {}. The {} planes taken are kept.",
            failure.message.as_deref().unwrap_or("The camera stopped"),
            h.plane + 1,
            h.plane
        ));
    }
    match host.phase {
        HostPhase::Complete => GlanceState::Done(format!(
            "Finished: {} planes, {} RAWs.",
            h.plane, h.raws_taken
        )),
        HostPhase::Stopped => GlanceState::Stopped(format!(
            "Stopped at plane {}. The {} planes taken are kept as a stopped capture.",
            h.plane, h.plane
        )),
        HostPhase::Fault | HostPhase::Disconnected => GlanceState::Stopped(format!(
            "{} at plane {}.",
            host.message.as_deref().unwrap_or("The camera stopped"),
            h.plane
        )),
        HostPhase::Paused => GlanceState::NeedsYou(format!(
            "Paused at plane {}. The camera is holding focus.",
            h.plane
        )),
        _ if !s.fresh() => GlanceState::NeedsYou(
            "The camera host stopped answering. The capture goes on on the Pi; check the network."
                .into(),
        ),
        _ if host.storage.mode.as_deref() == Some("host-pc")
            && s.receiver["ok"] != true
            && s.receiver_error.is_some() =>
        {
            GlanceState::NeedsYou(
                "The receiver on this PC stopped answering. RAWs wait on the Pi while its memory lasts."
                    .into(),
            )
        }
        _ => GlanceState::Fine,
    }
}

/// The footer's sentence: the state's own, or what happens next.
pub(crate) fn next_sentence(state: &GlanceState, next: Next) -> String {
    match state {
        GlanceState::Fine => {
            let what = match (next.stack, next.power_down) {
                (true, true) => "it will be stacked and the rig will power down",
                (true, false) => "it will be stacked",
                (false, true) => "the rig will power down",
                (false, false) => "it waits for you",
            };
            format!("Nothing needs you. When it finishes, {what}.")
        }
        GlanceState::NeedsYou(s) | GlanceState::Stopped(s) | GlanceState::Done(s) => s.clone(),
    }
}

/// The four health lines in glance words.
pub(crate) fn glance_lines(
    s: &Snapshot,
    h: &Headline,
    progress: Option<&Progress>,
) -> [(Mark, String, String); 4] {
    let lines = flight::health(s, progress, progress.is_some());
    let behind = s.host.storage.pending_frames.unwrap_or(0);
    let pace = (
        if h.paused { Mark::Warn } else { Mark::Ok },
        if h.paused { "Paused" } else { "On track" }.to_owned(),
        h.per_plane
            .map(|p| format!("{p:.1} s per plane"))
            .unwrap_or_default(),
    );
    let files = if s.host.storage.mode.as_deref() == Some("host-pc") {
        (
            lines[0].mark,
            "Files arriving".to_owned(),
            format!("{behind} RAWs behind"),
        )
    } else {
        (
            Mark::Idle,
            "On the card".to_owned(),
            "RAWs stay on the camera".to_owned(),
        )
    };
    let planes = match progress {
        Some(p) => (
            lines[1].mark,
            "Planes pass".to_owned(),
            format!(
                "{} of {}{}",
                p.passed.max(p.checked.saturating_sub(p.attention)),
                p.checked,
                if p.retaken > 0 {
                    format!(" · {} retaken", p.retaken)
                } else {
                    String::new()
                }
            ),
        ),
        None => (
            Mark::Idle,
            "Not checked".to_owned(),
            "checking is off".to_owned(),
        ),
    };
    let free = s.receiver["free_bytes"].as_u64();
    let disk = (
        lines[2].mark,
        if lines[2].mark == Mark::Ok {
            "Disk fine"
        } else {
            "Disk"
        }
        .to_owned(),
        free.map(|f| format!("{:.0} GB free", f as f64 / 1e9))
            .unwrap_or_default(),
    );
    [pace, files, planes, disk]
}

/// Everything glance mode shows.
pub(crate) struct GlanceInputs<'a> {
    pub s: &'a Snapshot,
    pub progress: Option<&'a Progress>,
    pub proof: Option<(TextureId, egui::Vec2)>,
    /// "Blue weevil · Dorsal · 2.8× · proof from planes 1–61".
    pub caption: String,
    pub next: Next,
}

/// Draws glance mode over the whole of `ui`; `true` when Escape asks to
/// return.
pub(crate) fn show(ui: &mut Ui, inputs: &GlanceInputs<'_>, palette: &CapturePalette) -> bool {
    let r = ui.max_rect();
    let p = ui.painter().clone();
    let bg = Color32::from_rgb(6, 6, 7);
    p.rect_filled(r, 0.0, bg);
    let h = flight::headline(inputs.s);
    let state = glance_state(inputs.s, &h);
    let color = state.color(palette);
    p.rect_filled(
        Rect::from_min_size(r.min, egui::vec2(r.width(), 6.0)),
        0.0,
        color,
    );
    let main = Rect::from_min_max(
        egui::pos2(r.left() + 70.0, r.top() + 6.0),
        egui::pos2(r.right() - 70.0, r.bottom() - 160.0),
    );
    // The proof at the left.
    let proof = Rect::from_min_size(
        egui::pos2(main.left(), main.center().y - 166.0),
        egui::vec2(500.0, 333.0),
    );
    p.rect_filled(proof, 0.0, Color32::BLACK);
    if let Some((id, size)) = inputs.proof
        && size.x > 0.0
    {
        let scale = (proof.width() / size.x).min(proof.height() / size.y);
        let shown = Rect::from_center_size(proof.center(), size * scale);
        p.image(
            id,
            shown,
            Rect::from_min_max(egui::Pos2::ZERO, egui::pos2(1.0, 1.0)),
            Color32::WHITE,
        );
    }
    style::paint_job(
        &p,
        proof.left_bottom() + egui::vec2(0.0, 14.0),
        Align2::LEFT_TOP,
        style::caps_job(&inputs.caption, 11.0, palette.ink3),
    );
    // The dial: one tick per plane, done ones in the state's colour.
    let center = egui::pos2(r.center().x, main.center().y);
    let radius = 196.0;
    let ticks = h.total.clamp(1, 180) as usize;
    let done = ((h.fraction * ticks as f32).round() as usize).min(ticks);
    for i in 0..ticks {
        let a = std::f32::consts::TAU * i as f32 / ticks as f32 - std::f32::consts::FRAC_PI_2;
        let dir = egui::vec2(a.cos(), a.sin());
        p.line_segment(
            [center + dir * (radius - 9.0), center + dir * (radius + 9.0)],
            Stroke::new(
                2.5_f32,
                if i < done {
                    color
                } else {
                    Color32::from_rgb(44, 44, 48)
                },
            ),
        );
    }
    p.circle_stroke(
        center,
        180.0,
        Stroke::new(1.0_f32, Color32::from_rgb(35, 35, 38)),
    );
    let left = h
        .left
        .filter(|_| state == GlanceState::Fine || matches!(state, GlanceState::NeedsYou(_)));
    style::paint_job(
        &p,
        center + egui::vec2(0.0, 22.0),
        Align2::CENTER_BOTTOM,
        style::job(
            &left.map(style::clock).unwrap_or_else(|| "—".into()),
            136.0,
            palette.ink,
            -2.0,
        ),
    );
    let ends = h
        .left
        .map(style::local_time_in)
        .unwrap_or_else(|| "—".into());
    style::paint_job(
        &p,
        center + egui::vec2(0.0, 76.0),
        Align2::CENTER_BOTTOM,
        style::caps_job(&format!("Left · ends {ends}"), 13.0, palette.ink3),
    );
    style::paint_job(
        &p,
        center + egui::vec2(0.0, radius + 52.0),
        Align2::CENTER_TOP,
        style::caps_job(
            &format!("Plane {} of {}", h.plane, h.total),
            14.0,
            palette.ink2,
        ),
    );
    // Four health lines at the right.
    let side = Rect::from_min_size(
        egui::pos2(main.right() - 320.0, center.y - 166.0),
        egui::vec2(320.0, 332.0),
    );
    let lines = glance_lines(inputs.s, &h, inputs.progress);
    let row_h = side.height() / 4.0;
    for (i, (mark, title, detail)) in lines.iter().enumerate() {
        let row = Rect::from_min_size(
            egui::pos2(side.left(), side.top() + row_h * i as f32),
            egui::vec2(side.width(), row_h),
        );
        style::hairline(
            &p,
            row.left_top(),
            row.right_top(),
            Color32::from_rgb(35, 35, 38),
        );
        style::mark(
            &p,
            egui::pos2(row.left() + 4.5, row.top() + 33.0),
            *mark,
            9.0,
            palette,
        );
        style::paint_job(
            &p,
            egui::pos2(row.left() + 28.0, row.top() + 16.0),
            Align2::LEFT_TOP,
            style::job(title, 24.0, palette.ink, 0.0),
        );
        style::paint_job(
            &p,
            egui::pos2(row.left() + 28.0, row.top() + 46.0),
            Align2::LEFT_TOP,
            style::job(detail, 15.0, palette.ink3, 0.0),
        );
    }
    style::hairline(
        &p,
        side.left_bottom(),
        side.right_bottom(),
        Color32::from_rgb(35, 35, 38),
    );
    // The sentence and the way back.
    let foot_y = r.bottom() - 150.0;
    style::paint_job(
        &p,
        egui::pos2(r.left() + 70.0, foot_y),
        Align2::LEFT_TOP,
        style::job(
            &next_sentence(&state, inputs.next),
            20.0,
            Color32::from_rgb(189, 187, 179),
            0.0,
        ),
    );
    style::paint_job(
        &p,
        egui::pos2(r.right() - 70.0, foot_y),
        Align2::RIGHT_TOP,
        style::job("Esc to return", 20.0, palette.ink3, 0.0),
    );
    ui.input(|i| i.key_pressed(egui::Key::Escape))
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;
    use std::time::Instant;

    fn snapshot(state: serde_json::Value) -> Snapshot {
        let mut s = Snapshot {
            online: true,
            observed: Some(Instant::now()),
            receiver: json!({"ok":true,"free_bytes":355_000_000_000u64}),
            ..Default::default()
        };
        s.set_state(state);
        s
    }

    fn capturing() -> serde_json::Value {
        json!({"camera_revision":4,"plan_revision":3,"sequence_id":2,"phase":"capturing","connected":true,
            "busy":false,"editable":false,"completed":61,"total":96,"shots_per_plane":4,
            "timer":{"elapsed":341.6,"remaining":198.0},
            "storage":{"mode":"host-pc","captured_frames":244,"saved_frames":242,"pending_frames":2}})
    }

    /// Green while it runs, amber when it waits for the user, red when it
    /// stopped, blue when done; each with its sentence.
    #[test]
    fn glance_reads_each_state() {
        let palette = CapturePalette::default();
        let s = snapshot(capturing());
        let h = flight::headline(&s);
        assert_eq!(
            (h.plane, h.total, h.raws_taken, h.raws_total),
            (61, 96, 244, 384)
        );
        assert!((h.per_plane.unwrap() - 5.6).abs() < 0.01);
        let fine = glance_state(&s, &h);
        assert_eq!(fine, GlanceState::Fine);
        assert_eq!(fine.color(&palette), palette.ok);
        assert_eq!(
            next_sentence(
                &fine,
                Next {
                    stack: true,
                    power_down: true
                }
            ),
            "Nothing needs you. When it finishes, it will be stacked and the rig will power down."
        );
        let mut paused = capturing();
        paused["phase"] = json!("paused");
        let s = snapshot(paused);
        let state = glance_state(&s, &flight::headline(&s));
        assert!(matches!(&state, GlanceState::NeedsYou(m) if m.contains("Paused at plane 61")));
        assert_eq!(state.color(&palette), palette.warn);
        let mut stopped = capturing();
        stopped["phase"] = json!("fault");
        stopped["failure"] = json!({"message":"Camera disconnected","exposure_uncertain":false});
        let s = snapshot(stopped);
        let state = glance_state(&s, &flight::headline(&s));
        assert!(
            matches!(&state, GlanceState::Stopped(m) if m.starts_with("Camera disconnected at plane 62"))
        );
        assert_eq!(state.color(&palette), palette.bad);
        let mut done = capturing();
        done["phase"] = json!("complete");
        done["completed"] = json!(96);
        let s = snapshot(done);
        let state = glance_state(&s, &flight::headline(&s));
        assert!(matches!(&state, GlanceState::Done(_)));
        assert_eq!(state.color(&palette), palette.info);
        let mut lost = snapshot(capturing());
        lost.receiver = json!(null);
        lost.receiver_error = Some("refused".into());
        assert!(
            matches!(glance_state(&lost, &flight::headline(&lost)), GlanceState::NeedsYou(m) if m.contains("receiver"))
        );
    }

    /// Escape returns; the dial pools its ticks above 180 planes.
    #[test]
    fn escape_returns_and_the_dial_is_bounded() {
        let ctx = egui::Context::default();
        let mut state = capturing();
        state["total"] = json!(1500);
        let s = snapshot(state);
        let inputs = GlanceInputs {
            s: &s,
            progress: None,
            proof: None,
            caption: "proof from planes 1–61".into(),
            next: Next::default(),
        };
        let palette = CapturePalette::default();
        let mut back = false;
        let out = ctx.run(
            egui::RawInput {
                screen_rect: Some(Rect::from_min_size(
                    egui::Pos2::ZERO,
                    egui::vec2(1680.0, 1050.0),
                )),
                events: vec![egui::Event::Key {
                    key: egui::Key::Escape,
                    physical_key: None,
                    pressed: true,
                    repeat: false,
                    modifiers: Default::default(),
                }],
                ..Default::default()
            },
            |ctx| {
                egui::CentralPanel::default()
                    .frame(egui::Frame::NONE)
                    .show(ctx, |ui| back = show(ui, &inputs, &palette));
            },
        );
        assert!(back);
        let segments = out
            .shapes
            .iter()
            .filter(|s| matches!(s.shape, egui::Shape::LineSegment { .. }))
            .count();
        assert!((180..200).contains(&segments), "{segments}");
    }
}
