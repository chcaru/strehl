use super::*;
use crate::pipeline::{
    DiagnosticKind, DiagnosticScale, DiagnosticScope, DiagnosticSurface, PipelineProgress,
};

#[test]
fn releasing_a_transient_source_keeps_deliberately_pinned_ranges() {
    let mut participation = CaptureParticipation::default();
    participation.select(2, false, false);
    participation.select(6, true, false);
    let spans = participation.spans().to_vec();
    assert!(
        !spans.is_empty(),
        "control must contain an actual pinned span"
    );
    participation.active_source = Some(4);
    participation.held = Some(4);
    participation.source_drag = true;
    participation.hover_sweep = Some(HoverSweep {
        frame: 4,
        inside_at: 1.0,
    });
    participation.wheel_frame = Some(5);
    participation.release_source();
    assert_eq!(participation.spans(), spans);
    assert_eq!(participation.active_source, None);
    assert_eq!(participation.held, None);
    assert_eq!(participation.wheel_frame, None);
    assert!(!participation.source_drag && participation.hover_sweep.is_none());
}

#[test]
fn rendered_timeline_caption_uses_photo_pixels_or_explicit_grid_units() {
    for (writer, expected) in [
        (
            Some("stack.tiff (262 x 198, 16-bit RGB, sRGB, Malvar-He-Cutler demosaic)"),
            "2px photo",
        ),
        (
            Some("stack.tiff (131 x 99, 16-bit RGB, sRGB, binned from one 2x2 quad per pixel)"),
            "1px photo",
        ),
        (None, "1px grid"),
    ] {
        let ctx = egui::Context::default();
        let mut progress = PipelineProgress::default();
        progress.bands = Some(3);
        progress.output_geometry = writer.map(|value| {
            crate::process_output_space::OutputGeometry::parse(value)
                .expect("known writer geometry")
        });
        progress.mark_complete();
        let mut row = CaptureParticipation::default();
        let output = ctx.run(
            egui::RawInput {
                screen_rect: Some(Rect::from_min_size(Pos2::ZERO, egui::vec2(1060.0, 320.0))),
                ..Default::default()
            },
            |ctx| {
                egui::CentralPanel::default().show(ctx, |ui| {
                    row.show(
                        ui,
                        Rect::from_min_size(egui::pos2(10.0, 10.0), egui::vec2(1040.0, HEIGHT)),
                        &input(&progress, 2),
                        &progress.admission_archive,
                        0,
                        Rect::from_min_max(Pos2::ZERO, egui::pos2(1.0, 1.0)),
                    );
                });
            },
        );
        assert!(
            output.shapes.iter().any(|shape| matches!(&shape.shape,
                egui::Shape::Text(text) if text.galley.text().contains(expected)
            )),
            "missing actual timeline caption {expected}"
        );
    }
}

fn packet(sequence: u64, frame: usize, level: usize, pixels: &[u8]) -> DiagnosticSurface {
    DiagnosticSurface {
        sequence,
        frame,
        level,
        kind: DiagnosticKind::GateSupport,
        scope: DiagnosticScope::Frame,
        scale: DiagnosticScale::Linear,
        width: 4,
        height: 2,
        min: 0.0,
        max: 1.0,
        pixels: pixels.to_vec().into(),
        folded: 1,
    }
}

fn input(progress: &PipelineProgress, frames: usize) -> Input<'_> {
    Input {
        epoch: 1,
        progress,
        frame_count: frames,
        selected: 0,
        inspected_pair: None,
        photos: &[],
        inspection_photos: &[],
        surfaces: &[],
        output: None,
        output_size: None,
    }
}

