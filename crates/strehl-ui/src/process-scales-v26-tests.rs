//! Exercise the real matrix map consumer with retained packets and pointer
//! events. New receipts, domain changes and faded generations are controls.
use super::*;
use crate::pipeline::{DiagnosticScope, PipelineProgress};

fn packet(sequence: u64, right: bool) -> DiagnosticSurface {
    DiagnosticSurface {
        sequence,
        frame: 17,
        level: 0,
        kind: DiagnosticKind::GateSupport,
        scope: DiagnosticScope::Frame,
        scale: DiagnosticScale::Linear,
        width: 128,
        height: 96,
        min: 0.0,
        max: 1.0,
        folded: 1,
        pixels: (0..128 * 96)
            .map(|i| if (i % 128 >= 64) == right { 255 } else { 0 })
            .collect::<Vec<_>>()
            .into(),
    }
}
fn draw(
    ctx: &egui::Context,
    field: &mut ProcessScales,
    packet: &DiagnosticSurface,
    texture: &TextureHandle,
    extent: Option<[usize; 2]>,
    time: f64,
    at: Pos2,
) -> egui::FullOutput {
    let mut progress = PipelineProgress::default();
    progress.bands = Some(1);
    progress.plane_size = extent;
    let surfaces = [Surface {
        epoch: 1,
        stage: Stage::Merge,
        level: packet.level,
        texture,
        frame: Some(packet.frame),
        meta: Some(SurfaceMeta {
            sequence: packet.sequence,
            kind: packet.kind,
            scale: packet.scale,
            min: packet.min,
            max: packet.max,
            samples: [packet.width, packet.height],
            folded: packet.folded,
        }),
        packet: Some(packet),
    }];
    let input = Input {
        epoch: 1,
        progress: &progress,
        frame_count: 130,
        selected: 17,
        inspected_pair: None,
        photos: &[],
        inspection_photos: &[],
        surfaces: &surfaces,
        output: None,
        output_size: None,
    };
    ctx.run(
        egui::RawInput {
            screen_rect: Some(Rect::from_min_size(Pos2::ZERO, egui::vec2(700.0, 600.0))),
            time: Some(time),
            events: vec![egui::Event::PointerMoved(at)],
            ..Default::default()
        },
        |ctx| {
            egui::CentralPanel::default()
                .frame(egui::Frame::NONE)
                .show(ctx, |ui| {
                    field.prepare_frame(ui, &input);
                    field.map(ui, bounds(), 0, DiagnosticKind::GateSupport, &input);
                });
        },
    )
}
fn bounds() -> Rect {
    Rect::from_min_max(egui::pos2(20.0, 20.0), egui::pos2(620.0, 540.0))
}
fn texture(ctx: &egui::Context) -> TextureHandle {
    ctx.load_texture(
        "matrix-binary",
        egui::ColorImage::filled([128, 96], Color32::GRAY),
        egui::TextureOptions::NEAREST,
    )
}
fn counters(field: &ProcessScales) -> (usize, usize) {
    let retained = field
        .get(0, DiagnosticKind::GateSupport)
        .unwrap()
        .binary
        .borrow();
    (retained.preparations, retained.builds)
}

#[test]
fn warm_matrix_pointer_motion_reuses_validation_glyphs_and_the_submitted_mesh() {
    let ctx = egui::Context::default();
    let texture = texture(&ctx);
    let packet = packet(1, false);
    let mut field = ProcessScales::default();
    let first = draw(
        &ctx,
        &mut field,
        &packet,
        &texture,
        Some([4096, 3072]),
        0.0,
        Pos2::ZERO,
    );
    let image = fit(egui::vec2(4096.0, 3072.0), map_aperture(bounds()));
    crate::process_sample_glyphs::assert_painted_samples(
        &first,
        image,
        field.aperture(),
        &packet,
        [4096, 3072],
    );
    let markers = crate::process_result::overlay_marker_centers(&first);
    assert!(
        !markers.is_empty(),
        "cache cannot pass by dropping positive observations"
    );
    assert!(markers.iter().all(|at| at.x < image.center().x));
    assert_eq!(counters(&field), (1, 1));
    let retained = Arc::clone(
        &field
            .get(0, DiagnosticKind::GateSupport)
            .unwrap()
            .binary
            .borrow()
            .mesh,
    );
    for step in 1..=100 {
        let output = draw(
            &ctx,
            &mut field,
            &packet,
            &texture,
            Some([4096, 3072]),
            step as f64 / 120.0,
            image.min + egui::vec2(20.0 + step as f32 * 2.0, 60.0),
        );
        assert!(
            output.shapes.iter().any(|shape| matches!(&shape.shape,
            egui::Shape::Mesh(mesh) if Arc::ptr_eq(mesh, &retained))),
            "actual paint must share the retained mesh allocation"
        );
    }
    assert_eq!(
        counters(&field),
        (1, 1),
        "hovering all100 frames must not rescan or rebuild"
    );
    assert_eq!(
        field
            .get(0, DiagnosticKind::GateSupport)
            .unwrap()
            .binary
            .borrow()
            .counts,
        Some((6144, 12288))
    );
}

