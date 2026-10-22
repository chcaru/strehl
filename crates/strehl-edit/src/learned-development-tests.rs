use super::*;
use crate::learned_asset::{GainDescriptor, ProfileOrigin, TableDescriptor, TableEncoding};
use crate::learned_profile::IDENTITY_MATRIX;
use crate::learned_scene_asset::{FrozenSceneData, FrozenSceneDescriptor};
use crate::{
    Adjustments, DisplayBaseline, RegionAdjustment, RegionShape, SourceRange, SpatialTreatment,
};
use std::sync::atomic::AtomicUsize;

const SOURCE: AssetDigest = [73; 32];

fn image(origin: ImageOrigin, baseline: bool) -> Arc<LinearImage> {
    Arc::new(LinearImage {
        width: 9,
        height: 7,
        pixels: (0..63)
            .flat_map(|i| {
                [
                    (i % 9) as f32 * 0.12 - 0.08,
                    (i / 9) as f32 * 0.11 + 0.03,
                    (i % 5) as f32 * 0.18,
                ]
            })
            .collect(),
        origin,
        baseline: baseline.then_some(DisplayBaseline {
            black: 0.01,
            white: 0.73,
            contrast: 0.37,
            exposure_gain: 0.83,
        }),
        baked_recipe: None,
    })
}

fn recipe() -> DevelopmentRecipe {
    DevelopmentRecipe {
        global: Adjustments {
            exposure: 0.4,
            contrast: 13.,
            saturation: 9.,
            temperature: 7.,
            ..Default::default()
        },
        regions: vec![RegionAdjustment {
            id: "left".into(),
            name: "Feathered edit".into(),
            note: String::new(),
            shape: RegionShape::Ellipse {
                center: [0.35, 0.6],
                radius: [0.3, 0.35],
            },
            feather: 0.7,
            enabled: true,
            adjustments: Adjustments {
                exposure: -0.6,
                temperature: -17.,
                shadows: 11.,
                ..Default::default()
            },
            source_range: None,
        }],
        spatial: vec![SpatialTreatment {
            version: 1,
            target_region: Some("left".into()),
            parameters: Default::default(),
            amount: 0.72,
            bounds: [[0., 0.], [1., 1.]],
            width: 2,
            height: 2,
            levels: 3,
            log_min: -8.,
            log_max: 2.,
            tone_ev: vec![
                -0.1, 0.05, 0.2, 0.2, 0.1, -0.1, 0.3, 0., -0.1, 0.2, 0.2, 0.1,
            ],
            color_gain: vec![1., 1.1, 1.02, 1.15],
            delivery_ceiling: 2.,
            centering_ev: 0.,
        }],
        ..Default::default()
    }
}

fn asset() -> Arc<FrozenSceneAsset> {
    let table = (0..3)
        .flat_map(|c| {
            (0..3).flat_map(move |r| {
                (0..3).flat_map(move |g| {
                    (0..3).map(move |b| {
                        let p = [r as f32 / 2., g as f32 / 2., b as f32 / 2.];
                        p[c] * 0.68 + p[(c + 1) % 3] * 0.13
                    })
                })
            })
        })
        .collect();
    Arc::new(
        FrozenSceneAsset::freeze(
            FrozenSceneDescriptor {
                identities: AssetIdentities {
                    contract_id: SCENE_SDR_LINEAR_V1.into(),
                    contract_sha256: [11; 32],
                    model_sha256: [23; 32],
                    input_sha256: [37; 32],
                    source_sha256: SOURCE,
                },
                origin: ProfileOrigin {
                    full_size: [9, 7],
                    region: None,
                },
                gain: GainDescriptor {
                    dimensions: [3, 2, 2],
                    origin_yx: [0.05, -0.1],
                    spacing_yx: [0.8, 0.9],
                    input_weights: [0.23, 0.57, 0.2, 0., 0.],
                    gamma: 0.81,
                },
                table: TableDescriptor {
                    size: 3,
                    source_to_table: IDENTITY_MATRIX,
                    encoding: TableEncoding::Linear,
                    gamut_extension: false,
                },
                linear_709_to_working: [[1., 0.1, 0.], [0., 1., 0.], [0., 0., 1.]],
                working_to_linear_709: [[1., -0.1, 0.], [0., 1., 0.], [0., 0., 1.]],
                gain_query_scale: 1.7,
                exposure_scale: 0.91,
            },
            FrozenSceneData {
                gain: vec![0.4, 1.3, 0.8, 1.7, 0.8, 0.7, 1.4, 0.6, 1.2, 1.1, 0.7, 1.5],
                table,
            },
        )
        .unwrap(),
    )
}

