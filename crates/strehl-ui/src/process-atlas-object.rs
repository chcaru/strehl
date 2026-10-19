// Object-attached instruments. No screen-edge bars or independent panels.
fn object_scene(bounds: Rect) -> Rect {
    let margin = egui::vec2((bounds.width() * 0.14).clamp(72.0, 140.0), 86.0);
    Rect::from_center_size(
        bounds.center(),
        (bounds.size() - margin * 2.0).max(Vec2::splat(40.0)),
    )
}

struct ObjectDock {
    hub: Rect,
    phases: Rect,
    details: Rect,
    camera: Option<Rect>,
    identity: Pos2,
    info: Pos2,
}
impl ObjectDock {
    fn new(bounds: Rect, projection: Projection) -> Self {
        let front = Rect::from_points(&projection.quad(0.0));
        let width = front.width().clamp(180.0, 500.0);
        let hub = Rect::from_min_size(
            egui::pos2(
                front.left().clamp(
                    bounds.left() + 12.0,
                    (bounds.right() - 256.0).max(bounds.left() + 12.0),
                ),
                (front.top() - 68.0).clamp(
                    bounds.top() + 12.0,
                    (bounds.bottom() - 40.0).max(bounds.top() + 12.0),
                ),
            ),
            egui::vec2(244.0, 24.0),
        );
        let phases =
            Rect::from_min_size(front.min - egui::vec2(0.0, 39.0), egui::vec2(width, 20.0));
        let details = Rect::from_min_size(
            front.min - egui::vec2(102.0, 0.0),
            egui::vec2(84.0, front.height().clamp(168.0, 496.0)),
        );
        // Camera pixels must not occlude either the photograph or the exposed
        // capture layers. The front alone underestimates the object's width.
        let volume = front.union(Rect::from_points(&projection.quad(1.0)));
        // Flattening the volume leaves a real, vertical capture instrument.
        // Reserve its arcs, labels and hit area as well as the projected object.
        let capture = capture_instrument_bounds(projection);
        let camera_size = egui::vec2(118.0, 112.0);
        let camera = [
            volume.right_top() + egui::vec2(26.0, 78.0),
            egui::pos2(volume.right() + 26.0, capture.bottom() + 16.0),
            volume.right_bottom() + egui::vec2(26.0, -camera_size.y),
            volume.left_bottom() + egui::vec2(0.0, 26.0),
            volume.right_bottom() + egui::vec2(-camera_size.x, 26.0),
            volume.left_top() - egui::vec2(camera_size.x + 26.0, 0.0),
        ]
        .into_iter()
        .map(|at| Rect::from_min_size(at, camera_size))
        .find(|rect| {
            bounds.shrink(10.0).contains_rect(*rect)
                && [volume, hub, phases, details, capture]
                    .iter()
                    .all(|occupied| !rect.intersects(occupied.expand(10.0)))
        });
        Self {
            hub,
            phases,
            details,
            camera,
            identity: front.min - egui::vec2(0.0, 14.0),
            info: front.left_bottom() + egui::vec2(0.0, 18.0),
        }
    }
}

