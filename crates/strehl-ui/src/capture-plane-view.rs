//! The plane view of a capture in flight (h-proof): the newest plane at
//! full resolution, or any earlier one, with what is known of it.
//!
//! - **The picture.** The try's RAWs as the stack will use them (four shots
//!   combined, or the first demosaiced), tiled from the full-resolution
//!   pyramid: the wheel zooms about the pointer, a drag pans, a double click
//!   goes between fit and 100 % (one photosite a screen pixel, square
//!   texels above it). It follows the newest try unless the user picked
//!   another, or holds the one shown while the user is zooming or panning.
//! - **On the picture.** *Sharp*: the cells where this plane is within 70 %
//!   of the sharpest any plane has been (the band of the subject in focus
//!   now). *Checks*: the checker's witness tiles over its limit and the
//!   witness pairs' shift in each quadrant.
//! - **About it.** Plane, try and verdict; focus and how far from the
//!   plane before; when; exposure; what the picture is; how much is sharp and
//!   how much of that the neighbouring planes share (no overlap with both
//!   neighbours is a gap in depth).
//! - **History.** One bar a plane, its height the share of the frame sharp
//!   there, marked by its verdict: the stack moving through the subject.
//!   Click or drag to pick a plane; ← → step; End returns to the newest.
//!
//! Nothing here decodes or moves pixels: [`super::planes`] does, off the
//! UI thread.
use std::{sync::Arc, time::Instant};

use eframe::egui::{self, Align2, Color32, Rect, Sense, TextureOptions, Ui};

use super::flight::Failure;
use super::follow::{FeedItem, Progress, Verdict};
use super::planes::{
    DeckSnapshot, ImageKind, PAIR_SHIFT, PlaneDeck, PlaneImage, TILE, TILE_RATIO, TileKey, TryKey,
};
use super::style::{self, ButtonKind, CapturePalette, Mark};

/// How long zooming or panning holds the shown plane while following.
const HOLD_SECONDS: f32 = 2.5;
/// Zoom limit: screen pixels a photosite.
const MAX_ZOOM: f32 = 16.0;

/// The Sharp overlay as built: for which revision and try, its texture
/// and the band's outline (UV segments).
type SharpOverlay = ((u64, TryKey), egui::TextureHandle, Vec<[egui::Pos2; 2]>);

/// The view's state across frames.
pub(crate) struct PlaneView {
    /// The newest try is shown as it arrives.
    pub following: bool,
    /// The try picked (not following).
    pub selected: Option<TryKey>,
    /// "Show" for a try not arrived yet: its plane and first RAW.
    pending: Option<(u64, Option<Arc<str>>)>,
    /// Points a source pixel; `None` fits the picture.
    zoom: Option<f32>,
    /// The source UV at the view's centre.
    center: egui::Pos2,
    /// The width of the picture `zoom` was set for.
    basis: u32,
    pub sharp: bool,
    pub checks: bool,
    /// The last zoom or pan, and the try shown then (held while following).
    inspected: Option<(Instant, TryKey)>,
    sharp_tex: Option<SharpOverlay>,
    checks_tex: Option<(u64, egui::TextureHandle)>,
    strip: Option<((u64, usize, u64), Vec<Bar>)>,
    verdicts: Option<((usize, TryKey), Option<usize>)>,
    /// Tiles painted last frame, and the panel's milliseconds
    /// (performance checks).
    pub tiles_drawn: usize,
    pub paint_ms: f64,
}

impl Default for PlaneView {
    fn default() -> Self {
        Self {
            following: true,
            selected: None,
            pending: None,
            zoom: None,
            center: egui::pos2(0.5, 0.5),
            basis: 0,
            sharp: true,
            checks: true,
            inspected: None,
            sharp_tex: None,
            checks_tex: None,
            strip: None,
            verdicts: None,
            tiles_drawn: 0,
            paint_ms: 0.0,
        }
    }
}

impl PlaneView {
    /// "Show" from the feed: the try whose first RAW is `first` (else the
    /// plane's last), held until the user returns to the newest.
    pub fn show(&mut self, plane: u64, first: Option<Arc<str>>) {
        self.following = false;
        self.pending = Some((plane, first));
    }
    /// Back to following the newest try.
    pub fn follow(&mut self) {
        self.following = true;
        self.selected = None;
        self.pending = None;
    }
    /// 100 % about the centre (tests and `--capture-plane-zoom`).
    #[allow(dead_code)]
    pub fn set_zoom(&mut self, points_per_pixel: Option<f32>, center: egui::Pos2) {
        self.zoom = points_per_pixel;
        self.center = center;
    }
}

/// What the panel needs besides the deck.
pub(crate) struct PlaneInputs<'a> {
    pub progress: Option<&'a Progress>,
    /// Planes planned.
    pub total: u64,
    /// The checker is on.
    pub checking: bool,
    /// The run's exposure ("ISO 100 · 1/8 s").
    pub exposure: Option<String>,
}

/// One plane's bar in the history strip.
#[derive(Clone, Copy, Debug, Default, PartialEq)]
pub(crate) struct Bar {
    /// Share of the frame sharp in the plane's last try, if measured.
    pub share: Option<f32>,
    pub mark: Option<Mark>,
    pub retaken: bool,
}

/// The strip's bars, one a plane up to `planes`: shares from `snap`, marks
/// from the checker's last line of each plane.
pub(crate) fn bars(snap: &DeckSnapshot, progress: Option<&Progress>, planes: u64) -> Vec<Bar> {
    let mut out = vec![Bar::default(); planes as usize];
    for t in &snap.tries {
        let i = t.t.plane.saturating_sub(1) as usize;
        if let Some(b) = out.get_mut(i)
            && t.share.is_some()
        {
            // The plane's last try is the stack's.
            b.share = t.share;
        }
    }
    if let Some(p) = progress {
        // Each plane's tries checked, from the feed.
        let mut tries = vec![0u32; planes as usize];
        for item in &p.feed {
            if let Some(n) = tries.get_mut(item.plane.saturating_sub(1) as usize) {
                *n = (*n).max(item.attempt);
            }
        }
        for (plane, line) in &p.planes {
            let i = plane.saturating_sub(1) as usize;
            let retaking = line["retake"] == true
                && tries
                    .get(i)
                    .is_some_and(|n| *n as usize <= strehl_capture::worker::MAX_RETAKES);
            if let Some(b) = out.get_mut(i) {
                b.mark = Some(match line["verdict"].as_str() {
                    Some("pass" | "decoded") => Mark::Ok,
                    Some("incomplete") => Mark::Idle,
                    // A retake to come, or the stack folds it to one shot.
                    _ if retaking => Mark::Warn,
                    _ => Mark::Bad,
                });
            }
        }
        for plane in &p.retaken_planes {
            if let Some(b) = out.get_mut(plane.saturating_sub(1) as usize) {
                b.retaken = true;
            }
        }
    }
    out
}

