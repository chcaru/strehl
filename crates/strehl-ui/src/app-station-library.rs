//! The Library station composed into the Studio 2 shell (plan 7.3; P4 stage 2).
//!
//! `LibraryStation` and `SubjectPage` draw themselves from their inputs and
//! return intents; this module gives them the catalog, a revision, the shared
//! preview service, the theme's palette, the capture on the rig and the
//! storage card, and carries out every intent. Long work (folder scans for
//! an import or a relocation, disk space) runs on workers and is polled from
//! `tick`, never from paint.
use super::studio_route::{Drawer, LibraryView as RouteLibraryView, Route, Station};
use super::*;
use crate::{
    depth_signature::DepthSignatures,
    library_paint::LibraryPalette,
    library_previews::TILE_SIDE,
    library_station::{LibraryInputs, LibraryIntent, LibraryStation, RigCapture, StorageCard},
    notices::{Severity, Source},
    project_explorer::ExplorerAction,
    studio_theme, studio_widgets as w,
    subject_page::{QueueView, SubjectInputs, SubjectPage},
    workspace_history::{ImportGroup, NodeId, NodeKind, StackDraft},
};

/// Disk space is read again after this long while the Library is open.
/// The preview request group of the rig strip's picture.
const RIG_PICTURE_GROUP: u64 = u64::MAX;
const STORAGE_INTERVAL: Duration = Duration::from_secs(60);

/// Where the next capture belongs, set by "New stack of this subject" and
/// "Shoot again". The Capture station reads it to name the stack and, for
/// Shoot again, to start from that stack's plan; the finished capture is
/// imported into `subject` (else `collection`) through `capture_parent`.
#[derive(Clone, Debug, Default, PartialEq)]
pub(super) struct CaptureTarget {
    pub subject: Option<NodeId>,
    pub collection: Option<NodeId>,
    /// "Shoot again": the stack whose bounds, step, exposure and light to reuse.
    pub from_stack: Option<NodeId>,
    /// The subject's name, for the Capture plan's subject field.
    pub subject_name: String,
}

enum FolderPick {
    /// Folders to import into a collection or a subject.
    Import {
        collection: Option<NodeId>,
        subject: Option<NodeId>,
    },
    /// The new folder of a stack whose sources moved.
    Locate(NodeId),
}

/// Folders waiting to become stacks, scanned one at a time.
#[derive(Default)]
struct ImportQueue {
    waiting: VecDeque<(NodeId, PathBuf)>,
    running: Option<(NodeId, PathBuf, Task<StackScan>)>,
    made: usize,
    refused: Vec<String>,
}

pub(super) struct RenameDraft {
    id: NodeId,
    name: String,
    focus: bool,
}

/// What the rig card shows changes with: the folder, the plane count, the
/// phase and the capture's subject.
type RigKey = (
    Option<PathBuf>,
    Option<u64>,
    Option<u64>,
    Option<String>,
    Option<NodeId>,
);

#[derive(Default)]
pub(super) struct LibraryState {
    pub(super) station: LibraryStation,
    pub(super) subject: SubjectPage,
    pick: Option<(FolderPick, mpsc::Receiver<Option<Vec<PathBuf>>>)>,
    imports: ImportQueue,
    locate: Option<(NodeId, Task<StackScan>)>,
    pub(super) rename: Option<RenameDraft>,
    pub(super) target: Option<CaptureTarget>,
    pub(super) rig: Option<RigCapture>,
    /// The capturing subject's pictures, looked up once per rig change: the
    /// strip shows the subject until a live frame is available.
    rig_pictures: Option<Vec<(PathBuf, bool)>>,
    rig_key: Option<RigKey>,
    storage: Option<StorageCard>,
    storage_task: Option<Task<Option<StorageCard>>>,
    pub(super) storage_read: Option<Instant>,
    /// Depth signatures for list rows and stack rows (`depth-signature.rs`).
    signatures: DepthSignatures,
    /// The queue's waiting stacks, refreshed each frame the Library paints.
    waiting: Vec<NodeId>,
    /// Delete, move, merge and Show in Explorer (`app-library-manage.rs`).
    pub(super) manage: super::library_manage::ManageState,
    /// The naming of a new subject, while open (`app-library-subject.rs`).
    pub(super) new_subject: Option<super::library_subject::NewSubjectDraft>,
}

