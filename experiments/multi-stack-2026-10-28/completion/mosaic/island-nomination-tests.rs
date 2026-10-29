use super::*;
use session_mosaic_geometry::GuideReceipt;
use strehl_core::{
    align::{Cx, Resampler},
    plane::PlaneGeometry,
    warpmap::{FrameWarp, Provenance, StackIdentity},
};

pub(crate) fn guides(size: [usize; 2]) -> [MosaicGuide; 2] {
    [0, 1].map(|pass| {
        let geometry = PlaneGeometry {
            width: size[0].div_ceil(4),
            height: size[1].div_ceil(4),
        };
        let n = geometry.pixels();
        MosaicGuide {
            pass,
            source_geometry: PlaneGeometry {
                width: size[0],
                height: size[1],
            },
            geometry,
            origin: [1.5; 2],
            step: 4,
            intensity: vec![1.; n],
            covered: vec![false; n],
            focus_ordinal: vec![2.; n],
            focus_width: vec![1.; n],
            usable_focus: vec![false; n],
            source_indices: vec![[pass, usize::MAX, usize::MAX, usize::MAX]; n],
            receipt: GuideReceipt {
                pass,
                source_geometry: size,
                guide_geometry: [geometry.width, geometry.height],
                origin_quad_pixels: [1.5; 2],
                step_quad_pixels: 4,
                alignment_sha256: "control".into(),
                focus_evidence_sha256: "control".into(),
                guide_sha256: "control".into(),
                covered_pixels: 0,
                usable_focus_pixels: 0,
                source_contributions: Vec::new(),
                reserved_work_bytes: 0,
                construction: "selector control".into(),
            },
        }
    })
}
fn mark(guide: &mut MosaicGuide, point: [f64; 2]) {
    let (_, _, index) = coordinate(guide, point).unwrap();
    guide.covered[index] = true;
    guide.usable_focus[index] = true;
}
fn both(guides: &mut [MosaicGuide; 2], point: [f64; 2]) {
    for guide in guides {
        mark(guide, point);
    }
}
pub(crate) fn maps(guides: &[MosaicGuide; 2]) -> [WarpMap; 2] {
    [0, 1].map(|pass| {
        WarpMap::new(
            Provenance {
                stack: StackIdentity::from_entries("selector", &[("a", 1), ("b", 1)]),
                strategy: "control".into(),
                heldout_px: None,
                cycle_floor_px: None,
                reference: pass,
                note: String::new(),
            },
            guides[pass].source_geometry,
            Resampler::Bilinear,
            vec![FrameWarp::Placed(Similarity::IDENTITY); 2],
        )
    })
}
fn config() -> MosaicGeometryConfig {
    MosaicGeometryConfig {
        native_tile: 16,
        native_search_radius: 8,
        native_lowpass: false,
        coarse_residual_guide_pixels: 2.,
        mesh_cell_quad_pixels: 500,
        ..MosaicGeometryConfig::default()
    }
}
fn run(
    guides: &[MosaicGuide; 2],
    ancestors: &[AncestorFootprint],
) -> (Vec<IslandProposal>, Vec<Value>, Vec<Value>) {
    let grids = [0, 1].map(|pass| AnchorGrid {
        source_size_quad: [
            guides[pass].source_geometry.width,
            guides[pass].source_geometry.height,
        ],
        guide_origin_quad: [1.5; 2],
        guide_step_quad: 4,
        initial_block_guide_pixels: 128,
        global_source_range: [pass, pass + 1],
    });
    propose(
        guides,
        &maps(guides),
        &config(),
        [1., 0., 0., 0.],
        Policy::FocusCoverage,
        Planning {
            upstream: &"a".repeat(64),
            evidence: &"b".repeat(64),
            grids: &grids,
            ancestors,
        },
    )
    .unwrap()
}

