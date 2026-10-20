//! One retained overview and one bounded, source-registered detail patch.
//! Pointer motion only changes geometry; workers develop the latest demand.
use crate::{
    hdr_display::{FloatPhoto, PhotoLayer, PhotoPresenter},
    jobs::{Task, spawn_task},
};
use eframe::egui::{self, Color32, Pos2, Rect, TextureHandle, Vec2};
use std::{
    sync::Arc,
    time::{Duration, Instant},
};
use strehl_edit::{DevelopmentRecipe, DisplayRegionRequest, LinearImage};

const MAX_PATCH_SIDE: u32 = 3072;
const MAX_PATCH_PIXELS: u64 = 6 * 1024 * 1024;
const SETTLE: Duration = Duration::from_millis(80);
const REVEAL: Duration = Duration::from_millis(120);

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(super) struct Identity {
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

pub(super) fn prepare(
    source: &LinearImage,
    recipe: &DevelopmentRecipe,
    request: DisplayRegionRequest,
    cancelled: &std::sync::atomic::AtomicBool,
    presenter: Option<&PhotoPresenter>,
    hdr: bool,
    retain_fallback: bool,
) -> anyhow::Result<PreparedPhoto> {
    let start = Instant::now();
    let image = source.render_display_region_mode(recipe, request, cancelled, hdr)?;
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
            presenter.upload_sdr(image.size, rgba.into(), uv)
        }
    });
    anyhow::ensure!(
        !cancelled.load(std::sync::atomic::Ordering::Relaxed),
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

#[derive(Clone)]
struct Patch {
    request: DisplayRegionRequest,
    texture: Option<TextureHandle>,
    size: [u32; 2],
    layer: Option<PhotoLayer>,
    uv: Rect,
    published: Instant,
}

/// Immutable geometry/pixel generation passed to the photograph painter.
#[derive(Clone)]
pub(crate) struct PhotoPaint {
    overview: TextureHandle,
    presenter: Option<PhotoPresenter>,
    layer: Option<PhotoLayer>,
    detail: Option<Patch>,
    hdr: bool,
}

impl PhotoPaint {
    pub(crate) fn paint(&self, painter: &egui::Painter, destination: Rect, aperture: Rect) {
        let opacity = self.detail.as_ref().map_or(0.0, |patch| {
            (patch.published.elapsed().as_secs_f32() / REVEAL.as_secs_f32()).clamp(0.0, 1.0)
        });
        if opacity > 0.0 && opacity < 1.0 {
            painter.ctx().request_repaint();
        }
        if let (Some(presenter), Some(overview)) = (&self.presenter, &self.layer) {
            let detail = self
                .detail
                .as_ref()
                .and_then(|p| p.layer.as_ref())
                .map(|p| (p, opacity));
            let painted = if self.hdr {
                presenter.paint(painter, destination, aperture, overview, detail)
            } else {
                presenter.paint_sdr(painter, destination, aperture, overview, detail)
            };
            if painted {
                return;
            }
        }
        painter.image(self.overview.id(), destination, aperture, Color32::WHITE);
        if let Some(patch) = &self.detail
            && let Some(texture) = &patch.texture
        {
            let shared = aperture.intersect(patch.uv);
            if shared.is_positive() {
                let project = |p: Pos2| {
                    destination.min + (p - aperture.min) / aperture.size() * destination.size()
                };
                let local = |p: Pos2| Pos2::ZERO + (p - patch.uv.min) / patch.uv.size();
                painter.image(
                    texture.id(),
                    Rect::from_min_max(project(shared.min), project(shared.max)),
                    Rect::from_min_max(local(shared.min), local(shared.max)),
                    Color32::WHITE.gamma_multiply(opacity),
                );
            }
        }
    }
}

#[derive(Clone, Copy)]
struct Demand {
    aperture: Rect,
    physical: [u32; 2],
    source: [u32; 2],
    request: DisplayRegionRequest,
}

struct Pending {
    identity: Identity,
    request: DisplayRegionRequest,
    task: Task<PreparedPhoto>,
}

#[derive(Default)]
pub(super) struct ViewportRefinement {
    pub presenter: Option<PhotoPresenter>,
    paint: Option<PhotoPaint>,
    identity: Option<Identity>,
    desired: Option<Demand>,
    since: Option<Instant>,
    pending: Option<Pending>,
    failed: Option<(Identity, DisplayRegionRequest)>,
    jobs: u64,
    cancellations: u64,
    reuses: u64,
    source_samples: u64,
    rendered_pixels: u64,
    last_ms: f64,
    last_publication_ms: f64,
    max_publication_ms: f64,
    last_error: Option<String>,
}

impl ViewportRefinement {
    pub fn reset(&mut self) {
        self.cancel();
        self.paint = None;
        self.identity = None;
        self.desired = None;
        self.since = None;
        self.failed = None;
        self.last_error = None;
    }
    fn cancel(&mut self) {
        if let Some(pending) = &self.pending
            && !pending.task.is_cancelled()
        {
            pending.task.cancel();
            self.cancellations += 1;
        }
    }
    pub fn publish_overview(
        &mut self,
        ctx: &egui::Context,
        id: Identity,
        image: PreparedPhoto,
    ) -> TextureHandle {
        let publication = Instant::now();
        self.cancel();
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
            detail: None,
            hdr: id.hdr,
        });
        self.identity = Some(id);
        self.failed = None;
        self.last_ms = image.elapsed_ms;
        self.source_samples += image.source_samples;
        self.record_publication(publication);
        ctx.request_repaint();
        texture
    }
    pub fn paint(&self) -> Option<PhotoPaint> {
        self.paint.clone()
    }
    fn record_publication(&mut self, start: Instant) {
        self.last_publication_ms = start.elapsed().as_secs_f64() * 1000.0;
        self.max_publication_ms = self.max_publication_ms.max(self.last_publication_ms);
    }
    pub fn settled(&self) -> bool {
        if self.pending.is_some() {
            return false;
        }
        let Some(demand) = self.desired else {
            return true;
        };
        if self.failed.is_some() && self.failed == self.identity.map(|id| (id, demand.request)) {
            return true;
        }
        let Some(paint) = &self.paint else {
            return false;
        };
        let size = paint.overview.size();
        let overview_enough =
            (0..2).all(|i| size[i] as u32 >= demand.source[i].div_ceil(demand.request.stride));
        let detail_enough = paint.detail.as_ref().is_some_and(|p| {
            covers(
                p.request,
                demand.source,
                demand.aperture,
                demand.request.stride,
            )
        });
        (overview_enough || detail_enough)
            && paint
                .detail
                .as_ref()
                .is_none_or(|p| p.published.elapsed() >= REVEAL)
    }
    pub fn refresh_display(&mut self, ctx: &egui::Context) {
        if self.presenter.as_mut().is_some_and(|p| p.poll()) {
            ctx.request_repaint();
        }
    }
    pub fn hdr_active(&self, origin: strehl_edit::ImageOrigin) -> bool {
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
        // A non-native renderer still gets bounded refinement, with a smaller
        // texture-transfer ceiling. The production wgpu path uploads off-thread.
        let max_side = if self.presenter.is_some() {
            max_side
        } else {
            max_side.min(1024)
        };
        let Some(request) = plan(source, aperture, physical, max_side) else {
            self.desired = None;
            return;
        };
        if self
            .desired
            .is_none_or(|previous| previous.request != request)
        {
            self.since = Some(Instant::now());
            if self
                .pending
                .as_ref()
                .is_some_and(|pending| !covers(pending.request, source, aperture, request.stride))
            {
                self.cancel();
            }
            if self
                .paint
                .as_ref()
                .and_then(|p| p.detail.as_ref())
                .is_some_and(|p| covers(p.request, source, aperture, request.stride))
            {
                self.reuses += 1;
            }
        }
        self.desired = Some(Demand {
            aperture,
            physical,
            source,
            request,
        });
    }

    pub fn poll(
        &mut self,
        ctx: &egui::Context,
        source: Option<Arc<LinearImage>>,
        recipe: &DevelopmentRecipe,
        current: Identity,
    ) {
        if self
            .pending
            .as_ref()
            .is_some_and(|pending| pending.identity != current)
        {
            self.cancel();
        }
        if let Some(pending) = &self.pending {
            let result = pending.task.receiver.try_recv();
            if !matches!(result, Err(std::sync::mpsc::TryRecvError::Empty)) {
                let pending = self.pending.take().unwrap();
                if let Ok(result) = result
                    && pending.identity == current
                    && self.identity == Some(current)
                {
                    match result {
                        Ok(image) if !pending.task.is_cancelled() => {
                            let publication = Instant::now();
                            let uv = Rect::from_min_max(
                                Pos2::from(image.uv[0]),
                                Pos2::from(image.uv[1]),
                            );
                            self.last_ms = image.elapsed_ms;
                            self.source_samples += image.source_samples;
                            self.rendered_pixels +=
                                u64::from(image.size[0]) * u64::from(image.size[1]);
                            if let Some(error) = image.upload_error {
                                self.last_error = Some(error);
                                self.failed = Some((current, pending.request));
                                return;
                            }
                            let texture = image.sdr.map(|sdr| {
                                ctx.load_texture(
                                    "developed-detail",
                                    sdr,
                                    egui::TextureOptions::LINEAR,
                                )
                            });
                            if let Some(paint) = &mut self.paint {
                                paint.detail = Some(Patch {
                                    request: pending.request,
                                    texture,
                                    size: image.size,
                                    layer: image.layer,
                                    uv,
                                    published: Instant::now(),
                                });
                            }
                            self.record_publication(publication);
                            ctx.request_repaint();
                        }
                        Err(error) => {
                            self.failed = Some((current, pending.request));
                            self.last_error = Some(error);
                        }
                        _ => {}
                    }
                }
            }
        }
        if let (Some(demand), Some(source)) = (self.desired, source) {
            let overview_enough = self.paint.as_ref().is_some_and(|p| {
                let size = p.overview.size();
                size[0] as u32 >= source.width.div_ceil(demand.request.stride)
                    && size[1] as u32 >= source.height.div_ceil(demand.request.stride)
            });
            let already = overview_enough
                || self
                    .paint
                    .as_ref()
                    .and_then(|p| p.detail.as_ref())
                    .is_some_and(|patch| {
                        covers(
                            patch.request,
                            [source.width, source.height],
                            demand.aperture,
                            demand.request.stride,
                        )
                    });
            let settled = self.since.is_some_and(|at| at.elapsed() >= SETTLE);
            if self.presenter.is_some()
                && self.last_error.is_some()
                && self.paint.as_ref().is_some_and(|p| p.layer.is_none())
            {
                self.failed = Some((current, demand.request));
            }
            if self.pending.is_none()
                && !already
                && settled
                && self.identity == Some(current)
                && self.failed != Some((current, demand.request))
            {
                let recipe = recipe.clone();
                let request = demand.request;
                let presenter = self.presenter.clone();
                self.jobs += 1;
                self.pending = Some(Pending {
                    identity: current,
                    request,
                    task: spawn_task("strehl-photo-detail", move |cancelled| {
                        prepare(
                            &source,
                            &recipe,
                            request,
                            &cancelled,
                            presenter.as_ref(),
                            current.hdr,
                            false,
                        )
                    }),
                });
            }
            if !already && self.failed != Some((current, demand.request)) {
                ctx.request_repaint_after(Duration::from_millis(16));
            }
        }
        if self.pending.is_some() {
            ctx.request_repaint_after(Duration::from_millis(16));
        }
    }

    pub fn stats(&self) -> serde_json::Value {
        let rect = |r: Rect| [[r.min.x, r.min.y], [r.max.x, r.max.y]];
        serde_json::json!({
            "requested": self.desired.map(|d| serde_json::json!({"uv":rect(d.aperture),"physical_pixels":d.physical,"stride":d.request.stride})),
            "published": self.paint.as_ref().and_then(|p| p.detail.as_ref()).map(|p| serde_json::json!({
                "uv":rect(p.uv), "pixels":p.size, "stride":p.request.stride,
                "revision":self.identity.map(|i|i.revision),"before":self.identity.map(|i|i.before)
            })),
            "jobs":self.jobs,"cancelled":self.cancellations,"cache_reuses":self.reuses,
            "source_samples":self.source_samples,"refined_pixels":self.rendered_pixels,"last_development_ms":self.last_ms,
            "last_publication_ms":self.last_publication_ms,"max_publication_ms":self.max_publication_ms,
            "pending":self.pending.is_some(),
            "settled":self.settled(),
            "last_error":self.last_error,
            "hdr_pixels":self.identity.is_some_and(|id|id.hdr),
            "display":self.presenter.as_ref().map(|p|p.status())
        })
    }
}

