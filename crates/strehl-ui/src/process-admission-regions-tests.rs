use super::*;
use crate::pipeline::{DiagnosticKind, DiagnosticScale, DiagnosticScope, DiagnosticSurface};

#[test]
fn sparse_region_compaction_preserves_every_triangle_and_contour_exactly() {
    let mut region = Arc::try_unwrap(extracted([128, 96], |x, y| {
        (60..68).contains(&x) && (44..52).contains(&y)
    }))
    .ok()
    .unwrap();
    assert!(
        !region.is_empty(),
        "the fixture must contain a drawn region"
    );
    assert!(
        region.vertices.len() < (128 + 2) * (96 + 2) / 16,
        "a sparse patch must not retain the full padded lattice"
    );
    let vertices = region.vertices.clone();
    let indices = region.indices.clone();
    let contours = region.contours.clone();
    let triangles: Vec<_> = region
        .indices
        .iter()
        .map(|&index| region.vertices[index as usize])
        .collect();
    // Put an unused vertex before every live vertex, so compaction must move
    // every reference; merely removing an unused tail cannot pass this check.
    region.vertices = vertices
        .iter()
        .flat_map(|&point| [egui::pos2(-9.0, -7.0), point])
        .collect();
    for index in &mut region.indices {
        *index = *index * 2 + 1;
    }
    assert_eq!(region.vertices.len(), vertices.len() * 2);
    region.compact_vertices();
    assert_eq!(region.vertices, vertices);
    assert_eq!(
        region.indices, indices,
        "remapping follows original vertex order"
    );
    assert_eq!(region.contours, contours);
    assert_eq!(
        region
            .indices
            .iter()
            .map(|&index| region.vertices[index as usize])
            .collect::<Vec<_>>(),
        triangles
    );
    region.compact_vertices();
    assert_eq!(region.vertices, vertices, "a second compaction is stable");
    assert_eq!(region.indices, indices);
}

const DOMAIN: [u64; 2] = [4, 7];
const EXTENT: [usize; 2] = [1001, 701];

fn packet(
    sequence: u64,
    frame: usize,
    size: [usize; 2],
    yes: impl Fn(usize, usize) -> bool,
) -> DiagnosticSurface {
    DiagnosticSurface {
        sequence,
        frame,
        level: 0,
        kind: DiagnosticKind::GateSupport,
        scope: DiagnosticScope::Frame,
        scale: DiagnosticScale::Linear,
        width: size[0],
        height: size[1],
        min: 0.0,
        max: 1.0,
        pixels: (0..size[0] * size[1])
            .map(|index| {
                if yes(index % size[0], index / size[0]) {
                    255
                } else {
                    0
                }
            })
            .collect::<Vec<_>>()
            .into(),
        folded: 1,
    }
}

fn extracted(size: [usize; 2], yes: impl Fn(usize, usize) -> bool) -> Arc<DenseRegion> {
    let mut archive = AdmissionArchive::default();
    archive.ingest(&packet(1, 0, size, yes), EXTENT);
    DenseAdmissionCache::default()
        .region(&archive, DOMAIN, 0, 0, EXTENT, RegionSettings::default())
        .unwrap()
}

fn covered(region: &DenseRegion, point: Pos2) -> bool {
    let cross = |a: Pos2, b: Pos2, c: Pos2| (b.x - a.x) * (c.y - a.y) - (b.y - a.y) * (c.x - a.x);
    region.indices.as_chunks::<3>().0.iter().any(|triangle| {
        let [a, b, c] =
            [triangle[0], triangle[1], triangle[2]].map(|index| region.vertices[index as usize]);
        let signs = [cross(a, b, point), cross(b, c, point), cross(c, a, point)];
        signs.iter().all(|&value| value >= -1e-7) || signs.iter().all(|&value| value <= 1e-7)
    })
}

#[test]
fn settings_are_display_only_enabled_by_default_and_bounded() {
    let context = egui::Context::default();
    assert_eq!(
        RegionSettings::read(&context),
        RegionSettings {
            enabled: true,
            threshold: 60
        }
    );
    RegionSettings {
        enabled: false,
        threshold: 255,
    }
    .write(&context);
    assert_eq!(
        RegionSettings::read(&context),
        RegionSettings {
            enabled: false,
            threshold: 85
        }
    );
    RegionSettings {
        enabled: true,
        threshold: 1,
    }
    .write(&context);
    assert_eq!(RegionSettings::read(&context).threshold, 35);
}

#[test]
fn isolated_and_distributed_positives_fail_before_a_coherent_patch_passes() {
    // Nulls precede the positive control. Shuffling the same 64 admitted
    // observations breaks their spatial evidence without changing the count.
    let isolated = extracted([32, 32], |x, y| x == 0 && y == 0);
    assert_eq!(isolated.admitted, 1);
    assert!(isolated.is_empty());
    let dispersed = extracted([32, 32], |x, y| x % 4 == 0 && y % 4 == 0);
    let patch = extracted([32, 32], |x, y| {
        (12..20).contains(&x) && (12..20).contains(&y)
    });
    assert_eq!(dispersed.admitted, patch.admitted);
    assert_eq!(patch.admitted, 64);
    assert!(
        dispersed.is_empty(),
        "equal counts do not establish a coherent surface"
    );
    assert!(
        !patch.is_empty(),
        "the positive control must actually retain a patch"
    );
    assert_eq!(patch.islands, 1);
    assert!(covered(&patch, egui::pos2(0.5, 0.5)));
    assert!(!covered(&patch, egui::pos2(0.1, 0.1)));
}

