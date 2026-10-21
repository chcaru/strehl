use std::fs::File;
use std::io::{BufReader, BufWriter, Write};
use std::path::Path;

use anyhow::{Context, Result, bail, ensure};
use rayon::prelude::*;
use serde::{Deserialize, Serialize};
use tiff::{
    ColorType,
    decoder::{Decoder, DecodingResult},
    encoder::{TiffEncoder, colortype},
    tags::Tag,
};

use crate::DevelopmentRecipe;

pub(crate) struct IccBytes<'a>(pub(crate) &'a [u8]);
impl tiff::encoder::TiffValue for IccBytes<'_> {
    const BYTE_LEN: u8 = 1;
    const FIELD_TYPE: tiff::tags::Type = tiff::tags::Type::UNDEFINED;
    fn count(&self) -> usize {
        self.0.len()
    }
    fn data(&self) -> std::borrow::Cow<'_, [u8]> {
        std::borrow::Cow::Borrowed(self.0)
    }
}

pub const LINEAR_MASTER_DESCRIPTION: &str = "Strehl scene-linear master v1; RGB32Float; BT.709 primaries; D65; linear transfer; unclipped pre-tone values; 1.0 is sensor-normalized reference white.";

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum ImageOrigin {
    SceneLinear,
    /// Existing SDR photograph, linearized for editing. Clipped detail cannot be recovered.
    DisplayReferred,
}

/// Recorded legacy viewing placement, separate from the unclipped master samples.
#[derive(Debug, Clone, Copy, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct DisplayBaseline {
    pub black: f32,
    pub white: f32,
    pub contrast: f32,
    pub exposure_gain: f32,
}

impl DisplayBaseline {
    pub(crate) fn validate(&self) -> Result<()> {
        ensure!(
            [self.black, self.white, self.contrast, self.exposure_gain]
                .iter()
                .all(|v| v.is_finite())
                && self.white > self.black
                && (0.0..=1.0).contains(&self.contrast)
                && self.exposure_gain > 0.0,
            "invalid display baseline"
        );
        Ok(())
    }
    pub(crate) fn place(&self, v: [f32; 3]) -> [f32; 3] {
        let l = crate::recipe::luma(v).max(0.0);
        if l <= 0.0 {
            return [0.0; 3];
        }
        let s = 1.0 / (self.white - self.black);
        let y = (l - self.black) * s;
        let soft = 0.5 * (y + (y * y + 0.004 * 0.004).sqrt());
        let gain = (soft / l).min(s) * self.exposure_gain;
        v.map(|x| x * gain)
    }
}

#[derive(Debug, Clone)]
pub struct LinearImage {
    pub width: u32,
    pub height: u32,
    /// Interleaved RGB in linear BT.709/D65. Negative and >1 values are preserved.
    pub pixels: Vec<f32>,
    pub origin: ImageOrigin,
    pub baseline: Option<DisplayBaseline>,
    /// Only the enabled source-range repairs were applied during stacking.
    /// Tone controls in this provenance are not baked into the master.
    pub baked_recipe: Option<DevelopmentRecipe>,
}

impl LinearImage {
    pub fn validate(&self) -> Result<()> {
        let count = image_samples(self.width, self.height)?;
        ensure!(
            self.pixels.len() == count,
            "RGB sample count does not match image dimensions"
        );
        ensure!(
            self.pixels.iter().all(|v| v.is_finite()),
            "image contains non-finite samples"
        );
        if let Some(baseline) = self.baseline {
            baseline.validate()?;
        }
        if let Some(recipe) = &self.baked_recipe {
            recipe.validate()?;
        }
        Ok(())
    }

