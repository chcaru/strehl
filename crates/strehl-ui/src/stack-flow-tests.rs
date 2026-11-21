//! The mockup's interaction checks (check.html, spec 10.1 items 1-5 and 9),
//! ported at the module level: rail, filmstrip, plane lens and core sample
//! wired the way the Stack station composes them. Stage 2 repeats these
//! through the full app.
use crate::{
    core_sample::{CoreAction, CoreInput, CorePalette, CoreResponse, CoreSample},
    depth_rail::{DepthRail, RailGeometry, RailMarkers, RailPalette, evidence_revision},
    filmstrip::{FilmMarks, FilmPalette, Filmstrip},
    pipeline::{
        DiagnosticKind, DiagnosticScale, DiagnosticScope, DiagnosticSurface, PipelineProgress,
    },
    plane_lens::{
        LensEvidence, LensPalette, LensPhoto, PlaneLens, PlaneLensView, TwoUpResponse,
        two_up_layout,
    },
    process_admission_regions::RegionSettings,
};
use eframe::egui::{self, Color32, Pos2, Rect, Shape};

const ANALYSIS: [usize; 2] = [3516, 2344];
const PLANES: usize = 130;
const PHOTO: Rect = Rect {
    min: Pos2 { x: 128.0, y: 94.0 },
    max: Pos2 {
        x: 1204.0,
        y: 812.0,
    },
};
const CANVAS: Rect = Rect {
    min: Pos2 { x: 0.0, y: 80.0 },
    max: Pos2 {
        x: 1332.0,
        y: 836.0,
    },
};
const RAIL: Rect = Rect {
    min: Pos2 { x: 0.0, y: 867.0 },
    max: Pos2 {
        x: 1332.0,
        y: 951.0,
    },
};
const FILM: Rect = Rect {
    min: Pos2 { x: 0.0, y: 951.0 },
    max: Pos2 {
        x: 1332.0,
        y: 1026.0,
    },
};

fn progress() -> PipelineProgress {
    let mut progress = PipelineProgress::default();
    let mut sequence = 0;
    for level in 0..8 {
        let spacing = 1usize << level;
        let width = ANALYSIS[0].div_ceil(spacing).min(128);
        let height = ANALYSIS[1].div_ceil(spacing).min(96);
        for plane in 0..PLANES {
            sequence += 1;
            let centre = (plane as f32 + 0.5) / PLANES as f32;
            let reach = 0.08 + 0.02 * level as f32;
            progress.admission_archive.ingest(
                &DiagnosticSurface {
                    sequence,
                    frame: plane,
                    level,
                    kind: DiagnosticKind::GateSupport,
                    scope: DiagnosticScope::Frame,
                    scale: DiagnosticScale::Linear,
                    width,
                    height,
                    min: 0.0,
                    max: 1.0,
                    folded: 1,
                    pixels: (0..width * height)
                        .map(|index| {
                            let x = (index % width) as f32 / width as f32;
                            if (x - centre).abs() < reach { 255 } else { 0 }
                        })
                        .collect::<Vec<_>>()
                        .into(),
                },
                ANALYSIS,
            );
        }
    }
    progress
}

#[derive(Default)]
struct Station {
    rail: DepthRail,
    film: Filmstrip,
    core: CoreSample,
    lens: PlaneLens,
    view: PlaneLensView,
    two_up: TwoUpResponse,
    sample: CoreResponse,
}

