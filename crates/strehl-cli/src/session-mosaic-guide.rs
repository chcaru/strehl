use super::{GuideReceipt, MosaicGeometryConfig, MosaicGuide, hex};
use crate::session_cache::SourceCache;
use crate::session_focus::PassFocusEvidence;
use crate::session_input::{ResolvedSession, SourceIdentity};
use crate::session_sampling::SamplingDomain;
use anyhow::{Context, Result, ensure};
use sha2::{Digest, Sha256};
use std::collections::{BTreeMap, BTreeSet};
use strehl_core::align::Similarity;
use strehl_core::noise::Levels;
use strehl_core::plane::{PlaneGeometry, QuadSource};
use strehl_core::warpmap::WarpMap;
#[path = "session-mosaic-original-guide.rs"]
mod original;
pub(super) use original::original_boxes;

/// Builds an alignment diagnostic directly from original u16 CFA. The guide
/// averages the admissible regularized top-four focus band, or uses the regularized
/// peak when focus shape is ambiguous. Neither is a final merge or quality arm.
/// At most four assignments per guide pixel and one cached original are consumed;
/// there is no N-by-native-pixel intensity or aligned-frame volume.
#[allow(clippy::too_many_arguments)]
pub fn build_guide(
    session: &ResolvedSession,
    identities: &[SourceIdentity],
    pass: usize,
    map: &WarpMap,
    cache: &mut SourceCache,
    domain: SamplingDomain,
    focus: &PassFocusEvidence,
    config: &MosaicGeometryConfig,
    budget: usize,
) -> Result<MosaicGuide> {
    config.validate()?;
    domain.validate()?;
    let field = &focus.field;
    let track = session
        .passes
        .get(pass)
        .context("mosaic guide pass out of range")?;
    ensure!(
        identities.len() == session.len()
            && map.len() == session.len()
            && map.geometry() == domain.full
            && field.geometry.width == domain.width
            && field.geometry.height == domain.height
            && field.frames.len() == track.global_range.len(),
        "mosaic guide input census or coordinate gauge differs"
    );
    let field_pixels = domain.pixels();
    ensure!(
        [
            field.ordinal.len(),
            field.width_frames.len(),
            field.prominence_sigma.len(),
            field.perplexity.len(),
            field.top_global_indices.len(),
            field.flags.len(),
            field.covered.len(),
            field.usable.len(),
            focus.raw_coverage.len()
        ]
        .into_iter()
        .all(|n| n == field_pixels),
        "mosaic guide focus evidence buffer length mismatch"
    );
    for (ordinal, frame) in field.frames.iter().enumerate() {
        ensure!(
            frame.global_index == track.global_range.start + ordinal,
            "mosaic guide focus frame order differs from acquisition order"
        );
    }
    let step = domain
        .width
        .max(domain.height)
        .div_ceil(config.guide_max_side)
        .max(1);
    let geometry = PlaneGeometry {
        width: domain.width / step,
        height: domain.height / step,
    };
    ensure!(
        geometry.width >= 32 && geometry.height >= 32,
        "mosaic guide is too small"
    );
    let n = geometry
        .width
        .checked_mul(geometry.height)
        .context("guide dimensions overflow")?;
    let reserved = n
        .checked_mul(128)
        .and_then(|a| {
            domain
                .full
                .pixels()
                .checked_mul(32)
                .and_then(|b| a.checked_add(b))
        })
        .and_then(|a| {
            session
                .len()
                .checked_mul(128)
                .and_then(|b| a.checked_add(b))
        })
        .context("mosaic guide reservation overflow")?;
    ensure!(
        reserved <= budget,
        "mosaic guide exceeds explicit memory budget"
    );
    let origin = [
        domain.x as f64 + (step - 1) as f64 * 0.5,
        domain.y as f64 + (step - 1) as f64 * 0.5,
    ];
    let mut intensity = vec![0.0_f32; n];
    let mut counts = vec![0_u8; n];
    let mut covered = vec![false; n];
    let mut usable_focus = vec![false; n];
    let mut ordinals = vec![f32::NAN; n];
    let mut widths = vec![f32::NAN; n];
    let mut source_indices = vec![[usize::MAX; 4]; n];
    let mut assignments: BTreeMap<usize, Vec<usize>> = BTreeMap::new();
    for y in 0..geometry.height {
        for x in 0..geometry.width {
            let pixel = y * geometry.width + x;
            let native = (y * step + step / 2) * domain.width + x * step + step / 2;
            ordinals[pixel] = field.ordinal[native];
            widths[pixel] = field.width_frames[native];
            usable_focus[pixel] = field.usable[native];
            if !field.covered[native] {
                continue;
            }
            let mut chosen = BTreeSet::new();
            for (rank, global) in field.top_global_indices[native].into_iter().enumerate() {
                if !track.global_range.contains(&global) || map.warps()[global].placed().is_none() {
                    continue;
                }
                if field.usable[native] {
                    let distance =
                        ((global - track.global_range.start) as f32 - field.ordinal[native]).abs();
                    if distance > field.width_frames[native].max(1.0) {
                        continue;
                    }
                } else if rank != 0 {
                    continue;
                }
                chosen.insert(global);
            }
            for global in chosen {
                assignments.entry(global).or_default().push(pixel);
            }
        }
    }
    let mut contributions = Vec::new();
    for (global, pixels) in assignments {
        let original = cache.load_or_decode(&session.frames[global], &identities[global])?;
        ensure!(
            original.geometry() == domain.full,
            "mosaic guide original geometry differs"
        );
        let transform = map.warps()[global]
            .placed()
            .context("guide placement disappeared")?;
        let mut accepted = 0;
        for pixel in pixels {
            let x = pixel % geometry.width;
            let y = pixel / geometry.width;
            let start = [domain.x + x * step, domain.y + y * step];
            if let Some(value) =
                sample_box(original.as_ref(), original.levels(), transform, start, step)
            {
                intensity[pixel] += value;
                source_indices[pixel][usize::from(counts[pixel])] = global;
                counts[pixel] += 1;
                accepted += 1;
            }
        }
        contributions.push((global, accepted));
    }
    for i in 0..n {
        covered[i] = counts[i] > 0;
        if covered[i] {
            intensity[i] /= f32::from(counts[i]);
            let native = (i / geometry.width * step + step / 2) * domain.width
                + i % geometry.width * step
                + step / 2;
            rank_witnesses(&mut source_indices[i], &field.top_global_indices[native]);
        }
        usable_focus[i] &= covered[i];
    }
    let mut focus_hash = Sha256::new();
    for frame in &field.frames {
        focus_hash.update((frame.global_index as u64).to_le_bytes());
        focus_hash.update(frame.acquisition.to_le_bytes());
    }
    for i in 0..field_pixels {
        for value in [
            field.ordinal[i],
            field.width_frames[i],
            field.prominence_sigma[i],
            field.perplexity[i],
        ] {
            focus_hash.update(value.to_bits().to_le_bytes());
        }
        for global in field.top_global_indices[i] {
            focus_hash.update((global as u64).to_le_bytes());
        }
        focus_hash.update([
            field.flags[i],
            u8::from(field.covered[i]),
            u8::from(field.usable[i]),
            u8::from(focus.raw_coverage[i]),
        ]);
    }
    let mut guide_hash = Sha256::new();
    for value in [
        pass,
        geometry.width,
        geometry.height,
        step,
        domain.x,
        domain.y,
    ] {
        guide_hash.update((value as u64).to_le_bytes());
    }
    for i in 0..n {
        guide_hash.update(intensity[i].to_bits().to_le_bytes());
        guide_hash.update([u8::from(covered[i]), u8::from(usable_focus[i])]);
        for source in source_indices[i] {
            guide_hash.update((source as u64).to_le_bytes());
        }
    }
    let receipt = GuideReceipt { pass, source_geometry: [domain.full.width, domain.full.height],
        guide_geometry: [geometry.width, geometry.height], origin_quad_pixels: origin, step_quad_pixels: step,
        alignment_sha256: hex(&Sha256::digest(map.to_text().as_bytes())),
        focus_evidence_sha256: hex(&focus_hash.finalize()), guide_sha256: hex(&guide_hash.finalize()),
        covered_pixels: covered.iter().filter(|&&v| v).count(),
        usable_focus_pixels: usable_focus.iter().filter(|&&v| v).count(), source_contributions: contributions,
        reserved_work_bytes: reserved,
        construction: "original-CFA bilinear green box; equal mean of regularized top-four within measured focus width; accepted original witnesses retain strongest-first focus rank; ambiguous shape uses regularized peak only; geometry diagnostic, never final pixels".into() };
    let guide = MosaicGuide {
        pass,
        source_geometry: domain.full,
        geometry,
        origin,
        step,
        intensity,
        covered,
        focus_ordinal: ordinals,
        focus_width: widths,
        usable_focus,
        source_indices,
        receipt,
    };
    guide.validate()?;
    Ok(guide)
}

