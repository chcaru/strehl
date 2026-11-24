//! One retained overview and a bounded cache of source-registered detail
//! tiles. Pointer motion only changes geometry; one worker develops the tiles
//! the latest view needs, nearest its centre first, and supersedes the rest.
//!
//! Tiles form a power-of-two pyramid on the master's pixel grid: a tile at
//! stride `s` holds up to `TILE` x `TILE` texels, each the mean of an `s` x `s`
//! bin of source pixels developed with the current recipe (stride 1 is the
//! export's own development, pixel for pixel). The view asks for the coarsest
//! stride whose texels are no larger than a screen pixel, so the photograph
//! is sharp at every zoom up to native, and shows true pixels beyond it.
use crate::{
    development_job::{DevelopmentJob, DevelopmentToken},
    hdr_display::{FloatPhoto, PhotoLayer, PhotoPresenter},
};
use eframe::egui::{self, Color32, Pos2, Rect, TextureHandle, Vec2};
use std::{
    collections::{HashMap, HashSet, VecDeque},
    panic::AssertUnwindSafe,
    sync::{
        Arc, Condvar, Mutex,
        atomic::{AtomicBool, Ordering},
        mpsc,
    },
    time::{Duration, Instant},
};
#[cfg(test)]
use strehl_edit::DevelopmentRecipe;
use strehl_edit::{DisplayRegionRequest, LinearImage};

#[path = "photo-export.rs"]
mod export;
pub(crate) use export::ExportRequest;

/// Core texels on a tile's side. Each tile also carries a one-texel apron so
/// bilinear filtering is continuous across tile edges.
const TILE: u32 = 1024;
/// Texture bytes the cache may hold beyond the tiles the view shows.
const CACHE_BYTES: u64 = 384 << 20;
/// The tiles a view shows never exceed this many texels; a larger view (an
/// 8K canvas at nearly 2x oversampling) takes the next coarser level.
const MAX_VIEW_TEXELS: f32 = 40.0 * 1024.0 * 1024.0;
const SETTLE: Duration = Duration::from_millis(80);
const REVEAL: Duration = Duration::from_millis(120);
const FRAME_DELAY: Duration = Duration::from_millis(16);
/// Egui-texture uploads per frame when no presenter uploads off-thread.
const FALLBACK_UPLOADS: usize = 2;
/// The loading mark appears only once detail has been pending this long.
const QUIET: Duration = Duration::from_millis(150);

