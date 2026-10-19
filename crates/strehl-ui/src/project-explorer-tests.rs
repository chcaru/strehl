use super::*;
use crate::workspace_history::StackDraft;

fn fixture() -> (Catalog, NodeId, NodeId) {
    let mut catalog = Catalog::default();
    let project = catalog.create_project("Fieldwork").unwrap();
    let run: Run = serde_json::from_value(serde_json::json!({
        "directory":"render-one", "source":"capture-one", "output":"render-one/photo.tiff", "log":"render-one/render.log",
        "label":"Warmer light", "created":123, "status":"Saved", "frames":3,
        "settings":crate::jobs::RenderSettings::default(),"exposure":null,"gate":null,"workers":3
    })).unwrap();
    let stack = catalog
        .create_stack(project, "Bee antennae", StackDraft::from_run(&run))
        .unwrap();
    catalog.add_revision(stack, run).unwrap();
    (catalog, project, stack)
}
fn paint(
    explorer: &mut ProjectExplorer,
    catalog: &mut Catalog,
    ctx: &egui::Context,
    events: Vec<egui::Event>,
    busy: bool,
) -> (egui::FullOutput, ExplorerResponse) {
    let mut response = ExplorerResponse::default();
    let output = ctx.run(
        egui::RawInput {
            screen_rect: Some(egui::Rect::from_min_size(
                egui::Pos2::ZERO,
                egui::vec2(300.0, 700.0),
            )),
            events,
            ..Default::default()
        },
        |ctx| {
            egui::CentralPanel::default().show(ctx, |ui| {
                response = explorer.show(ui, catalog, busy);
            });
        },
    );
    (output, response)
}
fn find(output: &egui::FullOutput, needle: &str) -> Option<egui::Pos2> {
    fn visit(shape: &egui::Shape, needle: &str) -> Option<egui::Pos2> {
        match shape {
            egui::Shape::Text(t) if t.galley.text() == needle => {
                Some(t.pos + t.galley.size() * 0.5)
            }
            egui::Shape::Vec(v) => v.iter().find_map(|s| visit(s, needle)),
            _ => None,
        }
    }
    output.shapes.iter().find_map(|s| visit(&s.shape, needle))
}
fn click(
    explorer: &mut ProjectExplorer,
    catalog: &mut Catalog,
    ctx: &egui::Context,
    at: egui::Pos2,
    busy: bool,
) -> ExplorerResponse {
    let pointer = |pressed| egui::Event::PointerButton {
        pos: at,
        button: egui::PointerButton::Primary,
        pressed,
        modifiers: egui::Modifiers::NONE,
    };
    paint(
        explorer,
        catalog,
        ctx,
        vec![egui::Event::PointerMoved(at), pointer(true)],
        busy,
    );
    paint(explorer, catalog, ctx, vec![pointer(false)], busy).1
}
#[test]
fn rendered_stack_and_revision_have_distinct_open_actions() {
    let (mut catalog, _, stack) = fixture();
    let mut explorer = ProjectExplorer::default();
    let ctx = egui::Context::default();
    theme::install(&ctx);
    let (out, _) = paint(&mut explorer, &mut catalog, &ctx, vec![], false);
    let at = find(&out, "Bee antennae").expect("stack row is rendered");
    let opened = click(&mut explorer, &mut catalog, &ctx, at, false);
    assert!(matches!(opened.action,Some(ExplorerAction::OpenStack{id}) if id==stack));
    let (out, _) = paint(&mut explorer, &mut catalog, &ctx, vec![], false);
    let at = find(&out, "01  Warmer light").expect("saved revision row is rendered");
    let opened = click(&mut explorer, &mut catalog, &ctx, at, false);
    assert!(
        matches!(opened.action,Some(ExplorerAction::OpenRun{run}) if run.directory==std::path::Path::new("render-one"))
    );
}
#[test]
fn add_capture_targets_the_selected_project_and_busy_blocks_navigation() {
    let (mut catalog, project, _) = fixture();
    let mut explorer = ProjectExplorer::default();
    let ctx = egui::Context::default();
    let (out, _) = paint(&mut explorer, &mut catalog, &ctx, vec![], false);
    let at = find(&out, "New stack").expect("capture action exists");
    let request = click(&mut explorer, &mut catalog, &ctx, at, false);
    assert!(
        matches!(request.action,Some(ExplorerAction::NewCapture{parent:Some(id)}) if id==project)
    );
    let (out, _) = paint(&mut explorer, &mut catalog, &ctx, vec![], true);
    let at = find(&out, "Bee antennae").unwrap();
    assert!(
        click(&mut explorer, &mut catalog, &ctx, at, true)
            .action
            .is_none(),
        "running stack cannot be replaced by navigation"
    );
    let at = find(&out, "New stack").unwrap();
    assert!(
        click(&mut explorer, &mut catalog, &ctx, at, true)
            .action
            .is_none(),
        "running stack cannot be replaced by an import"
    );
}
#[test]
fn searching_a_revision_keeps_its_project_and_stack_context_visible() {
    let (mut catalog, project, _) = fixture();
    catalog
        .create_stack(
            project,
            "Unrelated flower",
            StackDraft::from_run(&catalog.runs[0].clone()),
        )
        .unwrap();
    let mut explorer = ProjectExplorer {
        filter: "warmer".into(),
        ..Default::default()
    };
    let ctx = egui::Context::default();
    let (out, _) = paint(&mut explorer, &mut catalog, &ctx, vec![], false);
    assert!(find(&out, "Fieldwork").is_some());
    assert!(find(&out, "Bee antennae").is_some());
    assert!(find(&out, "01  Warmer light").is_some());
    assert!(
        find(&out, "Unrelated flower").is_none(),
        "nonmatching sibling must not conceal a broken filter"
    );
}
#[test]
fn committed_project_name_is_an_identity_not_a_directory_operation() {
    let (mut catalog, project, _) = fixture();
    let evidence = serde_json::to_vec(&catalog.runs[0]).unwrap();
    let mut explorer = ProjectExplorer::default();
    explorer.edit(EditTarget::Node(project), "Different purpose / same files");
    let ctx = egui::Context::default();
    paint(&mut explorer, &mut catalog, &ctx, vec![], false);
    let at = explorer
        .editor_save_rect
        .expect("editor must expose a save action")
        .center();
    let response = click(&mut explorer, &mut catalog, &ctx, at, false);
    assert!(response.changed);
    assert_eq!(
        catalog.node(project).unwrap().name,
        "Different purpose / same files"
    );
    assert_eq!(serde_json::to_vec(&catalog.runs[0]).unwrap(), evidence);
}