/// Source-ordered streaming must not turn a lower acquisition ordinal into the
/// preferred native witness. Sort only originals that actually supplied pixels;
/// a clipped/missing strongest source is never reintroduced by its focus rank.
fn rank_witnesses(accepted: &mut [usize; 4], preferred: &[usize; 4]) {
    accepted.sort_by_key(|&source| {
        (
            source == usize::MAX,
            preferred
                .iter()
                .position(|&p| p == source)
                .unwrap_or(usize::MAX),
            source,
        )
    });
}

pub(super) fn sample_box<S: QuadSource + ?Sized>(
    source: &S,
    levels: Levels,
    transform: Similarity,
    start: [usize; 2],
    side: usize,
) -> Option<f32> {
    let g = source.geometry();
    let center = [g.width as f64 * 0.5, g.height as f64 * 0.5];
    let mut sum = 0.0_f32;
    for y in start[1]..start[1] + side {
        for x in start[0]..start[0] + side {
            for (dx, dy) in [(1, 0), (0, 1)] {
                let site = [dx as f64 * 0.5 - 0.25, dy as f64 * 0.5 - 0.25];
                let (sx, sy) = transform.apply_at(
                    x as f64 + site[0],
                    y as f64 + site[1],
                    center[0],
                    center[1],
                );
                sum += sample_site(source, levels, [sx - site[0], sy - site[1]], dx, dy)?;
            }
        }
    }
    Some(sum / (2 * side * side) as f32)
}

