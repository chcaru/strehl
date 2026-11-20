//! Camera -> bounded tmpfs queue -> PC. Never retry a shutter.
use crate::{
    backend::{Camera, Native, Preview},
    lan::Lan,
    receiver::{MAX_RAW, hash_file, save_json},
    transport,
};
use anyhow::{Context, Result, ensure};
use serde::{Deserialize, Serialize};
use serde_json::{Value, json};
use sha2::{Digest, Sha256};
use std::{
    collections::VecDeque,
    path::{Path, PathBuf},
    sync::{
        Arc, Condvar, Mutex,
        atomic::{AtomicBool, Ordering},
    },
    thread::{self, JoinHandle},
    time::{Duration, Instant},
};

pub type TransferReport = Arc<Mutex<Value>>;
#[derive(Clone, Serialize, Deserialize)]
pub struct TransferConfig {
    pub receiver: String,
    pub key: String,
    pub lan: String,
    pub ram_directory: PathBuf,
    pub state_directory: PathBuf,
    /// Automatic, negotiated, exact transport compression. Disable for diagnosis.
    #[serde(default = "default_compression")]
    pub transport_compression: bool,
}
fn default_compression() -> bool {
    true
}
#[derive(Clone)]
pub struct Sink {
    config: TransferConfig,
    client: reqwest::blocking::Client,
    report: TransferReport,
    compression: Arc<AtomicBool>,
    journal_append: Arc<AtomicBool>,
    encoders: Arc<rayon::ThreadPool>,
}
/// The receiver appends the body to its copy of `events.jsonl` when the copy
/// is exactly this many bytes long.
pub const APPEND_HEADER: &str = "x-append-offset";

