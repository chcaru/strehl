//! Bounded, deterministic metering for an editable development suggestion.
//!
//! This is an original photographic heuristic, not an ML model or an imitation
//! of another application's rendering. It never edits the master or annotations.
use anyhow::{Result, ensure};
use serde::Serialize;

use crate::{Adjustments, DevelopmentRecipe, ImageOrigin, LinearImage};

const SAMPLE_BUDGET: usize = 16_384;

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum AdaptiveIntent {
    Balance,
    RestoreHighlights,
}

#[derive(Debug, Clone, PartialEq, Serialize)]
pub struct HighlightDiagnosis {
    pub bright_fraction: f32,
    pub above_delivery_fraction: f32,
    /// Present only for an SDR input. A white channel in the stored TIFF is a
    /// limit of this input, not proof of clipping in the original camera RAW.
    pub stored_white_channel_fraction: Option<f32>,
    /// p90-p10 of unedited, display-placed source luminance at currently bright
    /// samples; not a texture/detail score or a sensor-clipping determination.
    pub bright_luminance_span: f32,
    pub assessment: String,
}

#[derive(Debug, Clone, PartialEq, Serialize)]
pub struct AdaptiveStatistics {
    pub sample_count: usize,
    pub image_pixels: u64,
    /// Linear, display-placed luminance at p1, p10, p50, p90, p99.
    pub luminance_percentiles: [f32; 5],
    /// p90 / p10; the floor prevents black samples from creating infinities.
    pub dynamic_range_stops: f32,
    /// Sample fraction below linear luminance 0.018.
    pub dark_fraction: f32,
    /// Sample fraction with any developed channel above 1.0, before display clamp.
    pub above_white_fraction: f32,
    /// Working-space linear channel ceiling: HDR peak/reference white, or 1 for SDR.
    pub delivery_ceiling: f32,
    /// Fraction of non-dark samples with (max-min)/max above 0.8.
    pub saturated_color_fraction: f32,
    /// Difference between p50/p90 metering on interleaved spatial sample subsets.
    pub sampling_disagreement_stops: f32,
}

#[derive(Debug, Clone, PartialEq, Serialize)]
pub struct AdaptiveChange {
    pub control: String,
    pub before: f32,
    pub after: f32,
    pub reason: String,
}

#[derive(Debug, Clone, PartialEq, Serialize)]
pub struct AdaptiveSuggestion {
    pub base: DevelopmentRecipe,
    pub suggested: DevelopmentRecipe,
    pub stats: AdaptiveStatistics,
    pub after_stats: AdaptiveStatistics,
    pub target_region: Option<String>,
    pub intent: AdaptiveIntent,
    pub highlights: HighlightDiagnosis,
    pub changes: Vec<AdaptiveChange>,
    pub limitations: Vec<String>,
}

impl AdaptiveSuggestion {
    /// Blend against the frozen input, never against the last slider position.
    /// There is no image scan here. Only the addressed adjustment controls change;
    /// shapes, source constraints, other regions and HDR settings stay unchanged.
    pub fn recipe_at(&self, strength: f32) -> Result<DevelopmentRecipe> {
        ensure!(
            strength.is_finite() && (0.0..=1.0).contains(&strength),
            "adaptive strength must be finite and in 0..=1"
        );
        if strength == 0.0 {
            return Ok(self.base.clone());
        }
        if strength == 1.0 {
            return Ok(self.suggested.clone());
        }
        let mut recipe = self.base.clone();
        let target = self.target_region.as_deref();
        *adjustment_mut(&mut recipe, target)? = interpolate(
            adjustment(&self.base, target)?,
            adjustment(&self.suggested, target)?,
            strength,
        );
        recipe.validate()?;
        Ok(recipe)
    }
}

/// Meter at most 16,384 stratified image samples and propose ordinary editable
/// global controls. Local adjustments remain intact but are deliberately excluded
/// from metering: a painted bright patch must not cause a compensating global edit.
///
/// Call on a loaded/validated master or linear preview on a worker. Structural
/// checks and sampled finite checks are bounded here; this is not a replacement
/// for validating every source sample when importing an image.
pub fn analyze_adaptive(
    image: &LinearImage,
    base: &DevelopmentRecipe,
) -> Result<AdaptiveSuggestion> {
    analyze(image, base, None, AdaptiveIntent::Balance)
}

