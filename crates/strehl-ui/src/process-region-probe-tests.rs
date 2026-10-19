use super::*;

fn packet(frame: usize, level: usize, size: [usize; 2], pixels: Vec<u8>) -> DiagnosticSurface {
    DiagnosticSurface {
        sequence: frame as u64 + 1,
        frame,
        level,
        kind: DiagnosticKind::GateSupport,
        scope: DiagnosticScope::Frame,
        scale: DiagnosticScale::Linear,
        width: size[0],
        height: size[1],
        min: 0.0,
        max: 1.0,
        pixels: pixels.into(),
        folded: 1,
    }
}
fn unit() -> Rect {
    Rect::from_min_max(Pos2::ZERO, egui::pos2(1.0, 1.0))
}

#[test]
fn sample_window_reads_only_actual_members_and_keeps_unknown_distinct_from_rejected() {
    let meta = AdmissionMeta {
        sequence: 1,
        samples: [128, 96],
        extent: [2048, 1536],
    };
    let mut archive = AdmissionArchive::default();
    archive.ingest(
        &packet(
            0,
            0,
            meta.samples,
            (0..128 * 96)
                .map(|index| if index == 129 { 255 } else { 0 })
                .collect(),
        ),
        meta.extent,
    );
    let cells = || archive.cells(0, 0).unwrap().1;
    let mut local = cells();
    let region = Rect::from_min_max(egui::pos2(0.010, 0.014), egui::pos2(0.015, 0.018));
    // Actual level-zero centre of index129 is24.5/2048,24.5/1536.
    let window = SampleWindow::new(0, meta, region).unwrap();
    assert!(window.contains(129));
    assert_eq!(
        window.counts(&mut local),
        SampleCount {
            observed: 1,
            admitted: 1
        }
    );
    assert_eq!(
        local.bit_reads(),
        1,
        "actual archive iterator skips the other12287 bit reads"
    );
    let mut all = cells();
    let global = SampleWindow::new(0, meta, unit()).unwrap().counts(&mut all);
    assert_eq!(global.observed, 12288);
    assert_eq!(
        all.bit_reads(),
        12288,
        "negative control exercises the whole-grid path"
    );
    let gap = Rect::from_min_max(egui::pos2(0.015, 0.018), egui::pos2(0.016, 0.019));
    assert_eq!(
        SampleWindow::new(0, meta, gap)
            .unwrap()
            .counts(cells())
            .fraction(),
        None
    );
    assert_eq!(
        window.counts((0..12288).map(|_| false)).fraction(),
        Some(0.0)
    );
    assert_eq!(window.counts((0..12287).map(|_| true)).fraction(), None);
}

#[test]
fn membership_cache_survives_motion_but_refreshes_packet_changes_and_domains() {
    let mut archive = AdmissionArchive::default();
    archive.ingest(
        &packet(0, 2, [3, 3], vec![255, 0, 0, 0, 0, 0, 0, 0, 255]),
        [9, 9],
    );
    archive.ingest(&packet(2, 2, [3, 3], vec![0; 9]), [9, 9]);
    assert_eq!(archive.frames(2).collect::<Vec<_>>(), vec![0, 2]);
    let mut probe = RegionProbe::default();
    let region = Rect::from_min_max(Pos2::ZERO, egui::pos2(0.1, 0.1));
    probe.update(&archive, 2, [9, 9], 130, region);
    assert_eq!(probe.readings, 2);
    assert_eq!(
        probe.evidence[&(2, 0)].count,
        SampleCount {
            observed: 1,
            admitted: 1
        }
    );
    assert_eq!(
        probe.evidence[&(2, 2)].count,
        SampleCount {
            observed: 1,
            admitted: 0
        }
    );
    assert!(
        !probe.evidence.contains_key(&(2, 1)),
        "missing capture has no zero-valued evidence"
    );
    assert!(
        !probe.evidence.contains_key(&(2, 129)),
        "unknown trailing captures remain represented only by the axis"
    );
    probe.update(
        &archive,
        2,
        [9, 9],
        130,
        region.translate(Vec2::splat(0.003)),
    );
    assert_eq!(
        probe.readings, 2,
        "float aperture motion with identical membership performs no mask reads"
    );
    let mut update = packet(0, 2, [3, 3], vec![0; 9]);
    update.sequence = 30;
    archive.ingest(&update, [9, 9]);
    probe.update(&archive, 2, [9, 9], 130, region);
    assert_eq!(probe.readings, 3);
    assert_eq!(probe.evidence[&(2, 0)].count.admitted, 0);
    probe.update(&archive, 2, [18, 18], 130, region);
    assert!(
        probe.evidence.is_empty(),
        "old analysis extent cannot be placed on a new photograph"
    );
}

