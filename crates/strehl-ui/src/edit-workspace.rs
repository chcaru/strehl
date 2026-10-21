//! Nondestructive photo edits. Decoding, development and export never run in a UI frame.
use crate::jobs::{Task, spawn_task};
use eframe::egui::{self, TextureHandle};
use std::{
    collections::{BTreeMap, BTreeSet},
    path::{Path, PathBuf},
    sync::Arc,
    time::{Duration, Instant},
};
use strehl_edit::{Adjustments, DevelopmentRecipe, LinearImage, RegionAdjustment, RegionShape};

#[path = "edit-magic.rs"]
mod magic;
#[path = "edit-recovery.rs"]
mod recovery;
#[path = "edit-regions.rs"]
mod regions;

pub(crate) struct LoadedPhoto {
    pub image: Arc<LinearImage>,
    pub preview: Arc<LinearImage>,
    pub recipe: DevelopmentRecipe,
    pub source: PathBuf,
    pub warnings: Vec<String>,
}

pub(crate) struct DevelopedPreview {
    pub revision: u64,
    pub before: bool,
    pub hdr: bool,
    pub prepared: crate::photo_viewport::PreparedPhoto,
}

#[derive(Clone, Copy, Debug, Default, PartialEq)]
pub(crate) enum DrawingTool {
    #[default]
    Navigate,
    Select,
    Ellipse,
    Rectangle,
    Polygon,
    Lasso,
    MagicLasso,
}

#[derive(Default)]
pub(crate) struct EditorState {
    pub path: Option<PathBuf>,
    pub loaded: Option<LoadedPhoto>,
    pub recipe: DevelopmentRecipe,
    pub selected: Option<String>,
    pub tool: DrawingTool,
    pub before: bool,
    pub show_regions: bool,
    pub drag: Option<egui::Pos2>,
    pub polygon: Vec<[f32; 2]>,
    region_interaction: regions::RegionInteraction,
    magic: magic::MagicState,
    pub texture: Option<TextureHandle>,
    pub loading: Option<Task<LoadedPhoto>>,
    pub developing: Option<Task<DevelopedPreview>>,
    developing_revision: Option<u64>,
    developing_before: bool,
    developing_hdr: bool,
    painted_before: bool,
    painted_hdr: bool,
    pub(crate) viewport: crate::photo_viewport::ViewportRefinement,
    pub exporting: Option<Task<PathBuf>>,
    pub dialog: Option<Task<Option<PathBuf>>>,
    pub dialog_kind: Option<&'static str>,
    pub preset: Option<(u64, Task<strehl_edit::XmpImport>)>,
    pub last_export: Option<PathBuf>,
    pub warnings: Vec<String>,
    pub error: Option<String>,
    pub revision: u64,
    pub painted_revision: Option<u64>,
    painted_side: u32,
    pub changed: Option<Instant>,
    pub saved_revision: Option<u64>,
    pub saving: Option<Task<u64>>,
    save_failed: bool,
    pub pending_edit: Option<(DevelopmentRecipe, f64)>,
    undo: Vec<DevelopmentRecipe>,
    redo: Vec<DevelopmentRecipe>,
    history_revision: u64,
    history_commits: u64,
    // Keep only recipes, never pixels or textures from another photograph.
    recoveries: BTreeMap<PathBuf, DevelopmentRecipe>,
    recovery_files: BTreeMap<PathBuf, PathBuf>,
    recovered_from_disk: BTreeSet<PathBuf>,
    recovery_root: Option<PathBuf>,
}

