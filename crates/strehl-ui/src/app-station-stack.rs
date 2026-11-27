//! The Stack station (Studio 2, spec 7.2) composed in the shell's frame.
//!
//! Photograph room: the control strip (lens, detail size, hold note, Fit /
//! 100 %, render comparison), the canvas (the finished photograph with the
//! plane lens and the core sample, or the held two-up), the depth rail with
//! its head and filmstrip, and the inspector's Checks, Recipe and Renders.
//! The engine room (`E`) keeps today's process view with its animation; a
//! render that has not finished also shows there, live.
//!
//! Performance: every part caches its own geometry (see each module); this
//! file only routes input and textures. Previews come from `SourceBrowser`
//! through the theater's shared inspection state; nothing here decodes.
use super::studio_route::{Room, StackTab, Station};
use super::studio_shell::StationLayout;
use super::*;
use crate::{
    core_sample::{CoreAction, CoreInput, CorePalette, CoreSample},
    depth_rail::{DepthRail, RailGeometry, RailHead, RailMarkers, RailPalette},
    filmstrip::{FilmMarks, FilmPalette, Filmstrip},
    plane_lens::{LensEvidence, LensPalette, LensPhoto, PlaneLens, PlaneLensView},
    process_admission_regions::RegionSettings,
    studio_theme::{self, Tokens, scale},
    studio_widgets as w,
};
use eframe::egui::{Color32, Pos2, Rect, Stroke};

/// The rail slot: head 30, chart 84, filmstrip 75, plus the top rule.
pub(super) const STACK_RAIL: f32 = 190.0;
const RAIL_HEAD_HEIGHT: f32 = 30.0;
const RAIL_CHART: f32 = 84.0;

#[derive(Clone, Copy, Debug, Default, PartialEq, Eq)]
pub(crate) enum Lens {
    #[default]
    Photograph,
    Plane,
    Depth,
    SoftSpots,
    Alignment,
}
impl Lens {
    const ALL: [(Lens, &'static str); 5] = [
        (Lens::Photograph, "Photograph"),
        (Lens::Plane, "Plane"),
        (Lens::Depth, "Depth"),
        (Lens::SoftSpots, "Soft spots"),
        (Lens::Alignment, "Alignment"),
    ];
    /// Lenses without engine evidence are shown, disabled, never guessed.
    fn available(self) -> bool {
        matches!(self, Lens::Photograph | Lens::Plane)
    }
}

#[derive(Clone, Copy, Debug, Default, PartialEq, Eq)]
pub(crate) enum StationTab {
    #[default]
    Checks,
    Recipe,
    Renders,
}

/// The station's state, one field on `StrehlApp`.
pub(crate) struct StackStation {
    pub(crate) rail: DepthRail,
    pub(crate) film: Filmstrip,
    pub(crate) core: CoreSample,
    pub(crate) lens: PlaneLens,
    pub(crate) view: PlaneLensView,
    pub(crate) mode: Lens,
    tab: StationTab,
    seen_tab: Option<StackTab>,
    /// The photograph's UV window (Fit is the whole frame).
    pub(crate) aperture: Rect,
    document: Option<(u64, u64)>,
    chart: Option<Rect>,
    canvas: Option<Rect>,
    /// `--plane-hold N` (one-based), applied once the stack's planes are known.
    pub(crate) launch_hold: Option<usize>,
    /// The depth rail Develop shows in its control strip.
    pub(crate) develop_rail: DepthRail,
    /// The core sample's last answer: its peak heads the rail, and a click
    /// inside its pinned popover is not a new pin.
    last_core: crate::core_sample::CoreResponse,
    /// Develop's compact rail: pooled columns per series and width.
    develop_columns: Option<DevelopColumns>,
    develop_anchor: Option<usize>,
    applied_inspection: Option<(Option<usize>, Option<usize>)>,
}
impl Default for StackStation {
    fn default() -> Self {
        Self {
            rail: DepthRail::default(),
            film: Filmstrip::default(),
            core: CoreSample::default(),
            lens: PlaneLens::default(),
            view: PlaneLensView::default(),
            mode: Lens::Photograph,
            tab: StationTab::Checks,
            seen_tab: None,
            aperture: full(),
            document: None,
            chart: None,
            canvas: None,
            launch_hold: None,
            develop_rail: DepthRail::default(),
            last_core: Default::default(),
            develop_columns: None,
            develop_anchor: None,
            applied_inspection: None,
        }
    }
}

fn full() -> Rect {
    Rect::from_min_max(Pos2::ZERO, egui::pos2(1.0, 1.0))
}

/// The photograph centred at its aspect in the canvas, 14 px from the top
/// and 24 px for the scale rule below (appendix B: 128, 94, 1076, 718).
/// Develop's pooled rail columns, keyed by series, planes and width.
type DevelopColumns = ((u64, usize, u32), std::sync::Arc<Vec<Option<f32>>>);

pub(crate) fn photo_rect(canvas: Rect, aspect: f32) -> Rect {
    let height = (canvas.height() - 38.0).max(40.0);
    let width = (height * aspect).min(canvas.width() - 20.0);
    let height = width / aspect;
    Rect::from_min_size(
        egui::pos2(
            canvas.center().x - width * 0.5,
            canvas.top() + 14.0 + ((canvas.height() - 38.0) - height).max(0.0) * 0.5,
        ),
        egui::vec2(width, height),
    )
}

impl StrehlApp {
    /// True while the photograph room has a finished render to show.
    fn stack_photograph_ready(&self) -> bool {
        self.progress.stage == Stage::Complete
            && self.result.is_some()
            && self.image_path == self.result
            && self.stack_final_texture().is_some()
    }

    fn stack_final_texture(&self) -> Option<egui::TextureHandle> {
        self.editor
            .display_texture()
            .or(self.result_viewer.texture.as_ref())
            .cloned()
    }

    fn stack_planes(&self) -> usize {
        self.progress
            .frames_total
            .or_else(|| self.stack.as_ref().map(|stack| stack.frames.len()))
            .unwrap_or(0)
    }

    fn stack_room(&self) -> Room {
        self.shell.navigator.route().room().unwrap_or_default()
    }