#[test]
fn alternating_noise_and_tiny_clusters_cannot_seed_regions() {
    let checker = extracted([32, 24], |x, y| (x + y) % 2 == 0);
    let tiny = extracted([32, 24], |x, y| {
        (10..12).contains(&x) && (10..12).contains(&y)
    });
    assert!(checker.admitted > checker.observed / 3);
    assert!(
        checker.is_empty(),
        "raw admission count must not stand in for coherent density"
    );
    assert!(tiny.is_empty());
    let samples: Vec<_> = (0..32 * 24).map(|i| (i % 32 + i / 32) % 2 == 0).collect();
    let local = density(&samples, 32, 24);
    let (retained, islands) = coherent(&local, &samples, 32, 24, 0.35, 0.55);
    assert_eq!(
        islands, 0,
        "the lowest user setting must still reject checker noise"
    );
    assert!(!retained.iter().any(|&yes| yes));
}

#[test]
fn density_is_normalized_at_the_border_without_amplifying_one_sample() {
    assert!(
        density(&[false; 49], 7, 7)
            .iter()
            .all(|&value| value == 0.0)
    );
    assert!(density(&[true; 49], 7, 7).iter().all(|&value| value == 1.0));
    let mut one = [false; 49];
    one[0] = true;
    assert!(density(&one, 7, 7).iter().all(|&value| value < 0.35));
}

#[test]
fn lower_density_edges_require_connection_to_high_confidence_seeds() {
    // This fixture distinguishes hysteresis from either a high-only mask or
    // an unseeded low cutoff. Two generous components share the same fringe.
    let mut field = vec![0.0; 24 * 12];
    for y in 2..10 {
        for x in 2..10 {
            field[y * 24 + x] = 0.65;
        }
        for x in 14..22 {
            field[y * 24 + x] = 0.65;
        }
    }
    field[4 * 24 + 4] = 0.9;
    field[4 * 24 + 5] = 0.9;
    let samples: Vec<_> = field.iter().map(|&value| value > 0.0).collect();
    let (retained, islands) = coherent(&field, &samples, 24, 12, 0.6, 0.8);
    assert_eq!(islands, 1);
    assert!(
        retained[8 * 24 + 8],
        "connected lower-density fringe is retained"
    );
    assert!(
        !retained[8 * 24 + 18],
        "same-density unseeded island is rejected"
    );
}

#[test]
fn strong_seeds_do_not_override_the_minimum_island_area() {
    let mut field = vec![0.0; 16 * 16];
    for y in 4..7 {
        for x in 4..7 {
            field[y * 16 + x] = 1.0;
        }
    }
    let samples: Vec<_> = field.iter().map(|&value| value > 0.0).collect();
    let (_, islands) = coherent(&field, &samples, 16, 16, 0.6, 0.8);
    assert_eq!(samples.iter().filter(|&&value| value).count(), 9);
    assert_eq!(islands, 0, "a strong but tiny island must still fail");
    for x in 4..7 {
        field[7 * 16 + x] = 1.0;
    }
    let samples: Vec<_> = field.iter().map(|&value| value > 0.0).collect();
    assert_eq!(coherent(&field, &samples, 16, 16, 0.6, 0.8).1, 1);
}

#[test]
fn diagonal_saddles_do_not_join_four_connected_islands() {
    let mut archive = AdmissionArchive::default();
    archive.ingest(
        &packet(1, 0, [24, 24], |x, y| {
            ((3..11).contains(&x) && (3..11).contains(&y))
                || ((11..19).contains(&x) && (11..19).contains(&y))
        }),
        EXTENT,
    );
    let region = DenseAdmissionCache::default()
        .region(
            &archive,
            DOMAIN,
            0,
            0,
            EXTENT,
            RegionSettings {
                threshold: 55,
                ..RegionSettings::default()
            },
        )
        .unwrap();
    // At this cutoff the two diagonal corner samples survive, while both
    // cardinal neighbours do not. This explicitly exercises the saddle.
    assert!(region.retained[10 * 24 + 10]);
    assert!(region.retained[11 * 24 + 11]);
    assert!(!region.retained[10 * 24 + 11]);
    assert!(!region.retained[11 * 24 + 10]);
    assert_eq!(region.islands, 2);
    assert_eq!(region.contours.len(), 2);
    assert!(
        region
            .contours
            .iter()
            .all(|contour| contour.first() == contour.last())
    );
    let geometry = SampleGeometry::new(0, archive.metadata(0, 0).unwrap()).unwrap();
    let saddle = geometry
        .at(10 * 24 + 10)
        .unwrap()
        .center
        .lerp(geometry.at(11 * 24 + 11).unwrap().center, 0.5);
    assert!(
        !covered(&region, saddle),
        "a fixed positive diagonal would paint this gap"
    );
}

#[test]
fn rejected_hole_is_unshaded_and_has_its_own_closed_contour() {
    let region = extracted([32, 32], |x, y| {
        !((12..20).contains(&x) && (12..20).contains(&y))
    });
    assert_eq!(region.islands, 1);
    assert_eq!(
        region.contours.len(),
        2,
        "outer image perimeter and inner hole"
    );
    assert!(
        region
            .contours
            .iter()
            .all(|contour| contour.first() == contour.last())
    );
    assert!(!region.retained[16 * 32 + 16]);
    assert!(
        !covered(&region, egui::pos2(0.5, 0.5)),
        "a contour-only hole would still incorrectly shade its interior"
    );
    assert!(covered(&region, egui::pos2(0.2, 0.5)));
}

#[test]
fn disconnected_components_keep_an_unshaded_gap() {
    let region = extracted([40, 24], |x, y| {
        (5..19).contains(&y) && ((3..14).contains(&x) || (26..37).contains(&x))
    });
    assert_eq!(region.islands, 2);
    assert_eq!(region.contours.len(), 2);
    assert!(
        region
            .contours
            .iter()
            .all(|contour| contour.first() == contour.last())
    );
    assert!(covered(&region, egui::pos2(0.2, 0.5)));
    assert!(covered(&region, egui::pos2(0.8, 0.5)));
    assert!(!covered(&region, egui::pos2(0.5, 0.5)));
}