    /// Area-averaged linear preview. Never resizes an already-developed SDR view.
    pub fn preview(&self, max_edge: u32) -> Self {
        let max_edge = max_edge.max(1);
        let scale = self.width.max(self.height) as f32 / max_edge as f32;
        if scale <= 1.0 {
            return self.clone();
        }
        let width = ((self.width as f32 / scale).round() as u32).max(1);
        let height = ((self.height as f32 / scale).round() as u32).max(1);
        let mut pixels = vec![0.0; width as usize * height as usize * 3];
        pixels
            .par_chunks_mut(width as usize * 3)
            .enumerate()
            .for_each(|(y, row)| {
                let y0 = y * self.height as usize / height as usize;
                let y1 = ((y + 1) * self.height as usize / height as usize).max(y0 + 1);
                for (x, out) in row.as_chunks_mut::<3>().0.iter_mut().enumerate() {
                    let x0 = x * self.width as usize / width as usize;
                    let x1 = ((x + 1) * self.width as usize / width as usize).max(x0 + 1);
                    let mut sum = [0.0f64; 3];
                    for sy in y0..y1 {
                        for sx in x0..x1 {
                            let i = (sy * self.width as usize + sx) * 3;
                            for (c, value) in sum.iter_mut().enumerate() {
                                *value += f64::from(self.pixels[i + c]);
                            }
                        }
                    }
                    let n = ((x1 - x0) * (y1 - y0)) as f64;
                    for c in 0..3 {
                        out[c] = (sum[c] / n) as f32;
                    }
                }
            });
        Self {
            width,
            height,
            pixels,
            origin: self.origin,
            baseline: self.baseline,
            baked_recipe: self.baked_recipe.clone(),
        }
    }

    pub fn render_sdr8(&self, recipe: &DevelopmentRecipe) -> Result<Vec<u8>> {
        self.validate()?;
        recipe.validate()?;
        let mut result = vec![0u8; self.pixels.len()];
        result.par_chunks_mut(3).enumerate().for_each(|(i, out)| {
            let rgb = self.display_pixel(i, recipe);
            for c in 0..3 {
                out[c] = (rgb[c] * 255.0 + 0.5) as u8;
            }
        });
        Ok(result)
    }

    pub fn render_sdr16(&self, recipe: &DevelopmentRecipe) -> Result<Vec<u16>> {
        self.validate()?;
        recipe.validate()?;
        let mut result = vec![0u16; self.pixels.len()];
        result.par_chunks_mut(3).enumerate().for_each(|(i, out)| {
            let rgb = self.display_pixel(i, recipe);
            for c in 0..3 {
                out[c] = (rgb[c] * 65535.0 + 0.5) as u16;
            }
        });
        Ok(result)
    }

    /// Develop an ROI without rebasing normalized annotation coordinates.
    pub fn render_region_sdr8(
        &self,
        recipe: &DevelopmentRecipe,
        min: [f32; 2],
        max: [f32; 2],
        max_edge: u32,
    ) -> Result<(u32, u32, Vec<u8>)> {
        recipe.validate()?;
        ensure!(
            self.pixels.len() == image_samples(self.width, self.height)?,
            "invalid image sample count"
        );
        ensure!(
            min.iter()
                .chain(max.iter())
                .all(|v| v.is_finite() && (0.0..=1.0).contains(v))
                && max[0] > min[0]
                && max[1] > min[1],
            "preview region must be a normalized positive rectangle"
        );
        let x0 = (min[0] * self.width as f32).floor() as u32;
        let y0 = (min[1] * self.height as f32).floor() as u32;
        let x1 = (max[0] * self.width as f32).ceil().min(self.width as f32) as u32;
        let y1 = (max[1] * self.height as f32).ceil().min(self.height as f32) as u32;
        let rw = (x1 - x0).max(1);
        let rh = (y1 - y0).max(1);
        let scale = rw.max(rh) as f32 / max_edge.max(1) as f32;
        let width = (rw as f32 / scale.max(1.0)).round().max(1.0) as u32;
        let height = (rh as f32 / scale.max(1.0)).round().max(1.0) as u32;
        let mut rgb = vec![0u8; (width * height * 3) as usize];
        rgb.par_chunks_mut(3).enumerate().for_each(|(i, p)| {
            let x = x0 + ((i % width as usize) as u32 * rw / width);
            let y = y0 + ((i / width as usize) as u32 * rh / height);
            let c = self.display_pixel((y * self.width + x) as usize, recipe);
            for ch in 0..3 {
                p[ch] = (c[ch] * 255.0 + 0.5) as u8;
            }
        });
        Ok((width, height, rgb))
    }

