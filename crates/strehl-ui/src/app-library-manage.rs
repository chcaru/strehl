//! Library management (owner feedback, 2026-11-21: "how do i delete
//! something there?"): delete with a confirmation that states what happens,
//! move stacks between subjects and subjects between collections, merge
//! subjects, and Show in Explorer.
//!
//! Removing from the library is a catalog edit through the undo journal
//! (`ProjectExplorer::organize_removing`), done at once. Deleting files is
//! opt-in per category, measured and then carried out on workers
//! (`library-delete.rs`); the source photographs need a second, explicit
//! confirmation that says whether they go to the Recycle Bin or are deleted
//! permanently. Stacks that are rendering, waiting in the queue or being
//! captured are kept, and the open stack's files are never deleted.
use super::studio_route::Route;
use super::*;
use crate::{
    library_delete::{
        self as delete, CategoryMeasure, DeleteMeasure, DeletePlan, DeleteReport, Disposal, Guard,
    },
    library_paint::{bytes, plural},
    library_station::LibraryIntent,
    notices::Severity,
    studio_theme, studio_widgets as w,
    workspace_history::{
        FileCategory, NodeId, NodeKind, OwnedFiles, Refusal, RemovalCounts, RemovalScope,
        path_within,
    },
};
use std::sync::{
    Arc,
    atomic::{AtomicUsize, Ordering},
};

/// The confirmation of a deletion, open until confirmed or cancelled.
pub(super) struct DeleteDialog {
    pub title: String,
    pub scope: RemovalScope,
    pub counts: RemovalCounts,
    /// Stacks that stay in the library, and why.
    pub kept: Vec<(String, String)>,
    pub owned: OwnedFiles,
    pub measure: Option<DeleteMeasure>,
    task: Option<Task<DeleteMeasure>>,
    guard: Guard,
    /// Delete Strehl's render folders too.
    pub renders: bool,
    /// Delete the source photographs too (off by default).
    pub sources: bool,
    /// The second step: confirming the source photographs.
    pub confirming_sources: bool,
}
impl DeleteDialog {
    pub(super) fn measuring(&self) -> bool {
        self.task.is_some()
    }
}

/// Deletion running on a worker.
struct Deleting {
    task: Task<DeleteReport>,
    done: Arc<AtomicUsize>,
    items: usize,
}

#[derive(Default)]
pub(super) struct ManageState {
    pub dialog: Option<DeleteDialog>,
    deleting: Option<Deleting>,
    /// Errors from Show in Explorer, which runs on its own thread.
    reveal: Option<(mpsc::Sender<String>, mpsc::Receiver<String>)>,
    /// `--overlay library-*` / `subject-*`, applied once the view painted.
    pub overlay: Option<String>,
}

/// "1 subject, 4 stacks, 6 renders, 2 versions and 1 export".
fn counts_line(counts: &RemovalCounts) -> String {
    let mut parts = Vec::new();
    if counts.subjects > 0 {
        parts.push(plural(counts.subjects, "subject", "subjects"));
    }
    parts.push(plural(counts.stacks, "stack", "stacks"));
    if counts.renders > 0 {
        parts.push(plural(counts.renders, "render", "renders"));
    }
    if counts.versions > 0 {
        parts.push(plural(counts.versions, "version", "versions"));
    }
    if counts.exports > 0 {
        parts.push(plural(counts.exports, "export record", "export records"));
    }
    match parts.len() {
        1 => parts.remove(0),
        _ => {
            let last = parts.pop().unwrap();
            format!("{} and {last}", parts.join(", "))
        }
    }
}
/// "1,488 files".
fn counted(count: usize, one: &str, many: &str) -> String {
    let digits = count.to_string();
    let mut grouped = String::new();
    for (index, digit) in digits.chars().enumerate() {
        if index > 0 && (digits.len() - index).is_multiple_of(3) {
            grouped.push(',');
        }
        grouped.push(digit);
    }
    format!("{grouped} {}", if count == 1 { one } else { many })
}
/// "D:\StrehlCaptures\stack-1 and 2 more".
fn folders_line(folders: &[&Path]) -> String {
    let Some(first) = folders.first() else {
        return String::new();
    };
    let shown = crate::display_path::display_path(first);
    match folders.len() {
        1 => shown,
        n => format!("{shown} and {} more", n - 1),
    }
}
/// Where a category's files would go.
fn disposal_line(total: &CategoryMeasure) -> String {
    match (total.disposal, &total.permanent_because) {
        (Disposal::RecycleBin, _) => {
            let bins: Vec<&str> = total.bins.iter().map(|b| b.volume.as_str()).collect();
            format!("to the Recycle Bin on {}", bins.join(", "))
        }
        (Disposal::Permanent, Some(why)) => format!("deleted permanently: {why}"),
        (Disposal::Permanent, None) => "deleted permanently".into(),
    }
}
fn refusal_line(refusal: &Refusal) -> String {
    let what = match refusal.category {
        FileCategory::Renders => "render folder",
        FileCategory::Sources => "photographs",
    };
    let name = if refusal.name.is_empty() {
        crate::display_path::display_path(&refusal.path)
    } else {
        refusal.name.clone()
    };
    format!("{name} · {what}: {}", refusal.reason)
}

