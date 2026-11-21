//! Develop and Export stations, app side: building their views from app state,
//! applying the intents that need the app (looks, the white-balance sample,
//! versions, export), the depth repair's background re-stack (P7c), and the
//! Export station's preset library, batch and history.
//!
//! The depth repair runs as its own render job, beside `self.job`: the
//! photograph stays loaded and Export stays enabled, exporting the master's
//! baked repairs (`EditorState::export_recipe`) with a visible note.
#![allow(
    dead_code,
    reason = "the Studio 2 shell (P1) calls the show_* parts; the editor polls the rest"
)]
use super::*;
use crate::develop_station::{
    self as station, DevelopIntent, DevelopPanel, DevelopView, RangeFallback, RepairView,
    VersionRow, style::StudioPalette,
};
use crate::export_presets::{self as presets, NameFields};
use crate::export_station::{
    self as exporting, BatchContext, BatchDone, BatchProgress, BatchText, ExportIntent,
    ExportPanel, ExportView, HistoryRow, HistoryStatus,
};
use std::{collections::HashMap, sync::Arc};
use strehl_edit::{AdaptiveIntent, DevelopmentRecipe};

/// The depth repair's own re-stack.
pub(super) struct DepthRepair {
    job: jobs::RenderJob,
    progress: PipelineProgress,
    pub(super) document: PathBuf,
    recipe: DevelopmentRecipe,
    started: Instant,
    run: Option<crate::workspace_history::Run>,
    stack: Option<crate::workspace_history::NodeId>,
    pub(super) route: RepairRoute,
    /// The whole-stack re-render a region-only rebuild falls back to if it
    /// stops, with its library record.
    fallback: Option<(RenderRequest, crate::workspace_history::Run)>,
}

/// How a depth repair rebuilds (implementation plan E4).
#[derive(Clone, Debug, PartialEq, Eq)]
pub(super) enum RepairRoute {
    /// Only the painted regions, against the open render's master: their
    /// frames alone are decoded and every other pixel keeps its bytes.
    Region,
    /// The whole stack again, and why the region-only rebuild was not used.
    Full(String),
}

impl DepthRepair {
    pub(super) fn status(&self) -> String {
        let seconds = self.started.elapsed().as_secs();
        let area = match self.progress.source_repair {
            Some(repair) if !repair.finished && repair.regions > 1 => {
                format!(" · area {} of {}", repair.region + 1, repair.regions)
            }
            _ => String::new(),
        };
        match self.route {
            RepairRoute::Region => format!("Rebuilding the painted area only{area} · {seconds} s"),
            RepairRoute::Full(_) => format!("Re-stacking the whole stack{area} · {seconds} s"),
        }
    }

    /// Why the whole stack is re-stacked, or what the region-only rebuild keeps.
    pub(super) fn detail(&self) -> String {
        match &self.route {
            RepairRoute::Region => {
                "Region-only: only the painted frames are read; the rest of the photograph keeps its pixels"
                    .into()
            }
            RepairRoute::Full(why) => format!("Whole stack: {why}"),
        }
    }
}

/// App-side state of the two stations.
#[derive(Default)]
pub(super) struct DevelopApp {
    pub(super) panel: DevelopPanel,
    pub(super) repair: Option<DepthRepair>,
    /// The repaired render, opened once the editor is idle.
    repair_ready: Option<Task<PathBuf>>,
    pub(super) notice: Option<String>,
    notice_shown: Option<String>,
    /// The theme's palette, refreshed each frame the station draws.
    pub(super) palette: StudioPalette,
    carry: Option<Task<DevelopmentRecipe>>,
    /// Set by the Export… intent; the shell routes to the Export station.
    pub(super) export_requested: bool,
}

/// One recorded export's check: its id, its file's state, and its version's
/// recipe (to flag files older than the current edit).
type HistoryCheck = (String, HistoryStatus, Option<(String, DevelopmentRecipe)>);

/// App-side state of the Export station.
#[derive(Default)]
pub(super) struct ExportApp {
    pub(super) panel: ExportPanel,
    pub(super) library: Option<presets::Library>,
    library_bytes: Option<Vec<u8>>,
    loading: Option<Task<presets::LoadedLibrary>>,
    saving: Option<Task<Vec<u8>>>,
    save_again: bool,
    pub(super) batch: Option<RunningBatch>,
    checked: HashMap<String, HistoryStatus>,
    version_recipes: HashMap<String, DevelopmentRecipe>,
    checking: Option<Task<Vec<HistoryCheck>>>,
    folder: Option<Task<Option<PathBuf>>>,
    pub(super) error: Option<String>,
    error_shown: Option<String>,
}

pub(super) struct RunningBatch {
    pub(super) progress: Arc<BatchProgress>,
    task: Task<(Option<crate::workspace_history::PhotoVersion>, BatchDone)>,
}

/// Local `9 Nov 22:10` for a Unix time.
fn when_text(seconds: u64) -> String {
    chrono::DateTime::from_timestamp(seconds as i64, 0)
        .map(|t| {
            t.with_timezone(&chrono::Local)
                .format("%-d %b %H:%M")
                .to_string()
        })
        .unwrap_or_default()
}

/// Today's local date for the `{date}` name token.
fn date_text() -> String {
    chrono::Local::now().format("%Y-%m-%d").to_string()
}

impl StrehlApp {
    // ------------------------------------------------------------- develop

    /// The subject of the open photograph: its key, name and calibration.
    fn develop_subject(&self) -> (String, String, Option<f64>) {
        let stack = self.active_stack;
        let subject = stack.and_then(|id| self.catalog.subject_of(id));
        if let Some(node) = subject.and_then(|id| self.catalog.node(id)) {
            let scale = node
                .subject
                .as_ref()
                .and_then(|meta| meta.scale.as_ref())
                .map(|s| s.um_per_px);
            return (format!("subject-{}", node.id), node.name.clone(), scale);
        }
        let name = self
            .editor
            .path
            .as_ref()
            .and_then(|p| p.parent())
            .and_then(|p| p.file_name())
            .map_or_else(|| "photograph".into(), |n| n.to_string_lossy().into_owned());
        (format!("photo-{name}"), name, None)
    }

