//! Canvas-owned geometry gestures. Drafts never mutate the saved recipe.
use super::*;
use egui::{Color32, CursorIcon, Key, Pos2, Rect, Sense, Shape, Stroke, Vec2};

#[derive(Clone, Copy)]
enum Control {
    Move,
    Resize([i8; 2]),
    Vertex(usize),
}

enum Gesture {
    Create {
        tool: DrawingTool,
        start: [f32; 2],
        points: Vec<[f32; 2]>,
    },
    Transform {
        id: String,
        original: RegionShape,
        draft: RegionShape,
        control: Control,
        start: [f32; 2],
        revision: u64,
    },
}

#[derive(Default)]
pub(super) struct RegionInteraction {
    gesture: Option<Gesture>,
    vertex: Option<(String, usize)>,
    tool: DrawingTool,
    cancelled_press: bool,
    text_focus: Option<egui::Id>,
    navigation_press: bool,
    ownership_frame: Option<u64>,
    owns_pointer: bool,
}

impl EditorState {
    pub(super) fn text_owns_geometry_input(&self, ctx: &egui::Context) -> bool {
        text_editor_focused(ctx)
            || self
                .region_interaction
                .text_focus
                .is_some_and(|id| ctx.memory(|m| m.had_focus_last_frame(id)))
    }
    pub fn set_tool(&mut self, tool: DrawingTool) {
        if self.tool != tool {
            self.cancel_geometry();
            self.region_interaction.ownership_frame = None;
            self.tool = tool;
            self.region_interaction.tool = tool;
        }
    }

    pub fn cancel_geometry(&mut self) {
        self.cancel_magic();
        self.region_interaction.gesture = None;
        self.region_interaction.vertex = None;
        self.drag = None;
        self.polygon.clear();
    }

    pub fn owns_canvas(&self, ctx: &egui::Context) -> bool {
        self.tool != DrawingTool::Navigate
            && !ctx.input(|i| i.key_down(Key::Space) || i.modifiers.alt)
    }

    /// Decide once before the photograph handles input, and reuse that decision
    /// for the overlay. A pan which starts outside a region stays a pan even
    /// when the moving photograph carries a region under the pointer.
    pub fn owns_canvas_at(&mut self, ctx: &egui::Context, mapping: Option<(Rect, Rect)>) -> bool {
        let frame = ctx.cumulative_frame_nr();
        if self.region_interaction.ownership_frame == Some(frame) {
            return self.region_interaction.owns_pointer;
        }
        let (down, released, pressed, pointer, wheel) = ctx.input(|i| {
            (
                i.pointer.primary_down(),
                i.pointer.primary_released(),
                i.pointer.primary_pressed(),
                i.pointer.interact_pos(),
                i.raw_scroll_delta != Vec2::ZERO
                    || i.smooth_scroll_delta != Vec2::ZERO
                    || (i.zoom_delta() - 1.0).abs() > f32::EPSILON,
            )
        });
        let hit = mapping.is_some_and(|(image, clip)| {
            pointer.is_some_and(|at| {
                image.intersect(clip).contains(at) && self.region_hit(at, image).is_some()
            })
        });
        if !down && !released {
            self.region_interaction.navigation_press = false;
        }
        if pressed {
            self.region_interaction.navigation_press = self.tool == DrawingTool::Select && !hit;
        }
        let active = self.region_interaction.gesture.is_some();
        let owns = self.owns_canvas(ctx)
            && !self.region_interaction.navigation_press
            && (active || pressed || !wheel)
            && (active || self.tool != DrawingTool::Select || hit);
        self.region_interaction.ownership_frame = Some(frame);
        self.region_interaction.owns_pointer = owns;
        owns
    }

    pub fn select_photograph(&mut self) {
        self.commit_edit();
        self.cancel_geometry();
        self.selected = None;
        self.set_tool(DrawingTool::Select);
    }

    fn finish_geometry(&mut self, shape: RegionShape) {
        if shape.validate().is_ok()
            && let Err(error) = self.add_region(shape)
        {
            self.error = Some(error.to_string());
        }
    }

