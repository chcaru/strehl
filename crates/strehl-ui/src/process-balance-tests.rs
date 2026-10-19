use super::*;
use crate::jobs::tests::TestDirectory;
use image::{ImageBuffer, Luma};

fn write_map(path: &Path, size: [usize; 2], values: Vec<u16>) {
    ImageBuffer::<Luma<u16>, Vec<u16>>::from_raw(size[0] as u32, size[1] as u32, values)
        .unwrap()
        .save_with_format(path, ImageFormat::Tiff)
        .unwrap();
}

fn read(path: &Path, size: [usize; 2]) -> Result<Decoded> {
    decode(path, size, &AtomicBool::new(false), &AtomicBool::new(false))
}

fn settle(lens: &mut ObservationBalance, ctx: &egui::Context, output: &Path, size: [usize; 2]) {
    let deadline = std::time::Instant::now() + Duration::from_secs(3);
    loop {
        lens.update(ctx, Some(output), Some(size));
        if lens.pending.is_none() {
            break;
        }
        assert!(
            std::time::Instant::now() < deadline,
            "balance worker did not finish"
        );
        std::thread::sleep(Duration::from_millis(2));
    }
}

#[test]
fn gray16_preserves_rank_endpoints_ties_and_missing_without_rescaling() {
    let directory = TestDirectory::new("balance-values");
    let path = directory.path().join("confidence.tiff");
    write_map(&path, [4, 1], vec![0, 500, 1000, MISSING]);
    let map = read(&path, [4, 1]).unwrap();
    assert_eq!(map.values, [0, 500, 1000, MISSING]);
    assert_eq!(map.image.size, [4, 1]);
    assert!(map.image.pixels[0].a() > 0, "a valid zero is not missing");
    assert_eq!(map.image.pixels[3].a(), 0);
    assert_ne!(map.image.pixels[0], map.image.pixels[2]);
    // A rank value cannot identify its generating observations. In particular,
    // all ties and an output below all observations both encode as zero.
    let same_zero_from_different_clouds = [vec![7.0, 7.0, 7.0], vec![8.0, 9.0, 10.0]];
    for observations in same_zero_from_different_clouds {
        assert_eq!(observations.iter().filter(|&&v| v < 7.0).count(), 0);
    }
    assert_eq!(
        value_at(&map.values, map.size, egui::pos2(0.1, 0.5)),
        Some(0)
    );
    assert_eq!(value_at(&map.values, map.size, egui::pos2(0.9, 0.5)), None);
}

#[test]
fn rejects_invalid_rank_and_matching_aspect_with_wrong_analysis_extent() {
    let directory = TestDirectory::new("balance-invalid");
    let path = directory.path().join("confidence.tiff");
    write_map(&path, [4, 2], vec![0; 8]);
    assert!(read(&path, [4, 2]).is_ok(), "positive control must decode");
    assert!(
        read(&path, [8, 4]).is_err(),
        "same aspect is not the analysis grid"
    );
    write_map(&path, [4, 2], vec![1001; 8]);
    assert!(
        read(&path, [4, 2]).is_err(),
        "1001 must not be clamped or normalized"
    );
    write_map(&path, [4, 2], vec![65534; 8]);
    assert!(read(&path, [4, 2]).is_err());
    write_map(&path, [4, 2], vec![MISSING; 8]);
    assert!(
        read(&path, [4, 2]).is_ok(),
        "sentinel is a distinct permitted value"
    );
    assert!(!valid_size([0, 2]));
    assert!(!valid_size([MAX_SIDE + 1, 1]));
    assert!(!valid_size([8192, 8192]));
}

#[test]
fn refuses_8_bit_rgb_and_non_tiff_maps_and_obsolete_work() {
    let directory = TestDirectory::new("balance-formats");
    let path = directory.path().join("confidence.tiff");
    image::GrayImage::new(2, 2)
        .save_with_format(&path, ImageFormat::Tiff)
        .unwrap();
    assert!(read(&path, [2, 2]).is_err());
    image::RgbImage::new(2, 2)
        .save_with_format(&path, ImageFormat::Tiff)
        .unwrap();
    assert!(read(&path, [2, 2]).is_err());
    ImageBuffer::<Luma<u16>, Vec<u16>>::from_raw(2, 2, vec![0; 4])
        .unwrap()
        .save_with_format(&path, ImageFormat::Png)
        .unwrap();
    assert!(read(&path, [2, 2]).is_err());
    write_map(&path, [2, 2], vec![500; 4]);
    assert!(
        decode(
            &path,
            [2, 2],
            &AtomicBool::new(false),
            &AtomicBool::new(true)
        )
        .is_err()
    );
    assert!(
        decode(
            &path,
            [2, 2],
            &AtomicBool::new(true),
            &AtomicBool::new(false)
        )
        .is_err()
    );
    assert!(read(&path, [2, 2]).is_ok());
}