fn request_paced_repaint(ctx: &egui::Context, delay: Duration) {
    // egui subtracts predicted_dt. Compensate so this is an actual future
    // deadline, including on 60Hz displays where 16ms would otherwise be zero.
    let predicted =
        ctx.input(|input| Duration::try_from_secs_f32(input.predicted_dt).unwrap_or_default());
    ctx.request_repaint_after(delay.saturating_add(predicted));
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(super) struct Identity {
    pub snapshot: Option<DevelopmentToken>,
    pub revision: u64,
    pub before: bool,
    pub hdr: bool,
}

pub(super) struct PreparedPhoto {
    pub sdr: Option<egui::ColorImage>,
    pub size: [u32; 2],
    pub uv: [[f32; 2]; 2],
    pub layer: Option<PhotoLayer>,
    pub upload_error: Option<String>,
    pub source_samples: u64,
    pub elapsed_ms: f64,
}

pub(super) fn prepare_job(
    job: &DevelopmentJob,
    coarse: bool,
    request: DisplayRegionRequest,
    cancelled: &AtomicBool,
    presenter: Option<&PhotoPresenter>,
    hdr: bool,
    retain_fallback: bool,
) -> anyhow::Result<PreparedPhoto> {
    prepare_covered(
        job.image(coarse),
        job.recipe(),
        request,
        cancelled,
        presenter,
        (hdr, retain_fallback, false),
        job.coverage(),
    )
}

#[cfg(test)]
pub(super) fn prepare(
    source: &LinearImage,
    recipe: &DevelopmentRecipe,
    request: DisplayRegionRequest,
    cancelled: &AtomicBool,
    presenter: Option<&PhotoPresenter>,
    hdr: bool,
    retain_fallback: bool,
) -> anyhow::Result<PreparedPhoto> {
    prepare_covered(
        source,
        recipe,
        request,
        cancelled,
        presenter,
        (hdr, retain_fallback, false),
        None,
    )
}

/// `(hdr, retain_fallback, nearest)`: float pixels, keep the SDR bytes for an
/// egui texture, and keep magnified texels square (native tiles).
fn prepare_covered(
    source: &LinearImage,
    recipe: &strehl_edit::DevelopmentRecipe,
    request: DisplayRegionRequest,
    cancelled: &AtomicBool,
    presenter: Option<&PhotoPresenter>,
    (hdr, retain_fallback, nearest): (bool, bool, bool),
    coverage: Option<&crate::photo_coverage::Coverage>,
) -> anyhow::Result<PreparedPhoto> {
    let start = Instant::now();
    let mut image = source.render_display_region_mode(recipe, request, cancelled, hdr)?;
    if let Some(coverage) = coverage {
        for y in 0..image.size[1] {
            anyhow::ensure!(
                !cancelled.load(Ordering::Relaxed),
                "Display refinement cancelled"
            );
            for x in 0..image.size[0] {
                let min = [
                    request.min[0] + x * request.stride,
                    request.min[1] + y * request.stride,
                ];
                let max = [0, 1].map(|c| (min[c] + request.stride).min(request.max[c]));
                if !coverage.supported([source.width, source.height], min, max) {
                    let value = coverage.checker_rgb([source.width, source.height], min);
                    let i = (y * image.size[0] + x) as usize;
                    image.rgb[i * 3..i * 3 + 3].fill(value);
                    if hdr {
                        let encoded = f32::from(value) / 255.0;
                        let linear = ((encoded + 0.055) / 1.055).powf(2.4);
                        image.rgba_linear[i * 4..i * 4 + 3].fill(linear);
                        image.rgba_linear[i * 4 + 3] = 1.0;
                    }
                }
            }
        }
    }
    let uv = [
        [
            request.min[0] as f32 / source.width as f32,
            request.min[1] as f32 / source.height as f32,
        ],
        [
            request.max[0] as f32 / source.width as f32,
            request.max[1] as f32 / source.height as f32,
        ],
    ];
    let sdr = (retain_fallback || presenter.is_none())
        .then(|| egui::ColorImage::from_rgb(image.size.map(|v| v as usize), &image.rgb));
    // Device/queue work and payload validation happen in this worker, never in
    // publication. The UI receives only immutable GPU handles and a small fallback.
    let uploaded = presenter.map(|presenter| {
        if hdr {
            presenter.upload(Arc::new(FloatPhoto {
                size: image.size,
                rgba: image.rgba_linear.into(),
                uv,
                reference_white_nits: recipe.hdr.reference_white_nits,
                peak_nits: recipe.hdr.peak_nits,
                origin: source.origin,
            }))
        } else {
            let rgba = image
                .rgb
                .as_chunks::<3>()
                .0
                .iter()
                .flat_map(|p| [p[0], p[1], p[2], 255])
                .collect::<Vec<_>>();
            presenter.upload_sdr_sampled(image.size, rgba.into(), uv, nearest)
        }
    });
    anyhow::ensure!(
        !cancelled.load(Ordering::Relaxed),
        "Display refinement cancelled"
    );
    let (layer, upload_error) = match uploaded {
        Some(Ok(layer)) => (Some(layer), None),
        Some(Err(error)) => (None, Some(format!("{error:#}"))),
        None => (None, None),
    };
    Ok(PreparedPhoto {
        sdr,
        size: image.size,
        uv,
        layer,
        upload_error,
        source_samples: image.source_samples,
        elapsed_ms: start.elapsed().as_secs_f64() * 1000.0,
    })
}

/// One tile of the pyramid: `stride` source pixels per texel, `side` texels.
#[derive(Clone, Copy, Debug, PartialEq, Eq, Hash)]
pub(super) struct TileKey {
    pub stride: u32,
    pub side: u32,
    pub x: u32,
    pub y: u32,
}

impl TileKey {
    fn span(self) -> u32 {
        self.side * self.stride
    }
    /// The tile's own source pixels, maximum excluded.
    pub(super) fn core(self, source: [u32; 2]) -> [u32; 4] {
        let span = self.span();
        let (x0, y0) = (self.x * span, self.y * span);
        [
            x0,
            y0,
            (x0 + span).min(source[0]),
            (y0 + span).min(source[1]),
        ]
    }
    /// The core plus one texel of apron on every side inside the photograph.
    /// Bins stay on the global grid: every edge but the photograph's own is
    /// a multiple of the stride.
    pub(super) fn request(self, source: [u32; 2]) -> DisplayRegionRequest {
        let [x0, y0, x1, y1] = self.core(source);
        DisplayRegionRequest {
            min: [
                x0.saturating_sub(self.stride),
                y0.saturating_sub(self.stride),
            ],
            max: [
                (x1 + self.stride).min(source[0]),
                (y1 + self.stride).min(source[1]),
            ],
            stride: self.stride,
        }
    }
    fn core_uv(self, source: [u32; 2]) -> Rect {
        let [x0, y0, x1, y1] = self.core(source);
        Rect::from_min_max(
            egui::pos2(x0 as f32 / source[0] as f32, y0 as f32 / source[1] as f32),
            egui::pos2(x1 as f32 / source[0] as f32, y1 as f32 / source[1] as f32),
        )
    }
}

/// Tile indices `[x0, y0, x1, y1)` covering `aperture` at `stride`.
fn tile_range(source: [u32; 2], aperture: Rect, stride: u32, side: u32) -> [u32; 4] {
    let span = (side * stride) as f32;
    let count = [0, 1].map(|i| source[i].div_ceil(side * stride));
    let index = |v: f32, i: usize, up: bool| {
        let t = v * source[i] as f32 / span;
        let t = if up { t.ceil() } else { t.floor() };
        (t.max(0.0) as u32).min(count[i])
    };
    let x0 = index(aperture.min.x, 0, false).min(count[0] - 1);
    let y0 = index(aperture.min.y, 1, false).min(count[1] - 1);
    [
        x0,
        y0,
        index(aperture.max.x, 0, true).max(x0 + 1),
        index(aperture.max.y, 1, true).max(y0 + 1),
    ]
}

/// The coarsest power-of-two stride whose texels are no larger than a screen
/// pixel, coarsened only while the view would exceed `MAX_VIEW_TEXELS`.
pub(super) fn target_stride(source: [u32; 2], aperture: Rect, physical: [u32; 2]) -> Option<u32> {
    if source.contains(&0) || !aperture.is_positive() || !aperture.is_finite() {
        return None;
    }
    let native = [
        aperture.width() * source[0] as f32,
        aperture.height() * source[1] as f32,
    ];
    let ratio = (native[0] / physical[0].max(1) as f32).min(native[1] / physical[1].max(1) as f32);
    let mut stride = 1u32;
    // 1 % tolerance: an exact 50 % view takes stride 2, not twice its pixels.
    while (stride * 2) as f32 <= ratio * 1.01 && stride < 32768 {
        stride *= 2;
    }
    while native[0] * native[1] / (stride as f32 * stride as f32) > MAX_VIEW_TEXELS
        && stride < 32768
    {
        stride *= 2;
    }
    Some(stride)
}

#[derive(Clone)]
struct TilePaint {
    stride: u32,
    /// Photograph UV the tile owns, and the UV its texture covers (apron).
    core: Rect,
    uv: Rect,
    size: [u32; 2],
    texture: Option<TextureHandle>,
    layer: Option<PhotoLayer>,
    published: Instant,
}

/// Immutable geometry/pixel generation passed to the photograph painter.
#[derive(Clone)]
pub(crate) struct PhotoPaint {
    overview: TextureHandle,
    presenter: Option<PhotoPresenter>,
    layer: Option<PhotoLayer>,
    /// Coarse to fine; every tile shares the overview's recipe.
    tiles: Arc<Vec<TilePaint>>,
    hdr: bool,
    /// Visible detail ready, while detail is pending: the quiet loading mark.
    progress: Option<f32>,
    /// Export: the selected preset's own pixels over its crop.
    export: Option<export::ExportPaint>,
}

impl PhotoPaint {
    pub(crate) fn paint(&self, painter: &egui::Painter, destination: Rect, aperture: Rect) {
        match &self.export {
            Some(export) if export.covers(aperture) => export.paint(painter, destination, aperture),
            Some(export) => {
                self.paint_development(painter, destination, aperture);
                export.paint(painter, destination, aperture);
            }
            None => self.paint_development(painter, destination, aperture),
        }
        if let Some(done) = self.progress {
            paint_progress(painter, destination, done);
        }
    }

    /// [`Self::paint`], returned as shapes for a slot reserved earlier in
    /// `painter`'s layer (the split view's "before", beneath the tools). The
    /// shapes are taken back out of the layer; they stay within
    /// `destination`, so the slot's clip is enough.
    pub(crate) fn paint_shapes(
        &self,
        painter: &egui::Painter,
        destination: Rect,
        aperture: Rect,
    ) -> Vec<egui::Shape> {
        let layer = painter.layer_id();
        let ctx = painter.ctx();
        let start = ctx.graphics(|g| g.get(layer).map_or(0, |list| list.next_idx().0));
        self.paint(&painter.with_clip_rect(destination), destination, aperture);
        ctx.graphics_mut(|g| {
            let list = g.entry(layer);
            let end = list.next_idx().0;
            let mut shapes = Vec::with_capacity(end.saturating_sub(start));
            for i in start..end {
                list.mutate_shape(egui::layers::ShapeIdx(i), |clipped| {
                    shapes.push(std::mem::replace(&mut clipped.shape, egui::Shape::Noop));
                });
            }
            shapes
        })
    }

    fn paint_development(&self, painter: &egui::Painter, destination: Rect, aperture: Rect) {
        let now = Instant::now();
        let opacity = |tile: &TilePaint| {
            (now.saturating_duration_since(tile.published).as_secs_f32() / REVEAL.as_secs_f32())
                .clamp(0.0, 1.0)
        };
        let visible: Vec<(&TilePaint, f32)> = self
            .tiles
            .iter()
            .filter(|tile| tile.core.intersect(aperture).is_positive())
            .map(|tile| (tile, opacity(tile)))
            .filter(|(_, alpha)| *alpha > 0.0)
            .collect();
        if visible.iter().any(|(_, alpha)| *alpha < 1.0) {
            request_paced_repaint(painter.ctx(), FRAME_DELAY);
        }
        // The finest level whose opaque tiles cover the aperture is the
        // whole base: the overview and coarser levels would be overwritten.
        let base = covering_stride(&visible, aperture);
        let shown = visible
            .iter()
            .filter(|(tile, _)| base.is_none_or(|stride| tile.stride <= stride))
            .collect::<Vec<_>>();
        let ppp = painter.ctx().pixels_per_point();
        // Screen pixels per texel: at or above one, a native tile shows true
        // pixels (nearest); below one every level filters linearly.
        let nearest = |tile: &TilePaint| {
            tile.stride == 1
                && destination.width() / aperture.width() * tile.uv.width() * ppp
                    / tile.size[0].max(1) as f32
                    >= 0.999
        };
        let mut painted = false;
        if let (Some(presenter), Some(overview)) = (&self.presenter, &self.layer) {
            let everything = Rect::from_min_max(Pos2::ZERO, egui::pos2(1.0, 1.0));
            let mut layers = vec![(
                overview,
                if base.is_some() {
                    Rect::NOTHING
                } else {
                    everything
                },
                1.0,
                false,
            )];
            layers.extend(shown.iter().filter_map(|(tile, alpha)| {
                tile.layer
                    .as_ref()
                    .map(|layer| (layer, tile.core, *alpha, nearest(tile)))
            }));
            painted = presenter.paint_regions(painter, destination, aperture, self.hdr, &layers);
        }
        if !painted {
            let gaps = shown.iter().any(|(tile, _)| tile.texture.is_none());
            if base.is_none() || gaps {
                painter.image(self.overview.id(), destination, aperture, Color32::WHITE);
            }
            let project = |p: Pos2| {
                destination.min + (p - aperture.min) / aperture.size() * destination.size()
            };
            for (tile, alpha) in &shown {
                let Some(texture) = &tile.texture else {
                    continue;
                };
                let shared = aperture.intersect(tile.core);
                let local = |p: Pos2| Pos2::ZERO + (p - tile.uv.min) / tile.uv.size();
                painter.image(
                    texture.id(),
                    Rect::from_min_max(project(shared.min), project(shared.max)),
                    Rect::from_min_max(local(shared.min), local(shared.max)),
                    Color32::WHITE.gamma_multiply(*alpha),
                );
            }
        }
    }
}

/// A one-pixel ruled mark along the bottom of the visible photograph: how
/// much of the view's detail has arrived. No spinner, no overlay.
fn paint_progress(painter: &egui::Painter, destination: Rect, done: f32) {
    let visible = destination.intersect(painter.clip_rect());
    if !visible.is_positive() {
        return;
    }
    let t = crate::studio_theme::tokens(painter.ctx());
    let y = visible.bottom() - 1.5;
    let width = visible.width() * done.clamp(0.0, 1.0);
    painter.line_segment(
        [
            egui::pos2(visible.left(), y),
            egui::pos2(visible.right(), y),
        ],
        egui::Stroke::new(1.0_f32, t.line),
    );
    painter.line_segment(
        [
            egui::pos2(visible.left(), y),
            egui::pos2(visible.left() + width, y),
        ],
        egui::Stroke::new(1.0_f32, t.accent),
    );
}

/// The finest stride whose opaque tiles cover `aperture` completely.
fn covering_stride(visible: &[(&TilePaint, f32)], aperture: Rect) -> Option<u32> {
    let mut strides = visible.iter().map(|(t, _)| t.stride).collect::<Vec<_>>();
    strides.sort_unstable();
    strides.dedup();
    strides.into_iter().find(|&stride| {
        // Tiles of one level own disjoint cores, so an area sum decides.
        let area = visible
            .iter()
            .filter(|(t, alpha)| {
                t.stride == stride && *alpha >= 1.0 && (t.layer.is_some() || t.texture.is_some())
            })
            .map(|(t, _)| t.core.intersect(aperture).area())
            .sum::<f32>();
        area >= aperture.area() * (1.0 - 1e-4)
    })
}

struct Tile {
    request: DisplayRegionRequest,
    core: Rect,
    uv: Rect,
    size: [u32; 2],
    texture: Option<TextureHandle>,
    layer: Option<PhotoLayer>,
    bytes: u64,
    published: Instant,
    used: u64,
}

#[derive(Clone, Copy, Debug, PartialEq)]
struct Demand {
    aperture: Rect,
    physical: [u32; 2],
    source: [u32; 2],
    stride: u32,
    side: u32,
    /// Tile indices the view shows, at `stride`.
    visible: [u32; 4],
}

impl Demand {
    fn keys(&self, range: [u32; 4]) -> impl Iterator<Item = TileKey> + '_ {
        (range[1]..range[3]).flat_map(move |y| {
            (range[0]..range[2]).map(move |x| TileKey {
                stride: self.stride,
                side: self.side,
                x,
                y,
            })
        })
    }
    fn shows(&self, key: &TileKey) -> bool {
        key.stride == self.stride
            && key.side == self.side
            && (self.visible[0]..self.visible[2]).contains(&key.x)
            && (self.visible[1]..self.visible[3]).contains(&key.y)
    }
    /// One more tile on every side: the pan prefetch.
    fn ring(&self) -> [u32; 4] {
        let count = [0, 1].map(|i| self.source[i].div_ceil(self.side * self.stride));
        [
            self.visible[0].saturating_sub(1),
            self.visible[1].saturating_sub(1),
            (self.visible[2] + 1).min(count[0]),
            (self.visible[3] + 1).min(count[1]),
        ]
    }
    /// Nearest the view's centre first.
    fn ordered(&self, mut keys: Vec<TileKey>) -> Vec<TileKey> {
        let centre = self.aperture.center();
        let centre = [
            centre.x * self.source[0] as f32,
            centre.y * self.source[1] as f32,
        ];
        let distance = |k: &TileKey| {
            let span = k.span() as f32;
            let c = [(k.x as f32 + 0.5) * span, (k.y as f32 + 0.5) * span];
            (c[0] - centre[0]).powi(2) + (c[1] - centre[1]).powi(2)
        };
        keys.sort_by(|a, b| distance(a).total_cmp(&distance(b)));
        keys
    }
    fn overview_enough(&self, overview: [usize; 2]) -> bool {
        (0..2).all(|i| overview[i] as u32 >= self.source[i].div_ceil(self.stride))
    }
}