impl EditorState {
    pub fn display_stats(&self) -> serde_json::Value {
        self.viewport.stats()
    }
    pub fn photo_paint(&self) -> Option<crate::photo_viewport::PhotoPaint> {
        (self.painted_before == self.before)
            .then(|| self.viewport.paint())
            .flatten()
    }
    pub fn display_texture(&self) -> Option<&TextureHandle> {
        (self.painted_before == self.before)
            .then_some(self.texture.as_ref())
            .flatten()
    }
    pub fn request_view(
        &mut self,
        ctx: &egui::Context,
        mapping: (egui::Rect, egui::Rect),
        max_side: u32,
    ) {
        if let Some(loaded) = &self.loaded {
            self.viewport.demand(
                [loaded.image.width, loaded.image.height],
                mapping,
                ctx.pixels_per_point(),
                max_side,
            );
        }
    }
    pub fn import_preset(&mut self, path: PathBuf) -> anyhow::Result<()> {
        anyhow::ensure!(
            self.loaded.is_some() && self.loading.is_none(),
            "Open a completed photograph first"
        );
        anyhow::ensure!(self.preset.is_none(), "A preset is already loading");
        self.preset = Some((
            self.revision,
            spawn_task("strehl-preset-import", move |_| {
                let bytes = read_bounded(&path, 2 * 1024 * 1024)?;
                strehl_edit::import_xmp(std::str::from_utf8(&bytes)?)
            }),
        ));
        Ok(())
    }
    fn apply_preset(&mut self, import: strehl_edit::XmpImport) -> anyhow::Result<()> {
        let mut recipe = self.recipe.clone();
        let imported = import.recipe.global;
        self.warnings = import.warnings;
        for field in import.applied {
            match field.as_str() {
                "Exposure2012" => recipe.global.exposure = imported.exposure,
                "Contrast2012" => recipe.global.contrast = imported.contrast,
                "Highlights2012" => recipe.global.highlights = imported.highlights,
                "Shadows2012" => recipe.global.shadows = imported.shadows,
                "Whites2012" => recipe.global.whites = imported.whites,
                "Blacks2012" => recipe.global.blacks = imported.blacks,
                "Vibrance" => recipe.global.vibrance = imported.vibrance,
                "Saturation" => recipe.global.saturation = imported.saturation,
                _ => self.warnings.push(format!(
                    "{field}: the photograph's current HDR delivery settings were preserved."
                )),
            }
        }
        self.replace(recipe)
    }
    pub fn reset_document(&mut self) {
        let error = self
            .flush()
            .err()
            .map(|error| format!("Saving previous photo edits: {error:#}"));
        if error.is_some() {
            self.retain_current_recipe();
            let _ = self.persist_recoveries();
        }
        let recoveries = std::mem::take(&mut self.recoveries);
        let recovery_files = std::mem::take(&mut self.recovery_files);
        let recovered_from_disk = std::mem::take(&mut self.recovered_from_disk);
        let recovery_root = self.recovery_root.take();
        let exporting = self.exporting.take();
        let last_export = self.last_export.take();
        self.viewport.reset();
        let viewport = std::mem::take(&mut self.viewport);
        *self = Self {
            show_regions: true,
            exporting,
            last_export,
            viewport,
            error,
            recoveries,
            recovery_files,
            recovered_from_disk,
            recovery_root,
            ..Self::default()
        };
    }

    /// Save once at a document/exit boundary. Routine edits are saved by a
    /// worker; waiting here prevents an older write racing the final recipe.
    pub fn flush(&mut self) -> anyhow::Result<()> {
        if let Some(task) = self.saving.take() {
            let result = task
                .receiver
                .recv()
                .map_err(|error| anyhow::anyhow!(error))?;
            if let Ok(revision) = result {
                self.saved_revision = Some(revision);
                if revision == self.revision
                    && let Some(path) = self.path.clone()
                {
                    self.forget_recovery(&path);
                }
            }
        }
        if self.loaded.is_some()
            && self.saved_revision != Some(self.revision)
            && let Some(path) = self.path.clone()
        {
            save_recipe(&recipe_path(&path), &self.recipe)?;
            self.saved_revision = Some(self.revision);
            self.forget_recovery(&path);
        }
        let mut failed = None;
        let paths = self
            .recoveries
            .keys()
            .filter(|path| !self.recovered_from_disk.contains(*path))
            .cloned()
            .collect::<Vec<_>>();
        for path in paths {
            match save_recipe(&recipe_path(&path), &self.recoveries[&path]) {
                Ok(()) => self.forget_recovery(&path),
                Err(error) => failed = Some(error),
            }
        }
        if let Some(error) = failed {
            return Err(error);
        }
        Ok(())
    }