impl StrehlApp {
    /// Management intents from the Library or a subject page.
    pub(super) fn library_manage(&mut self, ctx: &egui::Context, intent: LibraryIntent) {
        match intent {
            LibraryIntent::Delete(ids) => self.library_open_delete(ctx, &ids),
            LibraryIntent::MoveStacks { stacks, subject } => {
                let result = self
                    .project_explorer
                    .organize(&mut self.catalog, |catalog| {
                        for &stack in &stacks {
                            catalog.can_move(stack, Some(subject))?;
                        }
                        for &stack in &stacks {
                            catalog.move_node(stack, Some(subject))?;
                        }
                        Ok(())
                    });
                self.library_moved(result, plural(stacks.len(), "stack", "stacks"), subject);
            }
            LibraryIntent::MoveSubjects {
                subjects,
                collection,
            } => {
                let result = self
                    .project_explorer
                    .organize(&mut self.catalog, |catalog| {
                        for &subject in &subjects {
                            catalog.can_move(subject, Some(collection))?;
                        }
                        for &subject in &subjects {
                            catalog.move_node(subject, Some(collection))?;
                        }
                        Ok(())
                    });
                self.library_moved(
                    result,
                    plural(subjects.len(), "subject", "subjects"),
                    collection,
                );
            }
            LibraryIntent::MoveSubjectsToNewCollection(subjects) => {
                let name = self.library_unique_name("New collection");
                let made = self
                    .project_explorer
                    .organize(&mut self.catalog, |catalog| {
                        let collection = catalog.create_project(&name)?;
                        for &subject in &subjects {
                            catalog.can_move(subject, Some(collection))?;
                        }
                        for &subject in &subjects {
                            catalog.move_node(subject, Some(collection))?;
                        }
                        Ok(collection)
                    });
                match made {
                    Ok(collection) => {
                        self.persist_catalog();
                        self.library_rename(collection);
                    }
                    Err(error) => self.library_notice(Severity::Warning, format!("{error:#}")),
                }
            }
            LibraryIntent::MergeSubjects { into, others } => {
                let merged =
                    self.project_explorer
                        .organize_removing(&mut self.catalog, |catalog| {
                            let emptied = catalog.merge_subjects(into, &others)?;
                            Ok((emptied.len(), emptied))
                        });
                match merged {
                    Ok((count, _)) => {
                        self.persist_catalog();
                        let name = self
                            .catalog
                            .node(into)
                            .map(|n| n.name.clone())
                            .unwrap_or_default();
                        self.library_notice(
                            Severity::Done,
                            format!(
                                "Merged {} into \"{name}\" · Ctrl Z undoes it",
                                plural(count, "subject", "subjects")
                            ),
                        );
                        if let Route::Subject(open) = self.shell.navigator.route()
                            && others.contains(open)
                        {
                            self.navigate(Route::Subject(into));
                        }
                    }
                    Err(error) => self.library_notice(Severity::Warning, format!("{error:#}")),
                }
            }
            LibraryIntent::ShowSources(id) => self.library_show(id, false),
            LibraryIntent::ShowRenders(id) => self.library_show(id, true),
            _ => {}
        }
        ctx.request_repaint();
    }

    fn library_moved(&mut self, result: anyhow::Result<()>, what: String, to: NodeId) {
        match result {
            Ok(()) => {
                self.persist_catalog();
                let name = self
                    .catalog
                    .node(to)
                    .map(|n| n.name.clone())
                    .unwrap_or_default();
                self.library_notice(
                    Severity::Done,
                    format!("Moved {what} to \"{name}\" · Ctrl Z undoes it"),
                );
            }
            Err(error) => self.library_notice(Severity::Warning, format!("{error:#}")),
        }
    }

