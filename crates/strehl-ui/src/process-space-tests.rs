use super::*;
use eframe::egui::{Color32, Pos2};
fn input(p: &PipelineProgress) -> Input<'_> {
    Input {
        epoch: 1,
        progress: p,
        frame_count: 12,
        selected: 0,
        inspected_pair: None,
        photos: &[],
        inspection_photos: &[],
        surfaces: &[],
        output: None,
        output_size: None,
    }
}
fn draw(
    space: &mut ProcessSpace,
    ctx: &egui::Context,
    input: Input<'_>,
    time: f64,
    events: Vec<egui::Event>,
) -> (Response, egui::FullOutput) {
    let mut response = Response::default();
    let output = ctx.run(
        egui::RawInput {
            screen_rect: Some(Rect::from_min_size(Pos2::ZERO, egui::vec2(1060.0, 720.0))),
            time: Some(time),
            events,
            ..Default::default()
        },
        |ctx| {
            egui::CentralPanel::default()
                .frame(egui::Frame::NONE)
                .show(ctx, |ui| {
                    response = space.show(ui, input);
                });
        },
    );
    (response, output)
}
fn texture(ctx: &egui::Context, name: &str, c: Color32) -> TextureHandle {
    ctx.load_texture(
        name,
        egui::ColorImage::filled([12, 8], c),
        egui::TextureOptions::NEAREST,
    )
}
fn mesh(output: &egui::FullOutput, id: egui::TextureId) -> bool {
    output
        .shapes
        .iter()
        .any(|s| matches!(&s.shape,egui::Shape::Mesh(m) if m.texture_id==id))
}
fn text(output: &egui::FullOutput, label: &str) -> Pos2 {
    output
        .shapes
        .iter()
        .find_map(|s| match &s.shape {
            egui::Shape::Text(t) if t.galley.text() == label => {
                Some(t.visual_bounding_rect().center())
            }
            _ => None,
        })
        .unwrap_or_else(|| panic!("missing actual label {label}"))
}
fn click(
    space: &mut ProcessSpace,
    ctx: &egui::Context,
    input: Input<'_>,
    time: f64,
    at: Pos2,
) -> Response {
    let event = |pressed| egui::Event::PointerButton {
        pos: at,
        button: egui::PointerButton::Primary,
        pressed,
        modifiers: egui::Modifiers::NONE,
    };
    let _ = draw(
        space,
        ctx,
        input,
        time,
        vec![egui::Event::PointerMoved(at), event(true)],
    );
    draw(space, ctx, input, time + 0.05, vec![event(false)]).0
}

