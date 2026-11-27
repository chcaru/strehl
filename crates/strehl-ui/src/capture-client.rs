//! Native LAN client. Network, JPEG decoding and receiver I/O never run on egui.
//! Mutations are sent once with the revisions seen at the time of the click.
use anyhow::{Context, Result, ensure};
use eframe::egui;
use reqwest::blocking::{Client, Response};
use serde::{Deserialize, Serialize};
use serde_json::{Value, json};
use std::{
    collections::{BTreeMap, BTreeSet},
    io::Read,
    net::IpAddr,
    path::{Path, PathBuf},
    sync::{
        Arc, Mutex,
        atomic::{AtomicU8, Ordering},
        mpsc,
    },
    time::{Duration, Instant},
};
use strehl_capture::{
    lan::Lan,
    receiver::{ReceiverConfig, save_json},
    session::{Command, CommandRequest},
};

#[path = "capture-host.rs"]
pub(crate) mod host;
use host::HostState;

#[derive(Clone, Serialize, Deserialize)]
#[serde(default, deny_unknown_fields)]
pub(crate) struct Config {
    pub controller: String,
    pub pairing_key: String,
    pub lan: String,
    pub receiver_config: PathBuf,
}
impl Default for Config {
    fn default() -> Self {
        Self {
            controller: String::new(),
            pairing_key: String::new(),
            lan: "10.0.0.0/24".into(),
            receiver_config: local_data().join("StrehlCaptureReceiver/receiver.json"),
        }
    }
}
fn local_data() -> PathBuf {
    std::env::var_os("LOCALAPPDATA")
        .map(PathBuf::from)
        .or_else(|| std::env::var_os("XDG_CONFIG_HOME").map(PathBuf::from))
        .unwrap_or_else(|| {
            std::env::var_os("HOME")
                .map(PathBuf::from)
                .unwrap_or_default()
                .join(".config")
        })
}
pub(crate) fn default_path() -> PathBuf {
    local_data().join("Strehl/capture.json")
}
impl Config {
    pub fn load(path: &Path) -> Result<Self> {
        if !path.exists() {
            return Ok(Self::default());
        }
        serde_json::from_slice(&read_file(path, 64 * 1024)?).context("Read capture settings")
    }
    pub fn normalize(&mut self) -> Result<()> {
        let mut url =
            reqwest::Url::parse(self.controller.trim()).context("Enter the Pi's LAN address")?;
        if let Some(fragment) = url.fragment() {
            self.pairing_key = fragment
                .strip_prefix("key=")
                .context("Invalid pairing link")?
                .to_owned();
        }
        ensure!(
            url.scheme() == "http"
                && url.username().is_empty()
                && url.password().is_none()
                && url.query().is_none()
                && matches!(url.path(), "" | "/"),
            "Use a local http://IP:port address or pairing link"
        );
        let ip: IpAddr = url
            .host_str()
            .context("Missing Pi address")?
            .parse()
            .context("Use the Pi's numeric LAN address")?;
        ensure!(
            Lan::parse(&self.lan)?.permits(ip),
            "The Pi address must be in your configured LAN"
        );
        ensure!(
            (16..=256).contains(&self.pairing_key.len())
                && self
                    .pairing_key
                    .bytes()
                    .all(|b| b.is_ascii_alphanumeric() || b == b'-' || b == b'_'),
            "Paste the complete pairing key or link"
        );
        ensure!(
            self.receiver_config.is_absolute(),
            "Use an absolute receiver configuration path"
        );
        url.set_fragment(None);
        self.controller = url.as_str().trim_end_matches('/').into();
        Ok(())
    }
}

#[derive(Clone, Debug, Serialize)]
pub(crate) struct CompletedStack {
    pub folder: PathBuf,
    pub frames: usize,
    pub planes: usize,
    pub shots_per_plane: usize,
}
/// A registered run that ended before its plan did: its `result.json` says
/// `stopped` (an orderly Stop) or `uncertain` (a fault). Listed beside the
/// completed stacks (Studio 2, D13) and opened like any folder; nothing
/// about it is promoted to "complete".
#[derive(Clone, Debug, PartialEq, Serialize)]
pub(crate) struct StoppedCapture {
    pub folder: PathBuf,
    /// `stopped` or `uncertain`.
    pub outcome: String,
    /// Focal planes the camera completed (`completed_camera_events`).
    pub planes: usize,
    /// RAWs on this PC with a durable receipt and their recorded length.
    pub frames: usize,
    /// RAWs whose receipt is missing, not durable or whose file changed.
    pub unverified: usize,
    pub shots_per_plane: usize,
    pub message: Option<String>,
}
impl StoppedCapture {
    /// "stopped · N planes".
    pub fn label(&self) -> String {
        format!(
            "stopped · {} plane{}",
            self.planes,
            if self.planes == 1 { "" } else { "s" }
        )
    }
}
/// The newest run registered with this PC's receiver while it has no
/// `result.json`: the capture being written now, or one that ended without
/// finishing. `idle` is the time since its records last changed.
#[derive(Clone, Debug, PartialEq)]
pub(crate) struct InProgress {
    pub folder: PathBuf,
    pub idle: Duration,
    /// A test shot (manifest `capture_kind` "test", or a run this desktop
    /// took as one on a host without the capture kind): never followed.
    pub test: bool,
}
/// What a past capture's RAWs took on disk: the newest registered run of
/// each camera model with RAW receipts. The basis of the capture screen's
/// expected stack size.
#[derive(Clone, Debug, PartialEq, Serialize)]
pub(crate) struct StoredRaws {
    pub folder: PathBuf,
    pub model: String,
    /// The manifest's `raw_format` (`sony-uncompressed` is a plain CFA strip).
    pub raw_format: String,
    pub raws: usize,
    /// Mean original RAW bytes and mean bytes stored per RAW.
    pub original: u64,
    pub stored: u64,
    /// The receipts' storage encoding (one per run).
    pub encoding: String,
}

/// Format 2's size against format 1's on plain-CFA RAWs. MEASURED on the
/// A7CR scarab capture (784 RAWs, 51.21 GB to 49.00 GB, 2026-11-19).
pub(crate) const FORMAT_2_OVER_1: f64 = 49.00 / 51.21;

impl StoredRaws {
    /// Expected bytes on disk per RAW of a new capture with this camera, and
    /// how that was reckoned: the receiver now compresses (`compress`) in
    /// archive `format`.
    pub fn expected(&self, compress: bool, format: u8) -> (u64, String) {
        let last = format!("your last {} capture", self.model);
        match (compress, self.encoding.as_str()) {
            (false, _) => (self.original, format!("uncompressed, as {last}")),
            (true, "strehl-archive-v2") => (self.stored, format!("as {last}")),
            (true, "strehl-archive-v1")
                if format == 2 && self.raw_format == "sony-uncompressed" =>
            {
                (
                    (self.stored as f64 * FORMAT_2_OVER_1) as u64,
                    format!("{last} less 4 % for archive format 2"),
                )
            }
            (true, "strehl-archive-v1") => (self.stored, format!("as {last}")),
            _ => (self.original, format!("uncompressed size of {last}")),
        }
    }
}

/// [`StoredRaws`] of one run folder, or `None` without a manifest naming the
/// camera or with fewer than four RAW receipts.
pub(crate) fn stored_raws(folder: &Path) -> Option<StoredRaws> {
    let manifest: Value =
        serde_json::from_slice(&read_file(&folder.join("manifest.json"), 4 * 1024 * 1024).ok()?)
            .ok()?;
    let model = manifest["initial_status"]["model"].as_str()?.to_owned();
    let raw_format = manifest["raw_format"].as_str().unwrap_or("").to_owned();
    let text = read_file(&folder.join("transfer-receipts.jsonl"), 64 * 1024 * 1024).ok()?;
    let (mut raws, mut original, mut stored) = (0u64, 0u64, 0u64);
    let mut encoding = String::new();
    for line in text.split(|b| *b == b'\n').filter(|l| !l.is_empty()) {
        let Ok(r) = serde_json::from_slice::<Value>(line) else {
            continue;
        };
        if !r["logical_name"]
            .as_str()
            .is_some_and(|n| n.ends_with(".ARW"))
            || r["ok"] != true
        {
            continue;
        }
        let (Some(b), Some(s)) = (r["bytes"].as_u64(), r["storage_bytes"].as_u64()) else {
            continue;
        };
        raws += 1;
        original += b;
        stored += s;
        encoding = r["storage_encoding"]
            .as_str()
            .unwrap_or("identity")
            .to_owned();
    }
    (raws >= 4).then(|| StoredRaws {
        folder: folder.to_owned(),
        model,
        raw_format,
        raws: raws as usize,
        original: original / raws,
        stored: stored / raws,
        encoding,
    })
}

