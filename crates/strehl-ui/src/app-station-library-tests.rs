//! The Library composed into the shell: the station replaces the tree, every
//! intent reaches its destination, the long work runs off the paint path, and
//! pointer motion rebuilds nothing.
use super::*;
use crate::library_station::tests::{catalog as library_catalog, draft};

const SIZE: egui::Vec2 = egui::vec2(1680.0, 1050.0);

fn app_with(catalog: crate::workspace_history::Catalog) -> StrehlApp {
    let mut app = StrehlApp::from_launch(4096, LaunchOptions::default());
    app.catalog = catalog;
    app.go_station(Station::Library);
    app
}
fn context() -> egui::Context {
    let ctx = egui::Context::default();
    crate::theme::install(&ctx);
    ctx
}
fn frame(
    app: &mut StrehlApp,
    ctx: &egui::Context,
    time: f64,
    events: Vec<egui::Event>,
) -> egui::FullOutput {
    ctx.run(
        egui::RawInput {
            screen_rect: Some(egui::Rect::from_min_size(egui::Pos2::ZERO, SIZE)),
            time: Some(time),
            events,
            ..Default::default()
        },
        |ctx| {
            app.sync_route();
            app.shell_shortcuts(ctx);
            app.shell_bars(ctx);
            app.workspace(ctx);
            app.shell_overlays(ctx);
        },
    )
}
fn texts(output: &egui::FullOutput) -> Vec<(String, egui::Rect)> {
    output
        .shapes
        .iter()
        .filter_map(|shape| match &shape.shape {
            egui::Shape::Text(text) => {
                Some((text.galley.text().to_owned(), text.visual_bounding_rect()))
            }
            _ => None,
        })
        .collect()
}
fn find(output: &egui::FullOutput, needle: &str) -> Option<egui::Rect> {
    texts(output)
        .into_iter()
        .find(|(t, _)| t == needle)
        .map(|(_, r)| r)
}
fn subject_named(app: &StrehlApp, name: &str) -> NodeId {
    app.catalog
        .nodes
        .iter()
        .find(|n| n.kind == NodeKind::Subject && n.name == name)
        .map(|n| n.id)
        .unwrap()
}
fn stack_of(app: &StrehlApp, subject: NodeId) -> NodeId {
    app.catalog
        .nodes
        .iter()
        .find(|n| n.kind == NodeKind::Stack && n.parent == Some(subject))
        .map(|n| n.id)
        .unwrap()
}

#[test]
fn the_library_route_shows_the_subject_grid_and_the_tree_moves_to_a_drawer() {
    let ctx = context();
    let mut app = app_with(library_catalog(12, None));
    frame(&mut app, &ctx, 0.0, vec![]);
    let out = frame(&mut app, &ctx, 0.1, vec![]);
    let all = find(&out, "All subjects").expect("the station's own list");
    assert!(all.left() < 232.0 && all.top() > 44.0, "{all:?}");
    assert!(find(&out, "Subject 000").is_some(), "a subject card");
    assert!(
        find(&out, "PROJECTS").is_none(),
        "the tree is not on the Library route"
    );
    assert_eq!(app.station_layout(Station::Library).sidebar, None);
    assert!(!app.station_paints_legacy(Station::Library));
    // Every function of the tree stays reachable from the drawer.
    app.open_project_tree();
    let out = frame(&mut app, &ctx, 0.2, vec![]);
    let tab = find(&out, "PROJECT TREE").expect("the drawer's tab");
    assert!(tab.left() > SIZE.x - 440.0);
    assert!(find(&out, "New stack").is_some(), "the tree's own commands");
    assert!(
        find(&out, "All subjects").is_some(),
        "the grid stays beside it"
    );
}

