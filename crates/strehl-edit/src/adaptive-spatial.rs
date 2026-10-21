//! Original deterministic spatial treatment. A small bilateral moment lattice
//! separates location from brightness; its coefficients are then frozen in the
//! recipe. This is not a trained model, segmentation, or detail reconstruction.
use super::*;
use crate::{AdaptiveParameters, AdaptiveToneRange, SpatialTreatment};

#[derive(Clone, Copy, Default)]
struct Moment {
    weight: f32,
    log: f32,
    square: f32,
    color: f32,
}
impl Moment {
    fn plus(self, other: Self, w: f32) -> Self {
        Self {
            weight: self.weight + other.weight * w,
            log: self.log + other.log * w,
            square: self.square + other.square * w,
            color: self.color + other.color * w,
        }
    }
    fn mean(self) -> f32 {
        self.log / self.weight.max(1e-10)
    }
}

fn blur(
    input: &[Moment],
    w: usize,
    h: usize,
    levels: usize,
    axis: usize,
    passes: usize,
) -> Vec<Moment> {
    let mut a = input.to_vec();
    let mut b = a.clone();
    for _ in 0..passes {
        for y in 0..h {
            for x in 0..w {
                for z in 0..levels {
                    let mut m = Moment::default();
                    for (delta, k) in [(-1, 0.25), (0, 0.5), (1, 0.25)] {
                        let xx = if axis == 0 {
                            (x as isize + delta).clamp(0, w as isize - 1) as usize
                        } else {
                            x
                        };
                        let yy = if axis == 1 {
                            (y as isize + delta).clamp(0, h as isize - 1) as usize
                        } else {
                            y
                        };
                        let zz = if axis == 2 {
                            (z as isize + delta).clamp(0, levels as isize - 1) as usize
                        } else {
                            z
                        };
                        m = m.plus(a[(yy * w + xx) * levels + zz], k);
                    }
                    b[(y * w + x) * levels + z] = m;
                }
            }
        }
        std::mem::swap(&mut a, &mut b);
    }
    a
}

fn working_pixel(image: &LinearImage, recipe: &DevelopmentRecipe, i: usize) -> [f32; 3] {
    let p = &image.pixels[i * 3..i * 3 + 3];
    let rgb = [p[0], p[1], p[2]];
    let placed = image.baseline.map_or(rgb, |b| b.place(rgb));
    recipe.apply_pixel(placed, pixel_uv(image, i))
}

fn pixel_uv(image: &LinearImage, i: usize) -> [f32; 2] {
    [
        ((i % image.width as usize) as f32 + 0.5) / image.width as f32,
        ((i / image.width as usize) as f32 + 0.5) / image.height as f32,
    ]
}

