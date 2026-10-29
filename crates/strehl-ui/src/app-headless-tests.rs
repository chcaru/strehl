//! Independent headless lifecycle tests. Only fresh temporary catalogs and tiny
//! generated photographs are used; no renderer, desktop, or RAW corpus is opened.
use super::*;
use crate::agent_interface::{AgentBridge, AgentCommand, AgentRequest};
use serde_json::json;

fn launch(root: &Path) -> LaunchOptions {
    LaunchOptions {
        headless: true,
        agent: true,
        agent_session_out: Some(root.join("ready.json")),
        ..Default::default()
    }
}

fn isolated_app(root: &Path) -> StrehlApp {
    StrehlApp::from_launch(
        128,
        LaunchOptions {
            headless: true,
            catalog: Some(root.join("catalog.json")),
            ..Default::default()
        },
    )
}

struct Pump {
    ctx: egui::Context,
    started: Instant,
}
impl Pump {
    fn new() -> Self {
        Self {
            ctx: egui::Context::default(),
            started: Instant::now(),
        }
    }
    fn tick(&self, app: &mut StrehlApp) {
        let _ = self.ctx.run(
            egui::RawInput {
                time: Some(self.started.elapsed().as_secs_f64()),
                focused: false,
                ..Default::default()
            },
            |ctx| app.headless_tick(ctx),
        );
    }
    fn until(&self, app: &mut StrehlApp, ready: impl Fn(&StrehlApp) -> bool) {
        let deadline = Instant::now() + Duration::from_secs(10);
        loop {
            self.tick(app);
            if ready(app) {
                return;
            }
            assert!(
                Instant::now() < deadline,
                "Headless work did not settle: {:?}",
                app.editor.error
            );
            std::thread::sleep(Duration::from_millis(2));
        }
    }
}

#[test]
fn invalid_automation_launches_do_not_create_or_replace_files() {
    let files = tempfile::tempdir().unwrap();
    let root = files.path();
    let sentinel = root.join("keep.json");
    fs::write(&sentinel, b"pre-existing publication").unwrap();

    let mut denied = LaunchOptions {
        agent_session_out: Some(root.join("ready.json")),
        ..Default::default()
    };
    assert!(validate_automation_launch(&mut denied).is_err());
    for change in [
        (|l: &mut LaunchOptions| l.agent_session_out = None) as fn(&mut LaunchOptions),
        |l| l.browse = Some(PathBuf::from(".")),
        |l| l.screenshot = Some(PathBuf::from("screen.png")),
        |l| l.reveal_at_ms = Some(1.0),
        |l| l.screenshot_hover = Some([0.5, 0.5]),
        |l| l.screenshot_ranges = Some(vec![[0, 1]]),
    ] {
        let mut options = launch(root);
        change(&mut options);
        assert!(validate_automation_launch(&mut options).is_err());
    }
    let mut collision = launch(root);
    collision.catalog = collision.agent_session_out.clone();
    assert!(validate_automation_launch(&mut collision).is_err());
    let mut existing = launch(root);
    existing.agent_session_out = Some(sentinel.clone());
    assert!(validate_automation_launch(&mut existing).is_err());
    let mut missing_parent = launch(root);
    missing_parent.agent_session_out = Some(root.join("not-created/ready.json"));
    assert!(validate_automation_launch(&mut missing_parent).is_err());
    let mut file_grant = launch(root);
    file_grant.agent_grants.push(sentinel.clone());
    assert!(validate_automation_launch(&mut file_grant).is_err());
    let mut absent_grant = launch(root);
    absent_grant.agent_grants.push(root.join("absent"));
    assert!(validate_automation_launch(&mut absent_grant).is_err());
    let mut excess = launch(root);
    excess.agent_grants = vec![root.to_owned(); 33];
    assert!(validate_automation_launch(&mut excess).is_err());

    assert_eq!(fs::read(&sentinel).unwrap(), b"pre-existing publication");
    assert_eq!(fs::read_dir(root).unwrap().count(), 1);
}

