//! A new subject from the Library (owner feedback, 2026-11-22): made empty
//! from the New subject menu, named (required, never another subject's
//! name), kept by the catalog, and undone by the window's Ctrl Z; and the
//! new subject of a stack move, which Ctrl Z no longer leaves behind empty.
use super::*;
use crate::library_station::{LibraryIntent, tests::catalog as library_catalog};
use crate::workspace_history::Catalog;

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
    fn visit(shape: &egui::Shape, found: &mut Vec<(String, egui::Rect)>) {
        match shape {
            egui::Shape::Text(text) => {
                found.push((text.galley.text().to_owned(), text.visual_bounding_rect()));
            }
            egui::Shape::Vec(shapes) => shapes.iter().for_each(|s| visit(s, found)),
            _ => {}
        }
    }
    let mut found = Vec::new();
    for shape in &output.shapes {
        visit(&shape.shape, &mut found);
    }
    found
}
fn find(output: &egui::FullOutput, needle: &str) -> Option<egui::Pos2> {
    texts(output)
        .into_iter()
        .find(|(t, _)| t == needle)
        .map(|(_, r)| r.center())
}
/// The last painted text equal to `needle` (a dialog paints above the view).
fn find_last(output: &egui::FullOutput, needle: &str) -> Option<egui::Pos2> {
    texts(output)
        .into_iter()
        .rfind(|(t, _)| t == needle)
        .map(|(_, r)| r.center())
}
fn containing(output: &egui::FullOutput, needle: &str) -> Option<String> {
    texts(output)
        .into_iter()
        .map(|(t, _)| t)
        .find(|t| t.contains(needle))
}
/// Press and release at `at`; `time` advances past double-click pairing.
fn click(app: &mut StrehlApp, ctx: &egui::Context, time: &mut f64, at: egui::Pos2) {
    *time += 1.0;
    let event = |pressed| egui::Event::PointerButton {
        pos: at,
        button: egui::PointerButton::Primary,
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
fn subjects(app: &StrehlApp) -> Vec<(NodeId, String)> {
    app.catalog
        .nodes
        .iter()
        .filter(|n| n.kind == NodeKind::Subject)
        .map(|n| (n.id, n.name.clone()))
        .collect()
}
fn subject_named(app: &StrehlApp, name: &str) -> NodeId {
    subjects(app)
        .into_iter()
        .find(|(_, n)| n == name)
        .map(|(id, _)| id)
        .unwrap()
}
fn key(key: egui::Key) -> Vec<egui::Event> {
    [true, false]
        .into_iter()
        .map(|pressed| egui::Event::Key {
            key,
            physical_key: None,
            pressed,
            repeat: false,
            modifiers: egui::Modifiers::NONE,
        })
        .collect()
}

#[test]
fn new_subject_names_must_be_given_valid_and_not_another_subjects() {
    let catalog = library_catalog(4, None);
    assert_eq!(
        format!("{:#}", catalog.new_subject_name("   ").unwrap_err()),
        "Name the subject"
    );
    assert!(
        format!(
            "{:#}",
            catalog.new_subject_name(" subject 002 ").unwrap_err()
        )
        .contains("\"Subject 002\" is already in the library"),
        "ignoring case and the spaces around it"
    );
    assert!(catalog.new_subject_name(&"x".repeat(161)).is_err());
    assert!(catalog.new_subject_name("Moth\u{7}").is_err());
    assert_eq!(
        catalog.new_subject_name("  Harvestman ").unwrap(),
        "Harvestman"
    );
    let third = catalog
        .nodes
        .iter()
        .find(|n| n.name == "Subject 003")
        .map(|n| n.id);
    assert_eq!(catalog.subject_named("SUBJECT 003"), third);
    assert_eq!(
        catalog.subject_named("Insects"),
        None,
        "a collection is no subject"
    );
}

#[test]
fn an_empty_subject_is_made_from_the_new_subject_menu_named_kept_and_undone() {
    let ctx = context();
    let file = tempfile::tempdir().unwrap();
    let mut app = app_with(library_catalog(8, None));
    app.catalog.path = Some(file.path().join("projects.json"));
    let mut time = 0.0;
    let output = frame(&mut app, &ctx, time, vec![]);
    let before = subjects(&app);
    let insects = app.catalog.nodes[0].id;
    // New subject > Empty subject…: the naming dialog, nothing made yet.
    click(
        &mut app,
        &ctx,
        &mut time,
        find(&output, "New subject").unwrap(),
    );
    let output = frame(&mut app, &ctx, time, vec![]);
    click(
        &mut app,
        &ctx,
        &mut time,
        find(&output, "Empty subject…").unwrap(),
    );
    let output = frame(&mut app, &ctx, time, vec![]);
    let draft = app.library.new_subject.clone().expect("the naming dialog");
    assert_eq!((draft.container, draft.stacks.len()), (Some(insects), 0));
    assert_eq!(subjects(&app), before);
    assert!(find(&output, "A name of its own: no other subject has it.").is_some());
    // Unnamed, or another subject's name: Make does nothing and says why.
    let make = find(&output, "Make subject").unwrap();
    click(&mut app, &ctx, &mut time, make);
    assert_eq!(subjects(&app), before, "a name is required");
    app.library.new_subject.as_mut().unwrap().name = "subject 005".into();
    let output = frame(&mut app, &ctx, time, vec![]);
    assert!(
        containing(&output, "\"Subject 005\" is already in the library").is_some(),
        "the clash is named"
    );
    click(&mut app, &ctx, &mut time, make);
    frame(&mut app, &ctx, time, key(egui::Key::Enter));
    assert_eq!(subjects(&app), before, "never another subject's name");
    // A name of its own, in the chosen collection.
    let minerals = app.catalog.nodes[1].id;
    app.library.new_subject.as_mut().unwrap().name = " Harvestman ".into();
    let output = frame(&mut app, &ctx, time, vec![]);
    click(
        &mut app,
        &ctx,
        &mut time,
        find_last(&output, "Minerals").unwrap(),
    );
    assert_eq!(
        app.library.new_subject.as_ref().unwrap().container,
        Some(minerals)
    );
    click(&mut app, &ctx, &mut time, make);
    assert!(app.library.new_subject.is_none(), "the dialog closed");
    let made = subject_named(&app, "Harvestman");
    let node = app.catalog.node(made).unwrap();
    assert_eq!(node.parent, Some(minerals));
    assert!(app.catalog.stacks_of(made).is_empty(), "empty");
    assert_eq!(app.library.station.selected, Some(made));
    let output = frame(&mut app, &ctx, time, vec![]);
    assert!(find(&output, "Harvestman").is_some(), "its card is shown");
    assert!(containing(&output, "no stacks yet").is_some());
    // Saved at once, and the catalog keeps an empty subject.
    let reloaded = Catalog::load(app.catalog.path.clone());
    assert_eq!(
        reloaded.node(made).map(|n| n.name.as_str()),
        Some("Harvestman")
    );
    // Ctrl Z takes it out of the library; Ctrl Shift Z brings it back.
    app.observe_edits(&ctx);
    assert!(app.undo_edit(false));
    assert!(app.catalog.node(made).is_none());
    assert_eq!(subjects(&app), before);
    assert!(app.undo_edit(true));
    assert_eq!(
        app.catalog.node(made).map(|n| (n.name.as_str(), n.parent)),
        Some(("Harvestman", Some(minerals)))
    );
}

#[test]
fn escape_closes_the_dialog_without_clearing_the_librarys_selection() {
    let ctx = context();
    let mut app = app_with(library_catalog(4, None));
    frame(&mut app, &ctx, 0.0, vec![]);
    let first = subjects(&app)[0].0;
    app.library.station.selection.set(&[first]);
    app.library_new_subject(None, Vec::new());
    frame(&mut app, &ctx, 1.0, key(egui::Key::Escape));
    assert!(app.library.new_subject.is_none());
    assert_eq!(app.library.station.selection.ids(), &[first]);
    // While it is open, what the Library asks waits (here: Delete).
    app.library_new_subject(None, Vec::new());
    app.library.station.selected = Some(first);
    frame(&mut app, &ctx, 2.0, key(egui::Key::Delete));
    assert!(app.library.manage.dialog.is_none());
}

#[test]
fn stacks_moved_into_a_new_subject_go_back_and_leave_no_empty_subject_on_undo() {
    let ctx = context();
    let mut app = app_with(library_catalog(6, None));
    frame(&mut app, &ctx, 0.0, vec![]);
    let s1 = subject_named(&app, "Subject 001");
    let s3 = subject_named(&app, "Subject 003");
    let moving = vec![app.catalog.stacks_of(s1)[0], app.catalog.stacks_of(s3)[0]];
    let before = subjects(&app);
    app.library_intent(&ctx, LibraryIntent::MoveStacksToNewSubject(moving.clone()));
    let mut draft = app.library.new_subject.take().unwrap();
    assert_eq!(draft.stacks, moving);
    draft.name = "Paired".into();
    app.library_make_subject(draft);
    let paired = subject_named(&app, "Paired");
    assert_eq!(app.catalog.stacks_of(paired), moving);
    app.observe_edits(&ctx);
    assert!(app.undo_edit(false));
    assert_eq!(app.catalog.subject_of(moving[0]), Some(s1));
    assert_eq!(app.catalog.subject_of(moving[1]), Some(s3));
    assert_eq!(subjects(&app), before, "no empty subject is left behind");
    assert!(app.undo_edit(true));
    assert_eq!(app.catalog.stacks_of(paired), moving);
    // A move that cannot be made changes nothing and makes no subject.
    let before = serde_json::to_value(&app.catalog.nodes).unwrap();
    app.library_make_subject(super::NewSubjectDraft {
        name: "Nowhere".into(),
        container: None,
        stacks: vec![paired],
        focus: false,
    });
    assert_eq!(serde_json::to_value(&app.catalog.nodes).unwrap(), before);
    assert!(
        !app.catalog.nodes.iter().any(|n| n.name == "Library"),
        "nor a collection for it"
    );
}