#[test]
fn spatial_admission_counts_sample_centers_and_preserves_unobserved_regions() {
    // The left half has all support, right half none. A swapped aperture must
    // change the local area while global stays 50%; absence cannot become zero.
    let cells = [true, true, false, false, true, true, false, false];
    let left = Rect::from_min_max(Pos2::ZERO, egui::pos2(0.5, 1.0));
    let right = Rect::from_min_max(egui::pos2(0.5, 0.0), egui::pos2(1.0, 1.0));
    assert_eq!(
        areas(
            AdmissionMeta {
                sequence: 1,
                samples: [4, 2],
                extent: [4, 2]
            },
            0,
            cells.into_iter(),
            left
        ),
        [
            Area {
                observed: 8,
                admitted: 4
            },
            Area {
                observed: 4,
                admitted: 4
            }
        ]
    );
    assert_eq!(
        areas(
            AdmissionMeta {
                sequence: 1,
                samples: [4, 2],
                extent: [4, 2]
            },
            0,
            cells.into_iter(),
            right
        ),
        [
            Area {
                observed: 8,
                admitted: 4
            },
            Area {
                observed: 4,
                admitted: 0
            }
        ]
    );
    let small = Rect::from_min_max(egui::pos2(0.45, 0.45), egui::pos2(0.55, 0.55));
    let [scene, window] = areas(
        AdmissionMeta {
            sequence: 1,
            samples: [4, 2],
            extent: [4, 2],
        },
        0,
        cells.into_iter(),
        small,
    );
    assert_eq!(scene.label(), "50%");
    assert_eq!(window.fraction(), None);
    assert_eq!(window.label(), "—");
    assert_eq!(
        areas(
            AdmissionMeta {
                sequence: 1,
                samples: [4, 2],
                extent: [4, 2]
            },
            0,
            cells.into_iter(),
            right
        )[1]
        .label(),
        "0%"
    );
}

#[test]
fn archive_cell_iterator_matches_actual_packet_across_word_boundaries() {
    let mut archive = AdmissionArchive::default();
    let mut observed = packet(1, 7, 2, &[0; 8]);
    observed.width = 13;
    observed.height = 7;
    observed.pixels = (0..91)
        .map(|i| {
            if [0, 12, 63, 64, 90].contains(&i) {
                255
            } else {
                0
            }
        })
        .collect::<Vec<_>>()
        .into();
    archive.ingest(&observed, [897, 611]);
    let (meta, cells) = archive.cells(2, 7).unwrap();
    assert_eq!(meta.samples, [13, 7]);
    assert_eq!(cells.len(), 91);
    let actual: Vec<_> = cells
        .enumerate()
        .filter_map(|(i, yes)| yes.then_some(i))
        .collect();
    assert_eq!(actual, [0, 12, 63, 64, 90]);
    assert!(archive.cells(2, 8).is_none());
    assert!(archive.cells(3, 7).is_none());
}

#[test]
fn cached_area_refreshes_on_packet_region_level_and_domain_changes() {
    let progress = PipelineProgress::default();
    let mut archive = AdmissionArchive::default();
    archive.ingest(
        &packet(1, 2, 0, &[255, 255, 0, 0, 255, 255, 0, 0]),
        [800, 600],
    );
    archive.ingest(&packet(2, 4, 0, &[0; 8]), [800, 600]);
    archive.ingest(&packet(3, 2, 1, &[255; 8]), [800, 600]);
    let mut row = CaptureParticipation::default();
    let left = Rect::from_min_max(Pos2::ZERO, egui::pos2(0.5, 1.0));
    let right = Rect::from_min_max(egui::pos2(0.5, 0.0), egui::pos2(1.0, 1.0));
    row.update(&input(&progress, 12), &archive, 0, left, 1000.0, HEIGHT);
    assert_eq!(row.evidence[&2].window.label(), "100%");
    assert_eq!(row.evidence[&4].window.label(), "0%");
    assert!(!row.evidence.contains_key(&3));
    row.update(&input(&progress, 12), &archive, 0, right, 1000.0, HEIGHT);
    assert_eq!(row.evidence[&2].window.label(), "0%");
    assert_eq!(row.evidence[&2].scene.label(), "50%");
    archive.ingest(&packet(4, 2, 0, &[255; 8]), [800, 600]);
    row.update(&input(&progress, 12), &archive, 0, right, 1000.0, HEIGHT);
    assert_eq!(row.evidence[&2].scene.label(), "100%");
    row.update(&input(&progress, 12), &archive, 1, right, 1000.0, HEIGHT);
    assert_eq!(row.evidence.len(), 1);
    row.held = Some(2);
    let changed = Input {
        epoch: 2,
        ..input(&progress, 12)
    };
    row.update(
        &changed,
        &AdmissionArchive::default(),
        0,
        right,
        1000.0,
        HEIGHT,
    );
    assert!(row.evidence.is_empty());
    assert!(row.held.is_none());
}