#[test]
fn current_aperture_counts_only_its_samples_and_never_turns_missing_into_zero() {
    let values = [0, 1000, 500, MISSING, 0, 1000, 500, MISSING];
    let full = Rect::from_min_max(Pos2::ZERO, egui::pos2(1.0, 1.0));
    let all = distribution(&values, [4, 2], full);
    assert_eq!((all.observed, all.missing), (6, 2));
    assert_eq!(all.bins[0], 2);
    assert_eq!(all.bins[BINS - 1], 2);
    let right = Rect::from_min_max(egui::pos2(0.5, 0.0), egui::pos2(1.0, 1.0));
    let cropped = distribution(&values, [4, 2], right);
    assert_eq!((cropped.observed, cropped.missing), (2, 2));
    assert_eq!(
        cropped.bins[0], 0,
        "outside zeros must not enter the region"
    );
    assert_eq!(cropped.bins[10], 2);
    let only_missing = distribution(
        &values,
        [4, 2],
        Rect::from_min_max(egui::pos2(0.75, 0.0), egui::pos2(1.0, 1.0)),
    );
    assert_eq!((only_missing.observed, only_missing.missing), (0, 2));
    assert_eq!(only_missing.bins.iter().sum::<u32>(), 0);
    assert_eq!(
        distribution(&values, [4, 2], Rect::NOTHING),
        Distribution::default()
    );
    assert!(
        normalized(Rect::from_min_max(
            egui::pos2(-0.1, 0.0),
            egui::pos2(1.0, 1.0)
        ))
        .is_none(),
        "out-of-domain UV must not be clamped and stretched onto the same image rectangle"
    );
    assert_eq!(value_at(&values, [4, 2], egui::pos2(f32::NAN, 0.0)), None);
    assert_eq!(value_at(&values, [4, 2], egui::pos2(-0.1, 0.0)), None);
}

#[test]
fn region_sampling_is_bounded_but_exact_pin_is_not_the_nearest_texture_sample() {
    let directory = TestDirectory::new("balance-sampling");
    let path = directory.path().join("confidence.tiff");
    let mut values = vec![0; 4097];
    values[0] = 1000;
    write_map(&path, [4097, 1], values);
    let map = read(&path, [4097, 1]).unwrap();
    assert_eq!(map.image.size, [1024, 1]);
    assert_eq!(value_at(&map.values, map.size, Pos2::ZERO), Some(1000));
    assert_eq!(
        sample_index(0, 1024, 4097),
        2,
        "texture samples a different stored point"
    );
    let all = distribution(
        &map.values,
        map.size,
        Rect::from_min_max(Pos2::ZERO, egui::pos2(1.0, 1.0)),
    );
    assert_eq!(all.observed, HISTOGRAM_SIDE as u32);
    assert_eq!(all.bins[0], HISTOGRAM_SIDE as u32);
}

#[test]
fn selecting_another_same_sized_run_cancels_old_delivery_and_starts_clean() {
    let directory = TestDirectory::new("balance-ownership");
    let a = directory.path().join("a");
    let b = directory.path().join("b");
    std::fs::create_dir(&a).unwrap();
    std::fs::create_dir(&b).unwrap();
    write_map(&a.join("confidence.tiff"), [2, 2], vec![1000; 4]);
    write_map(&b.join("confidence.tiff"), [2, 2], vec![0; 4]);
    let ctx = egui::Context::default();
    let mut lens = ObservationBalance::default();
    settle(&mut lens, &ctx, &a.join("result.tiff"), [2, 2]);
    assert!(lens.ready());
    assert!(
        !lens.enabled(),
        "a loaded map must not modify the final by default"
    );
    lens.set_enabled(true);
    assert!(lens.enabled());
    let (release, wait) = std::sync::mpsc::sync_channel(1);
    let stale = read(&a.join("confidence.tiff"), [2, 2]).unwrap();
    let old_key = lens.key.clone().unwrap();
    let obsolete = Arc::new(AtomicBool::new(false));
    lens.pending = Some(Pending {
        key: old_key,
        obsolete: Arc::clone(&obsolete),
        task: jobs::spawn_task("balance-stale-fixture", move |_| {
            wait.recv_timeout(Duration::from_secs(3)).unwrap();
            Ok(stale)
        }),
    });
    lens.update(&ctx, Some(&b.join("result.tiff")), Some([2, 2]));
    assert!(obsolete.load(Ordering::Relaxed));
    assert!(!lens.ready());
    assert!(!lens.enabled());
    assert_eq!(
        lens.pending.as_ref().unwrap().key.output,
        a.join("result.tiff"),
        "retain the old worker until it retires; never fan out decoders"
    );
    release.send(()).unwrap();
    settle(&mut lens, &ctx, &b.join("result.tiff"), [2, 2]);
    assert!(lens.ready());
    assert_eq!(
        lens.loaded.as_ref().unwrap().values,
        [0; 4],
        "same dimensions do not authorize stale run A"
    );
    assert_eq!(lens.reading_at(egui::pos2(0.5, 0.5)), Some(0));
    assert!(!lens.enabled());
    lens.set_enabled(true);
    lens.update(&ctx, Some(&b.join("result.tiff")), None);
    assert!(
        !lens.ready(),
        "an absent coordinate certificate clears the lens"
    );
    assert!(!lens.enabled());
}