#[test]
fn opening_subjects_stacks_renders_and_versions_goes_to_their_stations() {
    let ctx = context();
    let mut app = app_with(library_catalog(8, None));
    frame(&mut app, &ctx, 0.0, vec![]);
    let subject = subject_named(&app, "Subject 001");
    app.library_intent(&ctx, LibraryIntent::OpenSubject(subject));
    assert_eq!(app.shell.navigator.route(), &Route::Subject(subject));
    assert_eq!(app.sidebar, Some(workspace::Sidebar::Projects));
    let out = frame(&mut app, &ctx, 0.1, vec![]);
    assert!(find(&out, "Subject 001").is_some(), "the subject page");
    assert!(
        find(&out, "new stack of this subject").is_some(),
        "its keys"
    );
    // The breadcrumb names the subject; Library leads back to the grid.
    let library = texts(&out)
        .into_iter()
        .find(|(t, r)| t == "Library" && r.bottom() <= 44.0)
        .unwrap()
        .1;
    for (offset, pressed) in [(0.2, true), (0.22, false)] {
        frame(
            &mut app,
            &ctx,
            offset,
            vec![
                egui::Event::PointerMoved(library.center()),
                egui::Event::PointerButton {
                    pos: library.center(),
                    button: egui::PointerButton::Primary,
                    pressed,
                    modifiers: egui::Modifiers::NONE,
                },
            ],
        );
    }
    assert_eq!(app.shell.navigator.route().key(), "library");
    app.library_intent(&ctx, LibraryIntent::OpenSubject(subject));
    app.library_intent(&ctx, LibraryIntent::Back);
    assert_eq!(app.shell.navigator.route().key(), "library");
    let stack = stack_of(&app, subject);
    app.library_intent(&ctx, LibraryIntent::OpenStack(stack));
    assert_eq!(app.shell.navigator.station(), Station::Stack);
    assert_eq!(app.active_stack, Some(stack));
    let directory = app.catalog.runs[0].directory.clone();
    let owner = app.catalog.stack_for_run(&directory).unwrap();
    app.library_intent(
        &ctx,
        LibraryIntent::OpenRender {
            stack: owner,
            run: directory,
        },
    );
    assert_eq!(app.shell.navigator.station(), Station::Develop);
    assert!(app.replay.is_some(), "the render is reopening");
    app.library_intent(&ctx, LibraryIntent::OpenCapture);
    assert_eq!(app.shell.navigator.station(), Station::Capture);
}

#[test]
fn new_stack_and_shoot_again_open_capture_with_their_subject() {
    let ctx = context();
    let mut app = app_with(library_catalog(4, None));
    let subject = subject_named(&app, "Subject 002");
    app.library_intent(
        &ctx,
        LibraryIntent::NewStackFromCamera {
            collection: None,
            subject: Some(subject),
        },
    );
    assert_eq!(app.shell.navigator.station(), Station::Capture);
    assert_eq!(
        app.capture_parent,
        Some(subject),
        "the capture lands in the subject"
    );
    let target = app.capture_target().unwrap();
    assert_eq!((target.subject, target.from_stack), (Some(subject), None));
    assert_eq!(target.subject_name, "Subject 002");
    let stack = stack_of(&app, subject);
    app.library_intent(&ctx, LibraryIntent::ShootAgain(stack));
    let target = app.capture_target().unwrap();
    assert_eq!(
        (target.subject, target.from_stack),
        (Some(subject), Some(stack))
    );
}

fn tick_until(app: &mut StrehlApp, ctx: &egui::Context, done: impl Fn(&StrehlApp) -> bool) {
    let started = Instant::now();
    while !done(app) && started.elapsed() < Duration::from_secs(10) {
        let _ = ctx.run(egui::RawInput::default(), |ctx| app.library_tick(ctx));
        std::thread::sleep(Duration::from_millis(5));
    }
    assert!(done(app), "the background work finished");
}

#[test]
fn importing_folders_makes_one_stack_per_folder_off_the_paint_path() {
    let files = tempfile::tempdir().unwrap();
    let bug = files.path().join("bug-3");
    let mut folders = Vec::new();
    for name in ["107MSDCF", "108MSDCF"] {
        let folder = bug.join(name);
        std::fs::create_dir_all(&folder).unwrap();
        for index in 0..3 {
            std::fs::write(folder.join(format!("DSC{index:05}.ARW")), [index as u8; 64]).unwrap();
        }
        folders.push(folder);
    }
    let empty = files.path().join("notes");
    std::fs::create_dir_all(&empty).unwrap();
    folders.push(empty);
    let ctx = context();
    let mut app = app_with(library_catalog(2, None));
    let collection = app
        .catalog
        .nodes
        .iter()
        .find(|n| n.name == "Minerals")
        .unwrap()
        .id;
    let groups = crate::workspace_history::import_plan(&folders);
    assert_eq!(groups.len(), 2, "camera folders group by their parent");
    app.library_intent(
        &ctx,
        LibraryIntent::ImportFolders {
            collection: Some(collection),
            subject: None,
            groups,
        },
    );
    let subject = subject_named(&app, "bug-3");
    assert_eq!(app.catalog.node(subject).unwrap().parent, Some(collection));
    assert!(app.library_loading(), "the scans run on workers");
    tick_until(&mut app, &ctx, |app| !app.library_loading());
    let stacks: Vec<_> = app
        .catalog
        .nodes
        .iter()
        .filter(|n| n.kind == NodeKind::Stack && n.parent == Some(subject))
        .collect();
    assert_eq!(stacks.len(), 2, "one stack per camera folder");
    assert!(
        stacks
            .iter()
            .all(|s| s.stack.as_ref().unwrap().sources.len() == 3)
    );
    assert!(
        app.shell
            .notices
            .iter()
            .any(|n| n.text.starts_with("Not added") && n.text.contains("notes")),
        "a folder without RAWs is reported, not added"
    );
    assert!(app.shell.notices.iter().any(|n| n.text == "Added 2 stacks"));
}

