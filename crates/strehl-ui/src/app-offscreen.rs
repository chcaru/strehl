//! Paint the actual workspace to a GPU texture without creating an OS window.

use super::*;
use anyhow::{Context, Result, bail, ensure};
use eframe::egui_wgpu::{RenderState, RendererOptions, ScreenDescriptor};
use image::ImageEncoder;
use std::{
    future::Future,
    io::{BufWriter, Write},
    sync::Arc,
    task::{Context as TaskContext, Poll, Wake, Waker},
};

const MAX_WAIT: Duration = Duration::from_secs(60);
const FRAME_DELAY: Duration = Duration::from_millis(16);

pub(crate) fn run_offscreen(launch: LaunchOptions) -> Result<()> {
    let started = Instant::now();
    let deadline = started + MAX_WAIT;
    let destination = launch
        .screenshot
        .clone()
        .context("Offscreen rendering requires a screenshot destination")?;
    ensure!(
        !destination.try_exists()?,
        "Offscreen screenshot already exists; choose a fresh PNG destination"
    );
    let size = canvas_size(launch.size.unwrap_or([1440.0, 940.0]))?;
    let config = crate::hdr_display::configuration();
    let instance = wait_until(config.wgpu_setup.new_instance(), deadline)?;
    // No surface, winit event loop, window handle, or desktop capture is created.
    // The normal egui backend chooses gamma-encoded RGBA8 for this target.
    let render = wait_until(
        RenderState::create(&config, &instance, None, RendererOptions::default()),
        deadline,
    )??;
    ensure!(
        render.target_format == wgpu::TextureFormat::Rgba8Unorm,
        "Unexpected offscreen format: {:?}",
        render.target_format
    );
    let max_texture_side = render.device.limits().max_texture_dimension_2d;
    ensure!(
        size.iter().all(|side| *side <= max_texture_side),
        "Offscreen canvas exceeds this adapter's texture limit"
    );
    let canvas = render.device.create_texture(&wgpu::TextureDescriptor {
        label: Some("Strehl offscreen workspace"),
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
    let mut app = StrehlApp::from_launch(max_texture_side, launch);
    // No PhotoPresenter window negotiation: the existing SDR photo fallback and
    // ordinary egui source/metadata textures remain available to the real UI.
    let result = (|| -> Result<()> {
        while Instant::now() < deadline {
            let screen = egui::Rect::from_min_size(
                egui::Pos2::ZERO,
                egui::vec2(size[0] as f32, size[1] as f32),
            );
            let mut raw = egui::RawInput {
                screen_rect: Some(screen),
                max_texture_side: Some(max_texture_side as usize),
                time: Some(started.elapsed().as_secs_f64()),
                predicted_dt: FRAME_DELAY.as_secs_f32(),
                focused: true, // This is virtual egui input, never OS focus.
                ..Default::default()
            };
            if let Some(viewport) = raw.viewports.get_mut(&raw.viewport_id) {
                viewport.native_pixels_per_point = Some(1.0);
                viewport.inner_rect = Some(screen);
                viewport.outer_rect = Some(screen);
                viewport.minimized = Some(false);
                viewport.focused = Some(true);
            }
            eframe::App::raw_input_hook(&mut app, &ctx, &mut raw);
            let output = ctx.run(raw, |ctx| {
                let paint_started = Instant::now();
                app.update_workspace(ctx);
                app.frame_performance.record(
                    ctx.cumulative_frame_nr(),
                    paint_started.elapsed().as_secs_f64(),
                    None,
                );
            });
            let primitives = ctx.tessellate(output.shapes, output.pixels_per_point);
            let screen_descriptor = ScreenDescriptor {
                size_in_pixels: size,
                pixels_per_point: output.pixels_per_point,
            };
            let clear = eframe::App::clear_color(&app, &ctx.style().visuals);
            let ready = app.screenshot_requested;
            let captured = paint_frame(
                &render,
                &canvas,
                &primitives,
                &output.textures_delta,
                &screen_descriptor,
                clear,
                ready,
            )?;
            // Viewport commands, including Screenshot, are deliberately not sent
            // anywhere. The requested frame is read directly from our own texture.
            if let Some((buffer, submission, padded_row)) = captured {
                let rgba = read_pixels(
                    &render.device,
                    buffer,
                    submission,
                    size,
                    padded_row,
                    deadline,
                )?;
                ensure!(
                    Instant::now() < deadline,
                    "Offscreen screenshot timed out before PNG encoding"
                );
                write_png(&destination, &rgba, size)?;
                eprintln!(
                    "Offscreen workspace saved: {} ({}x{}, {:?}, no OS window)",
                    destination.display(),
                    size[0],
                    size[1],
                    render.adapter.get_info().backend
                );
                return Ok(());
            }
            render.device.poll(wgpu::PollType::Poll)?;
            std::thread::sleep(FRAME_DELAY.min(deadline.saturating_duration_since(Instant::now())));
        }
        bail!(
            "Offscreen screenshot did not become ready within 60 seconds (workspace status: {})",
            app.status
        )
    })();
    // The 60-second rendering budget does not bypass cooperative retirement.
    // Main may exit immediately on Err, so wait for the owned metadata child
    // and worker to finish before any loop result leaves this function.
    app.camera_metadata.retire();
    if result.is_ok() {
        eframe::App::on_exit(&mut app);
    }
    result
}

fn canvas_size(size: [f32; 2]) -> Result<[u32; 2]> {
    ensure!(
        size.iter().all(|side| side.is_finite() && *side <= 8192.0)
            && size[0] >= 640.0
            && size[1] >= 360.0,
        "Offscreen canvas must be finite, at least 640x360 and at most 8192x8192"
    );
    Ok(size.map(|side| side.round() as u32))
}

fn paint_frame(
    render: &RenderState,
    canvas: &wgpu::Texture,
    primitives: &[egui::ClippedPrimitive],
    delta: &egui::TexturesDelta,
    screen: &ScreenDescriptor,
    clear: [f32; 4],
    capture: bool,
) -> Result<Option<(wgpu::Buffer, wgpu::SubmissionIndex, u32)>> {
    let mut encoder = render
        .device
        .create_command_encoder(&wgpu::CommandEncoderDescriptor {
            label: Some("Strehl offscreen frame"),
        });
    let commands = {
        let mut renderer = render.renderer.write();
        for (id, image) in &delta.set {
            renderer.update_texture(&render.device, &render.queue, *id, image);
        }
        renderer.update_buffers(
            &render.device,
            &render.queue,
            &mut encoder,
            primitives,
            screen,
        )
    };
    let view = canvas.create_view(&Default::default());
    {
        let pass = encoder.begin_render_pass(&wgpu::RenderPassDescriptor {
            label: Some("Strehl offscreen workspace paint"),
            color_attachments: &[Some(wgpu::RenderPassColorAttachment {
                view: &view,
                resolve_target: None,
                ops: wgpu::Operations {
                    load: wgpu::LoadOp::Clear(wgpu::Color {
                        r: f64::from(clear[0]),
                        g: f64::from(clear[1]),
                        b: f64::from(clear[2]),
                        a: f64::from(clear[3]),
                    }),
                    store: wgpu::StoreOp::Store,
                },
                depth_slice: None,
            })],
            depth_stencil_attachment: None,
            timestamp_writes: None,
            occlusion_query_set: None,
        });
        render
            .renderer
            .read()
            .render(&mut pass.forget_lifetime(), primitives, screen);
    }
    let readback = if capture {
        let padded_row = (screen.size_in_pixels[0] * 4)
            .div_ceil(wgpu::COPY_BYTES_PER_ROW_ALIGNMENT)
            * wgpu::COPY_BYTES_PER_ROW_ALIGNMENT;
        let byte_length = u64::from(padded_row) * u64::from(screen.size_in_pixels[1]);
        ensure!(
            byte_length <= render.device.limits().max_buffer_size,
            "Offscreen readback exceeds adapter buffer limit"
        );
        let buffer = render.device.create_buffer(&wgpu::BufferDescriptor {
            label: Some("Strehl offscreen readback"),
            size: byte_length,
            usage: wgpu::BufferUsages::COPY_DST | wgpu::BufferUsages::MAP_READ,
            mapped_at_creation: false,
        });
        encoder.copy_texture_to_buffer(
            canvas.as_image_copy(),
            wgpu::TexelCopyBufferInfo {
                buffer: &buffer,
                layout: wgpu::TexelCopyBufferLayout {
                    offset: 0,
                    bytes_per_row: Some(padded_row),
                    rows_per_image: Some(screen.size_in_pixels[1]),
                },
            },
            canvas.size(),
        );
        Some((buffer, padded_row))
    } else {
        None
    };
    let submission = render
        .queue
        .submit(commands.into_iter().chain([encoder.finish()]));
    // Match eframe's lifecycle: a texture may still be used by this frame, so
    // free it only after its commands have been submitted.
    for id in &delta.free {
        render.renderer.write().free_texture(id);
    }
    Ok(readback.map(|(buffer, padded_row)| (buffer, submission, padded_row)))
}

fn read_pixels(
    device: &wgpu::Device,
    buffer: wgpu::Buffer,
    submission: wgpu::SubmissionIndex,
    size: [u32; 2],
    padded_row: u32,
    deadline: Instant,
) -> Result<Vec<u8>> {
    let (sender, receiver) = mpsc::sync_channel(1);
    buffer
        .slice(..)
        .map_async(wgpu::MapMode::Read, move |result| {
            let _ = sender.send(result);
        });
    device
        .poll(wgpu::PollType::Wait {
            submission_index: Some(submission),
            timeout: Some(deadline.saturating_duration_since(Instant::now())),
        })
        .context("Wait for offscreen GPU readback")?;
    receiver
        .recv_timeout(deadline.saturating_duration_since(Instant::now()))
        .context("Offscreen readback callback did not complete before the deadline")?
        .context("Map offscreen pixel buffer")?;
    let mapped = buffer.slice(..).get_mapped_range();
    let row_bytes = size[0] as usize * 4;
    let mut rgba = Vec::with_capacity(row_bytes * size[1] as usize);
    for row in mapped
        .chunks_exact(padded_row as usize)
        .take(size[1] as usize)
    {
        rgba.extend_from_slice(&row[..row_bytes]);
    }
    drop(mapped);
    buffer.unmap();
    ensure!(
        rgba.len() == row_bytes * size[1] as usize,
        "Incomplete offscreen pixel readback"
    );
    Ok(rgba)
}

fn write_png(path: &Path, rgba: &[u8], size: [u32; 2]) -> Result<()> {
    let file = std::fs::OpenOptions::new()
        .write(true)
        .create_new(true)
        .open(path)
        .with_context(|| format!("Create fresh offscreen screenshot {}", path.display()))?;
    let mut writer = BufWriter::new(file);
    image::codecs::png::PngEncoder::new(&mut writer)
        .write_image(rgba, size[0], size[1], image::ExtendedColorType::Rgba8)
        .context("Encode offscreen workspace PNG")?;
    writer.flush().context("Flush offscreen workspace PNG")
}

struct WakeThread(std::thread::Thread);
impl Wake for WakeThread {
    fn wake(self: Arc<Self>) {
        self.0.unpark();
    }
    fn wake_by_ref(self: &Arc<Self>) {
        self.0.unpark();
    }
}

/// GPU initialization is asynchronous; keep every wait within the same budget.
fn wait_until<F: Future>(future: F, deadline: Instant) -> Result<F::Output> {
    let waker = Waker::from(Arc::new(WakeThread(std::thread::current())));
    let mut context = TaskContext::from_waker(&waker);
    let mut future = std::pin::pin!(future);
    loop {
        ensure!(
            Instant::now() < deadline,
            "Offscreen GPU initialization timed out"
        );
        if let Poll::Ready(value) = future.as_mut().poll(&mut context) {
            return Ok(value);
        }
        std::thread::park_timeout(
            Duration::from_millis(25).min(deadline.saturating_duration_since(Instant::now())),
        );
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn invalid_or_non_drawable_canvases_are_rejected_before_gpu_work() {
        for size in [
            [f32::NAN, 940.0],
            [1440.0, f32::INFINITY],
            [639.0, 940.0],
            [1440.0, 359.0],
            [8193.0, 940.0],
        ] {
            assert!(canvas_size(size).is_err(), "{size:?}");
        }
        assert_eq!(canvas_size([1440.0, 940.0]).unwrap(), [1440, 940]);
    }

    #[test]
    fn gpu_wait_does_not_continue_past_its_deadline() {
        let expired = Instant::now() - Duration::from_millis(1);
        assert!(wait_until(std::future::pending::<()>(), expired).is_err());
    }
}
