//! Opt-in LAN/private-VPN HTTP remote. No camera/file API is owned by the server.
use crate::session::{CommandRequest, Session};
use anyhow::{Context, Result};
use axum::{
    Json, Router,
    body::Body,
    extract::{ConnectInfo, DefaultBodyLimit, State},
    http::{Request, StatusCode, header},
    middleware::{self, Next},
    response::{IntoResponse, Response},
    routing::{get, post},
};
use serde_json::json;
use std::{
    net::{IpAddr, Ipv4Addr, SocketAddr, TcpListener, UdpSocket},
    path::PathBuf,
    process::{Command, Stdio},
    sync::{
        Arc, Mutex,
        atomic::{AtomicBool, Ordering},
    },
    thread,
    time::Duration,
};

#[derive(Clone)]
pub struct Address {
    pub label: String,
    pub url: String,
}
struct WebState {
    session: Arc<Session>,
    key: String,
    remote_session: String,
    preview: Mutex<Option<(u64, Arc<Vec<u8>>)>>,
    lan: Option<crate::lan::Lan>,
}
pub struct WebServer {
    pub addresses: Vec<Address>,
    pub port: u16,
    pub key: String,
    state: Arc<WebState>,
    stop: Arc<AtomicBool>,
    shutdown: Option<tokio::sync::oneshot::Sender<()>>,
    thread: Option<thread::JoinHandle<()>>,
    preview_thread: Option<thread::JoinHandle<()>>,
}
impl WebServer {
    pub fn start(session: Arc<Session>, bind: SocketAddr) -> Result<Self> {
        Self::start_configured(session, bind, None, None)
    }
    /// A persistent pairing key and a single LAN are used by the Pi appliance.
    pub fn start_configured(
        session: Arc<Session>,
        bind: SocketAddr,
        persistent_key: Option<String>,
        lan: Option<crate::lan::Lan>,
    ) -> Result<Self> {
        let listener = TcpListener::bind(bind)
            .context("Open web remote port; another application may already be using it")?;
        listener.set_nonblocking(true)?;
        let port = listener.local_addr()?.port();
        // Independent public identity distinguishes server replacement from an
        // interrupted request. Neither the key nor its identity has an age TTL.
        let mut random = [0u8; 40];
        getrandom::fill(&mut random).map_err(|e| anyhow::anyhow!("Create pairing key: {e}"))?;
        let key = persistent_key.unwrap_or_else(|| {
            random[..24]
                .iter()
                .map(|b| format!("{b:02x}"))
                .collect::<String>()
        });
        anyhow::ensure!(
            key.len() == 48 && key.bytes().all(|b| b.is_ascii_hexdigit()),
            "Invalid pairing key"
        );
        let addresses = if lan.is_some() {
            vec![Address {
                label: "Local network".into(),
                url: format!("http://strehl.local:{port}/#key={key}"),
            }]
        } else {
            addresses(port, &key, bind.ip().is_loopback())
        };
        let state = Arc::new(WebState {
            session,
            key: key.clone(),
            remote_session: random[24..].iter().map(|b| format!("{b:02x}")).collect(),
            preview: Mutex::new(None),
            lan,
        });
        let router = Router::new()
            .route(
                "/",
                get(|| async {
                    asset(
                        "text/html; charset=utf-8",
                        include_bytes!("../web/index.html"),
                    )
                }),
            )
            .route(
                "/app.js",
                get(|| async {
                    asset(
                        "text/javascript; charset=utf-8",
                        include_bytes!("../web/app.js"),
                    )
                }),
            )
            .route(
                "/style.css",
                get(|| async {
                    asset(
                        "text/css; charset=utf-8",
                        include_bytes!("../web/style.css"),
                    )
                }),
            )
            .route("/api/state", get(state_route))
            .route("/api/preview", get(preview_route))
            .route("/api/command", post(command_route))
            .fallback(|| async { StatusCode::NOT_FOUND })
            .layer(DefaultBodyLimit::max(16 * 1024))
            .layer(middleware::from_fn_with_state(state.clone(), guard))
            .with_state(state.clone());
        let runtime = tokio::runtime::Builder::new_multi_thread()
            .worker_threads(2)
            .enable_all()
            .build()?;
        let (tx, rx) = tokio::sync::oneshot::channel();
        let thread = thread::spawn(move || {
            runtime.block_on(async move{
                if let Ok(listener)=tokio::net::TcpListener::from_std(listener) {
                    tokio::select! {
                        _ = async {let _=axum::serve(listener,router.into_make_service_with_connect_info::<SocketAddr>()).await;} => {},
                        _ = rx => {},
                    }
                }
            });
            runtime.shutdown_timeout(Duration::from_secs(1));
        });
        let stop = Arc::new(AtomicBool::new(false));
        let stopped = stop.clone();
        let shared = state.clone();
        let preview_thread = thread::spawn(move || {
            let mut generation = None;
            while !stopped.load(Ordering::Relaxed) {
                let snapshot = shared.session.worker.snapshot();
                if snapshot.connected
                    && let Some(preview) = snapshot.preview
                {
                    if generation != Some(snapshot.preview_generation) {
                        let jpeg = if let Some(jpeg) = &preview.jpeg {
                            Some(jpeg.clone())
                        } else {
                            let mut bytes = Vec::new();
                            image::codecs::jpeg::JpegEncoder::new_with_quality(&mut bytes, 90)
                                .encode(
                                    preview.rgb.as_raw(),
                                    preview.rgb.width(),
                                    preview.rgb.height(),
                                    image::ExtendedColorType::Rgb8,
                                )
                                .ok()
                                .map(|_| Arc::new(bytes))
                        };
                        if let Some(jpeg) = jpeg {
                            *shared.preview.lock().unwrap() =
                                Some((snapshot.preview_generation, jpeg));
                            generation = Some(snapshot.preview_generation);
                        }
                    }
                } else {
                    *shared.preview.lock().unwrap() = None;
                    generation = None;
                }
                thread::sleep(Duration::from_millis(160));
            }
        });
        Ok(Self {
            addresses,
            port,
            key,
            state,
            stop,
            shutdown: Some(tx),
            thread: Some(thread),
            preview_thread: Some(preview_thread),
        })
    }
    pub fn public_state(&self) -> serde_json::Value {
        self.state.session.state()
    }
    pub fn local_url(&self) -> String {
        format!("http://127.0.0.1:{}/#key={}", self.port, self.key)
    }
}
impl Drop for WebServer {
    fn drop(&mut self) {
        self.stop.store(true, Ordering::Relaxed);
        if let Some(tx) = self.shutdown.take() {
            let _ = tx.send(());
        }
        if let Some(join) = self.thread.take() {
            let _ = join.join();
        }
        if let Some(join) = self.preview_thread.take() {
            let _ = join.join();
        }
    }
}
fn asset(content_type: &'static str, bytes: &'static [u8]) -> Response {
    ([(header::CONTENT_TYPE, content_type)], bytes).into_response()
}
fn problem(status: StatusCode, message: &str) -> Response {
    (status, Json(json!({"error":message}))).into_response()
}
fn private_peer(ip: IpAddr) -> bool {
    match ip {
        IpAddr::V4(ip) => {
            let [a, b, _, _] = ip.octets();
            ip.is_loopback() || ip.is_private() || (a == 100 && (64..=127).contains(&b))
        }
        IpAddr::V6(ip) => ip.is_loopback() || (ip.segments()[0] & 0xfe00) == 0xfc00,
    }
}
fn equal_key(actual: &[u8], expected: &[u8]) -> bool {
    actual.len() == expected.len()
        && actual
            .iter()
            .zip(expected)
            .fold(0u8, |difference, (a, b)| difference | (a ^ b))
            == 0
}
async fn guard(State(state): State<Arc<WebState>>, request: Request<Body>, next: Next) -> Response {
    let peer = request
        .extensions()
        .get::<ConnectInfo<SocketAddr>>()
        .map(|c| c.0.ip());
    let mut response = if !peer.is_some_and(|ip| {
        state
            .lan
            .as_ref()
            .map_or_else(|| private_peer(ip), |lan| lan.permits(ip))
    }) {
        problem(StatusCode::FORBIDDEN, "Use the configured local network")
    } else if request.uri().path().starts_with("/api/") {
        let bearer = request
            .headers()
            .get(header::AUTHORIZATION)
            .and_then(|h| h.to_str().ok())
            .and_then(|h| h.strip_prefix("Bearer "));
        let host = request
            .headers()
            .get(header::HOST)
            .and_then(|h| h.to_str().ok())
            .unwrap_or("");
        let bad_origin = request.headers().get(header::ORIGIN).is_some_and(|h| {
            h.to_str().map_or(true, |origin| {
                origin != format!("http://{host}") && origin != format!("https://{host}")
            })
        }) || request
            .headers()
            .get("sec-fetch-site")
            .is_some_and(|v| v == "cross-site");
        if bad_origin {
            problem(
                StatusCode::FORBIDDEN,
                "Requests must come from this remote page",
            )
        } else if !bearer.is_some_and(|value| equal_key(value.as_bytes(), state.key.as_bytes())) {
            problem(
                StatusCode::UNAUTHORIZED,
                "Pair using the link shown in Strehl Capture",
            )
        } else {
            next.run(request).await
        }
    } else {
        next.run(request).await
    };
    let headers = response.headers_mut();
    headers.insert(
        "x-strehl-remote-session",
        state
            .remote_session
            .parse()
            .expect("hex session identifier"),
    );
    for (name, value) in [
        ("cache-control", "no-store"),
        ("referrer-policy", "no-referrer"),
        ("x-content-type-options", "nosniff"),
        (
            "content-security-policy",
            "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' blob:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'",
        ),
    ] {
        headers.insert(
            axum::http::HeaderName::from_static(name),
            axum::http::HeaderValue::from_static(value),
        );
    }
    response
}
async fn state_route(State(state): State<Arc<WebState>>) -> Json<serde_json::Value> {
    Json(state.session.state())
}
async fn command_route(
    State(state): State<Arc<WebState>>,
    Json(request): Json<CommandRequest>,
) -> Response {
    match state.session.dispatch(request) {
        Ok(()) => Json(json!({"ok":true,"state":state.session.state()})).into_response(),
        Err(error) => problem(StatusCode::CONFLICT, &error.to_string()),
    }
}
async fn preview_route(State(state): State<Arc<WebState>>) -> Response {
    let preview = state.preview.lock().unwrap().clone();
    if let Some((generation, jpeg)) = preview {
        let mut response = (
            [(header::CONTENT_TYPE, "image/jpeg")],
            jpeg.as_ref().clone(),
        )
            .into_response();
        response.headers_mut().insert(
            "x-preview-generation",
            generation.to_string().parse().unwrap(),
        );
        response
    } else {
        StatusCode::NO_CONTENT.into_response()
    }
}