impl StrehlApp {
    /// The catalog revision the Library's caches key on: every save, plus
    /// edits waiting for their debounced save.
    fn library_revision(&self) -> u64 {
        self.catalog
            .generation()
            .wrapping_mul(1_000_003)
            .wrapping_add(self.shell.catalog_revision())
    }

    /// The Library station never paints with the legacy constants.
    pub(super) fn library_paints_legacy(&self) -> bool {
        false
    }

    /// Where the next capture belongs (for the Capture station).
    #[allow(dead_code, reason = "the Capture station's composition reads it")]
    pub(super) fn capture_target(&self) -> Option<&CaptureTarget> {
        self.library.target.as_ref()
    }

    /// Images and sources the Library is still loading (offscreen readiness).
    pub(super) fn library_loading(&self) -> bool {
        self.project_explorer.preview_pending()
            || self.library.imports.running.is_some()
            || !self.library.imports.waiting.is_empty()
            || self.library.station.sources_pending()
            || self.library.storage_task.is_some()
            || self.library.signatures.pending()
            || self.library_manage_pending()
    }

    /// The canvas of the Library station: the subject grid, or a subject page.
    pub(super) fn library_canvas(&mut self, ui: &mut egui::Ui) {
        let palette = LibraryPalette::from_tokens(&studio_theme::tokens(ui.ctx()));
        let revision = self.library_revision();
        let subject = match self.shell.navigator.route() {
            Route::Subject(id) => Some(*id).filter(|id| {
                self.catalog
                    .node(*id)
                    .is_some_and(|node| node.kind == NodeKind::Subject)
            }),
            _ => None,
        };
        self.library_dialog_keys(ui.ctx());
        self.library_new_subject_keys(ui.ctx());
        let running = self
            .job
            .as_ref()
            .and(self.pending_stack.or(self.active_stack));
        let busy = self.job.is_some();
        let deleting = self.library_deleting();
        let state = &mut self.library;
        state.waiting.clear();
        state.waiting.extend(self.activity_hub.queue.stacks());
        state.signatures.refresh(&self.catalog, revision);
        let previews = self.project_explorer.previews_mut();
        if subject.is_some() {
            state
                .station
                .check_sources(&self.catalog, revision, ui.ctx());
        }
        if let Some(rig) = state.rig.as_mut().filter(|rig| rig.picture.is_none()) {
            if state.rig_pictures.is_none()
                && let (Some(id), Some(model)) = (rig.subject, state.station.model())
            {
                state.rig_pictures = Some(
                    model
                        .cards
                        .iter()
                        .find(|card| card.id == id)
                        .map(|card| card.pictures.clone())
                        .unwrap_or_default(),
                );
            }
            if let Some(pictures) = state.rig_pictures.as_ref().filter(|p| !p.is_empty()) {
                rig.picture = previews.first_tile(pictures, TILE_SIDE, RIG_PICTURE_GROUP);
            }
        }
        let intent = match subject {
            Some(subject) => state.subject.show(
                ui,
                SubjectInputs {
                    catalog: &self.catalog,
                    revision,
                    subject,
                    previews,
                    palette: &palette,
                    rig: state.rig.as_ref(),
                    sources: state.station.sources(),
                    signatures: Some(state.signatures.stacks()),
                    queue: QueueView {
                        running,
                        waiting: &state.waiting,
                        busy,
                    },
                },
            ),
            None => state.station.show(
                ui,
                LibraryInputs {
                    catalog: &self.catalog,
                    revision,
                    previews,
                    palette: &palette,
                    rig: state.rig.as_ref(),
                    storage: state.storage.as_ref(),
                    signatures: Some(state.signatures.subjects()),
                    stacking: busy,
                    deleting,
                },
            ),
        };
        // Signatures for the rows just painted (computed on a worker).
        match subject {
            Some(_) => {
                if let Some(model) = state.subject.model() {
                    state
                        .signatures
                        .want_stacks(model.stacks.iter().map(|stack| stack.id));
                }
            }
            None => state
                .signatures
                .want_subjects(state.station.painted_rows().iter().copied()),
        }
        // The dialogs are modal: what the Library asks meanwhile waits.
        let modal = self.library.manage.dialog.is_some() || self.library.new_subject.is_some();
        if let Some(intent) = intent.filter(|_| !modal) {
            self.library_intent(ui.ctx(), intent);
        }
        self.library_apply_overlay(ui.ctx());
        self.library_rename_window(ui.ctx());
        self.library_delete_window(ui.ctx());
        self.library_new_subject_window(ui.ctx());
    }

