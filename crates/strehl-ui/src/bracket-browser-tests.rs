use super::*;
use crate::jobs::tests::TestDirectory;
use crate::preview::PreviewImage;
use crate::source_preview::SourcePreview;
use std::sync::mpsc;
use std::time::Instant;

fn fixture(path: &Path, tint: u8) {
    let pixels = image::RgbImage::from_fn(48, 32, |x, y| {
        image::Rgb([tint, (x * 5) as u8, (y * 7) as u8])
    });
    let mut jpeg = Vec::new();
    image::codecs::jpeg::JpegEncoder::new_with_quality(&mut jpeg, 85)
        .encode_image(&pixels)
        .unwrap();
    let mut bytes = vec![0; 64 + jpeg.len()];
    bytes[..8].copy_from_slice(b"II*\0\x08\0\0\0");
    bytes[8..10].copy_from_slice(&2_u16.to_le_bytes());
    for (index, (tag, value)) in [(513_u16, 64_u32), (514, jpeg.len() as u32)]
        .into_iter()
        .enumerate()
    {
        let offset = 10 + index * 12;
        bytes[offset..offset + 2].copy_from_slice(&tag.to_le_bytes());
        bytes[offset + 2..offset + 4].copy_from_slice(&4_u16.to_le_bytes());
        bytes[offset + 4..offset + 8].copy_from_slice(&1_u32.to_le_bytes());
        bytes[offset + 8..offset + 12].copy_from_slice(&value.to_le_bytes());
    }
    bytes[64..].copy_from_slice(&jpeg);
    fs::write(path, bytes).unwrap();
}

fn wait(
    browser: &mut BracketBrowser,
    ctx: &egui::Context,
    predicate: impl Fn(&BracketBrowser) -> bool,
) {
    let deadline = Instant::now() + Duration::from_secs(8);
    while !predicate(browser) && Instant::now() < deadline {
        browser.poll(ctx);
        browser.schedule();
        std::thread::sleep(Duration::from_millis(2));
    }
    assert!(
        predicate(browser),
        "The bounded background browser did not settle"
    );
}

#[test]
fn directory_counts_direct_arws_and_samples_filename_order_without_recursing() {
    let temporary = TestDirectory::new("bracket-directory-scope");
    let nested = temporary.path().join("nested");
    fs::create_dir(&nested).unwrap();
    for name in ["z.ARW", "a.arw", "m.ArW", "b.arw", "ignore.jpeg"] {
        fs::write(temporary.path().join(name), b"metadata fixture only").unwrap();
    }
    fs::write(nested.join("not-a-parent-frame.arw"), b"nested").unwrap();
    // A directory whose name looks like a RAW must stay a folder.
    fs::create_dir(temporary.path().join("folder.arw")).unwrap();
    let result = read_directory(temporary.path(), true, &AtomicBool::new(false)).unwrap();
    assert_eq!(result.contents.frames, 4);
    assert_eq!(
        result
            .contents
            .samples
            .iter()
            .map(|path| path.file_name().unwrap().to_str().unwrap())
            .collect::<Vec<_>>(),
        ["a.arw", "b.arw", "z.ARW"]
    );
    assert_eq!(result.folders.len(), 2);
    assert!(
        result
            .folders
            .iter()
            .all(|folder| folder.contents.is_none())
    );
    assert!(!result.contents.limited);
    assert!(read_directory(temporary.path(), true, &AtomicBool::new(true)).is_err());
}

#[test]
fn asynchronous_visible_child_gallery_uses_actual_embedded_jpegs_and_reaches_idle() {
    let temporary = TestDirectory::new("bracket-gallery-camera-pixels");
    let folder = temporary.path().join("subject");
    fs::create_dir(&folder).unwrap();
    for index in 0..5 {
        fixture(&folder.join(format!("frame-{index}.ARW")), 30 + index * 35);
    }
    let untouched = temporary.path().join("offscreen");
    fs::create_dir(&untouched).unwrap();
    fs::write(untouched.join("also.arw"), b"never opened").unwrap();
    let before = fs::read(folder.join("frame-2.ARW")).unwrap();
    let ctx = egui::Context::default();
    let mut browser = BracketBrowser::default();
    browser.open(Some(temporary.path().to_path_buf()));
    wait(&mut browser, &ctx, |b| b.directory.is_some());
    let canonical = fs::canonicalize(&folder).unwrap();
    browser.visible = vec![canonical.clone()];
    browser.selected = Some(canonical.clone());
    wait(&mut browser, &ctx, |b| {
        b.covers.len() == 3 && b.scan.is_none() && b.covers_work.is_none()
    });
    assert_eq!(browser.selection().unwrap().1.frames, 5);
    assert!(browser.covers.values().all(|cover| {
        cover
            .texture
            .as_ref()
            .is_some_and(|texture| texture.size() == [48, 32])
    }));
    let entry = browser
        .directory
        .as_ref()
        .unwrap()
        .folders
        .iter()
        .find(|folder| folder.path == canonical)
        .unwrap();
    let samples = &entry.contents.as_ref().unwrap().as_ref().unwrap().samples;
    assert_eq!(
        samples,
        &vec![
            canonical.join("frame-0.ARW"),
            canonical.join("frame-2.ARW"),
            canonical.join("frame-4.ARW")
        ],
        "The capture samples retain actual filename order"
    );
    let output = ctx.run(
        egui::RawInput {
            time: Some(10.0),
            ..Default::default()
        },
        |ctx| {
            egui::CentralPanel::default().show(ctx, |ui| {
                browser.card(
                    ui,
                    Rect::from_min_size(egui::pos2(20.0, 20.0), egui::vec2(280.0, 173.0)),
                    entry,
                    true,
                    false,
                    false,
                );
            });
        },
    );
    let areas: Vec<f32> = samples
        .iter()
        .map(|path| {
            let id = browser.covers[path].texture.as_ref().unwrap().id();
            output
                .shapes
                .iter()
                .find_map(|shape| match &shape.shape {
                    egui::Shape::Mesh(mesh) if mesh.texture_id == id => Some(
                        Rect::from_points(
                            &mesh
                                .vertices
                                .iter()
                                .map(|vertex| vertex.pos)
                                .collect::<Vec<_>>(),
                        )
                        .area(),
                    ),
                    _ => None,
                })
                .expect("All three real camera samples must remain painted")
        })
        .collect();
    assert!(
        areas[1] > areas[0] * 4.0 && areas[1] > areas[2] * 4.0,
        "The actual midpoint JPEG must be the large cover, with both endpoints retained as insets"
    );
    assert!(
        browser
            .directory
            .as_ref()
            .unwrap()
            .folders
            .iter()
            .find(|entry| entry.name == "offscreen")
            .unwrap()
            .contents
            .is_none(),
        "Only visible or explicitly selected folders may be probed"
    );
    assert_eq!(fs::read(folder.join("frame-2.ARW")).unwrap(), before);
    for _ in 0..5 {
        browser.poll(&ctx);
        browser.schedule();
    }
    assert!(
        browser.scan.is_none() && browser.covers_work.is_none(),
        "Completed covers must not create repeated background reads"
    );
}

