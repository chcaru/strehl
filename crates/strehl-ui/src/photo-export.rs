//! Export: what the selected preset will write, over the photograph.
//!
//! When the preset's stages change pixels (a resize, output sharpening, a
//! burned-in scale bar) the view shows the export's own pixels, rendered by
//! `strehl_edit::render_export_preview` from the export's staged buffer on a
//! worker, at the output's resolution and placed over its crop. Zooming past
//! the output's 100 % shows its true pixels (nearest). Otherwise the
//! development tiles already are the export's pixels and nothing is built.
use super::{Identity, QUIET, REVEAL, SETTLE, request_paced_repaint};
use crate::{
    development_job::DevelopmentJob,
    hdr_display::{PhotoLayer, PhotoPresenter},
    jobs::{Task, spawn_notifying_task},
};
use eframe::egui::{self, Color32, Pos2, Rect, TextureHandle};
use std::{
    sync::Arc,
    time::{Duration, Instant},
};
use strehl_edit::{Crop, ExportSettings};

/// Larger outputs are previewed by the development tiles instead.
const MAX_OUTPUT_PIXELS: u64 = 40 * 1024 * 1024;
/// Until a preview has been timed: the weevil's Web preset took 0.3 s.
const FIRST_ESTIMATE_MS: f64 = 400.0;

#[derive(Clone, Debug, PartialEq)]
pub(crate) struct ExportRequest {
    pub settings: ExportSettings,
    pub um_per_px: Option<f64>,
}

/// Why a wanted preview is not shown.
#[derive(Clone, Debug, PartialEq)]
enum Outcome {
    /// The export is the development: the tiles are exact.
    Development,
    /// HDR, transparent coverage, a pending repair, or a very large output.
    Unsupported(&'static str),
    Failed(String),
}

struct Prepared {
    size: [u32; 2],
    developed: [u32; 2],
    layer: Option<PhotoLayer>,
    sdr: Option<egui::ColorImage>,
    elapsed_ms: f64,
}

#[derive(Clone)]
pub(super) struct ExportPaint {
    /// Photograph-UV corners, clockwise from the output's top left.
    pub(super) corners: [Pos2; 4],
    /// Axis-aligned bounds of `corners`.
    bounds: Rect,
    pub(super) turned: bool,
    size: [u32; 2],
    pub(super) texture: Option<TextureHandle>,
    layer: Option<PhotoLayer>,
    published: Instant,
}

struct Shown {
    identity: Identity,
    request: ExportRequest,
    paint: ExportPaint,
    developed: [u32; 2],
}

#[derive(Default)]
pub(super) struct ExportView {
    pub(super) wanted: Option<(ExportRequest, Instant)>,
    task: Option<(Identity, ExportRequest, Instant, Task<Option<Prepared>>)>,
    shown: Option<Shown>,
    outcome: Option<(Identity, ExportRequest, Outcome)>,
    last_ms: Option<f64>,
    pub(super) jobs: u64,
}

impl ExportView {
    pub(super) fn want(&mut self, request: Option<ExportRequest>) {
        if self.wanted.as_ref().map(|(r, _)| r) != request.as_ref() {
            self.wanted = request.map(|r| (r, Instant::now()));
        }
    }

    /// The preview for this recipe and preset, if one is shown.
    pub(super) fn paint(&self, current: Identity) -> Option<ExportPaint> {
        let shown = self.shown.as_ref()?;
        let (wanted, _) = self.wanted.as_ref()?;
        (shown.identity == current && &shown.request == wanted).then(|| shown.paint.clone())
    }

    /// Output pixels per source pixel of the shown preview (its resize).
    pub(super) fn output_scale(&self, current: Identity) -> Option<f32> {
        let shown = self.shown.as_ref()?;
        self.paint(current)?;
        Some(shown.paint.size[0] as f32 / shown.developed[0].max(1) as f32)
    }

    pub(super) fn burns_scale_bar(&self, current: Identity) -> bool {
        self.paint(current).is_some()
            && self
                .shown
                .as_ref()
                .is_some_and(|shown| shown.request.settings.scale_bar)
    }

    /// Fraction of the expected time spent, while a slow preview is pending.
    pub(super) fn progress(&self) -> Option<f32> {
        let (_, _, started, _) = self.task.as_ref()?;
        let elapsed = started.elapsed();
        (elapsed >= QUIET).then(|| {
            let estimate = self.last_ms.unwrap_or(FIRST_ESTIMATE_MS);
            (elapsed.as_secs_f64() * 1000.0 / estimate).min(0.95) as f32
        })
    }

    /// Nothing more is coming for this recipe and preset.
    pub(super) fn settled(&self, current: Identity) -> bool {
        let Some((wanted, _)) = &self.wanted else {
            return true;
        };
        if self.task.is_some() {
            return false;
        }
        self.paint(current).is_some_and(|p| p.opacity() >= 1.0)
            || self
                .outcome
                .as_ref()
                .is_some_and(|(id, request, _)| *id == current && request == wanted)
    }

