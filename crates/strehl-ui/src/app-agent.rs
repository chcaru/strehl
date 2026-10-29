//! Human and agent actions share the same workspace and undo journal.
use super::*;
#[path = "app-agent-metadata.rs"]
mod metadata;
use crate::agent_interface::{
    AgentBridge, AgentCommand, AgentImage, AgentReply, IncomingRequest, PreviewTarget, Region,
};
use serde_json::{Value, json};
use std::{
    collections::BTreeMap,
    hash::{Hash, Hasher},
    sync::Arc,
};

#[derive(Default)]
pub(super) struct AgentState {
    bridge: Option<AgentBridge>,
    pub(super) starting: Option<Task<AgentBridge>>,
    pending: Vec<(IncomingRequest, Task<AgentReply>)>,
    pub revision: u64,
    fingerprint: Option<u64>,
    pub grants: BTreeMap<String, PathBuf>,
    next_grant: u64,
    grant_dialog: Option<Task<Option<PathBuf>>>,
    events: VecDeque<String>,
    suggestions: Vec<(String, String, Option<Region>)>,
    error: Option<String>,
}

impl AgentState {
    pub(super) fn add_launch_grant(&mut self, path: PathBuf) {
        self.next_grant = self.next_grant.saturating_add(1);
        self.grants
            .insert(format!("folder-{}", self.next_grant), path);
    }
}

impl StrehlApp {
    pub(super) fn agent_start_error(&self) -> Option<&str> {
        self.agent.error.as_deref()
    }
    pub(super) fn agent_read_pending(&self) -> bool {
        !self.agent.pending.is_empty()
    }
    pub(super) fn close_agent_session(&mut self) {
        self.agent.bridge = None;
    }

    pub(super) fn start_agent_session(&mut self) {
        if self.agent.bridge.is_some() || self.agent.starting.is_some() {
            return;
        }
        let state_path = if self.headless {
            self.catalog.path.clone()
        } else {
            crate::workspace_history::default_path()
        };
        let parent = state_path
            .and_then(|p| p.parent().map(Path::to_path_buf))
            .unwrap_or_else(std::env::temp_dir)
            .join("agent-sessions");
        self.agent.starting = Some(jobs::spawn_task("strehl-agent-start", move |_| {
            AgentBridge::start(&parent)
        }));
    }

    fn sync_agent_revision(&mut self) {
        let state = json!({
            "epoch":self.epoch, "stack":self.active_stack, "selected":self.selected, "output":self.result,
            "settings":self.controls.settings, "exposure":self.controls.exposure,"gate":self.controls.gate,
            "workers":self.controls.workers, "edits":self.editor.revision,"before_preview":self.editor.before,
            "selected_region":self.editor.selected,
            "export_directory":self.export_destination_for_current(),
            "view":self.process_space.history_revision(), "projects":self.project_explorer.history_revision(),
            "running":self.job.is_some(), "opening":self.scan.is_some() || self.replay.is_some() || self.session_import.is_some()
        });
        let mut hash = std::collections::hash_map::DefaultHasher::new();
        state.to_string().hash(&mut hash);
        let fingerprint = hash.finish();
        if self.agent.fingerprint != Some(fingerprint) {
            self.agent.fingerprint = Some(fingerprint);
            self.agent.revision = self.agent.revision.wrapping_add(1);
        }
    }

    pub(super) fn poll_agent(&mut self, ctx: &egui::Context) {
        if let Some(result) = self
            .agent
            .starting
            .as_ref()
            .and_then(|task| task.receiver.try_recv().ok())
        {
            self.agent.starting = None;
            match result {
                Ok(bridge) => self.agent.bridge = Some(bridge),
                Err(error) => self.agent.error = Some(error),
            }
        }
        if let Some(path) = self.agent_session_out.as_ref()
            && let Some(bridge) = self.agent.bridge.as_ref()
        {
            match super::headless::publish_session(path, bridge.descriptor_path()) {
                Ok(()) => self.agent_session_out = None,
                Err(error) => {
                    self.agent.error = Some(format!("Publish agent session: {error:#}"));
                    self.agent.bridge = None;
                }
            }
        }
        if let Some(result) = self
            .agent
            .grant_dialog
            .as_ref()
            .and_then(|task| task.receiver.try_recv().ok())
        {
            self.agent.grant_dialog = None;
            match result {
                Ok(Some(path)) => {
                    self.agent.next_grant = self.agent.next_grant.saturating_add(1);
                    let id = format!("folder-{}", self.agent.next_grant);
                    self.agent.grants.insert(id, path);
                    self.agent.revision = self.agent.revision.wrapping_add(1);
                }
                Ok(None) => {}
                Err(error) => self.agent.error = Some(error),
            }
        }
        let mut index = 0;
        while index < self.agent.pending.len() {
            if let Ok(result) = self.agent.pending[index].1.receiver.try_recv() {
                let (request, _) = self.agent.pending.remove(index);
                request.reply(result.unwrap_or_else(AgentReply::error));
            } else if self.agent.pending[index].0.is_expired() {
                let (request, task) = self.agent.pending.remove(index);
                task.cancel();
                request.reply(AgentReply::error(
                    "The diagnostic request expired; try a smaller region.",
                ));
            } else {
                index += 1;
            }
        }
        if self.agent.bridge.is_some()
            && let Some(path) = self
                .result
                .as_ref()
                .filter(|path| Some(*path) == self.image_path.as_ref())
        {
            self.editor.open(path.clone());
        }
        self.sync_agent_revision();
        for _ in 0..4 {
            let Some(incoming) = self.agent.bridge.as_ref().and_then(AgentBridge::try_next) else {
                break;
            };
            if let Err(error) = incoming.request.check_revision(self.agent.revision) {
                incoming.reply(AgentReply::error(error));
                continue;
            }
            if self.picker_active()
                && !incoming.request.command.is_read_only()
                && !(self.session_import.is_some()
                    && matches!(incoming.request.command, AgentCommand::CancelStack {}))
                && !(self.view_bundle_export.is_some()
                    && matches!(
                        incoming.request.command,
                        AgentCommand::CancelViewBundleExport {}
                    ))
            {
                incoming.reply(AgentReply::error(
                    "A file selection or completed-session import is active. Read state and retry when it finishes.",
                ));
                continue;
            }
            if self.headless_shutdown {
                incoming.reply(AgentReply::error("The headless session is shutting down"));
                continue;
            }
            let command = incoming.request.command.clone();
            if matches!(
                command,
                AgentCommand::Probe { .. }
                    | AgentCommand::Preview { .. }
                    | AgentCommand::Metadata { .. }
            ) {
                if self.agent.pending.len() >= 2 {
                    incoming.reply(AgentReply::error(
                        "Two diagnostic reads are already running.",
                    ));
                } else {
                    match self.agent_read_task(command) {
                        Ok(task) => self.agent.pending.push((incoming, task)),
                        Err(error) => incoming.reply(AgentReply::error(error.to_string())),
                    }
                }
                continue;
            }
            let mutation = !command.is_read_only();
            let description = format!("{command:?}");
            let result = if matches!(command, AgentCommand::Shutdown {}) {
                self.prepare_headless_shutdown(ctx)
            } else {
                self.apply_agent_command(command)
            };
            match result {
                Ok(data) => {
                    if mutation {
                        self.agent.revision = self.agent.revision.wrapping_add(1);
                        self.agent
                            .events
                            .push_front(description.chars().take(220).collect());
                        self.agent.events.truncate(64);
                        self.editor.commit_edit();
                        self.observe_edits(ctx);
                    }
                    self.sync_agent_revision();
                    incoming.reply(AgentReply::success(
                        json!({"revision":self.agent.revision,"result":data}),
                    ));
                }
                Err(error) => incoming.reply(AgentReply::error(error.to_string())),
            }
        }
        if self.agent.bridge.is_some()
            || self.agent.starting.is_some()
            || self.agent.grant_dialog.is_some()
        {
            ctx.request_repaint_after(Duration::from_millis(50));
        }
    }

