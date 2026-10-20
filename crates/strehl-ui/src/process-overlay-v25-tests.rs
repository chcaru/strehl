use super::*;
use crate::pipeline::{DiagnosticKind, DiagnosticScale, DiagnosticScope, DiagnosticSurface};

fn archive() -> AdmissionArchive {
    let mut archive = AdmissionArchive::default();
    for level in 0..3 {
        for frame in 0..2 {
            archive.ingest(
                &DiagnosticSurface {
                    sequence: (level * 2 + frame + 1) as u64,
                    frame,
                    level,
                    kind: DiagnosticKind::GateSupport,
                    scope: DiagnosticScope::Frame,
                    scale: DiagnosticScale::Linear,
                    width: 128,
                    height: 96,
                    min: 0.0,
                    max: 1.0,
                    pixels: (0..128 * 96)
                        .map(|i| {
                            if (i % 128 < 64) == (frame == 0) {
                                255
                            } else {
                                0
                            }
                        })
                        .collect::<Vec<_>>()
                        .into(),
                    folded: 1,
                },
                [4096, 3072],
            );
        }
    }
    archive
}
fn draw(
    ctx: &egui::Context,
    field: &mut ResultPhoto,
    archive: &AdmissionArchive,
    texture: &TextureHandle,
    frame: usize,
    aperture: Rect,
    pointer: Pos2,
) -> egui::FullOutput {
    ctx.run(
        egui::RawInput {
            screen_rect: Some(Rect::from_min_size(Pos2::ZERO, egui::vec2(1700.0, 1300.0))),
            events: vec![egui::Event::PointerMoved(pointer)],
            ..Default::default()
        },
        |ctx| {
            egui::CentralPanel::default()
                .frame(egui::Frame::NONE)
                .show(ctx, |ui| {
                    field.show(
                        ui,
                        Rect::from_min_size(egui::pos2(20.0, 20.0), egui::vec2(1600.0, 1200.0)),
                        Context {
                            texture,
                            extent: egui::vec2(4096.0, 3072.0),
                            aperture,
                            pin: aperture.center(),
                            archive,
                            level: 0,
                            frame: Some(frame),
                            spans: &[],
                            linked_hover: false,
                        },
                    );
                });
        },
    )
}
#[test]
fn default_marks_one_detail_size_and_retains_one_draw_across_pointer_motion() {
    let ctx = egui::Context::default();
    let texture = ctx.load_texture(
        "overlay-witness",
        egui::ColorImage::filled([4, 3], Color32::GRAY),
        egui::TextureOptions::LINEAR,
    );
    let archive = archive();
    let mut field = ResultPhoto::default();
    let first = draw(&ctx, &mut field, &archive, &texture, 0, full(), Pos2::ZERO);
    assert_eq!(field.samples.len(), 6144);
    assert!(field.samples.iter().all(|sample| sample.level == 0));
    assert_eq!(
        field.legend_bands.len(),
        3,
        "other measured sizes remain discoverable"
    );
    let markers = overlay_marker_centers(&first);
    assert_eq!(markers.len(), 6144);
    assert!(
        markers.iter().all(|at| at.x < 820.0),
        "negative observed half must stay clean"
    );
    let builds = field.overlay.builds;
    let retained = field.samples.as_ptr();
    for step in 0..100 {
        draw(
            &ctx,
            &mut field,
            &archive,
            &texture,
            0,
            full(),
            egui::pos2(30.0 + step as f32 * 6.0, 200.0),
        );
    }
    assert_eq!(
        field.overlay.builds, builds,
        "pointer-only motion must reuse the GPU mesh"
    );
    assert_eq!(field.samples.as_ptr(), retained);
    let next = draw(&ctx, &mut field, &archive, &texture, 1, full(), Pos2::ZERO);
    let markers = overlay_marker_centers(&next);
    assert_eq!(markers.len(), 6144);
    assert!(
        markers.iter().all(|at| at.x > 820.0),
        "changed source must replace real spatial evidence"
    );
    assert_eq!(field.overlay.builds, builds + 1);
    OverlayMode::Clean.write(&ctx);
    let clean = draw(&ctx, &mut field, &archive, &texture, 1, full(), Pos2::ZERO);
    assert!(overlay_marker_centers(&clean).is_empty());
    assert_eq!(field.legend_bands.len(), 3);
    OverlayMode::Scales.write(&ctx);
    draw(&ctx, &mut field, &archive, &texture, 1, full(), Pos2::ZERO);
    assert_eq!(field.samples.len(), 3 * 6144);
}

