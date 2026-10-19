//! Fixed capture positions populated only by native contact previews.
//! Decode arrival, processing position and cache eviction never choose slots.

use std::collections::BTreeMap;

use eframe::egui::{self, Align2, Color32, FontId, Rect, Sense, Stroke, TextureHandle, Ui};

use crate::{
    pipeline::FrameObservation,
    process_space::{Input, Response},
    theme::{ACCENT, AMBER, BG, GREEN, INK, LINE, MUTED},
};

const MAX_CONTACTS: usize = 16;
const CONTACT_WIDTH: f32 = 64.0;

#[derive(Default)]
pub struct CaptureAxis {
    key: Option<(u64, usize, u32)>,
    anchors: Vec<usize>,
    contacts: BTreeMap<usize, TextureHandle>,
}

impl CaptureAxis {
    /// The exact fixed contacts the owner should prefetch after the first paint.
    pub fn indices(&self) -> Vec<usize> {
        self.anchors.clone()
    }

    pub fn show(&mut self, ui: &mut Ui, rect: Rect, input: &Input<'_>, response: &mut Response) {
        let key = (input.epoch, input.frame_count, rect.width().to_bits());
        if self.key != Some(key) {
            let same_capture = self.key.is_some_and(|old| old.0 == key.0 && old.1 == key.1);
            self.anchors = anchors(input.frame_count, rect.width());
            if same_capture {
                self.contacts
                    .retain(|index, _| self.anchors.contains(index));
            } else {
                self.contacts.clear();
            }
            self.key = Some(key);
        }
        if self.anchors.is_empty() || rect.height() <= 0.0 {
            return;
        }

        // Input.photos is the native contact lane. Canonical inspection images
        // are intentionally never consulted, even for a currently empty slot.
        for photo in input
            .photos
            .iter()
            .filter(|photo| photo.epoch == input.epoch)
        {
            if self.anchors.contains(&photo.index) {
                self.contacts
                    .entry(photo.index)
                    .or_insert_with(|| photo.texture.clone());
            }
        }

        let layout = Layout::new(rect, self.anchors.len());
        let painter = ui.painter_at(rect);
        let axis_y = rect.top() + 4.0;
        painter.line_segment(
            [
                egui::pos2(layout.left, axis_y),
                egui::pos2(layout.right, axis_y),
            ],
            Stroke::new(0.7_f32, LINE),
        );
        for &index in &input.progress.alignment_plane_observations {
            if index < input.frame_count {
                let x = layout.x(index, input.frame_count);
                painter.line_segment(
                    [
                        egui::pos2(x, rect.top() + 0.5),
                        egui::pos2(x, rect.top() + 3.0),
                    ],
                    Stroke::new(1.0_f32, GREEN),
                );
            }
        }
        for &index in &input.progress.alignment_pyramid_observations {
            if index < input.frame_count {
                let x = layout.x(index, input.frame_count);
                painter.line_segment(
                    [
                        egui::pos2(x, rect.top() + 5.0),
                        egui::pos2(x, rect.top() + 7.5),
                    ],
                    Stroke::new(1.0_f32, ACCENT),
                );
            }
        }
        for (&index, state) in &input.progress.frame_observations {
            if index < input.frame_count && *state == FrameObservation::Processed {
                let x = layout.x(index, input.frame_count);
                painter.line_segment(
                    [
                        egui::pos2(x, rect.top() + 9.0),
                        egui::pos2(x, rect.top() + 11.0),
                    ],
                    Stroke::new(1.2_f32, GREEN),
                );
            }
        }

        let pair = input
            .inspected_pair
            .or(input.progress.alignment_current_pair)
            .or(input.progress.alignment_latest_pair)
            .filter(|pair| pair.iter().all(|index| *index < input.frame_count));
        if let Some(pair) = pair {
            let colour = if input.inspected_pair.is_some() {
                AMBER
            } else if input.progress.alignment_current_pair.is_some() {
                ACCENT
            } else {
                MUTED
            };
            let a = layout.x(pair[0], input.frame_count);
            let b = layout.x(pair[1], input.frame_count);
            painter.line_segment(
                [egui::pos2(a, axis_y), egui::pos2(b, axis_y)],
                Stroke::new(1.5_f32, colour),
            );
            for x in [a, b] {
                painter.line_segment(
                    [egui::pos2(x, axis_y - 3.0), egui::pos2(x, axis_y + 3.0)],
                    Stroke::new(1.5_f32, colour),
                );
            }
        }

        let selected = input.selected.min(input.frame_count - 1);
        painter.circle_stroke(
            egui::pos2(layout.x(selected, input.frame_count), axis_y),
            3.2,
            Stroke::new(1.2_f32, ACCENT),
        );
        if let Some(index) = input
            .progress
            .processing_frame
            .filter(|index| *index < input.frame_count)
        {
            let x = layout.x(index, input.frame_count);
            painter.add(egui::Shape::convex_polygon(
                vec![
                    egui::pos2(x - 2.5, rect.top() + 8.0),
                    egui::pos2(x + 2.5, rect.top() + 8.0),
                    egui::pos2(x, rect.top() + 11.0),
                ],
                GREEN,
                Stroke::NONE,
            ));
        }

        for &index in &self.anchors {
            let image = layout.contact(index, input.frame_count);
            painter.rect_filled(image, 1.5, BG);
            if let Some(texture) = self.contacts.get(&index) {
                painter.image(
                    texture.id(),
                    image,
                    contact_uv(texture, image),
                    Color32::WHITE,
                );
            }
            painter.rect_stroke(
                image,
                1.5,
                Stroke::new(
                    if index == selected { 1.1_f32 } else { 0.7_f32 },
                    if index == selected { ACCENT } else { LINE },
                ),
                egui::StrokeKind::Inside,
            );
            painter.text(
                egui::pos2(image.center().x, image.bottom() + 6.0),
                Align2::CENTER_CENTER,
                format!("{:03}", index + 1),
                FontId::monospace(8.5),
                if index == selected { INK } else { MUTED },
            );
        }

        let index_at = |at: egui::Pos2| {
            self.anchors
                .iter()
                .copied()
                .find(|index| {
                    let image = layout.contact(*index, input.frame_count);
                    Rect::from_min_max(image.min, egui::pos2(image.right(), rect.bottom()))
                        .contains(at)
                })
                .unwrap_or_else(|| layout.index(at.x, input.frame_count))
        };
        let hit = ui.interact(rect, ui.id().with("capture-axis"), Sense::click());
        if hit.clicked()
            && let Some(at) = hit.interact_pointer_pos()
        {
            response.selected = Some(index_at(at));
        }
        if let Some(at) = hit.hover_pos() {
            let index = index_at(at);
            let pair_note = pair.map_or_else(String::new, |pair| {
                format!(
                    " · {} {:03} / {:03}",
                    if input.inspected_pair.is_some() {
                        "Inspected pair"
                    } else if input.progress.alignment_current_pair.is_some() {
                        "Comparing"
                    } else {
                        "Last comparison"
                    },
                    pair[0] + 1,
                    pair[1] + 1
                )
            });
            hit.on_hover_cursor(egui::CursorIcon::PointingHand)
                .on_hover_text(format!(
                    "Capture {:03} / {}{pair_note}",
                    index + 1,
                    input.frame_count
                ));
        }
    }
}

