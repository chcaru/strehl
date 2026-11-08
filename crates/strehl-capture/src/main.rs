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
    let app = app::App::new(worker, root, args.demo);
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
