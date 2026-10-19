use super::*;
use crate::pipeline::{DiagnosticScope, PipelineProgress};
use std::sync::Arc;

#[test]
fn rendered_detail_rows_use_photo_pixels_or_explicit_grid_units_and_keep_the_base_separate() {
    for (writer, expected) in [
        (
            Some("stack.tiff (262 x 198, 16-bit RGB, sRGB, Malvar-He-Cutler demosaic)"),
            ["2px photo", "4px photo", "8px photo"],
        ),
        (
            Some("stack.tiff (131 x 99, 16-bit RGB, sRGB, binned from one 2x2 quad per pixel)"),
            ["1px photo", "2px photo", "4px photo"],
        ),
        (None, ["1px grid", "2px grid", "4px grid"]),
    ] {
        let ctx = egui::Context::default();
        let mut progress = PipelineProgress::default();
        progress.bands = Some(3);
        progress.output_geometry = writer.map(|value| {
            crate::process_output_space::OutputGeometry::parse(value)
                .expect("known writer geometry")
        });
        let (_, output) = draw(
            &ctx,
            &mut ProcessScales::default(),
            egui::vec2(784.0, 650.0),
            input(&progress, &[]),
            0.0,
            vec![],
        );
        let texts: Vec<_> = output
            .shapes
            .iter()
            .filter_map(|shape| match &shape.shape {
                egui::Shape::Text(text) => Some(text.galley.text()),
                _ => None,
            })
            .collect();
        for label in expected {
            assert!(
                texts.contains(&label),
                "missing actual row label {label}: {texts:?}"
            );
        }
        assert!(texts.contains(&"Broad tone"));
        assert!(texts.contains(&"residual"));
    }
}

#[test]
fn a_pending_reset_keeps_the_map_stationary_then_fits_all_linked_views_on_release() {
    let ctx = egui::Context::default();
    let samples = Samples::new(&ctx, 7, 1);
    let surfaces = samples.surfaces();
    let mut progress = PipelineProgress::default();
    progress.bands = Some(7);
    progress.plane_size = Some([400, 300]);
    let size = egui::vec2(784.0, 650.0);
    let mut scales = ProcessScales::default();
    let (_, first) = draw(
        &ctx,
        &mut scales,
        size,
        input(&progress, &surfaces),
        0.0,
        vec![],
    );
    let mesh = image_meshes(&first, samples.textures[0].id())[0];
    let image = Rect::from_points(
        &mesh
            .vertices
            .iter()
            .map(|vertex| vertex.pos)
            .collect::<Vec<_>>(),
    );
    let at = image.center();
    let _ = draw(
        &ctx,
        &mut scales,
        size,
        input(&progress, &surfaces),
        0.1,
        vec![egui::Event::PointerMoved(at), pointer(at, true)],
    );
    let (picked, _) = draw(
        &ctx,
        &mut scales,
        size,
        input(&progress, &surfaces),
        0.14,
        vec![pointer(at, false)],
    );
    assert!(picked.is_some_and(|pick| !pick.reset));
    assert!(scales.detail_zoom() > 1.0);
    let _ = draw(
        &ctx,
        &mut scales,
        size,
        input(&progress, &surfaces),
        0.59,
        vec![pointer(at, true)],
    );
    let previous = scales.pin();
    let (moved, _) = draw(
        &ctx,
        &mut scales,
        size,
        input(&progress, &surfaces),
        0.62,
        vec![egui::Event::PointerMoved(at + egui::vec2(8.0, 0.0))],
    );
    assert!(moved.is_none());
    assert_eq!(
        scales.pin(),
        previous,
        "the pending pair must not pan the diagnostic map"
    );
    let (released, _) = draw(
        &ctx,
        &mut scales,
        size,
        input(&progress, &surfaces),
        0.64,
        vec![pointer(at + egui::vec2(8.0, 0.0), false)],
    );
    assert!(released.is_some_and(|pick| pick.reset));
    assert_eq!(scales.detail_zoom(), 1.0);
    assert!(scales.selected.is_none());
}

fn pointer(point: Pos2, pressed: bool) -> egui::Event {
    egui::Event::PointerButton {
        pos: point,
        button: egui::PointerButton::Primary,
        pressed,
        modifiers: egui::Modifiers::NONE,
    }
}

fn uv_rect(mesh: &egui::epaint::Mesh) -> Rect {
    Rect::from_points(
        &mesh
            .vertices
            .iter()
            .map(|vertex| vertex.uv)
            .collect::<Vec<_>>(),
    )
}

fn near_rect(actual: Rect, expected: Rect) {
    assert!(
        actual.min.distance(expected.min) < 0.0001 && actual.max.distance(expected.max) < 0.0001,
        "{actual:?} != {expected:?}"
    );
}

#[test]
fn wheel_and_pinch_hold_the_point_under_the_cursor_and_share_one_rendered_aperture() {
    let ctx = egui::Context::default();
    let samples = Samples::new(&ctx, 7, 1);
    let surfaces = samples.surfaces();
    let mut progress = PipelineProgress::default();
    progress.bands = Some(7);
    progress.plane_size = Some([400, 300]);
    let size = egui::vec2(784.0, 650.0);
    let mut scales = ProcessScales::default();
    let _ = draw(
        &ctx,
        &mut scales,
        size,
        input(&progress, &surfaces),
        0.0,
        vec![],
    );
    scales.set_view(egui::pos2(0.5, 0.5), 4.0);
    let (_, initial) = draw(
        &ctx,
        &mut scales,
        size,
        input(&progress, &surfaces),
        0.1,
        vec![],
    );
    let mesh = image_meshes(&initial, samples.textures[0].id())[0];
    let bounds = Rect::from_points(
        &mesh
            .vertices
            .iter()
            .map(|vertex| vertex.pos)
            .collect::<Vec<_>>(),
    );
    let anchor = egui::pos2(0.27, 0.68);
    let point = bounds.min + bounds.size() * anchor.to_vec2();
    let old = uv_rect(mesh);
    let physical = old.min + old.size() * anchor.to_vec2();
    let (_, wheel) = draw(
        &ctx,
        &mut scales,
        size,
        input(&progress, &surfaces),
        0.2,
        vec![
            egui::Event::PointerMoved(point),
            egui::Event::MouseWheel {
                unit: egui::MouseWheelUnit::Point,
                delta: egui::vec2(0.0, 80.0),
                modifiers: egui::Modifiers::NONE,
            },
        ],
    );
    let target = 4.0 * 0.48_f32.exp();
    assert!((scales.detail_zoom() - target).abs() < 0.0001);
    for texture in samples.scalar_textures() {
        near_rect(uv_rect(image_meshes(&wheel, texture.id())[0]), old);
    }
    let mut saw_easing = false;
    for time in [0.23, 0.28, 0.4, 0.6] {
        let (_, output) = draw(
            &ctx,
            &mut scales,
            size,
            input(&progress, &surfaces),
            time,
            vec![],
        );
        let uv = scales.aperture();
        assert!((uv.min + uv.size() * anchor.to_vec2()).distance(physical) < 0.0001);
        assert!(
            (scales.detail_zoom() - target).abs() < 0.0001,
            "wheel cannot coast into extra target changes"
        );
        saw_easing |= uv.width().recip() > 4.0 && uv.width().recip() < target;
        for texture in samples.scalar_textures() {
            near_rect(uv_rect(image_meshes(&output, texture.id())[0]), uv);
        }
    }
    assert!(saw_easing);
    let _ = draw(
        &ctx,
        &mut scales,
        size,
        input(&progress, &surfaces),
        0.7,
        vec![egui::Event::Zoom(1.25)],
    );
    assert!((scales.detail_zoom() - target * 1.25).abs() < 0.0001);
    let _ = draw(
        &ctx,
        &mut scales,
        size,
        input(&progress, &surfaces),
        1.0,
        vec![],
    );
    assert!(
        (scales.aperture().min + scales.aperture().size() * anchor.to_vec2()).distance(physical)
            < 0.0001
    );
    scales.reset_view();
    let _ = draw(
        &ctx,
        &mut scales,
        size,
        input(&progress, &surfaces),
        1.3,
        vec![],
    );
    assert_eq!(scales.detail_zoom(), 1.0);
    assert_eq!(scales.pin(), egui::pos2(0.5, 0.5));
    near_rect(
        scales.aperture(),
        Rect::from_min_max(Pos2::ZERO, egui::pos2(1.0, 1.0)),
    );
}