#[test]
fn region_tracks_screen_size_through_zoom_and_clamps_to_actual_photo_edges() {
    let image = Rect::from_min_size(egui::pos2(100.0, 80.0), egui::vec2(800.0, 600.0));
    let zoomed = Rect::from_min_max(egui::pos2(0.25, 0.3), egui::pos2(0.5, 0.55));
    let full = region_at(image, unit(), image.center(), 64.0).unwrap();
    let zoom = region_at(image, zoomed, image.center(), 64.0).unwrap();
    assert!((full.width() - 0.08).abs() < 0.00001);
    assert!((zoom.width() - 0.02).abs() < 0.00001);
    assert!(zoom.center().distance(zoomed.center()) < 0.00001);
    let edge = region_at(image, zoomed, image.left_top(), 64.0).unwrap();
    assert_eq!(edge.min, zoomed.min);
    assert!((edge.width() - 0.01).abs() < 0.00001);
    assert_eq!(
        region_at(image, zoomed, image.left_top() - Vec2::splat(1.0), 64.0),
        None
    );
}

#[test]
fn fallback_reports_actual_sample_count_without_turning_it_into_capture_weight() {
    let mut probe = RegionProbe::default();
    let mut fallback = packet(1, 2, [3, 3], vec![255, 0, 0, 0, 0, 0, 0, 0, 255]);
    fallback.kind = DiagnosticKind::Averaging;
    fallback.scope = DiagnosticScope::Stack;
    probe.set_fallback(Some((fallback.clone(), [9, 9])));
    probe.update(&AdmissionArchive::default(), 2, [9, 9], 4, unit());
    assert_eq!(
        probe.fallback.as_ref().unwrap().count,
        SampleCount {
            observed: 9,
            admitted: 2
        }
    );
    assert!(
        probe.evidence.is_empty(),
        "fallback never manufactures per-capture gate admission"
    );
    fallback.pixels = vec![127; 9].into();
    probe.set_fallback(Some((fallback, [9, 9])));
    assert!(
        probe.fallback.is_none(),
        "ambiguous continuous values cannot pass as binary evidence"
    );
}

fn paint(
    probe: &mut RegionProbe,
    ctx: &egui::Context,
    events: Vec<egui::Event>,
    focused: bool,
) -> (Option<Rect>, bool) {
    let mut result = (None, false);
    let _ = ctx.run(
        egui::RawInput {
            screen_rect: Some(Rect::from_min_size(Pos2::ZERO, egui::vec2(800.0, 640.0))),
            events,
            focused,
            ..Default::default()
        },
        |ctx| {
            egui::CentralPanel::default().show(ctx, |ui| {
                let image = Rect::from_min_size(egui::pos2(40.0, 40.0), egui::vec2(600.0, 450.0));
                let hit = ui.interact(
                    image,
                    ui.id().with("actual-photograph"),
                    egui::Sense::click_and_drag(),
                );
                result.0 = probe.show(
                    ui,
                    image,
                    unit(),
                    &AdmissionArchive::default(),
                    0,
                    [600, 450],
                    [1200, 900],
                    130,
                );
                result.1 = hit.clicked();
            });
        },
    );
    result
}

#[test]
fn hover_probe_does_not_capture_photo_gestures_and_clears_on_leave_focus_loss_or_press() {
    let ctx = egui::Context::default();
    let mut probe = RegionProbe::default();
    let at = egui::pos2(300.0, 240.0);
    paint(&mut probe, &ctx, vec![], true);
    assert!(
        paint(&mut probe, &ctx, vec![egui::Event::PointerMoved(at)], true)
            .0
            .is_some()
    );
    assert!(paint(&mut probe, &ctx, vec![], false).0.is_none());
    paint(&mut probe, &ctx, vec![], true);
    let press = |pressed| egui::Event::PointerButton {
        pos: at,
        button: egui::PointerButton::Primary,
        pressed,
        modifiers: egui::Modifiers::NONE,
    };
    assert!(paint(&mut probe, &ctx, vec![press(true)], true).0.is_none());
    let release = paint(&mut probe, &ctx, vec![press(false)], true);
    assert!(release.0.is_none());
    assert!(release.1, "underlying photograph still owns the real click");
    assert!(
        paint(
            &mut probe,
            &ctx,
            vec![egui::Event::PointerMoved(egui::pos2(760.0, 600.0))],
            true
        )
        .0
        .is_none()
    );
}

