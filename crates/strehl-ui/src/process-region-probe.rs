//! A temporary photograph region, measured only at retained kernel samples.
//! The caller certifies the photograph's aligned UV domain. This observer never
//! grabs input, modifies the exploration journal, or invents dense ownership.
use std::collections::BTreeMap;
#[path = "process-region-spatial.rs"]
mod spatial_paint;
#[path = "process-region-visual.rs"]
mod visual;

use crate::{
    pipeline::{DiagnosticKind, DiagnosticScale, DiagnosticScope, DiagnosticSurface},
    process_provenance::{AdmissionArchive, AdmissionMeta},
    process_sample_glyphs::{SampleGeometry, SampleGlyph, level_color},
    theme::{ACCENT, LINE, MUTED},
};
use eframe::egui::{self, Align2, Color32, FontId, Pos2, Rect, Stroke, Ui, Vec2};

fn consumed_zoom_id() -> egui::Id {
    egui::Id::new("regional-probe-consumed-wheel-zoom")
}

/// egui smooths command-wheel into a private zoom accumulator. Consuming its
/// public wheel fields does not drain that accumulator. After a probe resize,
/// image consumers ignore that derived tail until it ends. Fresh raw wheel is
/// still available to their normal wheel path; actual pinch/Zoom events survive.
pub(crate) fn zoom_delta(ui: &Ui) -> f32 {
    let consumed = ui
        .ctx()
        .data(|data| data.get_temp::<bool>(consumed_zoom_id()).unwrap_or(false));
    if !consumed {
        return ui.input(|state| state.zoom_delta());
    }
    let (derived, direct) = ui.input(|state| {
        let direct = state.multi_touch().map_or_else(
            || {
                state
                    .events
                    .iter()
                    .filter_map(|event| match event {
                        egui::Event::Zoom(factor) => Some(*factor),
                        _ => None,
                    })
                    .product()
            },
            |touch| touch.zoom_delta,
        );
        (state.zoom_delta(), direct)
    });
    if derived == 1.0 && direct == 1.0 {
        ui.ctx()
            .data_mut(|data| data.remove::<bool>(consumed_zoom_id()));
    }
    direct
}

#[derive(Clone, Copy, Debug, Default, PartialEq, Eq)]
pub(crate) struct SampleCount {
    pub observed: usize,
    pub admitted: usize,
}
impl SampleCount {
    fn fraction(self) -> Option<f32> {
        (self.observed > 0).then(|| self.admitted as f32 / self.observed as f32)
    }
}

/// Membership, rather than a floating point aperture, is the cache key. Moving
/// within the same gaps between transmitted samples cannot change the answer.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(crate) struct SampleWindow {
    samples: [usize; 2],
    columns: [usize; 2],
    rows: [usize; 2],
}
impl SampleWindow {
    pub(crate) fn new(level: usize, meta: AdmissionMeta, region: Rect) -> Option<Self> {
        if !region.is_finite() || region.width() < 0.0 || region.height() < 0.0 {
            return None;
        }
        let geometry = SampleGeometry::new(level, meta)?;
        let axis = |vertical: bool| {
            let count = meta.samples[usize::from(vertical)];
            let (low, high) = if vertical {
                (region.top(), region.bottom())
            } else {
                (region.left(), region.right())
            };
            let coordinate = |index| {
                let point = geometry
                    .at(if vertical {
                        index * meta.samples[0]
                    } else {
                        index
                    })
                    .unwrap()
                    .center;
                if vertical { point.y } else { point.x }
            };
            // Coefficient centres are strictly ordered, including odd extents.
            // Partition half-open windows so adjacent regions never double count.
            let partition = |value: f32| {
                let (mut first, mut end) = (0, count);
                while first < end {
                    let middle = first + (end - first) / 2;
                    if coordinate(middle) < value {
                        first = middle + 1;
                    } else {
                        end = middle;
                    }
                }
                first
            };
            let start = partition(low);
            let end = partition(high).max(start);
            [start, end]
        };
        Some(Self {
            samples: meta.samples,
            columns: axis(false),
            rows: axis(true),
        })
    }