#[test]
fn every_capture_is_scrubbable_including_between_fixed_contact_slots() {
    let rect = Rect::from_min_size(egui::pos2(20.0, 20.0), egui::vec2(1056.0, HEIGHT));
    let contacts = anchors(299, rect.width());
    assert!(
        !contacts.contains(&1),
        "fixture must include a non-thumbnail capture"
    );
    assert_eq!(contacts.first(), Some(&0));
    assert_eq!(contacts.last(), Some(&298));
    let layout = Layout::new(rect, 299, contacts.len()).unwrap();
    for frame in 0..299 {
        assert_eq!(layout.index(layout.x(frame)), frame);
    }
    assert_eq!(layout.index(rect.left() - 100.0), 0);
    assert_eq!(layout.index(rect.right() + 100.0), 298);
}

#[test]
fn narrow_timeline_paints_even_contact_slots_and_addresses_every_capture() {
    let ctx = egui::Context::default();
    let progress = PipelineProgress::default();
    let photos: Vec<_> = (0..12)
        .map(|index| crate::workbench::SourcePhoto {
            epoch: 1,
            index,
            texture: ctx.load_texture(
                format!("narrow-contact-{index}"),
                egui::ColorImage::filled([60, 40], Color32::from_gray(30 + index as u8 * 15)),
                egui::TextureOptions::LINEAR,
            ),
            aperture: [60, 40],
        })
        .collect();
    let data = Input {
        photos: &photos,
        ..input(&progress, 12)
    };
    let mut ribbon = CaptureParticipation::default();
    let rect = Rect::from_min_size(egui::pos2(10.0, 10.0), egui::vec2(716.0, HEIGHT));
    let output = ctx.run(
        egui::RawInput {
            screen_rect: Some(Rect::from_min_size(
                Pos2::ZERO,
                egui::vec2(736.0, HEIGHT + 60.0),
            )),
            ..Default::default()
        },
        |ctx| {
            egui::CentralPanel::default().show(ctx, |ui| {
                ribbon.show(
                    ui,
                    rect,
                    &data,
                    &progress.admission_archive,
                    0,
                    Rect::from_min_max(Pos2::ZERO, egui::pos2(1.0, 1.0)),
                );
            });
        },
    );
    let visible = ribbon.indices();
    assert!(
        visible.len() >= 4 && visible.len() < 12,
        "enlarged contacts trade sampling density for legibility"
    );
    let layout = Layout::new(rect, 12, visible.len()).unwrap();
    for frame in 0..12 {
        assert_eq!(layout.index(layout.x(frame)), frame);
    }
    let mut images = Vec::new();
    for photo in photos.iter().filter(|photo| visible.contains(&photo.index)) {
        let bounds = output
            .shapes
            .iter()
            .find_map(|shape| match &shape.shape {
                egui::Shape::Mesh(mesh) if mesh.texture_id == photo.texture.id() => {
                    let bounds = Rect::from_points(
                        &mesh
                            .vertices
                            .iter()
                            .map(|vertex| vertex.pos)
                            .collect::<Vec<_>>(),
                    );
                    shape.clip_rect.contains_rect(bounds).then_some(bounds)
                }
                _ => None,
            })
            .unwrap_or_else(|| panic!("capture {} must be visibly painted", photo.index + 1));
        images.push(bounds);
    }
    for pair in images.windows(2) {
        let gap = pair[1].left() - pair[0].right();
        assert!((5.0..=9.0).contains(&gap), "unexpected blank/overlap {gap}");
    }
}

