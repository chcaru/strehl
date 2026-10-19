//! A read-only, visual bracket library. Directory enumeration and embedded
//! camera JPEG decoding are bounded background work, never UI-thread I/O.

use std::collections::{BTreeMap, BTreeSet};
use std::fs;
use std::path::{Path, PathBuf};
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::mpsc::TryRecvError;
use std::time::Duration;

use anyhow::{Context, Result, ensure};
use eframe::egui::{self, Align2, Color32, FontId, Rect, Sense, Stroke, TextureHandle};

use crate::jobs::{Task, spawn_task};
use crate::source_preview::{FilmstripBatch, load_filmstrip_batch};
use crate::theme;

const MAX_ENTRIES: usize = 24_000;
const MAX_FOLDERS: usize = 512;
const MAX_COVERS: usize = 48;
const COVER_SIDE: u32 = 320;
const MAX_HISTORY: usize = 32;

/// History remembers navigation, never cached filesystem observations or pixels.
#[derive(Clone)]
struct Visit {
    path: PathBuf,
    selected: Option<PathBuf>,
    scroll: f32,
}

#[derive(Clone, Debug, Default)]
struct Contents {
    frames: usize,
    samples: Vec<PathBuf>,
    limited: bool,
}

#[derive(Clone, Debug)]
struct Folder {
    path: PathBuf,
    name: String,
    link: bool,
    contents: Option<std::result::Result<Contents, String>>,
}

#[derive(Debug)]
struct Directory {
    path: PathBuf,
    contents: Contents,
    folders: Vec<Folder>,
}

#[derive(Clone, Debug)]
enum ScanKind {
    Directory(PathBuf),
    Child(PathBuf),
}

struct ScanWork {
    epoch: u64,
    kind: ScanKind,
    task: Task<Directory>,
}

struct CoverWork {
    epoch: u64,
    paths: Vec<PathBuf>,
    task: Task<FilmstripBatch>,
}

struct Cover {
    texture: Option<TextureHandle>,
    arrived: f64,
}

#[derive(Default)]
pub(crate) struct BracketBrowser {
    active: bool,
    epoch: u64,
    path: PathBuf,
    path_text: String,
    directory: Option<Directory>,
    selected: Option<PathBuf>,
    error: Option<String>,
    scan: Option<ScanWork>,
    covers_work: Option<CoverWork>,
    covers: BTreeMap<PathBuf, Cover>,
    visible: Vec<PathBuf>,
    displayed_epoch: Option<u64>,
    recent: Vec<PathBuf>,
    roots: Vec<PathBuf>,
    roots_work: Option<Task<Vec<PathBuf>>>,
    back: Vec<Visit>,
    forward: Vec<Visit>,
    gallery_scroll: f32,
    restore_scroll: Option<f32>,
    scroll_to_focus: Option<PathBuf>,
}

impl BracketBrowser {
    pub(crate) fn active(&self) -> bool {
        self.active
    }

    /// True once the modal's current visible content has been painted and its
    /// actual covers have finished arriving/revealing. Offscreen folders need
    /// not be scanned merely to take a representative screenshot.
    pub(crate) fn settled(&self, now: f64) -> bool {
        if !self.active {
            return true;
        }
        if self.displayed_epoch != Some(self.epoch) || self.roots_work.is_some() {
            return false;
        }
        if self.error.is_some() {
            return true;
        }
        let Some(directory) = &self.directory else {
            return false;
        };
        if self.selected.iter().chain(self.visible.iter()).any(|path| {
            directory
                .folders
                .iter()
                .any(|folder| &folder.path == path && !folder.link && folder.contents.is_none())
        }) {
            return false;
        }
        let wanted = self.wanted_covers();
        if self.covers_work.as_ref().is_some_and(|work| {
            work.epoch == self.epoch && work.paths.iter().any(|path| wanted.contains(path))
        }) {
            return false;
        }
        wanted.iter().all(|path| {
            self.covers
                .get(path)
                .is_some_and(|cover| cover.texture.is_none() || now >= cover.arrived + 0.18)
        })
    }

    pub(crate) fn open(&mut self, path: Option<PathBuf>) {
        self.active = true;
        let path = path
            .or_else(|| (!self.path.as_os_str().is_empty()).then(|| self.path.clone()))
            .unwrap_or_else(home_directory);
        self.back.clear();
        self.forward.clear();
        self.load_visit(Visit {
            path,
            selected: None,
            scroll: 0.0,
        });
        if self.roots_work.is_none() && self.roots.is_empty() {
            self.roots_work = Some(spawn_task("strehl-browser-drives", move |cancelled| {
                let mut roots = Vec::new();
                #[cfg(windows)]
                for letter in b'A'..=b'Z' {
                    ensure!(!cancelled.load(Ordering::Relaxed), "Drive lookup cancelled");
                    let path = PathBuf::from(format!("{}:\\", char::from(letter)));
                    if path.is_dir() {
                        roots.push(path);
                    }
                }
                #[cfg(not(windows))]
                {
                    let _ = cancelled;
                    roots.push(PathBuf::from("/"));
                }
                Ok(roots)
            }));
        }
    }

