//! The live view in the Capture canvas (Studio 2; mockup `capture-plan.html`):
//! the camera's JPEG preview fitted or at 100 %, focus peaking with its
//! threshold, the clipping overlay, a thirds grid, the subject box, the
//! camera magnifier, and the estimate panel, labelled "estimate, not the
//! RAW".
//!
//! The subject box keeps its corner marks and has eight square handles
//! (corners and edge midpoints): a handle resizes it, a drag inside moves
//! it, a drag outside draws a new one. It is clamped to the picture and no
//! smaller than the host accepts ([`MIN_BOX`]); the new box goes to the host
//! on release, as a drawn one always did, and is shown until the host has it.
//!
//! The estimate panel draws the preview's histograms antialiased (luma filled
//! and stroked, red, green and blue as lines) with the black and clipped
//! shares at their ends; the focus in the subject box with its recent trace
//! (it rises as the lens brings the box's detail into focus; the lens
//! position of the sharpest recent preview is named); the exposure and the
//! preview rate.
//!
//! Textures are uploaded only when the preview's generation (or the peaking
//! threshold) changes. The per-pixel work (histograms, clip mask, focus
//! tiles) is done on the client thread; here the histogram and the focus
//! trace are meshes rebuilt once per generation (or rectangle), and the box's
//! focus is reduced from at most 768 tiles once per generation or box.
use std::collections::VecDeque;
use std::sync::Arc;

use eframe::egui::{
    self, Align2, Color32, CursorIcon, Mesh, Pos2, Rect, Sense, Shape, Stroke, StrokeKind,
    TextureHandle, TextureOptions, Ui, Vec2,
    epaint::{TessellationOptions, Tessellator},
};
use strehl_capture::model::{Roi, Subject};

use super::style::{self, ButtonKind, CapturePalette, Mark};
use crate::capture_aids::{PREVIEW_BLACK_CODE, PREVIEW_CLIP_CODE, PreviewLevels};
use crate::capture_client::Snapshot;

/// What the user asked of the live view.
#[derive(Clone, Debug, PartialEq)]
pub(crate) enum LiveIntent {
    /// A new subject box, normalised to the preview.
    SetRoi(Roi),
    /// A new subject outline (plan S3), or none.
    SetSubject(Option<Subject>),
    /// Find the subject automatically (plan S2), or again with other
    /// Sensitivity, Grow and Buffer.
    AutoSubject,
    AutoParams {
        sensitivity: f32,
        grow: f32,
        buffer_px: f32,
    },
    /// Remove the outline and put the automatic selection away (owner,
    /// 2026-11-24: "there is no way to clear a polygon").
    ClearOutline,
    /// The camera magnifier at `ratio` (0 off) centred at `x`, `y` of 639 x 479.
    Magnify { ratio: u32, x: u16, y: u16 },
}

/// The smallest subject box, as a share of the preview's width and height
/// (the host refuses smaller: `Roi::valid`).
pub(crate) const MIN_BOX: f32 = 0.05;
/// A handle's drawn side and its reach (points from its centre).
const HANDLE: f32 = 7.0;
const HANDLE_REACH: f32 = 8.0;
/// How near an edge between handles still takes that edge.
const EDGE_REACH: f32 = 4.0;
/// How many previews the focus trace keeps.
pub(crate) const TRACE_LEN: usize = 48;
/// The estimate panel's size.
const PANEL: Vec2 = Vec2::new(300.0, 202.0);

/// A handle of the subject box.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(crate) enum Handle {
    NorthWest,
    North,
    NorthEast,
    East,
    SouthEast,
    South,
    SouthWest,
    West,
}

impl Handle {
    pub const ALL: [Handle; 8] = [
        Handle::NorthWest,
        Handle::North,
        Handle::NorthEast,
        Handle::East,
        Handle::SouthEast,
        Handle::South,
        Handle::SouthWest,
        Handle::West,
    ];
    /// The sides it moves: left, right, top, bottom.
    fn sides(self) -> (bool, bool, bool, bool) {
        match self {
            Handle::NorthWest => (true, false, true, false),
            Handle::North => (false, false, true, false),
            Handle::NorthEast => (false, true, true, false),
            Handle::East => (false, true, false, false),
            Handle::SouthEast => (false, true, false, true),
            Handle::South => (false, false, false, true),
            Handle::SouthWest => (true, false, false, true),
            Handle::West => (true, false, false, false),
        }
    }
    fn is_corner(self) -> bool {
        let (l, r, t, b) = self.sides();
        (l || r) && (t || b)
    }
    /// Where it sits on `r`.
    pub fn at(self, r: Rect) -> Pos2 {
        let (l, rt, t, b) = self.sides();
        let x = if l {
            r.left()
        } else if rt {
            r.right()
        } else {
            r.center().x
        };
        let y = if t {
            r.top()
        } else if b {
            r.bottom()
        } else {
            r.center().y
        };
        egui::pos2(x, y)
    }
    pub fn cursor(self) -> CursorIcon {
        match self {
            Handle::North | Handle::South => CursorIcon::ResizeVertical,
            Handle::East | Handle::West => CursorIcon::ResizeHorizontal,
            Handle::NorthWest | Handle::SouthEast => CursorIcon::ResizeNwSe,
            Handle::NorthEast | Handle::SouthWest => CursorIcon::ResizeNeSw,
        }
    }
}

/// What a point on the picture is, for the subject box drawn at `r`.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(crate) enum BoxHit {
    Handle(Handle),
    Inside,
    Outside,
}

/// Hit-tests the box drawn at `r` (screen points): corners first, then the
/// edge midpoints, then the edges themselves, then inside.
pub(crate) fn box_hit(r: Rect, pos: Pos2) -> BoxHit {
    let near = |h: Handle| {
        let d = (h.at(r) - pos).abs();
        d.x <= HANDLE_REACH && d.y <= HANDLE_REACH
    };
    if let Some(h) = Handle::ALL
        .into_iter()
        .filter(|h| h.is_corner())
        .chain(Handle::ALL.into_iter().filter(|h| !h.is_corner()))
        .find(|h| near(*h))
    {
        return BoxHit::Handle(h);
    }
    let within_x = pos.x >= r.left() && pos.x <= r.right();
    let within_y = pos.y >= r.top() && pos.y <= r.bottom();
    let edge = [
        (
            Handle::West,
            within_y && (pos.x - r.left()).abs() <= EDGE_REACH,
        ),
        (
            Handle::East,
            within_y && (pos.x - r.right()).abs() <= EDGE_REACH,
        ),
        (
            Handle::North,
            within_x && (pos.y - r.top()).abs() <= EDGE_REACH,
        ),
        (
            Handle::South,
            within_x && (pos.y - r.bottom()).abs() <= EDGE_REACH,
        ),
    ]
    .into_iter()
    .find(|(_, hit)| *hit);
    match edge {
        Some((h, _)) => BoxHit::Handle(h),
        None if r.contains(pos) => BoxHit::Inside,
        None => BoxHit::Outside,
    }
}

/// `from` (preview fractions) with `handle` moved by `delta`: the sides it
/// moves follow, within the picture and no closer than `min` to the
/// opposite side (the box never turns inside out).
pub(crate) fn resized(from: Rect, handle: Handle, delta: Vec2, min: f32) -> Rect {
    let (l, r, t, b) = handle.sides();
    let (mut x0, mut x1, mut y0, mut y1) = (from.left(), from.right(), from.top(), from.bottom());
    if l {
        x0 = (x0 + delta.x).min(x1 - min).max(0.0);
    }
    if r {
        x1 = (x1 + delta.x).max(x0 + min).min(1.0);
    }
    if t {
        y0 = (y0 + delta.y).min(y1 - min).max(0.0);
    }
    if b {
        y1 = (y1 + delta.y).max(y0 + min).min(1.0);
    }
    Rect::from_min_max(egui::pos2(x0, y0), egui::pos2(x1, y1))
}

/// `from` moved by `delta`, kept whole inside the picture.
pub(crate) fn moved(from: Rect, delta: Vec2) -> Rect {
    let x = (from.left() + delta.x).min(1.0 - from.width()).max(0.0);
    let y = (from.top() + delta.y).min(1.0 - from.height()).max(0.0);
    Rect::from_min_size(egui::pos2(x, y), from.size())
}

/// Two outlines agree to a ten-thousandth of the frame.
fn same_rings(a: &[Vec<Pos2>], b: &[Vec<Pos2>]) -> bool {
    a.len() == b.len()
        && a.iter().zip(b).all(|(x, y)| {
            x.len() == y.len()
                && x.iter()
                    .zip(y)
                    .all(|(p, q)| (p.x - q.x).abs() < 1e-4 && (p.y - q.y).abs() < 1e-4)
        })
}

fn roi_rect(roi: Roi) -> Rect {
    Rect::from_min_size(egui::pos2(roi.x, roi.y), egui::vec2(roi.width, roi.height))
}

fn rect_roi(r: Rect) -> Roi {
    Roi {
        x: r.left(),
        y: r.top(),
        width: r.width(),
        height: r.height(),
    }
}

fn same_roi(a: Roi, b: Roi) -> bool {
    (a.x - b.x).abs() < 1e-3
        && (a.y - b.y).abs() < 1e-3
        && (a.width - b.width).abs() < 1e-3
        && (a.height - b.height).abs() < 1e-3
}

/// A drag on the picture.
#[derive(Clone, Copy, Debug, PartialEq)]
enum BoxDrag {
    /// A new box from this point (preview fractions).
    Draw(Pos2),
    /// The box as it was (preview fractions) and where the press was.
    Move { from: Rect, press: Pos2 },
    Resize {
        from: Rect,
        handle: Handle,
        press: Pos2,
    },
}

/// The focus in the subject box of one preview.
#[derive(Clone, Copy, Debug, PartialEq)]
pub(crate) struct FocusSample {
    /// Where the lens was when the preview arrived.
    pub lens: Option<u16>,
    /// The box's mean squared Laplacian (`FocusTiles::focus_in`).
    pub value: f32,
}

/// What makes focus readings comparable: the same box, magnifier,
/// exposure and preview size.
#[derive(Clone, Copy, Debug, PartialEq)]
struct TraceContext {
    roi: [u32; 4],
    magnifier: Option<u64>,
    iso: Option<u64>,
    shutter: Option<u64>,
    size: [usize; 2],
}

/// The subject box's focus over the recent previews, and when they came.
#[derive(Default)]
pub(crate) struct FocusTrace {
    context: Option<TraceContext>,
    /// The preview last read for this context, and the last seen at all.
    generation: Option<u64>,
    arrived: Option<u64>,
    samples: VecDeque<FocusSample>,
    arrivals: VecDeque<f64>,
    /// Changes with every sample: the trace mesh's cache key.
    pub revision: u64,
}

impl FocusTrace {
    /// Takes the box's focus from a new preview, once per generation; a new
    /// box, magnifier ratio, exposure or preview size starts the trace again
    /// (its readings are not comparable). `now` is the input's time.
    pub fn observe(&mut self, s: &Snapshot, roi: Roi, now: f64) -> bool {
        let Some((generation, peaks)) = &s.peaking else {
            return false;
        };
        let e = s.host.exposure.as_ref();
        let context = TraceContext {
            roi: [
                roi.x.to_bits(),
                roi.y.to_bits(),
                roi.width.to_bits(),
                roi.height.to_bits(),
            ],
            magnifier: s.host.magnifier_current,
            iso: e.and_then(|e| e.iso),
            shutter: e.and_then(|e| e.shutter),
            size: peaks.focus.size,
        };
        if self.context != Some(context) {
            if self.context.is_some() {
                self.samples.clear();
            }
            self.context = Some(context);
            self.generation = None;
        }
        if self.arrived != Some(*generation) {
            self.arrived = Some(*generation);
            if self.arrivals.len() == 8 {
                self.arrivals.pop_front();
            }
            self.arrivals.push_back(now);
        }
        if self.generation == Some(*generation) {
            return false;
        }
        self.generation = Some(*generation);
        if let Some(value) = peaks.focus.focus_in(roi.x, roi.y, roi.width, roi.height) {
            if self.samples.len() == TRACE_LEN {
                self.samples.pop_front();
            }
            self.samples.push_back(FocusSample {
                lens: s.host.position,
                value,
            });
        }
        self.revision += 1;
        true
    }

