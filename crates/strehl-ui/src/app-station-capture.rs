//! The Capture station in the Studio 2 shell (spec 7.4, P6): the pre-flight
//! strip, the live view or the capture in flight, the focus rail, the plan or
//! the health column in the inspector, and glance mode over the window. The
//! screens themselves live in `capture-*.rs`; this file places them in the
//! shell's slots and connects what belongs to the app: the catalog's
//! subjects and the naming of a finished capture, the rig popover, the
//! hint bar, notices and the top bar.
use super::studio_route::Station;
use super::studio_shell::StationLayout;
use super::*;
use crate::capture_workspace::{Confirm, station::StationMode, style::CapturePalette};
use crate::studio_theme::{self, scale};
use crate::studio_widgets as w;
use crate::workspace_history::{NodeId, NodeKind};

/// The collection new subjects of captures go in when nothing else says.
const NEW_HOME: &str = "Captures";

/// The catalog's subjects for the plan's list, by name, each with its
/// collection and stack count.
pub(super) fn subject_choices(
    catalog: &crate::workspace_history::Catalog,
) -> Vec<crate::capture_workspace::subject::SubjectChoice> {
    use std::collections::HashMap;
    let mut stacks: HashMap<NodeId, usize> = HashMap::new();
    for node in &catalog.nodes {
        if node.kind == NodeKind::Stack
            && let Some(parent) = node.parent
        {
            *stacks.entry(parent).or_default() += 1;
        }
    }
    let collection = |id: NodeId| {
        let mut at = catalog.node(id)?.parent?;
        for _ in 0..64 {
            match catalog.node(at)?.parent {
                Some(parent) => at = parent,
                None => break,
            }
        }
        catalog.node(at).map(|n| n.name.clone())
    };
    let mut choices: Vec<_> = catalog
        .nodes
        .iter()
        .filter(|n| n.kind == NodeKind::Subject)
        .map(|n| {
            let count = stacks.get(&n.id).copied().unwrap_or(0);
            let count = crate::library_paint::plural(count, "stack", "stacks");
            crate::capture_workspace::subject::SubjectChoice {
                id: n.id,
                name: n.name.clone(),
                detail: match collection(n.id) {
                    Some(home) => format!("{home} · {count}"),
                    None => count,
                },
            }
        })
        .collect();
    choices.sort_by_cached_key(|c| (c.name.to_lowercase(), c.id));
    choices
}

/// The rail's height in the shell: a 30 px head, the chart and a hairline
/// (the mockups' 135 px while planning, 127 px in flight).
const RAIL_PLAN: f32 = 135.0;
const RAIL_FLIGHT: f32 = 127.0;

impl StrehlApp {
    /// Every frame, from the shell's `tick`: the connection's cadence and
    /// background polling (P0 item 8), the checker and the proof, a finished
    /// capture opened in its subject, and the requests the station makes of
    /// the shell.
    pub(super) fn capture_tick(&mut self, ctx: &egui::Context) {
        let open = self.shell.navigator.station() == Station::Capture;
        self.capture.set_station_open(open);
        self.capture
            .set_palette(CapturePalette::from_tokens(&studio_theme::tokens(ctx)));
        if open {
            self.capture.activate(ctx);
            self.capture_subjects();
        }
        // The interactive window keeps a configured camera host connected on
        // every station; automation and tests connect only when Capture opens.
        if self.headless || cfg!(test) {
            self.capture.poll_follow(self.engine.as_deref());
        } else {
            self.capture.poll_background(ctx, self.engine.as_deref());
        }
        if self.capture.take_open_rig()
            && let Some(id) = self.shell.rig_popup
        {
            egui::Popup::open_id(ctx, id);
        }
        self.capture
            .set_presenter(self.editor.viewport.presenter.as_ref());
        self.capture_finished();
        self.capture_confirm_window(ctx);
    }

