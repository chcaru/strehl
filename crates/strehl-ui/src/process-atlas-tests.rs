use super::*;
use crate::pipeline::{DiagnosticScale, DiagnosticScope, PipelineProgress};

#[test]
fn atlas_starts_at_two_photo_pixels_and_preserves_the_chosen_level() {
    let ctx = egui::Context::default();
    let mut progress = complete();
    for level in 0..3 {
        let mut mask = packet(0, 1 + level as u64, vec![255; 8]);
        mask.level = level;
        progress.admission_archive.ingest(&mask, [131, 99]);
    }
    let mut atlas = ProcessAtlas::default();
    let (_, output) = draw(&ctx, &mut atlas, input(&progress), 0.0, vec![]);
    assert_eq!(atlas.level, 0);
    assert!(atlas.level_chosen);
    assert!(text(&output, "2px photo").is_some());
    assert!(text(&output, "4px photo").is_some());
    assert!(text(&output, "tone").is_some());
    atlas.level = 2;
    let _ = draw(&ctx, &mut atlas, input(&progress), 0.1, vec![]);
    assert_eq!(
        atlas.level, 2,
        "a user choice must survive another display update"
    );

    progress.output_geometry = None;
    let mut unknown = ProcessAtlas::default();
    let (_, output) = draw(&ctx, &mut unknown, input(&progress), 0.2, vec![]);
    assert_eq!(unknown.level, 1);
    assert!(text(&output, "1px grid").is_some());
    assert!(text(&output, "2px grid").is_some());

    progress.output_geometry = Some(
        crate::process_output_space::OutputGeometry::parse(
            "stack.tiff (131 x 99, 16-bit RGB, sRGB, binned from one 2x2 quad per pixel)",
        )
        .unwrap(),
    );
    let mut binned = ProcessAtlas::default();
    let (_, output) = draw(&ctx, &mut binned, input(&progress), 0.3, vec![]);
    assert_eq!(binned.level, 1);
    assert!(text(&output, "1px photo").is_some());
    assert!(text(&output, "2px photo").is_some());
}

fn input(progress: &PipelineProgress) -> Input<'_> {
    Input {
        epoch: 1,
        progress,
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
    ctx: &egui::Context,
    atlas: &mut ProcessAtlas,
    data: Input<'_>,
    time: f64,
    events: Vec<egui::Event>,
) -> (Response, egui::FullOutput) {
    draw_at(ctx, atlas, data, time, events, egui::vec2(1000.0, 720.0))
}
fn draw_at(
    ctx: &egui::Context,
    atlas: &mut ProcessAtlas,
    data: Input<'_>,
    time: f64,
    events: Vec<egui::Event>,
    size: Vec2,
) -> (Response, egui::FullOutput) {
    let mut response = Response::default();
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
                    response = atlas.show(ui, data);
                });
        },
    );
    (response, output)
}
fn click(at: Pos2, pressed: bool) -> egui::Event {
    egui::Event::PointerButton {
        pos: at,
        button: egui::PointerButton::Primary,
        pressed,
        modifiers: egui::Modifiers::NONE,
    }
}
fn packet(frame: usize, sequence: u64, pixels: Vec<u8>) -> DiagnosticSurface {
    DiagnosticSurface {
        sequence,
        frame,
        level: 0,
        kind: DiagnosticKind::GateSupport,
        scope: DiagnosticScope::Frame,
        scale: DiagnosticScale::Linear,
        width: 4,
        height: 2,
        min: 0.0,
        max: 1.0,
        pixels: pixels.into(),
        folded: 1,
    }
}
fn complete() -> PipelineProgress {
    let mut progress = PipelineProgress::default();
    progress.ingest(
        "planes : 131 x 99 per CFA plane\nbands : 7 Laplacian levels + 1 base, coarsest 2 x 1\n",
    );
    progress.ingest("wrote : C:\\results\\stack.tiff (262 x 198, 16-bit RGB, sRGB (BT.709 primaries, D65, sRGB transfer) -- for looking at, Malvar-He-Cutler demosaic)\n");
    progress.mark_complete();
    progress
}
fn picture(ctx: &egui::Context) -> TextureHandle {
    ctx.load_texture(
        "actual-photograph",
        egui::ColorImage::filled([262, 198], Color32::from_rgb(33, 70, 90)),
        egui::TextureOptions::LINEAR,
    )
}
fn photo_quad(output: &egui::FullOutput, id: egui::TextureId) -> Option<Vec<Pos2>> {
    output.shapes.iter().find_map(|shape| match &shape.shape {
        egui::Shape::Mesh(mesh) if mesh.texture_id == id => {
            Some(mesh.vertices.iter().map(|vertex| vertex.pos).collect())
        }
        _ => None,
    })
}
fn text(output: &egui::FullOutput, wanted: &str) -> Option<Rect> {
    output.shapes.iter().find_map(|shape| match &shape.shape {
        egui::Shape::Text(text) if text.galley.text() == wanted => {
            Some(Rect::from_min_size(text.pos, text.galley.size()))
        }
        _ => None,
    })
}

