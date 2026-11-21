//! The top bar and the hint bar (implementation plan 6.3 and 7.1), with the
//! popovers they open and the overlays above the frame: the command palette
//! and Preferences.
use super::*;
use crate::{
    activity_tray::{self, TrayAction},
    command_palette::{Command as PaletteCommand, Entry, Group},
    rig_status::{self, RigAction},
    studio_fonts::Face,
    studio_widgets::Mark,
    window_chrome,
};

/// The breadcrumb, rebuilt only when the document or catalog changes.
#[derive(Default)]
pub(super) struct CrumbCache {
    key: Option<CrumbKey>,
    segments: Vec<Crumb>,
}
#[derive(Clone, PartialEq)]
struct CrumbKey {
    catalog: u64,
    nodes: usize,
    stack: Option<crate::workspace_history::NodeId>,
    epoch: u64,
    result: bool,
    run: Option<PathBuf>,
    navigation: u64,
    /// On Capture: the plan's subject and stack, and the phase's word.
    capture: Option<(String, String, &'static str)>,
    /// On Develop and Export: the open version's id.
    version: Option<String>,
}
#[derive(Clone, Debug, PartialEq)]
pub(super) struct Crumb {
    pub label: String,
    pub target: CrumbTarget,
}
#[derive(Clone, Copy, Debug, PartialEq)]
pub(super) enum CrumbTarget {
    Library,
    /// A project or folder: open the Library with it selected.
    Container(crate::workspace_history::NodeId),
    /// The open stack: its siblings.
    Stack(crate::workspace_history::NodeId),
    /// The open render: the stack's other renders.
    Render(crate::workspace_history::NodeId),
    /// The engine room: back to the photograph.
    Room,
    /// A subject: its page.
    Subject(crate::workspace_history::NodeId),
    /// Where you are, with nothing behind it.
    Here,
}

const CRUMBS_MAX: f32 = 430.0;
const CRUMB_GAP: f32 = 18.0;

/// One status button on the right of the top bar.
struct Stat<'a> {
    id: &'a str,
    mark: Option<Mark>,
    name: &'a str,
    dim: &'a str,
    progress: Option<f32>,
    search: bool,
    /// The search stat's "Ctrl K" cap (dropped when the bar is tight).
    key: bool,
    max_width: f32,
}

/// A stat's parts at its allotted width: text shortens with an ellipsis,
/// and below a readable minimum it is left out.
struct StatLayout {
    name: Option<std::sync::Arc<egui::Galley>>,
    dim: Option<std::sync::Arc<egui::Galley>>,
    key: Option<std::sync::Arc<egui::Galley>>,
    width: f32,
}

/// Text narrower than this is not worth showing: the mark stands alone.
const STAT_TEXT_MIN: f32 = 28.0;
/// The activity keeps at least this much before anything else gives way.
const ACTIVITY_FLOOR: f32 = 170.0;
/// An unread failure keeps this much before it folds into the activity.
const FAILURE_FLOOR: f32 = 160.0;

fn stat_layout(ui: &egui::Ui, stat: &Stat<'_>) -> StatLayout {
    let gap = 8.0;
    let key = (stat.search && stat.key).then(|| {
        ui.painter().layout_job(crate::studio_fonts::tracked(
            "Ctrl K",
            w::font(ui, Face::Regular, scale::CAPS),
            egui::Color32::PLACEHOLDER,
            0.08,
        ))
    });
    let mut content = 0.0;
    if stat.mark.is_some() {
        content += w::MARK_SLOT;
    }
    if stat.search {
        content += 15.0 + key.as_ref().map_or(0.0, |k| gap + k.size().x + 10.0);
    }
    let lead = if content > 0.0 { gap } else { 0.0 };
    let mut room = stat.max_width - content - 28.0 - lead;
    let mut text = |label: &str| {
        if label.is_empty() || room < STAT_TEXT_MIN {
            return None;
        }
        let galley = elided(ui, label, room);
        room -= galley.size().x + gap;
        Some(galley)
    };
    let name = text(stat.name);
    let dim = text(stat.dim);
    let words = match (&name, &dim) {
        (Some(n), Some(d)) => n.size().x + gap + d.size().x,
        (Some(g), None) | (None, Some(g)) => g.size().x,
        (None, None) => 0.0,
    };
    let width = content + if words > 0.0 { lead + words } else { 0.0 } + 28.0;
    StatLayout {
        name,
        dim,
        key,
        width: width.ceil(),
    }
}

/// `text` on one line, at most `max` wide, ending in an ellipsis if cut.
fn elided(ui: &egui::Ui, text: &str, max: f32) -> std::sync::Arc<egui::Galley> {
    let mut job = egui::text::LayoutJob::single_section(
        text.to_owned(),
        egui::TextFormat {
            font_id: w::font(ui, Face::Regular, scale::CONTROL),
            color: egui::Color32::PLACEHOLDER,
            ..Default::default()
        },
    );
    job.wrap = egui::text::TextWrapping {
        max_width: max.max(1.0),
        max_rows: 1,
        break_anywhere: true,
        overflow_character: Some('…'),
    };
    ui.painter().layout_job(job)
}

/// Fit the right end of the top bar into `budget`, between the stations and
/// the window buttons. With nothing running, an unread failure takes the
/// activity's words. Then in order: the activity shortens to its floor; the
/// rig drops its fact; the failure shortens to its floor, then folds into the
/// activity's mark; search drops its key; the rig keeps only its lamp; the
/// activity takes what is left, down to its mark.
fn fit_right_cluster(
    ui: &egui::Ui,
    budget: f32,
    idle: bool,
    palette: &mut Stat<'_>,
    activity: &mut Stat<'_>,
    failure: &mut Option<Stat<'_>>,
    rig: &mut Stat<'_>,
) {
    let width = |stat: &Stat<'_>| stat_layout(ui, stat).width;
    let others = |palette: &Stat<'_>, failure: &Option<Stat<'_>>, rig: &Stat<'_>| {
        width(palette) + failure.as_ref().map_or(0.0, &width) + width(rig)
    };
    let over = |p: &Stat<'_>, a: &Stat<'_>, f: &Option<Stat<'_>>, r: &Stat<'_>| {
        others(p, f, r) + width(a) > budget
    };
    let idle_words = (activity.name, activity.dim);
    if idle && failure.is_some() && over(palette, activity, failure, rig) {
        (activity.name, activity.dim) = ("", "");
    }
    if over(palette, activity, failure, rig) {
        let left = budget - others(palette, failure, rig);
        activity.max_width = activity.max_width.min(left.max(ACTIVITY_FLOOR));
    }
    if over(palette, activity, failure, rig) {
        rig.dim = "";
    }
    if over(palette, activity, failure, rig)
        && let Some(failure) = failure.as_mut()
    {
        let left = budget - width(palette) - width(activity) - width(rig);
        failure.max_width = failure.max_width.min(left.max(FAILURE_FLOOR));
    }
    if over(palette, activity, failure, rig) && failure.take().is_some() {
        activity.mark = Some(Mark::Failed);
        if idle {
            (activity.name, activity.dim) = idle_words;
        }
    }
    if over(palette, activity, failure, rig) {
        palette.key = false;
    }
    if over(palette, activity, failure, rig) {
        rig.name = "";
    }
    if over(palette, activity, failure, rig) {
        activity.max_width = (budget - others(palette, failure, rig)).max(0.0);
    }
}

