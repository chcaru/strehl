//! Independent resize witnesses. The adversarial choices are collapse-direction
//! drags, extreme legal saved proportions, and slow motion below drag threshold.
use super::*;
use crate::workspace_layout::WorkspaceLayout;

fn visible(layout: Layout, complete: bool) -> Vec<(&'static str, Rect)> {
    let mut parts = vec![
        ("title", layout.title),
        ("photo", layout.hero),
        ("matrix", layout.signals),
        ("fingerprint", layout.weave),
        ("lenses", layout.contributions),
        ("history", layout.history),
    ];
    if !complete {
        parts.extend([
            ("network", layout.network),
            ("ledger", layout.ledger),
            ("source A", layout.origins[0]),
            ("source B", layout.origins[1]),
        ]);
    }
    parts
}

#[test]
fn every_resize_direction_retains_positive_disjoint_visible_regions() {
    for [width, height] in [
        [1000.0, 760.0],
        [1040.0, 480.0],
        [1410.0, 650.0],
        [2550.0, 1200.0],
    ] {
        let rect = Rect::from_min_size(egui::pos2(17.0, 131.0), egui::vec2(width, height));
        for complete in [false, true] {
            for network in [0.14, 0.38] {
                for detail in [0.36, 0.80] {
                    for final_detail in [0.25, 0.72] {
                        for lower in [-0.12, 0.20] {
                            for fingerprint in [-0.04, 0.16] {
                                let mut prefs = WorkspaceLayout {
                                    network,
                                    detail,
                                    final_detail,
                                    lower,
                                    fingerprint,
                                    focus_photo: false,
                                };
                                prefs.sanitize();
                                let arranged = Layout::configured(rect, complete, prefs);
                                let minimum_matrix_width = if complete { 380.0 } else { 360.0 };
                                assert!(
                                    arranged.signals.width() >= minimum_matrix_width - 0.1,
                                    "diagnostic matrix cannot surrender its readable physical width to saved fractions: width={width}, complete={complete}, {prefs:?}, actual={}",
                                    arranged.signals.width()
                                );
                                let regions = visible(arranged, complete);
                                for (i, &(name, region)) in regions.iter().enumerate() {
                                    assert!(
                                        region.width() > 0.0 && region.height() > 0.0,
                                        "{name} collapsed at {width}x{height}, complete={complete}, {prefs:?}: {region:?}"
                                    );
                                    assert!(
                                        rect.expand(0.1).contains_rect(region),
                                        "{name} escapes its workspace at {width}x{height}: {region:?}"
                                    );
                                    for &(other_name, other) in &regions[i + 1..] {
                                        let intersection = region.intersect(other);
                                        assert!(
                                            intersection.width() <= 0.1
                                                || intersection.height() <= 0.1,
                                            "{name} overlaps {other_name} at {width}x{height}, complete={complete}, {prefs:?}"
                                        );
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}

fn seam_frame(
    ctx: &egui::Context,
    time: f64,
    events: Vec<egui::Event>,
    value: &mut f32,
    modal: bool,
) {
    let _ = ctx.run(
        egui::RawInput {
            screen_rect: Some(Rect::from_min_size(Pos2::ZERO, egui::vec2(800.0, 600.0))),
            time: Some(time),
            events,
            ..Default::default()
        },
        |ctx| {
            egui::CentralPanel::default().show(ctx, |ui| {
                let rect = Rect::from_min_max(
                    egui::pos2(*value - 5.0, 50.0),
                    egui::pos2(*value + 5.0, 550.0),
                );
                *value += crate::workspace_layout::seam(ui, "review-seam", rect, true).0;
            });
            if modal {
                egui::Modal::new(egui::Id::new("resize-review-modal")).show(ctx, |ui| {
                    ui.label("Modal");
                });
            }
        },
    );
}

fn pointer(at: Pos2, pressed: bool) -> egui::Event {
    egui::Event::PointerButton {
        pos: at,
        button: egui::PointerButton::Primary,
        pressed,
        modifiers: egui::Modifiers::NONE,
    }
}

#[test]
fn resizing_preserves_slow_press_motion_and_modal_owns_its_input() {
    let ctx = egui::Context::default();
    let mut x = 300.0;
    let start = egui::pos2(x, 180.0);
    seam_frame(&ctx, 0.0, vec![], &mut x, false);
    seam_frame(
        &ctx,
        0.1,
        vec![egui::Event::PointerMoved(start), pointer(start, true)],
        &mut x,
        false,
    );
    for step in 1..=5 {
        seam_frame(
            &ctx,
            0.1 + step as f64 * 0.02,
            vec![egui::Event::PointerMoved(
                start + egui::vec2(step as f32, 0.0),
            )],
            &mut x,
            false,
        );
    }
    let end = start + egui::vec2(27.0, 0.0);
    seam_frame(
        &ctx,
        0.25,
        vec![egui::Event::PointerMoved(end)],
        &mut x,
        false,
    );
    seam_frame(&ctx, 0.3, vec![pointer(end, false)], &mut x, false);
    assert!(
        (x - 327.0).abs() < 0.01,
        "resize lost pre-threshold pointer displacement: {x}"
    );

    seam_frame(&ctx, 0.4, vec![], &mut x, true);
    seam_frame(&ctx, 0.5, vec![], &mut x, true);
    let blocked_start = egui::pos2(x, 180.0);
    seam_frame(
        &ctx,
        0.6,
        vec![
            egui::Event::PointerMoved(blocked_start),
            pointer(blocked_start, true),
        ],
        &mut x,
        true,
    );
    let blocked_end = blocked_start + egui::vec2(80.0, 0.0);
    seam_frame(
        &ctx,
        0.7,
        vec![egui::Event::PointerMoved(blocked_end)],
        &mut x,
        true,
    );
    seam_frame(&ctx, 0.8, vec![pointer(blocked_end, false)], &mut x, true);
    assert!(
        (x - 327.0).abs() < 0.01,
        "background resize moved through modal"
    );
}

#[test]
fn legal_minimum_network_resize_does_not_remove_the_capture_board() {
    let ctx = egui::Context::default();
    let mut theater = ProcessTheater::default();
    theater.layout.network = 0.14;
    let progress = crate::pipeline::PipelineProgress::default();
    let output = ctx.run(
        egui::RawInput {
            screen_rect: Some(Rect::from_min_size(Pos2::ZERO, egui::vec2(1000.0, 600.0))),
            time: Some(0.0),
            ..Default::default()
        },
        |ctx| {
            egui::CentralPanel::default()
                .frame(egui::Frame::NONE)
                .show(ctx, |ui| {
                    theater.show(
                        ui,
                        ui.max_rect(),
                        &Input {
                            epoch: 1,
                            progress: &progress,
                            frame_count: 13,
                            selected: 0,
                            inspected_pair: None,
                            photos: &[],
                            inspection_photos: &[],
                            surfaces: &[],
                            output: None,
                            output_size: None,
                        },
                        &mut Response::default(),
                    );
                });
        },
    );
    assert!(
        output.shapes.iter().any(|shape| matches!(&shape.shape,
        egui::Shape::Text(text) if text.galley.text() == "CAPTURES / DIRECT FITS")),
        "a legal resize must not silently erase the capture-index surface"
    );
}
