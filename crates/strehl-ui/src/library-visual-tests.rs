//! Offscreen pictures of the Library and Subject screens for the side-by-side
//! check against the mockup references (plan 10.2). Ignored: needs a GPU and
//! writes PNGs into `STREHL_P4_SHOTS`. With `STREHL_P4_CATALOG` set to a copy
//! of a catalog, the screens show that catalog instead of the fixture.
//!
//! The GPU helpers repeat `app-offscreen.rs` (not editable in this phase);
//! stage 2 replaces this with `--route library` in the real offscreen path.
use super::tests::{BASE, develop, draft, run};
use super::*;
use crate::subject_page::{SubjectInputs, SubjectPage};
use anyhow::{Context as _, Result, ensure};
use eframe::egui_wgpu::{RenderState, RendererOptions, ScreenDescriptor};
use image::ImageEncoder;
use std::{
    future::Future,
    sync::Arc,
    task::{Context as TaskContext, Poll, Wake, Waker},
    time::{Duration, Instant},
};

const SIZE: [u32; 2] = [1680, 982];

/// The mockup's subjects, with synthetic pictures.
fn mockup_catalog(pictures: &Path) -> (Catalog, NodeId) {
    let mut catalog = Catalog::default();
    let collections: Vec<NodeId> = ["Insects", "Minerals", "Plants and food", "Test targets"]
        .iter()
        .map(|name| catalog.create_project(name).unwrap())
        .collect();
    let subjects = [
        ("Blue weevil", 0, 3, [40, 170, 190]),
        ("Net-patterned beetle", 0, 1, [20, 120, 110]),
        ("White scarab", 0, 2, [200, 200, 195]),
        ("Orange weevil", 0, 1, [200, 130, 40]),
        ("Spotted flower beetle", 0, 2, [60, 140, 90]),
        ("Jewel beetle", 0, 2, [90, 60, 130]),
        ("Green scarab, wing case", 0, 4, [40, 160, 60]),
        ("Speckled weevil", 0, 3, [70, 90, 50]),
        ("Bumblebee", 0, 2, [190, 160, 80]),
        ("Etched garnet", 1, 2, [150, 20, 40]),
        ("Peacock ore", 1, 1, [30, 70, 120]),
        ("Marigold", 2, 1, [230, 170, 30]),
        ("Star sand", 1, 1, [210, 205, 200]),
        ("Chia seeds", 2, 1, [120, 120, 110]),
        ("Decapped chip", 3, 1, [120, 140, 60]),
    ];
    let mut first = 0;
    for (index, (name, collection, stacks, rgb)) in subjects.iter().enumerate() {
        let picture = pictures.join(format!("{index:02}.png"));
        let rgb = *rgb;
        image::RgbImage::from_fn(600, 400, |x, y| {
            let shade = 0.35
                + 0.65
                    * (1.0
                        - ((x as f32 - 300.0).powi(2) + (y as f32 - 200.0).powi(2)).sqrt() / 360.0)
                        .max(0.0);
            image::Rgb(rgb.map(|c| (c as f32 * shade) as u8))
        })
        .save(&picture)
        .unwrap();
        let subject = catalog
            .create_subject(collections[*collection], name)
            .unwrap();
        if index == 0 {
            first = subject;
        }
        for s in 0..*stacks {
            let source = format!("/captures/{index}/{s}/100MSDCF");
            let stack = catalog
                .create_stack(
                    subject,
                    [
                        "Dorsal · 2.8×",
                        "Lateral · 2.8×",
                        "Wing case · 5.6×",
                        "Head",
                    ][s % 4],
                    draft(&source, 9_000_000_000 + (index as u64 * 1_300_000_000)),
                )
                .unwrap();
            let created = BASE + (index * 10 + s) as u64 * 86_400;
            let directory = format!("/out/strehl-{index}-{s}-1");
            match (index + s) % 5 {
                0 => {}
                1 => {
                    catalog
                        .add_revision(stack, run(&directory, &source, "Saved", created))
                        .unwrap();
                    catalog
                        .add_revision(
                            stack,
                            run(&format!("{directory}b"), &source, "Failed", created + 60),
                        )
                        .unwrap();
                }
                2 => catalog
                    .add_revision(stack, run(&directory, &source, "Saved", created))
                    .unwrap(),
                _ => {
                    catalog
                        .add_revision(stack, run(&directory, &source, "Saved", created))
                        .unwrap();
                    develop(
                        &mut catalog,
                        stack,
                        &directory,
                        (index * 10 + s) as u64,
                        created,
                    );
                }
            }
        }
        catalog
            .set_subject_meta(
                subject,
                SubjectEdit {
                    hero: Some(Some(picture)),
                    notes: (index == 0).then(|| {
                        "Pinned specimen on a dark field. Dorsal view first, then lateral. Two diffused panels, left one a stop brighter.".to_owned()
                    }),
                    optics: (index == 0).then(|| {
                        Some(crate::workspace_history::Optics {
                            camera: "ILCE-7CR".into(),
                            lens: "FE 100mm F2.8 Macro GM + 2× converter".into(),
                        })
                    }),
                    scale: (index == 0).then(|| {
                        Some(crate::workspace_history::ScaleCalibration::entered(2.8, 3.76).unwrap())
                    }),
                },
            )
            .unwrap();
    }
    (catalog, first)
}