/// The activity as the top bar shows it: "Capturing 61 / 96 · 3:18 left".
/// The kind's word is dropped when the phase already says it.
fn activity_words(activity: &crate::activity::ActivityStatus) -> (String, String) {
    let stem = |word: &str| {
        let word = word.trim().to_lowercase();
        word.strip_suffix('e').map(str::to_owned).unwrap_or(word)
    };
    let phase = activity.phase.trim();
    let title = activity.title.trim();
    let repeats =
        !phase.is_empty() && !title.is_empty() && phase.to_lowercase().starts_with(&stem(title));
    let mut parts = Vec::new();
    if !phase.is_empty() && !repeats {
        parts.push(phase.to_owned());
    }
    if let (Some(done), Some(total)) = (activity.done, activity.total) {
        parts.push(format!("{done} / {total}"));
    }
    if let Some(eta) = activity.eta {
        parts.push(format!("{} left", clock(eta)));
    } else if let Some(started) = activity.started {
        parts.push(clock(Instant::now().saturating_duration_since(started)));
    }
    let name = if repeats { phase } else { title };
    (name.to_owned(), parts.join(" · "))
}

/// "3:18", "1:02:05".
fn clock(duration: Duration) -> String {
    let seconds = duration.as_secs_f64().round() as u64;
    let (h, m, s) = (seconds / 3600, seconds / 60 % 60, seconds % 60);
    if h > 0 {
        format!("{h}:{m:02}:{s:02}")
    } else {
        format!("{m}:{s:02}")
    }
}

impl StrehlApp {
    /// The top bar and the hint bar. In focus mode the canvas has the window.
    pub(crate) fn shell_bars(&mut self, ctx: &egui::Context) {
        if self.shell.focus {
            return;
        }
        let t = studio_theme::tokens(ctx);
        egui::TopBottomPanel::top("studio-top")
            .exact_height(TOP_BAR)
            .resizable(false)
            .show_separator_line(false)
            .frame(egui::Frame::new().fill(t.panel))
            .show(ctx, |ui| self.top_bar(ui));
        egui::TopBottomPanel::bottom("studio-hints")
            .exact_height(HINT_BAR)
            .resizable(false)
            .show_separator_line(false)
            .frame(egui::Frame::new().fill(t.panel))
            .show(ctx, |ui| self.hint_bar(ui));
    }

    /// The palette and Preferences, above the frame.
    pub(crate) fn shell_overlays(&mut self, ctx: &egui::Context) {
        if self.shell.palette.is_open() {
            let key = self
                .shell
                .catalog_revision()
                .wrapping_mul(31)
                .wrapping_add(self.catalog.nodes.len() as u64)
                .wrapping_mul(31)
                .wrapping_add(self.catalog.runs.len() as u64);
            // Gather the entries only when the catalog changed since the
            // index was built; an open palette otherwise rebuilds nothing.
            if self.shell.palette.index_key() != Some(key) {
                let entries = self.palette_entries();
                self.shell.palette.ensure_index(key, || entries);
            }
            let top = if self.shell.focus { 0.0 } else { TOP_BAR };
            let state = PaletteAvailability::of(self);
            let chosen = self
                .shell
                .palette
                .show(ctx, top, |command| state.allows(command));
            if let Some(command) = chosen {
                self.run_palette_command(ctx, command);
            }
        }
        if self.shell.preferences_open {
            self.preferences_window(ctx);
        }
    }

    // ----- top bar -----------------------------------------------------------

    fn top_bar(&mut self, ui: &mut egui::Ui) {
        let ctx = ui.ctx().clone();
        let t = studio_theme::tokens(&ctx);
        let bar = ui.max_rect();
        let modal = self.picker_active();
        let height = bar.height() - 1.0;
        theme::rule(ui.painter(), bar.left_bottom(), bar.right_bottom(), t.line);
        // The stations, centred on the window. The right end has the room
        // between them and the window buttons and never more.
        let stations = self.stations(ui, &t, bar, height);
        let mut right = bar.right() - window_chrome::CONTROLS_WIDTH;
        let budget = (right - stations.right() - 12.0).max(0.0);
        let activities = self.activities();
        let (activity_mark, activity_name, activity_dim, progress) = match activities.first() {
            None => (
                Mark::NotYet,
                String::new(),
                "Nothing running".to_owned(),
                None,
            ),
            Some(first) => {
                let (name, mut dim) = activity_words(first);
                if activities.len() > 1 {
                    dim = format!("{dim} · +{}", activities.len() - 1);
                }
                (Mark::Running, name, dim, first.fraction())
            }
        };
        if activities
            .iter()
            .any(|a| a.kind == crate::activity::ActivityKind::Stack)
        {
            ctx.request_repaint_after(Duration::from_secs(1));
        }
        let running = activities.len();
        let failure = self
            .shell
            .notices
            .newest_unread_failure()
            .map(|notice| notice.text.lines().next().unwrap_or_default().to_owned());
        let (rig_name, rig_dim) = self.shell.rig.headline();
        let mut palette_stat = Stat {
            id: "studio-palette",
            mark: None,
            name: "",
            dim: "",
            progress: None,
            search: true,
            key: true,
            max_width: 200.0,
        };
        let mut activity_stat = Stat {
            id: "studio-activity",
            mark: Some(activity_mark),
            name: &activity_name,
            dim: &activity_dim,
            progress,
            search: false,
            key: false,
            max_width: 340.0,
        };
        let mut failure_stat = failure.as_deref().map(|text| Stat {
            id: "studio-failure",
            mark: Some(Mark::Failed),
            name: text,
            dim: "",
            progress: None,
            search: false,
            key: false,
            max_width: 300.0,
        });
        let mut rig_stat = Stat {
            id: "studio-rig",
            mark: Some(rig_status::lamp_mark(self.shell.rig.lamp())),
            name: &rig_name,
            dim: &rig_dim,
            progress: None,
            search: false,
            key: false,
            max_width: 260.0,
        };
        fit_right_cluster(
            ui,
            budget,
            running == 0,
            &mut palette_stat,
            &mut activity_stat,
            &mut failure_stat,
            &mut rig_stat,
        );
        let palette = self.stat(ui, &t, right, height, palette_stat);
        let palette = palette.on_hover_text("Go to anything · Ctrl K");
        if palette.clicked() {
            egui::Popup::close_all(&ctx);
            self.shell.palette.open();
        }
        right = palette.rect.left();
        let activity = self.stat(ui, &t, right, height, activity_stat);
        let activity = if running == 0 {
            activity
        } else {
            activity.on_hover_text(format!("{activity_name}  {activity_dim}").trim().to_owned())
        };
        right = activity.rect.left();
        let failure_response = failure_stat.map(|stat| self.stat(ui, &t, right, height, stat));
        if let Some(response) = &failure_response {
            right = response.rect.left();
        }
        let rig_response = self.stat(ui, &t, right, height, rig_stat);
        let rig_response = rig_response.on_hover_text(format!("{rig_name}  {rig_dim}"));
        let right_edge = rig_response.rect.left();
        self.shell.rig_popup = Some(egui::Popup::default_response_id(&rig_response));
        self.shell.tray_popup = Some(egui::Popup::default_response_id(&activity));
        // Popovers: only one is open at a time.
        let popover = |response: &egui::Response| {
            egui::Popup::from_toggle_button_response(response)
                .align(egui::RectAlign::BOTTOM_END)
                .gap(0.0)
                .close_behavior(egui::PopupCloseBehavior::CloseOnClickOutside)
                .frame(popover_frame(&t))
        };
        let mut rig_action = None;
        popover(&rig_response).show(|ui| {
            rig_action = rig_status::popover(ui, &self.shell.rig);
        });
        if let Some(action) = rig_action {
            self.rig_action(&ctx, action);
        }
        let tray_target = failure_response
            .as_ref()
            .filter(|r| r.clicked())
            .map(|r| r.id);
        if tray_target.is_some() {
            egui::Popup::open_id(&ctx, egui::Popup::default_response_id(&activity));
        }
        let mut tray_action = None;
        let status = self.status.clone();
        let quiet = self.shell.prefs.quiet;
        let quiet_holds = quiet && self.activity_hub.quiet.full_screen();
        let tray = popover(&activity).show(|ui| {
            tray_action = activity_tray::tray(
                ui,
                activity_tray::TrayInputs {
                    activities: &self.activity_hub.activities,
                    notices: &mut self.shell.notices,
                    status: &status,
                    quiet,
                    quiet_holds,
                    now: Instant::now(),
                    unix: crate::workspace_history::timestamp(),
                },
            );
        });
        if tray.is_some() {
            // Opening the tray reads the notices.
            self.shell.notices.mark_all_read();
        }
        if let Some(action) = tray_action {
            egui::Popup::close_all(&ctx);
            match action {
                TrayAction::OpenLog => self.open_drawer_only(Drawer::Activity),
                TrayAction::OpenAgent => self.open_drawer_only(Drawer::Agent),
                TrayAction::Notice(crate::notices::Action::OpenLog) => {
                    self.open_drawer_only(Drawer::Activity)
                }
                TrayAction::Notice(crate::notices::Action::OpenStation(number)) => {
                    if let Some(station) = Station::from_number(number) {
                        self.go_station(station);
                    }
                }
                other => self.activity_action(other),
            }
        }
        // The left: brand, then the breadcrumb.
        let brand = self.brand(ui, &t, bar, height);
        let crumbs_right = self.crumbs(
            ui,
            &t,
            brand.right() + CRUMB_GAP,
            height,
            stations.left() - 12.0,
        );
        // Empty space moves the window; double-click maximises.
        for (index, gap) in [
            egui::Rect::from_min_max(
                egui::pos2(crumbs_right + 8.0, bar.top()),
                egui::pos2(stations.left() - 4.0, bar.top() + height),
            ),
            egui::Rect::from_min_max(
                egui::pos2(stations.right() + 4.0, bar.top()),
                egui::pos2(right_edge - 4.0, bar.top() + height),
            ),
        ]
        .into_iter()
        .enumerate()
        {
            if gap.width() >= 8.0 {
                let mut gap_ui = ui.new_child(
                    egui::UiBuilder::new()
                        .id_salt(("studio-drag", index))
                        .max_rect(gap),
                );
                window_chrome::drag_space(&mut gap_ui, gap, modal);
            }
        }
    }

