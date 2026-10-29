//! Child-local observation axes are never mixed with parent capture identities.
use super::{MAX_FRAME_OBSERVATIONS, PipelineProgress, Stage};
use serde::{Deserialize, Serialize};

#[derive(Clone, Debug, PartialEq, Eq, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
pub(crate) struct ViewProgress {
    schema: String,
    pub index: usize,
    pub count: usize,
    pub name: String,
    pub source_offset: usize,
    pub source_count: usize,
    pub parent_total: usize,
}
impl ViewProgress {
    pub(crate) fn parent_frame(&self, local: usize) -> Option<usize> {
        (local < self.source_count).then(|| self.source_offset + local)
    }
    pub(crate) fn local_frame(&self, parent: usize) -> Option<usize> {
        parent
            .checked_sub(self.source_offset)
            .filter(|&i| i < self.source_count)
    }
    pub(crate) fn label(&self) -> String {
        format!(
            "View {} / {} · {} · {} captures in this view · parent captures {}–{} of {}",
            self.index + 1,
            self.count,
            self.name,
            self.source_count,
            self.source_offset + 1,
            self.source_offset + self.source_count,
            self.parent_total
        )
    }
    fn valid(&self) -> bool {
        self.schema == "strehl.ui-view-progress.v1"
            && self.count > 0
            && self.count <= 64
            && self.index < self.count
            && !self.name.trim().is_empty()
            && self.name.len() <= 512
            && !self.name.chars().any(char::is_control)
            && self.source_count > 0
            && self.parent_total <= MAX_FRAME_OBSERVATIONS
            && self
                .source_offset
                .checked_add(self.source_count)
                .is_some_and(|end| {
                    end <= self.parent_total
                        && (self.index + 1 != self.count || end == self.parent_total)
                })
            && (self.index != 0 || self.source_offset == 0)
    }
}
impl PipelineProgress {
    /// Known independent-view jobs must not interpret child events as ordinary
    /// captures if the initial context was lost from a bounded live-log read.
    pub(crate) fn expect_view_progress(&mut self) {
        self.view_expected = true;
        self.view_observations_missing = true;
    }
    pub(crate) fn active_view(&self) -> Option<&ViewProgress> {
        (self.stage <= Stage::Rendering)
            .then_some(self.view.as_ref())
            .flatten()
    }
    pub(crate) fn parent_frame(&self, local: usize) -> Option<usize> {
        self.view
            .as_ref()
            .map_or(Some(local), |view| view.parent_frame(local))
    }
    pub(crate) fn parent_pair(&self, pair: [usize; 2]) -> Option<[usize; 2]> {
        Some([self.parent_frame(pair[0])?, self.parent_frame(pair[1])?])
    }
    fn reset_view_observations(&mut self, view: Option<ViewProgress>, missing: bool) {
        let diagnostic_epoch = self.diagnostic_epoch.wrapping_add(1);
        *self = Self {
            view,
            view_observations_missing: missing,
            view_expected: true,
            diagnostic_epoch,
            ..Self::default()
        };
    }
    pub(super) fn view_gap(&mut self) {
        if self.view_expected || self.view.is_some() {
            self.reset_view_observations(self.view.clone(), true);
        }
    }
    pub(super) fn view_context(&mut self, text: &str) {
        if self.stage > Stage::Rendering {
            return;
        }
        let Ok(next) = serde_json::from_str::<ViewProgress>(text) else {
            self.reset_view_observations(self.view.clone(), true);
            return;
        };
        let ordered = self.view.as_ref().is_none_or(|old| {
            next.parent_total == old.parent_total
                && next.count == old.count
                && next.index > old.index
                && next.source_offset >= old.source_offset + old.source_count
                && (self.view_observations_missing
                    || next.index == old.index + 1
                        && next.source_offset == old.source_offset + old.source_count)
        });
        if !next.valid() || !ordered {
            self.reset_view_observations(self.view.clone(), true);
            return;
        }
        self.reset_view_observations(Some(next.clone()), false);
        self.frames_total = Some(next.source_count);
        self.record(next.label());
    }
}

#[cfg(test)]
#[path = "pipeline-view-tests.rs"]
mod tests;