/// The share of `a`'s sharp cells also sharp in `b`.
pub(crate) fn overlap(snap: &DeckSnapshot, a: &[u16], b: &[u16]) -> Option<f32> {
    if a.len() != snap.max.len() || b.len() != a.len() {
        return None;
    }
    let mut both = 0usize;
    let mut mine = 0usize;
    for i in 0..a.len() {
        if snap.sharp(a, i) {
            mine += 1;
            both += usize::from(snap.sharp(b, i));
        }
    }
    (mine > 0).then(|| both as f32 / mine as f32)
}

/// Where the picture goes in `area` at the view's zoom and centre; the
/// centre is clamped so the picture covers what it can. Returns the
/// picture's rectangle and its points a source pixel.
pub(crate) fn place(area: Rect, size: [u32; 2], view: &mut PlaneView) -> (Rect, f32) {
    let (w, h) = (size[0].max(1) as f32, size[1].max(1) as f32);
    let fit = (area.width() / w).min(area.height() / h);
    let Some(zoom) = view.zoom.filter(|z| *z > fit) else {
        view.zoom = None;
        view.center = egui::pos2(0.5, 0.5);
        return (
            Rect::from_center_size(area.center(), egui::vec2(w * fit, h * fit)),
            fit,
        );
    };
    let img = egui::vec2(w * zoom, h * zoom);
    let mut c = view.center;
    for (i, (extent, span)) in [(img.x, area.width()), (img.y, area.height())]
        .into_iter()
        .enumerate()
    {
        let half = span / extent / 2.0;
        let v = if half >= 0.5 {
            0.5
        } else {
            c[i].clamp(half, 1.0 - half)
        };
        if i == 0 {
            c.x = v;
        } else {
            c.y = v;
        }
    }
    view.center = c;
    let min = area.center() - egui::vec2(c.x * img.x, c.y * img.y);
    (Rect::from_min_size(min, img), zoom)
}

/// Tiles of `stride` covering the UV rectangle `aperture`, centre first.
pub(crate) fn tiles_in(image: &PlaneImage, stride: u32, aperture: Rect) -> Vec<TileKey> {
    let Some(level) = image.level(stride) else {
        return Vec::new();
    };
    let [lw, lh] = level.size;
    let (nx, ny) = (lw.div_ceil(TILE), lh.div_ceil(TILE));
    let [w, h] = image.size.map(|v| v as f32);
    let span = (TILE * stride) as f32;
    let range = |a: f32, b: f32, extent: f32, n: u32| {
        let lo = ((a * extent / span).floor().max(0.0) as u32).min(n - 1);
        let hi = ((b * extent / span).ceil().max(0.0) as u32).clamp(lo + 1, n);
        (lo, hi)
    };
    let (x0, x1) = range(aperture.min.x, aperture.max.x, w, nx);
    let (y0, y1) = range(aperture.min.y, aperture.max.y, h, ny);
    let mut keys: Vec<TileKey> = (y0..y1)
        .flat_map(|y| (x0..x1).map(move |x| TileKey { stride, x, y }))
        .collect();
    let mid = aperture.center();
    keys.sort_by(|a, b| {
        let d = |k: &TileKey| {
            let cx = ((k.x as f32 + 0.5) * span / w - mid.x).abs();
            let cy = ((k.y as f32 + 0.5) * span / h - mid.y).abs();
            cx + cy
        };
        d(a).total_cmp(&d(b))
    });
    keys
}

/// The texel stride the view needs (a level of `image`), or `None` when the
/// overview is enough.
pub(crate) fn stride_for(image: &PlaneImage, aperture: Rect, physical: [u32; 2]) -> Option<u32> {
    let stride = crate::photo_viewport::target_stride(image.size, aperture, physical)?;
    (stride < image.overview().stride && image.level(stride).is_some()).then_some(stride)
}

/// The checker's item for the try `key` (whose first RAW is `first`).
fn item_of<'a>(
    view: &mut PlaneView,
    progress: Option<&'a Progress>,
    key: TryKey,
    first: Option<&str>,
) -> Option<&'a FeedItem> {
    let p = progress?;
    let stamp = (p.feed.len(), key);
    let index = match view.verdicts {
        Some((s, i)) if s == stamp => i,
        _ => {
            let i = p
                .feed
                .iter()
                .rposition(|i| first.is_some_and(|f| i.first.as_deref() == Some(f)))
                .or_else(|| {
                    p.feed
                        .iter()
                        .rposition(|i| i.plane == key.plane && i.attempt == key.attempt)
                });
            view.verdicts = Some((stamp, i));
            i
        }
    };
    index.and_then(|i| p.feed.get(i))
}

/// The verdict in words: its mark, a title and what the stack does.
pub(crate) fn verdict_text(
    item: Option<&FeedItem>,
    last: bool,
    later: Option<u32>,
    checking: bool,
) -> (Mark, String, String) {
    let Some(item) = item else {
        return if checking {
            (Mark::Run, "Not checked yet".into(), String::new())
        } else {
            (Mark::Idle, "Checking is off".into(), String::new())
        };
    };
    let what = if item.verdict == Verdict::Decoded || item.members == 1 {
        "Decoded and aligned"
    } else {
        "Four shots agree"
    };
    let then = match (later, last) {
        (Some(n), _) => format!("Retaken: try {n} follows."),
        (None, true) if item.verdict.passed() => "The stack uses this try.".to_owned(),
        (None, true) if item.retake => "A retake was asked for.".to_owned(),
        (None, true) => "The stack uses its first shot here.".to_owned(),
        (None, false) => String::new(),
    };
    match Failure::of(item) {
        None => (Mark::Ok, what.into(), then),
        Some(f) => (
            if item.retake { Mark::Warn } else { Mark::Bad },
            f.title().to_owned(),
            format!("{} {then}", f.cause()).trim().to_owned(),
        ),
    }
}

