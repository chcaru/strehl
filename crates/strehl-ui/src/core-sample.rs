//! The core sample (Studio 2, spec 7.2): one region of the photograph, plane
//! by plane. It replaces the "This region / source support" popover.
//!
//! Hovering the photograph marks a square (corner marks and the sampled sites
//! the leading planes kept); the popover opens beside it with a hairline
//! leader: the final crop and the three leading planes, eight strips (one per
//! detail size, plane by plane), one sentence, and the engine's caution. A
//! click pins the sample; a pinned sample offers Show the plane, Repair here…
//! and Note.
//!
//! Honesty: "kept" is support at the noise gate, not a share of the blend,
//! and planes overlap. Plane crops come from each plane's resident camera
//! preview, unregistered, so they are approximate. The sentence reports the
//! spans where the region's kept share is at least half and a fifth of its
//! peak; the fallback clause appears only when the averaging map is known.
//!
//! Performance: counts come from `RegionProbe`, which recounts only when the
//! sampled window (its cell set) changes. The strips and the reticle's dots
//! are built once per window key and level; pointer motion inside a cell
//! rebuilds nothing. The live popover registers no widget. Crops read only
//! textures already resident; a hover never requests a decode.
// Stage 1 builds the parts; the Stack station composes them in stage 2.
#![allow(dead_code)]

use std::sync::Arc;

use eframe::egui::{
    self, Align2, Color32, FontId, Pos2, Rect, Sense, Shape, Stroke, TextureId, Ui, Vec2,
    emath::TSTransform,
};

use crate::{
    depth_rail::tracked,
    plane_lens::{DETAIL_LEVELS, LensPhoto, size_label},
    process_output_space::OutputGeometry,
    process_provenance::AdmissionArchive,
    process_region_probe::{RegionProbe, SampleCount, popup_placement, region_at},
};

pub(crate) const WIDTH: f32 = 330.0;
const PAD: f32 = 15.0;
const LABEL_COLUMN: f32 = 34.0;
const ROW: f32 = 8.0;
const ROW_GAP: f32 = 3.0;
pub(crate) const CAUTION: &str = "Kept is support at the noise gate, not a share of the blend. Planes can overlap. Ctrl + wheel resizes the region.";

#[derive(Clone, Copy, Debug, PartialEq)]
pub(crate) struct CorePalette {
    pub accent: Color32,
    pub ink: Color32,
    pub ink2: Color32,
    pub ink3: Color32,
    pub line: Color32,
    pub line2: Color32,
    pub panel: Color32,
    pub surround: Color32,
    pub spectrum: [Color32; DETAIL_LEVELS],
}
impl CorePalette {
    pub(crate) const GRAPHITE: Self = Self {
        accent: Color32::from_rgb(0xe6, 0xb4, 0x50),
        ink: Color32::from_rgb(0xe9, 0xe6, 0xde),
        ink2: Color32::from_rgb(0xa1, 0x9f, 0x98),
        ink3: Color32::from_rgb(0x80, 0x7e, 0x77),
        line: Color32::from_rgb(0x23, 0x23, 0x26),
        line2: Color32::from_rgb(0x37, 0x37, 0x3c),
        panel: Color32::from_rgb(0x11, 0x11, 0x12),
        surround: Color32::from_rgb(0x0e, 0x0e, 0x0f),
        spectrum: crate::plane_lens::SPECTRUM_DARK,
    };
}
impl Default for CorePalette {
    fn default() -> Self {
        Self::GRAPHITE
    }
}

#[derive(Clone, Copy, Debug, PartialEq)]
pub(crate) enum CoreAction {
    /// Hold the leading plane (zero-based).
    ShowPlane(usize),
    /// Open Develop with the depth brush on this region (aperture UV).
    Repair(Rect),
    Note(Rect),
}