pub(super) fn analyze_spatial(
    image: &LinearImage,
    base: &DevelopmentRecipe,
    target: Option<&str>,
    parameters: AdaptiveParameters,
) -> Result<AdaptiveSuggestion> {
    base.validate()?;
    parameters.validate()?;
    ensure!(
        image.pixels.len() == crate::image::image_samples(image.width, image.height)?,
        "invalid image sample count"
    );
    if let Some(baseline) = image.baseline {
        baseline.validate()?;
    }
    let indices = scoped_indices(image, base, target)?;
    let mut metering = base.clone();
    metering.clear_adaptive_scope(target);
    if target.is_none() {
        metering.regions.clear();
        metering.spatial.clear();
    }
    let before = sample_pixels(image, &metering, &indices)?;
    let mut stats = statistics(&before, u64::from(image.width) * u64::from(image.height));
    let ceiling = match image.origin {
        ImageOrigin::SceneLinear => base.hdr.peak_nits / base.hdr.reference_white_nits,
        ImageOrigin::DisplayReferred => 1.0,
    };
    stats.delivery_ceiling = ceiling;
    let diagnosis = diagnose_highlights(image, &indices, &before, ceiling);
    let [_, p10, _, p90, p99] = stats.luminance_percentiles;
    let mut limitations=vec![
        "Spatial tone curves use local light and color statistics, not semantic recognition or a trained model. They cannot reconstruct missing texture.".into(),
        "The treatment preserves sampled working-light placement instead of raising global Exposure. Averages do not determine photographic quality; inspect the complete image and boundaries.".into(),
    ];
    if image.origin == ImageOrigin::DisplayReferred {
        limitations.push("This is an existing SDR photograph; clipped source channels have no recoverable HDR detail.".into());
    }
    let mut suggested = base.clone();
    suggested.clear_adaptive_scope(target);
    let mut changes = Vec::new();
    let flat = p90 - p10 < 0.002 || stats.dynamic_range_stops < 0.18;
    let dark = p99 < 0.008;
    let structure_enabled = !flat && !dark && stats.sampling_disagreement_stops <= 0.75;
    if (!structure_enabled && parameters.highlight_compression == 0.0)
        || (parameters.balance == 0.0
            && parameters.local_contrast == 0.0
            && parameters.color == 0.0
            && parameters.highlight_compression == 0.0)
    {
        limitations.push("There is insufficient sampled tonal variation for a spatial treatment, or all treatment controls are zero; ordinary controls remain unchanged.".into());
    } else {
        let field = build_field(
            image,
            &metering,
            &indices,
            target,
            parameters,
            ceiling,
            structure_enabled,
        )?;
        let max_tone = field
            .tone_ev
            .iter()
            .map(|v| (v + field.centering_ev).abs())
            .fold(0.0, f32::max);
        let max_color = field.color_gain.iter().copied().fold(1.0, f32::max);
        if max_tone > 0.002 || max_color > 1.001 {
            changes.push(AdaptiveChange { control:"spatial tone".into(),before:0.0,after:max_tone,reason:format!("{} × {} local tone curves distinguish location and input brightness; maximum unmasked correction {:.2} stops. Exposure and other manual sliders stay unchanged.",field.width,field.height,max_tone) });
            if max_color > 1.001 {
                changes.push(AdaptiveChange {control:"spatial color".into(),before:1.0,after:max_color,reason:"Color enrichment follows local color support; neutral, already saturated, and clipping-prone pixels are protected independently.".into()});
            }
            if parameters.tone_range != AdaptiveToneRange::All || parameters.shadow_protection > 0.0
            {
                limitations.push("Tonal focus and dark protection are smooth luminance weights, not semantic foreground/background masks. They constrain both local light and color; use a drawn region for spatial targeting.".into());
            }
            if parameters.highlight_compression > 0.0 {
                changes.push(AdaptiveChange { control: "bright-tone compression".into(), before: 0.0, after: parameters.highlight_compression, reason: "A bounded smooth shoulder lowers existing bright light after balancing, without compensating by lifting the rest of the image. It cannot recover clipped texture.".into() });
            }
            suggested.spatial.push(field);
        }
    }
    suggested.validate()?;
    let mut after_metering = metering.clone();
    if let Some(field) = suggested.adaptive_scope(target) {
        after_metering.spatial.push(field.clone());
    }
    let after = sample_pixels(image, &after_metering, &indices)?;
    let mut after_stats = statistics(&after, stats.image_pixels);
    after_stats.delivery_ceiling = ceiling;
    Ok(AdaptiveSuggestion {
        base: base.clone(),
        suggested,
        stats,
        after_stats,
        target_region: target.map(str::to_owned),
        intent: AdaptiveIntent::Balance,
        highlights: diagnosis,
        changes,
        limitations,
    })
}