/// Run folders' [`StoredRaws`] by the receipts' modification time, so an
/// unchanged run is not read again.
pub(crate) type StoredCache =
    BTreeMap<PathBuf, (Option<std::time::SystemTime>, Option<StoredRaws>)>;

/// The newest [`StoredRaws`] of each camera model among the registered runs.
fn stored_by_model(config_path: &Path, cache: &mut StoredCache) -> Result<Vec<StoredRaws>> {
    let mut found: Vec<StoredRaws> = Vec::new();
    let runs = registered_runs(config_path)?;
    cache.retain(|folder, _| runs.contains(folder));
    for folder in runs {
        let changed = folder
            .join("transfer-receipts.jsonl")
            .metadata()
            .and_then(|m| m.modified())
            .ok();
        let entry = match cache.get(&folder) {
            Some((when, s)) if *when == changed => s.clone(),
            _ => {
                let s = stored_raws(&folder);
                cache.insert(folder.clone(), (changed, s.clone()));
                s
            }
        };
        if let Some(s) = entry
            && !found.iter().any(|f| f.model == s.model)
        {
            found.push(s);
        }
    }
    Ok(found)
}

#[derive(Clone, Default)]
pub(crate) struct Snapshot {
    pub in_progress: Option<InProgress>,
    pub stored: Vec<StoredRaws>,
    /// The host's state as sent: passed through to the agent snapshot.
    pub state: Value,
    /// [`Self::state`], typed (see `capture-host.rs`). Set together with it
    /// by [`Self::set_state`].
    pub host: HostState,
    /// The state could not be read as [`HostState`]; `host` is then the
    /// default (disconnected, nothing editable).
    pub host_error: Option<String>,
    pub online: bool,
    pub observed: Option<Instant>,
    pub connection_error: Option<String>,
    pub command_error: Option<String>,
    /// The last success notice ("Request accepted"); see [`Self::notice_id`].
    pub notice: Option<String>,
    /// Counts notices set, so a reader can tell a new one from one it saw.
    pub notice_id: u64,
    pub pending: bool,
    pub receiver: Value,
    pub receiver_error: Option<String>,
    pub completed: Vec<CompletedStack>,
    /// Stopped and uncertain captures, newest first.
    pub stopped: Vec<StoppedCapture>,
    pub preview: Option<(u64, Arc<egui::ColorImage>)>,
    pub peaking: Option<(u64, Arc<crate::capture_aids::Peaking>)>,
    /// The live JPEG's histogram and clipped share, from the same image as
    /// `peaking` (an estimate, not the RAW).
    pub levels: Option<(u64, Arc<crate::capture_aids::PreviewLevels>)>,
    pub preview_error: Option<String>,
    pub handoff: Option<PathBuf>,
    /// Test shots this desktop took (bounded): kept out of the lists even
    /// on a host whose manifests cannot say so.
    pub test_runs: BTreeSet<PathBuf>,
}
impl Snapshot {
    pub fn fresh(&self) -> bool {
        self.online
            && self
                .observed
                .is_some_and(|t| t.elapsed() < Duration::from_secs(5))
    }
    pub fn public(&self) -> Value {
        json!({"online":self.fresh(),"state":self.state,"pending":self.pending,
            "connection_error":self.connection_error,"command_error":self.command_error,"notice":self.notice,
            "receiver":self.receiver,"receiver_error":self.receiver_error,"completed":self.completed,
            "stopped":self.stopped,"host_state_error":self.host_error,
            "preview":self.preview.as_ref().map(|(generation,image)|json!({"generation":generation,"width":image.width(),"height":image.height()})),
            "preview_levels":self.levels.as_ref().map(|(generation,l)|json!({"generation":generation,"clipped_share":l.clipped_share,
                "median":l.percentile(0.5),"caution":crate::capture_aids::PreviewLevels::CAUTION})),
            "preview_error":self.preview_error,"stored_raws":self.stored,
            "in_progress":self.in_progress.as_ref().map(|r| json!({"folder":r.folder,"idle_seconds":r.idle.as_secs_f64()}))})
    }
    /// Replaces the host's state and its typed reading together.
    pub fn set_state(&mut self, state: Value) {
        match HostState::parse(&state) {
            Ok(host) => {
                self.host = host;
                self.host_error = None;
            }
            Err(e) => {
                self.host = HostState::default();
                self.host_error = Some(format!(
                    "The camera host sent a state this desktop cannot read ({e}); update the desktop or the host"
                ));
            }
        }
        self.state = state;
    }
    pub fn request(&self, command: Command) -> Result<CommandRequest> {
        ensure!(
            self.fresh(),
            "Reconnect to the Pi before sending a camera command"
        );
        if let Some(e) = &self.host_error {
            anyhow::bail!("{e}");
        }
        Ok(CommandRequest {
            id: strehl_capture::lan::new_key()?,
            camera_revision: self
                .host
                .camera_revision
                .context("Missing camera revision")?,
            plan_revision: self.host.plan_revision.context("Missing plan revision")?,
            sequence_id: self.host.sequence_id.context("Missing sequence")?,
            command,
        })
    }
    fn set_notice(&mut self, notice: &str) {
        self.notice = Some(notice.into());
        self.notice_id += 1;
    }
}

/// How often the client asks the camera host for its state, and whether it
/// fetches the live preview (Studio 2, section 7.4). The shell chooses it
/// through [`Cadence::choose`]; the client's loop waits this long between
/// polls, so a command or a cadence change is answered at once.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(crate) enum Cadence {
    /// The Capture station is closed and no sequence runs: 1 Hz, no preview.
    Background,
    /// A sequence runs with the station closed: 5 Hz, no preview.
    Sequence,
    /// The Capture station is open: 5 Hz with the live preview.
    Live,
}
impl Cadence {
    pub fn choose(station_open: bool, sequence_running: bool) -> Self {
        match (station_open, sequence_running) {
            (true, _) => Self::Live,
            (false, true) => Self::Sequence,
            (false, false) => Self::Background,
        }
    }
    pub fn interval(self) -> Duration {
        match self {
            Self::Background => Duration::from_millis(1000),
            Self::Sequence | Self::Live => Duration::from_millis(200),
        }
    }
    pub fn preview(self) -> bool {
        self == Self::Live
    }
    fn code(self) -> u8 {
        match self {
            Self::Background => 0,
            Self::Sequence => 1,
            Self::Live => 2,
        }
    }
    fn from_code(code: u8) -> Self {
        match code {
            0 => Self::Background,
            1 => Self::Sequence,
            _ => Self::Live,
        }
    }
}

/// Test shots remembered by the desktop, so a host without the capture kind
/// cannot list them; the newest few are enough.
const TEST_RUNS_KEPT: usize = 32;