impl ProcessAtlas {
    fn object_menu(&mut self, ui: &mut Ui, result: &mut Response, history_action: &mut bool) {
        if ui.button("Workspace").clicked() {
            result.exit_space = true;
            ui.close();
        }
        if ui
            .button("Photograph / flatten and clear inspection")
            .clicked()
        {
            self.photograph();
            result.return_live = true;
            ui.close();
        }
        if ui.button("Explore capture volume").clicked() {
            self.camera = Camera::default();
            ui.close();
        }
        if ui.button("Clear capture highlight").clicked() {
            self.selected = None;
            self.pin = None;
            self.pin_is_aligned = false;
            ui.close();
        }
        ui.separator();
        ui.horizontal(|ui| {
            if ui
                .add_enabled(self.can_undo(), egui::Button::new("Undo view"))
                .clicked()
            {
                *history_action = self.undo();
                ui.close();
            }
            if ui
                .add_enabled(self.can_redo(), egui::Button::new("Redo view"))
                .clicked()
            {
                *history_action = self.redo();
                ui.close();
            }
        });
        ui.separator();
        ui.label("Drag: orbit · Shift-drag: pan · wheel: zoom");
        ui.label("Double-click: photograph · drag the lower corner to spread captures");
        ui.menu_button("Window", |ui| {
            if ui.button("Minimize").clicked() {
                ui.ctx()
                    .send_viewport_cmd(egui::ViewportCommand::Minimized(true));
                ui.close();
            }
            let maximized = ui.input(|state| state.viewport().maximized.unwrap_or(false));
            if ui
                .button(if maximized { "Restore" } else { "Maximize" })
                .clicked()
            {
                ui.ctx()
                    .send_viewport_cmd(egui::ViewportCommand::Maximized(!maximized));
                ui.close();
            }
            if ui.button("Close Strehl").clicked() {
                ui.ctx().send_viewport_cmd(egui::ViewportCommand::Close);
                ui.close();
            }
        });
    }

    fn object_controls(
        &mut self,
        ui: &mut Ui,
        p: &Painter,
        dock: &ObjectDock,
        input: &Input<'_>,
        result: &mut Response,
        history_action: &mut bool,
    ) {
        let workspace = Rect::from_min_size(dock.hub.min, egui::vec2(80.0, 24.0));
        let photo = workspace.translate(egui::vec2(82.0, 0.0));
        let explore = workspace.translate(egui::vec2(164.0, 0.0));
        if button(ui, p, workspace, "atlas-workspace", "Workspace", false) {
            result.exit_space = true;
        }
        if button(ui, p, photo, "atlas-home", "Photograph", false) {
            self.photograph();
            result.return_live = true;
        }
        if button(
            ui,
            p,
            explore,
            "atlas-explore",
            "Explore",
            self.camera.yaw != 0.0,
        ) {
            self.camera = Camera::default();
        }
        // The small object grip owns a local cursor menu, even when zoom has
        // carried other instruments outside the viewport.
        let grip = Rect::from_center_size(
            dock.hub.left_center() - egui::vec2(8.0, 0.0),
            Vec2::splat(12.0),
        );
        p.circle_stroke(grip.center(), 3.5, Stroke::new(1.0_f32, ACCENT));
        ui.interact(grip, ui.id().with("atlas-object-menu"), Sense::click())
            .context_menu(|ui| self.object_menu(ui, result, history_action));
        if dock.phases.width() >= 180.0 {
            phase_strip(ui, dock.phases, input);
        }
        p.line_segment(
            [
                dock.phases.left_bottom(),
                dock.identity + egui::vec2(0.0, 12.0),
            ],
            Stroke::new(0.7_f32, LINE),
        );
    }

