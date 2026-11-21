//! The Stack station's filmstrip (spec 7.2): frames chosen evenly through the
//! stack under the depth rail, each with its plane number and eight marks, one
//! per detail size, showing how much that plane kept at each size.
//!
//! Pictures come only from textures `SourceBrowser` already published: native
//! contacts, with a canonical tier bridging a slot until its contact arrives.
//! Like `PhotoSlot`, a slot never downgrades the same plane: once a canonical
//! picture is shown it stays. The filmstrip never requests or decodes; the
//! station passes `planes()` to `SourceBrowser::poll` as the visible set.
//!
//! Marks are gate support at the noise gate (sampled sites admitted), scaled
//! per detail size across the frames shown, not a share of the blend. A plane
//! without a map at a size draws a dotted mark; an observed zero a flat rule.
// Stage 1 builds the parts; the Stack station composes them in stage 2.
#![allow(dead_code)]

use std::sync::Arc;

use eframe::egui::{self, Align2, Color32, FontId, Rect, Sense, Shape, Stroke, TextureHandle, Ui};

use crate::{process_provenance::AdmissionArchive, workbench::SourcePhoto};

/// Appendix B: 74 × 63 frames; 17 across 1,332 px.
pub(crate) const FRAME: egui::Vec2 = egui::vec2(74.0, 63.0);
const INSET: f32 = 20.0;
const LABEL: f32 = 17.0;
const MIN_GAP: f32 = 2.0;
/// Never more frames than the timeline's contact bound.
pub(crate) const MAX_FRAMES: usize = 48;
/// Canonical bridges retained across all slots (as the timeline's contacts).
const BRIDGE_BYTES: usize = 32 * 1024 * 1024;
const LEVELS: usize = 8;

#[derive(Clone, Copy, Debug, PartialEq)]
pub(crate) struct FilmPalette {
    pub plane: Color32,
    pub accent: Color32,
    pub ink: Color32,
    pub ink3: Color32,
    pub line: Color32,
    pub line2: Color32,
    pub surround: Color32,
    pub spectrum: [Color32; LEVELS],
}
impl FilmPalette {
    pub(crate) const GRAPHITE: Self = Self {
        plane: Color32::from_rgb(0x55, 0xd6, 0xc4),
        accent: Color32::from_rgb(0xe6, 0xb4, 0x50),
        ink: Color32::from_rgb(0xe9, 0xe6, 0xde),
        ink3: Color32::from_rgb(0x80, 0x7e, 0x77),
        line: Color32::from_rgb(0x23, 0x23, 0x26),
        line2: Color32::from_rgb(0x37, 0x37, 0x3c),
        surround: Color32::from_rgb(0x0e, 0x0e, 0x0f),
        spectrum: crate::plane_lens::SPECTRUM_DARK,
    };
}
impl Default for FilmPalette {
    fn default() -> Self {
        Self::GRAPHITE
    }
}

/// How many frames fit: 17 at 1,332 px, never more than `MAX_FRAMES`.
pub(crate) fn frame_count(width: f32, planes: usize) -> usize {
    if planes == 0 || !width.is_finite() {
        return 0;
    }
    let usable = width - 2.0 * INSET + MIN_GAP;
    ((usable / (FRAME.x + MIN_GAP)).floor().max(1.0) as usize)
        .min(MAX_FRAMES)
        .min(planes)
}

/// Planes evenly through the stack, first and last included.
pub(crate) fn chosen_planes(planes: usize, count: usize) -> Vec<usize> {
    match (planes, count) {
        (0, _) | (_, 0) => Vec::new(),
        (_, 1) => vec![0],
        _ => (0..count)
            .map(|slot| {
                ((slot as u128 * (planes - 1) as u128 * 2 + (count - 1) as u128)
                    / (2 * (count - 1) as u128)) as usize
            })
            .collect(),
    }
}

#[derive(Clone)]
struct Slot {
    plane: usize,
    native: Option<TextureHandle>,
    /// A canonical tier shown before the contact arrived. Never downgraded.
    bridge: Option<(TextureHandle, usize)>,
}

#[derive(Clone, Copy, Debug, PartialEq)]
struct MarkKey {
    rect: Rect,
    revision: u64,
    count: usize,
    palette: FilmPalette,
    pixels_per_point: f32,
}

#[derive(Clone, Copy, Debug, Default, PartialEq, Eq)]
pub(crate) struct FilmResponse {
    pub hovered: Option<usize>,
    pub clicked: Option<usize>,
}

/// What the strip marks this frame.
#[derive(Clone, Copy, Debug, Default, PartialEq, Eq)]
pub(crate) struct FilmMarks {
    /// The plane under the pointer anywhere (rail or strip): the nearest frame
    /// gets a plane-colour outline.
    pub pointer: Option<usize>,
    /// The held plane: its nearest frame gets the accent outline.
    pub held: Option<usize>,
}

