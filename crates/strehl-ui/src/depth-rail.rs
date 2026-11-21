//! The depth rail: one bar per plane on an engraved scale (Studio 2, spec 7.2).
//!
//! A bar is the share of sampled sites whose noise gate admitted that plane at
//! the selected detail size. It is support at the gate, not a share of the
//! blend, and planes overlap. Exact counts come from a retained per-plane map;
//! otherwise from the pooled `sampled_mask_history` bin, which is coarser above
//! 1,024 planes. A plane observed at zero and a plane never observed are drawn
//! differently, so the absence of evidence never looks like an observed zero.
//!
//! Performance: the per-plane series is rebuilt only when the evidence
//! revision, the level or the plane count changes; the bars, outline, scale and
//! brackets are one cached `Arc<Mesh>` keyed on the rect, pixels per point,
//! that series and the palette. The hover marker, head and numerals are cheap
//! per-frame shapes. Pointer motion that does not change a key rebuilds nothing.
// Stage 1 builds the parts; the Stack station composes them in stage 2.
#![allow(dead_code)]

use std::{ops::Range, sync::Arc};

use eframe::egui::{
    self, Align2, Color32, FontId, Pos2, Rect, Sense, Shape, Stroke, Ui, epaint::Galley,
    text::LayoutJob,
};

use crate::{
    pipeline::{DiagnosticKind, PipelineProgress, SampledMaskHistory},
    process_provenance::AdmissionArchive,
};

/// Horizontal inset of the plane axis inside the chart, as in the mockup.
pub(crate) const PAD: f32 = 20.0;
/// Space above the tallest bar.
const TOP_GAP: f32 = 8.0;
/// The engraved scale under the baseline: ticks and numerals.
const AXIS: f32 = 19.0;
/// Planes at least this far apart get their own bar with a 1 px gap.
const BAR_PITCH: f32 = 3.0;
/// Pooled columns are never narrower than this (spec 5.2 item 9).
const COLUMN_PITCH: f32 = 2.0;
/// A dot marks each bar top when planes are at least this far apart.
const DOT_PITCH: f32 = 3.4;
/// Display heuristic for the "no subject detail" brackets: a plane whose kept
/// share is below this fraction of the busiest plane's share. UNVALIDATED: it
/// is drawn as a reading aid only and must not become a check (spec D4) until
/// it is validated on the corpus.
pub(crate) const NO_DETAIL_FRACTION: f32 = 0.03;

/// Colours the rail draws with. The Stack station passes its theme tokens;
/// integration with the shell's `Tokens` is a one-line constructor.
#[derive(Clone, Copy, Debug, PartialEq)]
pub(crate) struct RailPalette {
    pub ok: Color32,
    pub plane: Color32,
    /// Text on a plane-coloured marker.
    pub plane_ink: Color32,
    pub accent: Color32,
    /// Text on an accent marker.
    pub accent_ink: Color32,
    pub ink: Color32,
    pub ink2: Color32,
    pub ink3: Color32,
    pub line: Color32,
    pub line2: Color32,
}
impl RailPalette {
    /// Appendix A, Graphite.
    pub(crate) const GRAPHITE: Self = Self {
        ok: Color32::from_rgb(0xa9, 0xc7, 0x79),
        plane: Color32::from_rgb(0x55, 0xd6, 0xc4),
        plane_ink: Color32::from_rgb(0x04, 0x20, 0x1c),
        accent: Color32::from_rgb(0xe6, 0xb4, 0x50),
        accent_ink: Color32::from_rgb(0x17, 0x12, 0x04),
        ink: Color32::from_rgb(0xe9, 0xe6, 0xde),
        ink2: Color32::from_rgb(0xa1, 0x9f, 0x98),
        ink3: Color32::from_rgb(0x80, 0x7e, 0x77),
        line: Color32::from_rgb(0x23, 0x23, 0x26),
        line2: Color32::from_rgb(0x37, 0x37, 0x3c),
    };
}
impl Default for RailPalette {
    fn default() -> Self {
        Self::GRAPHITE
    }
}

/// Where a plane's evidence came from.
#[derive(Clone, Copy, Debug, Default, PartialEq, Eq)]
pub(crate) enum EvidenceSource {
    /// Never observed: drawn as a hatched baseline, never as a zero.
    #[default]
    Missing,
    /// The plane's own retained map: exact counts.
    Map,
    /// A `sampled_mask_history` bin; pooled above 1,024 planes.
    History,
}