#[test]
fn locating_moved_sources_relocates_the_stack_from_a_worker_scan() {
    let files = tempfile::tempdir().unwrap();
    let moved = files.path().join("moved");
    std::fs::create_dir_all(&moved).unwrap();
    std::fs::write(moved.join("DSC00001.ARW"), [7_u8; 100]).unwrap();
    let mut catalog = crate::workspace_history::Catalog::default();
    let project = catalog.create_project("Insects").unwrap();
    let subject = catalog.create_subject(project, "Weevil").unwrap();
    let stack = catalog
        .create_stack(subject, "Dorsal", draft("/gone/100MSDCF", 100))
        .unwrap();
    let ctx = context();
    let mut app = app_with(catalog);
    app.library.locate = Some((stack, jobs::scan_stack(moved.clone())));
    tick_until(&mut app, &ctx, |app| app.library.locate.is_none());
    let source = &app
        .catalog
        .node(stack)
        .unwrap()
        .stack
        .as_ref()
        .unwrap()
        .source;
    assert_eq!(
        std::fs::canonicalize(source).unwrap(),
        std::fs::canonicalize(&moved).unwrap()
    );
    assert!(
        app.shell
            .notices
            .iter()
            .any(|n| n.text == "Found the stack's photographs")
    );
}

#[test]
fn renaming_editing_and_new_collections_go_through_the_undo_journal() {
    let ctx = context();
    let mut app = app_with(library_catalog(3, None));
    let subject = subject_named(&app, "Subject 000");
    app.library_intent(
        &ctx,
        LibraryIntent::EditSubject {
            id: subject,
            name: "Blue weevil".into(),
            edit: crate::workspace_history::SubjectEdit {
                notes: Some("Dorsal, 2.8x".into()),
                ..Default::default()
            },
        },
    );
    assert_eq!(app.catalog.node(subject).unwrap().name, "Blue weevil");
    // The app observes the journal once a frame, ordering it with other edits.
    app.observe_edits(&ctx);
    assert!(app.can_undo_edit(false), "the edit is undoable");
    app.undo_edit(false);
    assert_eq!(app.catalog.node(subject).unwrap().name, "Subject 000");
    // F2: the shell's rename window.
    app.library_intent(&ctx, LibraryIntent::Rename(subject));
    frame(&mut app, &ctx, 0.0, vec![]);
    let out = frame(&mut app, &ctx, 0.05, vec![]);
    assert!(find(&out, "Rename").is_some(), "the rename window");
    app.library.rename.as_mut().unwrap().name = "Garnet".into();
    let button = texts(&out)
        .into_iter()
        .filter(|(t, _)| t == "Rename")
        .map(|(_, r)| r)
        .max_by(|a, b| a.top().total_cmp(&b.top()))
        .unwrap();
    for (time, pressed) in [(0.1, true), (0.12, false)] {
        frame(
            &mut app,
            &ctx,
            time,
            vec![
                egui::Event::PointerMoved(button.center()),
                egui::Event::PointerButton {
                    pos: button.center(),
                    button: egui::PointerButton::Primary,
                    pressed,
                    modifiers: egui::Modifiers::NONE,
                },
            ],
        );
    }
    assert_eq!(app.catalog.node(subject).unwrap().name, "Garnet");
    assert!(app.library.rename.is_none());
    let before = app.catalog.nodes.len();
    app.library_intent(&ctx, LibraryIntent::NewCollection);
    assert_eq!(app.catalog.nodes.len(), before + 1);
    let made = app.library.rename.as_ref().unwrap().id;
    assert_eq!(app.catalog.node(made).unwrap().kind, NodeKind::Project);
}