/// Analyze an existing annotation in output-image coordinates. Its actual
/// feather and all other edits participate in metering. This changes only the
/// selected region's ordinary, editable photo controls, never its source span.
pub fn analyze_adaptive_region(
    image: &LinearImage,
    base: &DevelopmentRecipe,
    region_id: &str,
    intent: AdaptiveIntent,
) -> Result<AdaptiveSuggestion> {
    analyze(image, base, Some(region_id), intent)
}

fn analyze(
    image: &LinearImage,
    base: &DevelopmentRecipe,
    target: Option<&str>,
    intent: AdaptiveIntent,
) -> Result<AdaptiveSuggestion> {
    base.validate()?;
    ensure!(
        image.pixels.len() == crate::image::image_samples(image.width, image.height)?,
        "invalid image sample count"
    );
    if let Some(baseline) = image.baseline {
        baseline.validate()?;
    }
    let indices = scoped_indices(image, base, target)?;
    let mut metering = base.clone();
    if target.is_none() {
        metering.regions.clear();
    }
    let before = sample_pixels(image, &metering, &indices)?;
    let ceiling = match image.origin {
        ImageOrigin::SceneLinear => base.hdr.peak_nits / base.hdr.reference_white_nits,
        ImageOrigin::DisplayReferred => 1.0,
    };
    let mut stats = statistics(&before, u64::from(image.width) * u64::from(image.height));
    stats.delivery_ceiling = ceiling;
    let [_, p10, p50, p90, p99] = stats.luminance_percentiles;
    let mut limitations = vec![
        "A deterministic starting point, not subject recognition or an AI model.".into(),
        if target.is_some() {
            "Metering includes the selected region's feather and existing photo edits; only that region's controls change. Review its boundary as well as the complete photograph.".into()
        } else {
            "Metering uses bounded spatial samples and ignores local edits; review the complete photograph.".into()
        },
    ];
    if image.origin == ImageOrigin::DisplayReferred {
        limitations.push(
            "This SDR source has no recoverable recorded headroom beyond its existing white."
                .into(),
        );
    } else {
        limitations.push(format!(
            "HDR metering preserves light above diffuse white up to the {:.2} linear peak/reference ratio. Inspect on an HDR display or in the HDR export; SDR presentation may clip this headroom.",
            ceiling
        ));
    }
    if !base.regions.is_empty() && target.is_none() {
        limitations
            .push("All existing region adjustments and source constraints are retained.".into());
    }

    let flat = p90 - p10 < 0.002 || stats.dynamic_range_stops < 0.18;
    let too_dark = p99 < 0.008;
    let low_key = stats.dark_fraction > 0.65;
    let high_key = p10 > 0.45 && p50 > 0.65;
    // A separated black/white composition is not necessarily underexposed
    // merely because its median lands in the dark mode.
    let separated_key = p50 < 0.05 && p90 > 0.65;
    let unstable = stats.sampling_disagreement_stops > 0.75;
    let original = adjustment(base, target)?;
    let mut wanted = original;
    let mut reasons = Vec::new();
    let diagnosis = diagnose_highlights(image, &indices, &before, ceiling);
    if intent == AdaptiveIntent::RestoreHighlights {
        let bright = channel_quantile(&before, 0.95);
        if bright < 0.8 {
            limitations.push("The selected region has no substantial bright end to compress; its controls are unchanged.".into());
        } else {
            // This is an explicit regional request to lower distracting light,
            // unlike global balancing which preserves HDR light above white.
            let goal = (bright * 0.80).clamp(0.70, 0.90);
            wanted = fit_highlights(
                image,
                &metering,
                &indices,
                target,
                wanted,
                |pixels| channel_quantile(pixels, 0.95) <= goal,
                85.0,
            )?;
            reasons.push(("highlights", format!(
                "The region's bright-channel 95th percentile is {bright:.3}; compress toward {goal:.3} without lowering its exposure or changing its color controls. This redistributes existing light; it cannot recreate missing texture."
            )));
            limitations.push(diagnosis.assessment.clone());
        }
    } else if flat || too_dark || unstable {
        limitations.push(if too_dark {
            "Almost all sampled light is near black; exposure and noise cannot be separated reliably, so controls are unchanged.".into()
        } else if flat {
            "The sampled tonal range is nearly uniform; no contrast, exposure or color boost is suggested.".into()
        } else {
            format!("Interleaved sample sets differ by {:.2} stops; metering is too sensitive for a whole-image suggestion.", stats.sampling_disagreement_stops)
        });
    } else {
        if low_key || high_key || separated_key {
            limitations.push(format!(
                "{} composition: retain its exposure placement instead of forcing the scene toward middle gray.",
                if low_key { "Predominantly dark" }
                else if high_key { "Predominantly bright" }
                else { "Strongly separated light/dark" }
            ));
        } else {
            let exposure = if p50 < 0.16 {
                (0.16 / p50.max(1e-6)).log2().min(0.65)
            } else if p50 > 0.32 {
                (0.32 / p50).log2().max(-0.35)
            } else {
                0.0
            };
            add(&mut wanted.exposure, exposure, -8.0, 8.0);
            reasons.push(("exposure", format!(
                "Median linear luminance is {p50:.3}; bring ordinary middle tones toward 0.16–0.32, limiting an upward move to 0.65 stops and protecting highlights separately."
            )));
        }
        // Restrained contrast is useful only when the central range has room.
        // In particular, do not steepen an already wide shadow/highlight scene.
        let contrast = if low_key || high_key || separated_key {
            0.0
        } else {
            (4.0 - stats.dynamic_range_stops).clamp(0.0, 2.0) * 5.0
        };
        add(&mut wanted.contrast, contrast, -100.0, 100.0);
        reasons.push(("contrast", format!(
            "The middle 80% spans {:.2} stops; add at most 10 contrast points only when that span is narrow.",
            stats.dynamic_range_stops
        )));
        let shadows = if !low_key && !high_key && !separated_key && p10 > 0.001 && p10 < 0.028 {
            (0.028 / p10).log2().mul_add(12.0, 0.0).clamp(0.0, 24.0)
        } else {
            0.0
        };
        add(&mut wanted.shadows, shadows, -100.0, 100.0);
        reasons.push(("shadows", format!(
            "The darker tenth is at {p10:.4} linear luminance; lift only a populated shadow range, keeping black-background scenes unchanged."
        )));

        // Meter highlights again after proposed exposure/contrast/shadow changes.
        // This is an editable compression, not recovery of sensor-clipped detail.
        let mut interim = metering.clone();
        *adjustment_mut(&mut interim, target)? = wanted;
        let interim_pixels = sample_pixels(image, &interim, &indices)?;
        let mut channels: Vec<f32> = interim_pixels
            .iter()
            .map(|p| p.iter().copied().fold(0.0, f32::max))
            .collect();
        channels.sort_unstable_by(f32::total_cmp);
        let bright = quantile(&channels, 0.99);
        let knee = ceiling * 0.88;
        let highlights = -(bright.max(knee) / knee)
            .log2()
            .mul_add(30.0, 0.0)
            .min(50.0);
        add(&mut wanted.highlights, highlights, -100.0, 100.0);
        reasons.push(("highlights", format!(
            "The bright-channel 99th percentile would be {bright:.3}; compress only above the {knee:.3} shoulder near the selected delivery ceiling."
        )));
        let white_limit = ceiling * 1.25;
        let whites = if bright > white_limit {
            -(bright / white_limit).log2().mul_add(8.0, 0.0).min(10.0)
        } else {
            0.0
        };
        add(&mut wanted.whites, whites, -100.0, 100.0);
        reasons.push(("whites", format!(
            "The same bright-channel percentile is {bright:.3}; reserve additional white-end compression for values above {white_limit:.3}."
        )));
        // Never infer a gray illuminant from the subject's colors. Vibrance's
        // existing per-pixel saturation mask leaves strongly colored pixels alone.
        let lit = before
            .iter()
            .filter(|&&p| crate::recipe::luma(p) > 0.018)
            .count();
        let colorful = before
            .iter()
            .filter(|&&p| {
                let span = p.iter().copied().fold(f32::NEG_INFINITY, f32::max)
                    - p.iter().copied().fold(f32::INFINITY, f32::min);
                // Relative chroma alone amplifies tiny channel differences in
                // dark gray. Require both relative and absolute color support.
                (0.1..0.95).contains(&chroma(p)) && span >= 0.035 && crate::recipe::luma(p) > 0.02
            })
            .count();
        let color_fraction = colorful as f32 / lit.max(1) as f32;
        let color_present = color_fraction >= 0.05;
        if color_present {
            // The rendering operator already suppresses the lift per pixel as
            // chroma rises. A second squared scene-wide mask previously reduced
            // the entire insect photograph to a 0.14-point color edit.
            let vibrance = 24.0 * color_fraction.sqrt();
            add(&mut wanted.vibrance, vibrance, -100.0, 100.0);
        }
        reasons.push(("vibrance", format!(
            "{:.1}% of non-dark samples have adjustable color (relative chroma 0.10–0.95 and channel span at least 0.035); require 5% support and scale a maximum 24-point vibrance lift by that support. The color operator protects already-saturated pixels individually; {:.1}% of this scene is strongly saturated.",
            color_fraction * 100.0,
            stats.saturated_color_fraction * 100.0
        )));
    }

    // Check the actual operators, rather than assuming the heuristic's direction.
    // Protect the actual upper tail first, instead of shrinking all useful edits
    // because a few bright colored samples reach the delivery ceiling. Back off
    // the whole proposal only if bounded highlight compression cannot protect it.
    let mut accepted = wanted;
    let mut accepted_scale = 1.0;
    let original_clip = clipped_channels(&before, ceiling);
    if accepted != original {
        let mut found = false;
        for scale in [1.0, 0.75, 0.5, 0.25, 0.125] {
            let mut candidate = interpolate(original, wanted, scale);
            candidate = fit_highlights(
                image,
                &metering,
                &indices,
                target,
                candidate,
                |pixels| clipped_channels(pixels, ceiling) <= original_clip,
                60.0,
            )?;
            if !monotone(candidate) {
                continue;
            }
            let mut recipe = metering.clone();
            *adjustment_mut(&mut recipe, target)? = candidate;
            let after = sample_pixels(image, &recipe, &indices)?;
            if clipped_channels(&after, ceiling) <= original_clip {
                accepted = candidate;
                accepted_scale = scale;
                found = true;
                break;
            }
        }
        if !found {
            accepted = original;
            accepted_scale = 0.0;
        }
    }
    if accepted_scale < 1.0 {
        limitations.push(format!(
            "The sampled clipping and monotonic-tone guard reduced the suggestion to {:.0}% of its initial strength.",
            accepted_scale * 100.0
        ));
    }
    if stats.above_white_fraction > 0.0 {
        limitations.push(format!(
            "{:.2}% of sampled pixels have a channel above display white; this is rendering headroom, not evidence that sensor-clipped detail exists.",
            stats.above_white_fraction * 100.0
        ));
    }
    let mut suggested = base.clone();
    *adjustment_mut(&mut suggested, target)? = accepted;
    suggested.validate()?;
    // Compression can be selected by the actual clipping guard even when the
    // percentile-based initial shoulder was zero.
    if accepted.highlights != original.highlights
        && !reasons.iter().any(|(name, _)| *name == "highlights")
    {
        reasons.push((
            "highlights",
            "Protect the sampled delivery ceiling while retaining the other proposed controls."
                .into(),
        ));
    }
    let mut after_metering = metering.clone();
    *adjustment_mut(&mut after_metering, target)? = accepted;
    let after = sample_pixels(image, &after_metering, &indices)?;
    let mut after_stats = statistics(&after, stats.image_pixels);
    after_stats.delivery_ceiling = ceiling;
    let changes = reasons
        .into_iter()
        .filter_map(|(name, reason)| {
            let before = control(original, name);
            let after = control(accepted, name);
            (before != after).then(|| AdaptiveChange {
                control: name.into(),
                before,
                after,
                reason,
            })
        })
        .collect();
    Ok(AdaptiveSuggestion {
        base: base.clone(),
        suggested,
        stats,
        after_stats,
        target_region: target.map(str::to_owned),
        intent,
        highlights: diagnosis,
        changes,
        limitations,
    })
}

