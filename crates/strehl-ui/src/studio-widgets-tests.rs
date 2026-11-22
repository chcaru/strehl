use super::*;
use crate::studio_theme::GRAPHITE;
use std::cell::Cell;

fn context() -> egui::Context {
    let ctx = egui::Context::default();
    crate::theme::install(&ctx);
    ctx
}

fn frame(
    ctx: &egui::Context,
    time: f64,
    events: Vec<egui::Event>,
    mut add: impl FnMut(&mut Ui),
) -> egui::FullOutput {
    ctx.run(
        egui::RawInput {
            screen_rect: Some(Rect::from_min_size(Pos2::ZERO, egui::vec2(640.0, 400.0))),
            time: Some(time),
            events,
            ..Default::default()
        },
        |ctx| {
            egui::CentralPanel::default()
                .frame(egui::Frame::NONE.inner_margin(20))
                .show(ctx, |ui| add(ui));
        },
    )
}

fn press(at: Pos2, pressed: bool) -> Vec<egui::Event> {
    vec![
        egui::Event::PointerMoved(at),
        egui::Event::PointerButton {
            pos: at,
            button: egui::PointerButton::Primary,
            pressed,
            modifiers: egui::Modifiers::NONE,
        },
    ]
}

/// Press and release over `at` across two frames, as a real click arrives.
fn click(ctx: &egui::Context, time: f64, at: Pos2, add: &mut dyn FnMut(&mut Ui)) {
    frame(ctx, time, press(at, true), &mut *add);
    frame(ctx, time + 0.05, press(at, false), &mut *add);
}

/// Shapes the widget painted, without the panel's own transparent background.
fn painted(output: &egui::FullOutput) -> Vec<&egui::Shape> {
    output
        .shapes
        .iter()
        .map(|shape| &shape.shape)
        .filter(|shape| {
            !matches!(shape, egui::Shape::Rect(r)
                if r.fill == Color32::TRANSPARENT && r.stroke.is_empty())
        })
        .collect()
}

fn texts(output: &egui::FullOutput) -> Vec<(String, Rect, f32)> {
    output
        .shapes
        .iter()
        .filter_map(|shape| match &shape.shape {
            egui::Shape::Text(text) => Some((
                text.galley.text().to_owned(),
                text.visual_bounding_rect(),
                text.galley
                    .job
                    .sections
                    .iter()
                    .map(|section| section.format.font_id.size)
                    .fold(f32::INFINITY, f32::min),
            )),
            _ => None,
        })
        .collect()
}

#[test]
fn buttons_have_the_three_heights_and_their_kinds_paint_differently() {
    let ctx = context();
    let mut rects = Vec::new();
    let output = frame(&ctx, 0.0, vec![], |ui| {
        rects.clear();
        rects.push(ui.add(Button::new("Render again").small()).rect);
        rects.push(ui.add(Button::new("Render again")).rect);
        rects.push(
            ui.add(Button::primary("Develop this render").large().chevron())
                .rect,
        );
        rects.push(ui.add(Button::quiet("Note")).rect);
        rects.push(ui.add(Button::danger("Shut down")).rect);
    });
    assert_eq!(
        rects.iter().take(3).map(|r| r.height()).collect::<Vec<_>>(),
        [SMALL_HEIGHT, CONTROL_HEIGHT, LARGE_HEIGHT]
    );
    let fills: Vec<_> = output
        .shapes
        .iter()
        .filter_map(|shape| match &shape.shape {
            egui::Shape::Rect(rect) => Some(rect.clone()),
            _ => None,
        })
        .collect();
    assert!(
        fills
            .iter()
            .any(|r| r.rect == rects[2] && r.fill == GRAPHITE.accent),
        "the main action is filled amber"
    );
    assert!(
        fills
            .iter()
            .any(|r| r.rect == rects[1] && r.stroke.color == GRAPHITE.line2),
        "a standard button is a hairline outline"
    );
    assert!(
        !fills.iter().any(|r| r.rect == rects[3]),
        "a quiet button has neither fill nor outline"
    );
    let danger = texts(&output)
        .into_iter()
        .find(|(text, ..)| text == "Shut down")
        .unwrap();
    assert!(rects[4].contains_rect(danger.1));
    for (text, rect, size) in texts(&output) {
        assert!(size >= 10.5, "{text} is {size} px");
        assert!(
            rects.iter().any(|r| r.contains_rect(rect)),
            "{text} must sit inside its button"
        );
    }
}