fn covers(request: DisplayRegionRequest, source: [u32; 2], aperture: Rect, stride: u32) -> bool {
    request.stride <= stride
        && (0..2).all(|i| {
            request.min[i] as f32 <= aperture.min[i] * source[i] as f32 + 0.01
                && request.max[i] as f32 >= aperture.max[i] * source[i] as f32 - 0.01
        })
}

fn plan(
    source: [u32; 2],
    aperture: Rect,
    physical: [u32; 2],
    max_side: u32,
) -> Option<DisplayRegionRequest> {
    if source.contains(&0) || !aperture.is_positive() || !aperture.is_finite() {
        return None;
    }
    let native = [
        aperture.width() * source[0] as f32,
        aperture.height() * source[1] as f32,
    ];
    let ratio = (native[0] / physical[0].max(1) as f32).min(native[1] / physical[1].max(1) as f32);
    let mut stride = 1u32;
    while (stride * 2) as f32 <= ratio && stride < 32768 {
        stride *= 2;
    }
    loop {
        let grid = stride * 32;
        let min = std::array::from_fn(|i| {
            let at = (aperture.min[i] * source[i] as f32 - native[i] * 0.12).max(0.0) as u32;
            at / grid * grid
        });
        let max = std::array::from_fn(|i| {
            let at = (aperture.max[i] * source[i] as f32 + native[i] * 0.12)
                .ceil()
                .min(source[i] as f32) as u32;
            at.div_ceil(grid).saturating_mul(grid).min(source[i])
        });
        let size: [u32; 2] = std::array::from_fn(|i| (max[i] - min[i]).div_ceil(stride));
        if size.iter().all(|&n| n <= max_side.clamp(1, MAX_PATCH_SIDE))
            && u64::from(size[0]) * u64::from(size[1]) <= MAX_PATCH_PIXELS
        {
            return Some(DisplayRegionRequest { min, max, stride });
        }
        stride = stride.checked_mul(2)?;
    }
}

#[cfg(test)]
#[path = "photo-viewport-tests.rs"]
mod tests;