    pub(super) fn agent_panel(&mut self, ui: &mut egui::Ui) {
        ui.label(
            RichText::new("LOCAL COLLABORATION")
                .monospace()
                .size(9.0)
                .color(ACCENT),
        );
        theme::caption(
            ui,
            "Use Codex, Claude Code, Copilot CLI, or another MCP host with its own login. Strehl does not receive your model credentials.",
        );
        if self.agent.bridge.is_some() {
            ui.horizontal(|ui| {
                ui.colored_label(GREEN, "Agent access enabled");
                if ui.button("Disconnect").clicked() {
                    self.agent.bridge = None;
                    for (request, task) in self.agent.pending.drain(..) {
                        task.cancel();
                        request.reply(AgentReply::error("The human disconnected this workspace."));
                    }
                    self.agent.grants.clear();
                }
            });
            if let Some(bridge) = &self.agent.bridge {
                let executable =
                    std::env::current_exe().unwrap_or_else(|_| PathBuf::from("Strehl.exe"));
                let config = json!({"mcpServers":{"strehl":{"command":executable,"args":["--mcp","--session",bridge.descriptor_path()]}}});
                if ui.button("Copy MCP configuration").clicked() {
                    ui.ctx()
                        .copy_text(serde_json::to_string_pretty(&config).unwrap());
                }
                theme::caption(
                    ui,
                    "This session gives the host access to the current photo, diagnostics, recipes, and project actions. Disconnect revokes access.",
                );
                if ui.button("Copy session path").clicked() {
                    ui.ctx()
                        .copy_text(bridge.descriptor_path().display().to_string());
                }
            }
        } else if ui
            .add_enabled(
                self.agent.starting.is_none(),
                egui::Button::new("Enable agent access"),
            )
            .clicked()
        {
            self.start_agent_session();
        }
        ui.separator();
        theme::caption(
            ui,
            "Circle an issue in Edit and write a note. Your agent can inspect that region, compare captures, suggest changes, and make reversible edits here.",
        );
        if ui.button("Circle an issue").clicked() {
            self.sidebar = Some(workspace::Sidebar::Edit);
            self.editor.tool = crate::edit_workspace::DrawingTool::Ellipse;
            if let Some(path) = &self.result {
                self.editor.open(path.clone());
            }
        }
        ui.add_enabled_ui(self.agent.bridge.is_some(), |ui| {
            if ui.button("Share a folder…").clicked() && self.agent.grant_dialog.is_none() {
                self.agent.grant_dialog = Some(jobs::spawn_task("strehl-agent-share", |_| {
                    Ok(rfd::FileDialog::new()
                        .set_title("Share this folder with the connected agent")
                        .pick_folder())
                }));
            }
        });
        let mut revoke = None;
        for (id, path) in &self.agent.grants {
            ui.horizontal(|ui| {
                ui.label(format!(
                    "{id}: {}",
                    path.file_name().unwrap_or_default().to_string_lossy()
                ));
                if ui.small_button("Revoke").clicked() {
                    revoke = Some(id.clone());
                }
            });
        }
        if let Some(id) = revoke {
            self.agent.grants.remove(&id);
            self.agent.revision = self.agent.revision.wrapping_add(1);
        }
        ui.separator();
        for (title, rationale, region) in &self.agent.suggestions {
            ui.label(RichText::new(title).color(INK));
            ui.label(rationale);
            if let Some(region) = region
                && ui.button("Locate in photograph").clicked()
            {
                let bounds = crate::edit_workspace::shape_bounds(region);
                self.process_space.set_photo_view(
                    [
                        (bounds[0][0] + bounds[1][0]) * 0.5,
                        (bounds[0][1] + bounds[1][1]) * 0.5,
                    ],
                    2.0,
                );
            }
            ui.separator();
        }
        egui::CollapsingHeader::new("Changes made by agent").show(ui, |ui| {
            for event in &self.agent.events {
                ui.label(RichText::new(event).size(10.0).color(MUTED));
            }
        });
        if let Some(error) = &self.agent.error {
            ui.colored_label(AMBER, error);
        }
    }