    #[cfg(test)]
    pub(crate) fn contains(self, index: usize) -> bool {
        let [width, height] = self.samples;
        index < width * height
            && (self.columns[0]..self.columns[1]).contains(&(index % width))
            && (self.rows[0]..self.rows[1]).contains(&(index / width))
    }

    fn indices(self) -> impl Iterator<Item = usize> {
        (self.rows[0]..self.rows[1]).flat_map(move |row| {
            (self.columns[0]..self.columns[1]).map(move |column| row * self.samples[0] + column)
        })
    }

    /// The archive exposes AdmissionCells: nth skips unobserved positions in
    /// constant time without reading their bits or creating a temporary mask.
    pub(crate) fn counts(self, mut cells: impl ExactSizeIterator<Item = bool>) -> SampleCount {
        if cells.len() != self.samples[0] * self.samples[1] {
            return SampleCount::default();
        }
        let mut result = SampleCount::default();
        let mut next = 0;
        for row in self.rows[0]..self.rows[1] {
            for column in self.columns[0]..self.columns[1] {
                let index = row * self.samples[0] + column;
                let Some(admitted) = cells.nth(index - next) else {
                    return SampleCount::default();
                };
                result.observed += 1;
                result.admitted += usize::from(admitted);
                next = index + 1;
            }
        }
        result
    }

    pub(crate) fn archive_counts(
        self,
        archive: &AdmissionArchive,
        level: usize,
        frame: usize,
    ) -> SampleCount {
        archive
            .window_counts(level, frame, self.columns, self.rows)
            .map_or_else(SampleCount::default, |(admitted, observed)| SampleCount {
                admitted,
                observed,
            })
    }

    fn counts_indexed(self, count: usize, mut value: impl FnMut(usize) -> bool) -> SampleCount {
        if count != self.samples[0] * self.samples[1] {
            return SampleCount::default();
        }
        let mut result = SampleCount::default();
        for row in self.rows[0]..self.rows[1] {
            for column in self.columns[0]..self.columns[1] {
                result.observed += 1;
                result.admitted += usize::from(value(row * self.samples[0] + column));
            }
        }
        result
    }
}

struct Evidence {
    meta: AdmissionMeta,
    window: Option<SampleWindow>,
    count: SampleCount,
}

struct Fallback {
    packet: DiagnosticSurface,
    meta: AdmissionMeta,
    window: Option<SampleWindow>,
    count: SampleCount,
    points: Vec<SampleGlyph>,
}

#[derive(Clone, Debug, PartialEq, Eq)]
struct SpatialKey {
    level: usize,
    sources: Vec<(usize, AdmissionMeta, SampleWindow)>,
}

#[derive(Clone, Copy, Debug)]
struct SpatialPoint {
    glyph: SampleGlyph,
    /// Independent admission bits for the displayed captures, not weights.
    sources: u8,
}