    fn develop_versions(&self) -> Vec<VersionRow> {
        let mut rows = vec![VersionRow {
            id: String::new(),
            name: "Edited now".into(),
            detail: format!(
                "{} layer{}",
                self.editor.recipe.regions.len(),
                if self.editor.recipe.regions.len() == 1 {
                    ""
                } else {
                    "s"
                }
            ),
            current: true,
        }];
        if let Some(path) = &self.editor.path {
            rows.extend(
                self.catalog
                    .photo_versions
                    .iter()
                    .rev()
                    .filter(|v| &v.owner.output == path)
                    .take(32)
                    .map(|v| VersionRow {
                        id: v.id.clone(),
                        name: v.name.clone(),
                        detail: when_text(v.created),
                        current: false,
                    }),
            );
        }
        rows
    }

    fn look_state(&self) -> (Option<usize>, Option<f32>) {
        let field = self
            .editor
            .recipe
            .adaptive_scope(self.editor.selected.as_deref());
        let look = field.and_then(|f| {
            station::looks()
                .iter()
                .position(|look| look.parameters == f.parameters)
        });
        (look, field.map(|f| f.amount))
    }

    /// Build the Develop view for this frame and run `show` with it.
    fn with_develop_view<R>(
        &mut self,
        show: impl FnOnce(
            &DevelopView<'_>,
            &[station::layers::LayerRow],
            &mut DevelopPanel,
            &station::DevelopCanvas,
        ) -> R,
    ) -> Option<R> {
        let loaded = self.editor.loaded.as_ref()?;
        let palette = self.edit_pane.develop.palette;
        let (_, _, um_per_px) = self.develop_subject();
        let (look, look_amount) = self.look_state();
        let versions = self.develop_versions();
        let baked = loaded.image.baked_recipe.clone();
        let pending_ids: Vec<String> = {
            let held = baked
                .as_ref()
                .map(|b| {
                    b.regions
                        .iter()
                        .filter(|r| r.enabled && r.source_range.is_some())
                        .cloned()
                        .collect::<Vec<_>>()
                })
                .unwrap_or_default();
            self.editor
                .recipe
                .regions
                .iter()
                .filter(|r| r.enabled && r.source_range.is_some())
                .filter(|r| {
                    !held.iter().any(|h| {
                        h.id == r.id
                            && h.shape == r.shape
                            && h.feather == r.feather
                            && h.source_range == r.source_range
                    })
                })
                .map(|r| r.id.clone())
                .collect()
        };
        let rows =
            station::layers::layer_rows(&self.editor.recipe, |r| pending_ids.contains(&r.id));
        let render = self
            .editor
            .path
            .as_ref()
            .and_then(|p| p.parent())
            .and_then(|p| p.file_name())
            .map_or_else(
                || "this render".into(),
                |n| n.to_string_lossy().into_owned(),
            );
        let view = DevelopView {
            palette: &palette,
            recipe: &self.editor.recipe,
            scope: self.editor.selected.as_deref(),
            histogram: self.editor.histogram.as_deref(),
            look,
            look_amount,
            look_busy: self.adaptive_busy() || self.presets_busy(),
            versions: &versions,
            render: &render,
            repair: RepairView {
                pending: self.editor.repairs_pending(),
                running: self
                    .edit_pane
                    .develop
                    .repair
                    .as_ref()
                    .map(DepthRepair::status),
            },
            planes: self.stack.as_ref().map(|s| s.frames.len()),
            um_per_px,
            image_size: [loaded.image.width, loaded.image.height],
            hdr_photo: loaded.image.origin == strehl_edit::ImageOrigin::SceneLinear,
            hdr_available: self.editor.viewport.hdr_available(loaded.image.origin),
            hdr_display: self.editor.viewport.hdr_active(loaded.image.origin),
            display: self.develop_display_lines(),
            can_export: self.develop_can_export(),
        };
        let canvas = &self.editor.develop;
        let panel = &mut self.edit_pane.develop.panel;
        Some(show(&view, &rows, panel, canvas))
    }

    /// The tools strip, for the shell's 44 px column, with the Develop keys.
    pub(super) fn show_develop_tools(&mut self, ui: &mut egui::Ui) {
        self.edit_pane.develop.palette = StudioPalette::of(ui.ctx());
        let palette = self.edit_pane.develop.palette;
        let mut intents = Vec::new();
        if let Some(tool) = station::tools_strip(ui, &palette, self.editor.develop.tool) {
            intents.push(DevelopIntent::SelectTool(tool));
        }
        if let Some(tool) = station::tool_shortcut(ui.ctx()) {
            intents.push(DevelopIntent::SelectTool(tool));
        }
        intents.extend(station::view_shortcuts(ui.ctx(), &self.editor.develop));
        let time = ui.input(|i| i.time);
        self.handle_develop_intents(intents, time);
    }

    /// The control strip, drawn into the shell's 36 px row.
    pub(super) fn show_develop_strip(&mut self, ui: &mut egui::Ui) {
        self.edit_pane.develop.palette = StudioPalette::of(ui.ctx());
        let intents = self
            .with_develop_view(|view, _, _, canvas| station::control_strip(ui, view, canvas))
            .unwrap_or_default();
        let time = ui.input(|i| i.time);
        self.handle_develop_intents(intents, time);
    }

    /// The rail slot while the depth brush is out. `RangeFallback` stands in
    /// for the Stack station's depth rail, which implements `DepthRail`.
    pub(super) fn show_develop_rail(&mut self, ui: &mut egui::Ui) {
        let intents = self
            .with_develop_view(|view, _, _, canvas| {
                station::depth_rail(ui, view, canvas, &mut RangeFallback)
            })
            .unwrap_or_default();
        let time = ui.input(|i| i.time);
        self.handle_develop_intents(intents, time);
    }

    /// The inspector's tab captions and the open tab.
    pub(super) fn develop_tab_labels(
        &mut self,
    ) -> Option<([(station::InspectorTab, String); 3], station::InspectorTab)> {
        self.with_develop_view(|view, rows, panel, _| (station::tab_labels(view, rows), panel.tab))
    }

    /// The open tab, for a body the caller pads and scrolls.
    pub(super) fn show_develop_tab(&mut self, ui: &mut egui::Ui) -> Vec<DevelopIntent> {
        self.with_develop_view(|view, rows, panel, _| station::tab_contents(ui, panel, view, rows))
            .unwrap_or_default()
    }