fn reference(a: &FrozenSceneAsset, amount: f32) -> SceneTreatmentReference {
    let d = &a.descriptor().identities;
    SceneTreatmentReference {
        key: AssetKey::from_digest(a.digest()),
        contract_sha256: d.contract_sha256,
        model_sha256: d.model_sha256,
        input_sha256: d.input_sha256,
        enabled: true,
        amount,
    }
}
fn prepare(
    image: Arc<LinearImage>,
    recipe: DevelopmentRecipe,
    amount: f32,
) -> PreparedSdrDevelopment {
    let a = asset();
    let r = reference(&a, amount);
    PreparedSdrDevelopment::prepare(
        image,
        SOURCE,
        recipe,
        Some(r),
        &AtomicBool::new(false),
        |_, _, _| Ok(a),
    )
    .unwrap()
}
fn full() -> DisplayRegionRequest {
    DisplayRegionRequest {
        min: [0, 0],
        max: [9, 7],
        stride: 1,
    }
}
fn bits(v: &[f32]) -> Vec<u32> {
    v.iter().map(|v| v.to_bits()).collect()
}

#[test]
fn bypass_reuses_existing_nonzero_edit_paths_for_absent_disabled_and_zero_assets() {
    let calls = AtomicUsize::new(0);
    let a = asset();
    let edits = recipe();
    edits.validate().unwrap();
    assert!(
        edits.global != Adjustments::default()
            && !edits.regions.is_empty()
            && !edits.spatial.is_empty()
    );
    for origin in [ImageOrigin::SceneLinear, ImageOrigin::DisplayReferred] {
        for baseline in [false, true] {
            let image = image(origin, baseline);
            let disabled = SceneTreatmentReference {
                enabled: false,
                ..reference(&a, 0.8)
            };
            for treatment in [None, Some(disabled), Some(reference(&a, 0.))] {
                let snapshot = PreparedSdrDevelopment::prepare(
                    image.clone(),
                    SOURCE,
                    edits.clone(),
                    treatment,
                    &AtomicBool::new(false),
                    |_, _, _| {
                        calls.fetch_add(1, Ordering::Relaxed);
                        anyhow::bail!("missing asset")
                    },
                )
                .unwrap();
                assert!(
                    !snapshot.is_active()
                        && snapshot.asset.is_none()
                        && snapshot.prepared.is_none()
                );
                for i in 0..63 {
                    assert_eq!(
                        snapshot.display_pixel(i).unwrap().map(f32::to_bits),
                        image.display_pixel(i, &edits).map(f32::to_bits)
                    );
                    assert_eq!(
                        snapshot.developed_pixel(i).unwrap().map(f32::to_bits),
                        image.developed_pixel(i, &edits).map(f32::to_bits)
                    );
                }
                let mut native8 = vec![0; 189];
                let mut native16 = vec![0; 189];
                let cancel = AtomicBool::new(false);
                snapshot
                    .render_region_sdr8(full(), &mut native8, &cancel)
                    .unwrap();
                snapshot
                    .render_region_sdr16(full(), &mut native16, &cancel)
                    .unwrap();
                assert_eq!(native8, image.render_sdr8(&edits).unwrap());
                assert_eq!(native16, image.render_sdr16(&edits).unwrap());
                for request in [
                    full(),
                    DisplayRegionRequest {
                        min: [1, 2],
                        max: [8, 7],
                        stride: 2,
                    },
                    DisplayRegionRequest {
                        min: [0, 0],
                        max: [9, 7],
                        stride: 4,
                    },
                ] {
                    let old = image
                        .render_display_region(&edits, request, &cancel)
                        .unwrap();
                    let mut out = vec![0; old.rgb.len()];
                    let mut linear = vec![0.; old.rgb.len()];
                    snapshot
                        .render_region_sdr8(request, &mut out, &cancel)
                        .unwrap();
                    snapshot
                        .render_region_developed(request, &mut linear, &cancel)
                        .unwrap();
                    assert_eq!(out, old.rgb);
                    let old_linear: Vec<_> = old
                        .rgba_linear
                        .as_chunks::<4>()
                        .0
                        .iter()
                        .flat_map(|p| [p[0], p[1], p[2]])
                        .collect();
                    assert_eq!(bits(&linear), bits(&old_linear));
                }
            }
        }
    }
    assert_eq!(calls.load(Ordering::Relaxed), 0);
}