#[derive(Clone, Copy, Debug, Default, PartialEq)]
pub(crate) struct PlaneEvidence {
    /// Admitted sampled sites. For a pooled history bin this is the mean per
    /// observation, so pooling several planes keeps the ratio of sums.
    pub admitted: f32,
    pub observed: f32,
    pub source: EvidenceSource,
    sequence: u64,
}
impl PlaneEvidence {
    pub(crate) fn share(self) -> Option<f32> {
        (self.observed > 0.0).then(|| self.admitted / self.observed)
    }
}

/// An O(1) key that changes whenever any diagnostic packet is ingested or the
/// run's diagnostic domain is replaced. Every binary map passes through the
/// bounded `diagnostic_surfaces` ring, so its last sequence moves even when the
/// archive is at capacity and only the history changes.
pub(crate) fn evidence_revision(progress: &PipelineProgress) -> u64 {
    let last = progress
        .diagnostic_surfaces
        .back()
        .map_or(0, |packet| packet.sequence);
    let mut key = progress.admission_archive.revision();
    for value in [
        progress.diagnostic_epoch,
        last,
        progress.diagnostic_surfaces.len() as u64,
        progress.sampled_mask_history.len() as u64,
    ] {
        key = key.rotate_left(17) ^ value.wrapping_mul(0x9e37_79b9_7f4a_7c15);
    }
    key
}

