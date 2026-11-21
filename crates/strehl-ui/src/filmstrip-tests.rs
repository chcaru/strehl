use super::*;
use crate::pipeline::{DiagnosticKind, DiagnosticScale, DiagnosticScope, DiagnosticSurface};
use eframe::egui::Pos2;

const STRIP: Rect = Rect {
    min: Pos2 { x: 0.0, y: 951.0 },
    max: Pos2 {
        x: 1332.0,
        y: 1026.0,
    },
};

fn photo(ctx: &egui::Context, index: usize, side: usize, name: &str) -> SourcePhoto {
    SourcePhoto {
        epoch: 1,
        index,
        aperture: [7008, 4672],
        texture: ctx.load_texture(
            format!("{name}-{index}"),
            egui::ColorImage::filled([side, side * 2 / 3], Color32::from_gray(90)),
            egui::TextureOptions::LINEAR,
        ),
    }
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

#[test]
fn seventeen_frames_fit_1332_px_evenly_through_the_stack() {
    assert_eq!(frame_count(1332.0, 299), 17);
    assert_eq!(frame_count(1332.0, 5), 5);
    assert_eq!(frame_count(8000.0, 6000), MAX_FRAMES);
    assert_eq!(frame_count(1332.0, 0), 0);
    let planes = chosen_planes(299, 17);
    assert_eq!(planes.first(), Some(&0));
    assert_eq!(planes.last(), Some(&298));
    assert_eq!(&planes[..4], &[0, 19, 37, 56]);
    assert!(planes.windows(2).all(|pair| pair[1] > pair[0]));
    let mut strip = Filmstrip::default();
    strip.layout(1332.0, 299);
    let first = strip.frame_rect(STRIP, 0);
    assert_eq!(
        [first.left(), first.top(), first.width(), first.height()],
        [20.0, 955.0, 74.0, 63.0]
    );
    let last = strip.frame_rect(STRIP, 16);
    assert!((last.right() - 1312.0).abs() < 0.01);
    assert_eq!(chosen_planes(1, 1), vec![0]);
}

#[test]
fn slots_adopt_published_textures_and_never_downgrade_a_bridge() {
    let ctx = egui::Context::default();
    let mut strip = Filmstrip::default();
    strip.layout(1332.0, 299);
    let shown = strip.planes();
    // Plane 19 only has a canonical tier; plane 37 has its contact.
    let canonical = vec![photo(&ctx, shown[1], 640, "scrub")];
    let contacts = vec![photo(&ctx, shown[2], 240, "contact")];
    strip.sync(1, &contacts, &canonical);
    assert_eq!(
        strip.slots[1]
            .bridge
            .as_ref()
            .map(|(texture, _)| texture.id()),
        Some(canonical[0].texture.id())
    );
    assert_eq!(
        strip.slots[2].native.as_ref().map(TextureHandle::id),
        Some(contacts[0].texture.id())
    );
    // The contact arriving later does not replace the larger bridge.
    let late = vec![photo(&ctx, shown[1], 240, "late-contact")];
    strip.sync(1, &late, &[]);
    assert!(
        strip.slots[1].bridge.is_some(),
        "a slot never drops to a lower tier"
    );
    // Another epoch's textures are never adopted.
    let foreign = SourcePhoto {
        epoch: 2,
        ..photo(&ctx, shown[3], 240, "foreign")
    };
    strip.sync(1, &[foreign], &[]);
    assert!(strip.slots[3].native.is_none());
    // A different width keeps the textures of planes that remain.
    strip.layout(1332.0, 299);
    assert!(strip.slots[2].native.is_some());
}

fn archive(planes: usize) -> AdmissionArchive {
    let mut archive = AdmissionArchive::default();
    let mut sequence = 0;
    for level in 0..LEVELS {
        for plane in 0..planes {
            // Plane 0 has no maps at all; plane 19 is observed at zero.
            if plane == 0 {
                continue;
            }
            sequence += 1;
            let admitted = if plane == 19 {
                0
            } else {
                (plane * 7 + level * 11) % 160 + 8
            };
            archive.ingest(
                &DiagnosticSurface {
                    sequence,
                    frame: plane,
                    level,
                    kind: DiagnosticKind::GateSupport,
                    scope: DiagnosticScope::Frame,
                    scale: DiagnosticScale::Linear,
                    width: 16,
                    height: 12,
                    min: 0.0,
                    max: 1.0,
                    folded: 1,
                    pixels: (0..192)
                        .map(|index| if index < admitted { 255 } else { 0 })
                        .collect::<Vec<_>>()
                        .into(),
                },
                [3516, 2344],
            );
        }
    }
    archive
}

#[test]
fn marks_read_once_per_revision_and_distinguish_zero_from_missing() {
    let archive = archive(299);
    let ctx = egui::Context::default();
    let mut strip = Filmstrip::default();
    strip.layout(1332.0, 299);
    for step in 0..30 {
        strip.update(&archive);
        let pointer = Some(step * 9);
        let _ = run(&ctx, vec![], |ui| {
            strip.paint(
                ui.painter(),
                STRIP,
                FilmPalette::GRAPHITE,
                FilmMarks {
                    pointer,
                    held: Some(127),
                },
            );
        });
    }
    assert_eq!(strip.share_reads, 1);
    assert_eq!(strip.mark_builds, 1, "pointer motion rebuilds no marks");
    assert_eq!(strip.shares[0], [None; LEVELS], "plane 1 has no maps");
    assert_eq!(
        strip.shares[1],
        [Some(0.0); LEVELS],
        "plane 20 observed at zero"
    );
    assert!(
        strip.shares[2]
            .iter()
            .all(|share| share.is_some_and(|value| value > 0.0))
    );
    let output = run(&ctx, vec![], |ui| {
        strip.paint(
            ui.painter(),
            STRIP,
            FilmPalette::GRAPHITE,
            FilmMarks::default(),
        );
    });
    let mesh = output
        .shapes
        .iter()
        .find_map(|clipped| match &clipped.shape {
            Shape::Mesh(mesh) if mesh.texture_id == egui::TextureId::default() => {
                Some(mesh.clone())
            }
            _ => None,
        })
        .unwrap();
    let in_frame = |slot: usize| {
        let frame = strip.frame_rect(STRIP, slot);
        mesh.vertices
            .iter()
            .filter(move |v| frame.expand(0.1).contains(v.pos))
            .collect::<Vec<_>>()
    };
    let missing = in_frame(0);
    let zero = in_frame(1);
    assert_eq!(missing.len(), LEVELS * 4);
    assert_eq!(zero.len(), LEVELS * 4);
    let width = |vertices: &[&egui::epaint::Vertex]| {
        let xs: Vec<f32> = vertices.iter().map(|v| v.pos.x).collect();
        xs.chunks(4)
            .map(|quad| {
                quad.iter().copied().fold(f32::MIN, f32::max)
                    - quad.iter().copied().fold(f32::MAX, f32::min)
            })
            .collect::<Vec<_>>()
    };
    assert!(
        width(&missing).iter().all(|w| (*w - 1.0).abs() < 0.01),
        "missing is dotted"
    );
    assert!(
        width(&zero).iter().all(|w| (*w - 3.0).abs() < 0.01),
        "zero is a flat rule"
    );
    assert!(
        in_frame(2)
            .iter()
            .any(|v| v.color.a() > 0 && v.color != FilmPalette::GRAPHITE.line2),
        "kept detail draws spectrum bars"
    );
}

#[test]
fn hover_and_click_name_the_frame_plane_and_one_frame_is_marked_held() {
    let ctx = egui::Context::default();
    let mut strip = Filmstrip::default();
    strip.layout(1332.0, 299);
    let target = strip.frame_rect(STRIP, 7).center();
    let mut responses = Vec::new();
    let events = [
        vec![egui::Event::PointerMoved(target)],
        vec![egui::Event::PointerMoved(target)],
        vec![egui::Event::PointerButton {
            pos: target,
            button: egui::PointerButton::Primary,
            pressed: true,
            modifiers: Default::default(),
        }],
        vec![egui::Event::PointerButton {
            pos: target,
            button: egui::PointerButton::Primary,
            pressed: false,
            modifiers: Default::default(),
        }],
    ];
    for events in events {
        let _ = run(&ctx, events, |ui| {
            responses.push(strip.interact(ui, STRIP, egui::Id::new("film")));
        });
    }
    let plane = strip.planes()[7];
    assert_eq!(responses[1].hovered, Some(plane));
    assert_eq!(responses[3].clicked, Some(plane));
    assert_eq!(strip.nearest(plane + 3), Some(7));
    let output = run(&ctx, vec![], |ui| {
        strip.paint(
            ui.painter(),
            STRIP,
            FilmPalette::GRAPHITE,
            FilmMarks {
                pointer: Some(200),
                held: Some(130),
            },
        );
    });
    let outlines = |color: Color32| {
        output
            .shapes
            .iter()
            .filter(|clipped| matches!(&clipped.shape, Shape::Rect(rect) if rect.stroke.color == color && rect.stroke.width == 1.5))
            .count()
    };
    assert_eq!(
        outlines(FilmPalette::GRAPHITE.accent),
        1,
        "exactly one frame is held"
    );
    assert_eq!(
        outlines(FilmPalette::GRAPHITE.plane),
        1,
        "one nearest frame"
    );
}
