use super::*;

struct Canvas {
    ctx: egui::Context,
    editor: EditorState,
    image: Rect,
    clip: Rect,
    time: f64,
}
impl Canvas {
    fn new() -> Self {
        let image = Arc::new(LinearImage {
            width: 16,
            height: 12,
            pixels: vec![0.2; 16 * 12 * 3],
            origin: strehl_edit::ImageOrigin::SceneLinear,
            baseline: None,
            baked_recipe: None,
        });
        let mut canvas = Self {
            ctx: egui::Context::default(),
            editor: EditorState {
                loaded: Some(LoadedPhoto {
                    image: image.clone(),
                    preview: image,
                    recipe: Default::default(),
                    source: "no-file".into(),
                    warnings: vec![],
                }),
                show_regions: true,
                ..Default::default()
            },
            image: Rect::from_min_max(egui::pos2(40.0, 30.0), egui::pos2(840.0, 630.0)),
            clip: Rect::from_min_max(Pos2::ZERO, egui::pos2(900.0, 680.0)),
            time: 0.0,
        };
        canvas.frame(vec![], Default::default());
        canvas.frame(vec![], Default::default());
        canvas
    }
    fn at(&self, uv: [f32; 2]) -> Pos2 {
        project(uv, self.image)
    }
    fn frame(&mut self, events: Vec<egui::Event>, modifiers: egui::Modifiers) {
        self.time += 0.04;
        let _ = self.ctx.run(
            egui::RawInput {
                screen_rect: Some(self.clip),
                time: Some(self.time),
                events,
                modifiers,
                ..Default::default()
            },
            |ctx| {
                egui::CentralPanel::default()
                    .frame(egui::Frame::NONE)
                    .show(ctx, |ui| {
                        self.editor.draw_overlay(ui, (self.image, self.clip))
                    });
            },
        );
    }
    fn pointer(&mut self, uv: [f32; 2], pressed: Option<bool>) {
        let at = self.at(uv);
        let mut events = vec![egui::Event::PointerMoved(at)];
        if let Some(pressed) = pressed {
            events.push(egui::Event::PointerButton {
                pos: at,
                button: egui::PointerButton::Primary,
                pressed,
                modifiers: Default::default(),
            });
        }
        self.frame(events, Default::default());
    }
    fn click(&mut self, uv: [f32; 2]) {
        self.pointer(uv, None);
        self.pointer(uv, Some(true));
        self.pointer(uv, Some(false));
    }
    fn key(&mut self, key: Key, pressed: bool) {
        self.frame(
            vec![egui::Event::Key {
                key,
                physical_key: None,
                pressed,
                repeat: false,
                modifiers: Default::default(),
            }],
            Default::default(),
        );
    }
    fn drag(&mut self, a: [f32; 2], b: [f32; 2]) {
        self.pointer(a, None);
        self.pointer(a, Some(true));
        self.pointer(b, None);
        self.pointer(b, Some(false));
    }
}
fn close(a: [f32; 2], b: [f32; 2]) {
    assert!(
        (a[0] - b[0]).abs() < 1e-5 && (a[1] - b[1]).abs() < 1e-5,
        "{a:?} != {b:?}"
    );
}

