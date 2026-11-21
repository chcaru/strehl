//! The command palette (implementation plan 7.1), Ctrl K: subjects, stacks,
//! renders and every station action with its key.
//!
//! Matching is case-insensitive: a prefix of the whole label or of any word
//! first, then any subsequence. The index is built when the palette opens and
//! kept until the catalog's revision changes; the matches are recomputed only
//! when the query or the index changes, so an open palette costs one short
//! list per frame.
use crate::studio_theme::{self, scale};
use crate::studio_widgets as w;
use crate::workspace_icons::{self, Icon};
use eframe::egui::{self, Color32, Key, Rect, Ui};
use std::path::PathBuf;

/// What running an entry does; the shell carries it out.
#[derive(Clone, Debug, PartialEq)]
pub(crate) enum Command {
    /// A station by its number, 1 to 5.
    Station(u8),
    EngineRoom,
    FocusMode,
    StartStack,
    StopStack,
    Undo,
    Redo,
    OpenSources,
    Preferences,
    Theme(crate::studio_theme::ThemeName),
    Agent,
    ActivityLog,
    /// Today's project tree, in the inspector.
    ProjectTree,
    Rig,
    ResetLayout,
    /// A stack in the catalog.
    OpenStack(u64),
    /// A saved render, by its run directory.
    OpenRun(PathBuf),
    /// A project or folder, selected in the Library.
    Reveal(u64),
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(crate) enum Group {
    Actions,
    GoTo,
}
impl Group {
    fn label(self) -> &'static str {
        match self {
            Self::Actions => "Actions",
            Self::GoTo => "Go to",
        }
    }
}

#[derive(Clone, Debug, PartialEq)]
pub(crate) struct Entry {
    pub group: Group,
    pub label: String,
    /// Dim text after the label, such as a stack's collection.
    pub detail: Option<String>,
    pub key: Option<&'static str>,
    pub icon: Option<Icon>,
    pub command: Command,
    lower: String,
}
impl Entry {
    pub(crate) fn new(group: Group, label: impl Into<String>, command: Command) -> Self {
        let label = label.into();
        Self {
            group,
            lower: label.to_lowercase(),
            label,
            detail: None,
            key: None,
            icon: None,
            command,
        }
    }
    pub(crate) fn icon(mut self, icon: Icon) -> Self {
        self.icon = Some(icon);
        self
    }
    pub(crate) fn key(mut self, key: &'static str) -> Self {
        self.key = Some(key);
        self
    }
    pub(crate) fn detail(mut self, detail: impl Into<String>) -> Self {
        self.detail = Some(detail.into());
        self
    }
}

/// 0 for a prefix of the label, 1 for a prefix of a later word, 2 for a
/// subsequence; `None` when the query does not match.
pub(crate) fn rank(label_lower: &str, query_lower: &str) -> Option<u8> {
    if query_lower.is_empty() || label_lower.starts_with(query_lower) {
        return Some(0);
    }
    if label_lower
        .split(|c: char| !c.is_alphanumeric())
        .any(|word| word.starts_with(query_lower))
    {
        return Some(1);
    }
    let mut letters = label_lower.chars();
    query_lower
        .chars()
        .filter(|c| !c.is_whitespace())
        .all(|wanted| letters.any(|c| c == wanted))
        .then_some(2)
}

/// Shown at most at once.
pub(crate) const VISIBLE: usize = 12;

#[derive(Default)]
pub(crate) struct CommandPalette {
    open: bool,
    query: String,
    selected: usize,
    index: Vec<Entry>,
    index_key: Option<u64>,
    matches: Vec<usize>,
    matches_for: Option<(String, Option<u64>)>,
    focus_requested: bool,
    /// Arrow and Enter presses taken at the start of the frame.
    pending: (bool, bool, bool),
    /// How many times the index was built (tests and diagnostics).
    pub builds: u64,
}