#[test]
fn object_instruments_follow_the_photo_and_camera_pixels_keep_their_own_coordinates() {
    let ctx = egui::Context::default();
    let photograph = picture(&ctx);
    let source = crate::workbench::SourcePhoto {
        epoch: 1,
        index: 0,
        aperture: [120, 80],
        texture: ctx.load_texture(
            "unregistered-camera",
            egui::ColorImage::filled([120, 80], GREEN),
            egui::TextureOptions::LINEAR,
        ),
    };
    let photos = [source];
    let progress = complete();
    let data = Input {
        photos: &photos,
        output: Some(&photograph),
        output_size: Some([262, 198]),
        ..input(&progress)
    };
    let mut atlas = ProcessAtlas::default();
    let (_, first) = draw(&ctx, &mut atlas, data, 0.0, vec![]);
    let camera = photo_quad(&first, photos[0].texture.id())
        .expect("a real camera source must be visible on the object");
    let front = photo_quad(&first, photograph.id()).unwrap();
    assert!(
        !Rect::from_points(&camera).intersects(Rect::from_points(&front)),
        "unregistered source pixels cannot cover registered photograph pixels"
    );
    assert!(text(&first, "Unregistered camera view").is_some());
    let workspace = text(&first, "Workspace").unwrap();
    atlas.camera.pan += egui::vec2(35.0, 22.0);
    let (_, moved) = draw(&ctx, &mut atlas, data, 0.1, vec![]);
    assert_eq!(
        text(&moved, "Workspace").unwrap().min - workspace.min,
        egui::vec2(35.0, 22.0),
        "object controls must move with the object, not stay in a screen-edge toolbar"
    );
    let moved_camera = photo_quad(&moved, photos[0].texture.id()).unwrap();
    assert!((moved_camera[0] - camera[0] - egui::vec2(35.0, 22.0)).length() < 0.01);
    let old_epoch = [crate::workbench::SourcePhoto {
        epoch: 0,
        ..photos[0].clone()
    }];
    let (_, wrong) = draw(
        &ctx,
        &mut atlas,
        Input {
            photos: &old_epoch,
            ..data
        },
        0.2,
        vec![],
    );
    assert!(
        photo_quad(&wrong, photos[0].texture.id()).is_none(),
        "a previous import cannot masquerade as this capture's source"
    );
    let at = text(&wrong, "Workspace").unwrap().center();
    let _ = draw(
        &ctx,
        &mut atlas,
        data,
        0.3,
        vec![egui::Event::PointerMoved(at), click(at, true)],
    );
    let (exit, _) = draw(&ctx, &mut atlas, data, 0.4, vec![click(at, false)]);
    assert!(
        exit.exit_space,
        "the visible object-local Workspace control must exit Space"
    );
}

#[test]
fn camera_card_avoids_the_whole_capture_volume_and_attached_instruments() {
    for (size, aspect) in [
        (egui::vec2(1060.0, 720.0), 1.5),
        (egui::vec2(1440.0, 940.0), 1.5),
        (egui::vec2(1060.0, 720.0), 2.0 / 3.0),
    ] {
        let bounds = Rect::from_min_size(Pos2::ZERO, size);
        let projection = Projection::new(object_scene(bounds), Camera::default(), aspect);
        let front = Rect::from_points(&projection.quad(0.0));
        let back = Rect::from_points(&projection.quad(1.0));
        let volume = front.union(back);
        let dock = ObjectDock::new(bounds, projection);
        let card = dock
            .camera
            .expect("normal photo apertures retain a camera companion");
        assert!(bounds.shrink(10.0).contains_rect(card));
        for occupied in [volume, dock.hub, dock.phases, dock.details] {
            assert!(!card.intersects(occupied.expand(10.0)));
        }
        if aspect == 1.5 {
            let old = Rect::from_min_size(
                front.right_top() + egui::vec2(38.0, 78.0),
                egui::vec2(118.0, 112.0),
            );
            assert!(
                old.intersects(back),
                "negative control must hide a real capture layer"
            );
        }
    }
}

#[test]
fn flat_camera_card_leaves_capture_scrubber_and_direct_fit_arcs_visible() {
    for size in [egui::vec2(1060.0, 720.0), egui::vec2(1440.0, 940.0)] {
        for aspect in [1.5, 2.0 / 3.0] {
            let bounds = Rect::from_min_size(Pos2::ZERO, size);
            for (zoom, pan) in [(1.0, Vec2::ZERO), (2.4, egui::vec2(180.0, -140.0))] {
                let projection = Projection::new(
                    object_scene(bounds),
                    Camera {
                        yaw: 0.0,
                        pitch: 0.0,
                        zoom,
                        pan,
                        ..Camera::default()
                    },
                    aspect,
                );
                let front = Rect::from_points(&projection.quad(0.0));
                let (start, end) = capture_rail(projection);
                assert!(start.x == end.x && end.y - start.y >= 80.0);
                let dock = ObjectDock::new(bounds, projection);
                if zoom == 1.0 {
                    assert!(
                        dock.camera.is_some(),
                        "normal flat views retain a companion"
                    );
                    let old = Rect::from_min_size(
                        front.right_top() + egui::vec2(26.0, 78.0),
                        egui::vec2(118.0, 112.0),
                    );
                    assert!(
                        old.intersects(
                            Rect::from_two_pos(start, end).expand2(egui::vec2(35.0, 8.0))
                        ),
                        "the prior volume-only placement must obscure the actual flat instrument"
                    );
                }
                let Some(card) = dock.camera else { continue };
                assert!(bounds.shrink(10.0).contains_rect(card));
                assert!(!card.intersects(Rect::from_two_pos(start, end).expand(7.0)));
                for occupied in [front, dock.hub, dock.phases, dock.details] {
                    assert!(!card.intersects(occupied.expand(10.0)));
                }
                // Independently sample the actual quadratic fit paths across
                // short and long capture intervals, beyond the rail itself.
                for (a, b) in [(0.08, 1.0), (0.2, 0.3), (0.4, 0.9)] {
                    let a = start.lerp(end, a);
                    let b = start.lerp(end, b);
                    let middle =
                        a.lerp(b, 0.5) + egui::vec2((a.distance(b) * 0.35).clamp(9.0, 34.0), -7.0);
                    for step in 0..=32 {
                        let t = step as f32 / 32.0;
                        let point = a.lerp(middle, t).lerp(middle.lerp(b, t), t);
                        assert!(!card.expand(1.0).contains(point));
                    }
                }
            }
        }
    }
}