    /// The new station in the photograph room; the engine room and an
    /// unfinished render keep today's process view.
    fn stack_station_view(&self) -> bool {
        self.stack_room() == Room::Photograph && self.stack_photograph_ready()
    }

    // ----- shell arms ------------------------------------------------------

    pub(super) fn stack_layout(&self) -> StationLayout {
        let station = self.stack_station_view();
        StationLayout {
            sidebar: None,
            tools: false,
            inspector: self.stack_room() != Room::Engine,
            control_strip: true,
            rail: station.then_some(STACK_RAIL),
            owns_body: false,
        }
    }

    pub(super) fn stack_paints_legacy(&self) -> bool {
        !self.stack_station_view()
    }

    pub(super) fn stack_canvas(&mut self, ui: &mut egui::Ui) {
        if self.stack.is_none()
            && !self.activity
            && self.expected_run.is_none()
            && self.result.is_none()
        {
            self.welcome_workspace(ui);
        } else if self.stack_station_view() {
            self.process_space.set_instant_inspection(true);
            self.stack_photograph(ui);
            let busy = self.stack_station.view.pending()
                || self.stack_station.core.probe_mut().recounting()
                || self.stack_station.launch_hold.is_some();
            self.process_space.set_station_busy(busy);
            self.reshoot_window(ui.ctx());
        } else {
            self.process_space.set_instant_inspection(false);
            self.show_process(ui);
        }
    }

    // ----- control strip -----------------------------------------------------

    pub(super) fn stack_control_strip(&mut self, ui: &mut egui::Ui) -> bool {
        if !self.stack_station_view() {
            return false;
        }
        let t = studio_theme::tokens(ui.ctx());
        let geometry = self.progress.output_geometry;
        w::caps(ui, "Lens");
        let mut lens = self.stack_station.mode;
        let options: Vec<(Lens, &str)> = Lens::ALL.to_vec();
        let before = lens;
        let response = w::segmented(ui, "stack-lens", &mut lens, &options);
        if lens != before {
            if lens.available() {
                self.set_stack_lens(lens);
            } else {
                // Shown for orientation; its evidence does not exist yet.
                self.stack_station.mode = before;
            }
        }
        response.on_hover_text(
            "Depth, Soft spots and Alignment need engine evidence this render does not have",
        );
        rule(ui, &t);
        w::caps(ui, "Detail size");
        let level = self.stack_station.lens.level();
        for index in 0..plane_lens_levels() {
            let label = crate::plane_lens::size_label(index, geometry);
            let number = label.trim_end_matches(" px").to_owned();
            let galley = w::text_galley(
                ui,
                &number,
                crate::studio_fonts::Face::Regular,
                scale::SECONDARY,
            );
            let size = egui::vec2(galley.size().x.max(14.0) + 12.0, 24.0);
            let (rect, hit) = ui.allocate_exact_size(size, egui::Sense::click());
            let selected = index == level;
            if selected {
                ui.painter().rect_stroke(
                    rect,
                    0.0,
                    Stroke::new(1.0_f32, t.line2),
                    egui::StrokeKind::Inside,
                );
            }
            let ink = if selected || hit.hovered() {
                t.ink
            } else {
                t.ink2
            };
            w::paint_galley_at(
                ui.painter(),
                rect.center().x - galley.size().x * 0.5,
                rect.center().y - 1.0,
                &galley,
                ink,
            );
            let y = rect.bottom() - 5.0;
            ui.painter().line_segment(
                [
                    egui::pos2(rect.center().x - 6.0, y),
                    egui::pos2(rect.center().x + 6.0, y),
                ],
                Stroke::new(1.5_f32, t.spectrum[index]),
            );
            if hit
                .on_hover_text(crate::process_output_space::detail_tooltip(index, geometry))
                .clicked()
            {
                self.stack_station.lens.set_level(index);
            }
        }
        ui.with_layout(egui::Layout::right_to_left(egui::Align::Center), |ui| {
            let renders = self.stack_render_choices();
            if renders.len() > 1 {
                let mut shown = 0;
                let labels: Vec<(usize, String)> = renders
                    .iter()
                    .enumerate()
                    .map(|(i, (label, _))| {
                        (
                            i,
                            if i == 0 {
                                label.clone()
                            } else {
                                format!("vs {label}")
                            },
                        )
                    })
                    .collect();
                let options: Vec<(usize, &str)> =
                    labels.iter().map(|(i, s)| (*i, s.as_str())).collect();
                w::segmented(ui, "stack-compare", &mut shown, &options).on_hover_text(
                    "Compare two renders arrives with the Renders tab's two-up (spec 7.2)",
                );
            }
            let mut fit = self.stack_station.aperture == full();
            let was = fit;
            w::segmented(
                ui,
                "stack-zoom",
                &mut fit,
                &[(true, "Fit"), (false, "100 %")],
            );
            if fit != was {
                self.stack_zoom(fit);
            }
            if self.stack_station.lens.holding() {
                rule(ui, &t);
                w::key_cap(ui, "Esc");
                ui.label(
                    egui::RichText::new("Holding a plane")
                        .size(scale::SECONDARY)
                        .color(t.ink),
                );
            }
        });
        true
    }

    fn set_stack_lens(&mut self, lens: Lens) {
        let station = &mut self.stack_station;
        match lens {
            Lens::Plane => {
                let default = station.core_peak().unwrap_or(station.lens.planes() / 2);
                station.lens.choose_plane_lens(default);
            }
            _ => {
                station.lens.release();
            }
        }
        station.mode = lens;
    }

    /// Fit, or 100 %: one photograph pixel per screen pixel, centred.
    fn stack_zoom(&mut self, fit: bool) {
        let station = &mut self.stack_station;
        if fit {
            station.aperture = full();
            return;
        }
        let (Some(canvas), [width, height]) = (station.canvas, self.result_viewer.source_size)
        else {
            return;
        };
        if width == 0 || height == 0 {
            return;
        }
        let image = photo_rect(canvas, width as f32 / height as f32);
        let size = egui::vec2(
            (image.width() / width as f32).min(1.0),
            (image.height() / height as f32).min(1.0),
        );
        let centre = station.aperture.center();
        station.aperture = clamp_aperture(Rect::from_center_size(centre, size));
    }