#[test]
fn standalone_photo_uses_the_canvas_and_shared_zoom_without_claiming_diagnostics() {
    for editing in [false, true] {
        let ctx = egui::Context::default();
        let mut space = ProcessSpace::default();
        space.set_edit_focus(editing);
        space.set_edit_navigation(editing);
        let mut progress = PipelineProgress::default();
        progress.mark_complete();
        let photo = texture(&ctx, "standalone", Color32::GREEN);
        let data = Input {
            frame_count: 0,
            output: Some(&photo),
            output_size: Some([6000, 4000]),
            ..input(&progress)
        };
        assert!(data.standalone_photo());
        assert!(
            crate::process_output_space::OutputSpace::from_progress(&progress, [6000, 4000])
                .is_none()
        );
        let (_, painted) = draw(&mut space, &ctx, data, 0.1, vec![]);
        let actual = largest_image(&painted, photo.id()).expect("decoded photo is painted");
        assert!(
            actual.width() > 850.0 && actual.height() > 550.0,
            "{actual:?}"
        );
        assert!(!painted.shapes.iter().any(|shape| matches!(&shape.shape,
            egui::Shape::Text(text) if text.galley.text().contains("HOW DETAIL")
                || text.galley.text().contains("frames ·")
                || text.galley.text() == "Source + final")));
        let (full, visible) = space
            .edit_mapping()
            .expect("editor has the actual photo aperture");
        assert!((full.width() / visible.width() - 1.0).abs() < 0.001);
        space.set_photo_view([0.65, 0.4], 3.0);
        for frame in 1..20 {
            draw(&mut space, &ctx, data, 0.1 + frame as f64 * 0.1, vec![]);
        }
        let (full, visible) = space.edit_mapping().unwrap();
        assert!((full.width() / visible.width() - 3.0).abs() < 0.01);
        let center = (visible.center() - full.min) / full.size();
        assert!((center.x - 0.65).abs() < 0.01 && (center.y - 0.4).abs() < 0.01);
        assert!(space.undo());
        for frame in 21..40 {
            draw(&mut space, &ctx, data, 0.1 + frame as f64 * 0.1, vec![]);
        }
        let (full, visible) = space.edit_mapping().unwrap();
        assert!((full.width() / visible.width() - 1.0).abs() < 0.01);
        let at = visible.center();
        for (time, pressed) in [(4.2, true), (4.25, false)] {
            draw(
                &mut space,
                &ctx,
                data,
                time,
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
        let (_, menu) = draw(&mut space, &ctx, data, 4.3, vec![]);
        text(&menu, "Fit photograph");
        assert!(!menu.shapes.iter().any(|shape| matches!(&shape.shape,
            egui::Shape::Text(text) if text.galley.text().contains("Regional repairs")
                || text.galley.text().contains("contribution lens")
                || text.galley.text().contains("Photograph overlay"))));
        assert!(
            !Input {
                frame_count: 1,
                ..data
            }
            .standalone_photo()
        );
        assert!(
            !Input {
                output_size: Some([0, 4000]),
                ..data
            }
            .standalone_photo()
        );
        let mut recorded = PipelineProgress::default();
        recorded.mark_complete();
        recorded.bands = Some(8);
        assert!(
            !Input {
                progress: &recorded,
                ..data
            }
            .standalone_photo()
        );
    }
}

#[test]
fn continuous_journey_maps_and_final_photo_coexist_without_phase_navigation() {
    let ctx = egui::Context::default();
    let mut space = ProcessSpace::default();
    let mut p = PipelineProgress::default();
    p.ingest("planes : 120 x 80 per CFA plane\n");
    p.ingest("STREHL_UI_PROGRESS event=stage name=read total=12\nSTREHL_UI_PROGRESS event=stage name=alignment total=12\nSTREHL_UI_PROGRESS event=align-phase name=pairs frames=12 total=33\nSTREHL_UI_PROGRESS event=align-pair i=0 j=9 completed=1 accepted=1 frames=12 total=33\nSTREHL_UI_PROGRESS event=stage name=merge total=12\n");
    let maps: Vec<_> = (0..5)
        .map(|i| {
            texture(
                &ctx,
                &format!("causal-map-{i}"),
                Color32::from_rgb(20 + i * 20, 60, 130),
            )
        })
        .collect();
    let kinds = [
        DiagnosticKind::FocusEnergy,
        DiagnosticKind::GateFloor,
        DiagnosticKind::GateSupport,
        DiagnosticKind::Averaging,
        DiagnosticKind::Coefficient,
    ];
    let packets: Vec<_> = kinds
        .iter()
        .enumerate()
        .map(|(i, &kind)| crate::pipeline::DiagnosticSurface {
            sequence: i as u64 + 1,
            frame: 0,
            level: 0,
            kind,
            scope: if i < 3 {
                crate::pipeline::DiagnosticScope::Frame
            } else {
                crate::pipeline::DiagnosticScope::Stack
            },
            scale: match i {
                0 | 1 => DiagnosticScale::Log,
                4 => DiagnosticScale::Symmetric,
                _ => DiagnosticScale::Linear,
            },
            width: 12,
            height: 8,
            min: 0.0,
            max: 1.0,
            pixels: (0..96)
                .map(|cell| if cell % 2 == 0 { 255 } else { 0 })
                .collect::<Vec<_>>()
                .into(),
            folded: if i < 3 { 1 } else { 3 },
        })
        .collect();
    let surfaces: Vec<_> = kinds
        .iter()
        .enumerate()
        .map(|(i, &kind)| Surface {
            epoch: 1,
            stage: Stage::Merge,
            level: 0,

            texture: &maps[i],

            frame: (i < 3).then_some(0),
            packet: Some(&packets[i]),
            meta: Some(SurfaceMeta {
                sequence: i as u64 + 1,
                kind,
                scale: match i {
                    0 | 1 => DiagnosticScale::Log,
                    4 => DiagnosticScale::Symmetric,
                    _ => DiagnosticScale::Linear,
                },
                min: 0.0,
                max: 1.0,
                samples: [12, 8],
                folded: if i < 3 { 1 } else { 3 },
            }),
        })
        .collect();
    let data = Input {
        surfaces: &surfaces,
        ..input(&p)
    };
    let assert_evidence = |phase: &str, scene: &egui::FullOutput| {
        for index in [0, 1, 4] {
            assert!(
                mesh(scene, maps[index].id()),
                "scalar map {index} must remain in the simultaneous matrix"
            );
        }
        for (index, color) in [(2, crate::theme::GREEN), (3, crate::theme::AMBER)] {
            assert!(
                !mesh(scene, maps[index].id()),
                "binary observations cannot paint a filled spatial ownership map"
            );
            let mut sampled_centers = Vec::new();
            for shape in &scene.shapes {
                let egui::Shape::Mesh(mesh) = &shape.shape else {
                    continue;
                };
                if mesh.texture_id != egui::TextureId::default() {
                    continue;
                }
                let mut uses = vec![0; mesh.vertices.len()];
                for &index in &mesh.indices {
                    uses[index as usize] += 1;
                }
                sampled_centers.extend(
                    mesh.vertices
                        .iter()
                        .zip(uses)
                        .filter(|(vertex, uses)| {
                            *uses == 8
                                && vertex.color == color.gamma_multiply(0.88)
                                && shape.clip_rect.contains(vertex.pos)
                        })
                        .map(|(vertex, _)| vertex.pos),
                );
            }
            assert!(
                !sampled_centers.is_empty(),
                "{phase}: binary map {index} must expose actual positive sample glyphs alongside scalar maps"
            );
        }
    };
    let (_, initial) = draw(&mut space, &ctx, data, 0.0, vec![]);
    assert!(
        crate::process_result::overlay_marker_centers(&initial).is_empty(),
        "the compact instrument scroll starts above the actual diagnostic rows; counting offscreen shapes would falsely pass"
    );
    draw(
        &mut space,
        &ctx,
        data,
        0.1,
        vec![
            egui::Event::PointerMoved(egui::pos2(120.0, 210.0)),
            egui::Event::MouseWheel {
                unit: egui::MouseWheelUnit::Point,
                delta: egui::vec2(0.0, -220.0),
                modifiers: egui::Modifiers::NONE,
            },
        ],
    );
    let (_, before) = draw(&mut space, &ctx, data, 0.5, vec![]);
    assert_evidence("initial", &before);
    for title in [
        "READ",
        "REGISTER",
        "SEPARATE",
        "COMBINE",
        "RECONSTRUCT",
        "DEVELOP + SAVE",
    ] {
        let position = text(&before, title);
        assert!(
            Rect::from_min_size(Pos2::ZERO, egui::vec2(1060.0, 720.0)).contains(position),
            "every operation must remain on screen together: {title}"
        );
    }
    let at = text(&before, "COMBINE");
    let response = click(&mut space, &ctx, data, 0.6, at);
    assert!(
        response.selected.is_none() && response.compare_pair.is_none() && !response.open_sources,
        "operation labels describe actual work rather than navigating away from it"
    );
    let (_, persistent) = draw(&mut space, &ctx, data, 0.8, vec![]);
    assert_evidence("persistent", &persistent);
    space.inspect_frame(7);
    assert_eq!(space.inspection_frame(), Some(7));
    p.ingest("STREHL_UI_PROGRESS event=stage name=render total=12\nSTREHL_UI_PROGRESS event=render-step name=reconstruct state=finished total=12\n");
    p.mark_complete();
    let output = texture(&ctx, "owned-real-result", Color32::GOLD);
    let (_, after) = draw(
        &mut space,
        &ctx,
        Input {
            surfaces: &surfaces,
            output: Some(&output),
            ..input(&p)
        },
        1.0,
        vec![],
    );
    assert_evidence("complete", &after);
    assert!(mesh(&after, output.id()));
    assert!(
        space.visited.contains(&Stage::Alignment)
            && space.visited.contains(&Stage::Merge)
            && space.visited.contains(&Stage::Rendering)
    );
    let at = text(&after, "Photograph");
    assert!(
        click(
            &mut space,
            &ctx,
            Input {
                surfaces: &surfaces,
                output: Some(&output),
                ..input(&p)
            },
            1.1,
            at
        )
        .return_live
    );
    assert_eq!(space.inspection_frame(), None);
}
#[test]
fn imports_retire_retained_map_and_native_contact_identities() {
    let ctx = egui::Context::default();
    let mut space = ProcessSpace::default();
    let mut p = PipelineProgress::default();
    p.ingest("STREHL_UI_PROGRESS event=stage name=merge total=12\n");
    let map = texture(&ctx, "old-energy", Color32::RED);
    let camera = texture(&ctx, "old-contact", Color32::BLUE);
    let photos = [SourcePhoto {
        epoch: 1,
        index: 0,
        texture: camera.clone(),
        aperture: [12, 8],
    }];
    let surfaces = [Surface {
        epoch: 1,
        stage: Stage::Merge,
        level: 0,

        texture: &map,

        frame: Some(0),
        packet: None,
        meta: Some(SurfaceMeta {
            sequence: 1,
            kind: DiagnosticKind::FocusEnergy,
            scale: DiagnosticScale::Log,
            min: 0.0,
            max: 10.0,
            samples: [12, 8],
            folded: 1,
        }),
    }];
    let (_, before) = draw(
        &mut space,
        &ctx,
        Input {
            surfaces: &surfaces,
            photos: &photos,
            ..input(&p)
        },
        0.0,
        vec![],
    );
    assert!(mesh(&before, map.id()) && mesh(&before, camera.id()));
    let fresh = PipelineProgress::default();
    let (_, after) = draw(
        &mut space,
        &ctx,
        Input {
            epoch: 2,
            surfaces: &surfaces,
            photos: &photos,
            ..input(&fresh)
        },
        0.1,
        vec![],
    );
    assert!(!mesh(&after, map.id()) && !mesh(&after, camera.id()));
    assert!(space.visited.is_empty());
}
#[test]
fn empty_capture_does_not_open_a_second_source_view_or_select_an_index() {
    let ctx = egui::Context::default();
    let mut space = ProcessSpace::default();
    let p = PipelineProgress::default();
    let data = Input {
        frame_count: 0,
        ..input(&p)
    };
    let (_, out) = draw(&mut space, &ctx, data, 0.0, vec![]);
    let at = text(&out, "Sources");
    let response = click(&mut space, &ctx, data, 0.1, at);
    assert!(!response.open_sources);
    assert_eq!(response.selected, None);
}

fn text_contains(output: &egui::FullOutput, label: &str) -> Pos2 {
    output
        .shapes
        .iter()
        .find_map(|shape| match &shape.shape {
            egui::Shape::Text(text) if text.galley.text().contains(label) => {
                Some(text.visual_bounding_rect().center())
            }
            _ => None,
        })
        .unwrap_or_else(|| panic!("missing painted label {label}"))
}
fn largest_image(output: &egui::FullOutput, id: egui::TextureId) -> Option<Rect> {
    output
        .shapes
        .iter()
        .filter_map(|shape| match &shape.shape {
            egui::Shape::Mesh(mesh) if mesh.texture_id == id && !mesh.vertices.is_empty() => Some(
                Rect::from_points(&mesh.vertices.iter().map(|v| v.pos).collect::<Vec<_>>()),
            ),
            _ => None,
        })
        .max_by(|a, b| a.area().total_cmp(&b.area()))
}
fn source_miniature_dots(output: &egui::FullOutput, id: egui::TextureId) -> (Rect, Vec<Pos2>) {
    let label = text(output, "FINAL");
    let map = output
        .shapes
        .iter()
        .filter_map(|shape| match &shape.shape {
            egui::Shape::Mesh(mesh) if mesh.texture_id == id && !mesh.vertices.is_empty() => {
                let rect =
                    Rect::from_points(&mesh.vertices.iter().map(|v| v.pos).collect::<Vec<_>>());
                (rect.left() > label.x
                    && (rect.center().y - label.y).abs() < 30.0
                    && rect.height() < 36.0)
                    .then_some(rect)
            }
            _ => None,
        })
        .min_by(|a, b| a.left().total_cmp(&b.left()))
        .expect("first final-domain admission miniature");
    let dots = output
        .shapes
        .iter()
        .filter_map(|shape| match &shape.shape {
            egui::Shape::Circle(circle)
                if (circle.radius - 0.7).abs() < 0.01
                    && circle.fill == crate::process_sample_glyphs::level_color(0)
                    && map.contains(circle.center) =>
            {
                Some(circle.center)
            }
            _ => None,
        })
        .collect();
    (map, dots)
}
fn camera_photos(ctx: &egui::Context) -> Vec<SourcePhoto> {
    (0..12)
        .map(|index| SourcePhoto {
            epoch: 1,
            index,
            aperture: [6000, 4000],
            texture: texture(
                ctx,
                &format!("canonical-camera-{index}"),
                Color32::from_rgb(30 + index as u8 * 15, 80, 120),
            ),
        })
        .collect()
}

#[test]
fn timeline_source_sweep_uses_the_primary_photo_and_never_requests_another_dock() {
    let ctx = egui::Context::default();
    let mut space = ProcessSpace::default();
    let p = PipelineProgress::default();
    let photos = camera_photos(&ctx);
    let data = Input {
        inspection_photos: &photos,
        photos: &photos,
        ..input(&p)
    };
    let (_, initial) = draw(&mut space, &ctx, data, 0.0, vec![]);
    let target = initial
        .shapes
        .iter()
        .filter_map(|shape| match &shape.shape {
            egui::Shape::Text(text)
                if text.galley.text() == "008"
                    && text.visual_bounding_rect().center().y > 550.0 =>
            {
                Some(text.visual_bounding_rect().center())
            }
            _ => None,
        })
        .next()
        .expect("capture 008 must be visible on the shared timeline");
    let response = click(&mut space, &ctx, data, 0.1, target);
    assert_eq!(response.selected, Some(7));
    assert!(!response.open_sources);
    assert_eq!(space.inspection_frame(), Some(7));
    let (_, source) = draw(&mut space, &ctx, data, 0.2, vec![]);
    let displayed = largest_image(&source, photos[7].texture.id()).unwrap();
    assert!(
        displayed.width() > 200.0 && displayed.height() > 130.0,
        "source must replace the primary photograph, not only a contact: {displayed:?}"
    );
    text_contains(&source, "SOURCE 008 / CAMERA");
    text_contains(&source, "CAPTURES / SOURCES");
    let (step, _) = draw(
        &mut space,
        &ctx,
        data,
        0.3,
        vec![egui::Event::Key {
            key: egui::Key::ArrowRight,
            physical_key: None,
            pressed: true,
            repeat: false,
            modifiers: egui::Modifiers::NONE,
        }],
    );
    assert_eq!(step.selected, Some(8));
    assert_eq!(space.inspection_frame(), Some(8));
}

#[test]
fn source_loading_retains_truthful_pixels_and_refinement_keeps_the_same_aperture() {
    let ctx = egui::Context::default();
    let mut space = ProcessSpace::default();
    let p = PipelineProgress::default();
    let photos = camera_photos(&ctx);
    let data = Input {
        inspection_photos: &photos,
        ..input(&p)
    };
    draw(&mut space, &ctx, data, 0.0, vec![]);
    space.inspect_frame(3);
    let (_, low) = draw(&mut space, &ctx, data, 0.1, vec![]);
    let bounds = largest_image(&low, photos[3].texture.id()).unwrap();
    space.inspect_frame(9);
    let (_, waiting) = draw(
        &mut space,
        &ctx,
        Input {
            inspection_photos: &photos[..4],
            ..data
        },
        0.2,
        vec![],
    );
    text_contains(&waiting, "SOURCE 004 / CAMERA · 010 pending");
    assert_eq!(
        largest_image(&waiting, photos[3].texture.id()),
        Some(bounds)
    );
    let (_, delivered) = draw(&mut space, &ctx, data, 0.3, vec![]);
    assert_eq!(
        largest_image(&delivered, photos[9].texture.id()),
        Some(bounds)
    );
    let mut refined = photos.clone();
    refined[9].texture = ctx.load_texture(
        "canonical-source-9-refined",
        egui::ColorImage::filled([120, 80], Color32::LIGHT_BLUE),
        egui::TextureOptions::LINEAR,
    );
    let (_, next) = draw(
        &mut space,
        &ctx,
        Input {
            inspection_photos: &refined,
            ..data
        },
        0.4,
        vec![],
    );
    assert_eq!(largest_image(&next, refined[9].texture.id()), Some(bounds));
    text_contains(&next, "SOURCE 010 / CAMERA");
    assert!(
        mesh(&next, photos[9].texture.id()),
        "the delivered low tier must remain behind the refinement reveal"
    );
}

#[test]
fn local_live_action_releases_source_comparison_and_shows_the_latest_composite() {
    let ctx = egui::Context::default();
    let mut space = ProcessSpace::default();
    let mut p = PipelineProgress::default();
    p.ingest(
        "planes: 120 x 80 per CFA plane\nSTREHL_UI_PROGRESS event=stage name=merge total=12\n",
    );
    for prefix in 1..=12 {
        p.ingest(&format!("STREHL_UI_PROGRESS event=diagnostic seq={prefix} frame={} level=1 kind=preview scope=stack scale=linear width=2 height=2 min=0 max=100 folded={prefix} total=12 sampling=nearest data=104080ff\n", prefix - 1));
    }
    let photos = camera_photos(&ctx);
    let data = Input {
        inspection_photos: &photos,
        ..input(&p)
    };
    draw(&mut space, &ctx, data, 0.0, vec![]);
    space.inspect_frame(7);
    let (_, sources) = draw(&mut space, &ctx, data, 0.5, vec![]);
    text_contains(&sources, "SOURCE 008 / CAMERA");
    assert_eq!(space.inspection_frame(), Some(7));
    let resume = text(&sources, "Live");
    assert!(click(&mut space, &ctx, data, 0.6, resume).return_live);
    assert_eq!(space.inspection_frame(), None);
    let (_, current) = draw(&mut space, &ctx, data, 1.1, vec![]);
    assert!(!current.shapes.iter().any(|shape| matches!(&shape.shape, egui::Shape::Text(text) if text.galley.text().contains("RECORDED BUILD"))));
    text_contains(&current, "LIVE STACK / 12 OF 12 FRAMES");
}

#[test]
fn passive_viewport_changes_never_rewrite_saved_workspace_proportions() {
    let ctx = egui::Context::default();
    let mut space = ProcessSpace::default();
    let p = PipelineProgress::default();
    let prefs = crate::workspace_layout::WorkspaceLayout {
        final_detail: 0.27,
        network: 0.38,
        detail: 0.61,
        ..Default::default()
    };
    space.set_layout(prefs);
    for iteration in 0..30 {
        draw(&mut space, &ctx, input(&p), iteration as f64 * 0.1, vec![]);
        assert_eq!(
            space.layout(),
            prefs,
            "paint-driven width clamping cannot ratchet the user's saved layout"
        );
    }
}

fn narrow_scene(
    space: &mut ProcessSpace,
    ctx: &egui::Context,
    data: Input<'_>,
    time: f64,
    events: Vec<egui::Event>,
) -> egui::FullOutput {
    ctx.run(
        egui::RawInput {
            screen_rect: Some(Rect::from_min_size(Pos2::ZERO, egui::vec2(734.0, 632.0))),
            time: Some(time),
            events,
            ..Default::default()
        },
        |ctx| {
            egui::CentralPanel::default()
                .frame(egui::Frame::NONE)
                .show(ctx, |ui| {
                    space.show(ui, data);
                });
        },
    )
}

#[test]
fn narrow_workspace_keeps_primary_image_journey_and_timeline_visible_while_instruments_scroll() {
    let ctx = egui::Context::default();
    crate::theme::install(&ctx);
    let mut space = ProcessSpace::default();
    let p = PipelineProgress::default();
    let photos = camera_photos(&ctx);
    let data = Input {
        inspection_photos: &photos,
        photos: &photos,
        ..input(&p)
    };
    let initial = narrow_scene(&mut space, &ctx, data, 0.0, vec![]);
    let assert_readable = |output: &egui::FullOutput, labels: &[&str]| {
        for label in labels {
            let (clip, bounds) = output
                .shapes
                .iter()
                .find_map(|shape| match &shape.shape {
                    egui::Shape::Text(text) if text.galley.text() == *label => {
                        Some((shape.clip_rect, text.visual_bounding_rect()))
                    }
                    _ => None,
                })
                .unwrap_or_else(|| panic!("missing instrument label: {label}"));
            assert!(
                clip.contains_rect(bounds),
                "instrument label {label} clipped: {bounds:?} outside {clip:?}"
            );
        }
    };
    assert_readable(&initial, &["CAPTURE CONTRIBUTIONS"]);
    let primary =
        largest_image(&initial, photos[0].texture.id()).expect("primary camera photograph");
    assert!(
        primary.width() > 250.0 && primary.height() > 160.0,
        "primary image must dominate its column at a sidebar-reduced viewport: {primary:?}"
    );
    let viewport = Rect::from_min_size(Pos2::ZERO, egui::vec2(734.0, 632.0));
    assert!(viewport.contains_rect(primary));
    for label in [
        "READ",
        "REGISTER",
        "COMBINE",
        "SAVE",
        "Sources",
        "CAPTURES / SOURCES",
    ] {
        assert!(
            viewport.contains(text_contains(&initial, label)),
            "persistent control escaped the visible workspace: {label}"
        );
    }
    let last = initial
        .shapes
        .iter()
        .filter_map(|shape| match &shape.shape {
            egui::Shape::Text(text)
                if text.galley.text() == "012"
                    && text.visual_bounding_rect().center().y > 470.0
                    && viewport.contains(text.visual_bounding_rect().center()) =>
            {
                Some(text.visual_bounding_rect().center())
            }
            _ => None,
        })
        .next()
        .expect("last capture visible inside the one timeline");
    let graph_before = text_contains(&initial, "CAPTURES / DIRECT FITS");
    narrow_scene(
        &mut space,
        &ctx,
        data,
        0.1,
        vec![
            egui::Event::PointerMoved(egui::pos2(120.0, 210.0)),
            egui::Event::MouseWheel {
                unit: egui::MouseWheelUnit::Point,
                delta: egui::vec2(0.0, -180.0),
                modifiers: egui::Modifiers::NONE,
            },
        ],
    );
    let scrolled = narrow_scene(&mut space, &ctx, data, 0.4, vec![]);
    assert_readable(
        &scrolled,
        &[
            "TEXTURE",
            "NOISE LIMIT",
            "ADMITTED",
            "FALLBACK",
            "ACCUMULATED",
        ],
    );
    assert_eq!(
        largest_image(&scrolled, photos[0].texture.id()),
        Some(primary)
    );
    assert!(scrolled.shapes.iter().any(|shape| matches!(&shape.shape, egui::Shape::Text(text) if text.galley.text() == "012" && text.visual_bounding_rect().center().distance(last) < 0.01)), "last={last:?}, actual={:?}", scrolled.shapes.iter().filter_map(|shape| match &shape.shape { egui::Shape::Text(text) if text.galley.text() == "012" => Some(text.visual_bounding_rect()), _ => None }).collect::<Vec<_>>());
    assert!(!scrolled.shapes.iter().any(|shape| matches!(&shape.shape, egui::Shape::Text(text) if text.galley.text() == "CAPTURES / DIRECT FITS" && text.visual_bounding_rect().center().distance(graph_before) < 0.01)), "fixture must really scroll the instrument region");
}

#[test]
fn limited_render_keeps_all_sources_browsable_but_live_photo_uses_the_engine_total() {
    let ctx = egui::Context::default();
    let mut space = ProcessSpace::default();
    let photos = camera_photos(&ctx);
    let mut p = PipelineProgress::default();
    p.ingest("planes: 120 x 80 per CFA plane\nSTREHL_UI_PROGRESS event=stage name=merge total=3\n");
    for prefix in 1..=3 {
        p.ingest(&format!("STREHL_UI_PROGRESS event=diagnostic seq={prefix} frame={} level=1 kind=preview scope=stack scale=linear width=2 height=2 min=0 max=100 folded={prefix} total=3 sampling=nearest data=104080ff\n", prefix - 1));
    }
    let data = Input {
        frame_count: 12,
        inspection_photos: &photos,
        photos: &photos,
        ..input(&p)
    };
    assert_eq!(data.processing_count(), 3);
    let (_, out) = draw(&mut space, &ctx, data, 0.0, vec![]);
    text_contains(&out, "LIVE STACK / 3 OF 3 FRAMES");
    assert!(!out.shapes.iter().any(
        |shape| matches!(&shape.shape, egui::Shape::Text(text) if text.galley.text() == "3 / 12")
    ));
    assert!(
        space.contact_indices().contains(&11),
        "last source remains part of the real capture timeline"
    );
    space.inspect_frame(11);
    let (_, source) = draw(&mut space, &ctx, data, 0.5, vec![]);
    assert!(
        largest_image(&source, photos[11].texture.id()).is_some_and(|rect| rect.width() > 250.0)
    );
    text_contains(&source, "SOURCE 012 / CAMERA");
    text_contains(&source, "outside rendered prefix");
}

fn contact_at(output: &egui::FullOutput, frame: usize) -> Pos2 {
    if let Some(at) = output.shapes.iter().find_map(|s| match &s.shape {
        egui::Shape::Text(t)
            if t.galley.text() == format!("{:03}", frame + 1)
                && t.visual_bounding_rect().center().y > 600.0
                && s.clip_rect.contains(t.visual_bounding_rect().center()) =>
        {
            Some(t.visual_bounding_rect().center())
        }
        _ => None,
    }) {
        return at;
    }
    // Enlarged contacts sample a long bracket evenly; omitted thumbnail slots
    // remain reachable on the actual continuous capture axis above them.
    let label_y = output
        .shapes
        .iter()
        .find_map(|shape| match &shape.shape {
            egui::Shape::Text(text)
                if ["Full image", "read"].contains(&text.galley.text())
                    && text.visual_bounding_rect().center().y > 400.0 =>
            {
                Some(text.visual_bounding_rect().center().y)
            }
            _ => None,
        })
        .expect("visible capture evidence lane");
    let axis = output
        .shapes
        .iter()
        .find_map(|shape| match &shape.shape {
            egui::Shape::LineSegment { points, .. }
                if points[0].y == points[1].y
                    && points[1].x - points[0].x > 500.0
                    && (label_y + 1.0..label_y + 25.0).contains(&points[0].y) =>
            {
                Some(*points)
            }
            _ => None,
        })
        .expect("actual full capture axis");
    axis[0].lerp(axis[1], frame as f32 / 11.0) - egui::vec2(0.0, 3.0)
}
fn pointer(at: Pos2, pressed: bool, modifiers: egui::Modifiers) -> egui::Event {
    egui::Event::PointerButton {
        pos: at,
        button: egui::PointerButton::Primary,
        pressed,
        modifiers,
    }
}
#[test]
fn a_source_drag_is_one_undoable_exploration_and_redo_requests_the_restored_source() {
    let ctx = egui::Context::default();
    let mut space = ProcessSpace::default();
    let p = PipelineProgress::default();
    let photos = camera_photos(&ctx);
    let data = Input {
        photos: &photos,
        inspection_photos: &photos,
        ..input(&p)
    };
    let (_, scene) = draw(&mut space, &ctx, data, 0.0, vec![]);
    click(&mut space, &ctx, data, 0.2, contact_at(&scene, 3));
    assert_eq!(space.inspection_frame(), Some(3));
    let depths = space.history_depths();
    assert_eq!(depths, (1, 0));
    let a = contact_at(&scene, 5);
    // Deliberate card clicks use card identity. A drag uses the full capture
    // axis. Locate its actual painted baseline below its local legend; neither
    // sparse card availability nor a fixed screen y describes that axis.
    let (legend, timeline) = scene
        .shapes
        .iter()
        .find_map(|shape| match &shape.shape {
            egui::Shape::Text(text) if text.galley.text() == "read" => {
                Some((text.visual_bounding_rect(), shape.clip_rect))
            }
            _ => None,
        })
        .expect("painted source timeline legend");
    let axis = scene
        .shapes
        .iter()
        .filter_map(|shape| match &shape.shape {
            egui::Shape::LineSegment { points, .. }
                if points[0].y == points[1].y
                    && points[0].y > legend.bottom()
                    && timeline.contains(points[0])
                    && timeline.contains(points[1])
                    && points[1].x - points[0].x > timeline.width() * 0.9 =>
            {
                Some(*points)
            }
            _ => None,
        })
        .min_by(|a, b| a[0].y.total_cmp(&b[0].y))
        .expect("actual full capture axis");
    let b = egui::pos2(egui::lerp(axis[0].x..=axis[1].x, 8.0 / 11.0), a.y);
    let c = egui::pos2(axis[1].x - 0.1, a.y);
    draw(
        &mut space,
        &ctx,
        data,
        0.6,
        vec![
            egui::Event::PointerMoved(a),
            pointer(a, true, egui::Modifiers::NONE),
        ],
    );
    draw(
        &mut space,
        &ctx,
        data,
        0.7,
        vec![egui::Event::PointerMoved(b)],
    );
    draw(
        &mut space,
        &ctx,
        data,
        0.8,
        vec![egui::Event::PointerMoved(c)],
    );
    draw(
        &mut space,
        &ctx,
        data,
        0.9,
        vec![pointer(c, false, egui::Modifiers::NONE)],
    );
    assert_eq!(space.inspection_frame(), Some(11));
    assert_eq!(
        space.history_depths(),
        (2, 0),
        "one drag must not emit one history entry per delivered capture"
    );
    assert!(space.undo());
    assert_eq!(space.inspection_frame(), Some(3));
    let (restored, _) = draw(&mut space, &ctx, data, 1.1, vec![]);
    assert_eq!(
        restored.selected,
        Some(3),
        "parent must request restored pixels"
    );
    assert!(space.redo());
    assert_eq!(space.inspection_frame(), Some(11));
    let (restored, _) = draw(&mut space, &ctx, data, 1.2, vec![]);
    assert_eq!(restored.selected, Some(11));
}

#[test]
fn retained_packets_advance_primary_pixels_without_texture_delivery_or_build_thumbnails() {
    let ctx = egui::Context::default();
    let mut space = ProcessSpace::default();
    let mut p = PipelineProgress::default();
    p.ingest(
        "planes: 120 x 80 per CFA plane\nSTREHL_UI_PROGRESS event=stage name=merge total=12\n",
    );
    for prefix in 1..=12 {
        p.ingest(&format!("STREHL_UI_PROGRESS event=diagnostic seq={prefix} frame={} level=1 kind=preview scope=stack scale=linear width=2 height=2 min=0 max=100 folded={prefix} total=12 sampling=nearest data={:02x}4080ff\n", prefix-1, prefix*7));
        let (_, scene) = draw(&mut space, &ctx, input(&p), prefix as f64, vec![]);
        let (_, settled) = draw(&mut space, &ctx, input(&p), prefix as f64 + 0.5, vec![]);
        text_contains(&settled, &format!("LIVE STACK / {prefix} OF 12 FRAMES"));
        assert!(
            !scene
                .shapes
                .iter()
                .any(|shape| matches!(&shape.shape, egui::Shape::Mesh(mesh)
            if !mesh.vertices.is_empty() && mesh.vertices.iter().all(|v| v.pos.y > 685.0))),
            "construction progress must be marks on the shared axis, not another image strip"
        );
    }
}

#[test]
fn completed_photo_keeps_network_and_source_comparison_until_explicit_return() {
    let ctx = egui::Context::default();
    let mut space = ProcessSpace::default();
    let photos = camera_photos(&ctx);
    let result = texture(&ctx, "final-baseline", Color32::GOLD);
    let mut p = PipelineProgress::default();
    p.ingest("planes : 120 x 80 per CFA plane\ncoverage : field of view scaled to 0.9500 so that EVERY frame covers every pixel\nwrote : result.tiff (240 x 160, 16-bit RGB, sRGB (BT.709 primaries, D65, sRGB transfer) -- for looking at, Malvar-He-Cutler demosaic)\n");
    p.mark_complete();
    let data = Input {
        photos: &photos,
        inspection_photos: &photos,
        output: Some(&result),
        output_size: Some([240, 160]),
        ..input(&p)
    };
    draw(&mut space, &ctx, data, 0.0, vec![]);
    let (_, scene) = draw(&mut space, &ctx, data, 0.6, vec![]);
    text_contains(&scene, "CAPTURES / DIRECT FITS");
    let at = contact_at(&scene, 7);
    let response = click(&mut space, &ctx, data, 0.8, at);
    assert_eq!(
        response.selected,
        Some(7),
        "a deliberate contact selection requests its actual camera pixels"
    );
    assert_eq!(space.inspection_frame(), Some(7));
    let (_, compared) = draw(&mut space, &ctx, data, 1.1, vec![]);
    let final_bounds = largest_image(&compared, result.id()).unwrap();
    let source_bounds = largest_image(&compared, photos[7].texture.id()).unwrap();
    assert!(
        source_bounds.width() > 160.0 && source_bounds.height() > 100.0,
        "comparison must be an inspectable camera image, not a filmstrip/inset: {source_bounds:?}"
    );
    assert!(
        !final_bounds.intersects(source_bounds),
        "camera and registered photograph cannot spatially overlap"
    );
    assert!((source_bounds.aspect_ratio() - 1.5).abs() < 0.001);
    text_contains(&compared, "SOURCE 008 / CAMERA");
    text_contains(&compared, "CAMERA SPACE · correspondence unavailable");
    let (_, hovered) = draw(
        &mut space,
        &ctx,
        data,
        1.2,
        vec![egui::Event::PointerMoved(contact_at(&compared, 10))],
    );
    assert_eq!(
        space.inspection_frame(),
        Some(10),
        "crossing another contact explores its actual camera pixels"
    );
    assert!(largest_image(&hovered, photos[10].texture.id()).is_some());
    draw(
        &mut space,
        &ctx,
        data,
        1.25,
        vec![egui::Event::PointerMoved(egui::pos2(1.0, 1.0))],
    );
    draw(&mut space, &ctx, data, 1.7, vec![]);
    assert_eq!(
        space.inspection_frame(),
        Some(10),
        "leaving keeps the last explored source until explicit return"
    );
    let response = click(&mut space, &ctx, data, 1.8, text(&compared, "Photograph"));
    assert!(response.return_live);
    assert_eq!(space.inspection_frame(), None);
    draw(&mut space, &ctx, data, 2.1, vec![]);
    let (_, clean) = draw(&mut space, &ctx, data, 2.2, vec![]);
    assert!(largest_image(&clean, result.id()).is_some());
    let at = contact_at(&clean, 7);
    let alt = egui::Modifiers {
        alt: true,
        ..Default::default()
    };
    draw(
        &mut space,
        &ctx,
        data,
        2.3,
        vec![egui::Event::PointerMoved(at), pointer(at, true, alt)],
    );
    draw(&mut space, &ctx, data, 2.4, vec![pointer(at, false, alt)]);
    let (_, compared) = draw(&mut space, &ctx, data, 2.8, vec![]);
    assert_eq!(
        space.inspection_frame(),
        Some(7),
        "release keeps source comparison"
    );
    let final_rect = largest_image(&compared, result.id()).unwrap();
    let camera_rect = largest_image(&compared, photos[7].texture.id()).unwrap();
    assert!(!final_rect.intersects(camera_rect));
    assert!(camera_rect.width() > 160.0 && final_rect.width() > 160.0);
    text_contains(&compared, "SOURCE 008 / CAMERA");
    assert!(click(&mut space, &ctx, data, 2.9, text(&compared, "Photograph")).return_live);
    assert_eq!(space.inspection_frame(), None);
}

#[test]
fn completed_source_drag_links_actual_camera_pixels_to_admission_and_is_undoable() {
    let ctx = egui::Context::default();
    let mut space = ProcessSpace::default();
    let mut photos = camera_photos(&ctx);
    // The camera portrait must remain portrait beside a landscape final; a
    // shared image-space crop/warp would violate this deliberately different
    // geometry. Capture identity is the only certified relation here.
    photos[7].aperture = [4000, 6000];
    let result = texture(&ctx, "registered-final-anchor", Color32::GOLD);
    let mut p = PipelineProgress::default();
    p.ingest("planes : 120 x 80 per CFA plane\ncoverage : field of view scaled to 0.9500 so that EVERY frame covers every pixel\nbands : 7 Laplacian levels + 1 base, coarsest 1 x 1\nwrote : result.tiff (240 x 160, 16-bit RGB, sRGB (BT.709 primaries, D65, sRGB transfer) -- for looking at, Malvar-He-Cutler demosaic)\n");
    for frame in [3, 7] {
        p.admission_archive.ingest(
            &crate::pipeline::DiagnosticSurface {
                sequence: frame as u64 + 1,
                frame,
                level: 0,
                kind: DiagnosticKind::GateSupport,
                scope: crate::pipeline::DiagnosticScope::Frame,
                scale: DiagnosticScale::Linear,
                width: 2,
                height: 2,
                min: 0.0,
                max: 1.0,
                pixels: (if frame == 3 {
                    vec![255, 0, 0, 0]
                } else {
                    vec![0, 255, 0, 255]
                })
                .into(),
                folded: 1,
            },
            [120, 80],
        );
    }
    p.mark_complete();
    let data = Input {
        photos: &photos,
        inspection_photos: &photos,
        output: Some(&result),
        output_size: Some([240, 160]),
        ..input(&p)
    };
    draw(&mut space, &ctx, data, 0.0, vec![]);
    let (_, clean) = draw(&mut space, &ctx, data, 0.5, vec![]);
    let from = contact_at(&clean, 3);
    let to = contact_at(&clean, 7);
    let baseline = space.history_depths();
    let (first, _) = draw(
        &mut space,
        &ctx,
        data,
        0.8,
        vec![
            egui::Event::PointerMoved(from),
            pointer(from, true, egui::Modifiers::NONE),
        ],
    );
    assert_eq!(first.selected, Some(3));
    let (moved, _) = draw(
        &mut space,
        &ctx,
        data,
        0.9,
        vec![egui::Event::PointerMoved(to)],
    );
    assert_eq!(moved.selected, Some(7));
    draw(
        &mut space,
        &ctx,
        data,
        1.0,
        vec![pointer(to, false, egui::Modifiers::NONE)],
    );
    let (_, compared) = draw(
        &mut space,
        &ctx,
        data,
        1.3,
        vec![egui::Event::PointerMoved(egui::pos2(1.0, 1.0))],
    );
    assert_eq!(space.inspection_frame(), Some(7));
    assert_eq!(
        space.history_depths(),
        (baseline.0 + 1, 0),
        "one source sweep is one reversible exploration"
    );
    let final_rect = largest_image(&compared, result.id()).unwrap();
    let source_rect = largest_image(&compared, photos[7].texture.id()).unwrap();
    assert!((final_rect.aspect_ratio() - 1.5).abs() < 0.001);
    assert!((source_rect.aspect_ratio() - 2.0 / 3.0).abs() < 0.001);
    assert!(!source_rect.intersects(final_rect));
    text_contains(&compared, "SOURCE 008 / CAMERA");
    text_contains(&compared, "LINKED REGION · APPROXIMATE");
    let (miniature, miniature_dots) = source_miniature_dots(&compared, result.id());
    assert_eq!(
        miniature_dots.len(),
        2,
        "both observed admissions are visualized beside the source"
    );
    assert!(miniature_dots.iter().all(|at| at.x > miniature.center().x));
    let dots: Vec<_> = crate::process_result::overlay_marker_centers(&compared)
        .into_iter()
        .filter(|point| final_rect.contains(*point))
        .collect();
    assert_eq!(
        dots.len(),
        2,
        "only the two observed positive samples may mark the final"
    );
    assert!(
        dots.iter().all(|at| at.x > final_rect.center().x),
        "capture008 admits only right-side observations"
    );
    assert!(space.undo());
    let (undone, _) = draw(&mut space, &ctx, data, 1.6, vec![]);
    assert!(undone.return_live && space.inspection_frame().is_none());
    assert!(space.redo());
    let (redone, _) = draw(&mut space, &ctx, data, 1.9, vec![]);
    assert_eq!(
        redone.selected,
        Some(7),
        "redo must request the actual source texture, not just restore a marker"
    );
    let (_, restored) = draw(&mut space, &ctx, data, 2.2, vec![]);
    let close = text(&restored, "Close");
    assert!(click(&mut space, &ctx, data, 2.4, close).return_live);
    assert_eq!(space.inspection_frame(), None);

    click(&mut space, &ctx, data, 2.8, from);
    draw(&mut space, &ctx, data, 3.1, vec![]);
    let cold = Input {
        inspection_photos: &photos[..4],
        ..data
    };
    assert_eq!(click(&mut space, &ctx, cold, 3.4, to).selected, Some(7));
    let (_, waiting) = draw(&mut space, &ctx, cold, 3.7, vec![]);
    text_contains(&waiting, "SOURCE 004 / CAMERA · 008 pending");
    let (miniature, miniature_dots) = source_miniature_dots(&waiting, result.id());
    assert_eq!(
        miniature_dots.len(),
        1,
        "pending comparison must retain the displayed source's admission sample, not the requested source's pair"
    );
    assert!(miniature_dots[0].x < miniature.center().x);
    assert!(
        largest_image(&waiting, photos[3].texture.id()).is_some(),
        "cold source request retains truthful previous pixels"
    );
    assert!(!waiting.shapes.iter().any(|shape| matches!(&shape.shape, egui::Shape::Text(text) if text.galley.text().starts_with("Camera 008 ·"))),
        "pending source cannot inherit the requested capture's admission count");
}