#[derive(Default)]
pub(crate) struct RegionProbe {
    texture: Option<egui::TextureId>,
    visual_revision: u64,
    visual_cache: std::cell::RefCell<visual::HeatCache>,
    spatial_paint: std::cell::RefCell<spatial_paint::Cache>,
    evidence: BTreeMap<(usize, usize), Evidence>,
    levels: Vec<usize>,
    fallback: Option<Fallback>,
    analysis_extent: Option<[usize; 2]>,
    balance: Option<u16>,
    side: Option<f32>,
    spatial_key: Option<SpatialKey>,
    spatial: Vec<SpatialPoint>,
    popup_bounds: Option<Rect>,
    source_frame: Option<usize>,
    receipt_key: Option<(u64, usize, [usize; 2], usize)>,
    level_meta: Vec<(usize, Option<AdmissionMeta>)>,
    windows: Vec<(usize, Option<SampleWindow>)>,
    region: Option<Rect>,
    spatial_dirty: bool,
    #[cfg(test)]
    receipt_scans: usize,
    #[cfg(test)]
    spatial_selections: usize,
    #[cfg(test)]
    readings: usize,
    #[cfg(test)]
    spatial_reads: usize,
}
impl RegionProbe {
    pub(crate) fn set_texture(&mut self, texture: egui::TextureId) {
        self.texture = Some(texture);
    }
    /// Call before photograph zoom, only in the caller-certified final image
    /// and outside its navigator. The returned flag owns this wheel event;
    /// callers must also skip egui's derived zoom_delta for that frame.
    pub(crate) fn resize(&mut self, ui: &mut Ui, image: Rect) -> bool {
        if !ui.is_enabled()
            || !ui.rect_contains_pointer(image)
            || !ui.ctx().memory(|m| m.is_above_modal_layer(ui.layer_id()))
            || egui::Popup::is_any_open(ui.ctx())
        {
            return false;
        }
        let delta = ui.input(|state| {
            if !state.focused
                || state.viewport().focused == Some(false)
                || state.viewport().minimized == Some(true)
                || state.pointer.any_down()
                || state.key_down(egui::Key::Space)
            {
                return None;
            }
            let wheel: f32 = state
                .events
                .iter()
                .filter_map(|event| {
                    if let egui::Event::MouseWheel {
                        unit,
                        delta,
                        modifiers,
                    } = event
                        && modifiers.ctrl
                    {
                        let scale = match unit {
                            egui::MouseWheelUnit::Point => 1.0,
                            egui::MouseWheelUnit::Line => 40.0,
                            egui::MouseWheelUnit::Page => 200.0,
                        };
                        Some(delta.y * scale)
                    } else {
                        None
                    }
                })
                .sum();
            let wheel = if wheel != 0.0 {
                wheel
            } else if state.modifiers.ctrl {
                state.raw_scroll_delta.y
            } else {
                0.0
            };
            (wheel.is_finite() && wheel != 0.0).then_some(wheel)
        });
        let Some(delta) = delta else {
            return false;
        };
        self.side = Some(
            (self.side.unwrap_or(96.0) * (delta.clamp(-400.0, 400.0) * 0.0035).exp())
                .clamp(32.0, 320.0),
        );
        ui.ctx()
            .data_mut(|data| data.insert_temp(consumed_zoom_id(), true));
        ui.input_mut(|state| {
            state.raw_scroll_delta = Vec2::ZERO;
            state.smooth_scroll_delta = Vec2::ZERO;
            state.events.retain(|event| !matches!(event, egui::Event::MouseWheel { modifiers, .. } if modifiers.ctrl));
        });
        ui.ctx().request_repaint();
        true
    }

    /// Compute against the current pointer even before this frame paints. The
    /// timeline can then share the observer region without a one-frame delay.
    pub(crate) fn current_region(&self, ui: &Ui, image: Rect, aperture: Rect) -> Option<Rect> {
        let pointer = ui.input(|state| {
            (state.focused
                && state.viewport().focused != Some(false)
                && state.viewport().minimized != Some(true)
                && !state.pointer.any_down()
                && !state.pointer.any_pressed()
                && !state.pointer.any_released()
                && state.raw_scroll_delta == Vec2::ZERO
                && state.smooth_scroll_delta == Vec2::ZERO
                && !state.key_down(egui::Key::Space))
            .then(|| state.pointer.hover_pos())
            .flatten()
        })?;
        if !ui.is_enabled()
            || !ui.rect_contains_pointer(image)
            || !ui
                .ctx()
                .memory(|memory| memory.is_above_modal_layer(ui.layer_id()))
            || egui::Popup::is_any_open(ui.ctx())
        {
            return None;
        }
        region_at(image, aperture, pointer, self.side.unwrap_or(96.0))
    }

    /// The compared source owns the first identity slot when its samples exist.
    /// Unknown or rejected samples stay explicit; this is never a weight rank.
    pub(crate) fn set_source_frame(&mut self, frame: Option<usize>) {
        if self.source_frame != frame {
            self.source_frame = frame;
            self.spatial_dirty = true;
        }
    }

