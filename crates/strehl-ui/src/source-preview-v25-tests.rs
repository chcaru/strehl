use super::*;

#[path = "source-preview-v25-image-tests.rs"]
mod image_tests;

/// Actual browser entry point, on the explicitly named owned twelve-frame RAW
/// fixture. Every round reverses source and tier order to expose warming/order
/// effects; report minima per tier rather than claiming a single stopwatch run.
#[test]
#[ignore = "explicit read-only source-preview release benchmark"]
fn benchmark_real_source_tiers() {
    use std::time::Instant;
    let source = PathBuf::from(std::env::var_os("STREHL_UI_BENCH_SOURCE").expect("source folder"));
    let report =
        PathBuf::from(std::env::var_os("STREHL_UI_BENCH_REPORT").expect("JSON report path"));
    let mut files: Vec<_> = std::fs::read_dir(&source)
        .unwrap()
        .map(|e| e.unwrap().path())
        .filter(|p| p.extension().is_some_and(|e| e.eq_ignore_ascii_case("arw")))
        .collect();
    files.sort();
    assert_eq!(files.len(), 12, "only the named compact sample is allowed");
    let cancelled = AtomicBool::new(false);
    let mut runs = Vec::new();
    let mut identities = std::collections::BTreeMap::new();
    for round in 0..4 {
        let indices: Vec<_> = if round % 2 == 0 {
            (0..files.len()).collect()
        } else {
            (0..files.len()).rev().collect()
        };
        for side in if round % 2 == 0 {
            [960, 1920]
        } else {
            [1920, 960]
        } {
            let mut timings = Vec::new();
            for index in &indices {
                let at = Instant::now();
                let image =
                    load_browser(&files[*index], side, side == 960, true, &cancelled).unwrap();
                timings.push(at.elapsed().as_secs_f64() * 1000.0);
                let digest = image
                    .rgba
                    .iter()
                    .fold(0xcbf29ce484222325_u64, |value, byte| {
                        (value ^ u64::from(*byte)).wrapping_mul(0x100000001b3)
                    });
                let identity = (image.source_size, image.size, digest);
                if let Some(prior) = identities.insert((*index, side), identity) {
                    assert_eq!(
                        identity, prior,
                        "repeat loads must preserve exact capture pixels"
                    );
                }
                assert_eq!(image.path, files[*index]);
                assert!(image.size.iter().all(|&v| v <= side as usize));
            }
            runs.push(serde_json::json!({"round": round, "side": side,
                "total_ms": timings.iter().sum::<f64>(), "frame_ms": timings}));
        }
    }
    let minimum = |side| {
        runs.iter()
            .filter(|r| r["side"] == side)
            .map(|r| r["total_ms"].as_f64().unwrap())
            .fold(f64::INFINITY, f64::min)
    };
    let frames: Vec<_> = identities
        .into_iter()
        .map(|((frame, side), (aperture, pixels, digest))| {
            serde_json::json!({"frame": frame, "side": side, "aperture": aperture,
            "pixels": pixels, "pixel_digest_fnv1a64": format!("{digest:016x}")})
        })
        .collect();
    let result = serde_json::json!({"source": source, "captures": files.len(),
        "ordering": "four alternating source and tier orders; minimum per tier",
        "overview_min_ms": minimum(960), "detail_min_ms": minimum(1920),
        "repeat_pixels_identical": true, "runs": runs, "frames": frames});
    std::fs::write(report, serde_json::to_vec_pretty(&result).unwrap()).unwrap();
    println!("{}", serde_json::to_string_pretty(&result).unwrap());
}
