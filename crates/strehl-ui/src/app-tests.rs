//! Independent consumer checks. Deliberately vary selection, generation, image
//! identity and viewport size rather than recomputing the producer's formulas.

use super::*;
use crate::{jobs::FrameFile, source_preview};
use eframe::egui::{Context, Pos2, RawInput, Rect};

fn app() -> StrehlApp {
    StrehlApp::from_launch(4096, LaunchOptions::default())
}

fn stack(count: usize) -> StackScan {
    StackScan {
        directory: PathBuf::from("independent capture with a deliberately long name"),
        frames: (0..count)
            .map(|index| FrameFile {
                path: PathBuf::from(format!("unopened-frame-{index:05}.ARW")),
                bytes: 42,
            })
            .collect(),
        total_bytes: count as u64 * 42,
    }
}

fn camera_stack_with_native_strip(directory: &Path, count: usize) -> StackScan {
    let mut frames = Vec::with_capacity(count);
    for index in 0..count {
        // The filmstrip's real4:3 camera thumbnail is distinct from both3:2
        // detail tiers. Small fixtures exercise delivery identity cheaply.
        let mut jpegs = Vec::new();
        for [width, height] in [[8, 6], [60, 40], [120, 80]] {
            let pixels = image::RgbImage::from_fn(width, height, |x, y| {
                image::Rgb([(x * 7 + index as u32 * 13) as u8, (y * 11) as u8, 61])
            });
            let mut jpeg = Vec::new();
            image::codecs::jpeg::JpegEncoder::new_with_quality(&mut jpeg, 90)
                .encode_image(&pixels)
                .unwrap();
            jpegs.push(jpeg);
        }
        let mut bytes = vec![0_u8; 256 + jpegs.iter().map(Vec::len).sum::<usize>()];
        bytes[..8].copy_from_slice(b"II*\0\x08\0\0\0");
        let mut payload = 256;
        for (tier, jpeg) in jpegs.iter().enumerate() {
            let offset = 8 + tier * 64;
            bytes[offset..offset + 2].copy_from_slice(&2_u16.to_le_bytes());
            for (position, (tag, value)) in [(513_u16, payload as u32), (514, jpeg.len() as u32)]
                .into_iter()
                .enumerate()
            {
                let entry = offset + 2 + position * 12;
                bytes[entry..entry + 2].copy_from_slice(&tag.to_le_bytes());
                bytes[entry + 2..entry + 4].copy_from_slice(&4_u16.to_le_bytes());
                bytes[entry + 4..entry + 8].copy_from_slice(&1_u32.to_le_bytes());
                bytes[entry + 8..entry + 12].copy_from_slice(&value.to_le_bytes());
            }
            let next = if tier == 2 {
                0
            } else {
                (8 + (tier + 1) * 64) as u32
            };
            bytes[offset + 26..offset + 30].copy_from_slice(&next.to_le_bytes());
            bytes[payload..payload + jpeg.len()].copy_from_slice(jpeg);
            payload += jpeg.len();
        }
        let path = directory.join(format!("native-strip-{index:03}.arw"));
        std::fs::write(&path, &bytes).unwrap();
        frames.push(FrameFile {
            path,
            bytes: bytes.len() as u64,
        });
    }
    StackScan {
        directory: directory.to_path_buf(),
        total_bytes: frames.iter().map(|frame| frame.bytes).sum(),
        frames,
    }
}

fn image(name: &str, color: [u8; 4]) -> PreviewImage {
    PreviewImage {
        path: PathBuf::from(name),
        source_size: [7, 5],
        size: [7, 5],
        rgba: color.repeat(35),
        is_overview: false,
    }
}

fn image_task(name: &str, color: [u8; 4]) -> Task<PreviewImage> {
    let image = image(name, color);
    jobs::spawn_task("independent-image-delivery", move |_| Ok(image))
}

fn wait_for(app: &mut StrehlApp, ctx: &Context, ready: impl Fn(&StrehlApp) -> bool) {
    let deadline = Instant::now() + Duration::from_secs(5);
    while !ready(app) && Instant::now() < deadline {
        app.poll(ctx);
        std::thread::yield_now();
    }
    assert!(
        ready(app),
        "the generated camera-preview fixture never became ready"
    );
}

fn camera_stack(directory: &Path, count: usize, base_width: u32) -> StackScan {
    camera_stack_with_height(directory, count, base_width, 24)
}

// Inspect actual submitted diagnostic markers, including retained meshes. The
// eight triangles at each fan centre distinguish a sample from panel borders,
// image quads, and the corner ticks that describe coefficient spacing.
fn painted_support_markers(output: &egui::FullOutput) -> Vec<(Pos2, Rect)> {
    let ink = GREEN.gamma_multiply(0.88);
    let mut points = Vec::new();
    for shape in &output.shapes {
        match &shape.shape {
            egui::Shape::Circle(circle) if circle.radius == 1.05 && circle.fill == ink => {
                points.push((circle.center, shape.clip_rect));
            }
            egui::Shape::Mesh(mesh) if mesh.texture_id == egui::TextureId::default() => {
                let mut uses = vec![0; mesh.vertices.len()];
                for &index in &mesh.indices {
                    uses[index as usize] += 1;
                }
                points.extend(
                    mesh.vertices
                        .iter()
                        .zip(uses)
                        .filter_map(|(vertex, count)| {
                            (count == 8
                                && vertex.color == ink
                                && shape.clip_rect.contains(vertex.pos))
                            .then_some((vertex.pos, shape.clip_rect))
                        }),
                );
            }
            _ => {}
        }
    }
    points
}

fn camera_stack_with_height(
    directory: &Path,
    count: usize,
    base_width: u32,
    height: u32,
) -> StackScan {
    let mut frames = Vec::with_capacity(count);
    for index in 0..count {
        let pixels = image::RgbImage::from_fn(base_width + index as u32, height, |x, y| {
            image::Rgb([(x * 7) as u8, (y * 9 + index as u32 * 13) as u8, 63])
        });
        let mut jpeg = Vec::new();
        image::codecs::jpeg::JpegEncoder::new_with_quality(&mut jpeg, 90)
            .encode_image(&pixels)
            .unwrap();
        let mut bytes = vec![0_u8; 128 + jpeg.len()];
        bytes[..8].copy_from_slice(b"II*\0\x08\0\0\0");
        bytes[8..10].copy_from_slice(&2_u16.to_le_bytes());
        for (position, (tag, value)) in [(513_u16, 128_u32), (514, jpeg.len() as u32)]
            .into_iter()
            .enumerate()
        {
            let offset = 10 + position * 12;
            bytes[offset..offset + 2].copy_from_slice(&tag.to_le_bytes());
            bytes[offset + 2..offset + 4].copy_from_slice(&4_u16.to_le_bytes());
            bytes[offset + 4..offset + 8].copy_from_slice(&1_u32.to_le_bytes());
            bytes[offset + 8..offset + 12].copy_from_slice(&value.to_le_bytes());
        }
        bytes[128..].copy_from_slice(&jpeg);
        let path = directory.join(format!("frame-{index:03}.arw"));
        std::fs::write(&path, &bytes).unwrap();
        frames.push(FrameFile {
            path,
            bytes: bytes.len() as u64,
        });
    }
    StackScan {
        directory: directory.to_path_buf(),
        total_bytes: frames.iter().map(|frame| frame.bytes).sum(),
        frames,
    }
}

#[test]
fn process_inspection_target_drives_real_detail_and_screenshot_readiness() {
    let ctx = Context::default();
    let directory = jobs::tests::TestDirectory::new("process-foreground-preview-target");
    let mut app = app();
    app.stack = Some(camera_stack(directory.path(), 4, 40));
    app.select(0);
    app.process_view = true;
    app.process_space.inspect_frame(2);
    assert_eq!(
        app.selected, 0,
        "inspection must differ from catalog selection"
    );
    assert_eq!(app.preview_target(), 2);
    wait_for(&mut app, &ctx, |app| {
        app.browser.has_image(app.preview_target()) && !app.browser.active()
    });
    assert_eq!(app.browser.displayed_index(), Some(2));
    assert_eq!(app.source_viewer.source_size, [42, 24]);
    assert!(
        !app.browser.has_image(0),
        "the old selection is not detail-ready"
    );
    assert!(
        app.process_pair()
            .iter()
            .all(|&i| app.source_photo(i).is_some())
    );
    app.updates = 11;
    app.screenshot = Some(directory.path().join("not-written-without-gpu-event.png"));
    app.screenshot(&ctx);
    assert!(
        app.screenshot_requested,
        "readiness must follow the painted source"
    );

    app.process_space.inspect_frame(99);
    assert_eq!(
        app.preview_target(),
        0,
        "invalid inspection cannot request outside the stack"
    );
    app.process_space.inspect_frame(2);
    app.process_view = false;
    assert_eq!(
        app.preview_target(),
        0,
        "Sources uses its own actual selection"
    );
}

#[test]
fn app_scrubbing_retains_the_photo_and_result_while_latest_capture_loads() {
    // This goes through the real app selection and camera-container reader.
    // A reset-to-empty Viewer, a stale source identity, or source/result mixing
    // fails independently of the scheduler's injected-decoder tests.
    let ctx = Context::default();
    let directory = jobs::tests::TestDirectory::new("app-continuous-scrub");
    let mut app = app();
    app.stack = Some(camera_stack(directory.path(), 8, 32));
    app.select(0);
    wait_for(&mut app, &ctx, |app| {
        app.browser.displayed_index() == Some(0)
    });
    let first_id = app.source_viewer.texture.as_ref().unwrap().id();
    let result = cache_image(&ctx, image("finished master.tiff", [18, 35, 231, 255]));
    let result_id = result.texture.id();
    install_viewer(&mut app.result_viewer, &result);
    app.image_path = Some(PathBuf::from("finished master.tiff"));
    app.view = View::Result;
    app.follow_processing = true;

    for index in [6, 2, 7, 3, 6] {
        app.select(index);
        assert!(
            app.follow_processing,
            "Browsing must not silently turn off live following"
        );
        assert!(app.view == View::Sources);
        assert!(app.browser.pending());
        assert_eq!(app.browser.displayed_index(), Some(0));
        assert_eq!(app.source_viewer.texture.as_ref().unwrap().id(), first_id);
    }
    wait_for(&mut app, &ctx, |app| app.browser.has_image(6));
    assert_eq!(app.selected, 6);
    assert_eq!(app.browser.displayed_index(), Some(6));
    assert_eq!(app.source_viewer.source_size, [38, 24]);
    assert_ne!(app.source_viewer.texture.as_ref().unwrap().id(), first_id);
    assert_eq!(app.result_viewer.texture.as_ref().unwrap().id(), result_id);
    assert_eq!(
        app.image_path.as_deref(),
        Some(Path::new("finished master.tiff"))
    );
}

#[test]
fn app_import_retires_previous_source_and_result_work_before_showing_new_capture() {
    for corrupt_old in [false, true] {
        let ctx = Context::default();
        let old = jobs::tests::TestDirectory::new("app-old-bracket");
        let new = jobs::tests::TestDirectory::new("app-new-bracket");
        let mut app = app();
        let old_stack = camera_stack(old.path(), 2, 17);
        let new_stack = camera_stack(new.path(), 3, 43);
        if corrupt_old {
            std::fs::write(&old_stack.frames[0].path, b"broken RAW container").unwrap();
        }
        app.stack = Some(old_stack);
        app.select(0);
        app.poll_images(&ctx);
        assert!(
            app.browser.active(),
            "fixture must have an old source task in flight"
        );
        let old_epoch = app.epoch;
        app.result_work = Some(ResultWork {
            epoch: old_epoch,
            task: image_task("previous result.tiff", [19, 33, 229, 255]),
        });
        app.import(new.path().to_path_buf());
        assert_ne!(app.epoch, old_epoch);
        assert!(app.source_viewer.texture.is_none());
        wait_for(&mut app, &ctx, |app| {
            app.scan.is_none() && app.browser.has_image(1)
        });
        assert_eq!(
            app.stack.as_ref().unwrap().frames.len(),
            new_stack.frames.len()
        );
        assert_eq!(app.browser.displayed_index(), Some(1));
        assert_eq!(app.source_viewer.source_size, [44, 24]);
        assert!(app.browser.error(0).is_none());
        assert!(app.browser.error(1).is_none());
        assert!(app.result_viewer.texture.is_none());
        assert!(app.image_path.is_none());
        assert!(app.error.is_none());
    }
}

#[test]
fn app_decode_error_keeps_the_previous_capture_visible_with_its_original_identity() {
    let ctx = Context::default();
    let directory = jobs::tests::TestDirectory::new("app-source-error-continuity");
    let mut app = app();
    let stack = camera_stack(directory.path(), 8, 32);
    std::fs::write(&stack.frames[7].path, b"broken camera JPEG container").unwrap();
    app.stack = Some(stack);
    app.select(0);
    wait_for(&mut app, &ctx, |app| {
        app.browser.displayed_index() == Some(0)
    });
    let displayed_id = app.source_viewer.texture.as_ref().unwrap().id();
    app.select(7);
    wait_for(&mut app, &ctx, |app| app.browser.error(7).is_some());
    assert_eq!(app.selected, 7);
    assert_eq!(app.browser.displayed_index(), Some(0));
    assert!(app.browser.pending());
    assert_eq!(
        app.source_viewer.texture.as_ref().unwrap().id(),
        displayed_id
    );
    assert_eq!(app.source_viewer.source_size, [32, 24]);
    assert!(
        app.error.is_none(),
        "a camera preview failure must not block RAW stacking"
    );
}

fn finished_draft(name: &str) -> DraftEvent {
    DraftEvent::Finished(Ok(draft_preview::DraftPreview {
        image: image(name, [222, 18, 43, 255]),
        source_frames: 8,
        aligned_frames: 8,
        skipped_frames: 0,
        alignment_edges: 18,
        cycle_rank: 11,
        reference_frame: 4,
        warnings: Vec::new(),
    }))
}

#[test]
fn app_draft_cancellation_retains_one_worker_and_rejects_its_late_result() {
    // The uncancelled arm is a positive control: the same real consumer must
    // accept the result when eligible, not silently discard all draft events.
    for cancelled in [false, true] {
        let ctx = Context::default();
        let directory = jobs::tests::TestDirectory::new("app-draft-retirement");
        let mut app = app();
        app.stack = Some(camera_stack(directory.path(), 2, 32));
        let existing = cache_image(&ctx, image("previous draft", [8, 183, 57, 255]));
        let previous_id = existing.texture.id();
        install_viewer(&mut app.draft_viewer, &existing);
        let (send, receive) = mpsc::sync_channel(8);
        app.draft_job = Some(DraftJob::test_receiver(receive));
        app.draft_epoch = app.epoch;
        if cancelled {
            app.draft_job.as_ref().unwrap().cancel();
            app.draft_cancelled = true;
        }
        // Repeated requests must keep the existing receiver attached until
        // terminal delivery, even after cancellation was requested.
        app.start_draft();
        app.start_draft();
        assert_eq!(app.draft_cancelled, cancelled);
        send.send(DraftEvent::Progress {
            stage: DraftStage::Aligning,
            completed: 3,
            total: 18,
        })
        .expect("a replacement draft detached the original worker");
        app.poll_images(&ctx);
        assert!(app.draft_job.is_some());
        assert_eq!(app.draft_progress.is_none(), cancelled);
        if !cancelled {
            assert_eq!(app.draft_progress, Some((DraftStage::Aligning, 3, 18)));
        }
        send.send(finished_draft("late camera draft")).unwrap();
        app.poll_images(&ctx);
        assert!(app.draft_job.is_none());
        assert!(app.draft_progress.is_none());
        assert_eq!(
            app.draft_viewer.texture.as_ref().unwrap().id() == previous_id,
            cancelled
        );
        assert_eq!(app.draft_info.is_none(), cancelled);
        assert!(app.error.is_none());
    }
}

