use super::*;
use std::sync::Arc;

#[path = "process-contribution-v24-tests.rs"]
mod v24_tests;

#[test]
fn lenses_paint_the_exact_shared_scene_or_local_aperture_and_report_pointer_anchored_zoom_once() {
    let ctx = egui::Context::default();
    let background = base(&ctx);
    let gate = packet(DiagnosticKind::GateSupport, 1);
    let fallback = packet(DiagnosticKind::Averaging, 2);
    let mut lenses = ContributionLenses::default();
    let mut data = Context {
        base: Some(&background),
        base_folded: 7,
        admitted: Some(&gate),
        fallback: Some(&fallback),
        level: 2,
        pin: egui::pos2(0.7, 0.3),
        aperture: Rect::from_min_max(Pos2::ZERO, egui::pos2(1.0, 1.0)),
        extent: None,
    };
    for (index, aperture) in [
        data.aperture,
        Rect::from_min_max(egui::pos2(0.625, 0.25), egui::pos2(0.75, 0.375)),
    ]
    .into_iter()
    .enumerate()
    {
        data.aperture = aperture;
        let (_, output) = draw(&mut lenses, &ctx, data, index as f64 * 0.1, vec![]);
        let meshes: Vec<_> = output
            .shapes
            .iter()
            .filter_map(|shape| match &shape.shape {
                egui::Shape::Mesh(mesh) if mesh.texture_id == background.id() => Some(mesh),
                _ => None,
            })
            .collect();
        assert_eq!(meshes.len(), 2);
        for mesh in meshes {
            let uv = Rect::from_points(
                &mesh
                    .vertices
                    .iter()
                    .map(|vertex| vertex.uv)
                    .collect::<Vec<_>>(),
            );
            assert_eq!(
                uv, aperture,
                "both photos must use the exact supplied snapshot; observations are sparse glyphs"
            );
        }
    }
    let (_, output) = draw(&mut lenses, &ctx, data, 0.2, vec![]);
    let destination = images(&output, background.id())[1];
    let anchor = egui::pos2(0.3, 0.65);
    let point = destination.min + destination.size() * anchor.to_vec2();
    let (response, _) = draw(
        &mut lenses,
        &ctx,
        data,
        0.3,
        vec![egui::Event::PointerMoved(point), egui::Event::Zoom(1.4)],
    );
    assert_eq!(response.zoom_factor, 1.4);
    assert!(response.zoom_anchor.unwrap().distance(anchor) < 0.0001);
    assert!(response.pin.is_none());
    let (still, _) = draw(&mut lenses, &ctx, data, 0.4, vec![]);
    assert_eq!(still.zoom_factor, 1.0);
    assert!(still.zoom_anchor.is_none());
}

#[test]
fn lens_grab_uses_all_press_motion_with_natural_direction_and_release_does_not_click() {
    let ctx = egui::Context::default();
    let background = base(&ctx);
    let gate = packet(DiagnosticKind::GateSupport, 1);
    let mut lenses = ContributionLenses::default();
    let mut data = Context {
        base: Some(&background),
        base_folded: 7,
        admitted: Some(&gate),
        fallback: None,
        level: 2,
        pin: egui::pos2(0.5, 0.5),
        aperture: sample_window(egui::pos2(0.5, 0.5)),
        extent: None,
    };
    let (_, initial) = draw(&mut lenses, &ctx, data, 0.0, vec![]);
    let destination = images(&initial, background.id())[0];
    let start = destination.center();
    let button = |point, pressed| egui::Event::PointerButton {
        pos: point,
        button: egui::PointerButton::Primary,
        pressed,
        modifiers: egui::Modifiers::NONE,
    };
    let _ = draw(
        &mut lenses,
        &ctx,
        data,
        0.1,
        vec![egui::Event::PointerMoved(start), button(start, true)],
    );
    let mut moved = false;
    for (index, delta) in [3.0, 6.0, 9.0].into_iter().enumerate() {
        let (response, _) = draw(
            &mut lenses,
            &ctx,
            data,
            0.2 + index as f64 * 0.1,
            vec![egui::Event::PointerMoved(start + egui::vec2(delta, 0.0))],
        );
        if let Some(pin) = response.pin {
            assert!(response.dragging);
            data.pin = pin;
            data.aperture = sample_window(pin);
            moved = true;
        }
    }
    assert!(moved);
    assert!((data.pin.x - (0.5 - 9.0 / destination.width() * 0.25)).abs() < 0.0001);
    let (stationary, _) = draw(&mut lenses, &ctx, data, 0.6, vec![]);
    assert!(stationary.pin.is_none());
    let (released, _) = draw(
        &mut lenses,
        &ctx,
        data,
        0.7,
        vec![button(start + egui::vec2(9.0, 0.0), false)],
    );
    assert!(
        released.pin.is_none(),
        "drag release cannot repin at its pointer location"
    );
}