fn adjustment(recipe: &DevelopmentRecipe, target: Option<&str>) -> Result<Adjustments> {
    match target {
        None => Ok(recipe.global),
        Some(id) => Ok(recipe
            .regions
            .iter()
            .find(|r| r.id == id)
            .ok_or_else(|| anyhow::anyhow!("Adaptive region does not exist"))?
            .adjustments),
    }
}

fn adjustment_mut<'a>(
    recipe: &'a mut DevelopmentRecipe,
    target: Option<&str>,
) -> Result<&'a mut Adjustments> {
    match target {
        None => Ok(&mut recipe.global),
        Some(id) => Ok(&mut recipe
            .regions
            .iter_mut()
            .find(|r| r.id == id)
            .ok_or_else(|| anyhow::anyhow!("Adaptive region does not exist"))?
            .adjustments),
    }
}

fn scoped_indices(
    image: &LinearImage,
    recipe: &DevelopmentRecipe,
    target: Option<&str>,
) -> Result<Vec<usize>> {
    let width = image.width as usize;
    let height = image.height as usize;
    let Some(id) = target else {
        return Ok(sample_indices(width, height));
    };
    let region = recipe
        .regions
        .iter()
        .find(|r| r.id == id)
        .ok_or_else(|| anyhow::anyhow!("Adaptive region does not exist"))?;
    ensure!(
        region.enabled,
        "Enable the selected region before analyzing it"
    );
    let (min, max) = region.shape.bounds();
    let x0 = (min[0] * width as f32).floor() as usize;
    let y0 = (min[1] * height as f32).floor() as usize;
    let x1 = ((max[0] * width as f32).ceil() as usize).min(width);
    let y1 = ((max[1] * height as f32).ceil() as usize).min(height);
    ensure!(
        x1 > x0 && y1 > y0,
        "The region is smaller than this image's pixels"
    );
    let rw = x1 - x0;
    let indices: Vec<_> = sample_indices(rw, y1 - y0)
        .into_iter()
        .filter_map(|i| {
            let x = x0 + i % rw;
            let y = y0 + i / rw;
            let uv = [
                (x as f32 + 0.5) / width as f32,
                (y as f32 + 0.5) / height as f32,
            ];
            (region.shape.weight(uv, region.feather) >= 0.5).then_some(y * width + x)
        })
        .collect();
    ensure!(
        !indices.is_empty(),
        "The region has no pixel centers with sufficient feather weight; enlarge it"
    );
    Ok(indices)
}

