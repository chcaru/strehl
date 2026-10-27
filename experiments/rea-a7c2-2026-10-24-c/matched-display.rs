//! Render two or more linear masters with the first master's exact display baseline.
use std::{path::Path, sync::atomic::AtomicBool};
use strehl_edit::{
    DevelopmentRecipe, ExportFormat, ExportSettings, OutputColorSpace, export_image, load_tiff,
};
fn main() -> anyhow::Result<()> {
    let args: Vec<_> = std::env::args().skip(1).collect();
    anyhow::ensure!(
        args.len() >= 3 && args.len() % 2 == 1,
        "usage: matched-display BASE_MASTER INPUT OUTPUT [INPUT OUTPUT ...]"
    );
    let baseline = load_tiff(Path::new(&args[0]))?.baseline;
    anyhow::ensure!(baseline.is_some(), "baseline has no display parameters");
    let settings = ExportSettings {
        format: ExportFormat::Tiff,
        hdr: false,
        color_space: OutputColorSpace::Srgb,
        quality: 100,
        speed: 6,
    };
    for pair in args[1..].as_chunks::<2>().0 {
        anyhow::ensure!(
            !Path::new(&pair[1]).exists(),
            "refuse to overwrite {}",
            pair[1]
        );
        let mut image = load_tiff(Path::new(&pair[0]))?;
        image.baseline = baseline;
        let report = export_image(
            Path::new(&pair[1]),
            &image,
            &DevelopmentRecipe::default(),
            &settings,
            &AtomicBool::new(false),
        )?;
        println!("{}", serde_json::to_string(&report)?);
    }
    Ok(())
}
