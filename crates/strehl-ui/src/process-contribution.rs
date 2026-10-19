//! Spatial decisions remain in the photograph's aligned working domain.
//! These lenses use the coarse green reconstruction, never an unregistered
//! camera original. A final TIFF is admitted only after its shared domain has
//! been certified against the writer's dimensions, mode and crop receipts.
use crate::{
    pipeline::{DiagnosticKind, DiagnosticScale, DiagnosticScope, DiagnosticSurface},
    process_provenance::AdmissionMeta,
    process_region_probe::SampleWindow,
    process_sample_glyphs::{SampleGeometry, SampleGlyph},
    theme::{AMBER, GREEN, LINE, MUTED, PANEL},
};
use eframe::egui::{self, Align2, Color32, FontId, Pos2, Rect, Sense, Stroke, TextureHandle, Ui};

#[path = "process-contribution-mesh.rs"]
mod mesh;
use mesh::SampleDraw;

struct Validated {
    packet: DiagnosticSurface,
    level: usize,
    extent: Option<[u32; 2]>,
    valid: bool,
}

struct Mask {
    packet: DiagnosticSurface,
    extent: Option<[usize; 2]>,
    glyphs: Vec<SampleGlyph>,
    previous: Option<Vec<SampleGlyph>>,
    arrived: f64,
    alpha: f32,
    draw: SampleDraw,
    previous_draw: SampleDraw,
    whole: SampleCount,
    count_window: Option<Option<SampleWindow>>,
    local_counts: Option<SampleCount>,
    #[cfg(test)]
    count_reads: usize,
}
impl Mask {
    fn counts(&mut self, aperture: Rect) -> (Option<SampleCount>, SampleCount) {
        let window = self.extent.and_then(|extent| {
            SampleWindow::new(
                self.packet.level,
                AdmissionMeta {
                    sequence: self.packet.sequence,
                    samples: [self.packet.width, self.packet.height],
                    extent,
                },
                aperture,
            )
        });
        if self.count_window != Some(window) {
            self.local_counts = window.map(|window| {
                let count = window.counts(self.packet.pixels.iter().map(|&value| value == 255));
                (count.admitted, count.observed)
            });
            self.count_window = Some(window);
            #[cfg(test)]
            {
                self.count_reads += 1;
            }
        }
        (self.local_counts, self.whole)
    }
}
struct Photo {
    current: TextureHandle,
    previous: Option<TextureHandle>,
    pending: Option<(TextureHandle, usize)>,
    folded: usize,
    previous_folded: usize,
    arrived: f64,
    alpha: f32,
    extent: Option<[usize; 2]>,
}

#[derive(Default)]
pub(crate) struct ContributionLenses {
    masks: [Option<Mask>; 2],
    validated: [Option<Validated>; 2],
    #[cfg(test)]
    validation_scans: usize,
    pending: bool,
    photo: Option<Photo>,
    drag: Option<(usize, Pos2)>,
}

#[derive(Clone, Copy)]
pub(crate) struct Context<'a> {
    pub base: Option<&'a TextureHandle>,
    pub base_folded: usize,
    pub admitted: Option<&'a DiagnosticSurface>,
    pub fallback: Option<&'a DiagnosticSurface>,
    pub level: usize,
    pub pin: Pos2,
    /// Exact rendered region shared by every diagnostic map this frame.
    pub aperture: Rect,
    pub extent: Option<egui::Vec2>,
}

pub(crate) struct Response {
    pub pin: Option<Pos2>,
    pub hovered: bool,
    pub dragging: bool,
    pub zoom_factor: f32,
    /// Pointer position normalized within the lens; passed to shared zoom_at.
    pub zoom_anchor: Option<Pos2>,
    pub reset: bool,
}
impl Default for Response {
    fn default() -> Self {
        Self {
            pin: None,
            hovered: false,
            dragging: false,
            zoom_factor: 1.0,
            zoom_anchor: None,
            reset: false,
        }
    }
}

impl ContributionLenses {
    pub(crate) fn transitioning(&self) -> bool {
        self.pending
            || self
                .masks
                .iter()
                .flatten()
                .any(|mask| mask.previous.is_some())
            || self
                .photo
                .as_ref()
                .is_some_and(|photo| photo.previous.is_some() || photo.pending.is_some())
    }