#[test]
fn ellipse_and_box_move_resize_commit_once_and_preserve_repair_provenance() {
    for tool in [DrawingTool::Ellipse, DrawingTool::Rectangle] {
        let mut canvas = Canvas::new();
        canvas.editor.set_tool(tool);
        canvas.drag([0.2, 0.2], [0.5, 0.5]);
        assert_eq!(canvas.editor.recipe.regions.len(), 1);
        assert_eq!(canvas.editor.tool, DrawingTool::Select);
        canvas.editor.recipe.regions[0].source_range =
            Some(strehl_edit::SourceRange { first: 3, last: 9 });
        canvas.editor.recipe.regions[0].adjustments.exposure = -0.7;
        let original = canvas.editor.recipe.clone();
        let history = canvas.editor.history_depths().0;
        canvas.pointer([0.35, 0.35], None);
        canvas.pointer([0.35, 0.35], Some(true));
        canvas.pointer([0.45, 0.43], None);
        assert_eq!(
            canvas.editor.recipe, original,
            "A draft must not be autosaved or restacked"
        );
        canvas.pointer([0.45, 0.43], Some(false));
        assert_eq!(canvas.editor.history_depths().0, history + 1);
        let bounds = shape_bounds(&canvas.editor.recipe.regions[0].shape);
        close(bounds[0], [0.3, 0.28]);
        close(bounds[1], [0.6, 0.58]);
        assert_eq!(
            canvas.editor.recipe.regions[0].source_range,
            original.regions[0].source_range
        );
        assert_eq!(
            canvas.editor.recipe.regions[0].adjustments,
            original.regions[0].adjustments
        );
        assert!(canvas.editor.undo());
        assert_eq!(canvas.editor.recipe, original);
        assert!(canvas.editor.redo());
        canvas.drag([0.6, 0.58], [0.75, 0.8]);
        close(
            shape_bounds(&canvas.editor.recipe.regions[0].shape)[1],
            [0.75, 0.8],
        );
        assert_eq!(canvas.editor.history_depths().0, history + 2);
    }
}

#[test]
fn escape_cancels_creation_and_geometry_without_a_recipe_or_undo_change() {
    let mut canvas = Canvas::new();
    canvas.editor.set_tool(DrawingTool::Rectangle);
    canvas.pointer([0.1, 0.1], None);
    canvas.pointer([0.1, 0.1], Some(true));
    canvas.pointer([0.7, 0.7], None);
    canvas.key(Key::Escape, true);
    canvas.pointer([0.7, 0.7], Some(false));
    canvas.key(Key::Escape, false);
    assert!(canvas.editor.recipe.regions.is_empty());
    assert!(!canvas.editor.can_undo());
    canvas.drag([0.2, 0.2], [0.5, 0.5]);
    let original = canvas.editor.recipe.clone();
    let depth = canvas.editor.history_depths();
    canvas.pointer([0.3, 0.3], None);
    canvas.pointer([0.3, 0.3], Some(true));
    canvas.pointer([0.6, 0.6], None);
    canvas.key(Key::Escape, true);
    canvas.pointer([0.6, 0.6], Some(false));
    assert_eq!(canvas.editor.recipe, original);
    assert_eq!(canvas.editor.history_depths(), depth);
}

#[test]
fn polygon_uses_clicks_and_lasso_captures_a_dragged_concave_path() {
    let mut canvas = Canvas::new();
    canvas.editor.set_tool(DrawingTool::Polygon);
    canvas.click([0.1, 0.1]);
    canvas.click([0.7, 0.1]);
    canvas.click([0.5, 0.7]);
    assert!(canvas.editor.recipe.regions.is_empty());
    assert_eq!(canvas.editor.polygon.len(), 3);
    canvas.key(Key::Enter, true);
    canvas.key(Key::Enter, false);
    assert_eq!(canvas.editor.recipe.regions.len(), 1);
    let RegionShape::Polygon { points } = &canvas.editor.recipe.regions[0].shape else {
        panic!("Polygon tool emitted another shape")
    };
    assert_eq!(points.len(), 3);
    let history = canvas.editor.history_depths().0;
    canvas.editor.set_tool(DrawingTool::Lasso);
    canvas.pointer([0.2, 0.2], None);
    canvas.pointer([0.2, 0.2], Some(true));
    let path = [
        [0.7, 0.2],
        [0.7, 0.4],
        [0.4, 0.4],
        [0.4, 0.7],
        [0.2, 0.7],
        [0.2, 0.2],
    ];
    let events = path
        .into_iter()
        .map(|p| egui::Event::PointerMoved(canvas.at(p)))
        .collect();
    canvas.frame(events, Default::default());
    canvas.pointer([0.2, 0.2], Some(false));
    assert_eq!(canvas.editor.recipe.regions.len(), 2);
    let lasso = &canvas.editor.recipe.regions[1].shape;
    let RegionShape::Polygon { points } = lasso else {
        panic!("Lasso must remain an editable polygon")
    };
    assert!((6..=256).contains(&points.len()));
    assert!(lasso.contains([0.3, 0.6]));
    assert!(
        !lasso.contains([0.6, 0.6]),
        "Lasso must preserve the concave notch rather than a bounding box"
    );
    assert_eq!(canvas.editor.history_depths().0, history + 1);
}