#[test]
fn sampled_contact_cards_have_even_spacing_and_keep_their_exact_capture_identity() {
    // Near sampling thresholds the rounded frame intervals alternate between
    // one and two; using their axis positions used to overlap or leave holes.
    for width in [240.0, 580.0, 716.0, 1000.0, 1800.0] {
        for count in [12, 14, 17, 23, 299] {
            let rect = Rect::from_min_size(egui::pos2(20.0, 10.0), egui::vec2(width, HEIGHT));
            let contacts = anchors(count, width);
            let layout = Layout::new(rect, count, contacts.len()).unwrap();
            let mut previous: Option<f32> = None;
            let mut previous_gap: Option<f32> = None;
            for &frame in &contacts {
                let image = layout.contact(frame);
                assert!(rect.contains_rect(image));
                assert_eq!(layout.index_at(image.center(), &contacts), frame);
                for point in [image.left_center(), image.right_center()] {
                    assert_eq!(layout.index_at(point, &contacts), frame);
                }
                if let Some(before) = previous {
                    let gap: f32 = image.left() - before;
                    assert!(
                        gap >= CONTACT_GAP - 0.1,
                        "overlap at {count} captures / {width}px"
                    );
                    if let Some(last) = previous_gap {
                        assert!((gap - last).abs() < 0.002, "uneven visual slots");
                    }
                    previous_gap = Some(gap);
                }
                previous = Some(image.right());
            }
            // Evidence remains on the full, uniformly spaced capture axis.
            for frame in 0..count {
                assert_eq!(layout.index(layout.x(frame)), frame);
            }
        }
    }
}

#[test]
fn adjacent_windows_do_not_double_count_samples_on_their_shared_edge() {
    let cells = [true, false, true, false];
    let left = Rect::from_min_max(Pos2::ZERO, egui::pos2(0.375, 1.0));
    let right = Rect::from_min_max(egui::pos2(0.375, 0.0), egui::pos2(1.0, 1.0));
    let a = areas(
        AdmissionMeta {
            sequence: 1,
            samples: [4, 1],
            extent: [4, 1],
        },
        0,
        cells.into_iter(),
        left,
    )[1];
    let b = areas(
        AdmissionMeta {
            sequence: 1,
            samples: [4, 1],
            extent: [4, 1],
        },
        0,
        cells.into_iter(),
        right,
    )[1];
    assert_eq!((a.observed, b.observed), (1, 3));
    assert_eq!((a.admitted, b.admitted), (1, 1));
}

