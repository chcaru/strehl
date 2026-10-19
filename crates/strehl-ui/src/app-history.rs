//! Undo belongs to user interaction, never to engine observations or output files.
use super::*;

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
enum Domain {
    View,
    Space,
    Projects,
    Recipe,
}
impl Domain {
    fn label(self) -> &'static str {
        match self {
            Self::View => "view",
            Self::Space => "space view",
            Self::Projects => "project edit",
            Self::Recipe => "settings",
        }
    }
}

#[derive(Clone, Debug, PartialEq)]
pub(super) struct Recipe {
    settings: jobs::RenderSettings,
    exposure: Option<f32>,
    gate: Option<f32>,
    workers: usize,
}
impl Recipe {
    pub(super) fn capture(controls: &Controls) -> Self {
        Self {
            settings: controls.settings.clone(),
            exposure: controls.exposure,
            gate: controls.gate,
            workers: controls.workers,
        }
    }
    fn apply(&self, controls: &mut Controls) {
        controls.settings = self.settings.clone();
        controls.exposure = self.exposure;
        controls.gate = self.gate;
        controls.workers = self.workers;
    }
}

#[derive(Default)]
pub(super) struct WorkspaceEdits {
    undo: Vec<Domain>,
    redo: Vec<Domain>,
    recipe_undo: Vec<Recipe>,
    recipe_redo: Vec<Recipe>,
    recipe_pending: Option<(Recipe, f64)>,
    view_revision: u64,
    space_revision: u64,
    project_revision: u64,
    view_depths: (usize, usize),
    space_depths: (usize, usize),
    project_depths: (usize, usize),
    view_commits: u64,
    space_commits: u64,
    project_commits: u64,
}
impl WorkspaceEdits {
    fn record(&mut self, domain: Domain) {
        self.undo.push(domain);
        if self.undo.len() > 64 {
            self.undo.remove(0);
        }
        self.redo.clear();
    }
    pub(super) fn changed_recipe(&mut self, before: Recipe, now: f64) {
        if let Some((_, time)) = &mut self.recipe_pending {
            *time = now;
        } else {
            self.recipe_pending = Some((before, now));
        }
    }
    pub(super) fn change_stack(&mut self) {
        self.undo.retain(|d| *d == Domain::Projects);
        self.redo.retain(|d| *d == Domain::Projects);
        self.recipe_undo.clear();
        self.recipe_redo.clear();
        self.recipe_pending = None;
        self.view_revision = 0;
        self.view_depths = (0, 0);
        self.view_commits = 0;
        self.space_revision = 0;
        self.space_depths = (0, 0);
        self.space_commits = 0;
    }
    fn synchronize(
        &mut self,
        domain: Domain,
        before: (usize, usize),
        after: (usize, usize),
        commits: u64,
    ) {
        if commits > 0 {
            for _ in 0..commits.min(64) {
                self.record(domain);
            }
        } else if after == (0, 0) {
            self.undo.retain(|d| *d != domain);
            self.redo.retain(|d| *d != domain);
        } else if before.0 > after.0 && after.1 == before.1 + before.0 - after.0 {
            for _ in 0..before.0 - after.0 {
                if let Some(i) = self.undo.iter().rposition(|d| *d == domain) {
                    self.undo.remove(i);
                    self.redo.push(domain);
                }
            }
        } else if after.0 > before.0 {
            let count = after.0 - before.0;
            if before.1 == after.1 + count {
                for _ in 0..count {
                    if let Some(i) = self.redo.iter().rposition(|d| *d == domain) {
                        self.redo.remove(i);
                    }
                    self.undo.push(domain);
                }
            } else {
                for _ in 0..count {
                    self.record(domain);
                }
            }
        }
    }
}

