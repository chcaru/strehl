use super::*;

fn packet(frame: usize, pixels: Vec<u8>) -> DiagnosticSurface {
    DiagnosticSurface {
        sequence: frame as u64 + 1,
        frame,
        level: 0,
        kind: DiagnosticKind::GateSupport,
        scope: DiagnosticScope::Frame,
        scale: DiagnosticScale::Linear,
        width: 16,
        height: 12,
        min: 0.0,
        max: 1.0,
        folded: 1,
        pixels: pixels.into(),
    }
}
fn unit() -> Rect {
    Rect::from_min_max(Pos2::ZERO, egui::pos2(1.0, 1.0))
}
fn image() -> Rect {
    Rect::from_min_size(egui::pos2(50.0, 50.0), egui::vec2(500.0, 375.0))
}
fn paint(
    ctx: &egui::Context,
    probe: &RegionProbe,
    image: Rect,
    clip: Rect,
) -> (Arc<egui::Mesh>, Rect) {
    let output = ctx.run(Default::default(), |ctx| {
        egui::CentralPanel::default().show(ctx, |ui| {
            probe.paint_spatial(ui.painter(), image, unit(), clip, 0);
        });
    });
    let meshes: Vec<_> = output
        .shapes
        .iter()
        .filter_map(|shape| {
            if let egui::Shape::Mesh(mesh) = &shape.shape {
                Some((mesh.clone(), shape.clip_rect))
            } else {
                None
            }
        })
        .collect();
    assert_eq!(meshes.len(), 1, "the actual on-image paint is one mesh");
    meshes[0].clone()
}

// Independent reference: the former per-point painter paths, constructed at
// the actual final-image coordinates and tessellated there rather than at0,0.
fn original(probe: &RegionProbe, ctx: &egui::Context, image: Rect) -> egui::Mesh {
    let mut tess = egui::epaint::Tessellator::new(
        ctx.pixels_per_point(),
        ctx.tessellation_options(|o| *o),
        [1, 1],
        Vec::new(),
    );
    let mut out = egui::Mesh::default();
    let project = |uv: Pos2| image.min + uv.to_vec2() * image.size();
    for point in &probe.spatial {
        let at = project(point.glyph.center);
        for (slot, &(frame, _, _)) in probe
            .spatial_key
            .as_ref()
            .unwrap()
            .sources
            .iter()
            .enumerate()
        {
            if point.sources & (1 << slot) == 0 {
                continue;
            }
            let mut vertices = vec![at];
            for step in 0..=3 {
                let angle = -std::f32::consts::FRAC_PI_2
                    + (slot as f32 + step as f32 / 3.0) * std::f32::consts::TAU / 3.0;
                vertices.push(at + egui::vec2(angle.cos(), angle.sin()) * 3.0);
            }
            tess.tessellate_shape(
                egui::Shape::convex_polygon(vertices, capture_ink(frame), Stroke::NONE),
                &mut out,
            );
        }
    }
    if let Some(fallback) = &probe.fallback {
        for point in &fallback.points {
            let at = project(point.center);
            tess.tessellate_shape(
                egui::Shape::closed_line(
                    vec![
                        at + egui::vec2(0.0, -3.5),
                        at + egui::vec2(3.5, 0.0),
                        at + egui::vec2(0.0, 3.5),
                        at + egui::vec2(-3.5, 0.0),
                    ],
                    Stroke::new(1.0_f32, crate::theme::INK),
                ),
                &mut out,
            );
        }
    }
    out
}

#[test]
fn retained_mesh_matches_original_identity_sectors_and_hollow_fallback_with_actual_renderer_aa() {
    let mut archive = AdmissionArchive::default();
    archive.ingest(&packet(0, vec![255; 192]), [2048, 1536]);
    archive.ingest(
        &packet(8, (0..192).map(|i| if i == 17 { 255 } else { 0 }).collect()),
        [2048, 1536],
    );
    archive.ingest(
        &packet(
            12,
            (0..192).map(|i| if i % 3 == 0 { 255 } else { 0 }).collect(),
        ),
        [2048, 1536],
    );
    let mut probe = RegionProbe::default();
    probe.set_source_frame(Some(8));
    let mut fallback = packet(
        0,
        (0..192)
            .map(|i| if i == 18 || i == 70 { 255 } else { 0 })
            .collect(),
    );
    fallback.kind = DiagnosticKind::Averaging;
    fallback.scope = DiagnosticScope::Stack;
    probe.set_fallback(Some((fallback, [2048, 1536])));
    probe.update(&archive, 0, [2048, 1536], 13, unit());
    assert_eq!(probe.spatial_key.as_ref().unwrap().sources[0].0, 8);
    assert_eq!(probe.fallback.as_ref().unwrap().points.len(), 2);
    let ctx = egui::Context::default();
    for (dpi, aa) in [(1.0, true), (2.0, true), (1.0, false)] {
        ctx.set_pixels_per_point(dpi);
        ctx.tessellation_options_mut(|options| options.feathering = aa);
        let (actual, _) = paint(&ctx, &probe, image(), image());
        let expected = original(&probe, &ctx, image());
        assert_eq!(actual.indices, expected.indices);
        assert_eq!(actual.vertices.len(), expected.vertices.len());
        assert!(!actual.vertices.is_empty());
        for (a, b) in actual.vertices.iter().zip(&expected.vertices) {
            assert!(
                a.pos.distance(b.pos) < 0.0002,
                "physical sample/sector position {a:?} vs {b:?}"
            );
            assert_eq!(a.color, b.color);
            assert_eq!(a.uv, b.uv);
        }
        assert_eq!(
            actual
                .vertices
                .iter()
                .any(|v| v.color == Color32::TRANSPARENT),
            aa,
            "real AA fringe must survive, with disabled-AA negative control"
        );
    }
}