fn frame(
    ctx: &egui::Context,
    station: &mut Station,
    progress: &PipelineProgress,
    texture: egui::TextureId,
    events: Vec<egui::Event>,
) -> egui::FullOutput {
    station.lens.set_planes(PLANES);
    ctx.run(
        egui::RawInput {
            screen_rect: Some(Rect::from_min_size(Pos2::ZERO, egui::vec2(1680.0, 1050.0))),
            events,
            ..Default::default()
        },
        |ctx| {
            egui::CentralPanel::default()
                .frame(egui::Frame::NONE)
                .show(ctx, |ui| {
                    let archive = &progress.admission_archive;
                    let level = station.lens.level();
                    station.rail.update(
                        archive,
                        &progress.sampled_mask_history,
                        PLANES,
                        level,
                        evidence_revision(progress),
                    );
                    station.film.layout(FILM.width(), PLANES);
                    station.film.update(archive);
                    let rail = station.rail.interact(ui, RAIL, egui::Id::new("rail"));
                    let film = station.film.interact(ui, FILM, egui::Id::new("film"));
                    station.lens.hover(rail.hovered.or(film.hovered));
                    if let Some(plane) = rail.clicked.or(film.clicked) {
                        station.lens.click(plane);
                    }
                    station.lens.read_keys(ui);
                    let photo = LensPhoto {
                        texture,
                        uv: Rect::from_min_max(Pos2::ZERO, egui::pos2(1.0, 1.0)),
                        aspect: 1.5,
                    };
                    let evidence = LensEvidence {
                        archive,
                        domain: [1, 0],
                        extent: Some(ANALYSIS),
                        settings: RegionSettings::default(),
                        geometry: None,
                    };
                    if let (Some(plane), true) = (station.lens.shown(), station.lens.holding()) {
                        let layout = two_up_layout(CANVAS, 1.5);
                        station.two_up = station.view.paint_two_up(
                            ui,
                            &layout,
                            evidence,
                            plane,
                            level,
                            photo,
                            Some(photo),
                            LensPalette::GRAPHITE,
                        );
                        if let Some(level) = station.two_up.level {
                            station.lens.set_level(level);
                        }
                    } else {
                        station.sample = station.core.show(
                            ui,
                            CoreInput {
                                archive,
                                level,
                                analysis_extent: ANALYSIS,
                                extent: [7032, 4688],
                                planes: PLANES,
                                image: PHOTO,
                                aperture: photo.uv,
                                final_texture: Some(texture),
                                geometry: None,
                                viewport: Rect::from_min_size(
                                    Pos2::ZERO,
                                    egui::vec2(1332.0, 1050.0),
                                ),
                            },
                            &|_| None,
                            CorePalette::GRAPHITE,
                        );
                        if let Some(CoreAction::ShowPlane(plane)) = station.sample.action {
                            station.lens.hold(plane);
                        }
                        if let Some(plane) = station.lens.shown() {
                            let lookup = station.view.region(ui.ctx(), evidence, plane, level);
                            if let Some(card) =
                                crate::plane_lens::peek_rect(CANVAS, RAIL, PLANES, plane)
                            {
                                let share = crate::plane_lens::kept_share(archive, level, plane);
                                station.view.paint_peek(
                                    ui.painter(),
                                    card,
                                    RailGeometry::new(RAIL, PLANES).unwrap().x(plane),
                                    plane,
                                    share,
                                    None,
                                    lookup.region.as_ref(),
                                    LensPalette::GRAPHITE,
                                );
                            }
                        }
                    }
                    let key = station.core.rail_key(level);
                    let core = &station.core;
                    station
                        .rail
                        .set_region(key, || core.rail_series(level).collect::<Vec<_>>());
                    station.rail.paint(
                        ui.painter(),
                        RAIL,
                        RailPalette::GRAPHITE,
                        RailMarkers {
                            hover: station.lens.hovered(),
                            head: station.lens.held().or(station.sample.peak),
                        },
                    );
                    station.film.paint(
                        ui.painter(),
                        FILM,
                        FilmPalette::GRAPHITE,
                        FilmMarks {
                            pointer: station.lens.hovered(),
                            held: station.lens.held(),
                        },
                    );
                });
        },
    )
}

fn texts(output: &egui::FullOutput) -> Vec<String> {
    output
        .shapes
        .iter()
        .filter_map(|clipped| match &clipped.shape {
            Shape::Text(text) => Some(text.galley.text().to_owned()),
            _ => None,
        })
        .collect()
}

fn click(at: Pos2) -> [Vec<egui::Event>; 3] {
    let button = |pressed| egui::Event::PointerButton {
        pos: at,
        button: egui::PointerButton::Primary,
        pressed,
        modifiers: Default::default(),
    };
    [
        vec![egui::Event::PointerMoved(at)],
        vec![button(true)],
        vec![button(false)],
    ]
}