#[test]
fn moving_and_clicking_through_the_previous_probe_display_never_steals_photo_input() {
    let ctx = egui::Context::default();
    let mut probe = RegionProbe::default();
    paint(&mut probe, &ctx, vec![], true);
    let first = egui::pos2(100.0, 110.0);
    paint(
        &mut probe,
        &ctx,
        vec![egui::Event::PointerMoved(first)],
        true,
    );
    paint(&mut probe, &ctx, vec![], true);
    let previous = probe.popup_bounds.unwrap();
    let target = previous.min + egui::vec2(20.0, 30.0);
    assert!(previous.contains(target));
    assert!(Rect::from_min_size(egui::pos2(40.0, 40.0), egui::vec2(600.0, 450.0)).contains(target));
    for delta in [0.0, 1.0, 2.0, 3.0, 4.0] {
        assert!(
            paint(
                &mut probe,
                &ctx,
                vec![egui::Event::PointerMoved(target + Vec2::splat(delta))],
                true
            )
            .0
            .is_some(),
            "passing through last painted probe cannot flicker off the source region"
        );
    }
    let prior_press_bounds = probe.popup_bounds.unwrap();
    let press_at = prior_press_bounds.min + egui::vec2(20.0, 30.0);
    assert!(prior_press_bounds.contains(press_at));
    assert!(
        Rect::from_min_size(egui::pos2(40.0, 40.0), egui::vec2(600.0, 450.0)).contains(press_at)
    );
    let button = |pressed| egui::Event::PointerButton {
        pos: press_at,
        button: egui::PointerButton::Primary,
        pressed,
        modifiers: egui::Modifiers::NONE,
    };
    paint(
        &mut probe,
        &ctx,
        vec![egui::Event::PointerMoved(press_at), button(true)],
        true,
    );
    assert!(
        paint(&mut probe, &ctx, vec![button(false)], true).1,
        "a press that jumps into the previous floating display belongs to the photograph"
    );
}

#[test]
fn floating_display_placement_stays_beside_the_pointer_and_inside_small_viewports() {
    for width in [360.0, 700.0, 1400.0] {
        let viewport = Rect::from_min_size(Pos2::ZERO, egui::vec2(width, 540.0)).shrink(8.0);
        for point in [
            viewport.left_top(),
            viewport.center(),
            viewport.right_bottom(),
        ] {
            let region = Rect::from_center_size(point, Vec2::splat(96.0)).intersect(viewport);
            let rect = popup_placement(viewport, region, egui::vec2(370.0, 470.0));
            assert!(viewport.contains_rect(rect));
            assert!(!rect.expand(10.0).contains(point));
            assert!(!rect.intersects(region));
        }
    }
}

