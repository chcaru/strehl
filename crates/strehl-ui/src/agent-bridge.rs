//! Capability-protected local mailbox. Disk I/O belongs to the worker, never
//! the render frame. Unix permissions / a protected Windows owner DACL make
//! the account boundary explicit; this is not a sandbox against the same user.
use super::{AgentReply, AgentRequest, MAX_REPLY_BYTES, MAX_REQUEST_BYTES};
use anyhow::{Context, Result, bail, ensure};
use serde::{Deserialize, Serialize};
use std::{
    collections::VecDeque,
    fs::{self, File, OpenOptions},
    io::{Read, Write},
    path::{Path, PathBuf},
    sync::{
        Arc,
        atomic::{AtomicBool, Ordering},
        mpsc::{self, Receiver, SyncSender},
    },
    thread,
    time::{Duration, Instant, SystemTime, UNIX_EPOCH},
};

const SCHEMA: u32 = 1;
const MAX_PENDING: usize = 16;
const REQUEST_LIFETIME_MS: u64 = 20_000;
const POLL: Duration = Duration::from_millis(30);

#[derive(Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
struct Descriptor {
    schema: u32,
    capability: String,
}
#[derive(Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
struct Envelope {
    capability: String,
    id: String,
    expires_at_ms: u64,
    request: AgentRequest,
}

/// Request handles own a one-shot response. Dropping one without replying
/// causes a bounded error, not a hang in the host.
pub(crate) struct IncomingRequest {
    pub request: AgentRequest,
    expires_at_ms: u64,
    reply: SyncSender<AgentReply>,
}
impl IncomingRequest {
    pub(crate) fn reply(self, reply: AgentReply) {
        let _ = self.reply.try_send(reply);
    }
    pub(crate) fn is_expired(&self) -> bool {
        now_ms() >= self.expires_at_ms
    }
}

pub(crate) struct AgentBridge {
    descriptor: PathBuf,
    requests: Receiver<IncomingRequest>,
    stopped: Arc<AtomicBool>,
}
impl AgentBridge {
    /// `parent` must be the application's private per-user data directory.
    /// Each enable creates a new session; stale host configurations cannot
    /// silently reconnect to a later workspace.
    pub(crate) fn start(parent: &Path) -> Result<Self> {
        fs::create_dir_all(parent).context("Create local agent session folder")?;
        let directory = parent.join(format!("session-{}", random_hex()?));
        create_private_directory(&directory)?;
        let descriptor = directory.join("session.json");
        let capability = random_hex()?;
        write_new(
            &descriptor,
            &serde_json::to_vec(&Descriptor {
                schema: SCHEMA,
                capability: capability.clone(),
            })?,
        )?;
        let (tx, requests) = mpsc::sync_channel(MAX_PENDING);
        let stopped = Arc::new(AtomicBool::new(false));
        let worker_stopped = stopped.clone();
        thread::Builder::new()
            .name("strehl-agent-mailbox".into())
            .spawn(move || {
                mailbox_worker(directory, capability, tx, worker_stopped);
            })?;
        Ok(Self {
            descriptor,
            requests,
            stopped,
        })
    }
    pub(crate) fn descriptor_path(&self) -> &Path {
        &self.descriptor
    }
    pub(crate) fn try_next(&self) -> Option<IncomingRequest> {
        while let Ok(request) = self.requests.try_recv() {
            if request.is_expired() {
                request.reply(AgentReply::error(
                    "Request expired before the UI could apply it; inspect state before retrying",
                ));
            } else {
                return Some(request);
            }
        }
        None
    }
}
impl Drop for AgentBridge {
    fn drop(&mut self) {
        self.stopped.store(true, Ordering::Release);
    }
}