struct Work {
    /// Results from before a reset or a new overview are never published,
    /// even when a reopened document repeats the identity.
    epoch: u64,
    identity: Identity,
    job: DevelopmentJob,
    presenter: Option<PhotoPresenter>,
    retain_fallback: bool,
    wake: egui::Context,
    tiles: VecDeque<TileKey>,
}

#[derive(Default)]
struct Queue {
    work: Option<Work>,
    in_flight: Option<(Identity, TileKey, Arc<AtomicBool>)>,
    closed: bool,
}

struct TileResult {
    epoch: u64,
    identity: Identity,
    key: TileKey,
    source: [u32; 2],
    outcome: Result<PreparedPhoto, String>,
    cancelled: bool,
}

/// One long-lived worker per viewport. Development inside a tile is already
/// row-parallel, so one tile at a time keeps every core busy while letting a
/// newer view take over between tiles.
struct Worker {
    queue: Arc<(Mutex<Queue>, Condvar)>,
    results: mpsc::Receiver<TileResult>,
}

impl Worker {
    fn start() -> std::io::Result<Self> {
        let queue = Arc::new((Mutex::new(Queue::default()), Condvar::new()));
        let (sender, results) = mpsc::channel();
        let shared = Arc::clone(&queue);
        std::thread::Builder::new()
            .name("strehl-photo-tiles".into())
            .spawn(move || run_worker(&shared, &sender))?;
        Ok(Self { queue, results })
    }
    /// Replace the queue. A tile in flight continues only if still wanted.
    /// Returns whether a tile in flight was cancelled.
    fn post(&self, mut work: Work) -> bool {
        let (lock, ready) = &*self.queue;
        let mut queue = lock.lock().unwrap();
        let mut cancelled = false;
        if let Some((identity, key, cancel)) = &queue.in_flight {
            if *identity == work.identity && work.tiles.contains(key) {
                work.tiles.retain(|tile| tile != key);
            } else if !cancel.swap(true, Ordering::Relaxed) {
                cancelled = true;
            }
        }
        queue.work = Some(work);
        drop(queue);
        ready.notify_one();
        cancelled
    }
    /// Drop the queue and cancel the tile in flight.
    fn stop(&self) -> bool {
        let mut queue = self.queue.0.lock().unwrap();
        queue.work = None;
        queue
            .in_flight
            .as_ref()
            .is_some_and(|(_, _, cancel)| !cancel.swap(true, Ordering::Relaxed))
    }
}