    pub fn recovery_panel(&mut self, ui: &mut egui::Ui) {
        if self.loaded.is_none()
            && self.loading.is_none()
            && self.error.is_some()
            && self.path.is_some()
            && ui.button("Retry opening photograph").clicked()
        {
            let path = self.path.take().unwrap();
            self.open(path);
        }
        if self.recoveries.is_empty() {
            return;
        }
        ui.colored_label(
            crate::theme::AMBER,
            format!("{} retained edit recipe(s)", self.recoveries.len()),
        );
        ui.label("Retained recipes can be restored on their photograph. Recipes recovered from another session are never applied over newer edits automatically.");
        if let Some(path) = self.path.clone()
            && self.recovered_from_disk.contains(&path)
            && self.loaded.is_some()
            && ui
                .button("Restore retained edits for this photograph")
                .clicked()
            && let Some(recipe) = self.recoveries.get(&path).cloned()
        {
            self.recovered_from_disk.remove(&path);
            if let Err(error) = self.replace(recipe) {
                self.error = Some(error.to_string());
            }
        }
        ui.horizontal(|ui| {
            if ui.button("Retry saving").clicked() {
                match self.flush() {
                    Ok(()) => self.error = None,
                    Err(error) => self.error = Some(format!("Saving retained edits: {error:#}")),
                }
            }
            if ui.button("Copy recipes").clicked() {
                let records = self
                    .recoveries
                    .iter()
                    .map(|(path, recipe)| serde_json::json!({"photograph":path, "recipe":recipe}))
                    .collect::<Vec<_>>();
                if let Ok(text) = serde_json::to_string_pretty(&records) {
                    ui.ctx().copy_text(text);
                }
            }
        });
        ui.separator();
    }

    pub fn open(&mut self, path: PathBuf) {
        if self.path.as_ref() == Some(&path) {
            return;
        }
        self.reset_document();
        self.path = Some(path.clone());
        self.loading = Some(spawn_task("strehl-edit-load", move |_| {
            let master = path.parent().unwrap_or(Path::new(".")).join("master.tiff");
            let source = if master.is_file() {
                master
            } else {
                path.clone()
            };
            let image = Arc::new(strehl_edit::load_tiff(&source)?);
            if source != path {
                let dimensions = image::ImageReader::open(&path)?
                    .with_guessed_format()?
                    .into_dimensions()?;
                anyhow::ensure!(
                    dimensions == (image.width, image.height),
                    "The scene-linear master dimensions do not match this photograph; its edits were not attached"
                );
            }
            let preview = Arc::new(image.preview(1600));
            let fallback = image.baked_recipe.clone().unwrap_or_default();
            let sidecar = recipe_path(&path);
            let mut warnings = Vec::new();
            let recipe = match read_bounded(&sidecar, 2 * 1024 * 1024) {
                Ok(bytes) => {
                    match serde_json::from_slice::<DevelopmentRecipe>(&bytes) {
                        Ok(recipe) if recipe.validate().is_ok() => recipe,
                        _ => {
                            warnings.push("The saved edit recipe could not be read. Original pixels are intact.".into());
                            fallback.clone()
                        }
                    }
                }
                Err(_) if !sidecar.exists() => fallback.clone(),
                _ => {
                    warnings.push("The saved edit recipe is unavailable or exceeds 2 MiB.".into());
                    fallback
                }
            };
            Ok(LoadedPhoto {
                image,
                preview,
                recipe,
                source,
                warnings,
            })
        }));
    }