#[test]
fn superseded_scan_and_pixels_cannot_cross_navigation_epoch_or_spawn_more_slots() {
    let temporary = TestDirectory::new("bracket-browser-generation");
    let target = temporary.path().join("new");
    fs::create_dir(&target).unwrap();
    fs::write(target.join("new.arw"), b"count without preview").unwrap();
    let ctx = egui::Context::default();
    let mut browser = BracketBrowser {
        active: true,
        ..Default::default()
    };
    browser.navigate(temporary.path().to_path_buf());
    let old_epoch = browser.epoch;
    let (scan_tx, scan_rx) = mpsc::sync_channel(1);
    browser.scan = Some(ScanWork {
        epoch: old_epoch,
        kind: ScanKind::Directory(temporary.path().to_path_buf()),
        task: spawn_task("held-old-directory", move |_| Ok(scan_rx.recv().unwrap())),
    });
    let (cover_tx, cover_rx) = mpsc::sync_channel(1);
    let old_photo = temporary.path().join("stale.arw");
    browser.covers_work = Some(CoverWork {
        epoch: old_epoch,
        paths: vec![old_photo.clone()],
        task: spawn_task("held-old-cover", move |_| Ok(cover_rx.recv().unwrap())),
    });
    browser.navigate(target.clone());
    browser.schedule();
    assert_eq!(
        browser.scan.as_ref().unwrap().epoch,
        old_epoch,
        "A replacement request must reuse the bounded slot after retirement"
    );
    assert_eq!(browser.covers_work.as_ref().unwrap().epoch, old_epoch);
    scan_tx
        .send(Directory {
            path: temporary.path().join("wrong"),
            contents: Contents {
                frames: 999,
                ..Contents::default()
            },
            folders: Vec::new(),
        })
        .unwrap();
    cover_tx
        .send(vec![(
            0,
            Ok(SourcePreview {
                image: PreviewImage {
                    path: old_photo.clone(),
                    source_size: [1, 1],
                    size: [1, 1],
                    rgba: vec![255; 4],
                    is_overview: false,
                },
                thumbnail: None,
            }),
        )])
        .unwrap();
    wait(&mut browser, &ctx, |b| {
        b.directory.is_some() && b.covers_work.is_none()
    });
    assert_eq!(
        browser.directory.as_ref().unwrap().path,
        fs::canonicalize(target).unwrap()
    );
    assert_eq!(browser.directory.as_ref().unwrap().contents.frames, 1);
    assert!(!browser.covers.contains_key(&old_photo));
    browser.close();
    assert!(!browser.active());
    assert!(browser.covers.is_empty());
}

#[test]
fn unreadable_preview_does_not_retry_and_invalid_folder_can_be_replaced() {
    let temporary = TestDirectory::new("bracket-browser-errors");
    let ctx = egui::Context::default();
    let mut browser = BracketBrowser::default();
    browser.open(Some(temporary.path().join("missing")));
    wait(&mut browser, &ctx, |b| b.error.is_some());
    assert!(browser.directory.is_none());
    fs::write(temporary.path().join("bad.arw"), b"not a camera container").unwrap();
    browser.navigate(temporary.path().to_path_buf());
    wait(&mut browser, &ctx, |b| {
        b.directory.is_some() && b.covers.len() == 1 && b.covers_work.is_none()
    });
    assert!(browser.error.is_none());
    assert!(browser.covers.values().all(|cover| cover.texture.is_none()));
    for _ in 0..5 {
        browser.poll(&ctx);
        browser.schedule();
    }
    assert!(browser.covers_work.is_none());
    assert_eq!(
        browser.selection().unwrap().1.frames,
        1,
        "Broken embedded JPEG does not invalidate a stack's RAW files"
    );
}