enum Work {
    Command(CommandRequest),
    Configure(Config),
    StartReceiver,
    Storage {
        folder: PathBuf,
        compress_raw: bool,
    },
    Handoff(PathBuf),
    /// The cadence changed: poll now rather than at the old interval's end.
    /// Not a request: it neither waits for nor sets `pending`.
    Cadence,
}
pub(crate) struct Connection {
    shared: Arc<Mutex<Snapshot>>,
    sender: mpsc::SyncSender<Work>,
    /// [`Cadence`], read by the client thread before every wait.
    cadence: Arc<AtomicU8>,
    /// A fixture's state stays fresh: it has no client thread.
    fixture: bool,
}
impl Connection {
    /// A fixture's connection: it sends nothing, and nothing drives the
    /// camera from it.
    pub fn is_fixture(&self) -> bool {
        self.fixture
    }
    pub fn start(config: Config, path: PathBuf, ctx: egui::Context) -> Result<Self> {
        let shared = Arc::new(Mutex::new(Snapshot::default()));
        let (sender, receiver) = mpsc::sync_channel(2);
        let output = shared.clone();
        // Live until told otherwise: the cadence today's screen always had.
        let cadence = Arc::new(AtomicU8::new(Cadence::Live.code()));
        let thread_cadence = cadence.clone();
        std::thread::Builder::new()
            .name("strehl-capture-client".into())
            .spawn(move || {
                if let Err(error) = run(config, path, &output, receiver, &thread_cadence, &ctx) {
                    output.lock().unwrap().connection_error = Some(format!("{error:#}"));
                    ctx.request_repaint();
                }
            })?;
        Ok(Self {
            shared,
            sender,
            cadence,
            fixture: false,
        })
    }
    pub fn cadence(&self) -> Cadence {
        Cadence::from_code(self.cadence.load(Ordering::Relaxed))
    }
    /// Sets how often the host is polled; a change wakes the client.
    pub fn set_cadence(&self, cadence: Cadence) {
        if self.cadence.swap(cadence.code(), Ordering::Relaxed) != cadence.code() {
            // Best effort: a full channel already wakes the client.
            let _ = self.sender.try_send(Work::Cadence);
        }
    }
    /// Keeps a run that is not a stack (a test shot this desktop took, or a
    /// calibration survey it stopped waiting for) out of the completed and
    /// stopped lists and out of following, whatever its manifest says.
    pub fn mark_test_run(&self, folder: PathBuf) {
        let mut s = self.shared.lock().unwrap();
        s.test_runs.insert(folder);
        while s.test_runs.len() > TEST_RUNS_KEPT {
            let first = s.test_runs.iter().next().cloned().unwrap();
            s.test_runs.remove(&first);
        }
        let runs = s.test_runs.clone();
        s.completed.retain(|c| !runs.contains(&c.folder));
        s.stopped.retain(|c| !runs.contains(&c.folder));
    }
    pub fn snapshot(&self) -> Snapshot {
        let mut s = self.shared.lock().unwrap().clone();
        if self.fixture {
            s.observed = Some(Instant::now());
        }
        s
    }
    fn send(&self, work: Work) -> Result<()> {
        let mut s = self.shared.lock().unwrap();
        ensure!(!s.pending, "Wait for the previous control request");
        self.sender
            .try_send(work)
            .context("Capture connection is unavailable")?;
        s.pending = true;
        s.command_error = None;
        s.notice = None;
        Ok(())
    }
    pub fn command(&self, request: CommandRequest) -> Result<()> {
        self.send(Work::Command(request))
    }
    pub fn configure(&self, config: Config) -> Result<()> {
        self.send(Work::Configure(config))
    }
    pub fn start_receiver(&self) -> Result<()> {
        self.send(Work::StartReceiver)
    }
    pub fn handoff(&self, folder: PathBuf) -> Result<()> {
        self.send(Work::Handoff(folder))
    }
    pub fn take_handoff(&self) -> Option<PathBuf> {
        self.shared.lock().unwrap().handoff.take()
    }
    pub fn storage(&self, folder: PathBuf, compress_raw: bool) -> Result<()> {
        self.send(Work::Storage {
            folder,
            compress_raw,
        })
    }
}

/// What a [`Connection::detached`] was asked to send.
#[cfg(test)]
pub(crate) struct TestInbox(mpsc::Receiver<Work>);

#[cfg(test)]
impl TestInbox {
    /// The next camera command sent, if any.
    pub fn command(&self) -> Option<CommandRequest> {
        loop {
            match self.0.try_recv().ok()? {
                Work::Command(request) => return Some(request),
                _ => continue,
            }
        }
    }
}

impl Connection {
    /// A connection without a client thread that shows `snapshot` and sends
    /// nothing (every request fails as "unavailable"): the offscreen
    /// fixtures (`--capture-fixture`).
    pub fn fixture(snapshot: Snapshot) -> Self {
        let (sender, _) = mpsc::sync_channel(1);
        Self {
            shared: Arc::new(Mutex::new(snapshot)),
            sender,
            cadence: Arc::new(AtomicU8::new(Cadence::Live.code())),
            fixture: true,
        }
    }
}

#[cfg(test)]
impl Connection {
    /// A connection without a client thread, showing `snapshot`; what it is
    /// asked to send waits in the inbox.
    pub fn detached(snapshot: Snapshot) -> (Self, TestInbox) {
        let (sender, receiver) = mpsc::sync_channel(8);
        (
            Self {
                shared: Arc::new(Mutex::new(snapshot)),
                sender,
                cadence: Arc::new(AtomicU8::new(Cadence::Live.code())),
                fixture: false,
            },
            TestInbox(receiver),
        )
    }
    /// Replaces the snapshot, as the client thread would after a poll.
    pub fn replace(&self, snapshot: Snapshot) {
        *self.shared.lock().unwrap() = snapshot;
    }
}

fn client() -> Result<Client> {
    Ok(Client::builder()
        .no_proxy()
        .redirect(reqwest::redirect::Policy::none())
        .connect_timeout(Duration::from_secs(1))
        .timeout(Duration::from_secs(3))
        .build()?)
}
fn read_response(response: Response, limit: u64) -> Result<Vec<u8>> {
    ensure!(
        response.status().is_success(),
        "Server refused request (HTTP {})",
        response.status()
    );
    let mut bytes = Vec::new();
    response.take(limit + 1).read_to_end(&mut bytes)?;
    ensure!(
        bytes.len() as u64 <= limit,
        "Response exceeds the capture preview limit"
    );
    Ok(bytes)
}
fn get_json(client: &Client, base: &str, path: &str, key: &str) -> Result<Value> {
    Ok(serde_json::from_slice(&read_response(
        client
            .get(format!("{base}{path}"))
            .bearer_auth(key)
            .send()?,
        1024 * 1024,
    )?)?)
}
fn post_json(
    client: &Client,
    base: &str,
    path: &str,
    key: &str,
    value: &impl Serialize,
) -> Result<Value> {
    // There is intentionally no retry loop here. An unanswered exposure request
    // may have succeeded; read state and explicitly recover instead of replaying.
    let response = client
        .post(format!("{base}{path}"))
        .bearer_auth(key)
        .json(value)
        .send()
        .context(
            "No acknowledgement; request was not retried. Check camera status before trying again",
        )?;
    let status = response.status();
    let mut bytes = Vec::new();
    response.take(1024 * 1024 + 1).read_to_end(&mut bytes)?;
    ensure!(bytes.len() <= 1024 * 1024, "Oversized command reply");
    let value: Value = serde_json::from_slice(&bytes)?;
    ensure!(
        status.is_success(),
        "{}",
        value["error"]
            .as_str()
            .unwrap_or("Request refused; refresh state and try again")
    );
    Ok(value)
}
/// Error correction: hands the in-capture checker's verdicts to this PC's
/// receiver, where the camera host reads them by group.
pub(crate) fn post_verdicts(config: &Config, run: &str, verdicts: &[Value]) -> Result<()> {
    let (settings, url) = receiver_config(config)?;
    post_json(
        &client()?,
        &url,
        &format!("/api/runs/{run}/verdicts"),
        &settings.key,
        &json!({"verdicts":verdicts}),
    )?;
    Ok(())
}
fn receiver_config(config: &Config) -> Result<(ReceiverConfig, String)> {
    let value: ReceiverConfig = serde_json::from_slice(&read_file(&config.receiver_config, 65536)?)
        .context("Read this PC's receiver settings")?;
    ensure!(
        value.bind.ip().is_unspecified() || value.bind.ip().is_loopback(),
        "Receiver must also listen on loopback for native settings"
    );
    Ok((
        value.clone(),
        format!("http://127.0.0.1:{}", value.bind.port()),
    ))
}
fn start_receiver(config: &Config, client: &Client) -> Result<()> {
    let (settings, url) = receiver_config(config)?;
    if get_json(client, &url, "/api/status", &settings.key).is_ok() {
        return Ok(());
    }
    let parent = config
        .receiver_config
        .parent()
        .context("Receiver settings directory")?;
    let log = std::fs::OpenOptions::new()
        .create(true)
        .append(true)
        .open(parent.join("strehl-receiver.log"))?;
    let mut process = std::process::Command::new(std::env::current_exe()?);
    process
        .args(["--capture-receiver", "--config"])
        .arg(&config.receiver_config)
        .stdin(std::process::Stdio::null())
        .stdout(log.try_clone()?)
        .stderr(log);
    #[cfg(windows)]
    {
        use std::os::windows::process::CommandExt;
        process.creation_flags(0x08000000 | 0x00000200); // no console; separate Ctrl-C group
    }
    let mut child = process.spawn().context("Start background receiver")?;
    // Reap only our own child, without tying its lifetime to the editing window.
    std::thread::spawn(move || {
        let _ = child.wait();
    });
    Ok(())
}

