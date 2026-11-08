#![cfg_attr(all(windows, not(debug_assertions)), windows_subsystem = "windows")]
mod app;
mod offscreen;
mod theme;
use clap::Parser;
use std::path::PathBuf;

#[derive(Parser)]
#[command(about = "Strehl Capture · USB Sony A7C II · RAWs stay on the SD card")]
struct Args {
    #[arg(long)]
    demo: bool,
    #[arg(long)]
    bridge: Option<PathBuf>,
    #[arg(long)]
    journal_dir: Option<PathBuf>,
    /// Render the real UI with simulated camera data; never connects hardware.
    #[arg(long)]
    offscreen_screenshot: Option<PathBuf>,
    #[arg(long, default_value = "1366x900")]
    size: String,
    /// Exercise actual egui controls with a simulator and save screenshots/receipt.
    #[arg(long)]
    exercise: Option<PathBuf>,
    /// HTTP interface when web remote is enabled in the desktop app.
    #[arg(long, default_value = "0.0.0.0:8787")]
    web_bind: std::net::SocketAddr,
    /// Bounded headless browser test; requires --demo and publishes a local test key.
    #[arg(long)]
    web_test_session: Option<PathBuf>,
    #[arg(long, default_value_t = 240)]
    web_test_seconds: u64,
}
fn main() {
    if let Err(e) = run() {
        eprintln!("{e:#}");
        std::process::exit(1);
    }
}
fn run() -> anyhow::Result<()> {
    let args = Args::parse();
    let exe = std::env::current_exe()?;
    let bridge = args
        .bridge
        .unwrap_or_else(|| exe.parent().unwrap().join("camera/strehl-sony-control.exe"));
    let root = args.journal_dir.unwrap_or_else(|| {
        std::env::var_os("LOCALAPPDATA")
            .map(PathBuf::from)
            .or_else(|| std::env::var_os("HOME").map(PathBuf::from))
            .unwrap_or_else(|| exe.parent().unwrap().to_owned())
            .join("Strehl/Capture")
    });
    if args.offscreen_screenshot.is_some() || args.exercise.is_some() {
        anyhow::ensure!(
            args.demo,
            "Offscreen checks require explicit --demo and never open a camera"
        );
    }
    let worker = strehl_capture::worker::Worker::new(bridge, args.demo);
    if let Some(path) = args.web_test_session {
        use std::sync::{Arc, Mutex};
        use strehl_capture::{
            remote::WebServer,
            session::{Controls, Session},
        };
        anyhow::ensure!(args.demo, "Headless browser tests require --demo");
        anyhow::ensure!(!path.exists(), "Choose a fresh test session file");
        anyhow::ensure!(
            (1..=600).contains(&args.web_test_seconds),
            "Test lifetime must be 1–600 seconds"
        );
        let session = Arc::new(Session::new(
            Arc::new(worker),
            Arc::new(Mutex::new(Controls::new(root))),
            true,
        ));
        let server = WebServer::start(session, "127.0.0.1:0".parse()?)?;
        std::fs::write(
            &path,
            serde_json::to_vec(
                &serde_json::json!({"pid":std::process::id(),"url":server.local_url(),"key":server.key,"port":server.port,"demo":true}),
            )?,
        )?;
        std::thread::sleep(std::time::Duration::from_secs(args.web_test_seconds));
        std::fs::remove_file(path)?;
        return Ok(());
    }
    let mut app = app::App::new(worker, root, args.demo);
    app.web_bind = args.web_bind;
    if let Some(dir) = args.exercise {
        return offscreen::exercise(app, &dir);
    }
    if let Some(path) = args.offscreen_screenshot {
        let (w, h) = args
            .size
            .split_once('x')
            .ok_or_else(|| anyhow::anyhow!("Use WIDTHxHEIGHT"))?;
        return offscreen::screenshot(app, &path, [w.parse()?, h.parse()?]);
    }
    let options = eframe::NativeOptions {
        viewport: eframe::egui::ViewportBuilder::default()
            .with_inner_size([1366.0, 900.0])
            .with_min_inner_size([960.0, 640.0]),
        ..Default::default()
    };
    eframe::run_native(
        "Strehl Capture",
        options,
        Box::new(move |cc| {
            theme::install(&cc.egui_ctx);
            Ok(Box::new(app))
        }),
    )
    .map_err(|e| anyhow::anyhow!("Open capture workspace: {e}"))
}