fn key(key: egui::Key, shift: bool) -> egui::Event {
    egui::Event::Key {
        key,
        physical_key: None,
        pressed: true,
        repeat: false,
        modifiers: egui::Modifiers {
            shift,
            ..Default::default()
        },
    }
}

fn setup() -> (
    egui::Context,
    Station,
    PipelineProgress,
    egui::TextureHandle,
) {
    let ctx = egui::Context::default();
    crate::theme::install(&ctx);
    let texture = ctx.load_texture(
        "final",
        egui::ColorImage::filled([30, 20], Color32::GRAY),
        egui::TextureOptions::LINEAR,
    );
    (ctx, Station::default(), progress(), texture)
}

#[test]
fn check_1_hovering_the_photograph_goes_live_names_three_planes_and_draws_the_region_line() {
    let (ctx, mut station, progress, texture) = setup();
    let at = PHOTO.min + PHOTO.size() * egui::vec2(0.6, 0.5);
    for _ in 0..2 {
        frame(
            &ctx,
            &mut station,
            &progress,
            texture.id(),
            vec![egui::Event::PointerMoved(at)],
        );
    }
    let output = frame(
        &ctx,
        &mut station,
        &progress,
        texture.id(),
        vec![egui::Event::PointerMoved(at)],
    );
    assert!(station.sample.live);
    assert_eq!(station.sample.leading.len(), 3);
    assert!(texts(&output).iter().any(|text| text == "LIVE"));
    assert!(
        station.rail.has_region(),
        "the rail's dashed region line appears"
    );
    // A click pins the sample where clicked.
    station.core.pin(
        at,
        PHOTO,
        Rect::from_min_max(Pos2::ZERO, egui::pos2(1.0, 1.0)),
    );
    let away = egui::pos2(5.0, 40.0);
    frame(
        &ctx,
        &mut station,
        &progress,
        texture.id(),
        vec![egui::Event::PointerMoved(away)],
    );
    let pinned = frame(
        &ctx,
        &mut station,
        &progress,
        texture.id(),
        vec![egui::Event::PointerMoved(away)],
    );
    assert!(!station.sample.live);
    assert!(texts(&pinned).iter().any(|text| text == "PINNED"));
}

#[test]
fn check_2_and_3_rail_hover_peeks_click_holds_keys_step_and_escape_releases() {
    let (ctx, mut station, progress, texture) = setup();
    let geometry = RailGeometry::new(RAIL, PLANES).unwrap();
    let at = egui::pos2(geometry.x(99), RAIL.center().y);
    frame(
        &ctx,
        &mut station,
        &progress,
        texture.id(),
        vec![egui::Event::PointerMoved(at)],
    );
    let peek = frame(
        &ctx,
        &mut station,
        &progress,
        texture.id(),
        vec![egui::Event::PointerMoved(at)],
    );
    assert!(station.lens.peeking());
    assert_eq!(station.lens.shown(), Some(99));
    let shown = texts(&peek);
    assert!(
        shown.iter().any(|text| text == "Plane 100"),
        "the peek names the plane"
    );
    assert!(
        shown
            .iter()
            .any(|text| text.ends_with("of the frame kept from here"))
    );
    assert!(shown.iter().any(|text| text == "click to hold"));
    assert_eq!(
        shown.iter().filter(|text| *text == "100").count(),
        1,
        "the numeral under the marker hides; only the marker's label remains"
    );
    // Click holds: the canvas becomes the two-up with eight size maps.
    for events in click(at) {
        frame(&ctx, &mut station, &progress, texture.id(), events);
    }
    assert_eq!(station.lens.held(), Some(99));
    let held = frame(&ctx, &mut station, &progress, texture.id(), vec![]);
    let shown = texts(&held);
    assert_eq!(
        shown.iter().filter(|text| text.ends_with(" kept")).count(),
        8
    );
    assert!(shown.iter().any(|text| text == "PLANE 100"));
    let accent_frames = held
        .shapes
        .iter()
        .filter(|clipped| {
            matches!(&clipped.shape, Shape::Rect(rect)
            if rect.stroke.color == FilmPalette::GRAPHITE.accent && rect.stroke.width == 1.5)
        })
        .count();
    assert_eq!(
        accent_frames, 1,
        "exactly one filmstrip frame is marked held"
    );
    // Hover shows another plane; leaving returns to the held one.
    let other = egui::pos2(geometry.x(40), RAIL.center().y);
    frame(
        &ctx,
        &mut station,
        &progress,
        texture.id(),
        vec![egui::Event::PointerMoved(other)],
    );
    assert_eq!(station.lens.shown(), Some(40));
    frame(
        &ctx,
        &mut station,
        &progress,
        texture.id(),
        vec![egui::Event::PointerMoved(egui::pos2(600.0, 40.0))],
    );
    assert_eq!(station.lens.shown(), Some(99));
    // Right steps by 1; Shift+Left by 10.
    frame(
        &ctx,
        &mut station,
        &progress,
        texture.id(),
        vec![key(egui::Key::ArrowRight, false)],
    );
    assert_eq!(station.lens.held(), Some(100));
    frame(
        &ctx,
        &mut station,
        &progress,
        texture.id(),
        vec![key(egui::Key::ArrowLeft, true)],
    );
    assert_eq!(station.lens.held(), Some(90));
    frame(
        &ctx,
        &mut station,
        &progress,
        texture.id(),
        vec![key(egui::Key::Escape, false)],
    );
    assert!(!station.lens.holding());
}

