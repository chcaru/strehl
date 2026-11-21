//! The plane lens (Studio 2, spec 7.2): where one plane was kept.
//!
//! Peek: hovering the rail or a filmstrip frame names a plane; the photograph
//! dims and the plane's kept region is painted over it, and a card above the
//! rail shows that plane's camera preview with the same region outlined.
//! Hold: a click keeps the plane; the canvas becomes a two-up (final beside the
//! plane's preview) with one small map per detail size. While holding, the
//! rail still peeks at other planes and leaving it returns to the held one.
//!
//! Honesty: the region on the final photograph is the engine's sampled gate
//! support at that detail size, a display estimate (`DenseRegion`), not a share
//! of the blend. On the camera preview the outline is approximate: the preview
//! is not registered to the final photograph.
//!
//! Performance: regions are extracted on a worker (`DenseRegionWorker`), never
//! during paint; the previous region stays until its replacement is ready.
//! Each painter caches its projected mesh, so pointer motion that does not
//! change the plane rebuilds nothing. Previews come only from textures the
//! caller already holds (`SourceBrowser` tiers); this module never decodes.
// Stage 1 builds the parts; the Stack station composes them in stage 2.
#![allow(dead_code)]

use std::sync::Arc;

use eframe::egui::{self, Align2, Color32, FontId, Pos2, Rect, Sense, Stroke, TextureId, Ui};

use crate::{
    depth_rail::{self, RailGeometry},
    process_admission_regions::{
        DenseRegion, DenseRegionPainter, DenseRegionWorker, KeptStyle, RegionLookup, RegionSettings,
    },
    process_output_space::{OutputGeometry, detail_label},
    process_provenance::AdmissionArchive,
};

/// The detail sizes on the switch: 2 to 256 px at the A7CR output scale.
pub(crate) const DETAIL_LEVELS: usize = 8;
/// The peek card above the rail (appendix B).
pub(crate) const PEEK_SIZE: egui::Vec2 = egui::vec2(372.0, 276.0);
/// A peek dims the photograph to 86 % brightness (spec 7.2). The 75 %
/// saturation needs the photograph presenter's shader; stage 2 wires it.
pub(crate) const PEEK_BRIGHTNESS: f32 = 0.86;
pub(crate) const PEEK_SATURATION: f32 = 0.75;
pub(crate) const SOURCE_CAPTION: &str =
    "camera preview \u{b7} the outline is approximate, not a registration";

/// Keys the lens consumes while it is the Stack station's focus.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(crate) enum LensKey {
    Left,
    Right,
    Escape,
}

/// Peek and hold. Plane arguments are zero-based; captions add one.
#[derive(Clone, Copy, Debug, Default, PartialEq, Eq)]
pub(crate) struct PlaneLens {
    planes: usize,
    held: Option<usize>,
    hover: Option<usize>,
    /// A key step hides a stale hover until the pointer names another plane.
    suppressed: Option<usize>,
    level: usize,
    last: Option<usize>,
}

impl PlaneLens {
    pub(crate) fn set_planes(&mut self, planes: usize) {
        if self.planes == planes {
            return;
        }
        self.planes = planes;
        let valid = |plane: Option<usize>| plane.filter(|&plane| plane < planes);
        self.held = valid(self.held);
        self.hover = valid(self.hover);
        self.last = valid(self.last);
        self.suppressed = None;
    }
    pub(crate) fn planes(&self) -> usize {
        self.planes
    }

    /// The plane under the pointer on the rail or the filmstrip, if any.
    pub(crate) fn hover(&mut self, plane: Option<usize>) {
        let plane = plane.filter(|&plane| plane < self.planes);
        if plane != self.suppressed {
            self.suppressed = None;
        }
        self.hover = plane.filter(|&plane| Some(plane) != self.suppressed);
    }

    /// A click on the rail or a frame: hold it, or release the held plane.
    pub(crate) fn click(&mut self, plane: usize) {
        if plane >= self.planes {
            return;
        }
        if self.held == Some(plane) {
            self.release();
        } else {
            self.hold(plane);
        }
    }

