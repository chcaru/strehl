//! The before/after split line, dragged through the shell (owner feedback,
//! 2026-11-22: "for the before/after split mode, i would like to be able to
//! drag that line"). The press lands anywhere along the line, not only on a
//! grip at its middle; the photograph does not pan; the line stays where it
//! was put while the view zooms and pans; it stops short of the edges.
use super::*;

/// Develop with Split on and the photograph painted.
fn split_view(dir: &Path, ctx: &egui::Context, time: &mut f64) -> StrehlApp {
    let mut app = app(dir);
    // A finished render, so the canvas shows the photograph and maps it.
    app.progress.mark_complete();
    app.result_viewer.texture = Some(ctx.load_texture(
        "split-final",
        egui::ColorImage::filled([96, 64], egui::Color32::from_rgb(40, 90, 110)),
        egui::TextureOptions::LINEAR,
    ));
    app.result_viewer.source_size = [96, 64];
    app.go_station(Station::Develop);
    app.editor.develop.compare = station::Compare::Split;
    for _ in 0..4 {
        *time += 0.05;
        frame(&mut app, ctx, *time, vec![]);
    }
    app
}

/// The photograph's screen rectangle and the part of it on screen.
fn visible(app: &StrehlApp) -> (egui::Rect, egui::Rect) {
    let (image, clip) = app
        .process_space
        .edit_mapping()
        .expect("the photograph is mapped");
    (image, image.intersect(clip))
}

/// The line's x on screen, as the canvas draws it.
fn line_x(app: &StrehlApp) -> f32 {
    let (image, clip) = app.process_space.edit_mapping().unwrap();
    app.editor
        .develop
        .split_x(image, clip)
        .expect("Split is on")
}

/// Press at `from`, move in `steps` to `to`, release; one frame each.
fn drag(
    app: &mut StrehlApp,
    ctx: &egui::Context,
    time: &mut f64,
    from: egui::Pos2,
    to: egui::Pos2,
) {
    *time += 1.0 / 60.0;
    frame(
        app,
        ctx,
        *time,
        vec![
            egui::Event::PointerMoved(from),
            egui::Event::PointerButton {
                pos: from,
                button: egui::PointerButton::Primary,
                pressed: true,
                modifiers: Default::default(),
            },
        ],
    );
    for step in 1..=8 {
        *time += 1.0 / 60.0;
        let at = from.lerp(to, step as f32 / 8.0);
        frame(app, ctx, *time, vec![egui::Event::PointerMoved(at)]);
    }
    *time += 1.0 / 60.0;
    frame(
        app,
        ctx,
        *time,
        vec![egui::Event::PointerButton {
            pos: to,
            button: egui::PointerButton::Primary,
            pressed: false,
            modifiers: Default::default(),
        }],
    );
    for _ in 0..2 {
        *time += 1.0 / 60.0;
        frame(app, ctx, *time, vec![]);
    }
}

#[test]
fn the_line_drags_from_anywhere_along_it_without_panning() {
    let dir = tempfile::tempdir().unwrap();
    let ctx = context();
    let mut time = 0.0;
    let mut app = split_view(dir.path(), &ctx, &mut time);
    let (image, shown) = visible(&app);
    let x = line_x(&app);
    assert!((x - shown.center().x).abs() < 1.0, "starts in the middle");
    // Near the top of the line, far from the middle of the photograph, and a
    // few points beside the hairline itself.
    let from = egui::pos2(x + 4.0, shown.top() + shown.height() * 0.12);
    let to = egui::pos2(shown.left() + shown.width() * 0.25, from.y + 30.0);
    drag(&mut app, &ctx, &mut time, from, to);
    let (after, _) = visible(&app);
    assert_eq!(after, image, "the photograph panned instead");
    let moved = line_x(&app);
    assert!(
        (moved - (to.x - 4.0)).abs() < 1.5,
        "the line is at {moved}, the pointer left it at {}",
        to.x - 4.0
    );
    // The press keeps the offset it began with: no jump on press.
    assert!((app.editor.develop.split - 0.25).abs() < 0.01);
    // Releasing leaves the photograph to panning again.
    assert!(!app.editor.develop.owns_pointer());
}

#[test]
fn the_line_stops_short_of_the_edges() {
    let dir = tempfile::tempdir().unwrap();
    let ctx = context();
    let mut time = 0.0;
    let mut app = split_view(dir.path(), &ctx, &mut time);
    let (_, shown) = visible(&app);
    let x = line_x(&app);
    let y = shown.center().y;
    drag(
        &mut app,
        &ctx,
        &mut time,
        egui::pos2(x, y),
        egui::pos2(shown.right() + 400.0, y),
    );
    let right = line_x(&app);
    assert!(
        right < shown.right() - 4.0 && right > shown.right() - 16.0,
        "{right}"
    );
    drag(
        &mut app,
        &ctx,
        &mut time,
        egui::pos2(right, y),
        egui::pos2(shown.left() - 400.0, y),
    );
    let left = line_x(&app);
    assert!(
        left > shown.left() + 4.0 && left < shown.left() + 16.0,
        "{left}"
    );
}

#[test]
fn the_line_keeps_its_place_while_the_view_zooms_and_pans() {
    let dir = tempfile::tempdir().unwrap();
    let ctx = context();
    let mut time = 0.0;
    let mut app = split_view(dir.path(), &ctx, &mut time);
    app.editor.develop.split = 0.3;
    time += 0.05;
    frame(&mut app, &ctx, time, vec![]);
    let at_fit = line_x(&app);
    let (fitted, _) = visible(&app);
    // Zoom to 4x about a point right of the centre: the photograph grows
    // and moves; the line stays where it is on screen.
    app.process_space.set_photo_view([0.7, 0.4], 4.0);
    for _ in 0..30 {
        time += 0.05;
        frame(&mut app, &ctx, time, vec![]);
    }
    let (zoomed, shown) = visible(&app);
    assert!(zoomed.width() > fitted.width() * 3.0, "{zoomed:?}");
    assert!((line_x(&app) - at_fit).abs() < 1.0);
    assert!(shown.contains(egui::pos2(line_x(&app), shown.center().y)));
    // Drag it while zoomed: the photograph still does not pan.
    let y = shown.top() + 20.0;
    drag(
        &mut app,
        &ctx,
        &mut time,
        egui::pos2(at_fit, y),
        egui::pos2(at_fit + 100.0, y),
    );
    assert_eq!(visible(&app).0, zoomed, "the photograph panned instead");
    assert!((line_x(&app) - (at_fit + 100.0)).abs() < 1.5);
    // A new photograph (another render) keeps the split for the session.
    let split = app.editor.develop.split;
    app.editor.develop.reset_document();
    assert_eq!(app.editor.develop.split, split);
}

#[test]
fn away_from_the_line_the_photograph_still_pans() {
    let dir = tempfile::tempdir().unwrap();
    let ctx = context();
    let mut time = 0.0;
    let mut app = split_view(dir.path(), &ctx, &mut time);
    app.process_space.set_photo_view([0.5, 0.5], 4.0);
    for _ in 0..30 {
        time += 0.05;
        frame(&mut app, &ctx, time, vec![]);
    }
    let (zoomed, shown) = visible(&app);
    let split = app.editor.develop.split;
    let from = egui::pos2(shown.left() + shown.width() * 0.8, shown.center().y);
    drag(
        &mut app,
        &ctx,
        &mut time,
        from,
        from - egui::vec2(120.0, 0.0),
    );
    assert_eq!(app.editor.develop.split, split, "the line moved");
    assert_ne!(visible(&app).0, zoomed, "the photograph did not pan");
}
