//! The Studio 2 frame (implementation plan 6.3): stations across the top, a
//! hint bar along the bottom, an inspector on the right, and the canvas with
//! its control strip and rail slots in between.
//!
//! Each station still shows today's panes inside this frame; the station
//! agents replace them through the extension points below:
//!
//! * `station_layout` says which panels a station has;
//! * `station_sidebar`, `station_tools`, `station_control_strip`,
//!   `station_rail`, `station_canvas` and `station_inspector_body` /
//!   `station_inspector_footer` fill them;
//! * `station_paints_legacy` says whether a station still paints with the
//!   Graphite constants (it is then drawn in the Graphite scope on a light
//!   theme so it stays legible).
//!
//! Side effects that used to run while painting live in `tick`, which the
//! windowed, offscreen and headless loops all call.
use super::studio_route::{Drawer, LaunchRoute, Navigator, Room, Route, StackTab, Station};
use super::*;
use crate::{
    activity::ActivityStatus,
    command_palette::CommandPalette,
    notices::{self, Notices, Severity, Source},
    rig_status::RigSummary,
    studio_preferences::{self, StudioPrefs},
    studio_theme::{self, ThemeName, scale},
    studio_widgets as w,
};

#[path = "studio-shell-bars.rs"]
mod bars;
#[cfg(test)]
#[path = "studio-shell-tests.rs"]
mod tests;

pub(super) const TOP_BAR: f32 = 44.0;
pub(super) const HINT_BAR: f32 = 24.0;
pub(super) const CONTROL_STRIP: f32 = 36.0;
pub(super) const INSPECTOR_TABS: f32 = 36.0;
pub(super) const INSPECTOR_FOOTER: f32 = 53.0;
pub(super) const TOOLS_WIDTH: f32 = 44.0;
#[allow(dead_code)]
pub(super) const RAIL_HEAD: f32 = 30.0;
pub(super) const LIBRARY_SIDEBAR: f32 = 300.0;
/// Focus mode: the floating panels fade after this long without pointer motion.
const FOCUS_IDLE: f64 = 2.0;
/// The rig summary is read from the capture client at most this often.
const RIG_INTERVAL: f64 = 0.25;

/// Which panels a station has. The shell builds them in the order of plan
/// 6.3 and calls the station's fill functions.
#[derive(Clone, Copy, Debug, PartialEq)]
pub(super) struct StationLayout {
    /// `SidePanel::left("library-nav")`, default width.
    pub sidebar: Option<f32>,
    /// `SidePanel::left("studio-tools")`, 44 wide.
    pub tools: bool,
    /// `SidePanel::right("studio-inspector")`.
    pub inspector: bool,
    /// `TopBottomPanel::top("studio-control-strip")` inside the canvas column.
    pub control_strip: bool,
    /// `TopBottomPanel::bottom("studio-rail")` inside the canvas column.
    pub rail: Option<f32>,
    /// The station draws its own body with context-level panels (today's
    /// Capture workspace).
    pub owns_body: bool,
}

pub(super) struct Shell {
    pub navigator: Navigator,
    pub notices: Notices,
    pub palette: CommandPalette,
    pub prefs: StudioPrefs,
    prefs_path: Option<PathBuf>,
    pub(super) prefs_dirty: bool,
    theme_applied: Option<(ThemeName, studio_theme::Surround, bool)>,
    pub preferences_open: bool,
    pub focus: bool,
    focus_motion: f64,
    pub rig: RigSummary,
    rig_read: Option<f64>,
    rig_notice: Option<String>,
    /// The Adjust pane changed the recipe during the last paint.
    recipe_changed: bool,
    catalog_revision: u64,
    catalog_pending_seen: Option<Instant>,
    job_was_running: bool,
    export_seen: Option<PathBuf>,
    crumbs: bars::CrumbCache,
    /// The popovers' ids, as the top bar last drew them.
    pub(super) rig_popup: Option<egui::Id>,
    pub(super) tray_popup: Option<egui::Id>,
}

impl Shell {
    pub(super) fn new(launch: &LaunchOptions, catalog: Option<&Path>) -> Self {
        let prefs_path = catalog.map(studio_preferences::path_beside);
        let mut prefs = studio_preferences::load(prefs_path.as_deref());
        if let Some(theme) = launch.theme {
            prefs.theme = theme;
        }
        Self {
            navigator: Navigator::default(),
            notices: Notices::default(),
            palette: CommandPalette::default(),
            prefs,
            // Automation never rewrites the owner's display choices.
            prefs_path: prefs_path.filter(|_| !launch.headless && !launch.offscreen),
            prefs_dirty: false,
            theme_applied: None,
            preferences_open: false,
            focus: false,
            focus_motion: f64::NEG_INFINITY,
            rig: RigSummary::from_snapshot(
                &serde_json::json!({"online":false,"initialized":false}),
            ),
            rig_read: None,
            rig_notice: None,
            recipe_changed: false,
            catalog_revision: 0,
            catalog_pending_seen: None,
            job_was_running: false,
            export_seen: None,
            crumbs: Default::default(),
            rig_popup: None,
            tray_popup: None,
        }
    }
    pub(super) fn catalog_revision(&self) -> u64 {
        self.catalog_revision
    }
    pub(super) fn catalog_changed(&mut self) {
        self.catalog_revision += 1;
    }
    /// Read the rig again on the next tick (after a command or connect).
    pub(super) fn rig_read_now(&mut self) {
        self.rig_read = None;
    }
    /// Save the next render's recipe at the next tick (an Adjust change).
    pub(super) fn request_draft_save(&mut self, recipe: bool) {
        self.recipe_changed |= recipe;
    }
}