#[test]
fn modal_has_stable_gallery_cells_and_crop_bounds_for_real_covers() {
    let temporary = TestDirectory::new("bracket-browser-paint");
    fixture(&temporary.path().join("frame.arw"), 110);
    let ctx = egui::Context::default();
    let mut browser = BracketBrowser::default();
    browser.open(Some(temporary.path().to_path_buf()));
    wait(&mut browser, &ctx, |b| {
        b.directory.is_some() && b.covers.len() == 1 && b.covers_work.is_none()
    });
    for (width, height) in [(1060.0, 720.0), (1440.0, 900.0)] {
        // egui first sizes a modal invisibly. Let that actual layout pass run
        // before checking visible cells; the JPEG remains cached throughout.
        let _ = ctx.run(
            egui::RawInput {
                screen_rect: Some(Rect::from_min_size(
                    egui::Pos2::ZERO,
                    egui::vec2(width, height),
                )),
                time: Some(10.0),
                ..Default::default()
            },
            |ctx| {
                let _ = browser.show(ctx);
            },
        );
        let output = ctx.run(
            egui::RawInput {
                screen_rect: Some(Rect::from_min_size(
                    egui::Pos2::ZERO,
                    egui::vec2(width, height),
                )),
                time: Some(10.0),
                ..Default::default()
            },
            |ctx| {
                assert!(browser.show(ctx).is_none());
            },
        );
        assert!(!output.shapes.is_empty());
        assert!(!browser.visible.is_empty());
        assert_eq!(browser.covers.len(), 1);
    }
    for image in [egui::vec2(48.0, 32.0), egui::vec2(32.0, 48.0)] {
        let uv = crop_uv(image, egui::vec2(246.0, 117.0));
        assert!(Rect::from_min_max(egui::Pos2::ZERO, egui::pos2(1.0, 1.0)).contains_rect(uv));
        assert!(
            uv.width() < 1.0 || uv.height() < 1.0,
            "Fixture must exercise real crop rather than identity UVs"
        );
    }
}

fn browser_frame(
    browser: &mut BracketBrowser,
    ctx: &egui::Context,
    time: f64,
    events: Vec<egui::Event>,
) -> (egui::FullOutput, Option<PathBuf>) {
    let mut selected = None;
    let output = ctx.run(
        egui::RawInput {
            screen_rect: Some(Rect::from_min_size(
                egui::Pos2::ZERO,
                egui::vec2(1060.0, 720.0),
            )),
            time: Some(time),
            events,
            ..Default::default()
        },
        |ctx| selected = browser.show(ctx),
    );
    (output, selected)
}

fn pointer(position: egui::Pos2, pressed: bool) -> Vec<egui::Event> {
    vec![
        egui::Event::PointerMoved(position),
        egui::Event::PointerButton {
            pos: position,
            button: egui::PointerButton::Primary,
            pressed,
            modifiers: egui::Modifiers::NONE,
        },
    ]
}

fn browser_key(key: egui::Key, modifiers: egui::Modifiers) -> egui::Event {
    egui::Event::Key {
        key,
        physical_key: Some(key),
        pressed: true,
        repeat: false,
        modifiers,
    }
}

fn painted_label(output: &egui::FullOutput, label: &str) -> Rect {
    output
        .shapes
        .iter()
        .find_map(|shape| match &shape.shape {
            egui::Shape::Text(text) if text.galley.text() == label => {
                Some(text.visual_bounding_rect().intersect(shape.clip_rect))
            }
            _ => None,
        })
        .unwrap_or_else(|| panic!("Expected visible label: {label}"))
}

