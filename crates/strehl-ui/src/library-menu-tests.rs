//! The Library's management surfaces: the selection model, the card menu
//! and its submenus, the selection bar, keys and dragging onto a
//! collection, on the station's synthetic catalog.
use super::*;
use crate::library_station::tests::{Harness, catalog as library_catalog, find};
use crate::library_station::{LibraryIntent, LibraryView};
use eframe::egui::{Event, Key, Modifiers, PointerButton, RawInput};

fn subject(catalog: &Catalog, name: &str) -> NodeId {
    catalog
        .nodes
        .iter()
        .find(|n| n.kind == NodeKind::Subject && n.name == name)
        .map(|n| n.id)
        .unwrap()
}
fn press(
    harness: &mut Harness,
    catalog: &Catalog,
    at: Pos2,
    button: PointerButton,
    modifiers: Modifiers,
) -> Option<LibraryIntent> {
    harness.time += 1.0;
    let event = |pressed| Event::PointerButton {
        pos: at,
        button,
        pressed,
        modifiers,
    };
    let input = |events| RawInput {
        events,
        modifiers,
        ..Default::default()
    };
    let (_, first) = harness.frame_with(catalog, input(vec![Event::PointerMoved(at), event(true)]));
    let (_, second) = harness.frame_with(catalog, input(vec![event(false)]));
    second.or(first)
}
fn key(
    harness: &mut Harness,
    catalog: &Catalog,
    key: Key,
    modifiers: Modifiers,
) -> Option<LibraryIntent> {
    let (_, intent) = harness.frame_with(
        catalog,
        RawInput {
            events: vec![Event::Key {
                key,
                physical_key: None,
                pressed: true,
                repeat: false,
                modifiers,
            }],
            modifiers,
            ..Default::default()
        },
    );
    intent
}
fn everywhere(output: &egui::FullOutput, text: &str) -> Vec<Pos2> {
    output
        .shapes
        .iter()
        .filter_map(|s| match &s.shape {
            egui::Shape::Text(t) if t.galley.text() == text => Some(t.pos + t.galley.size() * 0.5),
            _ => None,
        })
        .collect()
}
fn drawn(harness: &mut Harness, catalog: &Catalog, text: &str) -> Pos2 {
    let (output, _) = harness.frame(catalog, vec![]);
    find(&output, text).unwrap_or_else(|| panic!("{text} is drawn"))
}

#[test]
fn ctrl_toggles_shift_selects_a_range_and_a_plain_click_is_not_a_selection() {
    let order = [1, 2, 3, 4, 5];
    let mut selection = Selection::default();
    assert!(selection.click(2, Modifiers::COMMAND, &order));
    assert!(selection.click(4, Modifiers::COMMAND, &order));
    assert_eq!(selection.ids(), &[2, 4]);
    assert!(
        selection.click(2, Modifiers::COMMAND, &order),
        "toggles off"
    );
    assert_eq!(selection.ids(), &[4]);
    // Shift: the range from the last clicked (2, though now unselected), in
    // the shown order, as Explorer does.
    assert!(selection.click(1, Modifiers::SHIFT, &order));
    assert_eq!(selection.ids(), &[1, 2]);
    assert!(selection.click(4, Modifiers::SHIFT, &order));
    assert_eq!(selection.ids(), &[2, 3, 4], "the anchor stays");
    // Ctrl Shift adds a range to what is selected.
    selection.set(&[5]);
    assert!(selection.click(4, Modifiers::COMMAND | Modifiers::SHIFT, &order));
    assert_eq!(selection.ids(), &[5, 4]);
    assert!(!selection.click(3, Modifiers::NONE, &order));
    // An action on a selected item takes the selection; else the item.
    assert_eq!(selection.targets(4), vec![5, 4]);
    assert_eq!(selection.targets(1), vec![1]);
    selection.retain_in(&[1, 2, 4]);
    assert_eq!(selection.ids(), &[4]);
    assert_eq!(selection.len(), 1);
}

