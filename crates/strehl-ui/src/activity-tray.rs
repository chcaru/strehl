//! The activity tray (plan 6.6, mockup `capture-flight-jobs`): what runs,
//! what waits and what finished earlier today, with the Quiet switch. A
//! popover the shell opens from the top bar; it reads `Activities` and
//! returns a `TrayIntent`, and owns no state of its own.
#![allow(
    dead_code,
    reason = "the shell opens the tray from its top bar in P5 stage 2"
)]
use crate::{
    activity::{ActionId, Activities, ActivityState, ActivityStatus, CancelMode, HistoryEntry},
    library_paint::{self as paint, Glyph, LibraryPalette, Mark},
    render_eta::spoken,
};
use eframe::egui::{self, Align2, CornerRadius, Pos2, Rect, Sense, Ui, Vec2};
use std::time::Instant;

pub(crate) const WIDTH: f32 = 430.0;
const PAD: f32 = 14.0;
const HEADER: f32 = 38.0;
const EARLIER: usize = 5;

#[derive(Clone, Debug, PartialEq)]
pub(crate) enum TrayIntent {
    /// Stop a running activity (its `CancelMode` says how).
    Cancel(u64),
    /// Take a stack off the queue.
    Remove(u64),
    SetQuiet(bool),
    ResumeQueue,
    Action(ActionId),
    FullLog,
}

pub(crate) struct TrayInputs<'a> {
    pub activities: &'a Activities,
    /// The Preferences switch.
    pub quiet_switch: bool,
    /// Quiet holds heavy work now (switch or a full-screen program).
    pub quiet_holds: bool,
    pub palette: &'a LibraryPalette,
    pub now: Instant,
    /// Unix seconds now, for "Earlier today".
    pub unix: u64,
}

/// Draw the tray hanging from `top_right`; returns what was asked for.
pub(crate) fn show(
    ctx: &egui::Context,
    top_right: Pos2,
    inputs: TrayInputs<'_>,
) -> Option<TrayIntent> {
    let height = tray_height(&inputs);
    let rect = Rect::from_min_size(
        Pos2::new(top_right.x - WIDTH, top_right.y),
        Vec2::new(WIDTH, height),
    );
    let mut intent = None;
    egui::Area::new(egui::Id::new("activity-tray"))
        .order(egui::Order::Foreground)
        .fixed_pos(rect.min)
        .show(ctx, |ui| {
            let (frame, _) = ui.allocate_exact_size(rect.size(), Sense::hover());
            intent = paint_tray(ui, frame, &inputs);
        });
    intent
}

fn today(entry: &HistoryEntry, unix: u64) -> bool {
    use chrono::{Local, TimeZone};
    match (
        Local.timestamp_opt(entry.finished as i64, 0).single(),
        Local.timestamp_opt(unix as i64, 0).single(),
    ) {
        (Some(at), Some(now)) => at.date_naive() == now.date_naive(),
        _ => false,
    }
}
fn shown<'a>(
    inputs: &'a TrayInputs<'_>,
) -> (
    Vec<&'a ActivityStatus>,
    Vec<&'a ActivityStatus>,
    Vec<&'a HistoryEntry>,
) {
    let active: Vec<&ActivityStatus> = inputs
        .activities
        .statuses()
        .iter()
        .filter(|s| {
            matches!(
                s.state,
                ActivityState::Running | ActivityState::NeedsYou { .. }
            ) || (matches!(s.state, ActivityState::Waiting { .. }) && s.queued.is_none())
        })
        .collect();
    let waiting: Vec<&ActivityStatus> = inputs
        .activities
        .waiting()
        .filter(|s| s.queued.is_some())
        .collect();
    let earlier: Vec<&HistoryEntry> = inputs
        .activities
        .history()
        .iter()
        .filter(|e| today(e, inputs.unix))
        .take(EARLIER)
        .collect();
    (active, waiting, earlier)
}
fn row_height(bar: bool) -> f32 {
    if bar { 66.0 } else { 58.0 }
}
fn tray_height(inputs: &TrayInputs<'_>) -> f32 {
    let (active, waiting, earlier) = shown(inputs);
    let mut height = HEADER;
    height += if active.is_empty() {
        row_height(false)
    } else {
        active
            .iter()
            .map(|s| row_height(s.fraction().is_some()))
            .sum()
    };
    if !waiting.is_empty() {
        height += 36.0 + waiting.len() as f32 * row_height(false);
    }
    if !earlier.is_empty() {
        height += 36.0 + earlier.len() as f32 * row_height(false);
    }
    if inputs.quiet_holds {
        height += 74.0;
    }
    height
}