#[derive(Default)]
pub(crate) struct Filmstrip {
    /// Textures belong to one run; another run's plane 20 is not this one's.
    epoch: Option<u64>,
    planes: usize,
    slots: Vec<Slot>,
    /// Kept share per slot and level; None is "no map".
    shares: Vec<[Option<f32>; LEVELS]>,
    share_key: Option<(u64, usize, usize)>,
    marks: Option<(MarkKey, Arc<egui::Mesh>)>,
    #[cfg(test)]
    pub(crate) mark_builds: usize,
    #[cfg(test)]
    pub(crate) share_reads: usize,
}

impl Filmstrip {
    /// Choose the frames for this width. O(1) unless the plane count or the
    /// number of frames changed.
    pub(crate) fn layout(&mut self, width: f32, planes: usize) {
        let count = frame_count(width, planes);
        if self.planes == planes && self.slots.len() == count {
            return;
        }
        self.planes = planes;
        let old = std::mem::take(&mut self.slots);
        self.slots = chosen_planes(planes, count)
            .into_iter()
            .map(|plane| {
                old.iter()
                    .find(|slot| slot.plane == plane)
                    .cloned()
                    .unwrap_or(Slot {
                        plane,
                        native: None,
                        bridge: None,
                    })
            })
            .collect();
        self.share_key = None;
    }

    /// The planes shown, for `SourceBrowser::poll`'s visible set.
    pub(crate) fn planes(&self) -> Vec<usize> {
        self.slots.iter().map(|slot| slot.plane).collect()
    }

    /// Adopt textures the browser already published. `photos` are native
    /// contacts; `canonical` are scrub/overview/image tiers.
    pub(crate) fn sync(&mut self, epoch: u64, photos: &[SourcePhoto], canonical: &[SourcePhoto]) {
        if self.epoch != Some(epoch) {
            self.epoch = Some(epoch);
            for slot in &mut self.slots {
                slot.native = None;
                slot.bridge = None;
            }
        }
        let mut used: usize = self
            .slots
            .iter()
            .filter_map(|slot| slot.bridge.as_ref().map(|(_, bytes)| *bytes))
            .sum();
        for slot in &mut self.slots {
            if slot.native.is_none()
                && let Some(photo) = photos
                    .iter()
                    .find(|photo| photo.epoch == epoch && photo.index == slot.plane)
            {
                slot.native = Some(photo.texture.clone());
            }
            if slot.native.is_none()
                && slot.bridge.is_none()
                && let Some(photo) = canonical
                    .iter()
                    .find(|photo| photo.epoch == epoch && photo.index == slot.plane)
            {
                let [width, height] = photo.texture.size();
                let bytes = width.saturating_mul(height).saturating_mul(4);
                if used + bytes <= BRIDGE_BYTES {
                    used += bytes;
                    slot.bridge = Some((photo.texture.clone(), bytes));
                }
            }
        }
    }

    /// Kept shares for the shown planes at every level, read only when the
    /// archive revision or the frames change (17 × 8 counts, never per plane).
    pub(crate) fn update(&mut self, archive: &AdmissionArchive) {
        let key = (archive.revision(), self.planes, self.slots.len());
        if self.share_key == Some(key) {
            return;
        }
        self.share_key = Some(key);
        self.shares = self
            .slots
            .iter()
            .map(|slot| {
                std::array::from_fn(|level| {
                    archive
                        .counts(level, slot.plane)
                        .filter(|&(_, observed)| observed > 0)
                        .map(|(admitted, observed)| admitted as f32 / observed as f32)
                })
            })
            .collect();
        #[cfg(test)]
        {
            self.share_reads += 1;
        }
    }

    pub(crate) fn frame_rect(&self, rect: Rect, slot: usize) -> Rect {
        let count = self.slots.len().max(1);
        let span = rect.width() - 2.0 * INSET - FRAME.x;
        let pitch = if count > 1 {
            span / (count - 1) as f32
        } else {
            0.0
        };
        let left = if count > 1 {
            rect.left() + INSET + pitch * slot as f32
        } else {
            rect.center().x - FRAME.x * 0.5
        };
        Rect::from_min_size(egui::pos2(left, rect.top() + 4.0), FRAME)
    }

    /// The slot whose plane is nearest `plane`.
    pub(crate) fn nearest(&self, plane: usize) -> Option<usize> {
        self.slots
            .iter()
            .enumerate()
            .min_by_key(|(_, slot)| slot.plane.abs_diff(plane))
            .map(|(index, _)| index)
    }

    pub(crate) fn interact(&self, ui: &mut Ui, rect: Rect, id: egui::Id) -> FilmResponse {
        let mut response = FilmResponse::default();
        for (index, slot) in self.slots.iter().enumerate() {
            let hit = ui.interact(self.frame_rect(rect, index), id.with(index), Sense::click());
            if hit.hovered() {
                response.hovered = Some(slot.plane);
            }
            if hit.clicked() {
                response.clicked = Some(slot.plane);
            }
        }
        response
    }