#[test]
fn compact_control_stays_inside_caption_at_high_dpi_and_hidden_lens_paints_no_image() {
    let directory = TestDirectory::new("balance-layout");
    write_map(
        &directory.path().join("confidence.tiff"),
        [2, 2],
        vec![0, 500, 1000, MISSING],
    );
    for dpi in [1.0, 1.5, 2.0] {
        let ctx = egui::Context::default();
        ctx.set_pixels_per_point(dpi);
        let mut lens = ObservationBalance::default();
        settle(
            &mut lens,
            &ctx,
            &directory.path().join("result.tiff"),
            [2, 2],
        );
        let caption = Rect::from_min_size(egui::pos2(20.0, 20.0), egui::vec2(120.0, 24.0));
        let image = Rect::from_min_size(egui::pos2(20.0, 60.0), egui::vec2(200.0, 200.0));
        let aperture = Rect::from_min_max(Pos2::ZERO, egui::pos2(0.5, 1.0));
        let output = ctx.run(egui::RawInput::default(), |ctx| {
            egui::CentralPanel::default().show(ctx, |ui| {
                lens.paint(ui.painter(), image, aperture, egui::pos2(0.25, 0.25));
                lens.control(ui, caption);
            });
        });
        let mut labels = 0;
        for shape in &output.shapes {
            if let egui::epaint::Shape::Text(text) = &shape.shape
                && text.galley.text() == "Confidence"
            {
                labels += 1;
                assert!(caption.contains_rect(text.galley.rect.translate(text.pos.to_vec2())));
            }
            if let egui::epaint::Shape::Mesh(mesh) = &shape.shape {
                assert_ne!(
                    mesh.texture_id,
                    lens.loaded.as_ref().unwrap().texture.id(),
                    "disabled lens must not paint its image"
                );
            }
        }
        assert_eq!(labels, 1, "the compact label must be visible");
        assert_eq!(lens.at_pin, Some(0));
        assert_eq!(lens.distribution.observed, 2);
        lens.set_enabled(true);
        let output = ctx.run(egui::RawInput::default(), |ctx| {
            egui::CentralPanel::default().show(ctx, |ui| {
                lens.paint(ui.painter(), image, aperture, egui::pos2(0.25, 0.25));
            });
        });
        let meshes: Vec<_> = output
            .shapes
            .iter()
            .filter_map(|shape| {
                if let egui::epaint::Shape::Mesh(mesh) = &shape.shape {
                    (mesh.texture_id == lens.loaded.as_ref().unwrap().texture.id()).then_some(mesh)
                } else {
                    None
                }
            })
            .collect();
        assert_eq!(meshes.len(), 1);
        assert_eq!(
            lens.loaded.as_ref().unwrap().window,
            PixelWindow {
                min: [0, 0],
                max: [1, 2]
            }
        );
        let texture_uv = Rect::from_min_max(Pos2::ZERO, egui::pos2(1.0, 1.0));
        for vertex in &meshes[0].vertices {
            assert!(image.contains(vertex.pos));
            assert!(
                texture_uv.contains(vertex.uv),
                "the exact left-half pixel window fills its refined texture"
            );
        }
    }
}