    fn navigate(&mut self, path: PathBuf) {
        if self.path != path && !self.path.as_os_str().is_empty() {
            let current = self.visit();
            Self::remember(&mut self.back, current);
            self.forward.clear();
        }
        self.load_visit(Visit {
            path,
            selected: None,
            scroll: 0.0,
        });
    }

    fn visit(&self) -> Visit {
        Visit {
            path: self.path.clone(),
            selected: self.selected.clone(),
            scroll: self.gallery_scroll,
        }
    }

    fn remember(history: &mut Vec<Visit>, visit: Visit) {
        if history.len() == MAX_HISTORY {
            history.remove(0);
        }
        history.push(visit);
    }

    fn traverse(&mut self, backward: bool) {
        let destination = if backward {
            self.back.pop()
        } else {
            self.forward.pop()
        };
        if let Some(destination) = destination {
            let current = self.visit();
            Self::remember(
                if backward {
                    &mut self.forward
                } else {
                    &mut self.back
                },
                current,
            );
            self.load_visit(destination);
        }
    }

    fn load_visit(&mut self, visit: Visit) {
        self.epoch = self.epoch.wrapping_add(1);
        self.path_text = display_path(&visit.path);
        self.path = visit.path;
        self.directory = None;
        self.selected = visit.selected;
        self.gallery_scroll = visit.scroll;
        self.restore_scroll = Some(visit.scroll);
        self.scroll_to_focus = None;
        self.error = None;
        self.covers.clear();
        self.visible.clear();
        self.displayed_epoch = None;
        // Keep the two worker slots until they finish. Rapid navigation can
        // invalidate results but cannot create unbounded decoder/scan threads.
    }

    fn close(&mut self) {
        self.active = false;
        self.epoch = self.epoch.wrapping_add(1);
        self.covers.clear();
        self.visible.clear();
    }

