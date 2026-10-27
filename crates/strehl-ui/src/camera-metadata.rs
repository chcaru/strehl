//! Read-only bracket metadata, cached for native exploration. The bundled CLI owns parsing.
//! One owned child is retained through cancellation before another starts.
use crate::jobs::{self, FrameFile, Task};
use anyhow::{Context, Result, bail, ensure};
use eframe::egui;
use serde_json::Value;
use std::{
    fs::{self, File},
    io::Read,
    path::{Path, PathBuf},
    process::{Command, Stdio},
    sync::{
        atomic::{AtomicBool, Ordering},
        mpsc::TryRecvError,
    },
    time::{Duration, UNIX_EPOCH},
};

const MAX_JSON_BYTES: u64 = 4 * 1024 * 1024;
const MAX_BRACKET_JSON_BYTES: u64 = 64 * 1024 * 1024;
#[path = "camera-metadata-view.rs"]
mod view;
// MCP returns both text and structured data. Keep one complete metadata payload
// well below the bridge's 8 MiB reply budget; refuse rather than truncate it.
const MAX_AGENT_REPORT_BYTES: usize = 2 * 1024 * 1024;

#[derive(Clone)]
struct Target {
    frame: FrameFile,
    output: PathBuf,
}
#[derive(Clone)]
struct Request {
    token: u64,
    target: BracketTarget,
}
#[derive(Clone)]
struct BracketTarget {
    epoch: u64,
    directory: PathBuf,
    frames: Vec<FrameFile>,
    output: PathBuf,
}
impl BracketTarget {
    fn same_sources(&self, other: &Self) -> bool {
        self.epoch == other.epoch
            && self.directory == other.directory
            && self.frames.len() == other.frames.len()
            && self
                .frames
                .iter()
                .zip(&other.frames)
                .all(|(a, b)| a.path == b.path && a.bytes == b.bytes)
    }
}
#[derive(Debug)]
struct BracketInspection {
    view: view::BracketView,
    sources: Vec<(PathBuf, SourceStamp)>,
    json: PathBuf,
}
struct Work {
    token: u64,
    epoch: u64,
    task: Task<BracketInspection>,
}

#[derive(Clone, Debug, PartialEq, Eq)]
struct SourceStamp {
    bytes: u64,
    modified_ns: Option<String>,
}
impl SourceStamp {
    fn read(path: &Path) -> Result<Self> {
        let meta = fs::metadata(path).with_context(|| format!("Reading {}", path.display()))?;
        ensure!(meta.is_file(), "The selected source is not a file");
        Ok(Self {
            bytes: meta.len(),
            modified_ns: meta
                .modified()
                .ok()
                .and_then(|t| t.duration_since(UNIX_EPOCH).ok())
                .map(|t| t.as_nanos().to_string()),
        })
    }
}