impl StrehlApp {
    // ----- route ---------------------------------------------------------

    /// Adopt flags older code wrote and write the adapter's flags.
    pub(super) fn sync_route(&mut self) {
        let result = self.result.as_deref();
        self.shell.navigator.sync(
            &mut self.sidebar,
            &mut self.process_view,
            self.active_stack,
            result,
        );
    }
    /// Go somewhere now. Anything older code changed earlier in this frame
    /// is adopted first, so this explicit choice is the one that stays.
    pub(super) fn navigate(&mut self, route: Route) {
        self.sync_route();
        let station = route.station();
        self.shell.navigator.go(route);
        self.sync_route();
        if self.shell.prefs.station != station.number() {
            self.shell.prefs.station = station.number();
            self.shell.prefs_dirty = true;
        }
    }
    /// A station's button: its route for the open document.
    pub(super) fn go_station(&mut self, station: Station) {
        if station == self.shell.navigator.station() && self.shell.navigator.drawer.is_none() {
            return;
        }
        self.navigate(Route::for_station(
            station,
            self.active_stack,
            self.result.clone(),
        ));
    }
    pub(super) fn set_room(&mut self, room: Room) {
        if self.shell.navigator.station() != Station::Stack {
            self.go_station(Station::Stack);
        }
        self.sync_route();
        self.shell.navigator.set_room(room);
        if room == Room::Photograph {
            // Leaving the engine room always returns to the process view.
            self.process_view = true;
        }
        self.sync_route();
    }
    pub(super) fn open_drawer(&mut self, drawer: Drawer) {
        self.sync_route();
        self.shell.navigator.toggle_drawer(drawer);
        self.sync_route();
    }
    /// The `--route` launch option.
    pub(super) fn apply_launch_route(&mut self, route: LaunchRoute) {
        self.navigate(route.route(self.active_stack, self.result.clone()));
    }
    /// Restore the last station on an interactive launch that asked for none.
    pub(super) fn restore_station(&mut self) {
        let Some(station) = Station::from_number(self.shell.prefs.station) else {
            return;
        };
        let needs_document = matches!(station, Station::Stack | Station::Develop | Station::Export);
        if !needs_document || self.stack.is_some() || self.result.is_some() || self.scan.is_some() {
            self.navigate(Route::for_station(
                station,
                self.active_stack,
                self.result.clone(),
            ));
        }
    }

    // ----- tick: work that used to happen while painting ------------------

    /// Run once per frame before painting, by the window, offscreen and
    /// headless loops (plan 6.2 step 2).
    pub(super) fn tick(&mut self, ctx: &egui::Context) {
        self.apply_theme(ctx);
        self.sync_route();
        // The camera connection is wanted while Capture is open; once open it
        // stays for this session, as before.
        if self.shell.navigator.station() == Station::Capture {
            self.capture.activate(ctx);
        }
        // Following a capture and handing a finished one to the Library.
        self.poll_capture(ctx);
        self.sync_route();
        self.select_edit_tool();
        self.save_pending_draft();
        self.refresh_rig(ctx);
        self.track_catalog();
        if self.shell.prefs_dirty && !ctx.input(|i| i.pointer.any_down()) {
            self.save_preferences();
        }
    }

    /// Make the Preferences (or `--theme`) theme current. `tick` runs this
    /// before every frame; offscreen rendering also runs it before the first.
    pub(super) fn apply_theme(&mut self, ctx: &egui::Context) {
        let wanted = (
            self.shell.prefs.theme,
            self.shell.prefs.surround,
            self.shell.prefs.reduced_motion,
        );
        if self.shell.theme_applied == Some(wanted) {
            return;
        }
        let current = (
            studio_theme::theme_name(ctx),
            studio_theme::surround(ctx),
            studio_theme::reduced_motion(ctx),
        );
        // A context already in this theme keeps its style untouched.
        if current != wanted {
            studio_theme::apply(ctx, wanted.0, wanted.1, wanted.2);
        }
        self.shell.theme_applied = Some(wanted);
    }

    /// Save preferences changed since the last save (on exit).
    pub(super) fn flush_preferences(&mut self) {
        if self.shell.prefs_dirty {
            self.save_preferences();
        }
    }

    pub(super) fn save_preferences(&mut self) {
        self.shell.prefs_dirty = false;
        if let Some(path) = &self.shell.prefs_path
            && let Err(error) = studio_preferences::save(path, &self.shell.prefs)
        {
            self.shell.notices.push(
                Severity::Warning,
                Source::App,
                format!("Preferences were not saved: {error}"),
                None,
            );
        }
    }

    /// Develop owns the photograph only when its pane is open on a finished
    /// render; otherwise the editor's tool returns to navigation.
    fn edit_enabled(&self) -> bool {
        self.sidebar == Some(workspace::Sidebar::Edit)
            && self.editor.loaded.is_some()
            && self.editor.path == self.result
            && self.progress.stage == Stage::Complete
    }
    fn select_edit_tool(&mut self) {
        if !self.edit_enabled() {
            self.editor.cancel_geometry();
            self.editor
                .set_tool(crate::edit_workspace::DrawingTool::Navigate);
        } else if self.editor.tool == crate::edit_workspace::DrawingTool::Navigate {
            self.editor
                .set_tool(crate::edit_workspace::DrawingTool::Select);
        }
    }

