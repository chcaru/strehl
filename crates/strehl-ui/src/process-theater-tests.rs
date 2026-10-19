use super::*;
use crate::{
    pipeline::{DiagnosticScope, DiagnosticSurface, PipelineProgress},
    process_space::Surface,
    workbench::SourcePhoto,
};

fn texture(ctx: &egui::Context, name: &str, size: [usize; 2]) -> TextureHandle {
    ctx.load_texture(
        name,
        egui::ColorImage::new(size, vec![Color32::GRAY; size[0] * size[1]]),
        egui::TextureOptions::NEAREST,
    )
}
fn input(progress: &PipelineProgress) -> Input<'_> {
    Input {
        epoch: 1,
        progress,
        frame_count: 10,
        selected: 2,
        inspected_pair: None,
        photos: &[],
        inspection_photos: &[],
        surfaces: &[],
        output: None,
        output_size: None,
    }
}
fn draw(
    field: &mut ProcessTheater,
    ctx: &egui::Context,
    input: Input<'_>,
    size: [f32; 2],
    time: f64,
    events: Vec<egui::Event>,
) -> (Response, egui::FullOutput) {
    let mut response = Response::default();
    let output = ctx.run(
        egui::RawInput {
            screen_rect: Some(Rect::from_min_size(Pos2::ZERO, size.into())),
            time: Some(time),
            events,
            ..Default::default()
        },
        |ctx| {
            egui::CentralPanel::default()
                .frame(egui::Frame::NONE)
                .show(ctx, |ui| {
                    let rect = ui.max_rect();
                    field.show(ui, rect, &input, &mut response);
                });
        },
    );
    (response, output)
}
fn bounds(output: &egui::FullOutput, id: egui::TextureId) -> Vec<(Rect, u8)> {
    output
        .shapes
        .iter()
        .filter_map(|shape| match &shape.shape {
            egui::Shape::Mesh(mesh) if mesh.texture_id == id && !mesh.vertices.is_empty() => {
                Some((
                    Rect::from_points(
                        &mesh
                            .vertices
                            .iter()
                            .map(|vertex| vertex.pos)
                            .collect::<Vec<_>>(),
                    ),
                    mesh.vertices[0].color.a(),
                ))
            }
            _ => None,
        })
        .collect()
}
fn has(output: &egui::FullOutput, text: &str) -> bool {
    output.shapes.iter().any(
        |shape| matches!(&shape.shape, egui::Shape::Text(value) if value.galley.text() == text),
    )
}
fn map_pane(output: &egui::FullOutput, textures: &[TextureHandle], index: usize) -> Rect {
    if !matches!(index, 2 | 3) {
        return bounds(output, textures[index].id())[0].0;
    }
    let first = bounds(output, textures[0].id())[0].0;
    let second = bounds(output, textures[1].id())[0].0;
    let expected = first.translate((second.center() - first.center()) * index as f32);
    output
        .shapes
        .iter()
        .find_map(|shape| match &shape.shape {
            egui::Shape::Rect(rect)
                if rect.fill == crate::theme::BG
                    && rect.rect.min.distance(expected.min) < 0.01
                    && rect.rect.max.distance(expected.max) < 0.01 =>
            {
                Some(rect.rect)
            }
            _ => None,
        })
        .expect("the actual binary diagnostic pane must remain alongside the scalar maps")
}
fn maps_present(output: &egui::FullOutput, textures: &[TextureHandle]) -> bool {
    (0..textures.len()).all(|index| map_pane(output, textures, index).is_positive())
}

#[test]
fn photograph_heading_stays_anchored_while_real_merge_operations_interleave() {
    let ctx = egui::Context::default();
    let mut field = ProcessTheater::default();
    let mut progress = PipelineProgress::default();
    progress.ingest("STREHL_UI_PROGRESS event=stage name=merge total=10\n");
    let mut observed_steps = std::collections::BTreeSet::new();
    let mut heading_bounds = None;
    for (index, step) in ["decode", "pyramid", "focus", "fold", "decode"]
        .iter()
        .enumerate()
    {
        let level = if matches!(*step, "focus" | "fold") {
            "2"
        } else {
            "none"
        };
        progress.ingest(&format!("STREHL_UI_PROGRESS event=merge-step name={step} state=started index={index} level={level} total=10\n"));
        observed_steps.insert(progress.merge_step.unwrap() as u8);
        let (_, output) = draw(
            &mut field,
            &ctx,
            input(&progress),
            [1060.0, 600.0],
            index as f64 * 0.1,
            vec![],
        );
        let heading = output
            .shapes
            .iter()
            .find_map(|shape| match &shape.shape {
                egui::Shape::Text(text) if text.galley.text() == "Combining accepted frames" => {
                    Some(text.visual_bounding_rect())
                }
                _ => None,
            })
            .expect("the photograph subtitle must stay on the real merge phase");
        if let Some(previous) = heading_bounds {
            assert_eq!(heading, previous);
        }
        heading_bounds = Some(heading);
    }
    assert_eq!(
        observed_steps.len(),
        4,
        "fixture must actually change the engine operation"
    );
    progress.ingest("STREHL_UI_PROGRESS event=stage name=render total=10\n");
    assert_eq!(progress.stage, Stage::Rendering);
    let (_, output) = draw(
        &mut field,
        &ctx,
        input(&progress),
        [1060.0, 600.0],
        1.0,
        vec![],
    );
    assert!(has(&output, "Reconstructing + developing"));
    assert!(!has(&output, "Combining accepted frames"));
}

#[test]
fn contribution_lenses_share_the_cropped_stack_but_never_overlay_originals_or_saved_tiff() {
    let ctx = egui::Context::default();
    let mut field = ProcessTheater {
        level: 2,
        ..Default::default()
    };
    let mut progress = PipelineProgress::default();
    progress.stage = Stage::Merge;
    progress.plane_size = Some([900, 600]);
    progress.analysis_size = Some([200, 300]);
    let size = [1010.0, 490.0];
    let layout = Layout::new(Rect::from_min_size(Pos2::ZERO, size.into()));
    let camera = texture(&ctx, "unregistered-original", [90, 60]);
    let photos = [SourcePhoto {
        epoch: 1,
        index: 2,
        texture: camera.clone(),
        aperture: [900, 600],
    }];
    let packets: [DiagnosticSurface; 3] = std::array::from_fn(|i| DiagnosticSurface {
        sequence: i as u64 + 1,
        frame: 2,
        level: if i == 2 { 3 } else { 2 },
        kind: [
            DiagnosticKind::GateSupport,
            DiagnosticKind::Averaging,
            DiagnosticKind::Preview,
        ][i],
        scope: if i == 0 {
            DiagnosticScope::Frame
        } else {
            DiagnosticScope::Stack
        },
        scale: DiagnosticScale::Linear,
        width: 4,
        height: 6,
        min: 0.0,
        max: if i == 2 { 100.0 } else { 1.0 },
        folded: if i == 0 { 1 } else { 3 },
        pixels: std::sync::Arc::from(
            (0..24)
                .map(|j| if j % 2 == 0 { 0 } else { 255 })
                .collect::<Vec<_>>(),
        ),
    });
    let textures: [TextureHandle; 3] =
        std::array::from_fn(|i| texture(&ctx, &format!("cropped-map-{i}"), [4, 6]));
    let surfaces: [Surface<'_>; 3] = std::array::from_fn(|i| Surface {
        epoch: 1,
        stage: Stage::Merge,
        level: packets[i].level,
        texture: &textures[i],
        frame: (i == 0).then_some(2),
        packet: Some(&packets[i]),
        meta: Some(SurfaceMeta {
            sequence: packets[i].sequence,
            kind: packets[i].kind,
            scale: packets[i].scale,
            min: packets[i].min,
            max: packets[i].max,
            samples: [4, 6],
            folded: packets[i].folded,
        }),
    });
    let data = Input {
        inspection_photos: &photos,
        surfaces: &surfaces,
        ..input(&progress)
    };
    let _ = draw(&mut field, &ctx, data, size, 0.0, vec![]);
    field.level = 2;
    let (_, shown) = draw(&mut field, &ctx, data, size, 0.5, vec![]);
    let preview_id = field.preview_tone.as_ref().unwrap().1.id();
    let photograph = bounds(&shown, preview_id)
        .into_iter()
        .find(|(rect, _)| layout.hero.contains_rect(*rect))
        .unwrap()
        .0;
    assert!((photograph.aspect_ratio() - 2.0 / 3.0).abs() < 0.001);
    let lens_photos: Vec<_> = bounds(&shown, preview_id)
        .into_iter()
        .filter(|(rect, _)| layout.contributions.contains_rect(*rect))
        .collect();
    assert_eq!(lens_photos.len(), 2);
    assert!(
        lens_photos
            .iter()
            .all(|(rect, _)| (rect.aspect_ratio() - photograph.aspect_ratio()).abs() < 0.001)
    );
    assert!(
        bounds(&shown, camera.id())
            .iter()
            .all(|(rect, _)| !layout.contributions.intersects(*rect)),
        "camera pixels must never be treated as an aligned mask backdrop"
    );
    let mask_ids: Vec<_> = shown
        .shapes
        .iter()
        .filter_map(|shape| match &shape.shape {
            egui::Shape::Mesh(mesh)
                if mesh.texture_id != preview_id
                    && mesh.texture_id != egui::TextureId::default()
                    && layout.contributions.contains_rect(Rect::from_points(
                        &mesh.vertices.iter().map(|v| v.pos).collect::<Vec<_>>(),
                    )) =>
            {
                Some(mesh.texture_id)
            }
            _ => None,
        })
        .collect();
    assert!(
        mask_ids.is_empty(),
        "binary observations cannot become full-frame raster overlays"
    );
    for (index, (image, _)) in lens_photos.iter().enumerate() {
        crate::process_sample_glyphs::assert_painted_samples(
            &shown,
            *image,
            field.scales.aperture(),
            &packets[index],
            [200, 300],
        );
    }
    progress.mark_complete();
    let saved = texture(&ctx, "developed-tiff", [300, 200]);
    let data = Input {
        output: Some(&saved),
        surfaces: &surfaces,
        inspection_photos: &photos,
        ..input(&progress)
    };
    let _ = draw(&mut field, &ctx, data, size, 0.6, vec![]);
    let hover = layout.contributions.min + egui::vec2(layout.contributions.width() * 0.25, 40.0);
    let (_, complete) = draw(
        &mut field,
        &ctx,
        data,
        size,
        1.1,
        vec![egui::Event::PointerMoved(hover)],
    );
    let final_photo = bounds(&complete, saved.id())
        .into_iter()
        .find(|(rect, _)| layout.hero.contains_rect(*rect))
        .unwrap()
        .0;
    assert_eq!(field.hero.as_ref().unwrap().plate.kind, 3);
    for id in mask_ids {
        assert!(
            bounds(&complete, id)
                .iter()
                .all(|(rect, _)| layout.contributions.contains_rect(*rect))
        );
    }
    assert!(complete.shapes.iter().all(|shape| !matches!(&shape.shape, egui::Shape::Circle(circle) if final_photo.contains(circle.center))), "no diagnostic cursor or mask may contaminate the saved TIFF view");
}

