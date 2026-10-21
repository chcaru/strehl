//! A small coherent line vocabulary. All icons share a 20-point drawing grid;
//! axis-aligned rules are snapped to physical pixel centres at each UI scale.
use eframe::egui::{self, Color32, Painter, Pos2, Stroke};

#[derive(Clone, Copy)]
pub(crate) enum Icon {
    Projects,
    Folder,
    Stack,
    Photograph,
    Adjust,
    Review,
    Activity,
    Edit,
    Export,
    Agent,
    Layout,
    Add,
    Check,
    Close,
    Right,
    Down,
}

pub(crate) fn paint(painter: &Painter, center: Pos2, size: f32, icon: Icon, color: Color32) {
    let pixels = painter.ctx().pixels_per_point();
    let width = ((size / 20.0) * pixels).round().max(1.0) / pixels;
    let stroke = Stroke::new(width, color);
    let scale = size / 20.0;
    let snap = |value: f32| {
        ((value * pixels - width * pixels * 0.5).round() + width * pixels * 0.5) / pixels
    };
    let point = |x, y| Pos2::new(snap(center.x + x * scale), snap(center.y + y * scale));
    let line = |points: &[[f32; 2]]| {
        painter.add(egui::Shape::line(
            points.iter().map(|&[x, y]| point(x, y)).collect(),
            stroke,
        ));
    };
    let closed = |points: &[[f32; 2]]| {
        painter.add(egui::Shape::closed_line(
            points.iter().map(|&[x, y]| point(x, y)).collect(),
            stroke,
        ));
    };
    match icon {
        Icon::Projects | Icon::Folder => {
            // A complete folder silhouette, with an offset second folder for
            // the Projects collection. No stray diagonal "tab" stroke.
            if matches!(icon, Icon::Projects) {
                line(&[[-5.0, -8.0], [-1.0, -8.0], [1.0, -6.0], [7.0, -6.0]]);
            }
            closed(&[
                [-8.0, -5.0],
                [-3.0, -5.0],
                [-1.0, -2.0],
                [8.0, -2.0],
                [8.0, 7.0],
                [-8.0, 7.0],
            ]);
            line(&[[-8.0, 0.0], [8.0, 0.0]]);
        }
        Icon::Stack => {
            closed(&[[0.0, -8.0], [9.0, -3.0], [0.0, 2.0], [-9.0, -3.0]]);
            line(&[[-9.0, 1.0], [0.0, 6.0], [9.0, 1.0]]);
            line(&[[-9.0, 5.0], [0.0, 10.0], [9.0, 5.0]]);
        }
        Icon::Photograph => {
            closed(&[[-8.0, -7.0], [8.0, -7.0], [8.0, 7.0], [-8.0, 7.0]]);
            line(&[[-7.0, 5.0], [-2.0, 0.0], [1.0, 3.0], [4.0, 0.0], [7.0, 3.0]]);
            painter.circle_filled(point(3.0, -3.0), width, color);
        }
        Icon::Adjust => {
            for (x, y) in [(-6.0, -3.0), (0.0, 4.0), (6.0, -3.0)] {
                line(&[[x, -8.0], [x, y - 2.0]]);
                line(&[[x, y + 2.0], [x, 8.0]]);
                closed(&[
                    [x - 2.0, y - 2.0],
                    [x + 2.0, y - 2.0],
                    [x + 2.0, y + 2.0],
                    [x - 2.0, y + 2.0],
                ]);
            }
        }
        Icon::Review => {
            painter.circle_stroke(center, 8.0 * scale, stroke);
            line(&[[-4.0, 0.0], [-1.0, 3.0], [5.0, -4.0]]);
        }
        Icon::Activity => {
            for (y, end) in [(-6.0, 8.0), (0.0, 5.0), (6.0, 8.0)] {
                line(&[[-8.0, y], [-6.0, y]]);
                line(&[[-2.0, y], [end, y]]);
            }
        }
        Icon::Edit => {
            line(&[[-8.0, -7.0], [-8.0, 7.0], [6.0, 7.0]]);
            closed(&[
                [-3.0, 3.0],
                [-2.0, -1.0],
                [5.0, -8.0],
                [8.0, -5.0],
                [1.0, 2.0],
            ]);
            line(&[[3.0, -6.0], [6.0, -3.0]]);
        }
        Icon::Agent => {
            painter.circle_stroke(point(-5.0, -4.0), 3.0 * scale, stroke);
            painter.circle_stroke(point(5.0, 4.0), 3.0 * scale, stroke);
            line(&[[-2.0, -4.0], [5.0, -4.0], [5.0, 1.0]]);
            line(&[[2.0, 4.0], [-5.0, 4.0], [-5.0, -1.0]]);
        }
        Icon::Export => {
            line(&[[-8.0, 1.0], [-8.0, 8.0], [8.0, 8.0], [8.0, 1.0]]);
            line(&[[0.0, 4.0], [0.0, -8.0]]);
            line(&[[-4.0, -4.0], [0.0, -8.0], [4.0, -4.0]]);
        }
        Icon::Layout => {
            closed(&[[-8.0, -7.0], [8.0, -7.0], [8.0, 7.0], [-8.0, 7.0]]);
            line(&[[-2.0, -7.0], [-2.0, 7.0]]);
            line(&[[-2.0, 2.0], [8.0, 2.0]]);
        }
        Icon::Add => {
            line(&[[-6.0, 0.0], [6.0, 0.0]]);
            line(&[[0.0, -6.0], [0.0, 6.0]]);
        }
        Icon::Check => line(&[[-6.0, 0.0], [-2.0, 4.0], [6.0, -5.0]]),
        Icon::Close => {
            line(&[[-5.0, -5.0], [5.0, 5.0]]);
            line(&[[-5.0, 5.0], [5.0, -5.0]]);
        }
        Icon::Right => line(&[[-3.0, -5.0], [2.0, 0.0], [-3.0, 5.0]]),
        Icon::Down => line(&[[-5.0, -3.0], [0.0, 2.0], [5.0, -3.0]]),
    }
}