    pub(crate) fn hold(&mut self, plane: usize) {
        if plane < self.planes {
            self.held = Some(plane);
            self.last = Some(plane);
            // The clicked plane is now the held one; the hover is its own.
            self.suppressed = self.hover;
            self.hover = None;
        }
    }

    /// Escape, or a second click on the held plane. Returns whether it held.
    pub(crate) fn release(&mut self) -> bool {
        let held = self.held.take().is_some();
        if held {
            self.suppressed = self.hover;
            self.hover = None;
        }
        held
    }

    /// Step the held plane, clamped to the stack. Does nothing when not held.
    pub(crate) fn step(&mut self, delta: isize) -> bool {
        let Some(held) = self.held else {
            return false;
        };
        let next = held
            .saturating_add_signed(delta)
            .min(self.planes.saturating_sub(1));
        self.held = Some(next);
        self.last = Some(next);
        self.suppressed = self.hover.or(self.suppressed);
        self.hover = None;
        next != held
    }

    pub(crate) fn key(&mut self, key: LensKey, shift: bool) -> bool {
        let stride = if shift { 10 } else { 1 };
        match key {
            LensKey::Left if self.held.is_some() => {
                self.step(-stride);
                true
            }
            LensKey::Right if self.held.is_some() => {
                self.step(stride);
                true
            }
            LensKey::Escape => self.release(),
            _ => false,
        }
    }

    /// Read this frame's Left, Right and Escape presses. Each pressed event
    /// carries its own Shift, so a chord released before the paint still
    /// counts. Returns whether the lens consumed any.
    pub(crate) fn read_keys(&mut self, ui: &Ui) -> bool {
        let keys: Vec<(LensKey, bool)> = ui.input(|state| {
            state
                .events
                .iter()
                .filter_map(|event| match event {
                    egui::Event::Key {
                        key,
                        pressed: true,
                        modifiers,
                        ..
                    } => match key {
                        egui::Key::ArrowLeft => Some((LensKey::Left, modifiers.shift)),
                        egui::Key::ArrowRight => Some((LensKey::Right, modifiers.shift)),
                        egui::Key::Escape => Some((LensKey::Escape, modifiers.shift)),
                        _ => None,
                    },
                    _ => None,
                })
                .collect()
        });
        let mut consumed = false;
        for (key, shift) in keys {
            consumed |= self.key(key, shift);
        }
        consumed
    }

    /// The Plane lens chosen with the switch or key 2: hold the last plane, or
    /// the supplied default (the core sample's leading plane, for example).
    pub(crate) fn choose_plane_lens(&mut self, default: usize) {
        if self.held.is_none() {
            self.hold(
                self.last
                    .unwrap_or(default)
                    .min(self.planes.saturating_sub(1)),
            );
        }
    }

    pub(crate) fn set_level(&mut self, level: usize) {
        self.level = level.min(DETAIL_LEVELS - 1);
    }
    pub(crate) fn level(&self) -> usize {
        self.level
    }
    pub(crate) fn held(&self) -> Option<usize> {
        self.held
    }
    pub(crate) fn hovered(&self) -> Option<usize> {
        self.hover
    }
    /// The plane the canvas shows: while holding, a hover shows another plane
    /// and leaving returns to the held one.
    pub(crate) fn shown(&self) -> Option<usize> {
        if self.held.is_some() {
            self.hover.or(self.held)
        } else {
            self.hover
        }
    }
    pub(crate) fn peeking(&self) -> bool {
        self.held.is_none() && self.hover.is_some()
    }
    pub(crate) fn holding(&self) -> bool {
        self.held.is_some()
    }
    /// `ProcessTheater::set_inspection(hover, held)`: the shared state that
    /// requests previews through `SourceBrowser` for the shown plane.
    pub(crate) fn inspection(&self) -> (Option<usize>, Option<usize>) {
        (
            self.hover.filter(|&plane| Some(plane) != self.held),
            self.held,
        )
    }
}