/// The certified photograph and its evidence.
#[derive(Clone, Copy)]
pub(crate) struct CoreInput<'a> {
    pub archive: &'a AdmissionArchive,
    pub level: usize,
    pub analysis_extent: [usize; 2],
    /// The final photograph's pixel size.
    pub extent: [usize; 2],
    pub planes: usize,
    /// The photograph on screen and the UV window it shows.
    pub image: Rect,
    pub aperture: Rect,
    pub final_texture: Option<TextureId>,
    pub geometry: Option<OutputGeometry>,
    /// The viewport the popover must stay inside.
    pub viewport: Rect,
}

#[derive(Clone, Debug, Default, PartialEq)]
pub(crate) struct CoreResponse {
    /// The region shown (aperture UV), live or pinned.
    pub region: Option<Rect>,
    pub live: bool,
    pub leading: Vec<usize>,
    /// The peak of the region's profile at the level: the rail's head.
    pub peak: Option<usize>,
    pub action: Option<CoreAction>,
    /// The popover's screen rect; a click inside it is not a new pin.
    pub popover: Option<Rect>,
}

/// Where a profile stays at or above a fraction of its peak (zero-based,
/// inclusive), as the mockup's `span`.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(crate) struct Span {
    pub peak: usize,
    pub first: usize,
    pub last: usize,
}

pub(crate) fn span(values: &[f32], level: f32) -> Option<Span> {
    let (peak, top) =
        values
            .iter()
            .copied()
            .enumerate()
            .fold((0, 0.0_f32), |best, (index, value)| {
                if value > best.1 { (index, value) } else { best }
            });
    if top <= 0.0 {
        return None;
    }
    let (mut first, mut last) = (peak, peak);
    while first > 0 && values[first - 1] >= top * level {
        first -= 1;
    }
    while last + 1 < values.len() && values[last + 1] >= top * level {
        last += 1;
    }
    Some(Span { peak, first, last })
}

/// The one-sentence summary. `fallback` is the averaging map's share of the
/// region's sampled sites, when that map is known.
pub(crate) fn sentence(
    values: &[f32],
    observed: bool,
    size: &str,
    fallback: Option<f32>,
) -> String {
    let filled = match fallback {
        Some(share) if share > 0.0 => format!(
            " The fallback average filled {} of the sampled sites.",
            crate::plane_lens::percent(Some(share))
        ),
        Some(_) => " Nothing was filled in.".into(),
        None => String::new(),
    };
    if !observed {
        return format!("No plane recorded samples here at {size}.");
    }
    let (Some(half), Some(fifth)) = (span(values, 0.5), span(values, 0.2)) else {
        return format!("No plane passed the noise gate here at {size}.{filled}");
    };
    let planes = half.last - half.first + 1;
    let range = |span: Span| {
        if span.first == span.last {
            format!("plane {}", span.first + 1)
        } else {
            format!("planes {}\u{2013}{}", span.first + 1, span.last + 1)
        }
    };
    let main = if planes == 1 {
        format!("Detail at {size} here comes from {}", range(half))
    } else {
        format!(
            "Detail at {size} here comes from {} ({planes} planes)",
            range(half)
        )
    };
    let wide = if fifth != half {
        format!(", with fainter support from {}", range(fifth))
    } else {
        String::new()
    };
    format!("{main}{wide}.{filled}")
}

#[derive(Clone, Copy, Debug, PartialEq)]
struct StripKey {
    window: u64,
    level: usize,
    planes: usize,
    leading: [Option<usize>; 3],
    palette: CorePalette,
    pixels_per_point: f32,
}

#[derive(Clone, Copy, Debug, PartialEq)]
struct SitesKey {
    window: u64,
    image: Rect,
    aperture: Rect,
    color: Color32,
}

#[derive(Default)]
struct Profile {
    window: u64,
    level: usize,
    planes: usize,
    values: Vec<f32>,
    observed: bool,
}