fn run(
    mut config: Config,
    path: PathBuf,
    output: &Arc<Mutex<Snapshot>>,
    requests: mpsc::Receiver<Work>,
    cadence: &AtomicU8,
    ctx: &egui::Context,
) -> Result<()> {
    let client = client()?;
    let mut configured = config.normalize().is_ok();
    let mut receiver_due = Instant::now();
    let mut history_due = Instant::now();
    let mut stored_cache = StoredCache::new();
    let mut kind_cache = KindCache::new();
    let mut last_preview = None;
    loop {
        let pace = Cadence::from_code(cadence.load(Ordering::Relaxed));
        match requests.recv_timeout(pace.interval()) {
            Err(mpsc::RecvTimeoutError::Disconnected) => return Ok(()),
            Err(mpsc::RecvTimeoutError::Timeout) => {}
            Ok(Work::Cadence) => {}
            Ok(work) => {
                let result = (|| -> Result<&str> {
                    match work {
                        Work::Command(request) => {
                            ensure!(configured, "Configure the Pi connection first");
                            let reply = post_json(
                                &client,
                                &config.controller,
                                "/api/command",
                                &config.pairing_key,
                                &request,
                            )?;
                            if let Some(live) =
                                reply.get("state").filter(|v| v["camera_revision"].is_u64())
                            {
                                let mut s = output.lock().unwrap();
                                s.set_state(live.clone());
                                s.observed = Some(Instant::now());
                                s.online = true;
                                s.connection_error = None;
                            }
                            Ok("Request accepted")
                        }
                        Work::Configure(mut next) => {
                            next.normalize()?;
                            save_json(&path, &next)?;
                            config = next;
                            configured = true;
                            last_preview = None;
                            let mut s = output.lock().unwrap();
                            s.set_state(Value::Null);
                            s.preview = None;
                            s.online = false;
                            Ok("Connection saved")
                        }
                        Work::StartReceiver => {
                            start_receiver(&config, &client)?;
                            Ok("Receiver started or already available")
                        }
                        Work::Storage {
                            folder,
                            compress_raw,
                        } => {
                            let (settings, url) = receiver_config(&config)?;
                            post_json(
                                &client,
                                &url,
                                "/api/folder",
                                &settings.key,
                                &json!({"folder":folder,"compress_raw":compress_raw}),
                            )?;
                            Ok("Storage saved for new stacks; active stacks keep their destination")
                        }
                        Work::Handoff(folder) => {
                            let tests = output.lock().unwrap().test_runs.clone();
                            let registered = registered_runs(&config.receiver_config)?;
                            ensure!(
                                registered.contains(&folder) && !tests.contains(&folder),
                                "Choose a capture registered with this receiver"
                            );
                            let notice = if verify_completed(&folder).is_ok() {
                                "Completed capture ready for Projects"
                            } else {
                                verify_stopped(&folder).context(
                                    "Choose a completed or stopped capture registered with this receiver",
                                )?;
                                "Stopped capture ready for Projects"
                            };
                            output.lock().unwrap().handoff = Some(folder);
                            Ok(notice)
                        }
                        Work::Cadence => Ok("Cadence changed"),
                    }
                })();
                let mut s = output.lock().unwrap();
                s.pending = false;
                match result {
                    Ok(notice) => s.set_notice(notice),
                    Err(e) => s.command_error = Some(format!("{e:#}")),
                }
                receiver_due = Instant::now();
            }
        }
        if configured {
            match get_json(
                &client,
                &config.controller,
                "/api/state",
                &config.pairing_key,
            )
            .and_then(|state| {
                ensure!(
                    state["camera_revision"].is_u64(),
                    "Unexpected camera state response"
                );
                Ok(state)
            }) {
                Ok(state) => {
                    let generation = state["preview"]["generation"].as_u64();
                    let available = state["preview"]["available"] == true;
                    {
                        let mut s = output.lock().unwrap();
                        s.set_state(state);
                        s.online = true;
                        s.observed = Some(Instant::now());
                        s.connection_error = None;
                    }
                    // No preview is fetched while nobody shows it.
                    if pace.preview() && available && generation != last_preview {
                        let preview = (|| -> Result<egui::ColorImage> {
                            let bytes = read_response(
                                client
                                    .get(format!("{}/api/preview", config.controller))
                                    .bearer_auth(&config.pairing_key)
                                    .send()?,
                                8 * 1024 * 1024,
                            )?;
                            let mut reader = image::ImageReader::with_format(
                                std::io::Cursor::new(bytes),
                                image::ImageFormat::Jpeg,
                            );
                            let mut limits = image::Limits::default();
                            limits.max_image_width = Some(8192);
                            limits.max_image_height = Some(8192);
                            limits.max_alloc = Some(128 * 1024 * 1024);
                            reader.limits(limits);
                            let rgb = reader.decode()?.to_rgb8();
                            Ok(egui::ColorImage::from_rgb(
                                [rgb.width() as usize, rgb.height() as usize],
                                rgb.as_raw(),
                            ))
                        })();
                        let peaks = preview
                            .as_ref()
                            .ok()
                            .map(crate::capture_aids::Peaking::analyze);
                        let levels = preview
                            .as_ref()
                            .ok()
                            .map(crate::capture_aids::PreviewLevels::analyze);
                        let mut s = output.lock().unwrap();
                        match preview {
                            Ok(image) => {
                                s.peaking = peaks.map(|p| (generation.unwrap_or(0), Arc::new(p)));
                                s.levels = levels.map(|l| (generation.unwrap_or(0), Arc::new(l)));
                                s.preview = Some((generation.unwrap_or(0), Arc::new(image)));
                                s.preview_error = None;
                                last_preview = generation;
                            }
                            Err(e) => s.preview_error = Some(format!("{e:#}")),
                        }
                    }
                }
                Err(error) => {
                    let mut s = output.lock().unwrap();
                    s.online = false;
                    s.connection_error = Some(format!("{error:#}"));
                }
            }
        }
        if Instant::now() >= receiver_due {
            let tests = output.lock().unwrap().test_runs.clone();
            let mut in_progress = in_progress_run(&config.receiver_config).unwrap_or(None);
            if let Some(run) = &mut in_progress {
                run.test = tests.contains(&run.folder) || is_test_run(&run.folder, &mut kind_cache);
            }
            output.lock().unwrap().in_progress = in_progress;
            let result = receiver_config(&config)
                .and_then(|(settings, url)| get_json(&client, &url, "/api/status", &settings.key));
            let mut s = output.lock().unwrap();
            match result {
                Ok(receiver) => {
                    s.receiver = receiver;
                    s.receiver_error = None;
                }
                Err(e) => {
                    s.receiver = Value::Null;
                    s.receiver_error = Some(format!("{e:#}"));
                }
            }
            receiver_due = Instant::now() + Duration::from_secs(2);
        }
        if Instant::now() >= history_due {
            let tests = output.lock().unwrap().test_runs.clone();
            let (completed, stopped) =
                finished_captures(&config.receiver_config, &tests).unwrap_or_default();
            let stored =
                stored_by_model(&config.receiver_config, &mut stored_cache).unwrap_or_default();
            let mut s = output.lock().unwrap();
            s.completed = completed;
            s.stopped = stopped;
            s.stored = stored;
            drop(s);
            history_due = Instant::now() + Duration::from_secs(5);
        }
        ctx.request_repaint();
    }
}

