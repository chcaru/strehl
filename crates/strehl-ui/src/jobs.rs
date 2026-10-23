//! Background file work and an owned CLI child. No processing runs on the UI thread.

use std::fs::{self, File, OpenOptions};
use std::io::{Read, Write};
use std::path::{Path, PathBuf};
use std::process::{Child, Command, ExitStatus, Stdio};
use std::sync::atomic::{AtomicBool, AtomicU64, Ordering};
use std::sync::mpsc::{self, Receiver, SyncSender};
use std::sync::{Arc, OnceLock};
use std::thread::{self, JoinHandle};
use std::time::{Duration, SystemTime, UNIX_EPOCH};

use anyhow::{Context, Result, bail, ensure};

use crate::pipeline::Utf8LogDecoder;

static NEXT_JOB: AtomicU64 = AtomicU64::new(0);
const EVENT_CAPACITY: usize = 96;
const LOG_CHUNK: usize = 8 * 1024;
const LOG_READS_PER_TICK: usize = 64;
const LOG_RETRY: Duration = Duration::from_millis(5);

/// Available execution capacity. This controls pool limits only: it never
/// changes the engine's canonical reduction partition or image settings.
#[derive(Clone, Copy, Debug)]
pub(crate) struct MachineResources {
    pub logical_processors: usize,
    pub physical_memory_bytes: Option<u64>,
}

impl MachineResources {
    pub(crate) fn detect() -> Self {
        static MACHINE: OnceLock<MachineResources> = OnceLock::new();
        *MACHINE.get_or_init(|| Self {
            logical_processors: thread::available_parallelism().map_or(1, usize::from),
            physical_memory_bytes: physical_memory_bytes(),
        })
    }

    pub(crate) fn maximum_workers(self) -> usize {
        self.logical_processors.clamp(1, 1024)
    }
}

#[cfg(windows)]
fn physical_memory_bytes() -> Option<u64> {
    use windows_sys::Win32::System::SystemInformation::{GlobalMemoryStatusEx, MEMORYSTATUSEX};
    // MEMORYSTATUSEX contains only integers; zero is valid for each field.
    let mut memory: MEMORYSTATUSEX = unsafe { std::mem::zeroed() };
    memory.dwLength = std::mem::size_of::<MEMORYSTATUSEX>() as u32;
    // The call fills this owned, correctly sized structure synchronously.
    let read = unsafe { GlobalMemoryStatusEx(&mut memory) };
    (read != 0 && memory.ullTotalPhys > 0).then_some(memory.ullTotalPhys)
}

#[cfg(not(windows))]
fn physical_memory_bytes() -> Option<u64> {
    // Unknown is not zero capacity; other platforms still use their actual
    // available CPU count without inventing a memory budget.
    None
}

pub struct Task<T> {
    pub receiver: Receiver<Result<T, String>>,
    cancelled: Arc<AtomicBool>,
}

impl<T> Task<T> {
    /// Signal cooperative cancellation without releasing this worker's lane.
    /// Keep polling the receiver until it disconnects before starting a
    /// replacement: a codec already inside a decode may need time to return.
    pub(crate) fn cancel(&self) {
        self.cancelled.store(true, Ordering::Relaxed);
    }

    pub(crate) fn is_cancelled(&self) -> bool {
        self.cancelled.load(Ordering::Relaxed)
    }
}

impl<T> Drop for Task<T> {
    fn drop(&mut self) {
        self.cancelled.store(true, Ordering::Relaxed);
    }
}

pub(crate) fn spawn_task<T: Send + 'static>(
    name: &str,
    work: impl FnOnce(Arc<AtomicBool>) -> Result<T> + Send + 'static,
) -> Task<T> {
    let (sender, receiver) = mpsc::sync_channel(1);
    let cancelled = Arc::new(AtomicBool::new(false));
    let worker_cancelled = Arc::clone(&cancelled);
    let errors = sender.clone();
    if let Err(error) = thread::Builder::new().name(name.into()).spawn(move || {
        let result = work(Arc::clone(&worker_cancelled)).map_err(|error| format!("{error:#}"));
        if !worker_cancelled.load(Ordering::Relaxed) {
            let _ = sender.send(result);
        }
    }) {
        let _ = errors.send(Err(format!("Starting background work: {error}")));
    }
    Task {
        receiver,
        cancelled,
    }
}

struct CompletionNotice<T> {
    sender: Option<SyncSender<Result<T, String>>>,
    notify: Arc<dyn Fn() + Send + Sync>,
}

impl<T> Drop for CompletionNotice<T> {
    fn drop(&mut self) {
        // Notification promises a readable result OR a disconnected channel.
        // Drop the sole sender first, including during cancellation/unwinding.
        drop(self.sender.take());
        (self.notify)();
    }
}

/// Like `spawn_task`, with exactly one completion notice after publication.
/// The receiver needs no polling timer: a failed/cancelled/panicking worker
/// also notifies, after its channel becomes readable or disconnected.
pub(crate) fn spawn_notifying_task<T: Send + 'static>(
    name: &str,
    work: impl FnOnce(Arc<AtomicBool>) -> Result<T> + Send + 'static,
    notify: impl Fn() + Send + Sync + 'static,
) -> Task<T> {
    let (sender, receiver) = mpsc::sync_channel(1);
    let cancelled = Arc::new(AtomicBool::new(false));
    let worker_cancelled = Arc::clone(&cancelled);
    let notify: Arc<dyn Fn() + Send + Sync> = Arc::new(notify);
    let worker_notify = Arc::clone(&notify);
    let started = thread::Builder::new().name(name.into()).spawn(move || {
        let completion = CompletionNotice {
            sender: Some(sender),
            notify: worker_notify,
        };
        let result = work(Arc::clone(&worker_cancelled)).map_err(|error| format!("{error:#}"));
        if !worker_cancelled.load(Ordering::Relaxed) {
            let _ = completion.sender.as_ref().unwrap().send(result);
        }
    });
    if started.is_err() {
        // The failed spawn has already dropped its closure and sole sender.
        // No CompletionNotice was constructed, so this is the only notice.
        notify();
    }
    Task {
        receiver,
        cancelled,
    }
}

#[cfg(test)]
#[path = "jobs-worker-tests.rs"]
mod worker_tests;

#[derive(Clone, Debug)]
pub struct FrameFile {
    pub path: PathBuf,
    pub bytes: u64,
}

#[derive(Clone, Debug)]
pub struct StackScan {
    pub directory: PathBuf,
    pub frames: Vec<FrameFile>,
    pub total_bytes: u64,
}

pub fn scan_stack(directory: PathBuf) -> Task<StackScan> {
    spawn_task("strehl-scan", move |cancelled| scan(&directory, &cancelled))
}

fn scan(directory: &Path, cancelled: &AtomicBool) -> Result<StackScan> {
    let directory = canonical_directory(directory)?;
    let mut frames = Vec::new();
    let mut total_bytes = 0_u64;
    for entry in fs::read_dir(&directory).context("Reading the stack folder")? {
        ensure!(!cancelled.load(Ordering::Relaxed), "Folder scan cancelled");
        let entry = entry.context("Reading a folder entry")?;
        let path = entry.path();
        if !path
            .extension()
            .is_some_and(|extension| extension.to_string_lossy().eq_ignore_ascii_case("arw"))
        {
            continue;
        }
        let metadata = entry
            .metadata()
            .with_context(|| format!("Reading {}", path.display()))?;
        if !metadata.is_file() {
            continue;
        }
        total_bytes = total_bytes
            .checked_add(metadata.len())
            .context("Stack byte count overflow")?;
        frames.push(FrameFile {
            path,
            bytes: metadata.len(),
        });
    }
    // Match the CLI's filename order, including case-sensitive Path ordering.
    frames.sort_by(|left, right| left.path.cmp(&right.path));
    ensure!(!frames.is_empty(), "This folder contains no .arw frames");
    Ok(StackScan {
        directory,
        frames,
        total_bytes,
    })
}

#[derive(Clone, Copy, Debug, Default, PartialEq, Eq, serde::Serialize, serde::Deserialize)]
pub enum Resampler {
    Nearest,
    Bilinear,
    #[default]
    CatmullRom,
    ClampedCatmull,
    Lanczos2,
    Lanczos3,
}

