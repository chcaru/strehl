//! One continuous observation canvas. Geometry never changes with phase.
use crate::{
    pipeline::{DiagnosticKind, DiagnosticScale, PipelineProgress, Stage},
    process_theater::ProcessTheater,
    theme::BG,
    workbench::SourcePhoto,
};
use eframe::egui::{self, Rect, TextureHandle, Ui};
use std::collections::BTreeSet;

#[derive(Clone, Copy)]
pub struct SurfaceMeta {
    pub sequence: u64,
    pub kind: DiagnosticKind,
    pub scale: DiagnosticScale,
    pub min: f32,
    pub max: f32,
    pub samples: [usize; 2],
    pub folded: usize,
}
#[derive(Clone, Copy)]
pub struct Surface<'a> {
    pub epoch: u64,
    pub stage: Stage,
    pub level: usize,
    pub texture: &'a TextureHandle,
    /// None is an accumulated stack, never its last input frame.
    pub frame: Option<usize>,
    pub meta: Option<SurfaceMeta>,
    pub packet: Option<&'a crate::pipeline::DiagnosticSurface>,
}
#[derive(Clone, Copy)]
pub struct Input<'a> {
    pub epoch: u64,
    pub progress: &'a PipelineProgress,
    pub frame_count: usize,
    pub selected: usize,
    pub inspected_pair: Option<[usize; 2]>,
    /// Native contact thumbnails, with no full-image aperture claim.
    pub photos: &'a [SourcePhoto],
    /// Canonical overview/detail only. Never native letterboxed thumbs.
    pub inspection_photos: &'a [SourcePhoto],
    pub surfaces: &'a [Surface<'a>],
    /// Only this session's owned result, never an unrelated opened image.
    pub output: Option<&'a TextureHandle>,
    /// Decoded TIFF dimensions, before a device-limited display overview.
    pub output_size: Option<[u32; 2]>,
}
impl Input<'_> {
    /// Engine work may cover a prefix while the capture browser retains the
    /// whole bracket. Observed process counts never borrow that larger axis.
    pub(crate) fn processing_count(&self) -> usize {
        self.progress
            .frames_total
            .unwrap_or(self.frame_count)
            .min(self.frame_count)
    }
}
#[derive(Default, Debug, PartialEq, Eq)]
pub struct Response {
    pub selected: Option<usize>,
    pub compare_pair: Option<[usize; 2]>,
    pub open_sources: bool,
    pub return_live: bool,
    pub exit_space: bool,
}
#[derive(Default)]
pub struct ProcessSpace {
    epoch: Option<u64>,
    visited: BTreeSet<Stage>,
    theater: ProcessTheater,
    journey: crate::process_journey::ProcessJourney,
    output_path: Option<std::path::PathBuf>,
}
impl ProcessSpace {
    pub(crate) fn set_photo_paint(&mut self, paint: Option<crate::photo_viewport::PhotoPaint>) {
        self.theater.set_photo_paint(paint);
    }
    pub(crate) fn edit_mapping(&self) -> Option<(Rect, Rect)> {
        self.theater.edit_mapping
    }
    pub(crate) fn set_annotation_mode(&mut self, active: bool) {
        self.theater.annotation_mode = active;
    }
    pub(crate) fn set_edit_navigation(&mut self, active: bool) {
        self.theater.edit_navigation = active;
    }
    pub(crate) fn set_edit_focus(&mut self, active: bool) {
        self.theater.edit_focus = active;
    }
    pub(crate) fn set_photo_view(&mut self, center: [f32; 2], zoom: f32) {
        self.theater
            .set_photo_view(egui::pos2(center[0], center[1]), zoom);
    }
    pub(crate) fn set_output_path(&mut self, path: Option<&std::path::Path>) {
        if self.output_path.as_deref() != path {
            self.theater.invalidate_balance();
            self.output_path = path.map(std::path::Path::to_path_buf);
        }
    }
    pub(crate) fn undo(&mut self) -> bool {
        self.theater.undo()
    }
    pub(crate) fn redo(&mut self) -> bool {
        self.theater.redo()
    }
    pub(crate) fn can_undo(&self) -> bool {
        self.theater.can_undo()
    }
    pub(crate) fn can_redo(&self) -> bool {
        self.theater.can_redo()
    }
    pub(crate) fn history_revision(&self) -> u64 {
        self.theater.history_revision()
    }
    pub(crate) fn history_depths(&self) -> (usize, usize) {
        self.theater.history_depths()
    }
    pub(crate) fn history_commits(&self) -> u64 {
        self.theater.history_commits()
    }
    pub(crate) fn layout(&self) -> crate::workspace_layout::WorkspaceLayout {
        self.theater.layout
    }
    pub(crate) fn set_layout(&mut self, layout: crate::workspace_layout::WorkspaceLayout) {
        self.theater.layout = layout;
    }
    pub fn inspection_frame(&self) -> Option<usize> {
        self.theater.inspection_frame()
    }
    pub fn inspect_frame(&mut self, index: usize) {
        self.theater.inspect_frame(index);
    }
    pub(crate) fn screenshot_ranges(
        &mut self,
        domain: (u64, u64),
        frame_count: usize,
        ranges: &[[usize; 2]],
    ) -> Result<bool, &'static str> {
        if self.epoch != Some(domain.0) {
            return Ok(false);
        }
        self.theater.screenshot_ranges(domain, frame_count, ranges)
    }
    pub fn contact_indices(&self) -> Vec<usize> {
        let mut indices = self.theater.contact_indices();
        indices.sort_unstable();
        indices.dedup();
        indices
    }
    pub fn review_focus(&mut self, focus: crate::controls::ReviewFocus, selected: usize) {
        self.theater.review_focus(focus, selected);
    }

    pub fn transitioning(&self) -> bool {
        self.theater.transitioning()
    }

    pub fn show(&mut self, ui: &mut Ui, input: Input<'_>) -> Response {
        if self.epoch != Some(input.epoch) {
            let layout = self.theater.layout;
            let annotation_mode = self.theater.annotation_mode;
            let edit_navigation = self.theater.edit_navigation;
            let edit_focus = self.theater.edit_focus;
            let photo_paint = self.theater.photo_paint.clone();
            let requested_view = self.theater.requested_view;
            let output_path = self.output_path.take();
            *self = Self {
                epoch: Some(input.epoch),
                output_path,
                ..Default::default()
            };
            self.theater.layout = layout;
            self.theater.annotation_mode = annotation_mode;
            self.theater.edit_navigation = edit_navigation;
            self.theater.edit_focus = edit_focus;
            self.theater.set_photo_paint(photo_paint);
            if let Some((center, zoom)) = requested_view {
                self.theater.set_photo_view(center, zoom);
            }
        }
        let certified = input.output.is_some()
            && input.output_size.is_some_and(|size| {
                crate::process_output_space::OutputSpace::from_progress(input.progress, size)
                    .is_some()
            });
        self.visited.extend(
            input
                .progress
                .observed_stages
                .iter()
                .filter_map(|&s| normal_stage(s)),
        );
        if input.progress.alignment_phase.is_some() {
            self.visited.insert(Stage::Alignment);
        }
        if !input.progress.frame_observations.is_empty() {
            self.visited.insert(Stage::Merge);
        }
        for surface in input.surfaces.iter().filter(|s| s.epoch == input.epoch) {
            if let Some(stage) = normal_stage(surface.stage) {
                self.visited.insert(stage);
            }
        }
        let (scene, _) = ui.allocate_exact_size(ui.available_size(), egui::Sense::hover());
        let painter = ui.painter_at(scene);
        painter.rect_filled(scene, 0.0, BG);
        let mut response = Response::default();
        self.theater.navigation_shortcuts(ui, &mut response);
        let journey = Rect::from_min_size(
            scene.min + egui::vec2(12.0, 6.0),
            egui::vec2(
                (crate::window_chrome::dock_rect(ui.ctx().content_rect()).left()
                    - scene.left()
                    - 24.0)
                    .max(240.0),
                crate::process_journey::HEIGHT,
            ),
        );
        let edit_chrome = ui.ctx().animate_bool_with_time(
            ui.id().with("photo-edit-chrome"),
            self.theater.edit_focus && input.progress.stage == Stage::Complete,
            0.18,
        );
        if edit_chrome < 0.001 {
            self.journey.show(ui, journey, input.epoch, input.progress);
        }
        // One persistent timeline owns capture browsing, sampled participation,
        // and source inspection. Its seam never participates in
        // egui's auto-sizing feedback: only a pointer drag changes the fraction.
        let minimum_timeline = crate::process_participation::HEIGHT + 25.0;
        let maximum_timeline = (scene.height() - 340.0).clamp(minimum_timeline, 420.0);
        let default_timeline = (scene.height() * 0.29).clamp(minimum_timeline, 300.0);
        let height = |lower: f32| {
            (default_timeline + scene.height() * lower).clamp(minimum_timeline, maximum_timeline)
        };
        let boundary = scene.bottom() - height(self.theater.layout.lower) - 7.0;
        let seam = Rect::from_min_max(
            egui::pos2(scene.left(), boundary - 7.0),
            egui::pos2(scene.right(), boundary + 1.0),
        );
        let (delta, reset) =
            crate::workspace_layout::seam(ui, "process-timeline-height", seam, false);
        if reset {
            self.theater.layout.lower = 0.0;
        } else if delta != 0.0 {
            let next = (height(self.theater.layout.lower) - delta)
                .clamp(minimum_timeline, maximum_timeline);
            self.theater.layout.lower = (next - default_timeline) / scene.height().max(1.0);
        }
        let bottom = height(self.theater.layout.lower) + 14.0;
        let body = Rect::from_min_max(
            scene.min + egui::vec2(12.0, 92.0 - 80.0 * edit_chrome),
            scene.max - egui::vec2(12.0, bottom),
        );
        let detail = Input {
            selected: self
                .inspection_frame()
                .filter(|&i| i < input.frame_count)
                .unwrap_or_else(|| {
                    input
                        .progress
                        .processing_frame
                        .filter(|&i| i < input.frame_count)
                        .unwrap_or(input.selected)
                }),
            ..input
        };
        let contacts = Rect::from_min_max(
            egui::pos2(body.left(), scene.bottom() - bottom + 7.0),
            egui::pos2(body.right(), scene.bottom() - 7.0),
        );
        self.theater
            .show_with_ribbon(ui, body, &detail, &mut response, Some(contacts));
        // The theater has now established the epoch and owned photograph.
        // Start optional map loading after those transitions can reset its state.
        self.theater.update_balance(
            ui.ctx(),
            self.output_path.as_deref().filter(|_| certified),
            input
                .progress
                .analysis_size
                .or(input.progress.plane_size)
                .filter(|_| certified),
        );
        if let Some(index) = response.selected.filter(|&i| i < input.frame_count) {
            self.inspect_frame(index);
        }
        if response.compare_pair.is_some() {
            self.theater.resume_live();
        }
        response
    }
}
fn normal_stage(stage: Stage) -> Option<Stage> {
    match stage {
        Stage::Complete => Some(Stage::Rendering),
        Stage::Failed | Stage::Cancelled => None,
        stage => Some(stage),
    }
}
#[cfg(test)]
#[path = "process-space-tests.rs"]
mod tests;
