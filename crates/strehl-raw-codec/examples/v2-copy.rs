//! A copy of a capture folder with every archive stored in format 2, for
//! testing the readers on a real capture. Never writes the source: the
//! destination must not exist. Each archive is restored (its SHA-256
//! checked), stored again with `archive::store` (which decodes what it made
//! before returning it) and written beside copies of every other file; the
//! transfer receipts are rewritten for the new files, as the receiver would
//! have written them.
//!
//! usage: v2-copy <capture dir> <new dir>
use rayon::prelude::*;
use std::path::{Path, PathBuf};
use strehl_raw_codec::archive;

fn main() {
    let args: Vec<String> = std::env::args().collect();
    let (src, dest) = (PathBuf::from(&args[1]), PathBuf::from(&args[2]));
    assert!(!dest.exists(), "{} exists", dest.display());
    std::fs::create_dir_all(&dest).unwrap();
    let files: Vec<PathBuf> = std::fs::read_dir(&src)
        .unwrap()
        .map(|e| e.unwrap().path())
        .filter(|p| p.is_file())
        .collect();
    let started = std::time::Instant::now();
    let sizes: Vec<(String, u64, u64)> = files
        .par_iter()
        .filter(|p| p.file_name().unwrap() != "transfer-receipts.jsonl")
        .map(|p| {
            let name = p.file_name().unwrap().to_string_lossy().into_owned();
            let out = dest.join(&name);
            if archive::is_archive(p) {
                let header = archive::read_header(std::fs::File::open(p).unwrap()).unwrap();
                let original = archive::read_original(p).unwrap();
                let (stored, format) = archive::store(&original, &header.sha256, 2).unwrap();
                assert_eq!(format, 2, "{name} is not a plain CFA strip");
                std::fs::write(&out, &stored).unwrap();
                (
                    name,
                    std::fs::metadata(p).unwrap().len(),
                    stored.len() as u64,
                )
            } else {
                std::fs::copy(p, &out).unwrap();
                let n = std::fs::metadata(p).unwrap().len();
                (name, n, n)
            }
        })
        .collect();
    let receipts = src.join("transfer-receipts.jsonl");
    if receipts.exists() {
        let now = std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .unwrap()
            .as_millis() as u64
            + 1000;
        let mut lines = Vec::new();
        for line in std::fs::read_to_string(&receipts).unwrap().lines() {
            let mut v: serde_json::Value = serde_json::from_str(line).unwrap();
            let name = Path::new(&v["path"].as_str().unwrap().replace('\\', "/"))
                .file_name()
                .unwrap()
                .to_string_lossy()
                .into_owned();
            let out = dest.join(&name);
            v["path"] = out.to_string_lossy().into();
            if archive::is_archive(&out) {
                v["storage_encoding"] = archive::ENCODING_V2.into();
                v["storage_bytes"] = std::fs::metadata(&out).unwrap().len().into();
                v["saved_unix_ms"] = now.into();
            }
            lines.push(v.to_string());
        }
        std::fs::write(
            dest.join("transfer-receipts.jsonl"),
            lines.join("\n") + "\n",
        )
        .unwrap();
    }
    let (a, b): (u64, u64) = sizes
        .iter()
        .filter(|(n, ..)| n.ends_with(".straw"))
        .fold((0, 0), |(a, b), (_, x, y)| (a + x, b + y));
    println!(
        "{} archives: format 1 {:.2} GB -> format 2 {:.2} GB ({:.2} % smaller), {:.0} s",
        sizes.iter().filter(|(n, ..)| n.ends_with(".straw")).count(),
        a as f64 / 1e9,
        b as f64 / 1e9,
        100.0 * (1.0 - b as f64 / a as f64),
        started.elapsed().as_secs_f64()
    );
}