#[test]
fn zoom_refinement_reveals_actual_pixels_and_preserves_partial_edge_mapping() {
    let size = [4097, 3];
    let mut values = vec![0; size[0] * size[1]];
    values[0] = 1000;
    values[size[0] + 1] = MISSING;
    let aperture = Rect::from_min_max(
        egui::pos2(0.25 / 4097.0, 0.1),
        egui::pos2(3.75 / 4097.0, 0.9),
    );
    let window = PixelWindow::enclosing(size, aperture);
    assert_eq!(
        window,
        PixelWindow {
            min: [0, 0],
            max: [4, 3]
        }
    );
    let image = texture_for(&values, size, window);
    assert_eq!(image.size, [4, 3]);
    assert_eq!(
        image.pixels.len(),
        12,
        "zoom reads only visible actual map pixels"
    );
    assert_ne!(
        image.pixels[0], image.pixels[1],
        "initial full-map sampling missed this pixel; zoom must reveal it"
    );
    assert_eq!(image.pixels[5], Color32::TRANSPARENT);
    let uv = window.uv(size, aperture);
    assert!((uv.min.x - 0.0625).abs() < 0.0001);
    assert!((uv.max.x - 0.9375).abs() < 0.0001);
    assert!((uv.min.y - 0.1).abs() < 0.0001);
    assert!((uv.max.y - 0.9).abs() < 0.0001);
    let moved = Rect::from_min_max(
        egui::pos2(0.3 / 4097.0, 0.12),
        egui::pos2(3.8 / 4097.0, 0.92),
    );
    assert_eq!(
        PixelWindow::enclosing(size, moved),
        window,
        "subpixel pan must reuse cached texture"
    );
    assert_ne!(
        window.uv(size, moved),
        uv,
        "cached texture still follows subpixel motion"
    );
    assert_eq!(sampled_size([8192, 4096], TEXTURE_SIDE), [1024, 512]);
}

#[test]
fn completed_publication_requests_a_new_paint_after_the_worker_wakeup_has_been_consumed() {
    let ctx = egui::Context::default();
    let idle_frame = |time| egui::RawInput {
        time: Some(time),
        ..Default::default()
    };
    let mut baseline = Duration::ZERO;
    for frame in 0..12 {
        baseline = ctx
            .run(idle_frame(frame as f64 * 0.1), |_| {})
            .viewport_output[&egui::ViewportId::ROOT]
            .repaint_delay;
    }
    assert!(
        baseline > Duration::ZERO,
        "idle negative control must have no immediate repaint outstanding"
    );

    let key = Key {
        output: PathBuf::from("owned-run/result.tiff"),
        size: [2, 1],
    };
    let mut lens = ObservationBalance {
        key: Some(key.clone()),
        attempted: true,
        pending: Some(Pending {
            key,
            obsolete: Arc::new(AtomicBool::new(false)),
            // Deliberately no worker repaint: its earlier wake-up has already
            // been consumed by the renderer before the message arrives.
            task: jobs::spawn_task("balance-publication-fixture", |_| {
                Ok(Decoded {
                    size: [2, 1],
                    values: vec![0, 1000],
                    image: ColorImage::filled([2, 1], Color32::GRAY),
                })
            }),
        }),
        ..Default::default()
    };
    let deadline = std::time::Instant::now() + Duration::from_secs(3);
    let mut frame = 20;
    loop {
        let mut not_ready_before_publication = false;
        let output = ctx.run(idle_frame(frame as f64 * 0.1), |ctx| {
            // Matches ProcessSpace: its visible photograph/control pass has
            // already read the old state before the final delivery poll.
            not_ready_before_publication = !lens.ready();
            lens.poll(ctx);
        });
        if lens.ready() {
            assert!(
                not_ready_before_publication,
                "this must be the first publication frame"
            );
            assert!(
                lens.pending.is_none(),
                "no pending-work timer remains to rescue this state"
            );
            assert_eq!(
                output.viewport_output[&egui::ViewportId::ROOT].repaint_delay,
                Duration::ZERO,
                "installing the map after paint must request the next visible frame itself"
            );
            break;
        }
        assert!(std::time::Instant::now() < deadline);
        std::thread::sleep(Duration::from_millis(2));
        frame += 1;
    }
}
#[test]
fn missing_confidence_stays_visible_in_the_preview_control_without_inventing_a_map() {
    let ctx = egui::Context::default();
    let mut lens = ObservationBalance::default();
    let output = ctx.run(egui::RawInput::default(), |ctx| {
        egui::CentralPanel::default().show(ctx, |ui| {
            assert!(!lens.control(ui, Rect::from_min_size(Pos2::ZERO, egui::vec2(158.0, 24.0))));
        });
    });
    assert!(!lens.ready() && !lens.enabled());
    assert!(output.shapes.iter().any(|s| matches!(&s.shape,
        egui::Shape::Text(text) if text.galley.text().contains("Confidence") && text.galley.text().contains("unavailable"))));
}