    /// Readings from before the first preview (fixtures): oldest first.
    pub fn seed(&mut self, samples: impl IntoIterator<Item = FocusSample>) {
        for sample in samples {
            if self.samples.len() == TRACE_LEN {
                self.samples.pop_front();
            }
            self.samples.push_back(sample);
        }
        self.revision += 1;
    }

    pub fn samples(&self) -> &VecDeque<FocusSample> {
        &self.samples
    }

    pub fn latest(&self) -> Option<FocusSample> {
        self.samples.back().copied()
    }

    /// The sharpest reading kept (the newest of equals).
    pub fn best(&self) -> Option<FocusSample> {
        self.samples
            .iter()
            .copied()
            .reduce(|best, s| if s.value >= best.value { s } else { best })
    }

    /// The latest reading as a share of the best (0-1).
    pub fn share_of_best(&self) -> Option<f32> {
        let (latest, best) = (self.latest()?, self.best()?);
        (best.value > 0.0).then(|| latest.value / best.value)
    }

    /// Previews a second over the last few, when at least three came within
    /// the last five seconds of `now`.
    pub fn rate(&self, now: f64) -> Option<f32> {
        let recent: Vec<f64> = self
            .arrivals
            .iter()
            .copied()
            .filter(|t| now - t <= 5.0)
            .collect();
        let (first, last) = (recent.first()?, recent.last()?);
        (recent.len() >= 3 && last > first)
            .then(|| ((recent.len() - 1) as f64 / (last - first)) as f32)
    }
}

/// A cached mesh and its key.
type MeshCache<K> = Option<(K, Arc<Mesh>)>;
/// The histogram's key: the preview's generation, the rectangle, the scale.
type HistogramKey = (u64, [u32; 4], u32);
/// The trace's key: its revision, the rectangle, the scale.
type TraceKey = (u64, [u32; 4], u32);

fn rect_bits(r: Rect) -> [u32; 4] {
    [
        r.left().to_bits(),
        r.top().to_bits(),
        r.width().to_bits(),
        r.height().to_bits(),
    ]
}

/// The live view's switches and textures.
pub(crate) struct LiveView {
    pub actual_size: bool,
    pub peaking: bool,
    pub threshold: u8,
    pub clipping: bool,
    pub grid: bool,
    pub subject_box: bool,
    /// The subject is drawn as an outline (plan S3) instead of a box.
    pub outline: bool,
    /// The subject box or outline was chosen by hand; until then an outline
    /// the host holds is shown as one (owner, 2026-11-24: the outline and
    /// Auto were hard to find).
    outline_chosen: bool,
    outline_edit: OutlineEdit,
    /// An outline sent to the host, shown until the host reports it.
    outline_sent: Option<Vec<Vec<Pos2>>>,
    /// The automatic selection, as the station has it.
    pub auto: AutoView,
    /// The calibration's depth map, as the station has it, and whether the
    /// Depth lens is on (spec 6.1).
    pub depth: Option<Arc<DepthMap>>,
    pub lens: Lens,
    /// The depth rail's hovered position: the Depth lens isolates what is in
    /// focus there instead of at the lens (spec 6.2).
    pub rail_hover: Option<u16>,
    lens_mesh: Option<(LensKey, Arc<Mesh>, Cover)>,
    /// The sliders while dragged.
    auto_draft: Option<[f32; 3]>,
    /// The tool bar's width as last drawn: its box fits its buttons, and the
    /// estimate panel moves above it when both do not fit side by side.
    bar_width: f32,
    drag: Option<BoxDrag>,
    /// A box sent to the host, shown until the host reports it (or for
    /// three seconds), so a resized box does not jump back meanwhile.
    sent: Option<(Roi, f64)>,
    preview: Option<(u64, TextureHandle)>,
    peaks: Option<(u64, u8, TextureHandle)>,
    clip: Option<(u64, TextureHandle)>,
    histogram: MeshCache<HistogramKey>,
    trace_mesh: MeshCache<TraceKey>,
    /// The subject box's focus over the recent previews.
    pub trace: FocusTrace,
    /// Texture uploads (tests and performance checks).
    pub uploads: u64,
    /// Histogram and trace mesh builds (tests and performance checks).
    pub mesh_builds: u64,
}

impl Default for LiveView {
    fn default() -> Self {
        Self {
            actual_size: false,
            peaking: true,
            threshold: 18,
            clipping: true,
            grid: false,
            subject_box: true,
            outline: false,
            outline_chosen: false,
            outline_edit: OutlineEdit::None,
            outline_sent: None,
            auto: AutoView::default(),
            depth: None,
            lens: Lens::Off,
            rail_hover: None,
            lens_mesh: None,
            auto_draft: None,
            bar_width: 520.0,
            drag: None,
            sent: None,
            preview: None,
            peaks: None,
            clip: None,
            histogram: None,
            trace_mesh: None,
            trace: FocusTrace::default(),
            uploads: 0,
            mesh_builds: 0,
        }
    }
}

/// A lens's mesh: one square per tile, a hairline of picture between
/// tiles.
///
/// - Depth: tiles with a focus in the ramp's colour at [`LENS_ALPHA`]; with
///   the lens position `at`, tiles not in focus there are dimmed (spec 6.2).
/// - Cover: against the plan's ends `marks`, a tile in focus within the
///   planes (with half a sharp depth each side) faint, one in focus only
///   before Start or after End in the warning colour, counted.
/// - Light: the subject's tiles by the body's level at the chosen exposure,
///   in five bands.
/// - Glints: the subject's tiles whose highlights pass the pin at the chosen
///   exposure, by how many stops; outlined when the highlight groups hold
///   them, filled when they pin anyway.
#[allow(clippy::too_many_arguments)]
fn lens_mesh(
    lens: Lens,
    map: &DepthMap,
    photo: Rect,
    uv: Rect,
    at: Option<u16>,
    marks: Option<(u16, u16)>,
    exposure: Option<LensExposure>,
    palette: &CapturePalette,
) -> (Mesh, Cover) {
    let mut mesh = Mesh::default();
    let mut cover = Cover::default();
    if let (Lens::Still, Some(still)) = (lens, &map.still) {
        still_mesh(&mut mesh, &mut cover, still, photo, uv, palette);
        return (mesh, cover);
    }
    if let (Lens::Light | Lens::Glints, Some(light), Some(e)) = (lens, &map.light, exposure) {
        light_mesh(
            &mut mesh, &mut cover, lens, map, light, e, photo, uv, palette,
        );
        return (mesh, cover);
    }
    let span = (map.hi - map.lo).max(1.0);
    let to_screen = |u: f32, v: f32| {
        egui::pos2(
            photo.left() + (u - uv.left()) / uv.width() * photo.width(),
            photo.top() + (v - uv.top()) / uv.height() * photo.height(),
        )
    };
    let (tw, th) = (
        map.extent[0] / map.cols.max(1) as f32,
        map.extent[1] / map.rows.max(1) as f32,
    );
    for ty in 0..map.rows {
        for tx in 0..map.cols {
            let Some(f) = map.focus[ty * map.cols + tx] else {
                continue;
            };
            let a = to_screen(tx as f32 * tw, ty as f32 * th);
            let b = to_screen((tx + 1) as f32 * tw, (ty + 1) as f32 * th);
            let r = Rect::from_min_max(a, b).shrink(0.5);
            if r.width() <= 0.0 || !r.intersects(photo) {
                continue;
            }
            let c = match (lens, marks) {
                (Lens::Cover, Some((s, e))) => {
                    cover.tiles += 1;
                    let half = 0.5 * map.depth;
                    let (lo, hi) = (f64::from(s.min(e)) - half, f64::from(s.max(e)) + half);
                    if f < lo {
                        cover.before += 1;
                        palette.warn.gamma_multiply(LENS_ALPHA)
                    } else if f > hi {
                        cover.after += 1;
                        palette.warn.gamma_multiply(LENS_ALPHA)
                    } else {
                        palette.ink3.gamma_multiply(0.28)
                    }
                }
                _ => {
                    let near = at.is_none_or(|p| (f - f64::from(p)).abs() <= 0.5 * map.depth);
                    let alpha = if near { LENS_ALPHA } else { LENS_DIM };
                    ramp(((f - map.lo) / span) as f32).gamma_multiply(alpha)
                }
            };
            mesh.add_colored_rect(r.intersect(photo), c);
        }
    }
    (mesh, cover)
}

/// The Light and Glints lenses' tiles (see [`lens_mesh`]).
#[allow(clippy::too_many_arguments)]
fn light_mesh(
    mesh: &mut Mesh,
    tally: &mut Cover,
    lens: Lens,
    map: &DepthMap,
    light: &LightMap,
    e: LensExposure,
    photo: Rect,
    uv: Rect,
    palette: &CapturePalette,
) {
    let to_screen = |u: f32, v: f32| {
        egui::pos2(
            photo.left() + (u - uv.left()) / uv.width() * photo.width(),
            photo.top() + (v - uv.top()) / uv.height() * photo.height(),
        )
    };
    let (tw, th) = (
        map.extent[0] / map.cols.max(1) as f32,
        map.extent[1] / map.rows.max(1) as f32,
    );
    let scale = (e.shutter / light.long_s.max(1e-9)) as f32;
    let band_colour = [ramp(0.0), ramp(0.18), ramp(0.38), ramp(0.72), palette.warn];
    let mut top = 0.0f32;
    for t in 0..map.cols * map.rows {
        if !light.subject.get(t).copied().unwrap_or(false) {
            continue;
        }
        let (tx, ty) = (t % map.cols, t / map.cols);
        let a = to_screen(tx as f32 * tw, ty as f32 * th);
        let b = to_screen((tx + 1) as f32 * tw, (ty + 1) as f32 * th);
        let r = Rect::from_min_max(a, b).shrink(0.5);
        tally.tiles += 1;
        if lens == Lens::Light {
            let v = light.level[t] * scale;
            let band = LIGHT_BANDS.iter().take_while(|cut| v >= **cut).count();
            tally.bands[band] += 1;
            if r.width() > 0.0 && r.intersects(photo) {
                mesh.add_colored_rect(
                    r.intersect(photo),
                    band_colour[band].gamma_multiply(LENS_ALPHA),
                );
            }
            continue;
        }
        let g = light.glint[t] * scale;
        // Also skips NaN.
        if g.is_nan() || g <= 1.0 {
            continue;
        }
        tally.over += 1;
        let stops = g.log2();
        top = top.max(stops);
        let held = e
            .groups
            .is_some_and(|s| light.glint[t] * (s / light.long_s.max(1e-9)) as f32 <= 0.9);
        if r.width() <= 0.0 || !r.intersects(photo) {
            continue;
        }
        let c = ramp(0.62 + 0.38 * (stops / 6.0).min(1.0));
        if held {
            tally.held += 1;
            // Outlined: the groups hold it. A ring of four thin quads.
            let r = r.intersect(photo);
            let w = 1.5f32.min(r.width() / 3.0);
            for side in [
                Rect::from_min_max(r.min, egui::pos2(r.right(), r.top() + w)),
                Rect::from_min_max(egui::pos2(r.left(), r.bottom() - w), r.max),
                Rect::from_min_max(r.min, egui::pos2(r.left() + w, r.bottom())),
                Rect::from_min_max(egui::pos2(r.right() - w, r.top()), r.max),
            ] {
                mesh.add_colored_rect(side, c.gamma_multiply(0.9));
            }
        } else {
            mesh.add_colored_rect(r.intersect(photo), c.gamma_multiply(LENS_ALPHA));
        }
    }
    tally.top_centistops = (top * 100.0).round() as i32;
}