    /// Save the next render's recipe after the Adjust pane changed it.
    pub(super) fn save_pending_draft(&mut self) {
        if std::mem::take(&mut self.shell.recipe_changed) {
            self.save_active_draft();
        }
    }

    fn refresh_rig(&mut self, ctx: &egui::Context) {
        let now = ctx.input(|i| i.time);
        if self
            .shell
            .rig_read
            .is_some_and(|read| now - read < RIG_INTERVAL && now >= read)
        {
            return;
        }
        self.shell.rig_read = Some(now);
        let snapshot = self.capture.snapshot();
        let rig = RigSummary::from_snapshot(&snapshot);
        // The capture client's success notices, which nothing else shows.
        let notice = snapshot["notice"].as_str().map(str::to_owned);
        if notice != self.shell.rig_notice {
            if let Some(text) = &notice {
                self.shell
                    .notices
                    .push(Severity::Done, Source::Capture, text.clone(), None);
            }
            self.shell.rig_notice = notice;
        }
        if rig != self.shell.rig {
            self.shell.rig = rig;
        }
    }

    fn track_catalog(&mut self) {
        if self.catalog_edit_pending != self.shell.catalog_pending_seen {
            self.shell.catalog_pending_seen = self.catalog_edit_pending;
            self.shell.catalog_changed();
        }
    }

    /// Turn errors and finished work into notices. Runs after the polls.
    pub(super) fn observe_notices(&mut self) {
        let notices = &mut self.shell.notices;
        notices.observe(Source::Stack, self.error.as_deref());
        notices.observe(Source::Develop, self.editor.error.as_deref());
        notices.observe(Source::Capture, self.capture.error.as_deref());
        let running = self.job.is_some();
        if self.shell.job_was_running && !running {
            let name = self.document_name();
            match self.progress.stage {
                Stage::Complete => {
                    self.shell.notices.push(
                        Severity::Done,
                        Source::Stack,
                        format!("Stacked {name}"),
                        Some(notices::Action::OpenStation(Station::Develop.number())),
                    );
                }
                Stage::Cancelled => {
                    self.shell.notices.push(
                        Severity::Info,
                        Source::Stack,
                        format!("Stopped stacking {name}; its log is kept"),
                        Some(notices::Action::OpenLog),
                    );
                }
                _ => {}
            }
        }
        self.shell.job_was_running = running;
        if self.editor.last_export != self.shell.export_seen {
            if let Some(path) = &self.editor.last_export {
                let name = path
                    .file_name()
                    .unwrap_or_default()
                    .to_string_lossy()
                    .into_owned();
                self.shell.notices.push(
                    Severity::Done,
                    Source::Export,
                    format!("Exported {name}"),
                    None,
                );
            }
            self.shell.export_seen = self.editor.last_export.clone();
        }
    }

    /// The open stack's name, or its folder's.
    pub(super) fn document_name(&self) -> String {
        self.active_stack
            .and_then(|id| self.catalog.node(id))
            .map(|node| node.name.clone())
            .or_else(|| {
                self.stack.as_ref().map(|stack| {
                    stack
                        .directory
                        .file_name()
                        .unwrap_or_default()
                        .to_string_lossy()
                        .into_owned()
                })
            })
            .unwrap_or_else(|| "the stack".into())
    }