    fn detail_axis(
        &mut self,
        ui: &mut Ui,
        p: &Painter,
        rect: Rect,
        projection: Projection,
        input: &Input<'_>,
    ) {
        let count = input
            .progress
            .bands
            .map_or(8, |bands| bands + 1)
            .clamp(1, 64);
        let cell = rect.height() / count as f32;
        let rail = ui.interact(
            rect,
            ui.id().with("atlas-detail-rail"),
            Sense::click_and_drag(),
        );
        if (rail.dragged() || rail.clicked() || rail.is_pointer_button_down_on())
            && let Some(pointer) = rail.interact_pointer_pos()
        {
            self.level = ((pointer.y - rect.top()) / cell)
                .floor()
                .clamp(0.0, (count - 1) as f32) as usize;
            self.level_chosen = true;
        }
        label(p, rect.min - egui::vec2(0.0, 15.0), "DETAIL", 8.0, MUTED);
        for level in 0..count {
            let item = Rect::from_min_size(
                rect.min + egui::vec2(0.0, level as f32 * cell),
                egui::vec2(rect.width(), cell),
            );
            let color = crate::process_sample_glyphs::level_color(level);
            let image = Rect::from_min_size(
                item.min + egui::vec2(1.0, 2.0),
                egui::vec2(32.0, (cell - 6.0).clamp(6.0, 34.0)),
            );
            let surface = input
                .surfaces
                .iter()
                .filter(|surface| surface.epoch == input.epoch && surface.level == level)
                .filter(|surface| surface.frame.is_none() || surface.frame == self.selected)
                .filter_map(|surface| {
                    surface
                        .meta
                        .filter(|meta| {
                            matches!(
                                meta.kind,
                                DiagnosticKind::Coefficient
                                    | DiagnosticKind::GateSupport
                                    | DiagnosticKind::FocusEnergy
                                    | DiagnosticKind::Averaging
                            )
                        })
                        .map(|meta| (surface, meta))
                })
                .max_by_key(|(_, meta)| (meta.kind == DiagnosticKind::Coefficient, meta.sequence));
            if let Some((surface, _)) = surface {
                p.image(
                    surface.texture.id(),
                    image,
                    Rect::from_min_max(Pos2::ZERO, egui::pos2(1.0, 1.0)),
                    Color32::WHITE,
                );
            } else {
                // This glyph names the band, not an invented diagnostic image.
                let lines = (level + 1).min(8);
                for index in 0..lines {
                    let x = image.left() + (index as f32 + 0.5) * image.width() / lines as f32;
                    p.line_segment(
                        [
                            egui::pos2(x, image.top() + 3.0),
                            egui::pos2(x, image.bottom() - 3.0),
                        ],
                        Stroke::new(0.6_f32, color.gamma_multiply(0.45)),
                    );
                }
            }
            p.rect_stroke(
                image,
                0.0,
                Stroke::new(
                    if level == self.level {
                        1.2_f32
                    } else {
                        0.6_f32
                    },
                    color,
                ),
                egui::StrokeKind::Outside,
            );
            let label_text = if input.progress.bands == Some(level) {
                "tone".to_owned()
            } else {
                crate::process_output_space::detail_label(level, input.progress.output_geometry)
            };
            if cell >= 17.0 {
                label(
                    p,
                    image.right_top() + egui::vec2(5.0, 2.0),
                    &label_text,
                    7.0,
                    if level == self.level { INK } else { MUTED },
                );
            }
            let destination =
                projection.at(egui::pos2(0.0, (level as f32 + 0.5) / count as f32), 0.0);
            p.line_segment(
                [item.right_center(), destination],
                Stroke::new(
                    if level == self.level {
                        1.0_f32
                    } else {
                        0.5_f32
                    },
                    color.gamma_multiply(if level == self.level { 0.8 } else { 0.2 }),
                ),
            );
            let known = input.progress.admission_archive.frames(level).count();
            if known > 0 {
                p.line_segment(
                    [
                        image.left_bottom(),
                        image.left_bottom().lerp(
                            image.right_bottom(),
                            known as f32 / input.processing_count().max(1) as f32,
                        ),
                    ],
                    Stroke::new(1.0_f32, color),
                );
            }
            ui.interact(item, ui.id().with(("atlas-detail-level", level)), Sense::hover()).on_hover_text(format!(
                "Band {} · {}\n{} captures have observed admission samples. {}\n{}\nDrag this edge to compare bands.", level + 1, label_text, known,
                surface.map_or("No diagnostic image observed yet.", |(_, meta)| meta.kind.title()),
                crate::process_output_space::detail_tooltip(level, input.progress.output_geometry)));
        }
    }