#[test]
fn a_subject_route_resolves_by_name_or_id_and_falls_back_to_the_library() {
    let mut app = app_with(library_catalog(3, None));
    let subject = subject_named(&app, "Subject 001");
    app.library_launch_subject(Some("subject 001"));
    assert_eq!(app.shell.navigator.route(), &Route::Subject(subject));
    app.library_launch_subject(Some(&subject.to_string()));
    assert_eq!(app.shell.navigator.route(), &Route::Subject(subject));
    app.library_launch_subject(Some("no such subject"));
    assert_eq!(app.shell.navigator.route().key(), "library");
    assert!(
        app.shell
            .notices
            .iter()
            .any(|n| n.text.contains("no such subject"))
    );
}

#[test]
fn the_library_follows_the_theme_and_its_drawers_stay_legible_on_paper() {
    let ctx = context();
    crate::studio_theme::apply(
        &ctx,
        crate::studio_theme::ThemeName::Lightbox,
        crate::studio_theme::Surround::Theme,
        false,
    );
    let mut app = app_with(library_catalog(4, None));
    app.shell.prefs.theme = crate::studio_theme::ThemeName::Lightbox;
    frame(&mut app, &ctx, 0.0, vec![]);
    let out = frame(&mut app, &ctx, 0.1, vec![]);
    let paper = crate::studio_theme::LIGHTBOX.panel;
    assert!(
        out.shapes.iter().any(|s| matches!(&s.shape,
            egui::Shape::Rect(r) if r.fill == paper && r.rect.width() > 200.0 && r.rect.left() < 1.0
                && r.rect.top() >= 44.0)),
        "the station's list is on paper"
    );
    app.open_project_tree();
    let out = frame(&mut app, &ctx, 0.2, vec![]);
    let graphite = crate::studio_theme::GRAPHITE.panel;
    assert!(
        out.shapes.iter().any(|s| matches!(&s.shape,
            egui::Shape::Rect(r) if r.fill == graphite && r.rect.left() > SIZE.x - 440.0)),
        "the legacy tree is drawn in the Graphite scope"
    );
    // Badges sit on photographs: a dark plate with light capitals on paper too.
    let palette = LibraryPalette::from_tokens(&crate::studio_theme::LIGHTBOX);
    let graphite = LibraryPalette::graphite();
    assert_eq!(
        (palette.plate, palette.plate_ink),
        (graphite.plate, graphite.ink)
    );
    assert_ne!(palette.ink, graphite.ink);
}

#[test]
fn pointer_motion_over_the_library_rebuilds_nothing() {
    let pictures = tempfile::tempdir().unwrap();
    crate::library_station::tests::write_pictures(pictures.path(), 200);
    let ctx = context();
    let mut app = app_with(library_catalog(200, Some(pictures.path())));
    // Settle: the pictures in view decode on workers and upload once.
    let started = Instant::now();
    let mut time = 0.0;
    for _ in 0..3 {
        frame(&mut app, &ctx, time, vec![]);
        time += 0.05;
    }
    let mut uploads = 0;
    while app.library_loading() && started.elapsed() < Duration::from_secs(20) {
        uploads += frame(&mut app, &ctx, time, vec![]).textures_delta.set.len();
        time += 0.05;
        std::thread::sleep(Duration::from_millis(5));
    }
    assert!(!app.library_loading(), "the pictures in view arrived");
    assert!(
        uploads >= 10,
        "the control: pictures did upload ({uploads})"
    );
    frame(&mut app, &ctx, time, vec![]);
    let before = app.library.station.stats();
    let revision = app.library_revision();
    for step in 0..40 {
        let out = frame(
            &mut app,
            &ctx,
            time + 1.0 + step as f64 * 0.02,
            vec![egui::Event::PointerMoved(egui::pos2(
                300.0 + step as f32 * 30.0,
                200.0 + step as f32 * 15.0,
            ))],
        );
        assert!(
            out.textures_delta.set.is_empty() && out.textures_delta.free.is_empty(),
            "pointer motion uploads nothing (frame {step})"
        );
    }
    let after = app.library.station.stats();
    assert_eq!(app.library_revision(), revision);
    assert_eq!(
        (after.model_builds, after.list_builds),
        (before.model_builds, before.list_builds),
        "the model and the list are built once"
    );
    assert!(
        after.cards_painted < 40,
        "only the rows in view are laid out"
    );
}

