//! A bounded, inspectable starting point for development, shared with agents.
use super::*;
use serde_json::{Value, json};
use std::sync::Arc;
use strehl_edit::{AdaptiveSuggestion, DevelopmentRecipe, LinearImage};

struct PendingAdaptive {
    path: PathBuf,
    image: Arc<LinearImage>,
    revision: u64,
    strength: f32,
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
        anyhow::ensure!(
            strength.is_finite() && (0.0..=1.0).contains(&strength),
            "Adaptive amount must be between 0 and 1"
        );
        anyhow::ensure!(
            self.adaptive.pending.is_none(),
            "Adaptive is already analyzing"
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
        if self.adaptive.path.as_ref() == Some(&path)
            && let Some(applied) = self.adaptive.applied.as_mut()
            && applied.applied == self.editor.recipe
            && Arc::ptr_eq(&applied.image, &loaded.image)
        {
            let recipe = applied.suggestion.recipe_at(strength)?;
            self.editor.replace(recipe.clone())?;
            applied.applied = recipe;
            applied.strength = strength;
            self.adaptive.error = None;
            return Ok(());
        }
        let image = Arc::clone(&loaded.image);
        self.editor.commit_edit();
        let recipe = self.editor.recipe.clone();
        self.adaptive.path = Some(path.clone());
        self.adaptive.error = None;
        self.adaptive.pending = Some(PendingAdaptive {
            path,
            image: Arc::clone(&image),
            revision: self.editor.revision,
            strength,
            task: jobs::spawn_task("strehl-adaptive-develop", move |cancelled| {
                anyhow::ensure!(
                    !cancelled.load(std::sync::atomic::Ordering::Relaxed),
                    "Adaptive cancelled"
                );
                strehl_edit::analyze_adaptive(&image, &recipe)
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
                || self
                    .editor
                    .loaded
                    .as_ref()
                    .is_none_or(|loaded| !Arc::ptr_eq(&pending.image, &loaded.image))
            {
                self.adaptive.error =
                    Some("Edits changed during analysis. Run Adaptive again.".into());
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
                && self.editor.loaded.as_ref().is_some_and(|loaded| Arc::ptr_eq(&value.image, &loaded.image))),
            "analysis": applied.map(|value| &value.suggestion),
            "error": self.adaptive.error,
            "method": "Bounded scene measurements produce editable controls; no learned model or generated detail."
        })
    }

    pub(super) fn adaptive_panel(&mut self, ui: &mut egui::Ui) {
        let current = self
            .adaptive
            .applied
            .as_ref()
            .is_some_and(|applied| applied.applied == self.editor.recipe);
        ui.horizontal(|ui| {
            if ui
                .add_enabled(
                    self.adaptive.pending.is_none() && !current,
                    egui::Button::new("Adaptive"),
                )
                .on_hover_text(
                    "Measure this photograph and suggest restrained light and color adjustments. Every control stays editable; Undo restores your previous treatment.",
                )
                .on_disabled_hover_text(if current {
                    "Use Amount to adjust this treatment. After other edits, Adaptive can analyze the changed photograph again."
                } else {
                    "The current photograph is being analyzed."
                })
                .clicked()
                && let Err(error) = self.start_adaptive(1.0)
            {
                self.adaptive.error = Some(error.to_string());
            }
            if self.adaptive.pending.is_some() {
                theme::caption(ui, "Reading light and color…");
            } else {
                theme::caption(ui, "Scene-aware light & color");
            }
        });
        if let Some(applied) = &mut self.adaptive.applied {
            let current = applied.applied == self.editor.recipe;
            if current {
                let response = ui.add(
                    egui::Slider::new(&mut applied.strength, 0.0..=1.0)
                        .text("Amount")
                        .fixed_decimals(2),
                );
                if response.changed() {
                    match applied.suggestion.recipe_at(applied.strength) {
                        Ok(recipe) => {
                            self.editor.recipe = recipe.clone();
                            applied.applied = recipe;
                        }
                        Err(error) => self.adaptive.error = Some(error.to_string()),
                    }
                }
            } else {
                theme::caption(ui, "Edits changed · Adaptive can analyze them again");
            }
            egui::CollapsingHeader::new("What changed")
                .id_salt("adaptive-explanation")
                .show(ui, |ui| {
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
}