#[test]
fn full_admission_reaches_the_image_border_with_exact_unit_area() {
    let region = extracted([16, 12], |_, _| true);
    assert_eq!(region.islands, 1);
    assert_eq!(region.contours.len(), 1);
    let contour = &region.contours[0];
    assert_eq!(contour.first(), contour.last());
    for corner in [
        Pos2::ZERO,
        egui::pos2(1.0, 0.0),
        egui::pos2(1.0, 1.0),
        egui::pos2(0.0, 1.0),
    ] {
        assert!(contour.contains(&corner));
    }
    let area: f32 = region
        .indices
        .as_chunks::<3>()
        .0
        .iter()
        .map(|triangle| {
            let [a, b, c] = [triangle[0], triangle[1], triangle[2]]
                .map(|index| region.vertices[index as usize]);
            ((b.x - a.x) * (c.y - a.y) - (b.y - a.y) * (c.x - a.x)).abs() * 0.5
        })
        .sum();
    assert!(
        (area - 1.0).abs() < 1e-5,
        "triangles must partition the photo without overlap"
    );
}

#[test]
fn geometry_uses_the_actual_phase_zero_lattice_on_odd_extents() {
    let meta = AdmissionMeta {
        sequence: 1,
        samples: [8, 6],
        extent: [35, 27],
    };
    let geometry = SampleGeometry::new(2, meta).unwrap();
    let region =
        DenseRegion::extract(meta, geometry, &[true; 48], RegionSettings::default()).unwrap();
    // Interior grid vertices begin one padded row and one column in.
    assert_eq!(region.vertices[11], geometry.at(0).unwrap().center);
    assert_ne!(region.vertices[11], egui::pos2(0.5 / 8.0, 0.5 / 6.0));
    assert!(region.vertices.iter().all(|point| point.is_finite()
        && (0.0..=1.0).contains(&point.x)
        && (0.0..=1.0).contains(&point.y)));
}

#[test]
fn missing_invalid_and_observed_empty_domains_are_distinct() {
    let mut archive = AdmissionArchive::default();
    let mut cache = DenseAdmissionCache::default();
    assert!(
        cache
            .region(&archive, DOMAIN, 0, 0, EXTENT, RegionSettings::default())
            .is_none()
    );
    archive.ingest(&packet(1, 0, [12, 12], |_, _| false), EXTENT);
    let zero = cache
        .region(&archive, DOMAIN, 0, 0, EXTENT, RegionSettings::default())
        .unwrap();
    assert_eq!((zero.admitted, zero.observed), (0, 144));
    assert!(zero.is_empty());
    assert!(
        cache
            .region(
                &archive,
                DOMAIN,
                0,
                0,
                [1000, 701],
                RegionSettings::default()
            )
            .is_none()
    );
    let mut impossible = packet(2, 0, [12, 12], |_, _| true);
    impossible.level = 63;
    archive.ingest(&impossible, EXTENT);
    assert!(
        cache
            .region(&archive, DOMAIN, 0, 63, EXTENT, RegionSettings::default())
            .is_none()
    );
    let before = cache.builds;
    assert!(
        cache
            .region(
                &archive,
                DOMAIN,
                0,
                0,
                EXTENT,
                RegionSettings {
                    enabled: false,
                    ..RegionSettings::default()
                }
            )
            .is_none()
    );
    assert_eq!(
        cache.builds, before,
        "disabled overlay should do no extraction work"
    );
}

#[test]
fn cache_reuses_each_receipt_across_frames_and_unrelated_packets() {
    let mut archive = AdmissionArchive::default();
    archive.ingest(&packet(1, 0, [12, 12], |_, _| true), EXTENT);
    archive.ingest(&packet(2, 1, [12, 12], |_, _| true), EXTENT);
    let mut cache = DenseAdmissionCache::default();
    let first = cache
        .region(&archive, DOMAIN, 0, 0, EXTENT, RegionSettings::default())
        .unwrap();
    cache.region(&archive, DOMAIN, 1, 0, EXTENT, RegionSettings::default());
    for _ in 0..20 {
        let repeated = cache
            .region(&archive, DOMAIN, 0, 0, EXTENT, RegionSettings::default())
            .unwrap();
        assert!(Arc::ptr_eq(&first, &repeated));
    }
    archive.ingest(&packet(3, 2, [12, 12], |_, _| false), EXTENT);
    assert!(Arc::ptr_eq(
        &first,
        &cache
            .region(&archive, DOMAIN, 0, 0, EXTENT, RegionSettings::default())
            .unwrap()
    ));
    assert_eq!(cache.builds, 2);
    archive.ingest(&packet(4, 0, [12, 12], |_, _| false), EXTENT);
    let refreshed = cache
        .region(&archive, DOMAIN, 0, 0, EXTENT, RegionSettings::default())
        .unwrap();
    assert!(!Arc::ptr_eq(&first, &refreshed));
    assert!(refreshed.is_empty());
    assert_eq!(cache.builds, 3);
}

#[test]
fn threshold_run_identity_and_lru_capacity_invalidate_only_the_right_entries() {
    let mut archive = AdmissionArchive::default();
    for frame in 0..34 {
        archive.ingest(
            &packet(frame as u64 + 1, frame, [12, 12], |_, _| true),
            EXTENT,
        );
    }
    let mut cache = DenseAdmissionCache::default();
    let first = cache
        .region(&archive, DOMAIN, 0, 0, EXTENT, RegionSettings::default())
        .unwrap();
    let threshold = cache
        .region(
            &archive,
            DOMAIN,
            0,
            0,
            EXTENT,
            RegionSettings {
                threshold: 85,
                ..RegionSettings::default()
            },
        )
        .unwrap();
    let new_run = cache
        .region(&archive, [4, 8], 0, 0, EXTENT, RegionSettings::default())
        .unwrap();
    assert!(!Arc::ptr_eq(&first, &threshold));
    assert!(!Arc::ptr_eq(&first, &new_run));
    for frame in 1..34 {
        cache.region(
            &archive,
            DOMAIN,
            frame,
            0,
            EXTENT,
            RegionSettings::default(),
        );
    }
    assert_eq!(cache.entries.len(), 32);
    let evicted = cache
        .region(&archive, DOMAIN, 0, 0, EXTENT, RegionSettings::default())
        .unwrap();
    assert!(!Arc::ptr_eq(&first, &evicted));
    assert_eq!(cache.entries.len(), 32);
}