/// The Still lens's tiles: under the limit faint, by how near it; over it
/// in the warning colour (counted in `tally.over`, measured in `tiles`).
fn still_mesh(
    mesh: &mut Mesh,
    tally: &mut Cover,
    still: &StillMap,
    photo: Rect,
    uv: Rect,
    palette: &CapturePalette,
) {
    let to_screen = |u: f32, v: f32| {
        egui::pos2(
            photo.left() + (u - uv.left()) / uv.width() * photo.width(),
            photo.top() + (v - uv.top()) / uv.height() * photo.height(),
        )
    };
    let (tw, th) = (
        still.extent[0] / still.cols.max(1) as f32,
        still.extent[1] / still.rows.max(1) as f32,
    );
    let mut values = Vec::new();
    for (t, &v) in still.local.iter().enumerate() {
        if !v.is_finite() {
            continue;
        }
        values.push(v);
        tally.tiles += 1;
        let (tx, ty) = (t % still.cols, t / still.cols);
        let r = Rect::from_min_max(
            to_screen(tx as f32 * tw, ty as f32 * th),
            to_screen((tx + 1) as f32 * tw, (ty + 1) as f32 * th),
        )
        .shrink(0.5);
        if !(r.width() > 0.0 && r.intersects(photo)) {
            continue;
        }
        let c = if v > still.limit {
            tally.over += 1;
            palette.warn.gamma_multiply(LENS_ALPHA)
        } else {
            ramp(0.35).gamma_multiply(0.15 + 0.45 * (v / still.limit.max(1e-6)).clamp(0.0, 1.0))
        };
        mesh.add_colored_rect(r.intersect(photo), c);
    }
    values.sort_by(f32::total_cmp);
    tally.top_centistops = values
        .get(((values.len().max(1) - 1) as f32 * 0.99) as usize)
        .map_or(0, |v| (v * 100.0).round() as i32);
}

/// The Still lens's legend.
fn still_legend(
    p: &egui::Painter,
    photo: Rect,
    still: &StillMap,
    t: Cover,
    palette: &CapturePalette,
) {
    let origin = photo.left_bottom() + egui::vec2(10.0, -98.0);
    let line = format!(
        "{}: 99th percentile {:.2} px against the retake limit {:.2}; {} of {} tiles over it",
        still.verdict,
        f64::from(t.top_centistops) / 100.0,
        still.limit,
        t.over,
        t.tiles
    );
    let job = style::job(&line, 12.0, palette.ink, 0.0);
    let galley = p.layout_job(job);
    let box_ = Rect::from_min_size(origin, egui::vec2(galley.size().x.max(200.0) + 16.0, 50.0));
    p.rect_filled(box_, 0.0, palette.panel.gamma_multiply(0.92));
    p.rect_stroke(
        box_,
        0.0,
        Stroke::new(1.0_f32, palette.line),
        StrokeKind::Inside,
    );
    style::paint_job(
        p,
        origin + egui::vec2(8.0, 4.0),
        Align2::LEFT_TOP,
        style::job(
            "STILL \u{b7} the proof plane's four shots against each other",
            11.0,
            palette.ink2,
            0.0,
        ),
    );
    p.galley(origin + egui::vec2(8.0, 24.0), galley, palette.ink);
}

/// The Light and Glints lenses' legend.
fn light_legend(
    p: &egui::Painter,
    photo: Rect,
    lens: Lens,
    t: Cover,
    e: Option<LensExposure>,
    palette: &CapturePalette,
) {
    let origin = photo.left_bottom() + egui::vec2(10.0, -98.0);
    let pct = |n: usize| 100.0 * n as f64 / t.tiles.max(1) as f64;
    let (title, line) = match (lens, e) {
        (Lens::Light, Some(e)) => (
            format!("LIGHT \u{b7} the body at {}", seconds_label(e.shutter)),
            format!(
                "under 1 % {:.0} \u{b7} 1\u{2013}10 % {:.0} \u{b7} 10\u{2013}50 % {:.0} \u{b7} 50\u{2013}90 % {:.0} \u{b7} pinned {:.0} (% of the subject)",
                pct(t.bands[0]),
                pct(t.bands[1]),
                pct(t.bands[2]),
                pct(t.bands[3]),
                pct(t.bands[4])
            ),
        ),
        (_, Some(e)) => (
            format!("GLINTS \u{b7} past the pin at {}", seconds_label(e.shutter)),
            if t.over == 0 {
                "No highlight passes the pin".to_owned()
            } else {
                format!(
                    "{:.1} % of the subject, up to {:.1} stops over; {}",
                    pct(t.over),
                    f64::from(t.top_centistops) / 100.0,
                    match e.groups {
                        Some(g) if t.held == t.over =>
                            format!("held by groups at {}", seconds_label(g)),
                        Some(g) => format!(
                            "{} of {} held by groups at {}",
                            t.held,
                            t.over,
                            seconds_label(g)
                        ),
                        None => "no highlight groups: they pin".to_owned(),
                    }
                )
            },
        ),
        _ => ("LIGHT".to_owned(), "The exposure is not known".to_owned()),
    };
    let job = style::job(&line, 12.0, palette.ink, 0.0);
    let galley = p.layout_job(job);
    let box_ = Rect::from_min_size(origin, egui::vec2(galley.size().x.max(200.0) + 16.0, 50.0));
    p.rect_filled(box_, 0.0, palette.panel.gamma_multiply(0.92));
    p.rect_stroke(
        box_,
        0.0,
        Stroke::new(1.0_f32, palette.line),
        StrokeKind::Inside,
    );
    style::paint_job(
        p,
        origin + egui::vec2(8.0, 4.0),
        Align2::LEFT_TOP,
        style::job(&title, 11.0, palette.ink2, 0.0),
    );
    p.galley(origin + egui::vec2(8.0, 24.0), galley, palette.ink);
}

/// "1.3 s" or "1/40 s".
fn seconds_label(s: f64) -> String {
    if s >= 0.3 {
        format!("{s:.1} s")
    } else {
        format!("1/{:.0} s", 1.0 / s)
    }
}

/// The Cover lens's legend: what the plan leaves out, in words.
fn cover_legend(
    p: &egui::Painter,
    photo: Rect,
    cover: Cover,
    marks: Option<(u16, u16)>,
    palette: &CapturePalette,
) {
    let origin = photo.left_bottom() + egui::vec2(10.0, -98.0);
    let pct = |n: usize| 100.0 * n as f64 / cover.tiles.max(1) as f64;
    let line = match marks {
        None => "Mark Start and End to see what they cover".to_owned(),
        Some(_) if cover.before + cover.after == 0 => "All of the subject is covered".to_owned(),
        Some(_) => {
            let mut parts = Vec::new();
            if cover.before > 0 {
                parts.push(format!(
                    "{} tiles ({:.1} %) lie before Start",
                    cover.before,
                    pct(cover.before)
                ));
            }
            if cover.after > 0 {
                parts.push(format!(
                    "{} tiles ({:.1} %) lie after End",
                    cover.after,
                    pct(cover.after)
                ));
            }
            parts.join("; ")
        }
    };
    let job = style::job(&line, 12.0, palette.ink, 0.0);
    let galley = p.layout_job(job);
    let box_ = Rect::from_min_size(origin, egui::vec2(galley.size().x.max(200.0) + 16.0, 50.0));
    p.rect_filled(box_, 0.0, palette.panel.gamma_multiply(0.92));
    p.rect_stroke(
        box_,
        0.0,
        Stroke::new(1.0_f32, palette.line),
        StrokeKind::Inside,
    );
    style::paint_job(
        p,
        origin + egui::vec2(8.0, 4.0),
        Align2::LEFT_TOP,
        style::job(
            "COVER \u{b7} against Start and End",
            11.0,
            palette.ink2,
            0.0,
        ),
    );
    p.galley(origin + egui::vec2(8.0, 24.0), galley, palette.ink);
}

/// The Depth lens's legend, ruled, at the bottom left above the tool bar:
/// the ramp, its ends, the lens position on it, and where the map came from.
fn depth_legend(
    p: &egui::Painter,
    photo: Rect,
    map: &DepthMap,
    at: Option<u16>,
    palette: &CapturePalette,
) {
    let w = 220.0;
    let origin = photo.left_bottom() + egui::vec2(10.0, -98.0);
    let box_ = Rect::from_min_size(origin, egui::vec2(w + 16.0, 50.0));
    p.rect_filled(box_, 0.0, palette.panel.gamma_multiply(0.92));
    p.rect_stroke(
        box_,
        0.0,
        Stroke::new(1.0_f32, palette.line),
        StrokeKind::Inside,
    );
    let bar = Rect::from_min_size(origin + egui::vec2(8.0, 20.0), egui::vec2(w, 8.0));
    let steps = 44;
    for i in 0..steps {
        let x0 = bar.left() + bar.width() * i as f32 / steps as f32;
        let x1 = bar.left() + bar.width() * (i + 1) as f32 / steps as f32;
        p.rect_filled(
            Rect::from_min_max(egui::pos2(x0, bar.top()), egui::pos2(x1, bar.bottom())),
            0.0,
            ramp((i as f32 + 0.5) / steps as f32),
        );
    }
    let text = |pos: Pos2, align: Align2, s: &str, c: Color32| {
        style::paint_job(p, pos, align, style::job(s, 11.0, c, 0.0));
    };
    text(
        origin + egui::vec2(8.0, 4.0),
        Align2::LEFT_TOP,
        &format!("DEPTH \u{b7} {}", map.source),
        palette.ink2,
    );
    text(
        bar.left_bottom() + egui::vec2(0.0, 3.0),
        Align2::LEFT_TOP,
        &style::focus_units(map.lo.round() as u16),
        palette.ink3,
    );
    text(
        bar.right_bottom() + egui::vec2(0.0, 3.0),
        Align2::RIGHT_TOP,
        &style::focus_units(map.hi.round() as u16),
        palette.ink3,
    );
    if let Some(at) = at {
        let f = ((f64::from(at) - map.lo) / (map.hi - map.lo).max(1.0)) as f32;
        if (0.0..=1.0).contains(&f) {
            let x = bar.left() + bar.width() * f;
            p.line_segment(
                [
                    egui::pos2(x, bar.top() - 3.0),
                    egui::pos2(x, bar.bottom() + 3.0),
                ],
                Stroke::new(1.5_f32, palette.ink),
            );
        }
    }
}

/// The preview's rectangle in a canvas: its aspect, the canvas height less
/// 38 px, centred with 10 px below (the mockup's `.canvas.center > .photo`).
pub(crate) fn photo_rect(canvas: Rect, aspect: f32) -> Rect {
    let h = (canvas.height() - 38.0).max(40.0);
    let w = (h * aspect).min(canvas.width() - 24.0).max(40.0);
    let h = w / aspect;
    Rect::from_center_size(
        egui::pos2(canvas.center().x, canvas.center().y - 5.0),
        egui::vec2(w, h),
    )
}

