//! The subject page: intents, stack order, lineage, journal, editing and
//! cached depth signatures, on a synthetic catalog.
use super::*;
use crate::library_station::tests::{BASE, count, develop, draft, find, run};
use eframe::egui::{Event, Modifiers, PointerButton, RawInput};

const WIDTH: f32 = 1680.0;
const HEIGHT: f32 = 982.0;

struct Fixture {
    catalog: Catalog,
    subject: NodeId,
    /// Two renders, the newer failed.
    dorsal: NodeId,
    /// A saved render with a version and an export; the newest activity.
    wing: NodeId,
    /// Never stacked.
    lateral: NodeId,
}
fn fixture() -> Fixture {
    let mut catalog = Catalog::default();
    let project = catalog.create_project("Insects").unwrap();
    let subject = catalog.create_subject(project, "Blue weevil").unwrap();
    let dorsal = catalog
        .create_stack(
            subject,
            "Dorsal · 2.8×",
            draft("/captures/weevil/100MSDCF", 9_700_000_000),
        )
        .unwrap();
    catalog
        .add_revision(
            dorsal,
            run(
                "/out/strehl-1-1-1",
                "/captures/weevil/100MSDCF",
                "Saved",
                BASE,
            ),
        )
        .unwrap();
    catalog
        .add_revision(
            dorsal,
            run(
                "/out/strehl-2-1-2",
                "/captures/weevil/100MSDCF",
                "Failed",
                BASE + 100,
            ),
        )
        .unwrap();
    let wing = catalog
        .create_stack(
            subject,
            "Wing case · 5.6×",
            draft("/captures/weevil/101MSDCF", 35_800_000_000),
        )
        .unwrap();
    catalog
        .add_revision(
            wing,
            run(
                "/out/strehl-3-1-3",
                "/captures/weevil/101MSDCF",
                "Saved",
                BASE + 200,
            ),
        )
        .unwrap();
    develop(&mut catalog, wing, "/out/strehl-3-1-3", 3, BASE + 200);
    let lateral = catalog
        .create_stack(
            subject,
            "Lateral",
            draft("/captures/weevil/102MSDCF", 1_000_000_000),
        )
        .unwrap();
    catalog
        .set_subject_meta(
            subject,
            SubjectEdit {
                notes: Some("Pinned specimen on a dark field.".into()),
                optics: Some(Some(Optics {
                    camera: "ILCE-7CR".into(),
                    lens: "FE 100mm F2.8 Macro GM + 2× converter".into(),
                })),
                scale: Some(Some(ScaleCalibration::entered(2.8, 3.76).unwrap())),
                ..Default::default()
            },
        )
        .unwrap();
    Fixture {
        catalog,
        subject,
        dorsal,
        wing,
        lateral,
    }
}

