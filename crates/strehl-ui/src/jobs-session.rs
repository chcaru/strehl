//! The opt-in session worker owns its manifest and an isolated engine process.
use super::*;
use crate::session_workspace::{SessionDraft, SessionMode};

pub(crate) fn scan_session(draft: SessionDraft) -> Task<StackScan> {
    spawn_task("strehl-session-scan", move |cancelled| {
        draft.validate()?;
        ensure!(!cancelled.load(Ordering::Relaxed), "Session scan cancelled");
        let resolved = draft.manifest.resolve_from(draft.first_directory())?;
        let total_bytes = resolved.frames.iter().try_fold(0u64, |sum, frame| {
            sum.checked_add(frame.bytes)
                .context("Session byte count overflow")
        })?;
        ensure!(!cancelled.load(Ordering::Relaxed), "Session scan cancelled");
        Ok(StackScan {
            directory: resolved.passes[0].directories[0].clone(),
            frames: resolved
                .frames
                .into_iter()
                .map(|frame| FrameFile {
                    path: frame.path,
                    bytes: frame.bytes,
                })
                .collect(),
            total_bytes,
        })
    })
}

pub(super) fn session_command(
    request: &RenderRequest,
    manifest: &Path,
    output: &Path,
) -> Result<Command> {
    let session = request
        .settings
        .session
        .as_ref()
        .context("Session recipe missing")?;
    session.validate()?;
    ensure!(
        !request.settings.temporal_energy
            && request.settings.frame_limit.is_none()
            && !request.settings.auto_exposure
            && !request.settings.crop_to_coverage
            && !request.settings.binned,
        "Session rendering requires full resolution and its own pass coverage; temporal smoothing, capture limits and automatic exposure are unavailable"
    );
    ensure!(
        request.recipe.is_none(),
        "Session renders start from merge settings; develop their saved photographs afterwards"
    );
    let mut command = crate::engine::command(&request.executable)?;
    command
        .args(["session", "stack"])
        .arg(manifest)
        .arg("--out-dir")
        .arg(output)
        .arg("--memory-limit-gib")
        .arg(session.memory_limit_gib.to_string())
        .arg("--threads")
        .arg(
            request
                .worker_threads
                .unwrap_or_else(|| MachineResources::detect().maximum_workers())
                .to_string(),
        )
        .arg("--resampler")
        .arg(request.settings.resampler.cli_name());
    if let Some(value) = request.exposure_ev {
        command.arg(format!("--exposure={value}"));
    }
    if let Some(value) = request.pyramid_gate {
        command.arg(format!("--pyramid-gate={value}"));
    }
    if let Some(value) = request.settings.pyramid_bands {
        command.arg(format!("--pyramid-bands={value}"));
    }
    if let Some(value) = request.settings.pyramid_exponent {
        command.arg(format!("--pyramid-exponent={value}"));
    }
    if let Some(value) = request.settings.pyramid_sharpen {
        command.arg(format!("--pyramid-sharpen={value}"));
    }
    if request.settings.binned {
        command.arg("--binned");
    }
    configure_render_environment(&mut command, request, std::env::vars_os());
    #[cfg(windows)]
    {
        use std::os::windows::process::CommandExt;
        command.creation_flags(0x0800_0000);
    }
    Ok(command)
}

fn write_new(path: &Path, value: &impl serde::Serialize) -> Result<()> {
    let mut file = OpenOptions::new().write(true).create_new(true).open(path)?;
    serde_json::to_writer_pretty(&mut file, value)?;
    file.write_all(b"\n")?;
    file.sync_all()?;
    Ok(())
}

fn validate_completed_sources(output: &Path, session: &SessionDraft) -> Result<()> {
    let identities: Vec<strehl_cli::session_input::SourceIdentity> = serde_json::from_reader(
        File::open(output.join("source-identities.json"))
            .context("Reading the engine's completed source census")?,
    )?;
    ensure!(
        identities.len() == session.sources.len()
            && identities
                .iter()
                .zip(&session.sources)
                .all(|(actual, expected)| {
                    actual.path == expected.path
                        && actual.bytes == expected.bytes
                        && actual.modified_unix_nanos.map(u128::from) == expected.modified_ns
                        && actual.sha256.len() == 64
                        && actual.sha256.bytes().all(|b| b.is_ascii_hexdigit())
                }),
        "The engine consumed different sources from this run's snapshot; reload the session before rendering"
    );
    let completion: serde_json::Value = serde_json::from_reader(
        File::open(output.join("completed.json"))
            .context("Reading the engine's completion receipt")?,
    )?;
    ensure!(
        completion["schema"] == "strehl.session-completion.v1",
        "Session engine completion receipt is unsupported"
    );
    Ok(())
}