/// An upload that must not be retried.
#[derive(Debug)]
struct Fatal(&'static str);
impl std::fmt::Display for Fatal {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.write_str(self.0)
    }
}
impl std::error::Error for Fatal {}
impl Sink {
    pub fn new(config: TransferConfig, report: TransferReport) -> Result<Self> {
        let url = reqwest::Url::parse(&config.receiver)?;
        ensure!(
            url.scheme() == "http"
                && url.username().is_empty()
                && url.password().is_none()
                && url.query().is_none()
                && url.fragment().is_none(),
            "Receiver must be a local HTTP endpoint without credentials in its URL"
        );
        let ip: std::net::IpAddr = url
            .host_str()
            .context("Receiver address missing")?
            .parse()
            .context("Use the receiver's numeric LAN IPv4 address")?;
        ensure!(
            Lan::parse(&config.lan)?.permits(ip),
            "Receiver must be on the configured LAN"
        );
        ensure!(config.key.len() >= 48, "Missing receiver key");
        let client = reqwest::blocking::Client::builder()
            .no_proxy()
            .redirect(reqwest::redirect::Policy::none())
            .connect_timeout(Duration::from_secs(5))
            .timeout(Duration::from_secs(90))
            .build()?;
        Ok(Self {
            config,
            client,
            report,
            compression: Arc::new(AtomicBool::new(false)),
            journal_append: Arc::new(AtomicBool::new(false)),
            encoders: Arc::new(
                rayon::ThreadPoolBuilder::new()
                    .num_threads(transport::WORKERS)
                    .thread_name(|i| format!("raw-compress-{i}"))
                    .build()?,
            ),
        })
    }
    fn note(&self, value: Value) {
        let mut report = self.report.lock().unwrap();
        if !report.is_object() {
            *report = json!({});
        }
        for (key, value) in value.as_object().unwrap() {
            report[key] = value.clone();
        }
    }
    fn request(&self, method: reqwest::Method, path: &str) -> reqwest::blocking::RequestBuilder {
        self.client
            .request(
                method,
                format!("{}{}", self.config.receiver.trim_end_matches('/'), path),
            )
            .bearer_auth(&self.config.key)
    }
    fn retry(&self, raw: bool, mut operation: impl FnMut() -> Result<Value>) -> Result<Value> {
        let deadline = std::time::Instant::now() + Duration::from_secs(if raw { 180 } else { 10 });
        loop {
            match operation() {
                Ok(value) => {
                    let mut report = self.report.lock().unwrap();
                    if report["state"] == "waiting_for_pc" {
                        report["state"] = json!("ready");
                        report["message"] = json!("PC receiver reconnected; transfer acknowledged");
                    }
                    return Ok(value);
                }
                Err(e) => {
                    if e.downcast_ref::<Fatal>().is_some() {
                        return Err(e);
                    }
                    if std::time::Instant::now() >= deadline {
                        return Err(e).context("PC transfer stopped; any pending RAW is retained in Pi RAM. Restore the receiver and use Reconnect camera");
                    }
                    if let Some(http) = e.downcast_ref::<reqwest::Error>()
                        && http.status().is_some_and(|s| s.is_client_error())
                    {
                        return Err(e).context(
                            "Receiver refused the request; retained RAWs have not been discarded",
                        );
                    }
                    self.note(json!({"mode":"host-pc","state":"waiting_for_pc","message":format!("Waiting for PC receiver: {e}. Capture waits when the queue is full. Keep the Pi powered; pending RAWs stay in RAM.")}));
                    std::thread::sleep(Duration::from_secs(2));
                }
            }
        }
    }
    fn response(r: reqwest::blocking::Response) -> Result<Value> {
        let r = r.error_for_status()?;
        let value: Value = serde_json::from_reader(std::io::Read::take(r, 64 * 1024))?;
        ensure!(
            value["ok"] == true,
            "Receiver did not acknowledge the request"
        );
        Ok(value)
    }
    fn capacity(&self, run: Option<&str>, frames: usize, raw_bytes: u64) -> Result<()> {
        let path = run.map_or_else(|| "/api/status".into(), |r| format!("/api/runs/{r}"));
        let response = self
            .request(reqwest::Method::GET, &path)
            .timeout(Duration::from_secs(3))
            .send()?;
        let value = if let Some(run) = run
            && matches!(response.status().as_u16(), 404 | 405)
        {
            // Existing background receivers may outlive a UI upgrade. Their
            // idempotent registration reports the pinned folder. Free space is
            // usable only when that folder belongs to the current default root.
            let pinned = Self::response(
                self.request(reqwest::Method::POST, &path)
                    .timeout(Duration::from_secs(3))
                    .send()?,
            )?;
            let current = Self::response(
                self.request(reqwest::Method::GET, "/api/status")
                    .timeout(Duration::from_secs(3))
                    .send()?,
            )?;
            let root = current["folder"]
                .as_str()
                .context("Receiver did not report its folder")?
                .replace('\\', "/");
            let folder = pinned["folder"]
                .as_str()
                .context("Receiver did not report the pinned folder")?
                .replace('\\', "/");
            ensure!(
                folder == format!("{}/{}", root.trim_end_matches('/'), run),
                "Receiver was upgraded while open and its folder changed. Restart the PC receiver before continuing this stack"
            );
            current
        } else {
            Self::response(response)?
        };
        self.note(json!({"free_bytes":value["free_bytes"],"folder":value["folder"]}));
        crate::capacity::check(value["free_bytes"].as_u64(), frames, raw_bytes)?;
        Ok(())
    }
    fn refresh_capacity(&self) {
        let result = self
            .request(reqwest::Method::GET, "/api/status")
            .timeout(Duration::from_secs(1))
            .send()
            .map_err(anyhow::Error::from)
            .and_then(Self::response);
        match result {
            Ok(v) => self.note(json!({"free_bytes":v["free_bytes"],"folder":v["folder"]})),
            Err(_) => self.note(json!({"free_bytes":null})),
        }
    }
    pub fn ready(&self) -> Result<()> {
        let value = self.retry(false, || {
            let value = Self::response(self.request(reqwest::Method::GET, "/api/status").send()?)?;
            ensure!(value["protocol"] == 1, "Incompatible receiver protocol");
            ensure!(
                value["free_bytes"]
                    .as_u64()
                    .is_some_and(|n| n > MAX_RAW + 512 * 1024 * 1024),
                "PC capture disk has insufficient free space"
            );
            Ok(value)
        })?;
        let compression = self.config.transport_compression
            && value["raw_encodings"]
                .as_array()
                .is_some_and(|values| values.iter().any(|v| v == transport::ENCODING));
        self.compression.store(compression, Ordering::Relaxed);
        self.journal_append
            .store(value["journal_append"] == 1, Ordering::Relaxed);
        self.note(json!({"mode":"host-pc","state":"ready","folder":value["folder"],"free_bytes":value["free_bytes"],"message":"Lossless RAW L → PC · images buffered in RAM only"}));
        Ok(())
    }
    /// Transfer an existing file through the normal negotiated HTTP path without
    /// deleting its source. Diagnostics use this; camera queue ownership is separate.
    pub fn send_file(&self, run: &str, name: &str, path: &Path) -> Result<Value> {
        self.ready()?;
        self.register(run)?;
        self.put(run, name, path)
    }
    fn register(&self, run: &str) -> Result<()> {
        ensure!(crate::receiver::safe_run(run), "Invalid run name");
        self.retry(false, || {
            Self::response(
                self.request(reqwest::Method::POST, &format!("/api/runs/{run}"))
                    .send()?,
            )
        })?;
        Ok(())
    }
    fn put(&self, run: &str, name: &str, path: &Path) -> Result<Value> {
        let length = std::fs::metadata(path)?.len();
        ensure!(length <= MAX_RAW, "File exceeds transfer bound");
        self.put_bytes(run, name, std::fs::read(path)?, None)
    }
    fn put_bytes(
        &self,
        run: &str,
        name: &str,
        bytes: Vec<u8>,
        expected: Option<&str>,
    ) -> Result<Value> {
        ensure!(
            crate::receiver::safe_run(run) && crate::receiver::safe_name(name),
            "Invalid destination name"
        );
        let length = bytes.len() as u64;
        ensure!(length <= MAX_RAW, "File exceeds transfer bound");
        // A RAW was hashed when it reached the Pi. That hash is the one sent:
        // the receiver hashes what it receives and refuses a mismatch, so a
        // RAM copy that changed is still caught, without a second pass here
        // (MEASURED 2026-11-20: 0.4 s of each RAW's 1.36 s to the PC).
        let sum: String = match expected {
            Some(sum) => sum.to_owned(),
            None => Sha256::digest(&bytes)
                .iter()
                .map(|b| format!("{b:02x}"))
                .collect(),
        };
        // The immutable original body is shared with a bounded four-job encoder.
        // Each retry restarts the stream; no complete compressed copy is retained.
        let bytes = bytes::Bytes::from(bytes);
        let mut attempted = false;
        let mut encoding_refused = false;
        let mut receipt = self.retry(name.ends_with(".ARW"), || {
            if attempted && !encoding_refused && name.ends_with(".ARW") {
                // An early HTTP refusal can close a streaming body before the
                // client receives its status. Recheck capabilities on reconnect
                // rather than assuming the old receiver is still installed.
                let status =
                    Self::response(self.request(reqwest::Method::GET, "/api/status").send()?)?;
                ensure!(status["protocol"] == 1, "Incompatible receiver protocol");
                self.compression.store(
                    self.config.transport_compression
                        && status["raw_encodings"]
                            .as_array()
                            .is_some_and(|values| values.iter().any(|v| v == transport::ENCODING)),
                    Ordering::Relaxed,
                );
            }
            attempted = true;
            let started = Instant::now();
            let compressed = name.ends_with(".ARW") && self.compression.load(Ordering::Relaxed);
            let mut request = self
                .request(reqwest::Method::PUT, &format!("/api/files/{run}/{name}"))
                .header("x-content-sha256", &sum);
            request = if compressed {
                request
                    .header(transport::ENCODING_HEADER, transport::ENCODING)
                    .header(transport::LENGTH_HEADER, length)
                    .body(reqwest::blocking::Body::new(transport::Encoder::new(
                        bytes.clone(),
                        self.encoders.clone(),
                    )?))
            } else {
                request
                    .header(reqwest::header::CONTENT_LENGTH, length)
                    .body(bytes.clone())
            };
            let r = request.send()?;
            if r.status() == reqwest::StatusCode::UNPROCESSABLE_ENTITY {
                // The receiver's hash of what arrived differs from the one sent.
                // Only now is the RAM copy hashed again: changed, it is kept
                // for inspection and never sent; unchanged, the transfer was
                // damaged and is sent again.
                let local: String = Sha256::digest(bytes.as_ref())
                    .iter()
                    .map(|b| format!("{b:02x}"))
                    .collect();
                if local != sum {
                    return Err(Fatal("Buffered RAW changed; retained for inspection").into());
                }
                anyhow::bail!("Transfer damaged on the way to the PC; sending again");
            }
            // A receiver explicitly refusing a once-advertised encoding can have
            // been rolled back during this run. Retrying original bytes is safe;
            // it retries delivery, never the shutter.
            if compressed && r.status() == reqwest::StatusCode::UNSUPPORTED_MEDIA_TYPE {
                encoding_refused = true;
                self.compression.store(false, Ordering::Relaxed);
                anyhow::bail!("Receiver no longer accepts compression; retrying original bytes");
            }
            let mut receipt = Self::response(r)?;
            ensure!(
                receipt["durable"] == true
                    && receipt["bytes"].as_u64() == Some(length)
                    && receipt["sha256"].as_str() == Some(&sum),
                "PC acknowledgement failed length/checksum/durability checks"
            );
            if compressed {
                ensure!(
                    receipt["encoding"] == transport::ENCODING
                        && receipt["wire_bytes"]
                            .as_u64()
                            .is_some_and(|n| n > 0 && n <= transport::MAX_WIRE),
                    "PC acknowledgement omitted compressed transfer validation"
                );
            } else {
                receipt["encoding"] = json!("identity");
                receipt["wire_bytes"] = json!(length);
            }
            receipt["upload_seconds"] = json!(started.elapsed().as_secs_f64());
            Ok(receipt)
        })?;
        receipt["upload_MB_per_second"] =
            json!(length as f64 / receipt["upload_seconds"].as_f64().unwrap().max(0.000001) / 1e6);
        receipt["wire_MB_per_second"] = json!(
            receipt["wire_bytes"].as_u64().unwrap() as f64
                / receipt["upload_seconds"].as_f64().unwrap().max(0.000001)
                / 1e6
        );
        receipt["transfer_saved_percent"] = json!(
            (100.0 * (1.0 - receipt["wire_bytes"].as_u64().unwrap() as f64 / length.max(1) as f64))
                .max(0.0)
        );
        Ok(receipt)
    }
    /// Sends the part of a run's journal the receiver does not have yet.
    /// `Ok(false)` when the receiver cannot take an append (an older
    /// receiver, or its copy differs): the caller sends the whole file.
    fn append_journal(&self, run: &str, bytes: &[u8], offset: usize) -> Result<bool> {
        ensure!(offset <= bytes.len(), "Journal shrank");
        if !self.journal_append.load(Ordering::Relaxed) || offset == 0 {
            return Ok(false);
        }
        let body = bytes[offset..].to_vec();
        if body.is_empty() {
            return Ok(true);
        }
        let sum: String = Sha256::digest(&body)
            .iter()
            .map(|b| format!("{b:02x}"))
            .collect();
        let response = self
            .request(
                reqwest::Method::PUT,
                &format!("/api/files/{run}/events.jsonl"),
            )
            .header("x-content-sha256", &sum)
            .header(APPEND_HEADER, offset)
            .header(reqwest::header::CONTENT_LENGTH, body.len())
            .body(body)
            .send();
        match response
            .map_err(anyhow::Error::from)
            .and_then(Self::response)
        {
            Ok(receipt) => Ok(receipt["appended"] == true),
            Err(_) => Ok(false),
        }
    }
    fn raw_path(&self, path: &Path) -> Result<PathBuf> {
        let root = self.config.ram_directory.canonicalize()?;
        let path = path.canonicalize()?;
        ensure!(
            path.parent() == Some(root.as_path())
                && path
                    .extension()
                    .is_some_and(|s| s.eq_ignore_ascii_case("ARW")),
            "RAW escaped its RAM buffer"
        );
        Ok(path)
    }
    fn finish_pending(&self) -> Result<Option<Value>> {
        let pending = self.config.state_directory.join("pending-transfer.json");
        if !pending.exists() {
            return Ok(None);
        }
        self.deliver_pending(&pending).map(Some)
    }
    fn deliver_pending(&self, pending: &Path) -> Result<Value> {
        let data: Value = serde_json::from_slice(&std::fs::read(pending)?)?;
        let run = data["run"].as_str().context("Missing pending run")?;
        let name = data["name"].as_str().context("Missing pending filename")?;
        ensure!(
            crate::receiver::safe_run(run) && crate::receiver::safe_name(name),
            "Invalid pending destination"
        );
        let saved = self
            .config
            .state_directory
            .join("receipts")
            .join(run)
            .join(format!("{name}.json"));
        // A crash after unlinking RAM but before removing the intent is resolved
        // from the receipt that was flushed before either deletion.
        let raw = Path::new(data["path"].as_str().context("Missing pending RAM file")?);
        if !raw.exists() {
            let legacy = self.config.state_directory.join("last-transfer.json");
            for record in [&saved, &legacy] {
                if record.exists() {
                    let ack: Value = serde_json::from_slice(&std::fs::read(record)?)?;
                    if ack["pending"] == data
                        && ack["receipt"]["durable"] == true
                        && ack["receipt"]["sha256"] == data["sha256"]
                    {
                        std::fs::remove_file(pending)?;
                        return Ok(ack["receipt"].clone());
                    }
                }
            }
        }
        let path=self.raw_path(Path::new(data["path"].as_str().context("Missing pending RAM file")?)).context("Pending exposure is not in RAM. If the Pi lost power, inspect the PC receiver before acknowledging this exposure")?;
        ensure!(
            std::fs::metadata(&path)?.len()
                == data["bytes"].as_u64().context("Missing RAW size")?
                && std::fs::metadata(&path)?.len() <= MAX_RAW,
            "Pending RAW size changed"
        );
        self.register(run)?;
        self.note(json!({"mode":"host-pc","state":"transferring","message":format!("Saving {name} on the PC"),"bytes":data["bytes"]}));
        let receipt = self.put_bytes(
            run,
            name,
            std::fs::read(&path)?,
            Some(
                data["sha256"]
                    .as_str()
                    .context("Missing pending checksum")?,
            ),
        )?;
        // Record the durable PC receipt before removing the only RAM copy.
        save_json(&saved, &json!({"pending":data,"receipt":receipt}))?;
        std::fs::remove_file(path)?;
        std::fs::remove_file(pending)?;
        self.note(json!({"mode":"host-pc","state":"saved","message":"RAW verified and saved on PC","receipt":receipt,"upload_MB_per_second":receipt["upload_MB_per_second"]}));
        Ok(receipt)
    }
}
/// RAWs the Pi may hold for the PC. Admission also needs RAM and tmpfs room
/// for a whole group, so a 1 GiB tmpfs still admits one group at a time; the
/// studio Pi's 2 GiB lets the next group's shutter go while one uploads.
const MAX_PENDING_FRAMES: usize = 8;
/// Uploads at once. MEASURED (2026-11-20, studio Wi-Fi): 58 MB/s on one TCP
/// stream, 69 MB/s on two or four.
const UPLOAD_WORKERS: usize = 2;
const MAX_METADATA: u64 = 64 * 1024 * 1024;