    /// Must be called every application frame, even while closed, so the
    /// bounded worker slots can retire without holding decoded pixel buffers.
    pub(crate) fn show(&mut self, ctx: &egui::Context) -> Option<PathBuf> {
        self.poll(ctx);
        if !self.active {
            if self.scan.is_some() || self.covers_work.is_some() || self.roots_work.is_some() {
                ctx.request_repaint_after(Duration::from_millis(30));
            }
            return None;
        }
        let screen = ctx.content_rect();
        let safe = Rect::from_min_max(
            screen.min + egui::vec2(crate::window_chrome::RAIL_WIDTH + 16.0, 12.0),
            screen.max - egui::vec2(16.0, 16.0),
        );
        let frame = egui::Frame::new()
            .inner_margin(8)
            .fill(theme::PANEL)
            .stroke(Stroke::new(1.0_f32, theme::LINE));
        let available = safe.size() - frame.total_margin().sum();
        let width = available.x.clamp(1.0, 1120.0);
        let height = available.y.clamp(1.0, 730.0);
        let mut navigate = None;
        let mut open = None;
        let mut cancel = false;
        let mut history = None;
        self.visible.clear();
        let modal_id = egui::Id::new("visual-bracket-browser");
        let modal = egui::Modal::new(modal_id)
            .area(egui::Modal::default_area(modal_id).constrain_to(safe))
            .frame(frame)
            .show(ctx, |ui| {
                let (back, forward, up, location, open_key) = ui.input_mut(|input| {
                    (
                        input.consume_key(egui::Modifiers::ALT, egui::Key::ArrowLeft),
                        input.consume_key(egui::Modifiers::ALT, egui::Key::ArrowRight),
                        input.consume_key(egui::Modifiers::ALT, egui::Key::ArrowUp),
                        input.consume_key(egui::Modifiers::CTRL, egui::Key::L),
                        input.consume_key(egui::Modifiers::CTRL, egui::Key::Enter),
                    )
                });
                if back {
                    history = Some(true);
                }
                if forward {
                    history = Some(false);
                }
                if up {
                    navigate = self.path.parent().map(Path::to_path_buf);
                }
                if back || forward || up {
                    // egui also plans spatial focus movement before widgets run.
                    // A handled history shortcut must not move focus again later.
                    ui.memory_mut(|memory| memory.move_focus(egui::FocusDirection::None));
                }
                // The content aperture is exact. Each section owns its rectangle;
                // a tall separator or long Places list cannot grow the modal back
                // into the native title controls or push Open below the window.
                let (bounds, _) = ui.allocate_exact_size(egui::vec2(width, height), Sense::hover());
                let mut header = Rect::from_min_size(bounds.min, egui::vec2(width, 32.0));
                let window_dock = crate::window_chrome::dock_rect(ctx.viewport_rect());
                if header.intersects(window_dock.expand(8.0)) {
                    // Keep the local chooser actions beside the native dock.
                    // Only this header gives up the corner: the location row
                    // and gallery retain the entire available modal width.
                    header.max.x = header
                        .right()
                        .min(window_dock.left() - 8.0)
                        .max(header.left() + 1.0);
                }
                let path_row = Rect::from_min_size(
                    bounds.min + egui::vec2(0.0, 42.0),
                    egui::vec2(width, 28.0),
                );
                let body = Rect::from_min_max(
                    bounds.min + egui::vec2(0.0, 82.0),
                    bounds.max - egui::vec2(0.0, 52.0),
                );
                let footer = Rect::from_min_max(
                    egui::pos2(bounds.left(), bounds.bottom() - 36.0),
                    bounds.max - egui::vec2(0.0, 4.0),
                );
                let mut header_ui = browser_section(ui, header, "header");
                header_ui.horizontal(|ui| {
                    ui.label(
                        egui::RichText::new("Choose a bracket")
                            .size(20.0)
                            .color(theme::INK),
                    );
                    ui.with_layout(egui::Layout::right_to_left(egui::Align::Center), |ui| {
                        cancel = ui.button("Close").clicked();
                        theme::caption(ui, "CAMERA LIBRARY");
                    });
                });
                let mut path_ui = browser_section(ui, path_row, "path");
                path_ui.horizontal(|ui| {
                    if ui
                        .add_enabled(!self.back.is_empty(), egui::Button::new("←"))
                        .on_hover_text("Back · Alt+Left")
                        .clicked()
                    {
                        history = Some(true);
                    }
                    if ui
                        .add_enabled(!self.forward.is_empty(), egui::Button::new("→"))
                        .on_hover_text("Forward · Alt+Right")
                        .clicked()
                    {
                        history = Some(false);
                    }
                    if ui
                        .add_enabled(self.path.parent().is_some(), egui::Button::new("↑ Up"))
                        .on_hover_text("Parent folder · Alt+Up")
                        .clicked()
                    {
                        navigate = self.path.parent().map(Path::to_path_buf);
                    }
                    let response = ui
                        .add(
                            egui::TextEdit::singleline(&mut self.path_text)
                                .id_salt("bracket-location")
                                .desired_width((ui.available_width() - 44.0).max(1.0))
                                .hint_text("Folder path"),
                        )
                        .on_hover_text("Folder location · Ctrl+L to edit · Enter to browse");
                    if location {
                        response.request_focus();
                        if let Some(mut state) = egui::TextEdit::load_state(ui.ctx(), response.id) {
                            state
                                .cursor
                                .set_char_range(Some(egui::text::CCursorRange::two(
                                    egui::text::CCursor::new(0),
                                    egui::text::CCursor::new(self.path_text.chars().count()),
                                )));
                            state.store(ui.ctx(), response.id);
                        }
                    }
                    if (response.lost_focus() && ui.input(|i| i.key_pressed(egui::Key::Enter)))
                        || ui.button("Go").clicked()
                    {
                        let text = self.path_text.trim().trim_matches('"');
                        if !text.is_empty() {
                            navigate = Some(PathBuf::from(text));
                        }
                    }
                });
                let places =
                    Rect::from_min_max(body.min, egui::pos2(body.left() + 136.0, body.bottom()));
                let gallery = Rect::from_min_max(body.min + egui::vec2(160.0, 0.0), body.max);
                let mut places_ui = browser_section(ui, places, "places");
                egui::ScrollArea::vertical()
                    .id_salt("bracket-places")
                    .max_height(places.height())
                    .auto_shrink([false, false])
                    .show(&mut places_ui, |ui| {
                        theme::caption(ui, "PLACES");
                        if place(ui, "Home").clicked() {
                            navigate = Some(home_directory());
                        }
                        if place(ui, "Pictures").clicked() {
                            navigate = Some(home_directory().join("Pictures"));
                        }
                        ui.add_space(14.0);
                        theme::caption(ui, "DRIVES");
                        for root in &self.roots {
                            if place(ui, &display_path(root)).clicked() {
                                navigate = Some(root.clone());
                            }
                        }
                        ui.add_space(14.0);
                        if !self.recent.is_empty() {
                            theme::caption(ui, "RECENT BRACKETS");
                        }
                        for path in &self.recent {
                            let name = folder_name(path);
                            if place(ui, &name).on_hover_text(display_path(path)).clicked() {
                                navigate = Some(path.clone());
                            }
                        }
                    });
                ui.painter().line_segment(
                    [
                        egui::pos2(body.left() + 146.0, body.top()),
                        egui::pos2(body.left() + 146.0, body.bottom()),
                    ],
                    Stroke::new(1.0_f32, theme::LINE),
                );
                let mut gallery_ui = browser_section(ui, gallery, "gallery");
                self.gallery(&mut gallery_ui, body.height(), &mut navigate);
                ui.painter().line_segment(
                    [
                        egui::pos2(bounds.left(), bounds.bottom() - 44.0),
                        egui::pos2(bounds.right(), bounds.bottom() - 44.0),
                    ],
                    Stroke::new(1.0_f32, theme::LINE),
                );
                let mut footer_ui = browser_section(ui, footer, "footer");
                footer_ui.horizontal(|ui| {
                    let selected = self.selection();
                    let can_open = selected
                        .as_ref()
                        .is_some_and(|(_, c)| c.frames > 0 && !c.limited);
                    let label = selected.as_ref().map_or_else(
                        || "Choose a folder to inspect".to_owned(),
                        |(path, c)| {
                            format!(
                                "{}  ·  {} camera frames{}",
                                folder_name(path),
                                c.frames,
                                if c.limited {
                                    " · scan limit reached"
                                } else {
                                    ""
                                }
                            )
                        },
                    );
                    ui.with_layout(egui::Layout::right_to_left(egui::Align::Center), |ui| {
                        let clicked = ui
                            .add_enabled(
                                can_open,
                                egui::Button::new(
                                    egui::RichText::new("Use these photos").color(theme::INK),
                                )
                                .fill(theme::PANEL)
                                .stroke(Stroke::new(1.0_f32, theme::ACCENT))
                                .min_size(egui::vec2(144.0, 32.0)),
                            )
                            .on_hover_text("Review these photos in the workspace, then choose Stack · Ctrl+Enter")
                            .clicked();
                        if can_open && (clicked || open_key) {
                            open = selected.map(|(path, _)| path.clone());
                        }
                        // Reserve the action before the flexible folder label;
                        // a long capture name must never push Open offscreen.
                        ui.add(
                            egui::Label::new(egui::RichText::new(label).color(theme::MUTED))
                                .truncate(),
                        );
                    });
                });
            });
        if modal.should_close() || cancel {
            self.close();
        } else if let Some(path) = open {
            self.recent.retain(|old| old != &path);
            self.recent.insert(0, path.clone());
            self.recent.truncate(6);
            self.close();
            return Some(path);
        } else if let Some(backward) = history {
            self.traverse(backward);
        } else if let Some(path) = navigate {
            self.navigate(path);
        }
        self.schedule();
        if self.scan.is_some() || self.covers_work.is_some() || self.roots_work.is_some() {
            ctx.request_repaint_after(Duration::from_millis(30));
        }
        None
    }