    pub fn validate_source_repairs(&self, recipe: &DevelopmentRecipe) -> Result<()> {
        let active = |r: &DevelopmentRecipe| {
            r.regions
                .iter()
                .filter(|x| x.enabled && x.source_range.is_some())
                .map(|x| {
                    (
                        x.id.clone(),
                        x.shape.clone(),
                        x.feather,
                        x.source_range.clone(),
                    )
                })
                .collect::<Vec<_>>()
        };
        let wanted = active(recipe);
        let baked = self.baked_recipe.as_ref().map(active).unwrap_or_default();
        ensure!(
            wanted == baked,
            "source-range repair settings differ from this master; restack before export"
        );
        Ok(())
    }

    /// Developed linear BT.709, including the stored baseline and recipe.
    /// Values above reference white remain above 1, as in native HDR display.
    /// `i` must address a pixel in this image, just as for `display_pixel`.
    pub fn developed_pixel(&self, i: usize, recipe: &DevelopmentRecipe) -> [f32; 3] {
        let p = &self.pixels[i * 3..i * 3 + 3];
        let uv = [
            ((i % self.width as usize) as f32 + 0.5) / self.width as f32,
            ((i / self.width as usize) as f32 + 0.5) / self.height as f32,
        ];
        self.developed_sample([p[0], p[1], p[2]], uv, recipe)
    }

    pub(crate) fn developed_sample(
        &self,
        raw: [f32; 3],
        uv: [f32; 2],
        recipe: &DevelopmentRecipe,
    ) -> [f32; 3] {
        let base = self.baseline.map_or(raw, |b| b.place(raw));
        let developed = recipe.apply_pixel(base, uv);
        // Match the original SDR midtone style while retaining HDR headroom.
        // The display S-curve is extended with its positive tangent above white;
        // evaluating the cubic there would fold the highlight order backwards.
        self.baseline.map_or(developed, |b| {
            developed.map(|linear| {
                if linear < 0.0 {
                    return linear;
                }
                let x = if linear <= 0.0031308 {
                    linear * 12.92
                } else {
                    1.055 * linear.powf(1.0 / 2.4) - 0.055
                };
                let styled = if x <= 1.0 {
                    x + (x * x * (3.0 - 2.0 * x) - x) * b.contrast
                } else {
                    1.0 + (x - 1.0) * (1.0 - b.contrast).max(0.01)
                };
                srgb_decode(styled)
            })
        })
    }

    pub fn display_pixel(&self, i: usize, recipe: &DevelopmentRecipe) -> [f32; 3] {
        // Baseline stays fixed while editing. Exposure is applied after its placement
        // so an auto-tone cannot silently cancel a commanded exposure adjustment.
        let p = &self.pixels[i * 3..i * 3 + 3];
        let uv = [
            ((i % self.width as usize) as f32 + 0.5) / self.width as f32,
            ((i / self.width as usize) as f32 + 0.5) / self.height as f32,
        ];
        self.display_sample([p[0], p[1], p[2]], uv, recipe)
    }

    pub(crate) fn display_sample(
        &self,
        raw: [f32; 3],
        uv: [f32; 2],
        recipe: &DevelopmentRecipe,
    ) -> [f32; 3] {
        let base = self.baseline.map_or(raw, |b| b.place(raw));
        let rgb = recipe.apply_pixel(base, uv);
        let rgb = if self.baseline.is_some() {
            gamut_map(rgb)
        } else {
            rgb
        };
        rgb.map(|v| {
            let x = srgb_encode(v);
            self.baseline
                .map_or(x, |b| x + (x * x * (3.0 - 2.0 * x) - x) * b.contrast)
        })
    }
}

fn gamut_map(v: [f32; 3]) -> [f32; 3] {
    if v.iter().all(|x| (0.0..=1.0).contains(x)) {
        return v;
    }
    let y = crate::recipe::luma(v).clamp(0.0, 1.0);
    let mut t = 0.0f32;
    for c in v {
        if c < 0.0 && y - c > 1e-6 {
            t = t.max(-c / (y - c));
        } else if c > 1.0 && c - y > 1e-6 {
            t = t.max((c - 1.0) / (c - y));
        }
    }
    v.map(|c| (c + (y - c) * t.clamp(0.0, 1.0)).clamp(0.0, 1.0))
}