#[test]
fn grabbing_map_preserves_threshold_motion_and_clamped_edge_pullback_without_drift() {
    let ctx = egui::Context::default();
    let samples = Samples::new(&ctx, 7, 1);
    let surfaces = samples.surfaces();
    let mut progress = PipelineProgress::default();
    progress.bands = Some(7);
    progress.plane_size = Some([400, 300]);
    let size = egui::vec2(784.0, 650.0);
    let mut scales = ProcessScales::default();
    let _ = draw(
        &ctx,
        &mut scales,
        size,
        input(&progress, &surfaces),
        0.0,
        vec![],
    );
    scales.set_view(egui::pos2(0.5, 0.5), 4.0);
    let (_, initial) = draw(
        &ctx,
        &mut scales,
        size,
        input(&progress, &surfaces),
        0.1,
        vec![],
    );
    let mesh = image_meshes(&initial, samples.textures[0].id())[0];
    let bounds = Rect::from_points(
        &mesh
            .vertices
            .iter()
            .map(|vertex| vertex.pos)
            .collect::<Vec<_>>(),
    );
    let origin = bounds.center();
    let _ = draw(
        &ctx,
        &mut scales,
        size,
        input(&progress, &surfaces),
        0.2,
        vec![egui::Event::PointerMoved(origin), pointer(origin, true)],
    );
    for (index, x) in [3.0, 6.0, 9.0].into_iter().enumerate() {
        let _ = draw(
            &ctx,
            &mut scales,
            size,
            input(&progress, &surfaces),
            0.21 + index as f64 * 0.01,
            vec![egui::Event::PointerMoved(origin + egui::vec2(x, 0.0))],
        );
    }
    let expected = 0.5 - 9.0 / bounds.width() * 0.25;
    assert!(
        (scales.pin().x - expected).abs() < 0.0001,
        "all movement since press must be included, with natural grab sign"
    );
    let far = origin + egui::vec2(500.0, 0.0);
    let _ = draw(
        &ctx,
        &mut scales,
        size,
        input(&progress, &surfaces),
        0.3,
        vec![egui::Event::PointerMoved(far)],
    );
    assert_eq!(scales.pin().x, 0.125);
    let _ = draw(
        &ctx,
        &mut scales,
        size,
        input(&progress, &surfaces),
        0.4,
        vec![egui::Event::PointerMoved(far - egui::vec2(3.0, 0.0))],
    );
    assert!(
        scales.pin().x > 0.125,
        "pulling back from a clamped edge cannot have an overshoot dead zone"
    );
    let retained = scales.pin();
    let _ = draw(
        &ctx,
        &mut scales,
        size,
        input(&progress, &surfaces),
        0.5,
        vec![],
    );
    assert_eq!(scales.pin(), retained);
    let _ = draw(
        &ctx,
        &mut scales,
        size,
        input(&progress, &surfaces),
        0.6,
        vec![pointer(far - egui::vec2(3.0, 0.0), false)],
    );
    assert_eq!(scales.pin(), retained);
}

#[test]
fn modal_blocks_background_map_zoom_and_pin_gestures() {
    let ctx = egui::Context::default();
    let samples = Samples::new(&ctx, 7, 1);
    let surfaces = samples.surfaces();
    let mut progress = PipelineProgress::default();
    progress.bands = Some(7);
    progress.plane_size = Some([400, 300]);
    let size = egui::vec2(784.0, 650.0);
    let mut scales = ProcessScales::default();
    let (_, first) = draw(
        &ctx,
        &mut scales,
        size,
        input(&progress, &surfaces),
        0.0,
        vec![],
    );
    let mesh = image_meshes(&first, samples.textures[0].id())[0];
    let point = Rect::from_points(
        &mesh
            .vertices
            .iter()
            .map(|vertex| vertex.pos)
            .collect::<Vec<_>>(),
    )
    .center();
    for (index, events) in [
        vec![],
        vec![],
        vec![
            egui::Event::PointerMoved(point),
            egui::Event::Zoom(2.0),
            pointer(point, true),
        ],
        vec![pointer(point, false)],
    ]
    .into_iter()
    .enumerate()
    {
        let _ = ctx.run(
            egui::RawInput {
                screen_rect: Some(Rect::from_min_size(Pos2::ZERO, size)),
                time: Some(0.1 + index as f64 * 0.1),
                events,
                ..Default::default()
            },
            |ctx| {
                egui::CentralPanel::default()
                    .frame(egui::Frame::NONE)
                    .show(ctx, |ui| {
                        assert!(
                            scales
                                .show(ui, ui.max_rect(), &input(&progress, &surfaces))
                                .is_none()
                        );
                    });
                egui::Modal::new(egui::Id::new("map-gesture-modal")).show(ctx, |ui| {
                    ui.label("Choose a bracket");
                });
            },
        );
    }
    assert_eq!(scales.detail_zoom(), 1.0);
    assert_eq!(scales.pin(), egui::pos2(0.5, 0.5));
}