fn channel_quantile(pixels: &[[f32; 3]], q: f32) -> f32 {
    let mut values: Vec<_> = pixels
        .iter()
        .map(|p| p.iter().copied().fold(0.0, f32::max))
        .collect();
    values.sort_unstable_by(f32::total_cmp);
    quantile(&values, q)
}

/// Find the least extra highlight compression that satisfies a measurable
/// output constraint. Bounded to ten bisections over the existing tone operator.
fn fit_highlights(
    image: &LinearImage,
    recipe: &DevelopmentRecipe,
    indices: &[usize],
    target: Option<&str>,
    initial: Adjustments,
    accepts: impl Fn(&[[f32; 3]]) -> bool,
    max_delta: f32,
) -> Result<Adjustments> {
    let mut probe = recipe.clone();
    *adjustment_mut(&mut probe, target)? = initial;
    if accepts(&sample_pixels(image, &probe, indices)?) {
        return Ok(initial);
    }
    let mut limit = initial;
    limit.highlights = (initial.highlights - max_delta).max(-100.0);
    *adjustment_mut(&mut probe, target)? = limit;
    if !monotone(limit) || !accepts(&sample_pixels(image, &probe, indices)?) {
        // For a deliberate regional request the bounded maximum is still useful;
        // the outer clipping guard decides whether it is safe to publish.
        return Ok(if monotone(limit) { limit } else { initial });
    }
    let mut low = 0.0;
    let mut high = 1.0;
    for _ in 0..10 {
        let t = (low + high) * 0.5;
        let mut candidate = initial;
        candidate.highlights = initial.highlights + (limit.highlights - initial.highlights) * t;
        *adjustment_mut(&mut probe, target)? = candidate;
        if accepts(&sample_pixels(image, &probe, indices)?) {
            high = t;
        } else {
            low = t;
        }
    }
    limit.highlights = initial.highlights + (limit.highlights - initial.highlights) * high;
    Ok(limit)
}