    /// What Show in Explorer opens for a subject or stack: its photographs
    /// folder (for a subject whose stacks are camera folders of one folder,
    /// that folder), or its newest render's photograph, with the render
    /// folder as the fallback. Catalog only; no I/O.
    pub(super) fn library_reveal_target(
        &self,
        id: NodeId,
        renders: bool,
    ) -> Option<(PathBuf, Option<PathBuf>)> {
        let node = self.catalog.node(id)?;
        let stacks: Vec<NodeId> = match node.kind {
            NodeKind::Stack => vec![id],
            NodeKind::Subject => self.catalog.stacks_of(id),
            _ => Vec::new(),
        };
        if renders {
            return stacks
                .iter()
                .filter_map(|&s| self.catalog.node(s))
                .flat_map(|n| n.revisions.iter())
                .filter_map(|d| self.catalog.runs.iter().find(|r| &r.directory == d))
                .max_by_key(|r| r.created)
                .map(|r| (r.output.clone(), Some(r.directory.clone())));
        }
        let folders: Vec<PathBuf> = stacks
            .iter()
            .filter_map(|&s| self.catalog.node(s)?.stack.as_ref())
            .map(|d| d.source.clone())
            .collect();
        let parent = folders.first().and_then(|f| f.parent()).filter(|p| {
            folders.len() > 1
                && p.parent().is_some()
                && folders.iter().all(|f| f.parent() == Some(*p))
        });
        match parent {
            Some(parent) => Some((parent.to_path_buf(), None)),
            None => folders.last().cloned().map(|f| (f, None)),
        }
    }

    /// Show in Explorer, from a thread: Explorer validates the path and a
    /// slow volume must not stall the window.
    fn library_show(&mut self, id: NodeId, renders: bool) {
        let Some((path, fallback)) = self.library_reveal_target(id, renders) else {
            self.library_notice(Severity::Info, "Nothing to show yet".into());
            return;
        };
        let (sender, _) = self.library.manage.reveal.get_or_insert_with(mpsc::channel);
        let sender = sender.clone();
        std::thread::spawn(move || {
            let shown = match crate::reveal_path::reveal(&path) {
                Err(_) if fallback.as_ref().is_some_and(|f| f.is_dir()) => {
                    crate::reveal_path::reveal(fallback.as_ref().unwrap())
                }
                other => other,
            };
            if let Err(error) = shown {
                let _ = sender.send(format!("{error:#}"));
            }
        });
    }

    /// Open the confirmation for deleting `ids` (subjects and stacks).
    pub(super) fn library_open_delete(&mut self, ctx: &egui::Context, ids: &[NodeId]) {
        if self.library.manage.deleting.is_some() {
            self.library_notice(
                Severity::Info,
                "Wait for the deletion under way to finish".into(),
            );
            return;
        }
        let scope = self.catalog.removal_scope(ids);
        if scope.is_empty() {
            return;
        }
        // Kept in the library: what renders, waits or is being captured.
        let running = self
            .job
            .as_ref()
            .and(self.pending_stack.or(self.active_stack));
        let waiting: Vec<NodeId> = self.activity_hub.queue.stacks().collect();
        let capturing_stack = self.library.rig.as_ref().and_then(|r| r.stack);
        let capturing_folder = self.shell.rig.in_progress.as_ref().map(PathBuf::from);
        let mut kept = Vec::new();
        let mut kept_ids = Vec::new();
        for &stack in &scope.stacks {
            let Some(node) = self.catalog.node(stack) else {
                continue;
            };
            let why = if Some(stack) == running {
                Some("stacking now")
            } else if waiting.contains(&stack) {
                Some("waiting in the stack queue")
            } else if Some(stack) == capturing_stack
                || capturing_folder.as_deref().is_some_and(|folder| {
                    node.stack.as_ref().is_some_and(|d| {
                        path_within(&d.source, folder) && path_within(folder, &d.source)
                    })
                })
            {
                Some("being captured now")
            } else {
                None
            };
            if let Some(why) = why {
                kept.push((node.name.clone(), why.to_owned()));
                kept_ids.push(stack);
            }
        }
        let scope = self.catalog.scope_without(&scope, &kept_ids);
        let counts = self.catalog.removal_counts(&scope);
        let mut owned = self.catalog.owned_files(&scope);
        // The open stack leaves the library but keeps its files: the
        // workspace is reading them, and edits are saved beside the render.
        let open_stack = self.active_stack.filter(|id| scope.stacks.contains(id));
        let open_render = self.result.clone();
        let open_name = open_stack
            .and_then(|id| self.catalog.node(id))
            .map(|n| n.name.clone())
            .unwrap_or_default();
        let open_reason = "open in the workspace: open another stack to delete its files";
        owned.renders.retain(|render| {
            let open = Some(render.stack) == open_stack
                || open_render
                    .as_deref()
                    .is_some_and(|result| path_within(result, &render.directory));
            if open {
                owned.refused.push(Refusal {
                    category: FileCategory::Renders,
                    name: open_name.clone(),
                    path: render.directory.clone(),
                    reason: open_reason.into(),
                });
            }
            !open
        });
        owned.sources.retain(|sources| {
            let open = Some(sources.stack) == open_stack;
            if open {
                owned.refused.push(Refusal {
                    category: FileCategory::Sources,
                    name: sources.name.clone(),
                    path: sources.folder.clone(),
                    reason: open_reason.into(),
                });
            }
            !open
        });
        let title = match (scope.subjects.as_slice(), scope.stacks.as_slice()) {
            ([], []) => "Nothing can be deleted now".to_owned(),
            ([subject], _) if scope.subjects.len() == 1 => {
                let name = self
                    .catalog
                    .node(*subject)
                    .map(|n| n.name.clone())
                    .unwrap_or_default();
                format!("Delete \"{name}\"")
            }
            ([], [stack]) => {
                let name = self
                    .catalog
                    .node(*stack)
                    .map(|n| n.name.clone())
                    .unwrap_or_default();
                format!("Delete stack \"{name}\"")
            }
            ([], stacks) => format!("Delete {} stacks", stacks.len()),
            (subjects, _) => format!("Delete {} subjects", subjects.len()),
        };
        let guard = Guard {
            capturing: capturing_folder,
        };
        let task = {
            let owned = owned.clone();
            let guard = guard.clone();
            let notify = ctx.clone();
            jobs::spawn_notifying_task(
                "strehl-library-measure",
                move |cancelled| Ok(delete::measure(&owned, &guard, &cancelled)),
                move || notify.request_repaint(),
            )
        };
        self.library.manage.dialog = Some(DeleteDialog {
            title,
            scope,
            counts,
            kept,
            owned,
            measure: None,
            task: Some(task),
            guard,
            renders: false,
            sources: false,
            confirming_sources: false,
        });
    }