/// Colours the lens draws with; a one-line constructor from shell tokens.
#[derive(Clone, Copy, Debug, PartialEq)]
pub(crate) struct LensPalette {
    pub plane: Color32,
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
impl LensPalette {
    pub(crate) const GRAPHITE: Self = Self {
        plane: Color32::from_rgb(0x55, 0xd6, 0xc4),
        accent: Color32::from_rgb(0xe6, 0xb4, 0x50),
        ink: Color32::from_rgb(0xe9, 0xe6, 0xde),
        ink2: Color32::from_rgb(0xa1, 0x9f, 0x98),
        ink3: Color32::from_rgb(0x80, 0x7e, 0x77),
        line: Color32::from_rgb(0x23, 0x23, 0x26),
        line2: Color32::from_rgb(0x37, 0x37, 0x3c),
        panel: Color32::from_rgb(0x11, 0x11, 0x12),
        surround: Color32::from_rgb(0x0e, 0x0e, 0x0f),
        spectrum: SPECTRUM_DARK,
    };
}
impl Default for LensPalette {
    fn default() -> Self {
        Self::GRAPHITE
    }
}
impl LensPalette {
    /// Text on the photograph's surround uses the canvas inks (Lightbox keeps
    /// light ink there); the cards and captions use the panel inks.
    pub(crate) fn from_tokens(t: &crate::studio_theme::Tokens) -> Self {
        Self {
            plane: t.plane,
            accent: t.accent,
            ink: t.ink,
            ink2: t.ink2,
            ink3: t.ink3,
            line: t.line,
            line2: t.line2,
            panel: t.panel,
            surround: t.surround,
            spectrum: t.spectrum,
        }
    }
}

/// Appendix A: the detail spectrum on the dark themes (2 to 256 px).
pub(crate) const SPECTRUM_DARK: [Color32; DETAIL_LEVELS] = [
    Color32::from_rgb(0x5f, 0xd9, 0xcf),
    Color32::from_rgb(0x7f, 0xd3, 0xea),
    Color32::from_rgb(0xa7, 0xc9, 0xf2),
    Color32::from_rgb(0xc8, 0xc0, 0xef),
    Color32::from_rgb(0xe2, 0xb9, 0xdc),
    Color32::from_rgb(0xf1, 0xb7, 0xb4),
    Color32::from_rgb(0xf4, 0xc1, 0x8a),
    Color32::from_rgb(0xed, 0xd0, 0x6c),
];

/// "2 px" for a level: the engine's sample spacing in photograph pixels when
/// the output geometry is known, else in analysis-grid pixels.
pub(crate) fn size_label(level: usize, geometry: Option<OutputGeometry>) -> String {
    let label = detail_label(level, geometry);
    let number = label.split("px").next().unwrap_or_default();
    format!("{number} px")
}

/// The evidence the lens reads, with the caller's certificate: `extent` is the
/// analysis domain the final photograph is certified against (OutputSpace).
#[derive(Clone, Copy)]
pub(crate) struct LensEvidence<'a> {
    pub archive: &'a AdmissionArchive,
    pub domain: [u64; 2],
    pub extent: Option<[usize; 2]>,
    pub settings: RegionSettings,
    pub geometry: Option<OutputGeometry>,
}

/// A texture the caller already holds; never a decode request.
#[derive(Clone, Copy, Debug, PartialEq)]
pub(crate) struct LensPhoto {
    pub texture: TextureId,
    /// The UV window to draw (the full frame for camera previews).
    pub uv: Rect,
    /// Width / height of the photograph.
    pub aspect: f32,
}

/// The kept share of sampled sites for a plane at a level.
pub(crate) fn kept_share(archive: &AdmissionArchive, level: usize, plane: usize) -> Option<f32> {
    archive
        .counts(level, plane)
        .filter(|&(_, observed)| observed > 0)
        .map(|(admitted, observed)| admitted as f32 / observed as f32)
}

pub(crate) fn percent(share: Option<f32>) -> String {
    share.map_or_else(
        || "not recorded".into(),
        |share| {
            let value = share * 100.0;
            if value >= 10.0 {
                format!("{value:.0} %")
            } else {
                format!("{value:.1} %")
            }
        },
    )
}

/// The rectangles of the held two-up (appendix B: 16, 162, 1300, 591 at a
/// 1,332 × 756 canvas). Photos keep their aspect; everything scales down
/// together when the canvas is short.
#[derive(Clone, Copy, Debug, PartialEq)]
pub(crate) struct TwoUpLayout {
    pub bounds: Rect,
    pub final_caption: Rect,
    pub final_photo: Rect,
    pub plane_caption: Rect,
    pub plane_photo: Rect,
    pub sizes: [Rect; DETAIL_LEVELS],
    pub size_labels: [Rect; DETAIL_LEVELS],
}

