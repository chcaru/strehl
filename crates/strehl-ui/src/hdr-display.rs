//! Native extended-linear presentation. f32 photograph storage and math; only
//! the operating system's final swapchain uses its required RGBA16Float format.
use anyhow::{Result, ensure};
use eframe::{
    egui::{self, Rect},
    egui_wgpu,
};
#[cfg(any(windows, target_os = "macos"))]
use raw_window_handle::{HasWindowHandle, RawWindowHandle};
use serde::Serialize;
use std::{
    sync::{Arc, Mutex, RwLock, mpsc},
    time::{Duration, Instant},
};
use strehl_edit::ImageOrigin;
use wgpu::util::DeviceExt;

#[cfg(windows)]
#[path = "hdr-display-windows.rs"]
mod platform;
#[cfg(target_os = "macos")]
#[path = "hdr-display-macos.rs"]
mod platform;

#[derive(Clone, Debug, PartialEq, Serialize)]
pub(crate) struct DisplayStatus {
    pub active: bool,
    pub supported: bool,
    pub backend: String,
    pub monitor: String,
    pub sdr_white_nits: f32,
    pub peak_nits: f32,
    pub headroom: f32,
    pub reason: String,
}
impl Default for DisplayStatus {
    fn default() -> Self {
        Self {
            active: false,
            supported: false,
            backend: String::new(),
            monitor: String::new(),
            sdr_white_nits: 80.0,
            peak_nits: 80.0,
            headroom: 1.0,
            reason: "SDR presentation".into(),
        }
    }
}

pub(crate) struct FloatPhoto {
    pub size: [u32; 2],
    pub rgba: Arc<[f32]>,
    pub uv: [[f32; 2]; 2],
    pub reference_white_nits: f32,
    pub peak_nits: f32,
    pub origin: ImageOrigin,
}

#[derive(Clone)]
pub(crate) struct PhotoLayer(Arc<Layer>);
impl PhotoLayer {
    /// The registered egui texture of an SDR layer, for ordinary meshes.
    pub fn texture_id(&self) -> Option<egui::TextureId> {
        self.0.registered.as_ref().map(|r| r.id)
    }
    /// Display-referred bytes (an SDR development), not scene-linear floats.
    #[cfg(test)]
    pub fn is_sdr(&self) -> bool {
        self.0.sdr
    }
}
struct Layer {
    _texture: wgpu::Texture,
    view: wgpu::TextureView,
    uv: Rect,
    reference_white_nits: f32,
    peak_nits: f32,
    origin: ImageOrigin,
    sdr: bool,
    registered: Option<SdrRegistration>,
}

/// Plain egui meshes retain a texture ID, rather than the layer's Arc. Retire
/// registrations only after the frame which could reference them has rendered.
#[derive(Default)]
struct SdrRetirement(Mutex<Vec<(u64, egui::TextureId)>>);

struct SdrRegistration {
    id: egui::TextureId,
    retirement: Arc<SdrRetirement>,
    context: egui::Context,
}

impl Drop for SdrRegistration {
    fn drop(&mut self) {
        let frame = self.context.cumulative_frame_nr_for(egui::ViewportId::ROOT);
        self.retirement.0.lock().unwrap().push((frame, self.id));
    }
}

#[derive(Clone)]
pub(crate) struct PhotoPresenter(Arc<Presenter>);
struct Presenter {
    render: egui_wgpu::RenderState,
    pipeline: wgpu::RenderPipeline,
    bindings: wgpu::BindGroupLayout,
    status: RwLock<DisplayStatus>,
    refresh: Mutex<Refresh>,
    #[cfg(any(windows, target_os = "macos"))]
    window: usize,
    #[cfg(target_os = "macos")]
    native_color_space: bool,
    context: egui::Context,
    sdr_retirement: Arc<SdrRetirement>,
}
struct Refresh {
    next: Instant,
    pending: Option<mpsc::Receiver<DisplayStatus>>,
    #[cfg(windows)]
    window: WindowDisplay,
}

#[cfg(windows)]
#[derive(Default)]
struct WindowDisplay {
    bounds: Option<Rect>,
    monitor: usize,
    queried_monitor: usize,
}

