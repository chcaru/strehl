//! Replay an existing file through the production sender. Never opens a camera.
use anyhow::Result;
use clap::Parser;
use serde_json::json;
use std::{
    path::PathBuf,
    sync::{Arc, Mutex},
    time::Instant,
};
use strehl_capture::transfer::{Sink, TransferConfig};

#[derive(Parser)]
struct Args {
    /// Private TransferConfig JSON; never pass credentials on the command line.
    #[arg(long)]
    config: PathBuf,
    #[arg(long)]
    file: PathBuf,
    #[arg(long)]
    run: String,
    #[arg(long, default_value = "frame-000001.ARW")]
    name: String,
    /// Identity control using the same sender/receiver and durable-write path.
    #[arg(long)]
    identity: bool,
}
fn main() -> Result<()> {
    let args = Args::parse();
    let mut config: TransferConfig = serde_json::from_slice(&std::fs::read(args.config)?)?;
    config.transport_compression = !args.identity;
    let sink = Sink::new(config, Arc::new(Mutex::new(json!({}))))?;
    let start = Instant::now();
    let receipt = sink.send_file(&args.run, &args.name, &args.file)?;
    println!(
        "{}",
        json!({"receipt":receipt,"total_seconds":start.elapsed().as_secs_f64(),"source_retained":args.file.exists()})
    );
    Ok(())
}