#[cfg(windows)]
#[test]
fn the_storage_card_reads_its_volume() {
    let files = tempfile::tempdir().unwrap();
    let card = storage_card(&files.path().join("not-yet-made")).expect("a volume");
    assert!(card.total > 0 && card.free <= card.total);
    assert!(card.volume.ends_with(':'), "{}", card.volume);
    assert_eq!(card.compactable, None);
}

#[test]
fn a_folder_drop_on_the_library_imports_instead_of_opening_one_bracket() {
    let files = tempfile::tempdir().unwrap();
    let folder = files.path().join("100MSDCF");
    std::fs::create_dir_all(&folder).unwrap();
    std::fs::write(folder.join("DSC00001.ARW"), [1_u8; 64]).unwrap();
    let ctx = context();
    let mut app = app_with(library_catalog(2, None));
    let _ = ctx.run(
        egui::RawInput {
            screen_rect: Some(egui::Rect::from_min_size(egui::Pos2::ZERO, SIZE)),
            dropped_files: vec![egui::DroppedFile {
                path: Some(folder.clone()),
                ..Default::default()
            }],
            ..Default::default()
        },
        |ctx| app.update_workspace(ctx),
    );
    assert!(
        app.scan.is_none(),
        "the global drop did not open the folder as a bracket"
    );
    assert!(
        app.library.imports.running.is_some() || !app.library.imports.waiting.is_empty(),
        "the Library queued the folder"
    );
}

/// The Library with a large catalog, pointer sweeping the grid: CPU paint
/// plus tessellation per frame (not a GPU frame rate).
#[test]
#[ignore = "explicit CPU paint+tessellation benchmark of the Library station"]
fn benchmark_library_pointer_sweep() {
    for count in [40, 200] {
        let pictures = tempfile::tempdir().unwrap();
        crate::library_station::tests::write_pictures(pictures.path(), count);
        let ctx = context();
        let mut app = app_with(library_catalog(count, Some(pictures.path())));
        let started = Instant::now();
        let mut time = 0.0;
        let mut out = frame(&mut app, &ctx, time, vec![]);
        while (time < 0.25 || app.library_loading()) && started.elapsed() < Duration::from_secs(30)
        {
            time += 0.05;
            out = frame(&mut app, &ctx, time, vec![]);
            std::thread::sleep(Duration::from_millis(5));
        }
        assert!(!app.library_loading() && find(&out, "All subjects").is_some());
        let images = out
            .shapes
            .iter()
            .filter(|s| matches!(&s.shape, egui::Shape::Mesh(m) if m.texture_id != egui::TextureId::default()))
            .count();
        let mut times = Vec::new();
        for round in 0..5 {
            let started = Instant::now();
            for step in 0..80 {
                let phase = step as f32 / 79.0;
                let at = egui::pos2(300.0 + phase * 1300.0, 160.0 + phase * 800.0);
                let output = frame(
                    &mut app,
                    &ctx,
                    time + 1.0 + round as f64 + step as f64 / 120.0,
                    vec![egui::Event::PointerMoved(at)],
                );
                std::hint::black_box(ctx.tessellate(output.shapes, output.pixels_per_point));
            }
            times.push(started.elapsed().as_secs_f64() * 1000.0 / 80.0);
        }
        let stats = app.library.station.stats();
        eprintln!(
            "library, {count} subjects, {images} pictures in view, {} shapes: {:.3?} ms per frame; model builds {}, list builds {}",
            out.shapes.len(),
            times,
            stats.model_builds,
            stats.list_builds
        );
    }
}

