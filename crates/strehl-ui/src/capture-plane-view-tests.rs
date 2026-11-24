//! The plane view: placing and zooming the picture, the tiles in view, the
//! strip's bars, the facts, following and "Show".
use super::super::planes::{DeckSnapshot, FixtureSource, Level, TryInfo};
use super::*;
use std::time::Duration;

fn image(size: [u32; 2]) -> PlaneImage {
    let mut levels = vec![Level {
        stride: 1,
        size,
        rgb: Vec::new(),
    }];
    while levels.last().unwrap().size.iter().any(|s| *s > 1024) {
        let l = levels.last().unwrap();
        levels.push(Level {
            stride: l.stride * 2,
            size: l.size.map(|s| s.div_ceil(2)),
            rgb: Vec::new(),
        });
    }
    PlaneImage {
        id: 1,
        key: TryKey::default(),
        size,
        frame: size,
        levels,
        kind: ImageKind::FourShot,
        findings: None,
        iso: None,
        display_ev: 0.0,
        cost: [0.0; 3],
    }
}

/// Fit centres the whole picture; a zoom keeps the picture over the area
/// (its centre clamped), and zooming out past fit returns to fit.
#[test]
fn the_picture_is_placed_fitted_or_zoomed_and_clamped() {
    let area = Rect::from_min_size(egui::pos2(10.0, 20.0), egui::vec2(600.0, 300.0));
    let mut view = PlaneView::default();
    let (img, scale) = place(area, [9504, 6336], &mut view);
    assert!((img.height() - 300.0).abs() < 0.01 && (img.center() - area.center()).length() < 0.01);
    assert!((scale - 300.0 / 6336.0).abs() < 1e-6);
    // 100 % near the top-left corner: the corner stays at the area's.
    view.set_zoom(Some(1.0), egui::pos2(0.0, 0.0));
    let (img, scale) = place(area, [9504, 6336], &mut view);
    assert_eq!(scale, 1.0);
    assert_eq!(img.min, area.min);
    assert!(view.center.x > 0.0 && view.center.y > 0.0);
    view.set_zoom(Some(0.001), egui::pos2(0.5, 0.5));
    let (_, scale) = place(area, [9504, 6336], &mut view);
    assert!(scale > 0.001 && view.zoom.is_none(), "below fit is fit");
}

/// The tiles in view at a stride cover the aperture, nearest the centre
/// first; at fit the overview is enough.
#[test]
fn the_tiles_in_view_cover_the_aperture() {
    let im = image([9504, 6336]);
    assert_eq!(im.overview().stride, 16);
    let whole = Rect::from_min_max(egui::Pos2::ZERO, egui::pos2(1.0, 1.0));
    assert_eq!(
        stride_for(&im, whole, [500, 333]),
        None,
        "fit: the overview"
    );
    // The 594 px overview is short of a 600 px view: stride 8 tiles.
    assert_eq!(stride_for(&im, whole, [600, 400]), Some(8));
    assert_eq!(stride_for(&im, whole, [2400, 1600]), Some(2));
    // 100 % of a 600 x 400 view in the middle: stride 1, one or two tiles.
    let mid = Rect::from_center_size(
        egui::pos2(0.5, 0.5),
        egui::vec2(600.0 / 9504.0, 400.0 / 6336.0),
    );
    assert_eq!(stride_for(&im, mid, [600, 400]), Some(1));
    let keys = tiles_in(&im, 1, mid);
    assert!(!keys.is_empty() && keys.len() <= 4, "{keys:?}");
    for k in &keys {
        let core = Rect::from_min_max(
            egui::pos2((k.x * TILE) as f32 / 9504.0, (k.y * TILE) as f32 / 6336.0),
            egui::pos2(
                ((k.x + 1) * TILE) as f32 / 9504.0,
                ((k.y + 1) * TILE) as f32 / 6336.0,
            ),
        );
        assert!(core.intersects(mid), "{k:?}");
    }
    let all = tiles_in(&im, 2, whole);
    assert_eq!(all.len(), 20, "4752 x 3168 at stride 2: 5 x 4 tiles");
    let first = all[0];
    assert_eq!((first.x, first.y), (2, 1), "the centre first");
}