#[test]
fn launch_grants_catalog_and_recovery_are_explicit_and_isolated() {
    let files = tempfile::tempdir().unwrap();
    let root = files.path().canonicalize().unwrap();
    let shared = root.join("shared");
    fs::create_dir(&shared).unwrap();
    let output = root.join("chosen-output");
    let mut options = launch(&root);
    options.agent_grants = vec![shared.join(".")];
    options.output_directory = Some(output.clone());
    validate_automation_launch(&mut options).unwrap();
    assert_eq!(options.catalog, Some(root.join("ready.projects.json")));
    assert_eq!(options.agent_grants, vec![shared.canonicalize().unwrap()]);
    // Exercise state construction without creating an unnecessary mailbox.
    options.agent = false;
    let app = StrehlApp::from_launch(128, options);
    assert_eq!(app.catalog.path, Some(root.join("ready.projects.json")));
    assert_eq!(
        app.editor.recovery_root,
        Some(root.join("ready.projects.recovered-edits"))
    );
    assert_eq!(
        app.agent.grants.get("folder-1"),
        Some(&shared.canonicalize().unwrap())
    );
    assert_eq!(app.output, output);
    assert!(app.editor.viewport.presenter.is_none());
    assert!(!root.join("ready.json").exists());
    assert!(!root.join("ready.projects.json").exists());
    assert!(!output.exists());
}

#[test]
fn catalog_lease_refuses_an_existing_owner_and_releases_only_on_drop() {
    let files = tempfile::tempdir().unwrap();
    let catalog = files.path().join("catalog.json");
    let lock_path = files.path().join("catalog.json.headless-lock");
    let first = CatalogLease::acquire(&catalog).unwrap();
    let original = fs::read(&lock_path).unwrap();
    assert!(CatalogLease::acquire(&catalog).is_err());
    assert_eq!(fs::read(&lock_path).unwrap(), original);
    drop(first);
    assert!(!lock_path.exists());
    drop(CatalogLease::acquire(&catalog).unwrap());
    assert!(!lock_path.exists());
}

#[test]
fn discovery_publishes_a_pointer_without_copying_the_capability_or_overwriting() {
    let files = tempfile::tempdir().unwrap();
    let bridge = AgentBridge::start(files.path()).unwrap();
    let descriptor = bridge.descriptor_path();
    let secret: serde_json::Value = serde_json::from_slice(&fs::read(descriptor).unwrap()).unwrap();
    let path = files.path().join("ready.json");
    publish_session(&path, descriptor).unwrap();
    let original = fs::read(&path).unwrap();
    let pointer: serde_json::Value = serde_json::from_slice(&original).unwrap();
    assert_eq!(
        pointer["session"],
        serde_json::to_value(descriptor).unwrap()
    );
    assert_eq!(pointer["pid"], std::process::id());
    assert!(pointer.get("capability").is_none());
    assert!(
        !String::from_utf8(original.clone())
            .unwrap()
            .contains(secret["capability"].as_str().unwrap())
    );
    assert!(publish_session(&path, descriptor).is_err());
    assert_eq!(fs::read(&path).unwrap(), original);
}

#[test]
fn headless_ticks_load_save_undo_and_record_photograph_history_without_painting() {
    let files = tempfile::tempdir().unwrap();
    let photograph = files.path().join("photograph.tiff");
    image::ImageBuffer::<image::Rgb<u16>, Vec<u16>>::from_pixel(
        8,
        6,
        image::Rgb([18000, 25000, 8000]),
    )
    .save(&photograph)
    .unwrap();
    let original = fs::read(&photograph).unwrap();
    let catalog = files.path().join("catalog.json");
    let mut app = StrehlApp::from_launch(
        128,
        LaunchOptions {
            headless: true,
            edit: true,
            preview: Some(photograph.clone()),
            catalog: Some(catalog.clone()),
            ..Default::default()
        },
    );
    let pump = Pump::new();
    pump.until(&mut app, |a| {
        a.editor.loaded.is_some()
            && a.editor.loading.is_none()
            && a.result_work.is_none()
            && a.pending_result.is_none()
            && a.editor.developing.is_none()
    });
    assert!(app.editor.error.is_none(), "{:?}", app.editor.error);
    assert!(app.editor.viewport.presenter.is_none());
    assert!(app.process_space.edit_mapping().is_none());
    assert_eq!(app.updates, 0, "No workspace painting should be needed");
    let before = app.editor.recipe.clone();
    app.editor.recipe.global.exposure = 1.25;
    app.editor
        .begin_edit(before.clone(), pump.started.elapsed().as_secs_f64());
    pump.until(&mut app, |a| {
        a.editor.pending_edit.is_none()
            && a.editor.saving.is_none()
            && a.editor.saved_revision == Some(a.editor.revision)
            && a.editor.developing.is_none()
    });
    let recipe_path = crate::edit_workspace::recipe_path(&photograph);
    let saved: strehl_edit::DevelopmentRecipe =
        serde_json::from_slice(&fs::read(&recipe_path).unwrap()).unwrap();
    assert_eq!(saved.global.exposure, 1.25);
    assert!(
        app.undo_edit(false),
        "The polling loop must update the shared undo journal"
    );
    assert_eq!(app.editor.recipe, before);
    assert!(app.undo_edit(true));
    assert_eq!(app.editor.recipe.global.exposure, 1.25);
    app.save_edit_version("Headless retained version").unwrap();
    assert!(app.photo_history_busy());
    assert!(app.prepare_headless_shutdown(&pump.ctx).is_err());
    assert!(!app.headless_shutdown);
    pump.until(&mut app, |a| {
        !a.photo_history_busy() && a.editor.developing.is_none() && a.editor.saving.is_none()
    });
    assert_eq!(
        app.catalog.photo_versions.len(),
        1,
        "{}",
        app.photo_history_snapshot()
    );
    assert_eq!(
        app.photo_history_snapshot()["error"],
        serde_json::Value::Null
    );
    let result = app.prepare_headless_shutdown(&pump.ctx).unwrap();
    assert_eq!(result["state"], "shutdown_accepted");
    assert_eq!(result["saved"], true);
    assert!(app.headless_shutdown);
    assert_eq!(fs::read(&photograph).unwrap(), original);
    let reopened = crate::workspace_history::Catalog::load(Some(catalog));
    assert_eq!(reopened.photo_versions.len(), 1);
    let saved: strehl_edit::DevelopmentRecipe =
        serde_json::from_slice(&fs::read(recipe_path).unwrap()).unwrap();
    assert_eq!(saved.global.exposure, 1.25);
}

