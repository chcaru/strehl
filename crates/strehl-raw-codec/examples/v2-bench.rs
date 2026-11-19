//! Archive format 2 against format 1 on real archives (plan stage Q19's gate:
//! at least 4 % smaller and 2.5 times cheaper to decode per core).
//!
//! usage: v2-bench <format-1 capture dir> <scratch dir> [every Nth file, default 50]
//!
//! Writes each sampled file's format-2 archive into the scratch directory,
//! checks it restores the original exactly, and times one-thread decodes of
//! both formats (the serial route the engine's decoder threads use), with
//! the whole-file SHA-256 skipped (a trusted file) and checked, best of five
//! with the files in the OS cache.
use std::{path::PathBuf, time::Instant};
use strehl_raw_codec::{archive, cfa, v2};

fn best(mut f: impl FnMut()) -> f64 {
    (0..5)
        .map(|_| {
            let t = Instant::now();
            f();
            t.elapsed().as_secs_f64()
        })
        .fold(f64::INFINITY, f64::min)
}

fn main() {
    let args: Vec<String> = std::env::args().collect();
    let dir = PathBuf::from(&args[1]);
    let scratch = PathBuf::from(&args[2]);
    let every: usize = args.get(3).map_or(50, |s| s.parse().unwrap());
    std::fs::create_dir_all(&scratch).unwrap();
    let mut files: Vec<PathBuf> = std::fs::read_dir(&dir)
        .unwrap()
        .map(|e| e.unwrap().path())
        .filter(|p| archive::is_archive(p))
        .collect();
    files.sort();
    let one = rayon::ThreadPoolBuilder::new()
        .num_threads(1)
        .build()
        .unwrap();
    let (mut s1, mut s2, mut n) = (0u64, 0u64, 0usize);
    let (mut t1, mut t2, mut h1, mut h2, mut enc1, mut samples) = (0.0, 0.0, 0.0, 0.0, 0.0, 0u64);
    println!(
        "file | original MB | format 1 MB | format 2 MB | ratio | decode ms f1 / f2 (trusted) | f1 / f2 (hashed) | encode ms (1 thread)"
    );
    for path in files.iter().step_by(every.max(1)) {
        let original = archive::read_original(path).unwrap();
        let header = archive::read_header(std::fs::File::open(path).unwrap()).unwrap();
        assert_eq!(header.format, 1, "{} is not format 1", path.display());
        let t = Instant::now();
        let encoded = one
            .install(|| v2::encode(&original, &header.sha256))
            .unwrap()
            .expect("plain CFA strip");
        let e = t.elapsed().as_secs_f64();
        if n == 0 {
            let index = v2::parse(
                &encoded[..v2::head_len(&encoded).unwrap()],
                encoded.len() as u64,
            )
            .unwrap();
            let meta: usize = index
                .entries
                .iter()
                .filter(|e| !e.samples())
                .map(|e| e.stored)
                .sum();
            let meta_raw: usize = index
                .entries
                .iter()
                .filter(|e| !e.samples())
                .map(|e| e.len)
                .sum();
            println!(
                "{}x{} strip at {}; metadata {} bytes stored as {} in {} chunks; {} sample chunks",
                index.width,
                index.height,
                index.strip_offset,
                meta_raw,
                meta,
                index.entries.iter().filter(|e| !e.samples()).count(),
                index.entries.iter().filter(|e| e.samples()).count()
            );
        }
        let out = scratch.join(path.file_name().unwrap());
        std::fs::write(&out, &encoded).unwrap();
        assert_eq!(archive::read_original(&out).unwrap(), original);
        let f1 = std::fs::metadata(path).unwrap().len();
        let f2 = encoded.len() as u64;
        let sha = header.sha256.clone();
        let mut buf = None;
        let mut run = |p: &PathBuf, trusted: Option<&str>| {
            let c = cfa::decode_archive_trusting(p, buf.take(), true, trusted)
                .unwrap()
                .unwrap();
            assert_eq!(c.verified_sha256, trusted.is_none());
            buf = Some(c.samples);
        };
        let (a, b) = one.install(|| {
            (
                best(|| run(path, Some(&sha))),
                best(|| run(&out, Some(&sha))),
            )
        });
        let (c, d) = one.install(|| (best(|| run(path, None)), best(|| run(&out, None))));
        let first = cfa::decode_archive(path, None).unwrap().unwrap();
        let second = cfa::decode_archive(&out, None).unwrap().unwrap();
        assert_eq!(first.samples, second.samples);
        samples += first.samples.len() as u64;
        println!(
            "{} | {:.1} | {:.2} | {:.2} | {:.4} | {:.1} / {:.1} | {:.1} / {:.1} | {:.0}",
            path.file_name().unwrap().to_string_lossy(),
            original.len() as f64 / 1e6,
            f1 as f64 / 1e6,
            f2 as f64 / 1e6,
            f2 as f64 / f1 as f64,
            a * 1e3,
            b * 1e3,
            c * 1e3,
            d * 1e3,
            e * 1e3
        );
        s1 += f1;
        s2 += f2;
        t1 += a;
        t2 += b;
        h1 += c;
        h2 += d;
        enc1 += e;
        n += 1;
        std::fs::remove_file(&out).unwrap();
    }
    let nf = n as f64;
    println!(
        "{n} files, {:.1} M samples each: format 2 / format 1 size {:.4} ({:.2} % smaller); bits per sample {:.3} / {:.3}",
        samples as f64 / nf / 1e6,
        s2 as f64 / s1 as f64,
        100.0 * (1.0 - s2 as f64 / s1 as f64),
        s1 as f64 * 8.0 / samples as f64,
        s2 as f64 * 8.0 / samples as f64
    );
    println!(
        "one-thread decode per file: trusted {:.1} -> {:.1} ms ({:.2}x); hashed {:.1} -> {:.1} ms ({:.2}x); encode {:.0} ms",
        t1 / nf * 1e3,
        t2 / nf * 1e3,
        t1 / t2,
        h1 / nf * 1e3,
        h2 / nf * 1e3,
        h1 / h2,
        enc1 / nf * 1e3
    );
}