impl LiveView {
    /// Uploads the preview (and its overlays) when its generation changed.
    pub(crate) fn sync_textures(
        &mut self,
        ctx: &egui::Context,
        s: &Snapshot,
        palette: &CapturePalette,
    ) {
        if let Some((generation, image)) = &s.preview
            && self.preview.as_ref().is_none_or(|(g, _)| g != generation)
        {
            let image = image.as_ref().clone();
            match &mut self.preview {
                Some((g, t)) => {
                    t.set(image, TextureOptions::LINEAR);
                    *g = *generation;
                }
                None => {
                    self.preview = Some((
                        *generation,
                        ctx.load_texture("capture-live", image, TextureOptions::LINEAR),
                    ))
                }
            }
            self.uploads += 1;
        }
        if self.peaking
            && let Some((generation, peaks)) = &s.peaking
            && self
                .peaks
                .as_ref()
                .is_none_or(|(g, t, _)| g != generation || *t != self.threshold)
        {
            let image = peaks.overlay(self.threshold);
            match &mut self.peaks {
                Some((g, t, tex)) => {
                    tex.set(image, TextureOptions::NEAREST);
                    *g = *generation;
                    *t = self.threshold;
                }
                None => {
                    self.peaks = Some((
                        *generation,
                        self.threshold,
                        ctx.load_texture("capture-live-peaking", image, TextureOptions::NEAREST),
                    ))
                }
            }
            self.uploads += 1;
        }
        if self.clipping
            && let Some((generation, levels)) = &s.levels
            && self.clip.as_ref().is_none_or(|(g, _)| g != generation)
        {
            let image = levels.clip_overlay(palette.warn.gamma_multiply(0.85));
            match &mut self.clip {
                Some((g, tex)) => {
                    tex.set(image, TextureOptions::NEAREST);
                    *g = *generation;
                }
                None => {
                    self.clip = Some((
                        *generation,
                        ctx.load_texture("capture-live-clip", image, TextureOptions::NEAREST),
                    ))
                }
            }
            self.uploads += 1;
        }
    }

    /// The subject box to draw: a box sent and not yet reported by the host
    /// (for at most three seconds), else the host's.
    fn current_roi(&mut self, host: Option<Roi>, now: f64) -> Roi {
        let host = host.unwrap_or_else(Roi::subject);
        match self.sent {
            Some((roi, at)) if now - at < 3.0 && !same_roi(roi, host) => roi,
            _ => {
                self.sent = None;
                host
            }
        }
    }

    /// Draws the live view into the canvas `ui` gives it.
    pub fn show(&mut self, ui: &mut Ui, s: &Snapshot, palette: &CapturePalette) -> Vec<LiveIntent> {
        let mut out = Vec::new();
        let canvas = ui.max_rect();
        ui.painter().rect_filled(canvas, 0.0, palette.surround);
        self.sync_textures(ui.ctx(), s, palette);
        let host = &s.host;
        let now = ui.input(|i| i.time);
        let aspect = self
            .preview
            .as_ref()
            .map(|(_, t)| t.size_vec2())
            .filter(|v| v.y > 0.0)
            .map_or(1.5, |v| v.x / v.y);
        let photo = photo_rect(canvas, aspect);
        let p = ui.painter_at(canvas);
        p.rect_filled(photo, 0.0, Color32::BLACK);
        let roi = self.current_roi(host.roi, now);
        // The focus reading follows the box the host measures with.
        self.trace
            .observe(s, host.roi.unwrap_or_else(Roi::subject), now);
        // 100 %: one preview pixel a point, around the subject box.
        let uv = match (&self.preview, self.actual_size) {
            (Some((_, t)), true) => {
                let size = t.size_vec2();
                let w = (photo.width() / size.x).min(1.0);
                let h = (photo.height() / size.y).min(1.0);
                let cx = (roi.x + roi.width / 2.0).clamp(w / 2.0, 1.0 - w / 2.0);
                let cy = (roi.y + roi.height / 2.0).clamp(h / 2.0, 1.0 - h / 2.0);
                Rect::from_center_size(egui::pos2(cx, cy), egui::vec2(w, h))
            }
            _ => Rect::from_min_max(egui::Pos2::ZERO, egui::pos2(1.0, 1.0)),
        };
        let fresh = host.preview.fresh;
        if let Some((generation, t)) = &self.preview {
            p.image(t.id(), photo, uv, Color32::WHITE);
            if self.peaking
                && fresh
                && let Some((g, _, peaks)) = &self.peaks
                && g == generation
            {
                p.image(peaks.id(), photo, uv, Color32::WHITE);
            }
            if self.clipping
                && let Some((g, clip)) = &self.clip
                && g == generation
            {
                p.image(clip.id(), photo, uv, Color32::WHITE);
            }
        } else {
            style::paint_job(
                &p,
                photo.center(),
                Align2::CENTER_CENTER,
                style::job("The live view appears here", 13.0, palette.ink3, 0.0),
            );
        }
        p.rect_stroke(
            photo,
            0.0,
            Stroke::new(1.0_f32, Color32::from_white_alpha(13)),
            StrokeKind::Outside,
        );
        if self.lens != Lens::Off
            && let Some(map) = &self.depth
        {
            // In focus now: the lens within half a sharp depth of a tile's
            // focus (spec 6.2). A comparison per tile when the lens moves.
            let at = self
                .rail_hover
                .or(host.position.filter(|p| map.anchor != Some(*p)))
                .filter(|_| self.lens == Lens::Depth);
            let marks = (self.lens == Lens::Cover && host.bounds_set()).then(|| host.plan_bounds());
            let shutter = host.exposure.as_ref().and_then(|e| e.shutter);
            let groups = host
                .plan
                .as_ref()
                .and_then(|p| p.highlight)
                .map(|h| h.shutter);
            let exposure = shutter
                .and_then(strehl_capture::timing::shutter_seconds)
                .map(|s| LensExposure {
                    shutter: s,
                    groups: groups.and_then(strehl_capture::timing::shutter_seconds),
                });
            let key: LensKey = (
                self.lens,
                map.revision,
                rect_bits(photo),
                rect_bits(uv),
                at,
                marks,
                [shutter.unwrap_or(0), groups.unwrap_or(0)],
            );
            if self.lens_mesh.as_ref().is_none_or(|(k, _, _)| *k != key) {
                let (mesh, cover) =
                    lens_mesh(self.lens, map, photo, uv, at, marks, exposure, palette);
                self.lens_mesh = Some((key, Arc::new(mesh), cover));
                self.mesh_builds += 1;
            }
            if let Some((_, mesh, cover)) = &self.lens_mesh {
                p.add(egui::Shape::mesh(Arc::clone(mesh)));
                match self.lens {
                    Lens::Cover => cover_legend(&p, photo, *cover, marks, palette),
                    Lens::Light | Lens::Glints => {
                        light_legend(&p, photo, self.lens, *cover, exposure, palette)
                    }
                    Lens::Still => {
                        if let Some(still) = &map.still {
                            still_legend(&p, photo, still, *cover, palette);
                        }
                    }
                    _ => depth_legend(&p, photo, map, host.position, palette),
                }
            }
            // Hover a tile: where it is in focus.
            if let Some(pos) = ui.ctx().pointer_hover_pos().filter(|q| photo.contains(*q)) {
                let fx = uv.left() + (pos.x - photo.left()) / photo.width() * uv.width();
                let fy = uv.top() + (pos.y - photo.top()) / photo.height() * uv.height();
                let (tx, ty) = (
                    (fx / map.extent[0] * map.cols as f32).floor(),
                    (fy / map.extent[1] * map.rows as f32).floor(),
                );
                if tx >= 0.0 && ty >= 0.0 && (tx as usize) < map.cols && (ty as usize) < map.rows {
                    let text = match map.focus[ty as usize * map.cols + tx as usize] {
                        Some(f) => format!("in focus at {}", style::focus_units(f.round() as u16)),
                        None => "no peak here".into(),
                    };
                    let job = style::job(&text, 12.0, palette.ink, 0.0);
                    let galley = ui.fonts_mut(|f| f.layout_job(job));
                    let r = Rect::from_min_size(
                        pos + egui::vec2(14.0, 10.0),
                        galley.size() + egui::vec2(12.0, 6.0),
                    );
                    p.rect_filled(r, 0.0, palette.panel);
                    p.rect_stroke(
                        r,
                        0.0,
                        Stroke::new(1.0_f32, palette.line),
                        StrokeKind::Inside,
                    );
                    p.galley(r.min + egui::vec2(6.0, 3.0), galley, palette.ink);
                }
            }
        }
        if self.grid {
            for i in 1..3 {
                let f = i as f32 / 3.0;
                let x = photo.left() + photo.width() * f;
                let y = photo.top() + photo.height() * f;
                p.line_segment(
                    [egui::pos2(x, photo.top()), egui::pos2(x, photo.bottom())],
                    Stroke::new(1.0_f32, Color32::from_white_alpha(40)),
                );
                p.line_segment(
                    [egui::pos2(photo.left(), y), egui::pos2(photo.right(), y)],
                    Stroke::new(1.0_f32, Color32::from_white_alpha(40)),
                );
            }
        }
        // The subject box: its handles resize it, inside moves it, outside
        // draws a new one. The picture's hit area reaches the handles on
        // its border.
        let response = ui.interact(
            photo.expand(HANDLE_REACH),
            ui.id().with("capture-live-photo"),
            Sense::click_and_drag(),
        );
        let editable = s.fresh() && host.editable && !s.pending;
        let to_uv = |pos: Pos2| {
            let fx = ((pos.x - photo.left()) / photo.width()).clamp(0.0, 1.0);
            let fy = ((pos.y - photo.top()) / photo.height()).clamp(0.0, 1.0);
            egui::pos2(uv.left() + fx * uv.width(), uv.top() + fy * uv.height())
        };
        let to_screen = |u: Pos2| {
            egui::pos2(
                photo.left() + (u.x - uv.left()) / uv.width() * photo.width(),
                photo.top() + (u.y - uv.top()) / uv.height() * photo.height(),
            )
        };
        // A pointer move on the screen as a move in preview fractions.
        let to_delta = |d: Vec2| {
            egui::vec2(
                d.x / photo.width() * uv.width(),
                d.y / photo.height() * uv.height(),
            )
        };
        let mut roi = roi;
        let box_uv = roi_rect(roi);
        let mut box_screen = Rect::from_min_max(to_screen(box_uv.min), to_screen(box_uv.max));
        let host_subject = host.plan.as_ref().and_then(|plan| plan.subject.as_ref());
        if self
            .outline_sent
            .as_ref()
            .is_some_and(|sent| same_rings(sent, &outline_rings(host_subject)))
        {
            self.outline_sent = None;
        }
        if host_subject.is_some() && !self.outline_chosen {
            self.outline = true;
            self.subject_box = true;
        }
        if self.outline {
            self.auto_panel(ui, photo, palette, &mut out);
            self.outline_ui(
                ui,
                &p,
                &response,
                host_subject,
                host.position,
                self.subject_box && editable,
                &to_uv,
                &to_screen,
                palette,
                &mut out,
            );
        }
        let can_edit = self.subject_box && editable && !self.outline;
        if can_edit {
            if response.drag_started()
                && let Some(press) = ui.input(|i| i.pointer.press_origin())
            {
                self.drag = Some(match box_hit(box_screen, press) {
                    BoxHit::Handle(handle) => BoxDrag::Resize {
                        from: box_uv,
                        handle,
                        press,
                    },
                    BoxHit::Inside => BoxDrag::Move {
                        from: box_uv,
                        press,
                    },
                    BoxHit::Outside => BoxDrag::Draw(to_uv(press)),
                });
            }
        } else {
            self.drag = None;
        }
        let pointer = response.interact_pointer_pos();
        let dragged = match (self.drag, pointer) {
            (Some(BoxDrag::Draw(a)), Some(b)) => Some(Rect::from_two_pos(a, to_uv(b))),
            (Some(BoxDrag::Move { from, press }), Some(b)) => {
                Some(moved(from, to_delta(b - press)))
            }
            (
                Some(BoxDrag::Resize {
                    from,
                    handle,
                    press,
                }),
                Some(b),
            ) => Some(resized(from, handle, to_delta(b - press), MIN_BOX)),
            _ => None,
        };
        if response.drag_stopped()
            && self.drag.take().is_some()
            && let Some(r) = dragged
        {
            let next = rect_roi(r);
            let big_enough = next.width >= MIN_BOX && next.height >= MIN_BOX;
            if big_enough && !same_roi(next, roi) && next.valid() {
                out.push(LiveIntent::SetRoi(next));
                self.sent = Some((next, now));
                roi = next;
                box_screen = Rect::from_min_max(to_screen(r.min), to_screen(r.max));
            }
        }
        // The pointer's cursor: the handle's resize, move inside, a cross
        // to draw outside.
        if can_edit {
            let cursor = match (self.drag, response.hover_pos()) {
                (Some(BoxDrag::Resize { handle, .. }), _) => Some(handle.cursor()),
                (Some(BoxDrag::Move { .. }), _) => Some(CursorIcon::Grabbing),
                (Some(BoxDrag::Draw(_)), _) => Some(CursorIcon::Crosshair),
                (None, Some(pos)) => Some(match box_hit(box_screen, pos) {
                    BoxHit::Handle(h) => h.cursor(),
                    BoxHit::Inside => CursorIcon::Grab,
                    BoxHit::Outside => CursorIcon::Crosshair,
                }),
                (None, None) => None,
            };
            if let Some(cursor) = cursor
                && (self.drag.is_some() || response.hovered())
            {
                ui.ctx().set_cursor_icon(cursor);
            }
        }
        if self.subject_box && !self.outline {
            let (shown, active) = match dragged.filter(|_| self.drag.is_some()) {
                Some(r) => (
                    Rect::from_min_max(to_screen(r.min), to_screen(r.max)),
                    match self.drag {
                        Some(BoxDrag::Resize { handle, .. }) => Some(handle),
                        _ => None,
                    },
                ),
                None => (box_screen, None),
            };
            let hovered = match (self.drag, response.hover_pos()) {
                (None, Some(pos)) if can_edit => match box_hit(box_screen, pos) {
                    BoxHit::Handle(h) => Some(h),
                    _ => None,
                },
                _ => active,
            };
            let caption = match dragged.filter(|_| self.drag.is_some()) {
                Some(r) => format!(
                    "Subject box · {:.0} × {:.0} % of the frame",
                    100.0 * r.width(),
                    100.0 * r.height()
                ),
                None => "Subject box · used by the survey and the magnifier".to_owned(),
            };
            let ppp = ui.ctx().pixels_per_point();
            subject_box(&p, shown, &caption, can_edit, hovered, ppp);
        }
        // The state at the top left.
        let state = match host.preview.age_seconds {
            Some(age) if fresh => format!("Live · preview {age:.1} s old"),
            Some(age) => format!("Last preview · {age:.0} s old"),
            None => "No preview".into(),
        };
        let galley = p.layout_job(style::job(&state, 11.5, palette.ink2, 0.0));
        let tag = Rect::from_min_size(
            photo.left_top() + egui::vec2(10.0, 10.0),
            egui::vec2(galley.size().x + 35.0, 26.0),
        );
        glass(&p, tag, palette);
        style::mark(
            &p,
            egui::pos2(tag.left() + 13.5, tag.center().y),
            if fresh { Mark::Ok } else { Mark::Idle },
            7.0,
            palette,
        );
        p.galley(
            egui::pos2(tag.left() + 25.0, tag.center().y - galley.size().y / 2.0),
            galley,
            palette.ink2,
        );
        self.bar(ui, photo, s, roi, palette, &mut out);
        self.estimate(ui, photo, s, now, palette);
        out
    }

