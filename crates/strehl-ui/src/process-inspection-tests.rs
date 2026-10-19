//! Independent v15 witnesses: real painted coordinates and pointer events,
//! plus a parser burst that defeats a recent-packet-only history consumer.
use super::*;
use crate::{
    pipeline::{DiagnosticScope, DiagnosticSurface, PipelineProgress},
    process_space::Surface,
    workbench::SourcePhoto,
};

const SIZE: [f32; 2] = [1410.0, 850.0];

fn texture(ctx: &egui::Context, name: &str) -> TextureHandle {
    ctx.load_texture(
        name,
        egui::ColorImage::filled([13, 9], Color32::GRAY),
        egui::TextureOptions::NEAREST,
    )
}

fn input(progress: &PipelineProgress) -> Input<'_> {
    Input {
        epoch: 1,
        progress,
        frame_count: 67,
        selected: 2,
        inspected_pair: None,
        photos: &[],
        inspection_photos: &[],
        surfaces: &[],
        output: None,
        output_size: None,
    }
}

fn draw(
    field: &mut ProcessTheater,
    ctx: &egui::Context,
    input: Input<'_>,
    time: f64,
    events: Vec<egui::Event>,
) -> egui::FullOutput {
    ctx.run(
        egui::RawInput {
            screen_rect: Some(Rect::from_min_size(Pos2::ZERO, SIZE.into())),
            time: Some(time),
            events,
            ..Default::default()
        },
        |ctx| {
            egui::CentralPanel::default()
                .frame(egui::Frame::NONE)
                .show(ctx, |ui| {
                    field.show(ui, ui.max_rect(), &input, &mut Response::default());
                });
        },
    )
}

fn button(at: Pos2, pressed: bool) -> egui::Event {
    egui::Event::PointerButton {
        pos: at,
        button: egui::PointerButton::Primary,
        pressed,
        modifiers: egui::Modifiers::NONE,
    }
}

fn click(field: &mut ProcessTheater, ctx: &egui::Context, input: Input<'_>, at: Pos2, time: f64) {
    let _ = draw(
        field,
        ctx,
        input,
        time,
        vec![egui::Event::PointerMoved(at), button(at, true)],
    );
    let _ = draw(field, ctx, input, time + 0.02, vec![button(at, false)]);
}

#[derive(Debug)]
struct Image {
    id: egui::TextureId,
    rect: Rect,
    uv: Rect,
    alpha: u8,
}

fn images(output: &egui::FullOutput) -> Vec<Image> {
    output
        .shapes
        .iter()
        .filter_map(|shape| match &shape.shape {
            egui::Shape::Mesh(mesh) if !mesh.vertices.is_empty() => Some(Image {
                id: mesh.texture_id,
                rect: Rect::from_points(&mesh.vertices.iter().map(|v| v.pos).collect::<Vec<_>>()),
                uv: Rect::from_points(&mesh.vertices.iter().map(|v| v.uv).collect::<Vec<_>>()),
                alpha: mesh.vertices[0].color.a(),
            }),
            _ => None,
        })
        .collect()
}

fn same_rect(actual: Rect, expected: Rect) {
    assert!(
        actual.min.distance(expected.min) < 0.002 && actual.max.distance(expected.max) < 0.002,
        "painted {actual:?}, expected {expected:?}"
    );
}