#[test]
fn app_import_retires_a_draft_before_replacement_and_ignores_old_success() {
    let ctx = Context::default();
    let directory = jobs::tests::TestDirectory::new("app-import-draft-retirement");
    let mut app = app();
    let stack = camera_stack(directory.path(), 2, 32);
    let (send, receive) = mpsc::sync_channel(8);
    app.draft_job = Some(DraftJob::test_receiver(receive));
    app.draft_epoch = app.epoch;
    let old_epoch = app.epoch;
    app.import(directory.path().to_path_buf());
    assert_ne!(app.epoch, old_epoch);
    assert!(app.draft_cancelled);
    assert!(
        app.draft_job.is_some(),
        "import must retain the retiring worker"
    );
    app.scan = None;
    app.stack = Some(stack);
    app.start_draft();
    assert_eq!(
        app.draft_epoch, old_epoch,
        "new draft overlapped a retiring decoder"
    );
    send.send(finished_draft("wrong bracket composite"))
        .unwrap();
    app.poll_images(&ctx);
    assert!(app.draft_job.is_none());
    assert!(app.draft_viewer.texture.is_none());
    assert!(app.draft_info.is_none());
    assert!(app.error.is_none());

    // Once retirement completes the app may start a new worker. This bracket
    // intentionally has small JPEGs: the new worker must return a real error,
    // not remain permanently disabled by the previous cancellation state.
    app.start_draft();
    assert!(app.draft_job.is_some());
    assert!(!app.draft_cancelled);
    assert_eq!(app.draft_epoch, app.epoch);
    wait_for(&mut app, &ctx, |app| app.draft_job.is_none());
    assert!(
        app.error
            .as_deref()
            .is_some_and(|error| error.contains("too small"))
    );
}

#[test]
fn app_draft_disconnect_retires_work_and_only_reports_a_current_live_failure() {
    for (cancelled, stale) in [(false, false), (true, false), (false, true)] {
        let ctx = Context::default();
        let mut app = app();
        let (send, receive) = mpsc::sync_channel(1);
        app.draft_job = Some(DraftJob::test_receiver(receive));
        app.draft_progress = Some((DraftStage::Reading, 1, 8));
        app.draft_cancelled = cancelled;
        app.draft_epoch = app.epoch;
        if stale {
            app.epoch += 1;
        }
        drop(send);
        app.poll_images(&ctx);
        assert!(
            app.draft_job.is_none(),
            "disconnected worker remained permanently busy"
        );
        assert!(app.draft_progress.is_none());
        if !cancelled && !stale {
            assert!(
                app.error
                    .as_deref()
                    .is_some_and(|error| error.contains("worker ended"))
            );
        } else {
            assert!(
                app.error.is_none(),
                "obsolete/cancelled failure leaked into current bracket"
            );
        }
    }
}

#[test]
fn actual_filmstrip_keeps_visible_work_bounded_for_a_twenty_thousand_frame_bracket() {
    for size in [[1060.0, 720.0], [1440.0, 940.0]] {
        let ctx = Context::default();
        theme::install(&ctx);
        let mut app = app();
        app.stack = Some(stack(20_000));
        app.selected = 10_773;
        app.reveal_selected = true;
        for time in 0..4 {
            let input = RawInput {
                screen_rect: Some(Rect::from_min_size(
                    Pos2::ZERO,
                    egui::vec2(size[0], size[1]),
                )),
                time: Some(time as f64),
                ..Default::default()
            };
            let _ = ctx.run(input, |ctx| {
                app.inspector(ctx);
                app.filmstrip(ctx);
                app.canvas(ctx);
            });
            assert!(
                app.visible_sources.len() <= 24,
                "filmstrip requested {} items at {size:?}",
                app.visible_sources.len()
            );
        }
        assert!(
            !app.visible_sources.is_empty(),
            "the fixture must actually lay out sources"
        );
        assert!(
            app.visible_sources.contains(&app.selected),
            "reveal did not reach the selected middle frame"
        );
        assert!(
            app.visible_sources[0] > 0,
            "the fixture must exercise nonzero scroll offset"
        );
        assert!(app.visible_sources.iter().all(|&index| index < 20_000));
        assert!(
            !app.browser.active(),
            "layout itself must not open a RAW file"
        );
    }
}

#[test]
fn embedded_camera_orientation_preserves_actual_pixels_in_all_eight_directions() {
    // The author tested dimensions for orientation 6. This independent arm
    // compares pixel identities for every orientation against explicit inverse
    // coordinates, without using the producer's rotate/flip helpers.
    let directory = jobs::tests::TestDirectory::new("independent-camera-orientation");
    let source = image::RgbImage::from_fn(13, 9, |x, y| {
        image::Rgb([(x * 17 + y * 3) as u8, (y * 23) as u8, (x * 7) as u8])
    });
    let mut jpeg = Vec::new();
    image::codecs::jpeg::JpegEncoder::new_with_quality(&mut jpeg, 95)
        .encode_image(&source)
        .unwrap();
    let decoded = image::load_from_memory_with_format(&jpeg, image::ImageFormat::Jpeg)
        .unwrap()
        .into_rgba8();
    let path = directory.path().join("camera.arw");
    for orientation in 1_u16..=8 {
        let mut bytes = vec![0_u8; 128 + jpeg.len()];
        bytes[..8].copy_from_slice(b"II*\0\x08\0\0\0");
        bytes[8..10].copy_from_slice(&3_u16.to_le_bytes());
        for (entry_index, (tag, kind, value)) in [
            (513_u16, 4_u16, 128_u32),
            (514_u16, 4_u16, jpeg.len() as u32),
            (274_u16, 3_u16, u32::from(orientation)),
        ]
        .into_iter()
        .enumerate()
        {
            let offset = 10 + entry_index * 12;
            bytes[offset..offset + 2].copy_from_slice(&tag.to_le_bytes());
            bytes[offset + 2..offset + 4].copy_from_slice(&kind.to_le_bytes());
            bytes[offset + 4..offset + 8].copy_from_slice(&1_u32.to_le_bytes());
            bytes[offset + 8..offset + 12].copy_from_slice(&value.to_le_bytes());
        }
        bytes[128..].copy_from_slice(&jpeg);
        std::fs::write(&path, &bytes).unwrap();
        let preview = source_preview::load_source_preview(path.clone(), 100)
            .receiver
            .recv_timeout(Duration::from_secs(5))
            .unwrap()
            .unwrap();
        let (width, height) = if orientation >= 5 { (9, 13) } else { (13, 9) };
        assert_eq!(preview.size, [width as usize, height as usize]);
        for y in 0..height {
            for x in 0..width {
                let (source_x, source_y) = match orientation {
                    1 => (x, y),
                    2 => (12 - x, y),
                    3 => (12 - x, 8 - y),
                    4 => (x, 8 - y),
                    5 => (y, x),
                    6 => (y, 8 - x),
                    7 => (12 - y, 8 - x),
                    8 => (12 - y, x),
                    _ => unreachable!(),
                };
                let offset = ((y * width + x) * 4) as usize;
                assert_eq!(
                    &preview.rgba[offset..offset + 4],
                    &decoded.get_pixel(source_x, source_y).0,
                    "orientation {orientation}, pixel ({x}, {y})"
                );
            }
        }
        assert_eq!(std::fs::read(&path).unwrap(), bytes);
    }
}

#[test]
fn actual_processing_panel_keeps_its_instruments_inside_the_visible_minimum_workspace() {
    // This exercises the panel order the real app uses, with its sidebar,
    // filmstrip and viewport constraints. Individual instrument calls cannot
    // catch a header row consuming the processing panel's whole height.
    for size in [[1060.0, 720.0], [1440.0, 940.0]] {
        let ctx = Context::default();
        theme::install(&ctx);
        let mut app = app();
        app.stack = Some(stack(259));
        app.activity = true;
        app.dock_live = true;
        app.recorded = true;
        app.progress.ingest(
            "frames: 259 from recorded capture\n\
planes: 3516 x 2344 per CFA plane\n\
bands: 7 Laplacian levels + 1 base, coarsest 28 x 19\n\
per-band exp: 2 3 4 5 8 8 8 (coarsest -> finest)\n\
alignment: ON (solved), reference frame 129, 259 placed / 0 refused, 63.9 s\n\
coverage: field of view scaled to 0.9562 so that EVERY frame covers every pixel\n\
memory plan: 4 canonical chunks, 1 reusable frame worker, 1 retained + 1 scratch accumulator, 4 execution threads\n\
averaged: 4.8% 0.0% 0.0% 0.0% 0.0% 0.0% 0.0% 100.0%\n\
STREHL_UI_PROGRESS event=stage name=render total=259\n",
        );
        let draw = |app: &mut StrehlApp, time: f64| {
            ctx.run(
                RawInput {
                    screen_rect: Some(Rect::from_min_size(
                        Pos2::ZERO,
                        egui::vec2(size[0], size[1]),
                    )),
                    time: Some(time),
                    ..Default::default()
                },
                |ctx| {
                    egui::TopBottomPanel::bottom("status-v2")
                        .exact_height(25.0)
                        .show(ctx, |_| {});
                    app.inspector(ctx);
                    app.filmstrip(ctx);
                    app.canvas(ctx);
                },
            )
        };
        let _ = draw(&mut app, 0.0);
        let output = draw(&mut app, 0.1);
        for label in ["Make the photograph", "Read", "Blend"] {
            let (shape, clip) = output
                .shapes
                .iter()
                .find_map(|shape| match &shape.shape {
                    egui::Shape::Text(text) if text.galley.text() == label => {
                        Some((text, shape.clip_rect))
                    }
                    _ => None,
                })
                .unwrap_or_else(|| panic!("{label} was never painted at {size:?}"));
            assert!(
                clip.expand(1.0).contains_rect(shape.visual_bounding_rect()),
                "{label} is clipped at {size:?}: text {:?}, clip {clip:?}",
                shape.visual_bounding_rect(),
            );
            assert!(shape.pos.y > 40.0 && shape.pos.y < size[1] - 25.0);
        }
        // The negative control has the same capture and pipeline, but actually
        // collapses Signals. A permanently present offscreen chart must fail.
        app.dock_live = false;
        let collapsed = draw(&mut app, 0.2);
        assert!(!collapsed.shapes.iter().any(|shape| matches!(&shape.shape,
            egui::Shape::Text(text) if text.galley.text() == "Make the photograph"
        )));
    }
}

#[test]
fn actual_inspector_default_and_reset_only_change_the_clicked_override() {
    let ctx = Context::default();
    theme::install(&ctx);
    let mut app = app();
    app.dock_live = false;
    let draw = |app: &mut StrehlApp, time: f64, events| {
        ctx.run(
            RawInput {
                screen_rect: Some(Rect::from_min_size(Pos2::ZERO, egui::vec2(1060.0, 720.0))),
                time: Some(time),
                events,
                ..Default::default()
            },
            |ctx| {
                app.inspector(ctx);
                app.canvas(ctx);
            },
        )
    };
    let text_position = |output: &egui::FullOutput, label: &str, near_y: Option<f32>| {
        output
            .shapes
            .iter()
            .filter_map(|shape| match &shape.shape {
                egui::Shape::Text(text) if text.galley.text() == label => {
                    Some(text.visual_bounding_rect().center())
                }
                _ => None,
            })
            .min_by(|left, right| {
                let distance =
                    |position: &Pos2| near_y.map_or(position.y, |y| (position.y - y).abs());
                distance(left).total_cmp(&distance(right))
            })
            .unwrap_or_else(|| panic!("the inspector never painted {label}"))
    };
    let button = |position, pressed| egui::Event::PointerButton {
        pos: position,
        button: egui::PointerButton::Primary,
        pressed,
        modifiers: egui::Modifiers::NONE,
    };
    let _ = draw(&mut app, 0.0, vec![]);
    let initial = draw(&mut app, 0.1, vec![]);
    assert_eq!(
        app.controls.gate, None,
        "drawing cannot silently enable an override"
    );
    assert_eq!(app.controls.exposure, None);
    let row = text_position(&initial, "Noise gate", None);
    let default = text_position(&initial, "Default", Some(row.y));
    assert!(
        (default.y - row.y).abs() < 6.0,
        "the fixture must target the noise-gate row"
    );
    let _ = draw(
        &mut app,
        0.2,
        vec![egui::Event::PointerMoved(default), button(default, true)],
    );
    let _ = draw(&mut app, 0.3, vec![button(default, false)]);
    assert_eq!(
        app.controls.gate,
        Some(2.0),
        "the real Default button must open its numeric override"
    );
    assert_eq!(
        app.controls.exposure, None,
        "a neighboring override must remain automatic"
    );

    let enabled = draw(&mut app, 0.4, vec![]);
    let reset = text_position(&enabled, "Reset", Some(row.y));
    assert!(
        (reset.y - row.y).abs() < 6.0,
        "target the row Reset, not the global Reset"
    );
    let _ = draw(
        &mut app,
        0.5,
        vec![egui::Event::PointerMoved(reset), button(reset, true)],
    );
    let _ = draw(&mut app, 0.6, vec![button(reset, false)]);
    assert_eq!(app.controls.gate, None);
    assert_eq!(app.controls.exposure, None);

    // Different defensible settings from the initial/default arm: negative
    // exposure, a high noise gate, and upper-range scale parameters. Merely
    // opening the inspector must preserve all of them.
    app.controls.gate = Some(7.25);
    app.controls.exposure = Some(-2.25);
    app.controls.settings.pyramid_bands = Some(12);
    app.controls.settings.pyramid_exponent = Some(7.5);
    app.controls.settings.pyramid_sharpen = Some(1.9);
    let _ = draw(&mut app, 0.7, vec![]);
    let _ = draw(&mut app, 0.8, vec![]);
    assert_eq!(app.controls.gate, Some(7.25));
    assert_eq!(app.controls.exposure, Some(-2.25));
    assert_eq!(app.controls.settings.pyramid_bands, Some(12));
    assert_eq!(app.controls.settings.pyramid_exponent, Some(7.5));
    assert_eq!(app.controls.settings.pyramid_sharpen, Some(1.9));
}

fn canvas_photo_bounds(output: &egui::FullOutput, texture: egui::TextureId) -> Rect {
    canvas_photo_footprint(output, texture, true)
}
fn canvas_photo_footprint(
    output: &egui::FullOutput,
    texture: egui::TextureId,
    require_all_visible: bool,
) -> Rect {
    // Observe the actual image mesh handed to the painter. A helper that only
    // recomputes the intended photo_rect would miss a conditional layout row.
    let images: Vec<_> = output
        .shapes
        .iter()
        .filter_map(|shape| match &shape.shape {
            egui::Shape::Mesh(mesh) if mesh.texture_id == texture => Some((mesh, shape.clip_rect)),
            _ => None,
        })
        .collect();
    assert_eq!(
        images.len(),
        1,
        "The fixture must paint exactly one photograph"
    );
    let (image, clip) = images[0];
    assert_eq!(image.vertices.len(), 4);
    let bounds = Rect::from_points(&image.vertices.iter().map(|v| v.pos).collect::<Vec<_>>());
    let uv = Rect::from_points(&image.vertices.iter().map(|v| v.uv).collect::<Vec<_>>());
    assert_eq!(
        uv,
        Rect::from_min_max(Pos2::ZERO, egui::pos2(1.0, 1.0)),
        "A status transition must not conceal geometry changes by cropping the photo"
    );
    assert!(
        !require_all_visible || clip.expand(1.0).contains_rect(bounds),
        "The fit photograph must actually remain visible: image {bounds:?}, clip {clip:?}"
    );
    assert!(
        bounds.width() > 200.0 && bounds.height() > 100.0,
        "Empty or tiny images cannot commission this continuity criterion"
    );
    bounds
}