fn build_field(
    image: &LinearImage,
    recipe: &DevelopmentRecipe,
    indices: &[usize],
    target: Option<&str>,
    parameters: AdaptiveParameters,
    ceiling: f32,
    structure_enabled: bool,
) -> Result<SpatialTreatment> {
    let bounds = target
        .and_then(|id| recipe.regions.iter().find(|r| r.id == id))
        .map_or([[0.0, 0.0], [1.0, 1.0]], |r| {
            let (a, b) = r.shape.bounds();
            [a, b]
        });
    let aspect = image.width as f32 * (bounds[1][0] - bounds[0][0])
        / (image.height as f32 * (bounds[1][1] - bounds[0][1]));
    let (w, h) = if aspect >= 1.0 {
        (20, (20.0 / aspect).round().clamp(2.0, 20.0) as usize)
    } else {
        ((20.0 * aspect).round().clamp(2.0, 20.0) as usize, 20)
    };
    let levels = 33;
    let log_min = -12.0;
    let log_max = 4.0;
    let mut grid = vec![Moment::default(); w * h * levels];
    let mut samples = Vec::with_capacity(indices.len());
    for &i in indices {
        let rgb = working_pixel(image, recipe, i);
        ensure!(
            rgb.iter().all(|v| v.is_finite()),
            "spatial sample contains nonfinite light"
        );
        let uv = pixel_uv(image, i);
        let y = crate::recipe::luma(rgb).max(0.0);
        samples.push((uv, rgb));
        if y < 0.002 {
            continue;
        }
        let log = y.log2();
        let x = ((uv[0] - bounds[0][0]) / (bounds[1][0] - bounds[0][0]) * (w - 1) as f32)
            .clamp(0.0, (w - 1) as f32);
        let yy = ((uv[1] - bounds[0][1]) / (bounds[1][1] - bounds[0][1]) * (h - 1) as f32)
            .clamp(0.0, (h - 1) as f32);
        let z = ((log - log_min) / (log_max - log_min) * (levels - 1) as f32)
            .clamp(0.0, (levels - 1) as f32);
        let ix = (x as usize).min(w - 2);
        let iy = (yy as usize).min(h - 2);
        let iz = (z as usize).min(levels - 2);
        let (tx, ty, tz) = (x - ix as f32, yy - iy as f32, z - iz as f32);
        let color = if (0.08..0.9).contains(&chroma(rgb))
            && rgb.into_iter().fold(0.0, f32::max) - rgb.into_iter().fold(f32::INFINITY, f32::min)
                > 0.025
        {
            1.0
        } else {
            0.0
        };
        let m = Moment {
            weight: 1.0,
            log,
            square: log * log,
            color,
        };
        for (dx, wx) in [(0, 1.0 - tx), (1, tx)] {
            for (dy, wy) in [(0, 1.0 - ty), (1, ty)] {
                for (dz, wz) in [(0, 1.0 - tz), (1, tz)] {
                    let k = ((iy + dy) * w + ix + dx) * levels + iz + dz;
                    grid[k] = grid[k].plus(m, wx * wy * wz);
                }
            }
        }
    }
    // Range slicing keeps distant brightness bands apart; spatial filtering
    // occurs only in this compact coefficient space, never on image pixels.
    let range = blur(&grid, w, h, levels, 2, 1);
    let fine = blur(&blur(&range, w, h, levels, 0, 2), w, h, levels, 1, 2);
    let broad = blur(&blur(&fine, w, h, levels, 0, 10), w, h, levels, 1, 10);
    let mut global = vec![Moment::default(); levels];
    for cell in range.chunks_exact(levels) {
        for (z, m) in cell.iter().enumerate() {
            global[z] = global[z].plus(*m, 1.0);
        }
    }
    let colored_population = global.iter().map(|m| m.color).sum::<f32>()
        / global.iter().map(|m| m.weight).sum::<f32>().max(1e-10);
    let mut tone_ev = vec![0.0; w * h * levels];
    let mut color_gain = vec![1.0; w * h];
    for (cell, cell_color) in color_gain.iter_mut().enumerate() {
        let mut color_sum = 0.0;
        let mut color_weight = 0.0;
        for (z, global_level) in global.iter().enumerate() {
            let i = cell * levels + z;
            let f = fine[i];
            let b = broad[i];
            if f.weight < 0.01 || b.weight < 0.01 {
                continue;
            }
            let log = log_min + (log_max - log_min) * z as f32 / (levels - 1) as f32;
            let variance = (f.square / f.weight - f.mean().powi(2)).max(0.0);
            let support = (variance / 0.08).clamp(0.0, 1.0);
            let contrast = (log - f.mean()).clamp(-0.7, 0.7) * parameters.local_contrast * 0.6;
            let balance =
                (global_level.mean() - b.mean()).clamp(-0.65, 0.65) * parameters.balance * 0.65;
            tone_ev[i] = quantize(((contrast + balance) * support).clamp(-0.45, 0.45));
            color_sum += f.color;
            color_weight += f.weight;
        }
        *cell_color = if colored_population >= 0.05 {
            quantize(
                1.0 + 0.14
                    * parameters.color
                    * (color_sum / color_weight.max(1e-10)).clamp(0.0, 1.0),
            )
        } else {
            1.0
        };
        // Limit slope, in addition to amplitude. No local curve may reverse
        // brightness ordering; this is an operator constraint, not a quality score.
        for z in 1..levels {
            let i = cell * levels + z;
            tone_ev[i] = tone_ev[i].max(tone_ev[i - 1] - 0.25);
        }
    }
    let mut field = SpatialTreatment {
        version: 1,
        target_region: target.map(str::to_owned),
        parameters,
        amount: 1.0,
        bounds,
        width: w as u32,
        height: h as u32,
        levels: levels as u32,
        log_min,
        log_max,
        tone_ev,
        color_gain,
        delivery_ceiling: ceiling,
        centering_ev: 0.0,
    };
    let selective =
        parameters.tone_range != AdaptiveToneRange::All || parameters.shadow_protection > 0.0;
    if !structure_enabled {
        field.tone_ev.fill(0.0);
        field.color_gain.fill(1.0);
    }
    let tone_source = selective.then(|| field.tone_ev.clone());
    let tone_weights: Vec<f32> = (0..levels)
        .map(|z| {
            let log = log_min + (log_max - log_min) * z as f32 / (levels - 1) as f32;
            tonal_weight(log, parameters)
        })
        .collect();
    if selective {
        // Color uses the same input-light slice as tone. No new full-resolution
        // mask or pixel buffer is introduced; legacy fields retain their layout.
        field.version = 2;
        field.color_gain = field
            .color_gain
            .iter()
            .flat_map(|gain| {
                tone_weights
                    .iter()
                    .map(move |weight| 1.0 + (gain - 1.0) * weight)
            })
            .collect();
    }
    // Solve only a light-placement offset, not an aesthetic target. Contrast
    // redistribution must not silently act like a global exposure increase.
    let original: f64 = samples
        .iter()
        .map(|(_, p)| crate::recipe::luma(*p) as f64)
        .sum();
    let scope = target.and_then(|id| recipe.regions.iter().find(|r| r.id == id));
    let mut lo = -0.5;
    let mut hi = 0.5;
    for _ in 0..14 {
        let candidate = (lo + hi) * 0.5;
        set_centering(&mut field, tone_source.as_deref(), &tone_weights, candidate);
        let after: f64 = samples
            .iter()
            .map(|(uv, p)| {
                crate::recipe::luma(field.apply(
                    *p,
                    *uv,
                    scope.map_or(1.0, |r| r.shape.weight(*uv, r.feather)),
                )) as f64
            })
            .sum();
        if after > original {
            hi = candidate;
        } else {
            lo = candidate;
        }
    }
    set_centering(
        &mut field,
        tone_source.as_deref(),
        &tone_weights,
        if (selective || parameters.highlight_compression > 0.0)
            && (!structure_enabled
                || (parameters.balance == 0.0 && parameters.local_contrast == 0.0))
        {
            0.0
        } else {
            (lo + hi) * 0.5
        },
    );
    if parameters.highlight_compression > 0.0 {
        // Apply after the centering solve: a highlight correction must never
        // cause a compensating lift elsewhere. Bake it into the frozen curves.
        for curve in field.tone_ev.chunks_exact_mut(levels) {
            for (z, ev) in curve.iter_mut().enumerate() {
                let light = (log_min + (log_max - log_min) * z as f32 / (levels - 1) as f32).exp2();
                let original_ev = *ev + field.centering_ev;
                let developed = light * original_ev.exp2();
                let knee = ceiling * 0.55;
                let excess = (developed - knee).max(0.0);
                let compressed = knee
                    + excess / (1.0 + parameters.highlight_compression * excess / (ceiling - knee));
                let correction = if excess > 0.0 {
                    (compressed / developed).log2().max(-0.75)
                } else {
                    0.0
                };
                *ev = (original_ev + correction).clamp(-1.0, 1.0);
            }
        }
        field.centering_ev = 0.0;
    }
    field.validate()?;
    Ok(field)
}