impl StrehlApp {
    fn commit_recipe_edit(&mut self) {
        if let Some((before, _)) = self.edits.recipe_pending.take()
            && before != Recipe::capture(&self.controls)
        {
            self.edits.recipe_undo.push(before);
            if self.edits.recipe_undo.len() > 64 {
                self.edits.recipe_undo.remove(0);
            }
            self.edits.recipe_redo.clear();
            self.edits.record(Domain::Recipe);
        }
    }
    pub(super) fn observe_edits(&mut self, ctx: &egui::Context) {
        let view = self.process_space.history_revision();
        if view != self.edits.view_revision {
            self.commit_recipe_edit();
            let depths = self.process_space.history_depths();
            let commits = self.process_space.history_commits();
            self.edits.synchronize(
                Domain::View,
                self.edits.view_depths,
                depths,
                commits.saturating_sub(self.edits.view_commits),
            );
            self.edits.view_revision = view;
            self.edits.view_depths = depths;
            self.edits.view_commits = commits;
        }
        let space = self.process_atlas.history_revision();
        if space != self.edits.space_revision {
            self.commit_recipe_edit();
            let depths = self.process_atlas.history_depths();
            let commits = self.process_atlas.history_commits();
            self.edits.synchronize(
                Domain::Space,
                self.edits.space_depths,
                depths,
                commits.saturating_sub(self.edits.space_commits),
            );
            self.edits.space_revision = space;
            self.edits.space_depths = depths;
            self.edits.space_commits = commits;
        }
        let projects = self.project_explorer.history_revision();
        if projects != self.edits.project_revision {
            self.commit_recipe_edit();
            let depths = self.project_explorer.history_depths();
            let commits = self.project_explorer.history_commits();
            self.edits.synchronize(
                Domain::Projects,
                self.edits.project_depths,
                depths,
                commits.saturating_sub(self.edits.project_commits),
            );
            self.edits.project_revision = projects;
            self.edits.project_depths = depths;
            self.edits.project_commits = commits;
        }
        if let Some((_, changed)) = self.edits.recipe_pending {
            if !ctx.input(|i| i.pointer.any_down()) && ctx.input(|i| i.time) - changed >= 0.3 {
                self.commit_recipe_edit();
            } else {
                ctx.request_repaint_after(Duration::from_millis(100));
            }
        }
    }
    fn domain_available(&self, domain: Domain, redo: bool) -> bool {
        match domain {
            Domain::View => {
                if redo {
                    self.process_space.can_redo()
                } else {
                    self.process_space.can_undo()
                }
            }
            Domain::Space => {
                if redo {
                    self.process_atlas.can_redo()
                } else {
                    self.process_atlas.can_undo()
                }
            }
            Domain::Projects => {
                self.job.is_none()
                    && if redo {
                        self.project_explorer.can_redo()
                    } else {
                        self.project_explorer.can_undo()
                    }
            }
            Domain::Recipe => {
                self.job.is_none()
                    && if redo {
                        !self.edits.recipe_redo.is_empty()
                    } else {
                        !self.edits.recipe_undo.is_empty()
                    }
            }
        }
    }
    pub(super) fn undo_label(&self, redo: bool) -> String {
        let list = if redo {
            &self.edits.redo
        } else {
            &self.edits.undo
        };
        let verb = if redo { "Redo" } else { "Undo" };
        list.last()
            .map_or(verb.into(), |d| format!("{verb} {}", d.label()))
    }
    pub(super) fn can_undo_edit(&self, redo: bool) -> bool {
        let list = if redo {
            &self.edits.redo
        } else {
            &self.edits.undo
        };
        !self.picker_active()
            && list
                .last()
                .is_some_and(|&domain| self.domain_available(domain, redo))
    }
    pub(super) fn undo_edit(&mut self, redo: bool) -> bool {
        if self.picker_active() {
            return false;
        }
        self.commit_recipe_edit();
        let list = if redo {
            &mut self.edits.redo
        } else {
            &mut self.edits.undo
        };
        let Some(domain) = list.last().copied() else {
            return false;
        };
        if !self.domain_available(domain, redo) {
            return false;
        }
        let changed = match domain {
            Domain::View => {
                if redo {
                    self.process_space.redo()
                } else {
                    self.process_space.undo()
                }
            }
            Domain::Space => {
                if redo {
                    self.process_atlas.redo()
                } else {
                    self.process_atlas.undo()
                }
            }
            Domain::Projects => {
                if redo {
                    self.project_explorer.redo(&mut self.catalog)
                } else {
                    self.project_explorer.undo(&mut self.catalog)
                }
            }
            Domain::Recipe => {
                let current = Recipe::capture(&self.controls);
                let recipe = if redo {
                    self.edits.recipe_redo.pop()
                } else {
                    self.edits.recipe_undo.pop()
                };
                if let Some(recipe) = recipe {
                    recipe.apply(&mut self.controls);
                    if redo {
                        self.edits.recipe_undo.push(current);
                    } else {
                        self.edits.recipe_redo.push(current);
                    }
                    self.save_active_draft();
                    true
                } else {
                    false
                }
            }
        };
        if changed {
            match domain {
                Domain::View => self.spatial_view = false,
                Domain::Space => self.spatial_view = true,
                Domain::Projects | Domain::Recipe => {}
            }
            if redo {
                self.edits.redo.pop();
                self.edits.undo.push(domain);
            } else {
                self.edits.undo.pop();
                self.edits.redo.push(domain);
            }
            self.edits.view_revision = self.process_space.history_revision();
            self.edits.space_revision = self.process_atlas.history_revision();
            self.edits.space_depths = self.process_atlas.history_depths();
            self.edits.space_commits = self.process_atlas.history_commits();
            self.edits.project_revision = self.project_explorer.history_revision();
            self.edits.view_depths = self.process_space.history_depths();
            self.edits.project_depths = self.project_explorer.history_depths();
            self.edits.view_commits = self.process_space.history_commits();
            self.edits.project_commits = self.project_explorer.history_commits();
            if matches!(domain, Domain::Projects | Domain::Recipe) {
                self.persist_catalog();
            }
            self.status = format!(
                "{} {}",
                if redo { "Restored" } else { "Undid" },
                domain.label()
            );
        }
        changed
    }
    pub(super) fn undo_shortcuts(&mut self, ctx: &egui::Context) {
        // Dismiss menus before any panel sees Escape. Otherwise a menu painted
        // later loses the key to the photo reset; one painted earlier closes
        // itself but leaves the same key available to reset the photo as well.
        if egui::Popup::is_any_open(ctx)
            && ctx.input_mut(|i| i.consume_key(egui::Modifiers::NONE, egui::Key::Escape))
        {
            egui::Popup::close_all(ctx);
            return;
        }
        if self.spatial_view
            && !self.picker_active()
            && ctx.input_mut(|i| i.consume_key(egui::Modifiers::NONE, egui::Key::Escape))
        {
            self.spatial_view = false;
            self.process_view = true;
            return;
        }
        // wants_keyboard_input also includes focused tree rows, checkboxes and
        // buttons. Only an actual text editor owns native text Undo/Redo.
        let text_editor_focused = ctx
            .memory(|m| m.focused())
            .is_some_and(|id| egui::TextEdit::load_state(ctx, id).is_some());
        if text_editor_focused || self.picker_active() {
            return;
        }
        let command = egui::Modifiers::COMMAND;
        if !egui::Popup::is_any_open(ctx)
            && ctx.input_mut(|i| i.consume_key(command, egui::Key::Enter))
        {
            self.start_render();
            ctx.request_repaint();
            return;
        }
        let redo = ctx.input_mut(|i| {
            i.consume_key(command | egui::Modifiers::SHIFT, egui::Key::Z)
                || i.consume_key(command, egui::Key::Y)
        });
        let undo = !redo && ctx.input_mut(|i| i.consume_key(command, egui::Key::Z));
        if redo || undo {
            self.undo_edit(redo);
        }
    }
}