    /// The Library's management work: the dialog's measurement, deletion,
    /// Show in Explorer's errors and the launch overlay. From `tick`.
    pub(super) fn library_poll_manage(&mut self, ctx: &egui::Context) {
        let manage = &mut self.library.manage;
        if let Some(dialog) = manage.dialog.as_mut()
            && let Some(task) = &dialog.task
            && let Ok(result) = task.receiver.try_recv()
        {
            dialog.task = None;
            match result {
                Ok(measure) => dialog.measure = Some(measure),
                Err(error) => {
                    let text = format!("Measuring what to delete failed: {error}");
                    self.shell.notices.push(
                        Severity::Warning,
                        crate::notices::Source::Library,
                        text,
                        None,
                    );
                }
            }
            ctx.request_repaint();
        }
        let manage = &mut self.library.manage;
        if let Some(deleting) = &manage.deleting {
            match deleting.task.receiver.try_recv() {
                Ok(result) => {
                    manage.deleting = None;
                    self.library.storage_read = None;
                    match result {
                        Ok(report) => self.library_deleted(&report),
                        Err(error) => self.library_notice(
                            Severity::Failure,
                            format!("Deleting files failed: {error}"),
                        ),
                    }
                    ctx.request_repaint();
                }
                Err(_) => ctx.request_repaint_after(Duration::from_millis(200)),
            }
        }
        let errors: Vec<String> = self
            .library
            .manage
            .reveal
            .as_ref()
            .map(|(_, receiver)| receiver.try_iter().collect())
            .unwrap_or_default();
        for error in errors {
            self.library_notice(Severity::Warning, error);
        }
    }

    /// Deletion progress for the top bar's notices ("3 of 12").
    pub(super) fn library_deleting(&self) -> Option<(usize, usize)> {
        self.library
            .manage
            .deleting
            .as_ref()
            .map(|d| (d.done.load(Ordering::Relaxed), d.items))
    }

    fn library_deleted(&mut self, report: &DeleteReport) {
        if report.files > 0 || report.folders_removed > 0 {
            let place = if report.recycled == report.files && report.files > 0 {
                "moved to the Recycle Bin"
            } else if report.recycled == 0 {
                "deleted permanently"
            } else {
                "deleted (some to the Recycle Bin, the rest permanently)"
            };
            self.library_notice(
                Severity::Done,
                format!(
                    "{} ({}) {place}",
                    plural(report.files, "file", "files"),
                    bytes(report.bytes)
                ),
            );
        }
        if !report.folders_kept.is_empty() {
            self.library_notice(
                Severity::Info,
                format!(
                    "{} kept: other files are in them",
                    plural(report.folders_kept.len(), "folder", "folders")
                ),
            );
        }
        for line in &report.failed {
            self.library_notice(Severity::Warning, format!("Not deleted: {line}"));
        }
    }

