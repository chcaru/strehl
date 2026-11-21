//! The Library's management surfaces shared by the grid, the list and the
//! subject page: a context menu (square, ruled, keys on the right, one level
//! of submenus), the multi-selection model (Ctrl and Shift click, Ctrl A)
//! and the bar that shows what is selected and what can be done with it.
//!
//! The menu is drawn by the Library, not egui's popup, so it carries the
//! station's palette and can be opened offscreen for the look check. Its
//! entries are built once when it opens; painting allocates only the
//! galleys egui caches.
use crate::{
    library_paint::{self as paint, ButtonStyle, LibraryPalette},
    library_station::LibraryIntent,
    workspace_history::{Catalog, NodeId, NodeKind},
};
use eframe::egui::{self, Align2, CornerRadius, Pos2, Rect, Sense, Ui, Vec2};

const ITEM: f32 = 30.0;
const CAPTION: f32 = 26.0;
const SEPARATOR: f32 = 9.0;
const MIN_WIDTH: f32 = 228.0;
const MAX_WIDTH: f32 = 380.0;
const SUB_ROWS: usize = 12;
pub(crate) const BAR_HEIGHT: f32 = 46.0;

#[derive(Clone, Debug, PartialEq)]
pub(crate) struct SubItem {
    pub label: String,
    /// Dim text after the label ("Bugs", "4 stacks").
    pub detail: String,
    pub intent: LibraryIntent,
}
#[derive(Clone, Debug, PartialEq)]
pub(crate) enum MenuEntry {
    /// `intent: None` draws the item disabled.
    Item {
        label: String,
        key: Option<&'static str>,
        intent: Option<LibraryIntent>,
        danger: bool,
    },
    Sub {
        label: String,
        items: Vec<SubItem>,
    },
    Caption(String),
    Separator,
}
impl MenuEntry {
    pub(crate) fn item(label: impl Into<String>, intent: LibraryIntent) -> Self {
        Self::Item {
            label: label.into(),
            key: None,
            intent: Some(intent),
            danger: false,
        }
    }
    pub(crate) fn keyed(
        label: impl Into<String>,
        key: &'static str,
        intent: LibraryIntent,
    ) -> Self {
        Self::Item {
            label: label.into(),
            key: Some(key),
            intent: Some(intent),
            danger: false,
        }
    }
    pub(crate) fn disabled(label: impl Into<String>) -> Self {
        Self::Item {
            label: label.into(),
            key: None,
            intent: None,
            danger: false,
        }
    }
    pub(crate) fn danger(
        label: impl Into<String>,
        key: &'static str,
        intent: LibraryIntent,
    ) -> Self {
        Self::Item {
            label: label.into(),
            key: Some(key),
            intent: Some(intent),
            danger: true,
        }
    }
    fn height(&self) -> f32 {
        match self {
            Self::Item { .. } | Self::Sub { .. } => ITEM,
            Self::Caption(_) => CAPTION,
            Self::Separator => SEPARATOR,
        }
    }
}

#[derive(Clone, Debug, PartialEq)]
pub(crate) enum MenuOutcome {
    Open,
    /// Dismissed: Escape, or a press outside the menu.
    Closed,
    Chosen(LibraryIntent),
}