#[test]
fn typing_after_new_project_replaces_the_placeholder_name() {
    let mut catalog = Catalog::default();
    let mut explorer = ProjectExplorer::default();
    explorer.edit(EditTarget::Project, "New project");
    let ctx = egui::Context::default();
    paint(&mut explorer, &mut catalog, &ctx, vec![], false);
    paint(
        &mut explorer,
        &mut catalog,
        &ctx,
        vec![egui::Event::Text("Orchid study".into())],
        false,
    );
    let at = explorer.editor_save_rect.unwrap().center();
    click(&mut explorer, &mut catalog, &ctx, at, false);
    assert_eq!(catalog.nodes.len(), 1);
    assert_eq!(
        catalog.nodes[0].name, "Orchid study",
        "typing must replace the suggested name without a preliminary Ctrl+A gesture"
    );
}

#[test]
fn searching_a_project_reveals_its_contents_instead_of_an_apparently_empty_project() {
    let (mut catalog, _, _) = fixture();
    let mut explorer = ProjectExplorer {
        filter: "fieldwork".into(),
        ..Default::default()
    };
    let ctx = egui::Context::default();
    let (out, _) = paint(&mut explorer, &mut catalog, &ctx, vec![], false);
    assert!(find(&out, "Fieldwork").is_some());
    assert!(find(&out, "Bee antennae").is_some());
    assert!(find(&out, "01  Warmer light").is_some());
    assert!(
        find(&out, "New project").is_some(),
        "creation commands have visible labels"
    );
    assert!(
        find(&out, "PROJECTS").is_none(),
        "the inner explorer must not duplicate its outer pane title"
    );
}

#[test]
fn revision_recipe_distinguishes_default_manual_and_automatic_exposure() {
    let (catalog, _, _) = fixture();
    let mut run = catalog.runs[0].clone();
    let default = revision_description(&run);
    assert!(default.contains("exposure: engine default"));
    assert!(default.contains("CA enabled"));
    assert!(
        !default.contains("CA corrected"),
        "enabled profile-guarded correction is not proof it applied"
    );
    run.exposure = Some(-0.75);
    assert!(revision_description(&run).contains("exposure: -0.75 EV"));
    run.exposure = None;
    run.settings.auto_exposure = true;
    let automatic = revision_description(&run);
    assert!(automatic.contains("exposure: automatic"));
    assert_ne!(
        automatic, default,
        "the two distinct recipes must not receive identical labels"
    );
}

