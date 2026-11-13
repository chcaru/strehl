use anyhow::{Context, Result};
use clap::Parser;
use std::{net::SocketAddr, path::PathBuf};
use strehl_capture::receiver::Receiver;

#[derive(Parser)]
#[command(about = "Strehl Capture LAN RAW receiver")]
struct Args {
    #[arg(long)]
    config: PathBuf,
}
#[tokio::main]
async fn main() -> Result<()> {
    #[cfg(windows)]
    let _awake = Awake::new()?;
    let args = Args::parse();
    let receiver = Receiver::open(args.config)?;
    let address = receiver.bind();
    let listener = tokio::net::TcpListener::bind(address)
        .await
        .context("Open receiver port")?;
    println!(
        "Strehl RAW receiver listening on {address}. Use the saved local setup link to change the capture folder."
    );
    axum::serve(
        listener,
        receiver
            .router()
            .into_make_service_with_connect_info::<SocketAddr>(),
    )
    .with_graceful_shutdown(async {
        let _ = tokio::signal::ctrl_c().await;
    })
    .await?;
    Ok(())
}

// Receiving must not be interrupted by the PC's idle sleep timer. The display
// may still sleep; closing the receiver releases only this process's request.
#[cfg(windows)]
struct Awake;
#[cfg(windows)]
#[link(name = "kernel32")]
unsafe extern "system" {
    fn SetThreadExecutionState(flags: u32) -> u32;
}
#[cfg(windows)]
impl Awake {
    fn new() -> Result<Self> {
        anyhow::ensure!(
            unsafe { SetThreadExecutionState(0x80000001) } != 0,
            "Could not keep the receiver awake"
        );
        Ok(Self)
    }
}
#[cfg(windows)]
impl Drop for Awake {
    fn drop(&mut self) {
        unsafe {
            SetThreadExecutionState(0x80000000);
        }
    }
}