    fn agent_snapshot(&self) -> Value {
        let projects: Vec<_> = self.catalog.nodes.iter().take(256).map(|node| json!({
            "id":node.id,"parent":node.parent,"name":node.name,"kind":node.kind,
            "revisions":node.revisions.iter().enumerate().rev().take(32).map(|(i,path)| json!({"index":i,"name":path.file_name()})).collect::<Vec<_>>(),
            "revision_count":node.revisions.len()
        })).collect();
        let export_capabilities = json!({"formats":["avif","tiff","png","jpeg"],"color_spaces":["srgb","display_p3","rec2020"],
                "destination":self.export_destination_for_current(),
                "view_bundle":{"available":self.view_bundle_source().is_some(),"busy":self.view_bundle_export.is_some(),"last_export":self.last_view_bundle_export,"scope":"Complete bound artifacts; no original RAWs or developed edit versions"},
                "defaults":strehl_edit::ExportSettings::default(),
                "transparent_coverage":self.editor.loaded.as_ref().is_some_and(|p|p.coverage.is_some()),
                "coverage_preserving_formats":["tiff","png"],
                "hdr_available":self.editor.loaded.as_ref().is_some_and(|p|self.agent_photo_is_current() && p.image.origin==strehl_edit::ImageOrigin::SceneLinear)});
        let diagnostics = json!({"admission_packets":self.progress.admission_archive.len(),
                "omitted_packets":self.progress.admission_archive.dropped(),
                "confidence":self.progress.confidence.as_ref().map(|p|json!({"compared":p.compared,"total":p.total,
                    "meaning":"folded aligned-observation rank: 0 one-sided, 1000 balanced; ties can also read 0; neither end is a quality grade"})),
                "alignment":self.progress.alignment,"placed":self.progress.placed,"refused":self.progress.refused,
                "noise_model":self.progress.noise_model,"geometry_error":self.progress.alignment_error});
        let session = self.controls.settings.session.as_ref().map(|session|json!({"mode":session.manifest.mode,"primary_pass":session.manifest.primary_pass,"memory_limit_gib":session.memory_limit_gib,"precision_weights":session.precision_weights,"contribution_maps":session.contribution_maps,"focus_evidence":session.focus_evidence,"reproducibility":session.reproducibility,"original_cfa_reconstruction":session.original_cfa_reconstruction,"capture_groups":self.session_ui.groups,"layers":self.session_ui.layers,"selected_output":self.result,"selection_busy":self.session_output_selection.is_some(),"primary_scope":if session.manifest.mode == crate::session_workspace::SessionMode::IndependentViews {"Independent view coordinates and focus; no primary or cross-view geometry."} else if session.manifest.mode == crate::session_workspace::SessionMode::Mosaic {"No primary preference; framing follows measured overlap and coverage."} else if session.manifest.mode == crate::session_workspace::SessionMode::Layers {"Common reference frame and first displayed layer; each layer retains its own appearance."} else {"Framing, appearance and disagreement fallback; automatic reference has no fusion preference."}}));
        let mut snapshot = json!({
            "revision":self.agent.revision, "application":"Strehl", "version":env!("CARGO_PKG_VERSION"),
            "headless":self.headless,"output_directory":self.output,
            "active_stack":self.active_stack, "projects":projects, "project_list_truncated":self.catalog.nodes.len()>256,
            "source_count":self.stack.as_ref().map(|s|s.frames.len()), "selected_frame":self.selected,
            "frame_index_base":0, "status":self.status, "stage":format!("{:?}",self.progress.stage),
            "busy":{"stack":self.job.is_some(),"opening":self.scan.is_some()||self.replay.is_some()||self.session_import.is_some(),
                "photo":self.editor.loading.is_some(),"preset":self.editor.preset.is_some()||self.presets_busy(),"export":self.editor.exporting.is_some() || self.photo_history_busy()},
            "stack_blocker":self.stack_start_blocker(), "settings":self.controls.settings,
            "session":session,
            "exposure_ev":self.controls.exposure,"pyramid_gate":self.controls.gate,"workers":self.controls.workers,
            "photo_history":self.photo_history_snapshot(), "development":self.editor.recipe,"before_preview":self.editor.before, "photo_ready":self.agent_photo_is_current(),
            "selected_region":self.editor.selected,
            "adaptive":self.adaptive_snapshot(),
            "display":self.editor.display_stats(),
            "frame_performance":self.frame_performance.snapshot(),
            "photo_view":agent_photo_view(self.process_view, self.process_space.edit_mapping()),
            "photo":self.editor.loaded.as_ref().filter(|_|self.agent_photo_is_current()).map(|p|json!({"width":p.image.width,"height":p.image.height,"origin":p.image.origin,"source":p.source})),
            "export":self.editor.last_export,"error":self.editor.error.as_ref().or(self.error.as_ref()),
            "export_capabilities":export_capabilities,
            "grants":self.agent.grants.iter().map(|(id,p)|json!({"id":id,"name":p.file_name()})).collect::<Vec<_>>(),
            "diagnostics":diagnostics,
            "saved_diagnostics":self.process_space.diagnostic_snapshot(),
            "semantics":"Camera previews are unregistered. Admission is sampled gate evidence, not fractional ownership. Annotations use final-photo normalized coordinates. Exports and new runs preserve originals."
        });
        snapshot["view_progress"] =
            serde_json::to_value(self.progress.view.as_ref()).expect("Serializable view progress");
        snapshot["view_progress_observations_missing"] =
            json!(self.progress.view_observations_missing);
        snapshot["progress_source_identity"] = json!({"local_frame":self.progress.processing_frame,
            "parent_frame":self.progress.processing_frame.and_then(|i|self.progress.parent_frame(i)),
            "scope":"Child-local diagnostics map to parent original captures through view_progress"});
        snapshot["imported_session"] = serde_json::to_value(self.expected_run.as_ref().and_then(|r|r.imported.as_ref()).map(|p|json!({"scope":p.scope(),"renderer_bound":p.renderer_bound,"imported_at":p.imported_at,"diagnostic_warnings":p.diagnostic_warnings}))).expect("Serializable import provenance");
        snapshot
    }