    /// Carry out what the Library or a subject page asked for.
    pub(super) fn library_intent(&mut self, ctx: &egui::Context, intent: LibraryIntent) {
        let idle = self.job.is_none() && !self.picker_active();
        match intent {
            LibraryIntent::OpenSubject(id) => self.navigate(Route::Subject(id)),
            LibraryIntent::Back => self.navigate(Route::Library(RouteLibraryView::All)),
            LibraryIntent::QueueStack(id) => {
                let (queued, refused) = self.library_queue(&[id]);
                if queued == 0 {
                    for line in refused {
                        self.library_notice(Severity::Warning, format!("Not stacked: {line}"));
                    }
                }
            }
            LibraryIntent::QueueSubject(subject) => {
                let stacks = self.library_unstacked(subject);
                let (queued, refused) = self.library_queue(&stacks);
                if queued > 0 {
                    self.library_notice(
                        Severity::Info,
                        format!(
                            "{} the stack queue",
                            crate::library_paint::plural(queued, "stack joins", "stacks join")
                        ),
                    );
                }
                for line in refused {
                    self.library_notice(Severity::Warning, format!("Not stacked: {line}"));
                }
            }
            LibraryIntent::OpenStack(id) => {
                if idle {
                    self.open_project_stack(id);
                    self.navigate(Route::for_station(Station::Stack, Some(id), None));
                } else {
                    self.library_busy_notice();
                }
            }
            LibraryIntent::OpenRender { stack, run } => {
                let found = self
                    .catalog
                    .runs
                    .iter()
                    .find(|r| r.directory == run)
                    .cloned();
                match found {
                    Some(run) if idle => {
                        self.reopen_run(run);
                        self.navigate(Route::Develop {
                            stack: Some(stack),
                            render: None,
                        });
                    }
                    Some(_) => self.library_busy_notice(),
                    None => self.library_notice(
                        Severity::Warning,
                        "That render is no longer in the catalog".into(),
                    ),
                }
            }
            LibraryIntent::OpenVersion(id) => {
                self.handle_photo_history_action(ExplorerAction::RestoreVersion { id });
                self.go_station(Station::Develop);
            }
            LibraryIntent::OpenCapture => self.go_station(Station::Capture),
            LibraryIntent::NewStackFromCamera {
                collection,
                subject,
            } => self.library_capture_target(collection, subject, None),
            LibraryIntent::ShootAgain(stack) => {
                let subject = self.catalog.subject_of(stack);
                self.library_capture_target(None, subject, Some(stack));
            }
            LibraryIntent::PickFolders {
                collection,
                subject,
            } => self.library_pick(FolderPick::Import {
                collection,
                subject,
            }),
            LibraryIntent::ImportFolders {
                collection,
                subject,
                groups,
            } => self.library_import(collection, subject, groups),
            LibraryIntent::Locate(stack) => self.library_pick(FolderPick::Locate(stack)),
            LibraryIntent::RevealPath(path) => {
                if let Err(error) = crate::reveal_path::reveal(&path) {
                    self.library_notice(Severity::Warning, format!("{error:#}"));
                }
            }
            LibraryIntent::Rename(id) => self.library_rename(id),
            LibraryIntent::EditSubject { id, name, edit } => {
                let result = self
                    .project_explorer
                    .organize(&mut self.catalog, |catalog| {
                        if catalog.node(id).is_some_and(|node| node.name != name) {
                            catalog.rename(id, &name)?;
                        }
                        catalog.set_subject_meta(id, edit)
                    });
                match result {
                    Ok(()) => self.persist_catalog(),
                    Err(error) => self.library_notice(Severity::Warning, format!("{error:#}")),
                }
            }
            LibraryIntent::NewCollection => {
                let name = self.library_unique_name("New collection");
                let made = self
                    .project_explorer
                    .organize(&mut self.catalog, |catalog| catalog.create_project(&name));
                match made {
                    Ok(id) => {
                        self.persist_catalog();
                        self.library.rename = Some(RenameDraft {
                            id,
                            name,
                            focus: true,
                        });
                    }
                    Err(error) => self.library_notice(Severity::Warning, format!("{error:#}")),
                }
            }
            LibraryIntent::NewSubject { collection } => {
                self.library_new_subject(collection, Vec::new());
            }
            LibraryIntent::MoveStacksToNewSubject(stacks) => {
                if !stacks.is_empty() {
                    self.library_new_subject(None, stacks);
                }
            }
            intent @ (LibraryIntent::Delete(_)
            | LibraryIntent::MoveStacks { .. }
            | LibraryIntent::MoveSubjects { .. }
            | LibraryIntent::MoveSubjectsToNewCollection(_)
            | LibraryIntent::MergeSubjects { .. }
            | LibraryIntent::ShowSources(_)
            | LibraryIntent::ShowRenders(_)) => self.library_manage(ctx, intent),
            LibraryIntent::ReviewStorage => {
                // Compaction lives with the completed captures in Capture.
                self.go_station(Station::Capture);
                self.library_notice(
                    Severity::Info,
                    "Compaction is under Completed captures in Capture".into(),
                );
            }
        }
        ctx.request_repaint();
    }

