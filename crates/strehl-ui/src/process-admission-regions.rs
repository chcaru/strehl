//! Coherent *estimates* of dense sampled admission. These contours are a
//! display summary of sparse binary observations, never a merge-weight map.
//! Missing packets and mismatched domains produce no region. Within a packet,
//! recorded zeros remain evidence: sufficiently resolved holes survive the
//! local density filter, and disconnected islands are not joined by a hull.
//! Final-photo coordinates require the caller's OutputSpace certificate;
//! direct source-photo overlays must use the explicitly approximate painter.

use crate::{
    process_participation::SelectionSpan,
    process_provenance::{AdmissionArchive, AdmissionMeta},
    process_sample_glyphs::SampleGeometry,
};
use eframe::egui::{self, Color32, Painter, Pos2, Rect, Stroke};
use std::{
    collections::{HashMap, VecDeque},
    sync::Arc,
};

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(crate) struct RegionSettings {
    pub enabled: bool,
    /// Local admission percentage. This is a visualization threshold, not an
    /// engine setting. Seed evidence must exceed it by another 20 points.
    pub threshold: u8,
}
impl Default for RegionSettings {
    fn default() -> Self {
        Self {
            enabled: true,
            threshold: 60,
        }
    }
}
impl RegionSettings {
    pub(crate) fn read(ctx: &egui::Context) -> Self {
        ctx.data(|data| data.get_temp(egui::Id::new("dense-admission-region-settings")))
            .unwrap_or_default()
    }
    pub(crate) fn write(self, ctx: &egui::Context) {
        let settings = Self {
            threshold: self.threshold.clamp(35, 85),
            ..self
        };
        ctx.data_mut(|data| {
            data.insert_temp(egui::Id::new("dense-admission-region-settings"), settings)
        });
        ctx.request_repaint();
    }
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
struct Key {
    domain: [u64; 2],
    frame: usize,
    level: usize,
    meta: Option<AdmissionMeta>,
    extent: [usize; 2],
    settings: RegionSettings,
}

/// A bounded multi-source cache, so back-and-forth scrubbing does not repeat
/// morphology or contour extraction. Unrelated arriving packets do not evict
/// an unchanged source receipt.
#[derive(Default)]
pub(crate) struct DenseAdmissionCache {
    entries: VecDeque<(Key, Option<Arc<DenseRegion>>)>,
    selections: VecDeque<(SelectionKey, Option<Arc<DenseSelection>>)>,
    last_selection: Option<(SelectionRequest, u64, Option<Arc<DenseSelection>>)>,
    comparisons: VecDeque<ComparisonEntry>,
    #[cfg(test)]
    builds: usize,
    #[cfg(test)]
    selection_builds: usize,
    #[cfg(test)]
    selection_scans: usize,
    #[cfg(test)]
    comparison_builds: usize,
}
impl DenseAdmissionCache {
    pub(crate) fn region(
        &mut self,
        archive: &AdmissionArchive,
        domain: [u64; 2],
        frame: usize,
        level: usize,
        extent: [usize; 2],
        settings: RegionSettings,
    ) -> Option<Arc<DenseRegion>> {
        if !settings.enabled {
            return None;
        }
        let key = Key {
            domain,
            frame,
            level,
            extent,
            meta: archive.metadata(level, frame),
            settings: RegionSettings {
                threshold: settings.threshold.clamp(35, 85),
                ..settings
            },
        };
        if let Some(index) = self.entries.iter().position(|(entry, _)| *entry == key) {
            let entry = self.entries.remove(index).unwrap();
            let region = entry.1.clone();
            self.entries.push_back(entry);
            return region;
        }
        let region = archive
            .cells(level, frame)
            .filter(|(meta, _)| meta.extent == extent)
            .and_then(|(meta, cells)| {
                let geometry = SampleGeometry::new(level, meta)?;
                DenseRegion::extract(meta, geometry, &cells.collect::<Vec<_>>(), key.settings)
            })
            .map(Arc::new);
        #[cfg(test)]
        {
            self.builds += 1;
        }
        if self.entries.len() == 32 {
            self.entries.pop_front();
        }
        self.entries.push_back((key, region.clone()));
        region
    }

    /// Each interval is the union of its recorded admission samples, followed
    /// by the same coherent density filter as a single frame. Missing packets
    /// contribute no evidence; layer counts expose that partial coverage.
    pub(crate) fn selection(
        &mut self,
        archive: &AdmissionArchive,
        domain: [u64; 2],
        spans: &[SelectionSpan],
        level: usize,
        extent: [usize; 2],
        settings: RegionSettings,
    ) -> Option<Arc<DenseSelection>> {
        if !settings.enabled
            || spans.is_empty()
            || spans
                .iter()
                .any(|span| span.start > span.end || span.end >= 65_536)
        {
            return None;
        }
        let request = SelectionRequest {
            domain,
            spans: spans.to_vec(),
            level,
            extent,
            settings: RegionSettings {
                threshold: settings.threshold.clamp(35, 85),
                ..settings
            },
        };
        let revision = archive.revision();
        if let Some((previous, previous_revision, selection)) = &self.last_selection
            && *previous == request
            && *previous_revision == revision
        {
            return selection.clone();
        }
        #[cfg(test)]
        {
            self.selection_scans += 1;
        }
        let receipts = archive
            .frames(level)
            .filter(|&frame| spans.iter().any(|span| span.contains(frame)))
            .filter_map(|frame| archive.metadata(level, frame).map(|meta| (frame, meta)))
            .collect();
        let key = SelectionKey {
            request: request.clone(),
            receipts,
        };
        let selection =
            if let Some(index) = self.selections.iter().position(|(entry, _)| *entry == key) {
                let entry = self.selections.remove(index).unwrap();
                let selection = entry.1.clone();
                self.selections.push_back(entry);
                selection
            } else {
                #[cfg(test)]
                {
                    self.selection_builds += 1;
                }
                let selection = DenseSelection::extract(archive, &key).map(Arc::new);
                if self.selections.len() == 4 {
                    self.selections.pop_front();
                }
                self.selections.push_back((key, selection.clone()));
                selection
            };
        self.last_selection = Some((request, revision, selection.clone()));
        selection
    }