    fn open_drawer_only(&mut self, drawer: Drawer) {
        if self.shell.navigator.drawer != Some(drawer) {
            self.open_drawer(drawer);
        }
    }

    fn stat(
        &self,
        ui: &mut egui::Ui,
        t: &studio_theme::Tokens,
        right: f32,
        height: f32,
        stat: Stat<'_>,
    ) -> egui::Response {
        let top = ui.max_rect().top();
        let gap = 8.0;
        let layout = stat_layout(ui, &stat);
        let rect = egui::Rect::from_min_max(
            egui::pos2(right - layout.width, top),
            egui::pos2(right, top + height),
        );
        let response = ui.interact(rect, ui.id().with(stat.id), egui::Sense::click());
        let label = if stat.name.is_empty() {
            stat.dim
        } else {
            stat.name
        };
        response.widget_info(|| egui::WidgetInfo::labeled(egui::WidgetType::Button, true, label));
        let painter = ui.painter().with_clip_rect(rect);
        if response.hovered()
            || egui::Popup::is_id_open(ui.ctx(), egui::Popup::default_response_id(&response))
        {
            painter.rect_filled(rect, 0.0, t.raised);
        }
        theme::rule(&painter, rect.left_top(), rect.left_bottom(), t.line);
        let y = rect.center().y;
        let mut x = rect.left() + 14.0;
        if let Some(mark) = stat.mark {
            w::paint_mark(&painter, egui::pos2(x + w::MARK_SLOT * 0.5, y), mark, t);
            x += w::MARK_SLOT + gap;
        }
        if stat.search {
            crate::command_palette::paint_search_at(&painter, egui::pos2(x + 7.5, y), t.ink3);
            x += 15.0 + gap;
            if let Some(key) = &layout.key {
                let cap = egui::Rect::from_min_size(
                    egui::pos2(x, y - 8.0),
                    egui::vec2(key.size().x + 10.0, 16.0),
                );
                painter.rect_stroke(
                    cap,
                    0.0,
                    egui::Stroke::new(1.0_f32, t.line2),
                    egui::StrokeKind::Inside,
                );
                w::paint_galley_at(&painter, x + 5.0, y + 0.5, key, t.ink3);
            }
        }
        if let Some(name) = &layout.name {
            w::paint_galley_at(&painter, x, y, name, t.ink);
            x += name.size().x + gap;
        }
        if let Some(dim) = &layout.dim {
            w::paint_galley_at(&painter, x, y, dim, t.ink3);
        }
        if let Some(fraction) = stat.progress {
            painter.rect_filled(
                egui::Rect::from_min_size(
                    egui::pos2(rect.left(), rect.bottom() - 1.0),
                    egui::vec2(rect.width() * fraction.clamp(0.0, 1.0), 2.0),
                ),
                0.0,
                t.accent,
            );
        }
        if response.has_focus() {
            w::focus_outline(&painter, rect.shrink(3.0), t);
        }
        response.on_hover_cursor(egui::CursorIcon::PointingHand)
    }