pub(crate) fn two_up_layout(canvas: Rect, aspect: f32) -> TwoUpLayout {
    let aspect = if aspect.is_finite() && aspect > 0.1 {
        aspect
    } else {
        1.5
    };
    const MARGIN: f32 = 16.0;
    const CAPTION: f32 = 24.0;
    const PHOTO_GAP: f32 = 14.0;
    const ROW_GAP: f32 = 16.0;
    const CELL_GAP: f32 = 8.0;
    const LABEL: f32 = 18.0;
    let width = (canvas.width() - 2.0 * MARGIN).max(80.0);
    let cell_w = (width - CELL_GAP * (DETAIL_LEVELS - 1) as f32) / DETAIL_LEVELS as f32;
    let cell_h = cell_w / aspect;
    let fixed = CAPTION + ROW_GAP + cell_h + LABEL;
    let room = (canvas.height() - 2.0 * MARGIN - fixed).max(20.0);
    let photo_w = ((width - PHOTO_GAP) * 0.5).min(room * aspect);
    let photo_h = photo_w / aspect;
    let total = fixed + photo_h;
    let top = canvas.top() + ((canvas.height() - total) * 0.5).max(0.0);
    let left = canvas.left() + MARGIN;
    let pair_left = left + (width - (photo_w * 2.0 + PHOTO_GAP)) * 0.5;
    let final_photo = Rect::from_min_size(
        egui::pos2(pair_left, top + CAPTION),
        egui::vec2(photo_w, photo_h),
    );
    let plane_photo = final_photo.translate(egui::vec2(photo_w + PHOTO_GAP, 0.0));
    let caption = |photo: Rect| {
        Rect::from_min_max(
            egui::pos2(photo.left(), top),
            egui::pos2(photo.right(), photo.top()),
        )
    };
    let row = final_photo.bottom() + ROW_GAP;
    let sizes = std::array::from_fn(|index| {
        Rect::from_min_size(
            egui::pos2(left + index as f32 * (cell_w + CELL_GAP), row),
            egui::vec2(cell_w, cell_h),
        )
    });
    let size_labels = std::array::from_fn(|index: usize| {
        let cell: Rect = sizes[index];
        Rect::from_min_size(cell.left_bottom(), egui::vec2(cell.width(), LABEL))
    });
    TwoUpLayout {
        bounds: Rect::from_min_size(egui::pos2(left, top), egui::vec2(width, total)),
        final_caption: caption(final_photo),
        final_photo,
        plane_caption: caption(plane_photo),
        plane_photo,
        sizes,
        size_labels,
    }
}

/// The peek card: centred on the plane's rail position, 8 px above the rail.
pub(crate) fn peek_rect(canvas: Rect, rail: Rect, planes: usize, plane: usize) -> Option<Rect> {
    let geometry = RailGeometry::new(rail, planes)?;
    let x = geometry.x(plane);
    let left = (x - PEEK_SIZE.x * 0.5).clamp(
        canvas.left() + 10.0,
        (canvas.right() - PEEK_SIZE.x - 10.0).max(canvas.left() + 10.0),
    );
    Some(Rect::from_min_size(
        egui::pos2(left, canvas.bottom() - 8.0 - PEEK_SIZE.y),
        PEEK_SIZE,
    ))
}

/// Region extraction and the per-view painters. Each projection keeps its
/// own small mesh cache so the eight size maps never evict the big views.
pub(crate) struct PlaneLensView {
    worker: DenseRegionWorker,
    final_painter: DenseRegionPainter,
    source_painter: DenseRegionPainter,
    peek_painter: DenseRegionPainter,
    size_painters: [DenseRegionPainter; DETAIL_LEVELS],
    shares: Option<(u64, usize, [Option<f32>; DETAIL_LEVELS])>,
}
impl Default for PlaneLensView {
    fn default() -> Self {
        Self {
            worker: DenseRegionWorker::default(),
            final_painter: DenseRegionPainter::default(),
            source_painter: DenseRegionPainter::default(),
            peek_painter: DenseRegionPainter::default(),
            size_painters: std::array::from_fn(|_| DenseRegionPainter::default()),
            shares: None,
        }
    }
}