impl Resampler {
    pub const ALL: [Self; 6] = [
        Self::CatmullRom,
        Self::ClampedCatmull,
        Self::Lanczos3,
        Self::Lanczos2,
        Self::Bilinear,
        Self::Nearest,
    ];

    pub fn label(self) -> &'static str {
        match self {
            Self::Nearest => "Nearest neighbour",
            Self::Bilinear => "Bilinear",
            Self::CatmullRom => "Catmull–Rom · default",
            Self::ClampedCatmull => "Clamped Catmull–Rom",
            Self::Lanczos2 => "Lanczos 2",
            Self::Lanczos3 => "Lanczos 3",
        }
    }

    pub fn cli_name(self) -> &'static str {
        match self {
            Self::Nearest => "nearest",
            Self::Bilinear => "bilinear",
            Self::CatmullRom => "catmull-rom",
            Self::ClampedCatmull => "clamped-catmull",
            Self::Lanczos2 => "lanczos2",
            Self::Lanczos3 => "lanczos3",
        }
    }
}

/// Controls consumed by the shipping pyramid backend. Omitted numeric values
/// deliberately leave the engine's measured defaults in charge.
#[derive(Clone, Debug, PartialEq, serde::Serialize, serde::Deserialize)]
#[serde(default)]
pub struct RenderSettings {
    pub pyramid_bands: Option<usize>,
    pub pyramid_exponent: Option<f32>,
    pub pyramid_sharpen: Option<f32>,
    pub resampler: Resampler,
    pub binned: bool,
    pub correct_lateral_ca: bool,
    pub crop_to_coverage: bool,
    /// The first N captures in filename order. None keeps the whole bracket.
    pub frame_limit: Option<usize>,
    pub auto_exposure: bool,
    /// An optional second pass writes a centrality rank, not a quality score.
    pub confidence_map: bool,
}

impl Default for RenderSettings {
    fn default() -> Self {
        Self {
            pyramid_bands: None,
            pyramid_exponent: None,
            pyramid_sharpen: None,
            resampler: Resampler::default(),
            binned: false,
            correct_lateral_ca: true,
            crop_to_coverage: false,
            frame_limit: None,
            auto_exposure: false,
            confidence_map: true,
        }
    }
}

#[derive(Clone, Debug)]
pub struct RenderRequest {
    pub executable: PathBuf,
    pub source: PathBuf,
    pub output_parent: PathBuf,
    pub exposure_ev: Option<f32>,
    pub pyramid_gate: Option<f32>,
    pub worker_threads: Option<usize>,
    pub settings: RenderSettings,
    /// Keep scene-linear pixels for reversible development and HDR export.
    pub retain_master: bool,
    /// Immutable snapshot of this run's regional repairs and development.
    pub recipe: Option<strehl_edit::DevelopmentRecipe>,
}

#[derive(Debug)]
pub enum RenderEvent {
    Started {
        directory: PathBuf,
        output: PathBuf,
        log: PathBuf,
    },
    Log(String),
    Finished(RenderOutcome),
}

#[derive(Debug)]
pub enum RenderOutcome {
    Completed {
        directory: PathBuf,
        output: PathBuf,
        log: PathBuf,
    },
    Cancelled {
        directory: PathBuf,
    },
    Failed {
        directory: Option<PathBuf>,
        message: String,
    },
}

pub struct RenderJob {
    pub receiver: Receiver<RenderEvent>,
    cancelled: Arc<AtomicBool>,
    closing: Arc<AtomicBool>,
    worker: Option<JoinHandle<()>>,
}

impl RenderJob {
    pub fn is_cancelling(&self) -> bool {
        self.cancelled.load(Ordering::Relaxed)
    }
    pub fn cancel(&self) {
        self.cancelled.store(true, Ordering::Relaxed);
    }
}

impl Drop for RenderJob {
    fn drop(&mut self) {
        self.closing.store(true, Ordering::Relaxed);
        self.cancel();
        // Completion delivery is nonblocking, so shutdown cannot deadlock on
        // a full event queue. Join ensures the owned process is reaped.
        if let Some(worker) = self.worker.take() {
            let _ = worker.join();
        }
    }
}

pub fn start_render(request: RenderRequest) -> RenderJob {
    let (sender, receiver) = mpsc::sync_channel(EVENT_CAPACITY);
    let cancelled = Arc::new(AtomicBool::new(false));
    let closing = Arc::new(AtomicBool::new(false));
    let worker_cancelled = Arc::clone(&cancelled);
    let worker_closing = Arc::clone(&closing);
    let errors = sender.clone();
    let worker = match thread::Builder::new()
        .name("strehl-render".into())
        .spawn(move || {
            let outcome = run_render(&request, &worker_cancelled, &sender);
            // Logs use try_send and can fill the queue. The terminal state must
            // eventually be delivered while the UI is alive, yet allow Drop to join.
            deliver_terminal(&sender, outcome, &worker_closing);
        }) {
        Ok(worker) => Some(worker),
        Err(error) => {
            let _ = errors.try_send(RenderEvent::Finished(RenderOutcome::Failed {
                directory: None,
                message: format!("Starting the render worker: {error}"),
            }));
            None
        }
    };
    RenderJob {
        receiver,
        cancelled,
        closing,
        worker,
    }
}

fn deliver_terminal(
    sender: &SyncSender<RenderEvent>,
    outcome: RenderOutcome,
    closing: &AtomicBool,
) {
    let mut terminal = RenderEvent::Finished(outcome);
    loop {
        match sender.try_send(terminal) {
            Ok(()) | Err(mpsc::TrySendError::Disconnected(_)) => break,
            Err(mpsc::TrySendError::Full(event)) => {
                if closing.load(Ordering::Relaxed) {
                    break;
                }
                terminal = event;
                thread::sleep(Duration::from_millis(20));
            }
        }
    }
}