struct Samples {
    textures: Vec<TextureHandle>,
    packets: Vec<DiagnosticSurface>,
}
impl Samples {
    fn scalar_textures(&self) -> impl Iterator<Item = &TextureHandle> {
        self.packets
            .iter()
            .zip(&self.textures)
            .filter_map(|(packet, texture)| {
                (!matches!(
                    packet.kind,
                    DiagnosticKind::GateSupport | DiagnosticKind::Averaging
                ))
                .then_some(texture)
            })
    }
    fn new(ctx: &egui::Context, bands: usize, first_sequence: u64) -> Self {
        let mut textures = Vec::new();
        let mut packets = Vec::new();
        for level in 0..=bands {
            for kind in KINDS {
                // The real producer has no independent base-band energy election.
                if level == bands
                    && matches!(
                        kind,
                        DiagnosticKind::FocusEnergy | DiagnosticKind::GateFloor
                    )
                {
                    continue;
                }
                let sequence = first_sequence + packets.len() as u64;
                textures.push(ctx.load_texture(
                    format!("scale-{sequence}"),
                    egui::ColorImage::filled([4, 3], Color32::from_rgb(50, 130, 80)),
                    egui::TextureOptions::NEAREST,
                ));
                packets.push(packet(sequence, level, kind));
            }
        }
        Self { textures, packets }
    }
    fn surfaces(&self) -> Vec<Surface<'_>> {
        self.packets
            .iter()
            .zip(&self.textures)
            .map(|(packet, texture)| Surface {
                epoch: 1,
                stage: Stage::Merge,
                level: packet.level,

                texture,

                frame: (packet.scope == DiagnosticScope::Frame).then_some(packet.frame),
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
            })
            .collect()
    }
}
fn packet(sequence: u64, level: usize, kind: DiagnosticKind) -> DiagnosticSurface {
    let binary = matches!(
        kind,
        DiagnosticKind::GateSupport | DiagnosticKind::Averaging
    );
    DiagnosticSurface {
        sequence,
        level,
        kind,
        frame: 9,
        scope: if matches!(
            kind,
            DiagnosticKind::Averaging | DiagnosticKind::Coefficient
        ) {
            DiagnosticScope::Stack
        } else {
            DiagnosticScope::Frame
        },
        scale: if binary {
            DiagnosticScale::Linear
        } else if kind == DiagnosticKind::Coefficient {
            DiagnosticScale::Symmetric
        } else {
            DiagnosticScale::Log
        },
        width: 2,
        height: 2,
        min: if kind == DiagnosticKind::Coefficient {
            -255.0
        } else {
            0.0
        },
        max: if binary { 1.0 } else { 255.0 },
        pixels: Arc::from([0, 255, 255, 0]),
        folded: 3,
    }
}
fn input<'a>(progress: &'a PipelineProgress, surfaces: &'a [Surface<'a>]) -> Input<'a> {
    Input {
        epoch: 1,
        progress,
        frame_count: 12,
        selected: 0,
        inspected_pair: None,
        photos: &[],
        inspection_photos: &[],
        surfaces,
        output: None,
        output_size: None,
    }
}
fn draw(
    ctx: &egui::Context,
    scales: &mut ProcessScales,
    size: egui::Vec2,
    input: Input<'_>,
    time: f64,
    events: Vec<egui::Event>,
) -> (Option<ScaleInspection>, egui::FullOutput) {
    let mut pick = None;
    let output = ctx.run(
        egui::RawInput {
            screen_rect: Some(Rect::from_min_size(Pos2::ZERO, size)),
            time: Some(time),
            events,
            ..Default::default()
        },
        |ctx| {
            egui::CentralPanel::default()
                .frame(egui::Frame::NONE)
                .show(ctx, |ui| {
                    pick = scales.show(ui, ui.max_rect(), &input);
                });
        },
    );
    (pick, output)
}
fn has(output: &egui::FullOutput, text: &str) -> bool {
    output.shapes.iter().any(
        |shape| matches!(&shape.shape, egui::Shape::Text(value) if value.galley.text() == text),
    )
}
fn image_meshes(output: &egui::FullOutput, texture: egui::TextureId) -> Vec<&egui::epaint::Mesh> {
    output
        .shapes
        .iter()
        .filter_map(|shape| match &shape.shape {
            egui::Shape::Mesh(mesh) if mesh.texture_id == texture => Some(mesh.as_ref()),
            _ => None,
        })
        .collect()
}

#[test]
fn every_real_map_is_visible_together_at_compact_and_desktop_sizes_through_completion() {
    for size in [egui::vec2(580.0, 380.0), egui::vec2(784.0, 650.0)] {
        let ctx = egui::Context::default();
        let samples = Samples::new(&ctx, 7, 1);
        let surfaces = samples.surfaces();
        let mut progress = PipelineProgress::default();
        progress.bands = Some(7);
        progress.plane_size = Some([400, 300]);
        let mut scales = ProcessScales::default();
        let (_, initial) = draw(
            &ctx,
            &mut scales,
            size,
            input(&progress, &surfaces),
            0.0,
            vec![],
        );
        assert_eq!(
            samples.textures.len(),
            38,
            "seven detail rows plus the true base's three observed maps"
        );
        for texture in samples.scalar_textures() {
            let meshes = image_meshes(&initial, texture.id());
            assert_eq!(
                meshes.len(),
                1,
                "every available map must actually be painted together"
            );
            let bounds = Rect::from_points(
                &meshes[0]
                    .vertices
                    .iter()
                    .map(|vertex| vertex.pos)
                    .collect::<Vec<_>>(),
            );
            assert!(
                bounds.height() >= 26.0,
                "compact map pixels cannot collapse into a tiny strip: {bounds:?}"
            );
            assert!(Rect::from_min_size(Pos2::ZERO, size).contains_rect(bounds));
        }
        assert!(has(&initial, "Broad tone"));
        assert_eq!(scales.output_ports().len(), 8);
        assert!(
            scales
                .output_ports()
                .iter()
                .all(|port| port.observed && port.folded == 3)
        );
        let positions = scales
            .output_ports()
            .iter()
            .map(|port| port.position)
            .collect::<Vec<_>>();
        progress.mark_complete();
        let (_, finished) = draw(&ctx, &mut scales, size, input(&progress, &[]), 1.0, vec![]);
        assert_eq!(
            positions,
            scales
                .output_ports()
                .iter()
                .map(|port| port.position)
                .collect::<Vec<_>>(),
            "phase changes cannot rebuild row geometry"
        );
        for texture in samples.scalar_textures() {
            assert_eq!(
                image_meshes(&finished, texture.id()).len(),
                1,
                "completed evidence remains on screen"
            );
        }
    }
}