/// Local clock time of a Unix millisecond.
fn clock(ms: u64) -> String {
    chrono::DateTime::from_timestamp_millis(ms as i64)
        .map(|t| {
            t.with_timezone(&chrono::Local)
                .format("%H:%M:%S")
                .to_string()
        })
        .unwrap_or_default()
}

/// The panel in `rect`. Returns nothing: picking and following are the
/// view's own state.
pub(crate) fn panel(
    ui: &mut Ui,
    rect: Rect,
    deck: Option<&mut PlaneDeck>,
    view: &mut PlaneView,
    inputs: &PlaneInputs<'_>,
    palette: &CapturePalette,
) {
    let started = Instant::now();
    let p = ui.painter_at(rect);
    p.rect_filled(rect, 0.0, palette.bg);
    let Some(deck) = deck else {
        style::paint_job(
            &p,
            rect.center(),
            Align2::CENTER_CENTER,
            style::job(
                "Each plane appears here, at full resolution, as its RAWs reach this PC",
                12.5,
                palette.ink3,
                0.0,
            ),
        );
        return;
    };
    let snap = deck.snapshot().clone();
    // Which try: the picked one, a pending Show once it arrives, or the
    // newest (held while the user zooms or pans).
    if let Some((plane, first)) = view.pending.clone()
        && let Some(i) = snap.find(plane, first.as_deref())
    {
        view.selected = Some(snap.tries[i].t.key());
        view.pending = None;
    }
    let newest = snap.newest().map(|i| snap.tries[i].t.key());
    let held = view
        .inspected
        .filter(|(at, _)| at.elapsed().as_secs_f32() < HOLD_SECONDS)
        .map(|(_, k)| k);
    let key = if view.following {
        held.or(newest)
    } else {
        view.selected.or(newest)
    };
    // Rows: head, picture, facts, strip.
    let head = Rect::from_min_size(rect.min, egui::vec2(rect.width(), 30.0));
    let strip_h = 46.0;
    let strip = Rect::from_min_max(egui::pos2(rect.left(), rect.bottom() - strip_h), rect.max);
    let facts_h = if rect.width() < 640.0 { 62.0 } else { 44.0 };
    let facts = Rect::from_min_max(
        egui::pos2(rect.left() + 10.0, strip.top() - facts_h - 4.0),
        egui::pos2(rect.right() - 10.0, strip.top() - 4.0),
    );
    let area = Rect::from_min_max(
        egui::pos2(rect.left(), head.bottom()),
        egui::pos2(rect.right(), facts.top() - 4.0),
    );

    // The RAWs are read at full resolution when their detail can be seen:
    // zoomed in, a plane picked, or a fitted view wider than the camera's
    // preview. Following at fit, the preview is the picture (no RAW is
    // decoded; a 61 MP build stalls other threads, see `planes`).
    let ppp = ui.ctx().pixels_per_point();
    let preview_px = deck
        .image()
        .filter(|i| i.kind == ImageKind::Preview)
        .map_or(1616.0, |i| i.size[0] as f32);
    let fit_px = deck.image().map_or(0.0, |i| {
        let (w, h) = (i.size[0] as f32, i.size[1] as f32);
        (area.width() / w).min(area.height() / h) * w * ppp
    });
    let full = !view.following || view.zoom.is_some() || fit_px > preview_px * 1.05;
    deck.want(key, full, !view.following || deck.image().is_none());
    // The facts and the title are the picture's (the last plane stays on
    // screen while the next is read); without a picture, the wanted try's.
    let shown_key = deck.image().map(|i| i.key).or(key);
    let shown_index = shown_key.and_then(|k| snap.index(k));

    // The picture. A zoom is kept in screen points a pixel of the picture
    // shown: when a preview gives way to the RAWs (or back), it is
    // rescaled so the view does not jump.
    let image = deck.image().cloned();
    if let Some(i) = &image {
        if view.basis != 0 && view.basis != i.frame[0] && view.zoom.is_some() {
            view.zoom = view.zoom.map(|z| z * view.basis as f32 / i.frame[0] as f32);
        }
        view.basis = i.frame[0];
    }
    let response = ui.interact(
        area,
        ui.id().with("capture-plane-image"),
        Sense::click_and_drag(),
    );
    p.rect_filled(area, 0.0, palette.bg);
    let mut drawn = 0;
    if let Some(image) = &image {
        let (img, scale) = place(area, image.frame, view);
        let clip = p.with_clip_rect(area);
        // Interaction: zoom about the pointer, pan, double click.
        let mut touched = false;
        if response.hovered() {
            let wheel = ui.input(|i| i.smooth_scroll_delta.y + i.zoom_delta().ln() * 400.0);
            if wheel.abs() > 0.1
                && let Some(at) = response.hover_pos()
            {
                let fit = (area.width() / image.frame[0] as f32)
                    .min(area.height() / image.frame[1] as f32);
                let next = (scale * (wheel * 0.0025).exp()).clamp(fit, MAX_ZOOM / ppp);
                let uv = (at - img.min) / img.size();
                let size = egui::vec2(image.frame[0] as f32, image.frame[1] as f32) * next;
                let min = at - egui::vec2(uv.x * size.x, uv.y * size.y);
                view.center = egui::pos2(
                    (area.center().x - min.x) / size.x,
                    (area.center().y - min.y) / size.y,
                );
                view.zoom = (next > fit * 1.0001).then_some(next);
                touched = true;
            }
        }
        if response.dragged() && view.zoom.is_some() {
            let d = response.drag_delta();
            view.center -= egui::vec2(d.x / img.width(), d.y / img.height());
            touched = true;
        }
        if response.double_clicked() {
            if view.zoom.is_some() {
                view.zoom = None;
            } else if let Some(at) = response.interact_pointer_pos() {
                view.zoom = Some(1.0 / ppp);
                let uv = (at - img.min) / img.size();
                view.center = egui::pos2(uv.x, uv.y);
            }
            touched = true;
        }
        if touched && let Some(k) = key {
            view.inspected = Some((Instant::now(), k));
        }
        let (img, scale) = place(area, image.frame, view);
        let full = Rect::from_min_max(egui::Pos2::ZERO, egui::pos2(1.0, 1.0));
        if let Some(o) = deck.overview().and_then(|o| o.tex.id()) {
            clip.image(o, img, full, Color32::WHITE);
        }
        let visible = img.intersect(area);
        let aperture = Rect::from_min_max(
            ((visible.min - img.min) / img.size()).to_pos2(),
            ((visible.max - img.min) / img.size()).to_pos2(),
        );
        let physical = [
            (visible.width() * ppp).round().max(1.0) as u32,
            (visible.height() * ppp).round().max(1.0) as u32,
        ];
        let keys = stride_for(image, aperture, physical)
            .map(|s| tiles_in(image, s, aperture))
            .unwrap_or_default();
        deck.demand(&keys);
        let to_screen = |uv: Rect| {
            Rect::from_min_max(
                img.min + uv.min.to_vec2() * img.size(),
                img.min + uv.max.to_vec2() * img.size(),
            )
        };
        for k in &keys {
            if let Some(t) = deck.tile(k)
                && let Some(id) = t.tex.id()
            {
                clip.image(id, to_screen(t.core), t.uv, Color32::WHITE);
                drawn += 1;
            }
        }
        // Overlays.
        if view.sharp
            && let Some(i) = shown_index
            && let Some(map) = snap.tries[i].map.clone()
        {
            let stamp = (snap.revision, snap.tries[i].t.key());
            let [pw, ph] = snap.preview;
            let cell = pw.max(ph).div_ceil(super::planes::MAP_CELLS).max(1);
            // A cell's size in the picture's UV.
            let step = egui::vec2(cell as f32 / pw as f32, cell as f32 / ph as f32);
            if view.sharp_tex.as_ref().is_none_or(|(s, _, _)| *s != stamp) {
                let [gw, gh] = snap.grid;
                let on = |x: usize, y: usize| x < gw && y < gh && snap.sharp(&map, y * gw + x);
                let mut pixels = vec![Color32::TRANSPARENT; gw * gh];
                let fill = palette.plane.gamma_multiply(0.16);
                // The band's outline: the edges between sharp and other cells.
                let mut edges = Vec::new();
                for y in 0..gh {
                    for x in 0..gw {
                        if !on(x, y) {
                            continue;
                        }
                        pixels[y * gw + x] = fill;
                        let p = |i: usize, j: usize| {
                            egui::pos2((i as f32 * step.x).min(1.0), (j as f32 * step.y).min(1.0))
                        };
                        if x == 0 || !on(x - 1, y) {
                            edges.push([p(x, y), p(x, y + 1)]);
                        }
                        if !on(x + 1, y) {
                            edges.push([p(x + 1, y), p(x + 1, y + 1)]);
                        }
                        if y == 0 || !on(x, y - 1) {
                            edges.push([p(x, y), p(x + 1, y)]);
                        }
                        if !on(x, y + 1) {
                            edges.push([p(x, y + 1), p(x + 1, y + 1)]);
                        }
                    }
                }
                let image = egui::ColorImage::new([gw, gh], pixels);
                view.sharp_tex = Some((
                    stamp,
                    ui.ctx()
                        .load_texture("capture-plane-sharp", image, TextureOptions::NEAREST),
                    edges,
                ));
            }
            if let Some((_, t, edges)) = &view.sharp_tex {
                let uv = Rect::from_min_max(
                    egui::Pos2::ZERO,
                    egui::pos2(
                        pw as f32 / (snap.grid[0] * cell) as f32,
                        ph as f32 / (snap.grid[1] * cell) as f32,
                    ),
                );
                clip.image(t.id(), img, uv, Color32::WHITE);
                let stroke = egui::Stroke::new(1.25_f32, palette.plane.gamma_multiply(0.9));
                let at = |p: egui::Pos2| img.min + p.to_vec2() * img.size();
                for [a, b] in edges {
                    clip.line_segment([at(*a), at(*b)], stroke);
                }
            }
        }
        if view.checks
            && let Some(f) = image.findings.as_ref().filter(|f| !f.z2.is_empty())
        {
            if view
                .checks_tex
                .as_ref()
                .is_none_or(|(id, _)| *id != image.id)
            {
                let [gw, gh] = f.grid;
                let limit = f.median * TILE_RATIO as f32;
                // Warning colour where the tiles failed the group; in a group
                // that passed, its highest tiles in a quiet ink.
                let failed = f
                    .reason
                    .as_deref()
                    .is_some_and(|r| r.contains("tiles disagree"));
                let color = if failed {
                    palette.warn
                } else {
                    palette.canvas_ink[1]
                };
                let pixels: Vec<Color32> = f
                    .z2
                    .iter()
                    .map(|z| {
                        if z.is_finite() && *z >= limit && limit > 0.0 {
                            let strength = ((z / limit).log2() / 2.0).clamp(0.0, 1.0);
                            color.gamma_multiply(if failed { 0.35 + 0.4 * strength } else { 0.25 })
                        } else {
                            Color32::TRANSPARENT
                        }
                    })
                    .collect();
                let tex = egui::ColorImage::new([gw, gh], pixels);
                view.checks_tex = Some((
                    image.id,
                    ui.ctx()
                        .load_texture("capture-plane-checks", tex, TextureOptions::NEAREST),
                ));
            }
            if let Some((_, t)) = &view.checks_tex {
                let uv = Rect::from_min_max(
                    egui::Pos2::ZERO,
                    egui::pos2(
                        image.size[0] as f32 / (f.grid[0] * f.tile) as f32,
                        image.size[1] as f32 / (f.grid[1] * f.tile) as f32,
                    ),
                );
                clip.image(t.id(), img, uv, Color32::WHITE);
            }
            // The witness pairs' shift by quadrant (after the residual
            // correction, as the checker judges it), 0.2 photosite to 40
            // points: drawn when the group failed on it or a quadrant is
            // over the checker's limit.
            let worst = f
                .quadrants
                .iter()
                .flatten()
                .map(|v| v[0].hypot(v[1]))
                .fold(0.0, f64::max);
            let misregistered = f
                .reason
                .as_deref()
                .is_some_and(|r| r.contains("misregistered"));
            for (q, pairs) in f.quadrants.iter().enumerate() {
                if !(misregistered || worst >= PAIR_SHIFT) {
                    break;
                }
                let v = if pairs[0][0].hypot(pairs[0][1]) >= pairs[1][0].hypot(pairs[1][1]) {
                    pairs[0]
                } else {
                    pairs[1]
                };
                let m = v[0].hypot(v[1]);
                if !m.is_finite() {
                    continue;
                }
                let at = img.min
                    + egui::vec2(
                        img.width() * if q % 2 == 0 { 0.25 } else { 0.75 },
                        img.height() * if q < 2 { 0.25 } else { 0.75 },
                    );
                if !area.contains(at) {
                    continue;
                }
                let color = if m >= PAIR_SHIFT {
                    palette.warn
                } else {
                    palette.canvas_ink[0]
                };
                let tip = at + egui::vec2(v[0] as f32, v[1] as f32) * 200.0;
                clip.circle_stroke(
                    at,
                    20.0,
                    egui::Stroke::new(1.0_f32, color.gamma_multiply(0.45)),
                );
                clip.line_segment([at, tip], egui::Stroke::new(1.5_f32, color));
                clip.circle_filled(tip, 2.5, color);
                style::paint_job(
                    &clip,
                    at + egui::vec2(0.0, 26.0),
                    Align2::CENTER_TOP,
                    style::job(&format!("{m:.2} px"), 11.0, color, 0.0),
                );
            }
        }
        // The zoom at the picture's corner.
        let pct = scale * ppp * 100.0;
        let label = if view.zoom.is_none() {
            format!("Fit · {pct:.0} %")
        } else {
            format!("{pct:.0} %")
        };
        let galley = p.layout_job(style::job(&label, 11.5, palette.canvas_ink[0], 0.0));
        let r = Align2::RIGHT_BOTTOM
            .anchor_size(area.right_bottom() + egui::vec2(-8.0, -6.0), galley.size());
        p.rect_filled(
            r.expand2(egui::vec2(5.0, 2.0)),
            0.0,
            Color32::from_black_alpha(150),
        );
        p.galley(r.min, galley, palette.canvas_ink[0]);
    } else {
        let text = match &deck.failed {
            Some((_, e)) => format!("This plane could not be shown: {e}"),
            None if snap.tries.is_empty() => {
                "Each plane appears here, at full resolution, as its RAWs reach this PC".into()
            }
            None => "Reading the plane's RAWs…".into(),
        };
        let mut job = style::job(&text, 12.5, palette.canvas_ink[1], 0.0);
        job.wrap.max_width = area.width() - 40.0;
        style::paint_job(&p, area.center(), Align2::CENTER_CENTER, job);
    }
    view.tiles_drawn = drawn;
    // A build in progress: a one-pixel rule along the picture's foot.
    let building = key.is_some()
        && image
            .as_ref()
            .is_none_or(|i| Some(i.key) != key || (full && i.kind == ImageKind::Preview));
    if building && deck.failed.is_none() {
        let t = ui.input(|i| i.time) as f32;
        let x = area.left() + (t * 0.6).fract() * area.width();
        p.line_segment(
            [
                egui::pos2(area.left(), area.bottom() - 0.5),
                egui::pos2(area.right(), area.bottom() - 0.5),
            ],
            egui::Stroke::new(1.0_f32, palette.canvas_line[1]),
        );
        p.line_segment(
            [
                egui::pos2(x, area.bottom() - 0.5),
                egui::pos2((x + 80.0).min(area.right()), area.bottom() - 0.5),
            ],
            egui::Stroke::new(1.0_f32, palette.accent),
        );
        ui.ctx()
            .request_repaint_after(std::time::Duration::from_millis(33));
    }
    head_ui(
        ui,
        head,
        deck,
        view,
        &snap,
        key,
        shown_key,
        image.as_deref(),
        full,
        palette,
    );
    facts_ui(
        ui,
        facts,
        view,
        &snap,
        shown_index,
        image.as_deref(),
        inputs,
        palette,
    );
    strip_ui(ui, strip, view, &snap, key, inputs, palette);
    view.paint_ms = started.elapsed().as_secs_f64() * 1000.0;
    // ← → step through the planes; End returns to the newest.
    if !ui.ctx().wants_keyboard_input() {
        let (left, right, end) = ui.input(|i| {
            (
                i.key_pressed(egui::Key::ArrowLeft),
                i.key_pressed(egui::Key::ArrowRight),
                i.key_pressed(egui::Key::End),
            )
        });
        if end {
            view.follow();
        } else if (left || right)
            && let Some(k) = key
        {
            let planes: Vec<u64> = {
                let mut v: Vec<u64> = snap.tries.iter().map(|t| t.t.plane).collect();
                v.sort_unstable();
                v.dedup();
                v
            };
            if let Ok(at) = planes.binary_search(&k.plane) {
                let next = if left {
                    at.checked_sub(1)
                } else {
                    Some(at + 1)
                };
                if let Some(&plane) = next.and_then(|n| planes.get(n))
                    && let Some(i) = snap.find(plane, None)
                {
                    view.following = false;
                    view.selected = Some(snap.tries[i].t.key());
                }
            }
        }
    }
}