#[cfg(windows)]
impl WindowDisplay {
    fn observe_monitor(&mut self, monitor: usize) -> bool {
        let changed = self.monitor != monitor;
        self.monitor = monitor;
        changed
    }

    fn accepts_reply(&self) -> bool {
        self.monitor == self.queried_monitor
    }
}

pub(crate) fn configuration() -> egui_wgpu::WgpuConfiguration {
    #[allow(unused_mut)] // The native Windows adapter preference is platform-specific.
    let mut setup = egui_wgpu::WgpuSetupCreateNew::default();
    #[cfg(windows)]
    {
        // Prefer the native scRGB backend but retain other adapters as fallback.
        setup.native_adapter_selector = Some(Arc::new(|adapters, surface| {
            adapters
                .iter()
                .filter(|a| surface.is_none_or(|s| a.is_surface_supported(s)))
                .min_by_key(|a| {
                    let info = a.get_info();
                    (
                        info.backend != wgpu::Backend::Dx12,
                        info.device_type != wgpu::DeviceType::DiscreteGpu,
                    )
                })
                .cloned()
                .ok_or_else(|| "No compatible graphics adapter".into())
        }));
    }
    egui_wgpu::WgpuConfiguration {
        extended_linear_surface: cfg!(any(windows, target_os = "macos")),
        desired_maximum_frame_latency: Some(1),
        wgpu_setup: setup.into(),
        ..Default::default()
    }
}

impl PhotoPresenter {
    pub fn new(context: &eframe::CreationContext<'_>) -> Option<Self> {
        let render = context.wgpu_render_state.clone()?;
        #[cfg(any(windows, target_os = "macos"))]
        let window = match context.window_handle().ok()?.as_raw() {
            RawWindowHandle::Win32(h) => h.hwnd.get() as usize,
            RawWindowHandle::AppKit(h) => h.ns_view.as_ptr() as usize,
            _ => 0,
        };
        let (pipeline, bindings) = photo_pipeline(&render.device, render.target_format);
        #[cfg(target_os = "macos")]
        let native_color_space =
            render.target_format == wgpu::TextureFormat::Rgba16Float && platform::configure(window);
        let value = Self(Arc::new(Presenter {
            render,
            pipeline,
            bindings,
            #[cfg(any(windows, target_os = "macos"))]
            window,
            #[cfg(target_os = "macos")]
            native_color_space,
            context: context.egui_ctx.clone(),
            sdr_retirement: Arc::default(),
            status: RwLock::new(DisplayStatus::default()),
            refresh: Mutex::new(Refresh {
                next: Instant::now(),
                pending: None,
                #[cfg(windows)]
                window: WindowDisplay::default(),
            }),
        }));
        // Poll is asynchronous on Windows: enumerating monitors never blocks a
        // pointer-driven paint frame. Until the reply arrives the image is SDR.
        let mut value = value;
        value.poll();
        Some(value)
    }

    /// The production SDR presenter for a render state without a window
    /// (offscreen screenshots and GPU benchmarks): the same off-thread
    /// uploads and registered-texture painting, never an HDR surface.
    pub fn offscreen(render: egui_wgpu::RenderState, context: egui::Context) -> Self {
        let (pipeline, bindings) = photo_pipeline(&render.device, render.target_format);
        Self(Arc::new(Presenter {
            render,
            pipeline,
            bindings,
            #[cfg(any(windows, target_os = "macos"))]
            window: 0,
            #[cfg(target_os = "macos")]
            native_color_space: false,
            context,
            sdr_retirement: Arc::default(),
            status: RwLock::new(DisplayStatus {
                reason: "SDR: offscreen".into(),
                ..Default::default()
            }),
            refresh: Mutex::new(Refresh {
                next: Instant::now() + Duration::from_secs(365 * 24 * 3600),
                pending: None,
                #[cfg(windows)]
                window: WindowDisplay::default(),
            }),
        }))
    }

    pub fn status(&self) -> DisplayStatus {
        self.0.status.read().unwrap().clone()
    }

    /// Tests: the display state a window's poll would publish (HDR switched
    /// on or off, the window moved to another display).
    #[cfg(test)]
    pub(crate) fn set_status(&self, status: DisplayStatus) {
        *self.0.status.write().unwrap() = status;
    }