    /// The tool bar at the bottom left (`.lvbar`).
    fn bar(
        &mut self,
        ui: &mut Ui,
        photo: Rect,
        s: &Snapshot,
        roi: Roi,
        palette: &CapturePalette,
        out: &mut Vec<LiveIntent>,
    ) {
        // The box is drawn behind the buttons once they are laid out, as wide
        // as they are (owner, 2026-11-24: "Magnifier" hung over its end).
        let at = photo.left_bottom() + egui::vec2(10.0, -10.0);
        let room = Rect::from_min_size(
            egui::pos2(at.x, at.y - 34.0),
            egui::vec2((photo.width() - 20.0).max(120.0), 34.0),
        );
        let outline_rings_now = self.outline_sent.clone().unwrap_or_else(|| {
            outline_rings(s.host.plan.as_ref().and_then(|p| p.subject.as_ref()))
        });
        let editable = s.fresh() && s.host.editable && !s.pending;
        let backdrop = ui.painter().add(egui::Shape::Noop);
        let used = ui.scope_builder(
            egui::UiBuilder::new()
                .max_rect(room.shrink2(egui::vec2(8.0, 5.0)))
                .layout(egui::Layout::left_to_right(egui::Align::Center)),
            |ui| {
                ui.spacing_mut().item_spacing.x = 4.0;
                for (label, actual) in [("Fit", false), ("100%", true)] {
                    let kind = if self.actual_size == actual { ButtonKind::On } else { ButtonKind::Quiet };
                    if style::button(ui, label, kind, 24.0, true, palette).clicked() {
                        self.actual_size = actual;
                    }
                }
                ui.add_space(6.0);
                if self.depth.is_some() {
                    for (label, lens, tip) in [
                        ("Depth", Lens::Depth, "The Depth lens: where each part of the subject is in focus, near to far, from the calibration; tiles with no peak are left clear. Once the lens moves, tiles out of focus at its position are dimmed"),
                        ("Cover", Lens::Cover, "The Cover lens: against Start and End as they stand, the parts of the subject in focus only before Start or after End, counted"),
                        ("Light", Lens::Light, "The Light lens: the body's level at the chosen exposure, by tile, in five bands (from the survey's long frames)"),
                        ("Glints", Lens::Glints, "The Glints lens: highlights past the pin at the chosen exposure, by how many stops; outlined where the highlight groups hold them (from the survey's short frames)"),
                        ("Still", Lens::Still, "The Still lens: how far the proof plane's four shots disagree, by tile, against the capture's retake limit"),
                    ] {
                        if lens == Lens::Still && self.depth.as_ref().is_none_or(|m| m.still.is_none()) {
                            continue;
                        }
                        if matches!(lens, Lens::Light | Lens::Glints)
                            && self.depth.as_ref().is_none_or(|m| m.light.is_none())
                        {
                            continue;
                        }
                        let on = self.lens == lens;
                        if style::button(ui, label, if on { ButtonKind::On } else { ButtonKind::Quiet }, 22.0, true, palette)
                            .on_hover_text(tip)
                            .clicked()
                        {
                            self.lens = if on { Lens::Off } else { lens };
                        }
                    }
                }
                if style::button(ui, "Peaking", if self.peaking { ButtonKind::On } else { ButtonKind::Quiet }, 22.0, true, palette).clicked() {
                    self.peaking = !self.peaking;
                }
                let mut t = f32::from(self.threshold);
                ui.scope(|ui| {
                    ui.spacing_mut().slider_width = 70.0;
                    if ui
                        .add_enabled(self.peaking, egui::Slider::new(&mut t, 6.0..=40.0).show_value(false))
                        .on_hover_text("Peaking threshold: higher marks fewer, stronger edges")
                        .changed()
                    {
                        self.threshold = t.round() as u8;
                    }
                });
                if style::button(ui, "Auto", if self.auto.running { ButtonKind::On } else { ButtonKind::Quiet }, 22.0, self.auto.frames >= 5 && !self.auto.running, palette)
                    .on_hover_text(if self.auto.frames >= 5 {
                        format!("Find the subject in the {} live frames of the last survey", self.auto.frames)
                    } else {
                        "Survey first (Survey again on the depth rail): Auto reads the live frames it shows as it sweeps focus. Calibrate step also outlines the subject, from its RAWs".into()
                    })
                    .clicked()
                {
                    self.outline = true;
                    self.subject_box = true;
                    self.outline_chosen = true;
                    out.push(LiveIntent::AutoSubject);
                }
                if self.outline
                    && style::button(
                        ui,
                        "Clear",
                        ButtonKind::Quiet,
                        22.0,
                        editable && !self.auto.running && !outline_rings_now.is_empty(),
                        palette,
                    )
                    .on_hover_text("Remove the outline (and the automatic selection)")
                    .clicked()
                {
                    self.outline_sent = Some(Vec::new());
                    self.outline_edit = OutlineEdit::None;
                    self.auto_draft = None;
                    out.push(LiveIntent::ClearOutline);
                }
                for (label, flag) in [("Clipping", 0), ("Grid", 1), ("Subject box", 2), ("Outline", 3)] {
                    let on = match flag {
                        0 => self.clipping,
                        1 => self.grid,
                        2 => self.subject_box && !self.outline,
                        _ => self.subject_box && self.outline,
                    };
                    if style::button(ui, label, if on { ButtonKind::On } else { ButtonKind::Quiet }, 22.0, true, palette).clicked() {
                        if flag >= 2 {
                            self.outline_chosen = true;
                        }
                        match flag {
                            0 => self.clipping = !on,
                            1 => self.grid = !on,
                            2 => {
                                self.subject_box = !on;
                                self.outline = false;
                            }
                            _ => {
                                self.subject_box = true;
                                self.outline = !on;
                                self.outline_edit = OutlineEdit::None;
                            }
                        }
                    }
                }
                let ratios = &s.host.magnifier_ratios;
                if !ratios.is_empty() {
                    let current = s.host.magnifier_current.unwrap_or(0) as u32;
                    let label = if current == 0 {
                        "Magnifier".to_owned()
                    } else {
                        format!("Magnifier {}×", trim(current as f32 / 10.0))
                    };
                    if style::button(ui, &label, if current == 0 { ButtonKind::Quiet } else { ButtonKind::On }, 22.0, editable, palette)
                        .on_hover_text("The camera's magnifier, centred on the subject box; click for the next ratio")
                        .clicked()
                    {
                        let next = ratios.iter().copied().find(|r| *r > current).unwrap_or(0);
                        out.push(LiveIntent::Magnify {
                            ratio: next,
                            x: ((roi.x + roi.width / 2.0) * 639.0).round() as u16,
                            y: ((roi.y + roi.height / 2.0) * 479.0).round() as u16,
                        });
                    }
                }
            },
        )
        .response
        .rect;
        let rect = Rect::from_min_max(room.min, egui::pos2(used.right() + 8.0, room.bottom()));
        ui.painter().set(backdrop, glass_shape(rect, palette));
        self.bar_width = rect.width();
    }