    fn apply_agent_command(&mut self, command: AgentCommand) -> anyhow::Result<Value> {
        use AgentCommand::*;
        command.validate().map_err(anyhow::Error::msg)?;
        match command {
            Snapshot {} => return Ok(self.agent_snapshot()),
            Shutdown {} => {
                anyhow::bail!("Shutdown must run through the application command pump");
            }
            SelectStack { id } => {
                anyhow::ensure!(
                    self.job.is_none() && self.scan.is_none() && self.replay.is_none(),
                    "Wait for the active operation"
                );
                anyhow::ensure!(
                    self.catalog
                        .node(id)
                        .is_some_and(|node| node.stack.is_some()),
                    "Unknown stack"
                );
                self.open_project_stack(id);
            }
            SelectRun {
                stack_id,
                run_index,
            } => {
                anyhow::ensure!(
                    self.job.is_none() && self.scan.is_none() && self.replay.is_none(),
                    "Wait for the active operation"
                );
                let path = self
                    .catalog
                    .node(stack_id)
                    .and_then(|node| node.revisions.get(run_index))
                    .ok_or_else(|| anyhow::anyhow!("Unknown revision"))?;
                let run = self
                    .catalog
                    .runs
                    .iter()
                    .find(|run| &run.directory == path)
                    .ok_or_else(|| anyhow::anyhow!("Saved run is unavailable"))?
                    .clone();
                self.reopen_run(run);
            }
            SelectSessionOutput { index } => {
                self.select_session_output(index)?;
                return Ok(
                    json!({"state":"queued","operation":"select_session_output","index":index}),
                );
            }
            SelectSource { frame } => {
                anyhow::ensure!(
                    self.stack
                        .as_ref()
                        .is_some_and(|stack| frame < stack.frames.len()),
                    "Source frame out of range"
                );
                self.inspect_frame(frame);
                self.process_view = true;
            }
            SetSettings { patch } => self.agent_settings(patch)?,
            AdaptiveDevelop { strength, intent } => {
                match intent {
                    crate::agent_interface::AdaptiveDevelopIntent::Balance => {
                        self.start_adaptive(strength)?
                    }
                    crate::agent_interface::AdaptiveDevelopIntent::Highlights => {
                        self.start_highlight_restore(strength)?
                    }
                }
                let state = if self.adaptive_snapshot()["analyzing"] == true {
                    "queued"
                } else {
                    "applied"
                };
                return Ok(
                    json!({"state":state,"operation":"adaptive_develop", "intent":intent,
                    "selected_region":self.editor.selected}),
                );
            }
            SetDevelop { mut recipe } => {
                anyhow::ensure!(
                    self.agent_photo_is_current(),
                    "The current photograph is still loading"
                );
                // Older clients do not know about measured spatial fields. An
                // absent/empty list must not silently flatten the photograph.
                // ClearAdaptive is the explicit, scoped removal operation.
                if recipe.spatial.is_empty() {
                    recipe.spatial.clone_from(&self.editor.recipe.spatial);
                    anyhow::ensure!(
                        recipe.spatial.iter().all(|field| field
                            .target_region
                            .as_ref()
                            .is_none_or(|id| recipe.regions.iter().any(|region| &region.id == id))),
                        "This replacement removes a region with an Adaptive treatment. Use remove_annotation or clear_adaptive explicitly first"
                    );
                }
                self.editor.replace(recipe)?;
            }
            SetAdjustments {
                adjustments,
                region_id,
            } => {
                anyhow::ensure!(
                    self.agent_photo_is_current(),
                    "The current photograph is still loading"
                );
                let mut recipe = self.editor.recipe.clone();
                if let Some(id) = region_id {
                    let region = recipe
                        .regions
                        .iter_mut()
                        .find(|region| region.id == id)
                        .ok_or_else(|| anyhow::anyhow!("Unknown region"))?;
                    anyhow::ensure!(region.enabled, "Enable the region before adjusting it");
                    region.adjustments = adjustments;
                } else {
                    recipe.global = adjustments;
                }
                self.editor.replace(recipe)?;
            }
            ClearAdaptive { region_id } => {
                anyhow::ensure!(
                    self.agent_photo_is_current(),
                    "The current photograph is still loading"
                );
                if let Some(id) = &region_id {
                    anyhow::ensure!(
                        self.editor
                            .recipe
                            .regions
                            .iter()
                            .any(|region| &region.id == id),
                        "Unknown region"
                    );
                }
                let mut recipe = self.editor.recipe.clone();
                recipe.clear_adaptive_scope(region_id.as_deref());
                self.editor.replace(recipe)?;
            }
            Annotate { annotation } => {
                anyhow::ensure!(
                    self.agent_photo_is_current(),
                    "Open a completed photograph first"
                );
                let mut recipe = self.editor.recipe.clone();
                if let Some(region) = recipe
                    .regions
                    .iter_mut()
                    .find(|region| region.id == annotation.id)
                {
                    region.name = annotation.label;
                    region.note = format!("{:?}: {}", annotation.kind, annotation.note);
                    region.shape = annotation.region;
                } else {
                    recipe.regions.push(strehl_edit::RegionAdjustment {
                        id: annotation.id.clone(),
                        name: annotation.label,
                        note: format!("{:?}: {}", annotation.kind, annotation.note),
                        shape: annotation.region,
                        feather: 0.4,
                        enabled: true,
                        adjustments: Default::default(),
                        source_range: None,
                    });
                }
                self.editor.replace(recipe)?;
                self.editor.selected = Some(annotation.id);
                self.editor.show_regions = true;
            }
            RemoveAnnotation { id } => {
                anyhow::ensure!(
                    self.agent_photo_is_current(),
                    "Open a completed photograph first"
                );
                let mut recipe = self.editor.recipe.clone();
                anyhow::ensure!(recipe.regions.iter().any(|r| r.id == id), "Unknown region");
                recipe.regions.retain(|r| r.id != id);
                recipe.clear_adaptive_scope(Some(&id));
                self.editor.replace(recipe)?;
            }
            InspectSessionDiagnostic {
                map,
                opacity,
                sample_uv,
            } => {
                anyhow::ensure!(
                    self.session_ui
                        .summary
                        .as_ref()
                        .is_some_and(|s| s.completed)
                        && self.result.is_some()
                        && self.image_path == self.result,
                    "Open a completed session photograph first"
                );
                self.process_space
                    .inspect_diagnostic(map.as_deref(), opacity, sample_uv)?;
                self.process_view = true;
            }
            SetView { center, zoom } => {
                anyhow::ensure!(zoom <= 8.0, "The linked photo viewer supports 1..8× zoom");
                self.process_space.set_photo_view(center, zoom);
            }
            StartStack {} => {
                anyhow::ensure!(
                    self.stack_start_blocker().is_none(),
                    "{}",
                    self.stack_start_blocker().unwrap_or("Stack unavailable")
                );
                self.start_render();
                return Ok(json!({"state":"queued","operation":"stack"}));
            }
            CancelStack {} => {
                if let Some((_, _, task)) = &self.session_import {
                    task.cancel();
                    return Ok(
                        json!({"state":"cancellation_requested","operation":"completed_session_import"}),
                    );
                }
                let job = self
                    .job
                    .as_ref()
                    .ok_or_else(|| anyhow::anyhow!("No stack is running"))?;
                job.cancel();
                return Ok(json!({"state":"cancellation_requested","operation":"stack"}));
            }
            SaveEditVersion { name } => {
                self.save_edit_version(&name)?;
                return Ok(json!({"state":"queued","operation":"save_edit_version"}));
            }
            RestoreEditVersion { id } => {
                self.restore_edit_version(&id)?;
                return Ok(json!({"state":"queued","operation":"restore_edit_version"}));
            }
            ExportViewBundle {
                grant_id,
                relative_parent,
                folder_name,
            } => {
                let root = self
                    .agent
                    .grants
                    .get(&grant_id)
                    .ok_or_else(|| anyhow::anyhow!("Unknown shared destination folder"))?;
                let parent = crate::agent_interface::resolve_granted_path(root, &relative_parent)?;
                anyhow::ensure!(parent.is_dir(), "Choose an existing destination parent");
                self.start_view_bundle_export(parent.join(folder_name))?;
                return Ok(json!({"state":"queued","operation":"export_view_bundle"}));
            }
            CancelViewBundleExport {} => {
                let task = self
                    .view_bundle_export
                    .as_ref()
                    .ok_or_else(|| anyhow::anyhow!("No bundle export is running"))?;
                task.cancel();
                return Ok(
                    json!({"state":"cancellation_requested","operation":"export_view_bundle"}),
                );
            }
            Export {
                file_name,
                format,
                color_space,
                hdr,
                quality,
                speed,
            } => {
                anyhow::ensure!(
                    self.agent_photo_is_current(),
                    "The current photograph is still loading"
                );
                let destination = self.export_destination_for_current().ok_or_else(|| {
                    anyhow::anyhow!("Choose an export folder in Export → Destination")
                })?;
                anyhow::ensure!(
                    destination.is_dir(),
                    "Choose an export folder in Export → Destination"
                );
                jobs::validate_export_destination(
                    self.stack.as_ref().map(|s| s.directory.as_path()),
                    &destination,
                )?;
                let origin = self
                    .editor
                    .loaded
                    .as_ref()
                    .ok_or_else(|| anyhow::anyhow!("Open a completed photograph first"))?
                    .image
                    .origin;
                let settings = crate::agent_interface::resolve_export_settings(
                    &format,
                    color_space,
                    hdr,
                    quality,
                    speed,
                    Some(origin),
                )
                .map_err(anyhow::Error::msg)?;
                let resolved = serde_json::to_value(&settings)?;
                self.start_tracked_export(destination.join(file_name), settings)?;
                return Ok(json!({"state":"queued","operation":"export","settings":resolved}));
            }
            Undo {} => {
                self.editor.commit_edit();
                anyhow::ensure!(self.undo_edit(false), "No undo action is available");
            }
            Redo {} => {
                anyhow::ensure!(self.undo_edit(true), "No redo action is available");
            }
            CreateProject { name, parent_id } => {
                let id = self
                    .project_explorer
                    .organize(&mut self.catalog, |catalog| {
                        if let Some(parent) = parent_id {
                            catalog.create_folder(parent, &name)
                        } else {
                            catalog.create_project(&name)
                        }
                    })?;
                self.persist_catalog();
                return Ok(json!({"id":id}));
            }
            RenameNode { id, name } => {
                self.project_explorer
                    .organize(&mut self.catalog, |catalog| catalog.rename(id, &name))?;
                self.persist_catalog();
            }
            ImportCompletedSession {
                grant_id,
                relative_path,
                parent_id,
            } => {
                let root = self
                    .agent
                    .grants
                    .get(&grant_id)
                    .ok_or_else(|| anyhow::anyhow!("This folder is not shared"))?;
                let path = crate::agent_interface::resolve_granted_path(root, &relative_path)?;
                self.start_completed_import(path, parent_id)?;
                return Ok(json!({"state":"queued", "operation":"completed_session_import"}));
            }
            ImportStack {
                grant_id,
                relative_path,
                name,
                parent_id,
            } => {
                anyhow::ensure!(
                    self.job.is_none() && self.scan.is_none() && self.replay.is_none(),
                    "Wait for the active operation"
                );
                let root = self
                    .agent
                    .grants
                    .get(&grant_id)
                    .ok_or_else(|| anyhow::anyhow!("This folder is not shared"))?;
                let path = crate::agent_interface::resolve_granted_path(root, &relative_path)?;
                anyhow::ensure!(path.is_dir(), "Choose a capture directory");
                let parent = parent_id
                    .map(Ok)
                    .unwrap_or_else(|| self.catalog.create_project(&name))?;
                anyhow::ensure!(
                    self.catalog.node(parent).is_some_and(|n| n.stack.is_none()),
                    "Choose a project or folder"
                );
                self.capture_parent = Some(parent);
                self.import(path);
            }
            ImportPreset {
                grant_id,
                relative_path,
            } => {
                anyhow::ensure!(
                    self.agent_photo_is_current(),
                    "Open a completed photograph first"
                );
                let root = self
                    .agent
                    .grants
                    .get(&grant_id)
                    .ok_or_else(|| anyhow::anyhow!("This folder is not shared"))?;
                let path = crate::agent_interface::resolve_granted_path(root, &relative_path)?;
                anyhow::ensure!(
                    path.extension()
                        .is_some_and(|s| s.eq_ignore_ascii_case("xmp")),
                    "Choose an XMP preset"
                );
                self.editor.import_preset(path)?;
                return Ok(json!({"state":"queued","operation":"preset_import"}));
            }
            CreateSession {
                name,
                passes,
                mode,
                primary_pass,
                memory_limit_gib,
                precision_weights,
                contribution_maps,
                focus_evidence,
                reproducibility,
                original_cfa_reconstruction,
                parent_id,
            } => {
                anyhow::ensure!(
                    self.job.is_none()
                        && self.scan.is_none()
                        && self.replay.is_none()
                        && !self.picker_active(),
                    "Wait for the active operation"
                );
                let mut seen = std::collections::HashSet::new();
                let mut manifest_passes = Vec::new();
                for pass in passes {
                    let mut directories = Vec::new();
                    for id in pass.stack_ids {
                        anyhow::ensure!(
                            seen.insert(id),
                            "A source stack may appear only once in this session"
                        );
                        let draft = self
                            .catalog
                            .node(id)
                            .and_then(|node| node.stack.as_ref())
                            .ok_or_else(|| anyhow::anyhow!("Unknown imported source stack {id}"))?;
                        anyhow::ensure!(
                            draft.settings.session.is_none(),
                            "Choose original source stacks instead of nesting an existing session"
                        );
                        directories.push(draft.source.clone());
                    }
                    manifest_passes.push(crate::session_workspace::PassSpec {
                        name: pass.name,
                        directories,
                    });
                }
                if let Some(parent) = parent_id {
                    anyhow::ensure!(
                        self.catalog
                            .node(parent)
                            .is_some_and(|node| node.stack.is_none()),
                        "Choose a project or folder"
                    );
                }
                self.capture_parent = parent_id;
                self.reload_session(
                    crate::session_workspace::SessionDraft {
                        manifest: crate::session_workspace::SessionSpec {
                            passes: manifest_passes,
                            mode,
                            primary_pass,
                            ..Default::default()
                        },
                        memory_limit_gib,
                        precision_weights,
                        contribution_maps,
                        focus_evidence,
                        reproducibility,
                        original_cfa_reconstruction,
                        sources: Vec::new(),
                    },
                    false,
                );
                self.session_ui.pending_name = Some(name);
                return Ok(json!({"state":"queued","operation":"session_import"}));
            }
            Suggest {
                title,
                rationale,
                region,
            } => {
                self.agent.suggestions.insert(0, (title, rationale, region));
                self.agent.suggestions.truncate(24);
                self.sidebar = Some(workspace::Sidebar::Agent);
            }
            Probe { .. } | Preview { .. } | Metadata { .. } => {
                anyhow::bail!("Diagnostic reads must run through the background read queue")
            }
        }
        Ok(json!({"state":"applied"}))
    }