struct Harness {
    time: f64,
    ctx: egui::Context,
    page: SubjectPage,
    previews: LibraryPreviews,
    palette: LibraryPalette,
    sources: HashMap<NodeId, SourcesState>,
    signatures: HashMap<NodeId, Vec<f32>>,
    running: Option<NodeId>,
    waiting: Vec<NodeId>,
    busy: bool,
    rig: Option<RigCapture>,
    /// Held while the next frames run (Ctrl or Shift clicks).
    modifiers: Modifiers,
}
impl Harness {
    fn new() -> Self {
        let ctx = egui::Context::default();
        crate::theme::install(&ctx);
        Self {
            time: 0.0,
            ctx,
            page: SubjectPage::default(),
            previews: LibraryPreviews::default(),
            palette: LibraryPalette::graphite(),
            sources: HashMap::new(),
            signatures: HashMap::new(),
            rig: None,
            running: None,
            waiting: Vec::new(),
            busy: false,
            modifiers: Modifiers::NONE,
        }
    }
    fn frame(
        &mut self,
        f: &Fixture,
        events: Vec<Event>,
    ) -> (egui::FullOutput, Option<LibraryIntent>) {
        let mut intent = None;
        self.time += 1.0 / 60.0;
        let time = self.time;
        let Self {
            time: _,
            ctx,
            page,
            previews,
            palette,
            sources,
            signatures,
            rig,
            running,
            waiting,
            busy,
            modifiers,
        } = self;
        let input = RawInput {
            events,
            modifiers: *modifiers,
            time: Some(time),
            screen_rect: Some(Rect::from_min_size(Pos2::ZERO, Vec2::new(WIDTH, HEIGHT))),
            ..Default::default()
        };
        let output = ctx.run(input, |ctx| {
            egui::CentralPanel::default()
                .frame(egui::Frame::NONE)
                .show(ctx, |ui| {
                    intent = page.show(
                        ui,
                        SubjectInputs {
                            catalog: &f.catalog,
                            revision: f.catalog.generation(),
                            subject: f.subject,
                            previews,
                            palette,
                            rig: rig.as_ref(),
                            sources,
                            signatures: Some(signatures),
                            queue: crate::subject_page::QueueView {
                                running: *running,
                                waiting,
                                busy: *busy,
                            },
                        },
                    );
                });
        });
        (output, intent)
    }
    fn click(&mut self, f: &Fixture, at: Pos2) -> Option<LibraryIntent> {
        self.time += 1.0;
        let button = |pressed| Event::PointerButton {
            pos: at,
            button: PointerButton::Primary,
            pressed,
            modifiers: Modifiers::NONE,
        };
        let (_, first) = self.frame(f, vec![Event::PointerMoved(at), button(true)]);
        let (_, second) = self.frame(f, vec![button(false)]);
        second.or(first)
    }
    fn click_text(&mut self, f: &Fixture, text: &str) -> Option<LibraryIntent> {
        let (output, _) = self.frame(f, vec![]);
        let at = find(&output, text).unwrap_or_else(|| panic!("{text} is drawn"));
        self.click(f, at)
    }
}

#[test]
fn stacks_are_newest_first_with_lifecycle_lineage_and_journal() {
    let f = fixture();
    let model = SubjectModel::build(&f.catalog, f.subject, 0).unwrap();
    let order: Vec<NodeId> = model
        .order(StackOrder::Newest)
        .into_iter()
        .map(|i| model.stacks[i].id)
        .collect();
    assert_eq!(order, [f.wing, f.dorsal, f.lateral]);
    let by_name: Vec<&str> = model
        .order(StackOrder::Name)
        .into_iter()
        .map(|i| model.stacks[i].name.as_str())
        .collect();
    assert_eq!(by_name, ["Dorsal · 2.8×", "Lateral", "Wing case · 5.6×"]);
    let dorsal = model.stacks.iter().find(|s| s.id == f.dorsal).unwrap();
    assert_eq!(dorsal.life.stacked, StepState::NeedsLook);
    assert_eq!(dorsal.renders.len(), 2);
    let wing = model.stacks.iter().find(|s| s.id == f.wing).unwrap();
    assert_eq!(wing.renders[0].versions.len(), 1);
    assert_eq!(wing.renders[0].versions[0].exports[0].name, "3.png");
    assert_eq!(model.collection.as_deref(), Some("Insects"));
    assert_eq!(model.bytes, 46_500_000_000);
    // The journal: newest first, renders, versions and exports.
    let texts: Vec<&str> = model.journal.iter().map(|l| l.text.as_str()).collect();
    // The subject itself was created now, after every fixture event.
    assert!(
        texts[0].starts_with("Subject \"Blue weevil\" created"),
        "{texts:?}"
    );
    assert!(texts[1].starts_with("Exported 3.png"), "{texts:?}");
    assert!(
        texts
            .iter()
            .any(|t| t.starts_with("Version \"Warm\" developed from render 1"))
    );
    assert!(texts.iter().any(|t| t.contains("failed")));
    assert!(model.journal.windows(2).all(|w| w[0].at >= w[1].at));

    let mut harness = Harness::new();
    let (output, _) = harness.frame(&f, vec![]);
    assert_eq!(
        harness.page.open,
        Some(f.wing),
        "the newest stacked stack opens"
    );
    for text in [
        "Blue weevil",
        "Insects",
        "ILCE-7CR",
        "1 px = 1.34 µm",
        "Render 1",
        "Warm",
        "3.png",
    ] {
        assert!(find(&output, text).is_some(), "{text} is drawn");
    }
    assert!(
        find(&output, "Trim sources…").is_none(),
        "D9: trimming is not built"
    );
}