#[test]
fn only_an_enabled_button_clicks() {
    for enabled in [true, false] {
        let ctx = context();
        let clicks = Cell::new(0);
        let rect = Cell::new(Rect::NOTHING);
        let mut add = |ui: &mut Ui| {
            let response = ui.add(Button::primary("Stack 299 photos").enabled(enabled));
            rect.set(response.rect);
            clicks.set(clicks.get() + usize::from(response.clicked()));
        };
        frame(&ctx, 0.0, vec![], &mut add);
        click(&ctx, 0.1, rect.get().center(), &mut add);
        assert_eq!(clicks.get(), usize::from(enabled));
    }
}

#[test]
fn a_wide_button_fills_the_row_and_centres_its_label() {
    let ctx = context();
    let mut rect = Rect::NOTHING;
    let output = frame(&ctx, 0.0, vec![], |ui| {
        rect = ui.add(Button::primary("Develop").wide()).rect;
    });
    assert_eq!(rect.width(), 600.0);
    let label = texts(&output)[0].1;
    assert!((label.center().x - rect.center().x).abs() < 2.0);
}

#[test]
fn segments_choose_one_value_and_report_only_real_changes() {
    #[derive(Clone, Copy, Debug, PartialEq)]
    enum Room {
        Photograph,
        Engine,
    }
    let ctx = context();
    let room = Cell::new(Room::Photograph);
    let rect = Cell::new(Rect::NOTHING);
    let changes = Cell::new(0);
    let mut add = |ui: &mut Ui| {
        let mut value = room.get();
        let response = segmented(
            ui,
            "room",
            &mut value,
            &[
                (Room::Photograph, "Photograph"),
                (Room::Engine, "Engine room"),
            ],
        );
        room.set(value);
        rect.set(response.rect);
        changes.set(changes.get() + usize::from(response.changed()));
    };
    let output = frame(&ctx, 0.0, vec![], &mut add);
    assert_eq!(rect.get().height(), SEGMENT_HEIGHT);
    let engine = texts(&output)
        .into_iter()
        .find(|(text, ..)| text == "Engine room")
        .unwrap()
        .1;
    let photograph = texts(&output)
        .into_iter()
        .find(|(text, ..)| text == "Photograph")
        .unwrap()
        .1;
    click(&ctx, 0.1, engine.center(), &mut add);
    assert_eq!((room.get(), changes.get()), (Room::Engine, 1));
    click(&ctx, 0.2, engine.center(), &mut add);
    assert_eq!(
        changes.get(),
        1,
        "choosing the chosen segment changes nothing"
    );
    let output = frame(&ctx, 0.3, vec![], &mut add);
    let underline = output.shapes.iter().any(|shape| {
        matches!(&shape.shape, egui::Shape::Rect(r)
            if r.fill == GRAPHITE.accent && r.rect.height() == 1.5 && r.rect.center().x > photograph.right())
    });
    assert!(underline, "the chosen segment carries the amber rule");
}

#[test]
fn the_toggle_is_26_by_14_with_a_square_knob_that_turns_amber() {
    let ctx = context();
    let on = Cell::new(false);
    let rect = Cell::new(Rect::NOTHING);
    let mut add = |ui: &mut Ui| {
        let mut value = on.get();
        rect.set(toggle(ui, &mut value).rect);
        on.set(value);
    };
    frame(&ctx, 0.0, vec![], &mut add);
    let rect = rect.get();
    assert_eq!(rect.size(), TOGGLE_SIZE);
    click(&ctx, 0.1, rect.center(), &mut add);
    assert!(on.get());
    let output = frame(&ctx, 1.0, vec![], &mut add);
    let knob = output
        .shapes
        .iter()
        .find_map(|shape| match &shape.shape {
            egui::Shape::Rect(r) if r.rect.size() == egui::vec2(8.0, 8.0) => Some(r.clone()),
            _ => None,
        })
        .expect("a square knob");
    assert_eq!(knob.fill, GRAPHITE.accent);
    assert!(
        knob.rect.left() > rect.center().x,
        "on moves the knob right"
    );
}