    fn brand(
        &mut self,
        ui: &mut egui::Ui,
        t: &studio_theme::Tokens,
        bar: egui::Rect,
        height: f32,
    ) -> egui::Rect {
        let word = ui.painter().layout_job(crate::studio_fonts::tracked(
            "Strehl",
            w::font(ui, Face::Regular, scale::HINT),
            egui::Color32::PLACEHOLDER,
            0.2,
        ));
        let rect = egui::Rect::from_min_size(
            egui::pos2(bar.left() + 14.0, bar.top()),
            egui::vec2((19.0 + 9.0 + word.size().x).ceil(), height),
        );
        let response = ui.interact(rect, ui.id().with("studio-brand"), egui::Sense::click());
        response.widget_info(|| {
            egui::WidgetInfo::labeled(egui::WidgetType::Button, true, "Strehl menu")
        });
        let mark = egui::Rect::from_center_size(
            egui::pos2(rect.left() + 9.5, rect.center().y),
            egui::vec2(19.0, 19.0),
        );
        w::brand_mark(ui.painter(), mark, t);
        w::paint_galley_at(
            ui.painter(),
            mark.right() + 9.0,
            rect.center().y,
            &word,
            t.ink,
        );
        let mut chosen = None;
        egui::Popup::menu(&response)
            .frame(popover_frame(t))
            .show(|ui| {
                ui.set_min_width(220.0);
                for (label, key, command) in [
                    ("Preferences…", None, PaletteCommand::Preferences),
                    (
                        "Command palette",
                        Some("Ctrl K"),
                        PaletteCommand::Station(0),
                    ),
                    ("Focus mode", Some("F"), PaletteCommand::FocusMode),
                    ("Agent", None, PaletteCommand::Agent),
                    ("Activity log", None, PaletteCommand::ActivityLog),
                    ("Project tree", None, PaletteCommand::ProjectTree),
                    ("Reset layout", None, PaletteCommand::ResetLayout),
                ] {
                    let response = ui.add(
                        egui::Button::new(label)
                            .shortcut_text(key.unwrap_or_default())
                            .frame(false),
                    );
                    if response.clicked() {
                        chosen = Some(command);
                    }
                }
                ui.separator();
                ui.label(
                    egui::RichText::new(format!("Strehl {}", env!("CARGO_PKG_VERSION")))
                        .size(scale::SECONDARY)
                        .color(t.ink3),
                );
            });
        if let Some(command) = chosen {
            egui::Popup::close_all(ui.ctx());
            if command == PaletteCommand::Station(0) {
                self.shell.palette.open();
            } else {
                let ctx = ui.ctx().clone();
                self.run_palette_command(&ctx, command);
            }
        }
        rect
    }

    fn crumb_segments(&mut self) -> &[Crumb] {
        let run = self.expected_run.as_ref().map(|run| run.directory.clone());
        let station = self.shell.navigator.station();
        // Capture names what the plan names; the strings are short.
        let capture = (station == Station::Capture).then(|| {
            let (subject, stack) = self.capture.plan_names();
            let phase = match (self.shell.rig.capturing(), self.shell.rig.phase.as_deref()) {
                (true, Some("paused")) => "Paused",
                (true, _) => "Capturing",
                (false, _) => "New stack",
            };
            (subject.to_owned(), stack.to_owned(), phase)
        });
        let version = matches!(station, Station::Develop | Station::Export)
            .then(|| self.version_crumb().map(str::to_owned))
            .flatten();
        let key = CrumbKey {
            catalog: self.shell.catalog_revision(),
            nodes: self.catalog.nodes.len(),
            stack: self.active_stack,
            epoch: self.epoch,
            result: self.result.is_some(),
            run,
            navigation: self.shell.navigator.revision(),
            capture,
            version,
        };
        if self.shell.crumbs.key.as_ref() != Some(&key) {
            let segments = self.build_crumbs(station, &key);
            self.shell.crumbs = CrumbCache {
                key: Some(key),
                segments,
            };
        }
        &self.shell.crumbs.segments
    }

    /// The mockups' breadcrumb: Library / subject / stack / render, then the
    /// version or the room; on Capture the plan's subject and stack, then
    /// "New stack" or "Capturing".
    fn build_crumbs(&self, station: Station, key: &CrumbKey) -> Vec<Crumb> {
        let crumb = |label: &str, target| Crumb {
            label: label.to_owned(),
            target,
        };
        let mut segments = vec![crumb("Library", CrumbTarget::Library)];
        match self.shell.navigator.route() {
            Route::Subject(id) => {
                if let Some(subject) = self.catalog.node(*id) {
                    segments.push(crumb(&subject.name, CrumbTarget::Here));
                }
            }
            _ if station == Station::Library => {}
            _ if station == Station::Capture => {
                if let Some((subject, stack, phase)) = &key.capture {
                    if !subject.is_empty() {
                        let found = self.catalog.nodes.iter().find(|node| {
                            node.kind == crate::workspace_history::NodeKind::Subject
                                && node.name.eq_ignore_ascii_case(subject)
                        });
                        segments.push(crumb(
                            subject,
                            found.map_or(CrumbTarget::Here, |node| CrumbTarget::Subject(node.id)),
                        ));
                    }
                    if *phase != "New stack" && !stack.is_empty() {
                        segments.push(crumb(stack, CrumbTarget::Here));
                    }
                    segments.push(crumb(phase, CrumbTarget::Here));
                }
            }
            _ => {
                if let Some(id) = self.active_stack {
                    // The stack's subject; an older stack outside any
                    // subject shows the folder or collection holding it.
                    let holder = self
                        .catalog
                        .subject_of(id)
                        .or_else(|| self.catalog.node(id).and_then(|node| node.parent))
                        .and_then(|holder| self.catalog.node(holder));
                    if let Some(holder) = holder {
                        segments.push(crumb(
                            &holder.name,
                            if holder.kind == crate::workspace_history::NodeKind::Subject {
                                CrumbTarget::Subject(holder.id)
                            } else {
                                CrumbTarget::Container(holder.id)
                            },
                        ));
                    }
                    if let Some(node) = self.catalog.node(id) {
                        segments.push(crumb(&node.name, CrumbTarget::Stack(id)));
                        if let Some(label) = self.render_label() {
                            segments.push(crumb(&label, CrumbTarget::Render(id)));
                        }
                    }
                } else if self.stack.is_some() || self.result.is_some() {
                    segments.push(crumb(&self.document_name(), CrumbTarget::Here));
                }
                if self.shell.navigator.route().room() == Some(Room::Engine) {
                    segments.push(crumb("Engine room", CrumbTarget::Room));
                } else if let Some(id) = &key.version
                    && let Some(version) = self.catalog.photo_versions.iter().find(|version| {
                        version.id == *id
                            && self.editor.path.as_ref() == Some(&version.owner.output)
                    })
                {
                    segments.push(crumb(&version.name, CrumbTarget::Here));
                }
            }
        }
        segments
    }