#[test]
fn retained_mesh_rebuilds_for_crop_density_and_new_evidence() {
    let ctx = egui::Context::default();
    let texture = ctx.load_texture(
        "overlay-invalidation",
        egui::ColorImage::filled([4, 3], Color32::GRAY),
        egui::TextureOptions::LINEAR,
    );
    let mut archive = archive();
    let mut field = ResultPhoto::default();
    draw(&ctx, &mut field, &archive, &texture, 0, full(), Pos2::ZERO);
    let crop = Rect::from_min_max(egui::pos2(0.1, 0.1), egui::pos2(0.3, 0.3));
    let output = draw(&ctx, &mut field, &archive, &texture, 0, crop, Pos2::ZERO);
    assert_eq!(field.overlay.builds, 2);
    assert!(!overlay_marker_centers(&output).is_empty());
    sample_glyphs::Density::Quiet.write(&ctx);
    draw(&ctx, &mut field, &archive, &texture, 0, crop, Pos2::ZERO);
    assert_eq!(field.overlay.builds, 3);
    archive.ingest(
        &DiagnosticSurface {
            sequence: 100,
            frame: 0,
            level: 0,
            kind: DiagnosticKind::GateSupport,
            scope: DiagnosticScope::Frame,
            scale: DiagnosticScale::Linear,
            width: 128,
            height: 96,
            min: 0.0,
            max: 1.0,
            pixels: vec![0; 128 * 96].into(),
            folded: 1,
        },
        [4096, 3072],
    );
    let output = draw(&ctx, &mut field, &archive, &texture, 0, crop, Pos2::ZERO);
    assert!(
        overlay_marker_centers(&output).is_empty(),
        "a newer negative packet must remove old positive marks"
    );
    assert_eq!(field.overlay.builds, 4);
}

#[test]
fn repaired_photo_keeps_current_confidence_and_navigation_without_old_admission() {
    let directory = crate::jobs::tests::TestDirectory::new("repaired-photo-confidence");
    let result = directory.path().join("result.tiff");
    image::ImageBuffer::<image::Luma<u16>, Vec<u16>>::from_raw(
        4,
        3,
        vec![0, 250, 500, 1000, 0, 250, 500, 1000, 0, 250, 500, 1000],
    )
    .unwrap()
    .save_with_format(
        result.with_file_name("confidence.tiff"),
        image::ImageFormat::Tiff,
    )
    .unwrap();
    let ctx = egui::Context::default();
    let texture = ctx.load_texture(
        "repaired-photograph",
        egui::ColorImage::filled([4, 3], Color32::GRAY),
        egui::TextureOptions::LINEAR,
    );
    let archive = archive();
    let mut field = ResultPhoto::default();
    let initial = draw(&ctx, &mut field, &archive, &texture, 0, full(), Pos2::ZERO);
    assert!(
        !overlay_marker_centers(&initial).is_empty(),
        "positive control: this archive paints admission marks"
    );
    let deadline = std::time::Instant::now() + std::time::Duration::from_secs(3);
    while !field.balance.ready() {
        field.update_balance(&ctx, Some(&result), Some([4, 3]));
        assert!(std::time::Instant::now() < deadline);
        std::thread::sleep(std::time::Duration::from_millis(2));
    }
    field.balance.set_enabled(true);
    field.suppress_diagnostics(true);
    let crop = Rect::from_min_max(egui::pos2(0.1, 0.1), egui::pos2(0.5, 0.5));
    let repaired = draw(&ctx, &mut field, &archive, &texture, 0, crop, Pos2::ZERO);
    assert!(overlay_marker_centers(&repaired).is_empty());
    assert!(
        field.probe_overview.is_some(),
        "repair must not hide the zoom navigator"
    );
    assert!(
        field.probe_region.is_none(),
        "old admission cannot become a repaired ownership probe"
    );
    let confidence_meshes: Vec<_> = repaired
        .shapes
        .iter()
        .filter_map(|shape| {
            let egui::Shape::Mesh(mesh) = &shape.shape else {
                return None;
            };
            (mesh.texture_id != texture.id() && mesh.texture_id != egui::TextureId::default())
                .then_some(mesh)
        })
        .collect();
    assert_eq!(
        confidence_meshes.len(),
        1,
        "post-repair confidence must still paint"
    );
    assert_eq!(field.balance.reading_at(egui::pos2(0.1, 0.5)), Some(0));
    assert_eq!(field.balance.reading_at(egui::pos2(0.9, 0.5)), Some(1000));

    // A same-size replacement photograph must clear old evidence before its
    // first paint, even though the next asynchronous update occurs afterward.
    field.invalidate_balance();
    assert!(!field.balance.ready());
    assert_eq!(field.balance.reading_at(egui::pos2(0.9, 0.5)), None);
    let replaced = draw(&ctx, &mut field, &archive, &texture, 0, crop, Pos2::ZERO);
    assert!(!replaced.shapes.iter().any(|shape| {
        matches!(&shape.shape, egui::Shape::Mesh(mesh)
            if mesh.texture_id != texture.id() && mesh.texture_id != egui::TextureId::default())
    }));
}