    pub(crate) fn show(&mut self, ui: &mut Ui, rect: Rect, context: Context<'_>) -> Response {
        let now = ui.input(|input| input.time);
        let extent = analysis_extent(context.extent);
        if self
            .photo
            .as_ref()
            .is_some_and(|photo| photo.extent != extent)
        {
            // Retained pixels and pending reveals belong to one analysis crop.
            self.photo = None;
        }
        if let Some(base) = context.base {
            if let Some(photo) = &mut self.photo {
                if base.id() != photo.current.id() {
                    photo.pending = Some((base.clone(), context.base_folded));
                } else {
                    // A texture can be updated in place without changing its
                    // handle. Its accepted prefix still advances immediately.
                    photo.folded = context.base_folded;
                }
            } else {
                self.photo = Some(Photo {
                    current: base.clone(),
                    previous: None,
                    pending: None,
                    folded: context.base_folded,
                    previous_folded: 0,
                    arrived: now,
                    alpha: 1.0,
                    extent,
                });
            }
        }
        if let Some(photo) = &mut self.photo {
            if photo.previous.is_none()
                && let Some((next, folded)) = photo.pending.take()
            {
                photo.previous = Some(std::mem::replace(&mut photo.current, next));
                photo.previous_folded = std::mem::replace(&mut photo.folded, folded);
                photo.arrived = now;
                photo.alpha = 0.0;
            }
            if photo.previous.is_some() {
                let t = ((now - photo.arrived) / 0.18).clamp(0.0, 1.0) as f32;
                photo.alpha = t * t * (3.0 - 2.0 * t);
                if t >= 1.0 {
                    photo.previous = None;
                }
            }
        }
        self.pending = false;
        let mut result = Response::default();
        let gap = 10.0;
        for (index, packet) in [context.admitted, context.fallback].into_iter().enumerate() {
            let kind = if index == 0 {
                DiagnosticKind::GateSupport
            } else {
                DiagnosticKind::Averaging
            };
            let color = if index == 0 { GREEN } else { AMBER };
            let declared_extent = context
                .extent
                .map(|extent| [extent.x.to_bits(), extent.y.to_bits()]);
            let valid_packet = packet.filter(|packet| {
                let cached = &mut self.validated[index];
                if cached.as_ref().is_none_or(|old| {
                    old.level != context.level
                        || old.extent != declared_extent
                        || !same_packet(&old.packet, packet)
                }) {
                    let valid = valid_mask(packet, kind, context.level)
                        && (context.extent.is_none()
                            || extent
                                .is_some_and(|extent| mask_geometry(packet, extent).is_some()));
                    *cached = Some(Validated {
                        packet: (*packet).clone(),
                        level: context.level,
                        extent: declared_extent,
                        valid,
                    });
                    #[cfg(test)]
                    {
                        self.validation_scans += 1;
                    }
                }
                cached.as_ref().is_some_and(|cached| cached.valid)
            });
            if packet.is_none() {
                self.validated[index] = None;
            }
            if let Some(packet) = valid_packet {
                let old = &mut self.masks[index];
                if old
                    .as_ref()
                    .is_none_or(|mask| !same_packet(&mask.packet, packet) || mask.extent != extent)
                {
                    if old.as_ref().is_some_and(|mask| {
                        mask.previous.is_some() && same_mask_domain(mask, packet, extent)
                    }) {
                        self.pending = true;
                    } else {
                        let previous = old
                            .as_ref()
                            .filter(|mask| same_mask_domain(mask, packet, extent))
                            .map(|mask| mask.glyphs.clone());
                        let previous_draw = old
                            .as_mut()
                            .filter(|mask| same_mask_domain(mask, packet, extent))
                            .map(|mask| std::mem::take(&mut mask.draw))
                            .unwrap_or_default();
                        *old = Some(Mask {
                            packet: packet.clone(),
                            extent,
                            glyphs: mask_glyphs(packet, extent),
                            arrived: now,
                            alpha: if previous.is_some() { 0.0 } else { 1.0 },
                            previous,
                            draw: SampleDraw::default(),
                            previous_draw,
                            whole: (
                                packet.pixels.iter().filter(|&&value| value == 255).count(),
                                packet.pixels.len(),
                            ),
                            count_window: None,
                            local_counts: None,
                            #[cfg(test)]
                            count_reads: 0,
                        });
                    }
                }
            } else {
                // A rejected or absent packet must not borrow the previous
                // generation's evidence just because its source index matches.
                self.masks[index] = None;
            }
            if let Some(mask) = &mut self.masks[index]
                && mask.previous.is_some()
            {
                let t = ((now - mask.arrived) / 0.16).clamp(0.0, 1.0) as f32;
                mask.alpha = t * t * (3.0 - 2.0 * t);
                if t >= 1.0 {
                    mask.previous = None;
                    mask.previous_draw = SampleDraw::default();
                }
            }
            let width = (rect.width() - gap) * 0.5;
            let cell = Rect::from_min_size(
                rect.min + egui::vec2(index as f32 * (width + gap), 0.0),
                egui::vec2(width, rect.height()),
            );
            let p = ui.painter_at(cell);
            p.text(
                cell.min,
                Align2::LEFT_TOP,
                if index == 0 {
                    "ADMITTED DETAIL"
                } else {
                    "STACK FALLBACK"
                },
                FontId::proportional(8.0),
                color,
            );
            let image_box = Rect::from_min_max(
                cell.min + egui::vec2(0.0, 15.0),
                cell.max - egui::vec2(0.0, 15.0),
            );
            p.rect_filled(image_box, 0.0, PANEL);
            let mask = self.masks[index].as_mut().filter(|mask| {
                valid_packet.is_some_and(|packet| same_mask_domain(mask, packet, extent))
            });
            if let (Some(photo), Some(mask)) = (&self.photo, mask) {
                p.text(
                    cell.right_top(),
                    Align2::RIGHT_TOP,
                    if index == 0 {
                        format!("F{:03}", mask.packet.frame + 1)
                    } else {
                        format!("{} folded", mask.packet.folded)
                    },
                    FontId::monospace(7.0),
                    MUTED,
                );
                let size = context.extent.unwrap_or_else(|| photo.current.size_vec2());
                let scale = (image_box.width() / size.x).min(image_box.height() / size.y);
                let destination = Rect::from_center_size(image_box.center(), size * scale);
                let full = context.aperture;
                if let Some(previous) = &photo.previous {
                    p.image(previous.id(), destination, full, Color32::from_gray(180));
                }
                p.image(
                    photo.current.id(),
                    destination,
                    full,
                    Color32::from_rgba_premultiplied(180, 180, 180, 255)
                        .gamma_multiply(photo.alpha),
                );
                if let Some(previous) = &mask.previous {
                    mask.previous_draw.paint(
                        &p,
                        destination,
                        full,
                        previous,
                        color,
                        1.0 - mask.alpha,
                    );
                }
                mask.draw
                    .paint(&p, destination, full, &mask.glyphs, color, mask.alpha);
                let context_label = if photo.previous.is_some() {
                    format!("stack {}→{}", photo.previous_folded, photo.folded)
                } else {
                    format!("stack {}", photo.folded)
                };
                let galley =
                    p.layout_no_wrap(context_label, FontId::monospace(6.5), Color32::WHITE);
                let backing =
                    Rect::from_min_size(destination.min, galley.size() + egui::vec2(4.0, 2.0));
                p.rect_filled(backing, 0.0, Color32::from_black_alpha(190));
                p.galley(backing.min + egui::vec2(2.0, 1.0), galley, Color32::WHITE);
                let hit = ui.interact(
                    destination,
                    ui.id().with(("contribution-pin", index)),
                    Sense::click_and_drag(),
                );
                let allowed = ui.is_enabled()
                    && ui
                        .ctx()
                        .memory(|memory| memory.is_above_modal_layer(ui.layer_id()));
                if allowed {
                    result.hovered |= hit.hovered() || hit.dragged();
                    if hit.hovered()
                        && let Some(point) = hit.hover_pos()
                    {
                        result.zoom_factor = crate::process_scales::detail_zoom_factor(ui);
                        if result.zoom_factor != 1.0 {
                            result.zoom_anchor =
                                Some(((point - destination.min) / destination.size()).to_pos2());
                        }
                    }
                    if hit.is_pointer_button_down_on()
                        && ui.input(|input| input.pointer.primary_pressed())
                        && let Some(point) = hit.interact_pointer_pos()
                    {
                        self.drag = Some((index, point));
                    }
                    if hit.dragged()
                        && full.width() < 1.0
                        && let Some(point) = hit.interact_pointer_pos()
                        && let Some((active, last)) = self.drag
                        && active == index
                    {
                        result.dragging = true;
                        let delta = point - last;
                        self.drag = Some((active, point));
                        if delta != egui::Vec2::ZERO {
                            result.pin = Some(crate::process_scales::clamp_center(
                                full.center() - delta / destination.size() * full.size(),
                                full.width(),
                            ));
                        }
                        ui.ctx().set_cursor_icon(egui::CursorIcon::Grabbing);
                    } else if hit.clicked()
                        && let Some(point) = hit.interact_pointer_pos()
                    {
                        let uv =
                            full.min + (point - destination.min) / destination.size() * full.size();
                        if hit.double_clicked() {
                            result.reset = true;
                        } else {
                            result.pin = Some(clamped_pin(uv));
                        }
                    }
                }
                hit.context_menu(|ui| {
                    if ui.button("Fit all linked views").clicked() {
                        result.reset = true;
                        ui.close();
                    }
                });
                let pin =
                    destination.min + (context.pin - full.min) / full.size() * destination.size();
                p.circle_stroke(pin, 2.5, Stroke::new(0.8_f32, Color32::WHITE));
                let (local, whole) = mask.counts(full);
                let counts = match local {
                    Some((yes, total)) if total > 0 => {
                        format!("local {yes}/{total} · whole {}/{}", whole.0, whole.1)
                    }
                    _ => format!("local unobserved · whole {}/{}", whole.0, whole.1),
                };
                let spacing = 1u64.checked_shl(context.level as u32).unwrap_or(u64::MAX);
                p.with_clip_rect(cell).text(
                    cell.left_bottom() - egui::vec2(0.0, 12.0),
                    Align2::LEFT_TOP,
                    counts,
                    FontId::proportional(7.0),
                    MUTED,
                );
                let explanation = if index == 0 {
                    "Green points: observed positive support for this capture. Local counts use sample centers inside this view; whole counts use the full sampled map. Gaps are unobserved."
                } else {
                    "Amber points: the accumulated stack has no positive gate denominator at these observed samples, so its configured fallback supplies the coefficient. This is a stack result, not a source-capture map; scrubbing sources does not change it. Local/whole counts describe observed samples, not unsampled area."
                };
                if hit.hovered() {
                    hit.on_hover_text(format!("{explanation}\n{spacing}px coefficient spacing · {:.1}× · map through source {} / {} accepted · photograph {} accepted.\nWheel: zoom together · drag: explore · click: pin · double-click: fit.", full.width().recip(), mask.packet.frame + 1, mask.packet.folded, photo.folded));
                }
            } else {
                p.text(
                    image_box.center(),
                    Align2::CENTER_CENTER,
                    "awaiting aligned contribution",
                    FontId::proportional(7.0),
                    MUTED,
                );
                p.line_segment(
                    [image_box.left_bottom(), image_box.right_bottom()],
                    Stroke::new(0.5_f32, LINE),
                );
            }
        }
        if !ui.input(|input| input.pointer.primary_down())
            || !ui
                .ctx()
                .memory(|memory| memory.is_above_modal_layer(ui.layer_id()))
        {
            self.drag = None;
        }
        if self.transitioning() || result.pin.is_some() || result.zoom_factor != 1.0 {
            ui.ctx().request_repaint();
        }
        result
    }
}

