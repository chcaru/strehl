//! Real GPU, end to end: demand, worker, tiles and paint through the HDR
//! presenter on an `Rgba16Float` target (DX12 on Windows), read back.
//! Run explicitly on a desktop:
//!
//! ```text
//! cargo test --locked -p strehl-ui hdr_tiles -- --ignored --nocapture
//! ```
use super::*;
use crate::hdr_display::DisplayStatus;
use eframe::egui_wgpu;
use std::sync::atomic::AtomicBool;
use strehl_edit::{DevelopmentRecipe, ImageOrigin};

/// Canvas and source: the canvas shows source pixels `ORIGIN..ORIGIN+CANVAS`
/// one to one, across the stride-1 tile corner at (1024, 1024).
const CANVAS: [u32; 2] = [512, 320];
const SOURCE: [u32; 2] = [1400, 1200];
const ORIGIN: [u32; 2] = [768, 864];

fn block_on<T>(future: impl std::future::Future<Output = T>) -> T {
    struct Wake(std::thread::Thread);
    impl std::task::Wake for Wake {
        fn wake(self: Arc<Self>) {
            self.0.unpark();
        }
    }
    let waker = std::task::Waker::from(Arc::new(Wake(std::thread::current())));
    let mut task = std::task::Context::from_waker(&waker);
    let mut future = std::pin::pin!(future);
    loop {
        match future.as_mut().poll(&mut task) {
            std::task::Poll::Ready(value) => return value,
            std::task::Poll::Pending => std::thread::park_timeout(Duration::from_millis(1)),
        }
    }
}

/// The owner's HDR display as Windows reports it (MEASURED 2026-11-23 by
/// `display_capability_replies_are_stable_while_nothing_changes`).
fn hdr_on() -> DisplayStatus {
    DisplayStatus {
        active: true,
        supported: true,
        monitor: "HDR".into(),
        sdr_white_nits: 240.0,
        peak_nits: 499.3,
        headroom: 499.3 / 240.0,
        reason: "Native scRGB · Windows HDR enabled".into(),
        ..Default::default()
    }
}

fn hdr_off() -> DisplayStatus {
    DisplayStatus {
        reason: "Windows HDR is off for this display".into(),
        ..Default::default()
    }
}

struct Gpu {
    render: egui_wgpu::RenderState,
    canvas: wgpu::Texture,
}

impl Gpu {
    fn new() -> Self {
        let instance = wgpu::Instance::new(&wgpu::InstanceDescriptor {
            backends: if cfg!(windows) {
                wgpu::Backends::DX12
            } else {
                wgpu::Backends::PRIMARY
            },
            ..Default::default()
        });
        let adapter = block_on(instance.request_adapter(&Default::default())).unwrap();
        let (device, queue) = block_on(adapter.request_device(&Default::default())).unwrap();
        eprintln!("GPU: {:?}", adapter.get_info());
        let format = wgpu::TextureFormat::Rgba16Float;
        let renderer = egui_wgpu::Renderer::new(
            &device,
            format,
            egui_wgpu::RendererOptions {
                dithering: false,
                ..Default::default()
            },
        );
        let canvas = device.create_texture(&wgpu::TextureDescriptor {
            label: Some("HDR viewport canvas"),
            size: wgpu::Extent3d {
                width: CANVAS[0],
                height: CANVAS[1],
                depth_or_array_layers: 1,
            },
            mip_level_count: 1,
            sample_count: 1,
            dimension: wgpu::TextureDimension::D2,
            format,
            usage: wgpu::TextureUsages::RENDER_ATTACHMENT | wgpu::TextureUsages::COPY_SRC,
            view_formats: &[],
        });
        Self {
            render: egui_wgpu::RenderState {
                adapter: adapter.clone(),
                available_adapters: vec![adapter],
                device,
                queue,
                target_format: format,
                renderer: Arc::new(eframe::egui::mutex::RwLock::new(renderer)),
            },
            canvas,
        }
    }

    /// The renderer state a window's poll keeps for `status`.
    fn display(&self, presenter: &PhotoPresenter, status: DisplayStatus) {
        let white = if cfg!(windows) && status.active {
            status.sdr_white_nits / 80.0
        } else {
            1.0
        };
        {
            let mut renderer = self.render.renderer.write();
            renderer.set_output_white_scale(white);
            renderer.set_output_hdr_active(status.active);
        }
        presenter.set_status(status);
    }