    /// Open the rename window for a collection, subject or stack.
    pub(super) fn library_rename(&mut self, id: NodeId) {
        if let Some(node) = self.catalog.node(id) {
            self.library.rename = Some(RenameDraft {
                id,
                name: node.name.clone(),
                focus: true,
            });
        }
    }

    pub(super) fn library_notice(&mut self, severity: Severity, text: String) {
        self.shell
            .notices
            .push(severity, Source::Library, text, None);
    }
    fn library_busy_notice(&mut self) {
        self.library_notice(
            Severity::Info,
            "Finish the stack or the open chooser first".into(),
        );
    }

    pub(super) fn library_unique_name(&self, base: &str) -> String {
        let taken = |name: &str| self.catalog.nodes.iter().any(|node| node.name == name);
        if !taken(base) {
            return base.into();
        }
        (2..)
            .map(|n| format!("{base} {n}"))
            .find(|name| !taken(name))
            .unwrap_or_else(|| base.into())
    }

    /// Open Capture for a new stack of a subject (or into a collection).
    fn library_capture_target(
        &mut self,
        collection: Option<NodeId>,
        subject: Option<NodeId>,
        from_stack: Option<NodeId>,
    ) {
        let subject_name = subject
            .and_then(|id| self.catalog.node(id))
            .map(|node| node.name.clone())
            .unwrap_or_default();
        self.capture_parent = subject.or(collection);
        // A new stack starts from a clean plan, not the last capture's
        // review and stages (owner feedback, 2026-11-23). "Shoot again"
        // keeps the step calibration: the same subject, framed the same.
        self.capture.new_capture(from_stack.is_some());
        match subject {
            Some(id) => self.capture.set_plan_subject(id, &subject_name),
            // A new subject: the plan asks for its name.
            None => self.capture.clear_plan_subject(),
        }
        self.library.target = Some(CaptureTarget {
            subject,
            collection,
            from_stack,
            subject_name,
        });
        self.go_station(Station::Capture);
    }

