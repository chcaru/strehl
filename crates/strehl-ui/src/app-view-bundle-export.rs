//! Independent-view archive delivery, separate from a developed photograph export.
use super::*;
impl StrehlApp {
    pub(super) fn view_bundle_source(&self) -> Option<PathBuf> {
        let result = self.result.as_ref()?;
        let run = self
            .catalog
            .runs
            .iter()
            .find(|run| run.owns_output(result))?;
        if run.status != "Saved"
            || run.settings.session.as_ref()?.manifest.mode
                != crate::session_workspace::SessionMode::IndependentViews
        {
            return None;
        }
        Some(if run.imported.is_some() {
            run.directory.clone()
        } else {
            run.directory.join("session-output")
        })
    }
    pub(super) fn start_view_bundle_export(&mut self, destination: PathBuf) -> anyhow::Result<()> {
        anyhow::ensure!(
            !self.picker_active()
                && self.job.is_none()
                && self.scan.is_none()
                && self.replay.is_none(),
            "Wait for the active operation"
        );
        let source = self
            .view_bundle_source()
            .ok_or_else(|| anyhow::anyhow!("Open a completed independent-view bundle first"))?;
        self.last_view_bundle_export = None;
        self.view_bundle_export = Some(jobs::spawn_reporting_task(
            "strehl-export-view-bundle",
            move |cancelled| {
                crate::session_import::export_view_bundle(&source, &destination, &cancelled)
            },
        ));
        self.error = None;
        self.status = "Copying and verifying the complete view bundle…".into();
        Ok(())
    }
    pub(super) fn poll_view_bundle_export(&mut self) {
        let Some(result) =
            self.view_bundle_export
                .as_ref()
                .and_then(|t| {
                    match t.receiver.try_recv() {
                Ok(result) => Some(result),
                Err(mpsc::TryRecvError::Empty) => None,
                Err(mpsc::TryRecvError::Disconnected) => Some(Err(if t.is_cancelled() {
                    "View bundle export cancelled; incomplete destination is not a completed bundle"
                } else {
                    "View bundle export worker ended"
                }
                .into())),
            }
                })
        else {
            return;
        };
        self.view_bundle_export = None;
        match result {
            Ok(path) => {
                self.status = format!("Exported complete view bundle to {}", path.display());
                self.last_view_bundle_export = Some(path);
            }
            Err(error) => {
                self.status = "View bundle was not exported".into();
                self.error = Some(error);
            }
        }
    }
    pub(super) fn view_bundle_export_action(&mut self, ui: &mut egui::Ui) {
        if self.view_bundle_source().is_none() {
            return;
        }
        if let Some(task) = &self.view_bundle_export {
            ui.label("Exporting view bundle…");
            if ui.button("Cancel bundle export").clicked() { task.cancel(); }
        } else if ui.add_enabled(!self.picker_active(), egui::Button::new("Export view bundle…"))
            .on_hover_text("Copy every bound photograph, linear master, focus map and receipt to a new folder. Original RAWs and unsaved edits are not copied.").clicked() {
            self.pick(Dialog::ViewBundleExport);
        }
    }
}
