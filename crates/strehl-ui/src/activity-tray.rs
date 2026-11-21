//! The activity tray (plan 6.6, mockup `capture-flight-jobs`): what runs now
//! with its time left and a way to stop it, the stacks waiting in the queue,
//! what finished earlier today, the notices, and the Quiet switch. Drawn
//! inside the shell's popover; it reads `Activities` and returns a
//! `TrayAction` for the shell to route.
use crate::activity::{
    ActionId, Activities, ActivityState, ActivityStatus, CancelMode, HistoryEntry,
};
use crate::notices::{self, Notices, Severity};
use crate::studio_fonts::Face;
use crate::studio_theme::{self, Tokens, scale};
use crate::studio_widgets::{self as w, Mark};
use eframe::egui::{self, Ui};
use std::time::{Instant, SystemTime};

const WIDTH: f32 = 430.0;
const EARLIER: usize = 5;

#[derive(Clone, Debug, PartialEq)]
pub(crate) enum TrayAction {
    /// Stop a running activity (its `CancelMode` says how).
    Cancel(u64),
    /// Take a stack off the queue.
    Remove(u64),
    /// The Quiet preference.
    SetQuiet(bool),
    ResumeQueue,
    /// An activity's or a finished activity's next step.
    Action(ActionId),
    /// The engine log and full activity history.
    OpenLog,
    OpenAgent,
    Notice(notices::Action),
}

pub(crate) struct TrayInputs<'a> {
    pub activities: &'a Activities,
    pub notices: &'a mut Notices,
    /// The workspace status line, shown when nothing runs.
    pub status: &'a str,
    /// The Quiet preference.
    pub quiet: bool,
    /// Quiet holds heavy work now (a full-screen program is in front).
    pub quiet_holds: bool,
    pub now: Instant,
    /// Unix seconds now, for "Earlier today".
    pub unix: u64,
}

pub(crate) fn severity_mark(severity: Severity) -> Mark {
    match severity {
        Severity::Info => Mark::NotYet,
        Severity::Done => Mark::Fine,
        Severity::Warning => Mark::Look,
        Severity::Failure => Mark::Failed,
    }
}