/// An open context menu.
#[derive(Clone, Debug)]
pub(crate) struct ContextMenu {
    pub at: Pos2,
    pub entries: Vec<MenuEntry>,
    /// The submenu shown beside its entry.
    pub open_sub: Option<usize>,
    /// The egui pass that opened it: that pass's press does not dismiss it.
    born: u64,
}
impl ContextMenu {
    pub(crate) fn new(ctx: &egui::Context, at: Pos2, entries: Vec<MenuEntry>) -> Self {
        Self {
            at,
            entries,
            open_sub: None,
            born: ctx.cumulative_pass_nr(),
        }
    }
    /// Opened during this egui pass and not shown yet: show it before the
    /// pass ends, so its first (invisible, sizing) pass is not the next one.
    pub(crate) fn is_new(&self, ctx: &egui::Context) -> bool {
        self.born == ctx.cumulative_pass_nr()
    }
    /// A menu opening upwards from `anchor` (a button along the bottom).
    pub(crate) fn above(ctx: &egui::Context, anchor: Rect, entries: Vec<MenuEntry>) -> Self {
        let height = entries.iter().map(MenuEntry::height).sum::<f32>() + 8.0;
        Self::new(
            ctx,
            Pos2::new(anchor.left(), anchor.top() - 4.0 - height),
            entries,
        )
    }
    pub(crate) fn show(
        &mut self,
        ctx: &egui::Context,
        palette: &LibraryPalette,
        salt: &str,
    ) -> MenuOutcome {
        let id = egui::Id::new(("library-context-menu", salt));
        let measure = ctx.layer_painter(egui::LayerId::new(egui::Order::Foreground, id));
        let text_width = |text: &str, size: f32| {
            paint::galley(&measure, text, size, palette.ink, None)
                .size()
                .x
        };
        let mut width: f32 = MIN_WIDTH;
        for entry in &self.entries {
            let wanted = match entry {
                MenuEntry::Item { label, key, .. } => {
                    text_width(label, 13.0) + key.map_or(0.0, |k| text_width(k, 11.5) + 28.0) + 44.0
                }
                MenuEntry::Sub { label, .. } => text_width(label, 13.0) + 64.0,
                MenuEntry::Caption(label) => text_width(label, 10.5) * 1.25 + 40.0,
                MenuEntry::Separator => 0.0,
            };
            width = width.max(wanted);
        }
        width = width.min(MAX_WIDTH);
        let height = self.entries.iter().map(MenuEntry::height).sum::<f32>() + 8.0;
        let screen = ctx.content_rect();
        let mut origin = self.at;
        if origin.x + width > screen.right() - 4.0 {
            origin.x = (self.at.x - width).max(screen.left() + 4.0);
        }
        if origin.y + height > screen.bottom() - 4.0 {
            origin.y = (screen.bottom() - 4.0 - height).max(screen.top() + 4.0);
        }
        let frame = Rect::from_min_size(origin, Vec2::new(width, height));
        let mut chosen = None;
        let mut sub_anchor = None;
        let entries = &self.entries;
        let open_sub = &mut self.open_sub;
        egui::Area::new(id)
            .order(egui::Order::Foreground)
            .fixed_pos(frame.min)
            .constrain(false)
            .show(ctx, |ui| {
                let (rect, _) = ui.allocate_exact_size(frame.size(), Sense::hover());
                let painter = ui.painter();
                painter.add(ui.visuals().popup_shadow.as_shape(rect, CornerRadius::ZERO));
                painter.rect_filled(rect, CornerRadius::ZERO, palette.panel);
                paint::inset(painter, rect, palette.line_2);
                let mut y = rect.top() + 4.0;
                for (index, entry) in entries.iter().enumerate() {
                    let row = Rect::from_min_size(
                        Pos2::new(rect.left() + 1.0, y),
                        Vec2::new(rect.width() - 2.0, entry.height()),
                    );
                    y += entry.height();
                    match entry {
                        MenuEntry::Separator => {
                            paint::hline(
                                ui.painter(),
                                row.left() + 10.0..=row.right() - 10.0,
                                row.center().y,
                                palette.line,
                            );
                        }
                        MenuEntry::Caption(label) => {
                            paint::caps(
                                ui.painter(),
                                Pos2::new(row.left() + 14.0, row.center().y + 2.0),
                                Align2::LEFT_CENTER,
                                label,
                                10.5,
                                palette.ink_3,
                            );
                        }
                        MenuEntry::Item {
                            label,
                            key,
                            intent,
                            danger,
                        } => {
                            let enabled = intent.is_some();
                            let response = ui.interact(
                                row,
                                id.with(("item", index)),
                                if enabled {
                                    Sense::click()
                                } else {
                                    Sense::hover()
                                },
                            );
                            if response.hovered() {
                                *open_sub = None;
                            }
                            if enabled && response.hovered() {
                                ui.painter()
                                    .rect_filled(row, CornerRadius::ZERO, palette.raised);
                            }
                            let ink = if !enabled {
                                palette.ink_3
                            } else if *danger {
                                palette.bad
                            } else {
                                palette.ink
                            };
                            paint::text(
                                ui.painter(),
                                Pos2::new(row.left() + 14.0, row.center().y),
                                Align2::LEFT_CENTER,
                                label,
                                13.0,
                                ink,
                                Some(row.width() - if key.is_some() { 70.0 } else { 28.0 }),
                            );
                            if let Some(key) = key {
                                paint::text(
                                    ui.painter(),
                                    Pos2::new(row.right() - 14.0, row.center().y),
                                    Align2::RIGHT_CENTER,
                                    key,
                                    11.5,
                                    palette.ink_3,
                                    None,
                                );
                            }
                            if response.clicked()
                                && let Some(intent) = intent
                            {
                                chosen = Some(intent.clone());
                            }
                        }
                        MenuEntry::Sub { label, items } => {
                            let response =
                                ui.interact(row, id.with(("sub", index)), Sense::click());
                            if response.hovered() || response.clicked() {
                                *open_sub = Some(index);
                            }
                            let open = *open_sub == Some(index);
                            if open || response.hovered() {
                                ui.painter()
                                    .rect_filled(row, CornerRadius::ZERO, palette.raised);
                            }
                            let ink = if items.is_empty() {
                                palette.ink_3
                            } else {
                                palette.ink
                            };
                            paint::text(
                                ui.painter(),
                                Pos2::new(row.left() + 14.0, row.center().y),
                                Align2::LEFT_CENTER,
                                label,
                                13.0,
                                ink,
                                Some(row.width() - 50.0),
                            );
                            chevron(
                                ui.painter(),
                                Pos2::new(row.right() - 16.0, row.center().y),
                                palette.ink_3,
                            );
                            if open {
                                sub_anchor = Some(row);
                            }
                        }
                    }
                }
            });
        let mut sub_rect = None;
        if let (Some(index), Some(anchor)) = (self.open_sub, sub_anchor)
            && let Some(MenuEntry::Sub { items, .. }) = self.entries.get(index)
            && !items.is_empty()
        {
            let (found, rect) = show_sub(ctx, id, frame, anchor, items, palette);
            chosen = chosen.or(found);
            sub_rect = Some(rect);
        }
        if let Some(intent) = chosen {
            return MenuOutcome::Chosen(intent);
        }
        let fresh = ctx.cumulative_pass_nr() == self.born;
        let outside = ctx.input(|i| {
            (i.pointer.any_pressed() || i.pointer.any_click())
                && i.pointer.interact_pos().is_some_and(|p| {
                    !frame.contains(p) && !sub_rect.is_some_and(|r: Rect| r.contains(p))
                })
        });
        // Escape is the menu's: it does not also clear a selection beneath.
        let escape = ctx.input_mut(|i| i.consume_key(egui::Modifiers::NONE, egui::Key::Escape));
        if escape || (outside && !fresh) {
            return MenuOutcome::Closed;
        }
        MenuOutcome::Open
    }
}