    /// Keep pinned unions independent of the moving current capture. Scrubbing
    /// reads only that capture's receipt; pinned samples and density fields are
    /// reused. A current frame inside a pinned interval still has its own role.
    #[allow(clippy::too_many_arguments)] // Same cache identity inputs as selection/region, plus the current capture.
    pub(crate) fn selection_with_current(
        &mut self,
        archive: &AdmissionArchive,
        domain: [u64; 2],
        spans: &[SelectionSpan],
        current: Option<usize>,
        level: usize,
        extent: [usize; 2],
        settings: RegionSettings,
    ) -> Option<Arc<DenseSelection>> {
        let pinned = self.selection(archive, domain, spans, level, extent, settings);
        let Some(frame) = current else {
            return pinned;
        };
        let Some(region) = self.region(archive, domain, frame, level, extent, settings) else {
            return pinned;
        };
        let meta = archive.metadata(level, frame)?;
        if pinned.as_ref().is_some_and(|selection| {
            selection.meta.samples != meta.samples || selection.meta.extent != meta.extent
        }) {
            return pinned;
        }
        if let Some(index) = self.comparisons.iter().position(|entry| {
            entry.frame == frame
                && Arc::ptr_eq(&entry.current, &region)
                && match (&entry.pinned, &pinned) {
                    (Some(a), Some(b)) => Arc::ptr_eq(a, b),
                    (None, None) => true,
                    _ => false,
                }
        }) {
            let entry = self.comparisons.remove(index).unwrap();
            let selection = entry.selection.clone();
            self.comparisons.push_back(entry);
            return Some(selection);
        }
        let mut layers = pinned
            .as_ref()
            .map_or_else(Vec::new, |selection| selection.layers.clone());
        layers.push(DenseSelectionLayer {
            span: SelectionSpan {
                start: frame,
                end: frame,
                id: usize::MAX,
            },
            region: region.clone(),
            recorded_frames: 1,
            requested_frames: 1,
        });
        let selection = Arc::new(DenseSelection::from_layers(layers, level, meta)?);
        #[cfg(test)]
        {
            self.comparison_builds += 1;
        }
        if self.comparisons.len() == 8 {
            self.comparisons.pop_front();
        }
        self.comparisons.push_back(ComparisonEntry {
            pinned,
            current: region,
            frame,
            selection: selection.clone(),
        });
        Some(selection)
    }
}

struct ComparisonEntry {
    pinned: Option<Arc<DenseSelection>>,
    current: Arc<DenseRegion>,
    frame: usize,
    selection: Arc<DenseSelection>,
}

#[derive(Clone, PartialEq, Eq)]
struct SelectionRequest {
    domain: [u64; 2],
    spans: Vec<SelectionSpan>,
    level: usize,
    extent: [usize; 2],
    settings: RegionSettings,
}
#[derive(PartialEq, Eq)]
struct SelectionKey {
    request: SelectionRequest,
    receipts: Vec<(usize, AdmissionMeta)>,
}

#[derive(Clone)]
pub(crate) struct DenseSelectionLayer {
    pub span: SelectionSpan,
    pub region: Arc<DenseRegion>,
    pub recorded_frames: usize,
    pub requested_frames: usize,
}
impl DenseSelectionLayer {
    pub(crate) fn is_current(&self) -> bool {
        self.span.id == usize::MAX
    }
    pub(crate) fn label(&self) -> String {
        if self.is_current() {
            format!("CURRENT {:03}", self.span.start + 1)
        } else {
            self.span.label()
        }
    }
}
pub(crate) struct DenseSelection {
    pub layers: Vec<DenseSelectionLayer>,
    meta: AdmissionMeta,
    colors: Vec<Color32>,
    patches: Vec<SelectionPatch>,
}
struct SelectionPatch {
    membership: Membership,
    points: Vec<Pos2>,
}

/// Most selections need only the inline word. Unbounded interval editing can
/// create more independent identities; overflow preserves them instead of
/// making all regions disappear at a fixed bit limit.
#[derive(Clone, Default)]
struct Membership {
    inline: u64,
    overflow: Vec<u64>,
}
impl Membership {
    fn contains(&self, index: usize) -> bool {
        if index < 64 {
            self.inline & (1 << index) != 0
        } else {
            self.overflow
                .get(index / 64 - 1)
                .is_some_and(|word| word & (1 << (index % 64)) != 0)
        }
    }
    fn insert(&mut self, index: usize) {
        if index < 64 {
            self.inline |= 1 << index;
        } else {
            self.overflow.resize(self.overflow.len().max(index / 64), 0);
            self.overflow[index / 64 - 1] |= 1 << (index % 64);
        }
    }
    fn is_empty(&self) -> bool {
        self.inline == 0 && self.overflow.iter().all(|&word| word == 0)
    }
}

impl DenseSelection {
    pub(crate) fn is_empty(&self) -> bool {
        self.patches.is_empty()
    }