    pub(crate) fn set_balance(&mut self, value: Option<u16>) {
        self.balance = value.filter(|&value| value <= 1000);
    }
    /// The caller supplies only the completed selected-band observation in a
    /// certified output domain. Clearing that certificate must pass None.
    pub(crate) fn set_fallback(&mut self, value: Option<(DiagnosticSurface, [usize; 2])>) {
        let Some((packet, extent)) = value else {
            self.fallback = None;
            return;
        };
        let meta = AdmissionMeta {
            sequence: packet.sequence,
            samples: [packet.width, packet.height],
            extent,
        };
        if self.fallback.as_ref().is_some_and(|old| {
            old.meta == meta
                && old.packet.level == packet.level
                && old.packet.folded == packet.folded
                && std::sync::Arc::ptr_eq(&old.packet.pixels, &packet.pixels)
        }) {
            return;
        }
        let valid = packet.kind == DiagnosticKind::Averaging
            && packet.scope == DiagnosticScope::Stack
            && packet.scale == DiagnosticScale::Linear
            && packet.min == 0.0
            && packet.max == 1.0
            && packet.pixels.len() == packet.width.saturating_mul(packet.height)
            && packet.pixels.iter().all(|value| matches!(value, 0 | 255))
            && SampleGeometry::new(packet.level, meta).is_some();
        self.fallback = valid.then_some(Fallback {
            packet,
            meta,
            window: None,
            count: SampleCount::default(),
            points: Vec::new(),
        });
    }
    /// extent describes the final photograph; sample geometry is always read
    /// from each packet's analysis extent, which may be half the final size.
    #[allow(clippy::too_many_arguments)] // Keep the two certified image domains explicit at the drawing boundary.
    pub(crate) fn show(
        &mut self,
        ui: &mut Ui,
        image: Rect,
        aperture: Rect,
        archive: &AdmissionArchive,
        level: usize,
        analysis_extent: [usize; 2],
        extent: [usize; 2],
        frame_count: usize,
    ) -> Option<Rect> {
        if frame_count == 0 || extent.contains(&0) || analysis_extent.contains(&0) {
            return None;
        }
        let region = self.current_region(ui, image, aperture)?;
        self.update(archive, level, analysis_extent, frame_count, region);
        let project = |uv: Pos2| image.min + (uv - aperture.min) / aperture.size() * image.size();
        let outline = Rect::from_min_max(project(region.min), project(region.max));
        let painter = ui.painter_at(image);
        self.paint_spatial(&painter, image, aperture, outline, level);
        for (corner, direction) in [
            (outline.left_top(), Vec2::splat(1.0)),
            (outline.right_top(), egui::vec2(-1.0, 1.0)),
            (outline.right_bottom(), Vec2::splat(-1.0)),
            (outline.left_bottom(), egui::vec2(1.0, -1.0)),
        ] {
            for delta in [
                egui::vec2(direction.x * 7.0, 0.0),
                egui::vec2(0.0, direction.y * 7.0),
            ] {
                painter.line_segment([corner, corner + delta], Stroke::new(1.0_f32, ACCENT));
            }
        }
        // Pure painter output: even a disabled Area registers widget rectangles
        // that can hide a lower layer on the next pointer jump in egui0.33.
        // The observer must register no UI or Area at all.
        let viewport = ui.ctx().content_rect().shrink(8.0);
        let available = popup_placement(viewport, outline, egui::vec2(370.0, viewport.height()));
        if available.width() < 80.0 || available.height() < 60.0 {
            self.popup_bounds = None;
            return Some(region);
        }
        let width = available.width();
        let content = self.tooltip(
            ui.ctx(),
            width,
            available.height(),
            region,
            level,
            extent,
            frame_count,
        );
        let placement = popup_placement(viewport, outline, egui::vec2(width, content.y + 8.0));
        let floating = ui
            .ctx()
            .layer_painter(egui::LayerId::new(
                egui::Order::Tooltip,
                ui.id().with("regional-admission"),
            ))
            .with_clip_rect(placement.intersect(viewport));
        floating.rect_filled(placement, 0.0, crate::theme::BG);
        floating.rect_stroke(
            placement,
            0.0,
            Stroke::new(1.0_f32, LINE),
            egui::StrokeKind::Inside,
        );
        for mut shape in content.shapes {
            shape.translate(placement.min.to_vec2());
            floating.add(shape);
        }
        self.popup_bounds = Some(placement);
        Some(region)
    }