#[test]
fn amount_endpoints_and_linear_mix_keep_complete_branches_and_edit_order() {
    let image = image(ImageOrigin::SceneLinear, true);
    let edits = recipe();
    let snapshot = prepare(image.clone(), edits.clone(), 1.);
    let a = asset();
    let middle = snapshot.with_amount(0.37).unwrap();
    let zero = snapshot.with_amount(0.).unwrap();
    let mut saw_order = false;
    let mut saw_baseline = false;
    let mut saw_encoded_difference = false;
    for i in 0..63 {
        let (raw, uv) = snapshot.source_pixel(i).unwrap();
        let scene = a.prepared().develop_pixel(raw, uv).unwrap();
        let candidate = edits.apply_pixel(scene, uv).map(|v| v.clamp(0., 1.));
        let encoded = candidate.map(crate::image::srgb_encode);
        assert_eq!(
            snapshot.display_pixel(i).unwrap().map(f32::to_bits),
            encoded.map(f32::to_bits)
        );
        assert_eq!(
            zero.display_pixel(i).unwrap().map(f32::to_bits),
            image.display_pixel(i, &edits).map(f32::to_bits)
        );
        let baseline = image.display_pixel(i, &edits);
        let linear = baseline.map(crate::color::decode_srgb);
        let mixed = std::array::from_fn(|c| linear[c] * (1. - 0.37) + candidate[c] * 0.37)
            .map(crate::image::srgb_encode);
        assert_eq!(
            middle.display_pixel(i).unwrap().map(f32::to_bits),
            mixed.map(f32::to_bits)
        );
        saw_order |= a
            .prepared()
            .develop_pixel(edits.apply_pixel(raw, uv), uv)
            .unwrap()
            .map(crate::image::srgb_encode)
            != encoded;
        saw_baseline |= image.display_sample(scene, uv, &edits) != encoded;
        saw_encoded_difference |=
            std::array::from_fn::<_, 3, _>(|c| baseline[c] * (1. - 0.37) + encoded[c] * 0.37)
                != mixed;
    }
    assert!(saw_order && saw_baseline && saw_encoded_difference);
    let mut linear = vec![0.; 189];
    snapshot
        .render_region_sdr_linear(full(), &mut linear, &AtomicBool::new(false))
        .unwrap();
    for i in 0..63 {
        let (raw, uv) = snapshot.source_pixel(i).unwrap();
        let expected = edits
            .apply_pixel(a.prepared().develop_pixel(raw, uv).unwrap(), uv)
            .map(|v| v.clamp(0., 1.));
        assert_eq!(bits(&linear[i * 3..i * 3 + 3]), expected.map(f32::to_bits));
    }
}

