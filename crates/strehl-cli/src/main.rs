//! Standalone entry point for the shared Strehl engine.

fn main() -> anyhow::Result<()> {
    // SAFETY: this is the process entry point; no threads or GUI have started.
    unsafe { strehl_cli::run_from(std::env::args_os()) }
}