    /// The breadcrumb, at most 430 wide; middle segments shorten first.
    fn crumbs(
        &mut self,
        ui: &mut egui::Ui,
        t: &studio_theme::Tokens,
        left: f32,
        height: f32,
        limit: f32,
    ) -> f32 {
        let segments = self.crumb_segments().to_vec();
        let size = scale::CONTROL;
        let font = w::font(ui, Face::Regular, size);
        let separator = w::text_galley(ui, "/", Face::Regular, size);
        let sep_width = separator.size().x + 18.0;
        let widths: Vec<f32> = segments
            .iter()
            .map(|s| w::text_galley(ui, &s.label, Face::Regular, size).size().x)
            .collect();
        let room = CRUMBS_MAX.min(limit - left - 40.0).max(60.0);
        let natural: f32 =
            widths.iter().sum::<f32>() + sep_width * segments.len().saturating_sub(1) as f32;
        let mut allowed = widths.clone();
        if natural > room && segments.len() > 2 {
            let fixed =
                widths[0] + widths[widths.len() - 1] + sep_width * (segments.len() - 1) as f32;
            let middle = (room - fixed).max(24.0 * (segments.len() - 2) as f32);
            let total: f32 = widths[1..widths.len() - 1].iter().sum();
            for (i, width) in allowed
                .iter_mut()
                .enumerate()
                .skip(1)
                .take(segments.len() - 2)
            {
                *width = (widths[i] / total * middle)
                    .floor()
                    .max(24.0)
                    .min(widths[i]);
            }
        }
        let y = ui.max_rect().top() + height * 0.5;
        let mut x = left;
        let mut clicked = None;
        let last = segments.len().saturating_sub(1);
        for (index, segment) in segments.iter().enumerate() {
            if index > 0 {
                w::paint_galley_at(ui.painter(), x + 9.0, y, &separator, t.line2);
                x += sep_width;
            }
            let width = allowed[index];
            let mut job = egui::text::LayoutJob::single_section(
                segment.label.clone(),
                egui::TextFormat {
                    font_id: font.clone(),
                    color: egui::Color32::PLACEHOLDER,
                    ..Default::default()
                },
            );
            job.wrap = egui::text::TextWrapping {
                max_width: width + 0.5,
                max_rows: 1,
                break_anywhere: true,
                overflow_character: Some('…'),
            };
            let galley = ui.painter().layout_job(job);
            let rect = egui::Rect::from_min_size(
                egui::pos2(x, y - 10.0),
                egui::vec2(galley.size().x, 20.0),
            );
            let response = ui
                .interact(
                    rect,
                    ui.id().with(("studio-crumb", index)),
                    egui::Sense::click(),
                )
                .on_hover_text(&segment.label);
            let color = if index == last || response.hovered() {
                t.ink
            } else {
                t.ink3
            };
            w::paint_galley_at(ui.painter(), x, y, &galley, color);
            let mut picked = None;
            match segment.target {
                CrumbTarget::Stack(id) => {
                    egui::Popup::menu(&response)
                        .frame(popover_frame(t))
                        .show(|ui| {
                            picked = self.sibling_menu(ui, id);
                        });
                }
                CrumbTarget::Render(id) => {
                    egui::Popup::menu(&response)
                        .frame(popover_frame(t))
                        .show(|ui| {
                            picked = self.render_menu(ui, id);
                        });
                }
                _ => {
                    if response.clicked() {
                        picked = Some(PaletteCommandOrCrumb::Crumb(segment.target));
                    }
                }
            }
            if picked.is_some() {
                clicked = picked;
            }
            x += galley.size().x;
        }
        match clicked {
            Some(PaletteCommandOrCrumb::Command(command)) => {
                egui::Popup::close_all(ui.ctx());
                let ctx = ui.ctx().clone();
                self.run_palette_command(&ctx, command);
            }
            Some(PaletteCommandOrCrumb::Crumb(target)) => match target {
                CrumbTarget::Library => {
                    self.navigate(Route::Library(super::studio_route::LibraryView::All))
                }
                CrumbTarget::Container(id) => {
                    self.catalog.selected = Some(id);
                    self.navigate(Route::Library(super::studio_route::LibraryView::All));
                }
                CrumbTarget::Room => self.set_room(Room::Photograph),
                CrumbTarget::Subject(id) => self.navigate(Route::Subject(id)),
                CrumbTarget::Stack(_) | CrumbTarget::Render(_) | CrumbTarget::Here => {}
            },
            None => {}
        }
        x
    }

    fn sibling_menu(
        &self,
        ui: &mut egui::Ui,
        id: crate::workspace_history::NodeId,
    ) -> Option<PaletteCommandOrCrumb> {
        let parent = self.catalog.node(id).and_then(|n| n.parent);
        let mut chosen = None;
        ui.set_min_width(220.0);
        for node in self
            .catalog
            .nodes
            .iter()
            .filter(|n| n.parent == parent && n.kind == crate::workspace_history::NodeKind::Stack)
            .take(40)
        {
            if ui
                .add(egui::Button::selectable(node.id == id, &node.name))
                .clicked()
                && node.id != id
            {
                chosen = Some(PaletteCommandOrCrumb::Command(PaletteCommand::OpenStack(
                    node.id,
                )));
            }
        }
        chosen
    }

    fn render_menu(
        &self,
        ui: &mut egui::Ui,
        id: crate::workspace_history::NodeId,
    ) -> Option<PaletteCommandOrCrumb> {
        let node = self.catalog.node(id)?;
        let current = self.expected_run.as_ref().map(|r| r.directory.as_path());
        let mut chosen = None;
        ui.set_min_width(220.0);
        for (index, directory) in node.revisions.iter().enumerate().rev().take(40) {
            let label = self
                .catalog
                .runs
                .iter()
                .find(|run| run.directory == *directory)
                .map_or_else(
                    || format!("Render {}", index + 1),
                    |run| format!("Render {} · {}", index + 1, run.status),
                );
            if ui
                .add(egui::Button::selectable(
                    Some(directory.as_path()) == current,
                    label,
                ))
                .clicked()
                && Some(directory.as_path()) != current
            {
                chosen = Some(PaletteCommandOrCrumb::Command(PaletteCommand::OpenRun(
                    directory.clone(),
                )));
            }
        }
        chosen
    }

    /// Each lifecycle station's state mark; the open station shows none.
    fn station_mark(&self, station: Station) -> Mark {
        if station == self.shell.navigator.station() || !station.has_state() {
            return Mark::Hidden;
        }
        let document = self.stack.is_some() || self.expected_run.is_some() || self.result.is_some();
        let rendered = self.result.is_some() && self.progress.stage == Stage::Complete;
        match station {
            Station::Capture if self.shell.rig.capturing() => Mark::Running,
            Station::Capture if document => Mark::Fine,
            Station::Stack if self.job.is_some() => Mark::Running,
            Station::Stack if self.progress.stage == Stage::Failed => Mark::Failed,
            Station::Stack if rendered => Mark::Fine,
            Station::Stack if self.stack.is_some() => Mark::NotYet,
            Station::Develop | Station::Export if rendered => {
                let output = self.result.as_deref();
                let versions: Vec<&str> = self
                    .catalog
                    .photo_versions
                    .iter()
                    .filter(|v| Some(v.owner.output.as_path()) == output)
                    .map(|v| v.id.as_str())
                    .collect();
                let done = if station == Station::Develop {
                    !versions.is_empty()
                } else {
                    self.catalog
                        .photo_exports
                        .iter()
                        .any(|e| versions.contains(&e.version.as_str()))
                };
                if done { Mark::Fine } else { Mark::NotYet }
            }
            _ => Mark::Hidden,
        }
    }