fn draw_canvas(app: &mut StrehlApp, ctx: &Context, size: [f32; 2], time: f64) -> egui::FullOutput {
    ctx.run(
        RawInput {
            screen_rect: Some(Rect::from_min_size(
                Pos2::ZERO,
                egui::vec2(size[0], size[1]),
            )),
            time: Some(time),
            ..Default::default()
        },
        |ctx| app.canvas(ctx),
    )
}

fn assert_same_photo_bounds(expected: Rect, actual: Rect, state: &str) {
    for (a, b) in [
        (expected.min.x, actual.min.x),
        (expected.min.y, actual.min.y),
        (expected.max.x, actual.max.x),
        (expected.max.y, actual.max.y),
    ] {
        assert!(
            (a - b).abs() <= 0.05,
            "The photograph moved/resized in {state}: expected {expected:?}, got {actual:?}"
        );
    }
}

#[test]
fn actual_canvas_photo_does_not_move_for_status_text_errors_or_draft_progress() {
    // Rejectable inputs: a long wrapped error, conditional draft progress,
    // thumbnail-to-full resolution, and filename expansion used to change the
    // image rectangle. A smaller real viewport is the negative control.
    for size in [[1060.0, 720.0], [1440.0, 940.0]] {
        let ctx = Context::default();
        theme::install(&ctx);
        let directory = jobs::tests::TestDirectory::new("app-canvas-geometry");
        let mut app = app();
        let scan = camera_stack_with_height(directory.path(), 2, 1440, 960);
        std::fs::write(&scan.frames[1].path, b"broken camera JPEG container").unwrap();
        app.stack = Some(scan);
        app.select(0);
        wait_for(&mut app, &ctx, |app| app.browser.refining());
        assert!(
            app.source_viewer.overview,
            "The first arm must exercise a reduced thumbnail, not a full JPEG twice"
        );
        assert!(
            matches!(
                app.source_viewer.texture.as_ref().unwrap().size(),
                [640, 427] | [960, 640]
            ),
            "the continuity arm must exercise the resident or overview tier below the full JPEG"
        );
        assert_eq!(app.source_viewer.source_size, [1440, 960]);
        let thumb = app.source_viewer.texture.as_ref().unwrap().id();
        let first = draw_canvas(&mut app, &ctx, size, 0.0);
        let expected = canvas_photo_bounds(&first, thumb);

        wait_for(&mut app, &ctx, |app| app.browser.has_image(0));
        let full = app.source_viewer.texture.as_ref().unwrap().id();
        assert_ne!(thumb, full, "Refinement must actually replace the texture");
        assert_eq!(
            app.source_viewer.texture.as_ref().unwrap().size(),
            [1440, 960]
        );
        assert!(
            app.source_viewer.transitioning(),
            "the fixture must exercise a real resolution reveal"
        );
        let _ = draw_canvas(&mut app, &ctx, size, 0.1);
        let ready = draw_canvas(&mut app, &ctx, size, 0.4);
        assert_same_photo_bounds(
            expected,
            canvas_photo_bounds(&ready, full),
            "full JPEG refinement",
        );

        let original_name = app.stack.as_ref().unwrap().frames[0].path.clone();
        app.stack.as_mut().unwrap().frames[0].path =
            PathBuf::from(format!("{}.ARW", "long_capture_description_".repeat(25)));
        let long_name = draw_canvas(&mut app, &ctx, size, 0.5);
        assert_same_photo_bounds(
            expected,
            canvas_photo_bounds(&long_name, full),
            "long filename",
        );
        app.stack.as_mut().unwrap().frames[0].path = original_name;

        app.select(1);
        assert!(app.browser.pending());
        let pending = draw_canvas(&mut app, &ctx, size, 0.6);
        assert_same_photo_bounds(
            expected,
            canvas_photo_bounds(&pending, full),
            "pending source",
        );
        wait_for(&mut app, &ctx, |app| app.browser.error(1).is_some());
        let source_error = draw_canvas(&mut app, &ctx, size, 0.7);
        assert_same_photo_bounds(
            expected,
            canvas_photo_bounds(&source_error, full),
            "source decoding error",
        );

        app.error = Some(
            "A deliberately long engine error which previously wrapped into several layout rows. "
                .repeat(18),
        );
        let error = draw_canvas(&mut app, &ctx, size, 0.8);
        assert_same_photo_bounds(
            expected,
            canvas_photo_bounds(&error, full),
            "long global error",
        );
        app.error = None;

        let shared = CachedImage {
            texture: app.source_viewer.texture.as_ref().unwrap().clone(),
            source_size: app.source_viewer.source_size,
            overview: app.source_viewer.overview,
        };
        install_viewer(&mut app.draft_viewer, &shared);
        app.view = View::Draft;
        for (i, progress) in [
            None,
            Some((DraftStage::Reading, 1, 259)),
            Some((DraftStage::Aligning, 1027, 1549)),
            Some((DraftStage::Blending, 193, 259)),
            None,
        ]
        .into_iter()
        .enumerate()
        {
            app.draft_progress = progress;
            app.draft_info = if i == 4 {
                Some("259 sources, middle reference, camera JPEG composition with deliberately verbose provenance. ".repeat(15))
            } else {
                None
            };
            let output = draw_canvas(&mut app, &ctx, size, 0.9 + i as f64 * 0.1);
            assert_same_photo_bounds(
                expected,
                canvas_photo_bounds(&output, full),
                &format!("draft progress/provenance arm {i}"),
            );
        }

        let resized = draw_canvas(&mut app, &ctx, [size[0], size[1] - 160.0], 1.5);
        let actual = canvas_photo_bounds(&resized, full);
        assert!(
            (expected.height() - actual.height()).abs() > 50.0,
            "The negative control must change real image geometry, not pass through an unused layout path"
        );
    }
}

#[test]
fn actual_canvas_keeps_user_zoom_extent_when_camera_thumbnail_refines() {
    // Fit-mode alone cannot catch incorrect compensation of an inspected small
    // preview when a larger texture arrives. The same consumer must preserve
    // this user-selected extent, and still respond to a genuine zoom change.
    let ctx = Context::default();
    theme::install(&ctx);
    let directory = jobs::tests::TestDirectory::new("app-canvas-refinement-zoom");
    let mut app = app();
    app.stack = Some(camera_stack_with_height(directory.path(), 1, 1440, 960));
    app.select(0);
    wait_for(&mut app, &ctx, |app| app.browser.refining());
    app.source_viewer.fit = false;
    app.source_viewer.zoom = 1.4;
    let thumbnail = app.source_viewer.texture.as_ref().unwrap().id();
    assert!(
        matches!(
            app.source_viewer.texture.as_ref().unwrap().size(),
            [640, 427] | [960, 640]
        ),
        "Canvas must start with an actual resident/overview tier, not the native contact"
    );
    assert_eq!(app.source_viewer.source_size, [1440, 960]);
    let size = [1060.0, 720.0];
    let first = draw_canvas(&mut app, &ctx, size, 0.0);
    let expected = canvas_photo_footprint(&first, thumbnail, false);
    wait_for(&mut app, &ctx, |app| app.browser.has_image(0));
    let full = app.source_viewer.texture.as_ref().unwrap().id();
    assert_ne!(thumbnail, full);
    assert_eq!(
        app.source_viewer.texture.as_ref().unwrap().size(),
        [1440, 960]
    );
    assert!(
        app.source_viewer.transitioning(),
        "Fixture must exercise the real app resolution reveal"
    );
    assert!(
        !app.source_viewer.fit,
        "Refinement must not discard the user's inspection mode"
    );
    let _ = draw_canvas(&mut app, &ctx, size, 0.1);
    let refined = draw_canvas(&mut app, &ctx, size, 0.4);
    assert_same_photo_bounds(
        expected,
        canvas_photo_footprint(&refined, full, false),
        "user zoom during source refinement",
    );
    app.source_viewer.zoom *= 1.5;
    let enlarged = draw_canvas(&mut app, &ctx, size, 0.5);
    assert!(
        (canvas_photo_footprint(&enlarged, full, false).width() - expected.width()).abs() > 50.0,
        "The negative control must prove that actual zoom changes still alter the photo"
    );
}

#[test]
fn following_is_default_and_browsing_does_not_switch_it_off() {
    let mut app = app();
    assert!(app.follow_processing);
    app.stack = Some(stack(20));
    app.select(3);
    assert!(app.follow_processing);
    app.progress.processing_frame = Some(12);
    app.follow_current_frame();
    assert_eq!(app.selected, 12);
    app.view = View::Result;
    app.progress.processing_frame = Some(13);
    app.follow_current_frame();
    assert_eq!(app.selected, 13);
    assert!(
        app.view == View::Result,
        "Following updates Sources without stealing an explicitly opened result"
    );
    app.follow_processing = false;
    app.progress.processing_frame = Some(15);
    app.follow_current_frame();
    assert_eq!(
        app.selected, 13,
        "Explicit pause must actually pause following"
    );
    app.follow_processing = true;
    app.follow_current_frame();
    assert_eq!(app.selected, 15);
}

fn workbench_scene(
    app: &mut StrehlApp,
    ctx: &Context,
    time: f64,
    events: Vec<egui::Event>,
) -> egui::FullOutput {
    workbench_scene_sized(app, ctx, [1440.0, 940.0], time, events)
}

fn workbench_scene_sized(
    app: &mut StrehlApp,
    ctx: &Context,
    size: [f32; 2],
    time: f64,
    events: Vec<egui::Event>,
) -> egui::FullOutput {
    ctx.run(
        RawInput {
            screen_rect: Some(Rect::from_min_size(
                Pos2::ZERO,
                egui::vec2(size[0], size[1]),
            )),
            time: Some(time),
            events,
            ..Default::default()
        },
        |ctx| {
            egui::TopBottomPanel::bottom("status-v2")
                .exact_height(25.0)
                .show(ctx, |_| {});
            app.inspector(ctx);
            app.filmstrip(ctx);
            app.stack_ribbon(ctx);
            app.canvas(ctx);
        },
    )
}

#[test]
fn recorded_alignment_graph_and_capture_axis_fit_the_actual_minimum_dock() {
    let ctx = Context::default();
    theme::install(&ctx);
    let mut app = app();
    app.stack = Some(stack(259));
    app.activity = true;
    app.recorded = true;
    app.dock_live = true;
    app.progress.ingest(
        "STREHL_UI_PROGRESS event=stage name=alignment total=259\n\
STREHL_UI_PROGRESS event=align-phase name=pairs frames=259 total=170\n\
STREHL_UI_PROGRESS event=align-pair i=0 j=258 completed=14 accepted=11 frames=259 total=170\n\
STREHL_UI_PROGRESS event=align-pair-start i=2 j=180 started=15 frames=259 total=170\n",
    );
    let _ = workbench_scene_sized(&mut app, &ctx, [1060.0, 720.0], 0.0, vec![]);
    let output = workbench_scene_sized(&mut app, &ctx, [1060.0, 720.0], 0.1, vec![]);
    for label in [
        "RECORDED SESSION",
        "Comparing 003 ↔ 181",
        "Connections / 1",
        "Capture order",
        "259",
    ] {
        let shape = output.shapes.iter().find(|shape| {
            matches!(&shape.shape, egui::Shape::Text(text) if text.galley.text() == label)
        }).unwrap_or_else(|| panic!("the actual minimum dock did not paint {label}"));
        assert!(
            shape
                .clip_rect
                .expand(1.0)
                .contains_rect(shape.shape.visual_bounding_rect()),
            "{label} must be fully visible before scrolling: {:?} versus {:?}",
            shape.shape.visual_bounding_rect(),
            shape.clip_rect,
        );
    }
    let curves: Vec<_> = output
        .shapes
        .iter()
        .filter(|shape| matches!(&shape.shape, egui::Shape::Path(path) if path.points.len() == 21))
        .collect();
    assert!(
        curves.len() >= 2,
        "the fixture must draw both observed and active routes"
    );
    assert!(
        curves.iter().all(|shape| shape
            .clip_rect
            .expand(1.0)
            .contains_rect(shape.shape.visual_bounding_rect())),
        "the longest real connection and active route must fit above the visible axis"
    );
}

fn workbench_button(pos: Pos2, pressed: bool) -> egui::Event {
    egui::Event::PointerButton {
        pos,
        button: egui::PointerButton::Primary,
        pressed,
        modifiers: egui::Modifiers::NONE,
    }
}

fn workbench_click(
    app: &mut StrehlApp,
    ctx: &Context,
    time: &mut f64,
    pos: Pos2,
) -> egui::FullOutput {
    *time += 0.1;
    let _ = workbench_scene(
        app,
        ctx,
        *time,
        vec![egui::Event::PointerMoved(pos), workbench_button(pos, true)],
    );
    *time += 0.1;
    workbench_scene(app, ctx, *time, vec![workbench_button(pos, false)])
}

fn canvas_control(output: &egui::FullOutput, label: &str) -> Pos2 {
    output
        .shapes
        .iter()
        .find_map(|shape| match &shape.shape {
            egui::Shape::Text(text) if text.galley.text() == label && text.pos.x < 1116.0 => {
                Some(text.visual_bounding_rect().center())
            }
            _ => None,
        })
        .unwrap_or_else(|| panic!("the actual canvas toolbar never painted {label}"))
}