#[test]
fn admission_plots_show_true_selected_counts_and_do_not_bridge_missing_captures() {
    let ctx = egui::Context::default();
    let mut progress = PipelineProgress::default();
    progress.mark_complete();
    let mut archive = AdmissionArchive::default();
    for (frame, pixels) in [
        (0, [0; 8]),
        (1, [255, 255, 0, 0, 255, 255, 0, 0]),
        (2, [255; 8]),
        (4, [255; 8]),
    ] {
        archive.ingest(&packet(frame as u64 + 1, frame, 0, &pixels), [4, 2]);
    }
    let data = input(&progress, 5);
    let bounds = Rect::from_min_size(egui::pos2(10.0, 10.0), egui::vec2(940.0, HEIGHT));
    let left = Rect::from_min_max(Pos2::ZERO, egui::pos2(0.5, 1.0));
    let right = Rect::from_min_max(egui::pos2(0.5, 0.0), egui::pos2(1.0, 1.0));
    let mut row = CaptureParticipation::default();
    row.update(&data, &archive, 0, left, bounds.width(), bounds.height());
    row.select_frame(1);
    let paint = |row: &mut CaptureParticipation, aperture| {
        ctx.run(
            egui::RawInput {
                screen_rect: Some(Rect::from_min_size(Pos2::ZERO, egui::vec2(980.0, 240.0))),
                ..Default::default()
            },
            |ctx| {
                egui::CentralPanel::default().show(ctx, |ui| {
                    row.show(ui, bounds, &data, &archive, 0, aperture);
                });
            },
        )
    };
    let output = paint(&mut row, left);
    let texts: Vec<_> = output
        .shapes
        .iter()
        .filter_map(|shape| match &shape.shape {
            egui::Shape::Text(text) => Some(text.galley.text()),
            _ => None,
        })
        .collect();
    assert!(texts.contains(&"Full image") && texts.contains(&"Current region"));
    assert!(
        texts
            .iter()
            .any(|text| text.contains("50% full image  /  100% region"))
    );
    let full_curve: Vec<_> = output
        .shapes
        .iter()
        .filter_map(|shape| match &shape.shape {
            egui::Shape::LineSegment { points, stroke }
                if stroke.color == GREEN
                    && (stroke.width - 1.0).abs() < 0.001
                    && points[1].x > points[0].x + 1.0 =>
            {
                Some(*points)
            }
            _ => None,
        })
        .collect();
    assert_eq!(
        full_curve.len(),
        2,
        "only observed neighbors 0→1→2 connect; capture 3 is unknown"
    );
    let layout = Layout::new(bounds, 5, row.anchors.len()).unwrap();
    assert_eq!(
        layout.lane(0),
        layout.lane(1),
        "one graph shares one ordinate"
    );
    assert!(layout.lane(0).height() >= 50.0);
    assert!(
        output.shapes.iter().any(|shape| matches!(&shape.shape,
        egui::Shape::LineSegment { points, stroke } if stroke.color == ACCENT
        && (stroke.width - 1.2).abs() < 0.001 && points[0].distance(points[1]) <= 3.01)),
        "the regional curve is a distinct dashed trace in the same plot"
    );
    assert!(
        layout.contact(0).height() >= 65.0,
        "default contact images must be appreciably larger"
    );
    assert!(full_curve.iter().all(|line| line[1].x <= layout.x(2) + 1.0));
    assert!(full_curve[0][0].y > full_curve[0][1].y && full_curve[1][0].y > full_curve[1][1].y);
    let moved = paint(&mut row, right);
    let texts: Vec<_> = moved
        .shapes
        .iter()
        .filter_map(|shape| match &shape.shape {
            egui::Shape::Text(text) => Some(text.galley.text()),
            _ => None,
        })
        .collect();
    assert!(
        texts
            .iter()
            .any(|text| text.contains("50% full image  /  0% region")),
        "changing only the image region changes local admission, never full-image admission"
    );
}

#[test]
fn taller_timeline_grows_real_contacts_and_wider_timeline_admits_more_contacts() {
    let compact = Rect::from_min_size(Pos2::ZERO, egui::vec2(1040.0, HEIGHT));
    let expanded = Rect::from_min_size(Pos2::ZERO, egui::vec2(1040.0, 278.0));
    let wide = Rect::from_min_size(Pos2::ZERO, egui::vec2(1800.0, HEIGHT));
    let a = anchors_at_height(299, compact.width(), compact.height());
    let b = anchors_at_height(299, expanded.width(), expanded.height());
    let c = anchors_at_height(299, wide.width(), wide.height());
    let compact_layout = Layout::new(compact, 299, a.len()).unwrap();
    let expanded_layout = Layout::new(expanded, 299, b.len()).unwrap();
    let wide_layout = Layout::new(wide, 299, c.len()).unwrap();
    let small = compact_layout.contact(a[0]);
    let large = expanded_layout.contact(b[0]);
    assert!(
        large.height() > small.height() * 1.3 && large.width() > small.width() * 1.15,
        "extra timeline height must become actual image area: {small:?} -> {large:?}"
    );
    assert!(
        c.len() > a.len(),
        "extra width must increase contact density, not stop at16"
    );
    assert!(c.len() >= 10 && c.len() <= MAX_CONTACTS);
    for (bounds, contacts, layout) in [
        (compact, a, compact_layout),
        (expanded, b, expanded_layout),
        (wide, c, wide_layout),
    ] {
        assert_eq!(contacts.first(), Some(&0));
        assert_eq!(contacts.last(), Some(&298));
        for frame in contacts.iter().copied() {
            let card = layout.contact(frame);
            assert!(bounds.contains_rect(card));
            assert_eq!(layout.index_at(card.center(), &contacts), frame);
        }
    }
}