    fn spread_handle(
        &mut self,
        ui: &mut Ui,
        p: &Painter,
        scene: Rect,
        projection: Projection,
        allowed: bool,
    ) {
        let Some((start, end)) = spread_axis(projection) else {
            self.spread_grab = None;
            return;
        };
        let hit = ui.interact(
            Rect::from_center_size(end, Vec2::splat(26.0)),
            ui.id().with("atlas-capture-spread"),
            Sense::click_and_drag(),
        );
        let active = hit.hovered() || self.spread_grab.is_some();
        let ink = if active { ACCENT } else { MUTED };
        p.line_segment([start, end], Stroke::new(0.7_f32, ink));
        let normal = (end - start).normalized().rot90() * 4.0;
        p.line_segment([start - normal, start + normal], Stroke::new(0.8_f32, ink));
        p.rect_stroke(
            Rect::from_center_size(end, Vec2::splat(if active { 8.0 } else { 6.0 })),
            0.0,
            Stroke::new(1.0_f32, ink),
            egui::StrokeKind::Middle,
        );
        p.text(
            start.lerp(end, 0.5) + egui::vec2(0.0, 12.0),
            Align2::CENTER_TOP,
            format!(
                "SPREAD {:.1}×",
                self.camera.spread / Camera::default().spread
            ),
            FontId::monospace(7.5),
            ink,
        );
        if !allowed {
            self.spread_grab = None;
            return;
        }
        if hit.is_pointer_button_down_on()
            && ui.input(|state| state.pointer.primary_pressed())
            && let Some(pointer) = hit.interact_pointer_pos()
        {
            self.spread_grab = Some(SpreadGrab {
                pointer,
                endpoint: end,
                camera: self.camera,
            });
            self.grab = None;
        }
        if hit.dragged()
            && let (Some(grab), Some(pointer)) = (self.spread_grab, hit.interact_pointer_pos())
        {
            self.camera.spread = spread_at_pointer(scene, projection.aspect, grab, pointer);
            self.grab = None;
            ui.ctx().request_repaint();
        }
        if hit.double_clicked() {
            self.camera.spread = Camera::default().spread;
            self.spread_grab = None;
            ui.ctx().request_repaint();
        }
        if active {
            ui.ctx().set_cursor_icon(egui::CursorIcon::ResizeNwSe);
        }
        if !ui.input(|state| state.pointer.primary_down()) {
            self.spread_grab = None;
        }
        hit.on_hover_text("Drag this corner to separate capture layers. Double-click restores their spacing. This axis is capture order, not measured scene depth.");
    }

