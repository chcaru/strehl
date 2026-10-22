use super::*;
use std::sync::atomic::AtomicBool;
use strehl_edit::{DisplayRegionRequest, ImageOrigin};

fn fixture() -> (Arc<LinearImage>, DevelopmentRecipe) {
    let image = Arc::new(LinearImage {
        width: 97,
        height: 65,
        pixels: (0..97 * 65)
            .flat_map(|i| {
                [
                    0.03 + (i % 97) as f32 / 120.,
                    0.04 + (i / 97) as f32 / 100.,
                    0.1 + (i % 19) as f32 / 25.,
                ]
            })
            .collect(),
        origin: ImageOrigin::SceneLinear,
        baseline: Some(strehl_edit::DisplayBaseline {
            black: 0.01,
            white: 0.9,
            exposure_gain: 0.8,
            contrast: 0.15,
        }),
        baked_recipe: None,
    });
    let mut recipe = DevelopmentRecipe::default();
    recipe.global.exposure = -0.3;
    recipe.global.contrast = 17.;
    recipe.global.saturation = 9.;
    recipe.regions.push(strehl_edit::RegionAdjustment {
        id: "off-center".into(),
        name: "off-center".into(),
        note: String::new(),
        shape: strehl_edit::RegionShape::Ellipse {
            center: [0.3, 0.6],
            radius: [0.25, 0.3],
        },
        feather: 0.6,
        enabled: true,
        adjustments: strehl_edit::Adjustments {
            exposure: 0.7,
            temperature: -10.,
            ..Default::default()
        },
        source_range: None,
    });
    (image, recipe)
}

#[test]
fn baseline_job_keeps_coarse_native_hdr_thumbnail_and_export_pixels_exact() {
    let (image, recipe) = fixture();
    let overview = Arc::new(image.preview(31));
    let job = DevelopmentJob::new(image.clone(), overview.clone(), recipe.clone());
    let cancel = AtomicBool::new(false);
    for coarse in [false, true] {
        let source = if coarse { &overview } else { &image };
        for hdr in [false, true] {
            let request = DisplayRegionRequest {
                min: [3, 2],
                max: [source.width - 2, source.height - 1],
                stride: 2,
            };
            let expected = source
                .render_display_region_mode(&recipe, request, &cancel, hdr)
                .unwrap();
            let actual =
                crate::photo_viewport::prepare_job(&job, coarse, request, &cancel, None, hdr, true)
                    .unwrap();
            assert_eq!(
                actual.sdr.unwrap(),
                eframe::egui::ColorImage::from_rgb(
                    expected.size.map(|n| n as usize),
                    &expected.rgb
                )
            );
            assert_eq!(actual.size, expected.size);
        }
    }
    assert_eq!(
        job.thumbnail(29).unwrap(),
        image
            .render_region_sdr8(&recipe, [0., 0.], [1., 1.], 29)
            .unwrap()
    );
    let root = tempfile::tempdir().unwrap();
    for format in [
        strehl_edit::ExportFormat::Tiff,
        strehl_edit::ExportFormat::Png,
        strehl_edit::ExportFormat::Jpeg,
    ] {
        let settings = ExportSettings {
            format,
            hdr: false,
            color_space: strehl_edit::OutputColorSpace::Srgb,
            ..Default::default()
        };
        let old = root.path().join(format!("old-{format:?}"));
        let new = root.path().join(format!("new-{format:?}"));
        strehl_edit::export_image(&old, &image, &recipe, &settings, &cancel).unwrap();
        job.export(&new, &settings, &cancel).unwrap();
        assert_eq!(std::fs::read(old).unwrap(), std::fs::read(new).unwrap());
    }
}

#[test]
fn clone_shares_token_and_buffers_but_reload_and_new_recipe_do_not() {
    let (image, recipe) = fixture();
    let job = DevelopmentJob::native(image.clone(), recipe.clone());
    let cloned = job.clone();
    assert_eq!(job.token(), cloned.token());
    assert!(Arc::ptr_eq(job.image(false), cloned.image(false)));
    assert!(Arc::ptr_eq(&job.recipe, &cloned.recipe));
    let replacement = Arc::new((*image).clone());
    assert!(!job.matches_source(&replacement));
    let reloaded = DevelopmentJob::native(replacement, recipe.clone());
    assert_ne!(job.token(), reloaded.token());
    let mut next = recipe;
    next.global.exposure += 1.;
    let changed = DevelopmentJob::native(image, next);
    assert_ne!(job.token(), changed.token());
    assert_ne!(job.thumbnail(29).unwrap(), changed.thumbnail(29).unwrap());
}