    fn stack_render_choices(&self) -> Vec<(String, PathBuf)> {
        let Some(node) = self.active_stack.and_then(|id| self.catalog.node(id)) else {
            return Vec::new();
        };
        let shown = self.expected_run.as_ref().map(|run| run.directory.clone());
        let mut list: Vec<(String, PathBuf)> = node
            .revisions
            .iter()
            .enumerate()
            .map(|(i, dir)| (format!("Render {}", i + 1), dir.clone()))
            .collect();
        if let Some(at) = list.iter().position(|(_, dir)| Some(dir) == shown.as_ref()) {
            let current = list.remove(at);
            list.insert(0, current);
        }
        list.truncate(2);
        list
    }

    // ----- rail --------------------------------------------------------------

    pub(super) fn stack_rail(&mut self, ui: &mut egui::Ui) {
        if !self.stack_station_view() {
            return;
        }
        let t = studio_theme::tokens(ui.ctx());
        let rect = ui.max_rect();
        let head = Rect::from_min_size(
            rect.min + egui::vec2(0.0, 1.0),
            egui::vec2(rect.width(), RAIL_HEAD_HEIGHT),
        );
        let chart = Rect::from_min_size(head.left_bottom(), egui::vec2(rect.width(), RAIL_CHART));
        let film = Rect::from_min_max(chart.left_bottom(), rect.max);
        let planes = self.stack_planes();
        let station = &mut self.stack_station;
        station.chart = Some(chart);
        station.lens.set_planes(planes);
        if let Some(hold) = station.launch_hold.take_if(|_| planes > 0) {
            station.lens.hold(hold.saturating_sub(1).min(planes - 1));
            station.mode = Lens::Plane;
        }
        let level = station.lens.level();
        station.rail.update(
            &self.progress.admission_archive,
            &self.progress.sampled_mask_history,
            planes,
            level,
            crate::depth_rail::evidence_revision(&self.progress),
        );
        station.film.layout(film.width(), planes);
        station.film.update(&self.progress.admission_archive);
        // Textures the browser already published for the frames shown.
        let shown = station.film.planes();
        let epoch = self.epoch;
        let photos: Vec<SourcePhoto> = shown
            .iter()
            .filter_map(|&plane| {
                let texture = self.browser.native_thumbnail(plane)?;
                Some(SourcePhoto {
                    epoch,
                    index: plane,
                    texture: texture.clone(),
                    aperture: [texture.size()[0] as u32, texture.size()[1] as u32],
                })
            })
            .collect();
        let canonical: Vec<SourcePhoto> = shown
            .iter()
            .filter_map(|&plane| self.source_photo(plane))
            .collect();
        let station = &mut self.stack_station;
        station.film.sync(epoch, &photos, &canonical);
        let rail = station
            .rail
            .interact(ui, chart, ui.id().with("stack-depth-rail"));
        let strip = station
            .film
            .interact(ui, film, ui.id().with("stack-filmstrip"));
        let hovered = rail.hovered.or(strip.hovered);
        station.lens.hover(hovered);
        if let Some(plane) = rail.clicked.or(strip.clicked) {
            station.lens.click(plane);
            station.mode = if station.lens.holding() {
                Lens::Plane
            } else {
                Lens::Photograph
            };
        }
        let reading = match (station.lens.hovered(), station.lens.held()) {
            (Some(plane), _) => format!("Plane {} of {planes}", plane + 1),
            (None, Some(_)) => {
                "Holding a plane \u{b7} move along the rail to compare others \u{b7} click to hold another".into()
            }
            (None, None) => {
                "Hover a plane to see where it was kept \u{b7} click to hold it beside the photograph".into()
            }
        };
        let rail_palette = RailPalette::from_tokens(&t);
        crate::depth_rail::paint_head(
            ui.painter(),
            head,
            rail_palette,
            &RailHead {
                planes,
                step: None,
                reading: &reading,
            },
        );
        let head_marker = station.lens.held().or_else(|| station.core_peak());
        station.rail.paint(
            ui.painter(),
            chart,
            rail_palette,
            RailMarkers {
                hover: station.lens.hovered(),
                head: head_marker,
            },
        );
        station.film.paint(
            ui.painter(),
            film,
            FilmPalette::from_tokens(&t),
            FilmMarks {
                pointer: station.lens.hovered(),
                held: station.lens.held(),
            },
        );
        // The browser warms these frames, and requests previews for the
        // plane the lens shows through the theater's inspection state.
        let inspection = station.lens.inspection();
        // Only the lens's own changes: inspection set elsewhere (agent,
        // engine room, tests) is never overwritten by an idle station.
        let changed = station.applied_inspection != Some(inspection);
        station.applied_inspection = Some(inspection);
        self.process_space.set_station_contacts(shown);
        if changed {
            self.process_space
                .set_inspection(inspection.0, inspection.1);
        }
        if hovered.is_some() {
            ui.ctx().set_cursor_icon(egui::CursorIcon::PointingHand);
        }
    }

    // ----- canvas --------------------------------------------------------------