#[test]
fn native_crops_preserve_full_image_gain_and_manual_region_coordinates() {
    let snapshot = prepare(image(ImageOrigin::SceneLinear, true), recipe(), 0.73);
    let cancel = AtomicBool::new(false);
    let mut all = vec![0; 189];
    snapshot
        .render_region_sdr16(full(), &mut all, &cancel)
        .unwrap();
    let region = DisplayRegionRequest {
        min: [2, 3],
        max: [7, 6],
        stride: 1,
    };
    let mut crop = vec![0; 5 * 3 * 3];
    snapshot
        .render_region_sdr16(region, &mut crop, &cancel)
        .unwrap();
    let mut wrong_differs = false;
    for y in 0..3 {
        for x in 0..5 {
            let at = ((y + 3) * 9 + x + 2) * 3;
            let actual = (y * 5 + x) * 3;
            assert_eq!(&crop[actual..actual + 3], &all[at..at + 3]);
            let (raw, _) = snapshot.source_pixel(at / 3).unwrap();
            let wrong = snapshot
                .display_sample(raw, [(x as f32 + 0.5) / 5., (y as f32 + 0.5) / 3.])
                .unwrap()
                .map(|v| (v * 65535. + 0.5) as u16);
            wrong_differs |= wrong != crop[actual..actual + 3];
        }
    }
    assert!(
        wrong_differs,
        "fixture did not expose crop-local UV rebasing"
    );
}

#[test]
fn overview_uses_full_footprint_center_and_known_area_average() {
    let snapshot = prepare(image(ImageOrigin::SceneLinear, false), recipe(), 1.);
    let request = DisplayRegionRequest {
        min: [1, 1],
        max: [8, 7],
        stride: 4,
    };
    assert_eq!(snapshot.region_size(request).unwrap(), [2, 2]);
    let mut output = vec![0.; 12];
    snapshot
        .render_region_sdr_linear(request, &mut output, &AtomicBool::new(false))
        .unwrap();
    let mut saw_nonlinear_approximation = false;
    for y in 0..2 {
        for x in 0..2 {
            let (x0, x1) = (1 + x * 7 / 2, 1 + (x + 1) * 7 / 2);
            let (y0, y1) = (1 + y * 6 / 2, 1 + (y + 1) * 6 / 2);
            let mut raw = [0.; 3];
            let mut developed = [0.; 3];
            for sy in y0..y1 {
                for sx in x0..x1 {
                    let (p, uv) = snapshot.source_pixel(sy * 9 + sx).unwrap();
                    let d = snapshot.candidate_sample(p, uv).unwrap();
                    for c in 0..3 {
                        raw[c] += p[c];
                        developed[c] += d[c];
                    }
                }
            }
            let n = ((x1 - x0) * (y1 - y0)) as f32;
            raw = raw.map(|v| v / n);
            developed = developed.map(|v| v / n);
            let expected = snapshot
                .candidate_sample(
                    raw,
                    [(x0 + x1) as f32 * 0.5 / 9., (y0 + y1) as f32 * 0.5 / 7.],
                )
                .unwrap();
            let at = (y * 2 + x) * 3;
            assert_eq!(bits(&output[at..at + 3]), expected.map(f32::to_bits));
            saw_nonlinear_approximation |= expected
                .iter()
                .zip(developed)
                .any(|(a, b)| (*a - b).abs() > 1e-5);
        }
    }
    assert!(saw_nonlinear_approximation);
}