/// Positions on the rail. `plane` arguments are zero-based indices.
#[derive(Clone, Copy, Debug, PartialEq)]
pub(crate) struct RailGeometry {
    pub rect: Rect,
    pub left: f32,
    pub right: f32,
    /// Bar bottoms.
    pub base: f32,
    /// The tallest bar's top.
    pub top: f32,
    pub planes: usize,
    /// Drawn columns: one per plane, or pooled columns of at least 2 px.
    pub columns: usize,
}
impl RailGeometry {
    pub(crate) fn new(rect: Rect, planes: usize) -> Option<Self> {
        if planes == 0
            || !rect.is_finite()
            || rect.width() < 2.0 * PAD + 8.0
            || rect.height() < 40.0
        {
            return None;
        }
        let left = rect.left() + PAD;
        let right = rect.right() - PAD;
        let pitch = if planes == 1 {
            f32::INFINITY
        } else {
            (right - left) / (planes - 1) as f32
        };
        let columns = if pitch >= BAR_PITCH {
            planes
        } else {
            planes.min(((right - left) / COLUMN_PITCH).floor().max(1.0) as usize)
        };
        Some(Self {
            rect,
            left,
            right,
            base: rect.bottom() - AXIS,
            top: rect.top() + TOP_GAP,
            planes,
            columns,
        })
    }
    pub(crate) fn step(&self) -> f32 {
        if self.planes <= 1 {
            self.right - self.left
        } else {
            (self.right - self.left) / (self.planes - 1) as f32
        }
    }
    pub(crate) fn pooled(&self) -> bool {
        self.columns < self.planes
    }
    pub(crate) fn x(&self, plane: usize) -> f32 {
        if self.planes <= 1 {
            (self.left + self.right) * 0.5
        } else {
            egui::lerp(
                self.left..=self.right,
                plane.min(self.planes - 1) as f32 / (self.planes - 1) as f32,
            )
        }
    }
    /// The nearest plane, as the mockup's `planeAt`.
    pub(crate) fn plane_at(&self, x: f32) -> usize {
        if self.planes <= 1 || !x.is_finite() {
            return 0;
        }
        (((x - self.left) / (self.right - self.left)).clamp(0.0, 1.0) * (self.planes - 1) as f32)
            .round() as usize
    }
    pub(crate) fn column_range(&self, column: usize) -> Range<usize> {
        column * self.planes / self.columns..(column + 1) * self.planes / self.columns
    }
    pub(crate) fn column_of(&self, plane: usize) -> usize {
        (plane.min(self.planes - 1) * self.columns / self.planes).min(self.columns - 1)
    }
    /// A drawn column's horizontal extent, without the 1 px gap.
    fn column_span(&self, column: usize) -> [f32; 2] {
        let range = self.column_range(column);
        let half = self.step() * 0.5;
        [
            (self.x(range.start) - half).max(self.left - half.min(PAD)),
            (self.x(range.end - 1) + half).min(self.right + half.min(PAD)),
        ]
    }
    fn height(&self) -> f32 {
        (self.base - self.top).max(1.0)
    }
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
struct SeriesKey {
    revision: u64,
    level: usize,
    planes: usize,
}

#[derive(Clone, PartialEq)]
struct MeshKey {
    rect: Rect,
    pixels_per_point: f32,
    series: u64,
    palette: RailPalette,
}

struct Engraving {
    key: MeshKey,
    mesh: Arc<egui::Mesh>,
    /// Axis numerals: hidden individually under a marker, so not in the mesh.
    numerals: Vec<(Rect, Arc<Galley>)>,
    labels: Vec<(Pos2, Arc<Galley>)>,
}

/// One series for the region under the pointer (the dashed line).
#[derive(Clone, PartialEq)]
struct RegionKey {
    key: u64,
    rect: Rect,
    pixels_per_point: f32,
    palette: RailPalette,
    series: u64,
}

/// The markers drawn over the cached engraving each frame.
#[derive(Clone, Copy, Debug, Default, PartialEq, Eq)]
pub(crate) struct RailMarkers {
    /// The plane under the pointer (plane colour).
    pub hover: Option<usize>,
    /// The held plane or the core sample's leading plane (accent).
    pub head: Option<usize>,
}

#[derive(Clone, Copy, Debug, Default, PartialEq, Eq)]
pub(crate) struct RailResponse {
    pub hovered: Option<usize>,
    pub clicked: Option<usize>,
}

/// The rail model and its painter. Owns no texture and starts no work.
#[derive(Default)]
pub(crate) struct DepthRail {
    key: Option<SeriesKey>,
    planes: Vec<PlaneEvidence>,
    /// Bumped whenever a per-plane value actually changes.
    series: u64,
    peak: f32,
    brackets: Vec<Range<usize>>,
    engraving: Option<Engraving>,
    region_key: Option<u64>,
    region: Vec<Option<f32>>,
    region_series: u64,
    region_mesh: Option<(RegionKey, Arc<egui::Mesh>)>,
    #[cfg(test)]
    pub(crate) builds: RailBuilds,
}

#[cfg(test)]
#[derive(Clone, Copy, Debug, Default, PartialEq, Eq)]
pub(crate) struct RailBuilds {
    pub series: usize,
    pub counts: usize,
    pub meshes: usize,
    pub regions: usize,
}

impl DepthRail {
    /// Refresh the per-plane series. Returns whether any value changed. Call
    /// every frame: it is O(1) unless the key changed.
    pub(crate) fn update(
        &mut self,
        archive: &AdmissionArchive,
        histories: &[SampledMaskHistory],
        planes: usize,
        level: usize,
        revision: u64,
    ) -> bool {
        let key = SeriesKey {
            revision,
            level,
            planes,
        };
        if self.key == Some(key) {
            return false;
        }
        let level_changed = self.key.is_none_or(|old| old.level != level);
        self.key = Some(key);
        #[cfg(test)]
        {
            self.builds.series += 1;
        }
        if level_changed || self.planes.len() != planes {
            self.planes.clear();
            self.planes.resize(planes, PlaneEvidence::default());
        }
        let history = histories.iter().find(|history| {
            history.kind == DiagnosticKind::GateSupport
                && history.level == level
                && history.total == planes
                && !history.bins.is_empty()
        });
        let mut changed = level_changed;
        let mut maps = archive
            .frames(level)
            .filter(|&frame| frame < planes)
            .peekable();
        for plane in 0..planes {
            let has_map = maps.next_if_eq(&plane).is_some();
            let old = self.planes[plane];
            let next = if has_map && let Some(meta) = archive.metadata(level, plane) {
                if old.source == EvidenceSource::Map && old.sequence == meta.sequence {
                    old
                } else {
                    #[cfg(test)]
                    {
                        self.builds.counts += 1;
                    }
                    archive.counts(level, plane).map_or_else(
                        PlaneEvidence::default,
                        |(admitted, observed)| PlaneEvidence {
                            admitted: admitted as f32,
                            observed: observed as f32,
                            source: EvidenceSource::Map,
                            sequence: meta.sequence,
                        },
                    )
                }
            } else if let Some(history) = history {
                let bin = &history.bins[plane * history.bins.len() / planes];
                let observations = bin.observations();
                if observations == 0 || bin.samples == 0 {
                    PlaneEvidence::default()
                } else {
                    PlaneEvidence {
                        admitted: bin.on_samples as f32 / observations as f32,
                        observed: bin.samples as f32 / observations as f32,
                        source: EvidenceSource::History,
                        sequence: 0,
                    }
                }
            } else {
                PlaneEvidence::default()
            };
            if next != old {
                self.planes[plane] = next;
                changed = true;
            }
        }
        if changed {
            self.series = self.series.wrapping_add(1);
            self.peak = self
                .planes
                .iter()
                .filter_map(|plane| plane.share())
                .fold(0.0, f32::max);
            self.brackets = no_detail_runs(&self.planes, self.peak);
        }
        changed
    }