/// Identical normalized aperture for the aligned photograph and every map.
#[cfg(test)]
pub(crate) fn sample_window(pin: Pos2) -> Rect {
    let pin = clamped_pin(pin);
    let min = egui::pos2(
        (pin.x - 0.125).clamp(0.0, 0.75),
        (pin.y - 0.125).clamp(0.0, 0.75),
    );
    Rect::from_min_size(min, egui::vec2(0.25, 0.25))
}

fn clamped_pin(pin: Pos2) -> Pos2 {
    egui::pos2(pin.x.clamp(0.0, 1.0), pin.y.clamp(0.0, 1.0))
}

fn valid_mask(packet: &DiagnosticSurface, kind: DiagnosticKind, level: usize) -> bool {
    packet.sequence > 0
        && packet.folded > 0
        && (kind != DiagnosticKind::GateSupport || packet.folded == 1)
        && packet.kind == kind
        && packet.level == level
        && packet.scale == DiagnosticScale::Linear
        && packet.min == 0.0
        && packet.max == 1.0
        && packet.scope
            == if kind == DiagnosticKind::GateSupport {
                DiagnosticScope::Frame
            } else {
                DiagnosticScope::Stack
            }
        && packet.width > 0
        && packet.width <= crate::process_provenance::SAMPLE_LIMIT[0]
        && packet.height > 0
        && packet.height <= crate::process_provenance::SAMPLE_LIMIT[1]
        && packet.pixels.len() == packet.width * packet.height
        && packet.pixels.iter().all(|value| matches!(value, 0 | 255))
}