fn anchors(count: usize, width: f32) -> Vec<usize> {
    if count == 0 || !width.is_finite() || width <= 0.0 {
        return Vec::new();
    }
    if count == 1 {
        return vec![0];
    }
    let slots = ((width / (CONTACT_WIDTH + 12.0)).floor() as usize)
        .clamp(2, MAX_CONTACTS)
        .min(count);
    (0..slots)
        .map(|slot| {
            ((slot as u128 * (count - 1) as u128 + (slots - 1) as u128 / 2) / (slots - 1) as u128)
                as usize
        })
        .collect()
}

struct Layout {
    rect: Rect,
    left: f32,
    right: f32,
    width: f32,
    height: f32,
}
impl Layout {
    fn new(rect: Rect, slots: usize) -> Self {
        let width = (rect.width() / slots as f32 - 8.0).clamp(0.0, CONTACT_WIDTH);
        Self {
            rect,
            left: rect.left() + width * 0.5,
            right: rect.right() - width * 0.5,
            width,
            height: (rect.height() - 24.0).clamp(0.0, 34.0),
        }
    }
    fn x(&self, index: usize, count: usize) -> f32 {
        if count <= 1 {
            (self.left + self.right) * 0.5
        } else {
            self.left + (self.right - self.left) * index as f32 / (count - 1) as f32
        }
    }
    fn index(&self, x: f32, count: usize) -> usize {
        if count <= 1 || self.right <= self.left {
            0
        } else {
            (((x - self.left) / (self.right - self.left)).clamp(0.0, 1.0) * (count - 1) as f32)
                .round() as usize
        }
    }
    fn contact(&self, index: usize, count: usize) -> Rect {
        Rect::from_center_size(
            egui::pos2(
                self.x(index, count),
                self.rect.top() + 12.0 + self.height * 0.5,
            ),
            egui::vec2(self.width, self.height),
        )
    }
}

fn contact_uv(texture: &TextureHandle, image: Rect) -> Rect {
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
#[path = "capture-axis-tests.rs"]
mod tests;