    pub fn poll(&mut self) -> bool {
        self.retire_sdr_textures();
        let mut refresh = self.0.refresh.lock().unwrap();
        #[cfg(windows)]
        {
            let bounds = self.0.context.input(|input| input.viewport().outer_rect);
            // Only the cheap window-to-monitor lookup runs on movement, the
            // periodic deadline, or before accepting a worker response. DXGI
            // enumeration and white-level queries always stay off this thread.
            if bounds != refresh.window.bounds
                || Instant::now() >= refresh.next
                || refresh.pending.is_some()
            {
                refresh.window.bounds = bounds;
                if refresh
                    .window
                    .observe_monitor(platform::window_monitor(self.0.window))
                {
                    refresh.next = Instant::now();
                }
            }
        }
        #[allow(unused_mut)] // macOS queries NSWindow on the main thread below.
        let mut observed = None;
        if let Some(receiver) = &refresh.pending {
            match receiver.try_recv() {
                Ok(value) => {
                    #[cfg(windows)]
                    if refresh.window.accepts_reply() {
                        observed = Some(value);
                    }
                    #[cfg(not(windows))]
                    {
                        observed = Some(value);
                    }
                    refresh.pending = None;
                }
                Err(mpsc::TryRecvError::Disconnected) => {
                    refresh.pending = None;
                }
                Err(mpsc::TryRecvError::Empty) => {}
            }
        }
        if refresh.pending.is_none() && Instant::now() >= refresh.next {
            refresh.next = Instant::now() + Duration::from_millis(750);
            #[cfg(windows)]
            {
                let (tx, rx) = mpsc::sync_channel(1);
                let monitor = refresh.window.monitor;
                refresh.window.queried_monitor = monitor;
                let context = self.0.context.clone();
                refresh.pending = Some(rx);
                std::thread::spawn(move || {
                    let _ = tx.send(platform::detect_monitor(monitor));
                    context.request_repaint();
                });
            }
            #[cfg(target_os = "macos")]
            {
                observed = Some(platform::detect(self.0.window));
            }
            #[cfg(not(any(windows, target_os = "macos")))]
            {
                observed = Some(DisplayStatus {
                    reason:
                        "This platform uses SDR; native HDR color-space negotiation is unavailable"
                            .into(),
                    ..Default::default()
                });
            }
        }
        self.0
            .context
            .request_repaint_after(Duration::from_millis(750));
        let Some(mut status) = observed else {
            return false;
        };
        let backend = self.0.render.adapter.get_info();
        status.backend = format!("{:?} · {}", backend.backend, backend.name);
        if self.0.render.target_format != wgpu::TextureFormat::Rgba16Float {
            status.active = false;
            status.reason = "Graphics backend selected an SDR surface".into();
        }
        #[cfg(target_os = "macos")]
        if !self.0.native_color_space {
            status.active = false;
            status.reason =
                "SDR: the native extended-linear color space could not be confirmed".into();
        }
        let white_scale = if cfg!(windows) && status.active {
            status.sdr_white_nits / 80.0
        } else {
            1.0
        };
        {
            let mut renderer = self.0.render.renderer.write();
            renderer.set_output_white_scale(white_scale);
            renderer.set_output_hdr_active(status.active);
        }
        let mut current = self.0.status.write().unwrap();
        let changed = *current != status;
        *current = status;
        changed
    }

    fn retire_sdr_textures(&self) {
        let frame = self
            .0
            .context
            .cumulative_frame_nr_for(egui::ViewportId::ROOT);
        let mut retired = self.0.sdr_retirement.0.lock().unwrap();
        if retired.is_empty() {
            return;
        }
        let mut ready = Vec::new();
        retired.retain(|&(last_frame, id)| {
            let keep = frame.saturating_sub(last_frame) < 2;
            if !keep {
                ready.push(id);
            }
            keep
        });
        drop(retired);
        if !ready.is_empty() {
            let mut renderer = self.0.render.renderer.write();
            for id in ready {
                renderer.free_texture(&id);
            }
        }
    }