/// The Library, a capture on the rig and a subject page through the real
/// offscreen path (`--route library`, `--route subject`), in each theme, for
/// the side-by-side check against the mockup references. The rig has no
/// launch option, so a capture is stood in for before every frame; so is the
/// disk. Ignored: needs a GPU; writes PNGs into `STREHL_P4_SHOTS`.
#[test]
#[ignore = "needs a GPU; writes PNGs into STREHL_P4_SHOTS"]
fn offscreen_library_rig_and_subject_pictures() {
    use crate::library_station::visual_tests::mockup_catalog;
    use crate::studio_theme::ThemeName;
    use studio_route::LaunchRoute;
    let shots = PathBuf::from(std::env::var_os("STREHL_P4_SHOTS").expect("STREHL_P4_SHOTS"));
    std::fs::create_dir_all(&shots).unwrap();
    let root = tempfile::tempdir().unwrap();
    let fixture = root.path().join("fixture.json");
    let (mut catalog, first) = mockup_catalog(root.path());
    let capturing = catalog.stacks_of(first)[0];
    let folder = catalog
        .node(capturing)
        .unwrap()
        .stack
        .as_ref()
        .unwrap()
        .source
        .clone();
    catalog.path = Some(fixture.clone());
    catalog.save().unwrap();
    let rig = crate::rig_status::RigSummary {
        initialized: true,
        online: true,
        camera_connected: true,
        camera_model: Some("ILCE-7CR".into()),
        phase: Some("capturing".into()),
        completed: Some(60),
        planned: Some(96),
        in_progress: Some(folder),
        ..Default::default()
    };
    let storage = StorageCard {
        volume: "D:".into(),
        free: 371_000_000_000,
        total: 1_900_000_000_000,
        compactable: Some((14, 410_000_000_000)),
    };
    for (name, route, theme, capture) in [
        ("library", LaunchRoute::Library, ThemeName::Graphite, false),
        (
            "library-rig",
            LaunchRoute::Library,
            ThemeName::Graphite,
            true,
        ),
        ("subject", LaunchRoute::Subject, ThemeName::Graphite, false),
        (
            "library-instrument",
            LaunchRoute::Library,
            ThemeName::Instrument,
            true,
        ),
        (
            "library-lightbox",
            LaunchRoute::Library,
            ThemeName::Lightbox,
            true,
        ),
        (
            "subject-instrument",
            LaunchRoute::Subject,
            ThemeName::Instrument,
            true,
        ),
        (
            "subject-lightbox",
            LaunchRoute::Subject,
            ThemeName::Lightbox,
            false,
        ),
    ] {
        let png = shots.join(format!("{name}.png"));
        let _ = std::fs::remove_file(&png);
        // A fresh copy per picture: the application may save its catalog.
        let copy = root.path().join(format!("{name}.json"));
        std::fs::copy(&fixture, &copy).unwrap();
        let launch = LaunchOptions {
            offscreen: true,
            screenshot: Some(png.clone()),
            catalog: Some(copy),
            capture_settings: Some(root.path().join(format!("{name}.capture.json"))),
            output_directory: Some(root.path().join("results")),
            route: Some(route),
            route_subject: (route == LaunchRoute::Subject).then(|| first.to_string()),
            size: Some([1680.0, 1050.0]),
            theme: Some(theme),
            ..Default::default()
        };
        super::offscreen::run_offscreen_with(launch, |app, time| {
            if capture {
                app.shell.stand_in_rig(rig.clone(), time);
            }
            app.library.storage = Some(storage.clone());
            app.library.storage_read = Some(Instant::now());
        })
        .unwrap();
        assert!(png.exists(), "{name}");
        eprintln!("wrote {}", png.display());
    }
}

/// A catalog whose subject has one stack with a saved render whose log
/// carries level-0 gate maps for its three planes, and one stack never
/// stacked.
fn signature_catalog(
    root: &std::path::Path,
) -> (crate::workspace_history::Catalog, NodeId, NodeId, NodeId) {
    use crate::workspace_history::{Catalog, Run, StackDraft};
    let mut catalog = Catalog::default();
    let project = catalog.create_project("Insects").unwrap();
    let subject = catalog.create_subject(project, "Weevil").unwrap();
    let directory = root.join("strehl-1-1-1");
    std::fs::create_dir_all(&directory).unwrap();
    let log = directory.join("render.log");
    let mut text = String::from("STREHL_UI_PROGRESS event=stage name=merge total=3\n");
    for (sequence, (frame, data)) in [(0, "ffff"), (1, "ff00"), (2, "0000")].iter().enumerate() {
        text.push_str(&format!(
            "STREHL_UI_PROGRESS event=diagnostic seq={} frame={frame} level=0 kind=gate-support scope=frame scale=linear width=2 height=1 min=0 max=1 folded=1 total=3 sampling=nearest data={data}\n",
            sequence + 1
        ));
    }
    std::fs::write(&log, text).unwrap();
    let run = Run {
        directory: directory.clone(),
        source: root.join("captures/dorsal"),
        output: directory.join("result.tiff"),
        log,
        label: "dorsal".into(),
        created: 100,
        status: "Saved".into(),
        frames: 3,
        sources: Vec::new(),
        settings: Default::default(),
        exposure: None,
        gate: None,
        workers: 1,
        pinned: false,
        imported: None,
    };
    let stacked = catalog
        .create_stack(subject, "Dorsal", StackDraft::from_run(&run))
        .unwrap();
    catalog.add_revision(stacked, run).unwrap();
    let fresh = catalog
        .create_stack(subject, "Lateral", draft("/captures/weevil/lateral", 1_000))
        .unwrap();
    (catalog, subject, stacked, fresh)
}

