//! Real-master zoom benchmark through the production GPU path: the offscreen
//! presenter uploads on workers and draws registered textures, as the window
//! does. Run explicitly, release, on a copy of a render folder:
//!
//! ```text
//! STREHL_UI_BENCH_RUN=<render folder copy> STREHL_UI_BENCH_OUT=<scratch dir> \
//!   cargo test --release --locked -p strehl-ui zoom_benchmark -- --ignored --nocapture
//! ```
//!
//! The canvas is 3290 x 1750 physical pixels: a 4K display less the shell's
//! inspector, tools and bars. Frame times are the UI thread's work (egui,
//! tessellation, buffer upload, submit) and, separately, until the GPU is done.
use crate::{edit_workspace::EditorState, hdr_display::PhotoPresenter};
use eframe::{egui, egui_wgpu};
use std::{
    path::PathBuf,
    sync::mpsc,
    time::{Duration, Instant},
};

const CANVAS: [u32; 2] = [3290, 1750];

/// Forget every detail pixel (not the overview), so the next view is cold.
fn drop_detail(viewport: &mut super::ViewportRefinement) {
    viewport.cancel();
    viewport.clear_tiles();
}

fn block_on<T>(future: impl std::future::Future<Output = T>) -> T {
    struct Wake(std::thread::Thread);
    impl std::task::Wake for Wake {
        fn wake(self: std::sync::Arc<Self>) {
            self.0.unpark();
        }
    }
    let waker = std::task::Waker::from(std::sync::Arc::new(Wake(std::thread::current())));
    let mut task = std::task::Context::from_waker(&waker);
    let mut future = std::pin::pin!(future);
    loop {
        match future.as_mut().poll(&mut task) {
            std::task::Poll::Ready(value) => return value,
            std::task::Poll::Pending => std::thread::park_timeout(Duration::from_millis(1)),
        }
    }
}

struct Gpu {
    render: egui_wgpu::RenderState,
    canvas: wgpu::Texture,
}

impl Gpu {
    fn new() -> Self {
        let config = crate::hdr_display::configuration();
        let instance = block_on(config.wgpu_setup.new_instance());
        // No dithering: displayed codes must be comparable with the export's.
        let options = egui_wgpu::RendererOptions {
            dithering: false,
            ..Default::default()
        };
        let render = block_on(egui_wgpu::RenderState::create(
            &config, &instance, None, options,
        ))
        .unwrap();
        let canvas = render.device.create_texture(&wgpu::TextureDescriptor {
            label: Some("zoom benchmark canvas"),
            size: wgpu::Extent3d {
                width: CANVAS[0],
                height: CANVAS[1],
                depth_or_array_layers: 1,
            },
            mip_level_count: 1,
            sample_count: 1,
            dimension: wgpu::TextureDimension::D2,
            format: render.target_format,
            usage: wgpu::TextureUsages::RENDER_ATTACHMENT | wgpu::TextureUsages::COPY_SRC,
            view_formats: &[],
        });
        Self { render, canvas }
    }

