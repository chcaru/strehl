use super::*;
use crate::pipeline::{DiagnosticKind, DiagnosticScale, DiagnosticScope, DiagnosticSurface};
use std::time::{Duration, Instant};

const EXTENT: [usize; 2] = [1001, 701];
const DOMAIN: [u64; 2] = [1, 0];

/// Planes whose kept block slides across the frame, at every detail size.
fn archive(planes: usize) -> AdmissionArchive {
    let mut archive = AdmissionArchive::default();
    let mut sequence = 0;
    for level in 0..DETAIL_LEVELS {
        let spacing = 1usize << level;
        let size = [
            EXTENT[0].div_ceil(spacing).min(32),
            EXTENT[1].div_ceil(spacing).min(24),
        ];
        for plane in 0..planes {
            sequence += 1;
            let start = plane * size[0] / planes.max(1);
            let pixels = (0..size[0] * size[1])
                .map(|index| {
                    let (x, y) = (index % size[0], index / size[0]);
                    let width = (size[0] / 3).max(4);
                    if (start..start + width).contains(&x)
                        && (size[1] / 5..size[1] * 4 / 5).contains(&y)
                    {
                        255
                    } else {
                        0
                    }
                })
                .collect::<Vec<_>>();
            archive.ingest(
                &DiagnosticSurface {
                    sequence,
                    frame: plane,
                    level,
                    kind: DiagnosticKind::GateSupport,
                    scope: DiagnosticScope::Frame,
                    scale: DiagnosticScale::Linear,
                    width: size[0],
                    height: size[1],
                    min: 0.0,
                    max: 1.0,
                    folded: 1,
                    pixels: pixels.into(),
                },
                EXTENT,
            );
        }
    }
    archive
}

fn evidence(archive: &AdmissionArchive) -> LensEvidence<'_> {
    LensEvidence {
        archive,
        domain: DOMAIN,
        extent: Some(EXTENT),
        settings: RegionSettings::default(),
        geometry: None,
    }
}

fn wait(
    ctx: &egui::Context,
    view: &mut PlaneLensView,
    mut lookup: impl FnMut(&mut PlaneLensView) -> bool,
) {
    let deadline = Instant::now() + Duration::from_secs(5);
    loop {
        if lookup(view) {
            return;
        }
        assert!(Instant::now() < deadline, "region worker did not finish");
        std::thread::sleep(Duration::from_millis(1));
        let _ = ctx;
    }
}

#[test]
fn hover_peeks_click_holds_and_leaving_returns_to_the_held_plane() {
    let mut lens = PlaneLens::default();
    lens.set_planes(299);
    assert_eq!(lens.shown(), None);
    lens.hover(Some(127));
    assert!(lens.peeking());
    assert_eq!(lens.shown(), Some(127));
    assert_eq!(lens.inspection(), (Some(127), None));
    lens.click(127);
    assert!(lens.holding());
    assert_eq!(lens.held(), Some(127));
    assert_eq!(lens.shown(), Some(127));
    // While holding, hovering shows another plane; leaving returns.
    lens.hover(Some(127));
    assert_eq!(
        lens.hovered(),
        None,
        "the clicked hover is the held plane itself"
    );
    lens.hover(Some(200));
    assert_eq!(lens.shown(), Some(200));
    assert!(!lens.peeking(), "holding shows the two-up, not a peek");
    assert_eq!(lens.inspection(), (Some(200), Some(127)));
    lens.hover(None);
    assert_eq!(lens.shown(), Some(127));
    // A click holds a new plane; clicking the held plane releases it.
    lens.click(40);
    assert_eq!(lens.held(), Some(40));
    lens.click(40);
    assert_eq!(lens.held(), None);
    assert_eq!(lens.shown(), None);
}