fn same_packet(left: &DiagnosticSurface, right: &DiagnosticSurface) -> bool {
    left.sequence == right.sequence
        && left.level == right.level
        && left.frame == right.frame
        && left.folded == right.folded
        && left.width == right.width
        && left.height == right.height
        && left.kind == right.kind
        && left.scope == right.scope
        && left.scale == right.scale
        && left.min.to_bits() == right.min.to_bits()
        && left.max.to_bits() == right.max.to_bits()
        && std::sync::Arc::ptr_eq(&left.pixels, &right.pixels)
}

fn same_mask_domain(mask: &Mask, packet: &DiagnosticSurface, extent: Option<[usize; 2]>) -> bool {
    mask.extent == extent
        && mask.packet.kind == packet.kind
        && mask.packet.level == packet.level
        // The fallback is one accumulating stack map. Its newest source index
        // advances at every fold, without changing its registered domain.
        && (packet.scope == DiagnosticScope::Stack || mask.packet.frame == packet.frame)
}

fn mask_geometry(packet: &DiagnosticSurface, extent: [usize; 2]) -> Option<SampleGeometry> {
    SampleGeometry::new(
        packet.level,
        AdmissionMeta {
            sequence: packet.sequence,
            samples: [packet.width, packet.height],
            extent,
        },
    )
}