struct PendingReply {
    id: String,
    expires_at_ms: u64,
    receiver: Receiver<AgentReply>,
}
fn mailbox_worker(
    directory: PathBuf,
    capability: String,
    sender: SyncSender<IncomingRequest>,
    stopped: Arc<AtomicBool>,
) {
    let mut pending: Vec<PendingReply> = Vec::new();
    let mut seen: VecDeque<(String, u64)> = VecDeque::new();
    // Continue the bounded directory scan across ticks. Reopening and taking
    // only its first page can permanently hide requests behind old replies.
    let mut scan: Option<fs::ReadDir> = None;
    while !stopped.load(Ordering::Acquire) {
        let now = now_ms();
        while seen.front().is_some_and(|(_, expiry)| *expiry <= now) {
            seen.pop_front();
        }
        pending.retain(|p| {
            let result = match p.receiver.try_recv() {
                Ok(reply) => Some(reply),
                Err(mpsc::TryRecvError::Disconnected) => Some(AgentReply::error(
                    "The application did not complete the request",
                )),
                Err(mpsc::TryRecvError::Empty) if now >= p.expires_at_ms => Some(
                    AgentReply::error("Request expired; inspect state before retrying"),
                ),
                Err(mpsc::TryRecvError::Empty) => None,
            };
            if let Some(reply) = result {
                let _ = write_reply(&directory, &p.id, reply);
                false
            } else {
                true
            }
        });
        if scan.is_none() {
            scan = fs::read_dir(&directory).ok();
        }
        if let Some(entries) = scan.as_mut() {
            // Untrusted queue flooding must not starve UI work or grow memory.
            let mut exhausted = false;
            for _ in 0..128 {
                let Some(entry) = entries.next() else {
                    exhausted = true;
                    break;
                };
                let Ok(entry) = entry else {
                    continue;
                };
                let name = entry.file_name();
                let Some(name) = name.to_str() else {
                    continue;
                };
                if name.starts_with("reply-")
                    && (name.ends_with(".json") || name.ends_with(".tmp"))
                    && entry.metadata().ok().is_some_and(|metadata| {
                        metadata.is_file()
                            && metadata
                                .modified()
                                .ok()
                                .and_then(|time| time.elapsed().ok())
                                .is_some_and(|age| {
                                    age > Duration::from_millis(REQUEST_LIFETIME_MS * 2)
                                })
                    })
                {
                    let _ = fs::remove_file(entry.path());
                    continue;
                }
                let Some(id) = name
                    .strip_prefix("request-")
                    .and_then(|s| s.strip_suffix(".json"))
                else {
                    continue;
                };
                if !valid_id(id) {
                    continue;
                }
                let path = entry.path();
                let body = read_regular_bounded(&path, MAX_REQUEST_BYTES);
                let _ = fs::remove_file(&path);
                let envelope =
                    body.and_then(|bytes| Ok(serde_json::from_slice::<Envelope>(&bytes)?));
                let Ok(envelope) = envelope else {
                    continue;
                };
                if !same_capability(&capability, &envelope.capability) || envelope.id != id {
                    continue;
                }
                if envelope.expires_at_ms <= now
                    || envelope.expires_at_ms > now.saturating_add(REQUEST_LIFETIME_MS + 5_000)
                {
                    let _ = write_reply(
                        &directory,
                        id,
                        AgentReply::error("Expired or invalid request deadline"),
                    );
                    continue;
                }
                // The sidecar does not retry mutations, and an accidentally
                // repeated mailbox message must not apply an operation twice.
                if seen.iter().any(|(seen, _)| seen == id) {
                    continue;
                }
                if seen.len() >= 1024 {
                    let _ = write_reply(
                        &directory,
                        id,
                        AgentReply::error("Command rate limit reached; wait before trying again"),
                    );
                    continue;
                }
                seen.push_back((id.to_owned(), envelope.expires_at_ms));
                if let Err(error) = envelope.request.validate() {
                    let _ = write_reply(&directory, id, AgentReply::error(error));
                    continue;
                }
                if pending.len() >= MAX_PENDING {
                    let _ = write_reply(
                        &directory,
                        id,
                        AgentReply::error("Strehl is busy; try again after reading its state"),
                    );
                    continue;
                }
                let (reply, receiver) = mpsc::sync_channel(1);
                let request = IncomingRequest {
                    request: envelope.request,
                    expires_at_ms: envelope.expires_at_ms,
                    reply,
                };
                match sender.try_send(request) {
                    Ok(()) => pending.push(PendingReply {
                        id: id.to_owned(),
                        expires_at_ms: envelope.expires_at_ms,
                        receiver,
                    }),
                    Err(_) => {
                        let _ = write_reply(
                            &directory,
                            id,
                            AgentReply::error("Strehl's command queue is full or closed"),
                        );
                    }
                }
            }
            if exhausted {
                scan = None;
            }
        }
        thread::sleep(POLL);
    }
    // Delete only files created by this protocol inside our unique directory;
    // never recurse through supplied paths or follow a directory link.
    let _ = fs::remove_file(directory.join("session.json"));
    if let Ok(entries) = fs::read_dir(&directory) {
        for entry in entries.take(512).flatten() {
            let name = entry.file_name();
            let name = name.to_string_lossy();
            if (name.starts_with("request-") || name.starts_with("reply-"))
                && name.ends_with(".json")
            {
                let _ = fs::remove_file(entry.path());
            }
        }
    }
    let _ = fs::remove_dir(directory);
}