fn addresses(port: u16, key: &str, loopback_only: bool) -> Vec<Address> {
    let mut result = Vec::new();
    if !loopback_only {
        if let Some(ip) = tailscale_ip() {
            result.push(Address {
                label: "Away · Tailscale".into(),
                url: format!("http://{ip}:{port}/#key={key}"),
            });
        }
        if let Ok(socket) = UdpSocket::bind((Ipv4Addr::UNSPECIFIED, 0))
            && socket.connect("192.0.2.1:80").is_ok()
            && let Ok(address) = socket.local_addr()
            && private_peer(address.ip())
            && !address.ip().is_loopback()
        {
            result.push(Address {
                label: "Nearby · local network".into(),
                url: format!("http://{}:{port}/#key={key}", address.ip()),
            });
        }
    }
    result.push(Address {
        label: "This laptop".into(),
        url: format!("http://127.0.0.1:{port}/#key={key}"),
    });
    result
}
fn tailscale_ip() -> Option<Ipv4Addr> {
    let default = std::env::var_os("ProgramFiles")
        .map(PathBuf::from)
        .map(|p| p.join("Tailscale/tailscale.exe"));
    let executable = default
        .filter(|p| p.is_file())
        .unwrap_or_else(|| PathBuf::from("tailscale"));
    let mut command = Command::new(executable);
    command
        .args(["ip", "-4"])
        .stdout(Stdio::piped())
        .stderr(Stdio::null());
    #[cfg(windows)]
    {
        use std::os::windows::process::CommandExt;
        command.creation_flags(0x0800_0000);
    }
    let mut child = command.spawn().ok()?;
    let end = std::time::Instant::now() + Duration::from_secs(3);
    while child.try_wait().ok()?.is_none() {
        if std::time::Instant::now() > end {
            let _ = child.kill();
            let _ = child.wait();
            return None;
        }
        thread::sleep(Duration::from_millis(30));
    }
    let output = child.wait_with_output().ok()?;
    if !output.status.success() {
        return None;
    }
    let ip: Ipv4Addr = std::str::from_utf8(&output.stdout)
        .ok()?
        .trim()
        .parse()
        .ok()?;
    let octets = ip.octets();
    (octets[0] == 100 && (64..=127).contains(&octets[1])).then_some(ip)
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::{session::Controls, worker::Worker};
    use std::io::{Read, Write};
    #[test]
    fn accepts_only_lan_loopback_and_tailnet_peers() {
        for ip in [
            "127.0.0.1",
            "192.168.1.8",
            "10.2.3.4",
            "172.20.0.2",
            "100.100.1.2",
            "::1",
            "fd7a:115c:a1e0::1",
        ] {
            assert!(private_peer(ip.parse().unwrap()));
        }
        for ip in [
            "8.8.8.8",
            "100.63.0.1",
            "100.128.0.1",
            "172.32.0.1",
            "2001:4860::1",
        ] {
            assert!(!private_peer(ip.parse().unwrap()));
        }
        assert!(equal_key(b"123", b"123"));
        assert!(!equal_key(b"123", b"124"));
        assert!(!equal_key(b"123", b"1234"));
    }
    fn request(server: &WebServer, headers: &str, path: &str) -> String {
        let mut stream = std::net::TcpStream::connect((Ipv4Addr::LOCALHOST, server.port)).unwrap();
        stream
            .set_read_timeout(Some(Duration::from_secs(5)))
            .unwrap();
        write!(
            stream,
            "GET {path} HTTP/1.1\r\nHost: 127.0.0.1:{}\r\nConnection: close\r\n{headers}\r\n",
            server.port
        )
        .unwrap();
        let mut reply = String::new();
        stream.read_to_string(&mut reply).unwrap();
        reply
    }
    #[test]
    fn actual_http_requires_pairing_and_same_origin() {
        let temp = tempfile::tempdir().unwrap();
        let session = Arc::new(Session::new(
            Arc::new(Worker::new(PathBuf::new(), true)),
            Arc::new(Mutex::new(Controls::new(temp.path().into()))),
            true,
        ));
        let server = WebServer::start(session.clone(), "127.0.0.1:0".parse().unwrap()).unwrap();
        assert!(request(&server, "", "/api/state").starts_with("HTTP/1.1 401"));
        assert!(
            request(&server, "Authorization: Bearer wrong\r\n", "/api/state")
                .starts_with("HTTP/1.1 401")
        );
        let auth = format!("Authorization: Bearer {}\r\n", server.key);
        assert!(
            request(
                &server,
                &format!("{auth}Origin: https://foreign.invalid\r\n"),
                "/api/state"
            )
            .starts_with("HTTP/1.1 403")
        );
        let reply = request(&server, &auth, "/api/state");
        assert!(reply.starts_with("HTTP/1.1 200"));
        assert!(reply.contains("cache-control: no-store"));
        assert!(!reply.contains(&server.key));
        assert!(!reply.contains("bridge_sha256"));
        let identity = format!("x-strehl-remote-session: {}", server.state.remote_session);
        assert_eq!(server.state.remote_session.len(), 32);
        assert_eq!(server.key.len(), 48);
        assert!(reply.contains(&identity));
        // Rejections and further requests must not rotate an active session.
        assert!(request(&server, "", "/api/state").contains(&identity));
        assert!(request(&server, &auth, "/api/state").contains(&identity));
        assert!(request(&server, &auth, "/../../Cargo.toml").starts_with("HTTP/1.1 404"));
        let old_key = server.key.clone();
        let old_identity = server.state.remote_session.clone();
        drop(server);
        let replacement = WebServer::start(session, "127.0.0.1:0".parse().unwrap()).unwrap();
        assert_ne!(replacement.key, old_key);
        assert_ne!(replacement.state.remote_session, old_identity);
        assert!(request(&replacement, &auth, "/api/state").starts_with("HTTP/1.1 401"));
        let new_auth = format!("Authorization: Bearer {}\r\n", replacement.key);
        assert!(request(&replacement, &new_auth, "/api/state").starts_with("HTTP/1.1 200"));
    }
}
