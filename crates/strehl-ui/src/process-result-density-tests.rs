//! Independent density witnesses: paint policy may thin actual observations,
//! but retention and zoom must never substitute a sparse permanently decimated set.
use super::*;
use crate::pipeline::{DiagnosticKind, DiagnosticScale, DiagnosticScope, DiagnosticSurface};

fn archive() -> AdmissionArchive {
    let mut archive = AdmissionArchive::default();
    for (level, size) in [(0, [64, 48]), (1, [128, 96])] {
        archive.ingest(
            &DiagnosticSurface {
                sequence: level as u64 + 1,
                frame: 0,
                level,
                kind: DiagnosticKind::GateSupport,
                scope: DiagnosticScope::Frame,
                scale: DiagnosticScale::Linear,
                width: size[0],
                height: size[1],
                min: 0.0,
                max: 1.0,
                pixels: vec![255; size[0] * size[1]].into(),
                folded: 1,
            },
            [2048, 1536],
        );
    }
    archive
}
fn photo_rect() -> Rect {
    Rect::from_min_size(egui::pos2(20.0, 20.0), egui::vec2(800.0, 600.0))
}
fn texture(ctx: &egui::Context) -> TextureHandle {
    ctx.load_texture(
        "density-final-photo",
        egui::ColorImage::filled([80, 60], Color32::GRAY),
        egui::TextureOptions::NEAREST,
    )
}
fn paint(
    field: &mut ResultPhoto,
    ctx: &egui::Context,
    texture: &TextureHandle,
    archive: &AdmissionArchive,
    aperture: Rect,
    density: sample_glyphs::Density,
) -> egui::FullOutput {
    density.write(ctx);
    OverlayMode::Scales.write(ctx);
    ctx.run(
        egui::RawInput {
            screen_rect: Some(Rect::from_min_size(Pos2::ZERO, egui::vec2(900.0, 690.0))),
            ..Default::default()
        },
        |ctx| {
            egui::CentralPanel::default()
                .frame(egui::Frame::NONE)
                .show(ctx, |ui| {
                    field.show(
                        ui,
                        photo_rect(),
                        Context {
                            texture,
                            extent: egui::vec2(2048.0, 1536.0),
                            aperture,
                            pin: aperture.center(),
                            archive,
                            level: 1,
                            frame: Some(0),
                            spans: &[],
                            linked_hover: false,
                        },
                    );
                });
        },
    )
}
fn points(output: &egui::FullOutput) -> Vec<Pos2> {
    overlay_marker_centers(output)
        .into_iter()
        .filter(|point| photo_rect().contains(*point))
        .collect()
}

#[test]
fn old_and_dense_packets_retain_every_positive_observation_independent_of_display_density() {
    let ctx = egui::Context::default();
    let texture = texture(&ctx);
    let archive = archive();
    let mut field = ResultPhoto::default();
    let quiet = paint(
        &mut field,
        &ctx,
        &texture,
        &archive,
        full(),
        sample_glyphs::Density::Quiet,
    );
    assert_eq!(
        field.samples.iter().filter(|s| s.level == 0).count(),
        64 * 48
    );
    assert_eq!(
        field.samples.iter().filter(|s| s.level == 1).count(),
        128 * 96
    );
    let retained = field.samples.as_ptr();
    let balanced = paint(
        &mut field,
        &ctx,
        &texture,
        &archive,
        full(),
        sample_glyphs::Density::Balanced,
    );
    let all = paint(
        &mut field,
        &ctx,
        &texture,
        &archive,
        full(),
        sample_glyphs::Density::Full,
    );
    assert_eq!(
        field.samples.as_ptr(),
        retained,
        "display policy must not rebuild or discard retained observations"
    );
    assert_eq!(points(&quiet).len(), 1024 + 96);
    assert_eq!(points(&balanced).len(), 6144 + 384);
    assert_eq!(points(&all).len(), 128 * 96 + 64 * 48);
    let first = field.samples.iter().find(|s| s.level == 1).unwrap();
    assert!((first.glyph.center.x - 8.5 / 2048.0).abs() < 1e-6);
    assert!((first.glyph.center.y - 8.5 / 1536.0).abs() < 1e-6);
    assert_eq!(
        archive.metadata(0, 0).unwrap().samples,
        [64, 48],
        "older packets retain their literal grid"
    );
    assert_eq!(archive.metadata(1, 0).unwrap().samples, [128, 96]);
}