/// The core sample: a `RegionProbe` plus its own popover and reticle.
#[derive(Default)]
pub(crate) struct CoreSample {
    probe: RegionProbe,
    /// The pinned centre in aperture UV.
    pinned: Option<Pos2>,
    profile: Profile,
    /// The last pinned popover: the pointer on it is not a new live region.
    popover: Option<Rect>,
    strips: Option<(StripKey, Arc<egui::Mesh>)>,
    sites: Option<(SitesKey, Arc<egui::Mesh>)>,
    #[cfg(test)]
    pub(crate) strip_builds: usize,
    #[cfg(test)]
    pub(crate) profile_builds: usize,
}

impl CoreSample {
    pub(crate) fn probe_mut(&mut self) -> &mut RegionProbe {
        &mut self.probe
    }
    pub(crate) fn pinned(&self) -> bool {
        self.pinned.is_some()
    }
    /// Pin the sample at a clicked screen point on the photograph.
    pub(crate) fn pin(&mut self, at: Pos2, image: Rect, aperture: Rect) {
        if image.contains(at) && image.is_positive() {
            self.pinned = Some(aperture.min + (at - image.min) / image.size() * aperture.size());
        }
    }
    /// Escape closes the pinned sample. Returns whether it was pinned.
    pub(crate) fn unpin(&mut self) -> bool {
        self.popover = None;
        self.pinned.take().is_some()
    }

