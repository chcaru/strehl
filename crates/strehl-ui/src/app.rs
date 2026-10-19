use crate::{
    LaunchOptions,
    bracket_browser::BracketBrowser,
    controls::Controls,
    draft_preview::{self, DraftEvent, DraftJob, DraftStage},
    jobs::{self, RenderEvent, RenderOutcome, RenderRequest, StackScan, Task},
    pipeline::{DiagnosticKind, DiagnosticScope, DiagnosticSurface, PipelineProgress, Stage},
    preview::{self, PreviewImage},
    process_atlas::ProcessAtlas,
    process_space::{self, ProcessSpace},
    processing_view,
    source_browser::SourceBrowser,
    stack_map,
    theme::{self, ACCENT, AMBER, BG, GREEN, INK, LINE, MUTED, PANEL},
    viewer::Viewer,
    workbench::{SourcePhoto, Workbench, WorkbenchMode},
};
#[path = "app-history.rs"]
mod history;
#[cfg(test)]
#[path = "app-tests.rs"]
mod tests;
#[cfg(test)]
#[path = "app-v19-review-tests.rs"]
mod v19_review_tests;
#[cfg(test)]
#[path = "app-v20-independent-tests.rs"]
mod v20_independent_tests;
#[cfg(test)]
#[path = "app-v20-review-tests.rs"]
mod v20_review_tests;
#[cfg(test)]
#[path = "app-v25-start-tests.rs"]
mod v25_start_tests;
#[path = "app-workspace.rs"]
mod workspace;
#[cfg(test)]
#[path = "app-workspace-review-tests.rs"]
mod workspace_review_tests;

#[cfg(test)]
#[path = "app-provenance-tests.rs"]
mod provenance_tests;
use eframe::egui::{self, Color32, RichText, Stroke, TextureHandle};
use std::{
    collections::{BTreeSet, VecDeque},
    path::{Path, PathBuf},
    sync::mpsc,
    time::{Duration, Instant},
};

#[derive(Clone, Copy, PartialEq, Eq)]
enum View {
    Sources,
    Draft,
    Result,
}
#[derive(Clone, Copy)]
enum Dialog {
    Source,
    Output,
}
#[derive(Clone)]
struct CachedImage {
    texture: TextureHandle,
    source_size: [u32; 2],
    overview: bool,
}
struct ResultWork {
    epoch: u64,
    task: Task<PreviewImage>,
}
struct ProcessSurface {
    epoch: u64,
    sequence: u64,
    kind: DiagnosticKind,
    level: usize,
    stage: Stage,
    frame: Option<usize>,
    texture: TextureHandle,
    meta: process_space::SurfaceMeta,
    packet: DiagnosticSurface,
}

pub struct StrehlApp {
    stack: Option<StackScan>,
    scan: Option<Task<StackScan>>,
    epoch: u64,
    selected: usize,
    view: View,
    browser: SourceBrowser,
    draft_job: Option<DraftJob>,
    draft_viewer: Viewer,
    draft_info: Option<String>,
    draft_progress: Option<(DraftStage, usize, usize)>,
    draft_requested: bool,
    draft_epoch: u64,
    draft_cancelled: bool,
    result_work: Option<ResultWork>,
    pending_result: Option<PathBuf>,
    visible_sources: Vec<usize>,
    reveal_selected: bool,
    follow_processing: bool,
    followed_frame: Option<(Stage, Option<crate::pipeline::AlignmentPhase>, usize)>,
    source_viewer: Viewer,
    live_input: Option<(usize, TextureHandle)>,
    workbench: Workbench,
    process_space: ProcessSpace,
    process_atlas: ProcessAtlas,
    spatial_view: bool,
    process_view: bool,
    sidebar: Option<workspace::Sidebar>,
    project_explorer: crate::project_explorer::ProjectExplorer,
    active_stack: Option<crate::workspace_history::NodeId>,
    pending_stack: Option<crate::workspace_history::NodeId>,
    capture_parent: Option<crate::workspace_history::NodeId>,
    catalog: crate::workspace_history::Catalog,
    catalog_edit_pending: Option<Instant>,
    edits: history::WorkspaceEdits,
    replay: Option<Task<(crate::workspace_history::Run, PipelineProgress)>>,
    expected_run: Option<crate::workspace_history::Run>,
    pending_run: Option<crate::workspace_history::Run>,
    process_surfaces: Vec<ProcessSurface>,
    process_domain_epoch: u64,
    canvas_mode: Option<WorkbenchMode>,
    held_pair: Option<[usize; 2]>,
    last_stage: Stage,
    last_live_mode: Option<WorkbenchMode>,
    result_viewer: Viewer,
    result: Option<PathBuf>,
    image_path: Option<PathBuf>,
    job: Option<jobs::RenderJob>,
    dialog: Option<mpsc::Receiver<(Dialog, Option<PathBuf>)>>,
    bracket_browser: BracketBrowser,
    engine: Option<PathBuf>,
    output: PathBuf,
    controls: Controls,
    progress: PipelineProgress,
    logs: VecDeque<String>,
    activity: bool,
    dock_live: bool,
    raw_log: bool,
    recorded: bool,
    error: Option<String>,
    status: String,
    started: Option<Instant>,
    last_event: Option<Instant>,
    screenshot: Option<PathBuf>,
    screenshot_hover: Option<[f32; 2]>,
    screenshot_ranges: Option<Vec<[usize; 2]>>,
    screenshot_ranges_applied_frame: Option<u64>,
    screenshot_requested: bool,
    reveal_at_ms: Option<f64>,
    reveal_started: Option<f64>,
    reveal_requested_elapsed: Option<f64>,
    updates: usize,
    max_texture_side: u32,
}

impl StrehlApp {
    pub fn new(cc: &eframe::CreationContext<'_>, launch: LaunchOptions) -> Self {
        theme::install(&cc.egui_ctx);
        let max_texture_side = cc
            .wgpu_render_state
            .as_ref()
            .map_or(8192, |r| r.device.limits().max_texture_dimension_2d);
        Self::from_launch(max_texture_side, launch)
    }
    fn from_launch(max_texture_side: u32, launch: LaunchOptions) -> Self {
        let catalog =
            crate::workspace_history::Catalog::load(crate::workspace_history::default_path());
        let mut app = Self {
            stack: None,
            scan: None,
            epoch: 0,
            selected: 0,
            view: View::Sources,
            browser: SourceBrowser::default(),
            draft_job: None,
            draft_viewer: Viewer::default(),
            draft_info: None,
            draft_progress: None,
            draft_requested: launch.draft,
            draft_epoch: 0,
            draft_cancelled: false,
            result_work: None,
            pending_result: None,
            visible_sources: Vec::new(),
            reveal_selected: false,
            follow_processing: true,
            followed_frame: None,
            source_viewer: Viewer::default(),
            live_input: None,
            workbench: Workbench::default(),
            process_space: ProcessSpace::default(),
            process_atlas: ProcessAtlas::default(),
            spatial_view: launch.space,
            process_view: true,
            sidebar: Some(workspace::Sidebar::Projects),
            project_explorer: Default::default(),
            active_stack: None,
            pending_stack: None,
            capture_parent: None,
            catalog,
            catalog_edit_pending: None,
            edits: Default::default(),
            replay: None,
            expected_run: None,
            pending_run: None,
            process_surfaces: Vec::new(),
            process_domain_epoch: 0,
            canvas_mode: None,
            held_pair: None,
            last_stage: Stage::Preparing,
            last_live_mode: None,
            result_viewer: Viewer::default(),
            result: None,
            image_path: None,
            job: None,
            dialog: None,
            bracket_browser: BracketBrowser::default(),
            engine: launch.engine.or_else(find_engine),
            output: default_output(),
            controls: Controls::default(),
            progress: PipelineProgress::default(),
            logs: VecDeque::new(),
            activity: false,
            dock_live: true,
            raw_log: false,
            recorded: false,
            error: None,
            status: "No bracket loaded".into(),
            started: None,
            last_event: None,
            screenshot: launch.screenshot,
            screenshot_hover: launch.screenshot_hover,
            screenshot_ranges: launch.screenshot_ranges,
            screenshot_ranges_applied_frame: None,
            screenshot_requested: false,
            reveal_at_ms: launch.reveal_at_ms,
            reveal_started: None,
            reveal_requested_elapsed: None,
            updates: 0,
            max_texture_side,
        };
        if let Some(source) = launch.source {
            app.import(source);
        }
        let explicit_image =
            launch.preview.is_some() || launch.workbench.is_some() || launch.probe_at.is_some();
        if let Some(image) = launch.preview {
            app.open_result(image);
        }
        if let Some(log) = launch.activity_log {
            match std::fs::read_to_string(log) {
                Ok(text) if text.len() <= 16 * 1024 * 1024 => {
                    app.progress.ingest(&text);
                    app.progress.finish();
                    app.log(&text);
                    app.activity = true;
                    app.recorded = true;
                    app.dock_live = true;
                }
                Ok(_) => {
                    app.error = Some("The recorded log exceeds the 16 MiB display limit.".into())
                }
                Err(e) => app.error = Some(format!("Opening recorded activity: {e}")),
            }
        }
        app.sync_workbench_phase();
        if let Some(mode) = launch.workbench {
            app.set_canvas_mode(Some(mode));
        }
        if let Some([x, y]) = launch.probe_at {
            app.set_canvas_mode(Some(WorkbenchMode::Probe));
            app.workbench.set_pin(egui::pos2(x, y));
        }
        app.process_view = launch.process || !explicit_image;
        app.process_space.set_layout(app.catalog.layout);
        if let Some(directory) = launch.browse {
            app.bracket_browser.open(Some(directory));
        }
        if let Some(directory) = launch.open_run {
            let canonical = std::fs::canonicalize(&directory).ok();
            if let Some(run) = app
                .catalog
                .runs
                .iter()
                .find(|run| {
                    run.directory == directory
                        || canonical.as_ref().is_some_and(|path| {
                            std::fs::canonicalize(&run.directory).ok().as_ref() == Some(path)
                        })
                })
                .cloned()
            {
                app.reopen_run(run);
            } else {
                app.error = Some(
                    "This render is not in the project library. Open its stack from Projects."
                        .into(),
                );
            }
        }
        if app.screenshot_ranges.is_some() {
            app.process_view = true;
            app.spatial_view = false;
        }
        app
    }