#[test]
fn scale_plan_has_the_true_base_and_does_not_shrink_when_first_sample_arrives() {
    let ctx = egui::Context::default();
    let mut scales = ProcessScales::default();
    let mut progress = PipelineProgress::default();
    assert_eq!(scales.row_count(&input(&progress, &[])), 8);
    let samples = Samples::new(&ctx, 0, 1);
    let surfaces = samples.surfaces();
    scales.receive(&input(&progress, &surfaces), 0.0);
    assert_eq!(
        scales.row_count(&input(&progress, &surfaces)),
        8,
        "a sparse first event cannot collapse the unknown plan"
    );
    progress.bands = Some(7);
    let (_, output) = draw(
        &ctx,
        &mut scales,
        egui::vec2(784.0, 650.0),
        input(&progress, &[]),
        0.0,
        vec![],
    );
    let no_election = output
        .shapes
        .iter()
        .filter_map(|shape| match &shape.shape {
            egui::Shape::Text(text) if text.galley.text() == "not elected" => Some(text.pos.y),
            _ => None,
        })
        .collect::<Vec<_>>();
    assert_eq!(no_election.len(), 2);
    let base = Layout::new(Rect::from_min_size(Pos2::ZERO, egui::vec2(784.0, 650.0)), 8).row(7);
    assert!(
        no_election
            .iter()
            .all(|y| *y >= base.top() && *y <= base.bottom()),
        "detail level six is not the residual base"
    );
    assert_eq!(detail_label(0, None), "1px grid");
    assert_eq!(detail_label(1, None), "2px grid");
    assert_eq!(detail_label(7, None), "128px grid");
    progress.bands = Some(3);
    assert_eq!(
        ProcessScales::default().row_count(&input(&progress, &[])),
        4
    );
}

#[test]
fn clicking_a_late_scale_changes_the_shared_pin_without_hiding_any_row() {
    let ctx = egui::Context::default();
    let samples = Samples::new(&ctx, 7, 1);
    let surfaces = samples.surfaces();
    let mut progress = PipelineProgress::default();
    progress.bands = Some(7);
    progress.plane_size = Some([400, 300]);
    let mut scales = ProcessScales::default();
    let size = egui::vec2(784.0, 650.0);
    let layout = Layout::new(Rect::from_min_size(Pos2::ZERO, size), 8);
    let fitted = fit(egui::vec2(400.0, 300.0), map_aperture(layout.cell(6, 2)));
    let point = fitted.min + fitted.size() * egui::vec2(0.25, 0.75);
    let _ = draw(
        &ctx,
        &mut scales,
        size,
        input(&progress, &surfaces),
        0.0,
        vec![],
    );
    let _ = draw(
        &ctx,
        &mut scales,
        size,
        input(&progress, &surfaces),
        0.1,
        vec![
            egui::Event::PointerMoved(point),
            egui::Event::PointerButton {
                pos: point,
                button: egui::PointerButton::Primary,
                pressed: true,
                modifiers: egui::Modifiers::NONE,
            },
        ],
    );
    let (pick, output) = draw(
        &ctx,
        &mut scales,
        size,
        input(&progress, &surfaces),
        0.2,
        vec![egui::Event::PointerButton {
            pos: point,
            button: egui::PointerButton::Primary,
            pressed: false,
            modifiers: egui::Modifiers::NONE,
        }],
    );
    let pick =
        pick.expect("a source-support map in the penultimate detail row must be interactive");
    assert_eq!(pick.level, 6);
    assert_eq!(pick.kind, DiagnosticKind::GateSupport);
    assert!(pick.uv.distance(egui::pos2(0.25, 0.75)) < 0.001);
    assert_eq!(scales.pin(), pick.uv);
    for texture in samples.scalar_textures() {
        assert_eq!(image_meshes(&output, texture.id()).len(), 1);
    }
    scales.set_pin(egui::pos2(0.8, 0.2));
    assert_eq!(scales.pin(), egui::pos2(0.8, 0.2));
}

#[test]
fn accumulated_fold_counts_are_actual_events_not_source_prefixes_or_image_sample_counts() {
    let ctx = egui::Context::default();
    let mut progress = PipelineProgress::default();
    progress.bands = Some(7);
    progress.ingest("STREHL_UI_PROGRESS event=band-work level=3 completed=6 total=12 index=10\n");
    assert_eq!(
        progress.merge_bands.get(&3).map(|work| work.completed),
        Some(6),
        "fixture must exercise a real cumulative fold event"
    );
    let samples = Samples::new(&ctx, 7, 1);
    let surfaces = samples.surfaces();
    let mut scales = ProcessScales::default();
    let (_, output) = draw(
        &ctx,
        &mut scales,
        egui::vec2(784.0, 650.0),
        input(&progress, &surfaces),
        0.0,
        vec![],
    );
    assert!(has(&output, "6/12 folds"));
    assert!(has(&output, "3 frames"));
    assert_eq!(
        scales.output_ports()[3].folded,
        3,
        "latest accumulated sampled image can legitimately lag six completed folds"
    );
    let layout = Layout::new(Rect::from_min_size(Pos2::ZERO, egui::vec2(784.0, 650.0)), 8);
    let bars = output
        .shapes
        .iter()
        .filter_map(|shape| match &shape.shape {
            egui::Shape::Rect(rect)
                if rect.fill == GREEN && (rect.rect.height() - 3.0).abs() < 0.01 =>
            {
                Some(rect.rect)
            }
            _ => None,
        })
        .collect::<Vec<_>>();
    assert_eq!(
        bars.len(),
        1,
        "work on one scale does not advance any other row"
    );
    assert!((bars[0].width() - (layout.label_width - 17.0) * 0.5).abs() < 0.01);
    assert_eq!(bars[0].top(), layout.row(3).bottom() - 5.0);
}