fn smooth_weight(x: f32) -> f32 {
    let x = x.clamp(0.0, 1.0);
    x * x * (3.0 - 2.0 * x)
}

fn tonal_weight(log: f32, parameters: AdaptiveParameters) -> f32 {
    let range = match parameters.tone_range {
        AdaptiveToneRange::All => 1.0,
        AdaptiveToneRange::Shadows => 1.0 - smooth_weight((log + 5.0) / 3.0),
        AdaptiveToneRange::Midtones => {
            smooth_weight((log + 6.0) / 3.0) * (1.0 - smooth_weight(log / 2.0))
        }
        AdaptiveToneRange::Highlights => smooth_weight((log + 3.0) / 3.0),
    };
    range * (1.0 - parameters.shadow_protection * (1.0 - smooth_weight((log + 6.0) / 3.0)))
}

fn set_centering(
    field: &mut SpatialTreatment,
    original: Option<&[f32]>,
    weights: &[f32],
    shift: f32,
) {
    if let Some(original) = original {
        for (i, ev) in field.tone_ev.iter_mut().enumerate() {
            *ev = (original[i] + shift) * weights[i % weights.len()];
        }
        field.centering_ev = 0.0;
    } else {
        field.centering_ev = shift;
    }
}

fn quantize(value: f32) -> f32 {
    (value * 4096.0).round() / 4096.0
}