#[test]
fn every_control_on_the_page_returns_its_intent() {
    let f = fixture();
    let mut harness = Harness::new();
    assert_eq!(
        harness.click_text(&f, "‹ LIBRARY"),
        Some(LibraryIntent::Back)
    );
    assert_eq!(
        harness.click_text(&f, "New stack of this subject"),
        Some(LibraryIntent::NewStackFromCamera {
            collection: None,
            subject: Some(f.subject)
        })
    );
    assert_eq!(
        harness.click_text(&f, "Add folders…"),
        Some(LibraryIntent::PickFolders {
            collection: None,
            subject: Some(f.subject)
        })
    );
    assert_eq!(
        harness.click_text(&f, "Shoot again with these settings"),
        Some(LibraryIntent::ShootAgain(f.wing))
    );
    assert_eq!(
        harness.click_text(&f, "Reveal folder"),
        Some(LibraryIntent::RevealPath(PathBuf::from(
            "/captures/weevil/101MSDCF"
        )))
    );
    assert_eq!(
        harness.click_text(&f, "3.png"),
        Some(LibraryIntent::RevealPath(PathBuf::from("/exports/3.png")))
    );
    // The first Open belongs to the newest stack.
    assert_eq!(
        harness.click_text(&f, "Open"),
        Some(LibraryIntent::OpenStack(f.wing))
    );
    // A capturing stack opens Capture instead.
    harness.rig = Some(RigCapture {
        subject: Some(f.subject),
        stack: Some(f.wing),
        title: String::new(),
        detail: String::new(),
        progress: 0.5,
        picture: None,
    });
    assert_eq!(
        harness.click_text(&f, "Open capture"),
        Some(LibraryIntent::OpenCapture)
    );
    harness.rig = None;
    // Moved sources offer Locate on the row.
    harness.sources.insert(f.dorsal, SourcesState::Missing);
    assert_eq!(
        harness.click_text(&f, "locate sources…"),
        Some(LibraryIntent::Locate(f.dorsal))
    );
    // Opening another row's lineage; a render can be opened.
    assert_eq!(harness.click_text(&f, "Dorsal · 2.8×"), None);
    assert_eq!(harness.page.open, Some(f.dorsal));
    let (output, _) = harness.frame(&f, vec![]);
    let render = find(&output, "Render 2").expect("dorsal's renders are shown");
    let press = |pressed| Event::PointerButton {
        pos: render,
        button: PointerButton::Primary,
        pressed,
        modifiers: Modifiers::NONE,
    };
    harness.time += 1.0;
    harness.frame(&f, vec![Event::PointerMoved(render), press(true)]);
    harness.frame(&f, vec![press(false)]);
    harness.frame(&f, vec![press(true)]);
    let (_, opened) = harness.frame(&f, vec![press(false)]);
    assert_eq!(
        opened,
        Some(LibraryIntent::OpenRender {
            stack: f.dorsal,
            run: PathBuf::from("/out/strehl-2-1-2")
        })
    );
    let key = |key| Event::Key {
        key,
        physical_key: None,
        pressed: true,
        repeat: false,
        modifiers: Modifiers::NONE,
    };
    let (_, new) = harness.frame(&f, vec![key(egui::Key::N)]);
    assert_eq!(
        new,
        Some(LibraryIntent::NewStackFromCamera {
            collection: None,
            subject: Some(f.subject)
        })
    );
    assert!(f.catalog.node(f.lateral).is_some());
}