#[test]
fn the_slider_sets_by_pointer_resets_on_double_click_and_marks_its_default() {
    let ctx = context();
    let value = Cell::new(0.5_f32);
    let rect = Cell::new(Rect::NOTHING);
    let mut add = |ui: &mut Ui| {
        let mut v = value.get();
        rect.set(
            ui.add(
                Slider::new(&mut v, 0.0..=2.0)
                    .default_value(1.0)
                    .width(200.0),
            )
            .rect,
        );
        value.set(v);
    };
    let output = frame(&ctx, 0.0, vec![], &mut add);
    let rect = rect.get();
    assert_eq!(rect.size(), egui::vec2(200.0, SLIDER_HEIGHT));
    let tick = output.shapes.iter().any(|shape| {
        matches!(&shape.shape, egui::Shape::LineSegment { points, stroke }
            if points[0].x == points[1].x && (points[0].x - rect.center().x).abs() <= 1.0
            && stroke.color == GRAPHITE.ink3)
    });
    assert!(tick, "a tick marks the default");
    let at = rect.left_center() + egui::vec2(150.0, 0.0);
    click(&ctx, 0.1, at, &mut add);
    assert!((value.get() - 1.5).abs() < 0.02, "{}", value.get());
    // A separate gesture: a third click inside the double-click window would
    // be a triple click.
    for (offset, pressed) in [(1.0, true), (1.02, false), (1.04, true), (1.06, false)] {
        frame(&ctx, offset, press(at, pressed), &mut add);
    }
    assert_eq!(value.get(), 1.0, "double-click restores the default");
}

#[test]
fn status_marks_are_painted_shapes_in_their_own_colours() {
    let ctx = context();
    for (mark, color, expected) in [
        (Mark::Fine, GRAPHITE.ok, 1),
        (Mark::Look, GRAPHITE.warn, 1),
        (Mark::Failed, GRAPHITE.bad, 1),
        (Mark::NotYet, GRAPHITE.ink3, 1),
        (Mark::Running, GRAPHITE.accent, 2),
        (Mark::Hidden, GRAPHITE.ink3, 0),
    ] {
        let mut slot = Rect::NOTHING;
        let output = frame(&ctx, 0.0, vec![], |ui| slot = super::mark(ui, mark).rect);
        assert_eq!(
            slot.size(),
            egui::vec2(MARK_SLOT, MARK_SLOT),
            "{mark:?} slot"
        );
        let shapes = painted(&output);
        assert!(
            !shapes.iter().any(|s| matches!(s, egui::Shape::Text(_))),
            "{mark:?} must not be a glyph"
        );
        assert_eq!(shapes.len(), expected, "{mark:?}: {shapes:?}");
        for shape in shapes {
            let painted = match shape {
                egui::Shape::Circle(c) if c.fill != Color32::TRANSPARENT => c.fill,
                egui::Shape::Circle(c) => c.stroke.color,
                egui::Shape::Path(p) => p.fill,
                other => panic!("{mark:?} painted {other:?}"),
            };
            assert_eq!(painted, color, "{mark:?}");
        }
        if mark == Mark::Failed {
            let egui::Shape::Path(diamond) = painted(&output)[0] else {
                unreachable!()
            };
            assert_eq!(diamond.points.len(), 4);
            assert_eq!(
                diamond.points[0].x, diamond.points[2].x,
                "a diamond, not a square"
            );
        }
        if mark == Mark::Look {
            let egui::Shape::Path(triangle) = painted(&output)[0] else {
                unreachable!()
            };
            assert_eq!(triangle.points.len(), 3);
        }
    }
}

