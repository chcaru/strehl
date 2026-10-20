use anyhow::{Context, Result, ensure};
use clap::Args;
use std::path::PathBuf;
use strehl_edit::{DevelopmentRecipe, export_hdr_avif, import_xmp, load_tiff, save_sdr_tiff};

#[derive(Debug, Args)]
pub struct DevelopArgs {
    /// Strehl RGB32-float master, or an existing sRGB TIFF for SDR edits.
    pub input: PathBuf,
    #[arg(short, long)]
    pub out: PathBuf,
    /// Versioned JSON development recipe.
    #[arg(long)]
    pub recipe: Option<PathBuf>,
    /// Required for .avif output: true 10-bit PQ BT.2020 from a linear master.
    #[arg(long)]
    pub hdr: bool,
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
    ensure!(
        if args.hdr {
            extension.eq_ignore_ascii_case("avif")
        } else {
            matches!(extension.to_ascii_lowercase().as_str(), "tif" | "tiff")
        },
        "use --hdr with .avif output, or .tif/.tiff for SDR output"
    );
    let image = load_tiff(&args.input)?;
    if let Some(parent) = args.out.parent().filter(|p| !p.as_os_str().is_empty()) {
        std::fs::create_dir_all(parent)?;
    }
    if args.hdr {
        let report = export_hdr_avif(&args.out, &image, &recipe)?;
        println!("{}", serde_json::to_string_pretty(&report)?);
    } else {
        save_sdr_tiff(&args.out, &image, &recipe)?;
        println!(
            "{}",
            serde_json::json!({"output":args.out,"width":image.width,"height":image.height,"bit_depth":16,"space":"sRGB","source_origin":image.origin})
        );
    }
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
