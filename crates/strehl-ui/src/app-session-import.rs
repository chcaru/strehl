//! Product opening for completed CLI directories. Validation never grants RAW access.
use super::*;
impl StrehlApp {
    pub(super) fn start_completed_import(
        &mut self,
        directory: PathBuf,
        parent: Option<crate::workspace_history::NodeId>,
    ) -> anyhow::Result<()> {
        anyhow::ensure!(
            self.job.is_none()
                && self.scan.is_none()
                && self.replay.is_none()
                && !self.picker_active(),
            "Wait for the active operation"
        );
        anyhow::ensure!(
            parent.is_none_or(|id| self.catalog.node(id).is_some_and(|n| n.stack.is_none())),
            "Choose a project or folder"
        );
        self.editor.ensure_saved_on_close()?;
        let directory = std::fs::canonicalize(directory)?;
        if let Some(run) = self
            .catalog
            .runs
            .iter()
            .find(|r| r.directory == directory)
            .cloned()
        {
            self.reopen_run(run);
            return Ok(());
        }
        let task = jobs::spawn_task("strehl-import-completed", move |cancelled| {
            crate::session_import::load(&directory, &cancelled)
        });
        self.session_import = Some((self.epoch, parent, task));
        self.status = "Verifying completed CLI session and retained artifacts…".into();
        self.error = None;
        Ok(())
    }
    pub(super) fn poll_completed_import(&mut self) {
        let Some(result) =
            self.session_import
                .as_ref()
                .and_then(|(_, _, t)| match t.receiver.try_recv() {
                    Ok(value) => Some(value),
                    Err(mpsc::TryRecvError::Empty) => None,
                    Err(mpsc::TryRecvError::Disconnected) => Some(Err(if t.is_cancelled() {
                        "Completed-session import cancelled"
                    } else {
                        "Completed-session import worker ended"
                    }
                    .into())),
                })
        else {
            return;
        };
        let (epoch, parent, _) = self.session_import.take().unwrap();
        if epoch != self.epoch {
            return;
        }
        match result.and_then(|run| {
            self.catalog
                .import_completed_run(parent, run.clone())
                .map_err(|e| e.to_string())?;
            Ok(run)
        }) {
            Ok(run) => {
                self.persist_catalog();
                self.reopen_run(run);
                self.process_view = true;
                self.sidebar = Some(workspace::Sidebar::Projects);
            }
            Err(error) => {
                self.status = "Completed session was not imported".into();
                self.error = Some(format!("{error:#}"));
                if self.screenshot.is_some() {
                    self.screenshot_error = self.error.clone();
                }
            }
        }
    }
}
