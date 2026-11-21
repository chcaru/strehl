use super::*;
use crate::pipeline::{DiagnosticScale, DiagnosticScope, DiagnosticSurface};

const EXTENT: [usize; 2] = [3516, 2344];

fn packet(frame: usize, level: usize, sequence: u64, admitted: usize) -> DiagnosticSurface {
    let (width, height) = (16, 12);
    DiagnosticSurface {
        sequence,
        frame,
        level,
        kind: DiagnosticKind::GateSupport,
        scope: DiagnosticScope::Frame,
        scale: DiagnosticScale::Linear,
        width,
        height,
        min: 0.0,
        max: 1.0,
        folded: 1,
        pixels: (0..width * height)
            .map(|index| if index < admitted { 255 } else { 0 })
            .collect::<Vec<_>>()
            .into(),
    }
}

/// Planes 0..planes with `admitted(plane)` of 192 sites, skipping `missing`.
fn archive(
    planes: usize,
    missing: &[usize],
    admitted: impl Fn(usize) -> usize,
) -> AdmissionArchive {
    let mut archive = AdmissionArchive::default();
    for plane in (0..planes).filter(|plane| !missing.contains(plane)) {
        archive.ingest(&packet(plane, 0, plane as u64 + 1, admitted(plane)), EXTENT);
    }
    archive
}

fn ridge(planes: usize) -> impl Fn(usize) -> usize {
    move |plane| {
        let centre = planes as f32 * 0.45;
        let width = planes as f32 * 0.18;
        let t = (plane as f32 - centre) / width;
        if plane < planes / 6 || plane > planes * 5 / 6 {
            0
        } else {
            (180.0 * (-t * t).exp()).round() as usize + 4
        }
    }
}

fn run(
    ctx: &egui::Context,
    events: Vec<egui::Event>,
    paint: impl FnMut(&mut Ui),
) -> egui::FullOutput {
    let mut paint = paint;
    ctx.run(
        egui::RawInput {
            screen_rect: Some(Rect::from_min_size(Pos2::ZERO, egui::vec2(1332.0, 200.0))),
            events,
            ..Default::default()
        },
        |ctx| {
            egui::CentralPanel::default()
                .frame(egui::Frame::NONE)
                .show(ctx, |ui| paint(ui));
        },
    )
}

const CHART: Rect = Rect {
    min: Pos2 { x: 0.0, y: 30.0 },
    max: Pos2 {
        x: 1332.0,
        y: 114.0,
    },
};

fn texts(output: &egui::FullOutput) -> Vec<(String, Rect)> {
    let mut found = Vec::new();
    for clipped in &output.shapes {
        collect_texts(&clipped.shape, &mut found);
    }
    found
}
fn collect_texts(shape: &Shape, found: &mut Vec<(String, Rect)>) {
    match shape {
        Shape::Text(text) => found.push((
            text.galley.text().to_owned(),
            text.galley.rect.translate(text.pos.to_vec2()),
        )),
        Shape::Vec(shapes) => shapes.iter().for_each(|shape| collect_texts(shape, found)),
        _ => {}
    }
}

#[test]
fn exact_maps_history_bins_and_missing_planes_stay_distinct() {
    // Plane 2 is observed at zero, plane 3 has no map and no history.
    let archive = archive(6, &[3], |plane| [96, 48, 0, 0, 192, 12][plane]);
    let mut rail = DepthRail::default();
    assert!(rail.update(&archive, &[], 6, 0, 1));
    assert_eq!(rail.share(0), Some(0.5));
    assert_eq!(rail.share(1), Some(0.25));
    assert_eq!(rail.share(2), Some(0.0), "an observed zero is evidence");
    assert_eq!(rail.share(3), None, "a missing map is not a zero");
    assert_eq!(rail.evidence(3).unwrap().source, EvidenceSource::Missing);
    assert_eq!(rail.evidence(4).unwrap().source, EvidenceSource::Map);
    assert_eq!(rail.peak(), 1.0);

    // A history bin fills a plane whose map was dropped, at its own resolution.
    let mut progress = PipelineProgress::default();
    progress.ingest("STREHL_UI_PROGRESS event=diagnostic seq=9 frame=3 level=0 kind=gate-support scope=frame scale=linear width=2 height=1 min=0 max=1 folded=1 total=6 sampling=nearest data=ff00\n");
    assert_eq!(progress.sampled_mask_history.len(), 1);
    assert!(rail.update(&archive, &progress.sampled_mask_history, 6, 0, 2));
    assert_eq!(rail.share(3), Some(0.5));
    assert_eq!(rail.evidence(3).unwrap().source, EvidenceSource::History);
    assert_eq!(
        rail.evidence(0).unwrap().source,
        EvidenceSource::Map,
        "maps win"
    );
}

