//! Native egui/wgpu UI commissioning without desktop automation or a camera.
use crate::{app::App, theme};
use anyhow::{Context, Result, ensure};
use eframe::{
    egui,
    egui_wgpu::{RenderState, RendererOptions, ScreenDescriptor, WgpuConfiguration},
};
use std::{
    future::Future,
    path::Path,
    sync::{Arc, mpsc},
    task::{Poll, Wake, Waker},
    time::{Duration, Instant},
};
use strehl_capture::model::Phase;

struct WakeThread(std::thread::Thread);
impl Wake for WakeThread {
    fn wake(self: Arc<Self>) {
        self.0.unpark();
    }
    fn wake_by_ref(self: &Arc<Self>) {
        self.0.unpark();
    }
}
fn wait<F: Future>(future: F) -> Result<F::Output> {
    let waker = Waker::from(Arc::new(WakeThread(std::thread::current())));
    let mut cx = std::task::Context::from_waker(&waker);
    let mut future = std::pin::pin!(future);
    let end = Instant::now() + Duration::from_secs(30);
    loop {
        if let Poll::Ready(value) = future.as_mut().poll(&mut cx) {
            return Ok(value);
        }
        ensure!(Instant::now() < end, "GPU initialization timed out");
        std::thread::park_timeout(Duration::from_millis(10));
    }
}
struct Viewer {
    ctx: egui::Context,
    render: RenderState,
    canvas: wgpu::Texture,
    size: [u32; 2],
    time: Instant,
    rgba: Vec<u8>,
}
impl Viewer {
    fn new(size: [u32; 2]) -> Result<Self> {
        ensure!(
            size[0] >= 960 && size[1] >= 640 && size[0] <= 4096 && size[1] <= 4096,
            "Capture canvas must be 960×640 to 4096×4096"
        );
        let config = WgpuConfiguration::default();
        let instance = wait(config.wgpu_setup.new_instance())?;
        let render = wait(RenderState::create(
            &config,
            &instance,
            None,
            RendererOptions::default(),
        ))??;
        ensure!(
            render.target_format == wgpu::TextureFormat::Rgba8Unorm,
            "Unexpected offscreen format"
        );
        let canvas = render.device.create_texture(&wgpu::TextureDescriptor {
            label: Some("Strehl Capture offscreen"),
            size: wgpu::Extent3d {
                width: size[0],
                height: size[1],
                depth_or_array_layers: 1,
            },
            mip_level_count: 1,
            sample_count: 1,
            dimension: wgpu::TextureDimension::D2,
            format: render.target_format,
            usage: wgpu::TextureUsages::RENDER_ATTACHMENT | wgpu::TextureUsages::COPY_SRC,
            view_formats: &[],
        });
        let ctx = egui::Context::default();
        theme::install(&ctx);
        ctx.set_pixels_per_point(1.0);
        Ok(Self {
            ctx,
            render,
            canvas,
            size,
            time: Instant::now(),
            rgba: vec![],
        })
    }
    fn frame(&mut self, app: &mut App, events: Vec<egui::Event>, capture: bool) -> Result<()> {
        let input = egui::RawInput {
            screen_rect: Some(egui::Rect::from_min_size(
                egui::Pos2::ZERO,
                egui::vec2(self.size[0] as f32, self.size[1] as f32),
            )),
            time: Some(self.time.elapsed().as_secs_f64()),
            events,
            ..Default::default()
        };
        let output = self.ctx.run(input, |ctx| app.draw(ctx));
        let jobs = self.ctx.tessellate(output.shapes, output.pixels_per_point);
        let screen = ScreenDescriptor {
            size_in_pixels: self.size,
            pixels_per_point: 1.0,
        };
        let mut encoder = self
            .render
            .device
            .create_command_encoder(&Default::default());
        let commands = {
            let mut renderer = self.render.renderer.write();
            for (id, delta) in &output.textures_delta.set {
                renderer.update_texture(&self.render.device, &self.render.queue, *id, delta);
            }
            renderer.update_buffers(
                &self.render.device,
                &self.render.queue,
                &mut encoder,
                &jobs,
                &screen,
            )
        };
        let view = self.canvas.create_view(&Default::default());
        {
            let pass = encoder.begin_render_pass(&wgpu::RenderPassDescriptor {
                label: None,
                color_attachments: &[Some(wgpu::RenderPassColorAttachment {
                    view: &view,
                    resolve_target: None,
                    ops: wgpu::Operations {
                        load: wgpu::LoadOp::Clear(wgpu::Color::BLACK),
                        store: wgpu::StoreOp::Store,
                    },
                    depth_slice: None,
                })],
                depth_stencil_attachment: None,
                timestamp_writes: None,
                occlusion_query_set: None,
            });
            self.render
                .renderer
                .read()
                .render(&mut pass.forget_lifetime(), &jobs, &screen);
        }
        let padded = (self.size[0] * 4).div_ceil(256) * 256;
        let buffer = if capture {
            let buffer = self.render.device.create_buffer(&wgpu::BufferDescriptor {
                label: None,
                size: u64::from(padded) * u64::from(self.size[1]),
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
                        rows_per_image: Some(self.size[1]),
                    },
                },
                self.canvas.size(),
            );
            Some(buffer)
        } else {
            None
        };
        let submission = self
            .render
            .queue
            .submit(commands.into_iter().chain([encoder.finish()]));
        for id in &output.textures_delta.free {
            self.render.renderer.write().free_texture(id);
        }
        if let Some(buffer) = buffer {
            let (tx, rx) = mpsc::sync_channel(1);
            buffer.slice(..).map_async(wgpu::MapMode::Read, move |v| {
                let _ = tx.send(v);
            });
            self.render.device.poll(wgpu::PollType::Wait {
                submission_index: Some(submission),
                timeout: Some(Duration::from_secs(10)),
            })?;
            rx.recv_timeout(Duration::from_secs(10))??;
            let bytes = buffer.slice(..).get_mapped_range();
            self.rgba.clear();
            for row in bytes
                .chunks_exact(padded as usize)
                .take(self.size[1] as usize)
            {
                self.rgba
                    .extend_from_slice(&row[..self.size[0] as usize * 4]);
            }
            drop(bytes);
            buffer.unmap();
        }
        Ok(())
    }
    fn click(&mut self, app: &mut App, name: &str) -> Result<()> {
        self.frame(app, vec![], false)?;
        let rect = *app
            .widgets
            .get(name)
            .with_context(|| format!("UI widget {name} is absent"))?;
        ensure!(
            rect.center().y > 58.0 && rect.center().y < (self.size[1] - 64) as f32
                || name == "connection",
            "Widget {name} is outside the visible viewport: {rect:?}"
        );
        let pos = rect.center();
        self.frame(
            app,
            vec![
                egui::Event::PointerMoved(pos),
                egui::Event::PointerButton {
                    pos,
                    button: egui::PointerButton::Primary,
                    pressed: true,
                    modifiers: Default::default(),
                },
            ],
            false,
        )?;
        self.frame(
            app,
            vec![egui::Event::PointerButton {
                pos,
                button: egui::PointerButton::Primary,
                pressed: false,
                modifiers: Default::default(),
            }],
            false,
        )
    }
    fn until(&mut self, app: &mut App, test: impl Fn(&App) -> bool, seconds: u64) -> Result<()> {
        let end = Instant::now() + Duration::from_secs(seconds);
        loop {
            self.frame(app, vec![], false)?;
            if test(app) {
                return Ok(());
            }
            ensure!(
                Instant::now() < end,
                "UI wait timed out: {:?}: {}",
                app.worker.snapshot().phase,
                app.worker.snapshot().message
            );
            std::thread::sleep(Duration::from_millis(30));
        }
    }
    fn subject_rectangle(&mut self, app: &mut App) -> Result<()> {
        self.click(app, "select-roi")?;
        let rect = *app
            .widgets
            .get("preview")
            .context("Missing live preview rectangle")?;
        let from = rect.min + rect.size() * 0.2;
        let to = rect.min + rect.size() * 0.8;
        self.frame(
            app,
            vec![
                egui::Event::PointerMoved(from),
                egui::Event::PointerButton {
                    pos: from,
                    button: egui::PointerButton::Primary,
                    pressed: true,
                    modifiers: Default::default(),
                },
            ],
            false,
        )?;
        self.frame(
            app,
            vec![egui::Event::PointerMoved(from + egui::vec2(8.0, 8.0))],
            false,
        )?;
        self.frame(app, vec![egui::Event::PointerMoved(to)], false)?;
        self.frame(
            app,
            vec![egui::Event::PointerButton {
                pos: to,
                button: egui::PointerButton::Primary,
                pressed: false,
                modifiers: Default::default(),
            }],
            false,
        )?;
        ensure!(
            app.roi.x > 0.15 && app.roi.y > 0.15 && app.roi.width < 0.65 && app.roi.height < 0.65,
            "Subject rectangle did not follow pointer input: {:?}",
            app.roi
        );
        Ok(())
    }
    fn save(&mut self, app: &mut App, path: &Path) -> Result<()> {
        ensure!(!path.exists(), "Screenshot exists: {}", path.display());
        self.frame(app, vec![], true)?;
        ensure!(
            self.rgba.len() == self.size[0] as usize * self.size[1] as usize * 4,
            "Incomplete GPU readback"
        );
        image::save_buffer(
            path,
            &self.rgba,
            self.size[0],
            self.size[1],
            image::ColorType::Rgba8,
        )?;
        Ok(())
    }
}
pub fn screenshot(mut app: App, path: &Path, size: [u32; 2]) -> Result<()> {
    let mut viewer = Viewer::new(size)?;
    viewer.click(&mut app, "connection")?;
    viewer.until(&mut app, |a| a.worker.snapshot().preview.is_some(), 10)?;
    viewer.save(&mut app, path)?;
    viewer.click(&mut app, "connection")?;
    viewer.until(
        &mut app,
        |a| a.worker.snapshot().phase == Phase::Disconnected,
        10,
    )?;
    println!("Saved native capture workspace: {}", path.display());
    Ok(())
}
pub fn exercise(mut app: App, directory: &Path) -> Result<()> {
    std::fs::create_dir(directory).context("Choose a fresh UI exercise directory")?;
    app.root = directory.join("journals");
    let mut viewer = Viewer::new([1366, 900])?;
    let mut checks = Vec::new();
    viewer.save(&mut app, &directory.join("01-disconnected.png"))?;
    viewer.click(&mut app, "connection")?;
    viewer.until(&mut app, |a| a.worker.snapshot().preview.is_some(), 10)?;
    checks.push("Connect button starts simulator and renders a fresh live preview");
    viewer.subject_rectangle(&mut app)?;
    checks.push("Select subject and pointer drag set a bounded ROI in preview coordinates");
    viewer.click(&mut app, "mark-start")?;
    let start = app.plan.start;
    viewer.click(&mut app, "jog-128")?;
    viewer.until(
        &mut app,
        |a| {
            a.worker.snapshot().position == Some(start + 128)
                && a.worker.snapshot().phase == Phase::Ready
        },
        10,
    )?;
    viewer.click(&mut app, "mark-end")?;
    ensure!(
        app.plan.start == start && app.plan.end == start + 128,
        "Focus marks did not preserve preview positions"
    );
    checks.push("Mark A, jog +128, mark B bind the focus commands shown by the camera");
    viewer.save(&mut app, &directory.join("02-bounds-and-preview.png"))?;
    viewer.click(&mut app, "peaking")?;
    viewer.frame(&mut app, vec![], false)?;
    viewer.save(&mut app, &directory.join("03-preview-edges.png"))?;
    viewer.click(&mut app, "start")?;
    viewer.until(&mut app, |a| a.worker.snapshot().completed >= 1, 10)?;
    viewer.click(&mut app, "pause")?;
    viewer.until(&mut app, |a| a.worker.snapshot().phase == Phase::Paused, 10)?;
    let completed = app.worker.snapshot().completed;
    std::thread::sleep(Duration::from_millis(350));
    ensure!(
        app.worker.snapshot().completed == completed,
        "Capture advanced while paused"
    );
    viewer.save(&mut app, &directory.join("04-paused.png"))?;
    viewer.click(&mut app, "pause")?;
    viewer.until(&mut app, |a| a.worker.snapshot().completed > completed, 10)?;
    viewer.click(&mut app, "stop")?;
    viewer.until(
        &mut app,
        |a| a.worker.snapshot().phase == Phase::Stopped,
        10,
    )?;
    ensure!(
        app.worker.snapshot().completed < 129,
        "Stop did not prevent further exposures"
    );
    checks.push("Start, Pause, Resume and Stop exercised through actual egui button input");
    viewer.click(&mut app, "go-start")?;
    viewer.until(
        &mut app,
        |a| {
            a.worker.snapshot().phase == Phase::Ready && a.worker.snapshot().position == Some(start)
        },
        10,
    )?;
    for expected in [start + 1, start + 2] {
        viewer.click(&mut app, "jog-1")?;
        viewer.until(
            &mut app,
            |a| {
                a.worker.snapshot().phase == Phase::Ready
                    && a.worker.snapshot().position == Some(expected)
            },
            10,
        )?;
    }
    viewer.click(&mut app, "mark-end")?;
    viewer.click(&mut app, "start")?;
    viewer.until(
        &mut app,
        |a| a.worker.snapshot().phase == Phase::Complete,
        10,
    )?;
    ensure!(
        app.worker.snapshot().completed == 3,
        "Inclusive 3-plane sequence did not finish"
    );
    checks.push("A new three-plane run includes both bounds and finishes with three journalled acknowledgements");
    // A separate synthetic survey fixture spans the known simulated depth range.
    app.plan.start = 60500;
    app.plan.end = 60800;
    app.plan.settle_ms = 100;
    app.roi = strehl_capture::model::Roi::subject();
    viewer.click(&mut app, "scan")?;
    viewer.until(
        &mut app,
        |a| a.worker.snapshot().phase == Phase::Scanning,
        10,
    )?;
    viewer.until(&mut app, |a| a.worker.snapshot().phase == Phase::Ready, 50)?;
    ensure!(
        app.worker.snapshot().suggestion.is_some(),
        "Synthetic focus survey did not produce bounds"
    );
    checks.push("Preview-only survey uses fresh frames and suggests bounds without capture");
    viewer.save(&mut app, &directory.join("05-survey.png"))?;
    viewer.click(&mut app, "apply-bounds")?;
    ensure!(
        app.plan.start > 60500 && app.plan.end < 60800,
        "Apply bounds did not trim the synthetic sweep"
    );
    viewer.click(&mut app, "connection")?;
    viewer.until(
        &mut app,
        |a| a.worker.snapshot().phase == Phase::Disconnected,
        10,
    )?;
    ensure!(
        !app.start_set && !app.end_set,
        "Focus marks survived disconnection"
    );
    let mut laptop = Viewer::new([1280, 720])?;
    laptop.save(&mut app, &directory.join("06-laptop-layout.png"))?;
    let report = serde_json::json!({"schema":"strehl-capture-ui-verification-v1","camera":"simulator; no physical connection","renderer":format!("{:?}",viewer.render.adapter.get_info()),"checks":checks,"sizes":[[1366,900],[1280,720]],"last_phase":format!("{:?}",app.worker.snapshot().phase)});
    std::fs::write(
        directory.join("ui-receipt.json"),
        serde_json::to_string_pretty(&report)? + "\n",
    )?;
    println!("{}", serde_json::to_string(&report)?);
    Ok(())
}