#[test]
fn history_restores_location_selection_and_scroll_but_never_old_scan_or_pixels() {
    let temporary = TestDirectory::new("bracket-history-generation");
    let first = temporary.path().join("first");
    let child = first.join("selected");
    let second = temporary.path().join("second");
    fs::create_dir_all(&child).unwrap();
    fs::create_dir(&second).unwrap();
    fixture(&first.join("real.arw"), 60);
    fixture(&child.join("real.arw"), 130);
    let first = fs::canonicalize(first).unwrap();
    let child = fs::canonicalize(child).unwrap();
    let second = fs::canonicalize(second).unwrap();
    let ctx = egui::Context::default();
    let mut browser = BracketBrowser::default();
    browser.open(Some(first.clone()));
    browser.directory = Some(read_directory(&first, true, &AtomicBool::new(false)).unwrap());
    browser.selected = Some(child.clone());
    browser.gallery_scroll = 277.0;
    let stale_epoch = browser.epoch;
    let (scan_tx, scan_rx) = mpsc::sync_channel(1);
    browser.scan = Some(ScanWork {
        epoch: stale_epoch,
        kind: ScanKind::Directory(first.clone()),
        task: spawn_task("held-history-directory", move |_| {
            Ok(scan_rx.recv().unwrap())
        }),
    });
    let stale_photo = first.join("stale.arw");
    let (cover_tx, cover_rx) = mpsc::sync_channel(1);
    browser.covers_work = Some(CoverWork {
        epoch: stale_epoch,
        paths: vec![stale_photo.clone()],
        task: spawn_task("held-history-cover", move |_| Ok(cover_rx.recv().unwrap())),
    });
    browser.navigate(second.clone());
    browser.gallery_scroll = 47.0;
    browser.traverse(true);
    assert_eq!(browser.path, first);
    assert_eq!(browser.selected, Some(child.clone()));
    assert_eq!(browser.restore_scroll, Some(277.0));
    assert!(browser.directory.is_none() && browser.covers.is_empty());
    assert_eq!(browser.scan.as_ref().unwrap().epoch, stale_epoch);
    assert_eq!(browser.covers_work.as_ref().unwrap().epoch, stale_epoch);
    assert_ne!(
        browser.epoch, stale_epoch,
        "Returning to the identical path is a fresh generation"
    );
    scan_tx
        .send(Directory {
            path: first.clone(),
            contents: Contents {
                frames: 999,
                ..Default::default()
            },
            folders: Vec::new(),
        })
        .unwrap();
    cover_tx
        .send(vec![(
            0,
            Ok(SourcePreview {
                image: PreviewImage {
                    path: stale_photo.clone(),
                    source_size: [1, 1],
                    size: [1, 1],
                    rgba: vec![255; 4],
                    is_overview: false,
                },
                thumbnail: None,
            }),
        )])
        .unwrap();
    let deadline = Instant::now() + Duration::from_secs(8);
    while (browser.scan.is_some() || browser.covers_work.is_some()) && Instant::now() < deadline {
        browser.poll(&ctx);
        std::thread::sleep(Duration::from_millis(2));
    }
    assert!(browser.scan.is_none() && browser.covers_work.is_none());
    assert!(
        browser.directory.is_none(),
        "A same-path old scan must not reappear through history"
    );
    assert!(
        browser.covers.is_empty(),
        "History stores no prior decoded camera pixels"
    );
    wait(&mut browser, &ctx, |b| b.selection().is_some());
    assert_eq!(browser.directory.as_ref().unwrap().contents.frames, 1);
    assert_eq!(browser.selection().unwrap().0, &child);
    assert!(!browser.covers.contains_key(&stale_photo));
    browser.traverse(false);
    assert_eq!(browser.path, second);
    assert_eq!(browser.restore_scroll, Some(47.0));
    assert!(browser.directory.is_none() && browser.covers.is_empty());
    browser.traverse(true);
    browser.navigate(temporary.path().to_path_buf());
    assert!(
        browser.forward.is_empty(),
        "A new branch must discard the abandoned forward path"
    );
    browser.open(Some(first));
    assert!(
        browser.back.is_empty() && browser.forward.is_empty(),
        "A fresh chooser session has its own history"
    );
}

#[test]
fn gallery_arrows_focus_space_selects_and_ctrl_enter_opens_that_valid_selection() {
    let temporary = TestDirectory::new("bracket-arrow-selection");
    for name in ["First", "Second"] {
        let child = temporary.path().join(name);
        fs::create_dir(&child).unwrap();
        fixture(&child.join("photo.arw"), 100);
    }
    let first = fs::canonicalize(temporary.path().join("First")).unwrap();
    let second = fs::canonicalize(temporary.path().join("Second")).unwrap();
    let ctx = egui::Context::default();
    theme::install(&ctx);
    let mut browser = BracketBrowser::default();
    browser.open(Some(temporary.path().to_path_buf()));
    wait(&mut browser, &ctx, |b| b.directory.is_some());
    for time in [1.0, 1.1, 1.2] {
        let _ = browser_frame(&mut browser, &ctx, time, vec![]);
    }
    wait(&mut browser, &ctx, |b| {
        b.directory
            .as_ref()
            .unwrap()
            .folders
            .iter()
            .all(|f| f.contents.is_some())
    });
    let (output, _) = browser_frame(&mut browser, &ctx, 2.0, vec![]);
    let point = painted_label(&output, "First").center();
    let _ = browser_frame(&mut browser, &ctx, 2.1, pointer(point, true));
    let _ = browser_frame(&mut browser, &ctx, 2.2, pointer(point, false));
    let (output, chosen) = browser_frame(
        &mut browser,
        &ctx,
        2.3,
        vec![
            egui::Event::PointerGone,
            browser_key(egui::Key::ArrowRight, egui::Modifiers::NONE),
        ],
    );
    assert!(chosen.is_none());
    assert_eq!(
        browser.selection().unwrap().0,
        &first,
        "Arrows move focus without silently selecting"
    );
    let second_label = painted_label(&output, "Second");
    assert!(output.shapes.iter().any(|shape| matches!(&shape.shape,
        egui::Shape::Rect(rect) if rect.stroke.width == 2.0
        && rect.stroke.color == theme::ACCENT && rect.rect.contains_rect(second_label))));
    let (_, chosen) = browser_frame(
        &mut browser,
        &ctx,
        2.4,
        vec![browser_key(egui::Key::Space, egui::Modifiers::NONE)],
    );
    assert!(chosen.is_none());
    assert_eq!(browser.selection().unwrap().0, &second);
    let (_, chosen) = browser_frame(
        &mut browser,
        &ctx,
        2.5,
        vec![browser_key(egui::Key::Enter, egui::Modifiers::CTRL)],
    );
    assert_eq!(chosen, Some(second));
    assert!(!browser.active());
}

