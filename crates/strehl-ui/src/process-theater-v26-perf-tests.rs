//! Full finished-workspace CPU witness. Real pointer moves traverse the photo,
//! source companion, timeline, region observer, and egui tessellation together.
//! This excludes decoding, GPU upload/presentation, and operating-system input.
use super::*;
use crate::{
    pipeline::{DiagnosticScope, DiagnosticSurface, PipelineProgress},
    process_space::Surface,
    workbench::SourcePhoto,
};
use std::time::Instant;

const FRAMES: usize = 130;
const ANALYSIS: [usize; 2] = [3516, 2344];
const OUTPUT: [u32; 2] = [7032, 4688];

struct Fixture {
    ctx: egui::Context,
    progress: PipelineProgress,
    photos: Vec<SourcePhoto>,
    final_image: TextureHandle,
    maps: Vec<(DiagnosticSurface, TextureHandle)>,
}

impl Fixture {
    fn new() -> Self {
        let ctx = egui::Context::default();
        crate::theme::install(&ctx);
        let mut progress = PipelineProgress::default();
        progress.ingest("planes : 3516 x 2344 per CFA plane\ncoverage : field of view scaled to 0.9500 so that EVERY frame covers every pixel\nbands : 7 Laplacian levels + 1 base, coarsest 28 x 19\nwrote : result.tiff (7032 x 4688, 16-bit RGB, sRGB (BT.709 primaries, D65, sRGB transfer) -- for looking at, Malvar-He-Cutler demosaic)\n");
        progress.frames_total = Some(FRAMES);
        progress.frames_accepted = Some(FRAMES);
        let mut maps = Vec::new();
        for level in 0..8 {
            let spacing = 1usize << level;
            let width = ANALYSIS[0].div_ceil(spacing).min(128);
            let height = ANALYSIS[1].div_ceil(spacing).min(96);
            for frame in 0..FRAMES {
                // Broad overlapping capture support plus a changed fine pattern;
                // neither all-positive nor all-negative masks can pass for this.
                let pixels = (0..height)
                    .flat_map(|y| {
                        (0..width).map(move |x| {
                            if ((x * 13 / width + y * 7 / height + level) % 13).abs_diff(frame % 13)
                                <= 3
                                && (x + 3 * y + frame + level) % 9 != 0
                            {
                                255
                            } else {
                                0
                            }
                        })
                    })
                    .collect::<Vec<_>>();
                let packet = DiagnosticSurface {
                    sequence: (level * FRAMES + frame + 1) as u64,
                    frame,
                    level,
                    kind: DiagnosticKind::GateSupport,
                    scope: DiagnosticScope::Frame,
                    scale: DiagnosticScale::Linear,
                    width,
                    height,
                    min: 0.0,
                    max: 1.0,
                    folded: 1,
                    pixels: pixels.into(),
                };
                progress.admission_archive.ingest(&packet, ANALYSIS);
                if frame == 65 {
                    let texture = ctx.load_texture(
                        format!("perf-admission-{level}"),
                        egui::ColorImage::filled([width, height], Color32::GRAY),
                        egui::TextureOptions::NEAREST,
                    );
                    maps.push((packet, texture));
                }
            }
            for (kind, scope, max) in [
                (DiagnosticKind::FocusEnergy, DiagnosticScope::Frame, 255.0),
                (DiagnosticKind::GateFloor, DiagnosticScope::Frame, 255.0),
                (DiagnosticKind::Coefficient, DiagnosticScope::Stack, 255.0),
                (DiagnosticKind::Averaging, DiagnosticScope::Stack, 1.0),
            ] {
                let packet = DiagnosticSurface {
                    sequence: 2000 + maps.len() as u64,
                    frame: 65,
                    level,
                    kind,
                    scope,
                    scale: DiagnosticScale::Linear,
                    width,
                    height,
                    min: 0.0,
                    max,
                    folded: if scope == DiagnosticScope::Frame {
                        1
                    } else {
                        FRAMES
                    },
                    pixels: (0..width * height)
                        .map(|i| {
                            if kind == DiagnosticKind::Averaging {
                                if i % 11 == 0 { 255 } else { 0 }
                            } else {
                                (i % 256) as u8
                            }
                        })
                        .collect::<Vec<_>>()
                        .into(),
                };
                let texture = ctx.load_texture(
                    format!("perf-map-{}", maps.len()),
                    egui::ColorImage::filled([width, height], Color32::GRAY),
                    egui::TextureOptions::NEAREST,
                );
                maps.push((packet, texture));
            }
        }
        progress.mark_complete();
        assert_eq!(progress.admission_archive.len(), FRAMES * 8);
        for level in 0..8 {
            let (meta, _) = progress.admission_archive.cells(level, 65).unwrap();
            assert!(
                crate::process_sample_glyphs::SampleGeometry::new(level, meta).is_some(),
                "coarse telemetry must be geometrically usable, never silently rejected"
            );
            let (yes, total) = progress.admission_archive.counts(level, 65).unwrap();
            assert!(yes > 0 && yes < total);
        }
        let photos = (0..FRAMES)
            .map(|index| SourcePhoto {
                epoch: 1,
                index,
                aperture: OUTPUT,
                texture: ctx.load_texture(
                    format!("perf-camera-{index}"),
                    egui::ColorImage::filled(
                        [96, 64],
                        Color32::from_rgb(50 + (index % 120) as u8, 80, 110),
                    ),
                    egui::TextureOptions::LINEAR,
                ),
            })
            .collect();
        let final_image = ctx.load_texture(
            "perf-owned-result",
            egui::ColorImage::filled([192, 128], Color32::GOLD),
            egui::TextureOptions::LINEAR,
        );
        Self {
            ctx,
            progress,
            photos,
            final_image,
            maps,
        }
    }

    fn surfaces(&self) -> Vec<Surface<'_>> {
        self.maps
            .iter()
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