    fn agent_settings(
        &mut self,
        patch: crate::agent_interface::SettingsPatch,
    ) -> anyhow::Result<()> {
        anyhow::ensure!(
            self.job.is_none(),
            "Wait for the running stack before editing its next recipe"
        );
        let before = history::Recipe::capture(&self.controls);
        let mut settings = self.controls.settings.clone();
        let mut exposure = self.controls.exposure;
        let mut gate = self.controls.gate;
        let mut workers = self.controls.workers;
        for (key, value) in patch {
            let number = value.as_f64().map(|n| n as f32);
            match key.as_str() {
                "exposure_ev" => {
                    exposure = number;
                    if number.is_some() {
                        settings.auto_exposure = false;
                    }
                }
                "pyramid_gate" => gate = number,
                "pyramid_bands" => settings.pyramid_bands = value.as_u64().map(|n| n as usize),
                "pyramid_exponent" => settings.pyramid_exponent = number,
                "pyramid_sharpen" => settings.pyramid_sharpen = number,
                "frame_limit" => settings.frame_limit = value.as_u64().map(|n| n as usize),
                "workers" => workers = value.as_u64().unwrap() as usize,
                "binned" => settings.binned = value.as_bool().unwrap(),
                "correct_lateral_ca" => settings.correct_lateral_ca = value.as_bool().unwrap(),
                "crop_to_coverage" => settings.crop_to_coverage = value.as_bool().unwrap(),
                "confidence_map" => settings.confidence_map = value.as_bool().unwrap(),
                "auto_exposure" => {
                    settings.auto_exposure = value.as_bool().unwrap();
                    if settings.auto_exposure {
                        exposure = None;
                    }
                }
                "resampler" => {
                    settings.resampler = jobs::Resampler::ALL
                        .into_iter()
                        .find(|r| r.cli_name() == value.as_str().unwrap())
                        .ok_or_else(|| anyhow::anyhow!("Unsupported resampler"))?
                }
                _ => anyhow::bail!("Unknown setting"),
            }
        }
        self.controls.settings = settings;
        self.controls.exposure = exposure;
        self.controls.gate = gate;
        self.controls.workers = workers;
        self.edits.changed_recipe(before, 0.0);
        self.commit_recipe_edit();
        self.save_active_draft();
        Ok(())
    }