fn packet(kind: DiagnosticKind, sequence: u64) -> DiagnosticSurface {
    DiagnosticSurface {
        sequence,
        frame: 6,
        level: 2,
        kind,
        scope: if kind == DiagnosticKind::GateSupport {
            DiagnosticScope::Frame
        } else {
            DiagnosticScope::Stack
        },
        scale: DiagnosticScale::Linear,
        width: 4,
        height: 2,
        min: 0.0,
        max: 1.0,
        pixels: Arc::from([0, 255, 0, 255, 255, 0, 255, 0]),
        folded: if kind == DiagnosticKind::GateSupport {
            1
        } else {
            7
        },
    }
}
fn draw(
    lenses: &mut ContributionLenses,
    ctx: &egui::Context,
    data: Context<'_>,
    time: f64,
    events: Vec<egui::Event>,
) -> (Response, egui::FullOutput) {
    let mut response = Response::default();
    let result = ctx.run(
        egui::RawInput {
            screen_rect: Some(Rect::from_min_size(Pos2::ZERO, egui::vec2(350.0, 80.0))),
            time: Some(time),
            events,
            ..Default::default()
        },
        |ctx| {
            egui::CentralPanel::default()
                .frame(egui::Frame::NONE)
                .show(ctx, |ui| {
                    response = lenses.show(ui, ui.max_rect(), data);
                });
        },
    );
    (response, result)
}
fn base(ctx: &egui::Context) -> TextureHandle {
    ctx.load_texture(
        "aligned-green",
        egui::ColorImage::new([12, 8], vec![Color32::GRAY; 96]),
        egui::TextureOptions::LINEAR,
    )
}
fn images(output: &egui::FullOutput, id: egui::TextureId) -> Vec<Rect> {
    output
        .shapes
        .iter()
        .filter_map(|shape| match &shape.shape {
            egui::Shape::Mesh(mesh) if mesh.texture_id == id => Some(Rect::from_points(
                &mesh
                    .vertices
                    .iter()
                    .map(|vertex| vertex.pos)
                    .collect::<Vec<_>>(),
            )),
            _ => None,
        })
        .collect()
}

fn glyph_markers(output: &egui::FullOutput, color: Color32) -> Vec<Pos2> {
    let mut points = Vec::new();
    for shape in &output.shapes {
        let egui::Shape::Mesh(mesh) = &shape.shape else {
            continue;
        };
        if mesh.texture_id != egui::TextureId::default() {
            continue;
        }
        let mut uses = vec![0usize; mesh.vertices.len()];
        for &index in &mesh.indices {
            uses[index as usize] += 1;
        }
        for (vertex, uses) in mesh.vertices.iter().zip(uses) {
            if uses == 8
                && vertex.color == color.gamma_multiply(0.88)
                && shape.clip_rect.contains(vertex.pos)
            {
                points.push(vertex.pos);
            }
        }
    }
    points
}

#[test]
fn spatial_mask_marks_only_real_positive_samples_and_rejects_wrong_scope() {
    let mut gate = packet(DiagnosticKind::GateSupport, 1);
    let glyphs = mask_glyphs(&gate, Some([900, 600]));
    assert_eq!(glyphs.len(), 4);
    let geometry = SampleGeometry::new(
        2,
        AdmissionMeta {
            sequence: 1,
            samples: [4, 2],
            extent: [900, 600],
        },
    )
    .unwrap();
    assert!(!glyphs.contains(&geometry.at(0).unwrap()));
    assert!(glyphs.contains(&geometry.at(1).unwrap()));
    assert!(
        mask_glyphs(&gate, None).is_empty(),
        "unknown image dimensions cannot establish sample footprints"
    );
    assert!(valid_mask(&gate, DiagnosticKind::GateSupport, 2));
    gate.scope = DiagnosticScope::Stack;
    assert!(!valid_mask(&gate, DiagnosticKind::GateSupport, 2));
    gate.scope = DiagnosticScope::Frame;
    gate.scale = DiagnosticScale::Log;
    assert!(!valid_mask(&gate, DiagnosticKind::GateSupport, 2));
    gate.scale = DiagnosticScale::Linear;
    assert!(!valid_mask(&gate, DiagnosticKind::GateSupport, 3));
}

