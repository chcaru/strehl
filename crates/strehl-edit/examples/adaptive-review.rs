//! Render complete before/after photographs and an exact strength-zero placebo.
//! Usage: cargo run --release -p strehl-edit --example adaptive-review -- input.tiff new-output-dir
use std::{fs, path::PathBuf, time::Instant};
use strehl_edit::*;

fn main() -> anyhow::Result<()> {
    let mut args = std::env::args().skip(1);
    let input = PathBuf::from(args.next().expect("input TIFF"));
    let output = PathBuf::from(args.next().expect("new output directory"));
    anyhow::ensure!(!output.exists(), "review directory already exists");
    let image = load_tiff(&input)?;
    let mut base = image.baked_recipe.clone().unwrap_or_default();
    base.global = Adjustments::default();
    for region in &mut base.regions {
        region.adjustments = Adjustments::default();
    }
    let started = Instant::now();
    let suggestion = analyze_adaptive(&image, &base)?;
    let analysis_ms = started.elapsed().as_secs_f64() * 1000.0;
    let zero = suggestion.recipe_at(0.0)?;
    anyhow::ensure!(zero == base, "zero strength changed the recipe");
    let before = image.render_sdr16(&base)?;
    anyhow::ensure!(
        before == image.render_sdr16(&zero)?,
        "zero strength changed complete image pixels"
    );
    drop(before);
    fs::create_dir(&output)?;
    save_sdr_tiff(&output.join("before.tiff"), &image, &base)?;
    save_sdr_tiff(
        &output.join("after.tiff"),
        &image,
        &suggestion.recipe_at(1.0)?,
    )?;
    save_sdr_tiff(&output.join("zero.tiff"), &image, &zero)?;
    fs::write(
        output.join("suggestion.json"),
        serde_json::to_vec_pretty(&suggestion)?,
    )?;
    fs::write(
        output.join("receipt.json"),
        serde_json::to_vec_pretty(&serde_json::json!({
            "width": image.width, "height": image.height, "origin": image.origin,
            "analysis_ms": analysis_ms, "zero_strength_all_pixels_identical": true,
            "sample_count": suggestion.stats.sample_count,
            "scope": "Whole-photo development suggestions, not automatic quality acceptance or new stack reconstruction"
        }))?,
    )?;
    println!(
        "{}x{} {:?}; analysis {:.3} ms; {} changes",
        image.width,
        image.height,
        image.origin,
        analysis_ms,
        suggestion.changes.len()
    );
    Ok(())
}