#[test]
fn location_shortcut_edits_text_without_navigating_and_alt_keys_traverse_real_history() {
    let temporary = TestDirectory::new("bracket-path-shortcuts");
    let child = temporary.path().join("Child");
    fs::create_dir(&child).unwrap();
    fixture(&child.join("photo.arw"), 120);
    let parent = fs::canonicalize(temporary.path()).unwrap();
    let child = fs::canonicalize(child).unwrap();
    let ctx = egui::Context::default();
    theme::install(&ctx);
    let mut browser = BracketBrowser::default();
    browser.open(Some(parent.clone()));
    wait(&mut browser, &ctx, |b| b.directory.is_some());
    browser.navigate(child.clone());
    wait(&mut browser, &ctx, |b| b.directory.is_some());
    for time in [1.0, 1.1, 1.2] {
        let _ = browser_frame(&mut browser, &ctx, time, vec![]);
    }
    let _ = browser_frame(
        &mut browser,
        &ctx,
        2.0,
        vec![browser_key(egui::Key::L, egui::Modifiers::CTRL)],
    );
    let focused = ctx
        .memory(|m| m.focused())
        .expect("Ctrl+L must focus the path field");
    let state = egui::TextEdit::load_state(&ctx, focused)
        .expect("The focused control must be the editable path");
    let range = state.cursor.char_range().unwrap();
    assert_eq!(range.sorted_cursors()[0].index, 0);
    assert_eq!(
        range.sorted_cursors()[1].index,
        browser.path_text.chars().count()
    );
    let epoch = browser.epoch;
    let _ = browser_frame(
        &mut browser,
        &ctx,
        2.1,
        vec![egui::Event::Text("Uncommitted path".into())],
    );
    assert_eq!(browser.path_text, "Uncommitted path");
    let _ = browser_frame(
        &mut browser,
        &ctx,
        2.2,
        vec![browser_key(egui::Key::Backspace, egui::Modifiers::NONE)],
    );
    assert_eq!(browser.path_text, "Uncommitted pat");
    assert_eq!(
        browser.epoch, epoch,
        "Editing/backspace must not browse or clear covers"
    );
    let _ = browser_frame(
        &mut browser,
        &ctx,
        2.3,
        vec![browser_key(egui::Key::ArrowLeft, egui::Modifiers::ALT)],
    );
    assert_eq!(browser.path, parent);
    let _ = browser_frame(
        &mut browser,
        &ctx,
        2.4,
        vec![browser_key(egui::Key::ArrowRight, egui::Modifiers::ALT)],
    );
    assert_eq!(browser.path, child);
    let _ = browser_frame(
        &mut browser,
        &ctx,
        2.5,
        vec![browser_key(egui::Key::ArrowUp, egui::Modifiers::ALT)],
    );
    assert_eq!(browser.path, parent);
    assert!(
        browser.active(),
        "Navigation must not open the bracket or close the chooser"
    );
}

#[test]
fn end_focus_reveals_the_last_card_and_back_restores_its_actual_scrolled_view() {
    let temporary = TestDirectory::new("bracket-keyboard-long-gallery");
    for index in 0..24 {
        fs::create_dir(temporary.path().join(format!("Bracket {index:02}"))).unwrap();
    }
    let last = temporary.path().join("Bracket 23");
    fixture(&last.join("photo.arw"), 100);
    let last = fs::canonicalize(last).unwrap();
    let parent = fs::canonicalize(temporary.path()).unwrap();
    let ctx = egui::Context::default();
    theme::install(&ctx);
    let mut browser = BracketBrowser::default();
    browser.open(Some(parent.clone()));
    wait(&mut browser, &ctx, |b| b.directory.is_some());
    for time in [1.0, 1.1, 1.2] {
        let _ = browser_frame(&mut browser, &ctx, time, vec![]);
    }
    let (output, _) = browser_frame(&mut browser, &ctx, 2.0, vec![]);
    let point = painted_label(&output, "Bracket 00").center();
    let _ = browser_frame(&mut browser, &ctx, 2.1, pointer(point, true));
    let _ = browser_frame(&mut browser, &ctx, 2.2, pointer(point, false));
    assert!(
        !browser.visible.contains(&last),
        "The destination must begin offscreen"
    );
    let _ = browser_frame(
        &mut browser,
        &ctx,
        2.3,
        vec![
            egui::Event::PointerGone,
            browser_key(egui::Key::End, egui::Modifiers::NONE),
        ],
    );
    for time in [2.4, 2.6, 2.9] {
        let _ = browser_frame(&mut browser, &ctx, time, vec![]);
    }
    let (output, _) = browser_frame(&mut browser, &ctx, 3.0, vec![]);
    let rect = painted_label(&output, "Bracket 23");
    assert!(
        rect.width() > 20.0 && rect.height() > 5.0,
        "End must visibly reveal the focused card"
    );
    assert!(
        browser.gallery_scroll > 500.0,
        "Fixture must move multiple actual rows"
    );
    let _ = browser_frame(
        &mut browser,
        &ctx,
        3.1,
        vec![browser_key(egui::Key::Space, egui::Modifiers::NONE)],
    );
    assert_eq!(browser.selected, Some(last.clone()));
    let remembered_scroll = browser.gallery_scroll;
    let _ = browser_frame(
        &mut browser,
        &ctx,
        3.2,
        vec![browser_key(egui::Key::Enter, egui::Modifiers::NONE)],
    );
    assert_eq!(browser.path, last);
    wait(&mut browser, &ctx, |b| b.directory.is_some());
    let _ = browser_frame(
        &mut browser,
        &ctx,
        3.8,
        vec![browser_key(egui::Key::ArrowLeft, egui::Modifiers::ALT)],
    );
    assert_eq!(browser.path, parent);
    wait(&mut browser, &ctx, |b| b.directory.is_some());
    for time in [4.0, 4.1, 4.4] {
        let _ = browser_frame(&mut browser, &ctx, time, vec![]);
    }
    let (output, _) = browser_frame(&mut browser, &ctx, 4.6, vec![]);
    let rect = painted_label(&output, "Bracket 23");
    assert!(rect.width() > 20.0 && rect.height() > 5.0);
    assert_eq!(browser.selected, Some(last));
    assert!(
        (browser.gallery_scroll - remembered_scroll).abs() < 1.0,
        "Back must preserve the actual view rather than restart the filmstrip"
    );
}