pub(super) struct BridgeClient {
    directory: PathBuf,
    capability: String,
}
impl BridgeClient {
    pub(super) fn connect(path: &Path) -> Result<Self> {
        ensure!(
            path.file_name().is_some_and(|s| s == "session.json"),
            "Select the session.json supplied by Strehl"
        );
        let descriptor: Descriptor = serde_json::from_slice(&read_regular_bounded(path, 4096)?)?;
        ensure!(
            descriptor.schema == SCHEMA && valid_id(&descriptor.capability),
            "Invalid Strehl session descriptor"
        );
        let directory = path
            .parent()
            .context("Session has no directory")?
            .canonicalize()?;
        Ok(Self {
            directory,
            capability: descriptor.capability,
        })
    }
    pub(super) fn call(&self, request: AgentRequest) -> Result<AgentReply> {
        request.validate().map_err(anyhow::Error::msg)?;
        let descriptor: Descriptor = serde_json::from_slice(&read_regular_bounded(
            &self.directory.join("session.json"),
            4096,
        )?)?;
        ensure!(
            same_capability(&self.capability, &descriptor.capability),
            "Session was revoked; reconnect using the app"
        );
        let id = random_hex()?;
        let expires_at_ms = now_ms().saturating_add(REQUEST_LIFETIME_MS);
        let envelope = Envelope {
            capability: self.capability.clone(),
            id: id.clone(),
            expires_at_ms,
            request,
        };
        let bytes = serde_json::to_vec(&envelope)?;
        ensure!(
            bytes.len() <= MAX_REQUEST_BYTES,
            "Request is larger than 128 KiB"
        );
        let request_path = self.directory.join(format!("request-{id}.json"));
        let response_path = self.directory.join(format!("reply-{id}.json"));
        atomic_new(&request_path, &bytes)?;
        let deadline = Instant::now() + Duration::from_millis(REQUEST_LIFETIME_MS);
        while Instant::now() < deadline {
            if response_path.exists() {
                let bytes = read_regular_bounded(&response_path, MAX_REPLY_BYTES);
                let _ = fs::remove_file(&response_path);
                return Ok(serde_json::from_slice(&bytes?)?);
            }
            if !self.directory.join("session.json").is_file() {
                bail!("The human disconnected Strehl's agent session");
            }
            thread::sleep(POLL);
        }
        let _ = fs::remove_file(request_path);
        bail!(
            "Strehl did not answer before the deadline. Read a snapshot before retrying a mutation"
        )
    }
}

/// Resolve existing source/preset content only within a human-granted root.
/// Canonicalization rejects traversal via symlinks/junctions as well as `..`.
pub(crate) fn resolve_granted_path(root: &Path, relative: &str) -> Result<PathBuf> {
    super::safe_relative_path(relative).map_err(anyhow::Error::msg)?;
    let root = root
        .canonicalize()
        .context("The shared folder is unavailable")?;
    let path = root
        .join(relative)
        .canonicalize()
        .context("The requested item is unavailable")?;
    ensure!(
        path.starts_with(&root),
        "The item resolves outside the shared folder"
    );
    Ok(path)
}