#[test]
fn arrows_step_one_shift_steps_ten_clamped_and_escape_releases() {
    let mut lens = PlaneLens::default();
    lens.set_planes(299);
    assert!(
        !lens.key(LensKey::Right, false),
        "keys do nothing until a plane is held"
    );
    lens.click(127);
    assert!(lens.key(LensKey::Right, false));
    assert_eq!(lens.held(), Some(128));
    assert!(lens.key(LensKey::Left, true));
    assert_eq!(lens.held(), Some(118));
    for _ in 0..40 {
        lens.key(LensKey::Left, true);
    }
    assert_eq!(lens.held(), Some(0));
    for _ in 0..40 {
        lens.key(LensKey::Right, true);
    }
    assert_eq!(lens.held(), Some(298));
    // A key step hides the stale hover until the pointer names a new plane.
    lens.hover(Some(10));
    assert_eq!(lens.shown(), Some(10));
    lens.key(LensKey::Left, false);
    assert_eq!(lens.held(), Some(297));
    assert_eq!(lens.shown(), Some(297));
    lens.hover(Some(10));
    assert_eq!(
        lens.shown(),
        Some(297),
        "the same stationary hover stays hidden"
    );
    lens.hover(Some(11));
    assert_eq!(lens.shown(), Some(11));
    assert!(lens.key(LensKey::Escape, false));
    assert!(!lens.holding());
    assert!(!lens.key(LensKey::Escape, false), "nothing left to release");
}

#[test]
fn read_keys_uses_each_pressed_event_modifiers() {
    let ctx = egui::Context::default();
    let mut lens = PlaneLens::default();
    lens.set_planes(299);
    lens.click(127);
    let key = |key, shift| egui::Event::Key {
        key,
        physical_key: None,
        pressed: true,
        repeat: false,
        modifiers: egui::Modifiers {
            shift,
            ..Default::default()
        },
    };
    let _ = ctx.run(
        egui::RawInput {
            events: vec![
                key(egui::Key::ArrowRight, false),
                key(egui::Key::ArrowLeft, true),
            ],
            ..Default::default()
        },
        |ctx| {
            egui::CentralPanel::default().show(ctx, |ui| {
                assert!(lens.read_keys(ui));
            });
        },
    );
    assert_eq!(lens.held(), Some(118));
}

#[test]
fn the_plane_lens_without_a_plane_holds_the_last_or_the_default() {
    let mut lens = PlaneLens::default();
    lens.set_planes(50);
    lens.choose_plane_lens(84);
    assert_eq!(lens.held(), Some(49), "the default clamps to the stack");
    lens.click(12);
    lens.release();
    lens.choose_plane_lens(0);
    assert_eq!(lens.held(), Some(12), "the last held plane wins");
    lens.set_planes(10);
    assert_eq!(
        lens.held(),
        None,
        "a shorter stack drops planes it no longer has"
    );
    lens.set_level(42);
    assert_eq!(lens.level(), DETAIL_LEVELS - 1);
}

#[test]
fn regions_are_extracted_off_the_paint_path_and_the_previous_one_stays() {
    let archive = archive(40);
    let ctx = egui::Context::default();
    let mut view = PlaneLensView::default();
    let first = view.region(&ctx, evidence(&archive), 10, 0);
    assert!(
        !first.current,
        "the first request is answered by the worker"
    );
    assert!(first.region.is_none(), "nothing was shown before");
    assert!(view.pending());
    wait(&ctx, &mut view, |view| {
        view.region(&ctx, evidence(&archive), 10, 0).current
    });
    let ready = view.region(&ctx, evidence(&archive), 10, 0);
    assert_eq!((ready.frame, ready.level), (Some(10), Some(0)));
    let shown = ready.region.clone().expect("a coherent block has a region");
    // A new plane keeps the old region, named as such, until its own is ready.
    let next = view.region(&ctx, evidence(&archive), 11, 0);
    assert!(!next.current);
    assert_eq!(next.frame, Some(10));
    assert!(Arc::ptr_eq(next.region.as_ref().unwrap(), &shown));
    wait(&ctx, &mut view, |view| {
        view.region(&ctx, evidence(&archive), 11, 0).current
    });
    // Scrubbing back is a cache hit: no worker, same region.
    let back = view.region(&ctx, evidence(&archive), 10, 0);
    assert!(back.current && !view.pending());
    assert!(Arc::ptr_eq(back.region.as_ref().unwrap(), &shown));
    // A plane without a map is an immediate, honest "no region".
    let missing = view.region(&ctx, evidence(&archive), 400, 0);
    assert!(missing.current && missing.region.is_none());
}