#[test]
fn capture_spread_grip_tracks_pointer_without_orbiting_and_is_one_undoable_gesture() {
    let ctx = egui::Context::default();
    let photograph = picture(&ctx);
    let progress = complete();
    let data = Input {
        output: Some(&photograph),
        output_size: Some([262, 198]),
        ..input(&progress)
    };
    let mut atlas = ProcessAtlas::default();
    let (_, first) = draw(&ctx, &mut atlas, data, 0.0, vec![]);
    assert!(text(&first, "DETAIL").is_some());
    let initial = atlas.camera;
    let scene = object_scene(Rect::from_min_size(Pos2::ZERO, egui::vec2(1000.0, 720.0)));
    let projection = Projection::new(scene, initial, 262.0 / 198.0);
    let at = spread_axis(projection).unwrap().1;
    let destination = spread_axis(Projection::new(
        scene,
        Camera {
            spread: 1.65,
            ..initial
        },
        262.0 / 198.0,
    ))
    .unwrap()
    .1;
    assert!(
        at.distance(destination) > 15.0,
        "fixture must move the grip visibly"
    );
    draw(
        &ctx,
        &mut atlas,
        data,
        0.1,
        vec![egui::Event::PointerMoved(at), click(at, true)],
    );
    draw(
        &ctx,
        &mut atlas,
        data,
        0.2,
        vec![egui::Event::PointerMoved(destination)],
    );
    draw(&ctx, &mut atlas, data, 0.3, vec![click(destination, false)]);
    assert!((atlas.camera.spread - 1.65).abs() < 0.002);
    assert_eq!(
        Camera {
            spread: initial.spread,
            ..atlas.camera
        },
        initial
    );
    assert_eq!(atlas.selected, None);
    assert_eq!(atlas.history_depths(), (1, 0));
    let changed = atlas.camera;
    assert!(atlas.undo());
    assert_eq!(atlas.camera, initial);
    assert!(atlas.redo());
    assert_eq!(atlas.camera, changed);
    let at = spread_axis(Projection::new(scene, atlas.camera, 262.0 / 198.0))
        .unwrap()
        .1;
    draw(&ctx, &mut atlas, data, 0.8, vec![]);
    for (time, pressed) in [(1.0, true), (1.04, false), (1.14, true), (1.18, false)] {
        draw(
            &ctx,
            &mut atlas,
            data,
            time,
            vec![egui::Event::PointerMoved(at), click(at, pressed)],
        );
    }
    assert_eq!(
        atlas.camera, initial,
        "double-click resets spacing without flattening the camera"
    );
    assert!(atlas.undo());
    assert_eq!(
        atlas.camera, changed,
        "reset is undoable as a separate gesture"
    );
}

#[test]
fn spread_inverse_is_bounded_and_flat_photograph_has_no_fake_depth_handle() {
    let scene = object_scene(Rect::from_min_size(Pos2::ZERO, egui::vec2(1060.0, 720.0)));
    let camera = Camera::default();
    let projection = Projection::new(scene, camera, 1.5);
    let endpoint = spread_axis(projection).unwrap().1;
    let grab = SpreadGrab {
        pointer: endpoint,
        endpoint,
        camera,
    };
    for expected in [0.12, 0.35, 1.8, 2.4] {
        let target = Projection::new(
            scene,
            Camera {
                spread: expected,
                ..camera
            },
            1.5,
        )
        .at(egui::pos2(1.035, 1.035), 1.0);
        assert!((spread_at_pointer(scene, 1.5, grab, target) - expected).abs() < 0.002);
    }
    for target in [egui::pos2(-10000.0, -10000.0), egui::pos2(10000.0, 10000.0)] {
        assert!((0.12..=2.4).contains(&spread_at_pointer(scene, 1.5, grab, target)));
    }
    assert!(
        spread_axis(Projection::new(
            scene,
            Camera {
                yaw: 0.0,
                pitch: 0.0,
                ..camera
            },
            1.5
        ))
        .is_none()
    );
}

#[test]
fn object_lineage_draws_only_observed_direct_fits_and_selection_filters_the_neighborhood() {
    let ctx = egui::Context::default();
    let mut progress = complete();
    progress.alignment_edge_observations.extend([
        crate::pipeline::AlignmentEdgeObservation {
            pair: [2, 6],
            outcome: crate::pipeline::AlignmentOutcome::Accepted,
            completed: 1,
        },
        crate::pipeline::AlignmentEdgeObservation {
            pair: [4, 8],
            outcome: crate::pipeline::AlignmentOutcome::Refused,
            completed: 2,
        },
        crate::pipeline::AlignmentEdgeObservation {
            pair: [2, 99],
            outcome: crate::pipeline::AlignmentOutcome::Accepted,
            completed: 3,
        },
    ]);
    let mut atlas = ProcessAtlas::default();
    let (_, all) = draw(&ctx, &mut atlas, input(&progress), 0.0, vec![]);
    let arcs = |output: &egui::FullOutput| {
        output
            .shapes
            .iter()
            .filter(|shape| {
                matches!(&shape.shape,
        egui::Shape::Path(path) if path.points.len() == 13)
            })
            .count()
    };
    assert_eq!(
        arcs(&all),
        2,
        "invalid endpoints cannot manufacture lineage"
    );
    atlas.selected = Some(2);
    let (_, selected) = draw(&ctx, &mut atlas, input(&progress), 0.1, vec![]);
    assert_eq!(
        arcs(&selected),
        1,
        "the selected capture must reveal only its observed direct-fit neighborhood"
    );
    progress.alignment_edge_observations.clear();
    let (_, missing) = draw(&ctx, &mut atlas, input(&progress), 0.2, vec![]);
    assert_eq!(
        arcs(&missing),
        0,
        "a capture-order axis cannot invent chained transforms"
    );
}