#[test]
fn exact_packets_survive_transport_eviction_and_mismatched_inputs_do_not_light_the_path() {
    let ctx = egui::Context::default();
    let samples = Samples::new(&ctx, 7, 1);
    let mut surfaces = samples.surfaces();
    let mut progress = PipelineProgress::default();
    progress.bands = Some(7);
    let mut scales = ProcessScales::default();
    let _ = draw(
        &ctx,
        &mut scales,
        egui::vec2(784.0, 650.0),
        input(&progress, &surfaces),
        0.0,
        vec![],
    );
    assert!(scales.frame_inputs_match(0));
    assert!(
        progress.diagnostic_surfaces.is_empty(),
        "the texture-owned packet must work without a transport queue"
    );
    let item = scales.get(0, DiagnosticKind::GateSupport).unwrap();
    assert!(Arc::ptr_eq(
        &item.packet.as_ref().unwrap().pixels,
        &samples.packets[2].pixels
    ));
    let _ = draw(
        &ctx,
        &mut scales,
        egui::vec2(784.0, 650.0),
        input(&progress, &[]),
        1.0,
        vec![],
    );
    assert_eq!(
        value_at(
            scales
                .get(0, DiagnosticKind::GateSupport)
                .unwrap()
                .packet
                .as_ref()
                .unwrap(),
            egui::pos2(0.75, 0.25)
        ),
        Some(1.0)
    );
    surfaces[1].frame = Some(4);
    surfaces[1].meta.as_mut().unwrap().sequence = 1000;
    surfaces[1].packet = None;
    scales.receive(&input(&progress, &surfaces), 2.0);
    assert!(
        !scales.frame_inputs_match(0),
        "independently arriving maps from different captures cannot imply a matched comparison"
    );
    assert!(
        scales
            .get(0, DiagnosticKind::GateFloor)
            .unwrap()
            .packet
            .is_none(),
        "old exact numerical samples cannot accompany a newer unrelated texture"
    );
    let mut next = input(&progress, &[]);
    next.epoch = 2;
    let _ = draw(
        &ctx,
        &mut scales,
        egui::vec2(784.0, 650.0),
        next,
        3.0,
        vec![],
    );
    assert!(scales.snapshots.is_empty());
    assert!(
        scales
            .output_ports()
            .iter()
            .all(|port| !port.observed && port.folded == 0)
    );
}

#[test]
fn every_replacement_keeps_old_pixels_until_a_bounded_reveal_and_defers_a_third_generation() {
    let ctx = egui::Context::default();
    let first = Samples::new(&ctx, 0, 1);
    let second = Samples::new(&ctx, 0, 100);
    let third = Samples::new(&ctx, 0, 200);
    let old = first.surfaces();
    let new = second.surfaces();
    let newer = third.surfaces();
    let mut progress = PipelineProgress::default();
    progress.bands = Some(0);
    let mut scales = ProcessScales::default();
    let size = egui::vec2(580.0, 380.0);
    let _ = draw(&ctx, &mut scales, size, input(&progress, &old), 0.0, vec![]);
    let (_, start) = draw(&ctx, &mut scales, size, input(&progress, &new), 1.0, vec![]);
    let old_id = first.textures[2].id();
    let new_id = second.textures[2].id();
    assert_ne!(
        old_id, new_id,
        "real distinct immutable texture generations are required"
    );
    assert!(
        image_meshes(&start, old_id)[0]
            .vertices
            .iter()
            .all(|vertex| vertex.color.a() == 255)
    );
    assert!(
        image_meshes(&start, new_id)[0]
            .vertices
            .iter()
            .all(|vertex| vertex.color.a() == 0)
    );
    assert!(scales.transitioning());
    let (_, mid) = draw(
        &ctx,
        &mut scales,
        size,
        input(&progress, &newer),
        1.1,
        vec![],
    );
    assert_eq!(image_meshes(&mid, new_id)[0].vertices[0].color.a(), 128);
    assert!(
        image_meshes(&mid, third.textures[2].id()).is_empty(),
        "a third arrival cannot interrupt the reveal"
    );
    let visible = scales.presented_surfaces();
    assert_eq!(visible[2].texture.id(), new_id);
    assert_eq!(
        visible[2].meta.unwrap().sequence,
        second.packets[2].sequence
    );
    assert_eq!(
        visible[2].packet.unwrap().sequence,
        second.packets[2].sequence,
        "enlarged inspection must use the actual displayed generation, not queued input"
    );
    let _ = draw(&ctx, &mut scales, size, input(&progress, &[]), 1.21, vec![]);
    assert!(
        scales.transitioning(),
        "a deferred newest generation must prevent premature settled/screenshot state"
    );
    let (_, restarted) = draw(&ctx, &mut scales, size, input(&progress, &[]), 1.22, vec![]);
    assert_eq!(
        image_meshes(&restarted, new_id)[0].vertices[0].color.a(),
        255
    );
    let (_, final_frame) = draw(&ctx, &mut scales, size, input(&progress, &[]), 1.43, vec![]);
    assert!(!scales.transitioning());
    assert!(image_meshes(&final_frame, new_id).is_empty());
    assert_eq!(
        image_meshes(&final_frame, third.textures[2].id())[0].vertices[0]
            .color
            .a(),
        255
    );
}

#[test]
fn rapid_arrivals_keep_latest_exact_generation_without_interrupting_the_active_reveal() {
    let ctx = egui::Context::default();
    let generations = [1, 100, 200, 300].map(|sequence| Samples::new(&ctx, 0, sequence));
    let mut progress = PipelineProgress::default();
    progress.bands = Some(0);
    let mut scales = ProcessScales::default();
    let size = egui::vec2(580.0, 380.0);
    for (index, time) in [0.0, 1.0, 1.05, 1.1].into_iter().enumerate() {
        let surfaces = generations[index].surfaces();
        let _ = draw(
            &ctx,
            &mut scales,
            size,
            input(&progress, &surfaces),
            time,
            vec![],
        );
    }
    let snapshot = scales.get(0, DiagnosticKind::GateSupport).unwrap();
    assert_eq!(snapshot.meta.sequence, 100);
    assert_eq!(snapshot.pending.as_ref().unwrap().meta.sequence, 300);
    assert_eq!(
        snapshot.arrived, 1.0,
        "new arrivals cannot restart the active reveal"
    );
    assert_eq!(
        scales.snapshots.len(),
        3,
        "bounded one current and one pending per map"
    );
    let (_, promotion) = draw(&ctx, &mut scales, size, input(&progress, &[]), 1.21, vec![]);
    assert!(image_meshes(&promotion, generations[2].textures[2].id()).is_empty());
    assert_eq!(
        image_meshes(&promotion, generations[1].textures[2].id())[0].vertices[0]
            .color
            .a(),
        255
    );
    let surface = &scales.presented_surfaces()[2];
    assert_eq!(surface.texture.id(), generations[3].textures[2].id());
    assert_eq!(surface.meta.unwrap().sequence, 302);
    assert_eq!(surface.packet.unwrap().sequence, 302);
    let (_, settled) = draw(&ctx, &mut scales, size, input(&progress, &[]), 1.42, vec![]);
    assert!(!scales.transitioning());
    assert_eq!(
        image_meshes(&settled, generations[3].textures[2].id())[0].vertices[0]
            .color
            .a(),
        255
    );
    assert!(image_meshes(&settled, generations[1].textures[2].id()).is_empty());
}