    fn extract(archive: &AdmissionArchive, key: &SelectionKey) -> Option<Self> {
        let request = &key.request;
        let meta = key.receipts.first()?.1;
        if meta.extent != request.extent
            || key.receipts.iter().any(|(_, candidate)| {
                candidate.extent != meta.extent || candidate.samples != meta.samples
            })
        {
            return None;
        }
        let mut layers = Vec::new();
        for &span in &request.spans {
            let mut union = vec![false; meta.samples[0] * meta.samples[1]];
            let mut recorded_frames = 0;
            for &(frame, _) in &key.receipts {
                if !span.contains(frame) {
                    continue;
                }
                let (_, cells) = archive.cells(request.level, frame)?;
                for (admitted, cell) in union.iter_mut().zip(cells) {
                    *admitted |= cell;
                }
                recorded_frames += 1;
            }
            if recorded_frames == 0 {
                continue;
            }
            let geometry = SampleGeometry::new(request.level, meta)?;
            let region = Arc::new(DenseRegion::extract(
                meta,
                geometry,
                &union,
                request.settings,
            )?);
            layers.push(DenseSelectionLayer {
                span,
                region,
                recorded_frames,
                requested_frames: span.len(),
            });
        }
        Self::from_layers(layers, request.level, meta)
    }

    fn from_layers(
        layers: Vec<DenseSelectionLayer>,
        level: usize,
        meta: AdmissionMeta,
    ) -> Option<Self> {
        let geometry = SampleGeometry::new(level, meta)?;
        let mut identities = Vec::new();
        let mut colors = Vec::new();
        for layer in &layers {
            if !identities.contains(&layer.span.id) {
                identities.push(layer.span.id);
                colors.push(layer.span.color());
            }
        }
        // Identity is independent of its presentation color. Fragments of one
        // interval share a bit, but even an accidental palette collision must
        // not turn two independently selected ranges into one contributor.
        let patches = partition_selection(&layers, &identities, meta.samples, geometry)?;
        Some(Self {
            layers,
            meta,
            colors,
            patches,
        })
    }
}

pub(crate) struct DenseRegion {
    pub admitted: usize,
    pub observed: usize,
    /// Coherent islands retained by the seeded density filter.
    pub islands: usize,
    vertices: Vec<Pos2>,
    indices: Vec<u32>,
    contours: Vec<Vec<Pos2>>,
    // Signed values retain the exact piecewise-linear boundary used by the
    // mesh, so selection intersections do not approximate it with a new grid.
    signed: Vec<f32>,
    #[cfg(test)]
    retained: Vec<bool>,
}

impl DenseRegion {
    fn extract(
        meta: AdmissionMeta,
        geometry: SampleGeometry,
        samples: &[bool],
        settings: RegionSettings,
    ) -> Option<Self> {
        let [width, height] = meta.samples;
        if width < 3 || height < 3 || samples.len() != width * height {
            return None;
        }
        let density = density(samples, width, height);
        let threshold = settings.threshold as f32 * 0.01;
        let seed = (threshold + 0.20).min(0.97);
        let (retained, islands) = coherent(&density, samples, width, height, threshold, seed);
        let mut out = Self {
            admitted: samples.iter().filter(|&&yes| yes).count(),
            observed: samples.len(),
            islands,
            vertices: Vec::new(),
            indices: Vec::new(),
            contours: Vec::new(),
            signed: density
                .iter()
                .zip(&retained)
                .map(|(&value, &keep)| {
                    if keep {
                        (value - threshold).max(0.001)
                    } else {
                        (value - threshold).min(-0.001)
                    }
                })
                .collect(),
            #[cfg(test)]
            retained: retained.clone(),
        };
        if islands == 0 {
            return Some(out);
        }
        // Extend the observed edge density to the image border. Coordinates
        // in the interior are the *actual* sampled coefficient centers, not
        // evenly spaced invented final-photo pixels.
        let columns = width + 2;
        let rows = height + 2;
        let mut values = Vec::with_capacity(columns * rows);
        for y in 0..rows {
            for x in 0..columns {
                let sx = x.saturating_sub(1).min(width - 1);
                let sy = y.saturating_sub(1).min(height - 1);
                let index = sy * width + sx;
                let mut point = geometry.at(index)?.center;
                if x == 0 {
                    point.x = 0.0;
                } else if x == columns - 1 {
                    point.x = 1.0;
                }
                if y == 0 {
                    point.y = 0.0;
                } else if y == rows - 1 {
                    point.y = 1.0;
                }
                out.vertices.push(point);
                values.push(out.signed[index]);
            }
        }
        let mut intersections = HashMap::new();
        let mut boundary = Vec::new();
        for y in 0..rows - 1 {
            for x in 0..columns - 1 {
                let a = y * columns + x;
                let corners = [a, a + 1, a + columns + 1, a + columns];
                let signs = corners.map(|index| values[index] >= 0.0);
                if signs[0] == signs[2] && signs[1] == signs[3] && signs[0] != signs[1] {
                    // A saddle must respect the four-connected component
                    // rule. A fixed diagonal would invent a positive bridge.
                    let center = out.vertices.len();
                    out.vertices
                        .push(out.vertices[a].lerp(out.vertices[a + columns + 1], 0.5));
                    // Intersections have already appended vertices, so values
                    // must share the same index domain as all mesh vertices.
                    values.resize(center, 0.0);
                    values.push(-0.001);
                    for edge in 0..4 {
                        out.triangle(
                            [corners[edge], corners[(edge + 1) % 4], center],
                            &values,
                            &mut intersections,
                            &mut boundary,
                        );
                    }
                } else {
                    for triangle in [
                        [a, a + 1, a + columns + 1],
                        [a, a + columns + 1, a + columns],
                    ] {
                        out.triangle(triangle, &values, &mut intersections, &mut boundary);
                    }
                }
            }
        }
        // The clipping rectangle is also part of the contour, including a
        // full-domain positive field whose interior has no zero crossing.
        for x in 0..columns - 1 {
            out.border([x, x + 1], &values, &mut intersections, &mut boundary);
            let a = (rows - 1) * columns + x;
            out.border([a, a + 1], &values, &mut intersections, &mut boundary);
        }
        for y in 0..rows - 1 {
            let a = y * columns;
            out.border([a, a + columns], &values, &mut intersections, &mut boundary);
            let a = a + columns - 1;
            out.border([a, a + columns], &values, &mut intersections, &mut boundary);
        }
        out.contours = trace_contours(&out.vertices, &boundary);
        out.compact_vertices();
        Some(out)
    }