#[test]
fn all_observed_band_previews_remain_visible_while_the_object_selects_one_band() {
    let ctx = egui::Context::default();
    let progress = complete();
    let textures: Vec<_> = (0..3)
        .map(|index| {
            ctx.load_texture(
                format!("band-evidence-{index}"),
                egui::ColorImage::filled([32, 24], Color32::from_gray(60 + index * 45)),
                egui::TextureOptions::LINEAR,
            )
        })
        .collect();
    let surfaces: Vec<_> = textures
        .iter()
        .enumerate()
        .map(|(level, texture)| crate::process_space::Surface {
            epoch: 1,
            stage: Stage::Merge,
            level,
            texture,
            frame: None,
            packet: None,
            meta: Some(crate::process_space::SurfaceMeta {
                sequence: level as u64 + 1,
                kind: DiagnosticKind::Coefficient,
                scale: DiagnosticScale::Symmetric,
                min: -1.0,
                max: 1.0,
                samples: [32, 24],
                folded: 4,
            }),
        })
        .collect();
    let data = Input {
        surfaces: &surfaces,
        ..input(&progress)
    };
    let mut atlas = ProcessAtlas::default();
    let (_, before) = draw(&ctx, &mut atlas, data, 0.0, vec![]);
    for texture in &textures {
        assert!(photo_quad(&before, texture.id()).is_some());
    }
    let bounds = Rect::from_min_size(Pos2::ZERO, egui::vec2(1000.0, 720.0));
    let dock = ObjectDock::new(
        bounds,
        Projection::new(object_scene(bounds), atlas.camera, 1.5),
    );
    let at = egui::pos2(
        dock.details.center().x,
        dock.details.top() + dock.details.height() * 2.5 / 8.0,
    );
    let _ = draw(
        &ctx,
        &mut atlas,
        data,
        0.1,
        vec![egui::Event::PointerMoved(at), click(at, true)],
    );
    let (_, selected) = draw(&ctx, &mut atlas, data, 0.2, vec![click(at, false)]);
    assert_eq!(atlas.level, 2);
    for texture in &textures {
        assert!(
            photo_quad(&selected, texture.id()).is_some(),
            "selecting a detail size must not hide the other observed bands behind tabs"
        );
    }
}

#[test]
fn spatial_sample_cells_encode_coefficient_spacing_and_unsampled_pins_have_no_link() {
    let mut progress = complete();
    let mut source = packet(2, 1, vec![255; 8]);
    source.level = 2;
    progress.admission_archive.ingest(&source, [131, 99]);
    let layer = layer_from_archive(&input(&progress), 2, 2);
    assert_eq!(layer.points.len(), 8);
    assert!((layer.cells[0].width() - 4.0 / 131.0).abs() < 0.00001);
    assert!(
        layer.cells[0].width() < 0.04,
        "the transmitted four-column grid cannot become quarter-image ownership cells"
    );
    assert_eq!(
        observed_support(&input(&progress), 2, 2, layer.points[0]),
        Some(true)
    );
    assert_eq!(
        observed_support(&input(&progress), 2, 2, egui::pos2(0.5, 0.5)),
        None,
        "a pin between transmitted coefficient cells must stay unobserved"
    );
}

#[test]
fn flat_capture_axis_caption_stays_readable_in_narrow_scene_without_covering_photo() {
    for size in [egui::vec2(700.0, 640.0), egui::vec2(1000.0, 720.0)] {
        let ctx = egui::Context::default();
        let photograph = picture(&ctx);
        let progress = complete();
        let data = Input {
            output: Some(&photograph),
            output_size: Some([262, 198]),
            ..input(&progress)
        };
        let mut atlas = ProcessAtlas::default();
        let _ = draw_at(&ctx, &mut atlas, data, 0.0, vec![], size);
        atlas.photograph();
        let (_, output) = draw_at(&ctx, &mut atlas, data, 0.1, vec![], size);
        let caption = output
            .shapes
            .iter()
            .find_map(|shape| match &shape.shape {
                egui::Shape::Text(text) if text.galley.text() == "CAPTURE ORDER" => Some((
                    Rect::from_min_size(text.pos, text.galley.size()),
                    shape.clip_rect,
                )),
                _ => None,
            })
            .expect("the real flat-view capture axis must remain labeled");
        assert!(
            caption.1.contains_rect(caption.0),
            "the entire caption must be inside the actual painter clip"
        );
        let photo = Rect::from_points(&photo_quad(&output, photograph.id()).unwrap());
        assert!(
            !caption.0.intersects(photo),
            "fitting an axis label cannot cover final photograph pixels"
        );
        let scene = object_scene(Rect::from_min_size(Pos2::ZERO, size));
        let projection = Projection::new(scene, atlas.camera, 262.0 / 198.0);
        assert_eq!(
            photo,
            Rect::from_points(&projection.quad(0.0)),
            "label placement must not resize or move the photograph"
        );
        if size.x == 700.0 {
            let old_projection = Projection::new(
                Rect::from_min_max(egui::pos2(12.0, 59.0), egui::pos2(688.0, 545.0)),
                atlas.camera,
                262.0 / 198.0,
            );
            let old = Rect::from_min_size(
                old_projection.at(egui::pos2(1.035, 0.08), 0.0) + egui::vec2(7.0, -17.0),
                caption.0.size(),
            );
            assert!(
                !caption.1.contains_rect(old),
                "negative control: this aperture must expose the old clipped caption"
            );
        }
    }
}

#[test]
fn projection_keeps_image_coordinates_invertible_through_orbit_pan_zoom_and_resize() {
    for size in [egui::vec2(500.0, 350.0), egui::vec2(1600.0, 900.0)] {
        for (yaw, pitch) in [(-1.15, -0.7), (-0.58, 0.23), (0.0, 0.0), (1.15, 0.7)] {
            let projection = Projection::new(
                Rect::from_min_size(egui::pos2(20.0, 30.0), size),
                Camera {
                    yaw,
                    pitch,
                    zoom: 2.7,
                    pan: egui::vec2(30.0, -40.0),
                    ..Camera::default()
                },
                1.53,
            );
            for uv in [
                egui::pos2(0.1, 0.1),
                egui::pos2(0.5, 0.5),
                egui::pos2(0.8, 0.3),
                egui::pos2(0.95, 0.85),
            ] {
                for depth in [0.0, 0.2, 1.0] {
                    let point = projection.at(uv, depth);
                    assert!(quad_uv(projection.quad(depth), point).unwrap().distance(uv) < 0.00001);
                }
            }
            assert!(
                quad_uv(
                    projection.quad(0.0),
                    projection.at(egui::pos2(1.2, 0.5), 0.0)
                )
                .is_none()
            );
        }
    }
}

