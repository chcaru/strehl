use super::*;
use strehl_core::plane::PlaneGeometry;
fn guides() -> Vec<MosaicGuide> {
    let source = PlaneGeometry {
        width: 2048,
        height: 1536,
    };
    let g = PlaneGeometry {
        width: 128,
        height: 96,
    };
    let n = g.pixels();
    (0..2)
        .map(|pass| MosaicGuide {
            pass,
            source_geometry: source,
            geometry: g,
            origin: [0.; 2],
            step: 16,
            intensity: vec![0.; n],
            covered: vec![true; n],
            focus_ordinal: vec![0.; n],
            focus_width: vec![1.; n],
            usable_focus: vec![false; n],
            source_indices: vec![[pass, usize::MAX, usize::MAX, usize::MAX]; n],
            receipt: session_mosaic_geometry::GuideReceipt {
                pass,
                source_geometry: [2048, 1536],
                guide_geometry: [128, 96],
                origin_quad_pixels: [0.; 2],
                step_quad_pixels: 16,
                alignment_sha256: "control".into(),
                focus_evidence_sha256: "control".into(),
                guide_sha256: "control".into(),
                covered_pixels: n,
                usable_focus_pixels: 0,
                source_contributions: Vec::new(),
                reserved_work_bytes: 0,
                construction: "dense geometry operator control".into(),
            },
        })
        .collect()
}
fn row(id: usize, p: [f64; 2], q: [f64; 2], radius: f64) -> math::Row {
    math::Row {
        id: format!("row{id}"),
        a: p,
        b: q,
        bounds: [p, q].map(|p| [p.map(|x| x - radius), p.map(|x| x + radius)]),
        priority: 0.1,
    }
}
fn field(curved: bool) -> Vec<math::Row> {
    let mut rows = Vec::new();
    for y in (128..1408).step_by(128) {
        for x in (128..1920).step_by(128) {
            let p = [x as f64, y as f64];
            let mut q = [p[0] - 45., p[1] + 11.];
            if curved {
                q[0] += 13.5906 * (p[0] / 296.269).sin() * (p[1] / 296.269).sin();
                q[1] += 13.5906 * (p[0] / 296.269).cos() * (p[1] / 296.269).sin();
            }
            rows.push(row(rows.len(), p, q, 12.));
        }
    }
    rows
}
#[test]
fn overlap_component_mass_retains_greedy_count_without_extra_votes() {
    let rows = [
        row(0, [100., 100.], [100., 100.], 8.),
        row(1, [110., 100.], [110., 100.], 8.),
        row(2, [120., 100.], [120., 100.], 8.),
        row(3, [800., 100.], [800., 100.], 8.),
    ];
    let (w, n, receipt) = math::weights(&rows);
    assert_eq!(n, 3);
    assert_eq!(receipt.len(), 2);
    assert_eq!(&w[..3], &[2. / 3.; 3]);
    assert_eq!(w[3], 1.);
    assert!((w.iter().sum::<f64>() - 3.).abs() < 1e-12);
}
#[test]
fn complete_other_view_footprint_purges_training() {
    let mut rows = vec![
        row(0, [100., 100.], [100., 100.], 12.),
        row(1, [600., 100.], [900., 100.], 12.),
    ];
    rows[1].bounds[1] = rows[0].bounds[1];
    let (train, test, purged) = math::split(&rows, 3);
    assert!(train.is_empty());
    assert_eq!(test.len(), 1);
    assert_eq!(purged, vec!["row0"]);
}
#[test]
fn test_value_poison_cannot_change_actual_training_weights_seed_or_mesh() {
    let rows = field(true);
    let mut poisoned = rows.clone();
    for r in &mut poisoned {
        if math::fold(r) == 2 {
            r.b[0] += 700.;
            r.b[1] -= 500.;
            r.priority = 99.;
        }
    }
    let (a, _, purge_a) = math::split(&rows, 2);
    let (b, _, purge_b) = math::split(&poisoned, 2);
    assert_eq!(purge_a, purge_b);
    let a = math::training(&a).unwrap();
    let b = math::training(&b).unwrap();
    assert_eq!(a.weights, b.weights);
    assert_eq!(a.receipt, b.receipt);
    let g = guides();
    let a = math::fit(&a, &g, 256, 0.2).unwrap();
    let b = math::fit(&b, &g, 256, 0.2).unwrap();
    for (x, y) in a.meshes.iter().zip(&b.meshes) {
        assert_eq!(x.vertices, y.vertices);
    }
}
#[test]
fn weighted_similarity_and_native_inverse_placement_recover_translation() {
    let rows = field(false);
    let train = math::training(&rows).unwrap();
    let g = guides();
    let model = math::fit(&train, &g, 256, 0.2).unwrap();
    let errors = math::errors(&model, &rows).unwrap();
    assert!(errors.iter().all(|e| e[0] < 1e-8 && e[1] < 1e-8));
    let mut jump = rows.clone();
    for r in &mut jump {
        r.b[0] += 4.;
        r.b[1] -= 3.;
    }
    assert!(
        math::errors(&model, &jump)
            .unwrap()
            .iter()
            .all(|e| e[0] > 4.99)
    );
}
#[test]
fn missing_fold_is_not_silently_dropped_from_model_selection() {
    let rows = vec![row(0, [100., 100.], [100., 100.], 8.)];
    let (selected, receipts) = math::cv(&rows, &guides());
    assert!(selected.is_none());
    assert_eq!(receipts.len(), 9);
    for r in receipts {
        assert_eq!(r["all_five_folds_valid"], false);
        assert_eq!(r["folds"].as_array().unwrap().len(), 5);
    }
}
#[test]
fn contradictory_source_alternatives_are_retained_as_refused_groups() {
    let mut rows = field(false);
    let mut alternate = rows[0].clone();
    alternate.id = "bad-alternative".into();
    alternate.b[0] += 2.;
    rows.push(alternate);
    let t = math::training(&rows).unwrap();
    assert!(
        t.rows
            .iter()
            .all(|r| r.id != "row0" && r.id != "bad-alternative")
    );
    assert!(
        t.receipt["source_alternative_groups"]
            .as_array()
            .unwrap()
            .iter()
            .any(|g| g["coherent"] == false)
    );
}