fn maps(textures: &[TextureHandle; 5]) -> [Surface<'_>; 5] {
    std::array::from_fn(|index| Surface {
        epoch: 1,
        stage: Stage::Merge,
        level: 0,
        texture: &textures[index],
        frame: (index < 3).then_some(2),
        packet: None,
        meta: Some(SurfaceMeta {
            sequence: 20 + index as u64,
            kind: SIGNALS[index],
            scale: if index < 2 {
                DiagnosticScale::Log
            } else if index == 4 {
                DiagnosticScale::Symmetric
            } else {
                DiagnosticScale::Linear
            },
            min: if index == 4 { -10.0 } else { 0.0 },
            max: if matches!(index, 2 | 3) { 1.0 } else { 100.0 },
            samples: [6, 4],
            folded: if index < 3 { 1 } else { 3 },
        }),
    })
}
fn click(
    field: &mut ProcessTheater,
    ctx: &egui::Context,
    input: Input<'_>,
    size: [f32; 2],
    at: Pos2,
    time: f64,
) -> (Response, egui::FullOutput) {
    let button = |pressed| egui::Event::PointerButton {
        pos: at,
        button: egui::PointerButton::Primary,
        pressed,
        modifiers: egui::Modifiers::NONE,
    };
    let _ = draw(
        field,
        ctx,
        input,
        size,
        time,
        vec![egui::Event::PointerMoved(at), button(true)],
    );
    draw(field, ctx, input, size, time + 0.02, vec![button(false)])
}

fn inspect_large(
    field: &mut ProcessTheater,
    ctx: &egui::Context,
    input: Input<'_>,
    size: [f32; 2],
    at: Pos2,
    time: f64,
) -> egui::FullOutput {
    for (delta, pressed) in [(0.0, true), (0.005, false)] {
        draw(
            field,
            ctx,
            input,
            size,
            time + delta,
            vec![
                egui::Event::PointerMoved(at),
                egui::Event::PointerButton {
                    pos: at,
                    button: egui::PointerButton::Secondary,
                    pressed,
                    modifiers: egui::Modifiers::NONE,
                },
            ],
        );
    }
    let (_, menu) = draw(field, ctx, input, size, time + 0.01, vec![]);
    let target = menu
        .shapes
        .iter()
        .find_map(|s| match &s.shape {
            egui::Shape::Text(t) if t.galley.text() == "Inspect large" => {
                Some(t.visual_bounding_rect().center())
            }
            _ => None,
        })
        .expect("actual map context menu must expose large inspection");
    click(field, ctx, input, size, target, time + 0.015).1
}

#[test]
fn photo_anchor_is_stable_and_complete_promotes_actual_output_without_losing_maps() {
    for size in [[1010.0, 490.0], [1380.0, 720.0]] {
        let ctx = egui::Context::default();
        let mut field = ProcessTheater::default();
        let mut progress = PipelineProgress::default();
        progress.plane_size = Some([900, 600]);
        progress.stage = Stage::Alignment;
        let source = texture(&ctx, "canonical-camera", [90, 60]);
        let other = texture(&ctx, "distant-camera", [90, 60]);
        let native = texture(&ctx, "native-incompatible", [80, 60]);
        let photos = [
            SourcePhoto {
                epoch: 1,
                index: 2,
                texture: source.clone(),
                aperture: [900, 600],
            },
            SourcePhoto {
                epoch: 1,
                index: 9,
                texture: other.clone(),
                aperture: [900, 600],
            },
        ];
        // Capture2 still challenges the hero's same-index native/canonical
        // choice; capture3 is a visible ledger contact in compact layouts.
        let thumbs = [2, 3].map(|index| SourcePhoto {
            epoch: 1,
            index,
            texture: native.clone(),
            aperture: [80, 60],
        });
        let (_, first) = draw(
            &mut field,
            &ctx,
            Input {
                inspection_photos: &photos,
                photos: &thumbs,
                ..input(&progress)
            },
            size,
            0.0,
            vec![],
        );
        let initial = bounds(&first, source.id())
            .into_iter()
            .max_by(|a, b| a.0.area().total_cmp(&b.0.area()))
            .unwrap()
            .0;
        let layout = Layout::new(Rect::from_min_size(Pos2::ZERO, size.into()));
        assert!(
            layout.hero.contains_rect(initial)
                && initial.width() > layout.hero.width() * 0.85
                && initial.height() > 170.0,
            "photograph must fill its reserved region at the supported viewport"
        );
        assert!(
            !bounds(&first, native.id()).is_empty()
                && bounds(&first, native.id())
                    .iter()
                    .all(|(rect, _)| layout.network.contains_rect(*rect)
                        || layout.ledger.contains_rect(*rect))
                && bounds(&first, native.id())
                    .iter()
                    .any(|(rect, _)| layout.ledger.contains_rect(*rect)),
            "native contacts must paint in the retained contact regions, never the photograph"
        );
        progress.alignment_current_pair = Some([2, 9]);
        let (_, hopped) = draw(
            &mut field,
            &ctx,
            Input {
                selected: 9,
                inspection_photos: &photos,
                ..input(&progress)
            },
            size,
            0.2,
            vec![],
        );
        assert_eq!(field.source_index, Some(2));
        assert!(
            bounds(&hopped, source.id())
                .iter()
                .any(|(rect, _)| *rect == initial)
        );
        assert!(
            bounds(&hopped, other.id())
                .iter()
                .all(|(rect, _)| rect.width() < size[0] * 0.14
                    && rect.width() < initial.width() * 0.5),
            "active pair may change only the origin lens"
        );

        let textures: [TextureHandle; 5] =
            std::array::from_fn(|index| texture(&ctx, &format!("signal-{index}"), [6, 4]));
        let surfaces = maps(&textures);
        progress.stage = Stage::Merge;
        let (_, merge) = draw(
            &mut field,
            &ctx,
            Input {
                surfaces: &surfaces,
                ..input(&progress)
            },
            size,
            0.3,
            vec![],
        );
        assert!(
            maps_present(&merge, &textures),
            "all five maps must coexist"
        );
        assert!(
            field.hero.is_none(),
            "individual coefficients are not a photograph"
        );
        assert!(
            bounds(&merge, source.id())
                .iter()
                .any(|(rect, alpha)| *rect == initial && *alpha == 255)
        );
        field.enlarged = Some(DiagnosticKind::GateSupport);
        let output_texture = texture(&ctx, "actual-owned-tiff", [150, 100]);
        progress.mark_complete();
        let (_, arrived) = draw(
            &mut field,
            &ctx,
            Input {
                output: Some(&output_texture),
                ..input(&progress)
            },
            size,
            0.4,
            vec![],
        );
        assert!(has(&arrived, "PHOTOGRAPH COMPLETE"));
        assert_eq!(
            field.enlarged, None,
            "completion returns to actual photograph even from inspecting a map"
        );
        assert!(field.transitioning());
        // The actual TIFF automatically reveals over the stable camera context;
        // receiving individual scale coefficients never replaces that context.
        let _ = draw(&mut field, &ctx, input(&progress), size, 1.0, vec![]);
        let _ = draw(&mut field, &ctx, input(&progress), size, 1.02, vec![]);
        let (_, finished) = draw(&mut field, &ctx, input(&progress), size, 1.5, vec![]);
        assert!(!field.transitioning());
        let finished_plate = bounds(&finished, output_texture.id());
        assert!(
            finished_plate
                .iter()
                .any(|(rect, alpha)| rect.min.distance(initial.min) < 0.1
                    && rect.max.distance(initial.max) < 0.1
                    && *alpha == 255),
            "same-aperture TIFF must arrive fully opaque in the same frame without hover"
        );
        assert!(
            maps_present(&finished, &textures),
            "completion retains sampled diagnostic evidence"
        );
        let (_, imported) = draw(
            &mut field,
            &ctx,
            Input {
                epoch: 2,
                ..input(&PipelineProgress::default())
            },
            size,
            1.7,
            vec![],
        );
        assert!(bounds(&imported, output_texture.id()).is_empty());
        assert!(
            textures
                .iter()
                .all(|texture| bounds(&imported, texture.id()).is_empty())
        );
        assert!(field.observations.is_empty() && field.source_index.is_none());
    }
}