#[test]
fn dense_observations_reach_contribution_lenses_without_becoming_owned_cells() {
    let mut gate = packet(DiagnosticKind::GateSupport, 1);
    gate.width = 128;
    gate.height = 96;
    let mut pixels = vec![0; 128 * 96];
    let index = 95 * 128 + 127;
    pixels[index] = 255;
    gate.pixels = pixels.into();
    assert!(valid_mask(&gate, DiagnosticKind::GateSupport, 2));
    let glyphs = mask_glyphs(&gate, Some([3516, 2344]));
    assert_eq!(
        glyphs.len(),
        1,
        "the far-edge observation must survive the old grid limit"
    );
    let expected = egui::pos2(3500.5 / 3516.0, 2328.5 / 2344.0);
    assert!(glyphs[0].center.distance(expected) < 0.00001);
    assert!((glyphs[0].cell.width() - 4.0 / 3516.0).abs() < 0.00001);
    gate.width = 129;
    assert!(!valid_mask(&gate, DiagnosticKind::GateSupport, 2));
}

#[test]
fn contribution_samples_project_exact_spacing_and_do_not_create_full_mask_textures() {
    let ctx = egui::Context::default();
    let background = base(&ctx);
    let mut lenses = ContributionLenses::default();
    let gate = packet(DiagnosticKind::GateSupport, 1);
    let (_, output) = draw(
        &mut lenses,
        &ctx,
        Context {
            base: Some(&background),
            base_folded: 7,
            admitted: Some(&gate),
            fallback: None,
            level: 2,
            pin: egui::pos2(0.5, 0.5),
            aperture: Rect::from_min_max(Pos2::ZERO, egui::pos2(1.0, 1.0)),
            extent: Some(egui::vec2(900.0, 600.0)),
        },
        0.0,
        vec![],
    );
    let photograph = images(&output, background.id())[0];
    let dots = glyph_markers(&output, GREEN);
    assert_eq!(
        dots.len(),
        4,
        "all four observed positive samples must be visible"
    );
    let actual = photograph.min + photograph.size() * egui::vec2(336.5 / 900.0, 148.5 / 600.0);
    assert!(dots.iter().any(|point| point.distance(actual) < 0.001));
    assert!(
        lenses.masks[0]
            .as_ref()
            .unwrap()
            .glyphs
            .iter()
            .all(|glyph| glyph.cell.width() < 0.005),
        "the4px coefficient spacing must not become a225px telemetry rectangle"
    );
    assert!(
        !output
            .textures_delta
            .set
            .iter()
            .any(|(_, delta)| delta.image.size() == [4, 2]),
        "the spatial evidence cannot be painted through a nearest-neighbour full-frame mask"
    );
}