#[allow(clippy::field_reassign_with_default)]
fn fixture(ctx: &egui::Context) -> (PipelineProgress, Vec<DiagnosticSurface>, Vec<TextureHandle>) {
    let mut progress = PipelineProgress::default();
    progress.stage = Stage::Merge;
    progress.analysis_size = Some([131, 99]);
    progress.bands = Some(7);
    let mut packets = Vec::new();
    for level in 0..8 {
        let [width, height] = [
            131usize.div_ceil(1 << level).min(13),
            99usize.div_ceil(1 << level).min(9),
        ];
        for kind in SIGNALS {
            // The broad tone has actual support/fallback/coefficient packets,
            // but no focus-energy election. Do not invent the missing maps.
            if level == 7
                && matches!(
                    kind,
                    DiagnosticKind::FocusEnergy | DiagnosticKind::GateFloor
                )
            {
                continue;
            }
            let frame = matches!(
                kind,
                DiagnosticKind::FocusEnergy
                    | DiagnosticKind::GateFloor
                    | DiagnosticKind::GateSupport
            );
            packets.push(DiagnosticSurface {
                sequence: packets.len() as u64 + 1,
                frame: 4,
                level,
                kind,
                scope: if frame {
                    DiagnosticScope::Frame
                } else {
                    DiagnosticScope::Stack
                },
                scale: match kind {
                    DiagnosticKind::FocusEnergy | DiagnosticKind::GateFloor => DiagnosticScale::Log,
                    DiagnosticKind::Coefficient => DiagnosticScale::Symmetric,
                    _ => DiagnosticScale::Linear,
                },
                width,
                height,
                min: 0.0,
                max: 1.0,
                pixels: (0..width * height)
                    .map(|i| if i % 3 == 0 { 255 } else { 0 })
                    .collect::<Vec<_>>()
                    .into(),
                folded: if frame { 1 } else { 3 },
            });
        }
    }
    packets.push(DiagnosticSurface {
        sequence: 100,
        frame: 4,
        level: 3,
        kind: DiagnosticKind::Preview,
        scope: DiagnosticScope::Stack,
        scale: DiagnosticScale::Linear,
        width: 13,
        height: 9,
        min: 10.0,
        max: 300.0,
        pixels: (0..117).map(|i| (i * 2) as u8).collect::<Vec<_>>().into(),
        folded: 3,
    });
    let textures = packets
        .iter()
        .map(|packet| texture(ctx, &format!("v15-independent-{}", packet.sequence)))
        .collect();
    (progress, packets, textures)
}

fn surfaces<'a>(
    packets: &'a [DiagnosticSurface],
    textures: &'a [TextureHandle],
) -> Vec<Surface<'a>> {
    packets
        .iter()
        .zip(textures)
        .map(|(packet, texture)| Surface {
            epoch: 1,
            stage: Stage::Merge,
            level: packet.level,
            texture,
            frame: (packet.scope == DiagnosticScope::Frame).then_some(packet.frame),
            meta: Some(SurfaceMeta {
                sequence: packet.sequence,
                kind: packet.kind,
                scale: packet.scale,
                min: packet.min,
                max: packet.max,
                samples: [packet.width, packet.height],
                folded: packet.folded,
            }),
            packet: Some(packet),
        })
        .collect()
}

#[test]
fn single_map_click_focuses_every_available_scale_without_replacing_the_photograph() {
    let ctx = egui::Context::default();
    let (progress, packets, textures) = fixture(&ctx);
    let surfaces = surfaces(&packets, &textures);
    let input = Input {
        surfaces: &surfaces,
        ..input(&progress)
    };
    let mut field = ProcessTheater::default();
    let _ = draw(&mut field, &ctx, input, 0.0, vec![]);
    let before = draw(&mut field, &ctx, input, 0.5, vec![]);
    let layout = Layout::new(Rect::from_min_size(Pos2::ZERO, SIZE.into()));
    let photo_id = field.hero.as_ref().unwrap().plate.texture.id();
    let hero = images(&before)
        .into_iter()
        .find(|image| image.id == photo_id && layout.hero.contains_rect(image.rect))
        .unwrap()
        .rect;
    let map_index = packets
        .iter()
        .position(|p| p.level == 3 && p.kind == DiagnosticKind::FocusEnergy)
        .unwrap();
    let map = images(&before)
        .into_iter()
        .find(|image| image.id == textures[map_index].id())
        .unwrap();
    same_rect(map.uv, Rect::from_min_max(Pos2::ZERO, egui::pos2(1.0, 1.0)));
    let at = map.rect.min + map.rect.size() * egui::vec2(0.98, 0.02);
    click(&mut field, &ctx, input, at, 0.6);
    assert!(field.pin.distance(egui::pos2(0.98, 0.02)) < 0.0001);
    assert_eq!(field.level, 3);
    assert_eq!(
        field.enlarged, None,
        "a single inspection must keep the photograph visible"
    );
    for step in 0..25 {
        let _ = draw(&mut field, &ctx, input, 0.65 + step as f64 * 0.02, vec![]);
    }
    let after = draw(&mut field, &ctx, input, 1.2, vec![]);
    let painted = images(&after);
    let expected = Rect::from_min_max(egui::pos2(0.75, 0.0), egui::pos2(1.0, 0.25));
    let binary = crate::process_sample_glyphs::binary_panes(&after, layout.signals);
    assert_eq!(binary.len(), 16);
    let mut maps = 0;
    for (packet, texture) in packets
        .iter()
        .zip(&textures)
        .filter(|(p, _)| p.kind != DiagnosticKind::Preview)
    {
        if matches!(
            packet.kind,
            DiagnosticKind::GateSupport | DiagnosticKind::Averaging
        ) {
            let pane =
                binary[packet.level * 2 + usize::from(packet.kind == DiagnosticKind::Averaging)];
            crate::process_sample_glyphs::assert_painted_samples(
                &after,
                pane,
                expected,
                packet,
                [131, 99],
            );
            maps += 1;
            continue;
        }
        let image = painted
            .iter()
            .find(|image| image.id == texture.id())
            .unwrap_or_else(|| panic!("missing {:?} at level{}", packet.kind, packet.level));
        same_rect(image.uv, expected);
        maps += 1;
    }
    assert_eq!(
        maps, 38,
        "all actual maps across eight scales must remain painted"
    );
    let final_photo = painted
        .iter()
        .find(|image| image.id == photo_id && layout.hero.contains_rect(image.rect))
        .unwrap();
    assert_eq!(final_photo.alpha, 255);
    same_rect(final_photo.rect, hero);
    same_rect(
        final_photo.uv,
        Rect::from_min_max(Pos2::ZERO, egui::pos2(1.0, 1.0)),
    );
}