pub(super) fn run_session_render(
    request: &RenderRequest,
    cancelled: &Arc<AtomicBool>,
    sender: &SyncSender<RenderEvent>,
) -> RenderOutcome {
    let mut job_directory = None;
    let result = (|| -> Result<RenderOutcome> {
        validate_settings(request)?;
        let session = request
            .settings
            .session
            .as_ref()
            .context("Session recipe missing")?;
        session.validate()?;
        let resolved = session.manifest.resolve_from(session.first_directory())?;
        let scan = StackScan {
            directory: resolved.passes[0].directories[0].clone(),
            frames: resolved
                .frames
                .iter()
                .map(|frame| FrameFile {
                    path: frame.path.clone(),
                    bytes: frame.bytes,
                })
                .collect(),
            total_bytes: 0,
        };
        ensure!(
            !session.sources.is_empty()
                && session.sources == crate::workspace_history::source_identities(&scan),
            "Session sources changed since import; reload the session before rendering"
        );
        ensure!(
            !cancelled.load(Ordering::Relaxed),
            "Session cancelled before launch"
        );
        let output_parent = resolved.ensure_output_outside_sources(&request.output_parent)?;
        fs::create_dir_all(&output_parent).context("Creating the session destination")?;
        let output_parent = resolved.ensure_output_outside_sources(&output_parent)?;
        let directory = create_job_directory(&output_parent)?;
        job_directory = Some(directory.clone());
        let directory = fs::canonicalize(directory)?;
        resolved.ensure_output_outside_sources(&directory)?;
        let manifest = directory.join("session-manifest.json");
        write_new(&manifest, &session.manifest)?;
        write_new(&directory.join("session-recipe.json"), session)?;
        // The engine reserves this fresh directory; the UI must not create it.
        let engine_output = directory.join("session-output");
        let outputs: Vec<_> = if session.manifest.mode == SessionMode::Layers {
            (0..session.manifest.passes.len())
                .map(|i| {
                    engine_output
                        .join(format!("layer-{:02}", i + 1))
                        .join("photograph.tiff")
                })
                .collect()
        } else {
            vec![engine_output.join("photograph.tiff")]
        };
        let displayed = if session.manifest.mode == SessionMode::Layers {
            session.manifest.primary_pass.unwrap_or(0)
        } else {
            0
        };
        let output = outputs[displayed].clone();
        let log = directory.join("render.log");
        let mut command = session_command(request, &manifest, &engine_output)?;
        let shared_cache =
            resolved.ensure_output_outside_sources(&output_parent.join(".strehl-session-cache"))?;
        command.arg("--cache").arg(&shared_cache);
        let mut log_file = OpenOptions::new().write(true).create_new(true).open(&log)?;
        writeln!(
            log_file,
            "Strehl desktop multi-stack session\nProgram: {:?}\nArguments: {:?}\nManifest and resource settings are immutable snapshots. Sources remain read-only.\n",
            command.get_program(),
            command.get_args().collect::<Vec<_>>()
        )?;
        command
            .stdout(Stdio::from(log_file.try_clone()?))
            .stderr(Stdio::from(log_file))
            .stdin(Stdio::null())
            .current_dir(&directory);
        let _ = sender.try_send(RenderEvent::Started {
            directory: directory.clone(),
            output: output.clone(),
            log: log.clone(),
        });
        match run_process(&mut command, cancelled, sender, &log)? {
            ProcessResult::Cancelled => Ok(RenderOutcome::Cancelled { directory }),
            ProcessResult::Exited(status) => {
                ensure!(
                    status.success(),
                    "Session engine exited with {status}; full output: {}",
                    log.display()
                );
                ensure!(
                    !cancelled.load(Ordering::Relaxed),
                    "Session cancelled before publication"
                );
                validate_completed_sources(&engine_output, session)?;
                for photograph in &outputs {
                    ensure!(
                        photograph.is_file() && photograph.metadata()?.len() > 0,
                        "Session photograph was not completed: {}",
                        photograph.display()
                    );
                    let master = photograph.with_file_name("master.tiff");
                    ensure!(
                        master.is_file() && master.metadata()?.len() > 0,
                        "Session linear master was not completed: {}",
                        master.display()
                    );
                    crate::preview::validate_tiff(photograph)
                        .context("Validating the complete session photograph")?;
                    let linear = strehl_edit::load_tiff(&master)
                        .context("Validating the session linear master")?;
                    ensure!(
                        linear.origin == strehl_edit::ImageOrigin::SceneLinear
                            && linear.baseline.is_some(),
                        "Session master lacks its scene-linear display baseline"
                    );
                    ensure!(
                        (linear.width, linear.height) == image::image_dimensions(photograph)?,
                        "Session master and photograph dimensions differ"
                    );
                    ensure!(
                        !cancelled.load(Ordering::Relaxed),
                        "Session cancelled during output validation"
                    );
                }
                write_new(
                    &directory.join("session-outputs.json"),
                    &serde_json::json!({"version":1,"photographs":outputs,"initial_photograph":output,"completion_report":engine_output.join("completed.json")}),
                )?;
                Ok(RenderOutcome::Completed {
                    directory,
                    output,
                    log,
                })
            }
        }
    })();
    match result {
        Ok(outcome) => outcome,
        Err(_) if cancelled.load(Ordering::Relaxed) && job_directory.is_some() => {
            RenderOutcome::Cancelled {
                directory: job_directory.unwrap(),
            }
        }
        Err(error) => RenderOutcome::Failed {
            directory: job_directory,
            message: format!("{error:#}"),
        },
    }
}

#[cfg(test)]
#[path = "jobs-session-tests.rs"]
mod tests;