    pub fn poll(&mut self, ctx: &egui::Context, max_texture_side: u32) {
        self.poll_magic(ctx);
        if let Some(result) = self
            .preset
            .as_ref()
            .and_then(|(_, task)| task.receiver.try_recv().ok())
        {
            let (revision, _) = self.preset.take().unwrap();
            if revision != self.revision {
                self.error = Some("The photograph changed while the preset loaded. Import it again to apply it to this revision.".into());
            } else {
                match result {
                    Ok(import) => {
                        if let Err(error) = self.apply_preset(import) {
                            self.error = Some(error.to_string());
                        }
                    }
                    Err(error) => self.error = Some(error),
                }
            }
        }
        if let Some(result) = self
            .loading
            .as_ref()
            .and_then(|task| task.receiver.try_recv().ok())
        {
            self.loading = None;
            match result {
                Ok(loaded) => {
                    let recovered = self
                        .path
                        .as_ref()
                        .filter(|path| !self.recovered_from_disk.contains(*path))
                        .and_then(|path| self.recoveries.get(path))
                        .cloned();
                    self.recipe = recovered.clone().unwrap_or_else(|| loaded.recipe.clone());
                    self.reconcile_selection();
                    self.warnings = loaded.warnings.clone();
                    self.loaded = Some(loaded);
                    self.revision = self.revision.wrapping_add(1);
                    self.saved_revision = recovered.is_none().then_some(self.revision);
                    if recovered.is_some() {
                        self.changed = Some(Instant::now());
                    }
                }
                Err(error) => self.error = Some(error),
            }
        }
        self.viewport.refresh_display(ctx);
        let hdr = self
            .loaded
            .as_ref()
            .is_some_and(|p| self.viewport.hdr_active(p.image.origin));
        if let Some(task) = &self.developing
            && (self.developing_revision != Some(self.revision)
                || self.developing_before != self.before
                || self.developing_hdr != hdr)
        {
            task.cancel();
        }
        let developed = self
            .developing
            .as_ref()
            .map(|task| task.receiver.try_recv());
        if let Some(result) = developed
            && !matches!(result, Err(std::sync::mpsc::TryRecvError::Empty))
        {
            self.developing = None;
            let requested_revision = self.developing_revision.take();
            match result {
                Ok(Ok(preview))
                    if preview.revision == self.revision
                        && preview.before == self.before
                        && preview.hdr == hdr =>
                {
                    self.painted_side = preview.prepared.size[0].max(preview.prepared.size[1]);
                    self.texture = Some(self.viewport.publish_overview(
                        ctx,
                        crate::photo_viewport::Identity {
                            revision: preview.revision,
                            before: preview.before,
                            hdr: preview.hdr,
                        },
                        preview.prepared,
                    ));
                    self.painted_revision = Some(preview.revision);
                    self.painted_before = preview.before;
                    self.painted_hdr = preview.hdr;
                }
                Err(std::sync::mpsc::TryRecvError::Disconnected) => {}
                Ok(Err(error))
                    if requested_revision == Some(self.revision)
                        && self.developing_before == self.before
                        && self.developing_hdr == hdr =>
                {
                    self.error = Some(error);
                    self.painted_revision = Some(self.revision);
                    self.painted_before = self.before;
                    self.painted_hdr = hdr;
                }
                Ok(_) => {} // A newer gesture has superseded this preview.
                Err(_) => {}
            }
        }
        let needs_coarse = self.painted_revision != Some(self.revision)
            || self.painted_before != self.before
            || self.painted_hdr != hdr;
        if self.developing.is_none()
            && needs_coarse
            && let Some(loaded) = &self.loaded
        {
            let image = Arc::clone(&loaded.preview);
            let recipe = if self.before {
                DevelopmentRecipe::default()
            } else {
                self.recipe.clone()
            };
            let revision = self.revision;
            let before = self.before;
            self.developing_revision = Some(revision);
            self.developing_before = before;
            self.developing_hdr = hdr;
            let presenter = self.viewport.presenter.clone();
            self.developing = Some(spawn_task("strehl-edit-preview", move |cancelled| {
                let mut stride = 1u32;
                while image.width.max(image.height).div_ceil(stride) > max_texture_side.max(1) {
                    stride *= 2;
                }
                let prepared = crate::photo_viewport::prepare(
                    &image,
                    &recipe,
                    strehl_edit::DisplayRegionRequest {
                        min: [0, 0],
                        max: [image.width, image.height],
                        stride,
                    },
                    &cancelled,
                    presenter.as_ref(),
                    hdr,
                    true,
                )?;
                Ok(DevelopedPreview {
                    revision,
                    before,
                    hdr,
                    prepared,
                })
            }));
        }
        let display_recipe = if self.before {
            DevelopmentRecipe::default()
        } else {
            self.recipe.clone()
        };
        self.viewport.poll(
            ctx,
            self.loaded.as_ref().map(|p| Arc::clone(&p.image)),
            &display_recipe,
            crate::photo_viewport::Identity {
                revision: self.revision,
                before: self.before,
                hdr,
            },
        );
        if let Some(result) = self
            .exporting
            .as_ref()
            .and_then(|task| task.receiver.try_recv().ok())
        {
            self.exporting = None;
            match result {
                Ok(path) => self.last_export = Some(path),
                Err(error) => self.error = Some(error),
            }
        }
        if let Some(result) = self
            .saving
            .as_ref()
            .and_then(|task| task.receiver.try_recv().ok())
        {
            self.saving = None;
            match result {
                Ok(revision) => {
                    self.saved_revision = Some(revision);
                    if revision == self.revision
                        && let Some(path) = self.path.clone()
                    {
                        self.forget_recovery(&path);
                    }
                }
                Err(error) => {
                    self.error = Some(format!("Saving edits: {error}"));
                    self.save_failed = true;
                    self.retain_current_recipe();
                    if let Err(backup) = self.persist_recoveries() {
                        self.error = Some(format!(
                            "Saving edits: {error}. Recovery backup also failed: {backup:#}"
                        ));
                    }
                }
            }
        }
        if self.saving.is_none()
            && !self.save_failed
            && self.saved_revision != Some(self.revision)
            && self
                .changed
                .is_some_and(|time| time.elapsed() > Duration::from_millis(500))
            && let Some(path) = &self.path
        {
            let path = recipe_path(path);
            let recipe = self.recipe.clone();
            let revision = self.revision;
            self.saving = Some(spawn_task("strehl-edit-save", move |_| {
                save_recipe(&path, &recipe)?;
                Ok(revision)
            }));
        }
        if self.loading.is_some()
            || self.developing.is_some()
            || self.exporting.is_some()
            || self.preset.is_some()
            || self.saving.is_some()
            || (!self.save_failed
                && self.loaded.is_some()
                && self.saved_revision != Some(self.revision))
        {
            ctx.request_repaint_after(Duration::from_millis(25));
        }
    }

