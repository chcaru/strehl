//! Export as stages: develop -> f32 buffer -> resize -> output sharpening ->
//! scale bar -> encode.
//!
//! With no stage requested the development is fused into the encoder's loop,
//! exactly as before P7, so option-free exports keep their bytes and their
//! memory (`tests/export-freeze.rs`). With a stage, the photograph is first
//! developed into an f32 buffer of output values; linear stages convert it to
//! linear light in the output primaries once.
use crate::{
    Crop, DevelopmentRecipe, ExportSettings, LinearImage, OutputColorSpace, PreparedRecipe,
    ScaleBarStyle,
    color::decode_srgb,
    export::check_cancel,
    image::srgb_encode,
    resample::{Resize, catmull_rom, resize_rgb},
    scale_bar::{Burn, ScaleBarReport, burn_scale_bar, scale_bar_font},
    sharpen::{Coding, sharpen},
};
use anyhow::{Result, ensure};
use rayon::prelude::*;
use std::sync::atomic::AtomicBool;

/// How output pixels map to the photograph.
#[derive(Clone, Copy)]
pub(crate) enum Geometry {
    Full,
    /// An unturned crop: output pixel (x, y) is source pixel (x0 + x, y0 + y).
    Window {
        x0: u32,
        y0: u32,
    },
    /// A straightened crop, sampled with Catmull-Rom in linear light.
    Turned {
        centre: [f64; 2],
        cos: f64,
        sin: f64,
        half: [f64; 2],
    },
}

pub(crate) struct Layout {
    pub geometry: Geometry,
    /// Size after the crop, before any resize.
    pub developed: [u32; 2],
    /// Final size.
    pub output: [u32; 2],
}

impl Layout {
    pub fn new(image: &LinearImage, crop: Option<&Crop>, resize: Option<&Resize>) -> Result<Self> {
        let (geometry, developed) = match crop {
            None => (Geometry::Full, [image.width, image.height]),
            Some(crop) => {
                crop.validate()?;
                ensure!(
                    crop.fits(image.width, image.height),
                    "the straightened crop extends past the photograph; shrink it to fit"
                );
                let size = crop.output_size(image.width, image.height);
                if crop.angle_deg == 0.0 {
                    let [x0, y0, ..] = crop.pixel_rect(image.width, image.height);
                    (Geometry::Window { x0, y0 }, size)
                } else {
                    let centre = [
                        (f64::from(crop.min[0]) + f64::from(crop.max[0]))
                            * 0.5
                            * f64::from(image.width),
                        (f64::from(crop.min[1]) + f64::from(crop.max[1]))
                            * 0.5
                            * f64::from(image.height),
                    ];
                    let (sin, cos) = f64::from(crop.angle_deg).to_radians().sin_cos();
                    (
                        Geometry::Turned {
                            centre,
                            cos,
                            sin,
                            half: size.map(|n| f64::from(n) * 0.5),
                        },
                        size,
                    )
                }
            }
        };
        let output = resize
            .and_then(|r| r.target(developed))
            .unwrap_or(developed);
        Ok(Self {
            geometry,
            developed,
            output,
        })
    }

    /// Source sample and full-photograph coordinate for a developed pixel.
    #[inline]
    pub fn sample(&self, image: &LinearImage, x: u32, y: u32) -> ([f32; 3], [f32; 2]) {
        match self.geometry {
            Geometry::Full => image.raw_uv(y as usize * image.width as usize + x as usize),
            Geometry::Window { x0, y0 } => {
                image.raw_uv((y0 + y) as usize * image.width as usize + (x0 + x) as usize)
            }
            Geometry::Turned {
                centre,
                cos,
                sin,
                half,
            } => {
                let d = [f64::from(x) + 0.5 - half[0], f64::from(y) + 0.5 - half[1]];
                let p = [
                    centre[0] + cos * d[0] - sin * d[1],
                    centre[1] + sin * d[0] + cos * d[1],
                ];
                let raw = catmull_rom(
                    &image.pixels,
                    image.width,
                    image.height,
                    p[0] - 0.5,
                    p[1] - 0.5,
                );
                (
                    raw,
                    [
                        (p[0] / f64::from(image.width)) as f32,
                        (p[1] / f64::from(image.height)) as f32,
                    ],
                )
            }
        }
    }