    /// Contours already own their positions. Keep only fill vertices so each
    /// subsequent projection copies the retained region, not the whole grid.
    fn compact_vertices(&mut self) {
        let mut remap = vec![u32::MAX; self.vertices.len()];
        for &index in &self.indices {
            remap[index as usize] = 0;
        }
        let mut count = 0;
        for (original, mapped) in remap.iter_mut().enumerate() {
            if *mapped != u32::MAX {
                *mapped = count as u32;
                self.vertices[count] = self.vertices[original];
                count += 1;
            }
        }
        self.vertices.truncate(count);
        self.vertices.shrink_to_fit();
        for index in &mut self.indices {
            *index = remap[*index as usize];
        }
    }

    fn crossing(
        &mut self,
        a: usize,
        b: usize,
        values: &[f32],
        intersections: &mut HashMap<(usize, usize), u32>,
    ) -> u32 {
        *intersections
            .entry((a.min(b), a.max(b)))
            .or_insert_with(|| {
                let t = values[a] / (values[a] - values[b]);
                let point = self.vertices[a].lerp(self.vertices[b], t);
                let index = self.vertices.len() as u32;
                self.vertices.push(point);
                index
            })
    }

    fn border(
        &mut self,
        [a, b]: [usize; 2],
        values: &[f32],
        intersections: &mut HashMap<(usize, usize), u32>,
        boundary: &mut Vec<[u32; 2]>,
    ) {
        match (values[a] >= 0.0, values[b] >= 0.0) {
            (true, true) => boundary.push([a as u32, b as u32]),
            (true, false) => {
                let cross = self.crossing(a, b, values, intersections);
                boundary.push([a as u32, cross]);
            }
            (false, true) => {
                let cross = self.crossing(a, b, values, intersections);
                boundary.push([cross, b as u32]);
            }
            (false, false) => {}
        }
    }

    fn triangle(
        &mut self,
        triangle: [usize; 3],
        values: &[f32],
        intersections: &mut HashMap<(usize, usize), u32>,
        boundary: &mut Vec<[u32; 2]>,
    ) {
        let mut polygon = [0u32; 4];
        let mut count = 0;
        let mut contour = [0u32; 2];
        let mut boundary_count = 0;
        for edge in 0..3 {
            let a = triangle[edge];
            let b = triangle[(edge + 1) % 3];
            if values[a] >= 0.0 {
                polygon[count] = a as u32;
                count += 1;
            }
            if (values[a] >= 0.0) != (values[b] >= 0.0) {
                let index = self.crossing(a, b, values, intersections);
                polygon[count] = index;
                count += 1;
                contour[boundary_count] = index;
                boundary_count += 1;
            }
        }
        for index in 1..count.saturating_sub(1) {
            self.indices
                .extend_from_slice(&[polygon[0], polygon[index], polygon[index + 1]]);
        }
        if boundary_count == 2 {
            boundary.push(contour);
        }
    }