#[test]
fn history_above_1024_planes_is_pooled_per_bin_and_unobserved_bins_stay_missing() {
    let mut progress = PipelineProgress::default();
    // 1,500 planes share 1,024 bins; plane 0 sits alone in bin 0.
    progress.ingest("STREHL_UI_PROGRESS event=diagnostic seq=1 frame=0 level=0 kind=gate-support scope=frame scale=linear width=2 height=1 min=0 max=1 folded=1 total=1500 sampling=nearest data=ffff\n");
    progress.ingest("STREHL_UI_PROGRESS event=diagnostic seq=2 frame=1499 level=0 kind=gate-support scope=frame scale=linear width=2 height=1 min=0 max=1 folded=1 total=1500 sampling=nearest data=0000\n");
    let mut rail = DepthRail::default();
    rail.update(
        &AdmissionArchive::default(),
        &progress.sampled_mask_history,
        1500,
        0,
        evidence_revision(&progress),
    );
    assert_eq!(rail.share(0), Some(1.0));
    assert_eq!(rail.share(1499), Some(0.0));
    assert_eq!(rail.share(700), None);
    // A history for another plane count or level is never borrowed.
    rail.update(
        &AdmissionArchive::default(),
        &progress.sampled_mask_history,
        1501,
        0,
        7,
    );
    assert_eq!(rail.share(0), None);
    rail.update(
        &AdmissionArchive::default(),
        &progress.sampled_mask_history,
        1500,
        1,
        8,
    );
    assert_eq!(rail.share(0), None);
}

#[test]
fn evidence_revision_moves_with_every_packet_even_when_only_history_changes() {
    let mut progress = PipelineProgress::default();
    let before = evidence_revision(&progress);
    progress.ingest("STREHL_UI_PROGRESS event=diagnostic seq=1 frame=0 level=0 kind=gate-support scope=frame scale=linear width=2 height=1 min=0 max=1 folded=1 total=4 sampling=nearest data=ffff\n");
    let first = evidence_revision(&progress);
    assert_ne!(before, first);
    progress.ingest("STREHL_UI_PROGRESS event=diagnostic seq=2 frame=1 level=0 kind=gate-support scope=frame scale=linear width=2 height=1 min=0 max=1 folded=1 total=4 sampling=nearest data=ff00\n");
    assert_ne!(first, evidence_revision(&progress));
    assert_eq!(evidence_revision(&progress), evidence_revision(&progress));
}

#[test]
fn unchanged_receipts_are_not_recounted_on_a_new_revision() {
    let planes = 299;
    let mut archive = archive(planes, &[], ridge(planes));
    let mut rail = DepthRail::default();
    rail.update(&archive, &[], planes, 0, 1);
    assert_eq!(rail.builds.counts, planes);
    archive.ingest(&packet(10, 0, 9_999, 7), EXTENT);
    assert!(rail.update(&archive, &[], planes, 0, 2));
    assert_eq!(
        rail.builds.counts,
        planes + 1,
        "only the replaced receipt is recounted"
    );
    assert!(
        !rail.update(&archive, &[], planes, 0, 2),
        "same key does nothing"
    );
    assert_eq!(rail.builds.series, 2);
}

#[test]
fn pointer_motion_and_markers_rebuild_no_mesh_or_series() {
    let planes = 299;
    let archive = archive(planes, &[], ridge(planes));
    let ctx = egui::Context::default();
    let mut rail = DepthRail::default();
    let mut responses = Vec::new();
    for step in 0..60 {
        let x = 30.0 + step as f32 * 21.0;
        let events = vec![egui::Event::PointerMoved(egui::pos2(x, 70.0))];
        let _ = run(&ctx, events, |ui| {
            rail.update(&archive, &[], planes, 0, 1);
            let response = rail.interact(ui, CHART, egui::Id::new("rail"));
            responses.push(response.hovered);
            rail.paint(
                ui.painter(),
                CHART,
                RailPalette::GRAPHITE,
                RailMarkers {
                    hover: response.hovered,
                    head: Some(84),
                },
            );
        });
    }
    assert_eq!(rail.builds.series, 1);
    assert_eq!(
        rail.builds.meshes, 1,
        "markers are drawn over one cached mesh"
    );
    assert_eq!(rail.builds.regions, 0);
    let geometry = RailGeometry::new(CHART, planes).unwrap();
    assert_eq!(responses[1], Some(geometry.plane_at(51.0)));
    assert!(responses.iter().skip(1).all(Option::is_some));
    // A new rect, a new palette or a new series rebuilds exactly once.
    let _ = run(&ctx, vec![], |ui| {
        rail.paint(
            ui.painter(),
            CHART.translate(egui::vec2(0.0, 1.0)),
            RailPalette::GRAPHITE,
            RailMarkers::default(),
        );
    });
    assert_eq!(rail.builds.meshes, 2);
}

