//! Complete-photograph option review and bounded, alternating analysis timing.
//! Usage: adaptive-options-review input.tiff new-output-directory
use std::{fs, hint::black_box, path::PathBuf, time::Instant};
use strehl_edit::*;

fn main() -> anyhow::Result<()> {
    let mut args = std::env::args().skip(1);
    let input = PathBuf::from(args.next().expect("input TIFF"));
    let output = PathBuf::from(args.next().expect("new output directory"));
    anyhow::ensure!(
        args.next().is_none() && !output.exists(),
        "unexpected argument or output already exists"
    );
    let image = load_tiff(&input)?;
    let mut base = image.baked_recipe.clone().unwrap_or_default();
    base.global = Adjustments::default();
    base.spatial.clear();
    for region in &mut base.regions {
        region.adjustments = Adjustments::default();
    }
    let options = [
        ("natural", AdaptiveParameters::default()),
        (
            "deep-background",
            AdaptiveParameters {
                balance: 0.35,
                shadow_protection: 0.85,
                ..Default::default()
            },
        ),
        (
            "texture-contrast",
            AdaptiveParameters {
                balance: 0.2,
                local_contrast: 0.8,
                color: 0.15,
                tone_range: AdaptiveToneRange::Midtones,
                shadow_protection: 0.6,
                ..Default::default()
            },
        ),
        (
            "gentle-highlights",
            AdaptiveParameters {
                balance: 0.0,
                local_contrast: 0.25,
                color: 0.15,
                tone_range: AdaptiveToneRange::Highlights,
                shadow_protection: 1.0,
                highlight_compression: 0.65,
                ..Default::default()
            },
        ),
    ];
    let suggestions: Vec<_> = options
        .iter()
        .map(|(_, p)| {
            analyze_adaptive_with_parameters(&image, &base, None, AdaptiveIntent::Balance, *p)
        })
        .collect::<anyhow::Result<_>>()?;
    let mut timings = [Vec::new(), Vec::new(), Vec::new(), Vec::new()];
    for sweep in 0..4 {
        for offset in 0..4 {
            let arm = if sweep % 2 == 0 { offset } else { 3 - offset };
            let start = Instant::now();
            let suggestion = analyze_adaptive_with_parameters(
                &image,
                &base,
                None,
                AdaptiveIntent::Balance,
                options[arm].1,
            )?;
            timings[arm].push(start.elapsed().as_secs_f64() * 1000.0);
            anyhow::ensure!(
                suggestion == suggestions[arm],
                "repeated option analysis is not deterministic"
            );
            black_box(suggestion);
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
            "Amount zero changed pixels"
        );
        let recipe = suggestion.recipe_at(1.0)?;
        save_sdr_tiff(&output.join(format!("{name}.tiff")), &image, &recipe)?;
        fs::write(
            output.join(format!("{name}.json")),
            serde_json::to_vec_pretty(&recipe)?,
        )?;
        records.push(serde_json::json!({"name":name,"parameters":parameters,"analysis_ms":timings[index],"minimum_ms":timings[index].iter().copied().fold(f64::INFINITY,f64::min),"maximum_ms":timings[index].iter().copied().fold(0.0,f64::max),"sample_count":suggestion.stats.sample_count,"amount_zero_full_pixels_exact":true}));
    }
    fs::write(
        output.join("receipt.json"),
        serde_json::to_vec_pretty(&serde_json::json!({
            "size":[image.width,image.height],"origin":image.origin,"options":records,
            "timing_protocol":"one warm-up per option, then forward/reverse/forward/reverse; four samples each",
            "limits":"Analysis worker cost only: excludes import, whole-photograph rendering, texture upload, GPU and interaction. Options intentionally differ in output; timings compare their costs, not photographic merit. Complete TIFFs require independent visual review. No source RAW was modified or reconstructed."
        }))?,
    )?;
    println!(
        "{} complete option photographs at {}x{}",
        options.len(),
        image.width,
        image.height
    );
    Ok(())
}
