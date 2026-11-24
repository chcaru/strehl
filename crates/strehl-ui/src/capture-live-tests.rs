use super::*;
use crate::capture_aids::Peaking;
use eframe::egui::ColorImage;
use serde_json::json;
use std::time::Instant;

const SCREEN: Vec2 = Vec2::new(1332.0, 811.0);

fn state(generation: u64, roi: Roi, position: u16) -> serde_json::Value {
    json!({"camera_revision":1,"plan_revision":1,"sequence_id":1,"phase":"ready","connected":true,
        "editable":true,"busy":false,"position":position,
        "roi":{"x":roi.x,"y":roi.y,"width":roi.width,"height":roi.height},
        "preview":{"available":true,"fresh":true,"generation":generation,"age_seconds":0.2},
        "magnifier_ratios":[0,59,117],"magnifier_current":0,
        "exposure":{"iso":100,"shutter":65544,"f_number":560}})
}

fn snapshot_of(image: ColorImage, generation: u64, roi: Roi, position: u16) -> Snapshot {
    let image = Arc::new(image);
    let mut s = Snapshot {
        online: true,
        observed: Some(Instant::now()),
        preview: Some((generation, image.clone())),
        peaking: Some((generation, Arc::new(Peaking::analyze(&image)))),
        levels: Some((generation, Arc::new(PreviewLevels::analyze(&image)))),
        ..Default::default()
    };
    s.set_state(state(generation, roi, position));
    s
}

fn snapshot(generation: u64) -> Snapshot {
    let mut image = ColorImage::filled([120, 80], Color32::from_gray(100));
    image.pixels[0] = Color32::WHITE;
    snapshot_of(
        image,
        generation,
        Roi {
            x: 0.1,
            y: 0.1,
            width: 0.8,
            height: 0.8,
        },
        30_000,
    )
}

fn frame(
    ctx: &egui::Context,
    view: &mut LiveView,
    s: &Snapshot,
    time: f64,
    events: Vec<egui::Event>,
) -> (egui::FullOutput, Vec<LiveIntent>) {
    let palette = CapturePalette::default();
    let mut intents = Vec::new();
    let out = ctx.run(
        egui::RawInput {
            screen_rect: Some(Rect::from_min_size(egui::Pos2::ZERO, SCREEN)),
            time: Some(time),
            events,
            ..Default::default()
        },
        |ctx| {
            egui::CentralPanel::default()
                .frame(egui::Frame::NONE)
                .show(ctx, |ui| intents = view.show(ui, s, &palette));
        },
    );
    (out, intents)
}

fn texts(out: &egui::FullOutput) -> Vec<String> {
    out.shapes
        .iter()
        .filter_map(|s| match &s.shape {
            Shape::Text(t) => Some(t.galley.text().to_owned()),
            _ => None,
        })
        .collect()
}

fn button(pos: Pos2, pressed: bool) -> egui::Event {
    egui::Event::PointerButton {
        pos,
        button: egui::PointerButton::Primary,
        pressed,
        modifiers: Default::default(),
    }
}

/// A press at `from`, a move past the drag threshold, a move to `to` and
/// the release: the intents it gave.
fn drag(
    ctx: &egui::Context,
    view: &mut LiveView,
    s: &Snapshot,
    time: &mut f64,
    from: Pos2,
    to: Pos2,
) -> Vec<LiveIntent> {
    let nudge = from + (to - from).normalized() * 12.0;
    let mut all = Vec::new();
    for events in [
        vec![egui::Event::PointerMoved(from), button(from, true)],
        vec![egui::Event::PointerMoved(nudge)],
        vec![egui::Event::PointerMoved(to)],
        vec![button(to, false)],
    ] {
        *time += 0.05;
        all.extend(frame(ctx, view, s, *time, events).1);
    }
    all
}

fn photo() -> Rect {
    photo_rect(Rect::from_min_size(egui::Pos2::ZERO, SCREEN), 1.5)
}