#[test]
fn editing_returns_one_validated_edit_and_never_touches_the_catalog() {
    let f = fixture();
    let before = serde_json::to_vec(&f.catalog).unwrap();
    let mut harness = Harness::new();
    assert_eq!(harness.click_text(&f, "Edit"), None);
    assert!(harness.page.editing());
    let saved = harness.click_text(&f, "Save");
    let Some(LibraryIntent::EditSubject { id, name, edit }) = saved else {
        panic!("Save returns the edit: {saved:?}");
    };
    assert_eq!((id, name.as_str()), (f.subject, "Blue weevil"));
    assert_eq!(
        edit.notes.as_deref(),
        Some("Pinned specimen on a dark field.")
    );
    assert_eq!(
        edit.scale,
        Some(Some(ScaleCalibration::entered(2.8, 3.76).unwrap())),
        "the entered scale survives the round trip"
    );
    assert!(!harness.page.editing());
    assert_eq!(serde_json::to_vec(&f.catalog).unwrap(), before);

    let model = SubjectModel::build(&f.catalog, f.subject, 0).unwrap();
    let mut draft = Draft::of(&model);
    draft.entered = false;
    draft.um_per_px = "0,94".into();
    draft.slide = "0.01 mm slide".into();
    let (_, edit) = draft.edit().unwrap();
    assert_eq!(
        edit.scale,
        Some(Some(
            ScaleCalibration::measured(0.94, "0.01 mm slide").unwrap()
        ))
    );
    draft.um_per_px = "fine".into();
    assert!(draft.edit().is_err());
    draft.um_per_px.clear();
    draft.camera.clear();
    draft.lens.clear();
    let (_, edit) = draft.edit().unwrap();
    assert_eq!(
        (edit.scale, edit.optics),
        (Some(None), Some(None)),
        "empty fields clear"
    );
    draft.name = "  ".into();
    assert!(draft.edit().is_err());
}

#[test]
fn a_six_thousand_plane_signature_is_pooled_once_and_pointer_motion_rebuilds_nothing() {
    let f = fixture();
    let mut harness = Harness::new();
    harness.signatures.insert(
        f.wing,
        (0..6000).map(|i| ((i as f32) * 0.01).sin().abs()).collect(),
    );
    harness.frame(&f, vec![]);
    for step in 0..20 {
        harness.frame(
            &f,
            vec![Event::PointerMoved(Pos2::new(
                600.0 + step as f32 * 40.0,
                150.0 + step as f32 * 20.0,
            ))],
        );
    }
    let stats = harness.page.stats();
    assert_eq!((stats.model_builds, stats.spark_builds), (1, 1));
    assert!(stats.rows_painted <= 3);
    let pooled = &harness.page.sparks[&f.wing].1;
    assert!(pooled.len() <= 115, "at most one column per 2 px of 230");
    assert!(pooled.iter().all(|v| (0.0..=1.0).contains(v)));
    // Another subject resets the page's per-subject state.
    let mut other: Catalog =
        serde_json::from_slice(&serde_json::to_vec(&f.catalog).unwrap()).unwrap();
    let project = other
        .nodes
        .iter()
        .find(|n| n.kind == NodeKind::Project)
        .unwrap()
        .id;
    let second = other.create_subject(project, "Garnet").unwrap();
    let g = Fixture {
        catalog: other,
        subject: second,
        dorsal: f.dorsal,
        wing: f.wing,
        lateral: f.lateral,
    };
    harness.frame(&g, vec![]);
    assert_eq!(harness.page.open, None, "an empty subject opens nothing");
    assert_eq!(harness.page.stats().model_builds, 2);
}