#[test]
fn layout_matches_the_reference_rectangles() {
    let canvas = Rect::from_min_size(egui::pos2(0.0, 80.0), egui::vec2(1332.0, 756.0));
    let layout = two_up_layout(canvas, 1.5);
    let close = |rect: Rect, expected: [f32; 4]| {
        let actual = [rect.left(), rect.top(), rect.width(), rect.height()];
        assert!(
            actual
                .iter()
                .zip(expected)
                .all(|(a, e)| (a - e).abs() <= 2.0),
            "{actual:?} vs {expected:?}"
        );
    };
    close(layout.bounds, [16.0, 162.0, 1300.0, 591.0]);
    close(layout.final_photo, [16.0, 186.0, 643.0, 429.0]);
    close(layout.plane_photo, [673.0, 186.0, 643.0, 429.0]);
    assert!((layout.sizes[7].right() - 1316.0).abs() <= 2.0);
    assert!(
        layout
            .sizes
            .windows(2)
            .all(|pair| pair[0].right() < pair[1].left())
    );
    let rail = Rect::from_min_size(egui::pos2(0.0, 867.0), egui::vec2(1332.0, 84.0));
    close(
        peek_rect(canvas, rail, 299, 127).unwrap(),
        [385.0, 552.0, 372.0, 276.0],
    );
    close(
        peek_rect(canvas, rail, 299, 0).unwrap(),
        [10.0, 552.0, 372.0, 276.0],
    );
    // A short canvas scales the photographs, never overflows.
    let short = two_up_layout(
        Rect::from_min_size(egui::pos2(0.0, 0.0), egui::vec2(1332.0, 500.0)),
        1.5,
    );
    assert!(short.bounds.bottom() <= 500.0 && short.final_photo.height() > 100.0);
}

fn run(
    ctx: &egui::Context,
    events: Vec<egui::Event>,
    mut paint: impl FnMut(&mut Ui),
) -> egui::FullOutput {
    ctx.run(
        egui::RawInput {
            screen_rect: Some(Rect::from_min_size(Pos2::ZERO, egui::vec2(1332.0, 1050.0))),
            events,
            ..Default::default()
        },
        |ctx| {
            egui::CentralPanel::default()
                .frame(egui::Frame::NONE)
                .show(ctx, |ui| paint(ui));
        },
    )
}

fn meshes(output: &egui::FullOutput) -> Vec<Arc<egui::Mesh>> {
    output
        .shapes
        .iter()
        .filter_map(|clipped| match &clipped.shape {
            egui::Shape::Mesh(mesh) => Some(mesh.clone()),
            _ => None,
        })
        .collect()
}