#[test]
fn polygon_vertices_move_insert_and_delete_as_discrete_history_actions() {
    let mut canvas = Canvas::new();
    canvas
        .editor
        .add_region(RegionShape::Polygon {
            points: vec![[0.2, 0.2], [0.7, 0.2], [0.7, 0.7], [0.2, 0.7]],
        })
        .unwrap();
    canvas.drag([0.2, 0.2], [0.1, 0.1]);
    let RegionShape::Polygon { points } = &canvas.editor.recipe.regions[0].shape else {
        unreachable!()
    };
    close(points[0], [0.1, 0.1]);
    let depth = canvas.editor.history_depths().0;
    canvas.click([0.7, 0.45]);
    canvas.click([0.7, 0.45]);
    let RegionShape::Polygon { points } = &canvas.editor.recipe.regions[0].shape else {
        unreachable!()
    };
    assert_eq!(points.len(), 5);
    assert_eq!(canvas.editor.history_depths().0, depth + 1);
    canvas.key(Key::Delete, true);
    let RegionShape::Polygon { points } = &canvas.editor.recipe.regions[0].shape else {
        unreachable!()
    };
    assert_eq!(points.len(), 4);
    assert_eq!(canvas.editor.history_depths().0, depth + 2);
    assert!(canvas.editor.undo());
    let RegionShape::Polygon { points } = &canvas.editor.recipe.regions[0].shape else {
        unreachable!()
    };
    assert_eq!(points.len(), 5);
}

#[test]
fn modifiers_yield_the_canvas_and_focus_loss_cancels_without_mutation() {
    let mut canvas = Canvas::new();
    canvas.editor.set_tool(DrawingTool::Polygon);
    canvas.click([0.2, 0.2]);
    canvas.key(Key::Space, true);
    assert!(!canvas.editor.owns_canvas(&canvas.ctx));
    assert_eq!(canvas.editor.polygon.len(), 1);
    canvas.key(Key::Space, false);
    assert!(canvas.editor.owns_canvas(&canvas.ctx));
    canvas.frame(vec![], egui::Modifiers::ALT);
    assert!(!canvas.editor.owns_canvas(&canvas.ctx));
    assert_eq!(canvas.editor.polygon.len(), 1);
    canvas.frame(vec![], Default::default());
    canvas.editor.set_tool(DrawingTool::Lasso);
    canvas.pointer([0.2, 0.2], None);
    canvas.pointer([0.2, 0.2], Some(true));
    canvas.pointer([0.7, 0.7], None);
    let _ = canvas.ctx.run(
        egui::RawInput {
            focused: false,
            ..Default::default()
        },
        |ctx| {
            egui::CentralPanel::default().show(ctx, |ui| {
                canvas.editor.draw_overlay(ui, (canvas.image, canvas.clip))
            });
        },
    );
    assert!(canvas.editor.region_interaction.gesture.is_none());
    assert!(canvas.editor.recipe.regions.is_empty());
}