#[test]
fn map_pin_and_enlargement_are_interactive_without_claiming_camera_registration() {
    let ctx = egui::Context::default();
    let mut field = ProcessTheater::default();
    let mut progress = PipelineProgress::default();
    progress.plane_size = Some([900, 600]);
    progress.stage = Stage::Merge;
    let textures = std::array::from_fn(|index| texture(&ctx, &format!("pin-{index}"), [6, 4]));
    let surfaces = maps(&textures);
    let capture = texture(&ctx, "unregistered-original", [90, 60]);
    let photos = [SourcePhoto {
        epoch: 1,
        index: 2,
        texture: capture.clone(),
        aperture: [900, 600],
    }];
    let input = Input {
        surfaces: &surfaces,
        inspection_photos: &photos,
        ..input(&progress)
    };
    let size = [1010.0, 490.0];
    let (_, first) = draw(&mut field, &ctx, input, size, 0.0, vec![]);
    let support_rect = map_pane(&first, &textures, 2);
    let target = support_rect.min + support_rect.size() * egui::vec2(0.23, 0.71);
    let _ = click(&mut field, &ctx, input, size, target, 0.1);
    assert!((field.pin.x - 0.23).abs() < 0.01 && (field.pin.y - 0.71).abs() < 0.01);
    assert_eq!(field.selected_signal, DiagnosticKind::GateSupport);
    assert_eq!(
        field.enlarged, None,
        "single-click keeps the photograph visible"
    );
    click(&mut field, &ctx, input, size, target, 0.18);
    assert_eq!(
        field.enlarged, None,
        "double-click resets rather than entering an opaque mode"
    );
    let enlarged = inspect_large(&mut field, &ctx, input, size, target, 0.3);
    let layout = Layout::new(Rect::from_min_size(Pos2::ZERO, size.into()));
    assert_eq!(field.enlarged, Some(DiagnosticKind::GateSupport));
    assert!(
        bounds(&enlarged, textures[2].id())
            .iter()
            .any(|(rect, _)| layout.hero.contains_rect(*rect)
                && rect.width() > layout.hero.width() * 0.8)
    );
    assert!(maps_present(&enlarged, &textures));
    let back = egui::pos2(layout.hero.right() - 70.0, layout.hero.top() + 17.0);
    let _ = click(&mut field, &ctx, input, size, back, 0.5);
    assert_eq!(field.enlarged, None);
    let (_, returned) = draw(&mut field, &ctx, input, size, 0.6, vec![]);
    assert!(
        field.hero.is_none(),
        "an accumulated band must never claim to be the photograph"
    );
    assert!(has(&first, "CAMERA CONTEXT / FRAME 003"));
    let photo = bounds(&first, capture.id())
        .into_iter()
        .max_by(|a, b| a.0.area().total_cmp(&b.0.area()))
        .unwrap()
        .0;
    assert!(
        bounds(&returned, capture.id())
            .iter()
            .any(|(rect, alpha)| *rect == photo && *alpha == 255)
    );
    assert!(
        maps_present(&returned, &textures),
        "returning to the photograph must retain every measured map"
    );
}

#[test]
fn point_values_invert_real_transport_scales_and_expired_packets_are_not_relabelled() {
    use std::sync::Arc;
    let mut surface = DiagnosticSurface {
        sequence: 44,
        frame: 2,
        level: 0,
        kind: DiagnosticKind::FocusEnergy,
        scope: DiagnosticScope::Frame,
        scale: DiagnosticScale::Log,
        width: 3,
        height: 1,
        min: 0.0,
        max: 255.0,
        pixels: Arc::from([0, 128, 255]),
        folded: 1,
    };
    assert_eq!(sample_value(&surface, egui::pos2(0.0, 0.5)), Some(0.0));
    let middle = sample_value(&surface, egui::pos2(0.5, 0.5)).unwrap();
    assert!(
        middle > 15.0 && middle < 15.5,
        "log midpoint is about fifteen DN², not half the255DN² maximum"
    );
    assert!((sample_value(&surface, egui::pos2(1.0, 0.5)).unwrap() - 255.0).abs() < 0.001);
    surface.kind = DiagnosticKind::Coefficient;
    surface.scope = DiagnosticScope::Stack;
    surface.scale = DiagnosticScale::Symmetric;
    surface.min = -255.0;
    assert!(sample_value(&surface, egui::pos2(0.0, 0.5)).unwrap() < -254.9);
    assert!(
        sample_value(&surface, egui::pos2(0.5, 0.5)).unwrap().abs() < 0.1,
        "signed-log midpoint must stay near neutral"
    );
    surface.scale = DiagnosticScale::Linear;
    surface.min = 10.0;
    surface.max = 110.0;
    assert!((sample_value(&surface, egui::pos2(0.5, 0.5)).unwrap() - 60.2).abs() < 0.1);

    let ctx = egui::Context::default();
    let mut field = ProcessTheater::default();
    let textures = std::array::from_fn(|index| texture(&ctx, &format!("expired-{index}"), [6, 4]));
    let surfaces = maps(&textures);
    let mut progress = PipelineProgress::default();
    // Same kind but a different sequence cannot provide a number for retained pixels.
    surface.sequence = 999;
    progress.diagnostic_surfaces.push_back(surface);
    let (_, output) = draw(
        &mut field,
        &ctx,
        Input {
            surfaces: &surfaces,
            ..input(&progress)
        },
        [1010.0, 490.0],
        0.0,
        vec![],
    );
    assert!(
        field
            .observation(DiagnosticKind::Coefficient)
            .unwrap()
            .packet
            .is_none()
    );
    let presented = field.scales.presented_surfaces();
    let coefficient = presented
        .iter()
        .find(|item| item.meta.unwrap().kind == DiagnosticKind::Coefficient)
        .unwrap();
    assert_eq!(coefficient.meta.unwrap().sequence, 24);
    assert_eq!(coefficient.texture.id(), textures[4].id());
    assert!(
        coefficient.packet.is_none(),
        "an unrelated sequence cannot supply the map's physical value"
    );
    assert!(!bounds(&output, coefficient.texture.id()).is_empty());
    assert!(
        presented
            .iter()
            .filter(|item| item.frame.is_some())
            .all(|item| item.frame == Some(2))
    );
    let mut skew = surfaces;
    skew[2].frame = Some(7);
    skew[2].meta.as_mut().unwrap().sequence = 30;
    let (_, output) = draw(
        &mut field,
        &ctx,
        Input {
            surfaces: &skew,
            ..input(&progress)
        },
        [1010.0, 490.0],
        0.2,
        vec![],
    );
    let presented = field.scales.presented_surfaces();
    let energy = presented
        .iter()
        .find(|item| item.meta.unwrap().kind == DiagnosticKind::FocusEnergy)
        .unwrap();
    let support = presented
        .iter()
        .find(|item| item.meta.unwrap().kind == DiagnosticKind::GateSupport)
        .unwrap();
    assert_eq!(energy.frame, Some(2));
    assert_eq!(support.frame, Some(7));
    assert_eq!(support.meta.unwrap().sequence, 30);
    assert!(energy.packet.is_none() && support.packet.is_none());
    assert!(
        bounds(&output, support.texture.id()).is_empty(),
        "an expired packet cannot authorize a spatially filled mask"
    );
    assert!(map_pane(&output, &textures, 2).is_positive());
}

