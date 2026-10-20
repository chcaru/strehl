//! Sparse diagnostic samples on the actual pyramid lattice.
//!
//! A transmitted diagnostic grid is a set of nearest observations, not a set of
//! owned rectangles. The CLI samples a ceil-halved pyramid whose decimation
//! phase is zero. Keep those three geometries separate: telemetry density,
//! coefficient spacing, and the much wider filter support. Only the second
//! is drawn here, and never as an assertion about unsampled neighbours.
//!
//! UV is the aligned analysis domain. The caller must obtain an OutputSpace
//! certificate before applying these UVs to the developed photograph. CFA
//! plane pixels are not final RGB pixels: binning preserves their dimensions,
//! whereas the demosaic writer doubles both dimensions.

use crate::process_provenance::AdmissionMeta;
use eframe::egui::{self, Color32, Painter, Pos2, Rect, Stroke, Vec2};

/// Display thinning only. Every mark still belongs to a retained observation.
/// New runs transmit up to128x96; older runs retain their original resolution.
#[derive(Clone, Copy, Default, Debug, PartialEq, Eq)]
pub(crate) enum Density {
    Quiet,
    Balanced,
    #[default]
    Full,
}
impl Density {
    pub(crate) fn read(ctx: &egui::Context) -> Self {
        ctx.data(|data| data.get_temp(egui::Id::new("diagnostic-display-density")))
            .unwrap_or_default()
    }
    pub(crate) fn write(self, ctx: &egui::Context) {
        ctx.data_mut(|data| data.insert_temp(egui::Id::new("diagnostic-display-density"), self));
        ctx.request_repaint();
    }
    pub(crate) fn cap(self, active: bool) -> usize {
        match (self, active) {
            (Self::Quiet, true) => 1024,
            (Self::Quiet, false) => 96,
            (Self::Balanced, true) => 6144,
            (Self::Balanced, false) => 384,
            (Self::Full, _) => 128 * 96,
        }
    }
}

#[derive(Clone, Copy, Debug)]
pub(crate) struct SampleGeometry {
    extent: [usize; 2],
    samples: [usize; 2],
    grid: [usize; 2],
    spacing: usize,
}

#[derive(Clone, Copy, Debug, PartialEq)]
pub(crate) struct SampleGlyph {
    /// The coefficient that the telemetry packet actually sampled.
    pub center: Pos2,
    /// One coefficient-spacing cell, not reconstruction/filter support.
    pub cell: Rect,
}

impl SampleGeometry {
    pub(crate) fn new(level: usize, meta: AdmissionMeta) -> Option<Self> {
        // The desktop parser accepts much larger level IDs for forward
        // compatibility. They cannot establish finite, useful pixel geometry.
        let spacing = 1usize.checked_shl(u32::try_from(level).ok()?)?;
        if meta.extent.contains(&0)
            || meta.extent.iter().any(|&value| value > 65_536)
            || meta.samples.contains(&0)
            || meta.samples[0] > crate::process_provenance::SAMPLE_LIMIT[0]
            || meta.samples[1] > crate::process_provenance::SAMPLE_LIMIT[1]
            || spacing > 65_536
        {
            return None;
        }
        let grid = meta.extent.map(|size| size.div_ceil(spacing));
        if meta
            .samples
            .iter()
            .zip(grid)
            .any(|(&samples, size)| samples > size)
        {
            return None;
        }
        Some(Self {
            extent: meta.extent,
            samples: meta.samples,
            grid,
            spacing,
        })
    }

    pub(crate) fn spacing(self) -> usize {
        self.spacing
    }

    #[cfg(test)]
    pub(crate) fn grid(self) -> [usize; 2] {
        self.grid
    }

    /// Nearest transmitted observation, not an assertion at the requested
    /// pixel. Callers should retain its displaced `at(index).center` for links.
    pub(crate) fn nearest_index_at(self, pin: Pos2) -> Option<usize> {
        if !pin.is_finite() {
            return None;
        }
        let point = [pin.x.clamp(0.0, 1.0), pin.y.clamp(0.0, 1.0)];
        let nearest: [usize; 2] = std::array::from_fn(|axis| {
            (0..self.samples[axis])
                .min_by(|&left, &right| {
                    let distance = |sample: usize| {
                        let coefficient = ((2 * sample + 1) * self.grid[axis]
                            / (2 * self.samples[axis]))
                            .min(self.grid[axis] - 1);
                        let center = (coefficient * self.spacing) as f32 + 0.5;
                        (center / self.extent[axis] as f32 - point[axis]).abs()
                    };
                    distance(left).total_cmp(&distance(right))
                })
                .unwrap_or(0)
        });
        Some(nearest[1] * self.samples[0] + nearest[0])
    }