    fn import(&mut self, path: PathBuf) {
        self.edits.change_stack();
        self.active_stack = None;
        self.epoch += 1;
        self.follow_processing = true;
        self.followed_frame = None;
        self.scan = Some(jobs::scan_stack(path));
        self.stack = None;
        self.selected = 0;
        self.view = View::Sources;
        self.browser.reset(self.epoch);
        if let Some(job) = &self.draft_job {
            job.cancel();
            self.draft_cancelled = true;
        }
        self.draft_viewer = Viewer::default();
        self.draft_info = None;
        self.draft_progress = None;
        self.visible_sources.clear();
        self.source_viewer = Viewer::default();
        self.live_input = None;
        self.workbench = Workbench::default();
        self.process_space = ProcessSpace::default();
        self.process_atlas = ProcessAtlas::default();
        self.process_space.set_layout(self.catalog.layout);
        self.process_view = true;
        self.spatial_view = false;
        self.sidebar = Some(workspace::Sidebar::Projects);
        self.replay = None;
        self.expected_run = None;
        self.pending_run = None;
        self.process_surfaces.clear();
        self.held_pair = None;
        self.canvas_mode = None;
        self.last_stage = Stage::Preparing;
        self.last_live_mode = None;
        self.progress = PipelineProgress::default();
        self.logs.clear();
        self.activity = false;
        self.recorded = false;
        self.started = None;
        self.last_event = None;
        self.result_viewer = Viewer::default();
        self.result = None;
        self.image_path = None;
        self.pending_result = None;
        self.error = None;
        self.status = "Reading bracket…".into();
        // In-flight JPEG/ TIFF decodes finish serially; their old epoch is discarded.
    }
    fn open_result(&mut self, path: PathBuf) {
        self.process_view = false;
        self.pending_result = Some(path);
        self.error = None;
        self.view = View::Result;
    }
    fn select(&mut self, index: usize) {
        let Some(stack) = &self.stack else { return };
        self.selected = index.min(stack.frames.len().saturating_sub(1));
        self.view = View::Sources;
        self.reveal_selected = true;
        self.browser.select(self.selected, &mut self.source_viewer);
    }
    fn inspect_frame(&mut self, index: usize) {
        if self.process_view {
            self.process_space.inspect_frame(index);
        }
        self.held_pair = None;
        if self.canvas_mode == Some(WorkbenchMode::Compare) {
            self.canvas_mode = None;
        }
        self.select(index);
    }
    fn pick(&mut self, kind: Dialog) {
        if self.picker_active() {
            return;
        }
        if matches!(kind, Dialog::Source) {
            self.bracket_browser
                .open(self.stack.as_ref().map(|stack| stack.directory.clone()));
            return;
        }
        let (sender, receiver) = mpsc::sync_channel(1);
        self.dialog = Some(receiver);
        std::thread::spawn(move || {
            let dialog = rfd::FileDialog::new();
            let path = match kind {
                Dialog::Source => unreachable!("brackets use the visual browser"),
                Dialog::Output => dialog.set_title("Save stacks in").pick_folder(),
            };
            let _ = sender.send((kind, path));
        });
    }
    fn picker_active(&self) -> bool {
        self.dialog.is_some() || self.bracket_browser.active()
    }
    fn start_render(&mut self) {
        if self.stack_start_blocker().is_some() {
            return;
        }
        self.ensure_project_stack();
        self.pending_stack = self.active_stack;
        let (Some(stack), Some(engine)) = (&self.stack, &self.engine) else {
            return;
        };
        self.pending_run = Some(crate::workspace_history::Run {
            directory: PathBuf::new(),
            source: stack.directory.clone(),
            output: PathBuf::new(),
            log: PathBuf::new(),
            label: stack
                .directory
                .file_name()
                .unwrap_or_default()
                .to_string_lossy()
                .into_owned(),
            created: crate::workspace_history::timestamp(),
            status: "Stacking".into(),
            frames: self
                .controls
                .settings
                .frame_limit
                .unwrap_or(stack.frames.len())
                .min(stack.frames.len()),
            sources: crate::workspace_history::source_identities(stack),
            settings: self.controls.settings.clone(),
            exposure: self.controls.exposure,
            gate: self.controls.gate,
            workers: self.controls.workers,
            pinned: false,
        });
        self.replay = None;
        self.expected_run = None;
        self.job = Some(jobs::start_render(RenderRequest {
            executable: engine.clone(),
            source: stack.directory.clone(),
            output_parent: self.output.clone(),
            exposure_ev: self.controls.exposure,
            pyramid_gate: self.controls.gate,
            worker_threads: Some(self.controls.workers),
            settings: self.controls.settings.clone(),
        }));
        self.progress = PipelineProgress::default();
        self.process_space = ProcessSpace::default();
        self.process_atlas = ProcessAtlas::default();
        self.process_space.set_layout(self.catalog.layout);
        self.process_view = true;
        self.spatial_view = false;
        self.result_viewer = Viewer::default();
        self.result_work = None;
        self.process_surfaces.clear();
        self.result = None;
        self.image_path = None;
        self.pending_result = None;
        self.logs.clear();
        self.recorded = false;
        self.live_input = None;
        self.error = None;
        self.started = Some(Instant::now());
        self.last_event = Some(Instant::now());
        self.status = "Starting stack…".into();
        self.activity = true;
        self.dock_live = true;
        self.raw_log = false;
        self.follow_processing = true;
        self.held_pair = None;
        self.last_stage = Stage::Preparing;
        self.last_live_mode = None;
        self.resume_pair();
    }
    fn log(&mut self, text: &str) {
        for line in text.lines() {
            if self.logs.len() == 400 {
                self.logs.pop_front();
            }
            // The saved job log retains the transport payload. The visible
            // activity list presents metadata instead of thousands of hex bytes.
            let line = if line.starts_with("STREHL_UI_PROGRESS ") {
                line.split_once(" data=")
                    .map_or(line, |(metadata, _)| metadata)
            } else {
                line
            };
            self.logs.push_back(line.chars().take(2000).collect());
        }
    }
    fn poll(&mut self, ctx: &egui::Context) {
        if let Some(result) = self
            .replay
            .as_ref()
            .and_then(|task| task.receiver.try_recv().ok())
        {
            self.replay = None;
            match result {
                Ok((run, progress)) => {
                    self.expected_run = Some(run.clone());
                    if self
                        .stack
                        .as_ref()
                        .is_some_and(|stack| !run.matches_scan(stack))
                    {
                        self.stack = None;
                        self.browser.reset(self.epoch);
                        self.source_viewer = Viewer::default();
                        self.error = Some("Source bracket changed. Saved photograph and observations remain available; source previews are withheld.".into());
                    }
                    self.progress = progress;
                    self.activity = true;
                    self.recorded = true;
                    self.status = format!("Reopened {}", run.label);
                    if run.status == "Saved" && run.output.is_file() {
                        self.result = Some(run.output.clone());
                        self.open_result(run.output);
                        self.process_view = true;
                    }
                }
                Err(error) => self.error = Some(format!("Opening saved run: {error}")),
            }
        }
        if let Some((kind, path)) = self.dialog.as_ref().and_then(|r| r.try_recv().ok()) {
            self.dialog = None;
            if let Some(path) = path {
                match kind {
                    Dialog::Source => self.import(path),
                    Dialog::Output => self.output = path,
                }
            }
        }
        if let Some(result) = self.scan.as_ref().and_then(|t| t.receiver.try_recv().ok()) {
            self.scan = None;
            match result {
                Ok(stack) => {
                    if self
                        .expected_run
                        .as_ref()
                        .is_some_and(|run| !run.matches_scan(&stack))
                    {
                        self.status = "Saved stack / source bracket changed".into();
                        self.error = Some("Source bracket differs from this saved run. Its photograph and observations remain available.".into());
                    } else {
                        self.status = format!("{} source frames", stack.frames.len());
                        self.selected = stack.frames.len() / 2;
                        self.stack = Some(stack);
                        if self.expected_run.is_none() {
                            self.ensure_project_stack();
                        }
                        self.reveal_selected = true;
                    }
                }
                Err(error) => {
                    self.status = if self.expected_run.is_some() {
                        "Saved stack / sources unavailable"
                    } else {
                        "Could not open bracket"
                    }
                    .into();
                    self.error = Some(error);
                }
            }
        }
        self.follow_current_frame();
        self.sync_workbench_phase();
        let events: Vec<_> = self
            .job
            .as_ref()
            .map(|j| j.receiver.try_iter().take(64).collect())
            .unwrap_or_default();
        let log_backlog = events.len() == 64;
        for event in events {
            self.last_event = Some(Instant::now());
            match event {
                RenderEvent::Started {
                    directory,
                    output,
                    log,
                } => {
                    self.status = "Stacking".into();
                    if let Some(mut run) = self.pending_run.take() {
                        run.directory = directory.clone();
                        run.output = output.clone();
                        run.log = log.clone();
                        if let Some(id) = self.pending_stack {
                            if let Err(error) = self.catalog.add_revision(id, run.clone()) {
                                self.error = Some(error.to_string());
                                self.catalog.add(run);
                            }
                        } else {
                            self.catalog.add(run);
                        }
                        self.persist_catalog();
                    }
                    self.log(&format!(
                        "Job: {}\nOutput: {}\nLog: {}",
                        directory.display(),
                        output.display(),
                        log.display()
                    ));
                }
                RenderEvent::Log(text) => {
                    self.progress.ingest(&text);
                    self.log(&text);
                    self.follow_current_frame();
                }
                RenderEvent::Finished(outcome) => {
                    self.pending_run = None;
                    self.pending_stack = None;
                    self.job = None;
                    match outcome {
                        RenderOutcome::Completed {
                            directory,
                            output,
                            log,
                        } => {
                            self.catalog.finish(&directory, "Saved");
                            self.persist_catalog();
                            self.progress.mark_complete();
                            self.status = "Stack saved".into();
                            self.log(&format!(
                                "Saved {}\nJob: {}\nLog: {}",
                                output.display(),
                                directory.display(),
                                log.display()
                            ));
                            self.result = Some(output.clone());
                            self.open_result(output);
                            self.process_view = true;
                        }
                        RenderOutcome::Cancelled { directory } => {
                            self.catalog.finish(&directory, "Cancelled");
                            self.persist_catalog();
                            self.progress.mark_cancelled();
                            self.status = "Cancelled".into();
                            self.log(&format!(
                                "Cancelled. Activity retained in {}",
                                directory.display()
                            ));
                        }
                        RenderOutcome::Failed { directory, message } => {
                            if let Some(path) = &directory {
                                self.catalog.finish(path, "Failed");
                                self.persist_catalog();
                            }
                            if let Some(path) = directory {
                                self.log(&format!("Job: {}", path.display()));
                            }
                            self.progress.mark_failed();
                            self.status = "Stack stopped".into();
                            self.error = Some(message);
                        }
                    }
                }
            }
        }
        self.sync_workbench_phase();
        // Completion can queue the TIFF while removing the last active job.
        // Start its decode in this same tick, before the event loop decides
        // whether to sleep; the image must never need a pointer event to load.
        self.poll_images(ctx);
        self.cache_process_surfaces(ctx);
        if log_backlog {
            // Drain a bounded batch each paint. The log is lossless on disk;
            // never add the idle delay while another batch may be waiting.
            ctx.request_repaint();
        }
        if self.job.is_some()
            || self.scan.is_some()
            || self.replay.is_some()
            || self.browser.active()
            || self.draft_job.is_some()
            || self.result_work.is_some()
            || self.pending_result.is_some()
            || self.dialog.is_some()
        {
            ctx.request_repaint_after(Duration::from_millis(70));
        }
    }
    fn poll_images(&mut self, ctx: &egui::Context) {
        self.browser.set_live_frame(if self.activity {
            self.progress.processing_frame
        } else {
            None
        });
        let pair = if self.process_view {
            self.process_pair()
        } else {
            self.current_pair()
        };
        self.browser
            .set_probe_frames(if self.activity || self.canvas_mode.is_some() {
                pair.map(Some)
            } else {
                [None, None]
            });
        let mut warm_sources = if self.process_view {
            self.process_contacts()
        } else {
            self.visible_sources.clone()
        };
        if self.activity || self.process_view {
            for index in self.live_pair() {
                if !warm_sources.contains(&index) {
                    warm_sources.push(index);
                }
            }
            let count = self.stack.as_ref().map_or(0, |stack| stack.frames.len());
            if count > 1 && !self.process_view {
                for step in 0..8 {
                    let index = step * (count - 1) / 7;
                    if !warm_sources.contains(&index) {
                        warm_sources.push(index);
                    }
                }
            }
        }
        let frames = self.stack.as_ref().map_or(&[][..], |s| s.frames.as_slice());
        let preview_target = self.preview_target();
        self.browser.poll(
            ctx,
            self.epoch,
            preview_target,
            frames,
            &warm_sources,
            self.max_texture_side,
            &mut self.source_viewer,
        );
        if self.activity
            && let Some(index) = self.progress.processing_frame
            && index < frames.len()
            && let Some(texture) = self.browser.native_thumbnail(index)
        {
            self.live_input = Some((index, texture.clone()));
        }
        let mut events = Vec::new();
        if let Some(job) = &self.draft_job {
            for _ in 0..64 {
                match job.receiver.try_recv() {
                    Ok(event) => events.push(event),
                    Err(mpsc::TryRecvError::Empty) => break,
                    Err(mpsc::TryRecvError::Disconnected) => {
                        if !events
                            .iter()
                            .any(|event| matches!(event, DraftEvent::Finished(_)))
                        {
                            events.push(DraftEvent::Finished(Err(
                                "The draft worker ended before returning an image.".into(),
                            )));
                        }
                        break;
                    }
                }
            }
        }
        for event in events {
            match event {
                DraftEvent::Progress {
                    stage,
                    completed,
                    total,
                } => {
                    if self.draft_epoch == self.epoch && !self.draft_cancelled {
                        self.draft_progress = Some((stage, completed, total));
                    }
                }
                DraftEvent::Finished(result) => {
                    self.draft_job = None;
                    self.draft_progress = None;
                    if self.draft_epoch != self.epoch || self.draft_cancelled {
                        continue;
                    }
                    match result {
                        Ok(draft) => {
                            self.draft_info = Some(format!(
                                "{} / {} frames aligned · {} skipped · reference {} · {} direct pairs · {} cycles{}",
                                draft.aligned_frames,
                                draft.source_frames,
                                draft.skipped_frames,
                                draft.reference_frame + 1,
                                draft.alignment_edges,
                                draft.cycle_rank,
                                if draft.warnings.is_empty() {
                                    String::new()
                                } else {
                                    format!(" · {}", draft.warnings.join(" · "))
                                }
                            ));
                            install_viewer(&mut self.draft_viewer, &cache_image(ctx, draft.image));
                            self.draft_viewer.reset(true);
                        }
                        Err(error) => self.error = Some(format!("Camera JPEG draft: {error}")),
                    }
                }
            }
        }
        if self.draft_requested
            && self.stack.is_some()
            && self.scan.is_none()
            && self.draft_job.is_none()
        {
            self.draft_requested = false;
            self.start_draft();
        }
        if let Some(result) = self
            .result_work
            .as_ref()
            .and_then(|w| w.task.receiver.try_recv().ok())
        {
            let work = self.result_work.take().unwrap();
            if work.epoch == self.epoch {
                match result {
                    Ok(image) => {
                        self.image_path = Some(image.path.clone());
                        install_viewer(&mut self.result_viewer, &cache_image(ctx, image));
                        self.result_viewer.reset(true);
                    }
                    Err(error) => self.error = Some(error),
                }
            }
        }
        if self.result_work.is_none()
            && let Some(path) = self.pending_result.take()
        {
            self.result_work = Some(ResultWork {
                epoch: self.epoch,
                task: preview::load_preview(path, self.max_texture_side),
            });
        }
    }

