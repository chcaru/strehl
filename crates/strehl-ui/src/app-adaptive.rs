//! Spatial photographic treatment, with persistent controls and worker-only metering.
use super::*;
use serde_json::{Value, json};
use std::sync::Arc;
use strehl_edit::{
    AdaptiveIntent, AdaptiveParameters, AdaptiveSuggestion, DevelopmentRecipe, LinearImage,
};

#[path = "adaptive-effect.rs"]
mod effect;

struct ParameterDraft {
    image: Arc<LinearImage>,
    target: Option<String>,
    stored: Option<AdaptiveParameters>,
    value: AdaptiveParameters,
}

struct PendingAdaptive {
    path: PathBuf,
    image: Arc<LinearImage>,
    revision: u64,
    strength: f32,
    target_region: Option<String>,
    magic_generation: u64,
    parameters: AdaptiveParameters,
    task: Task<AdaptiveSuggestion>,
}

struct AppliedAdaptive {
    image: Arc<LinearImage>,
    suggestion: AdaptiveSuggestion,
    parameters: AdaptiveParameters,
    strength: f32,
    applied: DevelopmentRecipe,
}

#[derive(Default)]
pub(super) struct AdaptiveState {
    path: Option<PathBuf>,
    pending: Option<PendingAdaptive>,
    applied: Option<AppliedAdaptive>,
    error: Option<String>,
    parameters: Option<ParameterDraft>,
    effect: effect::EffectMap,
    wake: Option<egui::Context>,
}

impl StrehlApp {
    pub(super) fn adaptive_busy(&self) -> bool {
        self.adaptive.pending.is_some()
    }
    pub(super) fn start_adaptive(&mut self, strength: f32) -> anyhow::Result<()> {
        self.start_adaptive_action(strength, AdaptiveIntent::Balance)
    }

    pub(super) fn start_highlight_restore(&mut self, strength: f32) -> anyhow::Result<()> {
        anyhow::ensure!(
            self.editor.selected.is_some(),
            "Select or draw a region first"
        );
        self.start_adaptive_action(strength, AdaptiveIntent::RestoreHighlights)
    }

    fn start_adaptive_action(
        &mut self,
        strength: f32,
        intent: AdaptiveIntent,
    ) -> anyhow::Result<()> {
        let parameters = self
            .editor
            .recipe
            .adaptive_scope(self.editor.selected.as_deref())
            .map_or_else(AdaptiveParameters::default, |field| field.parameters);
        self.start_adaptive_parameters(strength, intent, parameters, true)
    }

    fn start_adaptive_parameters(
        &mut self,
        strength: f32,
        intent: AdaptiveIntent,
        parameters: AdaptiveParameters,
        allow_cached: bool,
    ) -> anyhow::Result<()> {
        parameters.validate()?;
        anyhow::ensure!(
            strength.is_finite() && (0.0..=1.0).contains(&strength),
            "Adaptive amount must be between 0 and 1"
        );
        anyhow::ensure!(
            self.adaptive.pending.is_none(),
            "Adaptive is already analyzing"
        );
        anyhow::ensure!(
            !self.presets_busy(),
            "Finish applying the preset before using Adaptive"
        );
        anyhow::ensure!(
            !self.editor.magic_pending(),
            "Finish or cancel Magic selection before using Adaptive"
        );
        anyhow::ensure!(
            self.editor.loading.is_none()
                && self.editor.path == self.result
                && self.image_path == self.result,
            "Open the current completed photograph first"
        );
        let loaded = self
            .editor
            .loaded
            .as_ref()
            .ok_or_else(|| anyhow::anyhow!("Open a completed photograph first"))?;
        let path = self
            .editor
            .path
            .clone()
            .ok_or_else(|| anyhow::anyhow!("The photograph has no saved location"))?;
        let target_region = self.editor.selected.clone();
        if allow_cached
            && self.adaptive.path.as_ref() == Some(&path)
            && let Some(applied) = self.adaptive.applied.as_mut()
            && applied.applied == self.editor.recipe
            && Arc::ptr_eq(&applied.image, &loaded.image)
            && applied.suggestion.target_region == target_region
            && applied.suggestion.intent == intent
            && applied.parameters == parameters
        {
            let recipe = applied.suggestion.recipe_at(strength)?;
            self.editor.replace(recipe.clone())?;
            applied.applied = recipe;
            applied.strength = strength;
            self.adaptive.error = None;
            self.editor.before = false;
            return Ok(());
        }
        let image = Arc::clone(&loaded.image);
        self.editor.commit_edit();
        let recipe = self.editor.recipe.clone();
        let worker_target = target_region.clone();
        self.adaptive.path = Some(path.clone());
        self.adaptive.error = None;
        let wake = self.adaptive.wake.clone();
        self.adaptive.pending = Some(PendingAdaptive {
            path,
            image: Arc::clone(&image),
            revision: self.editor.revision,
            strength,
            target_region,
            magic_generation: self.editor.magic_generation(),
            parameters,
            task: jobs::spawn_notifying_task(
                "strehl-adaptive-develop",
                move |cancelled| {
                    anyhow::ensure!(
                        !cancelled.load(std::sync::atomic::Ordering::Relaxed),
                        "Adaptive cancelled"
                    );
                    strehl_edit::analyze_adaptive_with_parameters(
                        &image,
                        &recipe,
                        worker_target.as_deref(),
                        intent,
                        parameters,
                    )
                },
                move || {
                    if let Some(ctx) = &wake {
                        ctx.request_repaint();
                    }
                },
            ),
        });
        Ok(())
    }