#[test]
fn spatial_region_preserves_shared_admissions_at_actual_odd_lattice_centres() {
    let mut archive = AdmissionArchive::default();
    for (frame, indices) in [
        (2, vec![0, 4]),
        (8, vec![4, 8]),
        (9, vec![4]),
        (12, vec![8]),
        (15, vec![]),
    ] {
        let pixels = (0..9)
            .map(|index| if indices.contains(&index) { 255 } else { 0 })
            .collect();
        archive.ingest(&packet(frame, 2, [3, 3], pixels), [9, 9]);
    }
    let mut probe = RegionProbe::default();
    probe.update(&archive, 2, [9, 9], 20, unit());
    let key = probe.spatial_key.as_ref().unwrap();
    assert_eq!(
        key.sources
            .iter()
            .map(|source| source.0)
            .collect::<Vec<_>>(),
        [2, 8, 9]
    );
    assert_eq!(probe.spatial.len(), 3);
    assert_eq!(
        probe.spatial_reads, 27,
        "only the three displayed capture masks are reread spatially"
    );
    let center = egui::pos2(4.5 / 9.0, 4.5 / 9.0);
    let shared = probe
        .spatial
        .iter()
        .find(|point| point.glyph.center == center)
        .unwrap();
    assert_eq!(
        shared.sources, 0b111,
        "co-admission cannot be replaced by one elected winner"
    );
    assert_eq!(
        probe.spatial[0].glyph.center,
        egui::pos2(0.5 / 9.0, 0.5 / 9.0)
    );
    assert_eq!(
        probe.spatial[2].glyph.center,
        egui::pos2(8.5 / 9.0, 8.5 / 9.0)
    );
    assert_eq!(probe.evidence[&(2, 15)].count.fraction(), Some(0.0));
    assert!(
        !probe.evidence.contains_key(&(2, 16)),
        "a missing source cannot become observed zero"
    );
    probe.update(&archive, 2, [9, 9], 20, unit());
    assert_eq!(
        probe.spatial_reads, 27,
        "same membership and receipts reuse the spatial cache"
    );
    let mut replacement = packet(2, 2, [3, 3], vec![0; 9]);
    replacement.sequence = 80;
    archive.ingest(&replacement, [9, 9]);
    probe.update(&archive, 2, [9, 9], 20, unit());
    assert_eq!(
        probe
            .spatial_key
            .as_ref()
            .unwrap()
            .sources
            .iter()
            .map(|source| source.0)
            .collect::<Vec<_>>(),
        [8, 9, 12]
    );
    assert!(
        !probe
            .spatial
            .iter()
            .any(|point| point.glyph.center == egui::pos2(0.5 / 9.0, 0.5 / 9.0))
    );
    probe.update(&archive, 2, [18, 18], 20, unit());
    assert!(
        probe.spatial.is_empty(),
        "same shape in a different analysis domain cannot place old evidence"
    );
}

#[test]
fn spatial_cache_reads_small_membership_and_paint_submissions_are_bounded_positive_samples() {
    let size = [128, 96];
    let extent = [2048, 1536];
    let mut archive = AdmissionArchive::default();
    for frame in 0..4 {
        archive.ingest(
            &packet(frame, 0, size, vec![255; size[0] * size[1]]),
            extent,
        );
    }
    let mut probe = RegionProbe::default();
    let small = Rect::from_min_max(egui::pos2(0.010, 0.014), egui::pos2(0.015, 0.018));
    probe.update(&archive, 0, extent, 4, small);
    assert_eq!(probe.spatial.len(), 1);
    assert_eq!(
        probe.spatial_reads, 3,
        "nth skips other actual bits for the three spatial source readers"
    );
    probe.update(
        &archive,
        0,
        extent,
        4,
        small.translate(Vec2::splat(0.00001)),
    );
    assert_eq!(probe.spatial_reads, 3);
    probe.update(&archive, 0, extent, 4, unit());
    assert_eq!(
        probe.spatial.len(),
        size[0] * size[1],
        "full membership positive control"
    );
    let ctx = egui::Context::default();
    let image = Rect::from_min_size(egui::pos2(50.0, 40.0), egui::vec2(400.0, 300.0));
    let output = ctx.run(egui::RawInput::default(), |ctx| {
        egui::CentralPanel::default().show(ctx, |ui| {
            probe.paint_spatial(ui.painter(), image, unit(), image, 0);
        });
    });
    let sectors: Vec<_> = output
        .shapes
        .iter()
        .filter_map(|clipped| match &clipped.shape {
            egui::Shape::Mesh(mesh) if mesh.texture_id == egui::TextureId::default() => {
                Some((clipped.clip_rect, mesh))
            }
            _ => None,
        })
        .collect();
    assert_eq!(
        sectors.len(),
        1,
        "actual source sectors share one retained mesh"
    );
    for (clip, mesh) in sectors {
        assert!(
            mesh.vertices.len() > 3 * 768,
            "dense positive control must really paint all sources"
        );
        assert!(
            mesh.vertices.len() <= 3 * 768 * 32,
            "bounded markers include their antialias fringe"
        );
        assert!(clip.max.x <= image.max.x && clip.max.y <= image.max.y);
        let centers: Vec<_> = probe
            .spatial
            .iter()
            .step_by(probe.spatial.len().div_ceil(768))
            .map(|sample| image.min + sample.glyph.center.to_vec2() * image.size())
            .collect();
        for vertex in &mesh.vertices {
            assert!(
                centers
                    .iter()
                    .any(|at| at.distance_sq(vertex.pos) < 4.5 * 4.5),
                "every antialiased vertex belongs to an actual transmitted sample"
            );
        }
    }
}