#[test]
fn sparse_scale_work_and_pair_memory_stay_visible_across_phases() {
    let ctx = egui::Context::default();
    let mut field = ProcessTheater::default();
    let mut progress = PipelineProgress::default();
    progress.ingest("STREHL_UI_PROGRESS event=stage name=alignment total=10\nSTREHL_UI_PROGRESS event=align-phase name=pairs frames=10 total=20\nSTREHL_UI_PROGRESS event=align-pair i=1 j=9 completed=1 accepted=1 frames=10 total=20\nSTREHL_UI_PROGRESS event=merge-step index=9 name=focus state=started level=3 total=10\nSTREHL_UI_PROGRESS event=merge-step index=9 name=fold state=finished level=3 total=10\n");
    assert_eq!(progress.alignment_edge_observations.len(), 1);
    assert!(
        progress.merge_frame_observations[&9]
            .fold_state(3)
            .is_some()
    );
    let size = [1010.0, 490.0];
    let (_, output) = draw(&mut field, &ctx, input(&progress), size, 0.0, vec![]);
    assert!(
        has(&output, "CAPTURES / DIRECT FITS") && has(&output, "HOW DETAIL BECOMES THE PHOTOGRAPH")
    );
    assert!(has(&output, "Edges"));
    let layout = Layout::new(Rect::from_min_size(Pos2::ZERO, size.into()));
    let plot = crate::process_network::diagram_rect(layout.network);
    let endpoint = |frame| crate::process_network::position(plot, frame, 10);
    let endpoints = [endpoint(1), endpoint(9)];
    assert!(
        output.shapes.iter().any(|shape| matches!(&shape.shape,
        egui::Shape::LineSegment { points, .. } if *points == endpoints)),
        "the selectable direct pair must actually be painted"
    );
    // Choose the real edge's interior, outside the tighter node target but
    // within the broad drag-ring region. The line must win this ambiguous
    // outer-graph hit; otherwise short-baseline fits become unselectable.
    let point = endpoints[0].lerp(endpoints[1], 0.25);
    assert!((0..10).all(|frame| endpoint(frame).distance(point) > 5.0));
    let ring_radius = endpoint(0).distance(plot.center());
    assert!(
        (point.distance(plot.center()) - ring_radius).abs() < 8.0,
        "negative control: the broader ring-first hit rule must intercept this actual edge click"
    );
    let (chosen, _) = click(&mut field, &ctx, input(&progress), size, point, 0.2);
    assert_eq!(chosen.compare_pair, Some([1, 9]));
    let (blank, _) = click(&mut field, &ctx, input(&progress), size, plot.center(), 0.4);
    assert_eq!(
        blank.compare_pair, None,
        "blank capture-network space must never invent a comparison"
    );
    progress.mark_complete();
    let (_, complete) = draw(&mut field, &ctx, input(&progress), size, 0.6, vec![]);
    assert!(
        has(&complete, "CAPTURES / DIRECT FITS")
            && has(&complete, "HOW DETAIL BECOMES THE PHOTOGRAPH")
    );
    assert_eq!(
        progress.merge_frame_observations.len(),
        1,
        "sparse events must not fabricate earlier completed captures"
    );
}

#[test]
fn detail_and_base_scales_remain_distinct_and_explicit_capture_inspection_reaches_pixels() {
    let ctx = egui::Context::default();
    let mut field = ProcessTheater::default();
    let mut progress = PipelineProgress::default();
    progress.bands = Some(7);
    let size = [1010.0, 490.0];
    let _ = draw(&mut field, &ctx, input(&progress), size, 0.0, vec![]);
    assert_eq!(
        field.levels(&input(&progress)),
        8,
        "seven detail bands include a separate eighth base plane"
    );
    field.level = 6;
    let (_, detail) = draw(&mut field, &ctx, input(&progress), size, 0.1, vec![]);
    field.level = 7;
    let (_, base) = draw(&mut field, &ctx, input(&progress), size, 0.2, vec![]);
    for output in [&detail, &base] {
        for label in [
            "Fine texture",
            "Texture",
            "Small edges",
            "Edges",
            "Small forms",
            "Forms",
            "Broad forms",
            "Broad tone",
        ] {
            assert!(
                has(output, label),
                "selecting a scale must not hide the other scale rows: {label}"
            );
        }
        assert!(
            has(output, "not elected"),
            "broad tone must remain distinct from focus-elected detail"
        );
    }

    let initial = texture(&ctx, "initial-original", [90, 60]);
    let inspected = texture(&ctx, "explicit-capture-seven", [90, 60]);
    let photos = [
        SourcePhoto {
            epoch: 1,
            index: 2,
            texture: initial.clone(),
            aperture: [900, 600],
        },
        SourcePhoto {
            epoch: 1,
            index: 7,
            texture: inspected.clone(),
            aperture: [900, 600],
        },
    ];
    let input = Input {
        inspection_photos: &photos,
        ..input(&progress)
    };
    let _ = draw(&mut field, &ctx, input, size, 0.3, vec![]);
    field.inspect_frame(7);
    let (_, changed) = draw(&mut field, &ctx, input, size, 0.4, vec![]);
    assert!(has(&changed, "INSPECTED SOURCE"));
    assert!(
        !bounds(&changed, inspected.id()).is_empty(),
        "explicit capture choices must paint that capture rather than only moving an ordinal"
    );
    assert_eq!(
        field.source_index,
        Some(2),
        "passive photo anchor is independent of explicit context inspection"
    );
    field.resume_live();
    let (_, live) = draw(&mut field, &ctx, input, size, 0.5, vec![]);
    assert!(!has(&live, "INSPECTED SOURCE"));
}

#[test]
fn packet_values_survive_eviction_and_camera_stays_anchored_through_coefficient_updates() {
    use std::sync::Arc;
    let ctx = egui::Context::default();
    ctx.style_mut(|style| style.interaction.tooltip_delay = 0.0);
    let mut field = ProcessTheater::default();
    let mut progress = PipelineProgress::default();
    progress.stage = Stage::Merge;
    progress.plane_size = Some([900, 600]);
    let camera = texture(&ctx, "stable-camera-during-merge", [90, 60]);
    let photos = [SourcePhoto {
        epoch: 1,
        index: 2,
        texture: camera.clone(),
        aperture: [900, 600],
    }];
    let textures = std::array::from_fn(|index| texture(&ctx, &format!("packet-{index}"), [6, 4]));
    let mut surfaces = maps(&textures);
    let packet = DiagnosticSurface {
        sequence: 20,
        frame: 2,
        level: 0,
        kind: DiagnosticKind::FocusEnergy,
        scope: DiagnosticScope::Frame,
        scale: DiagnosticScale::Log,
        width: 6,
        height: 4,
        min: 0.0,
        max: 255.0,
        pixels: Arc::from([128; 24]),
        folded: 1,
    };
    progress.diagnostic_surfaces.push_back(packet.clone());
    surfaces[0].packet = Some(&packet);
    surfaces[0].meta.as_mut().unwrap().max = packet.max;
    let (_, first) = draw(
        &mut field,
        &ctx,
        Input {
            surfaces: &surfaces,
            inspection_photos: &photos,
            ..input(&progress)
        },
        [1010.0, 490.0],
        0.0,
        vec![],
    );
    let camera_rect = bounds(&first, camera.id())
        .into_iter()
        .max_by(|a, b| a.0.area().total_cmp(&b.0.area()))
        .unwrap()
        .0;
    let coefficient_rect = bounds(&first, textures[4].id())[0].0;
    assert!(
        camera_rect.width()
            > Layout::new(Rect::from_min_size(Pos2::ZERO, egui::vec2(1010.0, 490.0)))
                .hero
                .width()
                * 0.85
            && coefficient_rect.width() < camera_rect.width() * 0.25,
        "fixture must distinguish the full camera context from a small measured coefficient map"
    );
    progress.diagnostic_surfaces.clear();
    let (_, retained) = draw(
        &mut field,
        &ctx,
        input(&progress),
        [1010.0, 490.0],
        0.5,
        vec![],
    );
    let presented = field.scales.presented_surfaces();
    let energy = presented
        .iter()
        .find(|item| item.meta.unwrap().kind == DiagnosticKind::FocusEnergy)
        .unwrap();
    assert_eq!(energy.texture.id(), textures[0].id());
    assert_eq!(energy.meta.unwrap().sequence, packet.sequence);
    let retained_packet = energy
        .packet
        .expect("matching values must survive recent queue eviction");
    assert_eq!(retained_packet.sequence, packet.sequence);
    assert_eq!(&*retained_packet.pixels, &[128; 24]);
    let reading = sample_value(retained_packet, field.pin).unwrap();
    assert!(
        (15.0..15.5).contains(&reading),
        "the retained log sample is about15DN², not128DN²"
    );
    let hover = bounds(&retained, textures[0].id())[0].0.center();
    for time in [0.51, 0.52] {
        let _ = draw(
            &mut field,
            &ctx,
            input(&progress),
            [1010.0, 490.0],
            time,
            vec![egui::Event::PointerMoved(hover)],
        );
    }
    let (_, tooltip) = draw(
        &mut field,
        &ctx,
        input(&progress),
        [1010.0, 490.0],
        0.53,
        vec![],
    );
    assert!(
        tooltip.shapes.iter().any(|shape| matches!(&shape.shape,
        egui::Shape::Text(text) if text.galley.text().contains("Nearest observed sample: ≈ 1.517e1 DN²"))),
        "the actual map hover must show the physical value from its retained matching packet"
    );

    let replacement = texture(&ctx, "new-band-generation", [6, 4]);
    let mut next = surfaces[4];
    next.texture = &replacement;
    next.meta.as_mut().unwrap().sequence = 100;
    let newer = [next];
    let (_, start) = draw(
        &mut field,
        &ctx,
        Input {
            surfaces: &newer,
            ..input(&progress)
        },
        [1010.0, 490.0],
        0.6,
        vec![],
    );
    let old_opaque = bounds(&start, textures[4].id())
        .iter()
        .any(|(rect, alpha)| *rect == coefficient_rect && *alpha == 255);
    let new_transparent = bounds(&start, replacement.id())
        .iter()
        .any(|(rect, alpha)| *rect == coefficient_rect && *alpha == 0);
    assert!(
        old_opaque && new_transparent && field.transitioning(),
        "previous measured pixels must remain opaque underneath the newly delivered generation"
    );
    let (_, middle) = draw(
        &mut field,
        &ctx,
        input(&progress),
        [1010.0, 490.0],
        0.7,
        vec![],
    );
    assert!(
        bounds(&middle, replacement.id())
            .iter()
            .any(|(rect, alpha)| *rect == coefficient_rect && *alpha > 80 && *alpha < 180)
    );
    let (_, finished) = draw(
        &mut field,
        &ctx,
        input(&progress),
        [1010.0, 490.0],
        1.1,
        vec![],
    );
    assert!(!field.transitioning());
    assert!(
        bounds(&finished, replacement.id())
            .iter()
            .any(|(rect, alpha)| *rect == coefficient_rect && *alpha == 255)
    );
    assert!(
        field.hero.is_none(),
        "coefficient updates cannot replace camera context before reconstruction"
    );
    for output in [&first, &retained, &start, &middle, &finished] {
        assert!(
            bounds(output, camera.id())
                .iter()
                .any(|(rect, alpha)| *rect == camera_rect && *alpha == 255),
            "camera context must retain its pixels, extent and opacity across every coefficient update"
        );
        assert!(
            maps_present(output, &textures[..4]),
            "an updated coefficient must not hide its other measured inputs"
        );
    }
}