    pub(super) fn poll_adaptive(&mut self, ctx: &egui::Context) {
        if self.adaptive.path != self.editor.path {
            self.adaptive = AdaptiveState {
                path: self.editor.path.clone(),
                ..Default::default()
            };
        }
        self.adaptive.wake = Some(ctx.clone());
        self.adaptive.effect.poll(
            ctx,
            self.editor.loaded.as_ref().map(|p| &p.image),
            &self.editor.recipe,
            self.editor.selected.as_deref(),
        );
        if self.adaptive.applied.as_ref().is_some_and(|applied| {
            self.editor
                .loaded
                .as_ref()
                .is_none_or(|loaded| !Arc::ptr_eq(&applied.image, &loaded.image))
        }) {
            self.adaptive.applied = None;
        }
        if self
            .adaptive
            .pending
            .as_ref()
            .is_some_and(|pending| pending.magic_generation != self.editor.magic_generation())
        {
            // A later Magic action wins even if it was cancelled or found no
            // regions. Do not let worker completion order choose the action.
            self.adaptive.pending = None;
            self.adaptive.error = Some(
                "Magic selection superseded Adaptive. Run Adaptive again after selecting the area."
                    .into(),
            );
        }
        if let Some(result) = self.adaptive.pending.as_ref().and_then(|pending| {
            match pending.task.receiver.try_recv() {
                Ok(result) => Some(result),
                Err(std::sync::mpsc::TryRecvError::Empty) => None,
                Err(std::sync::mpsc::TryRecvError::Disconnected) => Some(Err(
                    "Adaptive analysis ended without a result. Try again.".into(),
                )),
            }
        }) {
            let pending = self.adaptive.pending.take().unwrap();
            if self.editor.path.as_ref() != Some(&pending.path)
                || self.editor.revision != pending.revision
                || self.editor.loading.is_some()
                || self.editor.selected != pending.target_region
                || self
                    .editor
                    .loaded
                    .as_ref()
                    .is_none_or(|loaded| !Arc::ptr_eq(&pending.image, &loaded.image))
            {
                self.adaptive.error =
                    Some("Edits changed during analysis, or another region was selected. Run Adaptive again.".into());
            } else {
                match result.and_then(|suggestion| {
                    let recipe = suggestion
                        .recipe_at(pending.strength)
                        .map_err(|error| error.to_string())?;
                    self.editor
                        .replace(recipe.clone())
                        .map_err(|error| error.to_string())?;
                    Ok(AppliedAdaptive {
                        image: pending.image,
                        suggestion,
                        parameters: pending.parameters,
                        strength: pending.strength,
                        applied: recipe,
                    })
                }) {
                    Ok(applied) => {
                        self.adaptive.applied = Some(applied);
                        self.editor.before = false;
                    }
                    Err(error) => self.adaptive.error = Some(error),
                }
            }
        }
    }