impl Drop for Worker {
    fn drop(&mut self) {
        let (lock, ready) = &*self.queue;
        if let Ok(mut queue) = lock.lock() {
            queue.closed = true;
            queue.work = None;
            if let Some((_, _, cancel)) = &queue.in_flight {
                cancel.store(true, Ordering::Relaxed);
            }
        }
        ready.notify_all();
    }
}

fn run_worker(queue: &(Mutex<Queue>, Condvar), results: &mpsc::Sender<TileResult>) {
    let (lock, ready) = queue;
    loop {
        let (epoch, identity, key, job, presenter, retain_fallback, wake, cancel) = {
            let mut guard = lock.lock().unwrap();
            loop {
                if guard.closed {
                    return;
                }
                if let Some(work) = guard.work.as_mut()
                    && let Some(key) = work.tiles.pop_front()
                {
                    let cancel = Arc::new(AtomicBool::new(false));
                    let picked = (
                        work.epoch,
                        work.identity,
                        key,
                        work.job.clone(),
                        work.presenter.clone(),
                        work.retain_fallback,
                        work.wake.clone(),
                        Arc::clone(&cancel),
                    );
                    guard.in_flight = Some((work.identity, key, cancel));
                    break picked;
                }
                guard = ready.wait(guard).unwrap();
            }
        };
        let image = job.image(false);
        let source = [image.width, image.height];
        let outcome = std::panic::catch_unwind(AssertUnwindSafe(|| {
            prepare_covered(
                image,
                job.recipe(),
                key.request(source),
                &cancel,
                presenter.as_ref(),
                (identity.hdr, retain_fallback, key.stride == 1),
                job.coverage(),
            )
        }));
        {
            let mut guard = lock.lock().unwrap();
            if guard
                .in_flight
                .as_ref()
                .is_some_and(|(_, _, current)| Arc::ptr_eq(current, &cancel))
            {
                guard.in_flight = None;
            }
        }
        let result = TileResult {
            epoch,
            identity,
            key,
            source,
            cancelled: cancel.load(Ordering::Relaxed),
            outcome: match outcome {
                Ok(Ok(prepared)) => Ok(prepared),
                Ok(Err(error)) => Err(format!("{error:#}")),
                Err(_) => Err("Photo detail worker stopped before publishing its result".into()),
            },
        };
        if results.send(result).is_err() {
            return;
        }
        // A nonzero delay avoids egui's extra immediate pass.
        request_paced_repaint(&wake, Duration::from_millis(1));
    }
}

