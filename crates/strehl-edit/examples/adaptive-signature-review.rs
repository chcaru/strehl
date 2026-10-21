//! Complete-photograph review, not a photographic quality score.
//! Usage: adaptive-signature-review input.tiff new-output-directory
use std::{fs, hint::black_box, path::PathBuf, time::Instant};
use strehl_edit::*;

fn main() -> anyhow::Result<()> {
    let mut args = std::env::args().skip(1);
    let input = PathBuf::from(args.next().expect("input TIFF"));
    let output = PathBuf::from(args.next().expect("new output directory"));
    anyhow::ensure!(
        args.next().is_none() && !output.exists(),
        "unexpected argument or existing output"
    );
    let image = load_tiff(&input)?;
    let mut base = image.baked_recipe.clone().unwrap_or_default();
    base.global = Adjustments::default();
    for region in &mut base.regions {
        region.adjustments = Adjustments::default();
    }
    base.spatial.clear();
    let options = [
        ("natural", AdaptiveParameters::default()),
        ("signature", AdaptiveParameters::signature()),
    ];
    let suggestions: Vec<_> = options
        .iter()
        .map(|(_, p)| {
            analyze_adaptive_with_parameters(&image, &base, None, AdaptiveIntent::Balance, *p)
        })
        .collect::<anyhow::Result<_>>()?;
    let mut timings = [Vec::new(), Vec::new()];
    for sweep in 0..4 {
        for offset in 0..2 {
            let arm = if sweep % 2 == 0 { offset } else { 1 - offset };
            let start = Instant::now();
            let s = analyze_adaptive_with_parameters(
                &image,
                &base,
                None,
                AdaptiveIntent::Balance,
                options[arm].1,
            )?;
            timings[arm].push(start.elapsed().as_secs_f64() * 1000.0);
            anyhow::ensure!(s == suggestions[arm], "nondeterministic analysis");
            black_box(s);
        }
    }
    fs::create_dir(&output)?;
    let before = image.render_sdr16(&base)?;
    save_sdr_tiff(&output.join("before.tiff"), &image, &base)?;
    let mut records = Vec::new();
    for (index, ((name, parameters), suggestion)) in options.iter().zip(&suggestions).enumerate() {
        let zero = suggestion.recipe_at(0.0)?;
        anyhow::ensure!(
            zero == base && image.render_sdr16(&zero)? == before,
            "Amount zero changed complete image pixels"
        );
        let recipe = suggestion.recipe_at(1.0)?;
        save_sdr_tiff(&output.join(format!("{name}.tiff")), &image, &recipe)?;
        fs::write(
            output.join(format!("{name}.json")),
            serde_json::to_vec_pretty(suggestion)?,
        )?;
        records.push(serde_json::json!({"name":name,"parameters":parameters,
            "analysis_ms":timings[index],
            "minimum_ms":timings[index].iter().copied().fold(f64::INFINITY,f64::min),
            "sample_count":suggestion.stats.sample_count,"amount_zero_full_pixels_exact":true}));
    }
    fs::write(
        output.join("receipt.json"),
        serde_json::to_vec_pretty(&serde_json::json!({
            "source":input,"size":[image.width,image.height],"origin":image.origin,"options":records,
            "timing_protocol":"one warm-up each then forward/reverse/forward/reverse, four measurements per option",
            "limits":"Analysis worker only; excludes loading, rendering, GPU and UI responsiveness. Full images require independent visual review. Output difference is not a quality score."
        }))?,
    )?;
    println!(
        "Complete before/Natural/Signature photographs: {}x{}",
        image.width, image.height
    );
    Ok(())
}
