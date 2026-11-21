use super::*;
use strehl_edit::{
    Backdrop, Heal, RegionShape, ScaleBar, ScaleBarCorner, ScaleBarStyle, SourceRange,
};

fn region(id: &str, shape: RegionShape) -> RegionAdjustment {
    RegionAdjustment {
        id: id.into(),
        name: id.into(),
        note: String::new(),
        shape,
        feather: 0.4,
        enabled: true,
        adjustments: Adjustments::default(),
        source_range: None,
    }
}

fn recipe() -> DevelopmentRecipe {
    let mut glints = region(
        "Glints",
        RegionShape::Ellipse {
            center: [0.6, 0.4],
            radius: [0.1, 0.1],
        },
    );
    glints.adjustments.highlights = -25.0;
    let mut repair = region(
        "Leg joint",
        RegionShape::Stroke {
            points: vec![[0.3, 0.6], [0.32, 0.62]],
            radius: [0.02, 0.03],
        },
    );
    repair.source_range = Some(SourceRange {
        first: 115,
        last: 131,
    });
    let mut note = region(
        "Note 1",
        RegionShape::Ellipse {
            center: [0.2, 0.2],
            radius: [0.01, 0.01],
        },
    );
    note.note = "Check the antenna tip against plane 140".into();
    DevelopmentRecipe {
        regions: vec![glints, repair, note],
        heals: vec![
            Heal {
                center: [0.5, 0.5],
                radius: [0.01, 0.01],
                source_offset: [0.03, 0.0],
                enabled: true,
            };
            3
        ],
        backdrop: Some(Backdrop {
            threshold: 0.012,
            softness: 1.0,
            key: BackdropKey::Dark,
            enabled: true,
        }),
        scale_bar: Some(ScaleBar {
            length_um: 1000.0,
            corner: ScaleBarCorner::BottomRight,
            style: ScaleBarStyle::Light,
            enabled: true,
        }),
        ..Default::default()
    }
}

#[test]
fn rows_list_every_layer_top_first_with_the_mockup_details() {
    let rows = layer_rows(&recipe(), |r| r.id == "Leg joint");
    let titles: Vec<&str> = rows.iter().map(|r| r.title.as_str()).collect();
    assert_eq!(
        titles,
        [
            "Note 1",
            "Leg joint",
            "Glints",
            "Dust",
            "Backdrop",
            "Scale bar"
        ]
    );
    let detail = |title: &str| {
        rows.iter()
            .find(|r| r.title == title)
            .unwrap()
            .detail
            .clone()
    };
    assert_eq!(
        detail("Glints"),
        "Region · highlights \u{2212}25 · feather 0.4"
    );
    assert_eq!(detail("Leg joint"), "Depth repair · planes 116\u{2013}132");
    assert_eq!(detail("Dust"), "Heal · 3 spots");
    assert_eq!(detail("Backdrop"), "Clean to black below 1.2 % · soft edge");
    assert_eq!(detail("Scale bar"), "1 mm · bottom right · added on export");
    assert!(detail("Note 1").starts_with("Note · Check the antenna"));
    let repair = rows.iter().find(|r| r.title == "Leg joint").unwrap();
    assert_eq!(
        (repair.kind, repair.pending),
        (LayerKind::DepthRepair, true)
    );
    assert!(rows.iter().filter(|r| r.movable).count() == 3);
}

#[test]
fn moving_a_layer_changes_tone_order_and_never_the_repair_list() {
    let recipe = recipe();
    // Glints is the bottom region (applied first); move it to the top.
    let next = apply_layer_intent(&recipe, &LayerIntent::MoveTo("Glints".into(), 0))
        .unwrap()
        .unwrap();
    let titles: Vec<String> = layer_rows(&next, |_| false)
        .into_iter()
        .map(|r| r.title)
        .collect();
    assert_eq!(&titles[..3], ["Glints", "Note 1", "Leg joint"]);
    assert_eq!(
        *next.application_order().last().unwrap(),
        0,
        "top is applied last"
    );
    assert_eq!(
        next.regions.iter().map(|r| &r.id).collect::<Vec<_>>(),
        recipe.regions.iter().map(|r| &r.id).collect::<Vec<_>>(),
        "list order is the engine's repair-blend order and stays"
    );
    // Moving it back restores the plain list order and clears layers_order.
    let back = apply_layer_intent(&next, &LayerIntent::MoveTo("Glints".into(), 2))
        .unwrap()
        .unwrap();
    assert!(back.layers_order.is_empty());
    assert!(apply_layer_intent(&recipe, &LayerIntent::MoveTo("missing".into(), 0)).is_err());
}