#[test]
fn select_yields_empty_image_and_wheel_but_region_drag_stays_an_edit() {
    let mut canvas = Canvas::new();
    canvas.editor.set_tool(DrawingTool::Rectangle);
    canvas.drag([0.3, 0.3], [0.6, 0.6]);
    let original = canvas.editor.recipe.clone();
    canvas.pointer([0.1, 0.1], Some(true));
    assert!(
        !canvas.editor.region_interaction.owns_pointer,
        "empty image must allow plain pan"
    );
    canvas.pointer([0.45, 0.45], None);
    assert!(
        !canvas.editor.region_interaction.owns_pointer,
        "a pan cannot turn into region movement halfway through"
    );
    canvas.pointer([0.45, 0.45], Some(false));
    assert_eq!(canvas.editor.recipe, original);
    canvas.frame(
        vec![egui::Event::MouseWheel {
            unit: egui::MouseWheelUnit::Point,
            delta: egui::vec2(0.0, 40.0),
            modifiers: Default::default(),
        }],
        Default::default(),
    );
    assert!(
        !canvas.editor.region_interaction.owns_pointer,
        "wheel over a region must zoom without a modifier"
    );
    // A new press must win while the previous wheel still has inertia.
    canvas.pointer([0.45, 0.45], Some(true));
    assert!(
        canvas.ctx.input(|i| i.smooth_scroll_delta != Vec2::ZERO),
        "fixture must actually retain wheel inertia"
    );
    assert!(canvas.editor.region_interaction.owns_pointer);
    canvas.pointer([0.5, 0.5], None);
    canvas.pointer([0.5, 0.5], Some(false));
    assert_ne!(
        canvas.editor.recipe, original,
        "the same region must still be movable"
    );
}

#[test]
fn double_click_region_fits_photo_except_on_an_insertable_polygon_edge() {
    for shape in [
        RegionShape::Ellipse {
            center: [0.4, 0.4],
            radius: [0.2, 0.2],
        },
        RegionShape::Rectangle {
            min: [0.2, 0.2],
            max: [0.6, 0.6],
        },
        RegionShape::Polygon {
            points: vec![[0.2, 0.2], [0.6, 0.2], [0.6, 0.6], [0.2, 0.6]],
        },
    ] {
        let mut canvas = Canvas::new();
        canvas.editor.add_region(shape).unwrap();
        let original = canvas.editor.recipe.clone();
        let history = canvas.editor.history_depths();
        canvas.click([0.4, 0.4]);
        assert!(
            !canvas.editor.fit_view_requested,
            "a single click still selects"
        );
        canvas.click([0.4, 0.4]);
        assert!(
            canvas.editor.fit_view_requested,
            "region interior must not swallow photograph reset"
        );
        assert_eq!(canvas.editor.recipe, original);
        assert_eq!(canvas.editor.history_depths(), history);
    }
    let mut canvas = Canvas::new();
    canvas
        .editor
        .add_region(RegionShape::Polygon {
            points: vec![[0.2, 0.2], [0.6, 0.2], [0.6, 0.6], [0.2, 0.6]],
        })
        .unwrap();
    let original = canvas.editor.recipe.clone();
    canvas.click([0.4, 0.2]);
    canvas.click([0.4, 0.2]);
    let RegionShape::Polygon { points } = &canvas.editor.recipe.regions[0].shape else {
        panic!()
    };
    assert_eq!(
        points.len(),
        5,
        "polygon edge keeps its vertex-insertion gesture"
    );
    assert!(
        !canvas.editor.fit_view_requested,
        "local geometry edit must not also reset view"
    );
    assert!(canvas.editor.undo());
    assert_eq!(canvas.editor.recipe, original);
}

#[test]
fn whole_photograph_scope_keeps_regions_and_cancels_unfinished_drawing() {
    let mut canvas = Canvas::new();
    canvas.editor.set_tool(DrawingTool::Rectangle);
    canvas.drag([0.2, 0.2], [0.6, 0.6]);
    let recipe = canvas.editor.recipe.clone();
    assert!(canvas.editor.selected.is_some());
    canvas.editor.set_tool(DrawingTool::Polygon);
    canvas.click([0.1, 0.1]);
    assert!(!canvas.editor.polygon.is_empty());
    canvas.editor.select_photograph();
    assert!(canvas.editor.selected.is_none());
    assert!(canvas.editor.polygon.is_empty());
    assert_eq!(canvas.editor.tool, DrawingTool::Select);
    assert_eq!(canvas.editor.recipe, recipe);
}