    /// Source pixel index for a developed pixel, for masks (nearest).
    pub fn nearest(&self, image: &LinearImage, x: u32, y: u32) -> usize {
        let (w, h) = (image.width as usize, image.height as usize);
        match self.geometry {
            Geometry::Full => y as usize * w + x as usize,
            Geometry::Window { x0, y0 } => (y0 + y) as usize * w + (x0 + x) as usize,
            Geometry::Turned {
                centre,
                cos,
                sin,
                half,
            } => {
                let d = [f64::from(x) + 0.5 - half[0], f64::from(y) + 0.5 - half[1]];
                let px = (centre[0] + cos * d[0] - sin * d[1]).floor() as i64;
                let py = (centre[1] + sin * d[0] + cos * d[1]).floor() as i64;
                py.clamp(0, h as i64 - 1) as usize * w + px.clamp(0, w as i64 - 1) as usize
            }
        }
    }

    pub fn resized(&self) -> bool {
        self.output != self.developed
    }
}

/// What a developed value means.
#[derive(Clone, Copy, PartialEq)]
pub(crate) enum Domain {
    /// sRGB-coded display values in the output primaries, 0..1.
    Sdr(OutputColorSpace),
    /// Absolute light in the output primaries, nits, unclamped.
    Hdr(OutputColorSpace, f32),
}

impl Domain {
    pub fn space(self) -> OutputColorSpace {
        match self {
            Self::Sdr(s) | Self::Hdr(s, _) => s,
        }
    }
}

/// The pre-P7 SDR value of one source sample (`export::sdr_pixel`).
#[inline]
pub(crate) fn sdr_value(
    image: &LinearImage,
    recipe: &PreparedRecipe<'_>,
    space: OutputColorSpace,
    raw: [f32; 3],
    uv: [f32; 2],
) -> [f32; 3] {
    let p = image.display_sample(raw, uv, recipe);
    if space == OutputColorSpace::Srgb {
        return p;
    }
    space
        .convert_from_linear_srgb(p.map(decode_srgb))
        .map(srgb_encode)
}

#[inline]
pub(crate) fn develop_value(
    image: &LinearImage,
    recipe: &PreparedRecipe<'_>,
    domain: Domain,
    raw: [f32; 3],
    uv: [f32; 2],
) -> [f32; 3] {
    match domain {
        Domain::Sdr(space) => sdr_value(image, recipe, space, raw, uv),
        Domain::Hdr(space, white) => space
            .convert_from_linear_srgb(image.developed_sample(raw, uv, recipe))
            .map(|v| v * white),
    }
}

/// Stages beyond development that the settings and recipe ask for.
pub(crate) struct Stages {
    pub filter: crate::ResizeFilter,
    pub sharpen: Option<crate::OutputSharpening>,
    pub scale_bar: Option<(crate::ScaleBar, f64)>,
}

impl Stages {
    pub fn new(
        recipe: &DevelopmentRecipe,
        settings: &ExportSettings,
        layout: &Layout,
        um_per_px: Option<f64>,
    ) -> Result<Self> {
        let scale_bar = match (settings.scale_bar, recipe.scale_bar.filter(|b| b.enabled)) {
            (true, Some(bar)) => {
                let um = um_per_px.ok_or_else(|| {
                    anyhow::anyhow!(
                        "this export burns in a scale bar, but the subject has no scale calibration"
                    )
                })?;
                ensure!(
                    um.is_finite() && um > 0.0,
                    "the scale calibration must be a positive number of micrometres per pixel"
                );
                // Output pixels after crop are source pixels; a resize widens them.
                let per_output = um * f64::from(layout.developed[0]) / f64::from(layout.output[0]);
                Some((bar, per_output))
            }
            _ => None,
        };
        Ok(Self {
            filter: settings.resize.map(|r| r.filter).unwrap_or_default(),
            sharpen: settings.sharpen,
            scale_bar,
        })
    }

    pub fn any(&self, layout: &Layout) -> bool {
        layout.resized() || self.sharpen.is_some() || self.scale_bar.is_some()
    }
}

/// A developed photograph in memory.
pub(crate) struct Buffer {
    pub size: [u32; 2],
    pub pixels: Vec<f32>,
    /// False: SDR values are still sRGB-coded. HDR is always linear.
    pub linear: bool,
    pub alpha: Option<Vec<u8>>,
}