#[test]
fn chips_keys_caps_and_lifecycle_never_go_below_the_smallest_size() {
    let ctx = context();
    let output = frame(&ctx, 0.0, vec![], |ui| {
        chip(ui, Some(Mark::Fine), "online", false);
        chip(ui, Some(Mark::Look), "2 to check", true);
        key_cap(ui, "Ctrl K");
        caps(ui, "Depth rail");
        lifecycle(
            ui,
            &[
                ("Capture", Step::Done),
                ("Stack", Step::Current),
                ("Develop", Step::Todo),
                ("Export", Step::Look),
            ],
        );
    });
    let found = texts(&output);
    for needle in [
        "online",
        "2 to check",
        "CTRL K",
        "DEPTH RAIL",
        "Capture",
        "Export",
    ] {
        assert!(found.iter().any(|(t, ..)| t == needle), "missing {needle}");
    }
    for (text, _, size) in &found {
        assert!(*size >= 10.5, "{text} at {size} px");
    }
    let marks = output
        .shapes
        .iter()
        .filter(|s| matches!(&s.shape, egui::Shape::Circle(_) | egui::Shape::Path(_)))
        .count();
    assert!(marks >= 6, "every chip and lifecycle step draws its mark");
}

#[test]
fn links_are_neutral_unless_a_check_needs_a_look() {
    let ctx = context();
    for (needs_look, color) in [(false, GRAPHITE.ink2), (true, GRAPHITE.accent)] {
        let output = frame(&ctx, 0.0, vec![], |ui| {
            link(ui, "Show", needs_look);
        });
        let painted = output
            .shapes
            .iter()
            .find_map(|shape| match &shape.shape {
                egui::Shape::Text(text) if text.galley.text() == "SHOW" => {
                    Some(text.fallback_color)
                }
                _ => None,
            })
            .unwrap();
        assert_eq!(painted, color);
    }
}

#[test]
fn a_check_row_reports_its_link_and_the_tab_marks_the_open_one() {
    let ctx = context();
    let clicked = Cell::new(false);
    let mut add = |ui: &mut Ui| {
        let link = check_row(
            ui,
            Mark::Look,
            "Soft spots",
            "1.9 % of the subject has no sharp plane",
            Some("Show"),
        )
        .link_clicked;
        clicked.set(clicked.get() | link);
        ui.horizontal(|ui| {
            ui.set_height(36.0);
            tab(ui, "Checks", true, Some("2"));
            tab(ui, "Recipe", false, None);
        });
    };
    let output = frame(&ctx, 0.0, vec![], &mut add);
    let show = texts(&output)
        .into_iter()
        .find(|(t, ..)| t == "SHOW")
        .unwrap()
        .1;
    click(&ctx, 0.1, show.center(), &mut add);
    assert!(clicked.get());
    let checks = texts(&output)
        .into_iter()
        .find(|(t, ..)| t == "CHECKS")
        .unwrap()
        .1;
    let rule = output.shapes.iter().any(|shape| {
        matches!(&shape.shape, egui::Shape::Rect(r)
            if r.fill == GRAPHITE.accent && r.rect.height() == 2.0
            && r.rect.left() <= checks.left() + 0.5 && r.rect.right() >= checks.right() - 0.5)
    });
    assert!(rule, "the open tab has the amber rule");
}

#[test]
fn the_brand_mark_draws_the_gold_plane_and_the_darkening_planes_inside_its_square() {
    let ctx = context();
    let rect = Rect::from_min_size(egui::pos2(14.0, 12.0), egui::vec2(19.0, 19.0));
    let output = frame(&ctx, 0.0, vec![], |ui| {
        brand_mark(ui.painter(), rect);
    });
    let planes: Vec<_> = output
        .shapes
        .iter()
        .filter_map(|shape| match &shape.shape {
            egui::Shape::Path(path) if path.closed && path.fill != Color32::TRANSPARENT => {
                Some((path.fill, shape.shape.visual_bounding_rect()))
            }
            _ => None,
        })
        .collect();
    assert_eq!(planes.len(), 5);
    assert_eq!(
        planes[0].0, GRAPHITE.accent,
        "the plane in focus is the accent gold"
    );
    for pair in planes.windows(2) {
        assert!(pair[1].0.r() < pair[0].0.r(), "each lower plane is darker");
        assert!(
            pair[1].1.top() > pair[0].1.bottom(),
            "a gap separates the planes"
        );
    }
    assert!((planes[0].1.top() - rect.top()).abs() < 1.0);
    assert!((planes[4].1.bottom() - rect.bottom()).abs() < 1.0);
    for shape in painted(&output) {
        assert!(rect.expand(1.0).contains_rect(shape.visual_bounding_rect()));
    }
}