    pub fn upload(&self, photo: Arc<FloatPhoto>) -> Result<PhotoLayer> {
        let [width, height] = photo.size;
        let limit = self.0.render.device.limits().max_texture_dimension_2d;
        ensure!(
            width > 0 && height > 0 && width <= limit && height <= limit,
            "Invalid photograph texture size"
        );
        ensure!(
            photo.rgba.len() == width as usize * height as usize * 4,
            "Invalid float photograph length"
        );
        ensure!(
            photo.rgba.iter().all(|v| v.is_finite()),
            "Non-finite photograph samples"
        );
        ensure!(
            photo.reference_white_nits.is_finite()
                && photo.reference_white_nits > 0.0
                && photo.peak_nits.is_finite()
                && photo.peak_nits >= photo.reference_white_nits,
            "Invalid photograph luminance"
        );
        let uv = Rect::from_min_max(photo.uv[0].into(), photo.uv[1].into());
        ensure!(
            uv.is_finite()
                && uv.is_positive()
                && uv.min.x >= 0.0
                && uv.min.y >= 0.0
                && uv.max.x <= 1.0
                && uv.max.y <= 1.0,
            "Invalid photograph region"
        );
        let texture = self
            .0
            .render
            .device
            .create_texture(&wgpu::TextureDescriptor {
                label: Some("Strehl f32 developed photograph"),
                size: wgpu::Extent3d {
                    width,
                    height,
                    depth_or_array_layers: 1,
                },
                mip_level_count: 1,
                sample_count: 1,
                dimension: wgpu::TextureDimension::D2,
                format: wgpu::TextureFormat::Rgba32Float,
                usage: wgpu::TextureUsages::TEXTURE_BINDING | wgpu::TextureUsages::COPY_DST,
                view_formats: &[],
            });
        self.0.render.queue.write_texture(
            texture.as_image_copy(),
            bytemuck::cast_slice(&photo.rgba),
            wgpu::TexelCopyBufferLayout {
                offset: 0,
                bytes_per_row: Some(width * 16),
                rows_per_image: Some(height),
            },
            texture.size(),
        );
        let view = texture.create_view(&Default::default());
        Ok(PhotoLayer(Arc::new(Layer {
            _texture: texture,
            view,
            uv,
            reference_white_nits: photo.reference_white_nits,
            peak_nits: photo.peak_nits,
            origin: photo.origin,
            sdr: false,
            registered: None,
        })))
    }

    /// Upload from a background worker. SDR bytes remain gamma encoded so the
    /// ordinary SDR presentation matches egui's existing image interpolation.
    #[cfg(test)]
    pub fn upload_sdr(
        &self,
        size: [u32; 2],
        rgba: Arc<[u8]>,
        region: [[f32; 2]; 2],
    ) -> Result<PhotoLayer> {
        self.upload_sdr_sampled(size, rgba, region, false)
    }

    /// `upload_sdr`; with `nearest`, magnified texels stay square (true
    /// pixels above 100 %) while minification still filters linearly.
    pub fn upload_sdr_sampled(
        &self,
        size: [u32; 2],
        rgba: Arc<[u8]>,
        region: [[f32; 2]; 2],
        nearest: bool,
    ) -> Result<PhotoLayer> {
        self.upload_sdr_slice(size, &rgba, region, nearest)
    }