    fn capture_axis(
        &mut self,
        ui: &mut Ui,
        p: &Painter,
        projection: Projection,
        input: &Input<'_>,
        response: &mut Response,
    ) {
        let (start, end) = capture_rail(projection);
        p.line_segment([start, end], Stroke::new(0.8_f32, MUTED));
        let caption = p.layout_no_wrap("CAPTURE ORDER".to_owned(), FontId::proportional(8.0), INK);
        let visible = p.clip_rect().shrink(3.0);
        let size = caption.size();
        if visible.width() >= size.x && visible.height() >= size.y {
            let mut at = start + egui::vec2(7.0, -17.0);
            if at.x + size.x > visible.right() {
                at.x = visible.right() - size.x;
                at.y =
                    at.y.min(Rect::from_points(&projection.quad(0.0)).top() - 17.0);
            }
            at.x = at.x.clamp(visible.left(), visible.right() - size.x);
            at.y = at.y.clamp(visible.top(), visible.bottom() - size.y);
            p.galley(at, caption, INK);
        }
        // These arcs are actual direct fit observations, not composed transforms
        // or reconstructed depth. Selection reveals that capture's neighborhood.
        let edges = input
            .progress
            .alignment_edge_observations
            .iter()
            .rev()
            .filter(|edge| edge.pair.iter().all(|&frame| frame < input.frame_count))
            .filter(|edge| {
                self.selected
                    .is_none_or(|selected| edge.pair.contains(&selected))
            })
            .take(48);
        for edge in edges {
            let a = start.lerp(end, capture_depth(edge.pair[0], input.frame_count));
            let b = start.lerp(end, capture_depth(edge.pair[1], input.frame_count));
            let middle = a.lerp(b, 0.5) + egui::vec2((a.distance(b) * 0.35).clamp(9.0, 34.0), -7.0);
            let points: Vec<_> = (0..=12)
                .map(|index| {
                    let t = index as f32 / 12.0;
                    a.lerp(middle, t).lerp(middle.lerp(b, t), t)
                })
                .collect();
            let color = match edge.outcome {
                crate::pipeline::AlignmentOutcome::Accepted => GREEN,
                crate::pipeline::AlignmentOutcome::Refused => AMBER,
                crate::pipeline::AlignmentOutcome::Unknown => MUTED,
            };
            p.add(egui::Shape::line(
                points,
                Stroke::new(0.7_f32, color.gamma_multiply(0.6)),
            ));
        }
        for layer in &self.layers {
            let at = start.lerp(end, capture_depth(layer.frame, input.frame_count));
            let selected = self.selected == Some(layer.frame);
            p.circle_filled(
                at,
                if selected { 3.5 } else { 2.0 },
                if layer.sequence.is_some() {
                    capture_color(layer.frame)
                } else {
                    LINE
                },
            );
            let hit = ui.interact(
                Rect::from_center_size(at, Vec2::splat(14.0)),
                ui.id().with(("atlas-capture", layer.frame)),
                Sense::hover(),
            );
            if selected || hit.hovered() || layer.frame == 0 || layer.frame + 1 == input.frame_count
            {
                label(
                    p,
                    at + egui::vec2(7.0, 0.0),
                    &format!("{:03}", layer.frame + 1),
                    8.0,
                    if selected { INK } else { MUTED },
                );
            }
            hit.on_hover_text(format!("Capture {} · drag to inspect\nArcs: observed direct fits. Capture order is not physical depth.", layer.frame + 1));
        }
        let rail = Rect::from_two_pos(start, end).expand(7.0);
        let hit = ui.interact(
            rail,
            ui.id().with("atlas-capture-order"),
            Sense::click_and_drag(),
        );
        if input.frame_count > 0
            && (hit.dragged() || hit.clicked() || hit.is_pointer_button_down_on())
            && let Some(pointer) = hit.interact_pointer_pos()
        {
            let direction = end - start;
            let t =
                ((pointer - start).dot(direction) / direction.length_sq().max(1.0)).clamp(0.0, 1.0);
            let frame = (((t - 0.08) / 0.92 * input.frame_count as f32) - 1.0)
                .round()
                .clamp(0.0, input.frame_count.saturating_sub(1) as f32)
                as usize;
            self.selected = Some(frame);
            response.selected = Some(frame);
        }
    }

    fn camera_card(
        &self,
        ui: &mut Ui,
        p: &Painter,
        dock: &ObjectDock,
        projection: Projection,
        input: &Input<'_>,
    ) {
        let Some(card) = dock.camera else { return };
        let Some(frame) = self
            .selected
            .or(input.progress.processing_frame)
            .or((input.frame_count > 0).then_some(input.selected))
        else {
            return;
        };
        let (start, end) = capture_rail(projection);
        let at = start.lerp(end, capture_depth(frame, input.frame_count));
        let color = capture_color(frame);
        p.line_segment(
            [at, card.left_top() + egui::vec2(0.0, 9.0)],
            Stroke::new(0.7_f32, color.gamma_multiply(0.65)),
        );
        label(p, card.min, &format!("CAMERA {:03}", frame + 1), 8.0, color);
        let aperture = Rect::from_min_size(
            card.min + egui::vec2(0.0, 17.0),
            egui::vec2(card.width(), 72.0),
        );
        let photo = input
            .inspection_photos
            .iter()
            .chain(input.photos.iter())
            .filter(|photo| photo.epoch == input.epoch && photo.index == frame)
            .max_by_key(|photo| photo.texture.size()[0] * photo.texture.size()[1]);
        if let Some(photo) = photo {
            let size = photo.texture.size_vec2();
            let fit = (aperture.width() / size.x).min(aperture.height() / size.y);
            let rect = Rect::from_center_size(aperture.center(), size * fit);
            p.image(
                photo.texture.id(),
                rect,
                Rect::from_min_max(Pos2::ZERO, egui::pos2(1.0, 1.0)),
                Color32::WHITE,
            );
        } else {
            label(
                p,
                aperture.min + egui::vec2(0.0, 22.0),
                "Camera preview pending",
                8.0,
                MUTED,
            );
        }
        p.rect_stroke(
            aperture,
            0.0,
            Stroke::new(0.6_f32, color.gamma_multiply(0.6)),
            egui::StrokeKind::Inside,
        );
        label(
            p,
            aperture.left_bottom() + egui::vec2(0.0, 5.0),
            "Unregistered camera view",
            7.5,
            MUTED,
        );
        ui.interact(card, ui.id().with("atlas-camera-card"), Sense::hover()).on_hover_text("The actual camera preview for this capture. Its pixels are not registered to the final photograph; the tether identifies capture lineage only.");
    }
}