    /// `01 Library | 02 Capture 03 Stack 04 Develop 05 Export`, centred.
    /// Every lifecycle station reserves its mark's slot, so labels never move.
    fn stations(
        &mut self,
        ui: &mut egui::Ui,
        t: &studio_theme::Tokens,
        bar: egui::Rect,
        height: f32,
    ) -> egui::Rect {
        let current = self.shell.navigator.station();
        let size = scale::STATION;
        let items: Vec<_> = Station::ALL
            .into_iter()
            .map(|station| {
                let number = ui.painter().layout_job(crate::studio_fonts::tracked(
                    &format!("{:02}", station.number()),
                    w::font(ui, Face::Regular, size),
                    egui::Color32::PLACEHOLDER,
                    0.06,
                ));
                let label = ui.painter().layout_job(crate::studio_fonts::tracked(
                    station.label(),
                    w::font(ui, Face::Regular, size),
                    egui::Color32::PLACEHOLDER,
                    0.14,
                ));
                let width = 11.0
                    + number.size().x
                    + 7.0
                    + label.size().x
                    + if station.has_state() {
                        7.0 + w::MARK_SLOT
                    } else {
                        0.0
                    }
                    + 11.0;
                (station, number, label, width.ceil())
            })
            .collect();
        let rule = 17.0;
        let total: f32 = items.iter().map(|i| i.3).sum::<f32>() + rule;
        let left = (bar.center().x - total * 0.5).round();
        let mut x = left;
        let mut chosen = None;
        for (station, number, label, width) in &items {
            let rect =
                egui::Rect::from_min_size(egui::pos2(x, bar.top()), egui::vec2(*width, height));
            let response = ui.interact(
                rect,
                ui.id().with(("studio-station", station.number())),
                egui::Sense::click(),
            );
            response.widget_info(|| {
                egui::WidgetInfo::selected(
                    egui::WidgetType::SelectableLabel,
                    true,
                    *station == current,
                    station.label(),
                )
            });
            let selected = *station == current && self.shell.navigator.drawer.is_none();
            let (ink, number_ink) = if *station == current {
                (t.ink, t.accent)
            } else if response.hovered() {
                (t.ink2, t.ink3)
            } else {
                (t.ink3, t.ink3)
            };
            let y = rect.center().y;
            let painter = ui.painter();
            w::paint_galley_at(painter, x + 11.0, y, number, number_ink);
            let label_x = x + 11.0 + number.size().x + 7.0;
            w::paint_galley_at(painter, label_x, y, label, ink);
            if station.has_state() {
                let mark = self.station_mark(*station);
                w::paint_mark(
                    painter,
                    egui::pos2(label_x + label.size().x + 7.0 + w::MARK_SLOT * 0.5, y),
                    mark,
                    t,
                );
            }
            if selected {
                painter.rect_filled(
                    egui::Rect::from_min_max(
                        egui::pos2(rect.left() + 11.0, bar.bottom() - 2.0),
                        egui::pos2(rect.right() - 11.0, bar.bottom()),
                    ),
                    0.0,
                    t.accent,
                );
            }
            if response.has_focus() {
                w::focus_outline(painter, rect.shrink(4.0), t);
            }
            if response
                .on_hover_text(format!(
                    "{} · {}",
                    station.label(),
                    station_purpose(*station)
                ))
                .on_hover_cursor(egui::CursorIcon::PointingHand)
                .clicked()
            {
                chosen = Some(*station);
            }
            x += width;
            if *station == Station::Library {
                theme::rule(
                    ui.painter(),
                    egui::pos2(x + 8.0, bar.top() + 13.0),
                    egui::pos2(x + 8.0, bar.top() + height - 13.0),
                    t.line,
                );
                x += rule;
            }
        }
        if let Some(station) = chosen {
            self.go_station(station);
        }
        egui::Rect::from_min_size(egui::pos2(left, bar.top()), egui::vec2(total, height))
    }

    // ----- hint bar ----------------------------------------------------------

    fn hint_bar(&mut self, ui: &mut egui::Ui) {
        let t = studio_theme::tokens(ui.ctx());
        let bar = ui.max_rect();
        theme::rule(ui.painter(), bar.left_top(), bar.right_top(), t.line);
        let row = egui::Rect::from_min_max(
            egui::pos2(bar.left() + 14.0, bar.top() + 1.0),
            egui::pos2(bar.right() - 14.0, bar.bottom()),
        );
        let mut strip = ui.new_child(
            egui::UiBuilder::new()
                .max_rect(row)
                .layout(egui::Layout::left_to_right(egui::Align::Center)),
        );
        let ui = &mut strip;
        ui.spacing_mut().item_spacing = egui::vec2(6.0, 0.0);
        if self.shell.navigator.station() == Station::Capture {
            self.capture_hints(ui);
            return;
        }
        let route = self.shell.navigator.route();
        let tip = tip(route);
        for (keys, text) in hints(route) {
            for key in *keys {
                w::key_cap(ui, key);
            }
            ui.label(egui::RichText::new(*text).size(scale::HINT).color(t.ink3));
            ui.add_space(12.0);
        }
        ui.with_layout(egui::Layout::right_to_left(egui::Align::Center), |ui| {
            ui.spacing_mut().item_spacing = egui::vec2(4.0, 0.0);
            for redo in [true, false] {
                let enabled = self.can_undo_edit(redo);
                let label = self.undo_label(redo);
                if history_command(ui, redo, enabled, &label).clicked() {
                    self.undo_edit(redo);
                }
            }
            if self.can_undo_edit(false) {
                let label = self.undo_label(false);
                let next = label.strip_prefix("Undo ").unwrap_or(&label);
                ui.label(
                    egui::RichText::new(format!("Undo: {next}"))
                        .size(scale::HINT)
                        .color(t.ink3),
                );
            }
            ui.add_space(12.0);
            if let Some(tip) = tip {
                ui.label(egui::RichText::new(tip).size(scale::HINT).color(t.ink3));
            }
            for (fact, strong) in self.photo_facts().into_iter().rev() {
                ui.label(
                    egui::RichText::new(fact)
                        .size(scale::HINT)
                        .color(if strong { t.ink2 } else { t.ink3 }),
                );
            }
        });
    }

    /// The open render's facts for the hint bar: size, master and display.
    fn photo_facts(&self) -> Vec<(String, bool)> {
        let mut facts = Vec::new();
        if let Some(photo) = self
            .editor
            .loaded
            .as_ref()
            .filter(|_| self.editor.path == self.result)
        {
            facts.push((
                format!("{} × {}", photo.image.width, photo.image.height),
                false,
            ));
            let linear = photo.image.origin == strehl_edit::ImageOrigin::SceneLinear;
            facts.push((
                (if linear {
                    "linear master"
                } else {
                    "display master"
                })
                .to_owned(),
                false,
            ));
            if let Some(presenter) = &self.editor.viewport.presenter {
                let hdr = presenter.status().active && linear;
                facts.push((
                    (if hdr { "HDR display" } else { "SDR display" }).to_owned(),
                    true,
                ));
            }
        }
        if self.recorded {
            facts.push(("Recorded".to_owned(), false));
        }
        let mut separated = Vec::with_capacity(facts.len() * 2);
        for (index, fact) in facts.into_iter().enumerate() {
            if index > 0 {
                separated.push(("·".to_owned(), false));
            }
            separated.push(fact);
        }
        separated
    }

    // ----- popover actions ---------------------------------------------------

    fn rig_action(&mut self, ctx: &egui::Context, action: RigAction) {
        match action {
            RigAction::Connect => {
                self.capture.activate(ctx);
                self.shell.rig_read_now();
            }
            RigAction::OpenCapture => {
                egui::Popup::close_all(ctx);
                self.go_station(Station::Capture);
            }
            RigAction::Command(command) => {
                // Shutting the camera down or disconnecting it asks first.
                if self.capture_needs_confirm(&command.command()) {
                    egui::Popup::close_all(ctx);
                    return;
                }
                let snapshot = self.capture.snapshot();
                let result = rig_status::request(&snapshot, command.command())
                    .and_then(|request| self.capture.submit(request));
                if let Err(error) = result {
                    self.capture.error = Some(format!("{error:#}"));
                }
                self.shell.rig_read_now();
            }
        }
    }