    /// [`Self::upload_sdr_sampled`] from borrowed texels: a caller that
    /// uploads tile after tile reuses one buffer rather than allocating
    /// each (the capture plane view, `capture-planes.rs`).
    pub fn upload_sdr_slice(
        &self,
        size: [u32; 2],
        rgba: &[u8],
        region: [[f32; 2]; 2],
        nearest: bool,
    ) -> Result<PhotoLayer> {
        let [width, height] = size;
        let limit = self.0.render.device.limits().max_texture_dimension_2d;
        ensure!(
            width > 0 && height > 0 && width <= limit && height <= limit,
            "Invalid SDR photograph texture size"
        );
        ensure!(
            rgba.len() == width as usize * height as usize * 4,
            "Invalid SDR photograph length"
        );
        let uv = Rect::from_min_max(region[0].into(), region[1].into());
        ensure!(
            uv.is_finite()
                && uv.is_positive()
                && uv.min.x >= 0.0
                && uv.min.y >= 0.0
                && uv.max.x <= 1.0
                && uv.max.y <= 1.0,
            "Invalid SDR photograph region"
        );
        let texture = self
            .0
            .render
            .device
            .create_texture(&wgpu::TextureDescriptor {
                label: Some("Strehl SDR photograph"),
                size: wgpu::Extent3d {
                    width,
                    height,
                    depth_or_array_layers: 1,
                },
                mip_level_count: 1,
                sample_count: 1,
                dimension: wgpu::TextureDimension::D2,
                format: wgpu::TextureFormat::Rgba8Unorm,
                usage: wgpu::TextureUsages::TEXTURE_BINDING | wgpu::TextureUsages::COPY_DST,
                view_formats: &[],
            });
        self.0.render.queue.write_texture(
            texture.as_image_copy(),
            rgba,
            wgpu::TexelCopyBufferLayout {
                offset: 0,
                bytes_per_row: Some(width * 4),
                rows_per_image: Some(height),
            },
            texture.size(),
        );
        let view = texture.create_view(&Default::default());
        // Upload and immutable bind-group creation both run on the caller's
        // development worker. Painting only emits an ordinary batched mesh.
        let id = self
            .0
            .render
            .renderer
            .write()
            .register_native_texture_with_sampler_options(
                &self.0.render.device,
                &view,
                wgpu::SamplerDescriptor {
                    label: Some("Strehl SDR photograph sampler"),
                    mag_filter: if nearest {
                        wgpu::FilterMode::Nearest
                    } else {
                        wgpu::FilterMode::Linear
                    },
                    min_filter: wgpu::FilterMode::Linear,
                    ..Default::default()
                },
            );
        Ok(PhotoLayer(Arc::new(Layer {
            _texture: texture,
            view,
            uv,
            reference_white_nits: 80.0,
            peak_nits: 80.0,
            origin: ImageOrigin::DisplayReferred,
            sdr: true,
            registered: Some(SdrRegistration {
                id,
                retirement: self.0.sdr_retirement.clone(),
                context: self.0.context.clone(),
            }),
        })))
    }

    /// Paint layers in order, each clipped to its own photograph-UV rectangle
    /// (a tile's core, inside its apron). The first is the base. `nearest`
    /// keeps magnified texels square in the float shader; SDR layers carry
    /// their magnification filter from upload. Returns false, painting
    /// nothing, when the original SDR drawing path should paint instead.
    ///
    /// Float layers are never dropped while this target can show them: when
    /// the display is not presenting HDR (Windows HDR switched off, the window
    /// on an SDR display) or the photograph is shown as SDR, they are fitted
    /// to SDR white, so detail developed for one display state stays on
    /// screen until the other state's detail arrives.
    pub fn paint_regions(
        &self,
        painter: &egui::Painter,
        destination: Rect,
        aperture: Rect,
        hdr: bool,
        layers: &[(&PhotoLayer, Rect, f32, bool)],
    ) -> bool {
        let Some((base, ..)) = layers.first() else {
            return false;
        };
        if !destination.is_positive() || !aperture.is_positive() {
            return false;
        }
        let status = self.status();
        if hdr {
            let fit = !status.active;
            if base.0.origin != ImageOrigin::SceneLinear || (fit && !self.fits_float_to_sdr()) {
                return false;
            }
            for (layer, clip, alpha, nearest) in layers {
                self.paint_layer_clipped(
                    painter,
                    destination,
                    aperture,
                    layer,
                    (*clip, *nearest, fit),
                    alpha.clamp(0.0, 1.0),
                    &status,
                );
            }
        } else {
            if !base.0.sdr {
                return false;
            }
            for (layer, clip, alpha, nearest) in layers {
                let alpha = alpha.clamp(0.0, 1.0);
                if layer.0.sdr {
                    self.paint_sdr_clipped(
                        painter,
                        destination,
                        aperture,
                        layer,
                        (*clip, *nearest),
                        alpha,
                    );
                } else if self.fits_float_to_sdr() {
                    self.paint_layer_clipped(
                        painter,
                        destination,
                        aperture,
                        layer,
                        (*clip, *nearest, true),
                        alpha,
                        &status,
                    );
                }
            }
        }
        true
    }

    /// Whether the photo shader can show a float layer as SDR on this target:
    /// it writes linear light, which a float (scRGB) or sRGB target encodes.
    pub fn fits_float_to_sdr(&self) -> bool {
        let format = self.0.render.target_format;
        format == wgpu::TextureFormat::Rgba16Float || format.is_srgb()
    }