#[test]
fn dashed_source_contours_keep_their_gaps_across_tiny_segments() {
    let points: Vec<_> = (0..=18).map(|x| egui::pos2(x as f32, 0.0)).collect();
    let clip = Rect::from_min_max(egui::pos2(-1.0, -1.0), egui::pos2(20.0, 1.0));
    let dashes = dashed_segments(&points, clip);
    let length: f32 = dashes.iter().map(|edge| edge[0].distance(edge[1])).sum();
    assert_eq!(length, 10.0, "two 5px dashes separated by genuine 4px gaps");
    assert!(
        dashes
            .iter()
            .all(|edge| edge[1].x <= 5.0 || edge[0].x >= 9.0)
    );
    let far_away = [egui::pos2(-1_000_000.0, 0.0), egui::pos2(1_000_000.0, 0.0)];
    assert!(
        dashed_segments(&far_away, clip).len() < 6,
        "off-screen zoom must not expand a million dashes"
    );
}

#[test]
fn projection_cache_reuses_stationary_mesh_and_distinguishes_source_guides() {
    let region = extracted([16, 12], |_, _| true);
    let context = egui::Context::default();
    let mut cache = DenseRegionPainter::default();
    let image = Rect::from_min_max(egui::pos2(10.0, 20.0), egui::pos2(310.0, 220.0));
    let aperture = Rect::from_min_max(Pos2::ZERO, egui::pos2(1.0, 1.0));
    let _output = context.run(egui::RawInput::default(), |ctx| {
        egui::CentralPanel::default().show(ctx, |ui| {
            cache.paint(ui.painter(), &region, image, aperture, Color32::GREEN);
            let first = cache.entries[0].mesh.clone();
            for _ in 0..10 {
                cache.paint(ui.painter(), &region, image, aperture, Color32::GREEN);
            }
            assert_eq!(cache.entries.len(), 1);
            assert!(Arc::ptr_eq(&first, &cache.entries[0].mesh));
            cache.paint_approximate(ui.painter(), &region, image, aperture, Color32::GREEN);
            assert_eq!(cache.entries.len(), 2);
            assert!(!Arc::ptr_eq(&first, &cache.entries[1].mesh));
            cache.paint(ui.painter(), &region, image, aperture, Color32::RED);
            cache.paint(
                ui.painter(),
                &region,
                image,
                Rect::from_min_max(egui::pos2(0.1, 0.1), egui::pos2(0.8, 0.8)),
                Color32::RED,
            );
            cache.paint(
                ui.painter(),
                &region,
                image.translate(egui::vec2(5.0, 0.0)),
                aperture,
                Color32::RED,
            );
            assert_eq!(cache.entries.len(), 4);
            assert!(cache.entries.iter().all(|entry| entry.mesh.is_valid()));
        });
    });
}

fn span(start: usize, end: usize, id: usize) -> SelectionSpan {
    SelectionSpan { start, end, id }
}

fn selection(archive: &AdmissionArchive, spans: &[SelectionSpan]) -> Arc<DenseSelection> {
    DenseAdmissionCache::default()
        .selection(archive, DOMAIN, spans, 0, EXTENT, RegionSettings::default())
        .unwrap()
}

fn polygon_contains(points: &[Pos2], point: Pos2) -> bool {
    let mut positive = false;
    let mut negative = false;
    for i in 0..points.len() {
        let a = points[(i + 1) % points.len()] - points[i];
        let b = point - points[i];
        let cross = a.x * b.y - a.y * b.x;
        positive |= cross > 1e-7;
        negative |= cross < -1e-7;
    }
    !(positive && negative)
}

fn members(inline: u64) -> Membership {
    Membership {
        inline,
        overflow: Vec::new(),
    }
}

fn membership_at(selection: &DenseSelection, point: Pos2) -> u64 {
    selection
        .patches
        .iter()
        .filter(|patch| polygon_contains(&patch.points, point))
        .fold(0, |mask, patch| {
            assert!(patch.membership.overflow.is_empty());
            mask | patch.membership.inline
        })
}

#[test]
fn range_union_reads_middle_frames_and_preserves_disjoint_support() {
    let mut archive = AdmissionArchive::default();
    archive.ingest(&packet(1, 4, [40, 24], |_, _| false), EXTENT);
    archive.ingest(
        &packet(2, 5, [40, 24], |x, y| {
            (3..14).contains(&x) && (5..19).contains(&y)
        }),
        EXTENT,
    );
    archive.ingest(
        &packet(3, 6, [40, 24], |x, y| {
            (26..37).contains(&x) && (5..19).contains(&y)
        }),
        EXTENT,
    );
    archive.ingest(&packet(4, 7, [40, 24], |_, _| false), EXTENT);
    let selected = selection(&archive, &[span(4, 7, 2)]);
    assert_eq!(selected.layers.len(), 1);
    let layer = &selected.layers[0];
    assert_eq!((layer.recorded_frames, layer.requested_frames), (4, 4));
    assert_eq!(layer.region.islands, 2);
    assert_eq!(layer.region.admitted, 11 * 14 * 2);
    assert_eq!(membership_at(&selected, egui::pos2(0.2, 0.5)), 1);
    assert_eq!(membership_at(&selected, egui::pos2(0.8, 0.5)), 1);
    assert_eq!(membership_at(&selected, egui::pos2(0.5, 0.5)), 0);
    let endpoints = selection(&archive, &[span(4, 4, 2), span(7, 7, 3)]);
    assert!(
        endpoints.is_empty(),
        "endpoint-only aggregation must fail this fixture"
    );
}