fn try_info(plane: u64, attempt: u32, map: Option<Vec<u16>>) -> TryInfo {
    TryInfo {
        t: super::super::planes::PlaneTry {
            plane,
            attempt,
            names: vec![Arc::from(format!("frame-{:06}.ARW", plane * 4).as_str())],
            paths: vec![],
            focus: Some(30_000 + plane as u16 * 7),
            taken_ms: None,
        },
        share: map
            .as_ref()
            .map(|m| m.iter().filter(|v| **v > 40_000).count() as f32 / m.len() as f32),
        map: map.map(Into::into),
    }
}

fn snapshot() -> DeckSnapshot {
    // Four cells; planes 1-3 sharp in cells 0, 1 and 1-2.
    let maps = [
        vec![40_500, 33_000, 33_000, 33_000],
        vec![33_000, 40_500, 33_000, 33_000],
        vec![33_000, 40_500, 40_500, 33_000],
    ];
    DeckSnapshot {
        revision: 1,
        tries: maps
            .iter()
            .enumerate()
            .map(|(i, m)| try_info(i as u64 + 1, 1, Some(m.clone())))
            .collect(),
        grid: [2, 2],
        preview: [64, 64],
        max: vec![40_500, 40_500, 40_500, 33_000].into(),
        floor: 39_000,
        polled: true,
        ..Default::default()
    }
}

/// The overlap of two planes' sharp cells, and the strip's bars from the
/// shares and the checker's marks.
#[test]
fn neighbours_overlap_and_bars_carry_shares_and_marks() {
    let snap = snapshot();
    let map = |i: usize| snap.tries[i].map.clone().unwrap();
    assert_eq!(
        overlap(&snap, &map(0), &map(1)),
        Some(0.0),
        "planes 1 and 2 share nothing"
    );
    assert_eq!(overlap(&snap, &map(2), &map(1)), Some(0.5));
    assert_eq!(overlap(&snap, &map(1), &map(2)), Some(1.0));
    let progress = super::super::fixture::progress();
    let b = bars(&snap, Some(&progress), 96);
    assert_eq!(b.len(), 96);
    assert_eq!(b[0].share, Some(0.25));
    assert_eq!(b[2].share, Some(0.5));
    assert_eq!(b[50].mark, Some(Mark::Ok), "plane 51 passed");
    assert_eq!(b[51].mark, Some(Mark::Bad), "plane 52 failed every try");
    assert!(b[2].retaken, "plane 3 was retaken");
    assert_eq!(b[23].mark, Some(Mark::Bad), "plane 24: a pattern failure");
    assert_eq!(b[80].mark, None, "plane 81 is to come");
    // Plane 60 asked for a retake not taken yet: it waits (one try here
    // as in the fixture's deck).
    let mut snap = snap;
    snap.tries.push(try_info(60, 1, None));
    assert_eq!(bars(&snap, Some(&progress), 96)[59].mark, Some(Mark::Warn));
}

/// The verdict says what the stack does with the try.
#[test]
fn the_verdict_says_what_the_stack_does() {
    let progress = super::super::fixture::progress();
    let item = |plane: u64, attempt: u32| {
        progress
            .feed
            .iter()
            .find(|i| i.plane == plane && i.attempt == attempt)
    };
    let (mark, title, then) = verdict_text(item(10, 1), true, None, true);
    assert_eq!(
        (mark, title.as_str(), then.as_str()),
        (Mark::Ok, "Four shots agree", "The stack uses this try.")
    );
    let (mark, title, then) = verdict_text(item(39, 1), false, Some(2), true);
    assert_eq!(mark, Mark::Warn);
    assert_eq!(title, "Shots differ in places");
    assert!(then.ends_with("Retaken: try 2 follows."), "{then}");
    let (mark, _, then) = verdict_text(item(24, 1), true, None, true);
    assert_eq!(mark, Mark::Bad);
    assert!(
        then.ends_with("The stack uses its first shot here."),
        "{then}"
    );
    assert_eq!(verdict_text(None, true, None, false).1, "Checking is off");
}

fn texts(out: &egui::FullOutput) -> Vec<String> {
    fn walk(shape: &egui::Shape, into: &mut Vec<String>) {
        match shape {
            egui::Shape::Text(t) => into.push(t.galley.text().to_owned()),
            egui::Shape::Vec(v) => v.iter().for_each(|s| walk(s, into)),
            _ => {}
        }
    }
    let mut all = Vec::new();
    for s in &out.shapes {
        walk(&s.shape, &mut all);
    }
    all
}

