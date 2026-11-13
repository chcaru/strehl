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
    io::{Read, Write},
    net::SocketAddr,
    path::{Path, PathBuf},
    sync::{Arc, Mutex},
};
use tokio_util::io::{StreamReader, SyncIoBridge};

pub use crate::transport::MAX_RAW;
#[derive(Clone, Serialize, Deserialize)]
pub struct ReceiverConfig {
    pub bind: SocketAddr,
    pub lan: String,
    pub key: String,
    pub folder: PathBuf,
}
pub struct Receiver {
    config: Mutex<ReceiverConfig>,
    config_path: PathBuf,
    lan: Lan,
    runs: Mutex<BTreeMap<String, PathBuf>>,
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
            .route("/api/runs/{run}", post(create_run))
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
    match fs2::available_space(&c.folder) {
        Ok(free)=>Json(json!({"ok":true,"protocol":1,"raw_encodings":["identity",transport::ENCODING],"folder":c.folder,"free_bytes":free,"max_raw_bytes":MAX_RAW,"latest":*s.latest.lock().unwrap()})).into_response(),
        Err(e)=>problem(StatusCode::SERVICE_UNAVAILABLE,e)
    }
}
async fn folder(
    State(s): State<Arc<Receiver>>,
    ConnectInfo(peer): ConnectInfo<SocketAddr>,
    Json(data): Json<Value>,
) -> Response {
    if !peer.ip().is_loopback() {
        return problem(
            StatusCode::FORBIDDEN,
            "Change the capture folder on this PC",
        );
    }
    let result = (|| -> Result<()> {
        let p = PathBuf::from(data["folder"].as_str().context("Missing folder")?);
        ensure!(p.is_absolute(), "Use an absolute folder path");
        std::fs::create_dir_all(&p)?;
        let probe = tempfile::NamedTempFile::new_in(&p)?;
        probe.as_file().sync_all()?;
        let mut c = s.config.lock().unwrap();
        let mut next = c.clone();
        next.folder = p.canonicalize()?;
        save_json(&s.config_path, &next)?;
        *c = next;
        Ok(())
    })();
    match result{Ok(())=>Json(json!({"ok":true,"message":"Folder updated for new stacks; active stacks retain their folder"})).into_response(),Err(e)=>problem(StatusCode::BAD_REQUEST,e)}
}
async fn create_run(State(s): State<Arc<Receiver>>, UrlPath(run): UrlPath<String>) -> Response {
    let result = (|| -> Result<PathBuf> {
        ensure!(safe_run(&run), "Invalid stack identifier");
        let mut runs = s.runs.lock().unwrap();
        if let Some(p) = runs.get(&run) {
            ensure!(p.is_dir(), "Stack folder is missing");
            return Ok(p.clone());
        }
        let root = s.config.lock().unwrap().folder.clone();
        let p = root.join(&run);
        std::fs::create_dir(&p)
            .context("Create a new stack folder; refusing to reuse an unregistered directory")?;
        runs.insert(run, p.clone());
        save_json(&s.config_path.with_extension("runs.json"), &*runs)?;
        Ok(p)
    })();
    match result {
        Ok(p) => Json(json!({"ok":true,"folder":p})).into_response(),
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
    let directory = s
        .runs
        .lock()
        .unwrap()
        .get(run)
        .cloned()
        .context("Register the stack before uploading")?;
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
    let destination = directory.join(name);
    let duplicate = destination.exists()
        && std::fs::metadata(&destination)?.len() == length
        && hash_file(&destination)? == expected;
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
            transport::decode(reader, file.as_file_mut(), length, compressed)?
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
    if duplicate {
        return Ok(
            json!({"ok":true,"durable":true,"sha256":expected,"bytes":length,"path":destination,
            "already_saved":true,"encoding":encoding,"wire_bytes":decoded.wire_bytes,"chunks":decoded.chunks}),
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
        "encoding":encoding,"wire_bytes":decoded.wire_bytes,"chunks":decoded.chunks});
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
    async fn compressed_partials_corruption_retries_and_metadata_bounds() {
        let temp = tempfile::tempdir().unwrap();
        let config = temp.path().join("receiver.json");
        save_json(
            &config,
            &ReceiverConfig {
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
        s.runs.lock().unwrap().insert(run.into(), directory.clone());
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
        s.runs.lock().unwrap().insert(run.into(), directory.clone());
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