#[test]
fn matrix_cache_invalidates_view_density_dpi_and_analysis_domain_without_revalidating_unchanged_receipts()
 {
    let ctx = egui::Context::default();
    let texture = texture(&ctx);
    let packet = packet(1, false);
    let mut field = ProcessScales::default();
    draw(
        &ctx,
        &mut field,
        &packet,
        &texture,
        Some([4096, 3072]),
        0.0,
        Pos2::ZERO,
    );
    field.set_view(egui::pos2(0.30, 0.5), 4.0);
    let cropped = draw(
        &ctx,
        &mut field,
        &packet,
        &texture,
        Some([4096, 3072]),
        1.0,
        Pos2::ZERO,
    );
    let image = fit(egui::vec2(4096.0, 3072.0), map_aperture(bounds()));
    assert!(field.aperture().width() < 0.3);
    crate::process_sample_glyphs::assert_painted_samples(
        &cropped,
        image,
        field.aperture(),
        &packet,
        [4096, 3072],
    );
    assert_eq!(counters(&field), (1, 2));
    crate::process_sample_glyphs::Density::Quiet.write(&ctx);
    draw(
        &ctx,
        &mut field,
        &packet,
        &texture,
        Some([4096, 3072]),
        1.1,
        Pos2::ZERO,
    );
    assert_eq!(counters(&field), (1, 3));
    ctx.set_pixels_per_point(2.0);
    draw(
        &ctx,
        &mut field,
        &packet,
        &texture,
        Some([4096, 3072]),
        1.2,
        Pos2::ZERO,
    );
    assert_eq!(counters(&field), (1, 4));
    let invalid = draw(
        &ctx,
        &mut field,
        &packet,
        &texture,
        Some([10, 10]),
        1.3,
        Pos2::ZERO,
    );
    assert_eq!(counters(&field), (2, 5));
    assert!(
        crate::process_result::overlay_marker_centers(&invalid).is_empty(),
        "impossible coefficient lattice cannot borrow old spatial marks"
    );
    let restored = draw(
        &ctx,
        &mut field,
        &packet,
        &texture,
        Some([4096, 3072]),
        1.4,
        Pos2::ZERO,
    );
    assert_eq!(counters(&field), (3, 6));
    assert!(!crate::process_result::overlay_marker_centers(&restored).is_empty());
}

#[test]
fn replacement_moves_previous_cache_with_its_receipt_and_clears_invalid_new_evidence() {
    let ctx = egui::Context::default();
    let texture = texture(&ctx);
    let old = packet(1, false);
    let next = packet(2, true);
    let mut field = ProcessScales::default();
    draw(
        &ctx,
        &mut field,
        &old,
        &texture,
        Some([4096, 3072]),
        0.0,
        Pos2::ZERO,
    );
    draw(
        &ctx,
        &mut field,
        &next,
        &texture,
        Some([4096, 3072]),
        1.0,
        Pos2::ZERO,
    );
    let snapshot = field.get(0, DiagnosticKind::GateSupport).unwrap();
    assert_eq!(snapshot.previous_packet.as_ref().unwrap().sequence, 1);
    assert_eq!(snapshot.previous_binary.borrow().preparations, 1);
    assert_eq!(snapshot.binary.borrow().preparations, 1);
    let complete = draw(
        &ctx,
        &mut field,
        &next,
        &texture,
        Some([4096, 3072]),
        1.3,
        Pos2::ZERO,
    );
    let image = fit(egui::vec2(4096.0, 3072.0), map_aperture(bounds()));
    let markers = crate::process_result::overlay_marker_centers(&complete);
    assert!(
        !markers.is_empty() && markers.iter().all(|at| at.x > image.center().x),
        "new positive half must replace the old half after reveal"
    );
    assert!(
        field
            .get(0, DiagnosticKind::GateSupport)
            .unwrap()
            .previous_binary
            .borrow()
            .glyphs
            .is_empty()
    );
    let mut invalid = packet(3, false);
    invalid.pixels = vec![37; 128 * 96].into();
    draw(
        &ctx,
        &mut field,
        &invalid,
        &texture,
        Some([4096, 3072]),
        1.4,
        Pos2::ZERO,
    );
    let cleared = draw(
        &ctx,
        &mut field,
        &invalid,
        &texture,
        Some([4096, 3072]),
        1.7,
        Pos2::ZERO,
    );
    assert!(crate::process_result::overlay_marker_centers(&cleared).is_empty());
    assert_eq!(
        field
            .get(0, DiagnosticKind::GateSupport)
            .unwrap()
            .binary
            .borrow()
            .counts,
        None
    );
}