#[test]
fn each_stack_row_offers_stack_or_stack_next_and_shows_the_queue() {
    let f = fixture();
    let mut harness = Harness::new();
    // Nothing renders: Stack, on the newest stack's row first.
    assert_eq!(
        harness.click_text(&f, "Stack"),
        Some(LibraryIntent::QueueStack(f.wing))
    );
    // Another stack renders: Stack next on the others; the running one
    // and a waiting one say so instead of offering a button.
    harness.busy = true;
    harness.running = Some(f.dorsal);
    let (output, _) = harness.frame(&f, vec![]);
    let at = rightmost(&output, "Stack next").expect("a row button");
    assert_eq!(
        harness.click(&f, at),
        Some(LibraryIntent::QueueStack(f.wing))
    );
    harness.waiting = vec![f.wing];
    let (output, _) = harness.frame(&f, vec![]);
    assert!(find(&output, "STACKING").is_some());
    assert!(find(&output, "QUEUED").is_some());
    let at = rightmost(&output, "Stack next").expect("the lateral row's button");
    assert_eq!(
        harness.click(&f, at),
        Some(LibraryIntent::QueueStack(f.lateral)),
        "only the stack neither rendering nor waiting still offers it"
    );
    // A capturing stack offers no Stack.
    harness.busy = false;
    harness.running = None;
    harness.waiting.clear();
    harness.rig = Some(RigCapture {
        subject: Some(f.subject),
        stack: Some(f.wing),
        title: String::new(),
        detail: String::new(),
        progress: 0.5,
        picture: None,
    });
    let (output, _) = harness.frame(&f, vec![]);
    assert_eq!(
        count(&output, "Stack"),
        2,
        "dorsal and lateral, not the capturing wing case"
    );
}
/// The row button of that label (a life line may use the same words).
fn rightmost(output: &egui::FullOutput, needle: &str) -> Option<Pos2> {
    output
        .shapes
        .iter()
        .filter_map(|shape| match &shape.shape {
            egui::Shape::Text(t) if t.galley.text() == needle => {
                Some(t.pos + t.galley.size() * 0.5)
            }
            _ => None,
        })
        .max_by(|a, b| a.x.total_cmp(&b.x).then(b.y.total_cmp(&a.y)))
}

fn press_with(
    harness: &mut Harness,
    f: &Fixture,
    at: Pos2,
    button: PointerButton,
    modifiers: Modifiers,
) -> Option<LibraryIntent> {
    harness.modifiers = modifiers;
    harness.time += 1.0;
    let event = |pressed| Event::PointerButton {
        pos: at,
        button,
        pressed,
        modifiers,
    };
    let (_, first) = harness.frame(f, vec![Event::PointerMoved(at), event(true)]);
    let (_, second) = harness.frame(f, vec![event(false)]);
    harness.modifiers = Modifiers::NONE;
    second.or(first)
}
fn key_with(
    harness: &mut Harness,
    f: &Fixture,
    key: egui::Key,
    modifiers: Modifiers,
) -> Option<LibraryIntent> {
    harness.modifiers = modifiers;
    let (_, intent) = harness.frame(
        f,
        vec![Event::Key {
            key,
            physical_key: None,
            pressed: true,
            repeat: false,
            modifiers,
        }],
    );
    harness.modifiers = Modifiers::NONE;
    intent
}

#[test]
fn stack_rows_select_with_ctrl_and_shift_and_delete_and_f2_act_on_them() {
    let f = fixture();
    let mut harness = Harness::new();
    harness.frame(&f, vec![]);
    let (output, _) = harness.frame(&f, vec![]);
    let lateral = find(&output, "Lateral").unwrap();
    let dorsal = find(&output, "Dorsal · 2.8×").unwrap();
    let open_before = harness.page.open;
    assert_eq!(
        press_with(
            &mut harness,
            &f,
            lateral,
            PointerButton::Primary,
            Modifiers::COMMAND
        ),
        None
    );
    assert_eq!(
        harness.page.open, open_before,
        "a Ctrl click does not open the lineage"
    );
    assert_eq!(harness.page.selection.ids(), &[f.lateral]);
    press_with(
        &mut harness,
        &f,
        dorsal,
        PointerButton::Primary,
        Modifiers::SHIFT,
    );
    assert_eq!(harness.page.selection.ids().len(), 2);
    let (output, _) = harness.frame(&f, vec![]);
    assert!(find(&output, "2 STACKS SELECTED").is_some());
    let intent = key_with(&mut harness, &f, egui::Key::Delete, Modifiers::NONE);
    let Some(LibraryIntent::Delete(ids)) = intent else {
        panic!("{intent:?}")
    };
    assert_eq!(ids.len(), 2);
    assert!(ids.contains(&f.lateral) && ids.contains(&f.dorsal));
    // Ctrl A takes every stack; Escape clears; then keys act on the open one.
    key_with(&mut harness, &f, egui::Key::A, Modifiers::COMMAND);
    assert_eq!(harness.page.selection.ids().len(), 3);
    key_with(&mut harness, &f, egui::Key::Escape, Modifiers::NONE);
    assert!(harness.page.selection.is_empty());
    let open = harness
        .page
        .open
        .expect("the newest rendered stack is open");
    assert_eq!(
        key_with(&mut harness, &f, egui::Key::F2, Modifiers::NONE),
        Some(LibraryIntent::Rename(open))
    );
    assert_eq!(
        key_with(&mut harness, &f, egui::Key::Delete, Modifiers::NONE),
        Some(LibraryIntent::Delete(vec![open]))
    );
}