    /// Strict spatial hit: unsampled coefficient cells remain unknown. A
    /// point anywhere inside a giant telemetry bin does not count as observed.
    #[cfg(test)]
    pub(crate) fn observed_index_at(self, pin: Pos2) -> Option<usize> {
        let index = self.nearest_index_at(pin)?;
        self.at(index)?.cell.contains(pin).then_some(index)
    }

    pub(crate) fn at(self, index: usize) -> Option<SampleGlyph> {
        if index >= self.samples[0] * self.samples[1] {
            return None;
        }
        let cell = [index % self.samples[0], index / self.samples[0]];
        // Match ui-diagnostics::surface's integer nearest sample exactly.
        let coefficient: [usize; 2] = std::array::from_fn(|axis| {
            ((2 * cell[axis] + 1) * self.grid[axis] / (2 * self.samples[axis]))
                .min(self.grid[axis] - 1)
        });
        // REDUCE centres its taps on even indices. Pixel centres use +0.5 in
        // image UV; a coarser level must not gain a half-cell phase shift.
        let center = egui::pos2(
            (coefficient[0] * self.spacing) as f32 + 0.5,
            (coefficient[1] * self.spacing) as f32 + 0.5,
        );
        let extent = egui::vec2(self.extent[0] as f32, self.extent[1] as f32);
        let half = Vec2::splat(self.spacing as f32 * 0.5);
        Some(SampleGlyph {
            center: Pos2::ZERO + center.to_vec2() / extent,
            cell: Rect::from_min_max(
                Pos2::ZERO + (center.to_vec2() - half).max(Vec2::ZERO) / extent,
                Pos2::ZERO + (center.to_vec2() + half).min(extent) / extent,
            ),
        })
    }
}

/// Separate octave identity from source/selection identity when several sizes
/// are shown together. Position and footprint remain the primary encodings.
pub(crate) fn level_color(level: usize) -> Color32 {
    [
        Color32::from_rgb(92, 210, 196),
        Color32::from_rgb(100, 181, 239),
        Color32::from_rgb(150, 159, 239),
        Color32::from_rgb(196, 149, 220),
        Color32::from_rgb(230, 157, 175),
        Color32::from_rgb(236, 184, 126),
        Color32::from_rgb(203, 207, 129),
        Color32::from_rgb(143, 207, 154),
    ][level % 8]
}

/// Paint an observed positive sample. At overview scale the small dot is an
/// explicit visibility marker; it never expands to fill a telemetry cell.
/// At inspection scale corner marks reveal the real coefficient spacing.
/// Empty and unobserved positions should be left untouched by the caller.
pub(crate) fn paint_glyph(
    painter: &Painter,
    image: Rect,
    aperture: Rect,
    glyph: SampleGlyph,
    color: Color32,
    active: bool,
) {
    if !image.is_finite()
        || !aperture.is_finite()
        || image.width() <= 0.0
        || image.height() <= 0.0
        || aperture.width() <= 0.0
        || aperture.height() <= 0.0
        || !glyph.cell.intersects(aperture)
    {
        return;
    }
    let painter = painter.with_clip_rect(painter.clip_rect().intersect(image));
    let project = |uv: Pos2| image.min + (uv - aperture.min) / aperture.size() * image.size();
    let center = project(glyph.center);
    let cell = Rect::from_min_max(project(glyph.cell.min), project(glyph.cell.max));
    let ink = color.gamma_multiply(if active { 0.88 } else { 0.48 });
    let marker = if active { 1.05 } else { 0.65 };
    if image.contains(center) {
        painter.circle_filled(center, marker, ink);
    }
    // Corner ticks encode extent without a checkerboard or opaque ownership
    // claim. Small projected coefficients use only the visibility marker.
    if cell.width().min(cell.height()) >= 2.0 {
        let tick = (cell.width().min(cell.height()) * 0.24).min(7.0);
        let stroke = Stroke::new(if active { 1.0_f32 } else { 0.7_f32 }, ink);
        for (corner, direction) in [
            (cell.left_top(), Vec2::splat(1.0)),
            (cell.right_top(), egui::vec2(-1.0, 1.0)),
            (cell.right_bottom(), Vec2::splat(-1.0)),
            (cell.left_bottom(), egui::vec2(1.0, -1.0)),
        ] {
            painter.line_segment(
                [corner, corner + egui::vec2(direction.x * tick, 0.0)],
                stroke,
            );
            painter.line_segment(
                [corner, corner + egui::vec2(0.0, direction.y * tick)],
                stroke,
            );
        }
    }
}

