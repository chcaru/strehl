//! Compact virtual project tree. Every command is a catalog edit or an explicit
//! request to open a stack; no command moves photographs or deletes evidence.
use crate::{
    theme::{self, ACCENT, AMBER, GREEN, INK, LINE, MUTED, RAISED},
    workspace_history::{Catalog, NodeId, NodeKind, ProjectNode, Run, timestamp},
};
use eframe::egui::{self, Align2, Color32, FontId, Key, RichText, Sense, Stroke};
use std::path::{Path, PathBuf};
#[path = "explorer-previews.rs"]
mod previews;

#[derive(Clone, Debug)]
pub(crate) enum ExplorerAction {
    NewCapture { parent: Option<NodeId> },
    OpenStack { id: NodeId },
    OpenRun { run: Box<Run> },
    RestoreVersion { id: String },
    OpenExport { id: String },
    RevealPath { path: PathBuf },
}
#[derive(Default)]
pub(crate) struct ExplorerResponse {
    pub changed: bool,
    pub action: Option<ExplorerAction>,
}
#[derive(Default)]
pub(crate) struct ProjectExplorer {
    filter: String,
    edit: Option<Edit>,
    moving: Option<NodeId>,
    error: Option<String>,
    selected_revision: Option<PathBuf>,
    selected_stack: Option<NodeId>,
    selected_history: Option<String>,
    previews: previews::ExplorerPreviews,
    dragging: Option<NodeId>,
    notes_open: bool,
    notes_editor: Option<egui::Id>,
    undo: Vec<Organization>,
    redo: Vec<Organization>,
    evidence: Vec<(NodeId, Vec<PathBuf>)>,
    history_revision: u64,
    history_commits: u64,
    history_focus: Option<egui::Id>,
    #[cfg(test)]
    editor_save_rect: Option<egui::Rect>,
}
/// Reversible organization metadata only. Recipes, manifests and immutable Run
/// observations are deliberately outside this history.
#[derive(Clone, PartialEq, Eq)]
struct Organization {
    nodes: Vec<OrganizedNode>,
    results: Vec<(PathBuf, String, bool)>,
    version_names: Vec<(String, String)>,
}
#[derive(Clone, PartialEq, Eq)]
struct OrganizedNode {
    id: NodeId,
    parent: Option<NodeId>,
    name: String,
    kind: NodeKind,
    notes: String,
}
impl Organization {
    fn capture(catalog: &Catalog) -> Self {
        Self {
            nodes: catalog
                .nodes
                .iter()
                .map(|n| OrganizedNode {
                    id: n.id,
                    parent: n.parent,
                    name: n.name.clone(),
                    kind: n.kind,
                    notes: n.notes.clone(),
                })
                .collect(),
            version_names: catalog
                .photo_versions
                .iter()
                .map(|v| (v.id.clone(), v.name.clone()))
                .collect(),
            results: catalog
                .runs
                .iter()
                .map(|r| (r.directory.clone(), r.label.clone(), r.pinned))
                .collect(),
        }
    }
    fn apply(&self, catalog: &mut Catalog) {
        // Stacks can only enter through import; an undo never removes captures.
        catalog.nodes.retain(|n| {
            n.kind == NodeKind::Stack || self.nodes.iter().any(|saved| saved.id == n.id)
        });
        for saved in &self.nodes {
            if let Some(node) = catalog.node_mut(saved.id) {
                node.parent = saved.parent;
                node.name.clone_from(&saved.name);
                node.notes.clone_from(&saved.notes);
            } else if saved.kind != NodeKind::Stack {
                catalog.nodes.push(ProjectNode {
                    id: saved.id,
                    parent: saved.parent,
                    name: saved.name.clone(),
                    kind: saved.kind,
                    notes: saved.notes.clone(),
                    expanded: true,
                    stack: None,
                    revisions: vec![],
                });
            }
        }
        for (id, name) in &self.version_names {
            if let Some(v) = catalog.photo_versions.iter_mut().find(|v| v.id == *id) {
                v.name.clone_from(name);
            }
        }
        for (directory, label, pinned) in &self.results {
            if let Some(run) = catalog.runs.iter_mut().find(|r| r.directory == *directory) {
                run.label.clone_from(label);
                run.pinned = *pinned;
            }
        }
        if catalog
            .selected
            .is_some_and(|id| catalog.node(id).is_none())
        {
            catalog.selected = catalog.nodes.first().map(|n| n.id);
        }
    }
}
struct TreeRow {
    name: String,
    kind: NodeKind,
    expanded: bool,
    revisions: Vec<PathBuf>,
    source: Option<PathBuf>,
}
struct Edit {
    target: EditTarget,
    value: String,
    focus: bool,
}
enum EditTarget {
    Project,
    Folder(NodeId),
    Node(NodeId),
    Revision(PathBuf),
    Version(String),
}
impl ProjectExplorer {
    pub(crate) fn preview_pending(&self) -> bool {
        self.previews.pending()
    }

    pub(crate) fn set_current_photo(
        &mut self,
        path: Option<&Path>,
        image: Option<&std::sync::Arc<strehl_edit::LinearImage>>,
        preview: Option<&std::sync::Arc<strehl_edit::LinearImage>>,
    ) {
        self.previews.set_current(path, image, preview);
    }

    /// Agent organization commands enter the same reversible metadata journal
    /// as explorer edits. Capture imports and immutable run evidence stay out.
    pub(crate) fn organize<T>(
        &mut self,
        catalog: &mut Catalog,
        change: impl FnOnce(&mut Catalog) -> anyhow::Result<T>,
    ) -> anyhow::Result<T> {
        self.sync_evidence(catalog);
        let before = Organization::capture(catalog);
        let result = change(catalog)?;
        if before != Organization::capture(catalog) {
            self.undo.push(before);
            if self.undo.len() > 80 {
                self.undo.remove(0);
            }
            self.redo.clear();
            self.history_focus = None;
            self.history_revision = self.history_revision.wrapping_add(1);
            self.history_commits = self.history_commits.wrapping_add(1);
        }
        Ok(result)
    }