/// The box of `roi` on the screen.
fn on_screen(roi: Roi) -> Rect {
    let p = photo();
    Rect::from_min_size(
        p.lerp_inside(egui::vec2(roi.x, roi.y)),
        egui::vec2(roi.width * p.width(), roi.height * p.height()),
    )
}

/// Textures are uploaded when the preview changes, never on pointer
/// motion; the estimate panel says what it is.
#[test]
fn uploads_follow_the_preview_not_the_pointer() {
    let ctx = egui::Context::default();
    let mut view = LiveView::default();
    let s = snapshot(1);
    let (out, _) = frame(&ctx, &mut view, &s, 0.0, vec![]);
    assert_eq!(view.uploads, 3, "picture, peaking and clipping");
    let builds = view.mesh_builds;
    assert_eq!(builds, 2, "the histogram and the focus trace");
    for i in 0..5 {
        frame(
            &ctx,
            &mut view,
            &s,
            0.1 * (i + 1) as f64,
            vec![egui::Event::PointerMoved(egui::pos2(
                300.0 + 50.0 * i as f32,
                300.0,
            ))],
        );
    }
    assert_eq!(view.uploads, 3);
    assert_eq!(view.mesh_builds, builds, "no mesh on pointer motion");
    frame(&ctx, &mut view, &snapshot(2), 1.0, vec![]);
    assert_eq!(view.uploads, 6);
    assert_eq!(view.mesh_builds, builds + 2, "once per new preview");
    let texts = texts(&out);
    for want in [
        "estimate, not the RAW",
        "ISO 100",
        "1/8 s",
        "f/5.6",
        "LIVE VIEW",
        "0.0 % clipped",
        "0 % black",
        "FOCUS · SUBJECT BOX",
    ] {
        assert!(texts.iter().any(|t| t == want), "{want}: {texts:?}");
    }
}

/// Dragging outside the box draws a new subject box.
#[test]
fn dragging_outside_draws_a_subject_box() {
    let ctx = egui::Context::default();
    let mut view = LiveView::default();
    let s = snapshot_of(
        ColorImage::filled([120, 80], Color32::from_gray(100)),
        1,
        Roi {
            x: 0.6,
            y: 0.6,
            width: 0.3,
            height: 0.3,
        },
        30_000,
    );
    let mut time = 0.0;
    frame(&ctx, &mut view, &s, time, vec![]);
    let a = photo().lerp_inside(egui::vec2(0.25, 0.25));
    let b = photo().lerp_inside(egui::vec2(0.5, 0.45));
    match drag(&ctx, &mut view, &s, &mut time, a, b).as_slice() {
        [LiveIntent::SetRoi(roi)] => {
            assert!(
                (roi.x - 0.25).abs() < 0.01 && (roi.y - 0.25).abs() < 0.01,
                "{roi:?}"
            );
            assert!(
                (roi.width - 0.25).abs() < 0.01 && (roi.height - 0.2).abs() < 0.01,
                "{roi:?}"
            );
        }
        other => panic!("{other:?}"),
    }
}

/// Corners take precedence, then edge midpoints, then the edges, then the
/// inside; a little outside a handle still takes it.
#[test]
fn handles_are_hit_before_the_inside() {
    let r = Rect::from_min_max(egui::pos2(100.0, 100.0), egui::pos2(400.0, 300.0));
    assert_eq!(
        box_hit(r, egui::pos2(103.0, 98.0)),
        BoxHit::Handle(Handle::NorthWest)
    );
    assert_eq!(
        box_hit(r, egui::pos2(407.0, 306.0)),
        BoxHit::Handle(Handle::SouthEast)
    );
    assert_eq!(
        box_hit(r, egui::pos2(250.0, 95.0)),
        BoxHit::Handle(Handle::North)
    );
    assert_eq!(
        box_hit(r, egui::pos2(402.0, 200.0)),
        BoxHit::Handle(Handle::East)
    );
    assert_eq!(
        box_hit(r, egui::pos2(160.0, 302.0)),
        BoxHit::Handle(Handle::South),
        "along the edge"
    );
    assert_eq!(
        box_hit(r, egui::pos2(97.0, 230.0)),
        BoxHit::Handle(Handle::West)
    );
    assert_eq!(box_hit(r, egui::pos2(200.0, 200.0)), BoxHit::Inside);
    assert_eq!(box_hit(r, egui::pos2(60.0, 200.0)), BoxHit::Outside);
    assert_eq!(box_hit(r, egui::pos2(250.0, 320.0)), BoxHit::Outside);
    for (h, cursor) in [
        (Handle::North, CursorIcon::ResizeVertical),
        (Handle::West, CursorIcon::ResizeHorizontal),
        (Handle::NorthWest, CursorIcon::ResizeNwSe),
        (Handle::SouthWest, CursorIcon::ResizeNeSw),
    ] {
        assert_eq!(h.cursor(), cursor);
    }
}