    /// One frame; returns the canvas as linear RGBA (scRGB on Windows).
    fn frame(&self, ctx: &egui::Context, run: impl FnMut(&egui::Context)) -> Vec<[f32; 4]> {
        let screen = Rect::from_min_size(
            Pos2::ZERO,
            egui::vec2(CANVAS[0] as f32, CANVAS[1] as f32) / ctx.pixels_per_point(),
        );
        let output = ctx.run(
            egui::RawInput {
                screen_rect: Some(screen),
                ..Default::default()
            },
            run,
        );
        let primitives = ctx.tessellate(output.shapes, output.pixels_per_point);
        let descriptor = egui_wgpu::ScreenDescriptor {
            size_in_pixels: CANVAS,
            pixels_per_point: output.pixels_per_point,
        };
        let render = &self.render;
        let mut encoder = render.device.create_command_encoder(&Default::default());
        let commands = {
            let mut renderer = render.renderer.write();
            for (id, image) in &output.textures_delta.set {
                renderer.update_texture(&render.device, &render.queue, *id, image);
            }
            renderer.update_buffers(
                &render.device,
                &render.queue,
                &mut encoder,
                &primitives,
                &descriptor,
            )
        };
        let view = self.canvas.create_view(&Default::default());
        {
            let pass = encoder.begin_render_pass(&wgpu::RenderPassDescriptor {
                color_attachments: &[Some(wgpu::RenderPassColorAttachment {
                    view: &view,
                    resolve_target: None,
                    depth_slice: None,
                    ops: wgpu::Operations {
                        load: wgpu::LoadOp::Clear(wgpu::Color::BLACK),
                        store: wgpu::StoreOp::Store,
                    },
                })],
                ..Default::default()
            });
            render
                .renderer
                .read()
                .render(&mut pass.forget_lifetime(), &primitives, &descriptor);
        }
        let padded = (CANVAS[0] * 8).div_ceil(256) * 256;
        let buffer = render.device.create_buffer(&wgpu::BufferDescriptor {
            label: None,
            size: u64::from(padded) * u64::from(CANVAS[1]),
            usage: wgpu::BufferUsages::COPY_DST | wgpu::BufferUsages::MAP_READ,
            mapped_at_creation: false,
        });
        encoder.copy_texture_to_buffer(
            self.canvas.as_image_copy(),
            wgpu::TexelCopyBufferInfo {
                buffer: &buffer,
                layout: wgpu::TexelCopyBufferLayout {
                    offset: 0,
                    bytes_per_row: Some(padded),
                    rows_per_image: Some(CANVAS[1]),
                },
            },
            self.canvas.size(),
        );
        render
            .queue
            .submit(commands.into_iter().chain([encoder.finish()]));
        for id in &output.textures_delta.free {
            render.renderer.write().free_texture(id);
        }
        let (sender, receiver) = mpsc::sync_channel(1);
        buffer
            .slice(..)
            .map_async(wgpu::MapMode::Read, move |r| sender.send(r).unwrap());
        render
            .device
            .poll(wgpu::PollType::wait_indefinitely())
            .unwrap();
        receiver.recv().unwrap().unwrap();
        let mapped = buffer.slice(..).get_mapped_range();
        let half = |lo: u8, hi: u8| {
            let bits = u16::from_le_bytes([lo, hi]);
            let sign = if bits & 0x8000 != 0 { -1.0 } else { 1.0 };
            let e = i32::from((bits >> 10) & 31);
            let m = f32::from(bits & 1023);
            sign * if e == 0 {
                m * 2.0f32.powi(-24)
            } else {
                (1.0 + m / 1024.0) * 2.0f32.powi(e - 15)
            }
        };
        let mut pixels = Vec::with_capacity((CANVAS[0] * CANVAS[1]) as usize);
        for row in mapped.chunks_exact(padded as usize) {
            for p in row[..CANVAS[0] as usize * 8].as_chunks::<8>().0 {
                pixels.push(std::array::from_fn(|c| half(p[c * 2], p[c * 2 + 1])));
            }
        }
        pixels
    }
}