#[test]
fn expanded_contacts_keep_one_compatible_cached_tier_under_a_strict_budget_without_fetching() {
    fn paint(
        row: &mut CaptureParticipation,
        ctx: &egui::Context,
        data: Input<'_>,
        height: f32,
        time: f64,
    ) -> (ParticipationResponse, egui::FullOutput) {
        let mut response = ParticipationResponse::default();
        let output = ctx.run(
            egui::RawInput {
                screen_rect: Some(Rect::from_min_size(Pos2::ZERO, egui::vec2(1060.0, 320.0))),
                time: Some(time),
                ..Default::default()
            },
            |ctx| {
                egui::CentralPanel::default().show(ctx, |ui| {
                    response = row.show(
                        ui,
                        Rect::from_min_size(egui::pos2(10.0, 10.0), egui::vec2(1040.0, height)),
                        &data,
                        &data.progress.admission_archive,
                        0,
                        Rect::from_min_max(Pos2::ZERO, egui::pos2(1.0, 1.0)),
                    );
                });
            },
        );
        (response, output)
    }
    fn painted(output: &egui::FullOutput, id: egui::TextureId) -> Option<(Rect, u8)> {
        output.shapes.iter().find_map(|shape| match &shape.shape {
            egui::Shape::Mesh(mesh) if mesh.texture_id == id && !mesh.vertices.is_empty() => {
                Some((
                    Rect::from_points(&mesh.vertices.iter().map(|v| v.pos).collect::<Vec<_>>()),
                    mesh.vertices[0].color.a(),
                ))
            }
            _ => None,
        })
    }
    let ctx = egui::Context::default();
    let progress = PipelineProgress::default();
    let native: Vec<_> = (0..12)
        .map(|index| crate::workbench::SourcePhoto {
            epoch: 1,
            index,
            aperture: [160, 106],
            texture: ctx.load_texture(
                format!("native-refinement-{index}"),
                egui::ColorImage::filled([160, 106], Color32::GRAY),
                egui::TextureOptions::LINEAR,
            ),
        })
        .collect();
    let refined = ctx.load_texture(
        "cached-refinement",
        egui::ColorImage::filled([480, 320], Color32::GOLD),
        egui::TextureOptions::LINEAR,
    );
    let incompatible = ctx.load_texture(
        "cached-other-crop",
        egui::ColorImage::filled([480, 360], Color32::RED),
        egui::TextureOptions::LINEAR,
    );
    let canonical = vec![
        crate::workbench::SourcePhoto {
            epoch: 1,
            index: 11,
            texture: refined.clone(),
            aperture: [6000, 4000],
        },
        crate::workbench::SourcePhoto {
            epoch: 1,
            index: 6,
            texture: incompatible.clone(),
            aperture: [6000, 4000],
        },
    ];
    let data = Input {
        photos: &native,
        ..input(&progress, 12)
    };
    let with_cache = Input {
        inspection_photos: &canonical,
        ..data
    };
    let mut row = CaptureParticipation::default();
    let (_, compact) = paint(&mut row, &ctx, with_cache, HEIGHT, 0.0);
    assert!(
        painted(&compact, native[11].texture.id()).is_some(),
        "the no-refinement control must paint the same real source"
    );
    assert!(
        painted(&compact, refined.id()).is_none(),
        "an already sufficient compact contact must not promote a large tier"
    );
    let (_, base) = paint(&mut row, &ctx, data, 278.0, 0.4);
    let identity = row.indices();
    assert!(identity.contains(&11) && identity.contains(&6));
    let card = painted(&base, native[11].texture.id()).unwrap().0;
    let retain_count = ctx
        .tex_manager()
        .read()
        .meta(refined.id())
        .unwrap()
        .retain_count;
    let allocations = ctx.tex_manager().read().num_allocated();
    let (requested, first) = paint(&mut row, &ctx, with_cache, 278.0, 0.5);
    assert!(
        requested.open_source.is_none(),
        "cache refinement must not select/fetch a source"
    );
    assert_eq!(
        row.indices(),
        identity,
        "cache availability must not add thumbnail fetch targets"
    );
    let (first_rect, first_alpha) = painted(&first, refined.id())
        .expect("compatible existing cache can refine the enlarged card");
    assert_eq!(first_rect, card);
    assert_eq!(first_alpha, 0);
    let (_, middle) = paint(&mut row, &ctx, with_cache, 278.0, 0.6);
    let (middle_rect, middle_alpha) = painted(&middle, refined.id()).unwrap();
    assert_eq!(middle_rect, card);
    assert!(
        (1..255).contains(&middle_alpha),
        "a real bounded blend must occur"
    );
    let (_, full) = paint(&mut row, &ctx, with_cache, 278.0, 0.8);
    assert_eq!(painted(&full, refined.id()), Some((card, 255)));
    assert!(
        painted(&full, incompatible.id()).is_none(),
        "letterboxed/differently cropped camera tiers cannot replace contact geometry"
    );
    assert_eq!(
        ctx.tex_manager()
            .read()
            .meta(refined.id())
            .unwrap()
            .retain_count,
        retain_count + 1
    );
    assert_eq!(
        ctx.tex_manager().read().num_allocated(),
        allocations,
        "pinning a cached tier allocates no GPU texture"
    );
    let (_, lost) = paint(&mut row, &ctx, data, 278.0, 1.0);
    assert_eq!(
        painted(&lost, refined.id()),
        Some((card, 255)),
        "browser cache eviction cannot downgrade a visible contact"
    );
    assert_eq!(painted(&lost, native[11].texture.id()).unwrap().0, card);
    let id = refined.id();
    drop(canonical);
    drop(refined);
    assert_eq!(
        ctx.tex_manager().read().meta(id).unwrap().retain_count,
        1,
        "one visible contact retains exactly one chosen tier after browser handles leave"
    );
    let higher = vec![crate::workbench::SourcePhoto {
        epoch: 1,
        index: 11,
        aperture: [6000, 4000],
        texture: ctx.load_texture(
            "newer-bigger-tier",
            egui::ColorImage::filled([960, 640], Color32::BLUE),
            egui::TextureOptions::LINEAR,
        ),
    }];
    let (_, unchanged) = paint(
        &mut row,
        &ctx,
        Input {
            inspection_photos: &higher,
            ..data
        },
        278.0,
        1.1,
    );
    assert_eq!(painted(&unchanged, id), Some((card, 255)));
    assert!(
        painted(&unchanged, higher[0].texture.id()).is_none(),
        "a visible contact must not restart or jump between successive tiers"
    );
    paint(
        &mut row,
        &ctx,
        Input {
            frame_count: 2,
            ..data
        },
        278.0,
        1.2,
    );
    assert!(
        ctx.tex_manager().read().meta(id).is_none(),
        "leaving the contact layout releases its chosen canonical tier"
    );

    let large: Vec<_> = [0, 3, 6, 11]
        .into_iter()
        .map(|index| crate::workbench::SourcePhoto {
            epoch: 1,
            index,
            aperture: [6000, 4000],
            texture: ctx.load_texture(
                format!("budget-contact-{index}"),
                egui::ColorImage::filled([2048, 1365], Color32::BLUE),
                egui::TextureOptions::LINEAR,
            ),
        })
        .collect();
    let large_data = Input {
        inspection_photos: &large,
        ..data
    };
    let (response, _) = paint(&mut row, &ctx, large_data, 278.0, 1.4);
    assert!(response.open_source.is_none());
    assert_eq!(row.indices(), identity);
    assert_eq!(
        row.refinements.len(),
        3,
        "four eligible tiers exceed32MiB; the fourth must remain native"
    );
    let retained: usize = row.refinements.values().map(|chosen| chosen.bytes).sum();
    assert!(retained <= CONTACT_REFINEMENT_BYTES);
    assert!(
        retained + 2048 * 1365 * 4 > CONTACT_REFINEMENT_BYTES,
        "fixture must actually exhaust the budget"
    );
    let (_, budgeted) = paint(&mut row, &ctx, large_data, 278.0, 1.8);
    assert!(painted(&budgeted, large[3].texture.id()).is_none());
    assert!(painted(&budgeted, native[11].texture.id()).is_some());
    paint(&mut row, &ctx, Input { epoch: 2, ..data }, 278.0, 2.0);
    assert!(
        row.refinements.is_empty(),
        "new brackets release every retained contact tier"
    );
}