    /// What the display reports, for Develop's Display group.
    fn develop_display_lines(&self) -> Vec<String> {
        let Some(presenter) = &self.editor.viewport.presenter else {
            return Vec::new();
        };
        let display = presenter.status();
        let mut lines = vec![
            if display.active {
                "Display · HDR active".to_owned()
            } else {
                "Display · SDR".to_owned()
            },
            display.monitor.clone(),
            display.reason.clone(),
        ];
        if display.active {
            lines.push(format!(
                "{:.0} nits white · {:.0} nits peak",
                display.sdr_white_nits, display.peak_nits
            ));
        }
        lines.retain(|line| !line.is_empty());
        lines
    }

    /// The inspector footer: Export… and Save version.
    pub(super) fn show_develop_footer(&mut self, ui: &mut egui::Ui) {
        let intents = self
            .with_develop_view(|view, _, _, _| station::inspector_footer(ui, view))
            .unwrap_or_default();
        let time = ui.input(|i| i.time);
        self.handle_develop_intents(intents, time);
    }

    /// Export is enabled whenever a photograph is open and idle; a pending
    /// depth repair no longer blocks it (P7c).
    pub(super) fn develop_can_export(&self) -> bool {
        self.editor.loaded.is_some()
            && self.editor.path == self.result
            && self.editor.loading.is_none()
            && self.editor.exporting.is_none()
            && !self.photo_history_busy()
            && self.editor.dialog.is_none()
            && !self.adaptive_busy()
            && !self.presets_busy()
    }