#[cfg(test)]
#[path = "process-sample-glyphs-tests.rs"]
mod tests;

/// Test-only inspection of actual binary-pane paint geometry. No surrogate
/// texture mesh is manufactured to preserve the former implementation.
#[cfg(test)]
pub(crate) fn binary_panes(output: &egui::FullOutput, container: Rect) -> Vec<Rect> {
    let mut panes: Vec<_> = output
        .shapes
        .iter()
        .filter_map(|shape| match &shape.shape {
            egui::Shape::Rect(rect)
                if rect.fill == crate::theme::BG
                    && rect.rect.width() > 2.0
                    && rect.rect.height() > 2.0
                    && rect.rect.width() < container.width() * 0.3
                    && rect.rect.height() < container.height() * 0.5
                    && container.contains_rect(rect.rect) =>
            {
                Some(rect.rect)
            }
            _ => None,
        })
        .collect();
    panes.sort_by(|a, b| {
        a.center()
            .y
            .total_cmp(&b.center().y)
            .then(a.center().x.total_cmp(&b.center().x))
    });
    panes.dedup();
    panes
}

/// Re-derive expected positions directly from the producer's integer sampling
/// receipt, then compare actual painted points. The marker subset may be
/// density-limited, but every visible point must correspond to real data.
#[cfg(test)]
pub(crate) fn assert_painted_samples(
    output: &egui::FullOutput,
    image: Rect,
    aperture: Rect,
    packet: &crate::pipeline::DiagnosticSurface,
    extent: [usize; 2],
) {
    let spacing = 1usize << packet.level;
    let grid = extent.map(|side| side.div_ceil(spacing));
    let mut expected = Vec::new();
    for (index, &value) in packet.pixels.iter().enumerate() {
        if value != 255 {
            continue;
        }
        let sx = ((2 * (index % packet.width) + 1) * grid[0] / (2 * packet.width)).min(grid[0] - 1);
        let sy =
            ((2 * (index / packet.width) + 1) * grid[1] / (2 * packet.height)).min(grid[1] - 1);
        let uv = egui::pos2((sx * spacing) as f32 + 0.5, (sy * spacing) as f32 + 0.5);
        let uv = Pos2::ZERO + uv.to_vec2() / egui::vec2(extent[0] as f32, extent[1] as f32);
        if aperture.contains(uv) {
            expected.push(image.min + (uv - aperture.min) / aperture.size() * image.size());
        }
    }
    let mut actual: Vec<_> = output
        .shapes
        .iter()
        .filter_map(|shape| match &shape.shape {
            egui::Shape::Circle(circle)
                if (circle.radius - 1.05).abs() < 0.01
                    && circle.fill.a() > 0
                    && image.contains(circle.center)
                    && shape.clip_rect.min.distance(image.min) < 0.01
                    && shape.clip_rect.max.distance(image.max) < 0.01 =>
            {
                Some(circle.center)
            }
            _ => None,
        })
        .collect();
    for shape in &output.shapes {
        let egui::Shape::Mesh(mesh) = &shape.shape else {
            continue;
        };
        if mesh.texture_id != egui::TextureId::default()
            || shape.clip_rect.min.distance(image.min) >= 0.01
            || shape.clip_rect.max.distance(image.max) >= 0.01
        {
            continue;
        }
        let mut uses = vec![0usize; mesh.vertices.len()];
        for &index in &mesh.indices {
            uses[index as usize] += 1;
        }
        actual.extend(
            mesh.vertices
                .iter()
                .zip(uses)
                .filter_map(|(vertex, count)| {
                    (count == 8 && vertex.color.a() > 0 && image.contains(vertex.pos))
                        .then_some(vertex.pos)
                }),
        );
    }
    if !expected.is_empty() {
        assert!(
            !actual.is_empty(),
            "observed samples vanished from {image:?} at {:?}, level{}",
            aperture,
            packet.level
        );
    }
    for point in actual {
        assert!(
            expected
                .iter()
                .any(|expected| expected.distance(point) < 0.01),
            "sample {point:?} detached from the linked aperture {aperture:?}"
        );
    }
}