#[test]
fn ctrl_click_selects_without_opening_ctrl_a_takes_all_shown_and_escape_clears() {
    let catalog = library_catalog(12, None);
    let mut harness = Harness::new();
    harness.frame(&catalog, vec![]);
    let at = drawn(&mut harness, &catalog, "Subject 004");
    let intent = press(
        &mut harness,
        &catalog,
        at,
        PointerButton::Primary,
        Modifiers::COMMAND,
    );
    assert_eq!(intent, None, "a Ctrl click does not open the subject");
    assert_eq!(
        harness.station.selection.ids(),
        &[subject(&catalog, "Subject 004")]
    );
    // The selection shows: the bar names it, the card carries a tick.
    let (output, _) = harness.frame(&catalog, vec![]);
    assert!(find(&output, "1 SUBJECT SELECTED").is_some());
    assert_eq!(
        key(&mut harness, &catalog, Key::A, Modifiers::COMMAND),
        None
    );
    assert_eq!(harness.station.selection.ids().len(), 12);
    let (output, _) = harness.frame(&catalog, vec![]);
    assert!(find(&output, "12 SUBJECTS SELECTED").is_some());
    key(&mut harness, &catalog, Key::Escape, Modifiers::NONE);
    assert!(harness.station.selection.is_empty());
    // A plain click still opens, and clears any selection.
    press(
        &mut harness,
        &catalog,
        at,
        PointerButton::Primary,
        Modifiers::COMMAND,
    );
    let other = drawn(&mut harness, &catalog, "Subject 005");
    assert_eq!(
        press(
            &mut harness,
            &catalog,
            other,
            PointerButton::Primary,
            Modifiers::NONE
        ),
        Some(LibraryIntent::OpenSubject(subject(&catalog, "Subject 005")))
    );
    assert!(harness.station.selection.is_empty());
}

#[test]
fn the_delete_key_asks_for_the_selection_else_the_card_under_the_cursor() {
    let catalog = library_catalog(12, None);
    let mut harness = Harness::new();
    harness.frame(&catalog, vec![]);
    assert_eq!(
        key(&mut harness, &catalog, Key::Delete, Modifiers::NONE),
        None
    );
    // Arrow keys move the cursor; Delete asks for that card.
    key(&mut harness, &catalog, Key::ArrowRight, Modifiers::NONE);
    let first = harness.station.visible()[0];
    assert_eq!(
        key(&mut harness, &catalog, Key::Delete, Modifiers::NONE),
        Some(LibraryIntent::Delete(vec![first]))
    );
    let a = drawn(&mut harness, &catalog, "Subject 002");
    press(
        &mut harness,
        &catalog,
        a,
        PointerButton::Primary,
        Modifiers::COMMAND,
    );
    let b = drawn(&mut harness, &catalog, "Subject 003");
    press(
        &mut harness,
        &catalog,
        b,
        PointerButton::Primary,
        Modifiers::COMMAND,
    );
    assert_eq!(
        key(&mut harness, &catalog, Key::Delete, Modifiers::NONE),
        Some(LibraryIntent::Delete(vec![
            subject(&catalog, "Subject 002"),
            subject(&catalog, "Subject 003")
        ]))
    );
    // F2 renames the cursor card.
    assert!(matches!(
        key(&mut harness, &catalog, Key::F2, Modifiers::NONE),
        Some(LibraryIntent::Rename(_))
    ));
}

#[test]
fn the_card_menu_manages_the_subject_and_its_submenu_moves_it() {
    let catalog = library_catalog(12, None);
    let mut harness = Harness::new();
    harness.frame(&catalog, vec![]);
    let s3 = subject(&catalog, "Subject 003");
    let at = drawn(&mut harness, &catalog, "Subject 003");
    assert_eq!(
        press(
            &mut harness,
            &catalog,
            at,
            PointerButton::Secondary,
            Modifiers::NONE
        ),
        None
    );
    let labels: Vec<String> = harness
        .station
        .menu_entries()
        .expect("the menu is open")
        .iter()
        .filter_map(|e| match e {
            MenuEntry::Item { label, .. } | MenuEntry::Sub { label, .. } => Some(label.clone()),
            _ => None,
        })
        .collect();
    assert_eq!(
        labels,
        [
            "Open",
            "Rename…",
            "Move to collection",
            "Merge into",
            "Show photographs in Explorer",
            "Show renders in Explorer",
            "Delete…"
        ]
    );
    // Its keys are printed beside it.
    let (output, _) = harness.frame(&catalog, vec![]);
    for text in ["Enter", "F2", "Del"] {
        assert!(find(&output, text).is_some(), "{text}");
    }
    // Hover opens the submenu: the other collection and a new one, beside
    // the menu (the side list draws the collections too, further left).
    let entry = find(&output, "Move to collection").unwrap();
    harness.frame(&catalog, vec![Event::PointerMoved(entry)]);
    let (output, _) = harness.frame(&catalog, vec![]);
    let rightmost = |text: &str| {
        everywhere(&output, text)
            .into_iter()
            .max_by(|a, b| a.x.total_cmp(&b.x))
            .unwrap()
    };
    assert!(rightmost("New collection").x > entry.x, "in the submenu");
    let insects = rightmost("Insects");
    assert!(insects.x > entry.x);
    let collection = catalog
        .nodes
        .iter()
        .find(|n| n.name == "Insects")
        .unwrap()
        .id;
    assert_eq!(
        press(
            &mut harness,
            &catalog,
            insects,
            PointerButton::Primary,
            Modifiers::NONE
        ),
        Some(LibraryIntent::MoveSubjects {
            subjects: vec![s3],
            collection
        })
    );
    assert!(harness.station.menu_entries().is_none(), "chosen: closed");
}