    pub fn show(
        &mut self,
        ui: &mut egui::Ui,
        catalog: &mut Catalog,
        busy: bool,
    ) -> ExplorerResponse {
        self.previews.poll(ui.ctx());
        if !ui.is_enabled()
            || ui.input(|i| !i.focused || i.key_pressed(Key::Escape))
            || egui::Popup::is_any_open(ui.ctx())
            || !ui.ctx().memory(|m| m.is_above_modal_layer(ui.layer_id()))
        {
            self.dragging = None;
        }
        self.sync_evidence(catalog);
        // Painting and pointer hover do not edit the catalog. Avoid cloning
        // notes/result metadata on every animation frame of the photo workspace.
        let may_edit = ui.input(|i| {
            i.pointer.any_released()
                || i.events.iter().any(|event| {
                    matches!(
                        event,
                        egui::Event::Text(_)
                            | egui::Event::Paste(_)
                            | egui::Event::Cut
                            | egui::Event::Ime(_)
                            | egui::Event::Key { pressed: true, .. }
                    )
                })
        });
        let before = may_edit.then(|| Organization::capture(catalog));
        let mut response = ExplorerResponse::default();
        ui.spacing_mut().item_spacing = egui::vec2(0.0, 0.0);
        if self.selected_stack != catalog.selected {
            if self
                .selected_revision
                .as_ref()
                .and_then(|path| catalog.stack_for_run(path))
                != catalog.selected
            {
                self.selected_revision = None;
            }
            self.selected_stack = catalog.selected;
        }
        egui::Frame::new()
            .inner_margin(egui::Margin::symmetric(8, 6))
            .show(ui, |ui| {
                ui.spacing_mut().item_spacing = egui::vec2(4.0, 4.0);
                let width = ui.available_width();
                let (row, _) = ui.allocate_exact_size(egui::vec2(width, 27.0), Sense::hover());
                let primary = egui::Rect::from_min_size(
                    row.min,
                    egui::vec2((width * 0.55).floor(), row.height()),
                );
                let secondary =
                    egui::Rect::from_min_max(egui::pos2(primary.right() + 4.0, row.top()), row.max);
                let destination = catalog
                    .selected_container()
                    .map(|id| catalog.breadcrumb(id));
                if command(ui, primary, "New stack", Glyph::Add, true, !busy)
                    .on_hover_text(destination.map_or_else(
                        || "Choose source photos for your first stack".into(),
                        |p| format!("Choose source photos for a new stack in {p}"),
                    ))
                    .clicked()
                {
                    response.action = Some(ExplorerAction::NewCapture {
                        parent: catalog.selected_container(),
                    });
                }
                if command(ui, secondary, "New project", Glyph::Project, false, true)
                    .on_hover_text("A named home for related stacks and their results")
                    .clicked()
                {
                    self.edit(EditTarget::Project, "New project");
                }
                ui.add(
                    egui::TextEdit::singleline(&mut self.filter)
                        .hint_text("Search projects")
                        .margin(egui::Margin::symmetric(6, 4))
                        .desired_width((width - 12.0).max(1.0)),
                );
                if matches!(
                    self.edit.as_ref().map(|e| &e.target),
                    Some(EditTarget::Project)
                ) {
                    self.show_editor(ui, catalog, &mut response);
                }
                if let Some(error) = &catalog.load_error {
                    ui.colored_label(AMBER, error);
                }
                if let Some(error) = &self.error {
                    ui.colored_label(AMBER, error);
                }
            });
        divider(ui);
        let selected = catalog.selected.and_then(|id| catalog.node(id)).is_some();
        let footer_height = if selected {
            if self.notes_open { 108.0 } else { 59.0 }
        } else {
            0.0
        };
        let tree_height = (ui.available_height() - footer_height).max(70.0);
        egui::ScrollArea::vertical()
            .id_salt("project-explorer-tree")
            .auto_shrink([false, false])
            .max_height(tree_height)
            .show(ui, |ui| {
                if catalog.nodes.is_empty() && catalog.photo_versions.is_empty() {
                    egui::Frame::new().inner_margin(12).show(ui, |ui| {
                        ui.label(RichText::new("Your photographs start here").color(INK));
                        theme::caption(ui, "New stack opens your source photos.");
                    });
                }
                let roots: Vec<NodeId> = catalog
                    .nodes
                    .iter()
                    .filter(|node| node.parent.is_none())
                    .map(|n| n.id)
                    .collect();
                for id in roots {
                    self.show_node(ui, catalog, id, 0, busy, &mut response);
                }
                let mut photos: Vec<_> = catalog
                    .photo_versions
                    .iter()
                    .filter(|v| v.owner.stack.is_none())
                    .map(|v| v.owner.output.clone())
                    .collect();
                photos.sort();
                photos.dedup();
                if !photos.is_empty() {
                    divider(ui);
                    ui.label(RichText::new("PHOTOGRAPHS").small().color(MUTED));
                    for path in photos {
                        egui::CollapsingHeader::new(
                            path.file_name().unwrap_or_default().to_string_lossy(),
                        )
                        .id_salt(("photo-history", &path))
                        .default_open(true)
                        .show(ui, |ui| {
                            self.show_photo_history(ui, catalog, &path, 0, busy, &mut response);
                        });
                    }
                }
            });
        if let Some(id) = catalog.selected {
            divider(ui);
            egui::Frame::new()
                .inner_margin(egui::Margin::symmetric(8, 5))
                .show(ui, |ui| {
                    self.show_selected(ui, catalog, id, &mut response);
                });
        }
        if let Some(before) = before
            && before != Organization::capture(catalog)
        {
            let focus = ui
                .ctx()
                .memory(|m| m.focused())
                .filter(|id| self.notes_editor == Some(*id));
            if focus.is_none() || focus != self.history_focus || self.undo.is_empty() {
                self.undo.push(before);
                self.history_commits = self.history_commits.wrapping_add(1);
                if self.undo.len() > 80 {
                    self.undo.remove(0);
                }
            }
            self.redo.clear();
            self.history_focus = focus;
            self.history_revision = self.history_revision.wrapping_add(1);
        } else if !ui.ctx().wants_keyboard_input() {
            self.history_focus = None;
        }
        if ui.input(|i| i.pointer.any_released() || !i.focused || i.key_pressed(Key::Escape)) {
            self.dragging = None;
        }
        response
    }
    pub fn can_undo(&self) -> bool {
        !self.undo.is_empty()
    }
    pub fn can_redo(&self) -> bool {
        !self.redo.is_empty()
    }
    pub fn history_revision(&self) -> u64 {
        self.history_revision
    }
    pub fn history_commits(&self) -> u64 {
        self.history_commits
    }
    pub fn history_depths(&self) -> (usize, usize) {
        (self.undo.len(), self.redo.len())
    }
    pub fn clear_history(&mut self) {
        if !self.undo.is_empty() || !self.redo.is_empty() {
            self.history_revision = self.history_revision.wrapping_add(1);
        }
        self.undo.clear();
        self.redo.clear();
        self.history_focus = None;
    }
    fn sync_evidence(&mut self, catalog: &Catalog) {
        let evidence: Vec<_> = catalog
            .nodes
            .iter()
            .filter(|n| n.kind == NodeKind::Stack)
            .map(|n| (n.id, n.revisions.clone()))
            .collect();
        if evidence != self.evidence {
            self.clear_history();
            self.evidence = evidence;
        }
    }
    pub fn undo(&mut self, catalog: &mut Catalog) -> bool {
        self.sync_evidence(catalog);
        let Some(previous) = self.undo.pop() else {
            return false;
        };
        self.redo.push(Organization::capture(catalog));
        previous.apply(catalog);
        self.edit = None;
        self.moving = None;
        self.history_focus = None;
        self.history_revision = self.history_revision.wrapping_add(1);
        true
    }
    pub fn redo(&mut self, catalog: &mut Catalog) -> bool {
        self.sync_evidence(catalog);
        let Some(next) = self.redo.pop() else {
            return false;
        };
        self.undo.push(Organization::capture(catalog));
        next.apply(catalog);
        self.edit = None;
        self.moving = None;
        self.history_focus = None;
        self.history_revision = self.history_revision.wrapping_add(1);
        true
    }
    /// Keep the explorer's result identity synchronized with navigation outside it.
    pub fn select_stack(&mut self, id: NodeId) {
        self.selected_stack = Some(id);
        self.selected_history = None;
        self.selected_revision = None;
    }
    pub fn select_revision(&mut self, path: &Path) {
        self.selected_history = None;
        self.selected_revision = Some(path.to_path_buf());
    }
    pub(crate) fn reveal_photo_history(
        &mut self,
        catalog: &mut Catalog,
        path: &Path,
        item: Option<&str>,
    ) {
        let owner = catalog.photo_owner(path);
        self.filter.clear();
        self.selected_stack = owner.stack;
        self.selected_revision = owner.run;
        self.selected_history = item.map(str::to_owned);
        catalog.selected = owner.stack;
        let mut current = owner.stack;
        while let Some(id) = current {
            let Some(node) = catalog.node_mut(id) else {
                break;
            };
            node.expanded = true;
            current = node.parent;
        }
    }