#[derive(Default)]
pub(super) struct ViewportRefinement {
    pub presenter: Option<PhotoPresenter>,
    /// Develop's HDR/SDR switch: present an HDR photograph as SDR.
    pub prefer_sdr: bool,
    paint: Option<PhotoPaint>,
    /// The published overview's identity; every cached tile shares it.
    identity: Option<Identity>,
    /// The current identity and when it was first seen: detail waits for a
    /// recipe to rest (a slider drag changes it every frame).
    seen: Option<(Identity, Instant)>,
    desired: Option<Demand>,
    /// The last change of detail level (zoom), which must settle.
    since: Option<Instant>,
    worker: Option<Worker>,
    tiles: HashMap<TileKey, Tile>,
    /// The other display state's tiles over the view, painted beneath this
    /// state's until they cover it (see `carry`). Not in the cache budget:
    /// at most the view's tiles, for one tile generation.
    carried: Vec<TilePaint>,
    /// Posted to the worker and not yet returned, for `posted`'s identity.
    outstanding: HashSet<TileKey>,
    posted: Option<(Identity, Vec<TileKey>)>,
    failed: HashSet<TileKey>,
    /// Pixels waiting for an egui texture (no presenter: offscreen, tests).
    staged: VecDeque<(TileKey, [u32; 2], PreparedPhoto)>,
    /// When the view began to need tiles it does not have.
    wanting: Option<Instant>,
    epoch: u64,
    frame: u64,
    dirty: bool,
    jobs: u64,
    cancellations: u64,
    reuses: u64,
    evictions: u64,
    source_samples: u64,
    rendered_pixels: u64,
    peak_bytes: u64,
    last_ms: f64,
    last_sharp_ms: Option<f64>,
    last_publication_ms: f64,
    max_publication_ms: f64,
    last_error: Option<String>,
    export: export::ExportView,
    /// The device's texture limit, from the latest demand.
    max_side: u32,
    /// Tests shrink the cache budget; `None` is `CACHE_BYTES`.
    #[cfg(test)]
    budget: Option<u64>,
}

impl ViewportRefinement {
    fn cache_budget(&self) -> u64 {
        #[cfg(test)]
        if let Some(budget) = self.budget {
            return budget;
        }
        CACHE_BYTES
    }
    pub fn reset(&mut self) {
        self.export.reset();
        self.cancel();
        self.paint = None;
        self.identity = None;
        self.seen = None;
        self.desired = None;
        self.since = None;
        self.clear_tiles();
        self.last_error = None;
    }
    fn cancel(&mut self) {
        let stopped = self.worker.as_ref().is_some_and(Worker::stop);
        if stopped || !self.outstanding.is_empty() {
            self.cancellations += 1;
        }
        self.outstanding.clear();
        self.posted = None;
    }
    fn clear_tiles(&mut self) {
        self.epoch += 1;
        self.tiles.clear();
        self.carried.clear();
        self.staged.clear();
        self.failed.clear();
        self.wanting = None;
        self.dirty = true;
    }
    pub fn publish_overview(
        &mut self,
        ctx: &egui::Context,
        id: Identity,
        image: PreparedPhoto,
    ) -> TextureHandle {
        let publication = Instant::now();
        let carried = self.carry(id);
        self.cancel();
        // Tiles of another recipe generation can never be shown again.
        self.clear_tiles();
        self.carried = carried;
        let texture = ctx.load_texture(
            "developed-overview",
            image.sdr.expect("Overview includes its SDR fallback"),
            egui::TextureOptions::LINEAR,
        );
        self.last_error = image.upload_error;
        self.paint = Some(PhotoPaint {
            overview: texture.clone(),
            presenter: self.presenter.clone(),
            layer: image.layer,
            tiles: Arc::default(),
            hdr: id.hdr,
            progress: None,
            export: None,
        });
        self.identity = Some(id);
        self.last_ms = image.elapsed_ms;
        self.source_samples += image.source_samples;
        self.record_publication(publication);
        ctx.request_repaint();
        texture
    }
    pub fn paint(&self) -> Option<PhotoPaint> {
        self.paint.clone()
    }
    /// A new identity that differs only in HDR is the same development for
    /// the other display state (Windows HDR switched, the window moved to
    /// another display, Develop's HDR/SDR switch). The tiles shown over the
    /// view stay painted beneath the new state's tiles until those cover it,
    /// so the view never falls back to the overview while they develop.
    fn carry(&self, id: Identity) -> Vec<TilePaint> {
        let (Some(old), Some(paint), Some(demand)) = (self.identity, &self.paint, self.desired)
        else {
            return Vec::new();
        };
        if old.hdr == id.hdr
            || (Identity { hdr: id.hdr, ..old }) != id
            || !self
                .presenter
                .as_ref()
                .is_some_and(PhotoPresenter::fits_float_to_sdr)
        {
            return Vec::new();
        }
        paint
            .tiles
            .iter()
            .filter(|t| t.layer.is_some() && t.core.intersects(demand.aperture))
            .cloned()
            .collect()
    }
    /// Carried tiles go once this state's own detail covers the view.
    fn drop_carried(&mut self, now: Instant) {
        if self.carried.is_empty() {
            return;
        }
        let covered = self.desired.is_none_or(|demand| {
            self.overview_enough(&demand)
                || demand.keys(demand.visible).all(|k| {
                    self.tiles
                        .get(&k)
                        .is_some_and(|t| now.saturating_duration_since(t.published) >= REVEAL)
                })
        });
        if covered {
            self.carried.clear();
            self.dirty = true;
        }
    }
    fn record_publication(&mut self, start: Instant) {
        self.last_publication_ms = start.elapsed().as_secs_f64() * 1000.0;
        self.max_publication_ms = self.max_publication_ms.max(self.last_publication_ms);
    }
    fn overview_enough(&self, demand: &Demand) -> bool {
        self.paint
            .as_ref()
            .is_some_and(|p| demand.overview_enough(p.overview.size()))
    }
    fn has(&self, key: &TileKey) -> bool {
        self.tiles.contains_key(key) || self.staged.iter().any(|(k, ..)| k == key)
    }
    /// The keys neither present nor failed, in their given order.
    fn missing(&self, keys: impl IntoIterator<Item = TileKey>) -> Vec<TileKey> {
        keys.into_iter()
            .filter(|k| !self.has(k) && !self.failed.contains(k))
            .collect()
    }
    pub fn settled(&self) -> bool {
        if !self.outstanding.is_empty() || !self.staged.is_empty() {
            return false;
        }
        if let Some(id) = self.identity
            && !self.export.settled(id)
        {
            return false;
        }
        if let (Some(id), Some(demand)) = (self.identity, self.desired)
            && self
                .export
                .paint(id)
                .is_some_and(|export| export.covers(demand.aperture))
        {
            return true;
        }
        let Some(demand) = self.desired else {
            return true;
        };
        let Some(paint) = &self.paint else {
            return false;
        };
        if !self.overview_enough(&demand) && !self.missing(demand.keys(demand.visible)).is_empty() {
            return false;
        }
        let now = Instant::now();
        paint
            .tiles
            .iter()
            .filter(|t| t.core.intersect(demand.aperture).is_positive())
            .all(|t| now.saturating_duration_since(t.published) >= REVEAL)
    }
    pub fn refresh_display(&mut self, ctx: &egui::Context) {
        if self.presenter.as_mut().is_some_and(|p| p.poll()) {
            ctx.request_repaint();
        }
    }
    pub fn hdr_active(&self, origin: strehl_edit::ImageOrigin) -> bool {
        !self.prefer_sdr && self.hdr_available(origin)
    }

