//! Ordinary application state and worker pump, without a native window.
use super::*;
use anyhow::{Context, Result, ensure};
use std::{fs, io::Write};

pub(crate) fn validate_automation_launch(launch: &mut LaunchOptions) -> Result<()> {
    ensure!(
        !(launch.headless && launch.offscreen),
        "Choose headless control or offscreen rendering"
    );
    ensure!(
        !launch.metadata || (!launch.headless && launch.source.is_some()),
        "--metadata requires a GUI/offscreen --source bracket"
    );
    ensure!(
        !launch.offscreen || launch.screenshot.is_some(),
        "Offscreen rendering requires a screenshot path"
    );
    ensure!(
        launch.agent_grants.len() <= 32,
        "At most 32 --agent-grant directories are supported"
    );
    ensure!(
        launch.agent || (launch.agent_session_out.is_none() && launch.agent_grants.is_empty()),
        "Agent session and grant options require --agent or --headless"
    );
    for path in &mut launch.agent_grants {
        *path = path
            .canonicalize()
            .context("Resolve --agent-grant directory")?;
        ensure!(path.is_dir(), "--agent-grant requires a directory");
    }
    if let Some(path) = &mut launch.agent_session_out {
        *path = absolute_file(path)?;
        ensure!(
            !path.try_exists()?,
            "Session publication already exists; choose a fresh --agent-session-out path"
        );
    }
    if launch.headless {
        ensure!(
            launch.agent_session_out.is_some(),
            "--headless requires --agent-session-out JSON"
        );
        ensure!(
            launch.browse.is_none()
                && launch.screenshot.is_none()
                && launch.reveal_at_ms.is_none()
                && launch.screenshot_hover.is_none()
                && launch.screenshot_ranges.is_none(),
            "Headless mode does not open a browser or capture the desktop; use preview commands for images"
        );
        if launch.catalog.is_none() {
            launch.catalog = launch
                .agent_session_out
                .as_ref()
                .map(|p| p.with_extension("projects.json"));
        }
    }
    if launch.offscreen && launch.catalog.is_none() {
        launch.catalog = launch
            .screenshot
            .as_ref()
            .map(|p| p.with_extension("projects.json"));
    }
    if let Some(path) = &mut launch.catalog {
        *path = absolute_file(path)?;
        ensure!(
            Some(&*path) != launch.agent_session_out.as_ref(),
            "Catalog and session publication must be different files"
        );
        if launch.headless
            && let Some(default) = crate::workspace_history::default_path()
        {
            ensure!(
                absolute_file(&default).ok().as_ref() != Some(&*path),
                "Use a separate headless catalog, not the interactive desktop's projects.json"
            );
        }
    }
    Ok(())
}

fn absolute_file(path: &Path) -> Result<PathBuf> {
    let absolute = std::path::absolute(path)?;
    let name = absolute.file_name().context("Expected a file path")?;
    let parent = absolute
        .parent()
        .context("File needs a parent directory")?
        .canonicalize()
        .context("Create the parent directory before launching Strehl")?;
    Ok(parent.join(name))
}

pub(super) fn publish_session(path: &Path, descriptor: &Path) -> Result<()> {
    // Discovery pointer only: the secret remains in the protected session.
    let bytes = serde_json::to_vec_pretty(&serde_json::json!({
        "schema":1, "pid":std::process::id(), "session":descriptor,
        "build":option_env!("STREHL_BUILD_ID").unwrap_or("development")
    }))?;
    let mut file = fs::OpenOptions::new()
        .write(true)
        .create_new(true)
        .open(path)?;
    file.write_all(&bytes)?;
    file.write_all(b"\n")?;
    file.sync_all()?;
    Ok(())
}

struct CatalogLease(PathBuf);
impl CatalogLease {
    fn acquire(catalog: &Path) -> Result<Self> {
        let mut lock = catalog.as_os_str().to_os_string();
        lock.push(".headless-lock");
        let path = PathBuf::from(lock);
        let mut file = fs::OpenOptions::new().write(true).create_new(true).open(&path)
            .context("Headless catalog is already leased; use another catalog (a crashed process can leave its .headless-lock)")?;
        writeln!(file, "{}", std::process::id())?;
        Ok(Self(path))
    }
}
impl Drop for CatalogLease {
    fn drop(&mut self) {
        let _ = fs::remove_file(&self.0);
    }
}

pub(crate) fn run_headless(launch: LaunchOptions) -> Result<()> {
    ensure!(
        launch.headless && launch.agent,
        "Headless agent launch is required"
    );
    let _lease = CatalogLease::acquire(
        launch
            .catalog
            .as_deref()
            .context("Headless catalog required")?,
    )?;
    let mut app = StrehlApp::from_launch(4096, launch);
    let ctx = egui::Context::default();
    let started = Instant::now();
    loop {
        // Advance debounced-save time and drain texture deltas. No native runtime.
        let _ = ctx.run(
            egui::RawInput {
                time: Some(started.elapsed().as_secs_f64()),
                focused: false,
                ..Default::default()
            },
            |ctx| app.headless_tick(ctx),
        );
        if let Some(error) = app.agent_start_error() {
            anyhow::bail!(error.to_owned());
        }
        ensure!(
            app.agent_session_out.is_none() || started.elapsed() < Duration::from_secs(10),
            "Agent session did not become ready within 10 seconds"
        );
        if app.headless_shutdown {
            app.close_agent_session();
            return Ok(());
        }
        std::thread::sleep(Duration::from_millis(30));
    }
}

impl StrehlApp {
    fn headless_tick(&mut self, ctx: &egui::Context) {
        self.poll(ctx);
        self.poll_editing(ctx);
        self.poll_agent(ctx);
        self.observe_edits(ctx);
        if self
            .catalog_edit_pending
            .is_some_and(|time| time.elapsed() >= Duration::from_millis(300))
        {
            self.persist_catalog();
        }
    }

    pub(super) fn prepare_headless_shutdown(
        &mut self,
        ctx: &egui::Context,
    ) -> Result<serde_json::Value> {
        ensure!(
            self.headless,
            "Shutdown is available only for a headless session"
        );
        ensure!(
            self.job.is_none()
                && self.scan.is_none()
                && self.replay.is_none()
                && self.draft_job.is_none()
                && self.result_work.is_none()
                && self.pending_result.is_none()
                && self.editor.loading.is_none()
                && self.editor.developing.is_none()
                && self.editor.exporting.is_none()
                && self.editor.preset.is_none()
                && self.editor.saving.is_none()
                && !self.editor.magic_pending()
                && !self.presets_busy()
                && !self.photo_history_busy()
                && !self.agent_read_pending()
                && !self.camera_metadata.is_loading()
                && !self.picker_active()
                && self.adaptive_snapshot()["analyzing"] != true,
            "Strehl still has work in progress; cancel stacking if needed, then read state and retry shutdown"
        );
        self.editor.commit_edit();
        self.commit_recipe_edit();
        self.observe_edits(ctx);
        ensure!(
            self.flush_presets(ctx)? && self.flush_photo_history(ctx)?,
            "Saving history; read state and retry shutdown"
        );
        self.editor.ensure_saved_on_close()?;
        self.catalog.save()?;
        self.catalog_edit_pending = None;
        self.headless_shutdown = true;
        Ok(
            serde_json::json!({"state":"shutdown_accepted","saved":true,"warning":self.editor.error}),
        )
    }
}

#[cfg(test)]
#[path = "app-headless-tests.rs"]
mod tests;