/// The head row: which try, its verdict, and the view's switches.
#[allow(clippy::too_many_arguments)]
fn head_ui(
    ui: &mut Ui,
    head: Rect,
    deck: &PlaneDeck,
    view: &mut PlaneView,
    snap: &DeckSnapshot,
    key: Option<TryKey>,
    shown: Option<TryKey>,
    image: Option<&PlaneImage>,
    full: bool,
    palette: &CapturePalette,
) {
    let p = ui.painter_at(head);
    style::hairline(&p, head.left_bottom(), head.right_bottom(), palette.line);
    let y = head.center().y;
    let tries = shown.map_or(0, |k| {
        snap.tries.iter().filter(|t| t.t.plane == k.plane).count()
    });
    let title = match shown {
        Some(k) if tries > 1 || k.attempt > 1 => format!(
            "Plane {} · try {} of {}",
            k.plane,
            k.attempt,
            tries.max(k.attempt as usize)
        ),
        Some(k) => format!("Plane {}", k.plane),
        None => "Plane".into(),
    };
    let t = style::paint_job(
        &p,
        egui::pos2(head.left() + 2.0, y),
        Align2::LEFT_CENTER,
        style::caps_job(&title, 10.5, palette.ink),
    );
    // Following, holding, or picked.
    let newest = snap.newest().map(|i| snap.tries[i].t.key());
    let state = if view.following && key == newest {
        "following the newest".to_owned()
    } else if view.following {
        format!(
            "holding while you look · newest {}",
            newest.map_or(0, |n| n.plane)
        )
    } else {
        String::new()
    };
    // Reading: the picture asked for is not the one shown yet.
    let note = match (key, image) {
        _ if deck.failed.as_ref().is_some_and(|(f, _)| Some(*f) == key) => state,
        (Some(k), Some(i)) if i.key != k && k.plane != i.key.plane => {
            format!("reading plane {}…", k.plane)
        }
        (Some(k), Some(i)) if i.key != k => format!("reading try {}…", k.attempt),
        (Some(_), Some(i)) if i.kind == ImageKind::Preview && full => {
            "reading its RAWs…".to_owned()
        }
        (Some(_), Some(i)) if i.kind == ImageKind::Preview => {
            format!("{state} · camera preview: zoom in for the RAWs")
        }
        (Some(_), None) => "reading its RAWs…".to_owned(),
        _ => state,
    };
    let mut right = head.right();
    // Switches, right to left.
    let mut child = ui.new_child(
        egui::UiBuilder::new()
            .max_rect(Rect::from_min_max(
                egui::pos2(t.right() + 12.0, head.top() + 3.0),
                egui::pos2(head.right(), head.bottom() - 3.0),
            ))
            .layout(egui::Layout::right_to_left(egui::Align::Center)),
    );
    child.spacing_mut().item_spacing.x = 4.0;
    if !view.following {
        let label = match newest {
            Some(n) => format!("Newest · {}", n.plane),
            None => "Newest".into(),
        };
        if style::button(&mut child, &label, ButtonKind::Plain, 22.0, true, palette)
            .on_hover_text("Follow the newest plane as it arrives (End)")
            .clicked()
        {
            view.follow();
        }
    }
    child.add_space(6.0);
    let fit = view.zoom.is_none();
    if style::button(
        &mut child,
        "1:1",
        if fit {
            ButtonKind::Quiet
        } else {
            ButtonKind::On
        },
        22.0,
        image.is_some(),
        palette,
    )
    .on_hover_text("One photosite a screen pixel (double click the picture)")
    .clicked()
        && let Some(i) = image
    {
        let _ = i;
        view.zoom = Some(1.0 / ui.ctx().pixels_per_point());
    }
    if style::button(
        &mut child,
        "Fit",
        if fit {
            ButtonKind::On
        } else {
            ButtonKind::Quiet
        },
        22.0,
        true,
        palette,
    )
    .clicked()
    {
        view.zoom = None;
    }
    child.add_space(6.0);
    if style::button(&mut child, "Checks", if view.checks { ButtonKind::On } else { ButtonKind::Quiet }, 22.0, true, palette)
        .on_hover_text(
            "The checker's findings on the picture: witness tiles over its limit (where the four shots disagree) and the witness pairs' shift in each quadrant, 0.2 photosite drawn 40 points long",
        )
        .clicked()
    {
        view.checks = !view.checks;
    }
    if style::button(&mut child, "Sharp", if view.sharp { ButtonKind::On } else { ButtonKind::Quiet }, 22.0, true, palette)
        .on_hover_text(
            "Where this plane is within 70 % of the sharpest any plane has been there, from the camera previews' detail: the band of the subject in focus now",
        )
        .clicked()
    {
        view.sharp = !view.sharp;
    }
    right = right.min(child.min_rect().left());
    if !note.is_empty() {
        let mut job = style::job(&note, 12.0, palette.ink3, 0.0);
        job.wrap.max_width = (right - t.right() - 24.0).max(10.0);
        job.wrap.max_rows = 1;
        style::paint_job(
            &p,
            egui::pos2(t.right() + 12.0, y),
            Align2::LEFT_CENTER,
            job,
        );
    }
}