fn header(ui: &mut Ui, t: &Tokens, title: &str, right: impl FnOnce(&mut Ui)) {
    let frame = egui::Frame::NONE
        .inner_margin(egui::Margin::symmetric(14, 11))
        .show(ui, |ui| {
            ui.horizontal(|ui| {
                w::caps_colored(ui, title, scale::CAPS, t.ink3);
                ui.with_layout(egui::Layout::right_to_left(egui::Align::Center), right);
            });
        });
    let rect = frame.response.rect;
    crate::theme::rule(
        ui.painter(),
        rect.left_bottom(),
        rect.right_bottom(),
        t.line,
    );
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
fn clock(unix: u64) -> String {
    use chrono::{Local, TimeZone};
    Local
        .timestamp_opt(unix as i64, 0)
        .single()
        .map(|at| at.format("%H:%M").to_string())
        .unwrap_or_default()
}

/// The tray body, 430 wide.
pub(crate) fn tray(ui: &mut Ui, inputs: TrayInputs<'_>) -> Option<TrayAction> {
    let TrayInputs {
        activities,
        notices,
        status,
        quiet,
        quiet_holds,
        now,
        unix,
    } = inputs;
    let t = studio_theme::tokens(ui.ctx());
    ui.set_width(WIDTH);
    ui.set_max_width(WIDTH);
    ui.spacing_mut().item_spacing = egui::vec2(0.0, 0.0);
    let mut action = None;
    // ACTIVITY, then the moon, "Quiet" and its switch.
    let frame = egui::Frame::NONE
        .inner_margin(egui::Margin::symmetric(14, 11))
        .show(ui, |ui| {
            ui.horizontal(|ui| {
                w::caps_colored(ui, "Activity", scale::CAPS, t.ink);
                ui.with_layout(egui::Layout::right_to_left(egui::Align::Center), |ui| {
                    ui.spacing_mut().item_spacing = egui::vec2(8.0, 0.0);
                    let mut on = quiet;
                    if w::toggle(ui, &mut on)
                        .on_hover_text("Hold stacks, repairs and compaction while a full-screen program is in front")
                        .changed()
                    {
                        action = Some(TrayAction::SetQuiet(on));
                    }
                    ui.label(egui::RichText::new("Quiet").size(scale::SECONDARY).color(t.ink2));
                    let (moon, _) = ui.allocate_exact_size(egui::vec2(14.0, 14.0), egui::Sense::hover());
                    crate::library_paint::glyph(ui.painter(), moon.center(), crate::library_paint::Glyph::Moon, t.ink2);
                });
            });
        });
    let rect = frame.response.rect;
    crate::theme::rule(
        ui.painter(),
        rect.left_bottom(),
        rect.right_bottom(),
        t.line,
    );

    // Running and needs-you work; the queue's stacks are listed below.
    let active: Vec<&ActivityStatus> = activities.active().filter(|s| s.queued.is_none()).collect();
    if active.is_empty() {
        row(
            ui,
            &t,
            Mark::NotYet,
            "Nothing running",
            if status.is_empty() {
                "Queue a stack from any subject, or start a capture"
            } else {
                status
            },
            |_| {},
        );
    }
    for activity in &active {
        let (mark, detail) = match &activity.state {
            ActivityState::NeedsYou { message, .. } => (Mark::Look, message.clone()),
            ActivityState::Waiting { for_what, gives_up } => {
                let mut detail = format!("Waiting for {for_what}");
                if let Some(at) = gives_up {
                    detail.push_str(&format!(
                        " · gives up in {}",
                        crate::render_eta::spoken(at.saturating_duration_since(now))
                    ));
                }
                (Mark::NotYet, detail)
            }
            _ => (Mark::Running, running_detail(activity, now)),
        };
        let detail = if activity.facts.is_empty() {
            detail
        } else {
            format!("{detail}\n{}", activity.facts)
        };
        let rect = row(ui, &t, mark, &activity.title, &detail, |ui| {
            if let ActivityState::NeedsYou {
                action: Some(next), ..
            } = &activity.state
            {
                if w::link(ui, action_label(next), true).clicked() {
                    action = Some(TrayAction::Action(next.clone()));
                }
            } else if activity.cancel != CancelMode::None && w::link(ui, "Stop", false).clicked() {
                action = Some(TrayAction::Cancel(activity.id));
            }
        });
        if let Some(fraction) = activity.fraction() {
            let bar = egui::Rect::from_min_size(
                egui::pos2(rect.left() + 40.0, rect.bottom() - 7.0),
                egui::vec2(rect.width() - 54.0, 2.0),
            );
            w::progress_bar(ui.painter(), bar, fraction, t.ok, &t);
        }
    }

    // The queue.
    let waiting: Vec<&ActivityStatus> = activities
        .waiting()
        .filter(|s| s.queued.is_some())
        .collect();
    if !waiting.is_empty() {
        let paused = waiting.iter().any(|s| matches!(&s.state, ActivityState::Waiting { for_what, .. } if for_what.contains("resume the queue")));
        let note = match &waiting[0].state {
            ActivityState::Waiting { for_what, .. } => match for_what.as_str() {
                "the stack before it" => "start when the running stack ends".to_owned(),
                "its turn" => "start next".to_owned(),
                other => format!("waiting for {other}"),
            },
            _ => String::new(),
        };
        header(ui, &t, &format!("Waiting · {}", waiting.len()), |ui| {
            if paused {
                if w::link(ui, "Resume", true).clicked() {
                    action = Some(TrayAction::ResumeQueue);
                }
            } else {
                ui.label(
                    egui::RichText::new(&note)
                        .size(scale::SECONDARY)
                        .color(t.ink3),
                );
            }
        });
        for (index, item) in waiting.iter().enumerate() {
            let mut detail = item.phase.clone();
            if let Some(eta) = item.eta
                && !detail.contains("about")
            {
                detail.push_str(&format!(" · about {}", crate::render_eta::spoken(eta)));
            }
            row_numbered(ui, &t, index + 1, &item.title, &detail, |ui| {
                if let Some(id) = item.queued
                    && w::link(ui, "Remove", false).clicked()
                {
                    action = Some(TrayAction::Remove(id));
                }
            });
        }
    }

    // Earlier today.
    let earlier: Vec<&HistoryEntry> = activities
        .history()
        .iter()
        .filter(|e| today(e, unix))
        .take(EARLIER)
        .collect();
    if !earlier.is_empty() {
        header(ui, &t, "Earlier today", |ui| {
            if w::link(ui, "Full log", false).clicked() {
                action = Some(TrayAction::OpenLog);
            }
        });
        for entry in &earlier {
            let mark = match entry.outcome.as_str() {
                "done" => Mark::Fine,
                "needs_you" => Mark::Look,
                _ => Mark::Failed,
            };
            let mut detail = entry.summary.clone();
            if let Some(took) = entry.took_seconds.filter(|t| *t >= 1.0) {
                detail.push_str(&format!(
                    " · took {}",
                    crate::render_eta::spoken(std::time::Duration::from_secs_f64(took))
                ));
            }
            row(ui, &t, mark, &entry.title, &detail, |ui| {
                match &entry.action {
                    Some(
                        next @ (ActionId::Reveal { .. }
                        | ActionId::ShowLog { .. }
                        | ActionId::Retry { .. }
                        | ActionId::OpenRun { .. }
                        | ActionId::OpenStack { .. }),
                    ) => {
                        if w::link(ui, action_label(next), false).clicked() {
                            action = Some(TrayAction::Action(next.clone()));
                        }
                    }
                    _ => {
                        ui.label(
                            egui::RichText::new(clock(entry.finished))
                                .size(scale::SECONDARY)
                                .color(t.ink3),
                        );
                    }
                }
            });
        }
    }

    // The notices, newest first.
    header(ui, &t, "Notices", |ui| {
        if notices.unread() > 0 && w::link(ui, "Mark all read", false).clicked() {
            notices.mark_all_read();
        }
    });
    if notices.len() == 0 {
        row(
            ui,
            &t,
            Mark::Hidden,
            "No notices",
            "Finished stacks, exports and anything that failed appear here",
            |_| {},
        );
    }
    let wall = SystemTime::now();
    let mut dismiss = None;
    let listed: Vec<_> = notices.iter().take(6).cloned().collect();
    for notice in &listed {
        let detail = format!(
            "{} · {}{}",
            notice.source.label(),
            notices::ago(notice.time, wall),
            if notice.resolved { " · cleared" } else { "" }
        );
        row(
            ui,
            &t,
            severity_mark(notice.severity),
            &notice.text,
            &detail,
            |ui| {
                if ui
                    .add(w::Button::quiet("Dismiss").small())
                    .on_hover_text("Remove this notice")
                    .clicked()
                {
                    dismiss = Some(notice.id);
                }
                if let Some(next) = &notice.action {
                    let label = match next {
                        notices::Action::OpenLog => "Log",
                        notices::Action::OpenStation(_) => "Open",
                    };
                    if w::link(ui, label, notice.severity == Severity::Failure).clicked() {
                        action = Some(TrayAction::Notice(next.clone()));
                    }
                }
            },
        );
    }
    if notices.len() > listed.len() {
        egui::Frame::NONE
            .inner_margin(egui::Margin::symmetric(14, 8))
            .show(ui, |ui| {
                ui.label(
                    egui::RichText::new(format!("{} earlier", notices.len() - listed.len()))
                        .size(scale::SECONDARY)
                        .color(t.ink3),
                );
            });
    }
    if let Some(id) = dismiss {
        notices.dismiss(id);
    }

    // Quiet's promise while it holds, then the agent.
    if quiet_holds {
        let rect = row(
            ui,
            &t,
            Mark::Hidden,
            "Quiet holds heavy work",
            "Stacks, repairs and compaction wait while a full-screen program is in front. Captures and transfers never wait.",
            |_| {},
        );
        crate::library_paint::glyph(
            ui.painter(),
            egui::pos2(rect.left() + 18.0 + w::MARK_SLOT * 0.5, rect.top() + 18.0),
            crate::library_paint::Glyph::Moon,
            t.ink2,
        );
    }
    egui::Frame::NONE
        .inner_margin(egui::Margin::symmetric(14, 9))
        .show(ui, |ui| {
            ui.horizontal(|ui| {
                ui.spacing_mut().item_spacing = egui::vec2(16.0, 0.0);
                if w::link(ui, "Engine log", false).clicked() {
                    action = Some(TrayAction::OpenLog);
                }
                if w::link(ui, "Agent", false).clicked() {
                    action = Some(TrayAction::OpenAgent);
                }
            });
        });
    action
}

/// "Merge · 120 / 299 · 3 min 18 s left · ends 21:47"
fn running_detail(status: &ActivityStatus, now: Instant) -> String {
    let mut line = status.progress_line(now);
    if let Some(eta) = status.eta {
        let ends = chrono::Local::now() + chrono::Duration::seconds(eta.as_secs() as i64);
        line.push_str(&format!(" · ends {}", ends.format("%H:%M")));
    }
    line
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

/// A tray row: mark, title, detail under it, controls on the right. Title
/// and detail wrap in the space the controls leave.
fn row(
    ui: &mut Ui,
    t: &Tokens,
    mark: Mark,
    title: &str,
    detail: &str,
    controls: impl FnOnce(&mut Ui),
) -> egui::Rect {
    row_with(ui, t, Lead::Mark(mark), title, detail, controls)
}
/// A queued stack's row: its place in the queue instead of a mark.
fn row_numbered(
    ui: &mut Ui,
    t: &Tokens,
    place: usize,
    title: &str,
    detail: &str,
    controls: impl FnOnce(&mut Ui),
) -> egui::Rect {
    row_with(ui, t, Lead::Number(place), title, detail, controls)
}
enum Lead {
    Mark(Mark),
    Number(usize),
}
fn row_with(
    ui: &mut Ui,
    t: &Tokens,
    lead: Lead,
    title: &str,
    detail: &str,
    controls: impl FnOnce(&mut Ui),
) -> egui::Rect {
    const CONTROLS: f32 = 112.0;
    let frame = egui::Frame::NONE
        .inner_margin(egui::Margin {
            left: 14,
            right: 14,
            top: 10,
            bottom: 12,
        })
        .show(ui, |ui| {
            let width = ui.available_width();
            ui.set_width(width);
            ui.horizontal_top(|ui| {
                ui.spacing_mut().item_spacing = egui::vec2(0.0, 3.0);
                ui.add_space(4.0);
                let (slot, _) =
                    ui.allocate_exact_size(egui::vec2(w::MARK_SLOT, 16.0), egui::Sense::hover());
                match lead {
                    Lead::Mark(mark) => w::paint_mark(ui.painter(), slot.center(), mark, t),
                    Lead::Number(place) => {
                        ui.painter().text(
                            slot.center(),
                            egui::Align2::CENTER_CENTER,
                            place.to_string(),
                            egui::FontId::proportional(scale::SECONDARY),
                            t.ink3,
                        );
                    }
                }
                ui.add_space(14.0);
                let text_width = (width - 18.0 - w::MARK_SLOT - CONTROLS).max(80.0);
                ui.allocate_ui_with_layout(
                    egui::vec2(text_width, 0.0),
                    egui::Layout::top_down(egui::Align::Min),
                    |ui| {
                        ui.set_max_width(text_width);
                        ui.spacing_mut().item_spacing = egui::vec2(0.0, 3.0);
                        ui.add(
                            egui::Label::new(
                                egui::RichText::new(title)
                                    .font(w::font(ui, Face::Strong, scale::BODY))
                                    .color(t.ink),
                            )
                            .wrap(),
                        );
                        if !detail.is_empty() {
                            ui.add(
                                egui::Label::new(
                                    egui::RichText::new(detail)
                                        .size(scale::SECONDARY)
                                        .color(t.ink2),
                                )
                                .wrap(),
                            );
                        }
                    },
                );
                ui.with_layout(egui::Layout::right_to_left(egui::Align::Min), |ui| {
                    ui.spacing_mut().item_spacing = egui::vec2(8.0, 0.0);
                    controls(ui)
                });
            });
        });
    let rect = frame.response.rect;
    crate::theme::rule(
        ui.painter(),
        rect.left_bottom(),
        rect.right_bottom(),
        t.line,
    );
    rect
}

#[cfg(test)]
#[path = "activity-tray-tests.rs"]
mod tests;