fn run_render(
    request: &RenderRequest,
    cancelled: &Arc<AtomicBool>,
    sender: &SyncSender<RenderEvent>,
) -> RenderOutcome {
    let mut job_directory = None;
    let result = (|| -> Result<RenderOutcome> {
        validate_settings(request)?;
        let source = canonical_directory(&request.source)?;
        let output_parent = prepare_output_parent(&source, &request.output_parent)?;
        // Re-scan immediately before launch; a stale UI scan must not authorize
        // a folder that is now empty. Only names and sizes are read here.
        let captures = scan(&source, cancelled)?;
        if let Some(recipe) = &request.recipe {
            let count = request
                .settings
                .frame_limit
                .unwrap_or(captures.frames.len())
                .min(captures.frames.len());
            for region in recipe.regions.iter().filter(|region| region.enabled) {
                if let Some(range) = &region.source_range {
                    ensure!(
                        range.last < count,
                        "Region {} needs capture {}, but this run includes only {count}",
                        region.name,
                        range.last + 1
                    );
                }
            }
        }
        let directory = create_job_directory(&output_parent)?;
        job_directory = Some(directory.clone());
        let directory = fs::canonicalize(&directory).context("Resolving the new output folder")?;
        ensure!(
            !path_is_within(&directory, &source) && !path_is_within(&source, &directory),
            "The render folder overlaps the input stack"
        );
        let partial = directory.join("result.partial.tiff");
        let output = directory.join("result.tiff");
        let log = directory.join("render.log");
        let cache = directory.join("cache");
        fs::create_dir(&cache).context("Creating the render's private cache")?;
        if let Some(recipe) = &request.recipe {
            let bytes = serde_json::to_vec_pretty(recipe)?;
            for name in ["region-recipe.json", "result.strehl-edits.json"] {
                let mut file = OpenOptions::new()
                    .write(true)
                    .create_new(true)
                    .open(directory.join(name))
                    .context("Saving the run's edit recipe")?;
                file.write_all(&bytes)?;
                file.sync_all()?;
            }
        }
        let mut command = render_command(request, &source, &partial)?;
        command.env("STREHL_CACHE_DIR", &cache);
        let mut log_file = OpenOptions::new()
            .append(true)
            .create_new(true)
            .open(&log)
            .context("Creating the render log")?;
        let workers = request
            .worker_threads
            .map(|count| count.to_string())
            .unwrap_or_else(|| "engine default".into());
        writeln!(
            log_file,
            "Strehl desktop render\nProgram: {:?}\nArguments: {:?}\nInherited STREHL_* overrides removed; STREHL_CACHE_DIR explicitly set to {}.\nRAYON_NUM_THREADS: {workers}. STREHL_PYRAMID_WORKERS: {workers}.\nExecution limits only; engine canonical reduction order and memory plan preserved.\n",
            command.get_program(),
            command.get_args().collect::<Vec<_>>(),
            cache.display()
        )?;
        command.stdout(Stdio::from(log_file.try_clone()?));
        command.stderr(Stdio::from(log_file));
        command.stdin(Stdio::null());
        command.current_dir(&directory);
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
                    "The engine exited with {status}. Full output: {}",
                    log.display()
                );
                ensure!(
                    !cancelled.load(Ordering::Relaxed),
                    "Render cancelled before publication"
                );
                if request.retain_master {
                    publish_linear_master(&directory, cancelled)?;
                }
                publish_render_outputs(
                    &partial,
                    &output,
                    request.settings.confidence_map,
                    cancelled,
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

fn validate_settings(request: &RenderRequest) -> Result<()> {
    if let Some(recipe) = &request.recipe {
        recipe.validate()?;
        ensure!(
            request.retain_master,
            "Regional edits require a retained linear master"
        );
    }
    ensure!(
        !(request.settings.auto_exposure && request.exposure_ev.is_some()),
        "Choose either automatic exposure or an explicit exposure, not both"
    );
    if let Some(limit) = request.settings.frame_limit {
        ensure!(limit > 0, "Capture limit must be at least one");
    }
    if let Some(exposure) = request.exposure_ev {
        ensure!(
            exposure.is_finite() && (-12.0..=12.0).contains(&exposure),
            "Exposure must be finite and between -12 and +12 EV"
        );
    }
    if let Some(gate) = request.pyramid_gate {
        ensure!(
            gate.is_finite() && gate >= 0.0,
            "The pyramid gate must be finite and nonnegative"
        );
    }
    if let Some(threads) = request.worker_threads {
        ensure!(
            threads > 0 && threads <= 1024,
            "Worker count must be between 1 and 1024"
        );
    }
    if let Some(bands) = request.settings.pyramid_bands {
        ensure!(
            (1..=12).contains(&bands),
            "Detail bands must be between 1 and 12"
        );
    }
    if let Some(exponent) = request.settings.pyramid_exponent {
        ensure!(
            exponent.is_finite() && exponent > 0.0,
            "Selection exponent must be finite and positive"
        );
    }
    if let Some(sharpen) = request.settings.pyramid_sharpen {
        ensure!(
            sharpen.is_finite() && sharpen >= 1.0,
            "Selection ramp must be finite and at least 1.0"
        );
    }
    ensure!(
        !request.executable.as_os_str().is_empty(),
        "Choose the Strehl engine executable"
    );
    Ok(())
}

fn render_command(request: &RenderRequest, source: &Path, partial: &Path) -> Result<Command> {
    let mut command = crate::engine::command(&request.executable)?;
    command
        .arg("stack")
        .arg(source)
        .args(["--merge", "pyramid", "--srgb", "--out"])
        .arg(partial);
    let directory = partial
        .parent()
        .context("The render output needs a parent directory")?;
    if request.retain_master {
        command
            .arg("--linear-master")
            .arg(directory.join("master.partial.tiff"));
    }
    if request.recipe.is_some() {
        command
            .arg("--region-recipe")
            .arg(directory.join("region-recipe.json"));
    }
    if let Some(exposure) = request.exposure_ev {
        command.arg(format!("--exposure={exposure}"));
    }
    if request.settings.auto_exposure {
        command.arg("--auto-exposure");
    }
    if let Some(limit) = request.settings.frame_limit {
        command.arg(format!("--limit={limit}"));
    }
    if request.settings.confidence_map {
        command.arg("--confidence-map").arg(
            partial
                .parent()
                .context("The render output needs a parent directory")?
                .join("confidence.partial.tiff"),
        );
    }
    if let Some(gate) = request.pyramid_gate {
        command.arg(format!("--pyramid-gate={gate}"));
    }
    if let Some(bands) = request.settings.pyramid_bands {
        command.arg(format!("--pyramid-bands={bands}"));
    }
    if let Some(exponent) = request.settings.pyramid_exponent {
        command.arg(format!("--pyramid-exponent={exponent}"));
    }
    if let Some(sharpen) = request.settings.pyramid_sharpen {
        command.arg(format!("--pyramid-sharpen={sharpen}"));
    }
    if request.settings.resampler != Resampler::CatmullRom {
        command.arg(format!(
            "--resampler={}",
            request.settings.resampler.cli_name()
        ));
    }
    if request.settings.binned {
        command.arg("--binned");
    }
    if !request.settings.correct_lateral_ca {
        command.arg("--fix-ca=off");
    }
    if request.settings.crop_to_coverage {
        command.arg("--cover=crop");
    }
    // Experimental overrides should never silently change a normal desktop
    // render. Keep the OS environment (PATH, device drivers, LOCALAPPDATA).
    remove_experimental_overrides(&mut command, std::env::vars_os());
    command.env("STREHL_UI_PROGRESS", "1");
    command.env_remove("RAYON_NUM_THREADS");
    if let Some(threads) = request.worker_threads {
        command.env("RAYON_NUM_THREADS", threads.to_string());
        command.env("STREHL_PYRAMID_WORKERS", threads.to_string());
    }
    #[cfg(windows)]
    {
        use std::os::windows::process::CommandExt;
        command.creation_flags(0x0800_0000); // CREATE_NO_WINDOW, no shell involved.
    }
    Ok(command)
}

fn remove_experimental_overrides(
    command: &mut Command,
    environment: impl IntoIterator<Item = (std::ffi::OsString, std::ffi::OsString)>,
) {
    for (name, _) in environment {
        if name
            .to_string_lossy()
            .to_ascii_uppercase()
            .starts_with("STREHL_")
        {
            command.env_remove(name);
        }
    }
}

fn canonical_directory(path: &Path) -> Result<PathBuf> {
    let canonical =
        fs::canonicalize(path).with_context(|| format!("Finding {}", path.display()))?;
    ensure!(canonical.is_dir(), "{} is not a folder", path.display());
    Ok(canonical)
}

/// Resolve existing ancestors before any write. In particular, creating a new
/// export folder must not quietly create a directory inside the RAW corpus.
fn prepare_output_parent(source: &Path, requested: &Path) -> Result<PathBuf> {
    if requested
        .try_exists()
        .context("Checking the output folder")?
    {
        let directory = canonical_directory(requested)?;
        validate_output_parent(source, &directory)?;
        return Ok(directory);
    }
    ensure!(
        !requested
            .components()
            .any(|component| component == std::path::Component::ParentDir),
        "Choose a new output folder without parent-directory (..) components"
    );
    let absolute = if requested.is_absolute() {
        requested.to_path_buf()
    } else {
        std::env::current_dir()
            .context("Finding the working folder")?
            .join(requested)
    };
    let mut ancestor = absolute.as_path();
    let mut missing = Vec::new();
    while !ancestor
        .try_exists()
        .context("Checking the output folder's ancestors")?
    {
        missing.push(
            ancestor
                .file_name()
                .context("The output path has no existing ancestor")?
                .to_os_string(),
        );
        ancestor = ancestor
            .parent()
            .context("The output path has no existing ancestor")?;
    }
    let mut directory = canonical_directory(ancestor)?;
    validate_output_parent(source, &directory)?;
    let mut intended = directory.clone();
    for component in missing.iter().rev() {
        intended.push(component);
    }
    validate_output_parent(source, &intended)?;
    for component in missing.into_iter().rev() {
        directory.push(component);
        fs::create_dir(&directory)
            .with_context(|| format!("Creating output folder {}", directory.display()))?;
        directory = canonical_directory(&directory)?;
        validate_output_parent(source, &directory)?;
    }
    Ok(directory)
}

fn path_is_within(path: &Path, root: &Path) -> bool {
    #[cfg(windows)]
    {
        // Windows canonical paths use a verbatim prefix; compare ancestry with
        // the OS's normal case-insensitive drive/path spelling convention.
        fn normal(path: &Path) -> String {
            path.to_string_lossy()
                .replace('/', "\\")
                .trim_start_matches(r"\\?\")
                .trim_end_matches('\\')
                .to_lowercase()
        }
        let path = normal(path);
        let root = normal(root);
        path == root
            || path
                .strip_prefix(&root)
                .is_some_and(|suffix| suffix.starts_with('\\'))
    }
    #[cfg(not(windows))]
    {
        path.starts_with(root)
    }
}

fn validate_output_parent(source: &Path, output_parent: &Path) -> Result<()> {
    ensure!(
        !path_is_within(output_parent, source),
        "Choose an output folder outside the input stack"
    );
    validate_corpus_destination(output_parent)
}

fn validate_corpus_destination(output_parent: &Path) -> Result<()> {
    #[cfg(not(windows))]
    let _ = output_parent;
    #[cfg(windows)]
    for corpus in [Path::new(r"C:\dev\macro"), Path::new(r"D:\personal\macro")] {
        let corpus = fs::canonicalize(corpus).unwrap_or_else(|_| corpus.to_path_buf());
        ensure!(
            !path_is_within(output_parent, &corpus),
            "The photograph corpus is read-only; choose an output folder elsewhere"
        );
    }
    Ok(())
}

pub(crate) fn validate_export_destination(
    source: Option<&Path>,
    output_parent: &Path,
) -> Result<()> {
    let parent = canonical_directory(output_parent)?;
    if let Some(source) = source {
        return validate_output_parent(source, &parent);
    }
    validate_corpus_destination(&parent)
}

fn create_job_directory(parent: &Path) -> Result<PathBuf> {
    let timestamp = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .context("The system clock precedes 1970")?
        .as_millis();
    for _ in 0..100 {
        let sequence = NEXT_JOB.fetch_add(1, Ordering::Relaxed);
        let directory = parent.join(format!(
            "strehl-{timestamp}-{}-{sequence}",
            std::process::id()
        ));
        match fs::create_dir(&directory) {
            Ok(()) => return Ok(directory),
            Err(error) if error.kind() == std::io::ErrorKind::AlreadyExists => continue,
            Err(error) => return Err(error).context("Creating a fresh render folder"),
        }
    }
    bail!("Could not reserve a new render folder")
}

fn publish_render_outputs(
    partial: &Path,
    output: &Path,
    confidence_map: bool,
    cancelled: &AtomicBool,
) -> Result<()> {
    if confidence_map {
        let directory = output
            .parent()
            .context("The render output needs a parent directory")?;
        publish_output(
            &directory.join("confidence.partial.tiff"),
            &directory.join("confidence.tiff"),
            cancelled,
        )
        .context("Publishing the requested confidence map")?;
    }
    publish_output(partial, output, cancelled)
}

fn publish_linear_master(directory: &Path, cancelled: &AtomicBool) -> Result<()> {
    let partial = directory.join("master.partial.tiff");
    // Validate the complete float image, including embedded color and recipe
    // metadata. The SDR viewer would accept a wrongly encoded integer TIFF.
    let image = strehl_edit::load_tiff(&partial).context("Validating the linear master")?;
    ensure!(
        image.origin == strehl_edit::ImageOrigin::SceneLinear,
        "The engine's editing master is not scene-linear"
    );
    ensure!(
        image.baseline.is_some(),
        "The editing master has no display baseline"
    );
    let recipe_path = directory.join("region-recipe.json");
    let expected = if recipe_path.is_file() {
        let bytes = crate::edit_workspace::read_bounded(&recipe_path, 2 * 1024 * 1024)?;
        serde_json::from_slice::<strehl_edit::DevelopmentRecipe>(&bytes)?
    } else {
        strehl_edit::DevelopmentRecipe::default()
    };
    image
        .validate_source_repairs(&expected)
        .context("The engine did not apply the requested source-region repairs")?;
    let result_size = image::image_dimensions(directory.join("result.partial.tiff"))
        .context("Reading the SDR photograph dimensions")?;
    ensure!(
        (image.width, image.height) == result_size,
        "The editing master and photograph have different dimensions"
    );
    drop(image);
    ensure!(
        !cancelled.load(Ordering::Relaxed),
        "Render cancelled before publication"
    );
    publish_no_replace(&partial, &directory.join("master.tiff"))
}

fn publish_output(partial: &Path, output: &Path, cancelled: &AtomicBool) -> Result<()> {
    let metadata = fs::metadata(partial).context("The engine did not write its TIFF output")?;
    ensure!(
        metadata.is_file() && metadata.len() > 0,
        "The engine wrote no image data"
    );
    crate::preview::validate_tiff(partial)
        .context("The engine's TIFF is incomplete or exceeds the viewer's allocation limit")?;
    ensure!(
        !cancelled.load(Ordering::Relaxed),
        "Render cancelled before publication"
    );
    publish_no_replace(partial, output)
        .context("Publishing the completed TIFF without replacing existing files")
}

fn publish_no_replace(partial: &Path, output: &Path) -> Result<()> {
    ensure!(
        partial.parent() == output.parent(),
        "The completed image must stay in its reserved render folder"
    );
    #[cfg(windows)]
    {
        use windows_sys::Win32::Storage::FileSystem::MoveFileExW;

        let source = windows_path(partial)?;
        let destination = windows_path(output)?;
        // SAFETY: both owned buffers contain valid, NUL-terminated UTF-16 path
        // representations without interior NULs and live across this call.
        // Flags = 0 deliberately omits REPLACE_EXISTING and COPY_ALLOWED:
        // this same-directory rename fails if the final name already exists.
        // https://learn.microsoft.com/en-us/windows/win32/api/winbase/nf-winbase-movefileexw
        if unsafe { MoveFileExW(source.as_ptr(), destination.as_ptr(), 0) } == 0 {
            return Err(std::io::Error::last_os_error()).context("Renaming the completed TIFF");
        }
        Ok(())
    }
    #[cfg(not(windows))]
    {
        // A new hard-link entry cannot replace an existing destination.
        fs::hard_link(partial, output).context("Creating the completed TIFF's final name")?;
        fs::remove_file(partial).context("Removing the completed render's temporary name")?;
        Ok(())
    }
}

#[cfg(windows)]
fn windows_path(path: &Path) -> Result<Vec<u16>> {
    use std::os::windows::ffi::OsStrExt;

    let mut encoded: Vec<u16> = path.as_os_str().encode_wide().collect();
    ensure!(
        !encoded.contains(&0),
        "An image path contains a NUL character"
    );
    encoded.push(0);
    Ok(encoded)
}

enum ProcessResult {
    Exited(ExitStatus),
    Cancelled,
}

struct OwnedChild(Child);

impl Drop for OwnedChild {
    fn drop(&mut self) {
        if !matches!(self.0.try_wait(), Ok(Some(_))) {
            let _ = self.0.kill();
        }
        let _ = self.0.wait();
    }
}

fn run_process(
    command: &mut Command,
    cancelled: &AtomicBool,
    sender: &SyncSender<RenderEvent>,
    log: &Path,
) -> Result<ProcessResult> {
    if cancelled.load(Ordering::Relaxed) {
        return Ok(ProcessResult::Cancelled);
    }
    let mut child = OwnedChild(command.spawn().context("Starting the Strehl engine")?);
    let mut live_log = File::open(log).context("Opening live render output")?;
    let mut reader = LiveLogReader::default();
    loop {
        if cancelled.load(Ordering::Relaxed) {
            let _ = child.0.kill();
            child.0.wait().context("Waiting for the cancelled engine")?;
            tail_log(&mut live_log, sender, &mut reader, true)?;
            return Ok(ProcessResult::Cancelled);
        }
        let caught_up = tail_log(&mut live_log, sender, &mut reader, false)?;
        if let Some(status) = child
            .0
            .try_wait()
            .context("Checking the owned engine process")?
        {
            if !drain_log(&mut live_log, sender, &mut reader, cancelled)? {
                return Ok(ProcessResult::Cancelled);
            }
            return Ok(ProcessResult::Exited(status));
        }
        thread::sleep(if caught_up {
            Duration::from_millis(50)
        } else {
            LOG_RETRY
        });
    }
}

#[derive(Default)]
struct LiveLogReader {
    decoder: Utf8LogDecoder,
    pending: Option<String>,
    disconnected: bool,
}

impl LiveLogReader {
    fn flush(&mut self, sender: &SyncSender<RenderEvent>) -> bool {
        let Some(text) = self.pending.take() else {
            return true;
        };
        match sender.try_send(RenderEvent::Log(text)) {
            Ok(()) => true,
            Err(mpsc::TrySendError::Full(RenderEvent::Log(text))) => {
                self.pending = Some(text);
                false
            }
            Err(mpsc::TrySendError::Disconnected(_)) => {
                self.disconnected = true;
                true
            }
            Err(mpsc::TrySendError::Full(_)) => unreachable!("only a log was sent"),
        }
    }
}

/// The file is the spool: a full queue retains one chunk and stops reading.
/// Successful completion drains it before the terminal event can be sent.
/// Cancellation and closing may stop the live drain; the complete log remains
/// on disk, and neither can wait indefinitely for an abandoned UI receiver.
fn drain_log(
    log: &mut File,
    sender: &SyncSender<RenderEvent>,
    reader: &mut LiveLogReader,
    cancelled: &AtomicBool,
) -> Result<bool> {
    loop {
        if cancelled.load(Ordering::Relaxed) {
            return Ok(false);
        }
        if tail_log(log, sender, reader, true)? {
            return Ok(true);
        }
        thread::sleep(LOG_RETRY);
    }
}

fn tail_log(
    log: &mut File,
    sender: &SyncSender<RenderEvent>,
    reader: &mut LiveLogReader,
    finished: bool,
) -> Result<bool> {
    if !reader.flush(sender) {
        return Ok(false);
    }
    if reader.disconnected {
        return Ok(true);
    }
    let mut buffer = [0_u8; LOG_CHUNK];
    // Bound both worker scheduling and memory, independently of log size.
    // UTF-8 replacement can expand invalid bytes by 3x; valid diagnostic text
    // occupies at most one 8 KiB chunk here plus the bounded event queue.
    for _ in 0..LOG_READS_PER_TICK {
        let count = log.read(&mut buffer)?;
        if count == 0 {
            if finished {
                let text = reader.decoder.decode(&[], true);
                reader.pending = (!text.is_empty()).then_some(text);
            }
            return Ok(reader.flush(sender));
        }
        let text = reader.decoder.decode(&buffer[..count], false);
        reader.pending = (!text.is_empty()).then_some(text);
        if !reader.flush(sender) {
            return Ok(false);
        }
        if reader.disconnected {
            return Ok(true);
        }
    }
    Ok(false)
}

#[cfg(test)]
pub(crate) mod tests {
    use super::*;
    use std::ffi::OsStr;

    pub(crate) struct TestDirectory(PathBuf);

    impl TestDirectory {
        pub(crate) fn new(label: &str) -> Self {
            let directory = create_job_directory(&std::env::temp_dir()).unwrap();
            let path = directory.join(label);
            fs::create_dir(&path).unwrap();
            Self(path)
        }

        pub(crate) fn path(&self) -> &Path {
            &self.0
        }
    }

    impl Drop for TestDirectory {
        fn drop(&mut self) {
            // Only remove the fresh directory reserved by this fixture.
            if let Some(parent) = self.0.parent() {
                let _ = fs::remove_dir_all(parent);
            }
        }
    }

    fn request(source: PathBuf, output_parent: PathBuf) -> RenderRequest {
        RenderRequest {
            executable: PathBuf::from("strehl"),
            source,
            output_parent,
            exposure_ev: None,
            pyramid_gate: None,
            worker_threads: None,
            settings: RenderSettings::default(),
            retain_master: false,
            recipe: None,
        }
    }

    #[test]
    fn editing_master_and_recipe_are_explicit_arguments_in_the_reserved_run() {
        let mut request = request(PathBuf::from("input with spaces"), PathBuf::from("outputs"));
        request.retain_master = true;
        request.recipe = Some(strehl_edit::DevelopmentRecipe::default());
        let partial = Path::new("output with spaces/result.partial.tiff");
        let command = render_command(&request, &request.source, partial).unwrap();
        let args = command
            .get_args()
            .map(|v| v.to_string_lossy().into_owned())
            .collect::<Vec<_>>();
        let has_pair = |key: &str, path: &Path| {
            args.windows(2)
                .any(|pair| pair[0] == key && pair[1] == path.to_string_lossy())
        };
        assert!(has_pair(
            "--linear-master",
            &partial.parent().unwrap().join("master.partial.tiff")
        ));
        assert!(has_pair(
            "--region-recipe",
            &partial.parent().unwrap().join("region-recipe.json")
        ));
        request.retain_master = false;
        assert!(validate_settings(&request).is_err());
    }

    #[test]
    fn master_publication_rejects_wrong_pixels_and_preserves_existing_output() {
        let directory = TestDirectory::new("editing-master-publication");
        let root = directory.path();
        image::RgbImage::new(16, 12)
            .save(root.join("result.partial.tiff"))
            .unwrap();
        let cancelled = AtomicBool::new(false);
        assert!(publish_linear_master(root, &cancelled).is_err());
        fs::copy(
            root.join("result.partial.tiff"),
            root.join("master.partial.tiff"),
        )
        .unwrap();
        assert!(
            publish_linear_master(root, &cancelled).is_err(),
            "an SDR TIFF is not a linear master"
        );
        fs::remove_file(root.join("master.partial.tiff")).unwrap();
        let mut master = strehl_edit::LinearImage {
            width: 16,
            height: 12,
            pixels: vec![1.7; 16 * 12 * 3],
            origin: strehl_edit::ImageOrigin::SceneLinear,
            baseline: Some(strehl_edit::DisplayBaseline {
                black: 0.0,
                white: 1.0,
                contrast: 0.0,
                exposure_gain: 1.0,
            }),
            baked_recipe: None,
        };
        strehl_edit::save_linear_tiff(&root.join("master.partial.tiff"), &master).unwrap();
        cancelled.store(true, Ordering::Relaxed);
        assert!(publish_linear_master(root, &cancelled).is_err());
        assert!(!root.join("master.tiff").exists());
        cancelled.store(false, Ordering::Relaxed);
        fs::write(root.join("master.tiff"), b"existing-image").unwrap();
        assert!(publish_linear_master(root, &cancelled).is_err());
        assert_eq!(
            fs::read(root.join("master.tiff")).unwrap(),
            b"existing-image"
        );
        fs::remove_file(root.join("master.tiff")).unwrap();
        publish_linear_master(root, &cancelled).unwrap();
        let published = strehl_edit::load_tiff(&root.join("master.tiff")).unwrap();
        assert_eq!(published.pixels, master.pixels);
        assert!(!root.join("master.partial.tiff").exists());
        master.width = 12;
        master.height = 16;
        strehl_edit::save_linear_tiff(&root.join("master.partial.tiff"), &master).unwrap();
        assert!(
            publish_linear_master(root, &cancelled).is_err(),
            "same sample count, different shape must fail"
        );
    }

    #[test]
    fn scan_sorts_case_insensitive_arw_filter_and_does_not_recurse() {
        let directory = TestDirectory::new("scan");
        fs::write(directory.path().join("b.ARW"), [1_u8; 3]).unwrap();
        fs::write(directory.path().join("a.arw"), [1_u8; 2]).unwrap();
        fs::write(directory.path().join("ignored.jpg"), [1_u8; 7]).unwrap();
        let nested = directory.path().join("nested");
        fs::create_dir(&nested).unwrap();
        fs::write(nested.join("c.arw"), [1_u8; 11]).unwrap();
        fs::create_dir(directory.path().join("directory.arw")).unwrap();
        let scan = scan(directory.path(), &AtomicBool::new(false)).unwrap();
        assert_eq!(scan.frames.len(), 2);
        assert_eq!(scan.frames[0].path.file_name(), Some(OsStr::new("a.arw")));
        assert_eq!(scan.frames[1].path.file_name(), Some(OsStr::new("b.ARW")));
        assert_eq!(scan.frames[0].bytes, 2);
        assert_eq!(scan.total_bytes, 5);
    }

    #[test]
    fn output_guard_rejects_input_descendants_and_fresh_jobs_never_reuse() {
        let directory = TestDirectory::new("safety");
        let source = directory.path().join("source");
        fs::create_dir(&source).unwrap();
        let source = canonical_directory(&source).unwrap();
        assert!(validate_output_parent(&source, &source).is_err());
        assert!(validate_output_parent(&source, &source.join("exports")).is_err());
        let outside = canonical_directory(directory.path()).unwrap();
        assert!(validate_output_parent(&source, &outside).is_ok());
        let first = create_job_directory(&outside).unwrap();
        fs::write(first.join("keep.txt"), b"preserve").unwrap();
        let second = create_job_directory(&outside).unwrap();
        assert_ne!(first, second);
        assert_eq!(fs::read(first.join("keep.txt")).unwrap(), b"preserve");
        let nested = outside.join("exports").join("desktop");
        assert_eq!(
            prepare_output_parent(&source, &nested).unwrap(),
            canonical_directory(&nested).unwrap()
        );
        let forbidden = source.join("must-not-be-created").join("desktop");
        assert!(prepare_output_parent(&source, &forbidden).is_err());
        assert!(!source.join("must-not-be-created").exists());
        #[cfg(windows)]
        {
            assert!(
                validate_output_parent(&source, Path::new(r"c:\DEV\macro\new-output")).is_err()
            );
            assert!(
                validate_output_parent(&source, Path::new(r"D:\PERSONAL\macro\new-output"))
                    .is_err()
            );
            assert!(path_is_within(
                Path::new(r"\\?\C:\INPUT\exports"),
                Path::new(r"c:\input")
            ));
            assert!(!path_is_within(
                Path::new(r"C:\input-sibling"),
                Path::new(r"C:\input")
            ));
        }
    }

    #[test]
    fn command_routes_spaces_as_arguments_and_only_explicit_processing_options() {
        let mut request = request(PathBuf::from("input with spaces"), PathBuf::from("output"));
        let partial = Path::new("new output/result.partial.tiff");
        let defaults = render_command(&request, &request.source, partial).unwrap();
        let arguments: Vec<_> = defaults
            .get_args()
            .map(|value| value.to_string_lossy().into_owned())
            .collect();
        assert_eq!(
            arguments,
            [
                "stack",
                "input with spaces",
                "--merge",
                "pyramid",
                "--srgb",
                "--out",
                "new output/result.partial.tiff",
                "--confidence-map",
                Path::new("new output")
                    .join("confidence.partial.tiff")
                    .to_str()
                    .unwrap(),
            ]
        );
        request.exposure_ev = Some(-1.5);
        request.pyramid_gate = Some(2.5);
        request.worker_threads = Some(3);
        request.settings = RenderSettings {
            pyramid_bands: Some(8),
            pyramid_exponent: Some(2.25),
            pyramid_sharpen: Some(1.6),
            resampler: Resampler::Lanczos3,
            binned: true,
            correct_lateral_ca: false,
            crop_to_coverage: true,
            ..RenderSettings::default()
        };
        let explicit = render_command(&request, &request.source, partial).unwrap();
        let arguments: Vec<_> = explicit
            .get_args()
            .map(|value| value.to_string_lossy().into_owned())
            .collect();
        assert!(arguments.contains(&"--exposure=-1.5".into()));
        assert!(arguments.contains(&"--pyramid-gate=2.5".into()));
        for argument in [
            "--pyramid-bands=8",
            "--pyramid-exponent=2.25",
            "--pyramid-sharpen=1.6",
            "--resampler=lanczos3",
            "--binned",
            "--fix-ca=off",
            "--cover=crop",
        ] {
            assert!(
                arguments.iter().any(|value| value == argument),
                "missing {argument}"
            );
        }
        assert!(
            explicit
                .get_envs()
                .any(|(name, value)| name == "RAYON_NUM_THREADS" && value == Some(OsStr::new("3")))
        );
        assert!(
            explicit
                .get_envs()
                .any(|(name, value)| name == "STREHL_PYRAMID_WORKERS"
                    && value == Some(OsStr::new("3"))),
            "the pyramid pool does not consume RAYON_NUM_THREADS"
        );
        assert!(explicit.get_envs().any(|(name, value)| name == "STREHL_UI_PROGRESS" && value == Some(OsStr::new("1"))));
        assert!(
            !arguments
                .iter()
                .any(|value| value == "--auto-exposure" || value == "--gate")
        );
        let mut isolated = Command::new("strehl");
        remove_experimental_overrides(
            &mut isolated,
            [
                ("STREHL_MERGE".into(), "estimator".into()),
                ("STREHL_EXPERIMENT".into(), "enabled".into()),
                ("PATH".into(), "system path".into()),
            ],
        );
        assert_eq!(
            isolated
                .get_envs()
                .filter(
                    |(name, value)| name.to_string_lossy().starts_with("STREHL_")
                        && value.is_none()
                )
                .count(),
            2
        );
        assert!(!isolated.get_envs().any(|(name, _)| name == "PATH"));
    }

    #[test]
    fn publication_rejects_empty_and_truncated_output_and_never_clobbers_destination() {
        let directory = TestDirectory::new("publication");
        let partial = directory.path().join("result.partial.tiff");
        let output = directory.path().join("result.tiff");
        let cancelled = AtomicBool::new(false);
        fs::write(&partial, []).unwrap();
        assert!(publish_output(&partial, &output, &cancelled).is_err());
        assert!(!output.exists());
        fs::write(&partial, b"II*\0\x08\0\0\0").unwrap();
        assert!(publish_output(&partial, &output, &cancelled).is_err());
        image::RgbImage::new(2, 2).save(&partial).unwrap();
        fs::write(&output, b"existing user file").unwrap();
        assert!(publish_output(&partial, &output, &cancelled).is_err());
        assert_eq!(fs::read(&output).unwrap(), b"existing user file");
        fs::remove_file(&output).unwrap();
        cancelled.store(true, Ordering::Relaxed);
        assert!(publish_output(&partial, &output, &cancelled).is_err());
        assert!(!output.exists());
        cancelled.store(false, Ordering::Relaxed);
        publish_output(&partial, &output, &cancelled).unwrap();
        assert!(!partial.exists());
        crate::preview::validate_tiff(&output).unwrap();
    }

    #[test]
    fn new_settings_reopen_legacy_runs_and_round_trip_explicit_choices() {
        // A v18 run has none of the new fields. Deserialization must retain
        // its image settings while supplying the unchanged engine defaults.
        let legacy = r#"{"pyramid_bands":8,"pyramid_exponent":2.25,"pyramid_sharpen":1.6,"resampler":"Lanczos3","binned":true,"correct_lateral_ca":false,"crop_to_coverage":true}"#;
        let mut settings: RenderSettings = serde_json::from_str(legacy).unwrap();
        assert_eq!(settings.frame_limit, None);
        assert!(!settings.auto_exposure && settings.confidence_map);
        assert_eq!(settings.pyramid_bands, Some(8));
        assert_eq!(settings.resampler, Resampler::Lanczos3);
        settings.frame_limit = Some(17);
        settings.auto_exposure = true;
        settings.confidence_map = true;
        let round_trip: RenderSettings =
            serde_json::from_str(&serde_json::to_string(&settings).unwrap()).unwrap();
        assert_eq!(round_trip, settings);
    }

    #[test]
    fn requested_evidence_must_validate_before_a_finished_photograph_is_published() {
        let directory = TestDirectory::new("confidence-publication");
        let partial = directory.path().join("result.partial.tiff");
        let output = directory.path().join("result.tiff");
        let evidence_partial = directory.path().join("confidence.partial.tiff");
        let evidence = directory.path().join("confidence.tiff");
        let cancelled = AtomicBool::new(false);
        image::RgbImage::new(2, 2).save(&partial).unwrap();
        assert!(publish_render_outputs(&partial, &output, true, &cancelled).is_err());
        assert!(partial.exists() && !output.exists() && !evidence.exists());
        fs::write(&evidence_partial, b"not a TIFF").unwrap();
        assert!(publish_render_outputs(&partial, &output, true, &cancelled).is_err());
        assert!(!output.exists() && !evidence.exists());
        image::ImageBuffer::<image::Luma<u16>, Vec<u16>>::from_raw(
            2,
            2,
            vec![0, 400, 1000, u16::MAX],
        )
        .unwrap()
        .save(&evidence_partial)
        .unwrap();
        publish_render_outputs(&partial, &output, true, &cancelled).unwrap();
        assert!(output.exists() && evidence.exists());
        assert!(!partial.exists() && !evidence_partial.exists());
        assert_eq!(
            image::open(evidence).unwrap().into_luma16().into_raw(),
            vec![0, 400, 1000, u16::MAX]
        );
    }

    #[test]
    fn production_options_route_to_valid_pyramid_arguments_and_owned_artifacts() {
        let mut request = request(PathBuf::from("input with spaces"), PathBuf::from("output"));
        request.settings.auto_exposure = true;
        request.settings.frame_limit = Some(7);
        request.settings.confidence_map = true;
        validate_settings(&request).unwrap();
        let partial = Path::new("new output/result.partial.tiff");
        let command = render_command(&request, &request.source, partial).unwrap();
        let args: Vec<_> = command
            .get_args()
            .map(|s| s.to_string_lossy().into_owned())
            .collect();
        assert!(args.contains(&"--auto-exposure".into()));
        assert!(args.contains(&"--limit=7".into()));
        let index = args.iter().position(|s| s == "--confidence-map").unwrap();
        assert_eq!(
            Path::new(&args[index + 1]),
            Path::new("new output/confidence.partial.tiff")
        );
        assert!(
            !args
                .iter()
                .any(|s| s.starts_with("--exposure") || s.starts_with("--photometric"))
        );
        request.exposure_ev = Some(0.0);
        assert!(
            validate_settings(&request)
                .unwrap_err()
                .to_string()
                .contains("either automatic")
        );
        request.exposure_ev = None;
        request.settings.frame_limit = Some(0);
        assert!(
            validate_settings(&request)
                .unwrap_err()
                .to_string()
                .contains("at least one")
        );
    }

    #[cfg(windows)]
    #[test]
    fn native_publication_rejects_interior_nul_before_calling_windows() {
        use std::ffi::OsString;
        use std::os::windows::ffi::OsStringExt;

        let invalid = PathBuf::from(OsString::from_wide(&[b'a' as u16, 0, b'b' as u16]));
        assert!(windows_path(&invalid).is_err());
        let valid = windows_path(Path::new("render with spaces.tiff")).unwrap();
        assert_eq!(valid.last(), Some(&0));
        assert!(!valid[..valid.len() - 1].contains(&0));
    }

    #[test]
    fn invalid_settings_reject_nonfinite_and_empty_worker_values() {
        let mut request = request(PathBuf::from("input"), PathBuf::from("output"));
        request.exposure_ev = Some(f32::NAN);
        assert!(validate_settings(&request).is_err());
        request.exposure_ev = None;
        request.pyramid_gate = Some(-1.0);
        assert!(validate_settings(&request).is_err());
        request.pyramid_gate = None;
        request.worker_threads = Some(0);
        assert!(validate_settings(&request).is_err());
        request.worker_threads = Some(4);
        assert!(validate_settings(&request).is_ok());
        request.settings.pyramid_bands = Some(0);
        assert!(validate_settings(&request).is_err());
        request.settings.pyramid_bands = Some(7);
        request.settings.pyramid_exponent = Some(f32::INFINITY);
        assert!(validate_settings(&request).is_err());
        request.settings.pyramid_exponent = Some(2.0);
        request.settings.pyramid_sharpen = Some(0.9);
        assert!(validate_settings(&request).is_err());
        request.settings.pyramid_sharpen = Some(1.0);
        assert!(validate_settings(&request).is_ok());
    }

    fn child_command(mode: &str) -> Command {
        let mut command = Command::new(std::env::current_exe().unwrap());
        command.args([
            "--ignored",
            "--exact",
            "jobs::tests::engine_fixture",
            "--nocapture",
        ]);
        command.env("STREHL_UI_TEST_CHILD", mode);
        command
    }

    #[test]
    #[ignore = "invoked only as a separately owned child by lifecycle tests"]
    fn engine_fixture() {
        match std::env::var("STREHL_UI_TEST_CHILD").as_deref() {
            Ok("success") => {
                println!("fake child succeeded");
            }
            Ok("failure") => std::process::exit(7),
            Ok("wait") => loop {
                let ready = std::env::var_os("STREHL_UI_TEST_READY").expect("readiness path");
                fs::write(ready, std::process::id().to_string()).unwrap();
                thread::sleep(Duration::from_millis(25));
            },
            _ => panic!("fixture requires an explicit child mode"),
        }
    }

    #[test]
    fn owned_child_lifecycle_observes_success_failure_and_cancellation_without_shell() {
        let directory = TestDirectory::new("lifecycle");
        let log = directory.path().join("render.log");
        fs::write(&log, []).unwrap();
        let (sender, _receiver) = mpsc::sync_channel(EVENT_CAPACITY);
        let cancelled = AtomicBool::new(false);
        for (mode, expected_success) in [("success", true), ("failure", false)] {
            let mut command = child_command(mode);
            command.stdout(Stdio::null()).stderr(Stdio::null());
            match run_process(&mut command, &cancelled, &sender, &log).unwrap() {
                ProcessResult::Exited(status) => assert_eq!(status.success(), expected_success),
                ProcessResult::Cancelled => panic!("child was never cancelled"),
            }
        }
        let cancelled = Arc::new(AtomicBool::new(false));
        let worker_cancelled = Arc::clone(&cancelled);
        let worker_log = log.clone();
        let ready = directory.path().join("child-ready.txt");
        let worker_ready = ready.clone();
        let worker = thread::spawn(move || {
            let mut command = child_command("wait");
            command.env("STREHL_UI_TEST_READY", worker_ready);
            command.stdout(Stdio::null()).stderr(Stdio::null());
            run_process(&mut command, &worker_cancelled, &sender, &worker_log).unwrap()
        });
        let deadline = std::time::Instant::now() + Duration::from_secs(10);
        while !ready.exists() && std::time::Instant::now() < deadline {
            thread::sleep(Duration::from_millis(10));
        }
        cancelled.store(true, Ordering::Relaxed);
        assert!(matches!(worker.join().unwrap(), ProcessResult::Cancelled));
        assert!(
            ready.exists(),
            "The fake child must actually start before cancellation"
        );
    }

    #[test]
    fn live_log_backpressure_retains_one_chunk_without_seeking() {
        use std::io::Seek;
        let directory = TestDirectory::new("log-backpressure");
        let path = directory.path().join("render.log");
        fs::write(&path, vec![b'x'; 1024 * 1024]).unwrap();
        let (sender, receiver) = mpsc::sync_channel(1);
        let mut file = File::open(path).unwrap();
        let mut reader = LiveLogReader::default();
        assert!(!tail_log(&mut file, &sender, &mut reader, false).unwrap());
        assert_eq!(file.stream_position().unwrap(), (2 * LOG_CHUNK) as u64);
        assert_eq!(reader.pending.as_ref().unwrap().len(), LOG_CHUNK);
        for _ in 0..12 {
            assert!(!tail_log(&mut file, &sender, &mut reader, true).unwrap());
            assert_eq!(file.stream_position().unwrap(), (2 * LOG_CHUNK) as u64);
            assert_eq!(reader.pending.as_ref().unwrap().len(), LOG_CHUNK);
        }
        assert_eq!(receiver.try_iter().count(), 1);
    }

    #[test]
    fn every_maximum_preview_survives_slow_consumption_and_the_final_burst() {
        use crate::pipeline::{DiagnosticKind, PipelineProgress};
        use std::io::Seek;
        let directory = TestDirectory::new("maximum-live-previews");
        let path = directory.path().join("render.log");
        let mut source = String::new();
        // Rechoose a non-power-of-two population beyond the retired 32-frame
        // sampler. Every image is maximum size, not only the final image.
        for frame in 0..41 {
            let payload = format!("{:02x}{:02x}", frame, 255 - frame).repeat(512 * 384 / 2);
            let sequence = frame * 2 + 1;
            source.push_str(&format!(
                "STREHL_UI_PROGRESS event=diagnostic seq={sequence} frame={frame} level=0 kind=gate-support scope=frame scale=linear width=1 height=1 min=0 max=1 folded=1 total=41 sampling=nearest data=ff\n"
            ));
            source.push_str(&format!(
                "STREHL_UI_PROGRESS event=diagnostic seq={} frame={frame} level=3 kind=preview scope=stack scale=linear width=512 height=384 min=-4 max=200 folded={} total=41 sampling=nearest data={payload}\n",
                sequence + 1, frame + 1
            ));
        }
        assert!(source.len() > 15 * 1024 * 1024);
        fs::write(&path, &source).unwrap();
        let mut file = File::open(&path).unwrap();
        let (sender, receiver) = mpsc::sync_channel(2);
        let mut reader = LiveLogReader::default();
        let mut received = String::new();
        let mut progress = PipelineProgress::default();
        let mut blocked_ticks = 0;
        loop {
            let caught_up = tail_log(&mut file, &sender, &mut reader, true).unwrap();
            if reader.pending.is_some() {
                blocked_ticks += 1;
                let position = file.stream_position().unwrap();
                // A second worker tick without a UI tick cannot consume or
                // overwrite any bytes. Exactly two queued chunks + one held.
                assert!(!tail_log(&mut file, &sender, &mut reader, true).unwrap());
                assert_eq!(file.stream_position().unwrap(), position);
                assert!(reader.pending.as_ref().unwrap().len() <= LOG_CHUNK);
            }
            assert!(
                file.stream_position().unwrap() - received.len() as u64 <= (3 * LOG_CHUNK) as u64
            );
            if let Ok(event) = receiver.try_recv() {
                let RenderEvent::Log(text) = event else {
                    panic!("only logs were produced")
                };
                assert!(text.len() <= LOG_CHUNK);
                progress.ingest(&text);
                received.push_str(&text);
            }
            if caught_up {
                break;
            }
        }
        for event in receiver.try_iter() {
            let RenderEvent::Log(text) = event else {
                panic!("only logs were produced")
            };
            progress.ingest(&text);
            received.push_str(&text);
        }
        assert!(
            blocked_ticks > 1_000,
            "slow consumption must actually fill the queue repeatedly"
        );
        assert_eq!(received, source, "no earlier or final bytes may be skipped");
        assert!(reader.pending.is_none());
        assert!(!reader.disconnected);
        assert_eq!(progress.diagnostic_surfaces.len(), 82);
        let previews: Vec<_> = progress
            .diagnostic_surfaces
            .iter()
            .filter(|surface| surface.kind == DiagnosticKind::Preview)
            .collect();
        assert_eq!(previews.len(), 41);
        for (frame, preview) in previews.into_iter().enumerate() {
            assert_eq!((preview.frame, preview.folded), (frame, frame + 1));
            assert_eq!(
                (preview.width, preview.height, preview.level),
                (512, 384, 3)
            );
            assert_eq!(preview.pixels.len(), 512 * 384);
            assert!(
                preview
                    .pixels
                    .iter()
                    .enumerate()
                    .all(|(index, value)| *value
                        == if index % 2 == 0 {
                            frame as u8
                        } else {
                            255 - frame as u8
                        })
            );
        }
    }

    #[test]
    fn log_reads_keep_split_utf8_and_pending_chunks_in_order() {
        let directory = TestDirectory::new("log-decoder");
        let path = directory.path().join("render.log");
        fs::write(&path, b"camera: caf\xc3").unwrap();
        let mut file = File::open(&path).unwrap();
        let (sender, receiver) = mpsc::sync_channel(1);
        let mut reader = LiveLogReader::default();
        assert!(tail_log(&mut file, &sender, &mut reader, false).unwrap());
        let mut writer = OpenOptions::new().append(true).open(&path).unwrap();
        writer.write_all(b"\xa9\r\n").unwrap();
        assert!(!tail_log(&mut file, &sender, &mut reader, false).unwrap());
        assert_eq!(reader.pending.as_deref(), Some("\u{e9}\r\n"));
        writer
            .write_all(b"frames: 42 from the intact line\n")
            .unwrap();
        let mut text = String::new();
        loop {
            let RenderEvent::Log(chunk) = receiver.recv().unwrap() else {
                panic!("expected log")
            };
            text.push_str(&chunk);
            if tail_log(&mut file, &sender, &mut reader, true).unwrap() {
                break;
            }
        }
        for event in receiver.try_iter() {
            let RenderEvent::Log(chunk) = event else {
                panic!("expected log")
            };
            text.push_str(&chunk);
        }
        assert_eq!(
            text,
            "camera: caf\u{e9}\r\nframes: 42 from the intact line\n"
        );
        let mut progress = crate::pipeline::PipelineProgress::default();
        progress.ingest(&text);
        assert_eq!(progress.frames_total, Some(42));
    }

    #[test]
    fn cancelled_or_disconnected_log_drain_does_not_wait_on_a_full_queue() {
        use std::io::Seek;
        let directory = TestDirectory::new("log-cancel-drain");
        let path = directory.path().join("render.log");
        fs::write(&path, vec![b'x'; 1024 * 1024]).unwrap();
        let mut file = File::open(path).unwrap();
        let (sender, receiver) = mpsc::sync_channel(1);
        let mut reader = LiveLogReader::default();
        assert!(!tail_log(&mut file, &sender, &mut reader, true).unwrap());
        assert!(
            reader.pending.is_some(),
            "fixture must actually be backpressured"
        );
        let position = file.stream_position().unwrap();
        assert!(!drain_log(&mut file, &sender, &mut reader, &AtomicBool::new(true)).unwrap());
        assert_eq!(file.stream_position().unwrap(), position);
        drop(receiver);
        assert!(drain_log(&mut file, &sender, &mut reader, &AtomicBool::new(false)).unwrap());
        assert!(reader.disconnected);
        assert_eq!(file.stream_position().unwrap(), position);
    }

    #[test]
    fn successful_process_drains_its_entire_final_log_before_completion() {
        let directory = TestDirectory::new("log-terminal-order");
        let path = directory.path().join("render.log");
        let source = "final diagnostic burst\n".repeat(50_000);
        fs::write(&path, &source).unwrap();
        let (sender, receiver) = mpsc::sync_channel(1);
        let worker = thread::spawn(move || {
            let mut command = child_command("success");
            command.stdout(Stdio::null()).stderr(Stdio::null());
            let result =
                run_process(&mut command, &AtomicBool::new(false), &sender, &path).unwrap();
            assert!(matches!(result, ProcessResult::Exited(status) if status.success()));
            deliver_terminal(
                &sender,
                RenderOutcome::Completed {
                    directory: PathBuf::from("job"),
                    output: PathBuf::from("result.tiff"),
                    log: path,
                },
                &AtomicBool::new(false),
            );
        });
        let mut received = String::new();
        loop {
            match receiver.recv_timeout(Duration::from_secs(10)).unwrap() {
                RenderEvent::Log(text) => {
                    received.push_str(&text);
                    thread::sleep(Duration::from_millis(1));
                }
                RenderEvent::Finished(RenderOutcome::Completed { .. }) => break,
                _ => panic!("unexpected worker event"),
            }
        }
        worker.join().unwrap();
        assert_eq!(
            received, source,
            "completion cannot overtake the final diagnostic burst"
        );
    }

    #[test]
    fn full_live_log_queue_cannot_discard_cancellation_terminal_and_close_cannot_deadlock() {
        // The rejecting fixture must really fill the event queue before the
        // cancelled outcome is sent. Only closing, not cancelling, may skip it.
        let (sender, receiver) = mpsc::sync_channel(1);
        sender
            .send(RenderEvent::Log("queue is full".into()))
            .unwrap();
        let worker = thread::spawn(move || {
            deliver_terminal(
                &sender,
                RenderOutcome::Cancelled {
                    directory: PathBuf::from("job"),
                },
                &AtomicBool::new(false),
            );
        });
        assert!(matches!(receiver.recv().unwrap(), RenderEvent::Log(_)));
        assert!(matches!(
            receiver.recv_timeout(Duration::from_secs(5)).unwrap(),
            RenderEvent::Finished(RenderOutcome::Cancelled { .. })
        ));
        worker.join().unwrap();
        let (sender, _receiver) = mpsc::sync_channel(1);
        sender
            .send(RenderEvent::Log("queue is full".into()))
            .unwrap();
        deliver_terminal(
            &sender,
            RenderOutcome::Cancelled {
                directory: PathBuf::from("job"),
            },
            &AtomicBool::new(true),
        );
    }
}
