//! Independent lifecycle fixtures: unwritable destinations, different documents,
//! explicit embedded repair metadata, and superseded asynchronous previews.
use super::*;
use strehl_edit::{ImageOrigin, SourceRange};

struct TemporaryDirectory(PathBuf);
impl TemporaryDirectory {
    fn new() -> Self {
        let mut random = [0; 16];
        getrandom::fill(&mut random).unwrap();
        let name = random
            .iter()
            .map(|byte| format!("{byte:02x}"))
            .collect::<String>();
        let path = std::env::temp_dir().join(format!("strehl-edit-review-{name}"));
        std::fs::create_dir(&path).unwrap();
        Self(path)
    }
}
impl Drop for TemporaryDirectory {
    fn drop(&mut self) {
        assert_eq!(self.0.parent(), Some(std::env::temp_dir().as_path()));
        let _ = std::fs::remove_dir_all(&self.0);
    }
}
fn image() -> LinearImage {
    LinearImage {
        width: 128,
        height: 96,
        pixels: vec![0.2; 128 * 96 * 3],
        origin: ImageOrigin::SceneLinear,
        baseline: None,
        baked_recipe: None,
    }
}

#[test]
fn oversized_recipe_does_not_replace_reopenable_saved_edits() {
    let directory = TemporaryDirectory::new();
    let path = directory.0.join("photo.strehl-edits.json");
    let original = DevelopmentRecipe::default();
    save_recipe(&path, &original).unwrap();
    let previous_bytes = std::fs::read(&path).unwrap();
    let mut oversized = original.clone();
    for i in 0..128 {
        oversized.regions.push(RegionAdjustment {
            id: format!("region-{i}"),
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
    oversized.validate().unwrap();
    assert!(
        serde_json::to_vec_pretty(&oversized).unwrap().len() > 2 * 1024 * 1024,
        "fixture must exceed the reader's size limit"
    );
    assert!(
        save_recipe(&path, &oversized)
            .unwrap_err()
            .to_string()
            .contains("document limit")
    );
    assert_eq!(std::fs::read(&path).unwrap(), previous_bytes);
    let mut editor = EditorState::default();
    assert!(editor.replace(oversized).is_err());
    assert_eq!(editor.recipe, original);
    assert!(!editor.can_undo());
    let reopened: DevelopmentRecipe =
        serde_json::from_slice(&read_bounded(&path, 2 * 1024 * 1024).unwrap()).unwrap();
    assert_eq!(reopened, original);
}
fn editor() -> EditorState {
    let image = Arc::new(image());
    let preview = Arc::new(image.preview(32));
    EditorState {
        loaded: Some(LoadedPhoto {
            image,
            preview,
            recipe: Default::default(),
            source: PathBuf::from("not-opened-master.tiff"),
            warnings: Vec::new(),
        }),
        ..Default::default()
    }
}
fn poll_until(editor: &mut EditorState, predicate: impl Fn(&EditorState) -> bool) {
    let context = egui::Context::default();
    let deadline = Instant::now() + Duration::from_secs(8);
    while !predicate(editor) {
        assert!(
            Instant::now() < deadline,
            "Worker did not finish: {:?}",
            editor.error
        );
        editor.poll(&context, 128);
        std::thread::sleep(Duration::from_millis(2));
    }
}

#[test]
fn failed_save_survives_document_reset_without_pixels_and_retries_successfully() {
    let temporary = TemporaryDirectory::new();
    let blocked_parent = temporary.0.join("blocked");
    std::fs::write(&blocked_parent, b"file, not a directory").unwrap();
    let photograph = blocked_parent.join("result.tiff");
    let mut editor = editor();
    editor.path = Some(photograph.clone());
    editor.recipe.global.exposure = 1.5;
    let recipe = editor.recipe.clone();
    editor.reset_document();
    assert!(
        editor.error.is_some(),
        "Fixture must actually fail its save"
    );
    assert_eq!(editor.recoveries.get(&photograph), Some(&recipe));
    assert!(
        editor.loaded.is_none() && editor.texture.is_none() && editor.path.is_none(),
        "Unsaved recipes must never carry another photograph's pixels into the new view"
    );
    std::fs::remove_file(&blocked_parent).unwrap();
    std::fs::create_dir(&blocked_parent).unwrap();
    editor.flush().unwrap();
    assert!(editor.recoveries.is_empty());
    let saved: DevelopmentRecipe =
        serde_json::from_slice(&std::fs::read(recipe_path(&photograph)).unwrap()).unwrap();
    assert_eq!(saved, recipe);
}

#[test]
fn embedded_source_repair_recipe_is_restored_when_sidecar_is_missing() {
    let temporary = TemporaryDirectory::new();
    let path = temporary.0.join("result.tiff");
    let mut image = image();
    let mut recipe = DevelopmentRecipe::default();
    recipe.regions.push(RegionAdjustment {
        id: "repaired-edge".into(),
        name: "Repair".into(),
        note: String::new(),
        shape: RegionShape::Rectangle {
            min: [0.2, 0.1],
            max: [0.6, 0.9],
        },
        feather: 0.3,
        enabled: true,
        adjustments: Default::default(),
        source_range: Some(SourceRange { first: 2, last: 4 }),
    });
    image.baked_recipe = Some(recipe.clone());
    strehl_edit::save_linear_tiff(&path, &image).unwrap();
    let mut editor = EditorState::default();
    editor.open(path);
    poll_until(&mut editor, |state| {
        state.loaded.is_some() || state.error.is_some()
    });
    assert_eq!(
        editor.recipe, recipe,
        "Missing sidecar must not erase the baked repair contract"
    );
}

#[test]
fn viewport_refinement_keeps_overview_and_drops_a_superseded_recipe() {
    let mut editor = editor();
    let ctx = egui::Context::default();
    editor.request_view(
        &ctx,
        (
            egui::Rect::from_min_size(egui::Pos2::ZERO, egui::vec2(128.0, 96.0)),
            egui::Rect::from_min_size(egui::Pos2::ZERO, egui::vec2(128.0, 96.0)),
        ),
        128,
    );
    poll_until(&mut editor, |state| {
        !state.display_stats()["published"].is_null()
    });
    assert_eq!(editor.texture.as_ref().unwrap().size(), [32, 24]);
    assert_eq!(
        editor.display_stats()["published"]["pixels"],
        serde_json::json!([128, 96])
    );
    let old_revision = editor.revision;
    let mut next = editor.recipe.clone();
    next.global.exposure = 0.5;
    editor.replace(next).unwrap();
    editor.developing_revision = Some(old_revision);
    editor.developing = Some(spawn_task("test-old-preview", move |cancelled| {
        let source = image();
        let prepared = crate::photo_viewport::prepare(
            &source,
            &DevelopmentRecipe::default(),
            strehl_edit::DisplayRegionRequest {
                min: [0, 0],
                max: [128, 96],
                stride: 1,
            },
            &cancelled,
            None,
            false,
            true,
        )?;
        Ok(DevelopedPreview {
            revision: old_revision,
            before: false,
            hdr: false,
            prepared,
        })
    }));
    poll_until(&mut editor, |state| {
        state.painted_revision == Some(state.revision)
    });
    assert!(editor.revision > old_revision);
    assert!(editor.error.is_none());
    assert_eq!(editor.texture.as_ref().unwrap().size(), [32, 24]);
    let published = editor.display_stats()["published"].clone();
    assert!(
        published.is_null() || published["revision"] == editor.revision,
        "Coarse publication must atomically retire the old-recipe patch"
    );
}

#[test]
fn failed_stale_preview_does_not_mark_the_new_recipe_as_painted() {
    let mut editor = editor();
    let stale = editor.revision;
    editor.changed();
    editor.developing_revision = Some(stale);
    editor.developing = Some(spawn_task("test-old-preview-failure", |_| {
        anyhow::bail!("old failure")
    }));
    poll_until(&mut editor, |state| {
        state.painted_revision == Some(state.revision)
    });
    assert!(
        editor.error.is_none(),
        "Superseded errors must not suppress the current preview"
    );
    assert_eq!(editor.painted_side, 32);
}

#[test]
fn a_partial_preset_preserves_regions_source_repairs_and_unmentioned_controls() {
    let mut editor = editor();
    editor.recipe.global.shadows = 25.0;
    editor.recipe.hdr.peak_nits = 1400.0;
    editor.recipe.regions.push(RegionAdjustment {
        id: "keep".into(),
        name: "Existing issue".into(),
        note: "Keep this note".into(),
        shape: RegionShape::Rectangle {
            min: [0.0, 0.0],
            max: [0.5, 0.5],
        },
        feather: 0.2,
        enabled: true,
        adjustments: Default::default(),
        source_range: Some(SourceRange { first: 3, last: 5 }),
    });
    let before = editor.recipe.clone();
    let import=strehl_edit::import_xmp(r#"<x:xmpmeta xmlns:x="adobe:ns:meta/" xmlns:crs="http://ns.adobe.com/camera-raw-settings/1.0/"><rdf:Description xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#" crs:Exposure2012="1.25" crs:HDRMaxValue="2"/></x:xmpmeta>"#).unwrap();
    editor.apply_preset(import).unwrap();
    assert_eq!(editor.recipe.global.exposure, 1.25);
    assert_eq!(editor.recipe.global.shadows, 25.0);
    assert_eq!(editor.recipe.regions, before.regions);
    assert_eq!(editor.recipe.hdr, before.hdr);
    assert!(editor.undo());
    assert_eq!(editor.recipe, before);
}

#[test]
fn closing_preserves_failed_sidecar_edits_across_a_new_process_state() {
    let temporary = TemporaryDirectory::new();
    let blocked = temporary.0.join("read-only-parent");
    std::fs::write(&blocked, b"not a directory").unwrap();
    let photograph = blocked.join("result.tiff");
    let recovery = temporary.0.join("recovered-edits");
    let mut first = editor();
    first.path = Some(photograph.clone());
    first.recipe.global.exposure = 2.25;
    first.recovery_root = Some(recovery.clone());
    assert!(
        first.flush().is_err(),
        "The primary save must actually fail"
    );
    first.ensure_saved_on_close().unwrap();
    let saved = first.recipe.clone();
    drop(first);
    let mut restarted = EditorState {
        recovery_root: Some(recovery),
        ..Default::default()
    };
    restarted.restore_recoveries();
    assert!(restarted.error.is_none(), "{:?}", restarted.error);
    assert_eq!(restarted.recoveries.get(&photograph), Some(&saved));
    assert!(restarted.recovered_from_disk.contains(&photograph));
    restarted.flush().unwrap();
    assert_eq!(
        restarted.recoveries.get(&photograph),
        Some(&saved),
        "Old-session recovery must wait for explicit restore, never overwrite another session's sidecar"
    );
}

#[test]
fn closing_is_refused_when_both_photo_and_recovery_destinations_fail() {
    let temporary = TemporaryDirectory::new();
    let blocked = temporary.0.join("blocked");
    std::fs::write(&blocked, b"not a directory").unwrap();
    let mut editor = editor();
    editor.path = Some(blocked.join("result.tiff"));
    editor.recipe.global.exposure = 1.75;
    editor.recovery_root = Some(blocked.join("recovery"));
    assert!(editor.ensure_saved_on_close().is_err());
    assert_eq!(editor.recipe.global.exposure, 1.75);
    assert!(
        editor.loaded.is_some(),
        "A failed close must retain the live document"
    );
    assert_eq!(editor.recoveries.len(), 1);
}

#[test]
fn mismatched_master_is_never_attached_to_a_photograph() {
    let temporary = TemporaryDirectory::new();
    let result = temporary.0.join("result.tiff");
    let master = temporary.0.join("master.tiff");
    strehl_edit::save_linear_tiff(&result, &image().preview(32)).unwrap();
    strehl_edit::save_linear_tiff(&master, &image()).unwrap();
    let mut editor = EditorState::default();
    editor.open(result);
    poll_until(&mut editor, |state| state.error.is_some());
    assert!(editor.loaded.is_none());
    assert!(editor.texture.is_none());
    assert!(
        editor
            .error
            .as_ref()
            .unwrap()
            .contains("dimensions do not match")
    );
}

#[test]
fn a_failed_second_export_cannot_reuse_the_previous_success_receipt() {
    let temporary = TemporaryDirectory::new();
    let mut editor = editor();
    let loaded = editor.loaded.as_mut().unwrap();
    Arc::make_mut(&mut loaded.image).origin = ImageOrigin::DisplayReferred;
    editor.last_export = Some(PathBuf::from("previous-success.tiff"));
    editor
        .export_with_settings(
            temporary.0.join("rejected-hdr.avif"),
            strehl_edit::ExportSettings::default(),
        )
        .unwrap();
    assert!(
        editor.last_export.is_none(),
        "Starting a new export must invalidate the old success"
    );
    poll_until(&mut editor, |state| state.exporting.is_none());
    assert!(
        editor.error.is_some(),
        "The SDR-to-HDR fixture must actually fail"
    );
    assert!(editor.last_export.is_none());
}