    fn edit(&mut self, target: EditTarget, value: &str) {
        self.edit = Some(Edit {
            target,
            value: value.to_owned(),
            focus: true,
        });
        self.moving = None;
        self.error = None;
    }
    fn show_editor(
        &mut self,
        ui: &mut egui::Ui,
        catalog: &mut Catalog,
        response: &mut ExplorerResponse,
    ) {
        let (row, _) =
            ui.allocate_exact_size(egui::vec2(ui.available_width(), 27.0), Sense::hover());
        self.show_editor_at(ui, catalog, response, row);
    }
    fn show_editor_at(
        &mut self,
        ui: &mut egui::Ui,
        catalog: &mut Catalog,
        response: &mut ExplorerResponse,
        row: egui::Rect,
    ) {
        let Some(edit) = &mut self.edit else {
            return;
        };
        let mut accept = false;
        let mut cancel = false;
        let cancel_rect =
            egui::Rect::from_min_max(egui::pos2(row.right() - 28.0, row.top()), row.max);
        let save_rect = cancel_rect.translate(egui::vec2(-32.0, 0.0));
        #[cfg(test)]
        {
            self.editor_save_rect = Some(save_rect);
        }
        let field_rect = egui::Rect::from_min_max(
            row.min,
            egui::pos2((save_rect.left() - 4.0).max(row.left()), row.bottom()),
        );
        let mut field_ui = bounded_row_cell(ui, field_rect, "project-name-field");
        let field = field_ui.add(
            egui::TextEdit::singleline(&mut edit.value)
                .margin(egui::Margin::same(3))
                .desired_width((field_rect.width() - 6.0).max(1.0)),
        );
        if edit.focus {
            field.request_focus();
            if let Some(mut state) = egui::TextEdit::load_state(ui.ctx(), field.id) {
                state
                    .cursor
                    .set_char_range(Some(egui::text::CCursorRange::two(
                        egui::text::CCursor::new(0),
                        egui::text::CCursor::new(edit.value.chars().count()),
                    )));
                state.store(ui.ctx(), field.id);
            }
            edit.focus = false;
        }
        accept |= icon_button(ui, save_rect, "project-name-save", Glyph::Check)
            .on_hover_text("Save name · Enter")
            .clicked();
        cancel |= icon_button(ui, cancel_rect, "project-name-cancel", Glyph::Close)
            .on_hover_text("Cancel · Escape")
            .clicked();
        if field.has_focus() || field.lost_focus() || ui.ctx().wants_keyboard_input() {
            accept |= ui.input(|i| i.key_pressed(Key::Enter));
            cancel |= ui.input(|i| i.key_pressed(Key::Escape));
        }
        if accept {
            let result = match &edit.target {
                EditTarget::Project => catalog.create_project(&edit.value).map(|_| ()),
                EditTarget::Folder(parent) => {
                    catalog.create_folder(*parent, &edit.value).map(|_| ())
                }
                EditTarget::Node(id) => catalog.rename(*id, &edit.value),
                EditTarget::Version(id) => catalog.rename_photo_version(id, &edit.value),
                EditTarget::Revision(path) => {
                    let name = edit.value.trim();
                    if name.is_empty()
                        || name.chars().count() > 160
                        || name.chars().any(char::is_control)
                    {
                        Err(anyhow::anyhow!("Use a name with 1–160 characters"))
                    } else if let Some(run) = catalog.runs.iter_mut().find(|r| r.directory == *path)
                    {
                        run.label = name.into();
                        Ok(())
                    } else {
                        Err(anyhow::anyhow!("Revision no longer exists"))
                    }
                }
            };
            match result {
                Ok(()) => {
                    response.changed = true;
                    self.edit = None;
                    self.error = None;
                }
                Err(error) => self.error = Some(error.to_string()),
            }
        } else if cancel || ui.input_mut(|i| i.consume_key(egui::Modifiers::NONE, Key::Escape)) {
            self.edit = None;
            self.error = None;
        }
    }
    fn show_move(
        &mut self,
        ui: &mut egui::Ui,
        catalog: &mut Catalog,
        response: &mut ExplorerResponse,
    ) {
        let Some(id) = self.moving else {
            return;
        };
        let mut chosen = None;
        let mut cancel = false;
        let (row, _) =
            ui.allocate_exact_size(egui::vec2(ui.available_width(), 27.0), Sense::hover());
        let cancel_rect =
            egui::Rect::from_min_max(egui::pos2(row.right() - 28.0, row.top()), row.max);
        let picker_rect = egui::Rect::from_min_max(
            row.min,
            egui::pos2((cancel_rect.left() - 4.0).max(row.left()), row.bottom()),
        );
        let mut picker_ui = bounded_row_cell(ui, picker_rect, "project-move-picker");
        egui::ComboBox::from_id_salt("move-project-object")
            .selected_text("Move to…")
            .width((picker_rect.width() - 18.0).max(1.0))
            .show_ui(&mut picker_ui, |ui| {
                for target in &catalog.nodes {
                    if catalog.can_move(id, Some(target.id)).is_ok() {
                        let label = format!("{}  · {}", catalog.breadcrumb(target.id), target.id);
                        if ui.selectable_label(false, label).clicked() {
                            chosen = Some(target.id);
                        }
                    }
                }
            });
        cancel |= icon_button(ui, cancel_rect, "project-move-cancel", Glyph::Close)
            .on_hover_text("Cancel move")
            .clicked();
        if let Some(parent) = chosen {
            match catalog.move_node(id, Some(parent)) {
                Ok(()) => {
                    response.changed = true;
                    self.moving = None;
                    self.error = None;
                }
                Err(error) => self.error = Some(error.to_string()),
            }
        } else if cancel {
            self.moving = None;
        }
    }
    fn show_node(
        &mut self,
        ui: &mut egui::Ui,
        catalog: &mut Catalog,
        id: NodeId,
        depth: usize,
        busy: bool,
        response: &mut ExplorerResponse,
    ) {
        let Some(node) = catalog.node(id) else {
            return;
        };
        if !self.matches_branch(catalog, node) {
            return;
        }
        // Paint only the tree's small metadata. Source manifests may contain
        // hundreds of paths and are copied only when opening a stack.
        let node = TreeRow {
            name: node.name.clone(),
            kind: node.kind,
            expanded: node.expanded,
            revisions: node.revisions.clone(),
            source: node.stack.as_ref().map(|s| s.source.clone()),
        };
        let children: Vec<NodeId> = catalog
            .nodes
            .iter()
            .filter(|n| n.parent == Some(id))
            .map(|n| n.id)
            .collect();
        let has_children =
            node.kind == NodeKind::Stack || !children.is_empty() || !node.revisions.is_empty();
        let expanded = node.expanded || !self.filter.trim().is_empty();
        let (rect, _) =
            ui.allocate_exact_size(egui::vec2(ui.available_width(), 25.0), Sense::hover());
        let editing = matches!(self.edit.as_ref().map(|e|&e.target),Some(EditTarget::Node(target))if *target==id);
        let hit = ui.interact(
            rect,
            ui.id().with(("project-node", id)),
            if editing {
                Sense::hover()
            } else {
                Sense::click_and_drag()
            },
        );
        let selected = catalog.selected == Some(id) && self.selected_revision.is_none();
        paint_row(ui, rect, &hit, selected);
        let indent = (depth as f32 * 14.0).min(rect.width() * 0.42);
        let fold = egui::Rect::from_min_size(
            rect.min + egui::vec2(indent + 2.0, 0.0),
            egui::vec2(18.0, rect.height()),
        );
        if has_children {
            glyph(
                ui.painter(),
                fold.center(),
                if expanded { Glyph::Down } else { Glyph::Right },
                MUTED,
            );
        }
        let kind = match node.kind {
            NodeKind::Project => Glyph::Project,
            NodeKind::Folder => Glyph::Folder,
            NodeKind::Stack => Glyph::Stack,
        };
        glyph(
            ui.painter(),
            rect.min + egui::vec2(indent + 29.0, 12.5),
            kind,
            if node.kind == NodeKind::Project {
                ACCENT
            } else {
                MUTED
            },
        );
        let suffix = match node.kind {
            NodeKind::Project => "project".into(),
            NodeKind::Folder => "folder".into(),
            NodeKind::Stack => match node.revisions.len() {
                0 => "stack".into(),
                1 => "1 result".into(),
                count => format!("{count} results"),
            },
        };
        let representative = if node.kind == NodeKind::Stack {
            catalog
                .latest_run(id)
                .map(|r| (r.output.clone(), false))
                .or_else(|| {
                    catalog
                        .node(id)
                        .and_then(|n| n.stack.as_ref())
                        .and_then(|s| s.sources.first())
                        .map(|s| (s.path.clone(), true))
                })
        } else {
            None
        };
        let texture = representative
            .as_ref()
            .filter(|_| ui.is_rect_visible(rect))
            .and_then(|(path, source)| self.previews.file(path, *source));
        if representative.is_some() {
            previews::ExplorerPreviews::paint(
                ui,
                egui::Rect::from_center_size(
                    rect.min + egui::vec2(indent + 29.0, 12.5),
                    egui::vec2(22.0, 18.0),
                ),
                texture.as_ref(),
            );
        }
        if !editing {
            row_text(ui, rect, indent + 42.0, &node.name, &suffix, INK);
        }
        if hit.drag_started() && !editing && !busy && !egui::Popup::is_any_open(ui.ctx()) {
            self.dragging = Some(id);
            self.edit = None;
        }
        if let Some(dragged) = self.dragging
            && !busy
            && ui.is_enabled()
            && !egui::Popup::is_any_open(ui.ctx())
            && hit.contains_pointer()
        {
            let valid = catalog.can_move(dragged, Some(id));
            ui.painter().rect_stroke(
                rect.shrink(0.5),
                0.0,
                Stroke::new(1.0_f32, if valid.is_ok() { ACCENT } else { AMBER }),
                egui::StrokeKind::Inside,
            );
            if ui.input(|i| i.pointer.primary_released()) {
                match valid.and_then(|_| catalog.move_node(dragged, Some(id))) {
                    Ok(()) => {
                        response.changed = true;
                        self.error = None;
                    }
                    Err(e) => self.error = Some(e.to_string()),
                }
            }
        }

        if hit.clicked()
            && self.dragging.is_none()
            && !editing
            && !(busy && node.kind == NodeKind::Stack)
        {
            if has_children
                && hit
                    .interact_pointer_pos()
                    .is_some_and(|at| fold.contains(at))
            {
                catalog.node_mut(id).unwrap().expanded = !node.expanded;
            } else {
                hit.request_focus();
                catalog.selected = Some(id);
                self.select_stack(id);
                if node.kind == NodeKind::Stack {
                    response.action = Some(ExplorerAction::OpenStack { id });
                } else if has_children {
                    catalog.node_mut(id).unwrap().expanded = !node.expanded;
                }
            }
            response.changed = true;
        }
        if hit.secondary_clicked() {
            catalog.selected = Some(id);
            self.select_stack(id);
            response.changed = true;
        }
        if hit.has_focus()
            && ui.is_enabled()
            && ui.ctx().memory(|m| m.is_above_modal_layer(ui.layer_id()))
        {
            if ui.input_mut(|i| i.consume_key(egui::Modifiers::NONE, Key::F2)) {
                self.edit(EditTarget::Node(id), &node.name);
            }
            if !busy
                && node.kind == NodeKind::Stack
                && ui.input_mut(|i| i.consume_key(egui::Modifiers::NONE, Key::Enter))
            {
                response.action = Some(ExplorerAction::OpenStack { id });
            }
            if has_children
                && ui.input_mut(|i| i.consume_key(egui::Modifiers::NONE, Key::ArrowRight))
            {
                catalog.node_mut(id).unwrap().expanded = true;
                response.changed = true;
            }
            if has_children
                && ui.input_mut(|i| i.consume_key(egui::Modifiers::NONE, Key::ArrowLeft))
            {
                catalog.node_mut(id).unwrap().expanded = false;
                response.changed = true;
            }
        }
        let caption = format!(
            "{} · {}",
            catalog.breadcrumb(id),
            match node.kind {
                NodeKind::Project => "Project",
                NodeKind::Folder => "Virtual folder",
                NodeKind::Stack => "Stack · source captures and results",
            }
        );
        hit.clone().on_hover_ui(|ui| {
            previews::ExplorerPreviews::hover(ui, texture.as_ref(), &caption);
            if let Some((path, source)) = &representative
                && let Some(error) = self.previews.error(path, *source)
            {
                ui.label(egui::RichText::new(error).small().color(AMBER));
            }
        });
        hit.context_menu(|ui| {
            if ui.button("Rename…").clicked() {
                self.edit(EditTarget::Node(id), &node.name);
                ui.close();
            }
            if node.kind != NodeKind::Project && ui.button("Move to…").clicked() {
                self.moving = Some(id);
                self.edit = None;
                ui.close();
            }
            if node.kind != NodeKind::Stack {
                if ui.button("New folder…").clicked() {
                    self.edit(EditTarget::Folder(id), "New folder");
                    ui.close();
                }
                if ui
                    .add_enabled(!busy, egui::Button::new("New stack…"))
                    .clicked()
                {
                    response.action = Some(ExplorerAction::NewCapture { parent: Some(id) });
                    ui.close();
                }
            } else if let Some(source) = &node.source {
                if ui.button("Reveal in Explorer").clicked() {
                    response.action = Some(ExplorerAction::RevealPath {
                        path: source.clone(),
                    });
                    ui.close();
                }
                if ui.button("Copy source folder").clicked() {
                    ui.ctx().copy_text(source.display().to_string());
                    ui.close();
                }
                if let Some(run) = catalog.latest_run(id).cloned()
                    && ui
                        .add_enabled(!busy, egui::Button::new("Open latest result"))
                        .clicked()
                {
                    self.select_revision(&run.directory);
                    response.action = Some(ExplorerAction::OpenRun { run: Box::new(run) });
                    ui.close();
                }
            }
        });
        if matches!(self.edit.as_ref().map(|e|&e.target),Some(EditTarget::Node(target))if *target==id)
        {
            let edit_rect =
                egui::Rect::from_min_max(rect.min + egui::vec2(indent + 42.0, 0.0), rect.max);
            ui.painter().rect_filled(edit_rect, 0.0, RAISED);
            self.show_editor_at(ui, catalog, response, edit_rect);
        } else if matches!(self.edit.as_ref().map(|e|&e.target),Some(EditTarget::Folder(target))if *target==id)
        {
            self.show_editor(ui, catalog, response);
        }
        if self.moving == Some(id) {
            egui::Frame::new()
                .inner_margin(egui::Margin::symmetric(8, 3))
                .show(ui, |ui| self.show_move(ui, catalog, response));
        }
        if node.kind != NodeKind::Stack && children.is_empty() && catalog.selected == Some(id) {
            let (row, _) =
                ui.allocate_exact_size(egui::vec2(ui.available_width(), 27.0), Sense::hover());
            let local = egui::Rect::from_min_max(
                row.min + egui::vec2(indent + 39.0, 0.0),
                row.max - egui::vec2(8.0, 0.0),
            );
            if command(ui, local, "Add first stack", Glyph::Add, false, !busy).clicked() {
                response.action = Some(ExplorerAction::NewCapture { parent: Some(id) });
            }
        }
        if expanded {
            if node.kind == NodeKind::Stack {
                self.show_captures(ui, catalog, id, depth + 1, busy, response);
            }
            for child in children {
                self.show_node(ui, catalog, child, depth + 1, busy, response);
            }
            for (index, directory) in node.revisions.iter().enumerate().rev() {
                let Some(run_index) = catalog
                    .runs
                    .iter()
                    .position(|run| run.directory == *directory)
                else {
                    continue;
                };
                self.show_revision(
                    ui,
                    catalog,
                    run_index,
                    (id, index + 1, depth + 1),
                    busy,
                    response,
                );
            }
        }
    }
    fn show_revision(
        &mut self,
        ui: &mut egui::Ui,
        catalog: &mut Catalog,
        run_index: usize,
        position: (NodeId, usize, usize),
        busy: bool,
        response: &mut ExplorerResponse,
    ) {
        let (stack, number, depth) = position;
        let indent = (depth as f32 * 14.0).min(ui.available_width() * 0.42);
        let run = &catalog.runs[run_index];
        let (rect, _) =
            ui.allocate_exact_size(egui::vec2(ui.available_width(), 24.0), Sense::hover());
        let editing = matches!(self.edit.as_ref().map(|e|&e.target),Some(EditTarget::Revision(path))if *path==run.directory);
        let hit = ui.interact(
            rect,
            ui.id().with(("project-result", &run.directory)),
            if editing {
                Sense::hover()
            } else {
                Sense::click()
            },
        );
        let selected = self.selected_history.is_none()
            && catalog.selected == Some(stack)
            && self.selected_revision.as_ref() == Some(&run.directory);
        paint_row(ui, rect, &hit, selected);
        let status = match run.status.as_str() {
            "Saved" => GREEN,
            "Rendering" => ACCENT,
            _ => AMBER,
        };
        glyph(
            ui.painter(),
            rect.min + egui::vec2(indent + 29.0, 12.0),
            Glyph::Result,
            status,
        );
        let default_label = catalog
            .node(stack)
            .is_some_and(|node| node.name == run.label);
        let name = if default_label {
            format!("Result {number:02}")
        } else {
            format!("{number:02}  {}", run.label)
        };
        let thumbnail = ui
            .is_rect_visible(rect)
            .then(|| self.previews.file(&run.output, false))
            .flatten();
        previews::ExplorerPreviews::paint(
            ui,
            egui::Rect::from_center_size(
                rect.min + egui::vec2(indent + 29.0, 12.0),
                egui::vec2(22.0, 18.0),
            ),
            thumbnail.as_ref(),
        );
        row_text(
            ui,
            rect,
            indent + 42.0,
            &name,
            &if run.pinned {
                format!("{} · pinned", run.status.to_lowercase())
            } else {
                run.status.to_lowercase()
            },
            INK,
        );
        hit.clone().on_hover_ui(|ui| {
            previews::ExplorerPreviews::hover(ui, thumbnail.as_ref(), &revision_description(run));
            if let Some(error) = self.previews.error(&run.output, false) {
                ui.colored_label(AMBER, error);
            }
        });
        let mut pin = false;
        hit.context_menu(|ui| {
            ui.label(
                RichText::new(format!("{} · {} photos", run.status, run.frames))
                    .small()
                    .color(status),
            );
            if ui
                .add_enabled(!busy, egui::Button::new("Open result"))
                .clicked()
            {
                response.action = Some(ExplorerAction::OpenRun {
                    run: Box::new(run.clone()),
                });
                self.selected_revision = Some(run.directory.clone());
                ui.close();
            }
            if ui.button("Rename result…").clicked() {
                self.edit(EditTarget::Revision(run.directory.clone()), &run.label);
                ui.close();
            }
            if ui
                .button(if run.pinned {
                    "Unpin result"
                } else {
                    "Pin result"
                })
                .clicked()
            {
                pin = true;
                ui.close();
            }
            if ui.button("Reveal in Explorer").clicked() {
                response.action = Some(ExplorerAction::RevealPath {
                    path: run.output.clone(),
                });
                ui.close();
            }
            if ui.button("Copy TIFF path").clicked() {
                ui.ctx().copy_text(run.output.display().to_string());
                ui.close();
            }
        });
        if !editing && ((hit.clicked() && !busy) || hit.secondary_clicked()) {
            hit.request_focus();
            self.selected_history = None;
            catalog.selected = Some(stack);
            self.selected_stack = Some(stack);
            self.selected_revision = Some(run.directory.clone());
            response.changed = true;
            if hit.clicked() {
                response.action = Some(ExplorerAction::OpenRun {
                    run: Box::new(run.clone()),
                });
            }
        }
        if hit.has_focus() && ui.input_mut(|i| i.consume_key(egui::Modifiers::NONE, Key::F2)) {
            self.edit(EditTarget::Revision(run.directory.clone()), &run.label);
        }
        let output = run.output.clone();
        let directory = run.directory.clone();
        if pin {
            catalog.runs[run_index].pinned = !catalog.runs[run_index].pinned;
            response.changed = true;
        }
        if matches!(self.edit.as_ref().map(|e| &e.target), Some(EditTarget::Revision(target)) if *target == directory)
        {
            let edit_rect =
                egui::Rect::from_min_max(rect.min + egui::vec2(indent + 42.0, 0.0), rect.max);
            ui.painter().rect_filled(edit_rect, 0.0, RAISED);
            self.show_editor_at(ui, catalog, response, edit_rect);
        }
        self.show_photo_history(ui, catalog, &output, depth + 1, busy, response);
    }
    fn show_captures(
        &mut self,
        ui: &mut egui::Ui,
        catalog: &Catalog,
        id: NodeId,
        depth: usize,
        busy: bool,
        response: &mut ExplorerResponse,
    ) {
        let Some(draft) = catalog.node(id).and_then(|n| n.stack.as_ref()) else {
            return;
        };
        let (rect, _) =
            ui.allocate_exact_size(egui::vec2(ui.available_width(), 24.0), Sense::hover());
        let hit = ui.interact(rect, ui.id().with(("project-captures", id)), Sense::click());
        let indent = (depth as f32 * 14.0).min(ui.available_width() * 0.42);
        let external = catalog
            .latest_run(id)
            .is_some_and(|run| run.imported.is_some());
        let source = (!external)
            .then(|| draft.sources.first().map(|s| s.path.as_path()))
            .flatten();
        let thumbnail = source
            .filter(|_| ui.is_rect_visible(rect))
            .and_then(|path| self.previews.file(path, true));
        previews::ExplorerPreviews::paint(
            ui,
            egui::Rect::from_center_size(
                rect.min + egui::vec2(indent + 29.0, 12.0),
                egui::vec2(22.0, 18.0),
            ),
            thumbnail.as_ref(),
        );
        row_text(
            ui,
            rect,
            indent + 42.0,
            if external {
                "Captures · not loaded"
            } else {
                "Captures"
            },
            &format!("{} photos", draft.sources.len()),
            MUTED,
        );
        hit.clone().on_hover_ui(|ui| {
            previews::ExplorerPreviews::hover(
                ui,
                thumbnail.as_ref(),
                &format!(
                    "Camera preview · {} source photographs\n{}",
                    draft.sources.len(),
                    draft.source.display()
                ),
            );
            if let Some(path) = source
                && let Some(error) = self.previews.error(path, true)
            {
                ui.colored_label(AMBER, error);
            }
        });
        if hit.clicked() && !busy {
            response.action = Some(ExplorerAction::OpenStack { id });
        }
        hit.context_menu(|ui| {
            if ui.button("Reveal in Explorer").clicked() {
                response.action = Some(ExplorerAction::RevealPath {
                    path: draft.source.clone(),
                });
                ui.close();
            }
            if ui.button("Copy source folder").clicked() {
                ui.ctx().copy_text(draft.source.display().to_string());
                ui.close();
            }
        });
    }
    fn show_photo_history(
        &mut self,
        ui: &mut egui::Ui,
        catalog: &mut Catalog,
        path: &Path,
        depth: usize,
        busy: bool,
        response: &mut ExplorerResponse,
    ) {
        let versions: Vec<_> = catalog
            .photo_versions
            .iter()
            .filter(|v| v.owner.output == path)
            .cloned()
            .collect();
        for version in versions.iter().rev() {
            let indent = (depth as f32 * 14.0).min(ui.available_width() * 0.42);
            let (rect, _) =
                ui.allocate_exact_size(egui::vec2(ui.available_width(), 24.0), Sense::hover());
            let editing = matches!(self.edit.as_ref().map(|e|&e.target),Some(EditTarget::Version(id))if *id==version.id);
            let hit = ui.interact(
                rect,
                ui.id().with(("photo-version", &version.id)),
                if editing {
                    Sense::hover()
                } else {
                    Sense::click()
                },
            );
            paint_row(
                ui,
                rect,
                &hit,
                self.selected_history.as_ref() == Some(&version.id),
            );
            glyph(
                ui.painter(),
                rect.min + egui::vec2(indent + 15.0, 12.0),
                Glyph::Result,
                ACCENT,
            );
            let (thumbnail, exact) = if ui.is_rect_visible(rect) {
                self.previews
                    .version(catalog.history_root().as_deref(), version)
            } else {
                (None, false)
            };
            previews::ExplorerPreviews::paint(
                ui,
                egui::Rect::from_center_size(
                    rect.min + egui::vec2(indent + 15.0, 12.0),
                    egui::vec2(22.0, 18.0),
                ),
                thumbnail.as_ref(),
            );
            row_text(ui, rect, indent + 28.0, &version.name, "edit", INK);
            hit.clone().on_hover_ui(|ui| {
                previews::ExplorerPreviews::hover(
                    ui,
                    thumbnail.as_ref(),
                    if exact {
                        "Saved edit · SDR preview"
                    } else {
                        "Base photograph · saved edits appear when this photograph is open"
                    },
                );
                ui.label(
                    "Restore these edits. Your current edits are preserved and can be undone.",
                );
                if let Some(error) = self.previews.error(&version.owner.output, false) {
                    ui.colored_label(AMBER, error);
                }
            });
            let mut restore = hit.clicked() && !busy && !editing;
            hit.context_menu(|ui| {
                restore |= ui
                    .add_enabled(!busy, egui::Button::new("Restore edit version"))
                    .clicked();
                if ui.button("Rename version…").clicked() {
                    self.edit(EditTarget::Version(version.id.clone()), &version.name);
                    ui.close();
                }
                if ui.button("Reveal photograph in Explorer").clicked() {
                    response.action = Some(ExplorerAction::RevealPath {
                        path: version.owner.output.clone(),
                    });
                    ui.close();
                }
                if let Some(root) = catalog.history_root()
                    && ui.button("Reveal saved edits in Explorer").clicked()
                {
                    response.action = Some(ExplorerAction::RevealPath {
                        path: root.join(format!("{}.json", version.id)),
                    });
                    ui.close();
                }
                if ui.button("Copy photograph path").clicked() {
                    ui.ctx()
                        .copy_text(version.owner.output.display().to_string());
                    ui.close();
                }
            });
            if restore {
                hit.request_focus();
                self.selected_history = Some(version.id.clone());
                response.action = Some(ExplorerAction::RestoreVersion {
                    id: version.id.clone(),
                });
            }
            if matches!(self.edit.as_ref().map(|e|&e.target),Some(EditTarget::Version(id))if *id==version.id)
            {
                let edit_rect =
                    egui::Rect::from_min_max(rect.min + egui::vec2(indent + 28.0, 0.0), rect.max);
                ui.painter().rect_filled(edit_rect, 0.0, RAISED);
                self.show_editor_at(ui, catalog, response, edit_rect);
            }
            if hit.has_focus() && ui.input_mut(|i| i.consume_key(egui::Modifiers::NONE, Key::F2)) {
                self.edit(EditTarget::Version(version.id.clone()), &version.name);
            }
            for export in catalog
                .photo_exports
                .iter()
                .filter(|e| e.version == version.id)
            {
                let (rect, _) =
                    ui.allocate_exact_size(egui::vec2(ui.available_width(), 24.0), Sense::hover());
                let hit = ui.interact(
                    rect,
                    ui.id().with(("photo-export", &export.id)),
                    Sense::click(),
                );
                paint_row(
                    ui,
                    rect,
                    &hit,
                    self.selected_history.as_ref() == Some(&export.id),
                );
                glyph(
                    ui.painter(),
                    rect.min + egui::vec2(indent + 29.0, 12.0),
                    Glyph::Result,
                    GREEN,
                );
                let name = export
                    .path
                    .file_name()
                    .unwrap_or_default()
                    .to_string_lossy();
                row_text(
                    ui,
                    rect,
                    indent + 42.0,
                    &name,
                    if export.settings.hdr { "HDR" } else { "SDR" },
                    MUTED,
                );
                let decoded = export.settings.format != strehl_edit::ExportFormat::Avif
                    && export.settings.color_space == strehl_edit::OutputColorSpace::Srgb
                    && !export.settings.hdr;
                let export_thumbnail = if decoded && ui.is_rect_visible(rect) {
                    self.previews.file(&export.path, false)
                } else {
                    thumbnail.clone()
                };
                previews::ExplorerPreviews::paint(
                    ui,
                    egui::Rect::from_center_size(
                        rect.min + egui::vec2(indent + 29.0, 12.0),
                        egui::vec2(22.0, 18.0),
                    ),
                    export_thumbnail.as_ref(),
                );
                hit.clone().on_hover_ui(|ui| {
                    let preview_label = if decoded {
                        "Export preview"
                    } else if exact {
                        "Saved edit preview · export encoding not shown"
                    } else {
                        "Base photograph · export encoding not shown"
                    };
                    previews::ExplorerPreviews::hover(
                        ui,
                        export_thumbnail.as_ref(),
                        &format!(
                            "{preview_label}\n{}\n{:?} · {} · quality {}\nFrom edit: {}",
                            export.path.display(),
                            export.settings.format,
                            export.settings.color_space.label(),
                            export.settings.quality,
                            version.name
                        ),
                    );
                    if let Some(error) = self.previews.error(&export.path, false) {
                        ui.colored_label(AMBER, error);
                    }
                });
                let mut open = hit.clicked() && !busy;
                hit.context_menu(|ui| {
                    open |= ui
                        .add_enabled(!busy, egui::Button::new("Open exported photograph"))
                        .clicked();
                    if ui.button("Reveal in Explorer").clicked() {
                        response.action = Some(ExplorerAction::RevealPath {
                            path: export.path.clone(),
                        });
                        ui.close();
                    }
                    if ui.button("Copy export path").clicked() {
                        ui.ctx().copy_text(export.path.display().to_string());
                        ui.close();
                    }
                });
                if open {
                    self.selected_history = Some(export.id.clone());
                    response.action = Some(ExplorerAction::OpenExport {
                        id: export.id.clone(),
                    });
                }
            }
        }
    }
    fn matches_branch(&self, catalog: &Catalog, node: &ProjectNode) -> bool {
        let query = self.filter.trim().to_lowercase();
        if query.is_empty() || node.name.to_lowercase().contains(&query) {
            return true;
        }
        // A matching project/folder reveals its contents as well as ancestors
        // of matching stacks. Searching a project must not make it look empty.
        let mut parent = node.parent;
        while let Some(id) = parent {
            let Some(ancestor) = catalog.node(id) else {
                break;
            };
            if ancestor.name.to_lowercase().contains(&query) {
                return true;
            }
            parent = ancestor.parent;
        }
        if catalog.photo_versions.iter().any(|v| {
            v.owner.stack == Some(node.id)
                && (v.name.to_lowercase().contains(&query)
                    || catalog.photo_exports.iter().any(|e| {
                        e.version == v.id
                            && e.path.to_string_lossy().to_lowercase().contains(&query)
                    }))
        }) {
            return true;
        }
        if node.revisions.iter().any(|p| {
            catalog
                .runs
                .iter()
                .any(|r| r.directory == *p && r.label.to_lowercase().contains(&query))
        }) {
            return true;
        }
        catalog
            .nodes
            .iter()
            .filter(|child| child.parent == Some(node.id))
            .any(|child| self.matches_branch(catalog, child))
    }
    fn show_selected(
        &mut self,
        ui: &mut egui::Ui,
        catalog: &mut Catalog,
        id: NodeId,
        response: &mut ExplorerResponse,
    ) {
        let Some(node) = catalog.node(id) else {
            return;
        };
        let label = match node.kind {
            NodeKind::Project => "Project",
            NodeKind::Folder => "Folder",
            NodeKind::Stack => "Stack",
        };
        let details = if let Some(draft) = &node.stack {
            format!(
                "{label} · {} photos · {} results",
                draft.sources.len(),
                node.revisions.len()
            )
        } else {
            let count = catalog
                .nodes
                .iter()
                .filter(|n| n.parent == Some(id))
                .count();
            format!("{label} · {count} items")
        };
        let (row, _) =
            ui.allocate_exact_size(egui::vec2(ui.available_width(), 21.0), Sense::hover());
        let note_rect =
            egui::Rect::from_min_max(egui::pos2(row.right() - 47.0, row.top()), row.max);
        row_text(
            ui,
            egui::Rect::from_min_max(row.min, egui::pos2(note_rect.left(), row.bottom())),
            0.0,
            &details,
            "",
            MUTED,
        );
        if command(ui, note_rect, "Notes", Glyph::None, false, true).clicked() {
            self.notes_open = !self.notes_open;
        }
        if let Some(draft) = &node.stack {
            let source = draft.source.display().to_string();
            ui.add(egui::Label::new(RichText::new(&source).size(9.0).color(MUTED)).truncate())
                .on_hover_text(source);
        } else {
            theme::caption(ui, "New stack adds source photos here");
        }
        if self.notes_open {
            ui.add_space(4.0);
            let edit = ui.add(
                egui::TextEdit::multiline(&mut catalog.node_mut(id).unwrap().notes)
                    .hint_text("Capture notes, next changes…")
                    .char_limit(4000)
                    .desired_rows(2)
                    .desired_width((ui.available_width() - 8.0).max(1.0)),
            );
            self.notes_editor = Some(edit.id);
            response.changed |= edit.changed();
        } else {
            self.notes_editor = None;
        }
    }
}
const SELECTED: Color32 = Color32::from_rgb(43, 49, 61);
#[derive(Clone, Copy)]
enum Glyph {
    None,
    Add,
    Project,
    Folder,
    Stack,
    Result,
    Right,
    Down,
    Check,
    Close,
}
fn glyph(painter: &egui::Painter, center: egui::Pos2, glyph: Glyph, color: Color32) {
    use crate::workspace_icons::Icon;
    let icon = match glyph {
        Glyph::None => return,
        Glyph::Add => Icon::Add,
        Glyph::Project => Icon::Projects,
        Glyph::Folder => Icon::Folder,
        Glyph::Stack => Icon::Stack,
        Glyph::Result => Icon::Photograph,
        Glyph::Right => Icon::Right,
        Glyph::Down => Icon::Down,
        Glyph::Check => Icon::Check,
        Glyph::Close => Icon::Close,
    };
    crate::workspace_icons::paint(painter, center, 14.0, icon, color);
}