    /// The display can present this photograph in HDR, switched on or not.
    pub fn hdr_available(&self, origin: strehl_edit::ImageOrigin) -> bool {
        origin == strehl_edit::ImageOrigin::SceneLinear
            && self.presenter.as_ref().is_some_and(|p| p.status().active)
    }

    pub fn demand(
        &mut self,
        source: [u32; 2],
        mapping: (Rect, Rect),
        pixels_per_point: f32,
        max_side: u32,
    ) {
        let (full, visible) = mapping;
        if !full.is_positive() || !visible.is_positive() || !pixels_per_point.is_finite() {
            self.desired = None;
            return;
        }
        let uv = |p: Pos2| {
            Pos2::ZERO + ((p - full.min) / full.size()).clamp(Vec2::ZERO, Vec2::splat(1.0))
        };
        let aperture = Rect::from_min_max(uv(visible.min), uv(visible.max));
        let physical = [
            (visible.width() * pixels_per_point).ceil().max(1.0) as u32,
            (visible.height() * pixels_per_point).ceil().max(1.0) as u32,
        ];
        let Some(stride) = target_stride(source, aperture, physical) else {
            self.desired = None;
            return;
        };
        // Tiles and their apron stay within the device's texture limit.
        self.max_side = max_side;
        let side = TILE.min(max_side.saturating_sub(2)).max(16);
        let next = Demand {
            aperture,
            physical,
            source,
            stride,
            side,
            visible: tile_range(source, aperture, stride, side),
        };
        match self.desired {
            Some(previous) if previous.stride == next.stride && previous.side == next.side => {
                if previous.visible != next.visible {
                    // A pan onto tiles already cached (the prefetch ring).
                    self.reuses += next
                        .keys(next.visible)
                        .filter(|k| !previous.shows(k) && self.tiles.contains_key(k))
                        .count() as u64;
                }
            }
            _ => {
                // A new level waits for the zoom to rest.
                self.since = Some(Instant::now());
                self.dirty = true;
            }
        }
        self.desired = Some(next);
    }