#[test]
fn fallback_spatial_marks_keep_true_samples_and_never_create_source_weights() {
    let mut probe = RegionProbe::default();
    let mut fallback = packet(0, 2, [3, 3], vec![255, 0, 0, 0, 255, 0, 0, 0, 0]);
    fallback.kind = DiagnosticKind::Averaging;
    fallback.scope = DiagnosticScope::Stack;
    probe.set_fallback(Some((fallback, [9, 9])));
    probe.update(&AdmissionArchive::default(), 2, [9, 9], 4, unit());
    let fallback = probe.fallback.as_ref().unwrap();
    assert_eq!(fallback.points.len(), 2);
    assert_eq!(fallback.points[1].center, egui::pos2(0.5, 0.5));
    assert!(probe.spatial.is_empty());
    assert!(probe.evidence.is_empty());
    probe.set_balance(Some(1001));
    assert_eq!(probe.balance, None);
    probe.set_balance(Some(0));
    assert_eq!(
        probe.balance,
        Some(0),
        "a tied or one-sided value is valid, not missing"
    );
}

#[test]
fn ctrl_wheel_resizes_region_without_owning_clicks_or_unmodified_wheel() {
    let ctx = egui::Context::default();
    let mut probe = RegionProbe::default();
    let image = Rect::from_min_size(egui::pos2(40.0, 40.0), egui::vec2(600.0, 450.0));
    let at = image.center();
    let frame = |probe: &mut RegionProbe,
                 ctrl: bool,
                 amount: f32,
                 point: Pos2,
                 focused: bool,
                 pressed: bool| {
        let modifiers = egui::Modifiers {
            ctrl,
            ..Default::default()
        };
        let mut events = vec![
            egui::Event::PointerMoved(point),
            egui::Event::MouseWheel {
                unit: egui::MouseWheelUnit::Point,
                delta: egui::vec2(0.0, amount),
                modifiers,
            },
        ];
        if pressed {
            events.push(egui::Event::PointerButton {
                pos: point,
                button: egui::PointerButton::Primary,
                pressed: true,
                modifiers,
            });
        }
        let mut result = (false, false, Vec2::ZERO);
        let _ = ctx.run(
            egui::RawInput {
                screen_rect: Some(Rect::from_min_size(Pos2::ZERO, egui::vec2(800.0, 640.0))),
                modifiers,
                events,
                focused,
                ..Default::default()
            },
            |ctx| {
                egui::CentralPanel::default().show(ctx, |ui| {
                    let hit = ui.interact(
                        image,
                        ui.id().with("real-photo"),
                        egui::Sense::click_and_drag(),
                    );
                    result.0 = probe.resize(ui, image);
                    result.1 = hit.is_pointer_button_down_on();
                    result.2 = ui.input(|input| input.raw_scroll_delta);
                });
            },
        );
        result
    };
    frame(&mut probe, false, 0.0, at, true, false);
    let ordinary = frame(&mut probe, false, 60.0, at, true, false);
    assert!(!ordinary.0);
    assert_ne!(
        ordinary.2,
        Vec2::ZERO,
        "ordinary photo zoom input remains available"
    );
    assert_eq!(probe.side, None);
    let resize = frame(&mut probe, true, 60.0, at, true, false);
    assert!(resize.0);
    assert_eq!(resize.2, Vec2::ZERO);
    let first = probe.side.unwrap();
    assert!(first > 96.0);
    assert!(!frame(&mut probe, true, 60.0, at, false, false).0);
    assert_eq!(probe.side, Some(first));
    assert!(
        !frame(
            &mut probe,
            true,
            60.0,
            image.max + Vec2::splat(20.0),
            true,
            false
        )
        .0
    );
    for _ in 0..10 {
        assert!(frame(&mut probe, true, 400.0, at, true, false).0);
    }
    assert_eq!(probe.side, Some(320.0));
    for _ in 0..10 {
        assert!(frame(&mut probe, true, -400.0, at, true, false).0);
    }
    assert_eq!(probe.side, Some(32.0));
    let held = frame(&mut probe, true, 60.0, at, true, true);
    assert!(!held.0);
    assert!(held.1, "the photograph still owns its actual held gesture");
    assert_eq!(probe.side, Some(32.0));
}
