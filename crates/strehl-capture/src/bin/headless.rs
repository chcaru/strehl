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
    remote::WebServer,
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
        Worker::with_factory(Box::new(move || {
            Ok(Box::new(PcCamera::connect(
                &bridge,
                transfer.clone(),
                report.clone(),
            )?))
        }))
    };
    let worker = Arc::new(worker);
    let mut session = Session::new(
        worker.clone(),
        Arc::new(Mutex::new(Controls::new(config.journal_directory))),
        args.demo,
    );
    if !args.demo {
        session.transfer = Some(report);
    }
    let server = WebServer::start_configured(
        Arc::new(session),
        config.bind,
        Some(config.pairing_key),
        Some(Lan::parse(&config.transfer.lan)?),
    )?;
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