#[test]
fn distance_ties_and_nearest_moving_mask_are_explicit_and_signal_independent() {
    let mut g = guides([1024, 1024]);
    let anchor = [145.5, 145.5];
    let expected = [
        [145.5, 141.5],
        [141.5, 145.5],
        [149.5, 145.5],
        [145.5, 149.5],
    ];
    let seed = Similarity {
        a: Cx::new(1., 0.),
        b: Cx::new(2.1, 0.),
    };
    for p in expected {
        mark(&mut g[0], p);
        let q = predict(seed, p, &g[0]);
        mark(&mut g[1], q);
    }
    assert_eq!(eligible(&g, seed, anchor), expected);
    // Query145.5+2.1 rounds to149.5; the neighboring145.5 mask is not interchangeable.
    let (_, _, queried) = coordinate(&g[1], [147.6, 141.5]).unwrap();
    assert_eq!(
        g[1].full_point([(queried % 256) as f64, (queried / 256) as f64]),
        [149.5, 141.5]
    );
    g[1].usable_focus[queried] = false;
    mark(&mut g[1], [145.5, 141.5]);
    let without = eligible(&g, seed, anchor);
    assert_eq!(without, expected[1..]);
    for guide in &mut g {
        guide.intensity.fill(f32::NAN);
        guide.focus_ordinal.fill(999.);
        guide.focus_width.fill(17.);
    }
    assert_eq!(
        eligible(&g, seed, anchor),
        without,
        "selection must not read intensity or focus magnitude"
    );
}

#[test]
fn actual_selection_skips_ancestor_intersection_then_freezes_next() {
    let mut g = guides([1024, 1024]);
    both(&mut g, [145.5, 145.5]);
    both(&mut g, [149.5, 145.5]);
    let ancestors = [AncestorFootprint {
        pass: 0,
        source: 0,
        measurement_id: "refused-initial-query".into(),
        bounds: Rectangle::around([110.5, 145.5], 0.).unwrap(),
    }];
    let (selected, _, receipts) = run(&g, &ancestors);
    assert_eq!(selected.len(), 1);
    assert_eq!(selected[0].reference_center_quad, [149.5, 145.5]);
    assert_eq!(receipts[0]["selected"]["rank"], 1);
    assert_eq!(
        receipts[0]["geometric_refusals"].as_array().unwrap().len(),
        1
    );
    assert!(
        receipts[0]["geometric_refusals"][0]["reason"]
            .as_str()
            .unwrap()
            .contains("initial FIT attempt")
    );
    assert_eq!(receipts[0]["native_retry_policy"], "none");
}

#[test]
fn actual_selection_excludes_prior_island_before_next_ranked_candidate() {
    let mut g = guides([1024, 1024]);
    both(&mut g, [241.5, 145.5]);
    both(&mut g, [305.5, 145.5]);
    both(&mut g, [433.5, 145.5]);
    let (selected, _, receipts) = run(&g, &[]);
    assert_eq!(selected.len(), 2);
    assert_eq!(selected[0].reference_center_quad, [241.5, 145.5]);
    assert_eq!(selected[1].reference_center_quad, [433.5, 145.5]);
    assert_eq!(receipts[1]["selected"]["rank"], 1);
    assert!(
        receipts[1]["geometric_refusals"][0]["reason"]
            .as_str()
            .unwrap()
            .contains("distinct physical support")
    );
}

#[test]
fn selected_cell_comes_from_actual_point_and_unavailable_anchors_are_retained() {
    let mut g = guides([1024, 1024]);
    both(&mut g, [325.5, 145.5]);
    let (selected, absent, receipts) = run(&g, &[]);
    assert_eq!(selected.len(), 1);
    assert_eq!(selected[0].cell, [0, 0]);
    assert_eq!(receipts[1]["nominal_mesh_cell"], json!([1, 0]));
    assert_eq!(
        receipts[1]["selected"]["witness"]["physical_mesh_cell"],
        json!([0, 0])
    );
    assert_eq!(absent.len() + selected.len(), receipts.len());
    let (selected, absent, receipts) = run(&guides([3516, 2344]), &[]);
    assert!(selected.is_empty());
    assert_eq!(receipts.len(), 36);
    assert_eq!(absent.len(), 36);
    assert!(
        receipts.iter().all(|r| r["selected"].is_null()
            && r["ranked_candidates_quad"].as_array().unwrap().is_empty())
    );
}