fn ingest_mask(
    progress: &mut PipelineProgress,
    sequence: u64,
    frame: usize,
    folded: usize,
    kind: &str,
    data: &str,
) {
    let scope = if kind == "gate-support" {
        "frame"
    } else {
        "stack"
    };
    let folded = if scope == "frame" { 1 } else { folded };
    progress.ingest(&format!("STREHL_UI_PROGRESS event=diagnostic seq={sequence} frame={frame} level=0 kind={kind} scope={scope} scale=linear width=2 height=2 min=0 max=1 folded={folded} total=12 sampling=nearest data={data}\n"));
}

#[test]
fn all_supported_levels_retain_their_observed_maps_beyond_the_old_96_surface_limit() {
    let ctx = egui::Context::default();
    let samples = Samples::new(&ctx, 63, 1);
    assert_eq!(samples.packets.len(), 318);
    let surfaces = samples.surfaces();
    let progress = PipelineProgress::default();
    let mut scales = ProcessScales::default();
    scales.receive(&input(&progress, &surfaces), 0.0);
    assert_eq!(scales.snapshots.len(), 318);
    for packet in &samples.packets {
        let item = scales
            .get(packet.level, packet.kind)
            .expect("later scales cannot evict earlier observed maps");
        assert_eq!(item.packet.as_ref().unwrap().sequence, packet.sequence);
    }
}

#[test]
fn sampled_history_has_real_sparse_marks_distinct_zero_masks_and_stable_source_order() {
    let ctx = egui::Context::default();
    let mut progress = PipelineProgress::default();
    progress.bands = Some(7);
    // An all-zero observed mask is evidence; the ten unobserved masks are not.
    ingest_mask(&mut progress, 1, 1, 1, "gate-support", "00000000");
    ingest_mask(&mut progress, 2, 9, 2, "gate-support", "ffffffff");
    ingest_mask(&mut progress, 3, 9, 2, "averaging", "00ff00ff");
    assert_eq!(progress.sampled_mask_history[0].observations(), 2);
    let mut scales = ProcessScales::default();
    let size = egui::vec2(580.0, 380.0);
    let layout = Layout::new(Rect::from_min_size(Pos2::ZERO, size), 8);
    let support_trace = trace_rect(layout.cell(0, 2));
    let fallback_trace = trace_rect(layout.cell(0, 3));
    let (_, initial) = draw(&ctx, &mut scales, size, input(&progress, &[]), 0.0, vec![]);
    let marks = |output: &egui::FullOutput, region: Rect| {
        output
            .shapes
            .iter()
            .filter_map(|shape| match &shape.shape {
                egui::Shape::Rect(mark)
                    if mark.rect.height() == 2.0
                        && region.contains_rect(mark.rect)
                        && mark.fill != LINE.gamma_multiply(0.4) =>
                {
                    Some((mark.rect, mark.fill))
                }
                _ => None,
            })
            .collect::<Vec<_>>()
    };
    let support = marks(&initial, support_trace);
    assert_eq!(support.len(), 2, "unobserved positions must remain blank");
    assert_eq!(support[0].1, GREEN.gamma_multiply(0.3));
    assert_eq!(support[1].1, GREEN);
    assert!(
        (support[0].0.center().x - (support_trace.left() + support_trace.width() * 1.5 / 12.0))
            .abs()
            < 0.01
    );
    assert!(
        (support[1].0.center().x - (support_trace.left() + support_trace.width() * 9.5 / 12.0))
            .abs()
            < 0.01
    );
    let fallback = marks(&initial, fallback_trace);
    assert_eq!(fallback.len(), 1);
    assert!(
        (fallback[0].0.center().x - (fallback_trace.left() + fallback_trace.width() * 1.5 / 12.0))
            .abs()
            < 0.01,
        "fallback is placed at accepted prefix two, not source capture ten"
    );
    assert!(
        scales.snapshots.is_empty(),
        "history must survive independently of displayed textures"
    );
    ingest_mask(&mut progress, 4, 5, 3, "gate-support", "00ff00ff");
    progress.mark_complete();
    let (_, completed) = draw(&ctx, &mut scales, size, input(&progress, &[]), 1.0, vec![]);
    let after = marks(&completed, support_trace);
    assert_eq!(after.len(), 3);
    assert!(
        support.iter().all(|mark| after.contains(mark)),
        "later work and completion cannot move earlier evidence"
    );
    assert!(has(
        &completed,
        "Whole-field mask area · frame / prefix traces"
    ));
    assert!(has(&completed, "Double-click: fit · right-click: actions"));
    let footer = completed
        .shapes
        .iter()
        .filter_map(|shape| match &shape.shape {
            egui::Shape::Text(text)
                if text.galley.text().contains("traces")
                    || text.galley.text().starts_with("Double-click: fit") =>
            {
                Some(Rect::from_min_size(text.pos, text.galley.size()))
            }
            _ => None,
        })
        .collect::<Vec<_>>();
    assert_eq!(footer.len(), 2);
    assert!(
        !footer[0].intersects(footer[1]),
        "shared sampled-scope legend must not collide with interaction hint"
    );
}

#[test]
fn percentage_badges_use_actual_binary_samples_and_fit_inside_the_compact_maps() {
    for size in [egui::vec2(580.0, 380.0), egui::vec2(784.0, 650.0)] {
        let ctx = egui::Context::default();
        let mut samples = Samples::new(&ctx, 7, 1);
        let support = samples
            .packets
            .iter_mut()
            .find(|packet| packet.level == 0 && packet.kind == DiagnosticKind::GateSupport)
            .unwrap();
        support.pixels = Arc::from([0, 0, 0, 0]);
        let fallback = samples
            .packets
            .iter_mut()
            .find(|packet| packet.level == 0 && packet.kind == DiagnosticKind::Averaging)
            .unwrap();
        fallback.pixels = Arc::from([255, 255, 255, 255]);
        let surfaces = samples.surfaces();
        let mut progress = PipelineProgress::default();
        progress.bands = Some(7);
        progress.plane_size = Some([400, 300]);
        let mut scales = ProcessScales::default();
        let (_, output) = draw(
            &ctx,
            &mut scales,
            size,
            input(&progress, &surfaces),
            0.0,
            vec![],
        );
        let badges = output
            .shapes
            .iter()
            .filter_map(|shape| match &shape.shape {
                egui::Shape::Text(text) if text.galley.text().ends_with('%') => Some((
                    text.galley.text(),
                    Rect::from_min_size(text.pos, text.galley.size()),
                )),
                _ => None,
            })
            .collect::<Vec<_>>();
        assert_eq!(
            badges.len(),
            16,
            "both true mask columns must show sampled area on every row"
        );
        assert!(badges.iter().any(|(text, _)| *text == "0%"));
        assert!(badges.iter().any(|(text, _)| *text == "50%"));
        assert!(badges.iter().any(|(text, _)| *text == "100%"));
        let layout = Layout::new(Rect::from_min_size(Pos2::ZERO, size), 8);
        let bounds = (0..8)
            .flat_map(|level| {
                [2, 3].map(move |column| {
                    fit(
                        egui::vec2(400.0, 300.0),
                        map_aperture(layout.cell(level, column)),
                    )
                })
            })
            .collect::<Vec<_>>();
        assert!(
            badges
                .iter()
                .all(|(_, badge)| bounds.iter().any(|map| map.contains_rect(*badge)))
        );
    }
    let mut invalid = packet(1, 0, DiagnosticKind::GateSupport);
    invalid.pixels = Arc::from([0, 128, 255, 0]);
    assert_eq!(
        mask_counts(&invalid),
        None,
        "interpolated gray values cannot be counted as binary evidence"
    );
    invalid.pixels = Arc::from([0, 0, 0, 0]);
    assert_eq!(mask_counts(&invalid), Some((0, 4)));
}

