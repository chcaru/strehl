//! Explicit CPU-only viewport comparison. No RAW corpus, GPU FPS, or quality claim.
use std::{hint::black_box, sync::atomic::AtomicBool, time::Instant};
use strehl_edit::{DevelopmentRecipe, DisplayRegionRequest, ImageOrigin, LinearImage};

fn main() -> anyhow::Result<()> {
    rayon::ThreadPoolBuilder::new()
        .num_threads(8)
        .build_global()?;
    let (width, height) = (7032, 4688);
    let pixels = (0..width * height)
        .flat_map(|i| {
            let x = i % width;
            let y = i / width;
            let v = if x < width / 2 {
                0.15
            } else {
                0.05 + ((x % 19 + y % 11) as f32) * 0.013
            };
            [v, v * 0.9, v * 0.7]
        })
        .collect();
    let image = LinearImage {
        width,
        height,
        pixels,
        origin: ImageOrigin::SceneLinear,
        baseline: None,
        baked_recipe: None,
    };
    let mut recipe = DevelopmentRecipe::default();
    recipe.global.exposure = 0.7;
    recipe.global.highlights = -18.0;
    let request = DisplayRegionRequest {
        min: [3072, 1792],
        max: [4608, 2944],
        stride: 1,
    };
    let mut times = [Vec::new(), Vec::new(), Vec::new()];
    let mut reference = None;
    for sweep in 0..4 {
        for arm in if sweep % 2 == 0 { [0, 1, 2] } else { [2, 1, 0] } {
            let start = Instant::now();
            if arm == 0 {
                let (_, _, rgb) =
                    image.render_region_sdr8(&recipe, [0.0, 0.0], [1.0, 1.0], 8192)?;
                times[arm].push(start.elapsed().as_secs_f64() * 1000.0);
                reference = Some(rgb);
            } else {
                let result = image.render_display_region_mode(
                    &recipe,
                    request,
                    &AtomicBool::new(false),
                    arm == 2,
                )?;
                times[arm].push(start.elapsed().as_secs_f64() * 1000.0);
                black_box(&result);
                if let Some(reference) = &reference {
                    for y in 0..result.size[1] {
                        for x in 0..result.size[0] {
                            let actual = ((y * result.size[0] + x) * 3) as usize;
                            let expected =
                                (((y + request.min[1]) * width + x + request.min[0]) * 3) as usize;
                            anyhow::ensure!(
                                result.rgb[actual..actual + 3] == reference[expected..expected + 3],
                                "Native ROI changed SDR pixels"
                            );
                        }
                    }
                }
            }
        }
    }
    let minimum = times.map(|v| v.into_iter().fold(f64::INFINITY, f64::min));
    println!(
        "{}",
        serde_json::to_string_pretty(&serde_json::json!({
            "scope":"CPU development only; excludes decode, GPU transfer, presentation",
            "threads":8,"source":[width,height],"region":[request.min,request.max],
            "sweeps":"four alternating directions, per-arm minimum",
            "legacy_whole_image_ms":minimum[0],"viewport_sdr_ms":minimum[1],"viewport_sdr_and_hdr_ms":minimum[2],
            "legacy_output_pixels":u64::from(width)*u64::from(height),
            "viewport_output_pixels":1536*1152,"native_roi_matches_legacy_sdr":true,
            "sdr_work_ratio":minimum[0]/minimum[1]
        }))?
    );
    Ok(())
}
