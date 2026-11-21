//! Library management in the shell: the delete confirmation from the menu
//! and the Delete key, removal through the window's undo, file deletion on a
//! scratch fixture, stacks in use kept, moves and merges undone, and what
//! Show in Explorer opens. Explorer itself is never started here.
use super::*;
use crate::library_delete::Disposal;
use crate::library_station::tests::{catalog as library_catalog, draft, run};
use crate::workspace_history::{Catalog, SourceIdentity};

const SIZE: egui::Vec2 = egui::vec2(1680.0, 1050.0);

fn app_with(catalog: Catalog) -> StrehlApp {
    let mut app = StrehlApp::from_launch(4096, LaunchOptions::default());
    app.catalog = catalog;
    app.go_station(super::studio_route::Station::Library);
    app
}
fn context() -> egui::Context {
    let ctx = egui::Context::default();
    crate::theme::install(&ctx);
    ctx
}
fn frame_with(
    app: &mut StrehlApp,
    ctx: &egui::Context,
    time: f64,
    events: Vec<egui::Event>,
    modifiers: egui::Modifiers,
) -> egui::FullOutput {
    ctx.run(
        egui::RawInput {
            screen_rect: Some(egui::Rect::from_min_size(egui::Pos2::ZERO, SIZE)),
            time: Some(time),
            events,
            modifiers,
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
fn frame(
    app: &mut StrehlApp,
    ctx: &egui::Context,
    time: f64,
    events: Vec<egui::Event>,
) -> egui::FullOutput {
    frame_with(app, ctx, time, events, egui::Modifiers::NONE)
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
fn containing(output: &egui::FullOutput, needle: &str) -> Option<String> {
    texts(output)
        .into_iter()
        .map(|(t, _)| t)
        .find(|t| t.contains(needle))
}
fn subject_named(app: &StrehlApp, name: &str) -> NodeId {
    app.catalog
        .nodes
        .iter()
        .find(|n| n.kind == NodeKind::Subject && n.name == name)
        .map(|n| n.id)
        .unwrap()
}
/// Press and release at `at`; `time` advances past double-click pairing.
fn click(
    app: &mut StrehlApp,
    ctx: &egui::Context,
    time: &mut f64,
    at: egui::Pos2,
    button: egui::PointerButton,
) {
    *time += 1.0;
    let event = |pressed| egui::Event::PointerButton {
        pos: at,
        button,
        pressed,
        modifiers: egui::Modifiers::NONE,
    };
    frame(
        app,
        ctx,
        *time,
        vec![egui::Event::PointerMoved(at), event(true)],
    );
    *time += 0.05;
    frame(app, ctx, *time, vec![event(false)]);
}
fn measured(app: &mut StrehlApp, ctx: &egui::Context) {
    let deadline = Instant::now() + Duration::from_secs(30);
    while app
        .library
        .manage
        .dialog
        .as_ref()
        .is_some_and(|d| d.measure.is_none())
    {
        app.library_poll_manage(ctx);
        assert!(Instant::now() < deadline, "the measurement never arrived");
        std::thread::sleep(Duration::from_millis(5));
    }
}

#[test]
fn delete_from_the_menu_states_what_leaves_and_removing_is_undone_by_ctrl_z() {
    let ctx = context();
    let mut app = app_with(library_catalog(12, None));
    let mut time = 0.0;
    frame(&mut app, &ctx, time, vec![]);
    time += 0.1;
    let out = frame(&mut app, &ctx, time, vec![]);
    let card = find(&out, "Subject 003").expect("a card").center();
    click(
        &mut app,
        &ctx,
        &mut time,
        card,
        egui::PointerButton::Secondary,
    );
    time += 0.1;
    let out = frame(&mut app, &ctx, time, vec![]);
    for label in [
        "Open",
        "Rename…",
        "Move to collection",
        "Merge into",
        "Delete…",
    ] {
        assert!(find(&out, label).is_some(), "the menu offers {label}");
    }
    let delete = find(&out, "Delete…").unwrap().center();
    click(
        &mut app,
        &ctx,
        &mut time,
        delete,
        egui::PointerButton::Primary,
    );
    assert!(
        app.library.manage.dialog.is_some(),
        "the confirmation opened"
    );
    // Measured on a worker: the dialog says so until the answer arrives.
    time += 0.1;
    let out = frame(&mut app, &ctx, time, vec![]);
    assert!(find(&out, "measuring…").is_some());
    assert!(app.library_loading(), "offscreen pictures wait for it");
    measured(&mut app, &ctx);
    time += 0.1;
    let out = frame(&mut app, &ctx, time, vec![]);
    assert!(
        find(
            &out,
            "1 subject, 1 stack, 1 render, 1 version and 1 export record leave the library."
        )
        .is_some(),
        "{:?}",
        texts(&out).iter().map(|t| &t.0).collect::<Vec<_>>()
    );
    // Off by default; this synthetic catalog has no deletable folders.
    let dialog = app.library.manage.dialog.as_ref().unwrap();
    assert!(!dialog.renders && !dialog.sources);
    let subject = subject_named(&app, "Subject 003");
    let remove = find(&out, "Remove from library")
        .expect("the action")
        .center();
    click(
        &mut app,
        &ctx,
        &mut time,
        remove,
        egui::PointerButton::Primary,
    );
    assert!(app.library.manage.dialog.is_none());
    assert!(app.catalog.node(subject).is_none(), "removed at once");
    app.observe_edits(&ctx);
    assert!(app.can_undo_edit(false));
    assert!(app.undo_edit(false));
    assert!(app.catalog.node(subject).is_some(), "Ctrl Z puts it back");
    assert!(app.undo_edit(true));
    assert!(
        app.catalog.node(subject).is_none(),
        "and redo removes it again"
    );
}

#[test]
fn ctrl_click_then_the_delete_key_asks_for_the_whole_selection() {
    let ctx = context();
    let mut app = app_with(library_catalog(12, None));
    let mut time = 0.0;
    frame(&mut app, &ctx, time, vec![]);
    time += 0.1;
    let out = frame(&mut app, &ctx, time, vec![]);
    for name in ["Subject 001", "Subject 002"] {
        let at = find(&out, name).unwrap().center();
        time += 1.0;
        let event = |pressed| egui::Event::PointerButton {
            pos: at,
            button: egui::PointerButton::Primary,
            pressed,
            modifiers: egui::Modifiers::COMMAND,
        };
        let ctrl = egui::Modifiers::COMMAND;
        frame_with(
            &mut app,
            &ctx,
            time,
            vec![egui::Event::PointerMoved(at), event(true)],
            ctrl,
        );
        time += 0.05;
        frame_with(&mut app, &ctx, time, vec![event(false)], ctrl);
    }
    assert_eq!(app.library.station.selection.ids().len(), 2);
    assert!(
        matches!(
            app.shell.navigator.route(),
            super::studio_route::Route::Library(_)
        ),
        "a Ctrl click selects; it does not open"
    );
    time += 0.1;
    let out = frame(&mut app, &ctx, time, vec![]);
    assert!(
        find(&out, "2 SUBJECTS SELECTED").is_some(),
        "the selection bar"
    );
    time += 0.1;
    frame(
        &mut app,
        &ctx,
        time,
        vec![egui::Event::Key {
            key: egui::Key::Delete,
            physical_key: None,
            pressed: true,
            repeat: false,
            modifiers: egui::Modifiers::NONE,
        }],
    );
    let dialog = app
        .library
        .manage
        .dialog
        .as_ref()
        .expect("the confirmation");
    assert_eq!(dialog.title, "Delete 2 subjects");
    assert_eq!(dialog.scope.subjects.len(), 2);
}

struct Disk {
    _root: tempfile::TempDir,
    capture: PathBuf,
    job: PathBuf,
}
/// One subject whose stack is a finished capture folder with one render.
fn scratch_catalog() -> (Catalog, NodeId, NodeId, Disk) {
    let root = tempfile::tempdir().unwrap();
    let capture = root
        .path()
        .join("captures")
        .join("stack-1795291999414-6430");
    let write = |path: &Path, bytes: usize| {
        std::fs::create_dir_all(path.parent().unwrap()).unwrap();
        std::fs::write(path, vec![1u8; bytes]).unwrap();
    };
    for name in ["manifest.json", "events.jsonl", "result.json"] {
        write(&capture.join(name), 10);
    }
    write(&capture.join("frame-000001.ARW.straw"), 2000);
    write(&capture.join("frame-000002.ARW.straw"), 2000);
    let job = root.path().join("out").join("strehl-1795292000000-77-0");
    write(&job.join("result.tiff"), 500);
    write(&job.join("render.log"), 20);
    let mut catalog = Catalog::default();
    let project = catalog.create_project("Insects").unwrap();
    let subject = catalog.create_subject(project, "Weevil").unwrap();
    let mut recipe = draft(&capture.to_string_lossy(), 0);
    recipe.sources = ["frame-000001.ARW.straw", "frame-000002.ARW.straw"]
        .iter()
        .map(|n| SourceIdentity {
            path: capture.join(n),
            bytes: 2000,
            modified_ns: None,
        })
        .collect();
    let stack = catalog.create_stack(subject, "Dorsal", recipe).unwrap();
    let mut render = run(
        &job.to_string_lossy(),
        &capture.to_string_lossy(),
        "Saved",
        5,
    );
    render.output = job.join("result.tiff");
    render.log = job.join("render.log");
    catalog.add_revision(stack, render).unwrap();
    (
        catalog,
        subject,
        stack,
        Disk {
            _root: root,
            capture,
            job,
        },
    )
}

#[test]
fn deleting_a_scratch_capture_needs_the_second_confirmation_and_takes_only_its_files() {
    let ctx = context();
    let (catalog, subject, _, disk) = scratch_catalog();
    let mut app = app_with(catalog);
    let mut time = 0.0;
    frame(&mut app, &ctx, time, vec![]);
    app.library_open_delete(&ctx, &[subject]);
    measured(&mut app, &ctx);
    {
        let dialog = app.library.manage.dialog.as_mut().unwrap();
        let measure = dialog.measure.as_mut().unwrap();
        assert_eq!(measure.render_total.files, 2);
        assert_eq!(measure.source_total.files, 5);
        assert_eq!(measure.source_total.bytes, 4030);
        // Never the owner's Recycle Bin from a test: permanent, as for a
        // capture larger than the bin.
        measure.render_total.disposal = Disposal::Permanent;
        measure.source_total.disposal = Disposal::Permanent;
        measure.source_total.permanent_because =
            Some("larger than the Recycle Bin on C: (it holds 1 KB)".into());
        dialog.renders = true;
        dialog.sources = true;
    }
    // The modal's first pass sizes it; the next one draws it.
    time += 0.1;
    frame(&mut app, &ctx, time, vec![]);
    time += 0.1;
    let out = frame(&mut app, &ctx, time, vec![]);
    assert!(
        containing(&out, "deleted permanently: larger than the Recycle Bin").is_some(),
        "the first step says it is permanent: {:?}",
        texts(&out).iter().map(|t| &t.0).collect::<Vec<_>>()
    );
    let next = find(&out, "Delete photographs…")
        .expect("the first step")
        .center();
    click(
        &mut app,
        &ctx,
        &mut time,
        next,
        egui::PointerButton::Primary,
    );
    assert!(
        app.library
            .manage
            .dialog
            .as_ref()
            .unwrap()
            .confirming_sources
    );
    assert!(disk.capture.exists(), "nothing yet");
    time += 0.1;
    let out = frame(&mut app, &ctx, time, vec![]);
    assert!(containing(&out, "They cannot be recovered.").is_some());
    let go = find(&out, "Delete them permanently")
        .expect("the second step")
        .center();
    click(&mut app, &ctx, &mut time, go, egui::PointerButton::Primary);
    assert!(app.catalog.node(subject).is_none());
    let deadline = Instant::now() + Duration::from_secs(30);
    while app.library_deleting().is_some() {
        app.library_poll_manage(&ctx);
        assert!(Instant::now() < deadline);
        std::thread::sleep(Duration::from_millis(5));
    }
    assert!(!disk.job.exists(), "the render folder");
    assert!(!disk.capture.exists(), "the capture held nothing else");
    // Undo puts the entry back; the files are gone, as the dialog said.
    app.observe_edits(&ctx);
    assert!(app.undo_edit(false));
    assert!(app.catalog.node(subject).is_some());
}

#[test]
fn stacks_in_use_stay_and_the_open_stack_keeps_its_files() {
    let ctx = context();
    let (mut catalog, subject, open, disk) = scratch_catalog();
    let capturing = catalog
        .create_stack(subject, "Lateral", draft("/captures/lateral", 10))
        .unwrap();
    let mut app = app_with(catalog);
    app.library.rig = Some(crate::library_station::RigCapture {
        subject: Some(subject),
        stack: Some(capturing),
        title: "Weevil".into(),
        detail: String::new(),
        progress: 0.5,
        picture: None,
    });
    app.active_stack = Some(open);
    app.library_open_delete(&ctx, &[subject]);
    let dialog = app.library.manage.dialog.as_ref().unwrap();
    assert_eq!(
        dialog.kept,
        vec![("Lateral".into(), "being captured now".into())]
    );
    assert!(
        dialog.scope.subjects.is_empty(),
        "the subject keeps the kept stack"
    );
    assert_eq!(dialog.scope.stacks, vec![open]);
    assert!(dialog.owned.renders.is_empty() && dialog.owned.sources.is_empty());
    assert!(
        dialog
            .owned
            .refused
            .iter()
            .all(|r| r.reason.contains("open in the workspace")),
        "{:?}",
        dialog.owned.refused
    );
    measured(&mut app, &ctx);
    app.library_confirm_delete(&ctx);
    assert!(app.catalog.node(open).is_none());
    assert_eq!(app.active_stack, None, "the window no longer points at it");
    assert!(app.catalog.node(subject).is_some() && app.catalog.node(capturing).is_some());
    assert!(disk.capture.join("frame-000001.ARW.straw").is_file());
    assert!(disk.job.is_dir());
}

#[test]
fn moves_merges_and_new_subjects_go_through_the_window_undo() {
    let ctx = context();
    let mut app = app_with(library_catalog(8, None));
    frame(&mut app, &ctx, 0.0, vec![]);
    let insects = app.catalog.nodes[0].id;
    let minerals = app.catalog.nodes[1].id;
    let s1 = subject_named(&app, "Subject 001");
    let s3 = subject_named(&app, "Subject 003");
    assert_eq!(app.catalog.node(s1).unwrap().parent, Some(minerals));
    app.library_intent(
        &ctx,
        LibraryIntent::MoveSubjects {
            subjects: vec![s1, s3],
            collection: insects,
        },
    );
    assert_eq!(app.catalog.node(s1).unwrap().parent, Some(insects));
    app.observe_edits(&ctx);
    assert!(app.undo_edit(false));
    assert_eq!(app.catalog.node(s1).unwrap().parent, Some(minerals));
    // Merge: one subject leaves, its stack joins; undo brings both back.
    let stack3 = app.catalog.stacks_of(s3)[0];
    app.library_intent(
        &ctx,
        LibraryIntent::MergeSubjects {
            into: s1,
            others: vec![s3],
        },
    );
    assert!(app.catalog.node(s3).is_none());
    assert_eq!(app.catalog.subject_of(stack3), Some(s1));
    app.observe_edits(&ctx);
    assert!(app.undo_edit(false));
    assert_eq!(app.catalog.subject_of(stack3), Some(s3));
    // A stack into a new subject beside its own, named for renaming.
    app.library_intent(&ctx, LibraryIntent::MoveStacksToNewSubject(vec![stack3]));
    let made = app.catalog.subject_of(stack3).unwrap();
    assert_ne!(made, s3);
    assert_eq!(app.catalog.node(made).unwrap().parent, Some(minerals));
    assert_eq!(app.catalog.node(made).unwrap().name, "Subject 003 2");
    assert!(
        app.library.rename.is_some(),
        "the new subject is named next"
    );
    // Moving to a stack's own place is refused and changes nothing.
    app.library_intent(
        &ctx,
        LibraryIntent::MoveStacks {
            stacks: vec![stack3],
            subject: stack3,
        },
    );
    assert_eq!(app.catalog.subject_of(stack3), Some(made));
}

#[test]
fn show_in_explorer_opens_the_folder_above_camera_folders_and_the_newest_render() {
    let mut catalog = Catalog::default();
    let project = catalog.create_project("Insects").unwrap();
    let subject = catalog.create_subject(project, "bug-1").unwrap();
    let a = catalog
        .create_stack(subject, "100MSDCF", draft("/macro/bug-1/100MSDCF", 1))
        .unwrap();
    let b = catalog
        .create_stack(subject, "101MSDCF", draft("/macro/bug-1/101MSDCF", 1))
        .unwrap();
    catalog
        .add_revision(
            a,
            run("/out/strehl-1-1-1", "/macro/bug-1/100MSDCF", "Saved", 10),
        )
        .unwrap();
    catalog
        .add_revision(
            b,
            run("/out/strehl-2-1-2", "/macro/bug-1/101MSDCF", "Saved", 20),
        )
        .unwrap();
    let app = app_with(catalog);
    let (path, _) = app.library_reveal_target(subject, false).unwrap();
    assert_eq!(path, PathBuf::from("/macro/bug-1"));
    let (path, _) = app.library_reveal_target(a, false).unwrap();
    assert_eq!(path, PathBuf::from("/macro/bug-1/100MSDCF"));
    let (path, fallback) = app.library_reveal_target(subject, true).unwrap();
    assert_eq!(path, PathBuf::from("/out/strehl-2-1-2/photograph.tiff"));
    assert_eq!(fallback, Some(PathBuf::from("/out/strehl-2-1-2")));
}