    /// One frame: (UI thread ms, until GPU done ms, optional RGBA readback).
    fn frame(
        &self,
        ctx: &egui::Context,
        time: f64,
        readback: bool,
        run: impl FnMut(&egui::Context),
    ) -> (f64, f64, Option<Vec<u8>>) {
        let began = Instant::now();
        let screen = egui::Rect::from_min_size(
            egui::Pos2::ZERO,
            egui::vec2(CANVAS[0] as f32, CANVAS[1] as f32),
        );
        let output = ctx.run(
            egui::RawInput {
                screen_rect: Some(screen),
                time: Some(time),
                predicted_dt: 1.0 / 120.0,
                focused: true,
                ..Default::default()
            },
            run,
        );
        let ran = began.elapsed();
        let primitives = ctx.tessellate(output.shapes, output.pixels_per_point);
        let tessellated = began.elapsed();
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
        let updated = began.elapsed();
        let view = self.canvas.create_view(&Default::default());
        {
            let pass = encoder.begin_render_pass(&wgpu::RenderPassDescriptor {
                label: Some("zoom benchmark frame"),
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
            render
                .renderer
                .read()
                .render(&mut pass.forget_lifetime(), &primitives, &descriptor);
        }
        let padded = (CANVAS[0] * 4).div_ceil(256) * 256;
        let buffer = readback.then(|| {
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
            buffer
        });
        let submission = render
            .queue
            .submit(commands.into_iter().chain([encoder.finish()]));
        for id in &output.textures_delta.free {
            render.renderer.write().free_texture(id);
        }
        let cpu = began.elapsed().as_secs_f64() * 1000.0;
        if cpu > 8.0 {
            let ms = |d: Duration| d.as_secs_f64() * 1000.0;
            eprintln!(
                "slow frame {cpu:.2} ms: egui {:.2}, tessellate {:.2}, buffers {:.2}, render+submit {:.2}",
                ms(ran),
                ms(tessellated - ran),
                ms(updated - tessellated),
                cpu - ms(updated)
            );
        }
        let pixels = buffer.map(|buffer| {
            let (sender, receiver) = mpsc::sync_channel(1);
            buffer
                .slice(..)
                .map_async(wgpu::MapMode::Read, move |r| sender.send(r).unwrap());
            render
                .device
                .poll(wgpu::PollType::Wait {
                    submission_index: Some(submission.clone()),
                    timeout: Some(Duration::from_secs(10)),
                })
                .unwrap();
            receiver.recv().unwrap().unwrap();
            let mapped = buffer.slice(..).get_mapped_range();
            let mut rgba = Vec::with_capacity((CANVAS[0] * CANVAS[1] * 4) as usize);
            for row in mapped
                .chunks_exact(padded as usize)
                .take(CANVAS[1] as usize)
            {
                rgba.extend_from_slice(&row[..CANVAS[0] as usize * 4]);
            }
            rgba
        });
        render
            .device
            .poll(wgpu::PollType::Wait {
                submission_index: Some(submission),
                timeout: Some(Duration::from_secs(10)),
            })
            .unwrap();
        (cpu, began.elapsed().as_secs_f64() * 1000.0, pixels)
    }
}

/// Screen-space mapping: `scale` physical pixels per source pixel, `centre`
/// in photograph UV at the canvas centre. Returns (full, visible) rectangles.
fn mapping(source: [u32; 2], scale: f32, centre: [f32; 2]) -> (egui::Rect, egui::Rect) {
    let canvas = egui::Rect::from_min_size(
        egui::Pos2::ZERO,
        egui::vec2(CANVAS[0] as f32, CANVAS[1] as f32),
    );
    let size = egui::vec2(source[0] as f32, source[1] as f32) * scale;
    let full = egui::Rect::from_min_size(
        canvas.center() - egui::vec2(centre[0], centre[1]) * size,
        size,
    );
    (full, full.intersect(canvas))
}

fn fit(source: [u32; 2]) -> f32 {
    (CANVAS[0] as f32 / source[0] as f32).min(CANVAS[1] as f32 / source[1] as f32)
}

fn percentile(values: &[f64], q: f64) -> f64 {
    let mut v = values.to_vec();
    v.sort_by(f64::total_cmp);
    if v.is_empty() {
        return f64::NAN;
    }
    v[((v.len() - 1) as f64 * q).round() as usize]
}

fn summary(values: &[f64]) -> serde_json::Value {
    serde_json::json!({
        "n": values.len(),
        "median": percentile(values, 0.5),
        "p95": percentile(values, 0.95),
        "max": percentile(values, 1.0),
        "over_16ms": values.iter().filter(|v| **v > 16.0).count(),
        "over_8ms": values.iter().filter(|v| **v > 8.0).count(),
    })
}

struct Bench {
    gpu: Gpu,
    ctx: egui::Context,
    editor: EditorState,
    source: [u32; 2],
    view: (f32, [f32; 2]),
    start: Instant,
    max_side: u32,
}

impl Bench {
    fn step(&mut self, readback: bool) -> (f64, f64, Option<Vec<u8>>) {
        let (scale, centre) = self.view;
        let (full, visible) = mapping(self.source, scale, centre);
        let editor = &mut self.editor;
        let max_side = self.max_side;
        let time = self.start.elapsed().as_secs_f64();
        let result = self.gpu.frame(&self.ctx, time, readback, |ctx| {
            editor.poll(ctx, max_side);
            editor.request_view(ctx, (full, visible), max_side);
            let painter = ctx.layer_painter(egui::LayerId::background());
            let uv = |p: egui::Pos2| egui::Pos2::ZERO + (p - full.min) / full.size();
            if let Some(paint) = editor.photo_paint() {
                paint.paint(
                    &painter.with_clip_rect(visible),
                    visible,
                    egui::Rect::from_min_max(uv(visible.min), uv(visible.max)),
                );
            }
            // Split: the "before" left of the line, as the canvas paints it.
            if let (Some(before), Some(x)) =
                (editor.before_paint(), editor.develop.split_x(full, visible))
            {
                let left = egui::Rect::from_min_max(visible.min, egui::pos2(x, visible.max.y));
                if left.is_positive() {
                    let clipped = painter.with_clip_rect(visible);
                    let shapes = before.paint_shapes(
                        &clipped,
                        left,
                        egui::Rect::from_min_max(uv(left.min), uv(left.max)),
                    );
                    clipped.add(egui::Shape::Vec(shapes));
                }
            }
        });
        std::thread::sleep(Duration::from_millis(2));
        result
    }

    fn sharp(&self) -> bool {
        let stats = self.editor.display_stats();
        self.editor.loaded.is_some()
            && self.editor.developing.is_none()
            && self.editor.painted_revision == Some(self.editor.revision)
            && stats["settled"] == true
    }

    /// Frames until the view is sharp: (ms, frames, UI ms per frame).
    fn wait_sharp(&mut self, label: &str) -> (f64, usize, Vec<f64>) {
        let began = Instant::now();
        let mut frames = Vec::new();
        loop {
            let (cpu, ..) = self.step(false);
            frames.push(cpu);
            if self.sharp() {
                return (began.elapsed().as_secs_f64() * 1000.0, frames.len(), frames);
            }
            assert!(
                began.elapsed() < Duration::from_secs(120),
                "{label}: {}",
                self.editor.display_stats()
            );
        }
    }
}

#[test]
#[ignore = "real master and GPU: run explicitly with STREHL_UI_BENCH_RUN"]
fn zoom_benchmark_on_a_real_master() {
    let Ok(run) = std::env::var("STREHL_UI_BENCH_RUN") else {
        eprintln!("STREHL_UI_BENCH_RUN is not set");
        return;
    };
    let run = PathBuf::from(run);
    let out =
        PathBuf::from(std::env::var("STREHL_UI_BENCH_OUT").unwrap_or_else(|_| "bench-out".into()));
    std::fs::create_dir_all(&out).unwrap();
    let gpu = Gpu::new();
    let ctx = egui::Context::default();
    ctx.set_pixels_per_point(1.0);
    let max_side = gpu.render.device.limits().max_texture_dimension_2d;
    let mut editor = EditorState::default();
    editor.viewport.presenter = Some(PhotoPresenter::offscreen(gpu.render.clone(), ctx.clone()));
    editor.recovery_root = Some(out.join("recovery"));
    let opened = Instant::now();
    editor.open(run.join("result.tiff"));
    let mut bench = Bench {
        gpu,
        ctx,
        editor,
        source: [1, 1],
        view: (1.0, [0.5, 0.5]),
        start: Instant::now(),
        max_side,
    };
    while bench.editor.loaded.is_none() {
        assert!(bench.editor.error.is_none(), "{:?}", bench.editor.error);
        bench.step(false);
    }
    let loaded = bench.editor.loaded.as_ref().unwrap();
    bench.source = [loaded.image.width, loaded.image.height];
    let source = bench.source;
    let preview = [loaded.preview.width, loaded.preview.height];
    let fitted = fit(source);
    bench.view = (fitted, [0.5, 0.5]);
    let (first, ..) = bench.wait_sharp("open");
    let mut report = serde_json::json!({
        "master": source,
        "overview": preview,
        "canvas": CANVAS,
        "open_to_sharp_ms": opened.elapsed().as_secs_f64() * 1000.0,
        "fit_scale": fitted,
        "fit_after_load_ms": first,
        "fit": bench.editor.display_stats(),
    });
    eprintln!("open: {}", report);
    // Zoom steps, each cold from a settled fit view: time to sharp pixels,
    // the level and pixels published.
    let centre = [0.45, 0.42];
    let mut steps = Vec::new();
    for (label, scale) in [
        ("fit", fitted),
        ("50 %", 0.5),
        ("100 %", 1.0),
        ("200 %", 2.0),
        ("400 %", 4.0),
    ] {
        bench.view = (fitted, centre);
        bench.wait_sharp("fit before a step");
        drop_detail(&mut bench.editor.viewport);
        bench.view = (scale, centre);
        let (ms, frames, cpu) = bench.wait_sharp(label);
        let stats = bench.editor.display_stats();
        let step = serde_json::json!({
            "view": label, "scale": scale, "to_sharp_ms": ms, "frames": frames,
            "ui_ms": summary(&cpu),
            "requested": stats["requested"], "published": stats["published"],
            "cache_bytes": stats.get("cache_bytes"), "tiles_cached": stats.get("tiles_cached"),
            "tiles_present_ms": stats.get("last_sharp_ms"),
            "jobs": stats["jobs"],
        });
        eprintln!("{step}");
        steps.push(step);
    }
    report["steps"] = serde_json::Value::Array(steps);
    // Warm: back to 100 % after a step away (the cache keeps its tiles).
    bench.view = (1.0, centre);
    bench.wait_sharp("100 %");
    bench.view = (4.0, centre);
    bench.wait_sharp("400 %");
    bench.view = (1.0, centre);
    let (warm, ..) = bench.wait_sharp("100 % again");
    report["warm_return_to_100_ms"] = serde_json::json!(warm);
    if std::env::var("STREHL_UI_BENCH_EXPORT").as_deref() != Ok("0") {
        compare_with_export(&mut bench, &out, &mut report, centre);
        compare_export_view(&mut bench, &out, &mut report, centre);
    }
    run_interactions(&mut bench, &mut report, centre, fitted);
    report["final_stats"] = bench.editor.display_stats();
    let name = out.join(format!("zoom-benchmark-{}x{}.json", source[0], source[1]));
    std::fs::write(&name, serde_json::to_string_pretty(&report).unwrap()).unwrap();
    eprintln!("written {}", name.display());
    // Leave the scratch copy's recipe as it was.
    let _ = bench.editor.flush();
}

/// 100 %: the displayed pixels against the export's at the same place.
fn compare_with_export(
    bench: &mut Bench,
    out: &std::path::Path,
    report: &mut serde_json::Value,
    centre: [f32; 2],
) {
    let source = bench.source;
    bench.view = (1.0, centre);
    bench.wait_sharp("100 % for readback");
    let (.., pixels) = bench.step(true);
    let pixels = pixels.unwrap();
    let recipe = bench.editor.recipe.clone();
    let image = bench.editor.loaded.as_ref().unwrap().image.clone();
    let export = out.join(format!(
        "export-{}.png",
        std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .unwrap()
            .as_millis()
    ));
    let exported = Instant::now();
    strehl_edit::export_image(
        &export,
        &image,
        &recipe,
        &strehl_edit::ExportSettings {
            format: strehl_edit::ExportFormat::Png,
            color_space: strehl_edit::OutputColorSpace::Srgb,
            hdr: false,
            ..Default::default()
        },
        &std::sync::atomic::AtomicBool::new(false),
    )
    .unwrap();
    let export_ms = exported.elapsed().as_secs_f64() * 1000.0;
    let decoded = image::open(&export).unwrap().to_rgb16();
    let _ = std::fs::remove_file(&export);
    // Canvas pixel (x, y) shows source pixel centre*source + (x+0.5 - W/2).
    let (full, _) = mapping(source, 1.0, centre);
    let crop = [400u32, 300u32];
    let origin = [(CANVAS[0] - crop[0]) / 2, (CANVAS[1] - crop[1]) / 2];
    let mut best = (u64::MAX, 0i32, 0i32, 0u32);
    for dy in -2i32..=2 {
        for dx in -2i32..=2 {
            let mut total = 0u64;
            let mut worst = 0u32;
            for y in 0..crop[1] {
                for x in 0..crop[0] {
                    let cx = origin[0] + x;
                    let cy = origin[1] + y;
                    let sx = (cx as f32 + 0.5 - full.min.x).floor() as i32 + dx;
                    let sy = (cy as f32 + 0.5 - full.min.y).floor() as i32 + dy;
                    let e = decoded.get_pixel(sx as u32, sy as u32).0;
                    let d = ((cy * CANVAS[0] + cx) * 4) as usize;
                    for c in 0..3 {
                        let code = (u32::from(e[c]) + 128) / 257;
                        let diff = code.abs_diff(u32::from(pixels[d + c]));
                        total += u64::from(diff);
                        worst = worst.max(diff);
                    }
                }
            }
            if total < best.0 {
                best = (total, dx, dy, worst);
            }
        }
    }
    // Native crops with identical display transforms (none): canvas and export.
    let mut shown = image::RgbImage::new(crop[0], crop[1]);
    let mut native = image::RgbImage::new(crop[0], crop[1]);
    for y in 0..crop[1] {
        for x in 0..crop[0] {
            let cx = origin[0] + x;
            let cy = origin[1] + y;
            let d = ((cy * CANVAS[0] + cx) * 4) as usize;
            shown.put_pixel(x, y, image::Rgb([pixels[d], pixels[d + 1], pixels[d + 2]]));
            let sx = (cx as f32 + 0.5 - full.min.x).floor() as i32 + best.1;
            let sy = (cy as f32 + 0.5 - full.min.y).floor() as i32 + best.2;
            let e = decoded.get_pixel(sx as u32, sy as u32).0;
            native.put_pixel(
                x,
                y,
                image::Rgb(e.map(|v| ((u32::from(v) + 128) / 257) as u8)),
            );
        }
    }
    shown.save(out.join("crop-100-displayed.png")).unwrap();
    native.save(out.join("crop-100-export.png")).unwrap();
    report["readback_100"] = serde_json::json!({
        "crop": crop, "canvas_origin": origin, "best_offset": [best.1, best.2],
        "sum_abs_diff": best.0, "max_abs_diff": best.3, "export_ms": export_ms,
    });
    eprintln!("readback at 100 %: {}", report["readback_100"]);
}

fn run_interactions(
    bench: &mut Bench,
    report: &mut serde_json::Value,
    centre: [f32; 2],
    fitted: f32,
) {
    let source = bench.source;
    bench.view = (1.0, centre);
    bench.wait_sharp("before the pan");
    let repeats: usize = std::env::var("STREHL_UI_BENCH_PAN_REPEAT")
        .ok()
        .and_then(|v| v.parse().ok())
        .unwrap_or(0);
    for repeat in 0..repeats {
        drop_detail(&mut bench.editor.viewport);
        let start = [
            0.2 + 0.1 * (repeat % 4) as f32,
            0.3 + 0.1 * (repeat % 3) as f32,
        ];
        bench.view = (1.0, start);
        bench.wait_sharp("before a repeated pan");
        let mut frames = Vec::new();
        for i in 0..300 {
            let x = start[0] + (i as f32 * 6.0) / source[0] as f32;
            bench.view = (1.0, [x, start[1]]);
            frames.push(bench.step(false).0);
        }
        eprintln!("repeated pan {repeat}: {}", summary(&frames));
    }
    // A drag at 100 %: 6 physical pixels per frame for 300 frames (1800 px).
    let mut pan_cpu = Vec::new();
    let mut pan_total = Vec::new();
    let mut soft = 0;
    for i in 0..300 {
        let x = centre[0] + (i as f32 * 6.0) / source[0] as f32;
        bench.view = (1.0, [x, centre[1]]);
        let (cpu, total, _) = bench.step(false);
        pan_cpu.push(cpu);
        pan_total.push(total);
        // Not sharp: detail pending, missing or still fading in.
        if !bench.sharp() {
            soft += 1;
        }
    }
    let (after_pan, ..) = bench.wait_sharp("after the pan");
    report["pan_100"] = serde_json::json!({
        "ui_ms": summary(&pan_cpu), "until_gpu_ms": summary(&pan_total),
        "frames_not_sharp": soft, "after_pan_to_sharp_ms": after_pan,
    });
    eprintln!("pan at 100 %: {}", report["pan_100"]);
    // A continuous zoom from fit to 400 % over 90 frames.
    let mut zoom_cpu = Vec::new();
    for i in 0..=90 {
        let t = i as f32 / 90.0;
        bench.view = (fitted * (4.0 / fitted).powf(t), centre);
        zoom_cpu.push(bench.step(false).0);
    }
    let (after_zoom, ..) = bench.wait_sharp("after the zoom");
    report["zoom_sweep"] = serde_json::json!({
        "ui_ms": summary(&zoom_cpu), "after_zoom_to_sharp_ms": after_zoom,
    });
    eprintln!("zoom sweep: {}", report["zoom_sweep"]);
    // A slider drag at 100 %: one exposure step every 16.7 ms (60 Hz) for 40
    // steps, frames in between; latency from an edit to its overview.
    bench.view = (1.0, centre);
    bench.wait_sharp("before the drag");
    let mut drag_cpu = Vec::new();
    let mut overview_ms = Vec::new();
    let mut edits = std::collections::HashMap::new();
    let mut painted = bench.editor.painted_revision;
    let base = bench.editor.recipe.clone();
    let began = Instant::now();
    for i in 0..40 {
        let mut next = base.clone();
        next.global.exposure = base.global.exposure + 0.01 * (i + 1) as f32;
        bench.editor.replace(next).unwrap();
        edits.insert(bench.editor.revision, Instant::now());
        let due = began + Duration::from_secs_f64((i + 1) as f64 / 60.0);
        while Instant::now() < due {
            let (cpu, ..) = bench.step(false);
            drag_cpu.push(cpu);
            if bench.editor.painted_revision != painted {
                painted = bench.editor.painted_revision;
                if let Some(at) = painted.and_then(|r| edits.get(&r)) {
                    overview_ms.push(at.elapsed().as_secs_f64() * 1000.0);
                }
            }
        }
    }
    let (after_drag, ..) = bench.wait_sharp("after the drag");
    bench.editor.replace(base).unwrap();
    bench.wait_sharp("restored");
    report["slider_drag_100"] = serde_json::json!({
        "ui_ms": summary(&drag_cpu),
        "edit_to_overview_ms": summary(&overview_ms),
        "release_to_sharp_ms": after_drag,
    });
    eprintln!("slider drag at 100 %: {}", report["slider_drag_100"]);
    // Split at 100 %: the "before" half's own tiles, then the line dragged
    // from 0.1 to 0.9 of the view over 120 frames.
    bench.view = (1.0, centre);
    bench.editor.develop.compare = crate::develop_station::Compare::Split;
    bench.editor.develop.split = 0.1;
    let began = Instant::now();
    while !(bench.editor.before_overview.is_some() && bench.editor.before_view.settled()) {
        bench.step(false);
        assert!(began.elapsed() < Duration::from_secs(120), "split before");
    }
    let before_sharp = began.elapsed().as_secs_f64() * 1000.0;
    let mut split_cpu = Vec::new();
    let mut soft = 0;
    for i in 0..120 {
        bench.editor.develop.split = 0.1 + 0.8 * i as f32 / 119.0;
        split_cpu.push(bench.step(false).0);
        if !bench.editor.before_view.settled() {
            soft += 1;
        }
    }
    let began = Instant::now();
    while !bench.editor.before_view.settled() {
        bench.step(false);
        assert!(
            began.elapsed() < Duration::from_secs(120),
            "split after drag"
        );
    }
    report["split_100"] = serde_json::json!({
        "before_half_to_sharp_ms": before_sharp,
        "drag_ui_ms": summary(&split_cpu),
        "drag_frames_not_sharp": soft,
        "after_drag_to_sharp_ms": began.elapsed().as_secs_f64() * 1000.0,
        "before_view": bench.editor.before_view.stats(),
    });
    eprintln!("split at 100 %: {}", report["split_100"]);
    bench.editor.develop.compare = crate::develop_station::Compare::After;
}

/// A 14064 x 9376 render folder for the benchmark (the four-shot size, no
/// such render exists yet): the weevil master upsampled 2x (each pixel a 2x2
/// block), a header-only stand-in for `result.tiff` (the editor reads only its
/// dimensions), and the weevil's recipe. Performance only: no detail claim.
#[test]
#[ignore = "writes a 1.6 GB scratch master: run explicitly with STREHL_UI_BENCH_SYNTH_FROM/TO"]
fn make_synthetic_four_shot_render() {
    let (Ok(from), Ok(to)) = (
        std::env::var("STREHL_UI_BENCH_SYNTH_FROM"),
        std::env::var("STREHL_UI_BENCH_SYNTH_TO"),
    ) else {
        eprintln!("STREHL_UI_BENCH_SYNTH_FROM/TO are not set");
        return;
    };
    let (from, to) = (PathBuf::from(from), PathBuf::from(to));
    assert!(
        !to.join("master.tiff").exists(),
        "choose an empty destination"
    );
    std::fs::create_dir_all(&to).unwrap();
    let small = strehl_edit::load_tiff(&from.join("master.tiff")).unwrap();
    let (w, h) = (small.width as usize, small.height as usize);
    let mut pixels = vec![0f32; w * h * 12];
    for y in 0..h * 2 {
        for x in 0..w * 2 {
            let s = ((y / 2) * w + x / 2) * 3;
            let d = (y * w * 2 + x) * 3;
            pixels[d..d + 3].copy_from_slice(&small.pixels[s..s + 3]);
        }
    }
    let large = strehl_edit::LinearImage {
        width: small.width * 2,
        height: small.height * 2,
        pixels,
        ..small
    };
    strehl_edit::save_linear_tiff(&to.join("master.tiff"), &large).unwrap();
    image::GrayImage::new(large.width, large.height)
        .save_with_format(to.join("result.tiff"), image::ImageFormat::Png)
        .unwrap();
    std::fs::copy(
        from.join("result.strehl-edits.json"),
        to.join("result.strehl-edits.json"),
    )
    .unwrap();
    eprintln!(
        "synthetic {} x {} render in {}",
        large.width,
        large.height,
        to.display()
    );
}

/// Export: the Web preset (JPEG, sRGB, 2560 px) at one output pixel per
/// screen pixel, read back and compared with the export pipeline's file.
fn compare_export_view(
    bench: &mut Bench,
    out: &std::path::Path,
    report: &mut serde_json::Value,
    centre: [f32; 2],
) {
    let source = bench.source;
    let settings = strehl_edit::ExportSettings {
        format: strehl_edit::ExportFormat::Jpeg,
        color_space: strehl_edit::OutputColorSpace::Srgb,
        hdr: false,
        quality: 90,
        resize: Some(strehl_edit::Resize {
            long_edge: 2560,
            filter: strehl_edit::ResizeFilter::Mitchell,
        }),
        ..Default::default()
    };
    let output = settings.resize.unwrap().target(source).unwrap();
    let scale = output[0] as f32 / source[0] as f32;
    bench.view = (scale, centre);
    bench.wait_sharp("Export fitted to the output");
    let chosen = Instant::now();
    bench
        .editor
        .viewport
        .want_export(Some(super::ExportRequest {
            settings: settings.clone(),
            um_per_px: None,
        }));
    let (shown_ms, ..) = bench.wait_sharp("Export preview");
    let stats = bench.editor.display_stats();
    assert!(stats["export"]["shown"].is_array(), "{stats}");
    let _ = chosen;
    let (.., pixels) = bench.step(true);
    let pixels = pixels.unwrap();
    let path = out.join("export-web.png");
    let _ = std::fs::remove_file(&path);
    let image = bench.editor.loaded.as_ref().unwrap().image.clone();
    strehl_edit::export_image(
        &path,
        &image,
        &bench.editor.recipe,
        &strehl_edit::ExportSettings {
            format: strehl_edit::ExportFormat::Png,
            quality: 100,
            ..settings
        },
        &std::sync::atomic::AtomicBool::new(false),
    )
    .unwrap();
    let decoded = image::open(&path).unwrap().to_rgb16();
    let _ = std::fs::remove_file(&path);
    assert_eq!([decoded.width(), decoded.height()], output);
    let (full, _) = mapping(source, scale, centre);
    // Output pixels per canvas pixel: exactly one.
    let per = output[0] as f32 / full.width();
    let crop = [400u32, 300u32];
    let origin = [(CANVAS[0] - crop[0]) / 2, (CANVAS[1] - crop[1]) / 2];
    let at = |cx: u32, cy: u32, dx: i32, dy: i32| {
        let ox = ((cx as f32 + 0.5 - full.min.x) * per).floor() as i32 + dx;
        let oy = ((cy as f32 + 0.5 - full.min.y) * per).floor() as i32 + dy;
        decoded
            .get_pixel(ox as u32, oy as u32)
            .0
            .map(|v| ((u32::from(v) + 128) / 257) as u8)
    };
    let mut best = (u64::MAX, 0i32, 0i32, 0u32);
    for dy in -2i32..=2 {
        for dx in -2i32..=2 {
            let (mut total, mut worst) = (0u64, 0u32);
            for y in 0..crop[1] {
                for x in 0..crop[0] {
                    let (cx, cy) = (origin[0] + x, origin[1] + y);
                    let e = at(cx, cy, dx, dy);
                    let d = ((cy * CANVAS[0] + cx) * 4) as usize;
                    for c in 0..3 {
                        let diff = u32::from(e[c]).abs_diff(u32::from(pixels[d + c]));
                        total += u64::from(diff);
                        worst = worst.max(diff);
                    }
                }
            }
            if total < best.0 {
                best = (total, dx, dy, worst);
            }
        }
    }
    let mut shown = image::RgbImage::new(crop[0], crop[1]);
    let mut native = image::RgbImage::new(crop[0], crop[1]);
    for y in 0..crop[1] {
        for x in 0..crop[0] {
            let (cx, cy) = (origin[0] + x, origin[1] + y);
            let d = ((cy * CANVAS[0] + cx) * 4) as usize;
            shown.put_pixel(x, y, image::Rgb([pixels[d], pixels[d + 1], pixels[d + 2]]));
            native.put_pixel(x, y, image::Rgb(at(cx, cy, best.1, best.2)));
        }
    }
    shown
        .save(out.join("crop-export-web-displayed.png"))
        .unwrap();
    native.save(out.join("crop-export-web-file.png")).unwrap();
    report["export_view"] = serde_json::json!({
        "preset": "Web: JPEG sRGB, long edge 2560 (compared before encoding)",
        "output": output, "scale": scale, "preview_ms": stats["export"]["last_ms"],
        "chosen_to_shown_ms": shown_ms,
        "crop": crop, "best_offset": [best.1, best.2],
        "sum_abs_diff": best.0, "max_abs_diff": best.3,
    });
    eprintln!("export view: {}", report["export_view"]);
    bench.editor.viewport.want_export(None);
    bench.wait_sharp("Export closed");
}