/// High-frequency scene-linear detail: neighbours differ by up to 0.8.
fn source() -> LinearImage {
    let pixel = |x: u32, y: u32| {
        let h = (x * 73 + y * 151 + (x * y) % 7) % 16;
        let v = 0.08 + 0.8 * h as f32 / 15.0;
        [v, 0.5 * v + 0.1, 0.9 - 0.6 * v]
    };
    LinearImage {
        width: SOURCE[0],
        height: SOURCE[1],
        pixels: (0..SOURCE[1])
            .flat_map(|y| (0..SOURCE[0]).flat_map(move |x| pixel(x, y)))
            .collect(),
        origin: ImageOrigin::SceneLinear,
        baseline: None,
        baked_recipe: None,
    }
}

fn identity(hdr: bool) -> Identity {
    Identity {
        snapshot: None,
        revision: 1,
        before: false,
        hdr,
    }
}

/// One source pixel per physical pixel, in points at `ppp`: physical pixel
/// `p` shows source pixel `ORIGIN + p` (`offset` < 0.5 physical pixels moves
/// the photograph off the pixel grid without changing which texel is nearest).
fn mapping(ppp: f32, offset: f32) -> (Rect, Rect) {
    let full = Rect::from_min_size(
        egui::pos2(offset - ORIGIN[0] as f32, offset - ORIGIN[1] as f32) / ppp,
        egui::vec2(SOURCE[0] as f32, SOURCE[1] as f32) / ppp,
    );
    let canvas = Rect::from_min_size(
        Pos2::ZERO,
        egui::vec2(CANVAS[0] as f32, CANVAS[1] as f32) / ppp,
    );
    (full, full.intersect(canvas))
}

fn aperture(ppp: f32, offset: f32) -> Rect {
    let (full, visible) = mapping(ppp, offset);
    let uv = |p: Pos2| Pos2::ZERO + (p - full.min) / full.size();
    Rect::from_min_max(uv(visible.min), uv(visible.max))
}

struct Rig {
    gpu: Gpu,
    ctx: egui::Context,
    presenter: PhotoPresenter,
    job: DevelopmentJob,
    state: ViewportRefinement,
    max_side: u32,
    /// Display scaling, and the photograph's offset from the pixel grid.
    view: (f32, f32),
}

impl Rig {
    fn new(ppp: f32, offset: f32) -> Self {
        let gpu = Gpu::new();
        let ctx = egui::Context::default();
        ctx.set_pixels_per_point(ppp);
        let presenter = PhotoPresenter::offscreen(gpu.render.clone(), ctx.clone());
        gpu.display(&presenter, hdr_on());
        let mut recipe = DevelopmentRecipe::default();
        recipe.global.exposure = 0.3;
        recipe.validate().unwrap();
        let job = DevelopmentJob::native(Arc::new(source()), recipe);
        let state = ViewportRefinement {
            presenter: Some(presenter.clone()),
            ..Default::default()
        };
        let max_side = gpu.render.device.limits().max_texture_dimension_2d;
        Self {
            gpu,
            ctx,
            presenter,
            job,
            state,
            max_side,
            view: (ppp, offset),
        }
    }

    /// What the editor publishes for a new HDR identity: a stride-8 overview.
    fn publish_overview(&mut self, hdr: bool) {
        let prepared = prepare_job(
            &self.job,
            true,
            DisplayRegionRequest {
                min: [0, 0],
                max: SOURCE,
                stride: 8,
            },
            &AtomicBool::new(false),
            Some(&self.presenter),
            hdr,
            true,
        )
        .unwrap();
        let _ = self
            .state
            .publish_overview(&self.ctx, identity(hdr), prepared);
    }

    /// One editor frame: demand, poll, paint; returns the canvas.
    fn frame(&mut self, current: Identity) -> Vec<[f32; 4]> {
        let (ppp, offset) = self.view;
        let (full, visible) = mapping(ppp, offset);
        let aperture = aperture(ppp, offset);
        let (state, job, max_side) = (&mut self.state, &self.job, self.max_side);
        self.gpu.frame(&self.ctx, |ctx| {
            state.demand(SOURCE, (full, visible), ctx.pixels_per_point(), max_side);
            state.poll_job(ctx, Some(job.clone()), current);
            if let Some(paint) = state.paint() {
                let painter = ctx.layer_painter(egui::LayerId::background());
                paint.paint(&painter.with_clip_rect(visible), visible, aperture);
            }
        })
    }

    /// Frames until every visible tile is present and revealed; then the
    /// frame painted after that (the reveal is timed when painting).
    fn settle(&mut self, current: Identity) -> Vec<[f32; 4]> {
        let until = Instant::now() + Duration::from_secs(120);
        loop {
            let _ = self.frame(current);
            if self.state.outstanding.is_empty()
                && self.state.staged.is_empty()
                && self.state.settled()
                && self.state.paint().is_some_and(|p| !p.tiles.is_empty())
            {
                return self.frame(current);
            }
            assert!(Instant::now() < until, "{}", self.state.stats());
            std::thread::sleep(Duration::from_millis(2));
        }
    }

