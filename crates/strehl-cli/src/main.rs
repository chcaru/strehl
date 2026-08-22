//! `strehl` command line.

use std::path::PathBuf;
use std::time::Instant;

use anyhow::{Context, Result};
use clap::{Parser, Subcommand};

#[derive(Parser)]
#[command(name = "strehl", version, about = "Noise-aware RAW focus stacking")]
struct Cli {
    #[command(subcommand)]
    command: Command,
}

#[derive(Subcommand)]
enum Command {
    /// Decode a directory of RAW files and report what was found.
    ///
    /// This exists to make the sensor's real geometry and levels visible before
    /// anything is stacked, and to time decode against the recorded baseline.
    Probe {
        /// Directory containing RAW files.
        dir: PathBuf,
        /// Decode at most this many frames.
        #[arg(short, long)]
        limit: Option<usize>,
    },
}

fn main() -> Result<()> {
    tracing_subscriber::fmt()
        .with_env_filter(
            tracing_subscriber::EnvFilter::try_from_default_env().unwrap_or_else(|_| "info".into()),
        )
        .init();

    match Cli::parse().command {
        Command::Probe { dir, limit } => probe(&dir, limit),
    }
}

fn probe(dir: &PathBuf, limit: Option<usize>) -> Result<()> {
    let mut paths: Vec<PathBuf> = std::fs::read_dir(dir)
        .with_context(|| format!("reading {}", dir.display()))?
        .filter_map(|e| e.ok().map(|e| e.path()))
        .filter(|p| {
            p.extension()
                .and_then(|e| e.to_str())
                .map(|e| matches!(e.to_ascii_lowercase().as_str(), "arw"))
                .unwrap_or(false)
        })
        .collect();
    paths.sort();
    if let Some(n) = limit {
        paths.truncate(n);
    }

    anyhow::ensure!(!paths.is_empty(), "no RAW files found in {}", dir.display());

    let bytes: u64 = paths
        .iter()
        .filter_map(|p| std::fs::metadata(p).ok().map(|m| m.len()))
        .sum();

    let t0 = Instant::now();
    let frames = strehl_raw::decode_all(&paths);
    let elapsed = t0.elapsed().as_secs_f64();

    let (ok, failed): (Vec<_>, Vec<_>) = frames.into_iter().partition(|r| r.is_ok());
    for e in &failed {
        if let Err(e) = e {
            tracing::error!("{e}");
        }
    }
    let ok: Vec<_> = ok.into_iter().map(|r| r.unwrap()).collect();
    anyhow::ensure!(!ok.is_empty(), "every frame failed to decode");

    let f = &ok[0];
    println!("camera          : {}", f.camera);
    println!("buffer          : {} x {}", f.stride, f.buffer_height);
    println!(
        "active area     : {} x {} at ({}, {})  [{:.2} MP]",
        f.active.width,
        f.active.height,
        f.active.x,
        f.active.y,
        f.active.pixels() as f64 / 1e6
    );
    println!(
        "levels          : black {}, white {}",
        f.levels.black, f.levels.white
    );
    println!(
        "allocation      : {:.1} MB/frame, {:.1} MB useful ({:.1}% padding)",
        f.allocated_bytes() as f64 / 1e6,
        f.useful_bytes() as f64 / 1e6,
        100.0 * (1.0 - f.useful_bytes() as f64 / f.allocated_bytes() as f64)
    );
    println!();
    println!("decoded         : {} ok, {} failed", ok.len(), failed.len());
    println!("elapsed         : {elapsed:.3} s");
    println!("per frame       : {:.4} s", elapsed / ok.len() as f64);
    println!("throughput      : {:.1} MB/s", bytes as f64 / 1e6 / elapsed);
    println!(
        "60-frame stack  : {:.2} s",
        60.0 * elapsed / ok.len() as f64
    );

    Ok(())
}