#[test]
fn region_series_is_read_only_when_its_key_changes() {
    let planes = 130;
    let archive = archive(planes, &[], ridge(planes));
    let ctx = egui::Context::default();
    let mut rail = DepthRail::default();
    rail.update(&archive, &[], planes, 0, 1);
    let mut reads = 0;
    for step in 0..40 {
        // Pointer jitter inside one sample window keeps the same key.
        let key = Some(step / 10);
        rail.set_region(key, || {
            reads += 1;
            (40..80).map(|plane| (plane, plane % 7 + 1, 8))
        });
        let _ = run(&ctx, vec![], |ui| {
            rail.paint(
                ui.painter(),
                CHART,
                RailPalette::GRAPHITE,
                RailMarkers::default(),
            );
        });
    }
    assert_eq!(reads, 4);
    assert_eq!(rail.builds.regions, 4);
    assert!(rail.has_region());
    rail.set_region(None, Vec::new);
    assert!(!rail.has_region());
}

#[test]
fn six_thousand_planes_draw_at_most_one_column_per_two_pixels() {
    let planes = 6_000;
    // Maps are capped by the archive today; the history covers the rest.
    let mut progress = PipelineProgress::default();
    for frame in (0..planes).step_by(3) {
        let data = if (2_000..4_000).contains(&frame) {
            "ffff"
        } else {
            "ff00"
        };
        progress.ingest(&format!("STREHL_UI_PROGRESS event=diagnostic seq={} frame={frame} level=0 kind=gate-support scope=frame scale=linear width=2 height=1 min=0 max=1 folded=1 total={planes} sampling=nearest data={data}\n", frame + 1));
    }
    let archive = archive(1_000, &[], ridge(1_000));
    let mut rail = DepthRail::default();
    rail.update(
        &archive,
        &progress.sampled_mask_history,
        planes,
        0,
        evidence_revision(&progress),
    );
    let geometry = RailGeometry::new(CHART, planes).unwrap();
    assert!(geometry.pooled());
    assert!(geometry.columns as f32 <= (geometry.right - geometry.left) / 2.0);
    assert_eq!(geometry.columns, 646);
    let ctx = egui::Context::default();
    let output = run(&ctx, vec![], |ui| {
        rail.paint(
            ui.painter(),
            CHART,
            RailPalette::GRAPHITE,
            RailMarkers::default(),
        );
    });
    // Count the bar quads: vertices in the fill colour, four per bar.
    let fill = RailPalette::GRAPHITE.ok.gamma_multiply(0.6);
    let quads: usize = output
        .shapes
        .iter()
        .filter_map(|clipped| match &clipped.shape {
            Shape::Mesh(mesh) => Some(mesh.vertices.iter().filter(|v| v.color == fill).count() / 4),
            _ => None,
        })
        .sum();
    assert!(
        quads > 0 && quads <= geometry.columns,
        "{quads} quads for {} columns",
        geometry.columns
    );
    // The scale thins: no tick closer than 4 px, no numeral closer than 44 px.
    let (minor, major) = scale_intervals(geometry);
    assert!(minor as f32 * geometry.step() >= 4.0);
    assert!(major as f32 * geometry.step() >= 44.0);
    let numerals = texts(&output)
        .into_iter()
        .filter(|(text, _)| text.parse::<usize>().is_ok())
        .count();
    assert!(numerals <= 30, "{numerals} numerals");
}

#[test]
fn scale_matches_the_mockup_at_299_planes_and_numerals_hide_under_markers() {
    let planes = 299;
    let geometry = RailGeometry::new(CHART, planes).unwrap();
    assert!(!geometry.pooled());
    assert_eq!(scale_intervals(geometry), (5, 25));
    let archive = archive(planes, &[], ridge(planes));
    let ctx = egui::Context::default();
    let mut rail = DepthRail::default();
    rail.update(&archive, &[], planes, 0, 1);
    let bare = run(&ctx, vec![], |ui| {
        rail.paint(
            ui.painter(),
            CHART,
            RailPalette::GRAPHITE,
            RailMarkers::default(),
        );
    });
    let shown: Vec<String> = texts(&bare).into_iter().map(|(text, _)| text).collect();
    for expected in ["NEAR", "FAR", "25", "100", "275"] {
        assert!(
            shown.iter().any(|text| text == expected),
            "{expected} in {shown:?}"
        );
    }
    assert!(!shown.iter().any(|text| text == "300"));
    // The head marker on plane 100 hides the numeral 100 and shows its own box.
    let marked = run(&ctx, vec![], |ui| {
        rail.paint(
            ui.painter(),
            CHART,
            RailPalette::GRAPHITE,
            RailMarkers {
                hover: Some(149),
                head: Some(99),
            },
        );
    });
    let numerals: Vec<(String, Rect)> = texts(&marked);
    let hundred: Vec<_> = numerals.iter().filter(|(text, _)| text == "100").collect();
    assert_eq!(hundred.len(), 1, "only the marker's own label remains");
    assert!(numerals.iter().filter(|(text, _)| text == "150").count() == 1);
    assert!(
        numerals.iter().any(|(text, _)| text == "125"),
        "neighbours stay"
    );
}