fn memory_room(reservation: u64) -> Result<bool> {
    #[cfg(target_os = "linux")]
    {
        let info = std::fs::read_to_string("/proc/meminfo")?;
        let available: u64 = info
            .lines()
            .find_map(|line| line.strip_prefix("MemAvailable:"))
            .and_then(|s| s.split_whitespace().next())
            .context("Missing available memory")?
            .parse()?;
        // Reserve a new SDK file, its possible uploader byte body, bounded codec
        // workers and 64 MiB headroom, in addition to the tmpfs capacity gate.
        Ok(available.saturating_mul(1024)
            >= reservation + MAX_RAW + transport::WORKSPACE_BYTES + 64 * 1024 * 1024)
    }
    #[cfg(not(target_os = "linux"))]
    {
        let _ = reservation;
        Ok(true)
    }
}

#[derive(Clone)]
struct Job {
    intent: PathBuf,
    raw: PathBuf,
    bytes: u64,
    /// An upload worker has it.
    claimed: bool,
}
#[derive(Clone)]
struct Metadata {
    revision: u64,
    run: String,
    files: Vec<(String, Arc<Vec<u8>>)>,
}
#[derive(Default)]
struct QueueState {
    jobs: VecDeque<Job>,
    metadata: Option<Metadata>,
    metadata_revision: u64,
    metadata_done: u64,
    /// A worker is sending a metadata snapshot (one at a time, in order).
    metadata_busy: bool,
    /// A RAW was saved since the last metadata snapshot was taken.
    raw_since_metadata: bool,
    /// How much of each run's journal the receiver has.
    journal_sent: Option<(String, usize)>,
    closed: bool,
    error: Option<String>,
    captured: usize,
    saved: usize,
    peak: usize,
}
type SharedQueue = Arc<(Mutex<QueueState>, Condvar)>;
struct UploadQueue {
    shared: SharedQueue,
    sink: Sink,
    threads: Vec<JoinHandle<()>>,
}
fn progress(sink: &Sink, state: &QueueState) {
    sink.note(json!({"pipelined":true,"captured_frames":state.captured,"saved_frames":state.saved,
        "pending_frames":state.jobs.len(),"pending_bytes":state.jobs.iter().map(|j|j.bytes).sum::<u64>(),
        "queue_capacity":MAX_PENDING_FRAMES,"queue_peak":state.peak}));
}
impl UploadQueue {
    fn new(sink: Sink) -> Result<Self> {
        let shared = Arc::new((Mutex::new(QueueState::default()), Condvar::new()));
        progress(&sink, &shared.0.lock().unwrap());
        let mut threads = Vec::new();
        for i in 0..UPLOAD_WORKERS {
            let worker = shared.clone();
            let worker_sink = sink.clone();
            threads.push(
                thread::Builder::new()
                    .name(format!("raw-upload-{i}"))
                    .spawn(move || {
                        let result = std::panic::catch_unwind(std::panic::AssertUnwindSafe(|| {
                            Self::run(&worker_sink, &worker)
                        }));
                        let failure = match result {
                            Ok(Ok(())) => None,
                            Ok(Err(e)) => Some(format!("{e:#}")),
                            Err(_) => {
                                Some("Transfer worker failed; pending RAWs retained in RAM".into())
                            }
                        };
                        if let Some(error) = failure {
                            let mut state = worker.0.lock().unwrap();
                            state.error.get_or_insert(error.clone());
                            drop(state);
                            worker_sink.note(json!({"state":"transfer_failed","message":error}));
                        }
                        worker.1.notify_all();
                    })?,
            );
        }
        Ok(Self {
            shared,
            sink,
            threads,
        })
    }
    /// One upload worker. RAWs go in capture order but up to
    /// `UPLOAD_WORKERS` at once; a journal snapshot goes after a RAW (or
    /// when there is none), one snapshot at a time and only as an append
    /// after the first.
    fn run(sink: &Sink, shared: &SharedQueue) -> Result<()> {
        enum Task {
            Raw(Job),
            Metadata(Metadata, usize),
        }
        loop {
            let task = {
                let mut state = shared.0.lock().unwrap();
                loop {
                    if state.error.is_some() {
                        return Ok(());
                    }
                    let unclaimed = state.jobs.iter().position(|j| !j.claimed);
                    let pending_metadata =
                        state.metadata_revision > state.metadata_done && !state.metadata_busy;
                    if pending_metadata && (state.raw_since_metadata || unclaimed.is_none()) {
                        let snapshot =
                            state.metadata.clone().context("Missing journal snapshot")?;
                        let sent = match &state.journal_sent {
                            Some((run, sent)) if *run == snapshot.run => *sent,
                            _ => 0,
                        };
                        state.metadata_busy = true;
                        state.raw_since_metadata = false;
                        break Task::Metadata(snapshot, sent);
                    }
                    if let Some(i) = unclaimed {
                        state.jobs[i].claimed = true;
                        break Task::Raw(state.jobs[i].clone());
                    }
                    if state.closed && state.jobs.is_empty() && !state.metadata_busy {
                        return Ok(());
                    }
                    state = shared.1.wait(state).unwrap();
                }
            };
            match task {
                Task::Raw(job) => {
                    sink.deliver_pending(&job.intent)?;
                    let mut state = shared.0.lock().unwrap();
                    let i = state
                        .jobs
                        .iter()
                        .position(|j| j.intent == job.intent && j.claimed)
                        .context("Upload queue lost a claimed RAW")?;
                    state.jobs.remove(i);
                    state.saved += 1;
                    state.raw_since_metadata = true;
                    progress(sink, &state);
                }
                Task::Metadata(snapshot, sent) => {
                    let mut journal = None;
                    for (name, bytes) in &snapshot.files {
                        if name == "events.jsonl" {
                            if !sink.append_journal(&snapshot.run, bytes, sent)? {
                                sink.put_bytes(&snapshot.run, name, bytes.as_ref().clone(), None)?;
                            }
                            journal = Some(bytes.len());
                        } else {
                            sink.put_bytes(&snapshot.run, name, bytes.as_ref().clone(), None)?;
                        }
                    }
                    let mut state = shared.0.lock().unwrap();
                    state.metadata_done = snapshot.revision;
                    state.metadata_busy = false;
                    if let Some(length) = journal {
                        state.journal_sent = Some((snapshot.run.clone(), length));
                    }
                }
            }
            shared.1.notify_all();
        }
    }
    fn check(state: &QueueState) -> Result<()> {
        ensure!(
            state.error.is_none(),
            "{}",
            state.error.as_deref().unwrap_or_default()
        );
        Ok(())
    }
    fn reset(&self) -> Result<()> {
        self.finish()?;
        let mut state = self.shared.0.lock().unwrap();
        ensure!(!state.closed, "Transfer queue is closed");
        let journal_sent = state.journal_sent.take();
        *state = QueueState::default();
        state.journal_sent = journal_sent;
        self.sink
            .note(json!({"receipt":null,"upload_MB_per_second":null}));
        progress(&self.sink, &state);
        Ok(())
    }
    fn room(&self) -> Result<bool> {
        self.room_for(1, MAX_RAW)
    }
    fn room_for(&self, members: usize, reservation: u64) -> Result<bool> {
        let state = self.shared.0.lock().unwrap();
        Self::check(&state)?;
        let root = self.sink.config.ram_directory.canonicalize()?;
        for entry in std::fs::read_dir(root)? {
            let path = entry?.path();
            ensure!(
                state.jobs.iter().any(|job| job.raw == path),
                "Unbound file appeared in the RAM buffer; no new exposure. Preserve it before reconnecting."
            );
        }
        ensure!(
            (1..=MAX_PENDING_FRAMES).contains(&members),
            "Invalid group reservation"
        );
        let enough = state.jobs.len() + members <= MAX_PENDING_FRAMES
            && fs2::available_space(&self.sink.config.ram_directory)?
                >= reservation + 4 * 1024 * 1024
            && memory_room(reservation)?;
        let waiting = self.sink.report.lock().unwrap()["state"] == "waiting_for_pc";
        if !enough && !waiting {
            self.sink.note(json!({"state":"buffer_full","message":"Waiting for PC delivery to free RAM; no new exposure"}));
        }
        Ok(enough && !waiting)
    }
    fn enqueue(&self, data: Value) -> Result<()> {
        let run = data["run"].as_str().context("Missing queued run")?;
        let name = data["name"].as_str().context("Missing queued name")?;
        ensure!(
            crate::receiver::safe_run(run) && crate::receiver::safe_name(name),
            "Invalid queued filename"
        );
        let intent = self
            .sink
            .config
            .state_directory
            .join("pending-transfers")
            .join(format!("{run}-{name}.json"));
        ensure!(
            !intent.exists(),
            "Pending transfer already exists; no overwrite"
        );
        let bytes = data["bytes"]
            .as_u64()
            .context("Missing queued byte count")?;
        let raw = self.sink.raw_path(Path::new(
            data["path"].as_str().context("Missing queued RAW path")?,
        ))?;
        // Persist the binding before allowing another shutter, including if the
        // uploader encountered an error while this exposure was finishing.
        save_json(&intent, &data)?;
        let mut state = self.shared.0.lock().unwrap();
        ensure!(
            !state.closed && state.jobs.len() < MAX_PENDING_FRAMES,
            "RAW retained; upload queue cannot accept another frame"
        );
        state.jobs.push_back(Job {
            intent,
            raw,
            bytes,
            claimed: false,
        });
        state.captured += 1;
        state.peak = state.peak.max(state.jobs.len());
        progress(&self.sink, &state);
        self.shared.1.notify_all();
        Ok(())
    }
    fn snapshot(&self, directory: &Path, run: &str) -> Result<()> {
        let mut files = Vec::new();
        for name in ["events.jsonl", "result.json"] {
            let path = directory.join(name);
            if path.exists() {
                ensure!(
                    std::fs::metadata(&path)?.len() <= MAX_METADATA,
                    "Capture journal exceeded its RAM snapshot bound"
                );
                files.push((name.to_owned(), Arc::new(std::fs::read(path)?)));
            }
        }
        let mut state = self.shared.0.lock().unwrap();
        state.metadata_revision += 1;
        state.metadata = Some(Metadata {
            revision: state.metadata_revision,
            run: run.to_owned(),
            files,
        });
        self.shared.1.notify_all();
        Ok(())
    }
    fn finish(&self) -> Result<()> {
        let mut state = self.shared.0.lock().unwrap();
        loop {
            Self::check(&state)?;
            if state.jobs.is_empty()
                && state.metadata_done == state.metadata_revision
                && !state.metadata_busy
            {
                return Ok(());
            }
            state = self.shared.1.wait(state).unwrap();
        }
    }
    fn close(&mut self) {
        self.shared.0.lock().unwrap().closed = true;
        self.shared.1.notify_all();
        for thread in self.threads.drain(..) {
            let _ = thread.join();
        }
    }
}
impl Drop for UploadQueue {
    fn drop(&mut self) {
        self.close();
    }
}