#[test]
fn workbench_phase_defaults_run_once_and_manual_views_survive_same_stage_events() {
    let ctx = Context::default();
    theme::install(&ctx);
    let mut app = app();
    app.stack = Some(stack(20));
    app.activity = true;
    let result = cache_image(&ctx, image("previous.tiff", [18, 35, 231, 255]));
    install_viewer(&mut app.result_viewer, &result);
    app.image_path = Some(PathBuf::from("previous.tiff"));
    assert!(app.follow_processing);
    app.view = View::Result;
    app.progress
        .ingest("STREHL_UI_PROGRESS event=stage name=alignment total=20\n");
    app.sync_workbench_phase();
    assert_eq!(app.canvas_mode, None);
    assert!(
        app.view == View::Result,
        "a stage change must preserve an explicitly chosen result while the live portal keeps updating"
    );
    let mut time = 0.0;
    let output = workbench_scene(&mut app, &ctx, time, vec![]);
    let live = canvas_control(&output, "Live view");
    let _ = workbench_click(&mut app, &ctx, &mut time, live);
    assert!(app.view == View::Sources);
    assert_eq!(
        app.canvas_mode, None,
        "a banner naming alignment does not yet name an actual compared pair"
    );
    assert!(
        app.live_active(),
        "the explicit live action must restore the current phase's actual view"
    );
    app.progress.ingest(
        "STREHL_UI_PROGRESS event=align-phase name=pairs frames=20 total=10\n\
STREHL_UI_PROGRESS event=align-pair-start i=2 j=18 started=1 frames=20 total=10\n",
    );
    app.sync_workbench_phase();
    assert_eq!(
        app.canvas_mode,
        Some(WorkbenchMode::Compare),
        "the first real pair changes live context within the existing alignment stage"
    );
    time += 0.1;
    let output = workbench_scene(&mut app, &ctx, time, vec![]);
    let sources = canvas_control(&output, "Sources");
    let output = workbench_click(&mut app, &ctx, &mut time, sources);
    assert_eq!(app.canvas_mode, None);
    app.sync_workbench_phase();
    assert_eq!(
        app.canvas_mode, None,
        "a manual source view must not be overridden every update"
    );
    assert!(
        app.follow_processing,
        "choosing a view must not pause source following"
    );
    let probe = canvas_control(&output, "Detail");
    let output = workbench_click(&mut app, &ctx, &mut time, probe);
    assert_eq!(app.canvas_mode, Some(WorkbenchMode::Probe));
    assert_eq!(
        app.workbench.pin(),
        Some(egui::pos2(0.5, 0.5)),
        "initial Detail needs a real inspection point"
    );
    let result = canvas_control(&output, "Result");
    let _ = workbench_click(&mut app, &ctx, &mut time, result);
    app.sync_workbench_phase();
    app.progress.processing_frame = Some(14);
    app.follow_current_frame();
    assert!(
        app.view == View::Result,
        "same-stage follow must preserve an explicitly chosen finished image"
    );
    assert_eq!(app.selected, 14);
    app.progress
        .ingest("STREHL_UI_PROGRESS event=stage name=merge total=20\n");
    app.sync_workbench_phase();
    assert_eq!(app.canvas_mode, Some(WorkbenchMode::Probe));
    assert!(
        app.view == View::Result,
        "even a new processing phase must preserve an explicitly chosen result"
    );
    time += 0.1;
    let output = workbench_scene(&mut app, &ctx, time, vec![]);
    let live = canvas_control(&output, "Live view");
    let output = workbench_click(&mut app, &ctx, &mut time, live);
    assert!(app.view == View::Sources);
    assert_eq!(
        app.canvas_mode, None,
        "live merging shows the current source, without forcing magnified detail"
    );
    let compare = canvas_control(&output, "Frame difference");
    let _ = workbench_click(&mut app, &ctx, &mut time, compare);
    assert_eq!(app.canvas_mode, Some(WorkbenchMode::Compare));
    app.progress
        .ingest("STREHL_UI_PROGRESS event=frame-started index=8 total=20\n");
    app.follow_current_frame();
    app.sync_workbench_phase();
    assert_eq!(
        app.canvas_mode,
        Some(WorkbenchMode::Compare),
        "manual frame difference persists through subsequent merge observations"
    );
    assert_eq!(app.selected, 8);
    assert!(app.follow_processing);
}

#[test]
fn reading_does_not_invent_a_compared_pair_and_first_actual_pair_respects_manual_detail() {
    for manual_detail in [false, true] {
        let ctx = Context::default();
        theme::install(&ctx);
        let mut app = app();
        app.stack = Some(stack(10));
        app.activity = true;
        app.progress.ingest(
            "STREHL_UI_PROGRESS event=align-phase name=planes frames=10 total=10\n\
STREHL_UI_PROGRESS event=align-plane index=5 completed=6 frames=10 total=10\n",
        );
        app.sync_workbench_phase();
        app.follow_current_frame();
        assert_eq!(app.progress.stage, Stage::Alignment);
        assert_eq!(app.live_mode(), None);
        assert_eq!(
            app.canvas_mode, None,
            "read progress only identifies an input frame, not a compared pair"
        );
        let mut time = 0.0;
        let output = workbench_scene(&mut app, &ctx, time, vec![]);
        assert!(
            !output.shapes.iter().any(|shape| matches!(&shape.shape,
            egui::Shape::Text(text) if text.galley.text().starts_with("PAIR TARGET"))),
            "reading input must not display manufactured neighbor endpoints as the current comparison"
        );
        if manual_detail {
            let detail = canvas_control(&output, "Detail");
            let _ = workbench_click(&mut app, &ctx, &mut time, detail);
            assert_eq!(
                app.canvas_mode,
                Some(WorkbenchMode::Probe),
                "fixture must actually choose Detail through the toolbar"
            );
        }
        app.progress.ingest(
            "STREHL_UI_PROGRESS event=align-phase name=pyramids frames=10 total=10\n\
STREHL_UI_PROGRESS event=align-phase name=pairs frames=10 total=3\n\
STREHL_UI_PROGRESS event=align-pair-start i=1 j=9 started=1 frames=10 total=3\n",
        );
        app.sync_workbench_phase();
        app.follow_current_frame();
        assert_eq!(
            app.progress.stage,
            Stage::Alignment,
            "the positive arm stays inside the same long-running stage"
        );
        assert_eq!(app.progress.alignment_current_pair, Some([1, 9]));
        assert_eq!(app.live_mode(), Some(WorkbenchMode::Compare));
        assert_eq!(
            app.canvas_mode,
            Some(if manual_detail {
                WorkbenchMode::Probe
            } else {
                WorkbenchMode::Compare
            }),
            "an actual pair enables automatic frame difference only when the user was following the previous live context"
        );
        assert_eq!(
            app.selected, 9,
            "manual Detail keeps following actual source work without losing its chosen tool"
        );
    }
}

#[test]
fn persistent_live_action_restores_draft_result_and_held_pair_without_another_engine_event() {
    let ctx = Context::default();
    theme::install(&ctx);
    let directory = jobs::tests::TestDirectory::new("same-frame-return-to-live");
    let mut app = app();
    app.stack = Some(camera_stack_with_height(directory.path(), 8, 1000, 600));
    app.activity = true;
    app.progress.ingest(
        "STREHL_UI_PROGRESS event=align-phase name=pairs frames=8 total=10\n\
STREHL_UI_PROGRESS event=align-pair-start i=2 j=6 started=1 frames=8 total=10\n",
    );
    app.sync_workbench_phase();
    app.follow_current_frame();
    wait_for(&mut app, &ctx, |app| {
        app.source_photo(2).is_some() && app.source_photo(6).is_some()
    });
    let draft = cache_image(&ctx, image("draft-red.jpg", [231, 18, 35, 255]));
    let result = cache_image(&ctx, image("result-blue.tiff", [18, 35, 231, 255]));
    install_viewer(&mut app.draft_viewer, &draft);
    install_viewer(&mut app.result_viewer, &result);
    app.image_path = Some(PathBuf::from("result-blue.tiff"));
    let mut time = 0.0;
    for state in ["draft", "result", "held"] {
        match state {
            "draft" => app.view = View::Draft,
            "result" => app.view = View::Result,
            _ => app.hold_pair([0, 3]),
        }
        app.source_viewer.reset(false);
        assert_eq!(
            app.selected, 6,
            "the regression arm must already be at the processing identity"
        );
        let previous_frame = app.progress.processing_frame;
        let previous_stage = app.last_stage;
        time += 0.1;
        let output = workbench_scene(&mut app, &ctx, time, vec![]);
        let live = canvas_control(&output, "Live view");
        let _ = workbench_click(&mut app, &ctx, &mut time, live);
        assert!(
            app.view == View::Sources,
            "{state}: Live view must choose the live canvas even when select() has no new frame to select"
        );
        assert!(app.follow_processing && app.held_pair.is_none() && app.dock_live);
        assert!(app.source_viewer.fit);
        assert_eq!(app.canvas_mode, Some(WorkbenchMode::Compare));
        assert_eq!(app.current_pair(), [2, 6]);
        assert_eq!(
            app.progress.processing_frame, previous_frame,
            "the click cannot invent an engine update"
        );
        assert_eq!(
            app.last_stage, previous_stage,
            "the click cannot manufacture a stage transition"
        );
        assert!(app.live_active());
    }
}

#[test]
fn paused_other_view_portal_uses_actual_processing_thumbnail_and_its_original_crop() {
    let ctx = Context::default();
    let directory = jobs::tests::TestDirectory::new("actual-live-portal");
    let mut app = app();
    app.stack = Some(camera_stack(directory.path(), 8, 32));
    app.activity = true;
    app.select(1);
    app.follow_processing = false;
    app.progress.ingest(
        "STREHL_UI_PROGRESS event=stage name=merge total=8\n\
STREHL_UI_PROGRESS event=frame-started index=5 total=8\n",
    );
    let draft = cache_image(&ctx, image("unrelated-draft.jpg", [231, 18, 35, 255]));
    let result = cache_image(&ctx, image("unrelated-output.tiff", [18, 35, 231, 255]));
    install_viewer(&mut app.draft_viewer, &draft);
    install_viewer(&mut app.result_viewer, &result);
    app.view = View::Draft;
    wait_for(&mut app, &ctx, |app| {
        app.live_input
            .as_ref()
            .is_some_and(|(index, _)| *index == 5)
    });
    assert_eq!(
        app.selected, 1,
        "the actual processing-preview worker must not disturb paused inspection"
    );
    let actual = app.live_input.as_ref().unwrap().1.clone();
    let expected_source = app
        .browser
        .thumbnail(5)
        .expect("actual processing source must be decoded")
        .id();
    assert_eq!(actual.id(), expected_source);
    assert_ne!(actual.id(), draft.texture.id());
    assert_ne!(actual.id(), result.texture.id());
    let draw = |app: &mut StrehlApp, time, events| {
        ctx.run(
            RawInput {
                screen_rect: Some(Rect::from_min_size(Pos2::ZERO, egui::vec2(640.0, 420.0))),
                time: Some(time),
                events,
                ..Default::default()
            },
            |ctx| {
                egui::CentralPanel::default()
                    .frame(egui::Frame::NONE)
                    .show(ctx, |ui| {
                        app.live_portal(
                            ui,
                            Rect::from_min_max(egui::pos2(20.0, 30.0), egui::pos2(620.0, 390.0)),
                        );
                    });
            },
        )
    };
    for (step, view) in [View::Draft, View::Result].into_iter().enumerate() {
        app.view = view;
        let output = draw(&mut app, step as f64, vec![]);
        let meshes: Vec<_> = output
            .shapes
            .iter()
            .filter_map(|shape| match &shape.shape {
                egui::Shape::Mesh(mesh) => Some((mesh, shape.clip_rect)),
                _ => None,
            })
            .collect();
        assert_eq!(
            meshes.len(),
            1,
            "the portal paints one actual camera preview, not a composite or old result"
        );
        let (mesh, clip) = meshes[0];
        assert_eq!(mesh.texture_id, actual.id());
        let bounds = Rect::from_points(
            &mesh
                .vertices
                .iter()
                .map(|vertex| vertex.pos)
                .collect::<Vec<_>>(),
        );
        let uv = Rect::from_points(
            &mesh
                .vertices
                .iter()
                .map(|vertex| vertex.uv)
                .collect::<Vec<_>>(),
        );
        assert_eq!(uv, Rect::from_min_max(Pos2::ZERO, egui::pos2(1.0, 1.0)));
        let native_aspect = actual.size()[0] as f32 / actual.size()[1] as f32;
        assert!(
            (bounds.width() / bounds.height() - native_aspect).abs() < 1e-4,
            "camera thumbnail pixels retain their native crop and uniform scaling"
        );
        assert!(clip.contains_rect(bounds));
        assert!(output.shapes.iter().any(|shape| matches!(&shape.shape,
            egui::Shape::Text(text) if text.galley.text() == "LIVE INPUT / 006")));
    }
    // Keep the same processing event but replace the displayed inspection with
    // Result. Clicking the actual portal must restore live source following.
    app.view = View::Result;
    let output = draw(&mut app, 3.0, vec![]);
    let at = output
        .shapes
        .iter()
        .find_map(|shape| match &shape.shape {
            egui::Shape::Mesh(mesh) if mesh.texture_id == actual.id() => Some(
                Rect::from_points(
                    &mesh
                        .vertices
                        .iter()
                        .map(|vertex| vertex.pos)
                        .collect::<Vec<_>>(),
                )
                .center(),
            ),
            _ => None,
        })
        .unwrap();
    let _ = draw(
        &mut app,
        3.1,
        vec![egui::Event::PointerMoved(at), workbench_button(at, true)],
    );
    let _ = draw(&mut app, 3.2, vec![workbench_button(at, false)]);
    assert!(app.view == View::Sources && app.follow_processing);
    assert_eq!(app.selected, 5);
    assert_eq!(
        app.canvas_mode, None,
        "merge live view shows the current source without forcing Detail"
    );
}

#[test]
fn filmstrip_inspection_leaves_held_difference_and_waits_for_a_new_actual_capture_to_follow() {
    let ctx = Context::default();
    theme::install(&ctx);
    let directory = jobs::tests::TestDirectory::new("filmstrip-live-follow-gesture");
    let mut app = app();
    // This fixture renders the legacy Sources workbench directly. A hidden
    // Process inspection must not become its foreground browser request.
    app.process_view = false;
    app.stack = Some(camera_stack_with_height(directory.path(), 8, 1000, 600));
    app.activity = true;
    app.progress.ingest(
        "STREHL_UI_PROGRESS event=align-phase name=pairs frames=8 total=10\n\
STREHL_UI_PROGRESS event=align-pair-start i=2 j=6 started=1 frames=8 total=10\n",
    );
    app.sync_workbench_phase();
    app.follow_current_frame();
    wait_for(&mut app, &ctx, |app| {
        app.source_photo(2).is_some() && app.source_photo(6).is_some()
    });
    assert_eq!(app.selected, 6);
    app.hold_pair([0, 3]);
    wait_for(&mut app, &ctx, |app| {
        app.source_photo(0).is_some()
            && app.source_photo(3).is_some()
            && app.browser.has_thumbnail(2)
            && app.browser.has_thumbnail(1)
    });
    let tile = |app: &StrehlApp, output: &egui::FullOutput, index| {
        let texture = app
            .browser
            .thumbnail(index)
            .expect("the chosen source tile must have real pixels")
            .id();
        output
            .shapes
            .iter()
            .filter_map(|shape| match &shape.shape {
                egui::Shape::Mesh(mesh) if mesh.texture_id == texture => {
                    let bounds = Rect::from_points(
                        &mesh
                            .vertices
                            .iter()
                            .map(|vertex| vertex.pos)
                            .collect::<Vec<_>>(),
                    );
                    ((bounds.width() - 78.0).abs() < 0.1 && (bounds.height() - 38.0).abs() < 0.1)
                        .then_some(bounds.center())
                }
                _ => None,
            })
            .max_by(|a, b| a.y.total_cmp(&b.y))
            .expect("the real filmstrip must paint a clickable78x38 photo for this exact source")
    };
    let mut time = 0.0;
    let output = workbench_scene(&mut app, &ctx, time, vec![]);
    let at = tile(&app, &output, 2);
    let _ = workbench_click(&mut app, &ctx, &mut time, at);
    assert_eq!(app.selected, 2);
    assert!(app.view == View::Sources && app.held_pair.is_none());
    assert_eq!(
        app.canvas_mode, None,
        "a filmstrip click must visibly leave held frame difference"
    );
    assert!(
        app.follow_processing,
        "manual inspection must not silently pause following"
    );
    for _ in 0..4 {
        app.follow_current_frame();
    }
    assert_eq!(
        app.selected, 2,
        "polling the unchanged engine observation cannot undo the user's click"
    );
    wait_for(&mut app, &ctx, |app| {
        app.browser.displayed_index() == Some(2)
    });
    assert_eq!(
        app.selected, 2,
        "the old processing identity must not win while the selected JPEG is loading"
    );
    time += 0.1;
    let output = workbench_scene(&mut app, &ctx, time, vec![]);
    let selected_texture = app.source_viewer.texture.as_ref().unwrap().id();
    assert!(output.shapes.iter().any(|shape| matches!(&shape.shape,
        egui::Shape::Mesh(mesh) if mesh.texture_id == selected_texture
            && mesh.vertices.iter().all(|vertex| vertex.color.a() > 0)
            && Rect::from_points(&mesh.vertices.iter().map(|vertex| vertex.pos).collect::<Vec<_>>()).width() > 300.0)),
        "the selected source must actually replace the main photograph, not only update its ordinal");

    app.progress
        .ingest("STREHL_UI_PROGRESS event=align-pair-start i=3 j=7 started=2 frames=8 total=10\n");
    app.follow_current_frame();
    assert_eq!(
        app.selected, 7,
        "a genuinely different processing capture resumes normal following"
    );
    wait_for(&mut app, &ctx, |app| {
        app.browser.displayed_index() == Some(7)
    });
    time += 0.1;
    let output = workbench_scene(&mut app, &ctx, time, vec![]);
    let detail = canvas_control(&output, "Detail");
    let output = workbench_click(&mut app, &ctx, &mut time, detail);
    assert_eq!(app.canvas_mode, Some(WorkbenchMode::Probe));
    let at = tile(&app, &output, 1);
    let _ = workbench_click(&mut app, &ctx, &mut time, at);
    assert_eq!(app.selected, 1);
    assert_eq!(
        app.canvas_mode,
        Some(WorkbenchMode::Probe),
        "manual source scrubbing preserves a chosen Detail tool"
    );
    app.follow_current_frame();
    assert_eq!(app.selected, 1);
    let unchanged_event = app.progress.processing_frame;
    let unchanged_key = app.followed_frame;
    time += 0.1;
    let output = workbench_scene(&mut app, &ctx, time, vec![]);
    let live = canvas_control(&output, "Live view");
    let _ = workbench_click(&mut app, &ctx, &mut time, live);
    assert_eq!(
        app.selected, 7,
        "explicit Live returns immediately even though this observation was already followed"
    );
    assert_eq!(app.progress.processing_frame, unchanged_event);
    assert_eq!(
        app.followed_frame, unchanged_key,
        "returning live must consume the same real observation, not manufacture another one"
    );
    assert_eq!(app.canvas_mode, Some(WorkbenchMode::Compare));
    assert!(app.follow_processing && app.held_pair.is_none() && app.live_active());
}