/// What a two-up paint asks of the station.
#[derive(Clone, Copy, Debug, Default, PartialEq, Eq)]
pub(crate) struct TwoUpResponse {
    /// A size map was clicked: set the detail-size switch.
    pub level: Option<usize>,
}

impl PlaneLensView {
    /// The region for the shown plane at the lens level (keeps the previous
    /// region while the worker extracts the new one).
    pub(crate) fn region(
        &mut self,
        ctx: &egui::Context,
        evidence: LensEvidence<'_>,
        plane: usize,
        level: usize,
    ) -> RegionLookup {
        let Some(extent) = evidence.extent else {
            return RegionLookup {
                current: true,
                ..Default::default()
            };
        };
        self.worker.region(
            ctx,
            evidence.archive,
            evidence.domain,
            plane,
            level,
            extent,
            evidence.settings,
        )
    }

    pub(crate) fn pending(&self) -> bool {
        self.worker.pending()
    }

    /// Kept shares at every level for one plane, cached by archive revision.
    pub(crate) fn shares(
        &mut self,
        archive: &AdmissionArchive,
        plane: usize,
    ) -> [Option<f32>; DETAIL_LEVELS] {
        let revision = archive.revision();
        if let Some((cached_revision, cached_plane, shares)) = self.shares
            && cached_revision == revision
            && cached_plane == plane
        {
            return shares;
        }
        let shares = std::array::from_fn(|level| kept_share(archive, level, plane));
        self.shares = Some((revision, plane, shares));
        shares
    }

    /// Dim the photograph for a peek (brightness; see `PEEK_SATURATION`).
    pub(crate) fn dim(painter: &egui::Painter, image: Rect) {
        painter.rect_filled(
            image,
            0.0,
            Color32::from_black_alpha(((1.0 - PEEK_BRIGHTNESS) * 255.0).round() as u8),
        );
    }

    /// The kept region over the certified final photograph.
    pub(crate) fn paint_final_region(
        &mut self,
        painter: &egui::Painter,
        region: &Arc<DenseRegion>,
        image: Rect,
        aperture: Rect,
        palette: LensPalette,
    ) {
        self.final_painter.paint_kept(
            painter,
            region,
            image,
            aperture,
            palette.plane,
            KeptStyle::LENS,
        );
    }