#[test]
fn a_press_outside_the_menu_closes_it_and_does_not_open_the_card_beneath() {
    let catalog = library_catalog(12, None);
    let mut harness = Harness::new();
    harness.frame(&catalog, vec![]);
    let at = drawn(&mut harness, &catalog, "Subject 003");
    press(
        &mut harness,
        &catalog,
        at,
        PointerButton::Secondary,
        Modifiers::NONE,
    );
    assert!(harness.station.menu_entries().is_some());
    let elsewhere = drawn(&mut harness, &catalog, "Subject 000");
    assert_eq!(
        press(
            &mut harness,
            &catalog,
            elsewhere,
            PointerButton::Primary,
            Modifiers::NONE
        ),
        None,
        "the dismissing press is not a click on the card"
    );
    assert!(harness.station.menu_entries().is_none());
    // Escape closes it too.
    press(
        &mut harness,
        &catalog,
        at,
        PointerButton::Secondary,
        Modifiers::NONE,
    );
    key(&mut harness, &catalog, Key::Escape, Modifiers::NONE);
    assert!(harness.station.menu_entries().is_none());
}

#[test]
fn the_menu_of_a_selection_and_the_selection_bar_act_on_all_of_it() {
    let catalog = library_catalog(12, None);
    let mut harness = Harness::new();
    harness.frame(&catalog, vec![]);
    let names = ["Subject 002", "Subject 003", "Subject 004"];
    for name in names {
        let at = drawn(&mut harness, &catalog, name);
        press(
            &mut harness,
            &catalog,
            at,
            PointerButton::Primary,
            Modifiers::COMMAND,
        );
    }
    let ids: Vec<NodeId> = names.iter().map(|n| subject(&catalog, n)).collect();
    let at = drawn(&mut harness, &catalog, "Subject 003");
    press(
        &mut harness,
        &catalog,
        at,
        PointerButton::Secondary,
        Modifiers::NONE,
    );
    let entries = harness.station.menu_entries().unwrap().to_vec();
    assert!(entries.contains(&MenuEntry::Caption("3 subjects selected".into())));
    assert!(entries.iter().any(
        |e| matches!(e, MenuEntry::Item { label, intent: Some(LibraryIntent::Delete(d)), .. }
        if label == "Delete 3 subjects…" && *d == ids)
    ));
    // Merging offers each selected subject as the one to keep.
    let merge = entries
        .iter()
        .find_map(|e| match e {
            MenuEntry::Sub { label, items } if label == "Merge into one" => Some(items.clone()),
            _ => None,
        })
        .unwrap();
    assert_eq!(merge.len(), 3);
    assert_eq!(
        merge[0].intent,
        LibraryIntent::MergeSubjects {
            into: ids[0],
            others: vec![ids[1], ids[2]]
        }
    );
    key(&mut harness, &catalog, Key::Escape, Modifiers::NONE);
    // The bar's Delete asks for the same three.
    let bar = drawn(&mut harness, &catalog, "3 SUBJECTS SELECTED");
    let (output, _) = harness.frame(&catalog, vec![]);
    let delete = output
        .shapes
        .iter()
        .filter_map(|s| match &s.shape {
            egui::Shape::Text(t) if t.galley.text() == "Delete…" => {
                Some(t.pos + t.galley.size() * 0.5)
            }
            _ => None,
        })
        .find(|p| (p.y - bar.y).abs() < 20.0)
        .expect("the bar's Delete");
    assert_eq!(
        press(
            &mut harness,
            &catalog,
            delete,
            PointerButton::Primary,
            Modifiers::NONE
        ),
        Some(LibraryIntent::Delete(ids.clone()))
    );
    // Its Move opens the collections above it.
    let mover = drawn(&mut harness, &catalog, "Move to collection");
    press(
        &mut harness,
        &catalog,
        mover,
        PointerButton::Primary,
        Modifiers::NONE,
    );
    let entries = harness.station.menu_entries().expect("the move menu");
    assert!(entries.iter().any(|e| matches!(e, MenuEntry::Item { intent: Some(LibraryIntent::MoveSubjectsToNewCollection(s)), .. } if *s == ids)));
}