    fn stack_photograph(&mut self, ui: &mut egui::Ui) {
        let ctx = ui.ctx().clone();
        let t = studio_theme::tokens(&ctx);
        let canvas = ui.max_rect();
        let Some(texture) = self.stack_final_texture() else {
            return;
        };
        let [width, height] = self.result_viewer.source_size;
        let aspect = if width > 0 && height > 0 {
            width as f32 / height as f32
        } else {
            texture.aspect_ratio()
        };
        let document = (self.epoch, self.progress.diagnostic_epoch);
        let planes = self.stack_planes();
        let station = &mut self.stack_station;
        if station.document != Some(document) {
            // A different render: a fresh view. The first document keeps a
            // hold applied from `--plane-hold` this frame.
            if station.document.is_some() {
                station.aperture = full();
                station.core.unpin();
                station.lens.release();
            }
            station.document = Some(document);
        }
        station.canvas = Some(canvas);
        let level = station.lens.level();
        let clean = ctx.input(|i| i.key_down(egui::Key::Space)) && !ctx.wants_keyboard_input();
        // Keys: 1-5 lenses; arrows and Escape for the held plane; Escape unpins.
        let (keys, escape) = ctx.input(|i| {
            let mut lens = None;
            for (key, which) in [
                (egui::Key::Num1, Lens::Photograph),
                (egui::Key::Num2, Lens::Plane),
                (egui::Key::Num3, Lens::Depth),
                (egui::Key::Num4, Lens::SoftSpots),
                (egui::Key::Num5, Lens::Alignment),
            ] {
                if i.key_pressed(key) && i.modifiers.is_none() {
                    lens = Some(which);
                }
            }
            (lens, i.key_pressed(egui::Key::Escape))
        });
        if !ctx.wants_keyboard_input() {
            if let Some(lens) = keys.filter(|lens| lens.available()) {
                self.set_stack_lens(lens);
            }
            let station = &mut self.stack_station;
            let holding = station.lens.holding();
            if station.lens.read_keys(ui) && !station.lens.holding() && holding {
                station.mode = Lens::Photograph;
            } else if escape && !holding {
                station.core.unpin();
            }
        }
        let lens_photo = LensPhoto {
            texture: texture.id(),
            uv: full(),
            aspect,
        };
        let analysis = self.progress.analysis_size.or(self.progress.plane_size);
        let progress = &self.progress;
        let shares = |level: usize, plane: usize| progress.plane_share(level, plane);
        let evidence = LensEvidence {
            archive: &self.progress.admission_archive,
            domain: [self.epoch, self.progress.diagnostic_epoch],
            extent: analysis,
            settings: RegionSettings::read(&ctx),
            geometry: self.progress.output_geometry,
        };
        let lens_palette = LensPalette::from_tokens(&t);
        let station = &mut self.stack_station;
        let browser = &self.browser;
        let preview = |plane: usize| -> Option<LensPhoto> {
            let (_, texture, [w, h]) = browser.texture_snapshot(plane)?;
            Some(LensPhoto {
                texture: texture.id(),
                uv: full(),
                aspect: if w > 0 && h > 0 {
                    w as f32 / h as f32
                } else {
                    1.5
                },
            })
        };
        if let Some(plane) = station.lens.shown().filter(|_| station.lens.holding()) {
            // Held: the two-up, then the eight size maps.
            let layout = crate::plane_lens::two_up_layout(canvas, aspect);
            let response = station.view.paint_two_up(
                ui,
                &layout,
                evidence,
                plane,
                level,
                lens_photo,
                preview(plane),
                lens_palette,
            );
            if let Some(level) = response.level {
                station.lens.set_level(level);
            }
            if let Some(share) = shares(level, plane)
                && matches!(share.source, crate::pipeline::ShareSource::Bin { .. })
            {
                ui.painter().text(
                    layout.final_caption.right_center(),
                    egui::Align2::RIGHT_CENTER,
                    "kept share pooled from a bin: approximate",
                    egui::FontId::proportional(scale::SECONDARY),
                    t.warn,
                );
            }
            return;
        }
        let image = photo_rect(canvas, aspect);
        // Ctrl + wheel sizes the core sample's region; plain wheel zooms.
        let resized = station.core.probe_mut().resize(ui, image);
        let response = ui.interact(
            image,
            ui.id().with("stack-photograph"),
            egui::Sense::click_and_drag(),
        );
        if !resized && response.hovered() {
            let (scroll, pointer) = ctx.input(|i| (i.raw_scroll_delta.y, i.pointer.hover_pos()));
            if scroll != 0.0
                && let Some(at) = pointer
            {
                let factor = (scroll * 0.0025).exp();
                let anchor = station.aperture.min
                    + (at - image.min) / image.size() * station.aperture.size();
                let size = (station.aperture.size() / factor).min(egui::vec2(1.0, 1.0));
                let size = size.max(egui::vec2(0.01, 0.01));
                let min =
                    anchor - (anchor - station.aperture.min) * (size / station.aperture.size());
                station.aperture = clamp_aperture(Rect::from_min_size(min, size));
            }
        }
        if response.dragged() && station.aperture != full() {
            let delta = response.drag_delta() / image.size() * station.aperture.size();
            station.aperture = clamp_aperture(station.aperture.translate(-delta));
        }
        if response.double_clicked() {
            station.aperture = full();
        }
        let aperture = station.aperture;
        // The photograph through the same HDR presenter and detail patches
        // as Develop; the overview texture is the fallback.
        let painter = ui.painter_at(canvas);
        let full_size = image.size() / aperture.size();
        let mapping = (
            Rect::from_min_size(image.min - aperture.min.to_vec2() * full_size, full_size),
            image,
        );
        let editor_owns = self.editor.path == self.result && self.editor.loaded.is_some();
        if editor_owns {
            self.editor
                .request_view(&ctx, mapping, self.max_texture_side);
        }
        match self.editor.photo_paint().filter(|_| editor_owns) {
            Some(paint) => paint.paint(&painter.with_clip_rect(image), image, aperture),
            None => {
                painter.image(texture.id(), image, aperture, Color32::WHITE);
            }
        }
        let station = &mut self.stack_station;
        if clean {
            return;
        }
        if let Some(plane) = station.lens.shown() {
            // Peek: the plane's kept region over the dimmed photograph, and
            // its camera preview above the rail.
            let lookup = station.view.region(&ctx, evidence, plane, level);
            PlaneLensView::dim(&painter.with_clip_rect(image), image);
            if let Some(region) = &lookup.region {
                station.view.paint_final_region(
                    &painter.with_clip_rect(image),
                    region,
                    image,
                    aperture,
                    lens_palette,
                );
            }
            if let (Some(chart), Some(card)) = (
                station.chart,
                station
                    .chart
                    .and_then(|chart| crate::plane_lens::peek_rect(canvas, chart, planes, plane)),
            ) {
                let x = RailGeometry::new(chart, planes).map_or(card.center().x, |g| g.x(plane));
                let share = shares(level, plane);
                let floating = ctx.layer_painter(egui::LayerId::new(
                    egui::Order::Foreground,
                    ui.id().with("stack-peek"),
                ));
                station.view.paint_peek(
                    &floating,
                    card,
                    x,
                    plane,
                    share.as_ref().map(|share| share.share),
                    preview(plane),
                    lookup.region.as_ref(),
                    lens_palette,
                );
                if share.as_ref().is_some_and(|share| {
                    matches!(share.source, crate::pipeline::ShareSource::Bin { .. })
                }) {
                    floating.text(
                        card.right_top() + egui::vec2(-8.0, 8.0),
                        egui::Align2::RIGHT_TOP,
                        "approximate: pooled bin",
                        egui::FontId::proportional(scale::HINT),
                        t.warn,
                    );
                }
            }
            if lookup.region.is_none() && !lookup.current {
                ctx.request_repaint();
            }
            return;
        }
        // The core sample: live under the pointer, pinned by a click.
        let Some(analysis) = analysis else {
            return;
        };
        let extent = [width as usize, height as usize];
        let pointer = ctx.input(|i| i.pointer.interact_pos());
        if response.clicked()
            && let Some(at) = pointer
            && station
                .core_popover()
                .is_none_or(|popover| !popover.contains(at))
        {
            station.core.pin(at, image, aperture);
        }
        let core = station.core.show(
            ui,
            CoreInput {
                archive: &self.progress.admission_archive,
                level,
                analysis_extent: analysis,
                extent,
                planes,
                image,
                aperture,
                final_texture: Some(texture.id()),
                geometry: self.progress.output_geometry,
                viewport: canvas,
            },
            &preview,
            CorePalette::from_tokens(&t),
        );
        station.last_core = core.clone();
        let key = station
            .core
            .rail_key(level)
            .filter(|_| core.region.is_some());
        let sample = &station.core;
        station
            .rail
            .set_region(key, || sample.rail_series(level).collect::<Vec<_>>());
        match core.action {
            Some(CoreAction::ShowPlane(plane)) => {
                station.lens.hold(plane);
                station.mode = Lens::Plane;
            }
            Some(CoreAction::Repair(_)) => self.go_station(Station::Develop),
            // Plan R: the planes behind the region, from the leading ones.
            Some(CoreAction::Reshoot(region)) => {
                let first = core.leading.iter().copied().min().unwrap_or(0);
                let last = core.leading.iter().copied().max().unwrap_or(first);
                self.open_reshoot(region, first, last);
            }
            Some(CoreAction::Note(_)) | None => {}
        }
    }