#[test]
fn range_union_keeps_sparse_noise_and_missing_receipts_honest() {
    let mut archive = AdmissionArchive::default();
    archive.ingest(
        &packet(1, 5, [32, 32], |x, y| x % 8 == 0 && y % 4 == 0),
        EXTENT,
    );
    archive.ingest(
        &packet(2, 7, [32, 32], |x, y| x % 8 == 4 && y % 4 == 0),
        EXTENT,
    );
    let selected = selection(&archive, &[span(4, 8, 0), span(20, 25, 1)]);
    assert_eq!(
        selected.layers.len(),
        1,
        "wholly missing ranges have no fabricated region"
    );
    assert_eq!(
        (
            selected.layers[0].recorded_frames,
            selected.layers[0].requested_frames
        ),
        (2, 5)
    );
    assert_eq!(selected.layers[0].region.admitted, 64);
    assert!(selected.is_empty());
    let mut cache = DenseAdmissionCache::default();
    assert!(
        cache
            .selection(
                &archive,
                DOMAIN,
                &[span(20, 25, 0)],
                0,
                EXTENT,
                RegionSettings::default()
            )
            .is_none()
    );
    assert!(
        cache
            .selection(
                &archive,
                DOMAIN,
                &[span(4, 8, 0)],
                0,
                [1000, 701],
                RegionSettings::default()
            )
            .is_none()
    );
    // A new lattice replaces the archive's old lattice. Its one actual packet
    // must not be combined with the two incompatible packets it displaced.
    archive.ingest(&packet(3, 6, [16, 16], |_, _| true), EXTENT);
    let reset = selection(&archive, &[span(4, 8, 0)]);
    assert_eq!(reset.layers[0].recorded_frames, 1);
    assert_eq!(reset.layers[0].region.observed, 256);
    assert_eq!(reset.layers[0].region.admitted, 256);
}

fn overlap_fixture() -> (AdmissionArchive, Arc<DenseSelection>) {
    let mut archive = AdmissionArchive::default();
    archive.ingest(&packet(1, 4, [32, 32], |x, _| x < 24), EXTENT);
    archive.ingest(
        &packet(2, 31, [32, 32], |x, y| {
            x >= 8 && !((13..19).contains(&x) && (13..19).contains(&y))
        }),
        EXTENT,
    );
    let selected = selection(&archive, &[span(4, 12, 0), span(31, 35, 1)]);
    (archive, selected)
}

#[test]
fn overlap_partition_matches_independent_region_triangles_including_holes_and_borders() {
    let (_, selected) = overlap_fixture();
    assert_eq!(membership_at(&selected, egui::pos2(0.1, 0.5)), 1);
    assert_eq!(membership_at(&selected, egui::pos2(0.9, 0.5)), 2);
    assert_eq!(membership_at(&selected, egui::pos2(0.5, 0.2)), 3);
    assert_eq!(
        membership_at(&selected, egui::pos2(0.5, 0.5)),
        1,
        "the second range's hole is not an overlap"
    );
    let mut counts = [0usize; 4];
    for y in 0..73 {
        for x in 0..83 {
            let point = egui::pos2((x as f32 + 0.317) / 83.0, (y as f32 + 0.413) / 73.0);
            let expected = selected
                .layers
                .iter()
                .enumerate()
                .fold(0, |mask, (index, layer)| {
                    mask | if covered(&layer.region, point) {
                        1 << index
                    } else {
                        0
                    }
                });
            let actual = membership_at(&selected, point);
            assert_eq!(actual, expected, "membership at {point:?}");
            counts[actual as usize] += 1;
        }
    }
    assert!(
        counts[1..].iter().all(|&count| count > 100),
        "both exclusive regions and intersection must occur"
    );
    let area: f32 = selected
        .patches
        .iter()
        .map(|patch| polygon_area(&patch.points))
        .sum();
    assert!(
        (area - 1.0).abs() < 1e-4,
        "composited pieces partition the union once, including image edges"
    );
}

#[test]
fn selection_receipts_have_a_fast_path_and_bounded_identity_sensitive_cache() {
    let (mut archive, _) = overlap_fixture();
    let spans = [span(4, 12, 0), span(31, 35, 1)];
    let mut cache = DenseAdmissionCache::default();
    let get = |cache: &mut DenseAdmissionCache,
               archive: &AdmissionArchive,
               domain,
               spans: &[SelectionSpan],
               threshold| {
        cache
            .selection(
                archive,
                domain,
                spans,
                0,
                EXTENT,
                RegionSettings {
                    enabled: true,
                    threshold,
                },
            )
            .unwrap()
    };
    let first = get(&mut cache, &archive, DOMAIN, &spans, 60);
    for _ in 0..20 {
        assert!(Arc::ptr_eq(
            &first,
            &get(&mut cache, &archive, DOMAIN, &spans, 60)
        ));
    }
    assert_eq!((cache.selection_scans, cache.selection_builds), (1, 1));
    archive.ingest(&packet(3, 20, [32, 32], |_, _| true), EXTENT);
    assert!(Arc::ptr_eq(
        &first,
        &get(&mut cache, &archive, DOMAIN, &spans, 60)
    ));
    assert_eq!((cache.selection_scans, cache.selection_builds), (2, 1));
    archive.ingest(&packet(4, 5, [32, 32], |_, _| true), EXTENT);
    assert!(!Arc::ptr_eq(
        &first,
        &get(&mut cache, &archive, DOMAIN, &spans, 60)
    ));
    assert!(!Arc::ptr_eq(
        &first,
        &get(&mut cache, &archive, [4, 8], &spans, 60)
    ));
    assert!(!Arc::ptr_eq(
        &first,
        &get(&mut cache, &archive, DOMAIN, &spans, 85)
    ));
    for id in 2..7 {
        get(&mut cache, &archive, DOMAIN, &[span(4, 12, id)], 60);
    }
    assert_eq!(cache.selections.len(), 4);
    assert!(
        cache
            .selection(
                &archive,
                DOMAIN,
                &spans,
                0,
                EXTENT,
                RegionSettings {
                    enabled: false,
                    threshold: 60
                }
            )
            .is_none()
    );
}