fn chevron(painter: &egui::Painter, at: Pos2, color: egui::Color32) {
    let stroke = egui::Stroke::new(1.25_f32, color);
    painter.line_segment(
        [at + Vec2::new(-2.0, -4.0), at + Vec2::new(2.0, 0.0)],
        stroke,
    );
    painter.line_segment(
        [at + Vec2::new(2.0, 0.0), at + Vec2::new(-2.0, 4.0)],
        stroke,
    );
}

/// The submenu beside `anchor`: at most `SUB_ROWS` rows, then it scrolls.
fn show_sub(
    ctx: &egui::Context,
    id: egui::Id,
    menu: Rect,
    anchor: Rect,
    items: &[SubItem],
    palette: &LibraryPalette,
) -> (Option<LibraryIntent>, Rect) {
    let sub_id = id.with("sub-area");
    let measure = ctx.layer_painter(egui::LayerId::new(egui::Order::Foreground, sub_id));
    let mut width: f32 = 200.0;
    for item in items {
        let label = paint::galley(&measure, &item.label, 13.0, palette.ink, None)
            .size()
            .x;
        let detail = if item.detail.is_empty() {
            0.0
        } else {
            paint::galley(&measure, &item.detail, 11.5, palette.ink_3, None)
                .size()
                .x
                + 18.0
        };
        width = width.max(label + detail + 30.0);
    }
    width = width.min(MAX_WIDTH);
    let rows = items.len().min(SUB_ROWS);
    let height = rows as f32 * ITEM + 8.0;
    let screen = ctx.content_rect();
    let mut origin = Pos2::new(menu.right() - 1.0, anchor.top() - 4.0);
    if origin.x + width > screen.right() - 4.0 {
        origin.x = menu.left() - width + 1.0;
    }
    if origin.y + height > screen.bottom() - 4.0 {
        origin.y = (screen.bottom() - 4.0 - height).max(screen.top() + 4.0);
    }
    let frame = Rect::from_min_size(origin, Vec2::new(width, height));
    let mut chosen = None;
    egui::Area::new(sub_id)
        .order(egui::Order::Foreground)
        .fixed_pos(frame.min)
        .constrain(false)
        .show(ctx, |ui| {
            let painter = ui.painter().clone();
            painter.add(
                ui.visuals()
                    .popup_shadow
                    .as_shape(frame, CornerRadius::ZERO),
            );
            painter.rect_filled(frame, CornerRadius::ZERO, palette.panel);
            paint::inset(&painter, frame, palette.line_2);
            ui.set_clip_rect(frame);
            let inner = frame.shrink2(Vec2::new(1.0, 4.0));
            ui.scope_builder(egui::UiBuilder::new().max_rect(inner), |ui| {
                egui::ScrollArea::vertical()
                    .id_salt(sub_id.with("scroll"))
                    .max_height(inner.height())
                    .auto_shrink([false, true])
                    .show(ui, |ui| {
                        ui.spacing_mut().item_spacing.y = 0.0;
                        for (index, item) in items.iter().enumerate() {
                            let (row, response) = ui.allocate_exact_size(
                                Vec2::new(inner.width(), ITEM),
                                Sense::click(),
                            );
                            if index == 1 && items[0].label.starts_with("New ") {
                                paint::hline(
                                    ui.painter(),
                                    row.left() + 10.0..=row.right() - 10.0,
                                    row.top(),
                                    palette.line,
                                );
                            }
                            if response.hovered() {
                                ui.painter()
                                    .rect_filled(row, CornerRadius::ZERO, palette.raised);
                            }
                            let label = paint::text(
                                ui.painter(),
                                Pos2::new(row.left() + 14.0, row.center().y),
                                Align2::LEFT_CENTER,
                                &item.label,
                                13.0,
                                palette.ink,
                                Some(row.width() - 40.0),
                            );
                            if !item.detail.is_empty() {
                                paint::text(
                                    ui.painter(),
                                    Pos2::new(label.right() + 10.0, row.center().y),
                                    Align2::LEFT_CENTER,
                                    &item.detail,
                                    11.5,
                                    palette.ink_3,
                                    Some((row.right() - label.right() - 24.0).max(10.0)),
                                );
                            }
                            if response.clicked() {
                                chosen = Some(item.intent.clone());
                            }
                        }
                    });
            });
        });
    (chosen, frame)
}