/// A handle moves only its sides, within the picture, never below the
/// smallest box and never inside out; a move keeps the size.
#[test]
fn resizing_and_moving_stay_inside_the_picture() {
    let from = Rect::from_min_max(egui::pos2(0.2, 0.3), egui::pos2(0.6, 0.7));
    let close = |a: Rect, b: Rect| (a.min - b.min).length() + (a.max - b.max).length() < 1e-5;
    let r = resized(from, Handle::East, egui::vec2(0.1, 0.4), MIN_BOX);
    assert!(
        close(
            r,
            Rect::from_min_max(egui::pos2(0.2, 0.3), egui::pos2(0.7, 0.7))
        ),
        "{r:?}"
    );
    let r = resized(from, Handle::North, egui::vec2(0.3, -0.1), MIN_BOX);
    assert!((r.top() - 0.2).abs() < 1e-6 && r.left() == 0.2 && r.right() == 0.6);
    let r = resized(from, Handle::SouthWest, egui::vec2(-0.5, 0.5), MIN_BOX);
    assert!(
        close(
            r,
            Rect::from_min_max(egui::pos2(0.0, 0.3), egui::pos2(0.6, 1.0))
        ),
        "{r:?}"
    );
    // Past the opposite side: held at the smallest box.
    let r = resized(from, Handle::West, egui::vec2(0.9, 0.0), MIN_BOX);
    assert!(
        (r.width() - MIN_BOX).abs() < 1e-6 && r.right() == 0.6,
        "{r:?}"
    );
    let r = resized(from, Handle::NorthEast, egui::vec2(-0.9, 0.9), MIN_BOX);
    assert!((r.width() - MIN_BOX).abs() < 1e-6 && (r.height() - MIN_BOX).abs() < 1e-6);
    assert_eq!((r.left(), r.bottom()), (0.2, 0.7));
    let m = moved(from, egui::vec2(0.9, -0.9));
    assert!((m.right() - 1.0).abs() < 1e-6 && m.top() == 0.0);
    assert!((m.width() - from.width()).abs() < 1e-6 && (m.height() - from.height()).abs() < 1e-6);
}