#[test]
#[ignore = "needs a GPU; writes PNGs into STREHL_P4_SHOTS"]
fn offscreen_library_and_subject_pictures() {
    let shots = PathBuf::from(std::env::var_os("STREHL_P4_SHOTS").expect("STREHL_P4_SHOTS"));
    std::fs::create_dir_all(&shots).unwrap();
    let pictures = tempfile::tempdir().unwrap();
    let (catalog, first) = match std::env::var_os("STREHL_P4_CATALOG") {
        Some(path) => {
            let catalog = Catalog::load(Some(PathBuf::from(path)));
            assert!(catalog.load_error.is_none(), "{:?}", catalog.load_error);
            let first = catalog
                .nodes
                .iter()
                .filter(|n| n.kind == NodeKind::Subject)
                .max_by_key(|n| catalog.subject_summary(n.id).map_or(0, |s| s.renders))
                .unwrap()
                .id;
            (catalog, first)
        }
        None => mockup_catalog(pictures.path()),
    };
    let rig = RigCapture {
        subject: Some(first),
        stack: catalog.stacks_of(first).first().copied(),
        title: "Blue weevil · Dorsal · 2.8×".into(),
        detail:
            "Capturing plane 61 of 96 · 3 min 18 s left · every plane so far has passed its check"
                .into(),
        progress: 0.635,
        picture: None,
    };
    let storage = StorageCard {
        volume: "D:".into(),
        free: 371_000_000_000,
        total: 1_900_000_000_000,
        compactable: Some((14, 410_000_000_000)),
    };
    let palette = LibraryPalette::graphite();
    let mut station = LibraryStation::default();
    let mut page = SubjectPage::default();
    let mut previews = LibraryPreviews::default();
    let signatures: HashMap<NodeId, Vec<f32>> = catalog
        .stacks_of(first)
        .into_iter()
        .enumerate()
        .map(|(n, stack)| {
            let series = (0..299)
                .map(|i| {
                    let x = i as f32 / 299.0;
                    let ridge = (-((x - 0.45 - n as f32 * 0.05) * 7.0).powi(2)).exp();
                    ridge * (0.7 + 0.3 * ((i * 7919 % 97) as f32 / 97.0))
                })
                .collect();
            (stack, series)
        })
        .collect();
    // Fixture folders do not exist; show them present except one moved.
    let fixture = std::env::var_os("STREHL_P4_CATALOG").is_none();
    let present: HashMap<NodeId, SourcesState> = catalog
        .nodes
        .iter()
        .filter(|n| n.kind == NodeKind::Stack)
        .map(|n| {
            let moved = catalog
                .subject_of(n.id)
                .and_then(|s| catalog.node(s))
                .is_some_and(|s| s.name == "Peacock ore");
            (
                n.id,
                if moved {
                    SourcesState::Missing
                } else {
                    SourcesState::Present
                },
            )
        })
        .collect();
    render(&shots.join("library.png"), |ui| {
        if fixture {
            station.set_sources(present.clone());
        }
        station.show(
            ui,
            LibraryInputs {
                catalog: &catalog,
                revision: 1,
                previews: &mut previews,
                palette: &palette,
                rig: Some(&rig),
                storage: Some(&storage),
            },
        );
        !previews.pending()
    })
    .unwrap();
    let sources = station.sources().clone();
    render(&shots.join("subject.png"), |ui| {
        page.show(
            ui,
            SubjectInputs {
                catalog: &catalog,
                revision: 1,
                subject: first,
                previews: &mut previews,
                palette: &palette,
                rig: None,
                sources: &sources,
                signatures: Some(&signatures),
            },
        );
        !previews.pending()
    })
    .unwrap();
}