#[test]
fn eyes_hide_finishing_layers_and_remove_clears_them() {
    let recipe = recipe();
    for id in [
        LayerId::Heals,
        LayerId::Backdrop,
        LayerId::ScaleBar,
        LayerId::Region("Glints".into()),
    ] {
        let hidden = apply_layer_intent(&recipe, &LayerIntent::SetVisible(id.clone(), false))
            .unwrap()
            .unwrap();
        let row = layer_rows(&hidden, |_| false)
            .into_iter()
            .find(|r| r.id == id)
            .unwrap();
        assert!(!row.visible, "{id:?}");
        let removed = apply_layer_intent(&recipe, &LayerIntent::Remove(id.clone()))
            .unwrap()
            .unwrap();
        assert!(layer_rows(&removed, |_| false).iter().all(|r| r.id != id));
    }
    let hidden = apply_layer_intent(&recipe, &LayerIntent::SetVisible(LayerId::Heals, false))
        .unwrap()
        .unwrap();
    assert!(!hidden.has_neighbourhood() || hidden.backdrop.is_some());
    assert!(hidden.heals.iter().all(|h| !h.enabled));
    assert_eq!(
        apply_layer_intent(&recipe, &LayerIntent::Select(LayerId::Heals)).unwrap(),
        None
    );
}

#[test]
fn the_panel_draws_every_row_and_answers_an_eye_click() {
    let ctx = egui::Context::default();
    let rows = layer_rows(&recipe(), |_| false);
    let mut eye = None;
    let mut first = Vec::new();
    for frame in 0..3 {
        let mut input = egui::RawInput {
            screen_rect: Some(Rect::from_min_size(
                egui::Pos2::ZERO,
                egui::vec2(348.0, 900.0),
            )),
            ..Default::default()
        };
        if frame == 1 {
            let at = eye.unwrap();
            input.events.push(egui::Event::PointerMoved(at));
            input.events.push(egui::Event::PointerButton {
                pos: at,
                button: egui::PointerButton::Primary,
                pressed: true,
                modifiers: Default::default(),
            });
            input.events.push(egui::Event::PointerButton {
                pos: at,
                button: egui::PointerButton::Primary,
                pressed: false,
                modifiers: Default::default(),
            });
        }
        let mut intents = Vec::new();
        let output = ctx.run(input, |ctx| {
            egui::CentralPanel::default().show(ctx, |ui| {
                intents = layers_panel(ui, &StudioPalette::GRAPHITE, &rows, None, None);
            });
        });
        if frame == 0 {
            let texts: Vec<String> = output
                .shapes
                .iter()
                .filter_map(|s| match &s.shape {
                    egui::Shape::Text(t) => Some(t.galley.text().to_owned()),
                    _ => None,
                })
                .collect();
            for row in &rows {
                assert!(
                    texts.iter().any(|t| t == &row.title),
                    "{} not drawn",
                    row.title
                );
            }
            // The first row's eye sits 8 px in from the left at the row's middle.
            let top = output
                .shapes
                .iter()
                .find_map(|s| match &s.shape {
                    egui::Shape::Text(t) if t.galley.text() == rows[0].title => Some(t.pos.y),
                    _ => None,
                })
                .unwrap();
            eye = Some(egui::pos2(8.0 + 8.0, top + 9.0));
            first = intents;
        } else if frame == 1 {
            assert_eq!(
                intents,
                vec![LayerIntent::SetVisible(rows[0].id.clone(), false)]
            );
        }
    }
    assert!(first.is_empty(), "drawing alone raises nothing");
}