/// Sends the journal of the run that was capturing when the controller last
/// stopped, so the PC has its final state.
fn recover_journal(sink: &Sink, state: &Path) -> Result<()> {
    let active = state.join("active-journal.json");
    if active.exists() {
        let record: Value = serde_json::from_slice(&std::fs::read(&active)?)?;
        let directory = Path::new(
            record["directory"]
                .as_str()
                .context("Missing recovery journal")?,
        );
        let run = directory
            .file_name()
            .and_then(|s| s.to_str())
            .context("Invalid recovery journal")?;
        match sink.register(run) {
            Ok(()) => {
                for name in ["manifest.json", "events.jsonl", "result.json"] {
                    let path = directory.join(name);
                    if path.exists() {
                        sink.put(run, name, &path)?;
                    }
                }
            }
            // The run finished on the Pi and every RAW was acknowledged
            // (none is pending above), but the PC no longer has its
            // folder: the owner deleted the stack there. Nothing of it is
            // left to deliver; refusing to connect would only strand the
            // camera.
            Err(e) if directory.join("result.json").is_file() && refused_missing(&e) => {
                std::fs::remove_file(&active)?;
            }
            Err(e) => return Err(e),
        }
    }
    Ok(())
}

/// The receiver refused to register a run because its folder is gone
/// (HTTP 409 from `POST /api/runs/{run}`).
fn refused_missing(e: &anyhow::Error) -> bool {
    e.chain().any(|c| {
        c.downcast_ref::<reqwest::Error>()
            .and_then(reqwest::Error::status)
            == Some(reqwest::StatusCode::CONFLICT)
    })
}

