use super::*;
use strehl_edit::{
    Adjustments, DevelopmentRecipe, ImageOrigin, LinearImage, RegionAdjustment, RegionShape,
    SourceRange, SpatialTreatment,
};

fn field(target: Option<&str>) -> SpatialTreatment {
    SpatialTreatment {
        version: 1,
        target_region: target.map(str::to_owned),
        parameters: Default::default(),
        amount: 0.6,
        bounds: [[0.0, 0.0], [1.0, 1.0]],
        width: 2,
        height: 2,
        levels: 3,
        log_min: -8.0,
        log_max: 2.0,
        tone_ev: vec![0.2; 12],
        color_gain: vec![1.05; 4],
        delivery_ceiling: 4.0,
        centering_ev: 0.0,
    }
}

fn fixture() -> StrehlApp {
    let mut app = StrehlApp::from_launch(4096, LaunchOptions::default());
    app.catalog = Default::default();
    let path = PathBuf::from("never-written-agent-spatial-photo.tiff");
    let image = Arc::new(LinearImage {
        width: 16,
        height: 12,
        pixels: vec![0.2; 16 * 12 * 3],
        origin: ImageOrigin::SceneLinear,
        baseline: None,
        baked_recipe: None,
    });
    app.result = Some(path.clone());
    app.image_path = Some(path.clone());
    app.editor.path = Some(path.clone());
    app.editor.loaded = Some(crate::edit_workspace::LoadedPhoto {
        image: image.clone(),
        preview: image,
        source: path,
        recipe: Default::default(),
        warnings: Vec::new(),
    });
    app.editor.recipe.regions.push(RegionAdjustment {
        id: "reflection".into(),
        name: "Reflection".into(),
        note: "Original repair".into(),
        shape: RegionShape::Rectangle {
            min: [0.2, 0.3],
            max: [0.6, 0.8],
        },
        feather: 0.3,
        enabled: true,
        adjustments: Default::default(),
        source_range: Some(SourceRange { first: 2, last: 5 }),
    });
    app.editor.recipe.spatial = vec![field(None), field(Some("reflection"))];
    app.editor.recipe.validate().unwrap();
    app.result_viewer.source_size = [16, 12];
    assert!(app.agent_photo_is_current());
    app
}

#[test]
fn portable_adjustments_preserve_measured_fields_and_are_one_scoped_undo() {
    for region_id in [None, Some("reflection".to_owned())] {
        let mut app = fixture();
        let original = app.editor.recipe.clone();
        app.apply_agent_command(AgentCommand::SetAdjustments {
            adjustments: Adjustments {
                exposure: 0.7,
                ..Default::default()
            },
            region_id: region_id.clone(),
        })
        .unwrap();
        let after = app.editor.recipe.clone();
        assert_eq!(after.spatial, original.spatial);
        assert_eq!(after.hdr, original.hdr);
        assert_eq!(after.regions[0].shape, original.regions[0].shape);
        assert_eq!(
            after.regions[0].source_range,
            original.regions[0].source_range
        );
        if region_id.is_some() {
            assert_eq!(after.global, original.global);
            assert_eq!(after.regions[0].adjustments.exposure, 0.7);
        } else {
            assert_eq!(after.regions, original.regions);
            assert_eq!(after.global.exposure, 0.7);
        }
        assert!(app.editor.undo());
        assert_eq!(app.editor.recipe, original);
        assert!(app.editor.redo());
        assert_eq!(app.editor.recipe, after);
    }
}