#[test]
fn cropped_analysis_domain_controls_map_geometry_and_coordinate_pins() {
    let ctx = egui::Context::default();
    let mut progress = PipelineProgress::default();
    progress.bands = Some(7);
    progress.ingest("planes : 400 x 300, four CFA planes\n");
    progress.ingest("analysis domain : 200 x 300 at full-plane origin (100, 0) -- Crop is applied before merging\n");
    assert_eq!(progress.plane_size, Some([400, 300]));
    assert_eq!(progress.analysis_size, Some([200, 300]));
    for invalid in [
        "analysis domain : 0 x 300 at full-plane origin (0, 0)\n",
        "analysis domain : 200 x invalid at full-plane origin (0, 0)\n",
        "analysis domain : 999 x 300 estimated dimensions\n",
    ] {
        progress.ingest(invalid);
        assert_eq!(
            progress.analysis_size,
            Some([200, 300]),
            "malformed geometry must not replace an observed crop"
        );
    }
    let samples = Samples::new(&ctx, 7, 1);
    let surfaces = samples.surfaces();
    let mut scales = ProcessScales::default();
    let size = egui::vec2(580.0, 380.0);
    let layout = Layout::new(Rect::from_min_size(Pos2::ZERO, size), 8);
    let expected = fit(egui::vec2(200.0, 300.0), map_aperture(layout.cell(0, 0)));
    let old = fit(egui::vec2(400.0, 300.0), map_aperture(layout.cell(0, 0)));
    assert!(
        (old.width() - expected.width()).abs() > 10.0,
        "fixture must visibly distinguish full plane from analysis crop"
    );
    let (_, output) = draw(
        &ctx,
        &mut scales,
        size,
        input(&progress, &surfaces),
        0.0,
        vec![],
    );
    let mesh = image_meshes(&output, samples.textures[0].id())[0];
    let actual = Rect::from_points(
        &mesh
            .vertices
            .iter()
            .map(|vertex| vertex.pos)
            .collect::<Vec<_>>(),
    );
    assert_eq!(
        actual, expected,
        "map must preserve the analysis domain's aspect, not the camera's full plane"
    );
    let point = actual.min + actual.size() * egui::vec2(0.75, 0.25);
    let _ = draw(
        &ctx,
        &mut scales,
        size,
        input(&progress, &[]),
        0.1,
        vec![
            egui::Event::PointerMoved(point),
            egui::Event::PointerButton {
                pos: point,
                button: egui::PointerButton::Primary,
                pressed: true,
                modifiers: egui::Modifiers::NONE,
            },
        ],
    );
    let (pick, _) = draw(
        &ctx,
        &mut scales,
        size,
        input(&progress, &[]),
        0.2,
        vec![egui::Event::PointerButton {
            pos: point,
            button: egui::PointerButton::Primary,
            pressed: false,
            modifiers: egui::Modifiers::NONE,
        }],
    );
    assert!(pick.unwrap().uv.distance(egui::pos2(0.75, 0.25)) < 0.001);
    assert!(PipelineProgress::default().analysis_size.is_none());
}

#[test]
fn numeric_probe_inverts_the_producer_scale_and_binary_support_without_guessing_weights() {
    let mut sample = packet(1, 0, DiagnosticKind::FocusEnergy);
    sample.pixels = Arc::from([0, 128, 255, 0]);
    assert_eq!(value_at(&sample, egui::pos2(0.0, 0.0)), Some(0.0));
    assert!((value_at(&sample, egui::pos2(0.0, 0.75)).unwrap() - 255.0).abs() < 0.001);
    let mid = value_at(&sample, egui::pos2(0.75, 0.0)).unwrap();
    assert!(
        mid > 15.0 && mid < 15.3,
        "log-encoded midpoint is near15 DN², not128 DN²"
    );
    let support = packet(2, 0, DiagnosticKind::GateSupport);
    assert_eq!(value_at(&support, egui::pos2(0.75, 0.0)), Some(1.0));
    assert_eq!(value_at(&support, egui::pos2(0.0, 0.0)), Some(0.0));
    let signed = packet(3, 0, DiagnosticKind::Coefficient);
    assert!((value_at(&signed, egui::pos2(0.0, 0.0)).unwrap() + 255.0).abs() < 0.001);
    assert!((value_at(&signed, egui::pos2(0.75, 0.0)).unwrap() - 255.0).abs() < 0.001);
}

#[test]
fn binary_maps_keep_real_coarse_sample_positions_and_shared_zoom_without_full_grid_fills() {
    let ctx = egui::Context::default();
    let samples = Samples::new(&ctx, 7, 1);
    let surfaces = samples.surfaces();
    let mut progress = PipelineProgress::default();
    progress.bands = Some(7);
    progress.plane_size = Some([400, 300]);
    let size = egui::vec2(784.0, 650.0);
    let layout = Layout::new(Rect::from_min_size(Pos2::ZERO, size), 8);
    let fitted = fit(egui::vec2(400.0, 300.0), map_aperture(layout.cell(6, 2)));
    let mut scales = ProcessScales::default();
    for (time, zoom) in [(0.0, 1.0), (0.5, 4.0)] {
        scales.set_view(egui::pos2(0.8, 0.3), zoom);
        let (_, output) = draw(
            &ctx,
            &mut scales,
            size,
            input(&progress, &surfaces),
            time,
            vec![],
        );
        let snapshot = scales.get(6, DiagnosticKind::GateSupport).unwrap();
        assert!(image_meshes(&output, snapshot.texture.id()).is_empty());
        let uv = scales.aperture();
        //400→200→100→50→25→13→7; the transmitted right sample
        //reads coefficient5, rooted at320. The vertical sample reads1*64.
        let expected = fitted.min
            + (egui::vec2(320.5 / 400.0, 64.5 / 300.0) - uv.min.to_vec2()) / uv.size()
                * fitted.size();
        crate::process_sample_glyphs::assert_painted_samples(
            &output,
            fitted,
            uv,
            snapshot.packet.as_ref().unwrap(),
            [400, 300],
        );
        let markers: Vec<_> = crate::process_result::overlay_marker_centers(&output)
            .into_iter()
            .filter(|point| fitted.contains(*point))
            .collect();
        assert!(
            markers.iter().any(|point| point.distance(expected) < 0.001),
            "the same coarse observation must stay attached through shared zoom"
        );
        let old_uniform =
            fitted.min + (egui::vec2(0.75, 0.25) - uv.min.to_vec2()) / uv.size() * fitted.size();
        assert!(
            old_uniform.distance(expected) > 2.0,
            "negative control must expose the telemetry-bin displacement"
        );
    }
}