#[test]
fn observed_zero_draws_a_baseline_and_a_missing_plane_a_hatch_never_a_bar() {
    let planes = 40;
    // Plane 12 observed at zero; plane 20 missing.
    let archive = archive(planes, &[20], |plane| if plane == 12 { 0 } else { 96 });
    let ctx = egui::Context::default();
    let mut rail = DepthRail::default();
    rail.update(&archive, &[], planes, 0, 1);
    let output = run(&ctx, vec![], |ui| {
        rail.paint(
            ui.painter(),
            CHART,
            RailPalette::GRAPHITE,
            RailMarkers::default(),
        );
    });
    let geometry = RailGeometry::new(CHART, planes).unwrap();
    let mesh = output
        .shapes
        .iter()
        .find_map(|clipped| match &clipped.shape {
            Shape::Mesh(mesh) => Some(mesh.clone()),
            _ => None,
        })
        .unwrap();
    let near = |plane: usize, v: &egui::epaint::Vertex| {
        (v.pos.x - geometry.x(plane)).abs() < geometry.step() * 0.4
    };
    let fill = RailPalette::GRAPHITE.ok.gamma_multiply(0.6);
    let line2 = RailPalette::GRAPHITE.line2;
    for plane in [12, 20] {
        assert!(
            !mesh
                .vertices
                .iter()
                .any(|v| near(plane, v) && v.color == fill),
            "plane {plane} must draw no bar"
        );
    }
    let zero: Vec<_> = mesh
        .vertices
        .iter()
        .filter(|v| near(12, v) && v.color == line2)
        .collect();
    assert!(
        zero.iter().all(|v| v.pos.y >= geometry.base - 1.01),
        "zero is a 1 px baseline"
    );
    assert!(!zero.is_empty());
    let hatch_top = mesh
        .vertices
        .iter()
        .filter(|v| near(20, v) && v.color.a() > 0 && v.color.r() == line2.r())
        .map(|v| v.pos.y)
        .fold(f32::INFINITY, f32::min);
    assert!(
        hatch_top < geometry.base - 1.5,
        "a missing plane is hatched above the baseline"
    );
    assert!(mesh.vertices.iter().any(|v| near(11, v) && v.color == fill));
}

#[test]
fn no_detail_brackets_cover_empty_ends_but_never_unobserved_planes() {
    let planes = 299;
    let archive = archive(planes, &[150], ridge(planes));
    let mut rail = DepthRail::default();
    rail.update(&archive, &[], planes, 0, 1);
    let runs = rail.brackets().to_vec();
    assert_eq!(runs.first().unwrap().start, 0);
    assert_eq!(runs.last().unwrap().end, planes);
    assert!(runs.iter().all(|run| !run.contains(&150)));
    // Two short dips are not brackets.
    let archive = archive_with_dips();
    rail.update(&archive, &[], 100, 0, 2);
    assert!(rail.brackets().is_empty());
}

fn archive_with_dips() -> AdmissionArchive {
    archive(
        100,
        &[],
        |plane| if plane == 30 || plane == 31 { 0 } else { 120 },
    )
}

#[test]
fn geometry_picks_the_nearest_plane_and_handles_a_single_plane() {
    let geometry = RailGeometry::new(CHART, 299).unwrap();
    assert_eq!(
        geometry.plane_at(geometry.x(84) + geometry.step() * 0.45),
        84
    );
    assert_eq!(geometry.plane_at(-100.0), 0);
    assert_eq!(geometry.plane_at(5_000.0), 298);
    let one = RailGeometry::new(CHART, 1).unwrap();
    assert_eq!(one.plane_at(10.0), 0);
    assert_eq!(one.x(0), CHART.center().x);
    assert!(RailGeometry::new(CHART, 0).is_none());
    let pooled = RailGeometry::new(CHART, 1_500).unwrap();
    let covered: usize = (0..pooled.columns)
        .map(|c| pooled.column_range(c).len())
        .sum();
    assert_eq!(covered, 1_500);
    assert_eq!(pooled.column_of(1_499), pooled.columns - 1);
}