#[test]
fn sparse_alignment_read_and_scale_observations_reject_prefix_and_regressed_identity_paint() {
    let ctx = Context::default();
    theme::install(&ctx);
    let mut app = app();
    app.stack = Some(stack(10));
    app.activity = true;
    app.progress.ingest(
        "STREHL_UI_PROGRESS event=align-phase name=planes frames=10 total=10\n\
STREHL_UI_PROGRESS event=align-plane index=6 completed=6 frames=10 total=10\n\
STREHL_UI_PROGRESS event=align-plane index=9 completed=9 frames=10 total=10\n\
STREHL_UI_PROGRESS event=align-plane index=2 completed=8 frames=10 total=10\n\
STREHL_UI_PROGRESS event=align-plane index=10 completed=10 frames=10 total=10\n",
    );
    assert_eq!(app.progress.alignment_planes, Some((9, 10)));
    assert_eq!(
        app.progress
            .alignment_plane_observations
            .iter()
            .copied()
            .collect::<Vec<_>>(),
        vec![6, 9]
    );
    let draw = |app: &mut StrehlApp, time| {
        ctx.run(
            RawInput {
                screen_rect: Some(Rect::from_min_size(Pos2::ZERO, egui::vec2(1000.0, 200.0))),
                time: Some(time),
                ..Default::default()
            },
            |ctx| app.stack_ribbon(ctx),
        )
    };
    let raw = draw(&mut app, 0.0);
    let ticks = |output: &egui::FullOutput| {
        output
            .shapes
            .iter()
            .filter_map(|shape| match &shape.shape {
                egui::Shape::LineSegment { points, stroke }
                    if stroke.color == GREEN
                        && (points[0].x - points[1].x).abs() < 1e-4
                        && ((points[1].y - points[0].y).abs() - 6.0).abs() < 1e-4 =>
                {
                    Some(points[0].x)
                }
                _ => None,
            })
            .collect::<Vec<_>>()
    };
    let raw_ticks = ticks(&raw);
    assert_eq!(
        raw_ticks.len(),
        2,
        "nine cumulative reads with two emitted identities must paint exactly two known RAW ticks"
    );
    assert!(
        raw_ticks[0] > 600.0 && raw_ticks[1] > 900.0,
        "known identities6/9 land in the later capture cells, not a fabricated completed prefix"
    );
    app.progress.ingest(
        "STREHL_UI_PROGRESS event=align-phase name=pyramids frames=10 total=10\n\
STREHL_UI_PROGRESS event=align-pyramid index=1 completed=6 frames=10 total=10\n\
STREHL_UI_PROGRESS event=align-pyramid index=8 completed=9 frames=10 total=10\n\
STREHL_UI_PROGRESS event=align-pyramid index=4 completed=7 frames=10 total=10\n\
STREHL_UI_PROGRESS event=align-plane index=3 completed=10 frames=10 total=10\n",
    );
    assert_eq!(app.progress.alignment_pyramids, Some((9, 10)));
    assert_eq!(
        app.progress
            .alignment_pyramid_observations
            .iter()
            .copied()
            .collect::<Vec<_>>(),
        vec![1, 8]
    );
    assert_eq!(
        app.progress
            .alignment_plane_observations
            .iter()
            .copied()
            .collect::<Vec<_>>(),
        vec![6, 9],
        "a late read event cannot add an identity after the read phase has ended"
    );
    let scaled = draw(&mut app, 0.1);
    let scaled_ticks = ticks(&scaled);
    assert_eq!(
        scaled_ticks.len(),
        4,
        "two actual read identities and two actual scale identities remain visible"
    );
    assert!(scaled_ticks.iter().any(|x| *x < 200.0) && scaled_ticks.iter().any(|x| *x > 800.0));
}

#[test]
fn graph_hold_wipe_and_actual_live_button_keep_inspection_separate_from_following() {
    let ctx = Context::default();
    theme::install(&ctx);
    let directory = jobs::tests::TestDirectory::new("app-held-pair-workbench");
    let mut app = app();
    // Near-identical aspect ratios keep Compare valid while each generated
    // frame has distinct dimensions, pixels, source identity and texture.
    app.stack = Some(camera_stack_with_height(directory.path(), 8, 1000, 600));
    app.activity = true;
    app.progress.ingest(
        "STREHL_UI_PROGRESS event=stage name=alignment total=8\n\
STREHL_UI_PROGRESS event=align-phase name=pairs frames=8 total=10\n\
STREHL_UI_PROGRESS event=align-pair i=0 j=3 completed=1 accepted=1 frames=8 total=10\n\
STREHL_UI_PROGRESS event=align-pair-start i=2 j=6 started=2 frames=8 total=10\n",
    );
    app.sync_workbench_phase();
    app.follow_current_frame();
    wait_for(&mut app, &ctx, |app| {
        app.source_photo(2).is_some() && app.source_photo(6).is_some()
    });
    let mut time = 0.0;
    let output = workbench_scene(&mut app, &ctx, time, vec![]);
    let edge = output
        .shapes
        .iter()
        .find_map(|shape| match &shape.shape {
            egui::Shape::Path(path) if path.points.len() == 21 => {
                Some((path.points[10], shape.clip_rect))
            }
            _ => None,
        })
        .expect("the real dock must paint an observed comparison edge");
    assert!(
        edge.1.contains(edge.0),
        "the chosen graph curve must actually be visible and clickable"
    );
    let _ = workbench_click(&mut app, &ctx, &mut time, edge.0);
    assert_eq!(
        app.held_pair,
        Some([0, 3]),
        "the dock action must reach the actual app held-pair state"
    );
    assert_eq!(app.canvas_mode, Some(WorkbenchMode::Compare));
    assert!(
        app.follow_processing,
        "holding an inspection pair must not disable background source following"
    );
    wait_for(&mut app, &ctx, |app| {
        [0, 3].into_iter().all(|index| {
            app.source_photo(index)
                .is_some_and(|photo| photo.texture.size().into_iter().max().unwrap() >= 960)
        })
    });
    for index in [0, 3] {
        let photo = app
            .source_photo(index)
            .expect("both held endpoints must be real decoded previews");
        assert!(
            photo.texture.size().into_iter().max().unwrap() >= 960,
            "the pinned-pair fixture must use useful overview pixels, not tiny filmstrip thumbnails"
        );
        assert_eq!(photo.index, index);
    }
    time += 0.1;
    let output = workbench_scene(&mut app, &ctx, time, vec![]);
    let b = app
        .source_photo(3)
        .expect("held B must be decoded")
        .texture
        .id();
    let b_mesh = |output: &egui::FullOutput| {
        output
            .shapes
            .iter()
            .find_map(|shape| match &shape.shape {
                egui::Shape::Mesh(mesh) if mesh.texture_id == b => {
                    let bounds = Rect::from_points(
                        &mesh
                            .vertices
                            .iter()
                            .map(|vertex| vertex.pos)
                            .collect::<Vec<_>>(),
                    );
                    (bounds.width() > 200.0 && bounds.height() > 100.0)
                        .then_some((bounds, shape.clip_rect))
                }
                _ => None,
            })
            .expect("the actual held B photograph must reach the main Compare canvas")
    };
    let (photo, before) = b_mesh(&output);
    let start = photo.center();
    let target = egui::pos2(photo.left() + photo.width() * 0.25, start.y);
    time += 0.1;
    let _ = workbench_scene(
        &mut app,
        &ctx,
        time,
        vec![
            egui::Event::PointerMoved(start),
            workbench_button(start, true),
        ],
    );
    time += 0.1;
    let output = workbench_scene(
        &mut app,
        &ctx,
        time,
        vec![egui::Event::PointerMoved(target)],
    );
    let (_, after) = b_mesh(&output);
    assert!(
        before.left() - after.left() > photo.width() * 0.15,
        "dragging the real wipe must change B's painted clip, not merely app metadata"
    );
    time += 0.1;
    let _ = workbench_scene(&mut app, &ctx, time, vec![workbench_button(target, false)]);
    assert_eq!(app.held_pair, Some([0, 3]));
    app.progress
        .ingest("STREHL_UI_PROGRESS event=align-pair-start i=3 j=7 started=3 frames=8 total=10\n");
    app.follow_current_frame();
    app.sync_workbench_phase();
    assert_eq!(app.live_pair(), [3, 7]);
    assert_eq!(app.current_pair(), [0, 3]);
    assert_eq!(
        app.selected, 7,
        "live source following must continue behind the held inspection"
    );
    time += 0.1;
    let output = workbench_scene(&mut app, &ctx, time, vec![]);
    let live = canvas_control(&output, "Live view");
    let _ = workbench_click(&mut app, &ctx, &mut time, live);
    assert_eq!(app.held_pair, None);
    assert_eq!(app.current_pair(), [3, 7]);
    assert!(app.follow_processing);
    assert_eq!(app.selected, 7);
    app.hold_pair([50, 1]);
    assert_eq!(
        app.held_pair, None,
        "invalid endpoint indices cannot create an inspection pair"
    );
    wait_for(&mut app, &ctx, |app| {
        app.source_photo(3).is_some() && app.source_photo(7).is_some()
    });
    time += 0.1;
    let _ = workbench_scene(&mut app, &ctx, time, vec![]);
    time += 0.3;
    let output = workbench_scene(&mut app, &ctx, time, vec![]);
    let live_b = app
        .source_photo(7)
        .expect("live B must be decoded")
        .texture
        .id();
    let live_photo = output
        .shapes
        .iter()
        .find_map(|shape| match &shape.shape {
            egui::Shape::Mesh(mesh) if mesh.texture_id == live_b => {
                let bounds = Rect::from_points(
                    &mesh
                        .vertices
                        .iter()
                        .map(|vertex| vertex.pos)
                        .collect::<Vec<_>>(),
                );
                (bounds.width() > 200.0 && bounds.height() > 100.0).then_some(bounds)
            }
            _ => None,
        })
        .expect("the resumed live B must be painted in the actual Compare canvas");
    assert_eq!(
        app.held_pair, None,
        "the first live wipe must begin without an existing hold"
    );
    let start = live_photo.center();
    let target = egui::pos2(live_photo.left() + live_photo.width() * 0.7, start.y);
    time += 0.1;
    let _ = workbench_scene(
        &mut app,
        &ctx,
        time,
        vec![
            egui::Event::PointerMoved(start),
            workbench_button(start, true),
        ],
    );
    time += 0.1;
    let _ = workbench_scene(
        &mut app,
        &ctx,
        time,
        vec![egui::Event::PointerMoved(target)],
    );
    assert_eq!(
        app.held_pair,
        Some([3, 7]),
        "the app must consume the first wipe gesture's actual displayed-pair return"
    );
    time += 0.1;
    let _ = workbench_scene(&mut app, &ctx, time, vec![workbench_button(target, false)]);
    app.progress
        .ingest("STREHL_UI_PROGRESS event=align-pair-start i=4 j=6 started=4 frames=8 total=10\n");
    app.follow_current_frame();
    app.sync_workbench_phase();
    assert_eq!(app.live_pair(), [4, 6]);
    assert_eq!(
        app.current_pair(),
        [3, 7],
        "new observations must not move a pair the user is actively comparing"
    );
    assert!(app.follow_processing);
    assert_eq!(app.selected, 6);
}

fn filmstrip_scene(
    app: &mut StrehlApp,
    ctx: &Context,
    size: [f32; 2],
    time: f64,
    events: Vec<egui::Event>,
) -> egui::FullOutput {
    ctx.run(
        RawInput {
            screen_rect: Some(Rect::from_min_size(
                Pos2::ZERO,
                egui::vec2(size[0], size[1]),
            )),
            time: Some(time),
            events,
            ..Default::default()
        },
        |ctx| app.filmstrip(ctx),
    )
}

fn strip_photo(output: &egui::FullOutput, texture: egui::TextureId) -> (Rect, Rect, u8) {
    output
        .shapes
        .iter()
        .find_map(|shape| match &shape.shape {
            egui::Shape::Mesh(mesh) if mesh.texture_id == texture => {
                let bounds = Rect::from_points(
                    &mesh
                        .vertices
                        .iter()
                        .map(|vertex| vertex.pos)
                        .collect::<Vec<_>>(),
                );
                ((bounds.width() - 78.0).abs() < 0.01 && (bounds.height() - 38.0).abs() < 0.01)
                    .then_some((bounds, shape.clip_rect, mesh.vertices[0].color.a()))
            }
            _ => None,
        })
        .expect("actual source photograph must be painted in the strip")
}

