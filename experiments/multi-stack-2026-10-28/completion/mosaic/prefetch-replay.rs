//! Root-scheduled cold/warm preparation benchmark through the production helper.
//! It produces verified cache entries and a receipt, never an aligned image.
use anyhow::{Context, Result, ensure};
use serde_json::json;
use sha2::{Digest, Sha256};
use std::{
    fs::File,
    io::{BufReader, BufWriter, Read},
    path::{Path, PathBuf},
};
use strehl_cli::{session_cache, session_input};
#[path = "../../../../crates/strehl-cli/src/session-mosaic-source-prefetch.rs"]
mod prefetch;
fn hash(path: &Path) -> Result<String> {
    let mut input = BufReader::new(File::open(path)?);
    let mut hash = Sha256::new();
    let mut block = [0_u8; 65536];
    loop {
        let n = input.read(&mut block)?;
        if n == 0 {
            break;
        }
        hash.update(&block[..n]);
    }
    Ok(hash.finalize().iter().map(|b| format!("{b:02x}")).collect())
}
fn main() -> Result<()> {
    let args: Vec<_> = std::env::args().skip(1).collect();
    ensure!(
        args.len() == 4,
        "prefetch-replay MANIFEST CACHE OUTPUT_JSON WORKERS"
    );
    let session = session_input::ResolvedSession::load(Path::new(&args[0]))?;
    let ids = session.hash_sources(true)?;
    let metadata = session.read_metadata()?;
    let root = PathBuf::from(&args[1]);
    let workers = args[3].parse()?;
    let report = prefetch::prepare(&session, &ids, &metadata, &root, 4 << 30, workers)?;
    let mut verifier = session_cache::SourceCache::new(
        &root,
        &session,
        report.plan.resident_cfa_bytes_per_worker,
    )?;
    let mut files = Vec::new();
    for id in &ids {
        let original = verifier
            .load(id)?
            .context("prefetch left missing source cache")?;
        ensure!(original.identity == *id, "verified cache identity differs");
        drop(original);
        let path = verifier.cache_path(id)?;
        files.push(json!({"cache_file":path.file_name().unwrap().to_string_lossy(),"sha256":hash(&path)?,"source":id}));
    }
    serde_json::to_writer_pretty(
        BufWriter::new(
            File::options()
                .write(true)
                .create_new(true)
                .open(&args[2])?,
        ),
        &json!({"schema":"strehl.mosaic-prefetch-measurement.v1","memory_limit_bytes":4_u64<<30,"workers_requested":workers,"production_helper_sha256":hash(Path::new("crates/strehl-cli/src/session-mosaic-source-prefetch.rs"))?,"prefetch":report,"all_entries_passed_normal_cache_verification":true,"verified_cache_files":files}),
    )?;
    Ok(())
}