#[test]
fn lasso_storage_is_bounded_and_zoomed_mapping_keeps_global_coordinates() {
    let mut points = Vec::new();
    let image = Rect::from_min_size(Pos2::ZERO, Vec2::splat(20000.0));
    for i in 0..10000 {
        let angle = i as f32 * std::f32::consts::TAU / 10000.0;
        append_lasso(
            &mut points,
            [0.5 + angle.cos() * 0.4, 0.5 + angle.sin() * 0.4],
            image,
        );
    }
    assert!(points.len() <= 2048);
    let simplified = simplify_lasso(&points, image);
    assert!((3..=256).contains(&simplified.len()));
    RegionShape::Polygon { points: simplified }
        .validate()
        .unwrap();
    let mut canvas = Canvas::new();
    canvas.image = Rect::from_min_max(egui::pos2(-400.0, -300.0), egui::pos2(1200.0, 900.0));
    canvas.editor.set_tool(DrawingTool::Rectangle);
    canvas.drag([0.3, 0.3], [0.6, 0.6]);
    let bounds = shape_bounds(&canvas.editor.recipe.regions[0].shape);
    close(bounds[0], [0.3, 0.3]);
    close(bounds[1], [0.6, 0.6]);
}

#[test]
fn click_slop_and_superseding_recipe_never_commit_a_stale_geometry_gesture() {
    let mut canvas = Canvas::new();
    canvas
        .editor
        .add_region(RegionShape::Rectangle {
            min: [0.2, 0.2],
            max: [0.6, 0.6],
        })
        .unwrap();
    let before = canvas.editor.recipe.clone();
    let depth = canvas.editor.history_depths();
    canvas.drag([0.4, 0.4], [0.402, 0.401]);
    assert_eq!(
        canvas.editor.recipe, before,
        "Sub-click motion must not move a selected region"
    );
    assert_eq!(canvas.editor.history_depths(), depth);
    canvas.pointer([0.4, 0.4], None);
    canvas.pointer([0.4, 0.4], Some(true));
    canvas.pointer([0.5, 0.5], None);
    let mut replacement = before;
    replacement.regions[0].adjustments.exposure = 1.0;
    canvas.editor.replace(replacement.clone()).unwrap();
    canvas.pointer([0.5, 0.5], Some(false));
    assert_eq!(
        canvas.editor.recipe, replacement,
        "Agent/sidebar edits supersede an unfinished geometry draft"
    );
}

#[test]
fn resizing_a_clipped_ellipse_preserves_its_untouched_axis() {
    for (center, radius, from, to, untouched) in [
        ([0.05, 0.5], [0.30, 0.20], [0.05, 0.3], [0.05, 0.2], 0),
        ([0.5, 0.05], [0.20, 0.30], [0.7, 0.05], [0.8, 0.05], 1),
        ([0.95, 0.5], [0.30, 0.20], [0.95, 0.7], [0.95, 0.8], 0),
    ] {
        let mut canvas = Canvas::new();
        canvas
            .editor
            .add_region(RegionShape::Ellipse { center, radius })
            .unwrap();
        let original = canvas.editor.recipe.clone();
        canvas.drag(from, to);
        let RegionShape::Ellipse {
            center: changed_center,
            radius: changed_radius,
        } = canvas.editor.recipe.regions[0].shape
        else {
            unreachable!()
        };
        assert_eq!(changed_center[untouched], center[untouched]);
        assert_eq!(changed_radius[untouched], radius[untouched]);
        assert_ne!(
            changed_radius[1 - untouched],
            radius[1 - untouched],
            "The fixture must actually resize the other axis"
        );
        canvas.editor.recipe.validate().unwrap();
        assert!(canvas.editor.undo());
        assert_eq!(canvas.editor.recipe, original);
    }
}

