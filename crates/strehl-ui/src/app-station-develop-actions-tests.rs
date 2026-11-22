//! The Develop and Export action buttons, pressed through the shell after an
//! adjustment (owner feedback, 2026-11-21: "clicking Export... did nothing
//! after adjusting. same with Save version"). Every press must show
//! something: a station, a field, progress, a result or an error in words.
use super::*;

/// The shell fixture with its photograph on disk and a catalog beside it,
/// so a version can really be saved.
fn on_disk(dir: &Path) -> StrehlApp {
    let mut app = app(dir);
    let run = dir.join("run");
    std::fs::create_dir_all(&run).unwrap();
    let path = run.join("result.tiff");
    image::ImageBuffer::<image::Rgb<u16>, Vec<u16>>::from_fn(96, 64, |x, y| {
        image::Rgb([(4000 + x * 400) as u16, (9000 + y * 300) as u16, 12000])
    })
    .save(&path)
    .unwrap();
    let image = Arc::new(strehl_edit::load_tiff(&path).unwrap());
    app.catalog = crate::workspace_history::Catalog::load(Some(dir.join("projects.json")));
    app.result = Some(path.clone());
    app.image_path = Some(path.clone());
    app.editor.path = Some(path.clone());
    app.editor.loaded = Some(crate::edit_workspace::LoadedPhoto {
        coverage: None,
        image: Arc::clone(&image),
        preview: image,
        recipe: Default::default(),
        source: path,
        warnings: Vec::new(),
    });
    app.editor.saved_revision = Some(app.editor.revision);
    app
}

fn key(key: egui::Key) -> Vec<egui::Event> {
    vec![egui::Event::Key {
        key,
        physical_key: None,
        pressed: true,
        repeat: false,
        modifiers: Default::default(),
    }]
}

/// Drag the Exposure slider to the right, as a person adjusting would.
fn adjust_exposure(app: &mut StrehlApp, ctx: &egui::Context, time: &mut f64) {
    let output = frame(app, ctx, *time, vec![]);
    let label = find(&output, "Exposure").expect("the Exposure slider is drawn");
    let start = egui::pos2(label.left() + 150.0, label.center().y + 18.0);
    let mut press = vec![
        egui::Event::PointerMoved(start),
        egui::Event::PointerButton {
            pos: start,
            button: egui::PointerButton::Primary,
            pressed: true,
            modifiers: Default::default(),
        },
    ];
    for step in 1..=4 {
        *time += 1.0 / 60.0;
        frame(app, ctx, *time, std::mem::take(&mut press));
        let at = start + egui::vec2(step as f32 * 20.0, 0.0);
        press.push(egui::Event::PointerMoved(at));
    }
    let end = start + egui::vec2(100.0, 0.0);
    press.push(egui::Event::PointerButton {
        pos: end,
        button: egui::PointerButton::Primary,
        pressed: false,
        modifiers: Default::default(),
    });
    *time += 1.0 / 60.0;
    frame(app, ctx, *time, press);
    assert_ne!(
        app.editor.recipe.global.exposure, 0.0,
        "the drag did not adjust the photograph"
    );
}

/// Frames (with the photograph-history and station polls the app runs each
/// frame) until
/// `done`, or fail after ten seconds.
fn frames_until(
    app: &mut StrehlApp,
    ctx: &egui::Context,
    time: &mut f64,
    what: &str,
    done: impl Fn(&StrehlApp) -> bool,
) -> egui::FullOutput {
    let until = std::time::Instant::now() + std::time::Duration::from_secs(10);
    loop {
        *time += 1.0 / 60.0;
        let output = frame(app, ctx, *time, vec![]);
        app.poll_photo_history(ctx);
        app.poll_develop(ctx);
        if done(app) {
            return output;
        }
        assert!(std::time::Instant::now() < until, "{what} never happened");
        std::thread::sleep(std::time::Duration::from_millis(5));
    }
}

/// Develop with a photograph open and the Exposure slider just dragged.
fn adjusted(dir: &Path, ctx: &egui::Context, time: &mut f64) -> StrehlApp {
    let mut app = on_disk(dir);
    app.go_station(Station::Develop);
    for _ in 0..3 {
        *time += 0.05;
        frame(&mut app, ctx, *time, vec![]);
    }
    adjust_exposure(&mut app, ctx, time);
    app
}

/// Click the drawn `label`, then let two frames settle.
fn press(app: &mut StrehlApp, ctx: &egui::Context, time: &mut f64, label: &str) {
    *time += 0.05;
    let output = frame(app, ctx, *time, vec![]);
    let at = find(&output, label).unwrap_or_else(|| panic!("{label} is not drawn"));
    *time += 0.05;
    frame(app, ctx, *time, click(at.center()));
    for _ in 0..2 {
        *time += 0.05;
        frame(app, ctx, *time, vec![]);
    }
}

#[test]
fn export_goes_to_the_export_station_after_an_adjustment() {
    let dir = tempfile::tempdir().unwrap();
    let ctx = context();
    let mut time = 0.0;
    let mut app = adjusted(dir.path(), &ctx, &mut time);
    press(&mut app, &ctx, &mut time, "Export…");
    assert_eq!(
        app.shell.navigator.station(),
        Station::Export,
        "Export… left the photograph in Develop"
    );
}