    fn library_pick(&mut self, purpose: FolderPick) {
        if self.library.pick.is_some() || self.picker_active() {
            return;
        }
        let (sender, receiver) = mpsc::sync_channel(1);
        let multiple = matches!(purpose, FolderPick::Import { .. });
        self.library.pick = Some((purpose, receiver));
        std::thread::spawn(move || {
            let dialog = rfd::FileDialog::new();
            let folders = if multiple {
                dialog
                    .set_title("Folders to add: one stack per folder")
                    .pick_folders()
            } else {
                dialog
                    .set_title("Where are this stack's photographs now?")
                    .pick_folder()
                    .map(|folder| vec![folder])
            };
            let _ = sender.send(folders);
        });
    }

    /// One stack per folder: into `subject` when given, else a new subject per
    /// group in `collection` (or the first collection, or a new one).
    fn library_import(
        &mut self,
        collection: Option<NodeId>,
        subject: Option<NodeId>,
        groups: Vec<ImportGroup>,
    ) {
        if groups.is_empty() {
            return;
        }
        let collection = match collection.or_else(|| {
            self.catalog
                .nodes
                .iter()
                .find(|node| node.parent.is_none() && node.kind == NodeKind::Project)
                .map(|node| node.id)
        }) {
            Some(id) => id,
            None => match self.catalog.create_project("Library") {
                Ok(id) => id,
                Err(error) => {
                    self.library_notice(Severity::Warning, format!("{error:#}"));
                    return;
                }
            },
        };
        let mut queued = 0;
        for group in groups {
            let target = match subject {
                Some(id) => id,
                None => match self.catalog.create_subject(collection, &group.subject) {
                    Ok(id) => id,
                    Err(error) => {
                        self.library
                            .imports
                            .refused
                            .push(format!("{}: {error:#}", group.subject));
                        continue;
                    }
                },
            };
            for folder in group.folders {
                self.library.imports.waiting.push_back((target, folder));
                queued += 1;
            }
        }
        self.persist_catalog();
        self.library_notice(
            Severity::Info,
            format!(
                "Reading {queued} {} for new stacks",
                if queued == 1 { "folder" } else { "folders" }
            ),
        );
    }

    /// The Library's background work: folder pickers, the import queue,
    /// relocation scans, disk space and the capture on the rig. Runs from
    /// `tick`; cheap when there is nothing to do.
    pub(super) fn library_tick(&mut self, ctx: &egui::Context) {
        if let Some((_, receiver)) = &self.library.pick
            && let Ok(result) = receiver.try_recv()
        {
            let (purpose, _) = self.library.pick.take().unwrap();
            match (purpose, result) {
                (_, None) => {}
                (
                    FolderPick::Import {
                        collection,
                        subject,
                    },
                    Some(folders),
                ) => {
                    let groups = crate::workspace_history::import_plan(&folders);
                    self.library_import(collection, subject, groups);
                }
                (FolderPick::Locate(stack), Some(folders)) => {
                    if let Some(folder) = folders.into_iter().next() {
                        self.library.locate = Some((stack, jobs::scan_stack(folder)));
                    }
                }
            }
        }
        if let Some((_, task)) = &self.library.locate
            && let Ok(result) = task.receiver.try_recv()
        {
            let (stack, _) = self.library.locate.take().unwrap();
            let outcome = result
                .map_err(anyhow::Error::msg)
                .and_then(|scan| self.catalog.relocate_stack_to_scan(stack, &scan));
            match outcome {
                Ok(_) => {
                    self.persist_catalog();
                    self.library_notice(Severity::Done, "Found the stack's photographs".into());
                }
                Err(error) => self.library_notice(Severity::Warning, format!("{error:#}")),
            }
        }
        self.library_poll_imports(ctx);
        self.library_poll_manage(ctx);
        self.library_poll_storage(ctx);
        self.library_poll_signatures(ctx);
        self.library_rig();
        if self.library.pick.is_some()
            || self.library.locate.is_some()
            || self.library.imports.running.is_some()
            || self.library.storage_task.is_some()
        {
            ctx.request_repaint_after(Duration::from_millis(100));
        }
    }