    pub(crate) fn is_empty(&self) -> bool {
        self.indices.is_empty()
    }
}

/// Stitch the triangle and image-boundary edges into closed contours. Keep
/// separate loops: filling their hull would incorrectly paint holes and gaps.
fn trace_contours(vertices: &[Pos2], edges: &[[u32; 2]]) -> Vec<Vec<Pos2>> {
    let mut adjacent = vec![Vec::new(); vertices.len()];
    for (index, &[a, b]) in edges.iter().enumerate() {
        adjacent[a as usize].push(index);
        adjacent[b as usize].push(index);
    }
    let mut seen = vec![false; edges.len()];
    let mut contours = Vec::new();
    for start in 0..edges.len() {
        if seen[start] {
            continue;
        }
        let first = edges[start][0];
        let mut current = first;
        let mut edge = start;
        let mut points = vec![vertices[first as usize]];
        loop {
            seen[edge] = true;
            let [a, b] = edges[edge];
            current = if current == a { b } else { a };
            points.push(vertices[current as usize]);
            if current == first {
                break;
            }
            let Some(next) = adjacent[current as usize]
                .iter()
                .copied()
                .find(|&next| !seen[next])
            else {
                break;
            };
            edge = next;
        }
        contours.push(points);
    }
    contours
}

/// Binomial smoothing is bounded to the observed sample lattice. A single
/// positive in a negative field never reaches even the lowest allowed cutoff.
fn density(samples: &[bool], width: usize, height: usize) -> Vec<f32> {
    let weights = [1u32, 4, 6, 4, 1];
    let mut out = vec![0.0; samples.len()];
    for y in 0..height {
        for x in 0..width {
            let mut sum = 0u32;
            let mut weight = 0u32;
            for (dy, wy) in weights.iter().enumerate() {
                let iy = y as isize + dy as isize - 2;
                if !(0..height as isize).contains(&iy) {
                    continue;
                }
                for (dx, wx) in weights.iter().enumerate() {
                    let ix = x as isize + dx as isize - 2;
                    if !(0..width as isize).contains(&ix) {
                        continue;
                    }
                    let w = wx * wy;
                    weight += w;
                    sum += w * u32::from(samples[iy as usize * width + ix as usize]);
                }
            }
            out[y * width + x] = sum as f32 / weight as f32;
        }
    }
    out
}

fn coherent(
    density: &[f32],
    samples: &[bool],
    width: usize,
    height: usize,
    threshold: f32,
    seed: f32,
) -> (Vec<bool>, usize) {
    let mut visited = vec![false; samples.len()];
    let mut retained = vec![false; samples.len()];
    let mut island = Vec::new();
    let mut islands = 0;
    for start in 0..samples.len() {
        if visited[start] || density[start] < threshold {
            continue;
        }
        visited[start] = true;
        island.clear();
        island.push(start);
        let mut cursor = 0;
        let mut seeds = 0;
        let mut positives = 0;
        while cursor < island.len() {
            let index = island[cursor];
            cursor += 1;
            seeds += usize::from(density[index] >= seed);
            positives += usize::from(samples[index]);
            let x = index % width;
            let y = index / width;
            for next in [
                (x > 0).then(|| index - 1),
                (x + 1 < width).then_some(index + 1),
                (y > 0).then(|| index - width),
                (y + 1 < height).then_some(index + width),
            ]
            .into_iter()
            .flatten()
            {
                if !visited[next] && density[next] >= threshold {
                    visited[next] = true;
                    island.push(next);
                }
            }
        }
        // Explicit evidence floors stop isolated samples and tiny chance
        // clusters becoming an apparent in-focus surface.
        if island.len() >= 12 && seeds >= 2 && positives >= 8 {
            islands += 1;
            for &index in &island {
                retained[index] = true;
            }
        }
    }
    (retained, islands)
}

#[derive(Clone, Copy)]
struct CutVertex {
    // Keep all cuts in the original triangle's coordinates. Rounding UVs at
    // each cut can turn coincident boundaries into a false exclusive sliver.
    weights: [f64; 3],
}
impl CutVertex {
    fn point(self, triangle: [Pos2; 3]) -> Pos2 {
        let coordinate = |axis| {
            self.weights
                .iter()
                .zip(triangle)
                .map(|(&weight, point)| weight * f64::from(point[axis]))
                .sum::<f64>() as f32
        };
        egui::pos2(coordinate(0), coordinate(1))
    }
}

/// Partition a shared lattice triangle by each layer's linear boundary. The
/// resulting convex pieces have one exact membership mask: no alpha stacking,
/// hull filling, or hatch outside intersections. Four triangles around a cell
/// center reproduce the single-region diagonal, including its negative saddle.
fn partition_selection(
    layers: &[DenseSelectionLayer],
    identities: &[usize],
    [width, height]: [usize; 2],
    geometry: SampleGeometry,
) -> Option<Vec<SelectionPatch>> {
    let columns = width + 2;
    let rows = height + 2;
    let mut lattice = Vec::with_capacity(columns * rows);
    for y in 0..rows {
        for x in 0..columns {
            let index =
                y.saturating_sub(1).min(height - 1) * width + x.saturating_sub(1).min(width - 1);
            let mut point = geometry.at(index)?.center;
            if x == 0 {
                point.x = 0.0;
            }
            if x == columns - 1 {
                point.x = 1.0;
            }
            if y == 0 {
                point.y = 0.0;
            }
            if y == rows - 1 {
                point.y = 1.0;
            }
            lattice.push((point, index));
        }
    }
    let mut out = Vec::new();
    let groups: Vec<usize> = layers
        .iter()
        .map(|layer| {
            identities
                .iter()
                .position(|&id| id == layer.span.id)
                .unwrap()
        })
        .collect();
    for y in 0..rows - 1 {
        for x in 0..columns - 1 {
            let a = y * columns + x;
            let corners = [a, a + 1, a + columns + 1, a + columns];
            let points = corners.map(|index| lattice[index].0);
            let values: Vec<_> = layers
                .iter()
                .map(|layer| corners.map(|index| layer.region.signed[lattice[index].1]))
                .collect();
            if values
                .iter()
                .all(|v| v.iter().all(|&n| (n >= 0.0) == (v[0] >= 0.0)))
            {
                let mut membership = Membership::default();
                for (i, v) in values.iter().enumerate() {
                    if v[0] >= 0.0 {
                        membership.insert(groups[i]);
                    }
                }
                if !membership.is_empty() {
                    out.push(SelectionPatch {
                        membership,
                        points: points.to_vec(),
                    });
                }
                continue;
            }
            let centers: Vec<_> = values
                .iter()
                .map(|v| {
                    let signs = v.map(|n| n >= 0.0);
                    if signs[0] == signs[2] && signs[1] == signs[3] && signs[0] != signs[1] {
                        -0.001
                    } else {
                        (v[0] + v[2]) * 0.5
                    }
                })
                .collect();
            for edge in 0..4 {
                let triangle = [
                    points[edge],
                    points[(edge + 1) % 4],
                    points[0].lerp(points[2], 0.5),
                ];
                // The barycentric determinant is the fraction of the original
                // triangle's area. Keep the existing one-millionth cutoff, but
                // evaluate before f32 UV rounding can manufacture area along
                // an exactly shared boundary. Cast only the final vertices.
                let has_area = |polygon: &[CutVertex]| {
                    if polygon.len() < 3 {
                        return false;
                    }
                    let origin = polygon[0].weights;
                    let fraction = polygon[1..]
                        .windows(2)
                        .map(|pair| {
                            let a = pair[0].weights;
                            let b = pair[1].weights;
                            (a[1] - origin[1]) * (b[2] - origin[2])
                                - (a[2] - origin[2]) * (b[1] - origin[1])
                        })
                        .sum::<f64>()
                        .abs();
                    fraction > 1e-6
                };
                let mut pieces = vec![(
                    Membership::default(),
                    (0..3)
                        .map(|i| {
                            let mut weights = [0.0; 3];
                            weights[i] = 1.0;
                            CutVertex { weights }
                        })
                        .collect::<Vec<_>>(),
                )];
                for (layer, v) in values.iter().enumerate() {
                    let field = [v[edge], v[(edge + 1) % 4], centers[layer]].map(f64::from);
                    if field.iter().all(|&n| n < 0.0) {
                        continue;
                    }
                    if field.iter().all(|&n| n >= 0.0) {
                        for (mask, _) in &mut pieces {
                            mask.insert(groups[layer]);
                        }
                        continue;
                    }
                    let mut next = Vec::new();
                    for (mask, polygon) in pieces {
                        if mask.contains(groups[layer]) {
                            next.push((mask, polygon));
                            continue;
                        }
                        let positive = clip_field_polygon(&polygon, field, 1.0);
                        let negative = clip_field_polygon(&polygon, field, -1.0);
                        if has_area(&positive) {
                            let mut admitted = mask.clone();
                            admitted.insert(groups[layer]);
                            next.push((admitted, positive));
                        }
                        if has_area(&negative) {
                            next.push((mask, negative));
                        }
                    }
                    pieces = next;
                }
                for (membership, polygon) in pieces {
                    if membership.is_empty() {
                        continue;
                    }
                    let points: Vec<_> = polygon.into_iter().map(|v| v.point(triangle)).collect();
                    if polygon_area(&points) > 1e-12 {
                        out.push(SelectionPatch { membership, points });
                    }
                }
            }
        }
    }
    Some(out)
}

fn clip_field_polygon(polygon: &[CutVertex], field: [f64; 3], sign: f64) -> Vec<CutVertex> {
    let Some(&last) = polygon.last() else {
        return Vec::new();
    };
    let distance = |vertex: CutVertex| {
        vertex
            .weights
            .iter()
            .zip(field)
            .map(|(&weight, value)| weight * value)
            .sum::<f64>()
            * sign
    };
    let mut previous = last;
    let mut before = distance(previous);
    let mut out = Vec::new();
    for &current in polygon {
        let after = distance(current);
        if (before >= 0.0) != (after >= 0.0) {
            let t = before / (before - after);
            out.push(CutVertex {
                weights: std::array::from_fn(|i| {
                    previous.weights[i] + (current.weights[i] - previous.weights[i]) * t
                }),
            });
        }
        if after >= 0.0 {
            out.push(current);
        }
        previous = current;
        before = after;
    }
    out
}

fn clip_polygon<T: Copy>(
    polygon: &[T],
    distance: impl Fn(T) -> f32,
    interpolate: impl Fn(T, T, f32) -> T,
) -> Vec<T> {
    let Some(&last) = polygon.last() else {
        return Vec::new();
    };
    let mut previous = last;
    let mut before = distance(previous);
    let mut out = Vec::new();
    for &current in polygon {
        let after = distance(current);
        if (before >= 0.0) != (after >= 0.0) {
            out.push(interpolate(previous, current, before / (before - after)));
        }
        if after >= 0.0 {
            out.push(current);
        }
        previous = current;
        before = after;
    }
    out
}

fn polygon_area(points: &[Pos2]) -> f32 {
    if points.len() < 3 {
        return 0.0;
    }
    let origin = points[0];
    points[1..]
        .windows(2)
        .map(|pair| {
            let a = pair[0] - origin;
            let b = pair[1] - origin;
            a.x * b.y - a.y * b.x
        })
        .sum::<f32>()
        .abs()
        * 0.5
}

#[derive(PartialEq)]
struct PaintKey {
    image: Rect,
    aperture: Rect,
    color: Color32,
    pixels_per_point: f32,
    approximate: bool,
    options: egui::epaint::TessellationOptions,
}
struct PaintEntry {
    region: Arc<DenseRegion>,
    key: PaintKey,
    mesh: Arc<egui::Mesh>,
}

/// Two stable projections cover the final photograph and its companion.
/// Moving the pointer or clip rectangle does not clone or rebuild geometry.
#[derive(Default)]
pub(crate) struct DenseRegionPainter {
    entries: VecDeque<PaintEntry>,
}
impl DenseRegionPainter {
    pub(crate) fn paint(
        &mut self,
        painter: &Painter,
        region: &Arc<DenseRegion>,
        image: Rect,
        aperture: Rect,
        color: Color32,
    ) {
        self.paint_style(painter, region, image, aperture, color, false);
    }