fn paint_tray(ui: &mut Ui, frame: Rect, inputs: &TrayInputs<'_>) -> Option<TrayIntent> {
    let palette = inputs.palette;
    let painter = ui.painter().clone();
    painter.rect_filled(frame, CornerRadius::ZERO, palette.panel);
    paint::inset(&painter, frame, palette.line_2);
    let left = frame.left() + PAD;
    let right = frame.right() - PAD;
    let mut intent = None;
    // Header: ACTIVITY, the moon and the Quiet switch.
    let mid = frame.top() + HEADER * 0.5;
    paint::caps(
        &painter,
        Pos2::new(left, mid),
        Align2::LEFT_CENTER,
        "Activity",
        10.5,
        palette.ink,
    );
    if paint::toggle(
        ui,
        Pos2::new(right - 26.0, mid - 7.0),
        "tray-quiet",
        inputs.quiet_switch,
        palette,
    )
    .clicked()
    {
        intent = Some(TrayIntent::SetQuiet(!inputs.quiet_switch));
    }
    let quiet = paint::text(
        &painter,
        Pos2::new(right - 36.0, mid),
        Align2::RIGHT_CENTER,
        "Quiet",
        12.0,
        palette.ink_2,
        None,
    );
    paint::glyph(
        &painter,
        Pos2::new(quiet.left() - 12.0, mid),
        Glyph::Moon,
        palette.ink_2,
    );
    let mut y = frame.top() + HEADER;
    paint::hline(&painter, frame.left()..=frame.right(), y, palette.line);
    let (active, waiting, earlier) = shown(inputs);
    if active.is_empty() {
        row(
            &painter,
            frame,
            y,
            Mark::Idle,
            "Nothing running",
            "Queue a stack from any subject, or start a capture",
            palette,
        );
        y += row_height(false);
    }
    for (index, status) in active.iter().enumerate() {
        let found = active_row(ui, &painter, frame, y, status, inputs);
        intent = intent.or(found);
        y += row_height(status.fraction().is_some());
        if index + 1 < active.len() {
            paint::hline(
                &painter,
                frame.left()..=frame.right(),
                y - 1.0,
                palette.line,
            );
        }
    }
    if !waiting.is_empty() {
        let note = match &waiting[0].state {
            ActivityState::Waiting { for_what, .. } => format!("waiting for {for_what}"),
            _ => String::new(),
        };
        let paused = note.contains("resume the queue");
        let link = group_header(
            ui,
            &painter,
            frame,
            y,
            &format!("Waiting · {}", waiting.len()),
            if paused { "Resume" } else { "" },
            &note,
            palette,
        );
        if link {
            intent = intent.or(Some(TrayIntent::ResumeQueue));
        }
        y += 36.0;
        for (index, status) in waiting.iter().enumerate() {
            let rect = Rect::from_min_size(
                Pos2::new(frame.left(), y),
                Vec2::new(frame.width(), row_height(false)),
            );
            paint::text(
                &painter,
                Pos2::new(left, y + 20.0),
                Align2::LEFT_CENTER,
                &(index + 1).to_string(),
                12.0,
                palette.ink_3,
                None,
            );
            paint::text(
                &painter,
                Pos2::new(left + 27.0, y + 20.0),
                Align2::LEFT_CENTER,
                &status.title,
                13.0,
                palette.ink,
                Some(right - left - 110.0),
            );
            let mut detail = status.phase.clone();
            if let Some(eta) = status.eta
                && !detail.contains("about")
            {
                detail.push_str(&format!(" · about {}", spoken(eta)));
            }
            paint::text(
                &painter,
                Pos2::new(left + 27.0, y + 41.0),
                Align2::LEFT_CENTER,
                &detail,
                12.0,
                palette.ink_2,
                Some(right - left - 27.0),
            );
            if let Some(id) = status.queued
                && caps_link(
                    ui,
                    &painter,
                    Pos2::new(right, y + 20.0),
                    "Remove",
                    ("tray-remove", id),
                    palette,
                )
            {
                intent = intent.or(Some(TrayIntent::Remove(id)));
            }
            paint::hline(
                &painter,
                rect.left()..=rect.right(),
                rect.bottom() - 1.0,
                palette.line,
            );
            y += row_height(false);
        }
    }
    if !earlier.is_empty() {
        if group_header(
            ui,
            &painter,
            frame,
            y,
            "Earlier today",
            "Full log",
            "",
            palette,
        ) {
            intent = intent.or(Some(TrayIntent::FullLog));
        }
        y += 36.0;
        for (index, entry) in earlier.iter().enumerate() {
            let mark = match entry.outcome.as_str() {
                "done" => Mark::Ok,
                "needs_you" => Mark::Warn,
                _ => Mark::Bad,
            };
            let mut detail = entry.summary.clone();
            if let Some(took) = entry.took_seconds.filter(|t| *t >= 1.0) {
                detail.push_str(&format!(
                    " · took {}",
                    spoken(std::time::Duration::from_secs_f64(took))
                ));
            }
            let right_link = match &entry.action {
                Some(ActionId::Reveal { .. }) => Some("Reveal"),
                Some(ActionId::ShowLog { .. }) => Some("Log"),
                Some(ActionId::Retry { .. }) => Some("Retry"),
                Some(ActionId::OpenRun { .. } | ActionId::OpenStack { .. }) => Some("Open"),
                _ => None,
            };
            row(&painter, frame, y, mark, &entry.title, &detail, palette);
            if index + 1 < earlier.len() || inputs.quiet_holds {
                paint::hline(
                    &painter,
                    frame.left()..=frame.right(),
                    y + row_height(false) - 1.0,
                    palette.line,
                );
            }
            match (right_link, &entry.action) {
                (Some(label), Some(action)) => {
                    if caps_link(
                        ui,
                        &painter,
                        Pos2::new(right, y + 20.0),
                        label,
                        ("tray-earlier", index),
                        palette,
                    ) {
                        intent = intent.or(Some(TrayIntent::Action(action.clone())));
                    }
                }
                _ => {
                    paint::text(
                        &painter,
                        Pos2::new(right, y + 20.0),
                        Align2::RIGHT_CENTER,
                        &clock(entry.finished),
                        12.0,
                        palette.ink_3,
                        None,
                    );
                }
            }
            y += row_height(false);
        }
    }
    if inputs.quiet_holds {
        paint::glyph(
            &painter,
            Pos2::new(left + 6.0, y + 20.0),
            Glyph::Moon,
            palette.ink_2,
        );
        paint::text(
            &painter,
            Pos2::new(left + 27.0, y + 20.0),
            Align2::LEFT_CENTER,
            "Quiet holds heavy work",
            13.0,
            palette.ink,
            None,
        );
        paint::paragraph(
            &painter,
            Pos2::new(left + 27.0, y + 32.0),
            "Stacks, repairs and compaction wait while a full-screen program is in front. Captures and transfers never wait.",
            12.0,
            palette.ink_2,
            right - left - 27.0,
            2,
        );
    }
    intent
}

