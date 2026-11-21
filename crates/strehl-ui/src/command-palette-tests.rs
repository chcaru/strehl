use super::*;

fn index() -> Vec<Entry> {
    vec![
        Entry::new(
            Group::Actions,
            "Export again as last time",
            Command::Station(5),
        )
        .key("Ctrl Shift E"),
        Entry::new(Group::Actions, "Engine room", Command::EngineRoom).key("E"),
        Entry::new(Group::Actions, "Stop stacking", Command::StopStack),
        Entry::new(Group::GoTo, "Blue weevil / Dorsal", Command::OpenStack(3)).detail("Insects"),
        Entry::new(Group::GoTo, "Net-patterned beetle", Command::OpenStack(4)),
    ]
}

#[test]
fn prefixes_rank_before_word_prefixes_before_subsequences() {
    assert_eq!(rank("engine room", "eng"), Some(0));
    assert_eq!(rank("engine room", "roo"), Some(1));
    assert_eq!(rank("engine room", "erm"), Some(2));
    assert_eq!(rank("engine room", "xyz"), None);
    assert_eq!(rank("blue weevil / dorsal", "dors"), Some(1));
    assert_eq!(rank("anything", ""), Some(0));
}

#[test]
fn the_index_is_built_once_per_catalog_revision_and_matches_are_cached() {
    let mut palette = CommandPalette::default();
    palette.open();
    palette.ensure_index(7, index);
    palette.ensure_index(7, || panic!("an unchanged catalog must not rebuild"));
    assert_eq!(palette.builds, 1);
    palette.set_query("weevil");
    let first = palette.matches().to_vec();
    assert_eq!(first.len(), 1);
    assert_eq!(palette.entry(first[0]).command, Command::OpenStack(3));
    palette.ensure_index(8, index);
    assert_eq!(palette.builds, 2);
    palette.set_query("e");
    let matches = palette.matches().to_vec();
    let ranked: Vec<_> = matches
        .iter()
        .map(|&i| palette.entry(i).label.clone())
        .collect();
    assert_eq!(
        ranked[..2],
        [
            "Export again as last time".to_owned(),
            "Engine room".to_owned()
        ],
        "label prefixes first, in index order"
    );
}

fn run(
    ctx: &egui::Context,
    palette: &mut CommandPalette,
    time: f64,
    events: Vec<egui::Event>,
) -> (egui::FullOutput, Option<Command>) {
    let mut chosen = None;
    let output = ctx.run(
        egui::RawInput {
            screen_rect: Some(Rect::from_min_size(
                egui::Pos2::ZERO,
                egui::vec2(1680.0, 1050.0),
            )),
            time: Some(time),
            events,
            ..Default::default()
        },
        |ctx| {
            chosen = palette.show(ctx, 44.0, |command| *command != Command::StopStack);
        },
    );
    (output, chosen)
}
fn key(key: Key) -> egui::Event {
    egui::Event::Key {
        key,
        physical_key: Some(key),
        pressed: true,
        repeat: false,
        modifiers: egui::Modifiers::NONE,
    }
}

#[test]
fn arrows_move_enter_runs_and_escape_closes() {
    let ctx = egui::Context::default();
    crate::theme::install(&ctx);
    let mut palette = CommandPalette::default();
    palette.open();
    palette.ensure_index(1, index);
    // egui lays a new area out invisibly on its first frame.
    run(&ctx, &mut palette, 0.0, vec![]);
    let (output, _) = run(&ctx, &mut palette, 0.05, vec![]);
    let palette_rect = output
        .shapes
        .iter()
        .find_map(|shape| match &shape.shape {
            egui::Shape::Text(text) if text.galley.text() == "Engine room" => {
                Some(text.visual_bounding_rect())
            }
            _ => None,
        })
        .expect("entries are listed");
    assert!(
        palette_rect.top() > 150.0,
        "the palette opens below the top bar"
    );
    let (_, chosen) = run(
        &ctx,
        &mut palette,
        0.1,
        vec![key(Key::ArrowDown), key(Key::Enter)],
    );
    assert_eq!(chosen, Some(Command::EngineRoom));
    assert!(!palette.is_open(), "running a command closes the palette");
    palette.open();
    run(&ctx, &mut palette, 0.2, vec![]);
    run(&ctx, &mut palette, 0.3, vec![key(Key::Escape)]);
    assert!(!palette.is_open());
}

#[test]
fn an_unavailable_command_cannot_run_from_the_keyboard() {
    let ctx = egui::Context::default();
    crate::theme::install(&ctx);
    let mut palette = CommandPalette::default();
    palette.open();
    palette.ensure_index(1, index);
    palette.set_query("stop");
    let (_, chosen) = run(&ctx, &mut palette, 0.0, vec![key(Key::Enter)]);
    assert_eq!(chosen, None);
    assert!(palette.is_open());
}

#[test]
fn clicking_the_scrim_closes_without_running_anything() {
    let ctx = egui::Context::default();
    crate::theme::install(&ctx);
    let mut palette = CommandPalette::default();
    palette.open();
    palette.ensure_index(1, index);
    run(&ctx, &mut palette, 0.0, vec![]);
    run(&ctx, &mut palette, 0.05, vec![]);
    let at = egui::pos2(40.0, 900.0);
    let press = |pressed| egui::Event::PointerButton {
        pos: at,
        button: egui::PointerButton::Primary,
        pressed,
        modifiers: egui::Modifiers::NONE,
    };
    run(
        &ctx,
        &mut palette,
        0.1,
        vec![egui::Event::PointerMoved(at), press(true)],
    );
    let (_, chosen) = run(&ctx, &mut palette, 0.15, vec![press(false)]);
    assert_eq!(chosen, None);
    assert!(!palette.is_open());
}