    fn gallery(&mut self, ui: &mut egui::Ui, height: f32, navigate: &mut Option<PathBuf>) {
        if let Some(error) = &self.error {
            if ui.is_rect_visible(ui.max_rect()) {
                self.displayed_epoch = Some(self.epoch);
            }
            ui.colored_label(theme::AMBER, error);
            if ui.button("Retry folder").clicked() {
                *navigate = Some(self.path.clone());
            }
            return;
        }
        let Some(directory) = &self.directory else {
            ui.horizontal(|ui| {
                ui.spinner();
                theme::caption(ui, "Reading folders and camera frames…");
            });
            return;
        };
        let columns = ((ui.available_width() / 220.0).floor() as usize).clamp(1, 4);
        let card_width =
            (ui.available_width() - (columns - 1) as f32 * 10.0 - 10.0) / columns as f32;
        // Clone metadata only, never pixels. Stable ordering and fixed cell
        // geometry prevent asynchronous counts/covers from moving targets.
        let mut entries = Vec::new();
        if directory.contents.frames > 0 {
            entries.push(Folder {
                path: directory.path.clone(),
                name: "This folder".into(),
                link: false,
                contents: Some(Ok(directory.contents.clone())),
            });
        }
        entries.extend(directory.folders.clone());
        let limited = directory.contents.limited || directory.folders.len() == MAX_FOLDERS;
        theme::caption(
            ui,
            "Click / Space selects · Double-click / Enter explores · Ctrl+Enter opens",
        );
        let gallery_id = ui.id().with("bracket-cards");
        let focused = ui.memory(|memory| memory.focused());
        if let Some(index) = entries
            .iter()
            .position(|folder| Some(gallery_id.with(&folder.path)) == focused)
        {
            let destination = ui.input_mut(|input| {
                let keys = [
                    (egui::Key::ArrowLeft, index.saturating_sub(1)),
                    (egui::Key::ArrowRight, (index + 1).min(entries.len() - 1)),
                    (egui::Key::ArrowUp, index.saturating_sub(columns)),
                    (
                        egui::Key::ArrowDown,
                        (index + columns).min(entries.len() - 1),
                    ),
                    (egui::Key::Home, 0),
                    (egui::Key::End, entries.len() - 1),
                ];
                keys.into_iter().find_map(|(key, target)| {
                    input
                        .consume_key(egui::Modifiers::NONE, key)
                        .then_some(target)
                })
            });
            if let Some(target) = destination {
                let path = &entries[target].path;
                ui.memory_mut(|memory| {
                    memory.move_focus(egui::FocusDirection::None);
                    memory.request_focus(gallery_id.with(path));
                });
                self.scroll_to_focus = Some(path.clone());
            }
        }
        ui.add_space(6.0);
        let mut scroll = egui::ScrollArea::vertical()
            .id_salt(("bracket-gallery", self.epoch))
            .max_height(height - 30.0)
            .auto_shrink([false, false]);
        if let Some(offset) = self.restore_scroll.take() {
            scroll = scroll.vertical_scroll_offset(offset);
        }
        let output = scroll.show(ui, |ui| {
                for row in entries.chunks(columns) {
                    ui.horizontal_top(|ui| {
                        for folder in row {
                            let (rect, _) = ui.allocate_exact_size(egui::vec2(card_width, 173.0), Sense::hover());
                            let response = ui.interact(rect, gallery_id.with(&folder.path), Sense::click());
                            if self.scroll_to_focus.as_ref() == Some(&folder.path) {
                                ui.scroll_to_rect(rect, Some(egui::Align::Center));
                                self.scroll_to_focus = None;
                            }
                            response.widget_info(|| egui::WidgetInfo::labeled(
                                egui::WidgetType::Button,
                                true,
                                format!("Folder {}", folder.name),
                            ));
                            let selected = self.selected.as_ref().unwrap_or(&self.path) == &folder.path;
                            if ui.is_rect_visible(rect) {
                                self.visible.push(folder.path.clone());
                                self.card(ui, rect, folder, selected, response.hovered(), response.has_focus());
                            }
                            let enter = response.has_focus() && ui.input_mut(|input| input.consume_key(egui::Modifiers::NONE, egui::Key::Enter));
                            let space = response.has_focus() && ui.input_mut(|input| input.consume_key(egui::Modifiers::NONE, egui::Key::Space));
                            if response.double_clicked() || enter {
                                // The current folder is already being explored. Its
                                // own cover must not blink away on Enter/double-click.
                                if folder.path != self.path { *navigate = Some(folder.path.clone()); }
                            } else if space || response.clicked() {
                                response.request_focus();
                                self.selected = Some(folder.path.clone());
                                // Links are not probed by mere visibility. Explicit
                                // entry is required before following their target.
                                if folder.link && !space { *navigate = Some(folder.path.clone()); }
                            }
                            response.on_hover_text(format!("{}\nArrows move focus · Space selects\nEnter explores · Ctrl+Enter opens selected bracket", display_path(&folder.path)));
                        }
                    });
                    ui.add_space(5.0);
                }
                if entries.is_empty() { theme::caption(ui, "No folders or .ARW frames here. Choose another location."); }
                if limited { ui.colored_label(theme::AMBER, "Large directory: showing a bounded scan. Enter a narrower folder to open a bracket."); }
            });
        self.gallery_scroll = output.state.offset.y;
        // The first modal pass can be an invisible sizing pass. Only a real
        // visible paint establishes which child scans/covers a screenshot needs.
        if ui.is_rect_visible(ui.max_rect()) && (entries.is_empty() || !self.visible.is_empty()) {
            self.displayed_epoch = Some(self.epoch);
        }
    }