    pub fn draw_overlay(&mut self, ui: &mut egui::Ui, (image, clip): (Rect, Rect)) {
        // egui surrenders focus on Escape in begin-pass, before our widgets run.
        // Preserve only a real TextEdit ID and consult its previous-frame focus.
        let text_owned = self.text_owns_geometry_input(ui.ctx());
        self.region_interaction.text_focus = ui
            .ctx()
            .memory(|m| m.focused())
            .filter(|id| egui::TextEdit::load_state(ui.ctx(), *id).is_some());
        let allowed = ui.is_enabled()
            && ui.input(|i| i.focused && i.viewport().focused != Some(false))
            && ui.ctx().memory(|m| m.is_above_modal_layer(ui.layer_id()))
            && !egui::Popup::is_any_open(ui.ctx());
        if !image.is_finite() || !image.is_positive() || self.loaded.is_none() {
            self.cancel_geometry();
            return;
        }
        if !allowed {
            self.cancel_geometry();
            let visible = image.intersect(clip);
            if visible.is_positive() {
                self.paint_regions(ui, image, visible);
            }
            return;
        }
        if self.region_interaction.tool != self.tool {
            self.cancel_geometry();
            self.region_interaction.tool = self.tool;
        }
        if !text_owned && ui.input(|i| i.key_pressed(Key::Escape)) {
            let active = self.region_interaction.gesture.is_some()
                || !self.polygon.is_empty()
                || self.magic_pending();
            self.cancel_geometry();
            self.region_interaction.cancelled_press =
                ui.input(|i| i.pointer.primary_down() || i.pointer.primary_released());
            if !active {
                if self.tool == DrawingTool::Select {
                    self.selected = None;
                } else {
                    self.set_tool(DrawingTool::Select);
                }
            }
            self.paint_regions(ui, image, image.intersect(clip));
            return;
        }
        if !ui.input(|i| i.pointer.primary_down() || i.pointer.primary_released()) {
            self.region_interaction.cancelled_press = false;
        }
        let owns = self.owns_canvas_at(ui.ctx(), Some((image, clip)));
        if !owns {
            // Temporarily yielding the camera cancels a drag, while an unfinished
            // click polygon can remain in place for the next point after panning.
            self.region_interaction.gesture = None;
            self.drag = None;
        }
        if ui.input(|i| i.modifiers.alt) {
            return;
        }
        if self.region_interaction.gesture.as_ref().is_some_and(|gesture| {
            matches!(gesture, Gesture::Transform { revision, .. } if *revision != self.revision)
        }) {
            self.region_interaction.gesture = None;
        }
        let visible = image.intersect(clip);
        if !visible.is_positive() {
            return;
        }
        let hit = owns.then(|| {
            ui.interact(
                visible,
                ui.id().with("edit-region-canvas"),
                Sense::click_and_drag(),
            )
        });
        if let Some(hit) = &hit {
            let pointer = ui.input(|i| i.pointer.interact_pos());
            let hovered = hit.hovered();
            if self.tool == DrawingTool::Polygon {
                if hit.clicked()
                    && !self.region_interaction.cancelled_press
                    && let Some(at) = hit.interact_pointer_pos()
                {
                    let close = self.polygon.len() >= 3
                        && project(self.polygon[0], image).distance(at) <= 8.0;
                    if close || (hit.double_clicked() && self.polygon.len() >= 3) {
                        let points = std::mem::take(&mut self.polygon);
                        self.finish_geometry(RegionShape::Polygon { points });
                    } else if self.polygon.len() < 256 {
                        let point = normalized(at, image);
                        if self
                            .polygon
                            .last()
                            .is_none_or(|last| project(*last, image).distance(at) >= 2.0)
                        {
                            self.polygon.push(point);
                        }
                    }
                }
                if self.polygon.len() >= 3 && !text_owned && ui.input(|i| i.key_pressed(Key::Enter))
                {
                    let points = std::mem::take(&mut self.polygon);
                    self.finish_geometry(RegionShape::Polygon { points });
                }
            } else {
                // The overlay deliberately yields during wheel navigation, so
                // it may not exist in egui's previous-frame hit map. A fresh
                // press in this topmost, owned photo must still start a region
                // gesture without requiring an extra hover frame first.
                if (hit.is_pointer_button_down_on()
                    || (pointer.is_some_and(|at| visible.contains(at))
                        && ui.rect_contains_pointer(visible)))
                    && ui.input(|i| i.pointer.primary_pressed())
                    && !self.region_interaction.cancelled_press
                    && let Some(at) = pointer
                {
                    self.cancel_magic();
                    let uv = normalized(at, image);
                    if self.tool == DrawingTool::Select {
                        if let Some((id, control)) = self.region_hit(at, image) {
                            self.selected = Some(id.clone());
                            self.region_interaction.vertex = match control {
                                Control::Vertex(index) => Some((id.clone(), index)),
                                _ => None,
                            };
                            let original = self
                                .recipe
                                .regions
                                .iter()
                                .find(|r| r.id == id)
                                .unwrap()
                                .shape
                                .clone();
                            self.region_interaction.gesture = Some(Gesture::Transform {
                                id,
                                draft: original.clone(),
                                original,
                                control,
                                start: uv,
                                revision: self.revision,
                            });
                        } else {
                            self.selected = None;
                            self.region_interaction.vertex = None;
                        }
                    } else {
                        self.drag = Some(at);
                        self.region_interaction.gesture = Some(Gesture::Create {
                            tool: self.tool,
                            start: uv,
                            points: vec![uv],
                        });
                    }
                }
                if let Some(at) = pointer {
                    let uv = normalized(at, image);
                    if let Some(gesture) = &mut self.region_interaction.gesture {
                        match gesture {
                            Gesture::Transform {
                                original,
                                draft,
                                control,
                                start,
                                ..
                            } => {
                                *draft = if project(*start, image).distance(at) >= 3.0 {
                                    transform(original, *control, *start, uv, image)
                                } else {
                                    original.clone()
                                };
                            }
                            Gesture::Create {
                                tool: DrawingTool::Lasso | DrawingTool::MagicLasso,
                                points,
                                ..
                            } => {
                                for position in ui.input(|i| {
                                    i.events
                                        .iter()
                                        .filter_map(|event| match event {
                                            egui::Event::PointerMoved(at) => Some(*at),
                                            _ => None,
                                        })
                                        .collect::<Vec<_>>()
                                }) {
                                    append_lasso(points, normalized(position, image), image);
                                }
                                append_lasso(points, uv, image);
                            }
                            _ => {}
                        }
                    }
                }
                if ui.input(|i| i.pointer.primary_released()) {
                    if let Some(gesture) = self.region_interaction.gesture.take() {
                        match gesture {
                            Gesture::Create {
                                tool,
                                start,
                                points,
                            } => {
                                let shape =
                                    if matches!(tool, DrawingTool::Lasso | DrawingTool::MagicLasso)
                                    {
                                        RegionShape::Polygon {
                                            points: simplify_lasso(&points, image),
                                        }
                                    } else {
                                        drawn_shape(
                                            tool,
                                            start,
                                            pointer.map_or(start, |p| normalized(p, image)),
                                        )
                                    };
                                let bounds = shape_bounds(&shape);
                                if project(bounds[0], image).distance(project(bounds[1], image))
                                    >= 6.0
                                {
                                    if tool == DrawingTool::MagicLasso && shape.validate().is_ok() {
                                        self.start_magic(shape, ui.ctx());
                                    } else {
                                        self.finish_geometry(shape);
                                    }
                                }
                            }
                            Gesture::Transform {
                                id,
                                original,
                                draft,
                                revision,
                                ..
                            } => {
                                if revision == self.revision
                                    && draft != original
                                    && draft.validate().is_ok()
                                {
                                    let mut recipe = self.recipe.clone();
                                    if let Some(region) = recipe
                                        .regions
                                        .iter_mut()
                                        .find(|r| r.id == id && r.shape == original)
                                    {
                                        region.shape = draft;
                                        if let Err(error) = self.replace(recipe) {
                                            self.error = Some(error.to_string());
                                        }
                                    }
                                }
                            }
                        }
                    }
                    self.drag = None;
                }
                if self.tool == DrawingTool::Select
                    && hit.double_clicked()
                    && let Some(at) = pointer
                    && !self.insert_vertex(at, image)
                {
                    self.fit_view_requested = true;
                }
            }
            if hovered {
                let cursor = if self.tool == DrawingTool::Select {
                    pointer.and_then(|p| self.region_hit(p, image)).map_or(
                        CursorIcon::Default,
                        |(_, control)| match control {
                            Control::Move => CursorIcon::Grab,
                            Control::Vertex(_) => CursorIcon::Crosshair,
                            Control::Resize([x, y]) => match (x, y) {
                                (0, _) => CursorIcon::ResizeVertical,
                                (_, 0) => CursorIcon::ResizeHorizontal,
                                (-1, -1) | (1, 1) => CursorIcon::ResizeNwSe,
                                _ => CursorIcon::ResizeNeSw,
                            },
                        },
                    )
                } else {
                    CursorIcon::Crosshair
                };
                ui.ctx().set_cursor_icon(cursor);
            }
            if self.tool == DrawingTool::Select
                && !text_owned
                && ui.input(|i| i.key_pressed(Key::Delete) || i.key_pressed(Key::Backspace))
            {
                self.delete_vertex();
            }
        }
        self.paint_regions(ui, image, visible);
    }