    /// The catalog's subjects for the plan, rebuilt only when the catalog
    /// changes, and where a new subject would be made.
    fn capture_subjects(&mut self) {
        // The Library's "New stack of this subject" holds while the plan
        // keeps that subject; once the plan names another, it is let go.
        if let Some(target) = &self.library.target
            && target.subject.is_some()
            && target.subject != self.capture.plan_chosen()
        {
            self.library.target = None;
        }
        let home = self.capture_home();
        let home_name = home
            .and_then(|id| self.catalog.node(id))
            .map_or(NEW_HOME, |n| n.name.as_str())
            .to_owned();
        self.capture.set_subject_home(&home_name);
        let revision = self.shell.catalog_revision();
        if !self.capture.subjects_stale(revision) {
            return;
        }
        self.capture.set_subjects(subject_choices(&self.catalog));
    }

    /// Where a new subject of a capture is made: the collection the Library
    /// asked for, else beside the selected stack's subject (or in the
    /// selected collection or folder), else the "Captures" collection
    /// (None: it is made with the subject).
    pub(super) fn capture_home(&self) -> Option<NodeId> {
        let container = |id: NodeId| {
            self.catalog
                .node(id)
                .is_some_and(|n| matches!(n.kind, NodeKind::Project | NodeKind::Folder))
        };
        let asked = self
            .library
            .target
            .as_ref()
            .filter(|t| t.subject.is_none())
            .and_then(|t| t.collection)
            .filter(|&id| container(id));
        asked
            .or_else(|| {
                let id = self.catalog.selected_container()?;
                let node = self.catalog.node(id)?;
                if node.kind == NodeKind::Subject {
                    node.parent
                } else {
                    Some(id)
                }
            })
            .filter(|&id| container(id))
            .or_else(|| {
                self.catalog
                    .nodes
                    .iter()
                    .find(|n| {
                        n.kind == NodeKind::Project && n.parent.is_none() && n.name == NEW_HOME
                    })
                    .map(|n| n.id)
            })
    }

    /// Where a finished capture goes: the plan's subject (found by name, or
    /// created beside the selected one) and its stack name, or P4's default
    /// name for the folder.
    fn capture_names(&mut self, folder: &std::path::Path) {
        let (subject, stack) = self.capture_destination(folder);
        self.session_ui.pending_name = Some(stack);
        if let Some(id) = subject {
            self.capture_parent = Some(id);
        }
    }

    /// The subject `folder`'s capture goes to, and the stack's name. The
    /// plan chose an existing subject on purpose, or named a new one (found
    /// by name if it was made meanwhile); a capture the plan named nothing
    /// for (started by an agent, or opened from the captures list) stays
    /// where a stack of that folder already is, else starts a new subject
    /// named for the folder: never the most recent subject (owner feedback,
    /// 2026-11-22).
    pub(super) fn capture_destination(
        &mut self,
        folder: &std::path::Path,
    ) -> (Option<NodeId>, String) {
        let names = self.capture.run_names(folder).unwrap_or_default();
        let stack = if names.stack.trim().is_empty() {
            crate::workspace_history::default_stack_name(folder)
        } else {
            names.stack.trim().to_owned()
        };
        if let Some(id) = names.chosen.filter(|&id| {
            self.catalog
                .node(id)
                .is_some_and(|n| n.kind == NodeKind::Subject)
        }) {
            return (Some(id), stack);
        }
        let named = names.subject.trim();
        if named.is_empty() {
            let already = self.catalog.nodes.iter().find(|n| {
                n.kind == NodeKind::Stack
                    && n.stack
                        .as_ref()
                        .is_some_and(|d| d.source.as_path() == folder)
            });
            if let Some(subject) = already.and_then(|n| self.catalog.subject_of(n.id)) {
                return (Some(subject), stack);
            }
        }
        let subject = if named.is_empty() {
            crate::workspace_history::default_stack_name(folder)
        } else {
            named.to_owned()
        };
        if let Some(id) = self.capture_find_subject(&subject) {
            return (Some(id), stack);
        }
        let parent = match self.capture_home() {
            Some(id) => id,
            None => match self.catalog.create_project(NEW_HOME) {
                Ok(id) => id,
                Err(error) => {
                    self.capture.error = Some(error.to_string());
                    return (None, stack);
                }
            },
        };
        match self.catalog.create_subject(parent, &subject) {
            Ok(id) => {
                self.persist_catalog();
                (Some(id), stack)
            }
            Err(error) => {
                self.capture.error = Some(error.to_string());
                (None, stack)
            }
        }
    }