    /// Shown wherever an export starts while a repair waits.
    pub(super) fn repair_export_note(&self) -> Option<&'static str> {
        self.editor
            .repairs_pending()
            .then_some("A depth repair is pending: this export uses the last finished pixels.")
    }

    pub(super) fn handle_develop_intents(&mut self, intents: Vec<DevelopIntent>, time: f64) {
        for intent in intents {
            if let Err(error) = self.handle_develop_intent(&intent, time) {
                self.edit_pane.develop.notice = Some(error.to_string());
            }
        }
    }

    fn handle_develop_intent(&mut self, intent: &DevelopIntent, time: f64) -> anyhow::Result<()> {
        if self.editor.apply_develop(intent, time)? {
            return Ok(());
        }
        let keep_amount = || self.look_state().1.unwrap_or(1.0);
        match intent {
            DevelopIntent::PickLook(i) | DevelopIntent::ResetToLook(i) => {
                let look = station::looks()
                    .get(*i)
                    .copied()
                    .ok_or_else(|| anyhow::anyhow!("No such look"))?;
                let amount = keep_amount();
                self.start_adaptive_parameters(
                    amount,
                    AdaptiveIntent::Balance,
                    look.parameters,
                    false,
                )?;
            }
            DevelopIntent::Recalculate => {
                let field = self
                    .editor
                    .recipe
                    .adaptive_scope(self.editor.selected.as_deref())
                    .ok_or_else(|| anyhow::anyhow!("Choose a look first"))?;
                let (parameters, amount) = (field.parameters, field.amount);
                // Recalculate keeps the amount (it reset to 1.00 before P7).
                self.start_adaptive_parameters(amount, AdaptiveIntent::Balance, parameters, false)?;
            }
            DevelopIntent::SetLookAmount(amount) => {
                let before = self.editor.recipe.clone();
                self.set_spatial_amount(*amount)?;
                if self.editor.recipe != before {
                    self.editor.begin_edit(before, time);
                }
            }
            DevelopIntent::PickNeutral => {
                self.editor.develop.tool = station::DevelopTool::WhiteBalance;
            }
            DevelopIntent::SampleNeutral(uv) => {
                let pick = self
                    .editor
                    .loaded
                    .as_ref()
                    .and_then(|loaded| loaded.image.pick_white_balance(*uv, 3))
                    .ok_or_else(|| {
                        anyhow::anyhow!(
                            "That spot has no light to balance; pick something neutral and lit"
                        )
                    })?;
                let before = self.editor.recipe.clone();
                let index = self
                    .editor
                    .selected
                    .as_ref()
                    .and_then(|id| self.editor.recipe.regions.iter().position(|r| &r.id == id));
                let adjustments = match index {
                    Some(i) => &mut self.editor.recipe.regions[i].adjustments,
                    None => &mut self.editor.recipe.global,
                };
                adjustments.temperature = pick.temperature;
                adjustments.tint = pick.tint;
                self.editor.before = false;
                self.editor.begin_edit(before, time);
                self.editor.commit_edit();
                self.edit_pane.develop.notice = pick.clamped.then(|| {
                    "This neutral needs more than warmth and tint can give (a factor of 2); it is partly corrected.".into()
                });
            }
            DevelopIntent::StartRepair => self.start_depth_repair()?,
            DevelopIntent::SaveVersion => self.open_save_edit_version(),
            DevelopIntent::OpenVersion(id) if !id.is_empty() => self.restore_edit_version(id)?,
            DevelopIntent::CarryVersion(id) if !id.is_empty() => self.carry_version(id)?,
            DevelopIntent::Export => self.edit_pane.develop.export_requested = true,
            DevelopIntent::SetHdr(on) => self.editor.viewport.prefer_sdr = !on,
            _ => {}
        }
        Ok(())
    }

    /// Apply a version's recipe to the current render, keeping this master's
    /// repairs: "carry to the new render". The payload is read on a worker.
    fn carry_version(&mut self, id: &str) -> anyhow::Result<()> {
        anyhow::ensure!(
            self.edit_pane.develop.carry.is_none(),
            "A version is already being carried"
        );
        let record = self
            .catalog
            .photo_versions
            .iter()
            .find(|v| v.id == id)
            .cloned()
            .ok_or_else(|| anyhow::anyhow!("This version is no longer listed"))?;
        let root = self
            .catalog
            .history_root()
            .ok_or_else(|| anyhow::anyhow!("No project storage folder is available"))?;
        self.edit_pane.develop.carry = Some(jobs::spawn_task("strehl-carry-version", move |_| {
            crate::workspace_history::photographs::read_preview_recipe(&root, &record)
        }));
        Ok(())
    }

    /// Per frame, from `poll_editing`.
    pub(super) fn poll_develop(&mut self, ctx: &egui::Context) {
        let develop = &mut self.edit_pane.develop;
        if develop.notice.is_some() && develop.notice != develop.notice_shown {
            develop.notice_shown = develop.notice.clone();
            let text = develop.notice.clone().unwrap_or_default();
            self.shell.notices.push(
                crate::notices::Severity::Warning,
                crate::notices::Source::Develop,
                text,
                None,
            );
        }
        let station = &mut self.export_pane.station;
        if station.error.is_some() && station.error != station.error_shown {
            station.error_shown = station.error.clone();
            let text = station.error.clone().unwrap_or_default();
            self.shell.notices.push(
                crate::notices::Severity::Warning,
                crate::notices::Source::Export,
                text,
                None,
            );
        }
        let (_, _, um_per_px) = self.develop_subject();
        self.editor.um_per_px = um_per_px;
        let intents = self.editor.develop.take_intents();
        if !intents.is_empty() {
            let time = ctx.input(|i| i.time);
            self.handle_develop_intents(intents, time);
        }
        if let Some(result) = self
            .edit_pane
            .develop
            .carry
            .as_ref()
            .and_then(|task| task.receiver.try_recv().ok())
        {
            self.edit_pane.develop.carry = None;
            match result {
                Ok(recipe) => {
                    let baked = self
                        .editor
                        .loaded
                        .as_ref()
                        .and_then(|loaded| loaded.image.baked_recipe.clone());
                    let carried = recipe.with_baked_repairs(baked.as_ref());
                    if let Err(error) = self.editor.replace(carried) {
                        self.edit_pane.develop.notice = Some(error.to_string());
                    }
                }
                Err(error) => self.edit_pane.develop.notice = Some(error),
            }
        }
        self.poll_depth_repair(ctx);
        self.poll_export_station(ctx);
    }

    // -------------------------------------------------------- depth repair

    /// Re-stack with the recipe's repairs as a separate job. The photograph
    /// stays loaded and editable; `self.job` stays free.
    pub(super) fn start_depth_repair(&mut self) -> anyhow::Result<()> {
        anyhow::ensure!(
            self.edit_pane.develop.repair.is_none(),
            "A depth repair is already rebuilding"
        );
        if let Some(blocker) = self.stack_start_blocker() {
            anyhow::bail!(blocker);
        }
        anyhow::ensure!(
            self.editor.loaded.is_some() && self.editor.path == self.result,
            "Open the stack's photograph first"
        );
        anyhow::ensure!(
            self.controls.settings.session.is_none(),
            "Session stacking does not yet support source-range repairs"
        );
        let (Some(stack), Some(engine), Some(document)) = (
            self.stack.as_ref(),
            self.engine.clone(),
            self.editor.path.clone(),
        ) else {
            anyhow::bail!("Choose the stack's source photos first");
        };
        self.editor.commit_edit();
        let recipe = self.editor.recipe.clone();
        let mut run = crate::workspace_history::Run {
            directory: PathBuf::new(),
            source: stack.directory.clone(),
            output: PathBuf::new(),
            log: PathBuf::new(),
            label: format!(
                "{} · repaired",
                stack
                    .directory
                    .file_name()
                    .unwrap_or_default()
                    .to_string_lossy()
            ),
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
            imported: None,
        };
        let full = RenderRequest {
            executable: engine.clone(),
            source: stack.directory.clone(),
            output_parent: self.output.clone(),
            exposure_ev: self.controls.exposure,
            pyramid_gate: self.controls.gate,
            worker_threads: Some(self.controls.workers),
            settings: self.controls.settings.clone(),
            retain_master: true,
            recipe: Some(recipe.clone()),
        };
        let (job, route, fallback) = match self.region_only_source(&engine, &recipe) {
            Ok((original, request)) => {
                let fallback = (full, run.clone());
                run.label = run.label.replace("· repaired", "· region repaired");
                run.settings = request.settings.clone();
                run.exposure = request.exposure_ev;
                run.gate = request.pyramid_gate;
                (
                    jobs::start_render_with(request, Some(original)),
                    RepairRoute::Region,
                    Some(fallback),
                )
            }
            Err(why) => (jobs::start_render(full), RepairRoute::Full(why), None),
        };
        self.edit_pane.develop.repair = Some(DepthRepair {
            job,
            progress: PipelineProgress::default(),
            document,
            recipe,
            started: Instant::now(),
            run: Some(run),
            stack: self.active_stack,
            route,
            fallback,
        });
        self.edit_pane.develop.notice = None;
        Ok(())
    }

    /// The open render, when a region-only rebuild can repair it: its
    /// master, photograph, log and warp map, and the request its own
    /// settings make. Otherwise why the whole stack must be re-stacked.
    pub(super) fn region_only_source(
        &self,
        engine: &Path,
        recipe: &DevelopmentRecipe,
    ) -> Result<(jobs::RegionOnlySource, RenderRequest), String> {
        let result = self.result.as_ref().ok_or("no render is open")?;
        let run = self
            .catalog
            .runs
            .iter()
            .find(|run| run.owns_output(result))
            .ok_or("the open render is not in the library")?;
        if run.status != "Saved" {
            return Err(format!("its render is {}", run.status.to_lowercase()));
        }
        if run.settings.session.is_some() || run.settings.temporal_energy {
            return Err("its render is a session or uses temporal smoothing".into());
        }
        let stack = self
            .stack
            .as_ref()
            .ok_or("its source photos are not open")?;
        let master = self
            .editor
            .loaded
            .as_ref()
            .map(|loaded| loaded.source.clone())
            .filter(|master| master != &run.output && master.is_file())
            .ok_or("its render kept no linear master")?;
        if !run.output.is_file() || !run.log.is_file() {
            return Err("its photograph or render log is missing".into());
        }
        // Renders before the shared engine cache kept their alignment in
        // their own folder; later ones find it in the shared cache.
        let warp_map = std::fs::read_dir(run.directory.join("cache"))
            .ok()
            .map(|entries| {
                entries
                    .flatten()
                    .map(|entry| entry.path())
                    .filter(|path| path.to_string_lossy().ends_with(".warpmap.txt"))
                    .collect::<Vec<_>>()
            })
            .filter(|maps| maps.len() == 1)
            .and_then(|mut maps| maps.pop());
        let mut settings = run.settings.clone();
        // A second pass over every frame; the repaired render has none.
        settings.confidence_map = false;
        Ok((
            jobs::RegionOnlySource {
                master,
                photo: run.output.clone(),
                log: run.log.clone(),
                warp_map,
            },
            RenderRequest {
                executable: engine.to_path_buf(),
                source: stack.directory.clone(),
                output_parent: self.output.clone(),
                exposure_ev: run.exposure,
                pyramid_gate: run.gate,
                worker_threads: Some(self.controls.workers),
                settings,
                retain_master: true,
                recipe: Some(recipe.clone()),
            },
        ))
    }

    /// The repair in the activity tray, saying which rebuild runs.
    pub(super) fn report_depth_repair(&self, activities: &mut crate::activity::Activities) {
        let Some(repair) = &self.edit_pane.develop.repair else {
            return;
        };
        let mut status = crate::activity::ActivityStatus::new(
            crate::activity::ActivityKind::Repair,
            "depth-repair",
            match repair.route {
                RepairRoute::Region => "Depth repair · painted area only".to_owned(),
                RepairRoute::Full(_) => "Depth repair · whole stack".to_owned(),
            },
            crate::activity::Lane::Heavy,
        )
        .with_phase(repair.status())
        .with_cancel(crate::activity::CancelMode::Cooperative);
        status.facts = repair.detail();
        if let Some(r) = repair.progress.source_repair {
            status.done = Some(r.completed as u64);
            status.total = Some((r.last + 1 - r.first) as u64);
        }
        activities.report(status);
    }

    pub(super) fn cancel_depth_repair(&mut self) {
        if let Some(repair) = &self.edit_pane.develop.repair {
            repair.job.cancel();
        }
    }

    fn poll_depth_repair(&mut self, ctx: &egui::Context) {
        let mut events = Vec::new();
        if let Some(repair) = &self.edit_pane.develop.repair {
            while events.len() < 256
                && let Ok(event) = repair.job.receiver.try_recv()
            {
                events.push(event);
            }
            ctx.request_repaint_after(Duration::from_millis(250));
        }
        for event in events {
            match event {
                RenderEvent::Started {
                    directory,
                    output,
                    log,
                } => {
                    let Some(repair) = self.edit_pane.develop.repair.as_mut() else {
                        break;
                    };
                    if let Some(mut run) = repair.run.take() {
                        run.directory = directory;
                        run.output = output;
                        run.log = log;
                        match repair.stack {
                            Some(id) => {
                                if self.catalog.add_revision(id, run.clone()).is_err() {
                                    self.catalog.add(run);
                                }
                            }
                            None => self.catalog.add(run),
                        }
                        self.persist_catalog();
                    }
                }
                RenderEvent::Log(text) => {
                    if let Some(repair) = self.edit_pane.develop.repair.as_mut() {
                        repair.progress.ingest(&text);
                    }
                }
                // The repair shows only its progress line. Its per-plane maps
                // are read from the evidence file when the repaired render opens.
                RenderEvent::Evidence(_) => {}
                RenderEvent::Finished(outcome) => {
                    let Some(repair) = self.edit_pane.develop.repair.take() else {
                        break;
                    };
                    match outcome {
                        RenderOutcome::Completed {
                            directory, output, ..
                        } => {
                            self.catalog.finish(&directory, "Saved");
                            self.persist_catalog();
                            self.finish_depth_repair(repair, output);
                        }
                        RenderOutcome::Cancelled { directory } => {
                            self.catalog.finish(&directory, "Cancelled");
                            self.persist_catalog();
                            self.edit_pane.develop.notice = Some(
                                "The depth repair was cancelled; the photograph is unchanged."
                                    .into(),
                            );
                        }
                        RenderOutcome::Failed { directory, message } => {
                            if let Some(path) = &directory {
                                self.catalog.finish(path, "Failed");
                                self.persist_catalog();
                            }
                            // A region-only rebuild that stops falls back to
                            // the whole stack, and says so.
                            if let (RepairRoute::Region, Some((full, run))) =
                                (&repair.route, repair.fallback)
                            {
                                self.edit_pane.develop.notice = Some(format!(
                                    "Rebuilding only the painted area stopped ({message}); \
                                     re-stacking the whole stack instead."
                                ));
                                self.edit_pane.develop.repair = Some(DepthRepair {
                                    job: jobs::start_render(full),
                                    progress: PipelineProgress::default(),
                                    document: repair.document,
                                    recipe: repair.recipe,
                                    started: Instant::now(),
                                    run: Some(run),
                                    stack: repair.stack,
                                    route: RepairRoute::Full(format!(
                                        "the region-only rebuild stopped: {message}"
                                    )),
                                    fallback: None,
                                });
                                break;
                            }
                            self.edit_pane.develop.notice =
                                Some(format!("The depth repair stopped: {message}"));
                        }
                    }
                }
            }
        }
        // Open the repaired render once the editor is idle.
        if let Some(result) = self
            .edit_pane
            .develop
            .repair_ready
            .as_ref()
            .and_then(|task| task.receiver.try_recv().ok())
        {
            self.edit_pane.develop.repair_ready = None;
            match result {
                Ok(output) => {
                    self.result = Some(output.clone());
                    self.open_result(output);
                    self.edit_pane.develop.notice =
                        Some("The depth repair is finished; this is the repaired render.".into());
                }
                Err(error) => self.edit_pane.develop.notice = Some(error),
            }
        }
    }

    /// Carry the live edit to the repaired render, then open it.
    fn finish_depth_repair(&mut self, repair: DepthRepair, output: PathBuf) {
        let current = self.editor.path.as_ref() == Some(&repair.document);
        // Edits made during the re-stack travel with the photograph; repairs
        // painted meanwhile stay pending against the new master.
        let recipe = if current {
            self.editor.commit_edit();
            self.editor.recipe.clone()
        } else {
            repair.recipe
        };
        if !current {
            self.edit_pane.develop.notice = Some(format!(
                "The depth repair is finished: {}",
                output.display()
            ));
            return;
        }
        self.edit_pane.develop.repair_ready =
            Some(jobs::spawn_task("strehl-repair-carry", move |_| {
                let sidecar = crate::edit_workspace::recipe_path(&output);
                if !sidecar.exists() {
                    let bytes = serde_json::to_vec_pretty(&recipe)?;
                    let mut file = std::fs::OpenOptions::new()
                        .write(true)
                        .create_new(true)
                        .open(&sidecar)?;
                    std::io::Write::write_all(&mut file, &bytes)?;
                    file.sync_all()?;
                }
                Ok(output)
            }));
    }

    // ------------------------------------------------------------- export

    fn export_library_path(&self) -> Option<PathBuf> {
        self.catalog.path.as_deref().map(presets::library_path)
    }

    /// Build the Export view for this frame and run `show` with it.
    fn with_export_view<R>(
        &mut self,
        show: impl FnOnce(&ExportView<'_>, &mut ExportPanel) -> R,
    ) -> Option<R> {
        let library = self.export_pane.station.library.clone()?;
        let loaded = self.editor.loaded.as_ref()?;
        let palette = self.edit_pane.develop.palette;
        let (subject_key, subject_name, um_per_px) = self.develop_subject();
        let size = self
            .editor
            .recipe
            .crop
            .map_or([loaded.image.width, loaded.image.height], |c| {
                c.output_size(loaded.image.width, loaded.image.height)
            });
        let view_name = self
            .editor
            .path
            .as_ref()
            .and_then(|p| p.file_stem())
            .map_or_else(|| "photograph".into(), |s| s.to_string_lossy().into_owned());
        let date = date_text();
        let history = self.export_history_rows();
        let destination = library.destination(&subject_key).map(Path::to_path_buf);
        let note = self.repair_export_note();
        let view = ExportView {
            palette: &palette,
            library: &library,
            fields: NameFields {
                subject: &subject_name,
                view: &view_name,
                preset: "",
                date: &date,
            },
            destination: destination.as_deref(),
            size,
            has_scale_bar: self.editor.recipe.scale_bar.is_some_and(|b| b.enabled),
            calibrated: um_per_px.is_some(),
            hdr_photo: loaded.image.origin == strehl_edit::ImageOrigin::SceneLinear,
            history: &history,
            batch: self
                .export_pane
                .station
                .batch
                .as_ref()
                .map(|b| b.progress.snapshot()),
            can_export: self.develop_can_export(),
            note,
            view_bundle: self
                .view_bundle_source()
                .map(|_| self.view_bundle_export.is_some()),
        };
        let panel = &mut self.export_pane.station.panel;
        Some(show(&view, panel))
    }

    pub(super) fn show_export_inspector(&mut self, ui: &mut egui::Ui) {
        self.edit_pane.develop.palette = StudioPalette::of(ui.ctx());
        let intents = self
            .with_export_view(|view, panel| exporting::inspector_body(ui, panel, view))
            .unwrap_or_default();
        self.handle_export_intents(ui.ctx(), intents);
    }

    pub(super) fn show_export_footer(&mut self, ui: &mut egui::Ui) {
        let intents = self
            .with_export_view(|view, _| exporting::inspector_footer(ui, view))
            .unwrap_or_default();
        self.handle_export_intents(ui.ctx(), intents);
    }

    /// The selected preset, for the canvas preview: its settings, if an image.
    pub(super) fn export_preview_settings(&self) -> Option<strehl_edit::ExportSettings> {
        let station = &self.export_pane.station;
        let library = station.library.as_ref()?;
        let preset = station
            .panel
            .selected
            .as_ref()
            .and_then(|id| library.presets.iter().find(|p| &p.id == id))
            .or_else(|| library.ticked().next())?;
        match &preset.output {
            presets::PresetOutput::Image(image) => Some(image.settings.clone()),
            presets::PresetOutput::Archive => None,
        }
    }

    pub(super) fn show_export_strip(&mut self, ui: &mut egui::Ui) {
        let intents = self
            .with_export_view(|view, panel| exporting::control_strip(ui, panel, view))
            .unwrap_or_default();
        self.handle_export_intents(ui.ctx(), intents);
    }

    pub(super) fn show_export_history(&mut self, ui: &mut egui::Ui) {
        let intents = self
            .with_export_view(|view, _| exporting::history_table(ui, view))
            .unwrap_or_default();
        self.handle_export_intents(ui.ctx(), intents);
    }

    fn export_history_rows(&self) -> Vec<HistoryRow> {
        let Some(path) = &self.editor.path else {
            return Vec::new();
        };
        let versions: HashMap<&str, &crate::workspace_history::PhotoVersion> = self
            .catalog
            .photo_versions
            .iter()
            .filter(|v| &v.owner.output == path)
            .map(|v| (v.id.as_str(), v))
            .collect();
        let station = &self.export_pane.station;
        self.catalog
            .photo_exports
            .iter()
            .rev()
            .filter(|e| versions.contains_key(e.version.as_str()))
            .take(64)
            .map(|e| {
                let version = versions[e.version.as_str()];
                let mut status = station
                    .checked
                    .get(&e.id)
                    .copied()
                    .unwrap_or(HistoryStatus::Checking);
                if status == HistoryStatus::Unchanged
                    && station
                        .version_recipes
                        .get(&e.version)
                        .is_some_and(|recipe| recipe != &self.editor.recipe)
                {
                    status = HistoryStatus::Older;
                }
                HistoryRow {
                    id: e.id.clone(),
                    path: e.path.clone(),
                    preset: format!(
                        "{} {}",
                        match e.settings.format {
                            strehl_edit::ExportFormat::Avif => "AVIF",
                            strehl_edit::ExportFormat::Tiff => "TIFF",
                            strehl_edit::ExportFormat::Png => "PNG",
                            strehl_edit::ExportFormat::Jpeg => "JPEG",
                        },
                        e.settings.color_space.label()
                    ),
                    size: exporting::human_bytes(e.bytes),
                    version: version.name.clone(),
                    when: when_text(e.created),
                    status,
                }
            })
            .collect()
    }

    fn poll_export_station(&mut self, ctx: &egui::Context) {
        let station = &mut self.export_pane.station;
        // The library is read and written on workers only.
        if station.library.is_none()
            && station.loading.is_none()
            && let Some(path) = self.catalog.path.as_deref().map(presets::library_path)
        {
            station.loading = Some(jobs::spawn_task("strehl-export-presets-load", move |_| {
                presets::load(&path)
            }));
        }
        if let Some(result) = station
            .loading
            .as_ref()
            .and_then(|t| t.receiver.try_recv().ok())
        {
            station.loading = None;
            match result {
                Ok(loaded) => {
                    station.library = Some(loaded.library);
                    station.library_bytes = loaded.bytes;
                }
                Err(error) => station.error = Some(error),
            }
        }
        if let Some(result) = station
            .saving
            .as_ref()
            .and_then(|t| t.receiver.try_recv().ok())
        {
            station.saving = None;
            match result {
                Ok(bytes) => station.library_bytes = Some(bytes),
                Err(error) => station.error = Some(error),
            }
        }
        if station.save_again && station.saving.is_none() {
            station.save_again = false;
            self.save_export_library();
        }
        let station = &mut self.export_pane.station;
        if let Some(result) = station
            .folder
            .as_ref()
            .and_then(|t| t.receiver.try_recv().ok())
        {
            station.folder = None;
            if let Ok(Some(folder)) = result {
                let (key, _, _) = self.develop_subject();
                if let Some(library) = self.export_pane.station.library.as_mut() {
                    match library.remember_destination(&key, &folder) {
                        Ok(()) => self.save_export_library(),
                        Err(error) => self.export_pane.station.error = Some(error.to_string()),
                    }
                }
            }
        }
        self.poll_export_batch(ctx);
        self.poll_history_checks();
    }

    fn save_export_library(&mut self) {
        let station = &mut self.export_pane.station;
        if station.saving.is_some() {
            station.save_again = true;
            return;
        }
        let (Some(library), Some(path)) = (
            station.library.clone(),
            self.catalog.path.as_deref().map(presets::library_path),
        ) else {
            return;
        };
        let expected = station.library_bytes.clone();
        station.saving = Some(jobs::spawn_task("strehl-export-presets-save", move |_| {
            presets::save(&path, &library, expected.as_deref())
        }));
    }

    fn poll_history_checks(&mut self) {
        let rows: Vec<crate::workspace_history::PhotoExport> = {
            let Some(path) = &self.editor.path else {
                return;
            };
            let versions: Vec<&str> = self
                .catalog
                .photo_versions
                .iter()
                .filter(|v| &v.owner.output == path)
                .map(|v| v.id.as_str())
                .collect();
            self.catalog
                .photo_exports
                .iter()
                .filter(|e| versions.contains(&e.version.as_str()))
                .cloned()
                .collect()
        };
        let station = &mut self.export_pane.station;
        if let Some(result) = station
            .checking
            .as_ref()
            .and_then(|t| t.receiver.try_recv().ok())
        {
            station.checking = None;
            if let Ok(checked) = result {
                for (id, status, recipe) in checked {
                    station.checked.insert(id, status);
                    if let Some((version, recipe)) = recipe {
                        station.version_recipes.insert(version, recipe);
                    }
                }
            }
        }
        let unchecked: Vec<_> = rows
            .into_iter()
            .filter(|e| !station.checked.contains_key(&e.id))
            .collect();
        if unchecked.is_empty() || station.checking.is_some() {
            return;
        }
        let root = self.catalog.history_root();
        let versions: Vec<crate::workspace_history::PhotoVersion> = self
            .catalog
            .photo_versions
            .iter()
            .filter(|v| unchecked.iter().any(|e| e.version == v.id))
            .cloned()
            .collect();
        let station = &mut self.export_pane.station;
        station.checking = Some(jobs::spawn_task(
            "strehl-export-history-check",
            move |cancelled| {
                Ok(unchecked
                    .into_iter()
                    .map(|record| {
                        let status = if !record.path.exists() {
                            HistoryStatus::Missing
                        } else if crate::workspace_history::photographs::verify_export(
                            &record, &cancelled,
                        )
                        .is_ok()
                        {
                            HistoryStatus::Unchanged
                        } else {
                            HistoryStatus::Changed
                        };
                        let recipe = root.as_ref().and_then(|root| {
                            let version = versions.iter().find(|v| v.id == record.version)?;
                            crate::workspace_history::photographs::read_preview_recipe(
                                root, version,
                            )
                            .ok()
                            .map(|r| (version.id.clone(), r))
                        });
                        (record.id, status, recipe)
                    })
                    .collect())
            },
        ));
    }

    pub(super) fn handle_export_intents(
        &mut self,
        ctx: &egui::Context,
        intents: Vec<ExportIntent>,
    ) {
        for intent in intents {
            if let Err(error) = self.handle_export_intent(ctx, intent) {
                self.export_pane.station.error = Some(error.to_string());
            }
        }
    }

    fn handle_export_intent(
        &mut self,
        ctx: &egui::Context,
        intent: ExportIntent,
    ) -> anyhow::Result<()> {
        let mut changed = false;
        {
            let library = self
                .export_pane
                .station
                .library
                .as_mut()
                .ok_or_else(|| anyhow::anyhow!("The export presets are still loading"))?;
            match &intent {
                ExportIntent::Tick(id, on) => {
                    library.set_enabled(id, *on)?;
                    changed = true;
                }
                ExportIntent::Edit(id, output) => {
                    library.update(id, output.clone())?;
                    changed = true;
                }
                ExportIntent::NewPreset => {
                    let mut n = library.presets.len() + 1;
                    let name = loop {
                        let name = format!("Preset {n}");
                        if !library
                            .presets
                            .iter()
                            .any(|p| p.name.eq_ignore_ascii_case(&name))
                        {
                            break name;
                        }
                        n += 1;
                    };
                    let id = library.add(&name, presets::default_presets()[0].output.clone())?;
                    self.export_pane.station.panel.selected = Some(id);
                    changed = true;
                }
                ExportIntent::SetTemplate(template) => {
                    library.set_template(template)?;
                    changed = true;
                }
                _ => {}
            }
        }
        if changed {
            self.save_export_library();
            return Ok(());
        }
        match intent {
            ExportIntent::ChangeDestination => {
                anyhow::ensure!(
                    self.export_pane.station.folder.is_none(),
                    "A folder dialog is already open"
                );
                self.export_pane.station.folder =
                    Some(jobs::spawn_task("strehl-export-folder", |_| {
                        Ok(rfd::FileDialog::new()
                            .set_title("Export folder for this subject")
                            .pick_folder())
                    }));
            }
            ExportIntent::OpenFolder => {
                let (key, _, _) = self.develop_subject();
                if let Some(folder) = self
                    .export_pane
                    .station
                    .library
                    .as_ref()
                    .and_then(|l| l.destination(&key))
                    .map(Path::to_path_buf)
                {
                    jobs::spawn_task("strehl-open-export-folder", move |_| {
                        crate::reveal_path::reveal(&folder)?;
                        Ok(())
                    });
                }
            }
            ExportIntent::Reveal(path) => {
                jobs::spawn_task("strehl-reveal-export", move |_| {
                    crate::reveal_path::reveal(&path)?;
                    Ok(())
                });
            }
            ExportIntent::CopyPath(path) => ctx.copy_text(path.display().to_string()),
            ExportIntent::ExportTicked => self.start_export_batch(None)?,
            ExportIntent::ExportAgain(id) => self.start_export_batch(Some(id))?,
            ExportIntent::ExportViewBundle => {
                if !self.picker_active() && self.view_bundle_export.is_none() {
                    self.pick(Dialog::ViewBundleExport);
                }
            }
            ExportIntent::CancelViewBundle => {
                if let Some(task) = &self.view_bundle_export {
                    task.cancel();
                }
            }
            ExportIntent::CancelBatch => {
                if let Some(batch) = &self.export_pane.station.batch {
                    batch
                        .progress
                        .cancelled
                        .store(true, std::sync::atomic::Ordering::Relaxed);
                }
            }
            _ => {}
        }
        Ok(())
    }

    /// Start the ticked presets (or one recorded export again) as one job.
    pub(super) fn start_export_batch(&mut self, again: Option<String>) -> anyhow::Result<()> {
        anyhow::ensure!(
            self.export_pane.station.batch.is_none(),
            "An export batch is already running"
        );
        anyhow::ensure!(
            self.develop_can_export(),
            "Wait for the current photograph operation to finish"
        );
        let library = self
            .export_pane
            .station
            .library
            .clone()
            .ok_or_else(|| anyhow::anyhow!("The export presets are still loading"))?;
        let (key, subject, um_per_px) = self.develop_subject();
        let folder = library
            .destination(&key)
            .map(Path::to_path_buf)
            .ok_or_else(|| anyhow::anyhow!("Choose where this subject's files go"))?;
        jobs::validate_export_destination(
            self.stack.as_ref().map(|s| s.directory.as_path()),
            &folder,
        )?;
        let library = match &again {
            None => library,
            Some(id) => {
                let record = self
                    .catalog
                    .photo_exports
                    .iter()
                    .find(|e| &e.id == id)
                    .cloned()
                    .ok_or_else(|| anyhow::anyhow!("This export is no longer listed"))?;
                let mut settings = record.settings.clone();
                settings.metadata = Default::default();
                let mut one = library.clone();
                one.presets.clear();
                let stem = record
                    .path
                    .file_stem()
                    .unwrap_or_default()
                    .to_string_lossy()
                    .into_owned();
                one.template = "{preset}".into();
                one.add(
                    &presets::sanitize_stem(&stem),
                    presets::PresetOutput::Image(presets::ImagePreset {
                        settings,
                        copyright: false,
                        description: false,
                    }),
                )?;
                one
            }
        };
        self.editor.commit_edit();
        let job = self
            .editor
            .freeze_export_job()
            .ok_or_else(|| anyhow::anyhow!("Open a completed photograph first"))?;
        let guard_path = self
            .editor
            .path
            .clone()
            .ok_or_else(|| anyhow::anyhow!("Open a photograph first"))?;
        let loaded = self
            .editor
            .loaded
            .as_ref()
            .ok_or_else(|| anyhow::anyhow!("Open a photograph first"))?;
        let image = loaded.image.clone();
        let source = loaded.source.clone();
        let recipe = job.recipe().clone();
        let recipe_json = serde_json::to_vec_pretty(&recipe)?;
        let root = self.catalog.history_root();
        let owner = self.catalog.photo_owner(&guard_path);
        let view = guard_path
            .file_stem()
            .map_or_else(|| "photograph".into(), |s| s.to_string_lossy().into_owned());
        let date = date_text();
        let text = BatchText::default();
        let planned = exporting::plan_batch(
            &library,
            &NameFields {
                subject: &subject,
                view: &view,
                preset: "",
                date: &date,
            },
            &folder,
            &source,
            &text,
            |p| p.exists(),
        )?;
        let progress = BatchProgress::new(&planned);
        let worker_progress = progress.clone();
        let now = {
            let seconds = std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .map_or(0, |d| d.as_secs() as i64);
            let offset = chrono::Local::now().offset().local_minus_utc() / 60;
            strehl_edit::ExportDateTime::from_unix_seconds(seconds, offset as i16)
        };
        let task = jobs::spawn_task("strehl-export-batch", move |cancelled| {
            let version = match root {
                Some(root) => Some(crate::workspace_history::photographs::save_version(
                    &root,
                    owner,
                    "Export batch",
                    recipe,
                    &image,
                    &source,
                    &cancelled,
                )?),
                None => None,
            };
            let context = BatchContext {
                job,
                recipe_json,
                um_per_px,
                date: Some(now),
                version: version.clone(),
            };
            Ok((
                version,
                exporting::run_batch(planned, &context, &worker_progress),
            ))
        });
        self.export_pane.station.batch = Some(RunningBatch { progress, task });
        Ok(())
    }

    fn poll_export_batch(&mut self, ctx: &egui::Context) {
        let Some(batch) = &self.export_pane.station.batch else {
            return;
        };
        ctx.request_repaint_after(Duration::from_millis(100));
        let Ok(result) = batch.task.receiver.try_recv() else {
            return;
        };
        self.export_pane.station.batch = None;
        match result {
            Ok((version, done)) => {
                let result = (|| -> anyhow::Result<()> {
                    if let Some(version) = version {
                        self.catalog.add_photo_version(version)?;
                    }
                    for (_, record) in &done.written {
                        if let Some(record) = record {
                            self.catalog.add_photo_export(record.clone())?;
                        }
                    }
                    self.catalog.save()
                })();
                let written = done.written.len();
                self.export_pane.station.error = match (result, done.failed.first()) {
                    (Err(error), _) => Some(format!("Recording the exports: {error}")),
                    (Ok(()), Some((path, error))) => {
                        Some(format!("{} failed: {error}", path.display()))
                    }
                    (Ok(()), None) if done.cancelled => {
                        Some(format!("Cancelled after {written} file(s)"))
                    }
                    _ => None,
                };
            }
            Err(error) => self.export_pane.station.error = Some(error),
        }
    }
}

#[cfg(test)]
#[path = "app-develop-tests.rs"]
mod tests;