#[test]
fn two_up_draws_eight_size_maps_marks_the_size_and_a_click_sets_it() {
    let archive = archive(40);
    let ctx = egui::Context::default();
    let texture = ctx.load_texture(
        "final",
        egui::ColorImage::filled([30, 20], Color32::GRAY),
        egui::TextureOptions::LINEAR,
    );
    let photo = LensPhoto {
        texture: texture.id(),
        uv: Rect::from_min_max(Pos2::ZERO, egui::pos2(1.0, 1.0)),
        aspect: 1.5,
    };
    let canvas = Rect::from_min_size(egui::pos2(0.0, 80.0), egui::vec2(1332.0, 756.0));
    let layout = two_up_layout(canvas, 1.5);
    let mut view = PlaneLensView::default();
    let paint = |view: &mut PlaneLensView, events: Vec<egui::Event>, level: usize| {
        let mut response = TwoUpResponse::default();
        let output = run(&ctx, events, |ui| {
            response = view.paint_two_up(
                ui,
                &layout,
                evidence(&archive),
                20,
                level,
                photo,
                Some(photo),
                LensPalette::GRAPHITE,
            );
        });
        (output, response)
    };
    // Let the worker finish the main region and all eight maps.
    let deadline = Instant::now() + Duration::from_secs(10);
    loop {
        let _ = paint(&mut view, vec![], 0);
        let all = (0..DETAIL_LEVELS).all(|level| {
            view.worker
                .ready(
                    &archive,
                    DOMAIN,
                    20,
                    level,
                    EXTENT,
                    RegionSettings::default(),
                )
                .is_some()
        });
        if all && !view.pending() {
            break;
        }
        assert!(Instant::now() < deadline, "size maps did not warm");
        std::thread::sleep(Duration::from_millis(1));
    }
    let (first, _) = paint(&mut view, vec![], 0);
    let texts: Vec<String> = first
        .shapes
        .iter()
        .filter_map(|clipped| match &clipped.shape {
            egui::Shape::Text(text) => Some(text.galley.text().to_owned()),
            _ => None,
        })
        .collect();
    assert_eq!(
        texts.iter().filter(|text| text.ends_with("kept")).count(),
        DETAIL_LEVELS
    );
    assert!(texts.iter().any(|text| text == SOURCE_CAPTION));
    assert!(
        texts
            .iter()
            .any(|text| text.starts_with("where plane 21 was kept, at 1 px"))
    );
    // Pointer motion over the canvas reuses every cached region mesh.
    let before = meshes(&first);
    let (moved, _) = paint(
        &mut view,
        vec![egui::Event::PointerMoved(layout.final_photo.center())],
        0,
    );
    // Region meshes are untextured; photographs are textured quads.
    let regions: Vec<_> = meshes(&moved)
        .into_iter()
        .filter(|mesh| mesh.texture_id == egui::TextureId::default())
        .collect();
    assert!(
        regions.len() >= DETAIL_LEVELS,
        "{} region meshes",
        regions.len()
    );
    assert!(
        regions
            .iter()
            .all(|mesh| before.iter().any(|old| Arc::ptr_eq(old, mesh))),
        "pointer motion rebuilt a region mesh"
    );
    // A click on the 64 px map (level 5) moves the switch.
    let at = layout.sizes[5].center();
    let press = egui::Event::PointerButton {
        pos: at,
        button: egui::PointerButton::Primary,
        pressed: true,
        modifiers: Default::default(),
    };
    let release = egui::Event::PointerButton {
        pos: at,
        button: egui::PointerButton::Primary,
        pressed: false,
        modifiers: Default::default(),
    };
    let _ = paint(&mut view, vec![egui::Event::PointerMoved(at)], 0);
    let _ = paint(&mut view, vec![press], 0);
    let (_, clicked) = paint(&mut view, vec![release], 0);
    assert_eq!(clicked.level, Some(5));
}

#[test]
fn prefetching_size_maps_never_replaces_the_region_kept_on_screen() {
    let archive = archive(40);
    let ctx = egui::Context::default();
    let mut view = PlaneLensView::default();
    wait(&ctx, &mut view, |view| {
        view.region(&ctx, evidence(&archive), 5, 0).current
    });
    let shown = view.region(&ctx, evidence(&archive), 5, 0).region.unwrap();
    wait(&ctx, &mut view, |view| {
        view.worker
            .prefetch(
                &ctx,
                &archive,
                DOMAIN,
                5,
                6,
                EXTENT,
                RegionSettings::default(),
            )
            .is_some()
    });
    let next = view.region(&ctx, evidence(&archive), 6, 0);
    assert!(!next.current);
    assert_eq!((next.frame, next.level), (Some(5), Some(0)));
    assert!(Arc::ptr_eq(next.region.as_ref().unwrap(), &shown));
}

#[test]
fn shares_and_labels_read_the_archive_once_per_revision() {
    let archive = archive(12);
    let mut view = PlaneLensView::default();
    let shares = view.shares(&archive, 3);
    assert!(shares.iter().all(Option::is_some));
    assert_eq!(view.shares(&archive, 3), shares);
    assert_eq!(percent(Some(0.026)), "2.6 %");
    assert_eq!(percent(Some(0.27)), "27 %");
    assert_eq!(percent(None), "not recorded");
    assert_eq!(size_label(0, None), "1 px");
}