#[derive(Debug)]
struct Status {
    label: String,
    reason: Option<String>,
}
impl Status {
    fn parse(value: &Value) -> Result<Self> {
        let code = value["status"]
            .as_str()
            .context("Missing metadata read status")?;
        let label = match code {
            "present" => "Available",
            "absent" => "Not recorded",
            "unsupported" => "Unsupported layout",
            "malformed" => "Malformed metadata",
            "io_error" => "File read error",
            _ => bail!("Unknown metadata read status: {code}"),
        };
        Ok(Self {
            label: label.into(),
            reason: value["reason"].as_str().map(str::to_owned),
        })
    }
}
#[derive(Debug)]
struct OpticalRow {
    label: &'static str,
    raw_setting: String,
    maker_setting: String,
    table: String,
}
#[derive(Debug)]
struct Summary {
    camera: String,
    firmware: String,
    lens: String,
    focus: Status,
    optical: Status,
    focus_rows: Vec<(&'static str, String)>,
    optical_rows: Vec<OpticalRow>,
}
#[derive(Debug)]
struct Inspection {
    summary: Summary,
    report: Value,
    source: PathBuf,
    stamp: SourceStamp,
    json: PathBuf,
}

fn text(value: &Value) -> String {
    match value {
        Value::Null => "Not recorded".into(),
        Value::String(s) => s.clone(),
        _ => value.to_string(),
    }
}
fn header(facts: &Value, key: &str) -> String {
    text(&facts[key]["value"])
}
fn fallback(primary: &Value, secondary: &Value) -> String {
    text(if primary.is_null() {
        secondary
    } else {
        primary
    })
}
fn parse_report(report: &Value, source: &Path, stamp: &SourceStamp) -> Result<Summary> {
    ensure!(
        report["schema"] == "strehl-sony-focus-audit-v1",
        "Unsupported camera metadata report"
    );
    ensure!(report["file_count"] == 1, "Expected one selected capture");
    let frames = report["frames"]
        .as_array()
        .context("Missing report frames")?;
    ensure!(
        frames.len() == 1 && frames[0]["index"] == 0,
        "Report does not identify one capture"
    );
    parse_frame(&frames[0], source, stamp)
}
fn parse_frame(frame: &Value, source: &Path, stamp: &SourceStamp) -> Result<Summary> {
    let path: PathBuf = serde_json::from_value(frame["path"].clone())?;
    ensure!(path == source, "Report belongs to a different capture");
    ensure!(
        frame["file_identity"]["byte_length"].as_u64() == Some(stamp.bytes)
            && frame["file_identity"]["modified_unix_ns"].as_str() == stamp.modified_ns.as_deref(),
        "Source identity changed during metadata inspection"
    );
    let focus = Status::parse(frame)?;
    let optical = &frame["optical"];
    ensure!(
        optical["schema"] == "strehl-sony-optical-facts-v1",
        "The bundled engine did not include optical metadata; rebuild the desktop with its matching engine"
    );
    let optical_status = Status::parse(optical)?;
    let meta = &frame["metadata"];
    let facts = &optical["facts"];
    if frame["status"] == "present" {
        ensure!(meta.is_object(), "Missing AF metadata fields");
    }
    if optical["status"] == "present" {
        ensure!(facts.is_object(), "Missing optical metadata fields");
    }
    let mut focus_rows = Vec::new();
    if frame["status"] == "present" {
        focus_rows.push(("Focus position code", text(&meta["coarse_focus_position"])));
        focus_rows.push((
            "Scalars A / B (raw units)",
            format!(
                "{} / {}",
                text(&meta["scalars_raw"][0]),
                text(&meta["scalars_raw"][1])
            ),
        ));
        focus_rows.push((
            "Stored AF grid",
            format!(
                "{} × {} · {} records",
                text(&meta["grid"]["width"]),
                text(&meta["grid"]["height"]),
                text(&meta["grid"]["record_count"])
            ),
        ));
        focus_rows.push((
            "Section sequence IDs",
            match meta["section_sequences_agree"].as_bool() {
                Some(true) => "Match; measurement freshness unknown".into(),
                Some(false) => "Differ; measurement freshness unknown".into(),
                None => "Unknown".into(),
            },
        ));
    }
    let mut optical_rows = Vec::new();
    if optical["status"] == "present" {
        for (label, key, maker) in [
            ("Shading", "shading", "maker_shading_setting"),
            ("Color fringing", "chromatic_aberration", "maker_ca_setting"),
            ("Distortion", "distortion", "maker_distortion_setting"),
        ] {
            let table = match facts[key]["table"]["samples"].as_array() {
                None => "Not recorded".into(),
                Some(samples) => {
                    let values = samples
                        .iter()
                        .map(|v| v.as_i64().context("Invalid signed optical table"))
                        .collect::<Result<Vec<_>>>()?;
                    ensure!(
                        !values.is_empty() && values.iter().all(|v| i16::try_from(*v).is_ok()),
                        "Invalid signed optical table"
                    );
                    format!(
                        "{} samples: {} to {} raw",
                        values.len(),
                        values.iter().min().unwrap(),
                        values.iter().max().unwrap()
                    )
                }
            };
            optical_rows.push(OpticalRow {
                label,
                raw_setting: text(&facts[key]["setting"]["value"]),
                maker_setting: header(facts, maker),
                table,
            });
        }
    }
    Ok(Summary {
        camera: fallback(&facts["model"]["value"], &meta["model"]),
        firmware: fallback(&facts["software"]["value"], &meta["software"]),
        lens: fallback(
            &facts["lens_model"]["value"],
            &meta["optical_identity"]["lens_model"],
        ),
        focus,
        optical: optical_status,
        focus_rows,
        optical_rows,
    })
}

fn bounded_read(path: &Path, maximum: u64) -> Result<Vec<u8>> {
    let file = File::open(path).with_context(|| format!("Opening {}", path.display()))?;
    ensure!(
        file.metadata()?.len() <= maximum,
        "Metadata report is unexpectedly large"
    );
    let mut bytes = Vec::new();
    file.take(maximum + 1).read_to_end(&mut bytes)?;
    ensure!(
        bytes.len() as u64 <= maximum,
        "Metadata report grew beyond its size limit"
    );
    Ok(bytes)
}
fn command(source: &Path, json: &Path) -> Result<Command> {
    let executable =
        crate::engine::bundled_executable().context("Finding the bundled metadata engine")?;
    let mut command = crate::engine::command(&executable)?;
    command
        .arg("focus")
        .arg("inspect")
        .arg(source)
        .arg("--optical")
        .arg("--records")
        .arg("--out")
        .arg(json);
    jobs::remove_experimental_overrides(&mut command, std::env::vars_os());
    #[cfg(windows)]
    {
        use std::os::windows::process::CommandExt;
        command.creation_flags(0x0800_0000);
    }
    Ok(command)
}
fn run_child(mut command: Command, cancelled: &AtomicBool, log: &Path) -> Result<()> {
    ensure!(
        !cancelled.load(Ordering::Relaxed),
        "Metadata inspection cancelled"
    );
    let output = fs::OpenOptions::new()
        .write(true)
        .create_new(true)
        .open(log)?;
    command
        .stdin(Stdio::null())
        .stdout(Stdio::from(output.try_clone()?))
        .stderr(Stdio::from(output));
    let mut child = jobs::OwnedChild(command.spawn().context("Starting the metadata engine")?);
    loop {
        ensure!(
            !cancelled.load(Ordering::Relaxed),
            "Metadata inspection cancelled"
        );
        if let Some(status) = child.0.try_wait()? {
            ensure!(
                status.success(),
                "Metadata inspection failed ({status}). Details: {}",
                log.display()
            );
            return Ok(());
        }
        std::thread::sleep(Duration::from_millis(25));
    }
}
fn inspect_using(
    target: &Target,
    cancelled: &AtomicBool,
    build: impl FnOnce(&Path, &Path) -> Result<Command>,
) -> Result<Inspection> {
    ensure!(
        !cancelled.load(Ordering::Relaxed),
        "Metadata inspection cancelled"
    );
    let source = fs::canonicalize(&target.frame.path).context("Finding the selected capture")?;
    let before = SourceStamp::read(&source)?;
    ensure!(
        before.bytes == target.frame.bytes,
        "The source changed since import. Reopen the bracket before inspecting it"
    );
    let parent = jobs::prepare_output_parent(
        source.parent().context("Source has no parent")?,
        &target.output,
    )?;
    let directory = jobs::create_job_directory(&parent)?;
    let json = directory.join("camera-metadata.json");
    run_child(
        build(&source, &json)?,
        cancelled,
        &directory.join("metadata.log"),
    )?;
    ensure!(
        before == SourceStamp::read(&source)?,
        "Source changed during metadata inspection. Refresh to read it again"
    );
    let report: Value = serde_json::from_slice(&bounded_read(&json, MAX_JSON_BYTES)?)?;
    let summary = parse_report(&report, &source, &before)?;
    ensure!(
        !cancelled.load(Ordering::Relaxed),
        "Metadata inspection cancelled"
    );
    Ok(Inspection {
        summary,
        report,
        source,
        stamp: before,
        json,
    })
}

/// Reuse the panel's exact bounded reader without changing panel or app state.
/// Reports are generated in the configured destination; no browser is opened.
pub(crate) fn read_agent_report(
    frame: FrameFile,
    output: PathBuf,
    cancelled: &AtomicBool,
) -> Result<Value> {
    read_agent_report_using(frame, output, cancelled, command)
}

fn read_agent_report_using(
    frame: FrameFile,
    output: PathBuf,
    cancelled: &AtomicBool,
    build: impl FnOnce(&Path, &Path) -> Result<Command>,
) -> Result<Value> {
    let target = Target {
        frame,
        output: output.join("metadata"),
    };
    agent_report_payload(inspect_using(&target, cancelled, build)?)
}

fn agent_report_payload(result: Inspection) -> Result<Value> {
    let log = result.json.with_file_name("metadata.log");
    let payload = serde_json::json!({
        "source": result.source,
        "source_identity": {"byte_length":result.stamp.bytes,"modified_unix_ns":result.stamp.modified_ns},
        "report": result.report,
        "reports": {"json":result.json,"log":log},
        "camera":result.summary.camera,"firmware":result.summary.firmware,"lens":result.summary.lens,
        "limitations": ["Size and modification time identify this read, not a whole-file hash.",
            "Stored AF values are not calibrated depth or proof of exposure-time freshness."]
    });
    ensure!(
        serde_json::to_vec(&payload)?.len() <= MAX_AGENT_REPORT_BYTES,
        "Metadata reply exceeds 2 MiB; complete saved reports: {}",
        payload["reports"]
    );
    Ok(payload)
}

fn inspect_bracket_using(
    target: &BracketTarget,
    cancelled: &AtomicBool,
    build: impl FnOnce(&Path, &Path) -> Result<Command>,
) -> Result<BracketInspection> {
    ensure!(
        !cancelled.load(Ordering::Relaxed),
        "Metadata inspection cancelled"
    );
    ensure!(
        !target.frames.is_empty() && target.frames.len() <= view::MAX_FRAMES,
        "Metadata supports 1 through {} imported captures",
        view::MAX_FRAMES
    );
    let input = fs::canonicalize(&target.directory).context("Finding the imported bracket")?;
    ensure!(input.is_dir(), "Imported bracket directory is unavailable");
    let sources = target
        .frames
        .iter()
        .map(|frame| -> Result<_> {
            let source = fs::canonicalize(&frame.path).context("Finding an imported capture")?;
            ensure!(
                source.parent() == Some(input.as_path()),
                "Imported source is outside this bracket"
            );
            let stamp = SourceStamp::read(&source)?;
            ensure!(
                stamp.bytes == frame.bytes,
                "The source changed since import. Reopen the bracket"
            );
            Ok((source, stamp))
        })
        .collect::<Result<Vec<_>>>()?;
    let parent = jobs::prepare_output_parent(&input, &target.output)?;
    let directory = jobs::create_job_directory(&parent)?;
    let json = directory.join("camera-metadata.json");
    run_child(
        build(&input, &json)?,
        cancelled,
        &directory.join("metadata.log"),
    )?;
    for (source, before) in &sources {
        ensure!(
            *before == SourceStamp::read(source)?,
            "Source changed during metadata inspection. Refresh to read it again"
        );
    }
    let report: Value = serde_json::from_slice(&bounded_read(&json, MAX_BRACKET_JSON_BYTES)?)?;
    let view = view::BracketView::from_report(&report, &sources)?;
    ensure!(
        !cancelled.load(Ordering::Relaxed),
        "Metadata inspection cancelled"
    );
    Ok(BracketInspection {
        view,
        sources,
        json,
    })
}

#[derive(Default)]
pub(crate) struct CameraMetadata {
    open: bool,
    token: u64,
    target: Option<BracketTarget>,
    pending: Option<Request>,
    work: Option<Work>,
    result: Option<BracketInspection>,
    error: Option<String>,
    view: view::ViewState,
}
impl CameraMetadata {
    pub(crate) fn is_loading(&self) -> bool {
        self.work.is_some() || self.pending.is_some()
    }
    pub(crate) fn open_bracket(
        &mut self,
        epoch: u64,
        directory: PathBuf,
        frames: Vec<FrameFile>,
        output: PathBuf,
        ctx: &egui::Context,
    ) {
        let target = BracketTarget {
            epoch,
            directory,
            frames,
            output: output.join("metadata"),
        };
        self.open = true;
        if self
            .target
            .as_ref()
            .is_some_and(|old| old.same_sources(&target))
            && (self.result.is_some()
                || self
                    .work
                    .as_ref()
                    .is_some_and(|work| work.token == self.token)
                || self.pending.is_some())
        {
            // Keep the existing read snapshot; an explicit refresh uses the latest destination.
            if let Some(previous) = &mut self.target {
                previous.output = target.output;
            }
            return;
        }
        self.target = Some(target);
        self.view = view::ViewState::default();
        self.refresh();
        self.poll(ctx);
    }
    fn refresh(&mut self) {
        self.cancel();
        self.pending = self.target.clone().map(|target| Request {
            token: self.token,
            target,
        });
        self.result = None;
        self.error = None;
    }
    fn cancel(&mut self) {
        self.token = self.token.wrapping_add(1);
        self.pending = None;
        if let Some(work) = &self.work {
            work.task.cancel();
        }
    }
    /// Final teardown only: wait until the reader has reaped its owned engine.
    /// Normal panel cancellation stays asynchronous through poll().
    pub(crate) fn retire(&mut self) {
        self.cancel();
        if let Some(work) = self.work.take() {
            // A result can already be queued. Drain through disconnection so
            // cancellation, completion and unwinding all retire the worker.
            while work.task.receiver.recv().is_ok() {}
        }
    }
    pub(crate) fn reset(&mut self) {
        self.cancel();
        self.open = false;
        self.target = None;
        self.result = None;
        self.error = None;
    }
    pub(crate) fn poll(&mut self, ctx: &egui::Context) {
        let completed = self
            .work
            .as_ref()
            .and_then(|work| match work.task.receiver.try_recv() {
                Ok(value) => Some(Some(value)),
                Err(TryRecvError::Disconnected) => Some(None),
                Err(TryRecvError::Empty) => None,
            });
        if let Some(value) = completed {
            let work = self.work.take().unwrap();
            if self.token == work.token
                && self
                    .target
                    .as_ref()
                    .is_some_and(|target| target.epoch == work.epoch)
            {
                match value {
                    Some(Ok(result)) => self.result = Some(result),
                    Some(Err(error)) => self.error = Some(error),
                    None => self.error = Some("Metadata read cancelled or interrupted.".into()),
                }
            }
        }
        if self.work.is_none()
            && let Some(request) = self.pending.take()
        {
            let ctx = ctx.clone();
            self.work = Some(Work {
                token: request.token,
                epoch: request.target.epoch,
                task: jobs::spawn_notifying_task(
                    "strehl-camera-metadata",
                    move |cancelled| {
                        inspect_bracket_using(&request.target, &cancelled, |source, json| {
                            let mut child = command(source, json)?;
                            // One extra entry detects directory growth without reading an unbounded new corpus.
                            child
                                .arg("--limit")
                                .arg((request.target.frames.len() + 1).to_string());
                            Ok(child)
                        })
                    },
                    move || ctx.request_repaint(),
                ),
            });
        }
    }
    pub(crate) fn show(&mut self, ctx: &egui::Context, selected: usize) -> Option<usize> {
        if !self.open {
            return None;
        }
        let mut open = self.open;
        let mut refresh = false;
        let mut cancel = false;
        let mut select = None;
        let safe = metadata_window_safe_rect(ctx);
        let style = ctx.style();
        let frame = egui::Frame::window(&style).fill(egui::Color32::from_rgb(249, 250, 252));
        // Window size controls address its body; leave room for both the frame
        // and title/close controls inside the application's unobstructed area.
        let title: egui::WidgetText = egui::RichText::new("Camera metadata")
            .color(egui::Color32::from_rgb(32, 42, 55))
            .text_style(egui::TextStyle::Heading)
            .into();
        // Match egui::Window's measured title row, including font ascent/leading;
        // the nominal font size is smaller than this row for some system fonts.
        let title_height = ctx
            .fonts_mut(|fonts| fonts.row_height(&egui::TextStyle::Heading.resolve(&style)))
            .max(style.spacing.interact_size.y)
            + frame.inner_margin.sum().y
            + frame.stroke.width;
        let decoration = frame.total_margin().sum() + egui::vec2(0.0, title_height);
        let maximum = (safe.size() - decoration).max(egui::Vec2::splat(1.0));
        let initial = maximum.min(egui::vec2(800.0, 760.0));
        let position = safe.min + (safe.size() - initial - decoration).max(egui::Vec2::ZERO) * 0.5;
        egui::Window::new(title).id(egui::Id::new("camera-metadata"))
            .open(&mut open).default_size(initial).default_pos(position)
            .min_size(maximum.min(egui::vec2(320.0, 180.0))).max_size(maximum)
            .constrain_to(safe).resizable(true).scroll([true, true])
            .frame(frame)
            .show(ctx,|ui| {
                ui.set_style(egui::Style {visuals:egui::Visuals::light(),..(*ui.style()).as_ref().clone()});
                if self.work.is_some() || self.pending.is_some() {ui.horizontal(|ui|{ui.spinner();ui.label("Reading metadata for the imported bracket…");cancel=ui.small_button("Cancel").clicked();});}
                if let Some(error)=&self.error {ui.colored_label(egui::Color32::from_rgb(160,65,20),error);}
                if let Some(result)=&self.result {
                    select=self.view.show(ui,&result.view,selected);
                    ui.collapsing("Read snapshot",|ui| {
                        ui.label(format!("{} captures · {}",result.sources.len(),result.json.display()));
                        if let Some((path,stamp))=result.sources.get(selected) {ui.label(path.display().to_string());ui.label(format!("{} bytes · modified {}",stamp.bytes,stamp.modified_ns.as_deref().unwrap_or("unavailable")));}
                        ui.small("Source size and modification time agreed before and after the read. This cached snapshot is not a whole-file hash. Refresh rereads the bracket.");
                    });
                }
                refresh=ui.add_enabled(self.work.is_none()&&self.pending.is_none(),egui::Button::new("Refresh bracket metadata")).clicked();
            });
        self.open = open;
        if !open || cancel {
            self.cancel();
        }
        if cancel {
            self.error = Some("Metadata inspection cancelled.".into());
        }
        if refresh {
            self.refresh();
            self.poll(ctx);
        }
        select
    }
}
fn metadata_window_safe_rect(ctx: &egui::Context) -> egui::Rect {
    let screen = ctx.content_rect();
    let dock = crate::window_chrome::dock_rect(ctx.viewport_rect());
    let minimum = egui::pos2(
        (screen.left() + crate::window_chrome::RAIL_WIDTH + 16.0).min(screen.right() - 1.0),
        (screen.top() + 12.0)
            .max(dock.bottom() + 8.0)
            .min(screen.bottom() - 1.0),
    );
    let maximum = (screen.max - egui::vec2(16.0, 16.0)).max(minimum + egui::Vec2::splat(1.0));
    egui::Rect::from_min_max(minimum, maximum)
}
fn status(ui: &mut egui::Ui, label: &str, status: &Status) {
    ui.strong(format!("{label}: {}", status.label));
    if let Some(reason) = &status.reason {
        ui.label(reason);
    }
}

#[cfg(test)]
#[path = "camera-metadata-tests.rs"]
mod tests;