    /// Images, folder scans and measurements the Library still waits for.
    pub(super) fn library_manage_pending(&self) -> bool {
        self.library
            .manage
            .dialog
            .as_ref()
            .is_some_and(DeleteDialog::measuring)
            || self.library.manage.overlay.is_some()
    }

    /// Confirmed: out of the library now (undoable), files on a worker.
    fn library_confirm_delete(&mut self, ctx: &egui::Context) {
        let Some(dialog) = self.library.manage.dialog.take() else {
            return;
        };
        if dialog.scope.is_empty() {
            return;
        }
        let ids = dialog.scope.ids();
        let removed = self
            .project_explorer
            .organize_removing(&mut self.catalog, |_| Ok(((), ids.clone())));
        let records = match removed {
            Ok((_, records)) => records,
            Err(error) => {
                self.library_notice(Severity::Warning, format!("{error:#}"));
                return;
            }
        };
        // What referred to a removed stack no longer does.
        let gone = |id: &NodeId| ids.contains(id);
        if self.active_stack.is_some_and(|id| gone(&id)) {
            self.active_stack = None;
        }
        if self.pending_stack.is_some_and(|id| gone(&id)) {
            self.pending_stack = None;
        }
        if self.capture_parent.is_some_and(|id| gone(&id)) {
            self.capture_parent = None;
        }
        if let Some(target) = &self.library.target
            && (target.subject.is_some_and(|id| gone(&id))
                || target.from_stack.is_some_and(|id| gone(&id)))
        {
            self.library.target = None;
        }
        self.persist_catalog();
        let what = match (records.subjects(), records.stacks()) {
            (1, _) | (0, 1) => records
                .nodes
                .iter()
                .find(|(_, n)| n.kind == NodeKind::Subject)
                .or(records.nodes.first())
                .map(|(_, n)| format!("\"{}\"", n.name))
                .unwrap_or_default(),
            (0, stacks) => plural(stacks, "stack", "stacks"),
            (subjects, stacks) => format!(
                "{} ({})",
                plural(subjects, "subject", "subjects"),
                plural(stacks, "stack", "stacks")
            ),
        };
        self.library_notice(
            Severity::Done,
            format!("Removed {what} from the library · Ctrl Z puts it back"),
        );
        if let Route::Subject(open) = self.shell.navigator.route()
            && gone(open)
        {
            self.navigate(Route::Library(super::studio_route::LibraryView::All));
        }
        let Some(measure) = dialog.measure else {
            return;
        };
        let plan = DeletePlan {
            render_disposal: dialog.renders.then_some(measure.render_total.disposal),
            renders: if dialog.renders {
                measure.renders
            } else {
                Vec::new()
            },
            source_disposal: dialog.sources.then_some(measure.source_total.disposal),
            sources: if dialog.sources {
                measure.sources
            } else {
                Vec::new()
            },
        };
        if plan.is_empty() {
            return;
        }
        let items = plan.items();
        let done = Arc::new(AtomicUsize::new(0));
        let guard = dialog.guard.clone();
        let worker_done = done.clone();
        let notify = ctx.clone();
        let task = jobs::spawn_notifying_task(
            "strehl-library-delete",
            move |_| Ok(delete::execute(&plan, &guard, &worker_done)),
            move || notify.request_repaint(),
        );
        self.library.manage.deleting = Some(Deleting { task, done, items });
        self.library_notice(
            Severity::Info,
            format!("Deleting {}…", plural(items, "folder", "folders")),
        );
    }

    /// Escape while the confirmation is open steps back or closes it, and
    /// is not also seen by the Library beneath (which would clear the
    /// selection). Call before the Library paints.
    pub(super) fn library_dialog_keys(&mut self, ctx: &egui::Context) {
        let Some(dialog) = self.library.manage.dialog.as_mut() else {
            return;
        };
        if ctx.input_mut(|i| i.consume_key(egui::Modifiers::NONE, egui::Key::Escape)) {
            if dialog.confirming_sources {
                dialog.confirming_sources = false;
            } else {
                self.library.manage.dialog = None;
            }
        }
    }