    pub fn changed(&mut self) {
        self.revision = self.revision.wrapping_add(1);
        self.changed = Some(Instant::now());
        self.save_failed = false;
        self.last_export = None;
    }

    pub fn begin_edit(&mut self, before: DevelopmentRecipe, time: f64) {
        if let Some((_, last)) = &mut self.pending_edit {
            *last = time;
        } else {
            self.pending_edit = Some((before, time));
        }
        self.changed();
    }

    pub fn commit_edit(&mut self) {
        if let Some((before, _)) = self.pending_edit.take()
            && before != self.recipe
        {
            self.undo.push(before);
            if self.undo.len() > 64 {
                self.undo.remove(0);
            }
            self.redo.clear();
            self.history_revision = self.history_revision.wrapping_add(1);
            self.history_commits = self.history_commits.wrapping_add(1);
        }
    }

    pub fn replace(&mut self, recipe: DevelopmentRecipe) -> anyhow::Result<()> {
        // Refuse unsaveable bulk edits before changing pixels or the undo journal.
        recipe_bytes(&recipe)?;
        self.commit_edit();
        if recipe != self.recipe {
            let before = std::mem::replace(&mut self.recipe, recipe);
            self.pending_edit = Some((before, 0.0));
            self.changed();
            self.commit_edit();
        }
        self.reconcile_selection();
        Ok(())
    }

