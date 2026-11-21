//! The subject page: intents, stack order, lineage, journal, editing and
//! cached depth signatures, on a synthetic catalog.
use super::*;
use crate::library_station::tests::{BASE, develop, draft, find, run};
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
    rig: Option<RigCapture>,
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
        } = self;
        let input = RawInput {
            events,
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