    /// The peek card above the rail: the plane's camera preview, the same
    /// region outlined (approximate), its number, kept share and the hint.
    #[allow(clippy::too_many_arguments)]
    pub(crate) fn paint_peek(
        &mut self,
        painter: &egui::Painter,
        card: Rect,
        anchor_x: f32,
        plane: usize,
        share: Option<f32>,
        preview: Option<LensPhoto>,
        region: Option<&Arc<DenseRegion>>,
        palette: LensPalette,
    ) {
        let floating = painter.with_clip_rect(painter.clip_rect().union(card.expand(8.0)));
        // A square, ruled card with the one permitted shadow (popovers).
        floating.rect_filled(
            card.translate(egui::vec2(0.0, 3.0)),
            0.0,
            Color32::from_black_alpha(90),
        );
        floating.rect_filled(card, 0.0, palette.panel);
        floating.rect_stroke(
            card,
            0.0,
            Stroke::new(1.0_f32, palette.line2),
            egui::StrokeKind::Inside,
        );
        let image = Rect::from_min_size(
            card.min + egui::vec2(6.0, 6.0),
            egui::vec2(card.width() - 12.0, card.height() - 36.0),
        );
        floating.rect_filled(image, 0.0, palette.surround);
        if let Some(preview) = preview {
            let photo = fit(preview.aspect, image);
            floating.image(preview.texture, photo, preview.uv, Color32::WHITE);
            if let Some(region) = region {
                self.peek_painter.paint_approximate(
                    &floating,
                    region,
                    photo,
                    preview.uv,
                    palette.plane,
                );
            }
        } else {
            floating.text(
                image.center(),
                Align2::CENTER_CENTER,
                "preview not resident yet",
                FontId::proportional(12.0),
                palette.ink3,
            );
        }
        let y = (image.bottom() + card.bottom()) * 0.5;
        let name = floating.text(
            egui::pos2(card.left() + 6.0, y),
            Align2::LEFT_CENTER,
            format!("Plane {}", plane + 1),
            FontId::proportional(12.5),
            palette.plane,
        );
        floating.text(
            egui::pos2(name.right() + 10.0, y),
            Align2::LEFT_CENTER,
            format!("{} of the frame kept from here", percent(share)),
            FontId::proportional(12.0),
            palette.ink2,
        );
        floating.text(
            egui::pos2(card.right() - 6.0, y),
            Align2::RIGHT_CENTER,
            "click to hold",
            FontId::proportional(12.0),
            palette.ink3,
        );
        // The pointer: a small notch on the card's lower edge over the plane.
        let x = anchor_x.clamp(card.left() + 12.0, card.right() - 12.0);
        floating.add(egui::Shape::convex_polygon(
            vec![
                egui::pos2(x - 6.0, card.bottom() - 0.5),
                egui::pos2(x + 6.0, card.bottom() - 0.5),
                egui::pos2(x, card.bottom() + 6.0),
            ],
            palette.panel,
            Stroke::NONE,
        ));
        floating.line_segment(
            [
                egui::pos2(x - 6.0, card.bottom()),
                egui::pos2(x, card.bottom() + 6.0),
            ],
            Stroke::new(1.0_f32, palette.line2),
        );
        floating.line_segment(
            [
                egui::pos2(x + 6.0, card.bottom()),
                egui::pos2(x, card.bottom() + 6.0),
            ],
            Stroke::new(1.0_f32, palette.line2),
        );
    }