pub(crate) fn image_samples(w: u32, h: u32) -> Result<usize> {
    ensure!(w > 0 && h > 0, "image dimensions must be nonzero");
    let pixels = u64::from(w) * u64::from(h);
    ensure!(
        pixels <= 200_000_000,
        "image exceeds the 200-megapixel editing limit"
    );
    Ok(usize::try_from(pixels * 3)?)
}

pub(crate) fn srgb_encode(v: f32) -> f32 {
    let v = v.clamp(0.0, 1.0);
    if v <= 0.0031308 {
        v * 12.92
    } else {
        1.055 * v.powf(1.0 / 2.4) - 0.055
    }
}
fn srgb_decode(v: f32) -> f32 {
    if v <= 0.04045 {
        v / 12.92
    } else {
        ((v + 0.055) / 1.055).powf(2.4)
    }
}

pub fn load_tiff(path: &Path) -> Result<LinearImage> {
    let mut decoder = Decoder::new(BufReader::new(
        File::open(path).with_context(|| format!("opening {}", path.display()))?,
    ))?;
    let (width, height) = decoder.dimensions()?;
    let samples = image_samples(width, height)?;
    let mut limits = tiff::decoder::Limits::default();
    // The 33 MP RGB32 master is ~396 MB, above tiff's default 256 MiB limit.
    // Bound this to the validated dimensions instead of disabling limits.
    // TIFF also charges decoded metadata values to this limit, so a tiny
    // photograph still needs room for its ICC profile and recipe.
    limits.decoding_buffer_size = samples
        .checked_mul(4)
        .context("TIFF size overflow")?
        .max(2 * 1024 * 1024);
    limits.ifd_value_size = 2 * 1024 * 1024;
    decoder = decoder.with_limits(limits);
    let description = decoder
        .get_tag_ascii_string(Tag::ImageDescription)
        .unwrap_or_default();
    let color = decoder.colortype()?;
    let mut input_space = crate::OutputColorSpace::Srgb;
    if matches!(color, ColorType::RGB(8) | ColorType::RGB(16))
        && decoder.find_tag(Tag::IccProfile)?.is_some()
    {
        let profile = decoder.get_tag_u8_vec(Tag::IccProfile)?;
        input_space = [crate::OutputColorSpace::Srgb, crate::OutputColorSpace::DisplayP3, crate::OutputColorSpace::Rec2020]
            .into_iter().find(|&space| profile == crate::icc::icc_output_v2(space, false))
            .context("this TIFF has an unsupported embedded color profile; convert it to sRGB before editing (foreign profiles are never silently relabeled)")?;
    }
    let (mut pixels, origin) = match (color, decoder.read_image()?) {
        (ColorType::RGB(32), DecodingResult::F32(v)) => {
            ensure!(
                description.starts_with(LINEAR_MASTER_DESCRIPTION),
                "float TIFF must identify a Strehl scene-linear BT.709 master; unknown primaries are not assumed"
            );
            (v, ImageOrigin::SceneLinear)
        }
        (ColorType::RGB(16), DecodingResult::U16(v)) => {
            ensure!(
                !description.contains("camera-native") && !description.starts_with("Linear sRGB"),
                "this TIFF is not an sRGB display photograph; use a scene-linear master"
            );
            (
                v.into_par_iter()
                    .map(|x| srgb_decode(x as f32 / 65535.0))
                    .collect(),
                ImageOrigin::DisplayReferred,
            )
        }
        (ColorType::RGB(8), DecodingResult::U8(v)) => {
            ensure!(
                !description.contains("camera-native") && !description.starts_with("Linear sRGB"),
                "this TIFF is not an sRGB display photograph"
            );
            (
                v.into_par_iter()
                    .map(|x| srgb_decode(x as f32 / 255.0))
                    .collect(),
                ImageOrigin::DisplayReferred,
            )
        }
        _ => bail!("editing supports Strehl RGB32-float masters and sRGB RGB8/RGB16 TIFFs"),
    };
    if input_space != crate::OutputColorSpace::Srgb && origin == ImageOrigin::DisplayReferred {
        pixels.par_chunks_mut(3).for_each(|p| {
            p.copy_from_slice(&input_space.to_linear_srgb([p[0], p[1], p[2]]));
        });
    }
    let baseline = description
        .lines()
        .find_map(|line| line.strip_prefix("DisplayBaseline: "))
        .map(serde_json::from_str)
        .transpose()
        .context("reading master display baseline")?;
    let baked_recipe = description
        .lines()
        .find_map(|line| line.strip_prefix("BakedSourceRecipe: "))
        .map(serde_json::from_str)
        .transpose()
        .context("reading master source-repair provenance")?;
    let image = LinearImage {
        width,
        height,
        pixels,
        origin,
        baseline,
        baked_recipe,
    };
    image.validate()?;
    Ok(image)
}