    fn agent_read_task(&self, command: AgentCommand) -> anyhow::Result<Task<AgentReply>> {
        command.validate().map_err(anyhow::Error::msg)?;
        let revision = self.agent.revision;
        match command {
            AgentCommand::Metadata { frame } => self.agent_metadata_read_task(frame),
            AgentCommand::Probe {
                region,
                max_sources,
            } => {
                let archive = self.progress.admission_archive.clone();
                let current = self.agent_photo_is_current();
                let certified = current
                    && crate::process_output_space::OutputSpace::from_progress(
                        &self.progress,
                        self.result_viewer.source_size,
                    )
                    .is_some();
                let image = self
                    .editor
                    .loaded
                    .as_ref()
                    .filter(|_| current)
                    .map(|loaded| Arc::clone(&loaded.preview));
                let recipe = if self.editor.before {
                    Default::default()
                } else {
                    self.editor.recipe.clone()
                };
                let confidence_source = self.agent_confidence_source();
                let repaired = self.progress.source_repair.is_some();
                let baked_repairs = self
                    .editor
                    .loaded
                    .as_ref()
                    .filter(|_| current)
                    .and_then(|loaded| loaded.image.baked_recipe.as_ref())
                    .map(|recipe| {
                        recipe
                            .regions
                            .iter()
                            .filter(|r| r.enabled && r.source_range.is_some())
                            .cloned()
                            .collect::<Vec<_>>()
                    })
                    .unwrap_or_default();
                Ok(jobs::spawn_task("strehl-agent-probe", move |cancelled| {
                    let evidence = probe_region(&archive, &region, max_sources, certified);
                    let pixels = image
                        .as_ref()
                        .map(|image| region_statistics(image, &recipe, &region));
                    let confidence = confidence_source.map_or_else(
                        || json!({"available":false,"reason":"No certified current result"}),
                        |(path, size)| match crate::process_balance::read_evidence(
                            &path, size, &cancelled,
                        ) {
                            Ok(evidence) => evidence.probe(&region),
                            Err(error) => json!({"available":false,"reason":error.to_string()}),
                        },
                    );
                    Ok(AgentReply::success(
                        json!({"revision":revision,"region":region,"evidence":evidence,"pixels":pixels,
                        "confidence":confidence,"confidence_domain":"saved run output after regional reconstruction, before development edits",
                        "admission_domain":if repaired || !baked_repairs.is_empty() {"global merge before regional repair"}else{"global merge"},
                        "baked_source_repairs":baked_repairs,
                        "limitations":["Sparse admitted coefficients are not fractional RGB ownership.","Preview statistics cannot diagnose optical causes alone."]}),
                    ))
                }))
            }
            AgentCommand::Preview {
                target,
                region,
                max_side,
            } => match target {
                PreviewTarget::Final => {
                    anyhow::ensure!(
                        self.agent_photo_is_current(),
                        "The current photograph is loading; read state and retry"
                    );
                    let loaded = self.editor.loaded.as_ref().ok_or_else(|| {
                        anyhow::anyhow!("The editable photograph is loading; read state and retry")
                    })?;
                    let image = Arc::clone(&loaded.image);
                    let before = self.editor.before;
                    let recipe = if before {
                        Default::default()
                    } else {
                        self.editor.recipe.clone()
                    };
                    Ok(jobs::spawn_task("strehl-agent-photo", move |_| {
                        let bounds = region
                            .as_ref()
                            .map(crate::edit_workspace::shape_bounds)
                            .unwrap_or([[0.0, 0.0], [1.0, 1.0]]);
                        let (width, height, rgb) =
                            image.render_region_sdr8(&recipe, bounds[0], bounds[1], max_side)?;
                        png_reply(
                            revision,
                            image::RgbImage::from_raw(width, height, rgb)
                                .unwrap()
                                .into(),
                            json!({"domain":"final","region":region,"origin":image.origin,"display":"SDR","before_preview":before}),
                        )
                    }))
                }
                PreviewTarget::Source { frame } => {
                    let path = self
                        .stack
                        .as_ref()
                        .and_then(|s| s.frames.get(frame))
                        .ok_or_else(|| anyhow::anyhow!("Unknown source"))?
                        .path
                        .clone();
                    anyhow::ensure!(
                        region.is_none(),
                        "Camera previews are unregistered; use full source or final-region diagnostics"
                    );
                    Ok(jobs::spawn_task("strehl-agent-source", move |cancelled| {
                        let photo =
                            crate::source_preview::load_draft_source(&path, max_side, &cancelled)?;
                        let rgba = image::RgbaImage::from_raw(
                            photo.size[0] as u32,
                            photo.size[1] as u32,
                            photo.rgba,
                        )
                        .ok_or_else(|| anyhow::anyhow!("Invalid source preview"))?;
                        png_reply(
                            revision,
                            rgba.into(),
                            json!({"domain":"camera","frame":frame,"registered":false}),
                        )
                    }))
                }
                PreviewTarget::Diagnostic { name, level } => {
                    if name == "confidence" {
                        let (path, size) = self.agent_confidence_source().ok_or_else(|| {
                            anyhow::anyhow!("Open a certified completed photograph first")
                        })?;
                        return Ok(jobs::spawn_task(
                            "strehl-agent-confidence",
                            move |cancelled| {
                                let evidence =
                                    crate::process_balance::read_evidence(&path, size, &cancelled)?;
                                let image = evidence.preview(region.as_ref(), max_side);
                                png_reply(
                                    revision,
                                    image.into(),
                                    json!({
                                        "domain":"saved run output after regional reconstruction, before development edits",
                                        "name":"confidence","region":region,"missing":"transparent",
                                        "color_scale":{"blue":0,"sand":1000},
                                        "meaning":"folded observation rank: 0 one-sided, 1000 balanced; ties also read 0; neither end is a quality grade"
                                    }),
                                )
                            },
                        ));
                    }
                    let kind = match name.as_str() {
                        "admission" => DiagnosticKind::GateSupport,
                        "fallback" => DiagnosticKind::Averaging,
                        "detail" => DiagnosticKind::FocusEnergy,
                        _ => anyhow::bail!(
                            "This diagnostic has structured evidence in probe/snapshot but no retained image surface"
                        ),
                    };
                    let packet = self
                        .progress
                        .diagnostic_surfaces
                        .iter()
                        .rev()
                        .find(|s| s.kind == kind && s.level == level)
                        .cloned()
                        .ok_or_else(|| {
                            anyhow::anyhow!("That diagnostic surface was not retained")
                        })?;
                    anyhow::ensure!(
                        region.is_none(),
                        "Diagnostic preview exposes its whole sampled analysis grid"
                    );
                    Ok(jobs::spawn_task("strehl-agent-map", move |_| {
                        let gray = image::GrayImage::from_raw(
                            packet.width as u32,
                            packet.height as u32,
                            packet.pixels.to_vec(),
                        )
                        .ok_or_else(|| anyhow::anyhow!("Invalid diagnostic image"))?;
                        let image = image::DynamicImage::from(gray).resize(
                            max_side,
                            max_side,
                            image::imageops::FilterType::Nearest,
                        );
                        png_reply(
                            revision,
                            image,
                            json!({"domain":"sampled analysis grid","name":name,"level":level,"sequence":packet.sequence}),
                        )
                    }))
                }
            },
            _ => anyhow::bail!("Not a background read"),
        }
    }