#[test]
fn masks_need_actual_aligned_photo_context_and_keep_registration_during_reveal() {
    let ctx = egui::Context::default();
    let mut lenses = ContributionLenses::default();
    let first = packet(DiagnosticKind::GateSupport, 1);
    let fallback = packet(DiagnosticKind::Averaging, 2);
    let background = base(&ctx);
    let mut data = Context {
        base: None,
        base_folded: 7,
        admitted: Some(&first),
        fallback: Some(&fallback),
        level: 2,
        pin: egui::pos2(0.375, 0.25),
        aperture: sample_window(egui::pos2(0.375, 0.25)),
        extent: Some(egui::vec2(900.0, 600.0)),
    };
    let (_, waiting) = draw(&mut lenses, &ctx, data, 0.0, vec![]);
    assert!(images(&waiting, background.id()).is_empty());
    assert_eq!(
        glyph_markers(&waiting, GREEN).len(),
        0,
        "without a registered preview, an original camera image must never receive these masks"
    );
    data.base = Some(&background);
    let (_, initial) = draw(&mut lenses, &ctx, data, 0.1, vec![]);
    let frames = images(&initial, background.id());
    assert_eq!(frames.len(), 2);
    assert!(!frames[0].intersects(frames[1]));
    let marks = glyph_markers(&initial, GREEN);
    assert!(
        !marks.is_empty(),
        "fixture must inspect a real positive sample"
    );
    assert!(marks.iter().all(|&point| frames[0].contains(point)));
    let mut changed = packet(DiagnosticKind::GateSupport, 3);
    changed.pixels = Arc::from([255, 0, 255, 0, 0, 255, 0, 255]);
    data.admitted = Some(&changed);
    let (_, reveal) = draw(&mut lenses, &ctx, data, 0.2, vec![]);
    let current = lenses.masks[0].as_ref().unwrap();
    assert!(current.previous.is_some());
    assert!(
        glyph_markers(&reveal, GREEN)
            .iter()
            .all(|&point| frames[0].contains(point))
    );
    assert_eq!(images(&reveal, background.id()), frames);
    let _ = draw(&mut lenses, &ctx, data, 0.5, vec![]);
    assert!(!lenses.transitioning());
}

#[test]
fn clicking_a_photographic_contribution_returns_the_same_normalized_matrix_pin() {
    let ctx = egui::Context::default();
    let mut lenses = ContributionLenses::default();
    let background = base(&ctx);
    let gate = packet(DiagnosticKind::GateSupport, 1);
    let data = Context {
        base: Some(&background),
        base_folded: 7,
        admitted: Some(&gate),
        fallback: None,
        level: 2,
        pin: egui::pos2(0.5, 0.5),
        aperture: sample_window(egui::pos2(0.5, 0.5)),
        extent: None,
    };
    let (_, initial) = draw(&mut lenses, &ctx, data, 0.0, vec![]);
    let frame = images(&initial, background.id())[0];
    let point = frame.min + frame.size() * egui::vec2(0.25, 0.75);
    let event = |pressed| egui::Event::PointerButton {
        pos: point,
        button: egui::PointerButton::Primary,
        pressed,
        modifiers: egui::Modifiers::NONE,
    };
    let _ = draw(
        &mut lenses,
        &ctx,
        data,
        0.1,
        vec![egui::Event::PointerMoved(point), event(true)],
    );
    let (response, _) = draw(&mut lenses, &ctx, data, 0.12, vec![event(false)]);
    let pin = response
        .pin
        .expect("an actual photograph click must reach the matrix inspection point");
    assert!((pin.x - 0.4375).abs() < 0.001 && (pin.y - 0.5625).abs() < 0.001);
}

#[test]
fn crop_aperture_is_fixed_at_edges_and_matches_photo_and_mask_uvs() {
    assert_eq!(
        sample_window(egui::pos2(0.0, 1.0)),
        Rect::from_min_max(egui::pos2(0.0, 0.75), egui::pos2(0.25, 1.0))
    );
    let ctx = egui::Context::default();
    let mut lenses = ContributionLenses::default();
    let background = base(&ctx);
    let gate = packet(DiagnosticKind::GateSupport, 1);
    let (_, output) = draw(
        &mut lenses,
        &ctx,
        Context {
            base: Some(&background),
            base_folded: 7,
            admitted: Some(&gate),
            fallback: None,
            level: 2,
            pin: egui::pos2(0.0, 1.0),
            aperture: sample_window(egui::pos2(0.0, 1.0)),
            extent: None,
        },
        0.0,
        vec![],
    );
    let uvs: Vec<_> = output
        .shapes
        .iter()
        .filter_map(|shape| match &shape.shape {
            egui::Shape::Mesh(mesh) if mesh.texture_id == background.id() => Some(
                Rect::from_points(&mesh.vertices.iter().map(|v| v.uv).collect::<Vec<_>>()),
            ),
            _ => None,
        })
        .collect();
    assert_eq!(
        uvs,
        vec![Rect::from_min_max(egui::pos2(0.0, 0.75), egui::pos2(0.25, 1.0)); 1]
    );
}