fn read_file(path: &Path, max: u64) -> Result<Vec<u8>> {
    let mut bytes = Vec::new();
    std::fs::File::open(path)?
        .take(max + 1)
        .read_to_end(&mut bytes)?;
    ensure!(bytes.len() as u64 <= max, "Capture metadata too large");
    Ok(bytes)
}
/// Handoff trusts the receiver's durable checksum acknowledgements and rechecks
/// completeness and file lengths. RAW decoding independently verifies archives.
pub(crate) fn verify_completed(folder: &Path) -> Result<CompletedStack> {
    let result: Value = serde_json::from_slice(&read_file(&folder.join("result.json"), 65536)?)?;
    ensure!(
        result["outcome"] == "complete" && result["raw_file_verification"] == "pc-durable-sha256",
        "Capture is not durably complete"
    );
    let manifest: Value =
        serde_json::from_slice(&read_file(&folder.join("manifest.json"), 4 * 1024 * 1024)?)?;
    ensure!(
        manifest["capture_kind"] != "test",
        "A test shot is not a stack"
    );
    let planes = manifest["focus_positions"]
        .as_array()
        .context("Missing focal planes")?
        .len();
    let shots = manifest["camera"]["pixel_shift_shots"]
        .as_u64()
        .unwrap_or(1) as usize;
    ensure!(
        planes > 0 && planes <= 65536 && matches!(shots, 1 | 4 | 16),
        "Invalid capture count"
    );
    ensure!(
        result["completed_camera_events"].as_u64() == Some(planes as u64),
        "Incomplete focal planes"
    );
    let mut receipts = BTreeMap::new();
    for line in read_file(&folder.join("transfer-receipts.jsonl"), 64 * 1024 * 1024)?
        .split(|b| *b == b'\n')
        .filter(|l| !l.is_empty())
    {
        let r: Value = serde_json::from_slice(line)?;
        if let Some(name) = r["logical_name"].as_str().filter(|n| n.ends_with(".ARW")) {
            receipts.insert(name.to_owned(), r);
        }
    }
    // Error correction can take a plane's group again during the capture, so
    // a complete run has at least one group a plane, in whole groups, with
    // every RAW it numbered received.
    let frames = receipts.len();
    ensure!(
        frames >= planes * shots && frames.is_multiple_of(shots),
        "Incomplete RAW receipts"
    );
    for ordinal in 1..=frames {
        let name = format!("frame-{ordinal:06}.ARW");
        let r = receipts.get(&name).context("Missing RAW member")?;
        ensure!(
            r["durable"] == true
                && r["ok"] == true
                && r["sha256"].as_str().is_some_and(|h| h.len() == 64),
            "RAW has no durable receipt"
        );
        let stored = match r["storage_encoding"].as_str() {
            Some("strehl-archive-v1" | "strehl-archive-v2") => format!("{name}.straw"),
            Some("identity") | None => name,
            _ => anyhow::bail!("Unknown RAW storage format"),
        };
        let file = folder.join(stored);
        ensure!(
            file.canonicalize()?.parent() == Some(folder.canonicalize()?.as_path()),
            "RAW escapes capture folder"
        );
        let expected = r["storage_bytes"]
            .as_u64()
            .or_else(|| r["bytes"].as_u64())
            .context("Missing RAW length")?;
        ensure!(
            expected > 0 && file.metadata()?.len() == expected,
            "RAW length changed after receipt"
        );
    }
    Ok(CompletedStack {
        folder: folder.to_owned(),
        frames,
        planes,
        shots_per_plane: shots,
    })
}
/// The relaxed check for a capture that ended early (see [`StoppedCapture`]):
/// its result says `stopped` or `uncertain`, it is not a test shot, the
/// camera completed at least one plane, and at least one RAW has a durable
/// receipt with its file at the recorded length. Unlike
/// [`verify_completed`] it does not require every planned plane or a
/// gapless set of RAWs; it counts what it could not verify instead.
pub(crate) fn verify_stopped(folder: &Path) -> Result<StoppedCapture> {
    let result: Value = serde_json::from_slice(&read_file(&folder.join("result.json"), 65536)?)?;
    let outcome = result["outcome"].as_str().unwrap_or_default().to_owned();
    ensure!(
        matches!(outcome.as_str(), "stopped" | "uncertain"),
        "Not a stopped capture"
    );
    let manifest: Value =
        serde_json::from_slice(&read_file(&folder.join("manifest.json"), 4 * 1024 * 1024)?)?;
    ensure!(
        manifest["capture_kind"] != "test",
        "A test shot is not a stack"
    );
    let planes = result["completed_camera_events"].as_u64().unwrap_or(0) as usize;
    ensure!(planes > 0, "No focal plane was captured");
    let shots = manifest["camera"]["pixel_shift_shots"]
        .as_u64()
        .or_else(|| manifest["pixel_shift_shots"].as_u64())
        .unwrap_or(1) as usize;
    let canonical = folder.canonicalize()?;
    let (mut frames, mut unverified) = (0, 0);
    let mut seen = BTreeSet::new();
    for line in read_file(&folder.join("transfer-receipts.jsonl"), 64 * 1024 * 1024)?
        .split(|b| *b == b'\n')
        .filter(|l| !l.is_empty())
    {
        let Ok(r) = serde_json::from_slice::<Value>(line) else {
            unverified += 1;
            continue;
        };
        let Some(name) = r["logical_name"].as_str().filter(|n| n.ends_with(".ARW")) else {
            continue;
        };
        if !seen.insert(name.to_owned()) {
            continue;
        }
        let stored = match r["storage_encoding"].as_str() {
            Some("strehl-archive-v1" | "strehl-archive-v2") => format!("{name}.straw"),
            Some("identity") | None => name.to_owned(),
            _ => {
                unverified += 1;
                continue;
            }
        };
        let file = folder.join(stored);
        let expected = r["storage_bytes"].as_u64().or_else(|| r["bytes"].as_u64());
        let good = r["durable"] == true
            && r["ok"] == true
            && r["sha256"].as_str().is_some_and(|h| h.len() == 64)
            && file
                .canonicalize()
                .is_ok_and(|f| f.parent() == Some(canonical.as_path()))
            && expected.is_some_and(|n| n > 0 && file.metadata().is_ok_and(|m| m.len() == n));
        if good {
            frames += 1;
        } else {
            unverified += 1;
        }
    }
    ensure!(frames > 0, "No RAW of this capture is saved on this PC");
    Ok(StoppedCapture {
        folder: folder.to_owned(),
        outcome,
        planes,
        frames,
        unverified,
        shots_per_plane: shots,
        message: result["message"].as_str().map(str::to_owned),
    })
}
/// Whether a run's manifest names it a test shot, cached per folder (a
/// manifest never changes once written).
type KindCache = BTreeMap<PathBuf, bool>;
fn is_test_run(folder: &Path, cache: &mut KindCache) -> bool {
    if let Some(known) = cache.get(folder) {
        return *known;
    }
    let Some(manifest) = read_file(&folder.join("manifest.json"), 4 * 1024 * 1024)
        .ok()
        .and_then(|b| serde_json::from_slice::<Value>(&b).ok())
    else {
        // Not written yet: ask again next time.
        return false;
    };
    let test = manifest["capture_kind"] == "test";
    if cache.len() > 64 {
        cache.clear();
    }
    cache.insert(folder.to_owned(), test);
    test
}
/// The receiver's existing run folders, most recently active first.
/// Identifiers do not order runs: most are `stack-<unix ms>-<pid>`, but a
/// hand-named run (`stack-wifi-check-...`) sorts after all of them.
fn registered_runs(config_path: &Path) -> Result<Vec<PathBuf>> {
    let registry: BTreeMap<String, Value> = serde_json::from_slice(&read_file(
        &config_path.with_extension("runs.json"),
        8 * 1024 * 1024,
    )?)?;
    let mut runs: Vec<(std::time::SystemTime, PathBuf)> = registry
        .values()
        .filter_map(|entry| entry.as_str().or_else(|| entry["folder"].as_str()))
        .map(PathBuf::from)
        .filter_map(|folder| last_activity(&folder).map(|t| (t, folder)))
        .collect();
    runs.sort_by_key(|(changed, _)| std::cmp::Reverse(*changed));
    Ok(runs
        .into_iter()
        .take(32)
        .map(|(_, folder)| folder)
        .collect())
}
/// When a run folder last changed: the folder itself (a file was added) or
/// the two records the receiver appends to and replaces.
fn last_activity(folder: &Path) -> Option<std::time::SystemTime> {
    [
        folder.to_path_buf(),
        folder.join("events.jsonl"),
        folder.join("transfer-receipts.jsonl"),
    ]
    .iter()
    .filter_map(|p| p.metadata().and_then(|m| m.modified()).ok())
    .max()
}
/// See [`InProgress`]. Only the most recently active registered run is
/// considered, and only once its capture journal exists (the engine follows
/// nothing without it).
pub(crate) fn in_progress_run(config_path: &Path) -> Result<Option<InProgress>> {
    let Some(folder) = registered_runs(config_path)?.into_iter().next() else {
        return Ok(None);
    };
    let events = folder.join("events.jsonl");
    if folder.join("result.json").exists() || !events.is_file() {
        return Ok(None);
    }
    let changed = [events, folder.join("transfer-receipts.jsonl")]
        .iter()
        .filter_map(|p| p.metadata().and_then(|m| m.modified()).ok())
        .max();
    let idle = changed
        .and_then(|t| t.elapsed().ok())
        .unwrap_or(Duration::ZERO);
    Ok(Some(InProgress {
        folder,
        idle,
        test: false,
    }))
}
/// Up to eight completed stacks and eight stopped captures among the newest
/// registered runs, newest first; never a run in `tests`.
fn finished_captures(
    config_path: &Path,
    tests: &BTreeSet<PathBuf>,
) -> Result<(Vec<CompletedStack>, Vec<StoppedCapture>)> {
    let (mut completed, mut stopped) = (Vec::new(), Vec::new());
    for folder in registered_runs(config_path)? {
        if tests.contains(&folder) {
            continue;
        }
        if completed.len() < 8
            && let Ok(stack) = verify_completed(&folder)
        {
            completed.push(stack);
        } else if stopped.len() < 8
            && let Ok(run) = verify_stopped(&folder)
        {
            stopped.push(run);
        }
        if completed.len() == 8 && stopped.len() == 8 {
            break;
        }
    }
    Ok((completed, stopped))
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn pairing_is_numeric_lan_only_and_removes_secret_from_url() {
        let mut c = Config {
            controller: "http://10.0.0.178:8787/#key=abcdefghijklmnop".into(),
            ..Config::default()
        };
        c.normalize().unwrap();
        assert_eq!(c.controller, "http://10.0.0.178:8787");
        for url in [
            "https://10.0.0.178:8787",
            "http://example.org",
            "http://8.8.8.8",
            "http://10.0.1.2",
            "http://u:p@10.0.0.2",
            "http://10.0.0.2/?key=secret",
        ] {
            c.controller = url.into();
            assert!(c.normalize().is_err(), "{url}");
        }
    }
    #[test]
    fn request_preserves_camera_revisions_and_requires_fresh_state() {
        let mut s = Snapshot {
            online: true,
            observed: Some(Instant::now()),
            ..Default::default()
        };
        s.set_state(json!({"camera_revision":7,"plan_revision":9,"sequence_id":4}));
        let a = s.request(Command::Start {}).unwrap();
        s.set_state(json!({"camera_revision":8,"plan_revision":9,"sequence_id":4}));
        assert_eq!(a.camera_revision, 7);
        assert_eq!(a.plan_revision, 9);
        assert_eq!(a.sequence_id, 4);
        assert_eq!(s.request(Command::Start {}).unwrap().camera_revision, 8);
        s.online = false;
        assert!(s.request(Command::Start {}).is_err());
    }
    /// A state the desktop cannot read sends nothing: the typed state falls
    /// back to "disconnected" and every request names the problem.
    #[test]
    fn an_unreadable_host_state_refuses_every_request() {
        let mut s = Snapshot {
            online: true,
            observed: Some(Instant::now()),
            ..Default::default()
        };
        s.set_state(
            json!({"camera_revision":7,"plan_revision":9,"sequence_id":4,"editable":"yes"}),
        );
        assert!(s.host_error.as_deref().unwrap().contains("cannot read"));
        assert!(!s.host.editable && s.host.camera_revision.is_none());
        assert_eq!(s.state["editable"], "yes", "the raw state passes through");
        let error = s.request(Command::Start {}).unwrap_err().to_string();
        assert!(error.contains("cannot read"), "{error}");
        s.set_state(json!({"camera_revision":7,"plan_revision":9,"sequence_id":4,"editable":true}));
        assert!(s.host_error.is_none() && s.host.editable);
        assert!(s.public()["host_state_error"].is_null());
    }
    #[test]
    fn cadence_is_slow_only_with_the_station_closed_and_nothing_running() {
        assert_eq!(Cadence::choose(false, false), Cadence::Background);
        assert_eq!(Cadence::choose(false, true), Cadence::Sequence);
        assert_eq!(Cadence::choose(true, false), Cadence::Live);
        assert_eq!(Cadence::choose(true, true), Cadence::Live);
        assert_eq!(Cadence::Background.interval(), Duration::from_secs(1));
        assert_eq!(Cadence::Sequence.interval(), Duration::from_millis(200));
        assert!(Cadence::Live.preview() && !Cadence::Sequence.preview());
        for c in [Cadence::Background, Cadence::Sequence, Cadence::Live] {
            assert_eq!(Cadence::from_code(c.code()), c);
        }
    }
    /// A run folder with `n` RAW receipts (single shot), its manifest and
    /// result; `kind` is the manifest's capture kind.
    fn run_folder(
        root: &Path,
        name: &str,
        outcome: &str,
        planned: usize,
        done: usize,
        kind: &str,
    ) -> PathBuf {
        let folder = root.join(name);
        std::fs::create_dir(&folder).unwrap();
        save_json(
            &folder.join("manifest.json"),
            &json!({"focus_positions":(0..planned).collect::<Vec<_>>(),"camera":{"pixel_shift_shots":1},
                "capture_kind":kind}),
        )
        .unwrap();
        let verification = if outcome == "uncertain" {
            "partial-see-transfer-receipts"
        } else {
            "pc-durable-sha256"
        };
        save_json(
            &folder.join("result.json"),
            &json!({"outcome":outcome,"raw_file_verification":verification,
                "completed_camera_events":done,"message":"Stopped by request"}),
        )
        .unwrap();
        let receipts: Vec<String> = (1..=done)
            .map(|n| {
                let name = format!("frame-{n:06}.ARW");
                std::fs::write(folder.join(format!("{name}.straw")), b"fixture").unwrap();
                json!({"logical_name":name,"ok":true,"durable":true,"sha256":"a".repeat(64),
                    "storage_bytes":7,"storage_encoding":"strehl-archive-v2"})
                .to_string()
            })
            .collect();
        std::fs::write(folder.join("transfer-receipts.jsonl"), receipts.join("\n")).unwrap();
        std::fs::write(folder.join("events.jsonl"), b"{}\n").unwrap();
        std::thread::sleep(Duration::from_millis(20));
        folder
    }
    /// The listing rules over real runs, read only: every run folder under
    /// `STREHL_CAPTURE_RUNS` is judged complete, stopped, test or neither.
    /// `cargo test -p strehl-ui real_runs_are_listed -- --ignored --nocapture`
    #[test]
    #[ignore = "reads real capture folders named by STREHL_CAPTURE_RUNS"]
    fn real_runs_are_listed() {
        let root = PathBuf::from(std::env::var_os("STREHL_CAPTURE_RUNS").unwrap());
        let mut seen = BTreeMap::<String, usize>::new();
        for entry in std::fs::read_dir(&root).unwrap() {
            let folder = entry.unwrap().path();
            if !folder.join("result.json").is_file() {
                continue;
            }
            let verdict = match (verify_completed(&folder), verify_stopped(&folder)) {
                (Ok(c), _) => format!("complete ({} planes)", c.planes),
                (Err(_), Ok(s)) => {
                    println!(
                        "{}: {} · {} RAWs, {} unverified ({})",
                        folder.display(),
                        s.label(),
                        s.frames,
                        s.unverified,
                        s.outcome
                    );
                    format!("{} ({})", s.label(), s.outcome)
                }
                (Err(c), Err(s)) => format!("neither: {c:#} / {s:#}"),
            };
            *seen.entry(verdict).or_default() += 1;
        }
        for (verdict, n) in seen {
            println!("{n:>4}  {verdict}");
        }
    }
    /// Stopped and uncertain captures are listed beside the completed ones
    /// with what was verified; a complete run is never "stopped", a stopped
    /// run is never "complete", and test shots are in neither list.
    #[test]
    fn stopped_captures_are_listed_and_test_shots_are_not() {
        stopped_captures_are_listed_and_test_shots_are_not_body();
    }

    /// Plan Q6's gate on a real capture stopped by hand
    /// (`STREHL_RIG_STOPPED` = its folder): it passes the stopped-capture
    /// check with its planes, so the review offers to stack them.
    #[test]
    #[ignore = "needs a rig capture (STREHL_RIG_STOPPED)"]
    fn a_rig_capture_stopped_by_hand_is_offered() {
        let Some(folder) = std::env::var_os("STREHL_RIG_STOPPED").map(PathBuf::from) else {
            return;
        };
        let run = verify_stopped(&folder).unwrap();
        println!(
            "{} · {} planes, {} RAWs, {} unverified",
            run.outcome, run.planes, run.frames, run.unverified
        );
        assert!(run.planes.min(run.frames / run.shots_per_plane.max(1)) >= 2);
    }

    fn stopped_captures_are_listed_and_test_shots_are_not_body() {
        let dir = tempfile::tempdir().unwrap();
        let config = dir.path().join("receiver.json");
        let complete = run_folder(dir.path(), "stack-1", "complete", 3, 3, "plan");
        let stopped = run_folder(dir.path(), "stack-2", "stopped", 10, 4, "plan");
        let uncertain = run_folder(dir.path(), "stack-3", "uncertain", 10, 2, "plan");
        let empty = run_folder(dir.path(), "stack-4", "stopped", 10, 0, "plan");
        let test = run_folder(dir.path(), "stack-5", "complete", 1, 1, "test");
        let old_host_test = run_folder(dir.path(), "stack-6", "complete", 1, 1, "positions");
        let registry: BTreeMap<String, Value> = [
            &complete,
            &stopped,
            &uncertain,
            &empty,
            &test,
            &old_host_test,
        ]
        .iter()
        .map(|f| {
            (
                f.file_name().unwrap().to_string_lossy().into_owned(),
                json!({ "folder": f }),
            )
        })
        .collect();
        save_json(&config.with_extension("runs.json"), &registry).unwrap();

        assert!(verify_completed(&complete).is_ok());
        assert!(
            verify_stopped(&complete).is_err(),
            "complete is not stopped"
        );
        assert!(
            verify_completed(&stopped).is_err(),
            "stopped is not complete"
        );
        let s = verify_stopped(&stopped).unwrap();
        assert_eq!((s.planes, s.frames, s.unverified), (4, 4, 0));
        assert_eq!(s.label(), "stopped · 4 planes");
        assert_eq!(s.outcome, "stopped");
        let u = verify_stopped(&uncertain).unwrap();
        assert_eq!((u.outcome.as_str(), u.planes), ("uncertain", 2));
        assert!(verify_stopped(&empty).is_err(), "nothing captured");
        let error = verify_completed(&test).unwrap_err().to_string();
        assert!(error.contains("test shot"), "{error}");

        // A file that changed after its receipt is counted, not trusted.
        std::fs::write(stopped.join("frame-000002.ARW.straw"), b"truncated!").unwrap();
        let s = verify_stopped(&stopped).unwrap();
        assert_eq!((s.frames, s.unverified), (3, 1));

        // The desktop remembers a test shot taken on an older host.
        let tests: BTreeSet<PathBuf> = [old_host_test.clone()].into_iter().collect();
        let (completed, listed) = finished_captures(&config, &tests).unwrap();
        let names = |f: &[PathBuf]| -> Vec<String> {
            f.iter()
                .map(|f| f.file_name().unwrap().to_string_lossy().into_owned())
                .collect()
        };
        assert_eq!(
            names(
                &completed
                    .iter()
                    .map(|c| c.folder.clone())
                    .collect::<Vec<_>>()
            ),
            ["stack-1"]
        );
        assert_eq!(
            names(&listed.iter().map(|c| c.folder.clone()).collect::<Vec<_>>()),
            ["stack-3", "stack-2"],
            "newest first"
        );
        let (completed, _) = finished_captures(&config, &BTreeSet::new()).unwrap();
        assert_eq!(
            completed.len(),
            2,
            "without the memory, a positions run is listed"
        );

        // A test shot in progress is recognised from its manifest.
        let mut cache = KindCache::new();
        assert!(is_test_run(&test, &mut cache));
        assert!(!is_test_run(&stopped, &mut cache));
        assert!(!is_test_run(&dir.path().join("missing"), &mut cache));
        assert_eq!(cache.len(), 2, "a missing manifest is asked again");
    }
    #[test]
    fn completed_handoff_requires_every_pixel_shift_member_and_durable_result() {
        let dir = tempfile::tempdir().unwrap();
        let folder = dir.path();
        save_json(
            &folder.join("manifest.json"),
            &json!({"focus_positions":[123],"camera":{"pixel_shift_shots":4}}),
        )
        .unwrap();
        let complete = json!({"outcome":"complete","raw_file_verification":"pc-durable-sha256","completed_camera_events":1});
        save_json(&folder.join("result.json"), &complete).unwrap();
        let mut receipts = Vec::new();
        for n in 1..=4 {
            let name = format!("frame-{n:06}.ARW");
            std::fs::write(folder.join(format!("{name}.straw")), b"fixture").unwrap();
            receipts.push(json!({"logical_name":name,"ok":true,"durable":true,"sha256":"a".repeat(64),"storage_bytes":7,"storage_encoding":"strehl-archive-v1"}).to_string());
        }
        let journal = folder.join("transfer-receipts.jsonl");
        std::fs::write(&journal, receipts[..3].join("\n")).unwrap();
        assert!(
            verify_completed(folder).is_err(),
            "a three-member group must fail"
        );
        std::fs::write(&journal, receipts.join("\n")).unwrap();
        assert_eq!(verify_completed(folder).unwrap().frames, 4);
        std::fs::write(folder.join("frame-000004.ARW.straw"), b"truncated").unwrap();
        assert!(
            verify_completed(folder).is_err(),
            "a changed file must fail"
        );
        std::fs::write(folder.join("frame-000004.ARW.straw"), b"fixture").unwrap();
        save_json(&folder.join("result.json"), &json!({"outcome":"stopped"})).unwrap();
        assert!(
            verify_completed(folder).is_err(),
            "stopped stacks must not be promoted"
        );
    }
    #[test]
    fn a_completed_capture_may_hold_whole_retaken_groups() {
        let dir = tempfile::tempdir().unwrap();
        let folder = dir.path();
        save_json(
            &folder.join("manifest.json"),
            &json!({"focus_positions":[123],"camera":{"pixel_shift_shots":4}}),
        )
        .unwrap();
        save_json(
            &folder.join("result.json"),
            &json!({"outcome":"complete","raw_file_verification":"pc-durable-sha256","completed_camera_events":1}),
        )
        .unwrap();
        let receipt = |n: usize| {
            let name = format!("frame-{n:06}.ARW");
            std::fs::write(folder.join(format!("{name}.straw")), b"fixture").unwrap();
            json!({"logical_name":name,"ok":true,"durable":true,"sha256":"a".repeat(64),"storage_bytes":7,"storage_encoding":"strehl-archive-v1"}).to_string()
        };
        let journal = folder.join("transfer-receipts.jsonl");
        // The plane's group, then its retake taken during the capture.
        let all: Vec<String> = (1..=8).map(receipt).collect();
        std::fs::write(&journal, all.join("\n")).unwrap();
        assert_eq!(verify_completed(folder).unwrap().frames, 8);
        std::fs::write(&journal, all[..7].join("\n")).unwrap();
        assert!(verify_completed(folder).is_err(), "a partial retake group");
        let gap: Vec<String> = all
            .iter()
            .take(4)
            .cloned()
            .chain([receipt(12)])
            .chain(all[5..8].iter().cloned())
            .collect();
        std::fs::write(&journal, gap.join("\n")).unwrap();
        assert!(verify_completed(folder).is_err(), "a missing frame number");
    }
    /// The newest run of each camera with RAW receipts gives its mean sizes;
    /// a run without a model or with too few RAWs gives nothing; an unchanged
    /// run is served from the cache, a changed one is read again.
    #[test]
    fn stored_sizes_come_from_each_cameras_newest_run() {
        let dir = tempfile::tempdir().unwrap();
        let config = dir.path().join("receiver.json");
        let run = |name: &str, model: Option<&str>, raws: usize, stored: u64, encoding: &str| {
            let folder = dir.path().join(name);
            std::fs::create_dir(&folder).unwrap();
            let mut manifest = json!({"raw_format":"sony-uncompressed"});
            if let Some(m) = model {
                manifest["initial_status"] = json!({"model": m});
            }
            save_json(&folder.join("manifest.json"), &manifest).unwrap();
            let lines: Vec<String> = (1..=raws)
                .map(|n| {
                    json!({"logical_name":format!("frame-{n:06}.ARW"),"ok":true,"bytes":100 + n as u64,
                        "storage_bytes":stored,"storage_encoding":encoding})
                    .to_string()
                })
                .chain([json!({"logical_name":"manifest.json","ok":true,"bytes":9,"storage_bytes":9,
                    "storage_encoding":"identity"})
                .to_string()])
                .collect();
            std::fs::write(folder.join("transfer-receipts.jsonl"), lines.join("\n")).unwrap();
            std::thread::sleep(Duration::from_millis(30));
            folder
        };
        let old_r = run("stack-1", Some("ILCE-7CR"), 8, 60, "strehl-archive-v1");
        let ii = run("stack-2", Some("ILCE-7CM2"), 4, 40, "strehl-archive-v1");
        let _few = run("stack-3", Some("ILCE-7CR"), 3, 10, "strehl-archive-v2");
        let _anonymous = run("stack-4", None, 8, 10, "strehl-archive-v2");
        let new_r = run("stack-5", Some("ILCE-7CR"), 4, 50, "strehl-archive-v2");
        save_json(
            &config.with_extension("runs.json"),
            &json!({"stack-1":old_r,"stack-2":ii,"stack-3":dir.path().join("stack-3"),
                "stack-4":dir.path().join("stack-4"),"stack-5":{"folder":new_r,"compress_raw":true}}),
        )
        .unwrap();
        let mut cache = StoredCache::new();
        let found = stored_by_model(&config, &mut cache).unwrap();
        assert_eq!(found.len(), 2);
        assert_eq!(found[0].folder, new_r);
        assert_eq!(
            (found[0].raws, found[0].original, found[0].stored),
            (4, 102, 50)
        );
        assert_eq!(found[0].encoding, "strehl-archive-v2");
        assert_eq!(
            (found[1].model.as_str(), found[1].stored),
            ("ILCE-7CM2", 40)
        );
        assert_eq!(cache.len(), 5);
        // The cache answers for unchanged runs; a changed run is read again.
        let ii_stored = |cache: &mut StoredCache| {
            stored_by_model(&config, cache)
                .unwrap()
                .into_iter()
                .find(|s| s.model == "ILCE-7CM2")
                .unwrap()
                .stored
        };
        cache.get_mut(&ii).unwrap().1.as_mut().unwrap().stored = 41;
        assert_eq!(ii_stored(&mut cache), 41);
        std::fs::write(
            ii.join("transfer-receipts.jsonl"),
            (1..=4)
                .map(|n| {
                    json!({"logical_name":format!("frame-{n:06}.ARW"),"ok":true,"bytes":100,
                        "storage_bytes":30,"storage_encoding":"strehl-archive-v1"})
                    .to_string()
                })
                .collect::<Vec<_>>()
                .join("\n"),
        )
        .unwrap();
        assert_eq!(ii_stored(&mut cache), 30);
        // What a new capture is expected to take, by the receiver's storage.
        let r = &found[0];
        assert_eq!(r.expected(true, 2).0, 50);
        assert_eq!(r.expected(false, 2).0, 102, "uncompressed: the originals");
        let v1 = StoredRaws {
            encoding: "strehl-archive-v1".into(),
            stored: 1000,
            ..r.clone()
        };
        assert_eq!(v1.expected(true, 2).0, (1000.0 * FORMAT_2_OVER_1) as u64);
        assert_eq!(
            v1.expected(true, 1).0,
            1000,
            "an older receiver keeps format 1"
        );
        let compressed_raws = StoredRaws {
            raw_format: "sony-lossless-compressed-raw-l".into(),
            ..v1.clone()
        };
        assert_eq!(
            compressed_raws.expected(true, 2).0,
            1000,
            "not a plain strip: format 1"
        );
    }
    #[test]
    fn only_the_newest_run_with_a_journal_and_no_result_is_in_progress() {
        let dir = tempfile::tempdir().unwrap();
        let config = dir.path().join("receiver.json");
        assert!(in_progress_run(&config).is_err(), "no registry");
        // A hand-named run sorts after every timestamped one; activity, not
        // the name, says which run is current.
        let old = dir.path().join("stack-wifi-check-1794458669");
        let new = dir.path().join("stack-1794000000500-2");
        std::fs::create_dir(&old).unwrap();
        std::fs::write(old.join("events.jsonl"), b"{}\n").unwrap();
        std::thread::sleep(Duration::from_millis(50));
        std::fs::create_dir(&new).unwrap();
        save_json(
            &config.with_extension("runs.json"),
            &json!({"stack-1794000000500-2":{"folder":new},"stack-wifi-check-1794458669":old,
                "stack-1794000000000-9":dir.path().join("deleted")}),
        )
        .unwrap();
        assert_eq!(
            in_progress_run(&config).unwrap(),
            None,
            "the newest run has no capture journal yet; an older run is never followed"
        );
        std::fs::write(new.join("events.jsonl"), b"{}\n").unwrap();
        let found = in_progress_run(&config).unwrap().unwrap();
        assert_eq!(found.folder, new);
        assert!(found.idle < Duration::from_secs(60));
        std::fs::write(new.join("result.json"), b"{}").unwrap();
        assert_eq!(in_progress_run(&config).unwrap(), None, "finished");
    }
    #[test]
    fn lost_acknowledgement_does_not_replay_an_exposure() {
        use std::net::TcpListener;
        let listener = TcpListener::bind("127.0.0.1:0").unwrap();
        let url = format!("http://{}", listener.local_addr().unwrap());
        listener.set_nonblocking(true).unwrap();
        let thread = std::thread::spawn(move || {
            let deadline = Instant::now() + Duration::from_secs(5);
            let mut socket = loop {
                if let Ok((socket, _)) = listener.accept() {
                    break socket;
                }
                assert!(
                    Instant::now() < deadline,
                    "The test client did not reach the listener"
                );
                std::thread::sleep(Duration::from_millis(10));
            };
            // Windows can inherit the listening socket's nonblocking mode.
            // Read the full request before simulating a lost acknowledgement.
            socket.set_nonblocking(false).unwrap();
            socket
                .set_read_timeout(Some(Duration::from_secs(3)))
                .unwrap();
            let mut bytes = Vec::new();
            let mut buf = [0; 2048];
            loop {
                let count = socket.read(&mut buf).unwrap();
                if count == 0 {
                    break;
                }
                bytes.extend_from_slice(&buf[..count]);
                if bytes.windows(7).any(|w| w == b"\"start\"") {
                    break;
                }
            }
            assert!(bytes.windows(7).any(|w| w == b"\"start\""));
            drop(socket);
            listener.set_nonblocking(true).unwrap();
            std::thread::sleep(Duration::from_millis(250));
            assert!(
                listener.accept().is_err(),
                "capture was retried after the server accepted it"
            );
        });
        let result = post_json(
            &client().unwrap(),
            &url,
            "/api/command",
            "abcdefghijklmnop",
            &json!({"operation":"start"}),
        );
        assert!(result.is_err());
        thread.join().unwrap();
    }
}