    fn region_hit(&self, at: Pos2, image: Rect) -> Option<(String, Control)> {
        if !self.show_regions {
            return None;
        }
        if let Some(region) = self
            .recipe
            .regions
            .iter()
            .find(|r| Some(&r.id) == self.selected.as_ref())
            && let Some((_, control)) = handles(&region.shape)
                .into_iter()
                .filter(|(p, _)| project(*p, image).distance(at) <= 7.0)
                .min_by(|(a, _), (b, _)| {
                    project(*a, image)
                        .distance(at)
                        .total_cmp(&project(*b, image).distance(at))
                })
        {
            return Some((region.id.clone(), control));
        }
        let uv = normalized(at, image);
        self.recipe
            .regions
            .iter()
            .rev()
            .find(|region| {
                region.shape.contains(uv)
                    || nearest_edge(&region.shape, at, image)
                        .is_some_and(|(_, distance)| distance <= 6.0)
            })
            .map(|r| (r.id.clone(), Control::Move))
    }

    fn insert_vertex(&mut self, at: Pos2, image: Rect) -> bool {
        let Some(id) = &self.selected else {
            return false;
        };
        let Some(region) = self.recipe.regions.iter().find(|r| &r.id == id) else {
            return false;
        };
        let RegionShape::Polygon { points } = &region.shape else {
            return false;
        };
        if points.len() >= 256
            || points
                .iter()
                .any(|p| project(*p, image).distance(at) <= 7.0)
        {
            return false;
        }
        let Some((edge, distance)) = nearest_edge(&region.shape, at, image) else {
            return false;
        };
        if distance > 7.0 {
            return false;
        }
        let mut recipe = self.recipe.clone();
        let region = recipe.regions.iter_mut().find(|r| &r.id == id).unwrap();
        if let RegionShape::Polygon { points } = &mut region.shape {
            points.insert(edge + 1, normalized(at, image));
        }
        let id = id.clone();
        if self.replace(recipe).is_ok() {
            self.region_interaction.vertex = Some((id, edge + 1));
        }
        true
    }

