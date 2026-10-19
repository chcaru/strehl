use super::*;
use crate::pipeline::{AlignmentEdgeObservation, PipelineProgress};

fn input(progress: &PipelineProgress, count: usize) -> Input<'_> {
    Input {
        epoch: 1,
        progress,
        frame_count: count,
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
    input: Input<'_>,
    time: f64,
    events: Vec<egui::Event>,
) -> (Option<Pick>, egui::FullOutput) {
    draw_at(
        ctx,
        input,
        Rect::from_min_size(Pos2::ZERO, egui::vec2(600.0, 350.0)),
        time,
        events,
    )
}
fn draw_at(
    ctx: &egui::Context,
    input: Input<'_>,
    rect: Rect,
    time: f64,
    events: Vec<egui::Event>,
) -> (Option<Pick>, egui::FullOutput) {
    let mut selected = None;
    let output = ctx.run(
        egui::RawInput {
            screen_rect: Some(Rect::from_min_max(Pos2::ZERO, rect.max)),
            time: Some(time),
            events,
            ..Default::default()
        },
        |ctx| {
            egui::CentralPanel::default()
                .frame(egui::Frame::NONE)
                .show(ctx, |ui| {
                    selected = show(ui, rect, &input);
                });
        },
    );
    (selected, output)
}
fn diagram() -> Rect {
    diagram_rect(Rect::from_min_size(Pos2::ZERO, egui::vec2(600.0, 350.0)))
}
fn edge(output: &egui::FullOutput, pair: [usize; 2], count: usize) -> Vec<Stroke> {
    let points = pair.map(|index| position(diagram(), index, count));
    output
        .shapes
        .iter()
        .filter_map(|shape| match &shape.shape {
            egui::Shape::LineSegment {
                points: actual,
                stroke,
            } if actual[0].distance(points[0]) < 0.01 && actual[1].distance(points[1]) < 0.01 => {
                Some(*stroke)
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

#[test]
fn requested_contact_identities_equal_actual_photo_meshes_for_compact_and_roomy_apertures() {
    let ctx = egui::Context::default();
    let progress = PipelineProgress::default();
    let count = 259;
    let photos = (0..count)
        .map(|index| crate::workbench::SourcePhoto {
            epoch: 1,
            index,
            aperture: [300, 200],
            texture: ctx.load_texture(
                format!("visible-network-{index}"),
                egui::ColorImage::filled([6, 4], GREEN),
                egui::TextureOptions::LINEAR,
            ),
        })
        .collect::<Vec<_>>();
    let mut saw_hidden = false;
    let mut saw_photos = false;
    for (step, size) in [
        egui::vec2(216.0, 100.0),
        egui::vec2(216.0, 180.0),
        egui::vec2(176.0, 226.0),
        egui::vec2(216.0, 348.0),
        egui::vec2(296.0, 570.0),
    ]
    .into_iter()
    .enumerate()
    {
        let rect = Rect::from_min_size(Pos2::ZERO, size);
        let mut scene = input(&progress, count);
        scene.photos = &photos;
        let (_, output) = draw_at(&ctx, scene, rect, step as f64, vec![]);
        let painted = photos.iter().filter(|photo| output.shapes.iter().any(|shape| matches!(&shape.shape, egui::Shape::Mesh(mesh) if mesh.texture_id == photo.texture.id() && !mesh.vertices.is_empty()))).map(|photo| photo.index).collect::<Vec<_>>();
        let requested = visible_contact_indices(rect, count);
        assert_eq!(
            requested, painted,
            "prefetch must exactly name drawable photo identities at{size:?}"
        );
        saw_hidden |= painted.is_empty();
        saw_photos |= painted.len() >= 8;
    }
    assert!(
        saw_hidden && saw_photos,
        "fixture must exercise both compact suppression and a real contact board"
    );
    assert!(
        visible_contact_indices(
            Rect::from_min_size(Pos2::ZERO, egui::vec2(150.0, 570.0)),
            count
        )
        .is_empty()
    );
    assert!(
        visible_contact_indices(Rect::from_min_size(Pos2::ZERO, egui::vec2(296.0, 570.0)), 1)
            .is_empty()
    );
}

#[test]
fn real_edges_are_additive_in_capture_space_and_survive_finished_photo() {
    let ctx = egui::Context::default();
    let mut progress = PipelineProgress::default();
    progress.ingest("STREHL_UI_PROGRESS event=stage name=alignment total=10\nSTREHL_UI_PROGRESS event=align-phase name=pairs frames=10 total=20\nSTREHL_UI_PROGRESS event=align-pair i=1 j=8 completed=1 accepted=1 frames=10 total=20\n");
    let (_, first) = draw(&ctx, input(&progress, 10), 0.0, vec![]);
    assert_eq!(
        edge(&first, [1, 8], 10).len(),
        2,
        "the actual completed fit plus last-pair highlight must appear"
    );
    assert!(
        edge(&first, [2, 7], 10).is_empty(),
        "a plausible but unobserved pair is not a processing edge"
    );
    assert!(has(&first, "CAPTURES / DIRECT FITS"));
    progress.ingest(
        "STREHL_UI_PROGRESS event=align-pair i=2 j=7 completed=2 accepted=1 frames=10 total=20\n",
    );
    let (_, second) = draw(&ctx, input(&progress, 10), 0.1, vec![]);
    assert_eq!(edge(&second, [1, 8], 10).len(), 1);
    assert_eq!(edge(&second, [2, 7], 10).len(), 2);
    assert_ne!(
        edge(&second, [1, 8], 10)[0].color,
        edge(&second, [2, 7], 10)[0].color,
        "accepted and refused evidence must remain distinct"
    );
    progress.mark_complete();
    let _ = draw(&ctx, input(&progress, 10), 0.5, vec![]);
    let (_, finished) = draw(&ctx, input(&progress, 10), 1.0, vec![]);
    assert!(!edge(&finished, [1, 8], 10).is_empty());
    assert!(!edge(&finished, [2, 7], 10).is_empty());
    assert!(
        edge(&finished, [1, 8], 10)[0].color.a() < edge(&second, [1, 8], 10)[0].color.a(),
        "the graph yields visually to the finished photograph without losing history"
    );
    let (_, reset) = draw(&ctx, input(&PipelineProgress::default(), 10), 1.1, vec![]);
    assert!(
        edge(&reset, [1, 8], 10).is_empty(),
        "another capture cannot inherit prior observed edges"
    );
}

#[test]
fn graph_display_cap_is_disclosed_and_keeps_earliest_observed_edges_fixed() {
    let ctx = egui::Context::default();
    let mut progress = PipelineProgress::default();
    progress.stage = Stage::Alignment;
    for index in 1..=1200 {
        progress
            .alignment_edge_observations
            .push_back(AlignmentEdgeObservation {
                pair: [0, index],
                outcome: AlignmentOutcome::Unknown,
                completed: index,
            });
    }
    let (_, output) = draw(&ctx, input(&progress, 1500), 0.0, vec![]);
    assert_eq!(edge(&output, [0, 1], 1500).len(), 1);
    assert_eq!(edge(&output, [0, EDGE_CAP], 1500).len(), 1);
    assert!(edge(&output, [0, EDGE_CAP + 1], 1500).is_empty());
    assert!(has(&output, "1024/1200 OBSERVED EDGES SHOWN"));
    assert!(has(&output, "256/1500 NODE MARKERS"));
    progress
        .alignment_edge_observations
        .push_back(AlignmentEdgeObservation {
            pair: [1, 1499],
            outcome: AlignmentOutcome::Accepted,
            completed: 1201,
        });
    let (_, newer) = draw(&ctx, input(&progress, 1500), 0.1, vec![]);
    assert_eq!(
        edge(&newer, [0, 1], 1500),
        edge(&output, [0, 1], 1500),
        "new observations cannot make retained display edges hop"
    );
    assert!(has(&newer, "1024/1201 OBSERVED EDGES SHOWN"));
    progress.alignment_edge_history_omitted = 7;
    let (_, saturated) = draw(&ctx, input(&progress, 1500), 0.2, vec![]);
    assert!(has(
        &saturated,
        "1024/1201 EDGES SHOWN · +7 HISTORY OMITTED"
    ));
}

#[test]
fn actual_pair_endpoints_select_their_camera_capture_and_blank_graph_does_not() {
    let ctx = egui::Context::default();
    let mut progress = PipelineProgress::default();
    progress.ingest("STREHL_UI_PROGRESS event=stage name=alignment total=10\nSTREHL_UI_PROGRESS event=align-phase name=pairs frames=10 total=20\nSTREHL_UI_PROGRESS event=align-pair-start i=2 j=9 started=1 total=20 frames=10\n");
    let _ = draw(&ctx, input(&progress, 10), 0.0, vec![]);
    let at = position(diagram(), 9, 10);
    let click = |at, pressed| egui::Event::PointerButton {
        pos: at,
        button: egui::PointerButton::Primary,
        pressed,
        modifiers: egui::Modifiers::NONE,
    };
    let _ = draw(
        &ctx,
        input(&progress, 10),
        0.1,
        vec![egui::Event::PointerMoved(at), click(at, true)],
    );
    let (selected, output) = draw(&ctx, input(&progress, 10), 0.2, vec![click(at, false)]);
    assert_eq!(selected, Some(Pick::Frame(9)));
    assert!(has(&output, "B 010") && has(&output, "DIRECT COMPARISON IN PROGRESS"));
    let blank = diagram().center();
    let _ = draw(
        &ctx,
        input(&progress, 10),
        0.3,
        vec![egui::Event::PointerMoved(blank), click(blank, true)],
    );
    let (selected, _) = draw(&ctx, input(&progress, 10), 0.4, vec![click(blank, false)]);
    assert_eq!(selected, None);
    progress.alignment_latest_pair = progress.alignment_current_pair.take();
    let (_, last) = draw(&ctx, input(&progress, 10), 0.5, vec![]);
    assert!(has(&last, "LAST OBSERVED DIRECT PAIR"));
    assert!(
        !has(&last, "DIRECT COMPARISON IN PROGRESS"),
        "a latest completed fallback cannot claim an active comparison"
    );
}

#[test]
fn read_and_prepared_nodes_use_actual_ids_instead_of_a_completed_prefix() {
    let ctx = egui::Context::default();
    let mut progress = PipelineProgress::default();
    progress.ingest("STREHL_UI_PROGRESS event=stage name=alignment total=10\nSTREHL_UI_PROGRESS event=align-phase name=planes frames=10 total=10\nSTREHL_UI_PROGRESS event=align-plane index=8 completed=1 frames=10 total=10\nSTREHL_UI_PROGRESS event=align-phase name=pyramids frames=10 total=10\nSTREHL_UI_PROGRESS event=align-pyramid index=8 completed=1 frames=10 total=10\n");
    assert!(
        progress.alignment_plane_observations.contains(&8)
            && progress.alignment_pyramid_observations.contains(&8),
        "the fixture must deliver accepted sparse observations through the real parser"
    );
    let (_, output) = draw(&ctx, input(&progress, 10), 0.0, vec![]);
    let circles = |frame| {
        output
            .shapes
            .iter()
            .filter_map(|shape| match &shape.shape {
                egui::Shape::Circle(circle)
                    if circle.center.distance(position(diagram(), frame, 10)) < 0.01 =>
                {
                    Some(circle)
                }
                _ => None,
            })
            .collect::<Vec<_>>()
    };
    assert!(
        circles(8).iter().any(|circle| circle.radius > 3.0),
        "observed prepared capture receives its outer ring"
    );
    assert!(
        circles(0)
            .iter()
            .all(|circle| (circle.radius - 3.2).abs() > 0.01),
        "a completed count of one cannot invent a prepared first capture"
    );
    assert!(nodes(1500).len() <= NODE_CAP && nodes(1500).contains(&1499));
}

#[test]
fn photographic_contacts_keep_capture_positions_through_late_pixels_and_pair_changes() {
    use crate::workbench::SourcePhoto;
    let ctx = egui::Context::default();
    let mut progress = PipelineProgress::default();
    progress.stage = Stage::Alignment;
    progress.alignment_current_pair = Some([3, 15]);
    let anchors: Vec<_> = contacts(diagram(), 16).iter().map(|c| c.frame).collect();
    assert!(
        anchors.len() > 8,
        "the wide pane must expose more than the old fixed eight contacts"
    );
    assert!(contacts(diagram(), 0).is_empty());
    let photos: Vec<_> = anchors
        .iter()
        .map(|&index| SourcePhoto {
            epoch: 1,
            index,
            aperture: [90, 60],
            texture: ctx.load_texture(
                format!("actual-network-source-{index}"),
                egui::ColorImage::filled(
                    [90, 60],
                    Color32::from_rgb(20 + index as u8 * 10, 60, 90),
                ),
                egui::TextureOptions::NEAREST,
            ),
        })
        .collect();
    let image_rect = |output: &egui::FullOutput, id: egui::TextureId| {
        output.shapes.iter().find_map(|shape| match &shape.shape {
            egui::Shape::Mesh(mesh) if mesh.texture_id == id => Some(Rect::from_points(
                &mesh
                    .vertices
                    .iter()
                    .map(|vertex| vertex.pos)
                    .collect::<Vec<_>>(),
            )),
            _ => None,
        })
    };
    let early = [photos[0].clone(), photos[4].clone()];
    let early_indices = [early[0].index, early[1].index];
    let (_, first) = draw(
        &ctx,
        Input {
            photos: &early,
            ..input(&progress, 16)
        },
        0.0,
        vec![],
    );
    for photo in &early {
        let rect = image_rect(&first, photo.texture.id())
            .expect("available source must paint actual camera pixels");
        assert_eq!(
            rect,
            contacts(diagram(), 16)
                .iter()
                .find(|card| card.frame == photo.index)
                .unwrap()
                .image
        );
    }
    assert!(
        photos
            .iter()
            .filter(|photo| !early_indices.contains(&photo.index))
            .all(|photo| image_rect(&first, photo.texture.id()).is_none()),
        "the fixture must include contacts whose actual pixels have not arrived yet"
    );
    progress.alignment_current_pair = Some([2, 9]);
    let late: Vec<_> = photos.iter().rev().cloned().collect();
    let data = Input {
        photos: &late,
        ..input(&progress, 16)
    };
    let (_, arrived) = draw(&ctx, data, 0.1, vec![]);
    for photo in &photos {
        let rect = image_rect(&arrived, photo.texture.id()).unwrap();
        assert_eq!(
            rect,
            contacts(diagram(), 16)
                .iter()
                .find(|card| card.frame == photo.index)
                .unwrap()
                .image,
            "capture{} cannot be positioned by delivery order or live comparison",
            photo.index
        );
        if early_indices.contains(&photo.index) {
            assert_eq!(
                Some(rect),
                image_rect(&first, photo.texture.id()),
                "late neighbours must not move an existing contact"
            );
        }
    }
    let at = image_rect(&arrived, photos[6].texture.id())
        .unwrap()
        .center();
    let pointer = |pressed| egui::Event::PointerButton {
        pos: at,
        button: egui::PointerButton::Primary,
        pressed,
        modifiers: egui::Modifiers::NONE,
    };
    let _ = draw(
        &ctx,
        data,
        0.2,
        vec![egui::Event::PointerMoved(at), pointer(true)],
    );
    let (selected, _) = draw(&ctx, data, 0.3, vec![pointer(false)]);
    assert_eq!(
        selected,
        Some(Pick::Frame(photos[6].index)),
        "clicking an actual contact must select its labelled capture identity"
    );
    let (_, imported) = draw(&ctx, Input { epoch: 2, ..data }, 0.4, vec![]);
    assert!(
        photos
            .iter()
            .all(|photo| image_rect(&imported, photo.texture.id()).is_none()),
        "another import cannot reuse old camera contacts"
    );
}

#[test]
fn compact_photo_slots_and_all_labels_are_separate_visible_and_tied_to_real_nodes() {
    use crate::workbench::SourcePhoto;
    // Actual network allocation at the supported 1060 and 1440 point widths,
    // including its offset inside the complete process workspace.
    for panel in [
        Rect::from_min_size(egui::pos2(16.0, 156.0), egui::vec2(176.0, 226.0)),
        Rect::from_min_size(egui::pos2(16.0, 156.0), egui::vec2(216.0, 348.0)),
        Rect::from_min_size(egui::pos2(16.0, 156.0), egui::vec2(296.0, 570.0)),
    ] {
        for count in [2, 3, 12, 259] {
            let ctx = egui::Context::default();
            let mut progress = PipelineProgress::default();
            progress.stage = Stage::Alignment;
            progress.alignment_phase = Some(AlignmentPhase::Pairs);
            progress.alignment_current_pair = Some([0, count - 1]);
            progress.alignment_pairs = Some((1, 1, 33));
            progress
                .alignment_edge_observations
                .push_back(AlignmentEdgeObservation {
                    pair: [0, count - 1],
                    outcome: AlignmentOutcome::Accepted,
                    completed: 1,
                });
            if count > NODE_CAP {
                progress.alignment_edge_history_omitted = 7;
            }
            let photos: Vec<_> = visible_contact_indices(panel, count)
                .into_iter()
                .map(|index| SourcePhoto {
                    epoch: 1,
                    index,
                    aperture: [90, 60],
                    texture: ctx.load_texture(
                        format!("compact-contact-{index}"),
                        egui::ColorImage::filled([90, 60], Color32::GRAY),
                        egui::TextureOptions::NEAREST,
                    ),
                })
                .collect();
            let (_, output) = draw_at(
                &ctx,
                Input {
                    photos: &photos,
                    ..input(&progress, count)
                },
                panel,
                0.0,
                vec![],
            );
            let text: Vec<_> = output
                .shapes
                .iter()
                .filter_map(|shape| match &shape.shape {
                    egui::Shape::Text(text) => Some((
                        text.galley.text().to_owned(),
                        Rect::from_min_size(text.pos, text.galley.size()),
                    )),
                    _ => None,
                })
                .collect();
            let images: Vec<_> = photos.iter().map(|photo| {
                let (rect, clip) = output.shapes.iter().find_map(|shape| match &shape.shape {
                    egui::Shape::Mesh(mesh) if mesh.texture_id == photo.texture.id() => Some((
                        Rect::from_points(&mesh.vertices.iter().map(|v| v.pos).collect::<Vec<_>>()),
                        shape.clip_rect,
                    )),
                    _ => None,
                }).expect("fixture must paint each actual source photo");
                assert!(panel.contains_rect(rect) && clip.contains_rect(rect));
                assert!(rect.width() >= 40.0, "avoid solving overlaps by making photographs unreadably small");
                let caption = format!("{:03}", photo.index + 1);
                assert_eq!(text.iter().filter(|(value, _)| value == &caption).count(), 1,
                    "each sampled capture gets one ordinal, with no duplicate floating graph label");
                let label = text.iter().find(|(value, _)| value == &caption).unwrap().1;
                assert!(label.top() >= rect.bottom() && label.left() >= rect.left() - 0.01 && label.right() <= rect.right() + 0.01);
                let node = position(diagram_rect(panel), photo.index, count);
                assert!(!rect.contains(node), "the exact graph endpoint must remain visible beside its photo");
                let cards = contacts(diagram_rect(panel), count);
                let routes = contact_routes(diagram_rect(panel), count, &cards);
                let route = cards.iter().position(|card| card.frame == photo.index)
                    .map(|index| &routes[index]).unwrap();
                assert_eq!(route.first().copied(), Some(node));
                assert!(route.windows(2).map(|pair| pair[0].distance(pair[1])).sum::<f32>() > 6.0,
                    "leader must extend visibly beyond the node ring");
                for segment in route.windows(2) {
                    assert!(output.shapes.iter().any(|shape| matches!(&shape.shape,
                        egui::Shape::LineSegment { points, stroke }
                            if points[0].distance(segment[0]) < 0.01 && points[1].distance(segment[1]) < 0.01
                                && (stroke.color == LINE || stroke.color == ACCENT.gamma_multiply(0.75))
                    )), "capture {} needs every leg of its routed real-index leader painted", photo.index + 1);
                }
                rect
            }).collect();
            for (index, image) in images.iter().enumerate() {
                assert!(
                    images[index + 1..]
                        .iter()
                        .all(|other| !image.expand(2.0).intersects(other.expand(2.0))),
                    "camera cards must not overlap at {count} captures, {} points",
                    panel.width()
                );
            }
            for (index, (label, bounds)) in text.iter().enumerate() {
                assert!(
                    panel.contains_rect(*bounds),
                    "{label:?} must be fully inside the network panel"
                );
                assert!(
                    images.iter().all(|image| !bounds.intersects(*image)),
                    "{label:?} must not land on photograph pixels"
                );
                for (other, rect) in &text[index + 1..] {
                    assert!(
                        !bounds.intersects(*rect),
                        "labels {label:?} and {other:?} overlap at {count} captures, {} points",
                        panel.width()
                    );
                }
            }
            let data = Input {
                photos: &photos,
                ..input(&progress, count)
            };
            let first = images[0].center();
            let click = |pressed| egui::Event::PointerButton {
                pos: first,
                button: egui::PointerButton::Primary,
                pressed,
                modifiers: egui::Modifiers::NONE,
            };
            let _ = draw_at(
                &ctx,
                data,
                panel,
                0.1,
                vec![egui::Event::PointerMoved(first), click(true)],
            );
            let (chosen, _) = draw_at(&ctx, data, panel, 0.2, vec![click(false)]);
            assert_eq!(chosen, Some(Pick::Frame(0)));

            // The original 12-frame placement must fail this geometry check.
            // Its 001 and 002 cards share space even before either has pixels.
            if count == 12 && panel.width() < 220.0 {
                let diagram = diagram_rect(panel);
                let width = (panel.width() * 0.23).clamp(38.0, 70.0);
                let old: Vec<_> = (0..8)
                    .map(|slot| slot * count / 8)
                    .map(|frame| {
                        let angle = -std::f32::consts::FRAC_PI_2
                            + std::f32::consts::TAU * frame as f32 / count as f32;
                        Rect::from_center_size(
                            diagram.center()
                                + egui::vec2(
                                    angle.cos() * diagram.width() * 0.34,
                                    angle.sin() * diagram.height() * 0.37,
                                ),
                            egui::vec2(width, width * 0.67),
                        )
                    })
                    .collect();
                assert!(
                    old.windows(2)
                        .any(|pair| pair[0].expand(2.0).intersects(pair[1].expand(2.0))),
                    "the negative control must recreate the observed adjacent-photo collision"
                );
            }
        }
    }
}

#[test]
fn displaced_contacts_leave_observed_edge_clicks_and_empty_graph_distinct() {
    let ctx = egui::Context::default();
    let panel = Rect::from_min_size(Pos2::ZERO, egui::vec2(216.0, 348.0));
    let mut progress = PipelineProgress::default();
    progress.stage = Stage::Alignment;
    progress
        .alignment_edge_observations
        .push_back(AlignmentEdgeObservation {
            pair: [2, 9],
            outcome: AlignmentOutcome::Accepted,
            completed: 1,
        });
    let a = position(diagram_rect(panel), 2, 12);
    let b = position(diagram_rect(panel), 9, 12);
    let middle = a.lerp(b, 0.5);
    assert!(
        contacts(diagram_rect(panel), 12)
            .iter()
            .all(|contact| !contact.bounds.contains(middle)),
        "fixture must target the actual comparison line, not a photo hit box"
    );
    let _ = draw_at(&ctx, input(&progress, 12), panel, 0.0, vec![]);
    for (index, (at, expected)) in [
        (middle, Some(Pick::Pair([2, 9]))),
        (diagram_rect(panel).center() + egui::vec2(0.0, 14.0), None),
    ]
    .into_iter()
    .enumerate()
    {
        let click = |pressed| egui::Event::PointerButton {
            pos: at,
            button: egui::PointerButton::Primary,
            pressed,
            modifiers: egui::Modifiers::NONE,
        };
        let _ = draw_at(
            &ctx,
            input(&progress, 12),
            panel,
            0.1 + index as f64,
            vec![egui::Event::PointerMoved(at), click(true)],
        );
        let (selected, _) = draw_at(
            &ctx,
            input(&progress, 12),
            panel,
            0.2 + index as f64,
            vec![click(false)],
        );
        assert_eq!(selected, expected);
    }
}

#[test]
fn short_resize_never_paints_inverted_graphs_or_squeezes_contacts_over_each_other() {
    let ctx = egui::Context::default();
    let mut progress = PipelineProgress::default();
    progress.stage = Stage::Alignment;
    progress.alignment_current_pair = Some([0, 11]);
    for (index, height) in [100.0, 140.0, 180.0, 220.0].into_iter().enumerate() {
        let panel = Rect::from_min_size(egui::pos2(16.0, 20.0), egui::vec2(216.0, height));
        let (_, output) = draw_at(&ctx, input(&progress, 12), panel, index as f64, vec![]);
        assert!(has(&output, "CAPTURES / DIRECT FITS"));
        assert_eq!(
            contacts(diagram_rect(panel), 12).len(),
            if height >= 220.0 { 4 } else { 0 },
            "only the last aperture has enough room for four legible corner photographs"
        );
        for shape in &output.shapes {
            match &shape.shape {
                egui::Shape::Text(text) => {
                    assert!(panel.contains_rect(Rect::from_min_size(text.pos, text.galley.size())))
                }
                egui::Shape::LineSegment { points, .. } => {
                    assert!(points.iter().all(|point| panel.contains(*point)))
                }
                egui::Shape::Circle(circle) => {
                    assert!(panel.contains_rect(Rect::from_center_size(
                        circle.center,
                        egui::vec2(circle.radius * 2.0, circle.radius * 2.0)
                    )))
                }
                egui::Shape::Mesh(_) => {
                    panic!("no photograph pixels may paint outside the undersized board")
                }
                _ => {}
            }
        }
        if height < 144.0 {
            assert!(
                output.shapes.iter().all(|shape| !matches!(
                    &shape.shape,
                    egui::Shape::Circle(_) | egui::Shape::LineSegment { .. }
                )),
                "header-only fallback must not pass an inverted or tiny diagram to graph painting"
            );
        }
    }
}

#[test]
fn resizing_keeps_actual_node_orbit_circular_and_uses_spare_space_for_more_photographs() {
    let ctx = egui::Context::default();
    let progress = PipelineProgress::default();
    let panels = [
        egui::vec2(216.0, 348.0),
        egui::vec2(296.0, 570.0),
        egui::vec2(740.0, 570.0),
    ];
    let mut counts = Vec::new();
    for (step, size) in panels.into_iter().enumerate() {
        let panel = Rect::from_min_size(egui::pos2(20.0, 30.0), size);
        let (_, output) = draw_at(&ctx, input(&progress, 16), panel, step as f64, vec![]);
        let orbit = output
            .shapes
            .iter()
            .find_map(|shape| match &shape.shape {
                egui::Shape::Path(path) if path.points.len() == 97 => Some(&path.points),
                _ => None,
            })
            .expect("the fixture must paint the actual index orbit");
        let bounds = Rect::from_points(orbit);
        assert!(
            (bounds.width() - bounds.height()).abs() < 0.01,
            "screen aspect ratio must not distort the graph into an oval"
        );
        let d = diagram_rect(panel);
        assert!(
            (d.width() * 0.38 - d.height() * 0.44).abs() > 10.0,
            "negative control: the old independent x/y radius must fail on this aperture"
        );
        let cards = contacts(d, 259);
        counts.push(cards.len());
        for (index, card) in cards.iter().enumerate() {
            assert!(card.image.width() >= 40.0 && d.contains_rect(card.bounds));
            assert!(
                cards[index + 1..]
                    .iter()
                    .all(|other| !card.bounds.expand(2.0).intersects(other.bounds.expand(2.0))),
                "growing the board must never buy density by hiding captions under photographs"
            );
        }
    }
    assert!(
        counts[0] >= 8 && counts[1] > counts[0] && counts[2] > counts[1],
        "extra height and extra width must both expose more captures, got {counts:?}"
    );
}

#[test]
fn dragging_index_ring_reaches_unsampled_captures_and_keyboard_continues_that_selection() {
    let ctx = egui::Context::default();
    let progress = PipelineProgress::default();
    let count = 1500;
    let target = (600..900)
        .find(|frame| {
            !nodes(count).contains(frame)
                && !contacts(diagram(), count).iter().any(|c| c.frame == *frame)
        })
        .unwrap();
    let mut data = input(&progress, count);
    let _ = draw(&ctx, data, 0.0, vec![]);
    let start = position(diagram(), 1, count);
    let finish = position(diagram(), target, count);
    let button = |pos, pressed| egui::Event::PointerButton {
        pos,
        button: egui::PointerButton::Primary,
        pressed,
        modifiers: egui::Modifiers::NONE,
    };
    let _ = draw(
        &ctx,
        data,
        0.1,
        vec![egui::Event::PointerMoved(start), button(start, true)],
    );
    let (pick, _) = draw(&ctx, data, 0.2, vec![egui::Event::PointerMoved(finish)]);
    assert_eq!(
        pick,
        Some(Pick::Frame(target)),
        "dragging the real ring must reach a capture missing from both sampled display lists"
    );
    data.selected = target;
    let _ = draw(&ctx, data, 0.3, vec![button(finish, false)]);
    let key = |key| egui::Event::Key {
        key,
        physical_key: None,
        pressed: true,
        repeat: false,
        modifiers: egui::Modifiers::NONE,
    };
    let (next, _) = draw(&ctx, data, 0.4, vec![key(egui::Key::ArrowRight)]);
    assert_eq!(next, Some(Pick::Frame(target + 1)));
    let (last, _) = draw(&ctx, data, 0.5, vec![key(egui::Key::End)]);
    assert_eq!(last, Some(Pick::Frame(count - 1)));
    let (space, _) = draw(&ctx, data, 0.6, vec![key(egui::Key::Space)]);
    assert_eq!(
        space, None,
        "the workspace's clean-photograph gesture cannot synthesize a ring click"
    );
}

#[test]
fn hover_traces_real_incident_edges_without_changing_workspace_selection() {
    let ctx = egui::Context::default();
    let mut progress = PipelineProgress::default();
    progress.stage = Stage::Merge;
    progress.alignment_edge_observations.extend([
        AlignmentEdgeObservation {
            pair: [2, 9],
            outcome: AlignmentOutcome::Accepted,
            completed: 1,
        },
        AlignmentEdgeObservation {
            pair: [4, 5],
            outcome: AlignmentOutcome::Refused,
            completed: 2,
        },
        AlignmentEdgeObservation {
            pair: [4, 16],
            outcome: AlignmentOutcome::Accepted,
            completed: 3,
        },
    ]);
    let data = Input {
        selected: 2,
        ..input(&progress, 10)
    };
    let (_, idle) = draw(&ctx, data, 0.0, vec![]);
    let (pick, hover) = draw(
        &ctx,
        data,
        0.1,
        vec![egui::Event::PointerMoved(position(diagram(), 4, 10))],
    );
    assert_eq!(
        pick, None,
        "hover must not suspend follow-along or select a different camera preview"
    );
    assert!(edge(&hover, [4, 5], 10)[0].color.a() > edge(&idle, [4, 5], 10)[0].color.a());
    assert!(edge(&hover, [2, 9], 10)[0].color.a() < edge(&idle, [2, 9], 10)[0].color.a());
    assert!(
        has(&hover, "005 · 0 fit / 1 refused"),
        "the invalid comparison must not manufacture accepted evidence"
    );
    assert!(edge(&hover, [4, 16], 10).is_empty());
}

#[test]
fn merge_receipts_accrue_at_their_actual_capture_even_when_alignment_is_over() {
    let ctx = egui::Context::default();
    let mut progress = PipelineProgress::default();
    progress.stage = Stage::Merge;
    progress.bands = Some(8);
    progress.merge_frame_observations.insert(
        9,
        crate::pipeline::MergeFrameObservation {
            fold_finished: (1 << 1) | (1 << 5),
            ..Default::default()
        },
    );
    let (_, output) = draw(
        &ctx,
        Input {
            selected: 9,
            ..input(&progress, 10)
        },
        0.0,
        vec![],
    );
    assert!(has(&output, "010 · 0 fit / 0 refused · 2/8 sizes"));
    let node = position(diagram(), 9, 10);
    let direction = (node - diagram().center()).normalized();
    let start = node + direction * 6.0;
    assert!(output.shapes.iter().any(|shape| matches!(&shape.shape,
        egui::Shape::LineSegment { points, stroke } if points[0].distance(start) < 0.01 && stroke.color == GREEN
            && (points[1].distance(points[0]) - 1.5).abs() < 0.01)), "two actual fold receipts must paint a quarter-length tick on capture ten");
    assert!(
        folded(&input(&progress, 10), 0).is_none(),
        "sparse frame receipts cannot fill an earlier capture prefix"
    );
}

#[test]
fn photographic_shelf_leaders_route_around_all_other_contacts() {
    let mut blocked_straight_leaders = 0;
    let mut bends = 0;
    for size in [
        egui::vec2(176.0, 226.0),
        egui::vec2(216.0, 348.0),
        egui::vec2(296.0, 570.0),
        egui::vec2(740.0, 570.0),
        egui::vec2(980.0, 820.0),
    ] {
        let panel = Rect::from_min_size(egui::pos2(32.0, 42.0), size);
        let diagram = diagram_rect(panel);
        for count in [12, 259] {
            let cards = contacts(diagram, count);
            let paths = contact_routes(diagram, count, &cards);
            assert_eq!(paths.len(), cards.len());
            for (index, (card, path)) in cards.iter().zip(paths).enumerate() {
                let node = position(diagram, card.frame, count);
                assert!(
                    !path.is_empty(),
                    "capture {} needs a visible route at {size:?}",
                    card.frame
                );
                assert_eq!(path[0], node);
                assert!(card.bounds.contains(*path.last().unwrap()));
                assert!(
                    path.iter()
                        .all(|point| diagram.expand(0.01).contains(*point))
                );
                bends += usize::from(path.len() > 3);
                for (other_index, obstacle) in cards.iter().enumerate() {
                    if other_index == index {
                        continue;
                    }
                    blocked_straight_leaders += usize::from(segment_crosses_box(
                        node,
                        *path.last().unwrap(),
                        obstacle.bounds,
                    ));
                    for pair in path.windows(2) {
                        assert!(
                            !segment_crosses_box(pair[0], pair[1], obstacle.bounds.expand(1.0)),
                            "capture {} route {:?} passes under capture {} at {size:?}",
                            card.frame,
                            pair,
                            obstacle.frame
                        );
                    }
                }
            }
        }
    }
    assert!(
        blocked_straight_leaders > 0,
        "negative control must recreate obscured old straight leaders"
    );
    assert!(
        bends > 0,
        "fixture must actually exercise routed shelf leaders"
    );
}

#[test]
fn completed_network_keeps_observed_read_and_scale_evidence_legible() {
    let ctx = egui::Context::default();
    let mut progress = PipelineProgress::default();
    progress.stage = Stage::Complete;
    progress.alignment_plane_observations.insert(3);
    progress.alignment_pyramid_observations.insert(3);
    let (_, output) = draw(&ctx, input(&progress, 12), 1.0, vec![]);
    let at = position(diagram(), 3, 12);
    assert!(output.shapes.iter().any(|shape| matches!(&shape.shape,
        egui::Shape::Circle(circle) if circle.center == at && circle.fill.a() >= 190 && circle.radius == 2.0
    )), "actual observed evidence must not fade away after alignment");
    assert!(output.shapes.iter().any(|shape| matches!(&shape.shape,
        egui::Shape::Circle(circle) if circle.center == at && circle.stroke.color.a() >= 125 && circle.radius == 3.2
    )));
}

#[test]
fn contact_context_menu_links_only_actual_valid_comparisons_to_the_viewer() {
    let ctx = egui::Context::default();
    let mut progress = PipelineProgress::default();
    progress.alignment_edge_observations.extend([
        AlignmentEdgeObservation {
            pair: [0, 11],
            outcome: AlignmentOutcome::Accepted,
            completed: 1,
        },
        AlignmentEdgeObservation {
            pair: [0, 19],
            outcome: AlignmentOutcome::Accepted,
            completed: 2,
        },
    ]);
    let data = input(&progress, 12);
    let _ = draw(&ctx, data, 0.0, vec![]);
    let contact = contacts(diagram(), 12)
        .into_iter()
        .find(|card| card.frame == 0)
        .unwrap();
    let button = |pos, button, pressed| egui::Event::PointerButton {
        pos,
        button,
        pressed,
        modifiers: egui::Modifiers::NONE,
    };
    let at = contact.image.center();
    let _ = draw(
        &ctx,
        data,
        0.1,
        vec![
            egui::Event::PointerMoved(at),
            button(at, egui::PointerButton::Secondary, true),
        ],
    );
    let _ = draw(
        &ctx,
        data,
        0.12,
        vec![button(at, egui::PointerButton::Secondary, false)],
    );
    let (_, menu) = draw(&ctx, data, 0.2, vec![]);
    assert!(has(&menu, "Show in viewer"));
    assert!(
        !has(&menu, "001 / 020  fit"),
        "invalid frame identity cannot enter the action list"
    );
    let compare = menu
        .shapes
        .iter()
        .find_map(|shape| match &shape.shape {
            egui::Shape::Text(text) if text.galley.text() == "001 / 012  fit" => {
                Some(Rect::from_min_size(text.pos, text.galley.size()).center())
            }
            _ => None,
        })
        .expect("menu must expose the actual observed direct comparison");
    let _ = draw(
        &ctx,
        data,
        0.3,
        vec![
            egui::Event::PointerMoved(compare),
            button(compare, egui::PointerButton::Primary, true),
        ],
    );
    let (pick, _) = draw(
        &ctx,
        data,
        0.32,
        vec![button(compare, egui::PointerButton::Primary, false)],
    );
    assert_eq!(pick, Some(Pick::Pair([0, 11])));
}