/// The collection (top-level project) holding `id`.
fn collection_of(catalog: &Catalog, id: NodeId) -> Option<NodeId> {
    let mut at = catalog.node(id)?.parent;
    let mut last = None;
    for _ in 0..64 {
        let Some(node) = at.and_then(|a| catalog.node(a)) else {
            break;
        };
        last = Some(node.id);
        at = node.parent;
    }
    last
}
fn name_of(catalog: &Catalog, id: Option<NodeId>) -> String {
    id.and_then(|id| catalog.node(id))
        .map(|n| n.name.clone())
        .unwrap_or_default()
}
/// Every subject but `except`, by name, its collection as the detail.
fn subject_items(
    catalog: &Catalog,
    except: &[NodeId],
    intent: impl Fn(NodeId) -> LibraryIntent,
) -> Vec<SubItem> {
    let mut items: Vec<(String, SubItem)> = catalog
        .nodes
        .iter()
        .filter(|n| n.kind == NodeKind::Subject && !except.contains(&n.id))
        .map(|n| {
            (
                n.name.to_lowercase(),
                SubItem {
                    label: n.name.clone(),
                    detail: name_of(catalog, collection_of(catalog, n.id)),
                    intent: intent(n.id),
                },
            )
        })
        .collect();
    items.sort_by(|a, b| a.0.cmp(&b.0).then_with(|| a.1.detail.cmp(&b.1.detail)));
    items.into_iter().map(|(_, item)| item).collect()
}

/// What a subject's menu may offer for stacking.
#[derive(Clone, Copy, Debug, Default)]
pub(crate) struct SubjectFlags {
    /// A stack renders now: stacking more waits ("Stack next").
    pub stacking: bool,
    /// The subject on the rig.
    pub capturing: Option<NodeId>,
}

