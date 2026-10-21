//! A bounded, inspectable starting point for development, shared with agents.
use super::*;
use serde_json::{Value, json};
use std::sync::Arc;
use strehl_edit::{AdaptiveIntent, AdaptiveSuggestion, DevelopmentRecipe, LinearImage};

struct PendingAdaptive {
    path: PathBuf,
    image: Arc<LinearImage>,
    revision: u64,
    strength: f32,
    target_region: Option<String>,
    magic_generation: u64,
    task: Task<AdaptiveSuggestion>,
}

struct AppliedAdaptive {
    image: Arc<LinearImage>,
    suggestion: AdaptiveSuggestion,
    strength: f32,
    applied: DevelopmentRecipe,
}

#[derive(Default)]
pub(super) struct AdaptiveState {
    path: Option<PathBuf>,
    pending: Option<PendingAdaptive>,
    applied: Option<AppliedAdaptive>,
    error: Option<String>,
}

impl StrehlApp {
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
        anyhow::ensure!(
            strength.is_finite() && (0.0..=1.0).contains(&strength),
            "Adaptive amount must be between 0 and 1"
        );
        anyhow::ensure!(
            self.adaptive.pending.is_none(),
            "Adaptive is already analyzing"
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
        if self.adaptive.path.as_ref() == Some(&path)
            && let Some(applied) = self.adaptive.applied.as_mut()
            && applied.applied == self.editor.recipe
            && Arc::ptr_eq(&applied.image, &loaded.image)
            && applied.suggestion.target_region == target_region
            && applied.suggestion.intent == intent
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
        self.adaptive.pending = Some(PendingAdaptive {
            path,
            image: Arc::clone(&image),
            revision: self.editor.revision,
            strength,
            target_region,
            magic_generation: self.editor.magic_generation(),
            task: jobs::spawn_task("strehl-adaptive-develop", move |cancelled| {
                anyhow::ensure!(
                    !cancelled.load(std::sync::atomic::Ordering::Relaxed),
                    "Adaptive cancelled"
                );
                match worker_target.as_deref() {
                    Some(id) => strehl_edit::analyze_adaptive_region(&image, &recipe, id, intent),
                    None => strehl_edit::analyze_adaptive(&image, &recipe),
                }
            }),
        });
        Ok(())
    }

    pub(super) fn poll_adaptive(&mut self, ctx: &egui::Context) {
        if self.adaptive.path != self.editor.path {
            self.adaptive = AdaptiveState::default();
        }
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
        if self.adaptive.pending.is_some() {
            ctx.request_repaint_after(Duration::from_millis(30));
        }
    }

    pub(super) fn adaptive_snapshot(&self) -> Value {
        let applied = self.adaptive.applied.as_ref();
        json!({
            "analyzing": self.adaptive.pending.is_some(),
            "amount": applied.map(|value| value.strength),
            "current": applied.is_some_and(|value| value.applied == self.editor.recipe
                && value.suggestion.target_region == self.editor.selected
                && self.editor.loaded.as_ref().is_some_and(|loaded| Arc::ptr_eq(&value.image, &loaded.image))),
            "analysis": applied.map(|value| &value.suggestion),
            "error": self.adaptive.error,
            "method": "Bounded scene measurements produce editable controls; no learned model or generated detail."
        })
    }