    fn start_draft(&mut self) {
        if self.draft_job.is_some()
            || self.picker_active()
            || self.job.is_some()
            || self.scan.is_some()
        {
            return;
        }
        self.draft_epoch = self.epoch;
        self.draft_cancelled = false;
        let Some(stack) = &self.stack else { return };
        self.draft_job = Some(draft_preview::start_draft_preview(
            stack.frames.iter().map(|f| f.path.clone()).collect(),
        ));
        self.draft_progress = Some((DraftStage::Reading, 0, stack.frames.len()));
        self.view = View::Draft;
        self.process_view = false;
        self.error = None;
    }

    fn inspector(&mut self, ctx: &egui::Context) {
        egui::SidePanel::right("session-dock")
            .default_width(300.0)
            .width_range(250.0..=430.0)
            .resizable(true)
            .frame(egui::Frame::new().fill(PANEL).inner_margin(16))
            .show(ctx, |ui| {
                ui.allocate_ui_with_layout(
                    egui::vec2(ui.available_width(), 34.0),
                    egui::Layout::left_to_right(egui::Align::Center),
                    |ui| {
                        if theme::tab(ui, "Live", self.dock_live).clicked() {
                            self.dock_live = true;
                            self.raw_log = false;
                            if self.activity {
                                self.resume_pair();
                            }
                        }
                        if theme::tab(ui, "Adjust", !self.dock_live).clicked() {
                            self.dock_live = false;
                        }
                        ui.with_layout(egui::Layout::right_to_left(egui::Align::Center), |ui| {
                            if ui
                                .add(
                                    egui::Button::new(RichText::new("Log").size(10.0).color(MUTED))
                                        .frame(false),
                                )
                                .on_hover_text("Read the engine's full observations")
                                .clicked()
                            {
                                self.raw_log = !self.raw_log;
                                self.dock_live = true;
                            }
                        });
                    },
                );
                ui.add_space(8.0);
                ui.with_layout(egui::Layout::bottom_up(egui::Align::Min), |ui| {
                    ui.add_space(2.0);
                    self.render_actions(ui);
                    ui.add_space(10.0);
                    ui.separator();
                    ui.add_space(8.0);
                    egui::ScrollArea::vertical()
                        .id_salt(if self.dock_live {
                            "live-story"
                        } else {
                            "render-adjustments"
                        })
                        .auto_shrink([false, false])
                        .show(ui, |ui| {
                            ui.with_layout(egui::Layout::top_down(egui::Align::Min), |ui| {
                                if self.dock_live {
                                    if self.recorded {
                                        ui.label(
                                            RichText::new("RECORDED SESSION")
                                                .monospace()
                                                .size(9.0)
                                                .color(MUTED),
                                        );
                                        ui.add_space(8.0);
                                    }
                                    if self.raw_log {
                                        ui.label(RichText::new("Behind the photograph").size(19.0));
                                        ui.add_space(10.0);
                                        for line in &self.logs {
                                            ui.add(
                                                egui::Label::new(
                                                    RichText::new(line)
                                                        .monospace()
                                                        .size(10.0)
                                                        .color(MUTED),
                                                )
                                                .wrap(),
                                            );
                                        }
                                    } else if self.activity {
                                        let pair = self.live_pair();
                                        let previews = pair.map(|index| {
                                            self.browser
                                                .thumbnail(index)
                                                .map(|texture| (index, texture))
                                        });
                                        let response = processing_view::show_dock(
                                            ui,
                                            &self.progress,
                                            previews,
                                        );
                                        if let Some(index) = response.selected {
                                            self.inspect_frame(index);
                                        }
                                        if let Some(pair) = response.compare_pair {
                                            self.hold_pair(pair);
                                        }

                                        if self.job.is_some()
                                            && let Some(started) = self.started
                                        {
                                            ui.add_space(12.0);
                                            theme::caption(
                                                ui,
                                                &format!(
                                                    "Session time {}",
                                                    elapsed(started.elapsed())
                                                ),
                                            );
                                        }
                                    } else {
                                        self.ready_story(ui);
                                    }
                                } else {
                                    self.controls.show(ui, self.job.is_none());
                                    ui.add_space(16.0);
                                    egui::CollapsingHeader::new("Destination")
                                        .id_salt("destination-engine")
                                        .show(ui, |ui| self.destination_controls(ui));
                                }
                                if self.result.is_some() && self.job.is_none() {
                                    ui.add_space(16.0);
                                    ui.label(RichText::new("TIFF saved").color(GREEN));
                                    if ui
                                        .add(egui::Button::new("Copy output path").frame(false))
                                        .clicked()
                                        && let Some(path) = &self.result
                                    {
                                        ui.ctx().copy_text(path.display().to_string());
                                    }
                                }
                            });
                        });
                });
            });
    }
    fn render_actions(&mut self, ui: &mut egui::Ui) {
        let width = ui.available_width();
        if self.job.is_some() {
            if ui
                .add_sized(
                    [width, 38.0],
                    egui::Button::new("Stop stacking")
                        .fill(BG)
                        .stroke(Stroke::new(1.0_f32, LINE)),
                )
                .clicked()
            {
                if let Some(job) = &self.job {
                    job.cancel();
                }
                self.status = "Stopping stack...".into();
            }
        } else {
            let blocker = self.stack_start_blocker();
            let enabled = blocker.is_none();
            let spec = format!(
                "{} · {}",
                self.controls.quality_summary(),
                self.controls.machine_summary()
            );
            if theme::stack_action(
                ui,
                egui::vec2(width, if self.activity { 38.0 } else { 65.0 }),
                enabled,
                (!self.activity).then_some(spec.as_str()),
            )
            .on_hover_text(blocker.unwrap_or("Stack these photos into a new result · Ctrl+Enter"))
            .clicked()
            {
                self.start_render();
            }
            if let Some(reason) = blocker {
                theme::caption(ui, reason);
            }
        }
    }
    fn destination_controls(&mut self, ui: &mut egui::Ui) {
        ui.label(
            RichText::new(short_path(&self.output))
                .size(11.0)
                .color(MUTED),
        )
        .on_hover_text(self.output.display().to_string());
        if ui
            .add_enabled(
                self.job.is_none() && !self.picker_active(),
                egui::Button::new("Choose destination").frame(false),
            )
            .clicked()
        {
            self.pick(Dialog::Output);
        }
    }
    fn ready_story(&mut self, ui: &mut egui::Ui) {
        ui.label(
            RichText::new("FOCUS BRACKET")
                .monospace()
                .size(9.0)
                .color(ACCENT),
        );
        ui.add_space(14.0);
        ui.label(
            RichText::new(
                self.stack
                    .as_ref()
                    .map_or("--".into(), |s| format!("{:03}", s.frames.len())),
            )
            .monospace()
            .size(42.0),
        );
        ui.add_space(20.0);
        let count = self.stack.as_ref().map_or(0, |s| s.frames.len());
        let images = [
            self.selected.saturating_sub(1),
            self.selected,
            self.selected.saturating_add(1),
        ]
        .map(|i| i.min(count.saturating_sub(1)));
        let mut select = None;
        ui.horizontal(|ui| {
            let width = (ui.available_width() - 16.0) / 3.0;
            for index in images {
                let (rect, response) =
                    ui.allocate_exact_size(egui::vec2(width, width * 0.8), egui::Sense::click());
                let image_rect =
                    egui::Rect::from_min_size(rect.min, egui::vec2(width, width * 0.67));
                if let Some(texture) = self.browser.thumbnail(index) {
                    ui.painter().image(
                        texture.id(),
                        image_rect,
                        egui::Rect::from_min_max(egui::Pos2::ZERO, egui::pos2(1.0, 1.0)),
                        Color32::WHITE,
                    );
                } else {
                    ui.painter().rect_filled(image_rect, 0.0, BG);
                }
                ui.painter().text(
                    rect.left_bottom(),
                    egui::Align2::LEFT_BOTTOM,
                    format!("{:03}", index + 1),
                    egui::FontId::monospace(9.0),
                    MUTED,
                );
                if response.clicked() {
                    select = Some(index);
                }
            }
        });
        if let Some(index) = select {
            self.inspect_frame(index);
        }
        ui.add_space(24.0);
        ui.horizontal(|ui| {
            let width = (ui.available_width() - 8.0) / 2.0;
            if ui
                .add_sized(
                    [width, 38.0],
                    egui::Button::new("Inspect detail")
                        .stroke(Stroke::new(1.0_f32, LINE))
                        .fill(BG),
                )
                .clicked()
            {
                self.set_canvas_mode(Some(WorkbenchMode::Probe));
            }
            if ui
                .add_sized(
                    [width, 38.0],
                    egui::Button::new("Compare frames")
                        .stroke(Stroke::new(1.0_f32, LINE))
                        .fill(BG),
                )
                .clicked()
            {
                self.set_canvas_mode(Some(WorkbenchMode::Compare));
            }
        });
    }
    fn current_pair(&self) -> [usize; 2] {
        if let Some(pair) = self.held_pair {
            return pair;
        }
        self.live_pair()
    }
    fn process_pair(&self) -> [usize; 2] {
        let count = self.stack.as_ref().map_or(0, |s| s.frames.len());
        let mut pair = self
            .held_pair
            .or(self.progress.alignment_current_pair)
            .or(self.progress.alignment_latest_pair)
            .filter(|pair| pair[0] < pair[1] && pair[1] < count)
            .unwrap_or_else(|| self.live_pair());
        if let Some(index) = self.process_inspection().filter(|&i| i < count) {
            pair[0] = index;
        }
        pair
    }
    fn live_pair(&self) -> [usize; 2] {
        let count = self.stack.as_ref().map_or(0, |stack| stack.frames.len());
        if self.progress.stage == Stage::Alignment
            && let Some(pair) = self
                .progress
                .alignment_current_pair
                .or(self.progress.alignment_latest_pair)
            && pair[0] < count
            && pair[1] < count
        {
            return pair;
        }
        let selected = self.selected.min(count.saturating_sub(1));
        if selected > 0 {
            [selected - 1, selected]
        } else {
            [0, 1.min(count.saturating_sub(1))]
        }
    }
    fn source_photo(&self, index: usize) -> Option<SourcePhoto> {
        self.browser
            .texture_snapshot(index)
            .map(|(epoch, texture, aperture)| SourcePhoto {
                epoch,
                index,
                texture,
                aperture,
            })
    }
    fn set_canvas_mode(&mut self, mode: Option<WorkbenchMode>) {
        self.view = View::Sources;
        self.canvas_mode = mode;
        if mode == Some(WorkbenchMode::Probe) && self.workbench.pin().is_none() {
            self.workbench.set_pin(egui::pos2(0.5, 0.5));
        }
    }
    fn hold_pair(&mut self, pair: [usize; 2]) {
        if self
            .stack
            .as_ref()
            .is_some_and(|stack| pair.iter().all(|i| *i < stack.frames.len()))
        {
            self.held_pair = Some(pair);
            self.set_canvas_mode(Some(WorkbenchMode::Compare));
        }
    }
    fn resume_pair(&mut self) {
        self.held_pair = None;
        self.follow_processing = true;
        self.followed_frame = None;
        self.follow_current_frame();
        self.set_canvas_mode(self.live_mode());
        self.source_viewer.reset(true);
        self.dock_live = true;
        self.raw_log = false;
        self.process_view = self.activity;
    }
    fn live_mode(&self) -> Option<WorkbenchMode> {
        if self.progress.stage == Stage::Alignment
            && (self.progress.alignment_current_pair.is_some()
                || self.progress.alignment_latest_pair.is_some())
        {
            Some(WorkbenchMode::Compare)
        } else {
            None
        }
    }
    fn live_active(&self) -> bool {
        self.activity
            && self.view == View::Sources
            && self.follow_processing
            && self.held_pair.is_none()
            && self.canvas_mode == self.live_mode()
            && self
                .progress
                .processing_frame
                .is_none_or(|index| index == self.selected)
    }
    fn sync_workbench_phase(&mut self) {
        let mode = self.live_mode();
        let stage_changed = self.last_stage != self.progress.stage;
        if stage_changed || self.last_live_mode != mode {
            if self.follow_processing
                && self.held_pair.is_none()
                && self.view == View::Sources
                && (stage_changed || self.canvas_mode == self.last_live_mode)
                && matches!(
                    self.progress.stage,
                    Stage::Alignment | Stage::Merge | Stage::Rendering
                )
            {
                self.set_canvas_mode(mode);
            }
            self.last_stage = self.progress.stage;
            self.last_live_mode = mode;
        }
    }
    fn follow_current_frame(&mut self) {
        if self.follow_processing
            && let Some(index) = self.progress.processing_frame
            && Some((self.progress.stage, self.progress.alignment_phase, index))
                != self.followed_frame
        {
            self.followed_frame = Some((self.progress.stage, self.progress.alignment_phase, index));
            let view = self.view;
            let reveal = self.reveal_selected;
            self.select(index);
            if self.progress.stage == Stage::Alignment {
                self.reveal_selected = reveal;
            }
            self.view = view;
        }
    }
    fn filmstrip(&mut self, ctx: &egui::Context) {
        let Some(stack) = &self.stack else { return };
        let count = stack.frames.len();
        let mut select = None;
        egui::TopBottomPanel::bottom("filmstrip-v2")
            .exact_height(112.0)
            .frame(
                egui::Frame::new()
                    .fill(PANEL)
                    .inner_margin(egui::Margin::symmetric(14, 6)),
            )
            .show(ctx, |ui| {
                ui.horizontal(|ui| {
                    ui.label(RichText::new("Focus sweep").size(11.5).color(INK));
                    ui.add_space(9.0);
                    theme::caption(ui, &format!("{} / {}", self.selected + 1, count));
                    if ui
                        .small_button("‹")
                        .on_hover_text("Previous frame · Left arrow")
                        .clicked()
                    {
                        select = Some(self.selected.saturating_sub(1));
                    }
                    if ui
                        .small_button("›")
                        .on_hover_text("Next frame · Right arrow")
                        .clicked()
                    {
                        select = Some((self.selected + 1).min(count - 1));
                    }
                    let mut selected = self.selected;
                    if ui
                        .add(
                            egui::Slider::new(&mut selected, 0..=count - 1)
                                .show_value(false)
                                .clamping(egui::SliderClamping::Always),
                        )
                        .changed()
                    {
                        select = Some(selected);
                    }
                    ui.with_layout(egui::Layout::right_to_left(egui::Align::Center), |ui| {
                        if self.job.is_some(){if ui.add(egui::Button::new(RichText::new(if self.follow_processing { "Following live" } else { "Resume follow" }).color(if self.follow_processing { ACCENT } else { MUTED })).frame(false)).on_hover_text("Follow stays on when you browse. Click to pause or resume it explicitly.").clicked() { self.follow_processing = !self.follow_processing; }}
                        else{theme::caption(ui, "Camera JPEGs · browsing only");}
                    });
                });
                const TILE: f32 = 84.0;
                let mut strip = egui::ScrollArea::horizontal()
                    .id_salt(("filmstrip", self.epoch))
                    .auto_shrink([false, false]);
                if self.reveal_selected {
                    let max_scroll=(count as f32*TILE-ui.available_width()).max(0.0);
                    strip = strip.horizontal_scroll_offset(
                        (((self.selected as f32 * TILE - ui.available_width() * 0.45).max(0.0) / TILE).floor() * TILE).min(max_scroll),
                    );
                    self.reveal_selected = false;
                }
                strip.show_viewport(ui, |ui, viewport| {
                    let first = ((viewport.min.x / TILE).floor().max(0.0) as usize).min(count.saturating_sub(1));
                    let end = (first+(ui.clip_rect().width()/TILE).ceil() as usize+2).min(count);
                    self.visible_sources = (first.min(count)..end).collect();
                    ui.set_min_width(count as f32 * TILE);
                    ui.horizontal(|ui| {
                        ui.spacing_mut().item_spacing.x = 6.0;
                        ui.add_space(first as f32 * TILE);
                        for index in first.min(count)..end {
                            let frame = &stack.frames[index];
                            ui.allocate_ui_with_layout(egui::vec2(78.0,54.0),egui::Layout::top_down(egui::Align::Min), |ui| {
                                ui.set_max_width(78.0);
                                let (rect, response) = ui.allocate_exact_size(
                                    egui::vec2(78.0, 38.0),
                                    egui::Sense::click(),
                                );
                                ui.painter().rect_filled(rect, 0.0, BG);
                                if let Some(texture) = self.browser.native_thumbnail(index)
                                {
                                    let reveal=ui.ctx().animate_bool_with_time(egui::Id::new(("filmstrip-reveal",self.epoch,index)),true,0.14);
                                    let size = texture.size_vec2();
                                    let cover = (rect.width() / size.x).max(rect.height() / size.y);
                                    ui.painter().image(
                                        texture.id(),
                                        rect,
                                        egui::Rect::from_center_size(egui::pos2(0.5,0.5),rect.size()/(size*cover)),
                                        Color32::from_white_alpha((255.0*reveal).round() as u8),
                                    );
                                } else {
                                    ui.ctx().animate_bool_with_time(egui::Id::new(("filmstrip-reveal",self.epoch,index)),false,0.14);
                                    ui.painter().line_segment([rect.center()-egui::vec2(8.0,0.0),rect.center()+egui::vec2(8.0,0.0)],Stroke::new(1.0_f32,LINE));
                                }
                                if index == self.selected {
                                    ui.painter().rect_stroke(
                                        rect.expand(2.0),
                                        5.0,
                                        Stroke::new(1.5_f32, ACCENT),
                                        egui::StrokeKind::Inside,
                                    );
                                }
                                if response.clicked() {
                                    select = Some(index);
                                }
                                response.on_hover_text(format!(
                                    "{} · {}",
                                    frame.path.file_name().unwrap_or_default().to_string_lossy(),
                                    bytes(frame.bytes)
                                ));
                                ui.add(
                                    egui::Label::new(
                                        RichText::new(format!("{:03}",index+1))
                                        .size(10.0)
                                        .color(if index == self.selected { INK } else { MUTED }),
                                    )
                                    .truncate(),
                                );
                            });
                        }
                    });
                });
            });
        if let Some(index) = select {
            self.inspect_frame(index);
        }
    }
    fn stack_ribbon(&mut self, ctx: &egui::Context) {
        let Some(count) = self
            .stack
            .as_ref()
            .filter(|_| self.activity)
            .map(|stack| stack.frames.len())
        else {
            return;
        };
        let response = egui::TopBottomPanel::bottom("stack-spine")
            .exact_height(stack_map::HEIGHT + 8.0)
            .frame(
                egui::Frame::new()
                    .fill(BG)
                    .inner_margin(egui::Margin::symmetric(14, 4)),
            )
            .show(ctx, |ui| {
                let indices = self.browser.thumbnail_indices();
                let previews: Vec<_> = indices
                    .into_iter()
                    .filter_map(|index| {
                        self.browser
                            .thumbnail(index)
                            .map(|texture| (index, texture))
                    })
                    .collect();
                stack_map::show(
                    ui,
                    &self.progress,
                    count,
                    self.selected,
                    if self.view == View::Sources && self.canvas_mode.is_none() {
                        self.browser.displayed_index()
                    } else {
                        None
                    },
                    &previews,
                    self.visible_sources
                        .first()
                        .zip(self.visible_sources.last())
                        .map(|(first, last)| [*first, *last]),
                )
            })
            .inner;
        if let Some(index) = response.selected {
            self.inspect_frame(index);
        }
        if let Some(pair) = response.compare_pair {
            self.hold_pair(pair);
        }
    }
    fn live_portal(&mut self, ui: &mut egui::Ui, photo: egui::Rect) {
        if !self.activity
            || self.progress.stage > Stage::Rendering
            || (self.view == View::Sources
                && self.held_pair.is_none()
                && self.follow_processing
                && self
                    .progress
                    .processing_frame
                    .is_none_or(|index| index == self.selected))
        {
            return;
        }
        let Some((index, texture)) = self.live_input.as_ref() else {
            return;
        };
        let width = (photo.width() * 0.28).clamp(110.0, 156.0);
        let rect = egui::Rect::from_min_size(
            egui::pos2(photo.right() - width - 12.0, photo.top() + 12.0),
            egui::vec2(width, width * 0.667 + 29.0),
        );
        let painter = ui.painter().with_clip_rect(photo.intersect(ui.clip_rect()));
        painter.rect_filled(rect.expand(3.0), 0.0, PANEL);
        painter.rect_stroke(
            rect.expand(3.0),
            3.0,
            Stroke::new(1.0_f32, ACCENT.gamma_multiply(0.65)),
            egui::StrokeKind::Inside,
        );
        let image = egui::Rect::from_min_max(rect.min + egui::vec2(0.0, 22.0), rect.max);
        let aperture = texture.size_vec2();
        let uv = egui::Rect::from_min_max(egui::Pos2::ZERO, egui::pos2(1.0, 1.0));
        let scale = (image.width() / aperture.x).min(image.height() / aperture.y);
        painter.image(
            texture.id(),
            egui::Rect::from_center_size(image.center(), aperture * scale),
            uv,
            Color32::WHITE,
        );
        painter.text(
            rect.left_top() + egui::vec2(5.0, 10.0),
            egui::Align2::LEFT_CENTER,
            format!(
                "{} / {:03}",
                if self.recorded {
                    "RECORDED INPUT"
                } else if self.progress.processing_frame == Some(*index) {
                    "LIVE INPUT"
                } else {
                    "LAST INPUT"
                },
                index + 1
            ),
            egui::FontId::monospace(9.0),
            ACCENT,
        );
        if let Some(next) = self
            .progress
            .processing_frame
            .filter(|next| *next != *index)
        {
            painter.text(
                rect.right_bottom() - egui::vec2(5.0, 5.0),
                egui::Align2::RIGHT_BOTTOM,
                format!("→ {:03}", next + 1),
                egui::FontId::monospace(9.0),
                ACCENT,
            );
        }
        let response = ui.interact(
            rect,
            ui.id().with("live-input-portal"),
            egui::Sense::click(),
        );
        if response
            .on_hover_cursor(egui::CursorIcon::PointingHand)
            .on_hover_text("Return to the processing frame")
            .clicked()
        {
            self.resume_pair();
        }
    }
    fn canvas(&mut self, ctx: &egui::Context) {
        egui::CentralPanel::default()
            .frame(egui::Frame::new().fill(BG))
            .show(ctx, |ui| {
                // These three rectangles never depend on labels, loading state or errors.
                let canvas = ui.available_rect_before_wrap();
                ui.allocate_rect(canvas, egui::Sense::hover());
                let toolbar = egui::Rect::from_min_max(
                    canvas.min,
                    egui::pos2(canvas.right(), canvas.top() + 34.0),
                );
                let footer = egui::Rect::from_min_max(
                    egui::pos2(canvas.left(), canvas.bottom() - 22.0),
                    canvas.max,
                );
                let photo = egui::Rect::from_min_max(
                    egui::pos2(canvas.left(), toolbar.bottom()),
                    egui::pos2(canvas.right(), footer.top()),
                );
                let mut tools = ui.new_child(
                    egui::UiBuilder::new()
                        .id_salt("canvas-tools")
                        .max_rect(toolbar.shrink2(egui::vec2(10.0, 0.0))),
                );
                tools.horizontal_centered(|ui| {
                    if self.activity && theme::tab(ui, "Live view", self.live_active()).clicked() {
                        self.resume_pair();
                    }
                    if theme::tab(
                        ui,
                        "Sources",
                        self.view == View::Sources && !self.live_active(),
                    )
                    .clicked()
                    {
                        self.view = View::Sources;
                        self.held_pair = None;
                        self.canvas_mode = None;
                    }
                    if ui
                        .add_enabled_ui(
                            self.draft_viewer.texture.is_some() || self.draft_job.is_some(),
                            |ui| theme::tab(ui, "Draft", self.view == View::Draft),
                        )
                        .inner
                        .clicked()
                    {
                        self.view = View::Draft;
                    }
                    if ui
                        .add_enabled_ui(self.result_viewer.texture.is_some(), |ui| {
                            theme::tab(
                                ui,
                                if self.job.is_some() {
                                    "Previous result"
                                } else {
                                    "Result"
                                },
                                self.view == View::Result,
                            )
                        })
                        .inner
                        .clicked()
                    {
                        self.view = View::Result;
                    }
                    let name = match self.view {
                        View::Sources if self.canvas_mode.is_some() => {
                            let pair = self.current_pair();
                            Some(format!(
                                "PAIR TARGET {:03} / {:03}{}",
                                pair[0] + 1,
                                pair[1] + 1,
                                if self.held_pair.is_some() {
                                    " / HELD"
                                } else {
                                    ""
                                }
                            ))
                        }
                        View::Sources => self.stack.as_ref().and_then(|s| {
                            self.browser.displayed_index().and_then(|i| {
                                s.frames.get(i).map(|f| {
                                    format!(
                                        "{:03} / {:03}   {}",
                                        i + 1,
                                        s.frames.len(),
                                        f.path.file_name().unwrap_or_default().to_string_lossy()
                                    )
                                })
                            })
                        }),
                        View::Draft => Some("CAMERA JPEG / COMPOSITE".into()),
                        View::Result => self.image_path.as_ref().map(|p| {
                            p.file_name()
                                .unwrap_or_default()
                                .to_string_lossy()
                                .into_owned()
                        }),
                    };
                    let remaining = ui.available_rect_before_wrap();
                    let name_rect = egui::Rect::from_min_max(
                        remaining.left_top() + egui::vec2(12.0, 0.0),
                        egui::pos2(
                            (remaining.right() - 295.0).max(remaining.left() + 12.0),
                            remaining.bottom(),
                        ),
                    );
                    if let Some(name) = name {
                        ui.painter().with_clip_rect(name_rect).text(
                            name_rect.left_center(),
                            egui::Align2::LEFT_CENTER,
                            name,
                            egui::FontId::monospace(10.0),
                            MUTED,
                        );
                    }
                    let controls_rect = egui::Rect::from_min_max(
                        egui::pos2(remaining.right() - 285.0, remaining.top()),
                        remaining.max,
                    );
                    let mut controls = ui.new_child(
                        egui::UiBuilder::new()
                            .id_salt("canvas-scale")
                            .max_rect(controls_rect),
                    );
                    controls.with_layout(egui::Layout::right_to_left(egui::Align::Center), |ui| {
                        let in_workbench = self.view == View::Sources && self.canvas_mode.is_some();
                        let viewer = match self.view {
                            View::Sources => &mut self.source_viewer,
                            View::Draft => &mut self.draft_viewer,
                            View::Result => &mut self.result_viewer,
                        };
                        if ui
                            .add_enabled_ui(
                                !in_workbench && viewer.texture.is_some() && !viewer.overview,
                                |ui| theme::tab(ui, "1:1", !viewer.fit && viewer.zoom == 1.0),
                            )
                            .inner
                            .clicked()
                        {
                            viewer.reset(false);
                        }
                        if theme::tab(ui, "Fit", in_workbench || viewer.fit).clicked() {
                            viewer.reset(true);
                        }
                        if self.view == View::Sources {
                            if theme::tab(
                                ui,
                                "Frame difference",
                                matches!(self.canvas_mode, Some(WorkbenchMode::Compare)),
                            )
                            .clicked()
                            {
                                self.set_canvas_mode(
                                    if matches!(self.canvas_mode, Some(WorkbenchMode::Compare)) {
                                        None
                                    } else {
                                        Some(WorkbenchMode::Compare)
                                    },
                                );
                            }
                            if theme::tab(
                                ui,
                                "Detail",
                                matches!(self.canvas_mode, Some(WorkbenchMode::Probe)),
                            )
                            .clicked()
                            {
                                self.set_canvas_mode(
                                    if matches!(self.canvas_mode, Some(WorkbenchMode::Probe)) {
                                        None
                                    } else {
                                        Some(WorkbenchMode::Probe)
                                    },
                                );
                            }
                        }
                    });
                });
                let source_state = if self.view == View::Sources {
                    if let Some(error) = self.browser.error(self.selected) {
                        Some(format!(
                            "Showing {} / {} preview unavailable: {error}",
                            self.browser
                                .displayed_index()
                                .map_or("--".into(), |i| (i + 1).to_string()),
                            self.selected + 1
                        ))
                    } else if self.browser.pending() {
                        Some(format!(
                            "Showing frame {} / preparing frame {}",
                            self.browser
                                .displayed_index()
                                .map_or("--".into(), |i| (i + 1).to_string()),
                            self.selected + 1
                        ))
                    } else if self.browser.refining() {
                        Some("Refining detail / framing locked".into())
                    } else {
                        None
                    }
                } else {
                    None
                };
                let draft_caption = self.draft_info.as_ref().map_or_else(
                    || "Camera JPEG draft / composition only".into(),
                    |info| format!("Rough JPEG draft / {info}"),
                );
                let caption = match self.view {
                    View::Sources if self.canvas_mode.is_some() => {
                        "CAMERA JPEG / ORIGINAL POSITIONS"
                    }
                    View::Sources => source_state
                        .as_deref()
                        .unwrap_or("CAMERA JPEG / SOURCE FRAME"),
                    View::Draft => &draft_caption,
                    View::Result => "DEVELOPED TIFF / DISPLAY PREVIEW",
                };
                let loading = match self.view {
                    View::Sources => self.scan.is_some() || self.browser.active(),
                    View::Draft => self.draft_job.is_some(),
                    View::Result => self.result_work.is_some(),
                };
                let pair = self.current_pair();
                let (a_index, b_index) = if matches!(self.canvas_mode, Some(WorkbenchMode::Probe))
                    && self.held_pair.is_none()
                {
                    let current = self.browser.displayed_index().unwrap_or(self.selected);
                    let other = if pair[0] != current { pair[0] } else { pair[1] };
                    (current, other)
                } else {
                    (pair[0], pair[1])
                };
                let photo_a = self.source_photo(a_index);
                let photo_b = self.source_photo(b_index);
                let viewer = match self.view {
                    View::Sources => &mut self.source_viewer,
                    View::Draft => &mut self.draft_viewer,
                    View::Result => &mut self.result_viewer,
                };
                let mut image_ui = ui.new_child(
                    egui::UiBuilder::new()
                        .id_salt("photo-aperture")
                        .max_rect(photo),
                );
                image_ui.set_clip_rect(photo.intersect(ui.clip_rect()));
                let mut touched_pair = None;
                if self.view == View::Sources
                    && let Some(mode) = self.canvas_mode
                {
                    touched_pair =
                        self.workbench
                            .show(&mut image_ui, mode, photo_a, photo_b, self.epoch);
                } else {
                    viewer.show(&mut image_ui, loading);
                }
                let caption_rect = egui::Rect::from_min_max(
                    footer.min + egui::vec2(14.0, 0.0),
                    footer.max - egui::vec2(120.0, 0.0),
                );
                ui.painter().with_clip_rect(caption_rect).text(
                    caption_rect.left_center(),
                    egui::Align2::LEFT_CENTER,
                    caption,
                    egui::FontId::proportional(9.5),
                    MUTED,
                );
                ui.interact(
                    caption_rect,
                    ui.id().with("canvas-caption"),
                    egui::Sense::hover(),
                )
                .on_hover_text(caption);
                if viewer.texture.is_some()
                    && !(self.view == View::Sources && self.canvas_mode.is_some())
                {
                    ui.painter().text(
                        footer.right_center() - egui::vec2(14.0, 0.0),
                        egui::Align2::RIGHT_CENTER,
                        format!("{} x {}", viewer.source_size[0], viewer.source_size[1]),
                        egui::FontId::monospace(9.5),
                        MUTED,
                    );
                }
                if let Some(pair) = touched_pair {
                    self.hold_pair(pair);
                }
                // Notifications occupy an overlay; they never resize or re-fit the photo.
                let notice = self.error.as_ref().map(|e| (e.clone(), AMBER)).or_else(|| {
                    if self.view == View::Draft {
                        self.draft_progress.map(|(stage, done, total)| {
                            (format!("{} / {done} of {total}", stage.label()), ACCENT)
                        })
                    } else {
                        None
                    }
                });
                if let Some((notice, color)) = notice {
                    let rect = egui::Rect::from_min_max(
                        egui::pos2(photo.left() + 14.0, photo.bottom() - 40.0),
                        photo.right_bottom() - egui::vec2(14.0, 10.0),
                    );
                    ui.painter()
                        .rect_filled(rect, 0.0, PANEL.gamma_multiply(0.96));
                    ui.painter().line_segment(
                        [rect.left_top(), rect.left_bottom()],
                        Stroke::new(2.0_f32, color),
                    );
                    ui.painter().with_clip_rect(rect.shrink(6.0)).text(
                        rect.left_center() + egui::vec2(10.0, 0.0),
                        egui::Align2::LEFT_CENTER,
                        &notice,
                        egui::FontId::proportional(11.0),
                        color,
                    );
                    ui.interact(rect, ui.id().with("canvas-notice"), egui::Sense::hover())
                        .on_hover_text(notice);
                }
                self.live_portal(ui, photo);
            });
    }
    fn cache_process_surfaces(&mut self, ctx: &egui::Context) {
        if self.process_domain_epoch != self.progress.diagnostic_epoch {
            self.process_domain_epoch = self.progress.diagnostic_epoch;
            self.process_surfaces.clear();
        }
        let mut newest = BTreeSet::new();
        for sample in self
            .progress
            .diagnostic_surfaces
            .iter()
            .rev()
            .filter(|sample| newest.insert((sample.kind as u8, sample.level)))
        {
            let old = self.process_surfaces.iter().position(|s| {
                s.epoch == self.epoch && s.kind == sample.kind && s.level == sample.level
            });
            if old.is_some_and(|i| self.process_surfaces[i].sequence >= sample.sequence) {
                continue;
            }
            let colour = diagnostic_image(sample);
            let frame = (sample.scope == DiagnosticScope::Frame).then_some(sample.frame);
            let stage = if sample.kind == DiagnosticKind::Reconstructed {
                Stage::Rendering
            } else {
                Stage::Merge
            };
            let meta = process_space::SurfaceMeta {
                sequence: sample.sequence,
                kind: sample.kind,
                scale: sample.scale,
                min: sample.min,
                max: sample.max,
                samples: [sample.width, sample.height],
                folded: sample.folded,
            };
            if let Some(i) = old {
                let surface = &mut self.process_surfaces[i];
                // Delivered maps are immutable. The stage can retain the
                // preceding observation while revealing this one smoothly.
                surface.texture = ctx.load_texture(
                    format!("process-{}-{}", self.epoch, sample.sequence),
                    colour,
                    egui::TextureOptions::NEAREST,
                );
                surface.sequence = sample.sequence;
                surface.frame = frame;
                surface.meta = meta;
                surface.packet = sample.clone();
            } else {
                if self.process_surfaces.len() == 384 {
                    let oldest = self
                        .process_surfaces
                        .iter()
                        .enumerate()
                        .min_by_key(|(_, s)| s.sequence)
                        .unwrap()
                        .0;
                    self.process_surfaces.remove(oldest);
                }
                self.process_surfaces.push(ProcessSurface {
                    epoch: self.epoch,
                    sequence: sample.sequence,
                    kind: sample.kind,
                    level: sample.level,
                    stage,
                    frame,
                    texture: ctx.load_texture(
                        format!("process-{}-{}", self.epoch, sample.sequence),
                        colour,
                        egui::TextureOptions::NEAREST,
                    ),
                    meta,
                    packet: sample.clone(),
                });
            }
        }
        self.process_surfaces
            .sort_by_key(|surface| match surface.kind {
                DiagnosticKind::FocusEnergy => 0,
                DiagnosticKind::Coefficient => 1,
                DiagnosticKind::GateSupport => 2,
                DiagnosticKind::GateFloor => 3,
                DiagnosticKind::Averaging => 4,
                DiagnosticKind::Preview => 5,
                DiagnosticKind::Reconstructed => 6,
            });
    }
    fn show_process(&mut self, ctx: &egui::Context) {
        let count = self
            .stack
            .as_ref()
            .map(|stack| stack.frames.len())
            .or_else(|| self.expected_run.as_ref().map(|run| run.frames))
            .or(self.progress.frames_total)
            .unwrap_or(0);
        let photos: Vec<_> = self
            .browser
            .native_thumbnail_indices()
            .into_iter()
            .filter_map(|index| {
                self.browser
                    .native_thumbnail(index)
                    .map(|texture| SourcePhoto {
                        epoch: self.epoch,
                        index,
                        texture: texture.clone(),
                        aperture: [texture.size()[0] as u32, texture.size()[1] as u32],
                    })
            })
            .collect();
        let mut inspection_indices = self.browser.canonical_indices();
        inspection_indices.extend(self.process_pair());
        inspection_indices.push(self.selected);
        inspection_indices.sort_unstable();
        inspection_indices.dedup();
        let inspection_photos: Vec<_> = inspection_indices
            .into_iter()
            .filter_map(|index| self.source_photo(index))
            .collect();
        let surfaces: Vec<_> = self
            .process_surfaces
            .iter()
            .filter(|s| s.epoch == self.epoch)
            .map(|s| process_space::Surface {
                epoch: s.epoch,
                stage: s.stage,
                level: s.level,
                texture: &s.texture,
                frame: s.frame,
                meta: Some(s.meta),
                packet: Some(&s.packet),
            })
            .collect();
        self.process_space.set_output_path(
            self.result
                .as_deref()
                .filter(|_| self.image_path == self.result),
        );
        let response = egui::CentralPanel::default()
            .frame(egui::Frame::new().fill(BG))
            .show(ctx, |ui| {
                let input = process_space::Input {
                    progress: &self.progress,
                    frame_count: count,
                    selected: self.selected,
                    epoch: self.epoch,
                    photos: &photos,
                    inspection_photos: &inspection_photos,
                    surfaces: &surfaces,
                    output: if self.result.is_some() && self.image_path == self.result {
                        self.result_viewer.texture.as_ref()
                    } else {
                        None
                    },
                    inspected_pair: self.held_pair,
                    output_size: (self.result.is_some() && self.image_path == self.result)
                        .then_some(self.result_viewer.source_size),
                };
                if self.spatial_view {
                    self.process_atlas.show(ui, input)
                } else {
                    self.process_space.show(ui, input)
                }
            })
            .inner;
        self.apply_process_response(response, count);
    }
    fn apply_process_response(&mut self, response: process_space::Response, count: usize) {
        if response.exit_space {
            self.spatial_view = false;
            self.process_view = true;
        }
        if let Some(index) = response.selected {
            let view = self.view;
            self.select(index);
            self.view = view;
        }
        if let Some(pair) = response.compare_pair
            && pair.iter().all(|index| *index < count)
        {
            self.held_pair = Some(pair);
        }
        if response.return_live {
            self.resume_pair();
            self.process_view = true;
        }
        if response.open_sources {
            self.inspect_frame(self.process_inspection().unwrap_or(self.selected));
        }
    }
    fn workspace(&mut self, ctx: &egui::Context) {
        if !self.spatial_view {
            self.navigation_rail(ctx);
            self.sidebar(ctx);
        }
        if self.process_view {
            if self.stack.is_none() && !self.activity && self.expected_run.is_none() {
                self.welcome_workspace(ctx);
            } else {
                self.show_process(ctx);
            }
        } else {
            self.inspector(ctx);
            self.filmstrip(ctx);
            self.stack_ribbon(ctx);
            self.canvas(ctx);
        }
    }
    fn process_contacts(&self) -> Vec<usize> {
        if self.spatial_view {
            self.process_atlas.contact_indices()
        } else {
            self.process_space.contact_indices()
        }
    }
    fn process_inspection(&self) -> Option<usize> {
        if self.spatial_view {
            self.process_atlas.inspection_frame()
        } else {
            self.process_space.inspection_frame()
        }
    }
    fn preview_target(&self) -> usize {
        let count = self.stack.as_ref().map_or(0, |stack| stack.frames.len());
        let selected = self.selected.min(count.saturating_sub(1));
        if self.process_view {
            self.process_inspection()
                .filter(|&frame| frame < count)
                .unwrap_or(selected)
        } else {
            selected
        }
    }
    fn screenshot(&mut self, ctx: &egui::Context) {
        if self.screenshot.is_none() {
            return;
        }
        let now = ctx.input(|input| input.time);
        if self.reveal_started.is_none() && self.source_viewer.transitioning() {
            self.reveal_started = Some(now);
        }
        let reveal_ready = if let Some(ms) = self.reveal_at_ms {
            self.reveal_started
                .is_some_and(|started| (now - started) * 1000.0 >= ms)
        } else if self.process_view {
            // Hidden comparison widgets do not animate while Process owns the
            // viewport. Wait for the actual process input pair instead.
            let pair = self.process_pair();
            !(if self.spatial_view {
                self.process_atlas.transitioning()
            } else {
                self.process_space.transitioning()
            }) && (self.stack.is_none()
                || pair.iter().all(|index| {
                    self.source_photo(*index).is_some() || self.browser.error(*index).is_some()
                }))
        } else if self.view == View::Sources && self.canvas_mode.is_some() {
            let pair = self.current_pair();
            !self.workbench.transitioning()
                && self.source_photo(pair[0]).is_some()
                && self.source_photo(pair[1]).is_some()
        } else if self.view == View::Sources {
            !self.source_viewer.transitioning()
        } else {
            true
        };
        let ready = (self.reveal_at_ms.is_some() || self.updates > 10)
            && self.scan.is_none()
            && self.replay.is_none()
            && self.result_work.is_none()
            && self.pending_result.is_none()
            && reveal_ready
            && self.draft_job.is_none()
            && !self.draft_requested
            && (self.stack.is_none()
                || self.browser.has_image(self.preview_target())
                || self.browser.error(self.preview_target()).is_some())
            && (self.process_view
                || self.reveal_at_ms.is_some()
                || self
                    .visible_sources
                    .iter()
                    .all(|i| self.browser.has_thumbnail(*i) || self.browser.error(*i).is_some()));
        let ready = ready
            && (!self.bracket_browser.active() || self.bracket_browser.settled(now))
            && (!self.process_view
                || self.process_contacts().iter().all(|i| {
                    self.browser.native_thumbnail(*i).is_some()
                        || self.browser.native_thumbnail_error(*i).is_some()
                }));
        if ready && !self.screenshot_requested {
            if let Some(ranges) = self.screenshot_ranges.as_ref() {
                // Replay and result loading must finish before the theater's
                // initialized domain accepts this diagnostic-only selection.
                if self.progress.stage == Stage::Complete
                    && self.result.is_some()
                    && self.image_path == self.result
                    && self.result_viewer.texture.is_some()
                {
                    let captures = self.stack.as_ref().map_or(0, |stack| stack.frames.len());
                    let count = self.progress.frames_total.unwrap_or(captures).min(captures);
                    match self.process_space.screenshot_ranges(
                        (self.epoch, self.progress.diagnostic_epoch),
                        count,
                        ranges,
                    ) {
                        Ok(true) => {
                            self.screenshot_ranges = None;
                            self.screenshot_ranges_applied_frame = Some(ctx.cumulative_frame_nr());
                            self.held_pair = None;
                        }
                        Ok(false) => {}
                        Err(error) => {
                            eprintln!("Screenshot range preset rejected: {error}");
                            std::process::exit(2);
                        }
                    }
                }
                ctx.request_repaint_after(Duration::from_millis(30));
                return;
            }
            // The preset is applied after painting. Complete two later frames
            // before asking WGPU to capture; extra egui passes do not count.
            if self
                .screenshot_ranges_applied_frame
                .is_some_and(|applied| ctx.cumulative_frame_nr().saturating_sub(applied) <= 2)
            {
                ctx.request_repaint_after(Duration::from_millis(30));
                return;
            }
            self.screenshot_requested = true;
            self.reveal_requested_elapsed =
                self.reveal_started.map(|started| (now - started) * 1000.0);
            ctx.send_viewport_cmd(egui::ViewportCommand::Screenshot(egui::UserData::default()));
        }
        let image = ctx.input(|i| {
            i.events.iter().find_map(|e| {
                if let egui::Event::Screenshot { image, .. } = e {
                    Some(image.clone())
                } else {
                    None
                }
            })
        });
        if let Some(image) = image {
            if let Some(path) = self.screenshot.take() {
                if let Some(target) = self.reveal_at_ms {
                    let receipt = format!(
                        "{{\"target_elapsed_ms\":{target},\"requested_elapsed_ms\":{},\"source_index\":{}}}",
                        self.reveal_requested_elapsed.unwrap_or(0.0),
                        self.preview_target()
                    );
                    let _ = std::fs::write(path.with_extension("capture.json"), receipt);
                }
                let bytes: Vec<u8> = image.pixels.iter().flat_map(|p| p.to_array()).collect();
                if let Err(e) = image::save_buffer(
                    &path,
                    &bytes,
                    image.width() as u32,
                    image.height() as u32,
                    image::ColorType::Rgba8,
                ) {
                    eprintln!("Screenshot failed: {e}");
                    std::process::exit(1);
                }
            }
            ctx.send_viewport_cmd(egui::ViewportCommand::Close);
        }
        ctx.request_repaint_after(Duration::from_millis(30));
    }
    fn update_workspace(&mut self, ctx: &egui::Context) {
        self.updates += 1;
        let image_domain = (
            self.epoch,
            self.spatial_view,
            self.process_view,
            self.picker_active(),
        );
        let domain_changed = ctx.data_mut(|data| {
            let id = egui::Id::new("image-gesture-workspace-domain");
            let changed = data.get_temp::<(u64, bool, bool, bool)>(id) != Some(image_domain);
            data.insert_temp(id, image_domain);
            changed
        });
        if domain_changed || self.picker_active() {
            crate::image_gesture::clear(ctx);
        }
        self.poll(ctx);
        // Windows can deliver a tiny drawable area during minimize/restore.
        // Laying out that transient area clamps egui's remembered pane widths
        // and can produce negative child sizes. Continue consuming engine work
        // above, but preserve the last real layout until the window returns.
        let drawable = ctx.content_rect().size();
        if ctx.input(|i| i.viewport().minimized == Some(true))
            || drawable.x < 640.0
            || drawable.y < 360.0
        {
            ctx.request_repaint_after(Duration::from_millis(200));
            return;
        }
        self.undo_shortcuts(ctx);
        if !ctx.wants_keyboard_input() && !self.picker_active() {
            if ctx.input(|i| i.modifiers.command && i.key_pressed(egui::Key::O))
                && self.job.is_none()
            {
                self.pick(Dialog::Source);
            }
            if !self.process_view && ctx.input(|i| i.key_pressed(egui::Key::ArrowLeft)) {
                self.inspect_frame(self.selected.saturating_sub(1));
            }
            if !self.process_view && ctx.input(|i| i.key_pressed(egui::Key::ArrowRight)) {
                self.inspect_frame(self.selected.saturating_add(1));
            }
        }
        for path in ctx.input(|i| {
            i.raw
                .dropped_files
                .iter()
                .filter_map(|f| f.path.clone())
                .collect::<Vec<_>>()
        }) {
            if self.job.is_none() && !self.picker_active() {
                if path.is_dir() {
                    self.import(path);
                } else if is_image(&path) {
                    self.open_result(path);
                }
            }
        }
        if !self.spatial_view {
            self.status_bar(ctx);
        }
        self.workspace(ctx);
        self.observe_edits(ctx);
        let layout = self.process_space.layout();
        if layout != self.catalog.layout && !ctx.input(|i| i.pointer.primary_down()) {
            self.catalog.layout = layout;
            self.persist_catalog();
        }
        if let Some(directory) = self.bracket_browser.show(ctx) {
            self.import(directory);
            ctx.request_repaint();
        }
        if self.spatial_view {
            crate::window_chrome::finish_spatial(ctx, self.picker_active());
        } else {
            crate::window_chrome::finish(ctx, self.picker_active());
        }
        if let Some(edited) = self.catalog_edit_pending {
            if edited.elapsed() >= Duration::from_millis(300)
                && !ctx.input(|i| i.pointer.any_down())
            {
                self.persist_catalog();
            } else {
                ctx.request_repaint_after(Duration::from_millis(100));
            }
        }
        self.screenshot(ctx);
    }
}
impl eframe::App for StrehlApp {
    fn raw_input_hook(&mut self, ctx: &egui::Context, raw: &mut egui::RawInput) {
        // Deterministic, screenshot-only GPU inspection. This changes input
        // inside this owned renderer; no operating-system pointer is touched.
        if self.screenshot.is_some()
            && let Some([x, y]) = self.screenshot_hover
        {
            let screen = raw.screen_rect.unwrap_or_else(|| ctx.content_rect());
            if screen.is_finite() && screen.is_positive() {
                raw.focused = true;
                if let Some(viewport) = raw.viewports.get_mut(&raw.viewport_id) {
                    viewport.focused = Some(true);
                    viewport.minimized = Some(false);
                }
                // Applying a preset deliberately suppresses the old stationary
                // hover. Leave the canvas for one frame, then re-enter through
                // the same hover routing as a real source inspection.
                let after_preset = self
                    .screenshot_ranges_applied_frame
                    .is_some_and(|applied| ctx.cumulative_frame_nr().saturating_sub(applied) == 1);
                let pointer = if after_preset {
                    screen.min - egui::vec2(32.0, 32.0)
                } else {
                    screen.min + screen.size() * egui::vec2(x, y)
                };
                raw.events.push(egui::Event::PointerMoved(pointer));
            }
        }
    }
    fn update(&mut self, ctx: &egui::Context, _: &mut eframe::Frame) {
        self.update_workspace(ctx);
    }
    fn on_exit(&mut self) {
        if self.catalog_edit_pending.is_some() {
            self.persist_catalog();
        }
    }
}
pub(crate) fn diagnostic_image(sample: &DiagnosticSurface) -> egui::ColorImage {
    let pixels: Vec<_> = sample
        .pixels
        .iter()
        .map(|&v| {
            if matches!(
                sample.kind,
                DiagnosticKind::Preview | DiagnosticKind::Reconstructed
            ) {
                return Color32::from_gray(
                    ((v as f32 / 255.0).powf(1.0 / 2.2) * 255.0).round() as u8
                );
            }
            if sample.kind == DiagnosticKind::Coefficient && sample.min == 0.0 && sample.max == 0.0
            {
                // Diagnostic zero must match the signed colour ramp's centre,
                // independently of the surrounding workspace theme.
                return Color32::from_rgb(14, 17, 20);
            }
            let t = v as f32 / 255.0;
            let rgb = if sample.kind == DiagnosticKind::Coefficient {
                // The transport uses a symmetric physical range: its midpoint is
                // zero, not the midpoint of an independently stretched photograph.
                if t < 0.5 {
                    egui::lerp(egui::vec2(26.0, 92.0)..=egui::vec2(14.0, 17.0), t * 2.0)
                } else {
                    egui::lerp(
                        egui::vec2(14.0, 17.0)..=egui::vec2(224.0, 183.0),
                        (t - 0.5) * 2.0,
                    )
                }
            } else {
                egui::vec2(14.0 + 142.0 * t, 17.0 + 194.0 * t)
            };
            let blue = if sample.kind == DiagnosticKind::Coefficient {
                if t < 0.5 {
                    144.0 * (1.0 - t * 2.0) + 20.0 * t * 2.0
                } else {
                    20.0 + 96.0 * (t - 0.5) * 2.0
                }
            } else {
                20.0 + 204.0 * t
            };
            Color32::from_rgb(rgb.x as u8, rgb.y as u8, blue as u8)
        })
        .collect();
    egui::ColorImage::new([sample.width, sample.height], pixels)
}
fn cache_image(ctx: &egui::Context, image: PreviewImage) -> CachedImage {
    let color = egui::ColorImage::from_rgba_unmultiplied(image.size, &image.rgba);
    CachedImage {
        texture: ctx.load_texture(
            image.path.to_string_lossy(),
            color,
            egui::TextureOptions::LINEAR,
        ),
        source_size: image.source_size,
        overview: image.is_overview,
    }
}
fn install_viewer(viewer: &mut Viewer, image: &CachedImage) {
    viewer.install(&image.texture, image.source_size, image.overview);
}
fn dot(ui: &mut egui::Ui, color: Color32) {
    let (r, _) = ui.allocate_exact_size(egui::vec2(7.0, 14.0), egui::Sense::hover());
    ui.painter().circle_filled(r.center(), 2.5, color);
}
fn elapsed(t: Duration) -> String {
    format!("{:02}:{:02}", t.as_secs() / 60, t.as_secs() % 60)
}
fn bytes(n: u64) -> String {
    if n >= 1 << 30 {
        format!("{:.1} GiB", n as f64 / (1_u64 << 30) as f64)
    } else {
        format!("{:.0} MiB", n as f64 / (1_u64 << 20) as f64)
    }
}
fn short_path(p: &Path) -> String {
    let parent = p
        .parent()
        .and_then(|p| p.file_name())
        .unwrap_or_default()
        .to_string_lossy();
    format!(
        "{} / {}",
        parent,
        p.file_name().unwrap_or_default().to_string_lossy()
    )
}
fn is_image(p: &Path) -> bool {
    p.extension().and_then(|s| s.to_str()).is_some_and(|s| {
        ["png", "jpg", "jpeg", "tif", "tiff"].contains(&s.to_ascii_lowercase().as_str())
    })
}
fn default_output() -> PathBuf {
    let current = std::env::current_dir().unwrap_or_else(|_| PathBuf::from("."));
    let outputs = current.join("outputs");
    if outputs.is_dir() { outputs } else { current }
}
fn find_engine() -> Option<PathBuf> {
    crate::engine::bundled_executable()
}