#[test]
fn resolution_is_once_and_slider_changes_share_every_immutable_field() {
    let a = asset();
    let calls = AtomicUsize::new(0);
    let snapshot = PreparedSdrDevelopment::prepare(
        image(ImageOrigin::SceneLinear, true),
        SOURCE,
        recipe(),
        Some(reference(&a, 0.7)),
        &AtomicBool::new(false),
        |_, _, _| {
            calls.fetch_add(1, Ordering::Relaxed);
            Ok(a.clone())
        },
    )
    .unwrap();
    let clone = snapshot.clone();
    assert_eq!(snapshot.id(), clone.id());
    for amount in [0., 1., 0.2, 0., 0.8] {
        let changed = snapshot.with_amount(amount).unwrap();
        assert_ne!(snapshot.id(), changed.id());
        assert!(Arc::ptr_eq(&snapshot.image, &changed.image));
        assert!(Arc::ptr_eq(&snapshot.recipe, &changed.recipe));
        assert!(Arc::ptr_eq(
            snapshot.asset.as_ref().unwrap(),
            changed.asset.as_ref().unwrap()
        ));
        assert!(Arc::ptr_eq(
            snapshot.prepared.as_ref().unwrap(),
            changed.prepared.as_ref().unwrap()
        ));
        changed.display_pixel(21).unwrap();
    }
    let zero = snapshot.with_amount(0.).unwrap();
    assert!(zero.with_amount(1.).unwrap().is_active());
    assert_eq!(calls.load(Ordering::Relaxed), 1);
    let initial_zero = PreparedSdrDevelopment::prepare(
        snapshot.image.clone(),
        SOURCE,
        recipe(),
        Some(reference(&a, 0.)),
        &AtomicBool::new(false),
        |_, _, _| anyhow::bail!("missing"),
    )
    .unwrap();
    assert!(initial_zero.with_amount(0.1).is_err());
    assert!(initial_zero.with_amount(0.).is_ok());
}

#[test]
fn active_missing_corrupt_wrong_source_key_and_other_identities_fail_before_jobs() {
    let image = image(ImageOrigin::SceneLinear, false);
    let a = asset();
    let r = reference(&a, 1.);
    let cancel = AtomicBool::new(false);
    PreparedSdrDevelopment::prepare(
        image.clone(),
        SOURCE,
        recipe(),
        Some(r.clone()),
        &cancel,
        |_, _, _| Ok(a.clone()),
    )
    .unwrap();
    for message in ["missing asset", "corrupt asset"] {
        assert!(
            PreparedSdrDevelopment::prepare(
                image.clone(),
                SOURCE,
                recipe(),
                Some(r.clone()),
                &cancel,
                |_, _, _| anyhow::bail!("{message}")
            )
            .is_err()
        );
    }
    for choice in 0..6 {
        let mut changed = r.clone();
        let mut source = SOURCE;
        match choice {
            0 => source[0] ^= 1,
            1 => changed.key = AssetKey::from_digest([0; 32]),
            2 => changed.contract_sha256[0] ^= 1,
            3 => changed.model_sha256[0] ^= 1,
            4 => changed.input_sha256[0] ^= 1,
            _ => {}
        };
        let input = if choice == 5 {
            let mut i = (*image).clone();
            i.width = 7;
            i.height = 9;
            Arc::new(i)
        } else {
            image.clone()
        };
        assert!(
            PreparedSdrDevelopment::prepare(
                input,
                source,
                recipe(),
                Some(changed),
                &cancel,
                |_, expected, _| {
                    assert_eq!(expected.identities.source_sha256, source);
                    Ok(a.clone())
                }
            )
            .is_err(),
            "accepted stale identity {choice}"
        );
    }
}

#[test]
fn snapshot_rejects_reloaded_image_instance_and_retains_recipe_revision() {
    let image = image(ImageOrigin::SceneLinear, false);
    let mut edits = recipe();
    let snapshot = prepare(image.clone(), edits.clone(), 1.);
    assert!(snapshot.matches_source(&image, SOURCE));
    assert!(!snapshot.matches_source(&Arc::new((*image).clone()), SOURCE));
    assert!(!snapshot.matches_source(&image, [0; 32]));
    edits.global.exposure += 1.;
    assert_ne!(snapshot.recipe(), &edits);
    let next = prepare(image, edits, 1.);
    assert_ne!(next.id(), snapshot.id());
    assert_ne!(
        next.display_pixel(32).unwrap(),
        snapshot.display_pixel(32).unwrap()
    );
}