    fn card(
        &self,
        ui: &egui::Ui,
        rect: Rect,
        folder: &Folder,
        selected: bool,
        hovered: bool,
        focused: bool,
    ) {
        let p = ui.painter();
        p.rect_filled(
            rect,
            0.0,
            if selected {
                theme::RAISED
            } else {
                theme::PANEL
            },
        );
        p.rect_stroke(
            rect,
            0.0,
            Stroke::new(
                if focused { 2.0_f32 } else { 1.0_f32 },
                if selected || focused {
                    theme::ACCENT
                } else if hovered {
                    theme::MUTED
                } else {
                    theme::LINE
                },
            ),
            egui::StrokeKind::Inside,
        );
        let photo = Rect::from_min_max(
            rect.min + egui::vec2(7.0, 7.0),
            rect.max - egui::vec2(7.0, 49.0),
        );
        p.rect_filled(photo, 0.0, theme::BG);
        let contents = folder
            .contents
            .as_ref()
            .and_then(|result| result.as_ref().ok());
        let samples = contents.map_or(&[][..], |contents| contents.samples.as_slice());
        if samples.is_empty() {
            paint_folder(p, photo.center(), folder.link);
        } else {
            // The focus sweep's midpoint gives the large cover its context;
            // first/last remain visible as insets. This is presentation order,
            // never a reordering or sharpness ranking of the actual bracket.
            let middle = samples.len() / 2;
            let presentation =
                std::iter::once(middle).chain((0..samples.len()).filter(|&index| index != middle));
            for (index, sample) in presentation.enumerate() {
                let path = &samples[sample];
                let cell = if index == 0 {
                    photo
                } else {
                    let size = egui::vec2(photo.width() * 0.29, photo.height() * 0.37);
                    Rect::from_min_size(
                        egui::pos2(
                            photo.right() - size.x - 4.0,
                            photo.bottom() - (samples.len() - index) as f32 * (size.y + 4.0),
                        ),
                        size,
                    )
                };
                if index > 0 {
                    p.rect_filled(cell.expand(2.0), 0.0, theme::BG);
                }
                if let Some(cover) = self.covers.get(path) {
                    if let Some(texture) = &cover.texture {
                        let elapsed = (ui.input(|i| i.time) - cover.arrived).max(0.0);
                        let alpha = (elapsed / 0.18).min(1.0) as f32;
                        p.image(
                            texture.id(),
                            cell,
                            crop_uv(texture.size_vec2(), cell.size()),
                            Color32::WHITE.gamma_multiply(alpha),
                        );
                        if alpha < 1.0 {
                            ui.ctx().request_repaint();
                        }
                    } else {
                        p.text(
                            cell.center(),
                            Align2::CENTER_CENTER,
                            "—",
                            FontId::proportional(14.0),
                            theme::MUTED,
                        );
                    }
                }
            }
        }
        let name_rect = Rect::from_min_max(
            egui::pos2(rect.left() + 10.0, rect.bottom() - 42.0),
            egui::pos2(rect.right() - 8.0, rect.bottom() - 20.0),
        );
        let mut name = egui::text::LayoutJob::simple(
            folder.name.clone(),
            FontId::proportional(12.0),
            theme::INK,
            name_rect.width(),
        );
        name.wrap.max_rows = 1;
        name.wrap.break_anywhere = true;
        let galley = p.layout_job(name);
        p.with_clip_rect(name_rect)
            .galley(name_rect.min, galley, theme::INK);
        let detail = match &folder.contents {
            Some(Ok(c)) if c.frames > 0 => format!(
                "{}{} FRAMES  ·  CAMERA JPEG",
                c.frames,
                if c.limited { "+" } else { "" }
            ),
            Some(Ok(_)) => "FOLDER  ·  ENTER TO EXPLORE".into(),
            Some(Err(_)) => "UNAVAILABLE  ·  ENTER TO RETRY".into(),
            None if folder.link => "LINK  ·  ENTER TO EXPLORE".into(),
            None => "READING CONTENTS…".into(),
        };
        p.with_clip_rect(Rect::from_min_max(
            egui::pos2(rect.left() + 8.0, rect.bottom() - 20.0),
            rect.right_bottom() - egui::vec2(8.0, 2.0),
        ))
        .text(
            egui::pos2(rect.left() + 10.0, rect.bottom() - 11.0),
            Align2::LEFT_CENTER,
            detail,
            FontId::monospace(8.0),
            if selected {
                theme::ACCENT
            } else {
                theme::MUTED
            },
        );
    }