#[test]
fn zoom_exposes_a_real_retained_point_that_balanced_overview_thinned_out() {
    let ctx = egui::Context::default();
    let texture = texture(&ctx);
    let archive = archive();
    let mut field = ResultPhoto::default();
    let overview = paint(
        &mut field,
        &ctx,
        &texture,
        &archive,
        full(),
        sample_glyphs::Density::Balanced,
    );
    // The second recorded level1 coefficient is at(12,4) in its decimated
    // grid, hence(24.5,8.5) in analysis pixels. Balanced's whole-image stride2
    // omits it, while a crop must expose it from the retained measurements.
    let uv = egui::pos2(24.5 / 2048.0, 8.5 / 1536.0);
    let at = photo_rect().min + uv.to_vec2() * photo_rect().size();
    assert!(
        !points(&overview).iter().any(|p| p.distance(at) < 0.01),
        "fixture must target an actually thinned-out observation"
    );
    let retained = field.samples.as_ptr();
    let aperture = Rect::from_min_max(Pos2::ZERO, egui::pos2(0.25, 0.25));
    let zoom = paint(
        &mut field,
        &ctx,
        &texture,
        &archive,
        aperture,
        sample_glyphs::Density::Balanced,
    );
    let at = photo_rect().min + (uv - aperture.min) / aperture.size() * photo_rect().size();
    assert!(
        points(&zoom).iter().any(|p| p.distance(at) < 0.01),
        "crop-first thinning must reveal the same actual recorded point"
    );
    assert_eq!(
        field.samples.as_ptr(),
        retained,
        "panning/zooming uses retained data, not new telemetry or cache reconstruction"
    );
    assert_eq!(field.samples.len(), 128 * 96 + 64 * 48);
}

#[test]
fn density_key_stays_below_photograph_and_real_controls_share_state_across_panes() {
    let ctx = egui::Context::default();
    let texture = texture(&ctx);
    let archive = archive();
    let mut field = ResultPhoto::default();
    let photo = paint(
        &mut field,
        &ctx,
        &texture,
        &archive,
        full(),
        sample_glyphs::Density::Balanced,
    );
    assert!(
        !photo.shapes.iter().any(
            |shape| matches!(&shape.shape,egui::Shape::Text(text) if text.galley.text()=="Density")
        ),
        "photo rendering itself cannot insert the key over image pixels"
    );
    for width in [180.0, 320.0, 800.0] {
        let bounds = Rect::from_min_size(egui::pos2(20.0, 632.0), egui::vec2(width, 20.0));
        let mut paint_legend = |events| {
            ctx.run(
                egui::RawInput {
                    screen_rect: Some(Rect::from_min_size(Pos2::ZERO, egui::vec2(900.0, 690.0))),
                    events,
                    ..Default::default()
                },
                |ctx| {
                    egui::CentralPanel::default()
                        .frame(egui::Frame::NONE)
                        .show(ctx, |ui| {
                            field.legend(ui, bounds, egui::vec2(2048.0, 1536.0))
                        });
                },
            )
        };
        paint_legend(vec![]);
        let output = paint_legend(vec![]);
        let controls = output
            .shapes
            .iter()
            .filter(|shape| match &shape.shape {
                egui::Shape::Text(text) => text.galley.text() == "Density",
                _ => false,
            })
            .count();
        assert_eq!(controls, usize::from(width >= 270.0));
        assert!(
            output.shapes.iter().any(|shape| matches!(&shape.shape,
            egui::Shape::Text(text) if text.galley.text().starts_with("Confidence"))),
            "confidence remains discoverable even when density controls do not fit"
        );
        for shape in &output.shapes {
            if matches!(
                shape.shape,
                egui::Shape::Text(_) | egui::Shape::LineSegment { .. }
            ) {
                assert!(shape.clip_rect.top() >= bounds.top());
                assert!(!photo_rect().intersects(shape.clip_rect));
                assert!(
                    bounds.contains_rect(shape.shape.visual_bounding_rect()),
                    "legend marks must fit the actual reserved strip at width{width}"
                );
            }
        }
        if width < 270.0 {
            continue;
        }
        let all = egui::pos2(bounds.right() - 10.0, bounds.center().y);
        let button = |pressed| egui::Event::PointerButton {
            pos: all,
            button: egui::PointerButton::Primary,
            pressed,
            modifiers: egui::Modifiers::NONE,
        };
        paint_legend(vec![egui::Event::PointerMoved(all), button(true)]);
        paint_legend(vec![button(false)]);
        assert_eq!(
            sample_glyphs::Density::read(&ctx),
            sample_glyphs::Density::Full
        );
    }
}