fn diagnose_highlights(
    image: &LinearImage,
    indices: &[usize],
    pixels: &[[f32; 3]],
    ceiling: f32,
) -> HighlightDiagnosis {
    let neutral = DevelopmentRecipe::default();
    let mut bright: Vec<_> = pixels
        .iter()
        .zip(indices)
        .filter(|(p, _)| p.iter().any(|&v| v >= 0.8))
        .map(|(_, &index)| crate::recipe::luma(image.developed_pixel(index, &neutral)))
        .collect();
    bright.sort_unstable_by(f32::total_cmp);
    let white = (image.origin == ImageOrigin::DisplayReferred).then(|| {
        indices
            .iter()
            .filter(|&&i| image.pixels[i * 3..i * 3 + 3].iter().any(|&c| c >= 0.9995))
            .count() as f32
            / indices.len() as f32
    });
    let span = if bright.len() > 1 {
        quantile(&bright, 0.9) - quantile(&bright, 0.1)
    } else {
        0.0
    };
    let assessment = if white.is_some_and(|v| v > 0.01) {
        format!(
            "{:.1}% of sampled SDR pixels have a channel at or near stored white. Lowering brightness cannot restore missing channel values or texture; use the linear master or another capture if the source itself is clipped.",
            white.unwrap() * 100.0
        )
    } else if span > 0.01 {
        "The stored bright samples contain tonal variation that compression can make easier to inspect. This does not establish that sensor-clipped detail can be recovered.".into()
    } else {
        "Little variation was measured in the bright samples. This can lower their brightness, but it cannot invent texture or determine whether the original capture clipped.".into()
    };
    HighlightDiagnosis {
        bright_fraction: bright.len() as f32 / pixels.len() as f32,
        above_delivery_fraction: pixels
            .iter()
            .filter(|p| p.iter().any(|&v| v > ceiling))
            .count() as f32
            / pixels.len() as f32,
        stored_white_channel_fraction: white,
        bright_luminance_span: span,
        assessment,
    }
}