pub fn save_linear_tiff(path: &Path, image: &LinearImage) -> Result<()> {
    image.validate()?;
    ensure!(
        image.origin == ImageOrigin::SceneLinear,
        "a display-referred photograph cannot be relabeled as a scene-linear master"
    );
    let mut encoder = TiffEncoder::new(BufWriter::new(File::create(path)?))?;
    let mut output = encoder.new_image::<colortype::RGB32Float>(image.width, image.height)?;
    let mut description = match image.baseline {
        Some(b) => format!(
            "{LINEAR_MASTER_DESCRIPTION}\nDisplayBaseline: {}",
            serde_json::to_string(&b)?
        ),
        None => LINEAR_MASTER_DESCRIPTION.into(),
    };
    if let Some(recipe) = &image.baked_recipe {
        description.push_str("\nBakedSourceRecipe: ");
        description.push_str(&serde_json::to_string(recipe)?);
    }
    output
        .encoder()
        .write_tag(Tag::ImageDescription, description.as_str())?;
    output
        .encoder()
        .write_tag(Tag::Software, "Strehl scene-linear master v1")?;
    output
        .encoder()
        .write_tag(Tag::IccProfile, IccBytes(&crate::icc::icc_srgb_v2(true)))?;
    output.write_data(&image.pixels)?;
    Ok(())
}

pub fn save_sdr_tiff(path: &Path, image: &LinearImage, recipe: &DevelopmentRecipe) -> Result<()> {
    image.validate_source_repairs(recipe)?;
    let pixels = image.render_sdr16(recipe)?;
    let description = format!(
        "sRGB (IEC 61966-2-1), BT.709/D65; Strehl development recipe: {}",
        serde_json::to_string(recipe)?
    );
    crate::publish::new_file(path, |file| {
        let mut buffered = BufWriter::new(file);
        {
            let mut encoder = TiffEncoder::new(&mut buffered)?;
            let mut output = encoder.new_image::<colortype::RGB16>(image.width, image.height)?;
            output
                .encoder()
                .write_tag(Tag::ImageDescription, description.as_str())?;
            output
                .encoder()
                .write_tag(Tag::Software, "Strehl development v1")?;
            output
                .encoder()
                .write_tag(Tag::IccProfile, IccBytes(&crate::icc::icc_srgb_v2(false)))?;
            output.write_data(&pixels)?;
        }
        buffered.flush().context("flushing completed SDR TIFF")
    })
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn hdr_baseline_matches_sdr_midtone_but_preserves_monotone_headroom() {
        let image = LinearImage {
            width: 8,
            height: 1,
            pixels: [0.001, 0.02, 0.18, 0.5, 0.99, 1.5, 3.0, 10.0]
                .into_iter()
                .flat_map(|x| [x; 3])
                .collect(),
            origin: ImageOrigin::SceneLinear,
            baseline: Some(DisplayBaseline {
                black: 0.0,
                white: 1.0,
                contrast: 0.55,
                exposure_gain: 1.0,
            }),
            baked_recipe: None,
        };
        let recipe = DevelopmentRecipe::default();
        let hdr: Vec<f32> = (0..8)
            .map(|i| image.developed_pixel(i, &recipe)[0])
            .collect();
        for (i, value) in hdr.iter().enumerate().take(5) {
            let sdr_linear = srgb_decode(image.display_pixel(i, &recipe)[0]);
            assert!((value - sdr_linear).abs() < 1e-6);
        }
        assert!(
            hdr.windows(2).all(|p| p[1] > p[0]),
            "HDR contrast folded highlight order"
        );
        assert!(hdr[7] > 1.0, "HDR was clipped to SDR white");
    }
}