    /// The same paint with its tiles removed: what the overview alone shows.
    fn overview_only(&self) -> Vec<[f32; 4]> {
        let (ppp, offset) = self.view;
        let (_, visible) = mapping(ppp, offset);
        let aperture = aperture(ppp, offset);
        let mut paint = self.state.paint().unwrap();
        paint.tiles = Arc::default();
        self.gpu.frame(&self.ctx, |ctx| {
            let painter = ctx.layer_painter(egui::LayerId::background());
            paint.paint(&painter.with_clip_rect(visible), visible, aperture);
        })
    }

    /// The native development of the visible source pixels.
    fn developed(&self, hdr: bool) -> strehl_edit::DisplayRegion {
        self.job
            .image(false)
            .render_display_region_mode(
                self.job.recipe(),
                DisplayRegionRequest {
                    min: ORIGIN,
                    max: [ORIGIN[0] + CANVAS[0], ORIGIN[1] + CANVAS[1]],
                    stride: 1,
                },
                &AtomicBool::new(false),
                hdr,
            )
            .unwrap()
    }
}

/// What the photo shader writes for a float texel on Windows (80-nit units).
fn hdr_expected(linear: [f32; 3], status: &DisplayStatus) -> [f32; 3] {
    let recipe = DevelopmentRecipe::default();
    let scale = recipe.hdr.reference_white_nits / 80.0;
    let limit = recipe.hdr.peak_nits.min(status.peak_nits) / 80.0;
    let light = linear.map(|v| v * scale);
    let peak = light[0].max(light[1]).max(light[2]).max(1e-6);
    light.map(|v| v * (limit / peak).min(1.0))
}

/// An SDR byte as the float target holds it: decoded, times SDR white.
fn sdr_expected(code: [u8; 3], white: f32) -> [f32; 3] {
    code.map(|c| {
        let v = f32::from(c) / 255.0;
        let linear = if v <= 0.04045 {
            v / 12.92
        } else {
            ((v + 0.055) / 1.055).powf(2.4)
        };
        linear * white
    })
}

/// Largest relative error of the canvas against `expected` per pixel.
fn worst_error(pixels: &[[f32; 4]], expected: impl Fn(usize) -> [f32; 3]) -> f32 {
    let mut worst = 0.0f32;
    for (i, p) in pixels.iter().enumerate() {
        let e = expected(i);
        for c in 0..3 {
            worst = worst.max((p[c] - e[c]).abs() / (e[c].abs() + 0.02));
        }
    }
    worst
}

/// Mean neighbour difference over mean level, green channel: native detail
/// of this source is large; a stride-8 overview magnified 8x is nearly flat.
fn detail(pixels: &[[f32; 4]]) -> f32 {
    let width = CANVAS[0] as usize;
    let (mut difference, mut level, mut n) = (0.0f64, 0.0f64, 0usize);
    for row in pixels.chunks_exact(width) {
        for x in 1..width {
            difference += f64::from((row[x][1] - row[x - 1][1]).abs());
            level += f64::from(row[x][1]);
            n += 1;
        }
    }
    (difference / level.max(1e-9)) as f32 * (n > 0) as u8 as f32
}

#[test]
#[ignore = "real GPU: run explicitly with normal desktop permissions"]
fn hdr_tiles_show_native_pixels_and_survive_display_changes() {
    // 100 % display scaling on the pixel grid; then the owner's 4K display
    // at 150 %, off the grid (the photo shader's viewport is whole pixels).
    for (ppp, offset) in [(1.0, 0.0), (1.5, 0.37)] {
        eprintln!("pixels per point {ppp}, offset {offset}");
        display_changes(Rig::new(ppp, offset));
    }
}

