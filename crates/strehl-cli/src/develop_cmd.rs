use anyhow::{Context, Result, ensure};
use clap::{Args, ValueEnum};
use std::{path::PathBuf, sync::atomic::AtomicBool};
use strehl_edit::{
    DevelopmentRecipe, ExportFormat, ExportSettings, OutputColorSpace, export_image, import_xmp,
    load_tiff,
};

#[derive(Debug, Clone, Copy, ValueEnum)]
pub enum ExportGamut {
    Srgb,
    DisplayP3,
    Rec2020,
}

#[derive(Debug, Args)]
pub struct DevelopArgs {
    /// Strehl RGB32-float master, or an existing sRGB TIFF for SDR edits.
    pub input: PathBuf,
    #[arg(short, long)]
    pub out: PathBuf,
    /// Versioned JSON development recipe.
    #[arg(long)]
    pub recipe: Option<PathBuf>,
    /// 10-bit PQ HDR AVIF from a linear master. Other formats are SDR.
    #[arg(long)]
    pub hdr: bool,
    /// Output RGB primaries. Default: Rec.2020 for HDR, sRGB for SDR.
    #[arg(long, value_enum)]
    pub color_space: Option<ExportGamut>,
    /// AVIF/JPEG quality, 1..100. Highest supported quality remains lossy.
    #[arg(long, value_parser = clap::value_parser!(u8).range(1..=100))]
    pub quality: Option<u8>,
    /// AVIF encoder speed, 0..10. Higher is faster and can change coding quality.
    #[arg(long, value_parser = clap::value_parser!(u8).range(0..=10))]
    pub speed: Option<u8>,
}

#[derive(Debug, Args)]
pub struct ImportPresetArgs {
    pub input: PathBuf,
    #[arg(short, long)]
    pub out: PathBuf,
}

pub fn run(args: &DevelopArgs) -> Result<()> {
    ensure!(
        args.input != args.out,
        "development must not overwrite its original master"
    );
    ensure!(
        !args.out.exists(),
        "output already exists; choose a new export filename"
    );
    let recipe: DevelopmentRecipe = if let Some(path) = &args.recipe {
        serde_json::from_slice(&std::fs::read(path)?).context("reading development recipe")?
    } else {
        DevelopmentRecipe::default()
    };
    recipe.validate()?;
    let extension = args
        .out
        .extension()
        .and_then(|x| x.to_str())
        .unwrap_or_default();
    let format = match extension.to_ascii_lowercase().as_str() {
        "avif" => ExportFormat::Avif,
        "tif" | "tiff" => ExportFormat::Tiff,
        "png" => ExportFormat::Png,
        "jpg" | "jpeg" => ExportFormat::Jpeg,
        _ => anyhow::bail!("output extension must be .avif, .tif/.tiff, .png or .jpg/.jpeg"),
    };
    let settings = ExportSettings {
        format,
        hdr: args.hdr,
        color_space: match args.color_space {
            Some(ExportGamut::Srgb) => OutputColorSpace::Srgb,
            Some(ExportGamut::DisplayP3) => OutputColorSpace::DisplayP3,
            Some(ExportGamut::Rec2020) => OutputColorSpace::Rec2020,
            None if args.hdr => OutputColorSpace::Rec2020,
            None => OutputColorSpace::Srgb,
        },
        quality: args.quality.unwrap_or(recipe.hdr.quality),
        speed: args.speed.unwrap_or(recipe.hdr.speed),
    };
    settings.validate()?;
    let image = load_tiff(&args.input)?;
    if let Some(parent) = args.out.parent().filter(|p| !p.as_os_str().is_empty()) {
        std::fs::create_dir_all(parent)?;
    }
    let report = export_image(
        &args.out,
        &image,
        &recipe,
        &settings,
        &AtomicBool::new(false),
    )?;
    println!("{}", serde_json::to_string_pretty(&report)?);
    Ok(())
}

pub fn import(args: &ImportPresetArgs) -> Result<()> {
    ensure!(
        args.input != args.out && !args.out.exists(),
        "choose a new recipe filename"
    );
    let preset = import_xmp(&std::fs::read_to_string(&args.input)?)?;
    std::fs::write(&args.out, serde_json::to_vec_pretty(&preset.recipe)?)?;
    println!("{}", serde_json::to_string_pretty(&preset)?);
    Ok(())
}