/// Dragging the east handle widens the box, dragging inside moves it, and
/// the box sent is shown until the host reports it.
#[test]
fn handles_resize_and_the_inside_moves() {
    let ctx = egui::Context::default();
    let mut view = LiveView::default();
    let roi = Roi {
        x: 0.2,
        y: 0.3,
        width: 0.4,
        height: 0.4,
    };
    let s = snapshot_of(
        ColorImage::filled([120, 80], Color32::from_gray(100)),
        1,
        roi,
        30_000,
    );
    let mut time = 0.0;
    frame(&ctx, &mut view, &s, time, vec![]);
    let r = on_screen(roi);
    let east = Handle::East.at(r);
    let to = east + egui::vec2(0.1 * photo().width(), 40.0);
    match drag(&ctx, &mut view, &s, &mut time, east, to).as_slice() {
        [LiveIntent::SetRoi(next)] => {
            assert!((next.width - 0.5).abs() < 0.002, "{next:?}");
            assert!((next.x - roi.x).abs() < 1e-5 && (next.y - roi.y).abs() < 1e-5);
            assert!((next.height - roi.height).abs() < 1e-5, "{next:?}");
        }
        other => panic!("{other:?}"),
    }
    // Until the host has it, the box drawn is the one sent: its east handle
    // is where the drag ended.
    time += 0.05;
    let (out, _) = frame(
        &ctx,
        &mut view,
        &s,
        time,
        vec![egui::Event::PointerMoved(egui::pos2(to.x, east.y))],
    );
    assert_eq!(
        out.platform_output.cursor_icon,
        CursorIcon::ResizeHorizontal
    );
    let sent = match view.sent {
        Some((r, _)) => r,
        None => panic!("the sent box is kept"),
    };
    // The host reports the new box; moving it inside keeps its size.
    let s = snapshot_of(
        ColorImage::filled([120, 80], Color32::from_gray(100)),
        2,
        sent,
        30_000,
    );
    time += 0.05;
    frame(&ctx, &mut view, &s, time, vec![]);
    assert!(view.sent.is_none());
    let inside = on_screen(sent).center();
    let to = inside + egui::vec2(-0.1 * photo().width(), -0.1 * photo().height());
    match drag(&ctx, &mut view, &s, &mut time, inside, to).as_slice() {
        [LiveIntent::SetRoi(next)] => {
            assert!((next.x - (sent.x - 0.1)).abs() < 0.002, "{next:?}");
            assert!((next.y - (sent.y - 0.1)).abs() < 0.002, "{next:?}");
            assert!((next.width - sent.width).abs() < 1e-5);
            assert!((next.height - sent.height).abs() < 1e-5);
        }
        other => panic!("{other:?}"),
    }
}

/// Over a handle the pointer shows its resize; inside, a hand; outside, a
/// cross. Nothing changes the box while the camera cannot take it.
#[test]
fn the_cursor_names_what_a_drag_will_do() {
    let ctx = egui::Context::default();
    let mut view = LiveView::default();
    let s = snapshot(1);
    let roi = s.host.roi.unwrap();
    let r = on_screen(roi);
    let mut time = 0.0;
    frame(&ctx, &mut view, &s, time, vec![]);
    for (at, want) in [
        (Handle::NorthEast.at(r), CursorIcon::ResizeNeSw),
        (Handle::South.at(r), CursorIcon::ResizeVertical),
        (r.center(), CursorIcon::Grab),
        (
            photo().left_top() + egui::vec2(10.0, 50.0),
            CursorIcon::Crosshair,
        ),
    ] {
        time += 0.05;
        let (out, _) = frame(
            &ctx,
            &mut view,
            &s,
            time,
            vec![egui::Event::PointerMoved(at)],
        );
        assert_eq!(out.platform_output.cursor_icon, want, "{at:?}");
    }
    let mut locked = snapshot(1);
    locked.pending = true;
    let mut time = 10.0;
    let corner = Handle::SouthEast.at(r);
    let all = drag(
        &ctx,
        &mut view,
        &locked,
        &mut time,
        corner,
        corner + egui::vec2(-80.0, -60.0),
    );
    assert!(all.is_empty(), "{all:?}");
}

