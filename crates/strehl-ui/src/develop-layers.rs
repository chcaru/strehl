//! The Layers tab: regions, depth repairs, notes, heals, the backdrop and the
//! scale bar in one list, each with an eye. Region order is the recipe's tone
//! application order (`layers_order`), shown top first: the top layer is
//! applied last. Heals and the backdrop run before every region and the scale
//! bar after, so those rows keep their place.
use super::style::{self, Icon, Mark, StudioPalette};
use eframe::egui::{self, Align2, CornerRadius, Rect, Sense, Ui};
use strehl_edit::{Adjustments, BackdropKey, DevelopmentRecipe, RegionAdjustment};

#[derive(Clone, Debug, PartialEq, Eq, Hash)]
pub(crate) enum LayerId {
    Region(String),
    Heals,
    Backdrop,
    ScaleBar,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(crate) enum LayerKind {
    Region,
    DepthRepair,
    Note,
    Heal,
    Backdrop,
    ScaleBar,
}

impl LayerKind {
    pub(crate) fn icon(self) -> Icon {
        match self {
            Self::Region => Icon::Shape,
            Self::DepthRepair => Icon::Brush,
            Self::Note => Icon::Note,
            Self::Heal => Icon::Heal,
            Self::Backdrop => Icon::Backdrop,
            Self::ScaleBar => Icon::Ruler,
        }
    }