fn command(
    ui: &mut egui::Ui,
    rect: egui::Rect,
    text: &str,
    icon: Glyph,
    primary: bool,
    enabled: bool,
) -> egui::Response {
    let hit = ui.interact(
        rect,
        ui.id()
            .with(("explorer-command", text, rect.min.y.to_bits())),
        if enabled {
            Sense::click()
        } else {
            Sense::hover()
        },
    );
    let painter = ui.painter_at(rect);
    if primary || hit.hovered() {
        painter.rect_filled(rect, 0.0, if primary { SELECTED } else { RAISED });
    }
    let color = if !enabled {
        MUTED.gamma_multiply(0.5)
    } else if primary {
        ACCENT
    } else {
        INK
    };
    let icon_width = if matches!(icon, Glyph::None) {
        0.0
    } else {
        17.0
    };
    glyph(
        &painter,
        rect.left_center() + egui::vec2(12.0, 0.0),
        icon,
        color,
    );
    painter.text(
        rect.left_center() + egui::vec2(8.0 + icon_width, 0.0),
        Align2::LEFT_CENTER,
        text,
        FontId::proportional(11.0),
        color,
    );
    hit.widget_info(|| egui::WidgetInfo::labeled(egui::WidgetType::Button, enabled, text));
    hit
}
fn icon_button(ui: &mut egui::Ui, rect: egui::Rect, id: &str, icon: Glyph) -> egui::Response {
    let hit = ui.interact(rect, ui.id().with(id), Sense::click());
    if hit.hovered() {
        ui.painter().rect_filled(rect, 0.0, RAISED);
    }
    glyph(
        ui.painter(),
        rect.center(),
        icon,
        if hit.hovered() { ACCENT } else { INK },
    );
    // A real widget identity supplies a label for accessibility and test targeting
    // without relying on a font's support for pictographic Unicode characters.
    hit.widget_info(|| {
        egui::WidgetInfo::labeled(
            egui::WidgetType::Button,
            true,
            match icon {
                Glyph::Check => "Save name",
                _ => "Cancel",
            },
        )
    });
    hit
}
fn paint_row(ui: &egui::Ui, rect: egui::Rect, hit: &egui::Response, selected: bool) {
    if selected {
        ui.painter().rect_filled(rect, 0.0, SELECTED);
        ui.painter().vline(
            rect.left() + 0.5,
            rect.y_range(),
            Stroke::new(1.0 / ui.ctx().pixels_per_point(), ACCENT),
        );
    } else if hit.hovered() {
        ui.painter().rect_filled(rect, 0.0, RAISED);
    }
}
fn row_text(ui: &egui::Ui, rect: egui::Rect, left: f32, title: &str, suffix: &str, color: Color32) {
    let painter = ui.painter_at(rect);
    let suffix_galley = painter.layout_no_wrap(suffix.to_owned(), FontId::proportional(9.0), MUTED);
    let title_right = rect.right()
        - 8.0
        - if suffix.is_empty() {
            0.0
        } else {
            suffix_galley.size().x + 8.0
        };
    let title_rect = egui::Rect::from_min_max(
        rect.min + egui::vec2(left, 0.0),
        egui::pos2(title_right.max(rect.left() + left), rect.bottom()),
    );
    let mut title_job = egui::text::LayoutJob::simple(
        title.to_owned(),
        FontId::proportional(11.0),
        color,
        title_rect.width().max(1.0),
    );
    title_job.wrap.max_rows = 1;
    title_job.wrap.break_anywhere = true;
    let title_galley = painter.layout_job(title_job);
    painter
        .with_clip_rect(title_rect.intersect(ui.clip_rect()))
        .galley(
            title_rect.left_center() - egui::vec2(0.0, title_galley.size().y * 0.5),
            title_galley,
            color,
        );
    painter.galley(
        rect.right_center()
            - egui::vec2(suffix_galley.size().x + 8.0, suffix_galley.size().y * 0.5),
        suffix_galley,
        MUTED,
    );
}
fn divider(ui: &mut egui::Ui) {
    let (rect, _) = ui.allocate_exact_size(egui::vec2(ui.available_width(), 1.0), Sense::hover());
    ui.painter().hline(
        rect.x_range(),
        rect.center().y,
        Stroke::new(1.0 / ui.ctx().pixels_per_point(), LINE),
    );
}
/// A child whose measured content cannot enlarge the already allocated row.
/// Clipping is local; ComboBox popups still occupy their own overlay layer.
fn bounded_row_cell(ui: &mut egui::Ui, rect: egui::Rect, id: &str) -> egui::Ui {
    let mut child = ui.new_child(
        egui::UiBuilder::new()
            .id_salt(id)
            .max_rect(rect)
            .layout(egui::Layout::left_to_right(egui::Align::Center)),
    );
    child.set_clip_rect(ui.clip_rect().intersect(rect));
    child
}
fn revision_description(run: &Run) -> String {
    let age = timestamp().saturating_sub(run.created);
    let when = if age < 60 {
        "just now".into()
    } else if age < 3600 {
        format!("{}m ago", age / 60)
    } else if age < 86400 {
        format!("{}h ago", age / 3600)
    } else {
        format!("{}d ago", age / 86400)
    };
    format!(
        "{} · {} captures · {}\n{}\nBands: {} · gate: {} · exposure: {}\n{} · {} · {}\n{}",
        run.status,
        run.frames,
        when,
        run.label,
        run.settings
            .pyramid_bands
            .map_or_else(|| "engine default".into(), |v| v.to_string()),
        run.gate
            .map_or_else(|| "engine default".into(), |v| format!("{v:.2}")),
        if run.settings.auto_exposure {
            "automatic".into()
        } else {
            run.exposure
                .map_or_else(|| "engine default".into(), |v| format!("{v:+.2} EV"))
        },
        if run.settings.binned {
            "Binned"
        } else {
            "Full resolution"
        },
        if run.settings.correct_lateral_ca {
            "CA enabled"
        } else {
            "CA disabled"
        },
        if run.settings.crop_to_coverage {
            "Coverage crop"
        } else {
            "Default coverage"
        },
        run.source.display()
    )
}
#[cfg(test)]
#[path = "project-explorer-tests.rs"]
mod tests;
