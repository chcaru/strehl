//! Live preview must survive sparse paints without retaining build checkpoints.
use super::*;
use crate::pipeline::PipelineProgress;

fn line(prefix: usize) -> String {
    format!(
        "STREHL_UI_PROGRESS event=diagnostic seq={prefix} frame={} level=1 kind=preview scope=stack scale=linear width=2 height=2 min=0 max={} folded={prefix} total=12 sampling=nearest data={:02x}4080ff\n",
        prefix - 1,
        100 + prefix,
        prefix * 7
    )
}
fn input(progress: &PipelineProgress) -> Input<'_> {
    Input {
        epoch: 1,
        progress,
        frame_count: 12,
        selected: 0,
        inspected_pair: None,
        photos: &[],
        inspection_photos: &[],
        surfaces: &[],
        output: None,
        output_size: None,
    }
}
fn draw(
    theater: &mut ProcessTheater,
    ctx: &egui::Context,
    progress: &PipelineProgress,
    time: f64,
) -> egui::FullOutput {
    ctx.run(
        egui::RawInput {
            time: Some(time),
            screen_rect: Some(Rect::from_min_size(Pos2::ZERO, egui::vec2(1410.0, 850.0))),
            ..Default::default()
        },
        |ctx| {
            egui::CentralPanel::default()
                .frame(egui::Frame::NONE)
                .show(ctx, |ui| {
                    theater.show(
                        ui,
                        ui.max_rect(),
                        &input(progress),
                        &mut Response::default(),
                    );
                });
        },
    )
}
#[test]
fn replay_paints_only_the_latest_real_preview_without_build_navigation() {
    let mut progress = PipelineProgress::default();
    progress.ingest("planes: 120 x 80 per CFA plane\n");
    for prefix in 1..=12 {
        progress.ingest(&line(prefix));
    }
    let ctx = egui::Context::default();
    let mut theater = ProcessTheater::default();
    let output = draw(&mut theater, &ctx, &progress, 0.1);
    let latest = theater.latest_preview.as_ref().unwrap();
    assert_eq!(latest.folded, 12);
    assert_eq!(theater.hero.as_ref().unwrap().plate.folded, 12);
    assert!(output.shapes.iter().any(|shape| matches!(&shape.shape,
        egui::Shape::Mesh(mesh) if mesh.texture_id == latest.texture.id())));
    assert!(!output.shapes.iter().any(|shape| matches!(&shape.shape,
        egui::Shape::Text(text) if text.galley.text().contains("BUILD"))));
    assert_eq!(theater.preview_range, Some((0.0, 101.0)));
}

#[test]
fn sparse_replay_and_incremental_paints_reach_the_same_latest_observed_image() {
    let mut progress = PipelineProgress::default();
    progress.ingest("planes: 120 x 80 per CFA plane\n");
    let ctx = egui::Context::default();
    let mut live = ProcessTheater::default();
    for prefix in 1..=12 {
        progress.ingest(&line(prefix));
        draw(&mut live, &ctx, &progress, prefix as f64);
        draw(&mut live, &ctx, &progress, prefix as f64 + 0.5);
    }
    let mut replay = ProcessTheater::default();
    draw(&mut replay, &egui::Context::default(), &progress, 0.1);
    assert_eq!(live.hero.as_ref().unwrap().plate.sequence, 12);
    assert_eq!(replay.hero.as_ref().unwrap().plate.sequence, 12);
    assert_eq!(live.preview_range, replay.preview_range);
}

#[test]
fn crop_reset_replaces_the_live_preview_and_its_domain() {
    let mut progress = PipelineProgress::default();
    progress.ingest("planes: 120 x 80 per CFA plane\n");
    for prefix in 1..=12 {
        progress.ingest(&line(prefix));
    }
    let ctx = egui::Context::default();
    let mut theater = ProcessTheater::default();
    draw(&mut theater, &ctx, &progress, 0.1);
    let old_texture = theater.latest_preview.as_ref().unwrap().texture.id();
    progress.ingest(
        "analysis domain: 100 x 60 at full-plane origin (4, 7) -- Crop is applied BEFORE luma\n",
    );
    progress.ingest(&line(1).replace("seq=1 ", "seq=13 "));
    draw(&mut theater, &ctx, &progress, 1.0);
    let current = theater.latest_preview.as_ref().unwrap();
    assert_eq!(current.sequence, 13);
    assert_ne!(current.texture.id(), old_texture);
    assert_eq!(current.folded, 1);
}

#[test]
fn inspection_layout_prioritizes_photos_and_keeps_lenses_inside_on_wide_and_tall_windows() {
    for size in [
        egui::vec2(1840.0, 820.0),
        egui::vec2(800.0, 700.0),
        egui::vec2(550.0, 480.0),
    ] {
        let bounds = Rect::from_min_size(egui::pos2(30.0, 40.0), size);
        let (title, hero, lenses, rail) = inspection_layout(bounds);
        for rect in [title, hero, lenses, rail] {
            assert!(bounds.contains_rect(rect) && rect.is_positive());
        }
        assert!(hero.width() > bounds.width() * 0.85);
        assert!(hero.bottom() < lenses.top());
        assert!(rail.right() < hero.left());
    }
}