    fn with_overlapping_ranges() -> Self {
        let mut fixture = Self::new();
        for frame in 0..FRAMES {
            // Neither the last capture in a range nor an unrelated comparison
            // source can supply the whole selected region. The range unions
            // cover x16..78 and x50..112, with a substantial shared interior.
            let support = match frame {
                4..=8 => 16..60,
                9..=12 => 45..78,
                31..=32 => 50..92,
                33..=35 => 75..112,
                _ => 0..0,
            };
            let packet = DiagnosticSurface {
                sequence: 10_000 + frame as u64,
                frame,
                level: 0,
                kind: DiagnosticKind::GateSupport,
                scope: DiagnosticScope::Frame,
                scale: DiagnosticScale::Linear,
                width: 128,
                height: 96,
                min: 0.0,
                max: 1.0,
                folded: 1,
                pixels: (0..96)
                    .flat_map(|y| {
                        let support = support.clone();
                        (0..128).map(move |x| {
                            if support.contains(&x) && (16..80).contains(&y) {
                                255
                            } else {
                                0
                            }
                        })
                    })
                    .collect::<Vec<_>>()
                    .into(),
            };
            fixture.progress.admission_archive.ingest(&packet, ANALYSIS);
        }
        assert_eq!(
            fixture.progress.admission_archive.counts(0, 97).unwrap().0,
            0
        );
        assert_eq!(
            fixture.progress.admission_archive.counts(0, 88).unwrap().0,
            0
        );
        fixture
    }

