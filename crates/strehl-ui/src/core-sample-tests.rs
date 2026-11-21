use super::*;
use crate::pipeline::{DiagnosticKind, DiagnosticScale, DiagnosticScope, DiagnosticSurface};
use std::cell::RefCell;

const ANALYSIS: [usize; 2] = [3516, 2344];
const OUTPUT: [usize; 2] = [7032, 4688];
const IMAGE: Rect = Rect {
    min: Pos2 { x: 128.0, y: 94.0 },
    max: Pos2 {
        x: 1204.0,
        y: 812.0,
    },
};

/// Plane p keeps a vertical band centred at x = p / planes, at every size.
fn archive(planes: usize) -> AdmissionArchive {
    let mut archive = AdmissionArchive::default();
    let mut sequence = 0;
    for level in 0..DETAIL_LEVELS {
        let spacing = 1usize << level;
        let width = ANALYSIS[0].div_ceil(spacing).min(128);
        let height = ANALYSIS[1].div_ceil(spacing).min(96);
        for plane in 0..planes {
            sequence += 1;
            let centre = (plane as f32 + 0.5) / planes as f32;
            let reach = 0.06 + 0.02 * level as f32;
            archive.ingest(
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
                            if (x - centre).abs() < reach * (1.0 - (x - centre).abs() / reach * 0.5)
                            {
                                255
                            } else {
                                0
                            }
                        })
                        .collect::<Vec<_>>()
                        .into(),
                },
                ANALYSIS,
            );
        }
    }
    archive
}

fn input(archive: &AdmissionArchive, planes: usize) -> CoreInput<'_> {
    CoreInput {
        archive,
        level: 0,
        analysis_extent: ANALYSIS,
        extent: OUTPUT,
        planes,
        image: IMAGE,
        aperture: Rect::from_min_max(Pos2::ZERO, egui::pos2(1.0, 1.0)),
        final_texture: None,
        geometry: None,
        viewport: Rect::from_min_size(Pos2::ZERO, egui::vec2(1332.0, 1050.0)),
    }
}