    #[cfg(test)]
    fn paint_sdr_layer(
        &self,
        painter: &egui::Painter,
        destination: Rect,
        aperture: Rect,
        layer: &PhotoLayer,
        alpha: f32,
    ) {
        self.paint_sdr_clipped(
            painter,
            destination,
            aperture,
            layer,
            (layer.0.uv, false),
            alpha,
        );
    }

    fn paint_sdr_clipped(
        &self,
        painter: &egui::Painter,
        destination: Rect,
        aperture: Rect,
        layer: &PhotoLayer,
        (clip, nearest): (Rect, bool),
        alpha: f32,
    ) {
        // Upstream egui's sRGB-attachment shader decodes premultiplied gamma
        // colors directly. Keep the existing linear-alpha callback for fades
        // on that fallback format; our extended-linear shader handles it.
        if self.0.render.target_format.is_srgb() && alpha < 1.0 {
            self.paint_layer_clipped(
                painter,
                destination,
                aperture,
                layer,
                (clip, nearest, false),
                alpha,
                &self.status(),
            );
            return;
        }
        let Some(registered) = &layer.0.registered else {
            return;
        };
        let visible = aperture.intersect(layer.0.uv).intersect(clip);
        if !visible.is_positive() || alpha <= 0.0 {
            return;
        }
        let project = |point: egui::Pos2| {
            destination.min + (point - aperture.min) / aperture.size() * destination.size()
        };
        let local =
            |point: egui::Pos2| egui::Pos2::ZERO + (point - layer.0.uv.min) / layer.0.uv.size();
        painter.image(
            registered.id,
            Rect::from_min_max(project(visible.min), project(visible.max)),
            Rect::from_min_max(local(visible.min), local(visible.max)),
            egui::Color32::WHITE.gamma_multiply(alpha),
        );
    }

    #[allow(clippy::too_many_arguments)]
    fn paint_layer_clipped(
        &self,
        painter: &egui::Painter,
        destination: Rect,
        aperture: Rect,
        layer: &PhotoLayer,
        (clip, nearest, fit): (Rect, bool, bool),
        alpha: f32,
        status: &DisplayStatus,
    ) {
        let visible = aperture.intersect(layer.0.uv).intersect(clip);
        if !visible.is_positive() || alpha <= 0.0 {
            return;
        }
        let a = (visible.min - aperture.min) / aperture.size();
        let b = (visible.max - aperture.min) / aperture.size();
        let rect = Rect::from_min_max(
            destination.min + destination.size() * a,
            destination.min + destination.size() * b,
        );
        let lo = (visible.min - layer.0.uv.min) / layer.0.uv.size();
        let hi = (visible.max - layer.0.uv.min) / layer.0.uv.size();
        let unit = if cfg!(windows) {
            80.0
        } else {
            layer.0.reference_white_nits
        };
        let peak = if cfg!(windows) {
            status.peak_nits
        } else {
            status.headroom * unit
        };
        let float_surface = self.0.render.target_format == wgpu::TextureFormat::Rgba16Float;
        // Mode 0: scene-linear HDR. 1: gamma SDR target. 2: gamma SDR image
        // decoded into an extended-linear target. 3: sRGB attachment encoding.
        let white = if cfg!(windows) && status.active {
            status.sdr_white_nits / 80.0
        } else {
            1.0
        };
        let (scale, limit, mode) = if layer.0.sdr {
            (
                if float_surface { white } else { 1.0 },
                1.0,
                if float_surface {
                    2.0
                } else if self.0.render.target_format.is_srgb() {
                    3.0
                } else {
                    1.0
                },
            )
        } else if fit {
            // Shown as SDR: the photograph's reference white at SDR white,
            // brighter light clipped there with its hue kept.
            let white = if float_surface { white } else { 1.0 };
            (white, white, 0.0)
        } else {
            (
                layer.0.reference_white_nits / unit,
                layer.0.peak_nits.min(peak) / unit,
                0.0,
            )
        };
        let params = [
            lo.x,
            lo.y,
            hi.x,
            hi.y,
            scale,
            limit,
            alpha,
            mode,
            if nearest { 1.0 } else { 0.0 },
            0.0,
            0.0,
            0.0,
        ];
        let buffer = self
            .0
            .render
            .device
            .create_buffer_init(&wgpu::util::BufferInitDescriptor {
                label: Some("Strehl photo coordinates"),
                contents: bytemuck::cast_slice(&params),
                usage: wgpu::BufferUsages::UNIFORM,
            });
        let bindings = self
            .0
            .render
            .device
            .create_bind_group(&wgpu::BindGroupDescriptor {
                label: Some("Strehl photo presentation"),
                layout: &self.0.bindings,
                entries: &[
                    wgpu::BindGroupEntry {
                        binding: 0,
                        resource: wgpu::BindingResource::TextureView(&layer.0.view),
                    },
                    wgpu::BindGroupEntry {
                        binding: 1,
                        resource: buffer.as_entire_binding(),
                    },
                ],
            });
        painter.add(egui_wgpu::Callback::new_paint_callback(
            rect,
            PhotoCallback {
                pipeline: self.0.pipeline.clone(),
                bindings,
                _layer: layer.clone(),
                _parameters: buffer,
            },
        ));
    }
}