impl CommandPalette {
    pub(crate) fn is_open(&self) -> bool {
        self.open
    }
    pub(crate) fn open(&mut self) {
        self.open = true;
        self.query.clear();
        self.selected = 0;
        self.focus_requested = true;
        self.matches_for = None;
    }
    pub(crate) fn close(&mut self) {
        self.open = false;
        self.pending = (false, false, false);
    }
    /// Take the palette's keys before any view below it can: arrows, Enter,
    /// and Escape (which closes it). The shell calls this at the start of the
    /// frame; `show` calls it again for anything that arrived since.
    pub(crate) fn take_keys(&mut self, ctx: &egui::Context) {
        if !self.open {
            return;
        }
        let (up, down, enter, escape) = ctx.input_mut(|input| {
            (
                input.consume_key(egui::Modifiers::NONE, Key::ArrowUp),
                input.consume_key(egui::Modifiers::NONE, Key::ArrowDown),
                input.consume_key(egui::Modifiers::NONE, Key::Enter),
                input.consume_key(egui::Modifiers::NONE, Key::Escape),
            )
        });
        if escape {
            self.close();
            return;
        }
        self.pending.0 |= up;
        self.pending.1 |= down;
        self.pending.2 |= enter;
    }
    pub(crate) fn toggle(&mut self) {
        if self.open {
            self.close();
        } else {
            self.open();
        }
    }
    #[cfg(test)]
    pub(crate) fn set_query(&mut self, query: &str) {
        self.query = query.into();
        self.selected = 0;
    }
    /// The catalog revision the index was built for.
    pub(crate) fn index_key(&self) -> Option<u64> {
        self.index_key
    }
    /// Rebuild the index only for a new catalog revision.
    pub(crate) fn ensure_index(&mut self, key: u64, build: impl FnOnce() -> Vec<Entry>) {
        if self.index_key != Some(key) {
            self.index = build();
            self.index_key = Some(key);
            self.builds += 1;
            self.matches_for = None;
        }
    }
    pub(crate) fn matches(&mut self) -> &[usize] {
        let current = self
            .matches_for
            .as_ref()
            .is_some_and(|(query, key)| *query == self.query && *key == self.index_key);
        if !current {
            let key = (self.query.clone(), self.index_key);
            let query = self.query.trim().to_lowercase();
            let mut ranked: Vec<(u8, usize)> = self
                .index
                .iter()
                .enumerate()
                .filter_map(|(i, entry)| rank(&entry.lower, &query).map(|r| (r, i)))
                .collect();
            // Stable: equal ranks keep actions before places, in index order.
            ranked.sort_by_key(|(rank, i)| (*rank, self.index[*i].group == Group::GoTo, *i));
            self.matches = ranked.into_iter().map(|(_, i)| i).take(64).collect();
            self.matches_for = Some(key);
            self.selected = self.selected.min(self.matches.len().saturating_sub(1));
        }
        &self.matches
    }
    #[cfg(test)]
    pub(crate) fn entry(&self, index: usize) -> &Entry {
        &self.index[index]
    }

    /// Draw the palette and its scrim below the top bar. Returns the command
    /// to run; the palette closes itself when one is chosen.
    pub(crate) fn show(
        &mut self,
        ctx: &egui::Context,
        top: f32,
        available: impl Fn(&Command) -> bool,
    ) -> Option<Command> {
        if !self.open {
            return None;
        }
        let t = studio_theme::tokens(ctx);
        self.take_keys(ctx);
        if !self.open {
            return None;
        }
        let (up, down, enter) = std::mem::take(&mut self.pending);
        let count = self.matches().len();
        if down && count > 0 {
            self.selected = (self.selected + 1).min(count - 1);
        }
        if up {
            self.selected = self.selected.saturating_sub(1);
        }
        let screen = ctx.content_rect();
        let scrim = Rect::from_min_max(egui::pos2(screen.left(), top), screen.max);
        let scrim_layer =
            egui::LayerId::new(egui::Order::Foreground, egui::Id::new("palette-scrim"));
        let mut dismissed = false;
        egui::Area::new(scrim_layer.id)
            .order(scrim_layer.order)
            .fixed_pos(scrim.min)
            .constrain(false)
            .show(ctx, |ui| {
                let response = ui.allocate_rect(scrim, egui::Sense::click());
                ui.painter()
                    .rect_filled(scrim, 0.0, Color32::from_black_alpha(128));
                dismissed = response.clicked();
            });
        let width = 620.0_f32.min(screen.width() - 32.0);
        let origin = egui::pos2(screen.center().x - width * 0.5, top + 106.0);
        let layer = egui::LayerId::new(egui::Order::Foreground, egui::Id::new("command-palette"));
        let mut chosen = None;
        egui::Area::new(layer.id)
            .order(layer.order)
            .fixed_pos(origin)
            .constrain(false)
            .show(ctx, |ui| {
                egui::Frame::popup(ui.style())
                    .inner_margin(0)
                    .fill(t.panel)
                    .stroke(egui::Stroke::new(1.0_f32, t.line2))
                    .show(ui, |ui| {
                        ui.set_width(width);
                        ui.spacing_mut().item_spacing = egui::vec2(0.0, 0.0);
                        chosen = self.contents(ui, &t, enter, &available);
                    });
            });
        ctx.move_to_top(scrim_layer);
        ctx.move_to_top(layer);
        if chosen.is_some() || dismissed {
            self.close();
        }
        chosen
    }