/// Preserve the actual bounded diagnostic image even when geometry refuses.
/// These files are deliberately labelled as diagnostics, never photographs.
pub fn save_diagnostics(path: &std::path::Path, guide: &MosaicGuide) -> Result<()> {
    use std::io::Write;
    guide.validate()?;
    let mut output = std::io::BufWriter::new(
        std::fs::OpenOptions::new()
            .write(true)
            .create_new(true)
            .open(path.join("diagnostic-guide.tiff"))?,
    );
    tiff::encoder::TiffEncoder::new(&mut output)?
        .write_image::<tiff::encoder::colortype::Gray32Float>(
            guide.geometry.width.try_into()?,
            guide.geometry.height.try_into()?,
            &guide.intensity,
        )?;
    output.flush()?;
    output.get_ref().sync_all()?;
    let mut mask = std::io::BufWriter::new(
        std::fs::OpenOptions::new()
            .write(true)
            .create_new(true)
            .open(path.join("diagnostic-guide-covered.tiff"))?,
    );
    tiff::encoder::TiffEncoder::new(&mut mask)?.write_image::<tiff::encoder::colortype::Gray8>(
        guide.geometry.width.try_into()?,
        guide.geometry.height.try_into()?,
        &guide
            .covered
            .iter()
            .map(|&v| u8::from(v))
            .collect::<Vec<_>>(),
    )?;
    mask.flush()?;
    mask.get_ref().sync_all()?;
    Ok(())
}
fn sample_site<S: QuadSource + ?Sized>(
    source: &S,
    levels: Levels,
    point: [f64; 2],
    dx: usize,
    dy: usize,
) -> Option<f32> {
    let g = source.geometry();
    let [x, y] = point;
    if !x.is_finite()
        || !y.is_finite()
        || x < 0.0
        || y < 0.0
        || x > (g.width - 1) as f64
        || y > (g.height - 1) as f64
    {
        return None;
    }
    let ix = (x.floor() as usize).min(g.width - 2);
    let iy = (y.floor() as usize).min(g.height - 2);
    let fx = (x - ix as f64) as f32;
    let fy = (y - iy as f64) as f32;
    let mut result = 0.0_f32;
    for (sy, wy) in [(iy, 1.0 - fy), (iy + 1, fy)] {
        let (r0, r1) = source.quad_rows(sy);
        let row = if dy == 0 { r0 } else { r1 };
        if row.len() < g.width * 2 {
            return None;
        }
        for (sx, wx) in [(ix, 1.0 - fx), (ix + 1, fx)] {
            let weight = wx * wy;
            let value = f32::from(row[2 * sx + dx]);
            if weight != 0.0 && value >= levels.white {
                return None;
            }
            result += weight * (value - levels.black);
        }
    }
    Some(result)
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn native_witness_rank_survives_source_order_and_missing_peak() {
        let preferred = [9, 7, 3, usize::MAX];
        let mut accepted = [3, 7, 9, usize::MAX];
        rank_witnesses(&mut accepted, &preferred);
        assert_eq!(accepted, preferred);
        let mut clipped_peak = [3, 7, usize::MAX, usize::MAX];
        rank_witnesses(&mut clipped_peak, &preferred);
        assert_eq!(clipped_peak, [7, 3, usize::MAX, usize::MAX]);
        let mut none = [usize::MAX; 4];
        rank_witnesses(&mut none, &preferred);
        assert_eq!(none, [usize::MAX; 4]);
    }
    struct Source {
        data: Vec<u16>,
        g: PlaneGeometry,
    }
    impl QuadSource for Source {
        fn geometry(&self) -> PlaneGeometry {
            self.g
        }
        fn quad_rows(&self, y: usize) -> (&[u16], &[u16]) {
            let a = 4 * self.g.width * y;
            let b = a + 2 * self.g.width;
            (&self.data[a..b], &self.data[b..b + 2 * self.g.width])
        }
    }
    #[test]
    fn diagnostic_box_commissions_centroid_phase_negative_signal_and_clip_support() {
        let g = PlaneGeometry {
            width: 32,
            height: 24,
        };
        let mut source = Source {
            data: vec![0; 4 * g.pixels()],
            g,
        };
        for y in 0..2 * g.height {
            for x in 0..2 * g.width {
                source.data[y * 2 * g.width + x] = (1000 + 3 * x + 7 * y) as u16;
            }
        }
        let levels = Levels {
            black: 2000.0,
            white: 16000.0,
        };
        let value = sample_box(&source, levels, Similarity::IDENTITY, [5, 6], 4).unwrap();
        // Average green sensor sites have (2*x+.5,2*y+.5); the 4x4 box
        // has quad centre (6.5,7.5), independently of the gather loop.
        let expected = 1000.0 + 3.0 * 13.5 + 7.0 * 15.5 - 2000.0;
        assert_eq!(value, expected);
        assert!(value < 0.0);
        source.data[2 * 6 * 2 * g.width + 2 * 5 + 1] = 16000;
        assert!(sample_box(&source, levels, Similarity::IDENTITY, [5, 6], 4).is_none());
        assert!(sample_box(&source, levels, Similarity::IDENTITY, [31, 23], 4).is_none());
    }
}