#[test]
fn active_sdr_rejects_hdr_and_display_referred_sources_before_output() {
    let snapshot = prepare(image(ImageOrigin::SceneLinear, true), recipe(), 1.);
    assert!(snapshot.developed_pixel(0).is_err());
    let mut out = vec![123.; 189];
    assert!(
        snapshot
            .render_region_developed(full(), &mut out, &AtomicBool::new(false))
            .is_err()
    );
    assert!(out.iter().all(|v| *v == 123.));
    let a = asset();
    assert!(
        PreparedSdrDevelopment::prepare(
            image(ImageOrigin::DisplayReferred, false),
            SOURCE,
            recipe(),
            Some(reference(&a, 1.)),
            &AtomicBool::new(false),
            |_, _, _| panic!("must reject before resolution")
        )
        .is_err()
    );
}

#[test]
fn pending_source_repairs_preserve_bypass_preview_but_refuse_active_scene() {
    let image = image(ImageOrigin::SceneLinear, true);
    let mut edits = recipe();
    edits.regions[0].source_range = Some(SourceRange { first: 2, last: 4 });
    let a = asset();
    let cancel = AtomicBool::new(false);
    for reference in [
        None,
        Some(reference(&a, 0.)),
        Some(SceneTreatmentReference {
            enabled: false,
            ..reference(&a, 0.7)
        }),
    ] {
        let snapshot = PreparedSdrDevelopment::prepare(
            image.clone(),
            SOURCE,
            edits.clone(),
            reference,
            &cancel,
            |_, _, _| panic!("bypass resolved"),
        )
        .unwrap();
        assert_eq!(
            snapshot.display_pixel(26).unwrap(),
            image.display_pixel(26, &edits)
        );
    }
    assert!(
        PreparedSdrDevelopment::prepare(
            image,
            SOURCE,
            edits,
            Some(reference(&a, 1.)),
            &cancel,
            |_, _, _| panic!("unbaked source resolved")
        )
        .is_err()
    );
}

#[test]
fn cancellation_bounds_and_invalid_amounts_refuse_without_partial_preflight_writes() {
    let snapshot = prepare(image(ImageOrigin::SceneLinear, true), recipe(), 0.8);
    let mut out = vec![239; 189];
    assert!(
        snapshot
            .render_region_sdr8(full(), &mut out, &AtomicBool::new(true))
            .is_err()
    );
    assert!(out.iter().all(|v| *v == 239));
    for region in [
        DisplayRegionRequest {
            stride: 0,
            ..full()
        },
        DisplayRegionRequest {
            stride: 3,
            ..full()
        },
        DisplayRegionRequest {
            min: [8, 0],
            max: [7, 7],
            stride: 1,
        },
        DisplayRegionRequest {
            max: [10, 7],
            ..full()
        },
    ] {
        assert!(
            snapshot
                .render_region_sdr8(region, &mut out, &AtomicBool::new(false))
                .is_err()
        );
        assert!(out.iter().all(|v| *v == 239));
    }
    assert!(
        snapshot
            .render_region_sdr8(full(), &mut out[..188], &AtomicBool::new(false))
            .is_err()
    );
    assert!(snapshot.display_pixel(63).is_err());
    for amount in [f32::NAN, f32::INFINITY, -0.1, 1.01] {
        assert!(snapshot.with_amount(amount).is_err());
    }
    let a = asset();
    assert!(
        PreparedSdrDevelopment::prepare(
            snapshot.image.clone(),
            SOURCE,
            recipe(),
            Some(reference(&a, 1.)),
            &AtomicBool::new(true),
            |_, _, _| panic!("cancelled resolution")
        )
        .is_err()
    );
    let cancel = AtomicBool::new(false);
    assert!(
        PreparedSdrDevelopment::prepare(
            snapshot.image.clone(),
            SOURCE,
            recipe(),
            Some(reference(&a, 1.)),
            &cancel,
            |_, _, c| {
                c.store(true, Ordering::Relaxed);
                Ok(a)
            }
        )
        .is_err()
    );
}
