//! CPU paint + tessellation of the Stack station's parts on long stacks
//! (spec 5.3, 10.1 item 9). Stage 1 drives the parts directly at the
//! reference rectangles; stage 2 repeats this inside the composed station.
//! Excludes decoding, GPU upload/presentation and operating-system input.
use crate::{
    core_sample::{CoreInput, CorePalette, CoreSample},
    depth_rail::{DepthRail, RailMarkers, RailPalette, evidence_revision},
    filmstrip::{FilmMarks, FilmPalette, Filmstrip},
    pipeline::{
        DiagnosticKind, DiagnosticScale, DiagnosticScope, DiagnosticSurface, PipelineProgress,
    },
    plane_lens::{LensEvidence, LensPalette, PlaneLens, PlaneLensView},
    process_admission_regions::RegionSettings,
};
use eframe::egui::{self, Color32, Pos2, Rect};
use std::time::Instant;

const ANALYSIS: [usize; 2] = [3516, 2344];
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

/// Level-major ingestion: the finest level is complete first; whatever the
/// archive cap drops is counted and printed, never assumed.
fn progress(planes: usize) -> PipelineProgress {
    let mut progress = PipelineProgress::default();
    let mut sequence = 0;
    for level in 0..8 {
        let spacing = 1usize << level;
        let width = ANALYSIS[0].div_ceil(spacing).min(128);
        let height = ANALYSIS[1].div_ceil(spacing).min(96);
        for plane in 0..planes {
            sequence += 1;
            let centre = (plane as f32 + 0.5) / planes as f32;
            let reach = 0.05 + 0.02 * level as f32;
            let pixels: Vec<u8> = (0..width * height)
                .map(|index| {
                    let x = (index % width) as f32 / width as f32;
                    let y = (index / width) as f32 / height as f32;
                    if (x - centre).abs() < reach && (index + plane) % 7 != 0 && y > 0.1 {
                        255
                    } else {
                        0
                    }
                })
                .collect();
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
                    pixels: pixels.into(),
                },
                ANALYSIS,
            );
        }
    }
    progress
}

struct Parts {
    rail: DepthRail,
    film: Filmstrip,
    core: CoreSample,
    lens: PlaneLens,
    view: PlaneLensView,
}

#[allow(clippy::too_many_arguments)]
fn frame(
    ctx: &egui::Context,
    parts: &mut Parts,
    progress: &PipelineProgress,
    planes: usize,
    final_texture: egui::TextureId,
    pointer: Pos2,
    time: f64,
) -> egui::FullOutput {
    ctx.run(
        egui::RawInput {
            screen_rect: Some(Rect::from_min_size(Pos2::ZERO, egui::vec2(1680.0, 1050.0))),
            time: Some(time),
            events: vec![egui::Event::PointerMoved(pointer)],
            ..Default::default()
        },
        |ctx| {
            egui::CentralPanel::default()
                .frame(egui::Frame::NONE)
                .show(ctx, |ui| {
                    let archive = &progress.admission_archive;
                    let level = parts.lens.level();
                    parts.rail.update(
                        archive,
                        &progress.sampled_mask_history,
                        planes,
                        level,
                        evidence_revision(progress),
                    );
                    parts.film.layout(FILM.width(), planes);
                    parts.film.update(archive);
                    let rail = parts.rail.interact(ui, RAIL, egui::Id::new("rail"));
                    let film = parts.film.interact(ui, FILM, egui::Id::new("film"));
                    parts.lens.hover(rail.hovered.or(film.hovered));
                    let core = parts.core.show(
                        ui,
                        CoreInput {
                            archive,
                            level,
                            analysis_extent: ANALYSIS,
                            extent: [7032, 4688],
                            planes,
                            image: PHOTO,
                            aperture: Rect::from_min_max(Pos2::ZERO, egui::pos2(1.0, 1.0)),
                            final_texture: Some(final_texture),
                            geometry: None,
                            viewport: Rect::from_min_size(Pos2::ZERO, egui::vec2(1332.0, 1050.0)),
                        },
                        &|_| None,
                        CorePalette::GRAPHITE,
                    );
                    let key = parts.core.rail_key(level);
                    let core_sample = &parts.core;
                    parts
                        .rail
                        .set_region(key, || core_sample.rail_series(level).collect::<Vec<_>>());
                    if let Some(plane) = parts.lens.shown() {
                        let evidence = LensEvidence {
                            archive,
                            domain: [1, 0],
                            extent: Some(ANALYSIS),
                            settings: RegionSettings::default(),
                            geometry: None,
                        };
                        let lookup = parts.view.region(ui.ctx(), evidence, plane, level);
                        if let Some(region) = &lookup.region {
                            PlaneLensView::dim(ui.painter(), PHOTO);
                            parts.view.paint_final_region(
                                ui.painter(),
                                region,
                                PHOTO,
                                Rect::from_min_max(Pos2::ZERO, egui::pos2(1.0, 1.0)),
                                LensPalette::GRAPHITE,
                            );
                        }
                        if let Some(card) =
                            crate::plane_lens::peek_rect(CANVAS, RAIL, planes, plane)
                        {
                            let share = crate::plane_lens::kept_share(archive, level, plane);
                            parts.view.paint_peek(
                                ui.painter(),
                                card,
                                pointer.x,
                                plane,
                                share,
                                None,
                                lookup.region.as_ref(),
                                LensPalette::GRAPHITE,
                            );
                        }
                    }
                    parts.rail.paint(
                        ui.painter(),
                        RAIL,
                        RailPalette::GRAPHITE,
                        RailMarkers {
                            hover: parts.lens.hovered(),
                            head: parts.lens.held().or(core.peak),
                        },
                    );
                    parts.film.paint(
                        ui.painter(),
                        FILM,
                        FilmPalette::GRAPHITE,
                        FilmMarks {
                            pointer: parts.lens.hovered(),
                            held: parts.lens.held(),
                        },
                    );
                });
        },
    )
}