#[test]
fn split_same_color_intervals_neither_stripe_nor_bias_mixed_color() {
    let mut archive = AdmissionArchive::default();
    for frame in [4, 8, 31] {
        archive.ingest(&packet(frame as u64, frame, [16, 12], |_, _| true), EXTENT);
    }
    let split = selection(&archive, &[span(4, 6, 0), span(8, 12, 0)]);
    assert_eq!(
        membership_colors(&split, &members(3)),
        vec![span(4, 6, 0).color()]
    );
    let mixed = selection(&archive, &[span(4, 6, 0), span(8, 12, 0), span(31, 35, 1)]);
    let reversed = selection(&archive, &[span(31, 35, 1), span(8, 12, 0), span(4, 6, 0)]);
    assert_eq!(
        membership_colors(&mixed, &members(7)),
        membership_colors(&reversed, &members(7))
    );
    assert_eq!(membership_colors(&mixed, &members(7)).len(), 2);
    let key = PaintKey {
        image: Rect::from_min_size(Pos2::ZERO, egui::vec2(100.0, 100.0)),
        aperture: Rect::from_min_max(Pos2::ZERO, egui::pos2(1.0, 1.0)),
        color: Color32::WHITE,
        pixels_per_point: 1.0,
        approximate: false,
        options: Default::default(),
    };
    let mesh = selection_mesh(&split, &key);
    assert!(mesh.vertices.iter().any(|vertex| vertex.color.a() == 36));
    assert!(
        !mesh
            .vertices
            .iter()
            .any(|vertex| [46, 100].contains(&vertex.color.a()))
    );
    let mixed_mesh = selection_mesh(&mixed, &key);
    let reversed_mesh = selection_mesh(&reversed, &key);
    let fills = |mesh: &egui::Mesh| {
        mesh.vertices
            .iter()
            .filter(|vertex| vertex.color.a() == 46)
            .map(|vertex| vertex.color)
            .collect::<Vec<_>>()
    };
    assert!(!fills(&mixed_mesh).is_empty());
    assert_eq!(fills(&mixed_mesh), fills(&reversed_mesh));
}

#[test]
fn nine_same_color_fragments_survive_interval_subtraction_without_false_overlap() {
    let mut archive = AdmissionArchive::default();
    let spans: Vec<_> = (0..9).map(|index| span(index * 2, index * 2, 3)).collect();
    for (index, interval) in spans.iter().enumerate() {
        archive.ingest(
            &packet(index as u64 + 1, interval.start, [32, 24], |x, _| {
                if index == 8 { x >= 23 } else { x < 9 }
            }),
            EXTENT,
        );
    }
    let selected = selection(&archive, &spans);
    assert_eq!(selected.layers.len(), 9);
    assert_eq!(selected.colors, vec![spans[0].color()]);
    assert!(!selected.is_empty());
    assert_eq!(membership_at(&selected, egui::pos2(0.1, 0.5)), 1);
    assert_eq!(membership_at(&selected, egui::pos2(0.9, 0.5)), 1);
    assert_eq!(membership_at(&selected, egui::pos2(0.5, 0.5)), 0);
    assert!(
        selected
            .patches
            .iter()
            .all(|patch| patch.membership.inline == 1)
    );
}

#[test]
fn selection_partition_preserves_negative_saddles_between_diagonal_islands() {
    let mut archive = AdmissionArchive::default();
    archive.ingest(
        &packet(1, 0, [24, 24], |x, y| {
            ((3..11).contains(&x) && (3..11).contains(&y))
                || ((11..19).contains(&x) && (11..19).contains(&y))
        }),
        EXTENT,
    );
    archive.ingest(&packet(2, 1, [24, 24], |_, _| true), EXTENT);
    let selected = DenseAdmissionCache::default()
        .selection(
            &archive,
            DOMAIN,
            &[span(0, 0, 0), span(1, 1, 1)],
            0,
            EXTENT,
            RegionSettings {
                enabled: true,
                threshold: 55,
            },
        )
        .unwrap();
    let geometry = SampleGeometry::new(0, archive.metadata(0, 0).unwrap()).unwrap();
    let saddle = geometry
        .at(10 * 24 + 10)
        .unwrap()
        .center
        .lerp(geometry.at(11 * 24 + 11).unwrap().center, 0.5);
    assert_eq!(selected.layers[0].region.islands, 2);
    assert_eq!(
        membership_at(&selected, saddle),
        2,
        "the diagonal gap belongs only to the second range"
    );
    assert!(
        selected
            .patches
            .iter()
            .any(|patch| patch.membership.inline == 3)
    );
}