#[test]
fn last_filmstrip_photos_remain_fixed_and_opaque_during_end_follow_and_real_wheel_input() {
    const COUNT: usize = 31;
    for size in [[1060.0, 720.0], [1440.0, 940.0]] {
        let ctx = Context::default();
        theme::install(&ctx);
        let directory = jobs::tests::TestDirectory::new("end-clamped-filmstrip-native-and-detail");
        let mut app = app();
        app.process_view = false;
        app.stack = Some(camera_stack_with_native_strip(directory.path(), COUNT));
        app.activity = true;
        app.progress.ingest(&format!("STREHL_UI_PROGRESS event=stage name=merge total={COUNT}\nSTREHL_UI_PROGRESS event=frame-started index=30 total={COUNT}\n"));
        app.follow_current_frame();
        filmstrip_scene(&mut app, &ctx, size, 0.0, vec![]);
        wait_for(&mut app, &ctx, |app| {
            (COUNT - 24..COUNT).all(|index| app.browser.has_thumbnail(index))
        });
        assert_eq!(
            app.browser.thumbnail(27).unwrap().size(),
            [8, 6],
            "fixture must contain an actual native4:3 thumbnail before its3:2 detail decode"
        );
        let native_id = app.browser.thumbnail(27).unwrap().id();
        let last_id = app.browser.thumbnail(COUNT - 1).unwrap().id();
        filmstrip_scene(&mut app, &ctx, size, 0.2, vec![]);
        filmstrip_scene(&mut app, &ctx, size, 0.4, vec![]);
        let stable = filmstrip_scene(&mut app, &ctx, size, 0.6, vec![]);
        let expected = strip_photo(&stable, last_id);
        assert_eq!(
            expected.2, 255,
            "warm fixture must actually finish its thumbnail reveal"
        );
        assert!(
            expected.1.expand(0.1).contains_rect(expected.0),
            "last photo is visible at the actual scroll end"
        );
        let end_range = app.visible_sources.clone();
        assert!(end_range.contains(&(COUNT - 1)) && end_range[0] > 0);
        let pointer = expected.0.center();
        filmstrip_scene(
            &mut app,
            &ctx,
            size,
            0.7,
            vec![
                egui::Event::PointerMoved(pointer),
                egui::Event::MouseWheel {
                    unit: egui::MouseWheelUnit::Point,
                    delta: egui::vec2(-10_000.0, 0.0),
                    modifiers: egui::Modifiers::NONE,
                },
            ],
        );
        for (turn, index) in [28, 29, 30, 29, 30].into_iter().enumerate() {
            app.progress.ingest(&format!(
                "STREHL_UI_PROGRESS event=frame-started index={index} total={COUNT}\n"
            ));
            app.follow_current_frame();
            assert_eq!(
                app.selected, index,
                "fixture must exercise new actual processing identities"
            );
            let time = 1.0 + turn as f64 * 0.5;
            let on_follow = filmstrip_scene(&mut app, &ctx, size, time, vec![]);
            let settled = filmstrip_scene(&mut app, &ctx, size, time + 0.1, vec![]);
            for output in [&on_follow, &settled] {
                let actual = strip_photo(output, last_id);
                assert!(
                    (actual.0.min - expected.0.min).length() < 0.1
                        && (actual.0.max - expected.0.max).length() < 0.1,
                    "end-clamped following cannot paint an overshot strip then snap back: {:?} vs {:?}",
                    actual.0,
                    expected.0
                );
                assert_eq!(
                    actual.2, 255,
                    "cached thumbnails cannot restart a fade during live following"
                );
            }
            assert_eq!(
                app.visible_sources, end_range,
                "end-clamped visible identities remain fixed"
            );
            wait_for(&mut app, &ctx, |app| app.browser.has_image(index));
            assert_eq!(
                app.browser.thumbnail(27).unwrap().id(),
                native_id,
                "later canonical detail deliveries cannot replace an established native strip texture"
            );
        }
        // A newer foreground request may correctly cancel speculative27
        // refinement. Request it explicitly before checking its real delivery;
        // the established native contact must still retain identity.
        app.select(27);
        wait_for(&mut app, &ctx, |app| app.browser.has_image(27));
        assert_eq!(app.browser.thumbnail(27).unwrap().id(), native_id);
        assert_eq!(app.browser.texture_snapshot(27).unwrap().2, [120, 80]);
    }
}

#[test]
fn old_unclamped_follow_offset_really_overshoots_before_egui_clamps_its_state() {
    // Deliberate negative control: this is the retired offset rule. An egui
    // viewport consumer sees it before ScrollArea::end clamps persisted state.
    let ctx = Context::default();
    theme::install(&ctx);
    let texture = ctx.load_texture(
        "unclamped-scroll-pixel-witness",
        egui::ColorImage::new([8, 6], vec![Color32::WHITE; 48]),
        egui::TextureOptions::NEAREST,
    );
    let mut saw_excess = false;
    let mut draw = |force: bool, time: f64| {
        ctx.run(
            RawInput {
                screen_rect: Some(Rect::from_min_size(Pos2::ZERO, egui::vec2(1060.0, 720.0))),
                time: Some(time),
                ..Default::default()
            },
            |ctx| {
                egui::TopBottomPanel::bottom("unclamped-scroll-negative")
                    .exact_height(112.0)
                    .frame(egui::Frame::new().inner_margin(egui::Margin::symmetric(14, 6)))
                    .show(ctx, |ui| {
                        ui.label("Focus sweep");
                        let old_request =
                            ((30.0_f32 * 84.0 - ui.available_width() * 0.45).max(0.0) / 84.0)
                                .floor()
                                * 84.0;
                        let mut scroll = egui::ScrollArea::horizontal()
                            .id_salt("old-unclamped-offset")
                            .auto_shrink([false, false]);
                        if force {
                            scroll = scroll.horizontal_scroll_offset(old_request);
                        }
                        scroll.show_viewport(ui, |ui, viewport| {
                            if force {
                                saw_excess |= viewport.min.x
                                    > (31.0 * 84.0 - viewport.width()).max(0.0) + 20.0;
                            }
                            let first = (viewport.min.x / 84.0).floor().max(0.0) as usize;
                            ui.set_min_width(31.0 * 84.0);
                            ui.horizontal(|ui| {
                                ui.spacing_mut().item_spacing.x = 6.0;
                                ui.add_space(first as f32 * 84.0);
                                for _ in first..31 {
                                    let (rect, _) = ui.allocate_exact_size(
                                        egui::vec2(78.0, 38.0),
                                        egui::Sense::hover(),
                                    );
                                    ui.painter().image(
                                        texture.id(),
                                        rect,
                                        Rect::from_min_max(Pos2::ZERO, egui::pos2(1.0, 1.0)),
                                        Color32::WHITE,
                                    );
                                }
                            });
                        });
                    });
            },
        )
    };
    let forced = draw(true, 0.0);
    let clamped = draw(false, 0.2);
    let rightmost = |output: &egui::FullOutput| {
        output
            .shapes
            .iter()
            .filter_map(|shape| match &shape.shape {
                egui::Shape::Mesh(mesh) if mesh.texture_id == texture.id() => Some(
                    Rect::from_points(&mesh.vertices.iter().map(|v| v.pos).collect::<Vec<_>>()),
                ),
                _ => None,
            })
            .max_by(|a, b| a.max.x.total_cmp(&b.max.x))
            .expect("negative control must paint a real source quad")
    };
    assert!(
        saw_excess,
        "negative control must actually exceed the legal end offset"
    );
    assert!(
        (rightmost(&forced).right() - rightmost(&clamped).right()).abs() > 20.0,
        "retired rule must produce a visible snap, or the end-flicker gate has no rejecting power"
    );
}

#[test]
fn importing_a_new_capture_clears_the_old_process_and_inspection_state() {
    let directory = jobs::tests::TestDirectory::new("app-import-process-reset");
    let mut app = app();
    app.stack = Some(stack(20));
    app.progress.ingest(
        "STREHL_UI_PROGRESS event=stage name=alignment total=20\n\
STREHL_UI_PROGRESS event=align-phase name=pairs frames=20 total=100\n\
STREHL_UI_PROGRESS event=align-pair i=1 j=9 completed=1 accepted=1 frames=20 total=100\n",
    );
    app.sync_workbench_phase();
    app.hold_pair([1, 9]);
    app.workbench.set_pin(egui::pos2(0.27, 0.71));
    app.activity = true;
    app.recorded = true;
    app.process_view = true;
    app.log("old capture trace");
    assert!(
        app.progress.alignment_latest_pair.is_some()
            && !app.logs.is_empty()
            && app.workbench.pin().is_some(),
        "the fixture must carry real old-session evidence before reset"
    );
    let epoch = app.epoch;
    app.import(directory.path().to_path_buf());
    assert!(app.epoch > epoch);
    assert_eq!(app.progress.stage, Stage::Preparing);
    assert_eq!(app.progress.frames_total, None);
    assert_eq!(app.progress.alignment_latest_pair, None);
    assert!(app.progress.alignment_observed_pairs.is_empty());
    assert!(app.logs.is_empty());
    assert!(!app.activity && !app.recorded);
    assert!(
        app.process_view,
        "a new bracket remains in the persistent workspace"
    );
    assert_eq!(app.held_pair, None);
    assert_eq!(app.canvas_mode, None);
    assert_eq!(app.workbench.pin(), None);
    assert_eq!(app.last_stage, Stage::Preparing);
    assert!(app.follow_processing);
}

fn process_workspace(
    app: &mut StrehlApp,
    ctx: &Context,
    size: [f32; 2],
    time: f64,
) -> egui::FullOutput {
    ctx.run(
        RawInput {
            screen_rect: Some(Rect::from_min_size(
                Pos2::ZERO,
                egui::vec2(size[0], size[1]),
            )),
            time: Some(time),
            ..Default::default()
        },
        |ctx| {
            app.status_bar(ctx);
            app.workspace(ctx);
        },
    )
}

#[test]
fn process_replaces_the_small_dock_with_the_actual_full_workspace() {
    // A real stored output is the geometry witness. The primary photograph
    // must dominate the new process canvas, with no settings dock competing.
    for size in [[1060.0, 720.0], [1440.0, 940.0]] {
        let ctx = Context::default();
        theme::install(&ctx);
        let mut app = app();
        app.stack = Some(stack(259));
        app.activity = true;
        app.recorded = true;
        app.process_view = true;
        app.progress.ingest("STREHL_UI_PROGRESS event=stage name=alignment total=259\nSTREHL_UI_PROGRESS event=stage name=merge total=259\nSTREHL_UI_PROGRESS event=stage name=render total=259\n");
        app.progress.mark_complete();
        let result = cache_image(
            &ctx,
            image("actual-process-result.tiff", [211, 130, 24, 255]),
        );
        let texture = result.texture.id();
        install_viewer(&mut app.result_viewer, &result);
        app.result = Some(PathBuf::from("actual-process-result.tiff"));
        app.image_path = app.result.clone();
        let _ = process_workspace(&mut app, &ctx, size, 0.0);
        let output = process_workspace(&mut app, &ctx, size, 0.1);
        let text: Vec<_> = output
            .shapes
            .iter()
            .filter_map(|s| match &s.shape {
                egui::Shape::Text(t) => Some(t.galley.text()),
                _ => None,
            })
            .collect();
        assert!(
            text.contains(&"READ")
                && text.contains(&"REGISTER")
                && text.contains(&"COMBINE")
                && text.contains(&"SAVED")
                && text.contains(&"Recorded"),
            "actual workspace text: {text:?}"
        );
        assert!(
            !text.contains(&"Make the photograph"),
            "the settings dock must not consume the process viewport"
        );
        let bounds = output
            .shapes
            .iter()
            .filter_map(|s| match &s.shape {
                egui::Shape::Mesh(m) if m.texture_id == texture => Some(Rect::from_points(
                    &m.vertices.iter().map(|v| v.pos).collect::<Vec<_>>(),
                )),
                _ => None,
            })
            .max_by(|a, b| a.width().total_cmp(&b.width()))
            .expect("actual output must be in the process scene");
        assert!(
            bounds.width() > size[0] * 0.25 && bounds.height() > size[1] * 0.25,
            "the actual output must occupy the photo stage, not a small endpoint: {bounds:?}"
        );
        // Selecting Photos is an actual negative arm with the same capture.
        app.process_view = false;
        app.dock_live = false;
        app.view = View::Result;
        app.sidebar = Some(super::workspace::Sidebar::Adjust);
        let photos = process_workspace(&mut app, &ctx, size, 0.2);
        assert!(photos.shapes.iter().any(
            |s| matches!(&s.shape,egui::Shape::Text(t) if t.galley.text()=="RENDER SETTINGS")
        ));
        let old_right = photos
            .shapes
            .iter()
            .filter_map(|s| match &s.shape {
                egui::Shape::Mesh(m) if m.texture_id == texture => Some(
                    Rect::from_points(&m.vertices.iter().map(|v| v.pos).collect::<Vec<_>>())
                        .right(),
                ),
                _ => None,
            })
            .max_by(f32::total_cmp)
            .expect("negative arm must paint the same output alongside the real settings dock");
        assert!(
            old_right < size[0] - 300.0,
            "the rejecting layout arm must actually consume the324px settings width"
        );
    }
}

#[test]
fn process_inspection_keeps_the_scene_running_and_explicitly_opens_a_held_pair() {
    let mut app = app();
    app.stack = Some(stack(12));
    app.activity = true;
    app.process_view = true;
    app.progress.ingest("STREHL_UI_PROGRESS event=stage name=alignment total=12\nSTREHL_UI_PROGRESS event=align-phase name=pairs total=33 frames=12\nSTREHL_UI_PROGRESS event=align-pair-start i=4 j=9 started=1 total=33 frames=12\n");
    app.apply_process_response(
        process_space::Response {
            compare_pair: Some([1, 7]),
            ..Default::default()
        },
        12,
    );
    assert!(app.process_view && app.follow_processing);
    assert_eq!(app.held_pair, Some([1, 7]));
    app.apply_process_response(
        process_space::Response {
            compare_pair: Some([1, 7]),
            open_sources: true,
            ..Default::default()
        },
        12,
    );
    assert!(app.process_view, "source inspection remains inside Process");
    assert_eq!(app.process_space.inspection_frame(), Some(app.selected));
    assert_eq!(
        app.held_pair, None,
        "source inspection releases the comparison pair"
    );
    app.apply_process_response(
        process_space::Response {
            return_live: true,
            ..Default::default()
        },
        12,
    );
    assert!(app.process_view && app.follow_processing);
    assert_eq!(app.held_pair, None);
    assert_eq!(app.current_pair(), [4, 9]);
}

#[test]
fn alignment_follow_updates_the_photo_without_dragging_the_filmstrip_viewport() {
    let mut app = app();
    app.stack = Some(stack(259));
    app.follow_processing = true;
    app.progress.ingest("STREHL_UI_PROGRESS event=stage name=alignment total=259\nSTREHL_UI_PROGRESS event=align-phase name=pairs frames=259 total=900\n");
    for (started, pair) in [[0, 258], [3, 71], [1, 257], [108, 144]]
        .into_iter()
        .enumerate()
    {
        app.reveal_selected = false;
        app.progress.ingest(&format!(
            "STREHL_UI_PROGRESS event=align-pair-start i={} j={} started={} total=900 frames=259\n",
            pair[0],
            pair[1],
            started + 1
        ));
        app.follow_current_frame();
        assert_eq!(app.selected, pair[1]);
        assert!(app.follow_processing);
        assert!(
            !app.reveal_selected,
            "observed long-edge pair hops must not schedule a filmstrip pan"
        );
    }
    app.inspect_frame(17);
    assert_eq!(app.selected, 17);
    assert!(
        app.reveal_selected,
        "explicit source navigation still reveals its chosen cell"
    );
}