#[test]
fn live_composite_keeps_its_aperture_and_detail_until_owned_tiff_automatically_arrives() {
    use std::sync::Arc;
    let ctx = egui::Context::default();
    let mut field = ProcessTheater::default();
    let mut progress = PipelineProgress::default();
    progress.stage = Stage::Merge;
    progress.plane_size = Some([900, 600]);
    let size = [1010.0, 490.0];
    let camera = texture(&ctx, "coarse-preview-camera", [90, 60]);
    let photos = [SourcePhoto {
        epoch: 1,
        index: 2,
        texture: camera.clone(),
        aperture: [900, 600],
    }];
    let map_textures =
        std::array::from_fn(|index| texture(&ctx, &format!("coarse-preview-map-{index}"), [6, 4]));
    let surfaces = maps(&map_textures);
    let (_, camera_frame) = draw(
        &mut field,
        &ctx,
        Input {
            inspection_photos: &photos,
            surfaces: &surfaces,
            ..input(&progress)
        },
        size,
        0.0,
        vec![],
    );
    let aperture = bounds(&camera_frame, camera.id())
        .into_iter()
        .max_by(|a, b| a.0.area().total_cmp(&b.0.area()))
        .unwrap()
        .0;
    let coarse_texture = texture(&ctx, "actual-coarse-packet", [96, 64]);
    let packet = DiagnosticSurface {
        sequence: 80,
        frame: 8,
        level: 3,
        kind: DiagnosticKind::Preview,
        scope: DiagnosticScope::Stack,
        scale: DiagnosticScale::Linear,
        width: 96,
        height: 64,
        min: 0.0,
        max: 255.0,
        pixels: Arc::from(vec![223; 96 * 64]),
        folded: 3,
    };
    let preview = [Surface {
        epoch: 1,
        stage: Stage::Merge,
        level: packet.level,
        texture: &coarse_texture,
        frame: None,
        packet: Some(&packet),
        meta: Some(SurfaceMeta {
            sequence: packet.sequence,
            kind: packet.kind,
            scale: packet.scale,
            min: packet.min,
            max: packet.max,
            samples: [packet.width, packet.height],
            folded: packet.folded,
        }),
    }];
    let (_, arriving) = draw(
        &mut field,
        &ctx,
        Input {
            surfaces: &preview,
            ..input(&progress)
        },
        size,
        0.2,
        vec![],
    );
    let hero = field
        .hero
        .as_ref()
        .expect("an actual composite packet must become a live photograph preview");
    assert_eq!(hero.plate.kind, 1);
    assert_eq!(
        hero.plate.folded, 3,
        "fold count is observed contributions, never latest frame ordinal + 1"
    );
    assert_eq!(hero.plate.extent, egui::vec2(900.0, 600.0));
    let live_texture = hero.plate.texture.id();
    assert!(
        bounds(&arriving, camera.id())
            .iter()
            .any(|(rect, alpha)| *rect == aperture && *alpha == 255)
    );
    assert!(
        bounds(&arriving, live_texture)
            .iter()
            .any(|(rect, alpha)| *rect == aperture && *alpha == 0)
    );
    let (_, revealed) = draw(&mut field, &ctx, input(&progress), size, 0.7, vec![]);
    assert!(
        bounds(&revealed, live_texture)
            .iter()
            .any(|(rect, alpha)| *rect == aperture && *alpha == 255)
    );

    progress.stage = Stage::Rendering;
    let tiny_reconstruction = texture(&ctx, "lower-resolution-reconstruction", [12, 8]);
    let reconstructed = [Surface {
        epoch: 1,
        stage: Stage::Rendering,
        level: 0,
        texture: &tiny_reconstruction,
        frame: None,
        packet: None,
        meta: Some(SurfaceMeta {
            sequence: 100,
            kind: DiagnosticKind::Reconstructed,
            scale: DiagnosticScale::Linear,
            min: 0.0,
            max: 255.0,
            samples: [12, 8],
            folded: 10,
        }),
    }];
    let (_, rendering) = draw(
        &mut field,
        &ctx,
        Input {
            surfaces: &reconstructed,
            ..input(&progress)
        },
        size,
        0.8,
        vec![],
    );
    assert_eq!(
        field.hero.as_ref().unwrap().plate.kind,
        1,
        "a later stage must not replace the photograph with a visibly coarser diagnostic sample"
    );
    progress.mark_complete();
    let (_, pending_decode) = draw(&mut field, &ctx, input(&progress), size, 1.3, vec![]);
    for frame in [&rendering, &pending_decode] {
        assert!(
            bounds(frame, live_texture)
                .iter()
                .any(|(rect, alpha)| *rect == aperture && *alpha == 255)
        );
        assert!(
            bounds(frame, tiny_reconstruction.id())
                .iter()
                .all(|(rect, _)| rect.width() < aperture.width() * 0.5)
        );
    }
    assert_eq!(field.hero.as_ref().unwrap().plate.kind, 1);
    let tiff = texture(&ctx, "owned-tiff-after-live-composite", [300, 200]);
    let (_, tiff_arrival) = draw(
        &mut field,
        &ctx,
        Input {
            output: Some(&tiff),
            ..input(&progress)
        },
        size,
        1.4,
        vec![],
    );
    assert_eq!(field.hero.as_ref().unwrap().plate.kind, 3);
    assert!(field.transitioning());
    assert!(
        bounds(&tiff_arrival, live_texture)
            .iter()
            .any(|(rect, alpha)| *rect == aperture && *alpha == 255)
    );
    let (_, saved) = draw(&mut field, &ctx, input(&progress), size, 1.9, vec![]);
    assert!(!field.transitioning());
    assert!(
        bounds(&saved, tiff.id())
            .iter()
            .any(|(rect, alpha)| *rect == aperture && *alpha == 255),
        "saved TIFF must promote without hover or further delivery in the same photograph aperture"
    );
    assert!(
        maps_present(&saved, &map_textures),
        "finished photograph must retain every measured input map"
    );
}

