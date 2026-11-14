//! Native LAN client. Network, JPEG decoding and receiver I/O never run on egui.
//! Mutations are sent once with the revisions seen at the time of the click.
use anyhow::{Context, Result, ensure};
use eframe::egui;
use reqwest::blocking::{Client, Response};
use serde::{Deserialize, Serialize};
use serde_json::{Value, json};
use std::{
    collections::BTreeMap,
    io::Read,
    net::IpAddr,
    path::{Path, PathBuf},
    sync::{Arc, Mutex, mpsc},
    time::{Duration, Instant},
};
use strehl_capture::{
    lan::Lan,
    receiver::{ReceiverConfig, save_json},
    session::{Command, CommandRequest},
};

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

#[derive(Clone, Serialize)]
pub(crate) struct CompletedStack {
    pub folder: PathBuf,
    pub frames: usize,
    pub planes: usize,
    pub shots_per_plane: usize,
}
#[derive(Clone, Default)]
pub(crate) struct Snapshot {
    pub state: Value,
    pub online: bool,
    pub observed: Option<Instant>,
    pub connection_error: Option<String>,
    pub command_error: Option<String>,
    pub notice: Option<String>,
    pub pending: bool,
    pub receiver: Value,
    pub receiver_error: Option<String>,
    pub completed: Vec<CompletedStack>,
    pub preview: Option<(u64, Arc<egui::ColorImage>)>,
    pub peaking: Option<(u64, Arc<crate::capture_aids::Peaking>)>,
    pub preview_error: Option<String>,
    pub handoff: Option<PathBuf>,
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
            "preview":self.preview.as_ref().map(|(generation,image)|json!({"generation":generation,"width":image.width(),"height":image.height()})),
            "preview_error":self.preview_error})
    }
    pub fn request(&self, command: Command) -> Result<CommandRequest> {
        ensure!(
            self.fresh(),
            "Reconnect to the Pi before sending a camera command"
        );
        Ok(CommandRequest {
            id: strehl_capture::lan::new_key()?,
            camera_revision: self.state["camera_revision"]
                .as_u64()
                .context("Missing camera revision")?,
            plan_revision: self.state["plan_revision"]
                .as_u64()
                .context("Missing plan revision")?,
            sequence_id: self.state["sequence_id"]
                .as_u64()
                .context("Missing sequence")?,
            command,
        })
    }
}
enum Work {
    Command(CommandRequest),
    Configure(Config),
    StartReceiver,
    Storage { folder: PathBuf, compress_raw: bool },
    Handoff(PathBuf),
}
pub(crate) struct Connection {
    shared: Arc<Mutex<Snapshot>>,
    sender: mpsc::SyncSender<Work>,
}
impl Connection {
    pub fn start(config: Config, path: PathBuf, ctx: egui::Context) -> Result<Self> {
        let shared = Arc::new(Mutex::new(Snapshot::default()));
        let (sender, receiver) = mpsc::sync_channel(2);
        let output = shared.clone();
        std::thread::Builder::new()
            .name("strehl-capture-client".into())
            .spawn(move || {
                if let Err(error) = run(config, path, &output, receiver, &ctx) {
                    output.lock().unwrap().connection_error = Some(format!("{error:#}"));
                    ctx.request_repaint();
                }
            })?;
        Ok(Self { shared, sender })
    }
    pub fn snapshot(&self) -> Snapshot {
        self.shared.lock().unwrap().clone()
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
    ctx: &egui::Context,
) -> Result<()> {
    let client = client()?;
    let mut configured = config.normalize().is_ok();
    let mut receiver_due = Instant::now();
    let mut history_due = Instant::now();
    let mut last_preview = None;
    loop {
        match requests.recv_timeout(Duration::from_millis(200)) {
            Err(mpsc::RecvTimeoutError::Disconnected) => return Ok(()),
            Err(mpsc::RecvTimeoutError::Timeout) => {}
            Ok(work) => {
                let result = (|| -> Result<&str> {
                    match work {
                        Work::Command(request) => {
                            ensure!(configured, "Configure the Pi connection first");
                            post_json(
                                &client,
                                &config.controller,
                                "/api/command",
                                &config.pairing_key,
                                &request,
                            )?;
                            Ok("Request accepted")
                        }
                        Work::Configure(mut next) => {
                            next.normalize()?;
                            save_json(&path, &next)?;
                            config = next;
                            configured = true;
                            last_preview = None;
                            let mut s = output.lock().unwrap();
                            s.state = Value::Null;
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
                            ensure!(
                                completed_stacks(&config.receiver_config)?
                                    .iter()
                                    .any(|s| s.folder == folder),
                                "Choose a completed stack registered with this receiver"
                            );
                            output.lock().unwrap().handoff = Some(folder);
                            Ok("Completed capture ready for Projects")
                        }
                    }
                })();
                let mut s = output.lock().unwrap();
                s.pending = false;
                match result {
                    Ok(notice) => s.notice = Some(notice.into()),
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
                    {
                        let mut s = output.lock().unwrap();
                        s.state = state.clone();
                        s.online = true;
                        s.observed = Some(Instant::now());
                        s.connection_error = None;
                    }
                    if state["preview"]["available"] == true && generation != last_preview {
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
                        let mut s = output.lock().unwrap();
                        match preview {
                            Ok(image) => {
                                s.peaking = peaks.map(|p| (generation.unwrap_or(0), Arc::new(p)));
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
            let completed = completed_stacks(&config.receiver_config).unwrap_or_default();
            output.lock().unwrap().completed = completed;
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
    let frames = planes * shots;
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
    ensure!(receipts.len() == frames, "Incomplete RAW receipts");
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
            Some("strehl-archive-v1") => format!("{name}.straw"),
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
fn completed_stacks(config_path: &Path) -> Result<Vec<CompletedStack>> {
    let registry: BTreeMap<String, Value> = serde_json::from_slice(&read_file(
        &config_path.with_extension("runs.json"),
        8 * 1024 * 1024,
    )?)?;
    let mut completed = Vec::new();
    for (_, entry) in registry.iter().rev().take(32) {
        if let Some(folder) = entry.as_str().or_else(|| entry["folder"].as_str())
            && let Ok(stack) = verify_completed(Path::new(folder))
        {
            completed.push(stack);
        }
        if completed.len() == 8 {
            break;
        }
    }
    Ok(completed)
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
            state: json!({"camera_revision":7,"plan_revision":9,"sequence_id":4}),
            ..Default::default()
        };
        let a = s.request(Command::Start {}).unwrap();
        s.state["camera_revision"] = json!(8);
        assert_eq!(a.camera_revision, 7);
        assert_eq!(a.plan_revision, 9);
        assert_eq!(a.sequence_id, 4);
        s.online = false;
        assert!(s.request(Command::Start {}).is_err());
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