#[test]
fn rapid_photo_updates_reveal_retained_pixels_and_keep_pending_generation_without_more_input() {
    let ctx = egui::Context::default();
    let mut lenses = ContributionLenses::default();
    let photos: [TextureHandle; 3] = std::array::from_fn(|index| {
        ctx.load_texture(
            format!("contribution-photo-{index}"),
            egui::ColorImage::new([12, 8], vec![Color32::from_gray(40 + index as u8 * 80); 96]),
            egui::TextureOptions::LINEAR,
        )
    });
    let gate = packet(DiagnosticKind::GateSupport, 1);
    let mut data = Context {
        base: Some(&photos[0]),
        base_folded: 7,
        admitted: Some(&gate),
        fallback: None,
        level: 2,
        pin: egui::pos2(0.5, 0.5),
        aperture: sample_window(egui::pos2(0.5, 0.5)),
        extent: Some(egui::vec2(900.0, 500.0)),
    };
    let (_, initial) = draw(&mut lenses, &ctx, data, 0.0, vec![]);
    let rect = images(&initial, photos[0].id())[0];
    assert!(
        (rect.aspect_ratio() - 1.8).abs() < 0.001,
        "use the actual cropped working domain"
    );
    data.base = Some(&photos[1]);
    data.base_folded = 8;
    let (_, next) = draw(&mut lenses, &ctx, data, 0.1, vec![]);
    assert_eq!(images(&next, photos[0].id()), vec![rect]);
    assert_eq!(images(&next, photos[1].id()), vec![rect]);
    assert_eq!(
        lenses.photo.as_ref().unwrap().alpha,
        0.0,
        "new photo must start transparent over retained real pixels"
    );
    data.base = Some(&photos[2]);
    data.base_folded = 9;
    let (_, early) = draw(&mut lenses, &ctx, data, 0.2, vec![]);
    assert!(
        images(&early, photos[2].id()).is_empty(),
        "a newer context must not pop over an active reveal"
    );
    let photo = lenses.photo.as_ref().unwrap();
    assert!(photo.alpha > 0.0 && photo.alpha < 1.0);
    assert_eq!(photo.folded, 8);
    assert_eq!(photo.pending.as_ref().unwrap().1, 9);
    data.base = None;
    for time in [0.3, 0.31, 0.6] {
        let _ = draw(&mut lenses, &ctx, data, time, vec![]);
    }
    let photo = lenses.photo.as_ref().unwrap();
    assert_eq!(photo.current.id(), photos[2].id());
    assert_eq!(photo.folded, 9);
    assert!(photo.pending.is_none() && photo.previous.is_none());
    assert!(!lenses.transitioning());
}

#[test]
fn double_clicking_a_contribution_lens_requests_shared_fit_without_repinning() {
    let ctx = egui::Context::default();
    let background = base(&ctx);
    let gate = packet(DiagnosticKind::GateSupport, 1);
    let mut lenses = ContributionLenses::default();
    let data = Context {
        base: Some(&background),
        base_folded: 7,
        admitted: Some(&gate),
        fallback: None,
        level: 2,
        pin: egui::pos2(0.6, 0.4),
        aperture: sample_window(egui::pos2(0.6, 0.4)),
        extent: None,
    };
    let (_, initial) = draw(&mut lenses, &ctx, data, 0.0, vec![]);
    let target = images(&initial, background.id())[0].center();
    let mut saw_reset = false;
    for (time, pressed) in [(0.1, true), (0.12, false), (0.2, true), (0.22, false)] {
        let (response, _) = draw(
            &mut lenses,
            &ctx,
            data,
            time,
            vec![
                egui::Event::PointerMoved(target),
                egui::Event::PointerButton {
                    pos: target,
                    button: egui::PointerButton::Primary,
                    pressed,
                    modifiers: egui::Modifiers::NONE,
                },
            ],
        );
        if response.reset {
            saw_reset = true;
            assert!(response.pin.is_none());
            assert_eq!(response.zoom_factor, 1.0);
        }
    }
    assert!(
        saw_reset,
        "actual lens double click must provide a local way back to the whole scene"
    );
}

#[path = "process-contribution-v26-tests.rs"]
mod v26_tests;