#[test]
fn independent_range_identities_survive_palette_cycles_and_many_active_groups() {
    let mut archive = AdmissionArchive::default();
    archive.ingest(&packet(1, 0, [16, 12], |x, _| x < 8), EXTENT);
    let cycle = selection(&archive, &[span(0, 0, 0), span(0, 0, 8)]);
    assert_eq!(
        cycle.colors.len(),
        2,
        "independent identities must not merge across the original palette cycle"
    );
    assert!(
        cycle
            .patches
            .iter()
            .all(|patch| patch.membership.contains(0) && patch.membership.contains(1))
    );
    // Presentation changes cannot redefine contributor identity, even if two
    // colors accidentally become identical. This still has two contributors.
    let mut cycle = Arc::try_unwrap(cycle).ok().unwrap();
    cycle.colors[1] = cycle.colors[0];
    assert_eq!(membership_colors(&cycle, &members(3)).len(), 2);
    let spans: Vec<_> = (0..65).map(|id| span(0, 0, id)).collect();
    let many = selection(&archive, &spans);
    assert_eq!(many.layers.len(), 65);
    assert_eq!(many.colors.len(), 65);
    assert!(
        !many.is_empty(),
        "there must be no eight-, sixteen-, or sixty-four-identity cutoff"
    );
    assert!(
        many.patches.len() < 400,
        "coincident boundaries must not multiply zero-area pieces"
    );
    assert!(
        many.patches
            .iter()
            .any(|patch| polygon_contains(&patch.points, egui::pos2(0.2, 0.5)))
    );
    assert!(
        !many
            .patches
            .iter()
            .any(|patch| polygon_contains(&patch.points, egui::pos2(0.8, 0.5)))
    );
    for patch in &many.patches {
        assert_eq!(patch.membership.inline, u64::MAX);
        assert_eq!(patch.membership.overflow, vec![1]);
        assert!(patch.membership.contains(64));
        assert!(!patch.membership.contains(65));
        assert_eq!(membership_colors(&many, &patch.membership).len(), 65);
    }
}

#[test]
fn selection_stripe_triangles_stay_in_actual_intersections_and_projection_is_reused() {
    let (_, selected) = overlap_fixture();
    let context = egui::Context::default();
    let mut cache = DenseSelectionPainter::default();
    let image = Rect::from_min_size(egui::pos2(10.0, 20.0), egui::vec2(320.0, 240.0));
    let aperture = Rect::from_min_max(Pos2::ZERO, egui::pos2(1.0, 1.0));
    let _output = context.run(egui::RawInput::default(), |ctx| {
        egui::CentralPanel::default().show(ctx, |ui| {
            for approximate in [false, true] {
                if approximate {
                    cache.paint_approximate(ui.painter(), &selected, image, aperture);
                } else {
                    cache.paint(ui.painter(), &selected, image, aperture);
                }
                let mesh = &cache.entries.back().unwrap().mesh;
                assert!(mesh.is_valid());
                let mut stripes = 0;
                for triangle in mesh.indices.as_chunks::<3>().0 {
                    let vertices = [triangle[0], triangle[1], triangle[2]]
                        .map(|index| mesh.vertices[index as usize]);
                    if !vertices
                        .iter()
                        .all(|vertex| vertex.color.a() == if approximate { 55 } else { 100 })
                    {
                        continue;
                    }
                    stripes += 1;
                    assert!(
                        vertices
                            .iter()
                            .all(|vertex| image.expand(0.001).contains(vertex.pos))
                    );
                    let center = Pos2::new(
                        vertices.iter().map(|v| v.pos.x).sum::<f32>() / 3.0,
                        vertices.iter().map(|v| v.pos.y).sum::<f32>() / 3.0,
                    );
                    let uv = Pos2::ZERO + (center - image.min) / image.size();
                    assert_eq!(
                        membership_at(&selected, uv),
                        3,
                        "stripes cannot enter either exclusive region or the hole"
                    );
                }
                assert!(
                    stripes > 100,
                    "the overlap must actually produce stripe triangles"
                );
            }
            let first = cache.entries[0].mesh.clone();
            cache.paint(ui.painter(), &selected, image, aperture);
            assert!(Arc::ptr_eq(&first, &cache.entries.back().unwrap().mesh));
            assert_eq!(cache.entries.len(), 2);
            for offset in 1..6 {
                cache.paint(
                    ui.painter(),
                    &selected,
                    image.translate(egui::vec2(offset as f32, 0.0)),
                    aperture,
                );
            }
            assert_eq!(cache.entries.len(), 4);
        });
    });
}

#[test]
fn contained_current_capture_has_no_exclusive_patch_on_shared_boundaries() {
    let extent = [3516, 2344];
    let size = [128, 96];
    let mut archive = AdmissionArchive::default();
    for frame in 4..=12 {
        archive.ingest(
            &packet(frame as u64, frame, size, |x, y| {
                let right = if frame <= 8 { 60 } else { 78 };
                (16..right).contains(&x) && (16..80).contains(&y)
            }),
            extent,
        );
    }
    archive.ingest(
        &packet(20, 20, size, |x, y| {
            (50..112).contains(&x) && (16..80).contains(&y)
        }),
        extent,
    );
    let pins = [span(4, 12, 0)];
    let settings = RegionSettings::default();
    let mut cache = DenseAdmissionCache::default();
    let inside = cache
        .selection_with_current(&archive, DOMAIN, &pins, Some(7), 0, extent, settings)
        .unwrap();
    let pin_field = &inside.layers[0].region.signed;
    let current_field = &inside.layers[1].region.signed;
    assert!(
        pin_field
            .iter()
            .zip(current_field)
            .all(|(pin, current)| pin >= current)
    );
    assert!(
        pin_field
            .iter()
            .zip(current_field)
            .any(|(pin, current)| pin > current)
    );
    assert!(
        pin_field
            .iter()
            .zip(current_field)
            .any(|(pin, current)| pin == current && *pin > 0.0)
    );
    // The previous f32 clipping created a current-only sliver at lattice
    // cell (16, 18), despite these nested fields sharing their left edge.
    // Check every patch, not just representative interior points or pixels.
    let reversed = DenseSelection::from_layers(
        vec![inside.layers[1].clone(), inside.layers[0].clone()],
        0,
        inside.meta,
    )
    .unwrap();
    for (selection, pin_bit, current_bit) in [(&*inside, 0, 1), (&reversed, 1, 0)] {
        let mut shared = 0;
        let mut pin_only = 0;
        for patch in &selection.patches {
            let pin = patch.membership.contains(pin_bit);
            let current = patch.membership.contains(current_bit);
            assert!(
                !current || pin,
                "a contained current cannot acquire an exclusive polygon"
            );
            shared += usize::from(pin && current);
            pin_only += usize::from(pin && !current);
        }
        assert!(
            shared > 100 && pin_only > 100,
            "both real membership classes must be exercised"
        );
    }
    // A different capture extends beyond the pin. Suppressing all exclusive
    // current patches would fail this control, as would dropping its overlap.
    let outside = cache
        .selection_with_current(&archive, DOMAIN, &pins, Some(20), 0, extent, settings)
        .unwrap();
    let mut areas = [0.0_f32; 4];
    for patch in &outside.patches {
        let bits = usize::from(patch.membership.contains(0))
            | (usize::from(patch.membership.contains(1)) << 1);
        areas[bits] += polygon_area(&patch.points);
    }
    assert!(
        areas[1] > 0.05 && areas[2] > 0.05 && areas[3] > 0.05,
        "exclusive and shared regions must survive: {areas:?}"
    );
}