    /// A source photograph is not certified in final-photo coordinates. The
    /// caller labels this alignment guide as approximate; dashes reinforce it.
    pub(crate) fn paint_approximate(
        &mut self,
        painter: &Painter,
        region: &Arc<DenseRegion>,
        image: Rect,
        aperture: Rect,
        color: Color32,
    ) {
        self.paint_style(painter, region, image, aperture, color, true);
    }

    fn paint_style(
        &mut self,
        painter: &Painter,
        region: &Arc<DenseRegion>,
        image: Rect,
        aperture: Rect,
        color: Color32,
        approximate: bool,
    ) {
        if region.is_empty()
            || !image.is_finite()
            || !image.is_positive()
            || !aperture.is_finite()
            || !aperture.is_positive()
        {
            return;
        }
        let key = PaintKey {
            image,
            aperture,
            color,
            approximate,
            pixels_per_point: painter.ctx().pixels_per_point(),
            options: painter.ctx().tessellation_options(|options| *options),
        };
        let index = self
            .entries
            .iter()
            .position(|entry| Arc::ptr_eq(&entry.region, region) && entry.key == key);
        let mesh = if let Some(index) = index {
            let entry = self.entries.remove(index).unwrap();
            let mesh = entry.mesh.clone();
            self.entries.push_back(entry);
            mesh
        } else {
            let project =
                |uv: Pos2| image.min + (uv - aperture.min) / aperture.size() * image.size();
            let mut mesh = egui::Mesh::default();
            let fill = Color32::from_rgba_unmultiplied(
                color.r(),
                color.g(),
                color.b(),
                if approximate { 18 } else { 36 },
            )
            .gamma_multiply(f32::from(color.a()) / 255.0);
            mesh.vertices
                .extend(region.vertices.iter().map(|&uv| egui::epaint::Vertex {
                    pos: project(uv),
                    uv: egui::epaint::WHITE_UV,
                    color: fill,
                }));
            mesh.indices.extend_from_slice(&region.indices);
            let mut tessellator = egui::epaint::Tessellator::new(
                key.pixels_per_point,
                key.options,
                [1, 1],
                Vec::new(),
            );
            let stroke = Stroke::new(1.0_f32, color.gamma_multiply(0.8));
            for contour in &region.contours {
                let points: Vec<_> = contour.iter().copied().map(project).collect();
                if approximate {
                    for [from, to] in dashed_segments(&points, image) {
                        tessellator.tessellate_shape(
                            egui::Shape::line_segment([from, to], stroke),
                            &mut mesh,
                        );
                    }
                } else {
                    tessellator.tessellate_shape(egui::Shape::line(points, stroke), &mut mesh);
                }
            }
            let mesh = Arc::new(mesh);
            if self.entries.len() == 4 {
                self.entries.pop_front();
            }
            self.entries.push_back(PaintEntry {
                region: region.clone(),
                key,
                mesh: mesh.clone(),
            });
            mesh
        };
        painter
            .with_clip_rect(painter.clip_rect().intersect(image))
            .add(egui::Shape::mesh(mesh));
    }
}

struct SelectionPaintEntry {
    selection: Arc<DenseSelection>,
    key: PaintKey,
    mesh: Arc<egui::Mesh>,
}

/// Cached projections for both photographs. Intersections receive one mixed
/// fill and fine directional bands clipped to their convex membership pieces.
#[derive(Default)]
pub(crate) struct DenseSelectionPainter {
    entries: VecDeque<SelectionPaintEntry>,
}
impl DenseSelectionPainter {
    pub(crate) fn paint(
        &mut self,
        painter: &Painter,
        selection: &Arc<DenseSelection>,
        image: Rect,
        aperture: Rect,
    ) {
        self.paint_style(painter, selection, image, aperture, false);
    }