/// One fact: a mark (or none), its text and colour, and a hover.
struct Fact {
    mark: Option<Mark>,
    text: String,
    color: Color32,
    tip: Option<String>,
}

/// The facts under the picture, laid out in rows as they fit.
#[allow(clippy::too_many_arguments)]
fn facts_ui(
    ui: &mut Ui,
    rect: Rect,
    view: &mut PlaneView,
    snap: &DeckSnapshot,
    index: Option<usize>,
    image: Option<&PlaneImage>,
    inputs: &PlaneInputs<'_>,
    palette: &CapturePalette,
) {
    let Some(i) = index else {
        return;
    };
    let info = &snap.tries[i];
    let t = &info.t;
    let mut facts = Vec::new();
    // The verdict, and what the stack does with this try.
    let item = item_of(view, inputs.progress, t.key(), t.first().map(|s| &**s));
    let later = snap
        .tries
        .iter()
        .filter(|o| o.t.plane == t.plane && o.t.attempt > t.attempt)
        .map(|o| o.t.attempt)
        .min();
    let last = later.is_none();
    let (mark, title, then) = verdict_text(item, last, later, inputs.checking);
    facts.push(Fact {
        mark: Some(mark),
        text: if then.is_empty() {
            title.clone()
        } else {
            format!("{title}. {then}")
        },
        color: palette.ink,
        tip: item.and_then(|i| i.reason.as_deref().map(|r| format!("Checker: {r}"))),
    });
    // Sharpness, and how much of it the neighbouring planes share.
    if let Some(map) = &info.map {
        let share = snap.share(map);
        let neighbour = |plane: u64| {
            snap.tries
                .iter()
                .rev()
                .find(|o| o.t.plane == plane)
                .and_then(|o| o.map.as_ref())
                .and_then(|m| overlap(snap, map, m))
        };
        let prev = t.plane.checked_sub(1).and_then(neighbour);
        let next = neighbour(t.plane + 1);
        let mut text = format!("Sharp in {:.0} % of the frame", share * 100.0);
        let mut parts = Vec::new();
        if let Some(o) = prev {
            parts.push(format!(
                "{:.0} % shared with plane {}",
                o * 100.0,
                t.plane - 1
            ));
        }
        if let Some(o) = next {
            parts.push(format!("{:.0} % with {}", o * 100.0, t.plane + 1));
        }
        if !parts.is_empty() {
            text.push_str(&format!(" · {}", parts.join(", ")));
        }
        let gap = share > 0.01 && prev == Some(0.0) && next.is_none_or(|n| n == 0.0);
        facts.push(Fact {
            mark: gap.then_some(Mark::Warn),
            text: if gap { format!("{text} · no overlap: a gap in depth?") } else { text },
            color: if gap { palette.warn } else { palette.ink2 },
            tip: Some(
                "From the camera previews: cells within 70 % of the sharpest any plane has been there. Neighbouring planes that share none of it leave a band of depth no plane resolves."
                    .into(),
            ),
        });
    }
    // The checker's numbers for a four-shot group.
    if let Some(f) = image
        .filter(|im| im.key == t.key())
        .and_then(|im| im.findings.as_ref())
    {
        let text = if !f.parities {
            format!(
                "Offsets {:?} miss a colour site: the first shot is shown",
                &f.offsets[1..]
            )
        } else {
            let shift = f
                .pair_shift
                .iter()
                .map(|v| v[0].hypot(v[1]))
                .fold(0.0, f64::max);
            let over =
                f.z2.iter()
                    .filter(|z| f.median > 0.0 && **z >= f.median * TILE_RATIO as f32)
                    .count();
            format!(
                "Witness tiles {:.2}× median at p99 (limit {:.1}){} · pair shift {:.2} px (limit {:.1})",
                f.ratio,
                TILE_RATIO,
                if over > 0 {
                    format!(", {over} over")
                } else {
                    String::new()
                },
                shift,
                PAIR_SHIFT
            )
        };
        let bad = f.reason.is_some();
        facts.push(Fact {
            mark: None,
            text,
            color: if bad { palette.warn } else { palette.ink2 },
            tip: Some(format!(
                "Measured here from the decoded RAWs, as the checker measures the group.\nOffsets {:?}, gains {:.4?}, structure {:.3?}\n{}{}",
                f.offsets,
                f.gains,
                f.structure,
                f.reason.as_deref().map_or("Passes the checker's gates.".to_owned(), |r| format!("Checker: {r}")),
                if f.retake { "\nA retake could pass." } else { "" }
            )),
        });
    }
    // Focus and the step from the plane before.
    let focus = t.focus.or(item.and_then(|i| i.target));
    if let Some(f) = focus {
        let before = snap
            .tries
            .iter()
            .filter(|o| o.t.plane + 1 == t.plane)
            .find_map(|o| o.t.focus);
        let step = before
            .map(|b| {
                format!(
                    " · {:+} from plane {}",
                    i64::from(f) - i64::from(b),
                    t.plane - 1
                )
            })
            .unwrap_or_default();
        facts.push(Fact {
            mark: None,
            text: format!("Focus {}{step}", style::focus_units(f)),
            color: palette.ink2,
            tip: Some("The lens position the camera reported for this group".into()),
        });
    }
    if let Some(ms) = t.taken_ms {
        facts.push(Fact {
            mark: None,
            text: format!("Taken {}", clock(ms)),
            color: palette.ink2,
            tip: None,
        });
    }
    let iso = image.filter(|im| im.key == t.key()).and_then(|im| im.iso);
    if let Some(e) = &inputs.exposure {
        facts.push(Fact {
            mark: None,
            text: match iso {
                Some(iso) if !e.contains(&format!("ISO {iso:.0}")) => {
                    format!("{e} · RAW ISO {iso:.0}")
                }
                _ => e.clone(),
            },
            color: palette.ink2,
            tip: None,
        });
    }
    // What the picture is.
    if let Some(im) = image.filter(|im| im.key == t.key()) {
        let what = match im.kind {
            ImageKind::FourShot => "Four shots combined",
            ImageKind::FirstShot => "First shot, demosaiced",
            ImageKind::OneShot => "One shot, demosaiced",
            ImageKind::Preview => "The camera's preview",
        };
        let mut text = format!("{what} · {} × {}", im.size[0], im.size[1]);
        if im.kind != ImageKind::Preview && im.display_ev > 0.05 {
            text.push_str(&format!(" · display +{:.1} EV", im.display_ev));
        }
        facts.push(Fact {
            mark: None,
            text,
            color: palette.ink3,
            tip: Some(format!(
                "Developed here with the camera's matrix and white balance; the display gain is the same for every plane of the run.\nRead in {:.2} s, checked in {:.2} s, developed in {:.2} s.",
                im.cost[0] / 1000.0,
                im.cost[1] / 1000.0,
                im.cost[2] / 1000.0
            )),
        });
    }
    // Lay out: left to right, wrapping, as many rows as fit.
    let p = ui.painter_at(rect);
    let row_h = 18.0;
    let mut x = rect.left();
    let mut y = rect.top() + row_h / 2.0;
    for (n, f) in facts.iter().enumerate() {
        let mut job = style::job(&f.text, 12.0, f.color, 0.0);
        let indent = if f.mark.is_some() { 12.0 } else { 0.0 };
        let galley = p.layout_job(job.clone());
        let w = galley.size().x + indent;
        if x > rect.left() && x + w > rect.right() {
            x = rect.left();
            y += row_h;
        }
        if y > rect.bottom() {
            break;
        }
        job.wrap.max_width = (rect.right() - x - indent).max(20.0);
        job.wrap.max_rows = 1;
        if let Some(m) = f.mark {
            style::mark(&p, egui::pos2(x + 3.5, y), m, 7.0, palette);
        }
        let r = style::paint_job(&p, egui::pos2(x + indent, y), Align2::LEFT_CENTER, job);
        if let Some(tip) = &f.tip {
            let _ = ui
                .interact(r, ui.id().with(("capture-plane-fact", n)), Sense::hover())
                .on_hover_text(tip);
        }
        x = r.right() + 18.0;
    }
}