#[test]
fn subjects_dragged_onto_a_collection_move_there() {
    let catalog = library_catalog(12, None);
    let mut harness = Harness::new();
    harness.frame(&catalog, vec![]);
    let insects = catalog
        .nodes
        .iter()
        .find(|n| n.name == "Insects")
        .unwrap()
        .id;
    let card = drawn(&mut harness, &catalog, "Subject 003");
    let target = drawn(&mut harness, &catalog, "Insects");
    harness.time += 1.0;
    let button = |pos, pressed| Event::PointerButton {
        pos,
        button: PointerButton::Primary,
        pressed,
        modifiers: Modifiers::NONE,
    };
    harness.frame(
        &catalog,
        vec![Event::PointerMoved(card), button(card, true)],
    );
    let mut intent = None;
    for step in 1..=8 {
        let t = step as f32 / 8.0;
        let at = card + (target - card) * t;
        harness.time += 0.05;
        let (output, found) = harness.frame(&catalog, vec![Event::PointerMoved(at)]);
        intent = intent.or(found);
        if step == 4 {
            assert!(
                find(&output, "MOVE 1 SUBJECT TO A COLLECTION").is_some(),
                "the drag says what a drop does"
            );
        }
    }
    harness.time += 0.05;
    let (_, found) = harness.frame(&catalog, vec![button(target, false)]);
    let (_, later) = harness.frame(&catalog, vec![]);
    assert_eq!(
        intent.or(found).or(later),
        Some(LibraryIntent::MoveSubjects {
            subjects: vec![subject(&catalog, "Subject 003")],
            collection: insects
        })
    );
}

#[test]
fn list_rows_take_the_same_selection_menu_and_keys() {
    let catalog = library_catalog(12, None);
    let mut harness = Harness::new();
    harness.station.view = LibraryView::List;
    harness.frame(&catalog, vec![]);
    let at = drawn(&mut harness, &catalog, "Subject 001");
    press(
        &mut harness,
        &catalog,
        at,
        PointerButton::Primary,
        Modifiers::COMMAND,
    );
    let other = drawn(&mut harness, &catalog, "Subject 002");
    press(
        &mut harness,
        &catalog,
        other,
        PointerButton::Primary,
        Modifiers::SHIFT,
    );
    assert_eq!(harness.station.selection.ids().len(), 2);
    press(
        &mut harness,
        &catalog,
        at,
        PointerButton::Secondary,
        Modifiers::NONE,
    );
    assert!(
        harness
            .station
            .menu_entries()
            .unwrap()
            .contains(&MenuEntry::Caption("2 subjects selected".into()))
    );
}

#[test]
fn pointer_motion_with_a_selection_and_its_bar_rebuilds_nothing() {
    let catalog = library_catalog(200, None);
    let mut harness = Harness::new();
    harness.frame(&catalog, vec![]);
    key(&mut harness, &catalog, Key::A, Modifiers::COMMAND);
    harness.frame(&catalog, vec![]);
    let before = harness.station.stats();
    for i in 0..30 {
        let at = Pos2::new(300.0 + i as f32 * 30.0, 200.0 + (i % 7) as f32 * 60.0);
        harness.frame(&catalog, vec![Event::PointerMoved(at)]);
    }
    let after = harness.station.stats();
    assert_eq!(after.model_builds, before.model_builds);
    assert_eq!(after.list_builds, before.list_builds);
    assert_eq!(harness.station.selection.ids().len(), 200);
}