    fn update(
        &mut self,
        archive: &AdmissionArchive,
        active: usize,
        analysis_extent: [usize; 2],
        frame_count: usize,
        region: Rect,
    ) {
        if self.analysis_extent != Some(analysis_extent) {
            self.evidence.clear();
            self.analysis_extent = Some(analysis_extent);
        }
        if let Some(fallback) = &mut self.fallback {
            let window = SampleWindow::new(fallback.packet.level, fallback.meta, region);
            if fallback.window != window {
                fallback.count = window.map_or_else(SampleCount::default, |window| {
                    window.counts_indexed(fallback.packet.pixels.len(), |index| {
                        fallback.packet.pixels[index] == 255
                    })
                });
                fallback.window = window;
                fallback.points.clear();
                if let (Some(window), Some(geometry)) = (
                    window,
                    SampleGeometry::new(fallback.packet.level, fallback.meta),
                ) {
                    for index in window.indices() {
                        if fallback.packet.pixels[index] == 255 {
                            fallback.points.push(geometry.at(index).unwrap());
                        }
                    }
                }
            }
        }
        let key = (archive.revision(), active, analysis_extent, frame_count);
        let receipts_changed = self.receipt_key != Some(key);
        if receipts_changed {
            self.receipt_key = Some(key);
            #[cfg(test)]
            {
                self.receipt_scans += 1;
            }
            self.levels.clear();
            self.levels.extend(archive.levels().take(16));
            if !self.levels.contains(&active) && archive.frames(active).next().is_some() {
                if self.levels.len() == 16 {
                    self.levels.pop();
                }
                self.levels.push(active);
                self.levels.sort_unstable();
            }
            self.level_meta.clear();
            self.level_meta.extend(self.levels.iter().map(|&level| {
                let meta = archive
                    .frames(level)
                    .next()
                    .and_then(|frame| archive.metadata(level, frame))
                    .filter(|meta| meta.extent == analysis_extent);
                (level, meta)
            }));
            self.evidence.retain(|&(level, frame), evidence| {
                frame < frame_count
                    && self.levels.contains(&level)
                    && evidence.meta.extent == analysis_extent
                    && archive.metadata(level, frame) == Some(evidence.meta)
            });
            self.spatial_dirty = true;
        } else if self.region == Some(region) {
            self.sync_spatial(archive, active);
            return;
        }
        self.region = Some(region);
        for &(level, meta) in &self.level_meta {
            let window = meta.and_then(|meta| SampleWindow::new(level, meta, region));
            let old_window = self
                .windows
                .iter()
                .find(|(old, _)| *old == level)
                .map(|(_, old)| *old);
            if !receipts_changed && old_window == Some(window) {
                continue;
            }
            if let Some((_, old)) = self.windows.iter_mut().find(|(old, _)| *old == level) {
                *old = window;
            } else {
                self.windows.push((level, window));
            }
            self.spatial_dirty = true;
            for frame in archive.frames(level).filter(|&frame| frame < frame_count) {
                if self
                    .evidence
                    .get(&(level, frame))
                    .is_some_and(|evidence| evidence.window == window)
                {
                    continue;
                }
                if let Some(meta) = archive.metadata(level, frame)
                    && meta.extent == analysis_extent
                {
                    let count = window.map_or_else(SampleCount::default, |window| {
                        window.archive_counts(archive, level, frame)
                    });
                    self.evidence.insert(
                        (level, frame),
                        Evidence {
                            meta,
                            window,
                            count,
                        },
                    );
                    #[cfg(test)]
                    {
                        self.readings += 1;
                    }
                }
            }
        }
        self.sync_spatial(archive, active);
    }

