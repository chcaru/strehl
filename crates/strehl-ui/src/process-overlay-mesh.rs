//! A retained GPU draw for sparse evidence. No inferred pixels between samples.
use super::{ColoredSample, Context};
use crate::process_sample_glyphs::{Density, SampleGlyph};
use eframe::egui::{self, Color32, Pos2, Rect, Vec2};
use std::sync::Arc;

#[derive(Clone, Copy, Debug, Default, PartialEq, Eq)]
pub(super) enum Mode {
    #[default]
    Detail,
    Scales,
    Clean,
}
impl Mode {
    pub(super) fn read(ctx: &egui::Context) -> Self {
        ctx.data(|data| data.get_temp(egui::Id::new("final-overlay-mode")))
            .unwrap_or_default()
    }
    pub(super) fn write(self, ctx: &egui::Context) {
        ctx.data_mut(|data| data.insert_temp(egui::Id::new("final-overlay-mode"), self));
        ctx.request_repaint();
    }
}

#[derive(PartialEq)]
struct Key {
    image: Rect,
    aperture: Rect,
    level: usize,
    density: Density,
}
#[derive(Default)]
pub(super) struct Overlay {
    key: Option<Key>,
    mesh: Arc<egui::Mesh>,
    #[cfg(test)]
    pub(super) builds: usize,
}
impl Overlay {
    pub(super) fn invalidate(&mut self) {
        self.key = None;
    }
    pub(super) fn paint(
        &mut self,
        painter: &egui::Painter,
        image: Rect,
        input: &Context<'_>,
        samples: &[ColoredSample],
    ) {
        let key = Key {
            image,
            aperture: input.aperture,
            level: input.level,
            density: Density::read(painter.ctx()),
        };
        if self.key.as_ref() != Some(&key) {
            let mut mesh = egui::Mesh::default();
            for active in [false, true] {
                for level in 0..16 {
                    if (level == input.level) != active {
                        continue;
                    }
                    let start = samples.partition_point(|sample| sample.level < level);
                    let end = samples.partition_point(|sample| sample.level <= level);
                    let visible = || {
                        samples[start..end]
                            .iter()
                            .filter(|sample| sample.glyph.cell.intersects(input.aperture))
                    };
                    let stride = visible().count().div_ceil(key.density.cap(active)).max(1);
                    for sample in visible().step_by(stride) {
                        let color = if active {
                            sample.colors[0]
                        } else {
                            crate::process_sample_glyphs::level_color(level)
                        };
                        append_glyph(
                            &mut mesh,
                            image,
                            input.aperture,
                            sample.glyph,
                            color,
                            active,
                        );
                        if active
                            && sample.colors.len() > 1
                            && input.aperture.contains(sample.glyph.center)
                        {
                            let at = image.min
                                + (sample.glyph.center - input.aperture.min)
                                    / input.aperture.size()
                                    * image.size();
                            for (index, color) in sample.colors.iter().enumerate() {
                                let direction = Vec2::angled(
                                    std::f32::consts::TAU * index as f32
                                        / sample.colors.len() as f32,
                                );
                                segment(&mut mesh, at, at + direction * 3.5, 1.1, *color);
                            }
                        }
                    }
                }
            }
            self.mesh = Arc::new(mesh);
            self.key = Some(key);
            #[cfg(test)]
            {
                self.builds += 1;
            }
        }
        if !self.mesh.is_empty() {
            painter
                .with_clip_rect(painter.clip_rect().intersect(image))
                .add(egui::Shape::Mesh(Arc::clone(&self.mesh)));
        }
    }
}

fn segment(mesh: &mut egui::Mesh, from: Pos2, to: Pos2, width: f32, color: Color32) {
    let normal = (to - from).normalized().rot90() * width * 0.5;
    let start = mesh.vertices.len() as u32;
    for pos in [from + normal, from - normal, to + normal, to - normal] {
        mesh.colored_vertex(pos, color);
    }
    mesh.add_triangle(start, start + 1, start + 2);
    mesh.add_triangle(start + 1, start + 3, start + 2);
}

fn append_glyph(
    mesh: &mut egui::Mesh,
    image: Rect,
    aperture: Rect,
    glyph: SampleGlyph,
    color: Color32,
    active: bool,
) {
    let project = |uv: Pos2| image.min + (uv - aperture.min) / aperture.size() * image.size();
    let center = project(glyph.center);
    let cell = Rect::from_min_max(project(glyph.cell.min), project(glyph.cell.max));
    let ink = color.gamma_multiply(if active { 0.8 } else { 0.4 });
    if image.contains(center) {
        const UNIT: [[f32; 2]; 8] = [
            [1.0, 0.0],
            [0.70710677, 0.70710677],
            [0.0, 1.0],
            [-0.70710677, 0.70710677],
            [-1.0, 0.0],
            [-0.70710677, -0.70710677],
            [0.0, -1.0],
            [0.70710677, -0.70710677],
        ];
        let start = mesh.vertices.len() as u32;
        let radius = if active { 1.05 } else { 0.65 };
        mesh.colored_vertex(center, ink);
        for offset in UNIT {
            mesh.colored_vertex(center + Vec2::from(offset) * radius, ink);
        }
        for offset in UNIT {
            mesh.colored_vertex(
                center + Vec2::from(offset) * (radius + 0.65),
                Color32::TRANSPARENT,
            );
        }
        for i in 0..8u32 {
            let next = (i + 1) % 8;
            mesh.add_triangle(start, start + 1 + i, start + 1 + next);
            mesh.add_triangle(start + 1 + i, start + 9 + i, start + 9 + next);
            mesh.add_triangle(start + 1 + i, start + 9 + next, start + 1 + next);
        }
    }
    if cell.width().min(cell.height()) >= 2.0 {
        let tick = (cell.width().min(cell.height()) * 0.24).min(7.0);
        let width = if active { 1.0 } else { 0.7 };
        for (corner, direction) in [
            (cell.left_top(), Vec2::splat(1.0)),
            (cell.right_top(), egui::vec2(-1.0, 1.0)),
            (cell.right_bottom(), Vec2::splat(-1.0)),
            (cell.left_bottom(), egui::vec2(1.0, -1.0)),
        ] {
            segment(
                mesh,
                corner,
                corner + egui::vec2(direction.x * tick, 0.0),
                width,
                ink,
            );
            segment(
                mesh,
                corner,
                corner + egui::vec2(0.0, direction.y * tick),
                width,
                ink,
            );
        }
    }
}
