//! Exact original-u16 load trace; no decoder, aligned volume or quality claim.
use anyhow::{Context, Result, ensure};
use serde_json::{Value, json};
use sha2::{Digest, Sha256};
use std::{collections::{BTreeMap, BTreeSet}, fs::File, io::{BufReader, BufWriter}, path::Path, time::Instant};
use strehl_cli::{session_cache::SourceCache, session_input::{ResolvedSession, SourceIdentity}};
use strehl_core::plane::QuadSource;
fn hex(bytes: &[u8]) -> String { bytes.iter().map(|b| format!("{b:02x}")).collect() }
fn indices(row: &Value) -> Result<Vec<usize>> {
    let mut out = BTreeSet::new();
    for kind in ["sources", "guides"] {
        for i in row[kind].as_array().context("missing source list")? {
            out.insert(i.as_u64().context("invalid source index")? as usize);
        }
    }
    Ok(out.into_iter().collect())
}
fn main() -> Result<()> {
    let args: Vec<_> = std::env::args().skip(1).collect();
    ensure!(args.len() == 6, "cohort-cache-replay MANIFEST IDENTITIES CACHE TRACE OUTPUT CACHE_SOURCE_SLOTS");
    let session = ResolvedSession::load(Path::new(&args[0]))?;
    let ids: Vec<SourceIdentity> = serde_json::from_reader(BufReader::new(File::open(&args[1])?))?;
    ensure!(ids.len() == session.len(), "source census differs");
    let trace_bytes = std::fs::read(&args[3])?;
    let trace: Value = serde_json::from_slice(&trace_bytes)?;
    ensure!(trace["schema"] == "strehl.reconstruction-cohort-trace.v1", "unknown trace");
    let tiles: Vec<_> = trace["tiles"].as_array().context("missing tiles")?.iter().map(indices).collect::<Result<_>>()?;
    ensure!(tiles.iter().flatten().all(|&i| i < ids.len()), "trace outside source census");
    let slots: usize = args[5].parse()?;
    ensure!(slots > 1 && slots <= ids.len() + 1, "invalid cache slots");
    let mut probe = SourceCache::new(Path::new(&args[2]), &session, 256 << 20)?;
    let source = probe.load(&ids[0])?.context("missing original cache")?;
    let geometry = source.geometry();
    let original_bytes = geometry.pixels() * 8;
    drop(source);
    drop(probe);
    let mut cache = SourceCache::new(Path::new(&args[2]), &session, slots * original_bytes)?;
    let started = Instant::now();
    let mut cursor = 0;
    let mut histogram = BTreeMap::<usize, usize>::new();
    let mut digest = Sha256::new();
    let mut load_seconds = 0.;
    while cursor < tiles.len() {
        let begin = cursor;
        let mut union = BTreeSet::<usize>::new();
        while cursor < tiles.len() && cursor - begin < 16 {
            let mut next = union.clone();
            next.extend(tiles[cursor].iter().copied());
            if !union.is_empty() && next.len() > slots - 1 { break; }
            ensure!(next.len() < slots, "single tile exceeds source reservation");
            union = next;
            cursor += 1;
        }
        *histogram.entry(cursor - begin).or_default() += 1;
        let load_started = Instant::now();
        let mut originals = BTreeMap::new();
        for i in union {
            let raw = cache.load(&ids[i])?.context("trace source cache missing")?;
            ensure!(raw.geometry() == geometry && raw.identity == ids[i], "cached original differs");
            originals.insert(i, raw);
        }
        load_seconds += load_started.elapsed().as_secs_f64();
        // Identical source-order observation of raw CFA sites in every arm.
        // Whole payload integrity is checked by the normal cache loader.
        for (t, tile) in tiles.iter().enumerate().take(cursor).skip(begin) {
            digest.update(t.to_le_bytes());
            for &i in tile {
                digest.update(i.to_le_bytes());
                let raw = &originals[&i];
                for row in 0..16 {
                    let y = (row * 173 + t * 7) % geometry.height;
                    let (a, b) = raw.quad_rows(y);
                    for column in 0..16 {
                        let x = (column * 241 + t * 11) % (2 * geometry.width);
                        digest.update(a[x].to_le_bytes());
                        digest.update(b[x].to_le_bytes());
                    }
                }
            }
        }
    }
    let stats = cache.stats();
    ensure!(stats.decodes == 0 && stats.peak_resident_cfa_bytes <= slots * original_bytes, "cache contract failed");
    let report = json!({"schema":"strehl.reconstruction-cohort-cache-replay.v1", "cache_slots":slots,
        "cache_budget_bytes":slots * original_bytes, "source_count":ids.len(), "trace_tiles":tiles.len(),
        "trace_sha256":hex(&Sha256::digest(&trace_bytes)), "observed_originals_sha256":hex(&digest.finalize()),
        "cohort_sizes":histogram, "elapsed_seconds":started.elapsed().as_secs_f64(), "load_seconds":load_seconds,
        "cache":{"peak_resident_cfa_bytes":stats.peak_resident_cfa_bytes,"memory_hits":stats.memory_hits,"disk_hits":stats.disk_hits,"decodes":stats.decodes},
        "scope":"source-cache and cohort preparation only; no reconstruction arithmetic or whole-render timing"});
    serde_json::to_writer_pretty(BufWriter::new(File::options().write(true).create_new(true).open(&args[4])?), &report)?;
    println!("{report}");
    Ok(())
}