#[test]
fn save_version_asks_for_a_name_and_saves_after_an_adjustment() {
    let dir = tempfile::tempdir().unwrap();
    let ctx = context();
    let mut time = 0.0;
    let mut app = adjusted(dir.path(), &ctx, &mut time);
    press(&mut app, &ctx, &mut time, "Save version");
    // The name field has the keyboard: Enter saves.
    time += 0.05;
    frame(&mut app, &ctx, time, key(egui::Key::Enter));
    frames_until(&mut app, &ctx, &mut time, "saving the version", |app| {
        !app.photo_history_busy() && !app.catalog.photo_versions.is_empty()
    });
    time += 0.05;
    let output = frame(&mut app, &ctx, time, vec![]);
    let history = app.photo_history_snapshot();
    assert!(history["error"].is_null(), "{}", history["error"]);
    let version = app.catalog.photo_versions.last().unwrap();
    assert_eq!(version.owner.output, app.editor.path.clone().unwrap());
    assert_ne!(
        version.name, "Export batch",
        "only an export batch saved a version"
    );
    // The saved version is listed where the press was made, and the press
    // ends in words.
    assert!(
        find(&output, &version.name).is_some(),
        "the saved version {:?} is not shown",
        version.name
    );
    let said = format!("Saved version \u{201c}{}\u{201d}", version.name);
    assert!(find(&output, &said).is_some(), "{said} is not shown");
}

/// Export with only `ticked` presets and this subject's folder chosen.
fn exporting(app: &mut StrehlApp, folder: &Path, ticked: &[&str]) {
    let library = app.export_pane.station.library.as_mut().unwrap();
    for preset in &mut library.presets {
        preset.enabled = ticked.contains(&preset.name.as_str());
    }
    // Without a stack in the library, the subject is the render folder.
    library.remember_destination("photo-run", folder).unwrap();
    app.go_station(Station::Export);
}

#[test]
fn export_writes_the_ticked_presets_and_says_where() {
    let dir = tempfile::tempdir().unwrap();
    let ctx = context();
    let mut time = 0.0;
    let mut app = adjusted(dir.path(), &ctx, &mut time);
    let folder = dir.path().join("exports");
    std::fs::create_dir_all(&folder).unwrap();
    exporting(&mut app, &folder, &["Web"]);
    press(&mut app, &ctx, &mut time, "Export 1 file");
    assert!(
        app.export_pane.station.batch.is_some() || app.export_pane.station.done.is_some(),
        "the press started nothing: {:?}",
        app.export_pane.station.error
    );
    frames_until(&mut app, &ctx, &mut time, "the export batch", |app| {
        app.export_pane.station.batch.is_none()
    });
    time += 0.05;
    let output = frame(&mut app, &ctx, time, vec![]);
    assert!(
        app.export_pane.station.error.is_none(),
        "{:?}",
        app.export_pane.station.error
    );
    let written: Vec<PathBuf> = std::fs::read_dir(&folder)
        .unwrap()
        .map(|entry| entry.unwrap().path())
        .collect();
    assert_eq!(written.len(), 1, "{written:?}");
    assert_eq!(written[0].extension().unwrap(), "jpg");
    let said = format!("Wrote {}", crate::display_path::display_path(&written[0]));
    assert!(find(&output, &said).is_some(), "{said} is not shown");
    assert!(find(&output, "OPEN FOLDER").is_some());
    assert_eq!(app.catalog.photo_exports.len(), 1);
    // The adjusted edit is the one exported (recorded against its version).
    let version = app
        .catalog
        .photo_versions
        .iter()
        .find(|v| v.id == app.catalog.photo_exports[0].version)
        .unwrap();
    assert_eq!(version.name, "Export batch");
}

#[test]
fn a_blocked_export_says_what_it_waits_for() {
    let dir = tempfile::tempdir().unwrap();
    let ctx = context();
    let mut time = 0.0;
    let mut app = on_disk(dir.path());
    let folder = dir.path().join("exports");
    std::fs::create_dir_all(&folder).unwrap();
    exporting(&mut app, &folder, &["Web", "HDR"]);
    // A newer render is opening in place of this photograph.
    app.result = Some(dir.path().join("newer").join("result.tiff"));
    press(&mut app, &ctx, &mut time, "Export 2 files");
    assert!(app.export_pane.station.batch.is_none());
    time += 0.05;
    let output = frame(&mut app, &ctx, time, vec![]);
    assert!(
        find(&output, "Wait for the photograph to finish opening").is_some(),
        "the press said nothing: {:?}",
        app.export_pane.station.error
    );
    let dismiss = find(&output, "DISMISS").unwrap();
    time += 0.05;
    frame(&mut app, &ctx, time, click(dismiss.center()));
    assert!(app.export_pane.station.error.is_none());
}

#[test]
fn a_develop_action_that_cannot_run_says_why_in_the_inspector() {
    let dir = tempfile::tempdir().unwrap();
    let ctx = context();
    let mut time = 0.0;
    let mut app = adjusted(dir.path(), &ctx, &mut time);
    // No look is chosen, so there is nothing to recalculate (an action
    // with no side effects outside the app, unlike a re-stack).
    app.handle_develop_intents(vec![station::DevelopIntent::Recalculate], time);
    let notice = app
        .edit_pane
        .develop
        .notice
        .clone()
        .expect("the refusal is kept in words");
    time += 0.05;
    let output = frame(&mut app, &ctx, time, vec![]);
    assert!(
        find(&output, &notice).is_some(),
        "{notice} is not in the inspector"
    );
    let dismiss = find(&output, "DISMISS").unwrap();
    time += 0.05;
    frame(&mut app, &ctx, time, click(dismiss.center()));
    assert!(app.edit_pane.develop.notice.is_none());
}