    pub(crate) fn paint_approximate(
        &mut self,
        painter: &Painter,
        selection: &Arc<DenseSelection>,
        image: Rect,
        aperture: Rect,
    ) {
        self.paint_style(painter, selection, image, aperture, true);
    }

    fn paint_style(
        &mut self,
        painter: &Painter,
        selection: &Arc<DenseSelection>,
        image: Rect,
        aperture: Rect,
        approximate: bool,
    ) {
        if selection.is_empty()
            || !image.is_finite()
            || !image.is_positive()
            || !aperture.is_finite()
            || !aperture.is_positive()
        {
            return;
        }
        let key = PaintKey {
            image,
            aperture,
            color: Color32::WHITE,
            approximate,
            pixels_per_point: painter.ctx().pixels_per_point(),
            options: painter.ctx().tessellation_options(|options| *options),
        };
        let index = self
            .entries
            .iter()
            .position(|entry| Arc::ptr_eq(&entry.selection, selection) && entry.key == key);
        let mesh = if let Some(index) = index {
            let entry = self.entries.remove(index).unwrap();
            let mesh = entry.mesh.clone();
            self.entries.push_back(entry);
            mesh
        } else {
            let mesh = Arc::new(selection_mesh(selection, &key));
            if self.entries.len() == 4 {
                self.entries.pop_front();
            }
            self.entries.push_back(SelectionPaintEntry {
                selection: selection.clone(),
                key,
                mesh: mesh.clone(),
            });
            mesh
        };
        painter
            .with_clip_rect(painter.clip_rect().intersect(image))
            .add(egui::Shape::mesh(mesh));
    }
}

fn membership_colors(selection: &DenseSelection, membership: &Membership) -> Vec<Color32> {
    let mut colors = Vec::new();
    for (index, &color) in selection.colors.iter().enumerate() {
        if membership.contains(index) {
            colors.push(color);
        }
    }
    // Canonical stripe order makes the same geometry independent of selection
    // insertion order. Split intervals sharing an identity remain one contributor.
    colors.sort_unstable_by_key(|color| (color.r(), color.g(), color.b()));
    colors
}

fn selection_mesh(selection: &DenseSelection, key: &PaintKey) -> egui::Mesh {
    let project =
        |uv: Pos2| key.image.min + (uv - key.aperture.min) / key.aperture.size() * key.image.size();
    let mut mesh = egui::Mesh::default();
    for patch in &selection.patches {
        let colors = membership_colors(selection, &patch.membership);
        let overlap = colors.len() > 1;
        let alpha = match (key.approximate, overlap) {
            (false, false) => 36,
            (true, false) => 18,
            (false, true) => 46,
            (true, true) => 23,
        };
        let count = colors.len() as u32;
        let channel = |get: fn(&Color32) -> u8| {
            (colors
                .iter()
                .map(|color| u32::from(get(color)))
                .sum::<u32>()
                / count) as u8
        };
        let color = Color32::from_rgba_unmultiplied(
            channel(Color32::r),
            channel(Color32::g),
            channel(Color32::b),
            alpha,
        );
        let mut points: Vec<_> = patch.points.iter().copied().map(project).collect();
        // Clip before stripe expansion: a tight zoom must not generate bands
        // for off-screen geometry or make the cache proportional to zoom.
        for (axis, edge, sign) in [
            (0, key.image.left(), 1.0),
            (0, key.image.right(), -1.0),
            (1, key.image.top(), 1.0),
            (1, key.image.bottom(), -1.0),
        ] {
            points = clip_polygon(
                &points,
                |point| (point[axis] - edge) * sign,
                |a, b, t| a.lerp(b, t),
            );
        }
        if points.len() < 3 || polygon_area(&points) <= 1e-6 {
            continue;
        }
        append_polygon(&mut mesh, &points, color);
        if !overlap {
            continue;
        }
        let coordinate = |point: Pos2| {
            ((point.x - key.image.left()) + (point.y - key.image.top()))
                * std::f32::consts::FRAC_1_SQRT_2
        };
        let low = points
            .iter()
            .copied()
            .map(coordinate)
            .fold(f32::INFINITY, f32::min);
        let high = points
            .iter()
            .copied()
            .map(coordinate)
            .fold(f32::NEG_INFINITY, f32::max);
        for band in (low / 9.0).floor() as i32..=(high / 9.0).floor() as i32 {
            let start = band as f32 * 9.0;
            let stripe = clip_polygon(
                &points,
                |point| coordinate(point) - start,
                |a, b, t| a.lerp(b, t),
            );
            let stripe = clip_polygon(
                &stripe,
                |point| start + 1.5 - coordinate(point),
                |a, b, t| a.lerp(b, t),
            );
            if stripe.len() < 3 || polygon_area(&stripe) <= 1e-6 {
                continue;
            }
            let color = colors[band.rem_euclid(colors.len() as i32) as usize];
            append_polygon(
                &mut mesh,
                &stripe,
                Color32::from_rgba_unmultiplied(
                    color.r(),
                    color.g(),
                    color.b(),
                    if key.approximate { 55 } else { 100 },
                ),
            );
        }
    }
    let mut tessellator =
        egui::epaint::Tessellator::new(key.pixels_per_point, key.options, [1, 1], Vec::new());
    for layer in &selection.layers {
        let stroke = Stroke::new(1.0_f32, layer.span.color().gamma_multiply(0.8));
        for contour in &layer.region.contours {
            let points: Vec<_> = contour.iter().copied().map(project).collect();
            if key.approximate {
                for [from, to] in dashed_segments(&points, key.image) {
                    tessellator
                        .tessellate_shape(egui::Shape::line_segment([from, to], stroke), &mut mesh);
                }
            } else {
                tessellator.tessellate_shape(egui::Shape::line(points, stroke), &mut mesh);
            }
        }
    }
    mesh
}

fn append_polygon(mesh: &mut egui::Mesh, points: &[Pos2], color: Color32) {
    let base = mesh.vertices.len() as u32;
    mesh.vertices
        .extend(points.iter().map(|&pos| egui::epaint::Vertex {
            pos,
            uv: egui::epaint::WHITE_UV,
            color,
        }));
    for index in 1..points.len() - 1 {
        mesh.indices
            .extend([base, base + index as u32, base + index as u32 + 1]);
    }
}

/// Carry dash phase across the contour's small marching-triangle segments.
/// Restarting each segment would make dense contours appear solid again.
fn dashed_segments(points: &[Pos2], clip: Rect) -> Vec<[Pos2; 2]> {
    let mut segments = Vec::new();
    let mut phase = 0.0f32;
    for edge in points.windows(2) {
        let length = edge[0].distance(edge[1]);
        if !length.is_finite() || length <= f32::EPSILON {
            continue;
        }
        if let Some([lo, hi]) = clipped_interval([edge[0], edge[1]], clip) {
            let visible = [edge[0].lerp(edge[1], lo), edge[0].lerp(edge[1], hi)];
            let visible_length = visible[0].distance(visible[1]);
            let mut dash_phase = (phase + (lo * length) % 9.0) % 9.0;
            let mut offset = 0.0;
            while offset < visible_length {
                let on = dash_phase < 5.0;
                let step = (if on {
                    5.0 - dash_phase
                } else {
                    9.0 - dash_phase
                })
                .min(visible_length - offset);
                let next = offset + step;
                if next <= offset {
                    break;
                }
                if on {
                    segments.push([
                        visible[0].lerp(visible[1], offset / visible_length),
                        visible[0].lerp(visible[1], next / visible_length),
                    ]);
                }
                offset = next;
                dash_phase += step;
                if dash_phase >= 9.0 {
                    dash_phase = 0.0;
                }
            }
        }
        phase = (phase + length % 9.0) % 9.0;
    }
    segments
}

/// Clip before expanding dashes, so zoomed off-screen paths cost no geometry.
fn clipped_interval([from, to]: [Pos2; 2], clip: Rect) -> Option<[f32; 2]> {
    let delta = to - from;
    let mut range = [0.0f32, 1.0f32];
    for (origin, direction, low, high) in [
        (from.x, delta.x, clip.left(), clip.right()),
        (from.y, delta.y, clip.top(), clip.bottom()),
    ] {
        if direction.abs() <= f32::EPSILON {
            if origin < low || origin > high {
                return None;
            }
        } else {
            let a = (low - origin) / direction;
            let b = (high - origin) / direction;
            range[0] = range[0].max(a.min(b));
            range[1] = range[1].min(a.max(b));
            if range[0] > range[1] {
                return None;
            }
        }
    }
    Some(range)
}

#[cfg(test)]
#[path = "process-admission-regions-tests.rs"]
mod tests;