#[test]
fn live_preview_exposure_tracks_physical_values_instead_of_packet_extrema() {
    use std::sync::Arc;
    // These bytes encode the same independently known 0, 64, 128 DN in two
    // different linear packet ranges; their display exposure must be unchanged.
    let mut packet = DiagnosticSurface {
        sequence: 1,
        frame: 0,
        level: 3,
        kind: DiagnosticKind::Preview,
        scope: DiagnosticScope::Stack,
        scale: DiagnosticScale::Linear,
        width: 3,
        height: 1,
        min: 0.0,
        max: 255.0,
        pixels: Arc::from([0, 64, 128]),
        folded: 1,
    };
    let initial = preview_tone_image(&packet, (0.0, 255.0));
    packet.max = 510.0;
    packet.pixels = Arc::from([0, 32, 64]);
    let expanded_range = preview_tone_image(&packet, (0.0, 255.0));
    for (index, expected) in [0u8, 136, 186].into_iter().enumerate() {
        assert!(initial.pixels[index].r().abs_diff(expected) <= 1);
        assert!(
            expanded_range.pixels[index].r().abs_diff(expected) <= 1,
            "equal physical values must keep the same display exposure despite a changed transport range"
        );
        assert!(
            initial.pixels[index]
                .r()
                .abs_diff(expanded_range.pixels[index].r())
                <= 1
        );
    }
    let independently_stretched = preview_tone_image(&packet, (packet.min, packet.max));
    assert!(
        initial.pixels[2]
            .r()
            .abs_diff(independently_stretched.pixels[2].r())
            > 40,
        "fixture must reject the contrast-pumping per-packet stretch"
    );

    packet.scale = DiagnosticScale::Linear;
    packet.min = 20.0;
    packet.max = 20.0;
    packet.pixels = Arc::from([0, 128, 255]);
    let flat = preview_tone_image(&packet, (0.0, 255.0));
    assert!(
        flat.pixels.iter().all(|pixel| *pixel == flat.pixels[0]),
        "a physically flat packet must never acquire spatial contrast from its transport bytes"
    );
    assert!(
        (75..=85).contains(&flat.pixels[0].r()),
        "flat is displayed at its measured exposure, not forced black or white"
    );

    let ctx = egui::Context::default();
    let mut field = ProcessTheater::default();
    let mut progress = PipelineProgress::default();
    progress.stage = Stage::Merge;
    let transport = texture(&ctx, "initial-flat-preview", [3, 1]);
    let flat_packet = packet.clone();
    let flat_surface = [Surface {
        epoch: 1,
        stage: Stage::Merge,
        level: flat_packet.level,
        texture: &transport,
        frame: None,
        packet: Some(&flat_packet),
        meta: Some(SurfaceMeta {
            sequence: flat_packet.sequence,
            kind: flat_packet.kind,
            scale: flat_packet.scale,
            min: flat_packet.min,
            max: flat_packet.max,
            samples: [3, 1],
            folded: flat_packet.folded,
        }),
    }];
    let _ = draw(
        &mut field,
        &ctx,
        Input {
            surfaces: &flat_surface,
            ..input(&progress)
        },
        [1010.0, 490.0],
        0.0,
        vec![],
    );
    assert!(
        field.hero.is_some(),
        "the flat fixture must exercise the real preview delivery path"
    );
    assert!(
        field.preview_range.is_none(),
        "a zero-span first packet cannot fix the exposure of later photographs"
    );
    packet.sequence += 1;
    packet.min = 0.0;
    packet.max = 255.0;
    packet.pixels = Arc::from([0, 64, 128]);
    let nonflat_surface = [Surface {
        packet: Some(&packet),
        meta: Some(SurfaceMeta {
            sequence: packet.sequence,
            kind: packet.kind,
            scale: packet.scale,
            min: packet.min,
            max: packet.max,
            samples: [3, 1],
            folded: packet.folded,
        }),
        ..flat_surface[0]
    }];
    let (_, delivered) = draw(
        &mut field,
        &ctx,
        Input {
            surfaces: &nonflat_surface,
            ..input(&progress)
        },
        [1010.0, 490.0],
        0.2,
        vec![],
    );
    assert_eq!(field.preview_range, Some((0.0, 255.0)));
    let tone = field.preview_tone.as_ref().unwrap();
    assert_eq!(tone.0, packet.sequence);
    assert!(
        delivered
            .textures_delta
            .set
            .iter()
            .any(|(id, _)| *id == tone.1.id()),
        "nonflat data must produce a newly toned texture, not reuse the initial flat display"
    );
}

#[test]
fn clicking_during_a_map_transition_inspects_the_presented_generation() {
    let ctx = egui::Context::default();
    let mut field = ProcessTheater::default();
    let mut progress = PipelineProgress::default();
    progress.stage = Stage::Merge;
    progress.plane_size = Some([900, 600]);
    let size = [1010.0, 490.0];
    let textures =
        std::array::from_fn(|index| texture(&ctx, &format!("deferred-signal-{index}"), [6, 4]));
    let surfaces = maps(&textures);
    let (_, first) = draw(
        &mut field,
        &ctx,
        Input {
            surfaces: &surfaces,
            ..input(&progress)
        },
        size,
        0.0,
        vec![],
    );
    let target = map_pane(&first, &textures, 2).center();
    let presented = texture(&ctx, "currently-revealing-support", [6, 4]);
    let future = texture(&ctx, "deferred-support", [6, 4]);
    let mut next = surfaces[2];
    next.texture = &presented;
    next.meta.as_mut().unwrap().sequence = 30;
    let transition = [next];
    let _ = draw(
        &mut field,
        &ctx,
        Input {
            surfaces: &transition,
            ..input(&progress)
        },
        size,
        0.1,
        vec![],
    );
    next.texture = &future;
    next.meta.as_mut().unwrap().sequence = 40;
    let deferred = [next];
    let _ = click(
        &mut field,
        &ctx,
        Input {
            surfaces: &deferred,
            ..input(&progress)
        },
        size,
        target,
        0.12,
    );
    assert_eq!(
        field.enlarged, None,
        "single-click keeps the photograph visible"
    );
    let clicked = inspect_large(
        &mut field,
        &ctx,
        Input {
            surfaces: &deferred,
            ..input(&progress)
        },
        size,
        target,
        0.15,
    );
    assert_eq!(field.enlarged, Some(DiagnosticKind::GateSupport));
    assert_eq!(
        field
            .observation(DiagnosticKind::GateSupport)
            .unwrap()
            .meta
            .sequence,
        30,
        "a newer transport packet cannot relabel the generation still being shown and clicked"
    );
    assert!(
        bounds(&clicked, presented.id()).iter().any(|(rect, _)| {
            let hero = Layout::new(Rect::from_min_size(Pos2::ZERO, size.into())).hero;
            hero.contains_rect(*rect) && rect.width() > hero.width() * 0.8
        }),
        "the actual inspected pixels must belong to the displayed generation"
    );
    assert!(
        bounds(&clicked, future.id()).is_empty(),
        "deferred pixels must not jump into the inspector ahead of their row"
    );
    let _ = draw(
        &mut field,
        &ctx,
        Input {
            surfaces: &deferred,
            ..input(&progress)
        },
        size,
        0.35,
        vec![],
    );
    let _ = draw(
        &mut field,
        &ctx,
        Input {
            surfaces: &deferred,
            ..input(&progress)
        },
        size,
        0.36,
        vec![],
    );
    assert_eq!(
        field
            .observation(DiagnosticKind::GateSupport)
            .unwrap()
            .meta
            .sequence,
        40,
        "once the bounded reveal completes, the same inspected signal advances to the delivered generation"
    );
}