#[test]
fn pending_dialog_blocks_both_render_and_draft_before_any_worker_is_started() {
    let mut app = app();
    app.stack = Some(stack(20));
    app.engine = Some(PathBuf::from("dialog-guard-must-never-launch.exe"));
    let (_sender, receiver) = mpsc::channel();
    app.dialog = Some(receiver);
    app.draft_epoch = 711;
    app.status = "before pending dialog".into();
    assert!(
        app.stack.is_some()
            && app.engine.is_some()
            && app.scan.is_none()
            && app.job.is_none()
            && app.draft_job.is_none(),
        "the dialog must be the sole blocking precondition"
    );
    app.start_render();
    assert!(
        app.job.is_none(),
        "a pending file dialog cannot race a new render process"
    );
    assert!(app.started.is_none() && !app.activity);
    app.start_draft();
    assert!(
        app.draft_job.is_none(),
        "a pending file dialog cannot race a new JPEG draft worker"
    );
    assert_eq!(
        app.draft_epoch, 711,
        "the guard must run before draft-generation state is mutated"
    );
    assert!(app.view == View::Sources);
    assert_eq!(app.status, "before pending dialog");
}

#[test]
fn source_picker_uses_visual_browser_and_blocks_other_launches() {
    let directory = jobs::tests::TestDirectory::new("visual-bracket-picker");
    let mut app = app();
    app.stack = Some(camera_stack(directory.path(), 2, 32));
    app.engine = Some(PathBuf::from("picker-guard-must-never-launch.exe"));
    app.pick(Dialog::Source);
    assert!(app.bracket_browser.active());
    assert!(
        app.dialog.is_none(),
        "opening brackets must not launch a native folder dialog"
    );
    app.pick(Dialog::Output);
    assert!(
        app.dialog.is_none(),
        "a modal bracket choice cannot race a second picker"
    );
    app.start_render();
    app.start_draft();
    assert!(app.job.is_none() && app.draft_job.is_none());
    assert!(
        app.stack.is_some(),
        "browsing leaves the current capture intact until selection"
    );
}

#[test]
fn completion_loads_and_paints_owned_tiff_on_scheduled_frames_without_pointer_input() {
    // Rejection witness: move poll_images before terminal events and omit
    // pending_result from scheduling. With the source cache idle, this loop
    // loses its repaint deadline before the real TIFF decoder can start.
    let directory = jobs::tests::TestDirectory::new("completion-without-pointer");
    let sources = directory.path().join("source");
    std::fs::create_dir(&sources).unwrap();
    let output_path = directory.path().join("finished.tiff");
    image::RgbImage::from_fn(96, 64, |x, y| {
        image::Rgb([(x * 2) as u8, (y * 3) as u8, 143])
    })
    .save(&output_path)
    .unwrap();
    let ctx = Context::default();
    theme::install(&ctx);
    let mut app = app();
    app.stack = Some(camera_stack_with_native_strip(&sources, 3));
    app.selected = 1;
    app.process_view = true;
    app.activity = true;
    app.progress.ingest("planes: 90 x 60 per CFA plane\nSTREHL_UI_PROGRESS event=diagnostic seq=1 frame=2 level=0 kind=gate-support scope=frame scale=linear width=3 height=2 min=0 max=1 folded=1 total=3 sampling=nearest data=00ff00ff00ff\nSTREHL_UI_PROGRESS event=diagnostic seq=2 frame=2 level=0 kind=reconstructed scope=stack scale=linear width=3 height=2 min=10 max=1000 folded=3 total=3 sampling=nearest data=00102080c0ff\n");
    app.cache_process_surfaces(&ctx);
    assert_eq!(
        app.process_surfaces.len(),
        2,
        "fixture needs both an actual map and reconstruction"
    );
    let mut time = 0.0;
    let tick = |app: &mut StrehlApp, time: f64| {
        ctx.run(
            RawInput {
                screen_rect: Some(Rect::from_min_size(Pos2::ZERO, egui::vec2(1440.0, 940.0))),
                time: Some(time),
                // No cursor, keys, screenshot request or synthetic hover.
                ..Default::default()
            },
            |ctx| app.update_workspace(ctx),
        )
    };
    let warm_deadline = Instant::now() + Duration::from_secs(5);
    loop {
        let _ = tick(&mut app, time);
        time += 0.02;
        if app.browser.has_image(app.preview_target())
            && !app.browser.active()
            && !app.process_space.transitioning()
            && (0..3).all(|index| app.browser.native_thumbnail(index).is_some())
        {
            break;
        }
        assert!(
            Instant::now() < warm_deadline,
            "the idle-cache precondition never occurred"
        );
        std::thread::sleep(Duration::from_millis(2));
    }
    for _ in 0..8 {
        let _ = tick(&mut app, time);
        time += 0.02;
    }
    assert!(!app.browser.active() && app.result_work.is_none() && app.pending_result.is_none());
    // Completing while inspecting Sources must still present the photograph
    // with its diagnostics, without waiting for a manual return to Process.
    app.process_view = false;

    // Supply the engine's terminal transport from another thread. The actual
    // RenderJob still owns and reaps its worker; an invalid exposure makes that
    // unused worker fail before accessing any paths or launching an engine.
    let mut job = jobs::start_render(RenderRequest {
        executable: directory.path().join("must-never-launch.exe"),
        source: sources,
        output_parent: directory.path().join("unused-output"),
        exposure_ev: Some(f32::NAN),
        pyramid_gate: None,
        worker_threads: Some(1),
        settings: jobs::RenderSettings::default(),
    });
    let (sender, receiver) = mpsc::channel();
    job.receiver = receiver;
    app.job = Some(job);
    let delivered = output_path.clone();
    let job_directory = directory.path().to_path_buf();
    std::thread::spawn(move || {
        sender
            .send(RenderEvent::Finished(RenderOutcome::Completed {
                log: job_directory.join("render.log"),
                directory: job_directory,
                output: delivered,
            }))
            .unwrap();
    })
    .join()
    .unwrap();

    assert!(
        app.screenshot.is_none(),
        "screenshot mode must not supply its perpetual repaint timer"
    );
    let mut observed_loading = false;
    let mut observed_output = false;
    for frame in 0..180 {
        let painted = tick(&mut app, time);
        if frame == 0 {
            assert!(
                app.job.is_none() && app.result_work.is_some() && app.pending_result.is_none(),
                "the terminal tick must dispatch the actual TIFF decoder before the event loop can sleep; spare egui repaints cannot rescue this assertion"
            );
        }
        observed_loading |= app.result_work.is_some();
        let actual = app.result_viewer.texture.as_ref().map(TextureHandle::id);
        let opaque_output = actual.is_some_and(|id| {
            painted.shapes.iter().any(|shape| {
                matches!(&shape.shape, egui::Shape::Mesh(mesh)
                if mesh.texture_id == id && !mesh.vertices.is_empty()
                && mesh.vertices.iter().all(|vertex| vertex.color.a() == 255))
            })
        });
        if opaque_output && !app.process_space.transitioning() {
            assert!(
                painted_support_markers(&painted).len() >= 3,
                "completion must preserve visible observed diagnostics beside the photograph"
            );
            observed_output = true;
            break;
        }
        let delay = painted.viewport_output[&egui::ViewportId::ROOT].repaint_delay;
        assert!(
            delay <= Duration::from_millis(100),
            "TIFF publication or reveal went idle and would require pointer input: {delay:?}"
        );
        let elapsed = delay.max(Duration::from_millis(16));
        std::thread::sleep(elapsed);
        time += elapsed.as_secs_f64();
    }
    assert!(
        observed_loading,
        "the real asynchronous decoder must run in this fixture"
    );
    assert!(
        observed_output,
        "the actual saved TIFF never became fully visible"
    );
    assert_eq!(app.result.as_ref(), Some(&output_path));
    assert_eq!(app.image_path.as_ref(), Some(&output_path));
    assert!(app.process_view && app.job.is_none() && app.error.is_none());
}

#[test]
fn process_surface_cache_preserves_observed_identity_scope_and_import_boundary() {
    let ctx = Context::default();
    theme::install(&ctx);
    let mut app = app();
    app.stack = Some(stack(5));
    app.activity = true;
    app.process_view = true;
    app.progress.ingest("planes: 90 x 60 per CFA plane\nSTREHL_UI_PROGRESS event=diagnostic seq=1 frame=2 level=0 kind=gate-support scope=frame scale=linear width=3 height=2 min=0 max=1 folded=1 total=5 sampling=nearest data=000000ffffff\n");
    app.cache_process_surfaces(&ctx);
    assert_eq!(
        app.process_surfaces.len(),
        1,
        "fixture must cross parser and GPU cache"
    );
    let texture = app.process_surfaces[0].texture.id();
    assert_eq!(app.process_surfaces[0].frame, Some(2));
    assert_eq!(app.process_surfaces[0].packet.scope, DiagnosticScope::Frame);
    assert_eq!(app.process_surfaces[0].texture.size(), [3, 2]);
    let output = process_workspace(&mut app, &ctx, [1440.0, 940.0], 0.0);
    let support = painted_support_markers(&output);
    assert!(
        support.len() >= 3,
        "actual positive observations must reach Process painting at sampled positions"
    );
    assert!(
        support.iter().any(|(_, pane)| {
            [15.5_f32, 45.5, 75.5].into_iter().all(|x| {
                let expected = pane.min + egui::vec2(x / 90.0, 45.5 / 60.0) * pane.size();
                support
                    .iter()
                    .any(|(point, clip)| clip == pane && point.distance(expected) < 0.01)
            })
        }),
        "retained diagnostic mesh must preserve all three real bottom-row sample coordinates"
    );
    assert!(
        !output.shapes.iter().any(|shape| matches!(&shape.shape,
        egui::Shape::Mesh(mesh) if mesh.texture_id == texture)),
        "binary telemetry must not expand into inferred filled blocks"
    );

    app.progress.ingest("STREHL_UI_PROGRESS event=diagnostic seq=2 frame=4 level=0 kind=gate-support scope=frame scale=linear width=3 height=2 min=0 max=1 folded=1 total=5 sampling=nearest data=ffffff000000\n");
    app.cache_process_surfaces(&ctx);
    assert_eq!(
        app.process_surfaces.len(),
        1,
        "new actual frame updates the same kind/level slot"
    );
    assert_ne!(
        app.process_surfaces[0].texture.id(),
        texture,
        "a delivered observation must keep its pixels while the stage reveals its successor"
    );
    assert_eq!(app.process_surfaces[0].sequence, 2);
    assert_eq!(app.process_surfaces[0].frame, Some(4));
    assert_eq!(app.process_surfaces[0].packet.scope, DiagnosticScope::Frame);
    app.progress.ingest("STREHL_UI_PROGRESS event=diagnostic seq=1 frame=0 level=0 kind=gate-support scope=frame scale=linear width=3 height=2 min=0 max=1 folded=1 total=5 sampling=nearest data=ffffffffffff\n");
    app.cache_process_surfaces(&ctx);
    assert_eq!(
        app.process_surfaces[0].frame,
        Some(4),
        "stale map sequence cannot relabel current pixels"
    );

    app.progress.ingest("STREHL_UI_PROGRESS event=diagnostic seq=3 frame=4 level=0 kind=averaging scope=stack scale=linear width=3 height=2 min=0 max=1 folded=2 total=5 sampling=nearest data=000000ffffff\n");
    app.cache_process_surfaces(&ctx);
    let aggregate = app
        .process_surfaces
        .iter()
        .find(|surface| surface.kind == DiagnosticKind::Averaging)
        .unwrap();
    assert_eq!(
        aggregate.frame, None,
        "an accumulated stack map cannot be labelled as its last input frame"
    );
    assert_eq!(aggregate.packet.scope, DiagnosticScope::Stack);
    assert_eq!(aggregate.meta.folded, 2);
    let mut reached_cap = false;
    for sequence in 4..388 {
        let level = (sequence - 4) % 64;
        let (kind, scope, scale, min, max) = match (sequence - 4) / 64 {
            0 => ("gate-support", "frame", "linear", 0, 1),
            1 => ("gate-floor", "frame", "log", 0, 10),
            2 => ("focus-energy", "frame", "log", 0, 10),
            3 => ("averaging", "stack", "linear", 0, 1),
            4 => ("coefficient", "stack", "symmetric", -10, 10),
            _ => ("preview", "stack", "linear", 0, 10),
        };
        app.progress.ingest(&format!("STREHL_UI_PROGRESS event=diagnostic seq={sequence} frame=1 level={level} kind={kind} scope={scope} scale={scale} width=3 height=2 min={min} max={max} folded=1 total=5 sampling=nearest data=000000ffffff\n"));
        app.cache_process_surfaces(&ctx);
        assert!(app.process_surfaces.len() <= 384);
        reached_cap |= app.process_surfaces.len() == 384;
    }
    assert!(
        reached_cap,
        "fixture must exercise cache capacity, not only a two-map happy path"
    );
    let directory = jobs::tests::TestDirectory::new("process-map-import-boundary");
    let old_epoch = app.epoch;
    app.import(directory.path().to_path_buf());
    assert!(app.epoch > old_epoch);
    assert!(app.process_surfaces.is_empty() && app.progress.diagnostic_surfaces.is_empty());
    app.progress.ingest("STREHL_UI_PROGRESS event=diagnostic seq=1 frame=0 level=0 kind=gate-support scope=frame scale=linear width=3 height=2 min=0 max=1 folded=1 total=5 sampling=nearest data=000000ffffff\n");
    app.cache_process_surfaces(&ctx);
    assert_eq!(app.process_surfaces.len(), 1);
    assert_eq!(app.process_surfaces[0].epoch, app.epoch);
    assert_eq!(
        app.process_surfaces[0].sequence, 1,
        "new epoch accepts a fresh sequence without carrying the old surface"
    );
}

#[test]
fn a_frame_burst_retains_every_mask_observation_but_uploads_only_the_latest_pixels() {
    let ctx = Context::default();
    let mut app = app();
    for index in 0..67 {
        let data = if index % 2 == 0 {
            "00ff00ff00ff"
        } else {
            "ff00ff00ff00"
        };
        app.progress.ingest(&format!("STREHL_UI_PROGRESS event=diagnostic seq={} frame={index} level=0 kind=gate-support scope=frame scale=linear width=3 height=2 min=0 max=1 folded=1 total=67 sampling=nearest data={data}\n", index + 1));
    }
    let rendered = ctx.run(egui::RawInput::default(), |ctx| {
        app.cache_process_surfaces(ctx)
    });
    assert_eq!(app.process_surfaces.len(), 1);
    assert_eq!(app.process_surfaces[0].frame, Some(66));
    assert_eq!(app.progress.sampled_mask_history[0].observations(), 67);
    assert!(
        rendered.textures_delta.set.len() <= 2,
        "67 same-slot deliveries must not enqueue67 redundant GPU uploads in one paint"
    );
}