    fn sync_spatial(&mut self, archive: &AdmissionArchive, active: usize) {
        if !self.spatial_dirty {
            return;
        }
        self.spatial_dirty = false;
        self.visual_revision = self.visual_revision.wrapping_add(1);
        #[cfg(test)]
        {
            self.spatial_selections += 1;
        }
        let mut strongest: Vec<_> = self
            .evidence
            .range((active, 0)..=(active, usize::MAX))
            .filter(|(key, evidence)| {
                evidence.count.admitted > 0
                    || (Some(key.1) == self.source_frame && evidence.count.observed > 0)
            })
            .collect();
        strongest.sort_by(|left, right| {
            (Some(right.0.1) == self.source_frame)
                .cmp(&(Some(left.0.1) == self.source_frame))
                .then_with(|| {
                    right
                        .1
                        .count
                        .fraction()
                        .unwrap()
                        .total_cmp(&left.1.count.fraction().unwrap())
                })
                .then(left.0.1.cmp(&right.0.1))
        });
        let key = SpatialKey {
            level: active,
            sources: strongest
                .into_iter()
                .take(3)
                .filter_map(|(&(_, frame), evidence)| {
                    Some((frame, evidence.meta, evidence.window?))
                })
                .collect(),
        };
        if self.spatial_key.as_ref() == Some(&key) {
            return;
        }
        self.spatial.clear();
        if let Some(&(_, first_meta, window)) = key.sources.first()
            && let Some(geometry) = SampleGeometry::new(active, first_meta)
        {
            let mut cells: Vec<_> = key
                .sources
                .iter()
                .map(|&(frame, meta, _)| {
                    archive
                        .cells(active, frame)
                        .filter(|(actual, _)| {
                            *actual == meta
                                && actual.samples == first_meta.samples
                                && actual.extent == first_meta.extent
                        })
                        .map(|(_, cells)| cells)
                })
                .collect();
            let mut next = 0;
            for index in window.indices() {
                let mut sources = 0;
                for (slot, cells) in cells.iter_mut().enumerate() {
                    if let Some(cells) = cells {
                        if cells.nth(index - next) == Some(true) {
                            sources |= 1 << slot;
                        }
                        #[cfg(test)]
                        {
                            self.spatial_reads += 1;
                        }
                    }
                }
                next = index + 1;
                if sources > 0 {
                    self.spatial.push(SpatialPoint {
                        glyph: geometry.at(index).unwrap(),
                        sources,
                    });
                }
            }
        }
        self.spatial_key = Some(key);
    }

    fn paint_spatial(
        &self,
        painter: &egui::Painter,
        image: Rect,
        aperture: Rect,
        region: Rect,
        active: usize,
    ) {
        let painter = painter.with_clip_rect(painter.clip_rect().intersect(region));
        let cap = ((region.area() / 32.0) as usize).clamp(24, 768);
        let mesh = self
            .spatial_paint
            .borrow_mut()
            .mesh(self, &painter, image, aperture, cap, active);
        if !mesh.indices.is_empty() {
            painter.add(egui::Shape::Mesh(mesh));
        }
    }

    #[allow(clippy::too_many_arguments)]
    fn tooltip(
        &self,
        ctx: &egui::Context,
        width: f32,
        available_height: f32,
        region: Rect,
        active: usize,
        extent: [usize; 2],
        frames: usize,
    ) -> PopupPaint {
        self.diagnostic_tooltip(ctx, width, available_height, region, active, extent, frames)
    }
}