#[test]
fn opaque_photograph_occludes_hidden_samples_for_picking_as_well_as_painting() {
    let front = [
        egui::pos2(10.0, 10.0),
        egui::pos2(210.0, 10.0),
        egui::pos2(210.0, 110.0),
        egui::pos2(10.0, 110.0),
    ];
    let hidden = (
        Pick::Sample {
            frame: 7,
            uv: egui::pos2(0.25, 0.4),
        },
        egui::pos2(70.0, 50.0),
    );
    let exposed = (
        Pick::Sample {
            frame: 9,
            uv: egui::pos2(0.75, 0.8),
        },
        egui::pos2(245.0, 90.0),
    );
    let samples = [hidden, exposed];
    assert!(matches!(
        pick_scene(hidden.1, front, true, &samples),
        Some(Pick::Photograph(_))
    ));
    assert_eq!(
        pick_scene(exposed.1, front, true, &samples),
        Some(exposed.0)
    );
    assert_eq!(
        pick_scene(hidden.1, front, false, &samples),
        Some(hidden.0),
        "negative control: hiding the front plane must expose the occluded sample"
    );
    assert!(pick_scene(egui::pos2(280.0, 150.0), front, true, &samples).is_none());
}

#[test]
fn capture_sampling_is_bounded_reaches_both_ends_and_keeps_an_unsampled_selection() {
    for count in [0_usize, 1, 2, 12, 80, 1500, 65_535] {
        let selected = count.checked_sub(3);
        let frames = layer_indices(count, selected);
        assert!(frames.len() <= LAYER_CAP);
        assert!(frames.windows(2).all(|pair| pair[0] < pair[1]));
        assert!(frames.iter().all(|&frame| frame < count));
        if count > 0 {
            assert_eq!(frames.first(), Some(&0));
            assert_eq!(frames.last(), Some(&(count - 1)));
        }
        if let Some(selected) = selected {
            assert!(frames.contains(&selected));
        }
    }
}

#[test]
fn sparse_volume_uses_only_actual_positive_cells_and_distinguishes_missing_from_zero() {
    let mut progress = PipelineProgress::default();
    progress
        .admission_archive
        .ingest(&packet(2, 1, vec![0, 255, 0, 0, 0, 0, 255, 0]), [131, 99]);
    progress
        .admission_archive
        .ingest(&packet(3, 2, vec![0; 8]), [131, 99]);
    let data = input(&progress);
    let sparse = layer_from_archive(&data, 0, 2);
    assert_eq!(
        sparse.points,
        [
            egui::pos2(49.5 / 131.0, 24.5 / 99.0),
            egui::pos2(81.5 / 131.0, 74.5 / 99.0)
        ]
    );
    assert_eq!((sparse.admitted, sparse.samples), (2, 8));
    let zero = layer_from_archive(&data, 0, 3);
    let missing = layer_from_archive(&data, 0, 4);
    assert!(zero.points.is_empty() && missing.points.is_empty());
    assert_eq!(zero.sequence, Some(2));
    assert_eq!(zero.samples, 8);
    assert_eq!(missing.sequence, None);
    assert_eq!(missing.samples, 0);
    let mut dense = packet(5, 3, vec![255; 64 * 48]);
    dense.width = 64;
    dense.height = 48;
    progress.admission_archive.ingest(&dense, [131, 99]);
    let bounded = layer_from_archive(&input(&progress), 0, 5);
    assert_eq!(bounded.points.len(), POINT_CAP);
    assert_eq!(bounded.admitted, 64 * 48);
    for uv in bounded.points {
        assert_eq!(
            progress.admission_archive.sample(0, 5, [uv.x, uv.y]),
            Some(true)
        );
    }
}

#[test]
fn final_photograph_keeps_the_same_pixels_and_bounds_during_sample_highlighting() {
    let ctx = egui::Context::default();
    let photograph = picture(&ctx);
    let mut progress = complete();
    progress
        .admission_archive
        .ingest(&packet(2, 1, vec![0, 255, 0, 0, 0, 0, 255, 0]), [131, 99]);
    let data = Input {
        output: Some(&photograph),
        output_size: Some([262, 198]),
        ..input(&progress)
    };
    assert!(shared_domain(&data));
    let mut atlas = ProcessAtlas::default();
    let (_, before) = draw(&ctx, &mut atlas, data, 0.0, vec![]);
    atlas.selected = Some(2);
    atlas.pin = Some(egui::pos2(0.375, 0.25));
    let (_, after) = draw(&ctx, &mut atlas, data, 0.2, vec![]);
    assert_eq!(
        photo_quad(&before, photograph.id()),
        photo_quad(&after, photograph.id())
    );
    assert!(photo_quad(&after, photograph.id()).is_some());
    assert!(text(&after, "FINAL PHOTOGRAPH").is_some());
    assert!(
        atlas
            .layers
            .iter()
            .any(|layer| layer.frame == 2 && layer.points.len() == 2)
    );
}

