//! The Capture station in the Studio 2 shell (spec 7.4, P6): the pre-flight
//! strip, the live view or the capture in flight, the focus rail, the plan or
//! the health column in the inspector, and glance mode over the window. The
//! screens themselves live in `capture-*.rs`; this file places them in the
//! shell's slots and connects what belongs to the app: the catalog's
//! subjects and the naming of a finished capture, the rig popover, the Stack
//! station for a retaken plane, the hint bar, notices and the top bar.
use super::studio_route::Station;
use super::studio_shell::StationLayout;
use super::*;
use crate::capture_workspace::{Confirm, station::StationMode, style::CapturePalette};
use crate::studio_theme::{self, scale};
use crate::studio_widgets as w;
use crate::workspace_history::{NodeId, NodeKind};

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
        if let Some(plane) = self.capture.take_show_plane() {
            self.capture_show_plane(plane);
        }
        self.capture_finished();
        self.capture_confirm_window(ctx);
    }

    /// The catalog's subject names for the plan, rebuilt only when the
    /// catalog changes.
    fn capture_subjects(&mut self) {
        let revision = self.shell.catalog_revision();
        if !self.capture.subjects_stale(revision) {
            return;
        }
        let mut names: Vec<String> = self
            .catalog
            .nodes
            .iter()
            .filter(|n| n.kind == NodeKind::Subject)
            .map(|n| n.name.clone())
            .collect();
        names.sort_by_key(|n| n.to_lowercase());
        names.dedup();
        self.capture.set_subjects(names);
    }

    /// Where a finished capture goes: the plan's subject (found by name, or
    /// created beside the selected one) and its stack name, or P4's default
    /// name for the folder.
    fn capture_names(&mut self, folder: &std::path::Path) {
        let (subject, stack) = self.capture.names_for(folder).unwrap_or_default();
        let stack = if stack.trim().is_empty() {
            crate::workspace_history::default_stack_name(folder)
        } else {
            stack.trim().to_owned()
        };
        self.session_ui.pending_name = Some(stack);
        let subject = subject.trim();
        if subject.is_empty() {
            return;
        }
        if let Some(id) = self.capture_find_subject(subject) {
            self.capture_parent = Some(id);
            return;
        }
        // A new subject sits in the selected project or folder.
        let container = self.catalog.selected_container().and_then(|id| {
            let node = self.catalog.node(id)?;
            if node.kind == NodeKind::Subject {
                node.parent
            } else {
                Some(id)
            }
        });
        // With nothing selected: the "Captures" project, made once.
        let captures = self
            .catalog
            .nodes
            .iter()
            .find(|n| n.kind == NodeKind::Project && n.parent.is_none() && n.name == "Captures")
            .map(|n| n.id);
        let parent = match container.or(captures) {
            Some(id) => id,
            None => match self.catalog.create_project("Captures") {
                Ok(id) => id,
                Err(error) => {
                    self.capture.error = Some(error.to_string());
                    return;
                }
            },
        };
        match self.catalog.create_subject(parent, subject) {
            Ok(id) => {
                self.capture_parent = Some(id);
                self.persist_catalog();
            }
            Err(error) => self.capture.error = Some(error.to_string()),
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
            if busy || !(capture_open || self.stack.is_none()) {
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

    /// "Show" on a retaken plane: the plane in the Stack station when its
    /// run is open there, else its RAW's preview in the Capture canvas.
    fn capture_show_plane(&mut self, plane: u64) {
        let path = self.capture.plane_raw(plane);
        if let (Some(path), Some(stack)) = (&path, &self.stack) {
            let name = path.file_name();
            let index = stack.frames.iter().position(|f| {
                f.path.file_name() == name
                    || f.path
                        .file_name()
                        .map(|n| n.to_string_lossy().replace(".straw", ""))
                        == name.map(|n| n.to_string_lossy().replace(".straw", ""))
            });
            if let Some(index) = index {
                self.selected = index;
                self.go_station(Station::Stack);
                return;
            }
        }
        match path {
            Some(path) => self.capture.show_plane_raw(plane, path),
            None => {
                self.capture.error = Some(format!("Plane {plane}'s RAW is not on this PC yet"));
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