#[test]
fn clip_motion_reuses_mesh_but_same_metadata_fallback_replacement_projection_and_aa_invalidate() {
    let mut archive = AdmissionArchive::default();
    archive.ingest(&packet(0, vec![255; 192]), [2048, 1536]);
    let mut probe = RegionProbe::default();
    let mut fallback = packet(0, (0..192).map(|i| if i == 17 { 255 } else { 0 }).collect());
    fallback.kind = DiagnosticKind::Averaging;
    fallback.scope = DiagnosticScope::Stack;
    probe.set_fallback(Some((fallback.clone(), [2048, 1536])));
    probe.update(&archive, 0, [2048, 1536], 1, unit());
    let ctx = egui::Context::default();
    let (first, first_clip) = paint(&ctx, &probe, image(), image());
    let builds = probe.spatial_paint.borrow().builds;
    let (same, next_clip) = paint(
        &ctx,
        &probe,
        image(),
        image().translate(egui::vec2(1.0, 0.0)),
    );
    assert!(Arc::ptr_eq(&first, &same));
    assert_ne!(
        first_clip, next_clip,
        "actual clipping moves without rebuilding sample geometry"
    );
    assert_eq!(probe.spatial_paint.borrow().builds, builds);
    fallback.pixels = (0..192)
        .map(|i| if i == 18 { 255 } else { 0 })
        .collect::<Vec<_>>()
        .into();
    probe.set_fallback(Some((fallback, [2048, 1536])));
    probe.update(&archive, 0, [2048, 1536], 1, unit());
    let (changed, _) = paint(&ctx, &probe, image(), image());
    assert!(!Arc::ptr_eq(&first, &changed));
    assert_ne!(
        first.vertices, changed.vertices,
        "new fallback positions cannot retain old diamonds"
    );
    let shifted = image().translate(egui::vec2(19.0, 0.0));
    let (projected, _) = paint(&ctx, &probe, shifted, shifted);
    assert!(!Arc::ptr_eq(&changed, &projected));
    for (a, b) in changed.vertices.iter().zip(&projected.vertices) {
        assert!((b.pos - a.pos - egui::vec2(19.0, 0.0)).length() < 0.0001);
    }
    ctx.tessellation_options_mut(|options| options.feathering = false);
    let (aliased, _) = paint(&ctx, &probe, shifted, shifted);
    assert!(!Arc::ptr_eq(&projected, &aliased));
    assert!(
        !aliased
            .vertices
            .iter()
            .any(|v| v.color == Color32::TRANSPARENT)
    );
    probe.set_fallback(None);
    let (removed, _) = paint(&ctx, &probe, shifted, shifted);
    assert!(
        removed.vertices.len() < aliased.vertices.len(),
        "missing fallback leaves no stale diamond"
    );
}

#[test]
fn a_single_current_source_sample_survives_dense_peer_thinning_at_its_real_coordinate() {
    let mut archive = AdmissionArchive::default();
    let mut sparse = packet(8, vec![0; 128 * 96]);
    sparse.width = 128;
    sparse.height = 96;
    let index = 17;
    let mut values = sparse.pixels.to_vec();
    values[index] = 255;
    sparse.pixels = values.into();
    archive.ingest(&sparse, [2048, 1536]);
    let mut dense = sparse.clone();
    dense.frame = 0;
    dense.pixels = vec![255; 128 * 96].into();
    archive.ingest(&dense, [2048, 1536]);
    let mut probe = RegionProbe::default();
    probe.set_source_frame(Some(8));
    probe.update(&archive, 0, [2048, 1536], 9, unit());
    assert_eq!(probe.spatial.len(), 128 * 96);
    let cap = ((image().area() / 32.0) as usize).clamp(24, 768);
    assert!(
        !index.is_multiple_of(probe.spatial.len().div_ceil(cap)),
        "old union thinning really omitted this positive"
    );
    let ctx = egui::Context::default();
    let (mesh, _) = paint(&ctx, &probe, image(), image());
    let sparse_vertices: Vec<_> = mesh
        .vertices
        .iter()
        .filter(|v| v.color == capture_ink(8))
        .collect();
    assert!(
        !sparse_vertices.is_empty(),
        "the lone admitted current source must be visible"
    );
    let meta = archive.cells(0, 8).unwrap().0;
    let uv = SampleGeometry::new(0, meta)
        .unwrap()
        .at(index)
        .unwrap()
        .center;
    let actual_center = image().min + uv.to_vec2() * image().size();
    assert!(
        sparse_vertices
            .iter()
            .all(|v| v.pos.distance(actual_center) < 4.5)
    );
    assert!(
        mesh.vertices.iter().any(|v| v.color == capture_ink(0)),
        "dense peer remains independently visible"
    );
    assert!(
        mesh.vertices.len() <= (768 + 1) * 32,
        "each source independently respects the original marker budget"
    );
}