#[test]
fn compact_legend_with_loaded_balance_and_many_bands_has_disjoint_visible_labels() {
    use crate::jobs::tests::TestDirectory;
    use std::time::{Duration, Instant};

    let directory = TestDirectory::new("balance-dense-legend");
    image::ImageBuffer::<image::Luma<u16>, Vec<u16>>::from_raw(
        4,
        4,
        vec![
            0,
            1000,
            500,
            u16::MAX,
            0,
            1000,
            500,
            500,
            0,
            1000,
            500,
            500,
            0,
            1000,
            500,
            500,
        ],
    )
    .unwrap()
    .save_with_format(
        directory.path().join("confidence.tiff"),
        image::ImageFormat::Tiff,
    )
    .unwrap();
    let result = directory.path().join("result.tiff");
    for dpi in [1.0, 1.5, 2.0] {
        let ctx = egui::Context::default();
        ctx.set_pixels_per_point(dpi);
        let mut field = ResultPhoto::default();
        let deadline = Instant::now() + Duration::from_secs(5);
        loop {
            field.update_balance(&ctx, Some(&result), Some([4, 4]));
            if field.balance.ready() {
                break;
            }
            assert!(
                Instant::now() < deadline,
                "real Gray16 balance map must load for this layout witness"
            );
            std::thread::sleep(Duration::from_millis(2));
        }
        assert_eq!(field.balance.reading_at(egui::pos2(0.01, 0.01)), Some(0));
        assert_eq!(field.balance.reading_at(egui::pos2(0.4, 0.01)), Some(1000));
        for bands in [8, 16] {
            // This is deliberately the legend's metadata path. No surrogate
            // point cloud or enormous image is needed to paint a band label.
            field.mask_key = Some(MaskKey {
                level: bands - 1,
                spans: Vec::new(),
                evidence: (0..bands)
                    .map(|level| {
                        (
                            level,
                            0,
                            AdmissionMeta {
                                sequence: level as u64 + 1,
                                samples: [1, 1],
                                extent: [4, 4],
                            },
                        )
                    })
                    .collect(),
            });
            field.legend_bands = field
                .mask_key
                .as_ref()
                .unwrap()
                .evidence
                .iter()
                .map(|&(level, _, meta)| (level, meta))
                .collect();
            for width in [300.0, 320.0] {
                let bounds = Rect::from_min_size(egui::pos2(20.0, 20.0), egui::vec2(width, 24.0));
                let output = ctx.run(
                    egui::RawInput {
                        screen_rect: Some(Rect::from_min_size(
                            Pos2::ZERO,
                            egui::vec2(800.0, 600.0),
                        )),
                        ..Default::default()
                    },
                    |ctx| {
                        egui::CentralPanel::default()
                            .frame(egui::Frame::NONE)
                            .show(ctx, |ui| {
                                field.legend(ui, bounds, egui::vec2(4.0, 4.0));
                            });
                    },
                );
                let labels: Vec<_> = output
                    .shapes
                    .iter()
                    .filter_map(|shape| {
                        let egui::Shape::Text(text) = &shape.shape else {
                            return None;
                        };
                        let visible = text.visual_bounding_rect().intersect(shape.clip_rect);
                        visible
                            .is_positive()
                            .then(|| (text.galley.text().to_owned(), visible))
                    })
                    .collect();
                for required in ["Confidence", "Density"] {
                    assert_eq!(
                        labels.iter().filter(|(text, _)| text == required).count(),
                        1,
                        "both competing controls must actually be painted: bands{bands}, width{width}, dpi{dpi}"
                    );
                }
                for (index, (label, area)) in labels.iter().enumerate() {
                    assert!(
                        bounds.expand(0.5).contains_rect(*area),
                        "{label} escaped its caption at bands{bands}, width{width}, dpi{dpi}"
                    );
                    for (other, other_area) in &labels[index + 1..] {
                        assert!(
                            !area.shrink(0.25).intersects(other_area.shrink(0.25)),
                            "{label} overlaps {other} at bands{bands}, width{width}, dpi{dpi}"
                        );
                    }
                }
                // Compact numeric labels may yield to color marks, but the
                // legend cannot pass this test by dropping every band entry.
                let band_marks = output.shapes.iter().filter(|shape| {
                    matches!(&shape.shape, egui::Shape::LineSegment { stroke, points }
                        if points[0].x >= bounds.left() + 60.0 && points[0].x < bounds.right() - 200.0
                            && (0..bands).any(|level| stroke.color == sample_glyphs::level_color(level)))
                }).count();
                assert!(
                    band_marks >= bands,
                    "every band retains a visible mark while its numeric label yields space"
                );
            }
        }
    }
}