    pub(crate) fn planes(&self) -> usize {
        self.planes.len()
    }
    pub(crate) fn evidence(&self, plane: usize) -> Option<PlaneEvidence> {
        self.planes.get(plane).copied()
    }
    /// The absolute kept share, 0..1, or None when unobserved.
    pub(crate) fn share(&self, plane: usize) -> Option<f32> {
        self.planes.get(plane).and_then(|plane| plane.share())
    }
    pub(crate) fn peak(&self) -> f32 {
        self.peak
    }
    /// Runs of planes below the display threshold (zero-based, half-open).
    pub(crate) fn brackets(&self) -> &[Range<usize>] {
        &self.brackets
    }

    /// The region series (dashed line). `key` must change exactly when the
    /// sampled window or the evidence changes; `series` is read only then.
    pub(crate) fn set_region<I>(&mut self, key: Option<u64>, series: impl FnOnce() -> I)
    where
        I: IntoIterator<Item = (usize, usize, usize)>,
    {
        if self.region_key == key {
            return;
        }
        self.region_key = key;
        self.region.clear();
        if key.is_some() {
            self.region.resize(self.planes.len(), None);
            for (plane, admitted, observed) in series() {
                if let Some(slot) = self.region.get_mut(plane)
                    && observed > 0
                {
                    *slot = Some(admitted as f32 / observed as f32);
                }
            }
        }
        self.region_series = self.region_series.wrapping_add(1);
    }
    pub(crate) fn has_region(&self) -> bool {
        self.region.iter().any(Option::is_some)
    }

    /// Interaction over the chart: the nearest plane under the pointer and a
    /// click. The caller's lens state machine decides peek and hold.
    pub(crate) fn interact(&self, ui: &mut Ui, rect: Rect, id: egui::Id) -> RailResponse {
        let Some(geometry) = RailGeometry::new(rect, self.planes.len()) else {
            return RailResponse::default();
        };
        let hit = ui.interact(rect, id, Sense::click());
        let hovered = hit.hover_pos().map(|at| geometry.plane_at(at.x));
        let clicked = hit
            .clicked()
            .then(|| hit.interact_pointer_pos())
            .flatten()
            .map(|at| geometry.plane_at(at.x));
        RailResponse { hovered, clicked }
    }

    /// Paint the cached engraving, the region line, then the markers.
    pub(crate) fn paint(
        &mut self,
        painter: &egui::Painter,
        rect: Rect,
        palette: RailPalette,
        markers: RailMarkers,
    ) {
        let Some(geometry) = RailGeometry::new(rect, self.planes.len()) else {
            return;
        };
        let pixels_per_point = painter.ctx().pixels_per_point();
        let key = MeshKey {
            rect,
            pixels_per_point,
            series: self.series,
            palette,
        };
        if self
            .engraving
            .as_ref()
            .is_none_or(|cached| cached.key != key)
        {
            #[cfg(test)]
            {
                self.builds.meshes += 1;
            }
            self.engraving = Some(self.engrave(painter.ctx(), geometry, key));
        }
        let engraving = self.engraving.as_ref().expect("engraving was just built");
        painter.add(Shape::mesh(engraving.mesh.clone()));
        for (at, galley) in &engraving.labels {
            painter.galley(*at, galley.clone(), palette.ink3);
        }
        let region = RegionKey {
            key: self.region_key.unwrap_or(u64::MAX),
            rect,
            pixels_per_point,
            palette,
            series: self.region_series ^ self.series.rotate_left(32),
        };
        if self.has_region() {
            if self
                .region_mesh
                .as_ref()
                .is_none_or(|(old, _)| *old != region)
            {
                #[cfg(test)]
                {
                    self.builds.regions += 1;
                }
                let mesh = self.region_line(painter.ctx(), geometry, palette);
                self.region_mesh = Some((region, Arc::new(mesh)));
            }
            if let Some((_, mesh)) = &self.region_mesh {
                painter.add(Shape::mesh(mesh.clone()));
            }
        }
        // Numerals under a marker hide, so the marker's own number reads.
        let marked: Vec<f32> = [markers.hover, markers.head]
            .into_iter()
            .flatten()
            .filter(|&plane| plane < geometry.planes)
            .map(|plane| marker_box(geometry, plane).center().x)
            .collect();
        let engraving = self.engraving.as_ref().expect("engraving was just built");
        for (rect, galley) in &engraving.numerals {
            let reach = rect.width() * 0.5 + 18.0;
            if marked.iter().all(|x| (x - rect.center().x).abs() >= reach) {
                painter.galley(rect.min, galley.clone(), palette.ink3);
            }
        }
        if let Some(plane) = markers.head.filter(|&plane| plane < geometry.planes) {
            self.paint_marker(
                painter,
                geometry,
                plane,
                palette.accent,
                palette.accent_ink,
                true,
            );
        }
        if let Some(plane) = markers
            .hover
            .filter(|&plane| plane < geometry.planes && Some(plane) != markers.head)
        {
            self.paint_marker(
                painter,
                geometry,
                plane,
                palette.plane,
                palette.plane_ink,
                false,
            );
        }
    }