    /// The estimate panel at the bottom right (`.expo`): the histograms
    /// with the black and clipped shares at their ends, the focus in the
    /// subject box and its trace, the exposure and the preview rate.
    fn estimate(
        &mut self,
        ui: &mut Ui,
        photo: Rect,
        s: &Snapshot,
        now: f64,
        palette: &CapturePalette,
    ) {
        // Above the tool bar when the picture is too narrow for both.
        let lift = if photo.width() < self.bar_width + PANEL.x + 30.0 {
            34.0 + 8.0
        } else {
            0.0
        };
        let rect = Rect::from_min_size(
            photo.right_bottom() + egui::vec2(-10.0 - PANEL.x, -10.0 - lift - PANEL.y),
            PANEL,
        );
        // Presses on the panel do not draw a subject box under it.
        ui.interact(
            rect,
            ui.id().with("capture-live-estimate"),
            Sense::click_and_drag(),
        );
        let ppp = ui.ctx().pixels_per_point();
        let p = ui.painter();
        glass(p, rect, palette);
        let inner = rect.shrink2(egui::vec2(12.0, 10.0));
        let text = |pos: Pos2, anchor: Align2, s: &str, size: f32, color: Color32| {
            style::paint_job(p, pos, anchor, style::job(s, size, color, 0.0))
        };
        let caps = |pos: Pos2, anchor: Align2, s: &str| {
            style::paint_job(p, pos, anchor, style::caps_job(s, 10.5, palette.ink3))
        };
        caps(inner.left_top(), Align2::LEFT_TOP, "Live view");
        text(
            inner.right_top(),
            Align2::RIGHT_TOP,
            PreviewLevels::CAUTION_SHORT,
            12.0,
            palette.ink3,
        );
        // The histograms.
        let hist = Rect::from_min_size(
            egui::pos2(inner.left(), inner.top() + 19.0),
            egui::vec2(inner.width(), 48.0),
        );
        let ends = inner.top() + 70.0;
        if let Some((generation, levels)) = &s.levels {
            let key = (*generation, rect_bits(hist), ppp.to_bits());
            if self.histogram.as_ref().is_none_or(|(k, _)| *k != key) {
                self.histogram = Some((key, Arc::new(histogram_mesh(levels, hist, ppp, palette))));
                self.mesh_builds += 1;
            }
            if let Some((_, mesh)) = &self.histogram {
                p.add(Shape::mesh(mesh.clone()));
            }
            let black = 100.0 * levels.black_share;
            text(
                egui::pos2(hist.left(), ends),
                Align2::LEFT_TOP,
                &format!("{} % black", share_text(black)),
                11.5,
                palette.ink3,
            );
            let clipped = 100.0 * levels.clipped_share;
            text(
                egui::pos2(hist.right(), ends),
                Align2::RIGHT_TOP,
                &format!("{clipped:.1} % clipped"),
                11.5,
                if clipped > 0.05 {
                    palette.warn
                } else {
                    palette.ok
                },
            );
        } else {
            text(
                hist.center(),
                Align2::CENTER_CENTER,
                "no preview yet",
                11.5,
                palette.ink3,
            );
        }
        let rule = |y: f32| {
            style::hairline(
                p,
                egui::pos2(inner.left(), y),
                egui::pos2(inner.right(), y),
                palette.line2,
            );
        };
        // The focus in the subject box, and its trace.
        rule(inner.top() + 90.5);
        let head = inner.top() + 97.0;
        caps(
            egui::pos2(inner.left(), head),
            Align2::LEFT_TOP,
            "Focus · subject box",
        );
        let trace = Rect::from_min_size(
            egui::pos2(inner.left(), inner.top() + 114.0),
            egui::vec2(inner.width(), 22.0),
        );
        let key = (self.trace.revision, rect_bits(trace), ppp.to_bits());
        if self.trace_mesh.as_ref().is_none_or(|(k, _)| *k != key) {
            self.trace_mesh = Some((key, Arc::new(trace_mesh(&self.trace, trace, ppp, palette))));
            self.mesh_builds += 1;
        }
        if let Some((_, mesh)) = &self.trace_mesh {
            p.add(Shape::mesh(mesh.clone()));
        }
        let below = inner.top() + 139.0;
        match (self.trace.share_of_best(), self.trace.best()) {
            (Some(share), Some(best)) => {
                text(
                    egui::pos2(inner.right(), head - 1.0),
                    Align2::RIGHT_TOP,
                    &format!("{:.0} % of the best", 100.0 * share),
                    12.5,
                    if share >= 0.995 {
                        palette.plane
                    } else {
                        palette.ink
                    },
                );
                text(
                    egui::pos2(inner.left(), below),
                    Align2::LEFT_TOP,
                    &match best.lens {
                        Some(lens) => format!("sharpest at lens {}", style::focus_units(lens)),
                        None => "sharpest of these previews".to_owned(),
                    },
                    11.5,
                    palette.ink3,
                );
                let n = self.trace.samples().len();
                text(
                    egui::pos2(inner.right(), below),
                    Align2::RIGHT_TOP,
                    &if n == 1 {
                        "the first preview of this box".to_owned()
                    } else {
                        format!("last {n} previews")
                    },
                    11.5,
                    palette.ink3,
                );
            }
            _ => {
                text(
                    egui::pos2(inner.left(), below),
                    Align2::LEFT_TOP,
                    "rises as the box comes into focus",
                    11.5,
                    palette.ink3,
                );
            }
        }
        // The exposure and the preview rate.
        rule(inner.top() + 159.5);
        let y = inner.bottom();
        let e = s.host.exposure.as_ref();
        let mut x = inner.left();
        for t in [
            e.and_then(|e| e.iso).map(style::iso_label),
            e.and_then(|e| e.shutter).map(style::shutter_label),
            e.and_then(|e| e.f_number)
                .filter(|f| *f > 0)
                .map(|f| format!("f/{}", trim(f as f32 / 100.0))),
        ]
        .into_iter()
        .flatten()
        {
            x = style::paint_job(
                p,
                egui::pos2(x, y),
                Align2::LEFT_BOTTOM,
                style::job(&t, 12.5, palette.ink, 0.2),
            )
            .right()
                + 6.0;
        }
        if let Some(rate) = self.trace.rate(now) {
            text(
                egui::pos2(inner.right(), y),
                Align2::RIGHT_BOTTOM,
                &format!("{rate:.1} previews/s"),
                11.5,
                palette.ink3,
            );
        }
    }
}

/// A share in percent with the precision it needs (0.04, 0.4, 4, 40).
fn share_text(percent: f32) -> String {
    if percent > 0.0 && percent < 1.0 {
        format!("{percent:.1}")
    } else {
        format!("{percent:.0}")
    }
}

/// `x` on the nearest physical pixel.
fn on_pixel(x: f32, ppp: f32) -> f32 {
    (x * ppp).round() / ppp
}

/// The x of code `i` (0-255) across `rect`.
fn code_x(rect: Rect, i: f32) -> f32 {
    rect.left() + (i + 0.5) / 256.0 * rect.width()
}

/// Display heights (0-1) of a 256-bin histogram: smoothed by a 5-tap
/// binomial (a JPEG's tone curve combs its codes; the end bins are kept as
/// they are), square root of the count over `peak`.
fn heights(h: &[u32; 256], peak: f32) -> [f32; 256] {
    const TAPS: [f32; 5] = [1.0, 4.0, 6.0, 4.0, 1.0];
    let mut out = [0.0f32; 256];
    for (i, v) in out.iter_mut().enumerate() {
        let n = if !(2..=253).contains(&i) {
            h[i] as f32
        } else {
            TAPS.iter()
                .enumerate()
                .map(|(k, w)| w * h[i + k - 2] as f32)
                .sum::<f32>()
                / 16.0
        };
        *v = (n / peak).sqrt().min(1.0);
    }
    out
}

/// The runs of a curve that hold counts (with the zero point either side,
/// so a run comes down to the baseline), as separate polylines.
fn runs(points: &[Pos2], values: &[f32; 256]) -> Vec<Vec<Pos2>> {
    let mut out: Vec<Vec<Pos2>> = Vec::new();
    let mut open = false;
    for (i, p) in points.iter().enumerate() {
        let near = values[i.saturating_sub(1)..(i + 2).min(256)]
            .iter()
            .any(|v| *v > 0.0);
        if near {
            if !open {
                out.push(Vec::new());
                open = true;
            }
            if let Some(run) = out.last_mut() {
                run.push(*p);
            }
        } else {
            open = false;
        }
    }
    out.retain(|run| run.len() > 1);
    out
}

/// A filled area from `points` down to `base`, as triangles.
fn fill_under(mesh: &mut Mesh, points: &[Pos2], base: f32, color: Color32) {
    for pair in points.windows(2) {
        let i = mesh.vertices.len() as u32;
        mesh.colored_vertex(pair[0], color);
        mesh.colored_vertex(egui::pos2(pair[0].x, base), color);
        mesh.colored_vertex(pair[1], color);
        mesh.colored_vertex(egui::pos2(pair[1].x, base), color);
        mesh.add_triangle(i, i + 1, i + 2);
        mesh.add_triangle(i + 1, i + 3, i + 2);
    }
}

/// An antialiased polyline appended to `mesh` (egui's feathered stroke).
fn line(tessellator: &mut Tessellator, mesh: &mut Mesh, points: Vec<Pos2>, stroke: Stroke) {
    tessellator.tessellate_shape(Shape::line(points, stroke), mesh);
}

/// The preview's histograms, antialiased: the luma filled and stroked, red,
/// green and blue as lines, on a square-root scale (bins 0-3 and 254-255
/// are left out of the scale's peak: their spikes are the end zones). The
/// black zone at the left and the clipped zone at the right are marked, and
/// stronger when they hold pixels.
pub(crate) fn histogram_mesh(
    levels: &PreviewLevels,
    rect: Rect,
    ppp: f32,
    palette: &CapturePalette,
) -> Mesh {
    let mut mesh = Mesh::default();
    let px = 1.0 / ppp;
    let base = rect.bottom();
    let span = |a: u8, b: u8| {
        let w = rect.width() / 256.0;
        (
            on_pixel(rect.left() + f32::from(a) * w, ppp),
            on_pixel(rect.left() + (f32::from(b) + 1.0) * w, ppp),
        )
    };
    // Quarter rules and the baseline.
    for q in 1..4 {
        let x = on_pixel(rect.left() + rect.width() * q as f32 / 4.0, ppp);
        mesh.add_colored_rect(
            Rect::from_min_max(egui::pos2(x, rect.top()), egui::pos2(x + px, base)),
            palette.line,
        );
    }
    // The end zones.
    let (a, b) = span(0, PREVIEW_BLACK_CODE);
    mesh.add_colored_rect(
        Rect::from_min_max(egui::pos2(a, rect.top()), egui::pos2(b, base)),
        palette.ink3.gamma_multiply(if levels.black_share > 0.0005 {
            0.4
        } else {
            0.14
        }),
    );
    let (a, b) = span(PREVIEW_CLIP_CODE, 255);
    mesh.add_colored_rect(
        Rect::from_min_max(egui::pos2(a, rect.top()), egui::pos2(b, base)),
        palette
            .warn
            .gamma_multiply(if levels.clipped_share > 0.0005 {
                0.75
            } else {
                0.22
            }),
    );
    // One scale for all four: the highest bin between the end zones.
    let inner = usize::from(PREVIEW_BLACK_CODE) + 1..usize::from(PREVIEW_CLIP_CODE);
    let peak = std::iter::once(&levels.histogram)
        .chain(levels.channels.iter())
        .flat_map(|h| h[inner.clone()].iter().copied())
        .max()
        .unwrap_or(0)
        .max(1) as f32;
    // The curves stand a pixel above the baseline, where they hold counts.
    let floor = base - 1.5 * px;
    let height = floor - rect.top() - 1.0;
    let curve = |h: &[u32; 256]| -> (Vec<Pos2>, [f32; 256]) {
        let values = heights(h, peak);
        let points = values
            .iter()
            .enumerate()
            .map(|(i, v)| egui::pos2(code_x(rect, i as f32), floor - v * height))
            .collect();
        (points, values)
    };
    let (luma, luma_values) = curve(&levels.histogram);
    fill_under(&mut mesh, &luma, floor, palette.ink2.gamma_multiply(0.2));
    let mut tessellator = Tessellator::new(ppp, TessellationOptions::default(), [1, 1], vec![]);
    for (channel, color) in levels.channels.iter().zip(CHANNEL_COLORS) {
        let (points, values) = curve(channel);
        for run in runs(&points, &values) {
            line(
                &mut tessellator,
                &mut mesh,
                run,
                Stroke::new(1.0_f32, color),
            );
        }
    }
    for run in runs(&luma, &luma_values) {
        line(
            &mut tessellator,
            &mut mesh,
            run,
            Stroke::new(1.25_f32, palette.ink2),
        );
    }
    // The baseline over the curves' feet.
    mesh.add_colored_rect(
        Rect::from_min_max(
            egui::pos2(rect.left(), base - px),
            egui::pos2(rect.right(), base),
        ),
        palette.line2,
    );
    mesh
}