#[test]
fn detail_rail_owns_its_drags_without_stealing_an_orbit_that_crosses_it() {
    let ctx = egui::Context::default();
    let photograph = picture(&ctx);
    let progress = complete();
    let data = Input {
        output: Some(&photograph),
        output_size: Some([262, 198]),
        ..input(&progress)
    };
    let mut atlas = ProcessAtlas::default();
    let (_, before) = draw(&ctx, &mut atlas, data, 0.0, vec![]);
    let origin = Rect::from_points(&photo_quad(&before, photograph.id()).unwrap()).center();
    let original_level = atlas.level;
    let original_camera = atlas.camera;
    let bounds = Rect::from_min_size(Pos2::ZERO, egui::vec2(1000.0, 720.0));
    let rail = ObjectDock::new(
        bounds,
        Projection::new(object_scene(bounds), atlas.camera, 262.0 / 198.0),
    )
    .details;
    let at_level = |level: usize| {
        egui::pos2(
            rail.center().x,
            rail.top() + (level as f32 + 0.5) * rail.height() / 8.0,
        )
    };
    let _ = draw(
        &ctx,
        &mut atlas,
        data,
        0.1,
        vec![egui::Event::PointerMoved(origin), click(origin, true)],
    );
    let _ = draw(
        &ctx,
        &mut atlas,
        data,
        0.2,
        vec![egui::Event::PointerMoved(at_level(3))],
    );
    assert_ne!(
        atlas.camera, original_camera,
        "the input must exercise an actual orbit"
    );
    assert_eq!(
        atlas.level, original_level,
        "crossing the detail rail cannot change an orbit into a detail-size gesture"
    );
    let _ = draw(&ctx, &mut atlas, data, 0.3, vec![click(at_level(3), false)]);
    assert_eq!(
        atlas.level, original_level,
        "an orbit release cannot synthesize a detail-size click"
    );
    let rail = ObjectDock::new(
        bounds,
        Projection::new(object_scene(bounds), atlas.camera, 262.0 / 198.0),
    )
    .details;
    let at_level = |level: usize| {
        egui::pos2(
            rail.center().x,
            rail.top() + (level as f32 + 0.5) * rail.height() / 8.0,
        )
    };
    let _ = draw(
        &ctx,
        &mut atlas,
        data,
        0.5,
        vec![
            egui::Event::PointerMoved(at_level(1)),
            click(at_level(1), true),
        ],
    );
    let _ = draw(
        &ctx,
        &mut atlas,
        data,
        0.6,
        vec![egui::Event::PointerMoved(at_level(4))],
    );
    assert_eq!(
        atlas.level, 4,
        "positive control: a drag beginning on the detail rail must scrub across its cells"
    );
    let _ = draw(&ctx, &mut atlas, data, 0.7, vec![click(at_level(4), false)]);
    assert_eq!(atlas.level, 4);
}

#[test]
fn actual_orbit_gesture_changes_only_camera_and_double_click_fits_and_clears_inspection() {
    let ctx = egui::Context::default();
    let photograph = picture(&ctx);
    let progress = complete();
    let data = Input {
        output: Some(&photograph),
        output_size: Some([262, 198]),
        ..input(&progress)
    };
    let mut atlas = ProcessAtlas::default();
    let (_, before) = draw(&ctx, &mut atlas, data, 0.0, vec![]);
    let quad = photo_quad(&before, photograph.id()).unwrap();
    let at = Rect::from_points(&quad).center();
    let initial = atlas.camera;
    let _ = draw(
        &ctx,
        &mut atlas,
        data,
        0.1,
        vec![egui::Event::PointerMoved(at), click(at, true)],
    );
    let end = at + egui::vec2(35.0, 15.0);
    let _ = draw(
        &ctx,
        &mut atlas,
        data,
        0.2,
        vec![egui::Event::PointerMoved(end)],
    );
    assert_ne!(
        atlas.camera, initial,
        "fixture must dispatch a real orbit drag"
    );
    let (released, _) = draw(&ctx, &mut atlas, data, 0.3, vec![click(end, false)]);
    assert!(
        released.selected.is_none(),
        "orbit release cannot click a sample behind the pointer"
    );
    atlas.selected = Some(4);
    atlas.pin = Some(egui::pos2(0.3, 0.4));
    let mut reset = false;
    for (time, pressed) in [(1.0, true), (1.05, false), (1.15, true), (1.2, false)] {
        let (response, _) = draw(
            &ctx,
            &mut atlas,
            data,
            time,
            vec![egui::Event::PointerMoved(at), click(at, pressed)],
        );
        reset |= response.return_live;
    }
    assert!(reset);
    assert_eq!(atlas.camera.yaw, 0.0);
    assert_eq!(atlas.camera.pitch, 0.0);
    assert_eq!(atlas.camera.pan, Vec2::ZERO);
    assert_eq!(atlas.selected, None);
    assert_eq!(atlas.pin, None);
}

#[test]
fn new_import_cannot_reuse_old_photograph_or_admission_geometry() {
    let ctx = egui::Context::default();
    let photograph = picture(&ctx);
    let mut progress = complete();
    progress
        .admission_archive
        .ingest(&packet(2, 1, vec![255; 8]), [131, 99]);
    let data = Input {
        output: Some(&photograph),
        output_size: Some([262, 198]),
        ..input(&progress)
    };
    let mut atlas = ProcessAtlas::default();
    let _ = draw(&ctx, &mut atlas, data, 0.0, vec![]);
    assert!(atlas.layers.iter().any(|layer| !layer.points.is_empty()));
    let fresh = PipelineProgress::default();
    let (_, output) = draw(
        &ctx,
        &mut atlas,
        Input {
            epoch: 2,
            ..input(&fresh)
        },
        0.2,
        vec![],
    );
    assert!(photo_quad(&output, photograph.id()).is_none());
    assert!(
        atlas
            .layers
            .iter()
            .all(|layer| layer.points.is_empty() && layer.sequence.is_none())
    );
    assert!(atlas.front.is_none());
}