    fn library_poll_imports(&mut self, ctx: &egui::Context) {
        let queue = &mut self.library.imports;
        if let Some((_, _, task)) = &queue.running
            && let Ok(result) = task.receiver.try_recv()
        {
            let (subject, folder, _) = queue.running.take().unwrap();
            match result {
                Ok(scan) if !scan.frames.is_empty() => {
                    let defaults = crate::controls::Controls::default();
                    let draft = StackDraft::from_scan(
                        &scan,
                        defaults.settings,
                        defaults.exposure,
                        defaults.gate,
                        defaults.workers,
                    );
                    let name = crate::workspace_history::default_stack_name(&folder);
                    match self.catalog.create_stack(subject, &name, draft) {
                        Ok(_) => queue.made += 1,
                        Err(error) => queue.refused.push(format!("{name}: {error:#}")),
                    }
                }
                Ok(_) => queue.refused.push(format!(
                    "{}: no RAW photographs",
                    crate::display_path::display_path(&folder)
                )),
                Err(error) => queue.refused.push(format!(
                    "{}: {error}",
                    crate::display_path::display_path(&folder)
                )),
            }
            if queue.waiting.is_empty() {
                let (made, refused) = (queue.made, std::mem::take(&mut queue.refused));
                queue.made = 0;
                self.persist_catalog();
                if made > 0 {
                    self.library_notice(
                        Severity::Done,
                        format!(
                            "Added {made} {}",
                            if made == 1 { "stack" } else { "stacks" }
                        ),
                    );
                }
                for line in refused {
                    self.library_notice(Severity::Warning, format!("Not added: {line}"));
                }
            } else {
                self.catalog_edit_pending = Some(Instant::now());
            }
            ctx.request_repaint();
        }
        let queue = &mut self.library.imports;
        if queue.running.is_none()
            && let Some((subject, folder)) = queue.waiting.pop_front()
        {
            let task = jobs::scan_stack(folder.clone());
            queue.running = Some((subject, folder, task));
        }
    }

    /// Depth signatures: open the cache beside the catalog once (offscreen
    /// pictures keep theirs in memory), then one replay at a time, never
    /// while a stack renders or Quiet holds.
    fn library_poll_signatures(&mut self, ctx: &egui::Context) {
        if !self.library.signatures.opened() {
            let path = self
                .catalog
                .path
                .as_deref()
                .filter(|_| self.screenshot.is_none())
                .and_then(DepthSignatures::path_beside);
            self.library.signatures.open(path);
        }
        let allowed = self.job.is_none() && self.activity_hub.quiet.reason().is_none();
        let unix = crate::workspace_history::timestamp();
        if self.library.signatures.poll(allowed, unix) {
            ctx.request_repaint();
        }
        if allowed && self.library.signatures.pending() {
            ctx.request_repaint_after(Duration::from_millis(100));
        }
    }

    /// Stack `stacks` through the queue; returns (queued, why not).
    fn library_queue(&mut self, stacks: &[NodeId]) -> (usize, Vec<String>) {
        let mut queued = 0;
        let mut refused = Vec::new();
        for &id in stacks {
            match self.queue_stack(id) {
                Ok(_) => queued += 1,
                Err(error) => {
                    let name = self
                        .catalog
                        .node(id)
                        .map_or_else(String::new, |node| node.name.clone());
                    refused.push(format!("{name}: {error:#}"));
                }
            }
        }
        (queued, refused)
    }

    /// A subject's stacks with no saved render that are not already
    /// rendering or waiting.
    fn library_unstacked(&self, subject: NodeId) -> Vec<NodeId> {
        let running = self
            .job
            .as_ref()
            .and(self.pending_stack.or(self.active_stack));
        let waiting: Vec<NodeId> = self.activity_hub.queue.stacks().collect();
        self.catalog
            .nodes
            .iter()
            .filter(|node| node.kind == NodeKind::Stack && node.parent == Some(subject))
            .filter(|node| {
                !node.revisions.iter().any(|directory| {
                    self.catalog
                        .runs
                        .iter()
                        .any(|run| &run.directory == directory && run.status == "Saved")
                })
            })
            .map(|node| node.id)
            .filter(|id| Some(*id) != running && !waiting.contains(id))
            .collect()
    }