/// The focus trace takes one reading a preview, restarts when the box
/// changes, names the sharpest lens position and the share of the best.
#[test]
fn the_focus_trace_follows_the_previews() {
    let fixture = |sharp: f32| crate::capture_workspace::fixture::subject_image(240, 160, sharp);
    let roi = Roi {
        x: 0.2,
        y: 0.2,
        width: 0.6,
        height: 0.6,
    };
    let mut trace = FocusTrace::default();
    let mut values = Vec::new();
    for (i, (sharp, lens)) in [(0.2, 100u16), (0.6, 104), (1.0, 108), (0.5, 112)]
        .into_iter()
        .enumerate()
    {
        let s = snapshot_of(fixture(sharp), i as u64 + 1, roi, lens);
        assert!(trace.observe(&s, roi, i as f64 * 0.2));
        assert!(
            !trace.observe(&s, roi, i as f64 * 0.2 + 0.1),
            "once a preview"
        );
        values.push(trace.latest().unwrap().value);
    }
    assert!(
        values[0] < values[1] && values[1] < values[2] && values[3] < values[2],
        "{values:?}"
    );
    assert_eq!(trace.best().unwrap().lens, Some(108));
    let share = trace.share_of_best().unwrap();
    assert!((share - values[3] / values[2]).abs() < 1e-6);
    assert!(
        (trace.rate(0.6).unwrap() - 5.0).abs() < 1e-3,
        "four previews in 0.6 s"
    );
    assert_eq!(trace.rate(10.0), None, "stale");
    // Another box: the readings are not comparable, the trace restarts.
    let other = Roi { x: 0.1, ..roi };
    let s = snapshot_of(fixture(1.0), 4, other, 112);
    assert!(trace.observe(&s, other, 0.8));
    assert_eq!(trace.samples().len(), 1);
    for i in 0..60 {
        let s = snapshot_of(fixture(1.0), 100 + i, other, 112);
        trace.observe(&s, other, 1.0 + i as f64);
    }
    assert_eq!(trace.samples().len(), TRACE_LEN, "bounded");
}

/// The histogram is antialiased (feathered strokes fade to transparent at
/// their edges) and drawn as filled triangles, not one-pixel bars; the end
/// zones show where the black and clipped codes are.
#[test]
fn the_histogram_is_antialiased() {
    let mut image = ColorImage::filled([200, 100], Color32::from_gray(90));
    for (i, p) in image.pixels.iter_mut().enumerate() {
        let v = (i % 200) as u8;
        *p = Color32::from_rgb(v, v / 2 + 40, 255 - v);
    }
    let levels = PreviewLevels::analyze(&image);
    let rect = Rect::from_min_size(egui::pos2(10.0, 10.0), egui::vec2(276.0, 48.0));
    let palette = CapturePalette::default();
    let mesh = histogram_mesh(&levels, rect, 1.0, &palette);
    let faded = mesh.vertices.iter().filter(|v| v.color.a() == 0).count();
    assert!(faded > 600, "feathered outer edges of four curves: {faded}");
    let bounds = mesh.calc_bounds();
    assert!(rect.expand(1.5).contains_rect(bounds), "{bounds:?}");
    // The clipped zone is strong when something clips.
    let has = |mesh: &Mesh, color: Color32| mesh.vertices.iter().any(|v| v.color == color);
    let (strong, faint) = (
        palette.warn.gamma_multiply(0.75),
        palette.warn.gamma_multiply(0.22),
    );
    assert!(levels.clipped_share > 0.0);
    assert!(has(&mesh, strong) && !has(&mesh, faint));
    let quiet = histogram_mesh(
        &PreviewLevels::analyze(&ColorImage::filled([20, 20], Color32::from_gray(90))),
        rect,
        1.0,
        &palette,
    );
    assert!(has(&quiet, faint) && !has(&quiet, strong));
}

/// A curve is drawn only where it holds counts (and down to zero either
/// side), so empty codes leave the baseline alone; smoothing keeps counts.
#[test]
fn curves_are_drawn_where_they_hold_counts() {
    let mut h = [0u32; 256];
    h[10] = 100;
    h[200] = 50;
    h[201] = 50;
    let values = heights(&h, 100.0);
    let points: Vec<Pos2> = (0..256).map(|i| egui::pos2(i as f32, -values[i])).collect();
    let r = runs(&points, &values);
    assert_eq!(r.len(), 2, "{r:?}");
    assert_eq!((r[0][0].x, r[0][r[0].len() - 1].x), (7.0, 13.0));
    assert_eq!((r[1][0].x, r[1][r[1].len() - 1].x), (197.0, 204.0));
    let kept: f32 = values.iter().map(|v| v.powi(2) * 100.0).sum();
    assert!(
        (kept - 200.0).abs() < 1e-3,
        "smoothing keeps the counts: {kept}"
    );
}