    pub(super) fn adaptive_panel(&mut self, ui: &mut egui::Ui) {
        let magic_pending = self.editor.magic_pending();
        let scope_enabled = self.editor.selected.as_ref().is_none_or(|id| {
            self.editor
                .recipe
                .regions
                .iter()
                .any(|region| &region.id == id && region.enabled)
        });
        let current = self.adaptive.applied.as_ref().is_some_and(|applied| {
            applied.applied == self.editor.recipe
                && applied.suggestion.target_region == self.editor.selected
                && applied.suggestion.intent == AdaptiveIntent::Balance
                && self
                    .editor
                    .loaded
                    .as_ref()
                    .is_some_and(|loaded| Arc::ptr_eq(&applied.image, &loaded.image))
        });
        ui.vertical(|ui| {
            if ui
                .add_enabled_ui(self.adaptive.pending.is_none() && !current && scope_enabled && !magic_pending, |ui| {
                    ui.add_sized([ui.available_width(), 27.0], egui::Button::new(
                        if self.editor.selected.is_some() { "Balance region" } else { "Auto develop" }
                    ))
                }).inner
                .on_hover_text(
                    "Measure the selected area and balance light and color while protecting highlights. Every control stays editable; Undo restores your previous treatment.",
                )
                .on_disabled_hover_text(if magic_pending {
                    "Finish or cancel Magic selection before using Adaptive."
                } else if !scope_enabled {
                    "Enable this region before balancing its light and color."
                } else if current {
                    "Use Amount to adjust this treatment. After other edits, Adaptive can analyze the changed photograph again."
                } else {
                    "The current photograph is being analyzed."
                })
                .clicked()
                && let Err(error) = self.start_adaptive(1.0)
            {
                self.adaptive.error = Some(error.to_string());
            }
            if self.editor.selected.is_some() && ui
                .add_enabled_ui(self.adaptive.pending.is_none() && scope_enabled && !magic_pending, |ui| {
                    ui.add_sized([ui.available_width(), 25.0], egui::Button::new("Balance highlights"))
                }).inner
                .on_hover_text("Compress bright light in this region and diagnose available tonal variation. Already-clipped texture cannot be recreated.")
                .on_disabled_hover_text(if magic_pending { "Finish or cancel Magic selection before using Adaptive." } else if !scope_enabled { "Enable this region before balancing its highlights." } else { "Analysis is already running." })
                .clicked()
                && let Err(error) = self.start_highlight_restore(1.0)
            {
                self.adaptive.error = Some(error.to_string());
            }
            if self.adaptive.pending.is_some() {
                theme::caption(ui, "Reading light and color…");
            }
        });
        if let Some(applied) = &mut self.adaptive.applied {
            let current = applied.applied == self.editor.recipe
                && applied.suggestion.target_region == self.editor.selected
                && self
                    .editor
                    .loaded
                    .as_ref()
                    .is_some_and(|loaded| Arc::ptr_eq(&applied.image, &loaded.image));
            if current {
                let response = ui
                    .add_enabled_ui(!magic_pending, |ui| {
                        super::editing::controls::slider(
                            ui,
                            "Amount",
                            &mut applied.strength,
                            0.0..=1.0,
                            1.0,
                            2,
                            "",
                        )
                    })
                    .inner
                    .on_disabled_hover_text(
                        "Finish or cancel Magic selection before changing Adaptive Amount.",
                    );
                if response.changed() {
                    match applied.suggestion.recipe_at(applied.strength) {
                        Ok(recipe) => {
                            self.editor.recipe = recipe.clone();
                            applied.applied = recipe;
                            self.editor.before = false;
                        }
                        Err(error) => self.adaptive.error = Some(error.to_string()),
                    }
                }
                if applied.suggestion.changes.is_empty() {
                    theme::caption(
                        ui,
                        "No useful change found for this area. Controls are unchanged.",
                    );
                } else {
                    theme::caption(
                        ui,
                        &format!("{} adjustments", applied.suggestion.changes.len(),),
                    );
                }
                if applied.suggestion.intent == AdaptiveIntent::RestoreHighlights {
                    theme::caption(ui, &applied.suggestion.highlights.assessment);
                }
            } else {
                theme::caption(ui, "Edits changed · Adaptive can analyze them again");
            }
            egui::CollapsingHeader::new("What changed")
                .id_salt("adaptive-explanation")
                .show(ui, |ui| {
                    theme::caption(
                        ui,
                        &format!(
                            "Full-amount median linear light {:.3} → {:.3}",
                            applied.suggestion.stats.luminance_percentiles[2],
                            applied.suggestion.after_stats.luminance_percentiles[2]
                        ),
                    );
                    if applied.suggestion.changes.is_empty() {
                        ui.label("The measured scene did not call for further adjustments.");
                    }
                    for change in &applied.suggestion.changes {
                        ui.horizontal(|ui| {
                            ui.label(&change.control);
                            ui.label(
                                RichText::new(format!(
                                    "{:+.2} → {:+.2}",
                                    change.before, change.after
                                ))
                                .monospace()
                                .color(ACCENT),
                            );
                        });
                        theme::caption(ui, &change.reason);
                    }
                    for limitation in &applied.suggestion.limitations {
                        theme::caption(ui, limitation);
                    }
                    theme::caption(
                        ui,
                        &format!(
                            "{} scene samples · controls shown at full amount",
                            applied.suggestion.stats.sample_count
                        ),
                    );
                });
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
        assert_ne!(
            app.editor.recipe.global, original.global,
            "fixture must exercise a real edit"
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
            app.editor.recipe, old_recipe,
            "new uniform image should be unchanged"
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
}