    fn bar_height(&self, geometry: RailGeometry, share: f32) -> f32 {
        if self.peak <= 0.0 {
            0.0
        } else {
            (share / self.peak).clamp(0.0, 1.0) * geometry.height()
        }
    }

    /// Pooled evidence over a column: the ratio of sums of observed planes.
    fn column_share(&self, geometry: RailGeometry, column: usize) -> Option<f32> {
        let (admitted, observed) = self.planes[geometry.column_range(column)]
            .iter()
            .filter(|plane| plane.observed > 0.0)
            .fold((0.0_f64, 0.0_f64), |(a, o), plane| {
                (a + f64::from(plane.admitted), o + f64::from(plane.observed))
            });
        (observed > 0.0).then(|| (admitted / observed) as f32)
    }

    fn engrave(&self, ctx: &egui::Context, geometry: RailGeometry, key: MeshKey) -> Engraving {
        let palette = key.palette;
        let mut mesh = egui::Mesh::default();
        let mut tessellator = egui::epaint::Tessellator::new(
            key.pixels_per_point,
            ctx.tessellation_options(|options| *options),
            ctx.fonts(|fonts| fonts.font_image_size()),
            Vec::new(),
        );
        let px = 1.0 / key.pixels_per_point;
        let hrule = |mesh: &mut egui::Mesh, y: f32, color: Color32| {
            let y = (y * key.pixels_per_point).floor() / key.pixels_per_point;
            mesh.add_colored_rect(
                Rect::from_min_max(
                    egui::pos2(geometry.left, y),
                    egui::pos2(geometry.right, y + px),
                ),
                color,
            );
        };
        // Reference lines at half and full height.
        hrule(
            &mut mesh,
            geometry.base - geometry.height() * 0.5,
            palette.line,
        );
        hrule(&mut mesh, geometry.top, palette.line);

        // Bars, or pooled columns of at least 2 px.
        let fill = palette.ok.gamma_multiply(0.6);
        let mut outline: Vec<Pos2> = Vec::new();
        let mut outlines: Vec<Vec<Pos2>> = Vec::new();
        let mut dots: Vec<Pos2> = Vec::new();
        let mut missing: Vec<[f32; 2]> = Vec::new();
        let step = geometry.step();
        for column in 0..geometry.columns {
            let [x0, x1] = if geometry.pooled() {
                geometry.column_span(column)
            } else {
                let x = geometry.x(column);
                let width = (step - 1.0).clamp(1.0, 24.0);
                [x - width * 0.5, x + width * 0.5]
            };
            let centre = (x0 + x1) * 0.5;
            let share = if geometry.pooled() {
                self.column_share(geometry, column)
            } else {
                self.planes[column].share()
            };
            match share {
                None => {
                    if let Some(last) = missing.last_mut()
                        && (x0 - last[1]).abs() <= step.max(COLUMN_PITCH) + 0.5
                    {
                        last[1] = x1;
                    } else {
                        missing.push([x0, x1]);
                    }
                    if outline.len() > 1 {
                        outlines.push(std::mem::take(&mut outline));
                    } else {
                        outline.clear();
                    }
                }
                Some(share) => {
                    let height = self.bar_height(geometry, share);
                    if share <= 0.0 {
                        // Observed zero: a 1 px baseline, never a hatch.
                        mesh.add_colored_rect(
                            Rect::from_min_max(
                                egui::pos2(x0, geometry.base - 1.0),
                                egui::pos2(x1, geometry.base),
                            ),
                            palette.line2,
                        );
                    } else {
                        let height = height.max(1.0);
                        mesh.add_colored_rect(
                            Rect::from_min_max(
                                egui::pos2(x0, geometry.base - height),
                                egui::pos2(x1, geometry.base),
                            ),
                            fill,
                        );
                        if !geometry.pooled() && step >= DOT_PITCH && height >= 0.8 {
                            dots.push(egui::pos2(centre, geometry.base - height));
                        }
                    }
                    outline.push(egui::pos2(centre, geometry.base - height.max(0.5)));
                }
            }
        }
        if outline.len() > 1 {
            outlines.push(outline);
        }
        let top = Stroke::new(1.0_f32, palette.ok.gamma_multiply(0.9));
        for points in outlines {
            tessellator.tessellate_shape(Shape::line(points, top), &mut mesh);
        }
        let dot = palette.ink.gamma_multiply(0.75);
        for at in dots {
            tessellator.tessellate_shape(Shape::circle_filled(at, 1.0, dot), &mut mesh);
        }
        // Unobserved planes: a hatched baseline segment, never a bar.
        let hatch = Stroke::new(1.0_f32, palette.line2);
        for [x0, x1] in missing {
            let mut x = x0;
            while x < x1 {
                let x2 = (x + 3.0).min(x1);
                tessellator.tessellate_shape(
                    Shape::line_segment(
                        [
                            egui::pos2(x, geometry.base),
                            egui::pos2(x2, geometry.base - 3.0),
                        ],
                        hatch,
                    ),
                    &mut mesh,
                );
                x += 4.0;
            }
        }

        // "No subject detail" brackets (a display heuristic; see the constant).
        let mut labels = Vec::new();
        let bracket = Stroke::new(1.0_f32, palette.line2);
        for run in &self.brackets {
            let a = geometry.x(run.start);
            let b = geometry.x(run.end - 1);
            let y = geometry.base - 11.0;
            tessellator.tessellate_shape(
                Shape::line(
                    vec![
                        egui::pos2(a, y),
                        egui::pos2(a, y - 4.0),
                        egui::pos2(b, y - 4.0),
                        egui::pos2(b, y),
                    ],
                    bracket,
                ),
                &mut mesh,
            );
            if b - a > 190.0 {
                let text = format!(
                    "PLANES {}\u{2013}{} \u{b7} NO SUBJECT DETAIL",
                    run.start + 1,
                    run.end
                );
                let galley = tracked(ctx, text, 10.0, palette.ink3, 1.0);
                let at = egui::pos2(
                    (a + b) * 0.5 - galley.size().x * 0.5,
                    y - 6.0 - galley.size().y,
                );
                labels.push((at, galley));
            }
        }

        // The engraved scale: baseline, ticks, numerals, NEAR and FAR.
        hrule(&mut mesh, geometry.base, palette.line2);
        let (minor, major) = scale_intervals(geometry);
        let mut numerals = Vec::new();
        let near = tracked(ctx, "NEAR".into(), 10.0, palette.ink3, 1.2);
        let far = tracked(ctx, "FAR".into(), 10.0, palette.ink3, 1.2);
        let label_y = geometry.rect.bottom() - 1.0;
        let near_rect =
            Align2::LEFT_BOTTOM.anchor_size(egui::pos2(geometry.left, label_y), near.size());
        let far_rect =
            Align2::RIGHT_BOTTOM.anchor_size(egui::pos2(geometry.right, label_y), far.size());
        let mut number = minor;
        while number <= geometry.planes {
            let x = (geometry.x(number - 1) * key.pixels_per_point).floor() / key.pixels_per_point;
            let is_major = number % major == 0;
            mesh.add_colored_rect(
                Rect::from_min_max(
                    egui::pos2(x, geometry.base),
                    egui::pos2(x + px, geometry.base + if is_major { 6.0 } else { 3.0 }),
                ),
                if is_major {
                    palette.ink3
                } else {
                    palette.line2
                },
            );
            if is_major {
                let galley = tracked(ctx, number.to_string(), 10.0, palette.ink3, 0.4);
                let rect = Align2::CENTER_BOTTOM.anchor_size(egui::pos2(x, label_y), galley.size());
                if !rect.expand(6.0).intersects(near_rect) && !rect.expand(6.0).intersects(far_rect)
                {
                    numerals.push((rect, galley));
                }
            }
            number += minor;
        }
        numerals.push((near_rect, near));
        numerals.push((far_rect, far));
        Engraving {
            key,
            mesh: Arc::new(mesh),
            numerals,
            labels,
        }
    }