#[test]
fn check_4_detail_size_changes_caption_share_and_mark() {
    let (ctx, mut station, progress, texture) = setup();
    station.lens.set_planes(PLANES);
    station.lens.hold(64);
    let layout = two_up_layout(CANVAS, 1.5);
    frame(&ctx, &mut station, &progress, texture.id(), vec![]);
    let before = texts(&frame(&ctx, &mut station, &progress, texture.id(), vec![]));
    let caption = |texts: &[String]| {
        texts
            .iter()
            .find(|text| text.starts_with("where plane"))
            .cloned()
            .unwrap()
    };
    assert!(caption(&before).contains("at 1 px"));
    for events in click(layout.sizes[5].center()) {
        frame(&ctx, &mut station, &progress, texture.id(), events);
    }
    assert_eq!(
        station.lens.level(),
        5,
        "clicking a size map moves the switch"
    );
    let after = frame(&ctx, &mut station, &progress, texture.id(), vec![]);
    let shown = texts(&after);
    assert!(caption(&shown).contains("at 32 px"));
    assert_ne!(
        caption(&before),
        caption(&shown),
        "the share changes with the size"
    );
    let marked: Vec<Rect> = after
        .shapes
        .iter()
        .filter_map(|clipped| match &clipped.shape {
            Shape::Rect(rect)
                if rect.stroke.color == LensPalette::GRAPHITE.ink && rect.stroke.width == 1.5 =>
            {
                Some(rect.rect)
            }
            _ => None,
        })
        .collect();
    assert_eq!(marked.len(), 1);
    assert!(
        marked[0].center().distance(layout.sizes[5].center()) < 2.0,
        "that map is marked"
    );
}

#[test]
fn check_5_show_the_plane_in_a_pinned_sample_holds_its_leading_plane() {
    let (ctx, mut station, progress, texture) = setup();
    let at = PHOTO.min + PHOTO.size() * egui::vec2(0.3, 0.5);
    station.core.pin(
        at,
        PHOTO,
        Rect::from_min_max(Pos2::ZERO, egui::pos2(1.0, 1.0)),
    );
    let away = egui::pos2(5.0, 40.0);
    frame(
        &ctx,
        &mut station,
        &progress,
        texture.id(),
        vec![egui::Event::PointerMoved(away)],
    );
    let pinned = frame(
        &ctx,
        &mut station,
        &progress,
        texture.id(),
        vec![egui::Event::PointerMoved(away)],
    );
    let leader = station.sample.leading[0];
    let button = pinned
        .shapes
        .iter()
        .find_map(|clipped| match &clipped.shape {
            Shape::Text(text) if text.galley.text() == "Show the plane" => {
                Some(text.galley.rect.translate(text.pos.to_vec2()).center())
            }
            _ => None,
        })
        .unwrap();
    for events in click(button) {
        frame(&ctx, &mut station, &progress, texture.id(), events);
    }
    assert_eq!(station.lens.held(), Some(leader));
}
