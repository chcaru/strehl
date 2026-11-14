use anyhow::Result;
use clap::Parser;
use std::path::PathBuf;

#[derive(Parser)]
#[command(about = "Strehl Capture LAN RAW receiver")]
struct Args {
    #[arg(long)]
    config: PathBuf,
}
fn main() -> Result<()> {
    strehl_capture::receiver_service::run(Args::parse().config)
}