    /// The deletion confirmation, over the Library.
    pub(super) fn library_delete_window(&mut self, ctx: &egui::Context) {
        let Some(dialog) = self.library.manage.dialog.as_mut() else {
            return;
        };
        let t = studio_theme::tokens(ctx);
        let mut cancel = false;
        let mut confirm = false;
        let frame = egui::Frame::popup(&ctx.style())
            .fill(t.panel)
            .stroke(egui::Stroke::new(1.0_f32, t.line2))
            .inner_margin(egui::Margin::same(22));
        let modal = egui::Modal::new(egui::Id::new("library-delete"))
            .frame(frame)
            .backdrop_color(egui::Color32::from_black_alpha(if t.light {
                60
            } else {
                120
            }))
            .show(ctx, |ui| {
                ui.set_width(540.0);
                ui.spacing_mut().item_spacing = egui::vec2(10.0, 8.0);
                if dialog.confirming_sources {
                    sources_step(ui, dialog, &t, &mut cancel, &mut confirm);
                } else {
                    first_step(ui, dialog, &t, &mut cancel, &mut confirm);
                }
            });
        if modal.should_close() {
            if dialog.confirming_sources {
                dialog.confirming_sources = false;
            } else {
                cancel = true;
            }
        }
        if cancel {
            self.library.manage.dialog = None;
        } else if confirm {
            self.library_confirm_delete(ctx);
        }
    }

    /// `--overlay library-*` and `subject-*`: the management surfaces
    /// offscreen, applied once the view has painted. True when applied.
    pub(super) fn library_apply_overlay(&mut self, ctx: &egui::Context) {
        let Some(overlay) = self.library.manage.overlay.clone() else {
            return;
        };
        let station = &mut self.library.station;
        let subject = &mut self.library.subject;
        let catalog = &self.catalog;
        let done = match overlay.as_str() {
            "library-menu" => station.launch_menu(ctx, catalog, false),
            "library-menu-move" => station.launch_menu(ctx, catalog, true),
            "library-select" => station.launch_select(3),
            "library-list" => {
                station.view = crate::library_station::LibraryView::List;
                station.launch_select(2)
            }
            "subject-menu" => subject.launch_menu(ctx, catalog, false),
            "subject-menu-move" => subject.launch_menu(ctx, catalog, true),
            "subject-select" => subject.launch_select(2),
            "subject-move" => subject.launch_move(ctx, catalog),
            "library-new-menu" => station.launch_new_menu(),
            // The naming of a new subject (`app-library-subject.rs`).
            "library-new-subject" | "library-new-subject-taken" | "subject-new-subject" => {
                let first = station.visible().first().copied();
                let stacks: Vec<NodeId> = match overlay.as_str() {
                    "subject-new-subject" => subject
                        .model()
                        .and_then(|m| m.stacks.first())
                        .map(|s| s.id)
                        .into_iter()
                        .collect(),
                    _ => Vec::new(),
                };
                let name = match (overlay.as_str(), first.and_then(|id| catalog.node(id))) {
                    ("library-new-subject-taken", Some(node)) => node.name.to_lowercase(),
                    ("subject-new-subject", _) => "Harvestman".to_owned(),
                    _ => String::new(),
                };
                self.library_new_subject(None, stacks);
                if let Some(draft) = self.library.new_subject.as_mut() {
                    draft.name = name;
                }
                true
            }
            "library-delete" | "library-delete-sources" | "library-delete-confirm" => {
                match (
                    self.library.manage.dialog.as_mut(),
                    station.visible().first().copied(),
                ) {
                    (None, Some(first)) => {
                        self.library_open_delete(ctx, &[first]);
                        overlay == "library-delete"
                    }
                    (Some(dialog), _) if dialog.measure.is_some() => {
                        let measure = dialog.measure.as_ref().unwrap();
                        dialog.renders = measure.render_total.files > 0;
                        dialog.sources = measure.source_total.files > 0;
                        dialog.confirming_sources =
                            overlay == "library-delete-confirm" && dialog.sources;
                        true
                    }
                    _ => false,
                }
            }
            _ => true,
        };
        if done {
            self.library.manage.overlay = None;
            ctx.request_repaint();
        }
    }
}

/// A category's switch, name, size and where its files would go.
#[allow(clippy::too_many_arguments)]
fn category_row(
    ui: &mut egui::Ui,
    t: &studio_theme::Tokens,
    on: &mut bool,
    name: &str,
    total: Option<&CategoryMeasure>,
    unit: (&str, &str),
    folders: &[&Path],
    extra: Option<String>,
) {
    let enabled = total.is_some_and(|m| m.files > 0);
    if total.is_some() && !enabled {
        *on = false;
    }
    ui.horizontal(|ui| {
        ui.add_enabled_ui(enabled, |ui| w::toggle(ui, on));
        ui.add_space(4.0);
        ui.label(
            egui::RichText::new(name)
                .size(13.5)
                .color(if enabled { t.ink } else { t.ink3 }),
        );
        ui.with_layout(egui::Layout::right_to_left(egui::Align::Center), |ui| {
            let size = match total {
                None => "measuring…".to_owned(),
                Some(m) if m.files == 0 => "nothing to delete".to_owned(),
                Some(m) => format!("{} · {}", counted(m.files, unit.0, unit.1), bytes(m.bytes)),
            };
            ui.label(egui::RichText::new(size).size(12.5).color(t.ink2));
        });
    });
    if let Some(total) = total.filter(|m| m.files > 0) {
        let mut text = folders_line(folders);
        text.push_str(" · ");
        text.push_str(&disposal_line(total));
        ui.horizontal(|ui| {
            ui.add_space(36.0);
            ui.add(
                egui::Label::new(egui::RichText::new(text).size(12.0).color(
                    if total.disposal == Disposal::Permanent {
                        t.warn
                    } else {
                        t.ink3
                    },
                ))
                .wrap(),
            );
        });
    }
    if let Some(extra) = extra {
        ui.horizontal(|ui| {
            ui.add_space(36.0);
            ui.add(egui::Label::new(egui::RichText::new(extra).size(12.0).color(t.ink3)).wrap());
        });
    }
}