    fn delete_vertex(&mut self) {
        let Some((id, vertex)) = &self.region_interaction.vertex else {
            return;
        };
        let mut recipe = self.recipe.clone();
        let Some(region) = recipe.regions.iter_mut().find(|r| &r.id == id) else {
            return;
        };
        if let RegionShape::Polygon { points } = &mut region.shape
            && points.len() > 3
            && *vertex < points.len()
        {
            points.remove(*vertex);
            if self.replace(recipe).is_ok() {
                self.region_interaction.vertex = None;
            }
        }
    }

    fn paint_regions(&self, ui: &egui::Ui, image: Rect, visible: Rect) {
        let paint = ui.painter_at(visible);
        if let Some(shape) = &self.magic.outline {
            let points = outline(shape)
                .into_iter()
                .map(|p| project(p, image))
                .collect();
            paint.add(Shape::closed_line(
                points,
                Stroke::new(1.0f32, crate::theme::ACCENT),
            ));
            let at = project(shape_bounds(shape)[0], image).clamp(visible.min, visible.max);
            paint.text(
                at,
                egui::Align2::LEFT_TOP,
                "Finding detail…",
                egui::FontId::proportional(11.0),
                crate::theme::ACCENT,
            );
        }
        if self.show_regions {
            for (index, region) in self.recipe.regions.iter().enumerate() {
                let shape = match &self.region_interaction.gesture {
                    Some(Gesture::Transform { id, draft, .. }) if id == &region.id => draft,
                    _ => &region.shape,
                };
                let selected = self.selected.as_ref() == Some(&region.id);
                let color = if region.enabled {
                    crate::process_sample_glyphs::level_color(index % 7)
                } else {
                    crate::theme::MUTED
                };
                let points = outline(shape)
                    .into_iter()
                    .map(|p| project(p, image))
                    .collect::<Vec<_>>();
                paint.add(Shape::closed_line(
                    points.clone(),
                    Stroke::new(2.5f32, Color32::BLACK.gamma_multiply(0.7)),
                ));
                paint.add(Shape::closed_line(points, Stroke::new(1.0f32, color)));
                if selected && self.tool == DrawingTool::Select {
                    let mut shown: Vec<Pos2> = Vec::new();
                    let pointer = ui.input(|i| i.pointer.hover_pos());
                    for (position, control) in handles(shape) {
                        let at = project(position, image);
                        let picked = matches!(control, Control::Vertex(index) if self.region_interaction.vertex.as_ref().is_some_and(|(id, v)| id == &region.id && *v == index));
                        let nearby = pointer.is_some_and(|p| p.distance(at) < 30.0);
                        if !picked && !nearby && shown.iter().any(|p| p.distance(at) < 14.0) {
                            continue;
                        }
                        shown.push(at);
                        paint.rect_filled(
                            Rect::from_center_size(at, Vec2::splat(5.0)),
                            0.0,
                            crate::theme::BG,
                        );
                        paint.rect_stroke(
                            Rect::from_center_size(at, Vec2::splat(5.0)),
                            0.0,
                            Stroke::new(1.0f32, color),
                            egui::StrokeKind::Inside,
                        );
                    }
                    let at = project(shape_bounds(shape)[0], image) + egui::vec2(0.0, -17.0);
                    let label = paint.layout_no_wrap(
                        region.name.clone(),
                        egui::FontId::proportional(10.0),
                        color,
                    );
                    let bounds = Rect::from_min_size(at, label.size()).expand(2.0);
                    paint.rect_filled(bounds, 0.0, crate::theme::BG.gamma_multiply(0.9));
                    paint.galley(at, label, color);
                }
            }
        }
        let mut path = self
            .polygon
            .iter()
            .map(|p| project(*p, image))
            .collect::<Vec<_>>();
        if let Some(Gesture::Create {
            tool,
            start,
            points,
        }) = &self.region_interaction.gesture
        {
            path = if matches!(tool, DrawingTool::Lasso | DrawingTool::MagicLasso) {
                points.iter().map(|p| project(*p, image)).collect()
            } else {
                outline(&drawn_shape(
                    *tool,
                    *start,
                    ui.input(|i| i.pointer.interact_pos())
                        .map_or(*start, |p| normalized(p, image)),
                ))
                .into_iter()
                .map(|p| project(p, image))
                .collect()
            };
            if !matches!(tool, DrawingTool::Lasso | DrawingTool::MagicLasso) && !path.is_empty() {
                path.push(path[0]);
            }
        } else if self.tool == DrawingTool::Polygon
            && !path.is_empty()
            && let Some(at) = ui.input(|i| i.pointer.hover_pos())
        {
            path.push(at.clamp(image.min, image.max));
        }
        if path.len() >= 2 {
            paint.add(Shape::line(path, Stroke::new(1.0f32, crate::theme::ACCENT)));
        }
        if let Some(first) = self.polygon.first() {
            paint.circle_stroke(
                project(*first, image),
                4.0,
                Stroke::new(1.0f32, crate::theme::ACCENT),
            );
        }
    }
}

