//! Bound saved-output selection, shared by picker and local control.
use super::*;
impl StrehlApp {
    pub(super) fn select_session_output(&mut self, index: usize) -> anyhow::Result<()> {
        anyhow::ensure!(
            self.job.is_none()
                && self.scan.is_none()
                && self.replay.is_none()
                && !self.picker_active(),
            "Wait for the active operation"
        );
        let current = self
            .result
            .as_ref()
            .ok_or_else(|| anyhow::anyhow!("Open a completed session first"))?;
        let run = self
            .catalog
            .runs
            .iter()
            .find(|run| run.owns_output(current))
            .cloned()
            .ok_or_else(|| anyhow::anyhow!("Saved output provenance is unavailable"))?;
        let mode = run
            .settings
            .session
            .as_ref()
            .ok_or_else(|| anyhow::anyhow!("This result has no session outputs"))?;
        let prefix = crate::session_workspace::output_prefix(mode.manifest.mode)
            .ok_or_else(|| anyhow::anyhow!("This session has only one photograph"))?;
        anyhow::ensure!(
            run.status == "Saved" && index < mode.manifest.passes.len(),
            "Session output index is outside this completed run"
        );
        let root = if run.imported.is_some() {
            run.directory.clone()
        } else {
            run.directory.join("session-output")
        };
        let target = root.join(format!("{prefix}-{:02}/photograph.tiff", index + 1));
        anyhow::ensure!(
            self.session_ui.layers.get(index) == Some(&target) && run.owns_output(&target),
            "Session output does not belong to this saved directory"
        );
        self.editor.ensure_saved_on_close()?;
        let directory = run.directory.clone();
        let task = jobs::spawn_task("strehl-select-session-output", move |cancelled| {
            crate::session_import::validate_selected_output(&run, &target, &cancelled)?;
            Ok(target)
        });
        self.session_output_selection = Some((self.epoch, directory, task));
        self.error = None;
        self.status = "Verifying the selected saved photograph…".into();
        Ok(())
    }
    pub(super) fn poll_session_output_selection(&mut self) {
        let Some(result) = self
            .session_output_selection
            .as_ref()
            .and_then(|(_, _, t)| match t.receiver.try_recv() {
                Ok(result) => Some(result),
                Err(mpsc::TryRecvError::Empty) => None,
                Err(mpsc::TryRecvError::Disconnected) => {
                    Some(Err("Session output selection cancelled".into()))
                }
            })
        else {
            return;
        };
        let (epoch, directory, _) = self.session_output_selection.take().unwrap();
        if epoch != self.epoch {
            return;
        }
        match result.and_then(|path| {
            self.commit_session_output(&directory, path)
                .map_err(|e| e.to_string())
        }) {
            Ok(()) => {}
            Err(error) => {
                self.error = Some(error);
                self.status = "Saved photograph was not changed".into();
            }
        }
    }
    fn commit_session_output(&mut self, directory: &Path, path: PathBuf) -> anyhow::Result<()> {
        let run = self
            .catalog
            .runs
            .iter_mut()
            .find(|run| run.directory == directory)
            .ok_or_else(|| anyhow::anyhow!("Saved session is no longer available"))?;
        anyhow::ensure!(
            run.status == "Saved" && run.owns_output(&path),
            "Selected photograph no longer belongs to this saved run"
        );
        let previous = std::mem::replace(&mut run.output, path.clone());
        if let Err(error) = self.catalog.save() {
            self.catalog
                .runs
                .iter_mut()
                .find(|run| run.directory == directory)
                .unwrap()
                .output = previous;
            return Err(error);
        }
        if let Some(expected) = &mut self.expected_run
            && expected.directory == directory
        {
            expected.output = path.clone();
        }
        self.result = Some(path.clone());
        self.open_result(path);
        self.status = "Opened the selected saved photograph".into();
        Ok(())
    }
}
