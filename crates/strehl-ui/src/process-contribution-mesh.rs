//! Retained sparse sample geometry for the two photographic contribution lenses.
use crate::process_sample_glyphs::SampleGlyph;
use eframe::egui::{self, Color32, Pos2, Rect, Vec2};
use std::sync::Arc;

#[derive(PartialEq)]
struct Key {
    image: Rect,
    aperture: Rect,
    color: Color32,
    pixels_per_point: f32,
}
#[derive(Default)]
pub(super) struct SampleDraw {
    key: Option<Key>,
    mesh: Arc<egui::Mesh>,
    faded: Option<(u8, Arc<egui::Mesh>)>,
    #[cfg(test)]
    pub(super) builds: usize,
}
impl SampleDraw {
    pub(super) fn paint(
        &mut self,
        painter: &egui::Painter,
        image: Rect,
        aperture: Rect,
        glyphs: &[SampleGlyph],
        color: Color32,
        alpha: f32,
    ) {
        if !image.is_finite()
            || !aperture.is_finite()
            || image.width() <= 0.0
            || image.height() <= 0.0
            || aperture.width() <= 0.0
            || aperture.height() <= 0.0
        {
            return;
        }
        let key = Key {
            image,
            aperture,
            color,
            pixels_per_point: painter.ctx().pixels_per_point(),
        };
        if self.key.as_ref() != Some(&key) {
            let mut mesh = egui::Mesh::default();
            let visible = || {
                glyphs
                    .iter()
                    .filter(|glyph| glyph.cell.intersects(aperture))
            };
            let cap = ((image.area() / 24.0) as usize).clamp(24, 320);
            let stride = visible().count().div_ceil(cap).max(1);
            for glyph in visible().step_by(stride) {
                append_glyph(
                    &mut mesh,
                    image,
                    aperture,
                    *glyph,
                    color,
                    key.pixels_per_point,
                );
            }
            self.mesh = Arc::new(mesh);
            self.key = Some(key);
            self.faded = None;
            #[cfg(test)]
            {
                self.builds += 1;
            }
        }
        let alpha = (alpha.clamp(0.0, 1.0) * 255.0).round() as u8;
        if alpha == 0 || self.mesh.is_empty() {
            return;
        }
        let mesh = if alpha == 255 {
            Arc::clone(&self.mesh)
        } else {
            if self.faded.as_ref().is_none_or(|(old, _)| *old != alpha) {
                let mut mesh = (*self.mesh).clone();
                for vertex in &mut mesh.vertices {
                    vertex.color = vertex.color.gamma_multiply(f32::from(alpha) / 255.0);
                }
                self.faded = Some((alpha, Arc::new(mesh)));
            }
            Arc::clone(&self.faded.as_ref().unwrap().1)
        };
        painter
            .with_clip_rect(painter.clip_rect().intersect(image))
            .add(egui::Shape::Mesh(mesh));
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
    pixels_per_point: f32,
) {
    let project = |uv: Pos2| image.min + (uv - aperture.min) / aperture.size() * image.size();
    let center = project(glyph.center);
    let cell = Rect::from_min_max(project(glyph.cell.min), project(glyph.cell.max));
    let ink = color.gamma_multiply(0.88);
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
        mesh.colored_vertex(center, ink);
        for offset in UNIT {
            mesh.colored_vertex(center + Vec2::from(offset) * 1.05, ink);
        }
        for offset in UNIT {
            mesh.colored_vertex(
                center + Vec2::from(offset) * (1.05 + 0.65 / pixels_per_point.max(0.1)),
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
                1.0,
                ink,
            );
            segment(
                mesh,
                corner,
                corner + egui::vec2(0.0, direction.y * tick),
                1.0,
                ink,
            );
        }
    }
}