#[test]
fn shutdown_refuses_busy_or_interactive_state_without_changing_the_workspace() {
    let files = tempfile::tempdir().unwrap();
    let ctx = egui::Context::default();
    let mut app = isolated_app(files.path());
    let original_recipe = app.editor.recipe.clone();
    let original_catalog = serde_json::to_value(&app.catalog).unwrap();
    app.pending_result = Some(files.path().join("not-opened.tiff"));
    assert!(app.prepare_headless_shutdown(&ctx).is_err());
    assert!(!app.headless_shutdown);
    assert_eq!(app.editor.recipe, original_recipe);
    assert_eq!(
        serde_json::to_value(&app.catalog).unwrap(),
        original_catalog
    );
    assert!(!files.path().join("catalog.json").exists());
    app.pending_result = None;
    app.headless = false;
    assert!(app.prepare_headless_shutdown(&ctx).is_err());
    assert!(!app.headless_shutdown);
    assert_eq!(app.editor.recipe, original_recipe);
    assert!(!files.path().join("catalog.json").exists());
}

#[test]
fn shutdown_preserves_an_external_catalog_change_and_refuses_success() {
    let files = tempfile::tempdir().unwrap();
    let ctx = egui::Context::default();
    let mut app = isolated_app(files.path());
    app.catalog.create_project("This session").unwrap();
    app.catalog.save().unwrap();
    let path = app.catalog.path.clone().unwrap();
    let mut other = crate::workspace_history::Catalog::load(Some(path.clone()));
    other.create_project("External writer").unwrap();
    other.save().unwrap();
    let external = fs::read(&path).unwrap();
    let current = serde_json::to_value(&app.catalog).unwrap();
    let error = app.prepare_headless_shutdown(&ctx).unwrap_err().to_string();
    assert!(error.contains("changed in another window"), "{error}");
    assert!(!app.headless_shutdown);
    assert_eq!(fs::read(&path).unwrap(), external);
    assert_eq!(serde_json::to_value(&app.catalog).unwrap(), current);
}

#[test]
fn shutdown_is_a_revision_checked_mutation_and_unknown_fields_stay_rejected() {
    let request = AgentRequest {
        expected_revision: Some(41),
        command: AgentCommand::Shutdown {},
    };
    assert!(!request.command.is_read_only());
    assert!(request.check_revision(41).is_ok());
    assert!(request.check_revision(42).is_err());
    assert!(
        AgentRequest {
            expected_revision: None,
            command: AgentCommand::Shutdown {}
        }
        .validate()
        .is_err()
    );
    assert!(
        serde_json::from_value::<AgentRequest>(
            json!({"expected_revision":41,"command":{"operation":"shutdown","force":true}})
        )
        .is_err()
    );
}