    fn selection(&self) -> Option<(&PathBuf, &Contents)> {
        let directory = self.directory.as_ref()?;
        match self.selected.as_ref() {
            None => Some((&directory.path, &directory.contents)),
            Some(path) if path == &directory.path => Some((&directory.path, &directory.contents)),
            Some(path) => directory
                .folders
                .iter()
                .find(|folder| &folder.path == path)
                .and_then(|folder| {
                    folder
                        .contents
                        .as_ref()?
                        .as_ref()
                        .ok()
                        .map(|contents| (&folder.path, contents))
                }),
        }
    }

    fn poll(&mut self, ctx: &egui::Context) {
        if let Some(work) = &self.roots_work {
            match work.receiver.try_recv() {
                Ok(result) => {
                    self.roots = result.unwrap_or_default();
                    self.roots_work = None;
                }
                Err(TryRecvError::Disconnected) => self.roots_work = None,
                Err(TryRecvError::Empty) => {}
            }
        }
        let scan_result = self
            .scan
            .as_ref()
            .and_then(|work| match work.task.receiver.try_recv() {
                Ok(result) => Some(result),
                Err(TryRecvError::Disconnected) => Some(Err("Folder worker stopped".into())),
                Err(TryRecvError::Empty) => None,
            });
        if let Some(result) = scan_result {
            let work = self.scan.take().expect("scan received");
            if self.active && work.epoch == self.epoch {
                match work.kind {
                    ScanKind::Directory(_) => match result {
                        Ok(directory) => {
                            self.path = directory.path.clone();
                            self.path_text = display_path(&self.path);
                            self.directory = Some(directory);
                        }
                        Err(error) => self.error = Some(error),
                    },
                    ScanKind::Child(path) => {
                        if let Some(folder) = self.directory.as_mut().and_then(|directory| {
                            directory
                                .folders
                                .iter_mut()
                                .find(|folder| folder.path == path)
                        }) {
                            folder.contents = Some(result.map(|directory| directory.contents));
                        }
                    }
                }
            }
        }
        let cover_result =
            self.covers_work
                .as_ref()
                .and_then(|work| match work.task.receiver.try_recv() {
                    Ok(result) => Some(result),
                    Err(TryRecvError::Disconnected) => Some(Err("Preview worker stopped".into())),
                    Err(TryRecvError::Empty) => None,
                });
        if let Some(result) = cover_result {
            let work = self.covers_work.take().expect("covers received");
            if self.active && work.epoch == self.epoch {
                let mut images: BTreeMap<_, _> = result.unwrap_or_default().into_iter().collect();
                for (index, path) in work.paths.into_iter().enumerate() {
                    let texture = images
                        .remove(&index)
                        .and_then(|image| image.ok())
                        .map(|image| {
                            ctx.load_texture(
                                format!("bracket-cover-{}-{}", self.epoch, path.display()),
                                egui::ColorImage::from_rgba_unmultiplied(
                                    image.image.size,
                                    &image.image.rgba,
                                ),
                                egui::TextureOptions::LINEAR,
                            )
                        });
                    self.covers.insert(
                        path,
                        Cover {
                            texture,
                            arrived: ctx.input(|i| i.time),
                        },
                    );
                }
            }
        }
    }