/// A running or needs-you row: mark, title, Stop, detail and bar.
fn active_row(
    ui: &mut Ui,
    painter: &egui::Painter,
    frame: Rect,
    y: f32,
    status: &ActivityStatus,
    inputs: &TrayInputs<'_>,
) -> Option<TrayIntent> {
    let palette = inputs.palette;
    let (left, right) = (frame.left() + PAD, frame.right() - PAD);
    let (mark, detail) = match &status.state {
        ActivityState::NeedsYou { message, .. } => (Mark::Warn, message.clone()),
        ActivityState::Waiting { for_what, gives_up } => {
            let mut detail = format!("Waiting for {for_what}");
            if let Some(at) = gives_up {
                detail.push_str(&format!(
                    " · gives up in {}",
                    spoken(at.saturating_duration_since(inputs.now))
                ));
            }
            (Mark::Idle, detail)
        }
        _ => (Mark::Run, running_detail(status, inputs.now)),
    };
    let bar = status.fraction();
    row(painter, frame, y, mark, &status.title, &detail, palette);
    let mut intent = None;
    match &status.state {
        ActivityState::NeedsYou {
            action: Some(action),
            ..
        } => {
            if caps_link(
                ui,
                painter,
                Pos2::new(right, y + 20.0),
                action_label(action),
                ("tray-act", status.id),
                palette,
            ) {
                intent = Some(TrayIntent::Action(action.clone()));
            }
        }
        _ if status.cancel != CancelMode::None
            && caps_link(
                ui,
                painter,
                Pos2::new(right, y + 20.0),
                "Stop",
                ("tray-stop", status.id),
                palette,
            ) =>
        {
            intent = Some(TrayIntent::Cancel(status.id));
        }
        _ => {}
    }
    if let Some(fraction) = bar {
        let track = Rect::from_min_size(
            Pos2::new(left + 27.0, y + 54.0),
            Vec2::new(right - left - 27.0, 2.0),
        );
        painter.rect_filled(track, CornerRadius::ZERO, palette.line_2);
        painter.rect_filled(
            Rect::from_min_size(track.min, Vec2::new(track.width() * fraction, 2.0)),
            CornerRadius::ZERO,
            palette.ok,
        );
    }
    intent
}
/// "Merge · 120 of 299 · 1 min 40 s left · ends 21:47"
fn running_detail(status: &ActivityStatus, now: Instant) -> String {
    let mut parts = Vec::new();
    if !status.phase.is_empty() {
        parts.push(status.phase.clone());
    }
    if let (Some(done), Some(total)) = (status.done, status.total) {
        parts.push(format!("{done} of {total}"));
    }
    if let Some(eta) = status.eta {
        parts.push(format!("{} left", spoken(eta)));
        let ends = chrono::Local::now() + chrono::Duration::seconds(eta.as_secs() as i64);
        parts.push(format!("ends {}", ends.format("%H:%M")));
    } else if let Some(started) = status.started {
        parts.push(format!(
            "{} so far",
            spoken(now.saturating_duration_since(started))
        ));
    }
    parts.join(" · ")
}
fn action_label(action: &ActionId) -> &'static str {
    match action {
        ActionId::OpenStack { .. } | ActionId::OpenRun { .. } => "Open",
        ActionId::OpenCapture => "Capture",
        ActionId::Reveal { .. } => "Reveal",
        ActionId::ShowLog { .. } => "Log",
        ActionId::Retry { .. } => "Retry",
        ActionId::ResumeQueue => "Resume",
    }
}
fn clock(unix: u64) -> String {
    use chrono::{Local, TimeZone};
    Local
        .timestamp_opt(unix as i64, 0)
        .single()
        .map(|at| at.format("%H:%M").to_string())
        .unwrap_or_default()
}