#[test]
#[ignore = "explicit Stack parts CPU paint+tessellation benchmark; not GPU FPS"]
fn benchmark_stack_parts_pointer_sweeps() {
    for planes in [130, 1_500, 6_000] {
        let built = Instant::now();
        let progress = progress(planes);
        let build_s = built.elapsed().as_secs_f64();
        let ctx = egui::Context::default();
        crate::theme::install(&ctx);
        let texture = ctx.load_texture(
            "final",
            egui::ColorImage::filled([192, 128], Color32::GOLD),
            egui::TextureOptions::LINEAR,
        );
        let mut parts = Parts {
            rail: DepthRail::default(),
            film: Filmstrip::default(),
            core: CoreSample::default(),
            lens: PlaneLens::default(),
            view: PlaneLensView::default(),
        };
        parts.lens.set_planes(planes);
        let mut time = 0.0;
        // Warm every cache once (the first frame builds the series).
        for _ in 0..3 {
            time += 1.0 / 120.0;
            frame(
                &ctx,
                &mut parts,
                &progress,
                planes,
                texture.id(),
                PHOTO.center(),
                time,
            );
        }
        let mut photo = Vec::new();
        let mut rail = Vec::new();
        for sweep in 0..4 {
            // Over the photograph: the live core sample crosses sample cells.
            let start = Instant::now();
            for step in 0..120 {
                time += 1.0 / 120.0;
                let phase = if sweep % 2 == 0 { step } else { 119 - step } as f32 / 119.0;
                let at =
                    PHOTO.min + PHOTO.size() * egui::vec2(0.1 + 0.8 * phase, 0.3 + 0.4 * phase);
                let output = frame(&ctx, &mut parts, &progress, planes, texture.id(), at, time);
                std::hint::black_box(ctx.tessellate(output.shapes, output.pixels_per_point));
            }
            photo.push(start.elapsed().as_secs_f64() * 1000.0 / 120.0);
            // Along the rail: every frame peeks at another plane.
            let start = Instant::now();
            for step in 0..120 {
                time += 1.0 / 120.0;
                let phase = if sweep % 2 == 0 { step } else { 119 - step } as f32 / 119.0;
                let at = egui::pos2(
                    RAIL.left() + 20.0 + phase * (RAIL.width() - 40.0),
                    RAIL.center().y,
                );
                let output = frame(&ctx, &mut parts, &progress, planes, texture.id(), at, time);
                std::hint::black_box(ctx.tessellate(output.shapes, output.pixels_per_point));
            }
            rail.push(start.elapsed().as_secs_f64() * 1000.0 / 120.0);
        }
        let min = |values: &[f64]| values.iter().copied().fold(f64::INFINITY, f64::min);
        println!(
            "stack_parts_cpu_ms_per_frame planes={planes} retained_maps={} dropped_maps={} fixture_build_s={build_s:.1} photo_sweep={photo:?} rail_sweep={rail:?}",
            progress.admission_archive.len(),
            progress.admission_archive.dropped()
        );
        println!(
            "stack_parts_cpu_min_ms planes={planes} photo_sweep={:.3} rail_sweep={:.3}",
            min(&photo),
            min(&rail)
        );
    }
}