fn write_reply(directory: &Path, id: &str, reply: AgentReply) -> Result<()> {
    let mut bytes = serde_json::to_vec(&reply)?;
    if bytes.len() > MAX_REPLY_BYTES {
        bytes = serde_json::to_vec(&AgentReply::error(
            "Reply exceeds 8 MiB; request a smaller region or preview",
        ))?;
    }
    atomic_new(&directory.join(format!("reply-{id}.json")), &bytes)
}
fn read_regular_bounded(path: &Path, maximum: usize) -> Result<Vec<u8>> {
    let meta = fs::symlink_metadata(path)?;
    ensure!(
        meta.file_type().is_file() && !meta.file_type().is_symlink(),
        "Expected an ordinary file"
    );
    #[cfg(windows)]
    {
        use std::os::windows::fs::MetadataExt;
        ensure!(
            meta.file_attributes() & 0x400 == 0,
            "Reparse points are not session files"
        );
    }
    ensure!(meta.len() <= maximum as u64, "Protocol file is too large");
    let mut data = Vec::with_capacity((meta.len() as usize).min(maximum));
    File::open(path)?
        .take(maximum as u64 + 1)
        .read_to_end(&mut data)?;
    ensure!(data.len() <= maximum, "Protocol file grew beyond its limit");
    Ok(data)
}
fn atomic_new(path: &Path, data: &[u8]) -> Result<()> {
    let temporary = path.with_extension(format!("{}.tmp", random_hex()?));
    write_new(&temporary, data)?;
    let result = fs::rename(&temporary, path);
    if result.is_err() {
        let _ = fs::remove_file(&temporary);
    }
    result.context("Publish local protocol message")
}
fn write_new(path: &Path, data: &[u8]) -> Result<()> {
    let mut options = OpenOptions::new();
    options.write(true).create_new(true);
    #[cfg(unix)]
    {
        use std::os::unix::fs::OpenOptionsExt;
        options.mode(0o600);
    }
    options.open(path)?.write_all(data)?;
    Ok(())
}
fn create_private_directory(path: &Path) -> Result<()> {
    #[cfg(unix)]
    {
        use std::os::unix::fs::DirBuilderExt;
        std::fs::DirBuilder::new().mode(0o700).create(path)?;
    }
    #[cfg(windows)]
    {
        use std::os::windows::ffi::OsStrExt;
        use windows_sys::Win32::{
            Foundation::LocalFree,
            Security::{
                Authorization::ConvertStringSecurityDescriptorToSecurityDescriptorW,
                SECURITY_ATTRIBUTES,
            },
            Storage::FileSystem::CreateDirectoryW,
        };
        // std::fs handles long paths automatically; the Win32 API requires an
        // extended absolute prefix. Canonicalize before allocating the descriptor.
        let absolute = path
            .parent()
            .context("Session directory has no parent")?
            .canonicalize()?
            .join(path.file_name().context("Session directory has no name")?);
        let path: Vec<u16> = absolute.as_os_str().encode_wide().chain(Some(0)).collect();
        // Owner rights, protected from inherited broad ACLs; inheritance applies
        // only inside this newly created directory.
        let sddl: Vec<u16> = "D:P(A;OICI;FA;;;OW)\0".encode_utf16().collect();
        let mut descriptor = std::ptr::null_mut();
        let converted = unsafe {
            ConvertStringSecurityDescriptorToSecurityDescriptorW(
                sddl.as_ptr(),
                1,
                &mut descriptor,
                std::ptr::null_mut(),
            )
        };
        ensure!(
            converted != 0,
            "Cannot create a private agent directory descriptor: {}",
            std::io::Error::last_os_error()
        );
        let attributes = SECURITY_ATTRIBUTES {
            nLength: std::mem::size_of::<SECURITY_ATTRIBUTES>() as u32,
            lpSecurityDescriptor: descriptor,
            bInheritHandle: 0,
        };
        let created = unsafe { CreateDirectoryW(path.as_ptr(), &attributes) };
        let error = std::io::Error::last_os_error();
        unsafe {
            LocalFree(descriptor);
        }
        ensure!(
            created != 0,
            "Cannot create a private agent directory: {error}"
        );
    }
    #[cfg(not(any(unix, windows)))]
    bail!("Local agent sessions are unavailable on this platform");
    Ok(())
}
fn random_hex() -> Result<String> {
    let mut bytes = [0_u8; 32];
    getrandom::fill(&mut bytes)
        .map_err(|e| anyhow::anyhow!("Secure randomness unavailable: {e}"))?;
    Ok(bytes.iter().map(|byte| format!("{byte:02x}")).collect())
}
fn valid_id(id: &str) -> bool {
    id.len() == 64
        && id
            .bytes()
            .all(|b| b.is_ascii_hexdigit() && !b.is_ascii_uppercase())
}
fn same_capability(a: &str, b: &str) -> bool {
    a.len() == 64
        && b.len() == 64
        && a.bytes()
            .zip(b.bytes())
            .fold(0_u8, |acc, (a, b)| acc | (a ^ b))
            == 0
}
fn now_ms() -> u64 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap_or_default()
        .as_millis()
        .min(u64::MAX as u128) as u64
}

#[cfg(test)]
#[path = "agent-bridge-tests.rs"]
mod tests;