fn row(
    painter: &egui::Painter,
    frame: Rect,
    y: f32,
    mark: Mark,
    title: &str,
    detail: &str,
    palette: &LibraryPalette,
) {
    let (left, right) = (frame.left() + PAD, frame.right() - PAD);
    paint::mark(painter, Pos2::new(left + 4.0, y + 20.0), mark, palette);
    paint::text(
        painter,
        Pos2::new(left + 27.0, y + 20.0),
        Align2::LEFT_CENTER,
        title,
        13.0,
        palette.ink,
        Some(right - left - 110.0),
    );
    paint::text(
        painter,
        Pos2::new(left + 27.0, y + 41.0),
        Align2::LEFT_CENTER,
        detail,
        12.0,
        palette.ink_2,
        Some(right - left - 27.0),
    );
}
/// A group header with its count and a right-hand link or note; true when
/// the link was clicked.
#[allow(clippy::too_many_arguments)]
fn group_header(
    ui: &mut Ui,
    painter: &egui::Painter,
    frame: Rect,
    y: f32,
    label: &str,
    link: &str,
    note: &str,
    palette: &LibraryPalette,
) -> bool {
    let (left, right) = (frame.left() + PAD, frame.right() - PAD);
    paint::hline(painter, frame.left()..=frame.right(), y, palette.line);
    paint::caps(
        painter,
        Pos2::new(left, y + 18.0),
        Align2::LEFT_CENTER,
        label,
        10.5,
        palette.ink_3,
    );
    let clicked = !link.is_empty()
        && caps_link(
            ui,
            painter,
            Pos2::new(right, y + 18.0),
            link,
            ("tray-group", label),
            palette,
        );
    if link.is_empty() && !note.is_empty() {
        paint::text(
            painter,
            Pos2::new(right, y + 18.0),
            Align2::RIGHT_CENTER,
            note,
            12.0,
            palette.ink_3,
            Some(right - left - 140.0),
        );
    }
    paint::hline(
        painter,
        frame.left()..=frame.right(),
        y + 36.0,
        palette.line,
    );
    clicked
}
/// A right-aligned link in tracked capitals; true when clicked.
fn caps_link(
    ui: &mut Ui,
    painter: &egui::Painter,
    right_center: Pos2,
    label: &str,
    id: impl std::hash::Hash,
    palette: &LibraryPalette,
) -> bool {
    let rect = paint::caps_galley(painter, label, 10.5, palette.ink_2).size();
    let rect = Rect::from_min_size(
        Pos2::new(right_center.x - rect.x, right_center.y - rect.y * 0.5),
        rect,
    );
    let response = ui.interact(rect.expand(4.0), ui.id().with(id), Sense::click());
    paint::caps(
        painter,
        rect.left_center(),
        Align2::LEFT_CENTER,
        label,
        10.5,
        if response.hovered() {
            palette.ink
        } else {
            palette.ink_2
        },
    );
    response.clicked()
}

#[cfg(test)]
#[path = "activity-tray-tests.rs"]
mod tests;