#[test]
fn uncertified_output_never_claims_aligned_sample_correspondence() {
    let ctx = egui::Context::default();
    let photograph = picture(&ctx);
    let mut progress = complete();
    progress
        .admission_archive
        .ingest(&packet(2, 1, vec![255; 8]), [131, 99]);
    let data = Input {
        output: Some(&photograph),
        output_size: Some([263, 198]),
        ..input(&progress)
    };
    assert!(
        !shared_domain(&data),
        "one mismatched writer dimension must invalidate correspondence"
    );
    let mut atlas = ProcessAtlas::default();
    let _ = draw(&ctx, &mut atlas, data, 0.0, vec![]);
    atlas.selected = Some(2);
    let (_, output) = draw(&ctx, &mut atlas, data, 0.2, vec![]);
    assert!(
        text(
            &output,
            "Image / sample correspondence unavailable · no registered overlay"
        )
        .is_some()
    );
    assert!(photo_quad(&output, photograph.id()).is_some());
    assert!(
        !output.shapes.iter().any(|shape| matches!(&shape.shape,
        egui::Shape::Circle(circle) if circle.radius == 2.2 && circle.stroke.width == 0.8)),
        "selected support must not paint registered footprints on an uncertified photograph"
    );
}

#[test]
fn one_orbit_drag_is_one_reversible_navigation_step_and_telemetry_adds_none() {
    let ctx = egui::Context::default();
    let photograph = picture(&ctx);
    let progress = complete();
    let data = Input {
        output: Some(&photograph),
        output_size: Some([262, 198]),
        ..input(&progress)
    };
    let mut atlas = ProcessAtlas::default();
    let (_, initial) = draw(&ctx, &mut atlas, data, 0.0, vec![]);
    let before = atlas.view();
    let at = Rect::from_points(&photo_quad(&initial, photograph.id()).unwrap()).center();
    let _ = draw(
        &ctx,
        &mut atlas,
        data,
        0.1,
        vec![egui::Event::PointerMoved(at), click(at, true)],
    );
    for step in 1..=5 {
        let _ = draw(
            &ctx,
            &mut atlas,
            data,
            0.1 + step as f64 * 0.02,
            vec![egui::Event::PointerMoved(
                at + egui::vec2(step as f32 * 8.0, 0.0),
            )],
        );
    }
    let _ = draw(
        &ctx,
        &mut atlas,
        data,
        0.25,
        vec![click(at + egui::vec2(40.0, 0.0), false)],
    );
    let after = atlas.view();
    assert_ne!(before, after);
    assert_eq!(atlas.history_depths(), (1, 0));
    assert_eq!(atlas.history_commits(), 1);
    let _ = draw(&ctx, &mut atlas, data, 0.3, vec![]);
    assert_eq!(atlas.history_depths(), (1, 0));
    assert!(atlas.undo());
    assert_eq!(atlas.view(), before);
    assert_eq!(atlas.history_depths(), (0, 1));
    assert!(atlas.redo());
    assert_eq!(atlas.view(), after);
    assert_eq!(
        atlas.history_commits(),
        1,
        "undo/redo cannot masquerade as fresh commits"
    );
}

#[test]
fn object_phase_edge_uses_real_counts_and_unknown_work_never_fills_a_progress_track() {
    let ctx = egui::Context::default();
    let mut progress = PipelineProgress::default();
    progress.stage = Stage::Alignment;
    progress.alignment_planes = Some((3, 12));
    progress.alignment_pairs = Some((3, 1, 8));
    let data = input(&progress);
    assert_eq!(
        phase_receipts(&data),
        [Some((3, 12)), Some((3, 8)), None, None]
    );
    let mut atlas = ProcessAtlas::default();
    let (_, output) = draw(&ctx, &mut atlas, data, 0.0, vec![]);
    assert!(text(&output, "READ 3/12").is_some());
    assert!(text(&output, "ALIGN 3/8").is_some());
    let bounds = Rect::from_min_size(Pos2::ZERO, egui::vec2(1000.0, 720.0));
    let strip = ObjectDock::new(
        bounds,
        Projection::new(object_scene(bounds), atlas.camera, 1.5),
    )
    .phases;
    let width = strip.width() / 4.0;
    let start = egui::pos2(strip.left() + width + 4.0, strip.bottom() - 2.0);
    let end = egui::pos2(strip.left() + 2.0 * width - 4.0, start.y);
    assert!(
        output.shapes.iter().any(|shape| matches!(&shape.shape,
        egui::Shape::LineSegment {points,stroke} if points[0].distance(start)<0.01
            && points[1].distance(start.lerp(end,3.0/8.0))<0.01 && stroke.color==ACCENT)),
        "the actual active track must paint exactly the reported completed attempts, not accepted fits"
    );
    progress.alignment_pairs = None;
    assert_eq!(phase_receipts(&input(&progress))[1], None);
}

#[test]
fn clicking_exposed_working_sample_cannot_project_a_pin_onto_uncertified_final_pixels() {
    let ctx = egui::Context::default();
    let photograph = picture(&ctx);
    let mut progress = complete();
    progress
        .admission_archive
        .ingest(&packet(11, 1, vec![0, 0, 0, 0, 0, 0, 0, 255]), [131, 99]);
    let data = Input {
        output: Some(&photograph),
        output_size: Some([263, 198]),
        ..input(&progress)
    };
    let mut atlas = ProcessAtlas::default();
    let _ = draw(&ctx, &mut atlas, data, 0.0, vec![]);
    let projection = Projection::new(
        object_scene(Rect::from_min_size(Pos2::ZERO, egui::vec2(1000.0, 720.0))),
        atlas.camera,
        263.0 / 198.0,
    );
    let uv = egui::pos2(114.5 / 131.0, 74.5 / 99.0);
    let exposed = projection.at(uv, capture_depth(11, 12));
    assert!(
        quad_uv(projection.quad(0.0), exposed).is_none(),
        "fixture must pick a visible sample outside the opaque photograph"
    );
    let _ = draw(
        &ctx,
        &mut atlas,
        data,
        0.1,
        vec![egui::Event::PointerMoved(exposed), click(exposed, true)],
    );
    let (picked, _) = draw(&ctx, &mut atlas, data, 0.12, vec![click(exposed, false)]);
    assert_eq!(picked.selected, Some(11));
    assert!(atlas.pin_is_aligned);
    let (_, uncertified) = draw(&ctx, &mut atlas, data, 0.2, vec![]);
    let painted_pin = |output: &egui::FullOutput| {
        output.shapes.iter().any(|shape| {
            matches!(&shape.shape,
        egui::Shape::Circle(circle) if circle.radius==5.0 && circle.stroke.color==ACCENT)
        })
    };
    assert!(
        !painted_pin(&uncertified),
        "an aligned-grid click cannot invent final-image coordinates"
    );
    let valid = Input {
        output_size: Some([262, 198]),
        ..data
    };
    let (_, certified) = draw(&ctx, &mut atlas, valid, 0.3, vec![]);
    assert!(
        painted_pin(&certified),
        "positive control: the same sample becomes linkable with a valid coordinate certificate"
    );
    let (_, lost) = draw(&ctx, &mut atlas, data, 0.4, vec![]);
    assert!(
        !painted_pin(&lost),
        "losing correspondence must retire the registered pin immediately"
    );
    atlas.pin_is_aligned = false;
    let (_, photo_local) = draw(&ctx, &mut atlas, data, 0.5, vec![]);
    assert!(
        painted_pin(&photo_local),
        "a photograph-local pin does not claim cross-domain correspondence"
    );
}