/// Red, green and blue for the channel lines: muted, readable on the
/// dark glass of every theme.
const CHANNEL_COLORS: [Color32; 3] = [
    Color32::from_rgba_premultiplied(196, 78, 68, 214),
    Color32::from_rgba_premultiplied(104, 168, 88, 214),
    Color32::from_rgba_premultiplied(84, 128, 206, 214),
];

/// The focus trace: the subject box's focus over the recent previews, the
/// newest at the right, scaled between the lowest and highest kept; the
/// sharpest marked with a rule, the newest with a square.
pub(crate) fn trace_mesh(
    trace: &FocusTrace,
    rect: Rect,
    ppp: f32,
    palette: &CapturePalette,
) -> Mesh {
    let mut mesh = Mesh::default();
    let px = 1.0 / ppp;
    let base = on_pixel(rect.bottom(), ppp);
    mesh.add_colored_rect(
        Rect::from_min_max(
            egui::pos2(rect.left(), base - px),
            egui::pos2(rect.right(), base),
        ),
        palette.line2,
    );
    let samples = trace.samples();
    let Some(best) = trace.best() else {
        return mesh;
    };
    let (lo, hi) = samples
        .iter()
        .fold((f32::INFINITY, f32::NEG_INFINITY), |(lo, hi), s| {
            (lo.min(s.value), hi.max(s.value))
        });
    let flat = hi - lo <= hi.abs() * 1e-3;
    let height = rect.height() - 4.0;
    let dx = rect.width() / (TRACE_LEN - 1) as f32;
    let n = samples.len();
    let point = |i: usize, v: f32| {
        let f = if flat { 0.5 } else { (v - lo) / (hi - lo) };
        egui::pos2(
            rect.right() - (n - 1 - i) as f32 * dx,
            rect.bottom() - 2.0 - f * height,
        )
    };
    let points: Vec<Pos2> = samples
        .iter()
        .enumerate()
        .map(|(i, s)| point(i, s.value))
        .collect();
    fill_under(
        &mut mesh,
        &points,
        base - px,
        palette.plane.gamma_multiply(0.12),
    );
    // The sharpest: a rule down to the baseline.
    let best_at = samples
        .iter()
        .rposition(|s| s.value == best.value)
        .unwrap_or(n - 1);
    let bx = on_pixel(points[best_at].x, ppp);
    mesh.add_colored_rect(
        Rect::from_min_max(
            egui::pos2(bx - px * 0.5, rect.top()),
            egui::pos2(bx + px * 0.5, base),
        ),
        palette.ink3,
    );
    let mut tessellator = Tessellator::new(ppp, TessellationOptions::default(), [1, 1], vec![]);
    if points.len() > 1 {
        line(
            &mut tessellator,
            &mut mesh,
            points.clone(),
            Stroke::new(1.5_f32, palette.plane),
        );
    }
    let last = points[n - 1];
    mesh.add_colored_rect(
        Rect::from_center_size(
            egui::pos2(on_pixel(last.x, ppp), on_pixel(last.y, ppp)),
            egui::vec2(5.0, 5.0),
        ),
        palette.plane,
    );
    mesh
}

fn trim(v: f32) -> String {
    let s = format!("{v:.1}");
    s.strip_suffix(".0").map(str::to_owned).unwrap_or(s)
}

/// A floating panel (`.glass`).
fn glass(p: &egui::Painter, rect: Rect, palette: &CapturePalette) {
    p.add(glass_shape(rect, palette));
}

/// [`glass`] as one shape, for a box drawn behind what was laid out in it.
fn glass_shape(rect: Rect, palette: &CapturePalette) -> egui::Shape {
    egui::Shape::Vec(vec![
        egui::Shape::rect_filled(rect.expand(1.0), 0.0, palette.line2),
        egui::Shape::rect_filled(rect, 0.0, palette.panel),
    ])
}

/// The subject box: a faint frame, white corner marks, its caption and,
/// when it can be edited, eight square handles (the one under the pointer
/// or being dragged filled).
fn subject_box(
    p: &egui::Painter,
    r: Rect,
    caption: &str,
    handles: bool,
    hot: Option<Handle>,
    ppp: f32,
) {
    p.rect_stroke(
        r,
        0.0,
        Stroke::new(1.0_f32, Color32::from_white_alpha(71)),
        StrokeKind::Middle,
    );
    let l = 14.0f32.min(r.width() / 3.0).min(r.height() / 3.0);
    let stroke = Stroke::new(1.5_f32, Color32::WHITE);
    for (c, dx, dy) in [
        (r.left_top(), 1.0, 1.0),
        (r.right_top(), -1.0, 1.0),
        (r.left_bottom(), 1.0, -1.0),
        (r.right_bottom(), -1.0, -1.0),
    ] {
        p.line_segment([c, c + egui::vec2(l * dx, 0.0)], stroke);
        p.line_segment([c, c + egui::vec2(0.0, l * dy)], stroke);
    }
    if handles {
        for h in Handle::ALL {
            let c = h.at(r);
            let c = egui::pos2(on_pixel(c.x, ppp), on_pixel(c.y, ppp));
            let square = Rect::from_center_size(c, egui::vec2(HANDLE, HANDLE));
            p.rect_filled(
                square,
                0.0,
                if hot == Some(h) {
                    Color32::WHITE
                } else {
                    Color32::from_black_alpha(170)
                },
            );
            p.rect_stroke(
                square,
                0.0,
                Stroke::new(1.0_f32, Color32::WHITE),
                StrokeKind::Inside,
            );
        }
    }
    style::paint_job(
        p,
        r.left_top() - egui::vec2(0.0, 8.0),
        Align2::LEFT_BOTTOM,
        style::caps_job(caption, 10.0, Color32::from_white_alpha(153)),
    );
}

#[cfg(test)]
#[path = "capture-live-tests.rs"]
mod tests;

/// The calibration's depth map as the Depth lens shows it (spec 6.1): each
/// tile's focus, from the live sweep (32 px preview tiles) or from RAW (64 px
/// sensor tiles), over the part of the preview the grid covers.
#[derive(Clone, Debug, PartialEq)]
pub(crate) struct DepthMap {
    /// Changes whenever the map does: the lens's mesh is rebuilt then.
    pub revision: u64,
    pub cols: usize,
    pub rows: usize,
    pub focus: Vec<Option<f64>>,
    /// The ramp's ends: the in-focus range.
    pub lo: f64,
    pub hi: f64,
    /// "from the live sweep, coarse" or "from RAW".
    pub source: &'static str,
    /// The sharp depth: a tile is in focus now within half of it.
    pub depth: f64,
    /// The share of the preview's width and height the grid covers.
    pub extent: [f32; 2],
    /// Where the pass left the lens: away from it, the lens isolates the
    /// tiles in focus at its position (spec 6.2).
    pub anchor: Option<u16>,
    /// The survey's light, for the Light and Glints lenses (RAW only).
    pub light: Option<LightMap>,
    /// The last proof plane's check, for the Still lens.
    pub still: Option<StillMap>,
}

/// The lens's colour ramp, near (0) to far (1): a perceptual rainbow
/// (Mikhailov's turbo, polynomial fit), the same on the stage and in the
/// legend.
pub(crate) fn ramp(t: f32) -> Color32 {
    let t = t.clamp(0.0, 1.0);
    let (t2, t3, t4, t5) = (t * t, t * t * t, t * t * t * t, t * t * t * t * t);
    let r = 0.1357 + 4.5974 * t - 42.3277 * t2 + 130.5887 * t3 - 150.5666 * t4 + 58.1375 * t5;
    let g = 0.0914 + 2.1856 * t + 4.8052 * t2 - 14.0195 * t3 + 4.2109 * t4 + 2.7747 * t5;
    let b = 0.1067 + 12.5925 * t - 60.1097 * t2 + 109.0745 * t3 - 88.5066 * t4 + 26.8183 * t5;
    let u = |v: f32| (v.clamp(0.0, 1.0) * 255.0).round() as u8;
    Color32::from_rgb(u(r), u(g), u(b))
}

/// The lens's opacity, and a tile's when the lens isolates what is in focus
/// at the lens position and it is not.
const LENS_ALPHA: f32 = 0.62;
const LENS_DIM: f32 = 0.12;

/// The evidence lenses over the live view (spec 6.1): one at a time.
#[derive(Clone, Copy, Debug, Default, PartialEq, Eq)]
pub(crate) enum Lens {
    #[default]
    Off,
    /// Where each part is in focus, near to far.
    Depth,
    /// What the plan's Start and End leave out.
    Cover,
    /// The body's level at the chosen exposure.
    Light,
    /// The highlights past the pin.
    Glints,
    /// How far the proof plane's shots disagree, by tile.
    Still,
}

/// The proof plane's check by tile (the Still lens): columns, rows, the
/// share of the frame's width and height the grid covers, the local
/// disagreement in photosites (NaN where not measured), and its limit.
#[derive(Clone, Debug, PartialEq)]
pub(crate) struct StillMap {
    pub cols: usize,
    pub rows: usize,
    pub extent: [f32; 2],
    pub local: Vec<f32>,
    pub limit: f32,
    /// "clean", "would be retaken" (the proof's verdict in words).
    pub verdict: String,
}

/// The survey's per-tile light (64 px tiles, the depth map's RAW grid):
/// the body's level and the highlights' top as shares of full scale at the
/// survey's long shutter.
#[derive(Clone, Debug, PartialEq)]
pub(crate) struct LightMap {
    pub level: Vec<f32>,
    pub glint: Vec<f32>,
    pub subject: Vec<bool>,
    pub long_s: f64,
}

/// The exposure a light lens is read at: the chosen shutter, and the
/// highlight groups' (seconds).
#[derive(Clone, Copy, Debug, PartialEq)]
pub(crate) struct LensExposure {
    pub shutter: f64,
    pub groups: Option<f64>,
}

/// The Light lens's bands: under 1 %, to 10 %, to 50 %, to 90 % of full
/// scale, and at the pin.
const LIGHT_BANDS: [f32; 4] = [0.01, 0.10, 0.50, 0.90];

/// A lens mesh's key: the lens, the map, the picture's rectangle, the zoom,
/// the lens position it isolates (none: every tile at full colour) and the
/// plan's ends (Cover).
type LensKey = (
    Lens,
    u64,
    [u32; 4],
    [u32; 4],
    Option<u16>,
    Option<(u16, u16)>,
    [u64; 2],
);

/// What the Cover lens counted: tiles with a focus, and those in focus only
/// before Start or only after End.
#[derive(Clone, Copy, Debug, Default, PartialEq, Eq)]
pub(crate) struct Cover {
    pub tiles: usize,
    pub before: usize,
    pub after: usize,
    /// Light: subject tiles per band. Glints: tiles past the pin, of them
    /// held by the groups, and the top in stops over the pin (x100).
    pub bands: [usize; 5],
    pub over: usize,
    pub held: usize,
    pub top_centistops: i32,
}

/// The automatic selection as the live view shows it.
#[derive(Clone, Debug, Default, PartialEq)]
pub(crate) struct AutoView {
    /// Live frames kept from the last survey.
    pub frames: usize,
    pub running: bool,
    /// What was found, or why nothing was.
    pub line: Option<String>,
    /// Sensitivity, Grow and Buffer of the selection shown.
    pub params: Option<[f32; 3]>,
}