#[test]
fn exploring_this_folder_keeps_actual_preview_and_generation_steady() {
    let temporary = TestDirectory::new("bracket-this-folder-no-jank");
    fixture(&temporary.path().join("photo.arw"), 150);
    let ctx = egui::Context::default();
    let mut browser = BracketBrowser::default();
    browser.open(Some(temporary.path().to_path_buf()));
    wait(&mut browser, &ctx, |b| {
        b.directory.is_some() && !b.covers.is_empty() && b.covers_work.is_none()
    });
    for time in [1.0, 1.1, 1.2] {
        let _ = browser_frame(&mut browser, &ctx, time, vec![]);
    }
    let (output, _) = browser_frame(&mut browser, &ctx, 2.0, vec![]);
    let point = painted_label(&output, "This folder").center();
    let epoch = browser.epoch;
    let texture = browser
        .covers
        .values()
        .next()
        .unwrap()
        .texture
        .as_ref()
        .unwrap()
        .id();
    let _ = browser_frame(&mut browser, &ctx, 2.1, pointer(point, true));
    let _ = browser_frame(&mut browser, &ctx, 2.2, pointer(point, false));
    let (output, chosen) = browser_frame(
        &mut browser,
        &ctx,
        2.3,
        vec![browser_key(egui::Key::Enter, egui::Modifiers::NONE)],
    );
    assert!(chosen.is_none());
    assert!(browser.active() && browser.directory.is_some());
    assert_eq!(
        browser.epoch, epoch,
        "Entering the folder already shown must not reload it"
    );
    assert!(
        output.shapes.iter().any(|shape| matches!(&shape.shape,
        egui::Shape::Mesh(mesh) if mesh.texture_id == texture)),
        "The original actual camera cover must remain painted"
    );
}

#[test]
fn long_named_child_can_be_selected_and_opened_through_real_visible_controls() {
    let temporary = TestDirectory::new("bracket-visible-open-control");
    let name = "A very long macro bracket title showing tiny crystals and delicate transparent edges photographed in a continuous focus sweep with polarized illumination";
    let child = temporary.path().join(name);
    fs::create_dir(&child).unwrap();
    fixture(&child.join("one.ARW"), 100);
    fixture(&child.join("two.ARW"), 180);
    let ctx = egui::Context::default();
    let mut browser = BracketBrowser::default();
    browser.open(Some(temporary.path().to_path_buf()));
    wait(&mut browser, &ctx, |b| b.directory.is_some());
    for time in [1.0, 1.1, 1.2] {
        let _ = browser_frame(&mut browser, &ctx, time, vec![]);
    }
    wait(&mut browser, &ctx, |b| {
        b.directory.as_ref().unwrap().folders[0].contents.is_some()
            && b.covers.len() == 2
            && b.covers_work.is_none()
    });
    let (output, _) = browser_frame(&mut browser, &ctx, 2.0, vec![]);
    let point = output
        .shapes
        .iter()
        .find_map(|shape| match &shape.shape {
            egui::Shape::Text(text) if text.galley.text() == name => Some(
                text.visual_bounding_rect()
                    .intersect(shape.clip_rect)
                    .center(),
            ),
            _ => None,
        })
        .expect("Actual long-named child card text must be painted");
    let _ = browser_frame(&mut browser, &ctx, 2.1, pointer(point, true));
    let (_, chosen) = browser_frame(&mut browser, &ctx, 2.2, pointer(point, false));
    assert!(
        chosen.is_none(),
        "Single-click selects the bracket for inspection"
    );
    let canonical = fs::canonicalize(child).unwrap();
    assert_eq!(browser.selection().unwrap().0, &canonical);
    let (output, _) = browser_frame(&mut browser, &ctx, 2.3, vec![]);
    let label = output
        .shapes
        .iter()
        .find_map(|shape| match &shape.shape {
            egui::Shape::Text(text) if text.galley.text() == "Use these photos" => {
                Some(text.visual_bounding_rect())
            }
            _ => None,
        })
        .expect("Open action must survive a long selected title");
    let button = output
        .shapes
        .iter()
        .find_map(|shape| match &shape.shape {
            egui::Shape::Rect(rect)
                if rect.fill == theme::PANEL
                    && rect.stroke.color == theme::ACCENT
                    && rect.rect.contains(label.center()) =>
            {
                Some(rect.rect)
            }
            _ => None,
        })
        .expect("Open action must have a real visible button surface");
    assert!(
        Rect::from_min_max(egui::Pos2::ZERO, egui::pos2(1060.0, 720.0)).contains_rect(button),
        "Entire Open button must fit the supported narrow viewport: {button:?}"
    );
    assert!(button.contains_rect(label));
    let _ = browser_frame(&mut browser, &ctx, 2.4, pointer(button.center(), true));
    let (_, chosen) = browser_frame(&mut browser, &ctx, 2.5, pointer(button.center(), false));
    assert_eq!(chosen, Some(canonical));
    assert!(!browser.active());
}