    pub(super) fn reset(&mut self) {
        if let Some((.., task)) = self.task.take() {
            task.cancel();
        }
        self.shown = None;
        self.outcome = None;
    }

    /// `job` is `None` until the current recipe's overview is published.
    pub(super) fn poll(
        &mut self,
        ctx: &egui::Context,
        job: Option<&DevelopmentJob>,
        current: Identity,
        rested: Duration,
        presenter: Option<&PhotoPresenter>,
        max_side: u32,
    ) {
        let Some((wanted, since)) = self.wanted.clone() else {
            self.reset();
            return;
        };
        if let Some((identity, request, ..)) = &self.task
            && (*identity != current || *request != wanted)
        {
            let (.., task) = self.task.take().unwrap();
            task.cancel();
        }
        if let Some((identity, request, started, task)) = &self.task
            && let Ok(result) = task.receiver.try_recv()
        {
            let _ = started;
            let (identity, request) = (*identity, request.clone());
            self.task = None;
            match result {
                Ok(Some(prepared)) => {
                    self.last_ms = Some(prepared.elapsed_ms);
                    self.jobs += 1;
                    let texture = prepared.sdr.map(|sdr| {
                        ctx.load_texture(
                            "export-preview",
                            sdr,
                            egui::TextureOptions {
                                magnification: egui::TextureFilter::Nearest,
                                ..egui::TextureOptions::LINEAR
                            },
                        )
                    });
                    let source = job.map_or([1, 1], |job| {
                        let image = job.image(false);
                        [image.width, image.height]
                    });
                    let corners = corners(job, source);
                    self.shown = Some(Shown {
                        identity,
                        request,
                        developed: prepared.developed,
                        paint: ExportPaint {
                            bounds: Rect::from_points(&corners.0),
                            corners: corners.0,
                            turned: corners.1,
                            size: prepared.size,
                            texture,
                            layer: prepared.layer,
                            published: Instant::now(),
                        },
                    });
                    ctx.request_repaint();
                }
                Ok(None) => self.outcome = Some((identity, request, Outcome::Development)),
                Err(error) => self.outcome = Some((identity, request, Outcome::Failed(error))),
            }
        }
        let settled = |outcome: &(Identity, ExportRequest, Outcome)| {
            outcome.0 == current && outcome.1 == wanted
        };
        let shown = self
            .shown
            .as_ref()
            .is_some_and(|s| s.identity == current && s.request == wanted);
        if shown || self.task.is_some() || self.outcome.as_ref().is_some_and(settled) {
            return;
        }
        // No job yet: the recipe's overview is still developing. No texture
        // limit yet: the view has not been laid out.
        let Some(job) = job.filter(|_| max_side > 0) else {
            return;
        };
        if let Some(reason) = unsupported(&wanted.settings, job, max_side) {
            self.outcome = Some((current, wanted, Outcome::Unsupported(reason)));
            return;
        }
        // Wait for the recipe and the preset choice to rest.
        let remaining = SETTLE
            .saturating_sub(rested)
            .max(SETTLE.saturating_sub(since.elapsed()));
        if !remaining.is_zero() {
            request_paced_repaint(ctx, remaining);
            return;
        }
        let job = job.clone();
        let request = wanted.clone();
        let presenter = presenter.cloned();
        let wake = ctx.clone();
        self.task = Some((
            current,
            wanted,
            Instant::now(),
            spawn_notifying_task(
                "strehl-export-preview",
                move |cancelled| prepare(&job, &request, &cancelled, presenter.as_ref()),
                move || request_paced_repaint(&wake, Duration::from_millis(1)),
            ),
        ));
    }

    pub(super) fn stats(&self, current: Identity) -> serde_json::Value {
        let outcome = self.outcome.as_ref().map(|(.., outcome)| match outcome {
            Outcome::Development => "development".to_owned(),
            Outcome::Unsupported(reason) => format!("unsupported: {reason}"),
            Outcome::Failed(error) => format!("failed: {error}"),
        });
        serde_json::json!({
            "wanted": self.wanted.is_some(),
            "shown": self.paint(current).map(|p| p.size),
            "pending": self.task.is_some(),
            "outcome": outcome,
            "jobs": self.jobs,
            "last_ms": self.last_ms,
        })
    }
}

fn unsupported(
    settings: &ExportSettings,
    job: &DevelopmentJob,
    max_side: u32,
) -> Option<&'static str> {
    if settings.hdr {
        return Some("HDR exports show the development");
    }
    if job.coverage().is_some() {
        return Some("transparent coverage shows the development");
    }
    let image = job.image(false);
    let developed = job.recipe().crop.map_or([image.width, image.height], |c| {
        c.output_size(image.width, image.height)
    });
    let output = settings
        .resize
        .and_then(|r| r.target(developed))
        .unwrap_or(developed);
    (u64::from(output[0]) * u64::from(output[1]) > MAX_OUTPUT_PIXELS
        || output.iter().any(|&n| n > max_side))
    .then_some("the output is too large to preview whole")
}