    pub(crate) fn paint(
        &mut self,
        painter: &egui::Painter,
        rect: Rect,
        palette: FilmPalette,
        marks: FilmMarks,
    ) {
        let key = MarkKey {
            rect,
            revision: self.share_key.map_or(0, |key| key.0),
            count: self.slots.len(),
            palette,
            pixels_per_point: painter.ctx().pixels_per_point(),
        };
        if self.marks.as_ref().is_none_or(|(old, _)| *old != key) {
            #[cfg(test)]
            {
                self.mark_builds += 1;
            }
            let mesh = self.marks_mesh(rect, palette, painter.ctx());
            self.marks = Some((key, Arc::new(mesh)));
        }
        let nearest = marks.pointer.and_then(|plane| self.nearest(plane));
        let held = marks.held.and_then(|plane| self.nearest(plane));
        for (index, slot) in self.slots.iter().enumerate() {
            let frame = self.frame_rect(rect, index);
            let image =
                Rect::from_min_max(frame.min, egui::pos2(frame.right(), frame.bottom() - LABEL));
            painter.rect_filled(image, 0.0, palette.surround);
            if let Some(texture) = slot
                .bridge
                .as_ref()
                .map(|(texture, _)| texture)
                .or(slot.native.as_ref())
            {
                painter.image(
                    texture.id(),
                    image,
                    cover_uv(texture, image),
                    Color32::WHITE,
                );
            }
            let is_held = held == Some(index);
            painter.text(
                egui::pos2(frame.left() + 1.0, frame.bottom() - LABEL * 0.5 + 1.0),
                Align2::LEFT_CENTER,
                (slot.plane + 1).to_string(),
                FontId::proportional(10.0),
                if is_held { palette.ink } else { palette.ink3 },
            );
            if is_held {
                painter.rect_stroke(
                    image,
                    0.0,
                    Stroke::new(1.5_f32, palette.accent),
                    egui::StrokeKind::Outside,
                );
            } else if nearest == Some(index) {
                painter.rect_stroke(
                    image,
                    0.0,
                    Stroke::new(1.5_f32, palette.plane),
                    egui::StrokeKind::Outside,
                );
            }
        }
        if let Some((_, mesh)) = &self.marks {
            painter.add(Shape::mesh(mesh.clone()));
        }
    }

    /// Eight marks per frame, scaled per level by the busiest shown frame.
    fn marks_mesh(&self, rect: Rect, palette: FilmPalette, ctx: &egui::Context) -> egui::Mesh {
        let mut mesh = egui::Mesh::default();
        let peaks: [f32; LEVELS] = std::array::from_fn(|level| {
            self.shares
                .iter()
                .filter_map(|shares| shares[level])
                .fold(0.0, f32::max)
        });
        let px = 1.0 / ctx.pixels_per_point();
        for (index, shares) in self.shares.iter().enumerate().take(self.slots.len()) {
            let frame = self.frame_rect(rect, index);
            let base = frame.bottom() - 4.0;
            let right = frame.right() - 1.0;
            for level in 0..LEVELS {
                let x = right - (LEVELS - level) as f32 * 4.0;
                let color = palette.spectrum[level];
                match shares[level] {
                    Some(share) if share > 0.0 && peaks[level] > 0.0 => {
                        let value = (share / peaks[level]).clamp(0.0, 1.0).powf(0.7);
                        let height = 1.0 + value * 7.0;
                        mesh.add_colored_rect(
                            Rect::from_min_max(
                                egui::pos2(x, base - height),
                                egui::pos2(x + 3.0, base),
                            ),
                            color.gamma_multiply(0.25 + 0.75 * value),
                        );
                    }
                    Some(_) => {
                        // Observed zero: a flat rule.
                        mesh.add_colored_rect(
                            Rect::from_min_max(egui::pos2(x, base - px), egui::pos2(x + 3.0, base)),
                            palette.line2,
                        );
                    }
                    None => {
                        // No map: a dotted rule, never a zero.
                        mesh.add_colored_rect(
                            Rect::from_min_max(
                                egui::pos2(x + 1.0, base - px),
                                egui::pos2(x + 2.0, base),
                            ),
                            palette.line2,
                        );
                    }
                }
            }
        }
        mesh
    }
}

/// Crop a texture to fill `image` (centre crop), as the timeline's contacts.
fn cover_uv(texture: &TextureHandle, image: Rect) -> Rect {
    let [width, height] = texture.size();
    let source = width as f32 / height.max(1) as f32;
    let target = image.width() / image.height().max(f32::EPSILON);
    let extent = if source > target {
        egui::vec2(target / source, 1.0)
    } else {
        egui::vec2(1.0, source / target)
    };
    Rect::from_center_size(egui::pos2(0.5, 0.5), extent)
}

#[cfg(test)]
#[path = "filmstrip-tests.rs"]
mod tests;