#[test]
fn focused_gallery_folder_has_a_visible_outline_and_enter_explores_without_opening_a_stack() {
    let temporary = TestDirectory::new("bracket-keyboard-explore");
    let first = temporary.path().join("First bracket");
    let second = temporary.path().join("Second bracket");
    fs::create_dir(&first).unwrap();
    fs::create_dir(&second).unwrap();
    fixture(&first.join("one.ARW"), 80);
    fixture(&second.join("two.ARW"), 160);
    let ctx = egui::Context::default();
    crate::theme::install(&ctx);
    let mut browser = BracketBrowser::default();
    browser.open(Some(temporary.path().to_path_buf()));
    wait(&mut browser, &ctx, |b| b.directory.is_some());
    for time in [1.0, 1.1, 1.2] {
        let _ = browser_frame(&mut browser, &ctx, time, vec![]);
    }
    wait(&mut browser, &ctx, |b| {
        b.directory
            .as_ref()
            .unwrap()
            .folders
            .iter()
            .all(|folder| folder.contents.is_some())
    });
    let (output, _) = browser_frame(&mut browser, &ctx, 2.0, vec![]);
    let label = |output: &egui::FullOutput, name: &str| {
        output
            .shapes
            .iter()
            .find_map(|shape| match &shape.shape {
                egui::Shape::Text(text) if text.galley.text() == name => {
                    Some(text.visual_bounding_rect())
                }
                _ => None,
            })
            .expect("Both real folder cards must be visible")
    };
    let point = label(&output, "First bracket").center();
    let _ = browser_frame(&mut browser, &ctx, 2.1, pointer(point, true));
    let (_, chosen) = browser_frame(&mut browser, &ctx, 2.2, pointer(point, false));
    assert!(chosen.is_none());
    let first = fs::canonicalize(first).unwrap();
    let second = fs::canonicalize(second).unwrap();
    assert_eq!(browser.selection().unwrap().0, &first);
    let key = |key| egui::Event::Key {
        key,
        physical_key: Some(key),
        pressed: true,
        repeat: false,
        modifiers: egui::Modifiers::NONE,
    };
    let (output, chosen) = browser_frame(
        &mut browser,
        &ctx,
        2.3,
        vec![egui::Event::PointerGone, key(egui::Key::Tab)],
    );
    assert!(chosen.is_none());
    assert_eq!(
        browser.selection().unwrap().0,
        &first,
        "Moving focus must not silently change the selected bracket"
    );
    let second_label = label(&output, "Second bracket");
    assert!(
        output.shapes.iter().any(|shape| matches!(&shape.shape,
            egui::Shape::Rect(rect) if rect.stroke.width == 2.0
                && rect.stroke.color == theme::ACCENT
                && rect.rect.contains_rect(second_label)
        )),
        "The unselected keyboard destination must have its own visible focus outline"
    );
    let (_, chosen) = browser_frame(&mut browser, &ctx, 2.4, vec![key(egui::Key::Enter)]);
    assert!(
        chosen.is_none(),
        "Enter explores the focused folder; only Open bracket returns a stack"
    );
    assert!(browser.active());
    assert_eq!(browser.path, second);
    assert!(browser.selected.is_none());
}

#[test]
fn screenshot_readiness_waits_for_visible_work_and_reveal_but_not_offscreen_folders() {
    let temporary = TestDirectory::new("bracket-readiness");
    let child = temporary.path().join("visible");
    fs::create_dir(&child).unwrap();
    fixture(&child.join("photo.arw"), 100);
    let ctx = egui::Context::default();
    let mut browser = BracketBrowser::default();
    browser.open(Some(temporary.path().to_path_buf()));
    assert!(!browser.settled(20.0), "An unscanned root cannot be ready");
    wait(&mut browser, &ctx, |b| {
        b.directory.is_some() && b.roots_work.is_none()
    });
    assert!(
        !browser.settled(20.0),
        "A directory must be painted to establish visible cells"
    );
    let _ = browser_frame(&mut browser, &ctx, 1.0, vec![]);
    assert!(
        !browser.settled(20.0),
        "An invisible modal sizing pass must not bypass visible child work"
    );
    let _ = browser_frame(&mut browser, &ctx, 1.1, vec![]);
    assert!(
        !browser.visible.is_empty(),
        "Fixture must paint the child before waiting for its real cover"
    );
    assert!(
        !browser.settled(20.0),
        "The newly visible child must really require its background scan"
    );
    wait(&mut browser, &ctx, |b| {
        b.covers.len() == 1 && b.covers_work.is_none()
    });
    let arrived = browser.covers.values().next().unwrap().arrived;
    assert!(
        !browser.settled(arrived + 0.09),
        "A half-faded actual JPEG must not be called settled"
    );
    assert!(browser.settled(arrived + 0.19));
    let photo = browser.covers.keys().next().unwrap().clone();
    let cover = browser.covers.remove(&photo).unwrap();
    assert!(
        !browser.settled(arrived + 1.0),
        "A missing visible cover must reject readiness independently of task-slot state"
    );
    browser.covers.insert(photo, cover);
    browser.directory.as_mut().unwrap().folders.push(Folder {
        path: temporary.path().join("not visible"),
        name: "not visible".into(),
        link: false,
        contents: None,
    });
    assert!(
        browser.settled(arrived + 1.0),
        "Unobserved offscreen folders do not block the shot"
    );
    browser.navigate(temporary.path().join("does not exist"));
    assert!(!browser.settled(20.0));
    wait(&mut browser, &ctx, |b| b.error.is_some());
    let _ = browser_frame(&mut browser, &ctx, 3.0, vec![]);
    assert!(
        browser.settled(3.0),
        "An idle, painted folder error is a complete UI state"
    );
}