#[test]
fn painted_source_milestones_remain_additive_when_alignment_becomes_merge() {
    let ctx = egui::Context::default();
    crate::theme::install(&ctx);
    let mut ribbon = CaptureParticipation::default();
    ribbon.set_source_mode(true);
    let rect = Rect::from_min_size(egui::pos2(20.0, 30.0), egui::vec2(900.0, HEIGHT));
    let mut progress = PipelineProgress::default();
    progress.stage = crate::pipeline::Stage::Alignment;
    progress.alignment_plane_observations = (0..12).collect();
    progress.alignment_pyramid_observations = (0..12).collect();
    let mut paint = |progress: &PipelineProgress, time| {
        ctx.run(
            egui::RawInput {
                screen_rect: Some(Rect::from_min_size(Pos2::ZERO, egui::vec2(960.0, 240.0))),
                time: Some(time),
                ..Default::default()
            },
            |ctx| {
                egui::CentralPanel::default().show(ctx, |ui| {
                    ribbon.show(
                        ui,
                        rect,
                        &input(progress, 12),
                        &progress.admission_archive,
                        0,
                        Rect::from_min_max(Pos2::ZERO, egui::pos2(1.0, 1.0)),
                    );
                });
            },
        )
    };
    let bars = |output: &egui::FullOutput, row: usize| {
        let label = ["read", "scales", "folded"][row];
        let (label_clip, label_bounds) = output
            .shapes
            .iter()
            .find_map(|shape| match &shape.shape {
                egui::Shape::Text(text) if text.galley.text() == label => {
                    Some((shape.clip_rect, text.visual_bounding_rect()))
                }
                _ => None,
            })
            .unwrap_or_else(|| panic!("missing persistent source milestone {label}"));
        assert!(label_clip.contains_rect(label_bounds));
        // The compact legend is above all three full-width tracks. Locate
        // their actual baselines independently; completed scales must never
        // count as folded captures just because both are green milestones.
        let mut baselines: Vec<_> = output
            .shapes
            .iter()
            .filter_map(|shape| match &shape.shape {
                egui::Shape::LineSegment { points, .. }
                    if points[0].y == points[1].y
                        && points[1].x - points[0].x > rect.width() - 20.0
                        && points[0].y > label_bounds.bottom()
                        && points[0].y < rect.center().y =>
                {
                    Some(points[0].y)
                }
                _ => None,
            })
            .collect();
        baselines.sort_by(f32::total_cmp);
        baselines.dedup();
        assert_eq!(
            baselines.len(),
            3,
            "three actual processing tracks must be painted"
        );
        output
            .shapes
            .iter()
            .filter_map(|shape| match &shape.shape {
                egui::Shape::Rect(mark)
                    if (mark.rect.bottom() - baselines[row]).abs() < 0.01
                        && mark.rect.height() <= 24.0
                        && mark.fill == [GREEN, ACCENT, GREEN][row].gamma_multiply(0.85) =>
                {
                    Some(mark.rect)
                }
                _ => None,
            })
            .collect::<Vec<_>>()
    };
    let aligned = paint(&progress, 0.0);
    assert_eq!(bars(&aligned, 0).len(), 12);
    assert_eq!(bars(&aligned, 1).len(), 12);
    assert!(bars(&aligned, 2).is_empty());
    progress.stage = crate::pipeline::Stage::Merge;
    progress.frame_observations = (0..3)
        .map(|frame| (frame, crate::pipeline::FrameObservation::Processed))
        .collect();
    let merging = paint(&progress, 0.1);
    assert_eq!(bars(&merging, 0), bars(&aligned, 0));
    assert_eq!(bars(&merging, 1), bars(&aligned, 1));
    assert_eq!(bars(&merging, 2).len(), 3);
}