    // ----- palette -----------------------------------------------------------

    fn palette_entries(&self) -> Vec<Entry> {
        use crate::workspace_icons::Icon;
        let mut entries = vec![
            Entry::new(
                Group::Actions,
                "Stack these photos",
                PaletteCommand::StartStack,
            )
            .key("Ctrl Enter")
            .icon(Icon::Stack),
            Entry::new(Group::Actions, "Stop stacking", PaletteCommand::StopStack),
            Entry::new(Group::Actions, "Engine room", PaletteCommand::EngineRoom)
                .key("E")
                .icon(Icon::Review),
            Entry::new(Group::Actions, "Focus mode", PaletteCommand::FocusMode).key("F"),
            Entry::new(
                Group::Actions,
                "Open source photos…",
                PaletteCommand::OpenSources,
            )
            .key("Ctrl O")
            .icon(Icon::Folder),
            Entry::new(Group::Actions, "Undo", PaletteCommand::Undo).key("Ctrl Z"),
            Entry::new(Group::Actions, "Redo", PaletteCommand::Redo).key("Ctrl Shift Z"),
            Entry::new(Group::Actions, "Rig status", PaletteCommand::Rig).icon(Icon::Camera),
            Entry::new(Group::Actions, "Agent", PaletteCommand::Agent).icon(Icon::Agent),
            Entry::new(Group::Actions, "Activity log", PaletteCommand::ActivityLog)
                .icon(Icon::Activity),
            Entry::new(Group::Actions, "Project tree", PaletteCommand::ProjectTree)
                .icon(Icon::Folder),
            Entry::new(Group::Actions, "Preferences…", PaletteCommand::Preferences)
                .icon(Icon::Adjust),
            Entry::new(Group::Actions, "Reset layout", PaletteCommand::ResetLayout)
                .icon(Icon::Layout),
        ];
        for theme in ThemeName::ALL {
            entries.push(Entry::new(
                Group::Actions,
                format!("Theme: {}", theme.label()),
                PaletteCommand::Theme(theme),
            ));
        }
        for station in Station::ALL {
            let icon = match station {
                Station::Library => Icon::Projects,
                Station::Capture => Icon::Camera,
                Station::Stack => Icon::Stack,
                Station::Develop => Icon::Edit,
                Station::Export => Icon::Export,
            };
            entries.push(
                Entry::new(
                    Group::GoTo,
                    station.label(),
                    PaletteCommand::Station(station.number()),
                )
                .detail(station_purpose(station))
                .icon(icon),
            );
        }
        let path_of = |id: crate::workspace_history::NodeId| {
            let mut names = Vec::new();
            let mut parent = self.catalog.node(id).and_then(|n| n.parent);
            while let Some(node) = parent.and_then(|p| self.catalog.node(p)) {
                names.push(node.name.as_str());
                parent = node.parent;
                if names.len() > 8 {
                    break;
                }
            }
            names.reverse();
            names.join(" / ")
        };
        for node in &self.catalog.nodes {
            match node.kind {
                crate::workspace_history::NodeKind::Stack => {
                    let entry =
                        Entry::new(Group::GoTo, &node.name, PaletteCommand::OpenStack(node.id))
                            .icon(Icon::Stack);
                    let path = path_of(node.id);
                    entries.push(if path.is_empty() {
                        entry
                    } else {
                        entry.detail(path)
                    });
                    for (index, directory) in node.revisions.iter().enumerate() {
                        entries.push(
                            Entry::new(
                                Group::GoTo,
                                format!("{} · Render {}", node.name, index + 1),
                                PaletteCommand::OpenRun(directory.clone()),
                            )
                            .icon(Icon::Photograph),
                        );
                    }
                }
                _ => entries.push(
                    Entry::new(Group::GoTo, &node.name, PaletteCommand::Reveal(node.id))
                        .detail("Library")
                        .icon(Icon::Folder),
                ),
            }
        }
        entries
    }

    pub(super) fn run_palette_command(&mut self, ctx: &egui::Context, command: PaletteCommand) {
        match command {
            PaletteCommand::Station(number) => {
                if let Some(station) = Station::from_number(number) {
                    self.go_station(station);
                }
            }
            PaletteCommand::EngineRoom => self.set_room(Room::Engine),
            PaletteCommand::FocusMode => {
                self.shell.focus = !self.shell.focus;
            }
            PaletteCommand::StartStack => {
                self.start_render();
                if self.job.is_some() {
                    self.go_station(Station::Stack);
                }
            }
            PaletteCommand::StopStack => self.stop_stack(),
            PaletteCommand::Undo => {
                self.undo_edit(false);
            }
            PaletteCommand::Redo => {
                self.undo_edit(true);
            }
            PaletteCommand::OpenSources => {
                if self.job.is_none() && !self.picker_active() {
                    self.capture_parent = self.catalog.selected_container();
                    self.pick(Dialog::Source);
                }
            }
            PaletteCommand::Preferences => self.shell.preferences_open = true,
            PaletteCommand::Theme(theme) => {
                self.shell.prefs.theme = theme;
                self.shell.prefs_dirty = true;
            }
            PaletteCommand::Agent => self.open_drawer_only(Drawer::Agent),
            PaletteCommand::ActivityLog => self.open_drawer_only(Drawer::Activity),
            PaletteCommand::ProjectTree => self.open_project_tree(),
            PaletteCommand::Rig => {
                if self.shell.focus {
                    self.shell.focus = false;
                }
                egui::Popup::open_id(
                    ctx,
                    self.shell
                        .rig_popup
                        .unwrap_or_else(|| egui::Id::new("studio-rig-popup")),
                );
            }
            PaletteCommand::ResetLayout => self.reset_layout(),
            PaletteCommand::OpenStack(id) => {
                if self.job.is_none() && !self.picker_active() {
                    self.open_project_stack(id);
                    self.navigate(Route::for_station(
                        Station::Stack,
                        Some(id),
                        self.result.clone(),
                    ));
                }
            }
            PaletteCommand::OpenRun(directory) => {
                if let Some(run) = self
                    .catalog
                    .runs
                    .iter()
                    .find(|r| r.directory == directory)
                    .cloned()
                    && self.job.is_none()
                    && !self.picker_active()
                {
                    self.reopen_run(run);
                    self.navigate(Route::for_station(
                        Station::Stack,
                        self.active_stack,
                        self.result.clone(),
                    ));
                }
            }
            PaletteCommand::Reveal(id) => {
                self.catalog.selected = Some(id);
                self.go_station(Station::Library);
            }
        }
    }

    // ----- Preferences -------------------------------------------------------