    fn region_line(
        &self,
        ctx: &egui::Context,
        geometry: RailGeometry,
        palette: RailPalette,
    ) -> egui::Mesh {
        let mut mesh = egui::Mesh::default();
        let mut tessellator = egui::epaint::Tessellator::new(
            ctx.pixels_per_point(),
            ctx.tessellation_options(|options| *options),
            ctx.fonts(|fonts| fonts.font_image_size()),
            Vec::new(),
        );
        let pooled = |column: usize| -> Option<f32> {
            let values: Vec<f32> = self.region[geometry.column_range(column)]
                .iter()
                .flatten()
                .copied()
                .collect();
            (!values.is_empty()).then(|| values.iter().sum::<f32>() / values.len() as f32)
        };
        let values: Vec<Option<f32>> = (0..geometry.columns)
            .map(|column| {
                if geometry.pooled() {
                    pooled(column)
                } else {
                    self.region.get(column).copied().flatten()
                }
            })
            .collect();
        let peak = values.iter().flatten().copied().fold(0.0, f32::max);
        if peak <= 0.0 {
            return mesh;
        }
        let x = |column: usize| {
            if geometry.pooled() {
                let [a, b] = geometry.column_span(column);
                (a + b) * 0.5
            } else {
                geometry.x(column)
            }
        };
        let mut runs: Vec<Vec<Pos2>> = vec![Vec::new()];
        let mut dots = Vec::new();
        for (column, value) in values.iter().enumerate() {
            match value {
                Some(value) => {
                    let normal = value / peak;
                    let at =
                        egui::pos2(x(column), geometry.base - normal * geometry.height() * 0.96);
                    runs.last_mut().unwrap().push(at);
                    if normal > 0.04 {
                        dots.push(at);
                    }
                }
                None => runs.push(Vec::new()),
            }
        }
        let stroke = Stroke::new(1.3_f32, palette.accent);
        for run in runs.into_iter().filter(|run| run.len() > 1) {
            for shape in Shape::dashed_line(&run, stroke, 4.0, 3.0) {
                tessellator.tessellate_shape(shape, &mut mesh);
            }
        }
        // Dots only where they stay distinct; dense stacks keep the line.
        let spacing = if geometry.pooled() {
            COLUMN_PITCH
        } else {
            geometry.step()
        };
        if spacing >= DOT_PITCH {
            for at in dots {
                tessellator
                    .tessellate_shape(Shape::circle_filled(at, 1.3, palette.accent), &mut mesh);
            }
        }
        mesh
    }

