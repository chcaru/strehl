//! Shared runtime for the standalone receiver and Strehl's background mode.
use crate::receiver::Receiver;
use anyhow::{Context, Result};
use std::{net::SocketAddr, path::PathBuf};

pub fn run(config: PathBuf) -> Result<()> {
    #[cfg(windows)]
    let _awake = Awake::new()?;
    tokio::runtime::Builder::new_multi_thread()
        .worker_threads(2)
        .enable_all()
        .build()?
        .block_on(async {
            let receiver = Receiver::open(config)?;
            let listener = tokio::net::TcpListener::bind(receiver.bind())
                .await
                .context("Open receiver port")?;
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
        })
}

// This request belongs to the receiver process, not the editing window.
// The display may sleep. Exiting releases only this process's request.
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