    fn library_poll_storage(&mut self, ctx: &egui::Context) {
        if let Some(task) = &self.library.storage_task
            && let Ok(result) = task.receiver.try_recv()
        {
            self.library.storage_task = None;
            if let Ok(card) = result {
                self.library.storage = card;
            }
            ctx.request_repaint();
        }
        let open = self.shell.navigator.station() == Station::Library;
        let due = self
            .library
            .storage_read
            .is_none_or(|read| read.elapsed() >= STORAGE_INTERVAL);
        if open && due && self.library.storage_task.is_none() {
            self.library.storage_read = Some(Instant::now());
            let folder = self
                .shell
                .rig
                .receiver_folder
                .as_ref()
                .map(PathBuf::from)
                .unwrap_or_else(|| self.output.clone());
            self.library.storage_task =
                Some(jobs::spawn_task("strehl-library-storage", move |_| {
                    Ok(storage_card(&folder))
                }));
        }
    }

    /// The capture on the rig, rebuilt only when the rig's count changes.
    fn library_rig(&mut self) {
        let rig = &self.shell.rig;
        if !rig.capturing() {
            self.library.rig = None;
            self.library.rig_key = None;
            return;
        }
        let target = self.library.target.as_ref().and_then(|t| t.subject);
        let key = (
            rig.in_progress.clone(),
            rig.completed,
            rig.planned,
            rig.phase.clone(),
            target,
        );
        if self.library.rig_key.as_ref() == Some(&key) {
            return;
        }
        // The folder being written belongs to a stack only once it is
        // imported; until then the capture's target names the subject.
        let stack = rig.in_progress.as_ref().and_then(|folder| {
            self.catalog.nodes.iter().find(|node| {
                node.kind == NodeKind::Stack
                    && node
                        .stack
                        .as_ref()
                        .is_some_and(|draft| draft.source == *folder)
            })
        });
        let subject = target.or_else(|| stack.and_then(|s| self.catalog.subject_of(s.id)));
        // "Blue weevil · Dorsal · 2.8×" once the folder is a stack.
        let title = subject
            .and_then(|id| self.catalog.node(id))
            .map(|node| match stack {
                Some(stack) => format!("{} · {}", node.name, stack.name),
                None => node.name.clone(),
            })
            .or_else(|| {
                rig.in_progress
                    .as_ref()
                    .map(|folder| crate::workspace_history::default_stack_name(folder))
            })
            .unwrap_or_else(|| "Capture".into());
        let paused = rig.phase.as_deref() == Some("paused");
        let detail = match (rig.completed, rig.planned) {
            (Some(done), Some(total)) => format!(
                "{} plane {} of {total}",
                if paused { "Paused at" } else { "Capturing" },
                (done + 1).min(total)
            ),
            _ => "Capturing".into(),
        };
        let progress = match (rig.completed, rig.planned) {
            (Some(done), Some(total)) if total > 0 => done as f32 / total as f32,
            _ => 0.0,
        };
        self.library.rig = Some(RigCapture {
            subject,
            stack: stack.map(|s| s.id),
            title,
            detail,
            progress,
            picture: None,
        });
        self.library.rig_key = Some(key);
        self.library.rig_pictures = None;
    }