    fn paint_marker(
        &self,
        painter: &egui::Painter,
        geometry: RailGeometry,
        plane: usize,
        color: Color32,
        ink: Color32,
        head: bool,
    ) {
        let x = geometry.x(plane);
        let top = if head {
            geometry.top - 4.0
        } else {
            geometry.rect.top() + 2.0
        };
        painter.line_segment(
            [egui::pos2(x, top), egui::pos2(x, geometry.base + 6.0)],
            Stroke::new(1.0_f32, color),
        );
        if head && let Some(share) = self.share(plane) {
            let y = geometry.base - self.bar_height(geometry, share);
            painter.circle_filled(egui::pos2(x, y), 2.6, color);
        }
        let label = marker_box(geometry, plane);
        painter.rect_filled(label, 0.0, color);
        painter.text(
            egui::pos2(
                x.clamp(geometry.rect.left() + 15.0, geometry.rect.right() - 15.0),
                label.center().y,
            ),
            Align2::CENTER_CENTER,
            (plane + 1).to_string(),
            FontId::proportional(10.0),
            ink,
        );
    }
}

/// The 30 × 13 marker label under the scale.
fn marker_box(geometry: RailGeometry, plane: usize) -> Rect {
    let x = geometry.x(plane);
    let left = (x - 15.0).clamp(geometry.rect.left(), geometry.rect.right() - 30.0);
    Rect::from_min_size(
        egui::pos2(left, geometry.rect.bottom() - 13.0),
        egui::vec2(30.0, 13.0),
    )
}

/// Tick and numeral intervals in planes. At 299 planes on 1,332 px these are
/// the mockup's 5 and 25; long stacks thin both so neither ever crowds.
pub(crate) fn scale_intervals(geometry: RailGeometry) -> (usize, usize) {
    let step = geometry.step();
    let minor = [5, 10, 25, 50, 100, 250, 500, 1000, 2500, 5000]
        .into_iter()
        .find(|&interval| interval as f32 * step >= 4.0)
        .unwrap_or(10_000);
    let major = [25, 50, 100, 250, 500, 1000, 2500, 5000, 10_000]
        .into_iter()
        .find(|&interval| interval % minor == 0 && interval as f32 * step >= 44.0)
        .unwrap_or(minor * 10);
    (minor, major)
}

/// Runs of observed planes whose kept share is under the display threshold.
/// Unobserved planes end a run: missing evidence is never "no detail".
fn no_detail_runs(planes: &[PlaneEvidence], peak: f32) -> Vec<Range<usize>> {
    if peak <= 0.0 {
        return Vec::new();
    }
    let minimum = (planes.len() / 40).max(3);
    let mut runs = Vec::new();
    let mut start = None;
    for (index, plane) in planes.iter().enumerate() {
        let low = plane
            .share()
            .is_some_and(|share| share < peak * NO_DETAIL_FRACTION);
        match (low, start) {
            (true, None) => start = Some(index),
            (false, Some(from)) => {
                if index - from >= minimum {
                    runs.push(from..index);
                }
                start = None;
            }
            _ => {}
        }
    }
    if let Some(from) = start
        && planes.len() - from >= minimum
    {
        runs.push(from..planes.len());
    }
    runs
}

/// Tracked capitals or numerals (letter spacing in points).
pub(crate) fn tracked(
    ctx: &egui::Context,
    text: String,
    size: f32,
    color: Color32,
    spacing: f32,
) -> Arc<Galley> {
    let job = LayoutJob::single_section(
        text,
        egui::TextFormat {
            font_id: FontId::proportional(size),
            color,
            extra_letter_spacing: spacing,
            ..Default::default()
        },
    );
    ctx.fonts_mut(|fonts| fonts.layout_job(job))
}

/// The rail head: title, plane count, keys and the reading on the right.
pub(crate) struct RailHead<'a> {
    pub planes: usize,
    pub step: Option<&'a str>,
    pub reading: &'a str,
}