/// Explicitly run alone: alternating direction controls order/thermal drift.
/// These debug-build measurements bound this seam, not application responsiveness.
#[test]
#[ignore = "manual alternating-order commissioning benchmark"]
fn baseline_alternating_job_benchmark() {
    use sha2::{Digest, Sha256};
    use std::{hint::black_box, time::Instant};
    let (_, recipe) = fixture();
    let image = Arc::new(LinearImage {
        width: 2049,
        height: 1367,
        pixels: (0..2049 * 1367)
            .flat_map(|i| {
                [
                    0.02 + (i % 2049) as f32 / 2400.,
                    0.05 + (i / 2049) as f32 / 1600.,
                    0.1 + (i % 31) as f32 / 40.,
                ]
            })
            .collect(),
        origin: ImageOrigin::SceneLinear,
        baseline: Some(strehl_edit::DisplayBaseline {
            black: 0.01,
            white: 0.9,
            exposure_gain: 0.8,
            contrast: 0.15,
        }),
        baked_recipe: None,
    });
    let preview = Arc::new(image.preview(1600));
    let job = DevelopmentJob::new(image.clone(), preview, recipe.clone());
    let cancel = AtomicBool::new(false);
    for coarse in [true, false] {
        let source = job.image(coarse);
        let request = if coarse {
            DisplayRegionRequest {
                min: [0, 0],
                max: [source.width, source.height],
                stride: 1,
            }
        } else {
            DisplayRegionRequest {
                min: [317, 239],
                max: [1341, 1007],
                stride: 1,
            }
        };
        let render = |new| {
            if new {
                crate::photo_viewport::prepare_job(
                    &job, coarse, request, &cancel, None, false, true,
                )
            } else {
                crate::photo_viewport::prepare(source, &recipe, request, &cancel, None, false, true)
            }
            .unwrap()
        };
        let expected = render(false).sdr.unwrap();
        assert_eq!(expected, render(true).sdr.unwrap());
        let hash = Sha256::digest(
            expected
                .pixels
                .iter()
                .flat_map(|p| p.to_array())
                .collect::<Vec<_>>(),
        )
        .iter()
        .map(|b| format!("{b:02x}"))
        .collect::<String>();
        let mut old_ms = Vec::new();
        let mut new_ms = Vec::new();
        for pair in 0..8 {
            for new in if pair % 2 == 0 {
                [false, true]
            } else {
                [true, false]
            } {
                let start = Instant::now();
                let result = black_box(render(new));
                let elapsed = start.elapsed().as_secs_f64() * 1000.;
                if new {
                    new_ms.push(elapsed);
                } else {
                    old_ms.push(elapsed);
                }
                assert_eq!(result.sdr.as_ref().unwrap(), &expected);
            }
        }
        let old_min = old_ms.iter().copied().fold(f64::INFINITY, f64::min);
        let new_min = new_ms.iter().copied().fold(f64::INFINITY, f64::min);
        println!(
            "COMMISSIONING {}",
            serde_json::json!({"kind":if coarse {"coarse"} else {"native"},"build":"debug", "source":[2049,1367],"output":expected.size,"pixel_sha256":hash,"old_ms":old_ms,"new_ms":new_ms,"old_min_ms":old_min,"new_min_ms":new_min,"new_over_old_min":new_min/old_min})
        );
    }
    let mut old_ns = Vec::new();
    let mut new_ns = Vec::new();
    for pair in 0..8 {
        for new in if pair % 2 == 0 {
            [false, true]
        } else {
            [true, false]
        } {
            let start = Instant::now();
            for _ in 0..10000 {
                if new {
                    black_box(job.clone());
                } else {
                    black_box((image.clone(), recipe.clone()));
                }
            }
            let ns = start.elapsed().as_nanos() as f64 / 10000.;
            if new {
                new_ns.push(ns)
            } else {
                old_ns.push(ns)
            }
        }
    }
    println!(
        "COMMISSIONING {}",
        serde_json::json!({"kind":"capture-existing-job", "old_ns":old_ns,"new_ns":new_ns})
    );
    let mut large = recipe.clone();
    let region = large.regions[0].clone();
    large.regions.clear();
    for i in 0..6 {
        let mut region = region.clone();
        region.id = format!("spatial-{i}");
        large.spatial.push(strehl_edit::SpatialTreatment {
            version: 2,
            target_region: Some(region.id.clone()),
            parameters: Default::default(),
            amount: 0.7,
            bounds: [[0., 0.], [1., 1.]],
            width: 20,
            height: 20,
            levels: 33,
            log_min: -8.,
            log_max: 2.,
            tone_ev: vec![0.1; 20 * 20 * 33],
            color_gain: vec![1.05; 20 * 20 * 33],
            delivery_ceiling: 2.,
            centering_ev: 0.,
        });
        large.regions.push(region);
    }
    large.validate().unwrap();
    let mut editor = crate::edit_workspace::EditorState::default();
    editor.recipe = large;
    editor.loaded = Some(crate::edit_workspace::LoadedPhoto {
        image: image.clone(),
        preview: job.image(true).clone(),
        recipe: Default::default(),
        source: "in-memory.tiff".into(),
        warnings: vec![],
    });
    let cached = editor.development_job(false).unwrap();
    let mut old_us = Vec::new();
    let mut new_us = Vec::new();
    for pair in 0..8 {
        for new in if pair % 2 == 0 {
            [false, true]
        } else {
            [true, false]
        } {
            let start = Instant::now();
            for _ in 0..1000 {
                if new {
                    assert_eq!(
                        black_box(editor.development_job(false).unwrap()).token(),
                        cached.token()
                    );
                } else {
                    black_box((image.clone(), editor.recipe.clone()));
                }
            }
            let us = start.elapsed().as_secs_f64() * 1000.;
            if new {
                new_us.push(us)
            } else {
                old_us.push(us)
            }
        }
    }
    println!(
        "COMMISSIONING {}",
        serde_json::json!({"kind":"large-spatial-cache-hit", "spatial_fields":6,"lattice":[20,20,33],"coefficient_count":158400,"old_us":old_us,"new_us":new_us})
    );
}