#[test]
fn photograph_pixels_remain_clear_of_network_geometry_through_completion() {
    fn marks_inside(output: &egui::FullOutput, photograph: Rect) -> Vec<Rect> {
        output
            .shapes
            .iter()
            .filter_map(|shape| {
                if !matches!(
                    &shape.shape,
                    egui::Shape::Circle(_)
                        | egui::Shape::LineSegment { .. }
                        | egui::Shape::Path(_)
                        | egui::Shape::CubicBezier(_)
                        | egui::Shape::QuadraticBezier(_)
                ) {
                    return None;
                }
                let visible = shape
                    .shape
                    .visual_bounding_rect()
                    .intersect(shape.clip_rect)
                    .intersect(photograph.shrink(0.25));
                visible.is_positive().then_some(visible)
            })
            .collect()
    }
    let ctx = egui::Context::default();
    let mut field = ProcessTheater::default();
    let mut progress = PipelineProgress::default();
    progress.ingest("STREHL_UI_PROGRESS event=stage name=alignment total=10\nSTREHL_UI_PROGRESS event=align-phase name=pairs frames=10 total=20\nSTREHL_UI_PROGRESS event=align-pair i=1 j=9 completed=1 accepted=1 frames=10 total=20\n");
    progress.plane_size = Some([900, 600]);
    let camera = texture(&ctx, "unobstructed-camera", [90, 60]);
    let tiff = texture(&ctx, "unobstructed-owned-tiff", [900, 600]);
    let photos = [SourcePhoto {
        epoch: 1,
        index: 2,
        texture: camera.clone(),
        aperture: [900, 600],
    }];
    let map_textures =
        std::array::from_fn(|index| texture(&ctx, &format!("unobstructed-map-{index}"), [6, 4]));
    let surfaces = maps(&map_textures);
    let size = [1010.0, 490.0];
    let mut aperture = Rect::NOTHING;
    for (index, stage) in [Stage::Alignment, Stage::Merge, Stage::Complete]
        .into_iter()
        .enumerate()
    {
        progress.stage = stage;
        let (_, output) = draw(
            &mut field,
            &ctx,
            Input {
                inspection_photos: &photos,
                surfaces: if stage == Stage::Alignment {
                    &[]
                } else {
                    &surfaces
                },
                output: (stage == Stage::Complete).then_some(&tiff),
                ..input(&progress)
            },
            size,
            index as f64,
            vec![],
        );
        let id = if stage == Stage::Complete {
            tiff.id()
        } else {
            camera.id()
        };
        aperture = bounds(&output, id)
            .into_iter()
            .max_by(|a, b| a.0.area().total_cmp(&b.0.area()))
            .unwrap()
            .0;
        assert!(
            output.shapes.iter().any(
                |shape| matches!(&shape.shape, egui::Shape::Circle(circle) if circle.radius >= 2.0)
            ),
            "fixture must actually render the retained comparison network"
        );
        assert!(
            marks_inside(&output, aperture).is_empty(),
            "network nodes, edges and connectors must stay outside photograph pixels during {stage:?}"
        );
    }
    let (_, saved) = draw(&mut field, &ctx, input(&progress), size, 2.5, vec![]);
    assert!(
        bounds(&saved, tiff.id())
            .iter()
            .any(|(rect, alpha)| *rect == aperture && *alpha == 255)
    );
    assert!(marks_inside(&saved, aperture).is_empty());

    // This control paints the old overlay arrangement over the very same TIFF
    // rectangle. The geometry test must reject it even if titles are removed.
    let overlay = ctx.run(
        egui::RawInput {
            screen_rect: Some(Rect::from_min_size(Pos2::ZERO, size.into())),
            time: Some(3.0),
            ..Default::default()
        },
        |ctx| {
            egui::CentralPanel::default()
                .frame(egui::Frame::NONE)
                .show(ctx, |ui| {
                    crate::process_network::show(ui, aperture, &input(&progress));
                });
        },
    );
    assert!(
        !marks_inside(&overlay, aperture).is_empty(),
        "the regression must detect a real graph placed over the image, not merely check labels"
    );
}

fn live_packet(sequence: u64, folded: usize) -> DiagnosticSurface {
    DiagnosticSurface {
        sequence,
        frame: folded - 1,
        level: 3,
        kind: DiagnosticKind::Preview,
        scope: DiagnosticScope::Stack,
        scale: DiagnosticScale::Linear,
        width: 12,
        height: 8,
        min: 0.0,
        max: 255.0,
        pixels: vec![folded as u8 * 10; 96].into(),
        folded,
    }
}
fn live_surface<'a>(packet: &'a DiagnosticSurface, texture: &'a TextureHandle) -> Surface<'a> {
    Surface {
        epoch: 1,
        stage: Stage::Merge,
        level: packet.level,
        texture,
        frame: None,
        packet: Some(packet),
        meta: Some(SurfaceMeta {
            sequence: packet.sequence,
            kind: packet.kind,
            scale: packet.scale,
            min: packet.min,
            max: packet.max,
            samples: [packet.width, packet.height],
            folded: packet.folded,
        }),
    }
}

#[test]
fn successive_live_composites_replace_one_stable_photo_and_retire_on_import() {
    for size in [[1010.0, 490.0], [1400.0, 730.0]] {
        let ctx = egui::Context::default();
        let mut field = ProcessTheater::default();
        let mut progress = PipelineProgress::default();
        progress.stage = Stage::Merge;
        progress.plane_size = Some([900, 600]);
        let transport = texture(&ctx, "live-sequence-transport", [12, 8]);
        let mut previous = None;
        let mut all = Vec::new();
        for (step, folded) in [1, 2, 5, 7, 9, 11, 12].into_iter().enumerate() {
            let packet = live_packet(100 + folded as u64, folded);
            let surfaces = [live_surface(&packet, &transport)];
            let data = Input {
                frame_count: 12,
                surfaces: &surfaces,
                ..input(&progress)
            };
            let now = step as f64 + 1.0;
            let (_, arrival) = draw(&mut field, &ctx, data, size, now, vec![]);
            let hero = field.hero.as_ref().expect("actual photograph arrived");
            assert_eq!(
                (hero.plate.sequence, hero.plate.folded),
                (packet.sequence, folded)
            );
            let id = hero.plate.texture.id();
            let (rect, alpha) = bounds(&arrival, id)
                .into_iter()
                .max_by(|a, b| a.0.area().total_cmp(&b.0.area()))
                .unwrap();
            assert!(rect.area() > 10_000.0);
            if let Some((old, old_rect)) = previous {
                assert_eq!(rect, old_rect, "delivery cannot resize the photograph");
                assert_eq!(alpha, 0);
                assert!(
                    bounds(&arrival, old)
                        .iter()
                        .any(|(r, a)| *r == old_rect && *a == 255)
                );
                assert!(field.transitioning());
            } else {
                assert_eq!(alpha, 255);
            }
            let (_, settled) = draw(
                &mut field,
                &ctx,
                Input {
                    frame_count: 12,
                    ..input(&progress)
                },
                size,
                now + 0.5,
                vec![],
            );
            assert!(
                bounds(&settled, id)
                    .iter()
                    .any(|(r, a)| *r == rect && *a == 255)
            );
            assert!(
                !has(&settled, "BUILD"),
                "no duplicated construction gallery"
            );
            previous = Some((id, rect));
            all.push(id);
        }
        let (_, imported) = draw(
            &mut field,
            &ctx,
            Input {
                epoch: 2,
                ..input(&PipelineProgress::default())
            },
            size,
            9.0,
            vec![],
        );
        assert!(field.hero.is_none());
        assert!(all.into_iter().all(|id| bounds(&imported, id).is_empty()));
    }
}

#[test]
fn rapid_live_preview_keeps_the_visible_fade_and_releases_pending_tiff_without_input() {
    let ctx = egui::Context::default();
    let mut field = ProcessTheater::default();
    let mut progress = PipelineProgress::default();
    progress.stage = Stage::Merge;
    progress.plane_size = Some([900, 600]);
    let size = [1010.0, 490.0];
    let transport = texture(&ctx, "rapid-live-transport", [12, 8]);
    let first = live_packet(1, 1);
    let surfaces = [live_surface(&first, &transport)];
    draw(
        &mut field,
        &ctx,
        Input {
            frame_count: 12,
            surfaces: &surfaces,
            ..input(&progress)
        },
        size,
        0.0,
        vec![],
    );
    assert!(field.source.is_none(), "exercise camera-cold arrival");
    let first_id = field.hero.as_ref().unwrap().plate.texture.id();
    assert_eq!(field.hero.as_ref().unwrap().alpha, 1.0);
    let second = live_packet(2, 2);
    let surfaces = [live_surface(&second, &transport)];
    let (_, arrival) = draw(
        &mut field,
        &ctx,
        Input {
            frame_count: 12,
            surfaces: &surfaces,
            ..input(&progress)
        },
        size,
        0.1,
        vec![],
    );
    let second_id = field.hero.as_ref().unwrap().plate.texture.id();
    assert_ne!(first_id, second_id);
    assert_eq!(field.hero.as_ref().unwrap().plate.folded, 2);
    assert!(field.transitioning());
    assert!(
        bounds(&arrival, first_id)
            .iter()
            .any(|(_, alpha)| *alpha == 255)
    );
    assert!(
        bounds(&arrival, second_id)
            .iter()
            .any(|(_, alpha)| *alpha == 0)
    );
    progress.mark_complete();
    let tiff = texture(&ctx, "rapid-live-final", [300, 200]);
    draw(
        &mut field,
        &ctx,
        Input {
            frame_count: 12,
            output: Some(&tiff),
            ..input(&progress)
        },
        size,
        0.2,
        vec![],
    );
    assert_eq!(field.saved_output.as_ref().unwrap().id(), tiff.id());
    assert_eq!(field.hero.as_ref().unwrap().plate.kind, 1);
    assert!(field.hero_pending);
    for now in [0.51, 0.53, 0.95, 1.0] {
        draw(
            &mut field,
            &ctx,
            Input {
                frame_count: 12,
                ..input(&progress)
            },
            size,
            now,
            vec![],
        );
    }
    let (_, settled) = draw(
        &mut field,
        &ctx,
        Input {
            frame_count: 12,
            ..input(&progress)
        },
        size,
        1.4,
        vec![],
    );
    assert_eq!(field.hero.as_ref().unwrap().plate.kind, 3);
    assert!(!field.transitioning() && !field.hero_pending);
    assert!(
        bounds(&settled, tiff.id())
            .iter()
            .any(|(r, a)| r.area() > 10_000.0 && *a == 255)
    );
    assert!(
        bounds(&settled, second_id).is_empty(),
        "old preview is not a retained gallery"
    );
}