    /// The agent snapshot's additive Studio 2 keys (plan 11): `route`,
    /// `notices` and `activities`. `status` and `error` keep their meaning.
    pub(super) fn studio_snapshot(&self) -> [(&'static str, serde_json::Value); 3] {
        let navigator = &self.shell.navigator;
        [
            (
                "route",
                serde_json::json!({"key":navigator.route().key(),
                    "station":navigator.station().label().to_lowercase(),
                    "drawer":navigator.drawer.map(|d| d.label()),"focus":self.shell.focus}),
            ),
            ("notices", self.shell.notices.snapshot()),
            ("activities", Self::activities_value(&self.activity_hub)),
        ]
    }

    // ----- activities (plan 6.6) -------------------------------------------

    /// What runs now or needs the user, for the top bar: this frame's
    /// reports without the queue's waiting stacks. Empty, without
    /// allocating, when idle.
    pub(super) fn activities(&self) -> Vec<&ActivityStatus> {
        self.activity_hub
            .activities
            .active()
            .filter(|status| status.queued.is_none())
            .collect()
    }

    // ----- the body --------------------------------------------------------

    /// Which panels each station has. Station agents change their arm.
    pub(super) fn station_layout(&self, station: Station) -> StationLayout {
        let none = StationLayout {
            sidebar: None,
            tools: false,
            inspector: false,
            control_strip: false,
            rail: None,
            owns_body: false,
        };
        match station {
            Station::Library => StationLayout {
                sidebar: Some(LIBRARY_SIDEBAR),
                ..none
            },
            Station::Capture => StationLayout {
                owns_body: true,
                ..none
            },
            Station::Stack => StationLayout {
                inspector: self.shell.navigator.route().room() != Some(Room::Engine),
                control_strip: true,
                ..none
            },
            Station::Develop | Station::Export => StationLayout {
                inspector: true,
                control_strip: true,
                ..none
            },
        }
    }
    /// True while a station still paints with the Graphite constants. On a
    /// light theme it is then drawn in the Graphite scope.
    pub(super) fn station_paints_legacy(&self, _station: Station) -> bool {
        true
    }

    /// The station body: every panel below the top bar and above the hint bar.
    pub(super) fn workspace(&mut self, ctx: &egui::Context) {
        self.sync_route();
        let station = self.shell.navigator.station();
        if studio_theme::tokens(ctx).light && self.station_paints_legacy(station) {
            studio_theme::scoped(ctx, ThemeName::Graphite, || self.station_body(ctx, station));
        } else {
            self.station_body(ctx, station);
        }
        self.save_pending_draft();
    }

    fn station_body(&mut self, ctx: &egui::Context, station: Station) {
        let layout = self.station_layout(station);
        let drawer = self.shell.navigator.drawer;
        let inspector = layout.inspector || drawer.is_some();
        let focus = self.shell.focus;
        if !focus && inspector {
            self.inspector_panel(ctx, station);
        }
        if layout.owns_body {
            let can_import = self.job.is_none()
                && self.scan.is_none()
                && self.replay.is_none()
                && self.session_import.is_none()
                && !self.picker_active();
            self.capture.show(ctx, can_import);
            return;
        }
        let t = studio_theme::tokens(ctx);
        if let Some(width) = layout.sidebar.filter(|_| !focus) {
            egui::SidePanel::left("library-nav")
                .default_width(width)
                .width_range(232.0..=440.0)
                .resizable(true)
                .show_separator_line(false)
                .frame(egui::Frame::new().fill(t.panel).inner_margin(0))
                .show(ctx, |ui| {
                    let rect = ui.max_rect();
                    theme::rule(ui.painter(), rect.right_top(), rect.right_bottom(), t.line);
                    if self.picker_active() {
                        ui.disable();
                    }
                    self.station_sidebar(ui, station);
                });
        }
        if layout.tools && !focus {
            egui::SidePanel::left("studio-tools")
                .exact_width(TOOLS_WIDTH)
                .resizable(false)
                .show_separator_line(false)
                .frame(egui::Frame::new().fill(t.panel).inner_margin(0))
                .show(ctx, |ui| {
                    let rect = ui.max_rect();
                    theme::rule(ui.painter(), rect.right_top(), rect.right_bottom(), t.line);
                    self.station_tools(ui, station);
                });
        }
        if self.legacy_workbench() {
            // The diagnostic workbench (`--draft`, `--workbench`, a dropped
            // photograph) keeps its own panels inside the engine room.
            self.inspector(ctx);
            self.filmstrip(ctx);
            self.stack_ribbon(ctx);
            self.canvas(ctx);
        } else {
            egui::CentralPanel::default()
                .frame(egui::Frame::new().fill(t.surround))
                .show(ctx, |ui| {
                    if layout.control_strip && !focus {
                        egui::TopBottomPanel::top("studio-control-strip")
                            .exact_height(CONTROL_STRIP)
                            .resizable(false)
                            .show_separator_line(false)
                            .frame(egui::Frame::new().fill(t.panel))
                            .show_inside(ui, |ui| {
                                let rect = ui.max_rect();
                                theme::rule(
                                    ui.painter(),
                                    rect.left_bottom(),
                                    rect.right_bottom(),
                                    t.line,
                                );
                                self.station_control_strip(ui, station);
                            });
                    }
                    if let Some(height) = layout.rail.filter(|_| !focus) {
                        egui::TopBottomPanel::bottom("studio-rail")
                            .exact_height(height)
                            .resizable(false)
                            .show_separator_line(false)
                            .frame(egui::Frame::new().fill(t.panel))
                            .show_inside(ui, |ui| {
                                let rect = ui.max_rect();
                                theme::rule(
                                    ui.painter(),
                                    rect.left_top(),
                                    rect.right_top(),
                                    t.line,
                                );
                                self.station_rail(ui, station);
                            });
                    }
                    egui::CentralPanel::default()
                        .frame(egui::Frame::NONE)
                        .show_inside(ui, |ui| self.station_canvas(ui, station));
                });
        }
        if focus {
            self.focus_panels(ctx, station, layout);
        }
    }

    /// The engine room with the process view off: today's workbench.
    fn legacy_workbench(&self) -> bool {
        !self.process_view && self.shell.navigator.route().room() == Some(Room::Engine)
    }

    // ----- station fill functions: the extension points --------------------

    /// The Library's left panel. Today: the Projects pane under its heading.
    pub(super) fn station_sidebar(&mut self, ui: &mut egui::Ui, station: Station) {
        if station == Station::Library {
            let t = studio_theme::tokens(ui.ctx());
            let (heading, _) = ui
                .allocate_exact_size(egui::vec2(ui.available_width(), 29.0), egui::Sense::hover());
            let galley = w::caps_galley(ui, "Projects", scale::CAPS);
            w::paint_galley_at(
                ui.painter(),
                heading.left() + 12.0,
                heading.center().y,
                &galley,
                t.ink,
            );
            theme::rule(
                ui.painter(),
                heading.left_bottom(),
                heading.right_bottom(),
                t.line,
            );
            let (changed, action) = self.projects_pane(ui);
            self.after_pane(changed, false, action);
        }
    }
    /// The 44 px tool strip. No station has tools yet (Develop's arrive in P7).
    pub(super) fn station_tools(&mut self, _ui: &mut egui::Ui, _station: Station) {}
    /// The rail and filmstrip slot. The depth rail arrives in P3.
    pub(super) fn station_rail(&mut self, _ui: &mut egui::Ui, _station: Station) {}
    /// The canvas: today's process view, or the welcome page with nothing open.
    pub(super) fn station_canvas(&mut self, ui: &mut egui::Ui, _station: Station) {
        if self.stack.is_none()
            && !self.activity
            && self.expected_run.is_none()
            && self.result.is_none()
        {
            self.welcome_workspace(ui);
        } else {
            self.show_process(ui);
        }
    }

    /// The 36 px strip above the canvas.
    pub(super) fn station_control_strip(&mut self, ui: &mut egui::Ui, station: Station) {
        let t = studio_theme::tokens(ui.ctx());
        let rect = ui.max_rect();
        let row = egui::Rect::from_min_max(
            egui::pos2(rect.left() + 14.0, rect.top()),
            egui::pos2(rect.right() - 14.0, rect.bottom() - 1.0),
        );
        let mut strip = ui.new_child(
            egui::UiBuilder::new()
                .max_rect(row)
                .layout(egui::Layout::left_to_right(egui::Align::Center)),
        );
        strip.spacing_mut().item_spacing = egui::vec2(14.0, 0.0);
        let ui = &mut strip;
        match station {
            Station::Stack => {
                w::caps(ui, "View");
                let mut room = self.shell.navigator.route().room().unwrap_or_default();
                let before = room;
                w::segmented(
                    ui,
                    "studio-room",
                    &mut room,
                    &[
                        (Room::Photograph, "Photograph"),
                        (Room::Engine, "Engine room"),
                    ],
                );
                if room != before {
                    self.set_room(room);
                }
                vertical_rule(ui, &t);
                self.document_caption(ui, &t);
                ui.with_layout(egui::Layout::right_to_left(egui::Align::Center), |ui| {
                    if ui
                        .add(w::Button::quiet("Reset layout").small())
                        .on_hover_text("Restore the process view's proportions")
                        .clicked()
                    {
                        self.reset_layout();
                    }
                });
            }
            Station::Develop => {
                w::caps(ui, "Develop");
                self.document_caption(ui, &t);
                ui.with_layout(egui::Layout::right_to_left(egui::Align::Center), |ui| {
                    let ready = self.editor.loaded.is_some();
                    if ui
                        .add(w::Button::quiet("Fit").small().enabled(ready))
                        .on_hover_text("Fit the photograph to the canvas")
                        .clicked()
                    {
                        self.editor.fit_view_requested = true;
                    }
                    let mut large = self.edit_photo_focus;
                    w::segmented(
                        ui,
                        "studio-develop-room",
                        &mut large,
                        &[(true, "Photograph"), (false, "With instruments")],
                    );
                    self.edit_photo_focus = large;
                });
            }
            Station::Export => {
                w::caps(ui, "Export");
                self.document_caption(ui, &t);
                ui.with_layout(egui::Layout::right_to_left(egui::Align::Center), |ui| {
                    if w::link(ui, "Back to Develop", false).clicked() {
                        self.go_station(Station::Develop);
                    }
                });
            }
            Station::Library | Station::Capture => {}
        }
    }

    fn document_caption(&self, ui: &mut egui::Ui, t: &studio_theme::Tokens) {
        let name = if self.stack.is_some() || self.result.is_some() || self.active_stack.is_some() {
            self.document_name()
        } else {
            "Nothing open".into()
        };
        let state = if self.job.is_some() {
            self.progress.stage.title().to_owned()
        } else if self.progress.stage == Stage::Complete {
            match (self.render_label(), &self.expected_run) {
                (Some(label), Some(run)) => format!("{label} · {}", run.status.to_lowercase()),
                (Some(label), None) => label,
                (None, _) => "Rendered".into(),
            }
        } else if self.stack.is_some() {
            "Not stacked yet".into()
        } else {
            String::new()
        };
        ui.label(egui::RichText::new(name).size(scale::CONTROL).color(t.ink));
        if !state.is_empty() {
            ui.label(
                egui::RichText::new(state)
                    .size(scale::CONTROL)
                    .color(t.ink3),
            );
        }
    }

    /// "Render 2": the open render's place among its stack's renders, or its
    /// own label when it is not in the catalog.
    pub(super) fn render_label(&self) -> Option<String> {
        let run = self.expected_run.as_ref()?;
        let index = self
            .active_stack
            .and_then(|id| self.catalog.node(id))
            .and_then(|node| node.revisions.iter().position(|r| *r == run.directory));
        Some(index.map_or_else(|| run.label.clone(), |i| format!("Render {}", i + 1)))
    }

    pub(super) fn reset_layout(&mut self) {
        self.process_space.set_layout(Default::default());
        self.catalog.layout = Default::default();
        self.persist_catalog();
    }

    // ----- inspector ---------------------------------------------------------

    fn inspector_panel(&mut self, ctx: &egui::Context, station: Station) {
        let t = studio_theme::tokens(ctx);
        let response = egui::SidePanel::right("studio-inspector")
            .resizable(true)
            .default_width(self.shell.prefs.inspector_width)
            .width_range(studio_preferences::INSPECTOR_MIN..=studio_preferences::INSPECTOR_MAX)
            .show_separator_line(false)
            .frame(egui::Frame::new().fill(t.panel).inner_margin(0))
            .show(ctx, |ui| self.inspector_contents(ui, station));
        let width = response.response.rect.width();
        if (width - self.shell.prefs.inspector_width).abs() > 0.5
            && !ctx.input(|i| i.pointer.any_down())
        {
            self.shell.prefs.inspector_width = width;
            self.shell.prefs_dirty = true;
        }
    }

    /// Tabs, body and footer, in a panel or floating in focus mode.
    fn inspector_contents(&mut self, ui: &mut egui::Ui, station: Station) {
        let t = studio_theme::tokens(ui.ctx());
        let rect = ui.max_rect();
        // The tabs, body and footer are child areas; claim the whole panel so
        // egui keeps its width instead of shrinking it to the minimum.
        ui.expand_to_include_rect(rect);
        theme::rule(ui.painter(), rect.left_top(), rect.left_bottom(), t.line);
        let drawer = self.shell.navigator.drawer;
        let footer = drawer.is_none() && self.station_has_footer(station);
        let tabs = egui::Rect::from_min_size(rect.min, egui::vec2(rect.width(), INSPECTOR_TABS));
        let foot = egui::Rect::from_min_max(
            egui::pos2(
                rect.left(),
                rect.bottom() - if footer { INSPECTOR_FOOTER } else { 0.0 },
            ),
            rect.max,
        );
        let body = egui::Rect::from_min_max(
            egui::pos2(rect.left(), tabs.bottom()),
            egui::pos2(rect.right(), foot.top()),
        );
        let mut tab_ui = ui.new_child(
            egui::UiBuilder::new()
                .id_salt("studio-inspector-tabs")
                .max_rect(tabs.shrink2(egui::vec2(6.0, 0.0)))
                .layout(egui::Layout::left_to_right(egui::Align::Center)),
        );
        tab_ui.spacing_mut().item_spacing.x = 0.0;
        self.inspector_tabs(&mut tab_ui, station);
        theme::rule(
            ui.painter(),
            tabs.left_bottom(),
            tabs.right_bottom(),
            t.line,
        );
        let mut body_ui = ui.new_child(
            egui::UiBuilder::new()
                .id_salt("studio-inspector-body")
                .max_rect(body)
                .layout(egui::Layout::top_down(egui::Align::Min)),
        );
        body_ui.set_clip_rect(body.intersect(ui.clip_rect()));
        if self.picker_active() {
            body_ui.disable();
        }
        match drawer {
            Some(drawer) => self.drawer_body(&mut body_ui, drawer),
            None => self.station_inspector_body(&mut body_ui, station),
        }
        if footer {
            theme::rule(ui.painter(), foot.left_top(), foot.right_top(), t.line);
            let mut foot_ui = ui.new_child(
                egui::UiBuilder::new()
                    .id_salt("studio-inspector-footer")
                    .max_rect(
                        foot.shrink2(egui::vec2(16.0, 12.0))
                            .translate(egui::vec2(0.0, 0.5)),
                    )
                    .layout(egui::Layout::left_to_right(egui::Align::Center)),
            );
            foot_ui.spacing_mut().item_spacing.x = 8.0;
            self.station_inspector_footer(&mut foot_ui, station);
        }
    }

    fn inspector_tabs(&mut self, ui: &mut egui::Ui, station: Station) {
        if let Some(drawer) = self.shell.navigator.drawer {
            w::tab(ui, drawer.label(), true, None);
            ui.with_layout(egui::Layout::right_to_left(egui::Align::Center), |ui| {
                if ui
                    .add(w::Button::quiet("Close").small())
                    .on_hover_text(format!("Back to {}", station.label()))
                    .clicked()
                {
                    self.shell.navigator.close_drawer();
                    self.sync_route();
                }
            });
            return;
        }
        match station {
            Station::Stack => {
                for (tab, label) in [(StackTab::Adjust, "Adjust"), (StackTab::Review, "Review")] {
                    let selected = self.shell.navigator.stack_tab == tab;
                    if w::tab(ui, label, selected, None).clicked() && !selected {
                        self.shell.navigator.set_stack_tab(tab);
                        self.sync_route();
                    }
                }
            }
            Station::Develop => {
                w::tab(ui, "Develop", true, None);
            }
            Station::Export => {
                w::tab(ui, "Export", true, None);
            }
            Station::Library | Station::Capture => {}
        }
    }

    fn station_has_footer(&self, station: Station) -> bool {
        matches!(station, Station::Stack | Station::Develop)
    }

    /// The inspector body for a station. Today: Adjust and Review on Stack,
    /// the Edit pane on Develop, the Export pane on Export.
    pub(super) fn station_inspector_body(&mut self, ui: &mut egui::Ui, station: Station) {
        match station {
            Station::Stack => match self.shell.navigator.stack_tab {
                StackTab::Adjust => self.scrolling_pane(ui, "Adjust", |app, ui| {
                    app.session_panel(ui);
                    let recipe_before = history::Recipe::capture(&app.controls);
                    let before = (
                        app.controls.settings.clone(),
                        app.controls.exposure,
                        app.controls.gate,
                        app.controls.workers,
                    );
                    app.controls.show(ui, app.job.is_none());
                    let changed = before
                        != (
                            app.controls.settings.clone(),
                            app.controls.exposure,
                            app.controls.gate,
                            app.controls.workers,
                        );
                    if changed {
                        app.edits
                            .changed_recipe(recipe_before, ui.input(|i| i.time));
                        app.after_pane(true, true, None);
                    }
                    ui.add_space(8.0);
                    egui::CollapsingHeader::new("Destination")
                        .show(ui, |ui| app.destination_controls(ui));
                }),
                StackTab::Review => {
                    self.scrolling_pane(ui, "Review", |app, ui| app.review_panel(ui))
                }
            },
            Station::Develop => self.edit_panel(ui),
            Station::Export => self.export_panel(ui),
            Station::Library | Station::Capture => {}
        }
    }

    /// The inspector footer: the station's main action.
    pub(super) fn station_inspector_footer(&mut self, ui: &mut egui::Ui, station: Station) {
        match station {
            Station::Stack => self.stack_footer(ui),
            Station::Develop => {
                let ready = self.editor.loaded.is_some();
                if ui
                    .add(
                        w::Button::primary("Export this photograph")
                            .chevron()
                            .wide()
                            .enabled(ready),
                    )
                    .clicked()
                {
                    self.go_station(Station::Export);
                }
            }
            _ => {}
        }
    }

    fn stack_footer(&mut self, ui: &mut egui::Ui) {
        let t = studio_theme::tokens(ui.ctx());
        if let Some(job) = &self.job {
            let cancelling = job.is_cancelling();
            let label = if cancelling {
                "Stopping…"
            } else if self.pending_run.is_some() {
                "Starting…"
            } else {
                "Stacking…"
            };
            ui.add(w::Button::new(label).enabled(false));
            if ui
                .add(w::Button::danger("Stop").enabled(!cancelling))
                .on_hover_text("Stop this run; what it has written is kept")
                .clicked()
            {
                self.stop_stack();
            }
            return;
        }
        let blocker = self.stack_start_blocker();
        let total = self.stack.as_ref().map_or(0, |stack| stack.frames.len());
        let included = self
            .controls
            .settings
            .frame_limit
            .unwrap_or(total)
            .min(total);
        let finished = self.result.is_some() && self.progress.stage == Stage::Complete;
        if finished {
            if ui
                .add(w::Button::primary("Develop this render").chevron())
                .clicked()
            {
                self.go_station(Station::Develop);
            }
            let again = ui
                .add(w::Button::new("Render again").enabled(blocker.is_none()))
                .on_hover_text(blocker.map_or_else(
                    || format!("Stack {included} photos into a new render · Ctrl+Enter"),
                    str::to_owned,
                ));
            if again.clicked() {
                self.start_render();
                ui.ctx().request_repaint();
            }
        } else {
            let label = if total > 0 {
                format!("Stack {included} photos")
            } else {
                "Stack".into()
            };
            if ui
                .add(w::Button::primary(&label).enabled(blocker.is_none()))
                .on_hover_text(blocker.unwrap_or("Ctrl+Enter"))
                .clicked()
            {
                self.start_render();
                ui.ctx().request_repaint();
            }
            if let Some(reason) = blocker {
                ui.add(
                    egui::Label::new(
                        egui::RichText::new(reason)
                            .size(scale::SECONDARY)
                            .color(t.ink3),
                    )
                    .truncate(),
                );
            }
        }
    }

    pub(super) fn stop_stack(&mut self) {
        if let Some(job) = &self.job {
            job.cancel();
            self.status = "Stopping stack…".into();
        }
    }

    fn drawer_body(&mut self, ui: &mut egui::Ui, drawer: Drawer) {
        match drawer {
            Drawer::Agent => self.scrolling_pane(ui, "Agent", |app, ui| app.agent_panel(ui)),
            Drawer::Activity => self.scrolling_pane(ui, "Activity", |app, ui| {
                if let Some(error) = &app.error {
                    ui.colored_label(theme::RED, error);
                    ui.separator();
                }
                if app.logs.is_empty() {
                    theme::caption(ui, "Engine observations will be retained with each render.");
                }
                for line in &app.logs {
                    ui.add(egui::Label::new(RichText::new(line).monospace().color(MUTED)).wrap());
                }
            }),
        }
    }

    /// Today's padded, always-scrolling pane, under its old scroll id.
    fn scrolling_pane(
        &mut self,
        ui: &mut egui::Ui,
        label: &str,
        content: impl FnOnce(&mut Self, &mut egui::Ui),
    ) {
        egui::Frame::NONE.inner_margin(10).show(ui, |ui| {
            egui::ScrollArea::vertical()
                .id_salt(("workspace-pane", label))
                .auto_shrink([false, false])
                .scroll_bar_visibility(egui::scroll_area::ScrollBarVisibility::AlwaysVisible)
                .show(ui, |ui| content(self, ui));
        });
    }

    // ----- focus mode ---------------------------------------------------------

    /// How visible the floating chrome is in focus mode: it fades after
    /// two seconds without pointer motion, as one alpha (no relayout).
    pub(super) fn focus_chrome_alpha(&mut self, ctx: &egui::Context) -> f32 {
        let now = ctx.input(|i| i.time);
        let moved = ctx.input(|i| {
            i.pointer.delta() != egui::Vec2::ZERO
                || i.pointer.any_pressed()
                || i.events
                    .iter()
                    .any(|e| matches!(e, egui::Event::PointerMoved(_)))
        });
        if moved {
            self.shell.focus_motion = now;
        }
        let idle = now - self.shell.focus_motion;
        let visible = idle < FOCUS_IDLE;
        if visible {
            ctx.request_repaint_after(Duration::from_secs_f64((FOCUS_IDLE - idle).max(0.01)));
        }
        let time = if studio_theme::reduced_motion(ctx) {
            0.0
        } else {
            0.16
        };
        ctx.animate_bool_with_time(egui::Id::new("studio-focus-chrome"), visible, time)
    }

    fn focus_panels(&mut self, ctx: &egui::Context, station: Station, layout: StationLayout) {
        let alpha = self.focus_chrome_alpha(ctx);
        let t = studio_theme::tokens(ctx);
        let screen = ctx.content_rect();
        let label =
            egui::Rect::from_min_size(screen.min + egui::vec2(12.0, 10.0), egui::vec2(220.0, 20.0));
        egui::Area::new(egui::Id::new("studio-focus-label"))
            .order(egui::Order::Middle)
            .fixed_pos(label.min)
            .interactable(false)
            .show(ctx, |ui| {
                ui.set_opacity(alpha.max(0.0));
                ui.horizontal(|ui| {
                    w::caps(ui, "Focus");
                    w::key_cap(ui, "F");
                    ui.label(
                        egui::RichText::new("to leave")
                            .size(scale::HINT)
                            .color(t.ink3),
                    );
                });
            });
        if alpha <= 0.01 {
            return;
        }
        if layout.inspector || self.shell.navigator.drawer.is_some() {
            let width = self.shell.prefs.inspector_width;
            let rect = egui::Rect::from_min_max(
                egui::pos2(screen.right() - width - 8.0, screen.top() + 52.0),
                screen.max - egui::vec2(8.0, 8.0),
            );
            egui::Area::new(egui::Id::new("studio-inspector-floating"))
                .order(egui::Order::Middle)
                .fixed_pos(rect.min)
                .constrain(false)
                .show(ctx, |ui| {
                    ui.set_opacity(alpha);
                    egui::Frame::new()
                        .fill(t.panel)
                        .stroke(egui::Stroke::new(1.0_f32, t.line2))
                        .show(ui, |ui| {
                            ui.set_min_size(rect.size() - egui::vec2(2.0, 2.0));
                            ui.set_max_size(rect.size() - egui::vec2(2.0, 2.0));
                            self.inspector_contents(ui, station);
                        });
                });
        }
        if let Some(width) = layout.sidebar {
            let rect = egui::Rect::from_min_max(
                screen.min + egui::vec2(8.0, 52.0),
                egui::pos2(screen.left() + 8.0 + width, screen.bottom() - 8.0),
            );
            egui::Area::new(egui::Id::new("studio-sidebar-floating"))
                .order(egui::Order::Middle)
                .fixed_pos(rect.min)
                .constrain(false)
                .show(ctx, |ui| {
                    ui.set_opacity(alpha);
                    egui::Frame::new()
                        .fill(t.panel)
                        .stroke(egui::Stroke::new(1.0_f32, t.line2))
                        .show(ui, |ui| {
                            ui.set_min_size(rect.size() - egui::vec2(2.0, 2.0));
                            ui.set_max_size(rect.size() - egui::vec2(2.0, 2.0));
                            self.station_sidebar(ui, station);
                        });
                });
        }
    }

    // ----- keys ---------------------------------------------------------------

    /// Ctrl K, F, E and Escape (appendix C). Runs after the undo keys, which
    /// close any open menu on Escape first.
    pub(super) fn shell_shortcuts(&mut self, ctx: &egui::Context) {
        if self.picker_active() {
            return;
        }
        if ctx.input_mut(|i| i.consume_key(egui::Modifiers::COMMAND, egui::Key::K)) {
            egui::Popup::close_all(ctx);
            self.shell.palette.toggle();
        }
        if self.shell.palette.is_open() {
            self.shell.palette.take_keys(ctx);
            return;
        }
        let typing = ctx
            .memory(|m| m.focused())
            .is_some_and(|id| egui::TextEdit::load_state(ctx, id).is_some());
        if typing {
            return;
        }
        if ctx.input_mut(|i| i.consume_key(egui::Modifiers::NONE, egui::Key::F)) {
            self.shell.focus = !self.shell.focus;
            self.shell.focus_motion = ctx.input(|i| i.time);
        }
        if self.shell.navigator.station() == Station::Stack
            && ctx.input_mut(|i| i.consume_key(egui::Modifiers::NONE, egui::Key::E))
        {
            let room = match self.shell.navigator.route().room() {
                Some(Room::Engine) => Room::Photograph,
                _ => Room::Engine,
            };
            self.set_room(room);
        }
        if self.shell.focus
            && !egui::Popup::is_any_open(ctx)
            && ctx.input_mut(|i| i.consume_key(egui::Modifiers::NONE, egui::Key::Escape))
        {
            self.shell.focus = false;
        }
    }
}

fn vertical_rule(ui: &mut egui::Ui, t: &studio_theme::Tokens) {
    let (rect, _) = ui.allocate_exact_size(egui::vec2(1.0, 20.0), egui::Sense::hover());
    theme::rule(
        ui.painter(),
        rect.center_top(),
        rect.center_bottom(),
        t.line,
    );
}