    /// A subject of that name, preferring one in the selected container.
    fn capture_find_subject(&self, name: &str) -> Option<NodeId> {
        let wanted = name.to_lowercase();
        let container = self.catalog.selected_container();
        let matches: Vec<&crate::workspace_history::ProjectNode> = self
            .catalog
            .nodes
            .iter()
            .filter(|n| n.kind == NodeKind::Subject && n.name.to_lowercase() == wanted)
            .collect();
        matches
            .iter()
            .find(|n| n.parent == container || Some(n.id) == container)
            .or(matches.first())
            .map(|n| n.id)
    }

    /// A finished, checked capture opens in its subject and is stacked; a
    /// completed or stopped capture asked for from the station opens too.
    fn capture_finished(&mut self) {
        let busy = self.job.is_some()
            || self.scan.is_some()
            || self.replay.is_some()
            || self.session_import.is_some()
            || self.picker_active();
        if let Some(folder) = self.capture.take_finished_capture() {
            let name = folder
                .file_name()
                .unwrap_or_default()
                .to_string_lossy()
                .into_owned();
            // It opens itself only when that interrupts nothing: no operation
            // in flight, and either Capture is open or no other bracket is.
            let capture_open = self.shell.navigator.station() == Station::Capture;
            let only_stacking = self.job.is_some()
                && self.scan.is_none()
                && self.replay.is_none()
                && self.session_import.is_none()
                && !self.picker_active();
            if only_stacking {
                // A stack is rendering: this capture waits in the stack queue
                // and is stacked when the queue reaches it (plan 6.6).
                self.queue_finished_capture(folder);
            } else if busy || !(capture_open || self.stack.is_none()) {
                self.capture.follow_note = Some(format!(
                    "{name} is checked. Open it from the captures list to stack it."
                ));
            } else {
                self.capture.follow_note = Some(format!("Opened {name}."));
                self.capture_names(&folder);
                self.import(folder.clone());
                self.stack_when_read = Some(folder);
            }
        }
        if let Some(folder) = &self.stack_when_read
            && self.scan.is_none()
        {
            let same = self.stack.as_ref().is_some_and(|stack| {
                std::fs::canonicalize(&stack.directory).ok() == std::fs::canonicalize(folder).ok()
            });
            let name = folder
                .file_name()
                .unwrap_or_default()
                .to_string_lossy()
                .into_owned();
            self.stack_when_read = None;
            if same {
                match self.stack_start_blocker() {
                    None => {
                        self.start_render();
                        self.capture.follow_note = Some(format!("Stacking {name}."));
                    }
                    Some(reason) => {
                        self.capture.follow_note =
                            Some(format!("{name} is open. Not stacked: {reason}."));
                    }
                }
            }
        }
        if let Some(folder) = self.capture.take_handoff() {
            if busy {
                self.capture.error = Some(
                    "Finish the active workspace operation, then open the capture again.".into(),
                );
            } else {
                self.capture_names(&folder);
                self.import(folder);
            }
        }
    }