/// The menu of a subject card or list row (or of the selection it is in).
pub(crate) fn subject_menu(
    catalog: &Catalog,
    targets: &[NodeId],
    flags: SubjectFlags,
) -> Vec<MenuEntry> {
    let mut entries = Vec::new();
    let collections = |subjects: &[NodeId]| {
        let current: Vec<Option<NodeId>> = subjects
            .iter()
            .map(|&s| collection_of(catalog, s))
            .collect();
        let mut items = vec![SubItem {
            label: "New collection".into(),
            detail: String::new(),
            intent: LibraryIntent::MoveSubjectsToNewCollection(subjects.to_vec()),
        }];
        items.extend(
            catalog
                .nodes
                .iter()
                .filter(|n| n.kind == NodeKind::Project)
                .filter(|n| !current.iter().all(|c| *c == Some(n.id)))
                .map(|n| SubItem {
                    label: n.name.clone(),
                    detail: String::new(),
                    intent: LibraryIntent::MoveSubjects {
                        subjects: subjects.to_vec(),
                        collection: n.id,
                    },
                }),
        );
        items
    };
    match targets {
        [] => {}
        [id] => {
            let id = *id;
            let summary = catalog.subject_summary(id).unwrap_or_default();
            entries.push(MenuEntry::keyed(
                "Open",
                "Enter",
                LibraryIntent::OpenSubject(id),
            ));
            entries.push(MenuEntry::keyed("Rename…", "F2", LibraryIntent::Rename(id)));
            if summary.to_stack > 0 && flags.capturing != Some(id) {
                let what = paint::plural(summary.to_stack, "stack", "stacks");
                let label = if flags.stacking {
                    format!("Stack next · {what}")
                } else {
                    format!("Stack · {what}")
                };
                entries.push(MenuEntry::item(label, LibraryIntent::QueueSubject(id)));
            }
            entries.push(MenuEntry::Separator);
            entries.push(MenuEntry::Sub {
                label: "Move to collection".into(),
                items: collections(&[id]),
            });
            entries.push(MenuEntry::Sub {
                label: "Merge into".into(),
                items: subject_items(catalog, &[id], |into| LibraryIntent::MergeSubjects {
                    into,
                    others: vec![id],
                }),
            });
            entries.push(if catalog.stacks_of(id).is_empty() {
                MenuEntry::disabled("Show photographs in Explorer")
            } else {
                MenuEntry::item(
                    "Show photographs in Explorer",
                    LibraryIntent::ShowSources(id),
                )
            });
            entries.push(if summary.renders == 0 {
                MenuEntry::disabled("Show renders in Explorer")
            } else {
                MenuEntry::item("Show renders in Explorer", LibraryIntent::ShowRenders(id))
            });
            entries.push(MenuEntry::Separator);
            entries.push(MenuEntry::danger(
                "Delete…",
                "Del",
                LibraryIntent::Delete(vec![id]),
            ));
        }
        many => {
            entries.push(MenuEntry::Caption(paint::plural(
                many.len(),
                "subject selected",
                "subjects selected",
            )));
            entries.push(MenuEntry::Sub {
                label: "Move to collection".into(),
                items: collections(many),
            });
            entries.push(MenuEntry::Sub {
                label: "Merge into one".into(),
                items: many
                    .iter()
                    .map(|&into| SubItem {
                        label: name_of(catalog, Some(into)),
                        detail: name_of(catalog, collection_of(catalog, into)),
                        intent: LibraryIntent::MergeSubjects {
                            into,
                            others: many.iter().copied().filter(|&o| o != into).collect(),
                        },
                    })
                    .collect(),
            });
            entries.push(MenuEntry::Separator);
            entries.push(MenuEntry::danger(
                format!("Delete {} subjects…", many.len()),
                "Del",
                LibraryIntent::Delete(many.to_vec()),
            ));
        }
    }
    entries
}

/// What a stack's menu may offer.
#[derive(Clone, Copy, Debug, Default)]
pub(crate) struct StackFlags {
    /// On the rig now: Open goes to Capture.
    pub capturing: bool,
    /// Rendering or waiting in the queue already.
    pub queued: bool,
    /// A stack renders: stacking waits ("Stack next").
    pub busy: bool,
}