fn text_editor_focused(ctx: &egui::Context) -> bool {
    ctx.memory(|m| m.focused())
        .is_some_and(|id| egui::TextEdit::load_state(ctx, id).is_some())
}

fn project(point: [f32; 2], image: Rect) -> Pos2 {
    image.min + image.size() * Vec2::from(point)
}

fn drawn_shape(tool: DrawingTool, a: [f32; 2], b: [f32; 2]) -> RegionShape {
    let min = [a[0].min(b[0]), a[1].min(b[1])];
    let max = [a[0].max(b[0]), a[1].max(b[1])];
    if tool == DrawingTool::Rectangle {
        RegionShape::Rectangle { min, max }
    } else {
        RegionShape::Ellipse {
            center: [(min[0] + max[0]) * 0.5, (min[1] + max[1]) * 0.5],
            radius: [(max[0] - min[0]) * 0.5, (max[1] - min[1]) * 0.5],
        }
    }
}

fn handles(shape: &RegionShape) -> Vec<([f32; 2], Control)> {
    if let RegionShape::Polygon { points } = shape {
        return points
            .iter()
            .copied()
            .enumerate()
            .map(|(i, p)| (p, Control::Vertex(i)))
            .collect();
    }
    // Ellipse handles describe the actual shape, including its off-image part.
    let [min, max] = match shape {
        RegionShape::Ellipse { center, radius } => [
            [center[0] - radius[0], center[1] - radius[1]],
            [center[0] + radius[0], center[1] + radius[1]],
        ],
        _ => shape_bounds(shape),
    };
    [
        (-1, -1),
        (0, -1),
        (1, -1),
        (1, 0),
        (1, 1),
        (0, 1),
        (-1, 1),
        (-1, 0),
    ]
    .into_iter()
    .map(|(x, y)| {
        let position = |axis: usize, side| match side {
            -1 => min[axis],
            1 => max[axis],
            _ => (min[axis] + max[axis]) * 0.5,
        };
        ([position(0, x), position(1, y)], Control::Resize([x, y]))
    })
    .collect()
}