    // Geometry alone cannot bind diagnostics to pixels: two different stacks
    // may have identical dimensions while an asynchronous document load changes.
    fn agent_photo_is_current(&self) -> bool {
        self.editor.loaded.as_ref().is_some_and(|loaded| {
            [loaded.image.width, loaded.image.height] == self.result_viewer.source_size
        }) && self.editor.loading.is_none()
            && self.result.as_ref().is_some_and(|path| {
                self.editor.path.as_ref() == Some(path) && self.image_path.as_ref() == Some(path)
            })
    }

    fn agent_confidence_source(&self) -> Option<(PathBuf, [usize; 2])> {
        if !self.agent_photo_is_current() {
            return None;
        }
        crate::process_output_space::OutputSpace::from_progress(
            &self.progress,
            self.result_viewer.source_size,
        )?;
        let size = self.progress.analysis_size.or(self.progress.plane_size)?;
        Some((
            self.result.as_ref()?.with_file_name("confidence.tiff"),
            size,
        ))
    }
}

fn agent_photo_view(active: bool, mapping: Option<(egui::Rect, egui::Rect)>) -> Value {
    let Some((photo, visible)) = mapping.filter(|_| active) else {
        return Value::Null;
    };
    if !photo.is_positive() || !visible.is_positive() || !photo.is_finite() || !visible.is_finite()
    {
        return Value::Null;
    }
    let visible = visible.intersect(photo);
    if !visible.is_positive() {
        return Value::Null;
    }
    let local = |point: egui::Pos2| (point - photo.min) / photo.size();
    let min = local(visible.min);
    let max = local(visible.max);
    json!({"uv":[[min.x,min.y],[max.x,max.y]],
        "meaning":"Visible final-photograph aperture from the last painted process view, in normalized image coordinates."})
}

