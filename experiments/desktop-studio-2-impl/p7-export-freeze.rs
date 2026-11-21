//! P7 compatibility probe: export a real master with settings given as JSON so
//! the same source runs against the code before and after the P7 export split.
//! Writes outputs only to the path given; never touches the capture folder.
//!
//! cargo run --release --locked -p strehl-edit --example p7-export-freeze -- \
//!   export <master.tiff> <recipe.json> '<settings json>' <out>
//! cargo run --release --locked -p strehl-edit --example p7-export-freeze -- \
//!   develop <master.tiff> <recipe.json> <out.u16>
use std::{io::Write, sync::atomic::AtomicBool, time::Instant};

fn main() -> anyhow::Result<()> {
    let args: Vec<String> = std::env::args().skip(1).collect();
    anyhow::ensure!(
        args.len() >= 4,
        "usage: export|develop <master> <recipe> ..."
    );
    let start = Instant::now();
    let image = strehl_edit::load_tiff(std::path::Path::new(&args[1]))?;
    eprintln!(
        "loaded {}x{} in {:.2} s",
        image.width,
        image.height,
        start.elapsed().as_secs_f64()
    );
    let recipe: strehl_edit::DevelopmentRecipe = serde_json::from_slice(&std::fs::read(&args[2])?)?;
    match args[0].as_str() {
        "export" => {
            anyhow::ensure!(args.len() == 5, "export needs settings JSON and output");
            let settings: strehl_edit::ExportSettings = serde_json::from_str(&args[3])?;
            let start = Instant::now();
            let report = strehl_edit::export_image(
                std::path::Path::new(&args[4]),
                &image,
                &recipe,
                &settings,
                &AtomicBool::new(false),
            )?;
            eprintln!("exported in {:.2} s", start.elapsed().as_secs_f64());
            println!("{}", serde_json::to_string(&report)?);
        }
        // After P7 only: the staged pipeline with a scale calibration.
        "export-with" => {
            anyhow::ensure!(args.len() == 6, "export-with needs settings, output, um/px");
            let settings: strehl_edit::ExportSettings = serde_json::from_str(&args[3])?;
            let extras = strehl_edit::ExportExtras {
                um_per_px: Some(args[5].parse()?),
                date_time: Some(strehl_edit::ExportDateTime::now_utc()),
                ..Default::default()
            };
            let start = Instant::now();
            let report = strehl_edit::export_image_with(
                std::path::Path::new(&args[4]),
                &image,
                &recipe,
                &settings,
                &extras,
                &AtomicBool::new(false),
            )?;
            eprintln!("exported in {:.2} s", start.elapsed().as_secs_f64());
            println!("{}", serde_json::to_string(&report)?);
        }
        "develop" => {
            // Development only, no encoder: the loop whose speed P7 changes.
            let mut best = f64::MAX;
            let mut pixels = Vec::new();
            for _ in 0..3 {
                let start = Instant::now();
                pixels = image.render_sdr16(&recipe)?;
                best = best.min(start.elapsed().as_secs_f64());
            }
            eprintln!("render_sdr16 best of 3: {best:.3} s");
            let mut out = std::io::BufWriter::new(std::fs::File::create(&args[3])?);
            for v in pixels {
                out.write_all(&v.to_le_bytes())?;
            }
            out.flush()?;
            println!("{best:.3}");
        }
        other => anyhow::bail!("unknown mode {other}"),
    }
    Ok(())
}