#[test]
fn subject_and_list_rows_get_their_signatures_from_a_worker_when_no_stack_renders() {
    let files = tempfile::tempdir().unwrap();
    let (catalog, subject, stacked, _) = signature_catalog(files.path());
    let ctx = context();
    let mut app = app_with(catalog);
    app.library_intent(&ctx, LibraryIntent::OpenSubject(subject));
    let colour = LibraryPalette::from_tokens(&studio_theme::tokens(&ctx))
        .ok
        .gamma_multiply(0.75);
    let bars = |out: &egui::FullOutput| {
        out.shapes
            .iter()
            .filter(|s| matches!(&s.shape, egui::Shape::Rect(r) if r.fill == colour))
            .count()
    };
    let out = frame(&mut app, &ctx, 0.0, vec![]);
    assert_eq!(bars(&out), 0, "nothing until the worker has read the run");
    assert!(app.library.signatures.pending(), "the painted row asked");
    assert!(app.library_loading(), "offscreen pictures wait for it");
    tick_until(&mut app, &ctx, |app| !app.library.signatures.pending());
    let out = frame(&mut app, &ctx, 0.1, vec![]);
    // Planes 0 and 1 have evidence above zero; plane 2 was observed at zero.
    assert_eq!(bars(&out), 2);
    assert_eq!(
        app.library.signatures.stacks().get(&stacked),
        Some(&vec![1.0, 0.5, 0.0])
    );
    assert_eq!(app.library.signatures.computed, 1);
    // The list view shows the subject's newest render from the cache.
    app.library_intent(&ctx, LibraryIntent::Back);
    app.library.station.view = crate::library_station::LibraryView::List;
    let out = frame(&mut app, &ctx, 0.2, vec![]);
    assert_eq!(bars(&out), 2);
    assert!(!app.library.signatures.pending());
    assert_eq!(app.library.signatures.computed, 1, "computed once");
}

#[test]
fn stack_and_stack_next_go_through_the_queue() {
    let files = tempfile::tempdir().unwrap();
    let (catalog, subject, stacked, fresh) = signature_catalog(files.path());
    let ctx = context();
    let mut app = app_with(catalog);
    app.engine = Some(files.path().join("engine.exe"));
    app.output = files.path().join("results");
    // Keep what is queued waiting, so the test reads the queue itself.
    app.activity_hub.queue.paused = true;
    // Right-click "Stack": only the stack without a render.
    app.library_intent(&ctx, LibraryIntent::QueueSubject(subject));
    assert_eq!(app.activity_hub.queue.stacks().collect::<Vec<_>>(), [fresh]);
    // Again: nothing new; it already waits.
    app.library_intent(&ctx, LibraryIntent::QueueSubject(subject));
    assert_eq!(app.activity_hub.queue.stacks().count(), 1);
    // A row's Stack queues that stack with its saved recipe.
    app.library_intent(&ctx, LibraryIntent::QueueStack(stacked));
    assert_eq!(
        app.activity_hub.queue.stacks().collect::<Vec<_>>(),
        [fresh, stacked]
    );
    // The subject page shows both rows as queued.
    app.library_intent(&ctx, LibraryIntent::OpenSubject(subject));
    let out = frame(&mut app, &ctx, 0.0, vec![]);
    assert_eq!(texts(&out).iter().filter(|(t, _)| t == "QUEUED").count(), 2);
}