fn png_reply(
    revision: u64,
    image: image::DynamicImage,
    metadata: Value,
) -> anyhow::Result<AgentReply> {
    let mut bytes = std::io::Cursor::new(Vec::new());
    image.write_to(&mut bytes, image::ImageFormat::Png)?;
    let image = AgentImage::png(bytes.get_ref()).map_err(anyhow::Error::msg)?;
    Ok(AgentReply::image(
        json!({"revision":revision,"preview":metadata}),
        image,
    ))
}

pub(super) fn region_statistics(
    image: &strehl_edit::LinearImage,
    recipe: &strehl_edit::DevelopmentRecipe,
    region: &Region,
) -> Value {
    let mut count = 0u64;
    let mut sum = 0.0f64;
    let mut maximum = f32::NEG_INFINITY;
    let mut over_white = 0u64;
    for (i, pixel) in image.pixels.as_chunks::<3>().0.iter().enumerate() {
        let uv = [
            ((i % image.width as usize) as f32 + 0.5) / image.width as f32,
            ((i / image.width as usize) as f32 + 0.5) / image.height as f32,
        ];
        if region.weight(uv, 0.0) <= 0.0 {
            continue;
        }
        let rgb = recipe.apply_pixel([pixel[0], pixel[1], pixel[2]], uv);
        let y = 0.2126 * rgb[0] + 0.7152 * rgb[1] + 0.0722 * rgb[2];
        count += 1;
        sum += f64::from(y);
        maximum = maximum.max(y);
        over_white += u64::from(y > 1.0);
    }
    let reference = match image.origin {
        strehl_edit::ImageOrigin::SceneLinear => "sensor normalization",
        strehl_edit::ImageOrigin::DisplayReferred => "imported SDR white",
    };
    json!({"sampling":"area-averaged linear preview","samples":count,"mean_luminance":(count>0).then(||sum/count as f64),
        "maximum_luminance":(count>0).then_some(maximum),"above_source_reference":over_white,"origin":image.origin,
        "reference_kind":reference,
        "units":format!("recipe-adjusted linear BT.709 luminance before display baseline; 1 is {reference}, not a quality score")})
}

pub(super) fn probe_region(
    archive: &crate::process_provenance::AdmissionArchive,
    region: &Region,
    max_sources: usize,
    certified: bool,
) -> Value {
    if !certified {
        return json!({"available":false,"reason":"No certified mapping between this photograph and retained source diagnostics"});
    }
    let mut records: BTreeMap<usize, Vec<Value>> = BTreeMap::new();
    for level in archive.levels().take(12) {
        let frames = archive.frames(level).collect::<Vec<_>>();
        let Some(meta) = frames
            .first()
            .and_then(|&frame| archive.metadata(level, frame))
        else {
            continue;
        };
        let Some(geometry) = crate::process_sample_glyphs::SampleGeometry::new(level, meta) else {
            continue;
        };
        let indices = (0..meta.samples[0] * meta.samples[1])
            .filter(|&i| {
                geometry.at(i).is_some_and(|sample| {
                    region.weight([sample.center.x, sample.center.y], 0.0) > 0.0
                })
            })
            .collect::<Vec<_>>();
        if indices.is_empty() {
            continue;
        }
        for frame in frames {
            let Some((_, mut cells)) = archive.cells(level, frame) else {
                continue;
            };
            let mut admitted = 0;
            let mut next = 0;
            for &i in &indices {
                admitted += usize::from(cells.nth(i - next).unwrap_or(false));
                next = i + 1;
            }
            records
                .entry(frame)
                .or_default()
                .push(json!({"level":level,"admitted":admitted,"observed":indices.len()}));
        }
    }
    let mut records = records.into_iter().collect::<Vec<_>>();
    records.sort_by(|a, b| {
        let score = |row: &Vec<Value>| {
            row.first().map_or(0.0, |v| {
                v["admitted"].as_f64().unwrap_or(0.0) / v["observed"].as_f64().unwrap_or(1.0)
            })
        };
        score(&b.1).total_cmp(&score(&a.1)).then(a.0.cmp(&b.0))
    });
    let total = records.len();
    json!({"available":true,"ranking":"admitted fraction at the finest retained scale; not ownership",
        "sources":records.into_iter().take(max_sources).map(|(frame,levels)|json!({"frame":frame,"levels":levels})).collect::<Vec<_>>(),
        "sources_observed":total,"omitted_packets":archive.dropped()})
}

#[cfg(test)]
#[path = "app-agent-review-tests.rs"]
mod independent_review_tests;

#[cfg(test)]
#[path = "agent-export-tests.rs"]
mod export_tests;

#[cfg(test)]
#[path = "agent-spatial-tests.rs"]
mod spatial_tests;

#[cfg(test)]
#[path = "app-session-control-tests.rs"]
mod session_control_tests;