fn display_changes(mut rig: Rig) {
    let on = hdr_on();
    rig.publish_overview(true);
    // 1. HDR active, 100 %: the canvas is the native float development.
    let shown = rig.settle(identity(true));
    let stats = rig.state.stats();
    assert_eq!(stats["published"]["stride"], 1, "{stats}");
    let developed = rig.developed(true);
    let native = |i: usize| {
        let d = &developed.rgba_linear[i * 4..i * 4 + 3];
        hdr_expected([d[0], d[1], d[2]], &on)
    };
    let error = worst_error(&shown, native);
    let native_detail = detail(&shown);
    eprintln!("HDR 100 %: worst relative error {error:.5}, detail {native_detail:.4}");
    assert!(error < 2e-3, "HDR tiles are not the native development");
    // Negative control: the overview alone fails the same comparison.
    let soft = rig.overview_only();
    let soft_error = worst_error(&soft, native);
    let soft_detail = detail(&soft);
    eprintln!("overview only: worst relative error {soft_error:.4}, detail {soft_detail:.4}");
    assert!(soft_error > 0.1 && soft_detail < 0.3 * native_detail);

    // 2. Windows HDR switched off (or the window moved to the SDR display):
    // until the editor redevelops, the paint still holds float tiles.
    rig.gpu.display(&rig.presenter, hdr_off());
    let switched = rig.frame(identity(true));
    let switched_detail = detail(&switched);
    eprintln!("HDR off, float tiles still published: detail {switched_detail:.4}");
    assert!(
        switched_detail > 0.7 * native_detail,
        "Painting dropped to the overview when HDR switched off"
    );

    // 3. The editor publishes the SDR overview: never a soft frame while its
    // tiles develop, and then the native SDR development.
    rig.publish_overview(false);
    let mut frames = 0;
    let until = Instant::now() + Duration::from_secs(120);
    let shown = loop {
        let pixels = rig.frame(identity(false));
        frames += 1;
        let d = detail(&pixels);
        assert!(
            d > 0.7 * native_detail,
            "frame {frames} after the SDR overview fell to the overview: {d:.4}"
        );
        if rig.state.outstanding.is_empty()
            && rig.state.staged.is_empty()
            && rig.state.settled()
            && rig.state.paint().is_some_and(|p| !p.tiles.is_empty())
            && rig.state.paint().is_some_and(|p| {
                p.tiles
                    .iter()
                    .all(|t| t.layer.as_ref().is_some_and(PhotoLayer::is_sdr))
            })
        {
            let _ = pixels;
            break rig.frame(identity(false));
        }
        assert!(Instant::now() < until, "{}", rig.state.stats());
        std::thread::sleep(Duration::from_millis(2));
    };
    let sdr = rig.developed(false);
    let error = worst_error(&shown, |i| {
        sdr_expected(
            [sdr.rgb[i * 3], sdr.rgb[i * 3 + 1], sdr.rgb[i * 3 + 2]],
            1.0,
        )
    });
    eprintln!("SDR 100 % after {frames} frames: worst relative error {error:.5}");
    assert!(error < 4e-3, "SDR tiles are not the native development");

    // 4. HDR back on: float tiles again, no soft frame on the way.
    rig.gpu.display(&rig.presenter, on.clone());
    let back = rig.frame(identity(false));
    assert!(
        detail(&back) > 0.7 * native_detail,
        "SDR tiles dropped on HDR on"
    );
    rig.publish_overview(true);
    let until = Instant::now() + Duration::from_secs(120);
    let shown = loop {
        let pixels = rig.frame(identity(true));
        assert!(
            detail(&pixels) > 0.7 * native_detail,
            "fell to the overview returning to HDR"
        );
        if rig.state.outstanding.is_empty()
            && rig.state.staged.is_empty()
            && rig.state.settled()
            && rig.state.paint().is_some_and(|p| {
                !p.tiles.is_empty()
                    && p.tiles
                        .iter()
                        .all(|t| t.layer.as_ref().is_some_and(|l| !l.is_sdr()))
            })
        {
            let _ = pixels;
            break rig.frame(identity(true));
        }
        assert!(Instant::now() < until, "{}", rig.state.stats());
        std::thread::sleep(Duration::from_millis(2));
    };
    let error = worst_error(&shown, native);
    eprintln!("HDR again: worst relative error {error:.5}");
    assert!(error < 2e-3);
    // Carried tiles go once this state's own tiles cover the view, and only
    // a change of display state carries them: never a new recipe.
    assert!(rig.state.carried.is_empty(), "{}", rig.state.stats());
    assert!(!rig.state.carry(identity(false)).is_empty());
    let edited = Identity {
        revision: 2,
        ..identity(false)
    };
    assert!(rig.state.carry(edited).is_empty());
    assert!(rig.state.carry(identity(true)).is_empty());
}