fn panel_width(
    explorer: &mut ProjectExplorer,
    catalog: &mut Catalog,
    ctx: &egui::Context,
    frame: usize,
    events: Vec<egui::Event>,
    width: f32,
) -> f32 {
    let mut observed = 0.0;
    let _ = ctx.run(
        egui::RawInput {
            screen_rect: Some(egui::Rect::from_min_size(
                egui::Pos2::ZERO,
                egui::vec2(1440.0, 940.0),
            )),
            time: Some(frame as f64 / 60.0),
            events,
            ..Default::default()
        },
        |ctx| {
            observed = egui::SidePanel::left("actual-project-sidebar")
                .default_width(width)
                .width_range(220.0..=500.0)
                .resizable(true)
                .frame(egui::Frame::new().inner_margin(12))
                .show(ctx, |ui| {
                    explorer.show(ui, catalog, false);
                })
                .response
                .rect
                .width();
            egui::CentralPanel::default().show(ctx, |ui| {
                ui.label("Process remains beside Projects");
            });
        },
    );
    observed
}

#[test]
fn project_name_editor_cannot_ratchet_sidebar_width_during_idle_or_typing() {
    for width in [230.0, 280.0, 340.0] {
        let (mut catalog, project, _) = fixture();
        let mut explorer = ProjectExplorer::default();
        let ctx = egui::Context::default();
        theme::install(&ctx);
        panel_width(&mut explorer, &mut catalog, &ctx, 0, vec![], width);
        let stable = panel_width(&mut explorer, &mut catalog, &ctx, 1, vec![], width);
        explorer.edit(EditTarget::Node(project), "Fieldwork");
        let mut observed = Vec::new();
        for frame in 2..34 {
            let events = if frame == 4 {
                vec![egui::Event::Text(
                    "A long descriptive project name which should scroll inside the name field"
                        .into(),
                )]
            } else {
                vec![]
            };
            observed.push(panel_width(
                &mut explorer,
                &mut catalog,
                &ctx,
                frame,
                events,
                width,
            ));
        }
        assert!(
            explorer
                .edit
                .as_ref()
                .is_some_and(|edit| edit.value.starts_with("A long descriptive")),
            "the fixture must actually edit the focused text field"
        );
        explorer.edit = None;
        observed.push(panel_width(
            &mut explorer,
            &mut catalog,
            &ctx,
            35,
            vec![],
            width,
        ));
        assert!(
            observed.iter().all(|at| (*at - stable).abs() < 0.25),
            "opening, typing, idling and closing the editor must preserve sidebar width {stable}; got {observed:?}"
        );
    }
}

#[test]
fn project_move_picker_cannot_ratchet_sidebar_width() {
    for width in [230.0, 280.0, 340.0] {
        let (mut catalog, _, stack) = fixture();
        let mut explorer = ProjectExplorer::default();
        let ctx = egui::Context::default();
        theme::install(&ctx);
        panel_width(&mut explorer, &mut catalog, &ctx, 0, vec![], width);
        let stable = panel_width(&mut explorer, &mut catalog, &ctx, 1, vec![], width);
        explorer.moving = Some(stack);
        let widths: Vec<_> = (2..34)
            .map(|frame| panel_width(&mut explorer, &mut catalog, &ctx, frame, vec![], width))
            .collect();
        assert!(
            widths.iter().all(|at| (*at - stable).abs() < 0.25),
            "move picker must fit its fixed sidebar: {stable} became {widths:?}"
        );
    }
}

#[test]
fn bounded_move_picker_still_opens_and_commits_the_chosen_folder() {
    let (mut catalog, _, stack) = fixture();
    let target = catalog.create_project("Second project").unwrap();
    let mut explorer = ProjectExplorer {
        moving: Some(stack),
        ..Default::default()
    };
    let ctx = egui::Context::default();
    theme::install(&ctx);
    let (out, _) = paint(&mut explorer, &mut catalog, &ctx, vec![], false);
    let at = find(&out, "Move to…").expect("fixed move row has a visible dropdown");
    click(&mut explorer, &mut catalog, &ctx, at, false);
    let (out, _) = paint(&mut explorer, &mut catalog, &ctx, vec![], false);
    let target_at = find(&out, &format!("Second project  · {target}"))
        .expect("dropdown contents must escape the fixed row's clip");
    let response = click(&mut explorer, &mut catalog, &ctx, target_at, false);
    assert!(response.changed);
    assert_eq!(catalog.node(stack).unwrap().parent, Some(target));
    assert!(explorer.moving.is_none());
}