    fn schedule(&mut self) {
        if !self.active {
            return;
        }
        if self.scan.is_none() {
            let kind = if self.directory.is_none() && self.error.is_none() {
                Some(ScanKind::Directory(self.path.clone()))
            } else {
                self.directory.as_ref().and_then(|directory| {
                    self.selected
                        .iter()
                        .chain(self.visible.iter())
                        .find_map(|path| {
                            directory
                                .folders
                                .iter()
                                .find(|folder| {
                                    &folder.path == path
                                        && !folder.link
                                        && folder.contents.is_none()
                                })
                                .map(|folder| ScanKind::Child(folder.path.clone()))
                        })
                })
            };
            if let Some(kind) = kind {
                let (path, children) = match &kind {
                    ScanKind::Directory(path) => (path.clone(), true),
                    ScanKind::Child(path) => (path.clone(), false),
                };
                self.scan = Some(ScanWork {
                    epoch: self.epoch,
                    kind,
                    task: spawn_task("strehl-bracket-directory", move |cancelled| {
                        read_directory(&path, children, &cancelled)
                    }),
                });
            }
        }
        let wanted = self.wanted_covers();
        self.covers.retain(|path, _| wanted.contains(path));
        if self.covers_work.is_none() {
            let paths: Vec<_> = wanted
                .into_iter()
                .filter(|path| !self.covers.contains_key(path))
                .take(6)
                .collect();
            if !paths.is_empty() {
                let requests = paths.iter().cloned().enumerate().collect();
                self.covers_work = Some(CoverWork {
                    epoch: self.epoch,
                    paths,
                    task: load_filmstrip_batch(requests, COVER_SIDE),
                });
            }
        }
    }

    fn wanted_covers(&self) -> BTreeSet<PathBuf> {
        let mut wanted = BTreeSet::new();
        // Before first paint, seed the current/selected bracket. Thereafter
        // cover memory belongs to visible cells; an offscreen selection only
        // needs its count for the footer, not invisible camera JPEGs.
        if self.visible.is_empty()
            && let Some((_, contents)) = self.selection()
        {
            wanted.extend(contents.samples.iter().cloned());
        }
        if let Some(directory) = &self.directory {
            for path in &self.visible {
                let contents = if path == &directory.path {
                    Some(&directory.contents)
                } else {
                    directory
                        .folders
                        .iter()
                        .find(|folder| &folder.path == path)
                        .and_then(|folder| folder.contents.as_ref()?.as_ref().ok())
                };
                if let Some(contents) = contents {
                    wanted.extend(contents.samples.iter().cloned());
                }
            }
        }
        wanted.into_iter().take(MAX_COVERS).collect()
    }
}

fn read_directory(path: &Path, children: bool, cancelled: &AtomicBool) -> Result<Directory> {
    let path = fs::canonicalize(path).with_context(|| format!("Opening {}", path.display()))?;
    let entries = fs::read_dir(&path).with_context(|| format!("Reading {}", path.display()))?;
    let mut frames = Vec::new();
    let mut folders = Vec::new();
    let mut limited = false;
    for (index, entry) in entries.enumerate() {
        ensure!(!cancelled.load(Ordering::Relaxed), "Folder scan cancelled");
        if index >= MAX_ENTRIES {
            limited = true;
            break;
        }
        let entry = entry.context("Reading a directory entry")?;
        let kind = entry.file_type().context("Reading an entry type")?;
        let entry_path = entry.path();
        // A link/reparse point is shown as a place, never followed while probing
        // the gallery. Opening that card is the user's explicit traversal.
        let link = kind.is_symlink() || is_reparse_point(&entry);
        if children && (kind.is_dir() || link) {
            if folders.len() < MAX_FOLDERS {
                folders.push(Folder {
                    name: entry.file_name().to_string_lossy().into_owned(),
                    path: entry_path,
                    link,
                    contents: None,
                });
            } else {
                limited = true;
            }
        } else if !link
            && kind.is_file()
            && entry_path
                .extension()
                .is_some_and(|extension| extension.eq_ignore_ascii_case("arw"))
        {
            frames.push(entry_path);
        }
    }
    frames.sort();
    folders.sort_by(|a, b| {
        a.name
            .to_lowercase()
            .cmp(&b.name.to_lowercase())
            .then(a.path.cmp(&b.path))
    });
    let mut samples = Vec::new();
    if !frames.is_empty() {
        for index in [0, (frames.len() - 1) / 2, frames.len() - 1] {
            if samples.last() != Some(&frames[index]) {
                samples.push(frames[index].clone());
            }
        }
    }
    Ok(Directory {
        path,
        contents: Contents {
            frames: frames.len(),
            samples,
            limited,
        },
        folders,
    })
}