#[test]
fn current_capture_composes_inside_and_outside_pins_without_rebuilding_pinned_unions() {
    let mut archive = AdmissionArchive::default();
    for frame in 4..=12 {
        archive.ingest(
            &packet(frame as u64, frame, [32, 24], |x, _| x < 22),
            EXTENT,
        );
    }
    archive.ingest(&packet(20, 20, [32, 24], |x, _| x >= 12), EXTENT);
    archive.ingest(&packet(21, 21, [32, 24], |_, _| false), EXTENT);
    let pins = [span(4, 12, 2)];
    let settings = RegionSettings::default();
    let mut cache = DenseAdmissionCache::default();
    let pinned = cache
        .selection(&archive, DOMAIN, &pins, 0, EXTENT, settings)
        .unwrap();
    let outside = cache
        .selection_with_current(&archive, DOMAIN, &pins, Some(20), 0, EXTENT, settings)
        .unwrap();
    assert_eq!(outside.layers.len(), 2);
    assert_eq!(outside.layers[0].span, pins[0]);
    assert!(Arc::ptr_eq(
        &outside.layers[0].region,
        &pinned.layers[0].region
    ));
    assert!(outside.layers[1].is_current());
    assert_eq!(outside.layers[1].label(), "CURRENT 021");
    assert_eq!(membership_at(&outside, egui::pos2(0.2, 0.5)), 1);
    assert_eq!(membership_at(&outside, egui::pos2(0.5, 0.5)), 3);
    assert_eq!(membership_at(&outside, egui::pos2(0.9, 0.5)), 2);
    let inside = cache
        .selection_with_current(&archive, DOMAIN, &pins, Some(7), 0, EXTENT, settings)
        .unwrap();
    assert_eq!(
        inside.layers.len(),
        2,
        "a pinned capture still has its own current role"
    );
    assert_eq!(membership_at(&inside, egui::pos2(0.2, 0.5)), 3);
    assert_eq!(membership_at(&inside, egui::pos2(0.9, 0.5)), 0);
    for _ in 0..10 {
        let again = cache
            .selection_with_current(&archive, DOMAIN, &pins, Some(20), 0, EXTENT, settings)
            .unwrap();
        assert!(Arc::ptr_eq(&outside, &again));
        cache.selection_with_current(&archive, DOMAIN, &pins, Some(7), 0, EXTENT, settings);
    }
    assert_eq!(
        (
            cache.selection_builds,
            cache.selection_scans,
            cache.comparison_builds
        ),
        (1, 1, 2)
    );
    let cleared_current = cache
        .selection_with_current(&archive, DOMAIN, &pins, None, 0, EXTENT, settings)
        .unwrap();
    assert!(Arc::ptr_eq(&pinned, &cleared_current));
    let empty_current = cache
        .selection_with_current(&archive, DOMAIN, &pins, Some(21), 0, EXTENT, settings)
        .unwrap();
    assert_eq!(membership_at(&empty_current, egui::pos2(0.5, 0.5)), 1);
    let missing_current = cache
        .selection_with_current(&archive, DOMAIN, &pins, Some(99), 0, EXTENT, settings)
        .unwrap();
    assert!(Arc::ptr_eq(&pinned, &missing_current));
    let current_only = cache
        .selection_with_current(&archive, DOMAIN, &[], Some(20), 0, EXTENT, settings)
        .unwrap();
    assert_eq!(current_only.layers.len(), 1);
    assert!(current_only.layers[0].is_current());
    assert!(
        cache
            .selection_with_current(&archive, DOMAIN, &[], None, 0, EXTENT, settings)
            .is_none()
    );
    // A changed current receipt invalidates only its region/composition. The
    // unrelated current packet cannot make the pinned interval reread samples.
    archive.ingest(&packet(30, 20, [32, 24], |_, _| false), EXTENT);
    let refreshed = cache
        .selection_with_current(&archive, DOMAIN, &pins, Some(20), 0, EXTENT, settings)
        .unwrap();
    assert!(!Arc::ptr_eq(&outside, &refreshed));
    assert!(Arc::ptr_eq(
        &pinned.layers[0].region,
        &refreshed.layers[0].region
    ));
    assert_eq!(cache.selection_builds, 1);
    assert_eq!(membership_at(&refreshed, egui::pos2(0.5, 0.5)), 1);
    for frame in 30..40 {
        archive.ingest(
            &packet(frame as u64 + 1, frame, [32, 24], |x, _| x >= 12),
            EXTENT,
        );
        cache.selection_with_current(&archive, DOMAIN, &pins, Some(frame), 0, EXTENT, settings);
    }
    assert_eq!(cache.comparisons.len(), 8);
    assert_eq!(cache.selection_builds, 1);
}