    fn library_rename_window(&mut self, ctx: &egui::Context) {
        let Some(draft) = &mut self.library.rename else {
            return;
        };
        let mut open = true;
        let mut commit = false;
        let mut cancel = false;
        egui::Window::new("Rename")
            .id(egui::Id::new("library-rename"))
            .open(&mut open)
            .collapsible(false)
            .resizable(false)
            .anchor(egui::Align2::CENTER_TOP, egui::vec2(0.0, 160.0))
            .show(ctx, |ui| {
                ui.set_width(320.0);
                let edit = ui.add(
                    egui::TextEdit::singleline(&mut draft.name)
                        .desired_width(f32::INFINITY)
                        .font(egui::TextStyle::Body),
                );
                if std::mem::take(&mut draft.focus) {
                    edit.request_focus();
                }
                commit |= edit.lost_focus() && ui.input(|i| i.key_pressed(egui::Key::Enter));
                cancel |= ui.input(|i| i.key_pressed(egui::Key::Escape));
                ui.add_space(8.0);
                ui.horizontal(|ui| {
                    commit |= ui.add(w::Button::primary("Rename")).clicked();
                    cancel |= ui.add(w::Button::quiet("Cancel")).clicked();
                });
            });
        if commit {
            let RenameDraft { id, name, .. } = self.library.rename.take().unwrap();
            let result = self
                .project_explorer
                .organize(&mut self.catalog, |catalog| catalog.rename(id, &name));
            match result {
                Ok(()) => self.persist_catalog(),
                Err(error) => self.library_notice(Severity::Warning, format!("{error:#}")),
            }
        } else if cancel || !open {
            self.library.rename = None;
        }
    }

    /// `--route subject:<name or id>`, or the open stack's subject.
    pub(super) fn library_launch_subject(&mut self, wanted: Option<&str>) {
        let by_name = |wanted: &str| {
            let wanted = wanted.trim();
            self.catalog
                .nodes
                .iter()
                .filter(|node| node.kind == NodeKind::Subject)
                .find(|node| {
                    wanted.parse::<NodeId>().is_ok_and(|id| id == node.id)
                        || node.name.eq_ignore_ascii_case(wanted)
                })
                .map(|node| node.id)
        };
        // Without a name: the open stack's subject, else the most developed.
        let subject = match wanted {
            Some(wanted) => by_name(wanted),
            None => self
                .active_stack
                .and_then(|id| self.catalog.subject_of(id))
                .or_else(|| {
                    self.catalog
                        .nodes
                        .iter()
                        .filter(|node| node.kind == NodeKind::Subject)
                        .max_by_key(|node| {
                            self.catalog
                                .subject_summary(node.id)
                                .map_or(0, |summary| summary.renders)
                        })
                        .map(|node| node.id)
                }),
        };
        match subject {
            Some(id) => self.navigate(Route::Subject(id)),
            None => {
                self.navigate(Route::Library(RouteLibraryView::All));
                if let Some(wanted) = wanted {
                    self.library_notice(Severity::Warning, format!("No subject named {wanted}"));
                }
            }
        }
    }

    /// Open the project tree (today's Projects pane) over the station.
    pub(super) fn open_project_tree(&mut self) {
        if self.shell.navigator.drawer != Some(Drawer::Projects) {
            self.open_drawer(Drawer::Projects);
        }
    }
}

/// The volume holding `folder`: its free and total space.
fn storage_card(folder: &Path) -> Option<StorageCard> {
    let existing = folder.ancestors().find(|path| path.is_dir())?;
    let volume = match existing.components().next()? {
        std::path::Component::Prefix(prefix) => {
            crate::display_path::display_path(Path::new(prefix.as_os_str()))
        }
        _ => "/".into(),
    };
    let (free, total) = disk_space(existing)?;
    Some(StorageCard {
        volume: volume.trim_end_matches('\\').to_owned(),
        free,
        total,
        compactable: None,
    })
}

#[cfg(windows)]
fn disk_space(path: &Path) -> Option<(u64, u64)> {
    use std::os::windows::ffi::OsStrExt;
    use windows_sys::Win32::Storage::FileSystem::GetDiskFreeSpaceExW;
    let wide: Vec<u16> = path.as_os_str().encode_wide().chain(Some(0)).collect();
    let (mut available, mut total, mut free) = (0_u64, 0_u64, 0_u64);
    // SAFETY: a NUL-terminated wide path and three writable u64 out-parameters.
    let ok = unsafe { GetDiskFreeSpaceExW(wide.as_ptr(), &mut available, &mut total, &mut free) };
    (ok != 0).then_some((available, total))
}
#[cfg(not(windows))]
fn disk_space(_path: &Path) -> Option<(u64, u64)> {
    None
}

#[cfg(test)]
#[path = "app-station-library-tests.rs"]
mod tests;
