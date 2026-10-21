use super::*;
use strehl_edit::{ExportFormat, ExportSettings, ImageOrigin, LinearImage, OutputColorSpace};

fn export(value: Value) -> AgentCommand {
    serde_json::from_value(value).unwrap()
}

#[test]
fn old_export_commands_and_all_new_delivery_options_are_validated() {
    for format in ["avif", "tiff", "png", "jpeg"] {
        let command = export(json!({"operation":"export","file_name":"photo.bin","format":format}));
        command.validate().unwrap();
        let resolved = crate::agent_interface::resolve_export_settings(
            format,
            None,
            None,
            None,
            None,
            Some(ImageOrigin::SceneLinear),
        )
        .unwrap();
        assert_eq!(resolved.quality, ExportSettings::default().quality);
        assert_eq!(resolved.color_space, ExportSettings::default().color_space);
        assert_eq!(resolved.hdr, format == "avif");
    }
    for space in ["srgb", "display_p3", "rec2020"] {
        export(
            json!({"operation":"export","file_name":"photo.avif","format":"avif",
            "color_space":space,"hdr":false,"quality":89,"speed":3}),
        )
        .validate()
        .unwrap();
    }
    for fields in [
        json!({"format":"webp"}),
        json!({"quality":0}),
        json!({"quality":101}),
        json!({"speed":11}),
        json!({"format":"png","hdr":true}),
        json!({"file_name":"../escape.png"}),
        json!({"file_name":"C:\\outside.png"}),
    ] {
        let mut value = json!({"operation":"export","file_name":"photo.avif","format":"avif"});
        value
            .as_object_mut()
            .unwrap()
            .extend(fields.as_object().unwrap().clone());
        assert!(export(value).validate().is_err());
    }
    for fields in [
        json!({"color_space":"unmanaged"}),
        json!({"quality":2.5}),
        json!({"hdr":"yes"}),
        json!({"path":"outside"}),
    ] {
        let mut value = json!({"operation":"export","file_name":"photo.avif","format":"avif"});
        value
            .as_object_mut()
            .unwrap()
            .extend(fields.as_object().unwrap().clone());
        assert!(serde_json::from_value::<AgentCommand>(value).is_err());
    }
}

fn app(origin: ImageOrigin) -> StrehlApp {
    let mut app = StrehlApp::from_launch(4096, LaunchOptions::default());
    app.catalog = Default::default();
    let image = Arc::new(LinearImage {
        width: 16,
        height: 12,
        pixels: vec![0.2; 16 * 12 * 3],
        origin,
        baseline: None,
        baked_recipe: None,
    });
    let path = PathBuf::from("never-written-agent-export-master.tiff");
    app.editor.loaded = Some(crate::edit_workspace::LoadedPhoto {
        image: image.clone(),
        preview: image,
        recipe: Default::default(),
        source: path.clone(),
        warnings: Vec::new(),
    });
    app.result = Some(path.clone());
    app.image_path = Some(path.clone());
    app.editor.path = Some(path);
    app.result_viewer.source_size = [16, 12];
    assert!(app.agent_photo_is_current());
    app
}

#[test]
fn hdr_from_sdr_is_rejected_before_queuing_and_omitted_hdr_matches_human_defaults() {
    let mut app = app(ImageOrigin::DisplayReferred);
    app.export_pane.destination = Some(std::env::temp_dir());
    assert_eq!(
        app.agent_snapshot()["export_capabilities"]["hdr_available"],
        false
    );
    let error = app.apply_agent_command(export(json!({"operation":"export","file_name":"never-created-agent-export.avif","format":"avif","hdr":true}))).unwrap_err();
    assert!(error.to_string().contains("scene-linear"));
    assert!(app.editor.exporting.is_none());
    let resolved = crate::agent_interface::resolve_export_settings(
        "avif",
        None,
        None,
        None,
        None,
        Some(ImageOrigin::DisplayReferred),
    )
    .unwrap();
    assert_eq!(resolved.format, ExportFormat::Avif);
    assert!(!resolved.hdr);
    assert_eq!(resolved.color_space, OutputColorSpace::Rec2020);
}

#[test]
fn agent_exports_use_the_real_writer_and_preserve_existing_files() {
    let mut app = app(ImageOrigin::DisplayReferred);
    let nonce = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .unwrap()
        .as_nanos();
    let destination = std::env::temp_dir().join(format!(
        "strehl-agent-exports-{}-{nonce}",
        std::process::id()
    ));
    std::fs::create_dir(&destination).unwrap();
    app.output = destination.join("not-the-chosen-destination");
    app.export_pane.destination = Some(destination.clone());
    let recipe = app.editor.recipe.clone();
    for (format, suffix, image_format) in [
        ("tiff", "tiff", image::ImageFormat::Tiff),
        ("png", "png", image::ImageFormat::Png),
        ("jpeg", "jpg", image::ImageFormat::Jpeg),
    ] {
        let name = format!("photo.{suffix}");
        let value = json!({"operation":"export","file_name":name,"format":format,"color_space":"display_p3","quality":94,"hdr":false});
        let reply = app.apply_agent_command(export(value.clone())).unwrap();
        assert_eq!(reply["state"], "queued");
        assert_eq!(reply["settings"]["color_space"], "display_p3");
        assert_eq!(reply["settings"]["quality"], 94);
        let worker = app.editor.exporting.take().unwrap();
        let path = worker
            .receiver
            .recv_timeout(Duration::from_secs(15))
            .unwrap()
            .unwrap();
        assert_eq!(path.parent(), Some(destination.as_path()));
        let bytes = std::fs::read(&path).unwrap();
        let decoded = image::load_from_memory_with_format(&bytes, image_format).unwrap();
        assert_eq!((decoded.width(), decoded.height()), (16, 12));
        assert!(app.apply_agent_command(export(value)).is_err());
        assert!(app.editor.exporting.is_none());
        assert_eq!(std::fs::read(path).unwrap(), bytes);
    }
    assert_eq!(
        app.editor.recipe, recipe,
        "delivery options must not edit the photograph"
    );
    assert!(
        !app.output.exists(),
        "agent must not use the stack-output setting"
    );
    std::fs::remove_dir_all(&destination).unwrap();
}

#[test]
fn agent_export_requires_explicit_destination_and_folder_change_invalidates_revision() {
    let mut app = app(ImageOrigin::DisplayReferred);
    app.output = std::env::temp_dir(); // Existing writable stack output is insufficient.
    let command = export(
        json!({"operation":"export","file_name":"never-created-agent-destination.png","format":"png"}),
    );
    assert!(
        app.apply_agent_command(command.clone())
            .unwrap_err()
            .to_string()
            .contains("Destination")
    );
    assert!(app.editor.exporting.is_none());
    assert!(app.agent_snapshot()["export_capabilities"]["destination"].is_null());
    app.sync_agent_revision();
    let observed = app.agent.revision;
    app.export_pane.destination = Some(std::env::temp_dir());
    app.sync_agent_revision();
    assert!(
        crate::agent_interface::AgentRequest {
            expected_revision: Some(observed),
            command
        }
        .check_revision(app.agent.revision)
        .is_err()
    );
    assert_eq!(
        app.agent_snapshot()["export_capabilities"]["destination"],
        json!(std::env::temp_dir())
    );
}
