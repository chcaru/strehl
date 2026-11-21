//! The activity tray (implementation plan 6.6): what is running now, with its
//! progress and a way to stop it, and the notices, newest first.
use crate::activity::{ActivityStatus, CancelMode};
use crate::notices::{self, Notices, Severity};
use crate::studio_fonts::Face;
use crate::studio_theme::{self, Tokens, scale};
use crate::studio_widgets::{self as w, Mark};
use eframe::egui::{self, Ui};
use std::time::{Instant, SystemTime};

#[derive(Clone, Debug, PartialEq)]
pub(crate) enum TrayAction {
    /// Stop the activity with this kind (cooperative cancel).
    Stop(crate::activity::ActivityKind),
    OpenLog,
    OpenAgent,
    Notice(notices::Action),
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
                w::caps_colored(ui, title, scale::CAPS, t.ink);
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

/// The tray body, 430 wide.
pub(crate) fn tray(
    ui: &mut Ui,
    activities: &[ActivityStatus],
    notices: &mut Notices,
    status: &str,
) -> Option<TrayAction> {
    let t = studio_theme::tokens(ui.ctx());
    ui.set_width(430.0);
    ui.set_max_width(430.0);
    ui.spacing_mut().item_spacing = egui::vec2(0.0, 0.0);
    let mut action = None;
    header(ui, &t, "Activity", |ui| {
        if w::link(ui, "Engine log", false).clicked() {
            action = Some(TrayAction::OpenLog);
        }
    });
    let now = Instant::now();
    if activities.is_empty() {
        row(ui, &t, Mark::NotYet, "Nothing running", "", |ui| {
            ui.label(
                egui::RichText::new(if status.is_empty() { "Idle" } else { status })
                    .size(scale::SECONDARY)
                    .color(t.ink3),
            );
        });
    }
    for activity in activities {
        let line = activity.progress_line(now);
        let detail = match (line.is_empty(), activity.facts.is_empty()) {
            (false, false) => format!("{line}\n{}", activity.facts),
            (false, true) => line,
            (true, false) => activity.facts.clone(),
            (true, true) => String::new(),
        };
        let response = row(ui, &t, Mark::Running, &activity.title, &detail, |ui| {
            if activity.cancel == CancelMode::Cooperative && w::link(ui, "Stop", false).clicked() {
                action = Some(TrayAction::Stop(activity.kind));
            }
        });
        if let Some(fraction) = activity.fraction() {
            let rect = response;
            let bar = egui::Rect::from_min_size(
                egui::pos2(rect.left() + 41.0, rect.bottom() - 6.0),
                egui::vec2(rect.width() - 55.0, 2.0),
            );
            w::progress_bar(ui.painter(), bar, fraction, t.accent, &t);
        }
    }
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
    let clock = SystemTime::now();
    let mut dismiss = None;
    let mut chosen = None;
    let listed: Vec<_> = notices.iter().take(8).cloned().collect();
    for notice in &listed {
        let detail = format!(
            "{} · {}{}",
            notice.source.label(),
            notices::ago(notice.time, clock),
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
                        chosen = Some(TrayAction::Notice(next.clone()));
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
    egui::Frame::NONE
        .inner_margin(egui::Margin::symmetric(14, 9))
        .show(ui, |ui| {
            ui.horizontal(|ui| {
                if w::link(ui, "Agent", false).clicked() {
                    action = Some(TrayAction::OpenAgent);
                }
            });
        });
    action.or(chosen)
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
                w::paint_mark(ui.painter(), slot.center(), mark, t);
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
mod tests {
    use super::*;
    use crate::activity::{ActivityKind, Lane};
    use crate::notices::Source;

    fn paint(
        ctx: &egui::Context,
        activities: &[ActivityStatus],
        notices: &mut Notices,
        time: f64,
        events: Vec<egui::Event>,
    ) -> (egui::FullOutput, Option<TrayAction>) {
        let mut action = None;
        let output = ctx.run(
            egui::RawInput {
                screen_rect: Some(egui::Rect::from_min_size(
                    egui::Pos2::ZERO,
                    egui::vec2(800.0, 900.0),
                )),
                time: Some(time),
                events,
                ..Default::default()
            },
            |ctx| {
                egui::CentralPanel::default().show(ctx, |ui| {
                    action = tray(ui, activities, notices, "Stacking");
                });
            },
        );
        (output, action)
    }
    fn find(output: &egui::FullOutput, needle: &str) -> Option<egui::Pos2> {
        output.shapes.iter().find_map(|shape| match &shape.shape {
            egui::Shape::Text(text) if text.galley.text() == needle => {
                Some(text.visual_bounding_rect().center())
            }
            _ => None,
        })
    }

    #[test]
    fn the_tray_lists_running_work_with_stop_and_notices_newest_first() {
        let ctx = egui::Context::default();
        crate::theme::install(&ctx);
        let mut stack =
            ActivityStatus::running(ActivityKind::Stack, "Stacking Blue weevil", Lane::Heavy);
        stack.cancel = CancelMode::Cooperative;
        stack.done = Some(10);
        stack.total = Some(40);
        stack.facts = "32 workers · 299 RAW · 61.4 GiB".into();
        let mut notices = Notices::default();
        notices.push(Severity::Done, Source::Export, "Exported weevil.avif", None);
        notices.push(
            Severity::Failure,
            Source::Stack,
            "The engine stopped",
            Some(notices::Action::OpenLog),
        );
        let (output, _) = paint(&ctx, &[stack.clone()], &mut notices, 0.0, vec![]);
        for needle in [
            "Stacking Blue weevil",
            "STOP",
            "The engine stopped",
            "Exported weevil.avif",
        ] {
            assert!(find(&output, needle).is_some(), "missing {needle}");
        }
        let failure = find(&output, "The engine stopped").unwrap();
        let export = find(&output, "Exported weevil.avif").unwrap();
        assert!(failure.y < export.y, "newest first");
        let bar = output.shapes.iter().any(|s| matches!(&s.shape,
            egui::Shape::Rect(r) if r.rect.height() == 2.0 && r.fill == crate::studio_theme::GRAPHITE.accent));
        assert!(bar, "a counted task shows its progress rule");
        let stop = find(&output, "STOP").unwrap();
        let press = |pressed| egui::Event::PointerButton {
            pos: stop,
            button: egui::PointerButton::Primary,
            pressed,
            modifiers: egui::Modifiers::NONE,
        };
        paint(
            &ctx,
            &[stack.clone()],
            &mut notices,
            0.1,
            vec![egui::Event::PointerMoved(stop), press(true)],
        );
        let (_, action) = paint(&ctx, &[stack], &mut notices, 0.15, vec![press(false)]);
        assert_eq!(action, Some(TrayAction::Stop(ActivityKind::Stack)));
    }

    #[test]
    fn an_idle_tray_says_so_and_dismissing_removes_a_notice() {
        let ctx = egui::Context::default();
        crate::theme::install(&ctx);
        let mut notices = Notices::default();
        notices.push(Severity::Info, Source::App, "Preferences saved", None);
        let (output, _) = paint(&ctx, &[], &mut notices, 0.0, vec![]);
        assert!(find(&output, "Nothing running").is_some());
        let dismiss = find(&output, "Dismiss").unwrap();
        let press = |pressed| egui::Event::PointerButton {
            pos: dismiss,
            button: egui::PointerButton::Primary,
            pressed,
            modifiers: egui::Modifiers::NONE,
        };
        paint(
            &ctx,
            &[],
            &mut notices,
            0.1,
            vec![egui::Event::PointerMoved(dismiss), press(true)],
        );
        paint(&ctx, &[], &mut notices, 0.15, vec![press(false)]);
        assert_eq!(notices.len(), 0);
    }
}