fn transform(
    shape: &RegionShape,
    control: Control,
    start: [f32; 2],
    at: [f32; 2],
    image: Rect,
) -> RegionShape {
    let [mut min, mut max] = shape_bounds(shape);
    match control {
        Control::Move => {
            if let RegionShape::Ellipse { center, radius } = shape {
                return RegionShape::Ellipse {
                    center: std::array::from_fn(|i| (center[i] + at[i] - start[i]).clamp(0.0, 1.0)),
                    radius: *radius,
                };
            }
            let delta: [f32; 2] =
                std::array::from_fn(|i| (at[i] - start[i]).clamp(-min[i], 1.0 - max[i]));
            let shift = |p: [f32; 2]| [p[0] + delta[0], p[1] + delta[1]];
            match shape {
                RegionShape::Ellipse { center, radius } => RegionShape::Ellipse {
                    center: shift(*center),
                    radius: *radius,
                },
                RegionShape::Rectangle { min, max } => RegionShape::Rectangle {
                    min: shift(*min),
                    max: shift(*max),
                },
                RegionShape::Polygon { points } => RegionShape::Polygon {
                    points: points.iter().copied().map(shift).collect(),
                },
            }
        }
        Control::Resize(sides) => {
            if let RegionShape::Ellipse { center, radius } = shape {
                let (mut center, mut radius) = (*center, *radius);
                for axis in 0..2 {
                    if sides[axis] == 0 {
                        continue;
                    }
                    let minimum = (2.0 / image.size()[axis]).clamp(0.0002, 0.5);
                    let (lo, hi) = if sides[axis] < 0 {
                        let anchor = center[axis] + radius[axis];
                        (
                            at[axis].min(anchor - minimum).min(2.0 - anchor).max(0.0),
                            anchor,
                        )
                    } else {
                        let anchor = center[axis] - radius[axis];
                        (anchor, at[axis].max(anchor + minimum).max(-anchor).min(1.0))
                    };
                    center[axis] = (lo + hi) * 0.5;
                    radius[axis] = (hi - lo) * 0.5;
                }
                return RegionShape::Ellipse { center, radius };
            }
            for axis in 0..2 {
                let minimum = (2.0 / image.size()[axis]).clamp(0.0002, 0.5);
                if sides[axis] < 0 {
                    min[axis] = at[axis].min(max[axis] - minimum).max(0.0);
                }
                if sides[axis] > 0 {
                    max[axis] = at[axis].max(min[axis] + minimum).min(1.0);
                }
            }
            drawn_shape(
                if matches!(shape, RegionShape::Rectangle { .. }) {
                    DrawingTool::Rectangle
                } else {
                    DrawingTool::Ellipse
                },
                min,
                max,
            )
        }
        Control::Vertex(index) => {
            let mut shape = shape.clone();
            if let RegionShape::Polygon { points } = &mut shape
                && let Some(point) = points.get_mut(index)
            {
                *point = at;
            }
            shape
        }
    }
}