fn frame(
    ctx: &egui::Context,
    sample: &mut CoreSample,
    input: CoreInput<'_>,
    events: Vec<egui::Event>,
    previews: &dyn Fn(usize) -> Option<LensPhoto>,
) -> (CoreResponse, egui::FullOutput) {
    let mut response = CoreResponse::default();
    let output = ctx.run(
        egui::RawInput {
            screen_rect: Some(Rect::from_min_size(Pos2::ZERO, egui::vec2(1332.0, 1050.0))),
            events,
            ..Default::default()
        },
        |ctx| {
            egui::CentralPanel::default()
                .frame(egui::Frame::NONE)
                .show(ctx, |ui| {
                    response = sample.show(ui, input, previews, CorePalette::GRAPHITE);
                });
        },
    );
    (response, output)
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

#[test]
fn spans_and_the_sentence_follow_the_mockup() {
    let values = [0.0, 0.0, 0.1, 0.2, 0.8, 1.0, 0.6, 0.1, 0.0];
    assert_eq!(
        span(&values, 0.5),
        Some(Span {
            peak: 5,
            first: 4,
            last: 6
        })
    );
    assert_eq!(
        span(&values, 0.2),
        Some(Span {
            peak: 5,
            first: 3,
            last: 6
        })
    );
    assert_eq!(span(&[0.0; 4], 0.5), None);
    assert_eq!(
        sentence(&values, true, "2 px", Some(0.0)),
        "Detail at 2 px here comes from planes 5\u{2013}7 (3 planes), with fainter support from planes 4\u{2013}7. Nothing was filled in."
    );
    assert_eq!(
        sentence(&[0.0; 4], true, "2 px", None),
        "No plane passed the noise gate here at 2 px."
    );
    assert_eq!(
        sentence(&[0.0; 4], false, "2 px", None),
        "No plane recorded samples here at 2 px."
    );
    assert!(
        sentence(&values, true, "4 px", Some(0.25))
            .ends_with("The fallback average filled 25 % of the sampled sites.")
    );
}

#[test]
fn hovering_the_photograph_goes_live_and_names_three_leading_planes() {
    let planes = 130;
    let archive = archive(planes);
    let ctx = egui::Context::default();
    let mut sample = CoreSample::default();
    let requested = RefCell::new(Vec::new());
    let previews = |plane: usize| {
        requested.borrow_mut().push(plane);
        None
    };
    let at = IMAGE.min + IMAGE.size() * egui::vec2(0.6, 0.5);
    let _ = frame(
        &ctx,
        &mut sample,
        input(&archive, planes),
        vec![egui::Event::PointerMoved(at)],
        &previews,
    );
    let (response, output) = frame(
        &ctx,
        &mut sample,
        input(&archive, planes),
        vec![egui::Event::PointerMoved(at)],
        &previews,
    );
    assert!(response.live);
    assert_eq!(response.leading.len(), 3);
    // The band of plane p sits at x = p / planes: the leaders are near 60 %.
    for plane in &response.leading {
        assert!((70..=86).contains(plane), "leading plane {plane}");
    }
    let peak = response.peak.unwrap();
    assert!((70..=86).contains(&peak));
    let shown = texts(&output);
    assert!(shown.iter().any(|text| text == "CORE SAMPLE"));
    assert!(shown.iter().any(|text| text == "LIVE"));
    assert!(
        shown
            .iter()
            .any(|text| text.starts_with("Detail at 1 px here comes from planes"))
    );
    assert!(shown.iter().any(|text| text == CAUTION));
    for plane in &response.leading {
        assert!(
            shown
                .iter()
                .any(|text| text.starts_with(&format!("plane {}", plane + 1)))
        );
    }
    assert!(
        !shown.iter().any(|text| text == "Show the plane"),
        "a live sample has no actions"
    );
    // Crops asked only for the three leading planes' resident previews.
    let mut asked = requested.borrow().clone();
    asked.sort_unstable();
    asked.dedup();
    let mut leading = response.leading.clone();
    leading.sort_unstable();
    assert_eq!(asked, leading);
    // The rail's region line comes from the same window.
    let key = sample.rail_key(0).unwrap();
    let series: Vec<_> = sample.rail_series(0).collect();
    assert_eq!(series.len(), planes);
    assert!(series.iter().any(|&(_, admitted, _)| admitted > 0));
    assert_eq!(sample.rail_key(0), Some(key));
}

#[test]
fn pointer_motion_inside_one_sample_cell_rebuilds_no_strip_or_profile() {
    let planes = 299;
    let archive = archive(planes);
    let ctx = egui::Context::default();
    let mut sample = CoreSample::default();
    let none = |_: usize| None;
    let at = IMAGE.min + IMAGE.size() * egui::vec2(0.4, 0.5);
    for step in 0..3 {
        let _ = frame(
            &ctx,
            &mut sample,
            input(&archive, planes),
            vec![egui::Event::PointerMoved(
                at + egui::vec2(0.0, step as f32 * 0.01),
            )],
            &none,
        );
    }
    let (builds, profiles) = (sample.strip_builds, sample.profile_builds);
    assert_eq!(builds, 1);
    let key = sample.rail_key(0);
    // Sub-cell jitter (well under one 8 px sample at level 0).
    for step in 0..20 {
        let jitter = egui::vec2((step % 3) as f32 * 0.4, (step % 2) as f32 * 0.4);
        let _ = frame(
            &ctx,
            &mut sample,
            input(&archive, planes),
            vec![egui::Event::PointerMoved(at + jitter)],
            &none,
        );
    }
    assert_eq!(
        sample.strip_builds, builds,
        "no strip rebuild without a window change"
    );
    assert_eq!(sample.profile_builds, profiles);
    assert_eq!(sample.rail_key(0), key);
    // Crossing many cells rebuilds, once per new window at most.
    for step in 1..=10 {
        let _ = frame(
            &ctx,
            &mut sample,
            input(&archive, planes),
            vec![egui::Event::PointerMoved(
                at + egui::vec2(step as f32 * 30.0, 0.0),
            )],
            &none,
        );
    }
    assert!(sample.strip_builds > builds && sample.strip_builds <= builds + 10);
}

#[test]
fn a_click_pins_where_clicked_and_show_the_plane_holds_the_leader() {
    let planes = 130;
    let archive = archive(planes);
    let ctx = egui::Context::default();
    let mut sample = CoreSample::default();
    let none = |_: usize| None;
    let at = IMAGE.min + IMAGE.size() * egui::vec2(0.3, 0.5);
    sample.pin(at, IMAGE, input(&archive, planes).aperture);
    assert!(sample.pinned());
    // With the pointer away from the photograph, the pinned sample shows.
    let away = egui::pos2(5.0, 1040.0);
    let _ = frame(
        &ctx,
        &mut sample,
        input(&archive, planes),
        vec![egui::Event::PointerMoved(away)],
        &none,
    );
    let (pinned, output) = frame(
        &ctx,
        &mut sample,
        input(&archive, planes),
        vec![egui::Event::PointerMoved(away)],
        &none,
    );
    assert!(!pinned.live);
    let region = pinned.region.unwrap();
    assert!((region.center().x - 0.3).abs() < 0.01 && (region.center().y - 0.5).abs() < 0.01);
    let shown = texts(&output);
    assert!(shown.iter().any(|text| text == "PINNED"));
    assert!(shown.iter().any(|text| text == "Show the plane"));
    assert!(shown.iter().any(|text| text == "Repair here\u{2026}"));
    // Click Show the plane: find its rect from the layout.
    let popover = pinned.popover.unwrap();
    // Output shapes are already moved by the popover layer's transform.
    let button = output
        .shapes
        .iter()
        .find_map(|clipped| match &clipped.shape {
            Shape::Text(text) if text.galley.text() == "Show the plane" => {
                Some(text.galley.rect.translate(text.pos.to_vec2()).center())
            }
            _ => None,
        })
        .unwrap();
    assert!(popover.contains(button));
    let press = |pressed| egui::Event::PointerButton {
        pos: button,
        button: egui::PointerButton::Primary,
        pressed,
        modifiers: Default::default(),
    };
    let _ = frame(
        &ctx,
        &mut sample,
        input(&archive, planes),
        vec![egui::Event::PointerMoved(button)],
        &none,
    );
    let _ = frame(
        &ctx,
        &mut sample,
        input(&archive, planes),
        vec![press(true)],
        &none,
    );
    let (clicked, _) = frame(
        &ctx,
        &mut sample,
        input(&archive, planes),
        vec![press(false)],
        &none,
    );
    assert_eq!(
        clicked.action,
        Some(CoreAction::ShowPlane(pinned.leading[0]))
    );
    assert!(sample.unpin());
    assert!(!sample.unpin());
}

#[test]
fn six_thousand_planes_pool_each_strip_to_its_pixel_width() {
    let planes = 1_000;
    let archive = archive(planes);
    let ctx = egui::Context::default();
    let mut sample = CoreSample::default();
    let none = |_: usize| None;
    let at = IMAGE.min + IMAGE.size() * egui::vec2(0.5, 0.5);
    let _ = frame(
        &ctx,
        &mut sample,
        input(&archive, 6_000),
        vec![egui::Event::PointerMoved(at)],
        &none,
    );
    let _ = frame(
        &ctx,
        &mut sample,
        input(&archive, 6_000),
        vec![egui::Event::PointerMoved(at)],
        &none,
    );
    let (_, mesh) = sample.strips.as_ref().expect("strips were built");
    let width = WIDTH - 2.0 * PAD - LABEL_COLUMN;
    // One background row, at most one rect per pixel column, three marks.
    let rects = mesh.vertices.len() / 4;
    assert!(
        rects <= DETAIL_LEVELS * (1 + width as usize) + 3,
        "{rects} rects"
    );
}