    pub fn poll_job(
        &mut self,
        ctx: &egui::Context,
        job: Option<DevelopmentJob>,
        current: Identity,
    ) {
        self.frame += 1;
        let now = Instant::now();
        if self.seen.is_none_or(|(id, _)| id != current) {
            self.seen = Some((current, now));
        }
        if self.posted.as_ref().is_some_and(|(id, _)| *id != current) {
            self.cancel();
        }
        self.receive(current);
        self.upload_staged(ctx);
        let ready = self.identity == Some(current);
        self.export.poll(
            ctx,
            job.as_ref().filter(|_| ready && !current.before),
            current,
            self.seen.map_or(Duration::ZERO, |(_, at)| now - at),
            self.presenter.as_ref(),
            self.max_side,
        );
        let exported = self
            .export
            .paint(current)
            .zip(self.desired)
            .is_some_and(|(export, demand)| export.covers(demand.aperture));
        let mut wanted = Vec::new();
        let mut waiting = None;
        let planning = self
            .desired
            .filter(|demand| job.is_some() && ready && !exported && !self.overview_enough(demand));
        if planning.is_none() {
            self.wanting = None;
        }
        if let Some(demand) = planning {
            for key in demand.keys(demand.ring()) {
                if let Some(tile) = self.tiles.get_mut(&key) {
                    tile.used = self.frame;
                }
            }
            let visible = self.missing(demand.ordered(demand.keys(demand.visible).collect()));
            if visible.is_empty() {
                if let Some(at) = self.wanting.take() {
                    self.last_sharp_ms = Some((now - at).as_secs_f64() * 1000.0);
                }
            } else if self.wanting.is_none() {
                self.wanting = Some(now);
            }
            let since = self.since.map_or(Duration::MAX, |at| now - at);
            let rested = self.seen.map_or(Duration::ZERO, |(_, at)| now - at);
            let settle = SETTLE.saturating_sub(since.min(rested));
            if settle.is_zero() {
                wanted = visible;
                // Prefetch the ring only within the cache's budget.
                let budget = self.view_bytes(&demand) + self.cache_budget();
                let tile_bytes = u64::from(demand.side + 2).pow(2) * self.tile_texel_bytes(current);
                let mut projected = self.cached_bytes() + wanted.len() as u64 * tile_bytes;
                let ring = demand
                    .keys(demand.ring())
                    .filter(|k| !demand.shows(k))
                    .collect();
                for key in self.missing(demand.ordered(ring)) {
                    if projected + tile_bytes > budget {
                        break;
                    }
                    projected += tile_bytes;
                    wanted.push(key);
                }
            } else if !visible.is_empty() {
                waiting = Some(settle);
            }
        }
        if wanted.is_empty() {
            if !self.outstanding.is_empty() {
                // Nothing queued is wanted now (a new level, or the export
                // preview covers the view).
                self.cancel();
            }
        } else if self.posted.as_ref() != Some(&(current, wanted.clone()))
            && let Some(job) = job
        {
            self.post(ctx, job, current, wanted);
        }
        self.evict();
        if ready {
            self.drop_carried(now);
        }
        self.refresh_paint(now);
        if let Some(remaining) = waiting {
            request_paced_repaint(
                ctx,
                if remaining.is_zero() {
                    FRAME_DELAY
                } else {
                    remaining
                },
            );
        }
        if !self.staged.is_empty() {
            ctx.request_repaint();
        }
    }

    fn post(
        &mut self,
        ctx: &egui::Context,
        job: DevelopmentJob,
        identity: Identity,
        tiles: Vec<TileKey>,
    ) {
        if self.worker.is_none() {
            match Worker::start() {
                Ok(worker) => self.worker = Some(worker),
                Err(error) => {
                    // Without a worker the overview stays; never retry per frame.
                    self.last_error = Some(format!("Starting photo detail work: {error}"));
                    self.failed.extend(tiles);
                    return;
                }
            }
        }
        let cancelled = self.worker.as_ref().unwrap().post(Work {
            epoch: self.epoch,
            identity,
            job,
            presenter: self.presenter.clone(),
            retain_fallback: self.presenter.is_none(),
            wake: ctx.clone(),
            tiles: tiles.iter().copied().collect(),
        });
        if cancelled {
            self.cancellations += 1;
        }
        self.outstanding = tiles.iter().copied().collect();
        self.posted = Some((identity, tiles));
    }

    fn receive(&mut self, current: Identity) {
        let Some(worker) = &self.worker else {
            return;
        };
        let results = worker.results.try_iter().collect::<Vec<_>>();
        for result in results {
            if self
                .posted
                .as_ref()
                .is_some_and(|(id, _)| *id == result.identity)
            {
                self.outstanding.remove(&result.key);
            }
            if result.cancelled
                || result.epoch != self.epoch
                || result.identity != current
                || self.identity != Some(current)
            {
                continue;
            }
            match result.outcome {
                Ok(image) => {
                    self.jobs += 1;
                    self.last_ms = image.elapsed_ms;
                    self.source_samples += image.source_samples;
                    self.rendered_pixels += u64::from(image.size[0]) * u64::from(image.size[1]);
                    if let Some(error) = image.upload_error {
                        self.last_error = Some(error);
                        self.failed.insert(result.key);
                    } else if image.layer.is_some() {
                        let publication = Instant::now();
                        self.insert(result.key, result.source, image, None);
                        self.record_publication(publication);
                    } else {
                        self.staged.push_back((result.key, result.source, image));
                    }
                }
                Err(error) => {
                    self.failed.insert(result.key);
                    self.last_error = Some(error);
                }
            }
        }
    }

    fn upload_staged(&mut self, ctx: &egui::Context) {
        for _ in 0..FALLBACK_UPLOADS {
            let Some((key, source, mut image)) = self.staged.pop_front() else {
                break;
            };
            let publication = Instant::now();
            let texture = image.sdr.take().map(|sdr| {
                ctx.load_texture(
                    "developed-detail",
                    sdr,
                    egui::TextureOptions {
                        magnification: if key.stride == 1 {
                            egui::TextureFilter::Nearest
                        } else {
                            egui::TextureFilter::Linear
                        },
                        ..egui::TextureOptions::LINEAR
                    },
                )
            });
            self.insert(key, source, image, texture);
            self.record_publication(publication);
        }
    }

    fn insert(
        &mut self,
        key: TileKey,
        source: [u32; 2],
        image: PreparedPhoto,
        texture: Option<TextureHandle>,
    ) {
        let Some(id) = self.identity else {
            return;
        };
        let bytes = u64::from(image.size[0]) * u64::from(image.size[1]) * self.tile_texel_bytes(id);
        self.tiles.insert(
            key,
            Tile {
                request: key.request(source),
                core: key.core_uv(source),
                uv: Rect::from_min_max(Pos2::from(image.uv[0]), Pos2::from(image.uv[1])),
                size: image.size,
                texture,
                layer: image.layer,
                bytes,
                published: Instant::now(),
                used: self.frame,
            },
        );
        self.peak_bytes = self.peak_bytes.max(self.cached_bytes());
        self.dirty = true;
    }

    /// Bytes per texel of a tile: its GPU texture, plus the CPU copy egui
    /// keeps of its own textures when no presenter uploads them.
    fn tile_texel_bytes(&self, id: Identity) -> u64 {
        texel_bytes(id) + if self.presenter.is_none() { 4 } else { 0 }
    }
    fn cached_bytes(&self) -> u64 {
        self.tiles.values().map(|t| t.bytes).sum()
    }
    fn view_bytes(&self, demand: &Demand) -> u64 {
        demand
            .keys(demand.visible)
            .filter_map(|k| self.tiles.get(&k))
            .map(|t| t.bytes)
            .sum()
    }