/// The history strip: a bar a plane, its height the sharp share.
fn strip_ui(
    ui: &mut Ui,
    rect: Rect,
    view: &mut PlaneView,
    snap: &DeckSnapshot,
    key: Option<TryKey>,
    inputs: &PlaneInputs<'_>,
    palette: &CapturePalette,
) {
    let p = ui.painter_at(rect);
    style::hairline(&p, rect.left_top(), rect.right_top(), palette.line);
    let seen = snap.tries.iter().map(|t| t.t.plane).max().unwrap_or(0);
    let planes = inputs.total.max(seen).max(1);
    let stamp = (
        snap.revision,
        inputs.progress.map_or(0, |p| p.feed.len()),
        planes,
    );
    if view.strip.as_ref().is_none_or(|(s, _)| *s != stamp) {
        view.strip = Some((stamp, bars(snap, inputs.progress, planes)));
    }
    let Some((_, bars)) = &view.strip else {
        return;
    };
    let label = style::paint_job(
        &p,
        egui::pos2(rect.left() + 2.0, rect.top() + 9.0),
        Align2::LEFT_CENTER,
        style::caps_job("Planes · sharp share", 9.5, palette.ink3),
    );
    style::paint_job(
        &p,
        egui::pos2(rect.right() - 2.0, rect.top() + 9.0),
        Align2::RIGHT_CENTER,
        style::job(&format!("1–{planes}"), 11.0, palette.ink3, 0.0),
    );
    let chart = Rect::from_min_max(
        egui::pos2(rect.left(), label.bottom() + 3.0),
        egui::pos2(rect.right(), rect.bottom() - 4.0),
    );
    let top = bars
        .iter()
        .filter_map(|b| b.share)
        .fold(0.0f32, f32::max)
        .max(0.01);
    let columns = chart.width().floor().max(1.0) as usize;
    let per = (planes as f32 / columns as f32).max(1.0);
    let bar_w = (chart.width() / planes as f32).max(1.0);
    let mut mesh = egui::Mesh::default();
    let base = chart.bottom() - 3.0;
    let height = base - chart.top();
    let quad = |mesh: &mut egui::Mesh, r: Rect, c: Color32| mesh.add_colored_rect(r, c);
    // One column a pixel when the planes outnumber them: the most sharp and
    // the worst mark of the planes in it.
    let n_cols = if per > 1.0 { columns } else { planes as usize };
    for c in 0..n_cols {
        let (lo, hi) = if per > 1.0 {
            (
                (c as f32 * per) as usize,
                (((c + 1) as f32 * per) as usize).min(bars.len()),
            )
        } else {
            (c, c + 1)
        };
        let mut share: Option<f32> = None;
        let mut mark: Option<Mark> = None;
        for b in &bars[lo.min(bars.len())..hi.max(lo).min(bars.len())] {
            if let Some(s) = b.share {
                share = Some(share.map_or(s, |v: f32| v.max(s)));
            }
            mark = match (mark, b.mark) {
                (Some(Mark::Bad), _) | (_, Some(Mark::Bad)) => Some(Mark::Bad),
                (Some(Mark::Warn), _) | (_, Some(Mark::Warn)) => Some(Mark::Warn),
                (m, n) => n.or(m),
            };
        }
        let x0 = chart.left()
            + if per > 1.0 {
                c as f32
            } else {
                c as f32 * bar_w
            };
        let w = if per > 1.0 {
            1.0
        } else {
            (bar_w - 1.0).max(1.0)
        };
        if let Some(s) = share {
            let h = (s / top * height).max(1.0);
            quad(
                &mut mesh,
                Rect::from_min_size(egui::pos2(x0, base - h), egui::vec2(w, h)),
                palette.ink3.gamma_multiply(0.85),
            );
        }
        if let Some(m @ (Mark::Bad | Mark::Warn)) = mark {
            quad(
                &mut mesh,
                Rect::from_min_size(egui::pos2(x0, base + 1.0), egui::vec2(w, 2.0)),
                palette.mark_color(m),
            );
        }
    }
    p.add(egui::Shape::mesh(mesh));
    style::hairline(
        &p,
        egui::pos2(chart.left(), base + 0.5),
        egui::pos2(chart.right(), base + 0.5),
        palette.line,
    );
    let x_of = |plane: u64| {
        chart.left() + (plane.saturating_sub(1) as f32 + 0.5) / planes as f32 * chart.width()
    };
    if let Some(k) = key {
        let x = x_of(k.plane);
        p.line_segment(
            [egui::pos2(x, chart.top()), egui::pos2(x, base + 3.0)],
            egui::Stroke::new(1.0_f32, palette.accent),
        );
    }
    // Pick: click or drag along the strip.
    let resp = ui.interact(
        chart,
        ui.id().with("capture-plane-strip"),
        Sense::click_and_drag(),
    );
    let plane_at = |x: f32| {
        (((x - chart.left()) / chart.width() * planes as f32).floor() as i64 + 1)
            .clamp(1, planes as i64) as u64
    };
    if let Some(at) = resp.hover_pos() {
        let plane = plane_at(at.x);
        let b = bars.get(plane as usize - 1).copied().unwrap_or_default();
        let mut tip = format!("Plane {plane}");
        if let Some(s) = b.share {
            tip.push_str(&format!(" · sharp in {:.0} % of the frame", s * 100.0));
        } else if plane > seen {
            tip.push_str(" · to come");
        }
        if b.retaken {
            tip.push_str(" · retaken");
        }
        resp.clone().on_hover_text(tip);
    }
    if (resp.clicked() || resp.dragged())
        && let Some(at) = resp.interact_pointer_pos()
        && let Some(i) = snap.find(plane_at(at.x), None)
    {
        view.following = false;
        view.selected = Some(snap.tries[i].t.key());
    }
}

#[cfg(test)]
#[path = "capture-plane-view-tests.rs"]
mod tests;