    pub(crate) fn finishing(self) -> bool {
        matches!(self, Self::Heal | Self::Backdrop | Self::ScaleBar)
    }
}

#[derive(Clone, Debug, PartialEq)]
pub(crate) struct LayerRow {
    pub id: LayerId,
    pub kind: LayerKind,
    pub title: String,
    pub detail: String,
    pub visible: bool,
    /// Regions only: they can move within the tone order.
    pub movable: bool,
    /// A depth repair the current master does not hold yet.
    pub pending: bool,
}

/// What kind of layer a region is. A depth repair carries a source range; a
/// note is a region that changes nothing and says something.
pub(crate) fn region_kind(region: &RegionAdjustment) -> LayerKind {
    if region.source_range.is_some() {
        LayerKind::DepthRepair
    } else if region.adjustments == Adjustments::default() && !region.note.trim().is_empty() {
        LayerKind::Note
    } else {
        LayerKind::Region
    }
}

fn adjustment_summary(a: &Adjustments) -> String {
    let fields = [
        ("exposure", a.exposure, true),
        ("contrast", a.contrast, false),
        ("highlights", a.highlights, false),
        ("shadows", a.shadows, false),
        ("whites", a.whites, false),
        ("blacks", a.blacks, false),
        ("vibrance", a.vibrance, false),
        ("saturation", a.saturation, false),
        ("warmth", a.temperature, false),
        ("tint", a.tint, false),
    ];
    let set: Vec<String> = fields
        .iter()
        .filter(|(_, v, _)| v.abs() > 1e-4)
        .take(2)
        .map(|(name, v, stops)| {
            if *stops {
                format!("{name} {v:+.2}")
            } else {
                format!("{name} {}", style::format_number(*v, style::Number::Signed))
            }
            .replace('-', "\u{2212}")
        })
        .collect();
    if set.is_empty() {
        "no change".into()
    } else {
        set.join(" · ")
    }
}

/// Planes are counted from 1 on screen; source ranges are zero-based.
pub(crate) fn plane_range(first: usize, last: usize) -> String {
    format!("planes {}\u{2013}{}", first + 1, last + 1)
}

/// The rows of the Layers tab, top first. `pending` says whether a region's
/// repair is waiting for its re-stack.
pub(crate) fn layer_rows(
    recipe: &DevelopmentRecipe,
    pending: impl Fn(&RegionAdjustment) -> bool,
) -> Vec<LayerRow> {
    let mut rows = Vec::new();
    for index in recipe.application_order().into_iter().rev() {
        let region = &recipe.regions[index];
        let kind = region_kind(region);
        let detail = match kind {
            LayerKind::DepthRepair => {
                let range = region.source_range.as_ref().unwrap();
                format!("Depth repair · {}", plane_range(range.first, range.last))
            }
            LayerKind::Note => {
                let mut note: String = region.note.trim().chars().take(48).collect();
                if region.note.trim().chars().count() > 48 {
                    note.push('…');
                }
                format!("Note · {note}")
            }
            _ => format!(
                "Region · {} · feather {:.1}",
                adjustment_summary(&region.adjustments),
                region.feather
            ),
        };
        rows.push(LayerRow {
            id: LayerId::Region(region.id.clone()),
            kind,
            title: region.name.clone(),
            detail,
            visible: region.enabled,
            movable: true,
            pending: kind == LayerKind::DepthRepair && pending(region),
        });
    }
    if !recipe.heals.is_empty() {
        let spots = recipe.heals.len();
        rows.push(LayerRow {
            id: LayerId::Heals,
            kind: LayerKind::Heal,
            title: "Dust".into(),
            detail: format!("Heal · {spots} spot{}", if spots == 1 { "" } else { "s" }),
            visible: recipe.heals.iter().any(|h| h.enabled),
            movable: false,
            pending: false,
        });
    }
    if let Some(backdrop) = recipe.backdrop {
        let level = format!("{:.1} %", backdrop.threshold * 100.0);
        let edge = if backdrop.softness > 0.0 {
            "soft edge"
        } else {
            "hard edge"
        };
        rows.push(LayerRow {
            id: LayerId::Backdrop,
            kind: LayerKind::Backdrop,
            title: "Backdrop".into(),
            detail: match backdrop.key {
                BackdropKey::Dark => format!("Clean to black below {level} · {edge}"),
                BackdropKey::Light => format!("Smooth above {level} · {edge}"),
            },
            visible: backdrop.enabled,
            movable: false,
            pending: false,
        });
    }
    if let Some(bar) = recipe.scale_bar {
        let corner = match bar.corner {
            strehl_edit::ScaleBarCorner::TopLeft => "top left",
            strehl_edit::ScaleBarCorner::TopRight => "top right",
            strehl_edit::ScaleBarCorner::BottomLeft => "bottom left",
            strehl_edit::ScaleBarCorner::BottomRight => "bottom right",
        };
        rows.push(LayerRow {
            id: LayerId::ScaleBar,
            kind: LayerKind::ScaleBar,
            title: "Scale bar".into(),
            detail: format!("{} · {corner} · added on export", bar.label()),
            visible: bar.enabled,
            movable: false,
            pending: false,
        });
    }
    rows
}

#[derive(Clone, Debug, PartialEq)]
pub(crate) enum LayerIntent {
    Select(LayerId),
    SetVisible(LayerId, bool),
    Remove(LayerId),
    /// Move a region to this position among region rows, counted from the top.
    MoveTo(String, usize),
}

/// Apply a layer intent to a recipe. `Select` changes nothing here.
pub(crate) fn apply_layer_intent(
    recipe: &DevelopmentRecipe,
    intent: &LayerIntent,
) -> anyhow::Result<Option<DevelopmentRecipe>> {
    let mut next = recipe.clone();
    match intent {
        LayerIntent::Select(_) => return Ok(None),
        LayerIntent::SetVisible(id, visible) => match id {
            LayerId::Region(id) => {
                next.regions
                    .iter_mut()
                    .find(|r| &r.id == id)
                    .ok_or_else(|| anyhow::anyhow!("This layer no longer exists"))?
                    .enabled = *visible;
            }
            LayerId::Heals => next.heals.iter_mut().for_each(|h| h.enabled = *visible),
            LayerId::Backdrop => {
                if let Some(b) = &mut next.backdrop {
                    b.enabled = *visible;
                }
            }
            LayerId::ScaleBar => {
                if let Some(b) = &mut next.scale_bar {
                    b.enabled = *visible;
                }
            }
        },
        LayerIntent::Remove(id) => match id {
            LayerId::Region(id) => {
                next.remove_region(id)
                    .ok_or_else(|| anyhow::anyhow!("This layer no longer exists"))?;
            }
            LayerId::Heals => next.heals.clear(),
            LayerId::Backdrop => next.backdrop = None,
            LayerId::ScaleBar => next.scale_bar = None,
        },
        LayerIntent::MoveTo(id, from_top) => {
            // Top first on screen is last applied.
            let regions = next.regions.len();
            anyhow::ensure!(
                next.regions.iter().any(|r| &r.id == id),
                "This layer no longer exists"
            );
            let application_index = regions.saturating_sub(1).saturating_sub(*from_top);
            next.move_layer(id, application_index)?;
        }
    }
    next.validate()?;
    Ok((next != *recipe).then_some(next))
}

/// Paint the Layers tab. Rows are plain shapes; nothing here is cached
/// because a list of at most 128 regions is a handful of shapes.
pub(crate) fn layers_panel(
    ui: &mut Ui,
    pal: &StudioPalette,
    rows: &[LayerRow],
    selected: Option<&str>,
    repair_status: Option<&str>,
) -> Vec<LayerIntent> {
    let mut intents = Vec::new();
    style::sect(
        ui,
        pal,
        "Layers, top first",
        Some("each can be hidden or removed"),
    );
    if rows.is_empty() {
        style::text(
            ui,
            "No layers yet. Paint a depth repair, draw a region, heal dust, clean the backdrop or add a scale bar.",
            style::SMALL,
            pal.ink_2,
        );
    }
    let regions = rows.iter().filter(|r| r.movable).count();
    let mut region_index = 0usize;
    for row in rows {
        let width = ui.available_width();
        let (rect, response) = ui.allocate_exact_size(egui::vec2(width, 54.0), Sense::click());
        let on = matches!(&row.id, LayerId::Region(id) if Some(id.as_str()) == selected);
        let painter = ui.painter();
        if on {
            painter.rect_filled(
                Rect::from_min_size(rect.min, egui::vec2(2.0, rect.height())),
                CornerRadius::ZERO,
                pal.accent,
            );
        } else if response.hovered() {
            painter.rect_filled(rect, CornerRadius::ZERO, pal.raised);
        }
        style::hairline(painter, rect.left_bottom(), rect.right_bottom(), pal.line);
        let left = rect.left() + if on { 10.0 } else { 0.0 };
        let eye = Rect::from_center_size(
            egui::pos2(left + 8.0, rect.center().y),
            egui::vec2(15.0, 15.0),
        );
        let kind = Rect::from_center_size(
            egui::pos2(left + 33.0, rect.center().y),
            egui::vec2(15.0, 15.0),
        );
        style::icon(
            painter,
            eye,
            Icon::Eye,
            if row.visible { pal.ink_2 } else { pal.line_2 },
        );
        if !row.visible {
            style::hairline(painter, eye.left_bottom(), eye.right_top(), pal.ink_3);
        }
        style::icon(
            painter,
            kind,
            row.kind.icon(),
            if row.kind == LayerKind::DepthRepair {
                pal.accent
            } else {
                pal.ink_3
            },
        );
        let text_left = left + 50.0;
        style::paint_text(
            painter,
            egui::pos2(text_left, rect.center().y - 9.0),
            Align2::LEFT_CENTER,
            &row.title,
            style::BODY,
            if row.visible { pal.ink } else { pal.ink_3 },
        );
        style::paint_text(
            painter,
            egui::pos2(text_left, rect.center().y + 9.0),
            Align2::LEFT_CENTER,
            &row.detail,
            style::SMALL,
            pal.ink_2,
        );
        if row.pending {
            let status = repair_status.unwrap_or("waiting");
            let end = style::paint_text(
                painter,
                egui::pos2(rect.right() - 4.0, rect.center().y - 9.0),
                Align2::RIGHT_CENTER,
                status,
                style::SMALL,
                pal.ink_2,
            );
            style::mark(
                painter,
                egui::pos2(end.left() - 8.0, end.center().y),
                Mark::Run,
                pal,
            );
        }
        let eye_hit = ui.interact(
            eye.expand(4.0),
            ui.id().with(("eye", &row.id)),
            Sense::click(),
        );
        if eye_hit.clicked() {
            intents.push(LayerIntent::SetVisible(row.id.clone(), !row.visible));
        } else if response.clicked() {
            intents.push(LayerIntent::Select(row.id.clone()));
        }
        response.context_menu(|ui| {
            if row.movable {
                if region_index > 0
                    && ui.button("Move up").clicked()
                    && let LayerId::Region(id) = &row.id
                {
                    intents.push(LayerIntent::MoveTo(id.clone(), region_index - 1));
                    ui.close();
                }
                if region_index + 1 < regions
                    && ui.button("Move down").clicked()
                    && let LayerId::Region(id) = &row.id
                {
                    intents.push(LayerIntent::MoveTo(id.clone(), region_index + 1));
                    ui.close();
                }
            }
            if ui
                .button(if row.visible { "Hide" } else { "Show" })
                .clicked()
            {
                intents.push(LayerIntent::SetVisible(row.id.clone(), !row.visible));
                ui.close();
            }
            if ui.button("Remove").clicked() {
                intents.push(LayerIntent::Remove(row.id.clone()));
                ui.close();
            }
        });
        if row.movable {
            region_index += 1;
        }
    }
    if rows.iter().any(|r| r.kind == LayerKind::DepthRepair) {
        ui.add_space(4.0);
        egui::Frame::NONE
            .fill(pal.raised)
            .stroke(egui::Stroke::new(1.0_f32, pal.line))
            .inner_margin(egui::Margin::symmetric(14, 12))
            .show(ui, |ui| {
                ui.label(
                    egui::RichText::new("A depth repair no longer blocks export.")
                        .size(12.5)
                        .strong()
                        .color(pal.ink),
                );
                style::text(
                    ui,
                    "The engine rebuilds it in the background. Until it finishes, exports use the last finished pixels and say so.",
                    12.5,
                    pal.ink_2,
                );
            });
    }
    intents
}

#[cfg(test)]
#[path = "develop-layers-tests.rs"]
mod tests;