/// Paint `draw` until it reports ready (and at least a few frames), then save.
fn render(destination: &Path, mut draw: impl FnMut(&mut Ui) -> bool) -> Result<()> {
    let deadline = Instant::now() + Duration::from_secs(120);
    let config = crate::hdr_display::configuration();
    let instance = wait_until(config.wgpu_setup.new_instance(), deadline)?;
    let render = wait_until(
        RenderState::create(&config, &instance, None, RendererOptions::default()),
        deadline,
    )??;
    let canvas = render.device.create_texture(&wgpu::TextureDescriptor {
        label: Some("Strehl library offscreen"),
        size: wgpu::Extent3d {
            width: SIZE[0],
            height: SIZE[1],
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
    crate::theme::install(&ctx);
    ctx.set_pixels_per_point(1.0);
    let started = Instant::now();
    let mut frames = 0;
    let mut ready_frames = 0;
    while Instant::now() < deadline {
        let screen = Rect::from_min_size(Pos2::ZERO, Vec2::new(SIZE[0] as f32, SIZE[1] as f32));
        let raw = egui::RawInput {
            screen_rect: Some(screen),
            time: Some(started.elapsed().as_secs_f64()),
            focused: true,
            ..Default::default()
        };
        let mut ready = false;
        let output = ctx.run(raw, |ctx| {
            egui::CentralPanel::default()
                .frame(egui::Frame::NONE)
                .show(ctx, |ui| ready = draw(ui));
        });
        frames += 1;
        ready_frames = if ready { ready_frames + 1 } else { 0 };
        let capture = ready_frames >= 3 && frames >= 6;
        let primitives = ctx.tessellate(output.shapes, output.pixels_per_point);
        let screen_descriptor = ScreenDescriptor {
            size_in_pixels: SIZE,
            pixels_per_point: output.pixels_per_point,
        };
        if let Some((buffer, submission, padded_row)) = paint_frame(
            &render,
            &canvas,
            &primitives,
            &output.textures_delta,
            &screen_descriptor,
            capture,
        )? {
            let rgba = read_pixels(&render.device, buffer, submission, padded_row, deadline)?;
            let file = std::fs::File::create(destination)?;
            image::codecs::png::PngEncoder::new(std::io::BufWriter::new(file)).write_image(
                &rgba,
                SIZE[0],
                SIZE[1],
                image::ExtendedColorType::Rgba8,
            )?;
            eprintln!("library-visual: saved {}", destination.display());
            return Ok(());
        }
        render.device.poll(wgpu::PollType::Poll)?;
        std::thread::sleep(Duration::from_millis(16));
    }
    anyhow::bail!("not ready before the deadline")
}

fn paint_frame(
    render: &RenderState,
    canvas: &wgpu::Texture,
    primitives: &[egui::ClippedPrimitive],
    delta: &egui::TexturesDelta,
    screen: &ScreenDescriptor,
    capture: bool,
) -> Result<Option<(wgpu::Buffer, wgpu::SubmissionIndex, u32)>> {
    let mut encoder = render
        .device
        .create_command_encoder(&wgpu::CommandEncoderDescriptor { label: None });
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
        render
            .renderer
            .read()
            .render(&mut pass.forget_lifetime(), primitives, screen);
    }
    let readback = if capture {
        let padded_row = (SIZE[0] * 4).div_ceil(wgpu::COPY_BYTES_PER_ROW_ALIGNMENT)
            * wgpu::COPY_BYTES_PER_ROW_ALIGNMENT;
        let buffer = render.device.create_buffer(&wgpu::BufferDescriptor {
            label: None,
            size: u64::from(padded_row) * u64::from(SIZE[1]),
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
                    rows_per_image: Some(SIZE[1]),
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
    for id in &delta.free {
        render.renderer.write().free_texture(id);
    }
    Ok(readback.map(|(buffer, padded_row)| (buffer, submission, padded_row)))
}

fn read_pixels(
    device: &wgpu::Device,
    buffer: wgpu::Buffer,
    submission: wgpu::SubmissionIndex,
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
        .context("readback wait")?;
    receiver
        .recv_timeout(deadline.saturating_duration_since(Instant::now()))
        .context("readback callback")?
        .context("map")?;
    let mapped = buffer.slice(..).get_mapped_range();
    let row_bytes = SIZE[0] as usize * 4;
    let mut rgba = Vec::with_capacity(row_bytes * SIZE[1] as usize);
    for row in mapped
        .chunks_exact(padded_row as usize)
        .take(SIZE[1] as usize)
    {
        rgba.extend_from_slice(&row[..row_bytes]);
    }
    drop(mapped);
    buffer.unmap();
    ensure!(
        rgba.len() == row_bytes * SIZE[1] as usize,
        "incomplete readback"
    );
    Ok(rgba)
}

struct WakeThread(std::thread::Thread);
impl Wake for WakeThread {
    fn wake(self: Arc<Self>) {
        self.0.unpark();
    }
}
fn wait_until<F: Future>(future: F, deadline: Instant) -> Result<F::Output> {
    let waker = Waker::from(Arc::new(WakeThread(std::thread::current())));
    let mut context = TaskContext::from_waker(&waker);
    let mut future = std::pin::pin!(future);
    loop {
        ensure!(Instant::now() < deadline, "GPU initialization timed out");
        if let Poll::Ready(value) = future.as_mut().poll(&mut context) {
            return Ok(value);
        }
        std::thread::park_timeout(Duration::from_millis(25));
    }
}