struct PhotoCallback {
    pipeline: wgpu::RenderPipeline,
    bindings: wgpu::BindGroup,
    _layer: PhotoLayer,
    _parameters: wgpu::Buffer,
}
impl egui_wgpu::CallbackTrait for PhotoCallback {
    fn paint(
        &self,
        _: egui::PaintCallbackInfo,
        pass: &mut wgpu::RenderPass<'static>,
        _: &egui_wgpu::CallbackResources,
    ) {
        pass.set_pipeline(&self.pipeline);
        pass.set_bind_group(0, &self.bindings, &[]);
        pass.draw(0..3, 0..1);
    }
}

fn photo_pipeline(
    device: &wgpu::Device,
    format: wgpu::TextureFormat,
) -> (wgpu::RenderPipeline, wgpu::BindGroupLayout) {
    let bindings = device.create_bind_group_layout(&wgpu::BindGroupLayoutDescriptor {
        label: Some("Strehl f32 photograph layout"),
        entries: &[
            wgpu::BindGroupLayoutEntry {
                binding: 0,
                visibility: wgpu::ShaderStages::FRAGMENT,
                ty: wgpu::BindingType::Texture {
                    sample_type: wgpu::TextureSampleType::Float { filterable: false },
                    view_dimension: wgpu::TextureViewDimension::D2,
                    multisampled: false,
                },
                count: None,
            },
            wgpu::BindGroupLayoutEntry {
                binding: 1,
                visibility: wgpu::ShaderStages::VERTEX_FRAGMENT,
                ty: wgpu::BindingType::Buffer {
                    ty: wgpu::BufferBindingType::Uniform,
                    has_dynamic_offset: false,
                    min_binding_size: std::num::NonZeroU64::new(48),
                },
                count: None,
            },
        ],
    });
    let layout = device.create_pipeline_layout(&wgpu::PipelineLayoutDescriptor {
        label: Some("Strehl photo pipeline layout"),
        bind_group_layouts: &[&bindings],
        push_constant_ranges: &[],
    });
    let shader = device.create_shader_module(wgpu::include_wgsl!("hdr-display.wgsl"));
    let pipeline = device.create_render_pipeline(&wgpu::RenderPipelineDescriptor {
        label: Some("Strehl native HDR photograph"),
        layout: Some(&layout),
        vertex: wgpu::VertexState {
            module: &shader,
            entry_point: Some("vertex"),
            buffers: &[],
            compilation_options: Default::default(),
        },
        fragment: Some(wgpu::FragmentState {
            module: &shader,
            entry_point: Some("fragment"),
            targets: &[Some(wgpu::ColorTargetState {
                format,
                blend: Some(wgpu::BlendState::PREMULTIPLIED_ALPHA_BLENDING),
                write_mask: wgpu::ColorWrites::ALL,
            })],
            compilation_options: Default::default(),
        }),
        primitive: Default::default(),
        depth_stencil: None,
        multisample: Default::default(),
        multiview: None,
        cache: None,
    });
    (pipeline, bindings)
}

#[cfg(test)]
#[path = "hdr-display-review-tests.rs"]
mod independent_review;

#[cfg(test)]
#[path = "hdr-display-tests.rs"]
mod tests;
