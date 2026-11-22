//! The Library station: intents, filters, search, sort, virtualised painting
//! and preview budgets, on synthetic catalogs (no user catalog or capture).
use super::*;
use crate::library_previews::{MAX_BYTES, MAX_ENTRIES, UPLOAD_BUDGET, WORKERS};
use crate::workspace_history::{PhotoExport, PhotoVersion, Run, StackDraft};
use eframe::egui::{Event, Modifiers, PointerButton, RawInput};
use serde_json::json;

pub(crate) const WIDTH: f32 = 1448.0;
pub(crate) const HEIGHT: f32 = 982.0;
pub(crate) const BASE: u64 = 1_700_000_000;

pub(crate) fn run(directory: &str, source: &str, status: &str, created: u64) -> Run {
    serde_json::from_value(json!({
        "directory": directory, "source": source,
        "output": format!("{directory}/photograph.tiff"), "log": format!("{directory}/render.log"),
        "label": "Balanced", "created": created, "status": status, "frames": 2,
        "sources": [{"path":format!("{source}/DSC00001.ARW"),"bytes":100}],
        "settings": crate::jobs::RenderSettings::default(),
        "exposure": null, "gate": null, "workers": 4
    }))
    .unwrap()
}
fn hex(c: char) -> String {
    std::iter::repeat_n(c, 64).collect()
}
fn id(n: u64, c: char) -> String {
    format!("{n:031x}{c}")
}
/// A saved version of `run` and an export of it.
pub(crate) fn develop(catalog: &mut Catalog, stack: NodeId, directory: &str, n: u64, created: u64) {
    let output = format!("{directory}/photograph.tiff");
    let identity =
        json!({"canonical_path":output,"bytes":20,"dimensions":[20,10],"sha256":hex('a')});
    let version: PhotoVersion = serde_json::from_value(json!({
        "id": id(n, 'a'), "name": "Warm", "created": created + 10,
        "owner": {"stack": stack, "run": directory, "output": output},
        "photo": identity, "decoded_source": identity, "loaded_sha256": hex('b')
    }))
    .unwrap();
    catalog.add_photo_version(version).unwrap();
    let export: PhotoExport = serde_json::from_value(json!({
        "id": id(n, 'e'), "version": id(n, 'a'), "path": format!("/exports/{n}.png"),
        "created": created + 20,
        "settings": {"format":"png","color_space":"srgb","hdr":false,"quality":100,"speed":6},
        "bytes": 20, "sha256": hex('d')
    }))
    .unwrap();
    catalog.add_photo_export(export).unwrap();
}
pub(crate) fn draft(source: &str, bytes: u64) -> StackDraft {
    StackDraft {
        source: PathBuf::from(source),
        sources: vec![crate::workspace_history::SourceIdentity {
            path: PathBuf::from(format!("{source}/DSC00001.ARW")),
            bytes,
            modified_ns: None,
        }],
        settings: crate::jobs::RenderSettings::default(),
        exposure: None,
        gate: None,
        workers: 4,
    }
}

/// `count` subjects in two collections. Pattern by index: 0 to stack, 1 to
/// develop, 2 to check (latest render failed), 3 exported. Subject 7's lens
/// is searchable; `pictures` gives every subject a hero picture.
pub(crate) fn catalog(count: usize, pictures: Option<&Path>) -> Catalog {
    let mut catalog = Catalog::default();
    let insects = catalog.create_project("Insects").unwrap();
    let minerals = catalog.create_project("Minerals").unwrap();
    for i in 0..count {
        let collection = if i % 2 == 0 { insects } else { minerals };
        let subject = catalog
            .create_subject(collection, &format!("Subject {i:03}"))
            .unwrap();
        let source = format!("/captures/s{i:03}/100MSDCF");
        let stack = catalog
            .create_stack(
                subject,
                "Dorsal",
                draft(&source, (i as u64 + 1) * 1_000_000_000),
            )
            .unwrap();
        let created = BASE + i as u64 * 1000;
        let directory = format!("/out/strehl-{i}-1-1");
        match i % 4 {
            0 => {}
            1 => catalog
                .add_revision(stack, run(&directory, &source, "Saved", created))
                .unwrap(),
            2 => {
                catalog
                    .add_revision(stack, run(&directory, &source, "Saved", created))
                    .unwrap();
                catalog
                    .add_revision(
                        stack,
                        run(&format!("{directory}-b"), &source, "Failed", created + 1),
                    )
                    .unwrap();
            }
            _ => {
                catalog
                    .add_revision(stack, run(&directory, &source, "Saved", created))
                    .unwrap();
                develop(&mut catalog, stack, &directory, i as u64, created);
            }
        }
        let mut edit = SubjectEdit::default();
        if i == 7 {
            edit.optics = Some(Some(crate::workspace_history::Optics {
                camera: "ILCE-7CR".into(),
                lens: "Laowa 2.5-5x Ultra Macro".into(),
            }));
            edit.notes = Some("Found under the oak bark.".into());
        }
        if let Some(directory) = pictures {
            edit.hero = Some(Some(directory.join(format!("hero-{i:03}.png"))));
        }
        catalog.set_subject_meta(subject, edit).unwrap();
    }
    catalog
}
pub(crate) fn write_pictures(directory: &Path, count: usize) {
    for i in 0..count {
        image::RgbImage::from_pixel(420, 280, image::Rgb([(i * 37 % 255) as u8, 90, 140]))
            .save(directory.join(format!("hero-{i:03}.png")))
            .unwrap();
    }
}