    fn preferences_window(&mut self, ctx: &egui::Context) {
        let mut open = true;
        let mut prefs = self.shell.prefs;
        egui::Window::new("Preferences")
            .id(egui::Id::new("studio-preferences"))
            .open(&mut open)
            .collapsible(false)
            .resizable(false)
            .default_width(360.0)
            .anchor(egui::Align2::CENTER_TOP, egui::vec2(0.0, 120.0))
            .show(ctx, |ui| {
                ui.set_width(380.0);
                ui.set_max_width(380.0);
                ui.spacing_mut().item_spacing = egui::vec2(10.0, 10.0);
                w::section(ui, "Appearance", |_| {});
                ui.horizontal(|ui| {
                    ui.label("Theme");
                    ui.with_layout(egui::Layout::right_to_left(egui::Align::Center), |ui| {
                        w::segmented(
                            ui,
                            "preferences-theme",
                            &mut prefs.theme,
                            &ThemeName::ALL.map(|theme| (theme, theme.label())),
                        );
                    });
                });
                ui.horizontal(|ui| {
                    ui.label("Surround");
                    ui.with_layout(egui::Layout::right_to_left(egui::Align::Center), |ui| {
                        w::segmented(
                            ui,
                            "preferences-surround",
                            &mut prefs.surround,
                            &studio_theme::Surround::ALL.map(|s| (s, s.label())),
                        );
                    });
                });
                w::toggle_row(ui, "Reduced motion", &mut prefs.reduced_motion);
                w::section(ui, "Activity", |_| {});
                w::toggle_row(
                    ui,
                    "Quiet: hold stacks while a full-screen program is in front",
                    &mut prefs.quiet,
                );
                ui.add(
                    egui::Label::new(
                        egui::RichText::new(
                            "The surround is the canvas around the photograph. Views not yet \
                             redrawn for Studio 2 keep the Graphite palette on Lightbox.",
                        )
                        .size(scale::SECONDARY)
                        .color(studio_theme::tokens(ui.ctx()).ink3),
                    )
                    .wrap(),
                );
            });
        if prefs != self.shell.prefs {
            self.shell.prefs = prefs;
            self.shell.prefs_dirty = true;
        }
        self.shell.preferences_open = open;
    }
}

/// What the palette may run this frame, captured once so its rows can be
/// checked without borrowing the app.
struct PaletteAvailability {
    can_start: bool,
    running: bool,
    can_undo: bool,
    can_redo: bool,
    can_open: bool,
}
impl PaletteAvailability {
    fn of(app: &StrehlApp) -> Self {
        Self {
            can_start: app.stack_start_blocker().is_none(),
            running: app.job.is_some(),
            can_undo: app.can_undo_edit(false),
            can_redo: app.can_undo_edit(true),
            can_open: app.job.is_none() && !app.picker_active(),
        }
    }
    fn allows(&self, command: &PaletteCommand) -> bool {
        match command {
            PaletteCommand::StartStack => self.can_start,
            PaletteCommand::StopStack => self.running,
            PaletteCommand::Undo => self.can_undo,
            PaletteCommand::Redo => self.can_redo,
            PaletteCommand::OpenSources
            | PaletteCommand::OpenStack(_)
            | PaletteCommand::OpenRun(_) => self.can_open,
            _ => true,
        }
    }
}

enum PaletteCommandOrCrumb {
    Command(PaletteCommand),
    Crumb(CrumbTarget),
}

fn station_purpose(station: Station) -> &'static str {
    match station {
        Station::Library => "projects, stacks and saved renders",
        Station::Capture => "camera, light, focus bounds and the RAW receiver",
        Station::Stack => "the photograph, its recipe and its evidence",
        Station::Develop => "finishing the photograph",
        Station::Export => "files for the web, print and archive",
    }
}

/// A standing reassurance at the right of the hint bar (the mockups).
fn tip(route: &Route) -> Option<&'static str> {
    match route {
        Route::Library(_) => Some("Reorganising the library never moves your source photographs"),
        Route::Subject(_) => Some(
            "Scale comes from the lens data recorded in the RAW; correct it once per lens if needed",
        ),
        _ => None,
    }
}

/// The keys that apply on each station (appendix C), for the hint bar.
fn hints(route: &Route) -> &'static [(&'static [&'static str], &'static str)] {
    match route.station() {
        _ if matches!(route, Route::Subject(_)) => &[
            (&["Enter"], "open the stack"),
            (&["N"], "new stack of this subject"),
        ],
        Station::Library => &[
            (&["Ctrl", "K"], "go to anything"),
            (&["Enter"], "open"),
            (&["F2"], "rename"),
            (&["Drop"], "folders here to make subjects"),
        ],
        Station::Capture => &[(&["Ctrl", "K"], "go to anything"), (&["F"], "focus")],
        Station::Stack => &[
            (&["Ctrl", "Enter"], "stack again"),
            (&["E"], "engine room"),
            (&["F"], "focus"),
            (&["Ctrl", "K"], "go to anything"),
        ],
        Station::Develop => &[
            (&["B"], "depth brush"),
            (&["[", "]"], "brush size"),
            (&["\\"], "before and after"),
            (&["Ctrl", "Z"], "undo"),
            (&["F"], "focus"),
        ],
        Station::Export => &[
            (&["Ctrl", "E"], "export the ticked presets"),
            (&["F"], "focus"),
            (&["Ctrl", "K"], "go to anything"),
        ],
    }
}

/// The square, hairline popover frame with its shadow.
pub(super) fn popover_frame(t: &studio_theme::Tokens) -> egui::Frame {
    egui::Frame::new()
        .fill(t.panel)
        .stroke(egui::Stroke::new(1.0_f32, t.line2))
        .inner_margin(0)
        .shadow(egui::epaint::Shadow {
            offset: [0, 10],
            blur: 30,
            spread: 0,
            color: t.shadow,
        })
}

/// A small undo or redo arrow, as on today's status bar.
fn history_command(ui: &mut egui::Ui, redo: bool, enabled: bool, label: &str) -> egui::Response {
    let t = studio_theme::tokens(ui.ctx());
    let (rect, response) = ui.allocate_exact_size(
        egui::vec2(22.0, 19.0),
        if enabled {
            egui::Sense::click()
        } else {
            egui::Sense::hover()
        },
    );
    response.widget_info(|| egui::WidgetInfo::labeled(egui::WidgetType::Button, enabled, label));
    let p = ui.painter_at(rect);
    if enabled && response.hovered() {
        p.rect_filled(rect, 0.0, t.raised);
    }
    let color = if enabled {
        t.ink2
    } else {
        t.ink3.gamma_multiply(0.5)
    };
    let c = rect.center();
    let flip = if redo { -1.0 } else { 1.0 };
    let point = |x: f32, y: f32| c + egui::vec2(x * flip, y);
    let stroke = Stroke::new(1.0 / ui.ctx().pixels_per_point(), color);
    p.add(egui::Shape::line(
        vec![
            point(-5.0, -3.0),
            point(2.0, -3.0),
            point(5.0, 0.0),
            point(5.0, 4.0),
        ],
        stroke,
    ));
    p.add(egui::Shape::line(
        vec![point(-1.0, -6.0), point(-5.0, -3.0), point(-1.0, 0.0)],
        stroke,
    ));
    response.on_hover_text(format!(
        "{label} · {}",
        if redo {
            "Ctrl+Shift+Z / Ctrl+Y"
        } else {
            "Ctrl+Z"
        }
    ))
}