#[test]
fn headless_autosave_undo_shutdown_and_reload_do_not_require_immutable_versions() {
    // Keep the separate full photo-history test unchanged. This path checks the
    // ordinary editable recipe and lifecycle without replacing or bypassing
    // the immutable history writer, whose hard-link publication can fail on
    // a restricted filesystem.
    let files = tempfile::tempdir().unwrap();
    let photograph = files.path().join("editable-photograph.tiff");
    image::ImageBuffer::<image::Rgb<u16>, Vec<u16>>::from_pixel(
        8,
        6,
        image::Rgb([9000, 21000, 30000]),
    )
    .save(&photograph)
    .unwrap();
    let original = fs::read(&photograph).unwrap();
    let catalog = files.path().join("editable-catalog.json");
    let make_app = || {
        StrehlApp::from_launch(
            128,
            LaunchOptions {
                headless: true,
                edit: true,
                preview: Some(photograph.clone()),
                catalog: Some(catalog.clone()),
                ..Default::default()
            },
        )
    };
    let mut app = make_app();
    let pump = Pump::new();
    let settled = |a: &StrehlApp| {
        a.editor.loaded.is_some()
            && a.editor.loading.is_none()
            && a.result_work.is_none()
            && a.pending_result.is_none()
            && a.editor.developing.is_none()
            && a.editor.pending_edit.is_none()
            && a.editor.saving.is_none()
            && a.editor.saved_revision == Some(a.editor.revision)
    };
    pump.until(&mut app, settled);
    assert!(app.editor.error.is_none(), "{:?}", app.editor.error);
    let before = app.editor.recipe.clone();
    app.editor.recipe.global.exposure = -0.75;
    app.editor
        .begin_edit(before.clone(), pump.started.elapsed().as_secs_f64());
    pump.until(&mut app, settled);
    assert!(app.undo_edit(false));
    assert_eq!(app.editor.recipe, before);
    assert!(app.undo_edit(true));
    assert_eq!(app.editor.recipe.global.exposure, -0.75);
    pump.until(&mut app, settled);
    assert!(app.catalog.photo_versions.is_empty());
    assert!(!app.photo_history_busy());
    assert!(app.editor.viewport.presenter.is_none());
    assert!(app.process_space.edit_mapping().is_none());
    assert_eq!(app.updates, 0);
    let reply = app.prepare_headless_shutdown(&pump.ctx).unwrap();
    assert_eq!(reply["state"], "shutdown_accepted");
    assert_eq!(reply["saved"], true);
    assert!(reply["warning"].is_null(), "{reply}");
    assert_eq!(fs::read(&photograph).unwrap(), original);
    drop(app);

    // Re-enter through actual loading rather than checking only an in-memory
    // or serialized recipe. This also checks shutdown left a readable catalog.
    let mut reopened = make_app();
    let second_pump = Pump::new();
    second_pump.until(&mut reopened, settled);
    assert!(
        reopened.editor.error.is_none(),
        "{:?}",
        reopened.editor.error
    );
    assert_eq!(reopened.editor.recipe.global.exposure, -0.75);
    assert!(reopened.catalog.photo_versions.is_empty());
    assert_eq!(fs::read(&photograph).unwrap(), original);
    assert_eq!(reopened.catalog.path.as_ref(), Some(&catalog));
}

#[test]
fn diagnostic_capture_launch_requires_a_saved_run_and_normalized_view() {
    let root = tempfile::tempdir().unwrap();
    let mut valid = LaunchOptions {
        offscreen: true,
        screenshot: Some(root.path().join("view.png")),
        open_run: Some(root.path().join("run")),
        diagnostic_map: Some("First two passes · correlation".into()),
        diagnostic_opacity: Some(0.5),
        diagnostic_sample: Some([0.5, 0.5]),
        photo_zoom: Some(8.0),
        ..Default::default()
    };
    validate_automation_launch(&mut valid).unwrap();
    valid.photo_zoom = Some(f32::NAN);
    assert!(validate_automation_launch(&mut valid).is_err());
    valid.photo_zoom = Some(1.0);
    valid.open_run = None;
    assert!(validate_automation_launch(&mut valid).is_err());
    valid.open_run = Some(root.path().join("run"));
    valid.diagnostic_sample = Some([1.1, 0.5]);
    assert!(validate_automation_launch(&mut valid).is_err());
    assert!(!root.path().join("view.png").exists());
}
