//! Authenticated LAN receiver. Acknowledgements follow checksum and durable writes.
use crate::{
    lan::{Lan, equal_key},
    transport,
};
use anyhow::{Context, Result, ensure};
use axum::{
    Json, Router,
    body::Body,
    extract::{ConnectInfo, DefaultBodyLimit, Path as UrlPath, State},
    http::{Request, StatusCode, header},
    middleware::{self, Next},
    response::{IntoResponse, Response},
    routing::{get, post, put},
};
use futures_util::StreamExt;
use serde::{Deserialize, Serialize};
use serde_json::{Value, json};
use sha2::{Digest, Sha256};
use std::{
    collections::BTreeMap,
    fs::{File, OpenOptions},
    io::{BufWriter, Read, Write},
    net::SocketAddr,
    path::{Path, PathBuf},
    sync::{Arc, Mutex},
};
use strehl_raw_codec::archive;
use tokio_util::io::{StreamReader, SyncIoBridge};

pub use crate::transport::MAX_RAW;
#[derive(Clone, Serialize, Deserialize)]
pub struct ReceiverConfig {
    pub bind: SocketAddr,
    pub lan: String,
    pub key: String,
    pub folder: PathBuf,
    #[serde(default = "default_compress_raw")]
    pub compress_raw: bool,
}
fn default_compress_raw() -> bool {
    true
}
/// Existing registered runs retain their original file representation, even
/// after an upgrade, a restart, or a change to the new-stack default.
#[derive(Clone, Serialize, Deserialize)]
#[serde(untagged)]
enum RunDestination {
    Legacy(PathBuf),
    Current { folder: PathBuf, compress_raw: bool },
}
impl RunDestination {
    fn folder(&self) -> &Path {
        match self {
            Self::Legacy(p) => p,
            Self::Current { folder, .. } => folder,
        }
    }
    fn compress_raw(&self) -> bool {
        matches!(
            self,
            Self::Current {
                compress_raw: true,
                ..
            }
        )
    }
}
pub struct Receiver {
    config: Mutex<ReceiverConfig>,
    config_path: PathBuf,
    lan: Lan,
    runs: Mutex<BTreeMap<String, RunDestination>>,
    write_lock: tokio::sync::Mutex<()>,
    latest: Mutex<Value>,
}
pub fn save_json(path: &Path, value: &impl Serialize) -> Result<()> {
    let parent = path.parent().context("Configuration has no parent")?;
    std::fs::create_dir_all(parent)?;
    let mut tmp = tempfile::NamedTempFile::new_in(parent)?;
    serde_json::to_writer_pretty(&mut tmp, value)?;
    tmp.write_all(b"\n")?;
    tmp.as_file().sync_all()?;
    tmp.persist(path).map_err(|e| e.error)?;
    sync_directory(parent)?;
    Ok(())
}
fn sync_directory(path: &Path) -> Result<()> {
    #[cfg(unix)]
    File::open(path)?.sync_all()?;
    #[cfg(not(unix))]
    let _ = path;
    Ok(())
}
pub fn hash_file(path: &Path) -> Result<String> {
    let mut f = File::open(path)?;
    let mut hash = Sha256::new();
    let mut block = [0u8; 128 * 1024];
    loop {
        let n = f.read(&mut block)?;
        if n == 0 {
            break;
        }
        hash.update(&block[..n]);
    }
    Ok(hash.finalize().iter().map(|b| format!("{b:02x}")).collect())
}
pub fn safe_run(s: &str) -> bool {
    s.starts_with("stack-")
        && (7..=100).contains(&s.len())
        && s.bytes().all(|c| c.is_ascii_alphanumeric() || c == b'-')
}
pub fn safe_name(s: &str) -> bool {
    matches!(s, "manifest.json" | "events.jsonl" | "result.json")
        || (s.len() == 16
            && s.starts_with("frame-")
            && s.ends_with(".ARW")
            && s[6..12].bytes().all(|c| c.is_ascii_digit()))
}
impl Receiver {
    pub fn open(path: PathBuf) -> Result<Arc<Self>> {
        let config: ReceiverConfig = serde_json::from_slice(&std::fs::read(&path)?)?;
        ensure!(
            config.key.len() >= 48,
            "Receiver key is missing or too short"
        );
        ensure!(
            config.folder.is_absolute(),
            "Capture folder must be an absolute local path"
        );
        std::fs::create_dir_all(&config.folder)?;
        let index = path.with_extension("runs.json");
        let runs = if index.exists() {
            serde_json::from_slice(&std::fs::read(index)?)?
        } else {
            BTreeMap::new()
        };
        Ok(Arc::new(Self {
            lan: Lan::parse(&config.lan)?,
            config: Mutex::new(config),
            config_path: path,
            runs: Mutex::new(runs),
            write_lock: tokio::sync::Mutex::new(()),
            latest: Mutex::new(json!({})),
        }))
    }
    pub fn bind(&self) -> SocketAddr {
        self.config.lock().unwrap().bind
    }
    pub fn router(self: Arc<Self>) -> Router {
        Router::new()
            .route(
                "/",
                get(|| async {
                    (
                        [(header::CONTENT_TYPE, "text/html; charset=utf-8")],
                        include_str!("../web/receiver.html"),
                    )
                }),
            )
            .route(
                "/receiver.js",
                get(|| async {
                    (
                        [(header::CONTENT_TYPE, "text/javascript; charset=utf-8")],
                        include_str!("../web/receiver.js"),
                    )
                }),
            )
            .route(
                "/style.css",
                get(|| async {
                    (
                        [(header::CONTENT_TYPE, "text/css")],
                        include_str!("../web/style.css"),
                    )
                }),
            )
            .route("/api/status", get(status))
            .route("/api/folder", post(folder))
            .route("/api/runs/{run}", post(create_run).get(run_capacity))
            .route("/api/files/{run}/{name}", put(upload))
            .layer(DefaultBodyLimit::max(MAX_RAW as usize))
            .layer(middleware::from_fn_with_state(self.clone(), guard))
            .with_state(self)
    }
}
fn problem(status: StatusCode, error: impl std::fmt::Display) -> Response {
    (status, Json(json!({"error":error.to_string()}))).into_response()
}
async fn guard(
    State(s): State<Arc<Receiver>>,
    ConnectInfo(peer): ConnectInfo<SocketAddr>,
    request: Request<Body>,
    next: Next,
) -> Response {
    if !s.lan.permits(peer.ip()) {
        return problem(StatusCode::FORBIDDEN, "Local network only");
    }
    let host = request
        .headers()
        .get(header::HOST)
        .and_then(|v| v.to_str().ok())
        .unwrap_or("");
    if request
        .headers()
        .get(header::ORIGIN)
        .is_some_and(|v| v.to_str().ok() != Some(format!("http://{host}").as_str()))
        || request
            .headers()
            .get("sec-fetch-site")
            .is_some_and(|v| v == "cross-site")
    {
        return problem(StatusCode::FORBIDDEN, "Same-origin requests only");
    }
    if request.uri().path().starts_with("/api/") {
        let auth = request
            .headers()
            .get(header::AUTHORIZATION)
            .and_then(|v| v.to_str().ok())
            .and_then(|v| v.strip_prefix("Bearer "))
            .unwrap_or("");
        if !equal_key(auth, &s.config.lock().unwrap().key) {
            return problem(StatusCode::UNAUTHORIZED, "Pair this receiver");
        }
    }
    let mut r = next.run(request).await;
    r.headers_mut()
        .insert("cache-control", "no-store".parse().unwrap());
    r.headers_mut()
        .insert("referrer-policy", "no-referrer".parse().unwrap());
    r.headers_mut().insert("content-security-policy","default-src 'self'; script-src 'self'; style-src 'self'; frame-ancestors 'none'; base-uri 'none'".parse().unwrap());
    r
}
async fn status(State(s): State<Arc<Receiver>>) -> Response {
    let c = s.config.lock().unwrap();
    if !c.folder.is_dir() {
        return problem(
            StatusCode::SERVICE_UNAVAILABLE,
            "Capture folder is missing; choose an available folder on this PC",
        );
    }
    match fs2::available_space(&c.folder) {
        Ok(free)=>Json(json!({"ok":true,"protocol":1,"raw_encodings":["identity",transport::ENCODING],"folder":c.folder,"compress_raw":c.compress_raw,"free_bytes":free,"max_raw_bytes":MAX_RAW,"latest":*s.latest.lock().unwrap()})).into_response(),
        Err(e)=>problem(StatusCode::SERVICE_UNAVAILABLE,e)
    }
}
async fn folder(
    State(s): State<Arc<Receiver>>,
    ConnectInfo(peer): ConnectInfo<SocketAddr>,
    Json(data): Json<Value>,
) -> Response {
    if !peer.ip().is_loopback() {
        return problem(StatusCode::FORBIDDEN, "Change receiver settings on this PC");
    }
    let _write = s.write_lock.lock().await;
    let result = (|| -> Result<()> {
        let p = PathBuf::from(data["folder"].as_str().context("Missing folder")?);
        ensure!(p.is_absolute(), "Use an absolute folder path");
        std::fs::create_dir_all(&p)?;
        let probe = tempfile::NamedTempFile::new_in(&p)?;
        probe.as_file().sync_all()?;
        let mut c = s.config.lock().unwrap();
        let mut next = c.clone();
        next.folder = p.canonicalize()?;
        if let Some(value) = data.get("compress_raw") {
            next.compress_raw = value.as_bool().context("Invalid compression setting")?;
        }
        save_json(&s.config_path, &next)?;
        *c = next;
        Ok(())
    })();
    match result{Ok(())=>Json(json!({"ok":true,"message":"Saved for new stacks. Registered stacks keep their folder and storage format."})).into_response(),Err(e)=>problem(StatusCode::BAD_REQUEST,e)}
}
// Capacity of the pinned run, independent of later changes to the default folder.
async fn run_capacity(State(s): State<Arc<Receiver>>, UrlPath(run): UrlPath<String>) -> Response {
    let result = (|| -> Result<Value> {
        ensure!(safe_run(&run), "Invalid stack identifier");
        let runs = s.runs.lock().unwrap();
        let dest = runs.get(&run).context("Stack is not registered")?;
        ensure!(dest.folder().is_dir(), "Registered stack folder is missing");
        Ok(
            json!({"ok":true,"folder":dest.folder(),"free_bytes":fs2::available_space(dest.folder())?}),
        )
    })();
    match result {
        Ok(v) => Json(v).into_response(),
        Err(e) => problem(StatusCode::CONFLICT, e),
    }
}
async fn create_run(State(s): State<Arc<Receiver>>, UrlPath(run): UrlPath<String>) -> Response {
    let _write = s.write_lock.lock().await;
    let result = (|| -> Result<RunDestination> {
        ensure!(safe_run(&run), "Invalid stack identifier");
        let mut runs = s.runs.lock().unwrap();
        if let Some(p) = runs.get(&run) {
            ensure!(p.folder().is_dir(), "Stack folder is missing");
            return Ok(p.clone());
        }
        let config = s.config.lock().unwrap().clone();
        let p = config.folder.join(&run);
        std::fs::create_dir(&p)
            .context("Create a new stack folder; refusing to reuse an unregistered directory")?;
        let destination = RunDestination::Current {
            folder: p,
            compress_raw: config.compress_raw,
        };
        let mut next = runs.clone();
        next.insert(run, destination.clone());
        save_json(&s.config_path.with_extension("runs.json"), &next)?;
        *runs = next;
        Ok(destination)
    })();
    match result {
        Ok(p) => Json(json!({"ok":true,"folder":p.folder(),"compress_raw":p.compress_raw()}))
            .into_response(),
        Err(e) => problem(StatusCode::CONFLICT, e),
    }
}
async fn upload(
    State(s): State<Arc<Receiver>>,
    UrlPath((run, name)): UrlPath<(String, String)>,
    request: Request<Body>,
) -> Response {
    if request
        .headers()
        .get(transport::ENCODING_HEADER)
        .is_some_and(|v| v != "identity" && v != transport::ENCODING)
    {
        return problem(
            StatusCode::UNSUPPORTED_MEDIA_TYPE,
            "Unsupported RAW transport encoding",
        );
    }
    let result = receive_file(&s, &run, &name, request).await;
    match result {
        Ok(v) => Json(v).into_response(),
        Err(e) => problem(StatusCode::SERVICE_UNAVAILABLE, e),
    }
}
async fn receive_file(
    s: &Receiver,
    run: &str,
    name: &str,
    request: Request<Body>,
) -> Result<Value> {
    ensure!(safe_run(run) && safe_name(name), "Invalid destination name");
    let _write = s.write_lock.lock().await;
    let target = s
        .runs
        .lock()
        .unwrap()
        .get(run)
        .cloned()
        .context("Register the stack before uploading")?;
    let directory = target.folder().to_path_buf();
    let archive_raw = target.compress_raw() && name.ends_with(".ARW");
    let expected = request
        .headers()
        .get("x-content-sha256")
        .context("Missing checksum")?
        .to_str()?
        .to_owned();
    ensure!(
        expected.len() == 64
            && expected
                .bytes()
                .all(|c| c.is_ascii_hexdigit() && !c.is_ascii_uppercase()),
        "Invalid SHA-256"
    );
    let encoding = request
        .headers()
        .get(transport::ENCODING_HEADER)
        .map(|v| v.to_str())
        .transpose()?
        .unwrap_or("identity")
        .to_owned();
    ensure!(
        encoding == "identity" || encoding == transport::ENCODING,
        "Unsupported RAW transport encoding"
    );
    let compressed = encoding == transport::ENCODING;
    ensure!(
        !compressed || name.ends_with(".ARW"),
        "Compression is only supported for RAW files"
    );
    let wire_length: Option<u64> = request
        .headers()
        .get(header::CONTENT_LENGTH)
        .map(|v| Ok::<_, anyhow::Error>(v.to_str()?.parse()?))
        .transpose()?;
    ensure!(
        wire_length.is_none_or(|n| n <= transport::MAX_WIRE),
        "Wire body exceeds size limit"
    );
    let length: u64 = if compressed {
        request
            .headers()
            .get(transport::LENGTH_HEADER)
            .context("Missing original file length")?
            .to_str()?
            .parse()?
    } else {
        wire_length.context("Missing file length")?
    };
    ensure!(
        length <= MAX_RAW && (name != "manifest.json" || length <= 1024 * 1024),
        "File exceeds its size limit"
    );
    if name.ends_with(".ARW") {
        ensure!(length >= 1024, "Incomplete RAW");
    }
    let destination = directory.join(if archive_raw {
        format!("{name}.{}", archive::EXTENSION)
    } else {
        name.to_owned()
    });
    if name.ends_with(".ARW") {
        let alternative = directory.join(if archive_raw {
            name.to_owned()
        } else {
            format!("{name}.{}", archive::EXTENSION)
        });
        ensure!(
            !alternative.exists(),
            "A RAW in a different storage format already exists; refusing to create conflicting originals"
        );
    }
    let candidate = destination.clone();
    let checksum = expected.clone();
    let duplicate =
        tokio::task::spawn_blocking(move || -> Result<bool> {
            if !candidate.exists() {
                return Ok(false);
            }
            if archive_raw {
                // Never trust only the envelope on a retry: bit rot must not turn
                // into an acknowledgement that discards the Pi's remaining RAW.
                let decoded = archive::verify(&candidate)?;
                Ok(decoded.bytes == length && decoded.sha256 == checksum)
            } else {
                Ok(std::fs::metadata(&candidate)?.len() == length
                    && hash_file(&candidate)? == checksum)
            }
        })
        .await??;
    ensure!(
        duplicate || !destination.exists() || name == "events.jsonl",
        "Refusing to overwrite a different existing file"
    );
    ensure!(
        duplicate || fs2::available_space(&directory)? > length + 512 * 1024 * 1024,
        "PC disk is full; free space before capture can continue"
    );
    let temp = if duplicate {
        None
    } else {
        Some(
            tempfile::Builder::new()
                .prefix(".receiving-")
                .suffix(".partial")
                .tempfile_in(&directory)?,
        )
    };
    // Pull from HTTP only as the bounded decoder consumes it. CPU work and file
    // writes stay off the async executor; malformed/cancelled bodies own only a
    // removable partial file. A duplicate must decode/validate the entire retry.
    let stream =
        futures_util::stream::unfold(request.into_body().into_data_stream(), |mut s| async move {
            match tokio::time::timeout(std::time::Duration::from_secs(60), s.next()).await {
                Ok(Some(chunk)) => Some((chunk.map_err(std::io::Error::other), s)),
                Ok(None) => None,
                Err(e) => Some((Err(std::io::Error::new(std::io::ErrorKind::TimedOut, e)), s)),
            }
        });
    let reader = SyncIoBridge::new(StreamReader::new(Box::pin(stream)));
    let expected_copy = expected.clone();
    let (decoded, temp) = tokio::task::spawn_blocking(move || -> Result<_> {
        let mut temp = temp;
        let decoded = if let Some(file) = temp.as_mut() {
            let mut output = BufWriter::with_capacity(1024 * 1024, file.as_file_mut());
            let decoded = if archive_raw && compressed {
                archive::retain(reader, &mut output, length, &expected_copy)?
            } else if archive_raw {
                let mut bytes = Vec::with_capacity(length as usize);
                let decoded = transport::decode(reader, &mut bytes, length, false)?;
                ensure!(
                    decoded.sha256 == expected_copy,
                    "Checksum mismatch; file was not committed"
                );
                archive::pack(bytes, &mut output)?;
                decoded
            } else {
                transport::decode(reader, &mut output, length, compressed)?
            };
            output.flush()?;
            decoded
        } else {
            transport::decode(reader, std::io::sink(), length, compressed)?
        };
        ensure!(
            decoded.sha256 == expected_copy,
            "Checksum mismatch; file was not committed"
        );
        ensure!(
            wire_length.is_none_or(|n| n == decoded.wire_bytes),
            "Wire length mismatch"
        );
        if let Some(file) = &temp {
            file.as_file().sync_all()?;
        }
        Ok((decoded, temp))
    })
    .await??;
    let storage_encoding = if archive_raw {
        archive::ENCODING
    } else {
        "identity"
    };
    if duplicate {
        return Ok(
            json!({"ok":true,"durable":true,"sha256":expected,"bytes":length,"path":destination,
            "already_saved":true,"encoding":encoding,"wire_bytes":decoded.wire_bytes,"chunks":decoded.chunks,
            "logical_name":name,"storage_encoding":storage_encoding,"storage_bytes":std::fs::metadata(&destination)?.len()}),
        );
    }
    let temp = temp.context("Missing upload partial file")?;
    if destination.exists() {
        let old = std::fs::read(&destination)?;
        let mut prefix = vec![0; old.len()];
        File::open(temp.path())?.read_exact(&mut prefix)?;
        ensure!(
            prefix == old,
            "Journal update must preserve all prior records"
        );
        temp.persist(&destination).map_err(|e| e.error)?;
    } else {
        temp.persist_noclobber(&destination).map_err(|e| e.error)?;
    }
    sync_directory(&directory)?;
    let receipt = json!({"ok":true,"durable":true,"sha256":decoded.sha256,"bytes":decoded.bytes,"path":destination,"saved_unix_ms":crate::journal::now_ms(),
        "encoding":encoding,"wire_bytes":decoded.wire_bytes,"chunks":decoded.chunks,
        "logical_name":name,"storage_encoding":storage_encoding,"storage_bytes":std::fs::metadata(&destination)?.len()});
    let mut receipts = OpenOptions::new()
        .create(true)
        .append(true)
        .open(directory.join("transfer-receipts.jsonl"))?;
    serde_json::to_writer(&mut receipts, &receipt)?;
    receipts.write_all(b"\n")?;
    receipts.sync_all()?;
    if name.ends_with(".ARW") {
        *s.latest.lock().unwrap() = receipt.clone();
    }
    Ok(receipt)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn default_archive_pins_runs_validates_retries_and_migrates_old_settings() {
        let temp = tempfile::tempdir().unwrap();
        let config = temp.path().join("receiver.json");
        let root = temp.path().join("images");
        let legacy = root.join("stack-legacy");
        std::fs::create_dir_all(&legacy).unwrap();
        save_json(
            &config,
            &json!({"bind":"127.0.0.1:0","lan":"10.0.0.0/24","key":"a".repeat(48),"folder":root}),
        )
        .unwrap();
        save_json(
            &config.with_extension("runs.json"),
            &json!({"stack-legacy":legacy}),
        )
        .unwrap();
        let s = Receiver::open(config.clone()).unwrap();
        assert!(
            s.config.lock().unwrap().compress_raw,
            "Old configs default new stacks to compressed storage"
        );
        assert!(!s.runs.lock().unwrap()["stack-legacy"].compress_raw());
        let run = "stack-new-archive";
        assert!(
            create_run(State(s.clone()), UrlPath(run.into()))
                .await
                .status()
                .is_success()
        );
        assert!(
            folder(
                State(s.clone()),
                ConnectInfo("127.0.0.1:1".parse().unwrap()),
                Json(json!({"folder":root,"compress_raw":false}))
            )
            .await
            .status()
            .is_success()
        );
        assert_eq!(
            folder(
                State(s.clone()),
                ConnectInfo("10.0.0.13:1".parse().unwrap()),
                Json(json!({"folder":root,"compress_raw":true}))
            )
            .await
            .status(),
            StatusCode::FORBIDDEN
        );
        drop(s);
        let s = Receiver::open(config).unwrap();
        assert!(!s.config.lock().unwrap().compress_raw);
        assert!(
            s.runs.lock().unwrap()[run].compress_raw(),
            "Format is pinned across toggle and restart"
        );
        assert!(
            create_run(State(s.clone()), UrlPath("stack-plain".into()))
                .await
                .status()
                .is_success()
        );
        let bytes = (0..16384).map(|i| (i % 251) as u8).collect::<Vec<_>>();
        let sum: String = Sha256::digest(&bytes)
            .iter()
            .map(|b| format!("{b:02x}"))
            .collect();
        let mut archive_bytes = Vec::new();
        archive::pack(bytes.clone(), &mut archive_bytes).unwrap();
        let wire = archive_bytes[archive::HEADER_BYTES as usize..].to_vec();
        let request = |body: Vec<u8>, compressed: bool, checksum: &str| {
            let mut b = Request::builder()
                .header("x-content-sha256", checksum)
                .header(header::CONTENT_LENGTH, body.len());
            if compressed {
                b = b
                    .header(transport::ENCODING_HEADER, transport::ENCODING)
                    .header(transport::LENGTH_HEADER, bytes.len());
            }
            b.body(Body::from(body)).unwrap()
        };
        let name = "frame-000001.ARW";
        let file = root.join(run).join(format!("{name}.straw"));
        for (body, checksum) in [
            (wire[..wire.len() - 1].to_vec(), sum.clone()),
            (wire.clone(), "0".repeat(64)),
        ] {
            assert!(
                receive_file(&s, run, name, request(body, true, &checksum))
                    .await
                    .is_err()
            );
            assert_eq!(std::fs::read_dir(root.join(run)).unwrap().count(), 0);
        }
        let receipt = receive_file(&s, run, name, request(wire.clone(), true, &sum))
            .await
            .unwrap();
        assert_eq!(receipt["storage_encoding"], archive::ENCODING);
        assert_eq!(receipt["storage_bytes"], archive_bytes.len());
        assert_eq!(receipt["bytes"], bytes.len());
        assert_eq!(
            std::fs::read(&file).unwrap(),
            archive_bytes,
            "Retain exactly the existing compressed stream"
        );
        assert_eq!(archive::read_original(&file).unwrap(), bytes);
        assert!(
            !root.join(run).join(name).exists(),
            "No expanded ARW on disk"
        );
        let retry = receive_file(&s, run, name, request(wire.clone(), true, &sum))
            .await
            .unwrap();
        assert_eq!(retry["already_saved"], true);
        assert!(
            receive_file(
                &s,
                run,
                name,
                request(wire[..wire.len() - 1].to_vec(), true, &sum)
            )
            .await
            .is_err()
        );
        let mut corrupt = archive_bytes.clone();
        corrupt[16] ^= 1;
        std::fs::write(&file, &corrupt).unwrap();
        assert!(
            receive_file(&s, run, name, request(wire.clone(), true, &sum))
                .await
                .is_err(),
            "Corrupt stored copy must never acknowledge the only remaining original"
        );
        assert_eq!(std::fs::read(&file).unwrap(), corrupt);
        std::fs::write(&file, &archive_bytes).unwrap();
        std::fs::write(root.join(run).join(name), &bytes).unwrap();
        assert!(
            receive_file(&s, run, name, request(wire.clone(), true, &sum))
                .await
                .is_err(),
            "Conflicting representation refused"
        );
        // Identity-only sender still produces a compressed archive.
        let second = "frame-000002.ARW";
        receive_file(&s, run, second, request(bytes.clone(), false, &sum))
            .await
            .unwrap();
        assert_eq!(
            archive::read_original(&root.join(run).join(format!("{second}.straw"))).unwrap(),
            bytes
        );
        for plain_run in ["stack-legacy", "stack-plain"] {
            let saved = receive_file(&s, plain_run, name, request(wire.clone(), true, &sum))
                .await
                .unwrap();
            assert_eq!(saved["storage_encoding"], "identity");
            assert_eq!(
                std::fs::read(root.join(plain_run).join(name)).unwrap(),
                bytes
            );
        }
    }

    #[tokio::test]
    async fn capacity_uses_the_registered_folder_after_the_default_changes() {
        let temp = tempfile::tempdir().unwrap();
        let config = temp.path().join("receiver.json");
        let root = temp.path().join("original");
        save_json(
            &config,
            &json!({"bind":"127.0.0.1:0","lan":"10.0.0.0/24","key":"a".repeat(48),"folder":root}),
        )
        .unwrap();
        let receiver = Receiver::open(config).unwrap();
        assert!(
            create_run(State(receiver.clone()), UrlPath("stack-pinned".into()))
                .await
                .status()
                .is_success()
        );
        receiver.config.lock().unwrap().folder = temp.path().join("missing-default");
        assert_eq!(
            status(State(receiver.clone())).await.status(),
            StatusCode::SERVICE_UNAVAILABLE
        );
        let response = run_capacity(State(receiver.clone()), UrlPath("stack-pinned".into())).await;
        assert!(response.status().is_success());
        let body = axum::body::to_bytes(response.into_body(), 8192)
            .await
            .unwrap();
        let value: Value = serde_json::from_slice(&body).unwrap();
        assert_eq!(value["folder"], json!(root.join("stack-pinned")));
        assert!(value["free_bytes"].as_u64().unwrap() > 0);
        assert_eq!(
            run_capacity(State(receiver), UrlPath("stack-unknown".into()))
                .await
                .status(),
            StatusCode::CONFLICT
        );
    }

    #[tokio::test]
    async fn compressed_partials_corruption_retries_and_metadata_bounds() {
        let temp = tempfile::tempdir().unwrap();
        let config = temp.path().join("receiver.json");
        save_json(
            &config,
            &ReceiverConfig {
                compress_raw: false,
                bind: "127.0.0.1:0".parse().unwrap(),
                lan: "10.0.0.0/24".into(),
                key: "a".repeat(48),
                folder: temp.path().join("images"),
            },
        )
        .unwrap();
        let s = Receiver::open(config).unwrap();
        let run = "stack-compressed-test";
        let directory = temp.path().join("images").join(run);
        std::fs::create_dir(&directory).unwrap();
        s.runs
            .lock()
            .unwrap()
            .insert(run.into(), RunDestination::Legacy(directory.clone()));
        let bytes = vec![93u8; 4 * 1024 * 1024 + 39];
        let sum: String = Sha256::digest(&bytes)
            .iter()
            .map(|b| format!("{b:02x}"))
            .collect();
        let pool = Arc::new(
            rayon::ThreadPoolBuilder::new()
                .num_threads(transport::WORKERS)
                .build()
                .unwrap(),
        );
        let mut wire = Vec::new();
        transport::Encoder::new(bytes.clone().into(), pool)
            .unwrap()
            .read_to_end(&mut wire)
            .unwrap();
        let request = |wire: Vec<u8>, hash: &str, length: u64, encoding: &str| {
            Request::builder()
                .header("x-content-sha256", hash)
                .header(transport::ENCODING_HEADER, encoding)
                .header(transport::LENGTH_HEADER, length)
                .body(Body::from(wire))
                .unwrap()
        };
        let name = "frame-000001.ARW";
        let n = bytes.len() as u64;
        for bad in [
            wire[..wire.len() - 3].to_vec(),
            [wire.clone(), vec![1]].concat(),
        ] {
            assert!(
                receive_file(&s, run, name, request(bad, &sum, n, transport::ENCODING))
                    .await
                    .is_err()
            );
            assert_eq!(
                std::fs::read_dir(&directory).unwrap().count(),
                0,
                "No partial is retained or committed"
            );
        }
        assert!(
            receive_file(
                &s,
                run,
                name,
                request(wire.clone(), &"0".repeat(64), n, transport::ENCODING)
            )
            .await
            .is_err()
        );
        assert!(
            receive_file(
                &s,
                run,
                name,
                request(wire.clone(), &sum, MAX_RAW + 1, transport::ENCODING)
            )
            .await
            .is_err()
        );
        assert!(
            receive_file(
                &s,
                run,
                name,
                request(wire.clone(), &sum, n, "future-version")
            )
            .await
            .is_err()
        );
        assert!(
            receive_file(
                &s,
                run,
                "manifest.json",
                request(wire.clone(), &sum, n, transport::ENCODING)
            )
            .await
            .is_err()
        );
        assert_eq!(std::fs::read_dir(&directory).unwrap().count(), 0);
        let first = receive_file(
            &s,
            run,
            name,
            request(wire.clone(), &sum, n, transport::ENCODING),
        )
        .await
        .unwrap();
        assert_eq!(first["encoding"], transport::ENCODING);
        assert_eq!(first["wire_bytes"], wire.len());
        assert_eq!(std::fs::read(directory.join(name)).unwrap(), bytes);
        let again = receive_file(
            &s,
            run,
            name,
            request(wire.clone(), &sum, n, transport::ENCODING),
        )
        .await
        .unwrap();
        assert_eq!(again["already_saved"], true);
        assert!(
            receive_file(
                &s,
                run,
                name,
                request(
                    wire[..wire.len() - 1].to_vec(),
                    &sum,
                    n,
                    transport::ENCODING
                )
            )
            .await
            .is_err()
        );
        let different = vec![94u8; bytes.len()];
        let different_sum: String = Sha256::digest(&different)
            .iter()
            .map(|b| format!("{b:02x}"))
            .collect();
        assert!(
            receive_file(
                &s,
                run,
                name,
                request(wire, &different_sum, n, transport::ENCODING)
            )
            .await
            .is_err()
        );
        assert_eq!(std::fs::read(directory.join(name)).unwrap(), bytes);
        assert_eq!(std::fs::read_dir(&directory).unwrap().count(), 2);
    }
    #[test]
    fn rejects_paths_and_other_extensions() {
        for name in [
            "../x.ARW",
            "frame-000001.ARW.exe",
            "frame-000001.arw",
            "C:\\x",
            "events.jsonl/../../x",
        ] {
            assert!(!safe_name(name));
        }
        assert!(safe_name("frame-000001.ARW"));
        assert!(safe_name("events.jsonl"));
        assert!(!safe_run("stack-../../x"));
    }
    #[tokio::test]
    async fn checksum_length_idempotence_and_no_overwrite() {
        let temp = tempfile::tempdir().unwrap();
        let config = temp.path().join("receiver.json");
        save_json(
            &config,
            &ReceiverConfig {
                compress_raw: false,
                bind: "127.0.0.1:0".parse().unwrap(),
                lan: "10.0.0.0/24".into(),
                key: "a".repeat(48),
                folder: temp.path().join("images"),
            },
        )
        .unwrap();
        let s = Receiver::open(config).unwrap();
        let run = "stack-test-1";
        let directory = temp.path().join("images").join(run);
        std::fs::create_dir(&directory).unwrap();
        s.runs
            .lock()
            .unwrap()
            .insert(run.into(), RunDestination::Legacy(directory.clone()));
        let data = vec![19u8; 4096];
        let hash: String = Sha256::digest(&data)
            .iter()
            .map(|b| format!("{b:02x}"))
            .collect();
        let request = |bytes: Vec<u8>, sum: &str, len: usize| {
            Request::builder()
                .header("x-content-sha256", sum)
                .header(header::CONTENT_LENGTH, len)
                .body(Body::from(bytes))
                .unwrap()
        };
        assert!(
            receive_file(
                &s,
                run,
                "frame-000001.ARW",
                request(data.clone(), &"0".repeat(64), data.len())
            )
            .await
            .is_err()
        );
        assert!(!directory.join("frame-000001.ARW").exists());
        assert!(
            receive_file(
                &s,
                run,
                "frame-000001.ARW",
                request(data[..100].to_vec(), &hash, data.len())
            )
            .await
            .is_err()
        );
        let good = receive_file(
            &s,
            run,
            "frame-000001.ARW",
            request(data.clone(), &hash, data.len()),
        )
        .await
        .unwrap();
        assert_eq!(good["durable"], true);
        let again = receive_file(
            &s,
            run,
            "frame-000001.ARW",
            request(data.clone(), &hash, data.len()),
        )
        .await
        .unwrap();
        assert_eq!(again["already_saved"], true);
        assert!(
            receive_file(
                &s,
                run,
                "frame-000001.ARW",
                request(data[..100].to_vec(), &hash, data.len())
            )
            .await
            .is_err(),
            "An existing file must not acknowledge an interrupted request body"
        );
        assert!(
            receive_file(
                &s,
                run,
                "frame-000001.ARW",
                request(data.clone(), &"f".repeat(64), data.len())
            )
            .await
            .is_err()
        );
        assert_eq!(
            std::fs::read(directory.join("frame-000001.ARW")).unwrap(),
            data
        );
    }
}