pub struct PcCamera {
    inner: Native,
    sink: Sink,
    uploads: UploadQueue,
    run: Option<String>,
    ordinal: usize,
    /// Planes captured in this run, and whether the next capture repeats
    /// the last one (a retake).
    planes: usize,
    repeat: bool,
    /// The next capture retakes this earlier plane.
    retake: Option<usize>,
    planned_frames: usize,
    raw_limit: u64,
    capacity_at: Instant,
    /// When the PC last confirmed room for the rest of the run.
    run_capacity_at: Option<Instant>,
}
impl PcCamera {
    pub fn connect(bridge: &Path, config: TransferConfig, report: TransferReport) -> Result<Self> {
        std::fs::create_dir_all(&config.ram_directory)?;
        std::fs::create_dir_all(&config.state_directory)?;
        let sink = Sink::new(config.clone(), report)?;
        sink.finish_pending()?;
        let pending = config.state_directory.join("pending-transfers");
        if pending.exists() {
            let mut entries = std::fs::read_dir(pending)?
                .map(|e| e.map(|e| e.path()))
                .collect::<std::io::Result<Vec<_>>>()?;
            entries.sort();
            for entry in entries {
                ensure!(
                    entry.extension().is_some_and(|s| s == "json"),
                    "Unrecognized pending transfer retained"
                );
                sink.deliver_pending(&entry)?;
            }
        }
        recover_journal(&sink, &config.state_directory)?;
        ensure!(
            std::fs::read_dir(&config.ram_directory)?.next().is_none(),
            "Unbound RAW remains in RAM from an interrupted camera download. Preserve it before reconnecting; no new exposure was taken"
        );
        let inner = Native::connect_host(bridge, &config.ram_directory)?;
        let uploads = UploadQueue::new(sink.clone())?;
        Ok(Self {
            inner,
            sink,
            uploads,
            run: None,
            ordinal: 0,
            planes: 0,
            repeat: false,
            retake: None,
            planned_frames: 0,
            raw_limit: MAX_RAW,
            capacity_at: Instant::now(),
            run_capacity_at: None,
        })
    }
}
impl Camera for PcCamera {
    fn identity(&self) -> Value {
        let mut v = self.inner.identity();
        v["raw_destination"] = json!("host-pc");
        v["raw_format"] = json!(self.inner.raw_format());
        v["upload_queue_capacity"] = json!(MAX_PENDING_FRAMES);
        v
    }
    fn status(&mut self) -> Result<Value> {
        let mut v = self.inner.status()?;
        v["capture_destination"] = json!("host-pc");
        if self.capacity_at.elapsed() >= Duration::from_secs(2) {
            self.sink.refresh_capacity();
            self.capacity_at = Instant::now();
        }
        Ok(v)
    }
    fn configure(&mut self) -> Result<()> {
        self.inner.configure()
    }
    fn focus(&mut self, target: u16, settle_ms: u32) -> Result<Value> {
        self.inner.focus(target, settle_ms)
    }
    fn set_pixel_shift(&mut self, shots: usize) -> Result<()> {
        self.uploads.finish()?;
        self.inner.set_pixel_shift(shots)
    }
    fn set_exposure(&mut self, iso: u64, shutter: u64) -> Result<()> {
        self.uploads.finish()?;
        self.inner.set_exposure(iso, shutter)
    }
    fn prepare_stack(&mut self, frames: usize, raw_bytes: u64) -> Result<()> {
        self.uploads.finish()?;
        self.sink.capacity(None, frames, raw_bytes)?;
        self.planned_frames = frames;
        self.raw_limit = raw_bytes;
        Ok(())
    }
    fn prepare_capture(&mut self) -> Result<bool> {
        let shots = self.inner.shots_per_plane();
        let room = if self.inner.group_stream() {
            self.uploads
                .room_for(shots, shots as u64 * crate::ptp::MEMBER_LIMIT)?
        } else {
            self.uploads.room()?
        };
        if !room {
            return Ok(false);
        }
        let pending = self.sink.report.lock().unwrap()["pending_frames"]
            .as_u64()
            .unwrap_or(0) as usize;
        let remaining = self.planned_frames.saturating_sub(self.ordinal) + pending;
        // Room for the whole rest of the run was confirmed at most 5 s ago:
        // the run has only used some of it since. Asking on every plane cost
        // a round trip over the busy uplink before every shutter.
        if self
            .run_capacity_at
            .is_none_or(|at| at.elapsed() >= Duration::from_secs(5))
        {
            self.sink
                .capacity(self.run.as_deref(), remaining.max(shots), self.raw_limit)?;
            self.run_capacity_at = Some(Instant::now());
        }
        Ok(true)
    }
    fn finish_transfers(&mut self) -> Result<()> {
        self.uploads.finish()
    }
    fn capture(&mut self, timeout_s: u32) -> Result<Value> {
        let run = self.run.clone().context("PC run is not registered")?;
        let started = Instant::now();
        let shots = self.inner.shots_per_plane();
        let format = self.inner.raw_format();
        let group_stream = self.inner.group_stream();
        // Planes are counted, not derived from the file count: a retake
        // (error correction) records more files for the same plane.
        let plane = match self
            .retake
            .take()
            .filter(|&p| (1..=self.planes).contains(&p))
        {
            Some(plane) => {
                self.repeat = false;
                plane
            }
            None => {
                if !std::mem::take(&mut self.repeat) || self.planes == 0 {
                    self.planes += 1;
                }
                self.planes
            }
        };
        let mut files = Vec::new();
        let sink = &self.sink;
        let uploads = &self.uploads;
        let ordinal = &mut self.ordinal;
        let response=self.inner.capture_files(timeout_s,&mut |response| {
            ensure!(response["destination"]=="host-ram" && response["raw_compression"]==format
                && response["completion"]==if group_stream {"ptp-object-complete"}else{"sdk-download-complete"},
                "Bridge did not complete the expected RAW");
            if group_stream {
                ensure!(response["members"]==shots && response["member_index"]==files.len()+1
                    && response["group_id"].as_str().is_some_and(|s|!s.is_empty()),"Invalid pixel-shift member ordering");
                if let Some(first)=files.first() {
                    let first:&Value=first;
                    ensure!(first["group_id"]==response["group_id"],"Mixed pixel-shift groups");
                }
            }
            let path=sink.raw_path(Path::new(response["path"].as_str().context("Missing downloaded RAW path")?))?;
            let bytes=std::fs::metadata(&path)?.len();
            ensure!(response["bytes"].as_u64()==Some(bytes) && (1024..=MAX_RAW).contains(&bytes),"RAW length does not match completion; file retained");
            let name=format!("frame-{:06}.ARW",*ordinal+1);
            let sum=hash_file(&path)?;
            let file=json!({"name":name,"path":path,"bytes":bytes,"sha256":sum,"durable":false,
                "plane":plane,"group_id":response["group_id"],"member_index":if group_stream {response["member_index"].clone()}else{json!(1)},"members":shots});
            let pending=json!({"run":run,"name":name,"path":path,"bytes":bytes,"sha256":sum,
                "plane":plane,"group_id":response["group_id"],"member_index":file["member_index"],"members":shots,"camera_reply":response});
            uploads.enqueue(pending)?;
            *ordinal+=1;
            files.push(file);
            Ok(())
        })?;
        ensure!(
            files.len() == shots,
            "Missing group member; no focus move or shutter retry"
        );
        Ok(
            json!({"destination":"host-pc-queue","completion":"ram-queued-sha256","file_verification":"ram-sha256",
            "raw_compression":format,"pixel_shift_shots":shots,"group_complete":shots==1 || response["group_idle"]==true,
            "files":files,"camera_reply":response,"camera_seconds":started.elapsed().as_secs_f64()}),
        )
    }
    fn preview(&mut self) -> Result<Preview> {
        self.inner.preview()
    }
    fn magnify(&mut self, r: u32, x: u16, y: u16) -> Result<()> {
        self.inner.magnify(r, x, y)
    }
    fn disconnect(&mut self) -> Result<Value> {
        let transfer = self.uploads.finish();
        self.uploads.close();
        let mut result = self.inner.disconnect()?;
        if let Err(error) = transfer {
            result["transfer_warning"] = json!(format!("{error:#}"));
        }
        Ok(result)
    }
    fn standby(&mut self) -> Result<()> {
        self.uploads.finish()?;
        ensure!(
            std::fs::read_dir(&self.sink.config.ram_directory)?
                .next()
                .is_none(),
            "RAWs are still in Pi memory; camera supply left on"
        );
        self.inner.standby()?;
        self.uploads.close();
        Ok(())
    }
    fn sync_journal(&mut self, directory: &Path) -> Result<()> {
        let run = directory
            .file_name()
            .and_then(|v| v.to_str())
            .context("Invalid journal directory")?;
        if self.run.as_deref() != Some(run) {
            self.uploads.reset()?;
            self.sink.ready()?;
            self.sink.register(run)?;
            self.sink
                .put(run, "manifest.json", &directory.join("manifest.json"))?;
            save_json(
                &self.sink.config.state_directory.join("active-journal.json"),
                &json!({"directory":directory}),
            )?;
            self.run = Some(run.into());
            self.run_capacity_at = None;
            self.ordinal = 0;
            self.planes = 0;
            self.repeat = false;
            self.retake = None;
        }
        self.uploads.snapshot(directory, run)
    }
    fn verdict(&mut self, group: &str) -> Result<Option<Value>> {
        let run = self.run.clone().context("PC run is not registered")?;
        let value = Sink::response(
            self.sink
                .request(
                    reqwest::Method::GET,
                    &format!("/api/runs/{run}/verdicts/{group}"),
                )
                .timeout(Duration::from_secs(2))
                .send()?,
        )?;
        Ok((value["state"] == "checked").then_some(value))
    }
    fn repeat_plane(&mut self) {
        self.repeat = true;
    }
    fn retake_plane(&mut self, plane: Option<u64>) {
        match plane {
            Some(p) => self.retake = usize::try_from(p).ok(),
            None => self.repeat = true,
        }
    }
    fn set_next_focus(&mut self, next: Option<(u16, u32)>) {
        self.inner.set_next_focus(next);
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::receiver::{Receiver, ReceiverConfig};
    use axum::response::IntoResponse;
    use std::net::{SocketAddr, TcpListener};

    #[test]
    fn queue_overlaps_upload_bounds_memory_and_drains_latest_metadata() {
        use axum::{
            body::Body,
            http::Request,
            middleware::{self, Next},
        };
        use std::sync::{
            atomic::{AtomicBool, Ordering},
            mpsc,
        };
        let temp = tempfile::tempdir().unwrap();
        let config = temp.path().join("receiver.json");
        let pc = temp.path().join("pc");
        save_json(
            &config,
            &ReceiverConfig {
                compress_raw: false,
                bind: "127.0.0.1:0".parse().unwrap(),
                lan: "10.0.0.0/24".into(),
                key: "a".repeat(48),
                folder: pc.clone(),
            },
        )
        .unwrap();
        let receiver = Receiver::open(config).unwrap();
        let listener = TcpListener::bind("127.0.0.1:0").unwrap();
        let address = listener.local_addr().unwrap();
        listener.set_nonblocking(true).unwrap();
        let gate = Arc::new(tokio::sync::Semaphore::new(0));
        let server_gate = gate.clone();
        let first = Arc::new(AtomicBool::new(true));
        let (entered, uploading) = mpsc::channel();
        let router = receiver.router().layer(middleware::from_fn(
            move |request: Request<Body>, next: Next| {
                let gate = server_gate.clone();
                let first = first.clone();
                let entered = entered.clone();
                async move {
                    if !request.uri().path().ends_with(".ARW") {
                        return next.run(request).await;
                    }
                    let _ = entered.send(());
                    // Every RAW waits for the gate. The bound also makes a
                    // failing test release its owned server.
                    let _ = tokio::time::timeout(Duration::from_secs(10), gate.acquire()).await;
                    if request.uri().path().ends_with("frame-000001.ARW")
                        && first.swap(false, Ordering::SeqCst)
                    {
                        let committed = next.run(request).await;
                        assert!(committed.status().is_success());
                        // Lose the first acknowledgement after the file is durable.
                        // The sender must retry the entire compressed stream and
                        // receive an idempotent acknowledgement before removing RAM.
                        return axum::http::StatusCode::SERVICE_UNAVAILABLE.into_response();
                    }
                    next.run(request).await
                }
            },
        ));
        let (shutdown, stopped) = tokio::sync::oneshot::channel();
        let server = thread::spawn(move || {
            tokio::runtime::Runtime::new().unwrap().block_on(async {
                axum::serve(
                    tokio::net::TcpListener::from_std(listener).unwrap(),
                    router.into_make_service_with_connect_info::<SocketAddr>(),
                )
                .with_graceful_shutdown(async {
                    let _ = stopped.await;
                })
                .await
                .unwrap();
            })
        });
        let ram = temp.path().join("ram");
        let state = temp.path().join("state");
        std::fs::create_dir(&ram).unwrap();
        std::fs::create_dir(&state).unwrap();
        let sink = Sink::new(
            TransferConfig {
                receiver: format!("http://{address}"),
                key: "a".repeat(48),
                lan: "10.0.0.0/24".into(),
                ram_directory: ram.clone(),
                state_directory: state.clone(),
                transport_compression: true,
            },
            Arc::new(Mutex::new(json!({}))),
        )
        .unwrap();
        let run = "stack-overlap-test";
        sink.ready().unwrap();
        sink.register(run).unwrap();
        let mut queue = UploadQueue::new(sink.clone()).unwrap();
        let mut bindings = Vec::new();
        for i in 0..MAX_PENDING_FRAMES {
            assert!(queue.room().unwrap());
            let raw = ram.join(format!("source-{i}.ARW"));
            std::fs::write(&raw, vec![i as u8; 65536]).unwrap();
            let binding = json!({"run":run,"name":format!("frame-{:06}.ARW",i+1),"path":raw,"bytes":65536,"sha256":hash_file(&raw).unwrap()});
            queue.enqueue(binding.clone()).unwrap();
            bindings.push(binding);
            if i == 1 {
                // Two real HTTP uploads are in flight at once.
                for _ in 0..UPLOAD_WORKERS {
                    uploading.recv_timeout(Duration::from_secs(5)).unwrap();
                }
            }
        }
        // Blocked uploads while complete RAWs fill the queue.
        assert!(!queue.room().unwrap());
        assert!(uploading.recv_timeout(Duration::from_millis(300)).is_err());
        assert_eq!(std::fs::read_dir(&ram).unwrap().count(), MAX_PENDING_FRAMES);
        assert_eq!(sink.report.lock().unwrap()["saved_frames"], 0);
        let journal = temp.path().join(run);
        std::fs::create_dir(&journal).unwrap();
        std::fs::write(journal.join("events.jsonl"), b"{\"one\":1}\n").unwrap();
        queue.snapshot(&journal, run).unwrap();
        let latest = b"{\"one\":1}\n{\"two\":2}\n";
        std::fs::write(journal.join("events.jsonl"), latest).unwrap();
        queue.snapshot(&journal, run).unwrap();
        gate.add_permits(1000);
        queue.finish().unwrap();
        assert_eq!(
            sink.report.lock().unwrap()["saved_frames"],
            MAX_PENDING_FRAMES
        );
        assert_eq!(sink.report.lock().unwrap()["pending_frames"], 0);
        assert_eq!(
            sink.report.lock().unwrap()["queue_peak"],
            MAX_PENDING_FRAMES
        );
        assert_eq!(std::fs::read_dir(&ram).unwrap().count(), 0);
        assert_eq!(
            std::fs::read(pc.join(run).join("events.jsonl")).unwrap(),
            latest
        );
        for binding in &bindings {
            assert_eq!(
                hash_file(&pc.join(run).join(binding["name"].as_str().unwrap())).unwrap(),
                binding["sha256"]
            );
        }
        let first_ack: Value = serde_json::from_slice(
            &std::fs::read(state.join("receipts/stack-overlap-test/frame-000001.ARW.json"))
                .unwrap(),
        )
        .unwrap();
        assert_eq!(first_ack["receipt"]["already_saved"], true);
        assert_eq!(first_ack["receipt"]["encoding"], transport::ENCODING);
        assert!(first_ack["receipt"]["wire_bytes"].as_u64().unwrap() < 65536);
        // An old intent survives RAM deletion, even after newer receipts exist.
        let intent = state.join("pending-transfers/recovered.json");
        save_json(&intent, &bindings[0]).unwrap();
        let receipt = sink.deliver_pending(&intent).unwrap();
        assert_eq!(receipt["sha256"], bindings[0]["sha256"]);
        assert!(!intent.exists());
        queue.close();
        // Corrupt data must stop the uploader and remain recoverable, never be
        // counted as saved or silently discarded to make room for another shot.
        let mut queue = UploadQueue::new(sink.clone()).unwrap();
        let raw = ram.join("corrupt.ARW");
        std::fs::write(&raw, vec![23u8; 65536]).unwrap();
        queue.enqueue(json!({"run":run,"name":"frame-000099.ARW","path":raw,"bytes":65536,"sha256":"0".repeat(64)})).unwrap();
        assert!(queue.finish().is_err());
        assert!(queue.room().is_err());
        assert!(raw.exists());
        assert!(!pc.join(run).join("frame-000099.ARW").exists());
        assert!(
            state
                .join("pending-transfers")
                .read_dir()
                .unwrap()
                .next()
                .is_some()
        );
        queue.close();
        shutdown.send(()).unwrap();
        server.join().unwrap();
    }

    /// The owner deleted a finished stack's folder on the PC: the controller
    /// still connects. An unfinished run's journal is still owed and refused.
    #[test]
    fn a_finished_run_deleted_on_the_pc_does_not_block_connecting() {
        let temp = tempfile::tempdir().unwrap();
        let config = temp.path().join("receiver.json");
        let pc = temp.path().join("pc");
        save_json(
            &config,
            &ReceiverConfig {
                compress_raw: false,
                bind: "127.0.0.1:0".parse().unwrap(),
                lan: "10.0.0.0/24".into(),
                key: "a".repeat(48),
                folder: pc.clone(),
            },
        )
        .unwrap();
        let receiver = Receiver::open(config).unwrap();
        let listener = TcpListener::bind("127.0.0.1:0").unwrap();
        let address = listener.local_addr().unwrap();
        listener.set_nonblocking(true).unwrap();
        let router = receiver.router();
        let (shutdown, stopped) = tokio::sync::oneshot::channel();
        let server = thread::spawn(move || {
            tokio::runtime::Runtime::new().unwrap().block_on(async {
                axum::serve(
                    tokio::net::TcpListener::from_std(listener).unwrap(),
                    router.into_make_service_with_connect_info::<SocketAddr>(),
                )
                .with_graceful_shutdown(async {
                    let _ = stopped.await;
                })
                .await
                .unwrap();
            })
        });
        let state = temp.path().join("state");
        std::fs::create_dir(&state).unwrap();
        let sink = Sink::new(
            TransferConfig {
                receiver: format!("http://{address}"),
                key: "a".repeat(48),
                lan: "10.0.0.0/24".into(),
                ram_directory: temp.path().join("ram"),
                state_directory: state.clone(),
                transport_compression: false,
            },
            Arc::new(Mutex::new(json!({}))),
        )
        .unwrap();
        let journal = temp.path().join("journal").join("stack-1-deleted");
        std::fs::create_dir_all(&journal).unwrap();
        std::fs::write(journal.join("manifest.json"), b"{}").unwrap();
        std::fs::write(
            journal.join("events.jsonl"),
            b"{\"a\":1}
",
        )
        .unwrap();
        let active = state.join("active-journal.json");
        save_json(&active, &json!({"directory":journal})).unwrap();
        // Registered and then deleted by the owner, before the run finished.
        sink.register("stack-1-deleted").unwrap();
        std::fs::remove_dir_all(pc.join("stack-1-deleted")).unwrap();
        assert!(recover_journal(&sink, &state).is_err());
        assert!(active.exists());
        // Finished on the Pi: nothing is owed, the record is dropped.
        std::fs::write(journal.join("result.json"), b"{}").unwrap();
        recover_journal(&sink, &state).unwrap();
        assert!(!active.exists());
        // A run the PC still has is re-sent as before.
        let kept = temp.path().join("journal").join("stack-1-kept");
        std::fs::create_dir_all(&kept).unwrap();
        std::fs::write(kept.join("manifest.json"), b"{}").unwrap();
        std::fs::write(kept.join("result.json"), b"{}").unwrap();
        save_json(&active, &json!({"directory":kept})).unwrap();
        recover_journal(&sink, &state).unwrap();
        assert_eq!(
            std::fs::read(pc.join("stack-1-kept").join("result.json")).unwrap(),
            b"{}"
        );
        shutdown.send(()).unwrap();
        server.join().unwrap();
    }

    #[test]
    fn actual_http_delivery_is_bound_and_removes_ram_only_after_ack() {
        use axum::{
            body::Body,
            http::Request,
            middleware::{self, Next},
        };
        use std::sync::atomic::AtomicUsize;
        let temp = tempfile::tempdir().unwrap();
        let receiver_config = temp.path().join("receiver.json");
        let pc = temp.path().join("pc");
        save_json(
            &receiver_config,
            &ReceiverConfig {
                compress_raw: false,
                bind: "127.0.0.1:0".parse().unwrap(),
                lan: "10.0.0.0/24".into(),
                key: "a".repeat(48),
                folder: pc.clone(),
            },
        )
        .unwrap();
        let receiver = Receiver::open(receiver_config).unwrap();
        let listener = TcpListener::bind("127.0.0.1:0").unwrap();
        let address = listener.local_addr().unwrap();
        listener.set_nonblocking(true).unwrap();
        let (shutdown, stopped) = tokio::sync::oneshot::channel::<()>();
        let version = Arc::new(AtomicUsize::new(0));
        let server_version = version.clone();
        let router = receiver.router().layer(middleware::from_fn(move |request: Request<Body>, next: Next| {
            let version = server_version.clone();
            async move {
                    if request.uri().path() == "/api/status" && matches!(version.load(Ordering::Relaxed), 0 | 3) {
                    return axum::Json(json!({"ok":true,"protocol":1,"free_bytes":8u64*1024*1024*1024,"folder":"legacy"})).into_response();
                }
                if request.method() == axum::http::Method::PUT
                    && request.headers().get(transport::ENCODING_HEADER).is_some()
                    && version.load(Ordering::Relaxed) == 2
                {
                    version.store(3, Ordering::Relaxed);
                    return axum::http::StatusCode::UNSUPPORTED_MEDIA_TYPE.into_response();
                }
                next.run(request).await
            }
        }));
        let server = std::thread::spawn(move || {
            tokio::runtime::Runtime::new()
                .unwrap()
                .block_on(async move {
                    let listener = tokio::net::TcpListener::from_std(listener).unwrap();
                    axum::serve(
                        listener,
                        router.into_make_service_with_connect_info::<SocketAddr>(),
                    )
                    .with_graceful_shutdown(async {
                        let _ = stopped.await;
                    })
                    .await
                    .unwrap();
                })
        });
        let ram = temp.path().join("ram");
        let state = temp.path().join("state");
        std::fs::create_dir(&ram).unwrap();
        std::fs::create_dir(&state).unwrap();
        let sink = Sink::new(
            TransferConfig {
                receiver: format!("http://{address}"),
                key: "a".repeat(48),
                lan: "10.0.0.0/24".into(),
                ram_directory: ram.clone(),
                state_directory: state.clone(),
                transport_compression: true,
            },
            Arc::new(Mutex::new(json!({}))),
        )
        .unwrap();
        sink.ready().unwrap();
        assert!(!sink.compression.load(Ordering::Relaxed));
        let raw = ram.join("STREHL0001.ARW");
        // Transfer fixture, not a claimed photographic RAW.
        let bytes = (0..1048576).map(|i| (i % 251) as u8).collect::<Vec<_>>();
        std::fs::write(&raw, &bytes).unwrap();
        let sum = hash_file(&raw).unwrap();
        let pending = json!({"run":"stack-transfer-test","name":"frame-000001.ARW","path":raw,"bytes":bytes.len(),"sha256":sum});
        save_json(&state.join("pending-transfer.json"), &pending).unwrap();
        let receipt = sink.finish_pending().unwrap().unwrap();
        assert_eq!(receipt["sha256"], sum);
        assert!(!raw.exists());
        assert_eq!(
            std::fs::read(pc.join("stack-transfer-test/frame-000001.ARW")).unwrap(),
            bytes
        );
        // Simulate a crash between deleting the RAM copy and deleting its intent.
        save_json(&state.join("pending-transfer.json"), &pending).unwrap();
        let recovered = sink.finish_pending().unwrap().unwrap();
        for field in ["ok", "durable", "bytes", "sha256", "path", "saved_unix_ms"] {
            assert_eq!(recovered[field], receipt[field], "{field}");
        }
        // JSON persistence can round diagnostic floats by one ULP. The file
        // identity and durable acknowledgement above must still match exactly.
        for field in ["upload_seconds", "upload_MB_per_second"] {
            let expected = receipt[field].as_f64().unwrap();
            assert!((recovered[field].as_f64().unwrap() - expected).abs() <= expected * 1e-12);
        }
        assert!(!state.join("pending-transfer.json").exists());
        // A missing RAM file with no matching durable receipt cannot be cleared.
        let mut unknown = pending;
        unknown["name"] = json!("frame-000002.ARW");
        save_json(&state.join("pending-transfer.json"), &unknown).unwrap();
        assert!(sink.finish_pending().is_err());
        assert!(state.join("pending-transfer.json").exists());
        version.store(1, Ordering::Relaxed);
        sink.ready().unwrap();
        assert!(sink.compression.load(Ordering::Relaxed));
        let compressed = sink
            .put_bytes(
                "stack-transfer-test",
                "frame-000003.ARW",
                bytes.clone(),
                Some(&sum),
            )
            .unwrap();
        assert_eq!(compressed["encoding"], transport::ENCODING);
        version.store(2, Ordering::Relaxed);
        let rolled_back = sink
            .put_bytes(
                "stack-transfer-test",
                "frame-000004.ARW",
                bytes.clone(),
                Some(&sum),
            )
            .unwrap();
        assert_eq!(version.load(Ordering::Relaxed), 3);
        assert_eq!(rolled_back["encoding"], "identity");
        assert_eq!(
            std::fs::read(pc.join("stack-transfer-test/frame-000004.ARW")).unwrap(),
            bytes
        );
        shutdown.send(()).unwrap();
        server.join().unwrap();
    }
}