fn key(k: egui::Key) -> egui::Event {
    egui::Event::Key {
        key: k,
        physical_key: None,
        pressed: true,
        repeat: false,
        modifiers: Default::default(),
    }
}

/// Paints the panel until `done`, with `events` on the first frame.
fn run(
    ctx: &egui::Context,
    deck: &mut PlaneDeck,
    view: &mut PlaneView,
    mut events: Vec<egui::Event>,
    done: impl Fn(&PlaneDeck, &[String]) -> bool,
) -> Vec<String> {
    let progress = super::super::fixture::progress();
    let palette = CapturePalette::default();
    let end = Instant::now() + Duration::from_secs(60);
    loop {
        deck.poll();
        let out = ctx.run(
            egui::RawInput {
                screen_rect: Some(Rect::from_min_size(
                    egui::Pos2::ZERO,
                    egui::vec2(900.0, 640.0),
                )),
                events: std::mem::take(&mut events),
                ..Default::default()
            },
            |ctx| {
                egui::CentralPanel::default()
                    .frame(egui::Frame::NONE)
                    .show(ctx, |ui| {
                        let inputs = PlaneInputs {
                            progress: Some(&progress),
                            total: 96,
                            checking: true,
                            exposure: Some("ISO 100 · 1/8 s".into()),
                        };
                        let rect = ui.max_rect();
                        panel(ui, rect, Some(&mut *deck), view, &inputs, &palette);
                    });
            },
        );
        let t = texts(&out);
        if done(deck, &t) {
            return t;
        }
        assert!(Instant::now() < end, "timed out: {t:?}");
        std::thread::sleep(Duration::from_millis(15));
    }
}

/// The panel follows the newest try; "Show" picks a try and holds it with
/// its verdict and the checker's numbers; ← steps back a plane; End returns
/// to the newest.
#[test]
fn the_panel_follows_the_newest_and_show_picks_a_try() {
    let progress = super::super::fixture::progress();
    let source = FixtureSource::new(&progress, 96, [480, 320]);
    let mut deck = PlaneDeck::start(std::path::PathBuf::from("fixture"), Box::new(source));
    let ctx = egui::Context::default();
    crate::theme::install(&ctx);
    deck.set_uploader(None, &ctx);
    let mut view = PlaneView::default();
    // The fixture's newest try is plane 61 (plane 60's retake is not checked).
    let newest = progress.feed.last().map(|i| i.plane).unwrap();
    let t = run(&ctx, &mut deck, &mut view, vec![], |d, t| {
        d.settled() && t.iter().any(|s| s.starts_with("PLANE "))
    });
    assert!(
        t.iter().any(|s| s.starts_with("following the newest")),
        "{t:?}"
    );
    assert!(
        t.iter()
            .any(|s| s == &format!("PLANE {newest}") || s.starts_with(&format!("PLANE {newest} "))),
        "{t:?}"
    );
    assert!(t.iter().any(|s| s.starts_with("Sharp in ")), "{t:?}");
    // Following at fit, the camera's preview is the picture: no RAW read.
    assert!(
        t.iter().any(|s| s.starts_with("The camera's preview")),
        "{t:?}"
    );
    // Show plane 52's second try (the feed's "Show").
    let first = progress
        .feed
        .iter()
        .find(|i| i.plane == 52 && i.attempt == 2)
        .and_then(|i| i.first.clone());
    view.show(52, first);
    let t = run(&ctx, &mut deck, &mut view, vec![], |d, t| {
        d.settled() && t.iter().any(|s| s == "PLANE 52 · TRY 2 OF 3")
    });
    assert!(!view.following);
    assert!(
        t.iter().any(|s| s.starts_with("Shots differ in places")),
        "{t:?}"
    );
    assert!(
        t.iter()
            .any(|s| s.starts_with("Shots differ in places by ")),
        "{t:?}"
    );
    assert!(t.iter().any(|s| s.starts_with("Newest · ")), "{t:?}");
    // ← goes to plane 51 (its last try).
    run(
        &ctx,
        &mut deck,
        &mut view,
        vec![key(egui::Key::ArrowLeft)],
        |_, t| t.iter().any(|s| s == "PLANE 51"),
    );
    // End: back to the newest.
    run(
        &ctx,
        &mut deck,
        &mut view,
        vec![key(egui::Key::End)],
        |_, t| t.iter().any(|s| s.starts_with("following the newest")),
    );
    assert!(view.following);
}