    /// Least recently wanted first, never a tile the view shows.
    fn evict(&mut self) {
        let Some(demand) = self.desired else {
            return;
        };
        let budget = self.view_bytes(&demand) + self.cache_budget();
        let mut total = self.cached_bytes();
        if total <= budget {
            return;
        }
        let mut candidates = self
            .tiles
            .iter()
            .filter(|(k, _)| !demand.shows(k))
            .map(|(k, t)| (t.used, *k, t.bytes))
            .collect::<Vec<_>>();
        candidates.sort_unstable_by_key(|(used, ..)| *used);
        for (_, key, bytes) in candidates {
            if total <= budget {
                break;
            }
            self.tiles.remove(&key);
            total -= bytes;
            self.evictions += 1;
            self.dirty = true;
        }
    }

    fn refresh_paint(&mut self, now: Instant) {
        // Only while the view itself lacks detail, and not for quick work.
        let progress = self.desired.and_then(|demand| {
            let pending = self.wanting.is_some_and(|at| now - at >= QUIET);
            pending.then(|| {
                let total = demand.keys(demand.visible).count().max(1);
                let missing = self.missing(demand.keys(demand.visible)).len();
                (total - missing.min(total)) as f32 / total as f32
            })
        });
        let progress = progress.or_else(|| self.export.progress());
        let export = self.identity.and_then(|id| self.export.paint(id));
        let Some(paint) = &mut self.paint else {
            return;
        };
        paint.progress = progress;
        paint.export = export;
        if !std::mem::take(&mut self.dirty) {
            return;
        }
        // The wanted level, coarser levels while it arrives, and one finer
        // level just zoomed out of: never minified by more than 2x. Tiles
        // carried from the other display state come first, so this state's
        // tiles of the same level are painted (and fade in) over them; the
        // sort is stable.
        let stride = self.desired.map_or(1, |d| d.stride);
        let mut tiles = self.carried.clone();
        tiles.extend(
            self.tiles
                .iter()
                .filter(|(k, _)| k.stride * 2 >= stride && k.stride <= stride * 8)
                .map(|(k, t)| TilePaint {
                    stride: k.stride,
                    core: t.core,
                    uv: t.uv,
                    size: t.size,
                    texture: t.texture.clone(),
                    layer: t.layer.clone(),
                    published: t.published,
                }),
        );
        tiles.sort_by_key(|t| std::cmp::Reverse(t.stride));
        paint.tiles = Arc::new(tiles);
    }

    /// Export: the preset's request, or `None` on Develop.
    pub fn want_export(&mut self, request: Option<ExportRequest>) {
        self.export.want(request);
    }
    /// Output pixels per source pixel while the export's own pixels show.
    pub fn export_scale(&self) -> Option<f32> {
        self.identity.and_then(|id| self.export.output_scale(id))
    }
    /// The shown export already contains its burned-in scale bar.
    pub fn export_burns_scale_bar(&self) -> bool {
        self.identity
            .is_some_and(|id| self.export.burns_scale_bar(id))
    }

    pub fn stats(&self) -> serde_json::Value {
        let rect = |r: Rect| [[r.min.x, r.min.y], [r.max.x, r.max.y]];
        // Published: detail at the wanted level covering the whole view.
        let published = self.desired.and_then(|demand| {
            if !self.missing(demand.keys(demand.visible)).is_empty() {
                return None;
            }
            let tiles = self
                .tiles
                .iter()
                .filter(|(k, t)| k.stride == demand.stride && t.core.intersects(demand.aperture))
                .map(|(_, t)| t)
                .collect::<Vec<_>>();
            let first = tiles.first()?;
            let (uv, min, max) = tiles.iter().fold(
                (first.core, first.request.min, first.request.max),
                |(uv, min, max), t| {
                    (
                        uv.union(t.core),
                        [min[0].min(t.request.min[0]), min[1].min(t.request.min[1])],
                        [max[0].max(t.request.max[0]), max[1].max(t.request.max[1])],
                    )
                },
            );
            let pixels = [0, 1].map(|i| (max[i] - min[i]).div_ceil(demand.stride));
            Some(serde_json::json!({
                "uv":rect(uv), "pixels":pixels, "stride":demand.stride, "tiles":tiles.len(),
                "revision":self.identity.map(|i|i.revision),"before":self.identity.map(|i|i.before)
            }))
        });
        serde_json::json!({
            "requested": self.desired.map(|d| serde_json::json!({
                "uv":rect(d.aperture),"physical_pixels":d.physical,"stride":d.stride,
                "tiles":d.keys(d.visible).count(),"overview_enough":self.overview_enough(&d)
            })),
            "published": published,
            "jobs":self.jobs,"cancelled":self.cancellations,"cache_reuses":self.reuses,
            "tiles_cached":self.tiles.len(),"tiles_carried":self.carried.len(),"cache_bytes":self.cached_bytes(),
            "peak_cache_bytes":self.peak_bytes,"evictions":self.evictions,
            "failed_tiles":self.failed.len(),
            "source_samples":self.source_samples,"refined_pixels":self.rendered_pixels,
            "last_development_ms":self.last_ms,"last_sharp_ms":self.last_sharp_ms,
            "last_publication_ms":self.last_publication_ms,"max_publication_ms":self.max_publication_ms,
            "pending":!self.outstanding.is_empty(),
            "settled":self.settled(),
            "last_error":self.last_error,
            "hdr_pixels":self.identity.is_some_and(|id|id.hdr),
            "export":self.identity.map(|id| self.export.stats(id)),
            "display":self.presenter.as_ref().map(|p|p.status())
        })
    }
}

fn texel_bytes(id: Identity) -> u64 {
    if id.hdr { 16 } else { 4 }
}

#[cfg(test)]
#[path = "photo-viewport-tests.rs"]
mod tests;

#[cfg(test)]
#[path = "photo-viewport-bench.rs"]
mod bench;

#[cfg(test)]
#[path = "photo-viewport-hdr-tests.rs"]
mod hdr_tests;