#[test]
fn opened_unrelated_image_cannot_become_the_completed_process_output() {
    let ctx = Context::default();
    theme::install(&ctx);
    let mut app = app();
    app.stack = Some(stack(5));
    app.activity = true;
    app.process_view = true;
    app.progress
        .ingest("STREHL_UI_PROGRESS event=stage name=render total=5\n");
    app.progress.mark_complete();
    let owned_path = PathBuf::from("owned-completed-output.tiff");
    let owned = cache_image(
        &ctx,
        image("owned-completed-output.tiff", [214, 80, 18, 255]),
    );
    let owned_id = owned.texture.id();
    install_viewer(&mut app.result_viewer, &owned);
    app.result = Some(owned_path.clone());
    app.image_path = Some(owned_path.clone());
    let correct = process_workspace(&mut app, &ctx, [1440.0, 940.0], 0.0);
    assert!(
        correct.shapes.iter().any(|shape| matches!(&shape.shape,
        egui::Shape::Mesh(mesh) if mesh.texture_id == owned_id)),
        "owned output positive control must be painted"
    );

    let unrelated_path = PathBuf::from("opened-unrelated-image.tiff");
    app.open_result(unrelated_path.clone());
    app.pending_result = None;
    app.result_work = Some(ResultWork {
        epoch: app.epoch,
        task: image_task("opened-unrelated-image.tiff", [18, 40, 231, 255]),
    });
    wait_for(&mut app, &ctx, |app| {
        app.image_path.as_ref() == Some(&unrelated_path)
    });
    let unrelated_id = app.result_viewer.texture.as_ref().unwrap().id();
    assert_ne!(
        owned_id, unrelated_id,
        "fixture must load a different actual image"
    );
    assert_eq!(
        app.result.as_ref(),
        Some(&owned_path),
        "opening an image does not rewrite completed job ownership"
    );
    let photo_view = process_workspace(&mut app, &ctx, [1440.0, 940.0], 0.2);
    assert!(
        photo_view.shapes.iter().any(|shape| matches!(&shape.shape,
        egui::Shape::Mesh(mesh) if mesh.texture_id == unrelated_id)),
        "the opened image is genuinely available for ordinary photo viewing"
    );
    app.process_view = true;
    let process = process_workspace(&mut app, &ctx, [1440.0, 940.0], 0.4);
    assert!(
        !process.shapes.iter().any(|shape| matches!(&shape.shape,
        egui::Shape::Mesh(mesh) if mesh.texture_id == unrelated_id)),
        "an unrelated opened TIFF cannot impersonate the session's actual saved output"
    );
}

#[test]
fn new_render_resets_process_surfaces_output_and_late_previous_preview() {
    let ctx = Context::default();
    let directory = jobs::tests::TestDirectory::new("new-render-process-boundary");
    let mut app = app();
    app.stack = Some(stack(5));
    app.engine = Some(directory.path().join("missing-engine-no-raw-run.exe"));
    app.output = directory.path().join("job-output");
    app.progress.ingest("STREHL_UI_PROGRESS event=diagnostic seq=1 frame=2 level=0 kind=gate-support scope=frame scale=linear width=3 height=2 min=0 max=1 folded=1 total=5 sampling=nearest data=000000ffffff\n");
    app.cache_process_surfaces(&ctx);
    assert!(
        !app.process_surfaces.is_empty(),
        "fixture must carry an actual old diagnostic"
    );
    let old = cache_image(
        &ctx,
        image("previous-session-output.tiff", [231, 14, 44, 255]),
    );
    install_viewer(&mut app.result_viewer, &old);
    app.result = Some(PathBuf::from("previous-session-output.tiff"));
    app.image_path = app.result.clone();
    let (send, receive) = mpsc::sync_channel(1);
    app.result_work = Some(ResultWork {
        epoch: app.epoch,
        task: jobs::spawn_task("retired-old-output-test", move |_| {
            Ok(receive.recv().unwrap())
        }),
    });
    let epoch = app.epoch;
    app.start_render();
    assert!(
        app.job.is_some() && app.activity && app.process_view,
        "a newly started job opens Process by default"
    );
    assert_eq!(
        app.epoch, epoch,
        "rerender retains capture identity while resetting process history"
    );
    assert!(app.process_surfaces.is_empty() && app.progress.diagnostic_surfaces.is_empty());
    assert!(
        app.result_viewer.texture.is_none() && app.result.is_none() && app.image_path.is_none()
    );
    assert!(app.result_work.is_none() && app.pending_result.is_none());
    assert_eq!(app.progress.stage, Stage::Preparing);
    send.send(image("late-previous-output.tiff", [14, 231, 44, 255]))
        .unwrap();
    app.poll_images(&ctx);
    assert!(
        app.result_viewer.texture.is_none() && app.image_path.is_none(),
        "late old preview cannot enter the new process"
    );
}

#[test]
fn parsed_zero_coefficient_stays_neutral_without_erasing_real_signed_extrema() {
    fn observed(min: &str, max: &str, data: &str, width: usize) -> DiagnosticSurface {
        let mut progress = PipelineProgress::default();
        progress.ingest(&format!(
            "STREHL_UI_PROGRESS event=diagnostic seq=1 frame=2 level=3 kind=coefficient scope=stack scale=symmetric width={width} height=1 min={min} max={max} folded=3 total=3 sampling=nearest data={data}\n"
        ));
        assert_eq!(
            progress.diagnostic_surfaces.len(),
            1,
            "each control must pass the actual bounded transport parser"
        );
        progress.diagnostic_surfaces.pop_front().unwrap()
    }

    // The producer emits byte 00 for the degenerate all-zero range, but the
    // same byte is a real negative extremum when the symmetric extent is 4 DN.
    // Neutralising every zero byte would therefore fail the negative control.
    let zero = observed("0", "0", "00", 1);
    let negative = observed("-4", "-4", "00", 1);
    let positive = observed("4", "4", "ff", 1);
    assert_eq!(&*zero.pixels, &*negative.pixels);
    assert_ne!((zero.min, zero.max), (negative.min, negative.max));
    let neutral = diagnostic_image(&zero).pixels[0];
    let blue = diagnostic_image(&negative).pixels[0];
    let warm = diagnostic_image(&positive).pixels[0];
    assert_eq!(neutral.to_array(), [14, 17, 20, 255]);
    assert!(
        blue.b() > blue.r() + 50,
        "negative coefficients remain blue"
    );
    assert!(
        warm.r() > warm.b() + 50,
        "positive coefficients remain warm"
    );
    assert_ne!(blue, neutral);
    assert_ne!(warm, neutral);

    // Zero inside a nondegenerate signed range must agree with the neutral
    // degenerate surface, while both actual extrema retain their colours.
    let mixed = diagnostic_image(&observed("-4", "4", "0080ff", 3));
    assert_eq!(mixed.pixels, [blue, neutral, warm]);
}

#[test]
fn entering_process_from_a_middle_photos_viewport_warms_every_fixed_contact_then_stays_idle() {
    // A 65-frame middle bracket is insufficient: the ±40 trajectory would
    // eventually load its entire capture even with the retired truncation.
    const COUNT: usize = 259;
    const SELECTED: usize = 129;
    let directory = jobs::tests::TestDirectory::new("process-fixed-contact-prefetch");
    let ctx = Context::default();
    theme::install(&ctx);
    let mut app = app();
    app.stack = Some(camera_stack_with_native_strip(directory.path(), COUNT));
    app.selected = SELECTED;
    app.visible_sources = (123..=136).collect();
    app.view = View::Sources;
    app.process_view = true;
    app.activity = true;
    app.progress.ingest("STREHL_UI_PROGRESS event=stage name=alignment total=259\nSTREHL_UI_PROGRESS event=align-phase name=planes total=259 frames=259\nSTREHL_UI_PROGRESS event=align-plane index=129 completed=130 total=259 frames=259\n");
    let _ = process_workspace(&mut app, &ctx, [1060.0, 720.0], 0.0);
    let anchors = app.process_space.contact_indices();
    // The fixed capture axis and the adaptive contact network both
    // contribute identities to one bounded, deduplicated warming set.
    assert!(
        (2..=80).contains(&anchors.len()),
        "responsive network + shared timeline contacts stay within their combined fixed budget: {}",
        anchors.len()
    );
    assert_eq!(anchors.first(), Some(&0));
    assert_eq!(anchors.last(), Some(&(COUNT - 1)));

    // Whole-stack native residency now repairs even the retired narrow visible
    // list. Keep that actual input as a regression: an anchor outside the
    // old24-visible and40-neighbor policy must become resident without a new
    // selection, and a259-frame stack must exceed the old192-contact cache.
    let mut retired_warm = app.visible_sources.clone();
    retired_warm.extend(&anchors);
    retired_warm.extend(app.live_pair());
    retired_warm.extend((0..8).map(|step| step * (COUNT - 1) / 7));
    // Reproduce the retired scheduler's actual 24-visible nearest-first policy
    // explicitly. Passing its untruncated list to today's 96-visible scheduler
    // would silently repair the negative arm before any real decode occurred.
    retired_warm.sort_unstable_by_key(|index| index.abs_diff(SELECTED));
    retired_warm.dedup();
    retired_warm.truncate(24);
    let omitted = *anchors.iter().find(|&&index| index.abs_diff(SELECTED) > 40 && !retired_warm.contains(&index))
        .expect("the retired admission policy must actually reject a visible contact beyond trajectory warming");
    let mut retired = SourceBrowser::default();
    let mut retired_viewer = Viewer::default();
    assert!(retired.native_thumbnail(omitted).is_none());
    let start = Instant::now();
    let mut idle_samples = 0;
    while start.elapsed() < Duration::from_secs(5) {
        retired.poll(
            &ctx,
            app.epoch,
            SELECTED,
            &app.stack.as_ref().unwrap().frames,
            &retired_warm,
            4096,
            &mut retired_viewer,
        );
        if start.elapsed() > Duration::from_millis(300) && !retired.active() {
            idle_samples += 1;
            if idle_samples == 5 {
                break;
            }
        } else {
            idle_samples = 0;
        }
        std::thread::yield_now();
    }
    assert_eq!(
        idle_samples, 5,
        "the narrow visible-list arm must finish its whole-stack warming"
    );
    assert!(
        retired.native_thumbnail(omitted).is_some(),
        "whole-stack warming must repair an anchor omitted by the retired visible policy"
    );
    assert_eq!(retired.native_thumbnail_indices().len(), COUNT);

    let start = Instant::now();
    let mut idle_samples = 0;
    while start.elapsed() < Duration::from_secs(5) {
        app.poll_images(&ctx);
        let complete = anchors
            .iter()
            .all(|&index| app.browser.native_thumbnail(index).is_some());
        if complete && start.elapsed() > Duration::from_millis(300) && !app.browser.active() {
            idle_samples += 1;
            if idle_samples == 5 {
                break;
            }
        } else {
            idle_samples = 0;
        }
        std::thread::yield_now();
    }
    assert_eq!(
        idle_samples, 5,
        "the actual Process consumer must load all fixed contacts and stop decoding"
    );
    assert_eq!(app.selected, SELECTED);
    assert_eq!(
        app.visible_sources,
        (123..=136).collect::<Vec<_>>(),
        "warming Process must not rewrite the user's Photos viewport"
    );
    let identities: Vec<_> = anchors
        .iter()
        .map(|&index| (index, app.browser.native_thumbnail(index).unwrap().id()))
        .collect();
    let scene = process_workspace(&mut app, &ctx, [1060.0, 720.0], 1.0);
    assert_eq!(app.process_space.contact_indices(), anchors);
    for &(index, texture) in &identities {
        assert!(scene.shapes.iter().any(|shape| matches!(&shape.shape, egui::Shape::Mesh(mesh) if mesh.texture_id==texture && !mesh.vertices.is_empty())),
            "fixed contact {} must paint its actual decoded camera pixels", index + 1);
    }
    let native = app.browser.native_thumbnail_indices();
    assert!(
        native.len() <= 512,
        "native contacts retain their independent count cap"
    );
    assert_eq!(
        app.browser.canonical_indices().len(),
        COUNT,
        "whole-stack canonical coverage must coexist with the bounded native contact set"
    );
    let bytes: usize = native
        .iter()
        .map(|&index| {
            let [width, height] = app.browser.native_thumbnail(index).unwrap().size();
            width * height * 4
        })
        .sum();
    assert!(bytes <= 24 * 1024 * 1024);
    for _ in 0..20 {
        app.poll_images(&ctx);
        assert!(
            !app.browser.active(),
            "fully warmed contacts cannot enter a decode/evict loop"
        );
        for &(index, texture) in &identities {
            assert_eq!(app.browser.native_thumbnail(index).unwrap().id(), texture);
        }
    }
}

#[test]
fn process_capture_inspection_keeps_decoding_its_pixels_while_live_follow_advances() {
    // A distant, never-selected capture rejects the old accidental-cache path:
    // only an explicit persistent inspection pin can request its canonical JPEG.
    const INSPECTED: usize = 17;
    let directory = jobs::tests::TestDirectory::new("persistent-process-inspection");
    let ctx = Context::default();
    theme::install(&ctx);
    let mut app = app();
    app.stack = Some(camera_stack_with_native_strip(directory.path(), 259));
    app.activity = true;
    app.process_view = true;
    app.progress.ingest("STREHL_UI_PROGRESS event=stage name=alignment total=259\nSTREHL_UI_PROGRESS event=align-phase name=pairs frames=259 total=900\nSTREHL_UI_PROGRESS event=align-pair-start i=170 j=180 started=1 total=900 frames=259\n");
    app.follow_current_frame();
    wait_for(&mut app, &ctx, |app| app.source_photo(180).is_some());
    let _ = process_workspace(&mut app, &ctx, [1060.0, 720.0], 0.0);
    assert!(
        app.source_photo(INSPECTED).is_none(),
        "the target must genuinely start without canonical pixels"
    );
    app.process_space.inspect_frame(INSPECTED);

    let mut identity = None;
    let mut latest_scene = None;
    for (step, pair) in [[180, 190], [205, 215], [220, 230]].into_iter().enumerate() {
        app.progress.ingest(&format!(
            "STREHL_UI_PROGRESS event=align-pair-start i={} j={} started={} total=900 frames=259\n",
            pair[0],
            pair[1],
            step + 2
        ));
        app.follow_current_frame();
        assert_eq!(
            app.selected, pair[1],
            "live following must continue independently of explicit inspection"
        );
        assert!(app.follow_processing && app.process_view);
        assert_eq!(app.process_space.inspection_frame(), Some(INSPECTED));
        assert_eq!(
            app.process_pair(),
            [INSPECTED, pair[1]],
            "canonical scheduling must retain the inspected capture alongside current work"
        );
        wait_for(&mut app, &ctx, |app| {
            app.source_photo(INSPECTED).is_some() && app.source_photo(pair[1]).is_some()
        });
        let photo = app.source_photo(INSPECTED).unwrap();
        assert_eq!(photo.index, INSPECTED);
        assert_eq!(photo.aperture, [120, 80]);
        assert!(
            photo.texture.size()[0] >= 60,
            "an8×6 contact thumbnail cannot satisfy canonical inspection"
        );
        if let Some(previous) = identity {
            assert_eq!(
                photo.texture.id(),
                previous,
                "live hops must not evict and reload the protected canonical image"
            );
        }
        identity = Some(photo.texture.id());
        let scene = process_workspace(&mut app, &ctx, [1060.0, 720.0], step as f64 + 1.0);
        assert!(
            scene
                .shapes
                .iter()
                .any(|shape| matches!(&shape.shape, egui::Shape::Mesh(mesh)
            if mesh.texture_id == photo.texture.id() && !mesh.vertices.is_empty())),
            "the actual inspected capture must paint in the process scene while live selection moves"
        );
        latest_scene = Some(scene);
    }

    // Use the real Return live control, so this also exercises the parent
    // ProcessSpace -> app response handoff rather than clearing private state.
    let at = canvas_control(latest_scene.as_ref().unwrap(), "Live");
    for (time, events) in [
        (
            4.0,
            vec![egui::Event::PointerMoved(at), workbench_button(at, true)],
        ),
        (4.1, vec![workbench_button(at, false)]),
    ] {
        let _ = ctx.run(
            RawInput {
                screen_rect: Some(Rect::from_min_size(Pos2::ZERO, egui::vec2(1060.0, 720.0))),
                time: Some(time),
                events,
                ..Default::default()
            },
            |ctx| app.update_workspace(ctx),
        );
    }
    assert_eq!(app.process_space.inspection_frame(), None);
    assert_eq!(app.process_pair(), [220, 230]);
    assert_eq!(app.selected, 230);
    assert!(app.follow_processing && app.process_view);
}