#[test]
fn undo_redo_and_replacement_clear_missing_region_selection() {
    let mut canvas = Canvas::new();
    let id = canvas
        .editor
        .add_region(RegionShape::Rectangle {
            min: [0.2, 0.2],
            max: [0.6, 0.6],
        })
        .unwrap();
    assert_eq!(canvas.editor.selected.as_deref(), Some(id.as_str()));
    assert!(canvas.editor.undo());
    assert!(canvas.editor.selected.is_none());
    assert!(canvas.editor.redo());
    canvas.editor.selected = Some(id.clone());
    let mut removed = canvas.editor.recipe.clone();
    removed.regions.clear();
    canvas.editor.replace(removed).unwrap();
    assert!(canvas.editor.selected.is_none());
    assert!(canvas.editor.undo());
    canvas.editor.selected = Some(id);
    assert!(canvas.editor.redo());
    assert!(canvas.editor.selected.is_none());
}

#[test]
fn escape_belongs_to_focused_text_before_it_cancels_polygon_drawing() {
    let mut canvas = Canvas::new();
    canvas.editor.set_tool(DrawingTool::Polygon);
    canvas.click([0.2, 0.2]);
    canvas.click([0.6, 0.2]);
    let draft = canvas.editor.polygon.clone();
    let name = egui::Id::new("actual-region-name-editor");
    let mut text = String::from("Region");
    let _ = canvas.ctx.run(
        egui::RawInput {
            screen_rect: Some(canvas.clip),
            ..Default::default()
        },
        |ctx| {
            egui::CentralPanel::default().show(ctx, |ui| {
                ui.add(egui::TextEdit::singleline(&mut text).id(name))
                    .request_focus();
                canvas.editor.draw_overlay(ui, (canvas.image, canvas.clip));
            });
        },
    );
    assert!(text_editor_focused(&canvas.ctx));
    canvas.key(Key::Escape, true);
    assert_eq!(
        canvas.editor.polygon, draft,
        "Text cancellation must not cancel the canvas draft too"
    );
    canvas.ctx.memory_mut(|m| m.surrender_focus(name));
    canvas.key(Key::Escape, false);
    canvas.key(Key::Escape, true);
    assert!(canvas.editor.polygon.is_empty());
    assert!(canvas.editor.recipe.regions.is_empty());
}

#[test]
fn an_edge_crossing_ellipse_can_move_without_changing_its_radii() {
    let mut canvas = Canvas::new();
    let shape = RegionShape::Ellipse {
        center: [0.05, 0.5],
        radius: [0.3, 0.2],
    };
    let id = canvas.editor.add_region(shape).unwrap();
    canvas.drag([0.15, 0.5], [0.12, 0.5]);
    let RegionShape::Ellipse { center, radius } = canvas
        .editor
        .recipe
        .regions
        .iter()
        .find(|r| r.id == id)
        .unwrap()
        .shape
    else {
        panic!()
    };
    assert!((center[0] - 0.02).abs() < 1e-5);
    assert_eq!(radius, [0.3, 0.2]);
}

