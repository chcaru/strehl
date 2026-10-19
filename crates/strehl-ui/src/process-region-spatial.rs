//! Retained on-photograph source evidence. Tessellate the original four shapes
//! once per changed projection/evidence, including egui's own antialias fringe.
//! Pointer motion through the same samples changes clipping, not the mesh.
use super::*;
use std::sync::Arc;

#[derive(Clone)]
struct FallbackKey {
    meta: AdmissionMeta,
    window: Option<SampleWindow>,
    pixels: Arc<[u8]>,
}
impl PartialEq for FallbackKey {
    fn eq(&self, other: &Self) -> bool {
        self.meta == other.meta
            && self.window == other.window
            && Arc::ptr_eq(&self.pixels, &other.pixels)
    }
}

#[derive(PartialEq)]
struct Key {
    source: Option<SpatialKey>,
    fallback: Option<FallbackKey>,
    image: Rect,
    aperture: Rect,
    active: usize,
    cap: usize,
    pixels_per_point: f32,
    options: egui::epaint::TessellationOptions,
}

#[derive(Default)]
pub(super) struct Cache {
    key: Option<Key>,
    mesh: Arc<egui::Mesh>,
    #[cfg(test)]
    pub(super) builds: usize,
}
impl Cache {
    pub(super) fn mesh(
        &mut self,
        probe: &RegionProbe,
        painter: &egui::Painter,
        image: Rect,
        aperture: Rect,
        cap: usize,
        active: usize,
    ) -> Arc<egui::Mesh> {
        let fallback = probe.fallback.as_ref().filter(|fallback| {
            fallback.packet.level == active && Some(fallback.meta.extent) == probe.analysis_extent
        });
        let key = Key {
            source: probe.spatial_key.clone(),
            fallback: fallback.map(|fallback| FallbackKey {
                meta: fallback.meta,
                window: fallback.window,
                pixels: fallback.packet.pixels.clone(),
            }),
            image,
            aperture,
            active,
            cap,
            pixels_per_point: painter.ctx().pixels_per_point(),
            options: painter.ctx().tessellation_options(|options| *options),
        };
        if self.key.as_ref() != Some(&key) {
            let mut mesh = egui::Mesh::default();
            if image.is_finite()
                && image.is_positive()
                && aperture.is_finite()
                && aperture.is_positive()
            {
                let project =
                    |uv: Pos2| image.min + (uv - aperture.min) / aperture.size() * image.size();
                // These are paths, never text or atlas discs, so no font atlas
                // is required. Keep the renderer's actual DPI and AA options.
                let mut tessellator = egui::epaint::Tessellator::new(
                    key.pixels_per_point,
                    key.options,
                    [1, 1],
                    Vec::new(),
                );
                if let Some(source) = &key.source {
                    let templates: Vec<_> = source
                        .sources
                        .iter()
                        .enumerate()
                        .map(|(slot, &(frame, _, _))| {
                            let mut mesh = egui::Mesh::default();
                            tessellator
                                .tessellate_shape(sector(slot, capture_ink(frame)), &mut mesh);
                            mesh
                        })
                        .collect();
                    let mut positives = [0usize; 3];
                    for point in &probe.spatial {
                        for (slot, count) in positives.iter_mut().enumerate() {
                            *count += usize::from(point.sources & (1 << slot) != 0);
                        }
                    }
                    let strides = positives.map(|count| count.div_ceil(cap).max(1));
                    let mut seen = [0usize; 3];
                    // Thin each observed source independently. Thinning the
                    // union first can hide a sole positive among dense peers.
                    // Keep point/slot order so overlapping AA blends as before.
                    for point in &probe.spatial {
                        let center = project(point.glyph.center);
                        for (slot, template) in templates.iter().enumerate() {
                            if point.sources & (1 << slot) != 0 {
                                if seen[slot].is_multiple_of(strides[slot]) {
                                    append_at(&mut mesh, template, center);
                                }
                                seen[slot] += 1;
                            }
                        }
                    }
                }
                if let Some(fallback) = fallback {
                    let mut template = egui::Mesh::default();
                    tessellator.tessellate_shape(diamond(), &mut template);
                    for glyph in fallback
                        .points
                        .iter()
                        .step_by(fallback.points.len().div_ceil(cap).max(1))
                    {
                        append_at(&mut mesh, &template, project(glyph.center));
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
        self.mesh.clone()
    }
}

fn append_at(out: &mut egui::Mesh, template: &egui::Mesh, center: Pos2) {
    let offset = out.vertices.len() as u32;
    out.vertices
        .extend(template.vertices.iter().map(|vertex| egui::epaint::Vertex {
            pos: vertex.pos + center.to_vec2(),
            ..*vertex
        }));
    out.indices
        .extend(template.indices.iter().map(|index| offset + index));
}

fn sector(slot: usize, color: Color32) -> egui::Shape {
    // Three fixed identity slots even when only one capture is admitted.
    // This is independent binary support, not a pie chart of blend weights.
    let mut vertices = Vec::with_capacity(5);
    vertices.push(Pos2::ZERO);
    for step in 0..=3 {
        let angle = -std::f32::consts::FRAC_PI_2
            + (slot as f32 + step as f32 / 3.0) * std::f32::consts::TAU / 3.0;
        vertices.push(Pos2::ZERO + egui::vec2(angle.cos(), angle.sin()) * 3.0);
    }
    egui::Shape::convex_polygon(vertices, color, Stroke::NONE)
}

fn diamond() -> egui::Shape {
    egui::Shape::closed_line(
        vec![
            egui::pos2(0.0, -3.5),
            egui::pos2(3.5, 0.0),
            egui::pos2(0.0, 3.5),
            egui::pos2(-3.5, 0.0),
        ],
        Stroke::new(1.0_f32, crate::theme::INK),
    )
}

#[cfg(test)]
#[path = "process-region-spatial-tests.rs"]
mod tests;