    /// Shut down or disconnect from the rig popover asks first (P0 item 7).
    fn capture_confirm_window(&mut self, ctx: &egui::Context) {
        let Some(confirm) = self.capture.confirm.filter(|c| *c != Confirm::Stop) else {
            return;
        };
        let t = studio_theme::tokens(ctx);
        let (title, sentence, yes, command) = match confirm {
            Confirm::ShutDown => (
                "Shut down the camera",
                "Restore the camera's settings, put it in standby and switch its outlet off?",
                "Shut down now",
                strehl_capture::session::Command::Power {
                    device: strehl_capture::power::Outlet::Camera,
                    on: false,
                },
            ),
            _ => (
                "Disconnect the camera",
                "Release the camera? The marks and the subject region are cleared.",
                "Disconnect now",
                strehl_capture::session::Command::Disconnect {},
            ),
        };
        let mut answer = None;
        egui::Modal::new(egui::Id::new("capture-confirm")).show(ctx, |ui| {
            ui.set_width(360.0);
            w::caps(ui, title);
            ui.add_space(8.0);
            ui.label(egui::RichText::new(sentence).color(t.ink2));
            ui.add_space(12.0);
            ui.horizontal(|ui| {
                if ui.add(w::Button::danger(yes)).clicked() {
                    answer = Some(true);
                }
                if ui.add(w::Button::new("Cancel")).clicked() {
                    answer = Some(false);
                }
            });
        });
        match answer {
            Some(true) => {
                self.capture.confirm = None;
                let snapshot = self.capture.snapshot();
                let result = crate::rig_status::request(&snapshot, command)
                    .and_then(|request| self.capture.submit(request));
                if let Err(error) = result {
                    self.capture.error = Some(format!("{error:#}"));
                }
                self.shell.rig_read_now();
            }
            Some(false) => self.capture.confirm = None,
            None => {}
        }
    }

    /// Asks before the rig popover shuts the camera down or disconnects it;
    /// `true` when the command waits for that answer.
    pub(super) fn capture_needs_confirm(
        &mut self,
        command: &strehl_capture::session::Command,
    ) -> bool {
        use strehl_capture::{power::Outlet, session::Command};
        let confirm = match command {
            Command::Power {
                device: Outlet::Camera,
                on: false,
            } => Confirm::ShutDown,
            Command::Disconnect {} => Confirm::Disconnect,
            _ => return false,
        };
        self.capture.confirm = Some(confirm);
        true
    }

    // ----- the shell's slots ------------------------------------------------

    pub(super) fn capture_layout(&self) -> StationLayout {
        let flight = self.capture.station_mode() == StationMode::Flight;
        StationLayout {
            sidebar: None,
            tools: false,
            inspector: true,
            control_strip: !flight,
            rail: Some(if flight { RAIL_FLIGHT } else { RAIL_PLAN }),
            owns_body: false,
        }
    }

    pub(super) fn capture_control_strip(&mut self, ui: &mut egui::Ui) {
        self.capture.station_strip(ui);
    }

    pub(super) fn capture_rail(&mut self, ui: &mut egui::Ui) {
        self.capture.station_rail(ui);
    }

    pub(super) fn capture_canvas(&mut self, ui: &mut egui::Ui) {
        self.capture.station_canvas(ui);
        if self.capture.glance_open() {
            self.capture.station_glance_overlay(ui.ctx());
        }
    }

    pub(super) fn capture_inspector(&mut self, ui: &mut egui::Ui) {
        self.capture.station_inspector(ui);
    }

    /// The hint bar's keys and note for the Capture station.
    pub(super) fn capture_hints(&mut self, ui: &mut egui::Ui) {
        let t = studio_theme::tokens(ui.ctx());
        let hints = self.capture.station_hints();
        for (key, text) in &hints.keys {
            for part in key.split(' ') {
                w::key_cap(ui, part);
            }
            ui.label(egui::RichText::new(*text).size(scale::HINT).color(t.ink3));
            ui.add_space(12.0);
        }
        ui.with_layout(egui::Layout::right_to_left(egui::Align::Center), |ui| {
            ui.label(
                egui::RichText::new(crate::display_path::display_path(std::path::Path::new(
                    &hints.note,
                )))
                .size(scale::HINT)
                .color(t.ink3),
            );
        });
    }

    /// The capture client's unread success notice, once.
    pub(super) fn capture_notice(&mut self) -> Option<String> {
        self.capture.unread_notice()
    }
}

#[cfg(test)]
#[path = "app-station-capture-tests.rs"]
mod tests;