impl LiveView {
    /// The automatic selection's panel at the top right of the picture:
    /// its summary and the three sliders, which select again from the kept
    /// evidence when let go.
    fn auto_panel(
        &mut self,
        ui: &mut Ui,
        photo: Rect,
        palette: &CapturePalette,
        out: &mut Vec<LiveIntent>,
    ) {
        let Some(line) = self.auto.line.clone() else {
            return;
        };
        let height = if self.auto.params.is_some() {
            132.0
        } else {
            52.0
        };
        const WIDTH: f32 = 300.0;
        let rect = Rect::from_min_size(
            egui::pos2(photo.right() - WIDTH - 10.0, photo.top() + 10.0),
            egui::vec2(WIDTH, height),
        );
        glass(ui.painter(), rect, palette);
        ui.scope_builder(
            egui::UiBuilder::new().max_rect(rect.shrink2(egui::vec2(10.0, 8.0))),
            |ui| {
                ui.spacing_mut().item_spacing.y = 3.0;
                style::caps(ui, "Auto outline", palette);
                ui.add(
                    egui::Label::new(egui::RichText::new(line).size(11.0).color(palette.ink2))
                        .truncate(),
                );
                let Some(shown) = self.auto.params else {
                    return;
                };
                let mut values = self.auto_draft.unwrap_or(shown);
                let mut released = false;
                for (i, (label, range, hint)) in [
                    (
                        "Sensitivity",
                        1.0..=10.0,
                        "Higher keeps only the surest detail",
                    ),
                    (
                        "Grow",
                        0.0..=6.0,
                        "How far weaker detail joins what is sure",
                    ),
                    (
                        "Buffer px",
                        0.0..=96.0,
                        "Margin around the outline, in sensor pixels",
                    ),
                ]
                .into_iter()
                .enumerate()
                {
                    ui.horizontal(|ui| {
                        // Label, slider and its value inside the panel
                        // (owner, 2026-11-24: the value boxes hung over
                        // its right edge).
                        const LABEL: f32 = 74.0;
                        const VALUE: f32 = 44.0;
                        let gaps = 2.0 * ui.spacing().item_spacing.x;
                        ui.spacing_mut().slider_width =
                            (ui.available_width() - LABEL - VALUE - gaps).max(40.0);
                        ui.spacing_mut().interact_size.x = VALUE;
                        ui.add_sized(
                            egui::vec2(LABEL, 16.0),
                            egui::Label::new(
                                egui::RichText::new(label).size(11.0).color(palette.ink2),
                            ),
                        );
                        let r = ui
                            .add_enabled(
                                !self.auto.running,
                                egui::Slider::new(&mut values[i], range).show_value(true),
                            )
                            .on_hover_text(hint);
                        if r.changed() {
                            self.auto_draft = Some(values);
                        }
                        released |= r.drag_stopped() || (r.changed() && !r.dragged());
                    });
                }
                if released && let Some([sensitivity, grow, buffer_px]) = self.auto_draft.take() {
                    out.push(LiveIntent::AutoParams {
                        sensitivity,
                        grow,
                        buffer_px,
                    });
                }
            },
        );
    }
}

/// How near (points) a vertex is still taken by a press.
const VERTEX_REACH: f32 = 7.0;

/// The outline being drawn or dragged (plan S3).
#[derive(Clone, Debug, Default, PartialEq)]
pub(crate) enum OutlineEdit {
    #[default]
    None,
    /// Points placed so far, in preview fractions.
    Placing(Vec<Pos2>),
    /// A vertex of the outline's ring `ring` dragged.
    Dragging { ring: usize, index: usize },
}

/// The outline's rings in preview fractions (the active area: live view
/// shows the whole of it, MEASURED 100.0 % by 99.8 %).
pub(crate) fn outline_rings(subject: Option<&Subject>) -> Vec<Vec<Pos2>> {
    subject.map_or_else(Vec::new, |s| {
        s.rings
            .iter()
            .map(|ring| ring.iter().map(|[x, y]| egui::pos2(*x, *y)).collect())
            .collect()
    })
}

/// A manual outline from rings in preview fractions.
pub(crate) fn manual_subject(rings: &[Vec<Pos2>], focus: Option<u16>) -> Option<Subject> {
    let rings: Vec<Vec<[f32; 2]>> = rings
        .iter()
        .filter(|r| r.len() >= 3)
        .map(|r| {
            r.iter()
                .take(Subject::MAX_POINTS)
                .map(|p| [p.x.clamp(0.0, 1.0), p.y.clamp(0.0, 1.0)])
                .collect()
        })
        .collect();
    let subject = Subject {
        rings,
        reference_focus: focus,
        rate_ppm: None,
        provenance: serde_json::json!({"kind":"manual"}),
    };
    subject.validate().ok().map(|()| subject)
}

/// The nearest vertex within reach of `at` (screen points).
fn vertex_at(
    rings: &[Vec<Pos2>],
    at: Pos2,
    to_screen: &dyn Fn(Pos2) -> Pos2,
) -> Option<(usize, usize)> {
    let mut best: Option<(f32, usize, usize)> = None;
    for (r, ring) in rings.iter().enumerate() {
        for (i, p) in ring.iter().enumerate() {
            let d = to_screen(*p).distance(at);
            if d <= VERTEX_REACH && best.is_none_or(|b| d < b.0) {
                best = Some((d, r, i));
            }
        }
    }
    best.map(|(_, r, i)| (r, i))
}

/// The edge of a ring within reach of `at`, and where on it (the index the
/// new point takes).
fn edge_at(
    rings: &[Vec<Pos2>],
    at: Pos2,
    to_screen: &dyn Fn(Pos2) -> Pos2,
) -> Option<(usize, usize)> {
    for (r, ring) in rings.iter().enumerate() {
        for i in 0..ring.len() {
            let (a, b) = (to_screen(ring[i]), to_screen(ring[(i + 1) % ring.len()]));
            let ab = b - a;
            let t = ((at - a).dot(ab) / ab.length_sq().max(1e-6)).clamp(0.0, 1.0);
            if (a + ab * t).distance(at) <= EDGE_REACH + 1.0 {
                return Some((r, i + 1));
            }
        }
    }
    None
}

impl LiveView {
    /// The outline mode (plan S3): click to place points, click the first
    /// point (or double-click) to close the ring; on a drawn outline, drag a
    /// point to move it, click an edge to add one, right-click a point to
    /// remove it; Esc drops what is being placed.
    #[allow(clippy::too_many_arguments)]
    fn outline_ui(
        &mut self,
        ui: &Ui,
        p: &egui::Painter,
        response: &egui::Response,
        host_subject: Option<&Subject>,
        focus: Option<u16>,
        can_edit: bool,
        to_uv: &dyn Fn(Pos2) -> Pos2,
        to_screen: &dyn Fn(Pos2) -> Pos2,
        palette: &CapturePalette,
        out: &mut Vec<LiveIntent>,
    ) {
        let mut rings = self
            .outline_sent
            .clone()
            .unwrap_or_else(|| outline_rings(host_subject));
        if can_edit {
            if ui.input(|i| i.key_pressed(egui::Key::Escape)) {
                self.outline_edit = OutlineEdit::None;
            }
            let pointer = response.interact_pointer_pos();
            match self.outline_edit.clone() {
                OutlineEdit::Placing(mut points) => {
                    if response.double_clicked()
                        || (response.clicked()
                            && points.len() >= 3
                            && pointer.is_some_and(|at| {
                                to_screen(points[0]).distance(at) <= VERTEX_REACH
                            }))
                    {
                        if response.double_clicked() {
                            // The double click's first click placed a point.
                            points.pop();
                        }
                        let mut next = rings.clone();
                        next.push(points);
                        if let Some(subject) = manual_subject(&next, focus) {
                            out.push(LiveIntent::SetSubject(Some(subject)));
                            self.outline_sent = Some(next);
                        }
                        self.outline_edit = OutlineEdit::None;
                    } else if response.clicked()
                        && let Some(at) = pointer
                        && points.len() < Subject::MAX_POINTS
                    {
                        points.push(to_uv(at));
                        self.outline_edit = OutlineEdit::Placing(points);
                    }
                }
                OutlineEdit::Dragging { ring, index } => {
                    if let Some(at) = pointer
                        && let Some(point) = rings.get_mut(ring).and_then(|r| r.get_mut(index))
                    {
                        *point = to_uv(at);
                        self.outline_sent = Some(rings.clone());
                    }
                    if response.drag_stopped() {
                        self.outline_edit = OutlineEdit::None;
                        if let Some(subject) = manual_subject(&rings, focus) {
                            out.push(LiveIntent::SetSubject(Some(subject)));
                        }
                    }
                }
                OutlineEdit::None => {
                    let press = ui.input(|i| i.pointer.press_origin());
                    if response.drag_started()
                        && let Some((ring, index)) =
                            press.and_then(|at| vertex_at(&rings, at, to_screen))
                    {
                        self.outline_edit = OutlineEdit::Dragging { ring, index };
                    } else if response.secondary_clicked()
                        && let Some((ring, index)) =
                            pointer.and_then(|at| vertex_at(&rings, at, to_screen))
                    {
                        rings[ring].remove(index);
                        rings.retain(|r| r.len() >= 3);
                        let subject = manual_subject(&rings, focus);
                        out.push(LiveIntent::SetSubject(subject));
                        self.outline_sent = Some(rings.clone());
                    } else if response.clicked()
                        && let Some(at) = pointer
                    {
                        if let Some((ring, index)) = edge_at(&rings, at, to_screen)
                            .filter(|(r, _)| rings[*r].len() < Subject::MAX_POINTS)
                        {
                            rings[ring].insert(index, to_uv(at));
                            if let Some(subject) = manual_subject(&rings, focus) {
                                out.push(LiveIntent::SetSubject(Some(subject)));
                                self.outline_sent = Some(rings.clone());
                            }
                        } else {
                            // A new ring starts here (a second part, or a
                            // hole inside the first: even-odd).
                            self.outline_edit = OutlineEdit::Placing(vec![to_uv(at)]);
                        }
                    }
                }
            }
            let cursor = match &self.outline_edit {
                OutlineEdit::Dragging { .. } => Some(CursorIcon::Grabbing),
                _ => response.hover_pos().map(|at| {
                    if vertex_at(&rings, at, to_screen).is_some() {
                        CursorIcon::Grab
                    } else {
                        CursorIcon::Crosshair
                    }
                }),
            };
            if let Some(cursor) = cursor
                && response.hovered()
            {
                ui.ctx().set_cursor_icon(cursor);
            }
        }
        // The outline: its rings in the accent, their points as small squares.
        let line = Stroke::new(1.5_f32, palette.accent);
        for ring in &rings {
            let points: Vec<Pos2> = ring.iter().map(|q| to_screen(*q)).collect();
            if points.len() >= 2 {
                p.add(egui::Shape::closed_line(points.clone(), line));
            }
            if can_edit {
                for q in &points {
                    p.rect_filled(
                        Rect::from_center_size(*q, Vec2::splat(5.0)),
                        0.0,
                        palette.accent,
                    );
                }
            }
        }
        if let OutlineEdit::Placing(points) = &self.outline_edit {
            let mut shown: Vec<Pos2> = points.iter().map(|q| to_screen(*q)).collect();
            if let Some(hover) = response.hover_pos() {
                shown.push(hover);
            }
            if shown.len() >= 2 {
                p.add(egui::Shape::line(
                    shown.clone(),
                    Stroke::new(1.0_f32, palette.accent),
                ));
            }
            for q in &shown {
                p.rect_stroke(
                    Rect::from_center_size(*q, Vec2::splat(6.0)),
                    0.0,
                    Stroke::new(1.0_f32, palette.accent),
                    StrokeKind::Middle,
                );
            }
        }
        let caption = match (&self.outline_edit, rings.is_empty()) {
            (OutlineEdit::Placing(points), _) => format!(
                "Outline · {} points · click the first point or double-click to close · Esc drops it",
                points.len()
            ),
            (_, true) => "Outline · click around the subject to draw it".into(),
            (_, false) => format!(
                "Outline · {} part{} · drag a point, click an edge to add one, right-click to remove",
                rings.len(),
                if rings.len() == 1 { "" } else { "s" }
            ),
        };
        let galley = p.layout_job(style::job(&caption, 11.0, palette.ink2, 0.0));
        let at = to_screen(egui::pos2(0.0, 0.0)) + egui::vec2(12.0, 44.0);
        p.galley(at, galley, palette.ink2);
    }
}