    /// The held two-up: final with the region beside the plane's preview with
    /// the same outline, then one small map per detail size. Size maps warm on
    /// the worker only when it is idle; a missing map is drawn empty, never a
    /// neighbour's region.
    #[allow(clippy::too_many_arguments)]
    pub(crate) fn paint_two_up(
        &mut self,
        ui: &mut Ui,
        layout: &TwoUpLayout,
        evidence: LensEvidence<'_>,
        plane: usize,
        level: usize,
        final_photo: LensPhoto,
        preview: Option<LensPhoto>,
        palette: LensPalette,
    ) -> TwoUpResponse {
        let ctx = ui.ctx().clone();
        let painter = ui.painter().clone();
        let lookup = self.region(&ctx, evidence, plane, level);
        let shares = self.shares(evidence.archive, plane);
        let size = size_label(level, evidence.geometry);
        // Captions name the region actually drawn while a new one is pending.
        let drawn = lookup.frame.unwrap_or(plane);
        let final_text = format!(
            "where plane {} was kept, at {size} \u{b7} {} of the frame",
            drawn + 1,
            percent(shares[level]),
        );
        caption(
            &painter,
            layout.final_caption,
            "FINAL",
            &final_text,
            palette,
        );
        caption(
            &painter,
            layout.plane_caption,
            &format!("PLANE {}", plane + 1),
            SOURCE_CAPTION,
            palette,
        );
        let final_image = fit(final_photo.aspect, layout.final_photo);
        painter.rect_filled(layout.final_photo, 0.0, palette.surround);
        painter.image(
            final_photo.texture,
            final_image,
            final_photo.uv,
            Color32::WHITE,
        );
        if let Some(region) = &lookup.region {
            self.final_painter.paint_kept(
                &painter.with_clip_rect(painter.clip_rect().intersect(final_image)),
                region,
                final_image,
                final_photo.uv,
                palette.plane,
                KeptStyle::LENS,
            );
        }
        painter.rect_filled(layout.plane_photo, 0.0, palette.surround);
        if let Some(preview) = preview {
            let image = fit(preview.aspect, layout.plane_photo);
            painter.image(preview.texture, image, preview.uv, Color32::WHITE);
            if let Some(region) = &lookup.region {
                self.source_painter.paint_approximate(
                    &painter.with_clip_rect(painter.clip_rect().intersect(image)),
                    region,
                    image,
                    preview.uv,
                    palette.plane,
                );
            }
        } else {
            painter.text(
                layout.plane_photo.center(),
                Align2::CENTER_CENTER,
                format!("Plane {} \u{b7} preview not resident yet", plane + 1),
                FontId::proportional(12.0),
                palette.ink3,
            );
        }
        let mut response = TwoUpResponse::default();
        // The selected size is the main request; the others warm after it.
        let mut order: Vec<usize> = (0..DETAIL_LEVELS).collect();
        order.sort_by_key(|&index| index != level);
        let mut regions: [Option<Arc<DenseRegion>>; DETAIL_LEVELS] = Default::default();
        if let Some(extent) = evidence.extent {
            for &index in &order {
                regions[index] =
                    if index == level && lookup.level == Some(level) && lookup.frame == Some(plane)
                    {
                        lookup.region.clone()
                    } else {
                        self.worker
                            .prefetch(
                                &ctx,
                                evidence.archive,
                                evidence.domain,
                                plane,
                                index,
                                extent,
                                evidence.settings,
                            )
                            .flatten()
                    };
            }
        }
        for index in 0..DETAIL_LEVELS {
            let cell = layout.sizes[index];
            painter.rect_filled(cell, 0.0, palette.surround);
            let image = fit(final_photo.aspect, cell);
            painter.image(
                final_photo.texture,
                image,
                Rect::from_min_max(Pos2::ZERO, egui::pos2(1.0, 1.0)),
                Color32::from_gray(150),
            );
            if let Some(region) = &regions[index] {
                self.size_painters[index].paint_kept(
                    &painter.with_clip_rect(painter.clip_rect().intersect(image)),
                    region,
                    image,
                    Rect::from_min_max(Pos2::ZERO, egui::pos2(1.0, 1.0)),
                    palette.plane,
                    KeptStyle::SMALL,
                );
            }
            if index == level {
                painter.rect_stroke(
                    cell,
                    0.0,
                    Stroke::new(1.5_f32, palette.ink),
                    egui::StrokeKind::Outside,
                );
            }
            let label = layout.size_labels[index];
            let size = size_label(index, evidence.geometry);
            let named = painter.text(
                egui::pos2(label.left(), label.center().y),
                Align2::LEFT_CENTER,
                size.trim_end_matches(" px").to_owned() + if index == 0 { " px" } else { "" },
                FontId::proportional(11.5),
                palette.spectrum[index],
            );
            painter.text(
                egui::pos2(named.right() + 6.0, label.center().y),
                Align2::LEFT_CENTER,
                format!("{} kept", percent(shares[index])),
                FontId::proportional(11.5),
                palette.ink2,
            );
            let hit = ui.interact(
                cell.union(label),
                ui.id().with(("plane-lens-size", index)),
                Sense::click(),
            );
            if hit.clicked() {
                response.level = Some(index);
            }
        }
        response
    }
}

fn caption(painter: &egui::Painter, rect: Rect, title: &str, text: &str, palette: LensPalette) {
    let ctx = painter.ctx();
    let title = depth_rail::tracked(ctx, title.to_owned(), 10.5, palette.ink, 1.3);
    let y = rect.center().y;
    painter.galley(
        egui::pos2(rect.left(), y - title.size().y * 0.5),
        title.clone(),
        palette.ink,
    );
    painter.with_clip_rect(rect).text(
        egui::pos2(rect.left() + title.size().x + 12.0, y),
        Align2::LEFT_CENTER,
        text,
        FontId::proportional(12.0),
        palette.ink2,
    );
}

/// The largest rect of `aspect` centred in `bounds`.
pub(crate) fn fit(aspect: f32, bounds: Rect) -> Rect {
    let aspect = if aspect.is_finite() && aspect > 0.0 {
        aspect
    } else {
        1.5
    };
    let size = if bounds.width() / bounds.height().max(1e-3) > aspect {
        egui::vec2(bounds.height() * aspect, bounds.height())
    } else {
        egui::vec2(bounds.width(), bounds.width() / aspect)
    };
    Rect::from_center_size(bounds.center(), size)
}

#[cfg(test)]
#[path = "plane-lens-tests.rs"]
mod tests;
