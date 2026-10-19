use super::*;

fn meta(samples: [usize; 2], extent: [usize; 2]) -> AdmissionMeta {
    AdmissionMeta {
        sequence: 1,
        samples,
        extent,
    }
}

#[test]
fn sparse_telemetry_never_turns_into_large_claimed_pixel_ownership() {
    // Only one observation in each quadrant of a1024px image: its pixel
    // cannot legitimately acquire the512px telemetry-bin footprint.
    let fine = SampleGeometry::new(0, meta([2, 2], [1024, 1024])).unwrap();
    let glyph = fine.at(0).unwrap();
    assert_eq!(glyph.center, egui::pos2(256.5 / 1024.0, 256.5 / 1024.0));
    assert_eq!(glyph.cell.width(), 1.0 / 1024.0);
    assert_eq!(glyph.cell.height(), 1.0 / 1024.0);
    assert!(
        glyph.cell.width() < 0.01,
        "fixture must reject the old quadrant fill"
    );
}

#[test]
fn band_spacing_grows_while_telemetry_density_stays_the_same() {
    let input = meta([2, 2], [2048, 2048]);
    let fine = SampleGeometry::new(0, input).unwrap().at(0).unwrap();
    let coarse = SampleGeometry::new(7, input).unwrap();
    assert_eq!(coarse.grid(), [16, 16]);
    assert_eq!(coarse.spacing(), 128);
    assert_eq!(
        coarse.at(0).unwrap().cell.width(),
        fine.cell.width() * 128.0
    );
    // Both observations have the same phase-zero lattice centre. An
    // incorrect half-coefficient phase would shift the coarse centre64px.
    assert_eq!(coarse.at(0).unwrap().center, fine.center);
}

#[test]
fn odd_extents_follow_ceil_halving_and_sample_the_observed_coefficient() {
    //131→66→33; telemetry x=2 of3 selects coefficient27, rooted at108.
    //99→50→25; telemetry y=1 of2 selects coefficient18, rooted at72.
    let geometry = SampleGeometry::new(2, meta([3, 2], [131, 99])).unwrap();
    assert_eq!(geometry.grid(), [33, 25]);
    let glyph = geometry.at(5).unwrap();
    assert_eq!(glyph.center, egui::pos2(108.5 / 131.0, 72.5 / 99.0));
    assert_ne!(glyph.center, egui::pos2(2.5 / 3.0, 1.5 / 2.0));
    assert!(geometry.at(6).is_none());
}

#[test]
fn border_coefficient_cells_stay_inside_the_image_domain() {
    let geometry = SampleGeometry::new(2, meta([3, 3], [9, 9])).unwrap();
    let first = geometry.at(0).unwrap();
    let last = geometry.at(8).unwrap();
    assert_eq!(first.cell.min, Pos2::ZERO);
    assert_eq!(last.cell.max, egui::pos2(1.0, 1.0));
    assert_eq!(first.center, egui::pos2(0.5 / 9.0, 0.5 / 9.0));
    assert_eq!(last.center, egui::pos2(8.5 / 9.0, 8.5 / 9.0));
}

#[test]
fn impossible_sampling_geometry_has_no_spatial_claim() {
    for (level, input) in [
        (0, meta([0, 1], [1024, 1024])),
        (0, meta([2, 2], [0, 1024])),
        (0, meta([129, 2], [1024, 1024])),
        (10, meta([2, 2], [1024, 1024])),
        (64, meta([1, 1], [1024, 1024])),
        (1, meta([1, 1], [usize::MAX, 1024])),
    ] {
        assert!(SampleGeometry::new(level, input).is_none());
    }
}

#[test]
fn nearest_evidence_and_strict_observation_are_distinct() {
    let geometry = SampleGeometry::new(0, meta([2, 2], [1024, 1024])).unwrap();
    let center = geometry.at(0).unwrap().center;
    assert_eq!(geometry.observed_index_at(center), Some(0));
    let unsampled = egui::pos2(0.4, 0.4);
    assert_eq!(geometry.nearest_index_at(unsampled), Some(0));
    assert_eq!(geometry.observed_index_at(unsampled), None);
    assert_eq!(geometry.observed_index_at(egui::pos2(-1.0, 0.4)), None);
    assert_eq!(geometry.nearest_index_at(egui::pos2(f32::NAN, 0.4)), None);
}

#[test]
fn every_actual_coarse_observation_links_back_to_itself_on_odd_extents() {
    // A real positive observation must not vanish when its marker is picked.
    let geometry = SampleGeometry::new(3, meta([3, 3], [33, 33])).unwrap();
    for index in 0..9 {
        let center = geometry.at(index).unwrap().center;
        assert_eq!(geometry.nearest_index_at(center), Some(index));
        assert_eq!(geometry.observed_index_at(center), Some(index));
    }
    // The actual64×47 observer grid on66×49 coefficients exposes the old
    // uniform-bin mismatch; this sample is22.5/131, not11.5/64.
    let geometry = SampleGeometry::new(1, meta([64, 47], [131, 98])).unwrap();
    let center = geometry.at(11).unwrap().center;
    assert_ne!((center.x * 64.0) as usize, 11);
    assert_eq!(geometry.nearest_index_at(center), Some(11));
}

#[test]
fn painter_preserves_photo_pixels_between_sparse_observations() {
    let context = egui::Context::default();
    let output = context.run(egui::RawInput::default(), |ctx| {
        egui::CentralPanel::default().show(ctx, |ui| {
            let glyph = SampleGeometry::new(0, meta([2, 2], [1024, 1024]))
                .unwrap()
                .at(0)
                .unwrap();
            let image = Rect::from_min_size(egui::pos2(10.0, 10.0), Vec2::splat(512.0));
            paint_glyph(
                ui.painter(),
                image,
                Rect::from_min_max(Pos2::ZERO, egui::pos2(1.0, 1.0)),
                glyph,
                level_color(0),
                true,
            );
        });
    });
    let drawn = output
        .shapes
        .iter()
        .filter(|shape| {
            matches!(&shape.shape,
        egui::Shape::Circle(circle) if (circle.radius - 1.05).abs() < 0.01)
        })
        .count();
    assert_eq!(
        drawn, 1,
        "an overview coefficient paints one marker, never a filled telemetry rectangle"
    );
}