    fn contents(
        &mut self,
        ui: &mut Ui,
        t: &crate::studio_theme::Tokens,
        enter: bool,
        available: &impl Fn(&Command) -> bool,
    ) -> Option<Command> {
        let mut chosen = None;
        egui::Frame::NONE
            .inner_margin(egui::Margin::symmetric(16, 12))
            .show(ui, |ui| {
                ui.horizontal(|ui| {
                    paint_search(ui, t.ink3);
                    ui.add_space(10.0);
                    let edit = ui.add(
                        egui::TextEdit::singleline(&mut self.query)
                            .id_salt("command-palette-query")
                            .frame(false)
                            .hint_text("Go to a stack, a render, or a command")
                            .font(egui::FontId::proportional(16.0))
                            .desired_width(f32::INFINITY),
                    );
                    if std::mem::take(&mut self.focus_requested) {
                        edit.request_focus();
                    }
                    if edit.changed() {
                        self.selected = 0;
                    }
                });
            });
        let rect = ui.min_rect();
        crate::theme::rule(
            ui.painter(),
            rect.left_bottom(),
            rect.right_bottom(),
            t.line,
        );
        let matches = self.matches().to_vec();
        if matches.is_empty() {
            egui::Frame::NONE
                .inner_margin(egui::Margin::symmetric(16, 12))
                .show(ui, |ui| {
                    ui.label(
                        egui::RichText::new("Nothing matches")
                            .size(scale::SECONDARY)
                            .color(t.ink3),
                    );
                });
            return None;
        }
        // Keep the selection in view within the visible window.
        let first = self.selected.saturating_sub(VISIBLE - 1);
        let mut group = None;
        ui.add_space(4.0);
        for (position, &index) in matches.iter().enumerate().skip(first).take(VISIBLE) {
            let entry = &self.index[index];
            if group != Some(entry.group) {
                group = Some(entry.group);
                egui::Frame::NONE
                    .inner_margin(egui::Margin {
                        left: 16,
                        right: 16,
                        top: 8,
                        bottom: 4,
                    })
                    .show(ui, |ui| {
                        w::caps(ui, entry.group.label());
                    });
            }
            let enabled = available(&entry.command);
            let selected = position == self.selected;
            let (row, response) = ui.allocate_exact_size(
                egui::vec2(ui.available_width(), 31.0),
                if enabled {
                    egui::Sense::click()
                } else {
                    egui::Sense::hover()
                },
            );
            if response.hovered() && ui.input(|i| i.pointer.delta() != egui::Vec2::ZERO) {
                self.selected = position;
            }
            let painter = ui.painter();
            if selected {
                painter.rect_filled(row, 0.0, t.accent_soft);
                painter.rect_filled(
                    Rect::from_min_size(row.min, egui::vec2(2.0, row.height())),
                    0.0,
                    t.accent,
                );
            }
            let ink = if !enabled {
                t.ink3
            } else if selected {
                t.ink
            } else {
                t.ink2
            };
            let label = w::text_galley(
                ui,
                &entry.label,
                crate::studio_fonts::Face::Regular,
                scale::BODY,
            );
            let mut x = row.left() + 16.0;
            if let Some(icon) = entry.icon {
                workspace_icons::paint(
                    ui.painter(),
                    egui::pos2(x + 7.5, row.center().y),
                    15.0,
                    icon,
                    if selected { t.ink } else { t.ink3 },
                );
            }
            x += 25.0;
            w::paint_galley_at(ui.painter(), x, row.center().y, &label, ink);
            x += label.size().x + 10.0;
            if let Some(detail) = &entry.detail {
                let galley = w::text_galley(
                    ui,
                    detail,
                    crate::studio_fonts::Face::Regular,
                    scale::SECONDARY,
                );
                w::paint_galley_at(ui.painter(), x, row.center().y, &galley, t.ink3);
            }
            if let Some(key) = entry.key {
                let mut key_ui = ui.new_child(
                    egui::UiBuilder::new()
                        .max_rect(Rect::from_min_max(
                            egui::pos2(row.right() - 160.0, row.top() + 7.0),
                            egui::pos2(row.right() - 16.0, row.bottom() - 7.0),
                        ))
                        .layout(egui::Layout::right_to_left(egui::Align::Center)),
                );
                w::key_cap(&mut key_ui, key);
            }
            if response.clicked() || (enter && selected && enabled) {
                chosen = Some(entry.command.clone());
            }
        }
        ui.add_space(6.0);
        chosen
    }
}

/// The magnifier drawn with strokes, as in the top bar.
pub(crate) fn paint_search(ui: &mut Ui, color: Color32) -> egui::Response {
    let (rect, response) = ui.allocate_exact_size(egui::vec2(15.0, 15.0), egui::Sense::hover());
    paint_search_at(ui.painter(), rect.center(), color);
    response
}
pub(crate) fn paint_search_at(painter: &egui::Painter, center: egui::Pos2, color: Color32) {
    let stroke = egui::Stroke::new(1.25_f32, color);
    let lens = center + egui::vec2(-1.5, -1.5);
    painter.circle_stroke(lens, 4.5, stroke);
    painter.line_segment(
        [lens + egui::vec2(3.3, 3.3), lens + egui::vec2(7.0, 7.0)],
        stroke,
    );
}

#[cfg(test)]
#[path = "command-palette-tests.rs"]
mod tests;