    // ----- footer -----------------------------------------------------------------

    /// Develop this render and Render again; while a stack runs, Stop and a
    /// Queue button that hands this stack to P5's queue instead of a
    /// disabled button.
    pub(super) fn stack_station_footer(&mut self, ui: &mut egui::Ui) {
        let t = studio_theme::tokens(ui.ctx());
        if let Some(job) = &self.job {
            let cancelling = job.is_cancelling();
            if ui
                .add(w::Button::danger("Stop").enabled(!cancelling))
                .on_hover_text("Stop this run; what it has written is kept")
                .clicked()
            {
                self.stop_stack();
            }
            let queueable = self.active_stack.is_some() && !cancelling;
            if ui
                .add(w::Button::new("Queue a render").enabled(queueable))
                .on_hover_text(if queueable {
                    "Stack this again with its saved recipe when the running stack ends"
                } else {
                    "Save this stack in the Library to queue it"
                })
                .clicked()
            {
                self.queue_while_running();
                ui.ctx().request_repaint();
            }
            let label = if cancelling {
                "Stopping\u{2026}"
            } else if self.pending_run.is_some() {
                "Starting\u{2026}"
            } else {
                "Stacking\u{2026}"
            };
            ui.label(
                egui::RichText::new(label)
                    .size(scale::SECONDARY)
                    .color(t.ink3),
            );
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
        if finished
            && ui
                .add(w::Button::primary("Develop this render").chevron())
                .clicked()
        {
            self.go_station(Station::Develop);
        }
        let label = if finished {
            "Render again".to_owned()
        } else if total > 0 {
            format!("Stack {included} photos")
        } else {
            "Stack".into()
        };
        let button = if finished {
            w::Button::new(&label)
        } else {
            w::Button::primary(&label)
        };
        if ui
            .add(button.enabled(blocker.is_none()))
            .on_hover_text(blocker.map_or_else(
                || format!("Stack {included} photos into a new render \u{b7} Ctrl+Enter"),
                str::to_owned,
            ))
            .clicked()
        {
            self.start_render();
            ui.ctx().request_repaint();
        }
    }

    // ----- inspector -------------------------------------------------------------

    pub(super) fn stack_inspector_tabs(&mut self, ui: &mut egui::Ui) -> bool {
        if !self.stack_station_view() {
            return false;
        }
        self.sync_stack_tab();
        let checks = self.stack_checks();
        let looks = checks
            .iter()
            .filter(|check| check.mark == Some(w::Mark::Look))
            .count();
        let renders = self
            .active_stack
            .and_then(|id| self.catalog.node(id))
            .map_or(0, |node| node.revisions.len());
        let badge_checks = (looks > 0).then(|| looks.to_string());
        let renders_label = if renders > 0 {
            format!("Renders \u{b7} {renders}")
        } else {
            "Renders".into()
        };
        for (tab, label, badge) in [
            (
                StationTab::Checks,
                "Checks".to_owned(),
                badge_checks.as_deref(),
            ),
            (StationTab::Recipe, "Recipe".to_owned(), None),
            (StationTab::Renders, renders_label, None),
        ] {
            let selected = self.stack_station.tab == tab;
            if w::tab(ui, &label, selected, badge).clicked() && !selected {
                self.set_stack_tab(tab);
            }
        }
        true
    }

    /// The station's tabs follow the route's Adjust/Review adapter: Recipe is
    /// Adjust, Checks and Renders are Review.
    fn sync_stack_tab(&mut self) {
        let tab = self.shell.navigator.stack_tab;
        if self.stack_station.seen_tab.is_some_and(|seen| seen != tab) {
            self.stack_station.tab = match tab {
                StackTab::Adjust => StationTab::Recipe,
                StackTab::Review => StationTab::Checks,
            };
        }
        self.stack_station.seen_tab = Some(tab);
    }

    fn set_stack_tab(&mut self, tab: StationTab) {
        self.stack_station.tab = tab;
        let route = match tab {
            StationTab::Recipe => StackTab::Adjust,
            StationTab::Checks | StationTab::Renders => StackTab::Review,
        };
        self.shell.navigator.set_stack_tab(route);
        self.stack_station.seen_tab = Some(route);
        self.sync_route();
    }

    /// Returns false to let the shell draw today's Adjust/Review panes.
    pub(super) fn stack_inspector_body(&mut self, ui: &mut egui::Ui) -> bool {
        if !self.stack_station_view() {
            return false;
        }
        match self.stack_station.tab {
            StationTab::Checks => self.stack_checks_body(ui),
            StationTab::Recipe => return false,
            StationTab::Renders => self.stack_renders_body(ui),
        }
        true
    }

    fn stack_checks_body(&mut self, ui: &mut egui::Ui) {
        let t = studio_theme::tokens(ui.ctx());
        let checks = self.stack_checks();
        let rect = ui.max_rect();
        let mut child = ui.new_child(
            egui::UiBuilder::new()
                .max_rect(rect.shrink2(egui::vec2(16.0, 0.0)))
                .layout(egui::Layout::top_down(egui::Align::Min)),
        );
        let ui = &mut child;
        ui.add_space(14.0);
        let marked: Vec<_> = checks.iter().filter(|check| check.mark.is_some()).collect();
        let looks = marked
            .iter()
            .filter(|check| check.mark == Some(w::Mark::Look))
            .count();
        // The verdict: a light numeral, the statement, the facts, a tally.
        let (verdict, _) =
            ui.allocate_exact_size(egui::vec2(ui.available_width(), 74.0), egui::Sense::hover());
        let numeral = w::text_galley(
            ui,
            &looks.to_string(),
            crate::studio_fonts::Face::Light,
            56.0,
        );
        w::paint_galley_at(
            ui.painter(),
            verdict.left(),
            verdict.top() + 28.0,
            &numeral,
            if looks > 0 { t.warn } else { t.ok },
        );
        let x = verdict.left() + numeral.size().x + 14.0;
        let statement = w::text_galley(
            ui,
            &format!(
                "of {} checks need{} a look",
                checks.len(),
                if looks == 1 { "s" } else { "" }
            ),
            crate::studio_fonts::Face::Strong,
            scale::STATEMENT,
        );
        w::paint_galley_at(ui.painter(), x, verdict.top() + 16.0, &statement, t.ink);
        let facts = w::text_galley(
            ui,
            &self.stack_facts(),
            crate::studio_fonts::Face::Regular,
            scale::SECONDARY,
        );
        w::paint_galley_at(ui.painter(), x, verdict.top() + 37.0, &facts, t.ink2);
        let tally = Rect::from_min_size(
            egui::pos2(verdict.left(), verdict.bottom() - 4.0),
            egui::vec2(verdict.width(), 3.0),
        );
        let count = checks.len().max(1);
        let pitch = tally.width() / count as f32;
        for (index, check) in checks.iter().enumerate() {
            let color = match check.mark {
                Some(w::Mark::Look) => t.warn,
                Some(w::Mark::Failed) => t.bad,
                Some(_) => t.ok,
                None => t.line2,
            };
            ui.painter().rect_filled(
                Rect::from_min_size(
                    egui::pos2(tally.left() + index as f32 * pitch, tally.top()),
                    egui::vec2(pitch - 4.0, tally.height()),
                ),
                0.0,
                color,
            );
        }
        ui.add_space(20.0);
        for check in &checks {
            let (row, _) = ui
                .allocate_exact_size(egui::vec2(ui.available_width(), 54.0), egui::Sense::hover());
            if let Some(mark) = check.mark {
                w::paint_mark(
                    ui.painter(),
                    egui::pos2(row.left() + 4.0, row.top() + 12.0),
                    mark,
                    &t,
                );
            } else {
                w::paint_mark(
                    ui.painter(),
                    egui::pos2(row.left() + 4.0, row.top() + 12.0),
                    w::Mark::NotYet,
                    &t,
                );
            }
            let title = w::text_galley(
                ui,
                check.title,
                crate::studio_fonts::Face::Strong,
                scale::BODY,
            );
            w::paint_galley_at(
                ui.painter(),
                row.left() + 22.0,
                row.top() + 12.0,
                &title,
                t.ink,
            );
            let fact = ui.painter().layout(
                check.fact.clone(),
                egui::FontId::proportional(scale::SECONDARY),
                t.ink2,
                row.width() - 22.0,
            );
            let extra = (fact.size().y - 16.0).max(0.0);
            ui.painter().galley(
                egui::pos2(row.left() + 22.0, row.top() + 22.0),
                fact,
                t.ink2,
            );
            ui.add_space(extra);
        }
        ui.add_space(6.0);
        ui.label(
            egui::RichText::new(
                "A check shows a mark only once its threshold is validated; the rest are facts.",
            )
            .size(scale::SECONDARY)
            .color(t.ink3),
        );
    }

    fn stack_facts(&self) -> String {
        let mut parts = Vec::new();
        if let Some(label) = self.render_label_text() {
            parts.push(label);
        }
        let planes = self.stack_planes();
        if planes > 0 {
            parts.push(format!("{planes} planes"));
        }
        let [width, height] = self.result_viewer.source_size;
        if width > 0 {
            parts.push(format!("{width} \u{d7} {height}"));
        }
        parts.join(" \u{b7} ")
    }

    fn render_label_text(&self) -> Option<String> {
        let run = self.expected_run.as_ref()?;
        let index = self
            .active_stack
            .and_then(|id| self.catalog.node(id))
            .and_then(|node| node.revisions.iter().position(|r| *r == run.directory));
        Some(index.map_or_else(|| run.label.clone(), |i| format!("Render {}", i + 1)))
    }

    /// Checks from what the engine reported. Marks only where the threshold
    /// is a fact (refused frames); the others show their fact (spec D4).
    fn stack_checks(&self) -> Vec<StackCheck> {
        let p = &self.progress;
        let planes = self.stack_planes();
        let mut checks = Vec::new();
        let placed = p.placed.or(p.frames_accepted);
        let refused = p.refused.unwrap_or(0);
        checks.push(StackCheck {
            title: "Every plane read and placed",
            fact: match placed {
                Some(placed) => format!(
                    "{placed} of {planes} \u{b7} {}",
                    if refused == 0 {
                        "none refused".into()
                    } else {
                        format!("{refused} refused")
                    }
                ),
                None => "Not reported for this render".into(),
            },
            mark: placed.map(|_| {
                if refused == 0 {
                    w::Mark::Fine
                } else {
                    w::Mark::Look
                }
            }),
        });
        checks.push(StackCheck {
            title: "Alignment",
            fact: p
                .alignment
                .clone()
                .or_else(|| p.alignment_error.clone())
                .unwrap_or_else(|| "Not reported for this render".into()),
            mark: None,
        });
        if let Some(restore) = &p.optical_restore {
            checks.push(StackCheck {
                title: "Optical restoration",
                fact: restore.fact(),
                // Whether the stack measured its own cutoff is a fact: a
                // stand-in fit or no restoration is marked for a look.
                mark: Some(match restore {
                    crate::pipeline::OpticalRestore::Measured { .. }
                    | crate::pipeline::OpticalRestore::Given { .. } => w::Mark::Fine,
                    _ => w::Mark::Look,
                }),
            });
        }
        if let Some(h) = &p.highlights {
            // A capture must never spend its highlight frames silently.
            checks.push(StackCheck {
                title: "Highlight groups",
                fact: h.fact(),
                mark: Some(if h.complete() {
                    w::Mark::Fine
                } else {
                    w::Mark::Look
                }),
            });
        }
        let brackets = self.stack_station.rail.brackets();
        let ends: Vec<String> = brackets
            .iter()
            .filter(|run| run.start == 0 || run.end == planes)
            .map(|run| format!("{}\u{2013}{}", run.start + 1, run.end))
            .collect();
        checks.push(StackCheck {
            title: "Empty planes at the ends",
            fact: if ends.is_empty() {
                "No run of near-empty planes at either end".into()
            } else {
                format!(
                    "Planes {} keep almost no subject detail (display threshold, not validated)",
                    ends.join(" and ")
                )
            },
            mark: None,
        });
        let first = (0..planes).find(|&plane| {
            self.stack_station.rail.share(plane).is_some_and(|share| {
                share > self.stack_station.rail.peak() * crate::depth_rail::NO_DETAIL_FRACTION
            })
        });
        let last = (0..planes).rev().find(|&plane| {
            self.stack_station.rail.share(plane).is_some_and(|share| {
                share > self.stack_station.rail.peak() * crate::depth_rail::NO_DETAIL_FRACTION
            })
        });
        checks.push(StackCheck {
            title: "Range covers the subject",
            fact: match (first, last) {
                (Some(a), Some(b)) => {
                    format!("Detail begins at plane {} and ends at {}", a + 1, b + 1)
                }
                _ => "No recorded detail to place".into(),
            },
            mark: None,
        });
        checks.push(StackCheck {
            title: "Soft spots",
            fact: "Not measured for this render".into(),
            mark: None,
        });
        checks.push(StackCheck {
            title: "Light steady",
            fact: "Not measured (four-shot gains only)".into(),
            mark: None,
        });
        checks
    }

    fn stack_renders_body(&mut self, ui: &mut egui::Ui) {
        let t = studio_theme::tokens(ui.ctx());
        let rect = ui.max_rect();
        let mut child = ui.new_child(
            egui::UiBuilder::new()
                .max_rect(rect.shrink2(egui::vec2(16.0, 0.0)))
                .layout(egui::Layout::top_down(egui::Align::Min)),
        );
        let ui = &mut child;
        ui.add_space(12.0);
        w::section(ui, "Renders of this stack", |_| {});
        let shown = self.expected_run.as_ref().map(|run| run.directory.clone());
        let revisions = self
            .active_stack
            .and_then(|id| self.catalog.node(id))
            .map(|node| node.revisions.clone())
            .unwrap_or_default();
        let mut open = None;
        for (index, directory) in revisions.iter().enumerate().rev() {
            let run = self
                .catalog
                .runs
                .iter()
                .find(|run| &run.directory == directory);
            let (row, hit) = ui
                .allocate_exact_size(egui::vec2(ui.available_width(), 46.0), egui::Sense::click());
            let current = Some(directory) == shown.as_ref();
            if current {
                ui.painter().rect_filled(row, 0.0, t.accent_soft);
            } else if hit.hovered() {
                ui.painter().rect_filled(row, 0.0, t.raised);
            }
            let title = w::text_galley(
                ui,
                &format!("Render {}", index + 1),
                crate::studio_fonts::Face::Strong,
                scale::BODY,
            );
            w::paint_galley_at(
                ui.painter(),
                row.left() + 8.0,
                row.top() + 14.0,
                &title,
                t.ink,
            );
            let detail = run.map_or_else(
                || "No longer in Projects".to_owned(),
                |run| {
                    format!(
                        "{} \u{b7} {} frames \u{b7} {}",
                        run.label,
                        run.frames,
                        run.status.to_lowercase()
                    )
                },
            );
            ui.painter().text(
                egui::pos2(row.left() + 8.0, row.top() + 32.0),
                egui::Align2::LEFT_CENTER,
                detail,
                egui::FontId::proportional(scale::SECONDARY),
                t.ink2,
            );
            if current {
                ui.painter().text(
                    egui::pos2(row.right() - 8.0, row.center().y),
                    egui::Align2::RIGHT_CENTER,
                    "SHOWN",
                    egui::FontId::proportional(scale::CAPS),
                    t.accent,
                );
            } else if hit.clicked()
                && let Some(run) = run
            {
                open = Some(run.clone());
            }
            theme::rule(ui.painter(), row.left_bottom(), row.right_bottom(), t.line);
        }
        if revisions.is_empty() {
            ui.label(
                egui::RichText::new("This render is not part of a saved stack.")
                    .size(scale::SECONDARY)
                    .color(t.ink3),
            );
        }
        ui.add_space(10.0);
        ui.label(
            egui::RichText::new("A new render never replaces an old one.")
                .size(scale::SECONDARY)
                .color(t.ink3),
        );
        if let Some(run) = open
            && self.job.is_none()
        {
            self.reopen_run(run);
        }
    }
}

pub(crate) struct StackCheck {
    title: &'static str,
    fact: String,
    mark: Option<w::Mark>,
}

impl StackStation {
    pub(crate) fn with_hold(plane: Option<usize>) -> Self {
        Self {
            launch_hold: plane,
            ..Default::default()
        }
    }
    fn core_peak(&self) -> Option<usize> {
        self.last_core.peak
    }
    fn core_popover(&self) -> Option<Rect> {
        self.last_core.popover
    }
}

fn plane_lens_levels() -> usize {
    crate::plane_lens::DETAIL_LEVELS
}

fn clamp_aperture(rect: Rect) -> Rect {
    let size = rect.size().min(egui::vec2(1.0, 1.0));
    let min = egui::pos2(
        rect.min.x.clamp(0.0, 1.0 - size.x),
        rect.min.y.clamp(0.0, 1.0 - size.y),
    );
    Rect::from_min_size(min, size)
}

fn rule(ui: &mut egui::Ui, t: &Tokens) {
    let (rect, _) = ui.allocate_exact_size(egui::vec2(1.0, 20.0), egui::Sense::hover());
    theme::rule(
        ui.painter(),
        rect.center_top(),
        rect.center_bottom(),
        t.line,
    );
}

/// The real depth rail for Develop's depth brush (P7's `DepthRail` hook):
/// the kept share per plane at the finest size, pooled to the strip's width,
/// with the chosen range shaded. Drag across it to choose planes.
pub(crate) struct DevelopRangeRail<'a> {
    pub(crate) station: &'a mut StackStation,
    pub(crate) progress: &'a PipelineProgress,
}

impl crate::develop_station::DepthRail for DevelopRangeRail<'_> {
    fn show(
        &mut self,
        ui: &mut egui::Ui,
        palette: &crate::develop_station::style::StudioPalette,
        range: (usize, usize),
        planes: usize,
    ) -> Option<(usize, usize)> {
        let planes = planes.max(1);
        let station = &mut *self.station;
        station.develop_rail.update(
            &self.progress.admission_archive,
            &self.progress.sampled_mask_history,
            planes,
            0,
            crate::depth_rail::evidence_revision(self.progress),
        );
        // The rail's whole width, less room for the "of N" label after it.
        let width = (ui.available_width() - 64.0).max(160.0);
        let (rect, response) =
            ui.allocate_exact_size(egui::vec2(width, 26.0), egui::Sense::click_and_drag());
        let columns = ((rect.width() / 2.0) as usize).clamp(1, planes);
        let key = (
            station.develop_rail.series_revision(),
            planes,
            rect.width().to_bits(),
        );
        if station
            .develop_columns
            .as_ref()
            .is_none_or(|(old, _)| *old != key)
        {
            let rail = &station.develop_rail;
            let peak = rail.peak();
            let values: Vec<Option<f32>> = (0..columns)
                .map(|column| {
                    let start = column * planes / columns;
                    let end = ((column + 1) * planes / columns).max(start + 1);
                    let shares: Vec<f32> =
                        (start..end).filter_map(|plane| rail.share(plane)).collect();
                    (!shares.is_empty() && peak > 0.0).then(|| {
                        (shares.iter().sum::<f32>() / shares.len() as f32 / peak).clamp(0.0, 1.0)
                    })
                })
                .collect();
            station.develop_columns = Some((key, std::sync::Arc::new(values)));
        }
        let plane_at = |x: f32| -> usize {
            (((x - rect.left()) / rect.width()).clamp(0.0, 1.0) * (planes - 1) as f32).round()
                as usize
        };
        let x =
            |plane: usize| rect.left() + rect.width() * plane as f32 / (planes - 1).max(1) as f32;
        let painter = ui.painter_at(rect.expand(1.0));
        let (first, last) = (range.0.min(range.1), range.0.max(range.1).min(planes - 1));
        painter.rect_filled(
            Rect::from_min_max(
                egui::pos2(x(first), rect.top()),
                egui::pos2(x(last).max(x(first) + 1.0), rect.bottom()),
            ),
            0.0,
            palette.accent_soft,
        );
        if let Some((_, values)) = &station.develop_columns {
            let mut mesh = egui::Mesh::default();
            let pitch = rect.width() / values.len() as f32;
            for (column, value) in values.iter().enumerate() {
                let left = rect.left() + column as f32 * pitch;
                match value {
                    Some(value) => mesh.add_colored_rect(
                        Rect::from_min_max(
                            egui::pos2(left, rect.bottom() - 1.0 - value * (rect.height() - 4.0)),
                            egui::pos2(left + (pitch - 0.5).max(1.0), rect.bottom()),
                        ),
                        palette.ok.gamma_multiply(0.6),
                    ),
                    None => mesh.add_colored_rect(
                        Rect::from_min_max(
                            egui::pos2(left, rect.bottom() - 1.0),
                            egui::pos2(left + (pitch * 0.5).max(1.0), rect.bottom()),
                        ),
                        palette.line_2,
                    ),
                }
            }
            painter.add(egui::Shape::mesh(mesh));
        }
        for plane in [first, last] {
            painter.line_segment(
                [
                    egui::pos2(x(plane), rect.top()),
                    egui::pos2(x(plane), rect.bottom()),
                ],
                Stroke::new(1.0_f32, palette.accent),
            );
        }
        let mut chosen = None;
        if response.drag_started()
            && let Some(at) = response.interact_pointer_pos()
        {
            station.develop_anchor = Some(plane_at(at.x));
        }
        if (response.dragged() || response.clicked())
            && let Some(at) = response.interact_pointer_pos()
        {
            let here = plane_at(at.x);
            let anchor = station.develop_anchor.unwrap_or(here);
            chosen = Some((anchor.min(here), anchor.max(here)));
        }
        if !response.dragged() {
            station.develop_anchor = None;
        }
        response.on_hover_text(format!(
            "Planes {}\u{2013}{} of {planes} \u{b7} detail kept at the finest size \u{b7} drag to choose",
            first + 1,
            last + 1
        ));
        chosen.filter(|&new| new != (first, last))
    }
}

#[cfg(test)]
#[path = "app-station-stack-tests.rs"]
mod tests;