    /// The rail's dashed region line: per plane (admitted, observed) at the
    /// level, read only when `key` changes (pass it to `DepthRail::set_region`).
    pub(crate) fn rail_key(&self, level: usize) -> Option<u64> {
        self.probe
            .measured_region()
            .map(|_| self.probe.window_revision().rotate_left(8) ^ level as u64)
    }
    pub(crate) fn rail_series(
        &self,
        level: usize,
    ) -> impl Iterator<Item = (usize, usize, usize)> + '_ {
        self.probe
            .window_counts(level)
            .map(|(plane, count)| (plane, count.admitted, count.observed))
    }

    /// Measure and paint. `previews` returns a resident preview tier for a
    /// plane, or None; it must never start a decode.
    pub(crate) fn show(
        &mut self,
        ui: &mut Ui,
        input: CoreInput<'_>,
        previews: &dyn Fn(usize) -> Option<LensPhoto>,
        palette: CorePalette,
    ) -> CoreResponse {
        let mut response = CoreResponse::default();
        if input.planes == 0 || input.extent.contains(&0) || input.analysis_extent.contains(&0) {
            return response;
        }
        let over_popover = self.pinned.is_some()
            && self.popover.is_some_and(|popover| {
                ui.input(|state| state.pointer.hover_pos())
                    .is_some_and(|at| popover.expand(4.0).contains(at))
            });
        let live = (!over_popover)
            .then(|| self.probe.current_region(ui, input.image, input.aperture))
            .flatten();
        let region = live.or_else(|| {
            let pinned = self.pinned?;
            let at = input.image.min
                + (pinned - input.aperture.min) / input.aperture.size() * input.image.size();
            region_at(input.image, input.aperture, at, self.probe.side())
        });
        let Some(region) = region else {
            self.popover = None;
            return response;
        };
        response.region = Some(region);
        response.live = live.is_some();
        self.probe.measure(
            input.archive,
            input.level,
            input.analysis_extent,
            input.planes,
            region,
        );
        self.update_profile(input.level, input.planes);
        let leading = self.probe.leading();
        response.leading = leading.clone();
        response.peak = span(&self.profile.values, 0.5).map(|span| span.peak);

        let project = |uv: Pos2| {
            input.image.min + (uv - input.aperture.min) / input.aperture.size() * input.image.size()
        };
        let outline = Rect::from_min_max(project(region.min), project(region.max));
        self.paint_reticle(ui, input, outline, palette);

        // Lay out the text first: the popover's height depends on it.
        let ctx = ui.ctx().clone();
        let inner = WIDTH - 2.0 * PAD;
        let size = size_label(input.level, input.geometry);
        let fallback = self.probe.fallback_fraction(input.level);
        let words = sentence(&self.profile.values, self.profile.observed, &size, fallback);
        let words = ctx
            .fonts_mut(|fonts| fonts.layout(words, FontId::proportional(13.0), palette.ink, inner));
        let caution = ctx.fonts_mut(|fonts| {
            fonts.layout(
                CAUTION.to_owned(),
                FontId::proportional(11.0),
                palette.ink3,
                inner,
            )
        });
        let pinned = live.is_none();
        let crop = (inner - 3.0 * 8.0) / 4.0;
        let strips_top = 38.0 + crop + 16.0 + 26.0;
        let strips_bottom = strips_top + DETAIL_LEVELS as f32 * (ROW + ROW_GAP);
        let words_top = strips_bottom + 22.0;
        let caution_top = words_top + words.size().y + 14.0;
        let mut height = caution_top + caution.size().y + 12.0;
        if pinned {
            height += 34.0;
        }
        let placement = popup_placement(
            input.viewport.shrink(8.0),
            outline,
            egui::vec2(WIDTH, height),
        );
        if placement.width() < WIDTH - 1.0 || placement.height() < height - 1.0 {
            return response;
        }
        response.popover = Some(placement);
        self.popover = pinned.then_some(placement);
        // Paint in popover-local coordinates on a tooltip layer moved by its
        // transform, so only the window key rebuilds the strips.
        let layer = egui::LayerId::new(egui::Order::Tooltip, ui.id().with("core-sample"));
        ctx.set_transform_layer(
            layer,
            TSTransform::from_translation(placement.min.to_vec2()),
        );
        let local = Rect::from_min_size(Pos2::ZERO, placement.size());
        let painter = ctx.layer_painter(layer).with_clip_rect(local.expand(6.0));
        painter.rect_filled(
            local.translate(egui::vec2(0.0, 4.0)),
            0.0,
            Color32::from_black_alpha(80),
        );
        painter.rect_filled(local, 0.0, palette.panel);
        painter.rect_stroke(
            local,
            0.0,
            Stroke::new(1.0_f32, palette.line2),
            egui::StrokeKind::Inside,
        );

        // Header: title, live/pinned tag, size and position in photograph px.
        let title = tracked(&ctx, "CORE SAMPLE".into(), 10.5, palette.ink2, 1.3);
        painter.galley(egui::pos2(PAD, 14.0), title.clone(), palette.ink2);
        let tag = tracked(
            &ctx,
            if pinned { "PINNED" } else { "LIVE" }.into(),
            9.5,
            if pinned { palette.accent } else { palette.ink3 },
            1.0,
        );
        let tag_rect = Rect::from_min_size(
            egui::pos2(PAD + title.size().x + 10.0, 12.0),
            tag.size() + egui::vec2(8.0, 4.0),
        );
        painter.rect_stroke(
            tag_rect,
            0.0,
            Stroke::new(
                1.0_f32,
                if pinned {
                    palette.accent
                } else {
                    palette.line2
                },
            ),
            egui::StrokeKind::Inside,
        );
        painter.galley(tag_rect.min + egui::vec2(4.0, 2.0), tag, palette.ink3);
        let side = (region.width() * input.extent[0] as f32).round();
        let centre = region.center();
        painter.text(
            egui::pos2(WIDTH - PAD, tag_rect.center().y),
            Align2::RIGHT_CENTER,
            format!(
                "{side:.0} px square at {:.0}, {:.0}",
                centre.x * input.extent[0] as f32,
                centre.y * input.extent[1] as f32
            ),
            FontId::proportional(11.0),
            palette.ink3,
        );

        // Crops: the final, then the three leading planes (approximate).
        let crops: Vec<Rect> = (0..4)
            .map(|slot| {
                Rect::from_min_size(
                    egui::pos2(PAD + slot as f32 * (crop + 8.0), 38.0),
                    Vec2::splat(crop),
                )
            })
            .collect();
        let local_painter = painter.clone();
        local_painter.rect_filled(crops[0], 0.0, palette.surround);
        if let Some(texture) = input.final_texture {
            let mut mesh = egui::Mesh::with_texture(texture);
            mesh.add_rect_with_uv(crops[0], region, Color32::WHITE);
            local_painter.add(Shape::mesh(mesh));
        }
        caption(&local_painter, crops[0], "final".into(), palette.ink, true);
        for (slot, crop_rect) in crops.iter().enumerate().skip(1) {
            local_painter.rect_filled(*crop_rect, 0.0, palette.surround);
            let Some(&plane) = leading.get(slot - 1) else {
                continue;
            };
            if let Some(preview) = previews(plane) {
                // Unregistered camera preview: the same normalised window.
                let uv = Rect::from_min_max(
                    preview.uv.min + region.min.to_vec2() * preview.uv.size(),
                    preview.uv.min + region.max.to_vec2() * preview.uv.size(),
                );
                let mut mesh = egui::Mesh::with_texture(preview.texture);
                mesh.add_rect_with_uv(*crop_rect, uv, Color32::WHITE);
                local_painter.add(Shape::mesh(mesh));
            } else {
                local_painter.text(
                    crop_rect.center(),
                    Align2::CENTER_CENTER,
                    (plane + 1).to_string(),
                    FontId::proportional(11.0),
                    palette.ink3,
                );
            }
            let share = self
                .probe
                .window_counts(input.level)
                .find(|(frame, _)| *frame == plane)
                .and_then(|(_, count)| count.fraction());
            caption(
                &local_painter,
                *crop_rect,
                format!(
                    "plane {} \u{b7} {}",
                    plane + 1,
                    crate::plane_lens::percent(share)
                ),
                palette.ink2,
                false,
            );
        }

        // Strips: plane by plane at every detail size, built per window key.
        let label = tracked(
            &ctx,
            "KEPT, BY DETAIL SIZE AND PLANE".into(),
            10.0,
            palette.ink3,
            1.0,
        );
        painter.galley(egui::pos2(PAD, strips_top - 18.0), label, palette.ink3);
        let strip_rect = Rect::from_min_max(
            egui::pos2(PAD + LABEL_COLUMN, strips_top),
            egui::pos2(WIDTH - PAD, strips_bottom),
        );
        let key = StripKey {
            window: self.probe.window_revision(),
            level: input.level,
            planes: input.planes,
            leading: [0, 1, 2].map(|index| leading.get(index).copied()),
            palette,
            pixels_per_point: ctx.pixels_per_point(),
        };
        if self.strips.as_ref().is_none_or(|(old, _)| *old != key) {
            #[cfg(test)]
            {
                self.strip_builds += 1;
            }
            let mesh = self.strip_mesh(strip_rect, input.planes, &leading, palette);
            self.strips = Some((key, Arc::new(mesh)));
        }
        if let Some((_, mesh)) = &self.strips {
            painter.add(Shape::mesh(mesh.clone()));
        }
        for level in 0..DETAIL_LEVELS {
            let y = strips_top + level as f32 * (ROW + ROW_GAP) + ROW * 0.5;
            let text = size_label(level, input.geometry);
            painter.text(
                egui::pos2(PAD, y),
                Align2::LEFT_CENTER,
                if level == 0 {
                    text
                } else {
                    text.trim_end_matches(" px").to_owned()
                },
                FontId::proportional(9.5),
                palette.spectrum[level],
            );
        }
        for (x, text, anchor) in [
            (strip_rect.left(), "1".to_owned(), Align2::LEFT_TOP),
            (
                strip_rect.right(),
                input.planes.to_string(),
                Align2::RIGHT_TOP,
            ),
        ] {
            painter.text(
                egui::pos2(x, strips_bottom + 2.0),
                anchor,
                text,
                FontId::proportional(9.5),
                palette.ink3,
            );
        }
        painter.galley(egui::pos2(PAD, words_top), words, palette.ink);
        painter.line_segment(
            [
                egui::pos2(PAD, caution_top - 7.0),
                egui::pos2(WIDTH - PAD, caution_top - 7.0),
            ],
            Stroke::new(1.0_f32, palette.line),
        );
        painter.galley(egui::pos2(PAD, caution_top), caution.clone(), palette.ink3);

        // A hairline leader from the region to the popover.
        let leader_y = outline
            .center()
            .y
            .clamp(placement.top() + 10.0, placement.bottom() - 10.0);
        let (from, to) = if placement.left() >= outline.right() {
            (outline.right(), placement.left())
        } else {
            (outline.left(), placement.right())
        };
        ui.painter().line_segment(
            [egui::pos2(from, leader_y), egui::pos2(to, leader_y)],
            Stroke::new(1.0_f32, palette.ink3),
        );

        // Pinned actions: stationary, so they may be real widgets.
        if pinned {
            let top = caution_top + caution.size().y + 10.0;
            let mut x = PAD;
            for (index, label) in ["Show the plane", "Repair here\u{2026}", "Note"]
                .into_iter()
                .enumerate()
            {
                let galley =
                    painter.layout_no_wrap(label.into(), FontId::proportional(12.0), palette.ink);
                let quiet = index == 2;
                let button = Rect::from_min_size(
                    egui::pos2(x, top),
                    egui::vec2(galley.size().x + 16.0, 22.0),
                );
                x = button.right() + 8.0;
                if !quiet {
                    painter.rect_stroke(
                        button,
                        0.0,
                        Stroke::new(1.0_f32, palette.line2),
                        egui::StrokeKind::Inside,
                    );
                }
                let disabled = index == 0 && leading.is_empty();
                painter.galley(
                    button.center() - galley.size() * 0.5,
                    galley,
                    if disabled { palette.ink3 } else { palette.ink },
                );
                let hit = ui.interact(
                    button.translate(placement.min.to_vec2()),
                    ui.id().with(("core-sample-action", index)),
                    Sense::click(),
                );
                if hit.clicked() && !disabled {
                    response.action = Some(match index {
                        0 => CoreAction::ShowPlane(leading[0]),
                        1 => CoreAction::Repair(region),
                        _ => CoreAction::Note(region),
                    });
                }
            }
        }
        response
    }

    fn update_profile(&mut self, level: usize, planes: usize) {
        let window = self.probe.window_revision();
        if self.profile.window == window
            && self.profile.level == level
            && self.profile.planes == planes
            && !self.profile.values.is_empty()
        {
            return;
        }
        #[cfg(test)]
        {
            self.profile_builds += 1;
        }
        let mut values = vec![0.0; planes];
        let mut observed = false;
        for (plane, count) in self.probe.window_counts(level) {
            if let Some(slot) = values.get_mut(plane) {
                observed |= count.observed > 0;
                *slot = count.fraction().unwrap_or(0.0);
            }
        }
        self.profile = Profile {
            window,
            level,
            planes,
            values,
            observed,
        };
    }

    /// Eight rows, each pooled to at most one column per pixel and scaled by
    /// its own busiest column; the leading planes are marked across them.
    fn strip_mesh(
        &self,
        rect: Rect,
        planes: usize,
        leading: &[usize],
        palette: CorePalette,
    ) -> egui::Mesh {
        let mut mesh = egui::Mesh::default();
        let columns = planes.min(rect.width().floor().max(1.0) as usize);
        let column_of = |plane: usize| plane * columns / planes;
        let x = |column: usize| rect.left() + rect.width() * column as f32 / columns as f32;
        for level in 0..DETAIL_LEVELS {
            let top = rect.top() + level as f32 * (ROW + ROW_GAP);
            let row =
                Rect::from_min_size(egui::pos2(rect.left(), top), egui::vec2(rect.width(), ROW));
            mesh.add_colored_rect(row, palette.line);
            let mut pooled = vec![SampleCount::default(); columns];
            for (plane, count) in self.probe.window_counts(level) {
                if plane < planes {
                    let cell = &mut pooled[column_of(plane)];
                    cell.admitted += count.admitted;
                    cell.observed += count.observed;
                }
            }
            let peak = pooled
                .iter()
                .filter_map(|count| count.fraction())
                .fold(0.0, f32::max);
            if peak <= 0.0 {
                continue;
            }
            for (column, count) in pooled.iter().enumerate() {
                let Some(value) = count.fraction().map(|share| share / peak) else {
                    continue;
                };
                if value > 0.05 {
                    mesh.add_colored_rect(
                        Rect::from_min_max(
                            egui::pos2(x(column), top),
                            egui::pos2(x(column + 1).max(x(column) + 1.0), top + ROW),
                        ),
                        palette.spectrum[level].gamma_multiply((value * 1.05).min(1.0)),
                    );
                }
            }
        }
        for &plane in leading.iter().filter(|&&plane| plane < planes) {
            let at = rect.left() + rect.width() * (plane as f32 + 0.5) / planes as f32;
            mesh.add_colored_rect(
                Rect::from_min_max(
                    egui::pos2(at - 0.5, rect.top() - 1.0),
                    egui::pos2(at + 0.5, rect.bottom() - ROW_GAP + 1.0),
                ),
                palette.ink,
            );
        }
        mesh
    }

    /// The reticle: corner marks and the sites the leading planes kept.
    fn paint_reticle(
        &mut self,
        ui: &Ui,
        input: CoreInput<'_>,
        outline: Rect,
        palette: CorePalette,
    ) {
        let painter = ui
            .painter()
            .with_clip_rect(ui.clip_rect().intersect(input.image));
        for (corner, direction) in [
            (outline.left_top(), Vec2::splat(1.0)),
            (outline.right_top(), egui::vec2(-1.0, 1.0)),
            (outline.right_bottom(), Vec2::splat(-1.0)),
            (outline.left_bottom(), egui::vec2(1.0, -1.0)),
        ] {
            for delta in [
                egui::vec2(direction.x * 8.0, 0.0),
                egui::vec2(0.0, direction.y * 8.0),
            ] {
                painter.line_segment([corner, corner + delta], Stroke::new(1.5_f32, palette.ink));
            }
        }
        let key = SitesKey {
            window: self.probe.window_revision(),
            image: input.image,
            aperture: input.aperture,
            color: palette.ink,
        };
        if self.sites.as_ref().is_none_or(|(old, _)| *old != key) {
            let mut mesh = egui::Mesh::default();
            let sites: Vec<Pos2> = self.probe.leading_sites().map(|(at, _)| at).collect();
            let stride = sites.len().div_ceil(400).max(1);
            let dot = palette.ink.gamma_multiply(0.8);
            for &uv in sites.iter().step_by(stride) {
                let at = input.image.min
                    + (uv - input.aperture.min) / input.aperture.size() * input.image.size();
                mesh.add_colored_rect(Rect::from_center_size(at, Vec2::splat(1.6)), dot);
            }
            self.sites = Some((key, Arc::new(mesh)));
        }
        if let Some((_, mesh)) = &self.sites {
            // Dots stay inside the current region only.
            painter
                .with_clip_rect(painter.clip_rect().intersect(outline))
                .add(Shape::mesh(mesh.clone()));
        }
    }
}

fn caption(painter: &egui::Painter, crop: Rect, text: String, color: Color32, strong: bool) {
    painter.text(
        egui::pos2(crop.left(), crop.bottom() + 3.0),
        Align2::LEFT_TOP,
        text,
        FontId::proportional(if strong { 11.5 } else { 11.0 }),
        color,
    );
}

#[cfg(test)]
#[path = "core-sample-tests.rs"]
mod tests;