#[test]
fn a_stack_rows_menu_moves_it_to_another_subject_or_a_new_one() {
    let mut f = fixture();
    let project = f.catalog.nodes[0].id;
    let beetle = f.catalog.create_subject(project, "Ground beetle").unwrap();
    let mut harness = Harness::new();
    harness.frame(&f, vec![]);
    let (output, _) = harness.frame(&f, vec![]);
    let lateral = find(&output, "Lateral").unwrap();
    press_with(
        &mut harness,
        &f,
        lateral,
        PointerButton::Secondary,
        Modifiers::NONE,
    );
    let entries = harness
        .page
        .menu_entries()
        .expect("the stack's menu")
        .to_vec();
    let labels: Vec<&str> = entries
        .iter()
        .filter_map(|e| match e {
            MenuEntry::Item { label, .. } | MenuEntry::Sub { label, .. } => Some(label.as_str()),
            _ => None,
        })
        .collect();
    assert_eq!(
        labels,
        [
            "Open",
            "Stack",
            "Rename…",
            "Move to subject",
            "Show photographs in Explorer",
            "Show renders in Explorer",
            "Delete…"
        ]
    );
    let items = entries
        .iter()
        .find_map(|e| match e {
            MenuEntry::Sub { items, .. } => Some(items.clone()),
            _ => None,
        })
        .unwrap();
    // A new subject first; its own subject is not offered.
    assert_eq!(
        items[0].intent,
        LibraryIntent::MoveStacksToNewSubject(vec![f.lateral])
    );
    assert_eq!(items.len(), 2, "{items:?}");
    assert_eq!(
        items[1].intent,
        LibraryIntent::MoveStacks {
            stacks: vec![f.lateral],
            subject: beetle
        }
    );
    // It never rendered: Show renders is offered but disabled.
    assert!(entries.contains(&MenuEntry::disabled("Show renders in Explorer")));
    // Chosen through the pointer.
    let (output, _) = harness.frame(&f, vec![]);
    let entry = find(&output, "Move to subject").unwrap();
    harness.frame(&f, vec![Event::PointerMoved(entry)]);
    let (output, _) = harness.frame(&f, vec![]);
    let target = find(&output, "Ground beetle").expect("in the submenu");
    assert_eq!(
        press_with(
            &mut harness,
            &f,
            target,
            PointerButton::Primary,
            Modifiers::NONE
        ),
        Some(LibraryIntent::MoveStacks {
            stacks: vec![f.lateral],
            subject: beetle
        })
    );
}

#[test]
fn right_clicking_the_subjects_picture_offers_the_subjects_own_menu() {
    let f = fixture();
    let mut harness = Harness::new();
    harness.frame(&f, vec![]);
    let hero = Pos2::new(250.0, 200.0);
    press_with(
        &mut harness,
        &f,
        hero,
        PointerButton::Secondary,
        Modifiers::NONE,
    );
    let entries = harness.page.menu_entries().expect("the subject's menu");
    assert!(
        !entries
            .iter()
            .any(|e| matches!(e, MenuEntry::Item { label, .. } if label == "Open")),
        "already open"
    );
    assert!(entries.iter().any(|e| matches!(e,
        MenuEntry::Item { intent: Some(LibraryIntent::Delete(ids)), .. } if *ids == vec![f.subject])));
}