pub(crate) struct Harness {
    /// Simulated seconds: clicks are spaced apart so they never pair up.
    pub time: f64,
    pub ctx: egui::Context,
    pub station: LibraryStation,
    pub previews: LibraryPreviews,
    pub palette: LibraryPalette,
    pub rig: Option<RigCapture>,
    pub storage: Option<StorageCard>,
    /// Depth signatures by subject, for list rows.
    pub signatures: HashMap<NodeId, Vec<f32>>,
    pub stacking: bool,
}
impl Harness {
    pub(crate) fn new() -> Self {
        let ctx = egui::Context::default();
        crate::theme::install(&ctx);
        ctx.style_mut(|style| style.scroll_animation = egui::style::ScrollAnimation::none());
        Self {
            time: 0.0,
            ctx,
            station: LibraryStation::default(),
            previews: LibraryPreviews::default(),
            palette: LibraryPalette::graphite(),
            rig: None,
            storage: None,
            signatures: HashMap::new(),
            stacking: false,
        }
    }
    pub(crate) fn frame(
        &mut self,
        catalog: &Catalog,
        events: Vec<Event>,
    ) -> (egui::FullOutput, Option<LibraryIntent>) {
        self.frame_with(
            catalog,
            RawInput {
                events,
                ..Default::default()
            },
        )
    }
    pub(crate) fn frame_with(
        &mut self,
        catalog: &Catalog,
        mut input: RawInput,
    ) -> (egui::FullOutput, Option<LibraryIntent>) {
        input.screen_rect = Some(Rect::from_min_size(Pos2::ZERO, Vec2::new(WIDTH, HEIGHT)));
        self.time += 1.0 / 60.0;
        input.time = Some(self.time);
        let mut intent = None;
        let Self {
            time: _,
            ctx,
            station,
            previews,
            palette,
            rig,
            storage,
            signatures,
            stacking,
        } = self;
        let output = ctx.run(input, |ctx| {
            egui::CentralPanel::default()
                .frame(egui::Frame::NONE)
                .show(ctx, |ui| {
                    intent = station.show(
                        ui,
                        LibraryInputs {
                            catalog,
                            revision: catalog.generation(),
                            previews,
                            palette,
                            rig: rig.as_ref(),
                            storage: storage.as_ref(),
                            signatures: Some(signatures),
                            stacking: *stacking,
                            deleting: None,
                        },
                    );
                });
        });
        (output, intent)
    }
    /// Press and release at `at` over two frames; the intent either produced.
    pub(crate) fn click(&mut self, catalog: &Catalog, at: Pos2) -> Option<LibraryIntent> {
        self.time += 1.0;
        let button = |pressed| Event::PointerButton {
            pos: at,
            button: PointerButton::Primary,
            pressed,
            modifiers: Modifiers::NONE,
        };
        let (_, first) = self.frame(catalog, vec![Event::PointerMoved(at), button(true)]);
        let (_, second) = self.frame(catalog, vec![button(false)]);
        second.or(first)
    }
    pub(crate) fn settle(&mut self, catalog: &Catalog) {
        let deadline = std::time::Instant::now() + std::time::Duration::from_secs(60);
        loop {
            self.frame(catalog, vec![]);
            self.check_budgets();
            if !self.previews.pending() {
                break;
            }
            assert!(
                std::time::Instant::now() < deadline,
                "previews never settled"
            );
            std::thread::sleep(std::time::Duration::from_millis(2));
        }
    }
    pub(crate) fn check_budgets(&self) {
        let stats = self.previews.stats();
        assert!(stats.running <= WORKERS, "{stats:?}");
        assert!(stats.entries <= MAX_ENTRIES, "{stats:?}");
        assert!(stats.bytes <= MAX_BYTES, "{stats:?}");
        // A row of five 256 px tiles is under the budget, so no poll exceeds it.
        assert!(stats.uploaded_last_poll <= UPLOAD_BUDGET, "{stats:?}");
    }
}
pub(crate) fn find(output: &egui::FullOutput, needle: &str) -> Option<Pos2> {
    fn visit(shape: &egui::Shape, needle: &str) -> Option<Pos2> {
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
/// How many times `needle` is drawn as a whole text.
pub(crate) fn count(output: &egui::FullOutput, needle: &str) -> usize {
    fn visit(shape: &egui::Shape, needle: &str) -> usize {
        match shape {
            egui::Shape::Text(t) => usize::from(t.galley.text() == needle),
            egui::Shape::Vec(v) => v.iter().map(|s| visit(s, needle)).sum(),
            _ => 0,
        }
    }
    output.shapes.iter().map(|s| visit(&s.shape, needle)).sum()
}
fn subject_id(catalog: &Catalog, name: &str) -> NodeId {
    catalog
        .nodes
        .iter()
        .find(|n| n.name == name && n.kind == NodeKind::Subject)
        .unwrap()
        .id
}
fn names(catalog: &Catalog, ids: &[NodeId]) -> Vec<String> {
    ids.iter()
        .map(|id| catalog.node(*id).unwrap().name.clone())
        .collect()
}

#[test]
fn two_hundred_subjects_lay_out_only_the_rows_in_view_and_pointer_motion_rebuilds_nothing() {
    let large = catalog(200, None);
    let small = catalog(40, None);
    let mut painted = Vec::new();
    for catalog in [&small, &large] {
        let mut harness = Harness::new();
        let (output, _) = harness.frame(catalog, vec![]);
        let stats = harness.station.stats();
        assert_eq!((stats.model_builds, stats.list_builds), (1, 1));
        // Four rows of five cards fit 982 px less the header: at most five rows.
        assert!(stats.cards_painted <= 25, "{stats:?}");
        assert!(stats.prefetched <= 25, "{stats:?}");
        let shapes = output.shapes.len();
        let mut timings = Vec::new();
        for step in 0..30 {
            let at = Pos2::new(300.0 + step as f32 * 37.0, 200.0 + step as f32 * 23.0);
            let started = std::time::Instant::now();
            harness.frame(catalog, vec![Event::PointerMoved(at)]);
            timings.push(started.elapsed());
        }
        let stats = harness.station.stats();
        assert_eq!(
            (stats.model_builds, stats.list_builds),
            (1, 1),
            "pointer-only motion rebuilt the library"
        );
        timings.sort();
        eprintln!(
            "library-paint: {} subjects, {} cards laid out, {shapes} shapes, frame median {:?} max {:?} (debug build, incl. egui)",
            catalog
                .nodes
                .iter()
                .filter(|n| n.kind == NodeKind::Subject)
                .count(),
            stats.cards_painted,
            timings[timings.len() / 2],
            timings[timings.len() - 1]
        );
        painted.push((stats.cards_painted, shapes));
    }
    assert_eq!(
        painted[0].0, painted[1].0,
        "the cards laid out do not grow with the catalog"
    );
    // Shapes differ only with the drawn cards' own text and badges.
    assert!(
        painted[1].1 <= painted[0].1 + painted[0].1 / 10,
        "{painted:?}"
    );
}

#[test]
fn a_catalog_change_rebuilds_once_and_search_or_sort_rebuilds_only_the_list() {
    let mut catalog = catalog(30, None);
    let mut harness = Harness::new();
    harness.frame(&catalog, vec![]);
    harness.frame(&catalog, vec![]);
    assert_eq!(harness.station.stats().model_builds, 1);
    catalog
        .rename(subject_id(&catalog, "Subject 004"), "Garnet")
        .unwrap();
    catalog.save().unwrap();
    harness.frame(&catalog, vec![]);
    harness.frame(&catalog, vec![]);
    assert_eq!(harness.station.stats().model_builds, 2);
    harness.station.sort = LibrarySort::Name;
    harness.frame(&catalog, vec![]);
    let stats = harness.station.stats();
    assert_eq!((stats.model_builds, stats.list_builds), (2, 3));
    assert_eq!(names(&catalog, &harness.station.visible()[..1]), ["Garnet"]);
}

#[test]
fn cards_open_subjects_and_the_new_subject_menu_offers_camera_and_folders() {
    let catalog = catalog(12, None);
    let mut harness = Harness::new();
    let (output, _) = harness.frame(&catalog, vec![]);
    // Recent first: subject 011 has the newest export.
    let at = find(&output, "Subject 011").expect("the newest subject is drawn");
    assert_eq!(
        harness.click(&catalog, at),
        Some(LibraryIntent::OpenSubject(subject_id(
            &catalog,
            "Subject 011"
        )))
    );
    let (output, _) = harness.frame(&catalog, vec![]);
    let new = find(&output, "New subject").unwrap();
    assert_eq!(harness.click(&catalog, new), None, "the menu opens");
    let (output, _) = harness.frame(&catalog, vec![]);
    let camera = find(&output, "From the camera").expect("menu item");
    assert_eq!(
        harness.click(&catalog, camera),
        Some(LibraryIntent::NewStackFromCamera {
            collection: None,
            subject: None
        })
    );
    // Inside a collection the new subject goes there.
    let (output, _) = harness.frame(&catalog, vec![]);
    let minerals = find(&output, "Minerals").unwrap();
    harness.click(&catalog, minerals);
    let collection = catalog
        .nodes
        .iter()
        .find(|n| n.name == "Minerals")
        .unwrap()
        .id;
    assert_eq!(
        harness.station.filter,
        LibraryFilter::Collection(collection)
    );
    let (output, _) = harness.frame(&catalog, vec![]);
    harness.click(&catalog, find(&output, "New subject").unwrap());
    let (output, _) = harness.frame(&catalog, vec![]);
    let folders = find(&output, "From folders…").expect("menu item");
    assert_eq!(
        harness.click(&catalog, folders),
        Some(LibraryIntent::PickFolders {
            collection: Some(collection),
            subject: None
        })
    );
    let (output, _) = harness.frame(&catalog, vec![]);
    assert!(find(&output, "From folders…").is_none(), "the menu closed");
    assert_eq!(
        harness.click(&catalog, find(&output, "Review storage…").unwrap()),
        Some(LibraryIntent::ReviewStorage)
    );
    let (output, _) = harness.frame(&catalog, vec![]);
    assert_eq!(
        harness.click(&catalog, find(&output, "New collection").unwrap()),
        Some(LibraryIntent::NewCollection)
    );
}

#[test]
fn the_rig_strip_moved_sources_keys_and_drops_produce_their_intents() {
    let catalog = catalog(8, None);
    let blue = subject_id(&catalog, "Subject 005");
    let mut harness = Harness::new();
    harness.rig = Some(RigCapture {
        subject: Some(blue),
        stack: catalog.stacks_of(blue).first().copied(),
        title: "Blue weevil · Dorsal · 2.8×".into(),
        detail: "Capturing plane 61 of 96".into(),
        progress: 0.635,
        picture: None,
    });
    let (output, _) = harness.frame(&catalog, vec![]);
    assert!(
        find(&output, "CAPTURING").is_some(),
        "the capturing card is badged"
    );
    assert_eq!(
        harness.click(&catalog, find(&output, "Open capture").unwrap()),
        Some(LibraryIntent::OpenCapture)
    );
    // On the rig lists the capturing subject only.
    let (output, _) = harness.frame(&catalog, vec![]);
    harness.click(&catalog, find(&output, "On the rig").unwrap());
    harness.frame(&catalog, vec![]);
    assert_eq!(harness.station.visible(), [blue]);

    // Sources moved: badge, words and Locate.
    harness.station.filter = LibraryFilter::All;
    harness.rig = None;
    let moved_subject = subject_id(&catalog, "Subject 002");
    let moved_stack = catalog.stacks_of(moved_subject)[0];
    harness
        .station
        .set_sources(HashMap::from([(moved_stack, SourcesState::Missing)]));
    let (output, _) = harness.frame(&catalog, vec![]);
    assert!(find(&output, "SOURCES MOVED").is_some());
    let link = find(&output, "locate the sources…").expect("moved sources offer Locate");
    assert_eq!(
        harness.click(&catalog, link),
        Some(LibraryIntent::Locate(moved_stack))
    );

    // Keys: the selection moves with the arrows; Enter opens; F2 renames.
    harness.station.selected = None;
    let key = |key| Event::Key {
        key,
        physical_key: None,
        pressed: true,
        repeat: false,
        modifiers: Modifiers::NONE,
    };
    harness.frame(&catalog, vec![key(Key::ArrowRight)]);
    harness.frame(&catalog, vec![key(Key::ArrowRight)]);
    let second = harness.station.visible()[1];
    let (_, opened) = harness.frame(&catalog, vec![key(Key::Enter)]);
    assert_eq!(opened, Some(LibraryIntent::OpenSubject(second)));
    let (_, renamed) = harness.frame(&catalog, vec![key(Key::F2)]);
    assert_eq!(renamed, Some(LibraryIntent::Rename(second)));

    // Dropped folders: one stack per folder, camera folders grouped by parent.
    let root = tempfile::tempdir().unwrap();
    let a = root.path().join("bug-3").join("100MSDCF");
    let b = root.path().join("bug-3").join("101MSDCF");
    let c = root.path().join("chia-seeds");
    for folder in [&a, &b, &c] {
        std::fs::create_dir_all(folder).unwrap();
    }
    let file = root.path().join("notes.txt");
    std::fs::write(&file, "not a folder").unwrap();
    let dropped = [&c, &b, &a, &file]
        .into_iter()
        .map(|path| egui::DroppedFile {
            path: Some(path.to_path_buf()),
            ..Default::default()
        })
        .collect();
    let (_, intent) = harness.frame_with(
        &catalog,
        RawInput {
            dropped_files: dropped,
            ..Default::default()
        },
    );
    assert_eq!(
        intent,
        Some(LibraryIntent::ImportFolders {
            collection: None,
            subject: None,
            groups: vec![
                ImportGroup {
                    subject: "chia-seeds".into(),
                    folders: vec![c.clone()]
                },
                ImportGroup {
                    subject: "bug-3".into(),
                    folders: vec![a.clone(), b.clone()]
                },
            ]
        })
    );
}

#[test]
fn needs_you_lists_collections_search_and_sort_select_the_right_subjects() {
    let catalog = catalog(16, None);
    let model = LibraryModel::build(&catalog, 0, BASE + 100_000);
    assert_eq!(
        model.needs,
        NeedsYou {
            to_stack: 4,
            to_check: 4,
            to_develop: 4,
            exported: 4
        }
    );
    assert_eq!(model.stacks, 16);
    let pick = |filter, query: &str, sort| {
        model
            .select(filter, query, sort, None)
            .into_iter()
            .map(|i| model.cards[i].name.clone())
            .collect::<Vec<_>>()
    };
    assert_eq!(
        pick(LibraryFilter::ToCheck, "", LibrarySort::Name),
        ["Subject 002", "Subject 006", "Subject 010", "Subject 014"]
    );
    assert_eq!(
        pick(LibraryFilter::ToStack, "", LibrarySort::Name),
        ["Subject 000", "Subject 004", "Subject 008", "Subject 012"]
    );
    assert_eq!(
        pick(LibraryFilter::Exported, "", LibrarySort::Name),
        ["Subject 003", "Subject 007", "Subject 011", "Subject 015"]
    );
    let minerals = catalog
        .nodes
        .iter()
        .find(|n| n.name == "Minerals")
        .unwrap()
        .id;
    assert!(
        pick(LibraryFilter::Collection(minerals), "", LibrarySort::Name)
            .iter()
            .all(|name| name.ends_with(['1', '3', '5', '7', '9']))
    );
    assert_eq!(model.collections[1].subjects, 8);
    // Search covers names, notes, lenses and dates; every word must match.
    assert_eq!(
        pick(LibraryFilter::All, "laowa", LibrarySort::Name),
        ["Subject 007"]
    );
    assert_eq!(
        pick(LibraryFilter::All, "oak BARK", LibrarySort::Name),
        ["Subject 007"]
    );
    assert_eq!(
        pick(LibraryFilter::All, "subject 01", LibrarySort::Name).len(),
        7,
        "001 and 010 to 015"
    );
    let day = {
        use chrono::{Local, TimeZone};
        Local
            .timestamp_opt((BASE + 9 * 1000) as i64, 0)
            .unwrap()
            .format("%Y-%m-%d")
            .to_string()
    };
    assert!(pick(LibraryFilter::All, &day, LibrarySort::Name).contains(&"Subject 009".into()));
    assert!(pick(LibraryFilter::All, "no such thing", LibrarySort::Name).is_empty());
    // Sort: recent activity (a subject never stacked counts from its
    // creation, here the newest), name, recorded source size.
    let recent = pick(LibraryFilter::All, "", LibrarySort::Recent);
    assert_eq!(
        recent[..6],
        [
            "Subject 000",
            "Subject 004",
            "Subject 008",
            "Subject 012",
            "Subject 015",
            "Subject 014"
        ]
    );
    // The subject on the rig leads the recent sort.
    let on_rig = model
        .cards
        .iter()
        .find(|c| c.name == "Subject 009")
        .unwrap()
        .id;
    let first = model.select(LibraryFilter::All, "", LibrarySort::Recent, Some(on_rig))[0];
    assert_eq!(model.cards[first].name, "Subject 009");
    assert_eq!(
        pick(LibraryFilter::All, "", LibrarySort::Size)[..2],
        ["Subject 015", "Subject 014"]
    );
    assert_eq!(
        pick(LibraryFilter::All, "", LibrarySort::Name)[..2],
        ["Subject 000", "Subject 001"]
    );
    // The same selections through the left list and the search field.
    let mut harness = Harness::new();
    let (output, _) = harness.frame(&catalog, vec![]);
    harness.click(&catalog, find(&output, "To check").unwrap());
    harness.frame(&catalog, vec![]);
    assert_eq!(harness.station.visible().len(), 4);
    harness.station.filter = LibraryFilter::All;
    harness.station.query = "laowa".into();
    harness.frame(&catalog, vec![]);
    assert_eq!(names(&catalog, &harness.station.visible()), ["Subject 007"]);
    let (output, _) = harness.frame(&catalog, vec![]);
    assert!(find(&output, "1 subject · 1 stack · 1 render").is_some());
}

#[test]
fn scrolling_requests_visible_and_one_screen_ahead_within_the_preview_budgets() {
    let pictures = tempfile::tempdir().unwrap();
    write_pictures(pictures.path(), 200);
    let catalog = catalog(200, Some(pictures.path()));
    let mut harness = Harness::new();
    harness.station.sort = LibrarySort::Name;
    harness.frame(&catalog, vec![]);
    let stats = harness.previews.stats();
    assert!(stats.running <= WORKERS);
    assert!(
        stats.queued + stats.running <= 50,
        "only the view and one screen ahead are requested: {stats:?}"
    );
    harness.settle(&catalog);
    let warm = harness.previews.stats();
    assert!(warm.entries >= 20 && warm.entries <= 50, "{warm:?}");
    assert!(warm.largest_poll_upload <= UPLOAD_BUDGET, "{warm:?}");
    // A warm view uploads nothing and starts no task on pointer motion.
    for step in 0..10 {
        harness.frame(
            &catalog,
            vec![Event::PointerMoved(Pos2::new(
                400.0 + step as f32 * 50.0,
                400.0,
            ))],
        );
    }
    let still = harness.previews.stats();
    assert_eq!(
        (still.tasks_started, still.uploads),
        (warm.tasks_started, warm.uploads)
    );
    // Scroll far down: stale requests are dropped, new rows load, budgets hold.
    let at = Pos2::new(800.0, 600.0);
    for _ in 0..12 {
        harness.frame(
            &catalog,
            vec![
                Event::PointerMoved(at),
                Event::MouseWheel {
                    unit: egui::MouseWheelUnit::Point,
                    delta: Vec2::new(0.0, -800.0),
                    modifiers: Modifiers::NONE,
                },
            ],
        );
        harness.check_budgets();
        // This paint's view and screen ahead, plus the last paint's until
        // the next poll drops them.
        let stats = harness.previews.stats();
        assert!(stats.queued + stats.running <= 100, "{stats:?}");
    }
    harness.settle(&catalog);
    let cold = harness.previews.stats();
    assert!(
        cold.tasks_started > warm.tasks_started,
        "new rows were decoded"
    );
    assert!(cold.entries <= MAX_ENTRIES && cold.bytes <= MAX_BYTES);
    assert!(cold.largest_poll_upload <= UPLOAD_BUDGET, "{cold:?}");
    eprintln!(
        "library-previews: {} tasks, {} uploads, {} resident ({:.1} MiB), largest poll upload {:.0} KiB",
        cold.tasks_started,
        cold.uploads,
        cold.entries,
        cold.bytes as f64 / 1_048_576.0,
        cold.largest_poll_upload as f64 / 1024.0
    );
}

#[test]
fn list_rows_draw_each_subjects_signature_and_right_click_stacks_what_is_left() {
    let catalog = catalog(12, None);
    let mut harness = Harness::new();
    harness.station.view = LibraryView::List;
    harness.frame(&catalog, vec![]);
    let painted = harness.station.painted_rows().to_vec();
    assert!(!painted.is_empty() && painted.len() <= 12, "{painted:?}");
    // A signature on the first row: one bar per evidenced value, none for
    // a value without evidence, in the signature colour.
    harness
        .signatures
        .insert(painted[0], vec![0.2, 1.0, -1.0, 0.5]);
    let (output, _) = harness.frame(&catalog, vec![]);
    let colour = harness.palette.ok.gamma_multiply(0.75);
    let bars = |output: &egui::FullOutput| {
        output
            .shapes
            .iter()
            .filter(|s| matches!(&s.shape, egui::Shape::Rect(r) if r.fill == colour))
            .count()
    };
    assert_eq!(bars(&output), 3);
    // The grid's cards keep the mockup: no signatures there.
    harness.station.view = LibraryView::Grid;
    let (output, _) = harness.frame(&catalog, vec![]);
    assert_eq!(bars(&output), 0);
    assert!(harness.station.painted_rows().is_empty());
    // Subject 008 has a stack never stacked: right-click offers it.
    for stacking in [false, true] {
        harness.stacking = stacking;
        let (output, _) = harness.frame(&catalog, vec![]);
        let at = find(&output, "Subject 008").expect("drawn");
        harness.time += 1.0;
        let button = |pressed| Event::PointerButton {
            pos: at,
            button: PointerButton::Secondary,
            pressed,
            modifiers: Modifiers::NONE,
        };
        harness.frame(&catalog, vec![Event::PointerMoved(at), button(true)]);
        harness.frame(&catalog, vec![button(false)]);
        let (output, _) = harness.frame(&catalog, vec![]);
        let label = if stacking {
            "Stack next · 1 stack"
        } else {
            "Stack · 1 stack"
        };
        let item = find(&output, label).unwrap_or_else(|| panic!("{label}"));
        assert_eq!(
            harness.click(&catalog, item),
            Some(LibraryIntent::QueueSubject(subject_id(
                &catalog,
                "Subject 008"
            )))
        );
    }
    // A subject whose stacks all have renders offers nothing.
    let (output, _) = harness.frame(&catalog, vec![]);
    let at = find(&output, "Subject 009").expect("drawn");
    harness.time += 1.0;
    let button = |pressed| Event::PointerButton {
        pos: at,
        button: PointerButton::Secondary,
        pressed,
        modifiers: Modifiers::NONE,
    };
    harness.frame(&catalog, vec![Event::PointerMoved(at), button(true)]);
    harness.frame(&catalog, vec![button(false)]);
    let (output, _) = harness.frame(&catalog, vec![]);
    assert!(find(&output, "Stack · 1 stack").is_none());
    assert!(find(&output, "Stack next · 1 stack").is_none());
}

/// Offscreen picture of the list view with depth signatures, for the look
/// check. `STREHL_P4_SHOTS` names the folder.
#[test]
#[ignore = "needs a GPU; writes a PNG into STREHL_P4_SHOTS"]
fn offscreen_list_rows_with_signatures() {
    let shots =
        std::path::PathBuf::from(std::env::var_os("STREHL_P4_SHOTS").expect("STREHL_P4_SHOTS"));
    std::fs::create_dir_all(&shots).unwrap();
    let root = tempfile::tempdir().unwrap();
    let (catalog, _) = super::visual_tests::mockup_catalog(root.path());
    let signatures: HashMap<NodeId, Vec<f32>> = catalog
        .nodes
        .iter()
        .filter(|n| n.kind == NodeKind::Subject)
        .enumerate()
        .map(|(i, n)| {
            let centre = 30.0 + (i % 5) as f32 * 15.0;
            let values = (0..128)
                .map(|p| {
                    let d = (p as f32 - centre) / (10.0 + (i % 3) as f32 * 6.0);
                    let v = (-d * d).exp() * 0.8 + 0.04 * ((p * 7 + i) % 5) as f32;
                    if p % 41 == 40 { -1.0 } else { v }
                })
                .collect();
            (n.id, values)
        })
        .collect();
    let mut station = LibraryStation {
        view: LibraryView::List,
        ..Default::default()
    };
    let mut previews = LibraryPreviews::default();
    let palette = LibraryPalette::graphite();
    super::visual_tests::render(&shots.join("library-list.png"), |ui| {
        station.show(
            ui,
            LibraryInputs {
                catalog: &catalog,
                revision: catalog.generation(),
                previews: &mut previews,
                palette: &palette,
                rig: None,
                storage: None,
                signatures: Some(&signatures),
                stacking: true,
                deleting: None,
            },
        );
        !previews.pending()
    })
    .unwrap();
}

/// The list view with a 128-value signature on every row, pointer
/// sweeping: CPU paint plus tessellation per frame. Release:
/// `cargo test --release -- --ignored benchmark_list_rows_with_signatures`.
#[test]
#[ignore = "explicit CPU paint+tessellation benchmark of the list rows"]
fn benchmark_list_rows_with_signatures() {
    let catalog = catalog(200, None);
    let mut harness = Harness::new();
    harness.station.view = LibraryView::List;
    harness.signatures = catalog
        .nodes
        .iter()
        .filter(|n| n.kind == NodeKind::Subject)
        .map(|n| {
            let values = (0..128).map(|p| ((p as f32) * 0.1).sin().abs()).collect();
            (n.id, values)
        })
        .collect();
    for _ in 0..5 {
        harness.frame(&catalog, vec![]);
    }
    let built = harness.station.sparks.len();
    let mut times = Vec::new();
    for _ in 0..5 {
        let started = std::time::Instant::now();
        for step in 0..80 {
            let phase = step as f32 / 79.0;
            let at = Pos2::new(300.0 + phase * 1300.0, 160.0 + phase * 800.0);
            let (output, _) = harness.frame(&catalog, vec![Event::PointerMoved(at)]);
            std::hint::black_box(
                harness
                    .ctx
                    .tessellate(output.shapes, output.pixels_per_point),
            );
        }
        times.push(started.elapsed().as_secs_f64() * 1000.0 / 80.0);
    }
    assert_eq!(
        harness.station.sparks.len(),
        built,
        "pointer motion pools no signature again"
    );
    eprintln!(
        "library list, 200 subjects, {} rows painted, {built} signatures pooled: {:.3?} ms per frame",
        harness.station.painted_rows().len(),
        times
    );
}

/// Every picture mesh in a painted frame: (screen rect, uv rect).
fn picture_meshes(output: &egui::FullOutput) -> Vec<(Rect, Rect)> {
    fn visit(shape: &egui::Shape, found: &mut Vec<(Rect, Rect)>) {
        match shape {
            egui::Shape::Mesh(mesh) if mesh.texture_id != egui::TextureId::default() => {
                let rect =
                    Rect::from_points(&mesh.vertices.iter().map(|v| v.pos).collect::<Vec<_>>());
                let uv = Rect::from_points(&mesh.vertices.iter().map(|v| v.uv).collect::<Vec<_>>());
                found.push((rect, uv));
            }
            egui::Shape::Vec(shapes) => shapes.iter().for_each(|s| visit(s, found)),
            _ => {}
        }
    }
    let mut found = Vec::new();
    for clipped in &output.shapes {
        visit(&clipped.shape, &mut found);
    }
    found
}

/// Owner feedback, 2026-11-22: the cards "crop the actual subject". Every
/// picture on the grid and the list is drawn whole (uv 0..1) at its own
/// 3:2 aspect, inside a cell of another shape.
#[test]
fn grid_and_list_pictures_are_whole_at_their_own_aspect() {
    let pictures = tempfile::tempdir().unwrap();
    write_pictures(pictures.path(), 12);
    let catalog = catalog(12, Some(pictures.path()));
    for view in [LibraryView::Grid, LibraryView::List] {
        let mut harness = Harness::new();
        harness.station.view = view;
        harness.settle(&catalog);
        let (output, _) = harness.frame(&catalog, vec![]);
        let meshes = picture_meshes(&output);
        assert!(
            meshes.len() >= 10,
            "{view:?}: pictures painted: {}",
            meshes.len()
        );
        for (rect, uv) in meshes {
            assert!(
                uv == Rect::from_min_max(Pos2::ZERO, Pos2::new(1.0, 1.0)),
                "{view:?}: the whole picture, uncropped; uv x {}..{} y {}..{}",
                uv.min.x,
                uv.max.x,
                uv.min.y,
                uv.max.y
            );
            assert!(
                (rect.width() / rect.height() - 1.5).abs() < 0.02,
                "{view:?}: drawn at the picture's 3:2, not the cell's shape: {rect:?}"
            );
        }
    }
}

/// The grid scrolled with every picture resident: CPU paint plus
/// tessellation per frame (pictures 3:2, cells not). Release:
/// `cargo test --release -p strehl-ui -- --ignored benchmark_grid_scroll_with_pictures --nocapture`.
#[test]
#[ignore = "explicit CPU paint+tessellation benchmark of the grid scrolling with pictures"]
fn benchmark_grid_scroll_with_pictures() {
    let pictures = tempfile::tempdir().unwrap();
    write_pictures(pictures.path(), 200);
    let catalog = catalog(200, Some(pictures.path()));
    let mut harness = Harness::new();
    harness.station.sort = LibrarySort::Name;
    let at = Pos2::new(800.0, 600.0);
    let wheel = |dy: f32| {
        vec![
            Event::PointerMoved(at),
            Event::MouseWheel {
                unit: egui::MouseWheelUnit::Point,
                delta: Vec2::new(0.0, dy),
                modifiers: Modifiers::NONE,
            },
        ]
    };
    // Warm: walk the whole grid and back until every tile is resident.
    harness.settle(&catalog);
    for dy in [-240.0, 240.0] {
        for _ in 0..50 {
            harness.frame(&catalog, wheel(dy));
            harness.settle(&catalog);
        }
    }
    let warm = harness.previews.stats();
    let mut times = Vec::new();
    let mut images = 0;
    for _ in 0..5 {
        let started = std::time::Instant::now();
        for step in 0..120 {
            let (output, _) = harness.frame(&catalog, wheel(if step < 60 { -40.0 } else { 40.0 }));
            images = picture_meshes(&output).len();
            std::hint::black_box(
                harness
                    .ctx
                    .tessellate(output.shapes, output.pixels_per_point),
            );
        }
        times.push(started.elapsed().as_secs_f64() * 1000.0 / 120.0);
    }
    let after = harness.previews.stats();
    assert_eq!(
        after.tasks_started, warm.tasks_started,
        "the measured scroll decodes nothing: every tile is resident"
    );
    assert!(images >= 15, "pictures were drawn: {images}");
    eprintln!(
        "library grid scroll, 200 subjects, {} tiles resident, {images} pictures per frame: {:.3?} ms per frame",
        warm.entries, times
    );
}