    pub(super) fn adaptive_snapshot(&self) -> Value {
        let applied = self.adaptive.applied.as_ref();
        let field = self
            .editor
            .recipe
            .adaptive_scope(self.editor.selected.as_deref());
        json!({
            "analyzing": self.adaptive.pending.is_some(),
            "amount": field.map(|f| f.amount).or_else(|| applied.map(|value| value.strength)),
            "current": applied.map_or(field.is_some(), |value| value.applied == self.editor.recipe
                && value.suggestion.target_region == self.editor.selected
                && self.editor.loaded.as_ref().is_some_and(|loaded| Arc::ptr_eq(&value.image, &loaded.image))),
            // Do not duplicate up to six measured lattices twice in every snapshot.
            "analysis": applied.map(|value| json!({
                "stats": value.suggestion.stats,
                "after_stats": value.suggestion.after_stats,
                "target_region": value.suggestion.target_region,
                "intent": value.suggestion.intent,
                "highlights": value.suggestion.highlights,
                "changes": value.suggestion.changes,
                "limitations": value.suggestion.limitations,
            })),
            "spatial": field.map(|f| json!({"amount": f.amount, "parameters": f.parameters, "lattice": [f.width, f.height, f.levels]})),
            "error": self.adaptive.error,
            "method": "Image-dependent local light and color curves; deterministic, no learned model or generated detail."
        })
    }

    // Absolute Amount edits a persisted field without metering again. The outer
    // photo panel groups dragging/reset into the same shared Undo transaction.
    fn set_spatial_amount(&mut self, amount: f32) -> anyhow::Result<()> {
        anyhow::ensure!(
            amount.is_finite() && (0.0..=1.0).contains(&amount),
            "Amount must be between 0 and 1"
        );
        anyhow::ensure!(
            !self.adaptive_busy() && !self.presets_busy() && !self.editor.magic_pending(),
            "Finish the current adjustment first"
        );
        let field = self
            .editor
            .recipe
            .spatial
            .iter_mut()
            .find(|field| field.target_region == self.editor.selected)
            .ok_or_else(|| anyhow::anyhow!("Analyze this photograph or region first"))?;
        field.amount = amount;
        self.editor.before = false;
        Ok(())
    }

    fn reconcile_adaptive_parameters(&mut self) {
        let Some(loaded) = self.editor.loaded.as_ref() else {
            self.adaptive.parameters = None;
            return;
        };
        let stored = self
            .editor
            .recipe
            .adaptive_scope(self.editor.selected.as_deref())
            .map(|f| f.parameters);
        let changed = self.adaptive.parameters.as_ref().is_none_or(|draft| {
            !Arc::ptr_eq(&draft.image, &loaded.image)
                || draft.target != self.editor.selected
                || draft.stored != stored
        });
        if changed {
            self.adaptive.parameters = Some(ParameterDraft {
                image: Arc::clone(&loaded.image),
                target: self.editor.selected.clone(),
                stored,
                value: stored.unwrap_or_default(),
            });
        }
    }