#[test]
fn focused_map_drag_uses_relative_motion_and_holding_or_releasing_cannot_recenter() {
    let ctx = egui::Context::default();
    let (progress, packets, textures) = fixture(&ctx);
    let surfaces = surfaces(&packets, &textures);
    let input = Input {
        surfaces: &surfaces,
        ..input(&progress)
    };
    let mut field = ProcessTheater::default();
    let _ = draw(&mut field, &ctx, input, 0.0, vec![]);
    field.pin = egui::pos2(0.97, 0.02);
    field.scales.set_pin(field.pin);
    field.scales.focus_pin();
    for step in 0..25 {
        let _ = draw(&mut field, &ctx, input, 0.1 + step as f64 * 0.02, vec![]);
    }
    let before = draw(&mut field, &ctx, input, 0.65, vec![]);
    let index = packets
        .iter()
        .position(|p| p.level == 2 && p.kind == DiagnosticKind::FocusEnergy)
        .unwrap();
    let map = images(&before)
        .into_iter()
        .find(|image| image.id == textures[index].id())
        .unwrap();
    same_rect(
        map.uv,
        Rect::from_min_max(egui::pos2(0.75, 0.0), egui::pos2(1.0, 0.25)),
    );
    let start = map.rect.center();
    let end = start + egui::vec2(-48.0, 28.0);
    let _ = draw(
        &mut field,
        &ctx,
        input,
        0.7,
        vec![egui::Event::PointerMoved(start), button(start, true)],
    );
    let _ = draw(
        &mut field,
        &ctx,
        input,
        0.75,
        vec![egui::Event::PointerMoved(end)],
    );
    assert_eq!(
        field.pin,
        egui::pos2(0.875, 0.125),
        "fixture must cross both edges and clamp the shared aperture center"
    );
    let _ = draw(&mut field, &ctx, input, 0.8, vec![]);
    assert_eq!(
        field.pin,
        egui::pos2(0.875, 0.125),
        "a held pointer contributes zero delta"
    );
    let _ = draw(&mut field, &ctx, input, 0.85, vec![button(end, false)]);
    assert_eq!(field.pin, egui::pos2(0.875, 0.125));
    assert_eq!(field.enlarged, None);
}