fn add(value: &mut f32, delta: f32, min: f32, max: f32) {
    *value = (*value + delta).clamp(min, max);
}

fn control(a: Adjustments, name: &str) -> f32 {
    match name {
        "exposure" => a.exposure,
        "contrast" => a.contrast,
        "shadows" => a.shadows,
        "highlights" => a.highlights,
        "whites" => a.whites,
        "vibrance" => a.vibrance,
        _ => unreachable!("only adaptive controls have reasons"),
    }
}

fn interpolate(a: Adjustments, b: Adjustments, t: f32) -> Adjustments {
    let mix = |x, y| if x == y { x } else { x + (y - x) * t };
    Adjustments {
        exposure: mix(a.exposure, b.exposure),
        contrast: mix(a.contrast, b.contrast),
        highlights: mix(a.highlights, b.highlights),
        shadows: mix(a.shadows, b.shadows),
        whites: mix(a.whites, b.whites),
        blacks: a.blacks,
        vibrance: mix(a.vibrance, b.vibrance),
        saturation: a.saturation,
        temperature: a.temperature,
        tint: a.tint,
    }
}

fn sample_indices(width: usize, height: usize) -> Vec<usize> {
    if width * height <= SAMPLE_BUDGET {
        return (0..width * height).collect();
    }
    let columns = ((SAMPLE_BUDGET as f64 * width as f64 / height as f64)
        .sqrt()
        .round() as usize)
        .clamp(1, width.min(SAMPLE_BUDGET));
    let rows = (SAMPLE_BUDGET / columns).clamp(1, height);
    let mut indices = Vec::with_capacity(columns * rows);
    for y in 0..rows {
        for x in 0..columns {
            let x0 = x * width / columns;
            let x1 = (x + 1) * width / columns;
            let y0 = y * height / rows;
            let y1 = (y + 1) * height / rows;
            // Deterministic jitter avoids always sampling one phase of a mesh.
            let seed = ((y * columns + x) as u64).wrapping_add(0x9e3779b97f4a7c15);
            let hash = (seed ^ (seed >> 30)).wrapping_mul(0xbf58476d1ce4e5b9);
            let sx = x0 + (hash as usize % (x1 - x0));
            let sy = y0 + ((hash >> 32) as usize % (y1 - y0));
            indices.push(sy * width + sx);
        }
    }
    indices
}