    pub fn reconcile_selection(&mut self) {
        if self
            .selected
            .as_ref()
            .is_some_and(|id| !self.recipe.regions.iter().any(|r| &r.id == id))
        {
            self.selected = None;
            self.cancel_geometry();
        }
    }

    pub fn add_region(&mut self, shape: RegionShape) -> anyhow::Result<String> {
        shape.validate()?;
        let id = format!(
            "region-{}-{}",
            std::process::id(),
            crate::workspace_history::timestamp()
        );
        let mut id = id;
        while self.recipe.regions.iter().any(|region| region.id == id) {
            id.push('x');
        }
        let mut recipe = self.recipe.clone();
        recipe.regions.push(RegionAdjustment {
            id: id.clone(),
            name: format!("Region {}", recipe.regions.len() + 1),
            note: String::new(),
            shape,
            feather: 0.4,
            enabled: true,
            adjustments: Adjustments::default(),
            source_range: None,
        });
        self.replace(recipe)?;
        self.selected = Some(id.clone());
        self.set_tool(DrawingTool::Select);
        self.show_regions = true;
        Ok(id)
    }

    pub fn can_undo(&self) -> bool {
        !self.undo.is_empty() || self.pending_edit.is_some()
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
    pub fn undo(&mut self) -> bool {
        self.commit_edit();
        let Some(previous) = self.undo.pop() else {
            return false;
        };
        self.redo
            .push(std::mem::replace(&mut self.recipe, previous));
        self.history_revision = self.history_revision.wrapping_add(1);
        self.changed();
        self.reconcile_selection();
        true
    }
    pub fn redo(&mut self) -> bool {
        let Some(next) = self.redo.pop() else {
            return false;
        };
        self.undo.push(std::mem::replace(&mut self.recipe, next));
        self.history_revision = self.history_revision.wrapping_add(1);
        self.changed();
        self.reconcile_selection();
        true
    }

    pub fn export_with_settings(
        &mut self,
        path: PathBuf,
        settings: strehl_edit::ExportSettings,
    ) -> anyhow::Result<()> {
        settings.validate()?;
        anyhow::ensure!(self.exporting.is_none(), "An export is already running");
        anyhow::ensure!(
            !path.exists(),
            "Choose a new export filename; existing photographs are never replaced"
        );
        crate::jobs::validate_export_destination(
            None,
            path.parent()
                .ok_or_else(|| anyhow::anyhow!("Choose an export directory"))?,
        )?;
        let loaded = self
            .loaded
            .as_ref()
            .ok_or_else(|| anyhow::anyhow!("Open a completed photograph first"))?;
        let image = Arc::clone(&loaded.image);
        let recipe = self.recipe.clone();
        recipe.validate()?;
        self.last_export = None;
        self.exporting = Some(spawn_task("strehl-edit-export", move |cancelled| {
            // The writer publishes without replacement; file options determine color encoding.
            strehl_edit::export_image(&path, &image, &recipe, &settings, &cancelled)?;
            Ok(path)
        }));
        self.error = None;
        Ok(())
    }
}

pub(crate) fn recipe_path(image: &Path) -> PathBuf {
    image.with_extension("strehl-edits.json")
}

fn save_recipe(path: &Path, recipe: &DevelopmentRecipe) -> anyhow::Result<()> {
    write_json_atomic(path, &recipe_bytes(recipe)?)
}

fn recipe_bytes(recipe: &DevelopmentRecipe) -> anyhow::Result<Vec<u8>> {
    recipe.validate()?;
    let bytes = serde_json::to_vec_pretty(recipe)?;
    anyhow::ensure!(
        bytes.len() <= 2 * 1024 * 1024,
        "These edits exceed the 2 MiB document limit. Reduce selections or Adaptive treatments before saving. Existing saved edits are intact."
    );
    Ok(bytes)
}

fn write_json_atomic(path: &Path, bytes: &[u8]) -> anyhow::Result<()> {
    use std::io::Write;
    crate::jobs::validate_export_destination(
        None,
        path.parent()
            .ok_or_else(|| anyhow::anyhow!("Edits need a parent directory"))?,
    )?;
    let mut nonce = [0u8; 16];
    getrandom::fill(&mut nonce)
        .map_err(|error| anyhow::anyhow!("Creating edit save identifier: {error}"))?;
    let nonce = nonce
        .iter()
        .map(|byte| format!("{byte:02x}"))
        .collect::<String>();
    let temporary = path.with_extension(format!("pending-{nonce}"));
    let result = (|| {
        let mut file = std::fs::OpenOptions::new()
            .create_new(true)
            .write(true)
            .open(&temporary)?;
        file.write_all(bytes)?;
        file.sync_all()?;
        drop(file);
        // Windows std::fs::rename replaces a file atomically on the same filesystem.
        std::fs::rename(&temporary, path)?;
        Ok(())
    })();
    if result.is_err() {
        let _ = std::fs::remove_file(&temporary);
    }
    result
}

pub(crate) fn read_bounded(path: &Path, limit: usize) -> anyhow::Result<Vec<u8>> {
    use std::io::Read;
    let file = std::fs::File::open(path)?;
    anyhow::ensure!(
        file.metadata()?.len() <= limit as u64,
        "File exceeds the {} byte limit",
        limit
    );
    let mut bytes = Vec::new();
    file.take(limit as u64 + 1).read_to_end(&mut bytes)?;
    anyhow::ensure!(bytes.len() <= limit, "File grew beyond the size limit");
    Ok(bytes)
}

pub(crate) fn normalized(point: egui::Pos2, image: egui::Rect) -> [f32; 2] {
    [
        ((point.x - image.left()) / image.width()).clamp(0.0, 1.0),
        ((point.y - image.top()) / image.height()).clamp(0.0, 1.0),
    ]
}

pub(crate) fn shape_bounds(shape: &RegionShape) -> [[f32; 2]; 2] {
    match shape {
        RegionShape::Ellipse { center, radius } => [
            [
                (center[0] - radius[0]).max(0.0),
                (center[1] - radius[1]).max(0.0),
            ],
            [
                (center[0] + radius[0]).min(1.0),
                (center[1] + radius[1]).min(1.0),
            ],
        ],
        RegionShape::Rectangle { min, max } => [*min, *max],
        RegionShape::Polygon { points } => {
            points
                .iter()
                .fold([[1.0f32, 1.0], [0.0, 0.0]], |mut bounds, point| {
                    for (axis, value) in point.iter().enumerate() {
                        bounds[0][axis] = bounds[0][axis].min(*value);
                        bounds[1][axis] = bounds[1][axis].max(*value);
                    }
                    bounds
                })
        }
    }
}

fn outline(shape: &RegionShape) -> Vec<[f32; 2]> {
    match shape {
        RegionShape::Ellipse { center, radius } => (0..96)
            .map(|i| {
                let angle = i as f32 * std::f32::consts::TAU / 96.0;
                [
                    center[0] + radius[0] * angle.cos(),
                    center[1] + radius[1] * angle.sin(),
                ]
            })
            .collect(),
        RegionShape::Rectangle { min, max } => vec![*min, [max[0], min[1]], *max, [min[0], max[1]]],
        RegionShape::Polygon { points } => points.clone(),
    }
}

#[cfg(test)]
#[path = "edit-workspace-review-tests.rs"]
mod independent_review_tests;