#[test]
fn editable_paths_preserve_network_roots() {
    assert_eq!(
        display_path(Path::new(r"\\?\UNC\camera-server\photos\macro")),
        r"\\camera-server\photos\macro"
    );
    assert_eq!(
        display_path(Path::new(r"\\?\C:\photos\macro")),
        r"C:\photos\macro"
    );
    assert_eq!(
        display_path(Path::new(r"\\camera-server\photos\macro")),
        r"\\camera-server\photos\macro"
    );
}

#[test]
fn compact_library_stays_below_native_title_and_close_only_dismisses_the_chooser() {
    use crate::window_chrome;
    let temporary = TestDirectory::new("compact-library-native-title");
    for index in 0..12 {
        let folder = temporary
            .path()
            .join(format!("Photographic bracket {index:02}"));
        fs::create_dir(&folder).unwrap();
        fixture(&folder.join("camera.ARW"), 40 + index * 10);
    }
    let ctx = egui::Context::default();
    theme::install(&ctx);
    let mut browser = BracketBrowser::default();
    browser.open(Some(temporary.path().to_path_buf()));
    wait(&mut browser, &ctx, |browser| {
        browser.directory.is_some() && browser.roots_work.is_none()
    });
    // Exercise both independently scrollable panes. This longer Places list
    // must not push the header upward or the footer below the actual window.
    browser.roots = (b'A'..=b'Z')
        .map(|letter| PathBuf::from(format!("{}:\\", char::from(letter))))
        .collect();
    browser.recent = (0..6)
        .map(|index| temporary.path().join(format!("Recent bracket {index}")))
        .collect();
    let viewport = Rect::from_min_size(egui::Pos2::ZERO, egui::vec2(1060.0, 720.0));
    let frame = |browser: &mut BracketBrowser, time: f64, events: Vec<egui::Event>| {
        let mut selected = None;
        let output = ctx.run(
            egui::RawInput {
                screen_rect: Some(viewport),
                time: Some(time),
                events,
                ..Default::default()
            },
            |ctx| {
                egui::CentralPanel::default().show(ctx, |_| {});
                selected = browser.show(ctx);
                window_chrome::finish(ctx, browser.active());
            },
        );
        (output, selected)
    };
    for time in [0.0, 0.1, 0.2] {
        let _ = frame(&mut browser, time, vec![]);
    }
    let (output, _) = frame(&mut browser, 0.3, vec![]);
    assert!(
        !browser.visible.is_empty(),
        "the fixture must paint the actual populated gallery"
    );
    let below_title = Rect::from_min_max(egui::pos2(window_chrome::RAIL_WIDTH, 0.0), viewport.max);
    let window_dock = window_chrome::dock_rect(viewport);
    let label = |name: &str| {
        let (bounds, clip) = output
            .shapes
            .iter()
            .find_map(|shape| match &shape.shape {
                egui::Shape::Text(text) if text.galley.text() == name => {
                    Some((text.visual_bounding_rect(), shape.clip_rect))
                }
                _ => None,
            })
            .expect("real modal control must be painted");
        assert!(
            below_title.contains_rect(bounds) && clip.contains_rect(bounds),
            "{name:?} must be entirely visible beside the native controls: {bounds:?}"
        );
        assert!(
            !window_dock.intersects(bounds),
            "{name:?} cannot be covered by native window controls: {bounds:?} vs {window_dock:?}"
        );
        bounds
    };
    let close_label = label("Close");
    let _ = label("Choose a bracket");
    let _ = label("CAMERA LIBRARY");
    let _ = label("Use these photos");
    let close = output
        .shapes
        .iter()
        .filter_map(|shape| match &shape.shape {
            egui::Shape::Rect(rect) if rect.rect.contains_rect(close_label) => Some(rect.rect),
            _ => None,
        })
        .min_by(|a, b| a.area().total_cmp(&b.area()))
        .expect("Close needs its real visible button surface");
    assert!(below_title.contains_rect(close));
    assert!(
        !window_dock.expand(4.0).intersects(close),
        "the entire chooser Close hit area must stay separate from native controls"
    );
    let modal_frame = output
        .shapes
        .iter()
        .find_map(|shape| match &shape.shape {
            egui::Shape::Rect(rect)
                if rect.fill == theme::PANEL
                    && rect.stroke.color == theme::LINE
                    && rect.rect.width() > 900.0
                    && rect.rect.height() > 500.0 =>
            {
                Some(rect.rect)
            }
            _ => None,
        })
        .expect("bounded library frame must be present");
    assert!(
        Rect::from_min_max(
            egui::pos2(window_chrome::RAIL_WIDTH + 16.0, 12.0),
            egui::pos2(1044.0, 704.0)
        )
        .contains_rect(modal_frame),
        "the composed modal, not only its nominal minimum height, must fit beside the native rail: {modal_frame:?}"
    );
    let (pressed, selected) = frame(&mut browser, 0.4, pointer(close.center(), true));
    assert!(browser.active() && selected.is_none());
    let (released, selected) = frame(&mut browser, 0.5, pointer(close.center(), false));
    assert!(
        !browser.active() && selected.is_none(),
        "the actual chooser Close must dismiss its modal"
    );
    for output in [pressed, released] {
        assert!(
            !output.viewport_output[&egui::ViewportId::ROOT]
                .commands
                .iter()
                .any(|command| matches!(command, egui::ViewportCommand::Close)),
            "closing the chooser must never emit the native application Close command"
        );
    }
}