#[test]
fn legacy_replacement_preserves_spatial_and_only_explicit_clear_removes_its_scope() {
    let mut app = fixture();
    let original = app.editor.recipe.clone();
    let mut legacy = serde_json::to_value(&original).unwrap();
    legacy.as_object_mut().unwrap().remove("spatial");
    legacy["global"]["exposure"] = json!(0.5);
    let recipe: DevelopmentRecipe = serde_json::from_value(legacy).unwrap();
    assert!(
        recipe.spatial.is_empty(),
        "fixture must exercise a pre-spatial client"
    );
    app.apply_agent_command(AgentCommand::SetDevelop { recipe })
        .unwrap();
    assert_eq!(app.editor.recipe.spatial, original.spatial);
    assert_eq!(app.editor.recipe.global.exposure, 0.5);
    let before_clear = app.editor.recipe.clone();
    app.apply_agent_command(AgentCommand::ClearAdaptive {
        region_id: Some("reflection".into()),
    })
    .unwrap();
    assert_eq!(app.editor.recipe.spatial, vec![field(None)]);
    assert_eq!(app.editor.recipe.regions, before_clear.regions);
    assert!(app.editor.undo());
    assert_eq!(app.editor.recipe, before_clear);
    app.apply_agent_command(AgentCommand::RemoveAnnotation {
        id: "reflection".into(),
    })
    .unwrap();
    assert!(app.editor.recipe.regions.is_empty());
    assert_eq!(app.editor.recipe.spatial, vec![field(None)]);
    assert!(app.editor.undo());
    assert_eq!(app.editor.recipe, before_clear);
}

#[test]
fn unknown_scope_or_legacy_geometry_removal_fails_atomically() {
    let mut app = fixture();
    let before = app.editor.recipe.clone();
    for command in [
        AgentCommand::SetAdjustments {
            adjustments: Default::default(),
            region_id: Some("missing".into()),
        },
        AgentCommand::ClearAdaptive {
            region_id: Some("missing".into()),
        },
        AgentCommand::SetDevelop {
            recipe: DevelopmentRecipe::default(),
        },
    ] {
        assert!(app.apply_agent_command(command).is_err());
        assert_eq!(app.editor.recipe, before);
    }
}

#[test]
fn agent_rejects_unsavable_pretty_recipes_including_preserved_fields() {
    let limit = crate::agent_interface::MAX_RECIPE_BYTES;
    let mut app = fixture();
    let mut measured = field(None);
    measured.width = 20;
    measured.height = 20;
    measured.levels = 33;
    measured.tone_ev = vec![0.2; 20 * 20 * 33];
    measured.color_gain = vec![1.05; 20 * 20];
    app.editor.recipe = DevelopmentRecipe {
        spatial: vec![measured],
        ..Default::default()
    };
    let before = app.editor.recipe.clone();
    let revision = app.editor.revision;
    let mut candidate = DevelopmentRecipe::default();
    for i in 0..128 {
        candidate.regions.push(RegionAdjustment {
            id: format!("r-{i}"),
            name: "n".repeat(256),
            note: "x".repeat(4096),
            shape: RegionShape::Polygon {
                points: (0..256)
                    .map(|j| {
                        let angle = j as f32 * std::f32::consts::TAU / 256.0;
                        [0.5 + 0.4 * angle.cos(), 0.5 + 0.4 * angle.sin()]
                    })
                    .collect(),
            },
            feather: 0.0,
            enabled: true,
            adjustments: Default::default(),
            source_range: None,
        });
    }
    candidate.validate().unwrap();
    assert!(
        serde_json::to_vec(&candidate).unwrap().len() < limit,
        "compact wire fixture must fit"
    );
    assert!(
        serde_json::to_vec_pretty(&candidate).unwrap().len() > limit,
        "saved representation must exceed limit"
    );
    assert!(
        app.apply_agent_command(AgentCommand::SetDevelop {
            recipe: candidate.clone()
        })
        .is_err()
    );
    assert_eq!(app.editor.recipe, before);
    while serde_json::to_vec_pretty(&candidate).unwrap().len() > limit {
        candidate.regions.pop().unwrap();
    }
    AgentCommand::SetDevelop {
        recipe: candidate.clone(),
    }
    .validate()
    .unwrap();
    let mut merged = candidate.clone();
    merged.spatial.clone_from(&before.spatial);
    assert!(
        serde_json::to_vec_pretty(&merged).unwrap().len() > limit,
        "preservation must be the reason this candidate no longer fits"
    );
    assert!(
        app.apply_agent_command(AgentCommand::SetDevelop { recipe: candidate })
            .is_err()
    );
    assert_eq!(app.editor.recipe, before);
    assert_eq!(app.editor.revision, revision);
    assert!(
        !app.editor.undo(),
        "rejected operations must not enter Undo"
    );
}