/// The menu of a stack row on the subject page (or of the selection it is in).
pub(crate) fn stack_menu(
    catalog: &Catalog,
    targets: &[NodeId],
    flags: StackFlags,
) -> Vec<MenuEntry> {
    let mut entries = Vec::new();
    let current: Vec<NodeId> = targets
        .iter()
        .filter_map(|&s| catalog.subject_of(s))
        .collect();
    let move_to = |stacks: &[NodeId]| {
        let mut items = vec![SubItem {
            label: "New subject".into(),
            detail: String::new(),
            intent: LibraryIntent::MoveStacksToNewSubject(stacks.to_vec()),
        }];
        // The subject they all sit in is not offered.
        let shared: Vec<NodeId> = match current.first() {
            Some(first) if current.iter().all(|c| c == first) => vec![*first],
            _ => Vec::new(),
        };
        items.extend(subject_items(catalog, &shared, |subject| {
            LibraryIntent::MoveStacks {
                stacks: stacks.to_vec(),
                subject,
            }
        }));
        items
    };
    match targets {
        [] => {}
        [id] => {
            let id = *id;
            entries.push(if flags.capturing {
                MenuEntry::item("Open capture", LibraryIntent::OpenCapture)
            } else {
                MenuEntry::keyed("Open", "Enter", LibraryIntent::OpenStack(id))
            });
            if !flags.capturing && !flags.queued {
                entries.push(MenuEntry::item(
                    if flags.busy { "Stack next" } else { "Stack" },
                    LibraryIntent::QueueStack(id),
                ));
            }
            entries.push(MenuEntry::keyed("Rename…", "F2", LibraryIntent::Rename(id)));
            entries.push(MenuEntry::Separator);
            entries.push(MenuEntry::Sub {
                label: "Move to subject".into(),
                items: move_to(&[id]),
            });
            entries.push(MenuEntry::item(
                "Show photographs in Explorer",
                LibraryIntent::ShowSources(id),
            ));
            let renders = catalog.node(id).is_some_and(|n| !n.revisions.is_empty());
            entries.push(if renders {
                MenuEntry::item("Show renders in Explorer", LibraryIntent::ShowRenders(id))
            } else {
                MenuEntry::disabled("Show renders in Explorer")
            });
            entries.push(MenuEntry::Separator);
            entries.push(MenuEntry::danger(
                "Delete…",
                "Del",
                LibraryIntent::Delete(vec![id]),
            ));
        }
        many => {
            entries.push(MenuEntry::Caption(paint::plural(
                many.len(),
                "stack selected",
                "stacks selected",
            )));
            entries.push(MenuEntry::Sub {
                label: "Move to subject".into(),
                items: move_to(many),
            });
            entries.push(MenuEntry::Separator);
            entries.push(MenuEntry::danger(
                format!("Delete {} stacks…", many.len()),
                "Del",
                LibraryIntent::Delete(many.to_vec()),
            ));
        }
    }
    entries
}

/// The multi-selection of a list: Ctrl click toggles, Shift click selects
/// the range from the last clicked item, Ctrl A selects everything shown.
#[derive(Clone, Debug, Default, PartialEq, Eq)]
pub(crate) struct Selection {
    ids: Vec<NodeId>,
    anchor: Option<NodeId>,
}
impl Selection {
    pub(crate) fn ids(&self) -> &[NodeId] {
        &self.ids
    }
    pub(crate) fn contains(&self, id: NodeId) -> bool {
        self.ids.contains(&id)
    }
    pub(crate) fn is_empty(&self) -> bool {
        self.ids.is_empty()
    }
    pub(crate) fn len(&self) -> usize {
        self.ids.len()
    }
    pub(crate) fn clear(&mut self) {
        self.ids.clear();
        self.anchor = None;
    }
    pub(crate) fn set(&mut self, ids: &[NodeId]) {
        self.ids.clear();
        self.ids.extend_from_slice(ids);
        self.anchor = ids.last().copied();
    }
    /// A click with `modifiers` on `id`, in the shown `order`. Returns
    /// whether it was a selection click (Ctrl or Shift held).
    pub(crate) fn click(
        &mut self,
        id: NodeId,
        modifiers: egui::Modifiers,
        order: &[NodeId],
    ) -> bool {
        if modifiers.shift {
            let from = self
                .anchor
                .and_then(|a| order.iter().position(|&o| o == a))
                .unwrap_or(0);
            let Some(to) = order.iter().position(|&o| o == id) else {
                return true;
            };
            let (a, b) = if from <= to { (from, to) } else { (to, from) };
            if !modifiers.command {
                self.ids.clear();
            }
            for &item in &order[a..=b] {
                if !self.ids.contains(&item) {
                    self.ids.push(item);
                }
            }
            self.anchor.get_or_insert(id);
            true
        } else if modifiers.command {
            if let Some(at) = self.ids.iter().position(|&s| s == id) {
                self.ids.remove(at);
            } else {
                self.ids.push(id);
            }
            self.anchor = Some(id);
            true
        } else {
            false
        }
    }
    /// Drop what is no longer shown (deleted, filtered out).
    pub(crate) fn retain_in(&mut self, order: &[NodeId]) {
        self.ids.retain(|id| order.contains(id));
        if self.anchor.is_some_and(|a| !order.contains(&a)) {
            self.anchor = None;
        }
    }
    /// What an action on `id` applies to: the selection when `id` is in it,
    /// else `id` alone.
    pub(crate) fn targets(&self, id: NodeId) -> Vec<NodeId> {
        if self.contains(id) {
            self.ids.clone()
        } else {
            vec![id]
        }
    }
}