fn first_step(
    ui: &mut egui::Ui,
    dialog: &mut DeleteDialog,
    t: &studio_theme::Tokens,
    cancel: &mut bool,
    confirm: &mut bool,
) {
    w::caps(ui, "Delete");
    ui.label(
        egui::RichText::new(&dialog.title)
            .size(studio_theme::scale::STATEMENT + 3.0)
            .color(t.ink),
    );
    ui.add_space(6.0);
    w::section(ui, "From the library", |_| {});
    if dialog.scope.is_empty() {
        ui.label(
            egui::RichText::new("Everything chosen is in use; nothing leaves the library.")
                .size(13.0)
                .color(t.ink2),
        );
    } else {
        ui.add(
            egui::Label::new(
                egui::RichText::new(format!(
                    "{} leave the library.",
                    counts_line(&dialog.counts)
                ))
                .size(13.0)
                .color(t.ink),
            )
            .wrap(),
        );
        ui.label(
            egui::RichText::new(
                "Ctrl Z puts them back. Nothing on disk changes unless you choose it below.",
            )
            .size(12.0)
            .color(t.ink3),
        );
    }
    for (name, why) in &dialog.kept {
        ui.label(
            egui::RichText::new(format!("Kept: {name} · {why}"))
                .size(12.0)
                .color(t.warn),
        );
    }
    ui.add_space(6.0);
    w::section(ui, "On disk", |_| {});
    let measure = dialog.measure.as_ref();
    let render_folders: Vec<&Path> = measure
        .map(|m| m.renders.iter().map(|r| r.directory.as_path()).collect())
        .unwrap_or_default();
    let exports = match (dialog.owned.exports_inside, dialog.owned.exports_kept) {
        (0, 0) => None,
        (0, kept) => Some(format!(
            "{} written elsewhere stay where they are.",
            plural(kept, "Exported file", "Exported files")
        )),
        (inside, 0) => Some(format!(
            "{} inside these folders go with them.",
            plural(inside, "Exported file", "Exported files")
        )),
        (inside, kept) => Some(format!(
            "{} inside these folders go with them; {} elsewhere stay.",
            plural(inside, "exported file", "exported files"),
            kept
        )),
    };
    category_row(
        ui,
        t,
        &mut dialog.renders,
        "Strehl's renders",
        measure.map(|m| &m.render_total),
        ("file", "files"),
        &render_folders,
        exports,
    );
    ui.add_space(4.0);
    let source_folders: Vec<&Path> = measure
        .map(|m| m.sources.iter().map(|s| s.folder.as_path()).collect())
        .unwrap_or_default();
    let stay = measure.map_or(0, |m| m.sources.iter().map(|s| s.others).sum::<usize>());
    let missing = measure.map_or(0, |m| m.sources.iter().map(|s| s.missing).sum::<usize>());
    let mut note = String::from("The camera's originals, off by default");
    if stay > 0 {
        note.push_str(&format!(
            "; {} not recorded by these stacks stay, with their folders",
            plural(stay, "item", "items")
        ));
    } else {
        note.push_str("; a folder goes once nothing else is in it");
    }
    if missing > 0 {
        note.push_str(&format!(
            "; {} already gone",
            plural(missing, "photograph is", "photographs are")
        ));
    }
    note.push('.');
    category_row(
        ui,
        t,
        &mut dialog.sources,
        "Source photographs",
        measure.map(|m| &m.source_total),
        ("file", "files"),
        &source_folders,
        Some(note),
    );
    let refused: Vec<&Refusal> = measure
        .map(|m| m.refused.iter().collect())
        .unwrap_or_else(|| dialog.owned.refused.iter().collect());
    if !refused.is_empty() {
        ui.add_space(4.0);
        w::section(ui, "Not deleted", |_| {});
        for refusal in refused.iter().take(4) {
            ui.add(
                egui::Label::new(
                    egui::RichText::new(refusal_line(refusal))
                        .size(12.0)
                        .color(t.ink2),
                )
                .wrap(),
            );
        }
        if refused.len() > 4 {
            ui.label(
                egui::RichText::new(format!("and {} more", refused.len() - 4))
                    .size(12.0)
                    .color(t.ink3),
            );
        }
    }
    ui.add_space(10.0);
    let files = dialog.renders || dialog.sources;
    let ready = !dialog.scope.is_empty() && (!files || measure.is_some());
    let label = match (dialog.renders, dialog.sources, measure) {
        (_, true, _) => "Delete photographs…".to_owned(),
        (true, false, Some(m)) => format!("Delete {} of renders", bytes(m.render_total.bytes)),
        (true, false, None) => "Delete renders".to_owned(),
        (false, false, _) => "Remove from library".to_owned(),
    };
    ui.horizontal(|ui| {
        *cancel |= ui.add(w::Button::quiet("Cancel")).clicked();
        ui.with_layout(egui::Layout::right_to_left(egui::Align::Center), |ui| {
            let button = if files {
                w::Button::danger(&label)
            } else {
                w::Button::primary(&label)
            };
            if ui.add(button.enabled(ready)).clicked() {
                if dialog.sources {
                    dialog.confirming_sources = true;
                } else {
                    *confirm = true;
                }
            }
        });
    });
}