#[test]
fn accumulation_ports_remain_attached_to_actual_map_pixels_during_resize() {
    let ctx = egui::Context::default();
    let samples = Samples::new(&ctx, 7, 1);
    let surfaces = samples.surfaces();
    let mut progress = PipelineProgress::default();
    progress.bands = Some(7);
    progress.plane_size = Some([400, 300]);
    let mut scales = ProcessScales::default();
    let mut detached_old_ports = 0;
    for (step, size) in [
        egui::vec2(382.0, 620.0),
        egui::vec2(784.0, 650.0),
        egui::vec2(1000.0, 420.0),
    ]
    .into_iter()
    .enumerate()
    {
        let (_, output) = draw(
            &ctx,
            &mut scales,
            size,
            input(&progress, &surfaces),
            step as f64,
            vec![],
        );
        let layout = Layout::new(Rect::from_min_size(Pos2::ZERO, size), 8);
        for port in scales.output_ports() {
            let snapshot = scales.get(port.level, DiagnosticKind::Coefficient).unwrap();
            let mesh = image_meshes(&output, snapshot.texture.id())[0];
            let pixels =
                Rect::from_points(&mesh.vertices.iter().map(|v| v.pos).collect::<Vec<_>>());
            assert!(port.position.distance(pixels.right_center()) < 0.001);
            detached_old_ports += usize::from(
                layout
                    .cell(port.level, 4)
                    .right_center()
                    .distance(port.position)
                    > 2.0,
            );
        }
    }
    assert!(
        detached_old_ports > 0,
        "negative control must expose the cell edge / image edge mismatch"
    );
}

#[test]
fn fallback_branch_has_a_local_gated_operator_without_the_long_skip_line() {
    let ctx = egui::Context::default();
    let samples = Samples::new(&ctx, 7, 1);
    let surfaces = samples.surfaces();
    let mut progress = PipelineProgress::default();
    progress.bands = Some(7);
    let mut scales = ProcessScales::default();
    for (step, size) in [egui::vec2(382.0, 620.0), egui::vec2(784.0, 650.0)]
        .into_iter()
        .enumerate()
    {
        let (_, output) = draw(
            &ctx,
            &mut scales,
            size,
            input(&progress, &surfaces),
            step as f64,
            vec![],
        );
        let layout = Layout::new(Rect::from_min_size(Pos2::ZERO, size), 8);
        for level in 0..8 {
            let admitted = layout.cell(level, 2);
            let fallback = layout.cell(level, 3);
            let gate = egui::pos2(
                (admitted.right() + fallback.left()) * 0.5,
                admitted.center().y,
            );
            assert!(output.shapes.iter().any(|shape| matches!(&shape.shape,
                egui::Shape::Circle(circle) if circle.center == gate && circle.radius == 3.0 && circle.stroke.width <= 1.0)));
            let former_branch_y = layout.row(level).bottom() - 2.0;
            assert!(!output.shapes.iter().any(|shape| matches!(&shape.shape,
                egui::Shape::LineSegment {points, ..} if (points[0].y - former_branch_y).abs() < 0.01
                    && (points[1].y - former_branch_y).abs() < 0.01
                    && (points[1].x - points[0].x).abs() > fallback.width())));
        }
    }
}

#[test]
fn double_clicking_a_detail_resets_instead_of_trapping_the_photo_in_a_map() {
    let ctx = egui::Context::default();
    let samples = Samples::new(&ctx, 7, 1);
    let surfaces = samples.surfaces();
    let mut progress = PipelineProgress::default();
    progress.bands = Some(7);
    let mut scales = ProcessScales::default();
    let size = egui::vec2(784.0, 650.0);
    let (_, initial) = draw(
        &ctx,
        &mut scales,
        size,
        input(&progress, &surfaces),
        0.0,
        vec![],
    );
    scales.set_view(egui::pos2(0.65, 0.35), 4.0);
    let mesh = image_meshes(&initial, samples.textures[0].id())[0];
    let target =
        Rect::from_points(&mesh.vertices.iter().map(|v| v.pos).collect::<Vec<_>>()).center();
    let mut saw_reset = false;
    for (time, pressed) in [(0.1, true), (0.12, false), (0.2, true), (0.22, false)] {
        let (pick, _) = draw(
            &ctx,
            &mut scales,
            size,
            input(&progress, &surfaces),
            time,
            vec![egui::Event::PointerMoved(target), pointer(target, pressed)],
        );
        if let Some(pick) = pick {
            assert!(!pick.enlarge);
            saw_reset |= pick.reset;
        }
    }
    assert!(
        saw_reset,
        "fixture must dispatch the actual egui double click"
    );
    let _ = draw(
        &ctx,
        &mut scales,
        size,
        input(&progress, &surfaces),
        0.6,
        vec![],
    );
    assert_eq!(scales.detail_zoom(), 1.0);
    assert_eq!(scales.pin(), egui::pos2(0.5, 0.5));
    assert!(scales.selected.is_none());
}

#[test]
fn navigation_history_captures_intent_once_while_zoom_animation_advances() {
    let mut scales = ProcessScales::default();
    scales.set_view(egui::pos2(0.5, 0.5), 4.0);
    scales.painted_aperture = view_aperture(scales.pin, 4.0);
    let before = scales.view();
    scales.zoom_at(2.0, egui::pos2(0.25, 0.75));
    let destination = scales.view();
    assert_ne!(before, destination);
    for now in [0.02, 0.06, 0.1, 0.2, 0.3] {
        scales.advance_view(now);
        assert_eq!(
            scales.view(),
            destination,
            "animation cannot create extra undo entries"
        );
    }
    scales.restore_view(before);
    assert_eq!(scales.view(), before);
    scales.reset_view();
    let fit = scales.view();
    for now in [0.31, 0.4, 0.6] {
        scales.advance_view(now);
        assert_eq!(scales.view(), fit);
    }
}