    pub(super) fn adaptive_panel(&mut self, ui: &mut egui::Ui) {
        self.adaptive.wake = Some(ui.ctx().clone());
        self.reconcile_adaptive_parameters();
        let scope_enabled = self.editor.selected.as_ref().is_none_or(|id| {
            self.editor
                .recipe
                .regions
                .iter()
                .any(|region| &region.id == id && region.enabled)
        });
        let idle = !self.adaptive_busy() && !self.presets_busy() && !self.editor.magic_pending();
        let ready = idle && scope_enabled;
        let has_field = self
            .editor
            .recipe
            .adaptive_scope(self.editor.selected.as_deref())
            .is_some();
        let parameters = self
            .adaptive
            .parameters
            .as_ref()
            .map_or_else(AdaptiveParameters::default, |draft| draft.value);
        let disabled = if !scope_enabled {
            "Enable this region before changing its treatment."
        } else {
            "Finish or cancel the current adjustment first."
        };
        ui.label(RichText::new("Spatial light & color").color(INK).size(12.0));
        theme::caption(
            ui,
            "Light and color shaped by the photograph, area by area.",
        );
        let label = if has_field {
            "Recalculate treatment"
        } else if self.editor.selected.is_some() {
            "Analyze region"
        } else {
            "Analyze photograph"
        };
        if ui.add_enabled_ui(ready, |ui| ui.add_sized([ui.available_width(), 27.0], egui::Button::new(label))).inner
            .on_hover_text("Build local light and color curves from this photograph. Manual sliders stay unchanged. Undo restores the previous treatment.")
            .on_disabled_hover_text(disabled).clicked()
            && let Err(error) = self.start_adaptive_parameters(1.0, AdaptiveIntent::Balance, parameters, false) {
                self.adaptive.error = Some(error.to_string());
        }
        if self.adaptive.pending.is_some() {
            theme::caption(ui, "Reading local light and color…");
        }
        if let Some(field) = self
            .editor
            .recipe
            .adaptive_scope(self.editor.selected.as_deref())
        {
            let mut amount = field.amount;
            if ui
                .add_enabled_ui(ready, |ui| {
                    super::editing::controls::slider(
                        ui,
                        "Amount",
                        &mut amount,
                        0.0..=1.0,
                        1.0,
                        2,
                        "",
                    )
                })
                .inner
                .on_disabled_hover_text(disabled)
                .changed()
                && let Err(error) = self.set_spatial_amount(amount)
            {
                self.adaptive.error = Some(error.to_string());
            }
        }
        egui::CollapsingHeader::new("Shape the treatment").id_salt("adaptive-parameters").show(ui, |ui| {
            ui.add_enabled_ui(ready, |ui| {
                let defaults = AdaptiveParameters::default();
                if let Some(draft) = &mut self.adaptive.parameters {
                    for (label, value, default, help) in [
                        ("Light balance", &mut draft.value.balance, defaults.balance, "Redistribute local light while preserving the scene's overall light placement."),
                        ("Local contrast", &mut draft.value.local_contrast, defaults.local_contrast, "Separate local tones without sharpening pixels or inventing detail."),
                        ("Color", &mut draft.value.color, defaults.color, "Enrich supported local color with protection for neutral and already saturated areas."),
                    ] {
                        super::editing::controls::slider(ui, label, value, 0.0..=1.0, default, 2, "").on_hover_text(help);
                    }
                }
            });
            theme::caption(ui, "Recalculate to apply these choices · double-click resets a control");
        });
        if has_field {
            egui::CollapsingHeader::new("Where it changes")
                .id_salt("adaptive-effect")
                .show(ui, |ui| {
                    if let Some(loaded) = &self.editor.loaded {
                        self.adaptive.effect.show(
                            ui,
                            &loaded.image,
                            &self.editor.recipe,
                            self.editor.selected.as_deref(),
                        );
                    }
                });
        }
        if self.editor.selected.is_some() && ui.add_enabled_ui(ready, |ui|
            ui.add_sized([ui.available_width(), 25.0], egui::Button::new("Balance highlights"))).inner
            .on_hover_text("Compress bright light in this region and diagnose tonal variation. Already-clipped texture cannot be recreated.")
            .on_disabled_hover_text(disabled).clicked()
            && let Err(error) = self.start_highlight_restore(1.0) { self.adaptive.error = Some(error.to_string()); }
        if let Some(applied) = &mut self.adaptive.applied {
            let current = applied.applied == self.editor.recipe
                && applied.suggestion.target_region == self.editor.selected
                && self
                    .editor
                    .loaded
                    .as_ref()
                    .is_some_and(|loaded| Arc::ptr_eq(&applied.image, &loaded.image));
            let same_scope = applied.suggestion.target_region == self.editor.selected
                && self
                    .editor
                    .loaded
                    .as_ref()
                    .is_some_and(|loaded| Arc::ptr_eq(&applied.image, &loaded.image));
            if same_scope {
                if current && applied.suggestion.intent == AdaptiveIntent::RestoreHighlights {
                    if ui
                        .add_enabled_ui(ready, |ui| {
                            super::editing::controls::slider(
                                ui,
                                "Highlight amount",
                                &mut applied.strength,
                                0.0..=1.0,
                                1.0,
                                2,
                                "",
                            )
                        })
                        .inner
                        .changed()
                    {
                        match applied.suggestion.recipe_at(applied.strength) {
                            Ok(recipe) => {
                                self.editor.recipe = recipe.clone();
                                applied.applied = recipe;
                                self.editor.before = false;
                            }
                            Err(error) => self.adaptive.error = Some(error.to_string()),
                        }
                    }
                    theme::caption(ui, &applied.suggestion.highlights.assessment);
                }
                if applied.suggestion.changes.is_empty() {
                    theme::caption(ui, "No additional treatment found for the measured area.");
                }
                egui::CollapsingHeader::new("Analysis notes")
                    .id_salt("adaptive-explanation")
                    .show(ui, |ui| {
                        theme::caption(
                            ui,
                            "Measurements at analysis time, with full treatment amount.",
                        );
                        for change in &applied.suggestion.changes {
                            ui.label(&change.control);
                            theme::caption(ui, &change.reason);
                        }
                        for limitation in &applied.suggestion.limitations {
                            theme::caption(ui, limitation);
                        }
                        theme::caption(
                            ui,
                            &format!("{} scene samples", applied.suggestion.stats.sample_count),
                        );
                    });
            }
        }
        if let Some(error) = &self.adaptive.error {
            ui.colored_label(AMBER, error);
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::sync::Arc;
    use strehl_edit::{ImageOrigin, LinearImage, RegionAdjustment, RegionShape, SourceRange};

    fn fixture() -> StrehlApp {
        let mut app = StrehlApp::from_launch(4096, LaunchOptions::default());
        app.catalog = Default::default();
        let mut pixels = Vec::with_capacity(128 * 96 * 3);
        for y in 0..96 {
            for x in 0..128 {
                let light = 0.04 + 0.28 * (x + y) as f32 / 222.0;
                pixels.extend_from_slice(&[light * 1.15, light, light * 0.78]);
            }
        }
        let image = Arc::new(LinearImage {
            width: 128,
            height: 96,
            pixels,
            origin: ImageOrigin::SceneLinear,
            baseline: None,
            baked_recipe: None,
        });
        let path = PathBuf::from("never-written-adaptive-fixture.tiff");
        app.result = Some(path.clone());
        app.image_path = Some(path.clone());
        app.editor.path = Some(path.clone());
        app.editor.loaded = Some(crate::edit_workspace::LoadedPhoto {
            image: Arc::clone(&image),
            preview: image,
            recipe: Default::default(),
            source: path,
            warnings: Vec::new(),
        });
        app
    }

    fn complete(app: &mut StrehlApp) {
        let ctx = egui::Context::default();
        let deadline = Instant::now() + Duration::from_secs(5);
        while app.adaptive.pending.is_some() {
            app.poll_adaptive(&ctx);
            assert!(
                Instant::now() < deadline,
                "bounded adaptive work did not finish"
            );
            std::thread::yield_now();
        }
    }

    #[test]
    fn adaptive_worker_preserves_regions_and_has_one_reversible_application() {
        let mut app = fixture();
        app.editor.recipe.regions.push(RegionAdjustment {
            id: "repair".into(),
            name: "Preserve my repair".into(),
            note: "human annotation".into(),
            shape: RegionShape::Ellipse {
                center: [0.4, 0.6],
                radius: [0.1, 0.2],
            },
            feather: 0.25,
            enabled: true,
            adjustments: strehl_edit::Adjustments {
                exposure: -0.3,
                ..Default::default()
            },
            source_range: Some(SourceRange { first: 2, last: 5 }),
        });
        let original = app.editor.recipe.clone();
        app.start_adaptive(1.0).unwrap();
        complete(&mut app);
        assert!(app.adaptive.error.is_none(), "{:?}", app.adaptive.error);
        assert_eq!(
            app.editor.recipe.global, original.global,
            "Spatial treatment must leave manual sliders intact"
        );
        assert!(
            app.editor.recipe.adaptive_scope(None).is_some(),
            "fixture must exercise an actual field"
        );
        let image = &app.editor.loaded.as_ref().unwrap().image;
        assert!(
            (0..image.width as usize * image.height as usize)
                .any(|i| image.developed_pixel(i, &original)
                    != image.developed_pixel(i, &app.editor.recipe)),
            "field must actually affect pixels"
        );
        assert_eq!(app.editor.recipe.regions, original.regions);
        assert_eq!(app.editor.recipe.hdr, original.hdr);
        assert_eq!(app.adaptive_snapshot()["current"], true);
        assert!(app.editor.undo());
        assert_eq!(app.editor.recipe, original);
        assert!(
            !app.editor.can_undo(),
            "analysis plus application must create only one undo entry"
        );
        assert_eq!(app.adaptive_snapshot()["current"], false);
    }

    #[test]
    fn adaptive_reply_cannot_overwrite_a_newer_human_adjustment() {
        let mut app = fixture();
        app.start_adaptive(1.0).unwrap();
        let mut human = app.editor.recipe.clone();
        human.global.temperature = 22.0;
        human.global.exposure = -0.7;
        app.editor.replace(human.clone()).unwrap();
        complete(&mut app);
        assert_eq!(app.editor.recipe, human);
        assert!(
            app.adaptive
                .error
                .as_deref()
                .unwrap()
                .contains("Edits changed")
        );
        assert!(app.adaptive.applied.is_none());
    }

    #[test]
    fn switching_photographs_discards_pending_adaptive_work() {
        let mut app = fixture();
        app.start_adaptive(1.0).unwrap();
        app.editor.path = Some(PathBuf::from("different-photograph.tiff"));
        app.poll_adaptive(&egui::Context::default());
        assert!(app.adaptive.pending.is_none());
        assert!(app.adaptive.applied.is_none());
        assert_eq!(app.editor.recipe, DevelopmentRecipe::default());
    }

    #[test]
    fn zero_amount_is_exact_and_invalid_amounts_never_queue_work() {
        let mut app = fixture();
        for invalid in [f32::NAN, f32::INFINITY, -0.01, 1.01] {
            assert!(app.start_adaptive(invalid).is_err());
            assert!(app.adaptive.pending.is_none());
        }
        let original = app.editor.recipe.clone();
        app.start_adaptive(0.0).unwrap();
        complete(&mut app);
        assert_eq!(app.editor.recipe, original);
        assert!(!app.editor.can_undo());
        assert!(app.adaptive.applied.is_some());
    }

    #[test]
    fn agent_amount_reuses_the_original_analysis_instead_of_compounding_it() {
        let mut app = fixture();
        let original = app.editor.recipe.clone();
        app.start_adaptive(1.0).unwrap();
        complete(&mut app);
        let full = app.editor.recipe.clone();
        assert_ne!(full, original, "fixture must exercise a real treatment");
        app.start_adaptive(0.5).unwrap();
        assert!(app.adaptive.pending.is_none());
        app.start_adaptive(1.0).unwrap();
        assert_eq!(app.editor.recipe, full);
        app.start_adaptive(0.0).unwrap();
        assert_eq!(app.editor.recipe, original);
    }

    // Independent review controls: path and revision can repeat after a reload.
    fn replace_pixels_at_same_path(app: &mut StrehlApp) {
        let loaded = app.editor.loaded.as_mut().unwrap();
        let mut image = (*loaded.image).clone();
        image.pixels.fill(0.18);
        loaded.image = Arc::new(image);
        loaded.preview = Arc::clone(&loaded.image);
    }

    #[test]
    fn independent_review_same_path_new_pixels_reject_pending_analysis() {
        let mut app = fixture();
        let original = app.editor.recipe.clone();
        app.start_adaptive(1.0).unwrap();
        let revision = app.editor.revision;
        replace_pixels_at_same_path(&mut app);
        assert_eq!(app.editor.revision, revision, "exercise a reused revision");
        complete(&mut app);
        assert_eq!(app.editor.recipe, original);
        assert!(app.adaptive.applied.is_none());
        assert!(
            app.adaptive
                .error
                .as_deref()
                .unwrap()
                .contains("Edits changed")
        );
    }

    #[test]
    fn independent_review_same_path_reload_cannot_reuse_cached_treatment() {
        let mut app = fixture();
        app.start_adaptive(1.0).unwrap();
        complete(&mut app);
        let old_recipe = app.editor.recipe.clone();
        assert_ne!(old_recipe, DevelopmentRecipe::default());
        replace_pixels_at_same_path(&mut app);
        assert_eq!(app.adaptive_snapshot()["current"], false);
        app.start_adaptive(0.5).unwrap();
        assert!(
            app.adaptive.pending.is_some(),
            "new pixels require new analysis"
        );
        complete(&mut app);
        assert_eq!(
            app.editor.recipe.global, old_recipe.global,
            "uniform input must not shift manual light controls"
        );
        let remaining = app.editor.recipe.adaptive_scope(None).unwrap();
        assert_eq!(
            remaining.amount,
            old_recipe.adaptive_scope(None).unwrap().amount * 0.5,
            "new flat-image analysis fades the old addressed field instead of reusing its cached result"
        );
        assert_eq!(app.adaptive_snapshot()["current"], true);
        assert!(
            app.adaptive
                .applied
                .as_ref()
                .unwrap()
                .suggestion
                .changes
                .is_empty()
        );
    }

    #[test]
    fn independent_review_worker_disconnect_finishes_with_an_error() {
        let mut app = fixture();
        app.start_adaptive(1.0).unwrap();
        app.adaptive.pending.as_mut().unwrap().task =
            jobs::spawn_task("adaptive-disconnect-control", |_cancelled| {
                panic!("planted worker disconnect");
            });
        complete(&mut app);
        assert!(app.adaptive.pending.is_none());
        assert!(
            app.adaptive
                .error
                .as_deref()
                .unwrap()
                .contains("without a result")
        );
        assert_eq!(app.editor.recipe, DevelopmentRecipe::default());
    }

    #[test]
    fn reusing_amount_exits_before_and_does_not_reanalyze() {
        let mut app = fixture();
        app.start_adaptive(1.0).unwrap();
        complete(&mut app);
        app.editor.before = true;
        app.start_adaptive(0.5).unwrap();
        assert!(
            !app.editor.before,
            "a changed amount was hidden behind Before"
        );
        assert!(app.adaptive.pending.is_none());
    }

    fn select_bright_region(app: &mut StrehlApp) {
        app.editor.recipe.regions.push(RegionAdjustment {
            id: "bright".into(),
            name: "Bright patch".into(),
            note: String::new(),
            shape: RegionShape::Rectangle {
                min: [0.4, 0.2],
                max: [0.9, 0.9],
            },
            feather: 0.2,
            enabled: true,
            adjustments: strehl_edit::Adjustments {
                exposure: 3.0,
                ..Default::default()
            },
            source_range: Some(SourceRange { first: 2, last: 8 }),
        });
        app.editor.selected = Some("bright".into());
    }

    #[test]
    fn selected_highlight_treatment_is_local_reversible_and_amount_cached() {
        let mut app = fixture();
        assert!(app.start_highlight_restore(1.0).is_err());
        select_bright_region(&mut app);
        let original = app.editor.recipe.clone();
        app.editor.before = true;
        app.start_highlight_restore(1.0).unwrap();
        complete(&mut app);
        assert!(app.adaptive.error.is_none(), "{:?}", app.adaptive.error);
        assert!(!app.editor.before);
        assert_eq!(app.editor.recipe.global, original.global);
        assert!(app.editor.recipe.regions[0].adjustments.highlights < -1.0);
        assert_eq!(
            app.editor.recipe.regions[0].source_range,
            original.regions[0].source_range
        );
        let full = app.editor.recipe.clone();
        app.start_highlight_restore(0.4).unwrap();
        assert!(app.adaptive.pending.is_none());
        app.start_highlight_restore(1.0).unwrap();
        assert_eq!(app.editor.recipe, full);
        app.start_highlight_restore(0.0).unwrap();
        assert_eq!(app.editor.recipe, original);
        app.start_highlight_restore(1.0).unwrap();
        assert!(app.editor.undo());
        assert_eq!(app.editor.recipe, original);
    }

    #[test]
    fn selection_change_discards_pending_analysis_and_cannot_reuse_global_cache() {
        let mut app = fixture();
        app.start_adaptive(1.0).unwrap();
        complete(&mut app);
        select_bright_region(&mut app);
        app.start_adaptive(0.5).unwrap();
        assert!(
            app.adaptive.pending.is_some(),
            "region reused a global suggestion"
        );
        let before = app.editor.recipe.clone();
        app.editor.selected = None;
        complete(&mut app);
        assert_eq!(app.editor.recipe, before);
        assert!(app.adaptive.error.as_deref().unwrap().contains("region"));
    }

    #[test]
    fn magic_and_adaptive_follow_action_order_instead_of_worker_completion_order() {
        let mut app = fixture();
        let original = app.editor.recipe.clone();
        let revision = app.editor.revision;
        let context = egui::Context::default();
        let enclosure = RegionShape::Rectangle {
            min: [0.1, 0.1],
            max: [0.9, 0.9],
        };
        app.start_adaptive(1.0).unwrap();
        app.editor
            .set_tool(crate::edit_workspace::DrawingTool::MagicLasso);
        app.editor.start_magic(enclosure.clone(), &context);
        assert!(app.editor.magic_pending());
        // Even cancellation of the newer operation must not revive an older
        // ready reply. No changed recipe/revision can hide a missing guard here.
        app.editor.cancel_geometry();
        assert!(!app.editor.magic_pending());
        assert_eq!(app.editor.revision, revision);
        complete(&mut app);
        assert_eq!(app.editor.recipe, original);
        assert!(!app.editor.can_undo());
        assert!(
            app.adaptive
                .error
                .as_deref()
                .unwrap()
                .contains("superseded")
        );

        app.editor.start_magic(enclosure, &context);
        assert!(app.editor.magic_pending());
        assert!(app.start_adaptive(1.0).is_err());
        assert!(app.adaptive.pending.is_none());
        assert!(
            app.editor.magic_pending(),
            "Rejected Adaptive cancelled Magic"
        );
        assert_eq!(app.editor.recipe, original);
        app.editor.cancel_geometry();
        app.start_adaptive(1.0).unwrap();
        complete(&mut app);
        assert_ne!(
            app.editor.recipe, original,
            "The positive control must actually edit"
        );
        assert!(app.adaptive.error.is_none());
    }

    #[test]
    fn persisted_spatial_amount_works_without_analysis_and_keeps_other_scopes() {
        let mut app = fixture();
        app.start_adaptive(1.0).unwrap();
        complete(&mut app);
        let full = app.editor.recipe.clone();
        app.adaptive = AdaptiveState::default(); // reopen: no cached suggestion
        app.editor.before = true;
        app.set_spatial_amount(0.0).unwrap();
        assert!(!app.editor.before && !app.adaptive_busy());
        let image = &app.editor.loaded.as_ref().unwrap().image;
        assert_eq!(
            image.render_sdr16(&app.editor.recipe).unwrap(),
            image.render_sdr16(&DevelopmentRecipe::default()).unwrap(),
            "zero amount must exactly restore unmodified pixels"
        );
        assert_eq!(app.adaptive_snapshot()["spatial"]["amount"], 0.0);
        app.set_spatial_amount(0.37).unwrap();
        let partial = app.editor.recipe.clone();
        app.set_spatial_amount(1.0).unwrap();
        assert_eq!(app.editor.recipe, full);
        app.set_spatial_amount(0.37).unwrap();
        assert_eq!(
            app.editor.recipe, partial,
            "Amount must not compound after reopening"
        );
        select_bright_region(&mut app);
        let global_field = app.editor.recipe.adaptive_scope(None).unwrap().clone();
        assert!(
            app.set_spatial_amount(0.0).is_err(),
            "selected region must not edit the global field"
        );
        assert_eq!(
            app.editor.recipe.adaptive_scope(None).unwrap(),
            &global_field
        );
    }

    #[test]
    fn parameter_recalculation_is_explicit_and_snapshot_stays_compact() {
        let mut app = fixture();
        app.reconcile_adaptive_parameters();
        let parameters = AdaptiveParameters {
            balance: 0.2,
            local_contrast: 0.85,
            color: 0.65,
        };
        app.adaptive.parameters.as_mut().unwrap().value = parameters;
        assert_eq!(
            app.editor.recipe,
            DevelopmentRecipe::default(),
            "draft controls must not silently launch or change the photograph"
        );
        app.start_adaptive_parameters(1.0, AdaptiveIntent::Balance, parameters, false)
            .unwrap();
        assert!(app.set_spatial_amount(0.2).is_err());
        complete(&mut app);
        assert!(app.adaptive.error.is_none(), "{:?}", app.adaptive.error);
        assert_eq!(
            app.editor.recipe.adaptive_scope(None).unwrap().parameters,
            parameters
        );
        assert_eq!(
            app.editor.recipe.global,
            strehl_edit::Adjustments::default()
        );
        let snapshot = app.adaptive_snapshot();
        assert_eq!(
            snapshot["spatial"]["parameters"]["local_contrast"],
            serde_json::json!(0.85_f32)
        );
        let encoded = serde_json::to_vec(&snapshot).unwrap();
        assert!(
            encoded.len() < 16_384,
            "analysis snapshot duplicated spatial coefficients"
        );
        assert!(
            snapshot["analysis"].get("base").is_none()
                && snapshot["analysis"].get("suggested").is_none()
        );
        app.reconcile_adaptive_parameters();
        assert_eq!(app.adaptive.parameters.as_ref().unwrap().value, parameters);
        select_bright_region(&mut app);
        app.reconcile_adaptive_parameters();
        assert_eq!(
            app.adaptive.parameters.as_ref().unwrap().value,
            AdaptiveParameters::default(),
            "region must not inherit another scope's draft"
        );
    }
}