fn selected_row(output: &egui::FullOutput, at: egui::Pos2) -> Option<egui::Rect> {
    output.shapes.iter().find_map(|shape| match &shape.shape {
        egui::Shape::Rect(rect) if rect.fill == SELECTED && rect.rect.contains(at) => {
            Some(rect.rect)
        }
        _ => None,
    })
}
#[test]
fn selected_stack_and_saved_result_have_persistent_full_width_rows() {
    let (mut catalog, _, stack) = fixture();
    let mut explorer = ProjectExplorer::default();
    let ctx = egui::Context::default();
    let (out, _) = paint(&mut explorer, &mut catalog, &ctx, vec![], false);
    let at = find(&out, "Bee antennae").unwrap();
    click(&mut explorer, &mut catalog, &ctx, at, false);
    let (out, _) = paint(&mut explorer, &mut catalog, &ctx, vec![], false);
    let selected = selected_row(&out, at).expect("selected stack is visibly highlighted");
    assert!(
        selected.width() > 260.0,
        "selection spans the row, not just its text"
    );
    let result = find(&out, "01  Warmer light").unwrap();
    // Selecting the otherwise empty left edge must open the result as well.
    let opened = click(
        &mut explorer,
        &mut catalog,
        &ctx,
        egui::pos2(selected.left() + 3.0, result.y),
        false,
    );
    assert!(matches!(
        opened.action,
        Some(ExplorerAction::OpenRun { .. })
    ));
    assert_eq!(catalog.selected, Some(stack));
    for _ in 0..4 {
        let (out, _) = paint(&mut explorer, &mut catalog, &ctx, vec![], false);
        assert!(
            selected_row(&out, result).is_some(),
            "result highlight survives idle frames"
        );
        assert!(
            selected_row(&out, at).is_none(),
            "owning stack must not masquerade as selected result"
        );
    }
}
#[test]
fn new_project_leads_to_a_local_new_stack_action() {
    let mut catalog = Catalog::default();
    let mut explorer = ProjectExplorer::default();
    let ctx = egui::Context::default();
    let (out, _) = paint(&mut explorer, &mut catalog, &ctx, vec![], false);
    let at = find(&out, "New project").unwrap();
    click(&mut explorer, &mut catalog, &ctx, at, false);
    paint(&mut explorer, &mut catalog, &ctx, vec![], false);
    paint(
        &mut explorer,
        &mut catalog,
        &ctx,
        vec![egui::Event::Text("Rain garden".into())],
        false,
    );
    let save = explorer.editor_save_rect.unwrap().center();
    click(&mut explorer, &mut catalog, &ctx, save, false);
    let (out, _) = paint(&mut explorer, &mut catalog, &ctx, vec![], false);
    let project = catalog.selected.unwrap();
    assert_eq!(catalog.node(project).unwrap().name, "Rain garden");
    let at = find(&out, "Add first stack").expect("empty project offers its next action locally");
    assert!(
        matches!(click(&mut explorer, &mut catalog, &ctx, at, false).action, Some(ExplorerAction::NewCapture{parent:Some(id)}) if id == project)
    );
}
#[test]
fn tree_icons_and_editor_actions_do_not_depend_on_symbol_font_glyphs() {
    let (mut catalog, project, _) = fixture();
    let mut explorer = ProjectExplorer::default();
    explorer.edit(EditTarget::Node(project), "Fieldwork");
    let ctx = egui::Context::default();
    let (out, _) = paint(&mut explorer, &mut catalog, &ctx, vec![], false);
    for symbol in ["◇", "▱", "▤", "⌄", "›", "✓", "×", "•", "◦"] {
        assert!(
            find(&out, symbol).is_none(),
            "{symbol} should be vector geometry, not a missing glyph box"
        );
    }
    assert!(
        find(&out, "project").is_some(),
        "kind labels distinguish projects from stacks"
    );
    assert!(find(&out, "1 result").is_some());
}
#[test]
fn undo_redo_organization_preserves_recipe_and_saved_evidence() {
    let (mut catalog, project, stack) = fixture();
    let mut explorer = ProjectExplorer::default();
    let ctx = egui::Context::default();
    let evidence = serde_json::to_vec(&catalog.runs).unwrap();
    explorer.edit(EditTarget::Node(project), "Renamed study");
    paint(&mut explorer, &mut catalog, &ctx, vec![], false);
    let save = explorer.editor_save_rect.unwrap().center();
    click(&mut explorer, &mut catalog, &ctx, save, false);
    assert!(explorer.can_undo());
    assert!(explorer.history_revision() > 0);
    catalog
        .node_mut(stack)
        .unwrap()
        .stack
        .as_mut()
        .unwrap()
        .settings
        .frame_limit = Some(2);
    assert!(explorer.undo(&mut catalog));
    assert_eq!(catalog.node(project).unwrap().name, "Fieldwork");
    assert_eq!(
        catalog
            .node(stack)
            .unwrap()
            .stack
            .as_ref()
            .unwrap()
            .settings
            .frame_limit,
        Some(2),
        "organization undo must not restore a historical recipe"
    );
    assert_eq!(serde_json::to_vec(&catalog.runs).unwrap(), evidence);
    assert!(explorer.can_redo());
    assert!(explorer.redo(&mut catalog));
    assert_eq!(catalog.node(project).unwrap().name, "Renamed study");
    assert_eq!(serde_json::to_vec(&catalog.runs).unwrap(), evidence);
}
#[test]
fn new_engine_revision_invalidates_organization_undo_before_it_can_remove_evidence() {
    let (mut catalog, project, stack) = fixture();
    let mut explorer = ProjectExplorer::default();
    let ctx = egui::Context::default();
    explorer.edit(EditTarget::Node(project), "Renamed study");
    paint(&mut explorer, &mut catalog, &ctx, vec![], false);
    let save = explorer.editor_save_rect.unwrap().center();
    click(&mut explorer, &mut catalog, &ctx, save, false);
    assert!(explorer.can_undo());
    let mut fresh = catalog.runs[0].clone();
    fresh.directory = "render-two".into();
    fresh.output = "render-two/photo.tiff".into();
    fresh.log = "render-two/render.log".into();
    catalog.add_revision(stack, fresh.clone()).unwrap();
    assert!(
        !explorer.undo(&mut catalog),
        "new evidence is an undo boundary, even before the next explorer paint"
    );
    assert!(catalog.runs.iter().any(|r| r.directory == fresh.directory));
    assert_eq!(catalog.node(stack).unwrap().revisions.len(), 2);
}

