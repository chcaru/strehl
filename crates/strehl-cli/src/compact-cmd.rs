//! `strehl compact`: store a finished capture in the calibrated format.
//!
//! An explicit, owner-asked action on a finished stack, never automatic and
//! never during a capture. NOT lossless: every CFA sample is kept to within
//! half a step of `k` noise sigma and the camera's full-size embedded JPEG is
//! dropped (`strehl_raw_codec::calibrated` has the format and the evidence).
//! The capture's journal and receipts are untouched: each compacted file
//! records the SHA-256 of the original it replaced, the binding they hold.
//!
//! Without `--apply` nothing is written: a few planes are compacted in memory
//! and the saving for the whole run is estimated from them. With `--apply`
//! every file is compacted, written beside itself, read back and checked, and
//! only then put in its original's place. A run interrupted part way is safe
//! to compact again: files already compacted are checked and kept.

use anyhow::{Context, Result, bail, ensure};
use rayon::prelude::*;
use serde_json::{Value, json};
use std::io::Write;
use std::path::{Path, PathBuf};
use strehl_raw::codec::{archive, calibrated};

use crate::pixel_shift_cmd::all_groups;

#[derive(clap::Args, Debug)]
pub struct CompactArgs {
    /// Capture run folder.
    pub dir: PathBuf,
    /// Step of the quantiser in noise sigma. 1 keeps every sample within half
    /// a sigma of its value.
    #[arg(long, default_value_t = 1.0)]
    pub k: f64,
    /// Replace the run's files. Without it nothing is written: a few planes
    /// are compacted in memory to estimate the saving.
    #[arg(long)]
    pub apply: bool,
    /// Planes compacted in memory for the estimate.
    #[arg(long, default_value_t = 4)]
    pub sample: usize,
    /// Write the result as JSON here.
    #[arg(long)]
    pub json: Option<PathBuf>,
}

/// One bound file of the run.
struct Target {
    name: String,
    path: PathBuf,
    sha256: String,
}

fn targets(dir: &Path) -> Result<Vec<Target>> {
    let mut out: Vec<Target> = Vec::new();
    for g in all_groups(dir)? {
        for f in g.files {
            if f.durable && !out.iter().any(|t| t.name == f.name) {
                out.push(Target {
                    name: f.name,
                    path: f.path,
                    sha256: f.sha256,
                });
            }
        }
    }
    ensure!(!out.is_empty(), "{} has no saved RAWs", dir.display());
    Ok(out)
}

/// The table for this run: the camera profile's noise model at the run's
/// ISO and levels. A camera without a profile is refused: its table would
/// rest on a guess.
fn table(first: &Path, k: f64) -> Result<calibrated::Table> {
    let frame = strehl_raw::decode(first).with_context(|| first.display().to_string())?;
    let noise = strehl_core::profile::noise_model_for(&frame.camera, frame.iso, frame.levels);
    ensure!(
        noise.provenance == strehl_core::noise::Provenance::Profile,
        "No noise profile for {} at this ISO; a calibrated copy would rest on a guess",
        frame.camera
    );
    let p = noise.plane(strehl_core::CfaPlane::G1);
    calibrated::Table::new(
        k,
        calibrated::Noise {
            gain: f64::from(p.gain_dn_per_e),
            read: f64::from(p.read_floor_dn()),
            black: f64::from(p.levels.black),
        },
    )
}

/// The original bytes of a stored RAW, or `None` when it is already compacted
/// (then its recorded original must be this binding's).
fn original(t: &Target) -> Result<Option<Vec<u8>>> {
    if archive::is_archive(&t.path) {
        let header = archive::read_header(std::fs::File::open(&t.path)?)?;
        if header.format == 3 {
            let mut head = vec![0u8; 128];
            std::io::Read::read_exact(&mut std::fs::File::open(&t.path)?, &mut head)?;
            head.resize(calibrated::head_len(&head)?, 0);
            std::io::Read::read_exact(&mut std::fs::File::open(&t.path)?, &mut head)?;
            let h = calibrated::parse_head(&head)?;
            ensure!(
                h.original_sha256 == t.sha256,
                "{} was compacted from a different RAW than the journal records",
                t.name
            );
            return Ok(None);
        }
        return archive::read_original(&t.path).map(Some);
    }
    Ok(Some(std::fs::read(&t.path)?))
}

fn file_size(path: &Path) -> u64 {
    std::fs::metadata(path).map(|m| m.len()).unwrap_or(0)
}