#[test]
fn latest_live_preview_never_counts_refused_captures_as_folded() {
    for accepted in [3, 2] {
        let ctx = egui::Context::default();
        let mut field = ProcessTheater::default();
        let mut progress = PipelineProgress::default();
        progress.ingest(&format!(
            "STREHL_UI_PROGRESS event=stage name=alignment total=3\nSTREHL_UI_PROGRESS event=align-result source=solved reference=0 placed={accepted} refused={} total=3 frames=3\n", 3-accepted));
        assert_eq!(progress.refused, Some(3 - accepted));
        progress.stage = Stage::Merge;
        progress.plane_size = Some([900, 600]);
        let transport = texture(&ctx, "short-live-transport", [12, 8]);
        for folded in 1..=accepted {
            let packet = live_packet(folded as u64, folded);
            let surfaces = [live_surface(&packet, &transport)];
            draw(
                &mut field,
                &ctx,
                Input {
                    frame_count: 3,
                    surfaces: &surfaces,
                    ..input(&progress)
                },
                [1010.0, 490.0],
                folded as f64,
                vec![],
            );
            assert_eq!(field.hero.as_ref().unwrap().plate.folded, folded);
            draw(
                &mut field,
                &ctx,
                Input {
                    frame_count: 3,
                    ..input(&progress)
                },
                [1010.0, 490.0],
                folded as f64 + 0.5,
                vec![],
            );
        }
        progress.mark_complete();
        let (_, finished) = draw(
            &mut field,
            &ctx,
            Input {
                frame_count: 3,
                ..input(&progress)
            },
            [1010.0, 490.0],
            4.0,
            vec![],
        );
        assert_eq!(field.hero.as_ref().unwrap().plate.folded, accepted);
        assert!(!has(&finished, "waiting") && !has(&finished, "BUILD"));
    }
}

#[test]
fn finished_photo_zoom_keeps_the_point_under_the_cursor() {
    let ctx = egui::Context::default();
    let mut field = ProcessTheater::default();
    let mut progress = PipelineProgress::default();
    progress.mark_complete();
    let photo = texture(&ctx, "cursor-anchored-output", [900, 600]);
    let data = Input {
        output: Some(&photo),
        ..input(&progress)
    };
    let size = [1010.0, 490.0];
    let (_, first) = draw(&mut field, &ctx, data, size, 0.0, vec![]);
    let before = bounds(&first, photo.id())[0].0;
    let pointer = before.min + before.size() * egui::vec2(0.4, 0.4);
    let (_, zoomed) = draw(
        &mut field,
        &ctx,
        data,
        size,
        0.1,
        vec![
            egui::Event::PointerMoved(pointer),
            egui::Event::MouseWheel {
                unit: egui::MouseWheelUnit::Point,
                delta: egui::vec2(0.0, 200.0),
                modifiers: egui::Modifiers::NONE,
            },
        ],
    );
    let after = bounds(&zoomed, photo.id())[0].0;
    assert!(
        after.width() > before.width() * 1.4,
        "the wheel fixture must actually zoom"
    );
    let normalized = (pointer - after.min) / after.size();
    assert!(
        (normalized - egui::vec2(0.4, 0.4)).length() < 0.001,
        "the cursor must keep the same photograph location, not jump toward its centre"
    );
}

#[test]
fn newer_retained_preview_overtakes_a_stale_live_texture() {
    let ctx = egui::Context::default();
    let mut progress = PipelineProgress::default();
    progress.ingest("planes: 120 x 80 per CFA plane\nSTREHL_UI_PROGRESS event=stage name=merge total=10\nSTREHL_UI_PROGRESS event=diagnostic seq=1 frame=0 level=1 kind=preview scope=stack scale=linear width=2 height=2 min=0 max=100 folded=1 total=10 sampling=nearest data=104080ff\n");
    let stale = progress
        .diagnostic_surfaces
        .iter()
        .find(|p| p.kind == DiagnosticKind::Preview)
        .unwrap()
        .clone();
    let old_texture = texture(&ctx, "stale-live-preview", [2, 2]);
    let surfaces = [Surface {
        epoch: 1,
        stage: Stage::Merge,
        level: 1,
        texture: &old_texture,
        frame: None,
        packet: Some(&stale),
        meta: Some(SurfaceMeta {
            sequence: 1,
            kind: DiagnosticKind::Preview,
            scale: DiagnosticScale::Linear,
            min: 0.0,
            max: 100.0,
            samples: [2, 2],
            folded: 1,
        }),
    }];
    let mut field = ProcessTheater::default();
    draw(
        &mut field,
        &ctx,
        Input {
            surfaces: &surfaces,
            ..input(&progress)
        },
        [1410.0, 850.0],
        0.0,
        vec![],
    );
    assert_eq!(field.hero.as_ref().unwrap().plate.folded, 1);
    progress.ingest("STREHL_UI_PROGRESS event=diagnostic seq=9 frame=8 level=1 kind=preview scope=stack scale=linear width=2 height=2 min=0 max=100 folded=9 total=10 sampling=nearest data=ff804010\n");
    draw(
        &mut field,
        &ctx,
        Input {
            surfaces: &surfaces,
            ..input(&progress)
        },
        [1410.0, 850.0],
        1.0,
        vec![],
    );
    draw(
        &mut field,
        &ctx,
        Input {
            surfaces: &surfaces,
            ..input(&progress)
        },
        [1410.0, 850.0],
        1.5,
        vec![],
    );
    assert_eq!(
        field.hero.as_ref().unwrap().plate.folded,
        9,
        "an old texture cannot pin the main preview when real later packets survived ingestion"
    );
}

#[test]
fn exploration_commit_identity_advances_after_bounded_history_is_full() {
    let mut field = ProcessTheater::default();
    for index in 0..120 {
        let before = field.exploration();
        field.inspected_source = Some(index);
        field.remember(before);
    }
    assert_eq!(field.history_depths(), (80, 0));
    assert_eq!(field.history_commits(), 120);
    assert!(field.undo());
    assert_eq!(
        field.history_commits(),
        120,
        "undo is a reversal, not a new edit"
    );
    assert!(field.redo());
    assert_eq!(
        field.history_commits(),
        120,
        "redo is a reversal, not a new edit"
    );
}

#[test]
fn source_companion_opens_continuously_without_crossing_the_final_photograph() {
    for size in [[1024.0, 600.0], [520.0, 640.0], [380.0, 360.0]] {
        let bounds = Rect::from_min_size(egui::pos2(13.0, 21.0), size.into());
        assert_eq!(
            source_relation_layout(
                bounds,
                0.0,
                source_relation_axis(bounds, [egui::vec2(3.0, 2.0); 2], None)
            ),
            (bounds, None)
        );
        let mut previous_area = bounds.area();
        for step in 1..=20 {
            let (final_rect, source) = source_relation_layout(
                bounds,
                step as f32 / 20.0,
                source_relation_axis(bounds, [egui::vec2(3.0, 2.0); 2], None),
            );
            let source = source.unwrap();
            assert!(bounds.contains_rect(final_rect) && bounds.contains_rect(source));
            assert!(!final_rect.intersects(source));
            assert!(final_rect.area() < previous_area);
            assert!(
                final_rect.area() >= source.area(),
                "source grows toward an equal comparison"
            );
            if step == 20 {
                assert!(
                    (final_rect.area() - source.area()).abs() < 0.01,
                    "both photographs receive equal space"
                );
            }
            previous_area = final_rect.area();
        }
    }
}

#[test]
fn comparison_orientation_uses_photograph_area_and_resists_resize_crossover_jitter() {
    let bounds = Rect::from_min_size(Pos2::ZERO, egui::vec2(600.0, 640.0));
    assert_eq!(
        source_relation_axis(bounds, [egui::vec2(3.0, 2.0); 2], None),
        SourceRelationAxis::Rows
    );
    assert_eq!(
        source_relation_axis(bounds, [egui::vec2(2.0, 3.0); 2], None),
        SourceRelationAxis::Columns,
        "same container chooses another split for genuinely different photograph proportions"
    );
    // Independently calculated photo areas at 795x640: columns 2*373.5*249,
    // rows 2*375*250. Rows win by under 1%, so an existing column layout stays.
    let tie = Rect::from_min_size(Pos2::ZERO, egui::vec2(795.0, 640.0));
    assert_eq!(
        source_relation_axis(tie, [egui::vec2(3.0, 2.0); 2], None),
        SourceRelationAxis::Rows
    );
    assert_eq!(
        source_relation_axis(
            tie,
            [egui::vec2(3.0, 2.0); 2],
            Some(SourceRelationAxis::Columns)
        ),
        SourceRelationAxis::Columns
    );
    assert_eq!(
        source_relation_axis(
            bounds,
            [egui::vec2(3.0, 2.0); 2],
            Some(SourceRelationAxis::Columns)
        ),
        SourceRelationAxis::Rows,
        "a material area gain still changes orientation"
    );
}