    fn paint(
        &self,
        field: &mut ProcessTheater,
        surfaces: &[Surface<'_>],
        time: f64,
        at: Pos2,
    ) -> egui::FullOutput {
        self.paint_events(field, surfaces, time, vec![egui::Event::PointerMoved(at)])
    }

    fn paint_events(
        &self,
        field: &mut ProcessTheater,
        surfaces: &[Surface<'_>],
        time: f64,
        events: Vec<egui::Event>,
    ) -> egui::FullOutput {
        self.paint_modified(field, surfaces, time, egui::Modifiers::NONE, events)
    }

    fn paint_modified(
        &self,
        field: &mut ProcessTheater,
        surfaces: &[Surface<'_>],
        time: f64,
        modifiers: egui::Modifiers,
        events: Vec<egui::Event>,
    ) -> egui::FullOutput {
        let input = Input {
            epoch: 1,
            progress: &self.progress,
            frame_count: FRAMES,
            selected: 65,
            inspected_pair: None,
            photos: &self.photos,
            inspection_photos: &self.photos,
            surfaces,
            output: Some(&self.final_image),
            output_size: Some(OUTPUT),
        };
        self.ctx.run(
            egui::RawInput {
                screen_rect: Some(Rect::from_min_size(Pos2::ZERO, egui::vec2(1600.0, 1000.0))),
                time: Some(time),
                modifiers,
                events,
                ..Default::default()
            },
            |ctx| {
                egui::CentralPanel::default()
                    .frame(egui::Frame::NONE)
                    .show(ctx, |ui| {
                        field.navigation_shortcuts(ui, &mut Response::default());
                        field.show_with_ribbon(
                            ui,
                            Rect::from_min_max(egui::pos2(10.0, 10.0), egui::pos2(1590.0, 724.0)),
                            &input,
                            &mut Response::default(),
                            Some(Rect::from_min_max(
                                egui::pos2(10.0, 734.0),
                                egui::pos2(1590.0, 990.0),
                            )),
                        );
                    });
            },
        )
    }
}

fn has(output: &egui::FullOutput, label: &str) -> bool {
    output.shapes.iter().any(|shape| matches!(&shape.shape, egui::Shape::Text(text) if text.galley.text().contains(label)))
}

fn main_image(output: &egui::FullOutput, id: egui::TextureId) -> Option<Rect> {
    output
        .shapes
        .iter()
        .filter_map(|shape| {
            let egui::Shape::Mesh(mesh) = &shape.shape else {
                return None;
            };
            (mesh.texture_id == id && !mesh.vertices.is_empty()).then(|| {
                Rect::from_points(&mesh.vertices.iter().map(|v| v.pos).collect::<Vec<_>>())
            })
        })
        .filter(|rect| rect.bottom() < 734.0)
        .max_by(|a, b| a.area().total_cmp(&b.area()))
}

fn region_fill_meshes(output: &egui::FullOutput, alpha: u8) -> Vec<(Rect, Vec<[Pos2; 3]>)> {
    output
        .shapes
        .iter()
        .filter_map(|shape| {
            let egui::Shape::Mesh(mesh) = &shape.shape else {
                return None;
            };
            // Only indexed fill triangles count. Unreferenced lattice vertices,
            // outlines, and some unrelated green text cannot witness a region.
            let triangles: Vec<_> = mesh
                .indices
                .as_chunks::<3>()
                .0
                .iter()
                .filter_map(|indices| {
                    let vertices = [indices[0], indices[1], indices[2]]
                        .map(|index| mesh.vertices[index as usize]);
                    vertices
                        .iter()
                        .all(|vertex| {
                            vertex.color.a() == alpha && vertex.color.g() > vertex.color.r()
                        })
                        .then(|| vertices.map(|vertex| vertex.pos))
                })
                .collect();
            (!triangles.is_empty()).then_some((shape.clip_rect, triangles))
        })
        .collect()
}

fn assert_region_on_photo(output: &egui::FullOutput, photo: Rect, alpha: u8) {
    let fills = region_fill_meshes(output, alpha);
    assert_eq!(
        fills.len(),
        1,
        "exactly one region projection must use alpha {alpha}"
    );
    let (clip, triangles) = &fills[0];
    assert!(
        clip.min.distance(photo.min) < 0.1 && clip.max.distance(photo.max) < 0.1,
        "the region clip must be its actual photograph, not the neighbouring pane or whole window"
    );
    let mut area = 0.0;
    for &[a, b, c] in triangles {
        assert!(
            [a, b, c]
                .into_iter()
                .all(|point| photo.expand(0.1).contains(point)),
            "at fit, used region vertices must lie on the photo they describe"
        );
        area += ((b.x - a.x) * (c.y - a.y) - (b.y - a.y) * (c.x - a.x)).abs() * 0.5;
    }
    assert!(
        area > photo.area() * 0.02 && area < photo.area() * 0.9,
        "mixed support must shade a substantial proper subset, not a stray triangle or entire photo"
    );
}

fn timeline_point(output: &egui::FullOutput, frame: usize) -> Pos2 {
    let label_y = output
        .shapes
        .iter()
        .find_map(|shape| match &shape.shape {
            egui::Shape::Text(text) if text.galley.text() == "Full image" => {
                Some(text.visual_bounding_rect().center().y)
            }
            _ => None,
        })
        .expect("actual full-image timeline label");
    let axis = output
        .shapes
        .iter()
        .find_map(|shape| match &shape.shape {
            egui::Shape::LineSegment { points, .. }
                if points[0].y == points[1].y
                    && points[1].x - points[0].x > 600.0
                    && (label_y + 1.0..label_y + 25.0).contains(&points[0].y) =>
            {
                Some(*points)
            }
            _ => None,
        })
        .expect("actual painted timeline axis");
    axis[0].lerp(axis[1], frame as f32 / (FRAMES - 1) as f32) - egui::vec2(0.0, 4.0)
}

fn timeline_gesture(
    fixture: &Fixture,
    field: &mut ProcessTheater,
    surfaces: &[Surface<'_>],
    time: &mut f64,
    points: [Pos2; 2],
    modifiers: egui::Modifiers,
) -> egui::FullOutput {
    let button = |pos, pressed| egui::Event::PointerButton {
        pos,
        button: egui::PointerButton::Primary,
        pressed,
        modifiers,
    };
    *time += 0.2;
    fixture.paint_modified(
        field,
        surfaces,
        *time,
        modifiers,
        vec![
            egui::Event::PointerMoved(points[0]),
            button(points[0], true),
        ],
    );
    if points[0] != points[1] {
        *time += 0.2;
        fixture.paint_modified(
            field,
            surfaces,
            *time,
            modifiers,
            vec![egui::Event::PointerMoved(points[1])],
        );
    }
    *time += 0.2;
    fixture.paint_modified(
        field,
        surfaces,
        *time,
        modifiers,
        vec![button(points[1], false)],
    )
}

fn colored_triangles(output: &egui::FullOutput, photo: Rect, color: Color32) -> Vec<[Pos2; 3]> {
    output
        .shapes
        .iter()
        .filter(|shape| {
            shape.clip_rect.min.distance(photo.min) < 0.1
                && shape.clip_rect.max.distance(photo.max) < 0.1
        })
        .flat_map(|shape| {
            let egui::Shape::Mesh(mesh) = &shape.shape else {
                return Vec::new();
            };
            mesh.indices
                .as_chunks::<3>()
                .0
                .iter()
                .filter_map(|indices| {
                    let vertices = [indices[0], indices[1], indices[2]]
                        .map(|index| mesh.vertices[index as usize]);
                    vertices
                        .iter()
                        .all(|vertex| vertex.color == color)
                        .then(|| vertices.map(|vertex| vertex.pos))
                })
                .collect::<Vec<_>>()
        })
        .collect()
}

fn triangle_contains([a, b, c]: [Pos2; 3], point: Pos2) -> bool {
    if ((b.x - a.x) * (c.y - a.y) - (b.y - a.y) * (c.x - a.x)).abs() < 0.001 {
        return false;
    }
    let cross = |from: Pos2, to: Pos2| {
        (to.x - from.x) * (point.y - from.y) - (to.y - from.y) * (point.x - from.x)
    };
    let sides = [cross(a, b), cross(b, c), cross(c, a)];
    sides.iter().all(|side| *side >= -0.001) || sides.iter().all(|side| *side <= 0.001)
}

fn selection_colors(colors: [Color32; 2], approximate: bool) -> [Color32; 5] {
    let alpha = |color: Color32, alpha| {
        Color32::from_rgba_unmultiplied(color.r(), color.g(), color.b(), alpha)
    };
    let mixed = Color32::from_rgb(
        ((colors[0].r() as u16 + colors[1].r() as u16) / 2) as u8,
        ((colors[0].g() as u16 + colors[1].g() as u16) / 2) as u8,
        ((colors[0].b() as u16 + colors[1].b() as u16) / 2) as u8,
    );
    [
        alpha(colors[0], if approximate { 18 } else { 36 }),
        alpha(colors[1], if approximate { 18 } else { 36 }),
        alpha(mixed, if approximate { 23 } else { 46 }),
        alpha(colors[0], if approximate { 55 } else { 100 }),
        alpha(colors[1], if approximate { 55 } else { 100 }),
    ]
}

fn assert_selected_regions(
    output: &egui::FullOutput,
    photo: Rect,
    colors: [Color32; 2],
    approximate: bool,
) {
    let triangles =
        selection_colors(colors, approximate).map(|color| colored_triangles(output, photo, color));
    for (index, uv) in [
        (0, egui::vec2(0.25, 0.5)),
        (1, egui::vec2(0.75, 0.5)),
        (2, egui::vec2(0.5, 0.5)),
    ] {
        let at = photo.min + photo.size() * uv;
        assert!(
            triangles[index]
                .iter()
                .any(|&triangle| triangle_contains(triangle, at)),
            "range {index} must fill its known interior on approximate={approximate}"
        );
        for other in (0..3).filter(|other| *other != index) {
            assert!(
                !triangles[other]
                    .iter()
                    .any(|&triangle| triangle_contains(triangle, at)),
                "independent and shared regions must not overpaint each other's interiors"
            );
        }
    }
    let overlap_bounds = Rect::from_min_max(
        photo.min + photo.size() * egui::vec2(0.37, 0.14),
        photo.min + photo.size() * egui::vec2(0.63, 0.86),
    );
    for stripes in &triangles[3..] {
        assert!(
            stripes.len() > 5,
            "both range colours must occur in real shared-region stripe triangles"
        );
        assert!(
            stripes
                .iter()
                .flatten()
                .all(|point| overlap_bounds.contains(*point)),
            "stripes must remain inside the shared region rather than cross single-range interiors"
        );
    }
    let outside = photo.min + photo.size() * egui::vec2(0.05, 0.05);
    assert!(
        triangles
            .iter()
            .flatten()
            .all(|&triangle| !triangle_contains(triangle, outside)),
        "observed zero-admission corner must stay clear"
    );
}

fn assert_selection_hidden(output: &egui::FullOutput, photos: [Rect; 2], colors: [Color32; 2]) {
    for (index, photo) in photos.into_iter().enumerate() {
        for color in selection_colors(colors, index == 1) {
            assert!(
                colored_triangles(output, photo, color).is_empty(),
                "no selected-range fill or mixed stripe may remain on photo {index}"
            );
        }
    }
}

fn key_event(key: egui::Key, pressed: bool) -> egui::Event {
    egui::Event::Key {
        key,
        physical_key: None,
        pressed,
        repeat: false,
        modifiers: egui::Modifiers::NONE,
    }
}

fn click_photo_overlay(
    fixture: &Fixture,
    field: &mut ProcessTheater,
    surfaces: &[Surface<'_>],
    time: f64,
    photo: Rect,
    label: &str,
) -> egui::FullOutput {
    let button = |pos, button, pressed| egui::Event::PointerButton {
        pos,
        button,
        pressed,
        modifiers: egui::Modifiers::NONE,
    };
    fixture.paint_events(
        field,
        surfaces,
        time,
        vec![
            egui::Event::PointerMoved(photo.center()),
            button(photo.center(), egui::PointerButton::Secondary, true),
        ],
    );
    fixture.paint_events(
        field,
        surfaces,
        time + 0.01,
        vec![button(
            photo.center(),
            egui::PointerButton::Secondary,
            false,
        )],
    );
    let opened = fixture.paint(field, surfaces, time + 0.02, photo.center());
    let at = opened
        .shapes
        .iter()
        .find_map(|shape| match &shape.shape {
            egui::Shape::Text(text) if text.galley.text() == label => {
                Some(shape.shape.visual_bounding_rect().center())
            }
            _ => None,
        })
        .expect("real photo context menu must expose the requested overlay action");
    fixture.paint_events(
        field,
        surfaces,
        time + 0.03,
        vec![
            egui::Event::PointerMoved(at),
            button(at, egui::PointerButton::Primary, true),
        ],
    );
    fixture.paint_events(
        field,
        surfaces,
        time + 0.04,
        vec![button(at, egui::PointerButton::Primary, false)],
    );
    // Close only the popup with an outside click. Escape also returns the
    // theater to the final photograph, which would hide a broken overlay path.
    fixture.paint_events(
        field,
        surfaces,
        time + 0.05,
        vec![
            egui::Event::PointerMoved(Pos2::ZERO),
            button(Pos2::ZERO, egui::PointerButton::Primary, true),
        ],
    );
    fixture.paint_events(
        field,
        surfaces,
        time + 0.06,
        vec![button(Pos2::ZERO, egui::PointerButton::Primary, false)],
    );
    fixture.paint(field, surfaces, time + 0.07, Pos2::ZERO)
}

/// Fail before timing if an empty archive, absent photo, hidden probe, or
/// missing timeline would make the benchmark look artificially quick.
fn settle(
    fixture: &Fixture,
    surfaces: &[Surface<'_>],
    comparison: bool,
) -> (ProcessTheater, Rect, f64) {
    // The context is reused across modes and alternating benchmark sweeps.
    // egui retains pointer history even when the ProcessTheater is new.
    let start = fixture.ctx.input(|input| input.time) + 1.0;
    let mut field = ProcessTheater::default();
    fixture.paint(&mut field, surfaces, start, Pos2::ZERO);
    fixture.paint(&mut field, surfaces, start + 0.5, Pos2::ZERO);
    if comparison {
        field.inspect_frame(65);
    }
    fixture.paint(&mut field, surfaces, start + 1.0, Pos2::ZERO);
    fixture.paint(&mut field, surfaces, start + 1.5, Pos2::ZERO);
    let output = fixture.paint(&mut field, surfaces, start + 2.0, Pos2::ZERO);
    let image =
        main_image(&output, fixture.final_image.id()).expect("owned final photo actually painted");
    assert!(image.width() > 200.0 && image.height() > 100.0);
    assert!(
        has(&output, "Full image"),
        "actual timeline must be present"
    );
    if comparison {
        assert_eq!(field.inspection_frame(), Some(65));
        assert!(
            main_image(&output, fixture.photos[65].texture.id()).is_some(),
            "camera companion must actually be painted"
        );
    }
    let at = image.min + image.size() * egui::vec2(0.43, 0.43);
    let hover = fixture.paint(&mut field, surfaces, start + 2.1, at);
    assert!(
        has(&hover, "REGION /"),
        "pointer must exercise regional observation path"
    );
    assert!(
        has(&hover, "recorded"),
        "region has real evidence rather than a pending placeholder"
    );
    let primitives = fixture.ctx.tessellate(hover.shapes, hover.pixels_per_point);
    assert!(!primitives.is_empty());
    (field, image, start + 2.2)
}

#[test]
fn full_workspace_perf_fixture_reaches_real_final_source_timeline_and_probe_paths() {
    let fixture = Fixture::new();
    let surfaces = fixture.surfaces();
    for comparison in [false, true] {
        settle(&fixture, &surfaces, comparison);
    }
}

#[test]
fn v27_default_detail_and_region_shading_follow_both_photographs_and_clear_together() {
    use crate::process_admission_regions::RegionSettings;
    let fixture = Fixture::new();
    let surfaces = fixture.surfaces();
    let (mut field, _, time) = settle(&fixture, &surfaces, true);
    assert_eq!(
        field.level, 0,
        "demosaiced default must mean two photograph pixels"
    );
    assert_eq!(
        crate::process_sample_glyphs::Density::read(&fixture.ctx),
        crate::process_sample_glyphs::Density::Full
    );
    let output = fixture.paint(&mut field, &surfaces, time + 0.1, Pos2::ZERO);
    let final_rect = main_image(&output, fixture.final_image.id()).unwrap();
    let source_rect = main_image(&output, fixture.photos[65].texture.id()).unwrap();
    assert!(
        !final_rect.intersects(source_rect),
        "the fixture must distinguish both photographic destinations"
    );
    assert_region_on_photo(&output, final_rect, 36);
    assert_region_on_photo(&output, source_rect, 18);
    assert!(has(&output, "LINKED REGION · APPROXIMATE"));
    RegionSettings {
        enabled: false,
        threshold: 60,
    }
    .write(&fixture.ctx);
    let disabled = fixture.paint(&mut field, &surfaces, time + 0.2, Pos2::ZERO);
    assert!(
        region_fill_meshes(&disabled, 36).is_empty()
            && region_fill_meshes(&disabled, 18).is_empty(),
        "one shared overlay control clears both photo projections"
    );
    RegionSettings::default().write(&fixture.ctx);
    let restored = fixture.paint(&mut field, &surfaces, time + 0.3, Pos2::ZERO);
    assert_region_on_photo(&restored, final_rect, 36);
    assert_region_on_photo(&restored, source_rect, 18);
    let peek = fixture.paint_events(
        &mut field,
        &surfaces,
        time + 0.4,
        vec![key_event(egui::Key::Space, true)],
    );
    assert!(
        region_fill_meshes(&peek, 36).is_empty() && region_fill_meshes(&peek, 18).is_empty(),
        "an actual Space press clears both projections"
    );
    assert_eq!(
        main_image(&peek, fixture.final_image.id()),
        Some(final_rect)
    );
    assert_eq!(
        main_image(&peek, fixture.photos[65].texture.id()),
        Some(source_rect)
    );
    let released = fixture.paint_events(
        &mut field,
        &surfaces,
        time + 0.5,
        vec![key_event(egui::Key::Space, false)],
    );
    assert_region_on_photo(&released, final_rect, 36);
    assert_region_on_photo(&released, source_rect, 18);
    let hidden = click_photo_overlay(
        &fixture,
        &mut field,
        &surfaces,
        time + 0.6,
        final_rect,
        "Hide admission marks",
    );
    assert!(
        !crate::process_result::ResultPhoto::admission_visible(&fixture.ctx),
        "the real menu click must change overlay mode"
    );
    assert!(
        region_fill_meshes(&hidden, 36).is_empty() && region_fill_meshes(&hidden, 18).is_empty()
    );
    assert_eq!(
        main_image(&hidden, fixture.final_image.id()),
        Some(final_rect)
    );
    assert_eq!(
        main_image(&hidden, fixture.photos[65].texture.id()),
        Some(source_rect)
    );
    let reshown = click_photo_overlay(
        &fixture,
        &mut field,
        &surfaces,
        time + 0.8,
        final_rect,
        "Selected detail size",
    );
    assert!(crate::process_result::ResultPhoto::admission_visible(
        &fixture.ctx
    ));
    assert_region_on_photo(&reshown, final_rect, 36);
    assert_region_on_photo(&reshown, source_rect, 18);
    field.resume_live();
    field.participation.clear();
    field.participation_frame = None;
    let clean = fixture.paint(&mut field, &surfaces, time + 1.0, Pos2::ZERO);
    assert!(
        region_fill_meshes(&clean, 36).is_empty(),
        "unmodified final photo has no stale source region"
    );
}

#[test]
fn v27_selected_range_colours_and_mixed_stripes_survive_real_source_exploration() {
    let fixture = Fixture::with_overlapping_ranges();
    let surfaces = fixture.surfaces();
    let (mut field, _, mut time) = settle(&fixture, &surfaces, true);
    let initial = fixture.paint(&mut field, &surfaces, time, Pos2::ZERO);
    let at = |frame| timeline_point(&initial, frame);
    timeline_gesture(
        &fixture,
        &mut field,
        &surfaces,
        &mut time,
        [at(4); 2],
        egui::Modifiers::NONE,
    );
    timeline_gesture(
        &fixture,
        &mut field,
        &surfaces,
        &mut time,
        [at(12); 2],
        egui::Modifiers::SHIFT,
    );
    assert_eq!(
        field
            .participation
            .spans()
            .iter()
            .map(|span| (span.start, span.end))
            .collect::<Vec<_>>(),
        [(4, 12)]
    );
    let first_color = field.participation.spans()[0].color();
    timeline_gesture(
        &fixture,
        &mut field,
        &surfaces,
        &mut time,
        [at(31), at(35)],
        egui::Modifiers::CTRL,
    );
    let selected = field.participation.spans().to_vec();
    assert_eq!(
        selected
            .iter()
            .map(|span| (span.start, span.end))
            .collect::<Vec<_>>(),
        [(4, 12), (31, 35)]
    );
    let colors = [selected[0].color(), selected[1].color()];
    assert_eq!(
        colors[0], first_color,
        "adding a range must preserve the first identity's colour"
    );
    assert_ne!(colors[0], colors[1]);

    // Keep this pinned-range regression on an observed-empty current capture.
    // The v29 test below separately requires positive current/pin overlaps.
    timeline_gesture(
        &fixture,
        &mut field,
        &surfaces,
        &mut time,
        [at(88); 2],
        egui::Modifiers::NONE,
    );

    // Frame97 is observed but has no positive samples: replacing the ranges
    // with this hover would remove every coloured region, rather than passing
    // by coincidentally showing similar evidence from another source.
    time += 0.4;
    fixture.paint(&mut field, &surfaces, time, at(97));
    time += 0.5;
    let hovered = fixture.paint(&mut field, &surfaces, time, at(97));
    assert_eq!(field.inspection_frame(), Some(97));
    assert_eq!(field.participation.spans(), selected);
    let final_rect = main_image(&hovered, fixture.final_image.id()).unwrap();
    let hover_rect = main_image(&hovered, fixture.photos[97].texture.id())
        .expect("real outside-range source pixels");
    assert!(!final_rect.intersects(hover_rect));
    assert_selected_regions(&hovered, final_rect, colors, false);
    assert_selected_regions(&hovered, hover_rect, colors, true);

    time += 0.3;
    let left = fixture.paint(&mut field, &surfaces, time, Pos2::ZERO);
    assert_eq!(field.participation.spans(), selected);
    assert_selected_regions(
        &left,
        main_image(&left, fixture.final_image.id()).unwrap(),
        colors,
        false,
    );
    // A deliberate change of displayed source must preserve the same ranges
    // too; the single-selection fallback is tested separately above.
    timeline_gesture(
        &fixture,
        &mut field,
        &surfaces,
        &mut time,
        [at(88); 2],
        egui::Modifiers::NONE,
    );
    time += 0.5;
    let compared = fixture.paint(&mut field, &surfaces, time, Pos2::ZERO);
    assert_eq!(field.inspection_frame(), Some(88));
    assert_eq!(field.participation.spans(), selected);
    let final_rect = main_image(&compared, fixture.final_image.id()).unwrap();
    let source_rect = main_image(&compared, fixture.photos[88].texture.id())
        .expect("real newly held comparison pixels");
    assert_selected_regions(&compared, final_rect, colors, false);
    assert_selected_regions(&compared, source_rect, colors, true);
    assert!(has(&compared, "SELECTED REGIONS · APPROXIMATE"));

    // Opaque radial marks occur at admitted samples shared by both ranges;
    // polygon contours use lower alpha, so these triangles distinguish the
    // actual sample overlay from the coloured region mesh.
    for color in colors {
        assert!(
            colored_triangles(&compared, final_rect, color).is_empty(),
            "range polygons must start unobscured by dense sample marks"
        );
    }
    time += 0.2;
    let samples = click_photo_overlay(
        &fixture,
        &mut field,
        &surfaces,
        time,
        final_rect,
        "Sample marks over range regions",
    );
    for color in colors {
        assert!(
            colored_triangles(&samples, final_rect, color).len() > 100,
            "the real checkbox must restore actual shared-sample geometry in both range colours"
        );
    }
    assert_selected_regions(&samples, final_rect, colors, false);
    assert_selected_regions(&samples, source_rect, colors, true);
    assert_eq!(
        main_image(&samples, fixture.photos[88].texture.id()),
        Some(source_rect)
    );
    assert_eq!(field.participation.spans(), selected);
    time += 0.3;
    let polygons = click_photo_overlay(
        &fixture,
        &mut field,
        &surfaces,
        time,
        final_rect,
        "Sample marks over range regions",
    );
    for color in colors {
        assert!(
            colored_triangles(&polygons, final_rect, color).is_empty(),
            "turning the checkbox off must remove the sample overlay again"
        );
    }
    assert_selected_regions(&polygons, final_rect, colors, false);
    assert_selected_regions(&polygons, source_rect, colors, true);
    assert_eq!(
        main_image(&polygons, fixture.photos[88].texture.id()),
        Some(source_rect)
    );

    time += 0.2;
    let peek = fixture.paint_events(
        &mut field,
        &surfaces,
        time,
        vec![key_event(egui::Key::Space, true)],
    );
    assert_selection_hidden(&peek, [final_rect, source_rect], colors);
    assert_eq!(
        main_image(&peek, fixture.final_image.id()),
        Some(final_rect)
    );
    assert_eq!(
        main_image(&peek, fixture.photos[88].texture.id()),
        Some(source_rect)
    );
    assert_eq!(field.participation.spans(), selected);
    time += 0.2;
    let released = fixture.paint_events(
        &mut field,
        &surfaces,
        time,
        vec![key_event(egui::Key::Space, false)],
    );
    assert_selected_regions(&released, final_rect, colors, false);
    assert_selected_regions(&released, source_rect, colors, true);

    time += 0.2;
    let hidden = click_photo_overlay(
        &fixture,
        &mut field,
        &surfaces,
        time,
        final_rect,
        "Hide admission marks",
    );
    assert!(!crate::process_result::ResultPhoto::admission_visible(
        &fixture.ctx
    ));
    assert_selection_hidden(&hidden, [final_rect, source_rect], colors);
    assert_eq!(
        main_image(&hidden, fixture.final_image.id()),
        Some(final_rect)
    );
    assert_eq!(
        main_image(&hidden, fixture.photos[88].texture.id()),
        Some(source_rect)
    );
    assert_eq!(field.participation.spans(), selected);
    time += 0.3;
    let restored = click_photo_overlay(
        &fixture,
        &mut field,
        &surfaces,
        time,
        final_rect,
        "Selected detail size",
    );
    assert_selected_regions(&restored, final_rect, colors, false);
    assert_selected_regions(&restored, source_rect, colors, true);

    time += 0.3;
    fixture.paint_events(
        &mut field,
        &surfaces,
        time,
        vec![key_event(egui::Key::Escape, true)],
    );
    time += 0.3;
    let escaped = fixture.paint_events(
        &mut field,
        &surfaces,
        time,
        vec![key_event(egui::Key::Escape, false)],
    );
    assert!(
        field.participation.spans().is_empty(),
        "the real Escape path clears both selected ranges"
    );
    let escaped_rect = main_image(&escaped, fixture.final_image.id()).unwrap();
    assert_selection_hidden(&escaped, [escaped_rect, source_rect], colors);
}

#[test]
fn v29_current_capture_intersects_pins_on_both_photos_without_changing_saved_ranges() {
    let mut fixture = Fixture::with_overlapping_ranges();
    fixture.progress.admission_archive.ingest(
        &DiagnosticSurface {
            sequence: 50_000,
            frame: 97,
            level: 0,
            kind: DiagnosticKind::GateSupport,
            scope: DiagnosticScope::Frame,
            scale: DiagnosticScale::Linear,
            width: 128,
            height: 96,
            min: 0.0,
            max: 1.0,
            folded: 1,
            pixels: (0..96)
                .flat_map(|y| {
                    (0..128).map(move |x| {
                        if (50..112).contains(&x) && (16..80).contains(&y) {
                            255
                        } else {
                            0
                        }
                    })
                })
                .collect::<Vec<_>>()
                .into(),
        },
        ANALYSIS,
    );
    let surfaces = fixture.surfaces();
    let (mut field, _, mut time) = settle(&fixture, &surfaces, true);
    let initial = fixture.paint(&mut field, &surfaces, time, Pos2::ZERO);
    let at = |frame| timeline_point(&initial, frame);
    timeline_gesture(
        &fixture,
        &mut field,
        &surfaces,
        &mut time,
        [at(4); 2],
        egui::Modifiers::NONE,
    );
    timeline_gesture(
        &fixture,
        &mut field,
        &surfaces,
        &mut time,
        [at(12); 2],
        egui::Modifiers::SHIFT,
    );
    let pins = field.participation.spans().to_vec();
    assert_eq!(
        pins.iter()
            .map(|span| (span.start, span.end))
            .collect::<Vec<_>>(),
        [(4, 12)]
    );
    let current_color = crate::process_participation::SelectionSpan {
        start: 97,
        end: 97,
        id: usize::MAX,
    }
    .color();
    let colors = [pins[0].color(), current_color];
    assert_ne!(colors[0], colors[1]);

    timeline_gesture(
        &fixture,
        &mut field,
        &surfaces,
        &mut time,
        [at(97); 2],
        egui::Modifiers::NONE,
    );
    time += 0.6;
    let held = fixture.paint(&mut field, &surfaces, time, Pos2::ZERO);
    assert_eq!(field.dense_current_frame(), Some(97));
    assert_eq!(field.participation.spans(), pins);
    assert!(has(&held, "CURRENT 098"));
    let final_rect = main_image(&held, fixture.final_image.id()).unwrap();
    let source_rect = main_image(&held, fixture.photos[97].texture.id())
        .expect("actual current capture is displayed");
    assert_selected_regions(&held, final_rect, colors, false);
    assert_selected_regions(&held, source_rect, colors, true);

    // While a different request is pending, identity follows the displayed
    // pixels. It must never put the requested frame's polygon on the old JPEG.
    field.hover_source = Some(98);
    assert_eq!(field.dense_current_frame(), Some(97));
    field.hover_source = None;

    time += 0.3;
    fixture.paint(&mut field, &surfaces, time, at(7));
    time += 0.6;
    let inside = fixture.paint(&mut field, &surfaces, time, at(7));
    assert_eq!(field.inspection_frame(), Some(7));
    assert_eq!(field.dense_current_frame(), Some(7));
    assert_eq!(field.participation.spans(), pins);
    assert!(has(&inside, "CURRENT 008"));
    let inside_source = main_image(&inside, fixture.photos[7].texture.id()).unwrap();
    for (photo, approximate) in [(final_rect, false), (inside_source, true)] {
        let palette = selection_colors(colors, approximate);
        let overlap = colored_triangles(&inside, photo, palette[2]);
        assert!(
            overlap.iter().any(|&triangle| triangle_contains(
                triangle,
                photo.min + photo.size() * egui::vec2(0.25, 0.5)
            )),
            "a capture inside the pin must still have a distinct current footprint"
        );
        let pin_only = colored_triangles(&inside, photo, palette[0]);
        assert!(
            pin_only.iter().any(|&triangle| triangle_contains(
                triangle,
                photo.min + photo.size() * egui::vec2(0.55, 0.5)
            )),
            "the pin union must keep evidence beyond this one capture"
        );
        assert!(
            colored_triangles(&inside, photo, palette[4]).len() > 5,
            "current-colour stripes must really be painted inside the pin"
        );
        assert!(
            colored_triangles(&inside, photo, palette[1]).is_empty(),
            "a wholly contained current region has no exclusive fill"
        );
    }
    time += 0.5;
    let left = fixture.paint(&mut field, &surfaces, time, Pos2::ZERO);
    assert_eq!(
        field.dense_current_frame(),
        Some(7),
        "leaving the strip keeps the last actually displayed hover capture"
    );
    assert_eq!(field.participation.spans(), pins);
    assert!(has(&left, "CURRENT 008"));
    assert!(main_image(&left, fixture.photos[7].texture.id()).is_some());
    timeline_gesture(
        &fixture,
        &mut field,
        &surfaces,
        &mut time,
        [at(97); 2],
        egui::Modifiers::NONE,
    );
    time += 0.4;
    let restored_current = fixture.paint(&mut field, &surfaces, time, Pos2::ZERO);
    assert_eq!(field.dense_current_frame(), Some(97));
    assert_eq!(field.participation.spans(), pins);
    assert_selected_regions(&restored_current, final_rect, colors, false);
    assert_selected_regions(&restored_current, source_rect, colors, true);

    time += 0.2;
    let peek = fixture.paint_events(
        &mut field,
        &surfaces,
        time,
        vec![key_event(egui::Key::Space, true)],
    );
    assert_selection_hidden(&peek, [final_rect, source_rect], colors);
    assert_eq!(field.participation.spans(), pins);
    time += 0.2;
    let released = fixture.paint_events(
        &mut field,
        &surfaces,
        time,
        vec![key_event(egui::Key::Space, false)],
    );
    assert_selected_regions(&released, final_rect, colors, false);
    assert_selected_regions(&released, source_rect, colors, true);
    time += 0.2;
    let hidden = click_photo_overlay(
        &fixture,
        &mut field,
        &surfaces,
        time,
        final_rect,
        "Hide admission marks",
    );
    assert_selection_hidden(&hidden, [final_rect, source_rect], colors);
    time += 0.3;
    let restored = click_photo_overlay(
        &fixture,
        &mut field,
        &surfaces,
        time,
        final_rect,
        "Selected detail size",
    );
    assert_selected_regions(&restored, final_rect, colors, false);
    assert_selected_regions(&restored, source_rect, colors, true);
    time += 0.2;
    fixture.paint_events(
        &mut field,
        &surfaces,
        time,
        vec![key_event(egui::Key::Escape, true)],
    );
    time += 0.2;
    let cleared = fixture.paint_events(
        &mut field,
        &surfaces,
        time,
        vec![key_event(egui::Key::Escape, false)],
    );
    assert!(field.participation.spans().is_empty());
    assert_eq!(field.dense_current_frame(), None);
    assert_selection_hidden(
        &cleared,
        [
            main_image(&cleared, fixture.final_image.id()).unwrap(),
            source_rect,
        ],
        colors,
    );
}

#[test]
fn completed_comparison_retains_admission_bytes_until_the_actual_archive_receipt_changes() {
    let mut fixture = Fixture::new();
    let (mut field, image, time) = {
        let surfaces = fixture.surfaces();
        settle(&fixture, &surfaces, true)
    };
    let (meta, packet) = field
        .retained_admission
        .as_ref()
        .expect("real comparison synthesizes its archived mask");
    assert_eq!(packet.frame, 65);
    let old_meta = *meta;
    let old_pixels = std::sync::Arc::clone(&packet.pixels);
    let old_positive = old_pixels.iter().filter(|&&value| value == 255).count();
    assert!(
        old_positive > 0 && old_positive < old_pixels.len(),
        "mixed baseline must be capable of changing"
    );
    let level = packet.level;
    {
        let surfaces = fixture.surfaces();
        for step in 0..40 {
            fixture.paint(
                &mut field,
                &surfaces,
                time + step as f64 / 120.0,
                image.min + image.size() * egui::vec2(0.2 + step as f32 / 100.0, 0.43),
            );
            let (current_meta, current) = field.retained_admission.as_ref().unwrap();
            assert_eq!(*current_meta, old_meta);
            assert!(
                std::sync::Arc::ptr_eq(&current.pixels, &old_pixels),
                "pointer motion must not recreate the archived byte mask"
            );
        }
    }
    let replacement = DiagnosticSurface {
        sequence: 100_000,
        frame: 65,
        level,
        kind: DiagnosticKind::GateSupport,
        scope: DiagnosticScope::Frame,
        scale: DiagnosticScale::Linear,
        width: old_meta.samples[0],
        height: old_meta.samples[1],
        min: 0.0,
        max: 1.0,
        folded: 1,
        pixels: vec![0; old_pixels.len()].into(),
    };
    let previous_len = fixture.progress.admission_archive.len();
    fixture
        .progress
        .admission_archive
        .ingest(&replacement, ANALYSIS);
    assert_eq!(
        fixture.progress.admission_archive.len(),
        previous_len,
        "this is replacement, not a changed archive length"
    );
    let surfaces = fixture.surfaces();
    fixture.paint(&mut field, &surfaces, time + 1.0, image.center());
    let (current_meta, current) = field.retained_admission.as_ref().unwrap();
    assert_eq!(current_meta.sequence, 100_000);
    assert!(!std::sync::Arc::ptr_eq(&current.pixels, &old_pixels));
    assert_eq!(
        current.pixels.iter().filter(|&&value| value == 255).count(),
        0
    );
    assert_eq!(
        old_pixels.iter().filter(|&&value| value == 255).count(),
        old_positive,
        "new publication must not mutate a retained old receipt"
    );
    let new_pixels = std::sync::Arc::clone(&current.pixels);
    fixture.paint(&mut field, &surfaces, time + 1.4, image.center());
    assert!(std::sync::Arc::ptr_eq(
        &field.retained_admission.as_ref().unwrap().1.pixels,
        &new_pixels
    ));
    drop(surfaces);
    let foreign_extent = [ANALYSIS[0] + 2, ANALYSIS[1]];
    let foreign = DiagnosticSurface {
        sequence: 100_001,
        pixels: vec![255; old_pixels.len()].into(),
        ..replacement.clone()
    };
    fixture
        .progress
        .admission_archive
        .ingest(&foreign, foreign_extent);
    assert_eq!(
        fixture
            .progress
            .admission_archive
            .metadata(level, 65)
            .unwrap()
            .extent,
        foreign_extent,
        "negative control must actually publish a foreign analysis domain"
    );
    assert_eq!(
        fixture
            .progress
            .analysis_size
            .or(fixture.progress.plane_size),
        Some(ANALYSIS),
        "the photograph certificate stays in the original domain"
    );
    let surfaces = fixture.surfaces();
    let foreign_paint = fixture.paint(&mut field, &surfaces, time + 1.8, image.center());
    assert!(
        main_image(&foreign_paint, fixture.final_image.id()).is_some(),
        "rejecting foreign evidence must not hide the real final photo"
    );
    assert!(
        field.retained_admission.is_none(),
        "a certified final photo cannot borrow a differently sized archive mask"
    );
}

#[test]
#[ignore = "explicit full-workspace CPU paint+tessellation benchmark; not GPU FPS"]
fn benchmark_finished_workspace_pointer_sweeps() {
    let fixture = Fixture::new();
    let surfaces = fixture.surfaces();
    let mut timings = [Vec::new(), Vec::new()];
    let mut vertices = [0usize; 2];
    for sweep in 0..6 {
        for mode in if sweep % 2 == 0 { [0, 1] } else { [1, 0] } {
            let (mut field, image, mut time) = settle(&fixture, &surfaces, mode == 1);
            let start = Instant::now();
            for step in 0..80 {
                time += 1.0 / 120.0;
                let phase = if sweep % 2 == 0 { step } else { 79 - step } as f32 / 79.0;
                // Cross actual telemetry cells, rather than only moving within
                // a cached cell. Avoid the bottom-right overview navigator.
                let at =
                    image.min + image.size() * egui::vec2(0.15 + phase * 0.65, 0.30 + phase * 0.24);
                let output = fixture.paint(&mut field, &surfaces, time, at);
                let primitives = fixture
                    .ctx
                    .tessellate(output.shapes, output.pixels_per_point);
                vertices[mode] = primitives
                    .iter()
                    .map(|p| match &p.primitive {
                        egui::epaint::Primitive::Mesh(mesh) => mesh.vertices.len(),
                        _ => 0,
                    })
                    .sum();
                std::hint::black_box(primitives);
            }
            timings[mode].push(start.elapsed().as_secs_f64() * 1000.0 / 80.0);
        }
    }
    println!(
        "full_workspace_cpu_ms_per_frame process={:?} source={:?}",
        timings[0], timings[1]
    );
    println!(
        "full_workspace_cpu_min_ms process={} source={} final_vertices={vertices:?} frames={FRAMES} levels=8 max_grid=128x96 confidence_map=absent",
        timings[0].iter().copied().fold(f64::INFINITY, f64::min),
        timings[1].iter().copied().fold(f64::INFINITY, f64::min)
    );
}