/// A square tick marking a selected item, at a picture's top-left corner.
pub(crate) fn tick(painter: &egui::Painter, corner: Pos2, palette: &LibraryPalette) {
    let rect = Rect::from_min_size(corner + Vec2::new(6.0, 6.0), Vec2::splat(16.0));
    painter.rect_filled(rect, CornerRadius::ZERO, palette.accent);
    let stroke = egui::Stroke::new(1.6_f32, palette.accent_ink);
    let c = rect.center();
    painter.line_segment([c + Vec2::new(-4.5, 0.0), c + Vec2::new(-1.2, 3.3)], stroke);
    painter.line_segment([c + Vec2::new(-1.2, 3.3), c + Vec2::new(4.8, -3.6)], stroke);
}

/// One action of the selection bar.
#[derive(Clone, Copy)]
pub(crate) struct BarAction<'a> {
    pub label: &'a str,
    pub style: ButtonStyle,
}

/// The bar along the bottom of a list while something is selected: what is
/// selected, its actions, and the keys. Returns the index of the action
/// clicked (the last index + 1 is "Clear") and the clicked button's rect.
pub(crate) fn selection_bar(
    ui: &mut Ui,
    rect: Rect,
    salt: &str,
    caption: &str,
    actions: &[BarAction<'_>],
    palette: &LibraryPalette,
) -> Option<(usize, Rect)> {
    // The bar takes the pointer from the grid beneath it.
    let _ = ui.interact(rect, ui.id().with((salt, "bar")), Sense::click());
    let painter = ui.painter().clone();
    painter.rect_filled(rect, CornerRadius::ZERO, palette.panel);
    paint::hline(
        &painter,
        rect.left()..=rect.right(),
        rect.top(),
        palette.line_2,
    );
    painter.rect_filled(
        Rect::from_min_size(rect.min, Vec2::new(2.0, rect.height())),
        CornerRadius::ZERO,
        palette.accent,
    );
    let center = rect.center().y;
    let label = paint::caps(
        &painter,
        Pos2::new(rect.left() + 18.0, center),
        Align2::LEFT_CENTER,
        caption,
        10.5,
        palette.ink,
    );
    let mut x = label.right() + 20.0;
    let mut clicked = None;
    for (index, action) in actions.iter().enumerate() {
        let width = paint::button_width(&painter, action.label, false, false);
        let button = Rect::from_min_size(Pos2::new(x, center - 14.0), Vec2::new(width, 28.0));
        if paint::button(
            ui,
            button,
            (salt, index),
            action.label,
            None,
            action.style,
            palette,
        )
        .clicked()
        {
            clicked = Some((index, button));
        }
        x = button.right() + 8.0;
    }
    let keys = "Ctrl A all · Esc clear · Del delete";
    let keys_rect = paint::text(
        &painter,
        Pos2::new(rect.right() - 16.0, center),
        Align2::RIGHT_CENTER,
        keys,
        11.5,
        palette.ink_3,
        None,
    );
    let clear_width = paint::button_width(&painter, "Clear", false, false);
    let clear = Rect::from_min_size(
        Pos2::new(keys_rect.left() - 14.0 - clear_width, center - 14.0),
        Vec2::new(clear_width, 28.0),
    );
    if clear.left() > x
        && paint::button(
            ui,
            clear,
            (salt, "clear"),
            "Clear",
            None,
            ButtonStyle::Quiet,
            palette,
        )
        .clicked()
    {
        clicked = Some((actions.len(), clear));
    }
    clicked
}

#[cfg(test)]
#[path = "library-menu-tests.rs"]
mod tests;