#[test]
fn magic_lasso_pointer_release_refines_the_drawn_enclosure_into_editable_detail() {
    let mut canvas = Canvas::new();
    let mut pixels = vec![0.05; 96 * 72 * 3];
    for y in 23..50 {
        for x in 30..65 {
            for c in 0..3 {
                pixels[(y * 96 + x) * 3 + c] = 0.8;
            }
        }
    }
    let image = Arc::new(LinearImage {
        width: 96,
        height: 72,
        pixels,
        origin: strehl_edit::ImageOrigin::SceneLinear,
        baseline: None,
        baked_recipe: None,
    });
    canvas.editor.loaded = Some(LoadedPhoto {
        image: image.clone(),
        preview: image,
        recipe: Default::default(),
        source: "magic-pointer-fixture".into(),
        warnings: vec![],
    });
    canvas.editor.set_tool(DrawingTool::MagicLasso);
    canvas.pointer([0.1, 0.1], None);
    canvas.pointer([0.1, 0.1], Some(true));
    for point in [[0.9, 0.1], [0.9, 0.9], [0.1, 0.9], [0.1, 0.1]] {
        canvas.pointer(point, None);
    }
    assert!(
        canvas.editor.recipe.regions.is_empty(),
        "Drawing is only an enclosure draft"
    );
    canvas.pointer([0.1, 0.1], Some(false));
    assert!(
        canvas.editor.magic_pending(),
        "Pointer release must start actual segmentation"
    );
    let until = Instant::now() + Duration::from_secs(5);
    while canvas.editor.magic_pending() && Instant::now() < until {
        canvas.frame(vec![], Default::default());
        canvas.editor.poll_magic(&canvas.ctx);
        std::thread::sleep(Duration::from_millis(2));
    }
    assert!(!canvas.editor.magic_pending());
    assert_eq!(canvas.editor.recipe.regions.len(), 1);
    let region = &canvas.editor.recipe.regions[0];
    assert!(region.shape.contains([0.5, 0.5]));
    assert!(
        !region.shape.contains([0.2, 0.2]),
        "The result must not be the original lasso"
    );
    assert!(matches!(&region.shape,RegionShape::Polygon{points} if points.len()>=4));
    assert_eq!(canvas.editor.tool, DrawingTool::Select);
    assert_eq!(canvas.editor.selected.as_ref(), Some(&region.id));
    assert_eq!(canvas.editor.history_depths(), (1, 0));
    assert!(canvas.editor.undo());
    assert!(canvas.editor.recipe.regions.is_empty());
}

#[test]
fn close_polygon_handles_pick_the_nearest_vertex_not_the_first_in_the_path() {
    let mut canvas = Canvas::new();
    canvas
        .editor
        .add_region(RegionShape::Polygon {
            points: vec![[0.3, 0.3], [0.305, 0.3], [0.6, 0.6], [0.3, 0.6]],
        })
        .unwrap();
    canvas.drag([0.305, 0.3], [0.35, 0.27]);
    let RegionShape::Polygon { points } = &canvas.editor.recipe.regions[0].shape else {
        panic!()
    };
    assert_eq!(points[0], [0.3, 0.3]);
    assert!((points[1][0] - 0.35).abs() < 1e-5 && (points[1][1] - 0.27).abs() < 1e-5);
}

#[test]
fn an_unfocused_canvas_keeps_existing_annotations_visible_without_accepting_edits() {
    let mut canvas = Canvas::new();
    canvas
        .editor
        .add_region(RegionShape::Ellipse {
            center: [0.5, 0.5],
            radius: [0.2, 0.2],
        })
        .unwrap();
    let before = canvas.editor.recipe.clone();
    let at = canvas.at([0.5, 0.5]);
    let output = canvas.ctx.run(
        egui::RawInput {
            screen_rect: Some(canvas.clip),
            focused: false,
            events: vec![
                egui::Event::PointerMoved(at),
                egui::Event::PointerButton {
                    pos: at,
                    button: egui::PointerButton::Primary,
                    pressed: true,
                    modifiers: Default::default(),
                },
            ],
            ..Default::default()
        },
        |ctx| {
            egui::CentralPanel::default()
                .frame(egui::Frame::NONE)
                .show(ctx, |ui| {
                    canvas.editor.draw_overlay(ui, (canvas.image, canvas.clip))
                });
        },
    );
    assert_eq!(canvas.editor.recipe, before);
    assert!(canvas.editor.region_interaction.gesture.is_none());
    assert!(
        output.shapes.iter().any(
            |shape| matches!(&shape.shape,Shape::Path(path) if path.closed && path.points.len()>8)
        ),
        "A persistent ellipse outline must remain visible when input is not owned"
    );
}