#[test]
fn unregistered_source_and_saved_tiff_clicks_cannot_reinterpret_the_aligned_pin() {
    for saved in [false, true] {
        let ctx = egui::Context::default();
        let progress = PipelineProgress::default();
        let image = texture(
            &ctx,
            if saved {
                "saved-cropped-output"
            } else {
                "unregistered-camera"
            },
        );
        let photos = [SourcePhoto {
            epoch: 1,
            index: 2,
            texture: image.clone(),
            aperture: [907, 613],
        }];
        let input = Input {
            inspection_photos: &photos,
            output: saved.then_some(&image),
            ..input(&progress)
        };
        let mut field = ProcessTheater::default();
        let _ = draw(&mut field, &ctx, input, 0.0, vec![]);
        field.pin = egui::pos2(0.21, 0.79);
        let before = draw(&mut field, &ctx, input, 0.5, vec![]);
        let layout = Layout::new(Rect::from_min_size(Pos2::ZERO, SIZE.into()));
        let photo = images(&before)
            .into_iter()
            .find(|mesh| mesh.id == image.id() && layout.hero.contains_rect(mesh.rect))
            .unwrap();
        let at = photo.rect.min + photo.rect.size() * egui::vec2(0.64, 0.32);
        click(&mut field, &ctx, input, at, 0.6);
        assert_eq!(
            field.pin,
            egui::pos2(0.21, 0.79),
            "source/final coordinates are not aligned telemetry coordinates"
        );
    }
}

#[test]
fn ingest_time_revision_and_admission_history_survive_a_full_burst_before_any_view_is_painted() {
    let mut progress = PipelineProgress::default();
    let mut burst =
        String::from("planes: 131 x 99\nanalysis domain : 131 x 99 at full-plane origin (7, 11)\n");
    let mut sequence = 0;
    let mut folded = 0;
    for frame in 0..67 {
        if [0, 23].contains(&frame) {
            continue;
        }
        folded += 1;
        for level in 0..7 {
            sequence += 1;
            let pixels = if (frame + level) % 2 == 0 {
                "00ff"
            } else {
                "ff00"
            };
            burst.push_str(&format!("STREHL_UI_PROGRESS event=diagnostic seq={sequence} frame={frame} level={level} kind=gate-support scope=frame scale=linear width=2 height=1 min=0 max=1 folded=1 total=67 sampling=nearest data={pixels}\n"));
        }
        sequence += 1;
        let value = 100 + frame;
        burst.push_str(&format!("STREHL_UI_PROGRESS event=diagnostic seq={sequence} frame={frame} level=3 kind=preview scope=stack scale=linear width=2 height=1 min={value} max={value} folded={folded} total=67 sampling=nearest data=0000\n"));
    }
    progress.ingest(&burst);
    assert_eq!(folded, 65);
    assert_eq!(
        progress.diagnostic_surfaces.len(),
        384,
        "the fixture must actually evict packets"
    );
    assert!(progress.diagnostic_surfaces.front().unwrap().sequence > 1);
    let history = progress.revisions.history();
    assert_eq!(history.len(), 64);
    assert_eq!(
        (history.front().unwrap().from, history.front().unwrap().to),
        (1, 2)
    );
    let after_refusal = history.iter().find(|sample| sample.to_frame == 24).unwrap();
    assert_eq!((after_refusal.from_frame, after_refusal.to_frame), (22, 24));
    assert_eq!((after_refusal.from, after_refusal.to), (22, 23));
    assert_eq!(after_refusal.range_dn, [2.0, 2.0]);
    assert!(history.iter().all(|sample| sample.changed_samples == 2));
    assert_eq!(progress.admission_archive.len(), 65 * 7);
    assert_eq!(
        progress.admission_archive.sample(0, 1, [0.0, 0.0]),
        Some(true)
    );
    assert_eq!(
        progress.admission_archive.sample(0, 2, [0.0, 0.0]),
        Some(false)
    );
    for frame in [0, 23] {
        assert_eq!(
            progress.admission_archive.sample(0, frame, [0.0, 0.0]),
            None
        );
    }
    let mut old_ring_only = crate::process_revision::RevisionField::default();
    for packet in &progress.diagnostic_surfaces {
        old_ring_only.observe(packet, [131, 99]);
    }
    assert!(
        old_ring_only.history().len() < history.len(),
        "negative control must expose the retired receive-only path"
    );
    let epoch = progress.diagnostic_epoch;
    progress.ingest("analysis domain : 131 x 99 at full-plane origin (8, 11)\n");
    assert_ne!(progress.diagnostic_epoch, epoch);
    assert!(progress.diagnostic_surfaces.is_empty());
    assert!(progress.revisions.history().is_empty());
    assert_eq!(progress.admission_archive.len(), 0);
}
