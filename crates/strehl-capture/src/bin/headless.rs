use anyhow::{Context, Result};
use clap::Parser;
use serde::{Deserialize, Serialize};
use serde_json::json;
use std::{
    net::SocketAddr,
    path::PathBuf,
    sync::{Arc, Mutex},
};
use strehl_capture::{
    lan::Lan,
    power::{PowerConfig, RigPower},
    remote::WebServer,
    schedule,
    session::{Controls, Session},
    transfer::{PcCamera, TransferConfig},
    worker::Worker,
};

#[derive(Parser)]
#[command(about = "Strehl Capture headless LAN service")]
struct Args {
    #[arg(long)]
    config: PathBuf,
    /// Preview/controls simulator only; never opens a camera or transfers a RAW.
    #[arg(long)]
    demo: bool,
}
#[derive(Serialize, Deserialize)]
struct Config {
    bind: SocketAddr,
    pairing_key: String,
    bridge: PathBuf,
    journal_directory: PathBuf,
    transfer: TransferConfig,
    #[serde(default)]
    power: Option<PowerConfig>,
}
fn main() -> Result<()> {
    let args = Args::parse();
    let config: Config = serde_json::from_slice(
        &std::fs::read(&args.config).context("Read headless configuration")?,
    )?;
    let report = Arc::new(Mutex::new(
        json!({"mode":"host-pc","state":"idle","message":"Lossless RAW L → PC · RAM buffer only"}),
    ));
    let worker = if args.demo {
        Worker::new(PathBuf::new(), true)
    } else {
        let bridge = config.bridge;
        let transfer = config.transfer.clone();
        let report = report.clone();
        let power = config
            .power
            .map(|p| RigPower::new(p, Lan::parse(&transfer.lan)?))
            .transpose()?;
        Worker::with_power(
            Box::new(move || {
                Ok(Box::new(PcCamera::connect(
                    &bridge,
                    transfer.clone(),
                    report.clone(),
                )?))
            }),
            power,
        )
    };
    let worker = Arc::new(worker);
    // The lens's ends as found, kept across restarts (2026-11-24).
    worker.keep_lens_travel(config.transfer.state_directory.join("lens-travel.json"));
    let mut session = Session::new(
        worker.clone(),
        Arc::new(Mutex::new(Controls::new(config.journal_directory))),
        args.demo,
    );
    if !args.demo {
        session.transfer = Some(report);
    }
    let default_warmup = worker.power.as_ref().map_or(5, |rig| rig.warmup_seconds());
    let store = schedule::store(
        config.transfer.state_directory.join("studio-schedule.json"),
        default_warmup,
    )?;
    if let Some(rig) = &worker.power {
        rig.set_warmup(store.lock().unwrap().warmup());
    }
    session.schedule = Some(store);
    let session = Arc::new(session);
    let server = WebServer::start_configured(
        session.clone(),
        config.bind,
        Some(config.pairing_key),
        Some(Lan::parse(&config.transfer.lan)?),
    )?;
    schedule::start_clock(&session)?;
    println!(
        "Strehl Capture listening on port {} (local network only).",
        server.port
    );
    println!("Open the saved pairing link; credentials are not written to service logs.");
    // The runtime is used only for shutdown; camera calls remain on their owner thread.
    tokio::runtime::Runtime::new()?.block_on(async { tokio::signal::ctrl_c().await })?;
    worker.request_stop();
    drop(server);
    Ok(())
}
