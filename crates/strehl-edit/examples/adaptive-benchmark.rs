//! Bounded analysis/Amount timing, excluding import, preview generation and rendering.
//! Usage: adaptive-benchmark input.tiff new-receipt.json [recipe.json region-id]
use std::{fs, hint::black_box, path::PathBuf, time::Instant};
use strehl_edit::*;

fn main() -> anyhow::Result<()> {
    let mut args = std::env::args().skip(1);
    let input = PathBuf::from(args.next().expect("input TIFF"));
    let receipt = PathBuf::from(args.next().expect("new receipt JSON"));
    anyhow::ensure!(!receipt.exists(), "receipt already exists");
    let image = load_tiff(&input)?;
    let preview = image.preview(1600);
    let (recipe, region) = if let Some(path) = args.next() {
        (
            serde_json::from_slice(&fs::read(path)?)?,
            Some(args.next().expect("region ID")),
        )
    } else {
        (DevelopmentRecipe::default(), None)
    };
    anyhow::ensure!(args.next().is_none(), "unexpected argument");
    let mut timings = [Vec::new(), Vec::new(), Vec::new(), Vec::new()];
    let mut suggestions = Vec::new();
    for arm in 0..if region.is_some() { 4 } else { 2 } {
        let source = if arm % 2 == 0 { &image } else { &preview };
        suggestions.push(if arm < 2 {
            analyze_adaptive(source, &recipe)?
        } else {
            analyze_adaptive_region(
                source,
                &recipe,
                region.as_deref().unwrap(),
                AdaptiveIntent::RestoreHighlights,
            )?
        });
    }
    for sweep in 0..4 {
        for offset in 0..suggestions.len() {
            let arm = if sweep % 2 == 0 {
                offset
            } else {
                suggestions.len() - 1 - offset
            };
            let source = if arm % 2 == 0 { &image } else { &preview };
            let started = Instant::now();
            let suggestion = if arm < 2 {
                analyze_adaptive(source, &recipe)?
            } else {
                analyze_adaptive_region(
                    source,
                    &recipe,
                    region.as_deref().unwrap(),
                    AdaptiveIntent::RestoreHighlights,
                )?
            };
            timings[arm].push(started.elapsed().as_secs_f64() * 1000.0);
            anyhow::ensure!(
                suggestion == suggestions[arm],
                "repeated analysis changed its result"
            );
            black_box(suggestion);
        }
    }
    let labels = [
        "master_balance",
        "preview_balance",
        "master_region_highlights",
        "preview_region_highlights",
    ];
    let mut arms = Vec::new();
    for (arm, suggestion) in suggestions.iter().enumerate() {
        let started = Instant::now();
        for i in 0..5000 {
            black_box(suggestion.recipe_at((i % 101) as f32 / 100.0)?);
        }
        let amount_us = started.elapsed().as_secs_f64() * 1e6 / 5000.0;
        arms.push(serde_json::json!({
            "arm": labels[arm], "analysis_ms": timings[arm],
            "minimum_ms": timings[arm].iter().copied().fold(f64::INFINITY, f64::min),
            "maximum_ms": timings[arm].iter().copied().fold(0.0, f64::max),
            "cached_amount_mean_us": amount_us, "sample_count": suggestion.stats.sample_count,
        }));
    }
    let value = serde_json::json!({
        "source_size": [image.width,image.height], "preview_size": [preview.width,preview.height],
        "sweeps": "forward, reverse, forward, reverse after one warm-up per arm", "arms": arms,
        "limits": "Worker analysis only. Excludes import, preview creation, recipe publication, rendering, GPU work and interaction latency. Preview averaging changes the input; this is not an equal-output performance comparison. Production uses bounded master samples."
    });
    fs::write(receipt, serde_json::to_vec_pretty(&value)?)?;
    println!("{}", serde_json::to_string_pretty(&value)?);
    Ok(())
}