fn is_reparse_point(entry: &fs::DirEntry) -> bool {
    #[cfg(windows)]
    {
        use std::os::windows::fs::MetadataExt;
        entry
            .metadata()
            .is_ok_and(|metadata| metadata.file_attributes() & 0x400 != 0)
    }
    #[cfg(not(windows))]
    {
        let _ = entry;
        false
    }
}

fn home_directory() -> PathBuf {
    std::env::var_os("USERPROFILE")
        .or_else(|| std::env::var_os("HOME"))
        .map(PathBuf::from)
        .unwrap_or_else(|| PathBuf::from("."))
}

fn browser_section(ui: &mut egui::Ui, rect: Rect, name: &str) -> egui::Ui {
    let mut section = ui.new_child(
        egui::UiBuilder::new()
            .id_salt(("bracket-section", name))
            .max_rect(rect)
            .layout(egui::Layout::top_down(egui::Align::Min)),
    );
    section.set_clip_rect(ui.clip_rect().intersect(rect));
    section
}

fn place(ui: &mut egui::Ui, label: &str) -> egui::Response {
    let (rect, response) = ui.allocate_exact_size(
        egui::vec2(ui.available_width().clamp(1.0, 136.0), 25.0),
        Sense::click(),
    );
    response.widget_info(|| egui::WidgetInfo::labeled(egui::WidgetType::Button, true, label));
    let p = ui.painter_at(rect);
    if response.hovered() || response.has_focus() {
        p.rect_filled(rect, 0.0, theme::RAISED);
        p.line_segment(
            [rect.left_top(), rect.left_bottom()],
            Stroke::new(1.0_f32, theme::ACCENT),
        );
    }
    let mut text = egui::text::LayoutJob::simple(
        label.to_owned(),
        FontId::monospace(11.0),
        theme::INK,
        rect.width() - 14.0,
    );
    text.wrap.max_rows = 1;
    text.wrap.break_anywhere = true;
    let galley = p.layout_job(text);
    p.galley(
        egui::pos2(rect.left() + 7.0, rect.center().y - galley.size().y * 0.5),
        galley,
        theme::INK,
    );
    response.on_hover_cursor(egui::CursorIcon::PointingHand)
}

fn folder_name(path: &Path) -> String {
    path.file_name()
        .map(|name| name.to_string_lossy().into_owned())
        .unwrap_or_else(|| display_path(path))
}

fn display_path(path: &Path) -> String {
    let text = path.to_string_lossy();
    if let Some(network) = text.strip_prefix(r"\\?\UNC\") {
        format!(r"\\{network}")
    } else {
        text.strip_prefix(r"\\?\").unwrap_or(&text).to_owned()
    }
}

fn crop_uv(image: egui::Vec2, cell: egui::Vec2) -> Rect {
    let scale = (cell.x / image.x).max(cell.y / image.y);
    let size = cell / (image * scale);
    Rect::from_center_size(egui::pos2(0.5, 0.5), size)
}

fn paint_folder(p: &egui::Painter, center: egui::Pos2, link: bool) {
    let origin = center - egui::vec2(19.0, 13.0);
    let points = [
        (0.0, 5.0),
        (0.0, 0.0),
        (14.0, 0.0),
        (20.0, 5.0),
        (38.0, 5.0),
        (38.0, 27.0),
        (0.0, 27.0),
        (0.0, 5.0),
        (38.0, 5.0),
    ]
    .map(|(x, y)| origin + egui::vec2(x, y));
    p.add(egui::Shape::line(
        points.to_vec(),
        Stroke::new(1.3_f32, theme::MUTED),
    ));
    if link {
        let at = origin + egui::vec2(25.0, 17.0);
        let tip = at + egui::vec2(8.0, -8.0);
        p.line_segment([at, tip], Stroke::new(1.3_f32, theme::ACCENT));
        p.line_segment(
            [tip - egui::vec2(6.0, 0.0), tip],
            Stroke::new(1.3_f32, theme::ACCENT),
        );
        p.line_segment(
            [tip + egui::vec2(0.0, 6.0), tip],
            Stroke::new(1.3_f32, theme::ACCENT),
        );
    }
}

#[cfg(test)]
#[path = "bracket-browser-tests.rs"]
mod tests;