fn sample_pixels(
    image: &LinearImage,
    recipe: &DevelopmentRecipe,
    indices: &[usize],
) -> Result<Vec<[f32; 3]>> {
    indices
        .iter()
        .map(|&i| {
            let p = image.developed_pixel(i, recipe);
            ensure!(
                p.iter().all(|c| c.is_finite()),
                "adaptive sample contains nonfinite light"
            );
            Ok(p)
        })
        .collect()
}

fn quantile(sorted: &[f32], fraction: f32) -> f32 {
    sorted[((sorted.len() - 1) as f32 * fraction).round() as usize]
}

fn chroma(p: [f32; 3]) -> f32 {
    let max = p.into_iter().fold(0.0, f32::max);
    let min = p.into_iter().fold(f32::MAX, f32::min).max(0.0);
    if max > 1e-8 {
        ((max - min) / max).clamp(0.0, 1.0)
    } else {
        0.0
    }
}

fn statistics(pixels: &[[f32; 3]], image_pixels: u64) -> AdaptiveStatistics {
    let mut y: Vec<f32> = pixels
        .iter()
        .map(|&p| crate::recipe::luma(p).max(0.0))
        .collect();
    let mut halves = [Vec::new(), Vec::new()];
    for (i, &v) in y.iter().enumerate() {
        halves[i % 2].push(v);
    }
    y.sort_unstable_by(f32::total_cmp);
    for half in &mut halves {
        half.sort_unstable_by(f32::total_cmp);
    }
    let disagreement = if halves[1].is_empty() {
        0.0
    } else {
        [0.5, 0.9]
            .into_iter()
            .map(|q| {
                (quantile(&halves[0], q).max(0.001) / quantile(&halves[1], q).max(0.001))
                    .log2()
                    .abs()
            })
            .fold(0.0, f32::max)
    };
    let q = [0.01, 0.1, 0.5, 0.9, 0.99].map(|f| quantile(&y, f));
    let lit: Vec<_> = pixels
        .iter()
        .filter(|p| crate::recipe::luma(**p) > 0.018)
        .collect();
    AdaptiveStatistics {
        sample_count: pixels.len(),
        image_pixels,
        luminance_percentiles: q,
        dynamic_range_stops: (q[3].max(0.0001) / q[1].max(0.0001)).log2().max(0.0),
        dark_fraction: y.iter().filter(|&&v| v < 0.018).count() as f32 / y.len() as f32,
        above_white_fraction: pixels.iter().filter(|p| p.iter().any(|&v| v > 1.0)).count() as f32
            / y.len() as f32,
        delivery_ceiling: 1.0,
        saturated_color_fraction: if lit.is_empty() {
            0.0
        } else {
            lit.iter().filter(|&&p| chroma(*p) > 0.8).count() as f32 / lit.len() as f32
        },
        sampling_disagreement_stops: disagreement,
    }
}

fn clipped_channels(pixels: &[[f32; 3]], ceiling: f32) -> usize {
    pixels.iter().flatten().filter(|&&v| v > ceiling).count()
}

fn monotone(a: Adjustments) -> bool {
    let mut last = 0.0;
    for i in 0..=512 {
        let y = (-20.0 + i as f32 * 26.0 / 512.0).exp2();
        let mapped = crate::recipe::luma(a.apply([y; 3], 1.0));
        if !mapped.is_finite() || mapped < last {
            return false;
        }
        last = mapped;
    }
    true
}
