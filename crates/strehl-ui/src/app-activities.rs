//! Activity adapters for the work this window runs (Studio 2 P5 stage 1).
//! Read-only: each reports what an owner already holds. Stage 2 keeps an
//! `Activities` registry on `StrehlApp`, calls `report_activities` once a
//! frame and adds `activities_value` to the agent snapshot.
#![allow(dead_code, reason = "the shell calls these once a frame in P5 stage 2")]
use super::*;
use crate::activity::{
    ActionId, Activities, ActivityKind, ActivityStatus, CancelMode, Lane, metadata_status,
    render_status,
};

impl StrehlApp {
    /// Report every activity this window owns. `render_eta` comes from the
    /// render's `EtaTracker` (stage 2 keeps it beside the job).
    pub(super) fn report_activities(
        &self,
        activities: &mut Activities,
        render_eta: Option<Duration>,
    ) {
        if let Some(job) = &self.job {
            let stack = self.pending_stack.or(self.active_stack);
            let run = stack
                .and_then(|id| self.catalog.latest_run(id))
                .filter(|run| run.status == "Stacking");
            let name = stack
                .and_then(|id| self.catalog.node(id))
                .map_or_else(|| "this stack".to_owned(), |node| node.name.clone());
            let key = run.map_or_else(
                || "render".to_owned(),
                |run| run.directory.to_string_lossy().into_owned(),
            );
            activities.report(render_status(
                &key,
                &format!("Stack · {name}"),
                stack,
                &self.progress,
                job.is_cancelling(),
                self.started,
                render_eta,
                run.map(|run| run.log.clone()),
            ));
        }
        if let Some((phase, path)) = self.export_phase() {
            let file = path
                .file_name()
                .map(|n| n.to_string_lossy().into_owned())
                .unwrap_or_default();
            activities.report(
                ActivityStatus::new(
                    ActivityKind::Export,
                    &path.to_string_lossy(),
                    format!("Export · {file}"),
                    Lane::Background,
                )
                .with_phase(match phase {
                    1 => "Preparing the version",
                    2 => "Writing the file",
                    _ => "Recording the export",
                })
                .with_progress(Some(u64::from(phase.saturating_sub(1))), Some(3))
                .with_cancel(if phase == 2 {
                    CancelMode::Cooperative
                } else {
                    CancelMode::None
                }),
            );
        }
        if self.view_bundle_export.is_some() {
            activities.report(
                ActivityStatus::new(
                    ActivityKind::ViewBundle,
                    "view-bundle",
                    ActivityKind::ViewBundle.label(),
                    Lane::Background,
                )
                .with_phase("Copying and verifying the complete bundle")
                .with_cancel(CancelMode::Cooperative),
            );
        }
        if let Some((epoch, _, _)) = &self.session_import {
            activities.report(
                ActivityStatus::new(
                    ActivityKind::Import,
                    &format!("session-import:{epoch}"),
                    ActivityKind::Import.label(),
                    Lane::Background,
                )
                .with_phase("Verifying the session's files")
                .with_cancel(CancelMode::Cooperative),
            );
        }
        if let Some(status) = metadata_status(&self.camera_metadata) {
            activities.report(status);
        }
        self.capture.report_activities(activities);
    }

    /// The agent snapshot's additive `activities` key (plan 11): current
    /// activities and the newest history entries.
    pub(super) fn activities_value(activities: &Activities) -> serde_json::Value {
        activities.public(Instant::now(), 16)
    }

    /// What a finished render leaves in the history.
    pub(super) fn render_outcome_note(
        stack: Option<crate::workspace_history::NodeId>,
        title: &str,
        outcome: &jobs::RenderOutcome,
        took: Option<Duration>,
        unix: u64,
    ) -> crate::activity::HistoryEntry {
        let (state, summary, action, log) = match outcome {
            jobs::RenderOutcome::Completed { output, log, .. } => (
                "done",
                "Stack saved".to_owned(),
                Some(ActionId::Reveal {
                    path: output.clone(),
                }),
                Some(log.clone()),
            ),
            jobs::RenderOutcome::Cancelled { .. } => {
                ("stopped", "Cancelled".to_owned(), None, None)
            }
            jobs::RenderOutcome::Failed { message, .. } => (
                "needs_you",
                message.clone(),
                stack.map(|stack| ActionId::Retry { stack }),
                None,
            ),
        };
        crate::activity::HistoryEntry {
            kind: ActivityKind::Stack,
            title: title.to_owned(),
            stack,
            outcome: state.into(),
            summary,
            finished: unix,
            took_seconds: took.map(|d| d.as_secs_f64()),
            action,
            log,
        }
    }
}

#[cfg(test)]
#[path = "app-activities-tests.rs"]
mod tests;