#[test]
#[ignore = "explicit CPU draw-preparation comparison; excludes GPU presentation"]
fn benchmark_retained_overlay_against_individual_sample_shapes() {
    let ctx = egui::Context::default();
    let texture = ctx.load_texture(
        "overlay-benchmark",
        egui::ColorImage::filled([4, 3], Color32::GRAY),
        egui::TextureOptions::LINEAR,
    );
    let archive = archive();
    let mut field = ResultPhoto::default();
    draw(&ctx, &mut field, &archive, &texture, 0, full(), Pos2::ZERO);
    let input = Context {
        texture: &texture,
        extent: egui::vec2(4096.0, 3072.0),
        aperture: full(),
        pin: egui::pos2(0.5, 0.5),
        archive: &archive,
        level: 0,
        frame: Some(0),
        spans: &[],
        linked_hover: false,
    };
    let rect = Rect::from_min_size(egui::pos2(20.0, 20.0), egui::vec2(1600.0, 1200.0));
    let mut samples = [Vec::new(), Vec::new()];
    for sweep in 0..6 {
        for mode in if sweep % 2 == 0 { [0, 1] } else { [1, 0] } {
            let started = std::time::Instant::now();
            let mut shape_count = 0;
            for _ in 0..80 {
                let output = ctx.run(
                    egui::RawInput {
                        screen_rect: Some(Rect::from_min_size(
                            Pos2::ZERO,
                            egui::vec2(1700.0, 1300.0),
                        )),
                        ..Default::default()
                    },
                    |ctx| {
                        let painter = ctx.layer_painter(egui::LayerId::background());
                        if mode == 0 {
                            for sample in &field.samples {
                                sample_glyphs::paint_glyph(
                                    &painter,
                                    rect,
                                    full(),
                                    sample.glyph,
                                    sample.colors[0],
                                    true,
                                );
                            }
                        } else {
                            field.paint_samples(&painter, rect, &input);
                        }
                    },
                );
                shape_count = output.shapes.len();
                std::hint::black_box(ctx.tessellate(output.shapes, output.pixels_per_point));
            }
            samples[mode].push(started.elapsed().as_secs_f64() * 1000.0 / 80.0);
            assert_eq!(shape_count, if mode == 0 { 6144 } else { 1 });
        }
    }
    println!("overlay_cpu_ms_per_frame {:?}", samples);
    println!(
        "overlay_cpu_min_ms individual={} retained={}",
        samples[0].iter().copied().fold(f64::INFINITY, f64::min),
        samples[1].iter().copied().fold(f64::INFINITY, f64::min)
    );
}