#[test]
fn the_preview_fits_its_canvas() {
    let canvas = Rect::from_min_size(egui::pos2(0.0, 80.0), egui::vec2(1332.0, 811.0));
    let r = photo_rect(canvas, 1.5);
    assert!((r.height() - 773.0).abs() < 0.5, "the mockup's 1160 x 773");
    assert!((r.width() - 1159.5).abs() < 1.0);
}

/// A click: press and release at one place, apart in time from the last.
fn click_at(
    ctx: &egui::Context,
    view: &mut LiveView,
    s: &Snapshot,
    time: &mut f64,
    at: Pos2,
    secondary: bool,
) -> Vec<LiveIntent> {
    let press = |pressed| egui::Event::PointerButton {
        pos: at,
        button: if secondary {
            egui::PointerButton::Secondary
        } else {
            egui::PointerButton::Primary
        },
        pressed,
        modifiers: Default::default(),
    };
    let mut all = Vec::new();
    // Far enough apart that two clicks are never a double click.
    *time += 1.0;
    for events in [
        vec![egui::Event::PointerMoved(at), press(true)],
        vec![press(false)],
    ] {
        *time += 0.05;
        all.extend(frame(ctx, view, s, *time, events).1);
    }
    all
}

/// Plan S3: in outline mode, points placed and the first clicked again
/// send that ring as the subject; once the host holds it, a right-click on
/// a point removes it (a triangle stays a valid outline), and clicking an
/// edge adds one.
#[test]
fn an_outline_is_placed_point_by_point_and_edited() {
    let ctx = egui::Context::default();
    let mut view = LiveView {
        outline: true,
        ..LiveView::default()
    };
    let mut s = snapshot(1);
    let mut time = 0.0;
    frame(&ctx, &mut view, &s, time, vec![]);
    let at = |x: f32, y: f32| photo().lerp_inside(egui::vec2(x, y));
    let corners = [(0.3, 0.2), (0.7, 0.25), (0.65, 0.8), (0.35, 0.7)];
    for (x, y) in corners {
        assert!(click_at(&ctx, &mut view, &s, &mut time, at(x, y), false).is_empty());
    }
    let sent = click_at(&ctx, &mut view, &s, &mut time, at(0.3, 0.2), false);
    let subject = match sent.as_slice() {
        [LiveIntent::SetSubject(Some(subject))] => subject.clone(),
        other => panic!("{other:?}"),
    };
    assert_eq!(subject.rings.len(), 1);
    assert_eq!(subject.rings[0].len(), 4);
    for ([x, y], (ex, ey)) in subject.rings[0].iter().zip(corners) {
        assert!((x - ex).abs() < 0.01 && (y - ey).abs() < 0.01, "{x},{y}");
    }
    assert_eq!(subject.provenance["kind"], "manual");
    // The host reports it.
    let mut state = s.state.clone();
    let mut plan = serde_json::to_value(strehl_capture::model::Plan::default()).unwrap();
    plan["subject"] = serde_json::to_value(&subject).unwrap();
    state["plan"] = plan;
    s.set_state(state);
    frame(&ctx, &mut view, &s, time + 2.0, vec![]);
    let removed = click_at(&ctx, &mut view, &s, &mut time, at(0.35, 0.7), true);
    match removed.as_slice() {
        [LiveIntent::SetSubject(Some(next))] => assert_eq!(next.rings[0].len(), 3),
        other => panic!("{other:?}"),
    }
    // Mid-edge of the first side: a point is added there.
    let added = click_at(&ctx, &mut view, &s, &mut time, at(0.5, 0.225), false);
    match added.as_slice() {
        [LiveIntent::SetSubject(Some(next))] => assert_eq!(next.rings[0].len(), 4),
        other => panic!("{other:?}"),
    }
}