/// Compact one file in place: write beside, read back, check, replace.
fn compact_one(t: &Target, table: &calibrated::Table) -> Result<Value> {
    let before = file_size(&t.path);
    let Some(bytes) = original(t)? else {
        return Ok(json!({"name":t.name,"already":true,"after_bytes":before}));
    };
    let (archive_bytes, restored_sha, dropped) =
        calibrated::encode(&bytes, &t.sha256, table).with_context(|| t.name.clone())?;
    drop(bytes);
    let destination = if archive::is_archive(&t.path) {
        t.path.clone()
    } else {
        PathBuf::from(format!("{}.{}", t.path.display(), archive::EXTENSION))
    };
    let temp = PathBuf::from(format!("{}.compacting", destination.display()));
    {
        let mut f = std::fs::File::create(&temp)?;
        f.write_all(&archive_bytes)?;
        f.sync_all()?;
    }
    let check = archive::verify(&temp);
    match check {
        Ok(d) if d.sha256 == restored_sha => {}
        Ok(_) | Err(_) => {
            let _ = std::fs::remove_file(&temp);
            bail!(
                "{}: the written file did not read back; the original was kept",
                t.name
            );
        }
    }
    std::fs::rename(&temp, &destination)?;
    if destination != t.path {
        std::fs::remove_file(&t.path)?;
    }
    strehl_raw::trust::record_verified(&destination, &restored_sha);
    Ok(
        json!({"name":t.name,"original_sha256":t.sha256,"restored_sha256":restored_sha,
        "before_bytes":before,"after_bytes":archive_bytes.len(),"jpeg_dropped_bytes":dropped}),
    )
}

pub fn run(args: &CompactArgs) -> Result<()> {
    ensure!(
        (0.25..=2.0).contains(&args.k),
        "Choose k between 0.25 and 2"
    );
    let dir = &args.dir;
    ensure!(
        dir.join("result.json").is_file(),
        "{} has no result.json: compact only a finished capture",
        dir.display()
    );
    let targets = targets(dir)?;
    let table = table(&targets[0].path, args.k)?;
    let before: u64 = targets.iter().map(|t| file_size(&t.path)).sum();
    println!("run             : {}", dir.display());
    println!(
        "files           : {} RAWs, {:.2} GB now",
        targets.len(),
        before as f64 / 1e9
    );
    println!(
        "calibration     : k = {} (each sample within {:.2} sigma), {} codes; adds {:.1} % to the noise variance (gain {:.4} DN/e-, read {:.3} DN, black {:.0})",
        args.k,
        args.k / 2.0,
        table.values.len(),
        100.0 * table.added_variance,
        table.noise.gain,
        table.noise.read,
        table.noise.black
    );
    // At most eight files in memory at once.
    let pool = rayon::ThreadPoolBuilder::new()
        .num_threads(8.min(rayon::current_num_threads()))
        .build()?;
    let mut report = json!({"schema":"strehl-compaction-v1","run":dir,"k":args.k,
        "noise":{"gain":table.noise.gain,"read":table.noise.read,"black":table.noise.black},
        "added_variance":table.added_variance,"before_bytes":before});
    if !args.apply {
        let n = args.sample.clamp(1, targets.len());
        let picks: Vec<&Target> = (0..n)
            .map(|i| &targets[i * (targets.len() - 1) / (n - 1).max(1)])
            .collect();
        let sizes: Vec<(u64, u64)> = pool.install(|| {
            picks
                .par_iter()
                .map(|t| -> Result<(u64, u64)> {
                    let now = file_size(&t.path);
                    Ok(match original(t)? {
                        None => (now, now),
                        Some(bytes) => {
                            let (a, _, _) = calibrated::encode(&bytes, &t.sha256, &table)
                                .with_context(|| t.name.clone())?;
                            (now, a.len() as u64)
                        }
                    })
                })
                .collect::<Result<_>>()
        })?;
        let ratio = sizes.iter().map(|s| s.1).sum::<u64>() as f64
            / sizes.iter().map(|s| s.0).sum::<u64>().max(1) as f64;
        let after = (before as f64 * ratio) as u64;
        println!(
            "estimate        : {:.2} GB after ({:.0} % of now), {:.2} GB freed, from {} files compacted in memory; nothing was written",
            after as f64 / 1e9,
            100.0 * ratio,
            (before - after) as f64 / 1e9,
            sizes.len()
        );
        report["estimated_after_bytes"] = json!(after);
        report["applied"] = json!(false);
    } else {
        let results: Vec<Result<Value>> =
            pool.install(|| targets.par_iter().map(|t| compact_one(t, &table)).collect());
        let mut files = Vec::new();
        let mut failures = Vec::new();
        for r in results {
            match r {
                Ok(v) => files.push(v),
                Err(e) => failures.push(format!("{e:#}")),
            }
        }
        let after: u64 = targets
            .iter()
            .map(|t| {
                let straw = PathBuf::from(format!("{}.{}", t.path.display(), archive::EXTENSION));
                file_size(&t.path).max(file_size(&straw))
            })
            .sum();
        println!(
            "compacted       : {} files ({} already were), {:.2} GB now, {:.2} GB freed",
            files.len(),
            files.iter().filter(|f| f["already"] == true).count(),
            after as f64 / 1e9,
            before.saturating_sub(after) as f64 / 1e9
        );
        report["after_bytes"] = json!(after);
        report["applied"] = json!(true);
        report["files"] = json!(files);
        report["failures"] = json!(failures);
        report["unix_ms"] = json!(
            std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .map(|d| d.as_millis() as u64)
                .unwrap_or(0)
        );
        std::fs::write(
            dir.join("compaction.json"),
            serde_json::to_vec_pretty(&report)?,
        )?;
        if !failures.is_empty() {
            bail!(
                "{} files were not compacted (their originals are kept): {}",
                failures.len(),
                failures.join("; ")
            );
        }
    }
    if let Some(path) = &args.json {
        std::fs::write(path, serde_json::to_vec_pretty(&report)?)?;
    }
    Ok(())
}