#[cfg(test)]
mod screenshot_range_tests {
    use super::*;

    #[test]
    fn screenshot_hover_reenters_after_the_range_preset_without_editing_ranges() {
        let ctx = egui::Context::default();
        let mut app = StrehlApp::from_launch(4096, LaunchOptions::default());
        app.screenshot = Some(PathBuf::from("unused-range-hover.png"));
        app.screenshot_hover = Some([0.58, 0.87]);
        let mut row = crate::process_participation::CaptureParticipation::default();
        let mut progress = PipelineProgress::default();
        progress.mark_complete();
        let paint =
            |app: &mut StrehlApp, row: &mut crate::process_participation::CaptureParticipation| {
                let mut raw = egui::RawInput {
                    screen_rect: Some(egui::Rect::from_min_size(
                        egui::Pos2::ZERO,
                        egui::vec2(960.0, 600.0),
                    )),
                    ..Default::default()
                };
                eframe::App::raw_input_hook(app, &ctx, &mut raw);
                let mut picked = Default::default();
                let _ = ctx.run(raw, |ctx| {
                    egui::CentralPanel::default().show(ctx, |ui| {
                        picked = row.show(
                            ui,
                            egui::Rect::from_min_size(
                                egui::pos2(20.0, 340.0),
                                egui::vec2(900.0, crate::process_participation::HEIGHT),
                            ),
                            &process_space::Input {
                                epoch: 1,
                                progress: &progress,
                                frame_count: 67,
                                selected: 0,
                                inspected_pair: None,
                                photos: &[],
                                inspection_photos: &[],
                                surfaces: &[],
                                output: None,
                                output_size: None,
                            },
                            &progress.admission_archive,
                            1,
                            egui::Rect::from_min_max(egui::Pos2::ZERO, egui::pos2(1.0, 1.0)),
                        );
                    });
                });
                picked
            };
        paint(&mut app, &mut row);
        let original = paint(&mut app, &mut row);
        assert!(
            original.hover_source.is_some(),
            "fixture must begin over the source lane"
        );
        assert_eq!(
            row.screenshot_ranges((1, progress.diagnostic_epoch), 67, &[[4, 12], [31, 35]]),
            Ok(true)
        );
        let spans = row.spans().to_vec();
        app.screenshot_ranges_applied_frame = Some(ctx.cumulative_frame_nr() - 1);
        let outside = paint(&mut app, &mut row);
        assert!(outside.hover_source.is_none());
        let restored = paint(&mut app, &mut row);
        assert_eq!(restored.hover_source, original.hover_source);
        assert_eq!(restored.spans, spans);
        assert_eq!(
            paint(&mut app, &mut row).hover_source,
            original.hover_source
        );
        app.screenshot = None;
        let mut normal_input = egui::RawInput::default();
        eframe::App::raw_input_hook(&mut app, &ctx, &mut normal_input);
        assert!(normal_input.events.is_empty());
    }

    #[test]
    fn range_preset_waits_for_two_completed_paints_before_capture() {
        let ctx = egui::Context::default();
        let mut app = StrehlApp::from_launch(4096, LaunchOptions::default());
        app.updates = 11;
        app.screenshot = Some(PathBuf::from("unused-range-timing.png"));
        app.screenshot_ranges_applied_frame = Some(ctx.cumulative_frame_nr());
        for frame in 0..4 {
            let _ = ctx.run(egui::RawInput::default(), |ctx| {
                // Repeated application updates within one frame cannot count
                // as additional completed GPU paints.
                app.screenshot(ctx);
                app.screenshot(ctx);
            });
            assert_eq!(app.screenshot_requested, frame == 3, "frame {frame}");
        }
    }
}