pub(crate) fn paint_head(
    painter: &egui::Painter,
    rect: Rect,
    palette: RailPalette,
    head: &RailHead<'_>,
) {
    let ctx = painter.ctx();
    let y = rect.center().y;
    let title = tracked(ctx, "DEPTH RAIL".into(), 10.5, palette.ink, 1.4);
    let mut x = rect.left() + 14.0;
    painter.galley(
        egui::pos2(x, y - title.size().y * 0.5),
        title.clone(),
        palette.ink,
    );
    x += title.size().x + 16.0;
    let count = match head.step {
        Some(step) => format!("{} planes \u{b7} step {step}", head.planes),
        None => format!("{} planes", head.planes),
    };
    let font = FontId::proportional(12.0);
    let galley = painter.layout_no_wrap(count, font.clone(), palette.ink2);
    painter.galley(
        egui::pos2(x, y - galley.size().y * 0.5),
        galley.clone(),
        palette.ink2,
    );
    x += galley.size().x + 16.0;
    let reading = painter.layout_no_wrap(head.reading.to_owned(), font.clone(), palette.ink2);
    let reading_left = rect.right() - 14.0 - reading.size().x;
    for (key, text) in [
        (0, "detail held by each plane"),
        (1, "detail in the region under the pointer"),
        (2, "plane under the pointer"),
    ] {
        let galley = painter.layout_no_wrap(text.to_owned(), font.clone(), palette.ink2);
        if x + 22.0 + galley.size().x > reading_left - 16.0 {
            break;
        }
        match key {
            0 => {
                for bar in 0..4 {
                    painter.rect_filled(
                        Rect::from_min_size(
                            egui::pos2(x + bar as f32 * 3.0, y - 3.0),
                            egui::vec2(2.0, 7.0),
                        ),
                        0.0,
                        palette.ok.gamma_multiply(0.8),
                    );
                }
            }
            1 => {
                for dash in 0..3 {
                    let x0 = x + dash as f32 * 5.0;
                    painter.line_segment(
                        [egui::pos2(x0, y), egui::pos2(x0 + 3.0, y)],
                        Stroke::new(1.3_f32, palette.accent),
                    );
                }
            }
            _ => {
                painter.line_segment(
                    [egui::pos2(x, y), egui::pos2(x + 13.0, y)],
                    Stroke::new(1.5_f32, palette.plane),
                );
            }
        }
        x += 20.0;
        painter.galley(
            egui::pos2(x, y - galley.size().y * 0.5),
            galley.clone(),
            palette.ink2,
        );
        x += galley.size().x + 16.0;
    }
    painter.galley(
        egui::pos2(reading_left, y - reading.size().y * 0.5),
        reading,
        palette.ink2,
    );
}

#[cfg(test)]
#[path = "depth-rail-tests.rs"]
mod tests;