fn edge_distance(at: Pos2, a: Pos2, b: Pos2) -> f32 {
    let line = b - a;
    let t = ((at - a).dot(line) / line.length_sq().max(0.00001)).clamp(0.0, 1.0);
    at.distance(a + line * t)
}

fn nearest_edge(shape: &RegionShape, at: Pos2, image: Rect) -> Option<(usize, f32)> {
    let points = outline(shape);
    points
        .iter()
        .zip(points.iter().cycle().skip(1))
        .enumerate()
        .map(|(i, (a, b))| (i, edge_distance(at, project(*a, image), project(*b, image))))
        .min_by(|a, b| a.1.total_cmp(&b.1))
}

fn append_lasso(points: &mut Vec<[f32; 2]>, point: [f32; 2], image: Rect) {
    if points
        .last()
        .is_none_or(|last| project(*last, image).distance(project(point, image)) >= 2.0)
    {
        if points.len() >= 2048 {
            *points = points.iter().step_by(2).copied().collect();
        }
        points.push(point);
    }
}

pub(super) fn simplify_lasso(points: &[[f32; 2]], image: Rect) -> Vec<[f32; 2]> {
    fn reduce(points: &[[f32; 2]], image: Rect, tolerance: f32, output: &mut Vec<[f32; 2]>) {
        if points.len() < 2 {
            return;
        }
        let a = project(points[0], image);
        let b = project(*points.last().unwrap(), image);
        if let Some((index, distance)) = points
            .iter()
            .enumerate()
            .skip(1)
            .take(points.len() - 2)
            .map(|(i, p)| (i, edge_distance(project(*p, image), a, b)))
            .max_by(|a, b| a.1.total_cmp(&b.1))
            && distance > tolerance
        {
            reduce(&points[..=index], image, tolerance, output);
            reduce(&points[index..], image, tolerance, output);
        } else {
            output.push(points[0]);
        }
    }
    if points.len() < 3 {
        return Vec::new();
    }
    let mut closed = points.to_vec();
    if closed.last() != closed.first() {
        closed.push(closed[0]);
    }
    let mut tolerance = 1.5;
    loop {
        let mut simplified = Vec::new();
        reduce(&closed, image, tolerance, &mut simplified);
        if simplified.len() <= 256 {
            return simplified;
        }
        tolerance *= 1.5;
    }
}

#[cfg(test)]
#[path = "edit-region-tests.rs"]
mod tests;
