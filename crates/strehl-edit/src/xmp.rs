use crate::DevelopmentRecipe;
use anyhow::{Context, Result, ensure};
use quick_xml::{Reader, events::Event};
use serde::Serialize;

#[derive(Debug, Clone, Serialize)]
pub struct XmpImport {
    pub recipe: DevelopmentRecipe,
    pub applied: Vec<String>,
    pub warnings: Vec<String>,
}

/// Import the portable numeric subset. Adobe Look stubs/AI models cannot be executed.
/// The caller owns the private file; no preset contents are copied into the repository.
pub fn import_xmp(xml: &str) -> Result<XmpImport> {
    ensure!(
        xml.len() <= 4 * 1024 * 1024,
        "XMP exceeds the 4 MiB import limit"
    );
    let mut reader = Reader::from_str(xml);
    let mut result=XmpImport{recipe:DevelopmentRecipe::default(),applied:Vec::new(),warnings:vec![
        "Imported numeric settings use Strehl's rendering operators; they do not reproduce Adobe's process.".into()
    ]};
    let mut look_depth = 0usize;
    loop {
        match reader.read_event().context("reading XMP")? {
            Event::Start(e) | Event::Empty(e) => {
                if e.name().as_ref() == b"crs:Look" {
                    look_depth += 1;
                    result.warnings.push("Adobe Look/AI profile is not portable: its name is a reference, not an embedded model or LUT. It was not applied.".into());
                }
                if look_depth > 0 {
                    continue;
                }
                for attr in e.attributes() {
                    let attr = attr?;
                    let name = std::str::from_utf8(attr.key.as_ref())?;
                    let value = attr.decoded_and_normalized_value(
                        quick_xml::XmlVersion::Implicit1_0,
                        reader.decoder(),
                    )?;
                    let field = match name {
                        "crs:Exposure2012" => Some(&mut result.recipe.global.exposure),
                        "crs:Contrast2012" => Some(&mut result.recipe.global.contrast),
                        "crs:Highlights2012" => Some(&mut result.recipe.global.highlights),
                        "crs:Shadows2012" => Some(&mut result.recipe.global.shadows),
                        "crs:Whites2012" => Some(&mut result.recipe.global.whites),
                        "crs:Blacks2012" => Some(&mut result.recipe.global.blacks),
                        "crs:Vibrance" => Some(&mut result.recipe.global.vibrance),
                        "crs:Saturation" => Some(&mut result.recipe.global.saturation),
                        _ => None,
                    };
                    if let Some(field) = field {
                        *field = value
                            .parse()
                            .with_context(|| format!("invalid numeric XMP field {name}"))?;
                        result.applied.push(name.trim_start_matches("crs:").into());
                    } else if name == "crs:HDRMaxValue" {
                        let stops: f32 = value.parse().context("invalid XMP HDRMaxValue")?;
                        ensure!(
                            stops.is_finite() && (0.0..=5.6).contains(&stops),
                            "XMP HDR headroom is outside the supported range"
                        );
                        result.recipe.hdr.peak_nits = (203.0 * stops.exp2()).min(10_000.0);
                        result.applied.push(
                            "HDRMaxValue (headroom mapped above 203-nit reference white)".into(),
                        );
                    } else if (matches!(
                        name,
                        "crs:Temperature"
                            | "crs:Tint"
                            | "crs:Sharpness"
                            | "crs:ColorNoiseReduction"
                            | "crs:Texture"
                            | "crs:Clarity2012"
                            | "crs:Dehaze"
                            | "crs:LuminanceSmoothing"
                    ) || name.starts_with("crs:HueAdjustment")
                        || name.starts_with("crs:SaturationAdjustment")
                        || name.starts_with("crs:LuminanceAdjustment"))
                        && value != "0"
                        && value != "0.0"
                    {
                        result.warnings.push(format!("{name} was not applied; this XMP operator has no equivalent in the current Strehl recipe."));
                    }
                }
            }
            Event::End(e) if e.name().as_ref() == b"crs:Look" => {
                look_depth = look_depth.saturating_sub(1)
            }
            Event::DocType(_) => anyhow::bail!("XMP document type declarations are not supported"),
            Event::Eof => break,
            _ => {}
        }
    }
    ensure!(
        !result.applied.is_empty(),
        "no supported development settings found in this XMP"
    );
    result.recipe.validate()?;
    Ok(result)
}