type SampleCount = (usize, usize);

#[cfg(test)]
fn sample_counts(
    packet: &DiagnosticSurface,
    extent: Option<[usize; 2]>,
    aperture: Rect,
) -> (Option<SampleCount>, SampleCount) {
    let whole = (
        packet.pixels.iter().filter(|&&value| value == 255).count(),
        packet.pixels.len(),
    );
    let local = extent
        .and_then(|extent| mask_geometry(packet, extent))
        .map(|geometry| {
            packet
                .pixels
                .iter()
                .enumerate()
                .filter_map(|(index, &value)| {
                    geometry
                        .at(index)
                        .filter(|glyph| aperture.contains(glyph.center))
                        .map(|_| value)
                })
                .fold((0, 0), |(positive, total), value| {
                    (positive + usize::from(value == 255), total + 1)
                })
        });
    (local, whole)
}

fn analysis_extent(extent: Option<egui::Vec2>) -> Option<[usize; 2]> {
    let extent = extent?;
    (extent.is_finite()
        && extent.x >= 1.0
        && extent.y >= 1.0
        && extent.x <= 65_536.0
        && extent.y <= 65_536.0
        && extent.x.fract() == 0.0
        && extent.y.fract() == 0.0)
        .then_some([extent.x as usize, extent.y as usize])
}

fn mask_glyphs(packet: &DiagnosticSurface, extent: Option<[usize; 2]>) -> Vec<SampleGlyph> {
    let Some(geometry) = extent.and_then(|extent| mask_geometry(packet, extent)) else {
        return Vec::new();
    };
    packet
        .pixels
        .iter()
        .enumerate()
        .filter_map(|(index, &value)| (value == 255).then(|| geometry.at(index)).flatten())
        .collect()
}

#[cfg(test)]
#[path = "process-contribution-tests.rs"]
mod tests;