/// Layout text into shapes without creating widgets. In particular, the old
/// rectangle of a moving probe must never exist in egui's hit-test registry.
struct PopupPaint {
    ctx: egui::Context,
    shapes: Vec<egui::Shape>,
    width: f32,
    y: f32,
}
impl PopupPaint {
    fn new(ctx: &egui::Context, width: f32) -> Self {
        Self {
            ctx: ctx.clone(),
            shapes: Vec::new(),
            width: (width - 16.0).max(1.0),
            y: 8.0,
        }
    }
    fn label(&mut self, text: impl Into<String>, size: f32, color: Color32) {
        let galley = self.ctx.fonts_mut(|fonts| {
            fonts.layout(text.into(), FontId::proportional(size), color, self.width)
        });
        let height = galley.size().y;
        self.shapes
            .push(egui::Shape::galley(egui::pos2(8.0, self.y), galley, color));
        self.y += height + 4.0;
    }
    fn text(
        &mut self,
        at: Pos2,
        anchor: Align2,
        text: impl Into<String>,
        size: f32,
        color: Color32,
    ) {
        let galley = self
            .ctx
            .fonts_mut(|fonts| fonts.layout_no_wrap(text.into(), FontId::monospace(size), color));
        let rect = anchor.anchor_size(at, galley.size());
        self.shapes
            .push(egui::Shape::galley(rect.min, galley, color));
    }
    fn fitted(&mut self, at: Pos2, width: f32, text: impl Into<String>, size: f32, color: Color32) {
        let mut job = egui::text::LayoutJob::simple(
            text.into(),
            FontId::monospace(size),
            color,
            width.max(1.0),
        );
        job.wrap.max_rows = 1;
        job.wrap.break_anywhere = true;
        job.wrap.overflow_character = Some('…');
        let galley = self.ctx.fonts_mut(|fonts| fonts.layout_job(job));
        let origin = at - galley.rect.min.to_vec2();
        self.shapes.push(egui::Shape::galley(origin, galley, color));
    }
    fn row(&mut self, height: f32) -> Rect {
        let rect = Rect::from_min_size(egui::pos2(8.0, self.y), egui::vec2(self.width, height));
        self.y += height + 4.0;
        rect
    }
    fn line(&mut self, points: [Pos2; 2], width: f32, color: Color32) {
        self.shapes
            .push(egui::Shape::line_segment(points, Stroke::new(width, color)));
    }
}
fn region_at(image: Rect, aperture: Rect, pointer: Pos2, side: f32) -> Option<Rect> {
    if !image.is_finite()
        || !aperture.is_finite()
        || !image.contains(pointer)
        || image.size().min_elem() <= 0.0
        || aperture.size().min_elem() <= 0.0
        || !side.is_finite()
        || side <= 0.0
    {
        return None;
    }
    let screen = Rect::from_center_size(pointer, Vec2::splat(side)).intersect(image);
    let unproject = |at: Pos2| aperture.min + (at - image.min) / image.size() * aperture.size();
    Some(Rect::from_min_max(
        unproject(screen.min),
        unproject(screen.max),
    ))
}

fn popup_placement(viewport: Rect, region: Rect, desired: Vec2) -> Rect {
    let gap = 12.0;
    let right = (viewport.right() - region.right() - gap).max(0.0);
    let left = (region.left() - gap - viewport.left()).max(0.0);
    let below = (viewport.bottom() - region.bottom() - gap).max(0.0);
    let above = (region.top() - gap - viewport.top()).max(0.0);
    if right.max(left) < desired.x.min(120.0) && below.max(above) > 60.0 {
        let width = desired.x.min(viewport.width());
        let place_below = below >= above;
        let height = desired.y.min(if place_below { below } else { above });
        let x = (region.center().x - width * 0.5).clamp(viewport.left(), viewport.right() - width);
        let y = if place_below {
            region.bottom() + gap
        } else {
            region.top() - gap - height
        };
        return Rect::from_min_size(egui::pos2(x, y), egui::vec2(width, height));
    }
    let place_right = right >= desired.x || right >= left;
    let width = desired.x.min(if place_right { right } else { left });
    let height = desired.y.min(viewport.height());
    let x = if place_right {
        region.right() + gap
    } else {
        region.left() - gap - width
    }
    .clamp(
        viewport.left(),
        (viewport.right() - width).max(viewport.left()),
    );
    let y = region.top().clamp(
        viewport.top(),
        (viewport.bottom() - height).max(viewport.top()),
    );
    Rect::from_min_size(egui::pos2(x, y), egui::vec2(width, height))
}

/// Stable capture identity. It is deliberately independent of band, ranking,
/// admission fraction and current selection. The printed capture ID remains
/// the exact key even when a long stack contains similar hues.
fn capture_ink(frame: usize) -> Color32 {
    egui::ecolor::Hsva::new(
        ((frame % 4096) as f32 * 0.618_034).fract(),
        0.48,
        0.96,
        0.95,
    )
    .into()
}

#[cfg(test)]
#[path = "process-region-probe-tests.rs"]
mod tests;

#[cfg(test)]
#[path = "process-region-probe-v25-tests.rs"]
mod v25_tests;

#[cfg(test)]
#[path = "process-region-v26-tests.rs"]
mod v26_tests;