pub(crate) struct StageReport {
    pub scale_bar: Option<ScaleBarReport>,
    pub sharpened: bool,
}

/// Develop every output pixel into a buffer.
pub(crate) fn develop_buffer(
    image: &LinearImage,
    recipe: &PreparedRecipe<'_>,
    domain: Domain,
    layout: &Layout,
    coverage: Option<&[u8]>,
    cancel: &AtomicBool,
) -> Result<Buffer> {
    let [w, h] = layout.developed;
    let mut pixels = vec![0.0f32; w as usize * h as usize * 3];
    pixels
        .par_chunks_mut(w as usize * 3)
        .enumerate()
        .try_for_each(|(y, row)| -> Result<()> {
            check_cancel(cancel)?;
            for (x, out) in row.as_chunks_mut::<3>().0.iter_mut().enumerate() {
                let (raw, uv) = layout.sample(image, x as u32, y as u32);
                let p = develop_value(image, recipe, domain, raw, uv);
                ensure!(
                    p.iter().all(|v| v.is_finite()),
                    "development produced non-finite output samples"
                );
                *out = p;
            }
            Ok(())
        })?;
    let alpha = coverage.map(|mask| {
        (0..h)
            .flat_map(|y| (0..w).map(move |x| (x, y)))
            .map(|(x, y)| mask[layout.nearest(image, x, y)])
            .collect()
    });
    Ok(Buffer {
        size: layout.developed,
        pixels,
        linear: matches!(domain, Domain::Hdr(..)),
        alpha,
    })
}

impl Buffer {
    fn make_linear(&mut self) {
        if !self.linear {
            self.pixels
                .par_iter_mut()
                .for_each(|v| *v = decode_srgb(*v));
            self.linear = true;
        }
    }

    /// sRGB-coded values for SDR encoders.
    pub fn coded(&self, index: usize) -> [f32; 3] {
        let p = &self.pixels[index * 3..index * 3 + 3];
        if self.linear {
            [srgb_encode(p[0]), srgb_encode(p[1]), srgb_encode(p[2])]
        } else {
            [p[0], p[1], p[2]]
        }
    }
}

/// Resize, sharpen and burn in the scale bar, in that order.
pub(crate) fn run_stages(
    buffer: &mut Buffer,
    layout: &Layout,
    stages: &Stages,
    domain: Domain,
    cancel: &AtomicBool,
) -> Result<StageReport> {
    if layout.resized() {
        ensure!(
            buffer.alpha.is_none(),
            "transparent coverage cannot be resized yet; export it at full size"
        );
        buffer.make_linear();
        buffer.pixels = resize_rgb(
            &buffer.pixels,
            buffer.size,
            layout.output,
            stages.filter,
            cancel,
        )?;
        buffer.size = layout.output;
    }
    let space = domain.space();
    let mut sharpened = false;
    if let Some(settings) = stages.sharpen.as_ref().filter(|s| s.amount > 0.0) {
        buffer.make_linear();
        let coding = match domain {
            Domain::Sdr(_) => Coding::Srgb,
            Domain::Hdr(..) => Coding::Pq,
        };
        sharpen(
            &mut buffer.pixels,
            buffer.size,
            settings,
            coding,
            |p| space.luminance(p),
            cancel,
        )?;
        sharpened = true;
    }
    let mut scale_bar = None;
    if let Some((bar, um_per_px)) = &stages.scale_bar {
        buffer.make_linear();
        let level = match domain {
            Domain::Sdr(_) => 1.0,
            Domain::Hdr(_, white) => white,
        };
        let colour = match bar.style {
            ScaleBarStyle::Light => [level; 3],
            ScaleBarStyle::Dark => [0.0; 3],
        };
        let font = scale_bar_font();
        let mut burn = Burn {
            pixels: &mut buffer.pixels,
            alpha: buffer.alpha.as_deref_mut(),
            size: buffer.size,
        };
        scale_bar = Some(burn_scale_bar(
            &mut burn,
            bar,
            *um_per_px,
            colour,
            font.as_ref(),
        )?);
    }
    ensure!(
        buffer.pixels.iter().all(|v| v.is_finite()),
        "export stages produced non-finite output samples"
    );
    Ok(StageReport {
        scale_bar,
        sharpened,
    })
}