fn capture_rail(projection: Projection) -> (Pos2, Pos2) {
    let start = projection.at(egui::pos2(1.035, 0.08), 0.0);
    let mut end = projection.at(egui::pos2(1.035, 0.08), 1.0);
    if start.distance(end) < 48.0 {
        end = start + egui::vec2(0.0, (projection.scale * 0.5).clamp(80.0, 180.0));
    }
    (start, end)
}

fn capture_instrument_bounds(projection: Projection) -> Rect {
    let (start, end) = capture_rail(projection);
    let rail = Rect::from_two_pos(start, end);
    // Direct-fit control points extend at most 34 right / 7 up; capture
    // labels and the caption need additional room beyond the 7-point hit area.
    Rect::from_min_max(
        rail.min - egui::vec2(7.0, 24.0),
        rail.max + egui::vec2(84.0, 12.0),
    )
}

fn spread_axis(projection: Projection) -> Option<(Pos2, Pos2)> {
    let corner = egui::pos2(1.035, 1.035);
    let start = projection.at(corner, 0.0);
    let end = projection.at(corner, 1.0);
    // A flattened photograph has no exposed capture axis. Explore restores it.
    (start.distance(end) >= 4.0).then_some((start, end))
}

fn spread_at_pointer(scene: Rect, aspect: f32, grab: SpreadGrab, pointer: Pos2) -> f32 {
    let target = grab.endpoint + (pointer - grab.pointer);
    let distance = |spread: f32| {
        let projection = Projection::new(
            scene,
            Camera {
                spread,
                ..grab.camera
            },
            aspect,
        );
        projection
            .at(egui::pos2(1.035, 1.035), 1.0)
            .distance_sq(target)
    };
    // Projection also fits the volume as its depth changes. Invert that fit
    // instead of letting the grip drift away from the pointer on long drags.
    let (mut low, mut high) = (0.12_f32, 2.4_f32);
    for _ in 0..28 {
        let a = low + (high - low) / 3.0;
        let b = high - (high - low) / 3.0;
        if distance(a) < distance(b) {
            high = b;
        } else {
            low = a;
        }
    }
    [0.12, (low + high) * 0.5, 2.4]
        .into_iter()
        .min_by(|&a, &b| distance(a).total_cmp(&distance(b)))
        .unwrap_or(grab.camera.spread)
}

fn projected_sample_cell(
    p: &Painter,
    projection: Projection,
    cell: Rect,
    depth: f32,
    color: Color32,
    active: bool,
) {
    let quad = [
        cell.left_top(),
        cell.right_top(),
        cell.right_bottom(),
        cell.left_bottom(),
    ]
    .map(|uv| projection.at(uv, depth));
    if quad[0].distance(quad[1]).min(quad[0].distance(quad[3])) < 4.0 {
        return;
    }
    let stroke = Stroke::new(
        if active { 0.9_f32 } else { 0.6_f32 },
        color.gamma_multiply(if active { 0.7 } else { 0.28 }),
    );
    for index in 0..4 {
        let corner = quad[index];
        for neighbor in [(index + 1) % 4, (index + 3) % 4] {
            let edge = quad[neighbor] - corner;
            p.line_segment(
                [corner, corner + edge * (6.0 / edge.length()).min(0.22)],
                stroke,
            );
        }
    }
}