/// Photograph-UV corners of the output frame, and whether it is turned.
fn corners(job: Option<&DevelopmentJob>, source: [u32; 2]) -> ([Pos2; 4], bool) {
    let crop: Option<Crop> = job.and_then(|job| job.recipe().crop);
    let uv = |p: [f64; 2]| {
        egui::pos2(
            (p[0] / f64::from(source[0])) as f32,
            (p[1] / f64::from(source[1])) as f32,
        )
    };
    match crop {
        None => (
            [
                Pos2::ZERO,
                egui::pos2(1.0, 0.0),
                egui::pos2(1.0, 1.0),
                egui::pos2(0.0, 1.0),
            ],
            false,
        ),
        Some(crop) if crop.angle_deg == 0.0 => {
            let [x0, y0, x1, y1] = crop.pixel_rect(source[0], source[1]).map(f64::from);
            (
                [uv([x0, y0]), uv([x1, y0]), uv([x1, y1]), uv([x0, y1])],
                false,
            )
        }
        Some(crop) => (crop.corners_px(source[0], source[1]).map(uv), true),
    }
}

fn prepare(
    job: &DevelopmentJob,
    request: &ExportRequest,
    cancelled: &std::sync::atomic::AtomicBool,
    presenter: Option<&PhotoPresenter>,
) -> anyhow::Result<Option<Prepared>> {
    let start = Instant::now();
    let extras = strehl_edit::ExportExtras {
        um_per_px: request.um_per_px,
        ..Default::default()
    };
    let Some(preview) = strehl_edit::render_export_preview(
        job.image(false),
        job.recipe(),
        &request.settings,
        &extras,
        cancelled,
    )?
    else {
        return Ok(None);
    };
    let (layer, sdr) = match presenter {
        Some(presenter) => {
            let rgba = preview
                .rgb
                .as_chunks::<3>()
                .0
                .iter()
                .flat_map(|p| [p[0], p[1], p[2], 255])
                .collect::<Vec<_>>();
            let layer = presenter.upload_sdr_sampled(
                preview.size,
                Arc::from(rgba),
                [[0.0, 0.0], [1.0, 1.0]],
                true,
            )?;
            (Some(layer), None)
        }
        None => (
            None,
            Some(egui::ColorImage::from_rgb(
                preview.size.map(|v| v as usize),
                &preview.rgb,
            )),
        ),
    };
    anyhow::ensure!(
        !cancelled.load(std::sync::atomic::Ordering::Relaxed),
        "Export preview cancelled"
    );
    Ok(Some(Prepared {
        size: preview.size,
        developed: preview.developed,
        layer,
        sdr,
        elapsed_ms: start.elapsed().as_secs_f64() * 1000.0,
    }))
}

impl ExportPaint {
    pub(super) fn opacity(&self) -> f32 {
        (self.published.elapsed().as_secs_f32() / REVEAL.as_secs_f32()).clamp(0.0, 1.0)
    }

    /// Whether the opaque preview alone fills `aperture`.
    pub(super) fn covers(&self, aperture: Rect) -> bool {
        !self.turned && self.opacity() >= 1.0 && self.bounds.contains_rect(aperture)
    }

    /// The output as a textured quad: square texels when magnified.
    pub(super) fn paint(&self, painter: &egui::Painter, destination: Rect, aperture: Rect) {
        let alpha = self.opacity();
        if alpha < 1.0 {
            request_paced_repaint(painter.ctx(), super::FRAME_DELAY);
        }
        let Some(id) = self
            .texture
            .as_ref()
            .map(TextureHandle::id)
            .or_else(|| self.layer.as_ref().and_then(PhotoLayer::texture_id))
        else {
            return;
        };
        let project =
            |p: Pos2| destination.min + (p - aperture.min) / aperture.size() * destination.size();
        let tint = Color32::WHITE.gamma_multiply(alpha);
        let mut mesh = egui::Mesh::with_texture(id);
        for (corner, uv) in self.corners.iter().zip([
            Pos2::ZERO,
            egui::pos2(1.0, 0.0),
            egui::pos2(1.0, 1.0),
            egui::pos2(0.0, 1.0),
        ]) {
            mesh.vertices.push(egui::epaint::Vertex {
                pos: project(*corner),
                uv,
                color: tint,
            });
        }
        mesh.indices.extend([0, 1, 2, 0, 2, 3]);
        painter.add(egui::Shape::mesh(mesh));
    }
}