#[test]
fn later_low_resolution_reconstruction_cannot_downgrade_the_retained_photo_preview() {
    let ctx = egui::Context::default();
    let mut progress = PipelineProgress::default();
    progress.plane_size = Some([131, 99]);
    let mut preview = packet(3, 10, vec![120; 512 * 384]);
    preview.kind = DiagnosticKind::Preview;
    preview.scope = DiagnosticScope::Stack;
    preview.folded = 4;
    preview.width = 512;
    preview.height = 384;
    progress
        .live_preview
        .observe(&preview, 12, Some([131, 99]), [0, 0]);
    let mut atlas = ProcessAtlas::default();
    let _ = draw(&ctx, &mut atlas, input(&progress), 0.0, vec![]);
    let photographic = atlas.front.as_ref().unwrap().id();
    assert_eq!(atlas.front.as_ref().unwrap().size(), [512, 384]);
    let small = ctx.load_texture(
        "small-reconstruction",
        egui::ColorImage::filled([64, 48], Color32::GRAY),
        egui::TextureOptions::LINEAR,
    );
    let surfaces = [crate::process_space::Surface {
        epoch: 1,
        stage: Stage::Rendering,
        level: 0,
        texture: &small,
        frame: None,
        meta: Some(crate::process_space::SurfaceMeta {
            sequence: 100,
            kind: DiagnosticKind::Reconstructed,
            scale: DiagnosticScale::Linear,
            min: 0.0,
            max: 1.0,
            samples: [64, 48],
            folded: 12,
        }),
        packet: None,
    }];
    let (_, output) = draw(
        &ctx,
        &mut atlas,
        Input {
            surfaces: &surfaces,
            ..input(&progress)
        },
        0.5,
        vec![],
    );
    assert_eq!(atlas.front.as_ref().unwrap().id(), photographic);
    assert!(photo_quad(&output, small.id()).is_none());
    assert_eq!(atlas.front_sequence, 10);
    // A new independent session with no photographic Preview can still use the
    // only observed reconstruction, so the fallback has not been disabled.
    let empty = PipelineProgress::default();
    let fallback = [crate::process_space::Surface {
        epoch: 2,
        ..surfaces[0]
    }];
    let _ = draw(
        &ctx,
        &mut atlas,
        Input {
            epoch: 2,
            surfaces: &fallback,
            ..input(&empty)
        },
        0.6,
        vec![],
    );
    assert_eq!(atlas.front.as_ref().unwrap().id(), small.id());
}

#[test]
fn fast_preview_delivery_finishes_current_reveal_then_adopts_only_latest_pending_image() {
    let ctx = egui::Context::default();
    let mut progress = PipelineProgress::default();
    progress.plane_size = Some([131, 99]);
    let mut atlas = ProcessAtlas::default();
    let deliver = |progress: &mut PipelineProgress, sequence, folded| {
        let mut preview = packet(3, sequence, vec![128; 8]);
        preview.kind = DiagnosticKind::Preview;
        preview.scope = DiagnosticScope::Stack;
        preview.folded = folded;
        progress
            .live_preview
            .observe(&preview, 12, Some([131, 99]), [0, 0]);
    };
    deliver(&mut progress, 10, 2);
    let _ = draw(&ctx, &mut atlas, input(&progress), 0.0, vec![]);
    let first = atlas.front.as_ref().unwrap().id();
    deliver(&mut progress, 11, 3);
    let _ = draw(&ctx, &mut atlas, input(&progress), 0.1, vec![]);
    let second = atlas.front.as_ref().unwrap().id();
    assert_eq!(atlas.previous_front.as_ref().unwrap().id(), first);
    for (time, sequence, folded) in [(0.13, 12, 4), (0.17, 13, 5)] {
        deliver(&mut progress, sequence, folded);
        let _ = draw(&ctx, &mut atlas, input(&progress), time, vec![]);
        assert_eq!(
            atlas.front.as_ref().unwrap().id(),
            second,
            "barely revealed image cannot become the old base on another arrival"
        );
        assert_eq!(atlas.previous_front.as_ref().unwrap().id(), first);
    }
    assert_eq!(atlas.pending_front.as_ref().unwrap().sequence, 13);
    let _ = draw(&ctx, &mut atlas, input(&progress), 0.31, vec![]);
    assert_eq!(atlas.front_sequence, 13);
    assert_eq!(atlas.previous_front.as_ref().unwrap().id(), second);
    assert!(atlas.pending_front.is_none());
    let _ = draw(&ctx, &mut atlas, input(&progress), 0.6, vec![]);
    assert!(!atlas.transitioning());
}