fn sources_step(
    ui: &mut egui::Ui,
    dialog: &mut DeleteDialog,
    t: &studio_theme::Tokens,
    cancel: &mut bool,
    confirm: &mut bool,
) {
    let Some(measure) = &dialog.measure else {
        dialog.confirming_sources = false;
        return;
    };
    let total = &measure.source_total;
    let folders: Vec<&Path> = measure.sources.iter().map(|s| s.folder.as_path()).collect();
    w::caps(ui, "Delete the source photographs");
    ui.horizontal(|ui| {
        w::mark(ui, w::Mark::Failed);
        ui.label(
            egui::RichText::new(format!(
                "{} ({}) from {}?",
                counted(total.files, "file", "files"),
                bytes(total.bytes),
                plural(total.folders, "folder", "folders")
            ))
            .size(studio_theme::scale::STATEMENT + 3.0)
            .color(t.ink),
        );
    });
    ui.add(
        egui::Label::new(
            egui::RichText::new(format!(
                "These are the original captures: {}.",
                folders_line(&folders)
            ))
            .size(13.0)
            .color(t.ink2),
        )
        .wrap(),
    );
    let (how, button) = match total.disposal {
        Disposal::RecycleBin => {
            let mut how = format!("They go to the Recycle Bin on {}", {
                let bins: Vec<String> = total
                    .bins
                    .iter()
                    .map(|b| match b.capacity {
                        Some(c) => format!("{} (it holds {})", b.volume, bytes(c)),
                        None => b.volume.clone(),
                    })
                    .collect();
                bins.join(", ")
            });
            how.push_str(", where you can restore them.");
            if total
                .bins
                .iter()
                .any(|b| b.capacity.is_some_and(|c| b.used + total.bytes > c))
            {
                how.push_str(" Windows may empty older items from it to make room.");
            }
            (how, "Move them to the Recycle Bin")
        }
        Disposal::Permanent => (
            format!(
                "They are deleted permanently, not moved to the Recycle Bin: {}. They cannot be recovered.",
                total
                    .permanent_because
                    .clone()
                    .unwrap_or_else(|| "this volume has no Recycle Bin".into())
            ),
            "Delete them permanently",
        ),
    };
    ui.add(
        egui::Label::new(egui::RichText::new(how).size(13.0).color(
            if total.disposal == Disposal::Permanent {
                t.bad
            } else {
                t.ink2
            },
        ))
        .wrap(),
    );
    if dialog.renders && measure.render_total.files > 0 {
        ui.label(
            egui::RichText::new(format!(
                "Strehl's renders ({}) go too, {}.",
                bytes(measure.render_total.bytes),
                disposal_line(&measure.render_total)
            ))
            .size(12.0)
            .color(t.ink3),
        );
    }
    ui.add_space(10.0);
    ui.horizontal(|ui| {
        if ui.add(w::Button::quiet("Back")).clicked() {
            dialog.confirming_sources = false;
        }
        ui.with_layout(egui::Layout::right_to_left(egui::Align::Center), |ui| {
            *confirm |= ui.add(w::Button::danger(button)).clicked();
            *cancel |= ui.add(w::Button::quiet("Cancel")).clicked();
        });
    });
}

#[cfg(test)]
#[path = "app-library-manage-tests.rs"]
mod tests;
