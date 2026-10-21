//! Reproducible color/codec fixture; decode with an independent implementation.
use anyhow::Result;
use std::{path::PathBuf, sync::atomic::AtomicBool, time::Instant};
use strehl_edit::*;
fn main() -> Result<()> {
    let mut args = std::env::args_os().skip(1);
    let out = PathBuf::from(args.next().expect("output directory"));
    std::fs::create_dir_all(&out)?;
    let image = if let Some(input) = args.next() {
        load_tiff(&PathBuf::from(input))?
    } else {
        let mut pixels = Vec::new();
        let patches = [
            [0.02, 0.2, 0.6],
            [1.8, 0.2, 0.04],
            [0.1, 2.4, 0.15],
            [0.02, 0.3, 3.2],
            [0.18; 3],
            [1.0; 3],
            [3.0; 3],
            [-0.03, 0.4, 1.2],
        ];
        for y in 0..128 {
            for x in 0..192 {
                let mut p = patches[x / 24];
                if y >= 64 {
                    let detail = (((x * 17 + y * 29) % 31) as f32 - 15.0) * 0.001;
                    p = p.map(|v| v + detail);
                }
                pixels.extend(p);
            }
        }
        LinearImage {
            width: 192,
            height: 128,
            pixels,
            origin: ImageOrigin::SceneLinear,
            baseline: None,
            baked_recipe: None,
        }
    };
    let recipe = image.baked_recipe.clone().unwrap_or_default();
    let mut reports = Vec::new();
    for space in [
        OutputColorSpace::Srgb,
        OutputColorSpace::DisplayP3,
        OutputColorSpace::Rec2020,
    ] {
        for format in [
            ExportFormat::Avif,
            ExportFormat::Tiff,
            ExportFormat::Png,
            ExportFormat::Jpeg,
        ] {
            let hdr = format == ExportFormat::Avif && image.origin == ImageOrigin::SceneLinear;
            let settings = ExportSettings {
                format,
                color_space: space,
                hdr,
                ..Default::default()
            };
            let ext = match format {
                ExportFormat::Avif => "avif",
                ExportFormat::Tiff => "tiff",
                ExportFormat::Png => "png",
                ExportFormat::Jpeg => "jpg",
            };
            let path = out.join(format!("{space:?}.{ext}"));
            let start = Instant::now();
            let report = export_image(&path, &image, &recipe, &settings, &AtomicBool::new(false))?;
            reports.push(serde_json::json!({"file":path,"settings":settings,"seconds":start.elapsed().as_secs_f64(),"report":report}));
        }
    }
    if image.width == 192 && image.height == 128 {
        for (run, speed) in [6, 8, 10, 10, 8, 6].into_iter().enumerate() {
            let settings = ExportSettings {
                speed,
                ..Default::default()
            };
            let path = out.join(format!("speed-{run}-{speed}.avif"));
            let start = Instant::now();
            let report = export_image(&path, &image, &recipe, &settings, &AtomicBool::new(false))?;
            reports.push(serde_json::json!({"file":path,"settings":settings,"seconds":start.elapsed().as_secs_f64(),"report":report}));
        }
        save_linear_tiff(&out.join("source-linear.tiff"), &image)?;
    }
    std::fs::write(
        out.join("receipt.json"),
        serde_json::to_vec_pretty(&reports)?,
    )?;
    Ok(())
}