#[test]
fn folder_context_menu_offers_a_local_new_stack_and_targets_that_folder() {
    let (mut catalog, project, _) = fixture();
    let folder = catalog.create_folder(project, "Autumn captures").unwrap();
    let mut explorer = ProjectExplorer::default();
    let ctx = egui::Context::default();
    let (out, _) = paint(&mut explorer, &mut catalog, &ctx, vec![], false);
    let at = find(&out, "Autumn captures").unwrap();
    for pressed in [true, false] {
        paint(
            &mut explorer,
            &mut catalog,
            &ctx,
            vec![
                egui::Event::PointerMoved(at),
                egui::Event::PointerButton {
                    pos: at,
                    button: egui::PointerButton::Secondary,
                    pressed,
                    modifiers: egui::Modifiers::NONE,
                },
            ],
            false,
        );
    }
    let (out, _) = paint(&mut explorer, &mut catalog, &ctx, vec![], false);
    let at = find(&out, "New stack…").expect("folder context menu provides a local capture action");
    let opened = click(&mut explorer, &mut catalog, &ctx, at, false);
    assert!(
        matches!(opened.action, Some(ExplorerAction::NewCapture { parent: Some(id) }) if id == folder)
    );
}
#[test]
fn creating_project_is_reversible_without_reusing_ids_or_touching_captures() {
    let (mut catalog, _, stack) = fixture();
    let mut explorer = ProjectExplorer::default();
    let ctx = egui::Context::default();
    let evidence = serde_json::to_vec(&catalog.runs).unwrap();
    explorer.edit(EditTarget::Project, "Second project");
    paint(&mut explorer, &mut catalog, &ctx, vec![], false);
    let save = explorer.editor_save_rect.unwrap().center();
    click(&mut explorer, &mut catalog, &ctx, save, false);
    let created = catalog.selected.unwrap();
    assert!(catalog.node(created).is_some());
    assert!(explorer.undo(&mut catalog));
    assert!(catalog.node(created).is_none());
    assert!(catalog.node(stack).is_some());
    assert!(explorer.redo(&mut catalog));
    assert_eq!(catalog.node(created).unwrap().name, "Second project");
    assert_eq!(serde_json::to_vec(&catalog.runs).unwrap(), evidence);
    let next = catalog.create_project("Third project").unwrap();
    assert!(
        next > created,
        "redo must preserve the monotonic node identity allocator"
    );
}
